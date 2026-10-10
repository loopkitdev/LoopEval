#!/usr/bin/env python3
"""Score the alternating-week ISF estimators: repeatability and similar-people
agreement. Reads ice/isf_split.csv; writes ice/isf_split_score.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa

d = pd.read_csv(S.OUT / "ice" / "isf_split.csv")
age = pd.read_csv(S.OUT / "age.csv")[["alias", "age_years"]]
d = d.merge(age, on="alias", how="left")


def icc(x, y):
    """ICC(2,1)-style agreement on two halves (absolute agreement)."""
    X = np.column_stack([x, y]); n = len(X)
    gm = X.mean(); rm = X.mean(1); cm = X.mean(0)
    msr = 2 * ((rm - gm) ** 2).sum() / (n - 1)
    msc = n * ((cm - gm) ** 2).sum() / 1
    mse = ((X - rm[:, None] - cm[None, :] + gm) ** 2).sum() / (n - 1)
    return (msr - mse) / (msr + mse + 2 * (msc - mse) / n)


rows = []
for e, name in (("A", "scheduled"), ("B", "TDD rule"), ("C", "fasting regression"), ("D", "meal match")):
    h = d[[f"{e}_h1", f"{e}_h2"]]
    neg = int(((h <= 0).any(axis=1) & h.notna().all(axis=1)).sum())
    h = h[(h > 0).all(axis=1)].dropna()
    lr = np.log(h[f"{e}_h2"] / h[f"{e}_h1"])
    a = d[f"{e}_all"]
    a = a[a > 0]
    # similar people: nearest neighbour on standardised (log TDD, age), full record
    s = d[["alias", "tdd_all", "age_years", f"{e}_all"]].dropna()
    s = s[s[f"{e}_all"] > 0]
    z = np.column_stack([np.log(s.tdd_all), s.age_years])
    z = (z - z.mean(0)) / z.std(0)
    dist = ((z[:, None, :] - z[None, :, :]) ** 2).sum(-1); np.fill_diagonal(dist, np.inf)
    nn = dist.argmin(1)
    lv = np.log(s[f"{e}_all"].to_numpy())
    nn_diff = np.abs(lv - lv[nn])
    rand = np.abs(lv[:, None] - lv[None, :])[~np.eye(len(lv), dtype=bool)]
    rows.append({"estimator": f"{e} {name}", "people (both halves)": len(h), "non-positive": neg,
                 "ICC log, halves": icc(np.log(h.iloc[:, 0]), np.log(h.iloc[:, 1])),
                 "median within-person diff %": 100 * (np.exp(np.median(np.abs(lr))) - 1),
                 "share differing >25%": (np.abs(lr) > np.log(1.25)).mean(),
                 "median ISF (all)": a.median(),
                 "between-person p10-p90": f"{a.quantile(.1):.0f}-{a.quantile(.9):.0f}",
                 "nearest-neighbour diff %": 100 * (np.exp(np.median(nn_diff)) - 1),
                 "random-pair diff %": 100 * (np.exp(np.median(rand)) - 1),
                 "people (similar-people test)": len(s)})
r = pd.DataFrame(rows)
r.to_csv(S.OUT / "ice" / "isf_split_score.csv", index=False)
pd.set_option("display.width", 250)
print(r.round(2).to_string(index=False))
# cross-agreement on the full record
lg = np.log(d[[f"{e}_all" for e in "ABCD"]].where(lambda x: x > 0))
print("\nSpearman between estimators (full record):")
print(lg.corr(method="spearman").round(2).to_string())
