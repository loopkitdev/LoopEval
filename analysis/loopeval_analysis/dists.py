"""Distributional structure of glucose, glucose velocity, and insulin activity.

Builds one uniform 5-minute panel per dataset so that marginals, joints and
dynamics can be compared *across* people. Nothing here simulates or replays;
it is a description of what the recorded data actually looks like.

The panel is deliberately built around three quantities and their relationship:

    v      = ΔBG over the 5-min bin                       (mg/dL / 5 min)
    ia     = insulin activity: BG-lowering delivered by   (mg/dL / 5 min, ≥ 0)
             insulin absorbing during that same bin
    ice    = v + ia   — the insulin counteraction effect: everything that is
             NOT insulin (endogenous glucose production, carbs, exercise,
             sensor noise) expressed in the same units

`ia` is computed two ways, and the difference matters:

  * ``ia_abs``  — from **every unit delivered**, basal included. This is the
    physiological reading: all insulin in the body is acting.
  * ``ia_net``  — from **delivery minus the basal schedule**, which is Loop's
    own convention. Scheduled basal is booked at exactly zero.

``ia_abs - ia_net`` is therefore precisely the activity of the scheduled basal
stream — the part Loop's forecast never prices. ``ice_net`` (what Loop's
retrospective correction actually sees) folds that stream in with real
physiology, while ``ice_abs`` isolates non-insulin flux.

Conventions
-----------
* Positive ``ia`` means insulin is pushing BG **down**. ``v`` is signed.
* Everything is per 5-minute bin. Multiply by 12 for mg/dL per hour.
* Bin ``j`` covers ``(t[j-1], t[j]]``. ``v[j] = bg[j] - bg[j-1]`` and ``ia[j]``
  is the insulin effect delivered over that same interval, so they align.
* The index is tz-aware UTC. Local time enters only via ``tod_min``
  (minutes since local midnight), from a per-dataset UTC offset.
"""
from __future__ import annotations

import csv
import glob
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Optional, Sequence

import numpy as np
import pandas as pd

from .iob import (InsulinModel, RAPID_ACTING_ADULT, FIASP, LYUMJEV,
                  RAPID_ACTING_CHILD, percent_effect_remaining)

BIN_MIN = 5.0
LOOKBACK_MIN = 400.0          # > effect_duration (370) for any model here
MAX_CGM_GAP = pd.Timedelta("15min")
QUIET_START_LOCAL = 2         # calibrated; see infer_utc_offset
OFFSET_UNCERTAINTY_H = 2.0

INSULIN_MODELS = {
    "rapidactingadult": RAPID_ACTING_ADULT,
    "rapidactingchild": RAPID_ACTING_CHILD,
    "fiasp": FIASP,
    "lyumjev": LYUMJEV,
}


# ────────────────────────────────────────────────────────────────────────────
# Dataset description
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class Dataset:
    """One person's recorded data, located on disk.

    ``utc_offset_h`` is the *local* offset used only to build ``tod_min``.
    Where a dataset declares its timezone we use that; otherwise it is
    inferred (see :func:`infer_utc_offset`) and ``offset_inferred`` is True.
    """
    alias: str
    glucose_path: str
    doses_path: str
    therapy_path: str
    carbs_path: Optional[str] = None
    disruptions_path: Optional[str] = None
    insulin_model: InsulinModel = RAPID_ACTING_ADULT
    insulin_name: str = "rapidActingAdult"
    utc_offset_h: float = 0.0
    offset_inferred: bool = True
    source: str = "bddp"
    notes: str = ""

    def __repr__(self) -> str:      # keep reprs free of anything identifying
        return f"Dataset({self.alias}, {self.source}, {self.insulin_name})"


