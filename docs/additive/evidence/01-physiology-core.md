# 01 — Physiology core and parameter priors

Scope: the deterministic physiology of the virtual T1D patient (insulin PK/PD, glucose
production and disposal, renal loss, counter-regulation, insulin-sensitivity rhythms and noise,
carbohydrate/fat/protein absorption). Behavior (meal timing, carb-count error, rescue habits,
pump/site failures) and CGM error are separate evidence files.

Marking: **[unverified]** = value or citation detail recalled, or taken from a secondary source,
and not checked against the primary paper in this review. Everything else was read in the primary
source, its full text on PMC, or in the reference implementation's code (simglucose, py_replay_bg,
Tidepool data-science-models), on 2026-10-15.

---

## 1. Recommendation

**Use a ReplayBG/Hovorka hybrid of about 11–13 states.** Its spine is the identifiable
minimal-model core of ReplayBG (Cappon 2023). On top of that sit three nonlinear terms that matter
where t<54 lives: an EGP floor with insulin suppression (Hovorka), renal excretion above about
180 mg/dL, and a counter-regulatory EGP term below about 65 mg/dL that HAAF can blunt.
Insulin sensitivity varies by time of day, day to day and slowly over time. The gut has a
fat/protein slow channel.

### 1.1 Why this level

| Need | Loop effect model / Tidepool SMM | Bergman minimal | **Recommended hybrid** | UVA/Padova S2013/S2017 |
|---|---|---|---|---|
| Plant ≠ controller structure (no circularity) | ✗ SMM is the same ISF/CR-linear superposition the controller assumes | ✓ | ✓ | ✓ |
| EGP floor / homeostatic pull when insulin is withdrawn | ✗ (BG drifts unboundedly) | partial (SG·Gb) | ✓ | ✓ |
| Glucose-dependent disposal (low BG = slower fall) | ✗ | ✓ | ✓ | ✓ (Michaelis–Menten) |
| Renal loss above about 180 | ✗ | ✗ | ✓ | ✓ |
| Hypoglycaemia physiology | ✗ | ✗ | ✓ (counter-reg + HAAF + faster gastric emptying) | ✓ (risk function + glucagon) |
| SC insulin PK with a realistic tail | biexponential (Palerm) | ✗ | ✓ 2-comp + delay | ✓ |
| Circadian SI and dawn | schedule only | ✗ | ✓ | ✓ (S2017) |
| Parameters identifiable from CGM + pump + carbs | n/a | ✓ (SI, SG, p2) | ✓ about 8–12 per person (ReplayBG shows it) | ✗ (about 30 params; Bayesian population priors only) |
| Open, inspectable | ✓ | ✓ | ✓ | ✗ (T1DMS is licensed; simglucose = public S2008 subset) |

The deciding argument is the error budget. Over-parameterised physiology (UVA/Padova's two-pool
glucose kinetics, hepatic insulin extraction, glucagon kinetics) cannot be identified from
real-world data. It therefore adds parameters that come from priors, not from the donor, and its
fidelity gains are small next to carb-count error, meal-timing error and day-to-day SI variability
(CV 17–31%, §5.2). Some parts of the model decide the low tail, though: the EGP floor, saturating
disposal, the insulin-action tail and the counter-regulation and rescue-carb kinetics. A purely
linear model (Loop's effect model, Tidepool's SimpleMetabolismModel) gets those wrong in the
direction that flatters or punishes hypo-prevention candidates.

### 1.2 Model equations (recommended)

Units: G mg/dL; insulin mU/kg; rates per minute; BW kg.

**Subcutaneous insulin.** Two-compartment model with a delay (S2017/Schiavon 2018 structure;
ReplayBG drops ka1):
```
dIsc1/dt = -kd·Isc1 + u(t − τ_ins)·ω_bolus          (u = delivered insulin, mU/kg/min)
dIsc2/dt =  kd·Isc1 − ka2·Isc2
dIp/dt   =  ka2·Isc2 − ke·Ip                        (Ip plasma insulin, mU/kg)
I        =  Ip / VI
```
`ω_bolus` is a per-bolus absorption factor that scales kd and ka2 jointly, drawn from a lognormal
distribution (§3.4).

**Insulin action.** Two remote effects. The time constants differ, and EGP suppression is the arm
that produces the floor:
```
dX_D/dt = -p2·X_D + p2·SI_D(t)·(I − Ib)     (disposal, as in ReplayBG / Bergman)
dX_E/dt = -p2E·X_E + p2E·SI_E(t)·I          (hepatic suppression, Hovorka x3-style)
```

**Glucose.** One plasma compartment. ReplayBG and Kanderian show that one compartment is enough
for CGM-scale fidelity.
```
dG/dt = −SG·(G − Gb)·[G≥Gs]  − X_D·G·risk(G)
        + [EGP(t) − EGP_b] / VG
        + f·Ra_meal(t) / VG
        − E_renal(G)
EGP(t) = EGP_b·c_dawn(t)·max(0, 1 − X_E) + CR(G, h_HAAF)
E_renal(G) = Rcl·(G − Rthr)  if G > Rthr, else 0
```
`risk(G)` is the S2013/ReplayBG hypoglycaemic amplification of insulin-dependent uptake: ×1.9 at
80 mg/dL and ×3.6 at ≤60 mg/dL at the published defaults. It has a scale λ_risk calibrated jointly
with CR (§4.5).

`CR` is a counter-regulatory EGP boost below a threshold. `h_HAAF` is a memory state that
attenuates it after recent lows (§4.4).

**Gut.** Dalla Man three-compartment model with linear emptying (ReplayBG form), plus a
fat/protein slow channel (§6):
```
dQsto1/dt = −kgri·Qsto1 + D_fast(t − β)
dQsto2/dt = −kempt·φ_hypo(G)·φ_fat·Qsto2 + kgri·Qsto1
dQgut/dt  = −kabs·Qgut + kempt·φ_hypo(G)·φ_fat·Qsto2
dQslow/dt = −k_slow·Qslow + D_slow(t − β_slow)       (protein-derived glucose + fat tail)
Ra_meal   = kabs·Qgut + k_slow·Qslow
```

**State count:** Isc1, Isc2, Ip, X_D, X_E, G, Qsto1, Qsto2, Qgut, Qslow, h_HAAF, plus 1–2
stochastic SI states (OU) = **12–13**. CGM interstitial lag (1 state) belongs to the sensor model.

### 1.3 Prior table (adult; per-person draw, then within-person noise)

