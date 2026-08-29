"""Outcome scoring with disruption-window exclusion.

POLICY (2026-05-26, user): we DO NOT ignore the recovery window after a
disruption. The sim handles disruptions operationally — delivery is clamped to
0 only DURING a pump outage, and no dose is issued during a CGM gap (stale
guard) — and it resumes its OWN closed-loop dosing the moment the pump/CGM
returns. So the post-disruption trajectory genuinely measures the candidate
(in hands-off mode there's no real catch-up bolus to contaminate it). Only the
disruption INTERVAL itself is dropped: for a pump outage that's a forced
no-dose period (delivers 0 in both real and counter); for a CGM gap the
interior is absent/empty. `post_hours` therefore defaults to 0.

`exclusion_mask` marks the disruption intervals (and, if post_hours>0, the
recovery window after). `outcome_stats` reports the usual metrics on the
surviving samples.
"""
from __future__ import annotations
from typing import Optional, Sequence
import numpy as np
import pandas as pd


# --- Magni risk index -------------------------------------------------------------------------
# Magni et al., "Model Predictive Control of Type 1 Diabetes: An In Silico Trial" (JDST 2007).
#     r(g) = 10 * f(g)^2,  f(g) = 3.5506 * [ (ln g)^0.8353 - 3.7932 ],  g in mg/dL
# A single asymmetric risk scalar: one number that prices hypo and hyper on a common scale, so a
# candidate does not have to be judged by trading two axes against each other.
#
# MEASURED properties of these constants (verify_magni() below re-checks them at import-time cost
# nothing; they are asserted in the tests rather than trusted from memory):
#   * the minimum is at g = 138.9 mg/dL, NOT ~112 as the Kovatchev risk function's is. This is a
#     real and consequential difference: r(100) = 5.67 exceeds r(180) = 3.47, so Magni scores a
#     BG of 100 as RISKIER than 180. Anyone reading a Magni delta must know that the index prefers
#     running higher than a TIR-centred view does.
#   * it is hypo-weighted, which is why it suits this project: an equal excursion below the minimum
#     costs 1.8x (+/-40 mg/dL), 2.6x (+/-60) and 3.7x (+/-80) more than the same excursion above.
#   * reference values: r(40)=84.3, r(54)=48.0, r(70)=25.0, r(180)=3.5, r(250)=17.6, r(400)=56.3.
#
# Below 20 / above 600 mg/dL the CGM is clamped anyway; the input is clipped there so a floored 40
# or a ceilinged 400 cannot produce a spurious spike (see AGENTS.md on interval censoring).
MAGNI_MIN_BG = 138.9          # where r(g) = 0, measured not assumed

def magni_risk(bg):
    """Per-sample Magni risk. Accepts a scalar, ndarray or Series; returns the same shape."""
    g = np.clip(np.asarray(bg, dtype=float), 20.0, 600.0)
    f = 3.5506 * (np.log(g) ** 0.8353 - 3.7932)
    r = 10.0 * f * f
    if isinstance(bg, pd.Series):
        return pd.Series(r, index=bg.index, name="magni")
    return r


def verify_magni() -> dict:
    """Re-derive the documented properties from the constants. Used by the tests and safe to call."""
    g = np.arange(20.0, 600.01, 0.05)
    r = magni_risk(g)
    out = {"argmin_bg": float(g[r.argmin()]), "min_risk": float(r.min())}
    for x in (40, 54, 70, 100, 180, 250, 400):
        out[f"r{x}"] = float(magni_risk(x))
    m = out["argmin_bg"]
    for d in (40, 60, 80):
        out[f"asym{d}"] = float(magni_risk(m - d) / magni_risk(m + d))
    return out


def exclusion_mask(index: pd.DatetimeIndex,
                   outages: Sequence = (),
                   cgm_gaps: Sequence = (),
                   post_hours: float = 0.0,
                   include_interior: bool = True) -> pd.Series:
    """Boolean Series over `index`: True where the sample should be EXCLUDED.

    For each disruption window [start, end], excludes [end, end + post_hours].
    With `include_interior` (default) also excludes [start, end]. Default
    post_hours=0 ⇒ only the disruption interval is dropped, NOT the recovery
    window (see module docstring). Both outages and CGM gaps treated identically.
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
                         post_hours: float = 0.0,
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

    # IOB-at-crossing-54 danger metric (reads the sim's per-step candidateIOB).
    preds = t.get("predictions")
    if preds:
        p = pd.DataFrame(preds)
        if "candidateIOB" in p.columns and "t" in p.columns:
            p["t"] = pd.to_datetime(p["t"]).dt.tz_convert(tz)
            iob = p.dropna(subset=["t"]).set_index("t")["candidateIOB"]
            st.update(crossing_iob_stats(bg, iob, threshold=54.0, exclude=excl))
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


def crossing_iob_stats(bg: pd.Series,
                       iob: pd.Series,
                       threshold: float = 54.0,
                       exclude: Optional[pd.Series] = None,
                       max_gap_min: float = 6.0) -> dict:
    """Net IOB at each DOWNWARD crossing of `threshold` (a low-DANGER metric).

    Danger framing: the more committed insulin a candidate carries into a severe
    low, the more dangerous it is — it drives the low deeper and forces more
    rescue, EVEN WHEN the treated time-below-threshold looks identical. This is a
    danger axis that t<54 duration cannot see (duration is flattened by rescue
    behavior in real data and by the counter-reg floor in sim). See
    memory/project_iob_at_crossing_danger_2026_06_07.

    A crossing is the first sample that drops below `threshold` from at-or-above.
    Crossings whose preceding sample is >`max_gap_min` away (a data gap) or that
    fall in an `exclude`d interval are skipped. Returns counts and IOB summaries;
    `possum` (sum of positive IOB across crossings) is the aggregate exposure —
    it scales with BOTH how often the candidate goes low AND how much committed
    insulin it carries in. Negative IOB at a crossing is safe (no committed
    lowering left, e.g. already suspended), so it is floored to 0 in `possum`.
    """
    key = f"{threshold:.0f}"
    bg = bg.dropna()
    if len(bg) < 2:
        return {f"n_cross{key}": 0}
    iob = iob.reindex(bg.index)
    idx = bg.index
    dt = idx.to_series().diff().dt.total_seconds().to_numpy() / 60.0
    excl = (exclude.reindex(idx).fillna(False).to_numpy()
            if exclude is not None else np.zeros(len(idx), dtype=bool))
    v = bg.to_numpy(); iv = iob.to_numpy()
    cross = []
    for i in range(1, len(v)):
        if (v[i-1] >= threshold and v[i] < threshold
                and not excl[i] and dt[i] <= max_gap_min and not np.isnan(iv[i])):
            cross.append(iv[i])
    cross = np.asarray(cross, dtype=float)
    n = len(cross)
    if n == 0:
        return {f"n_cross{key}": 0}
    pos = np.clip(cross, 0.0, None)
    return {
        f"n_cross{key}": n,
        f"iob_cross{key}_med": float(np.median(cross)),
        f"iob_cross{key}_mean": float(cross.mean()),
        f"iob_cross{key}_p90": float(np.percentile(cross, 90)),
        f"iob_cross{key}_possum": float(pos.sum()),
    }
