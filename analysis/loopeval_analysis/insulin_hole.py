"""Insulin-shaped-hole analysis — non-simulation evaluator.

DESIGN NOTE: bounded vs unbounded framing
─────────────────────────────────────────

Both `insulin_hole` and `insulin_excess` (and their two-horizons variants)
are **unbounded** by physical deliverability constraints:

  • `insulin_hole(t)` = "BG-room-to-spare" expressed as additional U IF that
    insulin were delivered. Doesn't check against max_bolus or max_basal_rate.
    For aggressive boost rules you'd cap the proposed Δ to therapy.max_bolus
    externally.

  • `insulin_excess(t)` = "BG-effect-that-needed-to-be-cancelled" expressed
    in U. Does NOT cap at the actual insulin delivered in the step at t.
    If actual delivery at t was 0.05 U but the metric returns 0.5 U, that
    means 0.45 U of dose-reduction was theoretically needed but couldn't
    be achieved via dose-cut alone — it would need to come from another
    intervention (glucagon, rescue carbs, etc.) or upstream from an
    earlier dose.

The unbounded framing is the right "opportunity" view: it answers "what
BG-effect needed to be removed?" rather than "what could a dose-cut at t
have done?". Useful for algorithm-design as an upper bound, but be aware
that excess > actual_delivery_at_t means dose-reduction alone can't fully
solve it.

For each timestamp t on a real BG trace, ``insulin_hole`` computes the
maximum additional insulin Δ that could have been delivered at t WITHOUT
pushing BG below a safety floor at any future point in [t, t + DIA].

This is purely a function of the observed BG trace and the insulin model.
No closed-loop simulation, no recomputed-baseline assumptions, no feedback
artifacts. The cost: it ignores how user/algorithm would have responded to
the changed BG trajectory. For small/local changes that's a reasonable
approximation; for large structural changes, less so.

Math
----

A dose of Δ units delivered at time t causes a BG drop of
   Δ × ISF(t) × pd_delivered(τ)
at time t+τ, where pd_delivered(τ) = 1 - percent_effect_remaining(τ) is the
fraction of total effect that has acted by τ.

For BG to remain ≥ floor at every τ ∈ [0, DIA]:
   BG_actual(t+τ) - Δ × ISF × pd_delivered(τ) ≥ floor
   ⇔ Δ ≤ (BG_actual(t+τ) - floor) / (ISF × pd_delivered(τ))

Taking the min over all τ:
   max_safe_Δ(t) = min_{τ ∈ [0,DIA]} (BG_actual(t+τ) - floor) / (ISF × pd_delivered(τ))

Floored at 0 (can't undeliver dose).
"""
from __future__ import annotations

import math
from typing import Callable, Optional

import numpy as np
import pandas as pd

from .ice_sim import percent_remaining_lookup, _PD_TABLE, _PD_TABLE_DT_SEC, _PD_TABLE_N


# ─── Loop-style time-varying target (matches LoopAlgorithm DoseMath) ──────

def loop_target_at_tau(
    tau_sec: float,
    *,
    dia_sec: float,
    suspend_threshold: float,
    correction_range_avg: float,
    inflection_pct: float = 0.5,
) -> float:
    """Time-varying BG target as used by LoopAlgorithm's dose computation.

    Matches `targetGlucoseValue` in
    `LoopAlgorithm/Sources/LoopAlgorithm/Insulin/DoseMath.swift`:

      - For τ in [0, inflection_pct · DIA]: target = suspend_threshold
      - For τ in [inflection_pct · DIA, DIA]: target rises linearly from
        suspend_threshold to correction_range_avg
      - For τ ≥ DIA: target = correction_range_avg

    With default `inflection_pct=0.5` and `dia_hours=6`, this is:
      - 0 to 3h: target = suspend threshold (e.g. 78 mg/dL on user1)
      - 3h to 6h: target rises linearly to correction range mid (e.g. ~112)

    LoopAlgorithm uses this as the value the correction-dose calculation
    aims to "bring predicted BG down to". Equivalently for the insulin-hole
    framing: it is the time-varying lower bound the candidate Δ must not
    push BG below at any τ.
    """
    pct = tau_sec / dia_sec
    if pct <= inflection_pct:
        return suspend_threshold
    if pct >= 1.0:
        return correction_range_avg
    slope = (correction_range_avg - suspend_threshold) / (1.0 - inflection_pct)
    return suspend_threshold + slope * (pct - inflection_pct)


def loop_target_array(
    taus_sec: np.ndarray,
    *,
    dia_sec: float,
    suspend_threshold: float,
    correction_range_avg: float,
    inflection_pct: float = 0.5,
) -> np.ndarray:
    """Vectorized form of loop_target_at_tau over a τ grid."""
    pct = taus_sec / dia_sec
    target = np.full_like(taus_sec, suspend_threshold, dtype=float)
    rising_mask = (pct > inflection_pct) & (pct < 1.0)
    if np.any(rising_mask):
        slope = (correction_range_avg - suspend_threshold) / (1.0 - inflection_pct)
        target[rising_mask] = suspend_threshold + slope * (pct[rising_mask] - inflection_pct)
    target[pct >= 1.0] = correction_range_avg
    return target


