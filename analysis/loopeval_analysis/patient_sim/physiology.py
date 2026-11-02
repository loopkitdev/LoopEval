"""The body: a minimal-model glucose–insulin plant with named nonlinear extensions.

Structure (docs/additive/evidence/01-physiology-core.md §1.2, adopted 2026-10-15): the
identifiable minimal-model spine of ReplayBG (Cappon et al., IEEE TBME 2023;70:3227,
doi:10.1109/TBME.2023.3286856) plus the terms that decide the low tail and long highs:

  insulin    per-dose subcutaneous depots  Isc1 → Isc2 → plasma Ip  (delay τ, rates kd, ka2; ke)
  action     disposal   dX_D = −p2 (X_D − SI_D·I)              (absolute: uptake X·G can never go negative)
             EGP arm    dX_E = −p2E(X_E − (I − Ib)/Ib)          (relative insulin, slower)
  glucose    dG = −SG(G − Gb) − (X_D·M(G)·risk(G) − X_b·Gb) + (EGP − EGP_b)/VG + Ra/VG − renal(G)
             M(G) = Gb + κ(G − Gb): κ = 1 is Bergman's X·G, whose insulin-dependent glucose effectiveness
             SI·Ib (~0.01–0.08 /min once SI is calibrated to ISF) flattens every meal; κ ≈ 0.15 puts total
             effective glucose effectiveness at the 0.0013–0.0047 /min fitted on UVA/Padova (COMPONENTS A5)
             (X_b = SI_D·Ib: the basal uptake the constant term balances, so the body rests at Gb)
             EGP = EGP_b · c(t) · clip(1 − sE·X_E, 0, 1 + sE) + CR(G)   (floor at 0, ~2× when insulin is gone)
  gut        per meal parcel  Qsto1 → Qsto2 → Qgut  (kempt·φ_hypo(G), kabs, delay β, bioavailability f)
  extensions counter-regulation with HAAF memory, renal loss above Rthr, S2013 hypo risk scale λ,
             exercise uptake / EGP surge, multiplicative sensitivity and EGP modulators.

Units: G mg/dL; insulin amounts mU/kg; EGP and appearance mg/kg/min; VG dL/kg; VI L/kg; time min.
Everything per kg is fixed at construction; the public interface speaks U, grams and mg/dL.

At I = Ib and no meals the body rests at Gb (the person's TRUE basal requirement holds them at Gb);
`Person` calibration sets Ib from the true basal rate and SI_D from the true ISF.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace


@dataclass
class BodyParams:
    """Per-person physiology. Defaults are ReplayBG / Hovorka population medians (adult)."""
    bw: float = 70.0               # kg
    # subcutaneous insulin (ReplayBG priors: kd median .030, ka2 median .0137; ke .127)
    kd: float = 0.030
    ka2: float = 0.018             # median ReplayBG 0.0137 refit with p2/p2e to the lispro clamp profile (COMPONENTS A2/A5)
    ke: float = 0.127
    vi: float = 0.126              # L/kg
    # insulin action
    p2: float = 0.025              # 1/min, disposal-action rate; back to the clamp fit since 2026-10-19 (LESSONS 365: with lows now carried by counter-regulation and sensor low-range noise, 0.025 matches 37 of 51). Was 0.04 (LESSONS 324). 0.025 was the 0.2 U/kg (~15 U) lispro clamp fit (GIR peak ~100 min,
                                   # LESSONS 9); typical boluses and Loop's automatic doses are ~0.05 U/kg and act sooner (smaller s.c.
                                   # doses act earlier — direction known, size not found for analogues). 0.04 (LESSONS 324) put t54,
                                   # p_reach54 and CV onto the donors' before counter-regulation and the sensor's low range were refitted.
                                   # Not Loop's curve: the body follows evidence about patients (Pete 2026-10-17; LESSONS 114)
    si_d: float = 5.0e-4           # disposal sensitivity, 1/min per (mU/L)  — calibrated to ISF
    p2e: float = 0.012             # 1/min, EGP-suppression onset rate: clamp GIR peak 108 min on the share-0.8 base (target ~100; 0.006 gave 125;
                                   # LESSONS 197). Was 0.006 (Pete 2026-10-17, LESSONS 131: post-meal EGP nadir depth
                                   # 0.54 vs the Romeres 2025 tracer's 0.56; 0.010 gave 0.41). T1D meal EGP suppression is
                                   # sustained with its nadir at ~160 min (Romeres 2025); ReplayBG prior 0.008 (LESSONS 70, 75)
    se: float = 1.0                # EGP suppression per unit relative insulin above basal
    ib: float = 10.0               # basal plasma insulin, mU/L — set from the true basal rate
    # glucose
    vg: float = 1.88               # dL/kg (UVA/Padova; ReplayBG's 1.45 gives ~2x the carb sensitivity people's settings imply)
    sg: float = 0.003              # insulin-INDEPENDENT glucose effectiveness, 1/min (see COMPONENTS: physiology)
    sg_km: float = 0.0             # A1d, SMOOTH form (L 641): Michaelis-Menten half-saturation of the
                                   # insulin-independent uptake, mg/dL above `sg_g0`. 0 = off (use sg_kappa / linear).
                                   # Fitted 63.2 with sg_g0 80.4 and sg 0.00403 to ice's UNBIASED band profile
                                   # (their 2026-11-02 reply: same-span bins, 0.235 / 0.118 / 0.053 / 0.024 /h),
                                   # RMS 0.0008 /h. MEASURED AND REJECTED (L 642): band-faithful here means
                                   # x0.32 of the default dwell-weighted force, and the cohort cost orders with that
                                   # integral whatever shape removes it - t70 ~2.3x the reference and t54 3-4.7x on
                                   # all three draws, worse than either kink. The "near-low force 0.242" of L 641 is
                                   # the LOCAL SLOPE; the force a low feels is the span average from Gb, 0.177 at
                                   # G 65, so this form is WEAKER below 130 than `sg_kappa`, not stronger. Off.
    sg_g0: float = 80.0            # glucose below which the insulin-independent force is at FULL strength (mg/dL).
                                   # Below Gb deliberately: ice's profile is steepest below 90, and the zero of the
                                   # term stays at Gb by construction (the excess is F(G) - F(Gb)).
    sg_kappa: float = 0.0          # glucose-dependence of INSULIN-INDEPENDENT uptake, by analogy with kappa (L 637):
                                   # above Gb the excess it acts on rises at this fraction, below Gb full strength.
                                   # 0 = linear in (G - Gb), as before. ice L 140a's learned background slope falls
                                   # 0.17 -> 0.02 /h from the low band to 180-250, which a linear term cannot make.
    # ge_split (A1a–c, LESSONS 548): sg replaced by its named parts (sg is then unused)
    ge_split: bool = False
    ge_spare: bool = False         # A1c alone on the lumped SG: insulin-independent uptake falling below g_ii (L 561)
    sg_p: float = 0.0012           # A1a peripheral insulin-independent mass action, 1/min on (G − Gb), both sides (Del Prato 1997 T1D)
    sg_h_lo_ins: bool = True       # the below-basal hepatic term carries basal EGP's own insulin suppression (L 599)
    sg_h_lo: float = 0.0           # A1b BELOW basal: extra hepatic release as glucose falls under Gb, 1/min on
                                   # (Gb − G). A1b as implemented is one-sided — the liver withholds when high and
                                   # never releases when low (see `hep` below, gated on g > gb) — so below basal the
                                   # whole hepatic response is A9 counter-regulation, whose magnitude is pinned by the
                                   # donors' low DEPTHS (cr_max walked 0.5 -> 0.137 across L 166/272/360/394) and can
                                   # supply only ~2.6 mg/dL per 30 min against the 5 mg/dL recovery gap of L 559-560.
                                   # Glucose autoregulation of hepatic output is bidirectional in the literature
                                   # (Cherrington/Moore: HGP rises as glucose falls, independent of hormones), but
                                   # A1b's own evidence sizes the ABOVE-basal direction only (L 563), so the symmetric
                                   # value 0.0038 is the modelling assumption and the data-fitted range is above it:
                                   # symmetry gives 0.182 mg/kg/min at G 65 against L 589's needed ~0.34.
    sg_h: float = 0.0038           # A1b liver glucose autoregulation, 1/min on (G − Gb) ABOVE Gb only (UVA/Padova T1D kp2;
                                   # absent below Gb in T1D, Mevorach 2000); EGP floored at 0
    f_ii: float = 1.0              # A1c fixed insulin-independent uptake (brain, red cells), mg/kg/min (Best 1981, UVA Fsnc);
    g_ii: float = 81.0             # it falls ∝ G below g_ii (Hovorka 2004 F01c, 4.5 mmol/L), sparing glucose in a low
    kappa_ins: float = 0.0         # experiment (LESSONS 292): 1 = κ follows plasma insulin per Best 1981 (0.24 / 0.68 / 0.78 at low /
                                   # mid / high insulin; mapped [J] to 1 / 3 / 8× basal), scaled by the person's κ / 0.68
    kappa: float = 0.15            # glucose-dependence of insulin-mediated uptake: 1 = Bergman (X·G), 0 = linear (Loop) [J]
    low_prop: bool = True          # below Gb, uptake ∝ G (vanishes with glucose); False only for the linear calibration part
    ex_post: bool = False          # experiment: the exercise sensitivity boost multiplies insulin's action on glucose (after the remote
                                   # compartment, Breton 2008 / Dalla Man 2009) instead of the insulin entering it (40-min p2 lag)
    gb: float = 119.0              # mg/dL, rest point at true basal insulin
    egp_b: float = 2.5             # mg/kg/min at basal insulin
    rthr: float = 180.0            # renal threshold, mg/dL
    rcl: float = 0.003             # renal clearance, 1/min on (G − Rthr)
    # hypoglycaemic risk amplification of insulin-dependent uptake (S2013 / ReplayBG)
    risk_r1: float = 1.4407
    risk_r2: float = 0.8124
    risk_floor: float = 60.0
    risk_lambda: float = 0.0       # S2013 hypo amplification (1 = published). OFF: in this structure it produced
                                   # t<54 8.5% vs the field's 0.13% (ablation 2026-10-15, LESSONS 10)
    # counter-regulation (adrenaline-led in T1D) with HAAF memory
    cr_max: float = 1.0            # mg/kg/min EGP boost at full activation
    cr_g: float = 65.0             # mg/dL, half-activation glucose
    cr_s: float = 5.0              # mg/dL, sigmoid width
    cr_tau: float = 15.0           # min, activation time constant
    cr_tau_off: float = 0.0        # min, DEACTIVATION time constant; 0 = same as cr_tau (one symmetric lag, as before).
                                   # With a single tau the counter-regulatory EGP effect fades as fast as it builds, so
                                   # it peaks just after the nadir and is gone during the climb. The glycogenolytic
                                   # response outlasts the hormone pulse that triggers it (catecholamine and glucagon
                                   # clearance plus post-receptor effects run 20-60 min), so the decay is the slower
                                   # limb. This is the only shape that meets L 600's requirement: shorten the recovery
                                   # limb of an 80-excursion WITHOUT raising its nadir, since the peak value of `cr`
                                   # at the nadir is unchanged - only its persistence into the climb grows.
    haaf_tau_rec: float = 60 * 60.0  # min, recovery of the response
    haaf_kappa: float = math.log(1 / 0.6) / 120.0  # per minute below 54: 2 h → response ×0.6 [J; Dagogo-Jack 1993 thresholds shift within ~24 h]
    haaf_min: float = 0.3
    # gut
    f: float = 0.9                 # bioavailability
    kempt: float = 0.05            # initial (small-meal) emptying rate = Vmax/Km with Km 60 kcal (evidence/09)
    kabs: float = 0.05             # gut absorption; a 25 g snack peaks at ~45 min as the donor pool's small pulses do
    hypo_empty_gain: float = 1.5   # φ_hypo = 1 + gain·σ((70 − G)/5)
    ge_kcal_max: float = 3.0       # Vmax, kcal/min, of saturating gastric emptying E = Vmax·S/(Km + S) with Km = Vmax/kempt
                                   # (0 = off, plain first-order): emptying is energy-rate limited, so a big meal empties
                                   # for hours (Hunt 1985, Brener 1983, Calbet 1997; evidence/09). Vmax 3 is the review's
                                   # central value and the only setting that gives the donors' lognormal glucose (LESSONS 33)
    dose_beta: float = 0.0         # > 0: bolus depots absorb faster when small, rate × (dose / 15 U)^(−β), capped 0.7–3
                                   # (depot surface-to-volume; donors' corrections act 2–3× sooner than the 15-U clamp
                                   # timing at 0.5–3 U, LESSONS 154–155)
    ge_cap_speed: float = 0.0      # 1 = the energy ceiling scales with the energy-weighted speed of the meals in the stomach,
                                   # so a meal's composition (liquid, fibre, viscosity) changes its own Vmax; 0 = one ceiling per
                                   # person, under which per-meal speed vanishes once a meal saturates it (LESSONS 150)
    ge_gamma: float = 0.0          # > 0: power-law emptying instead of Michaelis–Menten: the stomach's energy outflow is
                                   # ge_kcal_max·(S/400 kcal)^γ, capped by each parcel's first-order kempt rate. The absolute
                                   # kcal/min keeps rising with load — doubling the load: ×1.45 (Schirra 1996, γ 0.54),
                                   # +0.72 on 2.5 kcal/min (Hunt 1985, γ ≈ 0.37) — where Km 60 kcal had flattened it to
                                   # ×1.07 above ~300 kcal (LESSONS 53)
    egp_vs: float = 0.0            # > 0: the hepatic insulin signal saturates, in suppression units v = sE·(I − Ib)/Ib:
                                   # v_eff = vs·v / (vs + v). 2.57 puts half suppression at v 0.62 and full at 1.64, the
                                   # 29 / 60 µU/mL of Rizza 1981 (half-max / complete HGO suppression) scaled to the T1D arm,
                                   # so clamp-level insulin no longer drives X_E far past full suppression (LESSONS 192–193)
    p2e_off: float = 0.0           # > 0: X_E's rate when the hepatic signal is falling (insulin withdrawn); p2e stays the onset
                                   # rate (meal tracer nadir, Romeres 2025). Gray 1982 HGO recovery half-times 59 / 119 min
                                   # after 40 / 120 mU/m²/min give 0.012–0.020 through egp_vs (LESSONS 193)
    ge_beta: float = 1.0           # Elashoff 1982 power-exponential emptying: the fraction of a parcel still in the
                                   # stomach is exp(−(k·t)^beta), so the emptying HAZARD is beta·(k·t)^(beta−1) — a
                                   # flatter start and a sharper finish. beta = 1 is the first-order tail this model
                                   # has had, and reproduces it exactly. Measured target (L 591): at a matched 35 g
                                   # the donors' labelled pulses peak at 50 min and decay for 60 (decay/peak 1.21),
                                   # the twins' peak at 37 and decay for 66 (1.44) — they rise too early and trail
                                   # too long, which is the one time-asymmetric shape L 575 asks for.
    ge_beta_cap: float = 4.0       # clip on the hazard multiplier, so a parcel's first minutes cannot empty instantly
    ge_order: int = 2              # number of STOMACH compartments (Erlang transit order). 2 is Dalla Man / UVA-Padova
                                   # and what this model has had; `kempt` is scaled by order / 2 so the MEAN transit
                                   # time is unchanged, and only the transit-time DISPERSION falls. Raising it moves
                                   # the appearance peak LATER and shortens the decay — the one form that meets
                                   # L 615's requirement, where `ge_beta` moved the peak earlier and `meal_lag` was
                                   # shift-invariant. Isolated 35 g parcel, mean held at 40 min: order 2 gives peak
                                   # 40 / decay 94, order 3 gives 44 / 82, order 4 gives 46 / 74, against the donors'
                                   # labelled 50 / 60 and the twins' 43 / 67 (L 617).
    ge_beta_mean: bool = True      # keep the MEAN emptying time while changing its shape: a Weibull's mean is
                                   # Gamma(1 + 1/beta)/k, so k is scaled by that factor. Without it, raising beta also
                                   # empties faster (total pulse 120 -> 98 min against the donors' 125) and the arm
                                   # tests speed as well as shape — which is what wrecked the first ge_beta run (L 591)
    ge_hyper: float = 0.0          # maximal slowing of emptying in hyperglycaemia: rate × (1 − h·(1 − e^(−(G−100)/50)));
                                   # h 0.45 gives ×0.74 at 8 mmol/L (Schvarcz 1997) and ×0.56 at 15–20 (Fraser 1990) [J]
    # exercise
    ex_abs: bool = False           # C1's uptake keyed to absolute work rate, not %VO2-reserve (L 565)
    ex_uptake: float = 0.0         # mg/kg/min insulin-independent uptake at intensity 1
    ex_egp_surge: float = 28.0     # mg/kg/min EGP rise at intensity 1 for anaerobic work, above the 60% threshold; calibrated
                                   # on donors' ≥ 8-MET workouts (rise ≥ 20 during in 46%; LESSONS 247; was 0)

    def scaled(self, **kw) -> "BodyParams":
        return replace(self, **kw)


@dataclass
class Parcel:
    """Carbohydrate (or glucose-equivalent) entering the stomach at minute `t` (+ delay)."""
    t: float
    grams: float
    kempt: float
    kabs: float
    delay: float = 0.0
    f: float = 0.9
    hypo_sensitive: bool = True    # gastric emptying speeds up in hypoglycaemia
    label: str = "meal"
    speed: float = 1.0             # the meal's own emptying-speed factor (composition), seen by the energy ceiling when
                                   # ge_cap_speed is on (LESSONS 150)
    kcal_per_g: float = 4.0        # energy leaving the stomach per gram of this parcel's carbohydrate (fat and protein
                                   # eaten with it included); used only by the energy-rate ceiling
    q: list = field(default_factory=lambda: [0.0, 0.0, 0.0])   # mg/kg in sto1, sto2, gut
    entered: bool = False


@dataclass
class Depot:
    """Subcutaneous insulin from one dose (or the shared basal depot). A fraction `psi` of each
    arrival takes the formulation's fast route (insulins.py) into plasma at `k_fast`."""
    kd: float
    ka2: float
    psi: float = 0.0
    k_fast: float = 0.1
    i1: float = 0.0                # mU/kg
    i2: float = 0.0
    fast: float = 0.0


