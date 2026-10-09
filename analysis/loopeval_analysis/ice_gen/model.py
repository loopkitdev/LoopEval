"""v1 generator: a GRU over the 5-min grid with a per-person profile vector, emitting a mixture
of Gaussians over the next slot's (scaled) ICE.

  input_t = [features_t, profile(person)]  ->  GRU (state carries the history)  ->  MDN(K)
Sampling feeds each draw back in as the next step's ICE feature, so a rollout conditions on its
own past ICE plus whatever BG / insulin the surrounding loop supplies.
"""
from __future__ import annotations

import math
import torch
import torch.nn as nn


class ICEGen(nn.Module):
    def __init__(self, n_features: int, n_people: int, profile_dim=16, hidden=256, layers=2, k=8):
        super().__init__()
        self.profile = nn.Embedding(n_people, profile_dim)
        nn.init.normal_(self.profile.weight, std=0.1)
        self.inp = nn.Linear(n_features + profile_dim, hidden)
        self.gru = nn.GRU(hidden, hidden, num_layers=layers, batch_first=True)
        self.head = nn.Linear(hidden, 3 * k)
        self.k = k

    def forward(self, x, person, h=None):
        """x [B, T, F], person [B] -> (logits, mu, log_sigma) each [B, T, K], new state."""
        p = self.profile(person)[:, None, :].expand(-1, x.shape[1], -1)
        z, h = self.gru(torch.relu(self.inp(torch.cat([x, p], -1))), h)
        logit, mu, ls = self.head(z).split(self.k, -1)
        return logit, mu, ls.clamp(-5, 3), h

    @staticmethod
    def nll(logit, mu, ls, y):
        """Mean negative log-likelihood over finite targets (scaled units)."""
        m = torch.isfinite(y)
        y0 = torch.where(m, y, torch.zeros_like(y))[..., None]
        lp = (torch.log_softmax(logit, -1) - 0.5 * ((y0 - mu) / ls.exp()) ** 2 - ls
              - 0.5 * math.log(2 * math.pi))
        return -(torch.logsumexp(lp, -1)[m]).mean()

    @staticmethod
    def sample(logit, mu, ls):
        comp = torch.distributions.Categorical(logits=logit).sample()[..., None]
        return (mu.gather(-1, comp) + ls.gather(-1, comp).exp() * torch.randn_like(comp, dtype=mu.dtype))[..., 0]
