"""ETL: Tidepool device_data (Databricks) → the 4 EvalCore JSON files for ONE donor.

Writes glucose.json / doses.json / carbs.json / therapy.json in the exact Codable
shapes that LoopEval's JSONFileDataSource reads, so the CF sim runs on Tidepool data
with no further changes (point `simulate --data-dir <out>`).

Tidepool quirks handled:
  • all numbers Mongo-wrapped: {"$numberDouble"/"$numberInt"/"$numberLong": "x"}
  • time = {"$date":{"$numberLong": <epoch ms>}}
  • BG stored in mmol/L  → ×18.0182 → mg/dL
  • bolus subType: 'automated' (Loop SMB) vs 'normal' (manual) → automatic flag
  • basal deliveryType: scheduled / automated(temp) / suspend, rate U/hr, duration ms
  • carbs are `food` records: nutrition.carbohydrate.net (g) + estimatedAbsorptionDuration (s)
  • pumpSettings daily schedules (start = ms-from-midnight) → expanded to absolute timeline

Usage:
    from loopeval_analysis.tidepool.etl import export_donor
    export_donor("d6954e6498", "2026-02-01", "2026-04-01", "runs/tidepool/DONOR_ID")
"""
import json, os
from datetime import datetime, timezone, timedelta
from loopeval_analysis.tidepool.conn import query

MMOL = 18.0182
TBL = "prod.default.device_data"

def _fin(x):
    """x if a finite number, else None (drops NULL→NaN from SQL casts)."""
    try:
        x = float(x)
        return x if x == x and x not in (float("inf"), float("-inf")) else None
    except Exception:
        return None

def _iso(ms):
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

def _num(j):
    """Parse a Mongo-wrapped number (dict, JSON string, or plain) → float, or None."""
    if j is None: return None
    if isinstance(j, (int, float)): return float(j)
    o = None
    if isinstance(j, dict):
        o = j
    elif isinstance(j, str) and j.startswith("{"):
        o = json.loads(j)
    if o is not None:
        for k in ("$numberDouble", "$numberInt", "$numberLong"):
            if k in o: return float(o[k])
        return None
    try: return float(j)
    except Exception: return None

