#!/usr/bin/env python3
"""ISF from correction boluses — the clinical definition, drop per unit.

An isolated correction: a user bolus >= 0.5 U with no carbs on board from 1 h
before to 5 h after, no other user bolus 3 h before to 5 h after, glucose
>= 140 at the bolus, no disruption and a contiguous 5 h of glucose.

Per event: glucose change over 5 h and units absorbed over the same 5 h (all
delivery, the controller's own adjustments included). Per person, regress the
change on units absorbed across events: the slope is minus the ISF the
corrections imply, the intercept is the drift that would have happened anyway.
"""
from __future__ import annotations
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa

H = 12
W = 5 * H


def person(alias):
    p = S.load(alias)
    bg = p["bg"].to_numpy(); cob = p["cob"].to_numpy()
    ub = p["manual_bolus_u"].fillna(0).to_numpy()
    isf = p["isf"].to_numpy()
    u = p["ia_abs"].to_numpy() / isf
    dis = p["disrupted"].astype(bool).to_numpy()
    t = p.index.asi8 // 10**9
    ev = []
    for i in np.flatnonzero(ub >= 0.5):
        lo, hi = i - 3 * H, i + W
        if lo < 0 or hi >= len(p) or t[hi] - t[i] != W * 300:
            continue
        if (cob[i - H:hi + 1] > 0).any() or (ub[lo:hi + 1] > 0).sum() != 1:
            continue
        if dis[i:hi + 1].any() or np.isnan(bg[i:hi + 1]).any() or bg[i] < 140:
            continue
        ev.append((ub[i], bg[i], bg[hi] - bg[i], u[i + 1:hi + 1].sum(), isf[i],
                   bg[i:hi + 1].min()))
    out = {"alias": alias, "isf_sched": np.nanmedian(isf), "n_corr": len(ev)}
    if len(ev) >= 12:
        e = np.array(ev)
        X = np.column_stack([np.ones(len(e)), e[:, 3]])
        beta, *_ = np.linalg.lstsq(X, e[:, 2], rcond=None)
        out["isf_corr"] = -beta[1]
        out["drift_5h"] = beta[0]
        out["corr_units_med"] = np.median(e[:, 0])
        out["corr_bg0_med"] = np.median(e[:, 1])
        out["corr_drop_med"] = -np.median(e[:, 2])
        # naive clinical reading: drop over 5 h per bolus unit
        out["isf_naive"] = np.median(-e[:, 2] / e[:, 0])
        out["nadir_lt70"] = np.mean(e[:, 5] < 70)
    return out


if __name__ == "__main__":
    co = S.cohort()
    with Pool(8) as pool:
        d = pd.DataFrame(pool.map(person, list(co.alias)))
    d.to_csv(S.OUT / "ice" / "isf_corrections.csv", index=False)
    print("people with >=12 isolated corrections:", d.isf_corr.notna().sum(),
          " events median", d.n_corr.median())
    k = d.dropna(subset=["isf_corr"])
    for c in ["isf_corr", "isf_naive"]:
        r = k[c] / k.isf_sched
        print(f"{c}: ratio to schedule median {r.median():.2f} p10-p90 {r.quantile(.1):.2f}-{r.quantile(.9):.2f}")
    print(k[["corr_units_med", "corr_bg0_med", "corr_drop_med", "drift_5h", "nadir_lt70"]].median().round(2))
