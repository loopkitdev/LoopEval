#!/usr/bin/env python3
"""Figures for the ICE findings page (i01-i04).

Reads ice/ice_person.csv, ice/isf_probe.csv, ice/episodes.pkl and
ice/episode_person.csv — run ice_first.py, isf_probe.py, ice_episodes.py first.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa
from ice_first import _quiet_mask  # noqa

D = S.OUT / "ice"
H = 12
UNANN = "#8a5a9e"          # unannounced episodes
ANN = S.GREEN              # announced


def _colors(co, aliases):
    return [S.color_for(co, a) for a in aliases]


# ── i01: one person's day ────────────────────────────────────────────────
def pick_day(co, eps):
    e = eps[(eps.m == 1) & (eps.sign == 1) & (eps.g >= 15)].copy()
    e["day"] = e.t.dt.floor("D")
    cands = co[(co.carb_g_day.between(60, 160))].alias
    samp = [a for a in S.sample_for(co) if a in set(cands)]
    for a in samp:
        g = e[e.alias == a].groupby("day").agg(ann=("announced", "sum"),
                                                un=("announced", lambda s: (~s).sum()))
        ok = g[(g.ann >= 2) & (g.un >= 1)]
        if len(ok):
            return a, ok.index[len(ok) // 2]
    raise RuntimeError("no example day")


def i01(co, eps):
    alias, day = pick_day(co, eps)
    p = S.load(alias)
    quiet = _quiet_mask(p)
    ice = p["ice_abs"] * H
    base = np.nanmedian(ice[quiet])
    t0 = day + pd.Timedelta(hours=6) - pd.Timedelta(hours=p.attrs["utc_offset_h"])
    w = p[(p.index >= t0) & (p.index < t0 + pd.Timedelta(hours=24))]
    ic = (w["ice_abs"] * H)
    sm = (ic - base).rolling(6, center=True, min_periods=4).mean() + base
    hrs = (w.index - t0).total_seconds() / 3600 + 6
    fig, ax = S.figure(3, 1, figsize=(13, 9.2), sharex=True,
                       gridspec_kw={"height_ratios": [1.1, 0.8, 1.4]})
    ax[0].plot(hrs, w["bg"], color=S.INK, lw=1.4)
    ax[0].axhspan(70, 180, color=S.GREEN, alpha=0.07, lw=0)
    ax[0].set_ylabel("glucose, mg/dL", fontsize=9, color=S.INK2)
    ax[0].set_title("Glucose", loc="left", fontsize=11, color=S.INK)
    ax[1].fill_between(hrs, 0, w["ia_abs"] * H, color=S.COOL, alpha=0.35, lw=0)
    ax[1].plot(hrs, w["ia_abs"] * H, color=S.COOL, lw=1.2)
    bol = w["bolus_u"].fillna(0)
    for x, u in zip(hrs[bol > 0], bol[bol > 0]):
        ax[1].plot([x, x], [0, u * 12], color=S.INK, lw=1)
    ax[1].set_ylabel("mg/dL per hour", fontsize=9, color=S.INK2)
    ax[1].set_title("Insulin activity (every unit delivered, scheduled ISF)   "
                    "·  ticks = boluses, height ∝ units", loc="left", fontsize=11, color=S.INK)
    ax[2].plot(hrs, ic, color=S.MUTED, lw=0.6, alpha=0.7, label="ICE, every 5 min")
    ax[2].plot(hrs, sm, color=S.INK, lw=1.5, label="30-min mean")
    ax[2].axhline(base, color=S.INK2, ls="--", lw=1)
    ax[2].text(hrs[-1], base, " fasting\n baseline", fontsize=8, color=S.INK2, va="center")
    ee = eps[(eps.alias == alias) & (eps.m == 1) & (eps.sign == 1) & (eps.g >= 10)
             & (eps.t >= t0) & (eps.t < t0 + pd.Timedelta(hours=24))]
    for _, r in ee.iterrows():
        a = (r.t - t0).total_seconds() / 3600 + 6
        b = a + r.dur_min / 60
        c = ANN if r.announced else UNANN
        ax[2].axvspan(a, b, color=c, alpha=0.16, lw=0)
        lab = f"{r.g:.0f} g-eq" + (f"\n({r.g_entered:.0f} g entered)" if r.announced else "\nunannounced")
        ax[2].text((a + b) / 2, 0.97, lab, transform=ax[2].get_xaxis_transform(),
                   ha="center", va="top", fontsize=7.8, color=c)
    jump = np.diff(w["cob"].to_numpy(), prepend=w["cob"].iloc[0])
    for x, g in zip(hrs[jump >= 5], jump[jump >= 5]):
        for a_ in ax:
            a_.axvline(x, color=ANN, lw=1.2, ls=":")
        ax[0].text(x, 0.96, f" {g:.0f} g", transform=ax[0].get_xaxis_transform(),
                   color=ANN, fontsize=8.5, va="top")
    ax[2].set_ylabel("mg/dL per hour", fontsize=9, color=S.INK2)
    ax[2].set_title("ICE = glucose velocity + insulin activity   ·   shaded: episodes above baseline, "
                    "green announced, purple not", loc="left", fontsize=11, color=S.INK)
    ax[2].set_xlabel("local hour", fontsize=9, color=S.INK2)
    ax[2].set_xticks(range(6, 31, 3)); ax[2].set_xticklabels([f"{h % 24:02d}:00" for h in range(6, 31, 3)])
    ax[2].legend(loc="upper left", bbox_to_anchor=(0, 0.8), fontsize=8, frameon=False)
    S.title(fig, "One day of counteraction",
            f"One person from the representative sample, 06:00 to 06:00 local. Dotted green lines are carb entries.")
    S.save(fig, "i01_day", tight=dict(left=0.07, right=0.93, top=0.88, bottom=0.07, hspace=0.32))
    return alias


# ── i02: the ISF question ─────────────────────────────────────────────────
def i02(co, summ, probe):
    fig = S.plt.figure(figsize=(13, 8.6))
    fig.patch.set_facecolor(S.SURFACE)
    gs = fig.add_gridspec(2, 3, hspace=0.55, wspace=0.32)
    axs = [S.axes(fig.add_subplot(gs[0, i])) for i in range(3)]
    ms = sorted(summ.m.unique())
    spec = [("baseline", "Fasting baseline, mg/dL per hour", axs[0]),
            ("pos_g_day", "ICE above baseline, g-eq per day", axs[1]),
            ("unann_share_g", "Share of it unannounced", axs[2])]
    for col, ttl, ax in spec:
        for a, g in summ.groupby("alias"):
            ax.plot(g.m, g[col], **S.line_style(co, a, lw=1.2))
        q = summ.groupby("m")[col].quantile([.1, .5, .9]).unstack()
        ax.plot(q.index, q[0.5], color=S.INK, lw=2.4, zorder=5)
        for m_, v in q[0.5].items():
            ax.text(m_, v, f" {v:.0%}" if col == "unann_share_g" else f" {v:.0f}",
                    fontsize=8.5, color=S.INK, va="bottom", zorder=6)
        ax.set_xticks(ms); ax.set_xticklabels([f"×{m}" for m in ms])
        ax.set_xlabel("ISF used, as a multiple of the schedule", fontsize=8.5, color=S.INK2)
        ax.set_title(ttl, loc="left", fontsize=10.5, color=S.INK)
        if col == "unann_share_g":
            ax.set_ylim(0, 1)
        else:
            ax.set_ylim(0, q[0.9].max() * 1.5)
    ax = S.axes(fig.add_subplot(gs[1, :2]))
    r = (probe.ols60 / probe.isf_sched).to_numpy()
    lo, med, hi = S.strip_kde(ax, r, _colors(co, probe.alias), fmt="{:.2f}")
    ax.axvline(1, color=S.ACCENT, lw=1.5, ls="--")
    ax.text(1.01, 1.1, "the schedule", color=S.ACCENT, fontsize=8.5)
    ax.set_title("ISF that makes fasting ICE uncorrelated with insulin absorbed, "
                 "as a multiple of the schedule", loc="left", fontsize=10.5, color=S.INK)
    ax.set_xlabel("fitted ISF ÷ scheduled ISF (60-min fasting blocks)", fontsize=8.5, color=S.INK2)
    ax = S.axes(fig.add_subplot(gs[1, 2]))
    ax.scatter(probe.isf_sched, probe.ols60, s=16, c=_colors(co, probe.alias), alpha=0.75, lw=0)
    mx = np.nanpercentile(probe.isf_sched, 99) * 1.1
    ax.plot([0, mx], [0, mx], color=S.MUTED, lw=1, ls="--")
    ax.plot([0, mx], [0, mx * med], color=S.INK, lw=1.2)
    ax.set_xlim(0, mx); ax.set_ylim(0, mx)
    ax.set_xlabel("scheduled ISF, mg/dL per U", fontsize=8.5, color=S.INK2)
    ax.set_ylabel("fitted ISF", fontsize=8.5, color=S.INK2)
    rho = pd.Series(probe.isf_sched).corr(pd.Series(probe.ols60), method="spearman")
    ax.set_title(f"It ranks people like the schedule (ρ {rho:.2f})", loc="left", fontsize=10.5, color=S.INK)
    S.title(fig, "Every ICE statistic moves with the ISF behind it",
            "Top: faint lines are people, bold the median. Bottom: a fasting regression lands at about half "
            "the schedule; closed-loop feedback biases it low, by an unknown amount.")
    S.save(fig, "i02_isf", tight=dict(left=0.05, right=0.98, top=0.86, bottom=0.08))


# ── i03: announced vs unannounced ─────────────────────────────────────────
def i03(co, summ):
    s = summ[summ.m == 1].merge(co[["alias"]], on="alias")
    fig, ax = S.figure(1, 3, figsize=(13, 5.8))
    a = ax[0]
    S.strip_kde(a, s.entries_seen, _colors(co, s.alias), fmt="{:.0%}")
    a.set_title("Carb entries ≥ 10 g that sit in an ICE episode", loc="left", fontsize=10.5, color=S.INK)
    a.set_xlabel("share of a person's entries", fontsize=8.5, color=S.INK2)
    a = ax[1]
    S.strip_kde(a, s.ann_ratio.clip(upper=3), _colors(co, s.alias), fmt="{:.2f}")
    a.set_title("ICE over those episodes ÷ grams entered", loc="left", fontsize=10.5, color=S.INK)
    a.set_xlabel("gram-equivalents per gram announced", fontsize=8.5, color=S.INK2)
    a = ax[2]
    a.scatter(s.carb_g_day, s.unann_share_g, s=18, c=_colors(co, s.alias), alpha=0.8, lw=0)
    a.set_xscale("symlog", linthresh=10)
    a.set_xlabel("announced carbohydrate, g per day", fontsize=8.5, color=S.INK2)
    a.set_ylim(0, 1.02)
    a.set_title("Share of meal-sized ICE that is unannounced", loc="left", fontsize=10.5, color=S.INK)
    S.title(fig, "ICE sees the meals people announce, and a quarter it never hears about",
            "Scheduled ISF. Colour: announcing behaviour (blue non-announcer, green moderate, orange heavy).")
    S.save(fig, "i03_meals", tight=dict(left=0.03, right=0.98, top=0.80, bottom=0.12, wspace=0.22))


# ── i04: episodes, size and hour ──────────────────────────────────────────
def i04(co, eps):
    e = eps[(eps.m == 1) & (eps.sign == 1) & (eps.g >= 10)]
    fig, ax = S.figure(1, 3, figsize=(13, 5.8))
    a = ax[0]
    for ann, c, lab in ((True, ANN, "announced"), (False, UNANN, "unannounced")):
        g = np.sort(e[e.announced == ann].g.to_numpy())
        a.plot(g, 1 - np.arange(len(g)) / len(g), color=c, lw=2, label=f"{lab}, median {np.median(g):.0f} g-eq")
    a.set_xscale("log"); a.set_yscale("log")
    a.set_xlabel("episode size, gram-equivalents", fontsize=8.5, color=S.INK2)
    a.set_ylabel("share of episodes at least this big", fontsize=8.5, color=S.INK2)
    a.legend(fontsize=8, frameon=False)
    a.set_title("Size", loc="left", fontsize=10.5, color=S.INK)
    a = ax[1]
    for ann, c in ((True, ANN), (False, UNANN)):
        g = np.sort(e[e.announced == ann].dur_min.to_numpy()) / 60
        a.plot(g, 1 - np.arange(len(g)) / len(g), color=c, lw=2,
               label=f"median {np.median(g):.1f} h")
    a.set_xlim(0, 10)
    a.set_xlabel("episode duration, hours", fontsize=8.5, color=S.INK2)
    a.legend(fontsize=8, frameon=False)
    a.set_title("Duration", loc="left", fontsize=10.5, color=S.INK)
    a = ax[2]
    h = (e.tod // 60).astype(int)
    for ann, c in ((True, ANN), (False, UNANN)):
        m = e.announced == ann
        share = e[m].groupby(h[m]).g.sum() / e[m].g.sum()
        share = share.reindex(range(24), fill_value=0)
        a.plot(np.r_[share.index, 24], np.r_[share.values, share.values[0]] * 100,
               color=c, lw=2, drawstyle="steps-post")
    a.set_xticks(range(0, 25, 6)); a.set_xticklabels(["00", "06", "12", "18", "24"])
    a.set_xlabel("local hour the episode starts", fontsize=8.5, color=S.INK2)
    a.set_ylabel("% of that kind's gram-equivalents", fontsize=8.5, color=S.INK2)
    a.set_title("Hour of day", loc="left", fontsize=10.5, color=S.INK)
    n = e.alias.nunique()
    S.title(fig, "Unannounced episodes are smaller, shorter, and happen late",
            f"Every episode ≥ 10 g-eq across {n} people at the scheduled ISF, "
            f"{len(e):,} episodes.")
    S.save(fig, "i04_episodes", tight=dict(left=0.06, right=0.98, top=0.80, bottom=0.12, wspace=0.26))


if __name__ == "__main__":
    co = S.cohort()
    eps = pd.read_pickle(D / "episodes.pkl")
    summ = pd.read_csv(D / "episode_person.csv")
    probe = pd.read_csv(D / "isf_probe.csv").dropna(subset=["ols60"])
    print("example:", i01(co, eps))
    i02(co, summ, probe)
    i03(co, summ)
    i04(co, eps)
