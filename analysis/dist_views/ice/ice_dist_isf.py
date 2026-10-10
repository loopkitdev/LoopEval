#!/usr/bin/env python3
"""i06/i07 — how the ISF assumption reshapes each person's ICE distribution.

ICE at ISF multiple m is v + m * ia_abs (absolute insulin), 30-minute mean,
non-disrupted steps. i06: the twelve-person representative sample, one panel
each, densities at m = 0.75, 0.9, 1.0, 1.1, 1.25. i07: cohort-wide, how each
person's quantiles and share below zero move with m.
"""
from __future__ import annotations
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
from matplotlib import cm, colors as mcolors
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa

H = 12
MULTS = (0.75, 0.9, 1.0, 1.1, 1.25)
GRID = np.linspace(-300, 700, 501)
QS = (0.01, 0.1, 0.5, 0.9, 0.99)
CMAP = mcolors.LinearSegmentedColormap.from_list("isf", ["#3b6ea5", "#9aa6b2", S.INK, "#d99a7a", "#eb6834"])
MC = {m: CMAP(i / (len(MULTS) - 1)) for i, m in enumerate(MULTS)}


def series(alias):
    p = S.load(alias)
    ok = p["v"].notna().to_numpy() & ~p["disrupted"].astype(bool).to_numpy()
    v = np.where(ok, p["v"].to_numpy(), np.nan)
    ia = np.where(ok, p["ia_abs"].to_numpy(), np.nan)
    out = {}
    for m in MULTS:
        x = pd.Series((v + m * ia) * H).rolling(6, center=True, min_periods=6).mean().to_numpy()
        out[m] = x[np.isfinite(x)]
    return out


def stats(alias):
    s = series(alias)
    row = {"alias": alias}
    for m, x in s.items():
        for q, val in zip(QS, np.quantile(x, QS)):
            row[f"{m}_q{int(q*100):02d}"] = val
        row[f"{m}_neg"] = (x < 0).mean()
        row[f"{m}_sd"] = x.std()
    return row


def i06(co):
    samp = S.sample_for(co)
    samp = sorted(samp, key=lambda a: float(co.set_index("alias").loc[a, "carb_g_day"]))
    fig, axs = S.figure(3, 4, figsize=(13, 9.6))
    for ax, a in zip(axs.ravel(), samp):
        s = series(a)
        r = co.set_index("alias").loc[a]
        for m in MULTS:
            ax.plot(GRID, S.kde(s[m], GRID, bw=8.0), color=MC[m],
                    lw=2.2 if m == 1.0 else 1.3, zorder=3 if m == 1.0 else 2)
        ax.axvline(0, color=S.INK2, lw=0.7)
        pp = S.load(a)
        isf_s = np.nanmedian(pp["isf"])
        cover = np.nanmedian(pp["basal_sched"] * pp["isf"])
        ax.axvline(isf_s, color=S.GREEN, lw=1.4, ls="--", zorder=4)
        ax.axvline(cover, color="#8a5a9e", lw=1.4, ls=":", zorder=4)
        ax.set_xlim(-200, 500); ax.set_ylim(0, None); ax.set_yticks([])
        neg = " / ".join(f"{(s[m] < 0).mean():.0%}" for m in (0.75, 1.0, 1.25))
        ax.text(0.98, 0.95, f"below 0: {neg}\nat ×0.75 / ×1 / ×1.25", transform=ax.transAxes,
                ha="right", va="top", fontsize=7.5, color=S.INK2, linespacing=1.4)
        ax.set_title(f"{r.carb_g_day:.0f} g/day announced · ISF {isf_s:.0f}"
                     f" · TIR {r.tir:.0f}%", loc="left", fontsize=9.5, color=S.color_for(co, a))
        ax.tick_params(labelsize=8)
    for ax in axs[-1]:
        ax.set_xlabel("ICE, 30-min mean, mg/dL per hour", fontsize=8.5, color=S.INK2)
    handles = [S.plt.Line2D([], [], color=MC[m], lw=2.2 if m == 1 else 1.4) for m in MULTS]
    handles += [S.plt.Line2D([], [], color=S.GREEN, lw=1.4, ls="--"),
                S.plt.Line2D([], [], color="#8a5a9e", lw=1.4, ls=":")]
    fig.legend(handles, [f"ISF ×{m}" for m in MULTS] + ["scheduled ISF × 1 U/hr",
               "scheduled basal × ISF"], loc="upper right", ncol=7, frameon=False,
               fontsize=8.5, bbox_to_anchor=(0.99, 0.925))
    S.title(fig, "Twelve people's ICE at five ISF assumptions",
            "The study's fixed representative sample, ordered by announced carbohydrate. "
            "Black is the scheduled ISF; blue weaker insulin, orange stronger.")
    S.save(fig, "i06_dist_isf_people", tight=dict(left=0.02, right=0.99, top=0.86, bottom=0.07,
                                                    hspace=0.42, wspace=0.08))


