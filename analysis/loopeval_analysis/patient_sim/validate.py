"""Score simulated people with the eda study's own statistics and compare against the donor cohort.

Per simulated person (`person_stats`), computed only on the closed-loop part (after LoopEval's
burn-in), the same quantities the eda tables hold for real donors:
  glucose   traits.block_features on the CGM the person's sensor reported (wholerecord.csv)
  outcomes  TIR, t<70, t<54, mean, CV (cohort.csv)
  insulin   delivery.py's definitions on what the pump DELIVERED in 5-min bins (delivery.csv),
            plus the day/night delivery ratio (eda L45: 1.65×, p10–p90 1.20–2.46)
  behavior  carb entries/day, user boluses/day (cohort.csv)
  lows      crossings below 70 per day, P(reach 54), minutes below 70 per crossing (ice L60)
  truth     true-BG TIR vs CGM TIR, carbs eaten, rescue grams — diagnostics with no field counterpart

`compare(sim, by="sensor")` sets each statistic's simulated distribution across people beside the
real one (same sensor family where the statistic is instrument-dependent, eda L33) and reports
p10 / p50 / p90 and a two-sample KS p-value. A gap is a missing or mis-specified component — never
a reason to add a fitted term (memory: no-mystery-terms).
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .. import traits as T
from .world import EPOCH

DIST = Path.home() / ".loop-eval/runs/2026-08-25-distributions"
INSTRUMENT = {"v_sd", "sd_over_mad", "v_kurtosis", "v_skew", "sigma_meas", "acf_min", "hurst_short"}
GLUCOSE_FEATS = ["bg_mean", "bg_cv", "bg_skew", "boxcox_lambda", "tir", "t70", "t180", "v_sd", "sd_over_mad",
                 "v_kurtosis", "v_skew", "hurst_short", "hurst_long", "sigma_meas", "acf_zero_min", "acf_min",
                 "vol_cluster_60m", "sigma_disp", "between_day_frac", "circadian_amp"]


def _series(minutes: pd.Series) -> pd.DatetimeIndex:
    return EPOCH + pd.to_timedelta(minutes, unit="m")


def lows_anatomy(cgm: pd.Series) -> dict:
    """Crossings below 70 on the reported CGM (ice L60's definitions, approximately)."""
    v = cgm.dropna()
    below = (v < 70).astype(int).to_numpy()
    starts = np.where(np.diff(below) == 1)[0] + 1
    days = (v.index[-1] - v.index[0]).total_seconds() / 86400 if len(v) > 1 else np.nan
    reach, mins = [], []
    vals = v.to_numpy(); tmin = (v.index - v.index[0]).total_seconds().to_numpy() / 60
    for s in starts:
        e = s
        while e < len(vals) and vals[e] < 70: e += 1
        seg = vals[s:e]
        reach.append(float(seg.min() < 54)); mins.append(tmin[min(e, len(vals) - 1)] - tmin[s])
    return dict(lows_per_day=len(starts) / days if days else np.nan,
                p_reach54=float(np.mean(reach)) if reach else np.nan,
                min_below70=float(np.median(mins)) if mins else np.nan)


def person_stats(run: Path) -> dict | None:
    tp = run / "truth.pkl"
    if not tp.exists(): return None
    tr = pickle.load(open(tp, "rb"))
    meta = json.load(open(run / "meta.json"))
    person = pickle.load(open(run / "person.pkl", "rb"))
    start = meta.get("burn_end", 18 * 60)
    cgm = tr["cgm"].sort_index()
    cgm = cgm[cgm.index >= start]
    cgm.index = _series(cgm.index.to_series())
    truth = tr["truth"]; truth = truth[truth.m >= start]
    days = (truth.m.max() - truth.m.min()) / 1440.0
    out = dict(name=person.name, template=person.template, sensor=person.sensor, strategy=person.strategy,
               formulation=person.formulation, days=days)
    b = T.block_features(cgm.dropna(), block=f"{int(days) + 3}D", min_samples=min(1200, int(len(cgm) * 0.5)))
    if len(b):
        r = b.iloc[b["n"].to_numpy().argmax()]
        out.update({k: float(r[k]) for k in GLUCOSE_FEATS})
    v = cgm.dropna()
    out.update(t54=100 * float((v < 54).mean()), wear=float(cgm.notna().mean()))
    out.update(lows_anatomy(cgm))
    # insulin delivered, 5-min bins
    d = pd.Series(truth.delivered.to_numpy(), index=_series(truth.m)).resample("5min").sum()
    tot = d.to_numpy()
    srt = np.sort(tot)[::-1]; k = max(int(0.01 * len(srt)), 1)
    day = d.resample("1D").sum(); nb = d.resample("1D").count(); day = day[nb > 240]
    hour = d.groupby(d.index.hour).mean()
    out.update(zero_frac=100 * float(np.mean(tot <= 1e-9)), med_nonzero=float(np.median(tot[tot > 1e-9])),
               p99=float(np.percentile(tot, 99)), conc1=100 * float(srt[:k].sum() / srt.sum()),
               tdd=float(day.median()) if len(day) else np.nan,
               tdd_cv=100 * float(day.std() / day.mean()) if len(day) > 2 else np.nan,
               ac1=float(np.corrcoef(day[:-1], day[1:])[0, 1]) if len(day) > 5 else np.nan,
               day_night=float(hour.loc[10:22].mean() / hour.loc[0:6].mean()) if hour.loc[0:6].mean() > 0 else np.nan)
    beh = pd.DataFrame(tr["behavior"], columns=["m", "kind", "g", "x"])
    beh = beh[beh.m >= start]
    ent = [e for e in tr["entries"] if e[0] >= start]
    bol = [b for b in tr["bolus_requests"] if b[0] >= start]
    out.update(carb_entries_per_day=len(ent) / days, user_boluses_per_day=len(bol) / days,
               carbs_eaten_day=float(beh[beh.kind.isin(["meal", "snack"])].g.sum() / days),
               rescue_g_day=float(beh[beh.kind.isin(["rescue", "retreat", "proactive"])].g.sum() / days),
               proactive_per_day=float((beh.kind == "proactive").sum() / days),
               rescues_per_day=float(beh.kind.isin(["rescue", "retreat"]).sum() / days),
               true_tir=100 * float(((truth.bg >= 70) & (truth.bg <= 180)).mean()),
               true_t54=100 * float((truth.bg < 54).mean()),
               true_min=float(truth.bg.min()))
    return out


def real_table() -> pd.DataFrame:
    w = pd.read_csv(DIST / "wholerecord.csv")
    c = pd.read_csv(DIST / "cohort.csv")[["alias", "sensor", "strategy", "t54", "carb_entries_per_day",
                                          "user_boluses_per_day"]]
    d = pd.read_csv(DIST / "delivery.csv")[["alias", "zero_frac", "med_nonzero", "p99", "conc1", "tdd", "tdd_cv", "ac1"]]
    r = w.merge(c, on="alias", how="left").merge(d, on="alias", how="left")
    r["strategy"] = r["strategy"].map(lambda s: "temp" if str(s).startswith("temp") else "autobolus")
    return r


def compare(sim: pd.DataFrame, by_sensor: bool = True) -> pd.DataFrame:
    from scipy.stats import ks_2samp
    real = real_table()
    rows = []
    stats = [c for c in sim.columns if c in real.columns and c not in ("alias", "sensor", "strategy")]
    groups = sorted(sim.sensor.unique()) if by_sensor else ["all"]
    for st in stats:
        for g in groups:
            if by_sensor and st in INSTRUMENT:
                rs = real.loc[real.sensor == g, st].dropna(); ss = sim.loc[sim.sensor == g, st].dropna(); lab = g
            else:
                if g != groups[0]: continue
                rs = real[st].dropna(); ss = sim[st].dropna(); lab = "all"
            if len(rs) < 3 or len(ss) < 3: continue
            q = lambda x: np.percentile(x, [10, 50, 90])
            rq, sq = q(rs), q(ss)
            rows.append(dict(stat=st, group=lab, n_real=len(rs), n_sim=len(ss),
                             real_p10=rq[0], real_p50=rq[1], real_p90=rq[2],
                             sim_p10=sq[0], sim_p50=sq[1], sim_p90=sq[2],
                             ks_p=ks_2samp(rs, ss).pvalue))
    return pd.DataFrame(rows)


def main():
    root = Path(sys.argv[1])
    rows = [s for s in (person_stats(p) for p in sorted(root.glob("v*"))) if s]
    sim = pd.DataFrame(rows)
    sim.to_csv(root / "sim_stats.csv", index=False)
    cmp = compare(sim)
    cmp.to_csv(root / "compare.csv", index=False)
    pd.set_option("display.width", 220)
    print(cmp.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
