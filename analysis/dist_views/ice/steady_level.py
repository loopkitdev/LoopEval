#!/usr/bin/env python3
"""Within-person: does the steady-state absorbed rate depend on the glucose level
it is steady at? Windows as steady_basal.main but with a 70-250 band."""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from steady_basal import windows  # noqa

EDGES = [70, 100, 120, 140, 160, 250]


def f(a):
    w = windows(S.load(a), hours=3, flat=10, band=(70, 250))
    w = w[w.sched_uhr > 0]
    w["r"] = w.abs_uhr / w.sched_uhr
    w["band"] = pd.cut(w.bg, EDGES)
    out = {"alias": a}
    for b, g in w.groupby("band", observed=True):
        if len(g) >= 8:
            out[str(b)] = g.r.median()
    if len(w) >= 30:
        x, y = w.bg.to_numpy(), np.log(w.r.to_numpy())
        out["slope_per_10"] = np.polyfit(x, y, 1)[0] * 10
    return out


if __name__ == "__main__":
    with Pool(8) as p:
        d = pd.DataFrame(p.map(f, list(S.cohort().alias)))
    d.to_csv(S.OUT / "ice" / "steady_level.csv", index=False)
    cols = [c for c in d.columns if c.startswith("(")]
    print("median ratio by band (people):")
    for c in cols:
        print(f"  {c}: {d[c].median():.2f}  (n={d[c].count()})")
    # paired: people with both lowest two bands and 140-160
    for lo, hi in (("(100, 120]", "(140, 160]"), ("(70, 100]", "(120, 140]")):
        m = d[[lo, hi]].dropna()
        print(f"paired {lo} -> {hi}: n={len(m)}, median within-person change x{(m[hi]/m[lo]).median():.2f}")
    s = d.slope_per_10.dropna()
    print(f"within-person log-slope per +10 mg/dL: median {s.median():.3f} (x{np.exp(s.median()):.3f}), "
          f"positive in {(s > 0).mean():.0%} of {len(s)}")