def bddp_datasets(root: str, aliases: Optional[Sequence[str]] = None,
                  source: str = "bddp") -> list[Dataset]:
    """Discover donor exports under ``root``.

    Accepts both layouts in use: ``<root>/<alias>/data_causal/*.json`` (the cohort
    run dirs) and ``<root>/<alias>/*.json`` (a plain ``export_donor`` outdir).
    """
    out: list[Dataset] = []
    dirs = sorted(glob.glob(os.path.join(root, "*", "data_causal")))
    if not dirs:
        dirs = sorted(d for d in glob.glob(os.path.join(root, "*"))
                      if os.path.isdir(d)
                      and os.path.exists(os.path.join(d, "therapy.json")))
    for d in dirs:
        alias = (os.path.basename(os.path.dirname(d))
                 if os.path.basename(d) == "data_causal" else os.path.basename(d))
        if aliases is not None and alias not in aliases:
            continue
        therapy = os.path.join(d, "therapy.json")
        if not os.path.exists(therapy):
            continue
        with open(therapy) as f:
            ins = str(json.load(f).get("insulinType", "rapidActingAdult"))
        ds = Dataset(
            alias=alias,
            glucose_path=os.path.join(d, "glucose.json"),
            doses_path=os.path.join(d, "doses.json"),
            therapy_path=therapy,
            carbs_path=os.path.join(d, "carbs.json"),
            disruptions_path=os.path.join(d, "disruptions.csv"),
            insulin_model=INSULIN_MODELS.get(ins.lower(), RAPID_ACTING_ADULT),
            insulin_name=ins,
            source=source,
        )
        out.append(ds)
    return out


def ns_dataset(alias: str, host: str, cache_dir: str = None) -> Dataset:
    """Build a Dataset from the Nightscout cache layout, by host.

    The host string is a real hostname and must never reach a plot, report or
    committed file — only ``alias`` does.
    """
    from .glucose import DEFAULT_CACHE_DIR
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    therapy = _find_cache(cache_dir, "therapy", host)
    with open(therapy) as f:
        t = json.load(f)
    ins = str(t.get("insulinType", "rapidActingAdult"))
    # The longest-span therapy file often predates the tz field; take the
    # modal declaration across every cached file for this host.
    tzid = t.get("scheduleTimeZoneIdentifier") or _modal_tzid(cache_dir, host)
    off, inferred = 0.0, True
    if tzid:
        try:
            import zoneinfo
            # Sample mid-window so we get the prevailing (usually DST) offset.
            probe = pd.Timestamp("2026-06-15", tz="UTC").tz_convert(zoneinfo.ZoneInfo(tzid))
            off, inferred = probe.utcoffset().total_seconds() / 3600.0, False
        except Exception:
            pass
    carbs = _find_cache(cache_dir, "carbs", host, required=False)
    return Dataset(
        alias=alias,
        glucose_path=_find_cache(cache_dir, "glucose", host),
        doses_path=_find_cache(cache_dir, "doses", host),
        therapy_path=therapy,
        carbs_path=carbs,
        insulin_model=INSULIN_MODELS.get(ins.lower(), RAPID_ACTING_ADULT),
        insulin_name=ins,
        utc_offset_h=off,
        offset_inferred=inferred,
        source="ns",
    )


def _find_cache(cache_dir: str, kind: str, host: str,
                required: bool = True) -> Optional[str]:
    """Widest-span cached file of `kind` for `host`.

    Filenames carry optional variant prefixes (``therapy_v9ex_fiasp_ov_<host>_…``),
    so match on the host segment rather than a fixed prefix.
    """
    hits = glob.glob(os.path.join(cache_dir, f"{kind}_*{host}_*.json"))
    hits = [h for h in hits if os.path.basename(h).startswith(kind + "_")]
    if not hits:
        if required:
            raise FileNotFoundError(f"no {kind} cache for that host in {cache_dir}")
        return None

    def span(path: str) -> tuple[int, int]:
        parts = os.path.basename(path).removesuffix(".json").rsplit("_", 2)
        try:
            return (int(parts[-1]) - int(parts[-2]), int(parts[-1]))
        except ValueError:
            return (0, 0)

    return max(hits, key=span)


def _modal_tzid(cache_dir: str, host: str) -> Optional[str]:
    import collections
    seen = collections.Counter()
    for f in glob.glob(os.path.join(cache_dir, f"therapy_*{host}_*.json")):
        try:
            with open(f) as fh:
                z = json.load(fh).get("scheduleTimeZoneIdentifier")
        except Exception:
            continue
        if z:
            seen[z] += 1
    return seen.most_common(1)[0][0] if seen else None


# ────────────────────────────────────────────────────────────────────────────
# Timezone inference
# ────────────────────────────────────────────────────────────────────────────
def interaction_hours(doses_path: str, carbs_path: Optional[str] = None
                      ) -> np.ndarray:
    """UTC hour-of-day of every deliberate user interaction with the system.

    Manual boluses and carb entries only — automatic delivery is the
    controller acting, not the person, and carries no waking-hours signal.
    """
    ev: list[float] = []
    doses = _load_doses(doses_path)
    if len(doses):
        manual = doses[(doses["delivery_type"] != "basal") & (~doses["automatic"])]
        ev += list(manual.index.hour + manual.index.minute / 60.0)
    if carbs_path and os.path.exists(carbs_path):
        c = _load_carbs(carbs_path)
        if len(c):
            ev += list(c.index.hour + c.index.minute / 60.0)
    return np.asarray(ev, dtype=float)


