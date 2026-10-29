"""x pool (ice_x32): per donor the dominant CGM family over the export window (per-reading deviceId, as the pilot's
2026-10-15-additive-sensor/pull_sensor.py) and age at the window's midpoint from seagull_profiles.birthday (whole years,
90+ as 90; as ice dist_views/pull_age.py). Aliases only out (Pete 2026-10-28, LESSONS 525).
Writes sensor_x.csv (alias, kind, n) and age_x.csv (alias, age_years)."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/pete/dev/loopeval-additive/analysis")
from loopeval_analysis.tidepool.conn import query
from loopeval_analysis.tidepool.etl import _TMS
OUT = "/Users/pete/.loop-eval/runs/2026-10-28-additive-xpool/"
amap = json.load(open("/Users/pete/.loop-eval/ice/alias_map_x.json"))
inv = {v: k for k, v in amap.items()}
ids = ",".join(f"'{u}'" for u in amap.values())
s, e = 1781568000000, 1791417600000          # 2026-06-16 .. 2026-10-08 UTC ms
q = f"""
SELECT _userId, kind, count(*) AS n FROM (
  SELECT _userId, {_TMS} AS t_ms, CASE
     WHEN d RLIKE '(?i)twiist' THEN 'Libre 3 (twiist)'
     WHEN d RLIKE '(?i)g7' THEN 'Dexcom G7'
     WHEN d RLIKE '(?i)g6' THEN 'Dexcom G6'
     WHEN d RLIKE '(?i)libre3|libre 3' THEN 'Libre 3'
     WHEN d RLIKE '(?i)libre2|libre 2' THEN 'Libre 2'
     WHEN d RLIKE '(?i)libre|abbott' THEN 'Libre (other)'
     WHEN d RLIKE '(?i)medtronic|guardian' THEN 'Medtronic'
     WHEN d IS NULL THEN 'unlabeled'
     ELSE 'other' END AS kind
  FROM (SELECT _userId, time, CAST(deviceId AS STRING) AS d FROM prod.default.device_data
        WHERE type='cbg' AND _userId IN ({ids})))
WHERE t_ms BETWEEN {s} AND {e} GROUP BY 1, 2"""
df = query(q); df["alias"] = df["_userId"].map(inv)
df.drop(columns="_userId").to_csv(OUT + "sensor_x.csv", index=False)
print(df.groupby("kind")["alias"].nunique().sort_values(ascending=False).to_string())
mid = pd.Timestamp("2026-08-11")
pr = query(f"SELECT userid AS uid, birthday FROM prod.default.seagull_profiles WHERE userid IN ({ids}) AND birthday IS NOT NULL")
pr["alias"] = pr.uid.map(inv); b = pd.to_datetime(pr.birthday, errors="coerce")
pr["age_years"] = np.minimum(np.floor((mid - b).dt.days / 365.25), 90)
pr = pr.dropna(subset=["alias", "age_years"]).groupby("alias").age_years.first().reset_index()
pr.to_csv(OUT + "age_x.csv", index=False)
print(f"ages for {len(pr)} of {len(amap)}; median {pr.age_years.median()}")
