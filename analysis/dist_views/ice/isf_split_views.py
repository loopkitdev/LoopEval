#!/usr/bin/env python3
"""i09 — alternating-week halves for each ISF estimator. Reads ice/isf_split.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa

co = S.cohort()
d = pd.read_csv(S.OUT / "ice" / "isf_split.csv")
sc = pd.read_csv(S.OUT / "ice" / "isf_split_score.csv").set_index("estimator")
fig, ax = S.figure(1, 4, figsize=(13, 4.6))
lim = (3, 400)
spec = [("B", "B · TDD rule"), ("C", "C · fasting regression"), ("D", "D · meal match")]
for a, (e, ttl) in zip(ax[:3], spec):
    h = d[["alias", f"{e}_h1", f"{e}_h2"]].dropna()
    h = h[(h[f"{e}_h1"] > 0) & (h[f"{e}_h2"] > 0)]
    a.scatter(h[f"{e}_h1"], h[f"{e}_h2"], s=14, c=[S.color_for(co, x) for x in h.alias], alpha=0.8, lw=0)
    row = sc.loc[[i for i in sc.index if i.startswith(e)][0]]
    a.text(0.04, 0.96, f"ICC {row['ICC log, halves']:.2f}\nhalves differ {row['median within-person diff %']:.0f}%"
           f" (median)\n{len(h)} people", transform=a.transAxes, va="top", fontsize=8.5, color=S.INK)
    a.set_title(ttl, loc="left", fontsize=10.5, color=S.INK)
    a.set_xlabel("odd weeks, mg/dL per U", fontsize=8.5, color=S.INK2)
a = ax[3]
h = d[["alias", "A_all", "C_all"]].dropna()
a.scatter(h.A_all, h.C_all, s=14, c=[S.color_for(co, x) for x in h.alias], alpha=0.8, lw=0)
a.set_title("C against the schedule", loc="left", fontsize=10.5, color=S.INK)
a.set_xlabel("scheduled ISF", fontsize=8.5, color=S.INK2)
a.set_ylabel("fasting regression, whole record", fontsize=8.5, color=S.INK2)
for a in ax:
    a.plot(lim, lim, color=S.MUTED, lw=1, ls="--")
    a.set_xscale("log"); a.set_yscale("log"); a.set_xlim(lim); a.set_ylim(lim)
    a.set_xticks([5, 10, 25, 50, 100, 250]); a.set_yticks([5, 10, 25, 50, 100, 250])
    for x_ in (a.xaxis, a.yaxis):
        x_.set_major_formatter(S.plt.FuncFormatter(lambda v, _: f"{v:g}"))
    a.minorticks_off()
ax[0].set_ylabel("even weeks, mg/dL per U", fontsize=8.5, color=S.INK2)
S.title(fig, "Does each ISF estimator give the same answer twice?",
        "Each person's record split into alternating weeks, every estimator computed on each half alone. "
        "Dashed line is equality.")
S.save(fig, "i09_isf_split", tight=dict(left=0.05, right=0.99, top=0.78, bottom=0.13, wspace=0.3))
