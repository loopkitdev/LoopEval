#!/usr/bin/env python3
"""The ISF used for ICE analysis — one place, three tiers.

Adopted 2026-10-10 (eda lesson 54). Every ICE analysis takes its ISF from here
(or from ice/isf_estimate.csv, which this module writes for the cohort).

  tier "start"     no dosing or glucose history: ISF = K / TDD^b fitted to the
                   yardstick (isf_start_rule.py; ~1290 / TDD^0.90, or ~1870 / TDD).
                   Needs a TDD from elsewhere (injections, previous pump, weight).
                   Expect about +-25%; carries diet (TDD includes meal insulin).
  tier "yardstick" any history: the fasting regression of each quiet hour's
                   glucose change on insulin absorbed, shrunk toward the basal
                   rule from the MEASURED fasting insulin rate, levelled by one
                   cohort factor. With under ~2 weeks of quiet hours (< 100
                   blocks) it returns the basal rule exactly; the weight on the
                   person's own slope then grows (about 0.5 at 2 weeks, 0.75 at
                   a month). Repeatability floor about +-15% month to month.

Quiet hours: no announced carbs on board, no user bolus in the prior 4 h, no
disruption, and the ICE bad-data screen (ice_raw.EXCLUDE). Cohort parameters
are read from ice/isf_yardstick_params.json, written by isf_basal_prior.py and
isf_start_rule.py; they are this cohort's calibration, borrowed by a newcomer.

Rationale page: "An ISF Yardstick" (artifact T8Dbp4JLN7EpZ64wttwTdX).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa

PARAMS = json.loads((S.OUT / "ice" / "isf_yardstick_params.json").read_text())
H = 12


def start_rule(tdd: float, simple: bool = False) -> float:
    """No-history ISF from total daily dose (U/day)."""
    if simple:
        return PARAMS["start_rule_X"] / tdd
    return PARAMS["start_rule_K"] / tdd ** PARAMS["start_rule_b"]


def basal_rule(fasting_u_per_hr: float) -> float:
    """ISF from the measured fasting insulin rate, at the yardstick's level."""
    raw = PARAMS["basal_rule_K"] * fasting_u_per_hr ** PARAMS["basal_rule_b"]
    return float(raw * np.exp(PARAMS["slope_offset_log"]) * PARAMS["level_factor"])


def yardstick(panel: pd.DataFrame, quiet: np.ndarray, select: np.ndarray | None = None) -> dict:
    """The yardstick for one person from a 5-min panel and its quiet-step mask.

    Returns isf, tier, weight on the person's own slope, quiet blocks used, and
    the measured fasting insulin rate. `select` restricts to part of the record.
    """
    from isf_shrink import fit
    sel = np.ones(len(panel), bool) if select is None else select
    u = panel["ia_abs"].to_numpy() / panel["isf"].to_numpy() * H        # U/hr absorbed
    m = quiet & sel & np.isfinite(u)
    if m.sum() < 12:
        return {"isf": np.nan, "tier": "none", "weight_own": 0.0, "blocks": 0, "fasting_u_hr": np.nan}
    fb = float(np.median(u[m]))
    prior = np.log(basal_rule(fb) / PARAMS["level_factor"])            # in raw-slope units
    c, se, n = fit(panel, quiet, sel)
    w = 0.0
    if n >= PARAMS["min_blocks"] and np.isfinite(c) and c > 0 and np.isfinite(se):
        se *= PARAMS["se_calibration"]
        w = PARAMS["tau_log"] ** 2 / (PARAMS["tau_log"] ** 2 + se ** 2)
        est = prior + w * (np.log(c) - prior)
    else:
        est = prior
    return {"isf": float(np.exp(est) * PARAMS["level_factor"]), "tier": "yardstick",
            "weight_own": float(w), "blocks": int(n), "fasting_u_hr": fb}


def for_alias(alias: str) -> dict:
    """The yardstick for a cohort member, quiet hours and screen applied."""
    from ice_first import _quiet_mask
    from ice_raw import excluded_on_grid
    p = S.load(alias)
    p = p[p["bg"].notna() | p["v"].notna()]
    q = _quiet_mask(p) & ~excluded_on_grid(alias, p.index)
    return {"alias": alias, **yardstick(p, q)}


if __name__ == "__main__":
    from multiprocessing import Pool
    co = S.cohort()
    S.datasets()
    with Pool(8) as pl:
        d = pd.DataFrame(pl.map(for_alias, list(co.alias)))
    ref = pd.read_csv(S.OUT / "ice" / "isf_estimate.csv").set_index("alias").isf_est
    r = np.log(d.set_index("alias").isf / ref).dropna()
    print(f"{d.isf.notna().sum()} of {len(d)} people; tiers {d.tier.value_counts().to_dict()}; "
          f"weight on own slope median {d.weight_own.median():.2f}")
    print(f"against ice/isf_estimate.csv: median |difference| {100 * (np.exp(r.abs().median()) - 1):.2f}%, "
          f"max {100 * (np.exp(r.abs().max()) - 1):.2f}%  (should be ~0: same method, same parameters)")
    print("start rule example, 40 U/day:", round(start_rule(40), 1), "| simple:", round(start_rule(40, True), 1))
