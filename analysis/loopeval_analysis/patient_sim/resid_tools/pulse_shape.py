"""Does the donors' carb absorption END more abruptly than the twins'? The post-meal fall / rise ratio needs a
TIME-ASYMMETRIC, non-mean-preserving mechanism (L 575), and every rate-like lever is ruled out. The gut's tail is
first-order (Qsto2 empties exponentially), so its absorption trails off; real gastric emptying is a power-exponential
(Elashoff 1982, exp(-(kt)^beta), beta ~1.5-2) that starts flatter and finishes sharply — which steepens the post-peak
fall WITHOUT lowering the peak, the one shape L 575 asks for.

The labeller gives each pulse a peak and an end, so the decay phase is (dur_h − peak_h). Same labeller on both sides.
    python pulse_shape.py <run> [...]"""
import sys, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path.home() / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L

def show(lab, D, n):
    D = D[(D.size_g >= 20) & (D.dur_h > 0) & (D.peak_h > 0) & (D.dur_h > D.peak_h)]
    if len(D) < 30: return
    dec = D.dur_h - D.peak_h
    print(f"  {lab:>9} n{len(D):6d}  size {D.size_g.median():4.0f} g   peak at {D.peak_h.median()*60:4.0f} min"
          f"   decay phase {dec.median()*60:5.0f} min   decay / peak {(dec / D.peak_h).median():.2f}"
          f"   total {D.dur_h.median()*60:5.0f} min")

don = []
for a in sorted({p.stem for p in (L.ICE_ROOT / "steps").glob("*.parquet")}):
    mp = L.ICE_ROOT / "meals" / f"{a}.parquet"
    if not mp.exists(): continue
    try: M = pd.read_parquet(mp)
    except Exception: continue
    if not {"size_g", "dur_h", "peak_h"}.issubset(M.columns): continue
    don.append(M[["size_g", "dur_h", "peak_h"]])
D = pd.concat(don)
print("labelled pulses >= 20 g; decay phase = end − peak, both sides through the same labeller")
show("donors", D, len(D))
for run in sys.argv[1:]:
    T = []
    for p in sorted(Path(run).glob("v*/meals_labeled.csv")):
        try: m = pd.read_csv(p)
        except Exception: continue
        if {"size_g", "dur_h", "peak_h"}.issubset(m.columns): T.append(m[["size_g", "dur_h", "peak_h"]])
    if T: show(Path(run).name, pd.concat(T), 0)
