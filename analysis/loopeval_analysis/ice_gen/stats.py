"""The statistics a generated ICE series must reproduce, measured identically on real and generated
step tables (the columns `extract` writes: t1, dt, ice, v, ia, bg1, iob, hour, local_day, clean).

Per person, on clean intervals only:
  quantiles5     ICE quantiles at the native ~5-min step (sensor noise dominates here)
  quantiles30    ICE quantiles on fixed 30-min bins with >= 25 clean minutes (noise telescopes away)
  acf            autocorrelation of 5-min ICE at lags 5 min .. 24 h (lag-1 carries the noise signature)
  hourly         mean ICE by local hour
  daily_sd       SD across days of the daily mean ICE, and its ratio to the within-day SD
  episodes       pulses of excess ICE (above the person's overnight-quiet baseline, 30-min centred
                 mean), sized by summed excess in gram-equivalents, gated at 10 g-eq: rate per day
                 by local hour, size and duration quantiles
  hazard         P(a new pulse starts within the next hour | hours since the last pulse ended)
  vs_bg, vs_iob  mean ICE over the next hour by current BG band / insulin-on-board band

Gram-equivalents use settings-free rules, like ISF: ISF_tdd and CR = 500 / TDD, so
1 g-eq = ISF_tdd / CR_tdd mg/dL.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

Q = np.array([.01, .05, .1, .25, .5, .75, .9, .95, .99])
LAGS = np.r_[1, 2, 3, 6, 12, 24, 48, 96, 144, 216, 288]          # in 5-min steps (5 min .. 24 h)
BG_BANDS = [0, 70, 100, 140, 180, 250, 1000]
IOB_BANDS = [-10, 1, 2, 4, 6, 100]
EPISODE_GATE_G = 10.0
MERGE_STEPS = 6                                    # pulses closer than 30 min are one episode


def grid5(df: pd.DataFrame) -> pd.DataFrame:
    """Clean ICE on a regular 5-min UTC grid (NaN where not clean), with context carried along."""
    c = df[df.clean].copy()
    c["slot"] = c.t1.dt.floor("5min")
    c = c.groupby("slot").agg(ice=("ice", "mean"), bg=("bg1", "last"), iob=("iob", "last"),
                              hour=("hour", "last"), day=("local_day", "last"))
    idx = pd.date_range(c.index.min(), c.index.max(), freq="5min")
    c = c.reindex(idx)
    # local clock on every slot (also the empty ones): carry the local-minus-UTC offset across gaps
    utc_h = idx.hour + idx.minute / 60
    off = (((c.hour - utc_h + 36) % 24) - 12).ffill().bfill()
    c["hour"] = (utc_h + off) % 24
    c["day"] = ((idx.asi8 + (off.to_numpy() * 3.6e12).astype("int64")) // 86_400_000_000_000)
    return c


def acf_nan(x: np.ndarray, lags=LAGS) -> np.ndarray:
    m = np.nanmean(x); v = np.nanvar(x); z = x - m
    out = []
    for k in lags:
        a, b = z[:-k], z[k:]
        ok = ~np.isnan(a) & ~np.isnan(b)
        out.append(np.mean(a[ok] * b[ok]) / v if ok.sum() > 100 else np.nan)
    return np.array(out)


def bins30(df: pd.DataFrame) -> pd.Series:
    """ICE on fixed 30-min bins: summed (v + ia) * dt over clean intervals / clean minutes."""
    c = df[df.clean]
    b = c.t1.dt.floor("30min")
    num = (c.ice * c.dt).groupby(b).sum(); den = c.dt.groupby(b).sum()
    return (num / den)[den >= 25]


def episodes(g: pd.DataFrame, geq_mgdl: float):
    """Pulses of excess ICE on the 5-min grid. Returns (episodes frame, baseline mg/dL/h)."""
    quiet = g.hour.between(2, 5)                       # overnight, least meal-driven
    base = float(np.nanmedian(g.ice[quiet])) if quiet.sum() > 200 else float(np.nanmedian(g.ice))
    ex = (g.ice - base).rolling(7, center=True, min_periods=4).mean()   # 30-min centred
    pos = (ex > 0).to_numpy() & ex.notna().to_numpy()
    edges = np.flatnonzero(np.diff(np.r_[0, pos.astype(int), 0]))
    runs = []
    for a, b in zip(edges[::2], edges[1::2]):        # one meal dips below baseline briefly: merge <30 min
        if runs and a - runs[-1][1] < MERGE_STEPS:
            runs[-1][1] = b
        else:
            runs.append([a, b])
    rows = []
    for a, b in runs:
        size_mgdl = float(np.nansum(ex.iloc[a:b].clip(lower=0)) * 5 / 60)   # mg/dL/h x h, dips excluded
        rows.append(dict(start=g.index[a], end=g.index[b - 1], hour=g.hour.iloc[a],
                         dur_h=(b - a) * 5 / 60, size_g=size_mgdl / geq_mgdl))
    ep = pd.DataFrame(rows)
    return (ep[ep.size_g >= EPISODE_GATE_G].reset_index(drop=True) if len(ep) else ep), base


def hazard(ep: pd.DataFrame, g: pd.DataFrame, max_h=12):
    """P(new pulse starts within the next hour | hours since the previous pulse ended), by whole hours."""
    if len(ep) < 5:
        return np.full(max_h, np.nan)
    starts = ep.start.to_numpy(); ends = ep.end.to_numpy()
    valid = g.ice.notna().to_numpy(); t = g.index.to_numpy()
    hits = np.zeros(max_h); n = np.zeros(max_h)
    for i in range(0, len(t), 12):                           # every hour on the grid
        if not valid[i]:
            continue
        j = np.searchsorted(ends, t[i]) - 1
        if j < 0:
            continue
        since = (t[i] - ends[j]) / np.timedelta64(1, "h")
        if since < 0 or since >= max_h:
            continue
        nxt = np.searchsorted(starts, t[i], side="right")
        hit = nxt < len(starts) and (starts[nxt] - t[i]) <= np.timedelta64(1, "h")
        n[int(since)] += 1; hits[int(since)] += hit
    with np.errstate(invalid="ignore"):
        return np.where(n >= 10, hits / n, np.nan)


def next_hour_by(g: pd.DataFrame, col: str, bands):
    fut = g.ice[::-1].rolling(12, min_periods=8).mean()[::-1].shift(-1)   # mean ICE over the next hour
    cut = pd.cut(g[col], bands)
    return fut.groupby(cut, observed=False).mean().to_numpy()


def person_stats(df: pd.DataFrame, tdd: float, isf: float) -> dict:
    g = grid5(df)
    x = g.ice.to_numpy()
    geq = isf / (500.0 / tdd)
    ep, base = episodes(g, geq)
    days = g.day.dropna()
    dmean = g.ice.groupby(g.day).mean()
    within = g.ice.groupby(g.day).std().median()
    n_days = max(days.nunique(), 1)
    ep_by_hour = np.bincount(ep.hour.astype(int), minlength=24)[:24] / n_days if len(ep) else np.zeros(24)
    return dict(
        quantiles5=np.nanquantile(x, Q),
        quantiles30=np.quantile(bins30(df), Q),
        acf=acf_nan(x),
        hourly=g.ice.groupby(g.hour.floordiv(1)).mean().reindex(range(24)).to_numpy(),
        daily_sd=float(dmean.std()), daily_sd_ratio=float(dmean.std() / within) if within else np.nan,
        baseline=base,
        ep_per_day=len(ep) / n_days, ep_by_hour=ep_by_hour,
        ep_size_q=np.quantile(ep.size_g, [.25, .5, .75, .9]) if len(ep) else np.full(4, np.nan),
        ep_dur_q=np.quantile(ep.dur_h, [.25, .5, .75, .9]) if len(ep) else np.full(4, np.nan),
        hazard=hazard(ep, g),
        vs_bg=next_hour_by(g, "bg", BG_BANDS),
        vs_iob=next_hour_by(g, "iob", IOB_BANDS),
    )
