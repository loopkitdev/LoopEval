#!/usr/bin/env python3
"""Look for insulin-shaped structure in ICE around user boluses.

If the yardstick ISF differs from the true effect of a unit, ICE carries an
extra (ISF_yardstick - ISF_true) x activity term, shaped like the bolus's own
activity pulse and scaling with its size. Meals (no carb entries used) put a
hump in the first hours; the pulse's TAIL (3-6 h) is mostly free of them.

Events: user boluses >= 1 U with no other user bolus from 2 h before to 6 h
after, and >= 80% of the -2..+6 h window clean (ice_raw.EXCLUDE). ICE in 15-min
bins from clean intervals, as excess over the pre-bolus baseline (-2 .. -0.5 h).
Also the bolus's OWN modelled activity, ISF x units x activity curve.
Size groups: each person's events in tertiles of bolus units.

Per person, the tail slope: across events, regress mean ICE excess over 3-6 h
on the bolus's own mean activity over 3-6 h. A slope of 0 means no
insulin-shaped residue in the tail; -1 would mean ICE fully missing the
credited action (yardstick far too weak); positive means too strong.
Odd/even-week split-half checks whether the slope is a stable property.

Output: ice/bolus_event.csv, ice/bolus_tail.csv
"""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_raw import EXCLUDE, ds_for  # noqa
from loopeval_analysis.iob import percent_effect_remaining  # noqa

BIN = 15
PRE, POST = -120, 360
EST = pd.read_csv(S.OUT / "ice" / "isf_estimate.csv").set_index("alias")


