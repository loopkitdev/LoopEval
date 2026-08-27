"""Which glucose properties are TRAITS of a person, and which are just weather?

A trait varies across the population but not within one person over time. A state
does the opposite. The statistic that separates them is the intraclass
correlation: split every person's record into blocks, compute a feature per
block, and ask what share of the feature's total variance is *between* people
rather than *within* them.

    ICC = sigma^2_between / (sigma^2_between + sigma^2_within)

ICC near 1  — the feature is a stable property of the person. Measure it once and
              it still describes them months later; it can carry a patient class.
ICC near 0  — the feature is a state. A single measurement says almost nothing
              about the person, only about that week.

Everything here is computed from the raw CGM series alone, so it scales to any
donor with glucose regardless of what else was exported. Every process statistic
(autocorrelation, structure function, volatility) uses gap-aware runs at a
normalised 5-minute cadence, for the reasons documented in
`loopeval_analysis.volatility`.
"""
from __future__ import annotations

from typing import Iterable, Optional, Sequence

import numpy as np
import pandas as pd

from .volatility import EWMA, measurement_floor

ANALYSIS_CADENCE_MIN = 5.0
MIN_STEP_FRAC, MAX_STEP_FRAC = 0.8, 1.2

__all__ = ["block_features", "panel_block_features", "icc", "icc_table",
           "runs_from_series"]


# ────────────────────────────────────────────────────────────────────────────
# gap-aware, cadence-normalised runs
# ────────────────────────────────────────────────────────────────────────────
def runs_from_series(bg: pd.Series, cadence_min: float = ANALYSIS_CADENCE_MIN,
                     minlen: int = 12) -> tuple[list[np.ndarray], float]:
    """Contiguous runs of raw samples, subsampled to a common cadence.

    Sensors differ — some report every minute — and mixing cadences corrupts
    every increment statistic, so a faster stream is decimated rather than
    rescaled. Returns ``(runs, cadence)`` where each run is a 1-D array of
    glucose values spaced one cadence apart with no gaps.
    """
    bg = bg.dropna().sort_index()
    if len(bg) < minlen + 1:
        return [], cadence_min
    dt = bg.index.to_series().diff().dt.total_seconds() / 60.0
    native = float(np.round(np.nanmedian(dt) * 2) / 2) or cadence_min
    if native < cadence_min - 0.25:
        step = max(int(round(cadence_min / native)), 1)
        bg = bg.iloc[::step]
        dt = bg.index.to_series().diff().dt.total_seconds() / 60.0
        native = float(np.round(np.nanmedian(dt) * 2) / 2) or cadence_min
    ok = ((dt >= MIN_STEP_FRAC * native) & (dt <= MAX_STEP_FRAC * native)).to_numpy()
    v = bg.to_numpy()
    out, start = [], 0
    for i in range(1, len(v)):
        if not ok[i]:
            if i - start >= minlen:
                out.append(v[start:i])
            start = i
    if len(v) - start >= minlen:
        out.append(v[start:])
    return [r for r in out if len(r) >= minlen], native


def _lagged(runs: Sequence[np.ndarray], k: int) -> np.ndarray:
    d = [r[k:] - r[:-k] for r in runs if len(r) > k]
    return np.concatenate(d) if d else np.array([])


def _acf(step_runs: Sequence[np.ndarray], nlags: int) -> np.ndarray:
    allv = np.concatenate(step_runs) if step_runs else np.array([])
    if allv.size < 50:
        return np.full(nlags + 1, np.nan)
    mu, var = allv.mean(), allv.var()
    out = np.ones(nlags + 1)
    for k in range(1, nlags + 1):
        num, cnt = 0.0, 0
        for r in step_runs:
            if len(r) > k:
                num += float(((r[k:] - mu) * (r[:-k] - mu)).sum())
                cnt += len(r) - k
        out[k] = num / cnt / var if cnt and var > 0 else np.nan
    return out


