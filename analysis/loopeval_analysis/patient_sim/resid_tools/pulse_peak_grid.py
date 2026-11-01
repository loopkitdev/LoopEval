"""Is the scored `pulse_peak_h` row measuring the body, or the labeller's fitting grid?

`peak_h` is not a measured peak time: `ice_gen.meals.fit_shapes` fits each pulse's lognormal over a 24-cell log
grid (`FIT_MODES`), so every pulse's peak_h is one of 24 values, spaced only 3.4-5.9 min apart near the cohort
median. The twins' scored median is **0.622 h for every arm tested** (order 2, order 3, both load cuts) and 0.622
is exactly grid cell 10 - which is what a quantized median looks like when the underlying shift is under one cell.

This prints, for each side, the median (what is scored), the MEAN (not pinned by one cell), and the share of
pulses in each cell. A real difference shows in the mean and the cell mix; a quantization floor shows as the mean
moving while the median does not.

Non-rescue pulses only, as `lifestats.life_stats` scores them.
    python pulse_peak_grid.py <run> [...]
"""
import sys, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path.home() / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L

MODES = np.exp(np.linspace(np.log(10 / 60), np.log(4), 24))      # ice_gen.meals.FIT_MODES
CELLS = MODES - 2.5 / 60                                          # what peak_h can take


def cell_of(v):
    return np.argmin(np.abs(CELLS[None, :] - np.asarray(v, float)[:, None]), axis=1)


def show(lab, pk, npeople):
    pk = np.asarray(pk, float)
    pk = pk[np.isfinite(pk)]
    c = cell_of(pk)
    mix = "".join(f" {k}:{(c == k).mean() * 100:.0f}%" for k in range(7, 15) if (c == k).mean() >= 0.03)
    print(f"  {lab:>12} {npeople:>4} people {len(pk):>6} pulses   median {np.median(pk):.3f} h"
          f" (cell {int(np.argmin(abs(CELLS - np.median(pk))))})   MEAN {pk.mean():.3f} h"
          f"   sd {pk.std():.3f}\n               cells{mix}")


print(f"grid cells 7-14, hours: {np.round(CELLS[7:15], 3)}")
print(f"spacing there, minutes: {np.round(np.diff(CELLS[7:15] * 60), 1)}\n")

# donors, same labeller output the scorer reads
rows, n = [], 0
for p in sorted((L.ICE_ROOT / "meals").glob("*.parquet")):
    try:
        d = pd.read_parquet(p, columns=["peak_h", "rescue"])
    except Exception:
        continue
    d = d[~d.rescue.astype(bool)]
    if d.empty:
        continue
    rows.append(d.peak_h.to_numpy(float)); n += 1
show("donors", np.concatenate(rows), n)
per = [np.median(r) for r in rows]
print(f"               per-person medians: median {np.median(per):.3f}  mean {np.mean(per):.3f}"
      f"  (the scored row is the cross-person median)")

for run in sys.argv[1:]:
    rows, n = [], 0
    for f in sorted(Path(run).glob("v*/meals_labeled.csv")):
        try:
            d = pd.read_csv(f, usecols=["peak_h", "rescue"])
        except Exception:
            continue
        d = d[~d.rescue.astype(bool)]
        if d.empty:
            continue
        rows.append(d.peak_h.to_numpy(float)); n += 1
    if not rows:
        print(f"  {Path(run).name:>12}   no meals_labeled.csv")
        continue
    show(Path(run).name, np.concatenate(rows), n)
    per = [np.median(r) for r in rows]
    print(f"               per-person medians: median {np.median(per):.3f}  mean {np.mean(per):.3f}")
