"""Insulin-delivery outage representation.

An *outage* is a window in which the physical insulin pump could not deliver
insulin (pod failure, cannula occlusion, intentional disconnect, etc.). The
record of "what Loop told the pump to deliver" still exists during these
windows, but it does not reflect what entered the body. The simulator must
therefore not credit candidate-side deliveries inside an outage when projecting
counter_BG, otherwise the counterfactual diverges from physical reality.

Design goals
------------

1. **Source-agnostic.** ``Outage`` is just (start, end, reason, source, notes).
   Loaders for different upstream data sources (Nightscout, Tidepool, raw pod
   logs, manual specs) live in this module behind a uniform CSV format.

2. **Round-trippable CSV.** Every outage in production should be persistable
   so the same outage set can drive both the Python case-study tool and the
   Swift simulator.

3. **Conservative defaults.** Inference heuristics target high precision — we'd
   rather miss a marginal outage than mark a Loop-initiated long suspend as
   one. The :func:`infer_outage_start_from_doses` rule looks for a contiguous
   zero-delivery run preceding a Pod/Site Change event; if no such run is
   found we fall back to "5 min before the change" (best-effort, marked in
   ``notes``).

CSV schema
----------

UTF-8, RFC 4180. Columns:

    start         ISO 8601 timestamp, UTC, e.g. "2026-04-01T20:04:02Z"
    end           ISO 8601 timestamp, UTC
    reason        free-text enum (pod_change, site_change, manual_disconnect, …)
    source        "nightscout/Site Change", "manual", "tidepool/pump_status", …
    notes         optional free text
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable, Optional, Sequence

import pandas as pd
import pytz


# --------------------------------------------------------------------------- #
#  Data model                                                                 #
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Outage:
    """A single insulin-delivery outage window.

    ``start`` and ``end`` are tz-aware ``pd.Timestamp``. The simulator should
    treat any sample inside [start, end] as having zero physical delivery.
    """
    start: pd.Timestamp
    end: pd.Timestamp
    reason: str = "unknown"
    source: str = "unknown"
    notes: str = ""

    def __post_init__(self):
        if not (isinstance(self.start, pd.Timestamp) and self.start.tzinfo is not None):
            raise ValueError(f"Outage.start must be tz-aware; got {self.start!r}")
        if not (isinstance(self.end, pd.Timestamp) and self.end.tzinfo is not None):
            raise ValueError(f"Outage.end must be tz-aware; got {self.end!r}")
        if self.end <= self.start:
            raise ValueError(f"Outage.end must be > start; got {self.start} → {self.end}")

    @property
    def duration_min(self) -> float:
        return (self.end - self.start).total_seconds() / 60.0

    def contains(self, t: pd.Timestamp) -> bool:
        return self.start <= t <= self.end

    def overlaps(self, win_start: pd.Timestamp, win_end: pd.Timestamp) -> bool:
        return self.start <= win_end and self.end >= win_start


def merge_overlapping(outages: Sequence[Outage]) -> list[Outage]:
    """Merge outages whose intervals touch or overlap (preserving the
    earliest source/reason/notes for the merged window)."""
    if not outages:
        return []
    sorted_ = sorted(outages, key=lambda o: o.start)
    merged: list[Outage] = [sorted_[0]]
    for o in sorted_[1:]:
        last = merged[-1]
        if o.start <= last.end:
            merged[-1] = Outage(
                start=last.start,
                end=max(last.end, o.end),
                reason=last.reason,
                source=last.source,
                notes=(last.notes + " | " + o.notes).strip(" |") if last.notes or o.notes else "",
            )
        else:
            merged.append(o)
    return merged


# --------------------------------------------------------------------------- #
#  CSV I/O                                                                    #
# --------------------------------------------------------------------------- #

_CSV_HEADER = ["start", "end", "reason", "source", "notes"]


def write_outages_csv(outages: Iterable[Outage], path: str | Path) -> Path:
    """Write outages to a CSV (one row per outage, UTC ISO 8601 timestamps)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(_CSV_HEADER)
        for o in outages:
            w.writerow([
                o.start.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
                o.end.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
                o.reason,
                o.source,
                o.notes,
            ])
    return path


