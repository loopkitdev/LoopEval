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

from .world import _num


def _one(args):
    seed, days, root, tmpl, binp, enable, controller, flags = args
    from .person import sample_person
    from .loopeval_io import run
    out = Path(root) / f"v{seed:05d}"
    if (out / "truth.pkl").exists():
        return seed, "cached"
    try:
        T = pd.read_csv(tmpl)
        # tmpl_cycle: twin i takes template row seed mod len(T), so n = len(T) seeds cover every template once (per-donor fits;
        # LESSONS 531) instead of drawing templates at random
        P = sample_person(T, seed, alias=(T.alias.iloc[seed % len(T)] if enable.get("tmpl_cycle") else None), isf_w=enable.get("isf_w") if _num(enable.get("isf_w")) else None,
                          csf_mult=enable.get("csf_mult", 1.0) if _num(enable.get("csf_mult")) else 1.0,
                          csf_f_floor=float(enable["csf_f_floor"]) if _num(enable.get("csf_f_floor")) else 0.3,
                          sg_mult=enable.get("sg_mult", 1.0) if _num(enable.get("sg_mult")) else 1.0,
                          prof_w=enable.get("prof_w") if _num(enable.get("prof_w")) else None,
                          egp_share=enable.get("egp_share") if _num(enable.get("egp_share")) else None,
                          isf_total=bool(enable.get("isf_total", True)),   # total-drop ISF + full intake budget, the base since 2026-10-18 (Pete; LESSONS 143)
                          kappa_mult=enable.get("kappa_mult", 1.0) if _num(enable.get("kappa_mult")) else 1.0,
                          ge_var=bool(enable.get("ge_var", True)), basal_own=bool(enable.get("basal_own", False)),
                          egp_sat=bool(enable.get("egp_sat", True)),   # default since 2026-10-18 (A5 review loop, LESSONS 196)
                          p2e=enable.get("p2e_cal") if _num(enable.get("p2e_cal")) else None,
                          prof_deliv=bool(enable.get("prof_deliv", True)),   # default since 2026-10-19 (LESSONS 250)
                          csf_own=bool(enable.get("csf_own", False)),
                          twin=bool(enable.get("twin", False)),
                          lvl_own=bool(enable.get("lvl_own", False)),
                          basal_fit=bool(enable.get("basal_fit", False)),
                          gb_own=bool(enable.get("gb_own", False)),
                          ge_split=bool(enable.get("ge_split", False)),   # glucose effectiveness from named parts (LESSONS 548)
                          ge_spare=bool(enable.get("ge_spare", False)),   # A1c alone: uptake falling below 81 (LESSONS 561)
                          suspend_own=bool(enable.get("suspend_own", True)),   # default since 2026-10-19 (LESSONS 232)
                          night_add=bool(enable.get("night_add", True)),   # night need added on top; default since 2026-10-19 (LESSONS 263)
                          night_own=bool(enable.get("night_own", False)),   # body night need from the donor's steady nights (LESSONS 251); off since 2026-10-19: the evening's own fat carries it (LESSONS 370)
                          basal_share=enable.get("basal_share") if _num(enable.get("basal_share")) else 0.42,
                          isf_blend=enable.get("isf_blend") if _num(enable.get("isf_blend")) else 0.0,
                          csf_w=enable.get("csf_w") if _num(enable.get("csf_w")) else 0.5,
                          isf_level=enable.get("isf_level") if _num(enable.get("isf_level")) else 1.0,
                          intake_own=bool(enable.get("intake_own")),
                          csf_geq=bool(enable.get("csf_geq", True)),
                          csf_lvl=enable.get("csf_lvl") if _num(enable.get("csf_lvl")) else 1.05,   # LESSONS 401
                          csf_lvl_keepg=bool(enable.get("csf_lvl_keepg")),
                          csf_sd_w=float(enable["csf_sd_w"]) if _num(enable.get("csf_sd_w")) else 1.0,   # L 632
                          prof_np=bool(enable.get("prof_np")))   # default since 2026-10-19 (LESSONS 358)   # default since 2026-10-19 (LESSONS 300)   # per-person gastric emptying, default on (Pete 2026-10-16, LESSONS 88)
        if enable.get("settings_mismatch") is False:      # ablation: the person tells Loop the truth
            P.settings.update(isf=P.truth["isf"], cr=P.truth["cr"], basal_uh=P.truth["basal_uh"])
        if _num(enable.get("preg_week")) and P.sex == "F" and 13 <= P.age <= 50:
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
    # a numeric override belongs in --set: in --enable it becomes a switch NAMED "k=v", the code's isinstance(..., float)
    # check fails, and the arm runs as its own control without a word (it voided the ex_surge_mets arms, 2026-11-01)
    bad = [k for k in (a.enable + "," + a.disable).split(",") if "=" in k]
    if bad: ap.error(f"--enable/--disable take switch names, not values: {bad}. Pass numeric overrides in --set.")
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
