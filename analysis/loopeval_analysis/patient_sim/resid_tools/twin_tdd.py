"""The twins' daily basal and bolus, against the donors' table (L 584: basal share 0.37, day-to-day CV 0.230, lag-1
+0.303). Four null mechanisms all acted on meals / activity / the residual and none touched basal, so this says
whether the twins' basal has the day-to-day structure the donors' has. Uses trace.json's delivery[] stream (the
basal/bolus split), NOT a threshold on truth["delivered"] (L 575's trap).
    python twin_tdd.py <run> [...]"""
import sys, json, numpy as np, pandas as pd
from pathlib import Path
for run in sys.argv[1:]:
    rows = []
    for p in sorted(Path(run).glob("v0*")):
        f = p / "trace.json"
        if not f.exists(): continue
        dl = json.load(open(f)).get("delivery") or []
        rec = [(x["t"], float(x.get("amountU") or 0), x.get("kind")) for x in dl
               if x.get("source") != "field" and x.get("amountU") is not None]
        if not rec: rec = [(x["t"], float(x.get("amountU") or 0), x.get("kind")) for x in dl if x.get("amountU") is not None]
        if not rec: continue
        D = pd.DataFrame(rec, columns=["t", "u", "kind"])
        D["d"] = pd.to_datetime(D.t, utc=True).dt.floor("1D")
        g = D.pivot_table(index="d", columns="kind", values="u", aggfunc="sum").fillna(0.0)
        for c in ("basal", "bolus"):
            if c not in g: g[c] = 0.0
        g = g[(g.basal + g.bolus) > 5]
        if len(g) < 10: continue
        def ac(x):
            x = np.asarray(x, float)
            return np.corrcoef(x[:-1], x[1:])[0, 1] if x.std() > 0 else np.nan
        tot = g.basal + g.bolus
        rows.append(dict(n=len(g), bas_share=g.basal.sum() / tot.sum(),
                         cv_bas=g.basal.std() / max(g.basal.mean(), 1e-9),
                         cv_bol=g.bolus.std() / max(g.bolus.mean(), 1e-9),
                         ac_bas=ac(g.basal), ac_bol=ac(g.bolus), ac_tot=ac(tot)))
    R = pd.DataFrame(rows).dropna()
    print(f"== {Path(run).name}: {len(R)} twins, median {R.n.median():.0f} days")
    print(f"   basal share {R.bas_share.median():.2f} (donors 0.37)")
    print(f"   day-to-day CV:  basal {R.cv_bas.median():.3f} (donors 0.230)   bolus {R.cv_bol.median():.3f} (0.348)")
    print(f"   lag-1 autocorr: basal {R.ac_bas.median():+.3f} (donors +0.303)  bolus {R.ac_bol.median():+.3f} (+0.265)"
          f"  total {R.ac_tot.median():+.3f} (+0.251)")
