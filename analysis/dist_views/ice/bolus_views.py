#!/usr/bin/env python3
"""q08 — ICE around isolated user boluses, against the bolus's own modelled
activity. Reads bolus_event.csv and bolus_correction_curve.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa

cv = pd.read_csv(S.OUT / "ice" / "bolus_event.csv", index_col=0)
cc = pd.read_csv(S.OUT / "ice" / "bolus_correction_curve.csv", index_col=0).iloc[:, 0]
xs = [i for i in cv.index if i.startswith("x")]
t = np.array([int(i[1:]) for i in xs]) / 60 + 0.125
fig, ax = S.figure(1, 2, figsize=(13, 5.6))
a = ax[0]
for sz, col in (("small", "#9aa6b2"), ("mid", S.COOL), ("large", S.INK)):
    a.plot(t, cv.loc[xs, sz], color=col, lw=2, label=f"{sz} ({cv.loc['units', sz]:.1f} U)")
    a.plot(t, cv.loc[["a" + i[1:] for i in xs], sz], color=col, lw=1.2, ls=":")
a.axhline(0, color=S.INK2, lw=0.8); a.axvline(0, color=S.INK2, lw=0.8)
a.set_xlabel("hours from the bolus", fontsize=9, color=S.INK2)
a.set_ylabel("mg/dL per hour", fontsize=9, color=S.INK2)
a.legend(fontsize=8.5, frameon=False, loc="upper right", title="solid: ICE above pre-bolus level\ndotted: the bolus's own credited action",
         title_fontsize=8)
a.set_title("All isolated user boluses ≥ 1 U, by size (each person's thirds)", loc="left", fontsize=10.5, color=S.INK)
a = ax[1]
a.plot(t, cc.loc[xs], color=S.ACCENT, lw=2.4, label="ICE above pre-bolus level")
a.plot(t, cc.loc[["a" + i[1:] for i in xs]], color=S.ACCENT, lw=1.3, ls=":", label="the bolus's own credited action")
a.fill_between(t, 0, cc.loc[xs], where=cc.loc[xs] > 0, color=S.ACCENT, alpha=0.12, lw=0)
a.fill_between(t, 0, cc.loc[xs], where=cc.loc[xs] < 0, color=S.COOL, alpha=0.15, lw=0)
a.axhline(0, color=S.INK2, lw=0.8); a.axvline(0, color=S.INK2, lw=0.8)
a.set_xlabel("hours from the bolus", fontsize=9, color=S.INK2)
a.legend(fontsize=8.5, frameon=False, loc="upper right")
a.set_title(f"Likely corrections: glucose ≥ 150 and not rising (median {cc.units:.1f} U)", loc="left", fontsize=10.5, color=S.INK)
S.title(fig, "Is there insulin-shaped structure in ICE around a bolus?",
        "Median of per-person medians, 15-min bins of clean ICE, yardstick ISF, no carb entries used. "
        "An ISF error would track the dotted curve; a timing error would cross zero as it decays.")
S.save(fig, "q08_bolus", tight=dict(left=0.06, right=0.98, top=0.82, bottom=0.12, wspace=0.18))
