"""Loaders + estimators for ISF time series.

Operates on archived CSVs under `runs/2026-05-14-isf-year/` that were emitted
by the now-removed `loop-eval isf-rolling` / `loop-eval isf-explore` Swift
subcommands. New analyses use the pure-Python estimators below.

Two CSV shapes are supported by the loaders:

1. *rolling* — τ-quantile-regression ISF on rolling windows. Best
   signal-to-noise for windows >= ~6h; minSamples gate prevents numerical
   garbage but causes NaN gaps in sparse sections.

2. *explore* — per-CGM-interval sample of
   ``local_isf = isf_scheduled × v_cgm / v_insulin`` plus classification
   (meal/exercise/neutral). ``event_sensitivity_series`` aggregates the
   most-sensitive events over short trailing windows. Works at 1h scale
   where quantile regression is too unstable.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


def load_isf_rolling_csv(path: str, *, tz: str = "America/Chicago") -> pd.DataFrame:
    """Load a CSV emitted by ``loop-eval isf-rolling``.

    Columns: center_time, window_start, window_end, n_samples, isf_q, intercept,
    pseudo_r2, ci_low, ci_high. Returns a DataFrame indexed by center_time
    (tz-aware in `tz`), one row per window.
    """
    df = pd.read_csv(path, parse_dates=["center_time", "window_start", "window_end"])
    df = df.set_index("center_time").sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert(tz)
    return df


def load_isf_explore_csv(path: str, *, tz: str = "America/Chicago") -> pd.DataFrame:
    """Load the per-sample CSV emitted by ``loop-eval isf-explore``.

    Columns: time, bg_smoothed, v_cgm_mgdl_min, v_insulin_mgdl_min, ice,
    rolling_ice, iob, isf_scheduled, local_isf, weight, class.
    """
    df = pd.read_csv(path, parse_dates=["time"])
    df = df.set_index("time").sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert(tz)
    # Standardize column names: drop _mgdl_min suffix for readability downstream.
    rename = {
        "v_cgm_mgdl_min": "v_cgm",
        "v_insulin_mgdl_min": "v_insulin",
    }
    df = df.rename(columns=rename)
    return df


def event_sensitivity_series(
    explore: pd.DataFrame,
    *,
    window_hours: float = 1.0,
    step_hours: float = 1.0,
    k_events: int = 5,
    min_abs_v_insulin: float = 0.1,
    neutral_only: bool = True,
    bg_min: Optional[float] = 80.0,
    bg_max: Optional[float] = 395.0,
) -> pd.DataFrame:
    """For each step-aligned timestamp, summarize the most-sensitive insulin
    events in the trailing ``window_hours``.

    Selection (within the window):
      • |v_insulin| ≥ ``min_abs_v_insulin`` (filter weak-action samples that
        amplify noise in local_isf)
      • optionally class == 'neutral' (no meal/exercise classifier override)
      • bg_smoothed inside [bg_min, bg_max)

    From the surviving samples, take the K with the *smallest* (most-negative)
    ``v_cgm / |v_insulin|`` ratio — i.e., where insulin appeared to lower BG
    hardest per unit of action. Report:

      • ``event_isf``  — median of those K samples' ``local_isf``
      • ``event_drop`` — median of (v_cgm / |v_insulin|) for those K, in
        mg/dL/min per mg/dL/min — a unit-free "drop velocity per insulin
        velocity" signal
      • ``n_window``   — count of samples in the window after filters
      • ``n_used``     — min(K, n_window)

    Low ``event_isf`` = strongly sensitive recent insulin response.

    Returns a DataFrame indexed at step-aligned timestamps.
    """
    if explore.empty:
        return pd.DataFrame(columns=["event_isf", "event_drop", "n_window", "n_used"])

    df = explore.copy()
    # Pre-filter
    mask = df["v_insulin"].abs() >= min_abs_v_insulin
    if neutral_only and "class" in df.columns:
        mask &= (df["class"] == "neutral")
    if bg_min is not None:
        mask &= (df["bg_smoothed"] >= bg_min)
    if bg_max is not None:
        mask &= (df["bg_smoothed"] < bg_max)
    df = df.loc[mask].copy()
    if df.empty:
        return pd.DataFrame(columns=["event_isf", "event_drop", "n_window", "n_used"])

    # The metric: "drop velocity per |insulin velocity|" — smaller (more
    # negative) means insulin was working harder per unit. Same monotonic
    # ordering as local_isf for v_insulin < 0, but doesn't reference the
    # scheduled-ISF normalization, so it's invariant to schedule changes.
    df["drop_per_u"] = df["v_cgm"] / df["v_insulin"].abs()

    step = pd.Timedelta(hours=step_hours)
    window = pd.Timedelta(hours=window_hours)
    start = df.index.min().ceil(step)
    end = df.index.max().floor(step)
    if start >= end:
        return pd.DataFrame(columns=["event_isf", "event_drop", "n_window", "n_used"])
    timestamps = pd.date_range(start=start, end=end, freq=step)

    # Numpy fast path: binary-search the sorted index for window bounds.
    idx_ns = df.index.view("int64")
    drop = df["drop_per_u"].to_numpy()
    isf = df["local_isf"].to_numpy()

    out_isf = np.full(len(timestamps), np.nan)
    out_drop = np.full(len(timestamps), np.nan)
    n_window = np.zeros(len(timestamps), dtype=np.int64)
    n_used = np.zeros(len(timestamps), dtype=np.int64)

    for i, t in enumerate(timestamps):
        t_end_ns = t.value
        t_start_ns = (t - window).value
        lo = np.searchsorted(idx_ns, t_start_ns, side="left")
        hi = np.searchsorted(idx_ns, t_end_ns, side="right")
        n = hi - lo
        n_window[i] = n
        if n == 0:
            continue
        slice_drop = drop[lo:hi]
        slice_isf = isf[lo:hi]
        # Pick K most-sensitive (smallest drop_per_u)
        k = min(k_events, n)
        n_used[i] = k
        partition = np.argpartition(slice_drop, k - 1)[:k]
        out_drop[i] = float(np.median(slice_drop[partition]))
        out_isf[i] = float(np.median(slice_isf[partition]))

    out = pd.DataFrame(
        {
            "event_isf": out_isf,
            "event_drop": out_drop,
            "n_window": n_window,
            "n_used": n_used,
        },
        index=timestamps,
    )
    return out


def _quantile_regression(xs: np.ndarray, ys: np.ndarray, tau: float) -> tuple[float, float, float]:
    """Pinball-loss minimisation. Returns (slope, intercept, pseudo_r2)."""
    n = xs.size
    if n < 20:
        return float("nan"), float("nan"), float("nan")

    def loss_for_slope(b):
        r = ys - b * xs
        a = float(np.quantile(r, tau, method="linear"))
        resid = ys - a - b * xs
        pos = tau * np.where(resid >= 0, resid, 0.0).sum()
        neg = (tau - 1.0) * np.where(resid < 0, resid, 0.0).sum()
        return pos + neg, a

    # Coarse grid → 4 zoom passes (matches the Swift solver).
    best_loss = float("inf")
    best_b = 0.0
    best_a = 0.0
    grid = np.arange(-100.0, 500.1, 20.0)
    for b in grid:
        l, a = loss_for_slope(b)
        if l < best_loss:
            best_loss, best_b, best_a = l, b, a
    step = 20.0
    for _ in range(4):
        step /= 5.0
        b_lo = best_b - 5 * step
        b_hi = best_b + 5 * step
        for b in np.arange(b_lo, b_hi + step / 2, step):
            l, a = loss_for_slope(b)
            if l < best_loss:
                best_loss, best_b, best_a = l, b, a

    # Null loss
    null_a = float(np.quantile(ys, tau, method="linear"))
    null_resid = ys - null_a
    null_loss = tau * np.where(null_resid >= 0, null_resid, 0.0).sum() \
              + (tau - 1.0) * np.where(null_resid < 0, null_resid, 0.0).sum()
    pseudo = max(0.0, 1.0 - best_loss / null_loss) if null_loss > 0 else 0.0
    return float(best_b), float(best_a), float(pseudo)


def rolling_multi_estimator(
    explore: pd.DataFrame,
    *,
    window_hours: float,
    step_min: int = 30,
    neutral_only: bool = True,
    min_n: int = 10,
    min_abs_v_insulin: float = 0.05,
    bg_min: Optional[float] = 80.0,
    bg_max: Optional[float] = 395.0,
    quantile: float = 0.10,
) -> pd.DataFrame:
    """For each step-aligned time t, compute a battery of short-term ISF
    estimators over the trailing ``window_hours``.

    Estimators (all in mg/dL/U, in the convention where larger = more
    sensitive direction except where noted):
      • ``mean_isf``       — arithmetic mean of per-sample local_isf
      • ``median_isf``     — median
      • ``wmean_isf``      — |v_insulin|-weighted mean
      • ``p10_isf``        — 10th percentile (toward resistance/meal tail)
      • ``p90_isf``        — 90th percentile (toward most-sensitive tail)
      • ``max_isf``        — maximum (most extreme sensitive event)
      • ``min_isf``        — minimum (most extreme meal/resistance event)
      • ``topK_mean_isf``  — mean of top-K=5 most-sensitive local_isf
      • ``botK_mean_isf``  — mean of bottom-K=5 (most resistance/meal-like)
      • ``ols_slope``      — OLS regression slope of v_cgm vs activity
      • ``quantile_slope`` — τ-quantile regression slope (carb-robust)
      • ``n_samples``      — number of samples used in this window

    Index is at step-aligned trailing window right-edges. The output has
    ``isnan`` rows where the window has fewer than ``min_n`` samples.
    """
    if explore.empty:
        return pd.DataFrame()

    df = explore.copy()
    mask = df["v_insulin"].abs() >= min_abs_v_insulin
    if neutral_only and "class" in df.columns:
        mask &= (df["class"] == "neutral")
    if bg_min is not None:
        mask &= (df["bg_smoothed"] >= bg_min)
    if bg_max is not None:
        mask &= (df["bg_smoothed"] < bg_max)
    df = df.loc[mask].copy()
    if df.empty:
        return pd.DataFrame()

    df["activity"] = df["v_insulin"] / df["isf_scheduled"]

    step = pd.Timedelta(minutes=step_min)
    window = pd.Timedelta(hours=window_hours)
    start = df.index.min().ceil(step)
    end = df.index.max().floor(step)
    if start >= end:
        return pd.DataFrame()
    timestamps = pd.date_range(start=start, end=end, freq=step)

    idx_ns = df.index.view("int64")
    isf = df["local_isf"].to_numpy()
    activity = df["activity"].to_numpy()
    v_cgm = df["v_cgm"].to_numpy()
    v_insulin_abs = df["v_insulin"].abs().to_numpy()

    K = 5
    cols = [
        "mean_isf", "median_isf", "wmean_isf",
        "p10_isf", "p90_isf", "max_isf", "min_isf",
        "topK_mean_isf", "botK_mean_isf",
        "ols_slope", "quantile_slope", "n_samples",
    ]
    out = {c: np.full(len(timestamps), np.nan) for c in cols}

    for i, t in enumerate(timestamps):
        t_end_ns = t.value
        t_start_ns = (t - window).value
        lo = np.searchsorted(idx_ns, t_start_ns, side="left")
        hi = np.searchsorted(idx_ns, t_end_ns, side="right")
        n = hi - lo
        out["n_samples"][i] = n
        if n < min_n:
            continue
        win_isf = isf[lo:hi]
        win_act = activity[lo:hi]
        win_cgm = v_cgm[lo:hi]
        win_w = v_insulin_abs[lo:hi]

        out["mean_isf"][i] = float(win_isf.mean())
        out["median_isf"][i] = float(np.median(win_isf))
        sw = float(win_w.sum())
        out["wmean_isf"][i] = float(np.sum(win_isf * win_w) / sw) if sw > 0 else np.nan
        out["p10_isf"][i] = float(np.percentile(win_isf, 10))
        out["p90_isf"][i] = float(np.percentile(win_isf, 90))
        out["max_isf"][i] = float(np.max(win_isf))
        out["min_isf"][i] = float(np.min(win_isf))

        k = min(K, n)
        sorted_isf = np.sort(win_isf)
        out["topK_mean_isf"][i] = float(np.mean(sorted_isf[-k:]))
        out["botK_mean_isf"][i] = float(np.mean(sorted_isf[:k]))

        # OLS slope of v_cgm vs activity
        var_a = float(np.var(win_act))
        if var_a > 1e-12 and n >= 5:
            slope, intercept = np.polyfit(win_act, win_cgm, 1)
            out["ols_slope"][i] = float(slope)

        # Quantile regression
        if n >= 20:
            b, _, _ = _quantile_regression(win_act, win_cgm, quantile)
            out["quantile_slope"][i] = b

    return pd.DataFrame(out, index=timestamps)


def forward_glucose_features(
    explore: pd.DataFrame,
    *,
    horizons_min: tuple[int, ...] = (30, 60, 120, 240, 480),
    low_threshold: float = 70.0,
    severe_threshold: float = 54.0,
) -> pd.DataFrame:
    """Build per-sample forward-looking glucose features from an `isf-explore`-style
    DataFrame (any frame indexed by datetime with a ``bg_smoothed`` column works).

    For each row at time t and each horizon h minutes, produces:
      • ``dbg_<h>m``       — bg_smoothed(t+h) − bg_smoothed(t)
      • ``min_bg_<h>m``    — min(bg_smoothed) over [t, t+h]
      • ``hits_low_<h>m``  — 1 if min_bg < ``low_threshold`` else 0
      • ``hits_sev_<h>m``  — 1 if min_bg < ``severe_threshold`` else 0

    The window is anchored at sample t and extends forward h minutes. Samples
    within h of the end of the dataset get NaN for that horizon.

    This is a pure look-ahead: do NOT use it to inform a model that will be
    deployed real-time without subtracting the look-ahead window. Useful for
    *correlating* signals available at time t against what BG does next.
    """
    if explore.empty or "bg_smoothed" not in explore.columns:
        return pd.DataFrame()

    bg = explore["bg_smoothed"].to_numpy(dtype=float)
    idx_ns = explore.index.view("int64")
    n = len(bg)

    out = {}
    for h in horizons_min:
        horizon_ns = int(h) * 60 * 1_000_000_000  # minutes → ns
        dbg = np.full(n, np.nan)
        min_bg = np.full(n, np.nan)
        # Walk forward with a moving right pointer that advances monotonically.
        right = 0
        for i in range(n):
            if right < i:
                right = i
            limit = idx_ns[i] + horizon_ns
            while right < n - 1 and idx_ns[right + 1] <= limit:
                right += 1
            # Now [i, right] are inside the window.
            if right > i:
                window = bg[i:right + 1]
                min_bg[i] = float(np.nanmin(window))
                dbg[i] = float(bg[right] - bg[i])
        out[f"dbg_{h}m"] = dbg
        out[f"min_bg_{h}m"] = min_bg
        out[f"hits_low_{h}m"] = (min_bg < low_threshold).astype(np.int8)
        out[f"hits_sev_{h}m"] = (min_bg < severe_threshold).astype(np.int8)

    return pd.DataFrame(out, index=explore.index)


def rolling_quantile_isf(
    explore: pd.DataFrame,
    *,
    window_hours: float = 6.0,
    step_hours: float = 1.0,
    quantile: float = 0.10,
    min_samples: int = 15,
    min_abs_v_insulin: float = 0.05,
    bg_min: Optional[float] = 80.0,
    bg_max: Optional[float] = 395.0,
) -> pd.DataFrame:
    """Python-side rolling τ-quantile ISF, computed directly from the
    per-sample ``isf-explore`` CSV. Avoids re-running the slow Swift
    ISFSample compute when iterating on window scales.

    Output columns: ``isf_q``, ``intercept``, ``pseudo_r2``, ``n_samples``.
    Index: step-aligned trailing-window centers (right edge of window).
    """
    if explore.empty:
        return pd.DataFrame(columns=["isf_q", "intercept", "pseudo_r2", "n_samples"])

    df = explore.copy()
    mask = df["v_insulin"].abs() >= min_abs_v_insulin
    if bg_min is not None:
        mask &= (df["bg_smoothed"] >= bg_min)
    if bg_max is not None:
        mask &= (df["bg_smoothed"] < bg_max)
    df = df.loc[mask].copy()
    if df.empty:
        return pd.DataFrame(columns=["isf_q", "intercept", "pseudo_r2", "n_samples"])

    # activity = v_insulin / isf_scheduled  (mg/dL/min per (mg/dL/U) = U/min, signed)
    df["activity"] = df["v_insulin"] / df["isf_scheduled"]

    step = pd.Timedelta(hours=step_hours)
    window = pd.Timedelta(hours=window_hours)
    start = df.index.min().ceil(step)
    end = df.index.max().floor(step)
    if start >= end:
        return pd.DataFrame(columns=["isf_q", "intercept", "pseudo_r2", "n_samples"])
    timestamps = pd.date_range(start=start, end=end, freq=step)

    idx_ns = df.index.view("int64")
    activity = df["activity"].to_numpy()
    v_cgm = df["v_cgm"].to_numpy()

    slope = np.full(len(timestamps), np.nan)
    intercept = np.full(len(timestamps), np.nan)
    pr2 = np.full(len(timestamps), np.nan)
    n_arr = np.zeros(len(timestamps), dtype=np.int64)

    for i, t in enumerate(timestamps):
        t_end_ns = t.value
        t_start_ns = (t - window).value
        lo = np.searchsorted(idx_ns, t_start_ns, side="left")
        hi = np.searchsorted(idx_ns, t_end_ns, side="right")
        n = hi - lo
        n_arr[i] = n
        if n < min_samples:
            continue
        b, a, p2 = _quantile_regression(activity[lo:hi], v_cgm[lo:hi], quantile)
        slope[i] = b
        intercept[i] = a
        pr2[i] = p2

    return pd.DataFrame(
        {"isf_q": slope, "intercept": intercept, "pseudo_r2": pr2, "n_samples": n_arr},
        index=timestamps,
    )
