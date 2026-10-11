"""Post-training calibration of the event-start hazards (meal, correction).

The start heads come out of training mis-calibrated by a run-dependent amount: fed real held-out inputs, the
v3 family's expected meals per day ranged 3.3-5.7 against a real 6.2 across nine trainings, under-predicting
in-sample as well. A generator that starts too few meals starves the near-low response and Loop's meal
dosing, and makes versions incomparable. One logit offset per head, fitted so that the teacher-forced
expected count equals the labeled count over a window the generator is NOT judged on, removes it; the plant
adds the offset before sampling (ck["calib"]).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq


def fit_bias(logits: np.ndarray, y: np.ndarray) -> float:
    """Offset b with sum(sigmoid(logits + b)) == sum(y), over the finite targets."""
    ok = np.isfinite(y) & np.isfinite(logits)
    l, n = logits[ok].astype(float), float(y[ok].sum())
    f = lambda b: (1 / (1 + np.exp(-(l + b)))).sum() - n
    return float(brentq(f, -10, 10))
