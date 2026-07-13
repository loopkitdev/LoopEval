"""Continuous carb-pressure predictor — EXPERIMENTAL meal-anticipation model.

Predicts near-future POSITIVE ICE ("carb pressure") from causal, trailing ICE
features + time-of-day/day-of-week. Built 2026-07 as a meal-anticipation
foundation: instead of detecting discrete meals, it treats the anticipated
carb-appearance magnitude as a continuous regression target.

STATUS: EXPERIMENTAL — kept for future exploration, may be removed.
  The signal is REAL (leak-free walk-forward: Spearman ~0.51 on user2, ~0.41 on
  user1; recent-ICE features roughly double the rank signal over time-of-day
  alone). BUT it did NOT convert to a closed-loop therapy win when wired as a
  forecast offset (`--candidate-forecast-offset-csv`): across modes/precisions it
  behaved as a uniform aggressiveness slider (highs down, lows up, flat TIR) or,
  when made high-precision, had negligible effect. The rhythm-level signal is not
  precise enough to pre-dose a specific meal without false-positive lows. See
  memory/project_meal_characterization_2026_07_06 for the full record.

Pipeline (each step is a standalone function; compose as needed):
  compute_causal_ice()        ICE on the CAUSAL fixed-lag-smoothed substrate
  build_ice_features()        trailing positive-ICE feature battery + time context
  make_target()               continuous target: mean positive-carb-ICE ahead
  walk_forward_eval()         honest expanding-train / future-test R2 + Spearman
  train_carb_pressure_model() fit a GradientBoosting regressor on a train window
  predict_to_offset_csv()     out-of-sample predictions -> TRANSIENT forecast-offset
                              CSV consumable by `loop-eval simulate
                              --candidate-forecast-offset-csv`

Substrate note: ICE is computed on `kalman.fixed_lag_smooth` (causal — only the
most recent ~lag_steps samples are provisional), NOT the full RTS smoother, so the
features are deployment-faithful (no future leak). See kalman.py and
memory/feedback_rts_smoothed_substrate.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .ice_rts import compute_ice
from .kalman import fixed_lag_smooth
from .glucose import load_glucose_cache, find_glucose_cache

# Causal trailing features + time context. The recent positive-carb-ICE battery
# carries almost all the predictive signal; time-of-day is a secondary contributor.
FEATURE_COLS = [
    "hour_sin", "hour_cos", "dow", "is_weekend",
    "carb_sum_1h", "carb_sum_2h", "carb_sum_4h", "carb_sum_6h",
    "carb_max_6h", "carb_frac_6h", "carb_ewm_hl2h", "ice_slope_30m", "ice_now",
]


def compute_causal_ice(host: str, start: pd.Timestamp, end: pd.Timestamp, *,
                       isf: float, tz: str, lag_steps: int = 6) -> pd.DataFrame:
    """ICE on the CAUSAL fixed-lag-smoothed substrate over [start, end].

    Reuses `ice_rts.compute_ice` for the (already-causal) insulin activity and the
    5-min grid, then replaces its RTS velocity with a fixed-lag causal velocity so
    the whole ICE trace is deployment-faithful. Columns: ice (mg/dL/min), in_gap.
    """
    d0 = compute_ice(host, start, end, isf=isf, tz=tz)
    grid, act, in_gap = d0.index, d0["act"], d0["in_gap"]
    g = load_glucose_cache(find_glucose_cache(host))
    bg = (g["bg"] if "bg" in g else g.iloc[:, 0]).dropna().sort_index()
    bg = bg[~bg.index.duplicated()]
    bg = bg[(bg.index >= start - pd.Timedelta("2h")) & (bg.index <= end + pd.Timedelta("1h"))]
    _, vel = fixed_lag_smooth(bg.index.asi8 / 1e9, bg.to_numpy(), lag_steps=lag_steps)
    v = pd.Series(vel, index=bg.index).reindex(grid, method="nearest", tolerance=pd.Timedelta("15min"))
    ice = v + isf * act
    ice[in_gap.astype(bool)] = np.nan
    return pd.DataFrame({"ice": ice, "in_gap": in_gap})


def build_ice_features(ice_df: pd.DataFrame, *, egp_win: int = 96):
    """Trailing positive-ICE features + time context. Returns (features_df, carb).

    `carb` is the EGP-baseline-subtracted positive ICE rate (mg/dL/min) — the
    carb-appearance signal used for both features and the target. All feature
    windows are TRAILING (causal at the feature level; the ICE itself is causal via
    the fixed-lag substrate). `egp_win` is the rolling-median EGP baseline width
    (bins; 96 = ±4h).
    """
    idx = ice_df.index
    ice = ice_df["ice"]
    base = ice.rolling(egp_win, center=True, min_periods=30).median()
    carb = (ice - base).clip(lower=0)
    F = pd.DataFrame(index=idx)
    hr = idx.hour + idx.minute / 60.0
    F["hour_sin"] = np.sin(2 * np.pi * hr / 24)
    F["hour_cos"] = np.cos(2 * np.pi * hr / 24)
    F["dow"] = idx.dayofweek
    F["is_weekend"] = (idx.dayofweek >= 5).astype(int)
    for h, b in [(1, 12), (2, 24), (4, 48), (6, 72)]:
        F[f"carb_sum_{h}h"] = carb.rolling(b, min_periods=1).sum() * 5.0     # mg/dL integrated
    F["carb_max_6h"] = carb.rolling(72, min_periods=1).max()
    F["carb_frac_6h"] = (carb > 0.5).rolling(72, min_periods=1).mean()       # frac of recent time absorbing
    F["carb_ewm_hl2h"] = carb.ewm(halflife=24, min_periods=1).mean()         # recency-weighted load
    F["ice_slope_30m"] = ice.diff().rolling(6, min_periods=2).mean()
    F["ice_now"] = ice
    if "in_gap" in ice_df:
        F["in_gap"] = ice_df["in_gap"].astype(int)
    return F.replace([np.inf, -np.inf], np.nan), carb


def make_target(carb: pd.Series, *, h0: int = 3, h1: int = 21) -> pd.Series:
    """Continuous target: mean positive-carb-ICE over the FORWARD window [+h0,+h1]
    bins (default +15..+105 min). This is the anticipated near-future carb pressure.
    """
    import warnings
    c = carb.to_numpy()
    n = len(c)
    y = np.full(n, np.nan)
    with warnings.catch_warnings():  # all-NaN forward windows (CGM gaps) -> NaN, dropped downstream
        warnings.simplefilter("ignore", category=RuntimeWarning)
        for i in range(n - h1):
            y[i] = np.nanmean(c[i + h0:i + h1])
    return pd.Series(y, index=carb.index)


def _gbr(**kw):
    from sklearn.ensemble import GradientBoostingRegressor
    params = dict(n_estimators=200, max_depth=3, subsample=0.7, random_state=0)
    params.update(kw)
    return GradientBoostingRegressor(**params)


def walk_forward_eval(F: pd.DataFrame, y: pd.Series, *, feats=FEATURE_COLS,
                      blocks: int = 5, embargo: int = 21, **gbr_kw):
    """Honest out-of-sample eval: expanding train, `blocks` sequential FUTURE test
    blocks over the back half, with an `embargo` gap (bins) so no target straddles
    the split. Returns (r2_list, spearman_list) across the blocks.
    """
    from sklearn.metrics import r2_score
    from scipy.stats import spearmanr
    D = pd.concat([F[feats], y.rename("__y")], axis=1)
    if "in_gap" in F:
        D = D[F["in_gap"] == 0]
    D = D.dropna().reset_index(drop=True)
    n = len(D)
    r2s, sps = [], []
    for bi in range(blocks):
        te0 = int(n * (0.5 + 0.5 * bi / blocks))
        te1 = int(n * (0.5 + 0.5 * (bi + 1) / blocks))
        tr = te0 - embargo
        if tr < int(n * 0.3):
            continue
        m = _gbr(**gbr_kw).fit(D.iloc[:tr][feats], D.iloc[:tr]["__y"])
        p = m.predict(D.iloc[te0:te1][feats])
        yy = D.iloc[te0:te1]["__y"].to_numpy()
        r2s.append(r2_score(yy, p))
        sps.append(spearmanr(yy, p).correlation)
    return r2s, sps


def train_carb_pressure_model(F: pd.DataFrame, y: pd.Series, *, feats=FEATURE_COLS, **gbr_kw):
    """Fit a GradientBoosting regressor on the given (feature, target) rows (drops
    gaps + NaNs). Returns the fitted model. Caller is responsible for time-ordering:
    to stay leak-free, fit on rows STRICTLY BEFORE the prediction/sim window.
    """
    D = pd.concat([F[feats], y.rename("__y")], axis=1)
    if "in_gap" in F:
        D = D[F["in_gap"] == 0]
    D = D.dropna()
    return _gbr(**gbr_kw).fit(D[feats], D["__y"])


def predict_to_offset_csv(model, F_test: pd.DataFrame, out_path: str, *,
                          feats=FEATURE_COLS, scale: float, pctl_thr: float = 60.0,
                          cap: float = 45.0, tz: str = "UTC") -> pd.DataFrame:
    """Predict carb pressure on F_test and write a TRANSIENT forecast-offset CSV
    (time, offset_mgdl) for `loop-eval simulate --candidate-forecast-offset-csv`.

    offset = clip(scale * max(0, p - p_thr), 0, cap), where p_thr is the
    `pctl_thr`-th percentile of the predicted pressure. The threshold is ESSENTIAL:
    raw predictions regress toward the mean and are always positive, so an
    un-thresholded offset is a constant positive bias => persistent over-dosing.
    Thresholding makes the offset fire only when anticipation is above-typical.

    Rows with any missing feature (e.g. CGM gaps) are dropped from the CSV (the sim
    treats missing timestamps as 0 offset). Returns the written DataFrame.
    """
    D = F_test.copy()
    if "in_gap" in D:
        D = D[D["in_gap"] == 0]
    D = D.dropna(subset=list(feats))
    p = np.clip(model.predict(D[feats]), 0, None)
    p_thr = np.percentile(p, pctl_thr)
    off = np.clip(scale * np.clip(p - p_thr, 0, None), 0, cap)
    ts = D.index.tz_convert(tz).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    out = pd.DataFrame({"time": ts, "offset": np.round(off, 2)})
    out.to_csv(out_path, index=False, header=False)
    return out


if __name__ == "__main__":  # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser(description="Walk-forward eval of the carb-pressure predictor.")
    ap.add_argument("host")
    ap.add_argument("--isf", type=float, required=True)
    ap.add_argument("--tz", default="America/Chicago")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    a = ap.parse_args()
    tz = a.tz
    icf = compute_causal_ice(a.host, pd.Timestamp(a.start, tz=tz), pd.Timestamp(a.end, tz=tz),
                             isf=a.isf, tz=tz)
    F, carb = build_ice_features(icf)
    y = make_target(carb)
    r2, sp = walk_forward_eval(F, y)
    print(f"{a.host}  {a.start}->{a.end}  ISF{a.isf}")
    print(f"  time+recent-ICE  walk-forward  R2 {np.mean(r2):.3f}  Spearman {np.mean(sp):.3f}")
    r2t, spt = walk_forward_eval(F, y, feats=["hour_sin", "hour_cos", "dow", "is_weekend"])
    print(f"  time-only        walk-forward  R2 {np.mean(r2t):.3f}  Spearman {np.mean(spt):.3f}")