def person(al):
    d = pd.read_pickle(S.OUT / "ice" / "raw" / f"{al}.pkl")
    d = d[d.on_cadence]
    good = ~d[EXCLUDE].any(axis=1)
    t = d.t0 + (d.t1 - d.t0) / 2
    g = pd.DataFrame({"dbg": np.where(good, d.bg1 - d.bg0, 0.0), "ia": np.where(good, d.ia * d.dt / 60, 0.0),
                      "dt": np.where(good, d.dt, 0.0)}, index=pd.DatetimeIndex(t)).resample(f"{BIN}min").sum()
    ok = g.dt >= 0.8 * BIN
    ice = ((g.dbg + g.ia) / (g.dt / 60)).where(ok)
    ds = ds_for(al)
    model = ds.insulin_model
    isf = EST.loc[al, "isf_est"]
    p = S.load(al)
    ub = p.manual_bolus_u.fillna(0)
    bt = ub[ub >= 1.0]
    allb = ub[ub > 0.05].index
    edges = np.arange(PRE, POST + BIN, BIN)
    # activity per 15-min bin of ONE unit, from the bolus time
    pct = percent_effect_remaining(np.arange(0, POST + BIN, BIN, dtype=float), model=model)
    act_u = np.r_[np.zeros(-PRE // BIN), np.maximum(pct[:-1] - pct[1:], 0)] * (60 / BIN)   # U/hr per unit
    rows = []
    ix = ice.index
    for tb, u in bt.items():
        others = allb[(allb > tb - pd.Timedelta(minutes=120)) & (allb < tb + pd.Timedelta(minutes=POST)) & (allb != tb)]
        if len(others):
            continue
        t0 = tb.floor(f"{BIN}min") + pd.Timedelta(minutes=PRE)
        w = ice.reindex(pd.date_range(t0, periods=len(edges) - 1, freq=f"{BIN}min"))
        if w.notna().mean() < 0.8:
            continue
        base = w.iloc[: (-30 - PRE) // BIN].mean()
        if not np.isfinite(base):
            continue
        bg_now = p.bg.asof(tb); bg_prev = p.bg.asof(tb - pd.Timedelta(minutes=60))
        rows.append({"alias": al, "t": tb, "units": u, "week": (tb - p.index[0]).days // 7,
                     "bg0": bg_now, "rise60": bg_now - bg_prev,
                     **{f"x{k}": v for k, v in zip(edges[:-1], (w - base).to_numpy())},
                     **{f"a{k}": v for k, v in zip(edges[:-1], isf * u * act_u[: len(edges) - 1])}})
    return rows


def tail_slope(e):
    tail = [c for c in e.columns if c.startswith("x") and 180 <= int(c[1:]) < 360]
    atail = ["a" + c[1:] for c in tail]
    y = e[tail].mean(axis=1); x = e[atail].mean(axis=1)
    m = y.notna()
    if m.sum() < 15 or x[m].std() == 0:
        return np.nan, int(m.sum())
    return np.polyfit(x[m], y[m], 1)[0], int(m.sum())


if __name__ == "__main__":
    al = list(EST.dropna(subset=["isf_est"]).index)
    S.datasets()
    with Pool(8) as pl:
        ev = pd.DataFrame([r for rows in pl.map(person, al) for r in rows])
    ev = ev[ev.groupby("alias").units.transform("size") >= 6]
    ev.to_pickle(S.OUT / "ice" / "bolus_events.pkl")
    xs = [c for c in ev.columns if c.startswith("x")]
    ev["size"] = pd.cut(ev.groupby("alias").units.rank(pct=True, method="first"), [0, 1/3, 2/3, 1],
                       labels=["small", "mid", "large"])
    pp = ev.groupby(["alias", "size"], observed=True)[xs + ["a" + c[1:] for c in xs] + ["units"]].median()
    curve = pp.groupby("size").median().T
    curve.to_csv(S.OUT / "ice" / "bolus_event.csv")
    print(f"{len(ev)} isolated user boluses >= 1 U in {ev.alias.nunique()} people")
    print("median bolus by size group:", pp.groupby("size").units.median().round(2).to_dict())
    show = [-60, 0, 30, 60, 90, 120, 180, 240, 300, 345]
    print(pd.DataFrame({sz: [curve.loc[f"x{k}", sz] for k in show] for sz in ["small", "mid", "large"]}, index=show)
          .round(1).rename_axis("min").T.to_string())
    print("own activity term (median, mg/dL/hr):")
    print(pd.DataFrame({sz: [curve.loc[f"a{k}", sz] for k in show] for sz in ["small", "mid", "large"]}, index=show)
          .round(1).rename_axis("min").T.to_string())
    # likely corrections, chosen from glucose alone: high and NOT rising in the prior hour
    cor = ev[(ev.bg0 >= 150) & (ev.rise60 <= 0)]
    pc = cor.groupby("alias")[xs + ["a" + c[1:] for c in xs] + ["units"]].median()
    pc = pc[cor.groupby("alias").size() >= 5]
    cc = pc.median()
    print(f"\nlikely corrections (glucose >= 150, not rising over the prior hour): {len(cor)} events, {len(pc)} people with >= 5;"
          f" median {cc.units:.2f} U")
    print(pd.DataFrame({"ICE excess": [cc[f"x{k}"] for k in show], "own activity": [cc[f"a{k}"] for k in show]},
                       index=show).round(1).rename_axis("min").T.to_string())
    cc.to_csv(S.OUT / "ice" / "bolus_correction_curve.csv")
    rows = []
    for a, e in ev.groupby("alias"):
        s_all, n = tail_slope(e)
        s1, _ = tail_slope(e[e.week % 2 == 1]); s2, _ = tail_slope(e[e.week % 2 == 0])
        rows.append({"alias": a, "slope": s_all, "n": n, "s_odd": s1, "s_even": s2})
    tl = pd.DataFrame(rows).merge(S.cohort()[["alias", "sensor", "strategy"]], on="alias")
    fm = pd.read_csv(S.OUT / "formulation.csv")[["alias", "category"]] if (S.OUT / "formulation.csv").exists() else None
    if fm is not None:
        tl = tl.merge(fm, on="alias", how="left")
    tl.to_csv(S.OUT / "ice" / "bolus_tail.csv", index=False)
    v = tl.dropna(subset=["slope"])
    print(f"\ntail slope (ICE excess 3-6 h on own activity 3-6 h), {len(v)} people with >= 15 events: "
          f"median {v.slope.median():+.2f} (p10 {v.slope.quantile(.1):+.2f}, p90 {v.slope.quantile(.9):+.2f}); "
          f"share negative {(v.slope < 0).mean():.0%}")
    h = v.dropna(subset=["s_odd", "s_even"])
    print(f"split-half: rho {stats.spearmanr(h.s_odd, h.s_even)[0]:.2f} (n={len(h)})")
    for f in ("strategy", "sensor", "category"):
        if f in v:
            print(f"  by {f}:", v.groupby(f).slope.agg(['median', 'size']).round(2).to_dict('index'))
