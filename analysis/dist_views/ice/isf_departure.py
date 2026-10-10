#!/usr/bin/env python3
"""What does the fasting fit's departure from the TDD rule line up with?

dep = log(estimate / TDD-rule prediction), whole record, for C (raw fit, the
cohort-wide level offset removed) and E (shrunk). Compared against things that
should not change insulin sensitivity (dosing strategy, pump, sensor, how much
is announced) and things that plausibly could (age, the schedule's own departure
from the TDD rule).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa

d = pd.read_csv(S.OUT / "ice" / "isf_shrink.csv")
co = S.cohort()[["alias", "strategy", "pump", "sensor", "carb_g_day", "tir", "target" if "target" in S.cohort().columns else "alias"]]
d = d.merge(S.cohort()[["alias", "strategy", "pump", "sensor", "carb_g_day", "tir"]], on="alias")
d = d.merge(pd.read_csv(S.OUT / "age.csv")[["alias", "age_years"]], on="alias", how="left")
d = d[(d.C_all > 0) & d.B_all.notna()].copy()
d["dep_C"] = np.log(d.C_all / d.B_all)
d["dep_C"] -= d.dep_C.median()
d["dep_E"] = np.log(d.E_all / d.B_all)
d["dep_E"] -= d.dep_E.median()
d["sched_dep"] = np.log(d.A_all / d.B_all)
d["log_carb"] = np.log1p(d.carb_g_day)
d["temp"] = (d.strategy == "temp").astype(float)
print(f"{len(d)} people; SD of departure: C {d.dep_C.std():.3f}, E {d.dep_E.std():.3f} (log)")

print("\n-- categorical (median departure as %, Kruskal-Wallis p)")
for col in ("strategy", "pump", "sensor"):
    g = d.groupby(col)
    for dep in ("dep_C", "dep_E"):
        groups = [x[dep].values for _, x in g if len(x) >= 5]
        p = stats.kruskal(*groups).pvalue if len(groups) > 1 else np.nan
        meds = {k: f"{100*(np.exp(x[dep].median())-1):+.0f}% (n={len(x)})" for k, x in g if len(x) >= 5}
        print(f"  {col:9s} {dep}: {meds}  p={p:.3g}")

print("\n-- continuous (Spearman)")
for col in ("age_years", "log_carb", "sched_dep", "tir"):
    for dep in ("dep_C", "dep_E"):
        r, p = stats.spearmanr(d[col], d[dep], nan_policy="omit")
        print(f"  {col:10s} {dep}: rho {r:+.2f} p={p:.3g}")

print("\n-- within one pump: strategy contrast")
for pump, g in d.groupby("pump"):
    if g.strategy.nunique() > 1:
        for s, x in g.groupby("strategy"):
            print(f"  {pump} / {s}: n={len(x)} median dep_C {100*(np.exp(x.dep_C.median())-1):+.0f}%")

print("\n-- multiple regression on dep_E: share of variance (R^2) by block, added last")
m = d.dropna(subset=["age_years"]).copy()
blocks = {"strategy (=pump/sensor)": ["temp"], "announcing": ["log_carb"],
          "age": ["age_years"], "schedule vs TDD rule": ["sched_dep"]}
def r2(cols):
    X = np.column_stack([np.ones(len(m))] + [m[c] for c in cols])
    b, *_ = np.linalg.lstsq(X, m.dep_E, rcond=None)
    res = m.dep_E - X @ b
    return 1 - res.var() / m.dep_E.var()
allc = [c for v in blocks.values() for c in v]
full = r2(allc)
print(f"  all together R^2 {full:.2f} (n={len(m)})")
for name, cols in blocks.items():
    rest = [c for c in allc if c not in cols]
    print(f"  {name:25s} alone {r2(cols):.2f}   added last {full - r2(rest):.2f}")
X = np.column_stack([np.ones(len(m))] + [m[c] for c in allc])
b, *_ = np.linalg.lstsq(X, m.dep_E, rcond=None)
print("  coefficients:", {c: round(v, 3) for c, v in zip(["const"] + allc, b)})
d.to_csv(S.OUT / "ice" / "isf_departure.csv", index=False)
