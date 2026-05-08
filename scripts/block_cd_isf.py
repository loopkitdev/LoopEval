#!/usr/bin/env python3
"""Block-coordinate-descent search for per-hour ISF multipliers.

Iterates 6 4-hour blocks (CDT local). For each block, evaluates a small set
of multipliers and locks in the one with the best benefit/cost ratio. Output:
the chosen 24-hour schedule, plus a markdown summary of each block's choice.
"""
import json, subprocess, csv, io, sys, os, datetime as dt

NIGHTSCOUT = "https://<NS>"
START = "2026-03-27"
END = "2026-04-26"
TZ = "America/Chicago"
BENCH = ".build/release/loop-eval"
MULTIPLIERS = [0.95, 1.00, 1.10, 1.15]
BLOCKS = [(0, 4), (4, 8), (8, 12), (12, 16), (16, 20), (20, 24)]


def run_sweep(candidates: list[dict]) -> list[dict]:
    cands_path = "/tmp/blockcd_cands.json"
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
    # CSV is on stdout; progress messages on stderr
    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    return rows


def main():
    X = [1.0] * 24  # current per-hour multipliers
    summary = []
    started = dt.datetime.now()
    print(f"Block-CD round started {started:%H:%M:%S}")
    print(f"Multipliers: {MULTIPLIERS}")
    print()

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
        # Pick best by ratio (ties → prefer higher RDB+IDB; if cost=0, ratio=inf, treat as best only if benefit>0)
        def score(r):
            try:
                ratio = float(r["ratio"])
            except ValueError:
                ratio = float("inf")
            # use ratio as primary, abs benefit as tiebreak
            cost = float(r["cost"])
            benefit = float(r["benefit"])
            # avoid picking pure-zero "ratio=inf" with benefit=0 (no change)
            if cost == 0 and benefit == 0:
                return (-1, 0)
            return (ratio, benefit)
        rows.sort(key=score, reverse=True)
        best = rows[0]
        best_m = float(best["label"].rsplit("x", 1)[-1])
        for h in range(lo, hi):
            X[h] = best_m
        elapsed = (dt.datetime.now() - block_started).total_seconds()
        print(f"Block {b} ({lo:02d}-{hi:02d} CDT): best ×{best_m:.2f} | ratio={best['ratio']:>6} | "
              f"cost={float(best['cost']):.4f} benefit={float(best['benefit']):.4f} | "
              f"OPR={float(best['opr']):.2f} | {elapsed:.0f}s")
        for r in rows:
            print(f"   ×{float(r['label'].rsplit('x',1)[-1]):.2f}: ratio={r['ratio']:>6}  "
                  f"ODR={float(r['odr']):.4f}  UDR={float(r['udr']):.4f}  "
                  f"IDB={float(r['idb']):.4f}  RDB={float(r['rdb']):.4f}")
        summary.append({"block": (lo, hi), "best_m": best_m, "rows": rows})

    total_elapsed = (dt.datetime.now() - started).total_seconds()
    print()
    print(f"Final schedule (CDT hours 00..23):")
    print("  " + "  ".join(f"{x:.2f}" for x in X))
    print()
    print(f"Total elapsed: {total_elapsed:.0f}s ({total_elapsed/60:.1f}min)")

    # Save final schedule + summary
    out_path = "/tmp/blockcd_result.json"
    with open(out_path, "w") as f:
        json.dump({"final_schedule": X, "summary": summary, "elapsed_s": total_elapsed}, f, indent=2)
    print(f"Saved → {out_path}")


if __name__ == "__main__":
    main()
