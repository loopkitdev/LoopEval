"""Candidate controllers on simulated cohorts: paired arms, deltas and lift over the insulin-needs dial.

Every arm runs the SAME simulated people (same seeds, meals, sensors, life events); only the controller's flags
differ (cohort.py --flags-json). Differences are therefore the controller's alone, and outcomes are read on CGM and
on TRUE glucose, which replay cannot see (LESSONS 83).

    # arms: baseline, candidate(s), and the dial at insulin-needs 0.95 / 1.05 (flags {"*": [...]} or per person)
    python -m loopeval_analysis.patient_sim.cohort ... --flags-json flags.json --out runs/arm_x
    python -m loopeval_analysis.patient_sim.candidates <baseline> <dial_down> <dial_up> <arm> [<arm> ...]

`sigma5_p50` gives a person's median σ5 for the σ-gated candidates (C22/C23/C29/C30), computed from their own
baseline run as replay computes it from the donor's prior data.
"""
from __future__ import annotations

import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

BURN = 2880.0


def outcomes(run: Path) -> dict:
    """Per-person outcomes after burn-in, on CGM and on true glucose; TDD delivered."""
    tr = pickle.load(open(run / "truth.pkl", "rb"))
    c = tr["cgm"].dropna()
    c = c[c.index >= BURN].to_numpy()
    T = tr["truth"]
    T = T[T.m >= BURN]
    g = T.bg.to_numpy()
    days = (T.m.max() - BURN) / 1440
    return dict(person=run.name, tir=100 * np.mean((c >= 70) & (c <= 180)), t54=100 * np.mean(c < 54),
                t70=100 * np.mean(c < 70), mean=float(c.mean()), true_tir=100 * np.mean((g >= 70) & (g <= 180)),
                true_t54=100 * np.mean(g < 54), true_t70=100 * np.mean(g < 70), tdd=float(T.delivered.sum() / days))


def load(root: Path, par: int = 8) -> pd.DataFrame:
    with ProcessPoolExecutor(par) as ex:
        return pd.DataFrame(list(ex.map(outcomes, sorted(Path(root).glob("v0*"))))).set_index("person")


def sigma5_p50(cgm: pd.Series, lam: float = 0.875, noise: float = 1.4) -> float:
    """Median causal EWMA std of the 5-min increment (26-min half-life, variance floored at 2·noise²), as the
    σ-band candidates compute σ5 (docs/candidates C22)."""
    c = cgm.dropna().sort_index()
    c = c[~c.index.duplicated()]
    r = c.reindex(np.arange(c.index.min(), c.index.max() + 1, 5.0)).to_numpy()
    floor = 2 * noise ** 2
    var, out = floor, []
    for i in range(1, len(r)):
        if np.isfinite(r[i]) and np.isfinite(r[i - 1]):
            d = r[i] - r[i - 1]
            var = lam * var + (1 - lam) * d * d
            out.append(np.sqrt(max(var, floor)))
    return float(np.median(out))


def paired(base: pd.DataFrame, arm: pd.DataFrame, n_boot: int = 2000, seed: int = 0) -> pd.Series:
    """Mean per-person delta (arm − baseline) with a bootstrap 95% interval over people."""
    D = (arm - base.reindex(arm.index)).dropna()
    rng = np.random.default_rng(seed)
    out = {"n": len(D)}
    for k in ["tir", "t54", "t70", "mean", "true_tir", "true_t54", "true_t70", "tdd"]:
        v = D[k].to_numpy()
        bs = [rng.choice(v, len(v)).mean() for _ in range(n_boot)]
        out[k] = f"{v.mean():+.2f} [{np.percentile(bs, 2.5):+.2f},{np.percentile(bs, 97.5):+.2f}]"
    return pd.Series(out)


def dial_lift(base: pd.DataFrame, down: pd.DataFrame, up: pd.DataFrame, arm: pd.DataFrame, true: bool = False,
              n_boot: int = 1000, seed: int = 1) -> tuple[float, float, float]:
    """ΔTIR above the insulin-needs dial at the candidate's Δt<54: the dial is a line through (down, 0, up) in
    (Δt54, ΔTIR) cohort means. Returns (lift, lo95, hi95) by bootstrap over people."""
    pre = "true_" if true else ""
    idx = base.index.intersection(arm.index).intersection(down.index).intersection(up.index)
    dT = {k: (x[pre + "tir"] - base[pre + "tir"]).reindex(idx).to_numpy() for k, x in (("d", down), ("u", up), ("a", arm))}
    dL = {k: (x[pre + "t54"] - base[pre + "t54"]).reindex(idx).to_numpy() for k, x in (("d", down), ("u", up), ("a", arm))}

    def lift(sel):
        x = np.array([dL["d"][sel].mean(), 0.0, dL["u"][sel].mean()])
        y = np.array([dT["d"][sel].mean(), 0.0, dT["u"][sel].mean()])
        return dT["a"][sel].mean() - np.polyfit(x, y, 1)[0] * dL["a"][sel].mean()

    rng = np.random.default_rng(seed)
    allv = np.arange(len(idx))
    bs = [lift(rng.integers(0, len(idx), len(idx))) for _ in range(n_boot)]
    return float(lift(allv)), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def main():
    base, down, up, *arms = [Path(a) for a in sys.argv[1:]]
    B, Dn, Up = load(base), load(down), load(up)
    pd.set_option("display.width", 250)
    for a in arms:
        A = load(a)
        print("==", a.name)
        print(paired(B, A).to_string())
        for true in (False, True):
            l, lo, hi = dial_lift(B, Dn, Up, A, true=true)
            print(f"  lift over the insulin-needs dial ({'true glucose' if true else 'CGM'}): {l:+.2f} TIR [{lo:+.2f},{hi:+.2f}]")


if __name__ == "__main__":
    main()
