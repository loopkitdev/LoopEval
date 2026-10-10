#!/usr/bin/env python3
"""Does each flag mark ICE that actually looks different? For every flag,
compare 30-min-scale ICE inside flagged stretches with the same person's clean
ICE: median shift and SD ratio, paired across people (median of per-person
values, people with >= 50 flagged intervals). Native-cadence intervals are
smoothed by a centred 6-interval mean so noise does not dominate."""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_raw import FLAGS  # noqa


def f(a):
    d = pd.read_pickle(S.OUT / "ice" / "raw" / f"{a}.pkl")
    d = d[d.on_cadence].copy()
    n = max(int(round(30 / d.cadence.iloc[0])), 1)
    d["ice30"] = d.ice.rolling(n, center=True, min_periods=n).mean()
    clean = d[~d[FLAGS].any(axis=1)].ice30.dropna()
    out = []
    for fl in FLAGS:
        x = d.loc[d[fl], "ice30"].dropna()
        if len(x) >= 50:
            out.append({"alias": a, "flag": fl, "n": len(x), "shift": x.median() - clean.median(),
                        "sd_ratio": x.std() / clean.std(), "below0": (x < 0).mean() - (clean < 0).mean()})
    return out


if __name__ == "__main__":
    est = pd.read_csv(S.OUT / "ice" / "isf_estimate.csv").dropna(subset=["isf_est"])
    with Pool(8) as p:
        d = pd.DataFrame([r for rows in p.map(f, list(est.alias)) for r in rows])
    d.to_csv(S.OUT / "ice" / "flag_effects.csv", index=False)
    print(d.groupby("flag").agg(people=("alias", "size"), median_shift=("shift", "median"),
                                sd_ratio=("sd_ratio", "median"), below0_extra=("below0", "median")).round(2).to_string())