def _resolve_target_array(
    taus_sec: np.ndarray,
    *,
    dia_sec: float,
    floor: Optional[float],
    suspend_threshold: Optional[float],
    correction_range_avg: Optional[float],
) -> np.ndarray:
    """Resolve which target convention to use:
      - If both `suspend_threshold` and `correction_range_avg` are given:
        use Loop-style time-varying target.
      - Otherwise: use flat `floor` for all τ (legacy behavior).
    """
    if suspend_threshold is not None and correction_range_avg is not None:
        return loop_target_array(
            taus_sec, dia_sec=dia_sec,
            suspend_threshold=suspend_threshold,
            correction_range_avg=correction_range_avg,
        )
    if floor is None:
        raise ValueError("Must specify either `floor` or both `suspend_threshold` "
                         "and `correction_range_avg`")
    return np.full_like(taus_sec, float(floor))


# ─── Core insulin-hole computation ────────────────────────────────────────

def insulin_hole(
    bg: pd.Series,
    *,
    isf_schedule: Optional[Callable[[pd.Timestamp], float]] = None,
    isf_constant: Optional[float] = None,
    floor: Optional[float] = 80.0,
    suspend_threshold: Optional[float] = None,
    correction_range_avg: Optional[float] = None,
    dia_hours: float = 6.0,
    step_sec: float = 300.0,
    min_future_samples: int = 50,
) -> pd.DataFrame:
    """Compute the insulin-shaped-hole time series.

    Parameters
    ----------
    bg : pd.Series
        BG (mg/dL), indexed by tz-aware datetime, expected at ~5-min cadence.
    isf_schedule : callable(timestamp) → float, optional
        ISF (mg/dL/U) at each timestamp. If None, use ``isf_constant``.
    isf_constant : float, optional
        Constant ISF in mg/dL/U.
    floor : float, optional
        Flat safety-floor BG threshold (mg/dL). Used only when
        ``suspend_threshold`` and ``correction_range_avg`` are NOT both given.
        Default 80.
    suspend_threshold, correction_range_avg : float, optional
        When BOTH are provided, the floor becomes time-varying matching
        LoopAlgorithm's `targetGlucoseValue` (see ``loop_target_at_tau``):
        suspend_threshold for τ in [0, DIA/2], rising linearly to
        correction_range_avg over [DIA/2, DIA]. Typical user1 values:
        suspend_threshold=78, correction_range_avg=112.5.
    dia_hours : float
        Insulin duration of action (h). Default 6.
    step_sec : float
        Expected interval between bg samples (sec). Default 300.

    Returns
    -------
    pd.DataFrame with columns:
        max_safe_dU       : maximum safe additional Δ-U at each t
        binding_tau_min   : τ in minutes at which the constraint is binding
        binding_bg        : BG at the binding τ
        binding_target    : target value at the binding τ (= floor if flat)
        min_future_bg     : min BG in the lookahead window
        n_future_samples  : how many BG samples were in the lookahead window
    """
    if bg.empty:
        return pd.DataFrame()

    bg = bg.sort_index().astype(float)
    times = bg.index
    bg_arr = bg.to_numpy()
    n = len(bg_arr)

    horizon_sec = dia_hours * 3600.0
    horizon_steps = int(horizon_sec / step_sec) + 1

    # Pre-compute pd_delivered(τ) for τ = 0, step, 2*step, ..., horizon_steps*step
    taus_sec = np.arange(horizon_steps + 1) * step_sec
    pd_remaining = percent_remaining_lookup(taus_sec)
    pd_delivered = 1.0 - pd_remaining   # fraction of dose effect delivered at τ

    # Per-τ target (Loop time-varying if both suspend_threshold and
    # correction_range_avg given; else flat `floor`)
    target_arr = _resolve_target_array(
        taus_sec, dia_sec=horizon_sec,
        floor=floor,
        suspend_threshold=suspend_threshold,
        correction_range_avg=correction_range_avg,
    )

    # For τ=0, pd_delivered=0 → effect_per_unit=0 → constraint is "BG(t) ≥ target(0)"
    # We handle this by skipping τ=0 in the min computation (no effect yet, no
    # constraint imposed by the dose itself).

    # ISF lookup. If callable, vectorize cheaply by caching per-row.
    if isf_schedule is not None:
        isf_at = np.array([float(isf_schedule(t)) for t in times])
    elif isf_constant is not None:
        isf_at = np.full(n, float(isf_constant))
    else:
        raise ValueError("Must specify isf_schedule or isf_constant")

    max_safe = np.zeros(n)
    binding_tau = np.full(n, np.nan)
    binding_bg_val = np.full(n, np.nan)
    binding_target_val = np.full(n, np.nan)
    min_future = np.full(n, np.nan)
    n_future = np.zeros(n, dtype=np.int64)

    for i in range(n):
        # Future window: [i, i + horizon_steps] inclusive, clipped to n
        end = min(i + horizon_steps + 1, n)
        win = bg_arr[i:end]
        n_future[i] = len(win)
        if len(win) <= 1 or len(win) < min_future_samples:
            # Insufficient lookahead — can't compute a meaningful constraint
            max_safe[i] = np.nan
            continue
        # min over future BG → naive lower bound only matters at peak-effect τ
        # We need min over τ of (BG[τ] - target(τ)) / (ISF * pd_delivered[τ])
        # Skip τ=0 (pd_delivered=0)
        win_taus = pd_delivered[1:len(win)]   # length = len(win)-1
        win_bg_future = win[1:]                # length = len(win)-1
        win_target = target_arr[1:len(win)]    # length = len(win)-1
        headroom = win_bg_future - win_target  # may be negative at some τ
        if isf_at[i] <= 0:
            max_safe[i] = np.nan
            continue
        effect_per_unit = isf_at[i] * win_taus
        # Where effect_per_unit > 0:
        with np.errstate(divide="ignore", invalid="ignore"):
            implied_max = np.where(effect_per_unit > 1e-9,
                                    headroom / effect_per_unit,
                                    np.inf)
        # Clip headroom for already-below-target points: max_Δ = 0 (no room)
        already_low = win_bg_future < win_target
        implied_max[already_low] = 0.0
        idx_min = int(np.argmin(implied_max))
        max_safe[i] = max(0.0, implied_max[idx_min])
        binding_tau[i] = (idx_min + 1) * step_sec / 60.0   # +1 because we skipped τ=0
        binding_bg_val[i] = float(win_bg_future[idx_min])
        binding_target_val[i] = float(win_target[idx_min])
        min_future[i] = float(win_bg_future.min())

    return pd.DataFrame(
        {
            "max_safe_dU": max_safe,
            "binding_tau_min": binding_tau,
            "binding_bg": binding_bg_val,
            "binding_target": binding_target_val,
            "min_future_bg": min_future,
            "n_future_samples": n_future,
        },
        index=times,
    )