| Parameter | Prior (population) | Source |
|---|---|---|
| kd | lognormal, median 0.030 min⁻¹ (log-mean −3.509, log-sd 0.619) | ReplayBG code (`logpriors_t1d.py`) |
| ka2 | lognormal, median 0.0137 min⁻¹ (−4.288, 0.427), constraint ka2 < kd | ReplayBG code |
| ke | 0.127 min⁻¹ fixed (Hovorka/Wilinska: N(0.14, 0.035²)) | ReplayBG; Wilinska 2010 |
| VI | 0.12–0.135 L/kg (Wilinska N(0.12, 0.012²)) | ReplayBG; Wilinska 2010 |
| τ_ins (delay) | 8 min (lispro/aspart); about 2–5 min less for Fiasp/Lyumjev (§3.2) | ReplayBG default; Linnebjerg 2020; Heise 2017 |
| p2 | √p2 ~ N(0.11, 0.004²) → p2 ≈ 0.0121 min⁻¹ | ReplayBG code |
| SI_D·VG | Gamma(shape 3.3, scale 5e-4) → mean 1.65e-3 | ReplayBG code |
| SG | lognormal(−3.8, 0.5) → median 0.022 min⁻¹ | ReplayBG code |
| Gb | N(119, 7.1²) truncated [70, 180] mg/dL | ReplayBG code |
| VG | 1.45 dL/kg (ReplayBG); Wilinska lnN(ln 0.15 L/kg, 0.23²) | ReplayBG; Wilinska 2010 |
| EGP_b | 2.5 ± 0.33 mg/kg/min (simglucose adults); Wilinska 16.9 µmol/kg/min ≈ 3.0 mg/kg/min | simglucose params; Wilinska 2010 |
| Rthr | N(9, 1.5²) mmol/L = 162 ± 27 mg/dL (UVA: ke2/VG ≈ 339/1.85 ≈ 183 mg/dL) | Wilinska 2010; simglucose |
| Rcl | 0.003 min⁻¹ (Hovorka) [unverified]; UVA ke1 = 0.0005 min⁻¹ on Gp (mg/kg) | Hovorka 2004 [unverified]; simglucose |
| kempt | lognormal median 0.14 min⁻¹ (−1.965, 0.707) | ReplayBG code |
| kabs | lognormal median 0.0043 min⁻¹ (−5.459, 1.440), < kempt; per meal slot | ReplayBG code |
| β (meal delay) | U(0, 60) min | ReplayBG code |
| f (bioavailability) | 0.9; Wilinska U(0.7, 1.2) + 20% inter-occasion | Dalla Man 2007; Wilinska 2010 |
| risk r1, r2 | 1.4407, 0.8124; Gth = 60 mg/dL | ReplayBG `model_parameters_t1d.py`; Dalla Man 2014 |
| Circadian SI | Visentin 7-class piecewise profile, low = 0.4 × high, ×N(1, 0.2) | Visentin 2015 |
| Dawn | EGP ramp 03:00→07:00, about +1.5 mg/kg/min peak, ≈ +30 mg/dL uncompensated, present in about 40–50% of people | Visentin 2018 (citing Mallad 2015); prevalence §5.1 |
| Day-to-day SI | lognormal per-day multiplier, CV about 15–20% (whole day), about 30% overnight | Ruan 2016 (calibration target) |

The p2E, SI_E, counter-regulation and fat/protein-channel priors are in §4 and §6. They have no
good identification data, so they carry wide priors and are flagged as the physiology layer's
largest open uncertainties.

---

## 2. Candidate model families

### 2.1 Bergman minimal model (1979)
- **States:** 2 (G, X), plus insulin as a forcing input. dG/dt = −(SG + X)G + SG·Gb;
  dX/dt = −p2X + p3(I − Ib); SI = p3/p2. Typical SG ~0.01–0.03 min⁻¹ and p2 ~0.01–0.03 min⁻¹
  [unverified, from the IVGTT literature].
- **Captures:** glucose effectiveness (the pull back to Gb) and delayed insulin action.
- **Misses:** EGP floor or suppression as a separate arm, SC PK, gut, renal, hypo physiology.
- **Identifiability:** excellent. This is why ReplayBG and Kanderian build on it.
- Bergman RN, Ider YZ, Bowden CR, Cobelli C. Am J Physiol 1979;236:E667–E677.
  doi:10.1152/ajpendo.1979.236.6.E667.

### 2.2 Hovorka / Cambridge (2004) and Wilinska (2010) simulation environment
- **States:** about 11. Q1/Q2 two-pool glucose, three insulin actions x1 (transport), x2
  (disposal) and x3 (EGP suppression), S1/S2 SC insulin, I plasma, G1/G2 gut, plus the CGM
  compartment.
- **Key nonlinearities** (Hovorka 2004 [values unverified against the PDF; widely reproduced]):
  - F01c = F01 if G ≥ 4.5 mmol/L, else F01·G/4.5. This is non-insulin-dependent uptake, mostly
    brain, and it falls away in hypoglycaemia.
  - FR = 0.003·(G − 9)·VG mmol/min when G > 9 mmol/L.
  - EGP = EGP0·(1 − x3), floored at 0. Verified as EGP0·(1 + x3) with sign convention in
    Wilinska 2010's appendix.
- **Classic point values** [unverified]: EGP0 0.0161 mmol/kg/min; F01 0.0097 mmol/kg/min;
  k12 0.066 min⁻¹; ka1/ka2/ka3 0.006/0.06/0.03 min⁻¹; SIT/SID/SIE 51.2e-4/8.2e-4/520e-4;
  tmaxI 55 min; ke 0.138 min⁻¹; VI 0.12 L/kg; VG 0.16 L/kg; tmaxG 40 min; AG 0.8.
- **Wilinska 2010 virtual population** (verified, PMC2825634):
  - 18 subjects.
  - Means estimated from clinical data: F01 11.1 µmol/kg/min; EGP0 16.9; k12 0.060;
    SIT 18.41e-4; SID 5.05e-4; SIE 0.019; kb1/kb2/kb3 0.0034/0.056/0.024.
  - Sampled priors: VG lnN(ln 0.15, 0.23²); Rthr N(9, 1.5²) mmol/L; VI N(0.12, 0.012²);
    ka N(0.018, 0.0045²) min⁻¹ (≈ tmaxI 55 min); ke N(0.14, 0.035²); Bio U(70, 120)% with 20%
    inter-occasion variability; 1/tmaxG lognormal around exp(−3.689) → tmaxG ≈ 40 min.
  - The gut has an absorption ceiling UG_ceil ~ U[0.02, 0.035] mmol/kg/min.
  - **Intra-subject variability:** "sinusoidal oscillations of 5% amplitude and 3 h period" on
    F01, EGP0, k12, SID, SIE, SIT, kb1–3, ke and ka_int, each with a random phase.
  - Population TDD 0.35 ± 0.14 U/kg/day; ICR 1.7 ± 1.0 U/10 g.
  - The printed Rcl spread, N(0.01, 0.025²), looks garbled in extraction [unverified].
- **Captures:** the separate EGP arm with a floor, renal loss, and brain uptake that falls in hypo.
  Simple gut.
- **Misses:** glucagon/adrenaline and circadian SI. Its intra-subject variability is a crude
  5%/3 h sinusoid, much smaller than the measured day-to-day CV (§5.2).
- Hovorka R et al. Physiol Meas 2004;25:905–920. doi:10.1088/0967-3334/25/4/010.
- Wilinska ME, Chassin LJ, Acerini CL, Allen JM, Dunger DB, Hovorka R. J Diabetes Sci Technol
  2010;4(1):132–144. doi:10.1177/193229681000400117 [DOI unverified; citation verified].
- Hovorka R et al. Am J Physiol Endocrinol Metab 2002;282:E992–E1007 (three-action partition)
  [unverified].

### 2.3 UVA/Padova S2008 → S2013 → S2017
- **S2008** (Kovatchev 2009; Dalla Man 2007 meal model): 13 states.
  - Glucose Gp/Gt; insulin Ip/Il with hepatic extraction; EGP with XL/I′ delays; X;
    Qsto1/Qsto2/Qgut; Isc1/Isc2; Gs.
  - Accepted by the FDA (2008) as a substitute for animal trials for AP preclinical testing.
  - Uid = (Vm0 + Vmx·X)·Gt/(Km0 + Gt), Michaelis–Menten.
  - Renal E = ke1·(Gp − ke2) for Gp > ke2.
