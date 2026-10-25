"""Meal pulse shape for the v3 generator: excess ICE of a meal over time since onset.

A lognormal in time: rate(t) = size_geq * geq * f(t), f the lognormal density in hours with
median m and log-sd s, so the pulse integrates to the meal's size and ENDS by construction. m and s
come from the labeled peak time and duration:
    mode = m * exp(-s^2) = peak,   90% of mass by m * exp(1.2816 s) = duration
    => s^2 + 1.2816 s - ln(duration / peak) = 0
"""
from __future__ import annotations

import numpy as np

Z90 = 1.2816


def params(peak_h, dur_h):
    peak = np.maximum(np.asarray(peak_h, float), 5 / 60)
    dur = np.maximum(np.asarray(dur_h, float), peak * 1.2)
    L = np.log(dur / peak)
    s = (-Z90 + np.sqrt(Z90 ** 2 + 4 * L)) / 2
    m = peak * np.exp(s ** 2)
    return m, np.maximum(s, 0.05)


def rate(t_h, size_mgdl, m, s):
    """mg/dL per hour at t_h hours after onset (0 before onset)."""
    t = np.asarray(t_h, float)
    out = np.zeros_like(t)
    ok = t > 0
    out[ok] = size_mgdl * np.exp(-0.5 * ((np.log(t[ok]) - np.log(m)) / s) ** 2) / (t[ok] * s * np.sqrt(2 * np.pi))
    return out


def remaining(t_h, size_mgdl, m, s):
    """mg/dL of the pulse still to come at t_h hours after onset (all of it before onset)."""
    from scipy.special import ndtr
    t = np.asarray(t_h, float)
    out = np.full_like(t, float(size_mgdl))
    ok = t > 0
    out[ok] = size_mgdl * (1 - ndtr((np.log(t[ok]) - np.log(m)) / s))
    return out


def reconstruct(index, meals, geq):
    """Sum of all labeled meal pulses on a 5-min DatetimeIndex, mg/dL per hour."""
    tot = np.zeros(len(index))
    tn = index.asi8
    m_, s_ = params(meals.peak_h.to_numpy() + 2.5 / 60, meals.dur_h.to_numpy())
    for i, r in enumerate(meals.itertuples()):
        t_h = (tn - r.onset.value) / 3.6e12
        win = (t_h > 0) & (t_h < 12)
        tot[win] += rate(t_h[win], r.size_g * geq, m_[i], s_[i])
    return tot
