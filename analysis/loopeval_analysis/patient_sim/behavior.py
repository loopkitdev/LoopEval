"""The person as a second controller: eating, entering, bolusing, correcting, defending against lows,
sleeping, exercising, changing sites.

Two kinds of behavior (evidence/05 §3 lessons 1–3):
  OFFENSE — exogenous, planned per day, blind to glucose: meals and snacks, exercise, sleep.
  DEFENSE — reacts to what the person SEES (CGM readings, trend, Loop's IOB on screen, alarms),
            never to true glucose or to anything the person could not know:
            * proactive snack: projected glucose (CGM + 30·trend − ISF_setting·IOB) below a personal
              onset while awake and looking → a small fast snack. Almost never logged. The trait
              (onset, size) is the most stable one measured in donors (ice L34: alternate-week
              reliability 0.76) and a large share of between-person outcome spread.
            * rescue treatment: CGM below the person's treat threshold → fast carbs, latency, re-check
              at ~15 min and re-treat if not rising (ice meals.py: 34% vs 25%); over-treaters exist
              (73% take > 20 g; Savard 2016).
            * asleep: only an alarm (or rarely the low itself) wakes them (Buckingham 2005: 29% of
              alarms in children; Schultes 2007: 1 in 16 wake unaided).
            * corrections: a manual bolus for a high seen at a glance.
Every trait is drawn per person; rates come from the person's donor template where measured
(carb entries / day, user boluses / day), else literature priors (evidence/04 summary table).
Nothing here is fitted to outcomes; a mismatch with donor statistics means a component is wrong
or missing (memory: no-mystery-terms).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .physiology import Parcel

DAY = 1440.0


@dataclass
class BehaviorTraits:
    # sleep
    bed: float = 23 * 60.0               # local minute
    wake: float = 7 * 60.0
    weekend_shift: float = 60.0          # later wake and meals on weekends [J; no literature, evidence/04 gap]
    # meals (Camerlingo 2021 timing; carbs scaled to the person's diet)
    breakfast_mu: float = 2.078          # lognormal of breakfast hour
    breakfast_sd: float = 0.175
    skip_breakfast: float = 0.1
    snack_rate: float = 1.2              # snacks per day (Camerlingo: ≥1 snack on 71% of days)
    carbs_day: float = 190.0             # grams eaten per day (truth)
    meal_cv: float = 0.35                # within-person per-event size spread (log sd); the person's measured pulse spread when known
    main_weight: float = 1.0             # a main meal's expected size relative to any other eating event: donors' eating
                                         # comes as ~5.6 pulses/day of median 26 g-eq (ice meals), not 3 big meals (LESSONS 16)
    gi_cv: float = 0.4                   # per-meal absorption-speed CV (01 §6.2)
    # announcement and bolusing
    p_entry_meal: float = 0.7
    p_entry_snack: float = 0.3
    count_bias: float = -0.10            # person's mean carb-count error (Brazeau 2013: 63% under)
    count_sd: float = 0.20               # per-meal count error sd
    bolus_timing: str = "before"         # before | immediate | during | after (Datye 2018)
    p_bolus_with_entry: float = 0.85     # ice L41: 0.67–0.87
    calc_up: float = 0.074               # Groat 2017: 7.4% larger, 6.9% smaller
    calc_down: float = 0.069
    absorption_entry_h: float = 3.0      # what they tell Loop
    p_free_bolus: float = 0.0            # P(an un-entered eating event gets a hand-dosed bolus)
    # monitoring and alerts
    glances_per_day: float = 8.0         # Puhr 2020: <3.3 to >8.25 trend-screen views/day
    low_alert: float = 75.0              # Akturk 2021: 74–78.5 mg/dL
    urgent_low: float = 55.0
    high_alert: float = 250.0
    p_respond_alert: float = 0.8         # awake [J]
    p_wake_alarm: float = 0.4            # asleep, per alarm (Buckingham 2005: 29% children / 53% adolescents)
    p_wake_unaided: float = 1.0 / 16     # per low episode (Schultes 2007)
    # defense
    pro_onset: float = 80.0              # projected glucose (mg/dL) below which they act proactively [J]
    pro_grams: float = 12.0              # proactive snack size [J]
    pro_refractory: float = 45.0         # min
    treat_thr: float = 70.0              # CGM level that triggers a rescue [J; alert 74–78]
    treat_grams: float = 25.0            # lnN median; Savard 2016: 32 ± 24 g
    treat_latency: float = 5.0           # min after seeing it
    retreat_wait: float = 15.0
    p_retreat: float = 0.34
    p_log_rescue: float = 0.05           # rescues entered in the app [J; "very under-represented" — Pete]
    # corrections
    corr_thr: float = 200.0              # glance-time CGM above which they may correct [J]
    p_correct: float = 0.3               # per qualifying glance [J; sized from the template's user-bolus rate]
    corr_wait: float = 120.0             # min since their last bolus
    # exercise (T1DEXI is an active cohort; scale down)
    ex_per_week: float = 2.0
    ex_minutes: float = 40.0
    ex_intensity: float = 0.5            # fraction of max effort above rest
    ex_anaerobic: float = 0.1
    ex_hour: float = 17.5
    p_ex_carbs: float = 0.3
    ex_carbs: float = 15.0
    # light daily activity (walking, chores): short bouts, more often after meals (COMPONENTS C6) [J; sized by
    # the quiet-window step statistics, quiet.py]
    walk_per_day: float = 4.0
    walk_min: float = 12.0
    walk_intensity: float = 0.25
    # grazing: small unlogged intake below the ice labeler's 12 g-eq gate (drinks, bites) (COMPONENTS F9) [J]
    graze_per_day: float = 2.0
    graze_g: float = 6.0
    # site changes
    site_days: float = 3.0
    site_hour: float = 19.5


def _num(rates, k):
    v = rates.get(k, np.nan)
    try:
        v = float(v)
    except (TypeError, ValueError):
        return np.nan
    return v if np.isfinite(v) else np.nan


POOLED_ESTIMATE_RATIO = 0.77      # ice pilot median entered grams per pulse g-eq (pulse/entered 1.30, ice L54)


def sample_behavior_traits(rng: np.random.Generator, person) -> BehaviorTraits:
    """Literature priors (evidence/04), replaced by the person's own MEASURED behavior wherever the
    donor template carries it (ice pilot meals tables: pulses, entries, boluses, corrections, rescues)."""
    rates = person.traits.get("template_rates", {})
    lj = lambda mu, sd: float(np.exp(rng.normal(math.log(mu), sd)))
    mpd = _num(rates, "meals_per_day")
    snack_rate = max(0.3, mpd - 3.0) if np.isfinite(mpd) else lj(1.2, 0.4)
    n_eat = 3.0 + snack_rate
    entries = _num(rates, "carb_entries_per_day")
    if np.isfinite(entries):
        p_meal = float(np.clip(entries / 3.0, 0.0, 1.0))
        p_snack = float(np.clip((entries - 3.0 * p_meal) / max(snack_rate, 0.1), 0.0, 1.0))
    else:
        p_meal = float(rng.uniform(0.2, 0.9)); p_snack = p_meal * 0.4
    er = _num(rates, "estimate_ratio")
    count_bias = (math.log(er / POOLED_ESTIMATE_RATIO) - 0.10) if np.isfinite(er) and er > 0 else float(rng.normal(-0.10, 0.097))
    lead = _num(rates, "bolus_lead_min")
    if np.isfinite(lead):
        timing = "before" if lead < -5 else "immediate" if lead < 1 else "during" if lead < 15 else "after"
    else:
        timing = str(rng.choice(["before", "immediate", "during", "after"], p=[0.21, 0.44, 0.10, 0.25]))
    pb = _num(rates, "p_bolus_ann")
    corr_rate = _num(rates, "true_corrections_per_day")
    if not np.isfinite(corr_rate): corr_rate = _num(rates, "corrections_per_day")
    free = _num(rates, "free_boluses_per_day")
    unentered = max(n_eat - (entries if np.isfinite(entries) else n_eat * p_meal), 0.5)
    p_free = float(np.clip(free / unentered, 0.0, 1.0)) if np.isfinite(free) else 0.0
    ub = _num(rates, "user_boluses_per_day")
    if not np.isfinite(corr_rate) and np.isfinite(ub):
        corr_rate = max(0.0, ub - entries) if np.isfinite(entries) else ub / 2
    cbg = _num(rates, "corr_bg_med")
    rsz = _num(rates, "rescue_size_med")
    rbg = _num(rates, "rescue_bg_med")
    t = BehaviorTraits(
        bed=float(rng.normal(23 * 60, 50)), wake=float(rng.normal(7 * 60, 50)),
        snack_rate=snack_rate, carbs_day=person.truth["carbs_g_day"],
        p_entry_meal=p_meal, p_entry_snack=p_snack,
        count_bias=count_bias, count_sd=lj(0.2, 0.3),
        bolus_timing=timing,
        p_bolus_with_entry=float(np.clip(pb, 0.05, 1.0)) if np.isfinite(pb) else 0.85,
        p_free_bolus=p_free,
        glances_per_day=lj(6.0, 0.6),
        low_alert=float(rng.normal(76, 8)), high_alert=float(rng.normal(240, 25)),
        p_wake_alarm=float(np.clip(rng.normal(0.45, 0.2), 0.05, 0.95)),
        pro_onset=float(rng.normal(80, 20)), pro_grams=lj(12, 0.4),
        treat_thr=float(np.clip(rbg - 5, 55, 85)) if np.isfinite(rbg) else float(rng.normal(70, 6)),
        treat_grams=float(np.clip(rsz, 8, 60)) if np.isfinite(rsz) else lj(25, 0.5),
        treat_latency=lj(5, 0.6), p_retreat=float(np.clip(rng.normal(0.34, 0.1), 0, 1)),
        corr_thr=float(np.clip(cbg - 20, 130, 300)) if np.isfinite(cbg) else float(rng.normal(200, 30)),
        # a qualifying glance corrects with this chance; sized so the person's measured rate is reachable
        # [J: ~4 qualifying glances a day for a person who runs high; refined by twin validation]
        p_correct=float(np.clip(corr_rate / 4.0, 0.01, 0.9)) if np.isfinite(corr_rate) else float(rng.uniform(0.05, 0.5)),
        ex_per_week=float(rng.choice([0, 0.5, 1, 2, 3, 4, 5], p=[0.2, 0.1, 0.15, 0.2, 0.15, 0.1, 0.1])),
        ex_minutes=lj(40, 0.4), ex_intensity=float(np.clip(rng.normal(0.5, 0.12), 0.2, 0.85)),
        ex_anaerobic=float(np.clip(rng.beta(1.2, 6), 0, 1)), ex_hour=float(rng.choice([7.0, 12.5, 17.5, 19.0])),
        site_days=float(np.clip(rng.normal(3.0, 0.4), 2.0, 4.0)),
        walk_per_day=lj(4.0, 0.6), walk_min=lj(12.0, 0.4), walk_intensity=float(np.clip(rng.normal(0.25, 0.06), 0.1, 0.45)),
        graze_per_day=lj(2.0, 0.7), graze_g=lj(6.0, 0.4),
    )
    lsd = _num(rates, "meal_size_logsd")
    if np.isfinite(lsd): t.meal_cv = float(np.clip(lsd, 0.2, 0.9))
    mh = rates.get("meal_hours")
    if isinstance(mh, str):
        import json as _json
        h = np.array(_json.loads(mh), dtype=float)
        if h.sum() > 0: t.snack_hours = h / h.sum()
    return t


@dataclass
class Meal:
    t: float
    grams: float
    kind: str                 # "meal" | "snack"
    speed: float              # kabs multiplier
    entered: Optional[float]  # grams entered in Loop (None = not announced)
    entry_t: float
    bolus: Optional[float]    # ratio of the calculator recommendation (None = no bolus)
    fat: float = 0.0          # g
    protein: float = 0.0      # g


class Behavior:
    """Call `minute(m, reading, state)` every minute. It returns a list of actions:
        ("eat", Parcel)                       — into the body
        ("carb", minute, grams, absorption_s) — a carb entry in Loop
        ("bolus", minute, ratio)              — a manual bolus as ratio × Loop's recommendation
        ("exercise", minute, minutes, intensity, anaerobic)
        ("site_change", minute)
    """

    def __init__(self, traits: BehaviorTraits, person, rng: np.random.Generator):
        self.t = traits
        self.p = person
        self.rng = rng
        self.readings: list[tuple[float, float]] = []
        self.planned: list = []                 # (minute, action) sorted
        self.planned_day = -1
        self.last_pro = -1e9
        self.last_treat = -1e9
        self.treat_check: Optional[float] = None
        self.last_bolus = -1e9
        self.last_alarm = -1e9
        self.in_low = False
        self.low_seen = False
        self.next_site = (rng.uniform(0, traits.site_days) * DAY // DAY) * DAY + traits.site_hour * 60
        self.log = []                           # ground truth of every behavior event

    # ------------------------------------------------------------------ helpers
    def _f_glucose(self) -> float:
        """Bioavailability of fast glucose (tabs, juice): the person's calibrated per-gram meal value
        × 1.25 — pure glucose vs mixed carbohydrate [J] — never a fixed 1.0, which on a small glucose
        space made 1 g of rescue raise 13 mg/dL against 3–4 in Brodows 1984 (LESSONS 18)."""
        return min(1.0, self.p.body.f * 1.25)

    def asleep(self, m: float) -> bool:
        mm = m % DAY
        wknd = int(m // DAY) % 7 in (5, 6)
        wake = self.t.wake + (self.t.weekend_shift if wknd else 0)
        bed = self.t.bed + (self.t.weekend_shift / 2 if wknd else 0)
        bed_mm = bed % DAY
        if bed_mm > wake:                        # bed before midnight
            return mm >= bed_mm or mm < wake
        return bed_mm <= mm < wake

    def trend(self) -> float:
        """mg/dL/min over the last ~15 min of readings the person can see."""
        r = self.readings[-4:]
        if len(r) < 2: return 0.0
        return (r[-1][1] - r[0][1]) / max(r[-1][0] - r[0][0], 1.0)

    # ------------------------------------------------------------------ the day's plan (offense)
    def plan_day(self, day: int, carb_scale: float = 1.0):
        t, r = self.t, self.rng
        base = day * DAY
        wknd = day % 7 in (5, 6)
        shift = t.weekend_shift if wknd else 0.0
        slots = []
        b = float(np.exp(r.normal(t.breakfast_mu, t.breakfast_sd))) * 60 + shift
        main_w = t.main_weight
        if r.random() > t.skip_breakfast: slots.append(("meal", b, 0.22 / 0.286 * main_w))
        lunch = b + max(120.0, r.gumbel(282.9, 80.0) * 0.9)
        dinner = lunch + max(150.0, r.gumbel(374.9, 85.0) * 0.9)
        slots += [("meal", lunch, 0.30 / 0.286 * main_w), ("meal", dinner, 0.34 / 0.286 * main_w)]
        n_snack = r.poisson(t.snack_rate)
        sh = getattr(t, "snack_hours", None)
        for _ in range(n_snack):
            if sh is not None:      # the person's own eating clock (ice pulses by hour)
                st = (float(r.choice(24, p=sh)) + r.random()) * 60
            else:
                st = float(r.uniform(t.wake + 60, t.bed + 30))
            slots.append(("snack", st + shift, 1.0))
        total_share = sum(s[2] for s in slots)
        for kind, mt, share in slots:
            grams = t.carbs_day * carb_scale * share / max(total_share, 1e-9) * float(np.exp(r.normal(0, t.meal_cv) - t.meal_cv ** 2 / 2))
            grams = max(3.0, grams)
            speed = float(np.exp(r.normal(0, t.gi_cv)))
            p_e = t.p_entry_meal if kind == "meal" else t.p_entry_snack
            entered = None; bolus = None; et = base + mt
            if r.random() < p_e:
                err = t.count_bias + r.normal(0, t.count_sd) - (0.1 * math.log(max(grams, 5) / 45.0) if t.count_sd > 0 else 0.0)
                entered = max(1.0, round(grams * math.exp(err)))
                off = {"before": r.uniform(-20, -5), "immediate": r.uniform(-3, 0),
                       "during": r.uniform(3, 15), "after": r.uniform(15, 45)}[t.bolus_timing]
                et = base + mt + off
                if r.random() < t.p_bolus_with_entry:
                    u = r.random()
                    bolus = 1.0 if u > t.calc_up + t.calc_down else (float(r.uniform(1.1, 1.5)) if u < t.calc_up else float(r.uniform(0.5, 0.9)))
            # composition [J]: T1D adults ~40% energy carbohydrate, 40% fat, 18% protein (Snell-Bergeon 2009,
            # unverified) → per carb gram ~0.44 g fat, 0.45 g protein for meals; snacks carry less
            fat_r, pro_r = (0.44, 0.45) if kind == "meal" else (0.2, 0.2)
            fat = grams * fat_r * float(np.exp(r.normal(0, 0.5) - 0.125))
            protein = grams * pro_r * float(np.exp(r.normal(0, 0.5) - 0.125))
            meal = Meal(base + mt, grams, kind, speed, entered, et, bolus, fat=fat, protein=protein)
            self.planned.append((base + mt, ("eat_meal", meal)))
            if entered is not None:
                self.planned.append((et, ("enter_meal", meal)))
            elif r.random() < t.p_free_bolus:
                # food dosed by hand: their own estimate of the grams over their own CR setting
                est = grams * math.exp(t.count_bias + r.normal(0, t.count_sd))
                units = round(est / self.p.settings["cr"] * 2) / 2
                off = {"before": r.uniform(-20, -5), "immediate": r.uniform(-3, 0),
                       "during": r.uniform(3, 15), "after": r.uniform(15, 45)}[t.bolus_timing]
                if units >= 0.5:
                    self.planned.append((base + mt + off, ("free_bolus", units)))
        # light activity bouts: daytime, half of them within 2 h after an eating event
        eat_times = sorted(base + st for _, st, _ in slots)
        for _ in range(r.poisson(t.walk_per_day)):
            if eat_times and r.random() < 0.5:
                st = float(r.choice(eat_times)) + float(r.uniform(10, 120))
            else:
                st = base + float(r.uniform(t.wake + 30, t.bed - 30)) + shift
            dur = max(3.0, float(np.exp(r.normal(math.log(t.walk_min), 0.5))))
            self.planned.append((st, ("walk", st, dur, t.walk_intensity * float(np.exp(r.normal(0, 0.2))), 0.0)))
        # grazing: never entered, never bolused
        for _ in range(r.poisson(t.graze_per_day)):
            st = base + float(r.uniform(t.wake + 30, t.bed)) + shift
            self.planned.append((st, ("graze", max(1.0, float(np.exp(r.normal(math.log(t.graze_g), 0.4)))))))
        # exercise
        if r.random() < t.ex_per_week / 7.0:
            st = base + (t.ex_hour * 60 + r.normal(0, 45)) + shift
            dur = max(10.0, float(np.exp(r.normal(math.log(t.ex_minutes), 0.3))))
            self.planned.append((st, ("exercise", st, dur, t.ex_intensity, t.ex_anaerobic)))
            if r.random() < t.p_ex_carbs:
                self.planned.append((st - 10, ("ex_carbs", t.ex_carbs)))
        self.planned.sort(key=lambda x: x[0])

    # ------------------------------------------------------------------ per minute
    def minute(self, m: float, reading, state: dict, carb_scale: float = 1.0) -> list:
        acts = []
        t, r = self.t, self.rng
        day = int(m // DAY)
        if day > self.planned_day:
            self.plan_day(day, carb_scale); self.planned_day = day
        while self.planned and self.planned[0][0] <= m:
            _, (kind, *rest) = self.planned.pop(0)
            if kind == "eat_meal":
                meal = rest[0]
                bp = self.p.body
                # fat slows gastric emptying (Bell 2020, Paterson 2017): kempt × 1/(1 + fat/60)
                phi_fat = 1.0 / (1.0 + meal.fat / 60.0)
                acts.append(("eat", Parcel(m, meal.grams, kempt=bp.kempt * meal.speed * phi_fat, kabs=bp.kabs * meal.speed,
                                           f=bp.f, label=meal.kind)))
                # protein → late glucose appearance: 0.1 g glucose per g protein, delayed ~90 min, peak 3–5 h
                # (Smart 2013; Paterson 2017; evidence/01 §6.3); it is glucose, so fast-glucose bioavailability
                if meal.protein > 0:
                    acts.append(("eat", Parcel(m, 0.1 * meal.protein, kempt=1 / 60.0, kabs=1 / 60.0, delay=90.0,
                                               f=self._f_glucose(), hypo_sensitive=False, label="protein")))
                if meal.fat > 0:
                    acts.append(("fat", m, meal.fat))
                self.log.append((m, meal.kind, meal.grams, meal.entered))
            elif kind == "enter_meal":
                meal = rest[0]
                acts.append(("carb", m, float(meal.entered), t.absorption_entry_h * 3600))
                if meal.bolus is not None:
                    acts.append(("bolus", m, meal.bolus)); self.last_bolus = m
                self.log.append((m, "entry", meal.entered, meal.bolus))
            elif kind == "walk":
                acts.append(("exercise",) + tuple(rest)); self.log.append((m, "walk", rest[1], rest[2]))
            elif kind == "graze":
                bp = self.p.body
                acts.append(("eat", Parcel(m, rest[0], kempt=bp.kempt * 1.5, kabs=bp.kabs * 1.5, f=self._f_glucose(), label="graze")))
                self.log.append((m, "graze", rest[0], None))
            elif kind == "free_bolus":
                acts.append(("bolus_units", m, rest[0])); self.last_bolus = m
                self.log.append((m, "free_bolus", rest[0], None))
            elif kind == "exercise":
                acts.append(("exercise",) + tuple(rest)); self.log.append((m, "exercise", rest[1], rest[2]))
            elif kind == "ex_carbs":
                acts.append(("eat", Parcel(m, rest[0], kempt=0.06, kabs=0.06, f=self._f_glucose(), label="ex_carbs")))
                self.log.append((m, "ex_carbs", rest[0], None))
        if m >= self.next_site:
            acts.append(("site_change", m)); self.log.append((m, "site_change", 0, None))
            self.next_site += t.site_days * DAY
        if reading:                                  # a new reading (None = withheld, False = no report)
            self.readings.append((m, reading))
            if len(self.readings) > 12: self.readings.pop(0)
        acts += self._defense_and_corrections(m, state)
        return acts

    def _defense_and_corrections(self, m: float, state: dict) -> list:
        t, r = self.t, self.rng
        if not self.readings: return []
        cgm = self.readings[-1][1]
        if m - self.readings[-1][0] > 15: return []          # nothing current to see
        asleep = self.asleep(m)
        acts = []
        # what draws the person's attention this minute
        alarm = False
        if cgm <= t.urgent_low or (cgm <= t.low_alert and m - self.last_alarm >= 30):
            alarm = m - self.last_alarm >= 15
        if alarm: self.last_alarm = m
        if asleep:
            looking = alarm and r.random() < t.p_wake_alarm
            if not looking and cgm < 60 and not self.low_seen and r.random() < t.p_wake_unaided / 30:
                looking = True
        else:
            looking = r.random() < t.glances_per_day / (16 * 60) or (alarm and r.random() < t.p_respond_alert)
        if not looking and self.treat_check is None:
            return acts
        # rescue re-check
        if self.treat_check is not None and m >= self.treat_check:
            self.treat_check = None
            if cgm < t.treat_thr + 10 and self.trend() <= 0.2 and r.random() < t.p_retreat / 0.5 * 0.5:
                g = max(5.0, t.treat_grams * float(np.exp(r.normal(0, 0.3))))
                acts.append(("eat", Parcel(m + t.treat_latency, g, kempt=0.08, kabs=0.08, f=self._f_glucose(), label="rescue")))
                self.log.append((m, "retreat", g, None)); self.treat_check = m + t.retreat_wait
            return acts
        if not looking: return acts
        self.low_seen = cgm < t.treat_thr
        # rescue
        if cgm < t.treat_thr and m - self.last_treat > 20:
            g = max(5.0, t.treat_grams * float(np.exp(r.normal(0, 0.3))))
            acts.append(("eat", Parcel(m + t.treat_latency, g, kempt=0.08, kabs=0.08, f=self._f_glucose(), label="rescue")))
            if r.random() < t.p_log_rescue: acts.append(("carb", m, round(g), 1800.0))
            self.last_treat = m; self.treat_check = m + t.treat_latency + t.retreat_wait
            self.log.append((m, "rescue", g, cgm))
            return acts
        # proactive snack: projected glucose from what Loop shows (IOB) and the trend
        if not asleep and m - self.last_pro > t.pro_refractory and m - self.last_treat > 30:
            iob = float(state.get("iob", 0.0) or 0.0)
            proj = cgm + 30 * self.trend() - self.p.settings["isf"] * max(iob, 0.0)
            # the defense state ice measured (L34, L69): near the low band and not rising — a person at
            # 220 with lots of IOB does not snack, however low the projection (LESSONS 11)
            if proj < t.pro_onset and cgm < t.pro_onset + 50 and self.trend() <= 0.0:
                g = max(3.0, t.pro_grams * float(np.exp(r.normal(0, 0.3))))
                acts.append(("eat", Parcel(m + 2, g, kempt=0.06, kabs=0.06, f=self._f_glucose(), label="proactive")))
                self.last_pro = m
                self.log.append((m, "proactive", g, proj))
                return acts
        # correction of a high seen at a glance
        if not asleep and cgm > t.corr_thr and self.trend() > -0.5 and m - self.last_bolus > t.corr_wait \
                and r.random() < t.p_correct:
            acts.append(("bolus", m, 1.0)); self.last_bolus = m
            self.log.append((m, "correction", 0, cgm))
        return acts
