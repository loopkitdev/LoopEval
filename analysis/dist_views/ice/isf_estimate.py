#!/usr/bin/env python3
"""Write the adopted ISF yardstick: one ISF per person, read by every later ICE step.

Definition (published as "An ISF Yardstick", artifact T8Dbp4JLN7EpZ64wttwTdX):
the fasting regression of hourly glucose change on insulin absorbed (60-min
blocks, every step fasting: no announced carbs on board, no user bolus in the
prior 4 h, no disruption), SEs calibrated on alternating weeks, shrunk toward a
measured-fasting-basal rule, levelled by one cohort-wide factor so the cohort
median equals the scheduled median. Computed by isf_basal_prior.py; this script
only selects the adopted column so downstream code reads one name.

Output: ice/isf_estimate.csv  alias, isf_est, isf_sched, weight_own, fb_uhr
"""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa

d = pd.read_csv(S.OUT / "ice" / "isf_basal_prior.csv")
out = pd.DataFrame({"alias": d.alias, "isf_est": d.E_basal_all, "isf_sched": d.A_all,
                    "weight_own": d.w_basal, "fb_uhr": d.fb_all})
co = S.cohort()
missing = set(co.alias) - set(out.dropna(subset=["isf_est"]).alias)
out.to_csv(S.OUT / "ice" / "isf_estimate.csv", index=False)
print(f"wrote {out.isf_est.notna().sum()} estimates; cohort {len(co)}; without an estimate: {sorted(missing)}")
