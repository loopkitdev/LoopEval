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
                 "free_bolus_u_med", "true_corrections_per_day", "tir", "t70",
                 "entries_raw", "entered_g_raw", "corr_over_share", "corr_over_u", "corr_u_med", "corr_u_lsd", "corr_p_mult", "corr_thr_adj", "stack_p", "unann_hours", "boluses_raw", "bolus_entry_raw", "topups_raw", "lone_raw", "manual_u_day",
                 "abs_fast_s", "abs_slow_s", "abs_fast_l", "abs_slow_l", "gap_short", "gap_long", "entry_hours",
                 "clk_b_med", "clk_b_sd", "clk_l_med", "clk_l_sd", "clk_d_med", "clk_d_sd"] + \
                [f"ov_{c}_{k}" for c in ("less", "more", "tgt") for k in ("day", "f", "lo", "hi", "h")] + \
                ["edit_basal_day", "edit_isf_day", "edit_cr_day", "corr_exposure", "slot_g", "slot_ann", "slot_lr", "night_need_ratio", "offline_day", "perr_day",
                 "treat_log_day", "low_entered_share", "skip_bfast"]
# ice L54 measures 1.30 g-eq of meal pulse per entered gram (1.21 for the pilot donors through the same
# labeler, meal_response/ice_check). Run through that labeler, simulated people at 1.30 read 0.91 —
# glucose effectiveness erodes the pulse before ICE sees it — so the constant is set by the labeler:
# 1.30 × 1.21/0.91 (LESSONS 27)
CSF_PER_GEQ = 1.85      # re-read through the labeler under saturating gastric emptying: 1.73 read 1.13 vs 1.21 (LESSONS 33)
CSF_BLEND_CAL = 1.25    # re-read through the labeler: 1.18 read 1.025 (LESSONS 37), then 1.15 as other components changed (c39); under the
                        # total-drop ISF option it must be 1.08 (labeler 1.40 → 1.21; LESSONS 75)
CSF_BLEND_CAL_TOTAL = 1.05   # labeler g-eq per entered gram 1.21 on the share-0.8 + egp_sat base (1.08 read 1.247; LESSONS 197)
ISF_W = 1.0      # weight of the yardstick against the person's own ISF setting in the truth: the body follows the data-fitted
                 # value, not the entered setting (Pete 2026-10-19; LESSONS 259; was 0.5)


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


def _probe_csf_effective(bp: BodyParams, formulation: str, g_op: float = 180.0, grams: float = 10.0,
                         minutes: int = 600) -> float:
    """EFFECTIVE carb sensitivity on the FULL body at the same operating point as the effective ISF probe: both
    arms raised to ~g_op with the same fast glucose, one eats `grams` more (a meal parcel) at minute 45; peak
    difference per gram. Glucose effectiveness, κ and renal loss erode a meal's rise as they erode a bolus's drop,
    so the true CR must be ISF_eff / CSF_eff, not ISF_eff / CSF_linear (LESSONS 40)."""
    a, c = Body(bp, formulation), Body(bp, formulation)
    br = a.basal_rate_u_per_h()
    a.prime(br); c.prime(br)
    g0 = max(5.0, (g_op - bp.gb) / max(csf_of(bp), 0.5) * 1.3)
    for b_ in (a, c): b_.eat(Parcel(0, g0, 0.08, 0.08, f=bp.f))
    best = 0.0
    for m in range(minutes):
        a.infuse(br / 60.0, m); c.infuse(br / 60.0, m)
        if m == 45: a.eat(Parcel(m, grams, bp.kempt, bp.kabs, f=bp.f))
        a.step(1.0); c.step(1.0)
        best = max(best, a.g - c.g)
    return best / grams


