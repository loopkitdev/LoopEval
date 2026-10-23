"""Meal, activity and fall statistics, computed by ONE function on a donor's 13-day block and on a simulated person's
window (like for like; LESSONS 494). The validate.py rows describe glucose and insulin; these describe what moves them:

  meals      unann_pulses_day, pulse_peak_h, pulse_dur_h, pulse_peak_per_g   (the ice labeller's pulses, non-rescue)
             unl_rises_day, unl_rise_rate      CGM rises >= 40 mg/dL with no carb entry from -4 h to +1 h of the peak
             entry_fast_fall                   share of entries followed within 2 h by a fast fall (< -2.5 mg/dL/min
                                               over 15 min, ending 70-180)
  falls      fast_fall_share                   share of falling 15-min windows ending 70-180 that are fast (per sensor)
             ice_dip_day, ice_dip_day_share    episodes where the 30-min mean ICE stays 70 mg/dL/h below the window's median for >= 20 min
                                               (glucose falling well beyond Loop's insulin model): per day, and the share
                                               between 08 and 22 h — the unexplained falls Pete proposed fitting to
                                               activity (2026-10-22)
  activity   workouts_week, workout_dur, workout_mets, workout_after_meal (share starting 0-2 h after a carb entry),
             act_net20 (Pemberton 2025's design: ΔCGM over a workout's first 20 min less matched non-workout windows of
             the same block — start CGM ±15, 15-min ROC ±0.5 mg/dL/min, IOB ±0.5 U); act_net20_hi the same for bouts starting
             above 150 mg/dL with IOB >= 2 U, where the donors' response lives (−19 above 180, −20 at IOB >= 3 U). Donors: HealthKit workouts, only
             for donors who record any; simulated people: structured sessions, only for twins of those donors.

    python -m loopeval_analysis.patient_sim.lifestats donors <out.csv> [par]     # per-block donor table (once)
    python -m loopeval_analysis.patient_sim.lifestats sim <run-root> [par]       # life_stats.csv + compare_life.csv
"""
from __future__ import annotations

import json
import pickle
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .world import EPOCH

ICE_ROOT = Path.home() / ".loop-eval/ice_v32"
ACTIVITY = Path.home() / ".loop-eval/runs/2026-10-18-additive-workouts/activity.parquet"
ICE_ANALYSIS = Path.home() / "dev/loopeval-ice/analysis"
FAST = -150.0          # mg/dL/h over 15 min
DIP = 70.0             # mg/dL/h below the block's median ICE, 30-min mean, >= 20 min
LIFE_STATS = ["unann_pulses_day", "pulse_peak_h", "pulse_dur_h", "pulse_peak_per_g", "unl_rises_day", "unl_rise_rate",
              "entry_fast_fall", "fast_fall_share", "ice_dip_day", "ice_dip_day_share", "workouts_week", "workout_dur",
              "workout_mets", "workout_after_meal"]   # + act_net20 / act_net20_hi, pooled (act_rows)
LIFE_INSTRUMENT = {"fast_fall_share"}


