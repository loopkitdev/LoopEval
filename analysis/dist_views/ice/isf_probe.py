#!/usr/bin/env python3
"""Why does the fasting regression give an ISF about half the schedule's?

Compare estimators of the ISF implied by fasting data, per person:
  ols30     block glucose change on units absorbed, 30-min blocks
  ols60     same, 60-min blocks
  mom60     60-min blocks, previous block's change as a control (momentum that
            the controller was responding to)
  lag60     units absorbed from delivery made at least 60 min before the block
            began — insulin that cannot be a reply to this block's trend
"""
from __future__ import annotations
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import style as S  # noqa
from ice_first import _quiet_mask  # noqa
from loopeval_analysis import dists as D  # noqa


def blocks(x, b):
    n = len(x) // b * b
    return x[:n].reshape(-1, b)


def fit(dv, cols):
    X = np.column_stack([np.ones(len(dv))] + cols)
    beta, *_ = np.linalg.lstsq(X, dv, rcond=None)
    return beta


def person(alias):
    p = S.load(alias)
    p = p[p.index >= p.index[0]]
    quiet = _quiet_mask(p)
    isf = p["isf"].to_numpy()
    u = p["ia_abs"].to_numpy() / isf
    v = p["v"].to_numpy()
    out = {"alias": alias, "isf_sched": np.nanmedian(isf)}
    for b, name in ((6, "30"), (12, "60")):
        m = blocks(quiet, b).all(1)
        dv = blocks(v, b).sum(1)
        du = blocks(u, b).sum(1)
        mm = m.copy()
        if mm.sum() < 150:
            continue
        out["ols" + name] = -fit(dv[mm], [du[mm]])[1]
        prev = np.r_[np.nan, dv[:-1]]
        mp = mm & np.r_[False, m[:-1]] & ~np.isnan(prev)
        if mp.sum() > 150:
            bt = fit(dv[mp], [du[mp], prev[mp]])
            out["mom" + name] = -bt[1]
            out["rho" + name] = bt[2]
    # lagged-delivery instrument: activity from doses >= 60 min before block start
    # approximate by the activity kernel's tail: rebuild from delivered units
    act_k = D._activity_kernel(D.INSULIN_MODELS.get(str(p.attrs.get("insulin", "")).lower(),
                                                    D.RAPID_ACTING_ADULT), 80)
    delivered = p["basal_eff"].to_numpy() / 12 + p["bolus_u"].fillna(0).to_numpy()
    lagk = act_k.copy(); lagk[:12] = 0                     # only units >= 60 min old
    u_lag = D._convolve(np.nan_to_num(delivered), lagk)
    b = 12
    m = blocks(quiet, b).all(1)
    dv = blocks(v, b).sum(1); du = blocks(u, b).sum(1); dz = blocks(u_lag, b).sum(1)
    # 2SLS: first stage du ~ dz, second dv ~ du_hat
    if m.sum() > 150:
        g = fit(du[m], [dz[m]])
        du_hat = g[0] + g[1] * dz[m]
        out["iv60"] = -fit(dv[m], [du_hat])[1]
        out["iv_first_r"] = np.corrcoef(du[m], dz[m])[0, 1]
    return out


if __name__ == "__main__":
    co = S.cohort()
    with Pool(8) as pool:
        rows = pool.map(person, list(co.alias))
    d = pd.DataFrame(rows)
    d.to_csv(S.OUT / "ice" / "isf_probe.csv", index=False)
    for c in ["ols30", "ols60", "mom60", "iv60"]:
        r = d[c] / d.isf_sched
        print(f"{c:6s} ratio to schedule: median {r.median():.2f}  p10-p90 {r.quantile(.1):.2f}-{r.quantile(.9):.2f}  n={r.notna().sum()}")
    print("momentum coef rho60 median", d.rho60.median().round(2), " iv first-stage r median", d.iv_first_r.median().round(2))
