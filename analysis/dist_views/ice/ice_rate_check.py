#!/usr/bin/env python3
"""How common are the two extreme patterns the flags miss, and on which sensor?

  fast       30-min glucose change faster than 4 mg/dL/min either way
             (240 mg/dL/hr) — beyond what CGM trend arrows even encode
  no_effect  insulin action above 400 mg/dL/hr (the ISF-scaled absorption)
             while glucose moves less than 60 mg/dL/hr either way for 30 min
Computed on the same unflagged 30-min windows as ice_extremes.py.
"""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_extremes import windows  # noqa


def f(a):
    w = windows(a)
    return {"alias": a, "n": len(w),
            "fall_fast": (w.v < -240).sum(), "rise_fast": (w.v > 240).sum(),
            "no_effect": ((w.ia > 400) & (w.v.abs() < 60)).sum(),
            "fall_from_peak_bg": w.loc[w.v < -240, "bg_start"].median()}


if __name__ == "__main__":
    est = pd.read_csv(S.OUT / "ice" / "isf_estimate.csv").dropna(subset=["isf_est"])
    with Pool(8) as p:
        d = pd.DataFrame(p.map(f, list(est.alias)))
    d = d.merge(S.cohort()[["alias", "sensor", "pump"]], on="alias")
    d.to_csv(S.OUT / "ice" / "rate_check.csv", index=False)
    g = d.groupby("sensor", dropna=False)
    t = pd.DataFrame({"people": g.size(), "windows": g.n.sum(),
                      "fast falls per 1000": 1000 * g.fall_fast.sum() / g.n.sum(),
                      "fast rises per 1000": 1000 * g.rise_fast.sum() / g.n.sum(),
                      "people with any fast fall": g.fall_fast.apply(lambda x: (x > 0).sum()),
                      "no-effect per 1000": 1000 * g.no_effect.sum() / g.n.sum(),
                      "people with no-effect": g.no_effect.apply(lambda x: (x > 0).sum())})
    print(t.round(2).to_string())
    print("\nfast falls: median starting glucose", round(d.fall_from_peak_bg.median()),
          "; top people:", d.nlargest(6, "fall_fast")[["alias", "sensor", "fall_fast", "rise_fast"]].to_dict("records"))
    print("no-effect top:", d.nlargest(6, "no_effect")[["alias", "sensor", "pump", "no_effect"]].to_dict("records"))
