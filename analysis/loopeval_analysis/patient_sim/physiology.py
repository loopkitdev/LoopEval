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
    p2: float = 0.025              # 1/min, disposal-action rate from the lispro clamp fit (GIR peak ~100 min, 50% by ~140; LESSONS 9).
                                   # Not Loop's curve: the body follows evidence about patients (Pete 2026-10-17; LESSONS 114)
    si_d: float = 5.0e-4           # disposal sensitivity, 1/min per (mU/L)  — calibrated to ISF
    p2e: float = 0.006             # 1/min, EGP-suppression action rate (Pete 2026-10-17, LESSONS 131: post-meal EGP nadir depth
                                   # 0.54 vs the Romeres 2025 tracer's 0.56; 0.010 gave 0.41). T1D meal EGP suppression is
                                   # sustained with its nadir at ~160 min (Romeres 2025); ReplayBG prior 0.008 (LESSONS 70, 75)
    se: float = 1.0                # EGP suppression per unit relative insulin above basal
    ib: float = 10.0               # basal plasma insulin, mU/L — set from the true basal rate
    # glucose
    vg: float = 1.88               # dL/kg (UVA/Padova; ReplayBG's 1.45 gives ~2x the carb sensitivity people's settings imply)
    sg: float = 0.003              # insulin-INDEPENDENT glucose effectiveness, 1/min (see COMPONENTS: physiology)
    kappa: float = 0.15            # glucose-dependence of insulin-mediated uptake: 1 = Bergman (X·G), 0 = linear (Loop) [J]
    low_prop: bool = True          # below Gb, uptake ∝ G (vanishes with glucose); False only for the linear calibration part
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
    ge_cap_speed: float = 0.0      # 1 = the energy ceiling scales with the energy-weighted speed of the meals in the stomach,
                                   # so a meal's composition (liquid, fibre, viscosity) changes its own Vmax; 0 = one ceiling per
                                   # person, under which per-meal speed vanishes once a meal saturates it (LESSONS 150)
    ge_gamma: float = 0.0          # > 0: power-law emptying instead of Michaelis–Menten: the stomach's energy outflow is
                                   # ge_kcal_max·(S/400 kcal)^γ, capped by each parcel's first-order kempt rate. The absolute
                                   # kcal/min keeps rising with load — doubling the load: ×1.45 (Schirra 1996, γ 0.54),
                                   # +0.72 on 2.5 kcal/min (Hunt 1985, γ ≈ 0.37) — where Km 60 kcal had flattened it to
                                   # ×1.07 above ~300 kcal (LESSONS 53)
    ge_hyper: float = 0.0          # maximal slowing of emptying in hyperglycaemia: rate × (1 − h·(1 − e^(−(G−100)/50)));
                                   # h 0.45 gives ×0.74 at 8 mmol/L (Schvarcz 1997) and ×0.56 at 15–20 (Fraser 1990) [J]
    # exercise
    ex_uptake: float = 0.0         # mg/kg/min insulin-independent uptake at intensity 1
    ex_egp_surge: float = 0.0      # mg/kg/min EGP rise at intensity 1 for anaerobic work

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
    def infuse(self, units: float, minute: float, omega: float | None = None):
        """Deliver `units` U at `minute`. A bolus with `omega` gets its own depot with kd, ka2 scaled
        by omega (per-dose absorption variability); otherwise it joins the basal depot."""
        if units <= 0: return
        p = self.p
        mu = units * 1000.0 / p.bw
        dep = self.basal if omega is None else self._depot(omega)
        if omega is not None and dep not in self.depots: self.depots.append(dep)
        self.pending.append((minute + self.form.tau, mu, dep))

    def eat(self, parcel: Parcel):
        self.parcels.append(parcel)

    # ------------------------------------------------------------------ helpers
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
             ex_intensity: float = 0.0, ex_anaerobic: float = 0.0, ex_si_boost: float = 0.0,
             abs_mult: float = 1.0, bio: float = 1.0):
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
                    kcal += pc.kempt * (phi if pc.hypo_sensitive else 1.0) * pc.q[1] * p.bw / 1000.0 / max(pc.f, 1e-6) * pc.kcal_per_g
                    w_ = pc.q[1] * pc.kcal_per_g
                    wsp += w_ * pc.speed; wk += w_
            cap = p.ge_kcal_max * phi
            if p.ge_cap_speed > 0 and wk > 0:
                cap *= 1.0 + p.ge_cap_speed * (wsp / wk - 1.0)
            if p.ge_gamma > 0:
                load = sum((pc.q[0] + pc.q[1]) * p.bw / 1000.0 / max(pc.f, 1e-6) * pc.kcal_per_g for pc in self.parcels if pc.entered)
                allowed = cap * (max(load, 1e-9) / 400.0) ** p.ge_gamma
                scale = min(1.0, allowed / kcal) if kcal > 0 else 1.0
            else:
                scale = cap / (cap + kcal)     # saturating (Michaelis–Menten in energy): ~first-order for small meals, toward cap for big
        for pc in self.parcels:
            if not pc.entered: continue
            ke_ = pc.kempt * (phi if pc.hypo_sensitive else 1.0)
            s1, s2, gut = pc.q
            e1 = ke_ * s1; e2 = ke_ * s2 * scale; a = pc.kabs * gut
            pc.q = [s1 - dt * e1, s2 + dt * (e1 - e2), gut + dt * (e2 - a)]
            ra += a
        if len(self.parcels) > 8:
            self.parcels = [pc for pc in self.parcels if not pc.entered or sum(pc.q) > 1e-3]
        self.ra = ra

        # --- insulin action
        si = p.si_d * si_mult * (1.0 + ex_si_boost)
        self.xd += dt * p.p2 * (si * I - self.xd)
        self.xe += dt * p.p2e * ((I - p.ib) / p.ib - self.xe)
        se = p.se * si_mult
        egp_ins = p.egp_b * egp_mult * min(max(1.0 - se * self.xe, 0.0), 1.0 + se)

        # --- counter-regulation and HAAF memory
        target = p.cr_max * self.haaf * sigmoid((p.cr_g - g) / p.cr_s)
        self.cr += dt * (target - self.cr) / p.cr_tau
        below = 1.0 if g < 54.0 else 0.0
        self.haaf += dt * ((1.0 - self.haaf) / p.haaf_tau_rec - p.haaf_kappa * below * self.haaf)
        self.haaf = max(p.haaf_min, min(1.0, self.haaf))

        egp = egp_ins + self.cr + p.ex_egp_surge * ex_intensity * ex_anaerobic
        self.egp = egp
        uex = p.ex_uptake * ex_intensity * g / p.gb          # mass action: fades as glucose falls (evidence/10 §7.3)
        renal = p.rcl * (g - p.rthr) if g > p.rthr else 0.0
        # insulin-mediated uptake's glucose dependence: weak above Gb (κ), proportional below it so
        # uptake vanishes with glucose (Bergman / UVA Michaelis–Menten at low G; LESSONS 7)
        mm = p.gb + p.kappa * (g - p.gb) if (g >= p.gb or not p.low_prop) else g
        dg = (-p.sg * (g - p.gb) - (self.xd * mm * self.risk(g) - p.si_d * p.ib * p.gb)
              + (egp - p.egp_b - uex + ra) / p.vg - renal)
        self.g = max(10.0, g + dt * dg)
        self.minute = m + dt
