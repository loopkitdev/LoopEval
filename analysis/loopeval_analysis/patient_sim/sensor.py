"""CGM: what the person's sensor reports, given true blood glucose.

Per family, one parameter set per SESSION (evidence/03 §2.1, Vettoretti 2019 structure):

    IG     dIG/dt = (BG − IG)/τ                        first-order blood→interstitium + device net lag
    raw    a(t)·IG + b0 + v(t) − compression(t)          a(t) = brand_gain·(a0 + a1·d + a2·d²)·day1(t)
    v      AR(2) on the reporting grid (α1, α2, σ)
    out    device smoothing (EMA, twiist Libre stream), integer mg/dL, clamped to 39 / 401, or None

Availability: warm-up after every session start; session length (+ optional grace); early
failure; random gaps drawn at the measured per-family rates (runs/2026-10-15-additive-sensor/gaps.py,
eda cohort, 153 donors), less the explicit warm-ups.

Compression lows (evidence/05 §1d; evidence/03 §2.6): a person-level rate, only while asleep,
first-order response to a rectangular pressure pulse (Facchinetti 2016 shape); 72% of events
withhold readings (gap), 25% are a dip, 3% pin the 40 floor.

Every parameter value cites its source in FAMILIES; [J] marks a judgement awaiting calibration
against the eda per-family statistics (lesson 33: step SD, increment lag-1, flat-step share,
implied noise, kurtosis).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

# measured gap rates per day by gap length bin (minutes), eda cohort (gaps.py, 2026-10-15)
GAP_EDGES = [7, 12, 17, 22, 32, 47, 62, 92, 122, 182, 362, 722, 1440]
MEASURED_GAPS = {
    "Dexcom G6": [1.037, 0.121, 0.085, 0.158, 0.108, 0.039, 0.040, 0.013, 0.077, 0.027, 0.013, 0.009],
    "Dexcom G7": [2.861, 0.797, 0.259, 0.222, 0.118, 0.052, 0.055, 0.021, 0.019, 0.021, 0.014, 0.010],
    "Libre 3":   [0.695, 0.398, 0.084, 0.087, 0.074, 0.031, 0.064, 0.018, 0.011, 0.012, 0.009, 0.013],
}


@dataclass(frozen=True)
class Family:
    name: str
    cadence: float = 5.0          # min between reported readings
    warmup: float = 30.0          # min
    session_days: float = 10.0
    grace_days: float = 0.0
    tau_med: float = 3.78         # min (Vettoretti 2019, G6); device net lag
    tau_logsd: float = 0.68
    a0: tuple = (0.95, 0.063)     # mean, sd (Vettoretti 2019)
    drift_sd: float = 0.04        # sd of the gain's change over a session, sampled jointly [J; bounded by per-day MARD]
    b0: tuple = (6.35, 6.0)       # mg/dL (Vettoretti 2019)
    brand_gain: float = 1.0       # same-person bias vs YSI (Eichenlaub 2025)
    day1: tuple = (0.06, 0.05)    # first-day gain deficit mean, sd, decaying with τ 12 h [J; G7 first-12 h bias −7.8%]
    ar: tuple = (1.30, -0.42)     # AR(2) on the reporting grid (Vettoretti 2019)
    sigma: tuple = (3.19, 1.0)    # mg/dL
    smooth: float = 0.0           # EMA weight on the PREVIOUS output (0 = none) [J; fit to eda L33 lag-1]
    early_fail: float = 0.05      # P(session ends early) [J; Eichenlaub 2025 small n: 0–18%]


FAMILIES = {
    "Dexcom G6": Family("Dexcom G6", warmup=120, session_days=10),
    # G7 is rougher than G6 in the same people (eda L33: switchers' step SD +0.87, white noise unchanged), so its
    # correlated noise is larger: σ 4.0 matches pilot G7 donors' quiet-window step SD (5.5), whole-record step
    # SD (7.0) and implied white noise (1.39); the Vettoretti AR(2) shape is kept — a less oscillatory shape
    # destroyed the short-lag persistence donors show (grid runs/2026-10-15-additive-sg_*, LESSONS 24)
    "Dexcom G7": Family("Dexcom G7", warmup=27, session_days=10, grace_days=0.5, tau_med=3.5,
                        brand_gain=1.0, sigma=(4.0, 1.0)),
    "Libre 3":   Family("Libre 3", warmup=60, session_days=14, tau_med=1.8, brand_gain=1.0, smooth=0.35),
    "Libre 2":   Family("Libre 2", warmup=60, session_days=14, tau_med=2.4),
    "Medtronic": Family("Medtronic", warmup=120, session_days=7, tau_med=8.4, a0=(1.0, 0.1),
                        ar=(1.367, -0.4816), sigma=(1.59, 0.5), brand_gain=0.94),
}
# Brand gains: Eichenlaub 2025 found G7 / Libre 3 +7–8% and Simplera −6% vs YSI, but within 1–3% of
# capillary blood. The simulator's truth is blood glucose, so Dexcom / Libre stay at 1.0 [J];
# Medtronic keeps its relative −6%.


def _family(name: str) -> Family:
    n = name.strip()
    if n in FAMILIES: return FAMILIES[n]
    if "libre" in n.lower() or "abbott" in n.lower(): return FAMILIES["Libre 3"]
    if "g6" in n.lower(): return FAMILIES["Dexcom G6"]
    return FAMILIES["Dexcom G7"]


@dataclass
class Session:
    start: float                  # minute
    end: float
    tau: float
    a0: float
    slope: float                  # gain change per day (linear part)
    curve: float                  # quadratic part
    b0: float
    d1: float
    sigma: float


class Sensor:
    """Advance with `step(minute, bg)` every minute; it returns a reading on reporting minutes
    (float mg/dL, or None when the sensor withholds), and nothing (False) between them."""

    def __init__(self, family: str, rng: np.random.Generator, compression_rate: float = 0.03,
                 start_minute: float = 0.0, phase: float = 0.0, overrides: dict | None = None):
        self.f = _family(family)
        if overrides:       # calibration grid: sensor_sigma (mean noise sd), sensor_a1, sensor_a2
            from dataclasses import replace as _r
            kw = {}
            if "sensor_sigma" in overrides: kw["sigma"] = (overrides["sensor_sigma"], self.f.sigma[1])
            if "sensor_a1" in overrides or "sensor_a2" in overrides:
                kw["ar"] = (overrides.get("sensor_a1", self.f.ar[0]), overrides.get("sensor_a2", self.f.ar[1]))
            if kw: self.f = _r(self.f, **kw)
        self.rng = rng
        self.compression_rate = compression_rate          # events per asleep-day
        self.ig: Optional[float] = None
        self.v1 = self.v2 = 0.0
        self.out_prev: Optional[float] = None
        self.gap_until = -1.0
        self.comp: Optional[dict] = None
        self.comp_level = 0.0
        self.next_report = start_minute + phase
        self.session = self._new_session(start_minute - rng.uniform(0, self.f.session_days) * 1440, warm=False)
        # per-reading gap start probability from the measured rates, warm-ups excluded
        rates = np.array(MEASURED_GAPS.get(self.f.name, MEASURED_GAPS["Dexcom G7"]), dtype=float)
        wb = np.searchsorted(GAP_EDGES, self.f.warmup + self.f.cadence) - 1
        if 0 <= wb < len(rates):
            rates[wb] = max(0.0, rates[wb] - 1.0 / (self.f.session_days + self.f.grace_days))
        self.gap_rate = rates                               # per day, by bin
        self.log = []                                       # (minute, true bg, reading or None, compression)

    # ------------------------------------------------------------------ sessions
    def _new_session(self, start: float, warm: bool = True) -> Session:
        f, r = self.f, self.rng
        length = (f.session_days + (f.grace_days * r.random())) * 1440
        if r.random() < f.early_fail:
            length *= r.uniform(0.1, 0.9)
        # gain drift: a smooth change of total size ~ drift_sd over the session (joint sampling,
        # evidence/03 warning against independent a1, a2 draws)
        total = r.normal(0, f.drift_sd)
        bend = r.normal(0, 0.5)
        days = f.session_days
        curve = bend * total / days ** 2
        slope = (total - curve * days ** 2) / days
        s = Session(start=start, end=start + length,
                    tau=float(np.exp(math.log(f.tau_med) + r.normal(0, f.tau_logsd))),
                    a0=r.normal(*f.a0), slope=slope, curve=curve, b0=r.normal(*f.b0),
                    d1=r.normal(*f.day1), sigma=max(0.5, r.normal(*f.sigma)))
        if warm:
            self.gap_until = max(self.gap_until, start + f.warmup)
        return s

    def gain(self, minute: float) -> float:
        s = self.session
        d = (minute - s.start) / 1440.0
        return self.f.brand_gain * (s.a0 + s.slope * d + s.curve * d * d) \
            * (1.0 - s.d1 * math.exp(-max(0.0, minute - s.start) / 720.0))

    # ------------------------------------------------------------------ compression
    def _maybe_compress(self, minute: float, asleep: bool):
        if self.comp is None and asleep and self.rng.random() < self.compression_rate / (8 * 60):
            r = self.rng
            u = r.random()
            self.comp = dict(start=minute, dur=float(np.clip(np.exp(r.normal(math.log(45), 0.3)), 15, 120)),
                             depth=float(np.clip(np.exp(r.normal(math.log(35), 0.4)), 10, 120)),
                             kind="gap" if u < 0.72 else "dip" if u < 0.97 else "floor", tau=8.0)
        c = self.comp
        if c is None:
            self.comp_level += (0.0 - self.comp_level) / 8.0
            return
        on = minute - c["start"] < c["dur"]
        target = c["depth"] if on else 0.0
        self.comp_level += (target - self.comp_level) / c["tau"]
        if not on and self.comp_level < 1.0:
            self.comp = None

    # ------------------------------------------------------------------ step
    def step(self, minute: float, bg: float, asleep: bool = False):
        f = self.f
        if self.ig is None: self.ig = bg
        self.ig += (bg - self.ig) / max(self.session.tau, 1.0)    # dt = 1 min
        self._maybe_compress(minute, asleep)
        if minute >= self.session.end:
            self.session = self._new_session(minute)
        if minute < self.next_report:
            return False
        self.next_report += f.cadence
        # noise on the reporting grid
        s = self.session
        w = self.rng.normal(0.0, s.sigma)
        v = f.ar[0] * self.v1 + f.ar[1] * self.v2 + w
        self.v2, self.v1 = self.v1, v
        # random gaps (per-reading start probability by length bin)
        if minute >= self.gap_until:
            p = self.gap_rate * f.cadence / 1440.0
            hit = self.rng.random(len(p)) < p
            if hit.any():
                b = int(np.argmax(hit))
                lo, hi = GAP_EDGES[b], GAP_EDGES[b + 1]
                self.gap_until = minute + self.rng.uniform(lo, hi) - f.cadence
        raw = self.gain(minute) * self.ig + s.b0 + v - self.comp_level
        c = self.comp
        withheld = minute < self.gap_until or (c is not None and c["kind"] == "gap" and self.comp_level > 0.5 * c["depth"])
        if c is not None and c["kind"] == "floor" and self.comp_level > 0.5 * c["depth"]:
            raw = 39.0
        if f.smooth > 0 and self.out_prev is not None and not withheld:
            raw = f.smooth * self.out_prev + (1 - f.smooth) * raw
        reading = None if withheld else float(min(401.0, max(39.0, round(raw))))
        if reading is not None: self.out_prev = raw
        self.log.append((minute, bg, reading, self.comp_level))
        return reading
