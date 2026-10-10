#!/usr/bin/env python3
"""ICE at the sensor's own cadence, with every interval flagged rather than dropped.

ICE over one interval between consecutive raw CGM readings (t0, t1]:
    ice = (bg1 - bg0) / dt  +  ISF_est * (insulin absorbed in (t0, t1]) / dt
in mg/dL per hour. Insulin absorbed comes from a 1-minute delivery grid
(effective basal rate + boluses) and the person's insulin activity curve:
absorbed(t) = delivered so far - insulin on board(t). No interpolation of
glucose: a reading pair at the native cadence is the unit, so sensor noise is
neither hidden nor smeared (lesson 1). ISF_est from ice/isf_estimate.csv.

Flags (an interval can carry several):
  jump        |step| faster than 8 mg/dL/min (the study's despike limit)
  clamp       either reading at the sensor's floor (<=39.5) or ceiling (>=400.5)
  disrupted   overlaps a pump error, suspend, loop-offline or disruption window
  no_insulin  falls in a local day with CGM but no insulin delivered at all
  post_gap    within 2 h after a CGM gap of 60 min or more (warm-up/restart)
  compression inside +-20 min of a V-shaped low: minimum < 70 reached at
              >= 2 mg/dL/min over the 15 min before and left at >= 2 mg/dL/min
              over the 15 min after
  unrecorded  inside a stretch of 60 min or more with no basal record at all
              (basal_coverage.py) — the grid assumes the schedule there, so
              insulin is unknown, not scheduled
  pre_early   within 12 h before a site change (twiist cannula prime) or pod
              change (Omnipod, "No pod paired" run) made when the previous
              site/pod had lasted under 0.6x the person's median life — a
              failing site or a faulted pod (ice_site.py, ice_pod.py)
  change      from 1 h before to 3 h after every site or pod change: the swap
              itself (no delivery, then a catch-up burst) distorts ICE
  fast        inside a ~30-min span whose glucose moves faster than 4 mg/dL/min
              (beyond what CGM trend arrows encode; ice_rate_check.py)
  occlusion   from 1 h before to 3 h after a twiist occlusion-alarm episode
              (alarms within 30 min merged; ice_occlusion.py)
  alternating within a 2-h stretch whose increments alternate in sign
              (lag-1 autocorrelation < -0.6) — two interleaved sensors
Intervals whose spacing is off the native cadence (gaps) carry no ICE and are
counted separately.

Output: ice/raw/<alias>.pkl (one row per interval), ice/raw_screen.csv
"""
from __future__ import annotations
import csv
import json
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
np.seterr(all="ignore")
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import style as S  # noqa
from loopeval_analysis import dists as D  # noqa
from loopeval_analysis.iob import percent_effect_remaining  # noqa

RAW = S.OUT / "ice" / "raw"
JUMP = 8.0
LOW, HIGH = 39.5, 400.5
_DS = None


def ds_for(alias):
    global _DS
    if _DS is None:
        _DS = S.datasets()
    return _DS[alias]


def insulin_absorbed(ds, t0, t1):
    """Cumulative units absorbed on a 1-minute UTC grid."""
    doses = D._load_doses(ds.doses_path)
    therapy = json.load(open(ds.therapy_path))
    grid = pd.date_range(t0.floor("min") - pd.Timedelta(minutes=420), t1.ceil("min"), freq="1min", tz="UTC")
    rate = D._effective_basal_rate(doses, therapy, grid).to_numpy()
    bol = doses[doses["delivery_type"] != "basal"]["volume"]
    u = rate / 60.0 + D._bin_events(bol, grid)
    n = int(ds.insulin_model.effect_duration_min) + 2
    iob_k = percent_effect_remaining(np.arange(n, dtype=float), model=ds.insulin_model)
    iob = np.convolve(u, iob_k)[:len(u)]
    absorbed = np.cumsum(u) - iob
    return grid, absorbed, u


