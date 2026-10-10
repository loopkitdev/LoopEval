#!/usr/bin/env python3
"""Occlusion alarms (twiist), site changes and ICE.

  * how often an occlusion alarm is followed by a site change, and how soon
  * ICE excess around occlusion alarms (event study, -12 h .. +6 h)
  * among early site changes: does an occlusion alarm in the prior 24 h go with
    a larger pre-change ICE excess?
Alarms within 30 min of each other are merged into one episode.

Output: ice/occlusion_event.csv, ice/occlusion_episodes.csv
"""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_site import series  # noqa
from site_change import site_changes  # noqa

MERGE_MIN = 30


def episodes(al):
    al = al.sort_values("t")
    gap = al.t.diff().dt.total_seconds() / 60
    start = gap.isna() | (gap > MERGE_MIN)
    e = al[start].copy()
    e["n_alarms"] = start.cumsum().map(start.cumsum().value_counts()).loc[start].to_numpy()
    return e


def person(args):
    alias, occ_h, chg_h = args
    s = series(alias)
    th = s.index.asi8 / 3.6e12
    ev = []
    for k, ta in enumerate(occ_h):
        rel = th - ta
        m = (rel >= -12) & (rel < 6)
        if m.sum() < 12:
            continue
        ev.append(pd.DataFrame({"bin": np.floor(rel[m] / 0.5) * 0.5, "ice_x": s.ice_x.to_numpy()[m],
                                "v_x": s.v_x.to_numpy()[m], "ia_x": s.ia_x.to_numpy()[m],
                                "alias": alias, "k": k}))
    return pd.concat(ev) if ev else None


if __name__ == "__main__":
    al = pd.read_pickle(S.OUT / "ice" / "alarms.pkl")
    occ = pd.concat([episodes(g) for _, g in al[al.alarmType == "occlusion"].groupby("alias")])
    ch = site_changes()
    have = {p.stem for p in (S.OUT / "ice" / "raw").glob("*.pkl")}
    # alarm -> next site change
    rows = []
    for a, g in occ.groupby("alias"):
        ts = np.sort(ch[ch.alias == a].t.astype("int64").to_numpy() / 3.6e12)
        for t in g.t.astype("int64").to_numpy() / 3.6e12:
            j = np.searchsorted(ts, t)
            rows.append({"alias": a, "t_h": t,
                         "to_next_change_h": ts[j] - t if j < len(ts) else np.nan,
                         "since_last_change_h": t - ts[j - 1] if j > 0 else np.nan})
    oe = pd.DataFrame(rows)
    oe.to_csv(S.OUT / "ice" / "occlusion_episodes.csv", index=False)
    print(f"occlusion episodes {len(oe)} in {oe.alias.nunique()} people (from {int((al.alarmType=='occlusion').sum())} alarms)")
    for h in (1, 3, 6, 24):
        print(f"  followed by a site change within {h:>2} h: {(oe.to_next_change_h <= h).mean():.0%}")
    print(f"  site age at the alarm: median {oe.since_last_change_h.median():.0f} h "
          f"(p10 {oe.since_last_change_h.quantile(.1):.0f}, p90 {oe.since_last_change_h.quantile(.9):.0f})")
    # early site changes with/without an alarm in the prior 24 h
    sc = pd.read_csv(S.OUT / "ice" / "site_changes_scored.csv")
    oa = {a: g.t_h.to_numpy() for a, g in oe.groupby("alias")}
    sc["alarm24"] = [bool(len(oa.get(a, [])) and np.any((oa[a] <= t) & (oa[a] > t - 24))) for a, t in zip(sc.alias, sc.t)]
    print("\nshare of site changes preceded (24 h) by an occlusion alarm:",
          sc.groupby("kind").alarm24.mean().round(3).to_dict())
    print("pre-6h ICE excess by kind x alarm (median, n):")
    print(sc.groupby(["kind", "alarm24"]).pre6_ice_x.agg(["median", "size"]).round(1).to_string())
    nl = pd.read_csv(S.OUT / "ice" / "site_null.csv")
    q95 = nl.pre6_ice_x.quantile(.95)
    hi = sc[sc.pre6_ice_x > 100]
    print(f"\nchanges with pre-6h excess > 100: {len(hi)}; with an alarm in the prior 24 h: {hi.alarm24.mean():.0%}")
    args = [(a, g.t_h.to_numpy(), None) for a, g in oe.groupby("alias") if a in have]
    with Pool(8) as p:
        ev = pd.concat([r for r in p.map(person, args) if r is not None])
    pp = ev.groupby(["alias", "bin"])[["ice_x", "v_x", "ia_x"]].median().reset_index()
    cv = pp.groupby("bin").agg(ice_x=("ice_x", "median"), v_x=("v_x", "median"), ia_x=("ia_x", "median"),
                               people=("alias", "nunique")).reset_index()
    cv.to_csv(S.OUT / "ice" / "occlusion_event.csv", index=False)
    print("\nICE excess around an occlusion alarm:\n", cv.set_index("bin").loc[[-12, -6, -3, -2, -1, -0.5, 0, 0.5, 1, 2, 3, 5.5]].round(1).to_string())
