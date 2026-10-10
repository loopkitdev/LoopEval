#!/usr/bin/env python3
"""q02 (flags: how common, and what they do to ICE) and q03 (sensor noise
against the averaging window). Reads raw_screen.csv, flag_effects.csv, noise.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa

co = S.cohort()
scr = pd.read_csv(S.OUT / "ice" / "raw_screen.csv")
eff = pd.read_csv(S.OUT / "ice" / "flag_effects.csv")
noise = pd.read_csv(S.OUT / "ice" / "noise.csv")
LAB = {"disrupted": "pump error, suspend,\nloop offline", "unrecorded": "no insulin record\n(60 min or more)",
       "clamp": "at sensor floor\nor ceiling", "post_gap": "2 h after a\nCGM gap ≥ 60 min",
       "jump": "step > 8 mg/dL/min", "compression": "V-shaped low\n(compression)",
       "alternating": "alternating steps", "no_insulin": "day with no\ninsulin at all", "any": "any flag"}
order = ["disrupted", "unrecorded", "clamp", "post_gap", "jump", "compression", "alternating", "no_insulin", "any"]
rng = np.random.default_rng(3)

fig, ax = S.figure(1, 2, figsize=(13, 7.2), gridspec_kw={"width_ratios": [1.25, 1]})
a = ax[0]
for i, f in enumerate(order):
    col = "any_flag_pct" if f == "any" else f"{f}_pct"
    x = scr[col].to_numpy()
    y = len(order) - 1 - i
    a.scatter(np.maximum(x, 0.003), y + rng.uniform(-0.25, 0.25, len(x)), s=10,
              c=[S.color_for(co, q) for q in scr.alias], alpha=0.55, lw=0)
    m = np.median(x)
    a.plot([max(m, 0.003)] * 2, [y - 0.35, y + 0.35], color=S.INK, lw=2.2)
    a.text(105, y, f"median {m:.2f}%\nmax {x.max():.0f}%", fontsize=8, va="center", color=S.INK2)
a.set_xscale("log"); a.set_xlim(0.003, 100)
a.set_xticks([0.01, 0.1, 1, 10, 100]); a.set_xticklabels(["≤0.01", "0.1", "1", "10", "100"])
a.minorticks_off()
a.set_yticks(range(len(order))); a.set_yticklabels([LAB[f] for f in order[::-1]], fontsize=8.5)
a.set_xlabel("% of a person's CGM time on cadence", fontsize=9, color=S.INK2)
a.set_title("How much of each record each flag marks", loc="left", fontsize=11, color=S.INK)
a = ax[1]
e = eff.groupby("flag").agg(n=("alias", "size"), shift=("shift", "median"), sd=("sd_ratio", "median"))
fl = [f for f in order if f in e.index]
for i, f in enumerate(fl):
    y = len(fl) - 1 - i
    x = eff[eff.flag == f]["shift"].clip(-150, 250)
    a.scatter(x, y + rng.uniform(-0.25, 0.25, len(x)), s=10, color=S.MUTED, alpha=0.5, lw=0)
    a.plot([e.loc[f, "shift"]] * 2, [y - 0.35, y + 0.35], color=S.ACCENT, lw=2.4)
    a.text(255, y, f"{e.loc[f, 'shift']:+.0f}  ·  SD ×{e.loc[f, 'sd']:.2f}  ·  n={e.loc[f, 'n']}",
           fontsize=8, va="center", color=S.INK2)
a.axvline(0, color=S.INK2, lw=0.8)
a.set_xlim(-150, 250)
a.set_yticks(range(len(fl))); a.set_yticklabels([LAB[f] for f in fl[::-1]], fontsize=8.5)
a.set_xlabel("flagged ICE minus the person's clean ICE, median, mg/dL per hour", fontsize=9, color=S.INK2)
a.set_title("What each flag does to ICE", loc="left", fontsize=11, color=S.INK)
S.title(fig, "The bad-data screen",
        f"{len(scr)} people, raw CGM intervals. Right: 30-minute ICE inside flagged stretches against the same "
        "person's clean ICE; people with 50+ flagged intervals.")
S.save(fig, "q02_flags", tight=dict(left=0.13, right=0.86, top=0.85, bottom=0.09, wspace=0.75), check=False)

fig, ax = S.figure(1, 3, figsize=(13, 5.6))
a = ax[0]
for al, g in noise.groupby("alias"):
    a.plot(g.W, 100 * g.noise_share, **S.line_style(co, al, lw=1.2))
med = noise.groupby("W").noise_share.median() * 100
a.plot(med.index, med.values, color=S.INK, lw=2.4, marker="o", ms=4, zorder=6)
for w, v in med.items():
    a.text(w, v * 1.25, f"{v:.1f}%" if v >= 0.1 else f"{v:.2f}%", fontsize=8, color=S.INK, ha="center")
a.set_xscale("log"); a.set_yscale("log")
a.set_xticks([5, 10, 15, 30, 60, 120]); a.set_xticklabels(["5", "10", "15", "30", "60", "120"])
a.set_yticks([0.01, 0.1, 1, 10]); a.set_yticklabels(["0.01%", "0.1%", "1%", "10%"])
a.minorticks_off()
a.set_xlabel("averaging window, minutes", fontsize=9, color=S.INK2)
a.set_title("Share of ICE variance that is sensor noise", loc="left", fontsize=10.5, color=S.INK)
a = ax[1]
q = noise.groupby("W")[["p01", "p99", "sd_noise"]].median()
mm = noise.groupby("W").mean_ice.median()
a.fill_between(q.index, q.p01, q.p99, color=S.COOL, alpha=0.15, lw=0, label="ICE, p1 to p99 (median person)")
a.plot(q.index, mm, color=S.COOL, lw=2, label="mean ICE")
a.fill_between(q.index, mm - 2 * q.sd_noise, mm + 2 * q.sd_noise, color=S.ACCENT, alpha=0.35, lw=0,
               label="± 2 SD of sensor noise")
a.axhline(0, color=S.INK2, lw=0.8)
a.set_xscale("log"); a.set_xticks([5, 10, 15, 30, 60, 120]); a.set_xticklabels(["5", "10", "15", "30", "60", "120"])
a.minorticks_off()
a.set_xlabel("averaging window, minutes", fontsize=9, color=S.INK2)
a.set_ylabel("mg/dL per hour", fontsize=9, color=S.INK2)
a.legend(fontsize=8, frameon=False, loc="upper right")
a.set_title("Noise against the spread of real ICE", loc="left", fontsize=10.5, color=S.INK)
a = ax[2]
one = noise[noise.W == 5]
for i, (sen, g) in enumerate(one.groupby("sensor")):
    a.scatter(g.sigma_meas, g.lag1_native, s=16, label=f"{sen} (n={len(g)})", alpha=0.8, lw=0)
a.set_xlabel("sensor noise of the reported stream, mg/dL", fontsize=9, color=S.INK2)
a.set_ylabel("lag-1 autocorrelation of native-cadence ICE", fontsize=9, color=S.INK2)
a.legend(fontsize=7.5, frameon=False, loc="lower left")
a.set_title("Native cadence, by sensor", loc="left", fontsize=10.5, color=S.INK)
S.title(fig, "Sensor noise matters at five minutes and almost nowhere else",
        "Noise over a window comes only from its two end readings, so it shrinks as 1/window. "
        "Sensor noise per person is the structure-function intercept of their raw stream.")
S.save(fig, "q03_noise", tight=dict(left=0.05, right=0.98, top=0.80, bottom=0.12, wspace=0.3))
