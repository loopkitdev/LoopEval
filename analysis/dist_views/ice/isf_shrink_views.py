#!/usr/bin/env python3
"""i10 — option 3, C shrunk toward the TDD rule. Reads ice/isf_shrink.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa

co = S.cohort()
d = pd.read_csv(S.OUT / "ice" / "isf_shrink.csv")
L = np.nanmedian(d.A_all) / np.nanmedian(d.C_all)       # put C on the same level for the ghost
fig, ax = S.figure(1, 3, figsize=(13, 5.4))
lim = (6, 300)
a = ax[0]
h = d.dropna(subset=["E_h1", "E_h2"])
hc = d[(d.C_h1 > 0) & (d.C_h2 > 0)]
a.scatter(hc.C_h1 * L, hc.C_h2 * L, s=12, color=S.MUTED, alpha=0.45, lw=0, label="C alone (same level)")
for _, r in h.merge(hc[["alias"]], on="alias").iterrows():
    c = d.loc[d.alias == r.alias].iloc[0]
    a.plot([c.C_h1 * L, r.E_h1], [c.C_h2 * L, r.E_h2], color=S.MUTED, lw=0.5, alpha=0.4)
a.scatter(h.E_h1, h.E_h2, s=15, c=[S.color_for(co, x) for x in h.alias], alpha=0.85, lw=0, label="shrunk")
a.legend(fontsize=8, frameon=False, loc="lower right")
a.set_xlabel("odd weeks, mg/dL per U", fontsize=8.5, color=S.INK2)
a.set_ylabel("even weeks, mg/dL per U", fontsize=8.5, color=S.INK2)
a.set_title("Halves: ICC 0.87 → 0.92, typical gap 17% → 12%", loc="left", fontsize=10.5, color=S.INK)
a = ax[1]
w = np.r_[d.w_h1.dropna(), d.w_h2.dropna()]
S.strip_kde(a, d.w_all, [S.color_for(co, x) for x in d.alias], fmt="{:.2f}", note_x=0.84)
a.set_xlim(0, 1.02)
a.set_xlabel("weight on the person's own fit (0 = TDD rule, 1 = own data)", fontsize=8.5, color=S.INK2)
a.set_title(f"Own data carries most of the weight (halves: {np.median(w):.2f})", loc="left", fontsize=10.5, color=S.INK)
a = ax[2]
a.scatter(d.A_all, d.E_all, s=15, c=[S.color_for(co, x) for x in d.alias], alpha=0.85, lw=0)
rho = d.A_all.corr(d.E_all, method="spearman")
a.set_xlabel("scheduled ISF", fontsize=8.5, color=S.INK2)
a.set_ylabel("shrunk estimate, whole record", fontsize=8.5, color=S.INK2)
a.set_title(f"Against the schedule (ρ {rho:.2f})", loc="left", fontsize=10.5, color=S.INK)
for a in (ax[0], ax[2]):
    a.plot(lim, lim, color=S.MUTED, lw=1, ls="--")
    a.set_xscale("log"); a.set_yscale("log"); a.set_xlim(lim); a.set_ylim(lim)
    a.set_xticks([10, 25, 50, 100, 250]); a.set_yticks([10, 25, 50, 100, 250])
    for x_ in (a.xaxis, a.yaxis):
        x_.set_major_formatter(S.plt.FuncFormatter(lambda v, _: f"{v:g}"))
    a.minorticks_off()
S.title(fig, "Fasting regression shrunk toward the TDD rule",
        "Level set so the cohort median equals the scheduled median (×2.06 on the raw fit). "
        "Grey: each person's unshrunk halves, with a line to where shrinking moves them.")
S.save(fig, "i10_isf_shrink", tight=dict(left=0.06, right=0.98, top=0.80, bottom=0.12, wspace=0.28))
