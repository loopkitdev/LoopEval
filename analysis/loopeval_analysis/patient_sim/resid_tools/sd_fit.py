"""One round of the per-person meal-glucose multiplier fitted to the donor's glucose SD (LESSONS 529): csf_sd_mult ×=
(donor SD / twin SD)^GAIN, step clipped 0.8–1.25, total 0.4–2.5; both draws pooled per template; donor SD = median over
13-day blocks of bg_cv × bg_mean (LVL_BLOCKS=odd: odd blocks only, for the held-out check).
    python sd_fit.py <template csv in> <template csv out> <run> [<run> ...]"""
import sys, os, glob, pickle, numpy as np, pandas as pd
from pathlib import Path
H = Path.home(); GAIN = float(os.environ.get("SD_GAIN", "1.5"))
tin, tout, runs = sys.argv[1], sys.argv[2], sys.argv[3:]
B = pd.read_csv(H / ".loop-eval/runs/2026-10-15-additive-templates/real_pilot_blocks.csv")
if os.environ.get("LVL_BLOCKS") == "odd": B = B[B.block % 2 == 1]
B["sd"] = B.bg_cv * B.bg_mean / 100; D = B.groupby("alias").sd.median()
if os.environ.get("LVL_TARGET") == "template": _t = pd.read_csv(tin).set_index("alias"); D = _t.bg_cv * _t.bg_mean / 100   # a pool without block tables
fr = []
for r in runs:
    S = pd.read_csv(Path(r) / "sim_stats.csv"); k = [c for c in S.columns if c in ("name", "who", "alias")][0]
    tm = {Path(d).name: pickle.load(open(d + "/person.pkl", "rb")).template for d in glob.glob(r + "/v0*")}
    S["tmpl"] = S[k].map(tm); S["sd"] = S.bg_cv * S.bg_mean / 100; fr.append(S[["tmpl", "sd"]])
now = pd.concat(fr).groupby("tmpl").sd.mean()
ratio = (D.reindex(now.index) / now).dropna()
T = pd.read_csv(tin).set_index("alias")
if "csf_sd_mult" not in T: T["csf_sd_mult"] = 1.0
T["csf_sd_mult"] = T.csf_sd_mult.fillna(1.0)
T.loc[ratio.index, "csf_sd_mult"] = (T.loc[ratio.index, "csf_sd_mult"] * (ratio ** GAIN).clip(0.8, 1.25)).clip(0.4, 2.5)
T.reset_index().to_csv(tout, index=False)
print(f"twins {len(now)}  SD twin/donor p10/50/90 {(1 / ratio).quantile([.1, .5, .9]).round(2).tolist()}  rho {now.corr(D.reindex(now.index), method='spearman'):.2f}")
print("csf_sd_mult p10/50/90", T.csf_sd_mult.quantile([.1, .5, .9]).round(2).tolist())
