"""Linear what-if simulator: apply candidate Δ-doses to observed BG via linear PD.

The static evaluator (insulin_hole / insulin_excess) uses linear PD to compute
per-step counterfactuals: a dose Δ at time t shifts BG at time t+τ by
   ΔBG(t+τ) = Δ × ISF × pd_fraction(τ)
where pd_fraction(τ) = 1 − percent_effect_remaining(τ) is the fraction of total
effect that has acted by τ.

This module extends that to a trajectory-level counterfactual: sum the BG
impact of EVERY proposed Δ across all future timestamps, add to observed BG,
then re-evaluate outcomes.

Limitations (important):
  • NO Loop response. If BG rises due to a cut, the real Loop would dose more
    to compensate. This simulator ignores that — so the result is an UPPER
    BOUND on benefit / cost. Real benefits (with Loop counter-action) are
    smaller.
  • Linear PD assumption. Real insulin action has BG-dependent components
    (e.g., glucose-mediated insulin sensitivity changes). The static evaluator
    accepts this approximation, and so does this simulator.
  • Observed BG was the true trajectory under actual doses. The counterfactual
    assumes physiology was otherwise stationary.

Use for fast first-pass evaluation: if even the upper bound shows trivial TIR
change, the rule isn't worth full-sim validation. If the upper bound shows
meaningful improvement, follow with closed-loop simulator.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd

from .ice_sim import percent_remaining_lookup


@dataclass
class WhatIfResult:
    times: pd.DatetimeIndex
    actual_bg: np.ndarray
    counter_bg: np.ndarray
    delta_applied: np.ndarray
    n_active_steps: int           # Number of steps where rule fired (|Δ| > 0)
    total_delta_u: float          # Sum of |Δ| across firing steps
    actual_outcomes: dict
    counter_outcomes: dict


def outcomes(bg_arr: np.ndarray) -> dict:
    bg = bg_arr[~np.isnan(bg_arr)]
    if bg.size == 0:
        return {"n": 0}
    return {
        "n": int(bg.size),
        "mean_bg":    float(bg.mean()),
        "tir_70_180": float(((bg >= 70) & (bg < 180)).mean()),
        "t_below_70": float((bg < 70).mean()),
        "t_below_54": float((bg < 54).mean()),
        "t_above_180":float((bg >= 180).mean()),
        "t_above_250":float((bg >= 250).mean()),
        "auc_below_70": float(np.maximum(0, 70 - bg).sum()),
        "auc_above_180":float(np.maximum(0, bg - 180).sum()),
    }


def apply_delta_stream(
    observed_bg: pd.Series,
    delta_u: pd.Series,
    isf_schedule: Callable[[float], float],
    *,
    dia_sec: float = 21600,
    step_sec: float = 300.0,
) -> WhatIfResult:
    """Apply candidate per-step Δ-doses to observed BG via linear PD.

    Parameters
    ----------
    observed_bg : pd.Series, indexed by timestamp.
    delta_u     : pd.Series of proposed Δ-doses (positive = boost, negative = cut),
                  indexed on same grid.
    isf_schedule : t_sec → ISF (mg/dL/U).
    dia_sec     : duration of insulin action (default 6h).
    step_sec    : sample cadence (default 5 min).

    Returns counterfactual BG + outcomes for observed AND counterfactual.
    """
    # Align
    idx = observed_bg.index
    actual_arr = observed_bg.to_numpy(dtype=float)
    delta_arr = delta_u.reindex(idx, method="nearest",
                                  tolerance=pd.Timedelta("3min")).fillna(0.0).to_numpy(dtype=float)
    n = len(idx)

    # Times in seconds
    if idx.tz is not None:
        t_sec = idx.tz_convert("UTC").asi8 // 1_000_000_000
    else:
        t_sec = idx.asi8 // 1_000_000_000
    t_sec = t_sec.astype(np.float64)

    # Window length: DIA / step_sec = number of future steps a dose impacts
    dia_steps = int(dia_sec / step_sec)

    # Pre-compute pd_done lookup for tau = 0, step, 2*step, ..., dia
    tau_grid = np.arange(0, dia_steps + 1) * step_sec
    pd_remaining = percent_remaining_lookup(tau_grid)
    pd_done = 1.0 - pd_remaining   # fraction of total effect acted by tau

    # Counter BG starts as actual
    counter_bg = actual_arr.copy()

    # Find indices where delta is non-zero
    active_idx = np.nonzero(np.abs(delta_arr) > 1e-9)[0]
    total_delta_u = float(np.abs(delta_arr).sum())
    n_active = int(len(active_idx))

    # For each active dose at index i, add ΔBG(τ) = δ × ISF × pd_done(τ) to counter_bg[i+τ_steps]
    # Sign convention: positive Δ (boost) → MORE insulin → BG LOWER by δ×ISF×pd_done.
    # So:  counter_bg(i+k) -= delta * isf * pd_done(k)
    for i in active_idx:
        delta = delta_arr[i]
        isf = float(isf_schedule(t_sec[i]))
        if isf <= 0: continue
        end = min(i + dia_steps + 1, n)
        ks = np.arange(end - i)
        # ΔBG (negative for boost, positive for cut)
        contrib = delta * isf * pd_done[:len(ks)]
        counter_bg[i:end] -= contrib

    actual_out = outcomes(actual_arr)
    counter_out = outcomes(counter_bg)

    return WhatIfResult(
        times=idx,
        actual_bg=actual_arr,
        counter_bg=counter_bg,
        delta_applied=delta_arr,
        n_active_steps=n_active,
        total_delta_u=total_delta_u,
        actual_outcomes=actual_out,
        counter_outcomes=counter_out,
    )


def format_outcome_diff(actual: dict, counter: dict) -> pd.DataFrame:
    """Side-by-side outcome diff table."""
    keys = ["mean_bg", "tir_70_180", "t_below_70", "t_below_54",
            "t_above_180", "t_above_250", "auc_below_70", "auc_above_180"]
    rows = []
    for k in keys:
        a = actual.get(k, np.nan); c = counter.get(k, np.nan)
        rows.append({
            "metric": k,
            "observed": a,
            "counter": c,
            "delta": c - a,
            "delta_pp": (c - a) * 100 if k.startswith(("tir", "t_")) else (c - a),
        })
    return pd.DataFrame(rows)