def insulin_hole_two_horizons(
    bg: pd.Series,
    future_corrections: pd.Series,
    *,
    isf_constant: Optional[float] = None,
    isf_schedule: Optional[Callable[[pd.Timestamp], float]] = None,
    floor: Optional[float] = 80.0,
    suspend_threshold: Optional[float] = None,
    correction_range_avg: Optional[float] = None,
    dia_hours: float = 6.0,
    step_sec: float = 300.0,
    min_future_samples: int = 50,
) -> pd.DataFrame:
    """Compute BOTH `hole_with_future` and `hole_no_future` in one pass.

    `future_corrections` is a per-step (or per-event) Series of additional
    U delivered above scheduled basal — boluses + above-scheduled temp basal
    contributions. The same series that's emitted by
    ``build_actual_delivery_trace.py`` works.

    The "no future" variant cancels all corrections occurring strictly AFTER t
    within the lookahead window. Scheduled basal still happens; only the user/
    Loop's discretionary corrections are removed.

    Returns a DataFrame with columns:
        hole_with_future  : max safe additional U at t given future corrections do happen
        hole_no_future    : max safe additional U at t if future corrections are cancelled
        substitutable_U   : hole_no_future − hole_with_future (≥ 0; how much of future
                            corrections in window could be moved up to t)
        binding_tau_with  : τ at which hole_with_future binds
        binding_tau_no    : τ at which hole_no_future binds
        n_future_corr     : count of correction events in window
        future_corr_sum_U : total U of corrections in window
    """
    if bg.empty:
        return pd.DataFrame()

    bg = bg.sort_index().astype(float)
    times = bg.index
    bg_arr = bg.to_numpy()
    n = len(bg_arr)

    horizon_sec = dia_hours * 3600.0
    horizon_steps = int(horizon_sec / step_sec) + 1
    taus_sec = np.arange(horizon_steps + 1) * step_sec
    pd_remaining = percent_remaining_lookup(taus_sec)
    pd_delivered = 1.0 - pd_remaining

    # Per-τ target (Loop time-varying if both params given, else flat `floor`)
    target_arr = _resolve_target_array(
        taus_sec, dia_sec=horizon_sec,
        floor=floor,
        suspend_threshold=suspend_threshold,
        correction_range_avg=correction_range_avg,
    )

    if isf_schedule is not None:
        isf_at = np.array([float(isf_schedule(t)) for t in times])
    elif isf_constant is not None:
        isf_at = np.full(n, float(isf_constant))
    else:
        raise ValueError("Must specify isf_schedule or isf_constant")

    # Align future_corrections onto the bg index — both should be at ~5-min cadence
    fc = future_corrections.reindex(times, method="nearest",
                                     tolerance=pd.Timedelta(seconds=step_sec / 2)).fillna(0.0)
    fc_arr = fc.to_numpy(dtype=float)

    hole_w = np.zeros(n)
    hole_no = np.zeros(n)
    bind_tau_w = np.full(n, np.nan)
    bind_tau_no = np.full(n, np.nan)
    n_future_corr = np.zeros(n, dtype=np.int64)
    future_corr_sum = np.zeros(n)

    for i in range(n):
        end = min(i + horizon_steps + 1, n)
        win = bg_arr[i:end]
        n_win = len(win)
        if n_win <= 1 or n_win < min_future_samples:
            hole_w[i] = np.nan
            hole_no[i] = np.nan
            continue
        if isf_at[i] <= 0:
            hole_w[i] = np.nan
            hole_no[i] = np.nan
            continue
        win_bg_future = win[1:]
        win_taus = pd_delivered[1:n_win]
        win_target = target_arr[1:n_win]
        effect_per_unit = isf_at[i] * win_taus

        # Bg_lift_no_future(τ) = sum over correction events j with j > i and j <= i+k
        # of fc_j × isf_j × (1 - pd_remaining(τ_k - (j-i) × step_sec))
        # where τ_k corresponds to k = 1, 2, …, n_win-1
        bg_lift = np.zeros(n_win - 1)
        n_corr = 0
        sum_corr = 0.0
        # Iterate over future correction events in window (j = i+1 to end-1)
        for j in range(i + 1, end):
            v = fc_arr[j]
            if abs(v) < 1e-9:
                continue
            n_corr += 1
            sum_corr += v
            # For each τ_k after the correction time:
            # k_start = j - i (first τ where correction has been delivered)
            k_start = j - i   # i+k_start = j
            # For k in [k_start, n_win-1], dose at j has been ago by (k - k_start) × step_sec
            for k in range(k_start, n_win):
                # δ = (k - k_start) × step_sec since correction
                δ_idx = k - k_start
                # pd_delivered at δ
                # δ in seconds = δ_idx × step_sec
                # Use the precomputed pd_delivered table (taus_sec[δ_idx])
                if δ_idx < len(pd_delivered):
                    pd_d = pd_delivered[δ_idx]
                else:
                    pd_d = 1.0
                # bg_lift index is k - 1 (since win_bg_future = win[1:])
                bg_lift_idx = k - 1
                if bg_lift_idx >= 0 and bg_lift_idx < len(bg_lift):
                    bg_lift[bg_lift_idx] += v * isf_at[j] * pd_d

        n_future_corr[i] = n_corr
        future_corr_sum[i] = sum_corr

        # WITH-future hole: bg_future already includes future corrections
        with np.errstate(divide="ignore", invalid="ignore"):
            implied_w = np.where(effect_per_unit > 1e-9,
                                  (win_bg_future - win_target) / effect_per_unit,
                                  np.inf)
        implied_w[win_bg_future < win_target] = 0.0
        idx_w = int(np.argmin(implied_w))
        hole_w[i] = max(0.0, float(implied_w[idx_w]))
        bind_tau_w[i] = (idx_w + 1) * step_sec / 60.0

        # NO-future hole: cancel future corrections (add back their effect)
        bg_no = win_bg_future + bg_lift
        with np.errstate(divide="ignore", invalid="ignore"):
            implied_no = np.where(effect_per_unit > 1e-9,
                                   (bg_no - win_target) / effect_per_unit,
                                   np.inf)
        implied_no[bg_no < win_target] = 0.0
        idx_no = int(np.argmin(implied_no))
        hole_no[i] = max(0.0, float(implied_no[idx_no]))
        bind_tau_no[i] = (idx_no + 1) * step_sec / 60.0

    return pd.DataFrame(
        {
            "hole_with_future": hole_w,
            "hole_no_future": hole_no,
            "substitutable_U": np.maximum(0.0, hole_no - hole_w),
            "binding_tau_with": bind_tau_w,
            "binding_tau_no": bind_tau_no,
            "n_future_corr": n_future_corr,
            "future_corr_sum_U": future_corr_sum,
        },
        index=times,
    )


