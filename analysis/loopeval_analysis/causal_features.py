"""Strict-causal CGM-derived features.

`bg_smoothed`, `v_cgm`, `ice`, `rolling_ice`, `local_isf`, and every trailing
aggregation built from them are LEAKY in the existing `isf_explore_1y.csv`,
because the Kalman smoother that produced `bg_smoothed` uses a forward Kalman
filter PLUS an RTS backward smoother — so the smoothed BG at time t is informed
by all future observations.

`v_insulin` and `iob` are causal (pure forward integration of dose
pharmacodynamics from dose history).

This module rebuilds CGM-derived features from RAW glucose (no smoothing) so
they're strict-causal — only use observations at or before each sample's
timestamp.

Strategy:
  • Raw BG resampled to the same 5-min grid as the explore CSV.
  • Strict-trailing 3-sample median for light noise reduction (causal).
  • Backward-difference velocities at 15m and 30m horizons.
  • Trailing-window aggregations using strict-trailing windows.

The output is meant to drop in alongside the IOB / dose / time features from
`state_features.py`. Drop the leaky columns from those panels first.
"""
from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd


# Columns from explore CSV / state_features.py that are LEAKY because they
# depend on bg_smoothed (which uses RTS backward smoother).
LEAKY_COLUMNS = frozenset({
    # Direct
    "bg", "bg_smoothed",
    "v_cgm",
    "ice", "rolling_ice",
    "local_isf",
    # Backward-looking lags (use bg_smoothed)
    "bg_30m_ago", "bg_60m_ago", "bg_120m_ago",
    "bg_delta_30m", "bg_delta_60m", "bg_delta_120m",
    # Trailing aggregations of v_cgm
    "v_cgm_30m_mean", "v_cgm_60m_mean",
    # Trailing aggregations of local_isf
    "topK_isf_60m", "topK_isf_240m",
    "botK_isf_60m", "botK_isf_240m",
})


def _resample_to_grid(raw_bg: pd.Series, grid_index: pd.DatetimeIndex,
                       max_gap: pd.Timedelta = pd.Timedelta("10min")) -> pd.Series:
    """Resample raw BG to the explore-CSV 5-min grid using nearest-prior, with
    a max-gap guard. Anything beyond max_gap returns NaN."""
    # Asof-like: at each grid time, pick the most recent raw BG sample with
    # timestamp <= grid time, dropping the value if gap > max_gap.
    raw_bg = raw_bg.dropna().sort_index()
    rs = raw_bg.reindex(grid_index, method="ffill", tolerance=max_gap)
    return rs


