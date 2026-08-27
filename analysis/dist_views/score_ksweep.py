#!/usr/bin/env python3
"""Score the volatility-band k sweep on both real-lows beds.

For each donor, k=0 IS the stock reference sweep — same dial (insulin-needs),
same window, same flags — so the only difference between reference and candidate
is the mechanism. That satisfies the "compare on ONE dial" requirement and gives
the mechanism-off control for free.

Lift is span-normalised by its own reference, so it is compared WITHIN a donor
and never across donors.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from loopeval_analysis.scoring import score_counterfactual      # noqa: E402
from loopeval_analysis import frontier as FR                    # noqa: E402

RUN = Path.home() / "dev/LoopEvalScenarios/runs/2026-08-25-distributions/ksweep"
DATA = Path.home() / "dev/LoopEval/runs/2026-08-13-cohort-2mo"
DONORS = ["bddp11", "bddp10"]
KS = ["0", "0.25", "0.5", "1.0", "2.0"]
NEEDS = ["0.80", "0.85", "0.90", "0.925", "0.95", "0.975", "1.00",
         "1.025", "1.05", "1.075", "1.10"]
# The original coarse grid, kept so the polyline chord bias can be measured
# directly rather than argued about. Same span, so lift is comparable.
COARSE = ["0.80", "0.90", "1.00", "1.10"]


def score_all() -> pd.DataFrame:
    rows = []
    for donor in DONORS:
        outages = DATA / donor / "data_causal" / "disruptions.csv"
        for k in KS:
            for f in NEEDS:
                p = RUN / f"{donor}_k{k}_{f}.json"
                if not p.exists():
                    continue
                try:
                    s = score_counterfactual(
                        str(p),
                        outages_csv=str(outages) if outages.exists() else None,
                        post_hours=0.0, burnin_hours=6.0)
                except Exception as e:                            # noqa: BLE001
                    print(f"  {p.name}: {type(e).__name__}: {e}")
                    continue
                rows.append(dict(donor=donor, k=float(k), multiplier=float(f),
                                 TIR=s.get("TIR"), t54=s.get("t54"),
                                 t70=s.get("t70"), mean=s.get("mean"),
                                 kept=s.get("kept_frac")))
    return pd.DataFrame(rows)


def main() -> int:
    D = score_all()
    if D.empty:
        print("nothing scored yet")
        return 1
    pd.set_option("display.width", 220)
    print(D.sort_values(["donor", "k", "multiplier"]).round(3).to_string(index=False))
    D.to_csv(RUN / "scores.csv", index=False)

    print("\n" + "=" * 74)
    print("MEAN LIFT vs each donor's own k=0 reference (same dial). + = better.")
    print("=" * 74)
    summary = []
    for donor in DONORS:
        sub = D[D.donor == donor]
        ref = sub[sub.k == 0].sort_values("multiplier")
        if len(ref) < 2:
            print(f"{donor}: reference incomplete ({len(ref)} pts) — skipping")
            continue
        print(f"\n{donor}   reference: {len(ref)} points, "
              f"TIR {ref.TIR.min():.1f}-{ref.TIR.max():.1f}, "
              f"t54 {ref.t54.min():.2f}-{ref.t54.max():.2f}")
        for k in sorted(sub.k.unique()):
            if k == 0:
                continue
            cand = sub[sub.k == k].sort_values("multiplier")
            if len(cand) < len(NEEDS):
                print(f"  k={k:<4} incomplete ({len(cand)}/{len(NEEDS)} pts)")
                continue
            lifts = np.array([FR.lift(ref, r.TIR, r.t54)
                              for r in cand.itertuples()], dtype=float)
            lifts = lifts[np.isfinite(lifts)]
            if len(lifts) < 3:
                continue
            # The first/last sweep points project onto a polyline END, which
            # collapses the closest-point search onto that vertex and
            # exaggerates the distance. Report the interior mean as the headline
            # and the raw one beside it.
            inner = lifts[1:-1]
            summary.append(dict(donor=donor, k=k, mean=inner.mean(),
                                raw_mean=lifts.mean(), median=np.median(inner),
                                frac_pos=float((inner > 0).mean())))
            print(f"  k={k:<4} INTERIOR mean {inner.mean():+.4f} "
                  f"(all {lifts.mean():+.4f})   median {np.median(inner):+.4f}"
                  f"   frac_pos {np.mean(inner > 0):.2f}\n"
                  f"          per-point {np.round(lifts, 4).tolist()}")

    # ── chord bias ────────────────────────────────────────────────────────
    # Lift is the distance to the reference POLYLINE, not to the true reference
    # curve. This reference is strongly convex in t54, and a chord across a
    # convex curve lies ABOVE it — so a candidate point falling between two
    # widely-spaced knots is credited with lift it has not earned. Quantify that
    # by scoring the SAME candidate points against the coarse and dense
    # references. Both have the same span, so the numbers are comparable.
    print("\n" + "=" * 74)
    print("CHORD BIAS: same candidate points, coarse (4-pt) vs dense (7-pt) reference")
    print("=" * 74)
    for donor in DONORS:
        sub = D[D.donor == donor]
        dense = sub[sub.k == 0].sort_values("multiplier")
        coarse = dense[dense.multiplier.round(2).isin([float(x) for x in COARSE])]
        if len(dense) < 5 or len(coarse) < 4:
            continue
        for k in sorted(x for x in sub.k.unique() if x > 0):
            cand = sub[sub.k == k].sort_values("multiplier")
            if cand.empty:
                continue
            lc = np.array([FR.lift(coarse, r.TIR, r.t54) for r in cand.itertuples()])
            ld = np.array([FR.lift(dense, r.TIR, r.t54) for r in cand.itertuples()])
            ok = np.isfinite(lc) & np.isfinite(ld)
            if not ok.any():
                continue
            print(f"  {donor} k={k:<5} coarse mean {lc[ok].mean():+.4f}   "
                  f"dense mean {ld[ok].mean():+.4f}   "
                  f"bias {lc[ok].mean() - ld[ok].mean():+.4f}"
                  f"   (coarse frac_pos {np.mean(lc[ok] > 0):.2f} -> "
                  f"dense {np.mean(ld[ok] > 0):.2f})")

    if summary:
        S = pd.DataFrame(summary)
        print("\nDoes mean lift TREND with k? A mechanism that works should improve")
        print("with gain up to some optimum, not wander around zero.")
        for donor in DONORS:
            s = S[S.donor == donor].sort_values("k")
            if len(s) >= 2:
                print(f"  {donor}: " + "  ".join(
                    f"k={r.k}: {r['mean']:+.4f}" for _, r in s.iterrows()))

    # Plot per donor — never read a lift number without the plot.
    for donor in DONORS:
        sub = D[D.donor == donor]
        ref = sub[sub.k == 0][["multiplier", "TIR", "t54"]]
        cand = sub[sub.k > 0][["multiplier", "TIR", "t54", "k"]].copy()
        if len(ref) < 2 or cand.empty:
            continue
        cand["mechanism"] = cand["k"].map(lambda v: f"VSB k={v}")
        try:
            FR.plot_sweeps(ref, cand.drop(columns=["k"]),
                           out=str(RUN / f"sweeps_{donor}.png"),
                           mechanism="mechanism", multiplier="multiplier",
                           ref_label="insulin-needs sweep (stock, k=0)",
                           title=f"Volatility band k sweep — {donor}, 2 months")
            print(f"wrote {RUN}/sweeps_{donor}.png")
        except Exception as e:                                    # noqa: BLE001
            print(f"plot {donor} failed: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