def insulin_excess_two_horizons(
    bg: pd.Series,
    future_corrections: pd.Series,
    *,
    isf_constant: Optional[float] = None,
    isf_schedule: Optional[Callable[[pd.Timestamp], float]] = None,
    low_threshold: Optional[float] = 70.0,
    suspend_threshold: Optional[float] = None,
    correction_range_avg: Optional[float] = None,
    dia_hours: float = 6.0,
    step_sec: float = 300.0,
    min_future_samples: int = 50,
    min_pd_delivered: float = 0.10,
) -> pd.DataFrame:
    """Symmetric counterpart to ``insulin_hole_two_horizons`` for the excess side.

    For each t, compute the required-reduction at t under both:
      • ``excess_with_future``: required cut at t given future Loop corrections
        happen anyway (= original insulin_excess()).
      • ``excess_no_future``: required cut at t if all future corrections in
        (t, t+DIA] are CANCELLED. If a low would have NOT happened absent the
        future corrections, excess_no_future = 0 — the low was the future
        corrections' fault, not t-dose's.

    The difference `attributable_to_future_U` = excess_with_future − excess_no_future
    is the portion of the low-prevention burden that belongs to future doses
    rather than to t.

    Returns DataFrame with columns:
        excess_with_future        : current insulin_excess() value
        excess_no_future          : version with future corrections cancelled
        attributable_to_future_U  : with - no  (≥ 0)
        binding_tau_with          : τ at which excess_with_future binds
        binding_tau_no            : τ at which excess_no_future binds
        n_future_corr             : count of correction events in window
        future_corr_sum_U         : total U of corrections in window
        any_future_low_with       : 1 if any future bg < threshold (with future)
        any_future_low_no         : 1 if any future bg < threshold (no future)
    """
    if bg.empty:
        return pd.DataFrame()

    bg = bg.sort_index().astype(float)
    times = bg.index
    bg_arr = bg.to_numpy()
    n = len(bg_arr)

    horizon_sec = dia_hours * 3600.0
    horizon_steps = int(horizon_sec / step_sec) + 1
    taus_sec = np.arange(horizon_steps + 1) * step_sec
    pd_remaining = percent_remaining_lookup(taus_sec)
    pd_delivered = 1.0 - pd_remaining

    # Per-τ threshold (Loop time-varying if both params given, else flat low_threshold)
    threshold_arr = _resolve_target_array(
        taus_sec, dia_sec=horizon_sec,
        floor=low_threshold,
        suspend_threshold=suspend_threshold,
        correction_range_avg=correction_range_avg,
    )

    if isf_schedule is not None:
        isf_at = np.array([float(isf_schedule(t)) for t in times])
    elif isf_constant is not None:
        isf_at = np.full(n, float(isf_constant))
    else:
        raise ValueError("Must specify isf_schedule or isf_constant")

    fc = future_corrections.reindex(times, method="nearest",
                                     tolerance=pd.Timedelta(seconds=step_sec / 2)).fillna(0.0)
    fc_arr = fc.to_numpy(dtype=float)

    excess_w = np.zeros(n)
    excess_no = np.zeros(n)
    bind_tau_w = np.full(n, np.nan)
    bind_tau_no = np.full(n, np.nan)
    n_future_corr = np.zeros(n, dtype=np.int64)
    future_corr_sum = np.zeros(n)
    any_low_w = np.zeros(n, dtype=np.int64)
    any_low_no = np.zeros(n, dtype=np.int64)

    for i in range(n):
        end = min(i + horizon_steps + 1, n)
        win = bg_arr[i:end]
        n_win = len(win)
        if n_win <= 1 or n_win < min_future_samples:
            excess_w[i] = np.nan
            excess_no[i] = np.nan
            continue
        if isf_at[i] <= 0:
            excess_w[i] = np.nan
            excess_no[i] = np.nan
            continue
        win_bg_future = win[1:]
        win_taus = pd_delivered[1:n_win]
        win_threshold = threshold_arr[1:n_win]
        effect_per_unit = isf_at[i] * win_taus

        # Compute bg_lift from future corrections (same logic as the hole version)
        bg_lift = np.zeros(n_win - 1)
        n_corr = 0
        sum_corr = 0.0
        for j in range(i + 1, end):
            v = fc_arr[j]
            if abs(v) < 1e-9:
                continue
            n_corr += 1
            sum_corr += v
            k_start = j - i
            for k in range(k_start, n_win):
                δ_idx = k - k_start
                if δ_idx < len(pd_delivered):
                    pd_d = pd_delivered[δ_idx]
                else:
                    pd_d = 1.0
                bg_lift_idx = k - 1
                if 0 <= bg_lift_idx < len(bg_lift):
                    bg_lift[bg_lift_idx] += v * isf_at[j] * pd_d

        n_future_corr[i] = n_corr
        future_corr_sum[i] = sum_corr

        # WITH-future: use observed BG
        deficit_w = win_threshold - win_bg_future
        attribute_w = (deficit_w > 0) & (win_taus >= min_pd_delivered)
        with np.errstate(divide="ignore", invalid="ignore"):
            req_w = np.where(attribute_w & (effect_per_unit > 1e-9),
                              deficit_w / effect_per_unit, 0.0)
        any_low_w[i] = int((win_bg_future < win_threshold).any())
        if req_w.max() > 0:
            idx_w = int(np.argmax(req_w))
            excess_w[i] = float(req_w[idx_w])
            bind_tau_w[i] = (idx_w + 1) * step_sec / 60.0

        # NO-future: add bg_lift to remove future corrections
        bg_no = win_bg_future + bg_lift
        deficit_no = win_threshold - bg_no
        attribute_no = (deficit_no > 0) & (win_taus >= min_pd_delivered)
        with np.errstate(divide="ignore", invalid="ignore"):
            req_no = np.where(attribute_no & (effect_per_unit > 1e-9),
                               deficit_no / effect_per_unit, 0.0)
        any_low_no[i] = int((bg_no < win_threshold).any())
        if req_no.max() > 0:
            idx_no = int(np.argmax(req_no))
            excess_no[i] = float(req_no[idx_no])
            bind_tau_no[i] = (idx_no + 1) * step_sec / 60.0

    # Signed delta: positive = future +corrections CAUSED part of the low
    #               (cancelling them removes some excess at t)
    # Negative = future SUSPENDING was preventing deeper lows
    #               (cancelling them increases required excess at t)
    signed_delta = excess_w - excess_no
    return pd.DataFrame(
        {
            "excess_with_future": excess_w,
            "excess_no_future": excess_no,
            "future_corr_blame_U": np.maximum(0.0, signed_delta),    # future +cor caused this low; cancellation would have removed it
            "future_suspending_saved_U": np.maximum(0.0, -signed_delta),  # future suspending was preventing deeper lows
            "signed_delta_U": signed_delta,
            "binding_tau_with": bind_tau_w,
            "binding_tau_no": bind_tau_no,
            "n_future_corr": n_future_corr,
            "future_corr_sum_U": future_corr_sum,
            "any_future_low_with": any_low_w,
            "any_future_low_no": any_low_no,
        },
        index=times,
    )


