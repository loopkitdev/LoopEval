#!/usr/bin/env python3
"""Fill the dosing × settings-maintenance grid from the cohort justification.

The justification asks for a modelling cohort where every engagement cell holds
enough people to report on, rather than one that mirrors the donor pool — the
pool is dominated by engaged Loop users, and conclusions about less-engaged
users have to rest on less-engaged users' data.

Cells are user-initiated boluses/day (<3, 3–4, 4–6, >6) crossed with therapy
configuration changes per 30 days (none, 1–3, >3).

Both axes needed a measurement decision that changes who lands where:

  * A HealthKit-mirrored bolus loses its `automated` subType, so mirrored rows
    are excluded — otherwise heavily automated users read as heavy manual
    bolusers and land in the wrong dosing cell.
  * A pumpSettings row is an UPLOAD, not an edit: the busiest donor uploaded
    27,899 of them in 90 days holding six distinct payloads. Counting rows gives
    ~37 "changes" per 30 days, and counting transitions counts oscillation. The
    metric is therefore DISTINCT therapy configurations, with rows falling
    inside an override window dropped first — a preset that scales ISF, basal
    and carb ratio is uploaded as a settings row, and toggling a preset is not
    editing therapy. (Overrides are 7% of settings rows; excluding them moves
    the median not at all and p90 from 8.0 to 7.7. Override use is worth
    reporting on its own, but it is not a settings change.) Donors already held are
counted first; the deficit is drawn hash-ordered (never by data volume) from the
eligible pool, which passes the data-quality gates: closed loop on >=50% of days,
CGM wear >=70%, total daily insulin >=5 U.

Writes grid_alias_map.json (git-ignored, aliases g01…), then export with:
    EXPORT_ROOT=grid EXPORT_MAP=grid_alias_map.json python3 export_full.py 6
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pandas as pd

CACHE = Path(os.path.expanduser("~/.loop-eval/trait-cohort"))
GRID = Path("/private/tmp/claude-501/-Users-pete-dev-loopeval-eda/"
            "bfa63131-1394-4401-ba0d-468c73f27a9b/scratchpad/eligible_grid.csv")
OUT_MAP = CACHE / os.environ.get("GRID_MAP", "grid_alias_map.json")
MIN_PER_CELL = int(sys.argv[1]) if len(sys.argv) > 1 else 5


def main() -> int:
    g = pd.read_csv(GRID)
    held = set()
    for f in ("alias_map.json", "handsoff_alias_map.json", "grid_alias_map.json",
              "device_alias_map.json"):
        p = CACHE / f
        if p.exists():
            held |= set(json.loads(p.read_text()).values())
    g["hash"] = [hashlib.md5(str(u).encode()).hexdigest() for u in g["_userId"]]
    picked: list[str] = []
    for (dose, sett), cell in g.groupby(["dosing", "settings"], observed=True):
        have = int(cell["_userId"].isin(held).sum())
        need = max(MIN_PER_CELL - have, 0)
        if not need:
            continue
        avail = cell[~cell["_userId"].isin(held)].sort_values("hash")
        take = avail["_userId"].head(need).tolist()
        picked += take
        print(f"  {str(dose):>4} boluses/day × {str(sett):>4} settings: "
              f"have {have}, taking {len(take)}")
    # Continue the alias numbering past anything already exported to this root:
    # reusing g01 would land on an existing directory, which export_full treats as
    # already complete and skips — the new donor would never be fetched.
    used = set()
    for f in CACHE.glob("*alias_map.json"):
        used |= {a for a in json.loads(f.read_text()) if a.startswith("g")}
    start = max((int(a[1:]) for a in used if a[1:].isdigit()), default=0)
    amap = {f"g{start + i + 1:02d}": u for i, u in enumerate(picked)}
    OUT_MAP.write_text(json.dumps(amap, indent=2))
    print(f"\n{len(amap)} donors selected -> {OUT_MAP} (git-ignored)")
    print("export with:  EXPORT_ROOT=grid EXPORT_MAP=grid_alias_map.json "
          "python3 export_full.py 6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
