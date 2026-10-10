#!/usr/bin/env python3
"""A starting rule for people with no history: predict the yardstick ISF from
TDD (and age).

Target: the yardstick ISF (ice/isf_estimate.csv). Candidates, all fitted on
log ISF:
  rule of 1800        ISF = 1800 / TDD                     (no fit)
  rule of X           ISF = X / TDD, X fitted (one number)
  power               log ISF = a + b log TDD
  power + age         ... + c * age
  power + age band    ... + band offsets (<13, 13-17, 18-25, 26-49, 50+)
  power + age spline  ... + c1 age + c2 max(age-18,0)   (a kink at 18)
Scored by leave-one-out: median and p90 absolute % error, and the share within
+-20%. Also the same rules scored against the SCHEDULED ISF, for comparison.

Output: ice/isf_start_rule.csv
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa

e = pd.read_csv(S.OUT / "ice" / "isf_estimate.csv")
r = pd.read_csv(S.OUT / "isf_rules.csv")[["alias", "tdd_use", "isf"]]
a = pd.read_csv(S.OUT / "age.csv")[["alias", "age_years"]]
d = e.merge(r, on="alias").merge(a, on="alias", how="left").dropna(subset=["isf_est", "tdd_use"])
d = d[d.age_years.notna()].reset_index(drop=True)
d["log_tdd"] = np.log(d.tdd_use)
BANDS = [0, 13, 18, 26, 50, 200]
d["band"] = pd.cut(d.age_years, BANDS, right=False, labels=["<13", "13-17", "18-25", "26-49", "50+"])


def design(df, kind):
    cols = [np.ones(len(df))]
    if kind in ("power", "power+age", "power+band", "power+spline"):
        cols.append(df.log_tdd.to_numpy())
    if kind == "power+age":
        cols.append(df.age_years.to_numpy())
    if kind == "power+spline":
        cols += [df.age_years.to_numpy(), np.maximum(df.age_years.to_numpy() - 18, 0)]
    if kind == "power+band":
        for b in ["<13", "13-17", "18-25", "50+"]:            # 26-49 is the reference
            cols.append((df.band == b).to_numpy().astype(float))
    return np.column_stack(cols)


def predict(train, test, kind, target):
    y = np.log(train[target])
    if kind == "rule1800":
        return np.log(1800 / test.tdd_use)
    if kind == "ruleX":
        X = np.exp(np.median(y + train.log_tdd))
        return np.log(X / test.tdd_use)
    beta = np.linalg.lstsq(design(train, kind), y, rcond=None)[0]
    return design(test, kind) @ beta


rows = []
KINDS = ["rule1800", "ruleX", "power", "power+age", "power+band", "power+spline"]
for target in ("isf_est", "isf"):
    for kind in KINDS:
        err = []
        for i in range(len(d)):
            tr, te = d.drop(i), d.iloc[[i]]
            err.append(np.asarray(predict(tr, te, kind, target))[0] - np.log(te[target].iloc[0]))
        err = np.abs(np.array(err))
        rows.append({"target": "yardstick" if target == "isf_est" else "schedule", "rule": kind,
                     "median abs err %": 100 * (np.exp(np.median(err)) - 1),
                     "p90 abs err %": 100 * (np.exp(np.quantile(err, .9)) - 1),
                     "within 20%": np.mean(err < np.log(1.2))})
res = pd.DataFrame(rows)
res.to_csv(S.OUT / "ice" / "isf_start_rule.csv", index=False)
print(f"{len(d)} people with age and a yardstick ISF")
print(res.round(3).to_string(index=False))
# the fitted rules on the full set, for writing down
for kind in ("ruleX", "power", "power+band", "power+spline"):
    y = np.log(d.isf_est)
    if kind == "ruleX":
        print(f"\nruleX: ISF = {np.exp(np.median(y + d.log_tdd)):.0f} / TDD")
        continue
    beta = np.linalg.lstsq(design(d, kind), y, rcond=None)[0]
    print(f"{kind}: coefficients {np.round(beta, 3).tolist()}")
beta = np.linalg.lstsq(design(d, "power+band"), np.log(d.isf_est), rcond=None)[0]
print(f"\npower+band: ISF = {np.exp(beta[0]):.0f} / TDD^{-beta[1]:.2f} x band factor:",
      {b: round(float(np.exp(c)), 2) for b, c in zip(["<13", "13-17", "18-25", "50+"], beta[2:])}, "(26-49 = 1)")
print("band sizes:", d.band.value_counts().sort_index().to_dict())
# residual of the power rule by age band (does age carry anything after TDD?)
bp = np.linalg.lstsq(design(d, "power"), np.log(d.isf_est), rcond=None)[0]
d["res"] = np.log(d.isf_est) - design(d, "power") @ bp
print("power-rule residual by age band (ISF % above the TDD rule):",
      d.groupby("band", observed=True).res.median().apply(lambda x: round(100 * (np.exp(x) - 1))).to_dict())
from scipy.stats import kruskal
print("kruskal across bands p =", round(kruskal(*[g.res for _, g in d.groupby('band', observed=True)]).pvalue, 3))

# record the no-history starting rule for ice/isf_yardstick.py
import json
beta = np.linalg.lstsq(design(d, "power"), np.log(d.isf_est), rcond=None)[0]
pfile = S.OUT / "ice" / "isf_yardstick_params.json"
prm = json.loads(pfile.read_text()) if pfile.exists() else {}
prm.update({"start_rule_K": float(np.exp(beta[0])), "start_rule_b": float(-beta[1]),
            "start_rule_X": float(np.exp(np.median(np.log(d.isf_est) + d.log_tdd)))})
pfile.write_text(json.dumps(prm, indent=1))
print("wrote start rule to", pfile)
