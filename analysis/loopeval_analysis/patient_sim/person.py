"""A virtual person: physiology, truth, settings and traits, drawn from a real donor template.

Sampling order (each step's evidence in docs/additive/COMPONENTS.md):
  1. a template row (templates.py) — a real donor's joint traits — jittered;
  2. truth: TDD, true basal (measured fasting insulin rate), true ISF (yardstick), from the row;
  3. body weight from TDD and an age-banded U/kg prior;
  4. physiology priors (ReplayBG / UVA / Hovorka distributions);
  5. calibration: Ib from the true basal, then SI_D and sE so a small probe bolus gives the true ISF
     with the drawn share of the effect through EGP suppression;
  6. derived truth: carb sensitivity (CSF) and true carb ratio (ISF / CSF);
  7. settings: the donor's own ISF / CR / basal, scaled by the same jitter as the truth, so each
     person keeps their donor's settings error;
  8. devices: sensor family, pump, dosing strategy, insulin formulation.
Behavior and modulator traits are attached by their own modules (behavior.py, modulators.py).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from .physiology import Body, BodyParams, Parcel
from .insulins import BRAND_TO_FORMULATION, FORMULATIONS

BEHAVIOR_COLS = ["carb_entries_per_day", "user_boluses_per_day", "carb_g_day", "archetype", "meals_per_day",
                 "meal_hours", "meal_size_med", "meal_size_logsd", "announced_share", "estimate_ratio",
                 "bolus_lead_min", "p_bolus_ann", "bolus_ratio", "corrections_per_day", "corr_bg_med", "corr_ratio",
                 "rescues_per_day", "rescue_size_med", "rescue_bg_med", "free_boluses_per_day",
                 "free_bolus_u_med", "true_corrections_per_day"]
CSF_PER_GEQ = 1.30        # ice L54: meal pulse g-eq per entered gram; g-eq = ISF_tdd/(500/TDD) mg/dL
ISF_W = 0.5      # weight of the yardstick against the person's own ISF setting in the truth (open, see sample_person)


@dataclass
class Person:
    name: str
    seed: int
    template: str                     # donor alias the person was drawn from
    age: float
    sex: str                          # "F" / "M" — BDDP has no sex field; drawn 50/50
    bw: float
    formulation: str
    sensor: str                       # "Dexcom G7" | "Dexcom G6" | "Libre 3" | ...
    pump: str                         # "Omnipod" | "twiist" | ...
    strategy: str                     # "autobolus" | "temp"
    body: BodyParams
    truth: dict                       # basal_uh, isf, csf, cr, tdd, carbs_g_day
    settings: dict                    # basal_uh, isf, cr, target, max_basal, max_bolus, suspend
    traits: dict = field(default_factory=dict)

    def controller_insulin(self) -> str:
        """The Loop curve this person's app is set to (a SETTING, not physiology)."""
        return FORMULATIONS[self.formulation].loop_preset


# ---------------------------------------------------------------------------- probes
def linear_part(bp: BodyParams) -> BodyParams:
    """The body with every non-insulin restoring or nonlinear term off: glucose effectiveness,
    the hypo risk amplification and counter-regulation. ISF and CSF are DEFINED on this linear
    part — the same bookkeeping ISF the eda yardstick estimates (ICE = velocity + ISF·activity) —
    and the full body then adds those terms on top."""
    return bp.scaled(sg=0.0, kappa=0.0, risk_lambda=0.0, cr_max=0.0, low_prop=False)


def _probe_isf(bp: BodyParams, formulation: str, dose: float = 0.1, minutes: int = 900) -> float:
    """Total glucose drop per unit of a small bolus at rest on the linear part, against a control."""
    bp = linear_part(bp)
    a, c = Body(bp, formulation), Body(bp, formulation)
    br = a.basal_rate_u_per_h()
    a.prime(br); c.prime(br)
    best = 0.0
    for m in range(minutes):
        a.infuse(br / 60.0, m); c.infuse(br / 60.0, m)
        if m == 0: a.infuse(dose, 0, omega=1.0)
        a.step(1.0); c.step(1.0)
        best = max(best, c.g - a.g)
    return best / dose


def _probe_isf_effective(bp: BodyParams, formulation: str, g_op: float = 180.0, dose: float = 0.5,
                         minutes: int = 600) -> float:
    """EFFECTIVE ISF at an operating glucose, on the FULL body: both arms eat the same fast glucose to
    reach ~g_op, one gets `dose` at the peak; peak difference per unit. This is what a closed-loop
    estimate (the eda yardstick) measures — glucose effectiveness and renal loss included (LESSONS 15)."""
    a, c = Body(bp, formulation), Body(bp, formulation)
    br = a.basal_rate_u_per_h()
    a.prime(br); c.prime(br)
    grams = max(5.0, (g_op - bp.gb) / max(csf_of(bp), 0.5) * 1.3)
    for b_ in (a, c): b_.eat(Parcel(0, grams, 0.08, 0.08, f=bp.f))
    best = 0.0
    for m in range(minutes):
        a.infuse(br / 60.0, m); c.infuse(br / 60.0, m)
        if m == 45: a.infuse(dose, m, omega=1.0)
        a.step(1.0); c.step(1.0)
        best = max(best, c.g - a.g)
    return best / dose


