#!/usr/bin/env python3
"""Block-coordinate-descent search for per-hour ISF multipliers using a
TIR-based objective:

    Maximize candidate TIR (% time 70-180)
    Subject to: candidate time-below-70 <= actual time-below-70 + epsilon

If no candidate satisfies the hypo constraint for a block, keep ×1.0
(no change). This implements the safety priority order: don't worsen
hypos first, then improve TIR (which balances "less hyper time" against
"more time in range").

Compare to block_cd_isf.py which used the benefit/cost ratio metric.
The ratio metric over-rewards small intensity gains and ignores TIR
duration shifts; this version optimizes the actual TIR outcome.
"""
import json, subprocess, csv, io, sys, datetime as dt

NIGHTSCOUT = "https://<NS>"
START = "2026-03-27"
END = "2026-04-26"
TZ = "America/Chicago"
BENCH = ".build/release/loop-eval"
MULTIPLIERS = [0.95, 1.00, 1.05, 1.10, 1.15]
BLOCKS = [(0, 4), (4, 8), (8, 12), (12, 16), (16, 20), (20, 24)]
HYPO_TOLERANCE = 0.001  # candidate <70 fraction must not exceed actual + this


def run_sweep(candidates: list[dict]) -> list[dict]:
    cands_path = "/tmp/blockcd_tir_cands.json"
    with open(cands_path, "w") as f:
        json.dump(candidates, f)
    result = subprocess.run([
        BENCH, "sweep",
        "--nightscout-url", NIGHTSCOUT,
        "--start", START, "--end", END,
        "--candidates-file", cands_path,
        "--local-timezone", TZ,
    ], capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    return rows


def main():
    X = [1.0] * 24
    summary = []
    started = dt.datetime.now()
    print(f"Block-CD (TIR objective) started {started:%H:%M:%S}")
    print(f"Multipliers: {MULTIPLIERS}")
    print(f"Constraint: candidate <70 fraction ≤ actual + {HYPO_TOLERANCE*100:.1f}pp")
    print(f"Objective: max candidate TIR")
    print()

    actual_below70 = None  # set after first sweep

    for b, (lo, hi) in enumerate(BLOCKS):
        block_started = dt.datetime.now()
        candidates = []
        for m in MULTIPLIERS:
            x_new = list(X)
            for h in range(lo, hi):
                x_new[h] = m
            candidates.append({
                "label": f"block{b}_{lo:02d}-{hi:02d}_x{m:.2f}",
                "isfHourly": x_new,
            })
        rows = run_sweep(candidates)

        if actual_below70 is None:
            actual_below70 = float(rows[0]["below70_act"])
            actual_tir = float(rows[0]["tir_act"])
            actual_above180 = float(rows[0]["above180_act"])
            print(f"Actual baseline: TIR={actual_tir*100:.1f}%  <70={actual_below70*100:.2f}%  "
                  f">180={actual_above180*100:.1f}%")
            print()

        cap = actual_below70 + HYPO_TOLERANCE
        # Filter: candidates that satisfy the hypo constraint
        feasible = [r for r in rows if float(r["below70_cand"]) <= cap]
        if not feasible:
            # No candidate satisfies — keep ×1.0
            print(f"Block {b} ({lo:02d}-{hi:02d} CDT): NO FEASIBLE candidate (all increase <70). Keeping ×1.0.")
            best_m = 1.00
        else:
            # Among feasible, pick max TIR (ties → prefer higher RDB+IDB safety signal)
            feasible.sort(key=lambda r: (float(r["tir_cand"]), float(r["benefit"])), reverse=True)
            best = feasible[0]
            best_m = float(best["label"].rsplit("x", 1)[-1])

        for h in range(lo, hi):
            X[h] = best_m
        elapsed = (dt.datetime.now() - block_started).total_seconds()
        # Print summary for this block
        rows_sorted = sorted(rows, key=lambda r: float(r["tir_cand"]), reverse=True)
        print(f"Block {b} ({lo:02d}-{hi:02d} CDT): chosen ×{best_m:.2f} | {elapsed:.0f}s")
        for r in rows_sorted:
            mult = float(r['label'].rsplit('x',1)[-1])
            tir = float(r['tir_cand']) * 100
            below = float(r['below70_cand']) * 100
            above = float(r['above180_cand']) * 100
            mark = " ✓" if mult == best_m else ""
            feasible_mark = " " if float(r['below70_cand']) <= cap else "✗"
            print(f"   {feasible_mark}×{mult:.2f}: TIR={tir:5.2f}%  <70={below:5.2f}%  >180={above:5.2f}%  "
                  f"ratio={r['ratio']:>6}{mark}")
        summary.append({"block": (lo, hi), "best_m": best_m, "rows": rows})
        print()

    total_elapsed = (dt.datetime.now() - started).total_seconds()
    print(f"Final schedule (CDT hours 00..23):")
    print("  " + "  ".join(f"{x:.2f}" for x in X))
    print(f"\nTotal elapsed: {total_elapsed:.0f}s ({total_elapsed/60:.1f}min)")

    # Save
    out_path = "/tmp/blockcd_tir_result.json"
    with open(out_path, "w") as f:
        json.dump({"final_schedule": X, "summary": summary, "elapsed_s": total_elapsed,
                   "actual_baseline": {"tir": actual_tir, "below70": actual_below70,
                                        "above180": actual_above180}}, f, indent=2)
    print(f"Saved → {out_path}")


if __name__ == "__main__":
    main()