def insulin_excess_fair_attribution(
    bg: pd.Series,
    total_deliveries_per_step: pd.Series,
    *,
    isf_constant: Optional[float] = None,
    isf_schedule: Optional[Callable[[pd.Timestamp], float]] = None,
    low_threshold: Optional[float] = 70.0,
    suspend_threshold: Optional[float] = None,
    correction_range_avg: Optional[float] = None,
    dia_hours: float = 6.0,
    step_sec: float = 300.0,
    min_future_samples: int = 50,
    min_pd_delivered: float = 0.10,
) -> pd.DataFrame:
    """Distributed-blame variant of insulin_excess.

    For each future low at T_low, distribute the BG-cancellation burden
    PROPORTIONALLY across all doses contributing to the IOB at T_low. Each
    dose's "fair share" required reduction is:

        f_event = (low_threshold - bg(T_low)) / total_insulin_effect_at(T_low)
        fair_required(t for this event) = f_event × V_t

    where ``total_insulin_effect_at(T_low) = Σ over doses d with t_d ∈ [T_low - DIA, T_low]
    of V_d × ISF(t_d) × pd_delivered(T_low - t_d)``.

    ``total_deliveries_per_step`` should be the TOTAL insulin delivered in each
    step (scheduled basal × step_h + any boluses + above-scheduled corrections).
    Algorithm cuts can reduce this all the way to 0 via temp-basal, so it's
    the natural upper limit on what a dose-cut at t can achieve.

    Per-step `fair_required_U(t)` is the max over future low events of
    `f_event × V_t`. Capped at V_t (can't undeliver more than was delivered).

    Returns DataFrame with columns:
        fair_required_U        : f_event × V_t at binding event (capped at V_t)
        fair_unbounded_U       : f_event × V_t without the V_t cap
        actual_delivered_U     : V_t (this step's delivery above scheduled)
        unmet_gap_U            : max(0, fair_unbounded - V_t) — would need non-dose
        binding_tau_min        : τ at the binding low event
        binding_f              : f at the binding event (≥1 means t-dose alone insufficient)
        any_future_low         : 1 if any future bg < threshold within DIA
    """
    if bg.empty:
        return pd.DataFrame()

    bg = bg.sort_index().astype(float)
    times = bg.index
    bg_arr = bg.to_numpy()
    n = len(bg_arr)

    horizon_sec = dia_hours * 3600.0
    horizon_steps = int(horizon_sec / step_sec) + 1
    taus_sec = np.arange(horizon_steps + 1) * step_sec
    pd_remaining = percent_remaining_lookup(taus_sec)
    pd_delivered = 1.0 - pd_remaining

    # Per-τ threshold (Loop time-varying if both params given, else flat low_threshold)
    threshold_arr = _resolve_target_array(
        taus_sec, dia_sec=horizon_sec,
        floor=low_threshold,
        suspend_threshold=suspend_threshold,
        correction_range_avg=correction_range_avg,
    )

    if isf_schedule is not None:
        isf_at = np.array([float(isf_schedule(t)) for t in times])
    elif isf_constant is not None:
        isf_at = np.full(n, float(isf_constant))
    else:
        raise ValueError("Must specify isf_schedule or isf_constant")

    # Align delivery series — TOTAL delivery per step (basal × step_h + boluses)
    deliveries = total_deliveries_per_step.reindex(times, method="nearest",
                                                     tolerance=pd.Timedelta(seconds=step_sec / 2)).fillna(0.0)
    V = deliveries.to_numpy(dtype=float)

    # Precompute insulin_effect_at[i] = sum over doses j ≤ i of V[j] × ISF[j] × pd_delivered(i - j)
    insulin_effect = np.zeros(n)
    for i in range(n):
        start = max(0, i - horizon_steps)
        for j in range(start, i + 1):
            v = V[j]
            if abs(v) < 1e-9:
                continue
            delta_idx = i - j
            if delta_idx < len(pd_delivered):
                pd_d = pd_delivered[delta_idx]
            else:
                pd_d = 1.0
            insulin_effect[i] += v * isf_at[j] * pd_d

    # For each t, look forward for lows, compute fair attribution
    fair_capped = np.zeros(n)
    fair_unbounded = np.zeros(n)
    actual_delivered = V.copy()
    binding_tau = np.full(n, np.nan)
    binding_f = np.full(n, np.nan)
    any_low = np.zeros(n, dtype=np.int64)

    for i in range(n):
        end = min(i + horizon_steps + 1, n)
        n_win = end - i
        if n_win <= 1 or n_win < min_future_samples:
            fair_capped[i] = np.nan
            fair_unbounded[i] = np.nan
            continue
        v_t = V[i]
        if v_t <= 0:
            # No delivery at t → no fair-share blame attaches to t
            continue
        max_unbounded = 0.0
        max_capped = 0.0
        best_tau = np.nan
        best_f = np.nan
        for k in range(1, n_win):
            bg_future = bg_arr[i + k]
            thresh_k = threshold_arr[k] if k < len(threshold_arr) else threshold_arr[-1]
            if bg_future >= thresh_k:
                continue
            # τ index k, but skip if pd_delivered too low to attribute to t
            if k < len(pd_delivered) and pd_delivered[k] < min_pd_delivered:
                continue
            any_low[i] = 1
            total_eff = insulin_effect[i + k]
            if total_eff <= 1e-9:
                continue
            f_event = (thresh_k - bg_future) / total_eff
            required_unbounded = f_event * v_t
            required_capped = min(required_unbounded, v_t)
            if required_unbounded > max_unbounded:
                max_unbounded = required_unbounded
                max_capped = required_capped
                best_tau = k * step_sec / 60.0
                best_f = f_event
        fair_capped[i] = max_capped
        fair_unbounded[i] = max_unbounded
        binding_tau[i] = best_tau
        binding_f[i] = best_f

    return pd.DataFrame(
        {
            "fair_required_U": fair_capped,
            "fair_unbounded_U": fair_unbounded,
            "actual_delivered_U": actual_delivered,
            "unmet_gap_U": np.maximum(0.0, fair_unbounded - actual_delivered),
            "binding_tau_min": binding_tau,
            "binding_f": binding_f,
            "any_future_low": any_low,
        },
        index=times,
    )


