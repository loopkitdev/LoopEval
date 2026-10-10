#!/usr/bin/env python3
"""q07 — what the distribution says: the level identity, the shape with the
level divided out, and when ICE goes negative. Reads shape_person.csv,
negative_conditional.csv, clean30/*.pkl (run ice_shape.py first)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa

co = S.cohort()
d = pd.read_csv(S.OUT / "ice" / "shape_person.csv")
c = pd.read_csv(S.OUT / "ice" / "negative_conditional.csv").merge(co[["alias", "sensor"]], on="alias")
fig, ax = S.figure(1, 4, figsize=(14, 5.4), gridspec_kw={"width_ratios": [1, 1.1, 1, 1]})
a = ax[0]
a.scatter(d.isf_x_u, d["mean"], s=14, c=[S.color_for(co, x) for x in d.alias], alpha=0.85, lw=0)
lim = [10, 250]
a.plot(lim, lim, color=S.MUTED, ls="--", lw=1)
a.set_xscale("log"); a.set_yscale("log"); a.set_xlim(lim); a.set_ylim(lim)
for x_ in (a.xaxis, a.yaxis):
    x_.set_major_formatter(S.plt.FuncFormatter(lambda v, _: f"{v:g}"))
a.set_xticks([10, 25, 50, 100, 250]); a.set_yticks([10, 25, 50, 100, 250]); a.minorticks_off()
a.set_xlabel("ISF × insulin delivered per hour", fontsize=8.5, color=S.INK2)
a.set_ylabel("mean ICE, mg/dL per hour", fontsize=8.5, color=S.INK2)
r = (d["mean"] / d.isf_x_u).median()
a.set_title(f"The level is an identity (ratio {r:.2f})", loc="left", fontsize=10, color=S.INK)
a = ax[1]
grid = np.linspace(-1.5, 5, 300)
dens = []
for al in d.alias:
    x = pd.read_pickle(S.OUT / "ice" / "clean30" / f"{al}.pkl").ice
    k = S.kde((x / x.mean()).to_numpy(), grid, bw=0.08)
    dens.append(k)
    a.plot(grid, k, **S.line_style(co, al, lw=1.2))
a.plot(grid, np.median(dens, axis=0), color=S.INK, lw=2.4, zorder=6)
for q, lab in ((d.rel_p05.median(), "p5"), (d.rel_p50.median(), "median"), (d.rel_p95.median(), "p95")):
    a.axvline(q, color=S.INK2, lw=0.8, ls=":")
    a.text(q, a.get_ylim()[1] * 0.97 if a.get_ylim()[1] else 1, f" {lab} {q:.2f}", fontsize=8, color=S.INK2, va="top")
a.axvline(0, color=S.INK2, lw=0.8)
a.set_xlim(-1, 4); a.set_ylim(0, None); a.set_yticks([])
a.set_xlabel("ICE ÷ the person's own mean", fontsize=8.5, color=S.INK2)
a.set_title("With the level divided out, one shape", loc="left", fontsize=10, color=S.INK)
order_t = ["[-500, -60)", "[-60, -20)", "[-20, 20)", "[20, 60)", "[60, 500)"]
lab_t = ["< −60", "−60 to −20", "flat", "20 to 60", "> 60"]
order_b = ["[0.0, 1.0)", "[1.0, 2.0)", "[2.0, 3.0)", "[3.0, 5.0)", "[5.0, 1000000.0)"]
lab_b = ["0–1", "1–2", "2–3", "3–5", "5+"]
for a, f, order, labs, xl, ttl in ((ax[2], "prior trend", order_t, lab_t, "glucose trend in the previous 30 min, mg/dL/hr",
                                   "Negative ICE follows a rise"),
                                  (ax[3], "hours since user bolus", order_b, lab_b, "hours since the last user bolus",
                                   "…and is rarest 1–3 h after a bolus")):
    for sen, col in (("Dexcom G7", S.ACCENT), ("Libre 3", S.COOL), (None, S.INK)):
        g = c[(c.factor == f) & ((c.sensor == sen) if sen else True)]
        m = g.groupby("bin").rate.median().reindex(order) * 100
        a.plot(range(len(order)), m.values, marker="o", ms=4, color=col, lw=2.2 if sen is None else 1.4,
               label=(f"{sen} ({g.alias.nunique()})" if sen else f"everyone ({g.alias.nunique()})"))
    a.set_xticks(range(len(order))); a.set_xticklabels(labs, fontsize=8)
    a.set_xlabel(xl, fontsize=8.5, color=S.INK2)
    a.set_ylim(0, None)
    a.set_title(ttl, loc="left", fontsize=10, color=S.INK)
ax[2].set_ylabel("% of 30-min bins with ICE below zero (median person)", fontsize=8.5, color=S.INK2)
ax[2].legend(fontsize=7.5, frameon=False, loc="upper left")
S.title(fig, "What the distribution of ICE says",
        "Clean 30-minute ICE, yardstick ISF, every unit delivered, no carb entries used. "
        "Dexcom G7 is almost all Omnipod automatic-bolus, Libre 3 almost all twiist temp-basal.")
S.save(fig, "q07_shape", tight=dict(left=0.05, right=0.99, top=0.8, bottom=0.14, wspace=0.32))
