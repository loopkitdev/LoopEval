"""Do donor meals have TWO phases — a sharp rise, a fast fall, then a second rise — where the twins have one hump?
That is the only shape that gives fast falls AND elevation at 3 h together (L 569-570, 512, 170). Measures the 4-hour
profile after a carb entry >= 20 g on both sides, same code.
    python bimodal.py <run> [...]"""
import sys, json, pickle, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path.home() / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L
from loopeval_analysis.patient_sim.quiet import local_offset, to_local

def shape(g):
    """g: 49 readings (4 h at 5 min) from the entry. Returns peak index, fall from peak, and the second rise."""
    if len(g) < 40 or np.isnan(g).any(): return None
    k = int(np.argmax(g[:30]))                      # first peak within 2.5 h
    if k < 3: return None
    fall = float(g[k] - np.min(g[k:min(k + 18, len(g))]))     # fall in the 90 min after the peak
    j = k + int(np.argmin(g[k:min(k + 18, len(g))]))
    rise2 = float(np.max(g[j:]) - g[j]) if j + 3 < len(g) else 0.0
    return dict(peak_min=k * 5, rise1=float(g[k] - g[0]), fall=fall, rise2=rise2,
                d3h=float(g[36] - g[0]) if len(g) > 36 else np.nan)

def show(lab, R):
    D = pd.DataFrame([r for r in R if r])
    print(f"  {lab:12s} n{len(D):5d}  peak at {D.peak_min.median():3.0f} min  rise1 {D.rise1.median():5.1f}"
          f"  fall after peak {D.fall.median():5.1f}  2nd rise {D.rise2.median():5.1f}  3-h change {D.d3h.median():5.1f}")
    print(f"               fall >= 30 mg/dL: {(D.fall >= 30).mean():.2f}   2nd rise >= 20: {(D.rise2 >= 20).mean():.2f}"
          f"   BOTH: {((D.fall >= 30) & (D.rise2 >= 20)).mean():.2f}")

FAM = pd.read_csv(Path.home() / ".loop-eval/runs/2026-10-15-additive-templates/templates_pilot.csv")[["alias", "sensor"]].set_index("alias").sensor.to_dict()
don = []
for a in sorted({p.stem for p in (L.ICE_ROOT / "steps").glob("*.parquet")}):
    try:
        off = local_offset(a, L.ICE_ROOT)
        c = json.load(open(L.ICE_ROOT / "full" / a / "carbs.json"))
        if not c: continue
        ct = L._mins(to_local(pd.to_datetime([x["startDate"] for x in c], utc=True), off))
        gr = [float(x.get("grams") or 0) for x in c]          # the key is `grams`; `carbInput` read 0 and filtered all
        o_ = np.argsort(ct); ct = ct[o_]; gr = [gr[i] for i in o_]   # keep grams paired with their own time
        s = pd.read_parquet(L.ICE_ROOT / "steps" / f"{a}.parquet", columns=["t1", "bg1"])
    except Exception:
        continue
    t = L._mins(to_local(s.t1, off)); g = pd.Series(s.bg1.to_numpy(float)).interpolate(limit=3).to_numpy()
    for t0, gm in zip(ct, gr):
        if gm < 20: continue
        i = int(np.searchsorted(t, t0))
        if i < 1 or i + 49 >= len(t) or t[i + 48] - t[i] > 260: continue
        r_ = shape(g[i:i + 49])
        if r_: don.append(dict(r_, fam=FAM.get(a, "?")))
print("== DONORS (carb entries >= 20 g), by sensor family")
_D = pd.DataFrame(don)
for _f, _g in _D.groupby("fam"):
    if len(_g) < 200: continue
    print(f"   {_f:12s} n{len(_g):6d}  rise {_g.rise1.median():5.1f}  fall after peak {_g.fall.median():5.1f}"
          f"  2nd rise {_g.rise2.median():5.1f}")
show("donors ALL", don)
for run in sys.argv[1:]:
    R = []
    for p in sorted(Path(run).glob("v0*")):
        tr = pickle.load(open(p / "truth.pkl", "rb")); c = tr["cgm"].dropna(); c = c[c.index >= 2880]
        t = c.index.to_numpy(float); g = c.to_numpy(float)
        for e in tr["entries"]:
            if e[1] < 20: continue
            i = int(np.searchsorted(t, e[0]))
            if i < 1 or i + 49 >= len(t) or t[i + 48] - t[i] > 260: continue
            R.append(shape(g[i:i + 49]))
    print(f"== {Path(run).name}"); show(Path(run).name, R)
