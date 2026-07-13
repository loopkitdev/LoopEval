"""Frontier scoring & plotting — the standard candidate-comparison workflow.

A *frontier experiment* asks: does an algorithm/settings change genuinely
improve outcomes, or does it just slide along the aggressiveness trade-off?

The method:

1. Run a **reference sweep**: the stock algorithm at several ISF multipliers
   (``simulate --candidate-sensitivity-multiplier``). Scoring each trace gives
   a TIR-vs-t<54 **reference curve** — the outcomes reachable by pure
   aggressiveness tuning.
2. Run each **candidate** (an algorithm change) once, at stock sensitivity
   (and optionally at a couple of multipliers of its own).
3. **Lift** = candidate TIR − reference-curve TIR *at the candidate's t<54*.
   Lift ≈ 0 → the change is a slider (a point on the same curve).
   Lift > 0 → a genuine structural improvement (more TIR at equal severe-lows).

Plot convention (see ``plotting.tir_t54_axes``): x = TIR (right = better),
y = t<54 (up = worse), better = lower-right; dotted line marks the ~1% t<54
budget.

Usage (Python)::

    from loopeval_analysis.frontier import score_traces, reference_curve, plot_frontier
    ref  = score_traces({"0.80": "m0.80.json", "1.00": "m1.00.json", ...},
                        outages_csv="outages.csv", cgm_gaps_csv="cgm_gaps.csv")
    cand = score_traces({"asym-IRC": "airc.json", ...}, ...)
    plot_frontier(ref, cand, out="frontier.png", field_trace="m1.00.json")

Usage (CLI)::

    python -m loopeval_analysis.frontier \
        --ref  'm*.json' \
        --cand airc.json:asym-IRC --cand sensmode.json:double-low-prevention \
        --outages-csv outages.csv --cgm-gaps-csv cgm_gaps.csv \
        --field-from m1.00.json --out frontier.png

``--ref`` takes a glob whose files are scored into the reference curve (label =
filename stem). ``--cand`` may repeat; ``path:label`` sets the display label.
"""
from __future__ import annotations

import argparse
import glob as _glob
import json
import sys
from pathlib import Path
from typing import Dict, Mapping, Optional

import numpy as np
import pandas as pd

from loopeval_analysis.scoring import score_counterfactual, outcome_stats, exclusion_mask
from loopeval_analysis.plotting import tir_t54_axes


# --------------------------------------------------------------------------- #
#  Scoring                                                                    #
# --------------------------------------------------------------------------- #

def score_traces(traces: Mapping[str, str | Path],
                 outages_csv: Optional[str] = None,
                 cgm_gaps_csv: Optional[str] = None,
                 post_hours: float = 0.0) -> pd.DataFrame:
    """Score a set of trace JSONs → DataFrame indexed by label.

    Columns include at least ``TIR`` and ``t54`` (all keys returned by
    ``scoring.outcome_stats``). Traces that fail to score are dropped with a
    warning on stderr.
    """
    rows = {}
    for label, path in traces.items():
        try:
            rows[label] = score_counterfactual(str(path), outages_csv, cgm_gaps_csv,
                                               post_hours=post_hours)
        except Exception as exc:  # noqa: BLE001
            print(f"[frontier] skipping {label} ({path}): {exc}", file=sys.stderr)
    return pd.DataFrame(rows).T


def field_point(trace_path: str | Path,
                outages_csv: Optional[str] = None,
                cgm_gaps_csv: Optional[str] = None,
                burnin_hours: float = 6.0) -> dict:
    """Score the REAL deployment (the trace's ``actual`` CGM series) with the
    same burn-in + disruption exclusions, so the field point is comparable to
    the sim points. Any trace from the same dataset/window works.
    """
    import pytz
    from loopeval_analysis.outage import read_outages_csv
    from loopeval_analysis.cgm_gaps import read_cgm_gaps_csv

    t = json.loads(Path(trace_path).read_text())
    a = pd.DataFrame(t["actual"])
    a["t"] = pd.to_datetime(a["t"], format="ISO8601", utc=True)
    bg = a.set_index("t")["bg"].dropna()
    cutoff = pd.to_datetime(t["intervalStart"]) + pd.Timedelta(hours=burnin_hours)
    bg = bg.loc[bg.index >= cutoff]
    outages = read_outages_csv(outages_csv) if outages_csv else []
    gaps = read_cgm_gaps_csv(cgm_gaps_csv) if cgm_gaps_csv else []
    excl = exclusion_mask(bg.index, outages, gaps, post_hours=0.0)
    s = outcome_stats(bg, exclude=excl)
    s["kept_frac"] = s["n"] / len(bg)
    return s


# --------------------------------------------------------------------------- #
#  Lift                                                                       #
# --------------------------------------------------------------------------- #