def _ms_bounds(start, end):
    s = int(datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    e = int(datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    return s, e

# t_ms expression reused everywhere
_TMS = "CAST(get_json_object(time,'$.$date.$numberLong') AS BIGINT)"

def _dedup(cols, where, typ):
    """One row per Tidepool logical `id` (the table has exact-duplicate rows AND
    edit-versions sharing an id; without this everything is 2-3× over-counted).
    `cols` are inner expressions ("EXPR AS alias" or a plain column); the outer
    query selects only the aliases."""
    inner = ", ".join(cols)
    aliases = [c.split(" AS ")[-1].strip() if " AS " in c else c.strip() for c in cols]
    outer = ", ".join(aliases)
    return (f"SELECT {outer} FROM (SELECT {inner}, ROW_NUMBER() OVER (PARTITION BY id ORDER BY _id) rn "
            f"FROM {TBL} WHERE {where} AND type='{typ}') WHERE rn=1 ORDER BY t_ms")

# brand (insulinFormulation.simple.brand) → EvalCore ExponentialInsulinModelPreset
_BRAND_MAP = {
    "fiasp": "fiasp", "lyumjev": "lyumjev", "afrezza": "afrezza",
    "novolog": "rapidActingAdult", "novorapid": "rapidActingAdult",
    "humalog": "rapidActingAdult", "admelog": "rapidActingAdult",
    "apidra": "rapidActingAdult",
}

def _insulin_type_from_data(user, s_ms, e_ms, default="rapidActingAdult"):
    """Read the actual insulin brand from insulinFormulation on bolus/basal records
    (Tidepool: {"simple":{"actingType":"rapid","brand":"Fiasp"}}) → EvalCore preset.
    Returns (preset, brand_str). Falls back to `default` if absent/unknown."""
    q = (f"SELECT get_json_object(insulinFormulation,'$.simple.brand') AS brand, count(*) n "
         f"FROM {TBL} WHERE _userId='{user}' AND {_TMS} BETWEEN {s_ms} AND {e_ms} "
         f"AND insulinFormulation IS NOT NULL GROUP BY brand ORDER BY n DESC LIMIT 1")
    df = query(q)
    if df.empty or not df.iloc[0]["brand"]:
        return default, None
    brand = str(df.iloc[0]["brand"])
    return _BRAND_MAP.get(brand.strip().lower(), default), brand

def _overrides(user, s_ms, e_ms, e_win_ms):
    """Fetch temporary-override usage (deviceEvent/pumpSettingsOverride) and build
    absolute-time intervals with the effective scale factors + target. Each enactment
    is logged twice at one timestamp (a finite-duration row and a None/indefinite row);
    collapse per timestamp, using the finite duration when present. An override runs
    [start, start+duration] (finite) or [start, modifiedTime] (indefinite — Tidepool
    bumps modifiedTime when it's turned off; falls back to the next enactment only if
    modifiedTime is missing), always cut short by the next enactment (supersession).
    Returns sorted list of (start_ms, end_ms, {isf_sf, basal_sf, cr_sf, tgt_low,
    tgt_high, preset}). NOTE: indefinite-→-next-enactment over-extended (a 6.6h "low"
    became 29.7h); modifiedTime end validated against Loop's recorded IOB (2026-08-07)."""
    q = (f"SELECT {_TMS} AS t_ms, "
         f"CAST(get_json_object(duration,'$.$numberInt') AS BIGINT) AS dur_s, "
         f"overridePreset AS preset, "
         f"get_json_object(insulinSensitivityScaleFactor,'$.$numberDouble') AS isf_sf, "
         f"get_json_object(basalRateScaleFactor,'$.$numberDouble') AS basal_sf, "
         f"get_json_object(carbRatioScaleFactor,'$.$numberDouble') AS cr_sf, "
         f"get_json_object(bgTarget,'$.low.$numberDouble') AS tgt_low, "
         f"get_json_object(bgTarget,'$.high.$numberDouble') AS tgt_high, "
         f"CAST(get_json_object(modifiedTime,'$.$date.$numberLong') AS BIGINT) AS mod_ms, id "
         # NO id-dedup: Tidepool stores an override as EDIT-VERSIONS sharing one id — it's
         # first uploaded INDEFINITE (duration null), then EDITED with the resolved finite
         # duration when it ends. Keeping rn=1 (oldest _id) drops the finite end → the
         # override looks indefinite and over-extends. Fetch all versions; the per-timestamp
         # collapse below keeps the finite (resolved) one.
         f"FROM {TBL} WHERE _userId='{user}' AND type='deviceEvent' AND subType='pumpSettingsOverride'")
    df = query(q)
    if df.empty:
        return []
    # collapse per (timestamp, preset): prefer the finite-duration (resolved) edit-version;
    # among finite versions keep the LARGEST duration (the final resolved end, not an interim).
    grp = {}
    for r in df.itertuples():
        t = int(r.t_ms); key = (t // 1000, r.preset)
        dur = _fin(r.dur_s)
        _m = _fin(r.mod_ms); mod = int(_m) if _m is not None else None
        cur = grp.get(key)
        rec = dict(t=t, dur=dur, mod=mod, preset=r.preset,
                   isf=_fin(r.isf_sf) or 1.0, basal=_fin(r.basal_sf) or 1.0, cr=_fin(r.cr_sf) or 1.0,
                   tlo=_fin(r.tgt_low), thi=_fin(r.tgt_high))
        # Keep the LATEST edit-version (by modifiedTime). When an override is turned off
        # EARLY, Tidepool writes a new version at the same start with the ACTUAL (shorter)
        # duration and a later modifiedTime, while the original carries the longer SCHEDULED
        # duration. The newest-modified version holds the resolved duration/end. An earlier
        # "keep the LARGEST duration" rule over-extended every early-cancelled override
        # (e.g. a 2.6h "hypo" override ran to its 4h scheduled length → ISF held ×3.33 for
        # 84 extra min → forecast/counter crater → spurious severe lows).
        if cur is None:
            grp[key] = rec
        elif mod is not None and (cur["mod"] is None or mod > cur["mod"]):
            grp[key] = rec
        elif mod is None and cur["mod"] is None and dur is not None and \
                (cur["dur"] is None or dur > cur["dur"]):
            grp[key] = rec  # no modifiedTime on either → fall back to the longer finite duration
    evs = sorted(grp.values(), key=lambda x: x["t"])
    ivals = []
    for i, ev in enumerate(evs):
        nxt = evs[i + 1]["t"] if i + 1 < len(evs) else e_win_ms
        if ev["dur"] is not None:
            end = ev["t"] + int(ev["dur"] * 1000)               # finite: start + duration
        elif ev["mod"] is not None and ev["mod"] > ev["t"]:
            end = ev["mod"]                                       # indefinite: ended at modifiedTime
        else:
            end = nxt                                             # truly-open: until next enactment
        end = min(end, nxt, e_win_ms)
        st = max(ev["t"], s_ms)
        if end <= st:
            continue
        ivals.append((st, end, {"isf_sf": ev["isf"], "basal_sf": ev["basal"], "cr_sf": ev["cr"],
                                "tgt_low": ev["tlo"], "tgt_high": ev["thi"], "preset": ev["preset"]}))
    return ivals

def _overlay_overrides(base, overrides, apply_fn):
    """Split base segments (dicts w/ startDate/endDate ISO + values) at override
    boundaries; apply_fn(rec, ov_or_None) yields the effective value dict per piece."""
    if not overrides:
        return base
    def pms(iso):
        return int(datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc).timestamp() * 1000) \
            if "." in iso else int(datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() * 1000)
    segs = [(pms(r["startDate"]), pms(r["endDate"]), r) for r in base]
    bnds = sorted(set([s for s, _, _ in segs] + [e for _, e, _ in segs]
                      + [o[0] for o in overrides] + [o[1] for o in overrides]))
    out = []
    for i in range(len(bnds) - 1):
        s, e = bnds[i], bnds[i + 1]
        if e <= s:
            continue
        rec = next((r for (bs, be, r) in segs if bs <= s and be >= e), None)
        if rec is None:
            continue
        ov = next((o[2] for o in overrides if o[0] <= s and o[1] >= e), None)
        val = apply_fn(rec, ov)
        row = {"startDate": _iso(s), "endDate": _iso(e)}
        row.update(val)
        # merge with previous if identical value (keep the file compact)
        if out and out[-1]["endDate"] == row["startDate"] and \
           {k: v for k, v in out[-1].items() if k not in ("startDate", "endDate")} == val:
            out[-1]["endDate"] = row["endDate"]
        else:
            out.append(row)
    return out

def _suspends(user, s_ms, e_ms):
    """Manual / pump-suspend intervals (basal deliveryType='suspend'). A suspend is
    the pump PHYSICALLY stopping delivery — a manual suspend or pod fault — which is
    exogenous to the control loop: deployed Loop STOPS auto-dosing while suspended
    (no reason='loop' dosingDecisions across the suspend), and it can't deliver. So
    the sim must clamp delivery to 0 over the interval and the scorer must exclude it;
    replaying dose logic through a suspend just measures the sim dosing where Loop
    didn't. Emitted as the standard outage/disruption CSV (loopeval_analysis.outage
    schema) so `--outages-csv` clamps both arms and scoring drops the window.

    Duration is on the suspend record (ms). Look back 6h before window start so a
    suspend straddling the start is captured; merge overlapping/adjacent windows."""
    q = (f"SELECT {_TMS} AS t_ms, "
         f"COALESCE(CAST(get_json_object(duration,'$.$numberInt') AS BIGINT), "
         f"CAST(get_json_object(duration,'$.$numberLong') AS BIGINT)) AS dur_ms "
         f"FROM {TBL} WHERE _userId='{user}' AND type='basal' AND deliveryType='suspend' "
         f"AND {_TMS} BETWEEN {int(s_ms - 6 * 3600 * 1000)} AND {int(e_ms)}")
    df = query(q)
    if df.empty:
        return []
    iv = []
    for r in df.itertuples():
        dur = _fin(r.dur_ms)
        if not dur or dur <= 0:
            continue
        st = int(r.t_ms)
        iv.append((st, st + int(dur)))
    iv.sort()
    merged = []
    for st, en in iv:
        if merged and st <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], en)
        else:
            merged.append([st, en])
    return [(s, e) for s, e in merged]

