"""Extended ICE- and local-ISF-derived feature variants.

Goal: explore the signal space of features derived from
  ICE = v_cgm - v_insulin    (non-insulin BG drivers)
  local_isf = isf_scheduled * v_cgm / v_insulin   (per-sample ISF estimate)

We compute many statistic-by-window combinations so we can later compare
their univariate relationships to the insulin-hole / insulin-excess targets.

All features are CAUSAL — only use information at or before each sample's
timestamp.

Conventions:
  • ICE units: mg/dL/min (positive = unexplained-rise; negative = unexplained-fall)
  • local_isf units: mg/dL/U (LARGER = more sensitive; smaller/negative = blunt/meal-mode)
  • All trailing windows are right-closed on `t` (include the current sample).

A "robust" estimator filters by ICE quietness — only count moments where
|ice| < ice_quiet_threshold so the local_isf reading isn't dominated by a
non-insulin disturbance.
"""
from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd

# Default time frames to compute statistics over.
DEFAULT_WINDOWS_MIN = (30, 60, 120, 240, 480, 1440)  # 30m, 1h, 2h, 4h, 8h, 24h


def _label(mins: int) -> str:
    """Compact human label for window minutes (60 → '1h', 1440 → '24h')."""
    if mins % 60 == 0:
        h = mins // 60
        if h == 24:
            return "24h"
        return f"{h}h"
    return f"{mins}m"


def _rolling_pct_above(series: pd.Series, window: str, threshold: float) -> pd.Series:
    """Fraction of values in trailing time-window that are > threshold."""
    return (series > threshold).rolling(window).mean()


def _rolling_pct_below(series: pd.Series, window: str, threshold: float) -> pd.Series:
    """Fraction of values in trailing time-window that are < threshold."""
    return (series < threshold).rolling(window).mean()


def _isf_clip(local_isf: pd.Series, lo: float = -400.0, hi: float = 400.0) -> pd.Series:
    """Clip insanely-large local_isf magnitudes that arise when v_insulin ≈ 0.
    These distort min/max and percentiles; clipping is safer than dropping for
    rolling statistics.
    """
    return local_isf.clip(lower=lo, upper=hi)


def ice_features(
    explore: pd.DataFrame,
    *,
    windows_min: Iterable[int] = DEFAULT_WINDOWS_MIN,
    strong_pos_threshold: float = 1.0,
    strong_neg_threshold: float = -0.5,
) -> pd.DataFrame:
    """Build ICE-derived features at multiple trailing windows.

    Per window m, columns added (× len(windows_min)):
      ice_mean_<W>          — trailing mean of instantaneous ICE
      ice_p10_<W>           — 10th percentile
      ice_p25_<W>           — 25th percentile
      ice_p50_<W>           — median
      ice_p75_<W>           — 75th
      ice_p90_<W>           — 90th
      ice_max_<W>           — max
      ice_min_<W>           — min
      ice_range_<W>         — max - min
      ice_pos_frac_<W>      — fraction of samples with ice > 0
      ice_neg_frac_<W>      — fraction of samples with ice < 0
      ice_strong_pos_<W>    — fraction with ice > strong_pos_threshold
      ice_strong_neg_<W>    — fraction with ice < strong_neg_threshold

    Plus deviation features:
      ice_dev_from_baseline   — (ice now) − (ice trailing-24h mean)
      ice_mean_60m_dev_24h    — (ice_mean_1h) − (ice_mean_24h)
    """
    if "ice" not in explore.columns:
        raise KeyError("explore must contain an 'ice' column")
    ice = explore["ice"].astype(float)

    out = pd.DataFrame(index=explore.index)

    for m in windows_min:
        win = f"{m}min"
        lbl = _label(m)
        roll = ice.rolling(win, min_periods=3)
        out[f"ice_mean_{lbl}"]   = roll.mean()
        out[f"ice_p10_{lbl}"]    = roll.quantile(0.10)
        out[f"ice_p25_{lbl}"]    = roll.quantile(0.25)
        out[f"ice_p50_{lbl}"]    = roll.quantile(0.50)
        out[f"ice_p75_{lbl}"]    = roll.quantile(0.75)
        out[f"ice_p90_{lbl}"]    = roll.quantile(0.90)
        out[f"ice_max_{lbl}"]    = roll.max()
        out[f"ice_min_{lbl}"]    = roll.min()
        out[f"ice_range_{lbl}"]  = out[f"ice_max_{lbl}"] - out[f"ice_min_{lbl}"]
        out[f"ice_pos_frac_{lbl}"]   = _rolling_pct_above(ice, win, 0.0)
        out[f"ice_neg_frac_{lbl}"]   = _rolling_pct_below(ice, win, 0.0)
        out[f"ice_strong_pos_{lbl}"] = _rolling_pct_above(ice, win, strong_pos_threshold)
        out[f"ice_strong_neg_{lbl}"] = _rolling_pct_below(ice, win, strong_neg_threshold)

    # Deviation-from-trailing-baseline features
    out["ice_dev_from_baseline"] = ice - ice.rolling("24h", min_periods=24).mean()
    if "ice_mean_1h" in out.columns and "ice_mean_24h" in out.columns:
        out["ice_mean_1h_dev_24h"] = out["ice_mean_1h"] - out["ice_mean_24h"]

    return out


