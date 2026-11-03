"""The twins' TDD day-to-day structure BY LIMB, to finish the `ac1` thread (L 583, 584). The donors' persistence is
in BOTH limbs and their BASAL carries most of it (37% of TDD, within-13-day lag-1 from `tdd_blocks.py`), while all
four mechanisms tried against `ac1` acted on meals, activity or the residual and none touched basal. If the twins'
basal is near-constant day to day, that is the defect; if it already varies as the donors' does, `ac1` is not a
basal story and the limit stands as documented.

Measured like for like with `tdd_blocks.py`'s "within 13d" column, never its long-record column (L 585: slow drift
inflates a long-record lag-1 and the twins only run 14 days). Basal is reconstructed as a per-minute ASSIGNMENT,
last writer wins, exactly as `tdd_parts.py` does it — accumulating overlapping temp records inflates it — and
boluses come from the tagged `delivery[]` stream, never a threshold on `truth["delivered"]` (L 575).

    python twin_limb_ac.py <run> [...]
"""
import json, sys, numpy as np, pandas as pd
from pathlib import Path

EP = pd.Timestamp("2026-01-05", tz="UTC")       # world.EPOCH
DAY = 1440.0


def ac(x):
    x = np.asarray(x, float)
    return np.corrcoef(x[:-1], x[1:])[0, 1] if len(x) > 3 and x.std() > 0 else np.nan


def per_day(path):
    """Daily basal / bolus units for one twin, or None."""
    try:
        dl = json.load(open(path)).get("delivery", [])
    except Exception:
        return None
    segs, bol = [], []
    for x in dl:
        if x.get("source") not in (None, "candidate"):
            continue
        if x.get("kind") == "basal":
            try:
                t0 = pd.Timestamp(x["t"]).tz_convert("UTC")
                t1 = pd.Timestamp(x.get("tEnd", x["t"])).tz_convert("UTC")
            except Exception:
                continue
            segs.append(((t0 - EP).total_seconds() / 60.0, (t1 - EP).total_seconds() / 60.0,
                         max(float(x.get("rateUhr") or 0.0), 0.0)))
        elif x.get("kind") == "bolus":
            u = float(x.get("amountU") or 0.0)
            if u <= 0:
                continue
            try:
                t0 = pd.Timestamp(x["t"]).tz_convert("UTC")
            except Exception:
                continue
            bol.append(((t0 - EP).total_seconds() / 60.0, u))
    if not segs:
        return None
    segs.sort()
    lo_ = int(segs[0][0])
    hi_ = int(max(e for _, e, _ in segs)) + 1
    rate = np.zeros(max(hi_ - lo_, 1))                      # U/hr per minute, last writer wins
    for s_, e_, r_ in segs:
        i0, i1 = int(s_) - lo_, int(e_) - lo_
        if i1 > i0:
            rate[max(i0, 0):min(i1, len(rate))] = r_
    mins = np.arange(lo_, lo_ + len(rate))
    d = (mins // DAY).astype(int)
    bas = pd.Series(rate / 60.0).groupby(d).sum()           # U per day
    bb = pd.Series({k: 0.0 for k in bas.index})
    for t_, u in bol:
        k = int(t_ // DAY)
        if k in bb.index:
            bb[k] += u
    g = pd.DataFrame(dict(bas=bas, bol=bb)).sort_index()
    g = g[(g.bas + g.bol) > 5]                              # drop partial days, as the donor side does
    return g if len(g) >= 8 else None


print(f"{'arm':>12} {'n':>5} {'basal share':>12} "
      f"{'CV bas':>8} {'CV bol':>8} {'ac bas':>8} {'ac bol':>8} {'ac TOTAL':>9}")
for run in sys.argv[1:]:
    rows = []
    for p in sorted(Path(run).glob("v*/trace.json")):
        g = per_day(p)
        if g is None:
            continue
        tot = g.bas + g.bol
        rows.append(dict(share=g.bas.sum() / tot.sum(),
                         cv_bas=g.bas.std() / g.bas.mean() if g.bas.mean() > 0 else np.nan,
                         cv_bol=g.bol.std() / g.bol.mean() if g.bol.mean() > 0 else np.nan,
                         ac_bas=ac(g.bas), ac_bol=ac(g.bol), ac_tot=ac(tot)))
    if not rows:
        print(f"{Path(run).name:>12}   no trace.json with delivery[]")
        continue
    R = pd.DataFrame(rows)
    print(f"{Path(run).name:>12} {len(R):>5} {R.share.median():>12.2f} "
          f"{R.cv_bas.median():>8.3f} {R.cv_bol.median():>8.3f} "
          f"{R.ac_bas.median():>+8.3f} {R.ac_bol.median():>+8.3f} {R.ac_tot.median():>+9.3f}")
print("\nDonor side: run tdd_blocks.py and read its 'within 13d' column (NOT the long record, L 585).")
