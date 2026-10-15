"""Glucose response to an announced, bolused meal — the same measure for donors and simulated people.

For each eating event with a carb entry and a bolus, and no other eating in the 3 h before: CGM at onset,
the peak rise over the next 3 h, minutes to that peak, and the change at 3 h. Rises per entered gram tie
the meal and insulin components (absorption speed, bioavailability, insulin action, bolus timing) to
what donors' glucose actually does. Donors: ice meal tables (onset, entry_g, bolus_u) + glucose.json.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from .world import EPOCH


def _response(cgm: pd.Series, onset: pd.Timestamp) -> dict | None:
    w = cgm[(cgm.index >= onset - pd.Timedelta(minutes=10)) & (cgm.index <= onset + pd.Timedelta(hours=3))].dropna()
    if len(w) < 24: return None
    b = w[w.index <= onset + pd.Timedelta(minutes=5)]
    if not len(b): return None
    g0 = float(b.iloc[-1])
    after = w[w.index > onset]
    pk = after.idxmax()
    end = after[after.index >= onset + pd.Timedelta(minutes=170)]
    return dict(g0=g0, rise=float(after.max() - g0), t_peak=(pk - onset).total_seconds() / 60,
                d3h=float(end.iloc[0] - g0) if len(end) else np.nan)


def donor(alias: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32") -> pd.DataFrame:
    g = json.load(open(ice_root / "full" / alias / "glucose.json"))
    cgm = pd.Series([x["quantity"] for x in g], index=pd.to_datetime([x["startDate"] for x in g])).sort_index()
    cgm = cgm[~cgm.index.duplicated()]
    m = pd.read_parquet(ice_root / "meals" / f"{alias}.parquet").sort_values("onset")
    rows = []
    prev = None
    for _, r in m.iterrows():
        isolated = prev is None or (r.onset - prev) > pd.Timedelta(hours=3)
        prev = r.onset
        if not (isolated and r.announced and r.entry_g > 0 and r.bolus_u > 0 and not r.rescue): continue
        x = _response(cgm, r.onset)
        if x: rows.append(dict(alias=alias, grams=float(r.entry_g), bolus=float(r.bolus_u), **x))
    return pd.DataFrame(rows)


def simulated(run: Path) -> pd.DataFrame:
    tr = pickle.load(open(run / "truth.pkl", "rb"))
    meta = json.load(open(run / "meta.json"))
    cgm = tr["cgm"].sort_index()
    cgm.index = EPOCH + pd.to_timedelta(cgm.index, unit="m")
    beh = pd.DataFrame(tr["behavior"], columns=["m", "k", "g", "x"]).sort_values("m")
    eats = beh[beh.k.isin(["meal", "snack"])]
    entries = beh[beh.k == "entry"]
    rows = []
    prev = None
    for _, r in eats.iterrows():
        isolated = prev is None or (r.m - prev) > 180
        prev = r.m
        if r.m < meta.get("burn_end", 1800) or not isolated or not (r.x and r.x > 0): continue
        e = entries[(entries.m >= r.m - 60) & (entries.m <= r.m + 60)]
        if not len(e) or not (e.x.iloc[0] and e.x.iloc[0] > 0): continue      # bolused entry
        x = _response(cgm, EPOCH + pd.Timedelta(minutes=float(r.m)))
        if x: rows.append(dict(alias=run.name, grams=float(r.x), eaten=float(r.g), **x))
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame) -> dict:
    df = df[df.grams >= 10]
    return dict(n=len(df), people=df.alias.nunique(), rise_med=df.rise.median(), rise_per10g=(10 * df.rise / df.grams).median(),
                t_peak_med=df.t_peak.median(), d3h_med=df.d3h.median(), g0_med=df.g0.median())