def csf_of(bp: BodyParams) -> float:
    """Carb sensitivity on the linear part: every absorbed gram lands in VG (mg/dL per g)."""
    return bp.f * 1000.0 / (bp.bw * bp.vg)


def calibrate(bp: BodyParams, formulation: str, isf: float, basal_uh: float,
              egp_share: float) -> BodyParams:
    """Set Ib from the true basal rate, split the effect between EGP suppression and disposal on the
    linear part (`egp_share`), then scale both so the EFFECTIVE ISF of the full body at operating
    glucose equals `isf` (the yardstick-type quantity; LESSONS 15)."""
    ib = basal_uh * 1000.0 / 60.0 / bp.bw / (bp.ke * bp.vi)
    bp = bp.scaled(ib=ib)
    tiny = 1e-7
    isf_e1 = _probe_isf(bp.scaled(se=1.0, si_d=tiny), formulation)        # EGP arm per unit sE
    isf_d1 = _probe_isf(bp.scaled(se=0.0, si_d=1e-3), formulation)        # disposal arm per 1e-3 SI_D
    se = egp_share * isf / max(isf_e1, 1e-9)
    sid = (1 - egp_share) * isf / max(isf_d1, 1e-9) * 1e-3
    lo, hi = 0.25, 6.0
    for _ in range(18):
        k = math.sqrt(lo * hi)
        got = _probe_isf_effective(bp.scaled(se=se * k, si_d=sid * k), formulation)
        if got > isf: hi = k
        else: lo = k
    k = math.sqrt(lo * hi)
    return bp.scaled(se=se * k, si_d=sid * k)


# ---------------------------------------------------------------------------- sampling
def _upk(age: float) -> float:
    """U/kg/day by age band [J; puberty raises need 25–30% (evidence/02), eda L47 TDD by age]."""
    return 0.75 if age < 13 else 1.0 if age < 18 else 0.6


# median body weight by age (kg), approximate CDC growth-chart medians for children, adult ~77 kg [J]
_BW = [(2, 12.0), (4, 16.0), (8, 26.0), (12, 40.0), (15, 56.0), (18, 65.0), (30, 77.0), (90, 77.0)]


def _bw_median(age: float) -> float:
    return float(np.interp(age, [a for a, _ in _BW], [w for _, w in _BW]))


def _formulation(brand: str, rng) -> str:
    b = str(brand).lower()
    if b in BRAND_TO_FORMULATION: return BRAND_TO_FORMULATION[b]
    # unrecorded (twiist uploader, eda L46): draw from the recorded mix, rapid 52 : ultra-rapid 20
    u = rng.random()
    return "lispro" if u < 27 / 72 else "aspart" if u < 52 / 72 else "fiasp" if u < 63 / 72 else "lyumjev"


