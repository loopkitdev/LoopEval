#!/usr/bin/env python3
"""Build the 5-minute panel for every available person and cache it.

Outputs (all under OUT, git-ignored):
    panels/<alias>.pkl     the per-person panel
    cohort.csv             one row per person: summary statistics
    offsets.csv            inferred/declared UTC offsets with confidence

Aliases only — no hostname, token or donor id is ever written here.
"""
from __future__ import annotations

import os
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S                                   # noqa: E402
from loopeval_analysis import dists as D            # noqa: E402

warnings.filterwarnings("ignore", category=FutureWarning)

BDDP_ROOT = os.path.expanduser("~/dev/LoopEval/runs/2026-08-13-cohort-2mo")
# The wide cohort's own four-stream exports (alias-named; ids never on disk here).
WIDE_ROOT = os.path.expanduser("~/.loop-eval/trait-cohort/full")
OUT = Path(os.path.expanduser("~/dev/LoopEvalScenarios/runs/2026-08-25-distributions"))

# Nightscout sites come from PRIVATE.md, which is git-ignored. Real hostnames must
# never appear in a tracked file — only aliases do. If PRIVATE.md is absent this
# simply yields no NS sites and the donor cohort is analysed on its own.
SKIP_ALIASES = {
    # A synthetic Loop test rig, not a person: its glucose and doses are injected
    # for plumbing tests and do not make biological sense.
    "looptest",
    # oref/Trio sites. The study describes Loop users; a different controller
    # shapes the trace differently (SMB cadence, dynamic ISF), and two people
    # cannot characterise that difference — they would just blur the population.
    "orefuser", "orefuser2",
}


def ns_sites(private_md: Path | None = None) -> list[tuple[str, str]]:
    """Parse `| **alias** | `https://host` ... |` rows out of PRIVATE.md."""
    private_md = private_md or Path(__file__).resolve().parents[2] / "PRIVATE.md"
    if not private_md.exists():
        print("  PRIVATE.md absent — donor cohort only")
        return []
    row = re.compile(r"^\|\s*\*\*([A-Za-z0-9_]+)\*\*\s*\|\s*`https?://([^/`\s]+)")
    out = []
    for line in private_md.read_text().splitlines():
        m = row.match(line.strip())
        if m and m.group(1) not in SKIP_ALIASES:
            out.append((m.group(1), m.group(2)))
    return out

# Behavioural labels from the cohort summary, for grouping in the views.
ARCHETYPE = {
    "bddp01": "non-announcer",   "bddp02": "non-announcer",
    "bddp03": "heavy announcer", "bddp04": "heavy announcer",
    "bddp05": "heavy announcer", "bddp06": "moderate announcer",
    "bddp07": "heavy announcer", "bddp08": "heavy announcer",
    "bddp09": "non-announcer",   "bddp10": "moderate announcer",
    "bddp11": "non-announcer",
}
ALGO: dict = {}          # Loop only; oref sites are excluded above


def archetype_from_carbs(g_per_day: float) -> str:
    """Same cut points the cohort summary used, so NS sites get a group too."""
    if g_per_day < 30:
        return "non-announcer"
    if g_per_day < 120:
        return "moderate announcer"
    return "heavy announcer"


def _strategy(panel: pd.DataFrame) -> str:
    """How Loop's automated insulin arrives: as boluses or as temp basals."""
    temp_u = float(((panel["basal_eff"] - panel["basal_sched"]).clip(lower=0)
                    * D.BIN_MIN / 60).sum())
    auto_u = float(panel["auto_bolus_u"].sum())
    if auto_u + temp_u <= 0:
        return "?"
    return "bolus" if auto_u > 0.5 * temp_u else "temp"