def insulin_excess(
    bg: pd.Series,
    *,
    isf_schedule: Optional[Callable[[pd.Timestamp], float]] = None,
    isf_constant: Optional[float] = None,
    low_threshold: Optional[float] = 70.0,
    suspend_threshold: Optional[float] = None,
    correction_range_avg: Optional[float] = None,
    dia_hours: float = 6.0,
    step_sec: float = 300.0,
    min_future_samples: int = 50,
    min_pd_delivered: float = 0.10,
) -> pd.DataFrame:
    """Symmetric counterpart to ``insulin_hole``. For each timestamp t, compute
    the MINIMUM dose reduction at t that would have prevented BG from going
    below ``low_threshold`` at any future τ ∈ [0, DIA].

    Math
    ----
    A dose of Δ units at t reduces BG at t+τ by Δ × ISF × pd_delivered(τ).
    If actual_BG(t+τ) < threshold, we'd need to REDUCE the dose at t by:
       required_reduction(τ) = (threshold - actual_BG(t+τ)) / (ISF × pd_delivered(τ))

    The MAXIMUM such requirement over the future window is the minimum
    reduction needed at t to prevent ALL future lows:
       required_reduction(t) = max_{τ : bg(t+τ) < threshold} required_reduction(τ)

    Caveats
    -------
    • UNBOUNDED: this metric is NOT capped at the actual insulin deliverable
      at t. If required_reduction > (actual delivered in step at t), the
      "excess" represents BG-effect that needed to be cancelled but couldn't
      be by dose-cut alone — would need glucagon, rescue carbs, or upstream
      action on earlier doses. See the module docstring for the design choice.
    • Rescue-carb confound: when BG actually went below threshold, the user
      likely took rescue carbs that bounced BG back up. The observed
      ``bg(t+τ)`` is therefore HIGHER than it would have been without the
      rescue, so the required_reduction we compute is a LOWER BOUND on the
      true required reduction. Treat the output as a lower bound.
    • Attribution: a low at t+τ could be caused by any insulin in [t-DIA, t+τ],
      not just the dose at t. This metric attributes responsibility to time t
      proportional to ``pd_delivered(τ)`` (the fraction of dose-at-t's effect
      that has been delivered by τ). Effectively: "what if I'd reduced dose
      at t by ΔR — how much smaller would the low have been?"
    • Non-insulin lows (exercise crashes, basal mismatch, sensor noise) are
      lumped in here. Filter the input or interpret cautiously.

    Returns
    -------
    pd.DataFrame with columns:
        required_reduction_dU : min Δ-U to REMOVE at t to prevent all future lows
        binding_tau_min       : τ at which the constraint is tightest
        binding_bg            : BG at the binding τ (will be < threshold)
        min_future_bg         : min BG in the lookahead window
        n_future_samples      : how many BG samples were in the lookahead window
        any_future_low        : 1 if any future bg < threshold within DIA
    """
    if bg.empty:
        return pd.DataFrame()

    bg = bg.sort_index().astype(float)
    times = bg.index
    bg_arr = bg.to_numpy()
    n = len(bg_arr)

    horizon_sec = dia_hours * 3600.0
    horizon_steps = int(horizon_sec / step_sec) + 1
    taus_sec = np.arange(horizon_steps + 1) * step_sec
    pd_remaining = percent_remaining_lookup(taus_sec)
    pd_delivered = 1.0 - pd_remaining

    # Per-τ threshold (Loop time-varying if both params given, else flat low_threshold)
    threshold_arr = _resolve_target_array(
        taus_sec, dia_sec=horizon_sec,
        floor=low_threshold,
        suspend_threshold=suspend_threshold,
        correction_range_avg=correction_range_avg,
    )

    if isf_schedule is not None:
        isf_at = np.array([float(isf_schedule(t)) for t in times])
    elif isf_constant is not None:
        isf_at = np.full(n, float(isf_constant))
    else:
        raise ValueError("Must specify isf_schedule or isf_constant")

    required = np.zeros(n)
    binding_tau = np.full(n, np.nan)
    binding_bg_val = np.full(n, np.nan)
    binding_threshold_val = np.full(n, np.nan)
    min_future = np.full(n, np.nan)
    n_future = np.zeros(n, dtype=np.int64)
    any_future_low = np.zeros(n, dtype=np.int64)

    for i in range(n):
        end = min(i + horizon_steps + 1, n)
        win = bg_arr[i:end]
        n_future[i] = len(win)
        if len(win) <= 1 or len(win) < min_future_samples:
            required[i] = np.nan
            continue

        win_bg_future = win[1:]
        win_taus = pd_delivered[1:len(win)]
        win_threshold = threshold_arr[1:len(win)]
        deficit = win_threshold - win_bg_future  # positive where bg < threshold(τ)
        # Where deficit > 0 AND pd_delivered > 0, compute required reduction
        if isf_at[i] <= 0:
            required[i] = np.nan
            continue
        effect_per_unit = isf_at[i] * win_taus
        # Physical filter: only attribute a low at τ to dose-at-t if the dose
        # has had time to materially act. Below min_pd_delivered, the dose's
        # contribution at τ is too small to attribute the low — the low must
        # have been caused by other earlier doses, not the one at t.
        attribute = (deficit > 0) & (win_taus >= min_pd_delivered)
        with np.errstate(divide="ignore", invalid="ignore"):
            req = np.where(
                attribute & (effect_per_unit > 1e-9),
                deficit / effect_per_unit,
                0.0,
            )
        min_future[i] = float(win_bg_future.min())
        any_future_low[i] = int((win_bg_future < win_threshold).any())
        if req.max() > 0:
            idx_max = int(np.argmax(req))
            required[i] = float(req[idx_max])
            binding_tau[i] = (idx_max + 1) * step_sec / 60.0
            binding_bg_val[i] = float(win_bg_future[idx_max])
            binding_threshold_val[i] = float(win_threshold[idx_max])
        else:
            required[i] = 0.0

    return pd.DataFrame(
        {
            "required_reduction_dU": required,
            "binding_tau_min": binding_tau,
            "binding_bg": binding_bg_val,
            "binding_threshold": binding_threshold_val,
            "min_future_bg": min_future,
            "n_future_samples": n_future,
            "any_future_low": any_future_low,
        },
        index=times,
    )


