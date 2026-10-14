"""v3m3 sequences: an announced meal always brings its pulse.

v3m drew carb entries and meal pulses independently; 25% of generated entries had no pulse within -60/+120 min and the
controller dosed for carbs that never came (t<54 3.1 vs field 0.04). In the field nearly every entry is followed by a
pulse: the 19% the labeler leaves unmatched still show ICE above baseline over the next 3 h (about half a matched
entry's), mostly small entries (median 20 g) below the labeler's gate or merged into another pulse.

Labels, causal (each pulse anchored where a generator would know of it):
  a pulse's claiming entry = the earliest entry from 120 min before to 60 min after its onset, each entry claiming
  at most one pulse
  pulse started > 5 min before its claiming entry, or claimed by none -> a MEAL event at the onset (eating began
      first; the entry, if any, joins it: e_new 0)
  pulse claimed by an entry at or before its start -> the ENTRY starts it: e_new 1 with e_off (log1p min from the
      entry to the onset), e_lsize, e_lpeak, e_ldur
  an entry with no labeled pulse within -60/+120 min -> e_new 1, pulse attributes unknown (NaN)
  any other entry (a second entry for a meal under way) -> e_new 0
The plant treats an e_new 0 entry with no meal begun in the last 2 h as starting one.
Inputs as dataset_v3m.FEATURES_M2; meal history counts the anchors above.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .dataset import to_grid, ICE_SCALE
from .kernel import reconstruct, remaining, params
from . import dataset_v3 as D3
from .dataset_v3m import action_inputs, entered_since_meal, FEATURES_M2, REC_ZERO, OWN_MEANS

FEATURES_M3 = FEATURES_M2
TARGETS = ["bgice", "meal", "m_lsize", "m_lpeak", "m_ldur", "entry", "e_lg", "e_new", "e_off", "e_lsize", "e_lpeak", "e_ldur",
           "bolus", "b_mode", "b_lr", "b_lu"]
BOLUS_T = ["bolus", "b_mode", "b_lr", "b_lu"]
BEFORE, AFTER, LEAD = 24, 12, 1        # slots: an entry claims a pulse starting up to 120 min after / 60 min before it


def build(steps, meals, bolus_dec, carbs, geq, features=FEATURES_M3, isf=None, decision_days=None, unknown_slots=None):
    """unknown_slots: UTC 5-min slots whose bolus targets are unknown (dataset_v3.pumpless_slots), as decision_days does by day."""
    g = to_grid(steps)
    T, idx = len(g), g.index
    pulses = reconstruct(idx, meals, geq) if len(meals) else np.zeros(T)
    bgice = (g.ice - pulses).to_numpy()
    slot = lambda t: int(idx.searchsorted(pd.Timestamp(t).floor("5min")))
    ti = TARGETS.index
    Y = np.full((T, len(TARGETS)), np.nan, np.float32)
    for k in ("meal", "entry", "bolus"):
        Y[:, ti(k)] = 0
    carb_g = np.zeros(T); bol_u = np.zeros(T); bol_rec = np.full(T, np.nan)
    for c in carbs:
        i = slot(c.get("entryDate") or c["startDate"])
        if 0 <= i < T and float(c["grams"]) > 0:
            carb_g[i] += float(c["grams"])
    for r in bolus_dec.itertuples() if len(bolus_dec) else []:
        if r.requested and r.requested > 0:
            i = slot(r.t)
            if 0 <= i < T:
                bol_u[i] += r.requested
                if not np.isfinite(bol_rec[i]):
                    bol_rec[i] = r.rec if (r.rec is not None and np.isfinite(r.rec)) else 0.0
    ent = np.flatnonzero(carb_g > 0)
    P = []                                   # (onset slot, size, peak, dur)
    for r in meals.itertuples() if len(meals) else []:
        o = slot(r.onset)
        if 0 <= o < T:
            P.append((o, r.size_g, r.peak_h, r.dur_h))
    P.sort()
    claimed_by = {}; used = set()
    for pi, (o, *_r) in enumerate(P):
        c = [e for e in ent if o - BEFORE <= e <= o + AFTER and e not in used]
        if c:
            claimed_by[pi] = c[0]; used.add(c[0])
    starts = {}                              # entry slot -> pulse it starts
    anchors = []; to_come = np.zeros(T)
    m_all, s_all = params(np.array([p[2] for p in P]) + 2.5 / 60, np.array([p[3] for p in P])) if P else ([], [])
    for pi, (o, size, pk, du) in enumerate(P):
        e = claimed_by.get(pi)
        if e is not None and o >= e - LEAD:
            starts[e] = pi; a = e
        else:
            a = o
            if a >= 1:
                Y[a - 1, ti("meal")] = 1; Y[a - 1, ti("m_lsize")] = np.log(size)
                Y[a - 1, ti("m_lpeak")] = np.log(max(pk + 2.5 / 60, 5 / 60)); Y[a - 1, ti("m_ldur")] = np.log(max(du, 0.25))
        anchors.append((a, size))
        j1 = min(o + 144, T)
        to_come[a:j1] += remaining((idx.asi8[a:j1] - idx.asi8[o]) / 3.6e12, size * geq, m_all[pi], s_all[pi])
    on = np.array([p[0] for p in P])
    for e in ent:
        if e < 1:
            continue
        Y[e - 1, ti("entry")] = 1; Y[e - 1, ti("e_lg")] = np.log(carb_g[e])
        if e in starts:
            o, size, pk, du = P[starts[e]]
            Y[e - 1, ti("e_new")] = 1; Y[e - 1, ti("e_off")] = np.log1p(max(o - e, 0) * 5.0)
            Y[e - 1, ti("e_lsize")] = np.log(size); Y[e - 1, ti("e_lpeak")] = np.log(max(pk + 2.5 / 60, 5 / 60))
            Y[e - 1, ti("e_ldur")] = np.log(max(du, 0.25))
        elif not len(on) or not ((on >= e - 12) & (on <= e + 24)).any():
            Y[e - 1, ti("e_new")] = 1        # a pulse the labeler missed: starts a meal, attributes unknown
        else:
            Y[e - 1, ti("e_new")] = 0
    for i in np.flatnonzero(bol_u > 0):
        if i >= 1:
            calc = bol_rec[i] > REC_ZERO
            Y[i - 1, ti("bolus")] = 1; Y[i - 1, ti("b_mode")] = 0.0 if calc else 1.0
            Y[i - 1, ti("b_lr")] = np.log(bol_u[i] / bol_rec[i]) if calc else np.nan
            Y[i - 1, ti("b_lu")] = np.log(max(bol_u[i], 0.05))
    since_meal = np.full(T, 24.0); last_size = np.zeros(T); n3 = np.zeros(T)
    last_i, last_s, recent = -10**9, 0.0, []
    am = dict(anchors)
    for i in range(T):
        if i in am:
            last_i, last_s = i, am[i]; recent.append(i)
        since_meal[i] = min((i - last_i) * 5 / 60, 24.0); last_size[i] = last_s
        n3[i] = sum(1 for j in recent if i - j < 36)
    sb = np.empty(T); last = -10**9
    for i in range(T):
        if bol_u[i] > 0:
            last = i
        sb[i] = min((i - last) * 5 / 60, 24.0)
    se, ub, b3 = action_inputs(T, carb_g, bol_u)
    eu = entered_since_meal(T, carb_g, [a for a, _ in anchors])
    ema = np.empty(T); e_ = np.nan
    for i in range(T):
        e_ = D3.ema_step(e_, bgice[i]); ema[i] = e_
    bgf = g.bg.to_numpy(); bgff = g.bg.ffill().bfill().to_numpy()
    trend = np.r_[np.full(D3.TREND_SLOTS, np.nan), (bgf[D3.TREND_SLOTS:] - bgf[:-D3.TREND_SLOTS]) / (D3.TREND_SLOTS * 5)]
    low30 = pd.Series((bgf < 70).astype(float)).rolling(6, min_periods=1).sum().to_numpy() * 5 / 30
    pr, hl = D3.predicted(bgff, np.nan_to_num(trend))
    cols = dict(
        bg=bgff / 100, bg_ok=g.bg.notna().to_numpy().astype(float), bg_trend=np.nan_to_num(trend) / 2, low30=low30,
        bg_pred30=pr / 100, heading_low=hl,
        eventual=(D3.eventual(bgff, g.iob.ffill().fillna(0).to_numpy(), isf, D3.basal_iob(steps), to_come) / 100) if isf else np.zeros(T),
        bgice=np.nan_to_num(bgice / ICE_SCALE), bgice_ema=np.nan_to_num(ema / ICE_SCALE), bgice_ok=np.isfinite(bgice).astype(float),
        pulse=pulses / ICE_SCALE, since_meal=since_meal / 24, last_size=last_size / 50, n_3h=n3 / 3,
        carbs=carb_g / 50, bolus=bol_u / 5, since_bolus=sb / 24, since_entry=se / 24, unbolused=ub / 50, bolus_3h=b3 / 5,
        entered_unabsorbed=eu / 50,
        **{k: np.nan_to_num(pd.Series(bgice / ICE_SCALE).rolling(n, min_periods=n // 6).mean().to_numpy()) for k, n in OWN_MEANS.items()},
        hour_sin=np.sin(2 * np.pi * g.hour / 24), hour_cos=np.cos(2 * np.pi * g.hour / 24),
        dow_sin=np.sin(2 * np.pi * g.dow / 7), dow_cos=np.cos(2 * np.pi * g.dow / 7))
    X = np.column_stack([np.asarray(cols[f], float) for f in features]).astype(np.float32)
    Y[:, ti("bgice")] = np.r_[bgice[1:], np.nan] / ICE_SCALE
    utc = pd.Series(idx.tz_convert("UTC") if idx.tz is not None else idx.tz_localize("UTC"))
    if decision_days is not None:
        off = ~utc.dt.floor("D").isin(decision_days).to_numpy()
        for k in BOLUS_T:
            Y[off, ti(k)] = np.nan
    if unknown_slots is not None and len(unknown_slots):
        off = np.r_[utc.dt.floor("5min").isin(unknown_slots).to_numpy()[1:], False]   # targets sit one row before their slot
        for k in BOLUS_T:
            Y[off, ti(k)] = np.nan
    return g, X, Y
