"""Case-study tooling for LoopEval closed-loop sim traces.

A "case study" answers: at this moment in this sim, what was BG / IOB / dose /
ISF-signal doing across one or more candidate sims, and how does that compare
to what really happened on the pump?

Public API
----------

- ``load_trace(path, label=None, color=None)``: read a SimulateCommand trace
  JSON into a ``SimTrace`` (counter_BG, actual_BG, per-step predictions, etc.).
- ``enumerate_lows(trace, threshold=70, min_duration_min=10, skip_burnin_hours=6)``:
  return a ``DataFrame`` of (start, nadir, duration_min, min_bg, depth_mg_min)
  rows ranked by mg/dL·min below threshold.
- ``plot_case(traces, t_center, window_hours=12, nightscout_host=None,
  out=None, title=None, show_isf_mult=True, show_devicestatus=True)``:
  three-panel figure (BG / dose / IOB) with one column per trace, plus real
  pump and devicestatus IOB for reference. Returns the output ``Path``.
- ``build_case_report(traces, events, out_html, ...)``: multi-event HTML
  report that embeds one plot per event with summary stats.

CLI
---

This module is invocable as a script:

    python -m loopeval_analysis.case_study lows TRACE.json
    python -m loopeval_analysis.case_study plot TRACE.json --time "2026-04-02 01:05" \\
        --window-hours 12 --compare conf.json sanity.json --out case.png
    python -m loopeval_analysis.case_study report TRACE.json --top 6 \\
        --compare conf.json sanity.json --out report.html
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Sequence

import numpy as np
import pandas as pd
import pytz

# Pulled in lazily inside plotting functions so the module imports cheaply.

TZ_DEFAULT = pytz.timezone("America/Chicago")
DT_MIN = 5.0  # sim step in minutes
BURNIN_HOURS_DEFAULT = 6.0


# --------------------------------------------------------------------------- #
#  Data model                                                                 #
# --------------------------------------------------------------------------- #

@dataclass
class SimTrace:
    """A loaded SimulateCommand trace.

    Attributes are pandas objects in the trace's timezone. ``predictions`` is a
    DataFrame indexed by ``t`` with at minimum ``candidateDose``, ``baselineDose``,
    ``deltaDose``, ``isf``, and ``candidateBolus`` / ``candidateTempRate``.
    """
    path: Path
    label: str
    color: str
    counter_bg: pd.Series
    actual_bg: pd.Series
    predictions: pd.DataFrame
    interval_start: pd.Timestamp
    interval_end: pd.Timestamp
    closed_loop: bool = True
    tz: pytz.BaseTzInfo = field(default_factory=lambda: TZ_DEFAULT)
    #: Canonical actual-delivery stream (from the trace's `delivery` array).
    #: Columns: t (index), tEnd, source {field,candidate}, kind {basal,bolus},
    #: automatic (bool), amountU, rateUhr. Empty for pre-delivery-stream traces.
    delivery: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def burnin_end(self) -> pd.Timestamp:
        return self.interval_start + pd.Timedelta(hours=BURNIN_HOURS_DEFAULT)


_DEFAULT_COLORS = [
    "tab:red", "tab:blue", "tab:green", "tab:orange",
    "tab:purple", "tab:brown", "tab:pink", "tab:gray",
]


def load_trace(path: str | Path, label: Optional[str] = None,
               color: Optional[str] = None,
               tz: Optional[pytz.BaseTzInfo] = None) -> SimTrace:
    """Read a SimulateCommand trace JSON into a SimTrace."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"trace JSON does not exist: {p}")
    j = json.loads(p.read_text())

    tz = tz or TZ_DEFAULT
    counter = pd.DataFrame(j["counter"])
    counter["t"] = pd.to_datetime(counter["t"]).dt.tz_convert(tz)
    counter_bg = counter.set_index("t")["bg"].dropna().sort_index()

    actual = pd.DataFrame(j["actual"])
    actual["t"] = pd.to_datetime(actual["t"]).dt.tz_convert(tz)
    actual_bg = actual.set_index("t")["bg"].dropna().sort_index()

    preds = pd.DataFrame(j["predictions"])
    preds["t"] = pd.to_datetime(preds["t"]).dt.tz_convert(tz)
    preds = preds.set_index("t").sort_index()

    delivery = pd.DataFrame(j.get("delivery", []))
    if len(delivery):
        delivery["t"] = pd.to_datetime(delivery["t"]).dt.tz_convert(tz)
        if "tEnd" in delivery:
            delivery["tEnd"] = pd.to_datetime(delivery["tEnd"]).dt.tz_convert(tz)
        delivery = delivery.set_index("t").sort_index()

    return SimTrace(
        path=p,
        label=label or j.get("candidateLabel") or p.stem,
        color=color or _DEFAULT_COLORS[0],
        counter_bg=counter_bg,
        actual_bg=actual_bg,
        predictions=preds,
        interval_start=pd.to_datetime(j["intervalStart"]).tz_convert(tz),
        interval_end=pd.to_datetime(j["intervalEnd"]).tz_convert(tz),
        closed_loop=bool(j.get("closedLoop", True)),
        tz=tz,
        delivery=delivery,
    )


# --------------------------------------------------------------------------- #
#  Low-event enumeration                                                      #
# --------------------------------------------------------------------------- #

def enumerate_lows(trace: SimTrace,
                   threshold: float = 70.0,
                   min_duration_min: float = 10.0,
                   skip_burnin_hours: Optional[float] = BURNIN_HOURS_DEFAULT,
                   use_actual: bool = False,
                   outages: Optional[Sequence] = None,
                   outage_pad_hours: float = 0.0) -> pd.DataFrame:
    """Find contiguous low-BG runs in `trace.counter_bg` (or `actual_bg` if
    `use_actual`). Returns a DataFrame sorted by depth_mg_min descending.

    A "low event" is a contiguous run of samples with bg < `threshold` lasting
    at least `min_duration_min`. ``depth_mg_min`` = ∫ max(0, thr − bg) · dt.

    If ``outages`` is provided, each event gains two columns:
    ``in_outage`` (bool — nadir falls inside an outage with the given pad)
    and ``outage_source`` (the source/notes string of the offending outage,
    or empty). The event is NOT removed — filtering is left to the caller.
    """
    bg = trace.actual_bg if use_actual else trace.counter_bg
    if skip_burnin_hours:
        cutoff = trace.interval_start + pd.Timedelta(hours=skip_burnin_hours)
        bg = bg.loc[bg.index >= cutoff]
    is_low = (bg < threshold).values
    rows: list[dict] = []
    n = len(is_low)
    i = 0
    while i < n:
        if not is_low[i]:
            i += 1
            continue
        j = i
        while j < n and is_low[j]:
            j += 1
        start = bg.index[i]
        end = bg.index[j - 1]
        dur_min = (end - start).total_seconds() / 60.0 + DT_MIN
        if dur_min >= min_duration_min:
            sub = bg.iloc[i:j]
            depth = ((threshold - sub).clip(lower=0).sum()) * DT_MIN
            rows.append({
                "start": start,
                "end": end,
                "nadir_t": sub.idxmin(),
                "duration_min": dur_min,
                "min_bg": float(sub.min()),
                "depth_mg_min": float(depth),
                "severe_t54": bool((sub < 54).any()),
                "severe_t40": bool((sub < 40).any()),
            })
        i = j
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.sort_values("depth_mg_min", ascending=False).reset_index(drop=True)
    if outages:
        from loopeval_analysis.outage import event_in_outage
        in_outage = []
        outage_source = []
        for _, r in df.iterrows():
            hit = event_in_outage(r["nadir_t"], outages, pad_min=outage_pad_hours * 60.0)
            in_outage.append(hit is not None)
            outage_source.append(
                (f"{hit.source}: "
                 f"{hit.start.tz_convert(trace.tz).strftime('%Y-%m-%d %H:%M')} → "
                 f"{hit.end.tz_convert(trace.tz).strftime('%H:%M')}")
                if hit else ""
            )
        df["in_outage"] = in_outage
        df["outage_source"] = outage_source
    return df