- **simglucose** (open Python, Jinyu Xie) implements the public S2008 parameters for 30 virtual
  patients (10 adolescents, 10 adults, 10 children). Code inspected: there is **no** hypoglycaemia
  risk term, no glucagon and no circadian SI.
  - Adult means ± SD from `vpatient_params.csv`: BW 86 ± 17 kg; Gb 143 ± 6 mg/dL;
    EGPb 2.51 ± 0.33 mg/kg/min; Vg 1.85 ± 0.14 dL/kg; Vmx 0.054 ± 0.032; Km0 237 ± 22; Vm0 4.9 ± 1.9;
    p2u 0.034 ± 0.011; kp1 4.6 ± 1.0; kp2 0.0042; kp3 0.0095 ± 0.0056; ki 0.0084;
    ke1 0.0005; ke2 339 mg/kg.
  - Gut: kmax 0.039 ± 0.011; kmin 0.0074 ± 0.004; kabs 0.21 ± 0.21; b 0.79; d 0.18; f 0.9.
  - SC insulin: kd 0.0159 ± 0.002; ka1 0.0034 ± 0.0008; ka2 0.0159 ± 0.0045.
  - A 30-subject population is too small and too homogeneous (Gb 135–153) to stand in for a
    real-world cohort.
- **S2013** (Dalla Man 2014; verified equations, PMC4454102): 17 states.
  - **Hypoglycaemia:** insulin-dependent utilisation is *amplified* below Gb:
    Uid = [Vm0 + Vmx·X·(1 + r1·risk)]·Gt/(Km0 + Gt), with risk = 10·[ln(G)^r2 − ln(Gb)^r2]² for
    60 ≤ G < Gb, frozen below Gth = 60 mg/dL.
  - **Glucagon:** secretion SRH = static + dynamic. The static part is driven by (Gth − G)/(I + 1)
    below Gb; the dynamic part is δ·max(−dG/dt, 0). Plasma glucagon kinetics H. Action on EGP via
    XH (EGP = kp1 − kp2·Gp − kp3·XL + ξ·XH). SC glucagon compartments are included.
  - Population mean Gb is 120 mg/dL. Numerical values for r1, r2, glucagon and the rest are not in
    the paper text (they are sampled from undisclosed joint distributions). ReplayBG publishes
    r1 = 1.4407 and r2 = 0.8124.
- **S2017** (Visentin 2018; verified, PMC5851236):
  - Time-varying SI through kp3 (hepatic) and Vmx (peripheral), using the Visentin 2015 seven-class
    profiles.
  - Dawn: kp1 ramps linearly 03:00–07:00 and kir decreases, built from Mallad 2015 ("almost
    30 mg/dL increase in glucose concentration from 3:00 am to 7:00 am", EGP up about
    1.5 mg/kg/min).
  - Faster analogues via a SC delay τ (Schiavon 2018, n = 116).
  - Over-basal glucose peaks after breakfast, lunch and dinner (adults): 68 ± 30, 54 ± 27 and
    53 ± 25 mg/dL. Breakfast CR 16.9 ± 7.9 g/U.
- **Identifiability:** population priors only. Visentin 2016 "one-day Bayesian cloning" identifies
  a subset per subject from one rich (tracer) day.
- **Verdict:** use as a *source of structure and priors* (risk function, dawn ramp, delay τ, SI
  classes), not as the core.

### 2.4 ReplayBG (Cappon 2023)
- Code inspected (`py_replay_bg/model/*.py`). **9 states:** G, X, Qsto1, Qsto2, Qgut, Isc1, Isc2,
  Ip, IG (CGM).
  - Bergman glucose: dG = SG(Gb − G) − risk·X·G + f·kabs·Qgut/VG.
  - Insulin action: X with p2·(SI/VI)·(Ip − Ipb).
  - The S2013 risk function is kept.
  - Linear gastric emptying: kgri = kempt.
  - SC PK: kd, ka2 (ka1 = 0); ke 0.127; VI 0.135; τ 8 min.
- **Identified per subject by MCMC:** Gb, SG, p2, ka2, kd, kempt, SI (or SI_B/SI_L/SI_D with
  switches at 04:00/11:00/17:00), kabs and β per meal type (breakfast, lunch, dinner, snack,
  hypotreatment). Priors are in §1.3.
- **Intended use:** "digital twin" replay of alternative therapies on real CGM/insulin/meal data.
  This is LoopEval's use case, which makes ReplayBG the closest published methodological
  precedent.
- **Gaps for our use:** no EGP floor (SG·(Gb − G) is symmetric and unbounded), no renal loss, no
  counter-regulation, no fat/protein channel, no day-to-day SI noise (one twin is a fixed
  parameter set over the window).
- Cappon G, Vettoretti M, Sparacino G, Del Favero S, Facchinetti A. IEEE Trans Biomed Eng
  2023;70(11):3105–3115. doi:10.1109/TBME.2023.3286856.

### 2.5 Kanderian / Medtronic virtual patient (Kanderian 2009)
- **States:** 4, plus 2 for a gamma-shaped meal Ra:
  - dIsc = −Isc/τ1 + ID/(τ1·CI)
  - dIp = (Isc − Ip)/τ2
  - dIEFF = −p2·IEFF + p2·SI·Ip
  - dG = −(GEZI + IEFF)·G + EGP + RA
  - RA = CH/VG·t·e^(−t/τm)/τm²
- **8 identifiable parameters per subject.** From the per-subject ranges (n = 10): τ1 41–131 min;
  τ2 10–70 min; CI 540–2010 mL/min; p2 0.0081–0.0233 min⁻¹. Meal τm (mean ± SEM) 47 ± 5
  (breakfast), 55 ± 6 (lunch), 74 ± 19 (dinner), 78 ± 17 (snack); supplemental carbs 31 ± 10 min.
- **Intraday SI, GEZI and EGP variation** was "substantial" in 7 of 10 subjects. SI ratios between
  windows ranged from about 0.4× to about 2.9×.
- **Verdict:** confirms that a single-compartment glucose model with a 2-compartment SC chain fits
  closed-loop data (R² 0.93), and that SI must vary within the day.
- Kanderian SS, Weinzimer S, Voskanyan G, Steil GM. J Diabetes Sci Technol 2009;3(5):1047–1057.
  doi:10.1177/193229680900300508.

### 2.6 Tidepool SimpleMetabolismModel (`tidepool-org/data-science-models`, read 2026-10-15)
- Linear superposition of per-event effect curves on BG. There are no physiological states.
- **Insulin ("Palerm"):** activity = (e^(−t/τ2) − e^(−t/τ1))/(τ2 − τ1). ΔBG = −ISF·cumulative
  activity; IOB = dose − cumulative.
  - τ1/τ2 = 55/70 min (rapid adult; activity peak ≈ 62 min), 50/65 (child), 35/45 (Fiasp; peak
    ≈ 40 min), with regular, NPH and long-acting entries.
- **Carbs ("Cescon"):** ΔBG = (ISF/CIR)·C·(1 − e^(−(t−θ)/τ))·H(t − θ), θ = 20 min. τ comes from a
  lookup on absorption time (180 min → τ = 34 min), so absorption is *first-order, front-loaded*:
  maximal rate right after 20 min.
- **"EGP":** the patient's *true basal schedule* is the EGP equivalent. Each step feeds the
  metabolism model with delivered − true-basal insulin. A "Type2InsulinModel" pancreas term exists
  and is zero for T1D.
- **Nonlinearities:** none. BG is unbounded below, with no EGP floor, renal term, counter-regulation
  or SI noise apart from schedule entries. The patient's ISF/CIR define the plant, so the plant has
  the *same structure* as Loop's own forecast. A controller evaluated on it is tested against its
  own model class.
- Code nit: `if insulin_model_name == 'Palerm' or 'palerm'` is always true. Harmless.
- **Verdict:** this is the baseline to beat, and it cannot represent the low-tail physiology that
  decides t<54.

### 2.7 Comparison summary

