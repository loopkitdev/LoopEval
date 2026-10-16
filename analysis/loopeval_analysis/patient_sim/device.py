"""The pump and the infusion site: what reaches the tissue, given what the controller commanded.

Structure (evidence/06 §5): LoopEval's trace holds what the controller COMMANDED (already
pulse-quantized by the engine for patch pumps, ice L25 — stage A). Everything after that is here,
and the controller never sees it: non-delivery becomes phantom IOB in Loop's own bookkeeping.

  B  mechanism     per-device bias + AR(1) basal flow error (τ 45 min, 1-h sd by pump family and
                   rate) + per-bolus error (sd ≈ c/√U) + start-up transient after each site change
                   (Freckmann 2019: first 12 h +0.1…+9.9%; 780G first hour −11%)
  C  environment   pressure/temperature bubbles — scenario only, OFF
  D  fluid path    state machine OK → {partial (silent), full occlusion, bubble, dislodged}; tracks
                   missed volume; a full occlusion alarms at V_alarm missed units (2–4.5 U, pump trait;
                   twiist detects early); a clearing occlusion releases part of the missed volume
                   (780G mean 1.12 U); dislodgement never alarms
  E  site          absorption speed over the site's life (Swan 2009), bioavailability of a failing
                   site (eda L52 early-change signature; Kanapka 2022 3.3% of sets), lipohypertrophy
                   (F ≈ 0.75–0.8, Famulla 2016) — OFF by default until a prevalence is assigned
  Leakage/backflow: no quantitative source (evidence/06 #11) — not modelled.

Rates of events per wear are [J] priors anchored on the evidence table; the calibration targets are
the eda L52 early-change signature and share, then Kanapka's failure rate (evidence/06 §5).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

DAY = 1440.0


@dataclass(frozen=True)
class PumpFamily:
    name: str
    basal_sd_1h: float          # 1-h window sd of basal delivery at 1 U/h (evidence/06 #2)
    rate_exp: float = -0.3      # sd ∝ rate^exp (Omnipod 10–13% at 1 U/h → ~22% at 0.1 U/h)
    bolus_c: float = 0.03       # per-bolus sd = c / sqrt(units), floor 0.6% (evidence/06 §1.4)
    v_alarm: float = 3.0        # U missed before an occlusion alarm (2–4.5 U)
    startup: tuple = (0.05, 0.05)   # mean, sd of the start-up deviation fraction, decays τ 4 h
    change_gap: float = 15.0    # min of no delivery at a site change [unverified: "minutes"]


PUMPS = {
    "Omnipod": PumpFamily("Omnipod", basal_sd_1h=0.11, bolus_c=0.12, v_alarm=3.0),
    "twiist": PumpFamily("twiist", basal_sd_1h=0.03, bolus_c=0.02, v_alarm=0.5, startup=(0.0, 0.01)),
    "Medtronic": PumpFamily("Medtronic", basal_sd_1h=0.045, bolus_c=0.03, v_alarm=2.5, startup=(-0.05, 0.05)),
    "Tandem": PumpFamily("Tandem", basal_sd_1h=0.045, bolus_c=0.03, v_alarm=3.0),
}


@dataclass
class SiteTraits:
    # sets ending early with prolonged hyperglycaemia, ALL causes: 3.3% (adults 1.9%, ages 14–17 5.8%; Kanapka 2022,
    # 22,741 wears). Split across failing absorption, full occlusion and dislodgement [J split]; the earlier 15% + 2% + 3%
    # was ~6× the measured rate and made whole days of highs (LESSONS 43)
    p_fail: float = 0.012           # sites whose absorption fails before the planned change
    fail_floor: float = 0.3         # absorbed fraction a failed site decays to [J]
    fail_tau: float = 240.0         # min
    p_partial: float = 0.4          # silent partial occlusions per wear (Gibney: 36–50% of standard-set wears)
    p_full: float = 0.003           # full occlusions per wear (within Kanapka's 1.9% adult total) [J split]
    p_bubble: float = 0.2           # bubbles per wear [J; common by self-report, no rate]
    p_dislodge: float = 0.004       # pull-outs ending a wear in prolonged hyperglycaemia (within Kanapka's total) [J split]
    lipo_bio: float = 1.0           # bioavailability of a lipohypertrophic site (0.75–0.8 if the person has LH)
    abs_new: float = 0.9            # absorption speed at insertion (relative)
    abs_slope: float = 0.0625       # per day, to 1.15 at day 4 [derived from Swan 2009]
    planned_days: float = 3.0


class Pump:
    def __init__(self, traits: SiteTraits, rng: np.random.Generator, family: str = "Omnipod",
                 faults: bool = True):
        self.t = traits
        self.f = PUMPS.get(family, PUMPS["Omnipod"])
        self.rng = rng
        self.faults = faults
        self.bias = float(rng.normal(0, 0.015))
        self.flow_e = 0.0
        self.queue: list = []                  # (start, end, units, bolus)
        self.delivered = 0.0
        self.commanded = 0.0
        self.missed = 0.0                      # units commanded but not delivered by the fluid path
        self.alarm = False
        self.log = []
        self._new_site(-rng.uniform(0, 2) * DAY, initial=True)

    # ------------------------------------------------------------------ site life
    def _new_site(self, start: float, initial: bool = False):
        r, t = self.rng, self.t
        self.site_start = start
        self.gap_until = -1.0 if initial else start
        self.startup = float(r.normal(*self.f.startup))
        life = t.planned_days * DAY
        draw = lambda p: start + r.uniform(0.05, 1.0) * life if (self.faults and r.random() < p) else None
        self.fail_at = draw(t.p_fail)
        self.partials = []
        if self.faults:
            for _ in range(r.poisson(t.p_partial)):
                s = start + r.uniform(0, life)
                self.partials.append((s, s + float(np.clip(np.exp(r.normal(math.log(60), 0.6)), 10, 360)),
                                      float(r.uniform(0.0, 0.5))))
        self.full_at = draw(t.p_full)
        self.dislodge_at = draw(t.p_dislodge)
        self.bubble_at = draw(t.p_bubble)
        self.bubble_left = float(np.clip(np.exp(r.normal(math.log(0.5), 0.6)), 0.1, 3.0)) if self.bubble_at else 0.0
        self.missed = 0.0
        self.release_pending = 0.0
        self.alarm = False

    def change_site(self, m: float):
        self._new_site(m + self.f.change_gap)
        self.gap_until = m + self.f.change_gap
        self.log.append((m, "site_change"))

    def command(self, start: float, end: float, units: float, bolus: bool = False):
        """A commanded dose (minutes); basal spread over [start, end), a bolus delivered in its first minute."""
        if units <= 0: return
        self.commanded += units
        self.queue.append((start, max(end, start + 1.0), units, bolus))

    def site_state(self, m: float) -> tuple[float, float]:
        """(absorption speed multiplier, absorbed fraction) of the current site."""
        age = max(0.0, (m - self.site_start) / DAY)
        absm = self.t.abs_new + self.t.abs_slope * min(age, 4.0)
        bio = self.t.lipo_bio
        if self.fail_at is not None and m > self.fail_at:
            bio *= self.t.fail_floor + (1 - self.t.fail_floor) * math.exp(-(m - self.fail_at) / self.t.fail_tau)
        if self.dislodge_at is not None and m > self.dislodge_at:
            bio = 0.0
        return absm, bio

    def failing(self, m: float) -> bool:
        """A fault the person can only discover through glucose (no alarm)."""
        return (self.fail_at is not None and m > self.fail_at) or (self.dislodge_at is not None and m > self.dislodge_at) \
            or (self.full_at is not None and m > self.full_at)

    # ------------------------------------------------------------------ fluid path
    def _path_fraction(self, m: float) -> float:
        """Fraction of the pump's output that passes the fluid path this minute."""
        if self.full_at is not None and m > self.full_at:
            return 0.0
        frac = 1.0
        for (s, e, f) in self.partials:
            if s <= m < e: frac = min(frac, f)
            elif e <= m < e + 1 and self.missed > 0:          # clearing: release part of the missed volume
                self.release_pending += min(self.missed * self.rng.uniform(0.3, 1.0), 1.2); self.missed = 0.0
        return frac

    def deliver(self, m: float):
        """(basal U, bolus U) reaching the site during minute [m, m+1)."""
        if m < self.gap_until:
            self.queue = [q for q in self.queue if q[1] > m + 1]
            return 0.0, 0.0
        r = self.rng
        u = ub = 0.0
        keep = []
        rate = 0.0
        for (s, e, units, bolus) in self.queue:
            if e <= m: continue
            lo, hi = max(s, m), min(e, m + 1)
            if hi > lo:
                part = units * (hi - lo) / (e - s)
                if bolus:
                    sd = max(0.006, self.f.bolus_c / math.sqrt(max(units, 0.05)))
                    ub += part * max(0.0, 1.0 + self.bias + r.normal(0, sd)) if self.faults else part
                else:
                    u += part; rate += units / ((e - s) / 60.0)
            if e > m + 1: keep.append((s, e, units, bolus))
        self.queue = keep
        if self.faults and u > 0:
            # AR(1) flow error, τ 45 min, 1-h sd scaled by rate; σ/0.82 makes the 60-min mean sd match
            sd1 = self.f.basal_sd_1h * max(rate, 0.05) ** self.f.rate_exp
            a = math.exp(-1 / 45.0)
            self.flow_e = a * self.flow_e + math.sqrt(1 - a * a) * r.normal(0, min(sd1 / 0.82, 0.6))
            startup = self.startup * math.exp(-max(0.0, m - self.site_start) / 240.0)
            u *= max(0.0, 1.0 + self.bias + self.flow_e + startup)
        out = u + ub
        if self.faults:
            frac = self._path_fraction(m)
            if self.bubble_at is not None and m > self.bubble_at and self.bubble_left > 0:
                take = min(out, self.bubble_left); self.bubble_left -= take
                frac = min(frac, 1 - take / out) if out > 0 else frac
            passed = out * frac
            self.missed += out - passed
            if self.release_pending > 0:
                passed += self.release_pending; self.log.append((m, "release", self.release_pending)); self.release_pending = 0.0
            if not self.alarm and self.full_at is not None and m > self.full_at and self.missed >= self.f.v_alarm:
                self.alarm = True; self.log.append((m, "occlusion_alarm", self.missed))
            scale = passed / out if out > 0 else 1.0
            u, ub = u * scale, ub * scale
        self.delivered += u + ub
        return u, ub
