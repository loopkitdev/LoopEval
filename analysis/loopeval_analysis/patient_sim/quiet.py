"""CGM increments in QUIET windows — the same measure for donors and simulated people.

A quiet window is a stretch with no eating event (labeled pulse / simulated meal, snack, rescue) and no
manual bolus in the 4 h before it. There, the 5-min CGM step is mostly sensor noise plus slow physiology,
so its SD and autocorrelation are the evidence that sizes the sensor's noise model (COMPONENTS D3) —
instead of tuning the sensor to whatever the full cohort comparison misses.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from .world import EPOCH

LAGS = range(1, 13)


def _quiet_stats(cgm: pd.Series, events: np.ndarray) -> dict | None:
    """cgm: datetime-indexed readings; events: datetime64 array of disturbance times."""
    cgm = cgm.dropna().sort_index()
    t = cgm.index.values
    ev = np.sort(events)
    k = np.searchsorted(ev, t, side="right") - 1
    last = np.where(k >= 0, ev[np.clip(k, 0, None)], np.datetime64("1970-01-01"))
    quiet = (t - last) > np.timedelta64(4, "h")
    dt = np.diff(t) / np.timedelta64(1, "m")
    v = cgm.to_numpy()
    runs, cur = [], [v[0]] if quiet[0] else []
    for i in range(1, len(v)):
        if quiet[i] and quiet[i - 1] and 4 <= dt[i - 1] <= 6:
            if not cur: cur = [v[i - 1]]
            cur.append(v[i])
        else:
            if len(cur) >= 13: runs.append(np.array(cur))
            cur = []
    if len(cur) >= 13: runs.append(np.array(cur))
    if not runs: return None
    d = [np.diff(r) for r in runs]
    alld = np.concatenate(d)
    if len(alld) < 300: return None
    mu = alld.mean(); var = alld.var()
    acf = []
    for lag in LAGS:
        num = sum(float(((x[lag:] - mu) * (x[:-lag] - mu)).sum()) for x in d if len(x) > lag)
        cnt = sum(len(x) - lag for x in d if len(x) > lag)
        acf.append(num / cnt / var if cnt else np.nan)
    return dict(n=len(alld), step_sd=float(alld.std()), kurt=float(pd.Series(alld).kurtosis()),
                **{f"acf{5 * l}": a for l, a in zip(LAGS, acf)})


def donor(alias: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32") -> dict | None:
    g = json.load(open(ice_root / "full" / alias / "glucose.json"))
    cgm = pd.Series([x["quantity"] for x in g], index=pd.to_datetime([x["startDate"] for x in g]).tz_localize(None)).sort_index()
    cgm = cgm[~cgm.index.duplicated()]
    m = pd.read_parquet(ice_root / "meals" / f"{alias}.parquet")
    doses = json.load(open(ice_root / "full" / alias / "doses.json"))
    man = [pd.Timestamp(x["startDate"]).tz_localize(None) for x in doses if x["deliveryType"] == "bolus" and not x.get("automatic")]
    ev = np.array(list(pd.to_datetime(m.onset).dt.tz_localize(None).values) + [np.datetime64(x) for x in man], dtype="datetime64[ns]")
    r = _quiet_stats(cgm, ev)
    return dict(alias=alias, **r) if r else None


def simulated(run: Path) -> dict | None:
    tr = pickle.load(open(run / "truth.pkl", "rb"))
    meta = json.load(open(run / "meta.json"))
    cgm = tr["cgm"].sort_index()
    cgm = cgm[cgm.index >= meta.get("burn_end", 1800)]
    cgm.index = (EPOCH + pd.to_timedelta(cgm.index, unit="m")).tz_localize(None)
    beh = pd.DataFrame(tr["behavior"], columns=["m", "k", "g", "x"])
    # what ice's labeler would see as a pulse or a bolus; walking and sub-gate grazing stay inside quiet
    # windows, as their real counterparts do in donors
    ev_m = list(beh[beh.k.isin(["meal", "snack", "rescue", "retreat", "proactive", "ex_carbs", "free_bolus", "correction", "entry"])].m)
    ev = np.array([np.datetime64((EPOCH + pd.Timedelta(minutes=float(x))).tz_localize(None)) for x in ev_m], dtype="datetime64[ns]")
    r = _quiet_stats(cgm, ev)
    if not r: return None
    P = pickle.load(open(run / "person.pkl", "rb"))
    return dict(alias=run.name, sensor=P.sensor, **r)
