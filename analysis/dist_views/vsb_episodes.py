#!/usr/bin/env python3
"""Does the volatility band fire at the moments it was designed for?

The frontier says the mechanism has no lift. That is an aggregate verdict and it
does not say WHY. This asks the mechanistic question directly, on the same
counterfactual traces:

  1. When sigma spikes, does a low actually follow?              (is the signal real?)
  2. When a low happens, had sigma spiked first?                 (is the signal complete?)
  3. Where the band fired, did the candidate withhold insulin?   (does the wiring work?)
  4. Did withholding actually prevent the low?                   (does it help?)

The 2x2 of {sigma spiked} x {low followed} is the crux. A mechanism can fail for
two very different reasons — the signal never fires before real lows (blind), or
it fires constantly before non-events (false alarms costing TIR). Those call for
opposite fixes, and the aggregate lift number cannot tell them apart.

Compares the k=0 (stock) and k>0 (candidate) counterfactual arms of the SAME
donor and dial setting, so the only difference between them is the mechanism.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

RUN = Path.home() / "dev/LoopEvalScenarios/runs/2026-08-25-distributions/ksweep"
LOW = 70.0
SEVERE = 54.0
LOOKAHEAD_MIN = 120.0
SPIKE_Q = 0.80          # "sigma spiked" = top quintile of that person's own sigma


def load(donor: str, k: str, needs: str) -> dict | None:
    p = RUN / f"{donor}_k{k}_{needs}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def frame(trace: dict) -> pd.DataFrame:
    """Per-decision frame: candidate counterfactual BG, sigma, band, dose."""
    pr = trace["predictions"]
    t = pd.to_datetime([p["t"] for p in pr], utc=True, format="ISO8601")
    g = lambda k, d=np.nan: np.array([p.get(k, d) if p.get(k) is not None else d
                                      for p in pr], float)
    df = pd.DataFrame({
        "sigma": g("candidateVolSigma", -1.0),
        "band": g("candidateVolBandMgdl", -1.0),
        "dose": g("candidateDose", 0.0),
        "iob": g("candidateIOB"),
        "minpred": g("candidateMinPredBG"),
    }, index=t)
    counter = pd.DataFrame(trace["counter"])
    counter["t"] = pd.to_datetime(counter["t"], utc=True, format="ISO8601")
    bg = counter.set_index("t")["bg"].dropna()
    df["bg"] = bg.reindex(df.index, method="nearest",
                          tolerance=pd.Timedelta("3min"))
    return df, bg


def forward_min(bg: pd.Series, minutes: float) -> pd.Series:
    """Lowest BG in the next `minutes`, on the counterfactual trace."""
    r = bg[::-1].rolling(f"{int(minutes)}min").min()[::-1]
    return r.shift(-1)


def analyse(donor: str, needs: str, k: str = "1.0") -> dict | None:
    st, cd = load(donor, "0", needs), load(donor, k, needs)
    if st is None or cd is None:
        return None
    fs, bgs = frame(st)
    fc, bgc = frame(cd)

    # sigma comes from the candidate arm (the stock arm does not compute it).
    sig = fc["sigma"].where(fc["sigma"] > 0)
    if sig.notna().sum() < 500:
        return None
    thresh = sig.quantile(SPIKE_Q)

    fmin_stock = forward_min(bgs, LOOKAHEAD_MIN).reindex(fc.index, method="nearest",
                                                         tolerance=pd.Timedelta("3min"))
    fmin_cand = forward_min(bgc, LOOKAHEAD_MIN).reindex(fc.index, method="nearest",
                                                        tolerance=pd.Timedelta("3min"))
    ok = sig.notna() & fmin_stock.notna() & fmin_cand.notna()
    spike = (sig >= thresh) & ok
    low_stock = (fmin_stock < LOW) & ok

    n = int(ok.sum())
    a = int((spike & low_stock).sum())        # spiked and a low followed
    b = int((spike & ~low_stock).sum())       # spiked, no low  -> false alarm
    c = int((~spike & low_stock).sum() & 1) if False else int(((~spike) & low_stock & ok).sum())
    d = int(((~spike) & (~low_stock) & ok).sum())

    # Did the mechanism actually change the dose where it fired?
    fired = (fc["band"] > 1.0) & ok
    dose_delta = (fc["dose"] - fs["dose"].reindex(fc.index, method="nearest",
                                                  tolerance=pd.Timedelta("3min")))
    return dict(
        donor=donor, needs=needs, k=k, n=n, thresh=float(thresh),
        precision=a / max(a + b, 1),          # P(low | spike)
        recall=a / max(a + c, 1),             # P(spike | low)
        base_rate=(a + c) / max(n, 1),        # P(low)
        lift_ratio=(a / max(a + b, 1)) / max((a + c) / max(n, 1), 1e-9),
        spike_frac=(a + b) / max(n, 1),
        fired_frac=float(fired.sum()) / max(n, 1),
        dose_delta_on_fire=float(dose_delta[fired].mean()) if fired.any() else np.nan,
        dose_delta_off_fire=float(dose_delta[~fired & ok].mean()) if (~fired & ok).any() else np.nan,
        lows_stock=int(low_stock.sum()),
        lows_cand=int(((fmin_cand < LOW) & ok).sum()),
        sev_stock=int(((fmin_stock < SEVERE) & ok).sum()),
        sev_cand=int(((fmin_cand < SEVERE) & ok).sum()),
        a=a, b=b, c=c, d=d,
    )


def main() -> int:
    rows = []
    for donor in ("bddp11", "bddp10"):
        for needs in ("1.00", "1.05", "1.10"):
            r = analyse(donor, needs)
            if r:
                rows.append(r)
    if not rows:
        print("no traces")
        return 1
    R = pd.DataFrame(rows)
    pd.set_option("display.width", 240)

    print("IS THE SIGNAL REAL? sigma in its top quintile vs a low within 2 h")
    print("(on the STOCK counterfactual, so the outcome is not contaminated by the")
    print(" candidate's own dosing)\n")
    print(f"{'bed':<8}{'needs':>6}{'n':>7}{'P(low)':>9}{'P(low|spike)':>14}"
          f"{'ratio':>7}{'recall':>8}{'spike%':>8}")
    for _, r in R.iterrows():
        print(f"{r.donor:<8}{r.needs:>6}{r.n:>7}{r.base_rate*100:>8.2f}%"
              f"{r.precision*100:>13.2f}%{r.lift_ratio:>7.2f}{r.recall*100:>7.1f}%"
              f"{r.spike_frac*100:>7.1f}%")

    print("\n\nDOES THE WIRING WORK? mean dose difference (candidate - stock), U/step")
    print(f"{'bed':<8}{'needs':>6}{'fired%':>8}{'on fire':>10}{'off fire':>10}"
          f"{'lows stock':>12}{'lows cand':>11}{'severe st':>11}{'severe cd':>11}")
    for _, r in R.iterrows():
        print(f"{r.donor:<8}{r.needs:>6}{r.fired_frac*100:>7.1f}%"
              f"{r.dose_delta_on_fire:>10.4f}{r.dose_delta_off_fire:>10.4f}"
              f"{r.lows_stock:>12}{r.lows_cand:>11}{r.sev_stock:>11}{r.sev_cand:>11}")

    print("\n\n2x2 (spike x low-followed), pooled per bed:")
    for donor in R.donor.unique():
        s = R[R.donor == donor]
        a, b, c, d = int(s.a.sum()), int(s.b.sum()), int(s.c.sum()), int(s.d.sum())
        print(f"  {donor}:  spike&low {a:>6}   spike&NO-low {b:>6} (false alarms)"
              f"   NO-spike&low {c:>6} (missed)   neither {d:>6}")
        print(f"           of all spikes, {100*a/max(a+b,1):.1f}% precede a low; "
              f"of all lows, {100*a/max(a+c,1):.1f}% were preceded by a spike")
    R.to_csv(RUN / "episodes.csv", index=False)
    print(f"\nwrote {RUN}/episodes.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
