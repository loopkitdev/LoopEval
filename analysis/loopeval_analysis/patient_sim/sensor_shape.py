"""Sensor variants over simulated TRUE glucose: FDA score (sensor_fit.score) beside two shape measures the donors' CGM
gives directly — the lag-1 / lag-2 autocorrelation of 5-min increments and the daytime turning-point rate of the 15-min
centred mean (5–15 / > 15 mg/dL per hour). Donors' quiet-hour reference: lag-1 0.511, lag-2 0.263, turns 0.375 / 0.614
(LESSONS 295; the base family over the same bodies gives the scale for "quiet vs all-day").

    python -m loopeval_analysis.patient_sim.sensor_shape <cohort-root> "Dexcom G7" base sensor_a1=0.9,sensor_a2=-0.2 ...
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from .sensor_fit import parse, run_sensor, score, truths


def shape(bgs, family, ov, seed0=0) -> dict:
    l1, l2, ts, tb, hours = [], [], 0, 0, 0.0
    for i, bg in enumerate(bgs):
        a = run_sensor(bg, family, seed0 + 2 * i, ov, 10_000 + i)
        m = np.arange(len(a)); k = (m >= 1800) & np.isfinite(a)
        ph = int(np.argmax(k)) % 5
        g = pd.Series(a[(m >= 1800) & (m % 5 == ph)])
        d = g.diff()
        l1.append(d.autocorr(1)); l2.append(d.autocorr(2))
        s = g.rolling(3, center=True, min_periods=1).mean().to_numpy(); mm = m[(m >= 1800) & (m % 5 == ph)]
        day = ((mm % 1440) >= 360)
        last, dirn = s[0], 0
        for j in range(1, len(s)):
            if not (day[j] and np.isfinite(s[j]) and np.isfinite(s[j - 1])): last, dirn = s[j], 0; continue
            st = s[j] - s[j - 1]
            nd = 1 if st > 0 else -1 if st < 0 else dirn
            if dirn and nd != dirn:
                amp = abs(s[j - 1] - last)
                if 5 <= amp < 15: ts += 1
                elif amp >= 15: tb += 1
                last = s[j - 1]
            dirn = nd
        hours += day.sum() * 5 / 60.0
    return dict(acf1=float(np.nanmedian(l1)), acf2=float(np.nanmedian(l2)), turns_small=ts / hours, turns_big=tb / hours)


def main():
    root, family, variants = sys.argv[1], sys.argv[2], sys.argv[3:]
    bgs = truths(root, 20)
    rows = {}
    for v in variants:
        sc = score(bgs, family, parse(v)); sh = shape(bgs, family, parse(v))
        rows[v] = dict(loss=sc["loss"], pard=sc["pard"], mard_70_180=sc.get("true70-180_mard", np.nan), step_sd=sc["step_sd"], **sh)
    pd.set_option("display.width", 250)
    print(pd.DataFrame(rows).T.round(3).to_string())


if __name__ == "__main__":
    main()
