#!/usr/bin/env python3
"""q04 — ICE around twiist site changes. Reads site_event.csv, site_changes_scored.csv, site_null.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa

TAG = sys.argv[1] if len(sys.argv) > 1 else "site"           # "site" (twiist) or "pod" (Omnipod)
cv = pd.read_csv(S.OUT / "ice" / f"{TAG}_event.csv")
sc = pd.read_csv(S.OUT / "ice" / f"{TAG}_changes_scored.csv")
nl = pd.read_csv(S.OUT / "ice" / f"{TAG}_null.csv")
WHAT = {"site": ("site change", "cannula primed",
                 "twiist only (cannula primes); Omnipod uploads no site-change event.", "site"),
        "pod": ("pod change", "new pod paired",
                "Omnipod, pod changes inferred from runs of Loop's \"No pod paired\" errors.", "pod")}[TAG]
EARLY, ROUT = S.ACCENT, S.COOL
fig = S.plt.figure(figsize=(13, 8.4)); fig.patch.set_facecolor(S.SURFACE)
gs = fig.add_gridspec(2, 3, height_ratios=[1.2, 1], hspace=0.55, wspace=0.28)
a = S.axes(fig.add_subplot(gs[0, :2]))
for kind, col in (("routine", ROUT), ("early", EARLY)):
    c = cv[cv.kind == kind].sort_values("bin")
    sm = c.set_index("bin").ice_x.rolling(3, center=True, min_periods=1).mean()
    n = sc[sc.kind == kind]
    a.plot(sm.index + 0.25, sm.values, color=col, lw=2.2,
           label=f"{kind}: previous {WHAT[3]} lasted {'under' if kind == 'early' else 'at least'} 0.6× the person's usual ({len(n):,} changes, {n.alias.nunique()} people)")
a.axvline(0, color=S.INK, lw=1); a.axhline(0, color=S.INK2, lw=0.8)
a.text(0.15, 0.04, WHAT[1], transform=a.get_xaxis_transform(), fontsize=8.5, color=S.INK)
a.set_xlim(-24, 12); a.set_xticks(range(-24, 13, 3))
a.set_xlabel(f"hours from the {WHAT[0]}", fontsize=9, color=S.INK2)
a.set_ylabel("ICE above the person's usual\nat that hour, mg/dL per hour", fontsize=9, color=S.INK2)
a.legend(fontsize=8.5, frameon=False, loc="upper left")
a.set_title(f"Median ICE excess around a {WHAT[0]} (per-person median, then across people; 1.5-h smoothing)",
            loc="left", fontsize=10.5, color=S.INK)
a = S.axes(fig.add_subplot(gs[0, 2]))
for kind, col in (("routine", ROUT), ("early", EARLY)):
    c = cv[cv.kind == kind].sort_values("bin").set_index("bin")
    pre = c.loc[-6:-0.5]
    a.bar([f"{kind}\nvelocity", f"{kind}\ninsulin"], [pre.v_x.mean(), pre.ia_x.mean()], color=col, alpha=0.8)
a.axhline(0, color=S.INK2, lw=0.8)
a.set_ylabel("mean excess over the 6 h before, mg/dL/hr", fontsize=9, color=S.INK2)
a.tick_params(axis="x", labelsize=8)
a.set_title("Where the excess comes from", loc="left", fontsize=10.5, color=S.INK)
a = S.axes(fig.add_subplot(gs[1, :]))
x = np.linspace(-80, 200, 300)
for lab, vals, col, ls in (("random 6-h windows, ≥ 24 h from any change", nl.pre6_ice_x, S.MUTED, "--"),
                           (f"6 h before a routine {WHAT[0]}", sc[sc.kind == "routine"].pre6_ice_x, ROUT, "-"),
                           (f"6 h before an early {WHAT[0]}", sc[sc.kind == "early"].pre6_ice_x, EARLY, "-")):
    v = np.sort(vals.dropna().to_numpy())
    a.plot(x, 1 - np.searchsorted(v, x) / len(v), color=col, lw=2, ls=ls, label=lab)
q95 = nl.pre6_ice_x.quantile(.95)
a.axvline(q95, color=S.INK2, lw=0.8, ls=":")
a.text(q95 + 2, 0.5, f"random windows' 95th percentile ({q95:.0f})\nexceeded before {100*(sc[sc.kind=='early'].pre6_ice_x>q95).mean():.0f}% "
       f"of early and {100*(sc[sc.kind=='routine'].pre6_ice_x>q95).mean():.0f}% of routine changes", fontsize=8.5, color=S.INK2, va="center")
a.set_yscale("log"); a.set_ylim(0.005, 1.05)
a.set_xlabel("mean ICE excess over 6 h, mg/dL per hour", fontsize=9, color=S.INK2)
a.set_ylabel("share of windows at least this high", fontsize=9, color=S.INK2)
a.legend(fontsize=8.5, frameon=False, loc="lower left")
a.set_title("As a detector: the 6 hours before a change against ordinary 6-hour stretches", loc="left", fontsize=10.5, color=S.INK)
S.title(fig, {"site": "A failing site shows in ICE, but faintly",
              "pod": "Around an Omnipod pod change"}[TAG],
        WHAT[2] + " Excess = 30-min ICE minus the same person's median at that local hour.")
S.save(fig, {"site": "q04_site", "pod": "q05_pod"}[TAG], tight=dict(left=0.07, right=0.98, top=0.86, bottom=0.07))
