"""Frontier scoring & plotting — the standard candidate-comparison workflow.

A *frontier experiment* asks: does an algorithm/settings change genuinely
improve outcomes, or does it just slide along the aggressiveness trade-off?

The method:

1. Run a **reference sweep**: the stock algorithm at several ISF multipliers
   (``simulate --candidate-sensitivity-multiplier``). Scoring each trace gives
   a TIR-vs-t<54 **reference curve** — the outcomes reachable by pure
   aggressiveness tuning.
2. Run each **candidate** (an algorithm change), ideally swept over its own ISF
   multipliers so it traces a curve comparable to the reference.
3. **Lift** = the signed, axis-normalized closest distance from a candidate
   (TIR, t<54) point to the reference sweep polyline: **+** when below-right of
   the sweep (more TIR / less t<54 than aggressiveness tuning reaches), **−** when
   above-left. See :func:`lift`. Rank a *mechanism* (one parameterization swept
   over ISF) by the **mean lift over its sweep** (:func:`summarize_mechanisms`),
   not by a single point — best-of-sweep max is jitter-inflated.
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
import re
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

def _multiplier_of(frame: pd.DataFrame):
    """ISF multiplier per row — from a ``multiplier`` column if present, else parsed
    from the index label (``m1.05`` → 1.05). Returns None if any row can't resolve."""
    if "multiplier" in frame.columns:
        m = frame["multiplier"].to_numpy(dtype=float)
        return None if np.isnan(m).any() else m
    vals = []
    for idx in frame.index:
        mm = re.search(r"m([0-9]*\.?[0-9]+)", str(idx))
        if not mm:
            return None
        vals.append(float(mm.group(1)))
    return np.array(vals, dtype=float)


def _ref_polyline(ref: pd.DataFrame):
    """Reference sweep as an (N,2) [TIR, t54] polyline **ordered by sweep multiplier**
    (the sweep path — adjacent vertices are adjacent settings, so segment
    interpolation is physically meaningful; ordering by TIR would connect
    non-adjacent settings and zig-zag on a non-monotonic sweep). Returns
    (P_sweeporder, span), or (None, None) when there are too few points."""
    sub = ref.dropna(subset=["TIR", "t54"])
    if len(sub) < 2:
        return None, None
    A = sub[["TIR", "t54"]].to_numpy(dtype=float)
    # NB: resolve the multiplier from the FULL frame — slicing to [TIR, t54] first
    # drops the `multiplier` column, silently forcing the TIR-order fallback.
    mult = _multiplier_of(sub)
    order = np.argsort(mult, kind="stable") if mult is not None \
        else np.argsort(A[:, 0], kind="stable")     # fallback: TIR order
    P = A[order]
    span = np.array([np.ptp(A[:, 0]), np.ptp(A[:, 1])])
    span[span == 0] = 1.0                             # guard degenerate axes
    return P, span


def lift(ref: pd.DataFrame, tir: float, t54: float) -> float:
    """Signed, axis-normalized closest distance from a candidate (TIR, t54) point
    to the plain ISF-sweep polyline (the baseline reachable by aggressiveness
    tuning alone).

    Sign is **+** when the point is below-and-to-the-right of the sweep (better:
    more TIR / less t<54) and **−** when above-left (worse). Both axes are scaled
    by the reference sweep's span so TIR (≈tens of %) and t<54 (≈fraction of a %)
    contribute comparably — a raw Euclidean distance would be swamped by TIR.

    Greatest positive lift = best. This replaces the old horizontal "TIR-at-
    matched-t54" gap, which blew up wherever the reference curve runs flat.

    Rank a *mechanism* (one candidate parameterization swept over ISF multipliers)
    by the MEAN (or median) of this lift across its sweep — see
    :func:`summarize_mechanisms`. Best-of-sweep max is optimistically biased (it
    grabs the highest jitter point), so use it only as a secondary "where it
    peaks" readout, not the headline.
    """
    P, span = _ref_polyline(ref)
    if P is None:
        return float("nan")
    q = np.array([tir, t54], dtype=float) / span
    best, closest = np.inf, None
    for a, b in zip(P[:-1], P[1:]):
        A, B = a / span, b / span
        ab = B - A
        denom = float(np.dot(ab, ab)) or 1.0
        s = np.clip(float(np.dot(q - A, ab)) / denom, 0.0, 1.0)
        c = A + s * ab
        d = float(np.hypot(*(q - c)))
        if d < best:
            best, closest = d, c
    # Sign LOCALLY, against the closest point: better = further right (+TIR) and/or
    # further down (-t54), i.e. the (+1,-1) direction in normalized space. Do NOT
    # sign by interpolating a TIR-sorted copy of the curve — on a hooked reference
    # (an announcer's sweep, where TIR rises then falls back as needs climb) TIR
    # order interleaves the two branches, so the lookup interpolates a mild point
    # against a catastrophic one and calls nearly everything an improvement.
    return best if float(np.dot(q - closest, np.array([1.0, -1.0]))) >= 0 else -best


