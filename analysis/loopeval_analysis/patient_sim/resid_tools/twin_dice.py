"""The twins' need shift at each edit, like the field's d_ice (LESSONS 533): clean-ICE mean of the after arm minus the
before arm (same window, same seed), the ice extractor on both, as the field's post - pre. Regressed on the insulin index
with the field's.   python twin_dice.py <arm>"""
import sys, subprocess, tempfile, glob, numpy as np, pandas as pd
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
H = Path.home(); sys.path.insert(0, str(H / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L
from loopeval_analysis.patient_sim.world import EPOCH
HERE = Path(__file__).resolve().parent


def ice_mean(d):
    from loopeval_analysis.patient_sim.ice_check import export_sim
    code = ("import sys; sys.path.insert(0, sys.argv[1]); from loopeval_analysis.ice_gen import extract as X; "
            "s, _ = X.extract(sys.argv[2]); s[['t1','ice','clean']].to_parquet(sys.argv[3])")
    with tempfile.TemporaryDirectory() as td:
        try: export_sim(Path(d), Path(td))
        except Exception: return d, np.nan
        r = subprocess.run([sys.executable, "-W", "ignore", "-c", code, str(L.ICE_ANALYSIS), td, td + "/s.parquet"], capture_output=True)
        if r.returncode: return d, np.nan
        s = pd.read_parquet(td + "/s.parquet")
    t = ((s.t1 - EPOCH).dt.total_seconds() / 60).to_numpy(); k = (t >= 2880) & s.clean.fillna(False).to_numpy(bool)
    return d, float(s.ice[k].mean())


if __name__ == "__main__":
    arm = HERE / sys.argv[1]
    dirs = sorted(glob.glob(str(arm / "*" / "v0*")))
    with ProcessPoolExecutor(8) as ex: res = dict(ex.map(ice_mean, dirs))
    rows = []
    for d, v in res.items():
        p = Path(d); eid, a = p.parent.name.rsplit("_", 1); rows.append(dict(eid=eid, arm=a, seed=p.name, ice=v))
    R = pd.DataFrame(rows).pivot_table(index=["eid", "seed"], columns="arm", values="ice").dropna()
    D = (R["after"] - R["before"]).groupby("eid").mean().rename("twin_dice")
    E = pd.read_csv(HERE / "events.csv"); F = pd.read_csv(HERE / "field_and_tools.csv")
    m = F.merge(E[["eid", "basal_before", "basal_after", "isf_before", "isf_after", "cr_before", "cr_after", "target_before", "target_after"]], on="eid").join(D, on="eid").dropna(subset=["d_ice", "twin_dice"])
    m["x"] = np.log(m.basal_after / m.basal_before) - np.log(m.isf_after / m.isf_before); m["lcr"] = np.log(m.cr_after / m.cr_before)
    X = np.column_stack([m.x, m.lcr, m.target_after - m.target_before, np.ones(len(m))])
    for c in ["d_ice", "twin_dice"]:
        b = np.linalg.lstsq(X, m[c], rcond=None)[0]
        print(f"{c:10s} n {len(m)}  per log-unit x {b[0]:+6.1f}  per log-unit CR {b[1]:+6.1f}  sd {m[c].std():.1f}")
    print("corr(field d_ice, twin d_ice)", round(m.d_ice.corr(m.twin_dice, method="spearman"), 2))
    m.to_csv(HERE / f"dice_{sys.argv[1]}.csv", index=False)
