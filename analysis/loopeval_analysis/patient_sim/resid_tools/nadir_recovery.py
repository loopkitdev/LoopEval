"""Recovery from a SHALLOW low, the target A1b-below-basal is built for (L 559-560, 596): at a 60-70 mg/dL nadir the
donors rise +26 mg/dL in 30 min and dwell 10 min under 70; the twins rise +21 and dwell 15. Same definition on both
sides: a local minimum in 60-70 with no carb entry in the 20 min before it (so the rise is the body's, not food's).
    python nadir_recovery.py <run> [...]"""
import sys, pickle, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path.home() / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L

def nadirs(t, g, carb_t, lo=60.0, hi=70.0):
    out = []
    n = len(g)
    ct = np.sort(np.asarray(carb_t, float))
    for i in range(6, n - 7):
        if not (lo <= g[i] <= hi): continue
        if not (g[i] <= g[i - 1] and g[i] <= g[i + 1]): continue
        if i >= 6 and g[i] > np.min(g[max(0, i - 6):i + 1]): continue
        k = np.searchsorted(ct, t[i])
        if k > 0 and t[i] - ct[k - 1] < 20: continue      # food just before: not a body recovery
        j = min(i + 6, n - 1)
        rise = float(g[j] - g[i])
        dwell = float(np.sum(g[i:min(i + 24, n)] < 70.0) * (t[1] - t[0] if n > 1 else 5.0))
        out.append((rise, dwell))
    return out

def show(lab, r):
    if len(r) < 20: return
    R = np.array(r)
    print(f"  {lab:>9} n{len(R):5d}  rise in 30 min {np.median(R[:,0]):+6.1f} mg/dL   dwell under 70 {np.median(R[:,1]):5.0f} min")

don = []
for a in sorted({p.stem for p in (L.ICE_ROOT / "steps").glob("*.parquet")}):
    try:
        s = pd.read_parquet(L.ICE_ROOT / "steps" / f"{a}.parquet", columns=["t1", "bg1", "carbs_g"])
    except Exception:
        continue
    t = np.asarray(L._mins(s.t1), float); g = s.bg1.to_numpy(float)
    m = np.isfinite(g)
    if m.sum() < 2000: continue
    don += nadirs(t[m], g[m], t[(s.carbs_g.fillna(0) > 0).to_numpy() & m])
print("nadirs in 60-70 mg/dL with no carb entry in the 20 min before (the body's own recovery)")
show("donors", don)

for run in sys.argv[1:]:
    r = []
    for p in sorted(Path(run).glob("v*/truth.pkl")):
        try: d = pickle.load(open(p, "rb"))
        except Exception: continue
        c = d["cgm"].dropna(); t = np.asarray(c.index, float); g = c.to_numpy(float)
        u = t >= 2880; t, g = t[u], g[u]
        ent = np.array([float(e[0]) for e in d["entries"]])
        r += nadirs(t, g, ent)
    show(Path(run).name, r)
