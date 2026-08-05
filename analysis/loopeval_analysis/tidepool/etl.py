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

def export_donor(user, start, end, outdir, insulin_type="rapidActingAdult"):
    os.makedirs(outdir, exist_ok=True)
    s_ms, e_ms = _ms_bounds(start, end)
    win = f"_userId='{user}' AND {_TMS} BETWEEN {s_ms} AND {e_ms}"

    # ---- glucose (cbg, mmol/L → mg/dL) ----
    g = query(_dedup([f"{_TMS} AS t_ms",
        "COALESCE(CAST(get_json_object(value,'$.$numberDouble') AS DOUBLE), "
        "CAST(get_json_object(value,'$.$numberInt') AS DOUBLE)) AS mmol"], win, "cbg"))
    # dedup cbg by timestamp (Tidepool has duplicate uploads; dupes break the
    # velocity/ICE grid). Keep last per (rounded-to-min) timestamp.
    seen = set(); glucose = []
    for r in g.itertuples():
        v = _fin(r.mmol)
        if v is None: continue
        key = int(r.t_ms) // 60000  # 1-min bucket
        if key in seen: continue
        seen.add(key)
        glucose.append({"startDate": _iso(int(r.t_ms)), "quantity": round(v * MMOL, 2)})

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
    segs.sort()
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
        doses.append({"deliveryType": "basal", "startDate": _iso(st), "endDate": _iso(en),
                      "volume": round(vol, 5),
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
    carbs = []; cseen = set()
    for r in f.itertuples():
        try: nut = json.loads(r.nutrition)
        except Exception: continue
        grams = _fin(_num(((nut.get("carbohydrate") or {}).get("net"))))
        if not grams: continue
        t = int(r.t_ms)
        # dedup: Tidepool food records are re-uploaded many times; collapse entries
        # at the same minute with the same grams (one real carb entry).
        key = (t // 60000, round(grams, 1))
        if key in cseen: continue
        cseen.add(key)
        absorb = _fin(_num(nut.get("estimatedAbsorptionDuration")))  # seconds
        # dosingVisibleDate: defer past the paired manual meal bolus so the sim's
        # auto-dosing doesn't cover the carb BEFORE the (passed-through) manual bolus
        # does — avoids double-covering announced meals (crash-low). startDate = meal
        # time (drives absorption); entryDate = meal time (best available).
        pb = paired_bolus(t)
        vis = (pb + POST_BOLUS_DELAY) if pb is not None else t
        e = {"startDate": _iso(t), "entryDate": _iso(t), "dosingVisibleDate": _iso(vis),
             "grams": round(grams, 1)}
        if absorb: e["absorptionTime"] = absorb
        carbs.append(e)

    # ---- therapy (latest pumpSettings at/before window start; expand daily schedules) ----
    therapy = _therapy(user, s_ms, e_ms, insulin_type)

    for name, obj in [("glucose", glucose), ("doses", doses), ("carbs", carbs), ("therapy", therapy)]:
        with open(os.path.join(outdir, f"{name}.json"), "w") as fh:
            json.dump(obj, fh, allow_nan=False)
    print(f"{user}: glucose={len(glucose)} doses={len(doses)} carbs={len(carbs)} "
          f"therapy(basal={len(therapy['basal'])},isf={len(therapy['sensitivity'])}) → {outdir}")
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

def _therapy(user, s_ms, e_ms, insulin_type="rapidActingAdult"):
    ps = query(f"""SELECT {_TMS} AS t_ms, units, basalSchedules, insulinSensitivities, carbRatios, bgTargets, bgSafetyLimit, timezone
        FROM {TBL} WHERE _userId='{user}' AND type='pumpSettings' AND {_TMS} <= {e_ms}
        ORDER BY t_ms DESC LIMIT 1""")
    if ps.empty:
        raise RuntimeError(f"no pumpSettings for {user} before window end")
    row = ps.iloc[0]
    tz = row.timezone or "UTC"
    basal = _expand(_sched(row.basalSchedules), s_ms, e_ms,
                    lambda it: {"value": round(_num(it["rate"]), 4)}, tz)
    sens = _expand(_sched(row.insulinSensitivities), s_ms, e_ms,
                   lambda it: {"value": round(_num(it["amount"]) * MMOL, 2)}, tz)
    cr = _expand(_sched(row.carbRatios), s_ms, e_ms,
                 lambda it: {"value": round(_num(it["amount"]), 2)}, tz)
    tgt = _expand(_sched(row.bgTargets), s_ms, e_ms,
                  lambda it: {"lowerBound": round(_num(it["low"]) * MMOL, 1),
                              "upperBound": round(_num(it["high"]) * MMOL, 1)}, tz)
    safety = _num(row.bgSafetyLimit)
    return {"basal": basal, "sensitivity": sens, "carbRatio": cr, "target": tgt,
            "suspendThreshold": round(safety * MMOL, 1) if safety else 70.0,
            "maxBolus": 12.0, "maxBasalRate": 8.0, "insulinType": insulin_type}

if __name__ == "__main__":
    import sys
    export_donor(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
