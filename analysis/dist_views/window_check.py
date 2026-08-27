#!/usr/bin/env python3
"""Does the trait/state ranking survive restriction to one common window?

The cohort is not window-uniform: most donors share a single pull window, while
the individually-validated datasets span windows of their own lengths, and one
record is cut short because it interleaves two sensors. Record length is part of
a tail statistic, so a ranking computed across mixed windows could in principle
be a ranking of window lengths. This re-runs the intraclass correlations on the
uniform-window subset alone and reports how far the answer moves.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S                                    # noqa: E402
from loopeval_analysis import traits as T            # noqa: E402

UNIFORM = ("2026-04-01", "2026-07-24")


def main() -> int:
    F = pd.read_pickle(S.OUT / "trait_blocks.pkl")
    W = pd.read_csv(S.OUT / "wholerecord.csv").set_index("alias")["days"]
    # A person is window-uniform when they are a wide-cohort donor whose record
    # was not trimmed: the wide pull spans ~114 days, the others are shorter.
    uniform = [a for a in F.alias.unique()
               if a.startswith("p") and W.get(a, 0) >= 100]
    other = sorted(set(F.alias.unique()) - set(uniform))
    print(f"uniform-window people: {len(uniform)} | other windows: {len(other)} -> {other}")

    I_all = pd.read_csv(S.OUT / "trait_icc.csv").set_index("feature")["icc"]
    feats = [f for f in I_all.index if np.isfinite(I_all[f])]
    I_uni = T.icc_table(F[F.alias.isin(uniform)], feats).set_index("feature")["icc"]

    J = pd.DataFrame({"all": I_all, "uniform": I_uni}).dropna()
    J["delta"] = (J["uniform"] - J["all"]).abs()
    J.sort_values("all", ascending=False).to_csv(S.OUT / "trait_icc_widecheck.csv")
    rho = spearmanr(J["all"], J["uniform"]).statistic
    print(f"\nfeatures compared: {len(J)}")
    print(f"largest |ICC shift|: {J.delta.max():.3f} ({J.delta.idxmax()})")
    print(f"median |ICC shift|:  {J.delta.median():.3f}")
    print(f"rank correlation:    {rho:.3f}")
    print(J.sort_values("delta", ascending=False).head(5).round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
