#!/usr/bin/env python3
"""Views 11-13.

11 — how much of a 5-minute glucose change is sensor noise rather than glucose
12 — what the joint structure of insulin activity and velocity actually is
13 — whether subtracting insulin makes the process any simpler to model
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt                      # noqa: E402
import style as S                                    # noqa: E402
import fundamentals as F                             # noqa: E402
from loopeval_analysis import dists as D             # noqa: E402


def structure_function(alias, mins):
    """Var of the difference over each horizon in MINUTES, from raw samples."""
    return np.array([
        (lambda d: d.var() if len(d) > 300 else np.nan)(S.raw_delta(alias, float(m)))
        for m in mins])


def noise_from_structure(alias, mins=(5, 10, 15, 20, 30, 40, 60)):
    """Estimate sensor-noise variance from the structure function's intercept.

    If the recorded series is a smooth glucose signal plus independent
    measurement error of variance σ², then

        Var[BG(t+τ) − BG(t)]  =  2σ²  +  C·τ^(2H)

    The measurement term does not vanish as τ → 0 while the signal term does,
    so the intercept of a fit through the smallest lags is 2σ². Solving for σ
    gives the noise the sensor contributes to every single reading.
    """
    mins = np.asarray(mins, dtype=float)
    sf = structure_function(alias, mins)
    ok = np.isfinite(sf)
    if ok.sum() < 4:
        return np.nan, np.nan, np.nan
    x, y = mins[ok], sf[ok]

    best = (np.inf, np.nan, np.nan, np.nan)
    for H in np.linspace(0.35, 1.15, 81):           # profile out the exponent
        b = x ** (2 * H)
        A = np.vstack([np.ones_like(b), b]).T
        coef, res, *_ = np.linalg.lstsq(A, y, rcond=None)
        if coef[0] < 0 or coef[1] < 0:
            continue
        r = float(np.sum((A @ coef - y) ** 2))
        if r < best[0]:
            best = (r, coef[0], coef[1], H)
    _, icept, C, H = best
    if not np.isfinite(icept):
        return np.nan, np.nan, np.nan
    return float(np.sqrt(max(icept, 0) / 2.0)), float(C), float(H)


def f11_noise(panels, co):
    order = S.order_by(co, "tir")
    fig, ax = S.figure(2, 3, figsize=(14.4, 9.0))
    mins = np.array([5, 10, 15, 20, 30, 40, 60, 90, 120])
    rec = {}
    for a in order:
        sf = structure_function(a, mins)
        sig, C, H = noise_from_structure(a)
        rec[a] = (sig, C, H, sf)
        col = S.color_for(co, a)
        ax[0][0].plot(mins, sf, **S.line_style(co, a), marker="o", ms=2.6)
        if np.isfinite(sig):
            ax[0][0].plot([0], [2 * sig ** 2], color=col, marker="_", ms=11,
                          mew=2.0)
    ax[0][0].set_xlim(-3, 125)
    ax[0][0].set_xlabel("horizon τ (minutes)", fontsize=9.5, color=S.INK2)
    ax[0][0].set_ylabel("Var[BG(t+τ) − BG(t)]", fontsize=9.5, color=S.INK2)
    ax[0][0].set_title("Structure function does not pass through the origin",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    al = sorted(rec, key=lambda k: rec[k][0] if np.isfinite(rec[k][0]) else 0)
    y = np.arange(len(al))
    sigs = [rec[a][0] for a in al]
    ax[0][1].barh(y, sigs, color=[S.color_for(co, a) for a in al], alpha=0.88,
                  height=0.72)
    ax[0][1].set_yticks(y)
    ax[0][1].set_yticklabels(al, fontsize=8, color=S.INK2)
    ax[0][1].set_xlabel("implied per-reading sensor noise σ (mg/dL)", fontsize=9.5,
                        color=S.INK2)
    for yi, sg in zip(y, sigs):
        if np.isfinite(sg):
            ax[0][1].text(sg + 0.03, yi, f"{sg:.2f}", va="center", fontsize=7.8,
                          color=S.INK2)
    ax[0][1].set_title("Implied noise per reading", fontsize=10.5, color=S.INK,
                       loc="left", pad=6, weight="bold")

    # What share of observed 5-min velocity variance is just noise?
    share = []
    for a in al:
        sig = rec[a][0]
        vv = S.raw_delta(a)
        share.append(2 * sig ** 2 / vv.var() if np.isfinite(sig) else np.nan)
    ax[0][2].barh(y, share, color=[S.color_for(co, a) for a in al], alpha=0.88,
                  height=0.72)
    ax[0][2].set_yticks(y)
    ax[0][2].set_yticklabels(al, fontsize=8, color=S.INK2)
    ax[0][2].set_xlim(0, max(1e-3, np.nanmax(share)) * 1.28)
    ax[0][2].set_xlabel("share of 5-min velocity variance that is measurement noise",
                        fontsize=9.5, color=S.INK2)
    for yi, sh in zip(y, share):
        if np.isfinite(sh):
            ax[0][2].text(sh + 0.006, yi, f"{sh*100:.0f}%", va="center",
                          fontsize=7.8, color=S.INK2)
    ax[0][2].set_title("Most of what a 5-minute delta reports is real",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # Signal-to-noise as a function of the horizon you difference over.
    tau = np.array([5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 240])
    for a in order:
        sig, C, H, _ = rec[a]
        if not np.isfinite(sig):
            continue
        snr = (C * tau ** (2 * H)) / (2 * sig ** 2)
        ax[1][0].plot(tau, snr, **S.line_style(co, a))
    ax[1][0].axhline(1, color=S.INK, lw=1.5, ls=(0, (4, 2)),
                     label="signal = noise")
    ax[1][0].set_xscale("log")
    ax[1][0].set_yscale("log")
    ax[1][0].set_xlabel("differencing horizon (minutes)", fontsize=9.5, color=S.INK2)
    ax[1][0].set_ylabel("signal variance / noise variance", fontsize=9.5, color=S.INK2)
    ax[1][0].legend(frameon=False, fontsize=8.5, labelcolor=S.INK2)
    ax[1][0].set_title("Longer differences buy signal-to-noise cheaply",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # The ACF signature of additive noise: a step down between lag 0 and lag 1.
    for a in order:
        rs, cad = S.raw_runs(a)
        vr = [np.diff(r) for r in rs if len(r) > 60]
        if not vr:
            continue
        nl = int(round(50 / cad))
        A = F.acf(vr, nl)
        ax[1][1].plot(np.arange(nl + 1) * cad, A, **S.line_style(co, a), marker="o", ms=2.8)
    ax[1][1].axhline(0, color=S.INK, lw=1.2)
    ax[1][1].axhline(-0.5, color=S.ACCENT, lw=1.5, ls=(0, (3, 3)),
                     label="pure noise: −0.5 at lag 1")
    ax[1][1].set_xlabel("lag (minutes)", fontsize=9.5, color=S.INK2)
    ax[1][1].set_ylabel("autocorrelation of Δ BG", fontsize=9.5, color=S.INK2)
    ax[1][1].legend(frameon=False, fontsize=8.5, labelcolor=S.INK2)
    ax[1][1].set_title("Lag-1 sits far above the pure-noise floor",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # Noise vs the velocity spread it sits inside.
    for _, r in co.iterrows():
        a = r["alias"]
        sig = rec[a][0]
        if not np.isfinite(sig):
            continue
        col = S.GROUP_COLOR.get(S.group_of(r), S.MUTED)
        ax[1][2].scatter(S.raw_delta(a).std(), sig, s=64, color=col, edgecolor=S.SURFACE,
                         lw=1.2, zorder=3)
        ax[1][2].annotate(a if a in S.sample_for(co) else "", (S.raw_delta(a).std(), sig), textcoords="offset points",
                          xytext=(7, -3), fontsize=8, color=S.INK2)
    ax[1][2].set_xlabel("raw-sample velocity SD (mg/dL / 5 min)", fontsize=9.5, color=S.INK2)
    ax[1][2].set_ylabel("implied sensor noise σ (mg/dL)", fontsize=9.5, color=S.INK2)
    ax[1][2].margins(x=0.16, y=0.18)
    ax[1][2].set_title("Noise is roughly constant; the spread is not",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    S.title(fig, "11 · How much of a 5-minute change is the sensor?",
            "Differences over τ minutes should have vanishing variance as τ → 0. They do not: the structure function hits a positive intercept, "
            "and that intercept is twice the\nper-reading measurement variance. It comes out near 1 mg/dL for everyone — small. "
            "A 5-minute delta is mostly real glucose, which is worth knowing before smoothing it away.")
    S.save(fig, "11_measurement_noise",
           dict(left=0.06, right=0.985, top=0.885, bottom=0.075, hspace=0.42, wspace=0.30))
    return rec


def f12_insulin_joint(panels, co):
    order = S.order_by(co, "tir")
    fig, ax = S.figure(2, 3, figsize=(14.4, 9.0))

    # Velocity distribution conditioned on how hard insulin is working.
    ref = "bddp10"
    c = D.clean(panels[ref])
    q = pd.qcut(c["ia_abs"], 5, labels=False, duplicates="drop")
    g = np.linspace(-22, 22, 300)
    cmap = plt.get_cmap("viridis")
    for k in sorted(pd.unique(q.dropna())):
        sel = c["v"][q == k]
        ax[0][0].plot(g, np.maximum(S.kde(sel, g), 1e-6), lw=1.6,
                      color=cmap(k / max(q.max(), 1)),
                      label=f"quintile {int(k)+1}: mean {sel.mean():+.2f}")
    ax[0][0].set_yscale("log")
    ax[0][0].set_ylim(1e-5, 0.3)
    ax[0][0].set_xlabel("Δ BG per 5 min (mg/dL)", fontsize=9.5, color=S.INK2)
    ax[0][0].set_ylabel("density (log)", fontsize=9.5, color=S.INK2)
    ax[0][0].legend(frameon=False, fontsize=7.6, labelcolor=S.INK2, loc="lower center")
    ax[0][0].set_title(f"{ref}: velocity by insulin-activity quintile",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # Across everyone: how much does the mean shift between top and bottom
    # quintile, and how much does the spread change?
    shifts, spreads = [], []
    for a in order:
        c = D.clean(panels[a])
        q = pd.qcut(c["ia_abs"], 5, labels=False, duplicates="drop")
        lo, hi = c["v"][q == 0], c["v"][q == q.max()]
        shifts.append((a, hi.mean() - lo.mean()))
        spreads.append((a, hi.std() / lo.std()))
    al = [x[0] for x in shifts]
    y = np.arange(len(al))
    ax[0][1].barh(y, [x[1] for x in shifts],
                  color=[S.color_for(co, a) for a in al], alpha=0.88, height=0.72)
    ax[0][1].axvline(0, color=S.INK, lw=1.3)
    ax[0][1].set_yticks(y)
    ax[0][1].set_yticklabels(al, fontsize=8, color=S.INK2)
    ax[0][1].set_xlabel("mean velocity shift, top minus bottom quintile (mg/dL / 5 min)",
                        fontsize=9.5, color=S.INK2)
    ax[0][1].set_title("Bottom to top quintile shifts the mean by about one SD",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    ax[0][2].barh(y, [x[1] for x in spreads],
                  color=[S.color_for(co, a) for a in al], alpha=0.88, height=0.72)
    ax[0][2].axvline(1, color=S.INK, lw=1.5, ls=(0, (4, 2)))
    ax[0][2].set_yticks(y)
    ax[0][2].set_yticklabels(al, fontsize=8, color=S.INK2)
    ax[0][2].set_xlabel("velocity SD ratio, top / bottom quintile", fontsize=9.5,
                        color=S.INK2)
    ax[0][2].set_title("and widens it by half again",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # Insulin activity is itself a very smooth, very predictable variable.
    for a in order:
        p = panels[a]
        rs_ia = [g_.to_numpy() for _, g_ in
                 p["ia_abs"].groupby((p["bg"].isna()).cumsum()) if len(g_) > 80]
        if rs_ia:
            A = F.acf(rs_ia[:40], 72)
            ax[1][0].plot(np.arange(73) * 5, A, **S.line_style(co, a))
    for a in order:
        rs = F.runs(panels[a])
        vr = [np.diff(r) for r in rs if len(r) > 100]
        if vr:
            ax[1][0].plot(np.arange(73) * 5, F.acf(vr, 72), color=S.MUTED, lw=0.9,
                          alpha=0.45)
    ax[1][0].axhline(0, color=S.INK, lw=1.2)
    ax[1][0].set_xlabel("lag (minutes)", fontsize=9.5, color=S.INK2)
    ax[1][0].set_ylabel("autocorrelation", fontsize=9.5, color=S.INK2)
    ax[1][0].set_title("Insulin activity (coloured) vs velocity (grey)",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # Does subtracting insulin change the shape of the increment distribution?
    for a in order:
        c = D.clean(panels[a])
        col = S.color_for(co, a)
        for A, col_name in ((ax[1][1], "v"), (ax[1][2], "ice_abs")):
            x = c[col_name].to_numpy()
            b = np.mean(np.abs(x - np.median(x)))
            th, xs = F.qq_points((x - np.median(x)) / b, "laplace")
            A.plot(th, xs, **S.line_style(co, a))
    for A, ttl in ((ax[1][1], "velocity vs Laplace"),
                   (ax[1][2], "velocity + insulin activity vs Laplace")):
        A.plot([-9, 9], [-9, 9], color=S.INK, lw=1.5, ls=(0, (4, 2)))
        A.set_xlim(-9, 9)
        A.set_ylim(-9, 9)
        A.set_xlabel("Laplace quantile", fontsize=9.5, color=S.INK2)
        A.set_ylabel("standardised sample quantile", fontsize=9.5, color=S.INK2)
        A.set_title(ttl, fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    S.title(fig, "12 · Insulin activity against velocity",
            "Insulin activity is slow, smooth and strongly autocorrelated — its memory runs for hours where velocity's runs for minutes. "
            "Going from the lowest to the highest\ninsulin-activity quintile moves mean velocity by roughly one velocity SD and widens the spread by "
            "half again. Read that as association, not effect: the controller doses\nin response to glucose, so the conditioning is endogenous — "
            "one person (bddp08) even comes out positive. Subtracting insulin off does not simplify the shape.")
    S.save(fig, "12_insulin_joint",
           dict(left=0.06, right=0.985, top=0.885, bottom=0.075, hspace=0.42, wspace=0.30))


def main():
    co = S.cohort()
    panels = S.load_all()
    f11_noise(panels, co)
    f12_insulin_joint(panels, co)


if __name__ == "__main__":
    main()