# ─── Scoring algorithm-proposed changes ───────────────────────────────────

def score_proposed_deltas(
    proposed_extra_U: pd.Series,
    hole: pd.DataFrame,
    *,
    tolerance: float = 0.0,
) -> pd.DataFrame:
    """Score a per-step series of proposed extra doses against the insulin hole.

    Parameters
    ----------
    proposed_extra_U : pd.Series
        Per-step proposed additional U (above baseline). Index should align
        with ``hole.index`` (will be reindexed with nearest-3min tolerance).
    hole : pd.DataFrame
        Output of insulin_hole().
    tolerance : float
        Allow proposed - max_safe up to this amount before flagging UNSAFE.

    Returns
    -------
    pd.DataFrame indexed at the hole index with columns:
        proposed_U   : proposed extra U at this step
        max_safe_dU  : hole value at this step
        margin_U     : max_safe_dU - proposed_U (positive = safe)
        flag         : SAFE / UNSAFE / NO_HOLE / NO_PROPOSAL
    """
    df = hole.copy()
    proposed = proposed_extra_U.reindex(df.index, method="nearest",
                                         tolerance=pd.Timedelta("3min"))
    df["proposed_U"] = proposed.fillna(0.0)
    df["margin_U"] = df["max_safe_dU"] - df["proposed_U"]

    flag = pd.Series("SAFE", index=df.index)
    flag[df["max_safe_dU"].isna()] = "NO_HOLE"
    flag[df["proposed_U"].abs() < 1e-9] = "NO_PROPOSAL"
    unsafe = (df["proposed_U"] > df["max_safe_dU"] + tolerance) & flag.eq("SAFE")
    flag[unsafe] = "UNSAFE"
    df["flag"] = flag
    return df


