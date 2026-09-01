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
    w = pd.read_csv(S.OUT / "wholerecord.csv")
    sf_path = S.OUT / "sensor_family.csv"
    sf = pd.read_csv(sf_path) if sf_path.exists() else pd.DataFrame(columns=["alias", "family"])

    fig, ax = S.figure(1, 3, figsize=(14.4, 4.9))
    cols = [S.color_for(co, a) for a in w["alias"]]

    S.strip_kde(ax[0], w["tir"], cols, fmt="{:.0f}%")
    ax[0].axvline(70, color=S.GREEN, lw=1.4, ls=(0, (4, 2)))
    ax[0].text(70, 1.14, " a common clinical target", fontsize=8.5, color=S.GREEN)
    ax[0].set_xlabel("time in range 70–180 (%)", fontsize=9.5, color=S.INK2)
    ax[0].set_title("Well-controlled, and spanning a wide range",
                    fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    for _, r in co.iterrows():
        ax[1].scatter(r["bg_mean"], r["bg_cv"], s=52, alpha=0.85, lw=1.1,
                      color=S.GROUP_COLOR.get(S.group_of(r), S.MUTED),
                      edgecolor=S.SURFACE, zorder=3)
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

    S.title(fig, "00 · Who this is",
            f"{len(w)} people wearing a CGM under an automated insulin-delivery system, {w['days'].sum():,.0f} person-days. "
            f"Time in range runs {w['tir'].min():.0f}% to {w['tir'].max():.0f}% with a median of {w['tir'].median():.0f}%, "
            f"so this is not one\nnarrow kind of person — but it is not a general diabetes population either: everyone here chose an automated system, "
            "donated their data, and kept it running. Age, sex,\ndiabetes duration and everything else about them is absent from the export.")
    S.save(fig, "00_population",
           dict(left=0.045, right=0.985, top=0.755, bottom=0.135, wspace=0.42))


if __name__ == "__main__":
    f00_population()
