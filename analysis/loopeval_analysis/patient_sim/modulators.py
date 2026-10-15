"""Time-varying physiology: what multiplies insulin sensitivity, EGP and insulin absorption.

Each factor is a separate, switchable term (COMPONENTS §B). `Modulators.at(minute)` returns the
product the body uses at that minute:

    si_mult   insulin sensitivity (disposal and EGP suppression together)
    egp_mult  basal endogenous glucose production
    abs_mult  subcutaneous absorption speed (heat, exercise — exercise owns its own term)

Time is LOCAL minutes from the simulation epoch (midnight local on day 0).

Factor           form                                                      evidence
B1 circadian     Visentin 7-class B/L/D SI profile, 1 h ramps, ±noise          01 §5.1 (Visentin 2015)
B2 dawn          EGP bump from onset (02:00–04:30) peaking ~07:00, gone ~10:00  01 §5.1; 02 (Ostrovski 2020: 52%)
B3 day level     intrinsic day-to-day SI, CV 8%, independent days (repeat clamps, evidence/07);
                 intraday OU OFF (no controlled-condition evidence)
B4 slow drift    OU on log SI — OFF, same reason (weight, season, growth are to be named instead)
B5 menstrual     luteal SI dip on a 24–35 d cycle, responders only (OFF default) 02 menstrual; 05 lesson 22
B6 illness       Poisson episodes, SI dip with ramps, EGP rise                  02 illness; 00 D21a
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

DAY = 1440.0

# Visentin 2015 classes: pattern of (breakfast, lunch, dinner) high/low and probability
VISENTIN = [("hhh", 0.10), ("hhl", 0.05), ("hlh", 0.05), ("hll", 0.10),
            ("lhh", 0.20), ("lhl", 0.20), ("llh", 0.30)]
SEGMENTS = [(4 * 60, "B"), (11 * 60, "L"), (17 * 60, "D")]      # switch minutes of the local day


@dataclass
class ModTraits:
    # day / intraday / drift are UNNAMED variability: off unless a controlled-condition source sizes them
    # (Pete 2026-10-15: no mystery terms fitted to field data; free-living CVs are targets for the named
    # factors, not inputs). circ_noise likewise.
    enabled: dict = field(default_factory=lambda: dict(circadian=True, dawn=True, day=True, intraday=False,
                                                       drift=False, menstrual=False, illness=True))
    circ_class: str = "llh"
    circ_low: float = 0.4               # low segment SI as a fraction of high (Visentin: 0.40 ± 0.23)
    circ_noise: float = 0.0             # per-day noise per segment; Visentin's N(1, 0.2) was a simulation choice, not a measurement
    dawn: bool = True
    dawn_amp: float = 0.3               # fractional EGP increase at the dawn peak [J]
    dawn_onset: float = 180.0           # local minute
    day_sd: float = 0.08                # INTRINSIC day-level SI CV: repeat clamps 6–15% (evidence/07)
    day_rho: float = 0.0                # no controlled-condition evidence of persistence; the field's
                                        # lag-1-day 0.4 (ice L19) must come from named factors
    intra_sd: float = 0.12              # stationary log-SI sd within a day [J]
    intra_tau: float = 240.0            # min
    drift_sd: float = 0.08
    drift_tau: float = 20 * DAY
    cycle_len: float = 28.0             # days
    cycle_phase: float = 0.0            # days
    luteal_amp: float = 0.08            # luteal SI dip (fraction) [02: population ±2.6%, responders more]
    illness_rate: float = 3.0           # episodes per year
    seed: int = 0


def sample_mod_traits(rng: np.random.Generator, age: float, sex: str) -> ModTraits:
    cls = VISENTIN[rng.choice(len(VISENTIN), p=[p for _, p in VISENTIN])][0]
    t = ModTraits(
        circ_class=cls,
        # Visentin's low/high SI ratio (0.40 ± 0.23) is an estimate from meal tests whose noise inflates the
        # swing: at that amplitude the simulated 24-h glucose amplitude was 0.23 vs the field's 0.12
        # (ablation 2026-10-15). Half the swing [J; to be settled on circadian_amp]
        circ_low=float(np.clip(1.0 - 0.5 * (1.0 - rng.normal(0.40, 0.23)), 0.4, 1.0)),
        dawn=bool(rng.random() < 0.52),
        dawn_amp=float(np.clip(np.exp(rng.normal(math.log(0.3), 0.6)), 0.05, 1.2)),
        dawn_onset=float(rng.uniform(120, 270)),
        cycle_len=float(np.clip(rng.normal(28, 3), 21, 38)),
        cycle_phase=float(rng.uniform(0, 28)),
        luteal_amp=float(np.clip(np.exp(rng.normal(math.log(0.08), 0.5)), 0.0, 0.3)) if rng.random() < 0.63 else 0.0,
        illness_rate=5.0 if age < 13 else 3.0,
        seed=int(rng.integers(1 << 31)),
    )
    t.enabled["menstrual"] = False                      # stress scenario only (evidence/05 lesson 22)
    t.menstruating = (sex == "F" and 13 <= age <= 50)
    return t


class Modulators:
    def __init__(self, traits: ModTraits, days: int):
        self.t = traits
        r = np.random.default_rng(traits.seed)
        self.days = days + 2
        # B1 circadian: segment levels per day, normalised so the day-average SI is 1
        hi_lo = {c: (1.0 if c == "h" else traits.circ_low) for c in "hl"}
        base = np.array([hi_lo[c] for c in traits.circ_class])
        hours = np.array([7.0, 6.0, 11.0])              # B 04–11, L 11–17, D 17–04
        base = base / (base @ hours / 24.0)
        self.circ = base[None, :] * np.exp(r.normal(0, traits.circ_noise, (self.days, 3)) - traits.circ_noise ** 2 / 2)
        # B3 day level: AR(1) on log SI
        z = np.zeros(self.days)
        for d in range(1, self.days):
            z[d] = traits.day_rho * z[d - 1] + math.sqrt(1 - traits.day_rho ** 2) * r.normal(0, traits.day_sd)
        z[0] = r.normal(0, traits.day_sd)
        self.day = z
        # B6 illness episodes
        self.ill = []
        n = r.poisson(traits.illness_rate * self.days / 365.0)
        for _ in range(n):
            start = r.uniform(0, self.days) * DAY
            dur = float(np.clip(np.exp(r.normal(math.log(4.0), 0.5)), 1.5, 15)) * DAY
            gi = r.random() < 0.2
            self.ill.append(dict(start=start, dur=dur, gi=gi,
                                 si_drop=float(r.uniform(-0.15, -0.05) if gi else r.uniform(0.1, 0.35)),
                                 egp=0.0 if gi else float(r.uniform(0.0, 0.15))))
        # B3 intraday OU and B4 drift, advanced minute by minute
        self.rng = r
        self.ou = r.normal(0, traits.intra_sd)
        self.drift = r.normal(0, traits.drift_sd)
        self.last = None

    # ---------------------------------------------------------------- pieces
    def circadian(self, m: float) -> float:
        d = int(m // DAY); mm = m % DAY
        # segment index with 1 h linear ramps around the switch times
        def seg_val(day, k): return self.circ[max(0, min(day, self.days - 1)), k]
        pts = []
        for day_off in (-1, 0, 1):
            for k, (sw, _) in enumerate(SEGMENTS):
                pts.append((day_off * DAY + sw, seg_val(d + day_off, k)))
        pts.sort()
        prev_v = pts[0][1]
        for (sw, v) in pts:
            if mm < sw - 30: return prev_v
            if mm < sw + 30: return prev_v + (v - prev_v) * (mm - (sw - 30)) / 60.0
            prev_v = v
        return prev_v

    def dawn(self, m: float) -> float:
        if not self.t.dawn: return 0.0
        mm = m % DAY
        on, peak, off = self.t.dawn_onset, 7 * 60.0, 10 * 60.0
        if mm < on or mm > off: return 0.0
        if mm < peak: return self.t.dawn_amp * (mm - on) / max(peak - on, 1)
        return self.t.dawn_amp * (off - mm) / (off - peak)

    def illness(self, m: float):
        si, egp, gi = 1.0, 1.0, False
        for e in self.ill:
            x = m - e["start"]
            if 0 <= x < e["dur"]:
                ramp = min(1.0, x / 720.0, (e["dur"] - x) / (0.3 * e["dur"]))
                si *= 1.0 - e["si_drop"] * ramp
                egp *= 1.0 + e["egp"] * ramp
                gi = gi or e["gi"]
        return si, egp, gi

    def menstrual(self, m: float) -> float:
        if not (self.t.enabled["menstrual"] and getattr(self.t, "menstruating", False)): return 1.0
        day = (m / DAY + self.t.cycle_phase) % self.t.cycle_len
        ov = self.t.cycle_len - 14.0                    # ovulation; luteal phase ~14 d
        if day < ov: return 1.0
        x = (day - ov) / 14.0                           # rises after ovulation, peaks mid-luteal, resolves at menses
        return 1.0 - self.t.luteal_amp * math.sin(math.pi * x)

    # ---------------------------------------------------------------- per minute
    def at(self, m: float) -> tuple[float, float, float]:
        en = self.t.enabled
        # minute-step OU updates (called once per minute, in order)
        if self.last is None or m > self.last:
            dt = 1.0 if self.last is None else m - self.last
            a = math.exp(-dt / self.t.intra_tau)
            self.ou = a * self.ou + math.sqrt(1 - a * a) * self.rng.normal(0, self.t.intra_sd)
            b = math.exp(-dt / self.t.drift_tau)
            self.drift = b * self.drift + math.sqrt(1 - b * b) * self.rng.normal(0, self.t.drift_sd)
            self.last = m
        log_si = 0.0
        if en["day"]:
            x = (m - 4 * 60) / DAY
            d = int(math.floor(x)); into = (x - d) * DAY
            cur = self.day[max(0, min(d, self.days - 1))]; prev = self.day[max(0, min(d - 1, self.days - 1))]
            log_si += cur if into >= 180 else prev + (cur - prev) * into / 180.0
        if en["intraday"]: log_si += self.ou
        if en["drift"]: log_si += self.drift
        si = math.exp(log_si)
        if en["circadian"]: si *= self.circadian(m)
        si *= self.menstrual(m)
        egp = 1.0 + (self.dawn(m) if en["dawn"] else 0.0)
        if en["illness"]:
            s_ill, e_ill, _ = self.illness(m)
            si *= s_ill; egp *= e_ill
        return si, egp, 1.0
