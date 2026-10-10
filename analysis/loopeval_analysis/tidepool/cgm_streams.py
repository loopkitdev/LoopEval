"""One CGM per instant: split an upload's glucose into physical sensors and keep the one Loop dosed on.

Tidepool can hold several glucose streams for one person: mirrors of ONE sensor (Loop's own upload, the
Dexcom app, HealthKit copies — same values, seconds apart) and, for some people, a SECOND independent sensor
worn at the same time (e.g. a twiist/Libre stream next to a Dexcom one). Deduplicating the union by timestamp
interleaves two sensors that read tens of mg/dL apart into a sawtooth: the increment's lag-1 goes to ~-1,
momentum and retrospective correction read noise Loop never saw, and ICE inherits it (eda lesson 21; in the
2026-10 ICE pilot one donor carried it for 26% of its record, two sensors ~40 mg/dL apart).

Method
  1. identity per reading: its per-sensor label (deviceId / transmitterId) when present; a label-less reading joins the labeled reading it
     mirrors (within MIRROR_S and MIRROR_MGDL); otherwise it is an 'unlabeled:<origin>' identity.
  2. identities whose overlapping readings mirror each other are one physical sensor (union-find).
  3. an hour with two sensors each reporting >= MIN_PER_HOUR readings over >= OVERLAP_MIN shared minutes is a
     CONFLICT hour. There the sensor
     Loop anchored on wins: dosingDecision.bgForecast[0] equals the latest reading of the sensor Loop read
     (proven exact for single-stream donors, stale_cgm lesson). No anchor evidence that hour -> the
     previous hour's choice, else the sensor with more readings.
  4. backstop: an hour whose kept readings still alternate (sub-4-min spacing and lag-1 of the increment
     < SAW_CORR over >= 9 increments) is reported as 'interleaved_unresolved' — two sensors under one label.
Sensor names in the report are a device TYPE or uploading app plus an index (the caller's `kind`), never the
label itself: labels carry transmitter / device serials.

quality() adds the other checks, on the kept stream:
  clipped           >= 30 min at a sensor limit (<= 40 or >= 400; 401 = the sensor's HIGH) — real, censored
  flat_run          >= FLAT_MIN of identical readings AWAY from the limits — stuck sensor or artificial data
                    (pilot: 3 such runs >= 60 min in 207 donors x 4 months; 30-45 min is common overnight)
  smooth_day        a day whose increment lag-1 exceeds SMOOTH_LAG1 — a heavily smoothed stream (sensor/app),
                    informational: a person's sensor property, not an exclusion
"""
from __future__ import annotations

import bisect
from collections import Counter, defaultdict

import numpy as np

MIRROR_S = 90          # a mirror reports the same sample within 90 s ...
MIRROR_MGDL = 2.0      # ... and within 2 mg/dL (mmol rounding)
SAME_SENSOR_SHARE = 0.8
MIN_PAIRS = 20
MIN_PER_HOUR = 3
OVERLAP_MIN = 10
ANCHOR_TOL = 2.0
ANCHOR_LOOKBACK_MS = 10 * 60_000
SAW_CORR = -0.6
HOUR = 3_600_000
FLAT_MIN = 60
CLIP_MIN = 30
SMOOTH_LAG1 = 0.9


