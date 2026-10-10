#!/usr/bin/env python3
"""Time in range against TDD, and the TIR gap between stronger- and weaker-than-
peers ISF along TDD.

TDD in fifths (cohort quantiles). Per fifth: median TIR overall and by strategy;
the TIR difference (median) between the half of that fifth with ISF stronger than
the cohort curve predicts for their TDD and the half with it weaker, with a
bootstrap 90% interval; the same for user boluses per day (above vs below the
fifth's median), as a comparison. Also a running (LOWESS-like) median curve.

Output: settings_tir_tdd.csv, figs/s05_tir_tdd.png
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa

d = pd.read_csv(S.OUT / "isf_rules.csv")
d = d[d[["isf", "tdd_use", "tir", "t54"]].notna().all(axis=1)].copy()
a, b0 = np.polyfit(np.log(d.tdd_use), np.log(d.isf), 1)
d["ratio"] = d.isf / (np.exp(b0) * d.tdd_use ** a)
d["q"] = pd.qcut(d.tdd_use, 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"])
rng = np.random.default_rng(0)


def gap(g, col, split):
    hi = g[g[split]][col].to_numpy(); lo = g[~g[split]][col].to_numpy()
    obs = np.median(hi) - np.median(lo)
    bs = [np.median(rng.choice(hi, len(hi))) - np.median(rng.choice(lo, len(lo))) for _ in range(2000)]
    return obs, *np.percentile(bs, [5, 95]), stats.mannwhitneyu(hi, lo).pvalue


rows = []
for q, g in d.groupby("q", observed=True):
    g = g.copy()
    g["strong"] = g.ratio < g.ratio.median()
    g["bol_hi"] = g.manual_bolus_day > g.manual_bolus_day.median()
    gi = gap(g, "tir", "strong"); gb = gap(g, "tir", "bol_hi")
    rows.append({"fifth": q, "tdd_lo": g.tdd_use.min(), "tdd_hi": g.tdd_use.max(), "tdd_med": g.tdd_use.median(),
                 "n": len(g), "tir": g.tir.median(), "tir_temp": g[g.strategy == "temp"].tir.median(),
                 "n_temp": int((g.strategy == "temp").sum()), "tir_bolus": g[g.strategy == "bolus"].tir.median(),
                 "n_bolus": int((g.strategy == "bolus").sum()), "t54": g.t54.median(),
                 "isf_gap": gi[0], "isf_lo": gi[1], "isf_hi": gi[2], "isf_p": gi[3],
                 "ratio_strong": g[g.strong].ratio.median(), "ratio_weak": g[~g.strong].ratio.median(),
                 "bol_gap": gb[0], "bol_lo": gb[1], "bol_hi": gb[2], "bol_p": gb[3],
                 "bol_split": g.manual_bolus_day.median()})
r = pd.DataFrame(rows)
r.to_csv(S.OUT / "settings_tir_tdd.csv", index=False)
pd.set_option("display.width", 220)
print(r.round(2).to_string(index=False))
rho = stats.spearmanr(d.tdd_use, d.tir)
print(f"\nTIR vs TDD: spearman {rho[0]:+.2f} (p={rho[1]:.4f}); by strategy:",
      {s: round(stats.spearmanr(g.tdd_use, g.tir)[0], 2) for s, g in d.groupby("strategy")})
# does the ISF gap shrink with TDD? interaction: TIR ~ rank(ratio) * log TDD
m = d[["tir", "ratio", "tdd_use"]].rank()
m["x"] = (m.ratio - m.ratio.mean()) * (m.tdd_use - m.tdd_use.mean())
X = np.column_stack([np.ones(len(m)), m.ratio, m.tdd_use, m.x])
beta, *_ = np.linalg.lstsq(X, m.tir, rcond=None)
e = m.tir - X @ beta; s2 = e @ e / (len(m) - 4)
se = np.sqrt(s2 * np.linalg.inv(X.T @ X)[3, 3])
print(f"ISF-ratio x TDD interaction on TIR (ranks): coef {beta[3]:+.4f}, p={2 * stats.t.sf(abs(beta[3] / se), len(m) - 4):.3f}")

# figure
COL = {"bolus": S.ACCENT, "temp": S.COOL}
fig, ax = S.figure(1, 2, figsize=(13, 5.6))
A = ax[0]
for s, g in d.groupby("strategy"):
    A.scatter(g.tdd_use, g.tir, s=16, color=COL[s], alpha=.55, lw=0, label={"bolus": "automatic bolus", "temp": "temp basal"}[s])
A.plot(r.tdd_med, r.tir, color=S.INK, lw=2.4, marker="o", ms=6, label="median of each TDD fifth")
for _, rr in r.iterrows():
    A.text(rr.tdd_med, rr.tir + 2.5, f"{rr.tir:.0f}", ha="center", fontsize=8.5, color=S.INK)
A.set_xscale("log"); A.set_xticks([10, 20, 50, 100, 200])
A.xaxis.set_major_formatter(S.plt.FuncFormatter(lambda v, _: f"{v:g}")); A.minorticks_off()
A.set_xlabel("total daily insulin, U", fontsize=9, color=S.INK2)
A.set_ylabel("time in range 70–180, %", fontsize=9, color=S.INK2)
A.legend(fontsize=8.5, frameon=False, loc="lower left")
A.set_title(f"Time in range falls with TDD (ρ {rho[0]:+.2f})", loc="left", fontsize=10.5, color=S.INK)
A = ax[1]
x = np.arange(len(r))
A.errorbar(x - .08, r.isf_gap, yerr=[r.isf_gap - r.isf_lo, r.isf_hi - r.isf_gap], fmt="o-", color=S.GREEN,
           lw=2, capsize=3, label="stronger-ISF half − weaker half (ratio to the curve)")
A.errorbar(x + .08, r.bol_gap, yerr=[r.bol_gap - r.bol_lo, r.bol_hi - r.bol_gap], fmt="s--", color=S.MUTED,
           lw=1.5, capsize=3, label="bolusing more − less (within the fifth)")
A.axhline(0, color=S.INK2, lw=0.8)
A.set_xticks(x); A.set_xticklabels([f"{rr.fifth}\n{rr.tdd_lo:.0f}–{rr.tdd_hi:.0f} U" for _, rr in r.iterrows()], fontsize=8)
A.set_xlabel("TDD fifth", fontsize=9, color=S.INK2)
A.set_ylabel("difference in median time in range, points", fontsize=9, color=S.INK2)
A.legend(fontsize=8.5, frameon=False, loc="upper right")
A.set_title("The TIR gap within each TDD fifth (90% bootstrap)", loc="left", fontsize=10.5, color=S.INK)
S.title(fig, "Time in range against daily insulin",
        f"{len(d)} Loop users in fifths of TDD (about {len(d) // 5} each). ISF halves: ISF ÷ the cohort curve's ISF at the person's "
        "TDD, split at that fifth's median of this ratio.")
S.save(fig, "s05_tir_tdd", tight=dict(left=0.06, right=0.98, top=0.82, bottom=0.14, wspace=0.22))
