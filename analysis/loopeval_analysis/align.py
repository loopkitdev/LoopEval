"""Time-alignment helpers for joining ISF series with outcome series."""
from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd


def to_daily(
    series_or_df,
    *,
    how: str = "mean",
    tz: Optional[str] = None,
) -> pd.DataFrame:
    """Resample a sub-daily, datetime-indexed series/dataframe to local-day means.

    The index of the input may be tz-aware; the output has a tz-naive day index
    (so it joins cleanly with `daily_outcomes`'s output).
    """
    obj = series_or_df.copy()
    if obj.index.tz is not None:
        if tz is not None:
            obj.index = obj.index.tz_convert(tz)
        # Bin by local date, then drop tz.
        day = obj.index.tz_localize(None).normalize()
    else:
        day = obj.index.normalize()

    grouped = obj.groupby(day)
    if how == "mean":
        out = grouped.mean(numeric_only=True)
    elif how == "median":
        out = grouped.median(numeric_only=True)
    elif how == "min":
        out = grouped.min(numeric_only=True)
    elif how == "max":
        out = grouped.max(numeric_only=True)
    elif how == "count":
        out = grouped.count()
    else:
        raise ValueError(f"unknown how={how!r}")
    if isinstance(out, pd.Series):
        out = out.to_frame()
    out.index = pd.DatetimeIndex(out.index, name="day")
    return out


def align_on_daily_index(
    *frames: pd.DataFrame,
    prefixes: Optional[Iterable[str]] = None,
    how: str = "outer",
) -> pd.DataFrame:
    """Join several daily-indexed DataFrames into one wide frame.

    Pass `prefixes=("isf_6h", "outcomes")` to disambiguate same-named columns.
    """
    prefixed: list[pd.DataFrame] = []
    if prefixes is None:
        prefixes = [None] * len(frames)
    prefixes = list(prefixes)
    for f, p in zip(frames, prefixes):
        if p is None:
            prefixed.append(f)
        else:
            prefixed.append(f.add_prefix(f"{p}__"))
    if not prefixed:
        return pd.DataFrame()
    out = prefixed[0]
    for nxt in prefixed[1:]:
        out = out.join(nxt, how=how)
    return out.sort_index()


def lagged_correlation(
    x: pd.Series,
    y: pd.Series,
    *,
    lags: Iterable[int] = range(-14, 15),
    method: str = "pearson",
) -> pd.DataFrame:
    """Compute corr(x_shifted_by_lag, y) for each lag (in days).

    Positive lag means x leads y by that many days. Index of the returned frame
    is the lag in days; columns are ``corr`` and ``n``.
    """
    x = x.sort_index()
    y = y.sort_index()
    rows = []
    for lag in lags:
        xs = x.shift(lag)
        df = pd.concat([xs, y], axis=1).dropna()
        if len(df) < 5:
            rows.append({"lag_days": lag, "corr": float("nan"), "n": len(df)})
        else:
            corr = df.iloc[:, 0].corr(df.iloc[:, 1], method=method)
            rows.append({"lag_days": lag, "corr": float(corr), "n": len(df)})
    return pd.DataFrame(rows).set_index("lag_days")
