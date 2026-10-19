"""A virtual person's world, minute by minute: body + modulators + exercise + pump + sensor + behavior.

Everything a simulation needs to be reproducible is in (person, seed): the world re-simulates
deterministically, so the history exported for LoopEval's burn-in and the plant's own state at the
first request agree exactly.

Two drives:
  internal  `run_internal(until)` — a simple open-loop pump user (scheduled basal, calculator meal
            boluses and corrections with the person's own ratios). Used for the burn-in history and
            for quick tests. NOT a model of Loop.
  plant     `advance(t0, t1, doses, samples, state)` — LoopEval commands the doses (protocol v2,
            Sources/EvalCore/Engine/ExternalPlant.swift); the world returns CGM at the sample times
            and the person's carb entries and bolus requests.

Ground truth (true BG, IG-free CGM error, carbs eaten, insulin delivered vs absorbed, every behavior
event) is kept in `self.truth` for scoring.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from .behavior import Behavior, sample_behavior_traits
from .device import Pump, SiteTraits
from .exercise import Exercise
from .modulators import Modulators, sample_mod_traits
from .physiology import Body
from .sensor import Sensor

EPOCH = pd.Timestamp("2026-01-05T00:00:00Z")      # a Monday; local time = UTC in the simulation
AUTOBOLUS_AF = 0.4                                 # LoopEval's default auto-bolus application factor (SimulateCommand)
import os as _os
NET_AF = _os.environ.get("PLANT_NET_AF") == "1"     # workaround for binaries older than main 8e86860
DAY = 1440.0


# Loop not acting (donors' disruptions.csv, 168 pilot donors; LESSONS 60): offline gaps and merged mixed windows run the
# scheduled basal with nothing corrected — 0.9/day mean (0.6 median), duration lnN(32 min, 0.86) in 5–360 (2.9% of
# windows ran longer: mostly pumpless stretches, insulin unknown, left out); pump-error cycles keep the last command for
# ~3 min, 2.4/day median. Start hours follow the pooled donor distribution (daytime-heavy).
OUTAGE_HOURS = [0.03, 0.027, 0.018, 0.017, 0.017, 0.019, 0.027, 0.037, 0.041, 0.045, 0.046, 0.047, 0.05, 0.05, 0.05,
                0.056, 0.054, 0.06, 0.06, 0.058, 0.055, 0.056, 0.046, 0.033]


def plan_outages(person, days: int, rng) -> list:
    """[(start_min, end_min, reason)] for the whole run, at the donor's own rates (templates.add_disruption_rates)."""
    rates = person.traits.get("template_rates", {})
    def num(k, default):
        v = rates.get(k)
        try:
            v = float(v)
        except (TypeError, ValueError):
            return default
        return v if np.isfinite(v) else default
    off_day, perr_day = num("offline_day", 0.75), num("perr_day", 2.4)
    h = np.array(OUTAGE_HOURS); h = h / h.sum()
    out = []
    for d in range(days):
        for _ in range(rng.poisson(off_day)):
            st = d * DAY + (rng.choice(24, p=h) + rng.random()) * 60
            dur = float(np.clip(np.exp(rng.normal(math.log(32.0), 0.86)), 5.0, 360.0))
            out.append((st, st + dur, "loop_offline"))
        for _ in range(rng.poisson(perr_day)):
            st = d * DAY + (rng.choice(24, p=h) + rng.random()) * 60
            out.append((st, st + 3.0, "pump_error"))
    return sorted(out)


def activity_carbs(person, bt, g_clamp: float = 140.0, ex_b: float | None = None, frag: bool = False,
                   frag_on: float | None = None) -> float:
    """Grams of glucose per day the person's EXPECTED everyday activity disposes of: the same body over one day
    at its true basal insulin, glucose clamped at g_clamp, with and without the activity (episodes at the person's
    rate and mean duration, mid-day; waking background), difference of the glucose the clamp had to add."""
    from .exercise import ExerciseParams
    import math as _m
    bp = person.body
    out = []
    for active in (True, False):
        b = Body(bp, person.formulation); br = b.basal_rate_u_per_h(); b.prime(br)
        kw = {} if ex_b is None else dict(b=ex_b[0], z_power=ex_b[1])
        ex = Exercise(ExerciseParams(gain=bt.act_gain, background=bt.act_bg if active else 0.0, frag=frag,
                                     frag_seed=int(person.seed) + 1811, **({"frag_on_med": frag_on} if frag_on else {}), **kw))
        if active:
            dur = bt.act_dur * _m.exp(0.75 ** 2 / 2)
            inten = 0.7 * (3.0 * _m.exp(0.2 ** 2 / 2) - 1.0) / (bt.metmax - 1.0)
            n = bt.act_rate
            k = int(n); frac = n - k
            for i in range(k + (1 if frac > 0 else 0)):
                ex.add(9 * 60 + i * 150, dur * (frac if i == k else 1.0), inten, 0.0)
        added = 0.0
        for m in range(1440):
            awake = 7 * 60 <= m < 23 * 60
            e = ex.at(m, awake=awake)
            b.infuse(br / 60.0, m)
            b.g = g_clamp
            b.step(1.0, ex_intensity=e["ex_intensity"], ex_si_boost=e["ex_si_boost"], abs_mult=e["abs_mult"])
            added += (g_clamp - b.g) * bp.vg * bp.bw / 1000.0      # g of glucose to restore the clamp
        out.append(added)
    return max(0.0, out[0] - out[1])


def ts(minute: float) -> str:
    return (EPOCH + pd.Timedelta(minutes=float(minute))).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def minute_of(iso: str) -> float:
    return (pd.Timestamp(iso) - EPOCH).total_seconds() / 60.0


def _gap_mult(person):
    """The donor's own CGM gap rates over the family's measured ones (templates.add_gap_rates; LESSONS 107)."""
    from .sensor import MEASURED_GAPS
    fam = MEASURED_GAPS.get(person.sensor, MEASURED_GAPS["Dexcom G7"])
    r = person.traits.get("template_rates", {})
    gs, gl = r.get("gap_short", np.nan), r.get("gap_long", np.nan)
    ms = float(gs) / sum(fam[:4]) if np.isfinite(gs) else 1.0
    ml = float(gl) / sum(fam[4:]) if np.isfinite(gl) else 1.0
    return (ms, ml)