def read_outages_csv(path: str | Path) -> list[Outage]:
    """Read an outages CSV produced by :func:`write_outages_csv`."""
    path = Path(path)
    if not path.exists():
        return []
    out: list[Outage] = []
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.append(Outage(
                start=pd.to_datetime(row["start"]).tz_convert("UTC"),
                end=pd.to_datetime(row["end"]).tz_convert("UTC"),
                reason=row.get("reason", "unknown") or "unknown",
                source=row.get("source", "unknown") or "unknown",
                notes=row.get("notes", "") or "",
            ))
    return out


# --------------------------------------------------------------------------- #
#  Loaders                                                                    #
# --------------------------------------------------------------------------- #

def infer_outage_start_from_doses(
    doses: pd.DataFrame,
    end_time: pd.Timestamp,
    *,
    lookback_hours: float = 12.0,
    min_zero_run_min: float = 30.0,
) -> tuple[pd.Timestamp, str]:
    """Heuristic: walk backward from ``end_time`` looking for the start of a
    contiguous zero-delivery run.

    Returns (start, source_note). Falls back to `end_time - 5min` with a note
    if no zero-run pattern is found.
    """
    window_start = end_time - pd.Timedelta(hours=lookback_hours)
    w = doses[(doses.index >= window_start) & (doses.index <= end_time)].copy()
    if w.empty:
        return end_time - pd.Timedelta(minutes=5), "no preceding dose data; defaulted to end-5min"

    # Sort by start time and walk backward from end
    w = w.sort_index()
    nonzero = w[w["volume"].fillna(0) > 1e-9]
    if nonzero.empty:
        return w.index.min(), "no non-zero delivery in lookback window"

    # Outage start = end of the last non-zero delivery before the change.
    last_nonzero = nonzero.iloc[-1]
    last_end = pd.Timestamp(last_nonzero["endDate"])
    if last_end.tzinfo is None:
        last_end = last_end.tz_localize("UTC")
    else:
        last_end = last_end.tz_convert("UTC")

    zero_run_min = (end_time - last_end).total_seconds() / 60.0
    if zero_run_min < min_zero_run_min:
        return end_time - pd.Timedelta(minutes=5), (
            f"zero-run only {zero_run_min:.0f}min (<min_zero_run_min); defaulted to end-5min"
        )
    return last_end, f"start = end of last non-zero delivery ({zero_run_min:.0f}min zero-run)"


def load_outages_from_nightscout(
    host: str,
    win_start: pd.Timestamp,
    win_end: pd.Timestamp,
    *,
    event_types: Sequence[str] = ("Site Change", "Pump Change", "Insulin Change"),
    doses: Optional[pd.DataFrame] = None,
    lookback_hours: float = 12.0,
    min_zero_run_min: float = 30.0,
) -> list[Outage]:
    """Pull pump-change events from a Nightscout treatments collection.

    Each event becomes an outage whose *end* is the event time and whose
    *start* is inferred from doses (zero-run preceding the event). If
    ``doses`` is ``None`` the outage is recorded with end - 5min as start
    (placeholder; pass a dose frame to get accurate starts).
    """
    if not host.startswith("http"):
        host = "https://" + host
    win_start_utc = win_start.tz_convert("UTC").isoformat().replace("+00:00", ".000Z")
    win_end_utc = win_end.tz_convert("UTC").isoformat().replace("+00:00", ".000Z")

    treatments: list[dict] = []
    for et in event_types:
        url = host.rstrip("/") + "/api/v1/treatments.json?" + urllib.parse.urlencode({
            "find[eventType]": et,
            "find[created_at][$gte]": win_start_utc,
            "find[created_at][$lt]":  win_end_utc,
            "count": 500,
        })
        try:
            treatments += json.loads(urllib.request.urlopen(url, timeout=30).read())
        except Exception as exc:  # noqa: BLE001
            print(f"  [outage] Nightscout fetch for '{et}' failed: {exc}", file=sys.stderr)

    out: list[Outage] = []
    for tr in treatments:
        end_ts = pd.to_datetime(tr["created_at"]).tz_convert("UTC")
        et = tr.get("eventType", "unknown")
        notes = tr.get("notes", "") or ""
        if doses is not None:
            start_ts, src_note = infer_outage_start_from_doses(
                doses, end_ts,
                lookback_hours=lookback_hours,
                min_zero_run_min=min_zero_run_min,
            )
        else:
            start_ts = end_ts - pd.Timedelta(minutes=5)
            src_note = "no dose data; placeholder 5min start"
        out.append(Outage(
            start=start_ts,
            end=end_ts,
            reason="pod_change" if "pod" in (notes + et).lower() else "site_change",
            source=f"nightscout/{et}",
            notes=f"{notes} ({src_note})".strip(),
        ))
    return merge_overlapping(out)


