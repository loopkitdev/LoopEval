"""Run a virtual cohort in closed loop through LoopEval, in parallel, then score it.

    python -m loopeval_analysis.patient_sim.cohort --n 40 --days 14 --out <root> [--par 14] [--seed0 1000]
                                                     [--disable exercise,illness,...] [--bin loop-eval]

Each person is `sample_person(templates, seed0 + i)`; seeds make every cohort reproducible and every
ablation (--disable) a paired comparison on the same people.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd


def _one(args):
    seed, days, root, tmpl, binp, enable, controller, flags = args
    from .person import sample_person
    from .loopeval_io import run
    out = Path(root) / f"v{seed:05d}"
    if (out / "truth.pkl").exists():
        return seed, "cached"
    try:
        T = pd.read_csv(tmpl)
        P = sample_person(T, seed, isf_w=enable.get("isf_w") if isinstance(enable.get("isf_w"), float) else None,
                          csf_mult=enable.get("csf_mult", 1.0) if isinstance(enable.get("csf_mult"), float) else 1.0,
                          sg_mult=enable.get("sg_mult", 1.0) if isinstance(enable.get("sg_mult"), float) else 1.0,
                          prof_w=enable.get("prof_w") if isinstance(enable.get("prof_w"), float) else None,
                          egp_share=enable.get("egp_share") if isinstance(enable.get("egp_share"), float) else None,
                          isf_total=bool(enable.get("isf_total", False)),
                          kappa_mult=enable.get("kappa_mult", 1.0) if isinstance(enable.get("kappa_mult"), float) else 1.0,
                          ge_var=bool(enable.get("ge_var", True)), basal_own=bool(enable.get("basal_own", False)),
                          basal_share=enable.get("basal_share") if isinstance(enable.get("basal_share"), float) else None)   # per-person gastric emptying, default on (Pete 2026-10-16, LESSONS 88)
        if enable.get("settings_mismatch") is False:      # ablation: the person tells Loop the truth
            P.settings.update(isf=P.truth["isf"], cr=P.truth["cr"], basal_uh=P.truth["basal_uh"])
        run(P, days, out, binp, enable=enable, controller=controller, extra_flags=flags.get(P.name, flags.get("*", [])))
        return seed, "ok"
    except Exception as e:                                       # noqa: BLE001
        (Path(root) / f"v{seed:05d}.err").write_text(traceback.format_exc())
        return seed, f"FAIL {e}"[:200]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--seed0", type=int, default=1000)
    ap.add_argument("--par", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--out", required=True)
    ap.add_argument("--templates", default=str(Path.home() / ".loop-eval/runs/2026-10-15-additive-templates/templates.csv"))
    ap.add_argument("--bin", default=os.environ.get("LOOPEVAL_BIN", str(Path.home() / "dev/LoopEval/.build/release/loop-eval")))
    ap.add_argument("--controller", default="loop-main", choices=["loop-main", "loopalgorithm"])
    ap.add_argument("--disable", default="")
    ap.add_argument("--enable", default="", help="switches to turn ON (e.g. perfect_person, menstrual)")
    ap.add_argument("--flags-json", default="", help="candidate flags for LoopEval: {person name or '*': [flag, ...]} — paired candidate arms")
    ap.add_argument("--set", default="", help="numeric component overrides, e.g. meal_k=0.6 (multiplies meal kempt/kabs)")
    a = ap.parse_args()
    enable = {k: False for k in a.disable.split(",") if k}
    enable.update({k: True for k in a.enable.split(",") if k})
    enable.update({kv.split("=")[0]: float(kv.split("=")[1]) for kv in a.set.split(",") if "=" in kv})
    root = Path(a.out); root.mkdir(parents=True, exist_ok=True)
    json.dump(vars(a), open(root / "cohort.json", "w"), indent=1)
    flags = json.load(open(a.flags_json)) if a.flags_json else {}
    jobs = [(a.seed0 + i, a.days, str(root), a.templates, a.bin, enable, a.controller, flags) for i in range(a.n)]
    with ProcessPoolExecutor(a.par) as ex:
        for f in as_completed([ex.submit(_one, j) for j in jobs]):
            s, st = f.result(); print(f"v{s:05d} {st}", flush=True)
    from .validate import main as vmain
    sys.argv = ["validate", str(root)]
    vmain()


if __name__ == "__main__":
    main()
