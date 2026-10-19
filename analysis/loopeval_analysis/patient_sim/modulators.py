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
B5 menstrual     SI low at menses onset (BDDP-log "late" shape), 21–38 d cycle, responders only (ON default; LESSONS 136, 235)
B6 illness       Poisson episodes, SI dip with ramps, EGP rise                  02 illness; 00 D21a
B14 steroids     oral glucocorticoid courses: morning dose, SI loss from 2 h, full 6–12 h, gone by 22 h; taper over the course
                 (Bevier 2008: insulin +69%, 30–100%, from 6 h after the first dose, baseline by day 4; Waljee 2017: 21.1%
                 of US adults with a short course in 3 years, half a 6-day dose pack) 00 D13
X9 pregnancy     scenario only: insulin need by gestational week, up to week 9, down to a week-16 nadir, +5%/week to
                 week 36, falling after 37 (García-Patterson 2010; ADA Standards 2023 §15) 00 X9
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

DAY = 1440.0

# Visentin 2015 classes: pattern of (breakfast, lunch, dinner) high/low and probability
VISENTIN = [("hhh", 0.10), ("hhl", 0.05), ("hlh", 0.05), ("hll", 0.10),
            ("lhh", 0.20), ("lhl", 0.20), ("llh", 0.30)]
# switch minutes of the local day. Visentin's levels are meal-test SI (breakfast ~07 h), so the breakfast level starts at
# breakfast, not at 04:00: with a 04:00 switch, 70% of people (low breakfast SI) needed 50–80% more insulin from 05:00 on
# quiet mornings, against donors' 0.92 (LESSONS 51) [J boundary]
SEGMENTS = [(7 * 60, "B"), (11 * 60, "L"), (17 * 60, "D")]


@dataclass
class ModTraits:
    # day / intraday / drift are UNNAMED variability: off unless a controlled-condition source sizes them
    # (Pete 2026-10-15: no mystery terms fitted to field data; free-living CVs are targets for the named
    # factors, not inputs). circ_noise likewise.
    enabled: dict = field(default_factory=lambda: dict(circadian=True, dawn=True, day=True, intraday=False,
                                                       drift=False, menstrual=True, illness=True, sleep=True,
                                                       gh=True, alcohol=True, stress=True, caffeine=False,
                                                       steroid=True, heat=False))
    circ_class: str = "llh"
    circ_low: float = 0.4               # low segment SI as a fraction of high (Visentin: 0.40 ± 0.23)
    circ_raw: float = 0.4               # the person's Visentin draw before the swing scale
    circ_swing: float = 1.0             # share of Visentin's measured swing: full (LESSONS 38; the halving of LESSONS 10 compensated for fixed-rate emptying)
    circ_noise: float = 0.0             # per-day noise per segment; Visentin's N(1, 0.2) was a simulation choice, not a measurement
    dawn: bool = True
    dawn_amp: float = 0.3               # fractional EGP increase at the dawn peak [J]
    dawn_onset: float = 180.0           # local minute
    day_sd: float = 0.08                # INTRINSIC day-level SI CV: repeat clamps 6–15% (evidence/07)
    day_tau: float = 0.0                # min; > 0 = the same intrinsic SI variance (sd day_sd) as a continuous OU with this
                                        # timescale instead of a step per day — repeat clamps size the variance, not
                                        # its shape in time (LESSONS 49) [J τ]
    day_rho: float = 0.0                # no controlled-condition evidence of persistence; the field's
                                        # lag-1-day 0.4 (ice L19) must come from named factors
    intra_sd: float = 0.12              # stationary log-SI sd within a day [J]
    intra_tau: float = 240.0            # min
    drift_sd: float = 0.08
    drift_tau: float = 20 * DAY
    cycle_len: float = 28.0             # days
    cycle_phase: float = 0.0            # days
    menstrual_shape: str = "late"       # "mid" (sine, peak mid-luteal) | "late" (peak at onset, BDDP logs; LESSONS 136)
    luteal_amp: float = 0.08            # luteal SI dip (fraction) [02: population ±2.6%, responders more]
    illness_rate: float = 3.0           # episodes per year
    # nightly named factors (evidence/12; LESSONS 77)
    sleep_sd: float = 77.0              # min, night-to-night sleep duration SD (Messman 2022)
    sleep_si_per_h: float = 0.05        # next-day SI loss per hour of lost sleep (Donga 2010: −21% after 4 h in T1D)
    gh_cv: float = 0.32                 # night-to-night CV of nocturnal GH (30–35%; Edge 1990, Campbell 1985)
    gh_dawn: float = 0.20               # dawn EGP increment that tracks GH, elasticity ~1 (evidence/12 §5)
    drinker: bool = False               # 63% of T1D adults drank in the past month
    p_drink: float = 0.0                # nights with ≥ 2 drinks (≤ 20%) [J within range]
    stress_reactive: bool = False       # ~1/3 of people raise glucose under stress (Riazi 2004)
    p_stress: float = 0.4               # days with a stressor (NSDE ~40%)
    stress_si: float = 0.10             # SI loss 1–5 h after onset (Moberg 1994; low end for everyday stress)
    steroid_rate: float = 0.09          # oral glucocorticoid courses per year: Waljee 2017's 21.1% of adults with >= 1 in 3 years
                                        # is 7.4%/yr for a first course; repeats lift it a little [J]
    preg_week: float = float("nan")     # gestational week at the simulation's start (scenario X9); nan = not pregnant
    caffeine_si: float = 0.15           # SI loss at the plasma peak of a ~200 mg dose (Keijzers 2002, IV clamp; evidence/11 §4.2)
    # B15 ambient heat (00 D36): insulin absorption × (1 + heat_a·max(0, T − 13 °C)) on the day's mean residential temperature.
    # Hypoglycaemia odds rise above 13 °C, OR 1.26 at 25 vs 13 °C, same-day (Diabetes Care 2026, 679 T1D adults, 33 M CGM
    # readings); the leading mechanism is faster subcutaneous absorption from skin blood flow (sauna: +110%, Koivisto 1980).
    # heat_a is calibrated to that OR in paired fixed-temperature arms (LESSONS 290)
    heat_a: float = 0.0
    temp_mean: float = 21.0             # the person's mean daily temperature over the window [J: US late-spring/summer normals]
    temp_sd: float = 3.0                # day-to-day SD around it [J]
    temp_rho: float = 0.7               # day-to-day persistence [J]
    heat_T: float = float("nan")        # fixed temperature for calibration arms (nan = the person's climate)
    seed: int = 0


