"""Label meals in a donor's real ICE: the event table the v3 generator trains on.

A meal is a pulse of excess ICE, with whatever the person logged and bolused for it:
  excess    30-min centred mean of clean ICE minus a LOCAL floor: the 25th percentile over a
            centred 6-h window (an overnight baseline sits below daytime ICE all day and fused
            breakfast, lunch and snacks into one pulse)
  pulse     a run of excess > 0, split at clear troughs (a dip of >= SPLIT_G g-eq/h below both
            neighbouring peaks starts a new meal); runs less than MERGE_MIN apart with no such
            trough between them are one meal (two- and three-phase absorption); sized by SUMMED
            excess in g-eq (ISF_tdd / (500/TDD) mg/dL per g-eq, settings-free), kept if >= GATE_G
  entry     carb entries logged (entryDate) from ENTRY_BEFORE before to ENTRY_AFTER after onset,
            each entry assigned to its nearest onset -> announced, grams, entry delay, estimate
            ratio (grams / pulse g-eq)
  bolus     manual boluses (calculator decision records) in the same window -> mode (calculator
            ratio or override units), lead time vs onset
  rescue    an unannounced pulse whose onset follows BG < 70 within 30 min
Boluses matched to no meal are corrections; the BG at the time is kept.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import grid5

GATE_G = 12.0
MERGE_MIN = 30
SPLIT_G = 12.0                      # g-eq per hour
PHASE_H = 2.5                       # an unannounced, smaller pulse this soon after an announced one is its later phase
ENTRY_BEFORE, ENTRY_AFTER = pd.Timedelta(minutes=60), pd.Timedelta(minutes=90)
REC_ZERO = 0.05
# rescues come in steps: people treat, wait ~15 min, and treat again if glucose has not turned up (Pete, 2026-10-14). The
# 35-min smoothing and the 12 g-eq/h trough rule merged a second treatment into the first: in held-out lows a second clear rise
# in raw ICE follows 34% of first rescues when glucose is not yet rising at 15 min (25% if it is), labels found 10-15% with no
# dependence on rising. For a pulse starting near a low: on 30-min smoothed ICE, after the first rise's peak (within 45 min), a
# dip >= RESCUE_SPLIT_MIN after onset followed by a renewed rise of >= RESCUE_RISE_MGDL mg/dL/h starts a new pulse (the
# same rule as the raw-ICE check); split rescue parts are kept down to RESCUE_GATE_G. A looser rule (15-min smoothing, any
# 4 g-eq/h rise) split 44% of first rescues, more when already rising: the first rise's own wiggles.
# Both sides require a real dip (>= RESCUE_DIP_MGDL below the first peak): a steady single rise is one treatment.
RESCUE_BG, RESCUE_SPLIT_MIN, RESCUE_RISE_MGDL, RESCUE_DIP_MGDL, RESCUE_GATE_G = 80.0, 15, 30.0, 10.0, 6.0


def label(steps: pd.DataFrame, carbs: list, bolus_dec: pd.DataFrame, tdd: float, isf: float):
    """-> (meals DataFrame, corrections DataFrame, constants)."""
    g = grid5(steps)
    base = float(np.nanmedian(g.ice[g.hour.between(2, 5)]))
    geq = isf / (500.0 / tdd)
    sm = g.ice.rolling(7, center=True, min_periods=4).mean()
    floor = sm.rolling(72, center=True, min_periods=24).quantile(0.25)
    ex = sm - floor
    pos = (ex > 0).to_numpy() & ex.notna().to_numpy()
    edges = np.flatnonzero(np.diff(np.r_[0, pos.astype(int), 0]))
    runs = []
    for a, b in zip(edges[::2], edges[1::2]):
        if runs and a - runs[-1][1] < MERGE_MIN // 5:
            runs[-1][1] = b
        else:
            runs.append([a, b])
    # split a run at clear troughs: a later rise after a dip of >= SPLIT_G g-eq/h is a new meal
    from scipy.signal import find_peaks
    split = []
    for a, b in runs:
        y = np.nan_to_num(ex.iloc[a:b].to_numpy()) / geq
        tr, _ = find_peaks(-y, prominence=SPLIT_G)
        cuts = [a] + [a + int(t) for t in tr] + [b]
        split += [[c0, c1] for c0, c1 in zip(cuts[:-1], cuts[1:]) if c1 > c0]
    runs = split
    # second treatments in a low (see RESCUE_*): split near-low pulses at a renewed rise on 30-min smoothed ICE
    ex6 = g.ice.rolling(6, min_periods=3).mean().to_numpy()
    bgv = g.bg.to_numpy(); rescue_part = set(); split = []
    for a, b in runs:
        near = np.nanmin(bgv[max(a - 6, 0):a + 1]) < RESCUE_BG if np.isfinite(bgv[max(a - 6, 0):a + 1]).any() else False
        if not near or b - a < RESCUE_SPLIT_MIN // 5 + 2:
            split.append([a, b]); continue
        y = ex6[a:b]; cut = None
        if np.isfinite(y[:9]).any():
            k = int(np.nanargmax(y[:9]))                                  # the first rise's peak, within 45 min
            for c in range(max(k + 1, RESCUE_SPLIT_MIN // 5), len(y) - 1):
                if (np.isfinite(y[c]) and y[c] <= y[c - 1] and y[c] <= y[c + 1] and np.nanmax(y[k:c + 1]) - y[c] >= RESCUE_DIP_MGDL
                        and np.nanmax(y[c:c + 9]) - y[c] >= RESCUE_RISE_MGDL):
                    cut = a + c; break
        if cut is None:
            split.append([a, b])
        else:
            split += [[a, cut], [cut, b]]; rescue_part.update({a, cut})
    runs = split
    idx = g.index
    meals = []
    for a, b in runs:
        seg = ex.iloc[a:b].clip(lower=0)
        size = float(np.nansum(seg) * 5 / 60 / geq)
        if size < (RESCUE_GATE_G if a in rescue_part else GATE_G):
            continue
        pk = int(np.nanargmax(seg.to_numpy()))
        pre = g.bg.iloc[max(a - 6, 0):a + 1]
        meals.append(dict(onset=idx[a], end=idx[b - 1], size_g=size, dur_h=(b - a) * 5 / 60,
                          peak_h=pk * 5 / 60, peak_geq_h=float(seg.iloc[pk]) / geq,
                          hour=float(g.hour.iloc[a]), bg_onset=float(g.bg.iloc[a]) if np.isfinite(g.bg.iloc[a]) else np.nan,
                          low_before=bool((pre < 70).any())))
    m = pd.DataFrame(meals)
    if m.empty:
        return m, pd.DataFrame(), dict(base=base, geq=geq)
    on = m.onset.astype("int64").to_numpy()                       # ns
    ends = m.end.astype("int64").to_numpy()

    def nearest(t: pd.Timestamp) -> int:
        tn = t.value
        j = int(np.argmin(np.abs(on - tn)))
        # an entry belongs to the meal whose onset is nearest, if logged between ENTRY_BEFORE the
        # onset and the end of its first ENTRY_AFTER (or its whole duration, if shorter)
        reach = min(ENTRY_AFTER.value, int(ends[j] - on[j]) + 15 * 60 * 10**9)
        return j if on[j] - ENTRY_BEFORE.value <= tn <= on[j] + reach else -1

    m["entry_g"] = 0.0; m["entry_delay_min"] = np.nan
    for c in carbs:
        t = pd.Timestamp(c.get("entryDate") or c["startDate"]).tz_convert("UTC")
        j = nearest(t)
        if j >= 0:
            m.loc[j, "entry_g"] += float(c["grams"])
            d = (t - m.onset.iloc[j]).total_seconds() / 60
            if not np.isfinite(m.loc[j, "entry_delay_min"]) or d < m.loc[j, "entry_delay_min"]:
                m.loc[j, "entry_delay_min"] = d
    m["announced"] = m.entry_g > 0
    m["phases"] = 1
    m["estimate_ratio"] = np.where(m.announced, m.entry_g / m.size_g, np.nan)
    m["bolus_u"] = 0.0; m["bolus_mode"] = None; m["bolus_ratio"] = np.nan; m["bolus_lead_min"] = np.nan
    corr = []
    for r in bolus_dec.itertuples():
        if not (r.requested and r.requested > 0):
            continue
        j = nearest(r.t)
        if j < 0:
            k = g.index.searchsorted(r.t.floor("5min"))
            corr.append(dict(t=r.t, units=r.requested, rec=r.rec,
                             bg=float(g.bg.iloc[min(k, len(g) - 1)]) if len(g) else np.nan))
            continue
        m.loc[j, "bolus_u"] += r.requested
        if m.loc[j, "bolus_mode"] is None:
            m.loc[j, "bolus_mode"] = "calculator" if (r.rec is not None and r.rec > REC_ZERO) else "override"
            m.loc[j, "bolus_ratio"] = r.requested / r.rec if (r.rec and r.rec > REC_ZERO) else np.nan
            m.loc[j, "bolus_lead_min"] = (r.t - m.onset.iloc[j]).total_seconds() / 60
    # later absorption phases: fold an unannounced, smaller pulse starting within PHASE_H of an
    # announced meal's onset into that meal (size and end), instead of counting a new meal
    m = m.sort_values("onset").reset_index(drop=True)
    keep = np.ones(len(m), bool); host = -1
    for i in range(len(m)):
        if m.announced.iloc[i]:
            host = i; continue
        if host >= 0 and keep[host] and (m.onset.iloc[i] - m.onset.iloc[host]) <= pd.Timedelta(hours=PHASE_H) \
                and m.size_g.iloc[i] < m.size_g.iloc[host] and m.bolus_u.iloc[i] == 0:
            m.loc[host, "size_g"] += m.size_g.iloc[i]
            m.loc[host, "end"] = max(m.end.iloc[host], m.end.iloc[i])
            m.loc[host, "phases"] = m.phases.iloc[host] + 1
            keep[i] = False
    m = m[keep].reset_index(drop=True)
    m["dur_h"] = (m.end - m.onset).dt.total_seconds() / 3600 + 5 / 60
    m["estimate_ratio"] = np.where(m.announced, m.entry_g / m.size_g, np.nan)
    m["rescue"] = ~m.announced & m.low_before
    m = fit_shapes(m, (g.ice - floor).to_numpy(), g.index, geq)
    return m, pd.DataFrame(corr), dict(base=base, geq=geq)


# Pulse shape: peak time and spread fitted to the meal's raw ICE above the local floor, onset and size kept. Read off the
# 35-min smoothed excess (peak = its argmax, 90% of mass by the end of the run), the rebuilt pulse under-shot real meal ICE
# by 12 / 23 mg/dL/h at 15 / 30 min after onset and over-shot it by 8-9 at 75-105 min (3,000 pulses, 30 donors); a per-meal
# least-squares lognormal leaves 0 / 4 and -4, with the same onset (median shift 0) and a peak 6 min earlier. The generator
# learns its pulse shapes from these labels, and a pulse too slow early put the meal bolus ahead of the food: generated meal
# boluses ran into a low within 3 h 26% of the time against 8% in the field (2026-10-14).
FIT_MODES = np.exp(np.linspace(np.log(10 / 60), np.log(4), 24))
FIT_S = np.linspace(0.15, 1.6, 20)


def fit_shapes(m: pd.DataFrame, y: np.ndarray, idx: pd.DatetimeIndex, geq: float, rounds: int = 2) -> pd.DataFrame:
    """Refit each pulse's peak_h / dur_h (kernel.params convention) by least squares to y = ICE minus the local floor,
    other pulses removed; keeps the labeler's run length as run_h."""
    from .kernel import params, rate
    if m.empty:
        return m
    m = m.copy(); m["run_h"] = m.dur_h
    tn = idx.asi8; mo = m.onset.astype("int64").to_numpy()
    mm, ss = params(m.peak_h.to_numpy() + 2.5 / 60, m.dur_h.to_numpy())
    span = [(int(idx.searchsorted(m.onset.iloc[i])), (tn - mo[i]) / 3.6e12) for i in range(len(m))]
    def one(i, mu, s):
        o, th = span[i]; j1 = min(o + 96, len(tn)); t = th[o:j1]; p = np.zeros(j1 - o); w = t > 0
        p[w] = rate(t[w], m.size_g.iloc[i] * geq, mu, s); return o, j1, p
    tot = np.zeros(len(tn))
    for i in range(len(m)):
        o, j1, p = one(i, mm[i], ss[i]); tot[o:j1] += p
    grid = [(md * np.exp(s ** 2), s) for md in FIT_MODES for s in FIT_S if md * np.exp(s ** 2 + 1.2816 * s) <= 10]   # the plant clips duration at 10 h
    for _ in range(rounds):
        for i in range(len(m)):
            o, j1, p0 = one(i, mm[i], ss[i])
            yy = y[o:j1] - (tot[o:j1] - p0); ok = np.isfinite(yy)
            if ok.sum() < 12:
                continue
            t = span[i][1][o:j1][ok]; best = None
            for mu, s in grid:
                e = float(np.sum((yy[ok] - rate(t, m.size_g.iloc[i] * geq, mu, s)) ** 2))
                if best is None or e < best[0]:
                    best = (e, mu, s)
            mm[i], ss[i] = best[1], best[2]
            o, j1, p1 = one(i, mm[i], ss[i]); tot[o:j1] += p1 - p0
    mode = mm * np.exp(-ss ** 2)
    m["peak_h"] = np.maximum(mode - 2.5 / 60, 5 / 60 - 2.5 / 60)
    m["dur_h"] = mm * np.exp(1.2816 * ss)
    return m