def infer_utc_offset(doses_path: str, carbs_path: Optional[str] = None,
                     *, night_hours: int = 6) -> tuple[float, float]:
    """Infer a dataset's UTC offset from *when the person is asleep*.

    People do not bolus or log carbs while asleep, so the quietest window of
    the day is night. We find the ``night_hours``-long circular window holding
    the least interaction mass and place its start at local ``QUIET_START_LOCAL``.

    That constant is calibrated, not assumed: on the three cached sites that
    declare a timezone the quiet window begins at local 02:00, 02:00 and 00:00.
    Taking 02:00 recovers two of the three exactly and misses the third by 2 h,
    so treat every inferred offset as carrying **± 2 h**. That is fine for
    features spanning hours (a dawn rise) and not fine for anything sharper.
    A fourth cached site was excluded from the calibration: it declares three
    different zones across its history, so its "truth" is not one.

    Returns ``(offset_hours, confidence)``. Confidence is
    ``1 - night_rate/day_rate`` — 1.0 means the quiet window is truly empty,
    0.0 means interactions are spread evenly and the estimate is worthless.

    This is an estimate, not a record. Validate against a dataset that
    declares its timezone before leaning on it, and treat any circadian
    finding as carrying roughly an hour of positional uncertainty.
    """
    ev = interaction_hours(doses_path, carbs_path)
    if len(ev) < 20:
        return 0.0, 0.0
    counts = np.bincount(ev.astype(int) % 24, minlength=24).astype(float)
    counts /= counts.sum()

    window = np.array([counts[(np.arange(night_hours) + q) % 24].sum()
                       for q in range(24)])
    q = int(np.argmin(window))          # quiet window starts at UTC hour q
    offset = float((QUIET_START_LOCAL - q) % 24)
    if offset > 12:
        offset -= 24                    # keep it in [-12, +12]

    night_rate = window[q] / night_hours
    day_rate = (1.0 - window[q]) / (24 - night_hours)
    conf = float(1.0 - night_rate / day_rate) if day_rate > 0 else 0.0
    return offset, max(conf, 0.0)


# ────────────────────────────────────────────────────────────────────────────
# Loaders (schema is shared between the donor exports and the NS cache)
# ────────────────────────────────────────────────────────────────────────────
def _load_glucose(path: str) -> pd.Series:
    with open(path) as f:
        data = json.load(f)
    if not data:
        return pd.Series(dtype=float)
    t = pd.to_datetime([r["startDate"] for r in data], utc=True, format="ISO8601")
    s = pd.Series([float(r["quantity"]) for r in data], index=t).sort_index()
    return s[~s.index.duplicated(keep="first")]


def _load_doses(path: str) -> pd.DataFrame:
    with open(path) as f:
        data = json.load(f)
    if not data:
        return pd.DataFrame(columns=["volume", "delivery_type", "automatic",
                                     "endDate", "rate_uhr"])
    starts = pd.to_datetime([r["startDate"] for r in data], utc=True, format="ISO8601")
    ends = pd.to_datetime([r.get("endDate", r["startDate"]) for r in data],
                          utc=True, format="ISO8601")
    df = pd.DataFrame({
        "volume": [float(r.get("volume", 0) or 0) for r in data],
        "delivery_type": [r.get("deliveryType", r.get("type", "")) for r in data],
        "automatic": [bool(r.get("automatic", False)) for r in data],
        "endDate": ends,
    }, index=starts).sort_index()
    dur_h = (df["endDate"] - df.index).dt.total_seconds() / 3600.0
    is_basal = df["delivery_type"] == "basal"
    df["rate_uhr"] = np.where(is_basal & (dur_h > 0), df["volume"] / dur_h, np.nan)
    return df


def _load_carbs(path: str) -> pd.DataFrame:
    with open(path) as f:
        data = json.load(f)
    if not data:
        return pd.DataFrame(columns=["grams", "absorption_s"])
    t = pd.to_datetime([r["startDate"] for r in data], utc=True, format="ISO8601")
    return pd.DataFrame({
        "grams": [float(r.get("grams", 0) or 0) for r in data],
        "absorption_s": [float(r.get("absorptionTime", 3 * 3600) or 3 * 3600) for r in data],
    }, index=t).sort_index()


