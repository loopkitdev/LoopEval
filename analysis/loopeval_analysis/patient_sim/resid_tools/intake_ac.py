"""Is intake_rho 0.29 actually producing day-to-day persistence in the twins' eating? If an enabled, evidenced
mechanism is not reaching the daily totals, that is a bug, not a missing factor (L 583).
    python intake_ac.py <run> [...]"""
import sys, pickle, numpy as np
from pathlib import Path
DAY = 1440.0
for run in sys.argv[1:]:
    ac_c, ac_t = [], []
    for p in sorted(Path(run).glob("v0*")):
        tr = pickle.load(open(p / "truth.pkl", "rb"))
        # daily EATEN carbohydrate from the behaviour log (true eating, all kinds)
        g = {}
        for e in tr["behavior"]:
            if e[1] in ("meal", "snack", "graze") and isinstance(e[2], (int, float)):
                d = int(e[0] // DAY)
                if e[0] >= 2880: g[d] = g.get(d, 0.0) + float(e[2])
        ks = sorted(g)
        if len(ks) < 8: continue
        x = np.array([g[k] for k in ks])
        if x.std() > 0: ac_c.append(np.corrcoef(x[:-1], x[1:])[0, 1])
        # daily delivered insulin
        T = tr["truth"]; mt = T.m.to_numpy(float); dv = T.delivered.to_numpy(float)
        sel = mt >= 2880
        dd = {}
        for m_, v_ in zip(mt[sel], dv[sel]): dd[int(m_ // DAY)] = dd.get(int(m_ // DAY), 0.0) + float(v_)
        kt = sorted(dd); y = np.array([dd[k] for k in kt])
        if len(y) >= 8 and y.std() > 0: ac_t.append(np.corrcoef(y[:-1], y[1:])[0, 1])
    print(f"== {Path(run).name}  n{len(ac_c)} people")
    print(f"   daily CARBS  lag-1 ac: median {np.median(ac_c):+.3f}   (intake_rho is 0.29; independent-day null ~-0.09)")
    print(f"   daily INSULIN lag-1 ac: median {np.median(ac_t):+.3f}   (the donors' TDD row is +0.091)")
