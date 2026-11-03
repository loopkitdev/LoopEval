"""WHERE the twins' extra insulin goes. L 597: the surplus cannot be fixed by a sensitivity scalar, because the
`resid_m` refit converts any such gain back into insulin — so the question is which limb carries it. Absolute U/day
by basal / automatic bolus / manual bolus, same definition both sides (donors from the ice steps' basal_u,
bolus_auto_u, bolus_manual_u; twins from `trace.json`'s tagged `delivery[]`, never a threshold on `delivered`).
    python tdd_parts.py <run> [...]"""
import json, pickle, sys, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path.home() / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L
EP = pd.Timestamp("2026-01-05", tz="UTC")

def show(lab, B, A, M, n):
    t = B + A + M
    print(f"  {lab:>9} n{n:5d}  TDD {np.median(t):5.1f}   basal {np.median(B):5.1f} ({np.median(B)/np.median(t)*100:2.0f}%)"
          f"   auto-bolus {np.median(A):5.1f}   manual-bolus {np.median(M):5.1f}")

rows = []
for a in sorted({p.stem for p in (L.ICE_ROOT / "steps").glob("*.parquet")}):
    try:
        s = pd.read_parquet(L.ICE_ROOT / "steps" / f"{a}.parquet",
                            columns=["t1", "basal_u", "bolus_auto_u", "bolus_manual_u"])
    except Exception:
        continue
    d = len(s) * 5 / 1440.0
    if d < 20: continue
    rows.append((s.basal_u.fillna(0).sum() / d, s.bolus_auto_u.fillna(0).sum() / d, s.bolus_manual_u.fillna(0).sum() / d))
D = np.array(rows)
print("U/day by limb, medians across people")
show("donors", D[:, 0], D[:, 1], D[:, 2], len(D))

for run in sys.argv[1:]:
    r = []
    for p in sorted(Path(run).glob("v*/trace.json")):
        try: dl = json.load(open(p)).get("delivery", [])
        except Exception: continue
        # basal: per-minute ASSIGNMENT, last writer wins, as validate._record_delivery and the donors' own
        # basal_eff do - accumulating overlapping temp records inflates it (47 U/day against the scored 42)
        auto = man = 0.0
        segs = []
        for x in dl:
            if x.get("source") not in (None, "candidate"): continue
            if x.get("kind") == "basal":
                try:
                    t0 = pd.Timestamp(x["t"]).tz_convert("UTC"); t1 = pd.Timestamp(x.get("tEnd", x["t"])).tz_convert("UTC")
                    segs.append(((t0 - EP).total_seconds() / 60.0, (t1 - EP).total_seconds() / 60.0,
                                 max(float(x.get("rateUhr") or 0.0), 0.0)))
                except Exception: pass
            elif x.get("kind") == "bolus":
                u = float(x.get("amountU") or 0.0)
                if u <= 0: continue
                if x.get("automatic", True): auto += u
                else: man += u
        bas = 0.0
        if segs:
            segs.sort()
            lo_, hi_ = int(segs[0][0]), int(max(e for _, e, _ in segs)) + 1
            rate = np.zeros(max(hi_ - lo_, 1))
            for s_, e_, r_ in segs:
                i0, i1 = int(s_) - lo_, int(e_) - lo_
                if i1 > i0: rate[max(i0, 0):min(i1, len(rate))] = r_
            bas = float(rate.sum()) / 60.0
        # per-day over the stream's OWN span: the run is 14 days and dividing by the 12-day scored window
        # inflated TDD to 47 against the scored 42 (the 13th definition slip of the session)
        if segs:
            span = (max(e for _, e, _ in segs) - min(s_ for s_, _, _ in segs)) / 1440.0
        else:
            span = 12.0
        span = max(span, 1.0)
        if bas + auto + man > 0: r.append((bas / span, auto / span, man / span))
    if r:
        R = np.array(r); show(Path(run).name, R[:, 0], R[:, 1], R[:, 2], len(R))
