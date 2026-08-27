#!/usr/bin/env python3
"""Which glucose properties are stable traits of a person — and do they cluster?

Two questions, in order:

  1. TRAIT OR STATE. Split every person's record into weekly blocks, compute each
     feature per block, and take the intraclass correlation: the share of the
     feature's variance that is between people rather than within them. High ICC
     means one measurement of that feature still describes the person months
     later. Low ICC means it describes that week and nothing more.

  2. CLASSES. Take only the trait-like features, reduce, and ask whether people
     fall into groups or spread along a continuum. Both answers are informative
     and the data decides which it is.

Purely descriptive. Nothing here says what to do about any of it.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S                                            # noqa: E402
from loopeval_analysis import traits as T                    # noqa: E402
from loopeval_analysis import dists as D                     # noqa: E402

COHORT = Path(os.path.expanduser("~/.loop-eval/trait-cohort"))
OUT = S.OUT
BLOCK = "7D"

# Features considered. Order is only for readability; ICC decides the verdict.
FEATURES = [
    "bg_mean", "bg_cv", "bg_sd", "bg_skew", "bg_iqr", "boxcox_lambda",
    "tir", "t70", "t180",
    "v_sd", "sd_over_mad", "v_kurtosis", "v_skew",
    "hurst_short", "hurst_long", "sigma_meas", "acf_zero_min", "acf_min",
    "vol_cluster_60m", "sigma_med", "sigma_disp",
    "between_day_frac", "circadian_amp",
]


def load_blocks(include_existing: bool = True) -> pd.DataFrame:
    """Per-(person, week) features for every donor we can reach."""
    frames = []
    for f in sorted(COHORT.glob("p*.pkl")):
        bg = S.clip_window(f.stem, pd.read_pickle(f)["bg"])
        b = T.block_features(bg, block=BLOCK)
        if len(b) >= 4:
            b["alias"] = f.stem
            b["source"] = "tidepool-wide"
            frames.append(b)
    if include_existing:
        try:
            dss = S.datasets()
        except Exception:                                     # noqa: BLE001
            dss = {}
        seen = {f["alias"].iloc[0] for f in frames}
        for alias, ds in dss.items():
            if alias in seen:          # the wide full exports reuse the pkl aliases
                continue
            try:
                bg = S.clip_window(alias, D._load_glucose(ds.glucose_path))
            except Exception:                                 # noqa: BLE001
                continue
            b = T.block_features(bg, block=BLOCK)
            if len(b) >= 4:
                b["alias"] = alias
                b["source"] = "existing-cohort"
                frames.append(b)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def main() -> int:
    F = load_blocks()
    if F.empty:
        print("no blocks — is the cohort cached?")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    F.to_pickle(OUT / "trait_blocks.pkl")
    n_sub = F.alias.nunique()
    per = F.groupby("alias").size()
    print(f"{n_sub} people, {len(F)} person-weeks "
          f"(blocks per person: min {per.min()}, median {int(per.median())}, max {per.max()})")
    print(F.groupby("source").agg(people=("alias", "nunique"),
                                  blocks=("alias", "size")).to_string())

    feats = [c for c in FEATURES if c in F.columns and F[c].notna().sum() > 50]
    I = T.icc_table(F, feats)
    I.to_csv(OUT / "trait_icc.csv", index=False)

    print("\n" + "=" * 78)
    print("TRAIT OR STATE — intraclass correlation over weekly blocks")
    print("  ICC = between-person variance / total variance; 90% CI over people")
    print("=" * 78)
    print(f"{'feature':<20}{'ICC':>7}{'90% CI':>16}{'people':>8}{'weeks':>7}   reading")
    for _, r in I.iterrows():
        if not np.isfinite(r.icc):
            continue
        band = ("TRAIT" if r.lo > 0.6 else
                "trait-ish" if r.icc > 0.5 else
                "mixed" if r.icc > 0.3 else "state")
        print(f"{r.feature:<20}{r.icc:>7.3f}{f'[{r.lo:.2f},{r.hi:.2f}]':>16}"
              f"{r.n_subj:>8}{r.n_obs:>7}   {band}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
