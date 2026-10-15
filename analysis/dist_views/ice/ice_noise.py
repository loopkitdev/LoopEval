#!/usr/bin/env python3
"""How much of ICE is sensor noise, as a function of the averaging window.

Over a window of W minutes, ICE's glucose term is (bg_end - bg_start) / W: only
the two END readings carry sensor error, so white measurement noise of SD
sigma_meas contributes SD sqrt(2) * sigma_meas / W (x60 for per hour), however
many readings lie between. Insulin activity is modelled and carries none.
So noise falls as 1/W while real ICE varies much more slowly.

Per person, on clean intervals only (on cadence, no flag), for W in WINDOWS:
  sd_ice(W)     SD of ICE over non-overlapping W-minute blocks
  sd_noise(W)   sqrt(2) * sigma_meas / W * 60, sigma_meas from wholerecord.csv
                (the structure-function intercept of the person's raw stream)
  noise_share   sd_noise^2 / sd_ice^2
Also the lag-1 autocorrelation of ICE at the native cadence: white noise in a
difference gives -0.5, real ICE gives near +1, so the observed value is a
second, model-free reading of how noisy the native-cadence series is.

Output: ice/noise.csv (per person x window)
"""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_raw import FLAGS  # noqa

WINDOWS = (5, 10, 15, 30, 60, 120)


def f(args):
    alias, sigma = args
    d = pd.read_pickle(S.OUT / "ice" / "raw" / f"{alias}.pkl")
    cad = float(d.cadence.iloc[0])
    good = (d.on_cadence & ~d[FLAGS].any(axis=1)).to_numpy()
    run = np.cumsum(~good)
    rows = []
    lag1 = []
    for W in WINDOWS:
        n = int(round(W / cad))
        if n < 1:
            continue
        vals = []
        for _, r in d[good].groupby(run[good]):
            k = len(r) // n
            if k == 0:
                continue
            dbg = (r.bg1 - r.bg0).to_numpy()[:k * n].reshape(k, n).sum(1)
            act = (r.ia * r.dt).to_numpy()[:k * n].reshape(k, n).sum(1)
            T = r.dt.to_numpy()[:k * n].reshape(k, n).sum(1)
            vals.append((dbg * 60 + act) / T)
            if W == WINDOWS[0] and len(r) > 3:
                x = r.ice.to_numpy()
                lag1.append((x[1:] - x.mean(), x[:-1] - x.mean()))
        v = np.concatenate(vals) if vals else np.array([])
        sd_noise = np.sqrt(2) * sigma / (n * cad) * 60
        rows.append({"alias": alias, "W": n * cad, "n_blocks": len(v), "sd_ice": v.std(),
                     "mean_ice": v.mean(), "sd_noise": sd_noise,
                     "noise_share": sd_noise ** 2 / v.var() if len(v) else np.nan,
                     "p01": np.percentile(v, 1) if len(v) else np.nan,
                     "p99": np.percentile(v, 99) if len(v) else np.nan,
                     "below0": (v < 0).mean() if len(v) else np.nan})
    # lag-1 at native cadence
    x1 = np.concatenate([a for a, b in lag1]); x0 = np.concatenate([b for a, b in lag1])
    r1 = float(np.corrcoef(x1, x0)[0, 1])
    for r in rows:
        r["lag1_native"] = r1
        r["cadence"] = cad
        r["sigma_meas"] = sigma
    return rows


if __name__ == "__main__":
    est = pd.read_csv(S.OUT / "ice" / "isf_estimate.csv").dropna(subset=["isf_est"])
    wr = pd.read_csv(S.OUT / "wholerecord.csv")
    wr = wr.groupby("alias").sigma_meas.median() if "block" in wr else wr.set_index("alias").sigma_meas
    args = [(a, float(wr.get(a, np.nan))) for a in est.alias]
    miss = [a for a, s in args if not np.isfinite(s)]
    assert not miss, f"no sigma_meas for {miss}"            # lesson 22: no silent default
    with Pool(8) as p:
        d = pd.DataFrame([r for rows in p.map(f, args) for r in rows])
    d = d.merge(S.cohort()[["alias", "sensor"]], on="alias")
    d.to_csv(S.OUT / "ice" / "noise.csv", index=False)
    pd.set_option("display.width", 200)
    t = d.groupby("W").agg(sd_ice=("sd_ice", "median"), sd_noise=("sd_noise", "median"),
                           noise_share=("noise_share", "median"),
                           share_p90=("noise_share", lambda x: x.quantile(.9)),
                           p01=("p01", "median"), p99=("p99", "median"), below0=("below0", "median"))
    print(t.round(3).to_string())
    one = d[d.W == 5]
    print("\nlag-1 of native-cadence ICE: median %.2f (p10 %.2f, p90 %.2f)" % tuple(one.lag1_native.quantile([.5, .1, .9])))
    print(one.groupby("sensor").agg(people=("alias", "size"), sigma=("sigma_meas", "median"),
                                    noise_share_5=("noise_share", "median"), lag1=("lag1_native", "median")).round(3))
    print(d[d.W == 30].groupby("sensor").noise_share.median().round(3).to_dict())
