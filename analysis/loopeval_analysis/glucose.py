"""Glucose loading and daily-outcome metrics from LoopEval's cache layout.

The Nightscout cache stores per-host glucose JSON as a flat list of
{quantity: <mg/dL>, startDate: <ISO8601 Z>, provenanceIdentifier: ...}.
"""
from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np
import pandas as pd


DEFAULT_CACHE_DIR = os.path.expanduser("~/.loop-eval/cache")


def find_glucose_cache(
    host: str,
    cache_dir: str = DEFAULT_CACHE_DIR,
    prefer: str = "longest",
) -> str:
    """Return the path of the best-matching cached glucose JSON for a host.

    The cache filename convention is `glucose_<host>_<startEpoch>_<endEpoch>.json`.
    `prefer="longest"` picks the entry covering the widest time span;
    `prefer="latest"` picks the one with the largest end timestamp.
    """
    pattern = os.path.join(cache_dir, f"glucose_{host}_*.json")
    matches = sorted(glob.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"no glucose cache for {host} in {cache_dir}")

    def span(path: str) -> tuple[int, int, int]:
        stem = os.path.basename(path).removesuffix(".json")
        # glucose_<host>_<startEpoch>_<endEpoch>
        parts = stem.rsplit("_", 2)
        start, end = int(parts[-2]), int(parts[-1])
        return (end - start, end, -start)

    if prefer == "longest":
        return max(matches, key=span)
    if prefer == "latest":
        return max(matches, key=lambda p: span(p)[1])
    raise ValueError(f"unknown prefer mode: {prefer}")


def load_glucose_cache(
    path: str,
    *,
    tz: str = "America/Chicago",
) -> pd.DataFrame:
    """Load a cached glucose JSON into a DataFrame indexed by tz-aware Timestamp.

    Columns: bg (mg/dL float). Sorted ascending, deduplicated on time.
    """
    with open(path) as f:
        data = json.load(f)
    if not data:
        return pd.DataFrame(columns=["bg"])
    times = pd.to_datetime([r["startDate"] for r in data], utc=True)
    bg = np.array([float(r["quantity"]) for r in data])
    df = pd.DataFrame({"bg": bg}, index=times).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df.index = df.index.tz_convert(tz)
    return df


@dataclass
class DailyOutcomes:
    """Per-day glucose-outcome metrics, indexed by local calendar day."""
    df: pd.DataFrame  # index = pd.DatetimeIndex (date only, tz-naive); columns below

    # Column reference (so callers can be type-clean):
    #   n_samples       number of CGM points that fell into the day
    #   tir_70_180      fraction of samples in [70, 180)
    #   t_below_70      fraction < 70
    #   t_below_54      fraction < 54
    #   t_above_180     fraction >= 180
    #   t_above_250     fraction >= 250
    #   mean_bg         mean mg/dL
    #   auc_below_70    mg/dL·min below 70 (Riemann from sample-to-sample spacing)
    #   auc_above_180   mg/dL·min above 180
    #   gv_cv           coefficient of variation (std / mean)

    def __getitem__(self, k):
        return self.df[k]


def daily_outcomes(
    glucose: pd.DataFrame,
    *,
    interval_minutes: float = 5.0,
) -> DailyOutcomes:
    """Bucket per-CGM-sample glucose into local-calendar-day metrics.

    `interval_minutes` is the assumed sample spacing for AUC integration. The
    CGM is ~5 min nominal; we don't try to be too clever about gaps — a sample
    is counted at its observed time. AUC is a sample-count * mg/dL*min product.
    """
    if glucose.empty:
        return DailyOutcomes(df=pd.DataFrame())

    bg = glucose["bg"].astype(float)
    day = bg.index.normalize()  # midnight of local day, same tz

    parts = {}
    parts["n_samples"]      = bg.groupby(day).count()
    parts["mean_bg"]        = bg.groupby(day).mean()
    parts["tir_70_180"]     = ((bg >= 70) & (bg < 180)).groupby(day).mean()
    parts["t_below_70"]     = (bg < 70).groupby(day).mean()
    parts["t_below_54"]     = (bg < 54).groupby(day).mean()
    parts["t_above_180"]    = (bg >= 180).groupby(day).mean()
    parts["t_above_250"]    = (bg >= 250).groupby(day).mean()
    parts["gv_cv"]          = bg.groupby(day).std() / bg.groupby(day).mean()

    # AUC: sum of clip(thr - bg, 0, ...) × dt
    below = np.clip(70.0 - bg, a_min=0.0, a_max=None)
    above = np.clip(bg - 180.0, a_min=0.0, a_max=None)
    parts["auc_below_70"]   = below.groupby(day).sum() * interval_minutes
    parts["auc_above_180"]  = above.groupby(day).sum() * interval_minutes

    df = pd.DataFrame(parts)
    # Drop tz from the index so it merges cleanly with date-indexed series.
    df.index = pd.DatetimeIndex(df.index.tz_localize(None), name="day")
    df = df.sort_index()
    return DailyOutcomes(df=df)


