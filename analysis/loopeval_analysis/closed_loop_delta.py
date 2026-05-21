"""Closed-loop ICE simulator with fixed-Δ rule overrides.

Extends `closed_loop_ice_sim` to support rules that propose arbitrary per-step
Δ-doses (positive = extra boost, negative = cut) instead of ISF multipliers.

The simulator:
  • At each 5-min step, advances counter_bg via ICE + v_insulin_candidate.
  • Loop sees counter_bg (NOT observed BG after t_0).
  • Loop computes its own recommendation via simple_loop_recommend.
  • The candidate's actual dose = Loop's recommendation + delta_lookup(t_sec).
    Cuts are floored at -(scheduled_basal × dt) so we can't deliver negative
    insulin overall.
  • Result: counter_bg evolves under (Loop's reactive dose + rule's fixed Δ).
    Loop's counter-response is implicit — if BG rises due to a cut, Loop's
    next recommendation increases. If BG falls due to a boost, Loop's
    recommendation decreases.

This is the missing piece between linear-what-if (no response) and the full
Swift simulator. Faster than Swift, more realistic than linear what-if.

Limitations:
  • Same linear PD model as static evaluator. Real insulin action has
    BG-dependent components.
  • Observed ICE is used as a fixed signal — assumes non-insulin BG drivers
    are the same in counterfactual. Reasonable for small rules, less for
    large structural changes.
  • simple_loop_recommend is a simplified Loop reimplementation, not the
    full Swift Loop. Known to produce different absolute TIR than real Loop
    (see feedback_sim_actual_baseline). Use deltas vs baseline-sim, not
    absolute values.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd

from .ice_sim import (
    DoseHistory, LoopConfig, simple_loop_recommend, v_insulin_at,
    percent_remaining_lookup,
)


@dataclass
class DeltaSimResult:
    times: pd.DatetimeIndex
    actual_bg: np.ndarray         # observed BG (reference)
    baseline_counter_bg: np.ndarray  # counter-BG under Loop alone (no rule)
    candidate_counter_bg: np.ndarray # counter-BG under Loop + rule
    loop_dose: np.ndarray         # Loop's per-step recommendation under candidate
    rule_delta: np.ndarray        # rule's per-step Δ-dose
    delivered_dose: np.ndarray    # net delivered = loop + rule_delta (after floor)
    baseline_outcomes: dict
    candidate_outcomes: dict


def outcomes(bg_arr: np.ndarray) -> dict:
    bg = bg_arr[~np.isnan(bg_arr)]
    if bg.size == 0: return {"n": 0}
    return {
        "n": int(bg.size),
        "mean_bg":     float(bg.mean()),
        "tir_70_180":  float(((bg >= 70) & (bg < 180)).mean()),
        "t_below_70":  float((bg < 70).mean()),
        "t_below_54":  float((bg < 54).mean()),
        "t_above_180": float((bg >= 180).mean()),
        "t_above_250": float((bg >= 250).mean()),
        "auc_below_70": float(np.maximum(0, 70 - bg).sum()),
        "auc_above_180":float(np.maximum(0, bg - 180).sum()),
    }


def closed_loop_delta_sim(
    observed_bg: pd.Series,            # observed BG at 5-min cadence
    actual_doses: DoseHistory,         # observed dose history
    ice: np.ndarray,                   # ICE = v_cgm - v_insulin (mg/dL/min) at each step
    isf_schedule: Callable[[float], float],   # ISF (mg/dL/U) lookup by t_sec
    scheduled_basal: Callable[[float], float],  # basal U/hr by t_sec
    delta_lookup: Optional[Callable[[float], float]] = None,  # rule's Δ U at t_sec; None = baseline
    config: Optional[LoopConfig] = None,
) -> DeltaSimResult:
    """Run closed-loop sim with arbitrary per-step Δ-overrides.

    Two passes:
      Pass 1: baseline (no rule, delta_lookup=None) — Loop alone on counterfactual.
      Pass 2: candidate (with delta_lookup) — Loop's recommendation + rule's Δ.

    Returns outcomes for both, plus diagnostic trace.
    """
    if config is None:
        config = LoopConfig()

    idx = observed_bg.index
    n = len(idx)
    actual_arr = observed_bg.to_numpy(dtype=float)

    if idx.tz is not None:
        t_sec_arr = idx.tz_convert("UTC").asi8 // 1_000_000_000
    else:
        t_sec_arr = idx.asi8 // 1_000_000_000
    t_sec_arr = t_sec_arr.astype(np.float64)

    def _run_pass(rule_callable):
        """Single closed-loop pass. Returns counter_bg, loop_dose, rule_delta, delivered."""
        cand_history = DoseHistory(
            times_sec=actual_doses.times_sec.copy(),
            volumes_U=actual_doses.volumes_U.copy(),
            isf_at_dose=actual_doses.isf_at_dose.copy(),
        )
        counter_bg = actual_arr.copy()
        loop_dose_arr = np.zeros(n)
        rule_delta_arr = np.zeros(n)
        delivered_arr = np.zeros(n)

        for i in range(n - 1):
            t_sec = t_sec_arr[i]
            dt_sec = float(t_sec_arr[i + 1] - t_sec)
            dt_h = dt_sec / 3600.0
            bg_now = counter_bg[i]
            isf = float(isf_schedule(t_sec))
            sched = float(scheduled_basal(t_sec))

            # Loop's per-step Δ-U recommendation (above scheduled, can be negative)
            loop_rec = simple_loop_recommend(
                bg_current=bg_now,
                dose_history=cand_history,
                t_sec=t_sec,
                scheduled_basal_uhr=sched,
                isf_mgdl_per_u=isf,
                config=LoopConfig(
                    target_bg=config.target_bg,
                    suspend_threshold=config.suspend_threshold,
                    application_factor=config.application_factor,
                    forecast_horizon_sec=config.forecast_horizon_sec,
                    max_basal_uhr=config.max_basal_uhr,
                    max_bolus_u=config.max_bolus_u,
                    eval_step_sec=dt_sec,
                    isf_multiplier=1.0,
                ),
            )
            loop_dose_arr[i] = loop_rec

            # Rule's fixed Δ override
            rule_d = rule_callable(t_sec) if rule_callable is not None else 0.0
            rule_delta_arr[i] = rule_d

            # Delivered = loop_rec + rule_d, but floor at -(scheduled × dt) so the
            # candidate can't go below "no insulin at all". Loop's `loop_rec` is
            # Δ above scheduled, so the floor for combined delta vs scheduled is
            # -sched × dt_h.
            sched_step_u = sched * dt_h
            min_delta_vs_sched = -sched_step_u
            combined = loop_rec + rule_d
            combined = max(combined, min_delta_vs_sched)
            delivered_arr[i] = combined

            # Append virtual dose representing the candidate's delta above scheduled
            if abs(combined) > 1e-9:
                cand_history = cand_history.add(
                    t_sec=t_sec + dt_sec / 2.0,
                    volume_U=combined,
                    isf=isf,
                )

            # Advance counter_bg
            v_ins = v_insulin_at(cand_history, t_sec, dt_sec=dt_sec)
            dt_min = dt_sec / 60.0
            counter_bg[i + 1] = bg_now + dt_min * (ice[i] + v_ins)
        return counter_bg, loop_dose_arr, rule_delta_arr, delivered_arr

    # Baseline pass (Loop alone)
    base_bg, _, _, _ = _run_pass(None)

    # Candidate pass (Loop + rule)
    cand_bg, loop_arr, rule_arr, deliv_arr = _run_pass(delta_lookup)

    return DeltaSimResult(
        times=idx,
        actual_bg=actual_arr,
        baseline_counter_bg=base_bg,
        candidate_counter_bg=cand_bg,
        loop_dose=loop_arr,
        rule_delta=rule_arr,
        delivered_dose=deliv_arr,
        baseline_outcomes=outcomes(base_bg),
        candidate_outcomes=outcomes(cand_bg),
    )
