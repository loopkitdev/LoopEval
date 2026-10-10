"""v3 sequences: meals as events.

ICE = background + sum of meal pulses (kernel.py). A meal is anchored at its FIRST action — the
earliest of absorption onset, carb entry and meal bolus — so a person can log and bolus before
eating; everything else about the meal is an offset >= 0 from that anchor.

Inputs per 5-min slot (fixed scaling):
  bg, bg_ok                      plant BG as a CGM reports it
  bgice, bgice_ok                background ICE (ICE minus labeled meal pulses), this slot
  pulse                          current total meal-pulse rate (known to a generator)
  since_meal, last_size, n_3h    hours since the last meal anchor, its size, meals in last 3 h
  carbs, bolus, since_bolus      the person's own actions this slot / hours since a bolus
  clock                          hour, weekday (sin/cos)
FEATURES_B (v3b) instead feeds background ICE as a causal 30-min EMA (bgice_ema): the plant cannot feed back
its own noisy draws (the spread runs away) and its predictive mean is smoother than anything seen in training
(meal durations 1.9 -> 2.5 h), so training and plant both get the same smoothed quantity. It adds what a person
reacts to near a low: the CGM trend (bg_trend, mg/dL per min over 15 min) and minutes below 70 in the last 30.
Targets for the NEXT slot:
  bgice                          background ICE (scaled), NaN where not clean
  meal                           a meal is anchored here (0/1); attributes when 1:
    m_lsize, m_lpeak, m_ldur     log g-eq, log peak h, log duration h
    m_onset, m_entry, m_bolus    log1p minutes from anchor to absorption onset / entry / bolus
    m_ann, m_lg                  announced (0/1), log grams logged (what the person typed; modelled
                                 directly — exp of a noisy log(grams/size) inflated entries ~3x)
    m_hasbol, m_mode, m_lr, m_lu meal bolus (0/1), override (1) vs calculator (0), log ratio, log units
  corr                           a correction bolus (no meal) here (0/1); c_mode, c_lr, c_lu
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .dataset import to_grid, ICE_SCALE
from .kernel import reconstruct

FEATURES = ["bg", "bg_ok", "bgice", "bgice_ok", "pulse", "since_meal", "last_size", "n_3h",
            "carbs", "bolus", "since_bolus", "hour_sin", "hour_cos", "dow_sin", "dow_cos"]
MEAL_T = ["m_lsize", "m_lpeak", "m_ldur", "m_onset", "m_entry", "m_bolus", "m_ann", "m_lg",
          "m_hasbol", "m_mode", "m_lr", "m_lu"]
FEATURES_B = ["bg", "bg_ok", "bg_trend", "low30", "bgice_ema", "bgice_ok", "pulse", "since_meal", "last_size", "n_3h",
              "carbs", "bolus", "since_bolus", "hour_sin", "hour_cos", "dow_sin", "dow_cos"]
TARGETS = ["bgice", "meal", *MEAL_T, "corr", "c_mode", "c_lr", "c_lu"]
REC_ZERO = 0.05
EMA_A = 1 - np.exp(-5 / 30)                 # 30-min time constant on 5-min slots
TREND_SLOTS = 3                             # 15 min


def ema_step(prev, x):
    """One causal EMA step; a missing value holds the previous level."""
    return prev if not np.isfinite(x) else (x if not np.isfinite(prev) else prev + EMA_A * (x - prev))


def build(steps, meals, corrections, bolus_dec, carbs, geq, features=FEATURES):
    g = to_grid(steps)
    T, idx = len(g), g.index
    pulses = reconstruct(idx, meals, geq) if len(meals) else np.zeros(T)
    bgice = (g.ice - pulses).to_numpy()
    slot = lambda t: int(idx.searchsorted(pd.Timestamp(t).floor("5min")))
    Y = np.full((T, len(TARGETS)), np.nan, np.float32)
    Y[:, TARGETS.index("meal")] = 0; Y[:, TARGETS.index("corr")] = 0
    since_meal = np.full(T, 24.0); last_size = np.zeros(T); n3 = np.zeros(T)
    anchors = []
    bd = bolus_dec.set_index("t") if len(bolus_dec) else None
    for r in meals.itertuples():
        onset = r.onset
        entry = onset + pd.Timedelta(minutes=r.entry_delay_min) if r.announced and np.isfinite(r.entry_delay_min) else None
        bol = onset + pd.Timedelta(minutes=r.bolus_lead_min) if np.isfinite(r.bolus_lead_min) else None
        anchor = min([x for x in (onset, entry, bol) if x is not None])
        i = slot(anchor)
        if not 0 <= i < T:
            continue
        anchors.append((i, r.size_g))
        off = lambda x: np.log1p(max((x - anchor).total_seconds() / 60, 0)) if x is not None else np.nan
        row = dict(meal=1, m_lsize=np.log(r.size_g), m_lpeak=np.log(max(r.peak_h + 2.5 / 60, 5 / 60)),
                   m_ldur=np.log(max(r.dur_h, 0.25)), m_onset=off(onset), m_entry=off(entry), m_bolus=off(bol),
                   m_ann=float(r.announced), m_lg=np.log(r.entry_g) if r.announced and r.entry_g > 0 else np.nan,
                   m_hasbol=float(r.bolus_u > 0),
                   m_mode=(1.0 if r.bolus_mode == "override" else 0.0) if r.bolus_u > 0 else np.nan,
                   m_lr=np.log(r.bolus_ratio) if r.bolus_u > 0 and np.isfinite(r.bolus_ratio) and r.bolus_ratio > 0 else np.nan,
                   m_lu=np.log(max(r.bolus_u, 0.05)) if r.bolus_u > 0 else np.nan)
        for k, v in row.items():
            Y[i - 1, TARGETS.index(k)] = v if i >= 1 else np.nan       # target of the PREVIOUS slot's step
    for c in corrections.itertuples() if len(corrections) else []:
        i = slot(c.t)
        if 1 <= i < T:
            Y[i - 1, TARGETS.index("corr")] = 1
            calc = c.rec is not None and np.isfinite(c.rec) and c.rec > REC_ZERO
            Y[i - 1, TARGETS.index("c_mode")] = 0.0 if calc else 1.0
            Y[i - 1, TARGETS.index("c_lr")] = np.log(c.units / c.rec) if calc else np.nan
            Y[i - 1, TARGETS.index("c_lu")] = np.log(max(c.units, 0.05))
    # meal-history inputs
    last_i, last_s, recent = -10**9, 0.0, []
    am = dict(anchors)
    for i in range(T):
        if i in am:
            last_i, last_s = i, am[i]; recent.append(i)
        since_meal[i] = min((i - last_i) * 5 / 60, 24.0); last_size[i] = last_s
        n3[i] = sum(1 for j in recent if i - j < 36)
    # actions as inputs
    carb_g = np.zeros(T); bol_u = np.zeros(T)
    for c in carbs:
        i = slot(c.get("entryDate") or c["startDate"])
        if 0 <= i < T:
            carb_g[i] += float(c["grams"])
    for r in bolus_dec.itertuples() if len(bolus_dec) else []:
        if r.requested and r.requested > 0:
            i = slot(r.t)
            if 0 <= i < T:
                bol_u[i] += r.requested
    sb = np.empty(T); last = -10**9
    for i in range(T):
        if bol_u[i] > 0:
            last = i
        sb[i] = min((i - last) * 5 / 60, 24.0)
    ema = np.empty(T); e = np.nan
    for i in range(T):
        e = ema_step(e, bgice[i]); ema[i] = e
    bgf = g.bg.to_numpy()
    trend = np.r_[np.full(TREND_SLOTS, np.nan), (bgf[TREND_SLOTS:] - bgf[:-TREND_SLOTS]) / (TREND_SLOTS * 5)]
    low30 = pd.Series((bgf < 70).astype(float)).rolling(6, min_periods=1).sum().to_numpy() * 5 / 30
    cols = dict(
        bg=g.bg.ffill().bfill().to_numpy() / 100, bg_ok=g.bg.notna().to_numpy().astype(float),
        bg_trend=np.nan_to_num(trend) / 2, low30=low30,
        bgice=np.nan_to_num(bgice / ICE_SCALE), bgice_ema=np.nan_to_num(ema / ICE_SCALE), bgice_ok=np.isfinite(bgice).astype(float),
        pulse=pulses / ICE_SCALE, since_meal=since_meal / 24, last_size=last_size / 50, n_3h=n3 / 3,
        carbs=carb_g / 50, bolus=bol_u / 5, since_bolus=sb / 24,
        hour_sin=np.sin(2 * np.pi * g.hour / 24), hour_cos=np.cos(2 * np.pi * g.hour / 24),
        dow_sin=np.sin(2 * np.pi * g.dow / 7), dow_cos=np.cos(2 * np.pi * g.dow / 7))
    X = np.column_stack([np.asarray(cols[f], float) for f in features]).astype(np.float32)
    Y[:, TARGETS.index("bgice")] = np.r_[bgice[1:], np.nan] / ICE_SCALE
    return g, X, Y