def _hurst_and_noise(runs, cadence, mins=(5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 240)):
    """Structure-function fit: Var[dBG(tau)] = 2*sigma_meas^2 + C*tau^(2H).

    Returns (H_short, H_long, sigma_meas). The intercept is the measurement
    noise — a difference of a noisily-measured series cannot have vanishing
    variance as the horizon goes to zero.
    """
    mins = np.array([m for m in mins], dtype=float)
    var = np.full(len(mins), np.nan)
    for i, m in enumerate(mins):
        k = max(int(round(m / cadence)), 1)
        d = _lagged(runs, k)
        if len(d) >= 300:
            var[i] = d.var()
    ok = np.isfinite(var)
    if ok.sum() < 4:
        return np.nan, np.nan, np.nan
    sd = np.sqrt(var)

    def slope(mask):
        m = ok & mask
        if m.sum() < 3:
            return np.nan
        return float(np.polyfit(np.log(mins[m]), np.log(sd[m]), 1)[0])

    # noise: profile the exponent out of a 2-parameter fit on the short lags
    short = ok & (mins <= 60)
    best = (np.inf, np.nan)
    if short.sum() >= 4:
        x, y = mins[short], var[short]
        for H in np.linspace(0.35, 1.15, 81):
            A = np.vstack([np.ones_like(x), x ** (2 * H)]).T
            coef, *_ = np.linalg.lstsq(A, y, rcond=None)
            if coef[0] < 0 or coef[1] < 0:
                continue
            r = float(np.sum((A @ coef - y) ** 2))
            if r < best[0]:
                best = (r, coef[0])
    sigma = float(np.sqrt(max(best[1], 0) / 2.0)) if np.isfinite(best[1]) else np.nan
    return slope(mins <= 60), slope((mins >= 120) & (mins <= 240)), sigma


def _boxcox_lambda(x: np.ndarray, lams=np.linspace(-1.5, 1.5, 61)) -> float:
    x = x[np.isfinite(x) & (x > 0)]
    if len(x) < 200:
        return np.nan
    if len(x) > 40000:
        x = np.random.default_rng(0).choice(x, 40000, replace=False)
    logx = np.log(x)
    s = logx.sum()
    best, bll = np.nan, -np.inf
    for lam in lams:
        y = logx if abs(lam) < 1e-8 else (np.power(x, lam) - 1) / lam
        ll = -0.5 * len(x) * np.log(y.var()) + (lam - 1) * s
        if ll > bll:
            best, bll = float(lam), ll
    return best


