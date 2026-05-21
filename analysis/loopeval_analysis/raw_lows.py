"""Raw-CGM severe-low audit.

The counterfactual `counter` trace cannot represent some real severe lows:
floor-clamped readings (Dexcom pins at 40 = "≤40"), and real-pump-caused lows
that the sim Loop would not reproduce (counter runs high there). The mandatory
disruption-exclusion also drops post-outage/post-gap windows. So real severe
lows can be invisible to the counter-based outcome stats.

This audit reads the RAW CGM (`actual` array of a sim trace) and enumerates
severe-low events independently of the counter, tagging:
  - floor : the event hit the 40 mg/dL sensor floor (true BG is ≤40, censored)
  - artifact : entry/exit single-step |ΔBG| is physiologically implausible
               (sensor spike, e.g. 305→40→49), so the "low" is likely not real
  - excluded : the event falls in a disruption-exclusion window (so it is NOT
               in the counter-based stats)

Use it alongside `scoring.score_counterfactual` so a real floor event is never
silently dropped.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

from .scoring import exclusion_mask

# physiologically, BG rarely moves >~4 mg/dL/min; a single 5-min step jump
# larger than this into/out of a "low" indicates a sensor artifact, not a real
# excursion.
ARTIFACT_STEP_MGDL = 35.0
SENSOR_FLOOR = 40.0


def _load_raw(trace_path: str, tz) -> pd.Series:
    t = json.loads(Path(trace_path).read_text())
    a = pd.DataFrame(t["actual"])
    a["t"] = pd.to_datetime(a["t"]).dt.tz_convert(tz)
    return a.sort_values("t").set_index("t")["bg"].astype(float)


def audit_raw_lows(trace_path: str,
                   outages_csv: Optional[str] = None,
                   cgm_gaps_csv: Optional[str] = None,
                   threshold: float = 54.0,
                   floor: float = SENSOR_FLOOR,
                   artifact_step: float = ARTIFACT_STEP_MGDL,
                   post_hours: float = 3.0,
                   tz_name: str = "America/Chicago") -> pd.DataFrame:
    """Enumerate raw-CGM severe-low events (contiguous runs below `threshold`).

    Returns a DataFrame, one row per event, with columns:
      start, end, dur_min, nadir, floor, artifact, excluded, entry_step, exit_step
    `entry_step`/`exit_step` are the largest single-5-min |ΔBG| just before / after
    the event (large ⇒ sensor jump). `floor` ⇒ event touched the 40 sensor floor.
    """
    import pytz
    tz = pytz.timezone(tz_name)
    bg = _load_raw(trace_path, tz)

    outs, gaps = [], []
    if outages_csv:
        from .outage import read_outages_csv
        outs = read_outages_csv(outages_csv)
    if cgm_gaps_csv:
        from .cgm_gaps import read_cgm_gaps_csv
        gaps = read_cgm_gaps_csv(cgm_gaps_csv)
    excl = exclusion_mask(bg.index, outs, gaps, post_hours=post_hours)

    below = (bg < threshold).values
    vals = bg.values
    idx = bg.index
    n = len(bg)
    events = []
    i = 0
    while i < n:
        if not below[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and below[j + 1]:
            j += 1
        seg = vals[i:j + 1]
        nadir = float(seg.min())
        dur_min = (idx[j] - idx[i]).total_seconds() / 60.0 + 5.0  # inclusive of the bin
        # entry/exit single-step deltas (sample just before i, just after j)
        entry_step = abs(vals[i] - vals[i - 1]) if i > 0 else float("nan")
        exit_step = abs(vals[j + 1] - vals[j]) if j + 1 < n else float("nan")
        big = max([d for d in (entry_step, exit_step) if d == d] or [0.0])
        # an artifact: a short event reached only via an implausible single jump,
        # OR any event entered/left via a physically-impossible step (>~12 mg/dL/min
        # = >60/5min) regardless of duration (sensor dropout/recovery glitch).
        artifact = (big > 2.0 * artifact_step) or ((big > artifact_step) and (dur_min <= 15.0))
        floored = bool((seg <= floor + 1e-9).any())
        excluded = bool(excl.loc[idx[i]:idx[j]].any())
        events.append(dict(
            start=idx[i], end=idx[j], dur_min=dur_min, nadir=nadir,
            floor=floored, artifact=artifact, excluded=excluded,
            entry_step=entry_step, exit_step=exit_step,
        ))
        i = j + 1
    return pd.DataFrame(events)


def summarize(df: pd.DataFrame) -> str:
    if df.empty:
        return "no raw severe-low events"
    real = df[~df.artifact]
    lines = [
        f"raw severe-low events: {len(df)} total "
        f"({int(df.artifact.sum())} artifact-suspect, {len(real)} likely-real)",
        f"  likely-real: {int(real.floor.sum())} hit the 40 floor; "
        f"{int(real.excluded.sum())} fall in disruption-excluded windows "
        f"(invisible to counter stats)",
    ]
    return "\n".join(lines)


def _main():
    import argparse, pytz
    ap = argparse.ArgumentParser(description="Raw-CGM severe-low audit")
    ap.add_argument("trace")
    ap.add_argument("--outages-csv")
    ap.add_argument("--cgm-gaps-csv")
    ap.add_argument("--threshold", type=float, default=54.0)
    ap.add_argument("--tz", default="America/Chicago")
    args = ap.parse_args()
    df = audit_raw_lows(args.trace, args.outages_csv, args.cgm_gaps_csv,
                        threshold=args.threshold, tz_name=args.tz)
    pd.set_option("display.width", 160)
    if not df.empty:
        show = df.copy()
        show["start"] = show["start"].dt.strftime("%m-%d %H:%M")
        show["end"] = show["end"].dt.strftime("%H:%M")
        print(show.to_string(index=False))
    print()
    print(summarize(df))


if __name__ == "__main__":
    _main()
