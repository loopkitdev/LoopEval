"""Reconstruct active-override correction RANGES from Nightscout devicestatus.

Loop's NAMED override presets ("Sick", "Grazing", ...) carry their correction
range in the app preset, NOT in the Nightscout `Temporary Override` treatment
(which has targetTop/targetBottom = null — only the multiplier/duration/reason).
The range Loop actually used each cycle appears ONLY in devicestatus
`override.currentCorrectionRange`. Treatment-based override replay therefore
applies the multiplier but MISSES the raised target → over-doses where Loop
withheld the correction (see runs/2026-06-19-divergence, case 06-12 15:07).

This module reads devicestatus, extracts the per-cycle active-override correction
range (+ multiplier), and emits an OVERLAY JSON of time intervals. The Swift CLI
(`--override-targets-json`) fills these ranges onto the gated override windows so
hands-on decision-time replay / sim uses the target Loop actually had.

CLI:
    python -m loopeval_analysis.override_targets from-nightscout \
        --host https://HOST --start 2026-06-01 --end 2026-06-15 \
        --tz America/Chicago --out override_targets.json
"""
from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from .reconstruct_carb_history import _fetch, _ISO_MS


def _override_stream(devicestatus: list[dict]) -> list[tuple[pd.Timestamp, dict | None]]:
    """Chronological (time, override-or-None) over ALL devicestatus (active AND inactive),
    so we can detect the active→inactive transition (the true override end)."""
    out = []
    for ds in devicestatus:
        t = ds.get("created_at")
        if t is None:
            continue
        ov = ds.get("override") or (ds.get("loop") or {}).get("override")
        out.append((pd.to_datetime(t).tz_convert("UTC"), ov))
    out.sort(key=lambda r: r[0])
    return out


def build_windows(devicestatus: list[dict], *, range_tol: float = 0.5) -> list[dict]:
    """Build override windows from the devicestatus stream — the decision-time-faithful source.

    An override is active over the CONTIGUOUS span of devicestatus records showing it
    active (same name+range), bridging active→active gaps. The window ENDS at the first
    record showing it INACTIVE (or a different override) — the realized cancel. The NS
    treatment's `duration` is unreliable (Loop back-fills it to the realized elapsed time
    at cancel, which leaks the future end into earlier forecasts), so we DON'T use it.

    `indefinite` = no record in the span carried a `duration` field (devicestatus omits
    duration iff the override's scheduledOverride.duration == .indefinite). For an
    indefinite override the forecast must NOT revert the target at `end` — at decision
    time the cancel was unknown, so it extends across the horizon (the sim handles that).
    """
    stream = _override_stream(devicestatus)
    windows: list[dict] = []
    cur = None

    def close(end_ts):
        nonlocal cur
        if cur is not None:
            cur["end"] = end_ts
            windows.append(cur)
            cur = None

    for ts, ov in stream:
        active = bool(ov and ov.get("active"))
        cr = (ov or {}).get("currentCorrectionRange") or {}
        lo, hi = cr.get("minValue"), cr.get("maxValue")
        if not active or lo is None or hi is None:
            close(ts)                     # inactive (or no range) → realized end here
            continue
        name = ov.get("name") or ""
        key = (name, round(float(lo), 1), round(float(hi), 1))
        if cur is not None and cur["_key"] == key:
            cur["_last"] = ts             # continue the span (bridges active→active gaps)
            cur["_dur"] = cur["_dur"] or ("duration" in ov)
        else:
            close(ts)                     # different override → close prev, open new
            cur = {"_key": key, "_start": ts, "_last": ts, "name": name,
                   "minValue": float(lo), "maxValue": float(hi),
                   "multiplier": ov.get("multiplier"), "_dur": ("duration" in ov)}
    if cur is not None:
        cur["end"] = cur["_last"] + pd.Timedelta(minutes=5)   # data ends while still active
        windows.append(cur)

    out = []
    for w in windows:
        out.append({
            "start": _ISO_MS(w["_start"]),
            "end": _ISO_MS(w["end"]),                  # realized cancel (decision-gate end)
            "indefinite": not w["_dur"],               # True ⇒ no horizon revert at `end`
            "minValue": round(w["minValue"], 1),
            "maxValue": round(w["maxValue"], 1),
            "multiplier": w["multiplier"],
            "name": w["name"],
        })
    return out


def _cmd_from_nightscout(args: argparse.Namespace) -> None:
    tz = args.tz
    start = pd.Timestamp(args.start, tz=tz)
    end = pd.Timestamp(args.end, tz=tz)
    print(f"[override-targets] {args.host}  {start} .. {end}", file=sys.stderr)
    devicestatus = _fetch(args.host, "devicestatus", start, end)
    print(f"[override-targets] fetched {len(devicestatus)} devicestatus", file=sys.stderr)
    windows = build_windows(devicestatus)
    with open(args.out, "w") as f:
        json.dump({"version": 1, "windows": windows}, f, indent=2, ensure_ascii=False)
    print(f"[override-targets] wrote {len(windows)} override-range windows -> {args.out}", file=sys.stderr)
    for w in windows:
        print(f"    {w['start'][:16]}..{w['end'][11:16]}  {w['name']}  "
              f"{w['minValue']:.0f}-{w['maxValue']:.0f}  x{w['multiplier']}  "
              f"{'INDEFINITE' if w['indefinite'] else 'definite'}", file=sys.stderr)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    fn = sub.add_parser("from-nightscout", help="fetch devicestatus + write override-range overlay")
    fn.add_argument("--host", required=True)
    fn.add_argument("--start", required=True)
    fn.add_argument("--end", required=True)
    fn.add_argument("--tz", default="UTC")
    fn.add_argument("--out", required=True)
    fn.set_defaults(func=_cmd_from_nightscout)
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
