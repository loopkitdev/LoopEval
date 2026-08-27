#!/usr/bin/env python3
"""Reading views for the elbow-densified k sweep.

`frontier.plot_sweeps` draws the canonical sweep figure and is what the full-range
plots come from. These are two complementary reading views it does not cover:

  A  the elbow, zoomed, both beds side by side — at 0.025 resolution the curves
     bunch into a corner of the full-range plot and the structure is unreadable
  B  lift against dial setting, which is the direct way to see WHERE a candidate
     beats the reference and whether the two beds agree about it

Both keep the house axis convention (x = TIR increasing right, y = t<54 increasing
UP so worse is up) and order every sweep line by its dial multiplier, never by TIR.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt                              # noqa: E402
import style as S                                            # noqa: E402
from loopeval_analysis import frontier as FR                 # noqa: E402
from loopeval_analysis.plotting import tir_t54_axes          # noqa: E402

RUN = Path.home() / "dev/LoopEvalScenarios/runs/2026-08-25-distributions/ksweep"
KCOL = {0.25: "#3b6ea5", 0.5: "#1baf7a", 1.0: "#eb6834", 2.0: "#8b5cf6"}
ELBOW = (0.925, 1.025)          # where bddp11's positive band sits


def load() -> pd.DataFrame:
    return pd.read_csv(RUN / "scores.csv")


def sweep_line(ax, sub: pd.DataFrame, color, label, lw=1.9, ms=4.5, zorder=3):
    """Order by MULTIPLIER — adjacent vertices must be adjacent settings."""
    s = sub.sort_values("multiplier")
    ax.plot(s.TIR, s.t54, color=color, lw=lw, marker="o", ms=ms,
            label=label, zorder=zorder, alpha=0.92)
    return s


def fig_zoom(D: pd.DataFrame):
    donors = ["bddp11", "bddp10"]
    fig, ax = S.figure(1, 2, figsize=(14.2, 6.2))
    for A, donor in zip(ax, donors):
        sub = D[D.donor == donor]
        ref = sub[sub.k == 0]
        hi = float(np.nanpercentile(
            sub[sub.multiplier <= 1.05].t54, 97)) * 1.35 + 0.05
        tir_t54_axes(A, ylim=(0.0, max(hi, 0.45)), budget=None)
        # shade the densified elbow band
        band = ref[(ref.multiplier >= ELBOW[0] - 1e-9) &
                   (ref.multiplier <= ELBOW[1] + 1e-9)].sort_values("multiplier")
        if len(band):
            A.axvspan(band.TIR.min(), band.TIR.max(), color=S.WARM, alpha=0.08, lw=0)
            A.text(band.TIR.mean(), A.get_ylim()[1] * 0.965,
                   f"elbow, ×{ELBOW[0]}–{ELBOW[1]}", fontsize=8.5, color=S.WARM,
                   ha="center", va="top")
        sweep_line(A, ref, S.MUTED, "stock (k=0)", lw=2.6, ms=5.5, zorder=2)
        for k in sorted(x for x in sub.k.unique() if x > 0):
            sweep_line(A, sub[sub.k == k], KCOL.get(k, S.INK), f"VSB k={k}")
        # label the reference knots so the dial setting is readable
        for _, r in ref.sort_values("multiplier").iterrows():
            if r.multiplier in (0.90, 0.95, 1.00, 1.05):
                A.annotate(f"×{r.multiplier:g}", (r.TIR, r.t54),
                           textcoords="offset points", xytext=(4, -11),
                           fontsize=7.5, color=S.MUTED)
        A.set_xlim(sub[sub.multiplier.between(0.86, 1.06)].TIR.min() - 1.2,
                   sub[sub.multiplier.between(0.86, 1.06)].TIR.max() + 1.2)
        A.set_title(f"{donor}", fontsize=11.5, color=S.INK, loc="left",
                    pad=7, weight="bold")
        A.legend(frameon=False, fontsize=8.5, labelcolor=S.INK2, loc="upper left")
    S.title(fig, "Elbow, zoomed — where the candidate lines cross the reference",
            "Same data as the full-range sweeps, restricted to the densified region. Better is toward the LOWER RIGHT. On bddp11 the k=0.25 and k=0.5 "
            "lines dip BELOW the stock line\nthrough the shaded band; on bddp10 they do not, and the higher gains sit clearly above it. Lines are "
            "ordered by dial multiplier, so adjacent dots are adjacent settings.")
    S.save(fig, "17_elbow_zoom",
           dict(left=0.055, right=0.99, top=0.80, bottom=0.10, wspace=0.20))
    import shutil
    shutil.copy(S.FIG / "17_elbow_zoom.png", RUN / "elbow_zoom.png")


def fig_lift_profile(D: pd.DataFrame):
    donors = ["bddp11", "bddp10"]
    fig, ax = S.figure(1, 2, figsize=(14.2, 5.8), sharey=True)
    for A, donor in zip(ax, donors):
        sub = D[D.donor == donor]
        ref = sub[sub.k == 0].sort_values("multiplier")
        for k in sorted(x for x in sub.k.unique() if x > 0):
            cand = sub[sub.k == k].sort_values("multiplier")
            lifts = np.array([FR.lift(ref, r.TIR, r.t54)
                              for r in cand.itertuples()], dtype=float)
            m = cand.multiplier.to_numpy()
            # endpoints project onto a polyline END and are distorted — draw
            # them hollow so they are visibly not part of the evidence
            A.plot(m[1:-1], lifts[1:-1], color=KCOL.get(k, S.INK), lw=1.9,
                   marker="o", ms=5, label=f"k={k}")
            A.plot(m[[0, -1]], lifts[[0, -1]], color=KCOL.get(k, S.INK),
                   lw=0, marker="o", ms=5, mfc="none", alpha=0.55)
        A.axhline(0, color=S.INK, lw=1.5)
        A.axvspan(ELBOW[0], ELBOW[1], color=S.WARM, alpha=0.10, lw=0)
        A.set_xlabel("insulin-needs multiplier", fontsize=9.5, color=S.INK2)
        A.set_title(donor, fontsize=11.5, color=S.INK, loc="left", pad=7,
                    weight="bold")
        A.legend(frameon=False, fontsize=8.5, labelcolor=S.INK2, ncol=2)
    ax[0].set_ylabel("lift vs stock  (+ = better)", fontsize=9.5, color=S.INK2)
    ax[0].set_ylim(-0.12, 0.09)
    S.title(fig, "Lift against dial setting — where the mechanism wins, and whether the two beds agree",
            "The direct read. Above the black line the candidate beats the stock sweep at that setting. bddp11 has a contiguous positive band across "
            "the shaded elbow, holding\nfor three different gains. bddp10 is NEGATIVE through the same band and puts its own small positive region "
            "elsewhere. Hollow markers are the sweep endpoints,\nwhose projection onto the end of the reference polyline is distorted — they are excluded from every mean.")
    S.save(fig, "18_lift_profile",
           dict(left=0.06, right=0.99, top=0.775, bottom=0.115, wspace=0.08))
    import shutil
    shutil.copy(S.FIG / "18_lift_profile.png", RUN / "lift_profile.png")


def main() -> int:
    D = load()
    fig_zoom(D)
    fig_lift_profile(D)
    print(f"also copied to {RUN}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
