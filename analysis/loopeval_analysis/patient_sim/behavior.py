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
    meal_slow_frac: float = 0.0          # share of a meal emptied in the slow phase (calibrated vs donor meal response)
    meal_slow_k: float = 0.008           # /min, Dalla Man kmin
    meal_fast_frac: float = 0.2          # share of a meal's carbohydrate in its fast-emptying liquid phase [J; 0.2 vs 0.35 by cohort, LESSONS 44]
    main_weight: float = 1.9             # a main meal's expected size relative to a snack: Camerlingo 2021 (B 41 / L 49 / D 53 vs
                                         # snack 25 g). Entered grams per entry then match donors (32.3 vs 32.6; LESSONS 47);
                                         # lesson 16's 1.0 compensated for fixed-rate emptying with three meals carrying all carbs
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
    # Temporary Overrides, planned with the events they serve (LESSONS 40; templates.add_override_rates)
    ov_less_day: float = 0.0             # less-insulin overrides/day (activity, low prevention)
    ov_less_f: float = 0.6
    ov_less_lo: float = float("nan")
    ov_less_hi: float = float("nan")
    ov_less_h: float = 1.4
    ov_more_day: float = 0.0             # more-insulin overrides/day, started in reaction to a rising high (plant-sent)
    ov_more_f: float = 1.33
    ov_more_lo: float = float("nan")
    ov_more_hi: float = float("nan")
    ov_more_h: float = 1.0
    p_more: float = 0.0                  # per qualifying awake minute (CGM > 180 and rising)
    ov_tgt_day: float = 0.0              # target-only overrides/day (pre-meal when the target is lowered)
    ov_tgt_lo: float = float("nan")
    ov_tgt_hi: float = float("nan")
    ov_tgt_h: float = 1.0
    intake_cv: float = 0.22              # day-to-day CV of food eaten (Tarasuk & Beaton 1992; ~20% for carbohydrate)
    intake_rho: float = 0.29             # next-day intake correlation (Levitsky 2017)
    intake_comp: float = 1.0             # 24-h regulation of the day total across its eating events (1 = full) [J]
    act_day_var: bool = True             # day-level gamma(3) on the activity rate (ablation switch)
    p_topup: float = 0.0                 # P(a second bolus 20–60 min after a meal bolus, no new entry) — raw donor top-ups
    p_split: float = 0.0                 # P(a meal bolus is split: 60% at the entry, the rest 10–30 min later) [J split]
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
    p_correct: float = 0.002             # per awake minute above the correction level (exposure-sized from the donor)
    corr_wait: float = 120.0             # min since their last bolus
    # exercise (T1DEXI is an active cohort; scale down)
    ex_per_week: float = 2.0
    ex_minutes: float = 40.0
    ex_intensity: float = 0.5            # fraction of max effort above rest
    ex_anaerobic: float = 0.1
    ex_hour: float = 17.5
    p_ex_carbs: float = 0.3
    ex_carbs: float = 15.0
    # everyday activity (walks, errands, chores) as episodes, plus a waking background (evidence/10 §7; LESSONS 34)
    act_rate: float = 2.0                # episodes/day (person; T1DEXI ~0.8 logged ≥15-min sessions + shorter unlogged)
    act_dur: float = 18.0                # min, lnN median; σ_log 0.75, truncated 5–150
    metmax: float = 9.0                  # T1D adults VO2max 32 ± 9 mL/kg/min → METmax ≈ 9 (Muñoz-Hernandez 2025)
    act_bg: float = 0.06                 # waking background intensity [J; NHANES light-activity minutes]
    act_gain: float = 1.0                # responsiveness of glucose to activity (lnN σ 0.5; Jaloli)
    act_after_meal: float = 0.4          # share of episodes starting 10–120 min after eating [J; not found]
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
    # rates from the RAW record where present (templates.add_raw_rates; LESSONS 36): the ice-labeled entry count
    # keeps only entries attached to a labeled pulse (2.07 vs 2.97/day)
    entries = _num(rates, "entries_raw")
    if not np.isfinite(entries): entries = _num(rates, "carb_entries_per_day")
    if np.isfinite(entries):
        p_meal = float(np.clip(entries / 3.0, 0.0, 1.0))
        p_snack = float(np.clip((entries - 3.0 * p_meal) / max(snack_rate, 0.1), 0.0, 1.0))
    else:
        p_meal = float(rng.uniform(0.2, 0.9)); p_snack = p_meal * 0.4
    er = _num(rates, "estimate_ratio")
    # person-level carb-count bias from the literature (Brazeau 2013: 63% under-estimated, ±9.7% per person). The
    # donor's labeled entered/pulse ratio is NOT a count bias: the labeler alone spreads per-person medians by ~0.46
    # log-sd (sim: 0.67 labeled vs 0.49 true), which is all of the donors' 0.45 (LESSONS 35)
    count_bias = float(rng.normal(-0.10, 0.10))
    lead = _num(rates, "bolus_lead_min")
    if np.isfinite(lead):
        timing = "before" if lead < -5 else "immediate" if lead < 1 else "during" if lead < 15 else "after"
    else:
        timing = str(rng.choice(["before", "immediate", "during", "after"], p=[0.21, 0.44, 0.10, 0.25]))
    pb = _num(rates, "p_bolus_ann")
    be_raw, lone_raw, top_raw = _num(rates, "bolus_entry_raw"), _num(rates, "lone_raw"), _num(rates, "topups_raw")
    p_split = 0.0
    if np.isfinite(be_raw) and np.isfinite(entries) and entries > 0:
        k = be_raw / entries                      # boluses per entry (donors: 1.09 median, 1.22 mean)
        pb = float(np.clip(k, 0.05, 1.0))
        p_split = float(np.clip(k - 1.0, 0.0, 1.0))   # the excess: a second bolus for the same meal (LESSONS 47)
    corr_rate = _num(rates, "true_corrections_per_day")
    if not np.isfinite(corr_rate): corr_rate = _num(rates, "corrections_per_day")
    free = _num(rates, "free_boluses_per_day")
    if np.isfinite(lone_raw):
        # the raw lone-bolus rate, split into hand-dosed food and corrections by the donor's own labeled split
        fr = free / (free + corr_rate) if np.isfinite(free) and np.isfinite(corr_rate) and free + corr_rate > 0 else 0.5
        free, corr_rate = lone_raw * fr, lone_raw * (1 - fr)
    # planned top-ups execute only when the meal is running high (~38% of plans, measured on simulated people), so the
    # plan rate is the donor's realized rate / 0.38 (LESSONS 42)
    p_topup = float(np.clip(top_raw / be_raw / 0.38, 0.0, 1.0)) if np.isfinite(top_raw) and np.isfinite(be_raw) and be_raw > 0 else 0.0
    unentered = max(n_eat - (entries if np.isfinite(entries) else n_eat * p_meal), 0.5)
    p_free = float(np.clip(free / unentered, 0.0, 1.0)) if np.isfinite(free) else 0.0
    ub = _num(rates, "user_boluses_per_day")
    if not np.isfinite(corr_rate) and np.isfinite(ub):
        corr_rate = max(0.0, ub - entries) if np.isfinite(entries) else ub / 2
    cbg = _num(rates, "corr_bg_med")
    corr_exp = _num(rates, "corr_exposure")
    tir_d, t70_d = _num(rates, "tir"), _num(rates, "t70")
    hi_frac = max((100 - tir_d - t70_d) / 100, 0.05) if np.isfinite(tir_d) and np.isfinite(t70_d) else 0.25
    rsz = _num(rates, "rescue_size_med")
    rbg = _num(rates, "rescue_bg_med")
    t = BehaviorTraits(
        bed=float(rng.normal(23 * 60, 50)), wake=float(rng.normal(7 * 60, 50)),
        snack_rate=snack_rate, carbs_day=person.truth["carbs_g_day"],
        p_entry_meal=p_meal, p_entry_snack=p_snack,
        count_bias=count_bias, count_sd=lj(0.2, 0.3),
        bolus_timing=timing,
        p_bolus_with_entry=float(np.clip(pb, 0.05, 1.0)) if np.isfinite(pb) else 0.85,
        p_free_bolus=p_free, p_topup=p_topup, p_split=p_split,
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
        # hazard per qualifying awake minute: the donor's rate over the donor's own waking exposure above THEIR
        # correction level (templates.add_corr_exposure), divided by the share of those minutes that pass the
        # not-falling / no-recent-bolus conditions (0.46, measured on simulated people; LESSONS 42)
        # / 0.64: a share of intended corrections deliver 0 U (Loop's recommendation already covered by IOB); sized
        # so the realized lone-bolus rate reaches the donor's (LESSONS 47)
        p_correct=float(np.clip(corr_rate / (16 * 60 * (corr_exp if np.isfinite(corr_exp) else hi_frac) * 0.46 * 0.64), 0.0, 0.05))
                  if np.isfinite(corr_rate) else float(rng.uniform(0.0005, 0.005)),
        ex_per_week=float(rng.choice([0, 0.5, 1, 2, 3, 4, 5], p=[0.2, 0.1, 0.15, 0.2, 0.15, 0.1, 0.1])),
        ex_minutes=lj(40, 0.4), ex_intensity=float(np.clip(rng.normal(0.5, 0.12), 0.2, 0.85)),
        ex_anaerobic=float(np.clip(rng.beta(1.2, 6), 0, 1)), ex_hour=float(rng.choice([7.0, 12.5, 17.5, 19.0])),
        site_days=float(np.clip(rng.normal(3.0, 0.4), 2.0, 4.0)),
        act_rate=lj(2.0, 0.55), metmax=float(np.clip(lj(9.0, 0.25) * (1 - 0.0075 * max(0.0, person.age - 30)), 4.0, 16.0)),
        act_bg=lj(0.06, 0.4), act_gain=lj(1.0, 0.5),
        graze_per_day=lj(2.0, 0.7), graze_g=lj(6.0, 0.4),
    )
    for k in ("ov_less_day", "ov_less_f", "ov_less_lo", "ov_less_hi", "ov_less_h", "ov_tgt_day", "ov_tgt_lo", "ov_tgt_hi", "ov_tgt_h",
              "ov_more_day", "ov_more_f", "ov_more_lo", "ov_more_hi", "ov_more_h"):
        v = _num(rates, k)
        if np.isfinite(v) or k.endswith(("_lo", "_hi")):
            setattr(t, k, v if np.isfinite(v) else (0.0 if k.endswith("_day") else getattr(t, k)))
    # more-insulin overrides react to a rising high (donors: started at ~210, +11 per 20 min; LESSONS 40): a hazard per
    # awake minute with CGM > 180 and rising, sized over the donor's waking time above 180 × ~0.4 rising [J share]
    if t.ov_more_day > 0:
        t.p_more = float(np.clip(t.ov_more_day / (16 * 60 * max(hi_frac, 0.05) * 0.4), 0.0, 0.05))
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
        self.day_z = 0.0
        self.overrides: list[dict] = []        # planned Temporary Overrides: start, end (min), factor, lo, hi
        self.defense = True                     # rescues and proactive snacks (World's behavior_defense switch)
        self.more_until = -1e9                  # a reactive more-insulin override is running until this minute
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
    def plan_all(self, days: int, carb_scale_of=None):
        """Plan every day up front, so the exported history and the plant's re-simulation see the same plan and
        the Temporary Overrides that go with it can be written into the therapy timeline (LESSONS 40)."""
        for d in range(days + 1):
            self.plan_day(d, carb_scale_of(d) if carb_scale_of else 1.0)
        self.planned_day = days

    def _override(self, start: float, hours: float, factor: float, lo: float, hi: float):
        r = self.rng
        dur = 60.0 * float(np.clip(np.exp(r.normal(math.log(max(hours, 0.25)), 0.6)), 0.25, 12.0))
        w = dict(start=start, end=start + dur, factor=factor)
        if np.isfinite(lo) and np.isfinite(hi): w.update(lo=lo, hi=max(hi, lo))
        self.overrides.append(w)

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
        # daily intake is regulated over 24 h more tightly than per eating occasion: a day total T_d = carbs_day ×
        # exp(z_d), z AR(1) across days (CV 0.22, ρ 0.29: within-person day-to-day carbohydrate CV ~20%, Tarasuk &
        # Beaton 1992 and dietary-record studies; next-day intake r 0.29, Levitsky 2017), shared by the day's events in
        # proportion to their drawn sizes with compensation exponent γ (1 = full 24-h regulation). Without it, simulated
        # entered carbs/day had CV 0.52 (donors 0.40) and daily means no day-to-day persistence (LESSONS 39)
        sd = math.sqrt(math.log(1 + t.intake_cv ** 2))
        self.day_z = t.intake_rho * self.day_z + math.sqrt(1 - t.intake_rho ** 2) * float(r.normal(0, sd))
        day_factor = math.exp(self.day_z - sd ** 2 / 2)
        total_share = (1 - t.skip_breakfast) * 0.22 / 0.286 * main_w + (0.30 + 0.34) / 0.286 * main_w + t.snack_rate
        draws = [share * float(np.exp(r.normal(0, t.meal_cv) - t.meal_cv ** 2 / 2)) for _, _, share in slots]
        comp = (total_share / max(sum(draws), 1e-9)) ** t.intake_comp
        for (kind, mt, share), w in zip(slots, draws):
            grams = t.carbs_day * carb_scale * day_factor * w / max(total_share, 1e-9) * comp
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
                # a target-only override ahead of eating ("pre-meal") at the donor's rate per entry, when the donor's
                # target-only overrides lower the target; raised-target ones go at random waking times below
                if t.ov_tgt_day > 0 and np.isfinite(t.ov_tgt_lo) and t.ov_tgt_lo < 110 \
                        and r.random() < min(1.0, t.ov_tgt_day / max(t.p_entry_meal * 3 + t.p_entry_snack * t.snack_rate, 0.1)):
                    self._override(et - float(r.uniform(15, 60)), t.ov_tgt_h, 1.0, t.ov_tgt_lo, t.ov_tgt_hi)
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
        # everyday activity episodes (evidence/10 §7.2): day-level gamma noise (shape 3) on the person's rate; start
        # times on the UK Biobank day profile (00–06 / 06–12 / 12–18 / 18–24: 0.04 / 0.34 / 0.39 / 0.23), awake only,
        # a share after eating [J]; duration lnN(18 min, 0.75) in 5–150; intensity = (MET − 1)/(METmax − 1) × duty 0.7
        # with MET lnN(3.0, 0.2) and 10% brisk episodes MET U(4.5, 6) (2024 Compendium; Pemberton 2025 mix)
        eat_times = sorted(base + st for _, st, _ in slots)
        day_act = r.gamma(3.0, 1 / 3.0)
        n_act = r.poisson(t.act_rate * (day_act if t.act_day_var else 1.0))
        for _ in range(n_act):
            st = None
            if eat_times and r.random() < t.act_after_meal:
                st = float(r.choice(eat_times)) + float(r.uniform(10, 120))
            else:
                for _try in range(10):
                    blk = int(r.choice(4, p=[0.04, 0.34, 0.39, 0.23]))
                    cand = base + (blk * 6 + r.uniform(0, 6)) * 60
                    if not self.asleep(cand): st = cand; break
            if st is None: continue
            dur = float(np.clip(np.exp(r.normal(math.log(t.act_dur), 0.75)), 5.0, 150.0))
            met = float(r.uniform(4.5, 6.0)) if r.random() < 0.1 else float(np.exp(r.normal(math.log(3.0), 0.2)))
            inten = float(np.clip((met - 1.0) / (t.metmax - 1.0), 0.05, 0.9)) * 0.7
            self.planned.append((st, ("walk", st, dur, inten, 0.0)))
            # a less-insulin override set ahead of the activity, at the donor's rate per episode
            if t.ov_less_day > 0 and r.random() < min(1.0, t.ov_less_day / max(t.act_rate, 0.1)):
                self._override(st - float(r.uniform(0, 30)), t.ov_less_h, t.ov_less_f, t.ov_less_lo, t.ov_less_hi)
        # raised-target-only overrides (the donor's target-only windows sit at >= 110): random waking times [J timing]
        if t.ov_tgt_day > 0 and np.isfinite(t.ov_tgt_lo) and t.ov_tgt_lo >= 110:
            for _ in range(r.poisson(t.ov_tgt_day)):
                self._override(base + float(r.uniform(t.wake, t.bed)), t.ov_tgt_h, 1.0, t.ov_tgt_lo, t.ov_tgt_hi)
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
                kcal_g = 4.0 + (9.0 * meal.fat + 4.0 * meal.protein) / max(meal.grams, 1.0)
                if bp.ge_kcal_max > 0:
                    phi_fat = 1.0      # the energy ceiling carries fat's slowing (its kcal), so no separate factor
                # gastric emptying slows as the stomach empties (Dalla Man 2007: kmax 0.056 → kmin 0.008 /min);
                # the linear chain keeps the fast phase, a slow fraction carries the tail (LESSONS 27) [J size]
                sf = t.meal_slow_frac
                if sf > 0:
                    acts.append(("eat", Parcel(m, meal.grams * sf, kempt=t.meal_slow_k * meal.speed, kabs=bp.kabs,
                                               f=bp.f, label=meal.kind + "_tail")))
                # the liquid part of a mixed meal empties first and fast (nutrient liquids: early delivery 3–8 kcal/min,
                # glucose t½ ~9 min; Calbet 1997, Hunt 1985): a share of the carbohydrate bypasses the energy-limited
                # solid phase [J share] (LESSONS 44)
                ff = t.meal_fast_frac
                if ff > 0:
                    acts.append(("eat", Parcel(m, meal.grams * (1 - sf) * ff, kempt=0.08 * meal.speed, kabs=0.08 * meal.speed,
                                               f=bp.f, label=meal.kind + "_liquid", kcal_per_g=0.0)))
                acts.append(("eat", Parcel(m, meal.grams * (1 - sf) * (1 - ff), kempt=bp.kempt * meal.speed * phi_fat, kabs=bp.kabs * meal.speed,
                                           f=bp.f, label=meal.kind, kcal_per_g=kcal_g)))
                # protein → late glucose appearance: 0.1 g glucose per g protein, delayed ~90 min, peak 3–5 h
                # (Smart 2013; Paterson 2017; evidence/01 §6.3); it is glucose, so fast-glucose bioavailability
                if meal.protein > 0:
                    acts.append(("eat", Parcel(m, 0.1 * meal.protein, kempt=1 / 60.0, kabs=1 / 60.0, delay=90.0,
                                               f=self._f_glucose(), hypo_sensitive=False, label="protein", kcal_per_g=0.0)))
                if meal.fat > 0:
                    acts.append(("fat", m, meal.fat))
                self.log.append((m, meal.kind, meal.grams, meal.entered))
            elif kind == "enter_meal":
                meal = rest[0]
                acts.append(("carb", m, float(meal.entered), t.absorption_entry_h * 3600))
                if meal.bolus is not None:
                    if t.p_split > 0 and r.random() < t.p_split:
                        acts.append(("bolus", m, 0.6 * meal.bolus))
                        self.planned.append((m + float(r.uniform(10, 30)), ("split_rest",)))
                        self.planned.sort(key=lambda x: x[0])
                    else:
                        acts.append(("bolus", m, meal.bolus))
                    self.last_bolus = m
                    if r.random() < t.p_topup:
                        self.planned.append((m + float(r.uniform(20, 60)), ("topup",)))
                        self.planned.sort(key=lambda x: x[0])
                self.log.append((m, "entry", meal.entered, meal.bolus))
            elif kind == "walk":
                acts.append(("exercise",) + tuple(rest)); self.log.append((m, "walk", rest[1], rest[2]))
            elif kind == "graze":
                bp = self.p.body
                acts.append(("eat", Parcel(m, rest[0], kempt=bp.kempt * 1.5, kabs=bp.kabs * 1.5, f=self._f_glucose(), label="graze")))
                self.log.append((m, "graze", rest[0], None))
            elif kind == "split_rest":
                # the rest of a split meal bolus: Loop's recommendation now covers what remains of the entry
                acts.append(("bolus", m, 1.0)); self.last_bolus = m
                self.log.append((m, "split_rest", 0, None))
            elif kind == "topup":
                # a top-up when the meal is running high: CGM above 120 and not falling [J on the condition]
                if self.readings and self.readings[-1][1] > 120 and self.trend() >= 0:
                    acts.append(("bolus", m, 1.0)); self.last_bolus = m
                    self.log.append((m, "topup", 0, self.readings[-1][1]))
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
        # correction: while awake and above the person's correction level (not falling, nothing bolused for
        # corr_wait), a per-minute hazard sized so the donor's measured correction rate is reached over the
        # donor's own time above 180 (LESSONS 26). The app shows CGM on the lock screen and alerts on highs,
        # so this is not gated on a discrete glance.
        # reactive more-insulin override (plant-sent; engine 14b2d58): a rising high while awake, one at a time
        if not asleep and t.p_more > 0 and m >= self.more_until and cgm > 180 and self.trend() > 0 and r.random() < t.p_more:
            dur = 60.0 * float(np.clip(np.exp(r.normal(math.log(max(t.ov_more_h, 0.25)), 0.6)), 0.25, 12.0))
            ov = dict(start=m, end=m + dur, factor=t.ov_more_f)
            if np.isfinite(t.ov_more_lo) and np.isfinite(t.ov_more_hi): ov.update(lo=t.ov_more_lo, hi=max(t.ov_more_hi, t.ov_more_lo))
            acts.append(("override", ov)); self.more_until = m + dur
            self.log.append((m, "override_more", t.ov_more_f, cgm))
        if not asleep and cgm > t.corr_thr and self.trend() > -0.5 and m - self.last_bolus > t.corr_wait \
                and r.random() < t.p_correct:
            acts.append(("bolus", m, 1.0)); self.last_bolus = m
            self.log.append((m, "correction", 0, cgm))
            return acts
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
        if not self.defense:
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
        return acts
