"""Is the post-meal fall partly SENSOR-made? Every body lever is eliminated (L 575), so compare the twins' TRUE
glucose fall after a meal peak with their own CGM's. If CGM ~= truth, our sensor does not exaggerate falls and the
donors' steeper CGM fall may be partly theirs — the false-lows trap of L 393, 498, in the meal window.
    python true_vs_cgm.py <run> [...]"""
import sys, pickle, numpy as np, pandas as pd
from pathlib import Path

def shape(t, g, ent):
    out = []
    for t0, gm in ent:
        if gm < 20: continue
        i = int(np.searchsorted(t, t0))
        if i < 1 or i + 49 >= len(t): continue
        seg = g[i:i + 49]
        if np.isnan(seg).any(): continue
        k = int(np.argmax(seg[:30]))
        if k < 3: continue
        out.append(dict(rise=float(seg[k] - seg[0]),
                        fall=float(seg[k] - np.min(seg[k:min(k + 18, len(seg))]))))
    return out

for run in sys.argv[1:]:
    C, T = [], []
    for p in sorted(Path(run).glob("v0*")):
        tr = pickle.load(open(p / "truth.pkl", "rb"))
        c = tr["cgm"].dropna(); c = c[c.index >= 2880]
        ent = [(e[0], e[1]) for e in tr["entries"]]
        C += shape(c.index.to_numpy(float), c.to_numpy(float), ent)
        tt = tr["truth"]
        m = tt.m.to_numpy(float); bg = tt.bg.to_numpy(float)
        sel = m >= 2880
        m5 = m[sel][::5]; b5 = bg[sel][::5]        # truth is per minute; sample to the CGM's 5-min grid
        T += shape(m5, b5, ent)
    dc, dt_ = pd.DataFrame(C), pd.DataFrame(T)
    print(f"== {Path(run).name}")
    print(f"   CGM   n{len(dc):5d}  rise {dc['rise'].median():5.1f}  fall after peak {dc['fall'].median():5.1f}")
    print(f"   TRUTH n{len(dt_):5d}  rise {dt_['rise'].median():5.1f}  fall after peak {dt_['fall'].median():5.1f}")
