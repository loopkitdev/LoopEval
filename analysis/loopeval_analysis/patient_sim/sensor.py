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
    # G6 / G7 from the PILOT donors the simulated people are compared with (162 donors; their long gaps run at about
    # half the eda cohort's; wear 0.977 vs the eda-rate simulation's 0.960; LESSONS 45). Libre 3: eda cohort (6 pilot
    # donors only)
    "Dexcom G6": [1.495, 0.197, 0.071, 0.113, 0.062, 0.030, 0.024, 0.007, 0.075, 0.018, 0.008, 0.003],
    "Dexcom G7": [2.737, 0.686, 0.248, 0.211, 0.115, 0.039, 0.033, 0.012, 0.011, 0.011, 0.008, 0.003],
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
    hetero_a: float = 1.0         # noise scale = a + (1 − a)·IG/130 (1 = constant absolute noise)
    hetero_q: float = 0.0         # if > 0, quadrature form instead: scale = √(q² + (1 − q²)·(IG/130)²), an additive floor
                                  # ⊕ a proportional part (evidence/08 §A: FDA total-error elasticity ~0.7)
    df: float = 0.0               # Student-t degrees of freedom of the noise innovations (0 = Gaussian). CGM error
                                  # is heavy-tailed (Breton & Kovatchev 2008: Johnson S_U); variance preserved
    early_fail: float = 0.05      # P(session ends early) [J; Eichenlaub 2025 small n: 0–18%]
    slow_bias: tuple = (0.0, 180.0)  # (sd mg/dL at 130, τ min): a sensor bias that wanders over hours (OU), scaled with the
                                  # noise floor ⊕ proportional form. Breton & Kovatchev 2008: sensor error autocorrelated
                                  # "up to several hours" (evidence/08 §1.2) [J size, within the FDA error budget]
    noise_wander: tuple = (0.0, 240.0)  # within-sensor noise level wanders: σ × exp(z), z OU (sd, τ min). SNR varies over
                                  # time within a sensor (Facchinetti 2011; evidence/08 §B) — the noise's own volatility
                                  # clustering, which stationary noise wipes out of the CGM (LESSONS 42) [J size]
    trans_rate: tuple = (0.0, 0.9)  # transient sensor biases: events/day per session (median, log-sd between sessions).
                                  # A bias of either sign appears within one reading and recovers first-order — the
                                  # quiet-window REVERSALS donors show (±~15 mg/dL undone in 10–15 min, any glucose,
                                  # day and night; quiet.reversal_events, LESSONS 32). Physiology cannot move that fast.
    trans_amp: tuple = (10.0, 0.4)  # mg/dL amplitude (median, log-sd)
    trans_tau: float = 10.0       # min, recovery time constant
    trans_down: float = 0.55      # share of events that read low first
    common_sigma: float = 0.0     # innovation sd of the error COMMON to co-located sensors (interstitial physiology):
                                  # AR(3) (1.584, −0.8842, 0.1798), var(w) 3.98 → σ 2.0 on Enlite (Biagi 2017).
                                  # Continues across sessions; YSI comparison sees it, two-sensor precision does not


