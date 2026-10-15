#!/usr/bin/env python3
"""Does each ISF estimate carry diet? The low-carb confound, measured.

Diet proxy: meal insulin per day = TDD - 24 x fasting insulin rate (fb, the
insulin absorbed per hour in quiet hours). It counts every unit beyond basal,
announced or not, because the loop doses for unannounced meals too.
Resistance proxy: fb itself. Holding fb fixed removes most of "resistant people
need more insulin for everything"; what meal insulin still varies with is
mostly how much is eaten.

For each estimator, the partial Spearman of log ISF with log meal insulin
holding log fb (and, as a second reading, with announced carbs per day holding
log fb). A diet-free estimate should sit near zero; the rule of 1800 is
negative by construction.

Estimators: rule of 1800 (1800/TDD), scheduled ISF, the basal rule alone, the
raw quiet-hour slope without and with the ICE meal mask (x1.0), and the
yardstick (shrunk, levelled).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
import style as S  # noqa
from settings_claims import pcorr  # noqa

bp = pd.read_csv(S.OUT / "ice" / "isf_basal_prior.csv")[["alias", "A_all", "Bb_all", "E_basal_all", "fb_all", "tdd_all", "carb_g_day"]]
im = pd.read_csv(S.OUT / "ice" / "isf_icemask.csv")[["alias", "C_none", "C_1.0"]]
d = bp.merge(im, on="alias").dropna(subset=["fb_all", "tdd_all"])
d["meal_u"] = d.tdd_all - 24 * d.fb_all
d = d[d.meal_u > 0].copy()
d["log_meal"] = np.log(d.meal_u); d["log_fb"] = np.log(d.fb_all); d["log_carb"] = np.log1p(d.carb_g_day)
est = {"rule of 1800 (1800 / TDD)": 1800 / d.tdd_all, "scheduled ISF": d.A_all, "basal rule alone": d.Bb_all,
       "raw quiet-hour slope": d.C_none, "raw slope, ICE meal mask": d["C_1.0"], "yardstick (current)": d.E_basal_all}
print(f"{len(d)} people; meal insulin median {d.meal_u.median():.1f} U/day ({(d.meal_u / d.tdd_all).median():.0%} of TDD); "
      f"corr(log meal, log fb) {stats.spearmanr(d.log_meal, d.log_fb)[0]:+.2f}")
rows = []
for name, v in est.items():
    x = d.assign(y=np.log(v.where(v > 0)))
    raw = stats.spearmanr(x.y, x.log_meal, nan_policy="omit")[0]
    pm = pcorr(x, "y", "log_meal", ["log_fb"])
    pc = pcorr(x, "y", "log_carb", ["log_fb"])
    # elasticity: % change in ISF per % change in meal insulin, holding fb (OLS on logs)
    m = x[["y", "log_meal", "log_fb"]].dropna()
    b = np.linalg.lstsq(np.column_stack([np.ones(len(m)), m.log_meal, m.log_fb]), m.y, rcond=None)[0][1]
    rows.append({"estimator": name, "raw rho vs meal insulin": raw, "partial rho | fasting rate": pm[0], "p": pm[1],
                 "elasticity | fasting rate": b, "partial rho, announced carbs | fasting": pc[0], "p carbs": pc[1], "n": pm[2]})
r = pd.DataFrame(rows)
pd.set_option("display.width", 220)
print(r.round(3).to_string(index=False))
# a concrete low-carb reading: people in the lowest vs highest third of meal insulin, matched on fasting rate
d["fb_t"] = pd.qcut(d.fb_all, 3, labels=False)
out = []
for name, v in est.items():
    dd = d.assign(v=v)
    diffs = []
    for _, g in dd.groupby("fb_t"):
        q = pd.qcut(g.meal_u, 3, labels=False)
        diffs.append(np.log(g.v[q == 0].median() / g.v[q == 2].median()))
    out.append((name, 100 * (np.exp(np.mean(diffs)) - 1)))
print("\nlowest third of meal insulin vs highest, within thirds of fasting rate (ISF % higher for light eaters):")
for n_, v_ in out:
    print(f"  {n_:28s} {v_:+.0f}%")
