#!/usr/bin/env python3
"""Give every part of the outcome range enough people to report on.

Matching the reference population's time in range cannot be done by matching
behaviour: at the same bolus frequency, Loop donors sit above the published
Omnipod 5 figures (63.7% against 59.9% for under four boluses a day). The
conditional distribution differs, not the mix, so the only variable that moves
time in range is time in range.

This therefore samples on the OUTCOME, deliberately and for coverage: it fills
the thin bands so that conclusions about less well-controlled users rest on
people who are less well-controlled, and so that analysis-time weights to any
target distribution have support everywhere. It does NOT tune the cohort's
median to a target — that would make a summary statistic a design parameter.
Read §7 of the justification before using this cohort to estimate anything
about time in range: it cannot.

Selection is hash-ordered within each band, from donors passing the same gates,
and skips records whose low reading is an artefact rather than a person (a
window with few covered days, values piled at the sensor floor or ceiling, or
an implausibly flat trace).

Writes tir_alias_map.json (aliases t01…); export with:
    EXPORT_ROOT=tir EXPORT_MAP=tir_alias_map.json python3 export_full.py 6
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S                                            # noqa: E402
from loopeval_analysis.tidepool.conn import query            # noqa: E402

CACHE = Path(os.path.expanduser("~/.loop-eval/trait-cohort"))
OUT_MAP = CACHE / "tir_alias_map.json"
TBL = os.environ.get("TIDEPOOL_TABLE") or "prod.default.device_data"
T = "CAST(get_json_object(time,'$.$date.$numberLong') AS BIGINT)"
V = ("COALESCE(CAST(get_json_object(value,'$.$numberDouble') AS DOUBLE),"
     "CAST(get_json_object(value,'$.$numberInt') AS DOUBLE)) * 18.0182")
START, END = 1775088000000, 1782864000000
SLOTS = (END - START) / 300000.0
BANDS = [(0, 40), (40, 50), (50, 60), (60, 70), (70, 80)]
TARGET_N = 150                     # cohort size the band shares are computed for
REFERENCE_MEDIAN = 64.2            # Omnipod 5, Forlenza 2024


def main() -> int:
    held = set()
    for f in CACHE.glob("*alias_map.json"):
        held |= set(json.loads(f.read_text()).values())

    print("screening the AID pool…", flush=True)
    pool = query(f"""
    SELECT c._userId AS uid,
           100*avg(CASE WHEN {V} BETWEEN 70 AND 180 THEN 1.0 ELSE 0.0 END) AS tir,
           count(DISTINCT floor({T.replace('time','c.time')}/300000)) AS slots,
           count(DISTINCT date_trunc('DAY',
                 from_unixtime({T.replace('time','c.time')}/1000))) AS days_seen,
           100*avg(CASE WHEN {V} <= 40.1 THEN 1.0 ELSE 0.0 END) AS at_floor,
           100*avg(CASE WHEN {V} >= 399 THEN 1.0 ELSE 0.0 END) AS at_ceiling,
           stddev({V}) AS sd
    FROM {TBL} c
    JOIN (SELECT DISTINCT _userId FROM {TBL} WHERE type='dosingDecision'
          AND {T} BETWEEN {START} AND {END}) a ON c._userId = a._userId
    WHERE c.type='cbg' AND {T.replace('time','c.time')} BETWEEN {START} AND {END}
    GROUP BY 1""")
    for c in pool.columns:
        if c != "uid":
            pool[c] = pd.to_numeric(pool[c], errors="coerce")
    pool["wear"] = pool["slots"] / SLOTS
    clean = pool[(pool.wear >= 0.7) & (pool.days_seen >= 60) & (pool.at_floor <= 5)
                 & (pool.at_ceiling <= 20) & (pool.sd >= 15)]
    print(f"  {len(pool):,} AID donors, {len(clean):,} with a usable record")

    co = S.cohort()
    shifted = clean["tir"] - (clean["tir"].median() - REFERENCE_MEDIAN)
    clean = clean.assign(hash=[hashlib.md5(str(u).encode()).hexdigest() for u in clean["uid"]])
    picked: list[str] = []
    for lo, hi in BANDS:
        have = int(((co.tir >= lo) & (co.tir < hi)).sum())
        want = int(round(float(((shifted >= lo) & (shifted < hi)).mean()) * TARGET_N))
        need = max(want - have, 0)
        if not need:
            continue
        avail = clean[(clean.tir >= lo) & (clean.tir < hi)
                      & ~clean["uid"].isin(held | set(picked))].sort_values("hash")
        take = avail["uid"].head(need).tolist()
        picked += take
        print(f"  TIR {lo:>2}–{hi:<3} have {have:3d}, target {want:3d}, taking {len(take):3d}"
              f" of {len(avail):5d} available")

    used = set()
    for f in CACHE.glob("*alias_map.json"):
        used |= {a for a in json.loads(f.read_text()) if a.startswith("t")}
    start = max((int(a[1:]) for a in used if a[1:].isdigit()), default=0)
    amap = {f"t{start + i + 1:02d}": u for i, u in enumerate(picked)}
    OUT_MAP.write_text(json.dumps(amap, indent=2))
    print(f"\n{len(amap)} donors -> {OUT_MAP} (git-ignored)")
    print("export with:  EXPORT_ROOT=tir EXPORT_MAP=tir_alias_map.json "
          "python3 export_full.py 6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
