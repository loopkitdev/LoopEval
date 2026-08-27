#!/usr/bin/env python3
"""Fit the volatility estimators per person and score them out of sample.

Split is chronological — train on the first 70% of each person's record, test
on the last 30%. Everything reported comes from the test split only.

Writes vol_scores.csv and vol_sigma/<alias>.npz (test-split σ aligned to the
panel timestamps, so the therapy questions can be asked on held-out data).
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S                                          # noqa: E402
from loopeval_analysis import dists as D                   # noqa: E402
from loopeval_analysis import volatility as V              # noqa: E402

warnings.filterwarnings("ignore")
OUT = S.OUT
TRAIN_FRAC = 0.70

# Per-person sensor noise (view 11) sets the floor a fitted variance may not
# go below — increments of a noisily-measured series have variance >= 2σ².
_f = OUT / "wholerecord.csv"
NOISE = (pd.read_csv(_f).set_index("alias")["sigma_meas"].to_dict()
         if _f.exists() else {})


ANALYSIS_CADENCE_MIN = 5.0


def runs_with_times(alias: str, cadence_min: float = ANALYSIS_CADENCE_MIN):
    """Contiguous raw runs as (increments, timestamps-of-the-increment, cadence).

    The timestamp attached to an increment is the time of its LATER sample, so
    a σ estimated from increments strictly before t carries timestamp t.

    Streams faster than `cadence_min` are subsampled down to it. Two reasons:
    the controller acts on a five-minute step, so that is the interval whose
    volatility matters; and one stream in this cohort reports every minute with
    consecutive samples that are clearly not independent measurements — its
    one-minute increments have a smaller SD than the measurement noise implies
    is possible, so a noise floor estimated at five minutes cannot be applied
    to them. Subsampling puts every dataset on the same footing.
    """
    from loopeval_analysis import dists as DD
    ds = S.datasets()[alias]
    raw = S.clip_window(alias, DD._load_glucose(ds.glucose_path))
    dt = raw.index.to_series().diff().dt.total_seconds() / 60.0
    cad = float(np.round(dt.median() * 2) / 2) or 5.0
    if cad < cadence_min - 0.25:                 # subsample a faster stream
        step = max(int(round(cadence_min / cad)), 1)
        raw = raw.iloc[::step]
        dt = raw.index.to_series().diff().dt.total_seconds() / 60.0
        cad = float(np.round(dt.median() * 2) / 2) or cadence_min
    ok = ((dt >= 0.8 * cad) & (dt <= 1.2 * cad)).to_numpy()
    v = raw.to_numpy()
    idx = raw.index
    out, start = [], 0
    for i in range(1, len(v)):
        if not ok[i]:
            if i - start >= 40:
                out.append((np.diff(v[start:i]), idx[start + 1:i]))
            start = i
    if len(v) - start >= 40:
        out.append((np.diff(v[start:]), idx[start + 1:]))
    return out, cad


def split(rt, frac=TRAIN_FRAC):
    """Chronological split by cumulative sample count, keeping runs intact."""
    total = sum(len(r) for r, _ in rt)
    cut, seen = total * frac, 0
    tr, te = [], []
    for r, t in rt:
        if seen + len(r) <= cut:
            tr.append((r, t))
        elif seen >= cut:
            te.append((r, t))
        else:                                    # the run straddling the cut
            k = int(cut - seen)
            if k > 20:
                tr.append((r[:k], t[:k]))
            if len(r) - k > 20:
                te.append((r[k:], t[k:]))
        seen += len(r)
    return tr, te


def main() -> int:
    (OUT / "vol_sigma").mkdir(parents=True, exist_ok=True)
    rows = []
    for alias in S.cohort()["alias"]:
        rt, cad = runs_with_times(alias)
        if not rt:
            continue
        tr, te = split(rt)
        tr_r = [r for r, _ in tr]
        te_r = [r for r, _ in te]
        if not tr_r or not te_r:
            continue

        vf = V.measurement_floor(NOISE.get(alias, 1.0))
        fitted = {}
        for kind in ("rolling", "ewma", "garch"):
            try:
                fitted[kind] = V.fit_estimator(kind, tr_r, cad, var_floor=vf)
            except Exception as e:                            # noqa: BLE001
                print(f"  {alias}/{kind}: {type(e).__name__}")

        for kind, est in fitted.items():
            sc = V.evaluate(est, te_r, cad)
            sc["alias"] = alias
            sc["cadence"] = cad
            if kind == "garch":
                sc["params"] = f"w={est.omega:.4f} a={est.alpha:.3f} b={est.beta:.3f}"
                sc["persistence"] = est.alpha + est.beta
            elif kind == "ewma":
                sc["params"] = f"lam={est.lam:.3f}"
                sc["persistence"] = est.lam
            else:
                sc["params"] = f"win={est.window_min:.0f}min"
                sc["persistence"] = np.nan
            rows.append(sc)

        # Persist the best estimator's test-split σ, timestamped.
        best_kind = min(fitted, key=lambda k: V.evaluate(fitted[k], te_r, cad)["nll"])
        sig = fitted[best_kind].filter(te_r)
        ts = np.concatenate([t.values for _, t in te])
        sg = np.concatenate(sig)
        ep = np.concatenate(te_r)
        np.savez(OUT / "vol_sigma" / f"{alias}.npz", t=ts, sigma=sg, eps=ep,
                 kind=best_kind, cadence=cad)
        g = [r for r in rows if r["alias"] == alias]
        print(f"  {alias:<10} cad {cad:.0f}min  best={best_kind:<8} " +
              "  ".join(f"{r['estimator']}: R2 {r['r2_logvar']:.3f} nll {r['nll']:.4f}"
                        for r in g))

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "vol_scores.csv", index=False)
    print(f"\nwrote {OUT}/vol_scores.csv")

    piv = df.pivot(index="alias", columns="estimator", values="r2_logvar")
    print("\nout-of-sample R² predicting log realised 30-min volatility")
    print(piv.round(3).to_string())
    print("\nmedian:", piv.median().round(3).to_dict())
    kz = df.pivot(index="alias", columns="estimator", values="z_kurtosis")
    print("\nexcess kurtosis of standardised increments (raw increment ≈ 3.7)")
    print(kz.round(2).to_string())
    print("median:", kz.median().round(2).to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