def _schedule_series(therapy: dict, key: str, grid: pd.DatetimeIndex) -> pd.Series:
    """Step-sample a dated therapy schedule (``basal``/``sensitivity``/…) onto a grid.

    The exports store schedules already expanded into dated blocks, so this is a
    plain as-of lookup rather than a time-of-day profile — which keeps
    settings changes over the window intact.
    """
    blocks = therapy.get(key) or []
    if not blocks:
        return pd.Series(np.nan, index=grid)
    starts = pd.to_datetime([b["startDate"] for b in blocks], utc=True, format="ISO8601")
    vals = np.array([float(b.get("value", b.get("lowerBound", np.nan))) for b in blocks],
                    dtype=float)
    order = np.argsort(starts.values)
    starts, vals = starts[order], vals[order]
    idx = np.searchsorted(starts.values, grid.values, side="right") - 1
    out = np.where(idx >= 0, vals[np.clip(idx, 0, len(vals) - 1)], np.nan)
    return pd.Series(out, index=grid)


def _activity_kernel(model: InsulinModel, n: int) -> np.ndarray:
    """Fraction of one unit's effect delivered in each 5-min bin after dosing."""
    edges = np.arange(n + 1) * BIN_MIN
    pct = percent_effect_remaining(edges, model=model)
    return np.maximum(pct[:-1] - pct[1:], 0.0)


def _iob_kernel(model: InsulinModel, n: int) -> np.ndarray:
    return percent_effect_remaining(np.arange(n) * BIN_MIN, model=model)