def select(readings, anchors):
    """readings: list of (t_ms, mgdl, label or None, kind); label = the most specific sensor attribute the row
    carries (None if only the app is known), kind = a safe type name (device type or app). anchors: (t_ms, mgdl) =
    Loop's bgForecast[0] per decision. Returns (kept readings [(t_ms, mgdl)] sorted, report rows, summary)."""
    r = sorted(readings, key=lambda x: x[0])
    if not r:
        return [], [], dict(sensors=0, conflict_hours=0, dropped=0, unresolved_hours=0)
    t = np.array([x[0] for x in r], np.int64); v = np.array([x[1] for x in r], float)
    lab = [x[2] for x in r]; org = [x[3] for x in r]
    kind_of = {}
    for l, k in zip(lab, org):
        if l is not None:
            kind_of.setdefault(l, k)
    ident = list(lab)
    labeled = np.array([l is not None for l in lab])
    lt, lv = t[labeled], v[labeled]; lid = [l for l in lab if l is not None]
    # 1. label-less readings inherit a mirrored labeled reading's identity
    for i in np.flatnonzero(~labeled):
        j0 = bisect.bisect_left(lt, t[i] - MIRROR_S * 1000); j1 = bisect.bisect_right(lt, t[i] + MIRROR_S * 1000)
        best = None
        for j in range(j0, j1):
            if abs(lv[j] - v[i]) <= MIRROR_MGDL and (best is None or abs(lt[j] - t[i]) < abs(lt[best] - t[i])):
                best = j
        ident[i] = lid[best] if best is not None else f"unlabeled:{org[i] or 'none'}"
    # 2. identities that mirror each other are one sensor
    ids = sorted(set(ident)); parent = {k: k for k in ids}
    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]; k = parent[k]
        return k
    by = defaultdict(list)
    for i, k in enumerate(ident):
        by[k].append(i)
    arr = {k: (t[ix], v[ix]) for k, ix in ((k, np.array(ix)) for k, ix in by.items())}
    for a_i, a in enumerate(ids):
        for b in ids[a_i + 1:]:
            ta, va = arr[a]; tb, vb = arr[b]
            if ta[-1] < tb[0] or tb[-1] < ta[0]:
                continue
            j = np.clip(np.searchsorted(tb, ta), 1, len(tb) - 1)
            jj = np.where(np.abs(tb[j - 1] - ta) < np.abs(tb[j] - ta), j - 1, j)
            close = np.abs(tb[jj] - ta) <= MIRROR_S * 1000
            if close.sum() >= MIN_PAIRS and (np.abs(vb[jj] - va)[close] <= MIRROR_MGDL).mean() >= SAME_SENSOR_SHARE:
                parent[find(b)] = find(a)
    sensor = [find(k) for k in ident]
    names, fam_n = {}, Counter()
    for s in sorted(set(sensor), key=lambda s: t[sensor.index(s)]):
        f = s.split(":", 1)[1] if s.startswith("unlabeled:") else kind_of.get(s, "sensor")
        fam_n[f] += 1; names[s] = f"{f}#{fam_n[f]}" + (" (unlabeled)" if s.startswith("unlabeled:") else "")
    # 3. conflict hours -> the sensor Loop anchored on
    hour = t // HOUR
    per_hour = defaultdict(Counter)
    for h, s in zip(hour, sensor):
        per_hour[h][s] += 1
    sens_idx = defaultdict(list)
    for i, s in enumerate(sensor):
        sens_idx[s].append(i)
    st = {s: t[np.array(ix)] for s, ix in sens_idx.items()}; sv = {s: v[np.array(ix)] for s, ix in sens_idx.items()}
    votes = defaultdict(Counter)
    for at, av in anchors:
        for s in st:
            k = bisect.bisect_right(st[s], at) - 1
            if k >= 0 and at - st[s][k] <= ANCHOR_LOOKBACK_MS and abs(sv[s][k] - av) <= ANCHOR_TOL:
                votes[at // HOUR][s] += 1
    keep = np.ones(len(r), bool); report = []; prev = None; conflict = 0
    sens_arr = np.array(sensor, dtype=object)
    for h in sorted(per_hour):
        present = [s for s, n in per_hour[h].items() if n >= MIN_PER_HOUR]
        if len(present) >= 2:
            # two sensors only conflict if they report over the SAME minutes: a label handing over to the
            # next (sensor change, re-labelled session) puts both in one hour without any overlap
            span = {s_: (t[(hour == h) & (sens_arr == s_)].min(), t[(hour == h) & (sens_arr == s_)].max()) for s_ in present}
            over = lambda x, y: min(span[x][1], span[y][1]) - max(span[x][0], span[y][0]) >= OVERLAP_MIN * 60_000
            present = [s_ for s_ in present if any(over(s_, o) for o in present if o != s_)] or present[:1]
        if len(present) < 2:
            if len(present) == 1:
                prev = present[0]
            continue
        conflict += 1
        vh = votes.get(h, Counter())
        top = [s for s in present if vh[s] == max(vh[s] for s in present)] if vh else []
        if vh and len(top) == 1 and vh[top[0]] > 0:
            choice, why = top[0], "loop_anchor"
        elif prev in present:
            choice, why = prev, "carried"
        else:
            choice, why = max(present, key=lambda s: per_hour[h][s]), "most_readings"
        prev = choice
        keep &= ~((hour == h) & (np.array(sensor) != choice))
        report.append(dict(hour_ms=int(h * HOUR), kind="two_sensors", sensors=";".join(names[s] for s in present),
                           kept=names[choice], reason=why,
                           anchors=";".join(f"{names[s]}={vh[s]}" for s in present),
                           readings=";".join(f"{names[s]}={per_hour[h][s]}" for s in present)))
    kt, kv = t[keep], v[keep]
    # 4. backstop: two sensors under one label still alternate
    unresolved = 0
    inc = np.diff(kv); gap = np.diff(kt); ih = kt[1:] // HOUR
    for h in np.unique(ih):
        x = inc[ih == h]; g = gap[ih == h]
        # interleaving shows as sub-cadence spacing too; a single 5-min sensor's noise alone can dip below
        # SAW_CORR over 11 increments a few % of hours
        if len(x) >= 9 and np.median(g) < 4 * 60_000 and np.std(x[:-1]) > 0 and np.std(x[1:]) > 0 \
                and np.corrcoef(x[:-1], x[1:])[0, 1] < SAW_CORR and np.median(np.abs(x)) >= 5:
            unresolved += 1
            report.append(dict(hour_ms=int(h * HOUR), kind="interleaved_unresolved", sensors="", kept="",
                               reason="alternating increments", anchors="", readings=str(len(x) + 1)))
    report.sort(key=lambda d: d["hour_ms"])
    summary = dict(sensors=len(names), conflict_hours=conflict, dropped=int((~keep).sum()), unresolved_hours=unresolved)
    return list(zip(kt.tolist(), kv.tolist())), report, summary


def quality(kept, utc_offset_ms=0):
    """Clipped / flat / smooth checks on the kept stream [(t_ms, mgdl)]. Returns report rows."""
    if len(kept) < 3:
        return []
    t = np.array([x[0] for x in kept], np.int64); v = np.array([x[1] for x in kept], float)
    rows = []
    same = np.r_[False, (np.abs(np.diff(v)) < 0.05) & (np.diff(t) <= 10 * 60_000)]
    i = 1
    while i < len(v):
        if not same[i]:
            i += 1; continue
        j = i
        while j + 1 < len(v) and same[j + 1]:
            j += 1
        a, b = i - 1, j
        dur = (t[b] - t[a]) / 60_000
        at_limit = v[a] <= 40.5 or v[a] >= 399.5
        if (at_limit and dur >= CLIP_MIN) or (not at_limit and dur >= FLAT_MIN):
            rows.append(dict(start_ms=int(t[a]), end_ms=int(t[b]), kind="clipped" if at_limit else "flat_run",
                             detail=f"{v[a]:.0f} mg/dL x {b - a + 1} readings"))
        i = j + 1
    day = (t + utc_offset_ms) // 86_400_000
    for d in np.unique(day):
        m = day == d; x = np.diff(v[m]); g = np.diff(t[m])
        x = x[(g >= 4 * 60_000) & (g <= 6 * 60_000)]
        if len(x) >= 200 and np.std(x[:-1]) > 0 and np.std(x[1:]) > 0:
            lag1 = float(np.corrcoef(x[:-1], x[1:])[0, 1])
            if lag1 > SMOOTH_LAG1:
                rows.append(dict(start_ms=int(t[m][0]), end_ms=int(t[m][-1]), kind="smooth_day", detail=f"increment lag-1 {lag1:.2f}"))
    return rows
