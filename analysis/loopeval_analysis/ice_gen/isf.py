"""ISF for ICE from eda's yardstick (dist_views/ice/isf_yardstick.py, adopted 2026-10-10), on this role's steps.

The yardstick regresses each quiet hour's glucose change on insulin absorbed (fasting), shrinks it toward the
basal rule from the measured fasting insulin rate, and levels it to the schedule median. It replaces
688 / TDD^0.74 (eda's fit to how people SET their ISF, which as a TDD rule also carries diet).

panel(steps, carbs) builds eda's 5-min panel columns from an ice_gen step table, in PER-BIN units as the
yardstick expects (its fasting rate is the median absorbed U per bin x 12):
  v       glucose change per bin (mg/dL), NaN where the step is not clean (the bad-data screen)
  ia_abs  insulin effect absorbed per bin at `isf` (mg/dL)
  isf     the ISF the steps were extracted at
  cob     announced carbs on board (g), linear absorption over each entry's absorption time (default 3 h)
  manual_bolus_u, disrupted
quiet(panel) is eda's mask: no announced COB, no manual bolus in the prior 4 h, no disruption, finite v.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "dist_views" / "ice"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "dist_views"))

QUIET_BOLUS_H = 4


def panel(steps: pd.DataFrame, carbs: list) -> pd.DataFrame:
    d = steps.copy(); d["slot"] = d.t1.dt.floor("5min"); per_bin = d.dt / 60.0      # h per step -> bins of 5 min
    clean = d.clean.astype(bool)
    g = pd.DataFrame({
        "v": (d.v.where(clean) * 5 / 60).groupby(d.slot).mean(),
        "ia_abs": (d.ia * 5 / 60).groupby(d.slot).mean(),
        "manual_bolus_u": d.bolus_manual_u.groupby(d.slot).sum(),
        "disrupted": d.disrupted.astype(bool).groupby(d.slot).max(),
    })
    idx = pd.date_range(g.index.min(), g.index.max(), freq="5min"); g = g.reindex(idx)
    g["manual_bolus_u"] = g.manual_bolus_u.fillna(0.0); g["disrupted"] = g.disrupted.astype("boolean").fillna(True).astype(bool)
    cob = np.zeros(len(idx)); tn = idx.asi8
    for c in carbs:
        t0 = pd.Timestamp(c["startDate"]).value; dur = float(c.get("absorptionTime") or 10800) * 1e9
        gr = float(c.get("grams") or 0)
        m = (tn >= t0) & (tn < t0 + dur)
        cob[m] += gr * (1 - (tn[m] - t0) / dur)
    g["cob"] = cob
    return g


def quiet(p: pd.DataFrame) -> np.ndarray:
    n = QUIET_BOLUS_H * 12
    recent = pd.Series(p.manual_bolus_u.to_numpy() > 0).rolling(n, min_periods=1).max().to_numpy() > 0
    return (p.cob.to_numpy() <= 0) & ~recent & ~p.disrupted.to_numpy() & p.v.notna().to_numpy()


def yardstick(steps: pd.DataFrame, carbs: list, isf_extracted: float, until=None) -> dict:
    """The yardstick ISF for one donor, on steps before `until` (the hold-out start) only."""
    import isf_yardstick as Y
    s = steps if until is None else steps[steps.t1 < until]
    p = panel(s, carbs); p["isf"] = isf_extracted
    return Y.yardstick(p, quiet(p))