def _grid(tm: np.ndarray, g: np.ndarray, t0: float, t1: float) -> np.ndarray:
    """CGM on a 5-min grid t0..t1 (minutes): the reading nearest each slot within 2.5 min, else NaN."""
    n = int((t1 - t0) // 5)
    out = np.full(n, np.nan)
    k = np.round((tm - t0) / 5).astype(int)
    ok = (k >= 0) & (k < n) & (np.abs(tm - (t0 + 5 * k)) <= 2.5)
    out[k[ok]] = g[ok]
    return out


def life_stats(tm, g, t0, t1, ent_t, ent_g, iob_t=None, iob_v=None, pulses=None, workouts=None, steps=None,
               hour0: float = 0.0, net_workouts=None) -> dict:
    """All rows for one window [t0, t1) in minutes (local clock: minute % 1440 is the time of day, after `hour0` hours).
    ent_t / ent_g: carb entries; iob_t / iob_v: Loop's IOB; pulses: DataFrame (onset_m, size_g, peak_h, dur_h,
    peak_geq_h, announced, rescue); workouts: DataFrame (start, dur, mets) or None (not a recorder); steps: DataFrame
    (t, ice, clean) on the ice extraction, or None."""
    days = (t1 - t0) / 1440.0
    G = _grid(np.asarray(tm, float), np.asarray(g, float), t0, t1)
    T = t0 + 5.0 * np.arange(len(G))
    v15 = np.full(len(G), np.nan); v15[3:] = (G[3:] - G[:-3]) * 4.0
    cov = np.isfinite(G[3:]) & np.isfinite(G[2:-1]) & np.isfinite(G[1:-2]) & np.isfinite(G[:-3])   # all 15 min covered
    v15[3:][~cov] = np.nan
    band = (G >= 70) & (G <= 180)
    fall = np.isfinite(v15) & (v15 < 0) & band
    fastk = fall & (v15 < FAST)
    out = dict(fast_fall_share=100 * fastk.sum() / fall.sum() if fall.sum() > 50 else np.nan)
    et = np.asarray(ent_t, float); eg = np.asarray(ent_g, float)
    sel = (et >= t0) & (et < t1) & (eg >= 5)
    et5 = np.sort(et[sel])
    # entries followed by a fast fall within 2 h (first entry of a 3-h cluster)
    n = hit = 0; last = -1e18
    for t in et5:
        if t - last < 180: last = t; continue
        last = t
        w = (T > t) & (T <= t + 120)
        if np.isfinite(G[w]).sum() < 18: continue
        n += 1; hit += bool(fastk[w].any())
    out["entry_fast_fall"] = 100 * hit / n if n >= 5 else np.nan
    # unlogged rises
    sm = pd.Series(G).rolling(3, center=True, min_periods=2).mean().to_numpy()
    rates = []; j = 24; N = len(G); all_e = et[(et >= t0 - 300) & (et < t1 + 120)]
    while j < N - 26:
        x = sm[j]
        if not np.isfinite(x) or not (x >= sm[j - 1] and x > sm[j + 1] and x >= np.nanmax(sm[j - 6:j + 7])):
            j += 1; continue
        pre = sm[j - 24:j]
        if np.isfinite(pre).sum() < 18 or np.isfinite(sm[j:j + 25]).sum() < 20: j += 1; continue
        amp = x - np.nanmin(pre)
        t = T[j]
        if amp < 40 or np.any((all_e >= t - 240) & (all_e <= t + 60)): j += 1; continue
        rise = 5.0 * (24 - int(np.nanargmin(pre)))
        rates.append(amp / max(rise, 5.0) * 60.0); j += 12
    out["unl_rises_day"] = len(rates) / days
    out["unl_rise_rate"] = float(np.median(rates)) if len(rates) >= 3 else np.nan
    # the ice labeller's pulses
    if pulses is not None:
        p = pulses[(pulses.onset_m >= t0) & (pulses.onset_m < t1) & ~pulses.rescue.astype(bool)]
        out["unann_pulses_day"] = float((~p.announced.astype(bool)).sum()) / days
        if len(p) >= 5:
            out.update(pulse_peak_h=float(p.peak_h.median()), pulse_dur_h=float(p.dur_h.median()),
                       pulse_peak_per_g=float((p.peak_geq_h / p.size_g.clip(lower=1)).median()))
    # unexplained-fall episodes on the ice steps
    if steps is not None and len(steps):
        s = steps[(steps.t >= t0) & (steps.t < t1)].sort_values("t")
        ice = s.ice.where(s.clean.astype(bool)).to_numpy(float)
        r = pd.Series(ice).rolling(6, min_periods=5).mean().to_numpy()
        # relative to the block's own typical counteraction (Loop's settings leave a person-specific offset)
        low = np.nan_to_num(r - np.nanmedian(ice), nan=0.0) < -DIP
        ts = s.t.to_numpy(float); starts = []; k = 0
        while k < len(low):
            if low[k]:
                e = k
                while e + 1 < len(low) and low[e + 1]: e += 1
                if ts[e] - ts[k] >= 15: starts.append(ts[k] - 25)       # the 30-min mean starts ~25 min before it reads low
                k = e + 1
            else: k += 1
        st = np.array(starts)
        out["ice_dip_day"] = len(st) / days
        hr = ((st - hour0 * 60) % 1440) / 60 if len(st) else st
        out["ice_dip_day_share"] = float(((hr >= 8) & (hr < 22)).mean()) if len(st) >= 3 else np.nan
    # workouts
    if workouts is not None:
        w = workouts[(workouts.start >= t0) & (workouts.start < t1 - 20)]
        out["workouts_week"] = len(w) / days * 7
        if len(w):
            out["workout_dur"] = float(w.dur.median())
            out["workout_mets"] = float(w.mets.median()) if w.mets.notna().any() else np.nan
            out["workout_after_meal"] = float(np.mean([np.any((et5 < s_) & (et5 >= s_ - 120)) for s_ in w.start]))
    # the response is physiology, not habit: a simulated person's sessions count whether or not its donor records them
    nw = workouts if net_workouts is None else net_workouts
    if nw is not None and iob_t is not None:
        w = nw[(nw.start >= t0) & (nw.start < t1 - 20)]
        if len(w): out["_bouts"] = _net20(G, T, w, nw, et5, np.asarray(iob_t, float), np.asarray(iob_v, float))
    return out


def _net20(G, T, w, allw, et5, iob_t, iob_v) -> list[dict]:
    """Pemberton 2025's matched net: workout ΔCGM over 20 min less matched non-workout windows (start CGM ±15, 15-min
    ROC ±0.5 mg/dL/min, IOB ±0.5 U; no workout from -30 to +10 min of either end, no entry from -20 to +30 min)."""
    def at(t):
        k = int(round((t - T[0]) / 5)); return G[k] if 0 <= k < len(G) else np.nan
    busy = np.zeros(len(T), bool)
    for s_, d_ in zip(allw.start, allw.dur): busy |= (T > s_ - 30) & (T < s_ + d_ + 10)
    for e in et5: busy |= (T > e - 30) & (T < e + 20)
    k = np.arange(3, len(T) - 4)
    k = k[~busy[k]]
    g0 = G[k]; roc = (G[k] - G[k - 3]) / 15; dc = G[k + 4] - G[k]
    io = np.interp(T[k], iob_t, iob_v)
    ok = np.isfinite(g0) & np.isfinite(roc) & np.isfinite(dc) & np.isfinite(io)
    g0, roc, dc, io = g0[ok], roc[ok], dc[ok], io[ok]
    bouts = []
    for s_ in w.start:
        a, b, c = at(s_), at(s_ - 15), at(s_ + 20)
        if not (np.isfinite(a) and np.isfinite(b) and np.isfinite(c)) or a <= 100: continue
        if np.any((et5 > s_ - 30) & (et5 < s_ + 20)): continue
        i0 = float(np.interp(s_, iob_t, iob_v))
        m = (np.abs(g0 - a) <= 15) & (np.abs(roc - (a - b) / 15) <= 0.5) & (np.abs(io - i0) <= 0.5)
        if m.sum() >= 5: bouts.append(dict(net=(c - a) - dc[m].mean(), g0=a, iob=i0))
    return bouts


# ---------------------------------------------------------------------------------------------------------- donors
def _workouts_all() -> pd.DataFrame:
    A = pd.read_parquet(ACTIVITY)
    num = lambda s: float(re.search(r'"\$numberDouble":"([-0-9.eE]+)"', s).group(1)) if isinstance(s, str) and "$numberDouble" in s else np.nan
    A["dur"] = A.duration.map(num) / 60.0
    A["t"] = pd.to_datetime(A.time.astype(str).str.extract(r'numberLong":"(\d+)')[0].astype(float), unit="ms")
    A["mets"] = A.payload.astype(str).str.extract(r'HKAverageMETs":"([0-9.]+)')[0].astype(float)
    A = A[A.dur.between(5, 360)][["alias", "t", "dur", "mets"]]
    # the extract repeats a workout once per upload (up to 7×): one row per alias, start and duration
    return A.assign(_k=A.t.dt.round("1min"), _d=A.dur.round(1)).drop_duplicates(["alias", "_k", "_d"]).drop(columns=["_k", "_d"])


def _mins(idx) -> np.ndarray:
    return (pd.DatetimeIndex(idx).asi8 / 6e10)


def donor_blocks(alias: str, A: pd.DataFrame | None, block_days: int = 13) -> list[dict]:
    """One row per 13-day block, the blocks of validate.real_stats (local clock, first whole day on)."""
    from .quiet import local_offset, to_local
    d = ICE_ROOT / "full" / alias
    g = json.load(open(d / "glucose.json"))
    off = local_offset(alias, ICE_ROOT)
    cgm = pd.Series([x["quantity"] for x in g], index=to_local(pd.to_datetime([x["startDate"] for x in g]), off), dtype=float).sort_index()
    cgm = cgm[~cgm.index.duplicated()]
    c = json.load(open(d / "carbs.json"))
    ct = _mins(to_local(pd.to_datetime([x["startDate"] for x in c], utc=True), off)) if c else np.array([])
    cg = np.array([float(x.get("grams") or 0) for x in c])
    s = pd.read_parquet(ICE_ROOT / "steps" / f"{alias}.parquet", columns=["t1", "iob", "ice", "clean", "compression"])
    st = pd.DataFrame(dict(t=_mins(to_local(s.t1, off)), ice=s.ice.to_numpy(float),
                           clean=(s.clean & ~s.compression).to_numpy(bool)))
    iob_t, iob_v = st.t.to_numpy(), s.iob.to_numpy(float)
    mp = ICE_ROOT / "meals" / f"{alias}.parquet"
    pulses = None
    if mp.exists():
        ml = pd.read_parquet(mp)
        pulses = ml.assign(onset_m=_mins(to_local(ml.onset, off)))
    W = None
    if A is not None and alias in set(A.alias):
        a = A[A.alias == alias]
        W = pd.DataFrame(dict(start=_mins(to_local(a.t, off)), dur=a.dur.to_numpy(), mets=a.mets.to_numpy()))
    tm, gv = _mins(cgm.index), cgm.to_numpy()
    t0 = _mins([cgm.index[0].floor("D") + pd.Timedelta(days=1)])[0]; t1 = _mins([cgm.index[-1].floor("D")])[0]
    rows, b, s_ = [], 0, t0
    while s_ + block_days * 1440 <= t1:
        e = s_ + block_days * 1440
        if ((tm >= s_) & (tm < e)).sum() > 0.7 * block_days * 288:   # the same blocks validate.real_stats keeps
            r = life_stats(tm, gv, s_, e, ct, cg, iob_t, iob_v, pulses, W, st)
            for x in r.pop("_bouts", []): _BOUTS.append(dict(alias=alias, **x))
            rows.append(dict(alias=alias, block=b, **r))
            b += 1
        s_ = e
    return rows


_BOUTS: list = []


def _donor_one(a):
    _BOUTS.clear()
    try:
        return donor_blocks(a, _A), list(_BOUTS)
    except Exception as ex:              # noqa: BLE001
        print(a, "skipped:", repr(ex)[:200]); return [], []


_A = None


def donors(out: str, par: int = 6):
    global _A
    from concurrent.futures import ProcessPoolExecutor
    T = pd.read_csv(Path.home() / ".loop-eval/runs/2026-10-15-additive-templates/templates_pilot.csv")
    _A = _workouts_all() if ACTIVITY.exists() else None
    with ProcessPoolExecutor(par) as ex:
        res = list(ex.map(_donor_one, sorted(T.alias)))
    D = pd.DataFrame([r for rs, _ in res for r in rs])
    D.to_csv(out, index=False)
    pd.DataFrame([b for _, bs in res for b in bs]).to_csv(Path(out).with_name("life_bouts.csv"), index=False)
    print(f"{len(D)} blocks, {D.alias.nunique()} donors -> {out}")


# ------------------------------------------------------------------------------------------------------- simulated
def _sim_steps(run: Path) -> pd.DataFrame | None:
    """ICE steps for a simulated person through the ice role's own extractor (ice_check's export), as the donors'."""
    import subprocess, tempfile
    from .ice_check import export_sim
    code = ("import sys, pandas as pd; sys.path.insert(0, sys.argv[1]); from loopeval_analysis.ice_gen import extract as X; "
            "s, _ = X.extract(sys.argv[2]); s[['t1','ice','clean']].to_parquet(sys.argv[3])")
    with tempfile.TemporaryDirectory() as d:
        export_sim(run, Path(d))
        r = subprocess.run([sys.executable, "-W", "ignore", "-c", code, str(ICE_ANALYSIS), d, d + "/s.parquet"],
                           capture_output=True, text=True)
        if r.returncode != 0: return None
        s = pd.read_parquet(d + "/s.parquet")
    return pd.DataFrame(dict(t=((s.t1 - EPOCH).dt.total_seconds() / 60).to_numpy(), ice=s.ice.to_numpy(float),
                             clean=s.clean.to_numpy(bool)))


def person_life(run: Path, recorders: set | None = None, with_steps: bool = True) -> dict | None:
    tp = run / "truth.pkl"
    if not tp.exists(): return None
    tr = pickle.load(open(tp, "rb"))
    meta = json.load(open(run / "meta.json")); person = pickle.load(open(run / "person.pkl", "rb"))
    t0 = float(np.ceil(meta.get("burn_end", 1080) / 1440.0) * 1440.0)
    t1 = float(tr["truth"].m.max()) + 1
    c = tr["cgm"].dropna().sort_index()
    ent = tr["entries"]
    pr = pd.DataFrame(json.load(open(run / "trace.json"))["predictions"])
    iob_t = ((pd.to_datetime(pr.t) - EPOCH).dt.total_seconds() / 60).to_numpy(); iob_v = pr.candidateIOB.astype(float).to_numpy()
    pulses = None
    if (run / "meals_labeled.csv").exists():
        ml = pd.read_csv(run / "meals_labeled.csv")
        pulses = ml.assign(onset_m=((pd.to_datetime(ml.onset, utc=True) - EPOCH).dt.total_seconds() / 60).to_numpy())
    b = [x for x in tr["behavior"] if x[1] == "exercise"]
    mm = tr.get("metmax")
    Wall = pd.DataFrame(dict(start=[x[0] for x in b], dur=[float(x[2]) for x in b],
                             mets=[1.0 + float(x[3]) * (mm - 1.0) if mm else np.nan for x in b]))
    W = Wall if recorders is None or person.template in recorders else None   # habit rows: twins of recording donors only
    steps = _sim_steps(run) if with_steps else None
    r = life_stats(c.index.to_numpy(float), c.to_numpy(float), t0, t1, [e[0] for e in ent], [e[1] for e in ent],
                   iob_t, iob_v, pulses, W, steps, net_workouts=Wall)
    bouts = [dict(alias=person.name, **x) for x in r.pop("_bouts", [])]
    return dict(name=person.name, template=person.template, sensor=person.sensor, **r), bouts


def _sim_one(a):
    run, rec = a
    try:
        return person_life(Path(run), rec)
    except Exception as ex:              # noqa: BLE001
        print(Path(run).name, "skipped:", repr(ex)[:200]); return None, []


HABIT = ["workouts_week", "workout_dur", "workout_mets", "workout_after_meal"]


def _recorders(D: pd.DataFrame) -> set:
    """Donors whose HealthKit record measures their exercise: a workout in at least half of their 13-day blocks. Most
    donors with any workout record one rarely (median 0.15 / week, 78% of blocks empty); their rate is a recording
    habit, not an exercise frequency (LESSONS 496)."""
    w = D.dropna(subset=["workouts_week"])
    s = w.groupby("alias").workouts_week.apply(lambda x: (x > 0).mean())
    return set(s[s >= 0.5].index)


def sim(root: str, par: int = 6, donor_csv: str | None = None):
    from concurrent.futures import ProcessPoolExecutor
    from .validate import compare_blocks, INSTRUMENT
    root = Path(root)
    dpath = Path(donor_csv) if donor_csv else Path.home() / ".loop-eval/runs/2026-10-15-additive-templates/life_blocks.csv"
    rec = _recorders(pd.read_csv(dpath)) if dpath.exists() else None
    runs = sorted(str(p) for p in root.glob("v*") if (p / "truth.pkl").exists())
    with ProcessPoolExecutor(par) as ex:
        res = list(ex.map(_sim_one, [(r, rec) for r in runs]))
    S = pd.DataFrame([r for r, _ in res if r]); S.to_csv(root / "life_stats.csv", index=False)
    pd.DataFrame([b for _, bs in res for b in bs]).to_csv(root / "life_bouts.csv", index=False)
    if dpath.exists():
        D = pd.read_csv(dpath)
        D.loc[~D.alias.isin(rec), HABIT] = np.nan
        tt = pd.read_csv(Path.home() / ".loop-eval/runs/2026-10-15-additive-templates/templates_pilot.csv")[["alias", "sensor"]]
        D = D.merge(tt, on="alias", how="left")
        INSTRUMENT.update(LIFE_INSTRUMENT)
        cp = compare_blocks(S, D)
        cp.to_csv(root / "compare_life.csv", index=False)
        pd.set_option("display.width", 200)
        print(cp[["stat", "group", "n_real", "n_sim", "real_p50", "sim_p50", "ks_p", "pass_share"]].round(3).to_string(index=False))
        print(pd.DataFrame(act_rows(root / "life_bouts.csv", dpath.with_name("life_bouts.csv")))[["stat", "real_p50", "sim_p50", "d50", "se"]].round(2).to_string(index=False))


ACT = {"act_net20": lambda b: b, "act_net20_hi": lambda b: b[(b.g0 > 150) & (b.iob >= 2.0)]}


def act_rows(sim_bouts: Path, donor_bouts: Path, seed: int = 0) -> list[dict]:
    """The activity response POOLED over bouts (a person has a handful per window, too few for a per-person median):
    the simulated cohort's mean net against the donors', in units of the donors' between-person spread (10–90% of the
    per-donor means, donors with >= 3 bouts), with a bootstrap SE over simulated people."""
    if not (sim_bouts.exists() and donor_bouts.exists()): return []
    Sb, Db = pd.read_csv(sim_bouts), pd.read_csv(donor_bouts)
    rng = np.random.default_rng(seed); out = []
    for st, f in ACT.items():
        s, d = f(Sb), f(Db)
        if len(s) < 10 or len(d) < 10: continue
        pm = d.groupby("alias").net.agg(["mean", "size"]); pm = pm[pm["size"] >= 3]["mean"]
        q = np.percentile(pm, [10, 50, 90]) if len(pm) >= 5 else np.array([np.nan] * 3)
        S_ = (q[2] - q[0]) / 2.563
        ppl = s.alias.unique(); g = s.groupby("alias").net
        boot = [np.mean(np.concatenate([g.get_group(a).to_numpy() for a in rng.choice(ppl, len(ppl))])) for _ in range(300)]
        out.append(dict(stat=st, group="all", n_sim=int(s.alias.nunique()), real_p10=q[0], real_p50=float(d.net.mean()),
                        real_p90=q[2], sim_p10=np.nan, sim_p50=float(s.net.mean()), sim_p90=np.nan, S=S_,
                        d50=(float(s.net.mean()) - float(d.net.mean())) / S_, spread=np.nan, se=float(np.std(boot)) / S_))
    return out


if __name__ == "__main__":
    if sys.argv[1] == "donors":
        donors(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 6)
    else:
        sim(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 6)
