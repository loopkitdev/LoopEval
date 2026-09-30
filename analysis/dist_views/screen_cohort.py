#!/usr/bin/env python3
"""Per-donor engagement, wear and settings measures for the cohort, from source.

Everything the cohort justification reports is measured HERE, over one common
90-day window, and written to screen.csv so the rest of the pipeline joins to a
file rather than to whatever was last computed in a notebook. Three measurement
rules the source data forces (each changes who lands where):

  * A HealthKit-mirrored bolus loses its `automated` subtype, so mirrored rows
    are excluded — otherwise automation reads as user-initiated dosing.
  * CGM wear counts distinct five-minute SLOTS, not rows: duplicate uploads
    otherwise push coverage above 100%.
  * A settings change is an HOUR containing a content change, not a row —
    one editing session writes a row per schedule segment touched.

Run:  python3 screen_cohort.py            (needs Databricks credentials)
"""
from __future__ import annotations

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
MAPS = ("alias_map.json", "handsoff_alias_map.json", "grid_alias_map.json",
        "grid2_alias_map.json", "device_alias_map.json", "bddp_alias_map.json",
        "tir_alias_map.json")
TBL = os.environ.get("TIDEPOOL_TABLE") or "prod.default.device_data"
T = "CAST(get_json_object(time,'$.$date.$numberLong') AS BIGINT)"
V = ("COALESCE(CAST(get_json_object(value,'$.$numberDouble') AS DOUBLE),"
     "CAST(get_json_object(value,'$.$numberInt') AS DOUBLE)) * 18.0182")
NORM = ("COALESCE(CAST(get_json_object(normal,'$.$numberDouble') AS DOUBLE),"
        "CAST(get_json_object(normal,'$.$numberInt') AS DOUBLE))")
RATE = ("COALESCE(CAST(get_json_object(rate,'$.$numberDouble') AS DOUBLE),"
        "CAST(get_json_object(rate,'$.$numberInt') AS DOUBLE))")
DUR = ("COALESCE(CAST(get_json_object(duration,'$.$numberLong') AS DOUBLE),"
       "CAST(get_json_object(duration,'$.$numberInt') AS DOUBLE))")
START, END = 1775088000000, 1782864000000          # 2026-04-02 .. 2026-07-01
DAYS = (END - START) / 86400000
SLOTS = (END - START) / 300000.0
SET_FIELDS = ["basalSchedules", "carbRatios", "insulinSensitivities", "bgTargets",
              "bgSafetyLimit"]
H = "md5(concat_ws('|', " + ", ".join(
    f"COALESCE(CAST({f} AS STRING),'')" for f in SET_FIELDS) + "))"


def _ids() -> dict[str, str]:
    out: dict[str, str] = {}
    for f in MAPS:
        p = CACHE / f
        if p.exists():
            out.update(json.loads(p.read_text()))
    return out


