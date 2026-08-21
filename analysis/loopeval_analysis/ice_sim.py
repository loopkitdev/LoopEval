"""ICE-based closed-loop simulator (Python).

Independent of the Swift simulator. Uses an ICE-extraction counterfactual that
avoids the "baseline_recompute vs actual_delivered" systematic-error problem in
the Swift sim.

Counterfactual construction
---------------------------

At each 5-min step the counter_BG evolves as:

    counter_BG(t+Δt) = counter_BG(t)  +  Δt × ( ICE(t)  +  v_insulin_candidate(t) )

where:
  • ``ICE(t) = v_cgm_actual(t) - v_insulin_actual(t)`` is extracted from the
    observed trace and the actual dose history. ICE captures everything
    non-insulin (carbs, EGP, exercise, noise, …).
  • ``v_insulin_candidate(t)`` is the time-derivative of the *candidate's*
    cumulative insulin effect, computed from the candidate's own dose history
    (which equals actual dose history initially and accumulates virtual doses
    as the candidate makes its own decisions).
  • Equivalently:
    ``counter_BG(t) = actual_BG(t) − (InsulinEffect_candidate(t) − InsulinEffect_actual(t))``.

Identity case: if candidate's dose history equals actual's, then InsulinEffect
diff is zero and counter_BG = actual_BG exactly. No drift, no systematic offset.

Simplified Loop dose model
--------------------------

The dose-recommendation function ``simple_loop_recommend`` reimplements a
faithful but simplified version of LoopAlgorithm's correction logic:

  • BG forecast at horizon h: ``BG(t) − insulin_effect_remaining(t, t+h)``
    (no momentum, no carb forecast — ICE captures recent carbs implicitly).
  • Correction: ``(BG_predicted - target) / ISF × application_factor``
    when BG_predicted > target.
  • Suspend logic: if BG_current ≤ suspend_threshold, recommend 0 U/hr temp basal.
  • Caps: max_basal_rate; max_bolus.
  • Output: U over the next eval_step (i.e., +deltaU above scheduled basal).

This is intentionally simpler than real Loop. It does not match real Loop's
behavior exactly but is faithful to the broad shape (forecast → correction →
caps) and is enough to test methodology + rule mechanism directionally.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import pandas as pd


# ─── Insulin pharmacodynamics ─────────────────────────────────────────────
# Matches LoopAlgorithm's exponential model for rapid-acting adult insulin
# closely enough for our purposes.

def percent_effect_remaining(t_sec: float,
                             action_duration_sec: float = 6 * 3600,
                             peak_min: float = 75,
                             delay_sec: float = 600.0) -> float:
    """Exponential insulin model — fraction of effect REMAINING at time t after dose.

    At t=0 returns 1.0 (no effect yet), at t≥delay+action_duration returns 0
    (fully delivered). Matches LoopAlgorithm.ExponentialInsulinModel, INCLUDING
    its 10-min effect delay (the curve evaluates at t−delay and the total span
    is delay+actionDuration — ExponentialInsulinModel.swift:27,40,55; the delay
    was previously omitted here, shifting every effect 10 min early).
    """
    t_sec = t_sec - delay_sec
    if t_sec <= 0:
        return 1.0
    if t_sec >= action_duration_sec:
        return 0.0
    peak_sec = peak_min * 60.0
    tau = peak_sec * (1 - peak_sec / action_duration_sec) / (
        1 - 2 * peak_sec / action_duration_sec)
    a = 2 * tau / action_duration_sec
    S = 1.0 / (1 - a + (1 + a) * math.exp(-action_duration_sec / tau))
    return 1 - S * (1 - a) * (
        (pow(t_sec, 2) / (tau * action_duration_sec * (1 - a))
         - t_sec / tau - 1) * math.exp(-t_sec / tau) + 1)


# Precompute a fine-grained lookup table for performance.
_PD_TABLE_DT_SEC = 30   # 30-sec grid
_PD_TABLE_N = int((6 * 3600 + 600) / _PD_TABLE_DT_SEC) + 1
_PD_TABLE = np.array([percent_effect_remaining(i * _PD_TABLE_DT_SEC) for i in range(_PD_TABLE_N)])


def percent_remaining_lookup(t_sec_arr: np.ndarray) -> np.ndarray:
    """Vectorized lookup of percent_effect_remaining for an array of times."""
    idx = np.clip((t_sec_arr / _PD_TABLE_DT_SEC).astype(int), 0, _PD_TABLE_N - 1)
    return _PD_TABLE[idx]


# ─── Insulin-effect bookkeeping ───────────────────────────────────────────

@dataclass
class DoseHistory:
    """Per-dose record (units, time). Stores ISF used at dose time for
    glucose-effect computation."""
    times_sec: np.ndarray   # seconds since reference epoch
    volumes_U: np.ndarray   # units delivered at each
    isf_at_dose: np.ndarray  # ISF (mg/dL/U) at dose time


    def add(self, t_sec: float, volume_U: float, isf: float) -> "DoseHistory":
        return DoseHistory(
            times_sec=np.append(self.times_sec, t_sec),
            volumes_U=np.append(self.volumes_U, volume_U),
            isf_at_dose=np.append(self.isf_at_dose, isf),
        )

    def empty(cls) -> "DoseHistory":
        return DoseHistory(
            times_sec=np.array([], dtype=np.float64),
            volumes_U=np.array([], dtype=np.float64),
            isf_at_dose=np.array([], dtype=np.float64),
        )


def insulin_effect_at(dose_history: DoseHistory, t_sec: float) -> float:
    """Cumulative insulin effect on BG at time t_sec (negative mg/dL contribution).

    For each past dose i with volume V_i at time t_i and ISF_i:
       contribution at t = V_i × ISF_i × (1 - percentRemaining(t - t_i))
    Insulin lowers BG so the cumulative effect is signed POSITIVE here for
    "amount BG was driven down by insulin". To compose with BG, SUBTRACT.
    """
    mask = dose_history.times_sec <= t_sec
    if not np.any(mask):
        return 0.0
    delta = t_sec - dose_history.times_sec[mask]
    pd = percent_remaining_lookup(delta)
    delivered = 1.0 - pd
    return float(np.sum(dose_history.volumes_U[mask] * dose_history.isf_at_dose[mask] * delivered))


def v_insulin_at(dose_history: DoseHistory, t_sec: float, dt_sec: float = 300) -> float:
    """Rate of change of insulin effect at time t (mg/dL/min).

    Computed as a finite difference over [t-dt/2, t+dt/2] of insulin_effect_at,
    converted to per-minute. Returns NEGATIVE values during insulin action
    (BG lowering rate).
    """
    e1 = insulin_effect_at(dose_history, t_sec - dt_sec / 2)
    e2 = insulin_effect_at(dose_history, t_sec + dt_sec / 2)
    # mg/dL change per dt_sec = (e2 - e1). Convert to mg/dL/min and negate
    # so insulin (which drives BG down) contributes negatively to v_BG.
    return -(e2 - e1) / (dt_sec / 60.0)


def insulin_effect_remaining(dose_history: DoseHistory, t_now_sec: float,
                              horizon_sec: float) -> float:
    """Predicted ADDITIONAL drop in BG due to currently-on-board insulin
    over the next horizon_sec, beyond what has already happened by t_now.

    Returned as a POSITIVE number (BG drop magnitude).
    """
    now_eff = insulin_effect_at(dose_history, t_now_sec)
    future_eff = insulin_effect_at(dose_history, t_now_sec + horizon_sec)
    return future_eff - now_eff


def iob_at(dose_history: DoseHistory, t_sec: float) -> float:
    """Active insulin (U) remaining at t."""
    mask = dose_history.times_sec <= t_sec
    if not np.any(mask):
        return 0.0
    delta = t_sec - dose_history.times_sec[mask]
    pd = percent_remaining_lookup(delta)
    return float(np.sum(dose_history.volumes_U[mask] * pd))


# ─── Simplified Loop dose recommendation ──────────────────────────────────

@dataclass
class LoopConfig:
    """Knobs for the simplified Loop dose recommendation."""
    target_bg: float = 100.0          # mg/dL target
    suspend_threshold: float = 75.0    # below this → 0 U/hr
    application_factor: float = 0.4    # fraction of correction to actually deliver per step
    forecast_horizon_sec: float = 60 * 60   # +60min prediction horizon
    max_basal_uhr: float = 4.0
    max_bolus_u: float = 8.0
    eval_step_sec: float = 5 * 60       # 5 min step
    isf_multiplier: float = 1.0        # rule's ISF modifier applied here


def simple_loop_recommend(
    bg_current: float,
    dose_history: DoseHistory,
    t_sec: float,
    scheduled_basal_uhr: float,
    isf_mgdl_per_u: float,
    config: LoopConfig,
) -> float:
    """Return the recommended Δ-U (above scheduled basal) over the next eval_step.

    Steps:
      1. If BG_current ≤ suspend_threshold, deliver 0 U/hr (Δ = -scheduled × dt).
      2. Forecast BG at +forecast_horizon using insulin_effect_remaining.
      3. If predicted BG ≤ target: deliver scheduled basal (Δ = 0).
      4. Else: correction = (predicted - target) / ISF × app_factor.
      5. Cap by max_basal (positive direction).
    """
    dt_h = config.eval_step_sec / 3600.0

    # 1. Suspend logic
    if bg_current <= config.suspend_threshold:
        return -scheduled_basal_uhr * dt_h

    # 2. Effective ISF (rule mechanism here)
    isf_eff = isf_mgdl_per_u * config.isf_multiplier

    # 3. Forecast: BG_current minus additional insulin effect over horizon
    drop_remaining = insulin_effect_remaining(
        dose_history, t_sec, config.forecast_horizon_sec
    )
    bg_predicted = bg_current - drop_remaining

    # 4. Correction
    if bg_predicted <= config.target_bg:
        return 0.0
    correction = (bg_predicted - config.target_bg) / isf_eff * config.application_factor

    # 5. Cap. Note: correction is U over the EVAL STEP, not per hour.
    #    Convert max_basal_uhr × dt_h to step-cap.
    step_cap = config.max_basal_uhr * dt_h
    return float(min(correction, step_cap))


# ─── Closed-loop ICE simulation ───────────────────────────────────────────

@dataclass
class SimResult:
    """Per-step trace of the ICE-based closed-loop sim."""
    times: pd.DatetimeIndex
    actual_bg: np.ndarray
    counter_bg: np.ndarray
    candidate_dose: np.ndarray
    actual_delta: np.ndarray
    ice_signal: np.ndarray
    isf_used: np.ndarray
    isf_multiplier_used: np.ndarray


def closed_loop_ice_sim(
    actual_bg: pd.Series,            # observed BG, indexed at 5-min cadence
    actual_doses: DoseHistory,       # observed full dose history (boluses + temp-above-scheduled)
    actual_v_insulin: np.ndarray,    # v_insulin from actual doses at each timepoint (mg/dL/min)
    ice: np.ndarray,                 # ICE = v_cgm - v_insulin (mg/dL/min), aligned to actual_bg.index
    isf_schedule: Callable[[float], float],   # ISF (mg/dL/U) lookup by t_sec
    scheduled_basal: Callable[[float], float], # basal rate (U/hr) lookup by t_sec
    score_lookup: Optional[Callable[[float], float]] = None,  # rule score [0,1] by t_sec; None = baseline
    low_anchor: float = 0.5,
    high_anchor: float = 1.0,
    max_boost: float = 0.5,
    down_low_anchor: float = 0.0,
    max_boost_down: float = 0.3,
    config: Optional[LoopConfig] = None,
) -> SimResult:
    """Run a closed-loop simulation with ICE-based counterfactual integration.

    For each 5-min step the candidate:
      • Sees counter_bg history up to current step (NOT actual BG after t_0)
      • Computes a dose recommendation via simple_loop_recommend with the rule's
        ISF multiplier applied (from score_lookup)
      • Δdose vs ACTUAL delivered is added/subtracted to running candidate dose
        history
      • counter_bg(t+dt) = counter_bg(t) + dt × (ice(t) + v_insulin_candidate(t))
    """
    if config is None:
        config = LoopConfig()

    t0_pd = actual_bg.index[0]
    times = actual_bg.index
    n = len(times)
    actual_arr = actual_bg.to_numpy(dtype=float)

    # Convert times to seconds since epoch for math
    if times.tz is not None:
        epoch = pd.Timestamp("1970-01-01", tz="UTC")
    else:
        epoch = pd.Timestamp("1970-01-01")
    t_sec_arr = (times.tz_convert("UTC").to_numpy().astype("datetime64[s]").view("int64").astype(np.float64)
                 if times.tz is not None else
                 times.to_numpy().astype("datetime64[s]").view("int64").astype(np.float64))

    # Candidate dose history — starts as actual doses
    cand = DoseHistory(
        times_sec=actual_doses.times_sec.copy(),
        volumes_U=actual_doses.volumes_U.copy(),
        isf_at_dose=actual_doses.isf_at_dose.copy(),
    )
    # We accumulate virtual doses (Δ above what actual already had) as needed.

    counter_bg = actual_arr.copy()
    candidate_dose_arr = np.zeros(n)
    actual_delta_arr = np.zeros(n)
    isf_used_arr = np.zeros(n)
    isf_mult_arr = np.ones(n)

    # Need actual deltaU (above scheduled) at each step to compare candidate against.
    # Approximation: take actual insulin delivered in [t, t+dt] above scheduled basal.
    # Compute outside this function via caller, but we can derive a rough version
    # from actual_v_insulin × dt × <isf-1>… better to pass in.
    # For now we approximate actual_delta = 0 (rate matches scheduled exactly) and let
    # the candidate's Δ vs that be the candidate's "extra".
    # NOTE: This is a known simplification. To improve later, pass `actual_delta_uhr`
    # per step from the caller (computed from doses cache).

    # Iterate
    for i in range(n - 1):
        t_sec = t_sec_arr[i]
        dt_sec = float(t_sec_arr[i + 1] - t_sec)
        dt_h = dt_sec / 3600.0

        bg_now = counter_bg[i]
        isf = isf_schedule(t_sec)
        sched = scheduled_basal(t_sec)
        isf_used_arr[i] = isf

        # Score → ISF multiplier
        if score_lookup is None:
            mult = 1.0
        else:
            s = score_lookup(t_sec)
            mult = _smooth_boost_factor(s, low_anchor, high_anchor, max_boost,
                                        down_low_anchor, max_boost_down)
        isf_mult_arr[i] = mult

        # Build a step config that applies the multiplier
        step_cfg = LoopConfig(
            target_bg=config.target_bg,
            suspend_threshold=config.suspend_threshold,
            application_factor=config.application_factor,
            forecast_horizon_sec=config.forecast_horizon_sec,
            max_basal_uhr=config.max_basal_uhr,
            max_bolus_u=config.max_bolus_u,
            eval_step_sec=dt_sec,
            isf_multiplier=mult,
        )

        candidate_step_u = simple_loop_recommend(
            bg_current=bg_now,
            dose_history=cand,
            t_sec=t_sec,
            scheduled_basal_uhr=sched,
            isf_mgdl_per_u=isf,
            config=step_cfg,
        )
        candidate_dose_arr[i] = candidate_step_u

        # Append virtual dose representing the candidate's correction over [t, t+dt]
        # The actual dose history already contains scheduled basal effect; we're
        # adding the candidate's delta. Net candidate insulin in [t, t+dt] is
        # scheduled_basal × dt + candidate_step_u. The candidate's TOTAL effect
        # at future times is sum over (cand doses) of v × pd. By appending only
        # `candidate_step_u` (not the scheduled portion), we encode it as the
        # ADDITIONAL insulin beyond scheduled.
        # That means cand's dose history represents the CANDIDATE-MINUS-ACTUAL
        # insulin path if actual_v_insulin is the actual scheduled-plus-corrections
        # full path.
        if abs(candidate_step_u) > 1e-9:
            cand = cand.add(t_sec=t_sec + dt_sec / 2.0,
                            volume_U=candidate_step_u,
                            isf=isf)

        # Compute v_insulin_candidate at this step
        v_ins_cand = v_insulin_at(cand, t_sec, dt_sec=dt_sec)

        # Advance counter_BG: dt × (ICE + v_ins_candidate). Note v_ins_candidate
        # is mg/dL/min and ICE is also mg/dL/min, so multiply by dt in minutes.
        dt_min = dt_sec / 60.0
        counter_bg[i + 1] = bg_now + dt_min * (ice[i] + v_ins_cand)

    return SimResult(
        times=times,
        actual_bg=actual_arr,
        counter_bg=counter_bg,
        candidate_dose=candidate_dose_arr,
        actual_delta=actual_delta_arr,
        ice_signal=ice,
        isf_used=isf_used_arr,
        isf_multiplier_used=isf_mult_arr,
    )


def _smooth_boost_factor(score: Optional[float],
                         low_anchor: float, high_anchor: float, max_boost: float,
                         down_low_anchor: float, max_boost_down: float) -> float:
    """Same mapping as the Swift sim's smoothBoostFactor."""
    if score is None or (isinstance(score, float) and math.isnan(score)):
        return 1.0
    if score >= low_anchor:
        span = high_anchor - low_anchor
        if span <= 1e-9:
            return 1.0
        clipped = max(0.0, min(1.0, (score - low_anchor) / span))
        return 1.0 + max_boost * clipped
    down_span = low_anchor - down_low_anchor
    if max_boost_down <= 1e-9 or down_span <= 1e-9:
        return 1.0
    aggression = max(0.0, min(1.0, (low_anchor - score) / down_span))
    return 1.0 - max_boost_down * aggression


# ─── Outcome metrics ──────────────────────────────────────────────────────

def outcome_metrics(bg_arr: np.ndarray) -> dict:
    bg = bg_arr[~np.isnan(bg_arr)]
    if bg.size == 0:
        return {"n": 0}
    return {
        "n": int(bg.size),
        "mean_bg": float(bg.mean()),
        "tir_70_180": float(((bg >= 70) & (bg < 180)).mean()),
        "t_below_70": float((bg < 70).mean()),
        "t_below_54": float((bg < 54).mean()),
        "t_above_180": float((bg >= 180).mean()),
        "t_above_250": float((bg >= 250).mean()),
    }
