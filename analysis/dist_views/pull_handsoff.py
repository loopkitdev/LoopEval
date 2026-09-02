#!/usr/bin/env python3
"""Over-sample the cell the wide cohort barely reached: hands-off, lower TIR.

The wide cohort is hash-ordered and therefore matches the donor pool — which is
the point of it, and also why it contains almost nobody who announces few carbs,
lets automation do the bolusing AND runs a time in range under 65%. That group
is what the unannounced-meal work is about, so it is sampled DELIBERATELY and
kept as a separate stratum; the pool-matched core is never diluted with it.

Selection (screened over one common 30-day window, automated-system donors only):
    fewer than 1.5 carb entries per day
    manual boluses under 35% of all boluses
    time in range under 65%

Writes handsoff_alias_map.json (git-ignored, aliases h01…), then export with:
    EXPORT_ROOT=handsoff EXPORT_MAP=handsoff_alias_map.json python3 export_full.py 6
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pandas as pd

CACHE = Path(os.path.expanduser("~/.loop-eval/trait-cohort"))
CANDIDATES = CACHE / "handsoff_candidates.csv"
OUT_MAP = CACHE / "handsoff_alias_map.json"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 24


def main() -> int:
    if not CANDIDATES.exists():
        raise SystemExit(f"{CANDIDATES} missing — run the pool screen first")
    ids = pd.read_csv(CANDIDATES)["_userId"].dropna().astype(str).tolist()
    already = set(json.loads((CACHE / "alias_map.json").read_text()).values())
    ids = [u for u in ids if u not in already]
    # Hash order, never volume: ordering by record count selects multi-device
    # duplicate uploaders (lesson 15).
    ids.sort(key=lambda u: hashlib.md5(u.encode()).hexdigest())
    amap = {f"h{i + 1:02d}": u for i, u in enumerate(ids[:N])}
    OUT_MAP.write_text(json.dumps(amap, indent=2))
    print(f"{len(ids)} candidates not already in the cohort; {len(amap)} selected")
    print(f"alias map -> {OUT_MAP}  (git-ignored)")
    print("export with:  EXPORT_ROOT=handsoff EXPORT_MAP=handsoff_alias_map.json "
          "python3 export_full.py 6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