def load_doses_cache(
    path: str,
    *,
    tz: str = "America/Chicago",
) -> pd.DataFrame:
    """Load a cached doses JSON (same naming convention as glucose).

    Columns: ``volume`` (U), ``delivery_type`` (e.g. 'basal', 'bolus'),
    ``automatic`` (bool), ``insulin_type`` (str), ``startDate``, ``endDate``.
    Indexed by ``startDate``. Bolus volumes are total U; basal-style entries
    are total U over their duration (rate × duration). A `volume == 0` basal
    entry is a Loop full-suspend temp basal for that interval.
    """
    with open(path) as f:
        data = json.load(f)
    if not data:
        return pd.DataFrame(columns=["volume", "delivery_type", "automatic", "endDate"])
    starts = pd.to_datetime([r["startDate"] for r in data], utc=True)
    ends = pd.to_datetime([r.get("endDate", r["startDate"]) for r in data], utc=True)
    vols = [float(r.get("volume", 0)) for r in data]
    delivery_types = [r.get("deliveryType", r.get("type", "")) for r in data]
    automatics = [bool(r.get("automatic", False)) for r in data]
    insulin_types = [r.get("insulinType", "") for r in data]
    df = pd.DataFrame(
        {
            "volume": vols,
            "delivery_type": delivery_types,
            "automatic": automatics,
            "insulin_type": insulin_types,
            "endDate": ends,
        },
        index=starts,
    ).sort_index()
    df.index = df.index.tz_convert(tz)
    df["endDate"] = df["endDate"].dt.tz_convert(tz)
    # Compute hourly rate for basal-style entries (volume / duration_hours)
    dur_h = (df["endDate"] - df.index).dt.total_seconds() / 3600.0
    is_basal = df["delivery_type"] == "basal"
    df["rate_uhr"] = np.where(
        is_basal & (dur_h > 0),
        df["volume"] / dur_h,
        np.nan,
    )
    return df


