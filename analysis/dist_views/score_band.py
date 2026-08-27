#!/usr/bin/env python3
"""Re-score the volatility-band sweep under the canonical scoring definition.

`docs/FRONTIERS.md` (unified 2026-08-24) supersedes whole-sweep mean lift, which
is what the earlier passes here reported. The canonical test is
dominance-with-retuning inside the donor's OPERATING BAND (validated multiplier
±0.1), with paired block-bootstrap CIs, via `loopeval_analysis.band`.

This matters for exactly the failure mode this sweep hit: FRONTIERS records that
an oracle carrying +6-8 TIR of gentle-end value scored NEGATIVE whole-sweep mean
lift. Our whole-sweep means were likewise dragged down by the ×0.80 endpoint, so
the earlier verdict needs re-deriving rather than restating.

Operating multipliers come from PRIVATE.md's per-donor validation:
  bddp11 — field point sits on the std curve near ×0.87
  bddp10 — re-validated 2026-08-24, field point ON the curve at ×1.00
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from loopeval_analysis import band as B                      # noqa: E402

RUN = Path.home() / "dev/LoopEvalScenarios/runs/2026-08-25-distributions/ksweep"
DATA = Path.home() / "dev/LoopEval/runs/2026-08-13-cohort-2mo"
MULTS = ["0.80", "0.85", "0.90", "0.925", "0.95", "0.975", "1.00",
         "1.025", "1.05", "1.075", "1.10"]
KS = ["0.25", "0.5", "1.0", "2.0"]
OP = {"bddp11": 0.87, "bddp10": 1.00}


def blocks_for(donor: str, k: str):
    outages = DATA / donor / "data_causal" / "disruptions.csv"
    out = {}
    for m in MULTS:
        p = RUN / f"{donor}_k{k}_{m}.json"
        if not p.exists():
            continue
        try:
            out[float(m)] = B.block_scores(
                str(p), outages_csv=str(outages) if outages.exists() else None)
        except Exception as e:                                # noqa: BLE001
            print(f"    {p.name}: {type(e).__name__}: {e}")
    return out


def main() -> int:
    for donor, op in OP.items():
        print("=" * 78)
        print(f"{donor}   operating band ×{op-0.1:.2f}–×{op+0.1:.2f}  "
              f"(validated multiplier ×{op:.2f})")
        print("=" * 78)
        ref = blocks_for(donor, "0")
        if len(ref) < 2:
            print("  no reference traces")
            continue
        cands = {}
        for k in KS:
            c = blocks_for(donor, k)
            if len(c) >= 2:
                cands[f"VSB k={k}"] = c
        if not cands:
            continue
        try:
            table, points = B.band_report(ref, cands, op_mult=op)
        except Exception as e:                                # noqa: BLE001
            print(f"  band_report failed: {type(e).__name__}: {e}")
            continue
        print(B.format_table(table))
        table.to_csv(RUN / f"band_{donor}.csv", index=False)
        pts = points[points.get("in_band", True)] if "in_band" in points else points
        cols = [c for c in ("mechanism", "multiplier", "TIR", "t54", "t70",
                            "lift", "dominant", "in_band") if c in pts.columns]
        print("\n  in-band points:")
        print("   " + pts[cols].round(3).to_string(index=False).replace("\n", "\n   "))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
