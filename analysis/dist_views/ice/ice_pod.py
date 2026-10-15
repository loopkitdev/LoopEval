#!/usr/bin/env python3
"""ICE around Omnipod pod changes (from pull_pod_changes.py) — the same event
study and detector as ice_site.py, with the change anchored at the END of the
"No pod paired" run (the new pod's pairing).

Output: ice/pod_event.csv, ice/pod_changes_scored.csv, ice/pod_null.csv
"""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_site import person  # noqa

if __name__ == "__main__":
    pc = pd.read_pickle(S.OUT / "ice" / "pod_changes.pkl")
    have = {p.stem for p in (S.OUT / "ice" / "raw").glob("*.pkl")}
    args = [(a, g.t_end.astype("int64").to_numpy() / 3.6e12) for a, g in pc.groupby("alias") if a in have]
    S.datasets()
    with Pool(8) as p:
        res = p.map(person, args)
    ev = pd.concat([r[0] for r in res if r[0] is not None])
    sc = pd.DataFrame([x for r in res for x in r[1]])
    nl = pd.DataFrame([x for r in res for x in r[2]])
    pp = ev.groupby(["kind", "alias", "bin"])[["ice_x", "v_x", "ia_x"]].median().reset_index()
    cv = pp.groupby(["kind", "bin"]).agg(ice_x=("ice_x", "median"), v_x=("v_x", "median"),
                                         ia_x=("ia_x", "median"), people=("alias", "nunique")).reset_index()
    cv.to_csv(S.OUT / "ice" / "pod_event.csv", index=False)
    sc.to_csv(S.OUT / "ice" / "pod_changes_scored.csv", index=False)
    nl.to_csv(S.OUT / "ice" / "pod_null.csv", index=False)
    print(f"{sc.alias.nunique()} people, {len(sc)} changes scored: {sc.kind.value_counts().to_dict()}")
    q95, q99 = nl.pre6_ice_x.quantile([.95, .99])
    print(f"null 6-h excess: median {nl.pre6_ice_x.median():.1f}, p95 {q95:.1f}, p99 {q99:.1f}")
    for kind, g in sc.groupby("kind"):
        print(f"{kind:8s} n={len(g):5d}  median pre-6h excess {g.pre6_ice_x.median():6.1f}  "
              f"> p95: {(g.pre6_ice_x > q95).mean():.0%}  > p99: {(g.pre6_ice_x > q99).mean():.0%}")
    for kind in ("routine", "early"):
        c = cv[cv.kind == kind].set_index("bin")
        print(kind, c.loc[[-12, -6, -3, -1, -0.5, 0, 1, 3, 6], ["ice_x", "v_x", "ia_x", "people"]].round(1).T.to_string())