def summarize(alias: str, panel: pd.DataFrame, ds: D.Dataset,
              conf: float) -> dict:
    c = D.clean(panel)
    if c.empty:
        return {}
    days = (panel.index.max() - panel.index.min()).total_seconds() / 86400
    deliv = panel["basal_eff"].sum() * D.BIN_MIN / 60 + panel["bolus_u"].sum()
    v, bg = c["v"], c["bg"]
    return {
        "alias": alias,
        "source": ds.source,
        "algo": ALGO.get(alias, "Loop"),
        "archetype": ARCHETYPE.get(alias, ""),
        "insulin": ds.insulin_name,
        "days": round(days, 1),
        "n_clean": len(c),
        "coverage_pct": round(100 * len(c) / len(panel), 1),
        "utc_offset_h": ds.utc_offset_h,
        "offset_inferred": ds.offset_inferred,
        "offset_conf": round(conf, 2),
        # glucose
        "bg_mean": round(bg.mean(), 1),
        "bg_sd": round(bg.std(), 1),
        "bg_cv": round(100 * bg.std() / bg.mean(), 1),
        "bg_p05": round(bg.quantile(0.05), 1),
        "bg_p50": round(bg.median(), 1),
        "bg_p95": round(bg.quantile(0.95), 1),
        "bg_skew": round(bg.skew(), 2),
        "tir": round(100 * bg.between(70, 180).mean(), 1),
        "t54": round(100 * (bg < 54).mean(), 2),
        "t70": round(100 * (bg < 70).mean(), 2),
        "t180": round(100 * (bg > 180).mean(), 1),
        "t250": round(100 * (bg > 250).mean(), 1),
        # velocity (mg/dL per 5 min)
        "v_sd": round(v.std(), 2),
        "v_skew": round(v.skew(), 2),
        "v_kurt": round(v.kurtosis(), 2),
        "v_p01": round(v.quantile(0.01), 2),
        "v_p99": round(v.quantile(0.99), 2),
        "v_rise_frac": round(100 * (v > 0).mean(), 1),
        # insulin
        "tdd": round(deliv / days, 1),
        "basal_frac": round(panel["basal_eff"].sum() * D.BIN_MIN / 60 / deliv, 2),
        "auto_frac_u": round(panel["auto_bolus_u"].sum()
                             / max(panel["bolus_u"].sum(), 1e-9), 2),
        "ia_abs_mean": round(c["ia_abs"].mean() * 12, 1),      # mg/dL per hour
        "ia_net_mean": round(c["ia_net"].mean() * 12, 1),
        # Two different "basal shares", and the difference is the dosing strategy:
        #   ia_sched_share — activity of the SCHEDULED stream (ia_abs − ia_net) over
        #                    all activity. This is what a basal-relative forecast books
        #                    at zero, and it is invariant to strategy.
        #   ia_basal_share — all basal DELIVERED (schedule + temps) over all activity.
        #                    For a temp-basal-strategy user this includes every
        #                    correction Loop made, so it is NOT the schedule.
        "ia_sched_share": round((c["ia_abs"] - c["ia_net"]).mean() / c["ia_abs"].mean(), 2),
        "ia_basal_share": round(c["ia_basal"].mean() / c["ia_abs"].mean(), 2),
        "strategy": _strategy(panel),
        "iob_net_mean": round(c["iob_net"].mean(), 2),
        "iob_abs_mean": round(c["iob_abs"].mean(), 2),
        # the non-insulin side
        "ice_abs_mean": round(c["ice_abs"].mean() * 12, 1),    # mg/dL per hour
        "ice_abs_sd": round(c["ice_abs"].std(), 2),
        "ice_net_mean": round(c["ice_net"].mean() * 12, 1),
        "carb_g_day": round(panel["carb_effect"].sum()
                            / max(panel["isf"].mean() / panel["cr"].mean(), 1e-9)
                            / days, 0),
        # how much of glucose motion insulin accounts for
        "var_expl_insulin": round(1 - c["ice_abs"].var() / v.var(), 3),
        "corr_v_ia": round(np.corrcoef(v, c["ia_abs"])[0, 1], 3),
    }


def main() -> int:
    (OUT / "panels").mkdir(parents=True, exist_ok=True)
    rows, offs = [], []

    datasets: list[D.Dataset] = list(D.bddp_datasets(BDDP_ROOT))
    if os.path.isdir(WIDE_ROOT):
        wide = D.bddp_datasets(WIDE_ROOT, source="wide")
        # A wide-cohort export is unvalidated: no per-donor override
        # reconstruction, no curve-through-field check. Keep it distinguishable
        # from the eleven that were individually validated, and never pool
        # silently in a figure.
        datasets += wide
        print(f"  + {len(wide)} wide-cohort exports")
    for alias, host in ns_sites():
        try:
            datasets.append(D.ns_dataset(alias, host))
        except Exception as e:                                  # noqa: BLE001
            print(f"  {alias}: skipped ({type(e).__name__})")

    for ds in datasets:
        inferred, conf = D.infer_utc_offset(ds.doses_path, ds.carbs_path)
        if ds.offset_inferred:
            ds.utc_offset_h = inferred
        offs.append({"alias": ds.alias, "used": ds.utc_offset_h,
                     "inferred": inferred, "conf": round(conf, 2),
                     "declared": None if ds.offset_inferred else ds.utc_offset_h})
        try:
            panel = S.clip_window(ds.alias, D.build_panel(ds))
        except Exception as e:                                  # noqa: BLE001
            print(f"  {ds.alias}: FAILED {type(e).__name__}: {e}")
            continue
        panel.to_pickle(OUT / "panels" / f"{ds.alias}.pkl")
        row = summarize(ds.alias, panel, ds, conf)
        if row:
            if not row["archetype"]:
                row["archetype"] = archetype_from_carbs(row["carb_g_day"])
            rows.append(row)
        print(f"  {ds.alias:<10} {row.get('days', 0):>6.1f}d  "
              f"{row.get('n_clean', 0):>6d} clean  TIR {row.get('tir', 0):>5.1f}  "
              f"meanBG {row.get('bg_mean', 0):>5.1f}  "
              f"ICE {row.get('ice_abs_mean', 0):>5.1f} mg/dL/hr")

    cohort = pd.DataFrame(rows).sort_values("tir", ascending=False)
    cohort.to_csv(OUT / "cohort.csv", index=False)
    pd.DataFrame(offs).to_csv(OUT / "offsets.csv", index=False)
    print(f"\nwrote {len(cohort)} people -> {OUT}/cohort.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
