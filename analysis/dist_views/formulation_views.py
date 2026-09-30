#!/usr/bin/env python3
"""Does the insulin formulation change how delivery looks?

Figure 27. Reads formulation.csv (from pull_formulation.py) and delivery.csv
(from delivery.py) and compares the delivery statistics between RAPID analogues
(Novolog, Humalog, Admelog, Apidra) and ULTRA-RAPID ones (Fiasp, Lyumjev).

Two cautions the figure has to carry. Formulation is a CHOICE, not an
assignment: whoever is on Fiasp chose it, or their clinic did, so any difference
between the groups mixes the insulin with the person. And formulation is what
sets the activity curve the export convolves with, so an ultra-rapid donor
exported as rapid has mis-timed activity — which makes this a data-integrity
check as much as a finding.

Run:  python3 formulation_views.py
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

CAT_COLOR = {"rapid": S.COOL, "ultra-rapid": S.ACCENT, "inhaled": S.MUTED}
# What the panels compare, and how to print it.
FIELDS = [
    ("tdd", "total daily dose (U)", "{:.1f}"),
    ("tdd_cv", "day-to-day variation in it (CV %)", "{:.1f}"),
    ("zero_frac", "5-min bins delivering nothing (%)", "{:.1f}"),
    ("conc1", "insulin in the busiest 1% of bins (%)", "{:.1f}"),
    ("med_nonzero", "median non-zero bin (U)", "{:.3f}"),
    ("trend_pct_30d", "drift (% of own mean / 30 d)", "{:+.1f}"),
]


def load():
    co = S.cohort()
    f = pd.read_csv(S.OUT / "formulation.csv")
    d = pd.read_csv(S.OUT / "delivery.csv")
    m = (d.merge(f[["alias", "brand", "category"]], on="alias", how="left")
          .merge(co[["alias", "strategy", "pump", "sensor", "archetype", "tir"]],
                 on="alias", how="left"))
    m["category"] = m["category"].fillna("unrecorded")
    return co, m


def f27(co, m):
    fig, ax = S.figure(2, 3, figsize=(14.4, 8.2))
    axf = ax.ravel()
    use = m[m["category"].isin(("rapid", "ultra-rapid"))]
    for i, (col, lab, fmt) in enumerate(FIELDS):
        A = axf[i]
        groups, labels, cols = [], [], []
        for cat in ("rapid", "ultra-rapid"):
            v = use.loc[use["category"].eq(cat), col].dropna()
            if len(v) >= 3:
                groups.append(v.to_numpy())
                labels.append(f"{cat}\nn={len(v)}")
                cols.append(CAT_COLOR[cat])
        if len(groups) < 2:
            A.set_visible(False)
            continue
        rng = np.random.default_rng(0)
        for j, (v, c) in enumerate(zip(groups, cols)):
            A.scatter(rng.normal(j, 0.055, len(v)), v, s=30, color=c, alpha=0.75,
                      edgecolor=S.SURFACE, lw=0.7, zorder=3)
            A.plot([j - 0.24, j + 0.24], [np.median(v)] * 2, color=S.INK, lw=2.2,
                   zorder=4, solid_capstyle="round")
            A.plot([j, j], np.percentile(v, [10, 90]), color=S.INK, lw=1.0,
                   alpha=0.5, zorder=3)
        try:
            from scipy.stats import mannwhitneyu
            p = mannwhitneyu(groups[0], groups[1]).pvalue
            ptxt = f"p = {p:.2f}" if p >= 0.01 else f"p = {p:.1g}"
        except ImportError:
            ptxt = ""
        A.text(0.5, 0.97, f"{fmt.format(np.median(groups[0]))} vs "
               f"{fmt.format(np.median(groups[1]))}   {ptxt}",
               transform=A.transAxes, fontsize=8.5, color=S.INK2, ha="center",
               va="top", zorder=7,
               bbox=dict(facecolor=S.SURFACE, edgecolor="none", alpha=0.9,
                         boxstyle="round,pad=0.3"))
        A.set_xticks(range(len(labels)))
        A.set_xticklabels(labels, fontsize=8.5, color=S.INK2)
        A.set_xlim(-0.5, len(labels) - 0.5)
        A.set_ylabel(lab, fontsize=9.5, color=S.INK2)
        S.axes(A)

    n_r = int(use["category"].eq("rapid").sum())
    n_u = int(use["category"].eq("ultra-rapid").sum())
    unrec = int(m["category"].eq("unrecorded").sum())
    # State how comparable the two groups are, rather than picking whichever
    # row sorts first and calling it a difference.
    def share(col, val):
        t = pd.crosstab(use[col], use["category"], normalize="columns") * 100
        if val not in t.index:
            return None
        return f"{val} {t.loc[val, 'rapid']:.0f}% vs {t.loc[val, 'ultra-rapid']:.0f}%"
    conf = [x for x in (share("strategy", "bolus"), share("pump", "Omnipod"),
                        share("sensor", "Dexcom G7")) if x]
    S.title(fig, "27 · Rapid against ultra-rapid",
            f"The recorded insulin brand, from the source rather than the model preset: {n_r} people on a rapid analogue "
            f"(Novolog, Humalog, Admelog, Apidra),\n{n_u} on an ultra-rapid one (Fiasp, Lyumjev), {unrec} with no brand "
            "recorded at all. One point per person, bar = median, whisker = p10–p90.\nFormulation is a choice, so a "
            "difference here mixes the insulin with whoever chose it, though the two groups\nare closely matched on "
            + ("; ".join(conf) if conf else "the other device variables")
            + ". The deeper limit is that a brand is only recorded by the Omnipod upload path: "
            "every one of the\nunrecorded donors is a twiist user, so this comparison describes "
            "the Omnipod half of the cohort and is silent about the other half.")
    S.save(fig, "27_formulation",
           dict(left=0.055, right=0.985, top=0.82, bottom=0.065, hspace=0.30, wspace=0.26))


def main() -> int:
    co, m = load()
    print("  category counts:", m["category"].value_counts().to_dict())
    print("  brands:", m[m.brand.notna()].brand.value_counts().to_dict())
    print("\n  medians by category:")
    print(m.groupby("category")[[c for c, _, _ in FIELDS] + ["tir"]]
           .median().round(3).to_string().replace("\n", "\n    "))
    print("\n  what else differs (row % within category):")
    for c in ("strategy", "pump", "sensor", "archetype"):
        if c in m:
            t = pd.crosstab(m[c], m["category"])
            print(f"\n  {c}:")
            print(t.to_string().replace("\n", "\n    "))
    f27(co, m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
