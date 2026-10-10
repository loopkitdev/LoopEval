#!/usr/bin/env python3
"""ISF estimators, scored on alternating weeks.

Each person's record is cut into calendar weeks from its first day; odd weeks
form half 1, even weeks half 2. Every estimator is computed on each half alone.

  A  scheduled   median scheduled ISF in the half. NOTE the export carries the
                 END-OF-WINDOW schedule only, so A cannot differ between halves
                 here; its repeatability is untestable with this data.
  B  tdd_rule    ISF = K / TDD^b with K, b fitted ONCE across people on the
                 whole record (log ISF on log TDD), applied to the half's TDD.
                 TDD = delivered units per day over days with >= 240 of 288
                 bins carrying glucose and no disruption.
  C  fasting     OLS of each fasting hour's glucose change on units absorbed in
                 that hour (60-min blocks, all 12 steps fasting); ISF = -slope.
  D  meal        isolated announced meals (>= 10 g, no other entry within 4 h
                 either side, 4 h window contiguous). With CR as scheduled:
                 ISF = sum(glucose change over 4 h after the meal, above the
                 fasting drift) * CR / (grams - CR * insulin units absorbed above
                 the fasting rate). I.e. the ISF at which the meal's leftover
                 glucose rise is exactly what the uncovered grams would cause.

Output: ice/isf_split.csv (one row per person, <est>_h1 / <est>_h2 / <est>_all)
"""
from __future__ import annotations
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_first import _quiet_mask  # noqa

H = 12
MIN_BLOCKS = 100
MIN_MEALS = 8


def tdd_rule_fit():
    r = pd.read_csv(S.OUT / "isf_rules.csv").dropna(subset=["isf", "tdd_use"])
    b, a = np.polyfit(np.log(r.tdd_use), np.log(r.isf), 1)
    return np.exp(a), b


K, B_EXP = tdd_rule_fit()


def est_tdd(p, sel):
    ok = sel & p["bg"].notna().to_numpy() & ~p["disrupted"].astype(bool).to_numpy()
    u = p["basal_eff"].to_numpy() / 12 + p["bolus_u"].fillna(0).to_numpy()
    day = p.index.tz_convert(None).floor("D") if False else (p.index + pd.Timedelta(hours=p.attrs["utc_offset_h"])).floor("D")
    df = pd.DataFrame({"u": np.where(sel, u, np.nan), "ok": ok, "day": day})
    g = df[sel].groupby("day").agg(u=("u", "sum"), n=("ok", "sum"))
    g = g[g.n >= 240]
    if len(g) < 7:
        return np.nan, np.nan
    tdd = g.u.mean()
    return K * tdd ** B_EXP, tdd


def est_fasting(p, quiet, sel):
    u = p["ia_abs"].to_numpy() / p["isf"].to_numpy()
    v = p["v"].to_numpy()
    n = len(p) // 12 * 12
    m = (quiet & sel)[:n].reshape(-1, 12).all(1)
    dv = v[:n].reshape(-1, 12).sum(1)[m]
    du = u[:n].reshape(-1, 12).sum(1)[m]
    if len(dv) < MIN_BLOCKS or np.std(du) == 0:
        return np.nan
    beta = np.polyfit(du, dv, 1)
    return -beta[0]


def est_meal(p, quiet, sel):
    cob = p["cob"].to_numpy()
    jump = np.diff(cob, prepend=cob[0])
    bg = p["bg"].to_numpy()
    u = p["ia_abs"].to_numpy() / p["isf"].to_numpy()
    cr = p["cr"].to_numpy()
    v = p["v"].to_numpy()
    t = p.index.asi8 // 10**9
    q = quiet & sel & np.isfinite(v)
    if q.sum() < 500:
        return np.nan, 0
    drift = np.median(v[q])                 # fasting glucose drift per step
    u_fast = np.median(u[q])                # fasting absorption per step
    n = 4 * H
    num = den = 0.0
    k = 0
    for i in np.flatnonzero(jump >= 10):
        lo, hi = i - n, i + n
        if lo < 0 or hi >= len(p) or not sel[i] or t[hi] - t[i] != n * 300:
            continue
        if (jump[lo:hi] >= 5).sum() != 1 or p["disrupted"].iloc[i:hi].any():
            continue
        if np.isnan(bg[i]) or np.isnan(bg[i + n]):
            continue
        dbg = bg[i + n] - bg[i] - drift * n
        units = u[i + 1:i + n + 1].sum() - u_fast * n
        num += dbg * cr[i]
        den += jump[i] - cr[i] * units
        k += 1
    if k < MIN_MEALS or den <= 0:
        return np.nan, k
    return num / den, k


def person(alias):
    p = S.load(alias)
    p = p[p["bg"].notna() | p["v"].notna()]
    quiet = _quiet_mask(p)
    week = ((p.index - p.index[0]).days // 7).to_numpy()
    out = {"alias": alias}
    for name, sel in (("all", np.ones(len(p), bool)), ("h1", week % 2 == 0), ("h2", week % 2 == 1)):
        out[f"A_{name}"] = np.nanmedian(p["isf"].to_numpy()[sel])
        out[f"B_{name}"], out[f"tdd_{name}"] = est_tdd(p, sel)
        out[f"C_{name}"] = est_fasting(p, quiet, sel)
        out[f"D_{name}"], out[f"nmeal_{name}"] = est_meal(p, quiet, sel)
    return out


if __name__ == "__main__":
    co = S.cohort()
    with Pool(8) as pool:
        d = pd.DataFrame(pool.map(person, list(co.alias)))
    d.to_csv(S.OUT / "ice" / "isf_split.csv", index=False)
    print(f"TDD rule fitted: ISF = {K:.0f} / TDD^{-B_EXP:.2f}")
    for e in "ABCD":
        both = d[[f"{e}_h1", f"{e}_h2"]].dropna()
        both = both[(both > 0).all(1)]
        print(f"{e}: people with both halves {len(both)}, all-record {d[f'{e}_all'].notna().sum()}")
