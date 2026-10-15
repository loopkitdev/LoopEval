#!/usr/bin/env python3
"""ICE episodes — contiguous stretches where counteraction runs above (or below)
the person's fasting baseline, sized in gram-equivalents, and matched to
announced carbohydrate.

ICE is recomputed at a scaled ISF, ice_m = v + m * ia_abs, for m in MULTS, so
every statistic can be read against the ISF assumption behind it.

  baseline   median ICE in fasting bins (no carbs on board, no user bolus in
             4 h, not disrupted)
  excess     ICE - baseline, 30-min centred mean
  episode    maximal run of excess > 0 (positive) or < 0 (negative); its area
             is the summed excess in mg/dL, divided by the carb sensitivity
             factor m*ISF/CR to give gram-equivalents. The sum of a velocity
             telescopes, so sensor noise barely moves an episode's area.
  announced  a carb entry of >= 5 g between 60 min before the start and the
             episode's end

Output: ice/episodes.pkl (every episode >= 5 g-eq at every m) and
        ice/episode_person.csv (per person x m summaries)
"""
from __future__ import annotations
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa
from ice_first import _quiet_mask  # noqa

H = 12
MULTS = (0.5, 0.75, 1.0, 1.25)
MIN_G = 5.0
SIZE_G = 10.0          # "meal-sized" floor for the summaries


def runs(mask):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return np.flatnonzero(d == 1), np.flatnonzero(d == -1)


def person(alias):
    p = S.load(alias)
    v = p["v"].to_numpy(); ia = p["ia_abs"].to_numpy()
    isf = p["isf"].to_numpy(); cr = p["cr"].to_numpy()
    cob = p["cob"].to_numpy()
    dis = p["disrupted"].astype(bool).to_numpy() | np.isnan(v)
    quiet = _quiet_mask(p)
    jump = np.diff(cob, prepend=cob[0])
    entry = np.flatnonzero(jump >= 5)
    tod = p["tod_min"].to_numpy()
    days = (~dis).sum() / (24 * H)
    carb_g_day = jump[entry].sum() / days
    eps, summ = [], []
    for m in MULTS:
        ice = v + m * ia
        base = np.nanmedian(ice[quiet])
        ex = pd.Series(np.where(dis, np.nan, ice - base)).rolling(6, center=True, min_periods=4).mean().to_numpy()
        csf = m * isf / cr
        for sign in (1, -1):
            st, en = runs(np.nan_to_num(sign * ex, nan=-1) > 0)
            for a, b in zip(st, en):
                area_mg = np.nansum(ex[a:b])            # per-bin units sum → mg/dL
                g = sign * area_mg / np.nanmedian(csf[a:b])
                if g < MIN_G:
                    continue
                ann = ((entry >= a - H) & (entry < b)).any()
                eps.append((alias, m, sign, p.index[a], (b - a) * 5, g, ann,
                            jump[entry[(entry >= a - H) & (entry < b)]].sum() if ann else 0.0,
                            tod[a], np.nanmax(sign * ex[a:b]) * H))
        e = pd.DataFrame([x for x in eps if x[1] == m],
                         columns=["alias", "m", "sign", "t", "dur_min", "g", "announced",
                                  "g_entered", "tod", "peak"])
        pos = e[(e.sign == 1) & (e.g >= SIZE_G)]
        neg = e[(e.sign == -1) & (e.g >= SIZE_G)]
        summ.append({"alias": alias, "m": m, "baseline": base * H,
                     "pos_per_day": len(pos) / days, "neg_per_day": len(neg) / days,
                     "pos_g_day": pos.g.sum() / days, "neg_g_day": neg.g.sum() / days,
                     "unann_share_g": pos.loc[~pos.announced, "g"].sum() / max(pos.g.sum(), 1e-9),
                     "unann_per_day": (~pos.announced).sum() / days,
                     "ann_ratio": (pos.loc[pos.announced, "g"].sum()
                                   / max(pos.loc[pos.announced, "g_entered"].sum(), 1e-9)),
                     "carb_g_day": carb_g_day,
                     "entries_seen": np.mean([((pos.t <= p.index[i] + pd.Timedelta("60min"))
                                               & (pos.t + pd.to_timedelta(pos.dur_min, "min") > p.index[i])).any()
                                              for i in entry if jump[i] >= 10]) if len(entry) else np.nan})
    return eps, summ


if __name__ == "__main__":
    co = S.cohort()
    with Pool(8) as pool:
        res = pool.map(person, list(co.alias))
    eps = pd.DataFrame([x for r in res for x in r[0]],
                       columns=["alias", "m", "sign", "t", "dur_min", "g", "announced",
                                "g_entered", "tod", "peak"])
    summ = pd.DataFrame([x for r in res for x in r[1]])
    eps.to_pickle(S.OUT / "ice" / "episodes.pkl")
    summ.to_csv(S.OUT / "ice" / "episode_person.csv", index=False)
    cols = ["baseline", "pos_per_day", "neg_per_day", "pos_g_day", "neg_g_day",
            "unann_share_g", "unann_per_day", "ann_ratio", "entries_seen", "carb_g_day"]
    print(summ.groupby("m")[cols].median().round(2).T.to_string())