| Model | States | Identifiable from CGM/pump/carbs | EGP floor | Renal | Hypo physiology | Circadian/dawn | SI noise |
|---|---|---|---|---|---|---|---|
| Tidepool SMM | 0 (superposition) | trivially (ISF, CIR, basal) | ✗ | ✗ | ✗ | via schedules | ✗ |
| Bergman | 2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Kanderian | 4–6 | ✓ (8 params) | ✗ | ✗ | ✗ | windowed SI | ✗ |
| ReplayBG | 9 | ✓ (MCMC, about 9–20 params) | ✗ | ✗ | risk fn only | 3-window SI | ✗ |
| Hovorka/Wilinska | about 11 | partial | ✓ | ✓ | F01c only | ✗ | 5% / 3 h sinusoid |
| simglucose (S2008) | 13 | ✗ | ✓ (kp) | ✓ | ✗ | ✗ | ✗ |
| UVA/Padova S2013/S2017 | 17+ | ✗ (priors) | ✓ | ✓ | risk fn + glucagon | ✓ | class-based ±20% |
| **Recommended** | 12–13 | core ✓, extras by prior | ✓ | ✓ | CR + HAAF + GE↑ + risk fn | ✓ | per-day + OU + intraday |

---

## 3. Subcutaneous insulin PK/PD

### 3.1 Rapid analogues (lispro, aspart)
- Plasma tmax is about 40–60 min after 0.1–0.2 U/kg. Clamp GIRmax comes at about 90–120 min, and
  duration of action is about 5–7 h at 0.2 U/kg [unverified; review values, e.g. Home 2015, Diabetes
  Obes Metab 17:1011, doi:10.1111/dom.12501].
- Larger doses have longer duration of action and somewhat later peaks. The effect is strong for
  regular insulin and weaker for analogues [unverified; Binder 1984 Diabetes Care 7:188; no
  analogue dose-tmax table found in this review]. Exposure is dose-proportional for lispro over
  0.1–0.4 U/kg (BioChaperone dose-range study; secondary report).
- Model-derived PD curve, computed by integrating each parameter set (scratch calculation; action
  = X state):

| Parameter set | Plasma-insulin peak | Action peak | 50% of action delivered | 95% delivered | Action remaining after 6 h |
|---|---|---|---|---|---|
| ReplayBG prior medians (kd .030, ka2 .0137, ke .127, p2 .0121, τ 8) | 65 min | 134 min | 180 min | 413 min | 9% |
| Hovorka (tmaxI 55) + p2 .0121 | 63 | 133 | 177 | 406 | 9% |
| simglucose adult means (p2u .034) | 55 | 90 | 125 | 308 | 2% |
| **Loop rapidActingAdult** (peak 75, DIA 360, delay 10) | — | **85** | **120** | **267** | 0% |
| Loop fiasp/lyumjev (peak 55, delay 10) | — | 65 | 97 | 231 | 0% |

**Reading:** Loop's exponential curve (Maksimovic's model in LoopKit; presets in
`LoopAlgorithm/.../ExponentialInsulinModelPreset.swift`: adult 75, child 65, Fiasp and Lyumjev 55,
DIA 360, delay 10 min) is *faster and more front-loaded* than the PD implied by the identified
physiological models or clamp GIR. The plant must therefore use its own PK/PD chain and must not
reuse Loop's curve. Otherwise the model mismatch Loop actually faces disappears from the
evaluation.

A plant with 5–10% of action after 6 h will make Loop's IOB under-count late insulin. That is a
real-world effect, and LoopEval's own replay has seen it as an "insulin-tail" forecast residual.

### 3.2 Ultra-rapid (Fiasp, Lyumjev)

**Fiasp** (aspart with niacinamide):
- Onset of appearance about 5 min vs about 11 min for aspart. Early (0–30 min) exposure about 2×.
  Total exposure unchanged. Onset of action about 10 min earlier [numbers unverified; pooled
  analysis Heise T, Pieber TR, Danne T, Erichsen L, Haahr H. Clin Pharmacokinet 2017;56:551–559,
  doi:10.1007/s40262-017-0514-8 — citation verified].
- Within-subject variability of glucose-lowering effect is CV about 20% (0.2 U/kg × 3 repeats,
  n = 46), not different from aspart [secondary source; unverified primary].

**Lyumjev** (URLi; lispro with treprostinil and citrate), T1D clamp, n = 80 (verified abstract,
Clin Pharmacokinet 2020, doi:10.1007/s40262-020-00903-0; authors [unverified]):
- Appearance 6 min sooner.
- Exposure 7.2× higher in the first 15 min.
- Exposure beyond 3 h 39–41% lower.
- Exposure duration 72–74 min shorter.
- Onset of action 11–12 min faster; action 3× greater over the first 30 min.
- Total exposure and action unchanged.

The pooled analysis of 4 clamp studies gives about 5 min faster onset, about 8× 15-min exposure and
68 min shorter duration (Clin Pharmacokinet 2021, doi:10.1007/s40262-021-01030-0).

**Prior shift relative to lispro/aspart:** τ_ins −3 to −6 min; kd ×1.3–1.5; late tail weight
−30 to −40% for URLi (about −15 to −25% Fiasp). Fit these against the clamp metrics above rather
than setting them by hand. Schiavon 2018 (TBME 65(9):2079, doi:10.1109/TBME.2017.2784101) gives the
UVA/Padova delay-based fast-analogue model (n = 116).

### 3.3 Between- and within-subject variability
- Between-subject spread in absorption is large. ReplayBG's kd prior has log-sd 0.62 and ka2 has
  log-sd 0.43, which gives about 0.4–0.6 CV on time constants. Kanderian's τ1 ranges 41–131 min
  (n = 10). Absorption rate correlates with BMI (PMC8069884, n = 116).
- Within-subject (bolus-to-bolus) variation:
  - Clamp GIR CV about 20% (Fiasp/aspart).
  - Classic reviews put within-subject CV of SC insulin absorption at about 15–25% for AUC and
    higher for early metrics [unverified; Heinemann L. Diabetes Technol Ther 2002;4:673,
    doi:10.1089/152091502320798312].
  - In free-living closed loop, model-derived absorption parameters varied by CV 34–94% across
    meals (ATTD 2020 poster; secondary). Some of that is confounded with meal error.
- **Prior:** ω_bolus ~ lognormal, CV 20% (clamp-grade) to 30% (free-living), applied per bolus;
  basal delivery gets a slower OU version of the same factor.

### 3.4 Site, lipohypertrophy, infusion-set age
- **Lipohypertrophy** (Famulla 2016, Diabetes Care 39:1486–1492, doi:10.2337/dc16-0610; n = 13,
  lispro):
  - Absorption is about 26% lower and PD effect about 24% lower.
  - Within-subject PK variability is up to 5× higher.
  - Postprandial glucose is ≥26% higher, with a later peak.
  - Aspart shows the same pattern: Cmax 169 vs 226 pmol/L (Johansson 2005, Diabetes Care
    [unverified]).
  - **Prior:** for a "lipo" subgroup (prevalence high in long-duration pump users [unverified]),
    bioavailability ×0.75 and ω_bolus CV ×2.
- **Site:** for analogues, abdomen/arm/thigh differences are small [unverified; Mudaliar 1999
  Diabetes Care 22:1501]. Needle depth (5 vs 8 mm) does not change peak timing (PMC4525656).
- **Infusion-set age:** absorption speeds up over days 1–3 of wear, and later wear brings rising
  occlusion risk [unverified; Swan 2009 Diabetes Care 32:240]. Model this as a slow drift in kd
  within each set's life, owned by the pump/behavior layer.

---

## 4. Glucose production, effectiveness, renal loss, counter-regulation

