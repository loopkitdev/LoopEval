#!/usr/bin/env python3
"""The shrunk fasting-regression ISF (option 3) under tighter definitions of
"fasting", scored on the same tests.

  base      no announced carbs on board, no user bolus in the prior 4 h, no
            disruption (ice_first._quiet_mask)
  night     base, 00:00-06:00 local only
  norise    base, and no 30-minute glucose rise of 30 mg/dL or more anywhere in
            the prior 4 h — unannounced eating excluded from glucose alone,
            without using ICE (which would be circular)
  both      night and norise

For each: C per half and whole record (60-min blocks, every step fasting),
SEs calibrated on the halves, shrunk toward the TDD rule, levelled to the
scheduled median — exactly as isf_shrink.py. Scores: alternating-week
repeatability, similar-people agreement, and the departure from the TDD rule
against announced carbohydrate (should vanish) and the person's schedule
(should stay).

Output: ice/isf_variants.csv (per person x variant), ice/isf_variants_score.csv
"""
from __future__ import annotations
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
np.seterr(all="ignore")
import pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_first import _quiet_mask  # noqa
from isf_shrink import fit  # noqa

H = 12
RISE = 30.0          # mg/dL over 30 min
RISE_LOOKBACK_H = 4


def masks(p):
    base = _quiet_mask(p)
    tod = p["tod_min"].to_numpy()
    night = base & (tod < 360)
    v30 = p["v30"].to_numpy()
    rise = np.nan_to_num(v30) >= RISE
    recent = pd.Series(rise).rolling(RISE_LOOKBACK_H * H, min_periods=1).max().to_numpy() > 0
    norise = base & ~recent
    return {"base": base, "night": night, "norise": norise, "both": night & ~recent}


def person(alias):
    p = S.load(alias)
    p = p[p["bg"].notna() | p["v"].notna()]
    week = ((p.index - p.index[0]).days // 7).to_numpy()
    sels = {"all": np.ones(len(p), bool), "h1": week % 2 == 0, "h2": week % 2 == 1}
    rows = []
    for var, q in masks(p).items():
        r = {"alias": alias, "variant": var, "fast_hours_per_day": q.sum() / H / (len(p) / (24 * H))}
        for name, sel in sels.items():
            r[f"C_{name}"], r[f"se_{name}"], r[f"nblk_{name}"] = fit(p, q, sel)
        rows.append(r)
    return rows


def shrink(d):
    d = d.copy()
    h = d.dropna(subset=["se_h1", "se_h2"])
    k = np.sqrt(np.var(np.log(h.C_h1 / h.C_h2)) / np.mean(h.se_h1 ** 2 + h.se_h2 ** 2))
    for c in ("se_all", "se_h1", "se_h2"):
        d[c] *= k
    a = d.dropna(subset=["se_all", "B_all"])
    a = a[a.C_all > 0]
    offset = np.median(np.log(a.C_all / a.B_all))
    tau2 = max(np.var(np.log(a.C_all) - np.log(a.B_all) - offset) - np.mean(a.se_all ** 2), 1e-6)
    for n in ("all", "h1", "h2"):
        prior = np.log(d[f"B_{n}"]) + offset
        c = np.log(d[f"C_{n}"].where(d[f"C_{n}"] > 0))
        w = (tau2 / (tau2 + d[f"se_{n}"] ** 2)).where(c.notna(), 0.0)
        d[f"w_{n}"] = w
        d[f"E_{n}"] = np.exp(prior + w * (c.fillna(prior) - prior))
    L = np.nanmedian(d.A_all) / np.nanmedian(d.E_all)
    for n in ("all", "h1", "h2"):
        d[f"E_{n}"] *= L
    return d, dict(se_calib=k, level_C_over_B=np.exp(offset), tau=np.sqrt(tau2), level_factor=L)


def icc(x, y):
    X = np.column_stack([x, y]); n = len(X); gm = X.mean(); rm = X.mean(1); cm = X.mean(0)
    msr = 2 * ((rm - gm) ** 2).sum() / (n - 1); msc = n * ((cm - gm) ** 2).sum()
    mse = ((X - rm[:, None] - cm[None, :] + gm) ** 2).sum() / (n - 1)
    return (msr - mse) / (msr + mse + 2 * (msc - mse) / n)


def score(d, e):
    h = d[[f"{e}_h1", f"{e}_h2"]].dropna(); h = h[(h > 0).all(1)]
    lr = np.log(h.iloc[:, 1] / h.iloc[:, 0])
    q = d[["tdd_all", "age_years", f"{e}_all"]].dropna(); q = q[q[f"{e}_all"] > 0]
    z = np.column_stack([np.log(q.tdd_all), q.age_years]); z = (z - z.mean(0)) / z.std(0)
    D = ((z[:, None] - z[None]) ** 2).sum(-1); np.fill_diagonal(D, np.inf)
    lv = np.log(q[f"{e}_all"].to_numpy()); nn = D.argmin(1)
    rnd = np.abs(lv[:, None] - lv[None])[~np.eye(len(lv), dtype=bool)]
    dd = d[(d[f"{e}_all"] > 0) & d.B_all.notna()]
    dep = np.log(dd[f"{e}_all"] / dd.B_all)
    return {"people": len(h), "ICC": icc(np.log(h.iloc[:, 0]), np.log(h.iloc[:, 1])),
            "halves gap %": 100 * (np.exp(np.median(np.abs(lr))) - 1),
            ">25% apart": (np.abs(lr) > np.log(1.25)).mean(),
            "similar %": 100 * (np.exp(np.median(np.abs(lv - lv[nn]))) - 1),
            "random %": 100 * (np.exp(np.median(rnd)) - 1),
            "rho announcing": stats.spearmanr(np.log1p(dd.carb_g_day), dep)[0],
            "p announcing": stats.spearmanr(np.log1p(dd.carb_g_day), dep)[1],
            "rho schedule": stats.spearmanr(np.log(dd.A_all / dd.B_all), dep)[0],
            "p schedule": stats.spearmanr(np.log(dd.A_all / dd.B_all), dep)[1]}


if __name__ == "__main__":
    co = S.cohort()
    with Pool(8) as pool:
        d = pd.DataFrame([r for rows in pool.map(person, list(co.alias)) for r in rows])
    sp = pd.read_csv(S.OUT / "ice" / "isf_split.csv")[["alias", "A_all", "B_all", "B_h1", "B_h2", "tdd_all"]]
    d = d.merge(sp, on="alias").merge(co[["alias", "carb_g_day"]], on="alias")
    d = d.merge(pd.read_csv(S.OUT / "age.csv")[["alias", "age_years"]], on="alias", how="left")
    out, rows = [], []
    for var, g in d.groupby("variant", sort=False):
        g, hp = shrink(g)
        out.append(g)
        for e, lab in (("C", "raw fit"), ("E", "shrunk")):
            rows.append({"fasting": var, "estimator": lab,
                         "fasting h/day": g.fast_hours_per_day.median(),
                         "blocks/person": g.nblk_all.median(), **score(g, e),
                         **({"weight on own": g.w_all.median(), **hp} if e == "E" else {})})
    pd.concat(out).to_csv(S.OUT / "ice" / "isf_variants.csv", index=False)
    r = pd.DataFrame(rows)
    r.to_csv(S.OUT / "ice" / "isf_variants_score.csv", index=False)
    pd.set_option("display.width", 260)
    print(r.round(3).to_string(index=False))