def _decode_sync_identifier(sync: str) -> str:
    """Loop encodes the DoseType in the treatment ``syncIdentifier`` as hex.
    Returns the decoded string (e.g. 'suspend 0.0 2026-04-28T18:38:52Z'), or
    '' if the field is missing / not hex."""
    if not sync:
        return ""
    try:
        return bytes.fromhex(sync).decode("utf-8", "replace")
    except ValueError:
        return ""


def load_outages_from_suspend_doses(
    host: str,
    win_start: pd.Timestamp,
    win_end: pd.Timestamp,
    *,
    min_duration_min: float = 1.0,
) -> list[Outage]:
    """Pull *suspend* doses (DoseType.suspend) from a Nightscout treatments
    collection and turn each into an outage window.

    A suspend means the pump actually STOPPED delivering — pod fault /
    deactivation or a manual suspend — which is exogenous to the control loop,
    so the simulator must clamp delivery to 0 across it (same as a pod outage).
    This is distinct from a 0 U/hr temp basal (normal looping; the sim's own
    Loop reproduces that). Loop publishes a suspend as ``eventType:"Temp Basal"``
    with ``rate:0`` and a ``syncIdentifier`` whose hex decodes to
    ``"suspend <value> <ISO-ts>"`` — querying ``eventType:"Suspend Pump"`` finds
    NOTHING, you must decode the syncIdentifier. The window is
    ``[created_at, created_at + duration]``.
    """
    if not host.startswith("http"):
        host = "https://" + host
    win_start_utc = win_start.tz_convert("UTC").isoformat().replace("+00:00", ".000Z")
    win_end_utc = win_end.tz_convert("UTC").isoformat().replace("+00:00", ".000Z")
    url = host.rstrip("/") + "/api/v1/treatments.json?" + urllib.parse.urlencode({
        "find[eventType]": "Temp Basal",
        "find[created_at][$gte]": win_start_utc,
        "find[created_at][$lt]":  win_end_utc,
        "count": 100000,
    })
    try:
        treatments = json.loads(urllib.request.urlopen(url, timeout=120).read())
    except Exception as exc:  # noqa: BLE001
        print(f"  [outage] Nightscout suspend-dose fetch failed: {exc}", file=sys.stderr)
        return []

    out: list[Outage] = []
    for tr in treatments:
        decoded = _decode_sync_identifier(tr.get("syncIdentifier", ""))
        if not decoded.startswith("suspend"):
            continue
        dur = float(tr.get("duration", 0) or 0)
        if dur < min_duration_min:
            continue
        start_ts = pd.to_datetime(tr["created_at"]).tz_convert("UTC")
        end_ts = start_ts + pd.Timedelta(minutes=dur)
        out.append(Outage(
            start=start_ts,
            end=end_ts,
            reason="suspend",
            source="nightscout/suspend_dose",
            notes=f"suspend dose {dur:.0f}min (automatic={tr.get('automatic')})",
        ))
    return merge_overlapping(out)


