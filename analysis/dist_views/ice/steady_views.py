#!/usr/bin/env python3
"""i08 — steady-state basal against the schedule. Reads steady_level.csv and
steady_at_target.csv (run steady_level.py, steady_at_target.py first)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa

co = S.cohort()
lv = pd.read_csv(S.OUT / "ice" / "steady_level.csv")
at = pd.read_csv(S.OUT / "ice" / "steady_at_target.csv")
bands = ["(70, 100]", "(100, 120]", "(120, 140]", "(140, 160]", "(160, 250]"]
xs = np.array([85, 110, 130, 150, 180])

fig, ax = S.figure(1, 3, figsize=(13, 6.3))
a = ax[0]
for _, r in lv.iterrows():
    y = r[bands].to_numpy(dtype=float)
    m = np.isfinite(y)
    if m.sum() >= 2:
        a.plot(xs[m], y[m], **S.line_style(co, r.alias, lw=1.2))
med = lv[bands].median().to_numpy()
a.plot(xs, med, color=S.INK, lw=2.4, marker="o", ms=5, zorder=6)
for x, v, n in zip(xs, med, lv[bands].count()):
    a.text(x, v, f" {v:.2f}\n n={n}", fontsize=8, color=S.INK, va="bottom", zorder=7)
a.axhline(1, color=S.ACCENT, lw=1.2, ls="--")
a.set_yscale("log"); a.set_ylim(0.4, 4)
a.set_yticks([0.5, 0.75, 1, 1.5, 2, 3]); a.set_yticklabels(["0.5", "0.75", "1", "1.5", "2", "3"])
a.minorticks_off()
a.set_xlabel("glucose the window is flat at, mg/dL", fontsize=8.5, color=S.INK2)
a.set_ylabel("insulin absorbed ÷ scheduled basal", fontsize=8.5, color=S.INK2)
a.set_title("Flat at a higher level takes more insulin", loc="left", fontsize=10.5, color=S.INK)

a = ax[1]
r = at.dropna(subset=["ratio_at_target"])
S.strip_kde(a, r.ratio_at_target, [S.color_for(co, x) for x in r.alias], fmt="{:.2f}")
a.axvline(1, color=S.ACCENT, lw=1.2, ls="--")
a.set_xlabel("steady-state rate at own target ÷ scheduled basal", fontsize=8.5, color=S.INK2)
a.set_title("At the person's own target", loc="left", fontsize=10.5, color=S.INK)

a = ax[2]
est = r.ratio_at_target * r.sched
a.scatter(r.sched, est, s=18, c=[S.color_for(co, x) for x in r.alias], alpha=0.8, lw=0)
lim = [0.15, 4]
a.plot(lim, lim, color=S.ACCENT, lw=1.2, ls="--")
a.set_xscale("log"); a.set_yscale("log"); a.set_xlim(lim); a.set_ylim(lim)
for ax_ in (a.xaxis, a.yaxis):
    ax_.set_major_formatter(S.plt.FuncFormatter(lambda v, _: f"{v:g}"))
a.minorticks_off()
a.set_xticks([0.25, 0.5, 1, 2, 4]); a.set_yticks([0.25, 0.5, 1, 2, 4])
a.set_xlabel("scheduled basal, U/hr (median)", fontsize=8.5, color=S.INK2)
a.set_ylabel("steady-state rate at target, U/hr", fontsize=8.5, color=S.INK2)
rho = r.sched.corr(est, method="spearman")
a.set_title(f"Against the schedule (ρ {rho:.2f})", loc="left", fontsize=10.5, color=S.INK)

S.title(fig, "Steady-state basal: what people absorb when nothing is happening",
        "3-h windows: fasting, glucose flat within 10 mg/dL, insulin on board steady. Absorbed insulin "
        "needs no ISF. Faint lines are people, coloured the representative sample.")
S.save(fig, "i08_steady_basal", tight=dict(left=0.06, right=0.98, top=0.80, bottom=0.12, wspace=0.28))
