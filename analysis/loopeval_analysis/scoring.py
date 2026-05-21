"""Outcome scoring with disruption-window exclusion.

Counter_BG in the closed-loop sim re-anchors to actual BG whenever CGM data
resumes after a gap, and a pump outage ends with a replacement + catch-up
bolus. For roughly a DIA afterwards the counterfactual is dominated by the
actual trajectory, not by the candidate's own divergence — so we (1) don't
really know how the candidate would have performed and (2) the candidate has
had little time to take effect. Those windows should be excluded from outcome
stats.

`exclusion_mask` marks every sample within `post_hours` AFTER the end of any
CGM gap or pump outage (and, by default, the disruption interval itself, since
CGM-gap interiors have no candidate signal and outage interiors deliver 0 in
both real and counter). `outcome_stats` reports the usual metrics on the
surviving samples.
"""
from __future__ import annotations
from typing import Optional, Sequence
import pandas as pd


def exclusion_mask(index: pd.DatetimeIndex,
                   outages: Sequence = (),
                   cgm_gaps: Sequence = (),
                   post_hours: float = 3.0,
                   include_interior: bool = True) -> pd.Series:
    """Boolean Series over `index`: True where the sample should be EXCLUDED.

    For each disruption window [start, end], excludes [end, end + post_hours]
    (the recovery window). With `include_interior` also excludes [start, end].
    Both outages and CGM gaps are treated identically.
    """
    idx = pd.DatetimeIndex(index)
    mask = pd.Series(False, index=idx)
    post = pd.Timedelta(hours=post_hours)
    for w in list(outages) + list(cgm_gaps):
        lo = w.start if include_interior else w.end
        hi = w.end + post
        mask |= (idx >= lo) & (idx <= hi)
    return mask


def score_counterfactual(trace_path: str,
                         outages_csv: Optional[str] = None,
                         cgm_gaps_csv: Optional[str] = None,
                         post_hours: float = 3.0,
                         burnin_hours: float = 6.0,
                         tz=None) -> dict:
    """Canonical outcome scorer for a SimulateCommand trace.

    THE STANDARD for every experiment: scores counter_BG with the burn-in
    skipped AND the disruption-recovery windows excluded (3h after every CGM
    gap and pump outage). Pass the dataset's outage/cgm-gap CSVs (generate once
    per dataset via `loopeval_analysis.outage from-nightscout` and
    `loopeval_analysis.cgm_gaps from-cache`). Returns the dict from
    `outcome_stats` plus `kept_frac`.
    """
    import json, pytz
    from pathlib import Path
    tz = tz or pytz.timezone("America/Chicago")
    t = json.loads(Path(trace_path).read_text())
    c = pd.DataFrame(t["counter"])
    c["t"] = pd.to_datetime(c["t"]).dt.tz_convert(tz)
    bg = c.set_index("t")["bg"].dropna()
    cf = pd.to_datetime(t["intervalStart"]).tz_convert(tz) + pd.Timedelta(hours=burnin_hours)
    bg = bg.loc[bg.index >= cf]

    outs, gaps = [], []
    if outages_csv:
        from loopeval_analysis.outage import read_outages_csv
        outs = read_outages_csv(outages_csv)
    if cgm_gaps_csv:
        from loopeval_analysis.cgm_gaps import read_cgm_gaps_csv
        gaps = read_cgm_gaps_csv(cgm_gaps_csv)
    excl = exclusion_mask(bg.index, outs, gaps, post_hours=post_hours) if (outs or gaps) else None
    st = outcome_stats(bg, exclude=excl)
    st["kept_frac"] = st["n"] / len(bg) if len(bg) else float("nan")
    return st


def outcome_stats(bg: pd.Series,
                  exclude: Optional[pd.Series] = None,
                  dt_min: float = 5.0) -> dict:
    """TIR / time-in-band / AUC / mean on `bg`, dropping `exclude`==True samples."""
    bg = bg.dropna()
    if exclude is not None:
        keep = ~exclude.reindex(bg.index).fillna(False)
        bg = bg[keep]
    n = len(bg)
    if n == 0:
        return {}
    tp = lambda m: m.mean() * 100
    auc_below = lambda thr: ((thr - bg).clip(lower=0).sum() * dt_min) / 60.0
    auc_above = lambda thr: ((bg - thr).clip(lower=0).sum() * dt_min) / 60.0
    return {
        "n": n, "days": n * dt_min / 1440,
        "TIR": tp((bg >= 70) & (bg <= 180)),
        "t70": tp(bg < 70), "t54": tp(bg < 54),
        "t180": tp(bg > 180), "t250": tp(bg > 250),
        "auc70": auc_below(70), "auc54": auc_below(54), "auc180": auc_above(180),
        "mean": bg.mean(), "min": bg.min(), "std": bg.std(),
    }