def local_isf_features(
    explore: pd.DataFrame,
    *,
    windows_min: Iterable[int] = (60, 120, 240, 480, 1440),
    isf_clip_bounds: tuple = (-400.0, 400.0),
    ice_quiet_threshold: float = 0.5,
    robust_v_insulin_min: float = 0.05,
) -> pd.DataFrame:
    """Build local-ISF percentile + extrema features at multiple trailing windows.

    The "true max" and "true min" of local_isf give the most-sensitive and
    most-resistant moments respectively. Percentiles give the full shape of
    recent ISF distribution.

    Per window m, columns added:
      isf_p05_<W>           — 5th percentile (very meal-mode)
      isf_p10_<W>           — 10th
      isf_p25_<W>           — 25th
      isf_p50_<W>           — median (recent typical ISF)
      isf_p75_<W>           — 75th
      isf_p90_<W>           — 90th
      isf_p95_<W>           — 95th (very sensitive)
      isf_max_<W>           — true max (peak sensitivity)
      isf_min_<W>           — true min (peak resistance — often v_insulin≈0 → meal-mode)
      isf_iqr_<W>           — P75 - P25 (typical-range volatility)
      isf_range_<W>         — max - min (full-range volatility)

    Plus:
      isf_p50_24h           — 24h baseline median
      isf_p50_1h_rel_24h    — isf_p50_1h / isf_p50_24h (current sensitivity vs baseline)

    Robust filtered estimator (quiet moments + active insulin only):
      isf_robust_p50_2h     — P50 of local_isf restricted to samples where
                              |ice| < ice_quiet_threshold and |v_insulin| ≥ robust_v_insulin_min
      isf_robust_p50_4h     — same over 4h
      isf_robust_count_4h   — number of qualifying samples (sanity check)
    """
    if "local_isf" not in explore.columns:
        raise KeyError("explore must contain a 'local_isf' column")
    isf = _isf_clip(explore["local_isf"].astype(float), *isf_clip_bounds)

    out = pd.DataFrame(index=explore.index)

    for m in windows_min:
        win = f"{m}min"
        lbl = _label(m)
        roll = isf.rolling(win, min_periods=6)
        out[f"isf_p05_{lbl}"] = roll.quantile(0.05)
        out[f"isf_p10_{lbl}"] = roll.quantile(0.10)
        out[f"isf_p25_{lbl}"] = roll.quantile(0.25)
        out[f"isf_p50_{lbl}"] = roll.quantile(0.50)
        out[f"isf_p75_{lbl}"] = roll.quantile(0.75)
        out[f"isf_p90_{lbl}"] = roll.quantile(0.90)
        out[f"isf_p95_{lbl}"] = roll.quantile(0.95)
        out[f"isf_max_{lbl}"] = roll.max()
        out[f"isf_min_{lbl}"] = roll.min()
        out[f"isf_iqr_{lbl}"]   = out[f"isf_p75_{lbl}"] - out[f"isf_p25_{lbl}"]
        out[f"isf_range_{lbl}"] = out[f"isf_max_{lbl}"] - out[f"isf_min_{lbl}"]

    if "isf_p50_1h" in out.columns and "isf_p50_24h" in out.columns:
        # Ratio of recent ISF median to 24h baseline ISF median.
        # Guard against divide-by-zero / sign flips by masking when baseline ≈ 0.
        baseline = out["isf_p50_24h"]
        ratio = out["isf_p50_1h"] / baseline.where(baseline.abs() > 1.0, np.nan)
        out["isf_p50_1h_rel_24h"] = ratio

    # ── Robust ISF (quiet, active-insulin moments only) ──
    v_ins_col = "v_insulin_mgdl_min" if "v_insulin_mgdl_min" in explore.columns else ("v_insulin" if "v_insulin" in explore.columns else None)
    if "ice" in explore.columns and v_ins_col is not None:
        ice = explore["ice"].astype(float)
        v_ins = explore[v_ins_col].astype(float)
        quiet_mask = (ice.abs() < ice_quiet_threshold) & (v_ins.abs() >= robust_v_insulin_min)
        isf_quiet = isf.where(quiet_mask, np.nan)

        for m, lbl in [(120, "2h"), (240, "4h"), (480, "8h")]:
            win = f"{m}min"
            roll = isf_quiet.rolling(win, min_periods=4)
            out[f"isf_robust_p50_{lbl}"] = roll.quantile(0.50)
            out[f"isf_robust_p25_{lbl}"] = roll.quantile(0.25)
            out[f"isf_robust_p75_{lbl}"] = roll.quantile(0.75)
            # Count of qualifying samples in window (sanity)
            out[f"isf_robust_count_{lbl}"] = quiet_mask.astype(float).rolling(win, min_periods=1).sum()

    return out


