#!/usr/bin/env python3
"""What the distribution of clean 30-min ICE says, beyond its level.

1. The level is an identity. Over a long record glucose ends roughly where it
   started, so mean ICE ~= mean insulin action = ISF x insulin per hour
   = ISF x TDD / 24 — the "rule of X" constant divided by 24. Checked per person.
2. Shape with the level divided out: ICE / person mean -> p05, p95, IQR, the share
   below zero, skew. Related to behaviour (announced carbs, user boluses/day,
   dosing strategy), sensor, and outcome (TIR, time below 70).
3. When ICE goes negative: rates by glucose level, glucose trend over the
   previous 30-min bin (non-overlapping with the bin scored), hours since the last user bolus, and local hour — each as the
   share of that person's bins below zero, then the median across people.

No carb entries are used anywhere here.
Output: ice/shape_person.csv, ice/negative_conditional.csv
"""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa

EST = pd.read_csv(S.OUT / "ice" / "isf_estimate.csv").set_index("alias")


def person(al):
    x = pd.read_pickle(S.OUT / "ice" / "clean30" / f"{al}.pkl")
    p = S.load(al)
    # insulin per hour over the whole panel (every unit delivered), for the identity
    u_hr = (p.basal_eff / 12 + p.bolus_u.fillna(0)).mean() * 12
    m = x.ice.mean()
    r = x.ice / m
    z = (x.ice - m) / x.ice.std()
    row = {"alias": al, "mean": m, "isf": EST.loc[al, "isf_est"], "u_hr": u_hr,
           "isf_x_u": EST.loc[al, "isf_est"] * u_hr, "ia_mean": x.ia.mean(), "v_mean": x.v.mean(),
           "rel_p05": r.quantile(.05), "rel_p25": r.quantile(.25), "rel_p50": r.median(),
           "rel_p75": r.quantile(.75), "rel_p95": r.quantile(.95), "cv": x.ice.std() / m,
           "below0": (x.ice < 0).mean(), "skew": (z ** 3).mean()}
    # conditions for the negative tail
    ub = p.manual_bolus_u.fillna(0)
    last = pd.Series(np.where(ub > 0.05, p.index.asi8, np.nan), index=p.index).ffill()
    since = ((p.index.asi8 - last) / 3.6e12).resample("30min").last()
    x = x.assign(since_bolus=since.reindex(x.index).to_numpy(),
                 trend=(x.bg.shift(1) - x.bg.shift(2)).where(
                     x.index.to_series().diff(2).eq(pd.Timedelta("60min"))) * 2)   # the PREVIOUS bin's trend, so it shares no reading with this bin
    neg = x.ice < 0
    cond = []
    for name, col, edges in (("glucose", "bg", [0, 80, 120, 180, 250, 500]),
                             ("prior trend", "trend", [-500, -60, -20, 20, 60, 500]),
                             ("hours since user bolus", "since_bolus", [0, 1, 2, 3, 5, 1e6]),
                             ("hour", "hour", [0, 4, 8, 12, 16, 20, 24])):
        b = pd.cut(x[col], edges, right=False)
        g = neg.groupby(b, observed=True).agg(["mean", "size"])
        for k, (mm, n) in g.iterrows():
            if n >= 30:
                cond.append({"alias": al, "factor": name, "bin": str(k), "rate": mm, "n": n})
    return row, cond


if __name__ == "__main__":
    al = [a for a in EST.dropna(subset=["isf_est"]).index]
    with Pool(8) as pl:
        res = pl.map(person, al)
    d = pd.DataFrame([r[0] for r in res]).merge(
        S.cohort()[["alias", "carb_g_day", "user_boluses_per_day", "strategy", "sensor", "tir", "t70", "tdd"]], on="alias")
    d.to_csv(S.OUT / "ice" / "shape_person.csv", index=False)
    c = pd.DataFrame([x for r in res for x in r[1]])
    c.to_csv(S.OUT / "ice" / "negative_conditional.csv", index=False)

    print("1. identity: mean ICE vs ISF x insulin/hr: ratio median %.3f (p10 %.3f, p90 %.3f), spearman %.3f"
          % ((d["mean"] / d.isf_x_u).median(), (d["mean"] / d.isf_x_u).quantile(.1),
             (d["mean"] / d.isf_x_u).quantile(.9), stats.spearmanr(d["mean"], d.isf_x_u)[0]))
    print("   clean-bin glucose term: median %.1f mg/dL/hr; mean ICE median %.0f = rule-of-X %.0f / 24"
          % (d.v_mean.median(), d["mean"].median(), 24 * d["mean"].median()))
    print("\n2. shape relative to own mean (median across people, p10-p90):")
    for col in ("rel_p05", "rel_p25", "rel_p50", "rel_p75", "rel_p95", "cv", "below0", "skew"):
        print(f"   {col:8s} {d[col].median():6.2f}  ({d[col].quantile(.1):.2f} to {d[col].quantile(.9):.2f})")
    print("   what the shape tracks (spearman):")
    for col in ("cv", "rel_p05", "below0", "skew"):
        out = []
        for f in ("carb_g_day", "user_boluses_per_day", "tir", "t70", "tdd", "isf"):
            rho, pv = stats.spearmanr(d[col], d[f], nan_policy="omit")
            out.append(f"{f} {rho:+.2f}{'*' if pv < 0.01 else ''}")
        print(f"   {col:8s} " + ", ".join(out))
    for f in ("strategy", "sensor"):
        print(f"   by {f}:", d.groupby(f)[["cv", "below0", "rel_p05"]].median().round(2).to_dict("index"))
    print("\n3. share of bins below zero, by condition (median across people, people):")
    t = c.groupby(["factor", "bin"], sort=False).agg(rate=("rate", "median"), people=("alias", "nunique"))
    print(t.round(3).to_string())
