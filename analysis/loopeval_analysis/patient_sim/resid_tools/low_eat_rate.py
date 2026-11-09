"""The twins log 2-3x the donors' carb entries per HOUR SPENT BELOW 80 (0.19-0.26 against 0.084), and match them in
every other glucose band. Two different components could do that: too much low-side EATING (the proactive snack and
the rescue), or too high a LOGGED SHARE of it (`p_log_pro` / `p_log_rescue`, both 0.12). Donor carb entries cannot
separate them — but the ice labeller sees unannounced eating too, so the donors' labelled pulses give the true rate
and `announced` gives the logged share.
    python low_eat_rate.py <run> [...]"""
import sys, pickle, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path.home() / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L
THR = 80.0
rows = []
for a in sorted({p.stem for p in (L.ICE_ROOT / "steps").glob("*.parquet")}):
    mp = L.ICE_ROOT / "meals" / f"{a}.parquet"
    if not mp.exists(): continue
    try:
        s = pd.read_parquet(L.ICE_ROOT / "steps" / f"{a}.parquet", columns=["t1", "bg1"])
        M = pd.read_parquet(mp)
    except Exception:
        continue
    g = s.bg1.to_numpy(float); ok = np.isfinite(g)
    h = float((g[ok] < THR).sum() * 5 / 60.0)
    if h < 1 or len(M) < 20: continue
    low = M[M.bg_onset < THR] if "bg_onset" in M.columns else M.iloc[:0]
    ann = float(low.announced.mean()) if len(low) and "announced" in low.columns else np.nan
    rows.append((len(low) / h, ann, float(low.size_g.median()) if len(low) else np.nan,
                 float(M.announced.mean()) if "announced" in M.columns else np.nan))
D = np.array(rows, dtype=float)
print(f"donors ({len(D)} with a labelled-meal table and >= 1 h below {THR:.0f}):")
print(f"  labelled pulses starting below 80, per hour below 80 : {np.nanmedian(D[:,0]):.3f}")
print(f"  of those, the share ANNOUNCED (logged)               : {np.nanmedian(D[:,1]):.2f}   (all pulses: {np.nanmedian(D[:,3]):.2f})")
print(f"  their median size                                    : {np.nanmedian(D[:,2]):.0f} g")

for run in sys.argv[1:]:
    r = []
    for p in sorted(Path(run).glob("v*/truth.pkl")):
        try: d = pickle.load(open(p, "rb"))
        except Exception: continue
        cgm = d["cgm"].dropna(); ci = np.asarray(cgm.index, float); cv = cgm.to_numpy(float)
        u = ci >= 2880
        h = float((cv[u] < THR).sum() * 5 / 60.0)
        if h < 1: continue
        # the behaviour log is (minute, kind, grams, cgm) but 'proactive' stores the PROJECTION there, so the
        # glucose is read from the CGM series for every kind alike
        eat = [x for x in (d.get("behavior") or []) if len(x) >= 3 and x[1] in ("meal", "proactive", "rescue", "graze")
               and float(x[0]) >= 2880]
        def gat(m):
            k = int(np.clip(np.searchsorted(ci, float(m)), 0, len(cv) - 1))
            return cv[k]
        lowe = [x for x in eat if np.isfinite(gat(x[0])) and gat(x[0]) < THR]
        ent = [e for e in d["entries"] if e[0] >= 2880]
        ei = []
        for e in ent:
            k = int(np.clip(np.searchsorted(ci, e[0]), 0, len(cv) - 1))
            if np.isfinite(cv[k]) and cv[k] < THR: ei.append(e)
        r.append((len(lowe) / h, (len(ei) / len(lowe)) if lowe else np.nan,
                  float(np.median([x[2] for x in lowe])) if lowe else np.nan, len(ei) / h))
    R = np.array(r, dtype=float)
    if not len(R): continue
    print(f"  {Path(run).name:>8} ({len(R)}): TRUE low eating {np.nanmedian(R[:,0]):.3f}/h below 80"
          f"   logged share {np.nanmedian(R[:,1]):.2f}   size {np.nanmedian(R[:,2]):.0f} g"
          f"   -> ENTRIES {np.nanmedian(R[:,3]):.3f}/h (donors 0.084)")
