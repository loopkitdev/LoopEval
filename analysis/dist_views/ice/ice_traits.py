#!/usr/bin/env python3
"""Are the features of a person's ICE distribution personal traits?

Each person's clean 30-min ICE is cut into calendar weeks (>= 4 days of clean
bins, i.e. >= 192). Per week: level (mean), spread relative to level (CV), the
low end (p05 / mean), the high end (p95 / mean), the median relative to the
mean, the share below zero, skew, and the low end in absolute units (p05).
A feature is a trait when people differ far more than a person's weeks do:
  ICC = between-person variance / (between + within), one-way, from the weekly
values (between corrected for the noise in each person's mean).
Also the odd-vs-even-week split-half rank correlation of each person's median
over weeks — a second, assumption-light reading.

Output: ice/traits_weekly.csv, ice/traits_icc.csv
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa

FEATS = {"level": "mean ICE", "cv": "spread ÷ level (CV)", "rel_p05": "low end ÷ level (p5)",
         "rel_p50": "median ÷ level", "rel_p95": "high end ÷ level (p95)", "below0": "share below zero",
         "skew": "skew", "p05": "low end, mg/dL/hr (p5)"}


def weekly(al):
    x = pd.read_pickle(S.OUT / "ice" / "clean30" / f"{al}.pkl").ice
    wk = ((x.index - x.index[0]).days // 7)
    rows = []
    for w, v in x.groupby(wk):
        if len(v) < 192:
            continue
        m = v.mean(); z = (v - m) / v.std()
        rows.append({"alias": al, "week": w, "n": len(v), "level": m, "cv": v.std() / m,
                     "rel_p05": v.quantile(.05) / m, "rel_p50": v.median() / m, "rel_p95": v.quantile(.95) / m,
                     "below0": (v < 0).mean(), "skew": (z ** 3).mean(), "p05": v.quantile(.05)})
    return rows


def icc(df, col):
    g = df.groupby("alias")[col]
    k = g.size(); mu = g.mean(); wv = g.var(ddof=1)
    ok = k >= 2
    within = np.average(wv[ok], weights=(k[ok] - 1))
    between = np.var(mu[ok], ddof=1) - np.mean(within / k[ok])
    return max(between, 0) / (max(between, 0) + within)


if __name__ == "__main__":
    est = pd.read_csv(S.OUT / "ice" / "isf_estimate.csv").dropna(subset=["isf_est"])
    w = pd.DataFrame([r for a in est.alias for r in weekly(a)])
    w.to_csv(S.OUT / "ice" / "traits_weekly.csv", index=False)
    out = []
    for f, lab in FEATS.items():
        odd = w[w.week % 2 == 1].groupby("alias")[f].median()
        even = w[w.week % 2 == 0].groupby("alias")[f].median()
        j = pd.concat([odd, even], axis=1, keys=["o", "e"]).dropna()
        per = w.groupby("alias")[f].median()
        out.append({"feature": lab, "ICC weekly": icc(w, f), "split-half rho": stats.spearmanr(j.o, j.e)[0],
                    "people": len(j), "median": per.median(), "p10": per.quantile(.1), "p90": per.quantile(.9)})
    r = pd.DataFrame(out)
    r.to_csv(S.OUT / "ice" / "traits_icc.csv", index=False)
    print(f"{w.alias.nunique()} people, {len(w)} person-weeks (median {w.groupby('alias').size().median():.0f} weeks each)")
    print(r.round(3).to_string(index=False))
    # how the traits relate to each other (person medians)
    pm = w.groupby("alias")[list(FEATS)].median()
    print("\nspearman between person-level traits:")
    print(pm.corr(method="spearman").round(2).to_string())
