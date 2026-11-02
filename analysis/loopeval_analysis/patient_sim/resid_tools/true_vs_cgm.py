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

import pandas as _pd
FAM = _pd.read_csv(Path.home() / ".loop-eval/runs/2026-10-15-additive-templates/templates_pilot.csv")[["alias", "sensor"]].set_index("alias").sensor.to_dict()
for run in sys.argv[1:]:
    rows = []
    for p in sorted(Path(run).glob("v0*")):
        tr = pickle.load(open(p / "truth.pkl", "rb"))
        pe = pickle.load(open(p / "person.pkl", "rb"))
        fam = FAM.get(getattr(pe, "template", None), "?")
        c = tr["cgm"].dropna(); c = c[c.index >= 2880]
        ent = [(e[0], e[1]) for e in tr["entries"]]
        for r in shape(c.index.to_numpy(float), c.to_numpy(float), ent): rows.append(dict(r, kind="cgm", fam=fam))
        tt = tr["truth"]; m = tt.m.to_numpy(float); bg = tt.bg.to_numpy(float); sel = m >= 2880
        for r in shape(m[sel][::5], bg[sel][::5], ent): rows.append(dict(r, kind="truth", fam=fam))
    D = pd.DataFrame(rows)
    print(f"== {Path(run).name}")
    for fam, g in D.groupby("fam"):
        cg, tu = g[g.kind == "cgm"], g[g.kind == "truth"]
        if len(cg) < 40: continue
        amp = cg["fall"].median() - tu["fall"].median()
        print(f"   {fam:12s} n{len(cg):5d}  CGM fall {cg['fall'].median():5.1f}  truth {tu['fall'].median():5.1f}"
              f"  sensor adds {amp:+5.1f} ({amp / tu['fall'].median():+.0%})")
