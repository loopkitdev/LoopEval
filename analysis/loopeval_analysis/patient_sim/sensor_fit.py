"""Offline sensor calibration: run sensor variants over simulated TRUE glucose and score them against
sensor-only targets (FDA iCGM tables, two-sensor precision), so the sensor never absorbs missing
physiology (evidence/08; LESSONS 31).

Targets (G7 adult, K213919): MARD / bias by comparator range and by CGM range, precision PARD 8.9%
(two sensors, same person and site), MAD elasticity 0.69.

    python -m loopeval_analysis.patient_sim.sensor_fit <cohort-root> "Dexcom G7" key=value[,key=value] ...
Each positional variant is a comma-separated override set (sensor_sigma, sensor_a1, sensor_a2,
sensor_hetero, sensor_floor, sensor_a0); "base" = the family as defined.
"""
from __future__ import annotations

import glob
import pickle
import sys

import numpy as np
import pandas as pd

from .sensor import Sensor
from .sensor_check import EDGES, LABELS

# per family: (comparator-binned {range: (bias, MARD)}, CGM-binned {...}, two-sensor PARD %) — evidence/08 §1.4
TARGETS = {
    "Dexcom G7": ({"<54": (4.0, 14.0), "54-69": (1.1, 10.7), "70-180": (1.1, 8.6), "181-250": (-1.9, 7.4), ">250": (-6.6, 6.4)},
                  {"<54": (-9.3, 16.0), "54-69": (-2.3, 9.1)}, 8.9),                         # K213919 adults
    "Dexcom G6": ({}, {"<54": (-6.9, 13.8), "54-69": (-0.5, 11.5), "70-180": (-2.8, 10.9), "181-250": (-10.0, 9.3),
                       ">250": (-3.8, 7.1)}, 9.0),                                              # DEN170088 / K200876 adults
    "Libre 3": ({"<54": (7.4, 15.5), "54-69": (1.4, 10.3), "70-180": (-4.5, 9.7), "181-250": (-7.3, 7.5), ">250": (-11.5, 6.9)},
                {"<54": (-6.7, 14.2)}, 6.8),                                                     # K212132 adults
}
FDA_G7_TRUE, FDA_G7_CGM, PARD_G7 = TARGETS["Dexcom G7"]


def truths(root: str, n: int = 30) -> list[np.ndarray]:
    out = []
    for d in sorted(glob.glob(root + "/v0*"))[:n]:
        T = pickle.load(open(d + "/truth.pkl", "rb"))["truth"]
        out.append(T.bg.to_numpy())
    return out


def run_sensor(bg: np.ndarray, family: str, seed: int, ov: dict, common_seed: int = 0) -> np.ndarray:
    s = Sensor(family, np.random.default_rng(seed), compression_rate=0.0, overrides=ov,
               common_rng=np.random.default_rng(common_seed))
    out = np.full(len(bg), np.nan)
    for m, g in enumerate(bg):
        r = s.step(float(m), float(g))
        if r: out[m] = r
    return out


def score(bgs, family, ov, seed0=0) -> dict:
    rows, prec, steps = [], [], []
    for i, bg in enumerate(bgs):
        # two sensors on one person share the common (interstitial) error, as in the FDA precision arm
        a = run_sensor(bg, family, seed0 + 2 * i, ov, 10_000 + i); b = run_sensor(bg, family, seed0 + 2 * i + 1, ov, 10_000 + i)
        m = np.arange(len(bg))
        day = (m >= 1800) & ((m % 1440) >= 480) & ((m % 1440) < 1200) & (m % 15 == 0)
        for arr in (a,):
            k = day & np.isfinite(arr) & (arr > 39) & (arr < 401)
            rows.append(pd.DataFrame(dict(cgm=arr[k], true=bg[k])))
        g5 = a[(m >= 1800) & (m % 5 == int(np.nanargmax(np.isfinite(a[1800:1810]))) % 5)]
        steps.append(np.diff(g5)[np.isfinite(np.diff(g5))])
        k = day & np.isfinite(a) & np.isfinite(b) & (a > 39) & (b > 39) & (a < 401) & (b < 401)
        prec.append(np.abs(a[k] - b[k]) / ((a[k] + b[k]) / 2))
    p = pd.concat(rows); p["err"] = p.cgm - p.true
    out = {}
    t_true, t_cgm, pard_t = TARGETS[family]
    for by, ref in (("true", t_true), ("cgm", t_cgm)):
        p["bin"] = pd.cut(p[by], EDGES, labels=LABELS, right=False)
        for b, q in p.groupby("bin", observed=True):
            if b in ref:
                out[f"{by}{b}_bias"] = q.err.mean(); out[f"{by}{b}_mard"] = 100 * (q.err.abs() / q.true).mean()
    p["bin"] = pd.cut(p["true"], EDGES, labels=LABELS, right=False)
    mid = {"54-69": 62, "70-180": 125, "181-250": 215, ">250": 310}
    mad = p.groupby("bin", observed=True).err.apply(lambda e: e.abs().mean())
    out["elast"] = np.polyfit(np.log([mid[b] for b in mid if b in mad]), np.log([mad[b] for b in mid if b in mad]), 1)[0]
    out["pard"] = 100 * np.mean(np.concatenate(prec))
    st = np.concatenate(steps)
    out["step_sd"] = st.std(); out["jumps12_per1000"] = 1000 * np.mean(np.abs(st) >= 12)
    # loss: squared relative misses against the FDA cells (MARD as ratio, bias in units of 5 mg/dL)
    loss = sum(np.log(out[f"true{b}_mard"] / r[1]) ** 2 + ((out[f"true{b}_bias"] - r[0]) / 5) ** 2 for b, r in t_true.items() if f"true{b}_mard" in out)
    loss += sum(np.log(out[f"cgm{b}_mard"] / r[1]) ** 2 + ((out[f"cgm{b}_bias"] - r[0]) / 5) ** 2 for b, r in t_cgm.items() if f"cgm{b}_mard" in out)
    loss += np.log(out["pard"] / pard_t) ** 2 + ((out["elast"] - 0.7) / 0.1) ** 2
    out["loss"] = loss
    return out


def parse(v: str) -> dict:
    if v == "base": return {}
    return {k: float(x) for k, x in (kv.split("=") for kv in v.split(","))}


def main():
    root, family, variants = sys.argv[1], sys.argv[2], sys.argv[3:]
    bgs = truths(root)
    res = {v: score(bgs, family, parse(v)) for v in variants}
    pd.set_option("display.width", 250)
    tt, tc, pt = TARGETS[family]
    ref = {f"true{b}_bias": r[0] for b, r in tt.items()} | {f"true{b}_mard": r[1] for b, r in tt.items()} \
        | {f"cgm{b}_bias": r[0] for b, r in tc.items()} | {f"cgm{b}_mard": r[1] for b, r in tc.items()} \
        | {"elast": 0.7, "pard": pt, "loss": 0.0, "step_sd": np.nan, "jumps12_per1000": np.nan}
    print(pd.DataFrame(res | {"FDA": ref}).round(2).to_string())


if __name__ == "__main__":
    main()