def add_lift(ref: pd.DataFrame, cand: pd.DataFrame) -> pd.DataFrame:
    """Return ``cand`` with a ``lift`` column computed against ``ref``."""
    out = cand.copy()
    out["lift"] = [lift(ref, r.TIR, r.t54) for r in cand.itertuples()]
    return out


def summarize_mechanisms(ref: pd.DataFrame, cand: pd.DataFrame,
                         mechanism: str = "mechanism",
                         multiplier: str = "multiplier") -> pd.DataFrame:
    """Aggregate per-point lift into a per-mechanism table.

    ``cand`` must carry a ``mechanism`` column (one row per ISF-multiplier point).
    Returns, per mechanism: ``lift_mean`` / ``lift_median`` (the robust ranking
    statistics — sort by these), ``frac_pos`` (fraction of the sweep on the
    better side), and ``lift_best`` with ``best_mult`` (best-of-sweep peak and the
    ISF multiplier where it occurs — secondary; jitter-inflated). Sorted by
    ``lift_mean`` descending.
    """
    c = add_lift(ref, cand)
    rows = []
    for name, g in c.groupby(mechanism):
        best = g.loc[g["lift"].idxmax()]
        rows.append({
            mechanism: name,
            "lift_mean": g["lift"].mean(),
            "lift_median": g["lift"].median(),
            "frac_pos": (g["lift"] > 0).mean(),
            "lift_best": best["lift"],
            "best_mult": best[multiplier] if multiplier in g.columns else float("nan"),
        })
    return pd.DataFrame(rows).sort_values("lift_mean", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- #
#  Plot                                                                       #
# --------------------------------------------------------------------------- #

def plot_sweeps(ref: pd.DataFrame, cand: pd.DataFrame,
                out: str | Path = "frontier_sweeps.png",
                field: Optional[dict] = None,
                mechanism: str = "mechanism", multiplier: str = "multiplier",
                mark_mult: float = 1.0,
                ref_label: str = "insulin-needs sweep (reference)",
                label_ref_points: bool = True,
                ylim: tuple[float, float] = (0.0, 1.5),
                deployed: Optional[dict] = None,
                ref_deployed: Optional[tuple] = None,
                title: str = "Candidate sweeps vs reference"):
    """Plot the reference and each candidate *mechanism* as a swept LINE, on the
    standard axes (t<54 up = worse — via :func:`plotting.tir_t54_axes`, never
    inverted). Every line is ordered by its **sweep multiplier** (insulin-needs or
    ISF, per the ``multiplier`` column), not by TIR — a TIR-ordered line zig-zags on
    a non-monotonic sweep. Use THIS instead of hand-rolling sweep plots so the
    ordering and axis convention can't be gotten wrong. ``ref_label`` names the gray
    reference line (default "insulin-needs sweep (reference)" — the preferred
    baseline; pass "ISF sweep (reference)" if you swept ISF). ``mark_mult`` (default
    1.0) drops a black-edged square on each line at that multiplier (the deployed
    point). ``ref``/``cand`` need TIR, t54 and a ``multiplier`` column (or an index
    like ``m1.05`` to parse it from).

    ``ylim`` keeps the standard 0-1.5 t<54 window by default. Widen it only to view
    a sweep pushed deep into the aggressive region (t<54 of several %), where the
    standard window would clip the points off-chart entirely; the orientation stays
    t<54-up either way. A widened window is an exploration view, not the house plot
    — the 0-1.5 window is what therapy claims get read on.

    ``deployed`` ({mechanism_name: (TIR, t54)}) and ``ref_deployed`` ((TIR, t54)) let a
    curve's deployed point (typically the insulin-needs=1.0 / ISF×1.0 point) be shown
    even when it sits above ``ylim``: a caret at the top edge (at its TIR) plus a
    color-matched label above the frame — so the off-chart value isn't silently lost
    without widening (and distorting) the sub-1% view. Points inside ``ylim`` are
    ignored (mark them with ``mark_mult`` instead).

    Returns the saved path.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _off_idx = [0]
    def _offlabel(tir, t54, color, tag):
        """Draw a deployed (f=1.0) point: an on-chart square if within ylim, else a
        caret at the top edge + a color-matched label above the frame. Returns True
        iff an on-chart square was drawn (so the legend can advertise the square)."""
        if tir is None or t54 is None:
            return False
        if t54 <= ylim[1]:
            ax.scatter([tir], [t54], s=110, marker="s", facecolor=color, edgecolor="k",
                       linewidth=1.2, zorder=7)
            return True
        ax.scatter([tir], [ylim[1]], marker="^", s=55, color=color, edgecolor="k",
                   linewidth=0.6, zorder=9, clip_on=False)
        ax.annotate(f"{tag}@1.0 → {tir:.0f}/{t54:.2f}", xy=(tir, ylim[1]),
                    xytext=(0, 9 + _off_idx[0] * 12), textcoords="offset points",
                    ha="center", va="bottom", fontsize=7.5, color=color, fontweight="bold",
                    zorder=9, clip_on=False)
        _off_idx[0] += 1
        return False

    def _ordered(frame):
        m = _multiplier_of(frame)
        f = frame.copy()
        f["_m"] = m if m is not None else frame["TIR"].to_numpy(float)
        return f.sort_values("_m")

    def _mark(ax, frame, color):
        hit = frame[np.isclose(frame["_m"], mark_mult)]
        if len(hit):
            ax.scatter(hit["TIR"], hit["t54"], s=110, marker="s",
                       facecolor=color, edgecolor="k", linewidth=1.2, zorder=7)
            return True
        return False

    # Any SWEEP point that craters above ylim (t<54 > ceiling) is drawn as a caret at
    # the top edge (at its TIR, color-matched) and listed in an info box — so the value
    # isn't silently clipped, WITHOUT widening the sub-1.5% view. (Distinct from the
    # `deployed`/`_offlabel` path, which handles only the single ×1.0 point.)
    _offchart: list[tuple] = []
    def _catch_off(frame, color, name):
        for _, row in frame.iterrows():
            if row["t54"] > ylim[1]:
                ax.scatter([row["TIR"]], [ylim[1]], marker="^", s=42, color=color,
                           edgecolor="k", linewidth=0.5, zorder=9, clip_on=False)
                _offchart.append((str(name), float(row["_m"]), float(row["t54"]), color))

    fig, ax = plt.subplots(figsize=(12, 8))
    r = _ordered(ref.dropna(subset=["TIR", "t54"]))
    ax.plot(r["TIR"], r["t54"], "o-", color="#888", lw=2, zorder=3, label=ref_label)
    marked = _mark(ax, r, "#888")
    _catch_off(r, "#888", ref_label)
    if ref_deployed is not None:
        marked = _offlabel(ref_deployed[0], ref_deployed[1], "#888", "std") or marked
    if label_ref_points and _multiplier_of(r) is not None:      # annotate each ref vertex with its sweep value
        for _, row in r.iterrows():
            ax.annotate(f"{row['_m']:g}", (row["TIR"], row["t54"]), fontsize=7, color="#555",
                        xytext=(3, 3), textcoords="offset points", zorder=8)
    for name, g in cand.dropna(subset=["TIR", "t54"]).groupby(mechanism):
        g = _ordered(g)
        line, = ax.plot(g["TIR"], g["t54"], "o-", ms=4, lw=1.5, zorder=4, label=str(name))
        marked = _mark(ax, g, line.get_color()) or marked
        _catch_off(g, line.get_color(), name)
        if deployed is not None and str(name) in deployed:
            dp = deployed[str(name)]
            marked = _offlabel(dp[0], dp[1], line.get_color(), str(name)) or marked
    if field is not None:
        ax.scatter([field["TIR"]], [field["t54"]], s=300, marker="*", color="crimson",
                   edgecolor="k", linewidth=0.5, zorder=6, label="FIELD (real deployment)")
    if marked:   # only advertise the deployed square if one actually landed on-chart
        ax.scatter([], [], s=110, marker="s", facecolor="none", edgecolor="k",
                   linewidth=1.2, label=f"×{mark_mult:g} (deployed)")
    tir_t54_axes(ax, ylim=ylim)   # t54 up = worse; NEVER invert
    if _offchart:                 # info box: off-chart points (t<54 above the ceiling)
        rows_by_mech: dict[str, list] = {}
        colfor: dict[str, str] = {}
        for name, m, t54, color in sorted(_offchart, key=lambda x: (x[0], x[1])):
            rows_by_mech.setdefault(name, []).append(f"{m:g}→{t54:.2f}")
            colfor[name] = color
        y = 0.045
        ax.text(0.985, y + 0.02 + 0.05 * len(rows_by_mech), f"off-chart  (t<54 > {ylim[1]:g}):",
                transform=ax.transAxes, ha="right", va="bottom", fontsize=8.5,
                fontweight="bold", color="#333", zorder=11)
        for name in sorted(rows_by_mech, key=lambda n: -max(float(v.split('→')[1]) for v in rows_by_mech[n])):
            ax.text(0.985, y, f"{name}:  " + ", ".join(rows_by_mech[name]),
                    transform=ax.transAxes, ha="right", va="bottom", fontsize=8,
                    family="monospace", color=colfor[name], fontweight="bold", zorder=11,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor=colfor[name], alpha=0.85))
            y += 0.05
    ax.set_title(title)
    ax.legend(fontsize=9, loc="upper left")
    fig.tight_layout()
    fig.savefig(out, dpi=110, bbox_inches="tight")   # bbox_inches captures off-chart labels above the frame
    plt.close(fig)
    return out


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
                   label=f"{label} (lift {row['lift']:+.3f})")

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