def _in_windows(t_ns, anchors_ns, lo_h, hi_h):
    out = np.zeros(len(t_ns), bool)
    for a in anchors_ns:
        out |= (t_ns >= a + lo_h * 3.6e12) & (t_ns < a + hi_h * 3.6e12)
    return out


def _event_anchors():
    """{alias: [ns]} for every site/pod change, early ones, and occlusion-alarm episodes."""
    early, occl, allc = {}, {}, {}
    per = {}
    try:
        from site_change import site_changes
        for a, g in site_changes().groupby("alias"):
            per.setdefault(a, []).extend(g.t.astype("int64").tolist())
    except FileNotFoundError:
        pass
    pp = S.OUT / "ice" / "pod_changes.pkl"
    if pp.exists():
        for a, g in pd.read_pickle(pp).groupby("alias"):
            per.setdefault(a, []).extend(g.t_end.astype("int64").tolist())
    for a, lst in per.items():
        ts = np.sort(np.asarray(lst, dtype=np.int64))
        age = np.r_[np.nan, np.diff(ts)] / 3.6e12
        life = np.nanmedian(age) if len(ts) > 2 else 72.0
        early[a] = list(ts[age < 0.6 * life])            # same definition as ice_site.EARLY_FRAC
        allc[a] = list(ts)
    p = S.OUT / "ice" / "alarms.pkl"
    if p.exists():
        al = pd.read_pickle(p)
        al = al[al.alarmType == "occlusion"].sort_values(["alias", "t"])
        for a, g in al.groupby("alias"):
            t = g.t.astype("int64").to_numpy()
            keep = np.r_[True, np.diff(t) > 30 * 6e10]
            occl[a] = list(t[keep])
    return early, occl, allc


EARLY, OCCL, CHANGES = _event_anchors()


def doses_b(ds):
    """Sorted (start, end) of every basal record, as int64 ns."""
    doses = D._load_doses(ds.doses_path)
    b = doses[doses.delivery_type == "basal"].sort_index()
    return list(zip(b.index.asi8, b.endDate.dt.tz_convert("UTC").astype("int64")))


def disruption_windows(ds):
    out = []
    p = ds.disruptions_path
    if not p or not Path(p).exists():
        return out
    for r in csv.DictReader(open(p)):
        try:
            out.append((pd.Timestamp(r["start"]).tz_convert("UTC").value,
                        pd.Timestamp(r["end"]).tz_convert("UTC").value))
        except Exception:
            pass
    return out