def sigmoid(x: float) -> float:
    if x > 40: return 1.0
    if x < -40: return 0.0
    return 1.0 / (1.0 + math.exp(-x))


class Body:
    """Integrates the plant minute by minute. Doses enter via `infuse`, meals via `eat`."""

    def __init__(self, p: BodyParams, formulation: str = "lispro"):
        from .insulins import get
        self.p = p
        self.form = get(formulation)
        self.g = p.gb
        self.ip = p.ib * p.vi                # mU/kg
        self.xd = p.si_d * p.ib
        self.xe = 0.0
        self.cr = 0.0
        self.haaf = 1.0
        self.basal = self._depot(1.0)
        self.depots: list[Depot] = []
        self.parcels: list[Parcel] = []
        self.pending: list[tuple[float, float, Depot]] = []   # (minute, mU/kg, depot) not yet arrived (delay τ)
        self.minute = 0.0
        # ground-truth bookkeeping, refreshed every step
        self.ra = 0.0                        # carbohydrate appearance, mg/kg/min
        self.egp = p.egp_b
        self.insulin_absorbed = 0.0          # mU/kg/min into plasma
        self.lost_mu = 0.0                   # mU/kg delivered but never absorbed (site loss)
        self._settle_basal_depot()

    # ------------------------------------------------------------------ setup
    def _depot(self, omega: float) -> Depot:
        p, f = self.p, self.form
        return Depot(p.kd * f.kd_mult * omega, p.ka2 * f.ka2_mult * omega, f.psi, f.k_fast * omega)

    def _settle_basal_depot(self):
        """Fill the basal depot to steady state for plasma insulin Ib."""
        p, d = self.p, self.basal
        u = p.ib * p.vi * p.ke               # mU/kg/min absorbed at steady state
        self.basal.fast = u * d.psi / d.k_fast
        self.basal.i1 = u * (1 - d.psi) / d.kd
        self.basal.i2 = u * (1 - d.psi) / d.ka2

    def prime(self, basal_u_per_h: float):
        """Fill the delivery delay line as if `basal_u_per_h` had been running before minute 0."""
        tau = int(round(self.form.tau))
        for k in range(tau):
            self.pending.append((self.minute + k + 0.5, basal_u_per_h * 1000.0 / 60.0 / self.p.bw, self.basal))

    def basal_rate_u_per_h(self) -> float:
        """The infusion that holds plasma insulin at Ib (the TRUE basal requirement)."""
        p = self.p
        return p.ib * p.vi * p.ke * p.bw * 60.0 / 1000.0

    # ------------------------------------------------------------------ inputs
    def infuse(self, units: float, minute: float, omega: float | None = None, dose: float | None = None):
        """Deliver `units` U at `minute`. A bolus with `omega` gets its own depot with kd, ka2 scaled
        by omega (per-dose absorption variability); otherwise it joins the basal depot. `dose` is the whole bolus the
        units belong to: with dose_beta > 0 its depot absorbs at (dose / 15 U)^(−β), 1 at the 15-U clamp dose the
        timing was fitted to (LESSONS 114, 155)."""
        if units <= 0: return
        p = self.p
        if omega is not None and p.dose_beta > 0 and dose:
            omega *= min(3.0, max(0.7, (max(dose, 0.05) / 15.0) ** (-p.dose_beta)))
        mu = units * 1000.0 / p.bw
        dep = self.basal if omega is None else self._depot(omega)
        if omega is not None and dep not in self.depots: self.depots.append(dep)
        self.pending.append((minute + self.form.tau, mu, dep))

    def eat(self, parcel: Parcel):
        self.parcels.append(parcel)

    # ------------------------------------------------------------------ helpers
    def _sg_excess(self, g: float) -> float:
        """The glucose excess the insulin-INDEPENDENT term acts on (L 637).

        `sg_kappa` 0 keeps the linear `g - gb`. Above 0 it saturates ABOVE Gb at that fraction, exactly as
        `kappa` already does for insulin-mediated uptake (LESSONS 7), and leaves the sub-basal side at full
        strength. That is the shape ice L 140a measured in the donors' learned background force (slope
        -0.17/h below 90 against -0.02/h at 180-250), which no linear -SG*(G - Gb) can produce.
        """
        p = self.p
        if p.sg_km > 0.0:
            return self._sg_F(g) - self._sg_F(p.gb)
        d = g - p.gb
        return d if (d <= 0.0 or p.sg_kappa <= 0.0) else p.sg_kappa * d

    def _sg_F(self, x: float) -> float:
        """Antiderivative of the SMOOTH relative uptake slope (L 641), so the excess is F(G) - F(Gb).

        The slope is 1 below `sg_g0` and 1 / (1 + (x - g0) / km)^2 above it, which is a Michaelis-Menten
        saturation in ABSOLUTE glucose - the form ice's unbiased profile picks (RMS 0.0008 /h against their
        same-span bands, where a kink at Gb reaches 0.0251 and MM anchored at Gb 0.0319). Taking the excess as
        a DIFFERENCE of F keeps the term's zero exactly at Gb however low `sg_g0` sits, so the basal balance
        is untouched; `sg_kappa`'s kink could not place the breakpoint below Gb without moving that zero.
        """
        p = self.p
        if x <= p.sg_g0:
            return x
        d = x - p.sg_g0
        return p.sg_g0 + p.sg_km * d / (p.sg_km + d)

    def risk(self, g: float) -> float:
        p = self.p
        if p.risk_lambda <= 0 or g >= p.gb: return 1.0
        gg = max(g, p.risk_floor)
        r = 10.0 * p.risk_r1 * (math.log(gg) ** p.risk_r2 - math.log(p.gb) ** p.risk_r2) ** 2
        return 1.0 + p.risk_lambda * r

    def plasma_insulin(self) -> float:
        return self.ip / self.p.vi

    def iob_units(self) -> float:
        """Insulin not yet in plasma (subcutaneous + pending), in U. Ground truth for diagnostics."""
        p = self.p
        mu = sum(d.i1 + d.i2 + d.fast for d in [self.basal] + self.depots) \
            + sum(x[1] for x in self.pending)
        return mu * p.bw / 1000.0

    def cob_grams(self) -> float:
        return sum(sum(pc.q) for pc in self.parcels if pc.entered) * self.p.bw / 1000.0 \
            + sum(pc.grams * pc.f for pc in self.parcels if not pc.entered)

    # ------------------------------------------------------------------ dynamics
    def step(self, dt: float = 1.0, si_mult: float = 1.0, egp_mult: float = 1.0,
             ex_intensity: float = 0.0, ex_anaerobic: float = 0.0, ex_si_boost: float = 0.0, ex_work: float = 0.0,
             abs_mult: float = 1.0, bio: float = 1.0, util_drop: float = 0.0, ge_mult: float = 1.0,
             si_d_mult: float = 1.0, cr_mult: float = 1.0):
        """Advance `dt` minutes (explicit midpoint for the fast states; dt ≤ 1 recommended).

        si_mult: product of sensitivity modulators (circadian, daily, cycle, illness, stress,
        exercise after-effect). egp_mult: product of EGP modulators (dawn, illness, stress).
        abs_mult: subcutaneous absorption speed (exercise, heat, site age). bio: fraction of insulin
        arriving at the depot that is absorbed (a failing or leaking site loses the rest).
        ex_intensity ∈ [0, 1]: current exercise intensity above rest; ex_anaerobic ∈ [0, 1]: its
        high-intensity share; ex_si_boost: acute sensitivity increase during exercise (fraction)."""
        p = self.p
        m = self.minute
        # arrivals into the depots
        if self.pending:
            keep = []
            for (tm, mu, dep) in self.pending:
                if tm <= m + dt:
                    mu *= bio
                    self.lost_mu += mu * (1 - bio) / max(bio, 1e-9) if bio < 1 else 0.0
                    dep.fast += mu * dep.psi
                    dep.i1 += mu * (1 - dep.psi)
                else: keep.append((tm, mu, dep))
            self.pending = keep
        # meal parcels entering the stomach
        for pc in self.parcels:
            if not pc.entered and m + dt > pc.t + pc.delay:
                if p.ge_order != 2 and len(pc.q) != p.ge_order + 1:
                    pc.q = [0.0] * (int(p.ge_order) + 1)      # size the transit chain at entry (L 617)
                pc.q[0] += pc.grams * pc.f * 1000.0 / p.bw    # mg/kg
                pc.entered = True

        g = self.g
        phi = 1.0 + p.hypo_empty_gain * sigmoid((70.0 - g) / 5.0)
        if p.ge_hyper > 0 and g > 100.0:
            phi *= 1.0 - p.ge_hyper * (1.0 - math.exp(-(g - 100.0) / 50.0))

        # --- insulin depots (linear, exact exponential update would be overkill at dt=1)
        absorbed = 0.0
        for dep in [self.basal] + self.depots:
            f1 = dep.kd * abs_mult * dep.i1
            f2 = dep.ka2 * abs_mult * dep.i2
            ff = dep.k_fast * abs_mult * dep.fast
            dep.i1 -= dt * f1
            dep.i2 += dt * (f1 - f2)
            dep.fast -= dt * ff
            absorbed += f2 + ff
        self.depots = [d for d in self.depots if d.i1 + d.i2 + d.fast > 1e-6 or any(x[2] is d for x in self.pending)]
        self.ip += dt * (absorbed - p.ke * self.ip)
        self.insulin_absorbed = absorbed
        I = self.ip / p.vi

        # --- gut
        ra = 0.0
        # energy-rate ceiling: the stomach's total outflow (kcal/min) is shared by every parcel in it
        scale = 1.0
        if p.ge_kcal_max > 0:
            kcal = 0.0; wsp = 0.0; wk = 0.0
            for pc in self.parcels:
                if pc.entered:
                    kcal += pc.kempt * (phi if pc.hypo_sensitive else 1.0) * pc.q[len(pc.q) - 2] * p.bw / 1000.0 / max(pc.f, 1e-6) * pc.kcal_per_g
                    w_ = pc.q[len(pc.q) - 2] * pc.kcal_per_g
                    wsp += w_ * pc.speed; wk += w_
            cap = p.ge_kcal_max * phi * ge_mult
            if p.ge_cap_speed > 0 and wk > 0:
                cap *= 1.0 + p.ge_cap_speed * (wsp / wk - 1.0)
            if p.ge_gamma > 0:
                load = sum(sum(pc.q[:-1]) * p.bw / 1000.0 / max(pc.f, 1e-6) * pc.kcal_per_g for pc in self.parcels if pc.entered)
                allowed = cap * (max(load, 1e-9) / 400.0) ** p.ge_gamma
                scale = min(1.0, allowed / kcal) if kcal > 0 else 1.0
            else:
                scale = cap / (cap + kcal)     # saturating (Michaelis–Menten in energy): ~first-order for small meals, toward cap for big
        for pc in self.parcels:
            if not pc.entered: continue
            ke_ = pc.kempt * (phi if pc.hypo_sensitive else 1.0) * (ge_mult if pc.kcal_per_g > 0 else 1.0)
            if p.ge_beta != 1.0:                     # Elashoff power-exponential: hazard beta·(k·age)^(beta−1)
                age = max(m - pc.t - pc.delay, dt)
                kb = pc.kempt * (math.gamma(1.0 + 1.0 / p.ge_beta) if p.ge_beta_mean else 1.0)
                ke_ *= min(p.ge_beta_cap, p.ge_beta * (kb * age) ** (p.ge_beta - 1.0)) * (kb / pc.kempt)
            n_ = len(pc.q) - 1                      # stomach stages; the last entry is the gut
            if n_ > 1: ke_ *= n_ / 2.0                 # keep the mean transit time as order rises (L 617)
            fl = [ke_ * pc.q[i] for i in range(n_)]
            fl[n_ - 1] *= scale                        # the energy ceiling applies to the final emptying step
            a = pc.kabs * pc.q[n_]
            q_ = list(pc.q)
            q_[0] -= dt * fl[0]
            for i in range(1, n_): q_[i] += dt * (fl[i - 1] - fl[i])
            q_[n_] += dt * (fl[n_ - 1] - a)
            pc.q = q_
            ra += a
        if len(self.parcels) > 8:
            self.parcels = [pc for pc in self.parcels if not pc.entered or sum(pc.q) > 1e-3]
        self.ra = ra

        # --- insulin action
        si = p.si_d * si_mult * si_d_mult * (1.0 + (0.0 if p.ex_post else ex_si_boost))   # si_d_mult: peripheral disposal only (LESSONS 410)
        self.xd += dt * p.p2 * (si * I - self.xd)
        se = p.se * si_mult
        u_h = (I - p.ib) / p.ib
        if p.egp_vs > 0 and u_h > 0 and p.se > 0:
            v_h = p.se * u_h; u_h = p.egp_vs * v_h / (p.egp_vs + v_h) / p.se
        r_e = p.p2e_off if (p.p2e_off > 0 and u_h < self.xe) else p.p2e
        self.xe += dt * r_e * (u_h - self.xe)
        egp_ins = p.egp_b * egp_mult * min(max(1.0 - se * self.xe, 0.0), 1.0 + se)

        # --- counter-regulation and HAAF memory
        target = p.cr_max * self.haaf * cr_mult * sigmoid((p.cr_g - g) / p.cr_s)
        tau_cr = p.cr_tau if (target >= self.cr or p.cr_tau_off <= 0) else p.cr_tau_off   # slower OFF limb (L 601)
        self.cr += dt * (target - self.cr) / tau_cr
        below = 1.0 if g < 54.0 else 0.0
        self.haaf += dt * ((1.0 - self.haaf) / p.haaf_tau_rec - p.haaf_kappa * below * self.haaf)
        self.haaf = max(p.haaf_min, min(1.0, self.haaf))

        # A1b below basal (L 596). Hepatic glucose output is INSULIN-SUPPRESSED, so the autoregulatory increase
        # carries the same suppression factor as basal EGP (L 599): at full strength it acted on the way INTO a low,
        # while insulin was still high, and so prevented lows instead of shortening them (counts 1.00 -> 0.75).
        # Suppressed, it is quiet while IOB is high and acts once insulin has fallen, which is the low itself.
        hep_lo = 0.0
        if p.sg_h_lo > 0:
            hep_lo = p.sg_h_lo * p.vg * max(p.gb - g, 0.0)
            if p.sg_h_lo_ins: hep_lo *= min(max(1.0 - se * self.xe, 0.0), 1.0 + se)
        egp = egp_ins + self.cr + hep_lo + p.ex_egp_surge * ex_intensity * ex_anaerobic
        self.egp = egp
        uex = p.ex_uptake * (ex_work if p.ex_abs else ex_intensity) * g / p.gb   # mass action: fades as glucose falls (evidence/10 §7.3)
        renal = p.rcl * (g - p.rthr) if g > p.rthr else 0.0
        # insulin-mediated uptake's glucose dependence: weak above Gb (κ), proportional below it so
        # uptake vanishes with glucose (Bergman / UVA Michaelis–Menten at low G; LESSONS 7)
        kap = p.kappa
        if p.kappa_ins > 0:
            r_ = I / p.ib
            kr = 0.24 if r_ <= 1.0 else 0.24 + 0.44 * (r_ - 1.0) / 2.0 if r_ <= 3.0 else 0.68 + 0.10 * min(r_ - 3.0, 5.0) / 5.0
            kap = p.kappa * kr / 0.68
        mm = p.gb + kap * (g - p.gb) if (g >= p.gb or not p.low_prop) else g
        xact = self.xd * (1.0 + ex_si_boost) if p.ex_post else self.xd
        if p.ge_split:
            hep = min(p.sg_h * p.vg * (g - p.gb), max(egp, 0.0)) if g > p.gb else 0.0     # mg/kg/min the liver withholds
            spare = p.f_ii * (1.0 - g / p.g_ii) if g < p.g_ii else 0.0                    # mg/kg/min the brain no longer takes
            ge = p.sg_p * (g - p.gb) + (hep - spare) / p.vg
        elif p.ge_spare:
            # A1c alone on the lumped SG (LESSONS 561): the fixed insulin-independent uptake falls with glucose below
            # g_ii (Best 1981 ~1 mg/kg/min; Hovorka 2004 F01c falls ∝ G below 4.5 mmol/L), which is the only part of
            # the L 548 split aimed at the shallow-low recovery gap of L 559-560. The rest of the split stays off, so
            # the liver's support below Gb is not removed — that is what made the full split add lows.
            ge = p.sg * self._sg_excess(g) - (p.f_ii * (1.0 - g / p.g_ii) if g < p.g_ii else 0.0) / p.vg
        else:
            ge = p.sg * self._sg_excess(g)
        dg = (-ge - (xact * mm * self.risk(g) - p.si_d * p.ib * p.gb)
              + (egp - p.egp_b - uex + ra + util_drop) / p.vg - renal)
        self.g = max(10.0, g + dt * dg)
        self.minute = m + dt
