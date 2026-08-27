#!/usr/bin/env python3
"""Views 14-15 — the volatility estimator, and what it is worth.

14  Does conditioning on a causal volatility estimate actually tame the
    increment distribution, and how well can σ be predicted at all?
15  The two therapy-relevant readings, out of sample.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt                            # noqa: E402
import style as S                                          # noqa: E402
import fundamentals as F                                   # noqa: E402
import vol_cache as VC                                     # noqa: E402

EST_COLOR = {"roll_centred": "#8a949e", "roll_causal": "#3b6ea5",
             "ewma": "#1baf7a", "garch": "#eb6834"}
EST_LABEL = {"roll_centred": "rolling window, centred (not causal)",
             "roll_causal": "rolling window, causal",
             "ewma": "EWMA", "garch": "GARCH(1,1)"}


def z_of(d, key):
    e, s = d["eps"], d[key]
    m = np.isfinite(s) & (s > 0) & np.isfinite(e)
    return e[m] / s[m]


def _strip(ax, groups, colors, labels, ylabel, ref_lines=(), logy=False):
    """Distribution of a per-person statistic across people, one strip per
    estimator: jittered dots, a heavy median tick, and a p10–p90 bar. Readable
    at any cohort size, which per-person bars are not."""
    rng = np.random.default_rng(3)
    for i, (g, c, lab) in enumerate(zip(groups, colors, labels)):
        g = np.asarray(g, float); g = g[np.isfinite(g)]
        if not len(g):
            continue
        x = i + rng.uniform(-0.18, 0.18, len(g))
        ax.scatter(x, g, s=14, color=c, alpha=0.55, lw=0, zorder=2)
        lo, med, hi = np.percentile(g, [10, 50, 90])
        ax.plot([i - 0.3, i + 0.3], [med, med], color=S.INK, lw=2.2, zorder=4)
        ax.plot([i, i], [lo, hi], color=c, lw=3.0, alpha=0.5, zorder=3)
        ax.text(i, ax.get_ylim()[1] if False else med, "", fontsize=7)
    for v, lab, col in ref_lines:
        ax.axhline(v, color=col, lw=1.3, ls=(0, (4, 2)))
        # Reference labels sit over the dot clouds; a surface-coloured box keeps
        # them legible without moving them somewhere less meaningful.
        ax.text(0.995, v, f"{lab} ", fontsize=7.5, color=col, va="bottom",
                ha="right", transform=ax.get_yaxis_transform(),
                bbox=dict(fc=S.SURFACE, ec="none", alpha=0.85, pad=1.5))
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(labels, fontsize=8.5, color=S.INK2)
    ax.set_ylabel(ylabel, fontsize=9.5, color=S.INK2)
    if logy:
        ax.set_yscale("log")


def _qq_band(ax, aliases, key, color, label, n_grid=41):
    """Median Q-Q across people with a p10–p90 band, on a shared theoretical grid."""
    th_grid = np.linspace(-4.0, 4.0, n_grid)
    curves = []
    for a in aliases:
        z = z_of(VC.load(a), key)
        if len(z) < 500:
            continue
        th, xs = F.qq_points(z / np.std(z), "normal", n=600)
        curves.append(np.interp(th_grid, th, xs))
    if not curves:
        return
    C = np.array(curves)
    lo, med, hi = np.percentile(C, [10, 50, 90], axis=0)
    ax.fill_between(th_grid, lo, hi, color=color, alpha=0.16, lw=0)
    ax.plot(th_grid, med, color=color, lw=2.0, label=label)


def f14_estimator(co):
    fig, ax = S.figure(2, 3, figsize=(14.4, 9.0))
    aliases = [a for a in co["alias"] if VC.load(a)]
    n = len(aliases)

    # 1 — Q-Q of standardised increments: median + band per estimator.
    for key in ("roll_centred", "roll_causal", "garch"):
        _qq_band(ax[0][0], aliases, key, EST_COLOR[key], EST_LABEL[key])
    ax[0][0].plot([-4.2, 4.2], [-4.2, 4.2], color=S.INK, lw=1.6, ls=(0, (4, 2)))
    ax[0][0].set_xlim(-4.2, 4.2); ax[0][0].set_ylim(-7, 7)
    ax[0][0].set_xlabel("normal quantile", fontsize=9.5, color=S.INK2)
    ax[0][0].set_ylabel("standardised increment", fontsize=9.5, color=S.INK2)
    ax[0][0].legend(frameon=False, fontsize=8, labelcolor=S.INK2, loc="upper left")
    ax[0][0].set_title("Only a non-causal window looks Gaussian",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # 2 — excess kurtosis across people, per estimator.
    K = {k: [] for k in ("raw", "roll_centred", "roll_causal", "ewma", "garch")}
    for a in aliases:
        d = VC.load(a)
        r = pd.Series(d["eps"]).kurtosis()
        if r >= 20:                       # sensor-spike records swamp the axis
            continue
        K["raw"].append(r)
        for key in EST_COLOR:
            z = z_of(d, key)
            K[key].append(pd.Series(z).kurtosis() if len(z) > 500 else np.nan)
    _strip(ax[0][1], [K["raw"], K["roll_centred"], K["roll_causal"], K["ewma"], K["garch"]],
           [S.INK, EST_COLOR["roll_centred"], EST_COLOR["roll_causal"], EST_COLOR["ewma"], EST_COLOR["garch"]],
           ["raw", "centred\n(not causal)", "rolling\ncausal", "EWMA", "GARCH"],
           "excess kurtosis", ref_lines=[(0, "Gaussian", S.MUTED), (3, "Laplace", S.ACCENT)])
    ax[0][1].set_ylim(-0.5, 8)
    ax[0][1].set_title("Causal conditioning removes 40% of the tail",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # 3 — out-of-sample R² across people.
    try:
        sc = pd.read_csv(S.OUT / "vol_scores.csv")
        piv = sc.pivot(index="alias", columns="estimator", values="r2_logvar")
        _strip(ax[0][2], [piv["rolling"], piv["ewma"], piv["garch"]],
               ["#3b6ea5", "#1baf7a", "#eb6834"], ["rolling", "EWMA", "GARCH"],
               "out-of-sample R²")
        ax[0][2].set_ylim(0, 0.42)
        ax[0][2].set_title("Predicting the next 30 min of volatility",
                           fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")
    except FileNotFoundError:
        pass

    # 4 — σ's own distribution, one thin line per person.
    for a in aliases:
        s_ = VC.load(a)["ewma"]; s_ = s_[np.isfinite(s_) & (s_ > 0)]
        g = np.linspace(0, 20, 300)
        ax[1][0].plot(g, S.kde(s_, g), **S.line_style(co, a))
    ax[1][0].set_xlabel("EWMA σ (mg/dL per 5 min)", fontsize=9.5, color=S.INK2)
    ax[1][0].set_ylabel("density", fontsize=9.5, color=S.INK2)
    ax[1][0].set_title("Within one person, σ spans about 4×",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # 5 — calibration, one thin line per person.
    for a in aliases:
        d = VC.load(a); s_, e = d["ewma"], d["eps"]
        m = np.isfinite(s_) & (s_ > 0) & np.isfinite(e); s_, e = s_[m], e[m]
        q = pd.qcut(pd.Series(s_), 10, labels=False, duplicates="drop")
        g = pd.DataFrame({"s": s_, "a": np.abs(e), "q": q}).groupby("q")
        ax[1][1].plot(g["s"].mean(), g["a"].mean(), **S.line_style(co, a))
    lim = np.linspace(0, 18, 20)
    ax[1][1].plot(lim, lim * np.sqrt(2 / np.pi), color=S.INK, lw=1.6, ls=(0, (4, 2)),
                  label="Gaussian: E|ε| = σ√(2/π)")
    ax[1][1].plot(lim, lim / np.sqrt(2), color=S.ACCENT, lw=1.5, ls=(0, (2, 2)),
                  label="Laplace: E|ε| = σ/√2")
    ax[1][1].set_xlabel("predicted σ (decile mean)", fontsize=9.5, color=S.INK2)
    ax[1][1].set_ylabel("realised mean |ε|", fontsize=9.5, color=S.INK2)
    ax[1][1].legend(frameon=False, fontsize=8, labelcolor=S.INK2, loc="upper left")
    ax[1][1].set_title("Calibrated at every level of σ",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # 6 — far-tail coverage across people, Gaussian vs Laplace band.
    cg, cl = [], []
    for a in aliases:
        z = z_of(VC.load(a), "ewma")
        if len(z) < 500:
            continue
        z = (z - np.median(z)) / np.std(z)
        cg.append(float(np.mean(np.abs(z) <= 2.576)))
        cl.append(float(np.mean(np.abs(z) <= 3.257)))
    _strip(ax[1][2], [cg, cl], ["#8a949e", S.ACCENT],
           ["±2.576σ\n(Gaussian 99%)", "±3.257σ\n(Laplace 99%)"],
           "actual coverage", ref_lines=[(0.99, "nominal 99%", S.INK)])
    ax[1][2].set_ylim(0.955, 1.0)
    ax[1][2].set_title("A Gaussian 99% band under-covers",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    S.title(fig, f"14 · A causal volatility estimator — {n} people",
            "Each panel is a distribution across people. Conditioning each increment on a volatility estimated only from the PAST removes about "
            "40% of its excess\nkurtosis and no more: the increment is partly a variance mixture and partly a genuinely heavy-tailed innovation. "
            "A window centred on the increment it scales\nappears to remove almost all of it, but that window contains the increment — it is not "
            "something a controller could compute. In the far tail the innovation is Laplace.")
    S.save(fig, "14_volatility_estimator",
           dict(left=0.058, right=0.972, top=0.855, bottom=0.085, hspace=0.50, wspace=0.30))


def f15_therapy(co):
    try:
        L = pd.read_csv(S.OUT / "vol_lows.csv")
        H = pd.read_csv(S.OUT / "vol_highs.csv")
    except FileNotFoundError:
        print("  (run vol_therapy.py first)"); return
    fig, ax = S.figure(1, 3, figsize=(14.4, 5.6))

    def forest(A, D, title, min_ev):
        D = D.sort_values("ratio").reset_index(drop=True)
        ok = D["events"] >= min_ev
        for i, r in D.iterrows():
            thin = r["events"] < min_ev
            if thin:
                col, lw, ms = "#d7d9dc", 1.0, 3
            elif r["ci_lo"] > 1:
                col, lw, ms = S.GREEN, 1.8, 5
            elif r["ci_hi"] < 1:
                col, lw, ms = S.ACCENT, 1.8, 5
            else:
                col, lw, ms = S.MUTED, 1.4, 4
            A.plot([r["ci_lo"], r["ci_hi"]], [i, i], color=col, lw=lw, alpha=0.8,
                   solid_capstyle="round")
            A.plot([r["ratio"]], [i], "o", color=col, ms=ms, mec=S.SURFACE, mew=0.8, zorder=3)
        A.axvline(1, color=S.INK, lw=1.6, ls=(0, (4, 2)))
        A.set_yticks([]); A.set_xscale("log"); A.set_xlim(0.1, 40)
        A.set_xlabel("rate ratio, high-σ / low-σ (log) · 90% CI", fontsize=9.5, color=S.INK2)
        P = D[ok]
        up, dn = int((P["ci_lo"] > 1).sum()), int((P["ci_hi"] < 1).sum())
        A.text(0.02, 0.97, f"{len(P)} people with enough events\nmedian ratio {P['ratio'].median():.2f}\n"
               f"{up} clearly above 1, {dn} clearly below", transform=A.transAxes,
               fontsize=8.5, color=S.INK2, va="top", linespacing=1.5,
               bbox=dict(fc=S.SURFACE, ec="none", alpha=0.85, pad=3))
        A.set_title(title, fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    forest(ax[0], L, "Lows: a hypo within 30 min, high-σ vs low-σ", 100)
    forest(ax[1], H[H["events"] >= 10], "Highs: from above 180, a low within 2 h", 30)

    Hs = H.sort_values("frac_high_lowvol").reset_index(drop=True)
    y = np.arange(len(Hs))
    ax[2].barh(y, Hs["frac_high"] * 100, height=0.8, color=S.RULE, label="all time above 180")
    ax[2].barh(y, Hs["frac_high_lowvol"] * 100, height=0.8,
               color=[S.color_for(co, a) for a in Hs["alias"]],
               label="above 180 AND in the low-σ tercile")
    ax[2].set_yticks([])
    ax[2].set_xlabel("share of all samples (%)", fontsize=9.5, color=S.INK2)
    ax[2].legend(frameon=False, fontsize=8, labelcolor=S.INK2, loc="lower right")
    ax[2].text(0.98, 0.97, f"median {Hs['frac_high_lowvol'].median()*100:.1f}% of time is\n"
               "'high and calm'", transform=ax[2].transAxes, fontsize=8.5, color=S.INK2,
               va="top", ha="right", linespacing=1.5)
    ax[2].set_title("How much time the calm-high state covers",
                    fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    S.title(fig, f"15 · What σ is associated with, person by person",
            "Out of sample: the estimator is fitted on the first 30% of each record and every point comes from the remaining 70%. One row per "
            "person, sorted; green intervals\nexclude 1 upward, grey straddle it, pale rows are underpowered. Left: at matched glucose and trend, a "
            "volatile recent trace carries more hypo risk. Middle: starting\nhigh, a calm trace is less likely to end low. Right: how often that "
            "calm-high state occurs. These are associations in data where dosing already responded to state.")
    S.save(fig, "15_therapy", dict(left=0.03, right=0.99, top=0.775, bottom=0.115, wspace=0.16))


def main():
    co = S.cohort()
    f14_estimator(co)
    f15_therapy(co)


if __name__ == "__main__":
    main()
