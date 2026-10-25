"""v2 generator: one GRU state (with the per-person profile vector) drives three heads for the next
5-min slot:
  ICE          mixture of K Gaussians (scaled ICE)
  carb entry   P(entry); log grams ~ mixture of 3; log absorption hours ~ Gaussian
  manual bolus P(bolus); P(override | bolus); calculator mode: log(requested/recommended) ~ mixture
               of 3; override mode: log units ~ mixture of 3
Event probabilities are trained with plain (unweighted) cross-entropy so they stay calibrated for
sampling.
"""
from __future__ import annotations

import math
import torch
import torch.nn as nn
import torch.nn.functional as F

LOG2PI = math.log(2 * math.pi)


def mdn_nll(params, y, k):
    logit, mu, ls = params.split(k, -1)
    ls = ls.clamp(-5, 3)
    lp = torch.log_softmax(logit, -1) - 0.5 * ((y[..., None] - mu) / ls.exp()) ** 2 - ls - 0.5 * LOG2PI
    return -torch.logsumexp(lp, -1)


def mdn_sample(params, k):
    logit, mu, ls = params.split(k, -1)
    c = torch.distributions.Categorical(logits=logit).sample()[..., None]
    return (mu.gather(-1, c) + ls.clamp(-5, 3).gather(-1, c).exp() * torch.randn_like(c, dtype=mu.dtype))[..., 0]


class ICEGenV2(nn.Module):
    K_ICE, K_EV = 8, 3

    def __init__(self, n_features, n_people, profile_dim=16, hidden=256, layers=2):
        super().__init__()
        self.profile = nn.Embedding(n_people, profile_dim)
        nn.init.normal_(self.profile.weight, std=0.1)
        self.inp = nn.Linear(n_features + profile_dim, hidden)
        self.gru = nn.GRU(hidden, hidden, num_layers=layers, batch_first=True)
        ke = self.K_EV
        self.sizes = dict(ice=3 * self.K_ICE, carb_p=1, carb_g=3 * ke, carb_abs=2,
                          bol_p=1, bol_mode=1, bol_r=3 * ke, bol_u=3 * ke)
        self.head = nn.Linear(hidden, sum(self.sizes.values()))

    def forward(self, x, person, h=None):
        p = self.profile(person)[:, None, :].expand(-1, x.shape[1], -1)
        z, h = self.gru(torch.relu(self.inp(torch.cat([x, p], -1))), h)
        out = dict(zip(self.sizes, self.head(z).split(list(self.sizes.values()), -1)))
        return out, h

    def loss(self, out, Y):
        """Y [B, T, 8] in dataset_v2.TARGETS order. Returns (total, parts).
        Masked-out targets are replaced by zeros_like, never 0 * y: 0 * NaN is NaN, and a NaN in an
        excluded position still reaches the gradients (it sent the first v2 run to NaN)."""
        ice, cev, clg, clabs, bev, bmode, blr, blu = Y.unbind(-1)
        parts = {}
        m = torch.isfinite(ice)
        parts["ice"] = mdn_nll(out["ice"], torch.where(m, ice, torch.zeros_like(ice)), self.K_ICE)[m].mean()
        parts["carb_p"] = F.binary_cross_entropy_with_logits(out["carb_p"][..., 0], torch.nan_to_num(cev))
        m = (cev > 0.5) & torch.isfinite(clg)
        parts["carb_g"] = mdn_nll(out["carb_g"], torch.where(m, clg, torch.zeros_like(clg)), self.K_EV)[m].mean() if m.any() else ice.new_zeros(())
        m = (cev > 0.5) & torch.isfinite(clabs)
        mu, ls = out["carb_abs"].unbind(-1); ls = ls.clamp(-5, 3)
        y = torch.where(m, clabs, torch.zeros_like(clabs))
        parts["carb_abs"] = (0.5 * ((y - mu) / ls.exp()) ** 2 + ls)[m].mean() if m.any() else ice.new_zeros(())
        parts["bol_p"] = F.binary_cross_entropy_with_logits(out["bol_p"][..., 0], torch.nan_to_num(bev))
        m = (bev > 0.5) & torch.isfinite(bmode)
        parts["bol_mode"] = (F.binary_cross_entropy_with_logits(out["bol_mode"][..., 0][m], bmode[m])
                             if m.any() else ice.new_zeros(()))
        m = (bmode == 0) & torch.isfinite(blr)
        parts["bol_r"] = mdn_nll(out["bol_r"], torch.where(m, blr, torch.zeros_like(blr)), self.K_EV)[m].mean() if m.any() else ice.new_zeros(())
        m = (bmode == 1) & torch.isfinite(blu)
        parts["bol_u"] = mdn_nll(out["bol_u"], torch.where(m, blu, torch.zeros_like(blu)), self.K_EV)[m].mean() if m.any() else ice.new_zeros(())
        return sum(parts.values()), parts

    @torch.no_grad()
    def sample(self, out):
        """One draw per batch element from the LAST time step. Returns a dict of floats/tensors."""
        o = {k: v[:, -1] for k, v in out.items()}
        s = dict(ice=mdn_sample(o["ice"], self.K_ICE))
        s["carb"] = torch.rand_like(s["ice"]) < torch.sigmoid(o["carb_p"][:, 0])
        s["carb_g"] = mdn_sample(o["carb_g"], self.K_EV).exp().clamp(1, 250)
        mu, ls = o["carb_abs"].unbind(-1)
        s["carb_abs_h"] = (mu + ls.clamp(-5, 3).exp() * torch.randn_like(mu)).exp().clamp(0.5, 8)
        s["bolus"] = torch.rand_like(s["ice"]) < torch.sigmoid(o["bol_p"][:, 0])
        s["override"] = torch.rand_like(s["ice"]) < torch.sigmoid(o["bol_mode"][:, 0])
        s["ratio"] = mdn_sample(o["bol_r"], self.K_EV).exp().clamp(0, 5)
        s["units"] = mdn_sample(o["bol_u"], self.K_EV).exp().clamp(0.05, 30)
        return s
