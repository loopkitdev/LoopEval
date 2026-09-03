#!/usr/bin/env python3
"""View 00 — who is in this study.

Every other figure describes glucose; this one describes the people whose glucose
it is, so a reader can judge what the numbers generalise to. Reads cohort.csv,
wholerecord.csv and sensor_family.csv (the per-donor sensor label recovered from
the source `deviceId`; aliases only).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt                          # noqa: E402
import style as S                                        # noqa: E402


def f00_population():
    co = S.cohort()
    ho = S.cohort("hands-off")
    w = pd.read_csv(S.OUT / "wholerecord.csv")
    sf_path = S.OUT / "sensor_family.csv"
    sf = pd.read_csv(sf_path) if sf_path.exists() else pd.DataFrame(columns=["alias", "family"])

    fig, ax = S.figure(1, 3, figsize=(14.4, 4.9))
    cols = [S.color_for(co, a) for a in w["alias"]]

    # The pool these people were drawn from, drawn behind them: every Tidepool
    # donor on an automated system, same window, same statistic.
    pool_path = S.OUT / "pool_compare.csv"
    if pool_path.exists():
        pool = pd.read_csv(pool_path)
        pool = pool[pool["aid"].astype(str).str.lower().isin(("true", "1"))]
        gx = np.linspace(20, 100, 240)
        gy = S.kde(pool["tir"].dropna(), gx)
        gy = gy / max(gy.max(), 1e-12)
        ax[0].fill_between(gx, 0, gy, color=S.MUTED, alpha=0.20, lw=0, zorder=0)
        ax[0].plot(gx, gy, color=S.MUTED, lw=1.6, zorder=0,
                   label=f"all {len(pool):,} donors on an automated system")
    S.strip_kde(ax[0], w["tir"], cols, fmt="{:.0f}%")
    # The over-sampled stratum, on its own row so it is never mistaken for part
    # of the pool-matched core.
    if len(ho):
        rng = np.random.default_rng(11)
        ax[0].scatter(ho["tir"], -0.62 - rng.uniform(0, 0.12, len(ho)), s=26,
                      color=S.ACCENT, alpha=0.85, lw=0, zorder=3)
        ax[0].plot([ho["tir"].median()] * 2, [-0.78, -0.50], color=S.ACCENT, lw=2.4)
        ax[0].text(0.985, 0.055, f"hands-off stratum, {len(ho)} people",
                   transform=ax[0].transAxes, ha="right", va="center",
                   fontsize=8.5, color=S.ACCENT)
        ax[0].set_ylim(-0.86, 1.26)
    if pool_path.exists():
        ax[0].plot([], [], color=S.COOL, lw=2.0, label=f"the {len(w)} people here")
        ax[0].legend(frameon=False, fontsize=8, labelcolor=S.INK2, loc="upper left")
    ax[0].set_xlim(35, 105)
    ax[0].set_xlabel("time in range 70–180 (%)", fontsize=9.5, color=S.INK2)
    ax[0].set_title("The same shape as the pool they came from",
                    fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    for _, r in co.iterrows():
        ax[1].scatter(r["bg_mean"], r["bg_cv"], s=52, alpha=0.85, lw=1.1,
                      color=S.GROUP_COLOR.get(S.group_of(r), S.MUTED),
                      edgecolor=S.SURFACE, zorder=3)
    if len(ho):
        ax[1].scatter(ho["bg_mean"], ho["bg_cv"], s=62, marker="D", lw=1.4,
                      facecolor="none", edgecolor=S.ACCENT, zorder=4,
                      label="hands-off stratum")
        ax[1].legend(frameon=False, fontsize=8, labelcolor=S.INK2, loc="lower right")
    ax[1].axhline(36, color=S.ACCENT, lw=1.3, ls=(0, (3, 3)))
    ax[1].text(0.99, 36, "CV 36% ", fontsize=8, color=S.ACCENT, ha="right",
               va="bottom", transform=ax[1].get_yaxis_transform())
    ax[1].set_xlabel("mean glucose (mg/dL)", fontsize=9.5, color=S.INK2)
    ax[1].set_ylabel("CV of glucose (%)", fontsize=9.5, color=S.INK2)
    ax[1].set_title("Level and variability, one dot per person",
                    fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # Composition: what kind of people, kit and behaviour this is.
    bars, labels, colors = [], [], []
    fam = sf["family"].value_counts() if len(sf) else pd.Series(dtype=int)
    for k in ("Libre 3 (twiist)", "Dexcom G7", "Dexcom G6", "unlabelled"):
        if k in fam:
            bars.append(fam[k]); labels.append(f"sensor: {k}"); colors.append(S.COOL)
    for k, v in co["strategy"].value_counts().items():
        bars.append(v); labels.append(f"dosing: {'temp basal' if k == 'temp' else 'auto-bolus'}")
        colors.append(S.WARM)
    for k, v in co["archetype"].fillna("unknown").value_counts().items():
        bars.append(v); labels.append(f"carbs: {k}")
        colors.append(S.GROUP_COLOR.get(k, S.MUTED))
    y = np.arange(len(bars))[::-1]
    ax[2].barh(y, bars, color=colors, alpha=0.9, height=0.72)
    for yi, b in zip(y, bars):
        ax[2].text(b + 0.6, yi, str(b), va="center", fontsize=8.5, color=S.INK2)
    ax[2].set_yticks(y)
    ax[2].set_yticklabels(labels, fontsize=8.5, color=S.INK2)
    ax[2].set_xlim(0, max(bars) * 1.16)
    ax[2].set_xlabel("people", fontsize=9.5, color=S.INK2)
    ax[2].set_title("Everyone runs an automated system", fontsize=10.5, color=S.INK,
                    loc="left", pad=6, weight="bold")

    ho_note = (f"\nA further {len(ho)} people (orange) were sampled deliberately rather than at random: they announce almost no carbohydrate, let automation do the bolusing, "
               f"and their median time in range is {ho['tir'].median():.0f}%.\nEvery other figure in this document describes the {len(w)}.") if len(ho) else ""
    S.title(fig, "00 · Who this is",
            f"{len(w)} people wearing a CGM under an automated insulin-delivery system, {w['days'].sum():,.0f} person-days. "
            f"Time in range runs {w['tir'].min():.0f}% to {w['tir'].max():.0f}% with a median of {w['tir'].median():.0f}%, "
            f"so this is not one\nnarrow kind of person — but it is not a general diabetes population either: everyone here chose an automated system, "
            "donated their data, and kept it running. Age, sex,\ndiabetes duration and everything else about them is absent from the export." + ho_note)
    S.save(fig, "00_population",
           dict(left=0.045, right=0.985, top=0.695, bottom=0.135, wspace=0.42))


if __name__ == "__main__":
    f00_population()
