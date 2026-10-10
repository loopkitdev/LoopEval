#!/usr/bin/env python3
"""q06 — clean 30-minute ICE, person by person: distributions and time of day.
Reads ice/clean30/<alias>.pkl and clean30_person.csv (run ice_clean30.py first)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa

co = S.cohort()
r = pd.read_csv(S.OUT / "ice" / "clean30_person.csv")
GRID = np.linspace(-200, 500, 351)
FAST = "#8a5a9e"
fig = S.plt.figure(figsize=(13, 11)); fig.patch.set_facecolor(S.SURFACE)
gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.15], hspace=0.35, wspace=0.2)
a0 = S.axes(fig.add_subplot(gs[0, 0])); a1 = S.axes(fig.add_subplot(gs[0, 1]))
dens, prof, proff = [], [], []
for al in r.alias:
    x = pd.read_pickle(S.OUT / "ice" / "clean30" / f"{al}.pkl")
    k = S.kde(x.ice.to_numpy(), GRID, bw=8.0)
    dens.append(k)
    a0.plot(GRID, k, **S.line_style(co, al, lw=1.3))
    med = x.ice.median()
    h = x.groupby("hour").ice.median() / med
    prof.append(h.reindex(range(24)).to_numpy())
    f = x[x.fasting]
    hf = f.groupby("hour").ice.median().where(f.groupby("hour").size() >= 20) / f.ice.median()
    proff.append(hf.reindex(range(24)).to_numpy())
a0.plot(GRID, np.median(dens, axis=0), color=S.INK, lw=2.4, zorder=6)
a0.axvline(0, color=S.INK2, lw=0.8)
a0.set_xlim(-150, 400); a0.set_ylim(0, None); a0.set_yticks([])
a0.set_xlabel("ICE, 30-min, mg/dL per hour", fontsize=9, color=S.INK2)
a0.set_title(f"Every person's distribution · median {r['median'].median():.0f}, below zero "
             f"{100 * r.below0.median():.0f}% of the time", loc="left", fontsize=10.5, color=S.INK)
prof, proff = np.array(prof), np.array(proff)
for i, al in enumerate(r.alias):
    a1.plot(range(24), prof[i], **S.line_style(co, al, lw=1.1))
m = np.nanmedian(prof, axis=0); mf = np.nanmedian(proff, axis=0)
a1.plot(range(24), m, color=S.INK, lw=2.4, zorder=6, label="all clean bins")
a1.plot(range(24), mf, color=FAST, lw=2.4, zorder=6, ls="--", label="fasting bins only")
a1.axhline(1, color=S.INK2, lw=0.8)
a1.set_xticks(range(0, 24, 3)); a1.set_xticklabels([f"{h:02d}" for h in range(0, 24, 3)])
a1.set_ylim(0, 2.6)
a1.set_xlabel("local hour", fontsize=9, color=S.INK2)
a1.set_ylabel("ICE ÷ the person's own median", fontsize=9, color=S.INK2)
a1.legend(fontsize=8.5, frameon=False, loc="upper left")
a1.set_title("Time of day (median at each hour)", loc="left", fontsize=10.5, color=S.INK)
a2 = S.axes(fig.add_subplot(gs[1, :]))
o = r.sort_values("median").reset_index(drop=True)
y = np.arange(len(o)); cols = [S.color_for(co, al) for al in o.alias]
a2.hlines(y, o.p05, o.p95, color=cols, lw=1.3, alpha=0.5)
a2.scatter(o["median"], y, s=10, color=S.INK, zorder=5, label="median")
a2.scatter(o.fast_median, y, s=12, marker="|", color=FAST, zorder=6, label="fasting median")
a2.scatter(o.fed_median, y, s=12, marker="|", color=S.ACCENT, zorder=6, label="non-fasting median")
a2.axvline(0, color=S.INK2, lw=0.8)
a2.set_ylim(-1, len(o)); a2.set_yticks([])
a2.set_xlim(-60, 350)
a2.set_xlabel("ICE, 30-min, mg/dL per hour", fontsize=9, color=S.INK2)
a2.legend(fontsize=8.5, frameon=False, loc="lower right")
a2.set_title("One row per person, sorted by median · line p5–p95", loc="left", fontsize=10.5, color=S.INK)
S.title(fig, "Clean ICE, person by person",
        f"{len(r)} people, 30-minute bins free of every bad-data flag (median {r.hours.median():,.0f} h per person), "
        "yardstick ISF. Faint lines are people, coloured the representative sample.")
S.save(fig, "q06_clean", tight=dict(left=0.05, right=0.98, top=0.9, bottom=0.06))
print("fasting/fed medians:", r.fast_median.median().round(1), r.fed_median.median().round(1),
      " fed/fast ratio median", (r.fed_median / r.fast_median).median().round(2))
print("hourly profile, all:", dict(zip(range(24), np.round(m, 2))))
print("hourly profile, fasting:", dict(zip(range(24), np.round(mf, 2))))