def sample_person(templates: pd.DataFrame, seed: int, alias: Optional[str] = None,
                  jitter: float = 0.10, name: Optional[str] = None) -> Person:
    rng = np.random.default_rng(seed)
    row = templates[templates.alias == alias].iloc[0] if alias else templates.iloc[rng.integers(len(templates))]
    lj = lambda: float(np.exp(rng.normal(0.0, jitter)))

    ages = templates.age_years.dropna()
    age = float(row.age_years) if np.isfinite(row.age_years) else (float(rng.choice(ages)) if len(ages) else float(rng.normal(35, 15)))
    age = max(4.0, age + rng.normal(0, 2.0))
    j_tdd, j_isf, j_basal = lj(), lj(), lj()
    tdd = float(row.tdd) * j_tdd
    # TRUE ISF: the person's own setting (tuned against their real body) moved part of the way toward
    # the eda yardstick. The yardstick/settings ratio spreads 0.41–2.69 but barely tracks lows (Spearman
    # −0.13 with t<70), so much of it is estimation noise (eda L53: ISF is not identifiable in closed
    # loop). ISF_W is an open parameter, settled by per-donor twin validation [J 0.5].
    r_isf = float(np.clip(row.isf_true / row.isf, 0.5, 2.0))
    isf_true = float(row.isf) * r_isf ** ISF_W * j_isf
    fasting_rate = float(row.basal_true) * j_basal          # measured; kept as a validation quantity
    # body weight: the age prior blended with what TDD implies at an age-banded U/kg (a profile age can
    # belong to the account holder, eda L47, so neither alone is trusted)
    bw_age = _bw_median(age)
    bw_tdd = tdd / _upk(age)
    bw = float(np.clip(math.exp(0.5 * math.log(bw_age) + 0.5 * math.log(bw_tdd) + rng.normal(0, 0.12)), 15, 160))
    formulation = _formulation(row.insulin_brand, rng)

    # physiology priors (COMPONENTS §A)
    bp = BodyParams(
        bw=bw,
        kd=float(np.exp(rng.normal(-3.509, 0.619 * 0.5))),     # half the ReplayBG log-sd: its prior is for identification, not a population
        ka2=float(np.exp(rng.normal(math.log(0.018), 0.427 * 0.5))),   # centre refit to the clamp profile
        sg=float(np.exp(rng.normal(math.log(0.003), 0.5))),
        gb=float(np.clip(rng.normal(119, 7.1), 95, 150)),
        egp_b=float(np.clip(rng.normal(2.5, 0.33), 1.5, 3.5)),
        vg=float(np.exp(rng.normal(math.log(1.88), 0.15))),
        rthr=float(np.clip(rng.normal(180, 25), 130, 250)),
        rcl=float(np.exp(rng.normal(math.log(0.003), 0.3))),
        cr_max=float(np.exp(rng.normal(0.0, 0.5))),
        cr_g=float(rng.normal(65, 5)),
        kappa=float(np.exp(rng.normal(math.log(0.15), 0.4))),
        # exercise muscle uptake at full intensity: moderate work (I 0.5) ≈ −50 mg/dL/h from uptake alone, the
        # rest of the lab −80 mg/dL/h (García-García 2015) from the acute SI boost [J; calibrate vs T1DEXI]
        ex_uptake=float(np.exp(rng.normal(math.log(3.0), 0.3))),
        f=float(np.clip(rng.normal(0.9, 0.05), 0.7, 1.0)),
    )
    if bp.ka2 >= bp.kd: bp = bp.scaled(ka2=0.9 * bp.kd)
    # CARB SENSITIVITY per LABELED gram: physics (f·1000 / BW·VG, f 0.9 for tracer glucose) gives ~1.7x
    # the rise donors show. Measured: a meal pulse is 1.30x what the entered grams predict at the
    # settings' ISF/CR (ice L54). Labeled carbohydrate is not all glucose appearance (fibre, fructose,
    # resistant starch), so bioavailability per labeled gram is the person's calibrated parameter, and f
    # follows (LESSONS 14, 17).
    # ice's g-eq is ISF_tdd / (500/TDD) mg/dL — settings-free (ice_gen/meals.py) — so the measured rise
    # per entered gram is 1.30 x that, not 1.30 x the settings' ISF/CR (LESSONS 17)
    csf_target = CSF_PER_GEQ * float(row.isf_true) * float(row.tdd) / 500.0 * float(np.exp(rng.normal(0, 0.15)))
    f_cal = csf_target * bw * bp.vg / 1000.0
    if f_cal > 1.0:
        bp = bp.scaled(f=1.0, vg=float(1000.0 / (bw * csf_target)))
    else:
        bp = bp.scaled(f=float(max(f_cal, 0.3)))
    egp_share = float(rng.uniform(0.3, 0.5))
    # INSULIN BALANCE (TDD is the measured constraint): a true basal share [J prior around the scheduled
    # share 0.43–0.51, eda L9], and the carbs EATEN are what the rest of TDD covers at the true CR
    # (= ISF / CSF of this body). Announced grams then drive only what the person enters.
    share = float(np.clip(rng.normal(0.5, 0.07), 0.35, 0.7))
    basal_true = tdd * share / 24.0
    bp = calibrate(bp, formulation, isf_true, basal_true, egp_share)
    csf = csf_of(bp)
    cr_true = isf_true / csf
    carbs = max(20.0, tdd * (1 - share) * cr_true)
    strategy = "temp" if str(row.strategy).startswith("temp") else "autobolus"
    settings = dict(
        basal_uh=float(row.basal) * j_basal, isf=float(row.isf) * j_isf, cr=float(row.cr) * j_isf / j_basal ** 0,
        target=float(row.target), max_basal=float(row.max_basal) * j_basal, max_bolus=float(row.max_bolus),
        suspend=70.0)
    return Person(
        name=name or f"v{seed:05d}", seed=seed, template=str(row.alias), age=age,
        sex="F" if rng.random() < 0.5 else "M", bw=bw, formulation=formulation,
        sensor=str(row.sensor), pump=str(row.pump), strategy=strategy, body=bp,
        truth=dict(tdd=tdd, basal_uh=basal_true, fasting_rate=fasting_rate, isf=isf_true, csf=csf, cr=cr_true,
                   carbs_g_day=carbs, egp_share=egp_share),
        settings=settings,
        traits=dict(template_rates={k: (row[k] if not isinstance(row[k], float) or np.isfinite(row[k]) else np.nan)
                                    for k in BEHAVIOR_COLS if k in row.index}))
