"""Loop's exact IOB model in Python.

Mirrors `LoopAlgorithm/Sources/LoopAlgorithm/Insulin/ExponentialInsulinModel.swift`
and the netBasalUnits convention from `InsulinMath.swift`.

Key facts that make this match Loop's reported IOB (devicestatus loop.iob.iob):
  1. The exponential model has a `delay` (10 min for rapidActingAdult): IOB
     stays at 100% during the delay, then decays via the exponential formula.
  2. For temp basals, Loop counts the NET delivery vs scheduled basal
     (`netBasalUnits = (actual_rate - scheduled_rate) * duration`). When Loop
     suspends, that yields a NEGATIVE dose. Using absolute deliveries gives
     a systematically inflated IOB (~2 U high on rloop). Use the netBasal
     approach to match Loop.
  3. Boluses count as their full amount (no scheduled offset).
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from typing import Optional


# ── Loop's rapidActingAdult preset ──────────────────────────────────────────
@dataclass(frozen=True)
class InsulinModel:
    action_duration_min: float  # exponential decay duration, after delay
    peak_min: float
    delay_min: float

    @property
    def effect_duration_min(self) -> float:
        return self.action_duration_min + self.delay_min


RAPID_ACTING_ADULT = InsulinModel(action_duration_min=360.0, peak_min=75.0, delay_min=10.0)
RAPID_ACTING_CHILD = InsulinModel(action_duration_min=360.0, peak_min=65.0, delay_min=10.0)
FIASP              = InsulinModel(action_duration_min=360.0, peak_min=55.0, delay_min=10.0)
LYUMJEV            = InsulinModel(action_duration_min=360.0, peak_min=55.0, delay_min=10.0)
AFREZZA            = InsulinModel(action_duration_min=300.0, peak_min=29.0, delay_min=10.0)


def percent_effect_remaining(elapsed_min: np.ndarray,
                              model: InsulinModel = RAPID_ACTING_ADULT) -> np.ndarray:
    """Loop's ExponentialInsulinModel.percentEffectRemaining(at:), vectorized.

    Returns the fraction of one unit still pending at `elapsed_min` after delivery.
    Matches Swift exactly: 1.0 during delay, exponential decay after, 0 past DIA.
    """
    elapsed_min = np.asarray(elapsed_min, dtype=float)
    out = np.zeros_like(elapsed_min)
    t_after_delay = elapsed_min - model.delay_min
    full = (elapsed_min >= 0) & (t_after_delay <= 0)
    out[full] = 1.0
    decay = (t_after_delay > 0) & (t_after_delay < model.action_duration_min)
    if not decay.any():
        return out
    t = t_after_delay[decay]
    AD = model.action_duration_min
    tau = model.peak_min * (1 - model.peak_min / AD) / (1 - 2 * model.peak_min / AD)
    a = 2 * tau / AD
    S = 1.0 / (1 - a + (1 + a) * np.exp(-AD / tau))
    val = 1 - S * (1 - a) * ((t * t / (tau * AD * (1 - a)) - t / tau - 1) * np.exp(-t / tau) + 1)
    out[decay] = np.clip(val, 0, 1)
    return out


def _continuous_delivery_percent_remaining(time_min: np.ndarray,
                                            duration_min: float,
                                            model: InsulinModel,
                                            delta_min: float = 5.0) -> np.ndarray:
    """Loop's continuousDeliveryInsulinOnBoard fraction for a temp basal of
    `duration_min`, evaluated at offsets `time_min` from the basal's startDate.

    Splits the basal into `delta_min` segments (matches Swift `delta`) and sums
    each segment's contribution. Returns fraction of the total basal still
    pending at each `time_min` value.
    """
    time_min = np.asarray(time_min, dtype=float)
    out = np.zeros_like(time_min, dtype=float)
    if duration_min <= 0:
        return out
    # Loop's repeat loop condition:
    #   doseDate += delta
    # while doseDate <= min(floor((time + delay)/delta)*delta, doseDuration)
    # We rebuild this per time index using vectorization-friendly approach.
    # For efficiency: iterate segments (typically 6-12 per temp basal at 30-60 min).
    for i, t in enumerate(time_min):
        if t <= 0:
            continue
        upper = min(np.floor((t + model.delay_min) / delta_min) * delta_min, duration_min)
        if upper < 0:
            continue
        # doseDate goes 0, delta, 2*delta, ... <= upper
        n_segments = int(upper / delta_min) + 1
        if n_segments <= 0:
            continue
        dose_dates = np.arange(n_segments, dtype=float) * delta_min
        segs = np.minimum(dose_dates + delta_min, duration_min) - dose_dates
        segs = np.clip(segs, 0, None) / duration_min
        pcts = percent_effect_remaining(t - dose_dates, model=model)
        out[i] = float(np.sum(segs * pcts))
    return out


@dataclass
class _DoseEvent:
    """A normalized dose for IOB convolution.

    For boluses: start==end, net_units = bolus volume.
    For temp basal segments: net_units = (rate - sched_rate) × duration_hr.
    """
    start: pd.Timestamp
    end: pd.Timestamp
    net_units: float


def _build_dose_events(doses: pd.DataFrame, therapy_cache_path: str,
                       tz: str = "America/Chicago") -> list[_DoseEvent]:
    """Decompose a real-pump doses frame into Loop-style net-unit dose events.

    Boluses contribute their full volume; temp basals contribute
    (actual_rate - scheduled_rate) × duration. Scheduled basal periods (no
    temp set) contribute 0 (they're treated as neutral / baseline).
    """
    from .glucose import scheduled_basal_at
    events: list[_DoseEvent] = []
    if doses.empty:
        return events
    # Boluses
    boluses = doses[doses["delivery_type"] != "basal"]
    for ts, b in boluses.iterrows():
        end_ts = b["endDate"] if pd.notna(b["endDate"]) else ts
        events.append(_DoseEvent(start=ts, end=end_ts, net_units=float(b["volume"])))
    # Temp basals (where rate_uhr is set — not NaN)
    basals = doses[(doses["delivery_type"] == "basal") & doses["rate_uhr"].notna()]
    if len(basals) == 0:
        return events
    # Lookup scheduled basal at each basal start
    basal_starts = pd.DatetimeIndex(basals.index)
    scheds = scheduled_basal_at(basal_starts, therapy_cache_path, tz=tz)
    for (ts, b), sched_rate in zip(basals.iterrows(), scheds.values):
        end_ts = b["endDate"]
        if pd.isna(end_ts):
            continue
        dur_hr = (end_ts - ts).total_seconds() / 3600.0
        if dur_hr <= 0:
            continue
        net_units = (float(b["rate_uhr"]) - float(sched_rate)) * dur_hr
        if abs(net_units) < 1e-9:
            continue
        events.append(_DoseEvent(start=ts, end=end_ts, net_units=net_units))
    events.sort(key=lambda e: e.start)
    return events


def loop_iob(doses: pd.DataFrame,
             therapy_cache_path: str,
             grid: pd.DatetimeIndex,
             *,
             model: InsulinModel = RAPID_ACTING_ADULT,
             delta_min: float = 5.0,
             tz: str = "America/Chicago") -> pd.Series:
    """Loop's IOB at each timestamp in `grid`, using the net-basal convention.

    Boluses convolved as point-dose events; temp basals as continuous-delivery
    events with net_units = (actual_rate - scheduled_rate) × duration.

    `doses` must include all dose history within `grid.min() - effect_duration`
    through `grid.max()`. Use a 6.5h lookback to be safe.
    """
    events = _build_dose_events(doses, therapy_cache_path, tz=tz)
    if not events:
        return pd.Series(0.0, index=grid, name="iob_U")
    grid_secs = grid.astype("int64").to_numpy() / 1e9
    iob = np.zeros(len(grid), dtype=float)
    for ev in events:
        start_sec = pd.Timestamp(ev.start).timestamp()
        end_sec = pd.Timestamp(ev.end).timestamp()
        duration_sec = end_sec - start_sec
        if duration_sec <= 60:
            # Point dose (bolus or near-zero-duration basal)
            elapsed_min = (grid_secs - start_sec) / 60.0
            iob += ev.net_units * percent_effect_remaining(elapsed_min, model=model)
        else:
            # Continuous delivery basal: use Loop's repeat-loop convolution
            elapsed_min = (grid_secs - start_sec) / 60.0
            duration_min = duration_sec / 60.0
            frac = _continuous_delivery_percent_remaining(
                elapsed_min, duration_min, model=model, delta_min=delta_min)
            iob += ev.net_units * frac
    return pd.Series(iob, index=grid, name="iob_U")