def load_outages_from_zero_run_heuristic(
    doses: pd.DataFrame,
    *,
    min_zero_run_min: float = 60.0,
    require_manual_bolus_after: bool = True,
    manual_bolus_window_min: float = 15.0,
) -> list[Outage]:
    """Heuristic for data sources without explicit pump-change events.

    Looks for contiguous zero-delivery runs ≥``min_zero_run_min``. If
    ``require_manual_bolus_after`` is set, only runs ending within
    ``manual_bolus_window_min`` of a non-automatic bolus qualify (the
    pod-replacement-catch-up signature).
    """
    if doses.empty:
        return []
    df = doses.sort_index().copy()
    # Walk through, tracking the current zero-run
    runs: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    current_start = None
    last_end = None
    for ts, row in df.iterrows():
        vol = row.get("volume", 0) or 0
        end_ts = pd.Timestamp(row["endDate"])
        if end_ts.tzinfo is None:
            end_ts = end_ts.tz_localize("UTC")
        else:
            end_ts = end_ts.tz_convert("UTC")
        if vol < 1e-9:
            # Zero delivery — extend the run
            if current_start is None:
                current_start = ts
            last_end = end_ts
        else:
            # Non-zero delivery — close any current run
            if current_start is not None and last_end is not None:
                runs.append((current_start, last_end))
            current_start = None
            last_end = None
    if current_start is not None and last_end is not None:
        runs.append((current_start, last_end))

    qualifying: list[Outage] = []
    manual_b = df[(df["delivery_type"] != "basal") & (~df["automatic"].astype(bool))]
    for start, end in runs:
        dur = (end - start).total_seconds() / 60.0
        if dur < min_zero_run_min:
            continue
        if require_manual_bolus_after:
            # Find any manual bolus within the window after the zero-run ends
            mb = manual_b[(manual_b.index >= end) &
                          (manual_b.index <= end + pd.Timedelta(minutes=manual_bolus_window_min))]
            if mb.empty:
                continue
            note = (f"zero-run {dur:.0f}min; manual bolus "
                    f"{mb['volume'].iloc[0]:.2f}U at {mb.index[0].strftime('%H:%M:%S')}")
        else:
            note = f"zero-run {dur:.0f}min"
        qualifying.append(Outage(
            start=start.tz_convert("UTC") if start.tz else start.tz_localize("UTC"),
            end=end.tz_convert("UTC") if end.tz else end.tz_localize("UTC"),
            reason="inferred_pod_change",
            source="heuristic/zero_run",
            notes=note,
        ))
    return merge_overlapping(qualifying)


def load_outages_from_dose_record_gaps(
    doses: pd.DataFrame,
    *,
    min_gap_min: float = 60.0,
    catchup_window_min: float = 30.0,
    glucose: Optional[pd.Series] = None,
    bg_rise_threshold: float = 40.0,
) -> list[Outage]:
    """Infer pod-offs from GAPS in the delivery record itself.

    A pod that is off/occluded writes no dose records at all — distinct from a
    0 U/hr temp basal, which IS recorded (and is normal looping). Some pod-offs
    carry no Site Change event and no suspend dose (e.g. an occlusion that the
    user clears with a catch-up bolus), so the ONLY signal is a long absence of
    any delivery record.

    But a record gap is ambiguous: it can also be a comms/recording gap where
    the pod kept running SCHEDULED basal (the rate_uhr-NaN trap), which must NOT
    be clamped. So a gap only qualifies as a pod-off if it carries a no-insulin
    signature:
      - a USER manual (catch-up) bolus within ``catchup_window_min`` after the
        gap (the pod-replacement-catch-up signature), OR
      - BG rose by more than ``bg_rise_threshold`` mg/dL across the gap.
    Window = [last record before the gap, first record after it].
    """
    if doses.empty:
        return []
    df = doses.sort_index()
    idx = df.index
    is_manual = (df["delivery_type"] == "bolus") & (~df["automatic"].fillna(False).astype(bool))
    manual_times = df.index[is_manual]

    out: list[Outage] = []
    for i in range(len(idx) - 1):
        s, e = idx[i], idx[i + 1]
        gap_min = (e - s).total_seconds() / 60.0
        if gap_min < min_gap_min:
            continue
        has_catchup = bool(((manual_times >= e - pd.Timedelta(minutes=5)) &
                            (manual_times <= e + pd.Timedelta(minutes=catchup_window_min))).any())
        bg_rose = False
        bg_delta = float("nan")
        if glucose is not None and len(glucose):
            seg = glucose[(glucose.index >= s) & (glucose.index <= e)]
            if len(seg) >= 2:
                bg_delta = float(seg.iloc[-1] - seg.iloc[0])
                bg_rose = bg_delta > bg_rise_threshold
        if not (has_catchup or bg_rose):
            continue
        sig = []
        if has_catchup:
            sig.append("catch-up bolus")
        if bg_rose:
            sig.append(f"BG +{bg_delta:.0f}")
        out.append(Outage(
            start=s.tz_convert("UTC") if s.tz else s.tz_localize("UTC"),
            end=e.tz_convert("UTC") if e.tz else e.tz_localize("UTC"),
            reason="inferred_pod_off",
            source="heuristic/dose_record_gap",
            notes=f"dose-record gap {gap_min:.0f}min ({'; '.join(sig)})",
        ))
    return merge_overlapping(out)


