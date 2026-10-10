#!/usr/bin/env python3
"""Option 3: the fasting regression (C) shrunk toward the TDD rule (B).

Everything in log ISF.
  c, se     C and the standard error of log C (OLS slope SE / slope), per half
            and for the whole record. The OLS SE ignores autocorrelation between
            fasting hours, so it is CALIBRATED against the halves: the observed
            variance of log(C_h1/C_h2) across people is compared with the mean
            of se_h1^2 + se_h2^2, and every SE is multiplied by the square root
            of that ratio.
  prior     log B + offset, offset = the cohort median of log(C/B) — the TDD rule
            moved to C's level.
  tau^2     between-person variance of C around that prior, net of noise:
            var(log C_all - prior_all) - mean(se_all^2), whole record.
  shrunk    prior + w (c - prior), w = tau^2 / (tau^2 + se^2)
  E         exp(shrunk) * L, with one cohort-wide L putting E's whole-record
            median on the scheduled median (it moves no ranking and no ratio).
Hyperparameters (offset, tau^2, SE calibration, L) are fitted once, on the
cohort; then E is computed for each half and the whole record.

Output: ice/isf_shrink.csv
"""
from __future__ import annotations
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
np.seterr(all="ignore")  # macOS Accelerate matmul emits spurious FP warnings
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_first import _quiet_mask  # noqa

MIN_BLOCKS = 100


def fit(p, quiet, sel):
    u = p["ia_abs"].to_numpy() / p["isf"].to_numpy()
    v = p["v"].to_numpy()
    n = len(p) // 12 * 12
    m = (quiet & sel)[:n].reshape(-1, 12).all(1)
    dv = v[:n].reshape(-1, 12).sum(1)[m]
    du = u[:n].reshape(-1, 12).sum(1)[m]
    if len(dv) < MIN_BLOCKS or np.std(du) == 0:
        return np.nan, np.nan, len(dv)
    X = np.column_stack([np.ones_like(du), du])
    beta, res, *_ = np.linalg.lstsq(X, dv, rcond=None)
    resid = dv - X @ beta
    s2 = resid @ resid / (len(dv) - 2)
    se_slope = np.sqrt(s2 * np.linalg.inv(X.T @ X)[1, 1])
    slope = -beta[1]
    if slope <= 0:
        return slope, np.nan, len(dv)
    return slope, se_slope / slope, len(dv)


def person(alias):
    p = S.load(alias)
    p = p[p["bg"].notna() | p["v"].notna()]
    quiet = _quiet_mask(p)
    week = ((p.index - p.index[0]).days // 7).to_numpy()
    out = {"alias": alias}
    for name, sel in (("all", np.ones(len(p), bool)), ("h1", week % 2 == 0), ("h2", week % 2 == 1)):
        out[f"C_{name}"], out[f"se_{name}"], out[f"nblk_{name}"] = fit(p, quiet, sel)
    return out


if __name__ == "__main__":
    co = S.cohort()
    with Pool(8) as pool:
        d = pd.DataFrame(pool.map(person, list(co.alias)))
    sp = pd.read_csv(S.OUT / "ice" / "isf_split.csv")[["alias", "A_all", "B_all", "B_h1", "B_h2"]]
    d = d.merge(sp, on="alias")

    # SE calibration against the halves
    h = d.dropna(subset=["se_h1", "se_h2"])
    obs = np.var(np.log(h.C_h1 / h.C_h2))
    pred = np.mean(h.se_h1 ** 2 + h.se_h2 ** 2)
    k = np.sqrt(obs / pred)
    for c in ("se_all", "se_h1", "se_h2"):
        d[c] *= k
    a = d.dropna(subset=["se_all"])
    offset = np.median(np.log(a.C_all / a.B_all))
    resid = np.log(a.C_all) - (np.log(a.B_all) + offset)
    tau2 = max(np.var(resid) - np.mean(a.se_all ** 2), 1e-6)
    for name in ("all", "h1", "h2"):
        prior = np.log(d[f"B_{name}"]) + offset
        c = np.log(d[f"C_{name}"].where(d[f"C_{name}"] > 0))
        w = tau2 / (tau2 + d[f"se_{name}"] ** 2)
        # no usable fit -> fall back to the prior (w = 0)
        w = w.where(c.notna(), 0.0)
        d[f"w_{name}"] = w
        d[f"lE_{name}"] = prior + w * (c.fillna(prior) - prior)
    L = np.nanmedian(d.A_all) / np.nanmedian(np.exp(d.lE_all))
    for name in ("all", "h1", "h2"):
        d[f"E_{name}"] = np.exp(d[f"lE_{name}"]) * L
    d.to_csv(S.OUT / "ice" / "isf_shrink.csv", index=False)
    print(f"SE calibration factor {k:.2f} (observed half-difference variance {obs:.3f} vs OLS-predicted {pred:.3f})")
    print(f"offset log(C/B) {offset:.3f} (C = {np.exp(offset):.2f} x B);  tau {np.sqrt(tau2):.3f} "
          f"(between-person SD of C beyond the TDD rule, log);  median se_all {a.se_all.median():.3f}, "
          f"se_half {np.nanmedian(np.r_[d.se_h1, d.se_h2]):.3f}")
    print(f"weight on own data: whole record median {d.w_all.median():.2f} (p10-p90 "
          f"{d.w_all.quantile(.1):.2f}-{d.w_all.quantile(.9):.2f}); per half median "
          f"{np.nanmedian(np.r_[d.w_h1, d.w_h2]):.2f};  level factor L {L:.2f}")
