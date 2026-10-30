"""Body-model sensitivity fits (patient_sim.fit_body regression form) for given aliases of one ICE root, without touching
the repo or the live templates: fit_body's module globals ICE / TPL are pointed at the root and at a template file.

  fit_reg.csv  — `fit_body --regression`          (b_all, se_all, halves) with isf_true = isf_true_ys (as at the fit, LESSONS 262)
  fit_seg.csv  — `fit_body --regression --segments` (b_B/L/D, halves)       with isf_true = yardstick × body mult (as at seg_fit)

  python run_fit.py ROOT ALIAS[,ALIAS] TEMPLATE_CSV OUTDIR [--stage reg|seg]
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))   # this tree's analysis/ (live or frozen)
from loopeval_analysis.patient_sim import fit_body as FB     # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("root"); ap.add_argument("aliases"); ap.add_argument("tpl"); ap.add_argument("outdir")
ap.add_argument("--stage", default="reg")
a = ap.parse_args()
FB.ICE = Path(a.root).expanduser()
T = pd.read_csv(a.tpl)
if a.stage == "reg":
    T["isf_true"] = T["isf_true_ys"] if "isf_true_ys" in T and T.isf_true_ys.notna().all() else T["isf_ys"].fillna(T["isf_true"])
tp = Path(a.outdir) / f"_tpl_{a.stage}.csv"; T.to_csv(tp, index=False); FB.TPL = tp
FB.SEGMENTS = a.stage == "seg"
rows = [FB.fit_alias_regression(x) for x in a.aliases.split(",")]
pd.DataFrame(rows).to_csv(Path(a.outdir) / f"fit_{a.stage}.csv", index=False)
print(pd.DataFrame(rows).T.to_string())
