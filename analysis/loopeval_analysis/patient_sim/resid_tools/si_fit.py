"""One round of the per-person intraday SI wander (si_var, log-SI SD of the B4 OU) fitted to the donor's glucose SD
(LESSONS 543): si_var x= (donor SD / twin SD)^GAIN, step 0.6-1.6, total 0-0.8; donor SD from the template (whole record).
    python si_fit.py <template in> <template out> <run> [<run> ...]"""
import sys, os, glob, pickle, numpy as np, pandas as pd
from pathlib import Path
GAIN = float(os.environ.get("SI_GAIN", "3.0"))
tin, tout, runs = sys.argv[1], sys.argv[2], sys.argv[3:]
T = pd.read_csv(tin).set_index("alias")
D = T.bg_cv * T.bg_mean / 100
fr = []
for r in runs:
    S = pd.read_csv(Path(r) / "sim_stats.csv"); k = [c for c in S.columns if c in ("name", "who", "alias")][0]
    tm = {Path(d).name: pickle.load(open(d + "/person.pkl", "rb")).template for d in glob.glob(r + "/v0*")}
    S["tmpl"] = S[k].map(tm); S["sd"] = S.bg_cv * S.bg_mean / 100; fr.append(S[["tmpl", "sd"]])
now = pd.concat(fr).groupby("tmpl").sd.mean()
ratio = (D.reindex(now.index) / now).dropna()
if "si_var" not in T: T["si_var"] = 0.12
T["si_var"] = T.si_var.fillna(0.12)
T.loc[ratio.index, "si_var"] = (T.loc[ratio.index, "si_var"].clip(lower=0.02) * (ratio ** GAIN).clip(0.6, 1.6)).clip(0.0, 0.8)
T.reset_index().to_csv(tout, index=False)
print(f"twins {len(now)}  SD twin/donor p10/50/90 {(1 / ratio).quantile([.1, .5, .9]).round(2).tolist()}  rho {now.corr(D.reindex(now.index), method='spearman'):.2f}")
print("si_var p10/50/90", T.si_var.quantile([.1, .5, .9]).round(3).tolist())