def causal_cgm_features(
    raw_glucose: pd.Series,
    target_index: pd.DatetimeIndex,
    *,
    v_insulin: Optional[pd.Series] = None,
    isf_scheduled: Optional[pd.Series] = None,
    short_diff_min: int = 15,
    long_diff_min: int = 30,
    smooth_window_samples: int = 3,
    windows_min: Iterable[int] = (30, 60, 120, 240),
) -> pd.DataFrame:
    """Build a strict-causal CGM-derived feature panel.

    Parameters
    ----------
    raw_glucose : pd.Series of raw BG values, indexed by timestamp (timezone-aware).
    target_index : the 5-min target grid (typically the explore CSV's index).
    v_insulin   : causal insulin-velocity, on `target_index`. If provided, ICE
                  and local-ISF causal features are computed.
    isf_scheduled : per-sample scheduled ISF on `target_index`. If provided
                    with `v_insulin`, local_isf_causal is computed.
    short_diff_min, long_diff_min : backward-difference horizons (minutes) for
                                     velocity. Default 15 and 30.
    smooth_window_samples : trailing-median window for light noise reduction.
                            Default 3 samples (≈15 min on 5-min grid).
    windows_min : trailing-aggregation windows for v_cgm and ICE features.

    Features (all start with `c_` for "causal"):

      c_bg                       — current causal-smoothed BG
      c_bg_<W>_ago               — causal-smoothed BG at trailing lag
      c_bg_delta_<W>             — bg(t) − bg(t-W)
      c_vcgm_15m, c_vcgm_30m     — backward-difference velocities
      c_vcgm_mean_<W>            — trailing mean of c_vcgm_15m
      c_vcgm_max_<W>             — trailing max
      c_vcgm_min_<W>             — trailing min
      c_ice_15m, c_ice_30m       — causal ICE = c_vcgm − v_insulin (if v_ins given)
      c_ice_mean_<W>, c_ice_p90_<W>, c_ice_strong_pos_<W>  — trailing summaries
      c_local_isf_15m            — isf_sched × c_vcgm_15m / v_insulin
      c_isf_p10_<W>, c_isf_p90_<W>  — trailing percentiles
      c_bg_excursion_<W>         — (max c_bg in W) − c_bg(t)
      c_bg_velocity_max_<W>      — max c_vcgm in trailing W
      c_mins_since_bg_peak_<W>   — minutes since trailing-W BG max

    Indexed on `target_index`.
    """
    out = pd.DataFrame(index=target_index)

    bg_grid = _resample_to_grid(raw_glucose, target_index)
    # Causal 3-sample trailing median (light noise reduction, strictly causal)
    bg_causal = bg_grid.rolling(smooth_window_samples, min_periods=1).median()
    out["c_bg"] = bg_causal

    # Backward-difference velocities (mg/dL/min)
    def _backward_velocity(bg: pd.Series, lag_min: int) -> pd.Series:
        bg_lag = bg.shift(lag_min // 5)  # 5-min grid spacing
        return (bg - bg_lag) / lag_min
    vcgm_15 = _backward_velocity(bg_causal, short_diff_min)
    vcgm_30 = _backward_velocity(bg_causal, long_diff_min)
    out[f"c_vcgm_{short_diff_min}m"] = vcgm_15
    out[f"c_vcgm_{long_diff_min}m"] = vcgm_30

    # BG lags + deltas (causal)
    for lag in (30, 60, 120):
        bg_lag = bg_causal.shift(lag // 5)
        out[f"c_bg_{lag}m_ago"] = bg_lag
        out[f"c_bg_delta_{lag}m"] = bg_causal - bg_lag

    # Trailing aggregations of v_cgm (using vcgm_15)
    def _label(mins: int) -> str:
        if mins % 60 == 0:
            h = mins // 60
            return "24h" if h == 24 else f"{h}h"
        return f"{mins}m"

    for m in windows_min:
        win = f"{m}min"
        lbl = _label(m)
        roll = vcgm_15.rolling(win, min_periods=3)
        out[f"c_vcgm_mean_{lbl}"] = roll.mean()
        out[f"c_vcgm_max_{lbl}"]  = roll.max()
        out[f"c_vcgm_min_{lbl}"]  = roll.min()

        roll_bg = bg_causal.rolling(win, min_periods=3)
        out[f"c_bg_max_{lbl}"]  = roll_bg.max()
        out[f"c_bg_excursion_{lbl}"] = roll_bg.max() - bg_causal
        # mins_since_bg_peak: scan trailing window for argmax position
        # Done lazily — only for windows up to 4h to keep cost reasonable.
        if m <= 240:
            # Build via rolling apply (slow but accurate)
            samples = m // 5
            arr = bg_causal.to_numpy()
            n = len(arr)
            mins_since = np.full(n, np.nan)
            for i in range(samples - 1, n):
                window = arr[i - samples + 1:i + 1]
                if np.all(np.isnan(window)): continue
                rel_argmax = int(np.nanargmax(window))
                # rel_argmax = 0 means peak was at oldest in window (samples-1 grid steps ago)
                # rel_argmax = samples-1 means peak is at t (now)
                mins_since[i] = (samples - 1 - rel_argmax) * 5
            out[f"c_mins_since_bg_peak_{lbl}"] = mins_since

    # ICE causal — needs v_insulin
    if v_insulin is not None:
        vi = v_insulin.reindex(target_index)
        ice_15 = vcgm_15 - vi
        ice_30 = vcgm_30 - vi
        out["c_ice_15m"] = ice_15
        out["c_ice_30m"] = ice_30

        for m in windows_min:
            win = f"{m}min"
            lbl = _label(m)
            roll = ice_15.rolling(win, min_periods=3)
            out[f"c_ice_mean_{lbl}"]   = roll.mean()
            out[f"c_ice_p90_{lbl}"]    = roll.quantile(0.90)
            out[f"c_ice_p75_{lbl}"]    = roll.quantile(0.75)
            out[f"c_ice_max_{lbl}"]    = roll.max()
            out[f"c_ice_strong_pos_{lbl}"] = (ice_15 > 1.0).astype(float).rolling(win, min_periods=3).mean()

        # ice anomaly vs 24h baseline
        out["c_ice_dev_from_baseline"] = ice_15 - ice_15.rolling("24h", min_periods=24).mean()

    # local_isf causal — needs both v_insulin and isf_scheduled
    if v_insulin is not None and isf_scheduled is not None:
        isf_s = isf_scheduled.reindex(target_index)
        vi = v_insulin.reindex(target_index)
        denom = vi.abs().clip(lower=0.01) * np.sign(vi).replace(0, 1)
        isf_local = isf_s * vcgm_15 / denom
        isf_local_clipped = isf_local.clip(lower=-400, upper=400)
        out["c_local_isf_15m"] = isf_local_clipped

        for m in (60, 120, 240):
            win = f"{m}min"
            lbl = _label(m)
            roll = isf_local_clipped.rolling(win, min_periods=6)
            out[f"c_isf_p10_{lbl}"] = roll.quantile(0.10)
            out[f"c_isf_p50_{lbl}"] = roll.quantile(0.50)
            out[f"c_isf_p90_{lbl}"] = roll.quantile(0.90)
            out[f"c_isf_iqr_{lbl}"] = roll.quantile(0.75) - roll.quantile(0.25)

    return out
