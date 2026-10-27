"""Distances between two `stats.person_stats` results, one number per statistic.

A generator is judged against two references measured on real data:
  floor    the same person's earlier weeks vs their held-out weeks (natural week-to-week drift)
  ceiling  a different person vs the held-out weeks (what ignoring the person costs)
Good = close to the floor, well below the ceiling, for every statistic.
"""
from __future__ import annotations
import numpy as np

UNITS = {"quantiles5": "mg/dL/h", "quantiles30": "mg/dL/h", "acf": "r", "hourly": "mg/dL/h",
         "daily_sd_ratio": "ratio", "ep_per_day": "/day", "ep_by_hour": "/day/h", "ep_size_q": "g-eq",
         "ep_dur_q": "h", "hazard": "p", "vs_bg": "mg/dL/h", "vs_iob": "mg/dL/h"}


def _mad(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    return float(np.mean(np.abs(a[ok] - b[ok]))) if ok.any() else np.nan


def distance(s: dict, ref: dict) -> dict:
    return {k: _mad(s[k], ref[k]) for k in UNITS}
