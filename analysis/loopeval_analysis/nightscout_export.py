"""Nightscout (Loop uploader) -> the per-donor export the ICE pipeline and the additive templates read.

Produces, for one site, the same files the Tidepool ETL (tidepool/etl.export_donor, data_version 32) writes into
``<ice_root>/full/<alias>/`` plus the ICE side tables at ``<ice_root>/`` (tz_daily.csv, site_events.csv,
loop_iob.parquet, bolus_decisions.parquet), so build_steps / label_meals / templates run on it unchanged.

Loop's Nightscout record carries what the Tidepool export is built from:

  glucose       entries (sgv), one per 1-minute bucket
  boluses       treatments 'Correction Bolus' (`insulin` delivered, `automatic`); one record per syncIdentifier
  basal         treatments 'Temp Basal' (`amount` = delivered units, pulse-truncated; `reason: suspend` = suspend).
                Loop uploads only temps: the gaps between them ran the scheduled basal, filled here from the
                schedule as Tidepool records it (scheduled segments), except where no pod was paired
  carbs         treatments 'Carb Correction' (`absorptionTime` min; `userEnteredAt` = when Loop could see it)
  therapy       every profile save (store schedules in the profile's own timezone; loopSettings limits):
                dated eras, expanded to absolute segments
  overrides     devicestatus.override per cycle (what Loop ran), runs of the same preset -> overrideWindows
  decisions     devicestatus.loop per cycle: iob (net of scheduled basal, as dosingDecision.insulinOnBoard),
                recommendedBolus, automaticDoseRecommendation, failureReason
  timezone      devicestatus.pump.secondsFromGMT, modal per UTC day

Differences from the Tidepool export, by construction: no HealthKit mirrors or second apps to remove; manual bolus
recommendations are the last cycle's `recommendedBolus` before the bolus (Nightscout has no normalBolus decision);
no carb revision chains (carb_revisions.json is written empty; no ICE consumer reads it).

Usage:
  NS_URL=https://YOUR-NS.example.com python -m loopeval_analysis.nightscout_export pull  ALIAS START END
  python -m loopeval_analysis.nightscout_export export ALIAS START END ICE_ROOT [--insulin-type rapidActingAdult]
The site URL is read from the NS_URL environment variable and never written anywhere.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import json
import os
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

DATA_VERSION = 32                       # the Tidepool ETL version whose output this matches
RAW = Path.home() / ".loop-eval"        # raw pull lands in ~/.loop-eval/<alias>/raw
_FIELD = {"entries": "date", "devicestatus": "created_at", "treatments": "created_at"}
_BRAND = {"novolog": "rapidActingAdult", "humalog": "rapidActingAdult", "apidra": "rapidActingAdult",
          "fiasp": "fiasp", "lyumjev": "lyumjev", "afrezza": "afrezza"}


# ------------------------------------------------------------------------------------------------ pull
def _get(url: str):
    err = None
    for k in range(5):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.loads(r.read())
        except Exception as e:                                  # noqa: BLE001
            err = e; time.sleep(3 * (k + 1))
    raise RuntimeError(f"fetch failed: {type(err).__name__}")   # never echo the URL


def pull(alias: str, start: str, end: str, base: str, par: int = 4) -> None:
    """Raw records by UTC day into ~/.loop-eval/<alias>/raw/<stream>/<day>.json.gz (days already pulled are kept)."""
    root = RAW / alias / "raw"; base = base.rstrip("/")

    def url(stream, a):
        if stream == "entries":
            return f"{base}/api/v1/entries.json?find[date][$gte]={a * 1000}&find[date][$lt]={(a + 86400) * 1000}&count=100000"
        A, B = (dt.datetime.fromtimestamp(x, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z") for x in (a, a + 86400))
        f = _FIELD[stream]
        return f"{base}/api/v1/{stream}.json?find[{f}][$gte]={A}&find[{f}][$lt]={B}&count=100000"

    def day(stream, d):
        out = root / stream / f"{d}.json.gz"
        if out.exists():
            return 0
        a = int(dt.datetime.fromisoformat(d).replace(tzinfo=dt.timezone.utc).timestamp())
        recs = _get(url(stream, a)); out.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(str(out) + ".tmp", "wt") as fh:
            json.dump(recs, fh)
        os.replace(str(out) + ".tmp", out)
        return len(recs)

    days = [d.date().isoformat() for d in pd.date_range(start, end, freq="D", inclusive="left")]
    for stream in _FIELD:
        with ThreadPoolExecutor(par) as ex:
            print(stream, sum(ex.map(lambda d: day(stream, d), days)), "records", flush=True)
    prof = _get(f"{base}/api/v1/profile.json?count=100000")
    with gzip.open(root / "profile_all.json.gz", "wt") as fh:
        json.dump(prof, fh)
    print("profile", len(prof), "saves", flush=True)


def _load(alias: str, stream: str, start: str, end: str) -> list:
    out = []
    for d in pd.date_range(pd.Timestamp(start) - pd.Timedelta(days=2), end, freq="D"):
        f = RAW / alias / "raw" / stream / f"{d.date().isoformat()}.json.gz"
        if f.exists():
            out += json.load(gzip.open(f))
    return out


# ------------------------------------------------------------------------------------------------ helpers
def _ms(x) -> int:
    return int(pd.Timestamp(x).tz_convert("UTC").value // 1_000_000) if pd.Timestamp(x).tzinfo else \
        int(pd.Timestamp(x).tz_localize("UTC").value // 1_000_000)


def _iso(ms: float) -> str:
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{int(ms) % 1000:03d}Z"


def _tz(name: str) -> dt.tzinfo:
    """Loop writes the schedule timezone as a fixed offset ('ETC/GMT+5'); Etc/GMT+N is UTC-N."""
    import zoneinfo
    n = name.strip()
    if n.upper().startswith("ETC/"):
        n = "Etc/" + n[4:].upper().replace("GMT", "GMT")
    try:
        return zoneinfo.ZoneInfo(n)
    except Exception:                                           # noqa: BLE001
        return dt.timezone.utc


def _intervals_minus(a: float, b: float, cuts: list) -> list:
    """[a, b) minus a sorted list of (s, e) spans."""
    out, cur = [], a
    for s, e in cuts:
        if e <= cur or s >= b:
            continue
        if s > cur:
            out.append((cur, min(s, b)))
        cur = max(cur, e)
        if cur >= b:
            break
    if cur < b:
        out.append((cur, b))
    return out


# ------------------------------------------------------------------------------------------------ therapy
def _eras(profiles: list, s_ms: int, e_ms: int) -> list:
    """Distinct settings eras [(start_ms, profile)] covering the window: the save in force at the start, then each
    save that changed a schedule, the timezone or a limit."""
    def key(p):
        st = p["store"][p.get("defaultProfile", "Default")]; L = p.get("loopSettings", {})
        return json.dumps([[(x["timeAsSeconds"], x["value"]) for x in st[k]] for k in
                           ("basal", "sens", "carbratio", "target_low", "target_high")] +
                          [st.get("timezone"), L.get("maximumBasalRatePerHour"), L.get("maximumBolus"),
                           L.get("minimumBGGuard")])
    ps = sorted((p for p in profiles if p.get("store")), key=lambda p: _ms(p.get("startDate") or p["created_at"]))
    eras, last = [], None
    for p in ps:
        t = _ms(p.get("startDate") or p["created_at"])
        if t > e_ms:
            break
        k = key(p)
        if t <= s_ms:
            eras = [(s_ms, p)]; last = k
        elif k != last:
            eras.append((t, p)); last = k
    if not eras:
        raise ValueError("no profile in force at the window start")
    return eras


def _expand(eras: list, e_ms: int, field: str, field_hi: str | None = None) -> list:
    """Absolute {startDate, endDate, value} (or lower/upperBound) segments from each era's daily schedule in that
    era's own timezone."""
    segs = []
    for i, (t0, p) in enumerate(eras):
        t1 = eras[i + 1][0] if i + 1 < len(eras) else e_ms
        st = p["store"][p.get("defaultProfile", "Default")]; tz = _tz(st.get("timezone", "UTC"))
        sched = st[field]; hi = st[field_hi] if field_hi else None
        day = dt.datetime.fromtimestamp(t0 / 1000, tz).replace(hour=0, minute=0, second=0, microsecond=0)
        while day.timestamp() * 1000 < t1:
            for j, x in enumerate(sched):
                a = (day + dt.timedelta(seconds=x["timeAsSeconds"])).timestamp() * 1000
                nxt = sched[j + 1]["timeAsSeconds"] if j + 1 < len(sched) else 86400
                b = (day + dt.timedelta(seconds=nxt)).timestamp() * 1000
                a, b = max(a, t0), min(b, t1)
                if b <= a:
                    continue
                seg = {"startDate": _iso(a), "endDate": _iso(b)}
                if hi is None:
                    seg["value"] = float(x["value"])
                else:
                    seg["lowerBound"] = float(x["value"]); seg["upperBound"] = float(hi[j]["value"])
                segs.append(seg)
            day = (day + dt.timedelta(days=1, hours=3)).replace(hour=0)   # DST-safe next local midnight
    return segs


