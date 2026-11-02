"""Where is the donors' TDD day-to-day persistence — basal or bolus? Four twin-side mechanisms are null (L 584), and
the dilution hypothesis says TDD is dominated by components with no day structure. If the donors' BASAL carries the
persistence, the twins' near-constant basal need is the defect; if their BOLUS does, it is meal-related.
    python tdd_decomp.py"""
import sys, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path.home() / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L
from loopeval_analysis.patient_sim.quiet import local_offset, to_local
DAY = 1440.0
rows = []
for a in sorted({p.stem for p in (L.ICE_ROOT / "steps").glob("*.parquet")}):
    try:
        off = local_offset(a, L.ICE_ROOT)
        s = pd.read_parquet(L.ICE_ROOT / "steps" / f"{a}.parquet",
                            columns=["t1", "basal_u", "bolus_auto_u", "bolus_manual_u"])
    except Exception:
        continue
    t = L._mins(to_local(s.t1, off))
    d = (t // DAY).astype(int)
    D = pd.DataFrame(dict(d=d, bas=s.basal_u.fillna(0).to_numpy(float),
                          bol=(s.bolus_auto_u.fillna(0) + s.bolus_manual_u.fillna(0)).to_numpy(float)))
    g = D.groupby("d").sum()
    g = g[(g.bas + g.bol) > 5]                      # drop partial days
    if len(g) < 12: continue
    def ac(x):
        x = np.asarray(x, float)
        return np.corrcoef(x[:-1], x[1:])[0, 1] if x.std() > 0 else np.nan
    tot = g.bas + g.bol
    rows.append(dict(alias=a, n=len(g), bas_share=g.bas.sum() / tot.sum(),
                     ac_bas=ac(g.bas), ac_bol=ac(g.bol), ac_tot=ac(tot),
                     cv_bas=g.bas.std() / g.bas.mean(), cv_bol=g.bol.std() / g.bol.mean()))
R = pd.DataFrame(rows).dropna()
print(f"{len(R)} donors, median {R.n.median():.0f} days each; basal share of TDD {R.bas_share.median():.2f}")
print(f"  day-to-day CV:    basal {R.cv_bas.median():.3f}   bolus {R.cv_bol.median():.3f}")
print(f"  lag-1 autocorr:   basal {R.ac_bas.median():+.3f}   bolus {R.ac_bol.median():+.3f}   TOTAL {R.ac_tot.median():+.3f}")
print(f"  (independent-day null at these lengths is about -0.07; the scored ac1 row reads +0.091)")
