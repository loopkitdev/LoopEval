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


def add_strategy_share(path: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32", min_auto: int = 5):
    """Per donor, the share of active days (>= 20 dose records) run on the automatic-bolus strategy: days with at least
    `min_auto` automatic boluses (autobolus days carry a median 60; temp-basal days none). The template's `strategy`
    is a whole-record call (> 2 automatic boluses a day), so a donor who switched mid-record is all one or the other;
    person.py draws each twin's strategy from this share (LESSONS 331)."""
    import json
    t = pd.read_csv(path)
    out = []
    for a in t.alias:
        row = dict(alias=a)
        p = ice_root / "full" / a / "doses.json"
        if p.exists():
            d = pd.DataFrame([(x["startDate"], x["deliveryType"] == "bolus" and bool(x.get("automatic")) and (x.get("volume") or 0) > 0)
                              for x in json.load(open(p))], columns=["t", "auto"])
            d["day"] = pd.to_datetime(d.t, format="ISO8601").dt.floor("D")
            g = d.groupby("day").agg(n=("auto", "size"), auto=("auto", "sum"))
            g = g[g.n >= 20]
            if len(g) >= 7:
                row["auto_day_share"] = float((g.auto >= min_auto).mean())
        out.append(row)
    r = pd.DataFrame(out)
    t = t.drop(columns=[c for c in r.columns if c != "alias" and c in t.columns]).merge(r, on="alias", how="left")
    t.to_csv(path, index=False)
    return t


def add_circ_own(path: str, seg_csv: str):
    """Per donor, the breakfast / lunch / dinner sensitivity pattern from `fit_body --regression --segments` (b per clock
    segment B 06–11, L 11–17, D 17–24 local): log b minus the donor's mean over segments, centred on the cohort median
    (no population pattern, Hinshaw 2013). Reliability w per segment from alternate-week halves (Spearman–Brown); stored as
    the posterior mean w·dev (`circ_mu_*`) and SD sqrt((1−w)·τ²) with τ² = w·var(dev) (`circ_sd_*`); donors without a fit
    get mean 0 and SD τ (the prior). person.py draws each twin's levels from these (LESSONS 335)."""
    d = pd.read_csv(seg_csv).set_index("alias")
    def dev(sfx):
        L = np.log(d[[f"b_{g}{sfx}" for g in "BLD"]].where(lambda x: x > 0))
        return L.sub(L.mean(axis=1), axis=0)
    full, h1, h2 = dev(""), dev("_h1"), dev("_h2")
    t = pd.read_csv(path)
    for i, g in enumerate("BLD"):
        a, b = h1.iloc[:, i], h2.iloc[:, i]; ok = a.notna() & b.notna()
        r = float(np.cov(a[ok], b[ok])[0, 1] / np.sqrt(a[ok].var() * b[ok].var())); w = max(0.0, 2 * r / (1 + r))
        f = full.iloc[:, i] - full.iloc[:, i].median(); tau2 = w * float(f.var())
        mu = (w * f).rename(f"circ_mu_{g}"); t = t.drop(columns=[c for c in (f"circ_mu_{g}", f"circ_sd_{g}") if c in t])
        t = t.merge(mu, left_on="alias", right_index=True, how="left")
        t[f"circ_sd_{g}"] = np.where(t[f"circ_mu_{g}"].notna(), np.sqrt((1 - w) * tau2), np.sqrt(tau2))
        t[f"circ_mu_{g}"] = t[f"circ_mu_{g}"].fillna(0.0)
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


def add_entry_windows(path: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32"):
    """Per donor, entered carbohydrate grams per day in the three meal windows (local 04–10.5 / 10.5–15.5 / 15.5–22 h,
    carbs.json, grams > 0) as `ent_win` (JSON triple): the like-for-like target for the per-window entry chance (LESSONS 341)."""
    import json
    from .quiet import local_offset, to_local
    t = pd.read_csv(path)
    out = []
    for a in t.alias:
        row = dict(alias=a)
        p = ice_root / "full" / a / "carbs.json"
        if p.exists():
            c = [x for x in json.load(open(p)) if (x.get("grams") or 0) > 0]
            g = json.load(open(ice_root / "full" / a / "glucose.json"))
            days = (pd.Timestamp(g[-1]["startDate"]) - pd.Timestamp(g[0]["startDate"])).total_seconds() / 86400
            if len(c) >= 20 and days > 7:
                lt = to_local(pd.to_datetime([x["startDate"] for x in c], utc=True, format="ISO8601"), local_offset(a, ice_root))
                h = np.asarray(lt.hour + lt.minute / 60.0); gr = np.array([x["grams"] for x in c], float)
                w = [float(gr[(h >= lo) & (h < hi)].sum() / days) for lo, hi in ((4, 10.5), (10.5, 15.5), (15.5, 22))]
                row["ent_win"] = json.dumps([round(x, 2) for x in w])
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


def add_delivered_profile(path: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32", quiet_min: float = 240.0,
                          no_pulse: bool = False, pulse_tail: float = 120.0):
    """Per donor, the 24-h shape (local hour, mean 1) of the insulin their Loop actually DELIVERED on quiet steps: no carb
    entry and no manual bolus in the prior 4 h, not disrupted. Delivered basal + automatic boluses per hour is what the
    closed loop found the body needed while fasting, the evidence the schedule only approximates (LESSONS 214).
    `quiet_min` 360 keeps late-evening eating out of the night hours (LESSONS 251).
    Column `basal_profile_deliv`; hours with < 20 quiet hours of data stay NaN (then the column is left empty).
    `no_pulse` (LESSONS 371): also drop steps inside any labelled glucose pulse (onset to end + `pulse_tail` min), so Loop's
    answer to unlogged eating is not read as the fasting body's need; column `basal_profile_deliv_np`."""
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
            quiet = (~((k >= 0) & (tm - np.where(k >= 0, ev[np.clip(k, 0, None)], -1e18) < quiet_min)) & ~dis) if len(ev) else ~dis
            mp = ice_root / "meals" / f"{a}.parquet"
            if no_pulse and mp.exists():
                M = pd.read_parquet(mp)
                on = (M.onset.astype("int64") / 6e10).to_numpy(); en = (M.end.astype("int64") / 6e10).to_numpy() + pulse_tail
                o = np.argsort(on); on, en = on[o], np.maximum.accumulate(en[o])
                j = np.searchsorted(on, tm, side="right") - 1
                quiet &= ~((j >= 0) & (tm <= np.where(j >= 0, en[np.clip(j, 0, None)], -1e18)))
            rate = ((s.basal_u.fillna(0) + s.bolus_auto_u.fillna(0)) / (s.dt / 60.0)).to_numpy()
            q = pd.DataFrame(dict(h=np.floor(s.hour.to_numpy()[quiet]).astype(int) % 24, r=rate[quiet], dt=s.dt.to_numpy()[quiet]))
            g = q.groupby("h"); hrs = g.dt.sum() / 60.0; prof = g.r.mean().reindex(range(24))
            need = 20.0
            if no_pulse:                     # pulses cover much of the day: thinner hours, gaps filled around the clock
                need = 0.0; hh = hrs.reindex(range(24)).fillna(0)
                prof = prof.where(hh >= 6.0)
                if prof.notna().sum() >= 16:
                    x = np.arange(72); y = np.tile(prof.to_numpy(), 3); k_ = np.isfinite(y)
                    prof = pd.Series(np.interp(x, x[k_], y[k_])[24:48], index=range(24))
            if (hrs.reindex(range(24)).fillna(0) >= need).all() and prof.notna().all() and prof.mean() > 0:
                row["basal_profile_deliv_np" if no_pulse else "basal_profile_deliv"] = json.dumps((prof / prof.mean()).round(4).tolist())
        out.append(row)
    r = pd.DataFrame(out)
    t = t.drop(columns=[c for c in r.columns if c != "alias" and c in t.columns]).merge(r, on="alias", how="left")
    t.to_csv(path, index=False)
    return t


def add_insulin_from_iob(path: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32", margin: float = 0.2):
    """Which insulin curve each donor's Loop ran, from Loop's own recorded IOB (LESSONS 248). Net-basal IOB is rebuilt from
    doses.json minus the therapy basal over 10 days (export days 3–13) with Loop's exponential model (10-min delay, DIA 360)
    at peak 75 (rapid-acting adult) and peak 55 (ultra-rapid), against loop_iob.parquet. A donor recorded as rapid-acting
    whose ultra-rapid RMSE is lower by more than `margin` (relative) is relabelled fiasp; column insulin_iob_infer holds the
    pick for every donor. Recorded Fiasp/Lyumjev donors matched the ultra-rapid curve 51 of 52."""
    import json
    import numpy as np

    def kernel(peak, dia=360.0, delay=10.0):
        tau = peak * (1 - peak / dia) / (1 - 2 * peak / dia); a = 2 * tau / dia
        s_ = 1 / (1 - a + (1 + a) * np.exp(-dia / tau)); t = np.arange(0, dia + delay + 1) - delay
        f = np.where(t <= 0, 1.0, 1 - s_ * (1 - a) * ((t ** 2 / (tau * dia * (1 - a)) - t / tau - 1) * np.exp(-t / tau) + 1))
        return np.where(t >= dia, 0.0, f)

    ks = {"adult": kernel(75.0), "fast": kernel(55.0)}
    ts = lambda s: pd.Timestamp(s).value / 6e10
    li = pd.read_parquet(ice_root / "loop_iob.parquet"); li["tm"] = li.t.astype("int64") / 6e10
    t = pd.read_csv(path); picks = {}
    for a in t.alias:
        d = ice_root / "full" / a; x = li[li.alias == a]
        if len(x) < 500 or not (d / "doses.json").exists(): continue
        th = json.load(open(d / "therapy.json")); ds = json.load(open(d / "doses.json"))
        t0 = np.floor(x.tm.min() / 1440) * 1440 + 2 * 1440; t1 = t0 + 12 * 1440; n = int(t1 - t0 + 1); net = np.zeros(n)
        for z in ds:
            s, e, v = ts(z["startDate"]), ts(z["endDate"]), float(z.get("volume") or 0)
            if e < t0 - 400 or s > t1: continue
            if z["deliveryType"] == "bolus":
                i = int(round(s - t0))
                if 0 <= i < n: net[i] += v
            else:
                i0, i1 = int(np.floor(max(s, t0) - t0)), int(np.ceil(min(e, t1) - t0))
                if i1 > i0 and e > s: net[i0:i1] += v / (e - s)
        for b in th["basal"]:
            s, e = ts(b["startDate"]), ts(b["endDate"]); i0, i1 = int(np.floor(max(s, t0) - t0)), int(np.ceil(min(e, t1) - t0))
            if i1 > i0: net[i0:i1] -= float(b["value"]) / 60.0
        y = x[(x.tm >= t0 + 400) & (x.tm <= t1)]
        if len(y) < 300: continue
        r = {k: float(np.sqrt(np.mean((np.interp(y.tm.to_numpy() - t0, np.arange(n), np.convolve(net, kk)[:n]) - y.iob.to_numpy()) ** 2)))
             for k, kk in ks.items()}
        picks[a] = ("fast" if r["fast"] < r["adult"] else "adult", (r["adult"] - r["fast"]) / min(r.values()))
    t["insulin_iob_infer"] = t.alias.map({a: p for a, (p, _) in picks.items()})
    relabel = t.alias.map(lambda a: a in picks and picks[a][1] > margin) & (t.insulin_brand == "humalog")
    t.loc[relabel, "insulin_brand"] = "fiasp"
    t.to_csv(path, index=False)
    return t


def add_isf_yardstick(path: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32",
                      params: Path = Path.home() / ".loop-eval/runs/2026-08-25-distributions/ice/isf_yardstick_params.json"):
    """isf_true from each donor's own glucose response: the ICE ISF yardstick (dist_views/ice/isf_basal_prior.py with the
    distribution cohort's fitted parameters) on the ice_v32 steps (LESSONS 261). Fasting steps (ice screen `clean`,
    |v| < 600 mg/dL/h, no carb entry and no manual bolus in the prior 4 h, not disrupted); hourly blocks: OLS of glucose
    change on insulin absorbed, C = −slope with its relative SE; shrunk toward the basal rule K·fb^b (fb = median absorbed
    U/h while fasting); levelled by the cohort factor. The previous value (the TDD rule, isf_tdd) is kept as isf_true_tdd."""
    import json
    import numpy as np
    prm = json.loads(Path(params).read_text())
    t = pd.read_csv(path)
    out = []
    for a in t.alias:
        f = ice_root / "steps" / f"{a}.parquet"
        if not f.exists():
            out.append(dict(alias=a)); continue
        s = pd.read_parquet(f).sort_values("t1"); tm = (s.t1.astype("int64") / 6e10).to_numpy()

        def recent(ev):
            if not len(ev): return np.zeros(len(tm), bool)
            i = np.searchsorted(ev, tm, side="right") - 1
            return (i >= 0) & (tm - ev[np.maximum(i, 0)] < 240)
        v = s.v.to_numpy(float)
        q = (~recent(tm[(s.carbs_g.fillna(0) > 0).to_numpy()]) & ~recent(tm[(s.bolus_manual_u.fillna(0) > 0).to_numpy()])
             & ~s.disrupted.fillna(False).to_numpy(bool) & np.isfinite(v) & (np.abs(v) < 600) & s.clean.fillna(False).to_numpy(bool))
        dg = v * s.dt.to_numpy(float) / 60.0; du = s.absorbed.to_numpy(float)
        n = len(s) // 12 * 12; m = q[:n].reshape(-1, 12).all(1)
        dv = np.nan_to_num(dg[:n]).reshape(-1, 12).sum(1)[m]; dd = np.nan_to_num(du[:n]).reshape(-1, 12).sum(1)[m]
        fb = float(np.median(du[q] * 12)) if q.sum() > 500 else np.nan
        c = se = np.nan
        if len(dv) >= prm["min_blocks"] and np.std(dd) > 0:
            x = np.column_stack([np.ones_like(dd), dd]); beta = np.linalg.lstsq(x, dv, rcond=None)[0]
            r = dv - x @ beta; s2 = r @ r / (len(dv) - 2); sl = np.sqrt(s2 * np.linalg.inv(x.T @ x)[1, 1])
            c = -beta[1]; se = sl / c if c > 0 else np.nan
        prior = np.log(prm["basal_rule_K"] * fb ** prm["basal_rule_b"]) + prm["slope_offset_log"] if fb > 0 else np.nan
        tau2 = prm["tau_log"] ** 2
        w = tau2 / (tau2 + (se * prm["se_calibration"]) ** 2) if (c > 0 and np.isfinite(se)) else 0.0
        est = np.exp(prior + w * ((np.log(c) if c > 0 else prior) - prior)) * prm["level_factor"] if np.isfinite(prior) else np.nan
        out.append(dict(alias=a, isf_ys=est))
    r = pd.DataFrame(out)
    if "isf_true_tdd" not in t: t["isf_true_tdd"] = t.isf_true
    t = t.drop(columns=[c_ for c_ in ("isf_ys",) if c_ in t]).merge(r, on="alias", how="left")
    t["isf_true"] = t.isf_ys.fillna(t.isf_true_tdd)
    t.to_csv(path, index=False)
    return t


def add_isf_body_fit(path: str, fit_csv: str):
    """isf_true × the donor's body-model sensitivity (LESSONS 262): `fit_csv` from `fit_body --regression` (per donor, the
    slope b of fasting hourly glucose change on the body's own insulin-driven effect, with SE). b is attenuated alike for
    everyone by closed-loop dosing, so only its spread is used: log b shrunk toward the cohort median by its reliability
    (tau² = var(log b) − mean(SE_rel²)), multiplier = shrunk b / median b, applied to the yardstick ISF (kept as isf_true_ys)."""
    import numpy as np
    d = pd.read_csv(fit_csv)
    d = d[d.b_all > 0]
    lb = np.log(d.b_all); rse = d.se_all / d.b_all
    tau2 = max(float(np.var(lb) - np.mean(rse ** 2)), 1e-4); w = tau2 / (tau2 + rse ** 2); med = float(np.median(lb))
    mult = dict(zip(d.alias, np.exp(med + w * (lb - med)) / np.exp(med)))
    t = pd.read_csv(path)
    if "isf_true_ys" not in t: t["isf_true_ys"] = t.isf_true
    t["isf_body_mult"] = t.alias.map(mult)
    t["isf_true"] = t.isf_true_ys * t.isf_body_mult.fillna(1.0)
    t.to_csv(path, index=False)
    return t


def add_missed_cycles(path: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32"):
    """Short missed Loop cycles per donor (LESSONS 377): five-minute slots with no dosing decision (decision_times.csv),
    in gaps of exactly 1 slot (`miss1_day`) and of 2–3 slots (`miss23_day`) where every missed slot has a CGM reading, per
    day of the export. Longer gaps are the
    offline windows (add_disruption_rates). Donors' Loop decides in a median 92% of slots; single misses 6.6 / day."""
    import numpy as np
    t = pd.read_csv(path)
    out = []
    for a in t.alias:
        row = dict(alias=a)
        f = ice_root / "full" / a / "decision_times.csv"
        if f.exists():
            d = pd.read_csv(f)
            s_ = np.unique((pd.to_datetime(d.t, utc=True).astype("int64") // (300 * 10 ** 9)).to_numpy())
            gl = ice_root / "full" / a / "glucose.json"
            if len(s_) > 288 and gl.exists():
                import json as _json
                cg = set((pd.to_datetime([x["date"] if "date" in x else x["startDate"] for x in _json.load(open(gl))], utc=True)
                          .astype("int64") // (300 * 10 ** 9)).tolist())
                days = (s_.max() - s_.min() + 1) / 288.0
                n1 = n23 = 0
                for a0, b0 in zip(s_[:-1], s_[1:]):
                    k = int(b0 - a0 - 1)
                    # only cycles Loop missed with a CGM reading present (the twin's sensor gaps make their own misses)
                    if 1 <= k <= 3 and all((a0 + j) in cg for j in range(1, k + 1)):
                        if k == 1: n1 += 1
                        else: n23 += 1
                row["miss1_day"] = float(n1 / days); row["miss23_day"] = float(n23 / days)
        out.append(row)
    r = pd.DataFrame(out)
    t = t.drop(columns=[c for c in r.columns if c != "alias" and c in t.columns]).merge(r, on="alias", how="left")
    t.to_csv(path, index=False)
    return t


def add_ex_timing(path: str, life_blocks: str, ice_root: Path = Path.home() / ".loop-eval/ice_v32"):
    """Recorded workout habit for donors who record consistently (a HealthKit workout in >= half their 13-day blocks,
    lifestats._recorders; LESSONS 496-497): workouts per week over the export (`ex_week_own`), median duration
    (`ex_dur_own`), the share starting 0-120 min after a carb entry (`ex_am_own`) and the local start hours
    (`ex_hours_own`, space-separated). Other donors stay NaN (their twins use the recorders' pooled timing)."""
    import json as _json
    import numpy as np
    from . import lifestats as L
    from .quiet import local_offset, to_local
    t = pd.read_csv(path)
    rec = L._recorders(pd.read_csv(life_blocks))
    A = L._workouts_all()
    out = []
    for a in t.alias:
        row = dict(alias=a)
        if a in rec:
            off = local_offset(a, ice_root)
            c = _json.load(open(ice_root / "full" / a / "carbs.json"))
            ct = np.sort(L._mins(to_local(pd.to_datetime([x["startDate"] for x in c], utc=True), off))) if c else np.array([])
            s = pd.read_parquet(ice_root / "steps" / f"{a}.parquet", columns=["t1"])
            it = L._mins(to_local(s.t1, off)); t0, t1 = it.min(), it.max()
            w = A[A.alias == a]
            st = L._mins(to_local(w.t, off)); keep = (st >= t0) & (st <= t1)
            st, du = st[keep], w.dur.to_numpy()[keep]
            if len(st):
                k = np.searchsorted(ct, st) - 1
                since = np.where(k >= 0, st - ct[np.clip(k, 0, None)], np.inf)
                row.update(ex_week_own=float(len(st) / ((t1 - t0) / 1440) * 7), ex_dur_own=float(np.median(du)),
                           ex_am_own=float(np.mean(since <= 120)),
                           ex_hours_own=" ".join(f"{(x % 1440) / 60:.2f}" for x in st))
        out.append(row)
    r = pd.DataFrame(out)
    t = t.drop(columns=[c for c in r.columns if c != "alias" and c in t.columns]).merge(r, on="alias", how="left")
    t.to_csv(path, index=False)
    return t
