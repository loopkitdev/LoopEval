#!/usr/bin/env python3
"""q01 — a gallery of the most extreme unflagged ICE windows, to judge by eye
whether each is physiology or bad data. Reads ice/extremes_top.csv and
ice/raw/<alias>.pkl. One case per person, highest and lowest."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_raw import FLAGS  # noqa

top = pd.read_csv(S.OUT / "ice" / "extremes_top.csv"); top["t"] = pd.to_datetime(top.t, utc=True, format="ISO8601")
hi = top.sort_values("ice", ascending=False).drop_duplicates("alias").head(4)
lo = top.sort_values("ice").drop_duplicates("alias").head(4)
cases = pd.concat([hi, lo])
fig, axs = S.figure(4, 2, figsize=(13, 13.5))
for ax, (_, c) in zip(axs.T.ravel(), cases.iterrows()):
    d = pd.read_pickle(S.OUT / "ice" / "raw" / f"{c.alias}.pkl")
    t0 = c.t - pd.Timedelta(hours=3); t1 = c.t + pd.Timedelta(hours=3)
    w = d[(d.t0 >= t0) & (d.t1 <= t1)]
    x = (w.t1 - c.t).dt.total_seconds() / 3600
    ax.plot(x, w.bg1, color=S.INK, lw=1.6, label="glucose")
    ax.axvspan(0, 0.5, color=S.ACCENT, alpha=0.12, lw=0)
    for f, col in (("disrupted", "#b98900"), ("unrecorded", "#8a5a9e"), ("clamp", S.MUTED),
                   ("compression", S.COOL), ("jump", S.ACCENT)):
        m = w[f].to_numpy()
        if m.any():
            ax.scatter(x[m], np.full(m.sum(), 30), marker="|", s=60, color=col, label=f)
    ax.set_ylim(20, 420)
    ax2 = ax.twinx()
    ax2.fill_between(x, 0, w.absorbed / w.dt * 60, color=S.COOL, alpha=0.25, lw=0, step="pre")
    ax2.set_ylim(0, max(4, (w.absorbed / w.dt * 60).max() * 2.2))
    ax2.set_ylabel("insulin absorbed, U/hr", fontsize=8, color=S.COOL)
    ax2.tick_params(labelsize=7.5, colors=S.COOL)
    for s_ in ("top",):
        ax2.spines[s_].set_visible(False)
    ax.set_title(f"{c.alias} · 30-min ICE {c.ice:+.0f} = glucose {c.v:+.0f} + insulin {c.ia:.0f} mg/dL/hr",
                 loc="left", fontsize=9.5, color=S.INK)
    ax.set_xlim(-3, 3)
    ax.legend(fontsize=7, frameon=False, loc="upper left", ncol=3)
for ax in axs[-1]:
    ax.set_xlabel("hours from the window (shaded)", fontsize=8.5, color=S.INK2)
axs[0, 0].text(0, 1.22, "Highest unflagged ICE", transform=axs[0, 0].transAxes, fontsize=11, weight="bold", color=S.INK)
axs[0, 1].text(0, 1.22, "Lowest unflagged ICE", transform=axs[0, 1].transAxes, fontsize=11, weight="bold", color=S.INK)
S.title(fig, "The most extreme ICE the flags let through",
        "Six hours around each person's most extreme 30-minute window. Black: glucose (mg/dL, left). "
        "Blue fill: insulin absorbed (right).")
S.save(fig, "q01_gallery", tight=dict(left=0.05, right=0.94, top=0.89, bottom=0.04, hspace=0.42, wspace=0.28), check=False)
