#!/usr/bin/env python3
"""Whole-record statistics, one row per person — the source of the doc's ledger.

The same feature set as the weekly blocks in view 19, computed over each
person's entire usable record instead of per week. Weekly blocks answer "is
this a trait?"; this answers "what is this person's value?", which is what the
per-person table at the foot of the document reports.

Every process statistic here comes from raw samples at the sensor's own cadence
(`style.raw_runs`), never from the interpolated 5-minute panel, and every record
is trimmed to its usable window first (`style.clip_window`).
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S                                    # noqa: E402
from loopeval_analysis import traits as T            # noqa: E402
from loopeval_analysis import dists as D             # noqa: E402

COHORT = Path("~/.loop-eval/trait-cohort").expanduser()
OUT = S.OUT


def series_for(alias: str) -> pd.Series | None:
    """The person's glucose, from the full export when we have it."""
    try:
        ds = S.datasets()[alias]
        return S.clip_window(alias, D._load_glucose(ds.glucose_path))
    except Exception:                                # noqa: BLE001
        f = COHORT / f"{alias}.pkl"
        if f.exists():
            return S.clip_window(alias, pd.read_pickle(f)["bg"])
    return None


def main() -> int:
    warnings.filterwarnings("ignore")
    aliases = sorted(set(S.datasets()) |
                     {f.stem for f in COHORT.glob("p*.pkl")})
    rows = []
    for a in aliases:
        bg = series_for(a)
        if bg is None or len(bg) < 5000:
            print(f"  {a:<6} skipped (no usable glucose)")
            continue
        span = bg.index.max() - bg.index.min()
        b = T.block_features(bg, block=f"{span.days + 2}D")
        if b.empty:
            print(f"  {a:<6} skipped (no complete block)")
            continue
        r = b.iloc[b["n"].to_numpy().argmax()].to_dict()
        r["alias"] = a
        r["days"] = span.days
        rows.append(r)
    W = pd.DataFrame(rows)
    co = S.cohort()
    W = W.merge(co[["alias", "archetype"]].rename(columns={"archetype": "grp"}),
                on="alias", how="left")
    W.to_csv(OUT / "wholerecord.csv", index=False)

    # The document's per-person ledger, derived entirely from the above. The
    # noise share is the fraction of one step's variance that is sensor noise:
    # two independent readings enter each difference, hence 2 sigma^2.
    M = pd.DataFrame({
        "alias": W["alias"],
        "tir": W["tir"],
        "lam": W["boxcox_lambda"],
        "sd_over_mad": W["sd_over_mad"],
        "sigma": W["sigma_meas"],
        "noise_share": 2 * W["sigma_meas"] ** 2 / W["v_sd"] ** 2,
        "H_short": W["hurst_short"],
        "H_long": W["hurst_long"],
        "zero_x": W["acf_zero_min"],
        "betw_day": W["between_day_frac"],
    }).merge(co[["alias", "ia_sched_share"]], on="alias", how="left")
    M.sort_values("tir", ascending=False).to_csv(OUT / "merged.csv", index=False)
    print(f"\n{len(W)} people -> {OUT/'wholerecord.csv'}")
    print(W[["sd_over_mad", "v_sd", "hurst_short", "hurst_long",
             "sigma_meas", "boxcox_lambda"]].describe().loc[
                 ["min", "50%", "max"]].round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
