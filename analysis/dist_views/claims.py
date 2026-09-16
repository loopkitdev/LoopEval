#!/usr/bin/env python3
"""Every numeric claim in the distribution study, recomputed from current data.

Figures regenerate from data; prose does not (lesson 23). After any cohort
change the narrative has to be re-verified sentence by sentence, and the
sentences that read as settled background are exactly the ones that rot. This
script is the check: it prints each published number beside the value the
current tables and panels give, so a rewrite is a transcription rather than a
recollection.

Tier A reads the derived tables. Tier B recomputes from raw samples and is
slower; skip it with `--fast`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S                                        # noqa: E402

OUT = S.OUT
FAST = "--fast" in sys.argv


def hdr(t):
    print(f"\n{'='*78}\n{t}\n{'='*78}")


def q(x, name, fmt="{:.2f}", pcts=(10, 50, 90)):
    x = pd.Series(x).dropna().astype(float)
    if not len(x):
        print(f"  {name:38s} (empty)")
        return
    vals = [np.percentile(x, p) for p in pcts]
    lo, hi = x.min(), x.max()
    s = "  ".join(f"p{p}={fmt.format(v)}" for p, v in zip(pcts, vals))
    print(f"  {name:38s} n={len(x):3d}  {s}  range {fmt.format(lo)}–{fmt.format(hi)}")


# ---------------------------------------------------------------- tier A
co = S.cohort()
call = S.cohort("all")
core = S.cohort("core")
tgt = S.cohort("targeted")
w = pd.read_csv(OUT / "wholerecord.csv")
m = pd.read_csv(OUT / "merged.csv")

hdr("COHORT")
print(f"  cohort.csv rows                  {len(call)}")
print(f"  eligible (modelling)             {len(co)}")
print(f"  core / targeted (all rows)        {len(core)} / {len(tgt)}")
print(f"  core / targeted (eligible)        {co.stratum.eq('core').sum()} / {co.stratum.eq('targeted').sum()}")
print(f"  wholerecord.csv / merged.csv     {len(w)} / {len(m)}")
print(f"  four-stream (ia_sched_share)     {co['ia_sched_share'].notna().sum()}")
print("\n  source x stratum (eligible):")
print(co.groupby(["source", "stratum"]).size().unstack(fill_value=0).to_string().replace("\n", "\n    "))
print(f"\n  person-days (wholerecord, canonical) {int(w['days'].sum()):,}")
print(f"  person-weeks                     {int(w['days'].sum()/7):,}")
print(f"  (cohort.csv days, for comparison) {int(co['days'].sum()):,}")
q(co["days"], "record length, days", "{:.0f}")
q(co["wear"] * 100, "CGM wear % (distinct slots, source)", "{:.1f}")
q(co["coverage_pct"], "panel retained after cleaning %", "{:.1f}")
q(co["loop_frac"] * 100, "closed-loop fraction %", "{:.1f}")

hdr("OUTCOMES (eligible cohort)")
for c, f in [("tir", "{:.1f}"), ("bg_mean", "{:.0f}"), ("bg_cv", "{:.1f}"),
             ("t70", "{:.2f}"), ("t54", "{:.2f}"), ("t180", "{:.1f}"),
             ("tdd", "{:.0f}"), ("carb_g_day", "{:.0f}")]:
    if c in co:
        q(co[c], c, f)
print("\n  by stratum (median):")
print(co.groupby("stratum")[["tir", "bg_mean", "bg_cv", "t70", "carb_g_day", "tdd"]]
        .median().round(1).to_string().replace("\n", "\n    "))

hdr("WHAT THEY RUN")
for c in ("strategy", "archetype", "sensor", "pump", "algo"):
    if c in co:
        print(f"  {c:12s} {co[c].value_counts(dropna=False).to_dict()}")
print(f"\n  sensor known                     {co['sensor'].notna().sum()} of {len(co)}")
print("\n  strategy x archetype:")
print(co.groupby(["strategy", "archetype"]).size().unstack(fill_value=0).to_string().replace("\n", "\n    "))

hdr("SHAPE — the headline distributional numbers")
q(w["boxcox_lambda"], "Box-Cox lambda", "{:+.2f}")
q(w["sd_over_mad"], "SD/MAD of dBG", "{:.3f}")
q(w["v_kurtosis"], "excess kurtosis of dBG", "{:.2f}")
q(w["sigma_meas"], "sensor noise mg/dL", "{:.2f}")
q(m["noise_share"] * 100, "noise share of v-variance %", "{:.1f}")
q(w["hurst_short"], "Hurst 5-60 min", "{:.3f}")
q(w["hurst_long"], "Hurst 2-4 h", "{:.3f}")
q(w["acf_zero_min"], "ACF zero crossing, min", "{:.0f}")
q(w["acf_min"], "ACF minimum", "{:+.3f}")
q(w["between_day_frac"] * 100, "between-day variance %", "{:.0f}")
q(w["bg_skew"], "glucose skew", "{:.2f}")
q(w["v_skew"], "increment skew", "{:.2f}")
q(w["vol_cluster_60m"], "vol clustering at 60 min", "{:.3f}")
q(w["sigma_med"], "median local volatility", "{:.2f}")
q(w["sigma_disp"], "volatility dispersion", "{:.2f}")
q(w["circadian_amp"], "circadian amplitude", "{:.3f}")

print()
print(f"  above Gaussian SD/MAD 1.253      {(w.sd_over_mad > 1.253).sum()} of {len(w)}"
      f"  ({100*(w.sd_over_mad > 1.253).mean():.0f}%)")
print(f"  above Laplace SD/MAD 1.414       {(w.sd_over_mad > 1.414).sum()} of {len(w)}"
      f"  ({100*(w.sd_over_mad > 1.414).mean():.0f}%)")
print(f"  above Laplace kurtosis 3.0       {(w.v_kurtosis > 3.0).sum()} of {len(w)}"
      f"  ({100*(w.v_kurtosis > 3.0).mean():.0f}%)")
print(f"  Hurst_short > 0.5                {(w.hurst_short > 0.5).sum()} of {len(w)}"
      f"  ({100*(w.hurst_short > 0.5).mean():.0f}%)")
print(f"  Hurst_long  > 0.5                {(w.hurst_long > 0.5).sum()} of {len(w)}"
      f"  ({100*(w.hurst_long > 0.5).mean():.0f}%)")
print(f"  cadence values                   {w.cadence.value_counts().to_dict()}")

hdr("VOLATILITY ESTIMATORS (out of sample)")
vs = pd.read_csv(OUT / "vol_scores.csv")
vp = pd.read_csv(OUT / "vol_params.csv")
print(f"  people scored                    {vs.alias.nunique()}")
print("\n  median by estimator:")
g = vs.groupby("estimator")[["r2_logvar", "nll", "z_kurtosis", "z_sd",
                             "cover_99_gauss", "cover_99_laplace", "spread"]].median()
print(g.round(3).to_string().replace("\n", "\n    "))
best = (vs.loc[vs.groupby("alias")["r2_logvar"].idxmax(), ["alias", "estimator"]]
          .estimator.value_counts())
print(f"\n  best per person (r2_logvar)      {best.to_dict()}  of {vs.alias.nunique()}")
ew = vs[vs.estimator.eq("ewma")]
if len(ew):
    q(ew["cover_99_gauss"] * 100 if ew["cover_99_gauss"].max() <= 1 else ew["cover_99_gauss"],
      "EWMA 99% gaussian coverage", "{:.2f}")
    under = (ew["cover_99_gauss"] < (0.99 if ew["cover_99_gauss"].max() <= 1 else 99)).sum()
    print(f"  under-covering at nominal 99%    {under} of {len(ew)}")
    q(ew["sigma_p90"] / ew["sigma_p10"], "sigma p90/p10 within person", "{:.2f}")
hl = np.log(2) / -np.log(vp["lam"]) * vp["cadence"] if "lam" in vp else None
if hl is not None:
    q(hl, "EWMA half-life, min", "{:.0f}")
    print(f"  lam at grid edge (0.30 / 0.99)   "
          f"{(vp.lam <= 0.301).sum()} low, {(vp.lam >= 0.989).sum()} high")

hdr("TRAIT OR STATE")
ti = pd.read_csv(OUT / "trait_icc.csv")
tm = pd.read_csv(OUT / "trait_magnitude.csv")
print(f"  features / subjects / obs        {len(ti)}  {ti.n_subj.max()}  {ti.n_obs.max()}")
print(ti.sort_values("icc", ascending=False).round(3).to_string(index=False).replace("\n", "\n    "))
tii = pd.read_csv(OUT / "trait_icc_insulin.csv")
print(f"\n  INSULIN SIDE — features / subjects {len(tii)}  {tii.n_subj.max()}")
print(tii.sort_values("icc", ascending=False).round(3).to_string(index=False).replace("\n", "\n    "))
wc = OUT / "trait_icc_widecheck.csv"
if wc.exists():
    d = pd.read_csv(wc)
    print(f"\n  uniform-window check: max |delta| {d['delta'].abs().max():.3f}"
          f"   rank corr {d['all'].corr(d['uniform'], method='spearman'):.2f}")

hdr("INSULIN SIDE")
fs = co[co["ia_sched_share"].notna()]
q(fs["ia_sched_share"] * 100, "scheduled-basal share of action %", "{:.0f}")
q(fs["ia_basal_share"] * 100, "DELIVERED basal share of action %", "{:.0f}")
print("\n  by strategy (median):")
print(fs.groupby("strategy")[["ia_sched_share", "ia_basal_share", "basal_frac",
                              "auto_frac_u", "corr_v_ia"]].median().round(3)
        .to_string().replace("\n", "\n    "))
print("\n  counts by strategy:", fs.strategy.value_counts().to_dict())
q(fs["corr_v_ia"], "corr(velocity, insulin activity)", "{:+.2f}")
q(fs["var_expl_insulin"] * 100, "variance explained by insulin %", "{:.1f}")
if "ia_abs_mean" in fs and "ice_abs_mean" in fs:
    bal = (fs["ice_abs_mean"] - fs["ia_abs_mean"]).abs() / fs["ia_abs_mean"] * 100
    q(bal, "|appearance - action| / action %", "{:.2f}")
    q(fs["ice_abs_mean"], "non-insulin appearance mg/dL/h", "{:.0f}")

hdr("THE TWO DECISIONS (held-out)")
for nm in ("vol_lows.csv", "vol_highs.csv"):
    p = OUT / nm
    if not p.exists():
        print(f"  {nm}: missing")
        continue
    d = pd.read_csv(p)
    MIN_EV = 100 if nm == "vol_lows.csv" else 30   # figure 15's own floors
    print(f"\n  {nm}: rows {len(d)}  people {d.alias.nunique()}  (events floor {MIN_EV})")
    if "ratio" in d:
        ok = d[d["events"] >= MIN_EV]
        q(ok["ratio"], "  rate ratio", "{:.2f}")
        print(f"    intervals clearly >1            {(ok.ci_lo > 1).sum()} of {len(ok)}")
        print(f"    intervals clearly <1            {(ok.ci_hi < 1).sum()} of {len(ok)}")
    if "frac_high" in d:
        q(d["frac_high"] * 100, "  share of record above 180 %", "{:.1f}")
        q(d["frac_high_lowvol"] * 100, "  ... and calm %", "{:.1f}")

if FAST:
    print("\n[--fast: tier B skipped]")
    raise SystemExit(0)

# ---------------------------------------------------------------- tier B
hdr("TIER B — recomputed from raw samples")
aliases = list(co["alias"])
# The clamps arrive in mg/dL having round-tripped through mmol/L, so they land
# at 39.01 and 401.1 rather than 40 and 400 — test with a tolerance, and test
# the lattice on the SPACING of reported values, not on their integrality.
MM, CEIL, FLOOR, TOL = 18.0182, 401.0, 39.0, 0.5
ceil_share, floor_share, hit_floor, hit_ceil, never45, past400 = [], [], [], [], 0, 0
grid_whole, grid_mmol, mins, maxs = 0, 0, [], []
ratios = {2: [], 5: [], 10: [], 15: []}
cross = []
kurt_h = {30: [], 120: [], 240: []}
logsdmad, logkurt, ownkurt = [], [], []
quint_raw, quint_log = [], []
spikes, spike_days = [], []
cens_inc = []
for i, a in enumerate(aliases):
    try:
        runs, cad = S.raw_runs(a)
    except Exception as e:
        print(f"  ! {a}: {type(e).__name__}")
        continue
    if not runs:
        print(f"  ! {a}: no runs")
        continue
    v = np.concatenate(runs)
    ceil_share.append(100 * np.mean(v >= CEIL - TOL))
    floor_share.append(100 * np.mean(v <= FLOOR + TOL))
    hit_floor.append(bool((v <= FLOOR + TOL).any()))
    hit_ceil.append(bool((v >= CEIL - TOL).any()))
    never45 += int(v.min() > 45)
    past400 += int(v.max() > 402)
    mins.append(v.min())
    maxs.append(v.max())
    du = np.diff(np.unique(v))
    du = du[du > 1e-6]
    step = du.min() if len(du) else np.nan
    if abs(step - 1.0) < 0.05:
        grid_whole += 1
    elif abs(step - 10.0 / MM * 1.8) < 0.15 or abs(step - 1.8) < 0.15:
        grid_mmol += 1
    d5 = S.raw_delta(a, 5.0)
    if len(d5) > 200:
        for x in ratios:
            nr, nf = (d5 >= x).sum(), (d5 <= -x).sum()
            if nf >= 40 and nr >= 40:
                ratios[x].append(nr / nf)
        xs = np.arange(1, 25, 0.5)
        r = [( (d5 >= x).sum(), (d5 <= -x).sum()) for x in xs]
        cr = [xs[j] for j, (nr, nf) in enumerate(r) if nf >= 40 and nr >= 40 and nr / nf >= 1]
        if cr:
            cross.append(cr[0])
        cens = np.mean((np.abs(d5) > 0) & ((d5 == 0)))  # placeholder, real one below
        lv = np.concatenate([np.diff(np.log(r_[r_ > 0])) for r_ in runs if (r_ > 0).all()])
        if len(lv) > 200:
            logsdmad.append(lv.std(ddof=1) / np.mean(np.abs(lv - lv.mean())))
            logkurt.append(pd.Series(lv).kurtosis())
        # spread by glucose quintile, raw vs log
        base = np.concatenate([r_[:-1] for r_ in runs if len(r_) > 1])
        dd = np.concatenate([np.diff(r_) for r_ in runs if len(r_) > 1])
        ql = np.quantile(base, [0.2, 0.8])
        lo, hi = dd[base <= ql[0]], dd[base >= ql[1]]
        if len(lo) > 50 and len(hi) > 50:
            quint_raw.append(hi.std(ddof=1) / lo.std(ddof=1))
            ldd = np.concatenate([np.diff(np.log(r_)) for r_ in runs if len(r_) > 1 and (r_ > 0).all()])
            lbase = np.concatenate([r_[:-1] for r_ in runs if len(r_) > 1 and (r_ > 0).all()])
            if len(ldd) == len(lbase) and len(ldd) > 200:
                l_lo, l_hi = ldd[lbase <= ql[0]], ldd[lbase >= ql[1]]
                if len(l_lo) > 50 and len(l_hi) > 50:
                    quint_log.append(l_hi.std(ddof=1) / l_lo.std(ddof=1))
    for h in kurt_h:
        dh = S.raw_delta(a, float(h))
        if len(dh) > 500:
            kurt_h[h].append(pd.Series(dh).kurtosis())
    # increments touching a censoring limit
    b = np.concatenate([r_[:-1] for r_ in runs if len(r_) > 1])
    e = np.concatenate([r_[1:] for r_ in runs if len(r_) > 1])
    if len(b):
        cens_inc.append(100 * np.mean((b <= 40) | (b >= 400) | (e <= 40) | (e >= 400)))
    if i % 25 == 0:
        print(f"    ...{i}/{len(aliases)}", flush=True)

print()
q(mins, "per-person minimum mg/dL", "{:.0f}")
q(maxs, "per-person maximum mg/dL", "{:.0f}")
q(ceil_share, f"samples at the ceiling ({CEIL:.0f}) %", "{:.2f}")
q(floor_share, f"samples at the floor ({FLOOR:.0f}) %", "{:.2f}")
print(f"  reach the floor at all           {sum(hit_floor)} of {len(hit_floor)}")
print(f"  reach the ceiling at all         {sum(hit_ceil)} of {len(hit_ceil)}")
print(f"  never below 45                   {never45}")
print(f"  record runs past the ceiling     {past400}")
print(f"  lattice: whole mg/dL {grid_whole}   0.1 mmol/L {grid_mmol}"
      f"   no single lattice {len(mins) - grid_whole - grid_mmol}")
q(cens_inc, "increments touching a limit %", "{:.2f}")
print()
for x in sorted(ratios):
    q(ratios[x], f"rise/fall exceedance at {x} mg/dL", "{:.2f}")
q(cross, "ratio crosses 1 at, mg/dL", "{:.1f}")
print()
q(logsdmad, "SD/MAD of d(log BG)", "{:.3f}")
q(logkurt, "excess kurtosis of d(log BG)", "{:.2f}")
q(quint_raw, "increment SD, top/bottom quintile (raw)", "{:.2f}")
q(quint_log, "  same after a log", "{:.2f}")
print()
for h in sorted(kurt_h):
    q(kurt_h[h], f"excess kurtosis at {h} min", "{:.2f}")


# ---------------------------------------------------------------- tier C
hdr("TIER C — reporting range, lattice, despiking, gaps")
from loopeval_analysis import dists as D                  # noqa: E402
from loopeval_analysis.traits import (                    # noqa: E402
    MAX_MGDL_PER_MIN, split_impossible)

dropped, dropped_per_day, gap_frac = [], [], []
pre_lo, post_lo, pre_hi, post_hi, pre_z = [], [], [], [], []
for a in aliases:
    try:
        ds = S.datasets()[a]
        raw = S.clip_window(a, D._load_glucose(ds.glucose_path))
    except Exception:
        continue
    v = raw.to_numpy()
    if len(v) < 500:
        continue
    # despiking: how much does the impossible-step guard remove?
    dt = raw.index.to_series().diff().dt.total_seconds() / 60.0
    cad = max(float(np.round(dt.median() * 2) / 2), 0.5)
    ok = ((dt >= 0.8 * cad) & (dt <= 1.2 * cad)).to_numpy()
    runs0, start = [], 0
    for i in range(1, len(v)):
        if not ok[i]:
            if i - start >= 12:
                runs0.append(v[start:i])
            start = i
    if len(v) - start >= 12:
        runs0.append(v[start:])
    _, nd = split_impossible(runs0, cad, 12)
    days = (raw.index[-1] - raw.index[0]).total_seconds() / 86400
    dropped.append(nd)
    dropped_per_day.append(nd / max(days, 1))
    # gaps, and whether the last reading before one is unusual
    big = dt > 2.5 * cad
    gap_frac.append(100 * dt[big].sum() / max(dt.sum(), 1))
    idx = np.where(big.to_numpy())[0] - 1
    idx = idx[idx >= 0]
    if len(idx) > 20:
        last = v[idx]
        z = (last.mean() - v.mean()) / v.std(ddof=1)
        pre_z.append(z)
        pre_lo.append(100 * np.mean(last < 70)); post_lo.append(100 * np.mean(v < 70))
        pre_hi.append(100 * np.mean(last > 250)); post_hi.append(100 * np.mean(v > 250))

print(f"  despike limit                    {MAX_MGDL_PER_MIN} mg/dL/min"
      f"  ({MAX_MGDL_PER_MIN*5:.0f} per 5-min step)")
q(dropped, "impossible steps removed, per person", "{:.0f}")
q(dropped_per_day, "  ... per day", "{:.2f}")
print(f"  people with none                 {sum(1 for x in dropped if x == 0)} of {len(dropped)}")
print()
q(gap_frac, "time inside gaps %", "{:.1f}")
q(pre_z, "last reading before a gap, SD from mean", "{:+.2f}")
q(pre_lo, "  below 70 before a gap %", "{:.1f}")
q(post_lo, "  below 70 overall %", "{:.1f}")
q(pre_hi, "  above 250 before a gap %", "{:.1f}")
q(post_hi, "  above 250 overall %", "{:.1f}")
