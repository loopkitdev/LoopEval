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

def _iso_to_ms(s):
    """ISO8601 string ('…Z' or with offset) → epoch ms, or None."""
    if not s or not isinstance(s, str): return None
    try:
        return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1000)
    except Exception:
        return None

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

from .provenance import write_manifest as _write_manifest

# ---------------------------------------------------------------------------
# BUMP THIS whenever an ETL change alters the DATA an export produces (dedup
# rules, decoding, reconstruction, new/changed fields). It is the staleness
# gate: `provenance.scan()` marks every export written at a lower version as
# STALE so it can be re-exported or deleted instead of silently re-analysed.
# Cosmetic edits (comments, prints, refactors) must NOT bump it.
#
#   1  pre-2026-08-12 baseline
#   2  basal dedup keeps the LATEST version of an id (92fafda) — earlier exports
#      carry 21-88 h of phantom basal [[stale-preFix-cohort-exports]]
#   3  disruptions.csv gains `pump_error` rows from dosingDecision.errors — cycles
#      Loop decided but the pump never received (bddp11: 220 cycles / 72.5 U in two
#      weeks). Earlier exports let the sim deliver through a disconnected pump.
#   4  new stale_cgm.csv: decisions Loop anchored on a stale sample
#      (bgForecast[0] vs the export's latest sample) — comparability exclusions
#      for verification, NOT delivery clamps.
#   5  post-dating guarded: >2% stale-detection rate = multi-source/1-min CGM
#      (bddp03 post-dated 12,358 samples at v4 — a wholesale input rewrite on a
#      heuristic validated only for clean 5-min streams); such donors keep
#      stale_cgm.csv but post-date nothing.
#   6  overrides: mid-flight slider edits expand to per-version sub-windows
#      (distinct ids under one enactment, activation = createdTime). bddp09's
#      24.5h window replayed the 02:04 slider position (×0.9) back into 21:58;
#      reality was ×1.04 → none → ×0.9.
#   7  carb visibility pairs FORWARD-only to the bolus that SAVED the entry
#      (bddp03: nearest-bolus pairing made a 70g meal visible 85 s before the
#      field's own carb-free forecast proves the store held it).
#   8  new decision_times.csv: every reason='loop' decision instant + recorded
#      recommendation — field-cadence stepping and no-rec cycle flags become
#      dataset properties instead of per-analysis Databricks queries.
#   9  carb visibility = payload.addedDate (Loop's recorded store-save instant),
#      proven exact on bddp03; bolus-pairing demoted to fallback for records
#      without addedDate. v7/v8 forward-pairing could defer a standalone entry
#      to an unrelated later bolus (bddp03 05-21: 7 min late, missed a 3.7 U rec).
#  10  exclude soft-deleted records (_active='false' + archivedTime): user-deleted
#      carbs/boluses stayed in every export (bddp03: 9 carbs incl. the 2.75 U
#      residual's phantom 80 g; bddp04: 7 deleted boluses = phantom insulin).
#  11  basal dedup prefers the NATIVE Loop row over its HealthKit mirror — mirror
#      `rate` is unreliable (0.00 for a real 0.15 temp; delivered-average vs
#      programmed). bddp11: 5,346 conflicting-rate groups, up to 1.25 U/hr.
#  12  pod-reported suspends carry receivedDate=createdTime (prompt-upload
#      evidence only) — a decision must not see a suspension Loop hadn't
#      learned yet (bddp11 07-04 00:15: +15.8 mg/dL from an unknown suspend
#      projected 30 min forward).
#  13  decision_times.csv gains `no_dose_guard`: loop cycles Loop ran but bailed
#      before the dosing path (errors pumpDataTooOld/glucoseTooOld, no forecast,
#      no rec stored). The replay skips those cycles — the guard's trigger
#      (pump-comms freshness) is exogenous, but Loop's error record marks the
#      exact cycles (bddp11: 107+18 over 2 mo; 07-04 00:55-01:00 read as 1.0-U
#      "mismatches" until this).
DATA_VERSION = 13


