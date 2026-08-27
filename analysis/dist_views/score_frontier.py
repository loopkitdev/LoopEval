#!/usr/bin/env python3
"""Score the volatility-band frontier sweep and compute lift.

Ranks mechanisms the way FRONTIERS.md requires: sweep the candidate over its own
dial, compare against the stock reference swept on the SAME dial, and rank by
mean lift across the sweep rather than best-of-sweep. Lift is only comparable
within one reference, so nothing here is compared across datasets.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from loopeval_analysis.scoring import score_counterfactual      # noqa: E402
from loopeval_analysis import frontier as FR                    # noqa: E402

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import style as _S

RUN = _S.OUT / "frontier"
DATA = Path.home() / "dev/LoopEval/runs/2026-08-13-cohort-2mo/bddp11/data_causal"
NEEDS = ["0.80", "0.90", "1.00", "1.10"]
ARMS = {"std": "stock", "vsb": "VSB k=1 caution-only", "lic": "VSB k=1 + licence"}


def main() -> int:
    outages = DATA / "disruptions.csv"
    rows = []
    for arm, label in ARMS.items():
        for f in NEEDS:
            p = RUN / f"{arm}_{f}.json"
            if not p.exists():
                print(f"  missing {p.name}")
                continue
            try:
                s = score_counterfactual(str(p),
                                         outages_csv=str(outages) if outages.exists() else None,
                                         post_hours=0.0, burnin_hours=6.0)
            except Exception as e:                                # noqa: BLE001
                print(f"  {p.name}: {type(e).__name__}: {e}")
                continue
            rows.append(dict(arm=arm, label=label, multiplier=float(f),
                             TIR=s.get("TIR"), t54=s.get("t54"),
                             t70=s.get("t70"), mean=s.get("mean"),
                             kept=s.get("kept_frac")))
    if not rows:
        print("nothing scored")
        return 1
    D = pd.DataFrame(rows).sort_values(["arm", "multiplier"])
    pd.set_option("display.width", 200)
    print(D.round(3).to_string(index=False))
    D.to_csv(RUN / "scores.csv", index=False)

    ref = D[D.arm == "std"].sort_values("multiplier")
    print("\nlift against the stock sweep (same dial), + = better:")
    for arm, label in ARMS.items():
        if arm == "std":
            continue
        cand = D[D.arm == arm].sort_values("multiplier")
        lifts = []
        for _, r in cand.iterrows():
            try:
                lifts.append(FR.lift(ref, r["TIR"], r["t54"]))
            except Exception as e:                                # noqa: BLE001
                print(f"  lift failed ({type(e).__name__}: {e})")
                lifts = []
                break
        lifts = [x for x in lifts if np.isfinite(x)]
        if lifts:
            lifts = np.asarray(lifts, dtype=float)
            print(f"  {label:<24} mean {np.nanmean(lifts):+.4f}   "
                  f"median {np.nanmedian(lifts):+.4f}   "
                  f"frac_pos {np.mean(lifts > 0):.2f}   "
                  f"per-point {np.round(lifts, 4).tolist()}")
    # AGENTS.md: never read a lift number without looking at the plot, and never
    # hand-roll a sweep plot — plot_sweeps orders by multiplier and applies the
    # standard axes (t<54 up = worse) so neither can be gotten wrong.
    try:
        ref_df = D[D.arm == "std"][["multiplier", "TIR", "t54"]].copy()
        cand_df = D[D.arm != "std"][["multiplier", "TIR", "t54", "label"]].copy()
        cand_df = cand_df.rename(columns={"label": "mechanism"})
        FR.plot_sweeps(ref_df, cand_df, out=str(RUN / "sweeps.png"),
                       mechanism="mechanism", multiplier="multiplier",
                       ref_label="insulin-needs sweep (stock reference)",
                       title="Volatility-scaled forecast band vs stock, bddp11, 2 months")
        print(f"\nwrote {RUN}/sweeps.png")
    except Exception as e:                                        # noqa: BLE001
        print(f"\nplot failed: {type(e).__name__}: {e}")

    print("\nRead the plot before believing any of these numbers — lift is a scalar "
          "summary of a geometric fact, and if its sign disagrees with where the "
          "point sits relative to the reference line, believe the plot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
