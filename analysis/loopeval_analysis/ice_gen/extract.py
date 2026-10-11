"""ICE at the sensor's own cadence, with a person-level ISF from total daily insulin.

One row per interval between consecutive raw CGM readings (t0, t1]:

    ice = v + ia,   v  = (bg1 - bg0) / dt                        mg/dL per hour
                    ia = ISF_tdd * (insulin absorbed in (t0, t1]) / dt

Conventions (from eda's ICE study, `dist_views/ice/ice_raw.py`, re-implemented here):
  - raw CGM, no smoothing; intervals off the native cadence carry no ICE (`on_cadence`)
  - ABSOLUTE insulin: every delivered unit (basal + boluses), not net of a schedule.
    absorbed(t) = delivered so far - insulin on board(t), on a 1-minute grid, with the
    donor's insulin model. Basal = each record's delivered volume spread over its span;
    where no basal record covers a minute, the pump's own (un-overridden) schedule runs.
  - ISF does NOT come from the person's settings or overrides. ISF_tdd = K / TDD^B, the
    population fit of scheduled ISF on TDD (eda lesson 49: ISF ~ 688 / TDD^0.74, 157 donors).
    TDD = mean daily delivered insulin over clean local days (>=240 of 288 five-minute
    bins with CGM, no disruption), one value per donor.
  - delivery is zero while no pod is paired (Omnipod "No pod paired" runs, `site_events`).
    Every other basal-record gap of >= 60 min is checked against Loop's recorded IOB
    (`gapcheck`): schedule fill kept where it ran, zeroed where nothing was delivered
    (`gap_none`), `unrecorded` where it can't tell. A set removed without a suspend is
    invisible to every record and stays inside ICE.
  - `dose_doubt`: UTC days on which a second dosing app uploads doses beside Loop's (copies the
    ETL's dedup misses, and doses that match nothing), plus 6 h after for the insulin tail. The
    recorded insulin there is wrong by tens of percent in an unknown direction; those days are
    also left out of TDD.
  - flags, never drops: jump, clamp, disrupted, no_insulin, unrecorded, gap_none, dose_doubt, change
    (1 h before to 3 h after a pod/site change), compression, fast, alternating, post_gap.
    `EXCLUDE` is all but post_gap. (Occlusion alarms are not pulled yet.)

Context columns for the generative model: insulin on board (absolute), insulin activity,
boluses (auto / manual) and basal delivered in the interval, carbs entered in the interval
(at the moment they became visible to Loop), local clock.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import gapcheck as G
from ..iob import (percent_effect_remaining, RAPID_ACTING_ADULT, RAPID_ACTING_CHILD,
                   FIASP, LYUMJEV, AFREZZA)

np.seterr(all="ignore")

ISF_K, ISF_B = 688.0, 0.74
JUMP = 8.0                    # mg/dL/min
LOW, HIGH = 39.5, 400.5       # sensor floor / ceiling
MODELS = {"rapidActingAdult": RAPID_ACTING_ADULT, "rapidActingChild": RAPID_ACTING_CHILD,
          "fiasp": FIASP, "lyumjev": LYUMJEV, "afrezza": AFREZZA}
FLAGS = ["jump", "clamp", "disrupted", "no_insulin", "unrecorded", "gap_none", "dose_doubt", "change", "compression",
         "fast", "alternating", "post_gap"]
EXCLUDE = [f for f in FLAGS if f != "post_gap"]
MIN = pd.Timedelta(minutes=1)


def isf_from_tdd(tdd: float) -> float:
    return ISF_K / tdd ** ISF_B


def _ts(x):
    return pd.to_datetime(x, utc=True, format="ISO8601")


def _schedule(segs, t: pd.DatetimeIndex) -> np.ndarray:
    st = pd.DatetimeIndex(_ts([s["startDate"] for s in segs])).asi8
    vals = np.array([s["value"] for s in segs], float)
    i = np.searchsorted(st, t.asi8, side="right") - 1
    return np.where(i >= 0, vals[np.clip(i, 0, None)], vals[0])


def _windows(t0_ns, t1_ns, wins):
    out = np.zeros(len(t0_ns), bool)
    for s, e in wins:
        out[np.searchsorted(t1_ns, s, side="right"):np.searchsorted(t0_ns, e, side="left")] = True
    return out


def insulin_grid(doses: list, therapy: dict, grid: pd.DatetimeIndex):
    """Units delivered per minute on `grid`: (basal, auto bolus, manual bolus), plus a mask of
    minutes covered by a basal record."""
    n = len(grid); g0 = grid[0]
    basal, auto, man = np.zeros(n), np.zeros(n), np.zeros(n)
    covered = np.zeros(n, bool)
    for d in doses:
        s, e = _ts(d["startDate"]), _ts(d.get("endDate", d["startDate"]))
        v = float(d.get("volume") or 0)
        i0 = int(np.floor((s - g0) / MIN))
        if d["deliveryType"] == "bolus":
            if 0 <= i0 < n and v > 0:
                (auto if d.get("automatic") else man)[i0] += v
            continue
        i1 = int(np.ceil((e - g0) / MIN))
        lo, hi = max(i0, 0), min(i1, n)
        if hi <= lo:
            continue
        covered[lo:hi] = True
        if v > 0:
            basal[lo:hi] += v / max(i1 - i0, 1)
    sched = _schedule(therapy.get("rawBasal") or therapy["basal"], grid) / 60.0
    basal = np.where(covered, basal, sched)
    return basal, auto, man, covered


def local_clock(t: pd.Series, tz_daily: pd.DataFrame | None):
    """Local hour (float) and day of week, using the donor's modal timezone for each UTC day."""
    if tz_daily is None or tz_daily.empty:
        loc = t.dt.tz_convert("UTC")
        return (loc.dt.hour + loc.dt.minute / 60).to_numpy(), loc.dt.dayofweek.to_numpy()
    day = (t.astype("int64") // 86_400_000_000_000).to_numpy()
    tzd = tz_daily.set_index("day").tz
    tzd = tzd.reindex(range(day.min(), day.max() + 1)).ffill().bfill()
    hour = np.empty(len(t)); dow = np.empty(len(t), int)
    for tz, idx in pd.Series(np.arange(len(t))).groupby(tzd.loc[day].to_numpy()):
        loc = t.iloc[idx.to_numpy()].dt.tz_convert(tz)
        hour[idx] = loc.dt.hour + loc.dt.minute / 60
        dow[idx] = loc.dt.dayofweek
    return hour, dow


def extract(data_dir: str | Path, tz_daily: pd.DataFrame | None = None,
            site_events: pd.DataFrame | None = None, loop_iob: pd.DataFrame | None = None,
            dose_doubt_days=None):
    """Interval table + person summary for one exported donor directory."""
    d = Path(data_dir)
    therapy = json.load(open(d / "therapy.json"))
    doses = json.load(open(d / "doses.json"))
    carbs = json.load(open(d / "carbs.json"))
    glu = json.load(open(d / "glucose.json"))
    model = MODELS.get(therapy.get("insulinType", "rapidActingAdult"), RAPID_ACTING_ADULT)

    g = pd.Series([float(x["quantity"]) for x in glu], index=_ts([x["startDate"] for x in glu])).sort_index()
    g = g[~g.index.duplicated(keep="first")].dropna()
    t, bg = g.index, g.to_numpy()
    dt = np.diff(t.asi8) / 6e10
    cad = max(float(np.round(np.median(dt) * 2) / 2), 0.5)
    ok = (dt >= 0.8 * cad) & (dt <= 1.2 * cad)

    # ---- insulin on a 1-minute grid (with a warm-up so IOB is complete at the first reading)
    grid = pd.date_range(t[0].floor("min") - pd.Timedelta(minutes=int(model.effect_duration_min) + 10),
                         t[-1].ceil("min"), freq="1min")
    basal, auto, man, covered = insulin_grid(doses, therapy, grid)
    gm = grid.asi8
    k = percent_effect_remaining(np.arange(int(model.effect_duration_min) + 2, dtype=float), model)

    # ---- where delivery is known to be zero: no pod paired (deactivate -> pair)
    ev = site_events if site_events is not None else pd.DataFrame(columns=["kind", "t_start", "t_end"])
    nopod = ev[ev.kind == "no_pod"]
    for s, e in zip(_ts(nopod.t_start).astype("int64"), _ts(nopod.t_end).astype("int64")):
        lo, hi = np.searchsorted(gm, s), np.searchsorted(gm, e, side="right")
        basal[lo:hi] = 0.0; covered[lo:hi] = True
    # ---- the remaining long gaps: did the schedule run? (Loop's own IOB decides; see gapcheck)
    sched = _schedule(therapy.get("rawBasal") or therapy["basal"], grid) / 60.0
    gaps = []
    if loop_iob is not None and len(loop_iob):
        li = loop_iob.sort_values("t")
        gaps = G.classify(gm, basal + auto + man, sched, covered, k,
                          li.t.astype("int64").to_numpy(), li.iob.to_numpy())
    else:
        gaps = [(a, b, G.UNKNOWN, np.nan, np.nan) for a, b in G.gap_runs(covered)]
    # a donor whose checkable gaps overwhelmingly ran (>= 90% of >= 20) gets the schedule in
    # the gaps too small to check, rather than having them excluded
    n_ran = sum(g[2] == G.RAN for g in gaps); n_none = sum(g[2] == G.NONE for g in gaps)
    if n_ran + n_none >= 20 and n_ran >= 0.9 * (n_ran + n_none):
        gaps = [(a, b, G.RAN_BY_DONOR if s == G.UNKNOWN else s, *r) for a, b, s, *r in gaps]
    for a, b, status, *_ in gaps:
        if status == G.NONE:
            basal[a:b] = 0.0
    u = basal + auto + man
    iob = np.convolve(u, k)[: len(u)]
    absorbed = np.cumsum(u) - iob
    A =np.interp(t.asi8, gm, absorbed)
    cum = lambda x: np.interp(t.asi8, gm, np.cumsum(x))

    df = pd.DataFrame({"t0": t[:-1], "t1": t[1:], "dt": dt, "bg0": bg[:-1], "bg1": bg[1:],
                       "absorbed": np.diff(A), "on_cadence": ok})
    df["iob"] = np.interp(t.asi8, gm, iob)[1:]
    for name, arr in (("basal_u", basal), ("bolus_auto_u", auto), ("bolus_manual_u", man)):
        df[name] = np.diff(cum(arr))

    # carbs, at the moment Loop could see them
    cg = np.zeros(len(grid))
    for c in carbs:
        i = int(np.floor((_ts(c.get("dosingVisibleDate") or c["startDate"]) - grid[0]) / MIN))
        if 0 <= i < len(grid):
            cg[i] += float(c["grams"])
    df["carbs_g"] = np.diff(cum(cg))

    t0n, t1n = df.t0.astype("int64").to_numpy(), df.t1.astype("int64").to_numpy()
    # ---- flags
    df["jump"] = ok & (np.abs(df.bg1 - df.bg0) / df.dt > JUMP)
    df["clamp"] = (df.bg0 <= LOW) | (df.bg1 <= LOW) | (df.bg0 >= HIGH) | (df.bg1 >= HIGH)
    dis = []
    if (d / "disruptions.csv").exists():
        r = pd.read_csv(d / "disruptions.csv")
        dis = list(zip(_ts(r.start).astype("int64"), _ts(r.end).astype("int64")))
    df["disrupted"] = _windows(t0n, t1n, dis)
    # long basal-record gaps: filled with the schedule when Loop's IOB confirms it ran; zeroed
    # (`gap_none`) when it shows nothing was delivered; `unrecorded` when it can't tell
    win = lambda st: [(gm[a], gm[min(b, len(gm) - 1)]) for a, b, s, *_ in gaps if s == st]
    df["unrecorded"] = _windows(t0n, t1n, win(G.UNKNOWN))
    df["gap_none"] = _windows(t0n, t1n, win(G.NONE))
    dd = [pd.Timestamp(x, tz="UTC") for x in (dose_doubt_days if dose_doubt_days is not None else [])]
    df["dose_doubt"] = _windows(t0n, t1n, [(x.value, (x + pd.Timedelta(hours=30)).value) for x in dd])
    # site / pod change: 1 h before to 3 h after (the swap itself, then the catch-up burst)
    ch = ev[ev.kind.isin(["no_pod", "prime:cannula", "prime:tubing", "reservoirChange"])]
    cw = [(s - 3600 * 10**9, e + 3 * 3600 * 10**9)
          for s, e in zip(_ts(ch.t_start).astype("int64"), _ts(ch.t_end).astype("int64"))]
    df["change"] = _windows(t0n, t1n, cw)
    # fast: ~30-min span moving faster than 4 mg/dL/min
    ti = t.asi8
    j = np.clip(np.searchsorted(ti, ti + 30 * 6e10), 0, len(ti) - 1)
    span = (ti[j] - ti) / 6e10
    rate = np.abs(bg[j] - bg) / np.where(span > 0, span, np.nan)
    gap_cum = np.r_[0, np.cumsum(~ok)]
    fastpt = (span >= 25) & (span <= 36) & ((gap_cum[j] - gap_cum[np.arange(len(ti))]) == 0) & (rate > 4)
    mark = np.zeros(len(ti) + 1, int)
    for i in np.flatnonzero(fastpt):
        mark[i] += 1; mark[j[i]] -= 1
    cover = np.cumsum(mark)[: len(ti)] > 0
    df["fast"] = cover[:-1]
    # post_gap: within 2 h after a CGM gap of >= 60 min
    gap_end = t1n[df.dt.to_numpy() >= 60]
    kk = np.searchsorted(gap_end, t0n, side="right") - 1
    since = np.where(kk >= 0, (t0n - gap_end[np.clip(kk, 0, None)]) / 6e10, np.inf) if len(gap_end) else np.full(len(t0n), np.inf)
    df["post_gap"] = (since >= 0) & (since < 120)
    # compression-shaped lows
    n15, n20 = max(int(round(15 / cad)), 1), max(int(round(20 / cad)), 1)
    comp = np.zeros(len(bg), bool)
    for i in np.flatnonzero(bg < 70):
        if i < n15 or i >= len(bg) - n15 or bg[i] > bg[i - 1] or bg[i] > bg[i + 1]:
            continue
        sb, sa = (ti[i] - ti[i - n15]) / 6e10, (ti[i + n15] - ti[i]) / 6e10
        if sb > 1.3 * 15 or sa > 1.3 * 15:
            continue
        if (bg[i - n15] - bg[i]) / sb >= 2 and (bg[i + n15] - bg[i]) / sa >= 2:
            comp[max(i - n20, 0): i + n20 + 1] = True
    df["compression"] = comp[:-1] | comp[1:]
    # every increment short of a gap: two interleaved CGMs report every ~1.6 / 3.4 min, which the
    # cadence mask `ok` drops, so masking by it hid them entirely (i171: 26% of its record, 0% flagged)
    inc = pd.Series(np.where(dt <= 1.2 * cad, df.bg1 - df.bg0, np.nan))
    w = max(int(round(120 / cad)), 8)
    df["alternating"] = (inc.rolling(w, min_periods=w // 2).corr(inc.shift(1)) < -0.6).to_numpy()

    # ---- local clock, no_insulin days, TDD
    df["hour"], df["dow"] = local_clock(df.t1, tz_daily)
    # local day index: UTC instant shifted by the local-minus-UTC hour offset
    shift = ((df.hour.to_numpy() - (df.t1.dt.hour + df.t1.dt.minute / 60).to_numpy() + 36) % 24) - 12
    lday = ((df.t1.astype("int64") + (shift * 3.6e12).astype("int64")) // 86_400_000_000_000).to_numpy()
    df["local_day"] = lday
    day_ins = pd.Series(df.basal_u + df.bolus_auto_u + df.bolus_manual_u).groupby(lday).sum()
    df["no_insulin"] = pd.Series(lday).map(day_ins <= 0).to_numpy()

    # a clean day: >= 240 five-minute bins with CGM and no disruption, and no unrecorded or doubtful insulin
    bad_ins = df.unrecorded | df.dose_doubt
    ok_bins = pd.Series(df.t1.dt.floor("5min").to_numpy())[~(df.disrupted | bad_ins).to_numpy()]
    n5 = ok_bins.groupby(lday[~(df.disrupted | bad_ins).to_numpy()]).nunique()
    clean = n5[(n5 >= 240) & ~bad_ins.groupby(df.local_day).any().reindex(n5.index).to_numpy()].index
    tdd = float(day_ins.loc[clean].mean()) if len(clean) >= 7 else np.nan
    isf = isf_from_tdd(tdd) if np.isfinite(tdd) else np.nan

    df["v"] = (df.bg1 - df.bg0) / df.dt * 60.0
    df["ia"] = isf * df.absorbed / df.dt * 60.0
    df["ice"] = np.where(df.on_cadence, df.v + df.ia, np.nan)
    df["ins_activity_uhr"] = df.absorbed / df.dt * 60.0
    df["clean"] = df.on_cadence & ~df[EXCLUDE].any(axis=1)
    gst = pd.Series([g[2] for g in gaps], dtype=object).value_counts().to_dict()
    person = dict(gaps_ran=gst.get(G.RAN, 0), gaps_ran_by_donor=gst.get(G.RAN_BY_DONOR, 0), gaps_none=gst.get(G.NONE, 0), gaps_unknown=gst.get(G.UNKNOWN, 0), tdd=tdd, isf_tdd=isf, clean_days=int(len(clean)), cadence_min=cad,
                  insulin_type=therapy.get("insulinType", "rapidActingAdult"),
                  n_intervals=int(len(df)), clean_frac=float(df.clean.mean()))
    return df, person