# --------------------------------------------------------------------------- #
#  Helpers: real pump rasterization, devicestatus, carbs                      #
# --------------------------------------------------------------------------- #

def rasterize_real_doses(doses_df: pd.DataFrame,
                         step_index: pd.DatetimeIndex,
                         step_minutes: float = DT_MIN) -> pd.Series:
    """Project real pump doses onto a fixed 5-min step grid (U per step).

    Boluses deposit instantly at the bin covering their start time. Basal
    entries are spread linearly across overlapping bins by their duration.
    Returns a Series indexed by `step_index`.
    """
    step_index = pd.DatetimeIndex(step_index).sort_values()
    step_delta_s = int(step_minutes * 60)
    out = np.zeros(len(step_index), dtype=float)
    if doses_df.empty or len(step_index) == 0:
        return pd.Series(out, index=step_index, name="real_u_step")

    grid_start = step_index[0]
    grid_end = step_index[-1] + pd.Timedelta(minutes=step_minutes)
    df = doses_df[
        (doses_df["endDate"] >= grid_start) & (doses_df.index <= grid_end)
    ].copy()
    if df.empty:
        return pd.Series(out, index=step_index, name="real_u_step")

    step_t_s = (step_index.asi8 // 10**9).astype(np.int64)
    starts_s = (df.index.asi8 // 10**9).astype(np.int64)
    ends_s = (df["endDate"].values.astype("datetime64[s]").astype(np.int64))
    vols = df["volume"].fillna(0).values.astype(float)
    is_basal = (df["delivery_type"].values == "basal")

    for k in np.where(~is_basal)[0]:
        if vols[k] == 0:
            continue
        bin_idx = int(np.searchsorted(step_t_s, starts_s[k], side="right") - 1)
        if 0 <= bin_idx < len(out):
            out[bin_idx] += vols[k]

    grid_start_s = step_t_s[0]
    for k in np.where(is_basal)[0]:
        s = max(starts_s[k], grid_start_s)
        e = min(ends_s[k], step_t_s[-1] + step_delta_s)
        if e <= s or vols[k] == 0:
            continue
        u_per_s = vols[k] / max(1, (ends_s[k] - starts_s[k]))
        i0 = int(np.searchsorted(step_t_s, s, side="right") - 1)
        i1 = int(np.searchsorted(step_t_s, e, side="right") - 1)
        i0 = max(0, i0); i1 = min(len(out) - 1, i1)
        if i0 == i1:
            out[i0] += u_per_s * (e - s)
        else:
            first_end = step_t_s[i0] + step_delta_s
            out[i0] += u_per_s * (first_end - s)
            if i1 > i0 + 1:
                out[i0+1:i1] += u_per_s * step_delta_s
            last_start = step_t_s[i1]
            out[i1] += u_per_s * (e - last_start)

    return pd.Series(out, index=step_index, name="real_u_step")


def fetch_devicestatus_iob(host: str, win_start: pd.Timestamp,
                           win_end: pd.Timestamp,
                           tz: pytz.BaseTzInfo = TZ_DEFAULT) -> pd.Series:
    """Pull deployed-Loop's IOB from Nightscout devicestatus over a window.

    Quietly returns an empty series on network failure; the case-study plot
    treats this as an optional reference trace.
    """
    if not host.startswith("http"):
        host = "https://" + host
    url = host.rstrip("/") + "/api/v1/devicestatus.json?" + urllib.parse.urlencode({
        "find[created_at][$gte]": win_start.tz_convert("UTC").isoformat().replace("+00:00", ".000Z"),
        "find[created_at][$lt]":  win_end.tz_convert("UTC").isoformat().replace("+00:00", ".000Z"),
        "count": 800,
    })
    try:
        ds = json.loads(urllib.request.urlopen(url, timeout=20).read())
    except Exception as exc:  # noqa: BLE001
        print(f"  [devicestatus] fetch failed: {exc}", file=sys.stderr)
        return pd.Series(dtype=float)
    rows = []
    for d in ds:
        loop_obj = d.get("loop")
        if not isinstance(loop_obj, dict):
            continue
        iob_obj = loop_obj.get("iob")
        iob_val = iob_obj.get("iob") if isinstance(iob_obj, dict) else iob_obj
        if iob_val is None:
            continue
        ts = pd.to_datetime(d["created_at"]).tz_convert(tz)
        rows.append((ts, float(iob_val)))
    if not rows:
        return pd.Series(dtype=float)
    s = pd.Series(dict(rows)).sort_index()
    return s[~s.index.duplicated(keep="last")]


def fetch_devicestatus_state(host: str, win_start: pd.Timestamp,
                             win_end: pd.Timestamp,
                             tz: pytz.BaseTzInfo = TZ_DEFAULT) -> pd.DataFrame:
    """Deployed-Loop GROUND TRUTH from Nightscout devicestatus over a window:
    columns ``iob`` (U), ``cob`` (g), ``eventualBG`` (mg/dL, last value of the
    uploaded predicted-glucose curve). These are the values the deployed Loop
    actually recorded (post-dose review snapshot) — the reference our baseline*
    reconstruction should be checked against. Empty frame on network failure.
    """
    if not host.startswith("http"):
        host = "https://" + host
    url = host.rstrip("/") + "/api/v1/devicestatus.json?" + urllib.parse.urlencode({
        "find[created_at][$gte]": win_start.tz_convert("UTC").isoformat().replace("+00:00", ".000Z"),
        "find[created_at][$lt]":  win_end.tz_convert("UTC").isoformat().replace("+00:00", ".000Z"),
        "count": 800,
    })
    try:
        ds = json.loads(urllib.request.urlopen(url, timeout=20).read())
    except Exception as exc:  # noqa: BLE001
        print(f"  [devicestatus] fetch failed: {exc}", file=sys.stderr)
        return pd.DataFrame(columns=["iob", "cob", "eventualBG"])
    rows = []
    for d in ds:
        loop_obj = d.get("loop")
        if not isinstance(loop_obj, dict):
            continue
        def _scalar(obj):
            return obj.get(k) if isinstance(obj, dict) else obj
        iob_obj = loop_obj.get("iob"); k = "iob"
        iob = _scalar(iob_obj)
        cob_obj = loop_obj.get("cob"); k = "cob"
        cob = _scalar(cob_obj)
        ebg = None
        pred = loop_obj.get("predicted")
        if isinstance(pred, dict):
            vals = pred.get("values")
            if isinstance(vals, list) and vals:
                ebg = vals[-1]
        ts = pd.to_datetime(d["created_at"]).tz_convert(tz)
        rows.append((ts, iob, cob, ebg))
    if not rows:
        return pd.DataFrame(columns=["iob", "cob", "eventualBG"])
    df = pd.DataFrame(rows, columns=["t", "iob", "cob", "eventualBG"]).set_index("t").sort_index()
    return df[~df.index.duplicated(keep="last")].astype(float)


def load_carbs_in_window(win_start: pd.Timestamp,
                         win_end: pd.Timestamp,
                         tz: pytz.BaseTzInfo = TZ_DEFAULT) -> pd.DataFrame:
    """Read the locally-cached Nightscout carb entries that fall in [start, end]."""
    import glob, os
    files = sorted(
        glob.glob("/Users/pete/.loop-eval/cache/carbs_v2_*.json"),
        key=os.path.getsize, reverse=True,
    )
    if not files:
        files = sorted(
            glob.glob("/Users/pete/.loop-eval/cache/carbs_*.json"),
            key=os.path.getsize, reverse=True,
        )
    if not files:
        return pd.DataFrame()
    try:
        data = json.loads(Path(files[0]).read_text())
    except Exception:
        return pd.DataFrame()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df["meal_t"] = pd.to_datetime(df["startDate"]).dt.tz_convert(tz)
    if "entryDate" in df.columns:
        df["entry_t"] = pd.to_datetime(df["entryDate"]).dt.tz_convert(tz)
    else:
        df["entry_t"] = df["meal_t"]
    return df[(df["entry_t"] >= win_start) & (df["entry_t"] <= win_end)]


# --------------------------------------------------------------------------- #
#  Plotting                                                                   #
# --------------------------------------------------------------------------- #

def _resolve_window(t_center: pd.Timestamp,
                    window_hours: float,
                    tz: pytz.BaseTzInfo) -> tuple[pd.Timestamp, pd.Timestamp]:
    half = pd.Timedelta(hours=window_hours / 2)
    return t_center - half, t_center + half


def _build_sim_iob(predictions: pd.DataFrame,
                   iob_grid: pd.DatetimeIndex,
                   therapy_path: str,
                   manual_boluses_df: pd.DataFrame) -> pd.Series:
    """Reconstruct sim Loop's IOB from a SimulateCommand predictions slice.

    In CF mode, sim's per-step delivery is `scheduled_basal + candidateDose`
    (where candidateDose is the dose-rec delta over scheduled). We synthesize
    a doses-style frame so `loop_iob` (canonical helper) can score it.
    """
    from loopeval_analysis.glucose import scheduled_basal_at
    from loopeval_analysis.iob import loop_iob

    if predictions.empty:
        return pd.Series(dtype=float)
    sched = scheduled_basal_at(predictions.index, therapy_path)
    abs_rate_uhr = sched + predictions["candidateDose"] * 60.0 / DT_MIN
    rows = []
    for ts, rate in abs_rate_uhr.items():
        rows.append({
            "_t": ts,
            "volume": rate * DT_MIN / 60.0,
            "delivery_type": "basal",
            "automatic": True,
            "insulin_type": "rapidActingAdult",
            "endDate": ts + pd.Timedelta(minutes=DT_MIN),
            "rate_uhr": rate,
        })
    if manual_boluses_df is not None and len(manual_boluses_df):
        for ts, mb in manual_boluses_df.iterrows():
            rows.append({
                "_t": ts,
                "volume": float(mb["volume"]),
                "delivery_type": "bolus",
                "automatic": False,
                "insulin_type": "rapidActingAdult",
                "endDate": ts,
                "rate_uhr": float("nan"),
            })
    df = pd.DataFrame(rows).set_index("_t").sort_index()
    return loop_iob(df, therapy_path, iob_grid)


ExtraPanel = Callable[
    [object, Sequence["SimTrace"], pd.Timestamp, pd.Timestamp, pd.Timestamp],
    Optional[str],
]
"""Signature for an experiment-specific extra panel.

Called as ``fn(ax, traces, win_start, win_end, t_center)``. ``ax`` is a
``matplotlib.axes.Axes``. The callable draws into the axis and may return a
short label string used for the y-axis if the callable doesn't set one.

Pre-built helpers below: ``panel_isf_mult``, ``panel_predictions_field``,
``panel_signal_csv``. Scripts can also pass their own inline callables.
"""


def panel_isf_mult(ax, traces, win_start, win_end, t_center) -> Optional[str]:
    """Per-trace ISF schedule normalized to that trace's window-median ISF."""
    plotted = False
    for tr in traces:
        isf = tr.predictions["isf"]
        isf_win = isf.loc[(isf.index >= win_start) & (isf.index <= win_end)]
        if len(isf_win) == 0 or isf_win.nunique() <= 1:
            continue
        med = isf_win.median()
        mult = isf_win / med if med > 0 else isf_win
        ax.plot(mult.index, mult.values, "-", color=tr.color, lw=1.4,
                label=f"{tr.label} (median ISF={med:.0f})")
        plotted = True
    if not plotted:
        return None
    ax.axhline(1.0, color="grey", lw=0.5)
    ax.axvline(t_center, ls=":", color="purple", alpha=0.5)
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)
    return "ISF / median"


def panel_predictions_field(field: str, label: Optional[str] = None,
                            color_by_trace: bool = True) -> ExtraPanel:
    """Overlay a column from each trace's `predictions` DataFrame.

    Useful for columns like ``deltaDose``, ``candidateBolus``, ``candidateTempRate``.
    """
    def _impl(ax, traces, win_start, win_end, t_center) -> Optional[str]:
        plotted = False
        for tr in traces:
            if field not in tr.predictions.columns:
                continue
            s = tr.predictions[field].loc[
                (tr.predictions.index >= win_start) & (tr.predictions.index <= win_end)
            ]
            if len(s) == 0:
                continue
            ax.plot(s.index, s.values, "-", color=tr.color if color_by_trace else None,
                    lw=1.3, label=f"{tr.label}.{field}")
            plotted = True
        if not plotted:
            return None
        ax.axhline(0, color="grey", lw=0.5)
        ax.axvline(t_center, ls=":", color="purple", alpha=0.5)
        ax.legend(loc="upper right", fontsize=9)
        ax.grid(True, alpha=0.3)
        return label or field
    return _impl


def panel_field_vs_candidate(cand_col: str, field_col: Optional[str], label: str,
                             unit: str = "", fill: bool = False,
                             ground_truth: Optional[pd.Series] = None) -> ExtraPanel:
    """Extra panel overlaying a Loop internal-state column, field vs candidate.

    ``field_col`` is the BASELINE column — OUR algorithm (the sim's baseline
    arm) recomputed on the REAL glucose/doses/carbs. It is NOT the deployed
    Loop's recorded value; label it as a reconstruction, not "field". ``cand_col``
    is the candidate column. Baseline drawn once in black; each candidate in its
    trace color. ``fill=True`` shades non-negative quantities (e.g. COB) to zero.
    """
    def _impl(ax, traces, win_start, win_end, t_center) -> Optional[str]:
        plotted = False
        if field_col:
            t0 = traces[0].predictions
            fw = t0.loc[(t0.index >= win_start) & (t0.index <= win_end)]
            if field_col in fw and fw[field_col].notna().any():
                ax.plot(fw.index, fw[field_col].values, "-", color="black", lw=1.6,
                        alpha=0.6, label=f"sim-Loop·real-inputs {label} (recon)")
                if fill:
                    ax.fill_between(fw.index, 0, fw[field_col].values, color="black", alpha=0.06)
                plotted = True
        for tr in traces:
            pw = tr.predictions.loc[(tr.predictions.index >= win_start) & (tr.predictions.index <= win_end)]
            if cand_col not in pw or not pw[cand_col].notna().any():
                continue
            ax.plot(pw.index, pw[cand_col].values, "-", color=tr.color, lw=1.5,
                    alpha=0.8, label=f"{tr.label} {label}")
            if fill:
                ax.fill_between(pw.index, 0, pw[cand_col].values, color=tr.color, alpha=0.08)
            plotted = True
        # deployed-Loop ground truth (devicestatus), where it exists — grey dotted.
        if ground_truth is not None and len(ground_truth):
            gw = ground_truth.loc[(ground_truth.index >= win_start) & (ground_truth.index <= win_end)].dropna()
            if len(gw):
                ax.plot(gw.index, gw.values, ":", color="grey", lw=1.2, alpha=0.8,
                        label=f"field {label} (devicestatus)")
                plotted = True
        if not plotted:
            return None
        ax.axhline(0, color="grey", lw=0.5)
        ax.axvline(t_center, ls=":", color="purple", alpha=0.5)
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.3)
        return f"{label} ({unit})" if unit else label
    return _impl


