"""Standard plot routines for ISF + outcome analyses.

Each function takes data and returns a Matplotlib Figure. No I/O — callers
decide whether to savefig() and where.
"""
from __future__ import annotations

from typing import Iterable, Mapping, Optional, Sequence

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def isf_and_outcomes(
    isf_series: Mapping[str, pd.Series],
    outcomes: pd.DataFrame,
    *,
    outcome_cols: Sequence[str] = ("tir_70_180", "t_below_70", "t_above_180", "mean_bg"),
    smooth_days: int = 7,
    figsize=(14, 10),
    title: Optional[str] = None,
    isf_ylim: Optional[tuple[float, float]] = (-20, 200),
) -> plt.Figure:
    """Multi-panel time series: ISF on top, daily outcomes below.

    Each ISF series is plotted as (1) a faint raw scatter and (2) a 7-day
    rolling mean of its daily-mean — so multi-week structure is visible without
    being drowned by hour-to-hour quantile-regression noise.

    isf_series: dict label → series indexed by datetime (sub-daily ok).
    outcomes: daily-indexed DataFrame.
    smooth_days: rolling mean over outcomes for visual readability.
    isf_ylim: clip the ISF panel so outlier fits don't squash the rest.
    """
    n_outcome = len(outcome_cols)
    fig, axes = plt.subplots(
        1 + n_outcome, 1,
        figsize=figsize,
        sharex=True,
        gridspec_kw={"height_ratios": [2] + [1] * n_outcome},
    )
    ax_isf = axes[0]
    color_cycle = plt.rcParams['axes.prop_cycle'].by_key()['color']
    for i, (label, s) in enumerate(isf_series.items()):
        s = s.dropna().sort_index()
        if s.empty:
            continue
        color = color_cycle[i % len(color_cycle)]
        # daily mean of the series (works whether sub-daily or already daily)
        if s.index.tz is not None:
            day_idx = s.index.tz_localize(None).normalize()
        else:
            day_idx = s.index.normalize()
        daily = s.groupby(day_idx).mean()
        smooth = daily.rolling(smooth_days, center=True, min_periods=1).mean()
        # raw scatter, faint
        ax_isf.plot(s.index, s.values, color=color, lw=0.3, alpha=0.15)
        # smoothed line, bold
        ax_isf.plot(smooth.index, smooth.values, color=color,
                    label=f"{label} ({smooth_days}d-mean)", lw=1.8)
    ax_isf.set_ylabel("ISF estimate\n(mg/dL/U)")
    ax_isf.legend(loc="upper left", fontsize=8, ncol=min(len(isf_series), 4))
    ax_isf.axhline(60, color="gray", lw=0.5, ls=":")
    if isf_ylim is not None:
        ax_isf.set_ylim(*isf_ylim)
    ax_isf.grid(alpha=0.2)
    if title:
        ax_isf.set_title(title)

    for ax, col in zip(axes[1:], outcome_cols):
        if col not in outcomes.columns:
            ax.text(0.5, 0.5, f"(no {col})", transform=ax.transAxes, ha="center")
            continue
        s = outcomes[col]
        if smooth_days > 1:
            s = s.rolling(smooth_days, center=True, min_periods=1).mean()
        ax.plot(s.index, s.values, lw=1.0, color="C3")
        ax.set_ylabel(_label_for(col))
        ax.grid(alpha=0.2)

    axes[-1].xaxis.set_major_locator(mdates.MonthLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    for lbl in axes[-1].get_xticklabels():
        lbl.set_rotation(0)
        lbl.set_ha("center")
    fig.tight_layout()
    return fig


def _label_for(col: str) -> str:
    return {
        "tir_70_180": "TIR 70-180\n(fraction)",
        "t_below_70": "Time <70\n(fraction)",
        "t_below_54": "Time <54\n(fraction)",
        "t_above_180": "Time >180\n(fraction)",
        "t_above_250": "Time >250\n(fraction)",
        "mean_bg": "Mean BG\n(mg/dL)",
        "auc_below_70": "AUC <70\n(mg/dL·min)",
        "auc_above_180": "AUC >180\n(mg/dL·min)",
        "gv_cv": "Glucose CV",
        "tdd": "TDD\n(U/day)",
    }.get(col, col)


def lag_correlation_grid(
    corr_table: pd.DataFrame,
    *,
    figsize=(8, 6),
    title: Optional[str] = None,
) -> plt.Figure:
    """Plot lagged-correlation curves from a wide DataFrame.

    `corr_table`: index = lag_days, columns = series labels, values = corr.
    """
    fig, ax = plt.subplots(figsize=figsize)
    for col in corr_table.columns:
        ax.plot(corr_table.index, corr_table[col], label=col, marker="o", ms=3)
    ax.axhline(0, color="gray", lw=0.5)
    ax.axvline(0, color="gray", lw=0.5, ls=":")
    ax.set_xlabel("lag (days; +ve = ISF leads outcome)")
    ax.set_ylabel("correlation")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8, loc="best")
    if title:
        ax.set_title(title)
    fig.tight_layout()
    return fig


