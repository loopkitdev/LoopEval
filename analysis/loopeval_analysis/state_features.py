"""Per-sample current-state features for conditional-pattern analyses.

The idea: at each 5-min slice, compute a vector of "what's going on right now"
features (BG context, IOB context, recent dose history, recent ISF events,
time-of-day, etc.). Then any downstream analysis can slice by any combination
of these features to find conditional cells with distinctive forward outcomes.

All features are CAUSAL — only use information available at or before each
sample's timestamp. No look-ahead.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


def _trailing_stat(values: np.ndarray, idx_ns: np.ndarray, window_ns: int,
                   reducer) -> np.ndarray:
    """Compute a reducer (callable on a slice) over each sample's trailing
    [t - window, t] window. Returns an array of the same length."""
    n = len(values)
    out = np.full(n, np.nan)
    lo = 0
    for i in range(n):
        t = idx_ns[i]
        while lo < i and idx_ns[lo] < t - window_ns:
            lo += 1
        if i - lo + 1 >= 3:
            out[i] = reducer(values[lo:i + 1])
    return out


def boost_damp_score(
    state: pd.DataFrame,
    *,
    mode: str = "discrete",
    bg_threshold: float = 180.0,
) -> pd.Series:
    """Compute a per-sample BOOST/DAMP score for the closed-loop simulator's
    `smoothBoostFactor`.

    Score convention (matches ``smoothBoostFactor`` two-sided mapping with
    lowAnchor=0.5, highAnchor=1.0, downLowAnchor=0.0):
      • ``score = 1.0`` → DAMP direction (less aggressive ISF; e.g., 1.5×)
      • ``score = 0.5`` → neutral (1.0× ISF, no change)
      • ``score = 0.0`` → BOOST direction (more aggressive ISF; e.g., 0.7×)

    Modes:
      • ``discrete`` — exact rule match → 0.0 / 0.5 / 1.0
      • ``continuous`` — smooth combination of underlying feature predicates
        in [0, 1]; cell membership becomes a confidence-weighted score

    Both apply only when BG > ``bg_threshold`` (180 mg/dL by default). Outside
    the hyper zone the score is 0.5 (neutral).

    Built from the rule definitions documented at
    `runs/2026-05-14-isf-year/safe_boost_rules_report.txt`.
    """
    if state.empty:
        return pd.Series(dtype=float, index=state.index)

    bg = state["bg"]
    in_hyper = bg > bg_threshold

    if mode == "discrete":
        # BOOST cell: iob ≤ 1.0 AND any of (bg_delta_120m ≥ 20, bg_delta_60m ≥ 10,
        #                                   v_cgm_30m_mean ≥ 0.3, botK_isf_60m ≥ -30)
        boost_mask = (
            in_hyper
            & (state["iob"] <= 1.0)
            & (
                (state.get("bg_delta_120m", pd.Series(np.nan, index=state.index)) >= 20)
                | (state.get("bg_delta_60m",  pd.Series(np.nan, index=state.index)) >= 10)
                | (state.get("v_cgm_30m_mean", pd.Series(np.nan, index=state.index)) >= 0.3)
                | (state.get("botK_isf_60m",   pd.Series(np.nan, index=state.index)) >= -30)
            )
        )
        # DAMP cell: iob_max_60m ≥ 3.5 AND (rolling_ice ≤ 0 OR morning)
        morning = (state["hour"] >= 6) & (state["hour"] < 12)
        damp_mask = (
            in_hyper
            & (state.get("iob_max_60m", pd.Series(np.nan, index=state.index)) >= 3.5)
            & (
                (state.get("rolling_ice", pd.Series(np.nan, index=state.index)) <= 0)
                | morning
            )
        )
        # Discrete score: 0.5 default, 0.0 in boost, 1.0 in damp.
        # If both somehow match (shouldn't), damp wins (safety side).
        score = pd.Series(0.5, index=state.index, dtype=float)
        score[boost_mask.fillna(False)] = 0.0
        score[damp_mask.fillna(False)] = 1.0
        return score

    if mode == "continuous":
        # Each component in [0, 1].
        def clip01(s: pd.Series) -> pd.Series:
            return s.clip(lower=0.0, upper=1.0)

        # DAMP components
        # IOB pipeline magnitude — ramps from 0 at iob_max_60m=2.5 to 1 at 4.5
        c_iob_high = clip01((state.get("iob_max_60m", pd.Series(np.nan, index=state.index)) - 2.5) / 2.0)
        # Active insulin response — ramps from 0 at rolling_ice=+0.5 to 1 at -1.0
        c_ice_active = clip01((0.5 - state.get("rolling_ice", pd.Series(np.nan, index=state.index))) / 1.5)
        # Morning indicator (hour 6-12) as 1.0, ramping at edges (5-6 and 12-13) for smoothness
        h = state["hour"].astype(float)
        c_morning = clip01(pd.concat([
            clip01((h - 5.0)),       # 0 at h=5, 1 at h≥6
            clip01(13.0 - h),        # 1 at h≤12, 0 at h=13
        ], axis=1).min(axis=1))

        # Damp strength: high IOB AND (active insulin OR morning). Use max for OR, multiply for AND.
        damp_strength = c_iob_high * pd.concat([c_ice_active, c_morning], axis=1).max(axis=1)

        # BOOST components
        # Low IOB — ramps from 1 at iob=0 to 0 at iob=2.0
        c_iob_low = clip01((2.0 - state["iob"]) / 2.0)
        # BG rising (over 60m) — ramps from 0 at no change to 1 at +20 mg/dL
        c_bg_rising = clip01(state.get("bg_delta_60m", pd.Series(0.0, index=state.index)) / 20.0)
        # No recent carbs — ramps from 0 at botK=-100 to 1 at botK=-30 (= "no recent carbs")
        botK = state.get("botK_isf_60m", pd.Series(0.0, index=state.index))
        c_no_carbs = clip01((botK + 100.0) / 70.0)

        boost_strength = c_iob_low * pd.concat([c_bg_rising, c_no_carbs], axis=1).max(axis=1)

        # Combine: damp pulls score up from 0.5; boost pulls down.
        score = 0.5 + 0.5 * damp_strength - 0.5 * boost_strength
        # Only in hyper zone; neutral elsewhere
        score = score.where(in_hyper, 0.5)
        return clip01(score).fillna(0.5)

    raise ValueError(f"unknown mode={mode!r}")


def apply_boost_guards(
    score: pd.Series,
    state: pd.DataFrame,
    *,
    max_consecutive_boost_steps: int = 3,
    kill_on_vcgm_below: float = 0.0,
    kill_on_bg_below: Optional[float] = None,
) -> pd.Series:
    """Apply kill switches and duration caps to a BOOST/DAMP score series.

    Designed to fix the "boost keeps firing for too long" problem identified
    after the discrete v1 sim showed >75% hypo rate for episodes >1h.

    Guards:
      1. ``max_consecutive_boost_steps``: cap contiguous BOOST runs (score<0.25)
         at this many 5-min steps. After the cap, score is forced to 0.5
         (neutral) until BG-rising condition recurs.
      2. ``kill_on_vcgm_below``: if ``state['v_cgm_30m_mean'] < this``, force
         score to 0.5. Default 0 → kill the boost the moment BG stops rising
         on a 30-min rolling basis. The boost is working; stop adding.
      3. ``kill_on_bg_below``: if ``state['bg'] < this``, force score to 0.5.
         Optional secondary safety floor (default None = disabled).

    DAMP cells (score>0.75) are left untouched — they're already the
    less-aggressive direction and don't have this duration issue.
    """
    out = score.copy()

    # 2. v_cgm kill switch (vectorized)
    if kill_on_vcgm_below is not None and "v_cgm_30m_mean" in state.columns:
        kill = (out < 0.25) & (state["v_cgm_30m_mean"].fillna(0) < kill_on_vcgm_below)
        out[kill] = 0.5

    # 3. BG-floor kill (optional)
    if kill_on_bg_below is not None and "bg" in state.columns:
        kill = (out < 0.25) & (state["bg"].fillna(999) < kill_on_bg_below)
        out[kill] = 0.5

    # 1. Max-consecutive cap (iterative)
    is_boost = (out < 0.25).to_numpy()
    n = len(is_boost)
    run_len = 0
    for i in range(n):
        if is_boost[i]:
            run_len += 1
            if run_len > max_consecutive_boost_steps:
                is_boost[i] = False
        else:
            run_len = 0
    # Anything that lost its boost flag → neutral
    capped = (out < 0.25) & (~pd.Series(is_boost, index=out.index))
    out[capped] = 0.5

    return out


def per_sample_state_features(
    explore: pd.DataFrame,
    *,
    basal_timeline: Optional[pd.DataFrame] = None,
    carbs: Optional[pd.DataFrame] = None,
    bg_normal: float = 80.0,
    bg_low: float = 70.0,
    bg_high: float = 180.0,
) -> pd.DataFrame:
    """Build a per-sample state-feature DataFrame aligned to ``explore.index``.

    Features (all evaluated at sample time t):

    Current state:
      • bg           — current bg_smoothed
      • iob          — current IOB
      • v_cgm        — instantaneous v_cgm (mg/dL/min)
      • ice          — instantaneous ICE (mg/dL/min)
      • rolling_ice  — 30-min centered ICE (pre-computed in isf-explore)
      • local_isf    — instant per-sample local_isf
      • hour         — local hour-of-day (0..23)
      • dow          — day-of-week (0=Mon)
      • month        — month-of-year (1..12)

    Trailing-window features:
      • v_cgm_30m_mean      — mean v_cgm over last 30 min
      • v_cgm_60m_mean      — mean v_cgm over last 60 min
      • bg_delta_30m        — bg(t) - bg(t-30m)
      • bg_delta_60m        — bg(t) - bg(t-60m)
      • bg_delta_120m       — bg(t) - bg(t-120m)
      • iob_delta_60m       — iob(t) - iob(t-60m)  (positive = IOB rising = dose stack)
      • iob_max_60m         — peak IOB in last 60 min
      • iob_max_240m        — peak IOB in last 4h
      • topK_isf_60m        — top-K=5 mean local_isf in last 60 min (sensitive bursts)
      • topK_isf_240m       — top-K=5 mean local_isf in last 4h
      • botK_isf_60m        — bot-K=5 mean local_isf in last 60 min (meal/carb bursts)
      • botK_isf_240m       — bot-K=5 mean local_isf in last 4h

    Dose-context features (if basal_timeline given):
      • suspend_pct_60m     — fraction of last 60 min at 0 U/hr
      • suspend_pct_240m    — fraction of last 4h at 0 U/hr
      • rate_uhr            — current basal rate (U/hr)

    Carb-context features (if carbs given):
      • mins_since_carb     — minutes since most recent carb entry (np.nan if none)
      • carbs_last_240m_g   — total grams of carbs entered in last 4h

    Returns a DataFrame indexed by ``explore.index`` with the columns above.
    """
    if explore.empty:
        return pd.DataFrame()

    out = pd.DataFrame(index=explore.index)
    out["bg"] = explore["bg_smoothed"]
    out["iob"] = explore["iob"]
    out["v_cgm"] = explore["v_cgm"]
    out["ice"] = explore.get("ice", explore.get("rolling_ice"))
    out["rolling_ice"] = explore.get("rolling_ice")
    out["local_isf"] = explore["local_isf"]

    tz_local = explore.index
    out["hour"] = tz_local.hour
    out["dow"] = tz_local.dayofweek
    out["month"] = tz_local.month

    idx_ns = explore.index.view("int64")
    bg = explore["bg_smoothed"].to_numpy()
    iob = explore["iob"].to_numpy()
    v_cgm = explore["v_cgm"].to_numpy()
    isf = explore["local_isf"].to_numpy()

    def _bg_at_lag(lag_ns: int) -> np.ndarray:
        n = len(idx_ns)
        target = idx_ns - lag_ns
        out_arr = np.full(n, np.nan)
        j = 0
        for i in range(n):
            while j < n - 1 and idx_ns[j + 1] <= target[i]:
                j += 1
            # j is the largest index with idx_ns[j] <= target[i]
            if idx_ns[j] <= target[i] and (target[i] - idx_ns[j]) <= 7 * 60 * 1_000_000_000:
                # within 7 minutes (allow gap)
                out_arr[i] = bg[j]
        return out_arr

    out["bg_30m_ago"]  = _bg_at_lag(30 * 60 * 1_000_000_000)
    out["bg_60m_ago"]  = _bg_at_lag(60 * 60 * 1_000_000_000)
    out["bg_120m_ago"] = _bg_at_lag(120 * 60 * 1_000_000_000)
    out["bg_delta_30m"]  = bg - out["bg_30m_ago"]
    out["bg_delta_60m"]  = bg - out["bg_60m_ago"]
    out["bg_delta_120m"] = bg - out["bg_120m_ago"]

    iob_60m_ago = pd.Series(iob, index=explore.index)
    out["iob_60m_ago"] = iob_60m_ago.reindex(explore.index - pd.Timedelta("60min"),
                                             method="nearest", tolerance=pd.Timedelta("7min")).values
    out["iob_delta_60m"] = iob - out["iob_60m_ago"]

    def trailing_max(arr, win_ns):
        return _trailing_stat(arr, idx_ns, win_ns, lambda s: float(np.max(s)))

    def trailing_mean(arr, win_ns):
        return _trailing_stat(arr, idx_ns, win_ns, lambda s: float(np.mean(s)))

    def trailing_topk(arr, win_ns, k=5):
        def red(s):
            n = len(s)
            kk = min(k, n)
            return float(np.mean(np.sort(s)[-kk:]))
        return _trailing_stat(arr, idx_ns, win_ns, red)

    def trailing_botk(arr, win_ns, k=5):
        def red(s):
            n = len(s)
            kk = min(k, n)
            return float(np.mean(np.sort(s)[:kk]))
        return _trailing_stat(arr, idx_ns, win_ns, red)

    out["v_cgm_30m_mean"]  = trailing_mean(v_cgm,  30 * 60 * 1_000_000_000)
    out["v_cgm_60m_mean"]  = trailing_mean(v_cgm,  60 * 60 * 1_000_000_000)
    out["iob_max_60m"]     = trailing_max(iob,    60 * 60 * 1_000_000_000)
    out["iob_max_240m"]    = trailing_max(iob,   240 * 60 * 1_000_000_000)
    out["topK_isf_60m"]    = trailing_topk(isf,   60 * 60 * 1_000_000_000)
    out["topK_isf_240m"]   = trailing_topk(isf,  240 * 60 * 1_000_000_000)
    out["botK_isf_60m"]    = trailing_botk(isf,   60 * 60 * 1_000_000_000)
    out["botK_isf_240m"]   = trailing_botk(isf,  240 * 60 * 1_000_000_000)

    # Dose-context
    if basal_timeline is not None and "rate_uhr" in basal_timeline.columns:
        bt = basal_timeline.copy()
        # Resample basal timeline to a finer grid to allow per-sample alignment
        rates = bt["rate_uhr"].reindex(explore.index, method="nearest",
                                       tolerance=pd.Timedelta("7min"))
        out["rate_uhr"] = rates.values

        # Suspend fraction over trailing windows.
        is_susp = (bt["rate_uhr"] == 0).astype(float)
        # Resample is_susp to a regular series first.
        is_susp_5m = is_susp.reindex(
            pd.date_range(start=bt.index.min(), end=bt.index.max(), freq="5min"),
            method="nearest", tolerance=pd.Timedelta("3min")
        ).fillna(0)
        susp_60m = is_susp_5m.rolling("60min").mean()
        susp_240m = is_susp_5m.rolling("240min").mean()
        out["suspend_pct_60m"] = susp_60m.reindex(explore.index, method="nearest",
                                                  tolerance=pd.Timedelta("5min")).values
        out["suspend_pct_240m"] = susp_240m.reindex(explore.index, method="nearest",
                                                    tolerance=pd.Timedelta("5min")).values

    # Carb context
    if carbs is not None and not carbs.empty and "grams" in carbs.columns:
        carb_idx = carbs.index.view("int64")
        carb_g = carbs["grams"].to_numpy()
        n = len(idx_ns)
        mins_since = np.full(n, np.nan)
        grams_240m = np.zeros(n)
        for i in range(n):
            t = idx_ns[i]
            # Last carb at or before t
            pos = np.searchsorted(carb_idx, t, side="right") - 1
            if pos >= 0:
                mins_since[i] = (t - carb_idx[pos]) / 60 / 1_000_000_000
            # Carbs in trailing 240min
            window_start = t - 240 * 60 * 1_000_000_000
            lo = np.searchsorted(carb_idx, window_start, side="left")
            hi = np.searchsorted(carb_idx, t, side="right")
            grams_240m[i] = float(carb_g[lo:hi].sum())
        out["mins_since_carb"] = mins_since
        out["carbs_last_240m_g"] = grams_240m

    return out
