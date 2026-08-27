#!/usr/bin/env python3
"""Pull raw CGM for a donor cohort and cache it locally, aliases only.

Glucose-only by design. Every trait in `loopeval_analysis.traits` is computable
from the CGM series alone, so this scales to far more people than a full
four-stream ETL export would — and the question here is about the population,
so breadth beats depth.

PRIVACY: `_userId` is a pseudonymous access key. It is used to query and to name
nothing. Cached files are named by alias; the alias↔id map is written to a
git-ignored sidecar under the cache dir and must be copied into PRIVATE.md by
hand, never into the repo.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path(os.path.expanduser("~/.loop-eval/trait-cohort"))
TBL = "prod.default.device_data"
TMS = "CAST(get_json_object(time,'$.$date.$numberLong') AS BIGINT)"
WINDOW = ("2026-04-01", "2026-07-24")
ALIAS_PREFIX = "p"


def _ms(s: str) -> int:
    return int(dt.datetime.strptime(s, "%Y-%m-%d")
               .replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


def _conn():
    sys.path.insert(0, os.path.expanduser("~/dev/LoopEval/analysis"))
    for line in open(os.path.expanduser("~/.loop-eval/databricks.env")):
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.strip().split("=", 1)
            os.environ.setdefault(k, v.strip())
    from loopeval_analysis.tidepool import conn
    return conn


def pull_glucose(conn, uid: str, s_ms: int, e_ms: int) -> pd.Series:
    """Deduplicated CGM series in mg/dL.

    Tidepool stores mmol/L and the same reading can appear from several uploads,
    so both the unit conversion and the dedup-by-timestamp matter — duplicates
    would otherwise show up as zero-increments and corrupt every process
    statistic downstream.
    """
    q = (f"SELECT {TMS} AS t_ms, "
         f"COALESCE(CAST(get_json_object(value,'$.$numberDouble') AS DOUBLE), "
         f"CAST(get_json_object(value,'$.$numberInt') AS DOUBLE), "
         f"CAST(value AS DOUBLE)) AS mmol "
         f"FROM {TBL} WHERE _userId='{uid}' AND type='cbg' "
         f"AND {TMS} BETWEEN {s_ms} AND {e_ms}")
    df = conn.query(q)
    if df.empty:
        return pd.Series(dtype=float)
    df = df.dropna()
    df["t"] = pd.to_datetime(df["t_ms"], unit="ms", utc=True)
    mg = df["mmol"] * 18.0182
    # A few uploads already store mg/dL; detect by magnitude rather than trusting
    # the unit field, which is not always present on the raw row.
    if mg.median() > 600:
        mg = df["mmol"]
    s = pd.Series(mg.to_numpy(), index=df["t"]).sort_index()
    s = s[(s > 10) & (s < 600)]
    return s[~s.index.duplicated(keep="first")]


def main(n_donors: int = 60) -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    pool = pd.read_csv("/tmp/donor_pool2.csv")
    conn = _conn()
    s_ms, e_ms = _ms(WINDOW[0]), _ms(WINDOW[1])

    mapfile = CACHE / "alias_map.json"
    amap = json.loads(mapfile.read_text()) if mapfile.exists() else {}
    rev = {v: k for k, v in amap.items()}

    took = 0
    for i, r in pool.iterrows():
        if took >= n_donors:
            break
        uid = r["uid"]
        alias = rev.get(uid) or f"{ALIAS_PREFIX}{len(amap) + 1:02d}"
        out = CACHE / f"{alias}.pkl"
        if out.exists():
            amap[alias] = uid
            took += 1
            continue
        t0 = time.time()
        try:
            s = pull_glucose(conn, uid, s_ms, e_ms)
        except Exception as e:                                    # noqa: BLE001
            print(f"  {alias}: FAILED {type(e).__name__}: {str(e)[:80]}")
            continue
        if len(s) < 20000:
            print(f"  {alias}: only {len(s)} usable samples — skipped")
            continue
        s.to_frame("bg").to_pickle(out)
        amap[alias] = uid
        rev[uid] = alias
        took += 1
        span = (s.index.max() - s.index.min()).days
        cad = float(np.median(np.diff(s.index.view("int64")) / 6e10))
        print(f"  {alias}: {len(s):>7} samples  {span:>3}d  ~{cad:.1f}min  "
              f"({time.time() - t0:.0f}s)")
        mapfile.write_text(json.dumps(amap, indent=1))

    mapfile.write_text(json.dumps(amap, indent=1))
    print(f"\ncached {took} donors -> {CACHE}")
    print(f"alias map -> {mapfile}  (git-ignored; copy into PRIVATE.md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 60))
