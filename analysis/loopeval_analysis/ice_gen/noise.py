"""Level noise: the fast part of real ICE that the generator leaves out, added to the plant's glucose.

Real ICE carries a fast component that reverts in glucose LEVEL within ~1-2 h: the cumulative ICE path
X(t) = integral of ICE dt (= CGM + ISF x insulin absorbed so far) of the real data has more variance
than the generator's at lags up to ~1 h and the same at longer lags. Whatever it is physically
(sensor wander, insulin-timing mismatch, real short swings), a CGM reports it and Loop doses on it.

The plant adds it as a stationary AR(2) process e on the reported glucose: CGM = BG + e. The reported
ICE then gains (e_t - e_{t-1}) / dt, and glucose never random-walks from it.

Fitted from the difference between real and generated structure functions on a window the generator
is NOT judged on: D(L) = V_real(L) - V_gen(L) = 2 (gamma_e(0) - gamma_e(L)). One AR(2) shape for the
pool (the decay and the overshoot), one scale per person.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LAGS = np.array([1, 2, 3, 4, 6, 9, 12, 18, 24, 36, 48])     # 5-min steps (5 min .. 4 h)
SHAPE_MAX = 12                                              # shape fitted on lags <= 60 min
SCALE_MAX = 6                                               # per-person scale on lags <= 30 min


def structure(g: pd.DataFrame, lags=LAGS) -> np.ndarray:
    """Var[X(t+L) - X(t)] (mg/dL^2) of the cumulative ICE path on a clean 5-min grid (stats.grid5)."""
    x = g.ice.to_numpy() * 5 / 60
    ok = np.isfinite(x)
    X = np.where(ok, x, 0).cumsum(); bad = (~ok).cumsum()
    out = []
    for k in lags:
        d = X[k:] - X[:-k]; valid = (bad[k:] - bad[:-k]) == 0
        out.append(np.var(d[valid]) if valid.sum() > 500 else np.nan)
    return np.array(out)


def ar2_rho(a1, a2, n):
    rho = np.empty(n + 1); rho[0] = 1.0; rho[1] = a1 / (1 - a2)
    for k in range(2, n + 1):
        rho[k] = a1 * rho[k - 1] + a2 * rho[k - 2]
    return rho


def ar2_gamma0(a1, a2, sw2):
    return sw2 * (1 - a2) / ((1 + a2) * ((1 - a2) ** 2 - a1 ** 2))


def stationary(a1, a2):
    return abs(a2) < 1 and a2 + a1 < 1 and a2 - a1 < 1


def shape(a1, a2, lags=LAGS):
    """D(L) per unit stationary variance: 2 (1 - rho(L))."""
    return 2 * (1 - ar2_rho(a1, a2, int(max(lags)))[lags])


def fit_shape(D: np.ndarray, lags=LAGS):
    """Pooled AR(2) coefficients from a pooled D(L) curve (relative least squares on lags <= SHAPE_MAX)."""
    m = (lags <= SHAPE_MAX) & np.isfinite(D) & (D > 0)
    best = (np.inf, None)
    for a1 in np.linspace(0.0, 1.99, 200):
        for a2 in np.linspace(-0.99, 0.99, 199):
            if not stationary(a1, a2):
                continue
            f = shape(a1, a2, lags)[m]
            v = np.sum(f * D[m] / D[m] ** 2) / np.sum(f ** 2 / D[m] ** 2)       # best scale, relative LS
            r = np.sum(((v * f - D[m]) / D[m]) ** 2)
            if r < best[0]:
                best = (r, (float(a1), float(a2)))
    return best[1]


def fit_scale(D: np.ndarray, a1, a2, lags=LAGS) -> float:
    """Per-person stationary variance of e (mg/dL^2), least squares on lags <= SCALE_MAX, floored at 0."""
    m = (lags <= SCALE_MAX) & np.isfinite(D)
    f = shape(a1, a2, lags)[m]
    return float(max(np.sum(f * D[m]) / np.sum(f ** 2), 0.0))


class LevelNoise:
    """AR(2) on 5-min steps, started from its stationary distribution."""

    def __init__(self, a1, a2, var, seed=0):
        self.a1, self.a2 = a1, a2
        g0 = ar2_gamma0(a1, a2, 1.0)
        self.sw = float(np.sqrt(var / g0)) if var > 0 else 0.0
        self.rng = np.random.default_rng(seed + 7919)
        self.e1 = self.e2 = 0.0
        for _ in range(500):
            self.step()

    def step(self) -> float:
        e = self.a1 * self.e1 + self.a2 * self.e2 + self.sw * self.rng.standard_normal()
        self.e2, self.e1 = self.e1, e
        return e