def scatter_isf_vs_outcome(
    daily_joined: pd.DataFrame,
    isf_col: str,
    outcome_col: str,
    *,
    color_col: Optional[str] = None,
    figsize=(6, 5),
    title: Optional[str] = None,
) -> plt.Figure:
    """Day-level scatter of (ISF, outcome). Optional color by another column."""
    df = daily_joined[[isf_col, outcome_col] + ([color_col] if color_col else [])].dropna()
    fig, ax = plt.subplots(figsize=figsize)
    if color_col:
        sc = ax.scatter(df[isf_col], df[outcome_col], c=df[color_col], s=10, alpha=0.7, cmap="viridis")
        plt.colorbar(sc, ax=ax, label=color_col)
    else:
        ax.scatter(df[isf_col], df[outcome_col], s=10, alpha=0.5)
    if len(df) >= 3:
        m, b = np.polyfit(df[isf_col], df[outcome_col], 1)
        xs = np.linspace(df[isf_col].min(), df[isf_col].max(), 50)
        ax.plot(xs, m * xs + b, color="red", lw=1, ls="--",
                label=f"slope={m:.3g}")
        r = df[isf_col].corr(df[outcome_col])
        ax.legend(title=f"r={r:.2f}, n={len(df)}", fontsize=8)
    ax.set_xlabel(isf_col)
    ax.set_ylabel(outcome_col)
    ax.grid(alpha=0.2)
    if title:
        ax.set_title(title)
    fig.tight_layout()
    return fig


def isf_change_vs_outcome_change(
    daily_joined: pd.DataFrame,
    isf_col: str,
    outcome_col: str,
    *,
    delta_days: int = 7,
    figsize=(6, 5),
) -> plt.Figure:
    """Scatter of Δ(ISF over delta_days) vs Δ(outcome over delta_days).

    Answers: when ISF shifts, does the outcome shift in the same direction?
    Less spurious than raw level-vs-level since it strips slow trends.
    """
    df = daily_joined[[isf_col, outcome_col]].dropna().sort_index()
    delta = df.diff(delta_days).dropna()
    fig, ax = plt.subplots(figsize=figsize)
    ax.scatter(delta[isf_col], delta[outcome_col], s=10, alpha=0.5)
    if len(delta) >= 3:
        m, b = np.polyfit(delta[isf_col], delta[outcome_col], 1)
        xs = np.linspace(delta[isf_col].min(), delta[isf_col].max(), 50)
        ax.plot(xs, m * xs + b, color="red", lw=1, ls="--",
                label=f"slope={m:.3g}")
        r = delta[isf_col].corr(delta[outcome_col])
        ax.legend(title=f"r={r:.2f}, n={len(delta)}", fontsize=8)
    ax.axhline(0, color="gray", lw=0.5)
    ax.axvline(0, color="gray", lw=0.5)
    ax.set_xlabel(f"Δ {isf_col} ({delta_days}d)")
    ax.set_ylabel(f"Δ {outcome_col} ({delta_days}d)")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    return fig


def tir_t54_axes(ax, ylim=(0.0, 1.5), budget=1.0,
                 xlabel="TIR 70-180 (%)", ylabel="time <54 (%)"):
    """Standard LoopEval outcome axes (convention 2026-06-09):
      x = TIR (increasing right), y = time<54 (increasing up), y fixed 0-1.5.
      Better outcomes are toward the LOWER-RIGHT (high TIR, low severe-lows).
      Always plot points as (x=TIR, y=t54). Dotted line marks the soft t<54 budget.
    """
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_ylim(*ylim)
    if budget is not None:
        ax.axhline(budget, color="#7b1fa2", ls=":", lw=0.9, zorder=0)
    return ax
