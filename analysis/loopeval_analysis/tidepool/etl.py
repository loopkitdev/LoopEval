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
    export_donor("d6954e6498", "2026-02-01", "2026-04-01", "/Users/pete/dev/loopalgo/runs/2026-06-15-tidepool/d6954e6498")
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

def export_donor(user, start, end, outdir):
    os.makedirs(outdir, exist_ok=True)
    s_ms, e_ms = _ms_bounds(start, end)
    win = f"_userId='{user}' AND {_TMS} BETWEEN {s_ms} AND {e_ms}"

    # ---- glucose (cbg, mmol/L → mg/dL) ----
    g = query(f"""SELECT {_TMS} AS t_ms,
        COALESCE(CAST(get_json_object(value,'$.$numberDouble') AS DOUBLE),
                 CAST(get_json_object(value,'$.$numberInt') AS DOUBLE)) AS mmol
        FROM {TBL} WHERE {win} AND type='cbg' ORDER BY t_ms""")
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
    b = query(f"""SELECT {_TMS} AS t_ms, subType,
        COALESCE(CAST(get_json_object(normal,'$.$numberDouble') AS DOUBLE),
                 CAST(get_json_object(normal,'$.$numberInt') AS DOUBLE)) AS units
        FROM {TBL} WHERE {win} AND type='bolus' ORDER BY t_ms""")
    doses = []
    for r in b.itertuples():
        u = _fin(r.units)
        if u is None: continue
        doses.append({"deliveryType": "bolus", "startDate": _iso(int(r.t_ms)), "endDate": _iso(int(r.t_ms)),
                      "volume": round(u, 4), "insulinType": "rapidActingAdult",
                      "automatic": (r.subType == "automated")})
    bas = query(f"""SELECT {_TMS} AS t_ms, deliveryType,
        COALESCE(CAST(get_json_object(rate,'$.$numberDouble') AS DOUBLE),
                 CAST(get_json_object(rate,'$.$numberInt') AS DOUBLE)) AS rate,
        COALESCE(CAST(get_json_object(duration,'$.$numberInt') AS BIGINT),
                 CAST(get_json_object(duration,'$.$numberLong') AS BIGINT)) AS dur_ms
        FROM {TBL} WHERE {win} AND type='basal' ORDER BY t_ms""")
    # collect basal segments, then CLIP each end to the next segment's start so
    # overlapping Loop basal records don't double-count delivery.
    segs = []
    for r in bas.itertuples():
        st = int(r.t_ms); dur_ms = int(_fin(r.dur_ms) or 0); rate = _fin(r.rate) or 0.0
        segs.append((st, st + dur_ms, rate))
    segs.sort()
    for i, (st, en, rate) in enumerate(segs):
        if i + 1 < len(segs):
            en = min(en, segs[i + 1][0])      # clip to next start (no overlap)
        if en <= st: continue
        doses.append({"deliveryType": "basal", "startDate": _iso(st), "endDate": _iso(en),
                      "volume": round(rate * ((en - st) / 3600000.0), 5),
                      "insulinType": "rapidActingAdult", "automatic": True})
    doses.sort(key=lambda d: d["startDate"])

    # ---- carbs (food: nutrition.carbohydrate.net g, estimatedAbsorptionDuration s) ----
    f = query(f"""SELECT {_TMS} AS t_ms, nutrition FROM {TBL} WHERE {win} AND type='food' ORDER BY t_ms""")
    carbs = []; cseen = set()
    for r in f.itertuples():
        try: nut = json.loads(r.nutrition)
        except Exception: continue
        grams = _fin(_num(((nut.get("carbohydrate") or {}).get("net"))))
        if not grams: continue
        # dedup: Tidepool food records are re-uploaded many times; collapse entries
        # at the same minute with the same grams (one real carb entry).
        key = (int(r.t_ms) // 60000, round(grams, 1))
        if key in cseen: continue
        cseen.add(key)
        absorb = _fin(_num(nut.get("estimatedAbsorptionDuration")))  # seconds
        iso = _iso(int(r.t_ms))
        e = {"startDate": iso, "entryDate": iso, "dosingVisibleDate": iso, "grams": round(grams, 1)}
        if absorb: e["absorptionTime"] = absorb
        carbs.append(e)

    # ---- therapy (latest pumpSettings at/before window start; expand daily schedules) ----
    therapy = _therapy(user, s_ms, e_ms)

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

def _expand(daily, s_ms, e_ms, valfn):
    """Expand a daily schedule [(start_ms_midnight, item)] to absolute segments over [s,e]."""
    out = []
    day0 = datetime.fromtimestamp(s_ms / 1000.0, tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    day = day0
    end_dt = datetime.fromtimestamp(e_ms / 1000.0, tz=timezone.utc)
    while day < end_dt:
        for i, (sms, item) in enumerate(daily):
            seg_s = day + timedelta(milliseconds=sms)
            seg_e = (day + timedelta(milliseconds=daily[i + 1][0])) if i + 1 < len(daily) else (day + timedelta(days=1))
            s = max(seg_s, datetime.fromtimestamp(s_ms / 1000.0, tz=timezone.utc))
            e = min(seg_e, end_dt)
            if e > s:
                rec = {"startDate": s.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                       "endDate": e.strftime("%Y-%m-%dT%H:%M:%S.000Z")}
                rec.update(valfn(item))
                out.append(rec)
        day += timedelta(days=1)
    return out

def _therapy(user, s_ms, e_ms):
    ps = query(f"""SELECT {_TMS} AS t_ms, units, basalSchedules, insulinSensitivities, carbRatios, bgTargets, bgSafetyLimit
        FROM {TBL} WHERE _userId='{user}' AND type='pumpSettings' AND {_TMS} <= {e_ms}
        ORDER BY t_ms DESC LIMIT 1""")
    if ps.empty:
        raise RuntimeError(f"no pumpSettings for {user} before window end")
    row = ps.iloc[0]
    basal = _expand(_sched(row.basalSchedules), s_ms, e_ms,
                    lambda it: {"value": round(_num(it["rate"]), 4)})
    sens = _expand(_sched(row.insulinSensitivities), s_ms, e_ms,
                   lambda it: {"value": round(_num(it["amount"]) * MMOL, 2)})
    cr = _expand(_sched(row.carbRatios), s_ms, e_ms,
                 lambda it: {"value": round(_num(it["amount"]), 2)})
    tgt = _expand(_sched(row.bgTargets), s_ms, e_ms,
                  lambda it: {"lowerBound": round(_num(it["low"]) * MMOL, 1),
                              "upperBound": round(_num(it["high"]) * MMOL, 1)})
    safety = _num(row.bgSafetyLimit)
    return {"basal": basal, "sensitivity": sens, "carbRatio": cr, "target": tgt,
            "suspendThreshold": round(safety * MMOL, 1) if safety else 70.0,
            "maxBolus": 12.0, "maxBasalRate": 8.0, "insulinType": "rapidActingAdult"}

if __name__ == "__main__":
    import sys
    export_donor(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
