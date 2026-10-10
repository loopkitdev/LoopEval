#!/usr/bin/env python3
"""Pump alarms for the cohort, from source: time and alarm type only.

Tidepool stores pump alarms as type='deviceEvent', subType='alarm' with an
alarmType (occlusion, no_insulin, no_power, other). Only the timestamp and the
type are selected — no device ids, serials or payloads (lesson 41) — and donor
ids are mapped to aliases before anything is written or printed.

Window: the study's screening window (screen_cohort.START..END), widened by the
export window actually on disk so every ICE interval can be matched.

Output: ice/alarms.pkl  alias, t (UTC), alarmType
Run:    python3 pull_alarms.py      (needs Databricks credentials)
"""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import screen_cohort as SC  # noqa
import style as S  # noqa
from loopeval_analysis.tidepool.conn import query  # noqa

LO, HI = 1774137600000, 1785715200000        # 2026-03-22 .. 2026-08-03, covers every export window


def main():
    amap = SC._ids()
    co = S.cohort()
    ids = {a: amap[a] for a in co.alias if a in amap}
    lst = ",".join(f"'{u}'" for u in sorted(set(ids.values())))
    d = query(f"""SELECT _userId, {SC.T} AS t_ms, alarmType
                  FROM {SC.TBL}
                  WHERE type='deviceEvent' AND subType='alarm'
                    AND {SC.T} BETWEEN {LO} AND {HI} AND _userId IN ({lst})""")
    rev = {v: k for k, v in ids.items()}
    d["alias"] = d.pop("_userId").map(rev)
    d["t"] = pd.to_datetime(pd.to_numeric(d.pop("t_ms")), unit="ms", utc=True)
    d = d.drop_duplicates(["alias", "t", "alarmType"]).sort_values(["alias", "t"])
    d[["alias", "t", "alarmType"]].to_pickle(S.OUT / "ice" / "alarms.pkl")
    pump = co.set_index("alias").pump
    d["pump"] = d.alias.map(pump)
    print(d.groupby(["alarmType", "pump"]).agg(n=("t", "size"), people=("alias", "nunique")).to_string())


if __name__ == "__main__":
    main()