def panel_oracle_components(csv_path: str | Path,
                            time_col: str = "time",
                            v_insulin_col: str = "v_insulin",
                            v_cgm_col: str = "c_vcgm",
                            sens_col: str = "sens",
                            mult_col: str = "mult_smoothed",
                            fire_col: Optional[str] = "fire",
                            sens_thresh: Optional[float] = 0.05,
                            tz: pytz.BaseTzInfo = TZ_DEFAULT) -> ExtraPanel:
    """Plot v_insulin / v_cgm / sens-signal / mult on one panel.

    Velocities (v_insulin, v_cgm, sens) share the left y-axis in mg/dL/min.
    The oracle multiplier sits on a twinned right y-axis. When ``fire_col`` is
    present, the moments where the detector fired are shaded.

    Designed for the ICE-based ISF oracle signal, but the column names are
    parameterized so the same panel can serve other detectors that emit
    similar (signal, multiplier) pairs.
    """
    csv_path = Path(csv_path)

    def _impl(ax, traces, win_start, win_end, t_center) -> Optional[str]:
        if not csv_path.exists():
            ax.text(0.5, 0.5, f"missing {csv_path.name}",
                    transform=ax.transAxes, ha="center")
            return "oracle signal"
        df = pd.read_csv(csv_path)
        ts = pd.to_datetime(df[time_col])
        if ts.dt.tz is None:
            ts = ts.dt.tz_localize("UTC")
        df["_t"] = ts.dt.tz_convert(tz)
        df = df.set_index("_t").sort_index()
        df = df.loc[(df.index >= win_start) & (df.index <= win_end)]
        if df.empty:
            ax.text(0.5, 0.5, "no diagnostic rows in window",
                    transform=ax.transAxes, ha="center")
            return "oracle signal"

        # Fire shading first so other lines draw on top
        if fire_col and fire_col in df.columns:
            fire = df[fire_col].astype(float)
            in_fire = False
            start = None
            for t, v in fire.items():
                if v > 0.5 and not in_fire:
                    in_fire = True
                    start = t
                elif v <= 0.5 and in_fire:
                    ax.axvspan(start, t, color="tab:orange", alpha=0.10, lw=0)
                    in_fire = False
            if in_fire:
                ax.axvspan(start, df.index[-1], color="tab:orange", alpha=0.10, lw=0)

        if v_insulin_col in df.columns:
            ax.plot(df.index, df[v_insulin_col], "-", color="tab:blue", lw=1.4,
                    label="v_insulin (mg/dL/min)")
        if v_cgm_col in df.columns:
            ax.plot(df.index, df[v_cgm_col], "-", color="black", lw=1.4,
                    label="v_cgm (causal 15min, mg/dL/min)")
        if sens_col in df.columns:
            ax.plot(df.index, df[sens_col], "-", color="tab:green", lw=1.2,
                    label="sens = v_insulin − v_cgm")
        ax.axhline(0, color="grey", lw=0.5)
        if sens_thresh is not None:
            ax.axhline(sens_thresh, color="tab:green", lw=0.5, ls=":")
        ax.axvline(t_center, ls=":", color="purple", alpha=0.5)
        ax.set_ylabel("velocity (mg/dL/min)")
        ax.grid(True, alpha=0.3)
        # Sym-clip to keep velocities visible even with one extreme reading
        try:
            vals = pd.concat([df[c] for c in (v_insulin_col, v_cgm_col, sens_col)
                              if c in df.columns]).dropna()
            if len(vals):
                q = np.nanmax(np.abs(np.nanpercentile(vals, [2, 98])))
                ax.set_ylim(-q * 1.2, q * 1.2)
        except Exception:
            pass
        ax.legend(loc="upper left", fontsize=9)

        if mult_col in df.columns:
            ax2 = ax.twinx()
            ax2.fill_between(df.index, 1.0, df[mult_col].values,
                             where=(df[mult_col].values > 1.0),
                             color="tab:red", alpha=0.18, step="post",
                             label="oracle mult")
            ax2.plot(df.index, df[mult_col].values, "-", color="tab:red", lw=1.0)
            ax2.axhline(1.0, color="tab:red", lw=0.4, alpha=0.4)
            ax2.set_ylabel("oracle mult", color="tab:red")
            ax2.tick_params(axis="y", labelcolor="tab:red")
            top = max(1.3, float(df[mult_col].max()) * 1.05)
            ax2.set_ylim(0.95, top)
            ax2.legend(loc="upper right", fontsize=9)
        return "velocity (mg/dL/min)"
    return _impl


