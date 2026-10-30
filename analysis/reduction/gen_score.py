"""Score surrogate arms against the gr needs dial on the ICE generator (tier B).

usage: python gen_score.py <red_scores csv> [<red_scores csv> ...]
Per training: donors common to every arm; reference curve = every gr_p0 / gr_pnXXX arm present (pooled means, in
needs order). For each sx arm: pooled means, paired difference against gr_p0, TIR gap at the arm's t<70 and
at its t<54 against the interpolated dial (positive = more TIR at equal lows; "out" when the arm's low
lies outside the dial's range), 2,000 donor bootstrap draws, and the worst donor. Columns cgm_* (sensor),
true_* also reported for the gap at t<70."""
import sys
import numpy as np, pandas as pd

def needs(arm):   # gr_p0 = x1.00, gr_pnXXX = xXXX/100
    return 1.0 if arm == "gr_p0" else int(arm[5:]) / 100

def interp(xr, yr, x):
    o = np.argsort(xr); xs, ys = np.asarray(xr)[o], np.asarray(yr)[o]
    return np.interp(x, xs, ys) if xs[0] <= x <= xs[-1] else np.nan

def score(path):
    d = pd.read_csv(path)
    d = d.groupby(["alias", "arm"]).mean(numeric_only=True).reset_index()
    REF = sorted((a for a in d.arm.unique() if a == "gr_p0" or a.startswith("gr_pn")), key=needs)
    arms = sorted(a for a in d.arm.unique() if a not in REF)
    n_arm = d.groupby("alias").arm.nunique(); keep = n_arm[n_arm == n_arm.max()].index
    d = d[d.alias.isin(keep)]
    W = {k: d.pivot(index="alias", columns="arm", values=k) for k in d.columns if k not in ("alias", "arm", "seed")}
    n = len(keep); rng = np.random.default_rng(0); B = [rng.integers(0, n, n) for _ in range(2000)]
    print(f"{path.split('/')[-1]}: {n} donors")
    for r in REF + arms:
        print(f"  {r:9s} TIR {W['cgm_tir'][r].mean():6.2f}  t70 {W['cgm_t70'][r].mean():5.2f}  t54 {W['cgm_t54'][r].mean():5.3f}"
              f"  mean {W['cgm_mean'][r].mean():6.1f}  U/d {W['insulin_u'][r].mean():5.1f}")
    out = {}
    for arm in arms:
        res = {}
        for pre in ("cgm", "true"):
            for low in ("t70", "t54"):
                T, L = W[f"{pre}_tir"], W[f"{pre}_{low}"]
                def gap(b):
                    return T[arm].iloc[b].mean() - interp([L[r].iloc[b].mean() for r in REF], [T[r].iloc[b].mean() for r in REF], L[arm].iloc[b].mean())
                g = gap(np.arange(n)); v = np.array([gap(b) for b in B])
                frac = np.isfinite(v).mean()
                res[f"{pre}_{low}"] = (g, np.nanpercentile(v, 2.5) if frac > 0 else np.nan, np.nanpercentile(v, 97.5) if frac > 0 else np.nan, frac)
        dt = W["cgm_tir"][arm] - W["cgm_tir"]["gr_p0"]; d70 = W["cgm_t70"][arm] - W["cgm_t70"]["gr_p0"]; d54 = W["cgm_t54"][arm] - W["cgm_t54"]["gr_p0"]
        w = dt.idxmin()
        print(f"  {arm}: dTIR {dt.mean():+.2f}  dt70 {d70.mean():+.2f}  dt54 {d54.mean():+.3f} vs gr_p0;  worst {w} {dt[w]:+.1f} TIR (dt70 {d70[w]:+.2f})")
        for k, (g, lo, hi, f) in res.items():
            print(f"     gap@{k:9s} " + (f"{g:+.2f} [{lo:+.2f},{hi:+.2f}]" if np.isfinite(g) else "out of dial range") + f"  (in range {f:.0%} of draws)")
        out[arm] = res
    return out

if __name__ == "__main__":
    for p in sys.argv[1:]: score(p)