def main() -> int:
    amap = _ids()
    ids = ",".join(f"'{u}'" for u in sorted(set(amap.values())))
    W = f"{T} BETWEEN {START} AND {END} AND _userId IN ({ids})"
    print(f"{len(set(amap.values()))} donor ids, window 90 days")

    def go(label, q):
        print(f"  {label}…", flush=True)
        d = query(q)
        for c in d.columns:
            if c not in ("_userId", "pump", "sensor"):
                d[c] = pd.to_numeric(d[c], errors="coerce")
        return d

    parts = [
        go("glucose", f"""
        SELECT _userId, count(*) AS n_cgm,
               count(DISTINCT floor({T}/300000)) AS slots,
               100*avg(CASE WHEN {V} BETWEEN 70 AND 180 THEN 1.0 ELSE 0.0 END) AS tir,
               100*avg(CASE WHEN {V} < 70 THEN 1.0 ELSE 0.0 END) AS t70,
               100*avg(CASE WHEN {V} < 54 THEN 1.0 ELSE 0.0 END) AS t54,
               avg({V}) AS mean_bg, 100*stddev({V})/avg({V}) AS cv
        FROM {TBL} WHERE type='cbg' AND {W} GROUP BY 1"""),
        go("boluses", f"""
        SELECT _userId,
               sum(CASE WHEN subType='normal' THEN 1 ELSE 0 END) AS n_manual,
               sum(CASE WHEN subType='automated' THEN 1 ELSE 0 END) AS n_auto,
               sum({NORM}) AS u_bolus
        FROM {TBL} WHERE type='bolus' AND {W}
          AND COALESCE(get_json_object(CAST(origin AS STRING),'$.name'),'')
              <> 'com.apple.HealthKit'
        GROUP BY 1"""),
        go("carb entries", f"""
        SELECT _userId, count(*) AS n_carb FROM {TBL}
        WHERE type='food' AND {W} GROUP BY 1"""),
        go("basal insulin", f"""
        SELECT _userId, sum({RATE} * {DUR} / 3600000.0) AS u_basal
        FROM {TBL} WHERE type='basal' AND {W} GROUP BY 1"""),
        go("closed-loop days", f"""
        SELECT _userId,
               count(DISTINCT date_trunc('DAY', from_unixtime({T}/1000))) AS loop_days
        FROM {TBL} WHERE type='dosingDecision' AND {W} GROUP BY 1"""),
        go("settings sessions", f"""
        SELECT _userId, count(DISTINCT hr) AS n_sessions FROM (
          SELECT _userId, date_trunc('HOUR', from_unixtime({T}/1000)) AS hr,
                 {H} AS h, LAG({H}) OVER (PARTITION BY _userId ORDER BY {T}) AS prev
          FROM {TBL} WHERE type='pumpSettings' AND {W}
            AND CAST(_active AS STRING) <> 'false')
        WHERE prev IS NOT NULL AND h <> prev GROUP BY 1"""),
        go("pump", f"""
        SELECT _userId, max(CASE
                 WHEN m RLIKE '(?i)sequel'    THEN 'twiist'
                 WHEN m RLIKE '(?i)insulet'   THEN 'Omnipod'
                 WHEN m RLIKE '(?i)medtronic' THEN 'Medtronic'
                 WHEN m RLIKE '(?i)medtrum'   THEN 'Medtrum' END) AS pump
        FROM (SELECT _userId, CAST(manufacturers AS STRING) AS m
              FROM {TBL} WHERE type='pumpSettings' AND {W})
        GROUP BY 1"""),
        go("sensor", f"""
        SELECT _userId, sensor FROM (
          SELECT _userId, sensor, row_number() OVER
                 (PARTITION BY _userId ORDER BY n DESC) AS rk FROM (
            SELECT _userId, count(*) AS n, CASE
                     WHEN d RLIKE '(?i)twiist'       THEN 'Libre 3'
                     WHEN d RLIKE '(?i)g7'           THEN 'Dexcom G7'
                     WHEN d RLIKE '(?i)g6'           THEN 'Dexcom G6'
                     WHEN d RLIKE '(?i)libre|abbott' THEN 'Libre (Abbott)' END AS sensor
            FROM (SELECT _userId, CAST(deviceId AS STRING) AS d FROM {TBL}
                  WHERE type='cbg' AND {W} AND deviceId IS NOT NULL)
            GROUP BY _userId, sensor))
        WHERE rk = 1 AND sensor IS NOT NULL"""),
    ]
    d = parts[0]
    for part in parts[1:]:
        d = d.merge(part, on="_userId", how="left")
    d = d.fillna({"n_manual": 0, "n_auto": 0, "n_carb": 0, "u_bolus": 0, "u_basal": 0,
                  "loop_days": 0, "n_sessions": 0})
    d["alias"] = d["_userId"].map({v: k for k, v in amap.items()})
    d["wear"] = d["slots"] / SLOTS
    d["user_boluses_per_day"] = d["n_manual"] / DAYS
    d["auto_boluses_per_day"] = d["n_auto"] / DAYS
    d["carb_entries_per_day"] = d["n_carb"] / DAYS
    d["tdd"] = (d["u_bolus"] + d["u_basal"]) / DAYS
    d["loop_frac"] = d["loop_days"] / DAYS
    d["settings_sessions_per_30d"] = d["n_sessions"] / DAYS * 30
    d["eligible"] = (d["wear"] >= 0.7) & (d["loop_frac"] >= 0.5) & d["tdd"].between(5, 250)
    # The id is an access key: it never reaches a file under runs/.
    out = d.drop(columns=["_userId"])
    out.to_csv(S.OUT / "screen.csv", index=False)
    print(f"\nwrote {S.OUT/'screen.csv'}: {len(out)} donors, "
          f"{int(out['eligible'].sum())} passing the gates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
