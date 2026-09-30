#!/usr/bin/env python3
"""Is this a real person's record, and is it intact?

A screen for synthetic or damaged data, on BOTH streams. Nothing systematic
existed before this: the cohort had a point-outlier filter on the glucose
increment (`traits.split_impossible`, 8 mg/dL/min), one hardcoded window trim
for the single donor whose dual-sensor problem was noticed by accident, and no
insulin-side check at all.

Each check is named, per-person, and reported as a number rather than a verdict,
because almost every signature here has an innocent explanation as well as a
guilty one — a long flat run is a stuck sensor OR a calm night, a repeated bolus
amount is a synthetic generator OR someone who always takes 6 units with dinner.
The output is a table to sort, not a pass/fail.

GLUCOSE
  dup_exact        share of (time, value) pairs appearing more than once
  flat_run         longest run of identical consecutive values (samples)
  flat_frac        share of increments exactly zero
  repeat_block     longest subsequence of >= 12 samples that recurs elsewhere
  alt_lag1         lag-1 autocorrelation of the increment (<= -0.6 = two sensors)
  sub2min_frac     share of consecutive gaps under 2 minutes
  sub2min_delta    median |dBG| across those pairs (~1 real, 0 re-upload, ~14 two sensors)
  per_day          samples per day (576 where 288 is expected = two streams)
  off_lattice      share of values off the person's modal value spacing
  impossible_day   steps faster than 8 mg/dL/min, per day
  clock_back       timestamps that go backwards
  digit_chi        chi-square of the last-digit distribution against uniform

INSULIN
  bolus_dup        share of boluses sharing a (time, amount) with another
  bolus_top_frac   share of all boluses taking the single most common amount
  bolus_off_grid   share of bolus amounts off a 0.05 U grid
  bolus_sec0       share of bolus timestamps at exactly :00 seconds
  basal_extreme    hours at a basal rate above 15 U/hr
  sched_frac       share of basal time exactly equal to the scheduled rate
  tdd_dup_days     days whose total matches another day to 0.01 U
  tdd_zero_days    days with data but no delivery
  carb_max         largest single carbohydrate entry (g)
  dose_overlap     share of basal records overlapping the next one

Run:  python3 integrity.py            (writes integrity.csv)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S                                            # noqa: E402
from loopeval_analysis import dists as D                      # noqa: E402
from loopeval_analysis.traits import MAX_MGDL_PER_MIN         # noqa: E402

BLOCK = 12          # a recurring subsequence this long is not chance
CEIL, FLOOR, TOL = 401.0, 39.0, 0.5   # the clamps as they arrive, in mg/dL

# S.datasets() re-execs build.py and rescans every export root, so calling it
# per person per stream turned a two-minute screen into a stalled one.
_DS: dict = {}


def _ds(alias: str):
    if not _DS:
        _DS.update(S.datasets())
    return _DS[alias]


def longest_flat(v: np.ndarray, mask: np.ndarray | None = None) -> int:
    """Longest run of identical consecutive values, optionally restricted.

    Restriction matters: the longest flat run in this cohort is always a stretch
    pinned at the sensor ceiling, which is a real excursion being clamped rather
    than a stuck reading. Away from the clamps, a long flat run has no innocent
    reading.
    """
    if not len(v):
        return 0
    same = np.r_[False, v[1:] == v[:-1]]
    if mask is not None:
        same = same & mask
    best = run = 0
    for s in same:
        run = run + 1 if s else 0
        best = max(best, run)
    return int(best + 1) if best else 0


def longest_repeat_block(v: np.ndarray, block: int = BLOCK) -> int:
    """Longest window length that occurs at two non-overlapping positions.

    Hashes fixed-length windows and grows only if a collision is found, so the
    cost is linear per length tried rather than quadratic in the record.
    """
    n = len(v)
    if n < 2 * block:
        return 0
    best = 0
    length = block
    while length <= n // 2:
        seen: dict[bytes, int] = {}
        hit = False
        for i in range(n - length + 1):
            key = v[i:i + length].tobytes()
            j = seen.get(key)
            if j is not None and i - j >= length:
                hit = True
                break
            if key not in seen:
                seen[key] = i
        if not hit:
            break
        best = length
        length *= 2
    return int(best)


MIN_DISTINCT = 6    # a block with fewer distinct values is a clamp, not a pattern


def longest_repeat_block_varying(v: np.ndarray, block: int = BLOCK) -> int:
    """As longest_repeat_block, but a window must genuinely VARY to count.

    Requiring merely "not constant" was too weak: every block it found was 99%
    pinned at the sensor ceiling with one differing sample at the start, so the
    check rediscovered the clamp. A real copy-paste block carries the ordinary
    variation of a trace, hence a distinct-value floor.
    """
    n = len(v)
    if n < 2 * block:
        return 0
    best, length = 0, block
    while length <= n // 2:
        seen: dict[bytes, int] = {}
        hit = False
        for i in range(n - length + 1):
            w = v[i:i + length]
            if len(np.unique(w)) < MIN_DISTINCT:
                continue
            key = w.tobytes()
            j = seen.get(key)
            if j is not None and i - j >= length:
                hit = True
                break
            if key not in seen:
                seen[key] = i
        if not hit:
            break
        best, length = length, length * 2
    return int(best)


def last_digit_chi(v: np.ndarray) -> float:
    """Chi-square of the last decimal digit against uniform, per 1000 samples.

    A human-entered or synthetic series often prefers 0 and 5; a sensor should
    not. Normalised by n so records of different lengths are comparable.
    """
    w = v[np.isfinite(v)]
    w = np.round(w).astype(int) % 10
    if len(w) < 200:
        return np.nan
    obs = np.bincount(w, minlength=10).astype(float)
    exp = len(w) / 10.0
    return float(((obs - exp) ** 2 / exp).sum() / len(w) * 1000)


def glucose_checks(alias: str) -> dict:
    ds = _ds(alias)
    raw = S.clip_window(alias, D._load_glucose(ds.glucose_path))
    out: dict[str, float] = {}
    if raw is None or len(raw) < 500:
        return out
    t = raw.index
    v = raw.to_numpy(dtype=float)
    dt = t.to_series().diff().dt.total_seconds() / 60.0
    days = max((t[-1] - t[0]).total_seconds() / 86400.0, 1.0)

    pairs = pd.Series(list(zip(t.astype("int64") // 10**9, np.round(v, 4))))
    out["dup_exact"] = 100 * (1 - pairs.nunique() / len(pairs))
    clamped = (v >= CEIL - TOL) | (v <= FLOOR + TOL)
    out["flat_run"] = longest_flat(v)
    out["flat_run_free"] = longest_flat(v, ~clamped)
    out["clamp_frac"] = 100 * float(np.mean(clamped))
    out["ceil_hours"] = float(longest_flat(v, v >= CEIL - TOL)
                              * max(float(np.nanmedian(dt)), 1.0) / 60.0)
    d1 = np.diff(v)
    out["flat_frac"] = 100 * np.mean(d1 == 0)
    out["repeat_block"] = longest_repeat_block(np.round(v, 3))
    # A constant block recurs trivially, so the interesting version excludes
    # windows that carry no variation at all.
    out["repeat_block_var"] = longest_repeat_block_varying(np.round(v, 3))
    out["alt_lag1"] = (float(np.corrcoef(d1[:-1], d1[1:])[0, 1])
                       if len(d1) > 10 else np.nan)
    sub2 = (dt < 2).to_numpy()
    out["sub2min_frac"] = 100 * np.nanmean(sub2)
    if sub2[1:].sum() >= 20:
        out["sub2min_delta"] = float(np.median(np.abs(d1[sub2[1:]])))
    out["per_day"] = len(v) / days
    u = np.unique(v)
    du = np.diff(u)
    du = du[du > 1e-9]
    if len(du):
        step = float(np.median(du))
        if step > 0:
            off = np.median((v / step) % 1.0)          # the lattice's phase
            resid = np.abs(((v / step) - off + 0.5) % 1.0 - 0.5)
            out["lattice_step"] = step
            out["off_lattice"] = 100 * np.mean(resid > 0.02)
    cad = max(float(np.round(np.nanmedian(dt) * 2) / 2), 0.5)
    out["impossible_day"] = float(np.sum(np.abs(d1) > MAX_MGDL_PER_MIN * cad) / days)
    out["clock_back"] = int((dt < 0).sum())
    out["digit_chi"] = last_digit_chi(v)
    return out


def insulin_checks(alias: str) -> dict:
    ds = _ds(alias)
    out: dict[str, float] = {}
    try:
        doses = json.load(open(ds.doses_path))
    except Exception:
        return out
    if not doses:
        return out
    df = pd.DataFrame(doses)
    for c in ("startDate", "endDate"):
        if c in df:
            df[c] = pd.to_datetime(df[c], errors="coerce", utc=True)
    df["volume"] = pd.to_numeric(df.get("volume"), errors="coerce")

    bol = df[df["deliveryType"].eq("bolus")].dropna(subset=["volume"])
    if len(bol) >= 20:
        key = list(zip(bol["startDate"].astype("int64") // 10**9,
                       np.round(bol["volume"], 4)))
        out["bolus_dup"] = 100 * (1 - len(set(key)) / len(key))
        cnt = Counter(np.round(bol["volume"], 3))
        out["bolus_top_frac"] = 100 * cnt.most_common(1)[0][1] / len(bol)
        out["bolus_sec0"] = 100 * np.mean(bol["startDate"].dt.second == 0)
        out["n_bolus"] = len(bol)
        man = bol[~bol.get("automatic", pd.Series(False, index=bol.index))
                  .fillna(False).astype(bool)]
        if len(man) >= 20:
            grid = np.round(man["volume"] / 0.05) * 0.05
            out["man_off_grid"] = 100 * np.mean(np.abs(grid - man["volume"]) > 1e-4)
            out["n_manual"] = len(man)
            out["man_top_frac"] = 100 * Counter(
                np.round(man["volume"], 3)).most_common(1)[0][1] / len(man)

    bas = df[df["deliveryType"].eq("basal")].dropna(subset=["startDate", "endDate"])
    if len(bas) >= 20:
        bas = bas.sort_values("startDate")
        hrs = (bas["endDate"] - bas["startDate"]).dt.total_seconds() / 3600.0
        rate = pd.to_numeric(bas.get("tempRate"), errors="coerce")
        rate = rate.where(rate.notna(), bas["volume"] / hrs.replace(0, np.nan))
        out["basal_extreme"] = float(hrs[rate > 15].sum())
        out["basal_max_rate"] = float(np.nanmax(rate))
        nxt = bas["startDate"].shift(-1)
        out["dose_overlap"] = 100 * np.nanmean(
            (bas["endDate"] > nxt + pd.Timedelta(seconds=1)).to_numpy())

    tot = df.dropna(subset=["startDate", "volume"])
    if len(tot):
        day = tot.set_index("startDate")["volume"].resample("1D").sum()
        day = day[day.index.isin(day.index)]
        out["tdd_zero_days"] = int((day == 0).sum())
        r = day[day > 0].round(2)
        out["tdd_dup_days"] = int(len(r) - r.nunique())

    # Does the automation ever move the basal off the schedule? A closed-loop
    # record that never does is either not looping or not reconstructed.
    try:
        c = D.clean(S.load(alias))
        eff, sch = c["basal_eff"].to_numpy(), c["basal_sched"].to_numpy()
        ok = np.isfinite(eff) & np.isfinite(sch)
        if ok.sum() > 500:
            out["at_schedule"] = 100 * np.mean(np.abs(eff[ok] - sch[ok]) < 1e-6)
    except Exception:
        pass

    # Was the automation dosing hard through the longest ceiling stretch? A
    # real excursion drives delivery up; a stuck sensor reading 401 would too,
    # so this cannot prove authenticity — but ORDINARY delivery through 30
    # hours of "400 mg/dL" is evidence the reading was not believed.
    try:
        c = D.clean(S.load(alias))
        bg = c["bg"].to_numpy()
        dl = c["basal_eff"].to_numpy() / 12.0 + c["bolus_u"].fillna(0).to_numpy()
        hi = bg >= CEIL - TOL
        if hi.sum() >= 24 and np.isfinite(dl).sum() > 500:
            out["ceil_delivery_ratio"] = float(np.nanmean(dl[hi])
                                               / max(np.nanmean(dl), 1e-9))
    except Exception:
        pass

    try:
        carbs = json.load(open(ds.carbs_path))
        g = pd.to_numeric(pd.DataFrame(carbs).get("grams"), errors="coerce")
        if g is not None and len(g):
            out["carb_max"] = float(g.max())
            out["carb_n"] = int(len(g))
    except Exception:
        pass
    return out


def main() -> int:
    co = S.cohort()
    rows = []
    for i, a in enumerate(co["alias"]):
        r = {"alias": a}
        for fn in (glucose_checks, insulin_checks):
            try:
                r.update(fn(a))
            except Exception as e:
                r[fn.__name__ + "_err"] = type(e).__name__
        rows.append(r)
        if i % 20 == 0:
            print(f"    ...{i}/{len(co)}", flush=True)
    t = pd.DataFrame(rows)
    t.to_csv(S.OUT / "integrity.csv", index=False)
    print(f"\n  integrity.csv — {len(t)} people, {t.shape[1] - 1} checks\n")

    num = [c for c in t.columns if c != "alias" and pd.api.types.is_numeric_dtype(t[c])]
    print(t[num].describe(percentiles=[.01, .1, .5, .9, .99]).T
           .loc[:, ["count", "min", "1%", "50%", "90%", "99%", "max"]]
           .round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