def sample_mod_traits(rng: np.random.Generator, age: float, sex: str) -> ModTraits:
    # the seven Visentin patterns, equally likely: Hinshaw 2013 (T1D, triple tracer) found no population B/L/D SI
    # difference, the pattern being individual; Visentin's mix (70% low at breakfast) put simulated 09 h glucose at
    # 153–157 against donors' 141 (equal classes: 143–145; LESSONS 59)
    cls = VISENTIN[rng.choice(len(VISENTIN))][0]
    t = ModTraits(
        circ_class=cls,
        # Visentin's low/high SI ratio (0.40 ± 0.23) is an estimate from meal tests whose noise inflates the
        # swing: at that amplitude the simulated 24-h glucose amplitude was 0.23 vs the field's 0.12
        # (ablation 2026-10-15). Half the swing [J; to be settled on circadian_amp]
        circ_raw=float(rng.normal(0.40, 0.23)),
        dawn=bool(rng.random() < 0.52),
        dawn_amp=float(np.clip(np.exp(rng.normal(math.log(0.3), 0.6)), 0.05, 1.2)),
        dawn_onset=float(rng.uniform(120, 270)),
        cycle_len=float(np.clip(rng.normal(28, 3), 21, 38)),
        cycle_phase=float(rng.uniform(0, 28)),
        luteal_amp=float(np.clip(np.exp(rng.normal(math.log(0.08), 0.5)), 0.0, 0.3)) if rng.random() < 0.63 else 0.0,
        illness_rate=5.0 if age < 13 else 3.0,
        drinker=bool(age >= 18 and rng.random() < 0.63),
        p_drink=float(rng.uniform(0.03, 0.20)),
        stress_reactive=bool(rng.random() < 0.33),
        seed=int(rng.integers(1 << 31)),
    )
    t.circ_low = float(np.clip(1.0 - t.circ_swing * (1.0 - t.circ_raw), 0.4, 1.0))
    # on by default with the BDDP-log shape (Pete 2026-10-18, LESSONS 136; was off: "stress scenario only")
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
        hours = np.array([4.0, 6.0, 14.0])              # B 07–11, L 11–17, D 17–07
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
        # nightly named factors (LESSONS 77): one draw per night / day, from a dedicated stream
        rn = np.random.default_rng(traits.seed + 101)
        self.sleep_loss_h = np.maximum(0.0, -rn.normal(0, traits.sleep_sd, self.days)) / 60.0    # night d (before day d)
        self.gh = np.exp(rn.normal(0, math.sqrt(math.log(1 + traits.gh_cv ** 2)), self.days) - math.log(1 + traits.gh_cv ** 2) / 2)
        self.drink = (rn.random(self.days) < traits.p_drink) & traits.drinker                     # evening of day d
        self.stress_on = np.where(rn.random(self.days) < traits.p_stress, rn.uniform(8 * 60, 20 * 60, self.days), -1.0)
        # B3 intraday OU and B4 drift, advanced minute by minute
        self.rng = r
        self.caf = self._caffeine(traits) if traits.enabled.get("caffeine") else None
        # B15 daily mean temperature: AR(1) around the person's climate mean, own stream
        rt = np.random.default_rng(traits.seed + 1511)
        tz = np.zeros(self.days); tz[0] = rt.normal()
        for d in range(1, self.days): tz[d] = traits.temp_rho * tz[d - 1] + math.sqrt(1 - traits.temp_rho ** 2) * rt.normal()
        self.temp = (getattr(traits, "temp_mean", 21.0) + rt.normal(0, 4.0)) + getattr(traits, "temp_sd", 3.0) * tz
        self.gc = self._glucocorticoid(traits)
        self.ou = r.normal(0, traits.intra_sd)
        self.day_ou = r.normal(0, traits.day_sd)
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

    def _caffeine(self, t: ModTraits):
        """Per-minute SI factor from caffeine, as a deviation from the person's own mean daily profile (evidence/11
        §4.2: the habitual part is already in the donor's tuned basal shape; only day-to-day dose and timing add).
        Everything is drawn on its own stream (seed + 202), so other factors stay paired.
        - user: 64% of adults drink coffee daily [unverified, NCA]; cups/day Poisson, person mean lognormal ~2
        - first cup ~ N(07:30, 60 min), later cups 10:00–16:00; ~95 mg a cup; 10% of days skipped
        - one-compartment oral PK: absorption ka 3/h (peak ~30–60 min), t½ lognormal median 5 h (2–10 h, CYP1A2)
        - effect linear in concentration: −caffeine_si at the peak of a 200 mg dose, capped at −30%"""
        rc = np.random.default_rng(t.seed + 202)
        if rc.random() >= 0.64: return None
        cups = float(np.clip(np.exp(rc.normal(math.log(2.0), 0.4)), 0.5, 5.0))
        th = float(np.clip(np.exp(rc.normal(math.log(5.0), 0.35)), 2.0, 10.0)) * 60.0
        ka, ke = 3.0 / 60.0, math.log(2) / th
        n = self.days * DAY; tt = np.arange(0, 12 * 60)
        kern = ka / (ka - ke) * (np.exp(-ke * tt) - np.exp(-ka * tt))           # per mg, arbitrary units
        ref = 200.0 * kern.max()
        conc = np.zeros(int(n) + len(tt))
        for d in range(self.days):
            if rc.random() < 0.10: continue
            k = rc.poisson(cups)
            for j in range(k):
                st = rc.normal(7.5 * 60, 60) if j == 0 else rc.uniform(10 * 60, 16 * 60)
                i = int(d * DAY + max(0.0, st))
                conc[i:i + len(tt)] += 95.0 * kern
        conc = conc[:int(n)]
        eff = 1.0 - np.minimum(t.caffeine_si * conc / ref, 0.30)
        mean_day = eff.reshape(self.days, int(DAY)).mean(axis=0)
        return eff / np.tile(mean_day, self.days)

    def _glucocorticoid(self, t: ModTraits, force_day: int | None = None) -> list:
        """B14 oral glucocorticoid courses, on their own stream (seed + 303) so every other factor stays paired.
        Each course: n days U(4, 7) (a 6-day dose pack is half of short courses, Waljee 2017; Bevier 2008's insulin was
        back to baseline by day 4), a morning dose N(08:00, 45 min), peak SI loss U(0.35, 0.60) on day 1 (Bevier: basal
        and boluses +30–100%, mean +69%, i.e. SI × 0.5–0.77 through the day) [J], tapering linearly to 1/n."""
        rg = np.random.default_rng(t.seed + 303)
        k = rg.poisson(getattr(t, "steroid_rate", 0.09) * self.days / 365.0)
        starts = list(rg.uniform(0, self.days, k))
        if force_day is not None: starts = [float(force_day)]
        out = []
        for st in starts:
            n = int(rg.integers(4, 8)); hour = float(rg.normal(8 * 60, 45)); peak = float(rg.uniform(0.35, 0.60))
            for j in range(n):
                out.append((int(st) + j, hour, peak * (n - j) / n))
        return out

    def steroid(self, m: float) -> float:
        """SI factor from glucocorticoid doses: none before 2 h after the morning dose, ramping to the day's loss by 6 h,
        held to 12 h, gone by 22 h (fasting glucose near normal, afternoon-evening highs; hospital guidance, PMC8157052)."""
        f = 1.0
        for (d, hour, loss) in self.gc:
            x = (m - (d * DAY + hour)) / 60.0
            if x < 2 or x >= 22: continue
            w = (x - 2) / 4 if x < 6 else 1.0 if x < 12 else (22 - x) / 10
            f *= 1.0 - loss * w
        return f

    @staticmethod
    def pregnancy_need(week: float) -> float:
        """Insulin need ÷ pre-pregnancy by gestational week (X9). Shape: García-Patterson 2010 (n = 65 T1D; three changes
        of direction: up to week 9, down to week 16, up to week 37); slope from week 16 ~5%/week, linear (ADA Standards
        2023 §15); a late fall after 37 (falling late requirement: J Perinatol 2021, s41372-021-00979-x). The early peak
        (+10%) and nadir (−5%) sizes are [J]."""
        w = float(week)
        if w < 9: return 1.0 + 0.10 * w / 9.0
        if w < 16: return 1.10 - 0.15 * (w - 9.0) / 7.0
        if w < 37: return 0.95 * (1.0 + 0.05 * (w - 16.0))
        return 0.95 * (1.0 + 0.05 * 21.0) * max(0.8, 1.0 - 0.05 * (w - 37.0))

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
        if getattr(self.t, "menstrual_shape", "mid") == "late":
            # BDDP cycle logs (LESSONS 136): glucose highest on the days before and at menses onset, back by ~day 3,
            # lowest a week after. SI falls through the late luteal phase to a low at onset (day 0), holds 2 days
            if day < 2.0: f = 1.0
            elif day < 3.0: f = 3.0 - day
            elif day >= ov + 3.0: f = (day - (ov + 3.0)) / (self.t.cycle_len - (ov + 3.0))
            else: f = 0.0
            return 1.0 - self.t.luteal_amp * f
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
            if self.t.day_tau > 0:
                c = math.exp(-dt / self.t.day_tau)
                self.day_ou = c * self.day_ou + math.sqrt(1 - c * c) * self.rng.normal(0, self.t.day_sd)
            self.last = m
        log_si = 0.0
        if en["day"] and self.t.day_tau > 0:
            log_si += self.day_ou
        elif en["day"]:
            x = (m - 4 * 60) / DAY
            d = int(math.floor(x)); into = (x - d) * DAY
            cur = self.day[max(0, min(d, self.days - 1))]; prev = self.day[max(0, min(d - 1, self.days - 1))]
            log_si += cur if into >= 180 else prev + (cur - prev) * into / 180.0
        if en["intraday"]: log_si += self.ou
        if en["drift"]: log_si += self.drift
        si = math.exp(log_si)
        if en["circadian"]: si *= self.circadian(m)
        si *= self.menstrual(m)
        d = int(m // DAY); mm = m % DAY; dd = max(0, min(d, self.days - 1))
        if en.get("sleep") and 7 * 60 <= mm < 23 * 60:
            si *= 1.0 - self.t.sleep_si_per_h * self.sleep_loss_h[dd]
        if self.caf is not None and en.get("caffeine"):
            si *= float(self.caf[min(int(m), len(self.caf) - 1)])
        if en.get("stress") and self.t.stress_reactive and self.stress_on[dd] >= 0:
            x = mm - self.stress_on[dd]
            if 60 <= x < 300: si *= 1.0 - self.t.stress_si
        if en.get("alcohol") and self.t.drinker:
            if mm >= 21 * 60 and self.drink[dd]: si *= 0.88                      # ethanol present (Kerr: −12%)
            if mm < 3 * 60 and d >= 1 and self.drink[max(0, d - 1)]: si *= 0.88
        egp = 1.0 + (self.dawn(m) if en["dawn"] else 0.0)
        if en.get("gh") and 3 * 60 <= mm < 10 * 60:
            # mean-zero night-to-night GH variation of the dawn increment (the mean dawn lives in the basal profile)
            shape = (mm - 180) / 180.0 if mm < 360 else 1.0 if mm < 480 else (600 - mm) / 120.0
            egp += self.t.gh_dawn * (self.gh[dd] - 1.0) * shape
        if en.get("alcohol") and self.t.drinker and d >= 1 and self.drink[d - 1] and 6 * 60 <= mm < 12 * 60:
            egp *= 0.85                                                            # morning after (Turner 2001) [I size]
        pw = getattr(self.t, "preg_week", float("nan"))
        if pw == pw:
            si /= self.pregnancy_need(pw + m / (7 * DAY))
        if en.get("steroid", True) and self.gc:
            si *= self.steroid(m)
        if en["illness"]:
            s_ill, e_ill, _ = self.illness(m)
            si *= s_ill; egp *= e_ill
        ab = 1.0
        if en.get("heat") and getattr(self.t, "heat_a", 0.0) > 0:
            T = self.t.heat_T if self.t.heat_T == self.t.heat_T else float(self.temp[dd])
            ab = 1.0 + self.t.heat_a * max(0.0, T - 13.0)
        return si, egp, ab
