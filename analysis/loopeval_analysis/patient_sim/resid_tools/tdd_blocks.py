"""Donor TDD persistence measured LIKE FOR LIKE with the twins: within 13-day blocks, not over the whole
128-day record. Slow drift (settings eras, seasonal need) inflates a long-record lag-1; the twins run 14 days,
so a long-record +0.30 is not the target they are failing. Also splits the long-record figure into the part
carried by the block means (drift) and the part inside blocks (genuine day-to-day coupling).
    python tdd_blocks.py"""
import sys, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path.home() / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L
from loopeval_analysis.patient_sim.quiet import local_offset, to_local
DAY, B = 1440.0, 13

def ac(x):
    x = np.asarray(x, float)
    return np.corrcoef(x[:-1], x[1:])[0, 1] if len(x) > 3 and x.std() > 0 else np.nan

rows = []
for a in sorted({p.stem for p in (L.ICE_ROOT / "steps").glob("*.parquet")}):
    try:
        off = local_offset(a, L.ICE_ROOT)
        s = pd.read_parquet(L.ICE_ROOT / "steps" / f"{a}.parquet",
                            columns=["t1", "basal_u", "bolus_auto_u", "bolus_manual_u"])
    except Exception:
        continue
    t = L._mins(to_local(s.t1, off))
    D = pd.DataFrame(dict(d=(t // DAY).astype(int), bas=s.basal_u.fillna(0).to_numpy(float),
                          bol=(s.bolus_auto_u.fillna(0) + s.bolus_manual_u.fillna(0)).to_numpy(float)))
    g = D.groupby("d").sum()
    g = g[(g.bas + g.bol) > 5]
    if len(g) < 2 * B: continue
    g = g.sort_index(); g["tot"] = g.bas + g.bol
    g["blk"] = np.arange(len(g)) // B
    # within-block lag-1, averaged over that donor's blocks (the twins' measurement)
    wb = {k: [] for k in ("bas", "bol", "tot")}
    cv = {k: [] for k in ("bas", "bol", "tot")}      # within-block CV: the AMPLITUDE counterpart (L 624)
    dem = {k: [] for k in ("bas", "bol", "tot")}     # blocks demeaned, then pooled: drift removed
    for _, blk in g.groupby("blk"):
        if len(blk) < B: continue
        for k in wb:
            v = blk[k].to_numpy(float)
            wb[k].append(ac(v)); dem[k].append(v - v.mean())
            cv[k].append(v.std() / v.mean() if v.mean() > 0 else float("nan"))
    if not wb["bas"]: continue
    r = dict(alias=a, nday=len(g), nblk=len(wb["bas"]))
    for k in wb:
        r[f"long_{k}"] = ac(g[k])                                  # whole record
        r[f"wblk_{k}"] = np.nanmean(wb[k])                         # inside 13-day blocks
        r[f"pool_{k}"] = ac(np.concatenate(dem[k]))                # drift-removed, pooled
        r[f"cvwb_{k}"] = np.nanmean(cv[k])                         # within-block CV
        r[f"cvlong_{k}"] = g[k].std() / g[k].mean()
    rows.append(r)

R = pd.DataFrame(rows)
print(f"{len(R)} donors, median {R.nday.median():.0f} days / {R.nblk.median():.0f} blocks of {B}")
print(f"{'limb':>6} {'long record':>12} {'within 13d':>12} {'drift-removed':>14}"
      f" | {'CV within':>10} {'CV long':>8}")
for k, lab in (("bas", "basal"), ("bol", "bolus"), ("tot", "TOTAL")):
    print(f"{lab:>6} {R[f'long_{k}'].median():>+12.3f} {R[f'wblk_{k}'].median():>+12.3f} {R[f'pool_{k}'].median():>+14.3f}"
          f" | {R[f'cvwb_{k}'].median():>10.3f} {R[f'cvlong_{k}'].median():>8.3f}")
print("\nThe twins' figures are within-14-day. Compare them with the 'within 13d' column, never the long record.")
print("Twin side: run resid_tools/twin_limb_ac.py on the arm - do NOT hardcode it here (L 624; the figures\n       that used to sit on this line were the superseded dr2 arm's). rf2 / rf2_5k, for reference:\n       basal -0.038 / -0.035   bolus -0.010 / +0.028   total +0.002 / -0.013")
