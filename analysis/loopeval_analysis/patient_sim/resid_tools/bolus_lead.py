"""The post-meal fall / rise ratio tracks BOLUS TIMING hard — 0.90 pre-bolused 20-60 min, 0.79 at the meal, 0.68 late,
0.62 unbolused, a spread of 0.28 against the twins' 0.11-0.19 deficit (L 575). So before any time-asymmetric
mechanism is built, check the like-for-like question: do the twins' meals carry their donors' DISTRIBUTION of bolus
timing? `bolus_lead_min` is a per-donor trait, but the realized lead is what shapes the meal, and a mix shifted a few
minutes late reproduces the whole deficit with identical physiology.

Measures, on both sides with one definition: for each carb entry >= 20 g, the minutes from the nearest bolus to the
entry (negative = bolused BEFORE the entry), and the share in each of L 575's timing strata.
    python bolus_lead.py <run> [...]"""
import sys, pickle, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path.home() / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L
DAY = 1440.0
STRATA = [("pre 20-60 min", -60, -20), ("pre 0-20 min", -20, -1), ("at the meal", -1, 15),
          ("late 15-60 min", 15, 60), ("none within 60", None, None)]

def strata_shares(lead):
    """lead: minutes from bolus to entry, NaN where no bolus within 60 min."""
    out = {}
    n = len(lead)
    for lab, lo, hi in STRATA:
        if lo is None:
            out[lab] = float(np.mean(~np.isfinite(lead)))
        else:
            out[lab] = float(np.mean(np.isfinite(lead) & (lead >= lo) & (lead < hi)))
    return out, n

def report(lab, lead):
    sh, n = strata_shares(np.asarray(lead, float))
    fin = np.asarray(lead, float); fin = fin[np.isfinite(fin)]
    print(f"  {lab:14s} n{n:6d}  median lead {np.median(fin):+6.1f} min  " +
          "  ".join(f"{k} {v:.2f}" for k, v in sh.items()))

# ---- donors: carb entries vs manual boluses, from the ice steps
don = []
for a in sorted({p.stem for p in (L.ICE_ROOT / "steps").glob("*.parquet")}):
    try:
        s = pd.read_parquet(L.ICE_ROOT / "steps" / f"{a}.parquet",
                            columns=["t1", "carbs_g", "bolus_manual_u", "bolus_auto_u"])
    except Exception:
        continue
    s = s.sort_values("t1").reset_index(drop=True)
    t = L._mins(s.t1)
    ent = t[(s.carbs_g.fillna(0) >= 20).to_numpy()]
    bol = t[(s.bolus_manual_u.fillna(0) > 0.05).to_numpy()]
    if len(ent) == 0 or len(bol) == 0: continue
    b = np.sort(np.asarray(bol, float))
    for e in np.asarray(ent, float):
        k = np.searchsorted(b, e)
        cand = [b[i] - e for i in (k - 1, k) if 0 <= i < len(b)]
        cand = [c for c in cand if -60 <= c < 60]
        don.append(min(cand, key=abs) if cand else np.nan)
print(f"donors ({len(don)} entries >= 20 g):")
report("donors", don)

# ---- twins: the same, from the person's own entries and bolus requests
for run in sys.argv[1:]:
    lead = []
    for p in sorted(Path(run).glob("v*/truth.pkl")):
        try: d = pickle.load(open(p, "rb"))
        except Exception: continue
        en = d.get("entries"); br = d.get("bolus_requests")
        if en is None or br is None: continue
        # entries are (minute, grams, absorption) tuples; bolus_requests are (minute, f) tuples
        ent = np.array([float(x[0]) for x in en if float(x[1]) >= 20])
        # bolus_requests: (minute, f) with + = ratio of Loop's recommendation, - = absolute units (L 575 trap)
        B = np.array([float(x[0]) for x in br if (x[1] > 0 or x[1] <= -0.05)]) if len(br) else np.array([])
        if not len(ent) or not len(B): continue
        B = np.sort(B)
        for e in ent:
            k = np.searchsorted(B, e)
            cand = [B[i] - e for i in (k - 1, k) if 0 <= i < len(B)]
            cand = [c for c in cand if -60 <= c < 60]
            lead.append(min(cand, key=abs) if cand else np.nan)
    if lead: report(Path(run).name, lead)
