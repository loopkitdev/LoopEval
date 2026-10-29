"""Build additive-simulator template rows (the 130 columns of templates_pilot_logs.csv) for given aliases of one ICE root.

Every producer is the one that wrote the column into templates_pilot_logs.csv (templates.py add_* functions, or the
inline / run-dir scripts recovered from the session record), parametrised by ICE root. Class-(b) columns (fitted over
twin cohort runs) are left NaN. Cohort-shrunk columns (isf_body_mult, circ_*) take ns3's own fit and the pilot cohort's
shrinkage parameters, which are read from the pilot's fit tables.

  python build_template.py ROOT ALIAS[,ALIAS] OUT.csv [--sensor "Dexcom G7"] [--fit]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("/Users/pete/dev/loopeval-additive/analysis")
sys.path.insert(0, str(REPO))
from loopeval_analysis.patient_sim import templates as TP          # noqa: E402
from loopeval_analysis.patient_sim import quiet as Q               # noqa: E402

H = Path.home()
TDIR = H / ".loop-eval/runs/2026-10-15-additive-templates"
LIVE = TDIR / "templates_pilot_logs.csv"
HERE = Path(__file__).resolve().parent
CLASS_B = ["csf_own_mult", "twin_isf_mult", "twin_csf_mult", "corr_p_mult", "corr_thr_adj", "intake_mult", "csf_geq_mult"]


# ---------------------------------------------------------------- 1. build_pilot, parametrised by root (copy of templates.build_pilot)
def build_base(root: Path, aliases, sensor_map: dict, age_map: dict) -> pd.DataFrame:
    P = pd.read_csv(root / "persons.csv"); P = P[P.alias.isin(aliases)]
    rows = []
    for _, p in P.iterrows():
        a = p.alias; d = root / "full" / a
        th = json.load(open(d / "therapy.json"))
        meals = pd.read_parquet(root / "meals" / f"{a}.parquet")
        corr = pd.read_parquet(root / "meals" / f"{a}_corrections.parquet")
        g = pd.Series([x["quantity"] for x in json.load(open(d / "glucose.json"))], dtype=float)
        doses = json.load(open(d / "doses.json"))
        days = max(float(p.clean_days), 1.0)
        span = (pd.Timestamp(th["basal"][-1]["endDate"]) - pd.Timestamp(th["basal"][0]["startDate"])).days or days
        auto = sum(1 for x in doses if x["deliveryType"] == "bolus" and x.get("automatic"))
        nr = meals[~meals.rescue]; rs = meals[meals.rescue]
        hours = np.histogram(nr.hour.to_numpy() % 24, bins=24, range=(0, 24))[0]
        ann = nr[nr.announced]
        _free = TP._free
        r = dict(alias=a, tdd=float(p.tdd), isf_true=float(p.isf_tdd),
                 isf=TP._tw_mean(th["sensitivity"]), cr=TP._tw_mean(th["carbRatio"]), basal=TP._tw_mean(th["basal"]),
                 target=TP._tw_mean(th["target"]), max_basal=float(th["maxBasalRate"]), max_bolus=float(th["maxBolus"]),
                 suspend=float(th.get("suspendThreshold", 70.0)),
                 strategy="bolus" if auto / span > 2 else "temp", pump="Omnipod",
                 sensor=sensor_map.get(a, "Dexcom G7"), insulin_brand=TP._FORM.get(th.get("insulinType", ""), "humalog"),
                 age_years=age_map.get(a, np.nan), basal_true=np.nan, archetype="",
                 meals_per_day=len(nr) / span, meal_hours=json.dumps((hours / max(hours.sum(), 1)).round(4).tolist()),
                 meal_size_med=float(nr.size_g.median()), meal_size_logsd=float(np.log(nr.size_g).std()),
                 announced_share=float(nr.announced.mean()) if len(nr) else 0.0,
                 estimate_ratio=float(ann.estimate_ratio.median()) if len(ann) else np.nan,
                 bolus_lead_min=float(ann.bolus_lead_min.median()) if ann.bolus_lead_min.notna().any() else np.nan,
                 p_bolus_ann=float((ann.bolus_u > 0).mean()) if len(ann) else np.nan,
                 bolus_ratio=float(ann.bolus_ratio.median()) if ann.bolus_ratio.notna().any() else np.nan,
                 corrections_per_day=len(corr) / span, corr_bg_med=float(corr.bg.median()) if len(corr) else np.nan,
                 corr_ratio=float((corr.units / corr.rec.replace(0, np.nan)).median()) if len(corr) else np.nan,
                 free_boluses_per_day=float(_free(corr).sum() / span),
                 free_bolus_u_med=float(corr.units[_free(corr)].median()) if _free(corr).any() else np.nan,
                 true_corrections_per_day=float((~_free(corr)).sum() / span),
                 rescues_per_day=len(rs) / span, rescue_size_med=float(rs.size_g.median()) if len(rs) else np.nan,
                 rescue_bg_med=float(rs.bg_onset.median()) if len(rs) else np.nan,
                 carb_entries_per_day=float(meals.entry_g.gt(0).sum() / span),
                 user_boluses_per_day=float((ann.bolus_u > 0).sum() / span + len(corr) / span),
                 carb_g_day=float(meals.entry_g.fillna(0).sum() / span),
                 tir=float(100 * g.between(70, 180).mean()), t70=float(100 * (g < 70).mean()),
                 t54=float(100 * (g < 54).mean()), bg_mean=float(g.mean()), bg_cv=float(100 * g.std() / g.mean()))
        rows.append(r)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- settings_edits.csv rows (edits.py, recovered)
def settings_edits(root: Path, a: str) -> pd.DataFrame:
    def daily_profile(series):
        df = pd.DataFrame(series); df["s"] = pd.to_datetime(df.startDate); df["e"] = pd.to_datetime(df.endDate)
        df["day"] = df.s.dt.floor("D"); df["w"] = (df.e - df.s).dt.total_seconds()
        return df.groupby("day").apply(lambda x: np.average(x.value, weights=x.w) if x.w.sum() > 0 else np.nan)
    p = root / "full" / a
    t = json.load(open(p / "therapy.json")); g = json.load(open(p / "glucose.json"))
    gs = pd.Series([x["quantity"] for x in g], index=pd.to_datetime([x["startDate"] for x in g])).sort_index()
    gd = gs.resample("1D").mean()
    prof = pd.concat({k: daily_profile(t[k]) for k in ("rawBasal", "rawSensitivity", "rawCarbRatio") if t.get(k)}, axis=1).sort_index()
    rows = []
    for k in prof.columns:
        x = prof[k].dropna(); r = np.log(x / x.shift(1)).dropna()
        for day, v in r[np.abs(r) > 0.01].items():
            pre = gd[(gd.index < day) & (gd.index >= day - pd.Timedelta("3D"))].mean()
            post = gd[(gd.index >= day + pd.Timedelta("1D")) & (gd.index < day + pd.Timedelta("4D"))].mean()
            rows.append(dict(alias=a, setting=k, logchg=v, pre3=pre, post3=post, gmean=gs.mean()))
    return pd.DataFrame(rows, columns=["alias", "setting", "logchg", "pre3", "post3", "gmean"])


# ---------------------------------------------------------------- night_ratio (night_ratio_tpl.py, recovered)
def night_ratio(root: Path, a: str):
    from loopeval_analysis.patient_sim.validate import delivered_5min
    d = root / "full" / a; doses = json.load(open(d / "doses.json")); th = json.load(open(d / "therapy.json"))
    off = Q.local_offset(a, root)
    conv = lambda xs: pd.DatetimeIndex(Q.to_local(pd.to_datetime(xs, utc=True, format="ISO8601"), off))

    def sched(idx):
        b = th["basal"]; s = conv([x["startDate"] for x in b]); e = conv([x["endDate"] for x in b]); v = np.array([x["value"] for x in b], float)
        out = np.full(len(idx), np.nan); k = np.searchsorted(s.values, idx.values, side="right") - 1
        ok = (k >= 0) & (k < len(s)); kk = np.clip(k, 0, len(s) - 1); ok &= idx.values < e.values[kk]
        out[ok] = v[kk[ok]]; return out
    aut = [x for x in doses if not (x["deliveryType"] == "bolus" and not x.get("automatic"))]
    if not aut: return np.nan
    st, en = conv([x["startDate"] for x in aut]), conv([x["endDate"] for x in aut])
    A = [dict(x, startDate=s_, endDate=e_) for x, s_, e_ in zip(aut, st, en)]
    a5 = delivered_5min(A, min(st).floor("D"), max(en).ceil("D"), mask_gaps=True)
    u = a5.resample("30min").sum(min_count=6) * 2.0
    df = pd.DataFrame(dict(u=u)).dropna(); df = df[df.index.hour < 6]
    df["s"] = sched(df.index); df = df.dropna()
    return float(df.u.mean() / df.s.mean()) if len(df) > 100 and df.s.mean() > 0 else np.nan


# ---------------------------------------------------------------- treat_log_day (treat_log_rate.py)
def treat_log_day(root: Path, a: str):
    d = root / "full" / a
    gl = json.load(open(d / "glucose.json")); c = json.load(open(d / "carbs.json")); ds = json.load(open(d / "doses.json"))
    tm = lambda v: pd.to_datetime(v, utc=True, format="ISO8601").astype("int64") / 6e10
    g = pd.Series([x["quantity"] for x in gl], index=tm([x["startDate"] for x in gl])).sort_index(); g = g[~g.index.duplicated()]
    if len(g) < 1000: return np.nan
    cc = [x for x in c if (x.get("grams") or 0) > 0]
    b = np.sort(np.array(tm([x["startDate"] for x in ds if x.get("deliveryType") == "bolus" and not x.get("automatic") and (x.get("volume") or 0) >= 0.3]) if ds else []))
    et = np.array(tm([x["startDate"] for x in cc])) if cc else np.array([])
    gi, gv = g.index.to_numpy(), g.to_numpy(float)
    n = 0
    for t in et:
        j = np.searchsorted(gi, t)
        if j <= 0 or j >= len(gi) or gi[j] - t > 10: continue
        if gv[j] >= 130: continue
        if len(b) and np.min(np.abs(b - t)) <= 30: continue
        n += 1
    return n / max((gi[-1] - gi[0]) / 1440, 1)


# ---------------------------------------------------------------- low_entered_share, skip_bfast, unann_hours, far_unann (inline, recovered)
def low_entered_share(root: Path, a: str):
    M = pd.read_parquet(root / "meals" / f"{a}.parquet")
    if len(M) == 0 or "bg_onset" not in M.columns: return np.nan
    L = M[M.bg_onset < 75]
    return float(L.announced.mean()) if len(L) >= 5 else np.nan


def skip_bfast(root: Path, a: str):
    M = pd.read_parquet(root / "meals" / f"{a}.parquet")
    if len(M) == 0 or "hour" not in M.columns: return np.nan
    o = pd.to_datetime(M.onset, utc=True)
    days = pd.date_range(o.min().normalize(), o.max().normalize(), freq="D")
    if len(days) < 20: return np.nan
    lh = M.hour.to_numpy(); uh = (o.dt.hour + o.dt.minute / 60).to_numpy()
    off = ((lh - uh + 12) % 24) - 12
    local = o + pd.to_timedelta(off, unit="h")
    M = M.assign(lday=local.dt.normalize(), lhr=lh)
    b = M[(M.lhr >= 5) & (M.lhr < 10.5) & (M.size_g >= 10) & ~M.rescue]
    return 1 - b.lday.nunique() / M.lday.nunique()


def unann_hours(root: Path, a: str):
    m = pd.read_parquet(root / "meals" / f"{a}.parquet"); u = m[(m.announced != True) & (m.rescue != True)]  # noqa: E712
    if len(u) < 20: return np.nan
    h = np.histogram(u.hour.to_numpy() % 24, bins=24, range=(0, 24))[0].astype(float)
    return json.dumps((h / h.sum()).round(4).tolist())


def far_unann(root: Path, a: str):
    M = pd.read_parquet(root / "meals" / f"{a}.parquet")
    on = pd.to_datetime(M.onset); days = max((on.max() - on.min()).total_seconds() / 86400, 1.0)
    t = on.astype("int64").to_numpy() / 6e10; o = np.argsort(t); M = M.iloc[o]; t = t[o]
    an = t[M.announced.astype(bool).to_numpy()]; u = ~M.announced.astype(bool).to_numpy() & ~M.rescue.astype(bool).to_numpy()
    s = 0.0
    for ti, g in zip(t[u], M.size_g.to_numpy()[u]):
        j = np.searchsorted(an, ti) - 1
        if j < 0 or (ti - an[j]) / 60 >= 6: s += g
    return s / days


# ---------------------------------------------------------------- lone-bolus traits from bolus_decisions (inline, recovered)
def lone_bolus_traits(root: Path, a: str) -> dict:
    B = pd.read_parquet(root / "bolus_decisions.parquet"); B["tm"] = pd.to_datetime(B.t, utc=True).astype("int64") / 6e10
    d = root / "full" / a
    c = json.load(open(d / "carbs.json")); gl = json.load(open(d / "glucose.json"))
    ct = np.array([pd.Timestamp(x["startDate"]).value / 6e10 for x in c if (x.get("grams") or 0) > 0])
    near = lambda tm: len(ct) and np.any(np.abs(ct - tm) <= 30)
    out = {}
    b = B[(B.alias == a) & (B.requested > 0)]
    lone = [(rq, rc) for tm, rq, rc in zip(b.tm, b.requested, b.rec) if not near(tm)]
    if len(lone) >= 10:                                  # corr_over_share / corr_over_u
        rq = np.array([x for x, _ in lone]); rc = np.nan_to_num(np.array([y for _, y in lone])); over = rq > rc + 0.05
        out.update(corr_over_share=float(over.mean()), corr_over_u=float(np.median(rq[over] - rc[over])) if over.any() else np.nan)
        out.update(corr_u_med=float(np.median(rq)), corr_u_lsd=float(np.std(np.log(np.maximum(rq, 0.05)))))
    G = pd.Series([x["quantity"] for x in gl], index=[pd.Timestamp(x["startDate"]).value / 6e10 for x in gl]).sort_index(); G = G[~G.index.duplicated()]
    days = (G.index[-1] - G.index[0]) / 1440
    b5 = B[(B.alias == a) & (B.requested >= 0.5)]
    lt = np.array([tm for tm in b5.tm if not near(tm)])
    if len(lt) >= 10 and days >= 10:                     # corr_rate_d / corr_bg_d (donor targets of corr_p_mult / corr_thr_adj)
        out.update(corr_rate_d=len(lt) / days, corr_bg_d=float(np.median(np.interp(lt, G.index.to_numpy(float), G.to_numpy(float)))))
    bt = np.sort(B[(B.alias == a) & (B.requested >= 0.3)].tm.to_numpy(float))
    if len(bt) >= 20:                                    # stack_p
        stk = [1 for i in range(1, len(bt)) if 2 <= bt[i] - bt[i - 1] <= 30 and not near(bt[i])]
        out["stack_p"] = len(stk) / len(bt)
    return out


# ---------------------------------------------------------------- night_need_ratio (night_need_all.py, need_all)
def night_need(root: Path, a: str):
    s = pd.read_parquet(root / "steps" / f"{a}.parquet").sort_values("t1"); d_ = root / "full" / a
    ds = json.load(open(d_ / "doses.json")); c_ = json.load(open(d_ / "carbs.json")); th = json.load(open(d_ / "therapy.json"))
    tm = (s.t1.astype("int64") / 6e10).to_numpy(); off = float(np.median(((s.hour.to_numpy() * 60 - (tm % 1440)) + 720) % 1440 - 720))
    g = s.bg1.to_numpy(float); k = np.isfinite(g); tg, gg = tm[k], g[k]
    ev = np.sort(np.r_[[pd.Timestamp(z["startDate"]).value / 6e10 for z in ds if z.get("deliveryType") == "bolus" and not z.get("automatic") and (z.get("volume") or 0) >= 0.3],
                       [pd.Timestamp(z["startDate"]).value / 6e10 for z in c_ if (z.get("grams") or 0) > 0]])
    bs = np.array([pd.Timestamp(b["startDate"]).value / 6e10 for b in th["basal"]]); bv = np.array([float(b["value"]) for b in th["basal"]])
    cs = np.cumsum((s.basal_u.fillna(0) + s.bolus_auto_u.fillna(0) + s.bolus_manual_u.fillna(0)).to_numpy()); dt = tm + 5.0
    r = []
    for day0 in np.arange(np.floor((tm[0] + off) / 1440) * 1440, tm[-1] + off, 1440.0):
        a0, a1 = day0 + 120 - off, day0 + 300 - off
        if a1 > tm[-1] or a0 < tm[0] + 240: continue
        if np.any((ev >= a0 - 240) & (ev <= a1)): continue
        w = (tg >= a0) & (tg <= a1)
        if w.sum() < 30: continue
        dG = np.interp(a1, tg, gg) - np.interp(a0, tg, gg); steady = abs(dG) <= 15
        sch = np.mean([bv[max(0, np.searchsorted(bs, x, side="right") - 1)] for x in np.arange(a0, a1, 15.0)]) * 3
        if sch > 0:
            dl = np.interp(a1, dt, cs) - np.interp(a0, dt, cs); isf = float(np.mean([z['value'] for z in th['sensitivity']]))
            r.append(((dl / sch), (dl + dG / isf) / sch, steady))
    if len(r) < 5: return dict()
    rr = np.array(r, dtype=float); st = rr[:, 2] > 0
    return dict(steady=float(np.median(rr[st, 0])) if st.sum() >= 5 else np.nan, deliv_all=float(np.median(rr[:, 0])),
                need_all=float(np.median(rr[:, 1])), n=len(r), n_st=int(st.sum()))


# ---------------------------------------------------------------- entry_split (entry_split.py)
def entry_split(root: Path, r) -> dict:
    a = r.alias
    s = pd.read_parquet(root / "steps" / f"{a}.parquet"); c_ = json.load(open(root / "full" / a / "carbs.json"))
    tm = (s.t1.astype("int64") / 6e10).to_numpy(); off = float(np.median(((s.hour.to_numpy() * 60 - (tm % 1440)) + 720) % 1440 - 720)); days = (tm.max() - tm.min()) / 1440
    e = [(pd.Timestamp(z["startDate"]).value / 6e10, float(z["grams"])) for z in c_ if (z.get("grams") or 0) > 0]
    e = [(t, g) for t, g in e if tm.min() <= t <= tm.max()]
    if not e or not np.isfinite([r.clk_b_med, r.clk_l_med, r.clk_d_med]).all(): return {}
    clk = np.array([r.clk_b_med, r.clk_l_med, r.clk_d_med]) * 60
    lh = np.array([((t + off) % 1440) for t, _ in e]); g = np.array([x for _, x in e])
    dist = np.min(np.abs(((lh[:, None] - clk[None, :]) + 720) % 1440 - 720), axis=1); meal = dist <= 60
    hist = np.bincount((lh[~meal] // 60).astype(int), minlength=24)
    return dict(meal_e_day=meal.sum() / days, snack_e_day=(~meal).sum() / days, snack_g_med=float(np.median(g[~meal])) if (~meal).any() else np.nan,
                snack_e_hours=json.dumps((hist / max(hist.sum(), 1)).round(4).tolist()))


def per_alias(path: Path, fn, cols=None):
    """Apply fn(alias) -> scalar or dict to each row; merge as columns (drop-then-merge, like the producers)."""
    t = pd.read_csv(path); out = []
    for a in t.alias:
        v = fn(a)
        out.append(dict(alias=a, **(v if isinstance(v, dict) else {cols: v})))
    r = pd.DataFrame(out)
    t = t.drop(columns=[c for c in r.columns if c != "alias" and c in t.columns]).merge(r, on="alias", how="left")
    t.to_csv(path, index=False)
    return t


# ---------------------------------------------------------------- main pipeline
def build(root: Path, aliases, out: Path, sensor_map, age_map, fit_dir: Path | None = None):
    t = build_base(root, aliases, sensor_map, age_map); t.to_csv(out, index=False)
    TP.add_raw_rates(str(out), root)
    TP.add_override_rates(str(out), root)
    ed = pd.concat([settings_edits(root, a) for a in aliases], ignore_index=True)
    ed_path = out.with_name(out.stem + "_settings_edits.csv"); ed.to_csv(ed_path, index=False)
    TP.add_edit_rates(str(out), str(ed_path), root)
    TP.add_basal_profile(str(out), root)
    TP.add_corr_exposure(str(out), root)
    TP.add_disruption_rates(str(out), root)
    TP.add_absorption_rates(str(out), root)
    TP.add_gap_rates(str(out), root)
    per_alias(out, lambda a: night_ratio(root, a), "night_ratio")
    per_alias(out, lambda a: treat_log_day(root, a), "treat_log_day")
    per_alias(out, lambda a: low_entered_share(root, a), "low_entered_share")
    per_alias(out, lambda a: skip_bfast(root, a), "skip_bfast")
    TP.add_meal_clock(str(out), root)
    TP.add_delivered_profile(str(out), root)          # quiet_min 240 (default) reproduces the live column
    per_alias(out, lambda a: lone_bolus_traits(root, a))
    per_alias(out, lambda a: unann_hours(root, a), "unann_hours")
    TP.add_slot_rates(str(out), root)
    TP.add_insulin_from_iob(str(out), root)
    nn = {a: night_need(root, a) for a in aliases}
    per_alias(out, lambda a: nn[a].get("need_all", np.nan), "night_need_ratio")
    TP.add_isf_yardstick(str(out), root)
    TP.add_entry_hours(str(out), root)
    t = pd.read_csv(out); es = {r.alias: entry_split(root, r) for _, r in t.iterrows()}
    per_alias(out, lambda a: es[a])
    TP.add_strategy_share(str(out), root)
    TP.add_entry_windows(str(out), root)
    TP.add_delivered_profile(str(out), root, no_pulse=True)
    TP.add_missed_cycles(str(out), root)
    per_alias(out, lambda a: far_unann(root, a), "far_unann")
    t = pd.read_csv(out)
    if fit_dir is not None:          # body-model fits (fit_body regression + segments), cohort shrinkage from the pilot tables
        t = apply_body_fits(t, fit_dir)
    for c in CLASS_B:
        t[c] = np.nan
    cols = list(pd.read_csv(LIVE, nrows=0).columns)
    for c in cols:
        if c not in t: t[c] = np.nan
    t = t[cols]; t.to_csv(out, index=False)
    return t


# ---------------------------------------------------------------- isf_body_mult and circ_* from the body fits
def apply_body_fits(t: pd.DataFrame, fit_dir: Path) -> pd.DataFrame:
    """isf_body_mult: templates.add_isf_body_fit's shrinkage, with tau² and the median from the pilot's fit_body_reg.csv and
    the donor's own b_all / se_all. circ_*: templates.add_circ_own with the pilot's seg_fit.csv reliability w, τ² and segment
    medians, and the donor's own segment fits."""
    t = t.copy()
    D = pd.read_csv(H / ".loop-eval/runs/2026-10-18-additive-workouts/fit_body_reg.csv"); D = D[D.b_all > 0]
    lb = np.log(D.b_all); rse = D.se_all / D.b_all
    tau2 = max(float(np.var(lb) - np.mean(rse ** 2)), 1e-4); med = float(np.median(lb))
    F = pd.read_csv(fit_dir / "fit_reg.csv").set_index("alias")
    t["isf_true_ys"] = t.isf_true
    mult = {}
    for a in t.alias:
        if a in F.index and F.loc[a, "b_all"] > 0:
            b, se = F.loc[a, "b_all"], F.loc[a, "se_all"]; w = tau2 / (tau2 + (se / b) ** 2)
            mult[a] = float(np.exp(med + w * (np.log(b) - med)) / np.exp(med))
    t["isf_body_mult"] = t.alias.map(mult)
    t["isf_true"] = t.isf_true_ys * t.isf_body_mult.fillna(1.0)
    # circ
    d = pd.read_csv(TDIR / "seg_fit.csv").set_index("alias")
    S = pd.read_csv(fit_dir / "fit_seg.csv").set_index("alias")
    def dev(X, sfx):
        L = np.log(X[[f"b_{g}{sfx}" for g in "BLD"]].where(lambda x: x > 0))
        return L.sub(L.mean(axis=1), axis=0)
    full, h1, h2 = dev(d, ""), dev(d, "_h1"), dev(d, "_h2")
    own = dev(S.reindex(columns=d.columns), "")
    for i, g in enumerate("BLD"):
        a_, b_ = h1.iloc[:, i], h2.iloc[:, i]; ok = a_.notna() & b_.notna()
        r = float(np.cov(a_[ok], b_[ok])[0, 1] / np.sqrt(a_[ok].var() * b_[ok].var())); w = max(0.0, 2 * r / (1 + r))
        f = full.iloc[:, i] - full.iloc[:, i].median(); tau2c = w * float(f.var())
        mu = {a: float(w * (own.loc[a].iloc[i] - full.iloc[:, i].median())) for a in t.alias if a in own.index and np.isfinite(own.loc[a].iloc[i])}
        t[f"circ_mu_{g}"] = t.alias.map(mu)
        t[f"circ_sd_{g}"] = np.where(t[f"circ_mu_{g}"].notna(), np.sqrt((1 - w) * tau2c), np.sqrt(tau2c))
        t[f"circ_mu_{g}"] = t[f"circ_mu_{g}"].fillna(0.0)
    return t


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("root"); ap.add_argument("aliases"); ap.add_argument("out")
    ap.add_argument("--sensor", default=None); ap.add_argument("--fit-dir", default=None)
    ap.add_argument("--sensor-csv", default=None); ap.add_argument("--age-csv", default=None)   # a pool's own tables (x pool)
    a = ap.parse_args()
    root = Path(a.root).expanduser(); al = a.aliases.split(",")
    if a.aliases.startswith("@"): al = list(pd.read_csv(a.aliases[1:]).alias)
    if a.sensor:
        sm = {x: a.sensor for x in al}
    elif a.sensor_csv:
        s = pd.read_csv(a.sensor_csv)
        s = s[~s.kind.isin(["unlabeled"]) & ~s.kind.str.startswith("other")]
        s = s.groupby(["alias", "kind"]).n.sum().reset_index().sort_values("n").groupby("alias").tail(1)
        sm = dict(zip(s.alias, s.kind.replace({"Libre 3 (twiist)": "Libre 3", "Libre (other)": "Libre 3"})))
    else:                                         # the pilot's own sensor-month table, as build_pilot reads it
        s = pd.read_csv(H / ".loop-eval/runs" / TP.SENSOR_MONTH)
        s = s[~s.kind.isin(["unlabeled"]) & ~s.kind.str.startswith("other")]
        s = s.groupby(["alias", "kind"]).n.sum().reset_index().sort_values("n").groupby("alias").tail(1)
        sm = dict(zip(s.alias, s.kind.replace({"Libre 3 (twiist)": "Libre 3", "Libre (other)": "Libre 3"})))
    ag = {}
    if a.age_csv:
        A = pd.read_csv(a.age_csv); ag = dict(zip(A.alias, A.age_years))
    elif (root / "age.csv").exists():
        A = pd.read_csv(root / "age.csv"); ag = dict(zip(A.alias, A.age_years))
    t = build(root, al, Path(a.out), sm, ag, Path(a.fit_dir) if a.fit_dir else None)
    print(t.T.to_string())
