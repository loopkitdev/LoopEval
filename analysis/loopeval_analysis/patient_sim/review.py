"""Component review: each fitted component measured against its own target on a cohort run, the same code for donors and
simulated people (Pete 2026-10-18: after every adopted change, re-check the existing components before adding another).

    python -m loopeval_analysis.patient_sim.review donors  [--out targets.json]   # Mac (needs pyarrow): donor targets
    python -m loopeval_analysis.patient_sim.review RUN_DIR [--targets targets.json] # any host: the run against them

Checks (Dexcom G7 people on both sides; donors from the ice_v32 exports, local clock; sim minute clock is local):
  A5   meal EGP nadir (true EGP / pre-meal after isolated entries)       target Romeres 2025: 0.56 at ~160 min
  A9   low episodes: nadir p10 / p25 / p50, share < 54, duration p90      target: donors (LESSONS 166)
  meal bolused isolated entries >= 15 g: 0-2 h nadir drop p10/p50,
       share ending < 70, 3-h change median                              target: donors (LESSONS 188)
  G4   carb entries/day, bolused >= 15 g entries/day                       target: donors (LESSONS 188)
  rise unentered rises/day, day (06-24) and night (00-06)                 target: donors (LESSONS 184)
  cut  night Loop cuts: P(unentered rise within 2 h)                       target: donors (LESSONS 191)
"""
from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

H = Path.home()
ICE = H / ".loop-eval/ice_v32"
TEMPLATES = H / ".loop-eval/runs/2026-10-15-additive-templates/templates_pilot.csv"
TARGETS = H / ".loop-eval/runs/2026-10-18-additive-workouts/review_targets.json"
FIXED = {"egp_nadir": 0.56, "egp_nadir_min": 160}          # Romeres 2025 T1D meal tracer (evidence/13)


