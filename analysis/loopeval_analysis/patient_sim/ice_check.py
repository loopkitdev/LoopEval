"""Run the ice role's own ICE extraction and meal labeler on a simulated person — like for like.

The simulator's carb sensitivity is calibrated to an ice measurement (pulse g-eq per entered gram, 1.30)
and its eating to ice pulse counts; the only honest check is to put simulated output through the SAME
code: ice_gen.extract (ICE on the person's CGM and delivered insulin) and ice_gen.meals.label (pulses,
entries, boluses, corrections, rescues). Imported read-only from the ice worktree (branch `ice`).

    python -m loopeval_analysis.patient_sim.ice_check <run-dir> [<run-dir> ...]
"""
from __future__ import annotations

import json
import pickle
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from .world import EPOCH, ts

ICE_ANALYSIS = Path.home() / "dev/loopeval-ice/analysis"


ICE_SCRIPT = r"""
import sys, json, pandas as pd, numpy as np
sys.path.insert(0, sys.argv[1])
from loopeval_analysis.ice_gen import extract as X, meals as M
d, burn_ms = sys.argv[2], int(sys.argv[3])
steps, person = X.extract(d)
steps = steps[steps.t1 >= pd.Timestamp(burn_ms, unit="ms", tz="UTC")]
tdd = person.get("tdd")
if not (tdd and np.isfinite(tdd)): tdd = float(sys.argv[4])
isf = X.isf_from_tdd(tdd)
carbs = json.load(open(d + "/carbs.json"))
bd = pd.read_csv(d + "/bolus_dec.csv", parse_dates=["t"])
meals, corr, const = M.label(steps, carbs, bd, tdd, isf)
days = (steps.t1.max() - steps.t1.min()).total_seconds() / 86400
nr = meals[~meals.rescue]; ann = nr[nr.announced]
out = dict(pulses_per_day=len(nr) / days, announced_share=float(nr.announced.mean()) if len(nr) else None,
           pulse_per_entered_g=float((1 / ann.estimate_ratio).median()) if len(ann) else None,
           size_med=float(nr.size_g.median()), peak_h=float(nr.peak_h.median()), dur_h=float(nr.dur_h.median()),
           rescues_per_day=float(meals.rescue.sum() / days), corrections_per_day=len(corr) / days,
           ice_mean=float(steps.ice[steps.clean].mean()))
meals.to_csv(d + "/meals_labeled.csv", index=False)
print(json.dumps(out))
"""


def export_sim(run: Path, out: Path):
    """The simulated person's history as an ETL-shaped export: CGM, delivered doses, carb entries, settings."""
    tr = pickle.load(open(run / "truth.pkl", "rb"))
    out.mkdir(parents=True, exist_ok=True)
    cgm = tr["cgm"].sort_index().dropna()
    json.dump([dict(startDate=ts(m), quantity=float(v)) for m, v in cgm.items()], open(out / "glucose.json", "w"))
    th = json.load(open(run / "data" / "therapy.json"))
    json.dump(th, open(out / "therapy.json", "w"))
    itype = th.get("insulinType", "rapidActingAdult")
    doses = []
    # burn-in history (the internal drive's doses, exported to LoopEval as the field) + everything LoopEval sent;
    # zero-volume temps included — a missing basal record reads as unrecorded insulin to ice's gap check
    hist = json.load(open(run / "data" / "doses.json"))
    first = min((r[1] for r in tr.get("received", [])), default=1e18)
    from .world import minute_of
    for x in hist:
        if minute_of(x["startDate"]) < first: doses.append(x)
    for (typ, s, e, u) in tr.get("received", []):
        if u < 0: continue
        if typ == "basal":
            doses.append(dict(deliveryType="basal", basalType="temp", startDate=ts(s), endDate=ts(max(e, s + 1)),
                              volume=float(u), tempRate=float(u) * 60 / max(e - s, 1), insulinType=itype, automatic=True))
        else:
            doses.append(dict(deliveryType="bolus", startDate=ts(s), endDate=ts(s), volume=float(u),
                              insulinType=itype, automatic=False))
    json.dump(sorted(doses, key=lambda d: d["startDate"]), open(out / "doses.json", "w"))
    carbs = [dict(startDate=ts(t), entryDate=ts(t), dosingVisibleDate=ts(t), grams=float(g), absorptionTime=float(a))
             for (t, g, a) in tr["entries"]]
    json.dump(carbs, open(out / "carbs.json", "w"))
    return carbs


def bolus_decisions(run: Path) -> pd.DataFrame:
    """Each plant-person bolus with the calculator recommendation LoopEval showed at that step."""
    t = json.load(open(run / "trace.json"))
    p = pd.DataFrame(t["predictions"])
    p = p[p.plantBolusU.fillna(0) > 0]
    return pd.DataFrame(dict(t=pd.to_datetime(p.t), requested=p.plantBolusU.astype(float),
                             rec=p.candidateManualBolusRecOut.astype(float)))


def check(run: Path) -> dict | None:
    import subprocess
    meta = json.load(open(run / "meta.json"))
    tdd = float(pickle.load(open(run / "person.pkl", "rb")).truth["tdd"])
    with tempfile.TemporaryDirectory() as d:
        export_sim(run, Path(d))
        bolus_decisions(run).to_csv(Path(d) / "bolus_dec.csv", index=False)
        burn_ms = int((EPOCH + pd.Timedelta(minutes=meta.get("burn_end", 1800))).value // 1_000_000)
        r = subprocess.run([sys.executable, "-W", "ignore", "-c", ICE_SCRIPT, str(ICE_ANALYSIS), d, str(burn_ms), str(tdd)],
                           capture_output=True, text=True)
        if r.returncode == 0 and (Path(d) / "meals_labeled.csv").exists():
            import shutil
            shutil.copy(Path(d) / "meals_labeled.csv", run / "meals_labeled.csv")
    if r.returncode != 0:
        print(run.name, "ice check failed:", r.stderr[-400:]); return None
    return dict(alias=run.name, **json.loads(r.stdout.strip().splitlines()[-1]))


def main():
    rows = [r for r in (check(Path(a)) for a in sys.argv[1:]) if r]
    df = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(df.round(3).to_string(index=False))
    print(df.median(numeric_only=True).round(3).to_string())


if __name__ == "__main__":
    main()