# ─── Aggregate stats ──────────────────────────────────────────────────────

def hole_aggregate_stats(hole: pd.DataFrame, bg: pd.Series) -> dict:
    """Quick summary of where the holes are and how big."""
    bg_aligned = bg.reindex(hole.index, method="nearest", tolerance=pd.Timedelta("3min"))
    hole = hole.copy()
    hole["bg"] = bg_aligned
    valid = hole["max_safe_dU"].notna()
    h = hole.loc[valid].copy()

    if h.empty:
        return {"n": 0}

    out = {
        "n_steps": int(len(h)),
        "n_with_hole_gt_0": int((h["max_safe_dU"] > 0).sum()),
        "n_with_hole_eq_0": int((h["max_safe_dU"] == 0).sum()),
        "hole_mean_U":   float(h["max_safe_dU"].mean()),
        "hole_median_U": float(h["max_safe_dU"].median()),
        "hole_p90_U":    float(h["max_safe_dU"].quantile(0.90)),
        "hole_p99_U":    float(h["max_safe_dU"].quantile(0.99)),
        "hole_max_U":    float(h["max_safe_dU"].max()),
        "total_step_U":  float(h["max_safe_dU"].sum()),
        # by current BG bucket
    }
    # Per-BG-bucket stats
    h["bg_bin"] = pd.cut(h["bg"], bins=[0, 70, 100, 130, 160, 180, 220, 260, 999],
                          labels=["<70","70-100","100-130","130-160","160-180","180-220","220-260","≥260"])
    by_bg = h.groupby("bg_bin", observed=False)["max_safe_dU"].agg(["count","mean","median","max","sum"])
    out["by_bg_bucket"] = by_bg.to_dict()
    return out