def _probe_cr_true(bp: BodyParams, formulation: str, grams: float = 30.0, hours: float = 6.0) -> float:
    """TRUE carb ratio: the grams one unit covers with no net glucose change once both have acted. A meal of
    `grams` plus a bolus at the meal, bisected on the bolus until glucose `hours` later equals an untreated
    control's (both at the true basal). This balances the whole excursion, which the ratio of the two peak
    probes does not: glucose effectiveness erodes the slower insulin effect more (LESSONS 40)."""
    def end_diff(units: float) -> float:
        a, c = Body(bp, formulation), Body(bp, formulation)
        br = a.basal_rate_u_per_h(); a.prime(br); c.prime(br)
        a.eat(Parcel(0, grams, bp.kempt, bp.kabs, f=bp.f))
        if units > 0: a.infuse(units, 0, omega=1.0)
        for m in range(int(hours * 60)):
            a.infuse(br / 60.0, m); c.infuse(br / 60.0, m)
            a.step(1.0); c.step(1.0)
        return a.g - c.g
    lo, hi = 0.0, grams / 2.0
    for _ in range(22):
        u = 0.5 * (lo + hi)
        if end_diff(u) > 0: lo = u
        else: hi = u
    return grams / max(0.5 * (lo + hi), 1e-6)


def csf_of(bp: BodyParams) -> float:
    """Carb sensitivity on the linear part: every absorbed gram lands in VG (mg/dL per g)."""
    return bp.f * 1000.0 / (bp.bw * bp.vg)


