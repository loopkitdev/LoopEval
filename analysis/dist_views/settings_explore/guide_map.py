import sys; sys.path.insert(0,'/Users/pete/dev/loopeval-eda/analysis/dist_views')
import numpy as np, pandas as pd, style as S
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
d = pd.read_csv(S.OUT/"isf_rules.csv").set_index("alias")
d = d[d[["tdd_use","k1800","tir","t54"]].notna().all(axis=1)].copy()
lx, ly = np.log10(d.tdd_use), np.log10(d.k1800)
gx = np.linspace(np.log10(12), np.log10(110), 120); gy = np.linspace(np.log10(800), np.log10(3600), 120)
GX, GY = np.meshgrid(gx, gy)
BX, BY = 0.13, 0.075          # kernel widths in log10 units (~35% in TDD, ~19% in X)
def surface(sub, val):
    wx = (GX[...,None]-np.log10(sub.tdd_use.to_numpy()))/BX
    wy = (GY[...,None]-np.log10(sub.k1800.to_numpy()))/BY
    w = np.exp(-.5*(wx**2+wy**2)); n = w.sum(-1)
    z = (w*val.to_numpy()).sum(-1)/np.maximum(n,1e-9)
    return np.where(n >= 2.5, z, np.nan), n      # blank where fewer than ~2.5 people contribute

TIRMAP = LinearSegmentedColormap.from_list("tir", ["#f3efe6","#b9d7c6","#4f9e7c","#155e45"])
LOWMAP = LinearSegmentedColormap.from_list("low", ["#f3efe6","#f2c5ad","#e07a4f","#a93a1c"])
fig, ax = S.figure(2, 2, figsize=(13.6, 10.2))
rows = (("temp", "Temp basal"), ("bolus", "Automatic bolus"))
for r,(st,name) in enumerate(rows):
    sub = d[d.strategy.eq(st)]
    for c,(val,cmap,vmin,vmax,lab) in enumerate((
            (sub.tir, TIRMAP, 50, 90, "time in range, smoothed over nearby people (%)"),
            ((sub.t54>1).astype(float)*100, LOWMAP, 0, 40, "share of nearby people with t<54 over 1% (%)"))):
        A = ax[r][c]
        z,_ = surface(sub, val)
        im = A.pcolormesh(10**gx, 10**gy, z, cmap=cmap, vmin=vmin, vmax=vmax, shading="auto", zorder=1)
        well = (sub.tir>=80)&(sub.t54<=1); bad = sub.t54>1
        A.scatter(sub.tdd_use[~well&~bad], sub.k1800[~well&~bad], s=18, facecolor="white",
                  edgecolor=S.INK2, lw=.7, zorder=4, label="other")
        A.scatter(sub.tdd_use[well], sub.k1800[well], s=34, color=S.GREEN, edgecolor="white",
                  lw=.8, zorder=5, label="TIR ≥ 80 and t<54 ≤ 1%")
        A.scatter(sub.tdd_use[bad], sub.k1800[bad], s=34, marker="X", color=S.ACCENT,
                  edgecolor="white", lw=.6, zorder=5, label="t<54 over 1%")
        A.axhline(1800, color=S.INK, lw=1.1, ls=(0,(4,2)), zorder=3)
        A.text(12.5, 1800*1.02, "rule of 1800", fontsize=8, color=S.INK, va="bottom", zorder=6)
        # ISF iso-lines: at a given TDD, rule of X = ISF x TDD
        for isf in (20, 40, 80):
            xs = np.linspace(12, 110, 50); A.plot(xs, isf*xs, color=S.MUTED, lw=.8, ls=(0,(1,2)), zorder=2)
            xe = min(110, 3500/isf); A.text(xe, isf*xe, f" ISF {isf}", fontsize=7.5, color=S.MUTED,
                                            va="center", ha="left" if xe<100 else "right", zorder=6)
        A.set_xscale("log"); A.set_yscale("log")
        A.set_xlim(12, 110); A.set_ylim(800, 3600)
        A.set_xticks([15,20,30,40,60,80,100]); A.set_xticklabels(["15","20","30","40","60","80","100"])
        A.set_yticks([1000,1200,1500,1800,2200,2800,3500]); A.set_yticklabels(["1000","1200","1500","1800","2200","2800","3500"])
        A.minorticks_off()
        A.set_xlabel("total daily dose (U)", fontsize=9.5, color=S.INK2)
        A.set_ylabel("rule of X  (ISF × TDD)   more aggressive ↓", fontsize=9.5, color=S.INK2)
        ttl = ("Time in range" if c==0 else "Lows") + f" — {name.lower()}, n={len(sub)}"
        A.set_title(ttl, fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")
        cb = fig.colorbar(im, ax=A, fraction=.045, pad=.02); cb.ax.tick_params(labelsize=8, colors=S.INK2)
        cb.set_label(lab, fontsize=8.5, color=S.INK2)
        if r==0 and c==0: A.legend(frameon=True, facecolor=S.SURFACE, edgecolor="none", fontsize=8,
                                   labelcolor=S.INK2, loc="upper right")
S.title(fig, "Where people land: insulin use against configured aggressiveness",
        f"{len(d)} Loop donors, one point each. Background is a smoothed average of the people nearby (blank where too few). "
        "Lower on the y-axis = stronger ISF for the amount of insulin used.\nFind a TDD, read vertically, and see which rule of X "
        "goes with good time in range and which with lows. Observational — these people chose their settings; see notes.")
S.save(fig, "aggressiveness_map", dict(left=0.06, right=0.97, top=0.875, bottom=0.06, hspace=0.28, wspace=0.18))