# ---------------------------------------------------------------- per-person series
def _donor_people():
    """(alias, minutes local, cgm, entry minutes, entry grams, manual-bolus minutes, steps or None)."""
    T = pd.read_csv(TEMPLATES)
    for a in T[T.sensor == "Dexcom G7"].alias:
        d = ICE / "full" / a
        try:
            s = pd.read_parquet(ICE / "steps" / f"{a}.parquet").sort_values("t1")
            c = json.load(open(d / "carbs.json")); ds = json.load(open(d / "doses.json"))
        except Exception:
            continue
        t = (s.t1.astype("int64") // 60_000_000_000).to_numpy().astype(float)
        off = np.median(((s.hour.to_numpy() * 60 - (t % 1440)) + 720) % 1440 - 720); off = round(off / 30) * 30
        tm = lambda x: pd.Timestamp(x).value / 6e10 + off
        cc = sorted((tm(x["startDate"]), x["grams"]) for x in c if (x.get("grams") or 0) > 0)
        bol = np.array(sorted(tm(x["startDate"]) for x in ds if x.get("deliveryType") == "bolus"
                              and not x.get("automatic") and (x.get("volume") or 0) >= 0.3))
        deliv = (s.basal_u.fillna(0) + s.bolus_auto_u.fillna(0) + s.bolus_manual_u.fillna(0)).to_numpy()
        yield a, t + off, s.bg1.to_numpy(float), np.array([x for x, _ in cc]), np.array([g for _, g in cc]), bol, deliv, None


def _sim_people(run: Path):
    for p in sorted(run.glob("v0*")):
        P = pickle.load(open(p / "person.pkl", "rb"))
        if P.sensor != "Dexcom G7": continue
        tr = pickle.load(open(p / "truth.pkl", "rb")); c = tr["cgm"].dropna(); c = c[c.index >= 2880]
        grid = np.arange(2880, c.index.max(), 5.0); g = np.interp(grid, c.index.to_numpy(float), c.to_numpy(float))
        e = [(m, gg) for (m, k, gg, x) in tr["behavior"] if k == "entry" and m >= 2880]
        T = tr["truth"]; m = T.m.to_numpy(float); cd = np.r_[0, np.cumsum(T.delivered.to_numpy(float))]
        deliv = np.diff(np.interp(np.r_[grid, grid[-1] + 5], np.r_[m, m[-1] + 1], cd))
        # bolus_requests: + = a ratio of Loop's recommendation, − = absolute units (hand-dialled: corrections, top-ups,
        # free and stacked boluses); both are user boluses (LESSONS 237)
        bol = np.array(sorted(mm for mm, f in tr["bolus_requests"] if f > 0 or f <= -0.05))
        yield p.name, grid, g, np.array([x for x, _ in e], float), np.array([x for _, x in e], float), bol, deliv, tr


# ---------------------------------------------------------------- measures
def _rises(tm, g, ent):
    """Unentered rise episodes (LESSONS 184): +30 within 60 min from >= 80, one per 3 h, no entry -60..+30."""
    out, last = [], -1e9
    for i in range(1, len(g) - 12):
        if tm[i] - last < 180 or not np.isfinite(g[i]) or g[i] < 80: continue
        w = g[i + 1:i + 13]
        if np.isfinite(w).sum() < 8 or not (np.nanmax(w) - g[i] >= 30) or not (np.isfinite(g[i - 1]) and g[i - 1] >= g[i] - 3): continue
        if not np.any((ent >= tm[i] - 60) & (ent <= tm[i] + 30)): out.append(tm[i])
        last = tm[i]
    return np.array(out)


def _lows(tm, g):
    """Episodes < 70 for >= 15 min, separated by >= 30 min at >= 70: (nadir, duration)."""
    eps, i, n = [], 0, len(g)
    while i < n:
        if g[i] < 70:
            j = i
            while j < n and (g[j] < 70 or not np.isfinite(g[j])): j += 1
            if tm[min(j, n - 1)] - tm[i] >= 15: eps.append((np.nanmin(g[i:j]), tm[min(j, n - 1)] - tm[i]))
            i = j + 6
        else:
            i += 1
    return eps


def measure(people) -> dict:
    R = dict(rise_day=[], rise_night=[], entries=[], bol15=[], meal_nad=[], meal_lo=[], meal_d3=[], low_nad=[], low_dur=[],
             cut_rise=[], egp=[])
    for name, tm, g, ent, eg, bol, deliv, tr in people:
        days = np.isfinite(g).sum() * 5 / 1440
        if days < 5: continue
        loc = tm % 1440
        ri = _rises(tm, g, ent)
        R["rise_night"].append(((ri % 1440) < 360).sum() / days); R["rise_day"].append(((ri % 1440) >= 360).sum() / days)
        R["entries"].append(len(ent) / days)
        R["bol15"].append(sum(1 for t, x in zip(ent, eg) if x >= 15 and len(bol) and np.any(np.abs(bol - t) <= 15)) / days)
        for t, x in zip(ent, eg):
            if x < 15 or np.any((ent > t - 180) & (ent < t + 240) & (ent != t)) or not (len(bol) and np.any(np.abs(bol - t) <= 15)): continue
            s = (tm >= t - 10) & (tm <= t + 190)
            if s.sum() < 30: continue
            y0 = np.interp(t, tm[s], g[s]); w = (tm >= t) & (tm <= t + 120)
            R["meal_nad"].append(np.nanmin(g[w]) - y0); R["meal_lo"].append(np.nanmin(g[w]) < 70)
            R["meal_d3"].append(np.interp(t + 180, tm[s], g[s]) - y0)
        for nad, dur in _lows(tm, g): R["low_nad"].append(nad); R["low_dur"].append(dur)
        # night Loop cuts (LESSONS 191)
        cs = np.r_[0, np.cumsum(deliv)]; w30 = np.full(len(deliv), np.nan); w30[6:] = cs[7:] - cs[1:-6]
        night = loc < 360; ref = np.nanmedian(w30[night]) if night.any() else np.nan
        if ref > 0:
            cut = w30 < 0.3 * ref; lastc = -1e9
            for i in range(12, len(tm) - 24):
                if night[i] and cut[i] and not cut[i - 12:i].any() and tm[i] - lastc >= 120:
                    lastc = tm[i]; R["cut_rise"].append(bool(len(ri) and np.any((ri >= tm[i]) & (ri <= tm[i] + 120))))
        if tr is not None:     # A5: true EGP after isolated entries >= 20 g
            T = tr["truth"]; m = T.m.to_numpy(float); e = T.egp.to_numpy(float)
            for t, x in zip(ent, eg):
                if x < 20 or np.any((ent > t - 180) & (ent < t + 360) & (ent != t)) or t + 360 > m[-1]: continue
                pre = np.interp(np.arange(t - 30, t, 5.0), m, e).mean()
                if pre > 0: R["egp"].append(np.interp(t + np.arange(0, 361, 10.0), m, e) / pre)
    nad = np.array(R["low_nad"]); out = {
        "low_nadir_p10": np.percentile(nad, 10), "low_nadir_p25": np.percentile(nad, 25), "low_nadir_p50": np.percentile(nad, 50),
        "low_share_lt54": float(np.mean(nad < 54)), "low_dur_p90": float(np.percentile(R["low_dur"], 90)),
        "meal_drop_p10": np.percentile(R["meal_nad"], 10), "meal_drop_p50": np.percentile(R["meal_nad"], 50),
        "meal_end_lt70": float(np.mean(R["meal_lo"])), "meal_d3_p50": np.percentile(R["meal_d3"], 50),
        "entries_day": float(np.mean(R["entries"])), "bolused15_day": float(np.mean(R["bol15"])),
        "rises_day_06_24": float(np.mean(R["rise_day"])), "rises_night_00_06": float(np.mean(R["rise_night"])),
        "night_cut_rise_p": float(np.mean(R["cut_rise"])) if R["cut_rise"] else np.nan}
    if R["egp"]:
        A = np.median(np.array(R["egp"]), 0); k = int(np.argmin(A)); out["egp_nadir"] = float(A[k]); out["egp_nadir_min"] = int(k * 10)
    return {k: round(float(v), 3) for k, v in out.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", help="'donors' or a cohort run directory")
    ap.add_argument("--targets", default=str(TARGETS)); ap.add_argument("--out", default=str(TARGETS))
    a = ap.parse_args()
    if a.what == "donors":
        t = measure(_donor_people()); t.update(FIXED)
        json.dump(t, open(a.out, "w"), indent=1); print(json.dumps(t, indent=1)); return
    got = measure(_sim_people(Path(a.what)))
    tgt = json.load(open(a.targets)) if Path(a.targets).exists() else dict(FIXED)
    print(f"{'measure':22s} {'run':>9s} {'target':>9s}   ratio")
    for k, v in got.items():
        t = tgt.get(k)
        r = (v / t) if (t not in (None, 0) and np.isfinite(v)) else np.nan
        print(f"{k:22s} {v:9.3f} {t if t is not None else float('nan'):9.3f}   {r:5.2f}")


if __name__ == "__main__":
    main()
