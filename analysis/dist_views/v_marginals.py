#!/usr/bin/env python3
"""Views 01-06: what the raw distributions look like, person by person."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt                       # noqa: E402
import style as S                                    # noqa: E402
from loopeval_analysis import dists as D             # noqa: E402



def _silverman(x) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return 1.06 * x.std() * len(x) ** (-1 / 5.0) if len(x) > 1 else 1.0


def _tail_limit(x, min_n: int) -> float:
    """The largest value with at least `min_n` samples at or beyond it."""
    x = np.sort(np.asarray(x, float))
    return float(x[-min_n]) if len(x) > min_n else 0.0


def f01_bg_ridgeline(panels, co):
    """Every person's glucose distribution, stacked and ordered by TIR."""
    order = S.order_by(co, "tir")
    samp = set(S.sample_for(co))
    ridge = [a for a in order if a in samp]          # 12 rows, not 73
    fig, (axL, axR) = S.figure(1, 2, figsize=(13.6, 9.4),
                               gridspec_kw={"width_ratios": [2.05, 1]})
    grid = np.linspace(35, 400, 500)
    step = 1.0
    for i, a in enumerate(ridge):
        c = D.clean(panels[a])
        d = S.kde(c["bg"], grid)
        d = d / d.max() * 0.92
        y = (len(ridge) - 1 - i) * step
        col = S.color_for(co, a)
        axL.fill_between(grid, y, y + d, color=col, alpha=0.55, lw=0)
        axL.plot(grid, y + d, color=col, lw=1.2)
        r = co[co["alias"] == a].iloc[0]
        axL.text(392, y + 0.12, f"{a}   TIR {r['tir']:.0f}", fontsize=8.5,
                 color=S.INK2, ha="right")
    axL.axvspan(70, 180, color=S.GREEN, alpha=0.07, lw=0, zorder=0)
    for x in (70, 180):
        axL.axvline(x, color=S.GREEN, lw=1.0, ls=(0, (3, 3)), zorder=1)
    axL.axvline(54, color=S.ACCENT, lw=1.0, ls=(0, (2, 2)), zorder=1)
    axL.set_xlim(35, 400)
    axL.set_ylim(-0.15, len(ridge) * step + 0.2)
    axL.set_yticks([])
    axL.set_xlabel("glucose (mg/dL)", fontsize=9.5, color=S.INK2)
    axL.set_title(f"{len(ridge)} representative people, ordered by time in range",
                  fontsize=11, color=S.INK, loc="left", pad=8, weight="bold")

    # Right: the same distributions on a log density axis, to show the tails.
    for a in order:
        c = D.clean(panels[a])
        d = S.kde(c["bg"], grid)
        axR.plot(grid, np.maximum(d, 1e-7), **S.line_style(co, a))
    axR.set_yscale("log")
    axR.set_ylim(1e-6, 3e-2)
    axR.set_xlim(35, 400)
    axR.axvspan(70, 180, color=S.GREEN, alpha=0.07, lw=0, zorder=0)
    axR.set_xlabel("glucose (mg/dL)", fontsize=9.5, color=S.INK2)
    axR.set_ylabel("density (log)", fontsize=9.5, color=S.INK2)
    axR.set_title("Same curves, log density — the tails", fontsize=11,
                  color=S.INK, loc="left", pad=8, weight="bold")

    S.title(fig, "01 · Glucose marginals",
            "Every distribution is right-skewed: the ceiling is far away and the floor is defended. "
            "Low tails differ by orders of magnitude between people;\nhigh tails differ by much less. "
            "Colour = behaviour group (blue non-announcer, green moderate, orange heavy announcer).")
    S.save(fig, "01_bg_marginals",
           dict(left=0.03, right=0.985, top=0.885, bottom=0.065, wspace=0.16))


