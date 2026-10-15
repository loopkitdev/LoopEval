#!/usr/bin/env python3
"""How much of each record has NO basal record at all.

The panel and ice_raw fill any time not covered by a basal record with the
scheduled rate (a NaN rate means "scheduled basal running", never a suspend).
That is right for a short seam between records and wrong for hours or days
where the upload simply has no insulin data: there ICE silently assumes the
schedule was delivered. This measures the uncovered time and its gap lengths,
and whether boluses or carb entries still appear inside the long gaps.

Output: ice/basal_coverage.csv, ice/basal_gaps.pkl (every uncovered stretch)
"""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import style as S  # noqa
import ice_raw as R  # noqa
from loopeval_analysis import dists as D  # noqa


def gaps_for(alias):
    ds = R.ds_for(alias)
    doses = D._load_doses(ds.doses_path)
    g = S.clip_window(alias, D._load_glucose(ds.glucose_path))
    t0, t1 = g.index[0], g.index[-1]
    b = doses[doses.delivery_type == "basal"]
    iv = pd.DataFrame({"s": b.index, "e": b.endDate}).sort_values("s")
    iv = iv[(iv.e > t0) & (iv.s < t1)]
    out, last = [], t0
    for s, e in zip(iv.s, iv.e):
        s = max(s, t0)
        if s > last:
            out.append((last, s))
        last = max(last, min(e, t1))
    if t1 > last:
        out.append((last, t1))
    gp = pd.DataFrame(out, columns=["s", "e"])
    gp["min"] = (gp.e - gp.s).dt.total_seconds() / 60
    bol = doses[doses.delivery_type != "basal"].index
    gp["boluses_inside"] = [((bol >= s) & (bol < e)).sum() for s, e in zip(gp.s, gp.e)]
    gpos = g.index
    gp["cgm_hours_inside"] = [((gpos >= s) & (gpos < e)).sum() * 5 / 60 for s, e in zip(gp.s, gp.e)]
    gp["alias"] = alias
    span = (t1 - t0).total_seconds() / 60
    long = gp[gp["min"] >= 60]
    row = {"alias": alias, "span_days": span / 1440, "uncovered_pct": 100 * gp["min"].sum() / span,
           "uncovered_ge60_pct": 100 * long["min"].sum() / span, "n_ge60": len(long),
           "longest_h": gp["min"].max() / 60 if len(gp) else 0,
           "short_seams_pct": 100 * gp.loc[gp["min"] < 60, "min"].sum() / span,
           "bolus_share_in_long": long.boluses_inside.sum() / max(len(bol), 1)}
    return row, gp


if __name__ == "__main__":
    co = S.cohort()
    S.datasets()
    with Pool(8) as p:
        res = p.map(gaps_for, list(co.alias))
    r = pd.DataFrame([x[0] for x in res]).merge(co[["alias", "pump", "sensor", "source"]], on="alias")
    r.to_csv(S.OUT / "ice" / "basal_coverage.csv", index=False)
    gp = pd.concat([x[1] for x in res])
    gp.to_pickle(S.OUT / "ice" / "basal_gaps.pkl")
    print(r[["uncovered_pct", "uncovered_ge60_pct", "short_seams_pct", "n_ge60", "longest_h", "bolus_share_in_long"]]
          .describe(percentiles=[.25, .5, .75, .9]).T.round(2).to_string())
    print("\nby pump (median uncovered >=60 min, %):", r.groupby("pump").uncovered_ge60_pct.median().round(2).to_dict())
    print("people with >10% of record in >=60-min uncovered stretches:", (r.uncovered_ge60_pct > 10).sum())
    print("gap length distribution (min):", gp["min"].quantile([.5, .9, .99]).round(1).to_dict(),
          " share of uncovered time in gaps >=60:", round(gp.loc[gp['min'] >= 60, 'min'].sum() / gp['min'].sum(), 3))
    long = gp[gp["min"] >= 60]
    print("long gaps: with CGM inside", (long.cgm_hours_inside > 0).mean().round(2),
          "; with a bolus inside", (long.boluses_inside > 0).mean().round(2))
    print(r.sort_values("uncovered_ge60_pct", ascending=False).head(12)[["alias", "pump", "source", "uncovered_ge60_pct", "n_ge60", "longest_h", "bolus_share_in_long"]].round(2).to_string(index=False))
