"""Slow level: the persistent part of a person's background ICE that no input explains.

Real daily background-ICE levels vary within a person about as much as between people (sd ~11 mg/dL/h),
and that variation persists: covariance of daily means 58 (mg/dL/h)^2 at 1 day, still ~8 at 2 weeks. The
record (site age, the previous day's lows and highs, weekends) explains ~1% of it (runs/2026-10-11-ice-slow).
The v3 generator's days are independent (1-day correlation 0.05 vs real 0.25 over the same 28-day windows),
so the plant adds it: u(t) = fast OU + slow OU on background ICE, fitted to the real covariance of daily
means (fit_slow.py: fast sd 8.4 mg/dL/h, tau ~20 h; slow sd 6.2, tau ~7.6 d). It enters the ICE, so the
generator's own background input and Loop both see a shifted day, as they do in real data.

`scale` is the per-person dial (1 = pooled fit; 0 = off; >1 = a person whose days swing more).
"""
from __future__ import annotations

import numpy as np


class SlowLevel:
    def __init__(self, fast_var, fast_tau_h, slow_var, slow_tau_h, scale=1.0, seed=0):
        self.c = [(float(fast_var) * scale ** 2, float(fast_tau_h)), (float(slow_var) * scale ** 2, float(slow_tau_h))]
        self.rng = np.random.default_rng(seed + 104729)
        self.x = [np.sqrt(v) * self.rng.standard_normal() for v, _ in self.c]     # stationary start

    def step(self, dt_h: float) -> float:
        """Advance dt_h hours (exact OU transition); returns the level in mg/dL/h."""
        for i, (v, tau) in enumerate(self.c):
            a = np.exp(-dt_h / tau)
            self.x[i] = a * self.x[i] + np.sqrt(v * (1 - a * a)) * self.rng.standard_normal()
        return float(sum(self.x))
