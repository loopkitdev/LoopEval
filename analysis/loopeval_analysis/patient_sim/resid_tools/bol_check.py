"""Confirm or refute the twins' unbolused-meal share (L 575): the delivered-stream threshold said 14-17% of meals
>= 20 g had no bolus against the donors' 3%. bolus_requests records USER boluses directly, so it settles whether that
was a detection artifact. Counted per the standing trap: f > 0 is a ratio of Loop's recommendation, f <= -0.05 is
absolute units.
    python bol_check.py <run> [...]"""
import sys, pickle, numpy as np
from pathlib import Path
for run in sys.argv[1:]:
    tot = none_req = none_dlv = 0
    for p in sorted(Path(run).glob("v0*")):
        tr = pickle.load(open(p / "truth.pkl", "rb"))
        req = np.array([t for t, f in tr["bolus_requests"] if f > 0 or f <= -0.05], float)
        T = tr["truth"]; mt = T.m.to_numpy(float); dv = T.delivered.to_numpy(float)
        base = np.median(dv[dv > 0]) if (dv > 0).any() else 0.0
        for e in tr["entries"]:
            t0, gm = e[0], e[1]
            if gm < 20 or t0 < 2880: continue
            tot += 1
            if not len(req) or not ((req > t0 - 60) & (req < t0 + 60)).any(): none_req += 1
            j0, j1 = np.searchsorted(mt, [t0 - 60, t0 + 60])
            w = dv[j0:j1]
            if not (w > max(0.2, 4 * base)).any(): none_dlv += 1
    print(f"== {Path(run).name}: {tot} meals >= 20 g")
    print(f"   no bolus by DELIVERED-stream threshold: {none_dlv/tot:.2f}   by bolus_requests: {none_req/tot:.2f}"
          f"   (donors, from pump records: 0.03)")
