"""Simulated activity episodes scored the way the free-living literature reports them (evidence/10 §7.4):
raw ΔCGM over each episode by starting CGM and by Loop's IOB at the start (Dhaliwal 2025, T1DEXI), and the
share of episodes with a low (CGM < 70 for >= 15 min) during them, by duration.

    python -m loopeval_analysis.patient_sim.activity_check <cohort-root>
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .world import EPOCH


def episodes(run: Path) -> pd.DataFrame:
    tr = pickle.load(open(run / "truth.pkl", "rb"))
    cgm = tr["cgm"].dropna().sort_index()
    b = pd.DataFrame(tr["behavior"], columns=["m", "k", "g", "x"])
    w = b[b.k.isin(["walk", "exercise"])]
    t = json.load(open(run / "trace.json"))
    p = pd.DataFrame(t["predictions"])
    pm = ((pd.to_datetime(p.t) - EPOCH).dt.total_seconds() / 60).to_numpy()
    iob = p.candidateIOB.astype(float).to_numpy()
    rows = []
    for _, e in w.iterrows():
        s, dur = float(e.m), float(e.g)
        if s < 1800: continue
        seg = cgm[(cgm.index >= s - 5) & (cgm.index <= s + dur + 5)]
        if len(seg) < 3: continue
        k = np.searchsorted(pm, s) - 1
        low = (seg < 70).to_numpy(); run_len = 0; hypo = False
        for x in low:
            run_len = run_len + 5 if x else 0
            if run_len >= 15: hypo = True
        rows.append(dict(kind=e.k, dur=dur, g0=float(seg.iloc[0]), dcgm=float(seg.iloc[-1] - seg.iloc[0]),
                         iob=float(iob[k]) if k >= 0 else np.nan, hypo=hypo))
    return pd.DataFrame(rows)


def main():
    root = Path(sys.argv[1])
    E = pd.concat([episodes(r) for r in sorted(root.glob("v0*")) if (r / "trace.json").exists()])
    W = E[E.kind == "walk"]
    pd.set_option("display.width", 200)
    print("everyday episodes:", len(W), " median dur", W.dur.median(), " median dCGM", W.dcgm.median(), "(Dhaliwal walking −18)")
    print("by start CGM (Dhaliwal raw: 100–150 −11, 150–200 −33, 200–250 −52):")
    print(W.groupby(pd.cut(W.g0, [50, 100, 150, 200, 250, 400]), observed=True).dcgm.agg(["size", "median"]).round(1).to_string())
    print("by IOB at start (Dhaliwal: <1 U ~0..+6, >=3 U −32):")
    print(W.groupby(pd.cut(W.iob, [-5, 1, 2, 3, 30]), observed=True).dcgm.agg(["size", "median"]).round(1).to_string())
    print("low during episode by duration (Dhaliwal 15–30 ~3%, 30–60 ~6%, 60–120 ~12%):")
    print((100 * W.groupby(pd.cut(W.dur, [0, 15, 30, 60, 120, 200]), observed=True).hypo.mean()).round(1).to_string())
    print("low during episode by start CGM (Dhaliwal 50–100 ~21%, 100–150 ~4%):")
    print((100 * W.groupby(pd.cut(W.g0, [50, 100, 150, 400]), observed=True).hypo.mean()).round(1).to_string())


if __name__ == "__main__":
    main()