def panel_signal_csv(csv_path: str | Path,
                     label: Optional[str] = None,
                     time_col: str = "time",
                     value_col: str = "value",
                     color: str = "tab:cyan",
                     yref: Optional[float] = None,
                     tz: pytz.BaseTzInfo = TZ_DEFAULT) -> ExtraPanel:
    """Generic per-step signal overlaid from a CSV.

    The CSV should have a time column (default ``time``) and a value column
    (default ``value``). Rows outside [win_start, win_end] are filtered out.
    """
    csv_path = Path(csv_path)
    label = label or csv_path.stem

    def _impl(ax, traces, win_start, win_end, t_center) -> Optional[str]:
        if not csv_path.exists():
            ax.text(0.5, 0.5, f"missing {csv_path.name}",
                    transform=ax.transAxes, ha="center")
            return label
        df = pd.read_csv(csv_path)
        # Normalize timezone — accept either tz-aware or naive
        ts = pd.to_datetime(df[time_col])
        if ts.dt.tz is None:
            ts = ts.dt.tz_localize("UTC")
        df["_t"] = ts.dt.tz_convert(tz)
        df = df.set_index("_t").sort_index()
        df = df.loc[(df.index >= win_start) & (df.index <= win_end)]
        if df.empty:
            return label
        ax.plot(df.index, df[value_col].values, "-", color=color, lw=1.4,
                label=label)
        if yref is not None:
            ax.axhline(yref, color="grey", lw=0.5)
        ax.axvline(t_center, ls=":", color="purple", alpha=0.5)
        ax.legend(loc="upper right", fontsize=9)
        ax.grid(True, alpha=0.3)
        return label
    return _impl


