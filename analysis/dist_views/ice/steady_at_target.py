#!/usr/bin/env python3
"""Steady-state absorbed rate evaluated AT each person's own target: per person,
regress log(absorbed / scheduled) on (window glucose - target) across steady
windows (70-250 band), read the intercept. Also by 6-h block."""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from steady_basal import windows, BLOCKS  # noqa


def fit(w, tgt):
    if len(w) < 20 or w.bg.std() < 3:
        return np.nan, np.nan
    x = w.bg.to_numpy() - tgt
    b, a = np.polyfit(x, np.log(w.r.to_numpy()), 1)
    return np.exp(a), b * 10


def f(a):
    p = S.load(a)
    tgt = float(np.nanmedian(p["target_lo"]))
    w = windows(p, hours=3, flat=10, band=(70, 250))
    w = w[(w.sched_uhr > 0) & (w.abs_uhr > 0)].copy()
    w["r"] = w.abs_uhr / w.sched_uhr
    out = {"alias": a, "target": tgt, "n": len(w), "sched": np.nanmedian(p["basal_sched"])}
    out["ratio_at_target"], out["slope10"] = fit(w, tgt)
    for lo, hi, lab in BLOCKS:
        out[f"rt_{lab}"], _ = fit(w[(w.tod >= lo) & (w.tod < hi)], tgt)
    return out


if __name__ == "__main__":
    with Pool(8) as p:
        d = pd.DataFrame(p.map(f, list(S.cohort().alias)))
    d = d.merge(S.cohort()[["alias", "strategy", "tir", "t70", "carb_g_day"]], on="alias")
    d.to_csv(S.OUT / "ice" / "steady_at_target.csv", index=False)
    r = d.ratio_at_target.dropna()
    print(f"target median {d.target.median():.0f}; people {len(r)}")
    print(f"steady-state at target / scheduled: median {r.median():.2f}, p10-p90 "
          f"{r.quantile(.1):.2f}-{r.quantile(.9):.2f}; within +-15%: {r.between(.85, 1.15).mean():.0%}; "
          f">1.15: {(r > 1.15).mean():.0%}; <0.85: {(r < 0.85).mean():.0%}")
    print("by block:", {lab: (round(d[f'rt_{lab}'].median(), 2), int(d[f'rt_{lab}'].count())) for _, _, lab in BLOCKS})
    print(d.groupby("strategy").ratio_at_target.median().round(2).to_dict())
    from scipy.stats import spearmanr
    for c in ["tir", "t70", "carb_g_day"]:
        rho, pv = spearmanr(d.ratio_at_target, d[c], nan_policy="omit")
        print(f"rho(ratio, {c}) {rho:.2f} p={pv:.3f}")
