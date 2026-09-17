#!/usr/bin/env python3
"""Views 25 and 26 — how insulin actually arrives.

The insulin document's subject is delivery as a quantity: how much reaches the
body in a five-minute bin, how much across a day, and how either moves over the
window. Not the basal/bolus accounting question, which is a forecast convention
rather than a description of the signal.

Writes delivery.csv (one row per person) and figures 25 and 26. Delivery in a
bin is `basal_eff/12 + bolus_u` — the effective basal rate over that bin plus
whatever bolus landed in it, in units. Local time throughout for the
time-of-day panel (lesson 37: a UTC hour-of-day is not an hour of anyone's
day).

Run:  python3 delivery.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt                              # noqa: E402
import style as S                                            # noqa: E402
from loopeval_analysis import dists as D                      # noqa: E402

MIN_BINS_PER_DAY = 240        # a day has to be near-complete to carry a total
MIN_DAYS = 30


def _delivery(c: pd.DataFrame) -> np.ndarray:
    return c["basal_eff"].to_numpy() / 12.0 + c["bolus_u"].fillna(0).to_numpy()


def table(co: pd.DataFrame) -> pd.DataFrame:
    """Per-person delivery statistics; also written to delivery.csv."""
    rows = []
    for a in co["alias"]:
        try:
            c = D.clean(S.load(a))
        except Exception:
            continue
        if len(c) < 5000:
            continue
        tot = _delivery(c)
        bol = c["bolus_u"].fillna(0).to_numpy()
        day = pd.Series(tot, index=c.index).resample("1D").sum()
        n = pd.Series(1, index=c.index).resample("1D").sum()
        day = day[n > MIN_BINS_PER_DAY]
        if len(day) < MIN_DAYS:
            continue
        srt = np.sort(tot)[::-1]
        k = max(int(0.01 * len(srt)), 1)
        dv = day.to_numpy()
        x = (day.index - day.index[0]).days.to_numpy(dtype=float)
        rows.append(dict(
            alias=a,
            zero_frac=100 * np.mean(tot <= 1e-9),
            med_nonzero=float(np.median(tot[tot > 1e-9])),
            p99=float(np.percentile(tot, 99)),
            mx=float(tot.max()),
            bolus_buckets=100 * np.mean(bol > 1e-9),
            conc1=100 * srt[:k].sum() / srt.sum(),
            tdd=float(day.median()),
            tdd_cv=100 * day.std() / day.mean(),
            trend_pct_30d=100 * np.polyfit(x, dv, 1)[0] * 30 / day.mean(),
            ac1=float(np.corrcoef(dv[:-1], dv[1:])[0, 1]) if len(dv) > 5 else np.nan,
            ac7=float(np.corrcoef(dv[:-7], dv[7:])[0, 1]) if len(dv) > 15 else np.nan,
            n_days=len(day)))
    t = pd.DataFrame(rows)
    t.to_csv(S.OUT / "delivery.csv", index=False)
    print(f"  delivery.csv — {len(t)} people")
    return t


def f25_five_minutes(co, t):
    """What a five-minute bin of insulin looks like."""
    fig, ax = S.figure(2, 2, figsize=(13.6, 8.6))
    order = S.order_by(co, "tir")
    samp = set(S.sample_for(co))

    # (a) the size distribution of a non-zero bin, on a log axis
    gx = np.logspace(np.log10(0.01), np.log10(12), 220)
    for a in order:
        try:
            c = D.clean(S.load(a))
        except Exception:
            continue
        v = _delivery(c)
        v = v[v > 1e-9]
        if len(v) < 500:
            continue
        gy = S.kde(np.log10(v), np.log10(gx))
        ax[0][0].plot(gx, gy / max(gy.max(), 1e-12), **S.line_style(co, a))
    ax[0][0].set_xscale("log")
    ax[0][0].set_xlabel("units delivered in a 5-minute bin (log)", fontsize=9.5, color=S.INK2)
    ax[0][0].set_ylabel("density (scaled)", fontsize=9.5, color=S.INK2)
    ax[0][0].set_title("A bin that delivers anything delivers very little",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")
    ax[0][0].text(0.97, 0.96, f"median non-zero bin {t.med_nonzero.median():.2f} U\n"
                  f"99th percentile {t.p99.median():.2f} U\n"
                  f"largest bin seen {t.mx.max():.0f} U",
                  transform=ax[0][0].transAxes, fontsize=8.5, color=S.INK2,
                  va="top", ha="right", linespacing=1.5, zorder=7,
                  bbox=dict(facecolor=S.SURFACE, edgecolor="none", alpha=0.88,
                            boxstyle="round,pad=0.35"))

    # (b) how often nothing is delivered at all
    S.strip_kde(ax[0][1], t["zero_frac"],
                [S.color_for(co, a) for a in t["alias"]], fmt="{:.0f}%")
    ax[0][1].set_xlabel("share of 5-minute bins with NO delivery (%)",
                        fontsize=9.5, color=S.INK2)
    ax[0][1].set_title("A third of the time, nothing is delivered",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # (c) insulin arrives in bursts, and equally so whichever way it is labelled
    S.strip_kde(ax[1][0], t["conc1"],
                [S.color_for(co, a) for a in t["alias"]], fmt="{:.0f}%")
    ax[1][0].set_xlabel("share of ALL insulin arriving in the busiest 1% of bins (%)",
                        fontsize=9.5, color=S.INK2)
    ax[1][0].set_title("A quarter of it arrives in 1% of the time",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")
    st = co.set_index("alias")["strategy"].reindex(t["alias"])
    by = t.assign(s=st.to_numpy()).groupby("s")["conc1"].median()
    if len(by) == 2:
        ax[1][0].text(0.97, 0.06,
                      f"temp-basal {by.get('temp', np.nan):.0f}%   "
                      f"auto-bolus {by.get('bolus', np.nan):.0f}%",
                      transform=ax[1][0].transAxes, fontsize=8.5, color=S.MUTED,
                      ha="right")

    # (d) the shape of a day, in local time
    prof = {}
    for a in order:
        try:
            c = D.clean(S.load(a))
        except Exception:
            continue
        h = (c["tod_min"].to_numpy() // 60).astype(int)
        v = _delivery(c)
        m = pd.DataFrame({"h": h, "v": v}).groupby("h")["v"].mean() * 12
        if len(m) == 24:
            prof[a] = m / m.mean()
    for a, m in prof.items():
        ax[1][1].plot(m.index, m.to_numpy(), **S.line_style(co, a))
    if prof:
        P = pd.DataFrame(prof)
        med = P.median(axis=1)
        ax[1][1].plot(med.index, med.to_numpy(), color=S.INK, lw=2.4, zorder=6)
        # A single "peak hour" misdescribes this: daytime is a broad plateau and
        # the structure is overnight-versus-day, so quote those blocks instead.
        night = P.loc[0:6].mean()
        dayt = P.loc[10:22].mean()
        rat = (dayt / night).dropna()
        ax[1][1].axvspan(0, 6, color=S.MUTED, alpha=0.10, lw=0, zorder=0)
        ax[1][1].text(0.03, 0.96,
                      f"00:00–06:00 runs at {med.loc[0:6].mean():.2f} of the daily mean,\n"
                      f"10:00–22:00 at {med.loc[10:22].mean():.2f}\n"
                      f"day/night ratio {np.median(rat):.2f}× "
                      f"(p10–p90 {np.percentile(rat, 10):.2f}–{np.percentile(rat, 90):.2f})",
                      transform=ax[1][1].transAxes, fontsize=8.5, color=S.INK2,
                      va="top", linespacing=1.5, zorder=7,
                      bbox=dict(facecolor=S.SURFACE, edgecolor="none", alpha=0.88,
                                boxstyle="round,pad=0.35"))
    ax[1][1].axhline(1, color=S.MUTED, lw=1.2, ls=(0, (4, 2)))
    ax[1][1].set_xlim(0, 23)
    ax[1][1].set_xlabel("hour of the local day", fontsize=9.5, color=S.INK2)
    ax[1][1].set_ylabel("delivery rate / own daily mean", fontsize=9.5, color=S.INK2)
    ax[1][1].set_title("Overnight runs at two-thirds the daytime rate",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    S.title(fig, "25 · How insulin arrives",
            f"Units delivered in each 5-minute bin — effective basal plus whatever bolus landed — across {len(t)} people. "
            "Delivery is sparse and spiky: a bin\nthat delivers anything delivers a median "
            f"{t.med_nonzero.median():.2f} U, {t.zero_frac.median():.0f}% of bins deliver nothing at all, and the busiest 1% of bins "
            f"carry {t.conc1.median():.0f}% of\nall the insulin. The burst structure is not a labelling artefact — it is the same for "
            "temp-basal and automatic-bolus users. Bottom right is local time,\nwhere the only strong structure is overnight against daytime.")
    S.save(fig, "25_delivery",
           dict(left=0.06, right=0.985, top=0.815, bottom=0.07, hspace=0.34, wspace=0.22))


def f26_the_day(co, t):
    """The daily total, and whether it moves."""
    fig, ax = S.figure(1, 3, figsize=(14.4, 5.0))
    cols = [S.color_for(co, a) for a in t["alias"]]

    S.strip_kde(ax[0], t["tdd"], cols, fmt="{:.0f}")
    ax[0].set_xlabel("total daily dose (U)", fontsize=9.5, color=S.INK2)
    ax[0].set_title("What a day comes to", fontsize=10.5, color=S.INK,
                    loc="left", pad=6, weight="bold")

    S.strip_kde(ax[1], t["tdd_cv"], cols, fmt="{:.0f}%")
    ax[1].set_xlabel("day-to-day variation in that total, within one person (CV %)",
                     fontsize=9.5, color=S.INK2)
    ax[1].set_title("and how much it moves day to day", fontsize=10.5, color=S.INK,
                    loc="left", pad=6, weight="bold")
    ax[1].text(0.97, 0.96, f"yesterday predicts today\nat a correlation of "
               f"{t.ac1.median():.2f}", transform=ax[1].transAxes, fontsize=8.5,
               color=S.INK2, ha="right", va="top", linespacing=1.5, zorder=7,
               bbox=dict(facecolor=S.SURFACE, edgecolor="none", alpha=0.88,
                         boxstyle="round,pad=0.35"))

    S.strip_kde(ax[2], t["trend_pct_30d"], cols, fmt="{:+.0f}%")
    ax[2].axvline(0, color=S.INK, lw=1.4)
    ax[2].set_xlabel("drift over the window (% of own mean per 30 days)",
                     fontsize=9.5, color=S.INK2)
    ax[2].set_title("and whether it drifts", fontsize=10.5, color=S.INK,
                    loc="left", pad=6, weight="bold")
    big = int((t.trend_pct_30d.abs() > 5).sum())
    ax[2].text(0.03, 0.96, f"{int((t.trend_pct_30d > 0).sum())} of {len(t)} rising\n"
               f"{big} move more than 5% / 30 d",
               transform=ax[2].transAxes, fontsize=8.5, color=S.INK2,
               va="top", linespacing=1.5, zorder=7,
               bbox=dict(facecolor=S.SURFACE, edgecolor="none", alpha=0.88,
                         boxstyle="round,pad=0.35"))

    S.title(fig, "26 · The daily total, and whether it holds still",
            f"One point per person. Median total daily dose {t.tdd.median():.0f} U, spanning "
            f"{t.tdd.min():.0f} to {t.tdd.max():.0f} across people — but the same person's "
            f"daily total varies\nby {t.tdd_cv.median():.0f}% around their own mean, and yesterday's total predicts today's at a "
            f"correlation of only {t.ac1.median():.2f}. Over the whole window the cohort barely\ndrifts (median "
            f"{t.trend_pct_30d.median():+.1f}% per 30 days), yet {big} individuals move more than 5% per 30 days.")
    S.save(fig, "26_daily_dose",
           dict(left=0.045, right=0.99, top=0.775, bottom=0.135, wspace=0.20))


def main() -> int:
    co = S.cohort()
    t = table(co)
    f25_five_minutes(co, t)
    f26_the_day(co, t)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
