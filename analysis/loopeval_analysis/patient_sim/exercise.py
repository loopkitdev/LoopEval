"""Exercise and everyday activity: insulin-independent uptake, acute and delayed sensitivity, absorption, EGP surge.

ETH / UVA-style structure (Deichmann 2023; Dalla Man 2009; evidence/02 §1.1, evidence/10), each term named:
  input     intensity I = %VO2-reserve ≈ %HR-reserve (Swain 1997) from structured sessions, everyday activity
            episodes, and a low waking-hours background; filtered Y: dY/dt = (I − Y)/τ, τ 7 min (HR dynamics,
            Dalla Man T_HR 5 / Jaloli 10)
  uptake    insulin-independent glucose uptake ex_uptake·gain·Y·G/Gb (mass action: fades as glucose falls, larger
            from a high start — Dhaliwal 2025 ΔCGM −11 / −33 / −52 from 100–150 / 150–200 / 200–250)
  acute SI  insulin action ×(1 + α·gain·Y), α 2.0 (Romeres 2021 clamp: +81–155% insulin-dependent uptake at ~0.6)
  delayed   Z: dZ/dt = b·drive(Y) − Z/τ_Z, drive above I 0.12 (UVA / Deichmann thresholds at light intensity),
            τ_Z 600 min; insulin action ×(1 + Z)
  absorb    subcutaneous absorption ×(1 + 0.5·Y) (Koivisto 1978; upper bound for abdominal sites, Pitt 2020)
  surge     catecholamine EGP pulse for the anaerobic share (BodyParams.ex_egp_surge)
`gain` is a per-person responsiveness lnN(0, 0.5) (Jaloli: ten-fold spread in 9 people).
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class ExerciseParams:
    alpha: float = 2.0          # acute SI boost per unit intensity (Romeres 2021, linearised) [I]
    b: float = 0.018            # delayed-state build per minute per unit drive [J]
    z_power: float = 1.0        # drive = ((Y − threshold)/(1 − threshold))^power. 2.0 with b 0.134 keeps everyday walking
                                # (I ~0.25) at the T1DEXI-sized build of b 0.018 linear and gives a 45-min moderate session
                                # (I ~0.5) McMahon 2007's late-phase size, ≈ +0.6 mg/kg/min at 7–11 h; muscle glycogen use,
                                # which the delayed sensitivity repletes, rises steeply with intensity (LESSONS 57)
    tau_z: float = 600.0        # min (ETH / UVA)
    absorb: float = 0.5         # absorption speed-up per unit intensity
    z_threshold: float = 0.12   # intensity above which delayed sensitivity builds (UVA / Deichmann) [I]
    filt_tau: float = 7.0       # min, intensity → physiological activity lag
    gain: float = 1.0           # per-person responsiveness (set from behavior traits)
    background: float = 0.0     # waking-hours background intensity (set from behavior traits)


class Exercise:
    def __init__(self, params: ExerciseParams | None = None):
        self.p = params or ExerciseParams()
        self.sessions: list[tuple[float, float, float, float]] = []   # start, end, intensity, anaerobic
        self.z = 0.0
        self.y = 0.0

    def add(self, start: float, minutes: float, intensity: float, anaerobic: float):
        self.sessions.append((start, start + minutes, intensity, anaerobic))

    def at(self, m: float, awake: bool = True) -> dict:
        """Advance one minute; returns the body's exercise inputs for this minute."""
        intensity = anaerobic = 0.0
        for (s, e, i, a) in self.sessions:
            if s <= m < e and i > intensity:
                intensity, anaerobic = i, a
        if awake: intensity = max(intensity, self.p.background)
        self.y += (intensity - self.y) / self.p.filt_tau
        # the delayed state follows activity above light intensity (LESSONS 23 had it at 0.35, which left everyday
        # walking without the after-effect the UVA and Deichmann models give it; LESSONS 34)
        drive = (max(0.0, self.y - self.p.z_threshold) / (1.0 - self.p.z_threshold)) ** self.p.z_power
        self.z += self.p.b * self.p.gain * drive - self.z / self.p.tau_z
        while self.sessions and self.sessions[0][1] < m - 2000:
            self.sessions.pop(0)
        return dict(ex_intensity=self.p.gain * self.y, ex_anaerobic=anaerobic,
                    ex_si_boost=self.p.alpha * self.p.gain * self.y + self.z,
                    abs_mult=1.0 + self.p.absorb * self.y)
