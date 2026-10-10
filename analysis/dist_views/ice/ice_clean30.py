#!/usr/bin/env python3
"""Clean 30-minute ICE — the working series for characterising counteraction.

From ice/raw/<alias>.pkl: on-cadence intervals free of every ice_raw.EXCLUDE
flag, summed into fixed 30-minute UTC bins; a bin is kept when at least 25 of
its 30 minutes are clean. ICE(bin) = sum(glucose change)/T + sum(ISF x absorbed)/T,
mg/dL per hour; the velocity and insulin terms are kept separately. Local hour
and a fasting tag (no announced carbs on board, no user bolus in the prior
4 h — taken from the 5-min panel) ride along.

Output: ice/clean30/<alias>.pkl, ice/clean30_person.csv (per-person summary)
"""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_raw import EXCLUDE, ds_for  # noqa
from ice_first import _quiet_mask  # noqa

OUTD = S.OUT / "ice" / "clean30"
MIN_MIN = 25


def build(alias):
    d = pd.read_pickle(S.OUT / "ice" / "raw" / f"{alias}.pkl")
    d = d[d.on_cadence & ~d[EXCLUDE].any(axis=1)]
    t = d.t0 + (d.t1 - d.t0) / 2
    g = pd.DataFrame({"dbg": (d.bg1 - d.bg0).to_numpy(), "ia_mg": (d.ia * d.dt / 60).to_numpy(),
                      "dt": d.dt.to_numpy(), "bg": (d.bg1 * d.dt).to_numpy()},
                     index=pd.DatetimeIndex(t)).resample("30min").sum()
    g = g[g.dt >= MIN_MIN]
    T = g.dt / 60
    out = pd.DataFrame({"v": g.dbg / T, "ia": g.ia_mg / T, "bg": g.bg / g.dt}, index=g.index)
    out["ice"] = out.v + out.ia
    off = ds_for(alias).utc_offset_h
    out["hour"] = (out.index + pd.Timedelta(hours=off)).hour
    p = S.load(alias)
    q = pd.Series(_quiet_mask(p), index=p.index).resample("30min").mean()
    out["fasting"] = q.reindex(out.index).fillna(0).to_numpy() >= 0.99
    out.to_pickle(OUTD / f"{alias}.pkl")
    x = out.ice
    z = (x - x.mean()) / x.std()
    return {"alias": alias, "hours": len(out) / 2, "mean": x.mean(), "median": x.median(), "sd": x.std(),
            "iqr": x.quantile(.75) - x.quantile(.25), "p05": x.quantile(.05), "p95": x.quantile(.95),
            "p99": x.quantile(.99), "below0": (x < 0).mean(), "skew": (z ** 3).mean(), "exkurt": (z ** 4).mean() - 3,
            "fast_median": x[out.fasting].median(), "fed_median": x[~out.fasting].median(),
            "fasting_share": out.fasting.mean(), "ia_mean": out.ia.mean(), "v_mean": out.v.mean()}


if __name__ == "__main__":
    OUTD.mkdir(exist_ok=True)
    est = pd.read_csv(S.OUT / "ice" / "isf_estimate.csv").dropna(subset=["isf_est"])
    S.datasets()
    with Pool(8) as p:
        r = pd.DataFrame(p.map(build, list(est.alias)))
    r.to_csv(S.OUT / "ice" / "clean30_person.csv", index=False)
    pd.set_option("display.width", 200)
    print(r.drop(columns="alias").describe(percentiles=[.1, .5, .9]).T[["10%", "50%", "90%"]].round(2).to_string())
