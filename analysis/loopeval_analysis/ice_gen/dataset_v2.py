"""v2 sequences: ICE plus the person's actions (carb entries, manual boluses) as targets, and a
running ICE budget as inputs.

Inputs per 5-min slot (fixed scaling, no fitting):
  v1 inputs without the controller-confounded ones (no IOB, insulin activity or auto-bolus — they
  read as meal evidence and ran the closed loop away; docs/ice/LESSONS.md):
    ice, ice_ok, bg, bg_ok, carbs entered, manual bolus units, clock
  running budget: excess ICE above the person's overnight baseline, positive part, summed over
    the last 1 / 3 / 6 / 24 h, in gram-equivalents (ISF_tdd / (500 / TDD) mg/dL per g-eq)
  hours since the last carb entry / manual bolus (capped at 24)

Targets for the NEXT slot:
  ice                                  (scaled, NaN where not clean)
  carb_ev, carb_lg, carb_labs          entry yes/no, log grams, log absorption hours
  bol_ev, bol_units_mode, bol_lr, bol_lu
                                       bolus yes/no; 1 = override (calculator recommended ~0, the
                                       person gave units anyway), 0 = calculator mode;
                                       log(requested / recommended); log units
Bolus events come from the bolus calculator's decision records (reason 'normalBolus'): what was
recommended and what the person requested.
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd

from .dataset import to_grid, ICE_SCALE

REC_ZERO = 0.05                     # U: below this the calculator recommended nothing
BUDGET_H = (1, 3, 6, 24)
FEATURES = ["ice", "ice_ok", "bg", "bg_ok", "carbs", "bolus_man", "hour_sin", "hour_cos", "dow_sin", "dow_cos",
            *[f"budget_{h}h" for h in BUDGET_H], "since_carb", "since_bolus"]
TARGETS = ["ice", "carb_ev", "carb_lg", "carb_labs", "bol_ev", "bol_units_mode", "bol_lr", "bol_lu"]


def person_constants(g: pd.DataFrame, tdd: float, isf: float) -> dict:
    base = float(np.nanmedian(g.ice[g.hour.between(2, 5)]))
    return dict(base=base if np.isfinite(base) else float(np.nanmedian(g.ice)), geq=isf / (500.0 / tdd))


def budget(ice: np.ndarray, base: float, geq: float) -> np.ndarray:
    """[T, 4] trailing sums of positive excess ICE in g-eq (NaN slots contribute 0)."""
    ex = np.clip(np.nan_to_num(ice - base), 0, None) * (5 / 60) / geq
    c = np.r_[0, np.cumsum(ex)]
    out = []
    for h in BUDGET_H:
        n = h * 12
        idx = np.arange(1, len(ex) + 1)
        out.append(c[idx] - c[np.clip(idx - n, 0, None)])
    return np.stack(out, 1)


def since(ev: np.ndarray, cap_h=24.0) -> np.ndarray:
    out = np.empty(len(ev)); last = -1e9
    for i, e in enumerate(ev):
        if e:
            last = i
        out[i] = min((i - last) * 5 / 60, cap_h)
    return out


def build(steps: pd.DataFrame, carbs: list, bolus_dec: pd.DataFrame, tdd: float, isf: float):
    """-> (grid, X [T, F], Y [T, len(TARGETS)], constants)."""
    g = to_grid(steps)
    k = person_constants(g, tdd, isf)
    T = len(g); idx = g.index
    slot = lambda t: idx.searchsorted(pd.Timestamp(t).floor("5min"))
    # carb entries at the moment Loop could see them
    carb_g = np.zeros(T); carb_abs = np.full(T, np.nan)
    for c in carbs:
        i = slot(c.get("dosingVisibleDate") or c["startDate"])
        if 0 <= i < T:
            carb_g[i] += float(c["grams"])
            carb_abs[i] = float(c.get("absorptionTime") or 10800) / 3600
    # manual boluses from the calculator's decision records
    bol_u = np.zeros(T); bol_mode = np.full(T, np.nan); bol_lr = np.full(T, np.nan)
    for r in bolus_dec.itertuples():
        if not (r.requested and r.requested > 0):
            continue
        i = slot(r.t)
        if not 0 <= i < T:
            continue
        bol_u[i] += r.requested
        if r.rec is not None and r.rec > REC_ZERO:
            bol_mode[i] = 0.0; bol_lr[i] = np.log(r.requested / r.rec)
        else:
            bol_mode[i] = 1.0
    ice = g.ice.to_numpy()
    B = budget(ice, k["base"], k["geq"])
    X = np.column_stack([
        np.nan_to_num(ice / ICE_SCALE), np.isfinite(ice).astype(float),
        g.bg.ffill().bfill().to_numpy() / 100.0, g.bg.notna().to_numpy().astype(float),
        carb_g / 50.0, bol_u / 5.0,
        np.sin(2 * np.pi * g.hour / 24), np.cos(2 * np.pi * g.hour / 24),
        np.sin(2 * np.pi * g.dow / 7), np.cos(2 * np.pi * g.dow / 7),
        B / 50.0, since(carb_g > 0) / 24, since(bol_u > 0) / 24,
    ]).astype(np.float32)
    nxt = lambda a: np.r_[a[1:], np.nan]
    Y = np.column_stack([
        nxt(ice / ICE_SCALE),
        nxt((carb_g > 0).astype(float)), nxt(np.where(carb_g > 0, np.log(np.maximum(carb_g, 1)), np.nan)),
        nxt(np.log(carb_abs)),
        nxt((bol_u > 0).astype(float)), nxt(bol_mode), nxt(bol_lr),
        nxt(np.where(bol_u > 0, np.log(np.maximum(bol_u, 0.05)), np.nan)),
    ]).astype(np.float32)
    Y[-1, [1, 4]] = 0.0
    return g, X, Y, k
