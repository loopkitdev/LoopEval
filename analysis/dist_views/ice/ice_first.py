#!/usr/bin/env python3
"""ICE first pass — per-person table of what the counteraction signal looks like.

ICE (insulin counteraction effect) = glucose velocity + modelled insulin activity,
in mg/dL per hour. The panel carries two conventions:
  ice_abs  every unit delivered is acting (basal included)
  ice_net  Loop's convention: scheduled basal booked at zero

Per person this writes:
  * fasting baseline      ICE in "quiet" bins (no carbs on board, no user bolus in
                          the last 4 h, not disrupted), overnight and all-day
  * effective ISF         the ISF that makes fasting ICE uncorrelated with insulin
                          absorption: OLS of the 30-min glucose change on units
                          absorbed over the same 30 min, fasting blocks only
  * announced meals       ICE excess over the fasting baseline for 4 h after an
                          isolated carb entry, in gram-equivalents (/CSF), against
                          the grams entered
  * unannounced share     share of positive ICE excess falling outside any
                          announced-carb absorption window

Output: runs/.../ice/ice_person.csv
"""
from __future__ import annotations

import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa: E402

OUTDIR = S.OUT / "ice"
H = 12.0                      # bins per hour
QUIET_BOLUS_H = 4.0
MEAL_H = 4.0
BLOCK = 6                     # 30-min blocks for the ISF regression


def _quiet_mask(p: pd.DataFrame) -> np.ndarray:
    ub = p["manual_bolus_u"].fillna(0).to_numpy()
    n = int(QUIET_BOLUS_H * H)
    recent = pd.Series(ub > 0).rolling(n, min_periods=1).max().to_numpy() > 0
    return ((p["cob"].to_numpy() <= 0) & ~recent
            & ~p["disrupted"].astype(bool).to_numpy()
            & p["v"].notna().to_numpy())


def _isf_fit(p: pd.DataFrame, quiet: np.ndarray, night: np.ndarray | None = None):
    """OLS of block glucose change on block units absorbed, fasting blocks only."""
    isf = p["isf"].to_numpy()
    u = p["ia_abs"].to_numpy() / isf              # units absorbing per bin
    v = p["v"].to_numpy()
    m = quiet if night is None else quiet & night
    n = len(p) // BLOCK * BLOCK
    shape = (-1, BLOCK)
    mb = m[:n].reshape(shape).all(1)
    dv = v[:n].reshape(shape).sum(1)[mb]
    du = u[:n].reshape(shape).sum(1)[mb]
    if len(dv) < 200 or np.std(du) == 0:
        return np.nan, np.nan, 0
    X = np.column_stack([np.ones_like(du), du])
    beta, *_ = np.linalg.lstsq(X, dv, rcond=None)
    # intercept per hour (glucose rise with no insulin), slope = -ISF
    return -beta[1], beta[0] * (60 / (5 * BLOCK)), int(len(dv))


def person(alias: str) -> dict:
    p = S.load(alias)
    p = p[p["bg"].notna()]
    quiet = _quiet_mask(p)
    tod = p["tod_min"].to_numpy()
    night = (tod >= 0) & (tod < 360)
    ice_a = p["ice_abs"].to_numpy() * H
    ice_n = p["ice_net"].to_numpy() * H
    isf = p["isf"].to_numpy()
    cr = p["cr"].to_numpy()
    sched = p["basal_sched"].to_numpy()

    out = {"alias": alias, "n_bins": len(p),
           "quiet_frac": quiet.mean(), "night_quiet_frac": (quiet & night).sum() / max(night.sum(), 1)}
    q, qn = quiet, quiet & night
    out["ice_abs_quiet"] = np.nanmedian(ice_a[q])
    out["ice_abs_night"] = np.nanmedian(ice_a[qn])
    out["ice_net_quiet"] = np.nanmedian(ice_n[q])
    out["ice_net_night"] = np.nanmedian(ice_n[qn])
    out["ice_abs_all"] = np.nanmean(ice_a)
    # the basal schedule, expressed as glucose it is meant to cover
    out["sched_cover_night"] = np.nanmedian((sched * isf)[qn])
    out["isf_sched"] = np.nanmedian(isf)
    out["cr_sched"] = np.nanmedian(cr)

    k, icpt, nb = _isf_fit(p, quiet)
    kn, icptn, nbn = _isf_fit(p, quiet, night)
    out.update(isf_eff=k, egp_eff=icpt, n_blocks=nb,
               isf_eff_night=kn, egp_eff_night=icptn, n_blocks_night=nbn)

    # ─── announced meals ────────────────────────────────────────────────
    base = out["ice_abs_quiet"]
    cob = p["cob"].to_numpy()
    # carb entries = upward jumps in COB
    jump = np.diff(cob, prepend=cob[0])
    idx = np.flatnonzero(jump >= 10)
    n = int(MEAL_H * H)
    ratios, grams = [], []
    tsec = p.index.asi8 // 10**9
    for i in idx:
        lo, hi = i - n, i + n
        if lo < 0 or hi >= len(p):
            continue
        # isolated: no other entry of >=5 g within +-4 h, window contiguous
        others = np.flatnonzero(jump[lo:hi] >= 5) + lo
        if len(others) != 1 or tsec[hi] - tsec[i] != n * 300:
            continue
        w = slice(i, i + n)
        e = ice_a[w]
        if np.isnan(e).mean() > 0.1:
            continue
        excess = np.nansum(e - base) / H          # mg/dL over the window
        csf = np.nanmedian(isf[w] / cr[w])
        ratios.append(excess / csf / jump[i])
        grams.append(jump[i])
    out["n_meals"] = len(ratios)
    out["meal_ratio"] = np.median(ratios) if len(ratios) >= 10 else np.nan
    out["meal_g_median"] = np.median(grams) if grams else np.nan

    # ─── unannounced share of positive excess ───────────────────────────
    sm = pd.Series(ice_a - base).rolling(6, center=True, min_periods=3).mean().to_numpy()
    pos = np.clip(sm, 0, None)
    ok = ~np.isnan(pos) & ~p["disrupted"].astype(bool).to_numpy()
    fed = cob > 0
    tot = pos[ok].sum()
    out["unannounced_share"] = pos[ok & ~fed].sum() / tot if tot > 0 else np.nan
    out["excess_per_day"] = tot / H / (ok.sum() / (24 * H))      # mg/dL per day
    out["excess_g_day"] = out["excess_per_day"] / np.nanmedian(isf / cr)
    return out


def main():
    OUTDIR.mkdir(exist_ok=True)
    co = S.cohort()
    with Pool(8) as pool:
        rows = pool.map(person, list(co["alias"]))
    df = pd.DataFrame(rows).merge(co, on="alias")
    df.to_csv(OUTDIR / "ice_person.csv", index=False)
    print(f"wrote {len(df)} people → {OUTDIR/'ice_person.csv'}")


if __name__ == "__main__":
    main()
