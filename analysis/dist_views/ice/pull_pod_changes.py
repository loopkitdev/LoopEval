#!/usr/bin/env python3
"""Omnipod pod changes, inferred from Loop's "No pod paired" decision errors.

Omnipod-via-Loop uploads no site-change event and no alarm. But between
deactivating one pod and pairing the next, every Loop cycle records
dosingDecision.errors = pumpManagerError with metadata.detail = "configuration"
("No pod paired", localised by app language). A run of those marks a pod
change. A pod fault (an occlusion on a pod is unrecoverable) forces the same
deactivate-and-pair, so a fault shows as an EARLY change: the old pod lasted
much less than this person's usual pod life.

Only timestamps are selected; donor ids are mapped to aliases before writing.

Output: ice/pod_changes.pkl  alias, t_start, t_end (the no-pod run), n_cycles
"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import screen_cohort as SC  # noqa
import style as S  # noqa
from loopeval_analysis.tidepool.conn import query  # noqa

LO, HI = 1774137600000, 1785715200000
MERGE_MIN = 120          # no-pod cycles closer than this belong to one change


def main():
    amap = SC._ids()
    co = S.cohort()
    om = co[co.pump == "Omnipod"].alias
    ids = {a: amap[a] for a in om if a in amap}
    lst = ",".join(f"'{u}'" for u in sorted(set(ids.values())))
    d = query(f"""SELECT _userId, {SC.T} AS t_ms FROM {SC.TBL}
                  WHERE type='dosingDecision' AND errors IS NOT NULL
                    AND {SC.T} BETWEEN {LO} AND {HI} AND _userId IN ({lst})
                    AND get_json_object(CAST(errors AS STRING), '$[0].metadata.detail') = 'configuration'""")
    rev = {v: k for k, v in ids.items()}
    d["alias"] = d.pop("_userId").map(rev)
    d["t"] = pd.to_datetime(pd.to_numeric(d.pop("t_ms")), unit="ms", utc=True)
    rows = []
    for a, g in d.sort_values("t").groupby("alias"):
        gap = g.t.diff().dt.total_seconds() / 60
        ep = (gap.isna() | (gap > MERGE_MIN)).cumsum()
        for _, e in g.groupby(ep):
            rows.append({"alias": a, "t_start": e.t.iloc[0], "t_end": e.t.iloc[-1], "n_cycles": len(e)})
    pc = pd.DataFrame(rows)
    pc.to_pickle(S.OUT / "ice" / "pod_changes.pkl")
    pc["life_h"] = pc.groupby("alias").t_end.diff().dt.total_seconds() / 3600
    print(f"{len(pc)} pod-change episodes in {pc.alias.nunique()} of {len(ids)} Omnipod people")
    print("pod life (h) between changes:", pc.life_h.quantile([.05, .1, .25, .5, .75, .9, .95]).round(1).to_dict())
    print("no-pod duration (min):", ((pc.t_end - pc.t_start).dt.total_seconds() / 60).quantile([.5, .9]).round(0).to_dict(),
          " cycles per episode median", pc.n_cycles.median())
    per = pc.groupby("alias").life_h.median()
    print("per-person median pod life: p10 %.0f, median %.0f, p90 %.0f" % tuple(per.quantile([.1, .5, .9])))
    rel = pc.life_h / pc.alias.map(per)
    print("share of changes under 0.6x the person's usual life:", round((rel < 0.6).mean(), 3),
          " under 0.25x:", round((rel < 0.25).mean(), 3))


if __name__ == "__main__":
    main()
