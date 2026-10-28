"""Where the twins lack variability: the ICE (glucose change not explained by insulin, ice extractor, same code both
sides) decomposed by time scale, per person, then pooled.
  day     SD of the daily mean ICE across days (the day's net need), and its lag-1 autocorrelation
  block   SD of 4-h block means within a day after removing the person's clock-hour profile and the day's mean
  fast    SD of the 15-min mean ICE minus its centred 2-h mean (pulse-scale motion)
each on ALL clean steps and on QUIET steps (no carb entry in the prior 4 h). Donors: their 13-day blocks (as the
twins' length) so day statistics compare like for like.
    python ice_var.py donors | <run>"""
import sys, subprocess, tempfile, numpy as np, pandas as pd
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
H = Path.home(); sys.path.insert(0, str(H / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L
from loopeval_analysis.patient_sim.world import EPOCH
COLS = ["t1", "ice", "carbs_g", "clean"]


def stats(t, ice, cg, who, block):
    o = np.argsort(t); t, ice, cg = t[o], ice[o], cg[o]
    et = t[cg > 0]
    q = np.ones(len(t), bool)
    k = np.searchsorted(et, t, side="right") - 1
    q[(k >= 0)] = (t[k >= 0] - et[k[k >= 0]]) > 240
    out = dict(who=who, block=block)
    for tag, m in (("all", np.ones(len(t), bool)), ("quiet", q)):
        s = pd.DataFrame(dict(t=t[m], ice=ice[m]))
        if len(s) < 288 * 5: continue
        s["day"] = (s.t // 1440).astype(int); s["hr"] = ((s.t % 1440) // 60).astype(int); s["b4"] = ((s.t % 1440) // 240).astype(int)
        dm = s.groupby("day").ice.agg(["mean", "size"]); dm = dm[dm["size"] >= (100 if tag == "quiet" else 200)]["mean"]
        if len(dm) >= 5:
            out[f"day_sd_{tag}"] = dm.std()
            dd = dm.reindex(range(dm.index.min(), dm.index.max() + 1))
            out[f"day_ac1_{tag}"] = dd.autocorr(1) if dd.notna().sum() >= 6 else np.nan
        s["r"] = s.ice - s.groupby("hr").ice.transform("mean") - s.groupby("day").ice.transform("mean") + s.ice.mean()
        bm = s.groupby(["day", "b4"]).r.agg(["mean", "size"]); bm = bm[bm["size"] >= 24]["mean"]
        out[f"block_sd_{tag}"] = bm.std()
        g = np.full(int((t[-1] - t[0]) // 5) + 1, np.nan); kk = ((s.t - t[0]) // 5).astype(int).to_numpy(); g[kk] = s.ice.to_numpy()
        x15 = pd.Series(g).rolling(3, center=True, min_periods=2).mean(); x2h = pd.Series(g).rolling(24, center=True, min_periods=12).mean()
        dv = (x15 - x2h).dropna()
        out[f"fast_sd_{tag}"] = float(dv.std())
        out[f"fast_skew_{tag}"] = float(dv.skew())
        out[f"fast_q05_{tag}"] = float(dv.quantile(.05)); out[f"fast_q95_{tag}"] = float(dv.quantile(.95))
        out[f"mean_{tag}"] = float(s.ice.mean())
    return out


def donor(a):
    from loopeval_analysis.patient_sim.quiet import local_offset, to_local
    try:
        off = local_offset(a, L.ICE_ROOT); s = pd.read_parquet(L.ICE_ROOT / "steps" / f"{a}.parquet", columns=COLS)
    except Exception: return []
    t = L._mins(to_local(s.t1, off)); cl = s.clean.fillna(False).to_numpy(bool)
    ice = s.ice.to_numpy(float); cg = s.carbs_g.fillna(0).to_numpy(float)
    rows = []; t0 = np.floor(t.min() / 1440) * 1440 + 1440; b = 0
    while t0 + 13 * 1440 <= t.max():
        w = (t >= t0) & (t < t0 + 13 * 1440)
        if (w & cl).sum() > 0.6 * 13 * 288:
            m = w & cl & np.isfinite(ice); r = stats(t[m], ice[m], cg[m], a, b); rows.append(r); b += 1
        t0 += 13 * 1440
    return rows


def twin(d):
    from loopeval_analysis.patient_sim.ice_check import export_sim
    code = ("import sys; sys.path.insert(0, sys.argv[1]); from loopeval_analysis.ice_gen import extract as X; "
            f"s, _ = X.extract(sys.argv[2]); s[{COLS!r}].to_parquet(sys.argv[3])")
    with tempfile.TemporaryDirectory() as td:
        try: export_sim(Path(d), Path(td))
        except Exception: return []
        r = subprocess.run([sys.executable, "-W", "ignore", "-c", code, str(L.ICE_ANALYSIS), td, td + "/s.parquet"], capture_output=True)
        if r.returncode: return []
        s = pd.read_parquet(td + "/s.parquet")
    t = ((s.t1 - EPOCH).dt.total_seconds() / 60).to_numpy(); cl = s.clean.fillna(False).to_numpy(bool) & (t >= 2 * 1440)
    ice = s.ice.to_numpy(float); m = cl & np.isfinite(ice)
    return [stats(t[m], ice[m], s.carbs_g.fillna(0).to_numpy(float)[m], Path(d).name, 0)]


if __name__ == "__main__":
    if sys.argv[1] == "donors":
        T = pd.read_csv(H / ".loop-eval/runs/2026-10-15-additive-templates/templates_pilot.csv"); items, f = sorted(T.alias), donor
    else:
        items, f = [str(p) for p in sorted(Path(sys.argv[1]).glob("v0*"))], twin
    with ProcessPoolExecutor(int(sys.argv[2]) if len(sys.argv) > 2 else 4) as ex: res = list(ex.map(f, items))
    R = pd.DataFrame([r for rs in res for r in rs]); R.to_csv((Path.cwd() / f"icevar_{Path(sys.argv[1]).name}.csv"), index=False)
    P = R.groupby("who").median(numeric_only=True)
    print(f"{sys.argv[1]}: {len(R)} blocks, {len(P)} people (per-person medians, then p10 / p50 / p90)")
    for c in [c for c in P.columns if c != "block"]:
        print(f"  {c:16s} {P[c].quantile(.1):8.2f} {P[c].median():8.2f} {P[c].quantile(.9):8.2f}")
