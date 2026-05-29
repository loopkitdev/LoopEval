"""2D constant-velocity Kalman filter + RTS backward smoother for CGM.

Python port of the Swift `KalmanSmoother` (EvalCore/Metrics/KalmanSmoother.swift)
used by the simulator's RTS substrate, with the same defaults so analysis matches
the sim's smoothed-glucose space:

  State x = [BG (mg/dL), velocity (mg/dL/SECOND)]
  Transition F = [[1, dt], [0, 1]]   (dt in seconds, irregular steps handled)
  Process noise Q = diag(processNoiseQ, velocityNoiseQ) = diag(1.0, 1e-4)
  Observation H = [1, 0], noise R = observationNoiseR = 4.0  (≈2 mg/dL std)
  x0 = [bg[0], 0], P0 = [[100, 0], [0, 1]]

The RTS backward pass makes the smoothed BG at t informed by FUTURE samples —
identical to the sim substrate (deliberate; not decision-time-causal). Returns the
smoothed BG and the velocity state converted to mg/dL/MINUTE (×60).
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def _forward_pass(t, z, Q, observation_noise_r, observation_noise_rel):
    """Forward Kalman filter. Returns (xs, Ps, xpreds, Ppreds, Fs).

    observation_noise_rel: if not None, R_k = observation_noise_r + (rel*z[k])**2
      (HETEROSKEDASTIC — models multiplicative CGM noise that grows with BG, matching
      log-normal glucose). None => homoskedastic R=observation_noise_r (default/legacy).
    """
    n = len(z)
    H = np.array([[1.0, 0.0]]); I2 = np.eye(2)
    xs = np.zeros((n, 2)); Ps = np.zeros((n, 2, 2))
    xpreds = np.zeros((n, 2)); Ppreds = np.zeros((n, 2, 2)); Fs = np.zeros((n, 2, 2))
    xs[0] = [z[0], 0.0]; Ps[0] = [[100.0, 0.0], [0.0, 1.0]]
    xpreds[0] = xs[0]; Ppreds[0] = Ps[0]; Fs[0] = I2
    for k in range(1, n):
        dt = max(t[k] - t[k - 1], 1.0)
        F = np.array([[1.0, dt], [0.0, 1.0]]); Fs[k] = F
        xpred = F @ xs[k - 1]; Ppred = F @ Ps[k - 1] @ F.T + Q
        xpreds[k] = xpred; Ppreds[k] = Ppred
        R = observation_noise_r if observation_noise_rel is None else \
            observation_noise_r + (observation_noise_rel * z[k]) ** 2
        y = z[k] - (H @ xpred)[0]
        S = (H @ Ppred @ H.T)[0, 0] + R
        K = (Ppred @ H.T)[:, 0] / S
        xs[k] = xpred + K * y
        Ps[k] = (I2 - np.outer(K, H[0])) @ Ppred
    return xs, Ps, xpreds, Ppreds, Fs


def rts_smooth(times_sec: np.ndarray, bg: np.ndarray, *,
               process_noise_q: float = 1.0,
               velocity_noise_q: float = 1e-4,
               observation_noise_r: float = 4.0,
               observation_noise_rel: float | None = None,
               smooth: bool = True):
    """Forward Kalman + RTS smoother over (times_sec, bg). Both 1D, sorted by time.

    Returns (bg_smoothed, velocity_mgdl_per_min), aligned with the inputs.

    smooth=True (default): RTS backward pass -> each estimate uses FUTURE samples
      (matches the sim substrate; NOT decision-time causal).
    smooth=False: forward Kalman FILTER only -> strictly causal (no leak).
    observation_noise_rel: heteroskedastic R (see _forward_pass). None = legacy homoskedastic.
    """
    t = np.asarray(times_sec, dtype=float); z = np.asarray(bg, dtype=float); n = len(z)
    if n == 0:
        return np.array([]), np.array([])
    Q = np.array([[process_noise_q, 0.0], [0.0, velocity_noise_q]])
    xs, Ps, xpreds, Ppreds, Fs = _forward_pass(t, z, Q, observation_noise_r, observation_noise_rel)
    if not smooth:
        return xs[:, 0], xs[:, 1] * 60.0
    xsm = xs.copy()
    for k in range(n - 2, -1, -1):
        Pp = Ppreds[k + 1]
        try:
            C = Ps[k] @ Fs[k + 1].T @ np.linalg.inv(Pp)
        except np.linalg.LinAlgError:
            C = Ps[k] @ Fs[k + 1].T @ np.linalg.pinv(Pp)
        xsm[k] = xs[k] + C @ (xsm[k + 1] - xpreds[k + 1])
    return xsm[:, 0], xsm[:, 1] * 60.0


def fixed_lag_smooth(times_sec: np.ndarray, bg: np.ndarray, *, lag_steps: int = 6,
                     process_noise_q: float = 1.0, velocity_noise_q: float = 1e-4,
                     observation_noise_r: float = 4.0,
                     observation_noise_rel: float | None = None):
    """CAUSAL fixed-lag smoother: estimate at k uses data through k+lag_steps ONLY.

    RTS-quality denoising for every sample older than `lag_steps` while remaining causal
    if the consumer guards out the most recent `lag_steps`. Reuses one forward pass; for
    each k runs the RTS backward recursion from k+lag back to k. O(N*lag).
    Returns (bg_fl, velocity_mgdl_per_min).
    """
    t = np.asarray(times_sec, dtype=float); z = np.asarray(bg, dtype=float); n = len(z)
    if n == 0:
        return np.array([]), np.array([])
    Q = np.array([[process_noise_q, 0.0], [0.0, velocity_noise_q]])
    xs, Ps, xpreds, Ppreds, Fs = _forward_pass(t, z, Q, observation_noise_r, observation_noise_rel)
    out = xs.copy()
    for k in range(n):
        end = min(k + lag_steps, n - 1)
        sm = xs[end].copy()
        for j in range(end - 1, k - 1, -1):
            Pp = Ppreds[j + 1]
            try:
                C = Ps[j] @ Fs[j + 1].T @ np.linalg.inv(Pp)
            except np.linalg.LinAlgError:
                C = Ps[j] @ Fs[j + 1].T @ np.linalg.pinv(Pp)
            sm = xs[j] + C @ (sm - xpreds[j + 1])
        out[k] = sm
    return out[:, 0], out[:, 1] * 60.0


def rts_smooth_series(bg_series: pd.Series, **kw) -> pd.DataFrame:
    """Convenience wrapper over a tz-aware BG Series. Returns a DataFrame indexed
    like the input with columns: bg_smoothed, v_cgm (mg/dL/min)."""
    s = bg_series.dropna().sort_index()
    times_sec = s.index.asi8 / 1e9   # int64 ns -> seconds (UTC-based, tz-agnostic)
    bgs, vel = rts_smooth(times_sec, s.to_numpy(), **kw)
    return pd.DataFrame({"bg_smoothed": bgs, "v_cgm": vel}, index=s.index)
