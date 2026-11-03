"""How many low-side eating events does ONE low episode produce? Neither the firing threshold (`pro_onset`) nor the
refractory sets the twins' low-side eating rate (L 588): a 20 mg/dL onset shift cut it 17% and doubled the tier-1 gap,
and the refractory never binds at ~1 event per hour below 80. What is left is events per EPISODE — the proactive
snack, the rescue on its 20-min gate and the retreat at `p_retreat` 0.34 can all fire inside one excursion.

An episode is a contiguous run below 80 mg/dL (joined across gaps of up to 15 min, since a treatment lifts glucose
briefly). Labelled pulses on both sides, since `meals_labeled.csv` is the same labeller as the donors' table.
    python per_episode.py <run> [...]"""
import sys, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path.home() / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L
THR, JOIN = 80.0, 15.0

def episodes(t, g):
    """[(start, end)] of contiguous runs below THR, joined across gaps shorter than JOIN minutes."""
    below = np.isfinite(g) & (g < THR)
    if not below.any(): return []
    idx = np.flatnonzero(below)
    cuts = np.flatnonzero(np.diff(t[idx]) > JOIN)
    out, s = [], 0
    for c in list(cuts) + [len(idx) - 1]:
        out.append((t[idx[s]], t[idx[c]])); s = c + 1
    return out

def report(lab, n_ep, per, share2):
    print(f"  {lab:>9} episodes {n_ep:6d}   events per episode  mean {np.mean(per):.2f}  median {np.median(per):.1f}"
          f"   share with >= 2 events {share2:.2f}   share with 0 {np.mean(np.asarray(per) == 0):.2f}")

rows, nep = [], 0
for a in sorted({p.stem for p in (L.ICE_ROOT / "steps").glob("*.parquet")}):
    mp = L.ICE_ROOT / "meals" / f"{a}.parquet"
    if not mp.exists(): continue
    try:
        s = pd.read_parquet(L.ICE_ROOT / "steps" / f"{a}.parquet", columns=["t1", "bg1"])
        M = pd.read_parquet(mp)
    except Exception:
        continue
    if "onset" not in M.columns or len(M) < 20: continue
    t = np.asarray(L._mins(s.t1), float); g = s.bg1.to_numpy(float)
    ons = np.asarray(L._mins(pd.to_datetime(M.onset, utc=True)), float)
    for s0, e0 in episodes(t, g):
        rows.append(int(((ons >= s0 - 20) & (ons <= e0 + 20)).sum())); nep += 1
R = np.array(rows)
print(f"donors: a low episode is a run below {THR:.0f} joined across < {JOIN:.0f} min gaps")
report("donors", nep, R, float(np.mean(R >= 2)))

for run in sys.argv[1:]:
    per, nep = [], 0
    for p in sorted(Path(run).glob("v*/meals_labeled.csv")):
        try:
            M = pd.read_csv(p)
            import pickle
            d = pickle.load(open(p.parent / "truth.pkl", "rb"))
        except Exception:
            continue
        cgm = d["cgm"].dropna(); t = np.asarray(cgm.index, float); g = cgm.to_numpy(float)
        u = t >= 2880; t, g = t[u], g[u]
        if "onset" not in M.columns or len(M) < 3: continue
        on = pd.to_datetime(M.onset, utc=True, errors="coerce")
        EP = pd.Timestamp("2026-01-05", tz="UTC")
        ons = ((on - EP).dt.total_seconds() / 60.0).to_numpy(float)
        for s0, e0 in episodes(t, g):
            per.append(int(((ons >= s0 - 20) & (ons <= e0 + 20)).sum())); nep += 1
    if per: report(Path(run).name, nep, per, float(np.mean(np.asarray(per) >= 2)))
