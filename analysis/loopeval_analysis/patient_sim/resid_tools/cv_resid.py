"""One round of the per-person fast-residual size fitted to the donor's glucose CV (LESSONS 524): resid_f ×=
(donor CV / twin CV)^gain, both draws pooled per template; donor CV = median over 13-day blocks (LVL_BLOCKS=odd: odd
blocks only, for the held-out check). A twin at resid_f 0 that needs more starts from the cohort median.
    python cv_resid.py <template csv in> <template csv out> <run> [<run> ...]"""
import sys, os, glob, pickle, numpy as np, pandas as pd
from pathlib import Path
H = Path.home()
GAIN = float(os.environ.get("CV_GAIN", "2.0"))
tin, tout, runs = sys.argv[1], sys.argv[2], sys.argv[3:]
B = pd.read_csv(H / ".loop-eval/runs/2026-10-15-additive-templates/real_pilot_blocks.csv")
if os.environ.get("LVL_BLOCKS") == "odd": B = B[B.block % 2 == 1]
D = B.groupby("alias").bg_cv.median()
fr = []
for r in runs:
    S = pd.read_csv(Path(r) / "sim_stats.csv"); k = [c for c in S.columns if c in ("name", "who", "alias")][0]
    tm = {Path(d).name: pickle.load(open(d + "/person.pkl", "rb")).template for d in glob.glob(r + "/v0*")}
    S["tmpl"] = S[k].map(tm); fr.append(S[["tmpl", "bg_cv"]])
now = pd.concat(fr).groupby("tmpl").bg_cv.mean()
ratio = (D.reindex(now.index) / now).dropna()
T = pd.read_csv(tin).set_index("alias"); T["resid_f"] = T.resid_f.fillna(0.0)
med = float(T.resid_f[T.resid_f > 0].median())
f = T.loc[ratio.index, "resid_f"].where(lambda x: x > 0, med * (ratio > 1))
T.loc[ratio.index, "resid_f"] = (f * ratio.clip(0.6, 1.6) ** GAIN).clip(0, 150)
T.reset_index().to_csv(tout, index=False)
print(f"twins {len(now)}  CV twin/donor p10/p50/p90 {(1 / ratio).quantile([.1, .5, .9]).round(2).tolist()}  rho {now.corr(D.reindex(now.index), method='spearman'):.2f}")
print("resid_f p10/p50/p90", T.resid_f.quantile([.1, .5, .9]).round(1).tolist())