# --------------------------------------------------------------------------- #
#  Query helpers                                                              #
# --------------------------------------------------------------------------- #

def event_in_outage(t: pd.Timestamp, outages: Sequence[Outage],
                    pad_min: float = 0.0) -> Optional[Outage]:
    """Return the outage containing ``t`` (with optional pad on both sides),
    or ``None``. Used for case-study filtering."""
    pad = pd.Timedelta(minutes=pad_min)
    for o in outages:
        if (o.start - pad) <= t <= (o.end + pad):
            return o
    return None


def event_window_overlaps_outage(win_start: pd.Timestamp,
                                 win_end: pd.Timestamp,
                                 outages: Sequence[Outage]) -> Optional[Outage]:
    """Return the first outage overlapping [win_start, win_end], or None."""
    for o in outages:
        if o.overlaps(win_start, win_end):
            return o
    return None


# --------------------------------------------------------------------------- #
#  CLI                                                                        #
# --------------------------------------------------------------------------- #

def _parse_ts(s: str, tz: pytz.BaseTzInfo) -> pd.Timestamp:
    ts = pd.to_datetime(s)
    if ts.tzinfo is None:
        ts = ts.tz_localize(tz)
    return ts.tz_convert("UTC")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="outage",
                                     description="Build / inspect insulin-delivery outage CSVs")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ns = sub.add_parser("from-nightscout",
                          help="generate an outage CSV from Nightscout Site Change events")
    p_ns.add_argument("--host", default="https://your-ns.example.com")
    p_ns.add_argument("--start", required=True, help="window start (e.g. 2026-03-01)")
    p_ns.add_argument("--end", required=True, help="window end")
    p_ns.add_argument("--tz", default="America/Chicago")
    p_ns.add_argument("--out", required=True, help="output CSV path")
    p_ns.add_argument("--event-types", nargs="*",
                      default=["Site Change", "Pump Change", "Insulin Change"])
    p_ns.add_argument("--no-suspend-doses", action="store_true",
                      help="do NOT merge in suspend-dose outage windows (default: include them)")
    p_ns.add_argument("--suspend-min-dur", type=float, default=1.0,
                      help="minimum suspend-dose duration (min) to count as an outage")
    p_ns.add_argument("--no-dose-gap-detection", action="store_true",
                      help="do NOT infer pod-offs from dose-record gaps (default: include them)")
    p_ns.add_argument("--dose-gap-min-min", type=float, default=60.0,
                      help="minimum dose-record gap (min) to consider a candidate pod-off")
    p_ns.add_argument("--dose-gap-bg-rise", type=float, default=40.0,
                      help="BG rise (mg/dL) across a dose-record gap that qualifies it as a pod-off")

    p_heur = sub.add_parser("from-heuristic",
                            help="infer outages from a doses cache via the zero-run heuristic")
    p_heur.add_argument("--host", default="your-ns.example.com")
    p_heur.add_argument("--start", required=True)
    p_heur.add_argument("--end", required=True)
    p_heur.add_argument("--tz", default="America/Chicago")
    p_heur.add_argument("--min-zero-run-min", type=float, default=60.0)
    p_heur.add_argument("--no-require-manual-bolus", action="store_true")
    p_heur.add_argument("--out", required=True)

    p_show = sub.add_parser("show", help="print an outages CSV in a human-readable format")
    p_show.add_argument("path")
    p_show.add_argument("--tz", default="America/Chicago")

    args = parser.parse_args(argv)
    tz = pytz.timezone(args.tz) if hasattr(args, "tz") else pytz.utc

    if args.cmd == "from-nightscout":
        from loopeval_analysis.glucose import find_doses_cache, load_doses_cache
        doses = None
        try:
            cache_host = args.host.replace("https://", "").replace("http://", "").rstrip("/")
            doses = load_doses_cache(find_doses_cache(cache_host))
        except Exception as exc:  # noqa: BLE001
            print(f"  [outage] doses cache load failed ({exc}); outages will use placeholder starts",
                  file=sys.stderr)
        ws = _parse_ts(args.start, tz)
        we = _parse_ts(args.end, tz)
        outs = load_outages_from_nightscout(args.host, ws, we,
                                            event_types=args.event_types, doses=doses)
        n_sitechange = len(outs)
        if not args.no_suspend_doses:
            sus = load_outages_from_suspend_doses(args.host, ws, we,
                                                  min_duration_min=args.suspend_min_dur)
            print(f"  [outage] {len(sus)} suspend-dose windows merged "
                  f"(with {n_sitechange} site/pod-change windows)", file=sys.stderr)
            outs = merge_overlapping(outs + sus)
        if not args.no_dose_gap_detection and doses is not None:
            glucose = None
            try:
                from loopeval_analysis.glucose import find_glucose_cache, load_glucose_cache
                gdf = load_glucose_cache(find_glucose_cache(cache_host))
                glucose = gdf["bg"] if "bg" in gdf else gdf.iloc[:, 0]
            except Exception as exc:  # noqa: BLE001
                print(f"  [outage] glucose cache load failed ({exc}); dose-gap detection uses catch-up only",
                      file=sys.stderr)
            dg = load_outages_from_dose_record_gaps(
                doses, min_gap_min=args.dose_gap_min_min,
                glucose=glucose, bg_rise_threshold=args.dose_gap_bg_rise)
            print(f"  [outage] {len(dg)} dose-record-gap pod-off windows merged", file=sys.stderr)
            outs = merge_overlapping(outs + dg)
        write_outages_csv(outs, args.out)
        print(f"Wrote {len(outs)} outages → {args.out}")
        for o in outs:
            print(f"  {o.start.tz_convert(tz).strftime('%Y-%m-%d %H:%M')} → "
                  f"{o.end.tz_convert(tz).strftime('%Y-%m-%d %H:%M')}  "
                  f"({o.duration_min:.0f}min)  {o.source}  {o.notes[:60]}")
        return 0

    if args.cmd == "from-heuristic":
        from loopeval_analysis.glucose import find_doses_cache, load_doses_cache
        doses = load_doses_cache(find_doses_cache(args.host))
        ws = _parse_ts(args.start, tz)
        we = _parse_ts(args.end, tz)
        doses_in_window = doses[(doses.index >= ws) & (doses.index <= we)]
        outs = load_outages_from_zero_run_heuristic(
            doses_in_window,
            min_zero_run_min=args.min_zero_run_min,
            require_manual_bolus_after=not args.no_require_manual_bolus,
        )
        write_outages_csv(outs, args.out)
        print(f"Wrote {len(outs)} outages → {args.out}")
        return 0

    if args.cmd == "show":
        outs = read_outages_csv(args.path)
        print(f"{len(outs)} outage(s) in {args.path}")
        for o in outs:
            print(f"  {o.start.tz_convert(tz).strftime('%Y-%m-%d %H:%M'):<20} → "
                  f"{o.end.tz_convert(tz).strftime('%Y-%m-%d %H:%M'):<20}  "
                  f"{o.duration_min:>6.0f}min  {o.reason:<18} {o.source:<28} {o.notes[:50]}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
