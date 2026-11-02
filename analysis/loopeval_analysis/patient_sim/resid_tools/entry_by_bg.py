"""Carb entries by the glucose they were made at, donors vs twins, one definition both sides. `entry_win` matches the
donors' entries PER DAY, but the post-meal fall / rise ratio is pooled over meals, so the BAND MIX decides how much
of the pooled gap is composition: an unbolused meal has the donors' lowest ratio (0.62 against 0.79 at the meal,
L 575), so a twin that under-enters at high glucose reads low on the pooled ratio with identical physiology.
    python entry_by_bg.py <run> [...]"""
import sys, pickle, glob, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path.home() / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L
BANDS = [(0, 80), (80, 120), (120, 180), (180, 1000)]
LAB = ["<80", "80-120", "120-180", ">180"]

def show(lab, per_day, sizes, n):
    tot = sum(per_day)
    print(f"  {lab:>9} n{n:6d}  entries/day {tot:5.2f}  " +
          "  ".join(f"{k} {v:4.2f} ({s:2.0f}g, {v/tot*100:2.0f}%)" for k, v, s in zip(LAB, per_day, sizes)))

rows = []
for a in sorted({p.stem for p in (L.ICE_ROOT / "steps").glob("*.parquet")}):
    try:
        s = pd.read_parquet(L.ICE_ROOT / "steps" / f"{a}.parquet", columns=["t1", "bg1", "carbs_g"])
    except Exception:
        continue
    c = s.carbs_g.fillna(0).to_numpy(float); g = s.bg1.to_numpy(float)
    days = len(s) * 5 / 1440.0
    if days < 20: continue
    m = (c > 0) & np.isfinite(g)
    if m.sum() < 30: continue
    rows.append([[(m & (g >= lo) & (g < hi)).sum() / days for lo, hi in BANDS],
                 [float(np.median(c[m & (g >= lo) & (g < hi)])) if (m & (g >= lo) & (g < hi)).sum() > 3 else np.nan
                  for lo, hi in BANDS], int(m.sum())])
P = np.array([r[0] for r in rows]); S = np.array([r[1] for r in rows])
print(f"donors ({len(rows)} with >= 30 entries and >= 20 days):")
show("donors", np.median(P, axis=0), np.nanmedian(S, axis=0), int(sum(r[2] for r in rows)))

for run in sys.argv[1:]:
    pp, ss, n = [], [], 0
    for p in sorted(Path(run).glob("v*/truth.pkl")):
        try: d = pickle.load(open(p, "rb"))
        except Exception: continue
        cgm = d["cgm"]; ci = np.asarray(cgm.index, float); cv = cgm.to_numpy(float)
        bg, gm = [], []
        for e in d["entries"]:
            k = int(np.clip(np.searchsorted(ci, e[0]), 0, len(cv) - 1))
            if np.isfinite(cv[k]): bg.append(cv[k]); gm.append(e[1])
        if len(bg) < 5: continue
        bg = np.array(bg); gm = np.array(gm); n += len(bg)
        days = 12.0                                    # 14-day window less the 2-day burn-in
        pp.append([((bg >= lo) & (bg < hi)).sum() / days for lo, hi in BANDS])
        ss.append([float(np.median(gm[(bg >= lo) & (bg < hi)])) if ((bg >= lo) & (bg < hi)).sum() > 2 else np.nan
                   for lo, hi in BANDS])
    if pp: show(Path(run).name, np.median(np.array(pp), axis=0), np.nanmedian(np.array(ss), axis=0), n)