### 4.1 Endogenous glucose production
- Basal EGP in T1D is about 2–3 mg/kg/min:
  - simglucose adults 2.51 ± 0.33 mg/kg/min (verified, file).
  - Wilinska EGP0 16.9 µmol/kg/min ≈ 3.0 mg/kg/min at zero insulin (verified).
  - Hovorka EGP0 0.0161 mmol/kg/min ≈ 2.9 [unverified].
- Insulin suppresses EGP with a slower time constant than disposal: Hovorka ka3 0.03 vs
  ka2 0.06 min⁻¹ [unverified]; Wilinska kb3 0.024 vs kb2 0.056 (verified).
- **EGP cannot go negative.** At low insulin it rises back toward EGP0. This is the "floor" that
  makes a suspended pump stop a fall, and linear models lack it.

### 4.2 Glucose effectiveness
- ReplayBG prior SG median 0.022 min⁻¹ (log-sd 0.5) (verified code). Kanderian GEZI varied across
  windows (values per subject, Table 1).
- In linear-effect terms, SG damps every perturbation with a time constant of about 45 min. A fixed
  rescue-carb effect fades, which matches LoopEval's ICE finding that "treatment kernel is
  transient". This is the term that makes rescue kernels non-permanent.
- Non-insulin-dependent uptake (brain) is about 1–1.2 mg/kg/min (F01 ≈ 0.0097–0.0111 mmol/kg/min).
  It *saturates and falls* below about 80 mg/dL (Hovorka F01c rule), which slightly slows falls into
  hypo.

### 4.3 Renal glucose excretion
- The threshold is about 160–200 mg/dL:
  - Wilinska Rthr N(9, 1.5²) mmol/L (verified).
  - UVA ke2 = 339 mg/kg ÷ VG 1.85 ≈ 183 mg/dL.
  - It varies between people and rises with age and nephropathy [unverified; Johansen 1984
    Diabetologia, PMID 6714538].
- Clearance above threshold: Hovorka 0.003 min⁻¹ × (G − Rthr) × VG [unverified]; UVA 0.0005 min⁻¹
  on Gp. At G = 300, both give about 0.4–0.6 mg/kg/min, roughly 20% of EGP. This bounds prolonged
  highs and matters for TIR comparisons of high-running arms.
- **Prior:** Rthr ~ N(180, 25²) mg/dL; Rcl ~ lognormal(median 0.003 min⁻¹ in Hovorka units, CV 30%).

### 4.4 Counter-regulation in T1D, HAAF, rebound
- **Glucagon** response to hypoglycaemia is lost early in T1D. In adolescents (n = 28), the peak was
  68 vs 96 pg/mL in controls, and a significant response was present in only 7% vs 83%. It is lost
  at a median of 8 months after diagnosis, while adrenaline, cortisol and GH responses are preserved
  (Siafarikas 2012, Diabetes Care 35:1757 [DOI unverified: 10.2337/dc11-2010]).
- **Adrenaline** is the remaining defence. Recent hypoglycaemia attenuates it and shifts its
  glycaemic threshold lower: this is HAAF (Cryer PE. N Engl J Med 2013;369:362–372,
  doi:10.1056/NEJMra1215228). Antecedent hypoglycaemia shifts thresholds within about 24 h
  (Dagogo-Jack, Craft, Cryer. J Clin Invest 1993;91:819, doi:10.1172/JCI116302 [details
  unverified]). Scrupulous avoidance of hypoglycaemia for 2–3 weeks restores the response
  [unverified].
- **Rebound:**
  - Counter-regulation can cause rebound hyperglycaemia without insulin waning, mainly through
    excess EGP (Bolli GB et al. N Engl J Med 1984;311:1214–1219, doi:10.1056/NEJM198411083111904).
  - CGM-era nocturnal studies find the "Somogyi effect" rare. Most post-hypo highs are
    over-treatment plus reduced insulin delivery [unverified; e.g. Guillod 2007 Diabetes Metab].
  - **Model rebound as behavior (rescue size) plus a modest physiological EGP boost.** Do not use
    a large endogenous rebound.
- **Recommended term:**
  ```
  CR(G) = CRmax · h_HAAF · σ((Gcr − G)/s)       Gcr ~ N(65, 5²) mg/dL, s ≈ 5 mg/dL
  CRmax ~ lognormal(median 1.0 mg/kg/min, CV 50%)   [prior by judgement; see note]
  dh_HAAF/dt = (1 − h_HAAF)/τ_rec − κ·[G < 54]·h_HAAF,  τ_rec ≈ 48–72 h, h ∈ [0.3, 1]
  ```
  This is a first-order boost (time constant about 15–20 min) on EGP.

  Note: there is no T1D-clamp-calibrated CR gain in the reviewed sources (S2013 does not publish
  its glucagon parameters). Calibrate CRmax and the HAAF depth to the *observed* nadir and duration
  distribution of untreated or minimally treated lows in the donor pool. LoopEval's ICE work found
  low response is a personal trait ("everyone responds; proactiveness differs"), which argues for
  a per-person CRmax.

### 4.5 S2013 hypoglycaemic risk function
- It amplifies insulin-dependent uptake as G falls below Gb: risk = 1 + 10·r1·[ln(G)^r2 −
  ln(Gb)^r2]², frozen below 60 mg/dL. ReplayBG code: `risk_coeff = 10.0 * r1`, multiplying X·G.
- With r1 = 1.4407, r2 = 0.8124 and Gb = 119, the multiplier on insulin-dependent uptake is
  (scratch calculation):

  | G (mg/dL) | Multiplier |
  |---|---|
  | 100 | ×1.18 |
  | 80 | ×1.9 |
  | ≤60 | ×3.6 |

  **This is not a small term.**
- The direction of effect is *opposite* to CR. It was introduced to fit clamp evidence that insulin
  action is stronger in the hypoglycaemic range (Dalla Man 2014).
- **Recommendation:** implement it, but give it a scale parameter λ_risk ∈ [0, 1] multiplying
  (risk − 1). Default λ_risk = 1 to match S2013/ReplayBG, which were validated on hypo data.
  Calibrate λ_risk jointly with CRmax against the donor pool's low dynamics (fall rate below
  80 mg/dL at a given IOB, nadir depth). The two terms are confounded and cannot be identified
  separately from CGM data.
- Run a λ_risk = 0 arm as a sensitivity check for any hypo-prevention candidate. A ×3.6 uptake
  amplification at 60 mg/dL can dominate a candidate's t<54 difference.

---

## 5. Insulin sensitivity: circadian, day-to-day, drift

### 5.1 Circadian profile and dawn
- **Hinshaw 2013** (Diabetes 62(7):2223–2229, doi:10.2337/db12-1759 [DOI unverified]; n = 19,
  C-peptide-negative, triple tracer, identical meals at B/L/D):
  - No significant population difference in SI between meals.
  - The T1D pattern differs from healthy people's.
  - "Individual-specific", so do not impose a population-mean daily curve.
- **Visentin 2015** (Diabetes Technol Ther 17(1):1–7, doi:10.1089/dia.2014.0192; verified;
  n = 20 T1D):
  - Seven classes of high (h) / low (l) SI at breakfast-lunch-dinner, where high = SI above 60% of
    the subject's maximum. Probabilities:

    | Class | Pattern (B-L-D) | Probability |
    |---|---|---|
    | 1 | hhh | 0.10 |
    | 2 | hhl | 0.05 |
    | 3 | hlh | 0.05 |
    | 4 | hll | 0.10 |
    | 5 | lhh | 0.20 |
    | 6 | lhl | 0.20 |
    | 7 | llh | 0.30 |

  - "Low" = 40 ± 23% of "high", so α = 0.4.
  - Switch times 04:00, 11:00, 17:00 ("almost stepwise").
  - Multiplicative noise N(1, 0.2), "deviations up to 40%". Temporary migration only to
    contiguous classes.
  - Most likely: lower SI at breakfast.
  - **Adopt directly**, with smoothed transitions (about 1 h ramps).
