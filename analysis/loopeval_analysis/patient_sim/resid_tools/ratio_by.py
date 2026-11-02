"""The donors' own post-meal fall / rise RATIO by meal size, clock hour, bolus timing and insulin type (L 575). The
twins sit at 0.70-0.78 against the donors' 0.89 and the ratio is invariant to every body lever, so the question is
what the ratio varies with IN THE DONORS. If it tracks bolus TIMING the cause is dosing behaviour, not physiology.
    python ratio_by.py"""
import sys, json, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path.home() / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L
from loopeval_analysis.patient_sim.quiet import local_offset, to_local

T = pd.read_csv(Path.home() / ".loop-eval/runs/2026-10-15-additive-templates/templates_pilot.csv")
INS = T.set_index("alias")[[c for c in T.columns if "insulin" in c.lower()][0]].to_dict() if any("insulin" in c.lower() for c in T.columns) else {}
rows = []
for a in sorted({p.stem for p in (L.ICE_ROOT / "steps").glob("*.parquet")}):
    try:
        off = local_offset(a, L.ICE_ROOT)
        c = json.load(open(L.ICE_ROOT / "full" / a / "carbs.json"))
        if not c: continue
        ct = L._mins(to_local(pd.to_datetime([x["startDate"] for x in c], utc=True), off))
        gr = np.array([float(x.get("grams") or 0) for x in c]); o = np.argsort(ct); ct, gr = ct[o], gr[o]
        s = pd.read_parquet(L.ICE_ROOT / "steps" / f"{a}.parquet",
                            columns=["t1", "bg1", "bolus_manual_u", "bolus_auto_u"])
    except Exception:
        continue
    t = L._mins(to_local(s.t1, off))
    g = pd.Series(s.bg1.to_numpy(float)).interpolate(limit=3).to_numpy()
    bol = (s.bolus_manual_u.fillna(0) + s.bolus_auto_u.fillna(0)).to_numpy(float)
    for t0, gm in zip(ct, gr):
        if gm < 20: continue
        i = int(np.searchsorted(t, t0))
        if i < 1 or i + 49 >= len(t) or t[i + 48] - t[i] > 260: continue
        seg = g[i:i + 49]
        if np.isnan(seg).any(): continue
        k = int(np.argmax(seg[:30]))
        if k < 3: continue
        rise = float(seg[k] - seg[0]); fall = float(seg[k] - np.min(seg[k:min(k + 18, len(seg))]))
        if rise < 20: continue                        # a ratio needs a real rise
        j0, j1 = np.searchsorted(t, [t0 - 60, t0 + 60])
        w = bol[j0:j1]
        off_m = float(t[j0 + int(np.argmax(w))] - t0) if len(w) and w.max() > 0.2 else np.nan
        rows.append(dict(alias=a, grams=gm, hour=int((t0 % 1440) // 60), rise=rise, fall=fall,
                         ratio=fall / rise, bol_off=off_m, ins=INS.get(a, "?")))
D = pd.DataFrame(rows)
print(f"{len(D)} donor meals >= 20 g with a rise >= 20 mg/dL, {D.alias.nunique()} donors; overall ratio {D.ratio.median():.2f}")
def by(col, bins, lab):
    print(f"\n  by {lab}:")
    B = pd.cut(D[col], bins) if bins is not None else D[col]
    for k, gg in D.groupby(B, observed=True):
        if len(gg) < 150: continue
        print(f"    {str(k):16s} n{len(gg):6d}  rise {gg.rise.median():5.1f}  fall {gg.fall.median():5.1f}  ratio {gg.ratio.median():.2f}")
by("grams", [20, 35, 50, 75, 400], "meal size (g)")
by("hour", [0, 6, 11, 15, 20, 24], "clock hour")
by("bol_off", [-60, -20, -5, 5, 20, 60], "bolus offset from the entry (min)")
print("\n  meals with NO bolus within +/-60 min:", int(D.bol_off.isna().sum()),
      f" ratio {D[D.bol_off.isna()].ratio.median():.2f}" if D.bol_off.isna().sum() > 150 else "")
