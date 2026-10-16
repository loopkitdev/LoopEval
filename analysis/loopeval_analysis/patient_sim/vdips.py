"""V-shaped CGM dips by local hour — the same detector for donors and simulated people.

A V-dip: from a point, CGM falls >= DROP mg/dL within 30 min and comes back within RECOVER of the start
by 60 min after the trough, with no eating event or manual bolus within 3 h before. Pressure-induced
sensor attenuation (compression lows) is the textbook source and is mostly nocturnal (evidence/03 §2.6),
so the NIGHT excess over the DAY rate is an estimate of the compression rate; the hour profile as a whole
is a validation target for every source of fast dips (sensor, activity).
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from .world import EPOCH

DROP, RECOVER = 25.0, 10.0


def _dips(t_min: np.ndarray, v: np.ndarray, hour: np.ndarray, blocked: np.ndarray) -> list:
    """t_min minutes (monotone, ~5-min cadence), v CGM, hour local hour, blocked bool (event within 3 h)."""
    out, i, n = [], 0, len(v)
    while i < n - 3:
        if blocked[i]:
            i += 1; continue
        j_end = np.searchsorted(t_min, t_min[i] + 30, side="right")
        seg = v[i:j_end]
        if len(seg) >= 3 and v[i] - seg.min() >= DROP:
            k = i + int(np.argmin(seg))
            r_end = np.searchsorted(t_min, t_min[k] + 60, side="right")
            back = v[k:r_end]
            if len(back) and back.max() >= v[i] - RECOVER:
                out.append(hour[i]); i = r_end; continue
        i += 1
    return out


def donor(alias: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32") -> dict | None:
    s = pd.read_parquet(ice_root / "steps" / f"{alias}.parquet", columns=["t1", "bg1", "hour", "carbs_g", "bolus_manual_u"])
    s = s.sort_values("t1")
    t = (s.t1.astype("int64") // 60_000_000_000).to_numpy().astype(float)
    m = pd.read_parquet(ice_root / "meals" / f"{alias}.parquet")
    ev = np.sort(np.r_[(pd.to_datetime(m.onset).astype("int64") // 60_000_000_000).to_numpy().astype(float),
                       t[s.bolus_manual_u.fillna(0).to_numpy() > 0]])
    k = np.searchsorted(ev, t, side="right") - 1
    blocked = (k >= 0) & ((t - np.where(k >= 0, ev[np.clip(k, 0, None)], -1e18)) < 180)
    h = s.hour.to_numpy()
    d = _dips(t, s.bg1.to_numpy(), h, blocked)
    return _summ(alias, d, h)


def simulated(run: Path) -> dict | None:
    tr = pickle.load(open(run / "truth.pkl", "rb"))
    meta = json.load(open(run / "meta.json"))
    c = tr["cgm"].dropna().sort_index()
    c = c[c.index >= meta.get("burn_end", 1800)]
    t = c.index.to_numpy().astype(float); v = c.to_numpy()
    h = (t % 1440) / 60.0
    beh = pd.DataFrame(tr["behavior"], columns=["m", "k", "g", "x"])
    ev = np.sort(beh[beh.k.isin(["meal", "snack", "rescue", "retreat", "proactive", "ex_carbs", "free_bolus",
                                 "correction", "entry"])].m.to_numpy().astype(float))
    k = np.searchsorted(ev, t, side="right") - 1
    blocked = (k >= 0) & ((t - np.where(k >= 0, ev[np.clip(k, 0, None)], -1e18)) < 180)
    return _summ(run.name, _dips(t, v, h, blocked), h)


def _summ(alias, d, h) -> dict:
    d = np.asarray(d)
    night_h = np.mean((h >= 0) & (h < 6)) * len(h) * 5 / 60       # hours of data at night (5-min samples)
    day_h = np.mean((h >= 9) & (h < 21)) * len(h) * 5 / 60
    n_night = int(((d >= 0) & (d < 6)).sum()); n_day = int(((d >= 9) & (d < 21)).sum())
    return dict(alias=alias, night_per_6h=6 * n_night / max(night_h, 1), day_per_6h=6 * n_day / max(day_h, 1),
                night_excess_per_night=6 * n_night / max(night_h, 1) - 6 * n_day / max(day_h, 1))