def _draw_delivery_panel(ax, traces: Sequence[SimTrace],
                         win_start: pd.Timestamp, win_end: pd.Timestamp) -> None:
    """Standard delivery rendering from the canonical `delivery` stream.

    ONE shared numeric axis (basal rate U/hr and boluses U live on the same
    scale — different units but comparable magnitude). Basal is drawn as a
    staircase: horizontal at each rate with a vertical connector at every rate
    change (a real gap in the stream breaks the line rather than bridging).
    Boluses are stems: ``o`` filled = automatic, ``D`` hollow = manual. Field
    (real pump, black) and each candidate (trace color) are semi-transparent so
    they read where they overlap — which is most of the time.
    """
    import numpy as np
    import matplotlib.lines as mlines

    def draw_basal(d, color, alpha):
        b = d[d["kind"] == "basal"].sort_index()
        if not len(b):
            return
        xs: list = []
        ys: list = []
        prev_end = None
        for t0, r in b.iterrows():
            te = r["tEnd"] if pd.notna(r["tEnd"]) else t0
            if te < win_start or t0 > win_end:
                continue
            # break the line at a real gap (non-contiguous spans), so we don't
            # bridge across scheduled-basal stretches not present in the stream.
            if prev_end is not None and (t0 - prev_end) > pd.Timedelta(minutes=1):
                xs.append(prev_end); ys.append(np.nan)
            xs.append(max(t0, win_start)); ys.append(r["rateUhr"])
            xs.append(min(te, win_end)); ys.append(r["rateUhr"])
            prev_end = te
        # consecutive (end_i, rate_i) -> (start_{i+1}, rate_{i+1}) at the same x
        # renders the vertical connector at each inflection point automatically.
        ax.plot(xs, ys, "-", color=color, lw=1.5, alpha=alpha, solid_capstyle="butt")

    def draw_bolus(d, color, alpha):
        b = d[(d["kind"] == "bolus") & (d.index >= win_start) & (d.index <= win_end)]
        for auto, marker, fill in [(True, "o", True), (False, "D", False)]:
            s = b[(b["automatic"] == auto) & (b["amountU"] > 0)]
            if not len(s):
                continue
            ax.vlines(s.index, 0, s["amountU"], color=color, lw=1.2, alpha=alpha)
            ax.scatter(s.index, s["amountU"], marker=marker, s=42, zorder=5,
                       alpha=min(1.0, alpha + 0.2),
                       facecolors=(color if fill else "none"), edgecolors=color, linewidths=1.4)

    # Field: same real pump across traces — draw once from the first that has it.
    field_src = next((tr.delivery for tr in traces if len(tr.delivery)
                      and (tr.delivery["source"] == "field").any()), None)
    if field_src is not None:
        fd = field_src[field_src["source"] == "field"]
        draw_basal(fd, "black", 0.55)
        draw_bolus(fd, "black", 0.55)
    for tr in traces:
        if not len(tr.delivery):
            continue
        cd = tr.delivery[tr.delivery["source"] == "candidate"]
        draw_basal(cd, tr.color, 0.6)
        draw_bolus(cd, tr.color, 0.6)

    ax.set_ylabel("basal (U/hr) · bolus (U)")
    # Lift 0 off the bottom spine so a suspend (basal == 0) line is visible and
    # doesn't merge with the axis; faint reference at 0.
    top = max(ax.get_ylim()[1], 0.5)
    ax.set_ylim(bottom=-0.04 * top, top=top)
    ax.axhline(0, color="grey", lw=0.6, alpha=0.5, zorder=1)
    # Legend: sources (color) + basal/bolus + auto/manual glyphs.
    handles = [mlines.Line2D([], [], color="black", lw=1.5, alpha=0.7, label="field basal (real pump)"),
               mlines.Line2D([], [], color="black", marker="o", ls="none", label="field bolus — auto"),
               mlines.Line2D([], [], color="black", marker="D", markerfacecolor="none", ls="none",
                             label="field bolus — manual")]
    for tr in traces:
        if not len(tr.delivery):
            continue
        cb = tr.delivery[tr.delivery["source"] == "candidate"]
        handles.append(mlines.Line2D([], [], color=tr.color, lw=1.5, alpha=0.75,
                                     label=f"{tr.label} basal"))
        handles.append(mlines.Line2D([], [], color=tr.color, marker="o", ls="none",
                                     label=f"{tr.label} bolus (auto)"))
        if ((cb["kind"] == "bolus") & (~cb["automatic"]) & (cb["amountU"] > 0)).any():
            handles.append(mlines.Line2D([], [], color=tr.color, marker="D", markerfacecolor="none",
                                         ls="none", label=f"{tr.label} bolus (manual, resized)"))
    ax.legend(handles=handles, loc="upper left", fontsize=8, ncol=2)


