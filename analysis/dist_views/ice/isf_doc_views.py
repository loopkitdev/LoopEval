#!/usr/bin/env python3
"""Figures r01-r05 for the ISF estimation rationale page.
Reads ice/isf_basal_prior.csv (run isf_basal_prior.py first)."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
np.seterr(all="ignore")
import pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_first import _quiet_mask  # noqa

co = S.cohort()
d = pd.read_csv(S.OUT / "ice" / "isf_basal_prior.csv")
pct = lambda x: 100 * (np.exp(x) - 1)
col = lambda aliases: [S.color_for(co, a) for a in aliases]


def logaxes(a, lim, ticks=(10, 25, 50, 100, 250)):
    a.set_xscale("log"); a.set_yscale("log"); a.set_xlim(lim); a.set_ylim(lim)
    a.set_xticks(ticks); a.set_yticks(ticks)
    for x_ in (a.xaxis, a.yaxis):
        x_.set_major_formatter(S.plt.FuncFormatter(lambda v, _: f"{v:g}"))
    a.minorticks_off()
    a.plot(lim, lim, color=S.MUTED, lw=1, ls="--", zorder=1)


# ── r01: the measurement, one person ────────────────────────────────────
LEV = None


def r01_draw():
    global LEV
    alias, b1, r, fig, ax = None, None, None, None, None
    # level factor: E = exp(prior + w (c - prior)) * L with prior = log Bb + offset.
    L = np.nanmedian(d.A_all) / np.nanmedian(np.exp(np.log(d.Bb_all) + np.nanmedian(np.log(d.C_all / d.Bb_all))
                                                    + d.w_basal * (np.log(d.C_all) - np.log(d.Bb_all)
                                                                   - np.nanmedian(np.log(d.C_all / d.Bb_all)))))
    LEV = L
    samp = S.sample_for(co)
    s = d[d.alias.isin(samp) & d.C_all.notna()].copy()
    s["dist"] = np.abs(np.log(s.C_all / s.A_all) - np.log(0.5)) + np.abs(s.w_basal - 0.9)
    alias = s.sort_values("dist").alias.iloc[0]
    r = d[d.alias == alias].iloc[0]
    p = S.load(alias); p = p[p["bg"].notna() | p["v"].notna()]
    q = _quiet_mask(p)
    u = p["ia_abs"].to_numpy() / p["isf"].to_numpy(); v = p["v"].to_numpy()
    n = len(p) // 12 * 12
    m = q[:n].reshape(-1, 12).all(1)
    dv = v[:n].reshape(-1, 12).sum(1)[m]; du = u[:n].reshape(-1, 12).sum(1)[m]
    b1, b0 = np.polyfit(du, dv, 1)
    off = np.nanmedian(np.log(d.C_all / d.Bb_all))
    shrunk_raw = np.exp(np.log(r.Bb_all) + off + r.w_basal * (np.log(r.C_all) - np.log(r.Bb_all) - off))
    fig, ax = S.figure(1, 2, figsize=(13, 5.8), gridspec_kw={"width_ratios": [1.55, 1]})
    a = ax[0]
    a.scatter(du, dv, s=6, color=S.COOL, alpha=0.16, lw=0)
    edges = np.quantile(du, np.linspace(0, 1, 11))
    mids = [du[(du >= lo) & (du <= hi)].mean() for lo, hi in zip(edges[:-1], edges[1:])]
    means = [dv[(du >= lo) & (du <= hi)].mean() for lo, hi in zip(edges[:-1], edges[1:])]
    a.plot(mids, means, "o", color=S.INK, ms=6, zorder=5, label="average of each tenth of the hours")
    xx = np.linspace(du.min(), du.max(), 50)
    a.plot(xx, b0 + b1 * xx, color=S.ACCENT, lw=2.4, zorder=6,
           label=f"fitted line: {-b1:.0f} mg/dL less per extra unit")
    a.axhline(0, color=S.INK2, lw=0.7)
    a.set_ylim(np.percentile(dv, 1) - 5, np.percentile(dv, 99) + 5)
    a.set_xlabel("insulin absorbed during the hour, units", fontsize=9, color=S.INK2)
    a.set_ylabel("glucose change over the hour, mg/dL", fontsize=9, color=S.INK2)
    a.legend(fontsize=8.5, frameon=False, loc="upper right")
    a.set_title(f"One person's {len(dv):,} quiet hours", loc="left", fontsize=11, color=S.INK)
    a = ax[1]
    a.set_xticks([]); a.set_yticks([]); a.grid(False)
    for s_ in a.spines.values():
        s_.set_visible(False)
    rows = [("Raw slope of the quiet hours", -b1, S.ACCENT),
            (f"Pulled {100*(1-r.w_basal):.0f}% of the way toward\nthe basal rule ({np.exp(np.log(r.Bb_all)+off):.0f} at this level)", shrunk_raw, S.INK2),
            (f"× {L:.2f}, the one shared level factor", shrunk_raw * L, S.INK),
            ("Their scheduled ISF, for comparison", r.A_all, S.MUTED)]
    a.set_xlim(0, 1); a.set_ylim(0, 1)
    for i, (lab, val, c) in enumerate(rows):
        y = 0.84 - i * 0.22
        a.text(0.02, y, lab, fontsize=10, color=S.INK2, va="center", linespacing=1.35)
        a.text(0.98, y, f"{val:.0f}", fontsize=22, color=c, va="center", ha="right", weight="bold")
        if i < 3:
            a.plot([0.02, 0.98], [y - 0.11, y - 0.11], color=S.RULE, lw=1)
    a.text(0.98, 0.99, "mg/dL per unit", fontsize=8.5, color=S.MUTED, ha="right", va="top")
    a.set_title("From slope to estimate", loc="left", fontsize=11, color=S.INK)
    S.title(fig, "The measurement: how much more glucose falls in hours with more insulin",
            "Quiet hours only: no announced carbs on board, no user bolus in the prior 4 h, no pump or sensor disruption. "
            "One person from the study's representative sample.")
    S.save(fig, "r01_measure", tight=dict(left=0.06, right=0.98, top=0.82, bottom=0.11, wspace=0.12))
    return alias


# ── r02: the level, and why it needs a shared factor ─────────────────────
def r02():
    fig, ax = S.figure(1, 2, figsize=(13, 5.6))
    a = ax[0]
    r = (d.C_all / d.A_all).where(d.C_all > 0)
    S.strip_kde(a, r, col(d.alias), fmt="{:.2f}")
    a.axvline(1, color=S.ACCENT, lw=1.4, ls="--")
    a.text(1.02, 1.12, "the schedule", color=S.ACCENT, fontsize=8.5)
    a.set_xlabel("raw slope ÷ scheduled ISF", fontsize=9, color=S.INK2)
    a.set_title("The raw slope runs at about half of people's settings", loc="left", fontsize=11, color=S.INK)
    a = ax[1]
    a.scatter(d.A_all, d.E_basal_all, s=16, c=col(d.alias), alpha=0.85, lw=0)
    logaxes(a, (8, 250))
    rho = stats.spearmanr(d.A_all, d.E_basal_all, nan_policy="omit")[0]
    q = (d.E_basal_all / d.A_all).quantile([.1, .9])
    a.set_xlabel("scheduled ISF, mg/dL per U", fontsize=9, color=S.INK2)
    a.set_ylabel("final estimate, mg/dL per U", fontsize=9, color=S.INK2)
    a.set_title(f"After the shared factor: ranks like the schedule (ρ {rho:.2f})", loc="left", fontsize=11, color=S.INK)
    a.text(0.97, 0.04, f"estimate ÷ schedule\np10 {q.iloc[0]:.2f} · median 1.00 · p90 {q.iloc[1]:.2f}",
           transform=a.transAxes, ha="right", va="bottom", fontsize=8.5, color=S.INK2, linespacing=1.5)
    S.title(fig, "One number sets the level; it moves no one relative to anyone else",
            f"Every person is multiplied by the same ×{LEV:.2f}, chosen so the cohort median equals the scheduled median.")
    S.save(fig, "r02_level", tight=dict(left=0.04, right=0.98, top=0.81, bottom=0.12, wspace=0.22))


# ── r03: shrinkage ───────────────────────────────────────────────────────
def r03():
    fig, ax = S.figure(1, 2, figsize=(13, 5.6))
    a = ax[0]
    S.strip_kde(a, d.w_basal, col(d.alias), fmt="{:.2f}", note_x=0.7)
    a.set_xlim(0, 1.02)
    a.set_xlabel("weight on the person's own slope   (0 = rule only, 1 = own data only)", fontsize=9, color=S.INK2)
    a.set_title("Most people keep almost all of their own measurement", loc="left", fontsize=11, color=S.INK)
    a = ax[1]
    raw = d.C_all * LEV
    ok = raw > 0
    a.scatter(raw[ok], d.E_basal_all[ok], s=18, c=d.w_basal[ok], cmap="viridis", vmin=0.5, vmax=1, alpha=0.9, lw=0)
    logaxes(a, (5, 300))
    sm = S.plt.cm.ScalarMappable(cmap="viridis", norm=S.plt.Normalize(0.5, 1)); sm.set_array([])
    cb = fig.colorbar(sm, ax=a, fraction=0.04, pad=0.02); cb.set_label("weight on own slope", fontsize=8.5, color=S.INK2)
    cb.ax.tick_params(labelsize=8)
    a.set_xlabel("own slope alone (same shared factor)", fontsize=9, color=S.INK2)
    a.set_ylabel("final estimate", fontsize=9, color=S.INK2)
    moved = np.abs(np.log(d.E_basal_all[ok] / raw[ok]))
    a.set_title(f"Noisy slopes move most; median move {pct(np.median(moved)):.0f}%", loc="left", fontsize=11, color=S.INK)
    S.title(fig, "When a person's own slope is noisy, lean on what is typical for their basal rate",
            "The weight is set by how uncertain the slope is against how much people genuinely differ. "
            "Points off the dashed line were pulled toward the basal rule.")
    S.save(fig, "r03_shrink", tight=dict(left=0.04, right=0.97, top=0.81, bottom=0.12, wspace=0.22))


# ── r04: why basal, not daily insulin ────────────────────────────────────
def r04():
    fig, ax = S.figure(1, 2, figsize=(13, 5.6), sharey=True)
    for a, est, prior, ttl in ((ax[0], "E_tdd_all", "B_all", "Daily-insulin rule"),
                               (ax[1], "E_basal_all", "Bb_all", "Basal rule")):
        dd = d[(d[est] > 0) & d[prior].notna()]
        lv = np.log(dd[est] / dd[prior]); lv -= lv.median()
        a.scatter(dd.carb_g_day, pct(lv), s=16, c=col(dd.alias), alpha=0.85, lw=0)
        a.set_xscale("symlog", linthresh=10)
        a.axhline(0, color=S.MUTED, lw=0.8)
        rho, p = stats.spearmanr(np.log1p(dd.carb_g_day), lv)
        a.set_xlabel("announced carbohydrate, g per day", fontsize=9, color=S.INK2)
        a.set_title(f"Shrunk toward the {ttl.lower()}:  ρ {rho:+.2f}, p {p:.2g}", loc="left", fontsize=11, color=S.INK)
    ax[0].set_ylabel("estimate ÷ rule, % (cohort median = 0)", fontsize=9, color=S.INK2)
    S.title(fig, "Daily insulin includes meal insulin, so a daily-insulin rule mistakes appetite for resistance",
            "Departure from each rule against how much a person announces. Against the basal rule the link disappears. "
            "Blue non-announcers, green moderate, orange heavy.")
    S.save(fig, "r04_why_basal", tight=dict(left=0.06, right=0.98, top=0.81, bottom=0.12, wspace=0.08))


# ── r05: repeatability ───────────────────────────────────────────────────
def r05():
    fig, ax = S.figure(1, 2, figsize=(13, 5.8))
    for a, h1, h2, ttl, lev in ((ax[0], "C_h1", "C_h2", "Own slope alone", LEV),
                                (ax[1], "E_basal_h1", "E_basal_h2", "Final estimate", 1.0)):
        h = d[["alias", h1, h2]].dropna(); h = h[(h[h1] > 0) & (h[h2] > 0)]
        x, y = h[h1] * lev, h[h2] * lev
        a.scatter(x, y, s=16, c=col(h.alias), alpha=0.85, lw=0)
        logaxes(a, (5, 300))
        lr = np.abs(np.log(y / x))
        a.text(0.04, 0.96, f"halves differ by {pct(np.median(lr)):.0f}% (median)\n"
               f"{(lr > np.log(1.25)).mean():.0%} of people more than 25% apart\n{len(h)} people",
               transform=a.transAxes, va="top", fontsize=9, color=S.INK, linespacing=1.5)
        a.set_xlabel("odd weeks, mg/dL per U", fontsize=9, color=S.INK2)
        a.set_title(ttl, loc="left", fontsize=11, color=S.INK)
    ax[0].set_ylabel("even weeks, mg/dL per U", fontsize=9, color=S.INK2)
    S.title(fig, "Measured twice, on alternate weeks, a person gets nearly the same answer",
            "Each person's slope, its uncertainty and their fasting basal are recomputed from each half alone; "
            "the cohort-wide rule and level factor stay fixed.")
    S.save(fig, "r05_repeat", tight=dict(left=0.06, right=0.98, top=0.81, bottom=0.12, wspace=0.18))


if __name__ == "__main__":
    print("example:", r01_draw(), " level factor", round(LEV, 3))
    r02(); r03(); r04(); r05()
