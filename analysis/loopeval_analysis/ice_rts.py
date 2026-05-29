"""ICE on the RTS-smoothed substrate — reusable primitive.

ICE(t) = v_cgm(t) + isf * activity_conv(t)        ( = v_cgm - v_insulin_on_bg )
  v_cgm         : RTS-Kalman-smoothed actual-BG velocity (mg/dL/min), matches the
                  sim substrate (loopeval_analysis.kalman, Swift-default params).
  activity_conv : net-basal doses convolved with the standard exponential insulin
                  ACTIVITY kernel (6h DIA / 75min peak), in U/min. Linear in ISF.

ICE>0 = BG rising faster than insulin lowers it (carbs/EGP); ICE<0 = dropping
faster than insulin alone explains (sensitive). `act` (=activity_conv) is returned
so callers can recompute ICE at any ISF cheaply: ice(isf) = v_cgm + isf*act.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from .glucose import (load_glucose_cache, find_glucose_cache,
                      load_doses_cache, find_doses_cache, find_therapy_cache,
                      effective_delivery_rate)
from .iob import _build_dose_events
from .ice_sim import percent_effect_remaining
from .kalman import rts_smooth_series

STEP_SEC = 300.0
STEP_MIN = 5.0
DIA_SEC = 6 * 3600


def compute_ice(host: str, start: pd.Timestamp, end: pd.Timestamp, *,
                isf: float = 70.0, max_gap: pd.Timedelta = pd.Timedelta("15min"),
                tz: str = "America/Chicago",
                insulin_mode: str = "net") -> pd.DataFrame:
    """ICE on a 5-min grid over [start, end]. Columns: ice, v_cgm, act, in_gap.

    insulin_mode:
      "net"      — activity from NET-basal doses (temp rate minus scheduled; a suspend
                   is NEGATIVE net delivery). Matches Loop's IOB convention; ICE then
                   captures carbs + EGP-*deviation*-from-baseline. During a suspend the
                   net activity collapses (can flip sign), so -v_cgm/act blows up — the
                   inflated peak-ISF artifact.
      "absolute" — activity from PHYSICAL delivered insulin (boluses at full volume +
                   effective basal rate incl. scheduled infill; a suspend is 0, never
                   negative). The local-ISF denominator no longer collapses during a
                   suspend. Trade-off: ICE absorbs the scheduled-basal lowering that the
                   body's baseline EGP normally balances, so mean ICE shifts up by
                   ~isf*(mean basal activity); the carb/EGP reading of ICE changes.
    """
    grid = pd.date_range(start, end, freq="5min", tz=tz)

    # v_cgm: RTS-smoothed velocity mapped to the grid (NaN in CGM gaps)
    g = load_glucose_cache(find_glucose_cache(host))
    bg = (g["bg"] if "bg" in g else g.iloc[:, 0]).dropna().sort_index()
    bg = bg[(bg.index >= start - pd.Timedelta("1h")) & (bg.index <= end + pd.Timedelta("1h"))]
    sm = rts_smooth_series(bg)
    v_cgm = sm["v_cgm"].reindex(grid, method="nearest", tolerance=max_gap)
    in_gap = v_cgm.isna()

    doses = load_doses_cache(find_doses_cache(host))
    therapy = find_therapy_cache(host)
    # Insulin ACTIVITY kernel: per-minute rate of effect delivery for 1 U.
    n_k = int(DIA_SEC / STEP_SEC) + 2
    delivered = np.array([1.0 - percent_effect_remaining(i * STEP_SEC) for i in range(n_k)])
    activity_kernel = np.gradient(delivered, STEP_MIN)            # per-minute

    if insulin_mode == "absolute":
        # Physical delivery on a 6h-lookback grid: effective basal (U/hr, incl.
        # scheduled infill, suspend=0) -> U/step, plus full-volume boluses.
        dgrid = pd.date_range(start - pd.Timedelta(hours=6), end, freq="5min", tz=tz)
        step_hr = STEP_MIN / 60.0
        eff = effective_delivery_rate(doses, therapy, target_index=dgrid, tz=tz)
        dose_u = np.nan_to_num(eff.to_numpy(dtype=float), nan=0.0) * step_hr
        bol = doses[doses["delivery_type"] != "basal"]
        if len(bol):
            bi = np.round(((bol.index - dgrid[0]) / pd.Timedelta("5min")).to_numpy()).astype(int)
            ok = (bi >= 0) & (bi < len(dgrid))
            np.add.at(dose_u, bi[ok], bol["volume"].to_numpy(dtype=float)[ok])
        act_full = np.convolve(dose_u, activity_kernel)[:len(dgrid)]
        act = pd.Series(act_full, index=dgrid).reindex(grid)        # U/min
    elif insulin_mode == "net":
        events = _build_dose_events(doses, therapy)
        ev_t = pd.DatetimeIndex([e.start for e in events]).tz_convert(tz)
        ev_u = np.array([e.net_units for e in events], dtype=float)
        keep = (ev_t >= start - pd.Timedelta(hours=6)) & (ev_t <= end)
        ev_t, ev_u = ev_t[keep], ev_u[keep]
        bin_idx = ((ev_t - grid[0]) / pd.Timedelta("5min")).astype(int)
        dose_u = np.zeros(len(grid))
        ok = (bin_idx >= 0) & (bin_idx < len(grid))
        np.add.at(dose_u, np.asarray(bin_idx)[ok], ev_u[ok])
        act = pd.Series(np.convolve(dose_u, activity_kernel)[:len(grid)], index=grid)  # U/min
    else:
        raise ValueError(f"insulin_mode must be 'net' or 'absolute', got {insulin_mode!r}")

    ice = v_cgm + isf * act
    ice[in_gap] = np.nan
    return pd.DataFrame({"ice": ice, "v_cgm": v_cgm, "act": act, "in_gap": in_gap})