FAMILIES = {
    # G6 with the G7 structure (sensor_fit.py vs DEN170088 CGM-binned bias/MARD and PARD 9.0%): loss 7.4 against 6.7 for
    # the Vettoretti 2019 values, and it carries the transients G6 donors show (reversals 5.7 per 1,000 quiet steps)
    "Dexcom G6": Family("Dexcom G6", warmup=120, session_days=10, df=4.0, sigma=(2.5, 0.8), hetero_q=0.5,
                        a0=(0.96, 0.05), b0=(2.0, 3.0), common_sigma=2.5, trans_rate=(6.0, 0.9), trans_amp=(12.0, 0.4),
                        noise_wander=(0.7, 480.0)),
    # G7 innovations near-Gaussian (df 30): with the noise level wandering and transient biases, df 4 double-counted
    # the tails (step kurtosis 3.1 vs donors 2.48; FDA loss 1.5 → 0.7; LESSONS 42).
    # G7 fitted to sensor-only targets, never to donor roughness (LESSONS 31; sensor_fit.py, evidence/08): FDA K213919
    # adult accuracy by range (bias 4.0/1.1/1.1/−1.9/−6.6, MARD 14/10.7/8.6/7.4/6.4 from <54 to >250) and two-sensor
    # precision PARD 8.9%. Fit: bias 3.8/2.7/1.2/−1.5/−6.8, MARD 13.7/10.9/7.9/6.9/6.8, PARD 8.9, MAD elasticity
    # 0.66 (FDA 0.69). Sensor-specific innovation σ 2.5 with a floor ⊕ proportional scale (q 0.5); calibration gain
    # N(0.98, 0.04) and offset N(3, 3) mg/dL; the error common to co-located sensors (interstitial; Biagi 2017 AR(3),
    # σ 2.0) carries the rest of the accuracy error. The G6 Vettoretti values (σ 3.19, a0 0.95 ± 0.063, b0 6.35 ± 6)
    # gave G7 MARD 17% at 54–69 and PARD 14%.
    "Dexcom G7": Family("Dexcom G7", warmup=27, session_days=10, grace_days=0.5, tau_med=3.5,
                        brand_gain=1.0, sigma=(2.8, 0.8), df=30.0, hetero_q=0.5, a0=(0.98, 0.04), b0=(3.0, 3.0),
                        common_sigma=2.0, trans_rate=(8.0, 0.9), trans_amp=(8.0, 0.4), noise_wander=(0.2, 480.0),
                        slow_bias=(5.0, 180.0)),   # refit on the c235 bodies against K213919 (LESSONS 211): slow bias sd 5 (Breton &
                                                   # Kovatchev 2008), transient amplitude 12 -> 8, noise wander 0.6 -> 0.2; loss 10.9 -> 4.0
    # Libre 3 fitted to K212132 (bias 7.4/1.4/−4.5/−7.3/−11.5, MARD 15.5/10.3/9.7/7.5/6.9, PARD 6.8): MARD 11/10/8/7.6/7.5,
    # PARD 6.8; it reads too little high at true < 54 (+0.4 vs +7.4) [open]
    "Libre 3":   Family("Libre 3", warmup=60, session_days=14, tau_med=1.8, brand_gain=1.0, smooth=0.35, df=4.0,
                        sigma=(1.5, 0.5), hetero_q=0.5, a0=(0.965, 0.03), b0=(0.0, 2.0), common_sigma=3.0,
                        trans_rate=(4.0, 0.9), trans_amp=(12.0, 0.4), noise_wander=(0.7, 480.0),
                        slow_bias=(5.0, 180.0)),   # K212132 loss 20.2 -> 14.7 on the c235 bodies (LESSONS 211)
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
    trans_rate: float = 0.0       # events/day for this session


class Sensor:
    """Advance with `step(minute, bg)` every minute; it returns a reading on reporting minutes
    (float mg/dL, or None when the sensor withholds), and nothing (False) between them."""

    def __init__(self, family: str, rng: np.random.Generator, compression_rate: float = 0.03,
                 start_minute: float = 0.0, phase: float = 0.0, overrides: dict | None = None,
                 common_rng: np.random.Generator | None = None, gap_mult: tuple | None = None):
        self.f = _family(family)
        if overrides:       # calibration grid: sensor_sigma (mean noise sd), sensor_a1, sensor_a2
            from dataclasses import replace as _r
            kw = {}
            if "sensor_sigma" in overrides: kw["sigma"] = (overrides["sensor_sigma"], self.f.sigma[1])
            if "sensor_df" in overrides: kw["df"] = overrides["sensor_df"]
            if "sensor_hetero" in overrides: kw["hetero_a"] = overrides["sensor_hetero"]
            if "sensor_hq" in overrides: kw["hetero_q"] = overrides["sensor_hq"]
            if "sensor_a0" in overrides or "sensor_a0sd" in overrides:
                kw["a0"] = (overrides.get("sensor_a0", self.f.a0[0]), overrides.get("sensor_a0sd", self.f.a0[1]))
            if "sensor_b0" in overrides or "sensor_b0sd" in overrides:
                kw["b0"] = (overrides.get("sensor_b0", self.f.b0[0]), overrides.get("sensor_b0sd", self.f.b0[1]))
            if "sensor_d1" in overrides: kw["day1"] = (overrides["sensor_d1"], self.f.day1[1])
            if "sensor_common" in overrides: kw["common_sigma"] = overrides["sensor_common"]
            if "sensor_trate" in overrides or "sensor_tratesd" in overrides:
                kw["trans_rate"] = (overrides.get("sensor_trate", self.f.trans_rate[0]), overrides.get("sensor_tratesd", self.f.trans_rate[1]))
            if "sensor_tamp" in overrides or "sensor_tampsd" in overrides:
                kw["trans_amp"] = (overrides.get("sensor_tamp", self.f.trans_amp[0]), overrides.get("sensor_tampsd", self.f.trans_amp[1]))
            if "sensor_ttau" in overrides: kw["trans_tau"] = overrides["sensor_ttau"]
            if "sensor_sbias" in overrides or "sensor_sbtau" in overrides:
                kw["slow_bias"] = (overrides.get("sensor_sbias", self.f.slow_bias[0]), overrides.get("sensor_sbtau", self.f.slow_bias[1]))
            if "sensor_wander" in overrides or "sensor_wtau" in overrides:
                kw["noise_wander"] = (overrides.get("sensor_wander", self.f.noise_wander[0]), overrides.get("sensor_wtau", self.f.noise_wander[1]))
            if "sensor_drift" in overrides: kw["drift_sd"] = overrides["sensor_drift"]
            if "sensor_smooth" in overrides: kw["smooth"] = overrides["sensor_smooth"]
            if "sensor_a1" in overrides or "sensor_a2" in overrides:
                kw["ar"] = (overrides.get("sensor_a1", self.f.ar[0]), overrides.get("sensor_a2", self.f.ar[1]))
            if kw: self.f = _r(self.f, **kw)
        self.rng = rng
        self.compression_rate = compression_rate          # events per asleep-day
        self.ig: Optional[float] = None
        self.v1 = self.v2 = 0.0
        self.c_rng = common_rng if common_rng is not None else np.random.default_rng(int(rng.integers(1 << 31)))
        self.c = [0.0, 0.0, 0.0]
        self.trans = 0.0                                    # current transient bias, mg/dL
        self.wz = 0.0                                       # log noise-level wander (OU)
        self.sb = 0.0                                       # slow bias (OU), mg/dL at 130
        self.out_prev: Optional[float] = None
        self.gap_until = -1.0
        self.comp: Optional[dict] = None
        self.comp_level = 0.0
        self.next_report = start_minute + phase
        self.session = self._new_session(start_minute - rng.uniform(0, self.f.session_days) * 1440, warm=False)
        # per-reading gap start probability from the measured rates, warm-ups excluded
        rates = np.array(MEASURED_GAPS.get(self.f.name, MEASURED_GAPS["Dexcom G7"]), dtype=float)
        if gap_mult is not None:     # the donor's own gap rates against the family's: short (7–32 min), long (32 min–12 h)
            rates[:4] *= gap_mult[0]; rates[4:] *= gap_mult[1]
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
                    d1=r.normal(*f.day1), sigma=max(0.5, r.normal(*f.sigma)),
                    trans_rate=float(f.trans_rate[0] * np.exp(r.normal(0, f.trans_rate[1]))) if f.trans_rate[0] > 0 else 0.0)
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
        if self.trans != 0.0:
            self.trans *= math.exp(-1.0 / f.trans_tau)
            if abs(self.trans) < 0.05: self.trans = 0.0
        if self.session.trans_rate > 0 and self.rng.random() < self.session.trans_rate / 1440.0:
            a = float(f.trans_amp[0] * np.exp(self.rng.normal(0, f.trans_amp[1])))
            self.trans += -a if self.rng.random() < f.trans_down else a
        if minute >= self.session.end:
            self.session = self._new_session(minute)
        if minute < self.next_report:
            return False
        self.next_report += f.cadence
        # noise on the reporting grid
        s = self.session
        wsd, wtau = f.noise_wander
        if wsd > 0:
            a = math.exp(-f.cadence / wtau)
            self.wz = a * self.wz + math.sqrt(1 - a * a) * float(self.rng.normal(0.0, wsd))
        nu = math.exp(self.wz - wsd ** 2) if wsd > 0 else 1.0      # E[ν²] = 1: the noise variance is unchanged on average
        sbsd, sbtau = f.slow_bias
        if sbsd > 0:
            a2 = math.exp(-f.cadence / sbtau)
            self.sb = a2 * self.sb + math.sqrt(1 - a2 * a2) * float(self.rng.normal(0.0, sbsd))
        if f.df > 2:
            w = nu * s.sigma * float(self.rng.standard_t(f.df)) * math.sqrt((f.df - 2) / f.df)
        else:
            w = nu * self.rng.normal(0.0, s.sigma)
        v = f.ar[0] * self.v1 + f.ar[1] * self.v2 + w
        if f.common_sigma > 0:
            c = 1.584 * self.c[0] - 0.8842 * self.c[1] + 0.1798 * self.c[2] + nu * self.c_rng.normal(0.0, f.common_sigma)
            self.c = [c, self.c[0], self.c[1]]
            v_all = v + c
        else:
            v_all = v
        self.v2, self.v1 = self.v1, v
        # random gaps (per-reading start probability by length bin)
        if minute >= self.gap_until:
            p = self.gap_rate * f.cadence / 1440.0
            hit = self.rng.random(len(p)) < p
            if hit.any():
                b = int(np.argmax(hit))
                lo, hi = GAP_EDGES[b], GAP_EDGES[b + 1]
                # a gap of interval L between readings withholds round(L/cadence) − 1 readings, this one included; the
                # unrounded L − cadence withheld two readings in 37% of the 7–12-min bin (LESSONS 74)
                k = max(1, int(round(self.rng.uniform(lo, hi) / f.cadence)) - 1)
                self.gap_until = minute + (k - 1) * f.cadence + 0.5
        # noise grows with glucose: G7 absolute error 8.5 mg/dL at 40–60, ~11.6 near 130 (MARD 8.9%), ~17 near
        # 240 (MARD 7.2%) (Garg 2022 tables, evidence/03 §2.3) → scale 0.6 + 0.4·IG/130 (LESSONS 29)
        if f.hetero_q > 0:
            x = max(self.ig, 20.0) / 130.0
            hs = math.sqrt(f.hetero_q ** 2 + (1 - f.hetero_q ** 2) * x * x)
        else:
            hs = (f.hetero_a + (1 - f.hetero_a) * max(self.ig, 20.0) / 130.0) if f.hetero_a < 1 else 1.0
        raw = self.gain(minute) * self.ig + s.b0 + (v_all + self.sb) * hs + self.trans - self.comp_level
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
