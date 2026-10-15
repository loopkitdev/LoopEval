"""Exercise: acute insulin-independent uptake, acute and delayed sensitivity, absorption, EGP surge.

ETH-style structure (Deichmann 2023; evidence/02 §1.1), each term separately named:
  uptake    insulin-independent glucose uptake ∝ intensity (BodyParams.ex_uptake, mg/kg/min at I = 1)
  acute SI  insulin action ×(1 + α·I) while active
  delayed   Z: dZ/dt = b·I during exercise, Z decays with τ_Z ≈ 600 min; insulin action ×(1 + Z)
            (glucose requirement raised up to ~11 h; overnight hypo 48% vs 28% of nights — evidence/02)
  absorb    subcutaneous absorption ×(1 + c·I) while active (raised skin/muscle blood flow)
  surge     catecholamine EGP pulse for the anaerobic share (BodyParams.ex_egp_surge)
Magnitudes are [J] priors; the calibration targets are T1DEXI's per-session drop by starting glucose
and by IOB (+4 below 100, −61 at 250–300; +5 at IOB < 1 U, −30 at ≥ 3 U) and the delayed-hypo rate.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExerciseParams:
    alpha: float = 0.8          # acute SI boost per unit intensity [J; Breton α 0.974 on a filtered HR state]
    b: float = 0.018            # delayed-state build per minute per unit intensity [J]
    tau_z: float = 600.0        # min (ETH model)
    absorb: float = 0.5         # absorption speed-up per unit intensity [J]


class Exercise:
    def __init__(self, params: ExerciseParams | None = None):
        self.p = params or ExerciseParams()
        self.sessions: list[tuple[float, float, float, float]] = []   # start, end, intensity, anaerobic
        self.z = 0.0

    def add(self, start: float, minutes: float, intensity: float, anaerobic: float):
        self.sessions.append((start, start + minutes, intensity, anaerobic))

    def at(self, m: float) -> dict:
        """Advance one minute; returns the body's exercise inputs for this minute."""
        intensity = anaerobic = 0.0
        for (s, e, i, a) in self.sessions:
            if s <= m < e:
                intensity, anaerobic = i, a
        self.z += self.p.b * intensity - self.z / self.p.tau_z
        if self.sessions and self.sessions[0][1] < m - 2000:
            self.sessions.pop(0)
        return dict(ex_intensity=intensity, ex_anaerobic=anaerobic,
                    ex_si_boost=self.p.alpha * intensity + self.z,
                    abs_mult=1.0 + self.p.absorb * intensity)
