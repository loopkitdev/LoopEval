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

import numpy as np


@dataclass
class ExerciseParams:
    alpha: float = 2.0          # acute SI boost per unit intensity (Romeres 2021, linearised) [I]
    b: float = 0.134            # delayed-state build per minute per unit drive; default since 2026-10-19 with z_power 2
                                # (LESSONS 246: donors' HealthKit workouts pin what LESSONS 57 could not; was 0.018 linear)
    z_power: float = 2.0        # drive = ((Y − threshold)/(1 − threshold))^power. 2.0 with b 0.134 keeps everyday walking
                                # (I ~0.25) at the T1DEXI-sized build of b 0.018 linear and gives a 45-min moderate session
                                # (I ~0.5) McMahon 2007's late-phase size, ≈ +0.6 mg/kg/min at 7–11 h; muscle glycogen use,
                                # which the delayed sensitivity repletes, rises steeply with intensity (LESSONS 57)
    tau_z: float = 600.0        # min (ETH / UVA)
    absorb: float = 0.5         # absorption speed-up per unit intensity
    surge_thr: float = 0.6      # intensity above which the C4 EGP surge builds (LESSONS 247)
    z_threshold: float = 0.12   # intensity above which delayed sensitivity builds (UVA / Deichmann) [I]
    filt_tau: float = 7.0       # min, intensity → physiological activity lag
    sat_k: float = 0.0          # > 0: the acute SI boost saturates in intensity, α·(0.6 + k)·Y/(Y + k), equal to the linear α·Y at
                                # Y 0.6 (Romeres 2021's clamp point) and larger at light effort (Pemberton 2025: no intensity
                                # dependence of the 20-min drop; donors' workouts by METs < 4 / 4–6 / ≥ 6: −7 / −13 / −9; LESSONS 495)
    gain: float = 1.0           # per-person responsiveness (set from behavior traits)
    background: float = 0.0     # waking-hours background intensity (set from behavior traits)
    frag: bool = False          # the waking background as alternating sitting and short light-activity bouts with the
                                # same mean (LESSONS 161): sitting lnN(12 min, 1.0), active lnN(4 min, 0.8) [J; Healy 2008:
                                # dozens of breaks in sedentary time a day, most sedentary time in longer bouts]
    frag_seed: int = 0
    frag_off_med: float = 12.0
    frag_on_med: float = 4.0


class Exercise:
    def _acute(self) -> float:
        p = self.p
        if p.sat_k > 0:
            return p.alpha * (0.6 + p.sat_k) * p.gain * self.y / (self.y + p.sat_k)
        return p.alpha * p.gain * self.y

    def __init__(self, params: ExerciseParams | None = None):
        self.p = params or ExerciseParams()
        self.sessions: list[tuple[float, float, float, float]] = []   # start, end, intensity, anaerobic
        self.z = 0.0
        self.y = 0.0
        p = self.p
        self._rng = np.random.default_rng(p.frag_seed)
        self._on = False; self._left = 0.0
        m_off = p.frag_off_med * math.exp(1.0 ** 2 / 2); m_on = p.frag_on_med * math.exp(0.8 ** 2 / 2)
        self._on_level = p.background * (m_off + m_on) / m_on      # same waking mean as the constant background

    def add(self, start: float, minutes: float, intensity: float, anaerobic: float):
        self.sessions.append((start, start + minutes, intensity, anaerobic))

    def at(self, m: float, awake: bool = True) -> dict:
        """Advance one minute; returns the body's exercise inputs for this minute."""
        intensity = anaerobic = 0.0
        for (s, e, i, a) in self.sessions:
            if s <= m < e and i > intensity:
                intensity, anaerobic = i, a
        if awake:
            if self.p.frag and self.p.background > 0:
                if self._left <= 0:
                    self._on = not self._on
                    med, sd = (self.p.frag_on_med, 0.8) if self._on else (self.p.frag_off_med, 1.0)
                    self._left = float(np.exp(self._rng.normal(math.log(med), sd)))
                self._left -= 1.0
                intensity = max(intensity, self._on_level if self._on else 0.0)
            else:
                intensity = max(intensity, self.p.background)
        self.y += (intensity - self.y) / self.p.filt_tau
        # the delayed state follows activity above light intensity (LESSONS 23 had it at 0.35, which left everyday
        # walking without the after-effect the UVA and Deichmann models give it; LESSONS 34)
        drive = (max(0.0, self.y - self.p.z_threshold) / (1.0 - self.p.z_threshold)) ** self.p.z_power
        self.z += self.p.b * self.p.gain * drive - self.z / self.p.tau_z
        while self.sessions and self.sessions[0][1] < m - 2000:
            self.sessions.pop(0)
        # C4: the catecholamine EGP surge appears only at hard effort (above ~60% of reserve; Marliss & Vranic 2002) —
        # zero below, linear to full at 100% (LESSONS 247); the session's anaerobic share scales it
        anaerobic = anaerobic * min(1.0, max(0.0, (intensity - self.p.surge_thr) / (1.0 - self.p.surge_thr)))
        return dict(ex_intensity=self.p.gain * self.y, ex_anaerobic=anaerobic,
                    ex_si_boost=self._acute() + self.z,
                    abs_mult=1.0 + self.p.absorb * self.y)
