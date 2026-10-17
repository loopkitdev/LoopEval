"""GLP-1 receptor agonist adjunct therapy (semaglutide, tirzepatide, dulaglutide, liraglutide): evidence/16.

A per-person trait. The drug level comes from one-compartment kinetics with first-order absorption, summed over every
dose since the person started (dose escalation included). It is normalized to 1 at the maintenance steady-state
average. Each effect follows a saturating curve of that level, E = (c/(c+EC50))/(1/(1+EC50)), EC50 0.5 [I], so the
within-week rhythm after each injection, and its dependence on injection weekday and hour, comes from the
kinetics alone; no study measured it (evidence/16 §3).

Effects, relative to the same person off the drug (randomized T1D trials on AID unless marked):
  carbs eaten    × (1 − c_max·E·ramp(3 wk))   semaglutide −25%, tirzepatide −32% (Pasqua 2025: 95 vs 142 g/day;
                                              ADJUST-T1D 137 → 107; TIRTLE1 −429 kcal/day)
  gastric emptying  kempt ÷ (1 + 0.42·E + 0.25·E·exp(−weeks since the last dose step / 4))
                                              (pooled scintigraphy ×1.45; larger after starting or a dose step, then
                                              partial tachyphylaxis)
  insulin sensitivity  × (1 + s_direct·E·ramp(2 wk)) × (1 + s_weight·(1 − e^(−weeks/20)))
                                              direct +10% semaglutide / +20% tirzepatide; weight-mediated +11% over
                                              ~20 weeks (ADJUST-T1D: weight explains 17% of the insulin drop at week 4,
                                              48% at week 26)
  settings       after ≥ 11 weeks, people have re-tuned: basal ×0.92, ISF ×1.11, CR ×1.04 (Pasqua 2025, day 77)
Check: ADJUST-T1D's bolus −30%, basal −12 to −16%, TDD −20 to −23% should come out without tuning (LESSONS 87).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

DAY = 1440.0

AGENTS = {
    # half-life (h), tmax (h), interval (h), escalation [(weeks, dose)], maintenance dose, carb effect, direct SI effect
    "semaglutide": dict(t_half=165.0, tmax=36.0, tau=168.0, steps=[(0, 0.25), (4, 0.5), (8, 1.0)], dose=1.0, carb=0.25, si=0.10),
    "tirzepatide": dict(t_half=120.0, tmax=24.0, tau=168.0, steps=[(0, 2.5), (4, 5.0)], dose=5.0, carb=0.32, si=0.20),
    "dulaglutide": dict(t_half=113.0, tmax=48.0, tau=168.0, steps=[(0, 0.75), (4, 1.5)], dose=1.5, carb=0.20, si=0.10),
    "liraglutide": dict(t_half=13.0, tmax=11.0, tau=24.0, steps=[(0, 0.6), (1, 1.2), (2, 1.8)], dose=1.8, carb=0.20, si=0.10),
}
EC50 = 0.5


@dataclass
class GLP1Traits:
    on: bool = False
    agent: str = "semaglutide"
    weeks_at_start: float = 12.0        # weeks on the drug when the simulation starts
    inj_weekday: int = 0                # 0 = the simulation's first weekday (a Monday)
    inj_hour: float = 20.0              # local hour of the injection (daily agents use it every day)
    retuned: bool = True                # settings re-tuned after ≥ 11 weeks (Pasqua 2025)


def sample_glp1(rng: np.random.Generator, weeks: float | None = None, agent: str | None = None) -> GLP1Traits:
    return GLP1Traits(on=True, agent=agent or str(rng.choice(["semaglutide", "tirzepatide"], p=[0.7, 0.3])),
                      weeks_at_start=float(weeks if weeks is not None else rng.choice([0.0, 2.0, 6.0, 12.0, 26.0])),
                      inj_weekday=int(rng.integers(0, 7)), inj_hour=float(rng.choice([8.0, 12.0, 20.0, 22.0])))


class GLP1:
    def __init__(self, t: GLP1Traits):
        self.t = t
        a = AGENTS[t.agent]
        self.a = a
        self.ke = math.log(2) / a["t_half"]
        self.ka = self._ka(a["tmax"], self.ke)
        # dose times (hours from the simulation epoch), back to the start of therapy
        start_h = -t.weeks_at_start * 168.0
        first = start_h + ((t.inj_weekday * 24 + t.inj_hour - start_h) % a["tau"])
        self.doses = []
        h = first
        while h < 120 * 24:
            wk = (h - start_h) / 168.0
            d = [dose for (w, dose) in a["steps"] if wk >= w][-1]
            self.doses.append((h, d / a["dose"]))
            h += a["tau"]
        self.step_weeks = [w for (w, _) in a["steps"]]
        # steady-state average level at the maintenance dose (per unit dose): 1/(ke·tau) for this normalization
        self.css = (1.0 / (self.ke * a["tau"]))

    @staticmethod
    def _ka(tmax, ke):
        lo, hi = ke * 1.0001, 50.0
        f = lambda ka: math.log(ka / ke) / (ka - ke) - tmax
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if f(mid) > 0: lo = mid
            else: hi = mid
        return 0.5 * (lo + hi)

    def level(self, m: float) -> float:
        """Drug level at minute m, 1 = maintenance steady-state average."""
        h = m / 60.0
        k, ka = self.ke, self.ka
        c = 0.0
        for (t0, d) in self.doses:
            if t0 > h: break
            x = h - t0
            c += d * ka / (ka - k) * (math.exp(-k * x) - math.exp(-ka * x))
        return c / self.css

    def effect(self, m: float) -> float:
        c = self.level(m)
        return (c / (c + EC50)) * (1 + EC50)

    def weeks(self, m: float) -> float:
        return self.t.weeks_at_start + m / (7 * DAY)

    def carb_mult(self, m: float) -> float:
        ramp = 1 - math.exp(-self.weeks(m) / 3.0)
        return 1.0 - self.a["carb"] * self.effect(m) * ramp

    def ge_stretch(self, m: float) -> float:
        w = self.weeks(m)
        since = min((w - s for s in self.step_weeks if w >= s), default=w)
        e = self.effect(m)
        return 1.0 + 0.42 * e + 0.25 * e * math.exp(-since / 4.0)

    def si_mult(self, m: float) -> float:
        w = self.weeks(m)
        direct = 1.0 + self.a["si"] * self.effect(m) * (1 - math.exp(-w / 2.0))
        weight = 1.0 + 0.11 * (1 - math.exp(-w / 20.0))
        return direct * weight
