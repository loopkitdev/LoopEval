"""Self-consistency check: a body dosed exactly to its own truth must sit near its rest level.

For each sampled person: settings := truth (ISF, CR, basal), a perfect person (every eating event entered
exactly and bolused at the meal), every disturbance off, the internal open-loop drive. A mean far above
the rest level means two components disagree in their units (LESSONS 18: rescue glucose at f = 1.0 on a
meal-calibrated body; LESSONS 15: ISF calibrated on the wrong part of the body).

    python -m loopeval_analysis.patient_sim.selfcheck [--n 8] [--templates ...]
"""
from __future__ import annotations

import argparse
import copy
from pathlib import Path

import pandas as pd

from .person import _probe_csf_effective, sample_person
from .world import World

QUIET = dict(exercise=False, illness=False, circadian=False, dawn=False, site_failure=False, pump_faults=False,
             compression=False, day=False, perfect_person=True, fat=False, behavior_defense=False, graze=False,
             # the gastric-emptying ceiling is timing, not units: an open-loop bolus at the start of a big meal acts
             # before the energy-limited stomach delivers it (LESSONS 33), which this units check must not read as a fault
             ge_kcal=0.0)


def check(templates: pd.DataFrame, seeds, days: int = 10, above_rest_max: float = 40.0, day_mean_max: float = 250.0) -> pd.DataFrame:
    """A unit mismatch shows as drift in the POST-ABSORPTIVE night (00–06) away from the body's own rest level (Gb):
    insulin and carbohydrate that do not balance accumulate there. Daytime meal excursions are timing physics (an
    open-loop bolus at the meal against the person's own absorption and carb sensitivity), so the day is only
    guarded against a runaway (no day mean above 250)."""
    rows = []
    for sd in seeds:
        P = sample_person(templates, sd)
        Q = copy.deepcopy(P)
        # dose with the CR consistent with the body (effective ISF ÷ effective CSF, same probe semantics); the person's
        # truth["cr"] is the linear-part bookkeeping ratio that sets intake against TDD (LESSONS 40)
        cr_eff = P.truth["isf"] / _probe_csf_effective(P.body, P.formulation)
        Q.settings.update(isf=P.truth["isf"], cr=cr_eff, basal_uh=P.truth["basal_uh"])
        W = World(Q, days, enable=QUIET)
        W.run_internal(days * 1440)
        tr = pd.DataFrame(W.truth, columns=["m", "bg", "ra", "egp", "si", "u", "abs"])
        tr = tr[tr.m >= 1440]
        mean = float(tr.bg.mean()); tir = float(100 * tr.bg.between(70, 180).mean())
        night = float(tr[(tr.m % 1440) < 360].bg.mean())
        worst_day = float(tr.groupby(tr.m // 1440).bg.mean().max())
        rows.append(dict(seed=sd, template=P.template, mean=round(mean, 1), night=round(night, 1), tir=round(tir, 1),
                         gb=round(P.body.gb, 1),
                         ok=abs(night - P.body.gb) <= above_rest_max and worst_day <= day_mean_max))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--seed0", type=int, default=1000)
    ap.add_argument("--templates", default=str(Path.home() / ".loop-eval/runs/2026-10-15-additive-templates/templates_pilot.csv"))
    a = ap.parse_args()
    r = check(pd.read_csv(a.templates), range(a.seed0, a.seed0 + a.n))
    print(r.to_string(index=False))
    print("PASS" if r.ok.all() else f"FAIL: {int((~r.ok).sum())} of {len(r)} bodies are inconsistent with their own truth")
    raise SystemExit(0 if r.ok.all() else 1)


if __name__ == "__main__":
    main()
