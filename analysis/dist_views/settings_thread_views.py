#!/usr/bin/env python3
"""Figures w01-w03 for "ISF, Rule of X and Outcomes" — the 2026-09-24 thread:
who meets TIR >= 80% with time below 54 <= 1%, the rule of X they run, the rule
of X in steps of 200, and the split by dosing strategy with max basal.
Reads isf_rules.csv; definitions shared with settings_claims.thread_claims."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from settings_claims import (tier, TIER_LABELS, BIN200_EDGES, BIN200_LABELS, BIN4_EDGES, BIN4_LABELS)  # noqa

d = pd.read_csv(S.OUT / "isf_rules.csv")
d = d[d[["isf", "tdd_use", "tir", "t54"]].notna().all(axis=1)].copy()
d["well"] = (d.tir >= 80) & (d.t54 <= 1)
a, b0 = np.polyfit(np.log(d.tdd_use), np.log(d.isf), 1)
K = np.exp(b0)
d["ratio"] = d.isf / (K * d.tdd_use ** a)
W, R = d[d.well], d[~d.well]
r_w = W.ratio.median()
rng = np.random.default_rng(0)
COL = {"bolus": S.ACCENT, "temp": S.COOL}; NAME = {"bolus": "automatic bolus", "temp": "temp basal"}


def logfmt(a_):
    for x_ in (a_.xaxis, a_.yaxis):
        x_.set_major_formatter(S.plt.FuncFormatter(lambda v, _: f"{v:g}"))
    a_.minorticks_off()


# w01 — who meets the target and the ISF they run
fig, ax = S.figure(1, 3, figsize=(15, 5.6))
A = ax[0]
A.scatter(R.tdd_use, R.isf, s=22, color=S.MUTED, alpha=.45, lw=0, label=f"everyone else ({len(R)})")
A.scatter(W.tdd_use, W.isf, s=40, color=S.GREEN, alpha=.9, edgecolor=S.SURFACE, lw=.8, zorder=4,
          label=f"TIR ≥ 80% and t<54 ≤ 1% ({len(W)})")
xs = np.linspace(d.tdd_use.min(), d.tdd_use.max(), 100)
A.plot(xs, 1800 / xs, color=S.ACCENT, lw=1.8, label="rule of 1800")
A.plot(xs, K * xs ** a, color=S.INK, lw=1.6, ls=(0, (4, 2)), label=f"cohort: {K:.0f} ÷ TDD^{-a:.2f}")
A.plot(xs, K * r_w * xs ** a, color=S.GREEN, lw=2, label=f"target group: {K * r_w:.0f} ÷ TDD^{-a:.2f}")
A.set_xscale("log"); A.set_yscale("log"); A.set_xticks([10, 20, 50, 100, 200]); A.set_yticks([10, 20, 50, 100])
logfmt(A)
A.set_xlabel("total daily insulin, U", fontsize=9, color=S.INK2)
A.set_ylabel("ISF, mg/dL per U", fontsize=9, color=S.INK2)
A.legend(frameon=False, fontsize=8, loc="lower left")
A.set_title("Who meets the target, and the ISF they run", loc="left", fontsize=10.5, color=S.INK)
A = ax[1]
d["tier"] = d.apply(tier, axis=1)
labs = ["TIR ≥ 80\nt<54 ≤ 1", "TIR ≥ 80\nt<54 > 1", "TIR\n70–80", "TIR\n60–70", "TIR\n< 60"]
for j, tl in enumerate(TIER_LABELS):
    g = d[d.tier == tl]
    A.scatter(rng.normal(j, .07, len(g)), g.k1800, s=24, color=S.GREEN if j == 0 else S.COOL, alpha=.75,
              edgecolor=S.SURFACE, lw=.6, zorder=3)
    m = g.k1800.median()
    A.plot([j - .26, j + .26], [m, m], color=S.INK, lw=2.2, zorder=5)
    A.annotate(f"{m:.0f}", (j, m), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=8, color=S.INK, zorder=6)
A.axhline(1800, color=S.ACCENT, lw=1.6, ls=(0, (4, 2)))
A.set_xticks(range(5)); A.set_xticklabels([f"{l}\nn={(d.tier == t).sum()}" for l, t in zip(labs, TIER_LABELS)], fontsize=8)
A.set_ylabel("rule of X (ISF × TDD)", fontsize=9, color=S.INK2)
A.set_title("The rule of X, by outcome", loc="left", fontsize=10.5, color=S.INK)
A = ax[2]
d["tband"] = pd.qcut(d.tdd_use, 3, labels=["low TDD", "mid TDD", "high TDD"])
for j, (lb, g) in enumerate(d.groupby("tband", observed=True)):
    for flag, c_ in ((True, S.GREEN), (False, S.MUTED)):
        v = g.loc[g.well == flag, "ratio"]
        x = j + (-.18 if flag else .18)
        if len(v):
            A.scatter(rng.normal(x, .05, len(v)), v, s=22, color=c_, alpha=.8, edgecolor=S.SURFACE, lw=.5, zorder=3)
            A.plot([x - .13, x + .13], [v.median()] * 2, color=S.INK, lw=2, zorder=5)
    w_, r_ = g.loc[g.well, "ratio"], g.loc[~g.well, "ratio"]
    txt = f"{len(w_)} of {len(g)}\nmeet it"
    if len(w_) >= 3:
        txt += f"\np = {mannwhitneyu(w_, r_).pvalue:.3f}"
    A.text(j, 2.25, txt, ha="center", va="top", fontsize=8, color=S.INK2, linespacing=1.4)
A.axhline(1, color=S.INK, lw=1, ls=(0, (3, 3)))
A.set_ylim(0.3, 2.35)
A.set_xticks(range(3)); A.set_xticklabels(["low TDD", "mid TDD", "high TDD"], fontsize=8.5)
A.set_ylabel("ISF ÷ cohort-expected ISF for that TDD", fontsize=9, color=S.INK2)
A.set_title("Held against peers of the same insulin use", loc="left", fontsize=10.5, color=S.INK)
S.title(fig, "ISF and the rule of X among people meeting TIR ≥ 80% with time below 54 ≤ 1%",
        f"{len(d)} Loop users. Green: the {len(W)} who meet both. Their median rule of X is {W.k1800.median():.0f} against "
        f"{R.k1800.median():.0f} for everyone else, mostly because they use less insulin; against peers of the same TDD\n"
        f"they run an ISF {100 * (1 - r_w):.0f}% stronger, all of it in the low-TDD third. Association, not effect.")
S.save(fig, "w01_target", tight=dict(left=0.05, right=0.99, top=0.78, bottom=0.15, wspace=0.28))

# w02 — rule of X in steps of 200
d["bin"] = pd.cut(d.k1800, BIN200_EDGES, labels=BIN200_LABELS, right=False)
fig, ax = S.figure(1, 3, figsize=(15.6, 5.4))


def strip(A, col, fmt, well_color=True):
    for j, lb in enumerate(BIN200_LABELS):
        x = d[d.bin == lb]
        if not len(x):
            continue
        c = np.where(x.well, S.GREEN, S.COOL) if well_color else S.COOL
        A.scatter(rng.normal(j, .08, len(x)), x[col], s=26, c=c, alpha=.8, edgecolor=S.SURFACE, lw=.6, zorder=3)
        m = x[col].median()
        A.plot([j - .28, j + .28], [m, m], color=S.INK, lw=2.3, zorder=5)
        A.annotate(fmt.format(m), (j, m), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=8,
                   color=S.INK, zorder=6, bbox=dict(facecolor=S.SURFACE, edgecolor="none", alpha=.8, pad=1))
    A.set_xticks(range(len(BIN200_LABELS)))
    A.set_xticklabels([f"{lb}\nn={(d.bin == lb).sum()}" for lb in BIN200_LABELS], fontsize=8)
    A.set_xlabel("rule of X (ISF × TDD)", fontsize=9, color=S.INK2)
    A.axvline(BIN200_LABELS.index("1800s") - .5, color=S.ACCENT, lw=1.2, ls=(0, (4, 2)), zorder=1)


strip(ax[0], "tir", "{:.0f}")
ax[0].set_ylabel("time in range 70–180, %", fontsize=9, color=S.INK2)
ax[0].set_title("Time in range", loc="left", fontsize=10.5, color=S.INK)
strip(ax[1], "t54", "{:.2f}")
ax[1].set_ylim(-.1, 3.5); ax[1].axhline(1, color=S.ACCENT, lw=1, alpha=.4)
ax[1].set_ylabel("time below 54, %", fontsize=9, color=S.INK2)
ax[1].set_title("Time below 54", loc="left", fontsize=10.5, color=S.INK)
strip(ax[2], "tdd_use", "{:.0f}", well_color=False)
ax[2].set_yscale("log"); ax[2].set_yticks([10, 20, 50, 100, 200])
ax[2].yaxis.set_major_formatter(S.plt.FuncFormatter(lambda v, _: f"{v:g}")); ax[2].minorticks_off()
ax[2].set_ylabel("total daily insulin, U", fontsize=9, color=S.INK2)
ax[2].set_title("Daily insulin in each band", loc="left", fontsize=10.5, color=S.INK)
S.title(fig, "Outcomes by the rule of X people's settings imply, in steps of 200",
        "Green: TIR ≥ 80% with time below 54 ≤ 1%. Black bars are medians; the dashed line marks 1800.")
S.save(fig, "w02_bins", tight=dict(left=0.05, right=0.99, top=0.84, bottom=0.15, wspace=0.25))

# w03 — by strategy, with max basal
d["b4"] = pd.cut(d.k1800, BIN4_EDGES, labels=BIN4_LABELS, right=False)
fig, ax = S.figure(1, 3, figsize=(15.6, 5.6))


def split_strip(A, col, fmt, ylab, title):
    for j, lb in enumerate(BIN4_LABELS):
        for st in ("bolus", "temp"):
            x = d[(d.b4 == lb) & (d.strategy == st)][col]
            xpos = j + (-.19 if st == "bolus" else .19)
            if len(x):
                A.scatter(rng.normal(xpos, .05, len(x)), x, s=20, color=COL[st], alpha=.75, edgecolor=S.SURFACE,
                          lw=.5, zorder=3, label=NAME[st] if j == 0 else None)
            if len(x) >= 3:
                A.plot([xpos - .13, xpos + .13], [x.median()] * 2, color=S.INK, lw=2.2, zorder=5)
                A.annotate(fmt.format(x.median()), (xpos, x.median()), xytext=(0, 6), textcoords="offset points",
                           ha="center", fontsize=7.5, color=S.INK, zorder=6,
                           bbox=dict(facecolor=S.SURFACE, edgecolor="none", alpha=.8, pad=.8))
    A.set_xticks(range(4))
    A.set_xticklabels([f"{lb}\n{((d.b4 == lb) & (d.strategy == 'bolus')).sum()} / {((d.b4 == lb) & (d.strategy == 'temp')).sum()}"
                       for lb in BIN4_LABELS], fontsize=8)
    A.set_xlabel("rule of X (n automatic bolus / temp basal)", fontsize=9, color=S.INK2)
    A.set_ylabel(ylab, fontsize=9, color=S.INK2)
    A.set_title(title, loc="left", fontsize=10.5, color=S.INK)


split_strip(ax[0], "tir", "{:.0f}", "time in range 70–180, %", "Time in range, by strategy")
ax[0].legend(frameon=False, fontsize=8.5, loc="lower left")
split_strip(ax[1], "t54", "{:.2f}", "time below 54, %", "Time below 54, by strategy")
ax[1].set_ylim(-.1, 3.5); ax[1].axhline(1, color=S.ACCENT, lw=1, alpha=.4)
A = ax[2]
for st in ("temp", "bolus"):
    g = d[d.strategy == st].copy()
    g["hb"] = pd.qcut(g.headroom, 3, labels=["low", "mid", "high"])
    for j, (lb, x) in enumerate(g.groupby("hb", observed=True)):
        xpos = j + (.19 if st == "temp" else -.19)
        A.scatter(rng.normal(xpos, .05, len(x)), x.t70, s=20, color=COL[st], alpha=.75, edgecolor=S.SURFACE, lw=.5, zorder=3)
        A.plot([xpos - .13, xpos + .13], [x.t70.median()] * 2, color=S.INK, lw=2.2, zorder=5)
        A.annotate(f"{x.t70.median():.1f}\n{x.headroom.median():.1f}×", (xpos, x.t70.median()), xytext=(0, 6),
                   textcoords="offset points", ha="center", fontsize=7.5, color=S.INK, zorder=6,
                   bbox=dict(facecolor=S.SURFACE, edgecolor="none", alpha=.8, pad=.8))
A.set_xticks(range(3)); A.set_xticklabels(["low", "middle", "high"], fontsize=8.5)
A.set_ylim(-.3, 12)
A.set_xlabel("max basal ÷ scheduled basal, thirds within each strategy", fontsize=9, color=S.INK2)
A.set_ylabel("time below 70, %", fontsize=9, color=S.INK2)
A.set_title("Max-basal headroom and the lows", loc="left", fontsize=10.5, color=S.INK)
A.text(.02, .97, "labels: median time below 70, and the headroom multiple", transform=A.transAxes, fontsize=7.8,
       color=S.INK2, va="top")
S.title(fig, "Rule of X by dosing strategy, and the max-basal cap",
        "Automatic bolus is almost all Omnipod with Dexcom; temp basal is almost all twiist with Libre 3.")
S.save(fig, "w03_strategy", tight=dict(left=0.05, right=0.99, top=0.84, bottom=0.15, wspace=0.25))
