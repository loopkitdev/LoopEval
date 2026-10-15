#!/usr/bin/env python3
"""Does each person's ICE peak sit at scheduled basal x ISF? (ice/ice_mode_cover.csv)"""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_dist_isf import series, GRID, MULTS  # noqa


def f(a):
    pp = S.load(a); s = series(a)
    out = {"alias": a, "cover": np.nanmedian(pp.basal_sched * pp.isf), "isf": np.nanmedian(pp.isf)}
    for m in MULTS:
        out[f"mode{m}"] = GRID[np.argmax(S.kde(s[m], GRID, bw=8.0))]
    return out


if __name__ == "__main__":
    with Pool(8) as p:
        d = pd.DataFrame(p.map(f, list(S.cohort().alias)))
    d.to_csv(S.OUT / "ice" / "ice_mode_cover.csv", index=False)
    print("cover median", round(d.cover.median(), 1))
    for m in MULTS:
        r = d[f"mode{m}"] / d.cover
        print(f"x{m}: peak median {d[f'mode{m}'].median():.0f}  peak/cover median {r.median():.2f} "
              f"(p10-p90 {r.quantile(.1):.2f}-{r.quantile(.9):.2f})")
    print("spearman(peak at x1, cover)", round(d["mode1.0"].corr(d.cover, method="spearman"), 2))
