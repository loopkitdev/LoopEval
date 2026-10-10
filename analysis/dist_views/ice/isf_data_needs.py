#!/usr/bin/env python3
"""How much data the ISF yardstick needs: repeatability against record length.

For N in DAYS, each person's record gives two NON-overlapping N-day stretches
(days [0, N) and [N, 2N)). The yardstick is computed on each alone, with the
cohort-wide settings fixed at their whole-cohort values (basal rule K, b; slope
offset; tau; SE calibration; level factor L) — i.e. what a new person with N
days of data would get. Reported: the median and p90 difference between the two
stretches, the weight the person's own slope receives, and how far an N-day
estimate sits from the person's full-record yardstick (overlapping, so only a
guide).

Output: ice/isf_data_needs.csv
"""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
np.seterr(all="ignore")
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_first import _quiet_mask  # noqa
from isf_shrink import fit  # noqa
from ice_raw import excluded_on_grid  # noqa

DAYS = (3, 7, 14, 21, 30, 45, 57)
H = 12
bp = pd.read_csv(S.OUT / "ice" / "isf_basal_prior.csv")
ok = bp.fb_all > 0
b_, a_ = np.polyfit(np.log(bp.fb_all[ok]), np.log(bp.A_all[ok]), 1)
K, BEXP = np.exp(a_), b_
OFF = np.nanmedian(np.log(bp.C_all / (K * bp.fb_all ** BEXP)).where(bp.C_all > 0))
CAL, TAU = 1.342, 0.366          # from the screened isf_basal_prior run
L = np.nanmedian(bp.A_all) / np.nanmedian(bp.E_basal_all / 1.0) * 1.0
L = 2.005
FULL = pd.read_csv(S.OUT / "ice" / "isf_estimate.csv").set_index("alias").isf_est


def yard(p, q, sel):
    c, se, n = fit(p, q, sel)
    u = p["ia_abs"].to_numpy() / p["isf"].to_numpy() * H
    m = q & sel & np.isfinite(u)
    if m.sum() < 100:
        return np.nan, np.nan
    prior = np.log(K * np.median(u[m]) ** BEXP) + OFF
    if not (np.isfinite(c) and c > 0 and np.isfinite(se)):
        return float(np.exp(prior) * L), 0.0
    se *= CAL
    w = TAU ** 2 / (TAU ** 2 + se ** 2)
    return float(np.exp(prior + w * (np.log(c) - prior)) * L), float(w)


def person(alias):
    p = S.load(alias)
    p = p[p["bg"].notna() | p["v"].notna()]
    q = _quiet_mask(p) & ~excluded_on_grid(alias, p.index)
    day = ((p.index - p.index[0]).total_seconds() // 86400).to_numpy()
    rows = []
    for N in DAYS:
        if day.max() + 1 < 2 * N:
            continue
        e1, w1 = yard(p, q, day < N)
        e2, w2 = yard(p, q, (day >= N) & (day < 2 * N))
        rows.append({"alias": alias, "N": N, "e1": e1, "e2": e2, "w1": w1, "w2": w2})
    return rows


if __name__ == "__main__":
    al = list(FULL.dropna().index)
    S.datasets()
    with Pool(8) as pl:
        d = pd.DataFrame([r for rows in pl.map(person, al) for r in rows])
    d.to_csv(S.OUT / "ice" / "isf_data_needs.csv", index=False)
    d["gap"] = np.abs(np.log(d.e2 / d.e1))
    d["off_full"] = np.abs(np.log(d.e1 / d.alias.map(FULL)))
    pct = lambda x: 100 * (np.exp(x) - 1)
    out = d.dropna(subset=["gap"]).groupby("N").agg(
        people=("alias", "size"), gap_med=("gap", "median"), gap_p90=("gap", lambda x: x.quantile(.9)),
        over25=("gap", lambda x: (x > np.log(1.25)).mean()), weight_own=("w1", "median"),
        off_full=("off_full", "median"))
    for c in ("gap_med", "gap_p90", "off_full"):
        out[c] = pct(out[c])
    print(f"basal rule ISF = {K:.0f} / fb^{-BEXP:.2f}; offset {np.exp(OFF):.3f}; tau {TAU}; level x{L}")
    print(out.round(2).to_string())
