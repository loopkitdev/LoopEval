"""Static rule scoring — fast non-simulation evaluator for candidate dose rules.

A candidate rule is a function: state_df → Series of proposed Δ-doses at each
5-min step. Positive Δ = BOOST (extra insulin); negative Δ = CUT (less insulin).

This module scores those proposals against pre-computed
`hole_no_future` (max safe BOOST) and `excess_no_future` (required CUT to
prevent observed lows) on the observed BG trace.

Key safety semantics:

  • BOOST step (Δ > 0): SAFE iff Δ ≤ hole_no_future. Otherwise UNSAFE
    (would have driven BG below the safety floor in the next 6h).

  • CUT step (Δ < 0): never unsafe in the hypo sense (less insulin can't cause
    a low). Effectiveness is measured against excess_no_future at steps where
    a low was coming.

  • SILENT step (Δ = 0) at a step with non-zero hole or excess: missed
    opportunity (no harm, but the metric thinks the rule should have acted).

What this evaluator IS:
  • A static counterfactual — assumes the observed BG trajectory would be
    unchanged by small/local dose modifications.
  • Therefore correct as an upper bound for small additive/subtractive rules
    that don't materially change the IOB pipeline.
  • Fast: scoring a year of 5-min steps is a few vectorized operations.

What it ISN'T:
  • A simulator. Large structural changes (e.g., "double all boluses") will
    cause counterfactual BG to diverge — the static metric becomes unreliable.
  • A TIR estimator. Per-step Δ-vs-oracle agreement; doesn't compute outcome
    TIR / time-low / AUC.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class RuleScore:
    """Aggregate result of scoring a candidate rule."""
    # Identification
    name: str
    n_steps: int
    n_days: float

    # Per-step categories (sum to n_steps)
    n_boost_safe: int
    n_boost_unsafe: int
    n_cut_effective: int          # cut covered the excess
    n_cut_partial: int            # cut < excess (insufficient)
    n_cut_when_no_excess: int     # cut at a step where excess = 0 (not unsafe, just unhelpful)
    n_quiet_with_hole: int        # rule silent, hole > threshold (missed boost opportunity)
    n_quiet_with_excess: int      # rule silent, excess > threshold (missed cut opportunity)
    n_quiet_no_opportunity: int   # rule silent, hole≈0 and excess≈0 (correct quiet)

    # Magnitudes
    total_boost_u: float          # total positive Δ over the period
    total_cut_u: float            # total |negative| Δ
    total_unsafe_severity_u: float  # sum of (Δ − hole) at UNSAFE boost steps
    total_excess_covered_u: float   # sum of min(|Δ|, excess) at CUT steps where excess > 0
    total_excess_available_u: float # sum of excess across all steps with excess > 0
    total_hole_available_u: float   # sum of hole across all steps with hole > 0

    # Derived metrics
    @property
    def per_day_boost(self) -> float:    return self.total_boost_u / max(self.n_days, 1)
    @property
    def per_day_cut(self) -> float:      return self.total_cut_u / max(self.n_days, 1)
    @property
    def per_day_unsafe(self) -> int:     return int(round(self.n_boost_unsafe / max(self.n_days, 1)))
    @property
    def safety_rate(self) -> float:
        n_boost = self.n_boost_safe + self.n_boost_unsafe
        return (self.n_boost_safe / n_boost) if n_boost > 0 else float("nan")
    @property
    def boost_efficiency(self) -> float:
        """Fraction of TOTAL hole the rule captured via SAFE boosts.
        100% means we extracted every U of safe-boost opportunity."""
        return self.total_boost_u / max(self.total_hole_available_u, 1e-9)
    @property
    def excess_coverage(self) -> float:
        """Fraction of TOTAL excess the rule covered via CUTS.
        100% means we cut every U of low-preventing dose-reduction needed."""
        return self.total_excess_covered_u / max(self.total_excess_available_u, 1e-9)


def score_proposals(
    proposed_delta: pd.Series,
    hole_no_future: pd.Series,
    excess_no_future: pd.Series,
    *,
    name: str = "rule",
    hole_opportunity_threshold: float = 0.5,
    excess_opportunity_threshold: float = 0.1,
    boost_tolerance: float = 0.0,
    max_cut_per_step: Optional[pd.Series] = None,
) -> tuple[RuleScore, pd.DataFrame]:
    """Score a per-step Δ-dose series against the static-hole / static-excess metrics.

    Parameters
    ----------
    proposed_delta : pd.Series, indexed by step timestamp.
        Positive = boost (extra insulin), negative = cut (less insulin), zero = quiet.
    hole_no_future : pd.Series, max safe additional U at each step (>= 0).
    excess_no_future : pd.Series, required dose-reduction in U at each step (>= 0).
    hole_opportunity_threshold : a step with hole >= this is considered
        "boost opportunity" for the silent-with-opportunity count.
    excess_opportunity_threshold : same for excess.
    boost_tolerance : allow Δ to exceed hole by this margin before flagging UNSAFE.
    max_cut_per_step : optional pd.Series of max deliverable cut per step (>= 0 U).
        Typically = actual basal delivered per step (rate_uhr × step_hours). If
        provided, negative deltas are clipped: cuts are bounded by this
        deliverability ceiling. Boosts are not affected by this argument.
        Without this argument, the scorer assumes any proposed Δ takes full
        effect, which is unrealistic for cuts during Loop suspend windows.

    Returns
    -------
    (RuleScore, per_step_df) — aggregate + step-level details. The detail
    DataFrame contains the EFFECTIVE delta (post-clipping) so downstream
    analyses see what actually applied, not what was proposed.
    """
    # Align all three on a common index (use proposed_delta's index as primary).
    idx = proposed_delta.index
    hole = hole_no_future.reindex(idx, method="nearest",
                                   tolerance=pd.Timedelta("3min")).fillna(0.0)
    excess = excess_no_future.reindex(idx, method="nearest",
                                        tolerance=pd.Timedelta("3min")).fillna(0.0)
    delta = proposed_delta.fillna(0.0)

    # Apply deliverability cap to cuts: clip negative deltas at -max_cut_per_step.
    # Positive deltas pass through unchanged.
    if max_cut_per_step is not None:
        cap = max_cut_per_step.reindex(idx, method="nearest",
                                         tolerance=pd.Timedelta("3min")).fillna(0.0)
        # cap is the max allowable |cut| in U (>= 0). Clip Δ ≥ -cap (lower bound).
        delta = delta.clip(lower=-cap)

    # Step categories
    is_boost = delta > 0
    is_cut   = delta < 0
    is_quiet = (~is_boost) & (~is_cut)

    # Boost side
    boost_unsafe = is_boost & (delta > hole + boost_tolerance)
    boost_safe   = is_boost & ~boost_unsafe

    # Cut side
    cut_with_excess     = is_cut & (excess > excess_opportunity_threshold)
    cut_no_excess       = is_cut & (excess <= excess_opportunity_threshold)
    cut_effective       = cut_with_excess & (delta.abs() >= excess)
    cut_partial         = cut_with_excess & ~cut_effective

    # Silent missed-opportunity
    quiet_with_hole   = is_quiet & (hole >= hole_opportunity_threshold)
    quiet_with_excess = is_quiet & (excess >= excess_opportunity_threshold)
    quiet_no_opp      = is_quiet & ~quiet_with_hole & ~quiet_with_excess

    # Severities / magnitudes
    boost_total = delta.where(is_boost, 0.0).sum()
    cut_total   = delta.where(is_cut, 0.0).abs().sum()
    unsafe_severity = (delta - hole).where(boost_unsafe, 0.0).clip(lower=0).sum()
    # Excess covered: at cut steps, min(|delta|, excess) — bounded by what was needed.
    excess_covered = (
        pd.concat([delta.abs(), excess], axis=1).min(axis=1)
        .where(cut_with_excess, 0.0).sum()
    )
    excess_available = excess.where(excess > excess_opportunity_threshold, 0.0).sum()
    hole_available   = hole.where(hole > 0, 0.0).sum()

    n_days = (idx.max() - idx.min()).total_seconds() / 86400.0 if len(idx) > 1 else 1.0

    score = RuleScore(
        name=name,
        n_steps=len(idx),
        n_days=float(n_days),
        n_boost_safe=int(boost_safe.sum()),
        n_boost_unsafe=int(boost_unsafe.sum()),
        n_cut_effective=int(cut_effective.sum()),
        n_cut_partial=int(cut_partial.sum()),
        n_cut_when_no_excess=int(cut_no_excess.sum()),
        n_quiet_with_hole=int(quiet_with_hole.sum()),
        n_quiet_with_excess=int(quiet_with_excess.sum()),
        n_quiet_no_opportunity=int(quiet_no_opp.sum()),
        total_boost_u=float(boost_total),
        total_cut_u=float(cut_total),
        total_unsafe_severity_u=float(unsafe_severity),
        total_excess_covered_u=float(excess_covered),
        total_excess_available_u=float(excess_available),
        total_hole_available_u=float(hole_available),
    )

    # Per-step detail
    detail = pd.DataFrame({
        "proposed_delta": delta,
        "hole":           hole,
        "excess":         excess,
        "category":       np.select(
            [boost_safe, boost_unsafe, cut_effective, cut_partial,
             cut_no_excess, quiet_with_hole, quiet_with_excess, quiet_no_opp],
            ["boost_safe", "boost_unsafe", "cut_effective", "cut_partial",
             "cut_no_excess", "quiet_w_hole", "quiet_w_excess", "quiet_no_opp"],
            default="other",
        ),
    }, index=idx)
    return score, detail


def score_breakdown_by_context(detail: pd.DataFrame, state: pd.DataFrame,
                                axes: tuple = ("hour", "iob_zone", "bg_zone")) -> dict:
    """Per-context breakdown of rule categories. `state` must contain columns
    referenced by the axes (e.g. `bg`, `iob` for the zones)."""
    d = detail.copy()
    if "hour" in axes:
        d["hour"] = d.index.hour
    if "iob_zone" in axes and "iob" in state.columns:
        d["iob_zone"] = pd.cut(state["iob"].reindex(d.index),
            [-np.inf, 0.5, 1.5, 2.5, 3.5, 5.0, np.inf],
            labels=["<0.5","0.5-1.5","1.5-2.5","2.5-3.5","3.5-5",">5"])
    if "bg_zone" in axes and "bg" in state.columns:
        d["bg_zone"] = pd.cut(state["bg"].reindex(d.index),
            [-np.inf, 70, 100, 140, 180, 220, np.inf],
            labels=["<70","70-100","100-140","140-180","180-220",">220"])

    out = {}
    for ax in axes:
        if ax not in d.columns:
            continue
        crosstab = pd.crosstab(d[ax], d["category"])
        out[ax] = crosstab
    return out


def render_score(score: RuleScore, indent: str = "  ") -> str:
    """One-string summary of a RuleScore for terminal / report output."""
    lines = [
        f"Rule: {score.name}",
        f"{indent}period: {score.n_days:.1f} days, {score.n_steps:,} steps",
        f"{indent}BOOST: {score.n_boost_safe:,} safe, {score.n_boost_unsafe:,} UNSAFE "
        f"({score.per_day_unsafe}/day) — safety rate {score.safety_rate:.2%}",
        f"{indent}  delivered: {score.total_boost_u:.1f} U  ({score.per_day_boost:.2f} U/day)",
        f"{indent}  unsafe severity: {score.total_unsafe_severity_u:.2f} U total",
        f"{indent}  hole coverage: {score.boost_efficiency:.2%} of {score.total_hole_available_u:.0f} U available",
        f"{indent}CUT: {score.n_cut_effective:,} effective, {score.n_cut_partial:,} partial, "
        f"{score.n_cut_when_no_excess:,} when no excess",
        f"{indent}  delivered: {score.total_cut_u:.2f} U  ({score.per_day_cut:.3f} U/day)",
        f"{indent}  excess coverage: {score.excess_coverage:.2%} of {score.total_excess_available_u:.1f} U available",
        f"{indent}QUIET: {score.n_quiet_with_hole:,} with-hole-opportunity, "
        f"{score.n_quiet_with_excess:,} with-excess-opportunity, "
        f"{score.n_quiet_no_opportunity:,} correctly quiet",
    ]
    return "\n".join(lines)