def _loop_offline_gaps(user, s_ms, e_ms, min_gap_min=20):
    """Loop-OFFLINE gaps: stretches with NO reason='loop' dosingDecision for longer than
    `min_gap_min` (Loop's decision cadence is ~5 min, so a 20+ min gap is 4+ consecutive
    missed cycles). Deployed Loop wasn't running its loop over the gap — phone off, out of
    range, app killed — so it auto-dosed NOTHING and simply ran scheduled basal. CGM keeps
    flowing (Dexcom uploads independently), so the sim, still fed readings, keeps
    recommending corrections into the rising BG → spurious over-dose (and, on a falling
    trace, over-lows). Same disruption family as a pump suspend (real system not
    controlling) but there is NO suspend record — it can only be seen from the
    dosingDecision cadence. Emitted to the same outage CSV so `--outages-csv` clamps both
    arms' delivery and the scorer drops the window; without it these gaps are the largest
    remaining DTR over-dose residual (bddp11 2026-05-15 17:12→17:58, 47 min: sim wants
    1.5 U into a spike Loop never touched). Distinct from a CGM outage (no readings), which
    `--cgm-stale-guard-min` already handles; clamping a gap that is both is harmless.

    Look back 6h before the window so a gap straddling the start is captured."""
    q = (f"SELECT {_TMS} AS t_ms FROM {TBL} WHERE _userId='{user}' AND type='dosingDecision' "
         f"AND CAST(reason AS STRING)='loop' "
         f"AND {_TMS} BETWEEN {int(s_ms - 6 * 3600 * 1000)} AND {int(e_ms)} ORDER BY {_TMS}")
    df = query(q)
    if len(df) < 2:
        return []
    ts = [int(x) for x in df["t_ms"].tolist()]
    gap_ms = min_gap_min * 60 * 1000
    return [(a, b) for a, b in zip(ts, ts[1:]) if b - a > gap_ms]


