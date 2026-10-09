"""Was the schedule really running through a basal-record gap? Check against Loop's own IOB.

Loop's recorded insulinOnBoard is NET of the scheduled basal and built from what the pump
reported delivering. Our net IOB fills every uncovered minute with the schedule. Across a gap:
  - schedule really ran  -> both IOBs move together: d_obs = d(ours - loop) ~ 0
  - nothing delivered    -> Loop's IOB falls below ours by the schedule-fill insulin still on
    board, d_if_none (computed from the fill alone)
d is measured from the last decision before the gap to the first decision >= LAG_MIN after it.
A gap is classified only when d_if_none >= MIN_SIGNAL_U, so the two outcomes are separable;
the per-gap noise is about +-0.65 of d_if_none at the 10th/90th percentile (i001, 532 gaps).
"""
from __future__ import annotations
import numpy as np

MIN_GAP_MIN = 60
LAG_MIN = 20
MIN_SIGNAL_U = 0.3
RAN, NONE, UNKNOWN, RAN_BY_DONOR = "ran", "none", "unknown", "ran_by_donor"


def gap_runs(covered: np.ndarray, min_len=MIN_GAP_MIN):
    """(a, b) index pairs of uncovered runs at least `min_len` minutes long."""
    edges = np.flatnonzero(np.diff(np.r_[0, (~covered).astype(int), 0]))
    return [(a, b) for a, b in zip(edges[::2], edges[1::2]) if b - a >= min_len]


def classify(gm, u_total, sched, covered, kernel, loop_t, loop_iob):
    """Per-gap status (ran / none / unknown) with the evidence. `gm` grid in int64 ns,
    `u_total` and `sched` in U/min on the grid (u_total with the schedule fill), loop_t int64 ns."""
    n = len(gm)
    net = np.convolve(u_total - sched, kernel)[:n]
    fill_only = np.convolve(np.where(covered, 0.0, sched), kernel)[:n]
    diff = np.interp(loop_t, gm, net) - loop_iob
    out = []
    for a, b in gap_runs(covered):
        s, e = gm[a], gm[min(b, n - 1)]
        i0 = np.searchsorted(loop_t, s) - 1
        i1 = np.searchsorted(loop_t, e + LAG_MIN * 6e10)
        status, d_obs, d_none = UNKNOWN, np.nan, np.nan
        if 0 <= i0 and i1 < len(loop_t) and s - loop_t[i0] <= 15 * 6e10 and loop_t[i1] - e <= (LAG_MIN + 15) * 6e10:
            d_obs = float(diff[i1] - diff[i0])
            d_none = float(np.interp(loop_t[i1], gm, fill_only) - np.interp(loop_t[i0], gm, fill_only))
            if d_none >= MIN_SIGNAL_U:
                status = NONE if d_obs / d_none > 0.5 else RAN
        out.append((a, b, status, d_obs, d_none))
    return out
