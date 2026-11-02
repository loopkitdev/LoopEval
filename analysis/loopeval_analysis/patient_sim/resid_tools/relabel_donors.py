"""The donors' stored pulse labels are STALE: they predate `ice_gen.meals.fit_shapes` (commit ece70cb1), so their
`peak_h` is the raw 5-min argmax and their `dur_h` the run length, while the twins' labels — produced by the
current `label()`, which calls `fit_shapes` — carry the fitted lognormal mode and the fitted 90th percentile.
`pulse_peak_h` and `pulse_dur_h` therefore compare two different quantities (L 625). Signature: 100% of donor
peak_h values are exact multiples of 5 min and 0% are `FIT_MODES` grid cells; the twins are the other way round.

This re-runs the CURRENT labeller on a sample of donors and prints both quantities side by side, so the size of
the mismatch is measured rather than assumed.

    python relabel_donors.py [n_donors]
"""
import json, sys, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path.home() / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L
from loopeval_analysis.ice_gen import meals as M

N = int(sys.argv[1]) if len(sys.argv) > 1 else 12
ROOT = L.ICE_ROOT
P = pd.read_csv(ROOT / "persons.csv").set_index("alias")
BD = pd.read_parquet(ROOT / "bolus_decisions.parquet")

rows = []
for a in list(P.index)[:N]:
    sp = ROOT / "steps" / f"{a}.parquet"
    cp = ROOT / "full" / a / "carbs.json"
    mp = ROOT / "meals" / f"{a}.parquet"
    if not (sp.exists() and cp.exists() and mp.exists()):
        continue
    try:
        steps = pd.read_parquet(sp)
        carbs = json.load(open(cp))
        bd = BD[BD.alias == a].copy()
        tdd = float(P.tdd[a]); isf = float(P.isf_tdd[a])
        new, _, _ = M.label(steps, carbs, bd, tdd, isf)
        old = pd.read_parquet(mp)
    except Exception as e:
        print(f"  {a}: {type(e).__name__}: {e}")
        continue
    o = old[~old.rescue.astype(bool)] if "rescue" in old.columns else old
    n = new[~new.rescue.astype(bool)]
    if not len(o) or not len(n):
        continue
    rows.append(dict(alias=a, n_old=len(o), n_new=len(n),
                     pk_old=o.peak_h.median(), pk_new=n.peak_h.median(),
                     du_old=o.dur_h.median(), du_new=n.dur_h.median(),
                     run_new=n.run_h.median() if "run_h" in n.columns else np.nan,
                     sz_old=o.size_g.median(), sz_new=n.size_g.median()))

R = pd.DataFrame(rows)
if R.empty:
    print("no donors re-labelled")
    raise SystemExit
print(f"{len(R)} donors re-labelled with the CURRENT labeller "
      f"(pulses: stored {R.n_old.sum()}, re-labelled {R.n_new.sum()})\n")
print(f"{'quantity':>26} {'stored (scored)':>16} {'current labeller':>17}")
print(f"{'pulse_peak_h  (median)':>26} {R.pk_old.median():>16.3f} {R.pk_new.median():>17.3f}")
print(f"{'pulse_dur_h   (median)':>26} {R.du_old.median():>16.3f} {R.du_new.median():>17.3f}")
print(f"{'  ... run length (run_h)':>26} {'':>16} {R.run_new.median():>17.3f}")
print(f"{'size_g        (median)':>26} {R.sz_old.median():>16.3f} {R.sz_new.median():>17.3f}")
print(f"\nThe twins' scored values, for reference: pulse_peak_h 0.622, pulse_dur_h 1.885 (rf2).")
print("If the donors' CURRENT-labeller peak sits near the twins' 0.622, the scored gap is a definition")
print("artifact, not a body difference.")
print(f"\nper donor: {', '.join(f'{r.alias} {r.pk_old:.2f}->{r.pk_new:.2f}' for _, r in R.iterrows())}")
