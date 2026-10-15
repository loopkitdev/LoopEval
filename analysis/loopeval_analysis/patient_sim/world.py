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
DAY = 1440.0


def ts(minute: float) -> str:
    return (EPOCH + pd.Timedelta(minutes=float(minute))).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def minute_of(iso: str) -> float:
    return (pd.Timestamp(iso) - EPOCH).total_seconds() / 60.0


class World:
    def __init__(self, person, days: int, seed: Optional[int] = None, enable: Optional[dict] = None):
        self.person = person
        self.days = days
        seed = person.seed if seed is None else seed
        ss = np.random.SeedSequence(seed)
        r_mod, r_beh, r_sen, r_pump, r_abs, r_misc = [np.random.default_rng(s) for s in ss.spawn(6)]
        self.mod_traits = person.traits.get("mod") or sample_mod_traits(r_misc, person.age, person.sex)
        if enable:
            self.mod_traits.enabled.update({k: v for k, v in enable.items() if k in self.mod_traits.enabled})
        self.enable = dict(exercise=True, site_failure=True, pump_faults=True, compression=True, behavior_defense=True,
                           perfect_person=False)
        if enable: self.enable.update({k: v for k, v in enable.items() if k in self.enable})
        self.mods = Modulators(self.mod_traits, days)
        self.beh_traits = person.traits.get("behavior") or sample_behavior_traits(r_beh, person)
        if enable and enable.get("perfect_person"):
            # diagnostic: every meal entered exactly and bolused at the meal; no snacks, no exercise
            t = self.beh_traits
            t.p_entry_meal = t.p_entry_snack = 1.0; t.count_bias = 0.0; t.count_sd = 0.0
            t.p_bolus_with_entry = 1.0; t.bolus_timing = "immediate"; t.calc_up = t.calc_down = 0.0
            t.ex_per_week = 0.0; t.p_free_bolus = 0.0
        self.beh = Behavior(self.beh_traits, person, r_beh)
        self.ex = Exercise()
        site = SiteTraits(p_fail=SiteTraits.p_fail if self.enable["site_failure"] else 0.0,
                          planned_days=self.beh_traits.site_days)
        self.pump = Pump(site, r_pump, family=person.pump, faults=self.enable["pump_faults"])
        self.sensor = Sensor(person.sensor, r_sen,
                             compression_rate=person.traits.get("compression_rate", float(r_misc.gamma(2.37, 1 / 75.7)))
                             if self.enable["compression"] else 0.0)
        self.r_abs = r_abs
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

    # ------------------------------------------------------------------ one minute
    def _minute(self, pending_actions: list):
        m = self.minute
        si, egp, absm_env = self.mods.at(m)
        gi_ill = self.mods.illness(m)[2] if self.mod_traits.enabled.get("illness") else False
        ex = self.ex.at(m) if self.enable["exercise"] else dict(ex_intensity=0, ex_anaerobic=0, ex_si_boost=0, abs_mult=1)
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
            else: pending_actions.append(a)
        # a failing site the person notices: a long high that corrections did not move (eda L52) [J: ~3 h]
        if self.pump.failing(m) and reading and reading > 250 and not asleep \
                and self.beh.rng.random() < 1.0 / 180:
            self.pump.change_site(m); self.beh.log.append((m, "site_change_early", 0, reading))
        # an occlusion alarm: changed promptly if awake, or if the alarm wakes them (alarms repeat ~15 min)
        if self.pump.alarm and int(m) % 15 == 0:
            p = 0.5 if not asleep else self.beh_traits.p_wake_alarm
            if self.beh.rng.random() < p:
                self.pump.change_site(m); self.beh.log.append((m, "site_change_alarm", 0, reading))
        self.truth.append((m, self.body.g, self.body.ra, self.body.egp, si, u, self.body.insulin_absorbed * self.person.bw / 1000.0))
        self.minute = m + 1.0

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
        return max(0.0, carbs / st["cr"] + (bg - st["target"]) / st["isf"] - max(self._calc_iob(m), 0.0))

    # ------------------------------------------------------------------ plant drive (LoopEval)
    def advance(self, t0: float, t1: float, doses: list, samples: list, state: dict) -> dict:
        """Protocol v2 step. `doses`: [(type, start_m, end_m, units)] newly delivered by LoopEval.
        Returns dict(bg=[...], carbs=[...], boluses=[...])."""
        for (typ, s, e, units) in doses:
            self.pump.command(s, e if typ == "basal" else s, units, bolus=(typ == "bolus"))
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
                    boluses.append(dict(t=ts(a[1]), ratio=float(a[2])))
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
