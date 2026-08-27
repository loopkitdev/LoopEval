#!/usr/bin/env python3
"""The two therapy-relevant questions, asked on held-out data only.

  LOWS   Does knowing σ tell you anything about imminent hypoglycaemia that
         glucose level and trend do not already tell you?

  HIGHS  When glucose is high AND σ is low — the forecast is trustworthy — is
         the subsequent hypo risk low enough to justify dosing harder than a
         fixed application factor does?

Both are asked out of sample: the estimator's one parameter is fitted on the
FIRST 30% of each record and σ is then produced for the remaining 70%, which is
where every number below comes from. (The first pass used the opposite split and
was too thin to measure anything — most people had zero events in matched cells.)
The estimator is EWMA, which won the out-of-sample contest for predicting future
realised volatility; GARCH scores better on likelihood but slightly worse here,
and this is the quantity that matters for risk. Both pool events across matched cells
rather than averaging per-cell rates, and both carry bootstrap intervals — an
earlier pass did neither and produced ratios that did not survive either fix.

Nothing here establishes therapy benefit. These are associations in observed
data, where dosing already responded to state. Benefit needs the counterfactual
simulator; this is the evidence for whether that run is worth setting up.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S                                          # noqa: E402
from loopeval_analysis import dists as D                   # noqa: E402

OUT = S.OUT
RNG = np.random.default_rng(11)
N_BOOT = 2000


def terciles(x: pd.Series) -> pd.Series:
    """Rank-based terciles. qcut fails once the variance floor creates ties."""
    return pd.qcut(x.rank(method="first"), 3, labels=["lo", "mid", "hi"])


FIT_FRAC = 0.30


def out_of_sample_sigma(alias: str):
    """Fit EWMA on the first FIT_FRAC of the record, emit σ for the rest."""
    from loopeval_analysis import volatility as V
    import vol_fit as VF
    rt, cad = VF.runs_with_times(alias)
    if not rt:
        return None
    fit_rt, test_rt = VF.split(rt, FIT_FRAC)
    fit_r = [r for r, _ in fit_rt]
    test_r = [r for r, _ in test_rt]
    if not fit_r or not test_r:
        return None
    vf = V.measurement_floor(VF.NOISE.get(alias, 1.0))
    est = V.fit_estimator("ewma", fit_r, cad, var_floor=vf)
    sig = est.filter(test_r)
    t = np.concatenate([tt.values for _, tt in test_rt])
    s = np.concatenate(sig)
    m = np.isfinite(s) & (s > 0)
    return pd.Series(s[m], index=pd.DatetimeIndex(t[m]).tz_localize("UTC")), est.lam


def frame(alias: str) -> pd.DataFrame | None:
    """Out-of-sample σ joined to the panel, with forward outcomes attached."""
    got = out_of_sample_sigma(alias)
    if got is None:
        return None
    sig, _ = got
    if sig.empty:
        return None

    p = D.clean(S.load(alias)).copy()
    p = p[p.index >= sig.index.min()]
    if p.empty:
        return None
    p["sigma"] = sig.reindex(p.index, method="nearest",
                             tolerance=pd.Timedelta("3min"))
    p["trend"] = p["bg"].diff(6)
    # forward outcomes on the 5-minute panel grid
    p["fmin30"] = p["bg"][::-1].rolling(6).min()[::-1].shift(-1)
    p["fmin120"] = p["bg"][::-1].rolling(24).min()[::-1].shift(-1)
    p["fmax120"] = p["bg"][::-1].rolling(24).max()[::-1].shift(-1)
    return p.dropna(subset=["sigma", "trend", "fmin30", "fmin120", "bg"])


def pooled_ratio(df: pd.DataFrame, cell_keys: list[str], target: str,
                 lo="lo", hi="hi", min_n=40):
    """Event-pooled hi/lo rate ratio across matched cells, with a 90% CI."""
    g = (df.groupby(cell_keys + ["vt"], observed=True)[target]
           .agg(["sum", "size"]).unstack("vt"))
    need = [("size", lo), ("size", hi), ("sum", lo), ("sum", hi)]
    if not all(c in g.columns for c in need):
        return None
    g = g[(g[("size", lo)] >= min_n) & (g[("size", hi)] >= min_n)].dropna(subset=need)
    if len(g) < 3:
        return None
    n_lo, n_hi = g[("size", lo)].to_numpy(), g[("size", hi)].to_numpy()
    k_lo, k_hi = g[("sum", lo)].to_numpy(), g[("sum", hi)].to_numpy()

    rate = lambda k, n: k.sum() / max(n.sum(), 1)
    r_lo, r_hi = rate(k_lo, n_lo), rate(k_hi, n_hi)
    boots = []
    for _ in range(N_BOOT):
        i = RNG.integers(0, len(n_lo), len(n_lo))
        a, b = rate(k_lo[i], n_lo[i]), rate(k_hi[i], n_hi[i])
        if a > 0:
            boots.append(b / a)
    ci = np.percentile(boots, [5, 95]) if len(boots) > 100 else (np.nan, np.nan)
    return dict(lo=r_lo, hi=r_hi, ratio=r_hi / max(r_lo, 1e-12),
                ci_lo=ci[0], ci_hi=ci[1],
                events=int(k_lo.sum() + k_hi.sum()), cells=len(g))


def main() -> int:
    lows, highs, expo = [], [], []
    for alias in S.cohort()["alias"]:
        df = frame(alias)
        if df is None or len(df) < 3000:
            continue
        df = df.assign(
            lvl=pd.cut(df.bg, [40, 100, 140, 190, 400]),
            trd=pd.qcut(df.trend, 3, duplicates="drop"),
            vt=terciles(df.sigma),
            hypo30=(df.fmin30 < 70).astype(int),
            hypo120=(df.fmin120 < 70).astype(int),
        )

        r = pooled_ratio(df, ["lvl", "trd"], "hypo30", min_n=25)
        if r:
            r["alias"] = alias
            lows.append(r)

        # HIGHS: restricted to glucose above 180, outcome is a low within 2 h.
        h = df[df.bg > 180]
        if len(h) > 800:
            h = h.assign(lvl=pd.cut(h.bg, [180, 230, 290, 400]),
                         trd=pd.qcut(h.trend, 3, duplicates="drop"),
                         vt=terciles(h.sigma))
            rh = pooled_ratio(h, ["lvl", "trd"], "hypo120", min_n=25)
            if rh:
                rh["alias"] = alias
                rh["frac_high"] = float((df.bg > 180).mean())
                rh["frac_high_lowvol"] = float(
                    ((df.bg > 180) & (df.vt == "lo")).mean())
                highs.append(rh)

        expo.append(dict(alias=alias, n=len(df),
                         at_floor=float((df.sigma <= df.sigma.min() * 1.001).mean()),
                         sigma_p10=float(df.sigma.quantile(.10)),
                         sigma_p90=float(df.sigma.quantile(.90)),
                         spread=float(df.sigma.quantile(.90) / df.sigma.quantile(.10))))

    L = pd.DataFrame(lows)
    H = pd.DataFrame(highs)
    E = pd.DataFrame(expo)
    L.to_csv(OUT / "vol_lows.csv", index=False)
    H.to_csv(OUT / "vol_highs.csv", index=False)

    print("LOWS — P(BG<70 within 30 min), high-σ vs low-σ, matched on level+trend")
    print(f"{'alias':<11}{'lo%':>7}{'hi%':>7}{'ratio':>7}{'90% CI':>14}{'events':>8}{'cells':>7}")
    for _, r in L.iterrows():
        print(f"{r.alias:<11}{r.lo*100:>7.2f}{r.hi*100:>7.2f}{r.ratio:>7.2f}"
              f"{f'{r.ci_lo:.2f}-{r.ci_hi:.2f}':>14}{r.events:>8.0f}{r.cells:>7.0f}")
    P = L[L.events >= 100]
    print(f"\nover the {len(P)}/{len(L)} people with >=100 events: median ratio "
          f"{P.ratio.median():.2f}, CI excludes 1 upward for "
          f"{int((P.ci_lo > 1).sum())}, downward for {int((P.ci_hi < 1).sum())}")
    print("people with <100 events are omitted from that summary — too few lows to measure")

    print("\n\nHIGHS — starting above 180, P(BG<70 within 2 h), high-σ vs low-σ")
    print(f"{'alias':<11}{'lo%':>7}{'hi%':>7}{'ratio':>7}{'90% CI':>14}"
          f"{'events':>8}{'%time>180':>10}{'%>180&loσ':>11}")
    for _, r in H.iterrows():
        print(f"{r.alias:<11}{r.lo*100:>7.2f}{r.hi*100:>7.2f}{r.ratio:>7.2f}"
              f"{f'{r.ci_lo:.2f}-{r.ci_hi:.2f}':>14}{r.events:>8.0f}"
              f"{r.frac_high*100:>10.1f}{r.frac_high_lowvol*100:>11.1f}")
    PH = H[H.events >= 30]
    print(f"\nover the {len(PH)}/{len(H)} people with >=30 events: median ratio "
          f"{PH.ratio.median():.2f}, CI excludes 1 upward for {int((PH.ci_lo > 1).sum())}")
    print(f"median share of time above 180 in the low-σ tercile: "
          f"{H.frac_high_lowvol.median()*100:.1f}% of all samples")
    print(f"\nσ spread p90/p10 (test split): median {E.spread.median():.2f}x")
    print(f"share of samples sitting exactly on the variance floor: median "
          f"{E.at_floor.median()*100:.1f}%, max {E.at_floor.max()*100:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
