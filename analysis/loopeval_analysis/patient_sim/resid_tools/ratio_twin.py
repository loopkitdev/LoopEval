"""The twins' post-meal fall / rise ratio and BOLUS-TIMING distribution, on the donors' strata (L 575). If the twins
bolus later or eat larger meals than their donors, the ratio deficit is behaviour reproduction, not physiology.

The donors' strata count AUTOMATIC boluses too (`ratio_by.py` uses bolus_manual_u + bolus_auto_u), so the twin side
must as well — which rules out `truth["bolus_requests"]` (the person's own requests only). Boluses come instead from
`trace.json`'s tagged `delivery[]`, NOT from a threshold on `truth["delivered"]`: that threshold over-counts the
share of meals with no bolus nearby (0.14 against 0.05, L 575) and "none" is the lowest-ratio stratum, so it
manufactures a mix artifact in the one statistic being measured.
    python ratio_twin.py <run> [...]"""
import sys, pickle, numpy as np, pandas as pd
from pathlib import Path

for run in sys.argv[1:]:
    rows = []
    for p in sorted(Path(run).glob("v0*")):
        tr = pickle.load(open(p / "truth.pkl", "rb"))
        c = tr["cgm"].dropna(); c = c[c.index >= 2880]
        t = c.index.to_numpy(float); g = c.to_numpy(float)
        T = tr["truth"]; mt = T.m.to_numpy(float)
        import json
        try:
            d_ = json.load(open(p / "trace.json")).get("delivery", [])
        except Exception:
            continue
        m0 = float(T.m.min())
        EP = pd.Timestamp("2026-01-05", tz="UTC")   # world.EPOCH; entry minutes are measured from it
        bt = np.sort(np.array([ (pd.Timestamp(x["t"]).tz_convert("UTC") - EP).total_seconds() / 60.0
                                for x in d_ if x.get("kind") == "bolus" and float(x.get("amountU") or 0) > 0.05 ]))
        for e in tr["entries"]:
            t0, gm = e[0], e[1]
            if gm < 20: continue
            i = int(np.searchsorted(t, t0))
            if i < 1 or i + 49 >= len(t): continue
            seg = g[i:i + 49]
            if np.isnan(seg).any(): continue
            k = int(np.argmax(seg[:30]))
            if k < 3: continue
            rise = float(seg[k] - seg[0]); fall = float(seg[k] - np.min(seg[k:min(k + 18, len(seg))]))
            if rise < 20: continue
            lo_, hi_ = np.searchsorted(bt, [t0 - 60, t0 + 60])      # tagged boluses within +/-60 min of the entry
            off = float(min(bt[lo_:hi_] - t0, key=abs)) if hi_ > lo_ else np.nan
            rows.append(dict(grams=gm, rise=rise, fall=fall, ratio=fall / rise, bol_off=off))
    D = pd.DataFrame(rows)
    print(f"== {Path(run).name}: {len(D)} meals >= 20 g with a rise >= 20; median ratio {D.ratio.median():.2f}"
          f"  (ratio of medians {D.fall.median() / D.rise.median():.2f})")
    print(f"   bolus-timing SHARES  pre(-60,-5] {((D.bol_off > -60) & (D.bol_off <= -5)).mean():.2f}"
          f"   at(-5,5] {((D.bol_off > -5) & (D.bol_off <= 5)).mean():.2f}"
          f"   late(5,60] {((D.bol_off > 5) & (D.bol_off <= 60)).mean():.2f}"
          f"   none {D.bol_off.isna().mean():.2f}")
    print("   donors' shares      pre 0.07   at 0.74   late 0.15   none 0.03")
    for lo, hi, lab in ((-60, -5, "pre"), (-5, 5, "at"), (5, 60, "late")):
        gg = D[(D.bol_off > lo) & (D.bol_off <= hi)]
        if len(gg) < 60: continue
        print(f"     {lab:5s} n{len(gg):5d}  rise {gg.rise.median():5.1f}  fall {gg.fall.median():5.1f}  ratio {gg.ratio.median():.2f}")
    print(f"   meal size p50 {D.grams.median():.0f} g  (donors 35)")