def export_donor(user, start, end, outdir, insulin_type=None):
    os.makedirs(outdir, exist_ok=True)
    s_ms, e_ms = _ms_bounds(start, end)
    win = f"_userId='{user}' AND {_TMS} BETWEEN {s_ms} AND {e_ms}"
    # Insulin type from data (insulinFormulation.brand) unless caller forces one.
    if insulin_type is None:
        insulin_type, brand = _insulin_type_from_data(user, s_ms, e_ms)
        print(f"{user}: insulin brand={brand} → --insulin-type {insulin_type}")

    # ---- glucose (cbg, mmol/L → mg/dL) ----
    # Replay LOOP'S OWN CGM stream, not the union of every source. A Tidepool cbg reading
    # appears from MULTIPLE provenances: Loop's own write (origin name '*.loopkit.Loop',
    # i.e. what Loop's CGMManager actually received & cached) AND the vendor app's parallel
    # write (e.g. com.dexcom.g7app) mirrored via HealthKit. Loop uses ITS OWN cached samples
    # for momentum/RC, and LoopKit's linearMomentumEffect DISABLES momentum when that stream
    # fails `count>2 && isContinuous() && hasSingleProvenance`. When Loop's BLE misses a
    # reading (present only in the vendor stream), merging it back FILLS a gap Loop actually
    # had → the sim computes momentum where Loop's guard turned it off (proven at bddp11
    # 05-15 19:32: Loop's own stream missing 19:22 → momentum off → forecast fell; the
    # merged sim kept 19:22 → momentum on → +34 mg/dL divergence). So: keep a reading only if
    # Loop's own app wrote it, and use Loop's own sample time. FALLBACK: donors whose Loop
    # reads HealthKit directly (few/no own-provenance samples) keep the merged stream, else
    # we'd drop everything. See [[momentum-provenance-guard-gap]].
    g = query(_dedup([f"{_TMS} AS t_ms",
        "COALESCE(CAST(get_json_object(value,'$.$numberDouble') AS DOUBLE), "
        "CAST(get_json_object(value,'$.$numberInt') AS DOUBLE)) AS mmol",
        "CAST(origin AS STRING) AS origin"], win, "cbg"))
    buckets = {}   # 1-min bucket -> list of (t_ms, mmol, is_loop)
    for r in g.itertuples():
        v = _fin(r.mmol)
        if v is None: continue
        is_loop = (r.origin is not None) and ("loopkit.Loop" in r.origin)
        buckets.setdefault(int(r.t_ms) // 60000, []).append((int(r.t_ms), v, is_loop))
    n_with_loop = sum(1 for s in buckets.values() if any(x[2] for x in s))
    loop_frac = (n_with_loop / len(buckets)) if buckets else 0.0
    use_own = loop_frac >= 0.5   # Loop is the CGM writer → replay its own (gapped) stream
    glucose = []
    for key in sorted(buckets):
        loop_s = [x for x in buckets[key] if x[2]]
        if use_own:
            if not loop_s:                 # Loop's own stream missed this reading → replay the gap
                continue
            t_ms, v = min(loop_s)[0], loop_s[0][1]   # Loop's own sample time (earliest loop copy)
        else:
            t_ms, v, _ = buckets[key][0]   # fallback: merged stream (Loop reads HealthKit directly)
        glucose.append({"startDate": _iso(t_ms), "quantity": round(v * MMOL, 2)})
    if buckets:
        print(f"{user}: glucose own-stream loop_frac={loop_frac:.2f} use_own={use_own} "
              f"({len(glucose)}/{len(buckets)} readings kept)", flush=True)

    # ---- doses (bolus + basal) ----
    b = query(_dedup([f"{_TMS} AS t_ms", "subType",
        "COALESCE(CAST(get_json_object(normal,'$.$numberDouble') AS DOUBLE), "
        "CAST(get_json_object(normal,'$.$numberInt') AS DOUBLE)) AS units"], win, "bolus"))
    doses = []; manual_ms = []; bseen = set()
    for r in b.sort_values("t_ms").itertuples():
        u = _fin(r.units)
        if u is None: continue
        # Loop mirrors every bolus to HealthKit, so each real bolus has TWO records
        # (origin com.loopkit.Loop + com.apple.HealthKit) with different `id`s but the
        # same time+amount — id-dedup can't catch them. Collapse by (second, amount) so
        # boluses aren't 2x-counted (which corrupts TDD and the counterfactual ICE).
        key = (int(r.t_ms) // 1000, round(u, 4))
        if key in bseen: continue
        bseen.add(key)
        auto = (r.subType == "automated")
        if not auto: manual_ms.append(int(r.t_ms))   # manual meal/correction boluses
        doses.append({"deliveryType": "bolus", "startDate": _iso(int(r.t_ms)), "endDate": _iso(int(r.t_ms)),
                      "volume": round(u, 4), "insulinType": insulin_type, "automatic": auto})
    manual_ms.sort()
    bas = query(_dedup([f"{_TMS} AS t_ms", "deliveryType",
        "COALESCE(CAST(get_json_object(rate,'$.$numberDouble') AS DOUBLE), "
        "CAST(get_json_object(rate,'$.$numberInt') AS DOUBLE)) AS rate",
        "COALESCE(CAST(get_json_object(duration,'$.$numberInt') AS BIGINT), "
        "CAST(get_json_object(duration,'$.$numberLong') AS BIGINT)) AS dur_ms",
        # ACTUAL pulse-quantized delivered units (Loop/diy-loop & trio write this in
        # payload.deliveredUnits). Loop reconciles IOB/effects on delivered, not
        # rate*duration. NULL for pumps that don't report it (aaps/sequel/xdrip) → fall back.
        "COALESCE(CAST(get_json_object(payload,'$.deliveredUnits.$numberDouble') AS DOUBLE), "
        "CAST(get_json_object(payload,'$.deliveredUnits.$numberInt') AS DOUBLE)) AS delivered"], win, "basal"))
    # collect basal segments, then CLIP each end to the next segment's start so
    # overlapping Loop basal records don't double-count delivery.
    segs = []
    for r in bas.itertuples():
        st = int(r.t_ms); dur_ms = int(_fin(r.dur_ms) or 0); rate = _fin(r.rate) or 0.0
        delivered = _fin(r.delivered)   # None if not reported
        segs.append((st, st + dur_ms, rate, delivered, dur_ms))
    segs.sort(key=lambda s: (s[0], s[1]))   # sort by (start, end); `delivered` may be None
    for i, (st, en, rate, delivered, rec_dur) in enumerate(segs):
        if i + 1 < len(segs):
            en = min(en, segs[i + 1][0])      # clip to next start (no overlap)
        if en <= st: continue
        if delivered is not None and rec_dur > 0:
            # Use the actual delivered amount, scaled by the clip ratio so a
            # clipped (superseded) segment counts only its delivered portion.
            vol = delivered * ((en - st) / rec_dur)
        else:
            vol = rate * ((en - st) / 3600000.0)   # fallback: nominal rate*duration
        # Emit the programmed temp RATE (U/hr) so the sim can truncate an in-progress
        # temp basal to `rate × elapsed` at the decision instant — matching deployed
        # Loop-main, which trims every non-bolus dose to `basalDosingEnd = now()` before
        # forecasting (LoopKit DoseStore.getGlucoseEffects → DoseEntry.trimmed(to:)).
        # Without it the sim projects the running temp forward, over-/under-counting its
        # future portion (the basal-dominant forecast-tail residual). Tidepool carries
        # `rate` (+ suppressed.rate for scheduled) on every basal record.
        doses.append({"deliveryType": "basal", "startDate": _iso(st), "endDate": _iso(en),
                      "volume": round(vol, 5), "tempRate": round(rate, 5),
                      "insulinType": insulin_type, "automatic": True})
    doses.sort(key=lambda d: d["startDate"])

    # ---- carbs (food: nutrition.carbohydrate.net g, estimatedAbsorptionDuration s) ----
    f = query(_dedup([f"{_TMS} AS t_ms", "nutrition"], win, "food"))
    import bisect
    PAIR_WIN = 10 * 60 * 1000   # ±10 min: a manual bolus this close = co-logged with the carb
    POST_BOLUS_DELAY = 10 * 1000  # dosingVisibleDate = paired bolus + 10s (matches NS postBolusVisibilityDelay)
    def paired_bolus(t):
        i = bisect.bisect_left(manual_ms, t)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(manual_ms) and abs(manual_ms[j] - t) <= PAIR_WIN:
                if best is None or abs(manual_ms[j] - t) < abs(best - t): best = manual_ms[j]
        return best
    carbs = []; cby = {}
    for r in f.itertuples():
        try: nut = json.loads(r.nutrition)
        except Exception: continue
        grams = _fin(_num(((nut.get("carbohydrate") or {}).get("net"))))
        if not grams: continue
        t = int(r.t_ms)
        absorb = _fin(_num(nut.get("estimatedAbsorptionDuration")))  # seconds
        # dedup: Tidepool food records are re-uploaded many times AND HealthKit-mirrored;
        # collapse to one real entry per (minute, grams). CRITICAL: the mirror copies carry
        # NO estimatedAbsorptionDuration (only the native Loop upload does), and they may
        # sort first — so keeping the first-seen record silently drops the real absorption
        # time and the carb defaults to 3h, systematically under-forecasting fast meals.
        # Keep the first-seen entry but MERGE in the absorption from whichever duplicate has
        # it (native Loop record). (Same family as the HealthKit bolus double-count.)
        key = (t // 60000, round(grams, 1))
        if key in cby:
            if absorb and "absorptionTime" not in cby[key]:
                cby[key]["absorptionTime"] = absorb   # backfill from the version that has it
            continue
        # dosingVisibleDate: defer past the paired manual meal bolus so the sim's
        # auto-dosing doesn't cover the carb BEFORE the (passed-through) manual bolus
        # does — avoids double-covering announced meals (crash-low). startDate = meal
        # time (drives absorption); entryDate = meal time (best available).
        pb = paired_bolus(t)
        vis = (pb + POST_BOLUS_DELAY) if pb is not None else t
        e = {"startDate": _iso(t), "entryDate": _iso(t), "dosingVisibleDate": _iso(vis),
             "grams": round(grams, 1)}
        if absorb: e["absorptionTime"] = absorb
        cby[key] = e            # same dict object is appended below; later backfill reflects here
        carbs.append(e)

    # ---- therapy (per-era pumpSettings schedules across the window; expand daily schedules) ----
    therapy = _therapy(user, s_ms, e_ms, insulin_type)

    for name, obj in [("glucose", glucose), ("doses", doses), ("carbs", carbs), ("therapy", therapy)]:
        with open(os.path.join(outdir, f"{name}.json"), "w") as fh:
            json.dump(obj, fh, allow_nan=False)

    # ---- disruptions: pump suspends + loop-offline gaps → outage CSV (clamp + exclude from scoring) ----
    import csv as _csv
    sus = _suspends(user, s_ms, e_ms)
    off = _loop_offline_gaps(user, s_ms, e_ms)
    # merge all disruption intervals (suspends + offline gaps), tagging source
    tagged = [(s, e, "suspend", "tidepool/suspend_dose") for s, e in sus] \
           + [(s, e, "loop_offline", "tidepool/decision_gap") for s, e in off]
    tagged.sort()
    merged = []
    for s, e, reason, src in tagged:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
            if merged[-1][2] != reason:
                merged[-1][2], merged[-1][3] = "disruption", "tidepool/merged"
        else:
            merged.append([s, e, reason, src])
    dis_path = os.path.join(outdir, "disruptions.csv")
    with open(dis_path, "w", newline="") as fh:
        w = _csv.writer(fh); w.writerow(["start", "end", "reason", "source", "notes"])
        for s, e, reason, src in merged:
            w.writerow([_iso(s), _iso(e), reason, src, f"{reason} {round((e - s) / 60000)}min"])
    sus_h = sum((e - s) for s, e in sus) / 3600000.0
    off_h = sum((e - s) for s, e in off) / 3600000.0

    print(f"{user}: glucose={len(glucose)} doses={len(doses)} carbs={len(carbs)} "
          f"therapy(basal={len(therapy['basal'])},isf={len(therapy['sensitivity'])}) "
          f"suspends={len(sus)}({sus_h:.1f}h) offline_gaps={len(off)}({off_h:.1f}h) → {outdir}")
    return dict(glucose=len(glucose), doses=len(doses), carbs=len(carbs))

def _sched(j):
    """[{amount/rate/high/low, start(ms)}] → sorted [(start_ms, value-dict)]."""
    arr = json.loads(j)
    # arr is {"Default":[...]} keyed by schedule name; take the (first) schedule
    if isinstance(arr, dict):
        arr = next(iter(arr.values()))
    out = []
    for it in arr:
        out.append((int(_num(it["start"])), it))
    return sorted(out, key=lambda x: x[0])

def _expand(daily, s_ms, e_ms, valfn, tz="UTC"):
    """Expand a daily schedule [(start_ms_from_LOCAL_midnight, item)] to absolute UTC
    segments over [s,e]. Tidepool schedules are keyed to the user's LOCAL midnight, so
    they must be laid on local-day boundaries (DST-aware): expanding at UTC midnight
    shifts the whole basal/ISF/CR/target timeline by the UTC offset (e.g. ~6-7h for
    America/Denver), so the replay runs the wrong scheduled basal/ISF/CR at every
    wall-clock time."""
    import pytz
    zone = pytz.timezone(tz) if tz else pytz.UTC
    out = []
    s_utc = datetime.fromtimestamp(s_ms / 1000.0, tz=timezone.utc)
    e_utc = datetime.fromtimestamp(e_ms / 1000.0, tz=timezone.utc)
    d = s_utc.astimezone(zone).date()
    last = e_utc.astimezone(zone).date()
    while d <= last:
        mid = zone.localize(datetime(d.year, d.month, d.day))
        nxt = zone.localize(datetime(d.year, d.month, d.day) + timedelta(days=1))
        for i, (sms, item) in enumerate(daily):
            seg_s = zone.normalize(mid + timedelta(milliseconds=sms))
            seg_e = zone.normalize(mid + timedelta(milliseconds=daily[i + 1][0])) if i + 1 < len(daily) else nxt
            s = max(seg_s.astimezone(timezone.utc), s_utc)
            e = min(seg_e.astimezone(timezone.utc), e_utc)
            if e > s:
                rec = {"startDate": s.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                       "endDate": e.strftime("%Y-%m-%dT%H:%M:%S.000Z")}
                rec.update(valfn(item))
                out.append(rec)
        d += timedelta(days=1)
    return out

def _merge_adj(segs):
    """Merge consecutive segments (startDate/endDate ISO + values) that share a
    boundary AND identical values — keeps concatenated per-era schedules compact."""
    out = []
    for r in segs:
        val = {k: v for k, v in r.items() if k not in ("startDate", "endDate")}
        if out and out[-1]["endDate"] == r["startDate"] and \
           {k: v for k, v in out[-1].items() if k not in ("startDate", "endDate")} == val:
            out[-1]["endDate"] = r["endDate"]
        else:
            out.append(dict(r))
    return out

def _therapy(user, s_ms, e_ms, insulin_type="rapidActingAdult"):
    # Full pumpSettings history up to window end (NO lower bound — we need the record
    # active at window START too), oldest→newest. We track SETTINGS CHANGES over the
    # window by building per-era dated schedules, instead of applying one end-of-window
    # snapshot across the whole window (which mis-replays base basal/ISF/CR/target for
    # the pre-edit period — biased toward the newest settings since it took ≤ window-end).
    ps = query(f"""SELECT {_TMS} AS t_ms, units, basalSchedules, insulinSensitivities, carbRatios, bgTargets, bgSafetyLimit, timezone
        FROM {TBL} WHERE _userId='{user}' AND type='pumpSettings' AND {_TMS} <= {e_ms}
        ORDER BY t_ms ASC""")
    if ps.empty:
        raise RuntimeError(f"no pumpSettings for {user} before window end")

    # Collapse consecutive records with identical therapy content into distinct eras
    # (Loop re-uploads pumpSettings frequently with no change; without this the schedules
    # churn into thousands of redundant segments). Each era is keyed by when it first
    # took effect.
    def _sig(r):
        return (r.basalSchedules, r.insulinSensitivities, r.carbRatios, r.bgTargets,
                str(r.bgSafetyLimit), r.timezone)
    eras, prev = [], None
    for r in ps.itertuples():
        sig = _sig(r)
        if sig != prev:
            eras.append((int(r.t_ms), r)); prev = sig

    # For each era, expand schedules over [max(era_start, s_ms), min(next_era_start, e_ms)]
    # and concatenate. Eras are sorted & contiguous, so the result is sorted & non-overlapping.
    basal, sens, cr, tgt, contrib = [], [], [], [], []
    for i, (t0, r) in enumerate(eras):
        era_s = max(t0, s_ms)
        era_e = min(eras[i + 1][0] if i + 1 < len(eras) else e_ms, e_ms)
        if era_e <= era_s:
            continue
        tz = r.timezone or "UTC"
        basal += _expand(_sched(r.basalSchedules), era_s, era_e,
                         lambda it: {"value": round(_num(it["rate"]), 4)}, tz)
        sens += _expand(_sched(r.insulinSensitivities), era_s, era_e,
                        lambda it: {"value": round(_num(it["amount"]) * MMOL, 2)}, tz)
        cr += _expand(_sched(r.carbRatios), era_s, era_e,
                      lambda it: {"value": round(_num(it["amount"]), 2)}, tz)
        tgt += _expand(_sched(r.bgTargets), era_s, era_e,
                       lambda it: {"lowerBound": round(_num(it["low"]) * MMOL, 1),
                                   "upperBound": round(_num(it["high"]) * MMOL, 1)}, tz)
        contrib.append(r)
    basal, sens, cr, tgt = map(_merge_adj, (basal, sens, cr, tgt))
    if len(contrib) > 1:
        print(f"{user}: therapy spans {len(contrib)} settings eras in-window (tracking mid-window changes)")

    # suspendThreshold is a single scalar in the therapy schema (not a schedule), so if it
    # changed in-window we can't represent the timeline — use the latest and warn.
    safeties = [_num(r.bgSafetyLimit) for r in contrib]
    safety = next((s for s in reversed(safeties) if s), None)
    distinct = sorted({round(s * MMOL, 1) for s in safeties if s})
    if len(distinct) > 1:
        print(f"{user}: WARNING suspendThreshold changed in-window {distinct} mg/dL — "
              f"schema stores one scalar; using latest {round(safety * MMOL, 1)}")

    # Emit temporary overrides as CAUSAL windows + RAW (un-baked) schedules. The sim
    # (InputWindowBuilder decision-time gating) then applies each override ONLY to
    # decisions at/after its start — a future override is excluded from earlier decisions.
    # We previously BAKED overrides into the schedules as fixed absolute windows, which
    # LEAKED a not-yet-enacted override into earlier decisions' 6h forecasts: e.g. a noon
    # override's raised target reached a 07:47 decision's horizon → insulinCorrection's
    # min-guard (min < target-at-eventual) mis-fired → spurious auto-bolus=0 (under-dose).
    # OverrideWindow.factor = insulinNeedsScaleFactor (basal×f, ISF÷f, CR÷f); target in mg/dL.
    ovs = _overrides(user, s_ms, e_ms, e_ms)
    override_windows = []
    for st, en, d in ovs:
        w = {"start": _iso(st), "end": _iso(en), "indefinite": False}
        bsf = d.get("basal_sf")
        if bsf is not None and abs(bsf - 1.0) > 1e-6:
            w["factor"] = round(bsf, 5)
        if d.get("tgt_low") is not None and d.get("tgt_high") is not None:
            w["targetLo"] = round(d["tgt_low"] * MMOL, 1)
            w["targetHi"] = round(d["tgt_high"] * MMOL, 1)
        override_windows.append(w)
    if override_windows:
        tot_h = sum((e - s) for s, e, _ in ovs) / 3600000.0
        print(f"{user}: {len(override_windows)} override windows ({tot_h:.0f}h) — applied CAUSALLY per-decision (not baked)")

    # base schedules stay un-baked; raw* mirror them so InputWindowBuilder's override
    # gating (applyOv, needs non-empty rawBasal + overrideWindows) engages.
    return {"basal": basal, "sensitivity": sens, "carbRatio": cr, "target": tgt,
            "rawBasal": basal, "rawSensitivity": sens, "rawCarbRatio": cr, "rawTarget": tgt,
            "overrideWindows": override_windows,
            "suspendThreshold": round(safety * MMOL, 1) if safety else 70.0,
            "maxBolus": 12.0, "maxBasalRate": 8.0, "insulinType": insulin_type}

if __name__ == "__main__":
    import sys
    export_donor(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