def plot_case(traces: Sequence[SimTrace],
              t_center: pd.Timestamp,
              window_hours: float = 12.0,
              nightscout_host: Optional[str] = None,
              out: Optional[str | Path] = None,
              title: Optional[str] = None,
              extra_panels: Sequence[ExtraPanel] = (),
              outages: Optional[Sequence] = None,
              cgm_gaps: Optional[Sequence] = None,
              show_devicestatus: bool = True,
              show_carbs: bool = True,
              extra_panel_height: float = 1.5,
              dpi: int = 120) -> Path:
    """Produce a multi-panel case-study figure centered on `t_center`.

    Standard panels (always shown):
      0) BG: each trace's counter_BG + real actual_BG + threshold lines + carbs/manual
      1) Dose: real pump bars (black) + sim absolute delivery bars per trace
      2) IOB: real (computed via loop_iob from cached doses), sim per trace,
             optional devicestatus reference

    Each callable in `extra_panels` adds one panel below the standard three.
    Use the pre-built helpers (``panel_isf_mult``, ``panel_predictions_field``,
    ``panel_signal_csv``) or supply your own. If a helper detects nothing to
    plot, it can return ``None`` — the panel still appears but stays blank.
    """
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from loopeval_analysis.glucose import (
        find_doses_cache, load_doses_cache, find_therapy_cache, scheduled_basal_at,
    )
    from loopeval_analysis.iob import loop_iob

    if not traces:
        raise ValueError("plot_case requires at least one SimTrace")
    tz = traces[0].tz
    if t_center.tzinfo is None:
        t_center = tz.localize(t_center) if hasattr(tz, "localize") else t_center.tz_localize(tz)
    elif t_center.tz != tz:
        t_center = t_center.tz_convert(tz)
    win_start, win_end = _resolve_window(t_center, window_hours, tz)

    # Heuristic: pick host from a trace label if not given (e.g., "user1 ...")
    host = nightscout_host or "https://your-ns.example.com"
    # Resolve cache hostname from the URL
    cache_host = host.replace("https://", "").replace("http://", "").rstrip("/")
    try:
        doses_cache_path = find_doses_cache(cache_host)
        therapy_path = find_therapy_cache(cache_host)
    except Exception as exc:  # noqa: BLE001
        print(f"[case_study] cache lookup failed for host '{cache_host}': {exc}", file=sys.stderr)
        raise
    doses = load_doses_cache(doses_cache_path)

    real_auto = doses[~((doses["delivery_type"] != "basal") & (~doses["automatic"]))]
    manual_b = doses[(doses["delivery_type"] != "basal") & (~doses["automatic"])]
    manual_in_window = manual_b[(manual_b.index >= win_start) & (manual_b.index <= win_end)]
    carbs_win = load_carbs_in_window(win_start, win_end, tz=tz) if show_carbs else pd.DataFrame()

    # Use the first trace's prediction grid as the canonical step grid
    pw0 = traces[0].predictions.loc[
        (traces[0].predictions.index >= win_start) & (traces[0].predictions.index <= win_end)
    ]
    if pw0.empty:
        raise ValueError(f"no predictions in window {win_start}..{win_end} for {traces[0].path}")
    step_index = pw0.index
    real_step = rasterize_real_doses(real_auto, step_index)
    sched = scheduled_basal_at(step_index, therapy_path) * DT_MIN / 60.0

    # IOB grid: extend back ~6h before window for warm-up
    iob_grid = pd.date_range(win_start, win_end, freq=f"{int(DT_MIN)}min", tz=tz)
    iob_lookback_start = win_start - pd.Timedelta(hours=6, minutes=30)
    real_iob_doses = doses[(doses.index >= iob_lookback_start) & (doses.index <= win_end)]
    real_iob_computed = loop_iob(real_iob_doses, therapy_path, iob_grid)
    devicestatus_iob = (
        fetch_devicestatus_iob(host, win_start, win_end, tz=tz)
        if show_devicestatus else pd.Series(dtype=float)
    )

    n_panels = 3 + len(extra_panels)
    height_ratios = [3, 2, 2] + [extra_panel_height] * len(extra_panels)
    fig, axes = plt.subplots(n_panels, 1, figsize=(20, 4 + 3 * n_panels),
                             sharex=True, gridspec_kw={"height_ratios": height_ratios})
    if n_panels == 1:
        axes = [axes]
    plt.rcParams.update({"font.size": 11})

    # ---- Outage / CGM-gap shading (drawn first so traces sit on top) ---------
    outages_in_window: list = []
    if outages:
        for o in outages:
            if o.overlaps(win_start, win_end):
                outages_in_window.append(o)
    cgm_gaps_in_window: list = []
    if cgm_gaps:
        for g in cgm_gaps:
            if g.overlaps(win_start, win_end):
                cgm_gaps_in_window.append(g)

    def _shade(ax):
        for o in outages_in_window:
            ax.axvspan(max(o.start.tz_convert(tz), win_start),
                       min(o.end.tz_convert(tz), win_end),
                       color="grey", alpha=0.18, lw=0,
                       label=("pump outage" if o is outages_in_window[0] else None))
        for g in cgm_gaps_in_window:
            ax.axvspan(max(g.start.tz_convert(tz), win_start),
                       min(g.end.tz_convert(tz), win_end),
                       color="tab:blue", alpha=0.10, lw=0,
                       label=("CGM gap" if g is cgm_gaps_in_window[0] else None))

    # ---- Panel 0: BG ----------------------------------------------------------
    ax = axes[0]
    _shade(ax)
    ab = traces[0].actual_bg.loc[
        (traces[0].actual_bg.index >= win_start) & (traces[0].actual_bg.index <= win_end)
    ]
    ax.plot(ab.index, ab.values, "-o", color="black", lw=1, ms=2.5,
            label="real actual BG (deployed Loop)")
    for tr, color in zip(traces, _DEFAULT_COLORS):
        cb = tr.counter_bg.loc[(tr.counter_bg.index >= win_start) & (tr.counter_bg.index <= win_end)]
        c = tr.color if tr.color != _DEFAULT_COLORS[0] or len(traces) == 1 else color
        tr.color = c
        ax.plot(cb.index, cb.values, "-o", color=c, lw=1.6, ms=2.5,
                label=f"counter — {tr.label}")
    ax.axhline(70, ls="--", color="red", alpha=0.4)
    ax.axhline(54, ls="--", color="darkred", alpha=0.5)
    ax.axhline(180, ls="--", color="orange", alpha=0.4)
    ax.axvline(t_center, ls=":", color="purple", alpha=0.6, label=f"t = {t_center.strftime('%H:%M')}")
    for ts, mb in manual_in_window.iterrows():
        ax.annotate(f"manual {mb['volume']:.1f}U", xy=(ts, 50), color="blue",
                    fontsize=8, rotation=90, va="bottom")
    if len(carbs_win):
        for _, c in carbs_win.iterrows():
            ax.annotate(f"{c['grams']:.0f}g", xy=(c['entry_t'], 260), color="green",
                        fontsize=9, rotation=90, va="bottom")
    ax.set_ylabel("BG (mg/dL)")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)
    bg_lo = min(40.0, ab.min() - 10.0,
                min((tr.counter_bg.loc[(tr.counter_bg.index >= win_start) & (tr.counter_bg.index <= win_end)].min())
                    for tr in traces) - 10.0)
    bg_hi = max(300.0,
                max((tr.counter_bg.loc[(tr.counter_bg.index >= win_start) & (tr.counter_bg.index <= win_end)].max())
                    for tr in traces) + 20.0,
                ab.max() + 20.0)
    ax.set_ylim(max(0, bg_lo), bg_hi)
    if title is None:
        title = f"Case study around {t_center.strftime('%Y-%m-%d %H:%M %Z')}"
    ax.set_title(title)

    # ---- Panel 1: Delivery (canonical stream) --------------------------------
    # Basal = rate segments (U/hr, left axis); boluses = stems (U, right axis),
    # auto = filled marker, manual = hollow marker. Field (real pump) + each
    # candidate. Reads the trace `delivery` stream — never `baselineDose` (which
    # is a decision-time recommendation, not delivery).
    ax = axes[1]
    _shade(ax)
    have_delivery = any(len(tr.delivery) for tr in traces)
    if have_delivery:
        _draw_delivery_panel(ax, traces, win_start, win_end)
    else:
        # Legacy fallback: reconstruct absolute delivery from caches (old traces).
        bar_width = pd.Timedelta(minutes=1.5).to_pytimedelta()
        ax.bar(step_index, real_step.values, width=bar_width, color="black",
               alpha=0.7, label="real auto pump (U/5min)")
        for tr in traces:
            pw = tr.predictions.loc[(tr.predictions.index >= win_start) & (tr.predictions.index <= win_end)]
            sim_abs = sched.reindex(pw.index).values + pw["candidateDose"].values
            ax.bar(pw.index, sim_abs, width=bar_width, color=tr.color, alpha=0.6, label=tr.label)
        ax.set_ylabel("Insulin delivered (U / 5min)")
        ax.legend(loc="upper left", fontsize=9)
    ax.axhline(0, color="grey", lw=0.5)
    ax.axvline(t_center, ls=":", color="purple", alpha=0.5)
    ax.grid(True, alpha=0.3)

    # ---- Panel 2: PATIENT IOB -------------------------------------------------
    # Independent, apples-to-apples IOB: field dosing and candidate dosing each
    # run through the SAME patient insulin model (trace `patientIOBField` /
    # `patientIOBCandidate`). NOT the NS devicestatus IOB (post-dose timing) and
    # NOT the candidate algorithm's own IOB (which may have method changes). The
    # devicestatus series is drawn faint as an external reference only. Falls back
    # to baselineIOB/candidateIOB, then cache, for traces predating patient IOB.
    ax = axes[2]
    _shade(ax)
    p0 = traces[0].predictions
    fw = p0.loc[(p0.index >= win_start) & (p0.index <= win_end)]
    if "patientIOBField" in fw and fw["patientIOBField"].notna().any():
        ax.plot(fw.index, fw["patientIOBField"].values, "-", color="black", lw=1.8,
                label="patient IOB — field dosing")
    elif "baselineIOB" in fw and fw["baselineIOB"].notna().any():
        ax.plot(fw.index, fw["baselineIOB"].values, "-", color="black", lw=1.8,
                label="field IOB (algo)")
    else:
        ax.plot(real_iob_computed.index, real_iob_computed.values, "-",
                color="black", lw=1.8, label="real IOB (computed, cache)")
    if len(devicestatus_iob) > 0:
        ax.plot(devicestatus_iob.index, devicestatus_iob.values, ":",
                color="grey", lw=1, alpha=0.6, label="field IOB (devicestatus ref)")
    for tr in traces:
        pw = tr.predictions.loc[(tr.predictions.index >= win_start) & (tr.predictions.index <= win_end)]
        if "patientIOBCandidate" in pw and pw["patientIOBCandidate"].notna().any():
            ax.plot(pw.index, pw["patientIOBCandidate"].values, "-", color=tr.color, lw=1.6,
                    label=f"patient IOB — {tr.label} dosing")
        elif "candidateIOB" in pw and pw["candidateIOB"].notna().any():
            ax.plot(pw.index, pw["candidateIOB"].values, "-", color=tr.color, lw=1.6,
                    label=f"sim IOB (algo) — {tr.label}")
        else:
            pw2 = tr.predictions.loc[(tr.predictions.index >= iob_lookback_start) & (tr.predictions.index <= win_end)]
            sim_iob = _build_sim_iob(pw2, iob_grid, therapy_path, manual_in_window)
            ax.plot(sim_iob.index, sim_iob.values, "-", color=tr.color, lw=1.6,
                    label=f"sim IOB — {tr.label}")
    ax.axhline(0, color="grey", lw=0.5, alpha=0.4)
    for ts, mb in manual_in_window.iterrows():
        ax.axvline(ts, color="blue", alpha=0.2, lw=0.7)
    ax.axvline(t_center, ls=":", color="purple", alpha=0.5)
    ax.set_ylabel("IOB (U)")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)

    # ---- Extra panels (experiment-specific) ----------------------------------
    for k, panel_fn in enumerate(extra_panels):
        ax = axes[3 + k]
        try:
            label = panel_fn(ax, traces, win_start, win_end, t_center)
        except Exception as exc:  # noqa: BLE001
            print(f"  [case_study] extra panel {k} raised: {exc}", file=sys.stderr)
            label = "(panel failed)"
        if label and not ax.get_ylabel():
            ax.set_ylabel(label)

    axes[-1].set_xlabel(f"Time ({t_center.strftime('%Z')})")
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M", tz=tz))
    import matplotlib.pyplot as plt2
    plt2.setp(axes[-1].xaxis.get_majorticklabels(), rotation=30)

    fig.tight_layout()
    if out is None:
        out = Path(f"case_{t_center.strftime('%Y%m%d_%H%M')}.png")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi)
    import matplotlib.pyplot as plt3
    plt3.close(fig)
    return out


