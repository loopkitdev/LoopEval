#!/usr/bin/env python3
"""The donor pool the cohort was drawn from, measured the same way.

View 00 draws the pool's outcome distribution behind our own, and the study
claims the pool-matched stratum is indistinguishable from it. Both need the
pool measured on the SAME window, with the SAME statistic and the SAME wear
gate as the cohort — and they need the `ours` flag to mean the cohort that
exists on disk now, not a donor list from an earlier pass. Writing this as a
named script is the point: the previous pool_compare.csv was an ad-hoc artefact
that still flagged a 60-donor selection after the cohort had moved on, which
makes every comparison against it a comparison with someone else's sample
(lessons 22 and 27).

Run:  python3 pool_compare.py             (needs Databricks credentials)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S                                            # noqa: E402
import screen_cohort as SC                                   # noqa: E402
from loopeval_analysis.tidepool.conn import query             # noqa: E402

WEAR_MIN = 0.70            # the cohort's own eligibility gate


def main() -> int:
    T, V, TBL = SC.T, SC.V, SC.TBL
    W = f"{T} BETWEEN {SC.START} AND {SC.END}"
    print(f"window {SC.DAYS:.0f} days, pool-wide")

    print("  glucose…", flush=True)
    g = query(f"""
        SELECT _userId, count(*) AS n,
               count(DISTINCT floor({T}/300000)) AS slots,
               100*avg(CASE WHEN {V} BETWEEN 70 AND 180 THEN 1.0 ELSE 0.0 END) AS tir,
               100*avg(CASE WHEN {V} < 54 THEN 1.0 ELSE 0.0 END) AS t54,
               100*avg(CASE WHEN {V} > 250 THEN 1.0 ELSE 0.0 END) AS t250,
               avg({V}) AS mean_bg, 100*stddev({V})/avg({V}) AS cv
        FROM {TBL} WHERE type='cbg' AND {W} GROUP BY 1""")

    print("  automation…", flush=True)
    a = query(f"""
        SELECT _userId, max(aid) AS aid FROM (
          SELECT _userId, 1 AS aid FROM {TBL}
            WHERE type='bolus' AND subType='automated' AND {W}
          UNION ALL
          SELECT _userId, 1 AS aid FROM {TBL}
            WHERE type='dosingDecision' AND {W})
        GROUP BY 1""")

    for c in ("n", "slots", "tir", "t54", "t250", "mean_bg", "cv"):
        g[c] = pd.to_numeric(g[c], errors="coerce")
    d = g.merge(a, on="_userId", how="left")
    d["aid"] = pd.to_numeric(d["aid"], errors="coerce").fillna(0).astype(bool)
    d["wear"] = d["slots"] / SC.SLOTS
    d = d[d["wear"] >= WEAR_MIN].copy()

    # `ours` means the pool-matched stratum as cohort.csv defines it today.
    amap = SC._ids()
    co = S.cohort()
    core = set(co[co["stratum"].eq("core")]["alias"])
    ours_ids = {amap[a] for a in core if a in amap}
    missing = sorted(a for a in core if a not in amap)
    d["ours"] = d["_userId"].isin(ours_ids)
    print(f"  pool with wear >= {WEAR_MIN:.0%}: {len(d):,}   of which AID: {d.aid.sum():,}")
    print(f"  core stratum: {len(core)} aliases, {len(ours_ids)} resolved to ids, "
          f"{int(d.ours.sum())} present in the window")
    if missing:
        print(f"  ! no id for {len(missing)} core aliases: {missing}")

    d = d.drop(columns=["_userId"])
    d.to_csv(S.OUT / "pool_compare.csv", index=False)

    pool = d[d.aid & ~d.ours]
    ours = d[d.ours]
    print(f"\n  {'statistic':10s} {'pool':>9s} {'ours':>9s}   n_pool={len(pool)} n_ours={len(ours)}")
    for c in ("tir", "mean_bg", "cv", "t54", "t250"):
        print(f"  {c:10s} {pool[c].median():9.1f} {ours[c].median():9.1f}")
    try:
        from scipy.stats import mannwhitneyu
        for c in ("tir", "mean_bg", "cv", "t54", "t250"):
            p = mannwhitneyu(pool[c].dropna(), ours[c].dropna()).pvalue
            print(f"    {c:10s} p = {p:.3f}")
    except ImportError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
