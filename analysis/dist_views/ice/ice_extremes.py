#!/usr/bin/env python3
"""Hunt for bad data the flags miss: the most extreme UNFLAGGED ICE.

ICE is averaged over 30-minute windows of consecutive, on-cadence, unflagged
intervals (the mean of a velocity telescopes, so this is (bg_end - bg_start)/0.5h
plus mean insulin activity). For each person: the 0.1st and 99.9th percentile
window, the single most extreme windows, and a cohort-wide list of the 40 most
extreme windows for inspection.

Output: ice/extremes_person.csv, ice/extremes_top.csv
"""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_raw import FLAGS  # noqa


def windows(alias, minutes=30):
    d = pd.read_pickle(S.OUT / "ice" / "raw" / f"{alias}.pkl")
    good = d.on_cadence & ~d[FLAGS].any(axis=1)
    cad = d.cadence.iloc[0]
    n = int(round(minutes / cad))
    # runs of consecutive good intervals
    run = (~good).cumsum()
    out = []
    for _, r in d[good].groupby(run[good]):
        if len(r) < n:
            continue
        cs_v = np.r_[0, np.cumsum((r.bg1 - r.bg0).to_numpy())]
        cs_a = np.r_[0, np.cumsum((r.ia * r.dt / 60).to_numpy())]      # mg/dL of insulin action
        cs_t = np.r_[0, np.cumsum(r.dt.to_numpy())]
        for i in range(0, len(r) - n + 1, max(n // 2, 1)):           # half-overlapping
            T = (cs_t[i + n] - cs_t[i]) / 60
            out.append((r.t0.iloc[i], (cs_v[i + n] - cs_v[i]) / T, (cs_a[i + n] - cs_a[i]) / T,
                        r.bg0.iloc[i], r.bg1.iloc[i + n - 1]))
    w = pd.DataFrame(out, columns=["t", "v", "ia", "bg_start", "bg_end"])
    w["ice"] = w.v + w.ia
    w["alias"] = alias
    return w


def person(alias):
    w = windows(alias)
    q = w.ice.quantile([0.001, 0.01, 0.5, 0.99, 0.999]).to_numpy()
    row = {"alias": alias, "n_win": len(w), "q001": q[0], "q01": q[1], "q50": q[2], "q99": q[3], "q999": q[4],
           "min": w.ice.min(), "max": w.ice.max(), "max_v": w.v.max(), "min_v": w.v.min(), "max_ia": w.ia.max()}
    top = pd.concat([w.nlargest(5, "ice"), w.nsmallest(5, "ice")])
    return row, top


if __name__ == "__main__":
    est = pd.read_csv(S.OUT / "ice" / "isf_estimate.csv").dropna(subset=["isf_est"])
    with Pool(8) as p:
        res = p.map(person, list(est.alias))
    r = pd.DataFrame([x[0] for x in res])
    r.to_csv(S.OUT / "ice" / "extremes_person.csv", index=False)
    top = pd.concat([x[1] for x in res])
    print(r[["q001", "q01", "q50", "q99", "q999", "min", "max", "max_v", "min_v", "max_ia"]]
          .describe(percentiles=[.1, .5, .9]).T[["min", "10%", "50%", "90%", "max"]].round(0).to_string())
    big = pd.concat([top.nlargest(20, "ice"), top.nsmallest(20, "ice")])
    big.to_csv(S.OUT / "ice" / "extremes_top.csv", index=False)
    pd.set_option("display.width", 200)
    print(big.round(0).to_string(index=False))
