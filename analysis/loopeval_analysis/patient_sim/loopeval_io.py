"""LoopEval integration: export a virtual person's data dir, serve the external-plant protocol, run.

    python -m loopeval_analysis.patient_sim.loopeval_io run --seed 7 --days 14 --out runs/.../v00007
    python -m loopeval_analysis.patient_sim.loopeval_io serve <person-dir>      (launched by simulate)

`simulate` takes its sample and decision times from the field glucose file, so the export holds
(a) the burn-in history the world produced under its internal drive — glucose, doses, carb entries —
and (b) the sensor's reporting grid for the rest of the window, with placeholder values the
candidate arm never reads (the plant supplies every candidate sample after burn-in). The baseline
arm replays the placeholders and is meaningless: read only the candidate arm.

The plant re-simulates the burn-in from the same (person, seed), so its state at the first request
equals what was exported; from then on LoopEval's doses drive it, and its person's carb entries and
bolus requests go back to LoopEval (--plant-behavior).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .world import EPOCH, DAY, World, minute_of, ts

DEFAULT_BIN = os.environ.get("LOOPEVAL_BIN", str(Path.home() / "dev/LoopEval/.build/release/loop-eval"))
# The controller the donors actually ran: deployed Loop-main ("class 1", docs/loop-algo-classes.md). The
# binary's default is the LoopAlgorithm package ("class 2"), whose gradual-transitions gate suppresses
# momentum and RC on any >40 mg/dL CGM step and under-doses fast unannounced rises (LESSONS 17).
CONTROLLER_FLAGS = {
    "loop-main": ["--no-mid-absorption-isf", "--no-gradual-transitions-gate", "--legacy-rc-decay"],
    "loopalgorithm": [],
}
WARMUP_H = 10.0         # LoopEval's eval warm-up (= insulinLookbackHours by default)
BURN_H = 6.0            # LoopEval's default counterfactual burn-in; the first plant request is at ~16 h
EXPORT_MARGIN_MIN = 120


def _override_windows(world: World) -> list:
    """The person's planned Temporary Overrides in the export's therapy-timeline form. LoopEval applies each one
    only from its start (InputWindowBuilder's causal gate), so a planned future override never leaks backward."""
    out = []
    ws = sorted(world.beh.overrides, key=lambda w: w["start"])
    for i, w in enumerate(ws):
        # a new override REPLACES the running one, as in Loop: clip each window at the next one's start (the engine's
        # active() otherwise keeps the earlier-starting window until it ends)
        if i + 1 < len(ws) and ws[i + 1]["start"] < w["end"]:
            w = dict(w, end=ws[i + 1]["start"])
        if w["end"] <= 0 or w["end"] <= w["start"]: continue
        d = dict(start=ts(max(0.0, w["start"])), end=ts(w["end"]), indefinite=False)
        if abs(w["factor"] - 1.0) > 1e-6: d["factor"] = float(w["factor"])
        if "lo" in w: d.update(targetLo=float(w["lo"]), targetHi=float(w["hi"]))
        out.append(d)
    return out


def export(world: World, out: Path, days: int, burn_end: float):
    """Write the data dir. `world` must have been run internally through `burn_end` minutes."""
    out.mkdir(parents=True, exist_ok=True)
    P = world.person
    st = P.settings
    end = days * DAY
    # glucose: real burn-in readings, then the reporting grid with placeholders
    g = []
    last = 110.0
    for k in sorted(world.readings):
        if k >= burn_end: break
        v = world.readings[k]
        if v is not None:
            g.append(dict(startDate=ts(k), quantity=float(v))); last = v
    phase = (max(world.readings) if world.readings else 0) % world.sensor.f.cadence
    k = burn_end - (burn_end % world.sensor.f.cadence) + phase
    while k < end:
        if k >= burn_end: g.append(dict(startDate=ts(k), quantity=float(last)))
        k += world.sensor.f.cadence
    json.dump(g, open(out / "glucose.json", "w"))
    itype = P.controller_insulin()
    doses = []
    for (typ, s, e, units, auto) in world.int_doses:
        if s >= burn_end: continue
        if typ == "basal":
            doses.append(dict(basalType="scheduled", deliveryType="basal", startDate=ts(s), endDate=ts(e),
                              volume=round(units, 5), tempRate=round(units * 60 / (e - s), 4),
                              insulinType=itype, automatic=True))
        else:
            doses.append(dict(deliveryType="bolus", startDate=ts(s), endDate=ts(s), volume=round(units, 2),
                              insulinType=itype, automatic=bool(auto)))
    json.dump(sorted(doses, key=lambda d: d["startDate"]), open(out / "doses.json", "w"))
    carbs = [dict(startDate=ts(t), entryDate=ts(t), dosingVisibleDate=ts(t), grams=float(gr), absorptionTime=float(a))
             for (t, gr, a) in world.entries if t < burn_end]
    json.dump(carbs, open(out / "carbs.json", "w"))
    seg = lambda v: [dict(startDate=ts(0), endDate=ts(end), value=round(float(v), 3))]
    eras = world.setting_eras + [(end, None)]

    prof = st.get("basal_profile") or [1.0] * 24

    def seg_eras(key: str, v: float) -> list:      # the schedule through the person's settings edits (LESSONS 41)
        out_ = []
        for (a, mult), (b, _) in zip(eras[:-1], eras[1:]):
            if b <= a: continue
            if key != "basal":
                out_.append(dict(startDate=ts(a), endDate=ts(b), value=round(float(v) * mult[key], 3)))
                continue
            # basal: the donor's hourly profile (LESSONS 48), hour by hour through the era
            h0 = a
            while h0 < b:
                h1 = min(b, (math.floor(h0 / 60.0) + 1) * 60.0)
                out_.append(dict(startDate=ts(h0), endDate=ts(h1),
                                 value=round(float(v) * mult[key] * prof[int((h0 % DAY) // 60) % 24], 3)))
                h0 = h1
        return out_
    tgt = [dict(startDate=ts(0), endDate=ts(end), lowerBound=st["target"] - 5, upperBound=st["target"] + 5)]
    th = dict(basal=seg_eras("basal", st["basal_uh"]), sensitivity=seg_eras("isf", st["isf"]),
              carbRatio=seg_eras("cr", st["cr"]), target=tgt,
              rawBasal=seg_eras("basal", st["basal_uh"]), rawSensitivity=seg_eras("isf", st["isf"]),
              rawCarbRatio=seg_eras("cr", st["cr"]), rawTarget=tgt,
              overrideWindows=_override_windows(world), scheduleShifts=[], suspendThreshold=st["suspend"], maxBolus=st["max_bolus"],
              maxBasalRate=st["max_basal"], maxBolusTimeline=seg(st["max_bolus"]),
              maxBasalRateTimeline=seg(st["max_basal"]), suspendThresholdTimeline=seg(st["suspend"]),
              insulinType=itype)
    json.dump(th, open(out / "therapy.json", "w"))
    # Loop-not-acting windows (LESSONS 60): LoopEval auto-detects disruptions.csv and delivers what the pump would —
    # the scheduled basal while offline, the last command through a pump error — with its own IOB following
    rows = [(s0, e0, r) for (s0, e0, r) in getattr(world, "outages", []) if s0 >= burn_end]
    with open(out / "disruptions.csv", "w") as fh:
        fh.write("start,end,reason,source,notes\n")
        for s0, e0, r in rows:
            fh.write(f"{ts(s0)},{ts(e0)},{r},additive/plan,\n")
    json.dump(dict(data_version=32, source="additive patient_sim", person=P.name, template=P.template,
                   seed=P.seed, days=days, burn_end_min=burn_end), open(out / "_export_manifest.json", "w"))
    flags = ["--temp-basal-strategy"] if P.strategy == "temp" else []
    json.dump(dict(required_flags=flags, notes="synthetic person; baseline arm is placeholder"),
              open(out / "replay_config.json", "w"))


# ------------------------------------------------------------------------------------------ plant
def serve(person_dir: Path):
    """Protocol v2 server on stdin/stdout. Writes truth.pkl to person_dir at EOF."""
    meta = json.load(open(person_dir / "meta.json"))
    person = pickle.load(open(person_dir / "person.pkl", "rb"))
    world = World(person, meta["days"], enable=meta.get("enable"))
    started = False
    out = sys.stdout
    for line in sys.stdin:
        req = json.loads(line)
        t0, t1 = minute_of(req["t0"]), minute_of(req["t1"])
        if not started:
            if t0 > meta["burn_end"]:
                raise SystemExit(f"plant: first request at minute {t0:.0f} is past the exported history ({meta['burn_end']:.0f})")
            world.run_internal(t0)
            started = True
        doses = [(d["type"], minute_of(d["start"]), minute_of(d["end"]), float(d["volume"])) for d in req.get("doses", [])]
        samples = [minute_of(s) for s in req.get("samples", [])]
        rep = world.advance(t0, t1, doses, samples, req.get("state") or {})
        out.write(json.dumps(rep) + "\n"); out.flush()
    save_truth(world, person_dir / "truth.pkl")


def save_truth(world: World, path: Path):
    tr = pd.DataFrame(world.truth, columns=["m", "bg", "ra", "egp", "si", "delivered", "absorbed"])
    cgm = pd.Series({k: (np.nan if v is None else v) for k, v in world.readings.items()}, name="cgm")
    pickle.dump(dict(truth=tr, cgm=cgm, behavior=world.beh.log, entries=world.entries, sent_overrides=world.sent_overrides,
                     bolus_requests=world.bolus_requests, pump=world.pump.log, ex_boost=world.ex_log,
                     illness=world.mods.ill, sensor_log=None, received=world.received,
                     person=world.person.name), open(path, "wb"))


# ------------------------------------------------------------------------------------------ run

RC_MODE_CSV = Path.home() / ".loop-eval/runs/2026-10-15-replay-change/rc/rc_mode.csv"


def _rc_flags(person, enable) -> list[str]:
    """rc_own (experiment, LESSONS 152): the controller runs the RC mode the person's template donor deployed —
    integral RC with the deployed clamp for donors called "ircc" in rc_mode.csv (DTR forecast match per day,
    2026-10-15; "mixed" stays standard). Without it every person ran standard RC."""
    if not (enable or {}).get("rc_own"): return []
    try:
        import csv
        calls = {r["alias"]: r["call"] for r in csv.DictReader(open(RC_MODE_CSV))}
    except OSError:
        return []
    return ["--candidate-integral-rc", "--candidate-integral-rc-clamp"] if calls.get(person.template) == "ircc" else []

def run(person, days: int, out: Path, bin_path: str = DEFAULT_BIN, enable: dict | None = None,
        extra_flags: list[str] | None = None, python: str = sys.executable, controller: str = "loop-main") -> dict:
    out.mkdir(parents=True, exist_ok=True)
    pickle.dump(person, open(out / "person.pkl", "wb"))
    burn_end = 30 * 60.0          # generous: the first request depends on the data (observed 16-22 h)
    json.dump(dict(days=days, enable=enable or {}, burn_end=burn_end, controller=controller),
              open(out / "meta.json", "w"))
    w = World(person, days, enable=enable)
    w.run_internal(burn_end)
    export(w, out / "data", days, burn_end)
    pkg_root = Path(__file__).resolve().parents[2]
    plant = f"cd {pkg_root} && {python} -m loopeval_analysis.patient_sim.loopeval_io serve {out}"
    flags = json.load(open(out / "data" / "replay_config.json"))["required_flags"]
    cmd = [bin_path, "simulate", "--data-dir", str(out / "data"),
           "--start", ts(0), "--end", ts(days * DAY),
           "--candidate-counterfactual", "--external-plant", plant, "--plant-behavior",
           "--cf-gap-reanchor-min", "0",
           # Loop issues no new dose once its latest glucose is > 15 min old (inputDataRecencyInterval); donors skip
           # 0.9% of decision cycles this way (median; mean 3.3%) — without the guard LoopEval doses on stale CGM
           # through every simulated sensor gap (LESSONS 61)
           "--cgm-stale-guard-min", "15",
           "--trace-out", str(out / "trace.json")] + flags \
        + CONTROLLER_FLAGS[controller] + _rc_flags(person, enable) + (extra_flags or [])
    t = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    (out / "simulate.log").write_text(" ".join(cmd) + "\n\n" + r.stderr[-20000:])
    if r.returncode != 0:
        raise RuntimeError(f"simulate failed ({r.returncode}): {r.stderr[-1500:]}")
    return dict(seconds=time.time() - t, out=str(out))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve"); s.add_argument("dir")
    r = sub.add_parser("run")
    r.add_argument("--seed", type=int, required=True); r.add_argument("--days", type=int, default=14)
    r.add_argument("--alias"); r.add_argument("--out", required=True)
    r.add_argument("--templates", default=str(Path.home() / ".loop-eval/runs/2026-10-15-additive-templates/templates.csv"))
    r.add_argument("--bin", default=DEFAULT_BIN)
    a = ap.parse_args()
    if a.cmd == "serve":
        serve(Path(a.dir)); return
    from .person import sample_person
    T = pd.read_csv(a.templates)
    P = sample_person(T, a.seed, alias=a.alias)
    res = run(P, a.days, Path(a.out), a.bin)
    print(json.dumps(res))


if __name__ == "__main__":
    main()
