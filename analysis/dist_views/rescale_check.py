#!/usr/bin/env python3
"""View 22 — how universal is each property?

Every property in this study has a population distribution, and its width is a
finding in its own right: some are near-constants across people, others are
personal enough that a cohort median describes nobody. This draws that
distribution for each, with the reference value marked where one exists.

Whole-record per person, not weekly blocks — a tail statistic depends on the
window it is measured over.
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

# (key, label, original 15-person min, max, reference value, reference label)
PANELS = [
    ("sd_over_mad", "increment SD / MAD", 1.406, 1.498, 1.414, "Laplace 1.414"),
    ("v_kurtosis", "increment excess kurtosis", 2.55, 13.21, 3.0, "Laplace 3.0"),
    ("hurst_short", "Hurst, 5–60 min", 0.50, 0.81, 0.5, "random walk 0.5"),
    ("hurst_long", "Hurst, 2–4 h", -0.02, 0.28, 0.5, "random walk 0.5"),
    ("boxcox_lambda", "Box-Cox λ", -0.50, 0.18, 0.0, "log (λ=0)"),
    ("sigma_meas", "sensor noise σ (mg/dL)", 0.18, 2.64, None, None),
    ("between_day_frac", "between-day variance share", 0.06, 0.32, None, None),
    ("bg_cv", "glucose CV (%)", None, None, 36.0, "36% threshold"),
]


def main() -> int:
    W = pd.read_csv(S.OUT / "wholerecord.csv")
    n = len(W)
    fig, ax = S.figure(2, 4, figsize=(15.0, 8.0))
    axf = ax.ravel()

    for A, (key, lab, lo0, hi0, ref, reflab) in zip(axf, PANELS):
        if key not in W:
            A.set_visible(False)
            continue
        v = W[key].dropna()
        orig = W[(W.grp == "orig")][key].dropna()
        new = W[(W.grp == "new")][key].dropna()
        gmin, gmax = v.min(), v.max()
        pad = 0.08 * (gmax - gmin + 1e-9)
        grid = np.linspace(gmin - pad, gmax + pad, 300)

        d = S.kde(v, grid)
        A.fill_between(grid, 0, d, color=S.MUTED, alpha=0.22, lw=0)
        A.plot(grid, d, color=S.INK2, lw=1.4)
        # rug: every person, so the sample size is visible not just asserted
        y0 = -0.10 * d.max()
        A.plot(v, np.full(len(v), y0), "|", color=S.COOL, ms=8, mew=1.1,
               alpha=0.65)
        if ref is not None:
            A.axvline(ref, color=S.GREEN, lw=1.5, ls=(0, (3, 3)))
            A.text(ref, 0.62, reflab, fontsize=7.6, color=S.GREEN, rotation=90,
                   ha="right", va="center", transform=A.get_xaxis_transform())
        A.axvline(v.median(), color=S.INK, lw=1.6)
        A.set_ylim(y0 * 2.2, d.max() * 1.16)
        A.set_yticks([])
        A.set_xlabel(lab, fontsize=9, color=S.INK2)
        extra = ""
        if ref is not None:
            share = 100 * float((v > ref).mean())
            extra = f"   ·   {share:.0f}% above {ref:g}"
        A.set_title(f"median {v.median():.3g}   ({v.min():.3g}–{v.max():.3g}){extra}",
                    fontsize=9, color=S.INK, loc="left", pad=5, weight="bold")

    for j in range(len(PANELS), len(axf)):
        axf[j].set_visible(False)
    S.title(fig, f"22 · How universal is each property?",
            f"Each statistic over every person's full record, {n} people. Black line = median, ticks = individual people, dashed green = the reference "
            "value where one exists.\nThe width of each distribution is the finding: not one person's increments are Gaussian and every one of them "
            "trends at short range, while the transform that\nnormalises glucose and the noise of the sensor vary several-fold from person to person.")
    S.save(fig, "22_scale_check",
           dict(left=0.03, right=0.99, top=0.845, bottom=0.075, hspace=0.34, wspace=0.14))

    print(f"{n} people")
    for key, lab, lo0, hi0, ref, _ in PANELS:
        if key not in W:
            continue
        v = W[key].dropna()
        note = ""
        if ref is not None:
            note = f"   {100*float((v > ref).mean()):.0f}% above {ref:g}"
        print(f"  {lab:<32} median {v.median():>7.3f}  "
              f"[{v.min():.3f}, {v.max():.3f}]{note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