def calibrate(bp: BodyParams, formulation: str, isf: float, basal_uh: float,
              egp_share: float, total: bool = False, blend: float = 0.0) -> BodyParams:
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
    if total:
        # opt-in (LESSONS 72): ISF as the TOTAL drop per unit on the linear part (Loop's meaning), independent of how fast
        # each arm acts; the default below matches the full body's PEAK drop at ~180 mg/dL
        return bp.scaled(se=se, si_d=sid)
    lo, hi = 0.25, 6.0
    for _ in range(18):
        k = math.sqrt(lo * hi)
        got = _probe_isf_effective(bp.scaled(se=se * k, si_d=sid * k), formulation)
        if got > isf: hi = k
        else: lo = k
    k = math.sqrt(lo * hi)
    # blend (experiment, LESSONS 133): 0 = peak calibration (default), 1 = total-drop (k = 1), geometric in between
    k = k ** (1.0 - min(max(blend, 0.0), 1.0))
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
                  jitter: float = 0.10, name: Optional[str] = None, isf_w: Optional[float] = None,
                  csf_mult: float = 1.0, sg_mult: float = 1.0, prof_w: float | None = None, egp_share: float | None = None, isf_total: bool = True,
                  kappa_mult: float = 1.0, ge_var: bool = True, basal_own: bool = False, egp_sat: bool = False, p2e: float | None = None, prof_deliv: bool = False, csf_own: bool = False, twin: bool = False, suspend_own: bool = False, night_own: bool = False, night_add: bool = False,
                  basal_share: float | None = 0.42, isf_blend: float = 0.0) -> Person:
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
    isf_true = float(row.isf) * r_isf ** (ISF_W if isf_w is None else isf_w) * j_isf
    if twin:
        # per-person twin calibration (Pete 2026-10-18, LESSONS 219): body ISF × the donor's fitted multiplier, so the
        # twin reproduces its donor's time < 70 (template column twin_isf_mult, iterated from cohort runs)
        k_ = row.get("twin_isf_mult") if hasattr(row, "get") else None
        if k_ is not None and np.isfinite(float(k_)): isf_true *= float(k_)
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
        # insulin-independent glucose effectiveness: median 0.0045/min, inside the 0.0013–0.0047 UVA/Padova range Pete allowed
        # for calibration (2026-10-16); 0.003 left the evidence base's level +6 and its excursions too persistent (LESSONS 208)
        sg=float(sg_mult * np.exp(rng.normal(math.log(0.0045), 0.5))),
        gb=float(np.clip(rng.normal(119, 7.1), 95, 150)),
        egp_b=float(np.clip(rng.normal(2.5, 0.33), 1.5, 3.5)),
        vg=float(np.exp(rng.normal(math.log(1.88), 0.15))),
        rthr=float(np.clip(rng.normal(180, 25), 130, 250)),
        rcl=float(np.exp(rng.normal(math.log(0.003), 0.3))),
        # counter-regulation gain, mg/kg/min: half the judged lnN(1.0) — fitted to the donors' low nadirs as evidence/01 §4.4
        # prescribes (T1D loses glucagon early; Pete 2026-10-18, LESSONS 166)
        cr_max=float(0.3 * np.exp(rng.normal(0.0, 0.5))),   # median 0.5 -> 0.3: refitted to the donors' low depths on the current body (LESSONS 272; was LESSONS 166)
        cr_g=float(rng.normal(65, 5)),
        # κ: insulin-mediated uptake's glucose dependence. Best 1981 (fixed-insulin clamps): doubling glucose raises
        # disposal ×1.24 / ×1.68 / ×1.78 at low / mid / high insulin, κ ≈ 0.24 / 0.68 / 0.78; the median is the mid-insulin
        # value, where meal and correction insulin acts (Pete 2026-10-18, LESSONS 165; was 0.15 on Del Prato's basal clamp)
        kappa=float(kappa_mult * np.exp(rng.normal(math.log(0.675), 0.4))),
        # exercise muscle uptake at full intensity: moderate work (I 0.5) ≈ −50 mg/dL/h from uptake alone, the
        # rest of the lab −80 mg/dL/h (García-García 2015) from the acute SI boost [J; calibrate vs T1DEXI]
        ex_uptake=float(np.exp(rng.normal(math.log(3.0), 0.3))),
        f=float(np.clip(rng.normal(0.9, 0.05), 0.7, 1.0)),
    )
    if bp.ka2 >= bp.kd: bp = bp.scaled(ka2=0.9 * bp.kd)
    if ge_var:
        # between-person gastric emptying (evidence/09 §parameters): Vmax lognormal CV 30% (Samsom 2003 SDs 28% controls,
        # 36% diabetes; Hellmig 2006), and the 28% of T1D adults with delayed emptying at ×0.6–0.8 (Samsom 2003). Km stays
        # 60 kcal, so the small-load rate kempt scales with Vmax. Own stream: the other draws are unchanged.
        rg = np.random.default_rng(seed + 313)
        g_mult = float(np.exp(rg.normal(-0.5 * 0.3 ** 2, 0.3)))
        if rg.random() < 0.28: g_mult *= float(rg.uniform(0.6, 0.8))
        bp = bp.scaled(ge_kcal_max=bp.ge_kcal_max * g_mult, kempt=bp.kempt * g_mult)
    # CARB SENSITIVITY per LABELED gram: physics (f·1000 / BW·VG, f 0.9 for tracer glucose) gives ~1.7x
    # the rise donors show. Measured: a meal pulse is 1.30x what the entered grams predict at the
    # settings' ISF/CR (ice L54). Labeled carbohydrate is not all glucose appearance (fibre, fructose,
    # resistant starch), so bioavailability per labeled gram is the person's calibrated parameter, and f
    # follows (LESSONS 14, 17).
    # ice's g-eq is ISF_tdd / (500/TDD) mg/dL — settings-free (ice_gen/meals.py) — so the measured rise
    # per entered gram is 1.30 x that, not 1.30 x the settings' ISF/CR (LESSONS 17)
    csf_target = csf_mult * CSF_PER_GEQ * float(row.isf_true) * float(row.tdd) / 500.0 * float(np.exp(rng.normal(0, 0.15)))
    # people tune their carb ratio on their own body, exactly as they tune ISF (G2): the body's carb sensitivity is
    # moved the same way toward what their settings imply (ISF/CR), with the same weight. Drawn independently of
    # the settings, settings-CR / true-CR spread 0.79–2.05 (p10–p90) and meals over- or under-bolused by 2× drove
    # post-meal lows at 4× the donors' rate (LESSONS 37)
    w = ISF_W if isf_w is None else isf_w
    csf_set = float(row.isf) / float(row.cr)
    # the labeler-calibrated constant depends on the ISF semantics: 1.25 for the peak calibration, 1.08 for total-drop
    # (LESSONS 75); the isf_total switch ran with 1.25 until 2026-10-18 (LESSONS 140)
    cal = CSF_BLEND_CAL_TOTAL if isf_total else CSF_BLEND_CAL
    csf_target = cal * csf_target ** (1 - w) * (csf_set * float(np.exp(rng.normal(0, 0.15)))) ** w
    if twin:
        k_ = row.get("twin_csf_mult") if hasattr(row, "get") else None    # the donor's median 3-h meal change (LESSONS 219)
        if k_ is not None and np.isfinite(float(k_)): csf_target *= float(k_)
    if csf_own:
        # per-person carbohydrate-to-insulin fit from data (LESSONS 217, Pete 2026-10-18: shape meal arrival from real
        # data): each donor's median 3-h meal outcome against their sim's, solved for the body's carb sensitivity
        k_ = row.get("csf_own_mult") if hasattr(row, "get") else None
        if k_ is not None and np.isfinite(float(k_)): csf_target *= float(k_)
    f_cal = csf_target * bw * bp.vg / 1000.0
    if f_cal > 1.0:
        bp = bp.scaled(f=1.0, vg=float(1000.0 / (bw * csf_target)))
    else:
        bp = bp.scaled(f=float(max(f_cal, 0.3)))
    # share of insulin's effect through EGP suppression on the linear part, centred on T1D meal tracer data: per-person
    # nadir suppression 44 ± 17% (time 160 ± 110 min) after a mixed meal with the usual bolus (Romeres 2025). Read like-for-
    # like (each person's own nadir, the liver's part of SG included), U(0.5, 0.7) gave 0.34 on the total-drop base and 0.8
    # gives 0.50 (LESSONS 195; adopted by Pete 2026-10-18) [centre from evidence, width J]
    egp_share_draw = float(rng.uniform(0.7, 0.9))
    if egp_share is not None: egp_share_draw = float(egp_share)
    egp_share = egp_share_draw
    # INSULIN BALANCE (TDD is the measured constraint): a true basal share [J prior around the scheduled
    # share 0.43–0.51, eda L9], and the carbs EATEN are what the rest of TDD covers at the true CR
    # (= ISF / CSF of this body). Announced grams then drive only what the person enters.
    share = float(np.clip(rng.normal(0.5, 0.07), 0.35, 0.7))
    # the true basal share's centre: 0.42 (Pete 2026-10-17, LESSONS 125). Donors' Loop trims overnight basal far more
    # than the sim's did at 0.5, i.e. real bodies need less than their schedule (median scheduled share 0.45) [J centre]
    if basal_share is not None:
        share = float(np.clip(share - 0.5 + basal_share, 0.25, 0.7))
    nr = float(row.get("night_ratio", np.nan)) if "night_ratio" in row.index else np.nan
    if basal_own and np.isfinite(nr) and float(row.basal) > 0:
        # the body's basal need from the donor's own overnight delivery: automatic delivery / scheduled basal on the
        # donor's nights (an upper bound: it includes night corrections), × the scheduled basal (LESSONS 125)
        share = float(np.clip(float(row.basal) * j_basal * min(nr, 3.0) * 24.0 / tdd, 0.30, 0.75))
    basal_true = tdd * share / 24.0
    if p2e is not None:               # refit of A5's EGP-arm rate, every person recalibrated at it (LESSONS 194)
        bp = bp.scaled(p2e=p2e)
    if egp_sat:                       # saturating hepatic signal + faster offset (LESSONS 193), before calibration
        bp = bp.scaled(egp_vs=2.57, p2e_off=0.015)
    bp = calibrate(bp, formulation, isf_true, basal_true, egp_share, total=isf_total, blend=isf_blend)
    # true CR on the LINEAR part: the TDD constraint holds with it (cohort c35 TDD 36 vs donors 37); the effective
    # peak-probe CSF (_probe_csf_effective) fed people for 42 U/day (c36), and a whole-excursion balance is
    # degenerate under glucose effectiveness (LESSONS 40)
    csf = csf_of(bp)
    cr_true = isf_true / csf
    k_isf_twin = 1.0
    if twin:
        k_ = row.get("twin_isf_mult") if hasattr(row, "get") else None
        if k_ is not None and np.isfinite(float(k_)): k_isf_twin = float(k_)
    # the intake budget is the donor's, not a consequence of the twin's ISF fit: divide the twin multiplier back out
    # (raising body ISF had raised cr_true and with it the carbs eaten; LESSONS 219)
    carbs = max(20.0, tdd * (1 - share) * cr_true / k_isf_twin)
    strategy = "temp" if str(row.strategy).startswith("temp") else "autobolus"
    # the donor's tuned 24-h basal shape (local hour, mean 1): Loop's schedule uses it as is; the body's basal need
    # follows it shrunk halfway (log), the same weight as ISF and CSF — people tune it on their body (LESSONS 48)
    prof = np.ones(24)
    bp_raw = row.get("basal_profile") if hasattr(row, "get") else None
    if isinstance(bp_raw, str):
        try:
            import json as _json
            prof = np.asarray(_json.loads(bp_raw), dtype=float)
        except ValueError:
            prof = np.ones(24)
    w_ = (ISF_W if isf_w is None else isf_w) if prof_w is None else prof_w
    prof_true = prof ** w_; prof_true = prof_true / prof_true.mean()
    if prof_deliv:
        # experiment (LESSONS 214): the body's need follows the donor's quiet-hour DELIVERED insulin shape (what their Loop
        # gave a fasting body), at full weight; Loop's schedule stays the donor's own
        dv = row.get("basal_profile_deliv") if hasattr(row, "get") else None
        if isinstance(dv, str):
            import json as _json
            d_ = np.asarray(_json.loads(dv), dtype=float)
            if np.isfinite(d_).all() and d_.mean() > 0: prof_true = d_ / d_.mean()
    nr_ = float(row.get("night_need_ratio", np.nan)) if hasattr(row, "get") else np.nan
    if night_own and np.isfinite(nr_) and nr_ > 0:
        # the body's 02-05 h need = the donor's steady-night delivered / scheduled × the schedule there (165 donors, median
        # 1.13; LESSONS 251), applied as a smooth bump: weight 1 at 02-05 h, cosine taper to 0 at 22 and 08 h; the shape is
        # renormalised to mean 1 (the 24-h basal total, and with it the intake budget, unchanged); m by bisection
        hh = np.arange(24); dist = np.minimum(np.abs(((hh - 3.5 + 12) % 24) - 12), 12.0)
        wgt = np.where(dist <= 1.5, 1.0, np.where(dist >= 5.5, 0.0, 0.5 * (1 + np.cos(np.pi * (dist - 1.5) / 4.0))))
        h25 = [2, 3, 4]
        q = nr_ * float(row.basal) * j_basal * float(np.mean(prof[h25])) / max(basal_true, 1e-6)
        f_ = (lambda m: float(np.mean((prof_true * (1 + (m - 1) * wgt) / prof_true.mean())[h25])) - q) if night_add else \
             (lambda m: (lambda pt: float(np.mean((pt / pt.mean())[h25])))(prof_true * (1 + (m - 1) * wgt)) - q)
        lo_, hi_ = 0.3, 20.0
        if f_(lo_) >= 0: m_ = lo_                     # target below reach: the lowest bump
        elif f_(hi_) <= 0: m_ = hi_                   # bodies whose basal level is far under the schedule: the highest
        else:                                         # (a silent skip here left them at 0.2-0.6x schedule; LESSONS 252)
            for _ in range(50):
                mid = 0.5 * (lo_ + hi_)
                if f_(mid) < 0: lo_ = mid
                else: hi_ = mid
            m_ = 0.5 * (lo_ + hi_)
        pt = prof_true * (1 + (m_ - 1) * wgt)
        if night_add:
            # experiment (LESSONS 255): the night need is added on top, the daytime shape kept; the body's 24-h basal rises by
            # the bump (the intake budget, set above from the unbumped basal, is not changed)
            prof_true = pt / prof_true.mean()
        else:
            prof_true = pt / pt.mean()
    settings = dict(
        basal_profile=[float(x) for x in prof],
        basal_uh=float(row.basal) * j_basal, isf=float(row.isf) * j_isf, cr=float(row.cr) * j_isf / j_basal ** 0,
        target=float(row.target), max_basal=float(row.max_basal) * j_basal, max_bolus=float(row.max_bolus),
        # the donor's own glucose safety limit (Loop suspends and withholds dosing below it; template median 80, 70 on 50
        # of 168): the sampler had given every person 70 since 79d7de3 (LESSONS 232)
        suspend=float(row.suspend) if suspend_own and np.isfinite(float(row.get("suspend", np.nan))) else 70.0)
    return Person(
        name=name or f"v{seed:05d}", seed=seed, template=str(row.alias), age=age,
        sex="F" if rng.random() < 0.5 else "M", bw=bw, formulation=formulation,
        sensor=str(row.sensor), pump=str(row.pump), strategy=strategy, body=bp,
        truth=dict(tdd=tdd, basal_uh=basal_true, fasting_rate=fasting_rate, isf=isf_true, csf=csf, cr=cr_true,
                   basal_profile=[float(x) for x in prof_true],
                   carbs_g_day=carbs, egp_share=egp_share),
        settings=settings,
        traits=dict(template_rates={k: (row[k] if not isinstance(row[k], float) or np.isfinite(row[k]) else np.nan)
                                    for k in BEHAVIOR_COLS if k in row.index}))