def lift(ref: pd.DataFrame, tir: float, t54: float) -> float:
    """TIR above the reference curve at this t<54 (interpolated).

    The reference curve is (t54 → TIR) from the ISF sweep, sorted by t54.
    Outside the swept t54 range the nearest endpoint is used (flat
    extrapolation) — treat lift for far-outside points with caution.
    """
    pts = ref[["t54", "TIR"]].dropna().sort_values("t54")
    if len(pts) < 2:
        return float("nan")
    return float(tir - np.interp(t54, pts["t54"].values, pts["TIR"].values))


def add_lift(ref: pd.DataFrame, cand: pd.DataFrame) -> pd.DataFrame:
    """Return ``cand`` with a ``lift`` column computed against ``ref``."""
    out = cand.copy()
    out["lift"] = [lift(ref, r.TIR, r.t54) for r in cand.itertuples()]
    return out


# --------------------------------------------------------------------------- #
#  Plot                                                                       #
# --------------------------------------------------------------------------- #

def plot_frontier(ref: pd.DataFrame, cand: pd.DataFrame,
                  out: str | Path = "frontier.png",
                  field: Optional[dict] = None,
                  title: str = "Frontier: candidates vs ISF reference curve",
                  ylim: tuple = (0.0, 1.5),
                  dpi: int = 130) -> Path:
    """Standard frontier plot.

    Reference curve: grey, connected in the order given (sort your sweep by
    multiplier). Candidates: one colored diamond each, ``lift`` in the legend.
    ``field``: optional dict from :func:`field_point`, drawn as a red star.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 7))
    r = ref.dropna(subset=["TIR", "t54"])
    ax.plot(r["TIR"], r["t54"], "o-", color="#888", zorder=2, label="ISF sweep (reference)")
    for label, row in r.iterrows():
        ax.annotate(str(label), (row["TIR"], row["t54"]), fontsize=6, color="#888",
                    xytext=(2, 2), textcoords="offset points")

    cand = add_lift(ref, cand)
    colors = plt.cm.tab10(np.linspace(0, 1, max(len(cand), 1)))
    for (label, row), c in zip(cand.iterrows(), colors):
        ax.scatter([row["TIR"]], [row["t54"]], s=95, color=c, marker="D", zorder=5,
                   label=f"{label} (lift {row['lift']:+.1f})")

    if field is not None:
        ax.scatter([field["TIR"]], [field["t54"]], s=280, marker="*", color="crimson",
                   zorder=6, label="FIELD (real deployment)")

    tir_t54_axes(ax, ylim=ylim)
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.3)
    out = Path(out)
    fig.tight_layout()
    fig.savefig(out, dpi=dpi)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------- #
#  CLI                                                                        #
# --------------------------------------------------------------------------- #

def _parse_labeled(items: list[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for it in items:
        path, sep, label = it.rpartition(":")
        if sep and Path(path).suffix == ".json":
            out[label] = path
        else:
            out[Path(it).stem] = it
    return out


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="frontier",
        description="Score simulate traces, build the ISF reference curve, compute lift, plot.")
    ap.add_argument("--ref", required=True,
                    help="glob of reference-sweep traces (ISF multipliers), e.g. 'm*.json'")
    ap.add_argument("--cand", action="append", default=[],
                    help="candidate trace, 'path.json:Label' (repeatable)")
    ap.add_argument("--outages-csv")
    ap.add_argument("--cgm-gaps-csv")
    ap.add_argument("--field-from", help="trace whose 'actual' series scores the real deployment")
    ap.add_argument("--out", default="frontier.png")
    ap.add_argument("--title", default="Frontier: candidates vs ISF reference curve")
    args = ap.parse_args(argv)

    ref_paths = sorted(_glob.glob(args.ref))
    if not ref_paths:
        print(f"no reference traces match {args.ref!r}", file=sys.stderr)
        return 1
    ref = score_traces({Path(p).stem: p for p in ref_paths},
                       args.outages_csv, args.cgm_gaps_csv)
    cand = score_traces(_parse_labeled(args.cand), args.outages_csv, args.cgm_gaps_csv)
    cand = add_lift(ref, cand)

    print("reference curve:")
    print(ref[["TIR", "t54"]].round(3).to_string())
    if len(cand):
        print("\ncandidates:")
        print(cand[["TIR", "t54", "lift"]].round(3).to_string())

    fp = field_point(args.field_from, args.outages_csv, args.cgm_gaps_csv) if args.field_from else None
    if fp:
        print(f"\nFIELD  TIR {fp['TIR']:.1f}  t54 {fp['t54']:.3f}  kept {fp['kept_frac']:.2f}")
    out = plot_frontier(ref, cand, out=args.out, field=fp, title=args.title)
    print(f"\nsaved {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
