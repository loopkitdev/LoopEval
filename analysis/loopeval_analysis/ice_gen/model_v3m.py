"""v3m generator: meal pulses, carb entries and manual boluses as separate events (dataset_v3m), drawn in order
within a slot, each conditioned on the earlier draws:
  state            background ICE (mixture of 8), meal start (P), pulse size (mixture of 3)
  peak | size, duration | size + peak
  entry, log grams | meal drawn, its size
  bolus, override, log ratio, log units | meal, size, entry, grams
Per-person traits: an explicit logit offset per person on the meal, entry and bolus heads, trained jointly with a
Gaussian prior (sd TRAIT_SD) instead of left to the profile vector, which pulled every person's rates toward the
middle (ice LESSONS 39). The profile vector still feeds the GRU for everything else.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from .model_v2 import mdn_nll, mdn_sample
from .dataset_v3m import TARGETS

B = ["meal", "entry", "bolus", "b_mode"]
G = ["m_lpeak", "m_ldur"]
M = ["m_lsize", "e_lg", "b_lr", "b_lu"]
TRAITS = ["meal", "entry", "bolus"]


class ICEGenV3M(nn.Module):
    arch = "v3m"
    K_ICE, K = 8, 3
    MAIN = ["bgice", "meal", "m_lsize"]
    STAGES = [  # (drawn here, conditioned on these earlier draws; *_ok = presence flags)
        (["m_lpeak"], ["m_lsize"]),
        (["m_ldur"], ["m_lsize", "m_lpeak"]),
        (["entry", "e_lg"], ["meal", "m_lsize"]),
        (["bolus", "b_mode", "b_lr", "b_lu"], ["meal", "m_lsize", "entry", "e_lg"]),
    ]

    def __init__(self, n_features, n_people, profile_dim=16, hidden=256, layers=2):
        super().__init__()
        self.profile = nn.Embedding(n_people, profile_dim)
        nn.init.normal_(self.profile.weight, std=0.1)
        self.trait = nn.Embedding(n_people, len(TRAITS))
        nn.init.zeros_(self.trait.weight)
        self.inp = nn.Linear(n_features + profile_dim, hidden)
        self.gru = nn.GRU(hidden, hidden, num_layers=layers, batch_first=True)
        self.sizes = {"bgice": 3 * self.K_ICE, **{k: 1 for k in B}, **{k: 2 for k in G}, **{k: 3 * self.K for k in M}}
        self.head = nn.Linear(hidden, sum(self.sizes[k] for k in self.MAIN))
        self.stage_heads = nn.ModuleList(
            nn.Sequential(nn.Linear(hidden + len(cond), 128), nn.ReLU(), nn.Linear(128, sum(self.sizes[k] for k in tgt)))
            for tgt, cond in self.STAGES)

    def forward(self, x, person, h=None):
        p = self.profile(person)[:, None, :].expand(-1, x.shape[1], -1)
        z, h = self.gru(torch.relu(self.inp(torch.cat([x, p], -1))), h)
        out = dict(zip(self.MAIN, self.head(z).split([self.sizes[k] for k in self.MAIN], -1)))
        out["z"] = z
        out["trait"] = self.trait(person)[:, None, :].expand(-1, x.shape[1], -1)
        out["meal"] = out["meal"] + out["trait"][..., 0:1]
        return out, h

    def _stage(self, i, out, vals):
        tgt, cond = self.STAGES[i]
        c = []
        for k in cond:   # a value absent (no meal drawn, no entry) enters as 0; meal/entry are the flags
            c.append(torch.nan_to_num(vals[k], nan=0.0))
        o = dict(zip(tgt, self.stage_heads[i](torch.cat([out["z"], torch.stack(c, -1)], -1)).split([self.sizes[k] for k in tgt], -1)))
        if "entry" in o:
            o["entry"] = o["entry"] + out["trait"][..., 1:2]
        if "bolus" in o:
            o["bolus"] = o["bolus"] + out["trait"][..., 2:3]
        return o

    def teacher(self, out, Y):
        y = {k: Y[..., TARGETS.index(k)] for k in TARGETS}
        vals = dict(y)
        vals["m_lsize"] = torch.where(y["meal"] > 0.5, y["m_lsize"], torch.zeros_like(y["m_lsize"]))
        vals["e_lg"] = torch.where(y["entry"] > 0.5, y["e_lg"], torch.zeros_like(y["e_lg"]))
        vals["meal"] = torch.nan_to_num(y["meal"]); vals["entry"] = torch.nan_to_num(y["entry"])
        o = dict(out)
        for i in range(len(self.STAGES)):
            o.update(self._stage(i, out, vals))
        return o

    def loss(self, out, Y, w=None, w_bgice=False, trait_frac=0.0, trait_sd=1.0):
        """trait_frac: this batch's share of all training steps, so the Gaussian prior on the per-person offsets
        (sd trait_sd) is spread over the batches as in a full-data MAP fit."""
        o = self.teacher(out, Y)
        y = {k: Y[..., TARGETS.index(k)] for k in TARGETS}
        z = lambda v, m: torch.where(m, v, torch.zeros_like(v))      # never 0 * v (LESSONS 8)
        parts = {}
        m = torch.isfinite(y["bgice"])
        nll = mdn_nll(o["bgice"], z(y["bgice"], m), self.K_ICE)
        parts["bgice"] = (nll * w)[m].sum() / w[m].sum() if (w_bgice and w is not None) else nll[m].mean()
        given = {"m_": y["meal"] > 0.5, "e_": y["entry"] > 0.5, "b_": y["bolus"] > 0.5}
        cond = lambda k: torch.isfinite(y[k]) & (given[k[:2]] if k[:2] in given else torch.ones_like(m))
        for k in B:
            c = cond(k)
            if c.any():
                ww = w[c] if (w is not None and k in TRAITS) else None
                parts[k] = F.binary_cross_entropy_with_logits(o[k][..., 0][c], y[k][c], weight=ww)
        for k in G:
            c = cond(k)
            if c.any():
                mu, ls = o[k].unbind(-1); ls = ls.clamp(-5, 3)
                parts[k] = (0.5 * ((z(y[k], c) - mu) / ls.exp()) ** 2 + ls)[c].mean()
        for k in M:
            c = cond(k)
            if c.any():
                parts[k] = mdn_nll(o[k], z(y[k], c), self.K)[c].mean()
        loss = sum(parts.values())
        if trait_frac > 0:
            loss = loss + trait_frac * 0.5 * (self.trait.weight ** 2).sum() / trait_sd ** 2
        return loss, parts

    @torch.no_grad()
    def sample(self, out, calib=None):
        """calib: {head: logit offset} applied to meal / entry / bolus before drawing (closed-loop calibrations)."""
        calib = calib or {}
        o = {k: v[:, -1] for k, v in out.items()}
        s = {"bgice": mdn_sample(o["bgice"], self.K_ICE)}
        u = lambda: torch.rand_like(s["bgice"])
        draw = lambda k, oo: (u() < torch.sigmoid(oo[k][:, 0] + calib.get(k, 0.0))) if k in B else \
            (oo[k][:, 0] + oo[k][:, 1].clamp(-5, 3).exp() * torch.randn_like(s["bgice"])) if k in G else mdn_sample(oo[k], self.K)
        s["meal"] = draw("meal", o); s["m_lsize"] = draw("m_lsize", o)
        vals = {"meal": s["meal"].float(), "m_lsize": torch.where(s["meal"], s["m_lsize"], torch.zeros_like(s["m_lsize"]))}
        for i, (tgt, _) in enumerate(self.STAGES):
            oo = self._stage(i, o, vals)
            for k in tgt:
                s[k] = draw(k, oo)
            if "m_lpeak" in tgt:
                vals["m_lpeak"] = s["m_lpeak"].float()
            if "entry" in tgt:
                vals["entry"] = s["entry"].float(); vals["e_lg"] = torch.where(s["entry"], s["e_lg"], torch.zeros_like(s["e_lg"]))
        return s


class ICEGenV3M3(ICEGenV3M):
    """v3m3 (dataset_v3m3): an entry that starts a meal draws its pulse with it. Stages, in order within a slot:
      peak | size, duration | size + peak                 (a pulse begun without an entry)
      entry, log grams | meal, size
      starts a meal (P), minutes to onset, pulse size | entry, grams
      peak, duration of that pulse: the same heads as a meal's, fed its size
      bolus, override, log ratio, log units | meal, size, entry, grams
    """
    arch = "v3m3"
    STAGES = [  # (drawn here, conditioned on, head index; a stage reusing a head renames its outputs in order)
        (["m_lpeak"], ["m_lsize"], 0),
        (["m_ldur"], ["m_lsize", "m_lpeak"], 1),
        (["entry", "e_lg"], ["meal", "m_lsize"], 2),
        (["e_new", "e_off", "e_lsize"], ["entry", "e_lg"], 3),
        (["e_lpeak"], ["e_lsize"], 0),
        (["e_ldur"], ["e_lsize", "e_lpeak"], 1),
        (["bolus", "b_mode", "b_lr", "b_lu"], ["meal", "m_lsize", "entry", "e_lg"], 4),
    ]
    HEADS = [0, 1, 2, 3, 6]   # the stages that own a head
    GIVEN = {"m_": "meal", "e_": "entry", "b_": "bolus"}
    NEW = ["e_off", "e_lsize", "e_lpeak", "e_ldur"]   # given entry AND e_new
    BERN = B + ["e_new"]
    TRAIT_NAMES = TRAITS

    def __init__(self, n_features, n_people, profile_dim=16, hidden=256, layers=2):
        nn.Module.__init__(self)
        self.profile = nn.Embedding(n_people, profile_dim)
        nn.init.normal_(self.profile.weight, std=0.1)
        self.trait = nn.Embedding(n_people, len(self.TRAIT_NAMES))
        nn.init.zeros_(self.trait.weight)
        self.inp = nn.Linear(n_features + profile_dim, hidden)
        self.gru = nn.GRU(hidden, hidden, num_layers=layers, batch_first=True)
        self.B = self.BERN; self.G = G + ["e_off", "e_lpeak", "e_ldur"]; self.M = M + ["e_lsize"]
        self.sizes = {"bgice": 3 * self.K_ICE, **{k: 1 for k in self.B}, **{k: 2 for k in self.G}, **{k: 3 * self.K for k in self.M}}
        self.head = nn.Linear(hidden, sum(self.sizes[k] for k in self.MAIN))
        self.stage_heads = nn.ModuleList(
            nn.Sequential(nn.Linear(hidden + len(self.STAGES[i][1]), 128), nn.ReLU(), nn.Linear(128, sum(self.sizes[k] for k in self.STAGES[i][0])))
            for i in self.HEADS)

    def _stage(self, i, out, vals):
        tgt, cond, h = self.STAGES[i]
        c = torch.stack([torch.nan_to_num(vals[k], nan=0.0) for k in cond], -1)
        o = dict(zip(tgt, self.stage_heads[h](torch.cat([out["z"], c], -1)).split([self.sizes[k] for k in tgt], -1)))
        if "entry" in o:
            o["entry"] = o["entry"] + out["trait"][..., 1:2]
        if "bolus" in o:
            o["bolus"] = o["bolus"] + out["trait"][..., 2:3]
        return o

    def teacher(self, out, Y):
        from .dataset_v3m3 import TARGETS as T3
        y = {k: Y[..., T3.index(k)] for k in T3}
        vals = dict(y)
        for flag, keys in (("meal", ["m_lsize", "m_lpeak"]), ("entry", ["e_lg"])):
            for k in keys:
                vals[k] = torch.where(y[flag] > 0.5, y[k], torch.zeros_like(y[k]))
        new = (y["entry"] > 0.5) & (y["e_new"] > 0.5)
        for k in ("e_lsize", "e_lpeak"):
            vals[k] = torch.where(new, y[k], torch.zeros_like(y[k]))
        vals["meal"] = torch.nan_to_num(y["meal"]); vals["entry"] = torch.nan_to_num(y["entry"])
        o = dict(out)
        for i in range(len(self.STAGES)):
            o.update(self._stage(i, out, vals))
        return o

    def loss(self, out, Y, w=None, w_bgice=False, trait_frac=0.0, trait_sd=1.0):
        from .dataset_v3m3 import TARGETS as T3
        o = self.teacher(out, Y)
        y = {k: Y[..., T3.index(k)] for k in T3}
        z = lambda v, m: torch.where(m, v, torch.zeros_like(v))
        parts = {}
        m = torch.isfinite(y["bgice"])
        nll = mdn_nll(o["bgice"], z(y["bgice"], m), self.K_ICE)
        parts["bgice"] = (nll * w)[m].sum() / w[m].sum() if (w_bgice and w is not None) else nll[m].mean()
        new = (y["entry"] > 0.5) & (y["e_new"] > 0.5)

        def cond(k):
            c = torch.isfinite(y[k])
            if k in self.NEW:
                return c & new
            if k[:2] in self.GIVEN and k not in ("meal", "entry", "bolus"):
                return c & (y[self.GIVEN[k[:2]]] > 0.5)
            return c
        for k in self.B:
            c = cond(k)
            if c.any():
                ww = w[c] if (w is not None and k in TRAITS) else None
                parts[k] = F.binary_cross_entropy_with_logits(o[k][..., 0][c], y[k][c], weight=ww)
        for k in self.G:
            c = cond(k)
            if c.any():
                mu, ls = o[k].unbind(-1); ls = ls.clamp(-5, 3)
                parts[k] = (0.5 * ((z(y[k], c) - mu) / ls.exp()) ** 2 + ls)[c].mean()
        for k in self.M:
            c = cond(k)
            if c.any():
                parts[k] = mdn_nll(o[k], z(y[k], c), self.K)[c].mean()
        loss = sum(parts.values())
        if trait_frac > 0:
            loss = loss + trait_frac * 0.5 * (self.trait.weight ** 2).sum() / trait_sd ** 2
        return loss, parts

    @torch.no_grad()
    def sample(self, out, calib=None):
        calib = calib or {}
        o = {k: v[:, -1] for k, v in out.items()}
        s = {"bgice": mdn_sample(o["bgice"], self.K_ICE)}
        u = lambda: torch.rand_like(s["bgice"])
        draw = lambda k, oo: (u() < torch.sigmoid(oo[k][:, 0] + calib.get(k, 0.0))) if k in self.B else \
            (oo[k][:, 0] + oo[k][:, 1].clamp(-5, 3).exp() * torch.randn_like(s["bgice"])) if k in self.G else mdn_sample(oo[k], self.K)
        s["meal"] = draw("meal", o); s["m_lsize"] = draw("m_lsize", o)
        zero = torch.zeros_like(s["bgice"])
        vals = {"meal": s["meal"].float(), "m_lsize": torch.where(s["meal"], s["m_lsize"], zero)}
        for i, (tgt, _, _) in enumerate(self.STAGES):
            oo = self._stage(i, o, vals)
            for k in tgt:
                s[k] = draw(k, oo); vals[k] = s[k].float()
            if "m_lpeak" in tgt:
                vals["m_lpeak"] = torch.where(s["meal"], s["m_lpeak"], zero)
            if "e_lg" in tgt:
                vals["entry"] = s["entry"].float(); vals["e_lg"] = torch.where(s["entry"], s["e_lg"], zero)
        return s


class ICEGenV3M4(ICEGenV3M3):
    """v3m4: the bolus decision split by whether an entry was drawn this step, each its own head and per-person trait:
      b_with   P(bolus | entry)     scored on entry steps only    (meal-bolus habit)
      b_alone  P(bolus | no entry)  scored on the other steps     (corrections, top-ups: rare on an automated system)
    v3m3's single head, averaged over all steps (entries ~1% of them), learned P(bolus | entry) 0.23-0.38 where the data
    has 0.76 (i005) and over-predicted boluses with no entry (0.016 vs 0.008), so generated meals went unbolused."""
    arch = "v3m4"
    TRAIT_NAMES = ["meal", "entry", "b_with", "b_alone"]
    STAGES = ICEGenV3M3.STAGES[:-1] + [(["b_with", "b_alone", "b_mode", "b_lr", "b_lu"], ["meal", "m_lsize", "entry", "e_lg"], 4)]
    BERN = ["meal", "entry", "b_mode", "e_new", "b_with", "b_alone"]

    def _stage(self, i, out, vals):
        tgt, cond, h = self.STAGES[i]
        c = torch.stack([torch.nan_to_num(vals[k], nan=0.0) for k in cond], -1)
        o = dict(zip(tgt, self.stage_heads[h](torch.cat([out["z"], c], -1)).split([self.sizes[k] for k in tgt], -1)))
        for k, j in (("entry", 1), ("b_with", 2), ("b_alone", 3)):
            if k in o:
                o[k] = o[k] + out["trait"][..., j:j + 1]
        return o

    def loss(self, out, Y, w=None, w_bgice=False, trait_frac=0.0, trait_sd=1.0):
        from .dataset_v3m3 import TARGETS as T3
        o = self.teacher(out, Y)
        y = {k: Y[..., T3.index(k)] for k in T3}
        z = lambda v, m: torch.where(m, v, torch.zeros_like(v))
        parts = {}
        m = torch.isfinite(y["bgice"])
        nll = mdn_nll(o["bgice"], z(y["bgice"], m), self.K_ICE)
        parts["bgice"] = (nll * w)[m].sum() / w[m].sum() if (w_bgice and w is not None) else nll[m].mean()
        ent = y["entry"] > 0.5; new = ent & (y["e_new"] > 0.5); bol = y["bolus"] > 0.5; fb = torch.isfinite(y["bolus"])
        conds = {"meal": torch.isfinite(y["meal"]), "entry": torch.isfinite(y["entry"]), "e_new": ent & torch.isfinite(y["e_new"]),
                 "b_with": ent & fb, "b_alone": ~ent & fb, "b_mode": bol & torch.isfinite(y["b_mode"])}
        tgt = {"b_with": y["bolus"], "b_alone": y["bolus"]}
        for k in self.B:
            c = conds[k]
            if c.any():
                ww = w[c] if (w is not None and k in ("meal", "entry", "b_alone")) else None
                parts[k] = F.binary_cross_entropy_with_logits(o[k][..., 0][c], tgt.get(k, y.get(k))[c], weight=ww)
        given = lambda k: torch.isfinite(y[k]) & (new if k in self.NEW else (y["meal"] > 0.5) if k.startswith("m_") else ent if k.startswith("e_") else bol)
        for k in self.G:
            c = given(k)
            if c.any():
                mu, ls = o[k].unbind(-1); ls = ls.clamp(-5, 3)
                parts[k] = (0.5 * ((z(y[k], c) - mu) / ls.exp()) ** 2 + ls)[c].mean()
        for k in self.M:
            c = given(k)
            if c.any():
                parts[k] = mdn_nll(o[k], z(y[k], c), self.K)[c].mean()
        loss = sum(parts.values())
        if trait_frac > 0:
            loss = loss + trait_frac * 0.5 * (self.trait.weight ** 2).sum() / trait_sd ** 2
        return loss, parts

    @torch.no_grad()
    def sample(self, out, calib=None):
        s = super().sample(out, calib)
        s["bolus"] = torch.where(s["entry"], s["b_with"], s["b_alone"])
        return s


class ICEGenV3M5(ICEGenV3M4):
    """v3m5: background ICE from its own recurrent path that does not see the CGM-trend inputs. The trend is mostly the last
    15 min of background ICE itself (plus CGM noise): in training it carries real, smooth ICE; in generation the model's own
    near-independent draws, so a wide draw read as a volatile state and widened the next (exposure bias). Swap test,
    2026-10-13: moving bg_trend alone onto its closed-loop distribution added 13.8 mg/dL/h to v3m4's predicted sd (5.6 for v3k);
    every other input < 3. Behavior heads keep the full inputs (low response lives there)."""
    arch = "v3m5"
    ICE_DROP = ["bg_trend", "bg_pred30", "heading_low", "low30"]

    def __init__(self, n_features, n_people, profile_dim=16, hidden=256, layers=2, features=None):
        super().__init__(n_features, n_people, profile_dim, hidden, layers)
        self.ice_mask = torch.ones(n_features)
        if features is not None:
            for f in self.ICE_DROP:
                if f in features:
                    self.ice_mask[features.index(f)] = 0.0
        self.register_buffer("ice_keep", self.ice_mask)
        self.inp_ice = nn.Linear(n_features + profile_dim, hidden)
        self.gru_ice = nn.GRU(hidden, hidden, num_layers=layers, batch_first=True)
        self.head_ice = nn.Linear(hidden, self.sizes["bgice"])

    def forward(self, x, person, h=None):
        h1, h2 = h if isinstance(h, tuple) else (None, None)
        out, h1 = super().forward(x, person, h1)
        p = self.profile(person)[:, None, :].expand(-1, x.shape[1], -1)
        z2, h2 = self.gru_ice(torch.relu(self.inp_ice(torch.cat([x * self.ice_keep, p], -1))), h2)
        out["bgice"] = self.head_ice(z2)
        return out, (h1, h2)
