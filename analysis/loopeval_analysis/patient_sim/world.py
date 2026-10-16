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


def activity_carbs(person, bt, g_clamp: float = 140.0) -> float:
    """Grams of glucose per day the person's EXPECTED everyday activity disposes of: the same body over one day
    at its true basal insulin, glucose clamped at g_clamp, with and without the activity (episodes at the person's
    rate and mean duration, mid-day; waking background), difference of the glucose the clamp had to add."""
    from .exercise import ExerciseParams
    import math as _m
    bp = person.body
    out = []
    for active in (True, False):
        b = Body(bp, person.formulation); br = b.basal_rate_u_per_h(); b.prime(br)
        ex = Exercise(ExerciseParams(gain=bt.act_gain, background=bt.act_bg if active else 0.0))
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


class World:
    def __init__(self, person, days: int, seed: Optional[int] = None, enable: Optional[dict] = None):
        if enable and isinstance(enable.get("meal_k"), float):
            import copy
            person = copy.deepcopy(person)        # calibration override: meal absorption speed multiplier
            person.body = person.body.scaled(kempt=person.body.kempt * enable["meal_k"], kabs=person.body.kabs * enable["meal_k"])
        if enable and isinstance(enable.get("ge_kcal"), float):
            import copy
            person = copy.deepcopy(person)        # gastric-emptying energy ceiling, kcal/min (the body and behavior both read it)
            person.body = person.body.scaled(ge_kcal_max=enable["ge_kcal"])
        if enable and (isinstance(enable.get("ins_p2"), float) or isinstance(enable.get("ins_p2e"), float)):
            import copy
            person = copy.deepcopy(person)        # insulin-action rates (ablation: clamp-fitted vs Loop-curve action)
            person.body = person.body.scaled(p2=enable.get("ins_p2", person.body.p2), p2e=enable.get("ins_p2e", person.body.p2e))
        if enable and isinstance(enable.get("ge_hyper"), float):
            import copy
            person = copy.deepcopy(person)
            person.body = person.body.scaled(ge_hyper=enable["ge_hyper"])
        self.person = person
        self.days = days
        seed = person.seed if seed is None else seed
        ss = np.random.SeedSequence(seed)
        r_mod, r_beh, r_sen, r_pump, r_abs, r_misc = [np.random.default_rng(s) for s in ss.spawn(6)]
        self.mod_traits = person.traits.get("mod") or sample_mod_traits(r_misc, person.age, person.sex)
        if enable:
            self.mod_traits.enabled.update({k: v for k, v in enable.items() if k in self.mod_traits.enabled})
            if isinstance(enable.get("circ_swing"), float):
                import copy
                self.mod_traits = copy.deepcopy(self.mod_traits)
                self.mod_traits.circ_swing = enable["circ_swing"]
                self.mod_traits.circ_low = float(np.clip(1.0 - enable["circ_swing"] * (1.0 - self.mod_traits.circ_raw), 0.4, 1.0))
        self.enable = dict(exercise=True, site_failure=True, pump_faults=True, compression=True, behavior_defense=True, graze=True,
                           perfect_person=False, fat=True)
        if enable: self.enable.update({k: v for k, v in enable.items() if k in self.enable and isinstance(v, bool)})
        self.mods = Modulators(self.mod_traits, days)
        self.beh_traits = person.traits.get("behavior") or sample_behavior_traits(r_beh, person)
        if enable and isinstance(enable.get("meal_slow"), float):
            self.beh_traits.meal_slow_frac = enable["meal_slow"]
        if enable and isinstance(enable.get("main_w"), float):
            self.beh_traits.main_weight = enable["main_w"]
        if enable and isinstance(enable.get("meal_fast"), float):
            self.beh_traits.meal_fast_frac = enable["meal_fast"]
        if enable and isinstance(enable.get("meal_slow_k"), float):
            self.beh_traits.meal_slow_k = enable["meal_slow_k"]
        if enable and enable.get("perfect_person"):
            # diagnostic: every meal entered exactly and bolused at the meal; no snacks, no exercise
            t = self.beh_traits
            t.p_entry_meal = t.p_entry_snack = 1.0; t.count_bias = 0.0; t.count_sd = 0.0
            t.p_bolus_with_entry = 1.0; t.bolus_timing = "immediate"; t.calc_up = t.calc_down = 0.0
            t.ex_per_week = 0.0; t.p_free_bolus = 0.0
        if not self.enable["graze"]: self.beh_traits.graze_per_day = 0.0
        if enable and enable.get("act_day_var") is False: self.beh_traits.act_day_var = False
        if enable and enable.get("intake_var") is False: self.beh_traits.intake_cv = 1e-6
        self.beh = Behavior(self.beh_traits, person, r_beh)
        self.beh.defense = self.enable["behavior_defense"]      # rescues and proactive snacks (switch was unwired before)
        if enable and enable.get("overrides") is False:       # ablation: no Temporary Overrides
            self.beh_traits.ov_less_day = 0.0; self.beh_traits.ov_tgt_day = 0.0
        from .exercise import ExerciseParams
        self.ex = Exercise(ExerciseParams(gain=self.beh_traits.act_gain, background=self.beh_traits.act_bg))
        # energy balance: a person eats for their activity. The donor's TDD (the measured constraint, G4) was spent
        # in a life that included it, so the glucose their everyday activity uses is added to what they eat
        # (activity_carbs: clamp probe, active day vs rest day; LESSONS 34)
        if self.enable["exercise"] and not (enable or {}).get("perfect_person") and "act_carbs" not in person.traits:
            person.traits["act_carbs"] = activity_carbs(person, self.beh_traits)
        if self.enable["exercise"]:
            self.beh_traits.carbs_day += person.traits.get("act_carbs", 0.0)
        # every day planned now: the export writes the planned Temporary Overrides into the therapy timeline, and
        # the plant's re-simulation reproduces the identical plan (LESSONS 40)
        gi = (lambda d: 0.7 if self.mods.illness(d * DAY + 720)[2] else 1.0) if self.mod_traits.enabled.get("illness") else None
        self.beh.plan_all(days, gi)
        youth = 3.0 if person.age < 18 else 1.0          # Kanapka 2022: 5.8% of sets at 14–17 vs 1.9% in adults
        site = SiteTraits(p_fail=SiteTraits.p_fail * youth if self.enable["site_failure"] else 0.0,
                          p_full=SiteTraits.p_full * youth, p_dislodge=SiteTraits.p_dislodge * youth,
                          planned_days=self.beh_traits.site_days)
        self.pump = Pump(site, r_pump, family=person.pump, faults=self.enable["pump_faults"])
        self.sensor = Sensor(person.sensor, r_sen,
                             compression_rate=person.traits.get("compression_rate", float(r_misc.gamma(2.37, 1 / 75.7)))
                             if self.enable["compression"] else 0.0,
                             overrides={k: v for k, v in (enable or {}).items() if k.startswith("sensor_")})
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
        self.received: list = []                           # every dose LoopEval sent, as received: (type, start, end, U)
        self.fat_events: list = []                         # (minute, fat g) — transient fat-induced insulin resistance
        # per person: Wolpert 2013 measured +42% insulin (mean) after a 60 g-fat dinner; 1 − ρ·60/50 at mean ρ 0.35 gives that,
        # with a wide individual spread (evidence/01 §6.3). U(0, 0.35) gave the median person half of it (LESSONS 46)
        self.fat_rho = float(r_misc.uniform(0.1, 0.6))
        # hyperglycaemia-induced insulin resistance (B11): 24 h at ~360 mg/dL lowers insulin-stimulated glucose uptake by
        # 26% in T1D (Vuorinen-Markkola 1992; Yki-Järvinen 1987). State H relaxes toward 0.26·clip((G − 140)/220, 0, 1)
        # with τ 12 h [J, both ways]; insulin sensitivity × (1 − H) (LESSONS 43)
        self.hyper_res = 0.0
        self.hyper_on = not (enable and enable.get("glucotox") is False)

    # ------------------------------------------------------------------ one minute
    def _minute(self, pending_actions: list):
        m = self.minute
        si, egp, absm_env = self.mods.at(m)
        si *= self._fat_si(m)
        if self.hyper_on:
            target = 0.26 * min(1.0, max(0.0, (self.body.g - 140.0) / 220.0))
            self.hyper_res += (target - self.hyper_res) / 720.0
            si *= 1.0 - self.hyper_res
        gi_ill = self.mods.illness(m)[2] if self.mod_traits.enabled.get("illness") else False
        ex = self.ex.at(m, awake=not self.beh.asleep(m)) if self.enable["exercise"] else dict(ex_intensity=0, ex_anaerobic=0, ex_si_boost=0, abs_mult=1)
        absm_site, bio = self.pump.site_state(m)
        u_basal, u_bolus = self.pump.deliver(m)
        if u_basal > 0:
            self.body.infuse(u_basal, m)
        if u_bolus > 0:   # per-dose absorption jitter, CV 15% (Heise 2017 repeat clamps; evidence/07)
            self.body.infuse(u_bolus, m, omega=float(np.exp(self.r_abs.normal(0, 0.15) - 0.15 ** 2 / 2)))
        u = u_basal + u_bolus
        self.body.step(1.0, si_mult=si, egp_mult=egp, ex_intensity=ex["ex_intensity"],
                       ex_anaerobic=ex["ex_anaerobic"], ex_si_boost=ex["ex_si_boost"],
                       abs_mult=absm_env * absm_site * ex["abs_mult"], bio=bio)
        asleep = self.beh.asleep(m)
        reading = self.sensor.step(m, self.body.g, asleep=asleep)
        if reading is not False:
            self.readings[int(round(m))] = reading
        acts = self.beh.minute(m, reading, self.loop_state, carb_scale=0.7 if gi_ill else 1.0)
        for a in acts:
            kind = a[0]
            if kind == "eat": self.body.eat(a[1])
            elif kind == "exercise": self.ex.add(*a[1:])
            elif kind == "site_change": self.pump.change_site(m)
            elif kind == "fat": self.fat_events.append((a[1], a[2]))
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

    def _fat_si(self, m: float) -> float:
        """Fat-induced insulin resistance: 1 − ρ·fat/50 at full effect, ramping in from 2 h, full 3–6 h,
        gone by 10 h after the meal (evidence/01 §6.3)."""
        if not self.fat_events or not self.enable.get("fat", True): return 1.0
        mult = 1.0
        keep = []
        for (t, fat) in self.fat_events:
            x = (m - t) / 60.0
            if x > 10: continue
            keep.append((t, fat))
            w = 0.0 if x < 2 else (x - 2) if x < 3 else 1.0 if x < 6 else (10 - x) / 4
            mult *= 1.0 - self.fat_rho * min(fat, 80.0) / 50.0 * w
        self.fat_events = keep
        return max(mult, 0.4)

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
                self.pump.command(m, m + 5, st["basal_uh"] / 12.0)
                self.int_doses.append(("basal", m, m + 5, st["basal_uh"] / 12.0, True))
                self.loop_state["iob"] = self._calc_iob(m)
            acts: list = []
            self._minute(acts)
            for a in acts:
                if a[0] == "carb":
                    self.entries.append((a[1], a[2], a[3]))
                elif a[0] in ("bolus", "bolus_units"):
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
        carbs, boluses = [], []
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
        bg = []
        for s in samples:
            k = int(round(s))
            v = self.readings.get(k, None)
            if v is None:   # nearest earlier report within the cadence (clock jitter)
                for j in range(1, 3):
                    if (k - j) in self.readings and self.readings[k - j] is not None and (k - j) > s - 3:
                        v = self.readings[k - j]; break
            bg.append(v)
        return dict(bg=bg, carbs=carbs, boluses=boluses)
