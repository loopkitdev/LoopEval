"""Per-person amplitudes of the data-driven residual (LESSONS 514): what the donor's unexplained drive has that the core
twin's does not, at three time scales, on ice_var.py's quiet statistics (fast, block, day SD; mg/dL/h).
  1. transfer: each residual part at unit amplitude, alone, through the same statistics (Monte Carlo) -> T (3x3, variance)
  2. targets: the donor's per-person median, shrunk toward the cohort median by the statistic's block-to-block
     reliability (in log)
  3. need = target^2 - core^2 per statistic (core = the core-only twin of the same template, else the cohort median of
     core twins); amplitudes^2 = NNLS(T, need)
Writes templates_pilot_resid.csv (templates_pilot_logs.csv + resid_f / resid_b / resid_d) and resid_fit.csv.
    python fit_resid.py <core run> [scale]"""
import sys, os, glob, pickle, numpy as np, pandas as pd
from pathlib import Path
from scipy.optimize import nnls
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))   # this tree's analysis/ (live or frozen)
from loopeval_analysis.patient_sim.resid_tools.ice_var import stats
H = Path.home()
TPL = Path(os.environ.get("TPL_CSV", str(H / ".loop-eval/runs/2026-10-15-additive-templates/templates_pilot_logs.csv")))
ST = ["fast_sd_quiet", "block_sd_quiet", "day_sd_quiet"]
TF, TB = 20.0, 180.0


def series(a, rng, days=13):
    n = int(days * 1440); x = np.zeros(2); out = np.zeros(n); lv = rng.normal(size=days + 2)
    af, ab, ad = a
    for m in range(n):
        for i, tau in enumerate((TF, TB)):
            k = np.exp(-1 / tau); x[i] = k * x[i] + np.sqrt(1 - k * k) * rng.normal()
        u = (m - 240) / 1440; d = int(np.floor(u)); w = min(1.0, (u - d) * 1440 / 120)
        out[m] = af * x[0] + ab * x[1] + ad * (w * lv[d + 1] + (1 - w) * lv[d])
    t = np.arange(0, n, 5, dtype=float); return t, out[::5]


def transfer(reps=6):
    rng = np.random.default_rng(7); T = np.zeros((3, 3))
    for j in range(3):
        a = [0.0, 0.0, 0.0]; a[j] = 1.0; v = []
        for _ in range(reps):
            t, y = series(a, rng); s = stats(t, y, np.zeros(len(t)), "mc", 0); v.append([s[k] ** 2 for k in ST])
        T[:, j] = np.mean(v, axis=0)
    return T


if __name__ == "__main__":
    core = Path(sys.argv[1]); scale = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    T = transfer(); print("transfer (variance of each statistic per unit amplitude^2; rows", ST, "cols f/b/d):\n", T.round(3))
    D = pd.read_csv(Path.cwd() / "icevar_donors.csv")
    rel = {}
    for k in ST:
        b = D.groupby("who").filter(lambda g: len(g) >= 2).groupby("who")[k].apply(lambda s: s.iloc[:2].to_list())
        x = np.array(b.to_list()); rel[k] = max(0.0, pd.Series(x[:, 0]).corr(pd.Series(x[:, 1])))
    print("reliability", {k: round(v, 2) for k, v in rel.items()})
    P = D.groupby("who")[ST].median()
    tgt = P.copy()
    for k in ST:
        lm = np.log(P[k]).median(); tgt[k] = np.exp(lm + rel[k] * (np.log(P[k]) - lm)).fillna(np.exp(lm))
    C = pd.read_csv(Path.cwd() / f"icevar_{core.name}.csv").set_index("who")
    tm = {Path(d).name: pickle.load(open(d + "/person.pkl", "rb")).template for d in glob.glob(str(core) + "/v0*")}
    C["tmpl"] = C.index.map(tm); Ct = C.groupby("tmpl")[ST].median(); cmed = C[ST].median()
    Tp = pd.read_csv(TPL); rows = []
    for a in Tp.alias:
        if a not in tgt.index: rows.append(dict(alias=a)); continue
        c = (Ct.loc[a] if a in Ct.index else cmed).fillna(cmed)
        need = np.maximum(0.0, (scale * tgt.loc[a, ST].to_numpy(float)) ** 2 - c.to_numpy(float) ** 2)
        a2, _ = nnls(T, need)
        rows.append(dict(alias=a, resid_f=np.sqrt(a2[0]), resid_b=np.sqrt(a2[1]), resid_d=np.sqrt(a2[2]),
                         **{f"tgt_{k}": tgt.loc[a, k] for k in ST}, **{f"core_{k}": c[k] for k in ST}, core_own=a in Ct.index))
    F = pd.DataFrame(rows); F.to_csv(Path.cwd() / "resid_fit.csv", index=False)
    print(F[["resid_f", "resid_b", "resid_d"]].describe().round(1).to_string())
    print("share with no residual needed on all three:", round(float((F[["resid_f", "resid_b", "resid_d"]].fillna(0).sum(axis=1) == 0).mean()), 2))
    out = Tp.merge(F[["alias", "resid_f", "resid_b", "resid_d"]], on="alias", how="left")
    if len(sys.argv) > 4:      # carry an earlier fit's per-person level (resid_m) into the new amplitudes
        L = pd.read_csv(sys.argv[4])[["alias", "resid_m"]]; out = out.merge(L, on="alias", how="left")
    dst = sys.argv[3] if len(sys.argv) > 3 else str(H / ".loop-eval/runs/2026-10-15-additive-templates/templates_pilot_resid.csv")
    out.to_csv(dst, index=False); print("->", dst)
