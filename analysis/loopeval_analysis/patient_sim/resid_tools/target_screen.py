"""Which row could a SECOND fitted parameter take as its target? L 606's open question.

A fitting target must be both:
  REACHABLE       - body parameters actually move it, or the fit runs to its clip bounds (L 606: that is exactly how
                    `twin_isf_mult` <- TDD failed, widening the ISF spread to [0.70, 1.43] and costing acf_zero_min,
                    circadian_amp and night_cv on all three draws);
  SIGNAL-BEARING  - its value is not dominated by the draw, or the fit chases noise (L 602: t70's draw scatter
                    exceeds its bias, which is why it is a poor target despite being reachable).

Both are measured here from `twin.csv` across arms already on disk, with no new runs:
  reach  = the spread (IQR, and max-min) of the PAIRED deviation across ARMS on one draw. A row many different body
           parameters move has a wide spread; a row none of them move is pinned.
  noise  = the spread of the REFERENCE's own paired deviation across DRAWS. Paired already removes the trait-draw
           variance (L 610), so what is left is how much the row still moves for no reason.
  ratio  = reach / noise. A usable target needs it well above 1: the parameter's leverage must exceed the draw noise.

    python target_screen.py --arms <run> [<run> ...] --ref <ref draw run> [<ref draw run> ...]
"""
import sys, numpy as np, pandas as pd
from pathlib import Path

ROWS = ["tir", "bg_mean", "t70", "t54", "tdd"]
a = sys.argv[1:]
arms = a[a.index("--arms") + 1:a.index("--ref")] if "--arms" in a and "--ref" in a else []
refs = a[a.index("--ref") + 1:] if "--ref" in a else []


def dev(run):
    f = Path(run) / "twin.csv"
    if not f.exists():
        return None
    D = pd.read_csv(f).set_index("stat")
    return {r: float(D.med_diff[r]) for r in ROWS if r in D.index}


A = [d for d in (dev(x) for x in arms) if d]
R = [d for d in (dev(x) for x in refs) if d]
print(f"{len(A)} arms (one draw) for REACH, {len(R)} reference draws for NOISE\n")
print(f"{'row':>9} {'reach IQR':>10} {'reach range':>12} {'noise (ref sd)':>15} {'ratio':>7}  verdict")
for r in ROWS:
    va = np.array([d[r] for d in A if r in d], float)
    vr = np.array([d[r] for d in R if r in d], float)
    if len(va) < 4 or len(vr) < 2:
        print(f"{r:>9}   too few arms/draws")
        continue
    iqr = float(np.percentile(va, 75) - np.percentile(va, 25))
    rng = float(va.max() - va.min())
    sd = float(vr.std(ddof=1))
    ratio = iqr / sd if sd > 0 else np.inf
    v = ("USABLE" if ratio >= 2 else "marginal" if ratio >= 1 else "NOT USABLE")
    print(f"{r:>9} {iqr:>10.3f} {rng:>12.3f} {sd:>15.3f} {ratio:>7.2f}  {v}")
print("\nreach is across ARMS on one draw (how much body parameters move it); noise is the reference's own")
print("paired deviation across DRAWS. A target needs reach >> noise, or the fit is chasing the draw.")
