"""Weighted match score: how far a simulated cohort (or one person's twins) sits from its real reference, statistic by
statistic, in units of how much real people differ, weighted by how much the statistic matters to an algorithm
comparison (LESSONS 492).

The KS count (validate.compare_blocks, "matched of 51") weights a sensor's kurtosis like time below 54 and turns each row
into pass / fail at p 0.05, which depends on the sample size. Here each statistic gets

  d50    the median gap (sim − real) / S, S = the real 10–90% spread / 2.563 (one between-window SD across donors)
  spread log of the sim / real 10–90% spread ratio
  gap    |d50| + 0.5 |spread|
  se     the bootstrap SE of d50 from the simulated sample; a gap inside 2 se is noise of the draw

Tiers (what decides the comparison; weights 3 / 2 / 1):
  1  outcome and what Loop sees: level, time in ranges, lows, insulin total, carb entries, the meal's 3-h change
  2  dynamics the controller reacts to: CV and skew, 5-min rate spread, day-to-day and circadian structure, delivery shape,
     user boluses
  3  the sensor's fingerprint and the distribution's shape: noise, tails, persistence, ACF, Box-Cox λ, wear

    python -m loopeval_analysis.patient_sim.score RUN [RUN ...] [--real BLOCKS.csv] [--yardstick compare_pilot.csv]

A cohort run is scored against its own compare_pilot.csv (the donors' pooled 13-day blocks). With --real (one person's
13-day blocks, a twin) the reference quantiles come from that file and S from --yardstick (a cohort run's
compare_pilot.csv), so every run is measured on the same donor spread.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .validate import INSTRUMENT

TIER = {
    1: ["bg_mean", "tir", "t180", "t70", "t54", "lows_per_day", "p_reach54", "min_below70", "tdd",
        "carb_entries_per_day", "meal_d3h", "act_net20", "act_net20_hi"],
    2: ["bg_cv", "bg_skew", "v_sd", "between_day_frac", "circadian_amp", "vol_cluster_60m", "sigma_disp", "zero_frac",
        "med_nonzero", "p99", "conc1", "day_night", "tdd_cv", "ac1", "night_cv", "user_boluses_per_day",
        "manual_u_day",
        # what moves glucose (lifestats.py, LESSONS 494): meal absorption, unlogged rises, falls, activity and its coupling
        "unann_pulses_day", "pulse_peak_h", "pulse_dur_h", "pulse_peak_per_g", "unl_rises_day", "unl_rise_rate",
        "entry_fast_fall", "fast_fall_share", "ice_dip_day", "ice_dip_day_share", "workouts_week", "workout_dur",
        "workout_mets", "workout_after_meal"],
    3: ["boxcox_lambda", "sd_over_mad", "v_kurtosis", "v_skew", "hurst_short", "hurst_long", "sigma_meas",
        "acf_zero_min", "acf_min", "wear"],
}
WEIGHT = {1: 3.0, 2: 2.0, 3: 1.0}
TIER_OF = {s: t for t, ss in TIER.items() for s in ss}
Z90 = 2.563          # 10–90% width of a normal in SDs
NB = 300


def _q(x) -> np.ndarray:
    return np.percentile(x, [10, 50, 90])


def _scale(p10: float, p90: float, x=None) -> float:
    w = (p90 - p10) / Z90
    if w > 0: return w
    return float(np.std(x)) if x is not None and np.std(x) > 0 else np.nan   # discrete statistics whose 10–90% collapse


def _meal_rows(run: Path, donor_meals: Path | None) -> list[dict]:
    """The bolused isolated meal's 3-h change (meal_response.py), on the ice labeller's meals (meal_response_labeled.csv,
    like for like with the donors' entries): the run's median against the donors' per-person medians."""
    mr = run / "meal_response_labeled.csv"
    if donor_meals is None or not mr.exists() or not donor_meals.exists(): return []
    m = pd.read_csv(mr, index_col=0)
    col = m.columns[0]
    if "d3h_med" not in m.index: return []
    d = pd.read_csv(donor_meals)
    d = d[d.grams >= 10].groupby("alias").d3h.median()
    rq = _q(d); S = _scale(rq[0], rq[2], d)
    s50 = float(m.loc["d3h_med", col])
    return [dict(stat="meal_d3h", group="all", n_sim=int(m.loc["people", col]), real_p10=rq[0], real_p50=rq[1],
                 real_p90=rq[2], sim_p10=np.nan, sim_p50=s50, sim_p90=np.nan, S=S, d50=(s50 - rq[1]) / S,
                 spread=np.nan, se=np.nan)]


def gaps(sim: pd.DataFrame, ref: pd.DataFrame, yard: pd.DataFrame, seed: int = 0) -> pd.DataFrame:
    """Per statistic and sensor group. `ref`: reference quantiles (stat, group, real_p10/50/90); `yard`: the same columns,
    the donor spread S is taken from."""
    rng = np.random.default_rng(seed)
    ref = ref.set_index(["stat", "group"]); yard = yard.set_index(["stat", "group"])
    rows = []
    for (st, g), r in ref.iterrows():
        if st not in TIER_OF or st not in sim: continue
        s = sim.loc[sim.sensor == g, st] if g != "all" else sim[st]
        s = s.dropna().to_numpy()
        if len(s) < 3: continue
        y = yard.loc[(st, g)] if (st, g) in yard.index else (yard.loc[(st, "all")] if (st, "all") in yard.index else None)
        if y is None: continue
        S = _scale(y.real_p10, y.real_p90)
        if not np.isfinite(S): continue
        sq = _q(s)
        boot = np.median(rng.choice(s, (NB, len(s))), axis=1)
        rw, sw = r.real_p90 - r.real_p10, sq[2] - sq[0]
        rows.append(dict(stat=st, group=g, n_sim=len(s), real_p10=r.real_p10, real_p50=r.real_p50, real_p90=r.real_p90,
                         sim_p10=sq[0], sim_p50=sq[1], sim_p90=sq[2], S=S, d50=(sq[1] - r.real_p50) / S,
                         spread=np.log(sw / rw) if rw > 0 and sw > 0 else np.nan, se=float(np.std(boot)) / S))
    return pd.DataFrame(rows)


def summarize(G: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    G = G.copy()
    G["tier"] = G.stat.map(TIER_OF)
    G["gap"] = G.d50.abs() + 0.5 * G.spread.abs().fillna(0)
    G["noise"] = (G.d50.abs() <= 2 * G.se).fillna(False)
    # one value per statistic: sensor groups pooled by their simulated sample size
    P = G.groupby("stat").apply(lambda x: pd.Series(dict(tier=x.tier.iloc[0], gap=np.average(x.gap, weights=x.n_sim),
                                                          d50=np.average(x.d50, weights=x.n_sim))), include_groups=False)
    P["w"] = P.tier.map(WEIGHT)
    out = {f"tier{t}": float(P.loc[P.tier == t, "gap"].mean()) for t in (1, 2, 3)}
    out["score"] = float(np.average(P.gap, weights=P.w))
    out["close"] = int((P.gap <= 0.25).sum()); out["n"] = len(P)
    return G, out


def score_run(run: Path, real: Path | None = None, yardstick: Path | None = None, donor_meals: Path | None = None):
    sim = pd.read_csv(run / "sim_stats.csv")
    if real is None:
        cp = pd.read_csv(run / "compare_pilot.csv")
        if (run / "life_stats.csv").exists() and (run / "compare_life.csv").exists():   # lifestats.py rows
            ls = pd.read_csv(run / "life_stats.csv").drop(columns=["template", "sensor"], errors="ignore")
            sim = sim.merge(ls, on="name", how="left")
            cp = pd.concat([cp, pd.read_csv(run / "compare_life.csv")], ignore_index=True)
        ref, yard = cp, cp
    else:
        B = pd.read_csv(real)
        yard = pd.read_csv(yardstick)
        sensor = sim.sensor.mode().iloc[0]
        rows = []
        for st in B.columns:
            if st not in TIER_OF: continue
            b = B[st].dropna()
            if len(b) < 3: continue
            q = _q(b)
            rows.append(dict(stat=st, group=sensor if st in INSTRUMENT else "all",
                             real_p10=q[0], real_p50=q[1], real_p90=q[2]))
        ref = pd.DataFrame(rows)
        sim = sim.assign(sensor=sim.sensor)
    G = gaps(sim, ref, yard)
    if real is None:
        G = pd.concat([G, pd.DataFrame(_meal_rows(run, donor_meals))], ignore_index=True)
    return G


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--real", help="one person's 13-day blocks (a twin's donor)")
    ap.add_argument("--yardstick", help="a cohort run's compare_pilot.csv: the donor spread S (needed with --real)")
    ap.add_argument("--donor-meals", default=str(Path.home() / ".loop-eval/runs/2026-10-15-additive-templates/meal_response_donors.csv"))
    ap.add_argument("--detail", action="store_true", help="print every statistic")
    a = ap.parse_args()
    pd.set_option("display.width", 220); pd.set_option("display.max_rows", 200)
    raw = {Path(r).name: score_run(Path(r), Path(a.real) if a.real else None, Path(a.yardstick) if a.yardstick else None,
                                   Path(a.donor_meals) if a.donor_meals else None) for r in a.runs}
    # the same statistics in every run, so the scores compare (the labelled meal table exists only where ice_check ran)
    common = set.intersection(*(set(G.stat) for G in raw.values()))
    summ, tabs = {}, {}
    for n, G in raw.items():
        tabs[n], summ[n] = summarize(G[G.stat.isin(common)])
    names = list(tabs)
    first = tabs[names[0]]
    T = first[["tier", "stat", "group", "real_p50"]].copy()
    for n in names:
        g = tabs[n].set_index(["stat", "group"])
        T[f"sim_{n}"] = [g.sim_p50.get(k, np.nan) for k in zip(T.stat, T.group)]
        T[f"d50_{n}"] = [g.d50.get(k, np.nan) for k in zip(T.stat, T.group)]
        T[f"gap_{n}"] = [g.gap.get(k, np.nan) for k in zip(T.stat, T.group)]
    T = T.sort_values(["tier", "stat", "group"])
    show = T if a.detail else T[T.tier == 1]
    print(show.round(3).to_string(index=False))
    print()
    print(pd.DataFrame(summ).T.round(3).to_string())


if __name__ == "__main__":
    main()
