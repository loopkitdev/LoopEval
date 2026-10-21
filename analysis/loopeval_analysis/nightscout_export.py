"""Nightscout (Loop uploader) -> the superset per-donor export, in the Tidepool export's shape.

One export serves replay (`simulate --data-dir`), the ICE pipeline and the additive templates. It is written in
two layers so a site's export and its live replay can never drift apart:

1. **The four streams** (glucose / doses / carbs / therapy JSON) come from `loop-eval export`, i.e. the same
   NightscoutEvalDataSource conversion `simulate --nightscout-url` replays.
2. **This module** adds what the Tidepool export carries beyond them:
   - glucose in the Tidepool representation (mg/dL / 18.01559 x 18.0182, what the pilot statistics and the sensor
     fits were measured on);
   - basal records labelled `temp` / `suspend`, and the scheduled basal between temps as records marked
     `inferred: true` (Loop uploads only temps to Nightscout). The fill is scaled by an active override's
     insulin-needs factor, as the pump runs it; it is left out where Loop reported no pod paired and across gaps
     under a minute (an uploaded temp can end a fraction of a second before the next);
   - decision_times.csv, disruptions.csv (outage.py's schema and suspend rule), dose_doubt / stale_cgm (empty),
     carb_revisions.json (empty), _export_manifest.json;
   - the ICE side tables at the ICE root: tz_daily.csv, site_events.csv, loop_iob.parquet, bolus_decisions.parquet.

Inference that remains (reported in the manifest): the schedule fill; manual-bolus recommendations read from the
status record Loop uploads at the bolus; Loop-offline time read from status gaps (Nightscout status uploads are not
backfilled, so it over-reads offline time). Checked against the same user's Tidepool export (additive LESSONS 486).

Usage:
  NS_URL=https://YOUR-NS.example.com python -m loopeval_analysis.nightscout_export pull ALIAS START END
  NS_URL=https://YOUR-NS.example.com python -m loopeval_analysis.nightscout_export export ALIAS START END ICE_ROOT \\
      [--bin .build/release/loop-eval] [--insulin-type rapidActingAdult]
The site URL is read from NS_URL and never written anywhere.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import json
import os
import subprocess
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from .outage import Outage, _decode_sync_identifier, write_outages_csv

DATA_VERSION = 32                       # the Tidepool ETL version whose output this matches
RAW = Path.home() / ".loop-eval"        # raw pull lands in ~/.loop-eval/<alias>/raw
_FIELD = {"devicestatus": "created_at", "treatments": "created_at"}
_BRAND = {"novolog": "rapidActingAdult", "humalog": "rapidActingAdult", "apidra": "rapidActingAdult",
          "fiasp": "fiasp", "lyumjev": "lyumjev", "afrezza": "afrezza"}
TIDEPOOL_MGDL_PER_MMOL = 18.01559       # Tidepool's storage conversion
ETL_MMOL = 18.0182                      # tidepool/etl.MMOL, the ETL's read-back factor


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
    """Raw devicestatus and treatments by UTC day into ~/.loop-eval/<alias>/raw/<stream>/<day>.json.gz, plus every
    profile save (days already pulled are kept). Glucose and the streams come through `loop-eval export`."""
    root = RAW / alias / "raw"; base = base.rstrip("/")

    def day(stream, d):
        out = root / stream / f"{d}.json.gz"
        if out.exists():
            return 0
        a = int(dt.datetime.fromisoformat(d).replace(tzinfo=dt.timezone.utc).timestamp())
        A, B = (dt.datetime.fromtimestamp(x, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z") for x in (a, a + 86400))
        f = _FIELD[stream]
        recs = _get(f"{base}/api/v1/{stream}.json?find[{f}][$gte]={A}&find[{f}][$lt]={B}&count=100000")
        out.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(str(out) + ".tmp", "wt") as fh:
            json.dump(recs, fh)
        os.replace(str(out) + ".tmp", out)
        return len(recs)

    days = [d.date().isoformat() for d in pd.date_range(start, end, freq="D", inclusive="left")]
    for stream in _FIELD:
        with ThreadPoolExecutor(par) as ex:
            print(stream, sum(ex.map(lambda d: day(stream, d), days)), "records", flush=True)
    with gzip.open(root / "profile_all.json.gz", "wt") as fh:
        json.dump(_get(f"{base}/api/v1/profile.json?count=100000"), fh)


def _load(alias: str, stream: str, start: str, end: str) -> list:
    out = []
    for d in pd.date_range(pd.Timestamp(start) - pd.Timedelta(days=2), end, freq="D"):
        f = RAW / alias / "raw" / stream / f"{d.date().isoformat()}.json.gz"
        if f.exists():
            out += json.load(gzip.open(f))
    return out


# ------------------------------------------------------------------------------------------------ helpers
def _ms(x) -> int:
    t = pd.Timestamp(x)
    t = t.tz_convert("UTC") if t.tzinfo else t.tz_localize("UTC")
    return int(t.value // 1_000_000)


def _iso(ms: float) -> str:
    ms = int(round(ms))
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms % 1000:03d}Z"


def _gaps(a: int, b: int, spans: list) -> list:
    """[a, b) minus sorted (s, e) spans."""
    out, cur = [], a
    for s, e in spans:
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


def streams(alias: str, start: str, end: str, out: Path, bin_path: str, base: str, insulin_type: str) -> None:
    """The four streams through `loop-eval export` (the replay conversion). The URL is passed, never logged."""
    r = subprocess.run([bin_path, "export", "--nightscout-url", base, "--start", f"{start}T00:00:00Z",
                        "--end", f"{end}T00:00:00Z", "--out-dir", str(out), "--insulin-type", insulin_type],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("loop-eval export failed: " + r.stderr.replace(base, "<NS_URL>")[-600:])


# ------------------------------------------------------------------------------------------------ export
def export(alias: str, start: str, end: str, ice_root: str, bin_path: str, base: str,
           insulin_type: str | None = None) -> dict:
    s_ms, e_ms = _ms(start), _ms(end)
    root = Path(ice_root).expanduser(); out = root / "full" / alias; out.mkdir(parents=True, exist_ok=True)
    T = _load(alias, "treatments", start, end); D = _load(alias, "devicestatus", start, end)
    inwin = lambda t: s_ms <= t < e_ms                                                      # noqa: E731

    if insulin_type is None:            # the uploader's brand on dose treatments, unless forced
        b = Counter(str(t.get("insulinType", "")).lower() for t in T if t.get("insulinType"))
        insulin_type = _BRAND.get(b.most_common(1)[0][0], "rapidActingAdult") if b else "rapidActingAdult"
    streams(alias, start, end, out, bin_path, base, insulin_type)
    glucose = json.load(open(out / "glucose.json")); doses = json.load(open(out / "doses.json"))
    therapy = json.load(open(out / "therapy.json"))

    # ---- glucose: the Tidepool representation; 1-minute dedup as the ETL does
    seen, g2 = set(), []
    for x in sorted(glucose, key=lambda x: x["startDate"]):
        t = _ms(x["startDate"])
        if not inwin(t) or t // 60000 in seen:
            continue
        seen.add(t // 60000)
        g2.append({"startDate": _iso(t), "quantity": round(float(x["quantity"]) / TIDEPOOL_MGDL_PER_MMOL * ETL_MMOL, 2)})

    # ---- Loop cycles (devicestatus), deduplicated by time
    ds, dseen = [], set()
    for d in sorted((d for d in D if d.get("loop")), key=lambda d: d["created_at"]):
        t = _ms(d["created_at"])
        if t in dseen or not inwin(t):
            continue
        dseen.add(t); ds.append(d)
    ts = np.array([_ms(d["created_at"]) for d in ds])

    # ---- no-pod spans: Loop cycles reporting no pod paired, merged across gaps < 120 min
    nopod = []
    for d in ds:
        t = _ms(d["created_at"]); fr = str(d["loop"].get("failureReason", ""))
        if "No pod paired" in fr or '"configuration"' in fr:
            if nopod and t - nopod[-1][1] < 120 * 60000:
                nopod[-1][1] = t
            else:
                nopod.append([t, t])

    # ---- suspends: Loop's suspend doses, decoded from the syncIdentifier (outage.py's rule)
    sus = []
    for t in T:
        if t.get("eventType") == "Temp Basal" and _decode_sync_identifier(t.get("syncIdentifier", "")).startswith("suspend"):
            a = _ms(t.get("timestamp") or t["created_at"]); sus.append((a, a + float(t.get("duration") or 0) * 60000))
    sus_start = {a for a, _ in sus}

    # ---- doses: Swift's records in the window, basal labelled; the inferred schedule fill
    d2, temps = [], []
    for x in doses:
        a, b = _ms(x["startDate"]), _ms(x["endDate"])
        if b < s_ms or a >= e_ms:
            continue
        if x["deliveryType"] == "basal":
            x = dict(x, basalType="suspend" if any(abs(a - s) < 2000 for s in sus_start) else "temp")
            temps.append((a, b))
        d2.append(x)
    ow = [(_ms(w["start"]), _ms(w["end"]), float(w.get("factor", 1.0))) for w in therapy.get("overrideWindows", [])
          if w.get("factor") not in (None, 1, 1.0)]
    sched = [(_ms(x["startDate"]), _ms(x["endDate"]), float(x["value"])) for x in therapy.get("rawBasal") or therapy["basal"]]
    sched.sort()
    cuts = sorted(temps + [(a, b) for a, b in nopod])
    n_fill = 0
    for a, b in _gaps(s_ms, e_ms, cuts):
        if b - a < 60000:                           # an uploaded temp ending just short of the next: not a gap
            continue
        # split the gap at schedule changes and override edges, each piece at the rate the pump ran
        edges = sorted({a, b} | {p for s_, e_, _ in sched for p in (s_, e_) if a < p < b}
                       | {p for s_, e_, _ in ow for p in (s_, e_) if a < p < b})
        for p, q in zip(edges, edges[1:]):
            m = (p + q) / 2
            r = next((v for s_, e_, v in sched if s_ <= m < e_), None)
            if r is None:
                continue
            f = next((f_ for s_, e_, f_ in ow if s_ <= m < e_), 1.0)
            d2.append({"deliveryType": "basal", "startDate": _iso(p), "endDate": _iso(q),
                       "volume": round(r * f * (q - p) / 3.6e6, 5), "tempRate": round(r * f, 4),
                       "insulinType": insulin_type, "automatic": True, "basalType": "scheduled", "inferred": True})
            n_fill += 1
    d2.sort(key=lambda x: x["startDate"])
    # the Tidepool shape: the schedules as set (Swift's raw*), overrides as windows the replay applies per decision,
    # only those reaching into the window (Swift scans 180 days back for long overrides)
    def merged(segs):
        # contiguous equal-value segments as one, as Tidepool records them (Swift cuts at every profile save, and a
        # cut moves a segment's weight between days for anything that averages by segment start)
        out = []
        for x in segs:
            if out and out[-1]["endDate"] == x["startDate"] and all(out[-1].get(f) == x.get(f) for f in
                                                                     ("value", "lowerBound", "upperBound")):
                out[-1] = dict(out[-1], endDate=x["endDate"])
            else:
                out.append(dict(x))
        return out
    for k in ("basal", "sensitivity", "carbRatio", "target"):
        raw = "raw" + k[0].upper() + k[1:]
        if raw in therapy:
            therapy[raw] = merged(therapy[raw]); therapy[k] = therapy[raw]
    therapy["overrideWindows"] = [w for w in therapy.get("overrideWindows", [])
                                  if _ms(w["end"]) > s_ms and _ms(w["start"]) < e_ms]
    therapy.setdefault("scheduleShifts", [])

    with open(out / "glucose.json", "w") as fh:
        json.dump(g2, fh, allow_nan=False)
    with open(out / "doses.json", "w") as fh:
        json.dump(d2, fh, allow_nan=False)
    with open(out / "therapy.json", "w") as fh:
        json.dump(therapy, fh, allow_nan=False)
    json.dump({"version": 1, "edited": []}, open(out / "carb_revisions.json", "w"))

    # ---- decision_times.csv (one row per Loop cycle)
    with open(out / "decision_times.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["t", "rec_bolus", "rec_rate", "rec_dur_min", "no_dose_guard", "mode", "bolus_in_progress"])
        for d in ds:
            L = d["loop"]; adr = L.get("automaticDoseRecommendation") or {}; ba = adr.get("basalAdjustment") or {}
            fr = str(L.get("failureReason", ""))
            guard = int(L.get("predicted") is None and ("glucose" in fr.lower() or "pumpDataTooOld" in fr))
            mode = "bolus" if "bolusVolume" in adr else ("temp" if adr or L.get("enacted") else "")
            w.writerow([_iso(_ms(d["created_at"])), L.get("recommendedBolus", ""), ba.get("rate", ""),
                        round(ba["duration"] / 60, 2) if "duration" in ba else "", guard, mode,
                        int("Bolus in progress" in fr)])

    # ---- disruptions.csv (outage.py's schema): suspends, Loop offline > 20 min, pump errors +-90 s, manual temps
    U = lambda ms: pd.Timestamp(ms, unit="ms", tz="UTC")                                     # noqa: E731
    dis = [Outage(U(a), U(b), "suspend", "nightscout/suspend_dose") for a, b in sus if b > a and b > s_ms and a < e_ms]
    for a, b in zip(np.r_[s_ms, ts], np.r_[ts, e_ms]):
        if b - a > 20 * 60000:
            dis.append(Outage(U(a), U(b), "loop_offline", "nightscout/devicestatus_gap"))
    for d in ds:
        if "pumpManagerError" in str(d["loop"].get("failureReason", "")):
            t = _ms(d["created_at"]); dis.append(Outage(U(t - 90000), U(t + 90000), "pump_error", "nightscout/failure_reason"))
    for t in T:
        if t.get("eventType") == "Temp Basal" and t.get("automatic") is False:
            a = _ms(t.get("timestamp") or t["created_at"]); b = a + float(t.get("duration") or 0) * 60000
            if b > a and inwin(a):
                dis.append(Outage(U(a), U(b), "manual_temp", "nightscout/manual_temp_basal"))
    write_outages_csv(sorted(dis, key=lambda o: o.start), out / "disruptions.csv")
    with open(out / "dose_doubt.csv", "w", newline="") as fh:
        csv.writer(fh).writerow(["start", "end", "reason", "notes"])
    with open(out / "stale_cgm.csv", "w", newline="") as fh:
        csv.writer(fh).writerow(["decision", "loop_anchor_mgdl", "our_sample_mgdl", "our_sample_time",
                                 "anchor_matches_sample_time"])

    manual = [(_ms(x["startDate"]), float(x["volume"])) for x in d2 if x["deliveryType"] == "bolus" and not x["automatic"]]
    counts = dict(glucose=len(g2), doses=len(d2), schedule_fill_inferred=n_fill, loop_cycles=len(ds),
                  overrides=len(therapy.get("overrideWindows", [])), manual_boluses=len(manual), suspends=len(sus),
                  no_pod_spans=len(nopod))
    json.dump(dict(data_version=DATA_VERSION, source="nightscout", streams="loop-eval export",
                   exported_at=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   window=dict(start=start, end=end), insulin_type=insulin_type, counts=counts,
                   inferred=["basal records with inferred=true (schedule fill)",
                             "bolus_decisions.rec from the status record at the bolus",
                             "loop_offline from devicestatus gaps (status is not backfilled)"]),
              open(out / "_export_manifest.json", "w"), indent=1)

    # ---- side tables at the ICE root (this alias's rows replace any earlier ones)
    def put(name, df):
        f = root / name
        if f.exists():
            old = pd.read_parquet(f) if name.endswith(".parquet") else pd.read_csv(f)
            old = old[old.alias != alias]
            df = pd.concat([old, df], ignore_index=True) if len(old) else df
        df.to_parquet(f, index=False) if name.endswith(".parquet") else df.to_csv(f, index=False)

    off = pd.DataFrame([(_ms(d["created_at"]) // 86400000, d.get("pump", {}).get("secondsFromGMT")) for d in ds],
                       columns=["day", "sec"]).dropna()
    tz = off.groupby(["day", "sec"]).size().reset_index(name="n").sort_values("n").groupby("day").tail(1)
    tz["tz"] = tz.sec.map(lambda s: "UTC" if s == 0 else f"Etc/GMT{'-' if s > 0 else '+'}{abs(int(s)) // 3600}")
    put("tz_daily.csv", tz[["day", "tz", "n"]].assign(alias=alias).sort_values("day"))
    li = pd.DataFrame([(d["loop"]["iob"].get("timestamp") or d["created_at"], d["loop"]["iob"]["iob"])
                       for d in ds if (d["loop"].get("iob") or {}).get("iob") is not None], columns=["t", "iob"])
    li["t"] = pd.to_datetime(li.t, utc=True)
    put("loop_iob.parquet", li.drop_duplicates("t").assign(alias=alias)[["alias", "t", "iob"]])
    # manual boluses with the bolus screen's recommendation: the status record Loop uploads at the bolus (it
    # differs from the bolus where the user changed it); without one, the last cycle within 10 min before
    rb = [d["loop"].get("recommendedBolus") for d in ds]
    req = {_ms(t.get("timestamp") or t["created_at"]): float(t.get("programmed") or t.get("insulin") or 0)
           for t in T if t.get("eventType") == "Correction Bolus" and not t.get("automatic")}
    bd = []
    for tm, u in manual:
        lo, hi = np.searchsorted(ts, tm - 10000), np.searchsorted(ts, tm + 10000)
        at = [rb[j] for j in range(lo, hi) if rb[j] is not None]
        k = np.searchsorted(ts, tm - 10000, side="right") - 1
        rec = (float(at[0]) if at else
               float(rb[k]) if k >= 0 and tm - ts[k] <= 600000 and rb[k] is not None else np.nan)
        prog = next((v for t_, v in req.items() if abs(t_ - tm) < 2000), u)
        bd.append((pd.Timestamp(tm, unit="ms", tz="UTC"), rec, prog))
    put("bolus_decisions.parquet", pd.DataFrame(bd, columns=["t", "rec", "requested"]).assign(alias=alias)
        [["alias", "t", "rec", "requested"]])
    ev = [dict(alias=alias, kind="reservoirChange", t_start=pd.Timestamp(x), t_end=pd.Timestamp(x), n=1)
          for t in T if t.get("eventType") == "Site Change" for x in [t.get("timestamp") or t["created_at"]] if inwin(_ms(x))]
    ev += [dict(alias=alias, kind="no_pod", t_start=U(a), t_end=U(b), n=1) for a, b in nopod]
    put("site_events.csv", pd.DataFrame(ev, columns=["alias", "kind", "t_start", "t_end", "n"]))
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["pull", "export"]); ap.add_argument("alias")
    ap.add_argument("start"); ap.add_argument("end"); ap.add_argument("ice_root", nargs="?")
    ap.add_argument("--bin", default=str(Path(__file__).resolve().parents[2] / ".build/release/loop-eval"))
    ap.add_argument("--insulin-type")
    a = ap.parse_args()
    if a.cmd == "pull":
        pull(a.alias, a.start, a.end, os.environ["NS_URL"])
    else:
        print(json.dumps(export(a.alias, a.start, a.end, a.ice_root, a.bin, os.environ["NS_URL"], a.insulin_type)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
