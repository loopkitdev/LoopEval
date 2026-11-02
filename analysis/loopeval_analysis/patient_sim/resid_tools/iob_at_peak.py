"""Is the shallow post-meal trough a DOSE difference or an action-shape difference? IOB at the meal peak and its fall
over the next 90 min, donors vs twins, both through the ice extractor's total IOB (L 497). The trough is already shown
insensitive to appearance (wave2) and to A12b (ppr_a), L 573.
    python iob_at_peak.py <run> [n]"""
import sys, json, pickle, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path.home() / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L
from loopeval_analysis.patient_sim.quiet import local_offset, to_local

def rows(t, g, iob_t, iob_v, ent):
    out = []
    for t0, gm in ent:
        if gm < 20: continue
        i = int(np.searchsorted(t, t0))
        if i < 1 or i + 49 >= len(t) or t[i + 48] - t[i] > 260: continue
        seg = g[i:i + 49]
        if np.isnan(seg).any(): continue
        k = int(np.argmax(seg[:30]))
        if k < 3: continue
        fall = float(seg[k] - np.min(seg[k:min(k + 18, len(seg))]))
        i0 = float(np.interp(t[i + k], iob_t, iob_v)); i1 = float(np.interp(t[i + k] + 90, iob_t, iob_v))
        if not (np.isfinite(i0) and np.isfinite(i1)): continue
        out.append(dict(grams=gm, fall=fall, iob_peak=i0, iob_used=i0 - i1, iob_per_g=i0 / max(gm, 1)))
    return out

def show(lab, R):
    D = pd.DataFrame(R)
    print(f"  {lab:12s} n{len(D):5d}  grams p50 {D.grams.median():4.0f}  IOB at peak p50 {D.iob_peak.median():5.2f} U"
          f"  IOB per entered g {D.iob_per_g.median():.3f}  IOB spent in next 90 min {D.iob_used.median():5.2f} U"
          f"  fall {D.fall.median():5.1f}")

don = []
for a in sorted({p.stem for p in (L.ICE_ROOT / "steps").glob("*.parquet")}):
    try:
        off = local_offset(a, L.ICE_ROOT)
        c = json.load(open(L.ICE_ROOT / "full" / a / "carbs.json"))
        if not c: continue
        ct = L._mins(to_local(pd.to_datetime([x["startDate"] for x in c], utc=True), off))
        gr = [float(x.get("grams") or 0) for x in c]
        o = np.argsort(ct); ent = [(ct[i], gr[i]) for i in o]
        s = pd.read_parquet(L.ICE_ROOT / "steps" / f"{a}.parquet", columns=["t1", "bg1", "iob"])
    except Exception:
        continue
    t = L._mins(to_local(s.t1, off))
    g = pd.Series(s.bg1.to_numpy(float)).interpolate(limit=3).to_numpy()
    io = pd.Series(s.iob.to_numpy(float)).interpolate(limit=6).to_numpy()
    don += rows(t, g, t, io, ent)
print("== DONORS (entries >= 20 g, total IOB)"); show("donors", don)
run = Path(sys.argv[1]); n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
R = []
for p in sorted(run.glob("v0*"))[:n]:
    st = L._sim_steps(p)
    if st is None: continue
    tr = pickle.load(open(p / "truth.pkl", "rb")); c = tr["cgm"].dropna(); c = c[c.index >= 2880]
    io = pd.Series(st.iob.to_numpy(float)).interpolate(limit=6).to_numpy()
    R += rows(c.index.to_numpy(float), c.to_numpy(float), st.t.to_numpy(float), io,
              [(e[0], e[1]) for e in tr["entries"]])
print(f"== {run.name} ({n} people)"); show(run.name, R)