def f02_velocity_marginals(panels, co):
    """Glucose velocity: tails, asymmetry, and how far from Gaussian it is."""
    order = S.order_by(co, "tir")
    fig, ax = S.figure(2, 2, figsize=(13.6, 8.8))
    grid = np.linspace(-25, 25, 400)

    for a in order:
        d = S.kde(S.raw_delta(a), grid)
        ax[0][0].plot(grid, np.maximum(d, 1e-7), **S.line_style(co, a))
    g = np.linspace(-25, 25, 400)
    sd = float(np.nanmedian([S.raw_delta(a).std() for a in order]))
    ax[0][0].plot(g, np.exp(-0.5 * (g / sd) ** 2) / (sd * np.sqrt(2 * np.pi)),
                  color=S.INK, lw=1.6, ls=(0, (4, 2)),
                  label=f"Gaussian, sd={sd:.1f}")
    ax[0][0].set_yscale("log")
    ax[0][0].set_ylim(1e-6, 0.5)
    ax[0][0].set_xlabel("Δ glucose per 5 min (mg/dL)", fontsize=9.5, color=S.INK2)
    ax[0][0].set_ylabel("density (log)", fontsize=9.5, color=S.INK2)
    ax[0][0].legend(frameon=False, fontsize=8.5, labelcolor=S.INK2, loc="lower center")
    ax[0][0].set_title("Velocity has far heavier tails than a Gaussian",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # Asymmetry: rise side vs fall side of the same distribution, folded over.
    #
    # Two things make this ratio ripple if you let them. The default Silverman
    # bandwidth is chosen for the BULK (median 0.64 mg/dL here) and is far too
    # narrow for the sparse tail, where each isolated sample becomes its own
    # bump — and a ratio of two such estimates oscillates on the scale of the
    # kernel. So floor the bandwidth. Then stop each line where the estimate
    # stops being an estimate: past the point where a side has fewer than
    # MIN_TAIL samples left, the curve is drawing individual observations.
    MIN_TAIL = 40
    pos = np.linspace(0, 25, 300)
    for a in order:
        v = S.raw_delta(a)
        up = S.kde(v[v > 0], pos, bw=max(1.2, _silverman(v[v > 0])))
        dn = S.kde(-v[v < 0], pos, bw=max(1.2, _silverman(-v[v < 0])))
        lim = min(_tail_limit(v[v > 0], MIN_TAIL), _tail_limit(-v[v < 0], MIN_TAIL))
        m = pos <= lim
        ax[0][1].plot(pos[m], np.maximum(up[m] / np.maximum(dn[m], 1e-9), 1e-3),
                      **S.line_style(co, a))
    ax[0][1].axhline(1.0, color=S.INK, lw=1.4, ls=(0, (4, 2)))
    ax[0][1].set_yscale("log")
    ax[0][1].set_ylim(0.2, 6)
    ax[0][1].set_xlim(0, 16)
    ax[0][1].set_xlabel("|Δ glucose| per 5 min (mg/dL)", fontsize=9.5, color=S.INK2)
    ax[0][1].set_ylabel("density(rise) / density(fall)", fontsize=9.5, color=S.INK2)
    ax[0][1].set_title("Rises outnumber falls only once they get big",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # 30-min velocity — much less sensor noise, the physiologically real motion.
    grid30 = np.linspace(-90, 90, 400)
    for a in order:
        d = S.kde(S.raw_delta(a, 30), grid30)
        ax[1][0].plot(grid30, np.maximum(d, 1e-8), **S.line_style(co, a))
    ax[1][0].set_yscale("log")
    ax[1][0].set_ylim(1e-7, 0.1)
    ax[1][0].set_xlabel("Δ glucose per 30 min (mg/dL)", fontsize=9.5, color=S.INK2)
    ax[1][0].set_ylabel("density (log)", fontsize=9.5, color=S.INK2)
    ax[1][0].set_title("Over 30 min the asymmetry is unmistakable",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # Excess kurtosis vs sd — where each person sits.
    for _, r in co.iterrows():
        col = S.GROUP_COLOR.get(S.group_of(r), S.MUTED)
        dv = pd.Series(S.raw_delta(r["alias"]))
        r = dict(r); r["v_sd"], r["v_kurt"] = dv.std(), dv.kurtosis()
        ax[1][1].scatter(r["v_sd"], r["v_kurt"], s=64, color=col,
                         edgecolor=S.SURFACE, lw=1.2, zorder=3)
        ax[1][1].annotate(r["alias"] if r["alias"] in S.sample_for(co) else "", (r["v_sd"], r["v_kurt"]),
                          textcoords="offset points", xytext=(7, -3),
                          fontsize=8, color=S.INK2)
    ax[1][1].axhline(0, color=S.INK, lw=1.2, ls=(0, (4, 2)))
    ax[1][1].set_yscale("symlog", linthresh=1)
    ax[1][1].set_xlabel("velocity SD (mg/dL / 5 min)", fontsize=9.5, color=S.INK2)
    ax[1][1].set_ylabel("excess kurtosis (symlog)", fontsize=9.5, color=S.INK2)
    ax[1][1].set_title("Spread and tail-weight are nearly independent",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    S.title(fig, "02 · Glucose velocity marginals",
            "Velocity is the quantity a forecast has to get right. It is sharply peaked, heavy-tailed and asymmetric — "
            "three properties a Gaussian error model gets wrong\nin three different directions.")
    S.save(fig, "02_velocity_marginals",
           dict(left=0.055, right=0.985, top=0.875, bottom=0.07, hspace=0.36, wspace=0.19))


def f03_phase_plane(panels, co):
    """The (glucose, velocity) phase plane — where each person actually lives."""
    samp = set(S.sample_for(co))
    order = [a for a in S.order_by(co, "tir") if a in samp]
    n = len(order)
    ncol = 4
    nrow = int(np.ceil(n / ncol))
    fig, ax = S.figure(nrow, ncol, figsize=(14.5, 3.0 * nrow + 1.5))
    axf = ax.ravel()
    xe = np.linspace(40, 350, 78)
    ye = np.linspace(-22, 22, 68)
    xc = 0.5 * (xe[:-1] + xe[1:])
    for i, a in enumerate(order):
        A = axf[i]
        c = D.clean(panels[a])
        H, _, _ = np.histogram2d(c["bg"], c["v"], bins=[xe, ye])
        H = H / H.sum()
        Hm = np.ma.masked_where(H.T <= 0, np.log10(np.maximum(H.T, 1e-12)))
        top = float(np.log10(H.max()))
        cmap = plt.get_cmap("magma_r").copy()
        cmap.set_bad(S.SURFACE)
        A.pcolormesh(xe, ye, Hm, cmap=cmap, vmin=top - 3.4, vmax=top,
                     shading="flat", rasterized=True)
        A.axhline(0, color=S.INK2, lw=0.9, ls=(0, (3, 3)), zorder=4)
        for x in (70, 180):
            A.axvline(x, color="#5bbf95", lw=0.9, ls=(0, (2, 2)), zorder=4)

        # Restoring force on its own scale, so a ±3 mg/dL signal is readable
        # inside a ±22 mg/dL cloud without being exaggerated.
        idx = np.digitize(c["bg"], xe) - 1
        ok = (idx >= 0) & (idx < len(xe) - 1)
        g = pd.DataFrame({"i": idx[ok], "v": c["v"].to_numpy()[ok]}).groupby("i")
        mv, cnt = g["v"].mean(), g["v"].size()
        mv = mv[cnt >= 50]
        A2 = A.twinx()
        A2.plot(xc[mv.index], mv.to_numpy(), color="#0f9d6d", lw=2.0, zorder=5)
        A2.axhline(0, color="#0f9d6d", lw=0.7, alpha=0.35, zorder=3)
        A2.set_ylim(-4.2, 4.2)
        A2.spines["top"].set_visible(False)
        A2.spines["left"].set_visible(False)
        A2.spines["right"].set_color("#0f9d6d")
        A2.tick_params(colors="#0f9d6d", labelsize=7.5)
        if i % ncol != ncol - 1 and i != n - 1:
            A2.set_yticklabels([])

        r = co[co["alias"] == a].iloc[0]
        A.set_title(f"{a} · TIR {r['tir']:.0f} · {S.group_of(r) or r['algo']}",
                    fontsize=9, color=S.INK, loc="left", pad=5)
        A.set_xlim(40, 350)
        A.set_ylim(-22, 22)
        if i % ncol == 0:
            A.set_ylabel("Δ BG / 5 min", fontsize=8.5, color=S.INK2)
        if i >= n - ncol:
            A.set_xlabel("glucose (mg/dL)", fontsize=8.5, color=S.INK2)
    for j in range(n, len(axf)):
        axf[j].set_visible(False)
    S.title(fig, "03 · The phase plane: glucose against its own velocity",
            "Log density of every 5-minute sample (dark = where the person spends time). The green line is mean velocity at each glucose — "
            "the restoring force — drawn on its own\nright-hand scale of ±4 mg/dL per 5 min, because it is a small signal inside a wide cloud. "
            "It crosses zero near the glucose each system actually defends.")
    S.save(fig, "03_phase_plane",
           dict(left=0.045, right=0.955, top=1 - 0.44 / nrow, bottom=0.06,
                hspace=0.44, wspace=0.30))


def f04_restoring_force(panels, co):
    """All the restoring-force curves on one axis, plus its spread."""
    order = S.order_by(co, "tir")
    fig, ax = S.figure(1, 3, figsize=(14.2, 5.2))
    edges = np.linspace(40, 340, 46)
    ctr = 0.5 * (edges[:-1] + edges[1:])
    for a in order:
        c = D.clean(panels[a])
        idx = np.digitize(c["bg"], edges) - 1
        ok = (idx >= 0) & (idx < len(edges) - 1)
        g = pd.DataFrame({"i": idx[ok], "v": c["v"].to_numpy()[ok],
                          "v30": c["v30"].to_numpy()[ok]}).groupby("i")
        m, sd, cnt = g["v"].mean(), g["v"].std(), g["v"].size()
        m, sd = m[cnt >= 40], sd[cnt >= 40]
        col = S.color_for(co, a)
        ax[0].plot(ctr[m.index], m.to_numpy(), **S.line_style(co, a))
        ax[1].plot(ctr[sd.index], sd.to_numpy(), **S.line_style(co, a))
    ax[0].axhline(0, color=S.INK, lw=1.3, ls=(0, (4, 2)))
    ax[0].set_xlabel("glucose (mg/dL)", fontsize=9.5, color=S.INK2)
    ax[0].set_ylabel("mean Δ BG per 5 min", fontsize=9.5, color=S.INK2)
    ax[0].set_title("Restoring force", fontsize=10.5, color=S.INK, loc="left",
                    pad=6, weight="bold")
    ax[1].set_xlabel("glucose (mg/dL)", fontsize=9.5, color=S.INK2)
    ax[1].set_ylabel("SD of Δ BG per 5 min", fontsize=9.5, color=S.INK2)
    ax[1].set_title("Volatility rises with glucose", fontsize=10.5, color=S.INK,
                    loc="left", pad=6, weight="bold")

    # Where does the restoring force cross zero, and how steep is it there?
    for _, r in co.iterrows():
        a = r["alias"]
        c = D.clean(panels[a])
        idx = np.digitize(c["bg"], edges) - 1
        ok = (idx >= 0) & (idx < len(edges) - 1)
        g = pd.DataFrame({"i": idx[ok], "v": c["v"].to_numpy()[ok]}).groupby("i")
        m, cnt = g["v"].mean(), g["v"].size()
        m = m[cnt >= 40]
        x, y = ctr[m.index], m.to_numpy()
        sel = (x > 80) & (x < 300)
        if sel.sum() < 5:
            continue
        sl = np.polyfit(x[sel], y[sel], 1)
        cross = -sl[1] / sl[0] if sl[0] != 0 else np.nan
        col = S.GROUP_COLOR.get(S.group_of(r), S.MUTED)
        ax[2].scatter(cross, -sl[0] * 1000, s=64, color=col,
                      edgecolor=S.SURFACE, lw=1.2, zorder=3)
        ax[2].annotate(a if a in S.sample_for(co) else "", (cross, -sl[0] * 1000), textcoords="offset points",
                       xytext=(7, -3), fontsize=8, color=S.INK2)
    ax[2].set_xlabel("zero-crossing: the glucose the system holds (mg/dL)",
                     fontsize=9.5, color=S.INK2)
    ax[2].set_ylabel("pull-back strength (×10⁻³ per 5 min)", fontsize=9.5, color=S.INK2)
    ax[2].set_title("Set point vs stiffness", fontsize=10.5, color=S.INK,
                    loc="left", pad=6, weight="bold")
    S.title(fig, "04 · The restoring force, isolated",
            "Mean velocity as a function of current glucose, for each person. The zero-crossing is the glucose their whole system "
            "(loop + behaviour + physiology) actually defends;\nthe slope is how hard it pulls. These are two separable knobs, and people differ on both.")
    S.save(fig, "04_restoring_force",
           dict(left=0.05, right=0.99, top=0.80, bottom=0.11, wspace=0.24))


def f05_insulin_activity(panels, co):
    """Insulin activity: absolute vs Loop's net convention, and the basal share."""
    order = S.order_by(co, "tir")
    fig, ax = S.figure(2, 2, figsize=(13.6, 8.8))
    grid = np.linspace(-4, 22, 400)
    for a in order:
        c = D.clean(panels[a])
        ax[0][0].plot(grid, np.maximum(S.kde(c["ia_abs"], grid), 1e-7),
                      **S.line_style(co, a))
        ax[0][1].plot(grid, np.maximum(S.kde(c["ia_net"], grid), 1e-7),
                      **S.line_style(co, a))
    for A, t in ((ax[0][0], "Absolute insulin activity — every unit in the body"),
                 (ax[0][1], "Net of the basal schedule — what Loop prices")):
        A.set_yscale("log")
        A.set_ylim(1e-5, 2)
        A.set_xlim(-4, 22)
        A.axvline(0, color=S.INK, lw=1.2, ls=(0, (4, 2)))
        A.set_xlabel("BG-lowering delivered per 5 min (mg/dL)", fontsize=9.5, color=S.INK2)
        A.set_ylabel("density (log)", fontsize=9.5, color=S.INK2)
        A.set_title(t, fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # The gap between the two conventions, per person: the SCHEDULED stream's
    # share of all insulin action. Not the delivered-basal share, which for a
    # temp-basal-strategy user would count every correction Loop made.
    col_share = "ia_sched_share" if "ia_sched_share" in co else "ia_basal_share"
    al = list(co.sort_values(col_share)["alias"])
    y = np.arange(len(al))
    share = [co.loc[co["alias"] == a, col_share].iloc[0] for a in al]
    cols = [S.color_for(co, a) for a in al]
    ax[1][0].barh(y, share, color=cols, alpha=0.85, height=0.72)
    if len(al) > 30:
        ax[1][0].set_yticks([])
        ax[1][0].set_ylabel(f"{len(al)} people, sorted", fontsize=9, color=S.INK2)
    else:
        ax[1][0].set_yticks(y)
        ax[1][0].set_yticklabels(al, fontsize=8.5, color=S.INK2)
    ax[1][0].set_xlim(0, 0.92)
    med = float(np.median(share))
    ax[1][0].axvline(med, color=S.INK, lw=1.4, ls=(0, (4, 2)))
    ax[1][0].text(med + 0.01, len(al) * 0.04, f"median {med*100:.0f}%", fontsize=8.5,
                  color=S.INK, va="bottom")
    ax[1][0].set_xlabel("share of all insulin action coming from scheduled basal",
                        fontsize=9.5, color=S.INK2)
    ax[1][0].set_title("The part a basal-relative forecast books at zero",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")
    for yi, s in zip(y, share):
        if len(al) <= 30:
            ax[1][0].text(s + 0.008, yi, f"{s*100:.0f}%", va="center", fontsize=8,
                          color=S.INK2)

    # Insulin activity against glucose: is insulin acting when glucose is high?
    edges = np.linspace(40, 340, 40)
    ctr = 0.5 * (edges[:-1] + edges[1:])
    for a in order:
        c = D.clean(panels[a])
        idx = np.digitize(c["bg"], edges) - 1
        ok = (idx >= 0) & (idx < len(edges) - 1)
        g = pd.DataFrame({"i": idx[ok], "ia": c["ia_abs"].to_numpy()[ok]}).groupby("i")
        m, cnt = g["ia"].mean(), g["ia"].size()
        m = m[cnt >= 40]
        ax[1][1].plot(ctr[m.index], m.to_numpy(), **S.line_style(co, a))
    ax[1][1].set_xlabel("glucose (mg/dL)", fontsize=9.5, color=S.INK2)
    ax[1][1].set_ylabel("mean insulin activity (mg/dL / 5 min)", fontsize=9.5, color=S.INK2)
    ax[1][1].set_title("Insulin action rises with glucose — but only mildly",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")
    S.title(fig, "05 · Insulin activity",
            "How much BG-lowering insulin delivers in each 5-minute bin. Left: the physiological quantity, every unit in the body. Right: the same "
            "stream as Loop measures it,\nwith the basal schedule subtracted. The bar chart is the difference — the scheduled stream is 3% to 81% "
            "of all insulin action, median 48%, and a basal-relative\nforecast books it at zero. This is the schedule only; a temp-basal-strategy "
            "user's corrections are not counted as basal here.")
    S.save(fig, "05_insulin_activity",
           dict(left=0.075, right=0.985, top=0.835, bottom=0.07, hspace=0.38, wspace=0.2))


def f06_ice(panels, co):
    """The non-insulin side: everything glucose does that insulin did not do."""
    order = S.order_by(co, "tir")
    fig, ax = S.figure(2, 2, figsize=(13.6, 8.8))
    grid = np.linspace(-25, 35, 420)
    for a in order:
        c = D.clean(panels[a])
        ax[0][0].plot(grid, np.maximum(S.kde(c["ice_abs"], grid), 1e-7),
                      **S.line_style(co, a))
        ax[0][1].plot(grid, np.maximum(S.kde(c["ice_net"], grid), 1e-7),
                      **S.line_style(co, a))
    for A, t in ((ax[0][0], "Non-insulin flux (absolute convention)"),
                 (ax[0][1], "The same thing Loop's retrospective correction sees")):
        A.set_yscale("log")
        A.set_ylim(1e-6, 0.4)
        A.axvline(0, color=S.INK, lw=1.2, ls=(0, (4, 2)))
        A.set_xlabel("mg/dL per 5 min", fontsize=9.5, color=S.INK2)
        A.set_ylabel("density (log)", fontsize=9.5, color=S.INK2)
        A.set_title(t, fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # Mean non-insulin appearance rate vs mean insulin action: they must balance.
    for _, r in co.iterrows():
        col = S.GROUP_COLOR.get(S.group_of(r), S.MUTED)
        ax[1][0].scatter(r["ia_abs_mean"], r["ice_abs_mean"], s=66, color=col,
                         edgecolor=S.SURFACE, lw=1.2, zorder=3)
        ax[1][0].annotate(r["alias"] if r["alias"] in S.sample_for(co) else "", (r["ia_abs_mean"], r["ice_abs_mean"]),
                          textcoords="offset points", xytext=(7, -3), fontsize=8,
                          color=S.INK2)
    lim = [0, max(co["ia_abs_mean"].max(), co["ice_abs_mean"].max()) * 1.08]
    ax[1][0].plot(lim, lim, color=S.INK, lw=1.3, ls=(0, (4, 2)), zorder=1)
    ax[1][0].set_xlim(lim)
    ax[1][0].set_ylim(lim)
    ax[1][0].set_xlabel("mean insulin action (mg/dL / hr)", fontsize=9.5, color=S.INK2)
    ax[1][0].set_ylabel("mean non-insulin appearance (mg/dL / hr)", fontsize=9.5, color=S.INK2)
    ax[1][0].set_title("Over months the two sides balance exactly",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # Does non-insulin flux depend on glucose level?
    edges = np.linspace(40, 340, 40)
    ctr = 0.5 * (edges[:-1] + edges[1:])
    for a in order:
        c = D.clean(panels[a])
        idx = np.digitize(c["bg"], edges) - 1
        ok = (idx >= 0) & (idx < len(edges) - 1)
        g = pd.DataFrame({"i": idx[ok], "e": c["ice_abs"].to_numpy()[ok]}).groupby("i")
        m, cnt = g["e"].mean(), g["e"].size()
        m = m[cnt >= 40]
        ax[1][1].plot(ctr[m.index], m.to_numpy() * 12, **S.line_style(co, a))
    ax[1][1].axhline(0, color=S.INK, lw=1.2, ls=(0, (4, 2)))
    ax[1][1].set_xlabel("glucose (mg/dL)", fontsize=9.5, color=S.INK2)
    ax[1][1].set_ylabel("mean non-insulin flux (mg/dL / hr)", fontsize=9.5, color=S.INK2)
    ax[1][1].set_title("It falls steeply as glucose rises",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")
    S.title(fig, "06 · The non-insulin side",
            "Velocity plus insulin activity leaves everything insulin did not do: glucose production, carbs, exercise, sensor noise. "
            "Its mean is large — 36 to 178 mg/dL per hour —\nand it must equal mean insulin action over a long window, which is the "
            "check in the lower left. The lower right is the part worth staring at.")
    S.save(fig, "06_non_insulin",
           dict(left=0.06, right=0.985, top=0.875, bottom=0.07, hspace=0.38, wspace=0.2))


def main():
    co = S.cohort()
    panels = S.load_all()
    f01_bg_ridgeline(panels, co)
    f02_velocity_marginals(panels, co)
    f03_phase_plane(panels, co)
    f04_restoring_force(panels, co)
    f05_insulin_activity(panels, co)
    f06_ice(panels, co)


if __name__ == "__main__":
    main()
