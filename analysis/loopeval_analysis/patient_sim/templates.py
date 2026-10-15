"""Person templates: real donors' joint traits, the population a virtual person is drawn from.

A virtual person starts from one real donor's row (jittered), never from independent marginals:
behavior rates are bimodal and traits co-vary (evidence/05 §3 lesson 4), and drawing from people
keeps both. One row per eda-cohort donor, aliases only.

Columns and where each comes from (all eda tables under runs/2026-08-25-distributions/):
  truth      isf_true  = yardstick ISF (ice/isf_estimate.csv `isf_est`; eda lesson 54)
             basal_true = measured fasting insulin rate (ice/isf_estimate.csv `fb_uhr`)
  settings   isf, cr, basal, target, max_basal, max_bolus (isf_rules.csv: the person's schedule,
             time-weighted)
  person     age_years, tdd, strategy, pump, sensor, archetype, carb_g_day (announced),
             manual_bolus_day (isf_rules.csv); carb_entries_per_day, user_boluses_per_day (cohort.csv);
             formulation brand (formulation.csv)
  outcomes   tir, t54, t70, bg_mean, bg_cv (for comparison only — never an input to a person)

Usage:  python -m loopeval_analysis.patient_sim.templates   → writes runs/<date>-additive-templates/templates.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

DIST = "2026-08-25-distributions"


def runs_root() -> Path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "dist_views"))
    import style                                   # noqa: E402  (honours LOOPEVAL_RUNS)
    return Path(style.OUT).parent


def build() -> pd.DataFrame:
    d = runs_root() / DIST
    r = pd.read_csv(d / "isf_rules.csv")
    e = pd.read_csv(d / "ice" / "isf_estimate.csv")[["alias", "isf_est", "fb_uhr"]]
    f = pd.read_csv(d / "formulation.csv")[["alias", "brand", "category"]]
    c = pd.read_csv(d / "cohort.csv")[["alias", "carb_entries_per_day", "user_boluses_per_day",
                                       "auto_boluses_per_day", "t54", "bg_mean"]]
    keep = ["alias", "isf", "cr", "basal", "target", "max_basal", "max_bolus", "tdd", "carb_g_day",
            "manual_bolus_day", "pump", "sensor", "strategy", "archetype", "age_years",
            "tir", "t70", "t180", "bg_cv"]
    t = (r[keep].merge(e, on="alias").merge(c, on="alias", how="left")
         .merge(f, on="alias", how="left"))
    t = t.rename(columns={"isf_est": "isf_true", "fb_uhr": "basal_true", "brand": "insulin_brand"})
    t["insulin_brand"] = t["insulin_brand"].fillna("unknown")
    t = t[(t.isf_true > 0) & (t.basal_true > 0) & (t.tdd > 0)]
    return t.reset_index(drop=True)


def main() -> int:
    t = build()
    out = runs_root() / "2026-10-15-additive-templates"
    out.mkdir(parents=True, exist_ok=True)
    t.to_csv(out / "templates.csv", index=False)
    print(f"{len(t)} templates -> {out/'templates.csv'}")
    print((t.isf / t.isf_true).describe(percentiles=[.1, .5, .9]).round(2).to_string())
    print((t.basal / t.basal_true).describe(percentiles=[.1, .5, .9]).round(2).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