def _convolve(units: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    return np.convolve(units, kernel)[:len(units)]


# ────────────────────────────────────────────────────────────────────────────
# The panel
# ────────────────────────────────────────────────────────────────────────────
def build_panel(ds: Dataset, *, start: Optional[str] = None,
                end: Optional[str] = None) -> pd.DataFrame:
    """Build the uniform 5-minute panel for one dataset.

    Columns
    -------
    bg, v, v30, accel      glucose and its derivatives (mg/dL per 5 min; v30
                           is the 30-min difference, far less sensor-noisy)
    ia_abs, ia_net         insulin activity (mg/dL per 5 min, ≥ 0 = lowering)
    ia_basal, ia_bolus     the absolute activity split by delivery stream
    iob_abs, iob_net       units on board, absolute and Loop's net convention
    ice_abs, ice_net       v + ia — non-insulin flux, both conventions
    carb_effect            announced-carb absorption expressed in mg/dL per bin
    isf, cr, basal_sched, basal_eff, target_lo   settings in force
    bolus_u, auto_bolus_u, manual_bolus_u        delivered this bin
    disrupted              pump error / suspend / loop-offline / CGM gap
    tod_min, dow           local minutes-since-midnight, day of week
    """
    bg_raw = _load_glucose(ds.glucose_path)
    doses = _load_doses(ds.doses_path)
    if bg_raw.empty:
        raise ValueError(f"{ds.alias}: no glucose")
    with open(ds.therapy_path) as f:
        therapy = json.load(f)

    t0 = bg_raw.index.min().floor("5min")
    t1 = bg_raw.index.max().ceil("5min")
    if start is not None:
        t0 = max(t0, pd.Timestamp(start, tz="UTC"))
    if end is not None:
        t1 = min(t1, pd.Timestamp(end, tz="UTC"))
    # Warm-up so insulin on board at the first reported bin is already correct.
    warm = t0 - pd.Timedelta(minutes=LOOKBACK_MIN)
    grid = pd.date_range(warm, t1, freq="5min", tz="UTC")

    # ─── glucose on the grid, with a gap guard ───────────────────────────
    bg = _interp_with_gap_guard(bg_raw, grid, MAX_CGM_GAP)
    v = bg.diff()
    v30 = bg.diff(6)
    accel = v.diff()

    # ─── delivery on the grid ────────────────────────────────────────────
    basal_eff = _effective_basal_rate(doses, therapy, grid)      # U/hr, never NaN
    basal_sched = _schedule_series(therapy, "basal", grid)
    basal_u = basal_eff.to_numpy() * (BIN_MIN / 60.0)
    sched_u = basal_sched.fillna(0.0).to_numpy() * (BIN_MIN / 60.0)

    boluses = doses[doses["delivery_type"] != "basal"]
    bolus_u = _bin_events(boluses["volume"], grid)
    auto_u = _bin_events(boluses.loc[boluses["automatic"], "volume"], grid)
    manual_u = bolus_u - auto_u

    abs_u = basal_u + bolus_u
    net_u = (basal_u - sched_u) + bolus_u

    # ─── insulin activity and IOB ────────────────────────────────────────
    nk = int(ds.insulin_model.effect_duration_min / BIN_MIN) + 2
    act_k, iob_k = _activity_kernel(ds.insulin_model, nk), _iob_kernel(ds.insulin_model, nk)

    isf = _schedule_series(therapy, "sensitivity", grid)
    isf_f = isf.ffill().bfill()

    u_abs_act = _convolve(abs_u, act_k)          # units absorbing per bin
    u_net_act = _convolve(net_u, act_k)
    u_bas_act = _convolve(basal_u, act_k)
    u_bol_act = _convolve(bolus_u, act_k)

    ia_abs = u_abs_act * isf_f.to_numpy()
    ia_net = u_net_act * isf_f.to_numpy()
    ia_basal = u_bas_act * isf_f.to_numpy()
    ia_bolus = u_bol_act * isf_f.to_numpy()

    iob_abs = _convolve(abs_u, iob_k)
    iob_net = _convolve(net_u, iob_k)

    # ─── announced carbs ─────────────────────────────────────────────────
    carb_effect = np.zeros(len(grid))
    cob = np.zeros(len(grid))
    cr = _schedule_series(therapy, "carbRatio", grid).ffill().bfill()
    if ds.carbs_path and os.path.exists(ds.carbs_path):
        g_per_bin, cob = _carb_absorption(_load_carbs(ds.carbs_path), grid)
        with np.errstate(divide="ignore", invalid="ignore"):
            carb_effect = g_per_bin * (isf_f.to_numpy() / cr.to_numpy())

    # ─── disruption mask ─────────────────────────────────────────────────
    disrupted = _disruption_mask(ds, grid) | bg.isna().to_numpy()

    tgt = _schedule_series(therapy, "target", grid)

    local = grid + pd.Timedelta(hours=ds.utc_offset_h)
    panel = pd.DataFrame({
        "bg": bg.to_numpy(), "v": v.to_numpy(), "v30": v30.to_numpy(),
        "accel": accel.to_numpy(),
        "ia_abs": ia_abs, "ia_net": ia_net,
        "ia_basal": ia_basal, "ia_bolus": ia_bolus,
        "iob_abs": iob_abs, "iob_net": iob_net,
        "ice_abs": v.to_numpy() + ia_abs,
        "ice_net": v.to_numpy() + ia_net,
        "carb_effect": carb_effect, "cob": cob,
        "isf": isf_f.to_numpy(), "cr": cr.to_numpy(),
        "basal_sched": basal_sched.to_numpy(),
        "basal_eff": basal_eff.to_numpy(),
        "target_lo": tgt.to_numpy(),
        "bolus_u": bolus_u, "auto_bolus_u": auto_u, "manual_bolus_u": manual_u,
        "disrupted": disrupted,
        "tod_min": local.hour * 60 + local.minute,
        "dow": local.dayofweek,
    }, index=grid)

    panel = panel[panel.index >= t0]
    panel.attrs["alias"] = ds.alias
    panel.attrs["source"] = ds.source
    panel.attrs["insulin"] = ds.insulin_name
    panel.attrs["utc_offset_h"] = ds.utc_offset_h
    panel.attrs["offset_inferred"] = ds.offset_inferred
    return panel


def clean(panel: pd.DataFrame, *, drop_disrupted: bool = True) -> pd.DataFrame:
    """Rows usable for distributional work: BG present, velocity defined.

    ``drop_disrupted`` additionally removes pump errors, suspend windows and
    loop-offline gaps, where delivery — and therefore insulin activity — is
    not trustworthy.
    """
    m = panel["bg"].notna() & panel["v"].notna()
    if drop_disrupted:
        m &= ~panel["disrupted"].astype(bool)
    return panel[m]


# ────────────────────────────────────────────────────────────────────────────
# helpers
# ────────────────────────────────────────────────────────────────────────────
def _interp_with_gap_guard(raw: pd.Series, grid: pd.DatetimeIndex,
                           max_gap: pd.Timedelta) -> pd.Series:
    """Linear-interpolate raw CGM onto the grid, but never across a real gap."""
    merged = raw.reindex(raw.index.union(grid)).interpolate(method="time")
    out = merged.reindex(grid)
    # Blank any grid point whose surrounding raw samples straddle a big gap.
    idx = raw.index
    pos = np.searchsorted(idx.values, grid.values, side="right")
    prev_ok = pos > 0
    next_ok = pos < len(idx)
    gap = np.full(len(grid), np.inf)
    both = prev_ok & next_ok
    gap[both] = (idx.values[pos[both]] - idx.values[pos[both] - 1]) / np.timedelta64(1, "s")
    # Edges: a grid point exactly on a sample is fine; beyond the data is not.
    on_sample = np.isin(grid.values, idx.values)
    bad = (gap > max_gap.total_seconds()) & ~on_sample
    bad |= ~(prev_ok & next_ok) & ~on_sample
    out[bad] = np.nan
    return out


def _bin_events(vals: pd.Series, grid: pd.DatetimeIndex) -> np.ndarray:
    """Sum point events into 5-min bins aligned with the grid."""
    out = np.zeros(len(grid))
    if vals is None or len(vals) == 0:
        return out
    pos = np.searchsorted(grid.values, vals.index.values, side="right") - 1
    ok = (pos >= 0) & (pos < len(grid))
    np.add.at(out, pos[ok], vals.to_numpy()[ok])
    return out


def _effective_basal_rate(doses: pd.DataFrame, therapy: dict,
                          grid: pd.DatetimeIndex) -> pd.Series:
    """Basal U/hr actually being delivered at each bin.

    Temp rate where a basal record covers the bin (including 0 for suspend),
    scheduled rate in the gaps. Never NaN — a NaN rate means *scheduled basal
    running*, not a suspend, and filling it with 0 fabricates suspends.
    """
    sched = _schedule_series(therapy, "basal", grid).ffill().bfill()
    basals = doses[(doses["delivery_type"] == "basal") & doses["rate_uhr"].notna()]
    rate = np.full(len(grid), np.nan)
    if len(basals):
        gv = grid.values
        ends = basals["endDate"].dt.tz_convert("UTC").dt.tz_localize(None).to_numpy()
        s = np.searchsorted(gv, basals.index.values, side="left")
        e = np.searchsorted(gv, ends, side="left")
        rates = basals["rate_uhr"].to_numpy()
        for lo, hi, r in zip(s, e, rates):       # last writer wins on overlap
            if lo < hi:
                rate[lo:hi] = r
    out = pd.Series(rate, index=grid)
    return out.fillna(sched)


def _carb_absorption(carbs: pd.DataFrame, grid: pd.DatetimeIndex
                     ) -> tuple[np.ndarray, np.ndarray]:
    """Grams absorbing per bin and carbs-on-board, using linear absorption.

    A deliberate simplification: Loop's dynamic absorption reshapes this from
    observed glucose, which would smuggle the outcome into a predictor. Linear
    absorption over the entry's own ``absorptionTime`` keeps it a pure
    description of what was *announced*.
    """
    g = np.zeros(len(grid))
    cob = np.zeros(len(grid))
    if carbs.empty:
        return g, cob
    gv = grid.values
    for ts, row in carbs.iterrows():
        grams, dur_s = float(row["grams"]), max(float(row["absorption_s"]), 600.0)
        nb = max(int(round(dur_s / 60.0 / BIN_MIN)), 1)
        lo = int(np.searchsorted(gv, np.datetime64(ts.tz_convert("UTC").tz_localize(None)),
                                 side="right") - 1)
        if lo < 0 or lo >= len(grid):
            continue
        hi = min(lo + nb, len(grid))
        if hi <= lo:
            continue
        per = grams / nb
        g[lo:hi] += per
        rem = grams - per * np.arange(hi - lo)
        cob[lo:hi] += rem
    return g, cob


def _disruption_mask(ds: Dataset, grid: pd.DatetimeIndex) -> np.ndarray:
    mask = np.zeros(len(grid), dtype=bool)
    p = ds.disruptions_path
    if not p or not os.path.exists(p):
        return mask
    gv = grid.values
    with open(p) as f:
        for row in csv.DictReader(f):
            try:
                s = pd.Timestamp(row["start"]).tz_convert("UTC")
                e = pd.Timestamp(row["end"]).tz_convert("UTC")
            except Exception:
                continue
            lo = np.searchsorted(gv, s.to_datetime64(), side="left")
            hi = np.searchsorted(gv, e.to_datetime64(), side="right")
            if lo < hi:
                mask[lo:hi] = True
    return mask