# --------------------------------------------------------------------------- #
#  Multi-event HTML report                                                    #
# --------------------------------------------------------------------------- #

def build_case_report(traces: Sequence[SimTrace],
                      events: pd.DataFrame,
                      out_html: str | Path,
                      *,
                      window_hours: float = 12.0,
                      max_events: int = 8,
                      nightscout_host: Optional[str] = None,
                      title: str = "Case-study report",
                      extra_panels: Sequence[ExtraPanel] = (),
                      outages: Optional[Sequence] = None,
                      cgm_gaps: Optional[Sequence] = None,
                      exclude_outage_events: bool = False,
                      center_on: str = "nadir",
                      center_offset_hours: float = 0.0,
                      images_dir: Optional[str | Path] = None) -> Path:
    """Render per-event plots.

    ``center_on`` picks which timestamp from each event row drives the plot
    window: ``"nadir"`` (default, where BG bottoms out), ``"start"`` (first
    sub-threshold sample — answers "what dose decisions led here?"), or
    ``"end"``.

    ``center_offset_hours`` shifts the center after that choice. Use
    ``center_on="start", center_offset_hours=-1`` to see the hour of descent
    that leads into the low.
    """
    """Render one plot per event into an HTML report.

    `events` is the DataFrame returned by `enumerate_lows`. The first `max_events`
    rows are plotted. Images go alongside `out_html` unless `images_dir` is given.
    """
    out_html = Path(out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    images_dir = Path(images_dir) if images_dir else out_html.parent
    images_dir.mkdir(parents=True, exist_ok=True)

    events_for_report = events
    if exclude_outage_events and "in_outage" in events.columns:
        events_for_report = events[~events["in_outage"]].reset_index(drop=True)
    chosen = events_for_report.head(max_events).copy().reset_index(drop=True)
    if len(chosen) == 0:
        out_html.write_text(f"<h1>{title}</h1><p>No qualifying events.</p>")
        return out_html

    rendered = []
    for idx, row in chosen.iterrows():
        nadir = row["nadir_t"]
        png_name = f"case_{idx+1:02d}_{nadir.strftime('%Y%m%d_%H%M')}.png"
        out_png = images_dir / png_name
        outage_flag = ""
        if "in_outage" in row.index and row["in_outage"]:
            outage_flag = f"  [OUTAGE: {row.get('outage_source','')}]"
        plot_case(
            traces=traces,
            t_center=nadir,
            window_hours=window_hours,
            nightscout_host=nightscout_host,
            out=out_png,
            extra_panels=extra_panels,
            outages=outages,
            cgm_gaps=cgm_gaps,
            title=(f"#{idx+1}  {nadir.strftime('%a %b %d %H:%M')}  "
                   f"min={row['min_bg']:.0f}  dur={row['duration_min']:.0f}min  "
                   f"depth={row['depth_mg_min']:.0f} mg·min  "
                   f"{'(severe <54)' if row['severe_t54'] else ''}"
                   f"{outage_flag}"),
        )
        rel = out_png.relative_to(out_html.parent) if out_png.is_relative_to(out_html.parent) else out_png
        rendered.append((idx, row, rel))

    has_outage_col = "in_outage" in chosen.columns
    rows_html = []
    for idx, row, rel in rendered:
        outage_cell = ""
        row_style = ""
        if has_outage_col and row.get("in_outage"):
            outage_cell = f"<span title='{row.get('outage_source','')}'>⚠ OUTAGE</span>"
            row_style = " style='background:#fff3cd;'"
        rows_html.append(
            f"<tr{row_style}><td>{idx+1}</td><td>{row['nadir_t'].strftime('%Y-%m-%d %H:%M')}</td>"
            f"<td>{row['min_bg']:.0f}</td><td>{row['duration_min']:.0f}</td>"
            f"<td>{row['depth_mg_min']:.0f}</td>"
            f"<td>{'✓' if row['severe_t54'] else ''}</td>"
            f"<td>{outage_cell}</td>"
            f"<td><a href='#case-{idx+1}'>jump</a></td></tr>"
        )
    figs_html = []
    for idx, row, rel in rendered:
        figs_html.append(
            f"<a id='case-{idx+1}'></a><h2>Case #{idx+1} — {row['nadir_t'].strftime('%a %b %d %H:%M')}</h2>"
            f"<p>min BG <b>{row['min_bg']:.0f}</b>, duration {row['duration_min']:.0f}min, "
            f"depth {row['depth_mg_min']:.0f} mg·min "
            f"{'(severe &lt;54)' if row['severe_t54'] else ''}</p>"
            f"<img src='{rel}' style='max-width:100%; border:1px solid #ddd;'/>"
        )
    traces_html = "<ul>" + "".join(
        f"<li><b>{t.label}</b> — <code>{t.path.name}</code></li>" for t in traces
    ) + "</ul>"
    html = f"""<!doctype html>
<html><head><meta charset='utf-8'>
<title>{title}</title>
<style>
 body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 1400px; margin: 1em auto; padding: 0 1em; }}
 table {{ border-collapse: collapse; margin: 1em 0; }}
 th, td {{ border: 1px solid #ccc; padding: 4px 8px; text-align: right; }}
 th:first-child, td:first-child {{ text-align: center; }}
 th, td:nth-child(2) {{ text-align: left; }}
 h2 {{ margin-top: 2em; border-top: 2px solid #eee; padding-top: 0.5em; }}
</style>
</head><body>
<h1>{title}</h1>
<h3>Traces</h3>
{traces_html}
<h3>Event index</h3>
<table>
 <thead><tr><th>#</th><th>nadir</th><th>min BG</th><th>dur (min)</th>
 <th>depth mg·min</th><th>severe &lt;54</th><th>outage</th><th></th></tr></thead>
 <tbody>{''.join(rows_html)}</tbody>
</table>
{''.join(figs_html)}
</body></html>
"""
    out_html.write_text(html)
    return out_html


# --------------------------------------------------------------------------- #
#  CLI                                                                        #
# --------------------------------------------------------------------------- #

def _parse_time(s: str, tz: pytz.BaseTzInfo = TZ_DEFAULT) -> pd.Timestamp:
    ts = pd.to_datetime(s)
    if ts.tzinfo is None:
        ts = ts.tz_localize(tz)
    else:
        ts = ts.tz_convert(tz)
    return ts


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="case_study",
                                     description="Case-study tooling for LoopEval sim traces")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_lows = sub.add_parser("lows", help="enumerate hypo events in a trace")
    p_lows.add_argument("trace", help="path to SimulateCommand trace JSON")
    p_lows.add_argument("--threshold", type=float, default=70.0)
    p_lows.add_argument("--min-duration-min", type=float, default=10.0)
    p_lows.add_argument("--top", type=int, default=12)
    p_lows.add_argument("--use-actual", action="store_true",
                        help="enumerate against actual_BG instead of counter_BG")
    p_lows.add_argument("--csv-out", default=None)
    p_lows.add_argument("--outages-csv", default=None,
                        help="path to outage CSV; flags events whose nadir falls in an outage")
    p_lows.add_argument("--outage-pad-hours", type=float, default=0.0)

    def _add_extra_panel_args(p):
        p.add_argument("--isf-mult-panel", action="store_true",
                       help="add an ISF-multiplier overlay panel below the IOB panel")
        p.add_argument("--predictions-field", action="append", default=[],
                       help="add a panel overlaying this column from each trace's "
                            "predictions DataFrame (e.g. deltaDose). Repeatable.")
        p.add_argument("--signal-csv", action="append", default=[],
                       help="add a panel from a CSV. Format: PATH[:label[:time_col[:value_col[:color]]]]. "
                            "Repeatable.")
        p.add_argument("--oracle-components-csv", default=None,
                       help="path to a diagnostic CSV with columns time, v_insulin, c_vcgm, "
                            "sens, fire, mult_smoothed — adds a single panel showing all of "
                            "them together (velocity scale on left, oracle mult on right).")
        p.add_argument("--cgm-gaps-csv", default=None,
                       help="CGM-gap CSV (start,end,...) — shades gap windows in blue "
                            "(distinct from grey pump outages). Generate with "
                            "`python -m loopeval_analysis.cgm_gaps from-cache ...`")

    p_plot = sub.add_parser("plot", help="generate a single case-study figure")
    p_plot.add_argument("trace", help="primary trace JSON")
    p_plot.add_argument("--time", required=True, help='center timestamp (e.g. "2026-04-02 01:05")')
    p_plot.add_argument("--window-hours", type=float, default=12.0)
    p_plot.add_argument("--compare", nargs="*", default=[],
                        help="additional trace JSONs to overlay (max ~3)")
    p_plot.add_argument("--labels", nargs="*", default=[],
                        help="optional labels matching trace + compare order")
    p_plot.add_argument("--nightscout", default="https://your-ns.example.com")
    p_plot.add_argument("--out", default=None)
    p_plot.add_argument("--title", default=None)
    p_plot.add_argument("--outages-csv", default=None,
                        help="outage CSV path; shades pump-outage windows in grey")
    _add_extra_panel_args(p_plot)

    p_rep = sub.add_parser("report", help="multi-event HTML report")
    p_rep.add_argument("trace", help="primary trace JSON (events enumerated from this one)")
    p_rep.add_argument("--compare", nargs="*", default=[])
    p_rep.add_argument("--labels", nargs="*", default=[])
    p_rep.add_argument("--top", type=int, default=6)
    p_rep.add_argument("--window-hours", type=float, default=12.0)
    p_rep.add_argument("--threshold", type=float, default=70.0)
    p_rep.add_argument("--min-duration-min", type=float, default=10.0)
    p_rep.add_argument("--nightscout", default="https://your-ns.example.com")
    p_rep.add_argument("--out", required=True, help="path to write report.html")
    p_rep.add_argument("--title", default="Case-study report")
    p_rep.add_argument("--use-actual", action="store_true")
    p_rep.add_argument("--outages-csv", default=None,
                       help="outage CSV path; events overlapping outages are flagged")
    p_rep.add_argument("--outage-pad-hours", type=float, default=0.0,
                       help="pad both sides of each outage by this many hours when "
                            "deciding if an event falls inside one")
    p_rep.add_argument("--exclude-outage-events", action="store_true",
                       help="skip events whose nadir falls in an outage (don't render plots)")
    _add_extra_panel_args(p_rep)

    args = parser.parse_args(argv)

    if args.cmd == "lows":
        from loopeval_analysis.outage import read_outages_csv
        tr = load_trace(args.trace)
        outages = read_outages_csv(args.outages_csv) if args.outages_csv else None
        df = enumerate_lows(tr, threshold=args.threshold,
                            min_duration_min=args.min_duration_min,
                            use_actual=args.use_actual,
                            outages=outages,
                            outage_pad_hours=args.outage_pad_hours)
        if df.empty:
            print(f"No events meet threshold < {args.threshold} mg/dL for ≥ {args.min_duration_min}min.")
            return 0
        print(f"{len(df)} event(s) total. Top {min(args.top, len(df))}:\n")
        header = f"{'#':>2}  {'nadir':<20} {'dur(min)':>9} {'min':>6} {'depth':>9} {'sev':>4}"
        if "in_outage" in df.columns:
            header += "   outage"
        print(header)
        print("-" * (len(header) + 4))
        for i, r in df.head(args.top).iterrows():
            line = (f"{i+1:>2}  {r['nadir_t'].strftime('%Y-%m-%d %H:%M'):<20} "
                    f"{r['duration_min']:>9.0f} {r['min_bg']:>6.0f} {r['depth_mg_min']:>9.0f} "
                    f"{'YES' if r['severe_t54'] else '':>4}")
            if "in_outage" in df.columns:
                line += f"   {'⚠ ' + r['outage_source'] if r['in_outage'] else ''}"
            print(line)
        if args.csv_out:
            df.to_csv(args.csv_out, index=False)
            print(f"\n→ {args.csv_out}")
        return 0

    def _build_extra_panels(ns) -> list[ExtraPanel]:
        out: list[ExtraPanel] = []
        if getattr(ns, "isf_mult_panel", False):
            out.append(panel_isf_mult)
        for field in getattr(ns, "predictions_field", []) or []:
            out.append(panel_predictions_field(field))
        for spec in getattr(ns, "signal_csv", []) or []:
            parts = spec.split(":")
            path = parts[0]
            label = parts[1] if len(parts) > 1 else None
            time_col = parts[2] if len(parts) > 2 else "time"
            value_col = parts[3] if len(parts) > 3 else "value"
            color = parts[4] if len(parts) > 4 else "tab:cyan"
            out.append(panel_signal_csv(path, label=label,
                                        time_col=time_col, value_col=value_col, color=color))
        oc = getattr(ns, "oracle_components_csv", None)
        if oc:
            out.append(panel_oracle_components(oc))
        return out

    if args.cmd == "plot":
        from loopeval_analysis.outage import read_outages_csv
        from loopeval_analysis.cgm_gaps import read_cgm_gaps_csv
        labels = args.labels or []
        primary = load_trace(args.trace, label=labels[0] if labels else None)
        compares = [load_trace(p, label=labels[i + 1] if i + 1 < len(labels) else None,
                               color=_DEFAULT_COLORS[(i + 1) % len(_DEFAULT_COLORS)])
                    for i, p in enumerate(args.compare)]
        traces = [primary] + compares
        t = _parse_time(args.time, tz=primary.tz)
        extras = _build_extra_panels(args)
        outages = read_outages_csv(args.outages_csv) if getattr(args, "outages_csv", None) else None
        gaps = read_cgm_gaps_csv(args.cgm_gaps_csv) if getattr(args, "cgm_gaps_csv", None) else None
        out = plot_case(traces, t, window_hours=args.window_hours,
                        nightscout_host=args.nightscout, out=args.out, title=args.title,
                        extra_panels=extras, outages=outages, cgm_gaps=gaps)
        print(f"→ {out}")
        return 0

    if args.cmd == "report":
        labels = args.labels or []
        primary = load_trace(args.trace, label=labels[0] if labels else None)
        compares = [load_trace(p, label=labels[i + 1] if i + 1 < len(labels) else None,
                               color=_DEFAULT_COLORS[(i + 1) % len(_DEFAULT_COLORS)])
                    for i, p in enumerate(args.compare)]
        traces = [primary] + compares
        from loopeval_analysis.outage import read_outages_csv
        from loopeval_analysis.cgm_gaps import read_cgm_gaps_csv
        outages = read_outages_csv(args.outages_csv) if args.outages_csv else None
        gaps = read_cgm_gaps_csv(args.cgm_gaps_csv) if getattr(args, "cgm_gaps_csv", None) else None
        events = enumerate_lows(primary, threshold=args.threshold,
                                min_duration_min=args.min_duration_min,
                                use_actual=args.use_actual,
                                outages=outages,
                                outage_pad_hours=args.outage_pad_hours)
        extras = _build_extra_panels(args)
        out = build_case_report(traces, events, out_html=args.out,
                                window_hours=args.window_hours,
                                max_events=args.top,
                                nightscout_host=args.nightscout,
                                title=args.title,
                                extra_panels=extras,
                                outages=outages,
                                cgm_gaps=gaps,
                                exclude_outage_events=args.exclude_outage_events)
        n_shown = min(args.top, len(events) - (events["in_outage"].sum() if (outages and "in_outage" in events.columns and args.exclude_outage_events) else 0))
        print(f"→ {out}  ({n_shown} cases shown; "
              f"{events['in_outage'].sum() if 'in_outage' in events.columns else 0} flagged as outage)")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
