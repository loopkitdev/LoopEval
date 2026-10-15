"""v3m sequences: carb entries and manual boluses as their own events, apart from meal pulses.

v3 tied each meal pulse to one summed carb entry and one summed bolus (labels within -60/+90 min of an onset);
entries no pulse claimed were dropped and their boluses became 'corrections'. That squeezed the hands-on people
most: a donor logging 11 entries and 13 boluses a day was labeled with ~6 meals, and generated with 3.7 and 5.8
(2026-10-13, runs/2026-10-13-ice-rates). Field: 76% of entries have a bolus within 2 min; 52% of boluses have no
entry within 2 min.

Here every action the person took is a target in its own slot, drawn in order within a slot:
  meal     a meal pulse starts (absorption onset); m_lsize, m_lpeak, m_ldur as in v3
  entry    a carb entry (0/1); e_lg log grams (entries in one slot summed)
  bolus    a manual bolus (0/1), after the entry draw; b_mode override (1) / calculator (0), b_lr log ratio to the
           calculator's recommendation (calculator only), b_lu log units
Inputs: FEATURES_C plus since_entry (h), unbolused (grams entered in the last 3 h since the last bolus) and
bolus_3h (units bolused in the last 3 h). Meal history inputs count pulse onsets.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .dataset import to_grid, ICE_SCALE
from .kernel import reconstruct, remaining, params
from . import dataset_v3 as D3

FEATURES_M = D3.FEATURES_C + ["since_entry", "unbolused", "bolus_3h"]
# FEATURES_M2: + grams entered in the last 3 h since the latest meal pulse began. v3m left 25% of generated entries with no
# pulse within -60/+120 min (field 16%), and the controller dosed for carbs that never came (t<54 3.1 vs 0.04)
FEATURES_M2 = FEATURES_M + ["entered_unabsorbed"]
# FEATURES_M2A: + this slot's background ICE itself (0 where unknown, with bgice_ok), so the model conditions on its own last
# value directly; generation feeds back the draw (plant --feedback sample / PLANT_FEEDBACK=sample). The indirect channels
# (CGM trend, 30-min EMA) carried real ICE in training and the model's draws in generation (LESSONS 42).
FEATURES_M2A = FEATURES_M2 + ["bgice"]
# M2I: + the insulin action still to come above the basal level, ISF x (IOB - basal IOB) in mg/dL / 100: what a person reads
# off Loop's screen and acts on ahead of a low (Pete, 2026-10-14: the defense, insulin plus anticipatory carbs and walks,
# strengthens as excursions widen and is individual in how early it acts). Generated lows began with 0.56 vs 0.15 U above
# basal and the model had no input that showed it (LESSONS 60).
FEATURES_M2I = FEATURES_M2A + ["iob_net"]
# FEATURES_M2B: + the person's own background ICE averaged over the last 6 h and 24 h (exact channels, computed the same way
# from real values in training and from the model's own draws in the plant). One channel (the last value) could not carry
# both the 5-min structure and the day level: generated levels drifted (day-to-day sd 23.5 vs 11.1), and teaching it to pull
# back through that channel cost the 5-min structure (LESSONS 47). Real days revert (1-day persistence 0.39).
FEATURES_M2B = FEATURES_M2A + ["bgice_6h", "bgice_24h"]
OWN_MEANS = {"bgice_6h": 72, "bgice_24h": 288}     # slots
TARGETS = ["bgice", "meal", "m_lsize", "m_lpeak", "m_ldur", "entry", "e_lg", "bolus", "b_mode", "b_lr", "b_lu"]
BOLUS_T = ["bolus", "b_mode", "b_lr", "b_lu"]
REC_ZERO = D3.REC_ZERO


def action_inputs(T, carb_g, bol_u):
    """since_entry (h, capped 24), unbolused grams (entered in the last 3 h after the last bolus), bolus_3h (U)."""
    se = np.empty(T); ub = np.zeros(T); b3 = np.zeros(T)
    last_e = -10**9; pend = []          # (slot, grams) not yet followed by a bolus
    cb = np.cumsum(bol_u)
    for i in range(T):
        if carb_g[i] > 0:
            last_e = i; pend.append((i, carb_g[i]))
        if bol_u[i] > 0:
            pend = []
        pend = [(j, g) for j, g in pend if i - j < 36]
        se[i] = min((i - last_e) * 5 / 60, 24.0); ub[i] = sum(g for _, g in pend)
        b3[i] = cb[i] - (cb[i - 36] if i >= 36 else 0.0)
    return se, ub, b3


def entered_since_meal(T, carb_g, onsets):
    """grams entered in the last 3 h (36 slots) after the latest meal-pulse onset at or before each slot"""
    out = np.zeros(T); last_on = -10**9; on = set(onsets); pend = []
    for i in range(T):
        if i in on:
            last_on = i; pend = []
        if carb_g[i] > 0:
            pend.append((i, carb_g[i]))
        pend = [(j, g) for j, g in pend if i - j < 36 and j >= last_on]
        out[i] = sum(g for _, g in pend)
    return out


def build(steps, meals, bolus_dec, carbs, geq, features=FEATURES_M, isf=None, decision_days=None):
    g = to_grid(steps)
    T, idx = len(g), g.index
    pulses = reconstruct(idx, meals, geq) if len(meals) else np.zeros(T)
    bgice = (g.ice - pulses).to_numpy()
    slot = lambda t: int(idx.searchsorted(pd.Timestamp(t).floor("5min")))
    Y = np.full((T, len(TARGETS)), np.nan, np.float32)
    for k in ("meal", "entry", "bolus"):
        Y[:, TARGETS.index(k)] = 0
    ti = TARGETS.index
    since_meal = np.full(T, 24.0); last_size = np.zeros(T); n3 = np.zeros(T)
    anchors = []; to_come = np.zeros(T)
    m_all, s_all = params(meals.peak_h.to_numpy() + 2.5 / 60, meals.dur_h.to_numpy()) if len(meals) else ([], [])
    for mi, r in enumerate(meals.itertuples()):
        i = slot(r.onset)
        if not 0 <= i < T:
            continue
        anchors.append((i, r.size_g))
        j1 = min(slot(r.onset + pd.Timedelta(hours=12)), T)
        to_come[i:j1] += remaining((idx.asi8[i:j1] - r.onset.value) / 3.6e12, r.size_g * geq, m_all[mi], s_all[mi])
        if i >= 1:                                   # target of the PREVIOUS slot's step
            Y[i - 1, ti("meal")] = 1; Y[i - 1, ti("m_lsize")] = np.log(r.size_g)
            Y[i - 1, ti("m_lpeak")] = np.log(max(r.peak_h + 2.5 / 60, 5 / 60)); Y[i - 1, ti("m_ldur")] = np.log(max(r.dur_h, 0.25))
    last_i, last_s, recent = -10**9, 0.0, []
    am = dict(anchors)
    for i in range(T):
        if i in am:
            last_i, last_s = i, am[i]; recent.append(i)
        since_meal[i] = min((i - last_i) * 5 / 60, 24.0); last_size[i] = last_s
        n3[i] = sum(1 for j in recent if i - j < 36)
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
    for i in np.flatnonzero(carb_g > 0):
        if i >= 1:
            Y[i - 1, ti("entry")] = 1; Y[i - 1, ti("e_lg")] = np.log(carb_g[i])
    for i in np.flatnonzero(bol_u > 0):
        if i >= 1:
            calc = bol_rec[i] > REC_ZERO
            Y[i - 1, ti("bolus")] = 1; Y[i - 1, ti("b_mode")] = 0.0 if calc else 1.0
            Y[i - 1, ti("b_lr")] = np.log(bol_u[i] / bol_rec[i]) if calc else np.nan
            Y[i - 1, ti("b_lu")] = np.log(max(bol_u[i], 0.05))
    sb = np.empty(T); last = -10**9
    for i in range(T):
        if bol_u[i] > 0:
            last = i
        sb[i] = min((i - last) * 5 / 60, 24.0)
    se, ub, b3 = action_inputs(T, carb_g, bol_u)
    eu = entered_since_meal(T, carb_g, [i for i, _ in anchors])
    ema = np.empty(T); e = np.nan
    for i in range(T):
        e = D3.ema_step(e, bgice[i]); ema[i] = e
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
        carbs=carb_g / 50, bolus=bol_u / 5, since_bolus=sb / 24, since_entry=se / 24, unbolused=ub / 50, bolus_3h=b3 / 5, entered_unabsorbed=eu / 50,
        hour_sin=np.sin(2 * np.pi * g.hour / 24), hour_cos=np.cos(2 * np.pi * g.hour / 24),
        dow_sin=np.sin(2 * np.pi * g.dow / 7), dow_cos=np.cos(2 * np.pi * g.dow / 7))
    X = np.column_stack([np.asarray(cols[f], float) for f in features]).astype(np.float32)
    Y[:, ti("bgice")] = np.r_[bgice[1:], np.nan] / ICE_SCALE
    if decision_days is not None:           # who issued a bolus is unknown on HealthKit-only days (D3.bolus_unknown_days)
        off = ~pd.Series(idx.tz_convert("UTC") if idx.tz is not None else idx.tz_localize("UTC")).dt.floor("D").isin(decision_days).to_numpy()
        for k in BOLUS_T:
            Y[off, ti(k)] = np.nan
    return g, X, Y