def _scheduled_rate(basal_segs: list):
    s = np.array([_ms(x["startDate"]) for x in basal_segs]); r = np.array([x["value"] for x in basal_segs])
    e = np.array([_ms(x["endDate"]) for x in basal_segs])
    return s, e, r


def _timeline(eras: list, e_ms: int, key: str, default: float) -> list:
    out = []
    for i, (t0, p) in enumerate(eras):
        t1 = eras[i + 1][0] if i + 1 < len(eras) else e_ms
        v = p.get("loopSettings", {}).get(key, default)
        if out and out[-1]["value"] == v:
            out[-1]["endDate"] = _iso(t1)
        else:
            out.append({"startDate": _iso(t0), "endDate": _iso(t1), "value": float(v)})
    return out


def _override_windows(T: list, ds: list, s_ms: int, e_ms: int) -> list:
    """Loop's 'Temporary Override' treatments: start, the duration it actually ran (Loop rewrites it when the override
    ends early), insulin-needs factor and its own correction range (none when the preset sets no target; the cycle's
    currentCorrectionRange then follows the schedule and is not the override's). An override active in the Loop cycles
    with no treatment covering it (one still running at the end of the pull) is added from the run of cycles."""
    def win(a, b, f, rng):
        w = {"start": _iso(a), "end": _iso(b), "indefinite": False}
        if f is not None and abs(float(f) - 1) > 1e-9:
            w["factor"] = float(f)
        if rng:
            w["targetLo"] = float(rng[0]); w["targetHi"] = float(rng[1])
        return w
    spans, out, seen = [], [], set()
    for t in sorted((t for t in T if t.get("eventType") == "Temporary Override"), key=lambda t: t.get("timestamp", "")):
        k = t.get("identifier") or t.get("timestamp")
        if k in seen:
            continue
        seen.add(k); a = _ms(t.get("timestamp") or t["created_at"]); b = a + float(t.get("duration") or 0) * 60000
        if b <= s_ms or a >= e_ms or b <= a:
            continue
        spans.append((a, b)); out.append(win(a, b, t.get("insulinNeedsScaleFactor"), t.get("correctionRange")))
    runs, cur = [], None
    for d in ds:
        o = d.get("override") or {}; t = _ms(d["created_at"])
        k = (o.get("name"), o.get("multiplier")) if o.get("active") else None
        if cur and k != cur[0]:
            runs.append(cur + [t]); cur = None
        if k and not cur:
            r_ = o.get("currentCorrectionRange") or {}
            cur = [k, t, (r_.get("minValue"), r_.get("maxValue"))]
    if cur:
        runs.append(cur + [_ms(ds[-1]["created_at"])])
    for (name, f), a, rng, b in runs:
        if any(sa <= a + 600000 and b <= sb + 600000 for sa, sb in spans):
            continue                                             # the treatment already covers it
        out.append(win(a, b, f, None))                           # the range there may be the schedule's: left out
    return sorted(out, key=lambda w: w["start"])


