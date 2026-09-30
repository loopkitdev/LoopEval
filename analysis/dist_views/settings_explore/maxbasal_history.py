import sys; sys.path.insert(0,'/Users/pete/dev/loopeval-eda/analysis/dist_views'); sys.path.insert(0,'/Users/pete/dev/loopeval-eda/analysis')
import numpy as np, pandas as pd, style as S, screen_cohort as SC
from loopeval_analysis.tidepool.conn import query
amap = SC._ids(); co = S.cohort()
ids = {a: amap[a] for a in co.alias if a in amap}; rev = {v:k for k,v in ids.items()}
lst = ",".join(f"'{u}'" for u in sorted(set(ids.values())))
num = lambda path: (f"COALESCE(CAST(get_json_object(CAST({path[0]} AS STRING),'$.{path[1]}.value.$numberDouble') AS DOUBLE),"
                    f"CAST(get_json_object(CAST({path[0]} AS STRING),'$.{path[1]}.value.$numberInt') AS DOUBLE))")
q = f"""SELECT _userId, {SC.T} AS t,
          {num(('basal','rateMaximum'))} AS max_basal,
          {num(('bolus','amountMaximum'))} AS max_bolus,
          md5(COALESCE(CAST(insulinSensitivities AS STRING),'')) AS h_isf,
          md5(COALESCE(CAST(basalSchedules AS STRING),''))       AS h_basal,
          md5(COALESCE(CAST(bgTargets AS STRING),''))            AS h_target,
          md5(COALESCE(CAST(carbRatios AS STRING),''))           AS h_cr
        FROM {SC.TBL}
        WHERE type='pumpSettings' AND _userId IN ({lst})
          AND {SC.T} BETWEEN {SC.START - 30*86400000} AND {SC.END}"""
d = query(q)
d["alias"] = d._userId.map(rev); d = d.drop(columns="_userId")          # ids never leave memory
d["t"] = pd.to_datetime(pd.to_numeric(d.t), unit="ms", utc=True)
for c in ("max_basal","max_bolus"): d[c] = pd.to_numeric(d[c], errors="coerce")
d = d.sort_values(["alias","t"])
d.to_pickle(S.OUT/"pumpsettings_history.pkl")
print(f"{len(d):,} pumpSettings rows for {d.alias.nunique()} donors")
nv = d.dropna(subset=["max_basal"]).groupby("alias").max_basal.nunique()
print(f"donors with a max basal recorded: {len(nv)};  more than one distinct value in the window: {(nv>1).sum()}")
print("distinct values per donor:", nv.value_counts().sort_index().to_dict())