- **Dawn phenomenon:**
  - S2017 ramps EGP (kp1) linearly 03:00→07:00 by about 1.5 mg/kg/min. This gives about +30 mg/dL
    uncompensated rise (Mallad 2015, Diabetes Technol Ther 17(8):587 [DOI unverified:
    10.1089/dia.2015.0017], n = 16, attributed to cortisol).
  - Prevalence in T1D with a ≥10 mg/dL 3–4 am→waking rise and no preceding hypo: 38% in a Japanese
    CGM sample (n = 21, PMC3850159), about half in a Canadian pump-trial analysis [secondary,
    unverified], and ">50%" in reviews [unverified; Porcellati F, Lucidi P, Bolli GB, Fanelli CG.
    Diabetes Care 2013;36:3860, doi:10.2337/dc13-2088].
  - **Prior:** dawn present with p = 0.45. Magnitude lognormal, median +1.0 mg/kg/min EGP
    (≈ +20 mg/dL uncompensated), 90% range 0.3–2.5. Onset U(02:00, 04:30), plateau to waking.

### 5.2 Day-to-day variability
- **Ruan 2016** (Diabetes Care 39(5):830 [DOI unverified: 10.2337/dc15-2623]; 32 adults, 12 weeks of
  home hybrid closed loop, 1,918 nights; verified via secondary summaries): within-person CV of
  insulin requirement:

  | Period | CV |
  |---|---|
  | Overnight | about 31% |
  | Daytime | about 22% |
  | Total daily | about 17% |

  Closed-loop delivered insulin is a direct readout of need, which makes this the best calibration
  target for SI noise. It includes meal-content variation in daytime, so *overnight* (31%) is the
  cleanest SI-plus-EGP signal.
- **Prior:**
  - Per-day multiplier on SI_D and SI_E: lognormal, CV 15%.
  - Intraday OU on log SI: σ_stationary about 0.2, τ about 3–6 h. This covers Visentin's N(1, 0.2)
    and Wilinska's oscillations.
  - Overnight EGP OU: CV about 15%.
  - Tune jointly so that simulated closed-loop delivered insulin reproduces Ruan's 31/22/17%
    pattern under LoopEval's controller.

### 5.3 Slow drift
- Menstrual cycle: luteal-phase insulin needs rise [unverified magnitude; reported as roughly
  +10–20% in small studies]. Illness, season and weight change also contribute.
- Model as a slow OU on log SI with τ ≈ 14–30 days and σ ≈ 0.1. Use an optional 28-day sinusoid
  (amplitude 0–15%) for menstruating people.
- This term mainly matters for how settings go stale. It belongs to the scenario layer's
  long-horizon runs, not to 1-day tests.

---

## 6. Carbohydrate, fat and protein absorption

### 6.1 Gut model
- Dalla Man two-stage stomach (solid → triturated) + gut:
  - Nonlinear emptying kempt(Qsto) between kmin and kmax driven by the fraction of the meal still
    in the stomach (b, c/d).
  - Healthy-population values [unverified against Table 1]: kmax 0.0558, kmin 0.0080,
    kabs 0.057 min⁻¹, b 0.82, d 0.010, f 0.90.
  - simglucose T1D adults (verified file): kmax 0.039 ± 0.011, kmin 0.0074 ± 0.004,
    kabs 0.21 ± 0.21, b 0.79, d 0.18.
  - Dalla Man C, Camilleri M, Cobelli C. IEEE TBME 2006;53:2472 (absorption model)
    [unverified DOI]; Dalla Man C, Rizza RA, Cobelli C. IEEE TBME 2007;54(10):1740–1749,
    doi:10.1109/TBME.2007.893506.
- **Recommendation:** use ReplayBG's linear-kempt simplification. The nonlinear emptying is not
  identifiable from free-living data. Per-meal-slot kabs and β come from donor fits.
- Population fallbacks:
  - Kanderian τm 47–78 min (mixed meals) and 31 min (supplemental carbs).
  - Wilinska tmaxG ≈ 40 min (lognormal sd 0.25), bioavailability U(0.7, 1.2) with 20%
    inter-occasion noise.

### 6.2 Glycaemic index, mixed-meal variability
- GI acts mainly through emptying and absorption speed (kabs, kempt) and peak height.
- Systematic review: Bell KJ, Smart CE, Steil GM, Brand-Miller JC, King B, Wolpert HA. Diabetes Care
  2015;38(6):1008–1015, doi:10.2337/dc15-0100. Fat, protein and GI all modify postprandial
  glycaemia; low GI reduces the early peak [details unverified].
