"""Is a change-response ratio partly an artefact of the arm's own pre-edit glucose DISTRIBUTION?

Answer, measured (LESSONS 662): beyond the LEVEL (which L 638 corrects for), no. Across eight real
e-pool arms the level-adjusted damping correlates -0.17 to -0.43 with dispersion, and `sk1_e` / `sr1_e`
share the pre-edit mean, sd and t180 while responding 1.16 against 1.66. Kept as the instrument that
showed it, and as the way to re-check the question when a new arm looks suspicious.

For each REAL e-pool arm (no-op versions excluded by bitwise check), measures the pre-edit
state the edit acts on, level-adjusts its response ratio the L 638 way, and asks whether
the residual damping tracks dispersion.  Pure pickle reads; no simulation.
"""
import pickle
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path("/Users/pete/.loop-eval/runs/2026-10-28-additive-epool/change_e")
BURN = 2880.0
E = pd.read_csv(HERE / "events.csv")
eids = list(E.eid)[:120]

# RAW ratios read from each arm's own score_change log (field = 1.0; higher = more damped)
ARMS = {
    "rf2e_s": (1.33, 1.28, "reference rf2"),
    "sk2_e":  (0.98, 0.95, "sg_kappa 0.15 + sg_mult 0.55"),
    "sk1_e":  (1.06, 1.06, "sg_kappa 0.15"),
    "hl2_e":  (1.43, 1.40, "sg_h_lo"),
    "sw0b_e": (1.44, 1.28, "csf_sd_w 0.0"),
    "sw5b_e": (1.47, 1.25, "csf_sd_w 0.5"),
    "sr1_e":  (1.52, 1.46, "sg_rate 0.55"),
    "sn_e":   (1.55, 1.54, "si_norm 1.0"),
    "afe1":   (1.57, 1.54, "act_frag  (job 175)"),
    "go3e2":  (1.59, 1.69, "ge_order 3 (job 172)"),
}


def outc(run):
    t = pickle.load(open(run / "truth.pkl", "rb"))
    c = t["cgm"].dropna(); c = c[c.index >= BURN].to_numpy()
    if c.size == 0:
        return None
    return dict(mean=float(c.mean()), sd=float(c.std()), cv=100 * float(c.std() / c.mean()),
                t180=100 * np.mean(c > 180))


rows = []
for arm in ARMS:
    for eid in eids:
        bd = HERE / arm / f"{eid}_before"
        if not bd.exists():
            continue
        vs = [outc(s) for s in sorted(bd.glob("v0*")) if (s / "truth.pkl").exists()]
        vs = [v for v in vs if v]
        if vs:
            rows.append(dict(arm=arm, **{k: float(np.mean([v[k] for v in vs])) for k in vs[0]}))

g = pd.DataFrame(rows).groupby("arm")[["mean", "sd", "cv", "t180"]].median()
ref = g.loc["rf2e_s", "mean"]
g["raw_mean"] = [ARMS[a][0] for a in g.index]
g["raw_tir"] = [ARMS[a][1] for a in g.index]
# L 638: dG/dI is proportional to G, so an arm sitting higher responds more for free.
g["lvl_mean"] = g.raw_mean * g["mean"] / ref
g["lvl_tir"] = g.raw_tir * g["mean"] / ref
g["what"] = [ARMS[a][2] for a in g.index]
g = g.sort_values("lvl_mean")
print("PRE-EDIT state per arm (median over %d events) with LEVEL-ADJUSTED response ratios" % len(eids))
print("1.00 = the field's own response size; higher = MORE damped\n")
print(g[["mean", "sd", "cv", "t180", "raw_mean", "lvl_mean", "raw_tir", "lvl_tir", "what"]].round(2).to_string())
print("\nDoes the LEVEL-ADJUSTED damping track dispersion?")
for y in ["lvl_mean", "lvl_tir"]:
    for x in ["sd", "cv", "t180"]:
        print(f"  corr({x:4s}, {y}) = {np.corrcoef(g[x], g[y])[0,1]:+.3f}")
    print()