# ------------------------------------------------------------------------------------------------ export
def export(alias: str, start: str, end: str, ice_root: str, insulin_type: str | None = None) -> dict:
    s_ms, e_ms = _ms(start), _ms(end)
    root = Path(ice_root).expanduser(); out = root / "full" / alias; out.mkdir(parents=True, exist_ok=True)
    E = _load(alias, "entries", start, end); T = _load(alias, "treatments", start, end)
    D = _load(alias, "devicestatus", start, end)
    P = json.load(gzip.open(RAW / alias / "raw" / "profile_all.json.gz"))
    inwin = lambda t: s_ms <= t < e_ms                                                      # noqa: E731

    # ---- glucose: one reading per 1-minute bucket
    seen, glucose = set(), []
    for x in sorted((x for x in E if x.get("type") == "sgv" and x.get("sgv")), key=lambda x: x["date"]):
        t = int(round(x["date"]))                     # Nightscout dates carry sub-ms fractions; Tidepool rounds
        if not inwin(t) or t // 60000 in seen:
            continue
        # the value as the Tidepool export carries it: Tidepool stores mg/dL / 18.01559 in mmol/L and the ETL multiplies
        # back by its MMOL (18.0182), so a reading of 177 reads 177.03. Exact against Tidepool (LESSONS 486); kept because
        # the pilot statistics and the sensor fits were measured on it (the integer form moves sigma_meas 15% by ties alone)
        seen.add(t // 60000)
        glucose.append({"startDate": _iso(t), "quantity": round(float(x["sgv"]) / 18.01559 * 18.0182, 2)})

    # ---- devicestatus (Loop cycles), deduplicated by time
    ds, dseen = [], set()
    for d in sorted((d for d in D if d.get("loop")), key=lambda d: d["created_at"]):
        t = _ms(d["created_at"])
        if t in dseen:
            continue
        dseen.add(t); ds.append(d)
    ds_in = [d for d in ds if inwin(_ms(d["created_at"]))]

    # ---- insulin type: the uploader's brand on dose treatments, unless forced
    if insulin_type is None:
        b = Counter(str(t.get("insulinType", "")).lower() for t in T if t.get("insulinType"))
        insulin_type = _BRAND.get(b.most_common(1)[0][0], "rapidActingAdult") if b else "rapidActingAdult"

    # ---- therapy
    eras = _eras(P, s_ms, e_ms)
    basal = _expand(eras, e_ms, "basal"); sens = _expand(eras, e_ms, "sens")
    cr = _expand(eras, e_ms, "carbratio"); tgt = _expand(eras, e_ms, "target_low", "target_high")
    mb = _timeline(eras, e_ms, "maximumBolus", 12.0); mr = _timeline(eras, e_ms, "maximumBasalRatePerHour", 8.0)
    sus = _timeline(eras, e_ms, "minimumBGGuard", 70.0)
    therapy = dict(basal=basal, sensitivity=sens, carbRatio=cr, target=tgt, rawBasal=basal, rawSensitivity=sens,
                   rawCarbRatio=cr, rawTarget=tgt, overrideWindows=_override_windows(T, ds_in, s_ms, e_ms), scheduleShifts=[],
                   suspendThreshold=sus[-1]["value"], maxBolus=mb[-1]["value"], maxBasalRate=mr[-1]["value"],
                   maxBolusTimeline=mb, maxBasalRateTimeline=mr, suspendThresholdTimeline=sus,
                   insulinType=insulin_type)

    # ---- no-pod spans (Loop cycles reporting no pod paired): nothing delivered there
    nopod = []                                                    # runs merged across gaps < 120 min
    for d in ds_in:
        t = _ms(d["created_at"]); fr = str(d["loop"].get("failureReason", ""))
        if "No pod paired" in fr or '"configuration"' in fr:
            if nopod and t - nopod[-1][1] < 120 * 60000:
                nopod[-1][1] = t
            else:
                nopod.append([t, t])
    nopod = [(a, b) for a, b in nopod]

    # ---- doses
    doses, manual = [], []
    bseen = set()
    for t in T:
        if t.get("eventType") != "Correction Bolus" and not (t.get("insulin") and t.get("eventType") in
                                                            ("Meal Bolus", "Snack Bolus", "Bolus")):
            continue
        u = t.get("insulin")
        k = t.get("syncIdentifier") or (t.get("timestamp"), u)
        if u is None or k in bseen:
            continue
        bseen.add(k); tm = _ms(t.get("timestamp") or t["created_at"])
        if not inwin(tm) or float(u) <= 0:
            continue
        auto = bool(t.get("automatic", False))
        doses.append({"deliveryType": "bolus", "startDate": _iso(tm), "endDate": _iso(tm), "volume": round(float(u), 4),
                      "insulinType": insulin_type, "automatic": auto})
        if not auto:
            manual.append((tm, float(u), float(t.get("programmed") or u)))
    temps, tseen = [], set()
    for t in T:
        if t.get("eventType") != "Temp Basal":
            continue
        k = t.get("syncIdentifier") or t.get("timestamp")
        if k in tseen:
            continue
        tseen.add(k); a = _ms(t.get("timestamp") or t["created_at"]); dur = float(t.get("duration") or 0) * 60000
        rate = float(t.get("absolute", t.get("rate")) or 0)
        temps.append(dict(a=a, b=a + dur, rate=rate, amount=t.get("amount"), suspend=t.get("reason") == "suspend",
                          auto=bool(t.get("automatic", True))))
    temps.sort(key=lambda x: x["a"])
    for i, x in enumerate(temps):                                    # clip to the next record's start
        if i + 1 < len(temps):
            nxt = temps[i + 1]["a"]
            # Loop's temps run back to back; the uploaded duration can end a fraction of a second short of the next
            # temp, which a schedule fill would turn into a scheduled sliver inside a zero temp (zero-delivery share
            # 4 points under the Tidepool export's; LESSONS 486): close gaps under a minute
            x["b"] = nxt if 0 <= nxt - x["b"] < 60000 else min(x["b"], nxt)
    temps = [x for x in temps if x["b"] > x["a"] and x["b"] > s_ms and x["a"] < e_ms]
    manual_temp = []
    for x in temps:
        a, b = max(x["a"], s_ms), min(x["b"], e_ms)
        full = x["b"] - x["a"]
        vol = (float(x["amount"]) * (b - a) / full if x["amount"] is not None and full > 0
               else x["rate"] * (b - a) / 3.6e6)
        rec = {"deliveryType": "basal", "startDate": _iso(a), "endDate": _iso(b), "volume": round(vol, 5),
               "tempRate": x["rate"], "insulinType": insulin_type, "automatic": True,
               "basalType": "suspend" if x["suspend"] else "temp"}
        if x["suspend"]:
            rec["volume"] = 0.0
        doses.append(rec)
        if not x["auto"] and not x["suspend"]:
            manual_temp.append((a, b))
    # scheduled basal between temps (Loop uploads none; the pod ran its schedule), except with no pod paired
    ss, se, sr = _scheduled_rate(basal)
    cuts = sorted([(x["a"], x["b"]) for x in temps] + [tuple(n) for n in nopod])
    for a, b in _intervals_minus(s_ms, e_ms, cuts):
        i = max(np.searchsorted(ss, a, side="right") - 1, 0)
        while a < b and i < len(ss):
            c = min(b, se[i])
            if c > a:
                doses.append({"deliveryType": "basal", "startDate": _iso(a), "endDate": _iso(c),
                              "volume": round(sr[i] * (c - a) / 3.6e6, 5), "tempRate": float(sr[i]),
                              "insulinType": insulin_type, "automatic": True, "basalType": "scheduled"})
            a = c; i += 1
    doses.sort(key=lambda x: x["startDate"])

    # ---- carbs
    carbs, cseen = [], set()
    for t in T:
        if t.get("eventType") not in ("Carb Correction", "Meal Bolus", "Snack Bolus") or not t.get("carbs"):
            continue
        k = t.get("syncIdentifier") or (t.get("timestamp"), t["carbs"])
        if k in cseen:
            continue
        cseen.add(k); tm = _ms(t.get("timestamp") or t["created_at"])
        if not inwin(tm):
            continue
        vis = max(tm, _ms(t.get("userEnteredAt") or t["created_at"]))
        c = {"startDate": _iso(tm), "entryDate": _iso(tm), "dosingVisibleDate": _iso(vis),
             "grams": round(float(t["carbs"]), 1)}
        if t.get("absorptionTime"):
            c["absorptionTime"] = float(t["absorptionTime"]) * 60
        carbs.append(c)
    carbs.sort(key=lambda x: x["startDate"])

    # ---- write the four streams + empty revisions
    for name, obj in (("glucose", glucose), ("doses", doses), ("carbs", carbs), ("therapy", therapy)):
        with open(out / f"{name}.json", "w") as fh:
            json.dump(obj, fh, allow_nan=False)
    json.dump({"version": 1, "edited": []}, open(out / "carb_revisions.json", "w"))

    # ---- decision_times.csv (one row per Loop cycle)
    with open(out / "decision_times.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["t", "rec_bolus", "rec_rate", "rec_dur_min", "no_dose_guard", "mode", "bolus_in_progress"])
        for d in ds_in:
            L = d["loop"]; adr = L.get("automaticDoseRecommendation") or {}; ba = adr.get("basalAdjustment") or {}
            fr = str(L.get("failureReason", ""))
            guard = int(L.get("predicted") is None and ("glucose" in fr.lower() or "pumpDataTooOld" in fr))
            mode = "bolus" if "bolusVolume" in adr else ("temp" if adr or L.get("enacted") else "")
            w.writerow([_iso(_ms(d["created_at"])), L.get("recommendedBolus", ""), ba.get("rate", ""),
                        round(ba["duration"] / 60, 2) if "duration" in ba else "", guard, mode,
                        int("Bolus in progress" in fr)])

    # ---- disruptions.csv: suspends, Loop offline > 20 min, pump errors +-90 s, manual temps
    dis = [(x["a"], x["b"], "suspend", "nightscout/temp_basal_suspend") for x in temps if x["suspend"]]
    ts = [_ms(d["created_at"]) for d in ds_in]
    for a, b in zip([s_ms] + ts, ts + [e_ms]):
        if b - a > 20 * 60000:
            dis.append((a, b, "loop_offline", "nightscout/devicestatus_gap"))
    for d in ds_in:
        if "pumpManagerError" in str(d["loop"].get("failureReason", "")):
            t = _ms(d["created_at"]); dis.append((t - 90000, t + 90000, "pump_error", "nightscout/failure_reason"))
    dis += [(a, b, "manual_temp", "nightscout/manual_temp_basal") for a, b in manual_temp]
    dis.sort()
    with open(out / "disruptions.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["start", "end", "reason", "source", "notes"])
        for a, b, r, s in dis:
            w.writerow([_iso(a), _iso(b), r, s, ""])
    with open(out / "dose_doubt.csv", "w", newline="") as fh:
        csv.writer(fh).writerow(["start", "end", "reason", "notes"])
    with open(out / "stale_cgm.csv", "w", newline="") as fh:
        csv.writer(fh).writerow(["decision", "loop_anchor_mgdl", "our_sample_mgdl", "our_sample_time",
                                 "anchor_matches_sample_time"])

    counts = dict(glucose=len(glucose), doses=len(doses), carbs=len(carbs), loop_cycles=len(ds_in),
                  eras=len(eras), overrides=len(therapy["overrideWindows"]), manual_boluses=len(manual),
                  suspends=sum(x["suspend"] for x in temps), no_pod_spans=len(nopod), manual_temps=len(manual_temp))
    json.dump(dict(data_version=DATA_VERSION, source="nightscout", exported_at=dt.datetime.now(dt.timezone.utc)
                   .strftime("%Y-%m-%dT%H:%M:%SZ"), window=dict(start=start, end=end), insulin_type=insulin_type,
                   counts=counts), open(out / "_export_manifest.json", "w"), indent=1)

    # ---- side tables at the ICE root (this alias's rows replace any earlier ones)
    def put(name, df):
        f = root / name
        if f.exists():
            old = pd.read_parquet(f) if name.endswith(".parquet") else pd.read_csv(f)
            df = pd.concat([old[old.alias != alias], df], ignore_index=True)
        df.to_parquet(f, index=False) if name.endswith(".parquet") else df.to_csv(f, index=False)

    off = pd.DataFrame([(_ms(d["created_at"]) // 86400000, d.get("pump", {}).get("secondsFromGMT")) for d in ds_in],
                       columns=["day", "sec"]).dropna()
    tz = (off.groupby(["day", "sec"]).size().reset_index(name="n").sort_values("n").groupby("day").tail(1))
    tz["tz"] = tz.sec.map(lambda s: "UTC" if s == 0 else f"Etc/GMT{'-' if s > 0 else '+'}{abs(int(s)) // 3600}")
    put("tz_daily.csv", tz[["day", "tz", "n"]].assign(alias=alias).sort_values("day"))
    li = pd.DataFrame([(pd.Timestamp(d["loop"]["iob"].get("timestamp") or d["created_at"]), d["loop"]["iob"]["iob"])
                       for d in ds_in if (d["loop"].get("iob") or {}).get("iob") is not None], columns=["t", "iob"])
    li["t"] = pd.to_datetime(li.t, utc=True)
    put("loop_iob.parquet", li.drop_duplicates("t").assign(alias=alias)[["alias", "t", "iob"]])
    # manual boluses with the bolus screen's recommendation: Loop uploads a status record at the moment of a
    # manual bolus whose recommendedBolus is the calculator's (it differs from the bolus where the user changed
    # it); without one, the last cycle before the bolus (within 10 min)
    dt_ms = np.array(ts); rb = [d["loop"].get("recommendedBolus") for d in ds_in]
    bd = []
    for tm, u, prog in manual:
        lo, hi = np.searchsorted(dt_ms, tm - 10000), np.searchsorted(dt_ms, tm + 10000)
        at = [rb[j] for j in range(lo, hi) if rb[j] is not None]
        k = np.searchsorted(dt_ms, tm - 10000, side="right") - 1
        rec = (float(at[0]) if at else
               float(rb[k]) if k >= 0 and tm - dt_ms[k] <= 600000 and rb[k] is not None else np.nan)
        bd.append((pd.Timestamp(tm, unit="ms", tz="UTC"), rec, prog))
    put("bolus_decisions.parquet", pd.DataFrame(bd, columns=["t", "rec", "requested"]).assign(alias=alias)
        [["alias", "t", "rec", "requested"]])
    ev = [("reservoirChange", t.get("timestamp") or t["created_at"]) for t in T if t.get("eventType") == "Site Change"]
    ev = [(k, pd.Timestamp(x)) for k, x in ev if inwin(_ms(x))]
    ev = pd.DataFrame([dict(alias=alias, kind=k, t_start=x, t_end=x, n=1) for k, x in ev] +
                      [dict(alias=alias, kind="no_pod", t_start=pd.Timestamp(a, unit="ms", tz="UTC"),
                            t_end=pd.Timestamp(b, unit="ms", tz="UTC"), n=1) for a, b in nopod],
                      columns=["alias", "kind", "t_start", "t_end", "n"])
    put("site_events.csv", ev)
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["pull", "export"]); ap.add_argument("alias")
    ap.add_argument("start"); ap.add_argument("end"); ap.add_argument("ice_root", nargs="?")
    ap.add_argument("--insulin-type")
    a = ap.parse_args()
    if a.cmd == "pull":
        pull(a.alias, a.start, a.end, os.environ["NS_URL"])
    else:
        print(json.dumps(export(a.alias, a.start, a.end, a.ice_root, a.insulin_type)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
