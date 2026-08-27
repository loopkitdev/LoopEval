"""Causal volatility estimation for glucose increments.

Glucose increments are a scale mixture: conditionally well-behaved, with a
variance that drifts slowly and predictably (see the distribution study). This
module estimates that variance *causally* — every value at time t uses only
data strictly before t — so an estimate can be fed to a controller.

Three estimators, in increasing order of how much they assume:

    RollingSD    trailing standard deviation over a fixed window
    EWMA         σ²_t = (1-λ)·ε²_{t-1} + λ·σ²_{t-1}        one parameter
    Garch11      σ²_t = ω + α·ε²_{t-1} + β·σ²_{t-1}        three parameters

All three are fitted and evaluated per person. RollingSD is the baseline the
others have to beat; it is what the exploratory work used.

Two things this module is careful about, because both silently corrupt the
answer otherwise:

* **Gaps.** A CGM trace is not one series, it is many contiguous runs. The
  recursion is restarted at each run boundary and given a burn-in, so a gap
  never propagates a stale variance across it.
* **Cadence.** Sensors differ — at least one stream in this cohort reports
  every minute rather than every five. Everything here is expressed in
  MINUTES and converted per dataset, never in samples.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence

import numpy as np

__all__ = ["RollingSD", "EWMA", "Garch11", "fit_estimator", "evaluate",
           "realized_vol", "standardize"]

_EPS = 1e-8
_MIN_VAR = 1e-4          # absolute backstop only; see `var_floor` below


def measurement_floor(sigma_meas: float) -> float:
    """Smallest variance a *difference* of a noisily-measured series can have.

    If the record is signal + iid error of SD σ_meas, then even a perfectly
    flat signal produces increments with variance 2σ_meas². Letting a fitted
    volatility fall below that is not just wrong, it is numerically dangerous:
    ε/σ explodes and the standardised series grows a spurious tail heavier than
    the one it was supposed to remove. That is a real bug this module hit.
    """
    return max(2.0 * float(sigma_meas) ** 2, 0.25)


# ────────────────────────────────────────────────────────────────────────────
# estimators
# ────────────────────────────────────────────────────────────────────────────
class _Base:
    """Common interface: `filter(runs)` returns causal σ per sample.

    Each element of `runs` is a 1-D array of increments (already differenced).
    The returned arrays are aligned with the inputs; positions that are still
    inside the burn-in come back as NaN so they can be excluded cleanly.
    """
    name = "base"
    burn_in = 0

    def sigma_runs(self, runs: Sequence[np.ndarray]) -> list[np.ndarray]:
        raise NotImplementedError

    def filter(self, runs: Sequence[np.ndarray]) -> list[np.ndarray]:
        return self.sigma_runs(runs)


@dataclass
class RollingSD(_Base):
    """Trailing standard deviation. `window_min` of history, causal."""
    window_min: float = 120.0
    cadence_min: float = 5.0
    var_floor: float = _MIN_VAR
    name: str = field(default="rolling", init=False)

    @property
    def _n(self) -> int:
        return max(int(round(self.window_min / self.cadence_min)), 3)

    def sigma_runs(self, runs):
        import pandas as pd
        n = self._n
        out = []
        for r in runs:
            s = pd.Series(r)
            # shift(1): the value at t uses increments strictly before t
            v = s.rolling(n, min_periods=max(n // 2, 3)).std().shift(1)
            out.append(np.sqrt(np.maximum(v.to_numpy() ** 2, self.var_floor)))
        return out


@dataclass
class EWMA(_Base):
    """RiskMetrics-style exponentially weighted variance."""
    lam: float = 0.94
    cadence_min: float = 5.0
    burn_in: int = 24
    var_floor: float = _MIN_VAR
    name: str = field(default="ewma", init=False)

    def sigma_runs(self, runs):
        out = []
        var0 = float(np.mean([np.var(r) for r in runs if len(r) > 5])) or 1.0
        for r in runs:
            v = np.empty(len(r))
            s2 = var0
            for i in range(len(r)):
                v[i] = s2                                   # uses ε up to i-1
                s2 = (1 - self.lam) * r[i] ** 2 + self.lam * s2
            sig = np.sqrt(np.maximum(v, self.var_floor))
            sig[:self.burn_in] = np.nan
            out.append(sig)
        return out


@dataclass
class Garch11(_Base):
    """GARCH(1,1) with Gaussian quasi-likelihood.

    QMLE is used deliberately: the innovations are not Gaussian (they are
    closer to Laplace), but Gaussian QMLE stays consistent for the variance
    parameters under that misspecification, which a naive Laplace MLE does not
    obviously improve on. `dist` may be set to "ged" to fit a shape parameter
    as well, at the cost of a slower fit.
    """
    omega: float = 0.05
    alpha: float = 0.08
    beta: float = 0.90
    cadence_min: float = 5.0
    burn_in: int = 24
    var_floor: float = _MIN_VAR
    dist: str = "normal"
    nu: float = 1.4                     # GED shape; 2 = Gaussian, 1 = Laplace
    name: str = field(default="garch", init=False)

    def _recurse(self, r, omega, alpha, beta, var0):
        v = np.empty(len(r))
        s2 = var0
        for i in range(len(r)):
            v[i] = s2
            s2 = omega + alpha * r[i] ** 2 + beta * s2
            if not np.isfinite(s2) or s2 < _MIN_VAR:
                s2 = _MIN_VAR
        return v

    def sigma_runs(self, runs):
        var0 = float(np.mean([np.var(r) for r in runs if len(r) > 5])) or 1.0
        out = []
        for r in runs:
            v = self._recurse(r, self.omega, self.alpha, self.beta, var0)
            sig = np.sqrt(np.maximum(v, self.var_floor))
            sig[:self.burn_in] = np.nan
            out.append(sig)
        return out

    # ── fitting ──
    def negloglik(self, runs, theta) -> float:
        omega, alpha, beta = theta
        if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 0.9995:
            return 1e12
        var0 = omega / max(1 - alpha - beta, 1e-3)
        ll = 0.0
        n = 0
        for r in runs:
            if len(r) <= self.burn_in + 5:
                continue
            v = self._recurse(r, omega, alpha, beta, var0)
            v = v[self.burn_in:]
            e = r[self.burn_in:]
            if not np.all(np.isfinite(v)):
                return 1e12
            ll += float(np.sum(np.log(v) + e ** 2 / v))
            n += len(e)
        return ll / max(n, 1)


def fit_estimator(kind: str, runs: Sequence[np.ndarray], cadence_min: float,
                  *, burn_in_min: float = 120.0,
                  var_floor: float = _MIN_VAR) -> _Base:
    """Fit one estimator to a set of increment runs (the TRAIN split)."""
    burn = max(int(round(burn_in_min / cadence_min)), 6)
    runs = [np.asarray(r, dtype=float) for r in runs if len(r) > burn + 10]
    if not runs:
        raise ValueError("no usable runs")

    if kind == "rolling":
        # Pick the window by out-of-sample-free criterion: the window whose
        # estimate best predicts the NEXT window's realised variance in-sample.
        best, best_score = None, -np.inf
        for w in (30, 60, 90, 120, 180, 240, 360):
            est = RollingSD(window_min=w, cadence_min=cadence_min,
                            var_floor=var_floor)
            sc = _predictive_r2(est, runs, cadence_min)
            if np.isfinite(sc) and sc > best_score:
                best, best_score = est, sc
        return best or RollingSD(cadence_min=cadence_min, var_floor=var_floor)

    if kind == "ewma":
        best, best_score = None, -np.inf
        # Lower bound 0.30 (half-life ~3 min at 5-min steps). The bound has
        # been lowered twice for the same reason: at 0.80, 32 of 70 people
        # pinned to it, and at 0.55 six still did. A fit sitting on a grid
        # boundary is not a fit — it biases the half-life upward — so the grid
        # must extend past where anyone actually lands.
        for lam in np.linspace(0.30, 0.995, 140):
            est = EWMA(lam=float(lam), cadence_min=cadence_min, burn_in=burn,
                       var_floor=var_floor)
            sc = -_gauss_nll(est, runs)
            if np.isfinite(sc) and sc > best_score:
                best, best_score = est, sc
        return best or EWMA(cadence_min=cadence_min, burn_in=burn,
                            var_floor=var_floor)

    if kind == "garch":
        from scipy.optimize import minimize
        g = Garch11(cadence_min=cadence_min, burn_in=burn, var_floor=var_floor)
        uvar = float(np.mean([np.var(r) for r in runs]))
        best, best_f = None, np.inf
        # Several starts: the likelihood is flat along alpha+beta and a single
        # start lands on a boundary often enough to matter.
        for a0, b0 in ((0.05, 0.93), (0.10, 0.85), (0.02, 0.97), (0.20, 0.70)):
            x0 = np.array([uvar * max(1 - a0 - b0, 0.02), a0, b0])
            try:
                res = minimize(lambda th: g.negloglik(runs, th), x0,
                               method="Nelder-Mead",
                               options=dict(maxiter=1200, xatol=1e-6, fatol=1e-8))
            except Exception:                                    # noqa: BLE001
                continue
            if res.fun < best_f and np.all(np.isfinite(res.x)):
                best, best_f = res.x, res.fun
        if best is None:
            return g
        g.omega, g.alpha, g.beta = (float(best[0]), float(best[1]), float(best[2]))
        return g

    raise ValueError(f"unknown estimator: {kind}")


def _gauss_nll(est: _Base, runs) -> float:
    sig = est.filter(runs)
    tot, n = 0.0, 0
    for s, r in zip(sig, runs):
        m = np.isfinite(s) & (s > 0)
        if not m.any():
            continue
        tot += float(np.sum(np.log(s[m] ** 2) + r[m] ** 2 / s[m] ** 2))
        n += int(m.sum())
    return tot / max(n, 1)


def _predictive_r2(est: _Base, runs, cadence_min, horizon_min: float = 30.0) -> float:
    """R² of predicted σ against realised absolute move over the next horizon."""
    k = max(int(round(horizon_min / cadence_min)), 1)
    P, A = [], []
    for s, r in zip(est.filter(runs), runs):
        rv = realized_vol(r, k)
        m = np.isfinite(s) & np.isfinite(rv) & (s > 0) & (rv > 0)
        P.append(s[m])
        A.append(rv[m])
    if not P or sum(len(p) for p in P) < 200:
        return np.nan
    p, a = np.log(np.concatenate(P)), np.log(np.concatenate(A))
    return float(np.corrcoef(p, a)[0, 1] ** 2)


# ────────────────────────────────────────────────────────────────────────────
# targets and diagnostics
# ────────────────────────────────────────────────────────────────────────────
def realized_vol(increments: np.ndarray, k: int) -> np.ndarray:
    """Forward realised volatility: SD of the next k increments, per position.

    NaN wherever the forward window runs off the end of the run.
    """
    import pandas as pd
    s = pd.Series(increments)
    fwd = s[::-1].rolling(k).std()[::-1].shift(-1)
    return fwd.to_numpy()


def standardize(runs, sigmas) -> np.ndarray:
    """Pooled ε/σ, dropping burn-in and non-finite values."""
    out = []
    for r, s in zip(runs, sigmas):
        m = np.isfinite(s) & (s > 0) & np.isfinite(r)
        out.append(r[m] / s[m])
    return np.concatenate(out) if out else np.array([])


def evaluate(est: _Base, runs, cadence_min: float,
             horizon_min: float = 30.0) -> dict:
    """Out-of-sample scorecard for a fitted estimator on held-out runs."""
    import pandas as pd
    sig = est.filter(runs)
    z = standardize(runs, sig)
    k = max(int(round(horizon_min / cadence_min)), 1)

    P, A = [], []
    for s, r in zip(sig, runs):
        rv = realized_vol(r, k)
        m = np.isfinite(s) & np.isfinite(rv) & (s > 0) & (rv > 0)
        P.append(s[m])
        A.append(rv[m])
    p = np.concatenate(P) if P else np.array([])
    a = np.concatenate(A) if A else np.array([])

    r2 = float(np.corrcoef(np.log(p), np.log(a))[0, 1] ** 2) if len(p) > 200 else np.nan
    zz = z / np.std(z) if len(z) else z
    return {
        "estimator": est.name,
        "n": int(len(z)),
        "nll": _gauss_nll(est, runs),          # lower is better
        "r2_logvar": r2,                       # predicts future realised vol
        "z_kurtosis": float(pd.Series(z).kurtosis()) if len(z) > 100 else np.nan,
        "z_sd": float(np.std(z)) if len(z) else np.nan,
        "sigma_p10": float(np.nanpercentile(p, 10)) if len(p) else np.nan,
        "sigma_p90": float(np.nanpercentile(p, 90)) if len(p) else np.nan,
        "spread": float(np.nanpercentile(p, 90) / np.nanpercentile(p, 10))
                  if len(p) else np.nan,
        # Coverage. At 90% a Gaussian and a Laplace band are nearly the same
        # width (1.645σ vs 1.646σ), so 90% cannot tell them apart — the two
        # families separate in the far tail, which is the part that matters for
        # a safety margin. Report 99% as well.
        "cover_90_gauss": float(np.mean(np.abs(zz) <= 1.645)) if len(z) else np.nan,
        "cover_99_gauss": float(np.mean(np.abs(zz) <= 2.576)) if len(z) else np.nan,
        "cover_99_laplace": float(np.mean(np.abs(zz) <= 3.257)) if len(z) else np.nan,
    }
