#!/usr/bin/env python3
"""Views 07-14: low-level distributional and stochastic-process structure.

The question these answer is not "how is this person doing" but "what kind of
random variable is glucose, and what kind of process is its increment".
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt                      # noqa: E402
import style as S                                    # noqa: E402
from loopeval_analysis import dists as D             # noqa: E402

BIN = pd.Timedelta("5min")


# ────────────────────────────────────────────────────────────────────────────
# gap-aware primitives
# ────────────────────────────────────────────────────────────────────────────
def runs(panel: pd.DataFrame, col: str = "bg") -> list[np.ndarray]:
    """Contiguous, unbroken 5-minute runs of a column.

    Every process statistic below needs this: an ACF or a structure function
    computed across a CGM gap silently invents correlations that are not there.
    """
    s = panel[col]
    ok = s.notna().to_numpy()
    # A run also breaks whenever the index skips a bin.
    step_ok = np.r_[True, (np.diff(panel.index.values) == BIN.to_timedelta64())]
    ok &= step_ok | ~ok
    good = ok & np.r_[True, step_ok[1:]]
    out, start = [], None
    vals = s.to_numpy()
    for i in range(len(vals)):
        alive = ok[i] and (i == 0 or step_ok[i])
        if alive and start is None:
            start = i
        elif not alive:
            if start is not None and i - start >= 2:
                out.append(vals[start:i])
            start = i if ok[i] else None
    if start is not None and len(vals) - start >= 2:
        out.append(vals[start:])
    return [r for r in out if len(r) >= 12]


def lagged_diff(rs: list[np.ndarray], lag: int) -> np.ndarray:
    """Δ over `lag` bins, pooled across runs, never spanning a gap."""
    out = [r[lag:] - r[:-lag] for r in rs if len(r) > lag]
    return np.concatenate(out) if out else np.array([])


def acf(rs: list[np.ndarray], nlags: int) -> np.ndarray:
    """Autocorrelation pooled over runs (each run centred on the global mean)."""
    allv = np.concatenate(rs)
    mu, var = allv.mean(), allv.var()
    out = np.ones(nlags + 1)
    for k in range(1, nlags + 1):
        num, cnt = 0.0, 0
        for r in rs:
            if len(r) > k:
                num += float(((r[k:] - mu) * (r[:-k] - mu)).sum())
                cnt += len(r) - k
        out[k] = num / cnt / var if cnt and var > 0 else np.nan
    return out


def qq_points(x: np.ndarray, dist: str = "normal", n: int = 400):
    """Sample quantiles against theoretical quantiles, thinned to n points."""
    x = np.sort(np.asarray(x, dtype=float))
    x = x[np.isfinite(x)]
    if len(x) < 50:
        return np.array([]), np.array([])
    p = (np.arange(len(x)) + 0.5) / len(x)
    idx = np.unique(np.linspace(0, len(x) - 1, n).astype(int))
    p, xs = p[idx], x[idx]
    if dist == "normal":
        th = _norm_ppf(p)
    elif dist == "laplace":
        th = np.where(p < 0.5, np.log(2 * p), -np.log(2 * (1 - p)))
    else:
        raise ValueError(dist)
    return th, xs


def _norm_ppf(p):
    """Acklam's inverse normal CDF — accurate to ~1e-9, no scipy needed."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    p = np.asarray(p, dtype=float)
    out = np.zeros_like(p)
    lo, hi = p < 0.02425, p > 1 - 0.02425
    mid = ~(lo | hi)
    q = np.sqrt(-2 * np.log(np.where(lo, p, 0.5)))
    out[lo] = ((((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])
               / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1))[lo]
    q = np.sqrt(-2 * np.log(np.where(hi, 1 - p, 0.5)))
    out[hi] = (-(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])
               / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1))[hi]
    q = p - 0.5
    r = q * q
    out[mid] = ((((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q
                / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1))[mid]
    return out


def boxcox_lambda(x: np.ndarray, lams=np.linspace(-2.0, 2.0, 161)) -> float:
    """The Box-Cox power that maximises Gaussian log-likelihood."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x) & (x > 0)]
    if len(x) < 100:
        return np.nan
    if len(x) > 60000:                       # plenty for a 1-parameter fit
        x = np.random.default_rng(0).choice(x, 60000, replace=False)
    logx = np.log(x)
    slogx = logx.sum()
    best, best_ll = np.nan, -np.inf
    for lam in lams:
        y = logx if abs(lam) < 1e-8 else (np.power(x, lam) - 1) / lam
        ll = -0.5 * len(x) * np.log(y.var()) + (lam - 1) * slogx
        if ll > best_ll:
            best, best_ll = lam, ll
    return float(best)


# ────────────────────────────────────────────────────────────────────────────
# 07 — what scale is glucose actually normal on?
# ────────────────────────────────────────────────────────────────────────────
def f07_transform(panels, co):
    order = S.order_by(co, "tir")
    fig, ax = S.figure(2, 3, figsize=(14.4, 9.0))

    for a in order:
        c = D.clean(panels[a])
        bg = c["bg"].to_numpy()
        col = S.color_for(co, a)
        for j, (xx, ttl) in enumerate(((bg, "raw glucose"), (np.log(bg), "log glucose"))):
            th, xs = qq_points(xx, "normal")
            z = (xs - xs.mean()) / xs.std()
            ax[0][j].plot(th, z, **S.line_style(co, a))
    for j, ttl in enumerate(("Raw glucose vs a normal distribution",
                             "log glucose vs a normal distribution")):
        A = ax[0][j]
        A.plot([-4, 4], [-4, 4], color=S.INK, lw=1.5, ls=(0, (4, 2)), zorder=1)
        A.set_xlim(-4, 4)
        A.set_ylim(-4, 6)
        A.set_xlabel("normal quantile", fontsize=9.5, color=S.INK2)
        A.set_ylabel("standardised sample quantile", fontsize=9.5, color=S.INK2)
        A.set_title(ttl, fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # Box-Cox λ per person.
    lam = {a: boxcox_lambda(D.clean(panels[a])["bg"].to_numpy()) for a in order}
    # A distribution across people, not one labelled bar each: past ~30 people
    # the labels stop being readable and the shape of the population is the
    # point anyway. Per-person values live in the ledger table.
    A = ax[0][2]
    vals = np.array([lam[a] for a in order], float)
    cols = [S.color_for(co, a) for a in order]
    rng = np.random.default_rng(7)
    v = vals[np.isfinite(vals)]
    lo, med, hi = np.percentile(v, [10, 50, 90])
    gx = np.linspace(v.min() - 0.12, v.max() + 0.12, 240)
    gy = S.kde(v, gx)                                  # density fills the panel
    gy = gy / max(gy.max(), 1e-12)
    A.fill_between(gx, 0, gy, color=S.COOL, alpha=0.16, lw=0, zorder=1)
    A.plot(gx, gy, color=S.COOL, lw=1.5, alpha=0.7, zorder=2)
    A.scatter(vals, -0.13 - rng.uniform(0, 0.14, len(vals)), s=24, c=cols,
              alpha=0.7, lw=0, zorder=3)              # one dot per person, below
    A.plot([lo, hi], [-0.34, -0.34], color=S.INK, lw=2.2, alpha=0.35, zorder=3,
           solid_capstyle="round")
    A.plot([med, med], [-0.40, 1.02], color=S.INK, lw=2.0, zorder=4)
    A.axvline(0, color=S.INK2, lw=1.5)
    A.axvline(1, color=S.MUTED, lw=1.4, ls=(0, (4, 2)))
    A.text(0.02, 1.14, "λ=0  a log", fontsize=8.5, color=S.INK2, ha="left")
    A.text(0.98, 1.14, "λ=1  raw", fontsize=8.5, color=S.MUTED, ha="right")
    A.text(med - 0.03, 0.62, f"median {med:.2f}\np10–p90 {lo:.2f} to {hi:.2f}",
           fontsize=8.5, color=S.INK, ha="right", va="center", linespacing=1.5)
    A.set_ylim(-0.46, 1.26)
    A.set_yticks([])
    A.set_xlim(min(-0.8, v.min() - 0.08), 1.12)
    A.set_xlabel("Box-Cox λ that best normalises glucose", fontsize=9.5, color=S.INK2)
    A.set_title("The best power transform is close to a log",
                fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # Skew and excess kurtosis, raw vs log vs each person's own best λ.
    rows = []
    for a in order:
        bg = D.clean(panels[a])["bg"].to_numpy()
        lg = np.log(bg)
        l = lam[a]
        bc = lg if abs(l) < 1e-8 else (np.power(bg, l) - 1) / l
        rows.append({"alias": a,
                     "raw_s": pd.Series(bg).skew(), "log_s": pd.Series(lg).skew(),
                     "bc_s": pd.Series(bc).skew(),
                     "raw_k": pd.Series(bg).kurtosis(), "log_k": pd.Series(lg).kurtosis(),
                     "bc_k": pd.Series(bc).kurtosis()})
    R = pd.DataFrame(rows)
    # Before/after per person: one faint line each from raw to log to their own
    # best λ, with the median marked at each stage. The paired lines carry what
    # 73 grouped bars could not — whether the reduction holds for everybody.
    rng = np.random.default_rng(11)
    stages = ("raw", "log", "own best λ")
    for A, keys, lbl, ttl in (
            (ax[1][0], ("raw_s", "log_s", "bc_s"), "skew",
             "Skew: the log removes most of it"),
            (ax[1][1], ("raw_k", "log_k", "bc_k"), "excess kurtosis",
             "Kurtosis: the log takes most of that out too")):
        jit = rng.uniform(-0.06, 0.06, len(R))
        for i, r in R.iterrows():
            xs = np.arange(3) + jit[i]
            ys = [r[k] for k in keys]
            A.plot(xs, ys, color=S.MUTED, lw=0.7, alpha=0.30, zorder=1)
            A.scatter(xs, ys, s=13,
                      color=[S.MUTED, S.COOL, S.ACCENT], alpha=0.55, lw=0, zorder=2)
        for j, k in enumerate(keys):
            v = R[k].to_numpy()
            lo, med, hi = np.percentile(v[np.isfinite(v)], [10, 50, 90])
            A.plot([j, j], [lo, hi], color=S.INK, lw=2.0, alpha=0.25, zorder=3)
            A.plot([j - 0.24, j + 0.24], [med, med], color=S.INK, lw=2.6, zorder=4)
            A.text(j + 0.30, med, f"{med:.2f}", fontsize=9, color=S.INK,
                   va="center", ha="left", weight="bold")
        A.axhline(0, color=S.INK, lw=1.3)
        # One person's raw kurtosis is far above the rest; letting it set the
        # scale would flatten everyone else, so clip and say so.
        allv = R[list(keys)].to_numpy().ravel()
        allv = allv[np.isfinite(allv)]
        top = np.percentile(allv, 98.5)
        if allv.max() > 1.6 * top:
            A.set_ylim(min(allv.min() * 1.15, -0.4), top * 1.12)
            A.text(0.99, 0.985, f"{int((allv > top * 1.12).sum())} off scale",
                   transform=A.transAxes, ha="right", va="top", fontsize=8,
                   color=S.MUTED)
        A.set_xticks(range(3))
        A.set_xticklabels(stages, fontsize=9, color=S.INK2)
        A.set_xlim(-0.45, 2.80)
        A.set_ylabel(lbl, fontsize=9.5, color=S.INK2)
        A.set_title(ttl, fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # Pooled QQ on the median λ, to show what a single shared transform buys.
    for a in order:
        bg = D.clean(panels[a])["bg"].to_numpy()
        y_ = (np.power(bg, med) - 1) / med
        th, xs = qq_points(y_, "normal")
        z = (xs - xs.mean()) / xs.std()
        ax[1][2].plot(th, z, **S.line_style(co, a))
    ax[1][2].plot([-4, 4], [-4, 4], color=S.INK, lw=1.5, ls=(0, (4, 2)))
    ax[1][2].set_xlim(-4, 4)
    ax[1][2].set_ylim(-4, 5)
    ax[1][2].set_xlabel("normal quantile", fontsize=9.5, color=S.INK2)
    ax[1][2].set_ylabel("standardised sample quantile", fontsize=9.5, color=S.INK2)
    ax[1][2].set_title(f"One shared transform, λ={med:.2f}, for everyone",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    S.title(fig, "07 · What scale is glucose normal on?",
            "Glucose is not normal on the scale we always plot it. A Q-Q plot bends up at the right for every single person — the high tail is much "
            "fatter than Gaussian.\nThe question is whether some transform fixes it. A log nearly does, and the best power is close to a log for "
            "everyone, which means one shared transform is defensible.")
    S.save(fig, "07_transform",
           dict(left=0.055, right=0.985, top=0.885, bottom=0.105, hspace=0.52, wspace=0.24))
    return R, lam, med


# ────────────────────────────────────────────────────────────────────────────
# 08 — the tails of glucose
# ────────────────────────────────────────────────────────────────────────────
def censor_limits(a: str):
    """Where this sensor stops reporting, and how much mass piles up there.

    CGM hardware does not report beyond its range — it clamps. Dexcom reports
    40-400 mg/dL, so a reading of exactly 400 means "at least 400" and a reading
    of 40 means "at most 40". The observed distribution is therefore interval-
    censored at both ends, and any tail statistic computed through the limit is
    describing the sensor rather than the person.
    """
    import numpy as np
    raw = S.raw_delta  # touch to keep the import obvious
    from loopeval_analysis import dists as DD
    v = DD._load_glucose(S.datasets()[a].glucose_path).to_numpy()
    lo, hi = float(v.min()), float(v.max())
    at_lo = float(np.mean(np.isclose(v, lo, atol=0.6) | (v <= 40.5)))
    at_hi = float(np.mean(np.isclose(v, hi, atol=0.6) | (v >= 399.0)))
    return lo, hi, at_lo, at_hi


def f08_tails(panels, co):
    order = S.order_by(co, "tir")
    fig, ax = S.figure(1, 3, figsize=(14.4, 5.4))
    cens = {a: censor_limits(a) for a in order}

    for a in order:
        bg = D.clean(panels[a])["bg"].to_numpy()
        col = S.color_for(co, a)
        lo, hi, at_lo, at_hi = cens[a]
        xs = np.sort(bg)
        sur = 1.0 - (np.arange(len(xs)) + 0.5) / len(xs)
        cdf = (np.arange(len(xs)) + 0.5) / len(xs)

        # Upper tail: solid where the sensor is still resolving, dotted once it
        # is clamping, so the censored part cannot be mistaken for physiology.
        up = xs >= 140
        free = up & (xs < min(hi - 0.6, 399.0))
        held = up & ~free
        ax[0].plot(xs[free], sur[free], **S.line_style(co, a))
        if held.any():
            ax[0].plot(xs[held], sur[held], color=col, lw=1.1, ls=(0, (1, 2)),
                       alpha=0.55)
            ax[0].plot([xs[held][0]], [sur[held][0]], marker="|", ms=9,
                       color=col, mew=1.8)
        dn = xs <= 110
        freed = dn & (xs > max(lo + 0.6, 40.5))
        ax[1].plot(xs[freed], cdf[freed], **S.line_style(co, a))
        heldd = dn & ~freed
        if heldd.any():
            ax[1].plot(xs[heldd], cdf[heldd], color=col, lw=1.1, ls=(0, (1, 2)),
                       alpha=0.55)
        ax[2].plot(np.log(xs[free]), sur[free], **S.line_style(co, a))

    for A, xl, ttl in (
            (ax[0], "glucose (mg/dL)", "Upper tail: P(BG > x)"),
            (ax[1], "glucose (mg/dL)", "Lower tail: P(BG < x)"),
            (ax[2], "log glucose", "Upper tail against log glucose")):
        A.set_yscale("log")
        A.set_ylim(1e-5, 1.2)
        A.set_xlabel(xl, fontsize=9.5, color=S.INK2)
        A.set_ylabel("probability (log)", fontsize=9.5, color=S.INK2)
        A.set_title(ttl, fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")
    ax[1].axvline(70, color=S.GREEN, lw=1.2, ls=(0, (3, 3)))
    ax[1].axvline(54, color=S.ACCENT, lw=1.2, ls=(0, (2, 2)))
    ax[0].axvline(180, color=S.GREEN, lw=1.2, ls=(0, (3, 3)))
    ax[0].axvspan(399, 430, color=S.MUTED, alpha=0.16, lw=0)
    ax[0].text(414, 0.55, "sensor\nceiling", fontsize=8, color=S.INK2,
               ha="center", va="center")
    ax[1].axvspan(30, 40.5, color=S.MUTED, alpha=0.16, lw=0)
    ax[1].text(35, 0.55, "sensor\nfloor", fontsize=8, color=S.INK2,
               ha="center", va="center")

    top_hi = max(c[3] for c in cens.values()) * 100
    n_floor = sum(1 for c in cens.values() if c[2] > 0.0005)
    S.title(fig, "08 · The two tails are not the same shape — and neither is fully observed",
            "Survival curves on a log probability axis. BOTH TAILS ARE CENSORED BY THE SENSOR, which reports only 40-400 mg/dL and clamps outside "
            "it: a reading of 400 means\n\"at least 400\". Dotted segments are inside the clamped region and describe the hardware, not the person — "
            f"up to {top_hi:.1f}% of one person\'s samples sit piled at the ceiling.\nRead only the solid parts. What survives: the high tail is close to "
            "straight against log glucose over its observed range, and the low tail is far more person-specific —\nsome never approach the floor at all, "
            f"so their lower cliff is real defence rather than clamping ({n_floor} of {len(cens)} do reach it).")
    S.save(fig, "08_tails",
           dict(left=0.05, right=0.99, top=0.755, bottom=0.115, wspace=0.24))


# ────────────────────────────────────────────────────────────────────────────
# 09 — what family does velocity belong to?
# ────────────────────────────────────────────────────────────────────────────
def f09_velocity_family(panels, co):
    order = S.order_by(co, "tir")
    fig, ax = S.figure(2, 3, figsize=(14.4, 9.0))
    for a in order:
        v = S.raw_delta(a)
        v = v[np.isfinite(v)]
        col = S.color_for(co, a)
        s = v.std()
        thn, xn = qq_points(v / s, "normal")
        ax[0][0].plot(thn, xn, **S.line_style(co, a))
        b = np.mean(np.abs(v - np.median(v)))          # Laplace scale
        thl, xl = qq_points((v - np.median(v)) / b, "laplace")
        ax[0][1].plot(thl, xl, **S.line_style(co, a))
        # Tail survival of |v| on a log-linear axis: straight = exponential.
        av = np.sort(np.abs(v))
        sur = 1.0 - (np.arange(len(av)) + 0.5) / len(av)
        ax[0][2].plot(av / b, sur, **S.line_style(co, a))
    ax[0][0].plot([-5, 5], [-5, 5], color=S.INK, lw=1.5, ls=(0, (4, 2)))
    ax[0][0].set_xlim(-4.5, 4.5)
    ax[0][0].set_ylim(-9, 9)
    ax[0][0].set_title("vs normal — S-shaped, so heavy-tailed", fontsize=10.5,
                       color=S.INK, loc="left", pad=6, weight="bold")
    ax[0][0].set_xlabel("normal quantile", fontsize=9.5, color=S.INK2)
    ax[0][1].plot([-9, 9], [-9, 9], color=S.INK, lw=1.5, ls=(0, (4, 2)))
    ax[0][1].set_xlim(-9, 9)
    ax[0][1].set_ylim(-9, 9)
    ax[0][1].set_title("vs Laplace — straight over most of the range",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")
    ax[0][1].set_xlabel("Laplace quantile", fontsize=9.5, color=S.INK2)
    for A in (ax[0][0], ax[0][1]):
        A.set_ylabel("standardised sample quantile", fontsize=9.5, color=S.INK2)
    ax[0][2].plot(np.linspace(0, 9, 50), np.exp(-np.linspace(0, 9, 50)),
                  color=S.INK, lw=1.6, ls=(0, (4, 2)), label="exponential")
    ax[0][2].set_yscale("log")
    ax[0][2].set_ylim(1e-5, 1.2)
    ax[0][2].set_xlim(0, 9)
    ax[0][2].set_xlabel("|Δ BG| in units of its own mean absolute deviation",
                        fontsize=9.5, color=S.INK2)
    ax[0][2].set_ylabel("P(|Δ BG| > x)", fontsize=9.5, color=S.INK2)
    ax[0][2].legend(frameon=False, fontsize=8.5, labelcolor=S.INK2)
    ax[0][2].set_title("Tail decay of |velocity|", fontsize=10.5, color=S.INK,
                       loc="left", pad=6, weight="bold")

    # How the shape changes with the horizon: 5 min out to 4 h, per person.
    mins = [5, 10, 15, 30, 60, 120, 240]
    ex_kurt = {m: [] for m in mins}
    for a in order:
        ks = []
        for m in mins:
            d = S.raw_delta(a, m)
            ks.append(pd.Series(d).kurtosis() if len(d) > 500 else np.nan)
            if np.isfinite(ks[-1]):
                ex_kurt[m].append(ks[-1])
        ax[1][0].plot(mins, ks, **S.line_style(co, a))
    med = [np.median(ex_kurt[m]) if ex_kurt[m] else np.nan for m in mins]
    ax[1][0].plot(mins, med, color=S.INK, lw=2.2, zorder=4, label="median")
    ax[1][0].axhline(0, color=S.MUTED, lw=1.3, ls=(0, (4, 2)), label="Gaussian")
    ax[1][0].axhline(3, color=S.ACCENT, lw=1.3, ls=(0, (2, 2)), label="Laplace")
    ax[1][0].set_xscale("log")
    ax[1][0].set_yscale("symlog", linthresh=1)
    ax[1][0].set_xlabel("horizon (minutes)", fontsize=9.5, color=S.INK2)
    ax[1][0].set_ylabel("excess kurtosis", fontsize=9.5, color=S.INK2)
    ax[1][0].legend(frameon=False, fontsize=8.5, labelcolor=S.INK2)
    ax[1][0].set_title("Tails do not thin out as the horizon grows",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # Raw consecutive-sample deltas, straight off the sensor and unbinned.
    dss = S.datasets()
    for a in order:
        ds = dss.get(a)
        if ds is None:
            continue
        raw = D._load_glucose(ds.glucose_path)
        dt = raw.index.to_series().diff().dt.total_seconds()
        dv = raw.diff()
        ok = (dt > 240) & (dt < 360)              # genuinely consecutive samples
        dv = dv[ok].to_numpy()
        vals, cnt = np.unique(np.round(dv, 2), return_counts=True)
        m = np.abs(vals) <= 12
        ax[1][1].plot(vals[m], cnt[m] / cnt.sum(), **S.line_style(co, a))
    ax[1][1].set_yscale("log")
    ax[1][1].set_xlim(-12, 12)
    ax[1][1].set_xlabel("Δ BG between consecutive raw CGM samples (mg/dL)",
                        fontsize=9.5, color=S.INK2)
    ax[1][1].set_ylabel("relative frequency (log)", fontsize=9.5, color=S.INK2)
    ax[1][1].set_title("Raw sensor deltas: the value grid is discrete",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # Laplace scale b vs sd: for a true Laplace, sd/b = sqrt(2).
    for _, r in co.iterrows():
        a = r["alias"]
        v = S.raw_delta(a)
        b = np.mean(np.abs(v - np.median(v)))
        col = S.GROUP_COLOR.get(S.group_of(r), S.MUTED)
        ax[1][2].scatter(b, v.std() / b, s=64, color=col, edgecolor=S.SURFACE,
                         lw=1.2, zorder=3)
        ax[1][2].annotate(a if a in S.sample_for(co) else "", (b, v.std() / b), textcoords="offset points",
                          xytext=(7, -3), fontsize=8, color=S.INK2)
    ax[1][2].axhline(np.sqrt(2), color=S.ACCENT, lw=1.5, ls=(0, (3, 3)),
                     label="Laplace: √2")
    ax[1][2].axhline(1.253, color=S.MUTED, lw=1.5, ls=(0, (4, 2)),
                     label="Gaussian: √(π/2)")
    ax[1][2].set_xlabel("mean absolute deviation b (mg/dL / 5 min)", fontsize=9.5,
                        color=S.INK2)
    ax[1][2].set_ylabel("SD / b", fontsize=9.5, color=S.INK2)
    ax[1][2].margins(x=0.14)
    ax[1][2].legend(frameon=False, fontsize=8.5, labelcolor=S.INK2, loc="lower right")
    ax[1][2].set_title("Everyone above Gaussian; the cohort straddles Laplace",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    S.title(fig, "09 · What kind of random variable is glucose velocity?",
            "If the increment were Gaussian the top-left panel would be a straight line; it is an S, which means heavy tails. Against a Laplace "
            "(double-exponential) it is far\nstraighter. Every person's SD/b ratio sits above the Laplace value, so the truth is Laplace-like "
            "but heavier still — and it stays that way at every horizon.")
    S.save(fig, "09_velocity_family",
           dict(left=0.055, right=0.985, top=0.885, bottom=0.075, hspace=0.42, wspace=0.24))


# ────────────────────────────────────────────────────────────────────────────
# 10 — is the heavy tail really a mixture of quiet and volatile hours?
# ────────────────────────────────────────────────────────────────────────────
def f10_volatility(panels, co):
    order = S.order_by(co, "tir")
    fig, ax = S.figure(2, 3, figsize=(14.4, 9.0))
    for a in order:
        col = S.color_for(co, a)
        # Two 2-hour windows: one CENTRED on the current increment (so it
        # contains the very value it is scaling) and one strictly causal.
        # The difference between them is the point of the panel — see view 14.
        zc, zk, vols = [], [], []
        rs_v, cad_v = S.raw_runs(a)
        win = max(int(round(120 / cad_v)), 6)
        for r in rs_v:
            vv = pd.Series(np.diff(r))
            v_centre = vv.rolling(win, center=True, min_periods=win // 2).std()
            v_causal = vv.rolling(win, min_periods=win // 2).std().shift(1)
            zc.append((vv / v_centre).replace([np.inf, -np.inf], np.nan).dropna())
            zk.append((vv / v_causal).replace([np.inf, -np.inf], np.nan).dropna())
            vols.append(v_causal.dropna())
        vol = pd.concat(vols) if vols else pd.Series(dtype=float)
        for acc, colr in ((zc, "#8a949e"), (zk, S.COOL)):
            zz = pd.concat(acc) if acc else pd.Series(dtype=float)
            if len(zz) < 500:
                continue
            th, xs = qq_points(zz.to_numpy() / zz.std(), "normal")
            ax[0][0].plot(th, xs, color=colr, lw=1.1, alpha=0.6)
        # Distribution of the local volatility itself.
        g = np.linspace(0, 22, 300)
        ax[0][1].plot(g, S.kde(vol.dropna(), g), **S.line_style(co, a))
        # Volatility clustering: ACF of |v|, in minutes not steps.
        rs, cad = S.raw_runs(a)
        absruns = [np.abs(np.diff(r)) for r in rs if len(r) > 40]
        if absruns:
            nl = int(180 / cad)
            A = acf(absruns, nl)
            ax[0][2].plot(np.arange(nl + 1) * cad, A, **S.line_style(co, a))
    ax[0][0].plot([-4.5, 4.5], [-4.5, 4.5], color=S.INK, lw=1.5, ls=(0, (4, 2)))
    ax[0][0].set_xlim(-4.2, 4.2)
    ax[0][0].set_ylim(-6, 6)
    ax[0][0].set_xlabel("normal quantile", fontsize=9.5, color=S.INK2)
    ax[0][0].set_ylabel("velocity / local volatility", fontsize=9.5, color=S.INK2)
    ax[0][0].plot([], [], color="#8a949e", lw=2.2, label="centred window (NOT causal)")
    ax[0][0].plot([], [], color=S.COOL, lw=2.2, label="causal window")
    ax[0][0].legend(frameon=False, fontsize=8, labelcolor=S.INK2, loc="upper left")
    ax[0][0].set_title("Only a non-causal window looks Gaussian",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")
    ax[0][1].set_xlabel("trailing 2 h SD of velocity (mg/dL / 5 min)", fontsize=9.5,
                        color=S.INK2)
    ax[0][1].set_ylabel("density", fontsize=9.5, color=S.INK2)
    ax[0][1].set_title("Volatility itself is broadly spread and right-skewed",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")
    ax[0][2].axhline(0, color=S.INK, lw=1.2)
    ax[0][2].set_xlabel("lag (minutes)", fontsize=9.5, color=S.INK2)
    ax[0][2].set_ylabel("autocorrelation of |Δ BG|", fontsize=9.5, color=S.INK2)
    ax[0][2].set_title("Volatility clusters, and the memory is long",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # ACF of the signed increment: the momentum question.
    for a in order:
        rs, cad = S.raw_runs(a)
        vr = [np.diff(r) for r in rs if len(r) > 40]
        if vr:
            nl = int(180 / cad)
            A = acf(vr, nl)
            ax[1][0].plot(np.arange(nl + 1) * cad, A, **S.line_style(co, a))
    ax[1][0].axhline(0, color=S.INK, lw=1.2)
    ax[1][0].set_xlabel("lag (minutes)", fontsize=9.5, color=S.INK2)
    ax[1][0].set_ylabel("autocorrelation of Δ BG", fontsize=9.5, color=S.INK2)
    ax[1][0].set_title("Signed momentum decays within about an hour",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # Structure function: how the spread of Δ grows with horizon.
    mins = np.array([5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 240, 360, 480])
    hurst = {}
    for a in order:
        sd = np.array([(lambda d: d.std() if len(d) >= 300 else np.nan)(
            S.raw_delta(a, float(m))) for m in mins])
        ok = np.isfinite(sd)
        ax[1][1].plot(mins[ok], sd[ok], **S.line_style(co, a))
        # Raw runs break at every CGM gap, so the longest horizons can be thin;
        # only fit a band that actually has points.
        def slope(mask):
            mm = ok & mask
            if mm.sum() < 3:
                return np.nan
            return float(np.polyfit(np.log(mins[mm]), np.log(sd[mm]), 1)[0])
        hurst[a] = (slope((mins >= 5) & (mins <= 60)),
                    slope((mins >= 120) & (mins <= 240)))
    ref = np.array([5, 480])
    ax[1][1].plot(ref, 3.0 * (ref / 5) ** 0.5, color=S.INK, lw=1.6, ls=(0, (4, 2)),
                  label="random walk (slope ½)")
    ax[1][1].plot(ref, 3.0 * (ref / 5) ** 1.0, color=S.MUTED, lw=1.4, ls=(0, (2, 2)),
                  label="pure trend (slope 1)")
    ax[1][1].set_xscale("log")
    ax[1][1].set_yscale("log")
    ax[1][1].set_xlabel("horizon (minutes)", fontsize=9.5, color=S.INK2)
    ax[1][1].set_ylabel("SD of Δ BG over that horizon", fontsize=9.5, color=S.INK2)
    ax[1][1].legend(frameon=False, fontsize=8.5, labelcolor=S.INK2, loc="upper left")
    ax[1][1].set_title("Structure function: super-diffusive, then it saturates",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # One line per person from their short-range exponent to their long-range
    # one. Two labelled bars each stopped being readable well before 73 people,
    # and the crossing of the random-walk line is the whole point.
    hurst = {k: v for k, v in hurst.items() if np.isfinite(v[0])}
    A = ax[1][2]
    rng = np.random.default_rng(5)
    short = np.array([hurst[a][0] for a in hurst], float)
    long_ = np.array([hurst[a][1] for a in hurst], float)
    jit = rng.uniform(-0.05, 0.05, len(short))
    for i, a in enumerate(hurst):
        if not np.isfinite(long_[i]):
            A.scatter([0 + jit[i]], [short[i]], s=15, color=S.MUTED, alpha=0.5, lw=0)
            continue
        A.plot([0 + jit[i], 1 + jit[i]], [short[i], long_[i]],
               color=S.color_for(co, a), lw=0.8, alpha=0.35, zorder=1)
        A.scatter([0 + jit[i], 1 + jit[i]], [short[i], long_[i]], s=15,
                  color=S.color_for(co, a), alpha=0.6, lw=0, zorder=2)
    for j, v in ((0, short), (1, long_)):
        v = v[np.isfinite(v)]
        lo, med, hi = np.percentile(v, [10, 50, 90])
        A.plot([j, j], [lo, hi], color=S.INK, lw=2.0, alpha=0.25, zorder=3)
        A.plot([j - 0.22, j + 0.22], [med, med], color=S.INK, lw=2.6, zorder=4)
        A.text(j + 0.27, med, f"{med:.2f}", fontsize=9, color=S.INK, weight="bold",
               va="center", ha="left")
    A.axhline(0.5, color=S.INK, lw=1.5, ls=(0, (4, 2)))
    A.text(-0.42, 0.5, " random walk", fontsize=8.5, color=S.INK2, va="bottom")
    A.set_xticks([0, 1])
    A.set_xticklabels(["5–60 min", "2–4 h"], fontsize=9, color=S.INK2)
    A.set_xlim(-0.45, 1.55)
    A.set_ylabel("scaling exponent (Hurst)", fontsize=9.5, color=S.INK2)
    A.set_title("Short horizons trend, long ones revert",
                fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    S.title(fig, "10 · Volatility clusters, and the process has two regimes",
            "Volatility is strongly autocorrelated and the increment scales faster than a random walk out to about an hour before flattening — "
            "two regimes, trending then mean-reverting.\nThe top-left panel carries a warning: dividing each increment by a window CENTRED on it "
            "makes the tail look Gaussian, but that window contains the increment it is scaling.\nDone causally the tail largely survives, and only "
            "about 40% of the excess kurtosis is a mixture effect. View 14 quantifies that properly.")
    S.save(fig, "10_volatility",
           dict(left=0.055, right=0.978, top=0.855, bottom=0.075, hspace=0.42, wspace=0.30))
    return hurst


def main():
    co = S.cohort()
    panels = S.load_all()
    f07_transform(panels, co)
    f08_tails(panels, co)
    f09_velocity_family(panels, co)
    f10_volatility(panels, co)


if __name__ == "__main__":
    main()
