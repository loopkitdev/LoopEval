"""Person templates: real donors' joint traits, the population a virtual person is drawn from.

A virtual person starts from one real donor's row (jittered), never from independent marginals:
behavior rates are bimodal and traits co-vary (evidence/05 §3 lesson 4), and drawing from people
keeps both. One row per eda-cohort donor, aliases only.

Columns and where each comes from (all eda tables under runs/2026-08-25-distributions/):
  truth      isf_true  = yardstick ISF (ice/isf_estimate.csv `isf_est`; eda lesson 54)
             basal_true = measured fasting insulin rate (ice/isf_estimate.csv `fb_uhr`)
  settings   isf, cr, basal, target, max_basal, max_bolus (isf_rules.csv: the person's schedule,
             time-weighted)
  person     age_years, tdd, strategy, pump, sensor, archetype, carb_g_day (announced),
             manual_bolus_day (isf_rules.csv); carb_entries_per_day, user_boluses_per_day (cohort.csv);
             formulation brand (formulation.csv)
  outcomes   tir, t54, t70, bg_mean, bg_cv (for comparison only — never an input to a person)

Usage:  python -m loopeval_analysis.patient_sim.templates   → writes runs/<date>-additive-templates/templates.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

DIST = "2026-08-25-distributions"


def runs_root() -> Path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "dist_views"))
    import style                                   # noqa: E402  (honours LOOPEVAL_RUNS)
    return Path(style.OUT).parent


def build() -> pd.DataFrame:
    d = runs_root() / DIST
    r = pd.read_csv(d / "isf_rules.csv")
    e = pd.read_csv(d / "ice" / "isf_estimate.csv")[["alias", "isf_est", "fb_uhr"]]
    f = pd.read_csv(d / "formulation.csv")[["alias", "brand", "category"]]
    c = pd.read_csv(d / "cohort.csv")[["alias", "carb_entries_per_day", "user_boluses_per_day",
                                       "auto_boluses_per_day", "t54", "bg_mean"]]
    keep = ["alias", "isf", "cr", "basal", "target", "max_basal", "max_bolus", "tdd", "carb_g_day",
            "manual_bolus_day", "pump", "sensor", "strategy", "archetype", "age_years",
            "tir", "t70", "t180", "bg_cv"]
    t = (r[keep].merge(e, on="alias").merge(c, on="alias", how="left")
         .merge(f, on="alias", how="left"))
    t = t.rename(columns={"isf_est": "isf_true", "fb_uhr": "basal_true", "brand": "insulin_brand"})
    t["insulin_brand"] = t["insulin_brand"].fillna("unknown")
    t = t[(t.isf_true > 0) & (t.basal_true > 0) & (t.tdd > 0)]
    return t.reset_index(drop=True)


def main() -> int:
    t = build()
    out = runs_root() / "2026-10-15-additive-templates"
    out.mkdir(parents=True, exist_ok=True)
    t.to_csv(out / "templates.csv", index=False)
    print(f"{len(t)} templates -> {out/'templates.csv'}")
    print((t.isf / t.isf_true).describe(percentiles=[.1, .5, .9]).round(2).to_string())
    print((t.basal / t.basal_true).describe(percentiles=[.1, .5, .9]).round(2).to_string())
    return 0



# ------------------------------------------------------------------------------------------------
# Pilot templates: the ice role's 207 donors, whose every meal pulse, correction and rescue is
# labeled (ice_v32/meals/*.parquet). Richer behavior than the eda cohort; aliases i001–i207.
# ------------------------------------------------------------------------------------------------
PILOT = Path.home() / ".loop-eval/ice_v32"
SENSOR_MONTH = "2026-10-15-additive-sensor/sensor_month.csv"
_FORM = {"rapidActingAdult": "humalog", "rapidActingChild": "humalog", "fiasp": "fiasp", "lyumjev": "lyumjev",
         "afrezza": "humalog"}


def _tw_mean(segs, key="value"):
    import numpy as np
    w = v = 0.0
    for s in segs:
        d = (pd.Timestamp(s["endDate"]) - pd.Timestamp(s["startDate"])).total_seconds()
        val = s[key] if key in s else (s["lowerBound"] + s["upperBound"]) / 2
        w += d; v += d * val
    return v / w if w else np.nan


def _free(corr: pd.DataFrame):
    """A lone manual bolus is FOOD dosed by hand (no carb entry) when it exceeds Loop's recommendation
    by > 20% + 0.2 U, or is given below 140 mg/dL; otherwise it is a correction."""
    if not len(corr) or "units" not in corr:
        return pd.Series(False, index=corr.index)
    return (corr.units > 1.2 * corr.rec.fillna(0) + 0.2) | (corr.bg < 140)


def build_pilot() -> pd.DataFrame:
    import json
    import numpy as np
    P = pd.read_csv(PILOT / "persons.csv")
    sm = pd.read_csv(runs_root() / SENSOR_MONTH)
    sm = sm[~sm.kind.isin(["unlabeled"]) & ~sm.kind.str.startswith("other")]
    sensor = sm.groupby(["alias", "kind"]).n.sum().reset_index().sort_values("n").groupby("alias").tail(1)
    sensor = dict(zip(sensor.alias, sensor.kind.replace({"Libre 3 (twiist)": "Libre 3", "Libre (other)": "Libre 3"})))
    rows = []
    for _, p in P.iterrows():
        a = p.alias; d = PILOT / "full" / a
        try:
            th = json.load(open(d / "therapy.json"))
            meals = pd.read_parquet(PILOT / "meals" / f"{a}.parquet")
            corr = pd.read_parquet(PILOT / "meals" / f"{a}_corrections.parquet")
            g = pd.Series([x["quantity"] for x in json.load(open(d / "glucose.json"))], dtype=float)
            doses = json.load(open(d / "doses.json"))
        except Exception:                                      # noqa: BLE001
            continue
        days = max(float(p.clean_days), 1.0)
        span = (pd.Timestamp(th["basal"][-1]["endDate"]) - pd.Timestamp(th["basal"][0]["startDate"])).days or days
        auto = sum(1 for x in doses if x["deliveryType"] == "bolus" and x.get("automatic"))
        nr = meals[~meals.rescue]; rs = meals[meals.rescue]
        hours = np.histogram(nr.hour.to_numpy() % 24, bins=24, range=(0, 24))[0]
        ann = nr[nr.announced]
        r = dict(alias=a, tdd=float(p.tdd), isf_true=float(p.isf_tdd),
                 isf=_tw_mean(th["sensitivity"]), cr=_tw_mean(th["carbRatio"]), basal=_tw_mean(th["basal"]),
                 target=_tw_mean(th["target"]), max_basal=float(th["maxBasalRate"]), max_bolus=float(th["maxBolus"]),
                 suspend=float(th.get("suspendThreshold", 70.0)),
                 strategy="bolus" if auto / span > 2 else "temp", pump="Omnipod",
                 sensor=sensor.get(a, "Dexcom G7"), insulin_brand=_FORM.get(th.get("insulinType", ""), "humalog"),
                 age_years=np.nan, basal_true=np.nan, archetype="",
                 meals_per_day=len(nr) / span, meal_hours=json.dumps((hours / max(hours.sum(), 1)).round(4).tolist()),
                 meal_size_med=float(nr.size_g.median()), meal_size_logsd=float(np.log(nr.size_g).std()),
                 announced_share=float(nr.announced.mean()) if len(nr) else 0.0,
                 estimate_ratio=float(ann.estimate_ratio.median()) if len(ann) else np.nan,
                 bolus_lead_min=float(ann.bolus_lead_min.median()) if ann.bolus_lead_min.notna().any() else np.nan,
                 p_bolus_ann=float((ann.bolus_u > 0).mean()) if len(ann) else np.nan,
                 bolus_ratio=float(ann.bolus_ratio.median()) if ann.bolus_ratio.notna().any() else np.nan,
                 corrections_per_day=len(corr) / span, corr_bg_med=float(corr.bg.median()) if len(corr) else np.nan,
                 corr_ratio=float((corr.units / corr.rec.replace(0, np.nan)).median()) if len(corr) else np.nan,
                 # lone boluses well above Loop's recommendation, or at normal glucose: food dosed by hand
                 # without a carb entry (Groat 2017: carbs entered for 2/3 of boluses); the rest are corrections
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
    t = pd.DataFrame(rows)
    age = pd.read_csv(PILOT / "age.csv")
    acol = next(c for c in age.columns if "age" in c.lower() and "group" not in c.lower())
    t = t.drop(columns="age_years").merge(age[["alias", acol]].rename(columns={acol: "age_years"}), on="alias", how="left")
    return t


def main_pilot() -> int:
    t = build_pilot()
    out = runs_root() / "2026-10-15-additive-templates"
    out.mkdir(parents=True, exist_ok=True)
    t.to_csv(out / "templates_pilot.csv", index=False)
    print(f"{len(t)} pilot templates -> {out/'templates_pilot.csv'}")
    print(t[["tdd", "isf", "isf_true", "meals_per_day", "announced_share", "corrections_per_day", "rescues_per_day",
             "tir", "t54"]].describe(percentiles=[.1, .5, .9]).round(2).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main_pilot() if "pilot" in sys.argv else main())


def add_raw_rates(path: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32"):
    """Per donor, behavior rates counted from the RAW record (carbs.json, doses.json), the way the simulator's own
    records are counted: carb entries/day (entries within 30 min merged), manual boluses/day, of which with an entry
    (±30 min), top-ups (≤ 60 min after a bolus, no entry) and lone. The ice-labeled carb_entries_per_day counts only
    entries the labeler attached to a pulse (2.07/day median vs 3.0 raw; LESSONS 36)."""
    import json
    import numpy as np
    t = pd.read_csv(path)
    out = []
    for a in t.alias:
        p = ice_root / "full" / a
        if not (p / "doses.json").exists():
            out.append(dict(alias=a)); continue
        d = json.load(open(p / "doses.json")); c = json.load(open(p / "carbs.json")); g = json.load(open(p / "glucose.json"))
        days = (pd.Timestamp(g[-1]["startDate"]) - pd.Timestamp(g[0]["startDate"])).total_seconds() / 86400
        ct = np.sort([pd.Timestamp(x["startDate"]).value // 60_000_000_000 for x in c])
        bt = np.sort([pd.Timestamp(x["startDate"]).value // 60_000_000_000 for x in d
                      if x["deliveryType"] == "bolus" and not x.get("automatic") and x.get("volume", 0) > 0])
        bu = sum(x["volume"] for x in d if x["deliveryType"] == "bolus" and not x.get("automatic") and x.get("volume", 0) > 0)
        ent = (1 + int(np.sum(np.diff(ct) > 30))) if len(ct) else 0
        near = np.array([np.any(np.abs(ct - b) <= 30) for b in bt]) if len(ct) and len(bt) else np.zeros(len(bt), bool)
        w60 = np.r_[False, np.diff(bt) <= 60] if len(bt) else np.zeros(0, bool)
        eg = sum((x.get("grams") or 0) for x in c if (x.get("grams") or 0) > 0)
        out.append(dict(alias=a, entries_raw=ent / days, entered_g_raw=eg / days, boluses_raw=len(bt) / days, bolus_entry_raw=near.sum() / days,
                        topups_raw=(w60 & ~near).sum() / days, lone_raw=(~w60 & ~near).sum() / days, manual_u_day=bu / days))
    r = pd.DataFrame(out)
    t = t.drop(columns=[c for c in r.columns if c != "alias" and c in t.columns]).merge(r, on="alias", how="left")
    t.to_csv(path, index=False)
    return t


def add_override_rates(path: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32"):
    """Per donor, Temporary Override use by class (LESSONS 40), from the export's therapy.json overrideWindows:
      less  factor < 0.99 — less insulin (activity, low prevention): starts ~126 mg/dL and falling, afternoon
      more  factor > 1.01 — more insulin (reaction to highs): starts ~210 and rising, evening
      tgt   target only — mostly a lowered target ahead of eating (Loop's pre-meal preset), ~0.8 h
    rate/day, median factor, target low/high and duration (h) per class."""
    import json
    import numpy as np
    t = pd.read_csv(path)
    out = []
    for a in t.alias:
        p = ice_root / "full" / a / "therapy.json"
        row = dict(alias=a)
        if p.exists():
            th = json.load(open(p))
            ow = th.get("overrideWindows", [])
            span = (pd.Timestamp(th["basal"][-1]["endDate"]) - pd.Timestamp(th["basal"][0]["startDate"])).total_seconds() / 86400
            W = pd.DataFrame([dict(f=w.get("factor", np.nan), lo=w.get("targetLo", np.nan), hi=w.get("targetHi", np.nan),
                                   d=(pd.Timestamp(w["end"]) - pd.Timestamp(w["start"])).total_seconds() / 3600) for w in ow])
            for cls, m in (("less", W.f < 0.99), ("more", W.f > 1.01),
                           ("tgt", W.f.isna() | ((W.f >= 0.99) & (W.f <= 1.01)))) if len(W) else ():
                x = W[m]
                row.update({f"ov_{cls}_day": len(x) / span,
                            f"ov_{cls}_f": float(x.f.median()) if len(x) and x.f.notna().any() else np.nan,
                            f"ov_{cls}_lo": float(x.lo.median()) if len(x) and x.lo.notna().any() else np.nan,
                            f"ov_{cls}_hi": float(x.hi.median()) if len(x) and x.hi.notna().any() else np.nan,
                            f"ov_{cls}_h": float(x.d.median()) if len(x) else np.nan})
        out.append(row)
    r = pd.DataFrame(out)
    t = t.drop(columns=[c for c in r.columns if c != "alias" and c in t.columns]).merge(r, on="alias", how="left")
    t.to_csv(path, index=False)
    return t


def add_edit_rates(path: str, edits_csv: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32"):
    """Per donor, settings edits per day for basal, ISF and CR (day-to-day changes of the time-weighted daily
    schedule mean in the RAW schedules, |log change| > 1%; LESSONS 41). Pooled size: median 3.6%, p90 14%."""
    import json
    t = pd.read_csv(path)
    e = pd.read_csv(edits_csv)
    out = []
    for a in t.alias:
        p = ice_root / "full" / a / "therapy.json"
        row = dict(alias=a)
        if p.exists():
            th = json.load(open(p))
            span = (pd.Timestamp(th["basal"][-1]["endDate"]) - pd.Timestamp(th["basal"][0]["startDate"])).total_seconds() / 86400
            x = e[e.alias == a]
            for k, s in (("basal", "rawBasal"), ("isf", "rawSensitivity"), ("cr", "rawCarbRatio")):
                row[f"edit_{k}_day"] = float((x.setting == s).sum() / span)
        out.append(row)
    r = pd.DataFrame(out)
    t = t.drop(columns=[c for c in r.columns if c != "alias" and c in t.columns]).merge(r, on="alias", how="left")
    t.to_csv(path, index=False)
    return t


def add_corr_exposure(path: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32"):
    """Per donor, the share of WAKING time (07–23 h) their CGM sat above their own correction level (median
    correction glucose − 20), the exposure the correction hazard is sized by (LESSONS 42)."""
    import json
    import numpy as np
    t = pd.read_csv(path)
    out = []
    for _, r in t.iterrows():
        p = ice_root / "full" / r.alias / "glucose.json"
        row = dict(alias=r.alias)
        if p.exists() and np.isfinite(r.get("corr_bg_med", np.nan)):
            g = json.load(open(p))
            from .quiet import local_offset, to_local
            # waking hours in the donor's LOCAL time (the export is UTC)
            s = pd.Series([x["quantity"] for x in g], index=to_local(pd.to_datetime([x["startDate"] for x in g]),
                                                                    local_offset(r.alias, ice_root)))
            w = s[(s.index.hour >= 7) & (s.index.hour < 23)]
            thr = float(np.clip(r.corr_bg_med - 20, 130, 300))
            row["corr_exposure"] = float((w > thr).mean())
        out.append(row)
    r = pd.DataFrame(out)
    t = t.drop(columns=[c for c in r.columns if c != "alias" and c in t.columns]).merge(r, on="alias", how="left")
    t.to_csv(path, index=False)
    return t


def add_basal_profile(path: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32"):
    """Per donor, the 24-h shape of their scheduled (raw) basal in LOCAL time, normalized to mean 1: the profile
    they tuned on their own body (LESSONS 48). Local offset from the ice steps (local `hour` vs UTC t0)."""
    import json
    import numpy as np
    t = pd.read_csv(path)
    out = []
    for a in t.alias:
        row = dict(alias=a)
        p = ice_root / "full" / a / "therapy.json"; sp = ice_root / "steps" / f"{a}.parquet"
        if p.exists() and sp.exists():
            st = pd.read_parquet(sp, columns=["t0", "hour"]).dropna().iloc[::50]
            off = ((st.hour - (st.t0.dt.hour + st.t0.dt.minute / 60.0)) % 24).round().mode().iloc[0]
            th = json.load(open(p))
            prof = np.zeros(24); w = np.zeros(24)
            for seg in th["rawBasal"]:
                s0, s1 = pd.Timestamp(seg["startDate"]), pd.Timestamp(seg["endDate"])
                rng = pd.date_range(s0.floor("h"), s1, freq="h")
                for h in rng:
                    lo, hi = max(h, s0), min(h + pd.Timedelta(hours=1), s1)
                    if hi <= lo: continue
                    k = int((h.hour + off) % 24); dur = (hi - lo).total_seconds()
                    prof[k] += seg["value"] * dur; w[k] += dur
            prof = np.where(w > 0, prof / np.maximum(w, 1), np.nan)
            if np.isfinite(prof).all() and prof.mean() > 0:
                row["basal_profile"] = json.dumps((prof / prof.mean()).round(4).tolist())
        out.append(row)
    r = pd.DataFrame(out)
    t = t.drop(columns=[c for c in r.columns if c != "alias" and c in t.columns]).merge(r, on="alias", how="left")
    t.to_csv(path, index=False)
    return t


SLOTS = (("B", 4.0, 10.5), ("L", 10.5, 15.5), ("D", 15.5, 22.0))
# labeled g-eq per entered gram of announced pulses by window, pooled over the G7 donors (LESSONS 231): the labeler reads a
# breakfast gram as more than a dinner gram (morning insulin resistance, fat / protein), so window g-eq is not window grams
SLOT_LR_POOLED = (1.32, 1.15, 1.05)


def add_slot_rates(path: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32"):
    """Per donor and main-meal window (local 04–10:30 / 10:30–15:30 / 15:30–22), from their labeled non-rescue
    pulses: grams eaten per day (`slot_g`), the share of pulses that carried a carb entry (`slot_ann`) and labeled g-eq per
    entered gram of the announced ones (`slot_lr`; pooled value below 10 pulses). Through
    the same labeler, simulated people ate the donors' grams at lunch and dinner but announced breakfast more and
    lunch and dinner less (17/19/23 vs 10/27/31 g/day entered; LESSONS 51)."""
    import json
    import numpy as np
    t = pd.read_csv(path)
    out = []
    for a in t.alias:
        row = dict(alias=a)
        p = ice_root / "meals" / f"{a}.parquet"
        if p.exists():
            m = pd.read_parquet(p); m = m[~m.rescue]
            days = (m.onset.max() - m.onset.min()).total_seconds() / 86400 if len(m) > 1 else 0
            h = m.hour.to_numpy() % 24
            g, ann, lr = [], [], []
            ent = m.entry_g.fillna(0).to_numpy() if "entry_g" in m else np.zeros(len(m))
            for (_, lo, hi), lr0 in zip(SLOTS, SLOT_LR_POOLED):
                s = (h >= lo) & (h < hi)
                g.append(float(m.size_g.fillna(0).to_numpy()[s].sum() / days) if days > 0 else np.nan)
                ann.append(float(m.announced.to_numpy()[s].astype(bool).mean()) if s.sum() >= 5 else np.nan)
                a = s & m.announced.to_numpy().astype(bool) & (ent > 0)
                lr.append(float(m.size_g.fillna(0).to_numpy()[a].sum() / ent[a].sum()) if a.sum() >= 10 else lr0)
            if days >= 7 and np.isfinite(g).all() and sum(g) > 0:
                row["slot_g"] = json.dumps([round(x, 2) for x in g])
            if np.isfinite(ann).all():
                row["slot_ann"] = json.dumps([round(x, 3) for x in ann])
            if np.isfinite(lr).all():
                row["slot_lr"] = json.dumps([round(x, 3) for x in lr])
        out.append(row)
    r = pd.DataFrame(out)
    t = t.drop(columns=[c for c in r.columns if c != "alias" and c in t.columns]).merge(r, on="alias", how="left")
    t.to_csv(path, index=False)
    return t



def add_absorption_rates(path: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32"):
    """Per donor, the absorption time entered with each carb entry (carbs.json absorptionTime): shares of fast
    (≤ 1 h) and slow (≥ 4 h) entries, separately for small (≤ 20 g) and larger entries. Donors: 14% of entries 0.5 h,
    mostly ~15 g snacks; 5% 5 h. Entries made below 80 mg/dL (rescues) are left out (LESSONS 102)."""
    import json
    t = pd.read_csv(path)
    out = []
    for a in t.alias:
        row = dict(alias=a)
        p = ice_root / "full" / a / "carbs.json"
        if p.exists():
            c = [x for x in json.load(open(p)) if x.get("absorptionTime") and (x.get("grams") or 0) > 0]
            # rescues are logged separately in the sim (0.5 h, behavior p_log_rescue): drop entries made below 80 mg/dL
            g = json.load(open(ice_root / "full" / a / "glucose.json"))
            gt = np.array([pd.Timestamp(x["startDate"]).value // 60_000_000_000 for x in g]); gv = np.array([x["quantity"] for x in g], float)
            o = np.argsort(gt); gt, gv = gt[o], gv[o]
            def _bg(ts):
                m = pd.Timestamp(ts).value // 60_000_000_000; j = np.searchsorted(gt, m) - 1
                return gv[j] if j >= 0 and m - gt[j] <= 15 else np.nan
            c = [x for x in c if not (_bg(x["startDate"]) < 80)]
            for lab, sel in (("s", lambda g: g <= 20), ("l", lambda g: g > 20)):
                v = [x["absorptionTime"] / 3600 for x in c if sel(x["grams"])]
                if len(v) >= 10:
                    v = np.asarray(v)
                    row[f"abs_fast_{lab}"] = float(np.mean(v <= 1.0)); row[f"abs_slow_{lab}"] = float(np.mean(v >= 4.0))
        out.append(row)
    r = pd.DataFrame(out)
    t = t.drop(columns=[c for c in r.columns if c != "alias" and c in t.columns]).merge(r, on="alias", how="left")
    t.to_csv(path, index=False)
    return t

def add_disruption_rates(path: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32"):
    """Per donor, from disruptions.csv: Loop-offline and merged mixed windows of ≤ 6 h per day (`offline_day`) and
    pump-error cycles per day (`perr_day`) (LESSONS 60)."""
    import json
    t = pd.read_csv(path)
    out = []
    for a in t.alias:
        row = dict(alias=a)
        p = ice_root / "full" / a / "disruptions.csv"
        if p.exists():
            d = pd.read_csv(p)
            g = json.load(open(ice_root / "full" / a / "glucose.json"))
            days = (pd.Timestamp(g[-1]["startDate"]) - pd.Timestamp(g[0]["startDate"])).total_seconds() / 86400
            dur = (pd.to_datetime(d.end, format="ISO8601") - pd.to_datetime(d.start, format="ISO8601")).dt.total_seconds() / 60
            if days > 7:
                row["offline_day"] = float((d.reason.isin(["loop_offline", "disruption"]) & (dur >= 1) & (dur <= 360)).sum() / days)
                row["perr_day"] = float((d.reason == "pump_error").sum() / days)
        out.append(row)
    r = pd.DataFrame(out)
    t = t.drop(columns=[c for c in r.columns if c != "alias" and c in t.columns]).merge(r, on="alias", how="left")
    t.to_csv(path, index=False)
    return t


def add_gap_rates(path: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32"):
    """Per donor, CGM gaps per day over the whole record: short (7–32 min between readings) and long (32 min–12 h),
    the bins of sensor.MEASURED_GAPS. Donors differ several-fold (G7 short gaps p10/p90 0.6/8.6 a day), which the
    family rate alone leaves out (LESSONS 107)."""
    import json
    t = pd.read_csv(path)
    out = []
    for a in t.alias:
        row = dict(alias=a)
        p = ice_root / "full" / a / "glucose.json"
        if p.exists():
            m = np.unique(np.array([pd.Timestamp(x["startDate"]).value // 1_000_000_000 for x in json.load(open(p))]) / 60.0)
            d = np.diff(m); days = (m[-1] - m[0]) / 1440 if len(m) > 1 else 0
            if days > 7:
                row["gap_short"] = float(((d >= 7) & (d < 32)).sum() / days)
                row["gap_long"] = float(((d >= 32) & (d < 722)).sum() / days)
        out.append(row)
    r = pd.DataFrame(out)
    t = t.drop(columns=[c for c in r.columns if c != "alias" and c in t.columns]).merge(r, on="alias", how="left")
    t.to_csv(path, index=False)
    return t


def add_entry_hours(path: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32"):
    """Per donor, the local-hour histogram of carb entries (carbs.json, grams > 0), as `entry_hours` (24 shares).
    With `meal_hours` (the labeler's eating clock) it gives the hour-by-hour chance an eating occasion is entered:
    donors eat at night (labeled pulses) but rarely enter it (LESSONS 123)."""
    import json
    from .quiet import local_offset, to_local
    t = pd.read_csv(path)
    out = []
    for a in t.alias:
        row = dict(alias=a)
        p = ice_root / "full" / a / "carbs.json"
        if p.exists():
            c = [x for x in json.load(open(p)) if (x.get("grams") or 0) > 0]
            if len(c) >= 20:
                lt = to_local(pd.to_datetime([x["startDate"] for x in c], utc=True, format="ISO8601"), local_offset(a, ice_root))
                h = np.histogram(np.asarray(lt.hour + lt.minute / 60.0), bins=24, range=(0, 24))[0].astype(float)
                row["entry_hours"] = json.dumps((h / h.sum()).round(4).tolist())
        out.append(row)
    r = pd.DataFrame(out)
    t = t.drop(columns=[c for c in r.columns if c != "alias" and c in t.columns]).merge(r, on="alias", how="left")
    t.to_csv(path, index=False)
    return t


def add_meal_clock(path: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32"):
    """Per donor, the median and SD (hours) of the day's largest carb ENTRY in each window, local time:
    B 04–10.5 h (≥ 15 g), L 10.5–15.5 h (≥ 20 g), D ≥ 15.5 h (≥ 30 g; no upper bound, so late dinners count).
    Entries need no labeler; the labeled largest-pulse version was near-uniform within each window (LESSONS 123).
    Columns `clk_{b,l,d}_med`, `clk_{b,l,d}_sd`; a window with < 7 days stays NaN (population draw)."""
    import json
    from .quiet import local_offset, to_local
    t = pd.read_csv(path)
    out = []
    for a in t.alias:
        row = dict(alias=a)
        p = ice_root / "full" / a / "carbs.json"
        if p.exists():
            c = [x for x in json.load(open(p)) if (x.get("grams") or 0) > 0]
            if c:
                lt = pd.DatetimeIndex(to_local(pd.to_datetime([x["startDate"] for x in c], utc=True, format="ISO8601"), local_offset(a, ice_root)))
                D = pd.DataFrame(dict(h=np.asarray(lt.hour + lt.minute / 60), g=[x["grams"] for x in c], day=lt.floor("D")))
                for k, a0, a1, gmin in (("b", 4, 10.5, 15), ("l", 10.5, 15.5, 20), ("d", 15.5, 24.0, 30)):
                    x = D[(D.h >= a0) & (D.h < a1) & (D.g >= gmin)]
                    if x.day.nunique() >= 7:
                        top = x.loc[x.groupby("day").g.idxmax()]
                        row[f"clk_{k}_med"] = float(top.h.median()); row[f"clk_{k}_sd"] = float(top.h.std())
        out.append(row)
    r = pd.DataFrame(out)
    t = t.drop(columns=[c for c in r.columns if c != "alias" and c in t.columns]).merge(r, on="alias", how="left")
    t.to_csv(path, index=False)
    return t


def add_delivered_profile(path: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32"):
    """Per donor, the 24-h shape (local hour, mean 1) of the insulin their Loop actually DELIVERED on quiet steps: no carb
    entry and no manual bolus in the prior 4 h, not disrupted. Delivered basal + automatic boluses per hour is what the
    closed loop found the body needed while fasting, the evidence the schedule only approximates (LESSONS 214).
    Column `basal_profile_deliv`; hours with < 20 quiet hours of data stay NaN (then the column is left empty)."""
    import json
    import numpy as np
    t = pd.read_csv(path)
    out = []
    for a in t.alias:
        row = dict(alias=a)
        sp = ice_root / "steps" / f"{a}.parquet"
        if sp.exists():
            s = pd.read_parquet(sp).sort_values("t1")
            tm = (s.t1.astype("int64") / 6e10).to_numpy()
            ev = np.sort(tm[(s.carbs_g.fillna(0) > 0).to_numpy() | (s.bolus_manual_u.fillna(0) > 0).to_numpy()])
            k = np.searchsorted(ev, tm, side="right") - 1
            dis = s.disrupted.fillna(False).to_numpy(bool)
            quiet = (~((k >= 0) & (tm - np.where(k >= 0, ev[np.clip(k, 0, None)], -1e18) < 240)) & ~dis) if len(ev) else ~dis
            rate = ((s.basal_u.fillna(0) + s.bolus_auto_u.fillna(0)) / (s.dt / 60.0)).to_numpy()
            q = pd.DataFrame(dict(h=np.floor(s.hour.to_numpy()[quiet]).astype(int) % 24, r=rate[quiet], dt=s.dt.to_numpy()[quiet]))
            g = q.groupby("h"); hrs = g.dt.sum() / 60.0; prof = g.r.mean().reindex(range(24))
            if (hrs.reindex(range(24)).fillna(0) >= 20).all() and prof.mean() > 0:
                row["basal_profile_deliv"] = json.dumps((prof / prof.mean()).round(4).tolist())
        out.append(row)
    r = pd.DataFrame(out)
    t = t.drop(columns=[c for c in r.columns if c != "alias" and c in t.columns]).merge(r, on="alias", how="left")
    t.to_csv(path, index=False)
    return t
