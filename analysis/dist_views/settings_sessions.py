"""Settings maintenance, on the definition the justification actually specified:
a content change, with multiple changes in the same hour counted as ONE event.

Three earlier attempts each measured something else — uploads (a donor uploaded
27,899 rows holding six payloads), payload transitions (counted oscillation
between stored profiles), and distinct configurations (counted every segment
edit separately). The diff shows why the last one over-counts: one editing
session writes one row PER SEGMENT touched, several within the same minute.

What the payloads actually show, from one twiist donor's consecutive rows: basal
and ISF never move together (which rules out an override, since an override
scales both at once); a single SEGMENT changes at a time (19h basal 0.7 -> 0.6,
then 00h 1.5 -> 1.2 -> 1.3); and the increments are human-sized and
human-rounded — basal in steps of 0.1 U/hr, ISF on round mg/dL values
(2.886 = 52, 3.053 = 55, 3.330 = 60 mg/dL per unit). This is a person tuning,
not a machine adapting and not a preset toggling.

Result on the eligible pool: median 1.3 sessions per 30 days, p90 8.0, and the
strata land at 25% none / 56% one-to-three / 19% more than three. twiist and
Omnipod donors have the SAME median (0.7), so the axis is not device-specific
and needs no per-device restriction.
"""
import sys, os
import pandas as pd
sys.path.insert(0, "/Users/pete/dev/loopeval-eda/analysis")
from loopeval_analysis.tidepool.conn import query
base = ("/private/tmp/claude-501/-Users-pete-dev-loopeval-eda/"
        "bfa63131-1394-4401-ba0d-468c73f27a9b/scratchpad")
tbl = "prod.default.device_data"
T = "CAST(get_json_object(time,'$.$date.$numberLong') AS BIGINT)"
S, E = 1775088000000, 1782864000000
DAYS = (E - S) / 86400000
F = ["basalSchedules", "carbRatios", "insulinSensitivities", "bgTargets", "bgSafetyLimit"]
H = "md5(concat_ws('|', " + ", ".join(f"COALESCE(CAST({f} AS STRING),'')" for f in F) + "))"

d = query(f"""
SELECT _userId, count(DISTINCT hr) AS n_sessions FROM (
  SELECT _userId, date_trunc('HOUR', from_unixtime({T}/1000)) AS hr, {H} AS h,
         LAG({H}) OVER (PARTITION BY _userId ORDER BY {T}) AS prev
  FROM {tbl} WHERE type='pumpSettings' AND {T} BETWEEN {S} AND {E}
    AND CAST(_active AS STRING) <> 'false')
WHERE prev IS NOT NULL AND h <> prev
GROUP BY 1""")
d["n_sessions"] = pd.to_numeric(d["n_sessions"], errors="coerce")
d["sessions_per_30d"] = d["n_sessions"] / DAYS * 30
d.to_csv(f"{base}/settings_sessions.csv", index=False)

g = pd.read_csv(f"{base}/eligible_grid.csv")
elig = set(g["_userId"])
e = d[d["_userId"].isin(elig)]
v = e["sessions_per_30d"]
print(f"eligible donors with any settings change: {len(e):,}")
print(f"editing sessions per 30 days: median {v.median():.1f}  p90 {v.quantile(.9):.1f}  "
      f"p99 {v.quantile(.99):.1f}  max {v.max():.0f}")
print("\nagainst the earlier attempts, same donors:")
old = pd.read_csv(f"{base}/settings_clean.csv")
old = old[old["_userId"].isin(elig)]["edits_per_30d"]
print(f"  distinct configurations : median {old.median():.1f}  p90 {old.quantile(.9):.1f}  max {old.max():.0f}")
print(f"  hour-collapsed sessions : median {v.median():.1f}  p90 {v.quantile(.9):.1f}  max {v.max():.0f}")
print("\nstrata on the corrected metric (eligible pool):")
full = g[["_userId","pump","dosing","mine"]].merge(d, on="_userId", how="left")
full["sessions_per_30d"] = full["sessions_per_30d"].fillna(0)
for lo, hi, lab in ((-.01,.001,"none"), (.001,3,"1–3 / 30 d"), (3,1e9,">3 / 30 d")):
    m = (full["sessions_per_30d"] > lo) & (full["sessions_per_30d"] <= hi)
    print(f"  {lab:12s} {m.sum():6,}  ({m.mean():.0%})")
print("\nby pump (median sessions/30 d):")
print(full.groupby("pump")["sessions_per_30d"].agg(["median","mean","max","size"]).round(1).to_string())