def _dedup(cols, where, typ, order="_id"):
    """One row per Tidepool logical `id` (the table has exact-duplicate rows AND
    edit-versions sharing an id; without this everything is 2-3× over-counted).
    `cols` are inner expressions ("EXPR AS alias" or a plain column); the outer
    query selects only the aliases. `order` picks WHICH version of an id survives
    (ROW_NUMBER rn=1) — default `_id` (earliest). For BASAL pass `_id DESC`: a temp
    basal is uploaded as an interim `dur=0` record FIRST and the authoritative
    completed segment (e.g. a `dur=20m` suspend) LATER, both sharing the id; keeping
    the earliest grabs the interim `dur=0`, which the clip then drops (en<=st),
    leaving a GAP that `annotated(fillBasalGaps:true)` backfills with SCHEDULED basal
    — crediting phantom insulin during suspends the pump delivered 0. Keep the LATEST
    (final) version instead. [[phantom-basal-dropped-suspends]]"""
    inner = ", ".join(cols)
    aliases = [c.split(" AS ")[-1].strip() if " AS " in c else c.strip() for c in cols]
    outer = ", ".join(aliases)
    return (f"SELECT {outer} FROM (SELECT {inner}, ROW_NUMBER() OVER (PARTITION BY id ORDER BY {order}) rn "
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
    absolute-time intervals with the effective scale factors + target.

    An enactment is a group of rows sharing one `time`; WITHIN it there are two kinds of
    versioning, and conflating them mis-replays hours of therapy:

    • SAME `id`, several rows — Tidepool edit-versions of one state (e.g. the finite
      `duration` stamped when the override ends). Resolve by LATEST modifiedTime — the
      early-cancel fix (a 2.6h "hypo" override otherwise runs its 4h scheduled length,
      ISF held ×3.33 for 84 extra minutes → spurious severe lows).

    • DIFFERENT `id`s — MID-FLIGHT EDITS: the user moved the needs slider while the
      override ran, and each slider position is its own record whose `createdTime` is
      when it took effect. bddp09 2026-06-05 21:58 (the case that exposed this): enacted
      ×1.04, edited to no-factors at 23:34, to ×0.90 at 06-06 02:04, ended 22:32.
      Collapsing to the final version replayed ×0.90 across all 24.5h — the under-dose
      cluster at 23:28-23:48 ran under ×1.04 in reality (confirmed by the pod's scheduled
      basal: 1.04 until ~23:23, 1.00 after). Emit ONE SUB-WINDOW PER VERSION:
      [activation, next version's activation), first from the enactment instant.
      `createdTime` is server ingestion, so activation can lag the true edit by an
      upload batch — bddp09's boundaries land within minutes of the pod-basal evidence.

    Enactment END: last version's finite duration (start+dur), else its modifiedTime
    (indefinite turned off), else the next enactment; always cut by supersession.
    Returns sorted (start_ms, end_ms, {isf_sf, basal_sf, cr_sf, tgt_low, tgt_high,
    preset})."""
    q = (f"SELECT {_TMS} AS t_ms, "
         f"CAST(get_json_object(duration,'$.$numberInt') AS BIGINT) AS dur_s, "
         f"overridePreset AS preset, "
         f"get_json_object(insulinSensitivityScaleFactor,'$.$numberDouble') AS isf_sf, "
         f"get_json_object(basalRateScaleFactor,'$.$numberDouble') AS basal_sf, "
         f"get_json_object(carbRatioScaleFactor,'$.$numberDouble') AS cr_sf, "
         f"get_json_object(bgTarget,'$.low.$numberDouble') AS tgt_low, "
         f"get_json_object(bgTarget,'$.high.$numberDouble') AS tgt_high, "
         f"CAST(get_json_object(modifiedTime,'$.$date.$numberLong') AS BIGINT) AS mod_ms, "
         f"CAST(get_json_object(createdTime,'$.$date.$numberLong') AS BIGINT) AS crt_ms, id "
         # NO id-dedup: Tidepool stores an override as EDIT-VERSIONS sharing one id — it's
         # first uploaded INDEFINITE (duration null), then EDITED with the resolved finite
         # duration when it ends. Keeping rn=1 (oldest _id) drops the finite end → the
         # override looks indefinite and over-extends. Fetch all versions; the per-timestamp
         # collapse below keeps the finite (resolved) one.
         f"FROM {TBL} WHERE _userId='{user}' AND type='deviceEvent' AND subType='pumpSettingsOverride'")
    df = query(q)
    if df.empty:
        return []
    # Group rows: enactment (t//1000, preset) -> logical record (id) -> versions.
    enact = {}
    for r in df.itertuples():
        t = int(r.t_ms); key = (t // 1000, r.preset)
        _m = _fin(r.mod_ms); _c = _fin(r.crt_ms)
        ver = dict(t=t, dur=_fin(r.dur_s),
                   mod=int(_m) if _m is not None else None,
                   crt=int(_c) if _c is not None else None,
                   preset=r.preset,
                   isf=_fin(r.isf_sf) or 1.0, basal=_fin(r.basal_sf) or 1.0, cr=_fin(r.cr_sf) or 1.0,
                   tlo=_fin(r.tgt_low), thi=_fin(r.tgt_high))
        enact.setdefault(key, {}).setdefault(r.id, []).append(ver)

    evs = []   # one entry per enactment: ordered sub-versions + resolved end
    for key, byid in enact.items():
        subs = []
        for _id, vers in byid.items():
            # Same-id edit-versions: content from the LATEST modifiedTime (early-cancel
            # fix — it holds the resolved duration); ACTIVATION from the EARLIEST
            # createdTime (the end-stamp's late createdTime is when the override ENDED,
            # not when this slider position began).
            best = max(vers, key=lambda v: (v["mod"] is not None, v["mod"] or 0))
            act = min((v["crt"] for v in vers if v["crt"] is not None), default=best["t"])
            subs.append(dict(best, act=act))
        subs.sort(key=lambda v: v["act"])
        subs[0]["act"] = subs[0]["t"]          # first version runs from the enactment instant
        evs.append(dict(t=subs[0]["t"], subs=subs))
    evs.sort(key=lambda e: e["t"])

    ivals = []
    for i, ev in enumerate(evs):
        nxt = evs[i + 1]["t"] if i + 1 < len(evs) else e_win_ms
        last = ev["subs"][-1]
        if last["dur"] is not None:
            end = ev["t"] + int(last["dur"] * 1000)             # finite: start + duration
        elif last["mod"] is not None and last["mod"] > ev["t"]:
            end = last["mod"]                                     # indefinite: ended at modifiedTime
        else:
            end = nxt                                             # truly-open: until next enactment
        end = min(end, nxt, e_win_ms)
        for j, sub in enumerate(ev["subs"]):
            sub_end = ev["subs"][j + 1]["act"] if j + 1 < len(ev["subs"]) else end
            st = max(sub["act"], s_ms)
            en = min(sub_end, end)
            if en <= st:
                continue
            ivals.append((st, en, {"isf_sf": sub["isf"], "basal_sf": sub["basal"], "cr_sf": sub["cr"],
                                   "tgt_low": sub["tlo"], "tgt_high": sub["thi"], "preset": sub["preset"]}))
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

    TWO record shapes carry suspends and BOTH must be read:
      1. `basal deliveryType='suspend'` — a suspend with an explicit `duration` (ms).
      2. `deviceEvent subType='status'` with `status='suspended'`/`'resumed'` — a PUMP
         STATUS suspend (manual suspend, or the pod expiring / coming off and no new pod
         put on). It has NO duration; the interval is [suspended, next resumed]. These are
         the LONG ones (a pod-off can run tens of hours) and were previously MISSED —
         bddp10 07-05 19:21→07-07 20:28 was a 49h pod-off (every dosingDecision across it
         carried `pumpDataTooOld`, BG pinned at 401, IOB→0) that the sim then dosed into
         and cratered. 55 such intervals / 139h (4.6% of window) for bddp10 alone.
    Look back 7 days for status events so a suspend straddling the window start (and its
    opening `suspended` edge) is captured; merge overlapping/adjacent windows."""
    iv = []
    # (1) basal deliveryType='suspend' (has duration)
    q = (f"SELECT {_TMS} AS t_ms, "
         f"COALESCE(CAST(get_json_object(duration,'$.$numberInt') AS BIGINT), "
         f"CAST(get_json_object(duration,'$.$numberLong') AS BIGINT)) AS dur_ms "
         f"FROM {TBL} WHERE _userId='{user}' AND type='basal' AND deliveryType='suspend' "
         f"AND {_TMS} BETWEEN {int(s_ms - 6 * 3600 * 1000)} AND {int(e_ms)}")
    for r in query(q).itertuples():
        dur = _fin(r.dur_ms)
        if dur and dur > 0:
            iv.append((int(r.t_ms), int(r.t_ms) + int(dur)))
    # (2) deviceEvent status suspended->resumed (no duration; pair the edges)
    qs = (f"SELECT {_TMS} AS t_ms, CAST(status AS STRING) st FROM {TBL} "
          f"WHERE _userId='{user}' AND type='deviceEvent' AND subType='status' "
          f"AND {_TMS} BETWEEN {int(s_ms - 7 * 86400 * 1000)} AND {int(e_ms)} ORDER BY {_TMS}")
    ds = query(qs)
    if not ds.empty:
        cur = None
        for r in ds.drop_duplicates("t_ms").itertuples():
            if r.st == "suspended" and cur is None:
                cur = int(r.t_ms)
            elif r.st == "resumed" and cur is not None:
                iv.append((cur, int(r.t_ms))); cur = None
        if cur is not None:                       # still suspended at window end
            iv.append((cur, int(e_ms)))
    # clip to the window (+6h lead) and drop intervals entirely before it
    lo = int(s_ms - 6 * 3600 * 1000)
    iv = [(max(a, lo), min(b, int(e_ms))) for a, b in iv if b > lo and a < e_ms]
    iv = [(a, b) for a, b in iv if b > a]
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


def _stale_cgm_decisions(user, s_ms, e_ms, glucose, tol_mgdl=2.0):
    """Decisions Loop made on a STALE CGM sample — the reading existed but hadn't reached
    Loop yet, so its anchor (and, for the next ~2 cycles, its momentum/RC windows)
    differ from any replay fed the complete export.

    Detection: `dosingDecision.bgForecast[0]` IS the sample Loop anchored on. Compare it
    with the export's latest sample at/before the decision; a mismatch that instead
    equals an EARLIER sample = Loop ran on stale glucose. Proven on bddp11
    2026-06-15 21:37 (the only such cycle in 3,746): Loop anchored 174 (the 21:32
    sample) while the 21:37 sample (181) already existed; deleting that one sample from
    the replay made the next two cycles match Loop EXACTLY (dose 0.65→0.30=rec,
    forecast Δ 34.7→0.4 mg/dL) — and re-diverge at 21:52, bracketing the late arrival
    at 10–15 min. Loop never anchored on a sample the export lacks; the failure mode is
    purely timing.

    This is a COMPARABILITY exclusion, not a delivery clamp: Loop dosed and the pump
    delivered, so these cycles must NOT go into disruptions.csv (clamping would falsify
    real delivery). Written to stale_cgm.csv for verification tooling to exclude the
    stale cycle and the following two (momentum window 15 min + RC retrospection 30 min
    heal as the sample lands).

    `glucose`: the export's [{startDate, quantity}] list (mg/dL), already built.
    NOTE bgForecast is uploaded in mmol/L; detect by magnitude (<40) as elsewhere."""
    import bisect
    q = (f"SELECT {_TMS} AS t_ms, "
         f"COALESCE(CAST(get_json_object(bgForecast,'$[0].value.$numberDouble') AS DOUBLE), "
         f"         CAST(get_json_object(bgForecast,'$[0].value.$numberInt') AS DOUBLE), "
         f"         CAST(get_json_object(bgForecast,'$[0].value') AS DOUBLE)) AS t0 "
         f"FROM {TBL} WHERE _userId='{user}' AND type='dosingDecision' "
         f"AND CAST(reason AS STRING)='loop' AND bgForecast IS NOT NULL "
         f"AND {_TMS} BETWEEN {int(s_ms)} AND {int(e_ms)} ORDER BY {_TMS}")
    df = query(q)
    gt = [(_iso_to_ms(g["startDate"]), float(g["quantity"])) for g in glucose]
    gt = [(t, v) for t, v in gt if t is not None]
    gt.sort()
    times = [t for t, _ in gt]
    out = []
    for t_ms, t0 in zip(df["t_ms"].tolist(), df["t0"].tolist()):
        v = _fin(t0)
        if v is None:
            continue
        if v < 40:                       # mmol/L upload
            v *= MMOL
        i = bisect.bisect_right(times, int(t_ms)) - 1
        if i < 1:                        # need a latest AND an earlier sample
            continue
        latest_v = gt[i][1]
        if abs(v - latest_v) <= tol_mgdl:
            continue                     # anchored on the sample we'd feed the replay
        # stale only if the anchor matches some EARLIER sample (not an unknown one)
        prior = next((j for j in range(i - 1, max(-1, i - 5), -1)
                      if abs(gt[j][1] - v) <= tol_mgdl), None)
        out.append(dict(t_ms=int(t_ms), loop_anchor=round(v, 2),
                        our_sample=round(latest_v, 2),
                        our_sample_t_ms=gt[i][0],
                        matched_earlier_t_ms=(gt[prior][0] if prior is not None else None)))
    return out


def _decision_times(user, s_ms, e_ms):
    """Every reason='loop' dosingDecision: its instant plus the recorded automatic
    recommendation (bolus U / temp rate+duration), for decision_times.csv.

    Two consumers: (1) `simulate --decision-times-csv` steps the replay at the field's
    REAL cadence instead of CGM samples — kills synthetic steps the field never computed
    (multi-source 1-min streams score every meal moment 2-5x) and steps inside field
    skip-gaps; (2) scorers compare ours-vs-recommendation directly, with an ABSENT
    recommendation scored as ZERO — a loop cycle that ran and stored no recommendation
    recommended nothing (a real algorithmic outcome to MATCH; corroborated by the
    same-instant updateRemoteRecommendation rows recording 0.0). A cycle a user's bolus
    actually BLOCKED reports through the errors channel ("Bolus in progress"
    pumpManagerError) and is excluded by the pump_error clamp, not by rec-absence.
    Cadence choice is dataset-level: field cadence when this file exists, CGM+delay
    otherwise."""
    q = (f"SELECT {_TMS} AS t_ms, "
         f"COALESCE(CAST(get_json_object(recommendedBolus,'$.amount.$numberDouble') AS DOUBLE), "
         f"         CAST(get_json_object(recommendedBolus,'$.amount.$numberInt') AS DOUBLE)) AS rec_bolus, "
         f"COALESCE(CAST(get_json_object(recommendedBasal,'$.rate.$numberDouble') AS DOUBLE), "
         f"         CAST(get_json_object(recommendedBasal,'$.rate.$numberInt') AS DOUBLE)) AS rec_rate, "
         f"CAST(get_json_object(recommendedBasal,'$.duration.$numberInt') AS BIGINT) AS rec_dur_ms, "
         f"CASE WHEN bgForecast IS NULL THEN 1 ELSE 0 END AS no_fc, "
         f"CAST(errors AS STRING) AS errors "
         f"FROM {TBL} WHERE _userId='{user}' AND type='dosingDecision' "
         f"AND CAST(reason AS STRING)='loop' AND {_TMS} BETWEEN {int(s_ms)} AND {int(e_ms)} "
         f"ORDER BY {_TMS}")
    df = query(q)
    out = []
    for r in df.itertuples():
        # no_dose_guard: the loop RAN but bailed before the dosing path — no forecast
        # and no recommendation stored, with an input-staleness error recorded
        # (pumpDataTooOld / glucoseTooOld: Loop refuses to dose on pump data or
        # glucose older than its freshness limit). The guard's trigger state
        # (pump-comms freshness) is exogenous and not reconstructible from the
        # export, but Loop's own error record marks exactly which cycles it fired
        # on; the replay skips those cycles (bddp11 07-04 00:55-01:00: three
        # no-rec cycles, 22-27 min after the pump went silent, read as 1.0-U
        # "mismatches" until this). Distinct from pumpManagerError, where the
        # recommendation IS computed and only delivery fails (pump_error clamp).
        guard = 0
        if r.no_fc and _fin(r.rec_bolus) is None and _fin(r.rec_rate) is None and r.errors:
            try:
                ids = {e.get("id") for e in json.loads(r.errors) if isinstance(e, dict)}
            except (ValueError, TypeError):
                ids = set()
            if ids & {"pumpDataTooOld", "glucoseTooOld"}:
                guard = 1
        out.append(dict(t_ms=int(r.t_ms), rec_bolus=_fin(r.rec_bolus),
                        rec_rate=_fin(r.rec_rate), rec_dur_ms=_fin(r.rec_dur_ms),
                        no_dose_guard=guard))
    return out


def _pump_error_cycles(user, s_ms, e_ms, half_window_ms=90 * 1000):
    """Cycles where Loop DECIDED but the pump could not be reached, so nothing was
    delivered.

    `dosingDecision.errors` records why a cycle failed to enact. Measured on bddp11 over
    2026-06-10..06-23 (3954 'loop' cycles), `pumpManagerError` separates delivery
    perfectly:

        error kind                              cycles w/ rec>0.05    delivered nothing
        (no error)                                     844                 0   (0%)
        pumpManagerError :: Pod not connected           196               196 (100%)
        pumpManagerError :: No pod paired                 4                 4 (100%)
        pumpManagerError :: Bolus in progress             2                 2 (100%)

    i.e. 220 cycles / 72.5 U that Loop asked for and the person never received — an
    out-of-range Omnipod, mostly. There is no bolus record for them in the dose stream OR
    in raw Tidepool, so nothing else in the export reveals them: without this the sim
    happily delivers through a disconnected pump and the dose-match score blames the
    replay for the pod being offline.

    Only `pumpManagerError` is treated as non-delivery. `pumpDataTooOld` also appears in
    `errors` but did not coincide with a suppressed dose in the measured window, so it is
    deliberately NOT clamped — clamping on an unverified signal would silently discard
    real delivery. Widen only with evidence.

    Interval is a TIGHT window centred on the failing decision (±`half_window_ms`), not a
    forward cadence span. Two reasons: the replay's step for a given decision can sit a few
    seconds either side of the field timestamp, so a window starting exactly at it misses
    the step it is meant to clamp; and a full 5-min span reaches the NEXT decision, which
    usually succeeded. Measured on bddp11: forward-span [T, T+5min] covered only 32% of the
    known non-delivered cycles while falsely clamping 15% of delivered ones.

    Only the COMMANDED dose is clamped, not basal — a disconnected pod keeps running its
    last programmed basal autonomously; what fails is Loop's new command.

    Errors are stored as a JSON array whose key order varies between otherwise identical
    entries, so match on a parse, never on the raw string."""
    q = (f"SELECT {_TMS} AS t_ms, CAST(errors AS STRING) AS errors FROM {TBL} "
         f"WHERE _userId='{user}' AND type='dosingDecision' AND CAST(reason AS STRING)='loop' "
         f"AND errors IS NOT NULL "
         f"AND {_TMS} BETWEEN {int(s_ms)} AND {int(e_ms)} ORDER BY {_TMS}")
    df = query(q)
    out = []
    for t_ms, raw in zip(df["t_ms"].tolist(), df["errors"].tolist()):
        try:
            entries = json.loads(raw) if isinstance(raw, str) else []
        except (ValueError, TypeError):
            continue
        if any(isinstance(e, dict) and e.get("id") == "pumpManagerError" for e in entries):
            out.append((int(t_ms) - half_window_ms, int(t_ms) + half_window_ms))
    return out


def _carbs(win, manual_ms):
    """Build the carb entries (food records) for a window. `manual_ms` = sorted list of
    manual-bolus epoch-ms (for the paired-bolus visibility gate). Independent of the giant
    glucose query, so carbs.json can be regenerated on its own."""
    import bisect
    f = query(_dedup([f"{_TMS} AS t_ms", "nutrition",
                      "get_json_object(CAST(payload AS STRING), '$.addedDate') AS added_iso",
                      f"CAST(get_json_object(createdTime,'$.$date.$numberLong') AS BIGINT) AS created_ms"],
                     win, "food"))
    PAIR_WIN = 10 * 60 * 1000   # forward window: the SAVING bolus follows the entry
    POST_BOLUS_DELAY = 10 * 1000  # dosingVisibleDate = saving bolus + 10s (matches NS postBolusVisibilityDelay)
    def paired_bolus(t):
        """The manual bolus that SAVED this entry — the FIRST one AT/AFTER the entry
        timestamp, never one before it.

        A carb typed in Loop's bolus flow is not persisted when typed: the store save
        happens when the user hits deliver, so visibility rides the FOLLOWING bolus.
        Proven on bddp03 2026-06-10: entry stamped 17:51:57, boluses at 17:51:56 (0.55 U)
        and 17:53:21 (7 U meal). Nearest-bolus pairing picked the 0.55 (1.4 s BEFORE the
        entry) → visible 17:52:06 — but the field's own 17:53:20 forecast is carb-free
        (eventual 108 where 70 g adds ~+350), so the store held nothing until the 7 U
        save; carbs appear by 17:58. Forward-only pairing picks the 7 U → visible
        17:53:31, inside the proven bracket. No backward tolerance at all: same-flow
        ordering can put a small bolus a second before the entry stamp, and any backward
        slack re-introduces exactly this bug.

        A carb with NO manual bolus in the forward window was saved standalone at entry
        time → visible then (the back-dated-entry gate below still applies on top). Cost
        of the forward window: a standalone entry followed within 10 min by an UNRELATED
        manual bolus defers visibility to that bolus — rarer and milder than the
        early-visibility bug this replaces (auto-dosing covering a meal the store did
        not yet contain)."""
        i = bisect.bisect_left(manual_ms, t)
        if i < len(manual_ms) and manual_ms[i] - t <= PAIR_WIN:
            return manual_ms[i]
        return None
    BACKDATE_TOL = 5 * 60 * 1000  # ignore <5min upload lag on real-time entries
    carbs = []; cby = {}
    for r in f.itertuples():
        try: nut = json.loads(r.nutrition)
        except Exception: continue
        grams = _fin(_num(((nut.get("carbohydrate") or {}).get("net"))))
        if not grams: continue
        t = int(r.t_ms)
        absorb = _fin(_num(nut.get("estimatedAbsorptionDuration")))  # seconds
        # addedDate = when the deployed Loop's carb store first held this entry (Loop-local),
        # falling back to createdTime (Tidepool server receive). For a carb the user logged
        # LATE and back-stamped to an earlier eat-time, this is hours after t.
        added_ms = _iso_to_ms(getattr(r, "added_iso", None))
        if added_ms is None:
            cm = _fin(getattr(r, "created_ms", None)); added_ms = int(cm) if cm is not None else None
        # dedup: Tidepool food records are re-uploaded many times AND HealthKit-mirrored;
        # collapse to one real entry per (SECOND, grams). CRITICAL: the mirror copies carry
        # NO estimatedAbsorptionDuration (only the native Loop upload does), and they may
        # sort first — so keeping the first-seen record silently drops the real absorption
        # time and the carb defaults to 3h, systematically under-forecasting fast meals.
        # Keep the first-seen entry but MERGE in the absorption from whichever duplicate has
        # it (native Loop record). (Same family as the HealthKit bolus double-count.)
        # Key on the SECOND, not the minute: a native carb and its HealthKit mirror share the
        # EXACT event second (verified across donors), so (second, grams) still collapses them,
        # BUT two GENUINELY-DISTINCT carbs the user logged seconds apart with the same grams
        # (e.g. two 30g entries at 00:09:25 and 00:09:33) are no longer wrongly merged — the
        # minute key dropped one, undercounting COB by a whole meal on those cycles.
        key = (t // 1000, round(grams, 1))
        if key in cby:
            if absorb and "absorptionTime" not in cby[key]:
                cby[key]["absorptionTime"] = absorb   # backfill from the version that has it
            if added_ms is not None and (cby[key]["_added_ms"] is None or added_ms < cby[key]["_added_ms"]):
                cby[key]["_added_ms"] = added_ms      # earliest "Loop learned it" across dup copies
            continue
        # dosingVisibleDate: defer past the paired manual meal bolus so the sim's
        # auto-dosing doesn't cover the carb BEFORE the (passed-through) manual bolus
        # does — avoids double-covering announced meals (crash-low). startDate = meal
        # time (drives absorption); entryDate = meal time (best available).
        # dosingVisibleDate = payload.addedDate — Loop's OWN record of the store-save
        # instant. PROVEN exact on bddp03 06-10: entry stamped 17:51:57, addedDate
        # 17:53:20.561 — 0.4 s after the field's loop cycle whose forecast is carb-free
        # and just before the 7 U meal command; and on 05-21: a standalone 85 g entry
        # saved 4 s after typing, which the field auto-dosed 2 min later (the v7
        # forward-pairing wrongly deferred it 7 min to an unrelated later bolus).
        # No heuristic needed when the save instant is recorded; forward-pairing to the
        # saving bolus remains the FALLBACK for records without addedDate.
        if added_ms is not None:
            vis = added_ms
        else:
            pb = paired_bolus(t)
            vis = (pb + POST_BOLUS_DELAY) if pb is not None else t
        e = {"startDate": _iso(t), "entryDate": _iso(t), "dosingVisibleDate": _iso(vis),
             "grams": round(grams, 1), "_base_vis": vis, "_added_ms": added_ms}
        if absorb: e["absorptionTime"] = absorb
        cby[key] = e            # same dict object is appended below; later backfill reflects here
        carbs.append(e)

    # Causal carb visibility for BACK-DATED entries: a carb the user logged late and
    # back-stamped to an earlier eat-time was NOT in the deployed Loop's carb store until
    # `addedDate`, so the real Loop never dosed for it at the eat-time. Absorption still
    # starts at the eat-time (startDate unchanged — the ICE/physiology is real), but dosing
    # can only see it from when Loop learned it → dosingVisibleDate = max(paired-bolus gate,
    # addedDate). A truly back-dated carb is mostly absorbed by addedDate → contributes ~0 to
    # dosing, exactly as it did for the real Loop. Real-time entries (addedDate ≈ eat-time)
    # are unchanged. Data-level → applies to BOTH arms → identity-preserving.
    for e in carbs:
        base_vis = e.pop("_base_vis"); added_ms = e.pop("_added_ms")
        if added_ms is not None and added_ms > base_vis + BACKDATE_TOL:
            e["dosingVisibleDate"] = _iso(added_ms)
    return carbs


def export_donor(user, start, end, outdir, insulin_type=None):
    os.makedirs(outdir, exist_ok=True)
    s_ms, e_ms = _ms_bounds(start, end)
    # Tidepool soft-deletes: a record the user DELETED stays in the table with
    # _active='false' + archivedTime. Never replay them: bddp03's worst dose residual
    # (2.75 U) was two deleted 40 g carb entries — Loop's own COB read 20 g while the
    # export replayed 100 g; bddp04 carries 7 deleted BOLUSES (phantom insulin).
    # (A deleted entry did live in the store for [addedDate, archivedTime) — minutes,
    # in every observed case; modeling that presence window is not worth the phantom
    # hours it prevents.)
    win = f"_userId='{user}' AND {_TMS} BETWEEN {s_ms} AND {e_ms} AND CAST(_active AS STRING) != 'false'"
    # Insulin type from data (insulinFormulation.brand) unless caller forces one.
    if insulin_type is None:
        insulin_type, brand = _insulin_type_from_data(user, s_ms, e_ms)
        print(f"{user}: insulin brand={brand} → --insulin-type {insulin_type}")

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
        "get_json_object(CAST(origin AS STRING),'$.name') AS orig",
        "COALESCE(CAST(get_json_object(normal,'$.$numberDouble') AS DOUBLE), "
        "CAST(get_json_object(normal,'$.$numberInt') AS DOUBLE)) AS units"], win, "bolus"))
    # Loop mirrors every bolus to HealthKit, so each real bolus has TWO records
    # (origin com.<team>.loopkit.Loop + com.apple.HealthKit) with different `id`s but the
    # same time+amount — id-dedup can't catch them. Collapse by (second, amount).
    # CRITICAL: HealthKit STRIPS the `automated` subType — every mirror comes through as
    # `normal`. So a plain first-seen dedup that keeps a mirror mislabels an auto-bolus as
    # manual (subType `normal` → automatic=False), which then gets passed through as a real
    # manual bolus in the counterfactual. bddp11: 5025 native `automated` + 42 native
    # `normal` (the true manuals) + 8497 HealthKit mirrors (all `normal`); a mirror-keeping
    # dedup yielded ~3244 "manual". PREFER THE NATIVE LOOP RECORD (non-HealthKit origin) so
    # the authoritative subType survives; fall back to the mirror only if no native exists.
    b = b.copy()
    b["_mirror"] = (b["orig"].astype(str) == "com.apple.HealthKit").astype(int)
    doses = []; manual_ms = []; bseen = set()
    for r in b.sort_values(["t_ms", "_mirror"]).itertuples():   # native (_mirror=0) sorts first
        u = _fin(r.units)
        if u is None: continue
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
        "CAST(get_json_object(payload,'$.deliveredUnits.$numberInt') AS DOUBLE)) AS delivered",
        "get_json_object(CAST(origin AS STRING),'$.name') AS orig",
        "CAST(deliveryType AS STRING) AS dtype",
        "CAST(get_json_object(createdTime,'$.$date.$numberLong') AS BIGINT) AS crt_ms"],
        win, "basal", order="_id DESC"))   # keep the LATEST version of each basal id (final completed segment, not the interim dur=0)
    # collect basal segments, then CLIP each end to the next segment's start so
    # overlapping Loop basal records don't double-count delivery.
    #
    # MIRROR PREFERENCE (same disease as the bolus HealthKit dedup): Loop mirrors every
    # basal record to HealthKit under a DIFFERENT id at the same (instant, duration), and
    # the mirror's `rate` is unreliable — observed 0.00 for a real 0.15 U/hr temp, and a
    # delivered-average (0.448) where the native row carries the programmed rate (0.550).
    # bddp11 alone: 5,346 same-(t,dur) groups with CONFLICTING rates, up to 1.25 U/hr
    # apart. id-dedup can't collapse them (distinct ids); an arbitrary pick corrupts the
    # temp rate that feeds IOB, forecasts and ICE. Found from a SINGLE +4 mg/dL forecast
    # cycle (bddp11 2026-07-03 21:20) whose neighbours matched to ±0.4 — the field ran a
    # 0.15 temp our export recorded as 0.0. Keep the NATIVE (non-HealthKit) row.
    bas = bas.copy()
    bas["_mirror"] = (bas["orig"].astype(str) == "com.apple.HealthKit").astype(int)
    bseen = set()
    keep = []
    for r in bas.sort_values(["t_ms", "_mirror", "_id_str"] if "_id_str" in bas.columns else ["t_ms", "_mirror"]).itertuples():
        key = (int(r.t_ms), int(_fin(r.dur_ms) or 0))
        if key in bseen: continue
        bseen.add(key)
        keep.append(r)
    segs = []
    for r in keep:
        st = int(r.t_ms); dur_ms = int(_fin(r.dur_ms) or 0); rate = _fin(r.rate) or 0.0
        delivered = _fin(r.delivered)   # None if not reported
        # Knowledge time for POD-INITIATED suspends: Loop learns of them only when the
        # pod reports back (bddp11 07-04 00:15: suspend created 0.45 s after it ENDED,
        # 90 s after a decision that provably didn't know it — the field's forecast
        # still carried the running temp). Gate ONLY with prompt-upload evidence
        # (created within [end-60s, end+180s]); batch-uploaded records get no
        # receivedDate rather than a false one that would hide doses Loop knew.
        recv = None
        crt = _fin(getattr(r, "crt_ms", None))
        if getattr(r, "dtype", None) == "suspend" and crt is not None:
            en0 = st + dur_ms
            if en0 - 60000 <= int(crt) <= en0 + 180000 and int(crt) > st + 15000:
                recv = int(crt)
        segs.append((st, st + dur_ms, rate, delivered, dur_ms, recv))
    segs.sort(key=lambda s: (s[0], s[1]))   # sort by (start, end); `delivered` may be None
    for i, (st, en, rate, delivered, rec_dur, recv) in enumerate(segs):
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
        extra = {"receivedDate": _iso(recv)} if recv else {}
        doses.append({**extra, "deliveryType": "basal", "startDate": _iso(st), "endDate": _iso(en),
                      "volume": round(vol, 5), "tempRate": round(rate, 5),
                      "insulinType": insulin_type, "automatic": True})
    doses.sort(key=lambda d: d["startDate"])

    # ---- carbs (food: nutrition.carbohydrate.net g, estimatedAbsorptionDuration s) ----
    carbs = _carbs(win, manual_ms)

    # ---- therapy (per-era pumpSettings schedules across the window; expand daily schedules) ----
    therapy = _therapy(user, s_ms, e_ms, insulin_type)

    for name, obj in [("glucose", glucose), ("doses", doses), ("carbs", carbs), ("therapy", therapy)]:
        with open(os.path.join(outdir, f"{name}.json"), "w") as fh:
            json.dump(obj, fh, allow_nan=False)

    # ---- disruptions: pump suspends + loop-offline gaps → outage CSV (clamp + exclude from scoring) ----
    import csv as _csv
    sus = _suspends(user, s_ms, e_ms)
    off = _loop_offline_gaps(user, s_ms, e_ms)
    perr = _pump_error_cycles(user, s_ms, e_ms)
    dts = _decision_times(user, s_ms, e_ms)
    import csv as _csvd
    with open(os.path.join(outdir, "decision_times.csv"), "w", newline="") as fh:
        w = _csvd.writer(fh, lineterminator="\n")
        w.writerow(["t", "rec_bolus", "rec_rate", "rec_dur_min", "no_dose_guard"])
        for r in dts:
            w.writerow([_iso(r["t_ms"]),
                        "" if r["rec_bolus"] is None else r["rec_bolus"],
                        "" if r["rec_rate"] is None else r["rec_rate"],
                        "" if r["rec_dur_ms"] is None else round(r["rec_dur_ms"] / 60000, 1),
                        r.get("no_dose_guard", 0)])

    stale = _stale_cgm_decisions(user, s_ms, e_ms, glucose)
    # Post-date the late samples: a decision replayed at/before the stale decision must
    # not see a sample the real Loop provably lacked. The PROVEN bound from anchors is
    # only "absent at the stale decision" (arrival needs forecast evidence — bddp11's one
    # case arrived 10-15 min late), so post-date minimally: 1 s past the last decision
    # whose anchor proves absence. glucose.json is rewritten with receivedDate on exactly
    # those samples; the sim's visibility gate (EvalGlucoseSample.receivedDate) does the
    # rest. stale_cgm.csv still lists the cycles — the following ~2 cycles can retain a
    # small momentum/RC mismatch until the true (unknown) arrival, so verification should
    # still exclude them.
    # SANITY GUARD on post-dating: the detector was validated on a clean 5-min
    # single-source CGM stream (bddp11: 1 detection / 3,746 decisions, proven by
    # reconstruction). On a 1-min or multi-uploader stream the export's "latest sample
    # at the decision" is routinely one deployed Loop legitimately never anchored on
    # (it never saw that uploader / that cadence), and the detector fires constantly —
    # bddp03: 6,294 "stale" decisions, 12,358 samples post-dated, i.e. a wholesale
    # rewrite of the replay's inputs on a heuristic outside its validated regime.
    # A real transport delay is RARE (bddp09: 2 in two months); a detection rate above
    # ~2% of decisions is a data-quality signature, not 100+ genuine delays. In that
    # regime: keep stale_cgm.csv (it is still a useful data-quality flag), post-date
    # NOTHING, and say so loudly.
    n_dec = max(len(stale), 1)
    try:
        n_dec = max(int(query(
            f"SELECT COUNT(*) n FROM {TBL} WHERE _userId='{user}' AND type='dosingDecision' "
            f"AND CAST(reason AS STRING)='loop' AND {_TMS} BETWEEN {int(s_ms)} AND {int(e_ms)}"
        ).iloc[0]["n"]), 1)
    except Exception:
        pass
    stale_frac = len(stale) / n_dec
    if stale and stale_frac > 0.02:
        print(f"{user}: WARNING stale_cgm={len(stale)} is {100*stale_frac:.1f}% of {n_dec} decisions "
              f"— outside the detector's validated regime (multi-source/1-min CGM?); NOT post-dating")
        stale_postdate = []
    else:
        stale_postdate = stale
    if stale_postdate:
        post = {}   # sample t_ms -> received_ms
        for r in stale_postdate:
            anchor_ms = r["matched_earlier_t_ms"]
            if anchor_ms is None:
                continue    # anchor matches no sample we hold — nothing safe to post-date
            for g in glucose:
                g_ms = _iso_to_ms(g["startDate"])
                if g_ms is not None and anchor_ms < g_ms <= r["t_ms"]:
                    post[g_ms] = max(post.get(g_ms, 0), r["t_ms"] + 1000)
        if post:
            for g in glucose:
                g_ms = _iso_to_ms(g["startDate"])
                if g_ms in post:
                    g["receivedDate"] = _iso(post[g_ms])
            with open(os.path.join(outdir, "glucose.json"), "w") as fh:
                json.dump(glucose, fh, allow_nan=False)
            print(f"{user}: post-dated {len(post)} late CGM sample(s) past the stale decision(s)")
    # stale-CGM decisions: comparability exclusions, NOT delivery clamps — own CSV.
    stale_path = os.path.join(outdir, "stale_cgm.csv")
    import csv as _csv0
    with open(stale_path, "w", newline="") as fh:
        w = _csv0.writer(fh)
        w.writerow(["decision", "loop_anchor_mgdl", "our_sample_mgdl", "our_sample_time", "anchor_matches_sample_time"])
        for r in stale:
            w.writerow([_iso(r["t_ms"]), r["loop_anchor"], r["our_sample"], _iso(r["our_sample_t_ms"]),
                        _iso(r["matched_earlier_t_ms"]) if r["matched_earlier_t_ms"] else "UNKNOWN_SAMPLE"])
    # merge all disruption intervals (suspends + offline gaps + pump errors), tagging source
    tagged = [(s, e, "suspend", "tidepool/suspend_dose") for s, e in sus] \
           + [(s, e, "loop_offline", "tidepool/decision_gap") for s, e in off] \
           + [(s, e, "pump_error", "tidepool/dosing_decision_errors") for s, e in perr]
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
    perr_h = sum((e - s) for s, e in perr) / 3600000.0

    _write_manifest(outdir, user, start, end,
                    counts=dict(glucose=len(glucose), doses=len(doses), carbs=len(carbs),
                                suspends=len(sus), offline_gaps=len(off),
                                pump_errors=len(perr), stale_cgm=len(stale)))

    print(f"{user}: glucose={len(glucose)} doses={len(doses)} carbs={len(carbs)} "
          f"therapy(basal={len(therapy['basal'])},isf={len(therapy['sensitivity'])}) "
          f"suspends={len(sus)}({sus_h:.1f}h) offline_gaps={len(off)}({off_h:.1f}h) "
          f"pump_errors={len(perr)}({perr_h:.1f}h) stale_cgm={len(stale)} → {outdir}")
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
