#!/usr/bin/env python3
"""Figures s01-s04 for the "ISF, Rule of X and Outcomes" page.
Reads isf_rules.csv, cap_changes_loose.csv, settings_claims.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from settings_claims import RULE_EDGES, RULE_LABELS, BOL_EDGES, BOL_LABELS  # noqa

d = pd.read_csv(S.OUT / "isf_rules.csv")
C = json.loads((S.OUT / "settings_claims.json").read_text())
COL = {"bolus": S.ACCENT, "temp": S.COOL}
LAB = {"bolus": "automatic bolus", "temp": "temp basal"}
rng = np.random.default_rng(4)


def logticks(a, xs, ys=None):
    a.set_xscale("log"); a.set_xticks(xs); a.xaxis.set_major_formatter(S.plt.FuncFormatter(lambda v, _: f"{v:g}"))
    if ys is not None:
        a.set_yscale("log"); a.set_yticks(ys); a.yaxis.set_major_formatter(S.plt.FuncFormatter(lambda v, _: f"{v:g}"))
    a.minorticks_off()


# s01 — the rule of X
fig, ax = S.figure(1, 2, figsize=(13, 5.6))
a = ax[0]
for s, g in d.groupby("strategy"):
    a.scatter(g.tdd_use, g.isf, s=18, color=COL[s], alpha=0.75, lw=0, label=LAB[s])
x = np.linspace(8, 200, 100)
a.plot(x, 1800 / x, color=S.MUTED, lw=1.4, ls="--", label="rule of 1800: ISF = 1800 ÷ TDD")
a.plot(x, C["fit_K"] / x ** C["fit_b"], color=S.INK, lw=2, label=f"best fit: ISF = {C['fit_K']:.0f} ÷ TDD^{C['fit_b']:.2f}")
logticks(a, [10, 20, 50, 100, 200], [10, 20, 50, 100, 150])
a.set_xlim(8, 200); a.set_ylim(8, 160)
a.set_xlabel("total daily insulin, U", fontsize=9, color=S.INK2)
a.set_ylabel("scheduled ISF, mg/dL per U", fontsize=9, color=S.INK2)
a.legend(fontsize=8.5, frameon=False, loc="lower left")
a.set_title("ISF falls with daily insulin, but more slowly than 1/TDD", loc="left", fontsize=10.5, color=S.INK)
a = ax[1]
for s, g in d.groupby("strategy"):
    a.scatter(g.tdd_use, g.k1800, s=18, color=COL[s], alpha=0.75, lw=0)
q = pd.qcut(d.tdd_use, 4)
med = d.groupby(q, observed=True).agg(t=("tdd_use", "median"), k=("k1800", "median"))
a.plot(med.t, med.k, color=S.INK, lw=2.2, marker="o", ms=6, label="median of each TDD quarter")
for t_, k_ in zip(med.t, med.k):
    a.text(t_, k_ + 120, f"{k_:.0f}", ha="center", fontsize=8.5, color=S.INK)
a.axhline(1800, color=S.MUTED, ls="--", lw=1.2)
logticks(a, [10, 20, 50, 100, 200])
a.set_xlim(8, 200)
a.set_xlabel("total daily insulin, U", fontsize=9, color=S.INK2)
a.set_ylabel("rule-of-X constant = ISF × TDD", fontsize=9, color=S.INK2)
a.legend(fontsize=8.5, frameon=False, loc="upper right")
a.set_title(f"So the 'constant' rises with TDD (median {C['rule_median']:.0f})", loc="left", fontsize=10.5, color=S.INK)
S.title(fig, "How Loop users set ISF against their daily insulin",
        f"{C['n']} people; scheduled ISF (time-weighted) against delivered total daily insulin.")
S.save(fig, "s01_rule", tight=dict(left=0.06, right=0.98, top=0.82, bottom=0.12, wspace=0.22))

# s02 — outcomes by rule-of-X band, by strategy
d["rule_bin"] = pd.cut(d.k1800, RULE_EDGES, labels=RULE_LABELS, right=False)
fig, ax = S.figure(1, 2, figsize=(13, 5.6))
for a, y, yl, ttl in ((ax[0], "tir", "time in range 70–180, %", "Time in range falls as the rule-of-X constant rises"),
                      (ax[1], "t54", "time below 54, %", "Time below 54 tracks strategy, not the rule")):
    for j, s in enumerate(("temp", "bolus")):
        g = d[d.strategy == s]
        xs = g.rule_bin.cat.codes + (j - 0.5) * 0.3
        a.scatter(xs + rng.uniform(-0.08, 0.08, len(g)), g[y], s=12, color=COL[s], alpha=0.45, lw=0)
        m = g.groupby("rule_bin", observed=False)[y].median()
        a.plot(np.arange(len(RULE_LABELS)) + (j - 0.5) * 0.3, m.values, color=COL[s], lw=2.2, marker="o", ms=5,
               label=f"{LAB[s]} (n={len(g)})")
    a.set_xticks(range(len(RULE_LABELS))); a.set_xticklabels(RULE_LABELS, fontsize=8.5)
    a.set_xlabel("rule-of-X constant (ISF × TDD)", fontsize=9, color=S.INK2)
    a.set_ylabel(yl, fontsize=9, color=S.INK2)
    a.set_title(ttl, loc="left", fontsize=10.5, color=S.INK)
ax[1].set_yscale("symlog", linthresh=0.5); ax[1].set_ylim(0, 8)
ax[1].set_yticks([0, 0.1, 0.25, 0.5, 1, 2, 5]); ax[1].yaxis.set_major_formatter(S.plt.FuncFormatter(lambda v, _: f"{v:g}"))
ax[0].legend(fontsize=8.5, frameon=False, loc="lower left")
n = [C["rule_bins"][b]["n"] for b in RULE_LABELS]
S.title(fig, "A lower rule-of-X goes with more time in range, and no more lows",
        "Dots are people, lines the median of each band. Band sizes " + ", ".join(f"{b} {k}" for b, k in zip(RULE_LABELS, n)) + ".")
S.save(fig, "s02_outcomes", tight=dict(left=0.06, right=0.98, top=0.82, bottom=0.12, wspace=0.22))

# s03 — the max-basal cap (temp-basal users) and within-person changes
tb = d[d.strategy == "temp"].copy()
fig, ax = S.figure(1, 3, figsize=(13, 5.6), gridspec_kw={"width_ratios": [1.2, 1, 1]})
a = ax[0]
strong = tb.k1800 < tb.k1800.median()
for s_, col, lab in ((True, S.INK, f"stronger ISF (rule < {C['temp_rule_median']:.0f})"),
                     (False, S.MUTED, "weaker ISF")):
    g = tb[strong == s_]
    a.scatter(g.headroom, g.t70, s=18, color=col, alpha=0.75, lw=0, label=lab)
a.axvline(C["temp_head_median"], color=S.INK2, lw=0.8, ls=":")
a.set_yscale("symlog", linthresh=1); a.set_ylim(0, 25); a.set_yticks([0, 1, 2, 5, 10, 20])
a.yaxis.set_major_formatter(S.plt.FuncFormatter(lambda v, _: f"{v:g}"))
a.set_xlabel("headroom: max basal ÷ scheduled basal", fontsize=9, color=S.INK2)
a.set_ylabel("time below 70, %", fontsize=9, color=S.INK2)
a.legend(fontsize=8.5, frameon=False, loc="upper right")
r = C["temp_head_t70"]
a.set_title(f"More headroom, more mild lows (partial ρ {r[0]:+.2f})", loc="left", fontsize=10.5, color=S.INK)
a = ax[1]
cells = [("strong", "low cap"), ("strong", "high cap"), ("weak", "low cap"), ("weak", "high cap")]
for i, (st, cp) in enumerate(cells):
    v = C["temp_2x2"][f"{st}|{cp}"]
    a.barh(i, v["t70"], color=S.ACCENT if cp == "low cap" else S.MUTED, alpha=0.85)
    a.text(v["t70"] + 0.05, i, f"t<70 {v['t70']:.2f}%   TIR {v['tir']:.0f}%   n={v['n']}", va="center", fontsize=8.5, color=S.INK)
a.set_yticks(range(4)); a.set_yticklabels([f"{st} ISF · {cp}" for st, cp in cells], fontsize=8.5)
a.invert_yaxis(); a.set_xlim(0, 5.5)
a.set_xlabel("median time below 70, %", fontsize=9, color=S.INK2)
a.set_title("The cap moves lows, ISF moves TIR", loc="left", fontsize=10.5, color=S.INK)
a = ax[2]
cc = pd.read_csv(S.OUT / "cap_changes_loose.csv")
up = cc[cc.clean & (cc.dir == "raised")]
for _, rr in up.iterrows():
    a.plot([0, 1], [rr.pre_tir, rr.post_tir], color=S.COOL, lw=1, alpha=0.6, marker="o", ms=3)
a.plot([0, 1], [up.pre_tir.median(), up.post_tir.median()], color=S.INK, lw=2.6, marker="o", ms=6)
a.set_xticks([0, 1]); a.set_xticklabels(["before", "after"]); a.set_xlim(-0.3, 1.3)
a.set_ylabel("time in range, %", fontsize=9, color=S.INK2)
t, t7 = C["cap_up_tir"], C["cap_up_t70"]
a.set_title(f"{len(up)} people who raised their cap", loc="left", fontsize=10.5, color=S.INK)
a.text(0.02, 0.03, f"TIR {t[0]:+.1f} points (p {t[1]:.3f})\ntime below 70 {t7[0]:+.2f} points (p {t7[1]:.3f})",
       transform=a.transAxes, fontsize=8.5, color=S.INK, va="bottom")
S.title(fig, "The max-basal cap governs mild lows; ISF governs time in range",
        f"Temp-basal users ({C['temp_n']}). Partial correlations hold daily insulin, age, target and the other setting. "
        "Right: within-person raises with no ISF change within 3 days.")
S.save(fig, "s03_cap", tight=dict(left=0.06, right=0.98, top=0.8, bottom=0.12, wspace=0.42))

# s04 — bolusing and daily insulin
fig, ax = S.figure(1, 2, figsize=(13, 5.4))
a = ax[0]
for s, g in d.groupby("strategy"):
    a.scatter(g.manual_bolus_day, g.tir, s=18, color=COL[s], alpha=0.7, lw=0, label=LAB[s])
bb = pd.cut(d.manual_bolus_day, BOL_EDGES, labels=BOL_LABELS, right=False)
med = d.groupby(bb, observed=True).agg(x=("manual_bolus_day", "median"), y=("tir", "median"))
a.plot(med.x, med.y, color=S.INK, lw=2.2, marker="o", ms=6, label="median by band")
a.set_xlabel("user boluses per day", fontsize=9, color=S.INK2)
a.set_ylabel("time in range, %", fontsize=9, color=S.INK2)
a.legend(fontsize=8.5, frameon=False, loc="lower right")
r = C["bol_tir"]
a.set_title(f"Bolusing tracks TIR (partial ρ {r[0]:+.2f})", loc="left", fontsize=10.5, color=S.INK)
a = ax[1]
for s, g in d.groupby("strategy"):
    a.scatter(g.tdd_use, g.tir, s=18, color=COL[s], alpha=0.7, lw=0)
logticks(a, [10, 20, 50, 100, 200]); a.set_xlim(8, 200)
a.set_xlabel("total daily insulin, U", fontsize=9, color=S.INK2)
a.set_ylabel("time in range, %", fontsize=9, color=S.INK2)
r0, r1 = C["tdd_tir_raw"], C["tdd_tir_adj"]
a.set_title(f"Daily insulin: ρ {r0[0]:+.2f} raw, {r1[0]:+.2f} once bolusing and ISF are held", loc="left",
            fontsize=10.5, color=S.INK)
S.title(fig, "User boluses per day is the strongest behavioural correlate of time in range",
        "Partial correlations hold daily insulin, rule of X, age, target and strategy. Association, not effect.")
S.save(fig, "s04_bolus", tight=dict(left=0.06, right=0.98, top=0.82, bottom=0.12, wspace=0.22))