class World:
    def __init__(self, person, days: int, seed: Optional[int] = None, enable: Optional[dict] = None):
        if enable and isinstance(enable.get("dose_beta"), float):
            # experiment (LESSONS 155): dose-dependent bolus absorption
            person = copy.copy(person); person.body = person.body.scaled(dose_beta=enable["dose_beta"])
        if enable and enable.get("kappa_ins"):
            # experiment (LESSONS 292): insulin-dependent κ (Best 1981)
            person = copy.copy(person); person.body = person.body.scaled(kappa_ins=1.0)
        if enable and enable.get("ceiling_speed"):
            # experiment (LESSONS 150): the meal's own speed scales the stomach's energy ceiling
            person = copy.copy(person); person.body = person.body.scaled(ge_cap_speed=1.0)
        if enable and isinstance(enable.get("meal_k"), float):
            person = copy.deepcopy(person)        # calibration override: meal absorption speed multiplier
            person.body = person.body.scaled(kempt=person.body.kempt * enable["meal_k"], kabs=person.body.kabs * enable["meal_k"])
        if enable and isinstance(enable.get("ge_kcal_mult"), float):
            # experiment (LESSONS 301): the energy ceiling × m for everyone, the person's spread kept (Km fixed, so kempt follows)
            person = copy.deepcopy(person); m_ = enable["ge_kcal_mult"]
            person.body = person.body.scaled(ge_kcal_max=person.body.ge_kcal_max * m_, kempt=person.body.kempt * m_)
        if enable and isinstance(enable.get("ge_kcal"), float):
            person = copy.deepcopy(person)        # gastric-emptying energy ceiling, kcal/min (the body and behavior both read it)
            person.body = person.body.scaled(ge_kcal_max=enable["ge_kcal"])
        if enable and isinstance(enable.get("rcl_mult"), float):
            person = copy.deepcopy(person)        # renal clearance above threshold: Hovorka 0.003/min (default) vs UVA/Padova
            person.body = person.body.scaled(rcl=person.body.rcl * enable["rcl_mult"])   # ke1 0.0005 on Gp ≈ ×1/6 (evidence/01 §4.3)
        if enable and isinstance(enable.get("ge_mult"), float):
            person = copy.deepcopy(person)        # scales the person's emptying (Vmax and kempt together, Km fixed): centre of
            b = person.body                       # the between-person distribution, inside evidence/09's 2–5 kcal/min
            person.body = b.scaled(ge_kcal_max=b.ge_kcal_max * enable["ge_mult"], kempt=b.kempt * enable["ge_mult"])
        if enable and (isinstance(enable.get("ins_p2"), float) or isinstance(enable.get("ins_p2e"), float)):
            person = copy.deepcopy(person)        # insulin-action rates (ablation: clamp-fitted vs Loop-curve action)
            person.body = person.body.scaled(p2=enable.get("ins_p2", person.body.p2), p2e=enable.get("ins_p2e", person.body.p2e))
        if enable and isinstance(enable.get("ge_gamma"), float):
            person.body = person.body.scaled(ge_gamma=enable["ge_gamma"])
        if enable and isinstance(enable.get("ge_hyper"), float):
            person = copy.deepcopy(person)
            person.body = person.body.scaled(ge_hyper=enable["ge_hyper"])
        self.person = person
        self.days = days
        # per-bolus absorption spread (A4): 0.15 net of SI from repeat clamps (Heise 2017); free-living estimates are wider
        # (Schiavon ATTD 2020: intra-individual CV of absorption parameters 34–94% under closed loop) (LESSONS 209)
        self.dose_cv = float(enable["dose_cv"]) if enable and isinstance(enable.get("dose_cv"), float) else 0.15
        seed = person.seed if seed is None else seed
        ss = np.random.SeedSequence(seed)
        r_mod, r_beh, r_sen, r_pump, r_abs, r_misc = [np.random.default_rng(s) for s in ss.spawn(6)]
        self.mod_traits = person.traits.get("mod") or sample_mod_traits(r_misc, person.age, person.sex)
        if person.truth.get("basal_profile") and self.mod_traits.dawn:
            # a donor's own basal profile already carries their dawn need (the body's EGP follows it); on quiet mornings
            # donors' delivered insulin falls 05–07 vs 01–03 (0.92) and glucose drifts −7 mg/dL 03→07, which the
            # profile alone reproduces (−5.6) while the extra dawn bump gave +11 (LESSONS 51)
            self.mod_traits = copy.deepcopy(self.mod_traits); self.mod_traits.dawn = False
        if enable:
            self.mod_traits.enabled.update({k: v for k, v in enable.items() if k in self.mod_traits.enabled})
            if isinstance(enable.get("heat_a"), float) or isinstance(enable.get("heat_T"), float):
                self.mod_traits = copy.deepcopy(self.mod_traits)
                if isinstance(enable.get("heat_a"), float): self.mod_traits.heat_a = enable["heat_a"]; self.mod_traits.enabled["heat"] = True
                if isinstance(enable.get("heat_T"), float): self.mod_traits.heat_T = enable["heat_T"]
            if enable.get("menstrual_late"):
                self.mod_traits = copy.deepcopy(self.mod_traits); self.mod_traits.menstrual_shape = "late"
                self.mod_traits.enabled["menstrual"] = True
            if "steroid" in enable and "steroid" not in self.mod_traits.enabled:      # persons sampled before B14
                self.mod_traits = copy.deepcopy(self.mod_traits); self.mod_traits.enabled["steroid"] = bool(enable["steroid"])
            if isinstance(enable.get("preg_week"), float) and getattr(self.mod_traits, "menstruating", False):
                # scenario X9: menstruating people are pregnant at this gestational week from day 0; no menstrual cycle
                self.mod_traits = copy.deepcopy(self.mod_traits); self.mod_traits.preg_week = enable["preg_week"]
                self.mod_traits.menstruating = False
            if isinstance(enable.get("day_tau"), float):
                self.mod_traits = copy.deepcopy(self.mod_traits); self.mod_traits.day_tau = enable["day_tau"]
            if isinstance(enable.get("circ_uniform"), float) and enable["circ_uniform"] > 0:
                # experiment: the seven Visentin classes equally likely (Hinshaw 2013: no population B/L/D pattern in T1D)
                from .modulators import VISENTIN
                self.mod_traits = copy.deepcopy(self.mod_traits)
                self.mod_traits.circ_class = VISENTIN[int(np.random.default_rng(person.seed + 11).integers(len(VISENTIN)))][0]
            if isinstance(enable.get("circ_swing"), float):
                self.mod_traits = copy.deepcopy(self.mod_traits)
                self.mod_traits.circ_swing = enable["circ_swing"]
                self.mod_traits.circ_low = float(np.clip(1.0 - enable["circ_swing"] * (1.0 - self.mod_traits.circ_raw), 0.4, 1.0))
        self.enable = dict(exercise=True, site_failure=True, pump_faults=True, compression=True, behavior_defense=True, graze=True,
                           perfect_person=False, fat=True, lipohypertrophy=True)
        if enable: self.enable.update({k: v for k, v in enable.items() if k in self.enable and isinstance(v, bool)})
        self.mods = Modulators(self.mod_traits, days)
        if enable and enable.get("steroid_course"):
            # scenario: one glucocorticoid course starting on day 3 (B14), whatever the person's own draw
            self.mods.gc = self.mods._glucocorticoid(self.mod_traits, force_day=3)
            self.mod_traits.enabled["steroid"] = True
        if enable and isinstance(enable.get("snack_minus"), float):
            person.traits["snack_minus"] = float(enable["snack_minus"])   # labeled pulses that are not eating (LESSONS 127)
        if enable and "slot_true" in enable: person.traits["slot_true"] = bool(enable["slot_true"])
        if enable and "snack_entry_hours" in enable: person.traits["snack_entry_hours"] = bool(enable["snack_entry_hours"])
        # the donor's own meal / snack split of carb entries, default since 2026-10-19 (LESSONS 280); --disable entry_split
        person.traits["entry_split"] = bool(enable.get("entry_split", True)) if enable else True
        self.beh_traits = person.traits.get("behavior") or sample_behavior_traits(r_beh, person)
        if enable and isinstance(enable.get("meal_slow"), float):
            self.beh_traits.meal_slow_frac = enable["meal_slow"]
        if enable and isinstance(enable.get("main_w"), float):
            self.beh_traits.main_weight = enable["main_w"]
        if enable and isinstance(enable.get("meal_fast"), float):
            self.beh_traits.meal_fast_frac = enable["meal_fast"]
        if enable and isinstance(enable.get("lead_shift"), float):
            self.beh_traits.lead_shift = enable["lead_shift"]
        if enable and enable.get("lead_own") is False:      # back to the four category windows
            self.beh_traits.lead_own = False
        if enable and isinstance(enable.get("lead_sd"), float):
            self.beh_traits.lead_sd = enable["lead_sd"]
        if enable and isinstance(enable.get("meal_drink_p"), float):
            self.beh_traits.meal_drink_p = float(enable["meal_drink_p"])
        if enable and isinstance(enable.get("meal_drink_share"), float):
            self.beh_traits.meal_drink_share = float(enable["meal_drink_share"])
        if (enable or {}).get("count_brazeau", True):   # default since 2026-10-19 (Brazeau 2013; LESSONS 304); --disable count_brazeau
            self.beh_traits = copy.deepcopy(self.beh_traits); self.beh_traits.count_size = "brazeau"   # LESSONS 146
        if enable and isinstance(enable.get("pro_shift"), float):
            self.beh_traits.pro_onset = self.beh_traits.pro_onset + float(enable["pro_shift"])   # LESSONS 126
        if enable and enable.get("own_clock"):
            self.beh_traits.own_clock = True
        if enable and enable.get("entry_clock"):
            self.beh_traits.entry_clock = True
        if enable and "graze_fast" in enable:
            self.beh_traits.graze_fast = bool(enable["graze_fast"])      # default on (LESSONS 158); --disable graze_fast
        if enable and isinstance(enable.get("graze_keep"), float):
            self.beh_traits.graze_keep = float(np.clip(enable["graze_keep"], 0.0, 1.0))
        if enable and isinstance(enable.get("announce_mult"), float):
            self.beh_traits.announce_mult = float(np.clip(enable["announce_mult"], 0.0, 1.0))
        if enable and enable.get("meal_gap_gev") is False:
            self.beh_traits.meal_gap_gev = False
        if enable and isinstance(enable.get("count_sd_mult"), float):
            # per-meal mismatch between the grams dosed for and the glucose delivered (ablation, LESSONS 149)
            self.beh_traits.count_sd = self.beh_traits.count_sd * enable["count_sd_mult"]
        if enable and isinstance(enable.get("graze_split"), float):
            # experiment (LESSONS 162): the same daily grazing grams as k times as many sips and bites, 1/k the size
            k_ = float(enable["graze_split"])
            self.beh_traits.graze_per_day = self.beh_traits.graze_per_day * k_
            self.beh_traits.graze_g = self.beh_traits.graze_g / k_
        if enable and enable.get("skip_drop"):
            self.beh_traits.skip_drop = True
        if enable and enable.get("split_full"):
            self.beh_traits.split_full = True
        if enable and enable.get("corr_own"):
            self.beh_traits.corr_own = True
        if enable and enable.get("corr_size_own"):
            self.beh_traits.corr_size_own = True
        if enable and enable.get("stack_own"):
            self.beh_traits.stack_own = True
        if enable and enable.get("graze_unann"):
            self.beh_traits.graze_unann = True
        if enable and enable.get("corr_trend"):
            self.beh_traits.corr_trend = True
        if enable and enable.get("ex_no_eat"):
            self.beh_traits.ex_no_eat = True
        if enable and enable.get("unent_light"):
            self.beh_traits.unent_light = True
        if enable and enable.get("unent_split"):
            self.beh_traits.unent_split = True
        if enable and isinstance(enable.get("entry_size_b"), float):
            self.beh_traits.entry_size_b = enable["entry_size_b"]
        if enable and enable.get("ex_mets"):
            self.beh_traits.ex_mets = True
        if enable and isinstance(enable.get("wake_mult"), float):
            # experiment (LESSONS 274): the chance a night alarm wakes the person, scaled
            self.beh_traits.p_wake_alarm = float(min(0.98, self.beh_traits.p_wake_alarm * enable["wake_mult"]))
        if enable and isinstance(enable.get("ex_surge"), float):
            # C4 calibration: catecholamine EGP surge, mg/kg/min at intensity 1 for fully anaerobic work (LESSONS 247)
            person = copy.deepcopy(person); person.body = person.body.scaled(ex_egp_surge=enable["ex_surge"]); self.person = person
        if enable and enable.get("skip_own"):
            # experiment (LESSONS 182): the donor's own breakfast-skip share (days with no labeled pulse >= 10 g-eq at
            # 05:00-10:30 local; donors median 0.18, the sim's constant 0.10)
            try:
                sk_ = float(person.traits.get("template_rates", {}).get("skip_bfast"))
                if np.isfinite(sk_): self.beh_traits.skip_breakfast = float(np.clip(sk_, 0.0, 0.9))
            except (TypeError, ValueError):
                pass
        if enable and enable.get("log_own"):
            # experiment (LESSONS 179): the donor's own treatment-logging rate (carb entries with no bolus within 30 min at
            # CGM < 130, per day) over the sim's median 1.4 treatments a day, as the person's logging probability
            # preferred: the donor's share of low-start labeled pulses (< 75 mg/dL) that were entered (LESSONS 179);
            # fallback: the logged-treatment rate over the sim's 1.4 treatments a day
            tr_ = person.traits.get("template_rates", {})
            try:
                sh_ = float(tr_.get("low_entered_share"))
            except (TypeError, ValueError):
                sh_ = float("nan")
            if np.isfinite(sh_):
                self.beh_traits.p_log_pro = self.beh_traits.p_log_rescue = float(np.clip(sh_, 0.0, 1.0))
            else:
                try:
                    r_ = float(tr_.get("treat_log_day"))
                    if np.isfinite(r_):
                        self.beh_traits.p_log_pro = self.beh_traits.p_log_rescue = float(np.clip(r_ / 1.4, 0.0, 1.0))
                except (TypeError, ValueError):
                    pass
        if enable and isinstance(enable.get("p_log_pro"), float):
            self.beh_traits.p_log_pro = enable["p_log_pro"]
        if enable and isinstance(enable.get("p_log_rescue"), float):
            self.beh_traits.p_log_rescue = enable["p_log_rescue"]
        if enable and enable.get("graze_eve"):
            self.beh_traits.graze_eve = True
        if enable and enable.get("slot_comp"):
            self.beh_traits.slot_comp = True
        if enable and isinstance(enable.get("snack_fast"), float):
            self.beh_traits.snack_fast_frac = enable["snack_fast"]          # snacks' fast share (LESSONS 159)
        if enable and isinstance(enable.get("gi_cv"), float):
            self.beh_traits.gi_cv = enable["gi_cv"]            # per-meal emptying-speed spread (ablation, LESSONS 147)
        if enable and isinstance(enable.get("meal_fast_sd"), float):
            self.beh_traits.meal_fast_sd = enable["meal_fast_sd"]
        if enable and isinstance(enable.get("meal_slow_k"), float):
            self.beh_traits.meal_slow_k = enable["meal_slow_k"]
        if enable and enable.get("perfect_person"):
            # diagnostic: every meal entered exactly and bolused at the meal; no snacks, no exercise
            t = self.beh_traits
            t.p_entry_meal = t.p_entry_snack = 1.0; t.count_bias = 0.0; t.count_sd = 0.0
            t.p_bolus_with_entry = 1.0; t.bolus_timing = "immediate"; t.lead_own = False; t.calc_up = t.calc_down = 0.0
            t.ex_per_week = 0.0; t.p_free_bolus = 0.0
        if not self.enable["graze"]: self.beh_traits.graze_per_day = 0.0
        if enable and enable.get("act_day_var") is False: self.beh_traits.act_day_var = False
        if enable and isinstance(enable.get("act_after_meal"), float): self.beh_traits.act_after_meal = enable["act_after_meal"]   # experiment (LESSONS 303)
        if enable and enable.get("intake_var") is False: self.beh_traits.intake_cv = 1e-6
        self.beh = Behavior(self.beh_traits, person, r_beh)
        self.beh.defense = self.enable["behavior_defense"]      # rescues and proactive snacks (switch was unwired before)
        if enable and enable.get("overrides") is False:       # ablation: no Temporary Overrides
            self.beh_traits.ov_less_day = 0.0; self.beh_traits.ov_tgt_day = 0.0; self.beh_traits.p_more = 0.0
        if enable and enable.get("reactive_overrides") is False:
            self.beh_traits.p_more = 0.0
        from .exercise import ExerciseParams
        self.ex_b = (enable.get("ex_b"), enable.get("ex_zp", 1.0)) if enable and isinstance(enable.get("ex_b"), float) else None
        self.act_frag = bool((enable or {}).get("act_frag", True))     # default since 2026-10-18 (Pete, LESSONS 163)
        # posture (LESSONS 163; --disable posture): insulin clamps, the PK's reference, are done supine; sitting up cuts
        # subcutaneous blood flow 29–47% and insulin absorption 19–44% (Hildebrandt 1985, 17 patients with diabetes).
        # Awake = upright: absorption × (1 − p), p per person U(0.19, 0.44) on its own stream; asleep = supine
        # half of Hildebrandt's sitting-vs-flat-supine contrast by default: real evenings include reclining and real
        # sleep is not constant flat supine, so the full step at bedtime overstated the night/day contrast [J]
        # (LESSONS 169: night lows 53% -> 46%, CV and Hurst pass, 37 of 51)
        self.posture_p = (float(enable["posture_mult"]) if enable and isinstance(enable.get("posture_mult"), float) else 0.5) \
            * float(np.random.default_rng(int(person.seed) + 1907).uniform(0.19, 0.44)) \
            if (enable or {}).get("posture", True) else 0.0                   # default since 2026-10-18 (Pete, LESSONS 163)
        self.posture_ramp = bool((enable or {}).get("posture_ramp", False))   # experiment (LESSONS 172)
        # sleep_util (experiment, LESSONS 173): sleep lowers glucose utilisation (Van Cauter 1991/1997: at constant glucose
        # infusion glucose rises 20-30% during sleep, ~2/3 from sleep itself, through lower brain and peripheral use).
        # While asleep, net glucose rises by delta × ~1 mg/kg/min of insulin-independent (mostly brain) uptake, delta per
        # person U(0.05, 0.12) [J within the studies' size], ramping in over the first 30 min of sleep
        self.sleep_util = float(np.random.default_rng(int(person.seed) + 2011).uniform(0.05, 0.12)) \
            if (enable or {}).get("sleep_util", True) else 0.0     # default since 2026-10-18 (LESSONS 214)
        self._sleep_since = None
        self.ge_circ = bool((enable or {}).get("ge_circ", False))
        self.ex = Exercise(ExerciseParams(gain=self.beh_traits.act_gain, background=self.beh_traits.act_bg,
                                          frag=self.act_frag, frag_seed=int(person.seed) + 1811,
                                          **({"frag_on_med": float(enable["frag_on"])} if enable and isinstance(enable.get("frag_on"), float) else {}),
                                          **({} if self.ex_b is None else dict(b=self.ex_b[0], z_power=self.ex_b[1]))))
        # energy balance: a person eats for their activity. The donor's TDD (the measured constraint, G4) was spent
        # in a life that included it, so the glucose their everyday activity uses is added to what they eat
        # (activity_carbs: clamp probe, active day vs rest day; LESSONS 34)
        if self.enable["exercise"] and not (enable or {}).get("perfect_person") and "act_carbs" not in person.traits:
            person.traits["act_carbs"] = activity_carbs(person, self.beh_traits, ex_b=self.ex_b, frag=self.act_frag,
                                                        frag_on=float(enable["frag_on"]) if enable and isinstance(enable.get("frag_on"), float) else None)
        if self.enable["exercise"]:
            self.beh_traits.carbs_day += person.traits.get("act_carbs", 0.0)
        if (enable or {}).get("budget_all", True) and not (enable or {}).get("perfect_person"):
            # default since 2026-10-18 (Pete, LESSONS 143; --disable budget_all): the donor's TDD covered ALL of their eating, unlogged grazing and hypo treatment
            # included, so the TDD budget pays for the person's expected grazing and the donor's measured rescue carbs
            # (template rescues_per_day × rescue_size_med); meals and snacks share what is left
            bt = self.beh_traits
            graze = bt.graze_per_day * bt.graze_g * float(np.exp(0.4 ** 2 / 2)) * min(1.0, bt.graze_keep)
            rr = person.traits.get("template_rates", {})
            try:
                resc = float(rr.get("rescues_per_day")) * float(rr.get("rescue_size_med"))
            except (TypeError, ValueError):
                resc = 0.0
            if not np.isfinite(resc): resc = 0.0
            bt = self.beh_traits = copy.deepcopy(bt)
            if (enable or {}).get("budget_tight", True):   # default since 2026-10-18 (review loop, LESSONS 202)
                # experiment (LESSONS 202): the TDD budget also pays for pre-emptive carbohydrate (the defense team eats
                # ~8% of the budget on the evidence base, c223) and heavy grazers are not floored at half
                pro = 0.08 * bt.carbs_day
                bt.carbs_day = max(0.2 * bt.carbs_day, bt.carbs_day - graze - resc - pro)
            else:
                bt.carbs_day = max(0.5 * bt.carbs_day, bt.carbs_day - graze - resc)
            self.beh.t = bt                                  # the Behavior was built above with the old traits
        # every day planned now: the export writes the planned Temporary Overrides into the therapy timeline, and
        # the plant's re-simulation reproduces the identical plan (LESSONS 40)
        gi = (lambda d: 0.7 if self.mods.illness(d * DAY + 720)[2] else 1.0) if self.mod_traits.enabled.get("illness") else None
        # GLP-1 receptor agonist adjunct (glp1.py, evidence/16): a per-person trait, off unless --enable glp1
        self.glp1 = None
        if (enable or {}).get("glp1"):
            from .glp1 import GLP1, sample_glp1
            wk = enable.get("glp1_weeks") if isinstance(enable.get("glp1_weeks"), float) else None
            ag = ("semaglutide" if enable.get("glp1_sema") else "tirzepatide" if enable.get("glp1_tirz")
                  else "liraglutide" if enable.get("glp1_lira") else None)
            gt = sample_glp1(np.random.default_rng(person.seed + 41), weeks=wk, agent=ag)
            if isinstance(enable.get("glp1_hour"), float): gt.inj_hour = enable["glp1_hour"]
            self.glp1 = GLP1(gt)
            if self.glp1.t.retuned and self.glp1.t.weeks_at_start >= 11:
                # people re-tune on the drug: basal −8%, ISF +11%, CR +4% by day 77 (Pasqua 2025)
                self.person = person = copy.deepcopy(person)
                st = person.settings
                st.update(basal_uh=st["basal_uh"] * 0.92, isf=st["isf"] * 1.11, cr=st["cr"] * 1.04)
            g0 = gi
            gi = (lambda d, g0=g0: (g0(d) if g0 else 1.0) * self.glp1.carb_mult(d * DAY + 720))
        tgt_e = person.traits.get("template_rates", {}).get("entered_g_raw")
        if (enable or {}).get("entry_g_own") and tgt_e is not None and np.isfinite(float(tgt_e)) and float(tgt_e) > 0:
            # experiment (LESSONS 220): move grams between meals and unentered grazing so the planned ENTERED grams/day match
            # the donor's own, total intake unchanged (heavy announcers enter most of what they eat; the graze draw is not
            # from data and was taking their meal grams)
            bt = self.beh.t
            g_tot = bt.graze_per_day * bt.graze_g * float(np.exp(0.4 ** 2 / 2))
            for _ in range(3):
                tmp = copy.deepcopy(self.beh); tmp.plan_all(days, gi)
                got = sum(x[1][1].entered or 0.0 for x in tmp.planned if x[1][0] == "enter_meal") / max(days + 1, 1)
                if got <= 0: break
                k = float(np.clip(float(tgt_e) / got, 0.67, 1.5))
                add = bt.carbs_day * (k - 1.0)
                if add > 0: add = min(add, g_tot)                    # only as much as grazing can give up
                bt.carbs_day += add; g_tot = max(g_tot - add, 0.0)
                bt.graze_per_day = g_tot / max(bt.graze_g * float(np.exp(0.4 ** 2 / 2)), 1e-9)
                if abs(k - 1) < 0.03: break
        if (enable or {}).get("entry_own") and tgt_e is not None and np.isfinite(float(tgt_e)) and float(tgt_e) > 0:
            # experiment (LESSONS 205): entry probabilities scaled so the planned ENTERED grams/day match the donor's own
            # raw entered grams (paired, the sim entered 0.84× its donors'), measured on a dry-run copy of the plan, so
            # every random stream is unchanged; meal sizes and the count error (Brazeau) are left as drawn
            for _ in range(3):
                tmp = copy.deepcopy(self.beh); tmp.plan_all(days, gi)
                got = sum(x[1][1].entered or 0.0 for x in tmp.planned if x[1][0] == "enter_meal") / max(days + 1, 1)
                if got <= 0: break
                k = float(tgt_e) / got
                self.beh.t.p_entry_meal = float(min(1.0, self.beh.t.p_entry_meal * k))
                self.beh.t.p_entry_snack = float(min(1.0, self.beh.t.p_entry_snack * k))
                if abs(k - 1) < 0.03: break
        self.beh.plan_all(days, gi)
        self._scenarios(enable or {})
        self.outages = plan_outages(person, days, np.random.default_rng(person.seed + 23)) if (enable or {}).get("outages", True) is not False else []
        youth = 3.0 if person.age < 18 else 1.0          # Kanapka 2022: 5.8% of sets at 14–17 vs 1.9% in adults
        lh = bool(self.enable.get("lipohypertrophy", True)
                  and np.random.default_rng(person.seed + 31).random() < (0.42 if person.age < 18 else 0.26))
        site = SiteTraits(lh_person=lh, p_fail=SiteTraits.p_fail * youth if self.enable["site_failure"] else 0.0,
                          p_full=SiteTraits.p_full * youth, p_dislodge=SiteTraits.p_dislodge * youth,
                          planned_days=self.beh_traits.site_days)
        if enable and isinstance(enable.get("site_cv"), float):
            site.site_cv = float(enable["site_cv"])
        self.pump = Pump(site, r_pump, family=person.pump, faults=self.enable["pump_faults"])
        self.sensor = Sensor(person.sensor, r_sen,
                             compression_rate=person.traits.get("compression_rate", float(r_misc.gamma(2.37, 1 / 75.7)))
                             if self.enable["compression"] else 0.0,
                             overrides={k: v for k, v in (enable or {}).items() if k.startswith("sensor_")},
                             gap_mult=_gap_mult(person) if (enable or {}).get("gap_own", True) else None)
        self.r_abs = r_abs
        # settings edits (LESSONS 41): dated, multiplicative changes to the basal / ISF / CR schedules at the donor's
        # measured rate per setting; size lnN(median 3.6%, σ 1.06 → p90 14%), sign random [J: donors' edits are only
        # weakly reactive, corr 0.16]. Applied by LoopEval through the exported therapy timeline, from day 2 on.
        r_edit = np.random.default_rng(np.random.SeedSequence(seed).spawn(7)[6])
        rates = person.traits.get("template_rates", {})
        cum = dict(basal=1.0, isf=1.0, cr=1.0); ev = []
        if not (enable and enable.get("edits") is False):
            for k in ("basal", "isf", "cr"):
                try: rate = float(rates.get(f"edit_{k}_day", 0.0) or 0.0)
                except (TypeError, ValueError): rate = 0.0
                if not np.isfinite(rate): rate = 0.0
                for _ in range(r_edit.poisson(rate * max(days - 2, 0))):
                    m = (2 + r_edit.uniform(0, days - 2)) * DAY
                    size = min(0.5, float(np.exp(r_edit.normal(math.log(0.036), 1.06))))
                    ev.append((m, k, size if r_edit.random() < 0.5 else -size))
        self.setting_eras = [(0.0, dict(cum))]
        for (m, k, d) in sorted(ev):
            cum[k] *= math.exp(d); self.setting_eras.append((m, dict(cum)))
        bp = person.body
        if enable and enable.get("risk") is False: bp = bp.scaled(risk_lambda=0.0)
        if enable and enable.get("counterreg") is False: bp = bp.scaled(cr_max=0.0)
        if enable and isinstance(enable.get("cr_mult"), float): bp = bp.scaled(cr_max=bp.cr_max * enable["cr_mult"])   # LESSONS 166
        if enable and isinstance(enable.get("cr_tau"), float): bp = bp.scaled(cr_tau=enable["cr_tau"])   # experiment, LESSONS 274
        self.body = Body(bp, person.formulation)
        br = self.body.basal_rate_u_per_h()
        self.body.prime(br)
        # the body starts at its true basal; the pump will deliver what is commanded from minute 0
        self.minute = 0.0
        self.readings: dict[int, Optional[float]] = {}     # minute -> reading (None = withheld)
        self.truth = []                                    # per minute: (m, bg, ra, egp, si, delivered, absorbed_mu)
        self.entries = []                                  # carb entries made (minute, grams, absorption_s)
        self.bolus_requests = []                           # (minute, ratio)
        self.loop_state = dict(iob=0.0, rec_bolus=0.0, cob=0.0, bg=np.nan)
        # internal controller state
        self.int_doses: list = []                          # exported history: (type, start_m, end_m, units, automatic)
        self.ex_log: list = []
        self.received: list = []                           # every dose LoopEval sent, as received: (type, start, end, U)
        self.fat_events: list = []                         # (minute, fat g) — transient fat-induced insulin resistance
        self.fat_log: list = []                            # every fat event, kept for the truth file (LESSONS 288)
        self.sent_overrides: list = []                     # reactive Temporary Overrides sent to LoopEval (plant-sent)
        # per person: Wolpert 2013 measured +42% insulin (mean) after a 60 g-fat dinner; 1 − ρ·60/50 at mean ρ 0.35 gives that,
        # with a wide individual spread (evidence/01 §6.3). U(0, 0.35) gave the median person half of it (LESSONS 46)
        self.fat_rho = float(r_misc.uniform(0.1, 0.6))
        # fat_rel (default since 2026-10-18, Pete; LESSONS 151; --disable fat_rel): the fat resistance relative to the person's own usual diet. Their ISF, CR and
        # TDD were tuned on their ordinary meals, average fat included, so the term is normalised to a mean of 1 over the
        # planned days (as caffeine is, relative to the person's habitual intake); fattier than usual still dips SI
        self.fat_norm = 1.0
        if (enable or {}).get("fat_rel", True) and self.enable.get("fat", True):
            ev = sorted((tm, a[1].fat) for (tm, a) in self.beh.planned if a[0] == "eat_meal" and getattr(a[1], "fat", 0) > 0)
            if ev:
                grid = np.arange(DAY, days * DAY, 5.0); mult = np.ones_like(grid)
                for (t0, fat) in ev:
                    x = (grid - t0) / 60.0
                    w = np.where(x < 2, 0.0, np.where(x < 3, x - 2, np.where(x < 6, 1.0, np.where(x < 10, (10 - x) / 4, 0.0))))
                    mult *= 1.0 - self.fat_rho * min(fat, 80.0) / 50.0 * w
                self.fat_norm = float(np.maximum(mult, 0.4).mean())
        # hyperglycaemia-induced insulin resistance (B11): 24 h at ~360 mg/dL lowers insulin-stimulated glucose uptake by
        # 26% in T1D (Vuorinen-Markkola 1992; Yki-Järvinen 1987). State H relaxes toward 0.26·clip((G − 140)/220, 0, 1)
        # with τ 12 h [J, both ways]; insulin sensitivity × (1 − H) (LESSONS 43)
        self.hyper_res = 0.0
        self.hyper_on = not (enable and enable.get("glucotox") is False)
        # size at 360 mg/dL: 0.26 fits the T1D clamps (Vuorinen-Markkola 1992, Yki-Järvinen 1987); Boden 1996 measured −55%
        # after 68 h at 227 mg/dL in healthy people (evidence/15)
        self.hyper_max = enable.get("glucotox_max") if enable and isinstance(enable.get("glucotox_max"), float) else 0.26

    # ------------------------------------------------------------------ one minute
    # ------------------------------------------------------------------ stress scenarios (candidates.py; LESSONS 85)
    SCENARIO_DAY = 4

    def _scenarios(self, enable: dict):
        """Ground-truth events on day SCENARIO_DAY, switched on with --enable scenario_<name>; identical across arms."""
        d0 = self.SCENARIO_DAY * DAY
        self.scenario_at = {}
        L = float(enable.get("scenario_level", 1.0)) if isinstance(enable.get("scenario_level"), float) else 1.0
        self.scenario_level = L
        if enable.get("scenario_illness"):
            # non-gastrointestinal illness: SI −30%, EGP +10% (inside the B6 ranges), 3 days with ramps
            self.mods.ill.append(dict(start=d0, dur=3 * DAY, gi=False, si_drop=0.30 * L, egp=0.10 * L))
        if enable.get("scenario_exercise"):
            st = d0 + 17 * 60          # 60 min moderate (intensity 0.6) late-afternoon session: McMahon 2007's design
            self.beh.planned.append((st, ("exercise", st, 60.0 * L, 0.6, 0.1))); self.beh.planned.sort(key=lambda x: x[0])
        if enable.get("scenario_missed_bolus"):
            # dinner eaten with no carb entry and no bolus
            for i, (t, act) in enumerate(self.beh.planned):
                if act[0] == "eat_meal" and act[1].kind == "meal" and d0 + 16 * 60 <= t <= d0 + 22 * 60:
                    meal = act[1]
                    self.beh.planned = [(tt, a) for (tt, a) in self.beh.planned if not (a[0] == "enter_meal" and a[1] is meal)]
                    meal.entered, meal.bolus = None, None
                    meal.grams *= L; meal.fat *= L; meal.protein *= L      # level scales the unbolused meal
                    break
        if enable.get("scenario_site_failure"):
            self.scenario_at[d0 + 14 * 60] = "dislodge"      # no insulin reaches the tissue until the person changes the site
        if enable.get("scenario_sensor_fault"):
            self.scenario_at[d0 + 2 * 60] = "false_low"      # 45-min false low of 40 mg/dL at 02:00 (a compression-type dip)

    def _minute(self, pending_actions: list):
        m = self.minute
        ev = self.scenario_at.get(m) if getattr(self, "scenario_at", None) else None
        if ev == "dislodge":
            self.pump.dislodge_at = m
        elif ev == "false_low":
            self.sensor.comp = dict(start=m, dur=45.0, depth=40.0 * self.scenario_level, kind="dip", tau=8.0)
        si, egp, absm_env = self.mods.at(m)
        bprof = self.person.truth.get("basal_profile")
        if bprof:                                   # basal need by local hour (EGP at basal insulin), LESSONS 48
            hh = (m % DAY) / 60.0; k = int(hh) % 24; f = hh - int(hh)
            egp *= bprof[k] * (1 - f) + bprof[(k + 1) % 24] * f
        si *= self._fat_si(m)
        if self.glp1 is not None: si *= self.glp1.si_mult(m)
        if self.hyper_on:
            target = self.hyper_max * min(1.0, max(0.0, (self.body.g - 140.0) / 220.0))
            # asymmetric: builds over ~6 h (Fanelli 1995: −15% after 6 h at 243 mg/dL; −22% after 15 h at 306), fades over
            # ~24 h (resistance persisted 1.5–10 h after normoglycaemia; Vuorinen-Markkola 1992, Fanelli 1995) [J within the
            # studies' bounds; was 12 h both ways] (LESSONS 80)
            self.hyper_res += (target - self.hyper_res) / (360.0 if target > self.hyper_res else 1440.0)
            si *= 1.0 - self.hyper_res
        gi_ill = self.mods.illness(m)[2] if self.mod_traits.enabled.get("illness") else False
        ex = self.ex.at(m, awake=not self.beh.asleep(m)) if self.enable["exercise"] else dict(ex_intensity=0, ex_anaerobic=0, ex_si_boost=0, abs_mult=1)
        absm_site, bio = self.pump.site_state(m)
        u_basal, u_bolus = self.pump.deliver(m)
        if u_basal > 0:
            self.body.infuse(u_basal, m)
        if u_bolus > 0:   # per-dose absorption jitter, CV 15% (Heise 2017 repeat clamps; evidence/07)
            cv = self.pump.t.lh_dose_cv if self.pump.site_lh else self.dose_cv
            self.body.infuse(u_bolus, m, omega=float(np.exp(self.r_abs.normal(0, cv) - cv ** 2 / 2)),
                             dose=getattr(self.pump, "bolus_size", 0.0) or u_bolus)
        u = u_basal + u_bolus
        ud = 0.0
        if self.sleep_util:
            if self.beh.asleep(m):
                if self._sleep_since is None: self._sleep_since = m
                ud = self.sleep_util * 1.0 * min(1.0, (m - self._sleep_since) / 30.0)
            else:
                self._sleep_since = None
        gm = 1.0
        if self.ge_circ:
            # circadian gastric emptying (Goo 1987: evening half-time ~54% longer than morning for the same solid meal):
            # x1.25 06-11 h, x0.8 17-23 h, x1.0 otherwise, ramped over an hour at each boundary [J shape] (LESSONS 180)
            hh = (m % DAY) / 60.0
            def _seg(h):
                return 1.25 if 6 <= h < 11 else 0.8 if 17 <= h < 23 else 1.0
            gm = 0.5 * (_seg(hh) + _seg((hh - 1.0) % 24))
        self.body.step(1.0, si_mult=si, egp_mult=egp, util_drop=ud, ge_mult=gm, ex_intensity=ex["ex_intensity"],
                       ex_anaerobic=ex["ex_anaerobic"], ex_si_boost=ex["ex_si_boost"],
                       abs_mult=absm_env * absm_site * ex["abs_mult"] * self._posture_mult(m), bio=bio)
        if int(m) % 5 == 0: self.ex_log.append((m, ex["ex_si_boost"]))     # exercise sensitivity, saved as truth ex_boost
        asleep = self.beh.asleep(m)
        reading = self.sensor.step(m, self.body.g, asleep=asleep)
        if reading is not False:
            self.readings[int(round(m))] = reading
        acts = self.beh.minute(m, reading, self.loop_state, carb_scale=0.7 if gi_ill else 1.0)
        for a in acts:
            kind = a[0]
            if kind == "eat":
                if self.glp1 is not None and a[1].label not in ("protein",):
                    a[1].kempt /= self.glp1.ge_stretch(self.minute)     # slowed gastric emptying of oral carbohydrate
                self.body.eat(a[1])
            elif kind == "exercise": self.ex.add(*a[1:])
            elif kind == "site_change": self.pump.change_site(m)
            elif kind == "fat": self.fat_events.append((a[1], a[2])); self.fat_log.append((a[1], a[2]))
            else: pending_actions.append(a)
        # a failing site the person notices: a long high that corrections did not move (eda L52) [J: ~3 h]
        # (checked every minute on the latest reading the person can see: gated on report minutes only, the
        # hazard ran at 1/900 per minute and a dislodged site went unnoticed for ~15 waking hours; LESSONS 30)
        seen = self.beh.readings[-1][1] if self.beh.readings and m - self.beh.readings[-1][0] <= 15 else None
        if self.pump.failing(m) and seen and seen > 250 and not asleep \
                and self.beh.rng.random() < 1.0 / 180:
            self.pump.change_site(m); self.beh.log.append((m, "site_change_early", 0, reading))
        # an occlusion alarm: changed promptly if awake, or if the alarm wakes them (alarms repeat ~15 min)
        if self.pump.alarm and int(m) % 15 == 0:
            p = 0.5 if not asleep else self.beh_traits.p_wake_alarm
            if self.beh.rng.random() < p:
                self.pump.change_site(m); self.beh.log.append((m, "site_change_alarm", 0, reading))
        self.truth.append((m, self.body.g, self.body.ra, self.body.egp, si, u, self.body.insulin_absorbed * self.person.bw / 1000.0))
        self.minute = m + 1.0

    def _posture_mult(self, m: float) -> float:
        """Upright absorption × (1 − p) while awake, supine asleep (A4b). With posture_ramp the reduction fades linearly
        over the last 3 h before bedtime (evenings reclining before sleep) [J shape] (LESSONS 172)."""
        if not self.posture_p or self.beh.asleep(m): return 1.0
        if self.posture_ramp:
            tb = self.beh.minutes_to_bed(m)
            if tb < 180.0: return 1.0 - self.posture_p * tb / 180.0
        return 1.0 - self.posture_p

    def _fat_si(self, m: float) -> float:
        """Fat-induced insulin resistance: 1 − ρ·fat/50 at full effect, ramping in from 2 h, full 3–6 h,
        gone by 10 h after the meal (evidence/01 §6.3)."""
        if not self.enable.get("fat", True): return 1.0
        if not self.fat_events: return 1.0 / self.fat_norm
        mult = 1.0
        keep = []
        for (t, fat) in self.fat_events:
            x = (m - t) / 60.0
            if x > 10: continue
            keep.append((t, fat))
            w = 0.0 if x < 2 else (x - 2) if x < 3 else 1.0 if x < 6 else (10 - x) / 4
            mult *= 1.0 - self.fat_rho * min(fat, 80.0) / 50.0 * w
        self.fat_events = keep
        return max(mult, 0.4) / self.fat_norm

    # ------------------------------------------------------------------ internal drive (burn-in)
    def _calc_iob(self, m: float) -> float:
        """Loop-style IOB of the internal history (exponential curve, net of scheduled basal) — what
        the person's app would show; the internal drive's stand-in for Loop's IOB."""
        peak, dia = (55.0, 360.0) if self.person.formulation in ("fiasp", "lyumjev") else (75.0, 360.0)
        tau = peak * (1 - peak / dia) / (1 - 2 * peak / dia)
        a = 2 * tau / dia; S = 1 / (1 - a + (1 + a) * math.exp(-dia / tau))
        def remain(t):
            if t <= 0: return 1.0
            if t >= dia: return 0.0
            return 1 - S * (1 - a) * ((t ** 2 / (tau * dia * (1 - a)) - t / tau - 1) * math.exp(-t / tau) + 1)
        sched = self.person.settings["basal_uh"] / 60.0
        iob = 0.0
        for (typ, s, e, units, auto) in self.int_doses[-200:]:
            if m - s > dia: continue
            net = units - (sched * (e - s) if typ == "basal" else 0.0)
            iob += net * remain(m - (s + e) / 2)
        return iob

    def run_internal(self, until: float):
        st = self.person.settings
        while self.minute < until:
            m = self.minute
            if int(m) % 5 == 0:
                prof = st.get("basal_profile") or [1.0] * 24
                rate = st["basal_uh"] * prof[int((m % DAY) // 60) % 24]
                self.pump.command(m, m + 5, rate / 12.0)
                self.int_doses.append(("basal", m, m + 5, rate / 12.0, True))
                self.loop_state["iob"] = self._calc_iob(m)
            acts: list = []
            self._minute(acts)
            for a in acts:
                if a[0] == "carb":
                    self.entries.append((a[1], a[2], a[3]))
                elif a[0] == "split_units":
                    first = sum(d[3] for d in self.int_doses if d[0] == "bolus" and a[2] <= d[1] <= a[2] + 2)
                    units = round(first * a[3] / 0.05) * 0.05
                    if units > 0:
                        self.pump.command(m + 1, m + 1, units, bolus=True)
                        self.int_doses.append(("bolus", m + 1, m + 1, units, False))
                    self.bolus_requests.append((a[1], -units))
                elif a[0] in ("bolus", "bolus_units", "bolus_min"):
                    if a[0] == "bolus_min":     # the larger of the person's own dialled size and the recommendation (LESSONS 224)
                        units = round(max(float(a[2]), self._internal_rec(a[1])) / 0.05) * 0.05
                    else:
                        units = float(a[2]) if a[0] == "bolus_units" else round(max(0.0, a[2] * self._internal_rec(a[1])) / 0.05) * 0.05
                    if units > 0:
                        self.pump.command(m + 1, m + 1, units, bolus=True)
                        self.int_doses.append(("bolus", m + 1, m + 1, units, False))
                    self.bolus_requests.append((a[1], a[2]))

    def _internal_rec(self, m: float) -> float:
        st = self.person.settings
        carbs = sum(g for (t, g, _) in self.entries if m - 30 <= t <= m + 1)
        bg = next((v for k, v in sorted(self.readings.items(), reverse=True) if v), st["target"])
        if self.enable.get("perfect_person"):
            # the diagnostic person doses each meal's own carbs exactly; netting the previous meal's bolus as IOB
            # (the calculator's way) under-doses stacked meals and reads as a units fault in selfcheck (LESSONS 40)
            return max(0.0, carbs / st["cr"])
        return max(0.0, carbs / st["cr"] + (bg - st["target"]) / st["isf"] - max(self._calc_iob(m), 0.0))

    # ------------------------------------------------------------------ plant drive (LoopEval)
    def advance(self, t0: float, t1: float, doses: list, samples: list, state: dict) -> dict:
        """Protocol v2 step. `doses`: [(type, start_m, end_m, units)] newly delivered by LoopEval.
        Returns dict(bg=[...], carbs=[...], boluses=[...])."""
        for (typ, s, e, units) in doses:
            self.received.append((typ, s, e, units))
            # The plant's clock is already past t0 (it advanced through the last request's t1), so a dose
            # starting at t0 lies in the past: deliver it from NOW with its full volume and duration.
            # Dropping it lost every bolus and a fifth of every basal segment (LESSONS 19).
            lag = max(0.0, self.minute - s)
            e2 = (e if typ == "basal" else s) + lag
            self.pump.command(s + lag, e2, units, bolus=(typ == "bolus"))
        if state:
            self.loop_state.update({k: v for k, v in state.items() if v is not None})
        carbs, boluses, overrides = [], [], []
        while self.minute <= t1:
            acts: list = []
            self._minute(acts)
            for a in acts:
                if a[0] == "carb":
                    carbs.append(dict(t=ts(a[1]), grams=float(a[2]), absorption_s=float(a[3])))
                    self.entries.append((a[1], a[2], a[3]))
                elif a[0] == "bolus":
                    # LoopEval before main 8e86860 decided the automatic dose WITHOUT the plant bolus (~1.4x
                    # every meal; LESSONS 21). Fixed in the engine; PLANT_NET_AF=1 restores the old workaround
                    # (ask for ratio - AF) only for runs on an older binary.
                    r = float(a[2])
                    if NET_AF and self.person.strategy == "autobolus":
                        r = max(0.0, r - AUTOBOLUS_AF)
                    boluses.append(dict(t=ts(a[1]), ratio=r))
                    self.bolus_requests.append((a[1], a[2]))
                elif a[0] == "bolus_units":
                    boluses.append(dict(t=ts(a[1]), units=float(a[2])))
                    self.bolus_requests.append((a[1], -float(a[2])))     # negative = absolute units
                elif a[0] == "bolus_min":
                    # plant mode: the internal history is empty (LoopEval doses), so _internal_rec would ignore real IOB; the
                    # person's dialled amount is sent as is (donor requested sizes already include those at/below Loop's)
                    u_ = round(float(a[2]) / 0.05) * 0.05
                    boluses.append(dict(t=ts(a[1]), units=u_))
                    self.bolus_requests.append((a[1], -u_))
                elif a[0] == "split_units":
                    # LoopEval delivered the first part as a bolus dose starting within a few minutes of the request
                    first = sum(u for (typ, s0, e0, u) in self.received if typ == "bolus" and a[2] - 1 <= s0 <= a[2] + 10)
                    if first <= 0 and a[1] - a[2] < 15:
                        # LoopEval delivers a request at its next step: not here yet, look again in 5 min
                        self.beh.planned.append((a[1] + 5, ("split_rest", a[2], a[3]))); self.beh.planned.sort(key=lambda x: x[0])
                        continue
                    units = round(first * a[3] / 0.05) * 0.05
                    if units > 0:
                        boluses.append(dict(t=ts(a[1]), units=units))
                    self.bolus_requests.append((a[1], -units))
                elif a[0] == "override":
                    w = a[1]; d = dict(t=ts(w["start"]), end=ts(w["end"]), factor=float(w["factor"]))
                    if "lo" in w: d.update(targetLo=float(w["lo"]), targetHi=float(w["hi"]))
                    overrides.append(d); self.sent_overrides.append(w)
        bg = []
        for s in samples:
            k = int(round(s))
            v = self.readings.get(k, None)
            if v is None:   # nearest earlier report within the cadence (clock jitter)
                for j in range(1, 3):
                    if (k - j) in self.readings and self.readings[k - j] is not None and (k - j) > s - 3:
                        v = self.readings[k - j]; break
            bg.append(v)
        out = dict(bg=bg, carbs=carbs, boluses=boluses)
        if overrides: out["overrides"] = overrides
        return out
