"""loopeval_analysis — reusable Python primitives for digging into LoopEval datasets.

Everything in here takes paths/options as arguments. No hardcoded hosts, no
hardcoded windows. Specific analyses live in per-experiment runs/ directories
and call into this package.
"""

from .glucose import (
    load_glucose_cache,
    load_doses_cache,
    daily_outcomes,
    daily_tdd,
    basal_delivery_timeline,
    DailyOutcomes,
    find_therapy_cache,
    scheduled_basal_profile,
    scheduled_basal_at,
    effective_delivery_rate,
)
from .isf_rolling import (
    load_isf_rolling_csv,
    load_isf_explore_csv,
    event_sensitivity_series,
    rolling_quantile_isf,
    rolling_multi_estimator,
    forward_glucose_features,
)
from .state_features import per_sample_state_features, boost_damp_score, apply_boost_guards
from .ice_isf_features import (
    ice_features, local_isf_features, ice_run_features, build_all_ice_isf_features,
)
from .extra_features import (
    meal_signature_features, dose_timing_features,
    bg_volatility_features, cyclic_time_features,
    build_all_extra_features,
)
from .causal_features import causal_cgm_features, LEAKY_COLUMNS
from .rule_scorer import (
    RuleScore, score_proposals, score_breakdown_by_context, render_score,
)
from .linear_what_if import (
    apply_delta_stream, WhatIfResult, outcomes, format_outcome_diff,
)
from .closed_loop_delta import (
    closed_loop_delta_sim, DeltaSimResult,
)
from . import ice_sim
from .insulin_hole import (
    insulin_hole, insulin_hole_two_horizons,
    insulin_excess, insulin_excess_two_horizons, insulin_excess_fair_attribution,
    score_proposed_deltas, hole_aggregate_stats,
)
from .align import align_on_daily_index
from . import plotting

__all__ = [
    "load_glucose_cache",
    "load_doses_cache",
    "daily_outcomes",
    "daily_tdd",
    "basal_delivery_timeline",
    "DailyOutcomes",
    "find_therapy_cache",
    "scheduled_basal_profile",
    "scheduled_basal_at",
    "effective_delivery_rate",
    "load_isf_rolling_csv",
    "load_isf_explore_csv",
    "event_sensitivity_series",
    "rolling_quantile_isf",
    "rolling_multi_estimator",
    "forward_glucose_features",
    "per_sample_state_features",
    "boost_damp_score",
    "apply_boost_guards",
    "ice_features",
    "local_isf_features",
    "ice_run_features",
    "build_all_ice_isf_features",
    "meal_signature_features",
    "dose_timing_features",
    "bg_volatility_features",
    "cyclic_time_features",
    "build_all_extra_features",
    "ice_sim",
    "insulin_hole",
    "insulin_hole_two_horizons",
    "insulin_excess",
    "insulin_excess_two_horizons",
    "insulin_excess_fair_attribution",
    "score_proposed_deltas",
    "hole_aggregate_stats",
    "align_on_daily_index",
    "plotting",
]