def _circadian_amplitude(bg: pd.Series) -> float:
    """Amplitude of the 24-hour component, as a fraction of mean glucose.

    Deliberately timezone-free: the amplitude of a daily cycle does not depend
    on where the clock is set, only its phase does. That keeps this comparable
    across donors whose local offset is unknown.
    """
    b = bg.dropna()
    if len(b) < 2000:
        return np.nan
    t = b.index.view("int64") / 1e9
    w = 2 * np.pi / 86400.0
    c, s = np.cos(w * t), np.sin(w * t)
    y = b.to_numpy() - b.mean()
    A = np.vstack([c, s]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(np.hypot(*coef) / b.mean())


# ────────────────────────────────────────────────────────────────────────────
# per-block features
# ────────────────────────────────────────────────────────────────────────────
def block_features(bg: pd.Series, block: str = "7D",
                   min_samples: int = 1200,
                   sigma_measurement: Optional[float] = None) -> pd.DataFrame:
    """One row of glucose features per time block.

    `min_samples` at 5-min cadence: 1200 ≈ 4.2 days of a 7-day block, so a block
    is only scored when it is mostly present. Partial blocks bias the process
    statistics far more than the level statistics.
    """
    bg = bg.dropna().sort_index()
    if bg.empty:
        return pd.DataFrame()
    rows = []
    for start, chunk in bg.groupby(pd.Grouper(freq=block)):
        if len(chunk) < min_samples:
            continue
        runs, cad = runs_from_series(chunk)
        if not runs:
            continue
        steps = [np.diff(r) for r in runs if len(r) > 3]
        d1 = np.concatenate(steps) if steps else np.array([])
        if len(d1) < 500:
            continue

        h_s, h_l, sig_meas = _hurst_and_noise(runs, cad)
        floor = measurement_floor(sig_meas if np.isfinite(sig_meas) else 1.0)
        est = EWMA(lam=0.875, cadence_min=cad, burn_in=6, var_floor=floor)
        sg = np.concatenate(est.filter(steps))
        sg = sg[np.isfinite(sg) & (sg > 0)]

        a = _acf(steps, max(int(round(180 / cad)), 12))
        zc = next((k * cad for k in range(1, len(a)) if np.isfinite(a[k]) and a[k] < 0),
                  np.nan)
        aabs = _acf([np.abs(s) for s in steps], max(int(round(120 / cad)), 12))
        k60 = int(round(60 / cad))

        v = chunk.to_numpy()
        b = float(np.mean(np.abs(d1 - np.median(d1))))
        day = chunk.index.floor("D")
        dmean = chunk.groupby(day).mean()

        rows.append({
            "block": start, "n": len(chunk), "cadence": cad,
            # level and shape
            "bg_mean": float(np.mean(v)), "bg_sd": float(np.std(v)),
            "bg_cv": float(100 * np.std(v) / np.mean(v)),
            "bg_skew": float(pd.Series(v).skew()),
            "bg_iqr": float(np.percentile(v, 75) - np.percentile(v, 25)),
            "boxcox_lambda": _boxcox_lambda(v),
            "tir": float(100 * np.mean((v >= 70) & (v <= 180))),
            "t70": float(100 * np.mean(v < 70)),
            "t180": float(100 * np.mean(v > 180)),
            # increment shape
            "v_sd": float(np.std(d1)),
            "sd_over_mad": float(np.std(d1) / b) if b > 0 else np.nan,
            "v_kurtosis": float(pd.Series(d1).kurtosis()),
            "v_skew": float(pd.Series(d1).skew()),
            # process structure
            "hurst_short": h_s, "hurst_long": h_l,
            "sigma_meas": sig_meas,
            "acf_zero_min": zc,
            "acf_min": float(np.nanmin(a[1:])) if np.isfinite(a[1:]).any() else np.nan,
            "vol_cluster_60m": float(aabs[k60]) if k60 < len(aabs) else np.nan,
            # volatility distribution
            "sigma_med": float(np.median(sg)) if len(sg) else np.nan,
            "sigma_disp": float(np.percentile(sg, 90) / np.percentile(sg, 10))
                          if len(sg) > 50 else np.nan,
            # organisation of variance
            "between_day_frac": float(np.var(dmean.to_numpy()) / np.var(v))
                                if np.var(v) > 0 and len(dmean) > 2 else np.nan,
            "circadian_amp": _circadian_amplitude(chunk),
        })
    return pd.DataFrame(rows)


# ────────────────────────────────────────────────────────────────────────────
# trait vs state
# ────────────────────────────────────────────────────────────────────────────
def icc(df: pd.DataFrame, feature: str, subject: str = "alias",
        min_blocks: int = 3) -> dict:
    """One-way random-effects ICC(1) for `feature`, with a subject bootstrap.

    Unbalanced-design estimator: sigma^2_within = MSW, and
    sigma^2_between = (MSB - MSW) / k0 with k0 the standard correction for
    unequal group sizes. Negative variance estimates are clipped to zero, which
    is the usual convention and means "no detectable between-subject spread".
    """
    d = df[[subject, feature]].dropna()
    counts = d.groupby(subject)[feature].size()
    keep = counts[counts >= min_blocks].index
    d = d[d[subject].isin(keep)]
    if d[subject].nunique() < 3 or len(d) < 12:
        return {"feature": feature, "icc": np.nan, "n_subj": d[subject].nunique(),
                "n_obs": len(d), "lo": np.nan, "hi": np.nan}

    def _one(dd):
        g = dd.groupby(subject)[feature]
        n_i = g.size().to_numpy().astype(float)
        m_i = g.mean().to_numpy()
        k = len(n_i)
        N = n_i.sum()
        grand = float((n_i * m_i).sum() / N)
        ssb = float((n_i * (m_i - grand) ** 2).sum())
        ssw = float(sum(((dd[dd[subject] == s][feature] -
                          dd[dd[subject] == s][feature].mean()) ** 2).sum()
                        for s in dd[subject].unique()))
        if k < 2 or N - k <= 0:
            return np.nan
        msb, msw = ssb / (k - 1), ssw / (N - k)
        k0 = (N - (n_i ** 2).sum() / N) / (k - 1)
        if k0 <= 0:
            return np.nan
        vb = max((msb - msw) / k0, 0.0)
        return vb / (vb + msw) if (vb + msw) > 0 else np.nan

    point = _one(d)
    rng = np.random.default_rng(0)
    subs = d[subject].unique()
    boots = []
    for _ in range(400):
        pick = rng.choice(subs, len(subs), replace=True)
        dd = pd.concat([d[d[subject] == s].assign(**{subject: f"{s}_{i}"})
                        for i, s in enumerate(pick)])
        val = _one(dd)
        if np.isfinite(val):
            boots.append(val)
    lo, hi = (np.percentile(boots, [5, 95]) if len(boots) > 50 else (np.nan, np.nan))
    return {"feature": feature, "icc": point, "n_subj": int(d[subject].nunique()),
            "n_obs": int(len(d)), "lo": float(lo), "hi": float(hi)}


def icc_table(df: pd.DataFrame, features: Iterable[str],
              subject: str = "alias") -> pd.DataFrame:
    rows = [icc(df, f, subject=subject) for f in features]
    return pd.DataFrame(rows).sort_values("icc", ascending=False)


# ────────────────────────────────────────────────────────────────────────────
# insulin-side features (needs the full four-stream export, not glucose alone)
# ────────────────────────────────────────────────────────────────────────────
def panel_block_features(panel: pd.DataFrame, block: str = "7D",
                         min_rows: int = 1200) -> pd.DataFrame:
    """Per-block features that require dose, carb and therapy streams.

    Two families here answer different questions. The *physiology* group
    (insulin action, non-insulin appearance, the basal share of action) asks
    whether a person's metabolic operating point is stable. The *operation*
    group (carbs announced, manual boluses, automation share, settings churn)
    asks whether how they run the system is stable. They can easily differ:
    a person can be metabolically steady while changing their settings weekly,
    or the reverse.

    Settings columns are included deliberately. Their ICC is not a statement
    about physiology — a schedule is whatever the person last typed — but their
    WITHIN-person variance measures settings churn, which is a real behaviour.
    """
    from .dists import BIN_MIN, clean
    c = clean(panel)
    if c.empty:
        return pd.DataFrame()
    rows = []
    for start, ch in c.groupby(pd.Grouper(freq=block)):
        if len(ch) < min_rows:
            continue
        raw = panel.loc[ch.index.min():ch.index.max()]
        days = max((ch.index.max() - ch.index.min()).total_seconds() / 86400, 1e-9)
        basal_u = float(raw["basal_eff"].sum() * BIN_MIN / 60)
        bolus_u = float(raw["bolus_u"].sum())
        tdd = basal_u + bolus_u
        ia = ch["ia_abs"]
        cr, isf = ch["cr"], ch["isf"]
        carb_g = float(raw["carb_effect"].sum() /
                       max(isf.mean() / max(cr.mean(), 1e-9), 1e-9))
        rows.append({
            "block": start, "n": len(ch),
            # physiology / operating point
            "ia_abs_mean": float(ia.mean() * 12),               # mg/dL per hour
            "ice_abs_mean": float(ch["ice_abs"].mean() * 12),
            # scheduled stream only — the delivered-basal version would count a
            # temp-basal-strategy user's corrections as "basal"
            "ia_sched_share": float((ia - ch["ia_net"]).mean() / max(ia.mean(), 1e-9)),
            "iob_net_mean": float(ch["iob_net"].mean()),
            "corr_v_ia": float(np.corrcoef(ch["v"], ia)[0, 1])
                         if ch["v"].std() > 0 and ia.std() > 0 else np.nan,
            # how the person operates the system
            "tdd": tdd / days,
            "basal_frac": basal_u / max(tdd, 1e-9),
            "auto_frac_u": float(raw["auto_bolus_u"].sum() / max(bolus_u, 1e-9)),
            "carb_g_day": carb_g / days,
            "manual_bolus_day": float((raw["manual_bolus_u"] > 0).sum() / days),
            # settings — level is trivially personal; the WITHIN variance is churn
            "isf_mean": float(isf.mean()),
            "cr_mean": float(cr.mean()),
            "basal_sched_mean": float(ch["basal_sched"].mean()),
            "target_lo_mean": float(ch["target_lo"].mean()),
        })
    return pd.DataFrame(rows)