def build(alias, isf):
    ds = ds_for(alias)
    g = S.clip_window(alias, D._load_glucose(ds.glucose_path)).dropna()
    t = g.index
    bg = g.to_numpy()
    dt = np.diff(t.asi8) / 6e10                                  # minutes
    cad = max(float(np.round(np.median(dt) * 2) / 2), 0.5)
    ok = (dt >= 0.8 * cad) & (dt <= 1.2 * cad)
    grid, A, u = insulin_absorbed(ds, t[0], t[-1])
    gm = grid.asi8
    Ai = np.interp(t.asi8, gm, A)
    d = pd.DataFrame({"t0": t[:-1], "t1": t[1:], "dt": dt, "bg0": bg[:-1], "bg1": bg[1:],
                      "absorbed": np.diff(Ai)})
    d["v"] = (d.bg1 - d.bg0) / d.dt * 60.0
    d["ia"] = isf * d.absorbed / d.dt * 60.0
    d["ice"] = d.v + d.ia
    d["on_cadence"] = ok
    # ── flags ───────────────────────────────────────────────────────────
    d["jump"] = ok & (np.abs(d.bg1 - d.bg0) / d.dt > JUMP)
    d["clamp"] = (d.bg0 <= LOW) | (d.bg1 <= LOW) | (d.bg0 >= HIGH) | (d.bg1 >= HIGH)
    mid = ((d.t0.astype("int64") + d.t1.astype("int64")) // 2).to_numpy()
    dis = np.zeros(len(d), bool)
    for s, e in disruption_windows(ds):
        lo, hi = np.searchsorted(d.t1.astype("int64").to_numpy(), s), np.searchsorted(d.t0.astype("int64").to_numpy(), e)
        dis[lo:hi] = True
    d["disrupted"] = dis
    # local days with CGM but zero delivery
    off = pd.Timedelta(hours=ds.utc_offset_h)
    day_u = pd.Series(u, index=(grid + off).floor("D")).groupby(level=0).sum()
    zero_days = set(day_u[day_u <= 0].index)
    d["no_insulin"] = (d.t0 + off).dt.floor("D").isin(zero_days)
    # no basal record at all for >= 60 min: insulin unknown
    b = doses_b(ds)
    unrec = np.zeros(len(d), bool)
    t1i_all = d.t1.astype("int64").to_numpy(); t0i_all = d.t0.astype("int64").to_numpy()
    last = t[0].value
    for s_, e_ in b:
        if s_ - last >= 60 * 6e10:
            unrec[np.searchsorted(t1i_all, last, side="right"):np.searchsorted(t0i_all, s_, side="left")] = True
        last = max(last, e_)
    if t[-1].value - last >= 60 * 6e10:
        unrec[np.searchsorted(t1i_all, last, side="right"):] = True
    d["unrecorded"] = unrec
    # twiist-only event windows
    mid_ns = mid
    d["pre_early"] = _in_windows(mid_ns, EARLY.get(alias, []), -12, 0)
    d["occlusion"] = _in_windows(mid_ns, OCCL.get(alias, []), -1, 3)
    d["change"] = _in_windows(mid_ns, CHANGES.get(alias, []), -1, 3)
    # glucose faster than 4 mg/dL/min over ~30 min (span 25-36 min, no gap inside)
    ti = t.asi8
    j = np.searchsorted(ti, ti + 30 * 6e10)
    j = np.clip(j, 0, len(ti) - 1)
    span = (ti[j] - ti) / 6e10
    rate = np.abs(bg[j] - bg) / np.where(span > 0, span, np.nan)
    gap_cum = np.r_[0, np.cumsum(~ok)]
    nogap = (gap_cum[j] - gap_cum[np.arange(len(ti))]) == 0
    fastpt = (span >= 25) & (span <= 36) & nogap & (rate > 4)
    fast = np.zeros(len(ti) + 1, int)
    for i in np.flatnonzero(fastpt):
        fast[i] += 1; fast[j[i]] -= 1
    cover = np.cumsum(fast)[:len(ti)] > 0               # sample-level coverage
    d["fast"] = cover[:-1] & cover[1:] | cover[:-1]
    # after a long gap
    gap_end = d.t1[(d.dt >= 60)].astype("int64").to_numpy()
    t0i = d.t0.astype("int64").to_numpy()
    k = np.searchsorted(gap_end, t0i, side="right") - 1
    since = (np.where(k >= 0, (t0i - gap_end[np.clip(k, 0, None)]) / 6e10, np.inf)
             if len(gap_end) else np.full(len(t0i), np.inf))
    d["post_gap"] = (since >= 0) & (since < 120)
    # compression-shaped lows, on the raw series
    n15 = max(int(round(15 / cad)), 1)
    n20 = max(int(round(20 / cad)), 1)
    comp = np.zeros(len(bg), bool)
    for i in range(n15, len(bg) - n15):
        if bg[i] >= 70 or bg[i] > bg[i - 1] or bg[i] > bg[i + 1]:
            continue
        span_b = (t.asi8[i] - t.asi8[i - n15]) / 6e10
        span_a = (t.asi8[i + n15] - t.asi8[i]) / 6e10
        if span_b > 1.3 * 15 or span_a > 1.3 * 15:
            continue
        if (bg[i - n15] - bg[i]) / span_b >= 2 and (bg[i + n15] - bg[i]) / span_a >= 2:
            comp[max(i - n20, 0):i + n20 + 1] = True
    d["compression"] = comp[:-1] | comp[1:]
    # alternating increments (interleaved sensors)
    inc = pd.Series(np.where(ok, d.bg1 - d.bg0, np.nan))
    w = max(int(round(120 / cad)), 8)
    r1 = inc.rolling(w, min_periods=w // 2).corr(inc.shift(1))
    d["alternating"] = (r1 < -0.6).to_numpy()
    d["cadence"] = cad
    return d


FLAGS = ["jump", "clamp", "disrupted", "unrecorded", "no_insulin", "post_gap", "compression", "alternating",
         "pre_early", "occlusion", "change", "fast"]
# what a clean interval must be free of: every flag except post_gap, which
# marked ICE no different from clean (flag_effects.py)
EXCLUDE = [f for f in FLAGS if f != "post_gap"]


def person(args):
    alias, isf = args
    try:
        d = build(alias, isf)
    except Exception as e:                                      # report, never hide
        return {"alias": alias, "error": repr(e)}
    d.to_pickle(RAW / f"{alias}.pkl")
    on = d[d.on_cadence]
    hrs = on.dt.sum() / 60
    r = {"alias": alias, "cadence": d.cadence.iloc[0], "hours_on_cadence": hrs,
         "days_span": (d.t1.iloc[-1] - d.t0.iloc[0]).total_seconds() / 86400,
         "gap_hours": d.loc[~d.on_cadence, "dt"].sum() / 60, "n_gaps_60": int((d.dt >= 60).sum())}
    for f in FLAGS:
        r[f"{f}_pct"] = 100 * on.loc[on[f], "dt"].sum() / on.dt.sum()
    anyf = on[FLAGS].any(axis=1)
    r["any_flag_pct"] = 100 * on.loc[anyf, "dt"].sum() / on.dt.sum()
    r["clean_hours"] = on.loc[~anyf, "dt"].sum() / 60
    r["n_jump"] = int(on.jump.sum())
    return r


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    est = pd.read_csv(S.OUT / "ice" / "isf_estimate.csv").dropna(subset=["isf_est"])
    S.datasets()
    with Pool(8) as pool:
        rows = pool.map(person, list(zip(est.alias, est.isf_est)))
    r = pd.DataFrame(rows)
    r.to_csv(S.OUT / "ice" / "raw_screen.csv", index=False)
    if "error" in r:
        print("errors:", r.dropna(subset=["error"])[["alias", "error"]].to_string())
    pd.set_option("display.width", 220)
    cols = ["cadence", "hours_on_cadence", "gap_hours", "n_gaps_60"] + [f"{f}_pct" for f in FLAGS] + ["any_flag_pct", "clean_hours", "n_jump"]
    print(r[cols].describe(percentiles=[.1, .5, .9]).T[["min", "10%", "50%", "90%", "max"]].round(2).to_string())


def excluded_on_grid(alias, index):
    """Bool per 5-min panel bin: True where any raw interval inside the bin carries
    an EXCLUDE flag. Panel bin j covers (index[j-1], index[j]]. Lets the panel-based
    ISF fit honour the same screen as raw-cadence ICE."""
    f = RAW / f"{alias}.pkl"
    if not f.exists():                         # never screened (no ISF yet): first pass uses
        return np.zeros(len(index), bool)      # the unscreened fit; ice_raw then covers them
    d = pd.read_pickle(f)
    bad = d[d[EXCLUDE].any(axis=1)]
    out = np.zeros(len(index), bool)
    if len(bad) == 0:
        return out
    gi = index.asi8
    for col in ("t0", "t1"):
        pos = np.searchsorted(gi, bad[col].astype("int64").to_numpy(), side="left")
        pos = pos[(pos >= 0) & (pos < len(gi))]
        out[pos] = True
    return out
