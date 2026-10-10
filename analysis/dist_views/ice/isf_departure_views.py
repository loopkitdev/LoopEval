#!/usr/bin/env python3
"""i11 — what the shrunk fit's departure from the TDD rule lines up with.
Reads ice/isf_departure.csv (run isf_departure.py first)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa

co = S.cohort()
d = pd.read_csv(S.OUT / "ice" / "isf_departure.csv")
pct = lambda x: 100 * (np.exp(x) - 1)
fig, ax = S.figure(1, 3, figsize=(13, 5.4))
c = [S.color_for(co, a) for a in d.alias]
a = ax[0]
for i, (s, lab) in enumerate((("bolus", "automatic bolus"), ("temp", "temp basal"))):
    x = d[d.strategy == s]
    a.scatter(i + np.random.default_rng(1).uniform(-0.18, 0.18, len(x)), pct(x.dep_E), s=14,
              c=[S.color_for(co, q) for q in x.alias], alpha=0.8, lw=0)
    m = pct(x.dep_E.median())
    a.plot([i - 0.28, i + 0.28], [m, m], color=S.INK, lw=2.2)
    a.text(i + 0.3, m, f"{m:+.0f}%\nn={len(x)}", fontsize=8.5, va="center", color=S.INK)
p = stats.mannwhitneyu(d[d.strategy == "bolus"].dep_E, d[d.strategy == "temp"].dep_E).pvalue
a.set_xticks([0, 1]); a.set_xticklabels(["automatic bolus", "temp basal"])
a.set_xlim(-0.6, 1.8)
a.set_title(f"Dosing strategy: small, not significant (p {p:.2f})", loc="left", fontsize=10.5, color=S.INK)
for a, col, xl, ttl in ((ax[1], "carb_g_day", "announced carbohydrate, g per day", "How much is announced"),
                        (ax[2], "sched_dep", "schedule ÷ TDD rule, %", "The person's own schedule")):
    x = d[col] if col == "carb_g_day" else pct(d[col])
    a.scatter(x, pct(d.dep_E), s=14, c=c, alpha=0.8, lw=0)
    r, p = stats.spearmanr(d[col], d.dep_E)
    if col == "carb_g_day":
        a.set_xscale("symlog", linthresh=10)
    a.set_xlabel(xl, fontsize=8.5, color=S.INK2)
    a.set_title(f"{ttl} (ρ {r:+.2f}, p {p:.0e})", loc="left", fontsize=10.5, color=S.INK)
for a in ax:
    a.axhline(0, color=S.MUTED, lw=0.8)
ax[0].set_ylabel("shrunk fit ÷ TDD rule, % (cohort median = 0)", fontsize=8.5, color=S.INK2)
S.title(fig, "What the fasting fit says beyond daily insulin",
        "Each person's shrunk estimate relative to the TDD-rule prediction. All four blocks together explain 19% of it; "
        "age explains nothing.")
S.save(fig, "i11_isf_departure", tight=dict(left=0.07, right=0.98, top=0.80, bottom=0.12, wspace=0.28))