def basal_delivery_timeline(
    doses: pd.DataFrame,
    *,
    interval_minutes: int = 5,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Build a uniform timeline of Loop's basal delivery rate (U/hr).

    For each ``interval_minutes`` bin, the active rate is taken from the
    latest-started ``basal``-type dose whose [startDate, endDate] contains
    the bin start. Returns a DataFrame indexed at the bin starts with one
    column ``rate_uhr``.

    ``rate_uhr == 0`` for a bin means Loop was in full-suspend (0 U/hr temp
    basal) during that bin.
    """
    basals = doses[doses["delivery_type"] == "basal"].copy()
    if basals.empty:
        return pd.DataFrame(columns=["rate_uhr"])
    if start is None:
        start = basals.index.min().floor(f"{interval_minutes}min")
    if end is None:
        end = basals["endDate"].max().ceil(f"{interval_minutes}min")
    timestamps = pd.date_range(start=start, end=end, freq=f"{interval_minutes}min",
                               inclusive="left")
    if len(timestamps) == 0:
        return pd.DataFrame(columns=["rate_uhr"])

    # Vectorized: for each timestamp, binary-search for the last basal whose
    # startDate <= ts AND endDate > ts. Iterate forward with running pointers.
    starts_ns = basals.index.view("int64")
    ends_ns = basals["endDate"].astype("int64").to_numpy()
    rates = basals["rate_uhr"].to_numpy()

    out_rates = np.full(len(timestamps), np.nan)
    # We want, for each ts, the basal with max startDate ≤ ts AND endDate > ts.
    # Doses can overlap; iterate over doses and last-writer-wins for ts in [start, end).
    for i in range(len(basals)):
        s_ns = starts_ns[i]
        e_ns = ends_ns[i]
        # Find first ts >= s_ns
        lo = np.searchsorted(timestamps.view("int64"), s_ns, side="left")
        hi = np.searchsorted(timestamps.view("int64"), e_ns, side="left")
        if lo < hi:
            out_rates[lo:hi] = rates[i]

    return pd.DataFrame({"rate_uhr": out_rates}, index=timestamps)


def find_therapy_cache(
    host: str,
    cache_dir: str = DEFAULT_CACHE_DIR,
    prefer: str = "longest",
) -> str:
    """Locate the best-matching cached therapy JSON for a host."""
    pattern = os.path.join(cache_dir, f"therapy_{host}_*.json")
    matches = sorted(glob.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"no therapy cache for {host} in {cache_dir}")

    def span(path: str) -> tuple[int, int, int]:
        stem = os.path.basename(path).removesuffix(".json")
        parts = stem.rsplit("_", 2)
        start, end = int(parts[-2]), int(parts[-1])
        return (end - start, end, -start)

    if prefer == "longest":
        return max(matches, key=span)
    if prefer == "latest":
        return max(matches, key=lambda p: span(p)[1])
    raise ValueError(f"unknown prefer mode: {prefer}")


def scheduled_basal_profile(
    therapy_cache_path: str,
    *,
    tz: str = "America/Chicago",
) -> np.ndarray:
    """Return a 288-element array of scheduled basal U/hr per 5-min slot
    (slot i covers local time [i*5min, (i+1)*5min) within a day).

    Built from the `basal` entries in the therapy cache. If the schedule is
    revised over time, this uses the most-recent block covering each slot.
    """
    with open(therapy_cache_path) as f:
        d = json.load(f)
    raw_blocks = d.get("basal", [])
    if not raw_blocks:
        raise ValueError(f"no basal schedule found in {therapy_cache_path}")
    df = pd.DataFrame(raw_blocks)
    df["start_utc"] = pd.to_datetime(df["startDate"], utc=True)
    df["end_utc"]   = pd.to_datetime(df["endDate"], utc=True)
    df["value"] = df["value"].astype(float)
    # Default to median rate if no block covers a slot (shouldn't happen
    # with well-formed therapy data).
    median_rate = float(df["value"].median())

    # Anchor at the start of the earliest UTC day in the schedule, expressed
    # in local time; build 288 5-min slot rates by sampling that day.
    earliest_local = df["start_utc"].min().tz_convert(tz).normalize()
    profile = np.full(288, median_rate, dtype=float)
    for i in range(288):
        h, m = i // 12, (i % 12) * 5
        sample_local = earliest_local + pd.Timedelta(hours=h, minutes=m)
        sample_utc = sample_local.tz_convert("UTC")
        mask = (df["start_utc"] <= sample_utc) & (df["end_utc"] > sample_utc)
        if mask.any():
            profile[i] = df.loc[mask, "value"].iloc[0]
        else:
            before = df[df["start_utc"] <= sample_utc]
            if len(before) > 0:
                profile[i] = before.iloc[-1]["value"]
    return profile


def scheduled_basal_at(
    timestamps: pd.DatetimeIndex,
    therapy_cache_path: str,
    *,
    tz: str = "America/Chicago",
) -> pd.Series:
    """Return the scheduled basal U/hr at each timestamp.

    Looks up each timestamp in the actual basal timeline (matches the entry
    whose half-open interval [startDate, endDate) covers the point).
    The schedule can change over time; if so, each timestamp gets the rate
    in effect at that wall-clock instant. Falls back to the most-recent prior
    entry if no entry covers the point.
    """
    with open(therapy_cache_path) as f:
        d = json.load(f)
    blocks = d.get("basal", [])
    if not blocks:
        raise ValueError(f"no basal schedule found in {therapy_cache_path}")
    df = pd.DataFrame(blocks)
    df["start_utc"] = pd.to_datetime(df["startDate"], utc=True)
    df["end_utc"]   = pd.to_datetime(df["endDate"], utc=True)
    df["value"]     = df["value"].astype(float)
    df = df.sort_values("start_utc").reset_index(drop=True)

    if timestamps.tz is None:
        ts_utc = timestamps.tz_localize(tz).tz_convert("UTC")
    else:
        ts_utc = timestamps.tz_convert("UTC")
    starts = df["start_utc"].values
    ends   = df["end_utc"].values
    values = df["value"].values
    out = np.empty(len(timestamps), dtype=float)
    for i, t in enumerate(ts_utc):
        idx = np.searchsorted(starts, t.to_numpy(), side="right") - 1
        if idx < 0:
            out[i] = values[0]
        else:
            # If t falls before this block's end, use its value;
            # otherwise the block has ended without a successor — use the last value.
            out[i] = values[idx] if t.to_numpy() < ends[idx] else values[idx]
    return pd.Series(out, index=timestamps, name="scheduled_uhr")


def effective_delivery_rate(
    doses: pd.DataFrame,
    therapy_cache_path: str,
    *,
    target_index: Optional[pd.DatetimeIndex] = None,
    interval_minutes: int = 5,
    tz: str = "America/Chicago",
) -> pd.Series:
    """Effective basal delivery rate (U/hr) — temp where set, scheduled in gaps.

    Merges the sparse `basal_delivery_timeline()` output (NaN at gaps) with
    the scheduled basal schedule from the therapy cache. The result is
    NEVER NaN within the data span: temp basal rate where Loop set one
    (including 0 for suspend), scheduled basal rate everywhere else.

    Use this — not ``btl["rate_uhr"].fillna(0)`` — when you need the rate
    of insulin actually being delivered at each step.

    Returns a Series indexed at ``target_index`` if provided, else at the
    uniform interval-minute grid built by ``basal_delivery_timeline``.
    """
    btl = basal_delivery_timeline(doses, interval_minutes=interval_minutes)
    raw_rate = btl["rate_uhr"]
    if target_index is not None:
        raw_rate = raw_rate.reindex(target_index, method="nearest",
                                     tolerance=pd.Timedelta(minutes=interval_minutes + 2))
        sched = scheduled_basal_at(target_index, therapy_cache_path, tz=tz)
    else:
        sched = scheduled_basal_at(raw_rate.index, therapy_cache_path, tz=tz)
    # Use the temp rate where present (including 0), scheduled elsewhere
    effective = raw_rate.combine_first(sched)
    effective.name = "effective_rate_uhr"
    return effective


def daily_tdd(doses: pd.DataFrame) -> pd.Series:
    """Sum doses by local-calendar-day start date. Returns a Series of U/day."""
    if doses.empty:
        return pd.Series(dtype=float)
    day = doses.index.tz_localize(None).normalize()
    out = doses.groupby(day)["volume"].sum()
    out.index = pd.DatetimeIndex(out.index, name="day")
    return out.sort_index()


def find_doses_cache(
    host: str,
    cache_dir: str = DEFAULT_CACHE_DIR,
    prefer: str = "longest",
) -> str:
    """Locate the best-matching cached doses JSON for a host."""
    pattern = os.path.join(cache_dir, f"doses_{host}_*.json")
    matches = sorted(glob.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"no doses cache for {host} in {cache_dir}")

    def span(path: str) -> tuple[int, int, int]:
        stem = os.path.basename(path).removesuffix(".json")
        parts = stem.rsplit("_", 2)
        start, end = int(parts[-2]), int(parts[-1])
        return (end - start, end, -start)

    if prefer == "longest":
        return max(matches, key=span)
    if prefer == "latest":
        return max(matches, key=lambda p: span(p)[1])
    raise ValueError(f"unknown prefer mode: {prefer}")


def filter_window(
    df: pd.DataFrame,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    """Clip a time-indexed DataFrame to [start, end). Both args are YYYY-MM-DD.

    Matches the tz-awareness of ``df.index``: if the index is tz-aware, the
    bounds are interpreted in that timezone; if tz-naive, bounds are naive.
    """
    out = df
    tz = getattr(out.index, "tz", None)
    if start is not None:
        ts = pd.Timestamp(start, tz=tz) if tz is not None else pd.Timestamp(start)
        out = out[out.index >= ts]
    if end is not None:
        ts = pd.Timestamp(end, tz=tz) if tz is not None else pd.Timestamp(end)
        out = out[out.index < ts]
    return out