- **Prior:** per meal, kabs multiplier lognormal (CV 40%, matching ReplayBG's wide kabs prior and
  Kanderian's dinner SEM), β ~ U(0, 30) min for announced meals, and bioavailability CV 15–20%.
  Carb-*count* error is separate (behavior layer).

### 6.3 Fat and protein: quantified

| Study | Design | Effect |
|---|---|---|
| Smart 2013, Diabetes Care 36(12):3897–3902, doi:10.2337/dc13-1195 | n = 33 children, same carb with 35 g fat vs 4 g and 40 g protein vs 5 g; insulin for carbs | Glucose higher from 180 min (high protein) and 210 min (high fat). High fat + high protein additive, elevated 180–300 min. High-protein meals cut hypo risk (OR 0.16). LF/HP vs reference about +2.4 mmol/L (CI 1.1–3.7) at the late timepoint [timepoint unverified] |
| Wolpert 2013, Diabetes Care 36(4):810–816, doi:10.2337/dc12-0092 | n = 7 adults, closed loop, high- vs low-fat dinner, same carb and protein | Insulin 12.6 ± 1.9 vs 9.0 ± 1.3 U (**+42%**, highly individual: one subject >2×, one slightly less). Still more hyperglycaemia; late rise about 3–5 h, insulin elevated to 5–10 h [fat grams unverified: about 60 vs 10 g] |
| Bell 2020, Diabetes Care 43(1):59 [DOI unverified: 10.2337/dc19-0687] | fat in 20 g increments, fixed carbs, dual-wave insulin | Dose-response: more fat lowers early and raises late glucose. Up to about 20% more insulin for high-fat meals. Fat *type* not clinically significant [secondary summary] |
| Paterson 2016, Diabet Med 33:592 [unverified DOI] | whey protein alone 0–100 g, no insulin | Only ≥75 g raised glucose, more slowly than 20 g glucose |
| Paterson 2017, Diabet Med 34:851 [unverified DOI] | 30 g carb + whey protein 0–75 g, insulin for carbs | Early (30–60 min) excursion falls with protein; 150–300 min rises, dose-dependent (about +5 mmol/L at 300 min with 75 g [secondary, unverified]) |

**Model (priors by judgement, anchored on the table):**
- **Early blunting:** φ_fat = 1/(1 + fat_g/60) on kempt. 35 g fat → about 0.63× emptying, which
  lowers the early peak as in Bell 2020 and Paterson 2017.
- **Late glucose appearance (slow channel):**
  - D_slow = 0.1·protein_g (protein above about 20 g; gluconeogenic glucose-equivalent fraction
    with a 90% range of 0.03–0.25).
  - Plus fat-tail carbs moved out of the fast path.
  - k_slow ≈ 1/120 min⁻¹, β_slow ≈ 90 min. Peak 3–5 h, done by about 8 h.
- **Fat-induced insulin resistance:** a transient SI multiplier
  1 − ρ·fat_g/50, with ρ ~ U(0, 0.35), ramping in from 2 h, peaking 3–6 h and fading by 10 h.
  It reproduces Wolpert's +42% (mean) with very wide spread.
- **Calibration:** check against Smart 2013's 180–300 min separation and Wolpert's insulin ratio
  under simulated closed loop. Most donor meals carry no fat/protein annotation, so draw the
  meal-composition mix from the behavior layer's meal library.

### 6.4 Gastric emptying in hypo- and hyperglycaemia
- **Hypoglycaemia accelerates emptying.** In healthy subjects, solid T50 was 16 ± 7 min during
  insulin-induced hypoglycaemia vs 43 ± 20 min at euglycaemia (Schvarcz E et al. Diabetes Care
  1995;18:674 [DOI unverified]). The same is reported for long-standing T1D [unverified; Russo A
  et al. J Clin Endocrinol Metab 2005;90:4489].
- **Hyperglycaemia slows it.** In IDDM, liquid T50 was 41 ± 3 min at 8 mmol/L vs 29 ± 4 min at
  4 mmol/L (Schvarcz 1997, Gastroenterology 113:60 [DOI unverified]).
- **Model:** φ_hypo(G) = 1 + 1.5·σ((70 − G)/5), up to ×2.5 below about 60 mg/dL. A mild slowing
  ×(1 − 0.004·max(0, G − 145)) at high G is optional.
- Gastroparesis (a subgroup of long-duration T1D) means kempt ×0.3–0.5 [prevalence unverified].

### 6.5 Rescue carbohydrate
- The response tracks *grams of glucose*, not the food form. Brodows recommended 20 g glucose
  (0.3 g/kg in children) (Brodows RG, Williams C, Amatruda JM. JAMA 1984;252:3378–3381 —
  citation verified, numbers [unverified]: roughly +40 mg/dL by 30 min for 10 g and +60–70 mg/dL
  by 45–60 min for 20 g).
- Fructose-heavy juice works more slowly than glucose or sucrose. Neither returns BG to normal
  reliably within 10–15 min (pooled analysis of dietary sugars vs tablets; secondary).
- **Model:**
  - Glucose/dextrose tablets: fast gut path with kabs ≈ 0.05–0.08 min⁻¹, β ≈ 5 min, f ≈ 1.0,
    *and* φ_hypo acceleration.
  - Juice/sucrose: kabs ×0.6.
  - Gel or buccal glucose is swallowed glucose, not buccal absorption [unverified].
- With SG ≈ 0.02 min⁻¹ the rescue effect peaks at 30–60 min and decays. It does not hold a
  permanent offset, consistent with LoopEval's transient-treatment-kernel finding. ReplayBG fits a
  separate kabs_H for hypotreatments for this reason.

---

## 7. Open uncertainties (largest first)
1. **Counter-regulatory gain, HAAF depth and the hypo risk-function scale (λ_risk).** No published
   per-person T1D prior was found for CR. The S2013 risk term is large (×3.6 at 60 mg/dL) and
   opposes CR. The two must be calibrated jointly to the donor pool's untreated-low dynamics. This
   pair most directly shapes t<54.
2. **Insulin-action tail beyond 4 h.** Physiological models put 2–9% of action after 6 h. Getting
   this wrong mis-scores IOB-based safety features.
3. **SI noise decomposition.** Ruan's CVs bound the total, but the split between per-day,
   intraday and overnight-EGP noise is a modelling choice.
4. **Fat/protein channel.** Effect sizes come from small trials (n = 7–33) with large individual
   spread.

---

## 8. References

Verified = read in the primary source, its full text, or authoritative bibliographic record during
this review; otherwise marked.

1. Bergman RN, Ider YZ, Bowden CR, Cobelli C. Quantitative estimation of insulin sensitivity. Am J
   Physiol 1979;236:E667–E677. doi:10.1152/ajpendo.1979.236.6.E667 [not re-read].
2. Hovorka R, Canonico V, Chassin LJ, et al. Nonlinear model predictive control of glucose
   concentration in subjects with type 1 diabetes. Physiol Meas 2004;25:905–920.
   doi:10.1088/0967-3334/25/4/010 [citation verified; parameter values unverified].
3. Hovorka R, Shojaee-Moradie F, Carroll PV, et al. Partitioning glucose distribution/transport,
   disposal, and endogenous production during IVGTT. Am J Physiol Endocrinol Metab
   2002;282:E992–E1007 [unverified].
4. Wilinska ME, Chassin LJ, Acerini CL, Allen JM, Dunger DB, Hovorka R. Simulation environment to
   evaluate closed-loop insulin delivery systems in type 1 diabetes. J Diabetes Sci Technol
   2010;4(1):132–144. PMC2825634 (verified). doi:10.1177/193229681000400117 [DOI unverified].
5. Wilinska ME, Chassin LJ, Schaller HC, et al. Insulin kinetics in type-1 diabetes: continuous and
   bolus delivery of rapid acting insulin. IEEE Trans Biomed Eng 2005;52:3–12.
   doi:10.1109/TBME.2004.839639 [unverified].
6. Dalla Man C, Rizza RA, Cobelli C. Meal simulation model of the glucose-insulin system. IEEE Trans
   Biomed Eng 2007;54(10):1740–1749. doi:10.1109/TBME.2007.893506 (citation verified).
7. Dalla Man C, Camilleri M, Cobelli C. A system model of oral glucose absorption: validation on
   gold standard data. IEEE Trans Biomed Eng 2006;53(12):2472–2478 [unverified].
8. Kovatchev BP, Breton M, Dalla Man C, Cobelli C. In silico preclinical trials: a proof of concept
   in closed-loop control of type 1 diabetes. J Diabetes Sci Technol 2009;3(1):44–55.
   doi:10.1177/193229680900300106 [unverified].
9. Dalla Man C, Micheletto F, Lv D, Breton M, Kovatchev B, Cobelli C. The UVA/PADOVA type 1 diabetes
   simulator: new features. J Diabetes Sci Technol 2014;8(1):26–34. doi:10.1177/1932296813514502.
   PMC4454102 (verified).
10. Visentin R, Dalla Man C, Kudva YC, Basu A, Cobelli C. Circadian variability of insulin
    sensitivity: physiological input for in silico artificial pancreas. Diabetes Technol Ther
    2015;17(1):1–7. doi:10.1089/dia.2014.0192. PMC4290795 (verified).
11. Visentin R, Dalla Man C, Cobelli C. One-day Bayesian cloning of type 1 diabetes subjects: toward
    a single-day UVA/Padova type 1 diabetes simulator. IEEE Trans Biomed Eng
    2016;63(11):2416–2424. doi:10.1109/TBME.2016.2535241 [DOI and pages unverified].
12. Visentin R, Campos-Náñez E, Schiavon M, et al. The UVA/Padova type 1 diabetes simulator goes
    from single meal to single day. J Diabetes Sci Technol 2018;12(2):273–281.
    doi:10.1177/1932296818757747. PMC5851236 (verified).
13. Schiavon M, Dalla Man C, Cobelli C. Modeling subcutaneous absorption of fast-acting insulin in
    type 1 diabetes. IEEE Trans Biomed Eng 2018;65(9):2079–2086. doi:10.1109/TBME.2017.2784101
    (DOI verified via ref. 12; pages unverified).
14. Cappon G, Vettoretti M, Sparacino G, Del Favero S, Facchinetti A. ReplayBG: a digital
    twin-based methodology to identify a personalized model from type 1 diabetes data and simulate
    glucose concentrations to assess alternative therapies. IEEE Trans Biomed Eng
    2023;70(11):3105–3115. doi:10.1109/TBME.2023.3286856 (verified). Code:
    github.com/gcappon/py_replay_bg (read).
15. Kanderian SS, Weinzimer S, Voskanyan G, Steil GM. Identification of intraday metabolic profiles
    during closed-loop glucose control in individuals with type 1 diabetes. J Diabetes Sci Technol
    2009;3(5):1047–1057. doi:10.1177/193229680900300508. PMC2769900 (verified).
16. Tidepool. data-science-models: `simple_metabolism_model.py`, `treatment_models.py`;
    data-science-simulator: `models/patient.py`. github.com/tidepool-org (read 2026-10-15).
17. Xie J. simglucose v0.2.x: UVA/Padova 2008 implementation. github.com/jxx123/simglucose (read
    `vpatient_params.csv`, `t1dpatient.py`).
18. LoopKit LoopAlgorithm, `ExponentialInsulinModelPreset.swift` (presets read from this project's
    checkout).
19. Heise T, Pieber TR, Danne T, Erichsen L, Haahr H. A pooled analysis of clinical pharmacology
    trials investigating the pharmacokinetic and pharmacodynamic characteristics of fast-acting
    insulin aspart in adults with type 1 diabetes. Clin Pharmacokinet 2017;56(5):551–559.
    doi:10.1007/s40262-017-0514-8 (citation verified; numbers unverified).
20. Ultra rapid lispro (URLi) accelerates insulin lispro absorption and insulin action vs Humalog in
    patients with type 1 diabetes. Clin Pharmacokinet 2020. doi:10.1007/s40262-020-00903-0
    (abstract numbers verified via secondary; authors unverified).
21. URLi pooled analysis of euglycemic clamp studies. Clin Pharmacokinet 2021.
    doi:10.1007/s40262-021-01030-0 (numbers via secondary).
22. Famulla S, Hövelmann U, Fischer A, et al. Insulin injection into lipohypertrophic tissue: blunted
    and more variable insulin absorption and action and impaired postprandial glucose control.
    Diabetes Care 2016;39:1486–1492. doi:10.2337/dc16-0610 (verified via secondary summaries).
23. Heinemann L. Variability of insulin absorption and insulin action. Diabetes Technol Ther
    2002;4:673–682. doi:10.1089/152091502320798312 [unverified].
24. Home PD. Plasma insulin profiles after subcutaneous injection: how close can we get to
    physiology in people with diabetes? Diabetes Obes Metab 2015;17:1011–1020.
    doi:10.1111/dom.12501 [unverified].
25. Swan KL, Dziura JD, Steil GM, et al. Effect of age of infusion site and type of rapid-acting
    analog on pharmacodynamic parameters of insulin boluses in youth with type 1 diabetes receiving
    insulin pump therapy. Diabetes Care 2009;32:240–244 [unverified].
26. Hinshaw L, Dalla Man C, Nandy DK, et al. Diurnal pattern of insulin action in type 1 diabetes:
    implications for a closed-loop system. Diabetes 2013;62(7):2223–2229. PMC3712033 (findings
    verified). doi:10.2337/db12-1759 [DOI unverified].
27. Mallad A, et al. Nocturnal glucose metabolism in type 1 diabetes: a study comparing single
    versus dual tracer approaches. Diabetes Technol Ther 2015;17(8):587–595. PMC4528985 [exact
    title, authors, DOI and EGP values unverified; the ~30 mg/dL and ~1.5 mg/kg/min magnitudes are
    taken from ref. 12].
28. Porcellati F, Lucidi P, Bolli GB, Fanelli CG. Thirty years of research on the dawn phenomenon:
    lessons to optimize blood glucose control in diabetes. Diabetes Care 2013;36:3860–3862.
    doi:10.2337/dc13-2088 [unverified].
29. Ruan Y, Thabit H, Leelarathna L, et al. Variability of insulin requirements over 12 weeks of
    closed-loop insulin delivery in adults with type 1 diabetes. Diabetes Care 2016;39(5):830–832
    (findings verified via secondary). doi:10.2337/dc15-2623 [DOI unverified].
30. Siafarikas A, Johnston RJ, Bulsara MK, et al. Early loss of the glucagon response to
    hypoglycemia in adolescents with type 1 diabetes. Diabetes Care 2012;35:1757–1762 (findings
    verified via secondary) [DOI unverified].
31. Cryer PE. Mechanisms of hypoglycemia-associated autonomic failure in diabetes. N Engl J Med
    2013;369:362–372. doi:10.1056/NEJMra1215228 (verified).
32. Dagogo-Jack SE, Craft S, Cryer PE. Hypoglycemia-associated autonomic failure in insulin-dependent
    diabetes mellitus. J Clin Invest 1993;91:819–828. doi:10.1172/JCI116302 [details unverified].
33. Bolli GB, Gottesman IS, Campbell PJ, Haymond MW, Gerich JE. Glucose counterregulation and waning
    of insulin in the Somogyi phenomenon (posthypoglycemic hyperglycemia). N Engl J Med
    1984;311:1214–1219. doi:10.1056/NEJM198411083111904 (citation and conclusion verified; author
    list unverified).
34. Johansen K, Svendsen PA, Lørup B. Variations in renal threshold for glucose in type 1
    (insulin-dependent) diabetes mellitus. Diabetologia 1984;26:180–182. PMID 6714538 [findings
    unverified].
35. Bell KJ, Smart CE, Steil GM, Brand-Miller JC, King B, Wolpert HA. Impact of fat, protein, and
    glycemic index on postprandial glucose control in type 1 diabetes. Diabetes Care
    2015;38(6):1008–1015. doi:10.2337/dc15-0100 [details unverified].
36. Smart CE, Evans M, O'Connell SM, et al. Both dietary protein and fat increase postprandial
    glucose excursions in children with type 1 diabetes, and the effect is additive. Diabetes Care
    2013;36(12):3897–3902. doi:10.2337/dc13-1195 (design and timing verified; mmol/L values
    partially).
37. Wolpert HA, Atakov-Castillo A, Smith SA, Steil GM. Dietary fat acutely increases glucose
    concentrations and insulin requirements in patients with type 1 diabetes. Diabetes Care
    2013;36(4):810–816. doi:10.2337/dc12-0092 (verified).
38. Bell KJ, Fio CZ, Twigg S, et al. Amount and type of dietary fat, postprandial glycemia, and
    insulin requirements in type 1 diabetes: a randomized within-subject trial. Diabetes Care
    2020;43(1):59–66 [secondary; DOI unverified].
39. Paterson MA, Smart CEM, Lopez PE, et al. Influence of pure protein on postprandial blood glucose
    levels in individuals with type 1 diabetes mellitus. Diabet Med 2016;33:592–598 [secondary].
40. Paterson MA, King BR, Smart CEM, et al. Impact of dietary protein on postprandial glycaemic
    control and insulin requirements in type 1 diabetes: a systematic review / dose-response study.
    Diabet Med 2017;34:851–854 [secondary; exact title unverified].
41. Schvarcz E, Palmér M, Aman J, Lindkvist B, Beckman KW. Hypoglycaemia increases the gastric
    emptying rate in healthy subjects. Diabetes Care 1995;18:674–676 (numbers verified via
    secondary; DOI unverified).
42. Schvarcz E, Palmér M, Aman J, Horowitz M, Stridsberg M, Berne C. Physiological hyperglycemia
    slows gastric emptying in normal subjects and patients with insulin-dependent diabetes
    mellitus. Gastroenterology 1997;113:60–66 (numbers verified via secondary).
43. Russo A, Stevens JE, Chen R, et al. Insulin-induced hypoglycemia accelerates gastric emptying of
    solids and liquids in long-standing type 1 diabetes. J Clin Endocrinol Metab 2005;90:4489–4495
    [unverified].
44. Brodows RG, Williams C, Amatruda JM. Treatment of insulin reactions in diabetics. JAMA
    1984;252(24):3378–3381 (citation verified; numeric responses unverified).
