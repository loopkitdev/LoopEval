"""v3 generator: meals as events. One GRU state (with the per-person profile vector) drives:
  background ICE   mixture of 8 Gaussians (ICE minus meal pulses, scaled)
  meal anchor      P(a meal starts its first action next slot) and, given one, its attributes:
                   size (mixture of 3 on log g-eq), peak and duration (log h, Gaussian), offsets of
                   absorption onset / carb entry / meal bolus from the anchor (log1p min,
                   Gaussian), announced (P), log grams logged (mixture of 3), meal bolus (P), override
                   (P), log ratio / log units (mixtures of 3)
  correction       P(a bolus not tied to a meal), override (P), log ratio / log units
The meal pulse itself is not learned point by point: kernel.py turns size/peak/duration into an
ICE bump that integrates to the meal's size and ends.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from .model_v2 import mdn_nll, mdn_sample
from .dataset_v3 import TARGETS

G = ["m_lpeak", "m_ldur", "m_onset", "m_entry", "m_bolus"]     # Gaussian attributes
B = ["meal", "m_ann", "m_hasbol", "m_mode", "corr", "c_mode"]           # Bernoulli
M = ["m_lsize", "m_lg", "m_lr", "m_lu", "c_lr", "c_lu"]                         # mixtures of 3


class ICEGenV3(nn.Module):
    K_ICE, K = 8, 3

    def __init__(self, n_features, n_people, profile_dim=16, hidden=256, layers=2):
        super().__init__()
        self.profile = nn.Embedding(n_people, profile_dim)
        nn.init.normal_(self.profile.weight, std=0.1)
        self.inp = nn.Linear(n_features + profile_dim, hidden)
        self.gru = nn.GRU(hidden, hidden, num_layers=layers, batch_first=True)
        self.sizes = {"bgice": 3 * self.K_ICE, **{k: 1 for k in B}, **{k: 2 for k in G}, **{k: 3 * self.K for k in M}}
        self.head = nn.Linear(hidden, sum(self.sizes.values()))

    def forward(self, x, person, h=None):
        p = self.profile(person)[:, None, :].expand(-1, x.shape[1], -1)
        z, h = self.gru(torch.relu(self.inp(torch.cat([x, p], -1))), h)
        return dict(zip(self.sizes, self.head(z).split(list(self.sizes.values()), -1))), h

    def loss(self, out, Y, w=None, w_bgice=False):
        """w: optional per-step weight on the meal / correction start terms. Weighting by STATE (e.g. near a
        low, where rescues are rare in the data) makes the head fit that region harder without biasing the
        hazard there, since events and non-events in the same state get the same weight. w_bgice: apply w to
        the background-ICE density as well (the same argument: a state weight, not an outcome weight)."""
        y = {k: Y[..., TARGETS.index(k)] for k in TARGETS}
        z = lambda v, m: torch.where(m, v, torch.zeros_like(v))      # never 0 * v (LESSONS 8)
        parts = {}
        m = torch.isfinite(y["bgice"])
        nll = mdn_nll(out["bgice"], z(y["bgice"], m), self.K_ICE)
        parts["bgice"] = (nll * w)[m].sum() / w[m].sum() if (w_bgice and w is not None) else nll[m].mean()
        meal = y["meal"] > 0.5
        for k in B:
            cond = torch.isfinite(y[k]) & (meal if k.startswith("m_") else (y["corr"] > 0.5) if k == "c_mode" else torch.ones_like(meal))
            if cond.any():
                ww = w[cond] if (w is not None and k in ("meal", "corr")) else None
                parts[k] = F.binary_cross_entropy_with_logits(out[k][..., 0][cond], y[k][cond], weight=ww)
        for k in G:
            cond = torch.isfinite(y[k]) & meal
            if cond.any():
                mu, ls = out[k].unbind(-1); ls = ls.clamp(-5, 3)
                parts[k] = (0.5 * ((z(y[k], cond) - mu) / ls.exp()) ** 2 + ls)[cond].mean()
        for k in M:
            cond = torch.isfinite(y[k]) & (meal if k.startswith("m_") else y["corr"] > 0.5)
            if cond.any():
                parts[k] = mdn_nll(out[k], z(y[k], cond), self.K)[cond].mean()
        return sum(parts.values()), parts

    @torch.no_grad()
    def sample(self, out):
        o = {k: v[:, -1] for k, v in out.items()}
        s = {"bgice": mdn_sample(o["bgice"], self.K_ICE)}
        for k in B:
            s[k] = torch.rand_like(s["bgice"]) < torch.sigmoid(o[k][:, 0])
        for k in G:
            mu, ls = o[k].unbind(-1)
            s[k] = mu + ls.clamp(-5, 3).exp() * torch.randn_like(mu)
        for k in M:
            s[k] = mdn_sample(o[k], self.K)
        return s
