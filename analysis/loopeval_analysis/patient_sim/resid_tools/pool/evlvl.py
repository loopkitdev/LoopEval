"""Per-event residual level (LESSONS 527): each event's before arm against the donor's own pre-edit mean (fieldpre_mean),
resid_m += gain x gap, starting from the template's resid_m (or the previous round's eid -> resid_m table).
    python evlvl.py <arm dir> <templates csv> <out evm csv> [<prev evm csv>]"""
import sys, glob, pickle, numpy as np, pandas as pd
from pathlib import Path
HERE = Path.cwd()                  # the change dir
GAIN = 1.2
arm, tpl, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
prev = dict(pd.read_csv(sys.argv[4]).values) if len(sys.argv) > 4 else None
E = pd.read_csv(HERE / "events.csv"); F = pd.read_csv(HERE / "field_and_tools.csv").set_index("eid")
T = pd.read_csv(tpl).set_index("alias")
rows = []
for e in E.itertuples():
    ms = []
    for d in glob.glob(str(arm / f"{e.eid}_before" / "v0*")):
        try: c = pickle.load(open(d + "/truth.pkl", "rb"))["cgm"].dropna()
        except Exception: continue
        ms.append(float(c[c.index >= 2880].mean()))
    if not ms or e.eid not in F.index: continue
    base = prev.get(e.eid) if prev else T.resid_m.get(e.alias, 0.0)
    base = 0.0 if base is None or not np.isfinite(base) else float(base)
    gap = float(F.loc[e.eid, "fieldpre_mean"]) - float(np.mean(ms))
    rows.append(dict(eid=e.eid, resid_m=float(np.clip(base + GAIN * np.clip(gap, -40, 40), -150, 150)), gap=gap))
R = pd.DataFrame(rows)
R[["eid", "resid_m"]].to_csv(out, index=False)
print(f"{len(R)} events  |gap| p50 {R.gap.abs().median():.1f}  gap p10/50/90 {R.gap.quantile([.1, .5, .9]).round(1).tolist()}")
