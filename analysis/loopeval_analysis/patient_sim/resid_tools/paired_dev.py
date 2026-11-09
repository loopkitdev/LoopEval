"""The PAIRED per-person instrument (L 610), which the cohort score cannot see: each twin against ITS OWN donor.

The cohort score compares a median of 112 sampled twins with a median of the donors, so it carries the full
trait-draw variance — between-draw sd 2.19 for TIR, 0.358 for t70, 1.51 U/day for TDD (L 609), which is why
resolving a 1-point TIR effect would need ~20 draws. `twin.csv`'s `med_diff` is the median of (twin − its own
donor) and removes that variance by construction.

The headline is the sum of |med_diff| over the five outcome rows, the same definition L 610 used to show rf2 at
2.28 against ov0's 5.36 where the cohort score called them level. Also prints each row's Spearman rho, which is
the per-person RANKING (does the model put the right people in the right order).

    python paired_dev.py <run> [...]
"""
import sys, numpy as np, pandas as pd
from pathlib import Path

ROWS = ["tir", "bg_mean", "t70", "t54", "tdd"]

print(f"{'arm':>12} {'SUM|dev|':>9} " + " ".join(f"{r:>9}" for r in ROWS)
      + "   | " + " ".join(f"rho_{r:<6}" for r in ROWS))
for run in sys.argv[1:]:
    f = Path(run) / "twin.csv"
    if not f.exists():
        print(f"{Path(run).name:>12}   no twin.csv (validate step not run)")
        continue
    D = pd.read_csv(f).set_index("stat")
    dev, rho, miss = [], [], []
    for r in ROWS:
        if r in D.index:
            dev.append(abs(float(D.med_diff[r]))); rho.append(float(D.spearman[r]))
        else:
            dev.append(np.nan); rho.append(np.nan); miss.append(r)
    tot = np.nansum(dev)
    print(f"{Path(run).name:>12} {tot:>9.3f} " + " ".join(f"{d:>9.3f}" for d in dev)
          + "   | " + " ".join(f"{x:>10.3f}" for x in rho)
          + ("   missing: " + ",".join(miss) if miss else ""))
print("\nLower SUM|dev| is better; it is in each row's own units, so it is dominated by TDD and TIR.")
print("rho is the per-person ranking: higher is better, and it is independent of the deviations.")
