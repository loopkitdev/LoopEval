"""Cohort comparison of Loop Adaptive arms against the reference needs dial.

usage: python cohort.py <traces dir> <subset csv> <arm> [<arm> ...]
Per donor x arm metrics (metrics.stats on traces/<donor>_<arm>.pkl); arms missing for any donor are dropped
from the pooled view. Reference curve = gr_n090, gr_n095, gr, gr_n105, gr_n110 (pooled donor means, in needs
order). For each other arm: pooled means, the paired difference against gr, and dTIR@t70 — the arm's TIR minus
the reference curve's TIR interpolated at the arm's t<70 (positive = more TIR at equal lows than the dial
reaches; only reported when the arm's t<70 lies inside the reference's range). CIs: 2,000 bootstrap draws over
donors, the same draw for every arm."""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics

REF = ["gr_n090", "gr_n095", "gr", "gr_n105", "gr_n110"]
KEYS = ["tir", "t70", "t54", "t180", "t250", "mean", "cv", "lbgi", "hbgi", "ins", "auto", "big1", "big2", "tv", "iob54"]

def load(tdir, donors, arms):
    rows = []
    for a in donors:
        for arm in arms:
            p = f"{tdir}/{a}_{arm}.pkl"
            if os.path.exists(p): rows.append(dict(donor=a, arm=arm, **metrics.stats(pd.read_pickle(p))))
    return pd.DataFrame(rows)

def tir_at(ref_t70, ref_tir, x):
    o = np.argsort(ref_t70)
    xs, ys = np.asarray(ref_t70)[o], np.asarray(ref_tir)[o]
    return np.interp(x, xs, ys) if xs[0] <= x <= xs[-1] else np.nan

def main(tdir, sub, arms):
    donors = list(pd.read_csv(sub).alias)
    d = load(tdir, donors, REF + arms)
    full = d.groupby("donor").arm.nunique(); keep = full[full == full.max()].index
    d = d[d.donor.isin(keep)]
    W = {k: d.pivot(index="donor", columns="arm", values=k) for k in KEYS}
    n = len(keep); rng = np.random.default_rng(0); B = [rng.integers(0, n, n) for _ in range(2000)]
    def boot(f):
        v = np.array([f(b) for b in B]); return np.nanpercentile(v, 2.5), np.nanpercentile(v, 97.5)
    print(f"donors {n}")
    print("reference (needs dial):")
    for r in REF: print(f"  {r:10s} " + " ".join(f"{k}={W[k][r].mean():.2f}" for k in ["tir", "t70", "t54", "mean", "cv", "ins"]))
    out = []
    for arm in arms:
        if arm not in W["tir"]: continue
        m = {k: W[k][arm].mean() for k in KEYS}
        dtir = W["tir"][arm] - W["tir"]["gr"]; dt70 = W["t70"][arm] - W["t70"]["gr"]; dt54 = W["t54"][arm] - W["t54"]["gr"]
        def gap(b):
            return W["tir"][arm].iloc[b].mean() - tir_at([W["t70"][r].iloc[b].mean() for r in REF], [W["tir"][r].iloc[b].mean() for r in REF], W["t70"][arm].iloc[b].mean())
        g = gap(np.arange(n)); glo, ghi = boot(gap)
        lo, hi = boot(lambda b: dtir.iloc[b].mean()); lo70, hi70 = boot(lambda b: dt70.iloc[b].mean()); lo54, hi54 = boot(lambda b: dt54.iloc[b].mean())
        worst = dtir.idxmin()
        out.append(dict(arm=arm, **{k: round(v, 3) for k, v in m.items()},
                        dTIR=f"{dtir.mean():+.2f} [{lo:+.2f},{hi:+.2f}]", dt70=f"{dt70.mean():+.2f} [{lo70:+.2f},{hi70:+.2f}]",
                        dt54=f"{dt54.mean():+.3f} [{lo54:+.3f},{hi54:+.3f}]",
                        dTIR_at_t70=f"{g:+.2f} [{glo:+.2f},{ghi:+.2f}]" if np.isfinite(g) else "out of range",
                        worst=f"{worst} {dtir[worst]:+.1f}"))
    t = pd.DataFrame(out); pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(t[["arm", "tir", "t70", "t54", "mean", "cv", "ins", "big1", "tv", "iob54", "dTIR", "dt70", "dt54", "dTIR_at_t70", "worst"]].to_string(index=False))
    d.to_csv(f"{tdir}/../per_donor.csv", index=False)
    return t

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
