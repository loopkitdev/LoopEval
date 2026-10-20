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
                          isf_total=bool(enable.get("isf_total", True)),   # total-drop ISF + full intake budget, the base since 2026-10-18 (Pete; LESSONS 143)
                          kappa_mult=enable.get("kappa_mult", 1.0) if isinstance(enable.get("kappa_mult"), float) else 1.0,
                          ge_var=bool(enable.get("ge_var", True)), basal_own=bool(enable.get("basal_own", False)),
                          egp_sat=bool(enable.get("egp_sat", True)),   # default since 2026-10-18 (A5 review loop, LESSONS 196)
                          p2e=enable.get("p2e_cal") if isinstance(enable.get("p2e_cal"), float) else None,
                          prof_deliv=bool(enable.get("prof_deliv", True)),   # default since 2026-10-19 (LESSONS 250)
                          csf_own=bool(enable.get("csf_own", False)),
                          twin=bool(enable.get("twin", False)),
                          suspend_own=bool(enable.get("suspend_own", True)),   # default since 2026-10-19 (LESSONS 232)
                          night_add=bool(enable.get("night_add", True)),   # night need added on top; default since 2026-10-19 (LESSONS 263)
                          night_own=bool(enable.get("night_own", False)),   # body night need from the donor's steady nights (LESSONS 251); off since 2026-10-19: the evening's own fat carries it (LESSONS 370)
                          basal_share=enable.get("basal_share") if isinstance(enable.get("basal_share"), float) else 0.42,
                          isf_blend=enable.get("isf_blend") if isinstance(enable.get("isf_blend"), float) else 0.0,
                          csf_w=enable.get("csf_w") if isinstance(enable.get("csf_w"), float) else 0.5,
                          isf_level=enable.get("isf_level") if isinstance(enable.get("isf_level"), float) else 1.0,
                          intake_own=bool(enable.get("intake_own")),
                          csf_geq=bool(enable.get("csf_geq", True)),
                          csf_lvl=enable.get("csf_lvl") if isinstance(enable.get("csf_lvl"), float) else 1.0,
                          csf_lvl_keepg=bool(enable.get("csf_lvl_keepg")))   # default since 2026-10-19 (LESSONS 358)   # default since 2026-10-19 (LESSONS 300)   # per-person gastric emptying, default on (Pete 2026-10-16, LESSONS 88)
        if enable.get("settings_mismatch") is False:      # ablation: the person tells Loop the truth
            P.settings.update(isf=P.truth["isf"], cr=P.truth["cr"], basal_uh=P.truth["basal_uh"])
        if isinstance(enable.get("preg_week"), float) and P.sex == "F" and 13 <= P.age <= 50:
            # X9: settings titrated to the need at the starting week (clinic care adjusts doses as pregnancy goes on), so
            # only the change inside the window is new to the controller
            from .modulators import Modulators
            n = Modulators.pregnancy_need(enable["preg_week"])
            P.settings.update(basal_uh=P.settings["basal_uh"] * n, isf=P.settings["isf"] / n, cr=P.settings["cr"] / n,
                              max_basal=P.settings["max_basal"] * n)
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
