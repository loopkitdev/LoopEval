"""Are the donors' Temporary Overrides attached to the events the model attaches them to? Every non-reactive override
in the model is planned against an activity episode or a carb entry, so a donor who overrides more often than they eat
or exercise cannot be reproduced (twins run 2.0 windows / 3.3 h per 14 days against the donors' 6.0 / 13.5). This
measures the share of donor override windows with NO carb entry nearby, and their duration, which is the rate and
length a standalone class would need.
    python ovr_standalone.py"""
import json, sys, numpy as np, pandas as pd
from pathlib import Path
FULL = Path.home() / ".loop-eval/ice_v32/full"
rows = []
for a in sorted(p.name for p in FULL.iterdir() if (p / "therapy.json").exists()):
    try:
        th = json.load(open(FULL / a / "therapy.json"))
        cb = json.load(open(FULL / a / "carbs.json"))
    except Exception:
        continue
    w = th.get("overrideWindows") or []
    if not w or not cb: continue
    t = pd.to_datetime([x["start"] for x in w], utc=True, format="mixed")
    e = pd.to_datetime([x["end"] for x in w], utc=True, format="mixed")
    dur = np.array((e - t).total_seconds()) / 60.0
    keep = dur > 30
    if keep.sum() == 0: continue
    ct = pd.to_datetime([x["startDate"] for x in cb], utc=True, format="mixed").sort_values()
    ts = t[keep].sort_values()
    k = np.searchsorted(ct.values, ts.values)
    near = np.full(len(ts), np.inf)
    for j, (i, s_) in enumerate(zip(k, ts.values)):
        for ii in (i - 1, i):
            if 0 <= ii < len(ct):
                near[j] = min(near[j], abs((ct.values[ii] - s_) / np.timedelta64(1, "m")))
    d2 = dur[keep][np.argsort(t[keep].values)]
    alone = near > 120
    f = float(w[0].get("factor") or np.nan)
    rows.append(dict(alias=a, n=int(keep.sum()), alone=float(alone.mean()),
                     h_alone=float(np.median(d2[alone]) / 60) if alone.any() else np.nan,
                     h_near=float(np.median(d2[~alone]) / 60) if (~alone).any() else np.nan,
                     long_share=float(np.mean(d2 > 240))))
R = pd.DataFrame(rows)
print(f"{len(R)} donors with overrides >30 min and carb entries")
print(f"  share of windows with NO carb entry within 2 h: median {R.alone.median()*100:.0f}%  mean {R.alone.mean()*100:.0f}%")
print(f"  median duration: standalone {R.h_alone.median():.1f} h   near an entry {R.h_near.median():.1f} h")
print(f"  share of windows longer than 4 h: median {R.long_share.median()*100:.0f}%")
print(f"  a standalone class would need about {R.alone.median()*6:.1f} windows per 14 days (donor median 6.0 total)")
