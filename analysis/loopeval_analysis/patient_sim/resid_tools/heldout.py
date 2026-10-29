"""Held-out check of the per-person residual level (LESSONS 519): the level was fitted to each donor's ODD 13-day blocks
(LVL_BLOCKS=odd); here twin outcomes (both draws pooled per template) against the donor's EVEN blocks, beside the
in-sample (odd) agreement and the ceiling (the donor's odd blocks against their even blocks).
    python heldout.py <run> [<run> ...]"""
import sys, glob, pickle, numpy as np, pandas as pd
from pathlib import Path
H = Path.home()
B = pd.read_csv(H / ".loop-eval/runs/2026-10-15-additive-templates/real_pilot_blocks.csv")
odd = B[B.block % 2 == 1].groupby("alias").median(numeric_only=True)
even = B[B.block % 2 == 0].groupby("alias").median(numeric_only=True)
rows = []
for r in sys.argv[1:]:
    S = pd.read_csv(Path(r) / "sim_stats.csv"); k = [c for c in S.columns if c in ("name", "who", "alias")][0]
    tm = {Path(d).name: pickle.load(open(d + "/person.pkl", "rb")).template for d in glob.glob(r + "/v0*")}
    S["tmpl"] = S[k].map(tm); rows.append(S)
S = pd.concat(rows).groupby("tmpl").median(numeric_only=True)
print(f"{len(S)} templates")
for st in ["bg_mean", "tir", "t70", "t54", "bg_cv"]:
    j = pd.concat([S[st].rename("twin"), odd[st].rename("odd"), even[st].rename("even")], axis=1, join="inner").dropna()
    sp = lambda a, b: j[a].corr(j[b], method="spearman")
    print(f"  {st:8s} n {len(j):3d}  twin~odd (fitted) {sp('twin', 'odd'):.2f}  twin~even (held out) {sp('twin', 'even'):.2f}"
          f"  ceiling odd~even {sp('odd', 'even'):.2f}  |twin-even| p50 {np.median(np.abs(j.twin - j.even)):.2f}  |odd-even| p50 {np.median(np.abs(j.odd - j.even)):.2f}")
