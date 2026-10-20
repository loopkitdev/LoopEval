"""Sensor variants scored on the donors' CGM statistics: re-sense each twin's saved TRUE glucose (a cohort run) with a
variant of its sensor family and compute eda's per-block statistics with the same code as validate.py, then compare
with the donors' 13-day blocks (median KS p over draws of one block per donor, LESSONS 330). The FDA score
(sensor_fit.score) is printed beside, so a fit to the donors' CGM shape stays inside the sensor's accuracy evidence.

Open loop: Loop does not answer the variant's readings, so read the variant against the `base` row, not against the
cohort run's own compare_pilot.csv.

    python -m loopeval_analysis.patient_sim.sensor_eda <run> <real_pilot_blocks.csv> "Dexcom G6" base sensor_wander=0.5 ...
"""
from __future__ import annotations

import json
import pickle
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from .. import traits as T
from .sensor_fit import parse, run_sensor, score
from .validate import _series

STATS = ["v_sd", "sd_over_mad", "v_kurtosis", "v_skew", "hurst_short", "sigma_meas", "acf_min", "acf_zero_min",
         "vol_cluster_60m", "sigma_disp"]


def _one(a):
    d, family, ov, seed = a
    tr = pickle.load(open(d / "truth.pkl", "rb"))
    meta = json.load(open(d / "meta.json"))
    start = float(np.ceil(meta.get("burn_end", 18 * 60) / 1440.0) * 1440.0)
    t = tr["truth"]
    bg, m = t.bg.to_numpy(), t.m.to_numpy()
    r = run_sensor(bg, family, seed, ov, 10_000 + seed)
    k = (m >= start) & np.isfinite(r)
    cgm = pd.Series(r[k], index=_series(pd.Series(m[k])))
    days = (m.max() - start) / 1440.0
    b = T.block_features(cgm, block=f"{int(days) + 3}D", min_samples=min(1200, int(k.sum() * 0.5)))
    if not len(b): return None
    row = b.iloc[b["n"].to_numpy().argmax()]
    return {s: float(row[s]) for s in STATS}


def people(run: Path, family: str):
    out = []
    for d in sorted(run.glob("v*")):
        if not (d / "truth.pkl").exists(): continue
        if pickle.load(open(d / "person.pkl", "rb")).sensor == family: out.append(d)
    return out


def evaluate(dirs, family, ov, real, ndraw=40, par=15):
    from scipy.stats import ks_2samp
    with Pool(par) as p:
        rows = [r for r in p.map(_one, [(d, family, ov, i) for i, d in enumerate(dirs)]) if r]
    sim = pd.DataFrame(rows)
    rng = np.random.default_rng(0)
    draws = [real.groupby("alias").sample(1, random_state=int(rng.integers(1 << 30))) for _ in range(ndraw)]
    out = {}
    for s in STATS:
        ss = sim[s].dropna()
        out[s] = float(ss.median())
        out["p_" + s] = float(np.median([ks_2samp(dr[s].dropna(), ss).pvalue for dr in draws]))
    return out


def main():
    run, blocks, family, variants = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4:]
    tt = pd.read_csv(Path(blocks).parent / "templates_pilot_logs.csv")[["alias", "sensor"]]
    real = pd.read_csv(blocks).merge(tt, on="alias")
    real = real[real.sensor == family]
    dirs = people(run, family)
    bgs = [pickle.load(open(d / "truth.pkl", "rb"))["truth"].bg.to_numpy() for d in dirs[:20]]
    res = {"donors": {s: float(real[s].median()) for s in STATS}}
    for v in variants:
        r = evaluate(dirs, family, parse(v), real)
        r["matched"] = sum(r["p_" + s] > 0.05 for s in STATS)
        fd = score(bgs, family, parse(v))
        r.update(fda_loss=fd["loss"], pard=fd["pard"])
        res[v] = r
        print(v, "done", flush=True)
    pd.set_option("display.width", 300)
    D = pd.DataFrame(res).T
    cols = [c for s in STATS for c in (s, "p_" + s)] + ["matched", "fda_loss", "pard"]
    print(f"{family}: {len(dirs)} twins, {real.alias.nunique()} donors")
    print(D[[c for c in cols if c in D]].round(3).to_string())


if __name__ == "__main__":
    main()
