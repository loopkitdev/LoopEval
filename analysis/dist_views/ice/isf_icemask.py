#!/usr/bin/env python3
"""Can ICE pick out meals for the ISF fit without biasing it? The invariance test.

The yardstick's raw slope (isf_shrink.fit: each fasting hour's glucose change on
insulin absorbed, 60-min blocks) is refitted with an extra exclusion: hours near
a meal-sized ICE episode. ICE is built at ISF_yardstick x m for m in MULTS, so
the mask itself depends on m. If the refitted slope tracks m, the mask is
leaking the selection ISF into the estimate; if it does not, the mask is driven
by meals.

ICE episodes, per person and m, on the 5-min panel:
  ice_m     v + m * ISF_yardstick * insulin absorbed
  baseline  median ice_m over the existing quiet steps
  excess    ice_m - baseline, 30-min centred mean
  episode   a run of excess > 0 whose area is >= MIN_G gram-equivalents
            (area / (m * ISF_yardstick / CR))
  mask      from PRE_H before each episode starts to POST_H after it ends
An hour is excluded because it is NEAR an episode, never because of its own ICE
alone — though an hour inside an episode is, by construction, near one.

Base quiet hours as before: no announced carbs on board, no user bolus in the
prior 4 h, no disruption, and the ICE bad-data screen (ice_raw.EXCLUDE).

Output: ice/isf_icemask.csv
"""
from __future__ import annotations
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
np.seterr(all="ignore")
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_first import _quiet_mask  # noqa
from isf_shrink import fit  # noqa
from ice_raw import excluded_on_grid  # noqa

MULTS = (0.35, 0.5, 0.75, 1.0, 1.25)
MIN_G, PRE_H, POST_H = 15.0, 1.0, 2.0
EST = pd.read_csv(S.OUT / "ice" / "isf_estimate.csv").set_index("alias")


def runs(mask):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return np.flatnonzero(d == 1), np.flatnonzero(d == -1)


def episode_mask(p, quiet, isf_y, m):
    u = (p["ia_abs"] / p["isf"]).to_numpy()
    v = p["v"].to_numpy()
    ice = v + m * isf_y * u
    base = np.nanmedian(ice[quiet])
    ex = pd.Series(ice - base).rolling(6, center=True, min_periods=4).mean().to_numpy()
    csf = m * isf_y / p["cr"].to_numpy()
    st, en = runs(np.nan_to_num(ex, nan=-1) > 0)
    mask = np.zeros(len(p), bool)
    n_ep = 0
    pre, post = int(PRE_H * 12), int(POST_H * 12)
    for a, b in zip(st, en):
        g = np.nansum(ex[a:b]) / np.nanmedian(csf[a:b])
        if g >= MIN_G:
            mask[max(a - pre, 0):min(b + post, len(p))] = True
            n_ep += 1
    return mask, n_ep


def person(alias):
    p = S.load(alias)
    p = p[p["bg"].notna() | p["v"].notna()]
    quiet = _quiet_mask(p) & ~excluded_on_grid(alias, p.index)
    isf_y = EST.loc[alias, "isf_est"]
    days = len(p) / 288
    out = {"alias": alias}
    c0, se0, n0 = fit(p, quiet, np.ones(len(p), bool))
    out.update(C_none=c0, se_none=se0, blk_none=n0)
    masks = {}
    for m in MULTS:
        mk, ne = episode_mask(p, quiet, isf_y, m)
        masks[m] = mk
        c, se, n = fit(p, quiet & ~mk, np.ones(len(p), bool))
        out.update({f"C_{m}": c, f"se_{m}": se, f"blk_{m}": n, f"ep_day_{m}": ne / days,
                    f"masked_quiet_{m}": (quiet & mk).sum() / max(quiet.sum(), 1)})
    # placebo: the x1.0 mask moved by 3 days (same coverage and episode
    # structure, unrelated to the meals of the hour being fitted)
    for lag_d in (3, 7):
        sh = np.roll(masks[1.0], lag_d * 288)
        c, se, n = fit(p, quiet & ~sh, np.ones(len(p), bool))
        out.update({f"C_shift{lag_d}": c, f"blk_shift{lag_d}": n,
                    f"masked_quiet_shift{lag_d}": (quiet & sh).sum() / max(quiet.sum(), 1)})
    # how much the masks agree across m
    a, b = masks[0.75], masks[1.25]
    out["mask_jaccard"] = (a & b).sum() / max((a | b).sum(), 1)
    return out


if __name__ == "__main__":
    al = list(EST.dropna(subset=["isf_est"]).index)
    S.datasets()
    with Pool(8) as pl:
        d = pd.DataFrame(pl.map(person, al))
    d.to_csv(S.OUT / "ice" / "isf_icemask.csv", index=False)
    ok = d[[f"C_{m}" for m in MULTS] + ["C_none"]].gt(0).all(axis=1)
    k = d[ok]
    print(f"{len(k)} of {len(d)} people with a positive slope under every mask")
    print(f"meal-sized episodes per day: " + ", ".join(f"x{m} {d[f'ep_day_{m}'].median():.1f}" for m in MULTS)
          + f";  share of quiet steps removed: " + ", ".join(f"x{m} {d[f'masked_quiet_{m}'].median():.0%}" for m in MULTS))
    print(f"mask agreement x0.75 vs x1.25 (Jaccard): median {d.mask_jaccard.median():.2f}")
    print(f"fasting blocks kept: none {d.blk_none.median():.0f}, " + ", ".join(f"x{m} {d[f'blk_{m}'].median():.0f}" for m in MULTS))
    for m in MULTS:
        r = np.log(k[f"C_{m}"] / k.C_none)
        print(f"  slope with ICE mask x{m} / without: median x{np.exp(r.median()):.3f}  (p10 x{np.exp(r.quantile(.1)):.2f}, p90 x{np.exp(r.quantile(.9)):.2f})")
    r = np.log(k["C_1.25"] / k["C_0.75"])
    for lag_d in (3, 7):
        kk = d[(d[f"C_shift{lag_d}"] > 0) & (d.C_none > 0)]
        r = np.log(kk[f"C_shift{lag_d}"] / kk.C_none)
        print(f"  PLACEBO (x1.0 mask moved {lag_d} days, removes {d[f'masked_quiet_shift{lag_d}'].median():.0%} of quiet steps): "
              f"slope / without: median x{np.exp(r.median()):.3f} (p10 x{np.exp(r.quantile(.1)):.2f}, p90 x{np.exp(r.quantile(.9)):.2f})")
    ms = np.log(np.array(MULTS))
    el = []
    for _, rr in k.iterrows():
        el.append(np.polyfit(ms, np.log([rr[f"C_{m}"] for m in MULTS]), 1)[0])
    print(f"  elasticity of slope to the mask ISF (log-log over all m): median {np.median(el):.3f} (p10 {np.percentile(el, 10):.2f}, p90 {np.percentile(el, 90):.2f})")
    print(f"\nINVARIANCE: slope(mask at x1.25) / slope(mask at x0.75): median x{np.exp(r.median()):.3f} "
          f"(p10 x{np.exp(r.quantile(.1)):.3f}, p90 x{np.exp(r.quantile(.9)):.3f}); the mask ISF itself moved x{1.25/0.75:.2f}")
    se = np.sqrt(k["se_1.25"] ** 2 + k["se_0.75"] ** 2)
    print(f"  per-person |log ratio| / its SE (both fits' SEs, overlapping data so conservative): median {(r.abs() / se).median():.2f}")
