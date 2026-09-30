#!/usr/bin/env python3
"""Per-person settings table: ISF, the rule-of-X it implies, and the max-basal cap.

Builds isf_rules.csv, the base table the settings / aggressiveness exploration
(settings_explore/) adds columns to. One row per person in the modelling cohort.

  isf, cr, basal, target   time-weighted means from the weekly blocks
  tdd_use                  delivered total daily dose (delivery.csv), falling back
                           to the weekly-block TDD
  k1800 = ISF x TDD        the "rule of X" constant that reproduces this ISF
  k500  = CR x TDD         the carb-ratio analogue
  max_basal, headroom      end-of-window max basal, and max / scheduled basal
  cap_avg                  max basal / (TDD/24): the cap against average delivery
  at_max_when_high         % of time above 180 spent pinned at the cap
  cap_cover                share of a +100 mg/dL correction the cap leaves room for,
                           using Loop's ~30-minute temp: (max - sched) / ((100/ISF)/0.5)

Run after delivery.py, age.csv (pull_age.py) and the weekly trait blocks exist.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S
from loopeval_analysis import dists as D

def main() -> int:
    B = pd.read_pickle(S.OUT/"trait_blocks_insulin.pkl")
    per = B.groupby("alias")[["isf_mean","cr_mean","basal_sched_mean","target_lo_mean","tdd",
                              "carb_g_day","manual_bolus_day","auto_frac_u"]].mean()
    co = S.cohort().set_index("alias")
    dl = pd.read_csv(S.OUT/"delivery.csv").set_index("alias")
    ag = pd.read_csv(S.OUT/"age.csv").set_index("alias")
    d = (per.join(co[["tir","t70","t54","t180","bg_mean","bg_cv","pump","sensor","strategy","archetype","stratum"]])
            .join(dl[["tdd","tdd_cv"]], rsuffix="_del").join(ag[["age_years"]]))
    d = d.rename(columns={"isf_mean":"isf","cr_mean":"cr","basal_sched_mean":"basal",
                          "target_lo_mean":"target","tdd_del":"tdd_measured"})
    d["tdd_use"] = d["tdd_measured"].fillna(d["tdd"])
    d["k1800"] = d.isf * d.tdd_use
    d["k500"] = d.cr * d.tdd_use
    d["basal_pct"] = 100 * d.basal * 24 / d.tdd_use
    DS = S.datasets(); rows = []
    for a in d.index:
        try:
            th = json.load(open(DS[a].therapy_path)); c = D.clean(S.load(a))
        except Exception:
            continue
        mb = th.get("maxBasalRate")
        if mb is None:
            continue
        eff, sch, bg = c.basal_eff.to_numpy(), c.basal_sched.to_numpy(), c.bg.to_numpy()
        hi = bg > 180
        rows.append(dict(alias=a, max_basal=float(mb), max_bolus=th.get("maxBolus"),
                         headroom=float(mb)/np.nanmean(sch),
                         at_max_when_high=100*np.mean(eff[hi] >= mb*0.99) if hi.sum() > 100 else np.nan))
    d = d.join(pd.DataFrame(rows).set_index("alias"))
    d["cap_avg"] = d.max_basal / (d.tdd_use/24)
    d["cap_cover"] = (d.max_basal - d.basal) / ((100/d.isf)/0.5)
    d.to_csv(S.OUT/"isf_rules.csv")
    print(f"isf_rules.csv - {len(d)} people; rule-of-X median {d.k1800.median():.0f}, "
          f"max basal known for {d.max_basal.notna().sum()}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
