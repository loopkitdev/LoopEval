"""One round of the per-person residual level (resid_m, mg/dL/h; LESSONS 515): each template's twin mean glucose
(sim_stats.csv, both draws pooled) against its donor's (median over 13-day blocks), resid_m += gain x gap, where the
gain is the cohort slope measured between rounds (first round: GAIN0). Templates without a twin keep their value.
    python lvl_resid.py <template csv in> <template csv out> <run> [<run> ...] [--prev <run> ...]"""
import sys, glob, pickle, numpy as np, pandas as pd
from pathlib import Path
H = Path.home()
GAIN0 = 0.5   # first round; 1 / the measured slope (0.6–1.0) after, or LVL_GAIN
import os as _os
if _os.environ.get("LVL_GAIN"): GAIN0 = float(_os.environ["LVL_GAIN"])
args = sys.argv[1:]
tin, tout = args[0], args[1]
rest = args[2:]
prev = rest[rest.index("--prev") + 1:] if "--prev" in rest else []
runs = rest[:rest.index("--prev")] if "--prev" in rest else rest


def twin_means(runs):
    out = []
    for r in runs:
        S = pd.read_csv(Path(r) / "sim_stats.csv")
        k = [c for c in S.columns if c in ("name", "who", "alias")][0]
        tm = {Path(d).name: pickle.load(open(d + "/person.pkl", "rb")).template for d in glob.glob(r + "/v0*")}
        S["tmpl"] = S[k].map(tm); out.append(S[["tmpl", "bg_mean"]])
    return pd.concat(out).groupby("tmpl").bg_mean.mean()


T = pd.read_csv(tin)
if "resid_m" not in T: T["resid_m"] = 0.0
T["resid_m"] = T.resid_m.fillna(0.0)
import os
B_ = pd.read_csv(H / ".loop-eval/runs/2026-10-15-additive-templates/real_pilot_blocks.csv")
if os.environ.get("LVL_BLOCKS") == "odd": B_ = B_[B_.block % 2 == 1]      # held-out check: fit on odd blocks only
D = B_.groupby("alias").bg_mean.median()
now = twin_means(runs)
gap = (D.reindex(now.index) - now).dropna()
gain = GAIN0
if prev:
    before = twin_means(prev); d_twin = (now - before.reindex(now.index)).dropna()
    hist = pd.read_csv(tin + ".step.csv").set_index("alias").step if Path(tin + ".step.csv").exists() else None
    if hist is not None:
        j = pd.concat([d_twin, hist], axis=1, join="inner").dropna(); j = j[j.iloc[:, 1].abs() > 1]
        slope = np.median(j.iloc[:, 0] / j.iloc[:, 1]) if len(j) > 10 else np.nan   # mg/dL of mean per mg/dL/h of drive
        print(f"measured slope {slope:.2f} mg/dL per mg/dL/h (n {len(j)})")
        if np.isfinite(slope) and slope > 0.2: gain = 1.0 / slope
step = (gain * gap).clip(-40, 40)
T = T.set_index("alias"); T.loc[step.index, "resid_m"] = (T.loc[step.index, "resid_m"] + step).clip(-150, 150)
T.reset_index().to_csv(tout, index=False)
step.rename("step").rename_axis("alias").to_csv(tout + ".step.csv")
print(f"twins {len(now)}  |gap| p50 {gap.abs().median():.1f}  gap p10/p50/p90 {gap.quantile([.1, .5, .9]).round(1).tolist()}  gain {gain:.2f}")
print(f"twin-donor mean rho {now.corr(D.reindex(now.index), method='spearman'):.2f}")
print("resid_m p10/p50/p90", T.resid_m.quantile([.1, .5, .9]).round(1).tolist())
