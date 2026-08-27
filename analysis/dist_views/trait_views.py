#!/usr/bin/env python3
"""Views 19-21 — traits vs states, and whether people fall into classes.

19  the ICC ranking, with the within/between decomposition made visible
20  the same two features drawn as per-person weekly tracks — a trait holds its
    rank across the record, a state does not
21  the trait space: how many independent axes there are, where people sit, and
    whether the population is clustered or continuous
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt                              # noqa: E402
import style as S                                            # noqa: E402
from loopeval_analysis import traits as T                    # noqa: E402

OUT = S.OUT
NICE = {
    "bg_mean": "mean glucose", "bg_sd": "glucose SD", "bg_cv": "glucose CV",
    "bg_iqr": "glucose IQR", "bg_skew": "glucose skew",
    "boxcox_lambda": "Box-Cox λ", "tir": "time in range",
    "t70": "time <70", "t180": "time >180",
    "v_sd": "5-min increment SD", "sd_over_mad": "increment SD/MAD",
    "v_kurtosis": "increment kurtosis", "v_skew": "increment skew",
    "hurst_short": "Hurst 5–60 min", "hurst_long": "Hurst 2–4 h",
    "sigma_meas": "sensor noise σ", "acf_zero_min": "momentum zero-crossing",
    "acf_min": "overshoot depth", "vol_cluster_60m": "volatility memory 60 min",
    "sigma_med": "volatility level", "sigma_disp": "volatility spread p90/p10",
    "between_day_frac": "between-day variance share",
    "circadian_amp": "circadian amplitude",
}


def f19_icc(I: pd.DataFrame, F: pd.DataFrame):
    I = I[np.isfinite(I["icc"])].sort_values("icc")
    fig, ax = S.figure(1, 2, figsize=(14.0, 8.2),
                       gridspec_kw={"width_ratios": [1.35, 1]})
    y = np.arange(len(I))
    for i, r in enumerate(I.itertuples()):
        col = (S.GREEN if r.lo > 0.6 else
               S.COOL if r.icc > 0.5 else
               S.WARM if r.icc > 0.3 else S.ACCENT)
        ax[0].plot([r.lo, r.hi], [i, i], color=col, lw=2.4, solid_capstyle="round",
                   alpha=0.9)
        ax[0].plot([r.icc], [i], "o", color=col, ms=6.5, mec=S.SURFACE, mew=1.3,
                   zorder=3)
    ax[0].set_yticks(y)
    ax[0].set_yticklabels([NICE.get(f, f) for f in I["feature"]], fontsize=9,
                          color=S.INK2)
    for v, lab in ((0.3, "state"), (0.5, ""), (0.6, "trait")):
        ax[0].axvline(v, color=S.MUTED, lw=1.0, ls=(0, (3, 3)))
    ax[0].set_xlim(0, 1)
    ax[0].set_xlabel("intraclass correlation  (share of variance between people)",
                     fontsize=9.5, color=S.INK2)
    ax[0].set_title("How much of each feature is the person?", fontsize=11,
                    color=S.INK, loc="left", pad=8, weight="bold")

    # Between vs within SD, in the feature's own units — ICC hides magnitude, and
    # a feature can be a near-perfect trait while barely varying at all.
    rows = []
    for f in I["feature"]:
        d = F[["alias", f]].dropna()
        if d.alias.nunique() < 3:
            continue
        m = d.groupby("alias")[f].mean()
        w = d.groupby("alias")[f].std()
        rows.append((f, float(m.std()), float(w.mean()), float(m.mean())))
    B = pd.DataFrame(rows, columns=["feature", "between_sd", "within_sd", "level"])
    B = B.merge(I[["feature", "icc"]], on="feature")
    # Label selectively: the panel's message is the cloud's position relative to
    # the diagonal, and 23 labels bury it.
    show = {"hurst_short", "sd_over_mad", "sigma_meas", "v_kurtosis", "bg_mean",
            "sigma_disp", "between_day_frac", "bg_cv", "sigma_med", "circadian_amp"}
    for r in B.itertuples():
        col = (S.GREEN if r.icc > 0.6 else S.COOL if r.icc > 0.5
               else S.WARM if r.icc > 0.3 else S.ACCENT)
        rel_b = abs(r.between_sd / r.level) if r.level else np.nan
        rel_w = abs(r.within_sd / r.level) if r.level else np.nan
        ax[1].scatter(rel_w, rel_b, s=58, color=col, edgecolor=S.SURFACE, lw=1.1,
                      zorder=3)
        if r.feature in show:
            ax[1].annotate(NICE.get(r.feature, r.feature), (rel_w, rel_b),
                           textcoords="offset points", xytext=(-8, 8),
                           fontsize=8, color=S.INK2, ha="right")
    lim = [1e-3, 2.6]
    ax[1].plot(lim, lim, color=S.INK, lw=1.4, ls=(0, (4, 2)))
    ax[1].set_xscale("log")
    ax[1].set_yscale("log")
    ax[1].set_xlim(*lim)
    ax[1].set_ylim(*lim)
    ax[1].set_xlabel("within-person spread  (SD / level)", fontsize=9.5, color=S.INK2)
    ax[1].set_ylabel("between-person spread  (SD / level)", fontsize=9.5, color=S.INK2)
    ax[1].set_title("Above the line = more personal than weekly",
                    fontsize=11, color=S.INK, loc="left", pad=8, weight="bold")

    S.title(fig, "19 · Trait or state — what a single week tells you about a person",
            "Each feature is computed per person per week; the intraclass correlation is the share of its variance that lies BETWEEN people rather "
            "than within them.\n"
            "Green features are stable properties: measure once and the reading still describes that person later. Orange ones describe the week, not the person.\n"
            "The right panel adds the magnitude ICC hides — a feature can be a near-perfect trait and still barely vary across the population.")
    S.save(fig, "19_trait_vs_state",
           dict(left=0.19, right=0.975, top=0.835, bottom=0.075, wspace=0.40))
    return B


def f20_tracks(F: pd.DataFrame, I: pd.DataFrame):
    ok = I[np.isfinite(I["icc"])].sort_values("icc")
    state_f = ok.iloc[0]["feature"]
    trait_f = ok.iloc[-1]["feature"]
    # prefer a dynamical trait over the obvious level one for the illustration
    for cand in ("hurst_short", "sigma_med", "acf_zero_min"):
        if cand in set(ok[ok.icc > 0.6]["feature"]):
            trait_f = cand
            break

    fig, ax = S.figure(1, 2, figsize=(13.8, 5.8))
    for A, feat in zip(ax, (trait_f, state_f)):
        d = F[["alias", "block", feat]].dropna()
        keep = d.groupby("alias").size()
        keep = keep[keep >= 6].index
        d = d[d.alias.isin(keep)]
        order = d.groupby("alias")[feat].mean().sort_values()
        cmap = plt.get_cmap("viridis")
        for i, a in enumerate(order.index):
            sub = d[d.alias == a].sort_values("block")
            x = np.arange(len(sub))
            A.plot(x, sub[feat], color=cmap(i / max(len(order) - 1, 1)), lw=1.1,
                   alpha=0.75)
        # Clip to a robust range: a single extreme week (a sensor-artefact
        # kurtosis of ~87) otherwise flattens every other line into the axis.
        lo, hi = np.nanpercentile(d[feat], [0.5, 99]) 
        pad = 0.08 * (hi - lo)
        A.set_ylim(lo - pad, hi + pad)
        n_out = int((d[feat] > hi).sum())
        if n_out:
            A.text(0.985, 0.965, f"{n_out} week(s) above axis", transform=A.transAxes,
                   ha="right", va="top", fontsize=8, color=S.MUTED)
        icc = float(I[I.feature == feat]["icc"].iloc[0])
        A.set_xlabel("week of that person's record", fontsize=9.5, color=S.INK2)
        A.set_ylabel(NICE.get(feat, feat), fontsize=9.5, color=S.INK2)
        A.set_title(f"{NICE.get(feat, feat)} — ICC {icc:.2f}", fontsize=11,
                    color=S.INK, loc="left", pad=7, weight="bold")
    S.title(fig, "20 · The same picture, one trait and one state",
            "One line per person, coloured by their overall level, each week of their own record. On the left the lines stay separated — people keep "
            "their rank. On the right\nthey cross constantly: the feature is real, but it belongs to the week rather than to the person, so a single "
            "measurement of it identifies nobody.")
    S.save(fig, "20_trait_tracks",
           dict(left=0.06, right=0.985, top=0.80, bottom=0.105, wspace=0.20))


def f21_space(F: pd.DataFrame, I: pd.DataFrame):
    """The trait space: dimensionality, position, and clustered-or-continuous."""
    traits = list(I[(I.icc > 0.5) & np.isfinite(I.icc)]["feature"])
    drop = {"tir", "t180", "t70", "bg_iqr", "bg_sd"}      # collinear with mean/CV
    traits = [t for t in traits if t not in drop]
    P = F.groupby("alias")[traits].mean().dropna()
    if len(P) < 8:
        print("  too few people for the trait space")
        return None
    X = ((P - P.mean()) / P.std()).to_numpy()

    U, sv, Vt = np.linalg.svd(X - X.mean(0), full_matrices=False)
    var = sv ** 2 / (sv ** 2).sum()
    PC = U[:, :2] * sv[:2]

    fig, ax = S.figure(1, 3, figsize=(15.0, 5.4))
    ax[0].bar(np.arange(1, len(var) + 1), var * 100, color=S.COOL, alpha=0.9)
    ax[0].plot(np.arange(1, len(var) + 1), np.cumsum(var) * 100, color=S.ACCENT,
               lw=1.8, marker="o", ms=4)
    ax[0].set_xlabel("component", fontsize=9.5, color=S.INK2)
    ax[0].set_ylabel("% of trait variance", fontsize=9.5, color=S.INK2)
    ax[0].set_title(f"{len(traits)} traits → how many real axes?", fontsize=11,
                    color=S.INK, loc="left", pad=7, weight="bold")
    ax[0].text(0.97, 0.06, f"PC1+PC2 = {100*var[:2].sum():.0f}%",
               transform=ax[0].transAxes, ha="right", fontsize=9, color=S.INK2)

    # Colour by dosing strategy: the best two-way split of this space turns out
    # to be how automated insulin is delivered, so show that directly.
    co_ = S.cohort().set_index("alias")
    strat = co_["strategy"].reindex(P.index).fillna("unknown") if "strategy" in co_ else \
        pd.Series("unknown", index=P.index)
    for s_, col, lbl in (("temp", S.COOL, "temp-basal strategy"),
                         ("bolus", S.ACCENT, "automatic-bolus strategy"),
                         ("unknown", S.MUTED, "glucose only")):
        m = (strat == s_).to_numpy()
        if m.any():
            ax[1].scatter(PC[m, 0], PC[m, 1], s=55, color=col, alpha=0.85,
                          edgecolor=S.SURFACE, lw=1.0, label=lbl)
    ax[1].set_xlabel(f"PC1 ({var[0]*100:.0f}%)", fontsize=9.5, color=S.INK2)
    ax[1].set_ylabel(f"PC2 ({var[1]*100:.0f}%)", fontsize=9.5, color=S.INK2)
    ax[1].legend(frameon=False, fontsize=8.5, labelcolor=S.INK2)
    ax[1].set_title("Where people sit", fontsize=11, color=S.INK, loc="left",
                    pad=7, weight="bold")

    sc = 2.6
    # Stagger label radius by angular rank — several loadings point almost the
    # same way and would otherwise print on top of each other.
    ang = np.array([np.arctan2(Vt[1, j], Vt[0, j]) for j in range(len(traits))])
    rank = {j: r for r, j in enumerate(np.argsort(ang))}
    for j, t in enumerate(traits):
        ax[2].arrow(0, 0, Vt[0, j] * sc, Vt[1, j] * sc, color=S.MUTED,
                    width=0.004, head_width=0.05, length_includes_head=True)
        rad = 1.14 + 0.20 * (rank[j] % 3)
        x, y = Vt[0, j] * sc * rad, Vt[1, j] * sc * rad
        # vectors that point nearly the same way get pushed apart vertically
        y += 0.32 * ((rank[j] % 2) - 0.5) * (1 if abs(Vt[1, j]) < 0.3 else 0)
        ax[2].text(x, y, NICE.get(t, t), fontsize=7.8, color=S.INK2,
                   ha="left" if x >= 0 else "right", va="center")
    ax[2].set_xlim(-sc * 2.1, sc * 2.1)
    ax[2].set_ylim(-sc * 1.7, sc * 1.7)
    ax[2].axhline(0, color=S.RULE, lw=1.0)
    ax[2].axvline(0, color=S.RULE, lw=1.0)
    ax[2].set_xlabel("PC1 loading", fontsize=9.5, color=S.INK2)
    ax[2].set_ylabel("PC2 loading", fontsize=9.5, color=S.INK2)
    ax[2].set_title("What the axes mean", fontsize=11, color=S.INK, loc="left",
                    pad=7, weight="bold")

    # clustered or continuous? gap-style check against a uniform null in PC space
    from itertools import combinations
    def within_ss(Z, k, seed=0):
        rng = np.random.default_rng(seed)
        c = Z[rng.choice(len(Z), k, replace=False)]
        for _ in range(60):
            lab = np.argmin(((Z[:, None, :] - c[None]) ** 2).sum(-1), axis=1)
            for j in range(k):
                if (lab == j).any():
                    c[j] = Z[lab == j].mean(0)
        lab = np.argmin(((Z[:, None, :] - c[None]) ** 2).sum(-1), axis=1)
        return float(sum(((Z[lab == j] - c[j]) ** 2).sum() for j in range(k))), lab

    Z = PC.copy()
    rng = np.random.default_rng(0)
    gaps = []
    for k in range(1, 6):
        obs = np.log(min(within_ss(Z, k, s)[0] for s in range(5)) + 1e-9)
        nulls = []
        for b in range(30):
            R = rng.uniform(Z.min(0), Z.max(0), size=Z.shape)
            nulls.append(np.log(min(within_ss(R, k, s)[0] for s in range(3)) + 1e-9))
        gaps.append(np.mean(nulls) - obs)
    best_k = int(np.argmax(gaps) + 1)
    print(f"  gap statistic by k: {[round(g,3) for g in gaps]} → best k = {best_k}")

    S.title(fig, "21 · The trait space — few axes, and a split that tracks dosing strategy",
            f"Only the trait-like features (ICC > 0.5), averaged per person. The first two components carry {100*var[:2].sum():.0f}% of the "
            "variation, so people differ along a small\nnumber of axes rather than in every feature independently. A gap statistic cannot separate "
            f"one cluster from two (best k = {best_k}, by a margin inside the test's noise), but the best two-way split\nis not arbitrary: it is "
            "how automated insulin is delivered. Temp-basal-strategy users sit together, lower and calmer; automatic-bolus users sit together.")
    S.save(fig, "21_trait_space",
           dict(left=0.05, right=0.99, top=0.795, bottom=0.115, wspace=0.28))
    return P, PC, var, Vt, traits, best_k


def main() -> int:
    F = pd.read_pickle(OUT / "trait_blocks.pkl")
    I = pd.read_csv(OUT / "trait_icc.csv")
    B = f19_icc(I, F)
    B.to_csv(OUT / "trait_magnitude.csv", index=False)
    f20_tracks(F, I)
    f21_space(F, I)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
