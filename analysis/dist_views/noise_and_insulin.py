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


def canonical_noise():
    """Per-person sensor noise sigma, from the ONE place it is fitted.

    `traits._hurst_and_noise` fits Var[dBG(tau)] = 2*sigma^2 + C*tau^(2H) and
    `wholerecord.py` writes it out; the volatility variance floor and the
    document's ledger both read it from there. This view used to refit the same
    intercept over its own lag set, which is how the figure came to say 1.12
    while the ledger beside it said 1.27 — one quantity, two fits, no error.
    Read it, never refit it.
    """
    f = S.OUT / "wholerecord.csv"
    if not f.exists():
        raise SystemExit("wholerecord.csv missing — run wholerecord.py first")
    w = pd.read_csv(f)
    return (w.set_index("alias")["sigma_meas"].to_dict(),
            w.set_index("alias")["v_sd"].to_dict())


def f11_noise(panels, co):
    order = S.order_by(co, "tir")
    fig, ax = S.figure(2, 3, figsize=(14.4, 9.0))
    mins = np.array([5, 10, 15, 20, 30, 40, 60, 90, 120])
    SIG, VSD = canonical_noise()
    rec = {}
    for a in order:
        sf = structure_function(a, mins)
        sig = float(SIG.get(a, np.nan))
        rec[a] = (sig, np.nan, np.nan, sf)
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

    # Everyone the noise is fitted for, not just the four-stream cohort: this
    # statistic needs glucose alone.
    al = sorted(SIG, key=lambda k: SIG[k] if np.isfinite(SIG[k]) else 0)
    sigs = np.array([SIG[a] for a in al], float)
    cols = [S.color_for(co, a) for a in al]
    S.strip_kde(ax[0][1], sigs, cols, fmt="{:.2f}")
    ax[0][1].axvline(1.0, color=S.MUTED, lw=1.4, ls=(0, (4, 2)))
    ax[0][1].text(1.0, 1.14, " 1 mg/dL", fontsize=8.5, color=S.MUTED, ha="left")
    ax[0][1].set_xlabel("implied per-reading sensor noise σ (mg/dL)", fontsize=9.5,
                        color=S.INK2)
    ax[0][1].set_title("Implied noise per reading", fontsize=10.5, color=S.INK,
                       loc="left", pad=6, weight="bold")

    # What share of observed 5-min velocity variance is just noise?
    share = [2 * SIG[a] ** 2 / VSD[a] ** 2 if np.isfinite(SIG[a]) else np.nan
             for a in al]
    share = np.array(share, float) * 100
    S.strip_kde(ax[0][2], share, cols, fmt="{:.0f}%")
    ax[0][2].set_xlim(0, max(1.0, np.nanmax(share)) * 1.12)
    ax[0][2].set_xlabel("share of 5-min velocity variance that is noise (%)",
                        fontsize=9.5, color=S.INK2)
    ax[0][2].set_title("Most of what a 5-minute delta reports is real",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # Signal-to-noise as a function of the horizon you difference over.
    # Signal-to-noise straight off the measured structure function — the signal
    # term is whatever the difference's variance has above the noise floor — so
    # nothing here depends on a second fit of its own.
    tau = np.array([5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 240], dtype=float)
    for a in order:
        sig = rec[a][0]
        if not np.isfinite(sig):
            continue
        sf = structure_function(a, tau)
        snr = (sf - 2 * sig ** 2) / (2 * sig ** 2)
        ok = np.isfinite(snr) & (snr > 0)
        ax[1][0].plot(tau[ok], snr[ok], **S.line_style(co, a))
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
    cmap = {r["alias"]: S.GROUP_COLOR.get(S.group_of(r), S.MUTED)
            for _, r in co.iterrows()}
    sample = S.sample_for(co)
    for a in al:
        sig, vsd = SIG[a], VSD[a]
        if not (np.isfinite(sig) and np.isfinite(vsd)):
            continue
        ax[1][2].scatter(vsd, sig, s=64, color=cmap.get(a, S.MUTED),
                         edgecolor=S.SURFACE, lw=1.2, zorder=3)
        ax[1][2].annotate(a if a in sample else "", (vsd, sig),
                          textcoords="offset points", xytext=(7, -3), fontsize=8,
                          color=S.INK2)
    ax[1][2].set_xlabel("raw-sample velocity SD (mg/dL / 5 min)", fontsize=9.5, color=S.INK2)
    ax[1][2].set_ylabel("implied sensor noise σ (mg/dL)", fontsize=9.5, color=S.INK2)
    ax[1][2].margins(x=0.16, y=0.18)
    ax[1][2].set_title("Noise is roughly constant; the spread is not",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    S.title(fig, "11 · How much of a 5-minute change is the sensor?",
            "Differences over τ minutes should have vanishing variance as τ → 0. They do not: the structure function hits a positive intercept, "
            "and that intercept is twice the\nper-reading measurement variance. Its median is 1.27 mg/dL and the middle 80% of people run 0.57 to 1.94 "
            "— small on any of those.\nA 5-minute delta is mostly real glucose, which is worth knowing before smoothing it away.")
    S.save(fig, "11_measurement_noise",
           dict(left=0.06, right=0.985, top=0.845, bottom=0.075, hspace=0.42, wspace=0.30))
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
    cols = [S.color_for(co, a) for a in al]
    S.strip_kde(ax[0][1], [x[1] for x in shifts], cols, fmt="{:.2f}")
    ax[0][1].axvline(0, color=S.INK, lw=1.3)
    ax[0][1].set_xlabel("mean velocity shift, top minus bottom quintile (mg/dL / 5 min)",
                        fontsize=9.5, color=S.INK2)
    ax[0][1].set_title("Top quintile shifts the mean by one SD",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    S.strip_kde(ax[0][2], [x[1] for x in spreads], cols, fmt="{:.2f}")
    ax[0][2].axvline(1, color=S.MUTED, lw=1.5, ls=(0, (4, 2)))
    ax[0][2].text(1.0, 1.14, " no change", fontsize=8.5, color=S.MUTED, ha="left")
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
           dict(left=0.06, right=0.985, top=0.845, bottom=0.075, hspace=0.42, wspace=0.30))


def main():
    co = S.cohort()
    panels = S.load_all()
    f11_noise(panels, co)
    f12_insulin_joint(panels, co)


if __name__ == "__main__":
    main()
