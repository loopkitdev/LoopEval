"""Cohort runner: ETL-export + CF-sim + score a list of Tidepool Loop donors.

For each donor: export the window → run `loop-eval simulate --data-dir` (stock Loop,
fidelity, raw-sim) → score SIM vs FIELD (TIR / t<54). CGM gaps detected from the
trace's own actual timestamps (no per-donor disruption CSV yet).

    python3 -m loopeval_analysis.tidepool.cohort 2026-02-01 2026-04-01 d6954e6498 c340c91dae ...
"""
import os, sys, json, subprocess
import numpy as np, pandas as pd
from loopeval_analysis.tidepool.etl import export_donor

BIN = "/Users/pete/dev/loopalgo/LoopEval/.build/release/loop-eval"
BASE = "/Users/pete/dev/loopalgo/runs/2026-06-15-tidepool/cohort"

def _score(trace):
    t = json.load(open(trace))
    def ser(k):
        a = pd.DataFrame(t[k]); a["t"] = pd.to_datetime(a["t"], utc=True)
        s = a.set_index("t")["bg"].astype(float).dropna().sort_index()
        return s[~s.index.duplicated()]
    c = ser("counter"); a = ser("actual")
    cf = pd.to_datetime(t["intervalStart"], utc=True) + pd.Timedelta(hours=6)
    c = c[c.index >= cf]
    a2 = a.reindex(c.index, method="nearest", tolerance=pd.Timedelta("3min"))
    d = pd.concat([c.rename("c"), a2.rename("a")], axis=1).dropna()
    def st(x):
        return dict(TIR=100*((x>=70)&(x<=180)).mean(), t54=100*(x<54).mean(),
                    t70=100*(x<70).mean(), t180=100*(x>180).mean(), mean=x.mean())
    return st(d.c), st(d.a), len(d)

def run_one(user, start, end):
    od = f"{BASE}/{user}"
    try:
        export_donor(user, start, end, od)
    except Exception as e:
        print(f"{user}: ETL FAILED {e}"); return None
    # sim window: skip first/last day to leave burn-in + edge margin
    s2 = (pd.Timestamp(start) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    e2 = (pd.Timestamp(end) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    tr = f"{od}/stock.json"
    cmd = [BIN, "simulate", "--data-dir", od, "--candidate-counterfactual",
           "--candidate-infer-sensitivity", "--counter-reg-onset", "54",
           "--counter-reg-gain", "0.4", "--counter-reg-max", "8.0",
           "--cgm-stale-guard-min", "5", "--glucose-lookback-hours", "24",
           "--start", s2, "--end", e2, "--baseline-label", "S",
           "--candidate-label", "stock", "--trace-out", tr]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"{user}: SIM FAILED\n{r.stdout[-400:]}\n{r.stderr[-400:]}"); return None
    sim, fld, n = _score(tr)
    print(f"{user}: n={n}  FIELD TIR {fld['TIR']:.1f}/t54 {fld['t54']:.2f}  "
          f"SIM TIR {sim['TIR']:.1f}/t54 {sim['t54']:.2f}  Δmean {sim['mean']-fld['mean']:+.0f}")
    return dict(user=user, n=n, **{f"f_{k}": v for k, v in fld.items()},
                **{f"s_{k}": v for k, v in sim.items()})

def main(start, end, users):
    rows = [r for u in users if (r := run_one(u, start, end))]
    df = pd.DataFrame(rows)
    if not df.empty:
        os.makedirs(BASE, exist_ok=True)
        df.to_csv(f"{BASE}/cohort_scores.csv", index=False)
        print("\n=== cohort summary (SIM vs FIELD) ===")
        print(df[["user","n","f_TIR","s_TIR","f_t54","s_t54","f_mean","s_mean"]].round(2).to_string(index=False))
        print(f"\nmean FIELD TIR {df.f_TIR.mean():.1f} | mean SIM TIR {df.s_TIR.mean():.1f} | "
              f"mean Δmean {(df.s_mean-df.f_mean).mean():+.1f} | wrote {BASE}/cohort_scores.csv")
    return df

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
