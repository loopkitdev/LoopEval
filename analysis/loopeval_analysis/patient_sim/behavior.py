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
    meal_cv: float = 0.35                # within-person per-meal CV [J; evidence/04 modelling choice]
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
    # site changes
    site_days: float = 3.0
    site_hour: float = 19.5


def sample_behavior_traits(rng: np.random.Generator, person) -> BehaviorTraits:
    rates = person.traits.get("template_rates", {})
    meals_day = 3.0 + 1.2
    entries = rates.get("carb_entries_per_day", np.nan)
    p_entry = float(np.clip(entries / meals_day, 0.0, 1.0)) if np.isfinite(entries) else float(rng.uniform(0.2, 0.9))
    ub = rates.get("user_boluses_per_day", np.nan)
    lj = lambda mu, sd: float(np.exp(rng.normal(math.log(mu), sd)))
    t = BehaviorTraits(
        bed=float(rng.normal(23 * 60, 50)), wake=float(rng.normal(7 * 60, 50)),
        snack_rate=lj(1.2, 0.4), carbs_day=person.truth["carbs_g_day"],
        p_entry_meal=p_entry, p_entry_snack=p_entry * 0.4,
        count_bias=float(rng.normal(-0.10, 0.097)), count_sd=lj(0.2, 0.3),
        bolus_timing=str(rng.choice(["before", "immediate", "during", "after"], p=[0.21, 0.44, 0.10, 0.25])),
        glances_per_day=lj(6.0, 0.6),
        low_alert=float(rng.normal(76, 8)), high_alert=float(rng.normal(240, 25)),
        p_wake_alarm=float(np.clip(rng.normal(0.45, 0.2), 0.05, 0.95)),
        pro_onset=float(rng.normal(80, 20)), pro_grams=lj(12, 0.4),
        treat_thr=float(rng.normal(70, 6)), treat_grams=lj(25, 0.5),
        treat_latency=lj(5, 0.6), p_retreat=float(np.clip(rng.normal(0.34, 0.1), 0, 1)),
        corr_thr=float(rng.normal(200, 30)),
        p_correct=float(np.clip(ub / 6.0, 0.02, 0.9)) if np.isfinite(ub) else float(rng.uniform(0.05, 0.5)),
        ex_per_week=float(rng.choice([0, 0.5, 1, 2, 3, 4, 5], p=[0.2, 0.1, 0.15, 0.2, 0.15, 0.1, 0.1])),
        ex_minutes=lj(40, 0.4), ex_intensity=float(np.clip(rng.normal(0.5, 0.12), 0.2, 0.85)),
        ex_anaerobic=float(np.clip(rng.beta(1.2, 6), 0, 1)), ex_hour=float(rng.choice([7.0, 12.5, 17.5, 19.0])),
        site_days=float(np.clip(rng.normal(3.0, 0.4), 2.0, 4.0)),
    )
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
        if r.random() > t.skip_breakfast: slots.append(("meal", b, 0.22))
        lunch = b + max(120.0, r.gumbel(282.9, 80.0) * 0.9)
        dinner = lunch + max(150.0, r.gumbel(374.9, 85.0) * 0.9)
        slots += [("meal", lunch, 0.30), ("meal", dinner, 0.34)]
        n_snack = r.poisson(t.snack_rate)
        for _ in range(n_snack):
            slots.append(("snack", float(r.uniform(t.wake + 60, t.bed + 30)) + shift, 0.14 / max(t.snack_rate, 0.5)))
        total_share = sum(s[2] for s in slots)
        for kind, mt, share in slots:
            grams = t.carbs_day * carb_scale * share / max(total_share, 1e-9) * float(np.exp(r.normal(0, t.meal_cv) - t.meal_cv ** 2 / 2))
            grams = max(3.0, grams)
            speed = float(np.exp(r.normal(0, t.gi_cv)))
            p_e = t.p_entry_meal if kind == "meal" else t.p_entry_snack
            entered = None; bolus = None; et = base + mt
            if r.random() < p_e:
                err = t.count_bias + r.normal(0, t.count_sd) - 0.1 * math.log(max(grams, 5) / 45.0)
                entered = max(1.0, round(grams * math.exp(err)))
                off = {"before": r.uniform(-20, -5), "immediate": r.uniform(-3, 0),
                       "during": r.uniform(3, 15), "after": r.uniform(15, 45)}[t.bolus_timing]
                et = base + mt + off
                if r.random() < t.p_bolus_with_entry:
                    u = r.random()
                    bolus = 1.0 if u > t.calc_up + t.calc_down else (float(r.uniform(1.1, 1.5)) if u < t.calc_up else float(r.uniform(0.5, 0.9)))
            meal = Meal(base + mt, grams, kind, speed, entered, et, bolus)
            self.planned.append((base + mt, ("eat_meal", meal)))
            if entered is not None:
                self.planned.append((et, ("enter_meal", meal)))
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
                acts.append(("eat", Parcel(m, meal.grams, kempt=0.025, kabs=0.05 * meal.speed, label=meal.kind)))
                self.log.append((m, meal.kind, meal.grams, meal.entered))
            elif kind == "enter_meal":
                meal = rest[0]
                acts.append(("carb", m, float(meal.entered), t.absorption_entry_h * 3600))
                if meal.bolus is not None:
                    acts.append(("bolus", m, meal.bolus)); self.last_bolus = m
                self.log.append((m, "entry", meal.entered, meal.bolus))
            elif kind == "exercise":
                acts.append(("exercise",) + tuple(rest)); self.log.append((m, "exercise", rest[1], rest[2]))
            elif kind == "ex_carbs":
                acts.append(("eat", Parcel(m, rest[0], kempt=0.06, kabs=0.06, label="ex_carbs")))
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
                acts.append(("eat", Parcel(m + t.treat_latency, g, kempt=0.08, kabs=0.08, f=1.0, label="rescue")))
                self.log.append((m, "retreat", g, None)); self.treat_check = m + t.retreat_wait
            return acts
        if not looking: return acts
        self.low_seen = cgm < t.treat_thr
        # rescue
        if cgm < t.treat_thr and m - self.last_treat > 20:
            g = max(5.0, t.treat_grams * float(np.exp(r.normal(0, 0.3))))
            acts.append(("eat", Parcel(m + t.treat_latency, g, kempt=0.08, kabs=0.08, f=1.0, label="rescue")))
            if r.random() < t.p_log_rescue: acts.append(("carb", m, round(g), 1800.0))
            self.last_treat = m; self.treat_check = m + t.treat_latency + t.retreat_wait
            self.log.append((m, "rescue", g, cgm))
            return acts
        # proactive snack: projected glucose from what Loop shows (IOB) and the trend
        if not asleep and m - self.last_pro > t.pro_refractory and m - self.last_treat > 30:
            iob = float(state.get("iob", 0.0) or 0.0)
            proj = cgm + 30 * self.trend() - self.p.settings["isf"] * max(iob, 0.0)
            if proj < t.pro_onset and self.trend() < 0.5:
                g = max(3.0, t.pro_grams * float(np.exp(r.normal(0, 0.3))))
                acts.append(("eat", Parcel(m + 2, g, kempt=0.06, kabs=0.06, f=1.0, label="proactive")))
                self.last_pro = m
                self.log.append((m, "proactive", g, proj))
                return acts
        # correction of a high seen at a glance
        if not asleep and cgm > t.corr_thr and self.trend() > -0.5 and m - self.last_bolus > t.corr_wait \
                and r.random() < t.p_correct:
            acts.append(("bolus", m, 1.0)); self.last_bolus = m
            self.log.append((m, "correction", 0, cgm))
        return acts
