"""Additional feature families for the static-evaluator exploration.

Complements `state_features.py` (28-feature baseline) and
`ice_isf_features.py` (148 ICE/ISF variants). The families here intentionally
do NOT rely on carb entries — this dataset has poor carb data; the design
target is a system that works without carb entry.

Families:

1. **Meal signature (CGM-only inferred)** — proxies for "did we just have a meal
   spike?" derived from BG/v_cgm/ICE patterns alone.

2. **Dose-event timing** — uses bolus data which is reliable. Both "all boluses"
   variants (includes SMB) and "manual only" variants (likely meal/correction).

3. **BG volatility** — stdev / range over trailing windows. Distinguishes calm
   vs chaotic recent traces.

4. **Cyclic time encoding** — sin/cos pairs for hour, day-of-week, and a 28-day
   cycle (motivated by the periodicity analysis in
   `runs/2026-05-15-insulin-hole/`).

All causal (no look-ahead).
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# 1. Meal-signature features (CGM-only inferred)
# ─────────────────────────────────────────────────────────────────────────────

def meal_signature_features(
    explore: pd.DataFrame,
    *,
    meal_search_window_min: int = 180,  # 3h
    excursion_window_min: int = 240,    # 4h
    velocity_window_min: int = 60,
    ice_rising_window_min: int = 60,
    ratio_window_min: int = 60,
    v_insulin_floor: float = 0.01,
) -> pd.DataFrame:
    """Carb-entry-free meal proxies.

    Features:
      mins_since_bg_peak_3h         — minutes since the BG max in last 3h
                                       (proxy for time-since-meal-spike)
      bg_velocity_max_60m           — max v_cgm in last 60 min
                                       (peak BG-rise speed: meal-like surges)
      bg_excursion_240m             — (max BG in last 4h) − current BG
                                       (size of the recent peak relative to now)
      bg_excursion_above_now_240m   — (max BG in last 4h) − current BG, clipped ≥ 0
                                       (cleaner version of excursion)
      ice_rising_60m_frac           — fraction of last 60 min where d(rolling_ice)/dt > 0
                                       (sustained-rising ICE = unannounced glucose source)
      vcgm_vins_ratio_p90_60m       — P90 of (v_cgm / max(|v_insulin|, floor)) over last 60 min
                                       (rises Loop's model can't explain)
      vcgm_vins_ratio_max_60m       — max of the same ratio (more extreme tail)
    """
    if "bg_smoothed" not in explore.columns:
        raise KeyError("explore must have 'bg_smoothed'")
    out = pd.DataFrame(index=explore.index)
    bg = explore["bg_smoothed"].astype(float)
    v_cgm = explore["v_cgm"].astype(float) if "v_cgm" in explore.columns else None
    rolling_ice = explore["rolling_ice"].astype(float) if "rolling_ice" in explore.columns else None
    v_ins_col = "v_insulin_mgdl_min" if "v_insulin_mgdl_min" in explore.columns else (
        "v_insulin" if "v_insulin" in explore.columns else None)
    v_ins = explore[v_ins_col].astype(float) if v_ins_col else None

    # mins_since_bg_peak_3h: find argmax of BG in trailing window, compute time since.
    idx_ns = explore.index.view("int64")
    win_ns = int(meal_search_window_min * 60 * 1_000_000_000)
    bg_arr = bg.to_numpy()
    n = len(bg_arr)
    mins_since = np.full(n, np.nan)
    lo = 0
    for i in range(n):
        t = idx_ns[i]
        while lo < i and idx_ns[lo] < t - win_ns:
            lo += 1
        sl_start = lo
        sl_end = i + 1
        if sl_end - sl_start < 3:
            continue
        # argmax in the trailing slice
        rel_argmax = int(np.argmax(bg_arr[sl_start:sl_end]))
        peak_ns = idx_ns[sl_start + rel_argmax]
        mins_since[i] = (t - peak_ns) / 60 / 1_000_000_000
    out["mins_since_bg_peak_3h"] = mins_since

    # bg_velocity_max_60m
    if v_cgm is not None:
        out["bg_velocity_max_60m"] = v_cgm.rolling(f"{velocity_window_min}min",
                                                    min_periods=3).max()

    # bg_excursion_240m: (max BG in last 4h) − current BG
    bg_max_4h = bg.rolling(f"{excursion_window_min}min", min_periods=3).max()
    excursion = bg_max_4h - bg
    out["bg_excursion_240m"] = excursion
    out["bg_excursion_above_now_240m"] = excursion.clip(lower=0)

    # ice_rising_60m_frac: fraction of samples in last hour where rolling_ice was rising
    if rolling_ice is not None:
        ice_delta = rolling_ice.diff()
        # Boolean: ICE increased from previous sample.
        is_rising = (ice_delta > 0).astype(float)
        out["ice_rising_60m_frac"] = is_rising.rolling(f"{ice_rising_window_min}min",
                                                       min_periods=3).mean()
        # Also strong-rising threshold: ICE accel > 0.05 mg/dL/min²
        is_strong_rising = (ice_delta > 0.05).astype(float)
        out["ice_strong_rising_60m_frac"] = is_strong_rising.rolling(
            f"{ice_rising_window_min}min", min_periods=3).mean()

    # vcgm_vins_ratio_p90_60m: 90th percentile of v_cgm / max(|v_insulin|, floor)
    if v_cgm is not None and v_ins is not None:
        denom = v_ins.abs().clip(lower=v_insulin_floor)
        ratio = v_cgm / denom
        # Clip extreme values for stable rolling percentiles
        ratio_clipped = ratio.clip(lower=-100, upper=100)
        roll = ratio_clipped.rolling(f"{ratio_window_min}min", min_periods=6)
        out["vcgm_vins_ratio_p90_60m"] = roll.quantile(0.90)
        out["vcgm_vins_ratio_max_60m"] = roll.max()
        out["vcgm_vins_ratio_p75_60m"] = roll.quantile(0.75)

    return out


# ─────────────────────────────────────────────────────────────────────────────
# 2. Dose-event timing features
# ─────────────────────────────────────────────────────────────────────────────

def dose_timing_features(
    explore: pd.DataFrame,
    doses: pd.DataFrame,
    *,
    manual_bolus_threshold_u: float = 1.0,
) -> pd.DataFrame:
    """Bolus-timing features. Two flavors per concept:

      • _any  — uses ALL boluses (includes Loop SMB, fires every ~5 min)
      • _manual — uses only manual boluses (rare, large, likely meal/correction)
      • _meal — uses any bolus with volume ≥ ``manual_bolus_threshold_u``
                (heuristic capture of meal-sized doses including manual + large auto)

    Features:
      mins_since_last_bolus_{any,manual,meal}
      bolus_count_2h_{any,manual,meal}
      bolus_count_4h_{any,manual,meal}
      bolus_sum_2h_{any,manual,meal}      (total U in trailing window)
      last_bolus_magnitude_{any,manual,meal}
    """
    if doses is None or doses.empty:
        return pd.DataFrame(index=explore.index)

    if "delivery_type" in doses.columns:
        boluses_all = doses[doses["delivery_type"] == "bolus"].copy()
    else:
        return pd.DataFrame(index=explore.index)

    if boluses_all.empty:
        return pd.DataFrame(index=explore.index)

    # Build the three bolus filters
    bolus_sets = {
        "any": boluses_all,
        "manual": boluses_all[~boluses_all["automatic"]] if "automatic" in boluses_all.columns else boluses_all.iloc[:0],
        "meal":   boluses_all[boluses_all["volume"] >= manual_bolus_threshold_u],
    }

    target_ns = explore.index.view("int64")
    n = len(target_ns)
    out = pd.DataFrame(index=explore.index)

    for label, b in bolus_sets.items():
        if b.empty:
            out[f"mins_since_last_bolus_{label}"] = np.nan
            out[f"bolus_count_2h_{label}"] = 0.0
            out[f"bolus_count_4h_{label}"] = 0.0
            out[f"bolus_sum_2h_{label}"] = 0.0
            out[f"last_bolus_magnitude_{label}"] = np.nan
            continue

        b_ns = b.index.view("int64")
        b_vol = b["volume"].to_numpy()

        mins_since = np.full(n, np.nan)
        last_mag = np.full(n, np.nan)
        cnt_2h = np.zeros(n)
        cnt_4h = np.zeros(n)
        sum_2h = np.zeros(n)

        win_2h_ns = 2 * 3600 * 1_000_000_000
        win_4h_ns = 4 * 3600 * 1_000_000_000

        for i in range(n):
            t = target_ns[i]
            # Last bolus at or before t
            pos = np.searchsorted(b_ns, t, side="right") - 1
            if pos >= 0:
                mins_since[i] = (t - b_ns[pos]) / 60 / 1_000_000_000
                last_mag[i] = b_vol[pos]
            # Counts and sums in trailing windows
            lo_2h = np.searchsorted(b_ns, t - win_2h_ns, side="left")
            hi = np.searchsorted(b_ns, t, side="right")
            cnt_2h[i] = hi - lo_2h
            sum_2h[i] = float(b_vol[lo_2h:hi].sum())
            lo_4h = np.searchsorted(b_ns, t - win_4h_ns, side="left")
            cnt_4h[i] = hi - lo_4h

        out[f"mins_since_last_bolus_{label}"] = mins_since
        out[f"bolus_count_2h_{label}"] = cnt_2h
        out[f"bolus_count_4h_{label}"] = cnt_4h
        out[f"bolus_sum_2h_{label}"] = sum_2h
        out[f"last_bolus_magnitude_{label}"] = last_mag

    return out


# ─────────────────────────────────────────────────────────────────────────────
# 3. BG volatility features
# ─────────────────────────────────────────────────────────────────────────────

def bg_volatility_features(
    explore: pd.DataFrame,
    *,
    windows_min=(60, 240, 720),  # 1h, 4h, 12h
) -> pd.DataFrame:
    """BG volatility features over trailing windows.

    Features:
      bg_std_<W>            — stdev of bg over trailing window
      bg_range_<W>          — max bg − min bg over trailing window
      bg_mean_<W>           — trailing mean (useful as a control / context)
    """
    if "bg_smoothed" not in explore.columns:
        raise KeyError("explore must have 'bg_smoothed'")
    bg = explore["bg_smoothed"].astype(float)

    def _label(mins: int) -> str:
        if mins % 60 == 0:
            h = mins // 60
            if h == 24: return "24h"
            return f"{h}h"
        return f"{mins}m"

    out = pd.DataFrame(index=explore.index)
    for m in windows_min:
        win = f"{m}min"
        lbl = _label(m)
        roll = bg.rolling(win, min_periods=3)
        out[f"bg_std_{lbl}"]   = roll.std()
        out[f"bg_range_{lbl}"] = roll.max() - roll.min()
        out[f"bg_mean_{lbl}"]  = roll.mean()
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 4. Cyclic time encoding
# ─────────────────────────────────────────────────────────────────────────────

def cyclic_time_features(
    explore: pd.DataFrame,
    *,
    period_28d_anchor: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """Sin/cos encodings of cyclic time variables, avoiding 23→0 discontinuity.

    Features:
      hour_sin, hour_cos              — 24h cycle
      dow_sin, dow_cos                — 7-day cycle
      day_of_28d_sin, day_of_28d_cos  — 28-day cycle
                                          (motivated by excess periodicity finding)

    ``period_28d_anchor``: a reference timestamp used as day 0 of the 28d cycle.
    Defaults to the first sample's date.
    """
    out = pd.DataFrame(index=explore.index)
    idx = explore.index

    hour = idx.hour + idx.minute / 60.0
    out["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    out["hour_cos"] = np.cos(2 * np.pi * hour / 24)

    dow = idx.dayofweek + (hour / 24.0)
    out["dow_sin"] = np.sin(2 * np.pi * dow / 7)
    out["dow_cos"] = np.cos(2 * np.pi * dow / 7)

    if period_28d_anchor is None:
        period_28d_anchor = idx.min().normalize()
    else:
        period_28d_anchor = pd.Timestamp(period_28d_anchor)
        if period_28d_anchor.tzinfo is None and idx.tzinfo is not None:
            period_28d_anchor = period_28d_anchor.tz_localize(idx.tzinfo)
    days_since = (idx - period_28d_anchor).total_seconds() / 86400.0
    day_of_28d = np.mod(days_since, 28.0)
    out["day_of_28d_sin"] = np.sin(2 * np.pi * day_of_28d / 28)
    out["day_of_28d_cos"] = np.cos(2 * np.pi * day_of_28d / 28)

    return out


def build_all_extra_features(
    explore: pd.DataFrame,
    doses: Optional[pd.DataFrame] = None,
    *,
    period_28d_anchor: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """Build all four extra families and concatenate."""
    parts = [
        meal_signature_features(explore),
        bg_volatility_features(explore),
        cyclic_time_features(explore, period_28d_anchor=period_28d_anchor),
    ]
    if doses is not None:
        parts.append(dose_timing_features(explore, doses))
    return pd.concat(parts, axis=1)
