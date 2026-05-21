"""CGM-gap representation: windows where no CGM value was received.

A *CGM gap* is distinct from a pump outage ([[outage.py]]): during a CGM gap
the pump keeps delivering scheduled basal, but Loop does not issue NEW dose
commands because it has no fresh glucose (its `inputDataRecencyInterval` is
15 min — once the latest reading is older than that, it refuses with
`glucoseTooOld`).

For the simulator, the faithful behavior is the per-step recency guard
(`loop-eval simulate --cgm-stale-guard-min 15`), which needs no CSV: at each
step it checks the age of the latest CGM sample and makes no dose adjustment
when stale. This module exists for **visualization and outcome-stat
filtering** — to mark gap windows in case-study plots and to flag/exclude
events that fall inside them.

A single missed sample (~10 min spacing) is "paved over" — it never crosses
the 15-min recency threshold, so it's not a gap. Only spacings beyond the
threshold (2+ missed samples) qualify.

CSV schema (parallels outage.py):

    start,end,gap_min,n_missed,source,notes
    2026-03-02T18:22:00Z,2026-03-02T18:52:00Z,30.0,5,cgm/spacing,...
"""
from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

import pandas as pd
import pytz

DEFAULT_GAP_MIN = 15.0       # matches LoopAlgorithm.inputDataRecencyInterval
TYPICAL_SAMPLE_MIN = 5.0


@dataclass(frozen=True)
class CgmGap:
    """A window [start, end] with no CGM samples (start = last sample before
    the gap, end = first sample after). tz-aware timestamps."""
    start: pd.Timestamp
    end: pd.Timestamp
    source: str = "cgm/spacing"
    notes: str = ""

    def __post_init__(self):
        if self.end <= self.start:
            raise ValueError(f"CgmGap.end must be > start; got {self.start} → {self.end}")

    @property
    def gap_min(self) -> float:
        return (self.end - self.start).total_seconds() / 60.0

    @property
    def n_missed(self) -> int:
        return max(0, int(round(self.gap_min / TYPICAL_SAMPLE_MIN)) - 1)

    def contains(self, t: pd.Timestamp) -> bool:
        return self.start <= t <= self.end

    def overlaps(self, win_start: pd.Timestamp, win_end: pd.Timestamp) -> bool:
        return self.start <= win_end and self.end >= win_start


def find_cgm_gaps(glucose: pd.Series,
                  min_gap_min: float = DEFAULT_GAP_MIN,
                  source: str = "cgm/spacing") -> list[CgmGap]:
    """Return gaps where consecutive CGM samples are more than `min_gap_min`
    apart. `glucose` is a tz-aware Series indexed by sample time."""
    if glucose.empty:
        return []
    idx = glucose.sort_index().index
    deltas = idx.to_series().diff().dt.total_seconds() / 60.0
    gaps: list[CgmGap] = []
    for i in range(1, len(idx)):
        spacing = deltas.iloc[i]
        if spacing > min_gap_min:
            gaps.append(CgmGap(
                start=idx[i - 1],
                end=idx[i],
                source=source,
                notes=f"{spacing:.0f}min spacing",
            ))
    return gaps


# --------------------------------------------------------------------------- #
#  CSV I/O                                                                    #
# --------------------------------------------------------------------------- #

_CSV_HEADER = ["start", "end", "gap_min", "n_missed", "source", "notes"]


def write_cgm_gaps_csv(gaps: Iterable[CgmGap], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(_CSV_HEADER)
        for g in gaps:
            w.writerow([
                g.start.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
                g.end.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
                f"{g.gap_min:.1f}",
                g.n_missed,
                g.source,
                g.notes,
            ])
    return path


def read_cgm_gaps_csv(path: str | Path) -> list[CgmGap]:
    path = Path(path)
    if not path.exists():
        return []
    out: list[CgmGap] = []
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.append(CgmGap(
                start=pd.to_datetime(row["start"]).tz_convert("UTC"),
                end=pd.to_datetime(row["end"]).tz_convert("UTC"),
                source=row.get("source", "cgm/spacing") or "cgm/spacing",
                notes=row.get("notes", "") or "",
            ))
    return out


def gap_containing(t: pd.Timestamp, gaps: Sequence[CgmGap],
                   pad_min: float = 0.0) -> Optional[CgmGap]:
    pad = pd.Timedelta(minutes=pad_min)
    for g in gaps:
        if (g.start - pad) <= t <= (g.end + pad):
            return g
    return None


# --------------------------------------------------------------------------- #
#  CLI                                                                        #
# --------------------------------------------------------------------------- #

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="cgm_gaps",
                                     description="Detect / inspect CGM gaps")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("from-cache", help="detect CGM gaps from the glucose cache")
    p.add_argument("--host", default="your-ns.example.com")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--tz", default="America/Chicago")
    p.add_argument("--min-gap-min", type=float, default=DEFAULT_GAP_MIN)
    p.add_argument("--out", required=True)

    p_show = sub.add_parser("show", help="print a CGM-gap CSV")
    p_show.add_argument("path")
    p_show.add_argument("--tz", default="America/Chicago")

    args = parser.parse_args(argv)
    tz = pytz.timezone(args.tz)

    if args.cmd == "from-cache":
        from loopeval_analysis.glucose import load_glucose_cache, find_glucose_cache
        raw = load_glucose_cache(find_glucose_cache(args.host))
        bg = raw["bg"] if isinstance(raw, pd.DataFrame) else raw
        if bg.index.tz is None:
            bg.index = bg.index.tz_localize("UTC")
        bg = bg.tz_convert(tz).sort_index()
        ws = pd.to_datetime(args.start).tz_localize(tz) if pd.to_datetime(args.start).tzinfo is None else pd.to_datetime(args.start).tz_convert(tz)
        we = pd.to_datetime(args.end).tz_localize(tz) if pd.to_datetime(args.end).tzinfo is None else pd.to_datetime(args.end).tz_convert(tz)
        bg = bg.loc[(bg.index >= ws) & (bg.index <= we)]
        gaps = find_cgm_gaps(bg, min_gap_min=args.min_gap_min)
        write_cgm_gaps_csv(gaps, args.out)
        total_h = sum(g.gap_min for g in gaps) / 60.0
        print(f"Wrote {len(gaps)} CGM gaps (>{args.min_gap_min:.0f}min) → {args.out}")
        print(f"  total missing time: {total_h:.1f}h over the window")
        # Histogram of gap sizes
        buckets = {"15-30m": 0, "30-60m": 0, "1-3h": 0, ">3h": 0}
        for g in gaps:
            m = g.gap_min
            if m <= 30: buckets["15-30m"] += 1
            elif m <= 60: buckets["30-60m"] += 1
            elif m <= 180: buckets["1-3h"] += 1
            else: buckets[">3h"] += 1
        for k, v in buckets.items():
            print(f"    {k:>8}: {v}")
        return 0

    if args.cmd == "show":
        gaps = read_cgm_gaps_csv(args.path)
        print(f"{len(gaps)} CGM gap(s) in {args.path}")
        for g in gaps:
            print(f"  {g.start.tz_convert(tz).strftime('%Y-%m-%d %H:%M'):<20} → "
                  f"{g.end.tz_convert(tz).strftime('%H:%M'):<8}  {g.gap_min:>6.0f}min  "
                  f"({g.n_missed} missed)  {g.notes}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
