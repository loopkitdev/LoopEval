#!/usr/bin/env python3
"""Figure 28 — insulin delivery against age.

Age is a first-order covariate for insulin: a child's requirement is a fraction
of an adult's, and a growing child's requirement should RISE over a four-month
window in a way an adult's should not. Both are testable here, and the second
is the more interesting because it is a prediction rather than a restatement.

Reads age.csv (pull_age.py) and delivery.csv (delivery.py). Every published
number is aggregate; ages are approximate because a Tidepool profile birthday
can belong to the account holder rather than the wearer.

Run:  python3 age_views.py
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

# Developmental bands, not a scatter against age. The relationship is NOT
# monotone — under-13s are low, adolescents are the highest of anyone, adults
# are flat — so a rank correlation across the whole range reports rho = -0.06
# and hides the structure entirely.
BANDS = [0, 13, 18, 26, 50, 200]
LABELS = ["<13", "13–17", "18–25", "26–49", "50+"]
# A 114-day AID record at 60+ U/day cannot belong to a two-year-old, so an age
# below this is the account holder's date, not the wearer's.
MIN_PLAUSIBLE = 3.0

PANELS = [
    ("tdd", "total daily dose (U)", "{:.1f}", False),
    ("zero_frac", "5-min bins delivering nothing (%)", "{:.1f}", False),
    ("trend_pct_30d", "drift (% of own mean / 30 d)", "{:+.1f}", True),
]

# Age is confounded with the pump: Omnipod users are a median 24 and twiist
# users 41, so any pooled age gradient has to be re-tested inside one pump
# before it can be called age. `within_pump` prints that test on the panel.
def within_pump(have, col):
    """The SAME banded test the panel runs, restricted to one pump.

    Using a rank correlation here instead would apply the monotone statistic
    this figure exists to reject.
    """
    try:
        from scipy.stats import kruskal
    except ImportError:
        return ""
    out = []
    for pu, g in have.groupby("pump"):
        if len(g) < 25:
            continue
        gs = [x[col].dropna().to_numpy() for _, x in g.groupby("band", observed=True)]
        gs = [x for x in gs if len(x) >= 3]
        if len(gs) < 3:
            continue
        out.append(f"{pu} p={kruskal(*gs).pvalue:.2f}")
    return "within pump: " + ", ".join(out) if out else ""


def load():
    co = S.cohort()
    ag = pd.read_csv(S.OUT / "age.csv")
    dl = pd.read_csv(S.OUT / "delivery.csv")
    m = (dl.merge(ag[["alias", "age_years", "age_group", "grantor"]],
                  on="alias", how="left")
           .merge(co[["alias", "pump", "strategy", "archetype", "tir"]],
                  on="alias", how="left"))
    return co, m


def f28(co, m):
    have = m[m["age_years"].notna()].copy()
    dropped = int((have["age_years"] < MIN_PLAUSIBLE).sum())
    have = have[have["age_years"] >= MIN_PLAUSIBLE]
    have["band"] = pd.cut(have["age_years"], BANDS, labels=LABELS, right=False)
    fig, ax = S.figure(1, 4, figsize=(15.6, 5.0))

    # (a) who is in the cohort, by age
    S.strip_kde(ax[0], have["age_years"],
                [S.color_for(co, a) for a in have["alias"]], fmt="{:.0f}")
    ax[0].axvline(18, color=S.MUTED, lw=1.4, ls=(0, (4, 2)))
    ax[0].text(18, 1.14, " 18", fontsize=8.5, color=S.MUTED, ha="left")
    ax[0].set_xlabel("age at the window midpoint (years)", fontsize=9.5, color=S.INK2)
    ax[0].set_title("The cohort is young", fontsize=10.5, color=S.INK,
                    loc="left", pad=6, weight="bold")
    n_minor = int((have["age_years"] < 18).sum())
    ax[0].text(0.97, 0.06, f"{n_minor} of {len(have)} under 18",
               transform=ax[0].transAxes, fontsize=8.5, color=S.MUTED, ha="right")

    # (b)-(d) each delivery statistic by developmental band
    rng = np.random.default_rng(0)
    try:
        from scipy.stats import kruskal
    except ImportError:
        kruskal = None
    for i, (col, lab, fmt, zero_line) in enumerate(PANELS, start=1):
        A = ax[i]
        groups, meds = [], []
        for j, lb in enumerate(LABELS):
            v = have.loc[have["band"].eq(lb), col].dropna().to_numpy()
            groups.append(v)
            if not len(v):
                meds.append(np.nan)
                continue
            meds.append(np.median(v))
            A.scatter(rng.normal(j, 0.07, len(v)), v, s=26, color=S.COOL,
                      alpha=0.7, edgecolor=S.SURFACE, lw=0.6, zorder=3)
            A.plot([j - 0.26, j + 0.26], [np.median(v)] * 2, color=S.INK, lw=2.2,
                   zorder=5, solid_capstyle="round")
            A.annotate(fmt.format(np.median(v)), (j, np.median(v)),
                       textcoords="offset points", xytext=(0, 7), ha="center",
                       fontsize=8, color=S.INK, zorder=6)
        A.plot(range(len(LABELS)), meds, color=S.ACCENT, lw=1.5, alpha=0.8, zorder=4)
        if zero_line:
            A.axhline(0, color=S.INK, lw=1.2, ls=(0, (4, 2)), zorder=2)
        big = [g for g in groups if len(g) >= 3]
        if kruskal and len(big) >= 3:
            p = kruskal(*big).pvalue
            txt = (f"across bands, p = {p:.3f}" if p < 0.1
                   else f"across bands, p = {p:.2f}")
            wp = within_pump(have, col)
            if wp:
                txt += "\n" + wp
            A.text(0.03, 0.97, txt, transform=A.transAxes, fontsize=8.5,
                   color=S.INK2, va="top", linespacing=1.5, zorder=7,
                   bbox=dict(facecolor=S.SURFACE, edgecolor="none",
                             alpha=0.9, boxstyle="round,pad=0.3"))
        A.set_xticks(range(len(LABELS)))
        A.set_xticklabels([f"{lb}\nn={len(g)}" for lb, g in zip(LABELS, groups)],
                          fontsize=8.5, color=S.INK2)
        A.set_xlim(-0.55, len(LABELS) - 0.45)
        A.set_ylabel(lab, fontsize=9.5, color=S.INK2)
        A.set_title(lab.split(" (")[0].capitalize(), fontsize=10.5, color=S.INK,
                    loc="left", pad=6, weight="bold")
        S.axes(A)

    a = have["age_years"]
    S.title(fig, "28 · Insulin against age",
            f"Age is available for {len(have)} of the {len(m)} people with delivery data — median "
            f"{a.median():.0f}, {n_minor} under 18. Read from the account profile, which can carry\nthe "
            f"account holder's date rather than the wearer's: two records giving an age under three "
            f"alongside an adult daily dose were dropped as exactly that.\nBands rather than a line "
            "because the relationship is not monotone — the under-13s are the lowest and the "
            "adolescents the highest of anyone.")
    S.save(fig, "28_age",
           dict(left=0.045, right=0.99, top=0.785, bottom=0.145, wspace=0.28))


def main() -> int:
    co, m = load()
    have = m[m["age_years"].notna()]
    print(f"  age for {len(have)} of {len(m)} people with delivery data")
    imp = have[have["age_years"] < MIN_PLAUSIBLE]
    if len(imp):
        print(f"  ! {len(imp)} implausible (age < {MIN_PLAUSIBLE:.0f} with an adult "
              f"daily dose) — the profile date is the account holder's:")
        print(imp[["alias", "age_years", "tdd"]].round(1).to_string(index=False)
              .replace("\n", "\n    "))
    have = have[have["age_years"] >= MIN_PLAUSIBLE]
    if not len(have):
        return 1
    a = have["age_years"]
    print(f"  median {a.median():.1f}  p10-p90 {a.quantile(.1):.0f}-{a.quantile(.9):.0f}"
          f"  range {a.min():.0f}-{a.max():.0f}   under 18: {int((a < 18).sum())}")
    from scipy.stats import spearmanr, mannwhitneyu, kruskal
    have = have.assign(band=pd.cut(have["age_years"], BANDS, labels=LABELS,
                                   right=False))
    print("\n  medians by developmental band:")
    print(have.groupby("band", observed=True)[
        ["tdd", "tdd_cv", "zero_frac", "conc1", "trend_pct_30d", "tir"]]
        .median().round(2).to_string().replace("\n", "\n    "))
    print("\n  across bands (Kruskal-Wallis):")
    for c_ in ("tdd", "tdd_cv", "zero_frac", "conc1", "trend_pct_30d", "tir"):
        g = [x[c_].dropna().to_numpy() for _, x in have.groupby("band", observed=True)]
        g = [x for x in g if len(x) >= 3]
        print(f"    {c_:14s} p = {kruskal(*g).pvalue:.4f}")
    print("\n  delivery statistics against age (rank, whole range):")
    for c_ in ("tdd", "tdd_cv", "zero_frac", "conc1", "med_nonzero",
               "trend_pct_30d", "ac1", "tir"):
        if c_ not in have:
            continue
        d = have[[c_, "age_years"]].dropna()
        rho, p = spearmanr(d["age_years"], d[c_])
        y, o = d.loc[d.age_years < 18, c_], d.loc[d.age_years >= 18, c_]
        extra = ""
        if len(y) >= 5 and len(o) >= 5:
            extra = (f"   <18 {y.median():8.2f} vs adult {o.median():8.2f}"
                     f"  p={mannwhitneyu(y, o).pvalue:.3f}")
        print(f"    {c_:14s} rho {rho:+.2f}  p={p:.3f}{extra}")
    print("\n  is age confounded with the device split?")
    for c_ in ("pump", "strategy", "archetype"):
        if c_ in have:
            print(f"    {c_}: " + "  ".join(
                f"{k} {v:.0f}" for k, v in have.groupby(c_)["age_years"].median().items()))
    print(f"\n  age availability by pump: "
          f"{m.assign(has=m.age_years.notna()).groupby('pump')['has'].mean().round(2).to_dict()}")
    f28(co, m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
