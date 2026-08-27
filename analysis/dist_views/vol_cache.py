#!/usr/bin/env python3
"""Fit each volatility estimator once per person and cache its σ series.

Parameters are fitted on the FIRST 30% of each record; σ is then emitted for
the remaining 70%, so everything downstream is out of sample.

Also caches two rolling-window variants deliberately, because the difference
between them is itself a result: `roll_causal` uses only increments strictly
before t, while `roll_centred` uses a window centred on t and therefore
includes the very increment it is scaling. The centred version flatters itself
badly and an early version of this study used it by accident.
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
import vol_fit as VF                                       # noqa: E402
from loopeval_analysis import volatility as V              # noqa: E402

warnings.filterwarnings("ignore")
OUT = S.OUT
CACHE = OUT / "vol_cache"
FIT_FRAC = 0.30

# Per-person sensor noise from the structure-function intercept (view 11).
_f = OUT / "wholerecord.csv"
NOISE = (pd.read_csv(_f).set_index("alias")["sigma_meas"].to_dict()
         if _f.exists() else {})


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    meta = []
    for alias in S.cohort()["alias"]:
        rt, cad = VF.runs_with_times(alias)
        if not rt:
            continue
        fit_rt, test_rt = VF.split(rt, FIT_FRAC)
        fit_r = [r for r, _ in fit_rt]
        test_r = [r for r, _ in test_rt]
        if not fit_r or not test_r:
            continue

        vf = V.measurement_floor(NOISE.get(alias, 1.0))
        ew = V.fit_estimator("ewma", fit_r, cad, var_floor=vf)
        ga = V.fit_estimator("garch", fit_r, cad, var_floor=vf)
        ro = V.fit_estimator("rolling", fit_r, cad, var_floor=vf)

        win = max(int(round(120 / cad)), 6)
        centred = []
        for r in test_r:
            s = pd.Series(r)
            c = s.rolling(win, center=True, min_periods=win // 2).std().to_numpy()
            centred.append(np.sqrt(np.maximum(c ** 2, vf)))

        np.savez(CACHE / f"{alias}.npz",
                 t=np.concatenate([t.values for _, t in test_rt]),
                 eps=np.concatenate(test_r),
                 ewma=np.concatenate(ew.filter(test_r)),
                 garch=np.concatenate(ga.filter(test_r)),
                 roll_causal=np.concatenate(ro.filter(test_r)),
                 roll_centred=np.concatenate(centred),
                 cadence=cad)
        meta.append(dict(alias=alias, cadence=cad, var_floor=vf, lam=ew.lam,
                         omega=ga.omega, alpha=ga.alpha, beta=ga.beta,
                         persistence=ga.alpha + ga.beta,
                         roll_win_min=ro.window_min,
                         n_test=int(sum(len(r) for r in test_r))))
        print(f"  {alias:<10} cad {cad:.0f}  λ={ew.lam:.3f}  "
              f"garch α={ga.alpha:.3f} β={ga.beta:.3f} (α+β={ga.alpha+ga.beta:.3f})  "
              f"roll={ro.window_min:.0f}min  n_test={meta[-1]['n_test']}")

    m = pd.DataFrame(meta)
    m.to_csv(OUT / "vol_params.csv", index=False)
    print(f"\nmedian EWMA λ {m.lam.median():.3f} | median GARCH persistence "
          f"{m.persistence.median():.3f} | median rolling window "
          f"{m.roll_win_min.median():.0f} min")
    return 0


def load(alias: str) -> dict | None:
    f = CACHE / f"{alias}.npz"
    if not f.exists():
        return None
    z = np.load(f, allow_pickle=True)
    return {k: z[k] for k in z.files}


if __name__ == "__main__":
    raise SystemExit(main())
