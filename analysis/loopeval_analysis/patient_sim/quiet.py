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


def tail_anatomy(cgm: pd.Series, events: np.ndarray) -> dict:
    """Big quiet-window steps: how many, and are they isolated spikes (up-then-down within one reading)
    or sustained (the next steps continue the same way)?"""
    cgm = cgm.dropna().sort_index(); t = cgm.index.values; v = cgm.to_numpy()
    ev = np.sort(events); k = np.searchsorted(ev, t, side="right") - 1
    last = np.where(k >= 0, ev[np.clip(k, 0, None)], np.datetime64("1970-01-01"))
    quiet = (t - last) > np.timedelta64(4, "h")
    dt = np.diff(t) / np.timedelta64(1, "m"); d = np.diff(v)
    ok = quiet[1:] & quiet[:-1] & (dt >= 4) & (dt <= 6)
    n = int(ok.sum())
    big = np.where(ok & (np.abs(d) >= 12))[0]
    spike = sum(1 for i in big if i + 1 < len(d) and d[i] * d[i + 1] < 0 and abs(d[i + 1]) >= 0.6 * abs(d[i]))
    sust = sum(1 for i in big if i + 2 < len(d) and np.sign(d[i + 1]) == np.sign(d[i]) and np.sign(d[i + 2]) == np.sign(d[i]))
    up = int((d[big] > 0).sum())
    return dict(n_steps=n, big_per_1000=1000 * len(big) / max(n, 1), spike_share=spike / max(len(big), 1),
                sustained_share=sust / max(len(big), 1), up_share=up / max(len(big), 1))


def donor_tail(alias: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32") -> dict:
    g = json.load(open(ice_root / "full" / alias / "glucose.json"))
    cgm = pd.Series([x["quantity"] for x in g], index=pd.to_datetime([x["startDate"] for x in g]).tz_localize(None)).sort_index()
    cgm = cgm[~cgm.index.duplicated()]
    m = pd.read_parquet(ice_root / "meals" / f"{alias}.parquet")
    doses = json.load(open(ice_root / "full" / alias / "doses.json"))
    man = [pd.Timestamp(x["startDate"]).tz_localize(None) for x in doses if x["deliveryType"] == "bolus" and not x.get("automatic")]
    ev = np.array(list(pd.to_datetime(m.onset).dt.tz_localize(None).values) + [np.datetime64(x) for x in man], dtype="datetime64[ns]")
    return dict(alias=alias, **tail_anatomy(cgm, ev))


def sim_tail(run: Path) -> dict:
    tr = pickle.load(open(run / "truth.pkl", "rb")); meta = json.load(open(run / "meta.json"))
    cgm = tr["cgm"].sort_index(); cgm = cgm[cgm.index >= meta.get("burn_end", 1800)]
    cgm.index = (EPOCH + pd.to_timedelta(cgm.index, unit="m")).tz_localize(None)
    beh = pd.DataFrame(tr["behavior"], columns=["m", "k", "g", "x"])
    ev_m = list(beh[beh.k.isin(["meal", "snack", "rescue", "retreat", "proactive", "ex_carbs", "free_bolus", "correction", "entry"])].m)
    ev = np.array([np.datetime64((EPOCH + pd.Timedelta(minutes=float(x))).tz_localize(None)) for x in ev_m], dtype="datetime64[ns]")
    P = pickle.load(open(run / "person.pkl", "rb"))
    return dict(alias=run.name, sensor=P.sensor, **tail_anatomy(cgm, ev))


def excursions(t: np.ndarray, v: np.ndarray, hour: np.ndarray, quiet: np.ndarray) -> pd.DataFrame:
    """Monotone runs inside quiet windows that contain a step >= 12 mg/dL/5 min: total excursion,
    duration, local hour, starting glucose, direction."""
    dt = np.diff(t) / np.timedelta64(1, "m"); d = np.diff(v)
    ok = quiet[1:] & quiet[:-1] & (dt >= 4) & (dt <= 6)
    rows, i, n = [], 0, len(d)
    while i < n:
        if not ok[i] or d[i] == 0: i += 1; continue
        sgn = np.sign(d[i]); j = i
        while j + 1 < n and ok[j + 1] and np.sign(d[j + 1]) == sgn: j += 1
        seg = d[i:j + 1]
        if np.abs(seg).max() >= 12:
            rows.append(dict(size=float(seg.sum()), minutes=5 * len(seg), hour=float(hour[i]), g0=float(v[i]), up=bool(sgn > 0)))
        i = j + 1
    return pd.DataFrame(rows)


def donor_excursions(alias: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32") -> pd.DataFrame:
    s = pd.read_parquet(ice_root / "steps" / f"{alias}.parquet", columns=["t1", "bg1", "hour"]).sort_values("t1")
    t = s.t1.dt.tz_localize(None).values; v = s.bg1.to_numpy(); h = s.hour.to_numpy()
    m = pd.read_parquet(ice_root / "meals" / f"{alias}.parquet")
    doses = json.load(open(ice_root / "full" / alias / "doses.json"))
    man = [pd.Timestamp(x["startDate"]).tz_localize(None) for x in doses if x["deliveryType"] == "bolus" and not x.get("automatic")]
    ev = np.sort(np.array(list(pd.to_datetime(m.onset).dt.tz_localize(None).values) + [np.datetime64(x) for x in man], dtype="datetime64[ns]"))
    k = np.searchsorted(ev, t, side="right") - 1
    last = np.where(k >= 0, ev[np.clip(k, 0, None)], np.datetime64("1970-01-01"))
    q = (t - last) > np.timedelta64(4, "h")
    E = excursions(t, v, h, q)
    E["alias"] = alias
    for a, b in ((0, 6), (6, 12), (12, 18), (18, 24)):
        E[f"qh_{a}"] = float((q & (h >= a) & (h < b)).sum() * 5 / 60)
    return E


def sim_excursions(run: Path) -> pd.DataFrame:
    tr = pickle.load(open(run / "truth.pkl", "rb")); meta = json.load(open(run / "meta.json"))
    c = tr["cgm"].dropna().sort_index(); c = c[c.index >= meta.get("burn_end", 1800)]
    tm = c.index.to_numpy().astype(float)
    t = (EPOCH + pd.to_timedelta(tm, unit="m")).tz_localize(None).values
    beh = pd.DataFrame(tr["behavior"], columns=["m", "k", "g", "x"])
    evm = np.sort(beh[beh.k.isin(["meal", "snack", "rescue", "retreat", "proactive", "ex_carbs", "free_bolus", "correction", "entry"])].m.to_numpy().astype(float))
    k = np.searchsorted(evm, tm, side="right") - 1
    quiet = (k < 0) | ((tm - np.where(k >= 0, evm[np.clip(k, 0, None)], -1e18)) > 240)
    h = (tm % 1440) / 60
    E = excursions(t, c.to_numpy(), h, quiet)
    E["alias"] = run.name
    for a, b in ((0, 6), (6, 12), (12, 18), (18, 24)):
        E[f"qh_{a}"] = float((quiet & (h >= a) & (h < b)).sum() * 5 / 60)
    return E