def i07(co):
    with Pool(8) as pool:
        rows = pool.map(stats, list(co.alias))
    d = pd.DataFrame(rows).set_index("alias")
    fig, axs = S.figure(1, 3, figsize=(13, 6.2))
    ax = axs[0]
    for q, c in zip(["q01", "q10", "q50", "q90", "q99"],
                    ["#3b6ea5", "#7f9cbf", S.INK, "#d99a7a", "#eb6834"]):
        med = [d[f"{m}_{q}"].median() for m in MULTS]
        lo = [d[f"{m}_{q}"].quantile(.1) for m in MULTS]
        hi = [d[f"{m}_{q}"].quantile(.9) for m in MULTS]
        ax.fill_between(MULTS, lo, hi, color=c, alpha=0.12, lw=0)
        ax.plot(MULTS, med, color=c, lw=2, marker="o", ms=4)
        ax.text(1.26, med[-1], f" p{q[1:]}", color=c, fontsize=8.5, va="center")
    ax.axhline(0, color=S.INK2, lw=0.7)
    ax.set_title("Each percentile of a person's ICE", loc="left", fontsize=10.5, color=S.INK)
    ax.set_ylabel("mg/dL per hour (median person, band p10–p90)", fontsize=8.5, color=S.INK2)
    ax = axs[1]
    for a in d.index:
        ax.plot(MULTS, [d.loc[a, f"{m}_neg"] * 100 for m in MULTS], **S.line_style(co, a, lw=1.2))
    med = [d[f"{m}_neg"].median() * 100 for m in MULTS]
    ax.plot(MULTS, med, color=S.INK, lw=2.4, zorder=5)
    for m, v in zip(MULTS, med):
        ax.text(m, v, f" {v:.1f}%", fontsize=8.5, color=S.INK, va="bottom", zorder=6)
    ax.set_ylim(0, 25)
    ax.set_title("Share of time ICE is below zero", loc="left", fontsize=10.5, color=S.INK)
    ax.set_ylabel("% of 30-min means", fontsize=8.5, color=S.INK2)
    ax = axs[2]
    for a in d.index:
        ax.plot(MULTS, [d.loc[a, f"{m}_sd"] / d.loc[a, "1.0_sd"] for m in MULTS],
                **S.line_style(co, a, lw=1.2))
    med = [(d[f"{m}_sd"] / d["1.0_sd"]).median() for m in MULTS]
    ax.plot(MULTS, med, color=S.INK, lw=2.4, zorder=5)
    for m, v in zip(MULTS, med):
        ax.text(m, v, f" {v:.2f}", fontsize=8.5, color=S.INK, va="bottom", zorder=6)
    ax.set_title("Spread (SD), relative to the scheduled ISF", loc="left", fontsize=10.5, color=S.INK)
    for ax in axs:
        ax.set_xticks(MULTS); ax.set_xticklabels([f"×{m}" for m in MULTS])
        ax.set_xlabel("ISF used, multiple of the schedule", fontsize=8.5, color=S.INK2)
    S.title(fig, "What the ISF assumption does to everyone's distribution",
            f"{len(d)} people, ICE as a 30-minute mean, absolute insulin. "
            "Faint lines are people, coloured the representative sample, black the median.")
    S.save(fig, "i07_dist_isf_cohort", tight=dict(left=0.06, right=0.97, top=0.80, bottom=0.12, wspace=0.25))
    d.to_csv(S.OUT / "ice" / "ice_dist_isf.csv")
    print(pd.DataFrame({m: {k: d[f"{m}_{k}"].median() for k in ["q01", "q10", "q50", "q90", "q99", "neg", "sd"]}
                        for m in MULTS}).round(3).to_string())


if __name__ == "__main__":
    co = S.cohort()
    i06(co)
    if "--people" not in sys.argv:
        i07(co)