def ice_run_features(
    explore: pd.DataFrame,
    *,
    windows_min: Iterable[int] = (60, 120, 240),
) -> pd.DataFrame:
    """Longest-consecutive-run features. Slow (O(n·W/Δt)) but useful as a
    qualitative shape signal: 'how sustained has the ICE departure been?'.

    Per window m:
      ice_run_pos_max_<W>   — longest contiguous run of ice > 0 within window
      ice_run_neg_max_<W>   — longest contiguous run of ice < 0 within window
    """
    if "ice" not in explore.columns:
        raise KeyError("explore must contain an 'ice' column")
    ice = explore["ice"].to_numpy()
    idx_ns = explore.index.view("int64")
    n = len(ice)

    out = pd.DataFrame(index=explore.index)
    for m in windows_min:
        win_ns = int(m * 60 * 1_000_000_000)
        lbl = _label(m)
        pos = np.full(n, np.nan)
        neg = np.full(n, np.nan)
        lo = 0
        for i in range(n):
            while lo < i and idx_ns[lo] < idx_ns[i] - win_ns:
                lo += 1
            sl = ice[lo:i + 1]
            if len(sl) < 3:
                continue
            # Longest run of positives
            run_p = run_p_max = 0
            run_n = run_n_max = 0
            for v in sl:
                if v > 0:
                    run_p += 1
                    if run_p > run_p_max:
                        run_p_max = run_p
                    run_n = 0
                elif v < 0:
                    run_n += 1
                    if run_n > run_n_max:
                        run_n_max = run_n
                    run_p = 0
                else:
                    run_p = 0
                    run_n = 0
            pos[i] = run_p_max
            neg[i] = run_n_max
        out[f"ice_run_pos_max_{lbl}"] = pos
        out[f"ice_run_neg_max_{lbl}"] = neg
    return out


def build_all_ice_isf_features(
    explore: pd.DataFrame,
    *,
    include_runs: bool = False,
    windows_min: Iterable[int] = DEFAULT_WINDOWS_MIN,
) -> pd.DataFrame:
    """Build the full ICE + local-ISF feature panel for downstream exploration.

    `include_runs=False` by default because the longest-run features cost
    O(n·W/Δt) Python time and aren't always informative.
    """
    parts = [
        ice_features(explore, windows_min=windows_min),
        local_isf_features(explore, windows_min=tuple(w for w in windows_min if w >= 60)),
    ]
    if include_runs:
        parts.append(ice_run_features(explore))
    return pd.concat(parts, axis=1)
