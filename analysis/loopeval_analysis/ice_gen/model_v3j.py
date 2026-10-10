"""v3j: v3 with a meal's attributes drawn JOINTLY instead of independently given the GRU state.

v3 samples pulse size, logged grams and the bolus independently given the state, so a 10 g-eq pulse can be
logged as 43 g (within-donor corr(log size, log grams) 0.10 generated vs 0.29 real) and Loop doses on the
grams. Here the meal is drawn in three stages, each conditioned on the earlier ones:
  A  from the state:                        meal / correction start, pulse size, peak, duration, onset
  B  + (size, peak, duration):              announced, log grams logged, entry offset
  C  + (size, peak, duration, ann, grams):  meal bolus, override, log ratio, log units, bolus offset
Training conditions B and C on the labeled values (teacher forcing); sampling on the drawn ones.
"""
from __future__ import annotations

import torch
import torch.nn as nn

from .model_v2 import mdn_sample
from .model_v3 import ICEGenV3, G, B, M

STAGE_B = ["m_ann", "m_lg", "m_entry"]
STAGE_C = ["m_hasbol", "m_mode", "m_lr", "m_lu", "m_bolus"]
COND_B = ["m_lsize", "m_lpeak", "m_ldur"]
COND_C = COND_B + ["m_ann", "m_lg"]


class ICEGenV3J(ICEGenV3):
    arch = "v3j"

    def __init__(self, n_features, n_people, profile_dim=16, hidden=256, layers=2):
        super().__init__(n_features, n_people, profile_dim, hidden, layers)
        sz = self.sizes
        self.head_b = nn.Sequential(nn.Linear(hidden + len(COND_B), 128), nn.ReLU(), nn.Linear(128, sum(sz[k] for k in STAGE_B)))
        self.head_c = nn.Sequential(nn.Linear(hidden + len(COND_C) + 1, 128), nn.ReLU(), nn.Linear(128, sum(sz[k] for k in STAGE_C)))

    def forward(self, x, person, h=None):
        p = self.profile(person)[:, None, :].expand(-1, x.shape[1], -1)
        z, h = self.gru(torch.relu(self.inp(torch.cat([x, p], -1))), h)
        out = dict(zip(self.sizes, self.head(z).split(list(self.sizes.values()), -1)))
        out["z"] = z
        return out, h

    def cond_heads(self, z, vals):
        """vals: {name: tensor [..]} of the conditioning attributes (NaN where absent)."""
        f = lambda k: torch.nan_to_num(vals[k], nan=0.0)
        cb = torch.stack([f(k) for k in COND_B], -1)
        ob = dict(zip(STAGE_B, self.head_b(torch.cat([z, cb], -1)).split([self.sizes[k] for k in STAGE_B], -1)))
        lg_ok = torch.isfinite(vals["m_lg"]).float()
        cc = torch.cat([torch.stack([f(k) for k in COND_C], -1), lg_ok[..., None]], -1)
        oc = dict(zip(STAGE_C, self.head_c(torch.cat([z, cc], -1)).split([self.sizes[k] for k in STAGE_C], -1)))
        return {**ob, **oc}

    def teacher(self, out, Y):
        from .dataset_v3 import TARGETS
        vals = {k: Y[..., TARGETS.index(k)] for k in COND_C}
        return {**out, **self.cond_heads(out["z"], vals)}

    def loss(self, out, Y, w=None):
        return super().loss(self.teacher(out, Y), Y, w)

    @torch.no_grad()
    def sample(self, out):
        o = {k: v[:, -1] for k, v in out.items()}
        s = {"bgice": mdn_sample(o["bgice"], self.K_ICE)}
        draw = lambda k, oo: (torch.rand_like(s["bgice"]) < torch.sigmoid(oo[k][:, 0])) if k in B else \
            (oo[k][:, 0] + oo[k][:, 1].clamp(-5, 3).exp() * torch.randn_like(s["bgice"])) if k in G else mdn_sample(oo[k], self.K)
        for k in ["meal", "corr", "c_mode", "c_lr", "c_lu", "m_lsize", "m_lpeak", "m_ldur", "m_onset"]:
            s[k] = draw(k, o)
        ob = self.cond_heads(o["z"], {k: s[k].float() for k in COND_B} | {"m_ann": torch.zeros_like(s["bgice"]), "m_lg": torch.zeros_like(s["bgice"])})
        for k in STAGE_B:
            s[k] = draw(k, ob)
        vals = {k: s[k].float() for k in COND_B} | {"m_ann": s["m_ann"].float(),
                                                    "m_lg": torch.where(s["m_ann"], s["m_lg"], torch.full_like(s["m_lg"], float("nan")))}
        oc = self.cond_heads(o["z"], vals)
        for k in STAGE_C:
            s[k] = draw(k, oc)
        return s
