#!/usr/bin/env python3
"""ICE around infusion-site changes (twiist) — the occlusion / failing-site signature.

If a site stops delivering, the record still shows insulin going in, the model
credits it as absorbed, glucose rises anyway, and ICE (= velocity + ISF x
absorbed) runs HIGH until the site is changed. So a failing site should look
like sustained excess ICE that ends at a cannula prime.

ICE here is the 30-minute mean on clean intervals (ice_raw flags excluded, the
post-gap flag kept since it showed no effect), expressed as EXCESS over the
person's own median at that local hour (changes cluster in the evening, ICE has
a daily rhythm). Velocity and insulin terms are kept separately.

Site changes: cannula primes, merged within 3 h (site_change.site_changes).
Early = the previous site lasted under EARLY_FRAC of the person's own median
site life (some people change every 24-48 h as a routine); routine otherwise.

Event study: excess in 30-min bins from 24 h before to 12 h after each change.
Detector: mean excess over the 6 h before each change, against the same
statistic at random times in the same person (>= 24 h from any change).

Output: ice/site_event.csv, ice/site_changes_scored.csv, ice/site_null.csv
"""
from __future__ import annotations
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_raw import FLAGS, ds_for  # noqa
from site_change import site_changes  # noqa

# the event flags are DEFINED by these events; excluding them here would be circular
EXCL = [f for f in FLAGS if f not in ("post_gap", "pre_early", "occlusion")]
BIN_H = 0.5
PRE_H, POST_H, DET_H = 24, 12, 6
EARLY_FRAC = 0.6


def series(alias):
    """30-min ICE, velocity and insulin terms on a regular grid, plus hour-of-day excess."""
    d = pd.read_pickle(S.OUT / "ice" / "raw" / f"{alias}.pkl")
    d = d[d.on_cadence & ~d[EXCL].any(axis=1)]
    t = d.t0 + (d.t1 - d.t0) / 2
    g = pd.DataFrame({"v": d.v.to_numpy() * d.dt.to_numpy(), "ia": d.ia.to_numpy() * d.dt.to_numpy(),
                      "dt": d.dt.to_numpy()}, index=t.to_numpy()).resample("30min").sum()
    g = g[g.dt >= 20]                                   # at least 20 of 30 min observed
    out = pd.DataFrame({"v": g.v / g.dt, "ia": g.ia / g.dt}, index=g.index)
    out["ice"] = out.v + out.ia
    off = ds_for(alias).utc_offset_h
    hour = ((out.index + pd.Timedelta(hours=off)).hour)
    for c in ("ice", "v", "ia"):
        out[c + "_x"] = out[c] - out.groupby(hour)[c].transform("median")
    return out


def person(args):
    alias, times = args
    s = series(alias)
    th = s.index.asi8 / 3.6e12
    ts = np.sort(np.asarray(times, dtype=float))
    prev_age = np.r_[np.nan, np.diff(ts)]
    life = np.nanmedian(prev_age) if len(ts) > 2 else 72.0
    ev, sc = [], []
    for k, tc in enumerate(ts):
        rel = th - tc
        m = (rel >= -PRE_H) & (rel < POST_H)
        if m.sum() < 20:
            continue
        kind = ("first" if np.isnan(prev_age[k]) else
                "early" if prev_age[k] < EARLY_FRAC * life else "routine")
        b = np.floor(rel[m] / BIN_H) * BIN_H
        e = pd.DataFrame({"bin": b, "ice_x": s.ice_x.to_numpy()[m], "v_x": s.v_x.to_numpy()[m],
                          "ia_x": s.ia_x.to_numpy()[m]})
        e["kind"] = kind; e["alias"] = alias; e["k"] = k
        ev.append(e)
        pre = (rel >= -DET_H) & (rel < 0)
        if pre.sum() >= 6:
            sc.append({"alias": alias, "t": tc, "kind": kind, "prev_age_h": prev_age[k],
                       "life_h": life, "pre6_ice_x": s.ice_x.to_numpy()[pre].mean(), "pre6_v_x": s.v_x.to_numpy()[pre].mean(),
                       "pre6_ia_x": s.ia_x.to_numpy()[pre].mean(), "n_pre": int(pre.sum())})
    # null: 6-h windows ending at random half-hours >= 24 h from any change
    rng = np.random.default_rng(abs(hash(alias)) % 2**32)
    far = np.array([np.min(np.abs(ts - x)) >= 24 for x in th]) if len(ts) else np.ones(len(th), bool)
    cand = th[far]
    null = []
    for x in rng.choice(cand, size=min(200, len(cand)), replace=False) if len(cand) else []:
        pre = (th >= x - DET_H) & (th < x)
        if pre.sum() >= 6:
            null.append({"alias": alias, "pre6_ice_x": s.ice_x.to_numpy()[pre].mean()})
    return (pd.concat(ev) if ev else None), sc, null


if __name__ == "__main__":
    ch = site_changes()
    have = {p.stem for p in (S.OUT / "ice" / "raw").glob("*.pkl")}
    args = [(a, g.t.astype("int64").to_numpy() / 3.6e12) for a, g in ch.groupby("alias") if a in have]
    S.datasets()
    with Pool(8) as p:
        res = p.map(person, args)
    ev = pd.concat([r[0] for r in res if r[0] is not None])
    sc = pd.DataFrame([x for r in res for x in r[1]])
    nl = pd.DataFrame([x for r in res for x in r[2]])
    # per-person medians first, then across people
    pp = ev.groupby(["kind", "alias", "bin"])[["ice_x", "v_x", "ia_x"]].median().reset_index()
    curve = pp.groupby(["kind", "bin"]).agg(ice_x=("ice_x", "median"), v_x=("v_x", "median"),
                                            ia_x=("ia_x", "median"), people=("alias", "nunique")).reset_index()
    curve.to_csv(S.OUT / "ice" / "site_event.csv", index=False)
    sc.to_csv(S.OUT / "ice" / "site_changes_scored.csv", index=False)
    nl.to_csv(S.OUT / "ice" / "site_null.csv", index=False)
    print(f"{sc.alias.nunique()} people, {len(sc)} changes scored: {sc.kind.value_counts().to_dict()}")
    for kind in ("routine", "early"):
        c = curve[curve.kind == kind].set_index("bin")
        sel = c.loc[[-24, -12, -6, -3, -1, -0.5, 0, 1, 3, 6, 11.5]] if -24 in c.index else c
        print(f"\n{kind}:\n", sel[["ice_x", "v_x", "ia_x", "people"]].round(1).to_string())
    q95 = nl.pre6_ice_x.quantile(0.95); q99 = nl.pre6_ice_x.quantile(0.99)
    print(f"\nnull 6-h excess: median {nl.pre6_ice_x.median():.1f}, p95 {q95:.1f}, p99 {q99:.1f} (n={len(nl)})")
    for kind, g in sc.groupby("kind"):
        print(f"{kind:8s} n={len(g):5d}  median pre-6h excess {g.pre6_ice_x.median():6.1f}  "
              f"> null p95: {(g.pre6_ice_x > q95).mean():.0%}   > null p99: {(g.pre6_ice_x > q99).mean():.0%}")
