#!/usr/bin/env python3
"""Steady-state basal — the insulin a person absorbs when nothing is happening.

A window is STEADY when, over its full length (default 3 h):
  * every 5-min step is fasting (no announced carbs on board, no user bolus in
    the 4 h before, no disruption — ice_first._quiet_mask), and
  * glucose ends within FLAT mg/dL of where it started, never wanders more
    than 2*FLAT from it, and sits inside the BAND, and
  * insulin on board changes by less than 0.3 U, so delivery ≈ absorption.
Then insulin absorbed is offsetting glucose output exactly, and the absorbed
rate (U/hr) estimates basal need. No ISF enters: absorbed units come from the
activity curve alone.

Windows end every 30 min and overlap; per person we take the median over
windows, overall and by local 6-hour block, against the scheduled basal over the
same windows. Variants re-run the criteria to see what they move.

Output: ice/steady_basal.csv (per person x variant), ice/steady_basal_windows.pkl
"""
from __future__ import annotations
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_first import _quiet_mask  # noqa

H = 12
VARIANTS = {
    "main":      dict(hours=3, flat=10, band=(80, 180)),
    "strict":    dict(hours=4, flat=5,  band=(80, 160)),
    "loose":     dict(hours=2, flat=15, band=(70, 200)),
    "night":     dict(hours=3, flat=10, band=(80, 180), tod=(0, 360)),
    "low":       dict(hours=3, flat=10, band=(80, 120)),
    "mid":       dict(hours=3, flat=10, band=(120, 160)),
    "high":      dict(hours=3, flat=10, band=(160, 250)),
}
BLOCKS = ((0, 360, "00-06"), (360, 720, "06-12"), (720, 1080, "12-18"), (1080, 1440, "18-24"))


def windows(p, hours, flat, band, tod=None):
    n = int(hours * H)
    quiet = _quiet_mask(p).astype(float)
    bg = p["bg"].to_numpy()
    u = p["ia_abs"].to_numpy() / p["isf"].to_numpy()            # U absorbed per bin
    iob = p["iob_abs"].to_numpy()
    sched = p["basal_sched"].to_numpy()
    t = p.index.asi8 // 10**9
    allq = pd.Series(quiet).rolling(n + 1).min().to_numpy() == 1
    contiguous = np.r_[np.zeros(n, bool), (t[n:] - t[:-n]) == n * 300]
    bg0 = np.r_[np.full(n, np.nan), bg[:-n]]
    bgmax = pd.Series(bg).rolling(n + 1).max().to_numpy()
    bgmin = pd.Series(bg).rolling(n + 1).min().to_numpy()
    iob0 = np.r_[np.full(n, np.nan), iob[:-n]]
    ok = (allq & contiguous & (np.abs(bg - bg0) <= flat)
          & (bgmax - bg0 <= 2 * flat) & (bg0 - bgmin <= 2 * flat)
          & (bgmin >= band[0]) & (bgmax <= band[1]) & (np.abs(iob - iob0) < 0.3))
    ends = np.flatnonzero(ok)
    ends = ends[(t[ends] // 60) % 30 < 5]                         # one window per 30 min
    absorbed = pd.Series(u).rolling(n).sum().to_numpy() * H / n   # U/hr over window
    sch = pd.Series(sched).rolling(n).mean().to_numpy()
    mid_tod = (p["tod_min"].to_numpy() - hours * 30) % 1440
    w = pd.DataFrame({"t": p.index[ends], "abs_uhr": absorbed[ends], "sched_uhr": sch[ends],
                      "bg": (bg[ends] + bg0[ends]) / 2, "tod": mid_tod[ends]})
    if tod is not None:
        w = w[(w.tod >= tod[0]) & (w.tod < tod[1])]
    return w


def person(alias):
    p = S.load(alias)
    rows, keep = [], None
    days = p["bg"].notna().sum() / (24 * H)
    for name, kw in VARIANTS.items():
        w = windows(p, **kw)
        r = {"alias": alias, "variant": name, "n_win": len(w), "win_per_week": len(w) / days * 7}
        if len(w) >= 20:
            r.update(est=w.abs_uhr.median(), sched=w.sched_uhr.median(),
                     ratio=(w.abs_uhr / w.sched_uhr).median(), bg=w.bg.median())
            for lo, hi, lab in BLOCKS:
                b = w[(w.tod >= lo) & (w.tod < hi)]
                if len(b) >= 10:
                    r[f"ratio_{lab}"] = (b.abs_uhr / b.sched_uhr).median()
                    r[f"est_{lab}"] = b.abs_uhr.median()
                    r[f"sched_{lab}"] = b.sched_uhr.median()
        rows.append(r)
        if name == "main":
            keep = w.assign(alias=alias)
    return rows, keep


if __name__ == "__main__":
    co = S.cohort()
    with Pool(8) as pool:
        res = pool.map(person, list(co.alias))
    d = pd.DataFrame([r for x in res for r in x[0]])
    d.to_csv(S.OUT / "ice" / "steady_basal.csv", index=False)
    pd.concat([x[1] for x in res]).to_pickle(S.OUT / "ice" / "steady_basal_windows.pkl")
    g = d.groupby("variant")
    print(pd.DataFrame({"people(>=20 win)": g.ratio.count(), "win/week": g.win_per_week.median(),
                        "ratio med": g.ratio.median(), "p10": g.ratio.quantile(.1),
                        "p90": g.ratio.quantile(.9), "bg": g.bg.median()}).round(2).to_string())
    m = d[d.variant == "main"]
    print("main, by block:", {b: round(m[f"ratio_{b}"].median(), 2) for _, _, b in BLOCKS},
          {b: int(m[f"ratio_{b}"].count()) for _, _, b in BLOCKS})
