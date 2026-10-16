# The additive patient simulator — model guide

A virtual person with type 1 diabetes, assembled from named, separately evidenced parts, that runs in
closed loop with LoopEval's real Loop algorithm. This guide lists every part of the model and, for each
one, gives:

- **Form**: what the part computes.
- **Values**: the parameters and their population distributions.
- **Evidence**: where each value comes from. The `evidence/0x §n` files hold full citations; the ones
  this guide leans on most are listed at the end.
- **Tuning**: what has been calibrated, against what, and the lesson behind it (`LESSONS n`).
- **Notes**: implementation details that are easy to get wrong.
- **Interactions**: which other parts it couples to.

`COMPONENTS.md` is the compact registry with a status column. This guide is the long-form companion.
Code lives in `analysis/loopeval_analysis/patient_sim/`.

**Tags.** **[J]** marks a judgement still waiting for evidence; these are the first values to replace.
`ice Lnn`, `eda Lnn` and `run:` point to measurements made on Tidepool donor data by the other roles.

---

## 0. Ground rules

1. **No mystery terms** (LESSONS 1). A variability or offset term exists only if its size comes from
   its own controlled-condition evidence. Free-living statistics (TDD CV, day-to-day spread, skew) are
   *targets* that the named parts must reproduce together, never inputs to fit. When a statistic
   misses, a named part is wrong or a part is missing.
2. **Real-world data is the primary test.** Every simulated person is scored with the same code as the
   real donors (`validate.py`), against 206 Tidepool pilot donors in 13-day blocks.
3. **The person is a second controller.** Behavior is modelled as traits taken from the donor each
   person is drawn from, not as noise.
4. **Truth and belief are separate.** The body's physiology, the controller's settings and the
   person's estimates are drawn separately, and the gaps between them are part of what is simulated.
5. **Reconcile at every boundary** (LESSONS 11, 19, 25). Before reading any statistic, check that the
   insulin crossing each interface (controller → plant → pump → depot → plasma) adds up.

---

## 1. Architecture

### 1.1 The minute loop (`world.py`, `World._minute`)

Every simulated minute runs in this order:

| # | Step | Code |
|---|---|---|
| 1 | Modulators: circadian × day-level × menstrual × illness → `si_mult`, `egp_mult` | `modulators.Modulators.at` |
| 2 | Fat-induced insulin resistance multiplies `si_mult` | `World._fat_si` |
| 3 | Exercise state: intensity, acute + delayed SI boost, absorption multiplier | `exercise.Exercise.at` |
| 4 | Site state: absorption speed by site age; absorbed fraction (failing or dislodged site) | `device.Pump.site_state` |
| 5 | Pump delivers this minute's basal and bolus, after its errors and faults | `device.Pump.deliver` |
| 6 | Delivered insulin enters the body: basal into the shared depot, each bolus into its own depot with ~15% absorption jitter | `physiology.Body.infuse` |
| 7 | Body integrates one minute | `physiology.Body.step` |
| 8 | Sensor sees the new blood glucose; on a reporting minute it returns a reading or a gap | `sensor.Sensor.step` |
| 9 | Behavior: the day's plan (eating, walks, exercise, grazing), then defense and corrections based on the latest *visible* reading | `behavior.Behavior.minute` |
| 10 | Site-change responses: a failing site seen as a long high (> 250), or an occlusion alarm | `World._minute` |
| 11 | Truth is logged | `World.truth` |

Time is local minutes from `EPOCH` (Monday 2026-01-05 00:00; local time = UTC inside the simulation).

### 1.2 Two drives

- **Internal** (`run_internal`): an open-loop pump user on scheduled basal, with calculator meal
  boluses and corrections at the person's own settings. It is used only for the 30 h burn-in history
  exported to LoopEval, and for quick tests. It is not a model of Loop.
- **Plant** (`advance`): LoopEval protocol v2 (`--external-plant --plant-behavior`). LoopEval sends
  doses; the world returns CGM at the sample times plus the person's carb entries and bolus requests.
  A bolus request is either a ratio of Loop's recommendation or, for food dosed by hand, absolute units.

### 1.3 Coupling to LoopEval (`loopeval_io.py`)

- **Export.** 30 h of internally driven history (glucose, doses, carb entries), then the sensor's
  reporting grid with placeholder values. The baseline arm of the trace replays the placeholders and is
  meaningless; read only the candidate arm.
- **Controller.** Deployed Loop-main ("class 1", `docs/loop-algo-classes.md`):
  `--no-mid-absorption-isf --no-gradual-transitions-gate --legacy-rc-decay`. Temp-basal users add
  `--temp-basal-strategy`. Auto-bolus users run LoopEval's default application factor, 0.4.
- **Reproducibility.** The plant re-simulates the burn-in from the same (person, seed), so its state at
  the first request matches the export exactly.
- **Engine requirement.** LoopEval main ≥ f11386e. Older binaries either stacked Loop's automatic dose
  on top of a plant bolus (LESSONS 21) or dropped plant boluses entirely (8e86860, LESSONS 25).
  `PLANT_NET_AF=1` restores the ratio − 0.4 workaround, for binaries older than 8e86860 only.
- **Late doses.** The plant's clock is already past t0 when doses arrive, so each dose is delivered
  from the current minute, at full volume and duration (LESSONS 19: dropping them lost half of all
  insulin in cohorts c1–c11).

### 1.4 Seeds and streams

`(person, seed)` determines everything. `World` spawns six independent RNG streams: modulators,
behavior, sensor, pump, absorption jitter and miscellaneous. Turning one part off (`--disable`) leaves
the other streams unchanged, so every ablation is a paired comparison on the same people.

---

## 2. The person — truth, settings, devices (`person.py`, `templates.py`)

### G1 Template
- **Form.** Each person starts from one real donor's row, jittered: TDD, ISF and basal each × lnN(0, 0.10).
- **Values.** `templates_pilot.csv` has 168 ice pilot donors with measured behavior. `templates.csv`
  has 156 eda cohort donors without it.
- **Notes.** Only aliases ever appear. The row carries settings, the yardstick ISF, the measured
  fasting rate, TDD, age, sensor family, pump, dosing strategy, insulin brand and the behavior rates
  (`BEHAVIOR_COLS`).

### G2 True ISF
- **Form.** `isf_true = settings_ISF × clip(yardstick/settings, 0.5, 2)^ISF_W × jitter`, with
  `ISF_W = 0.5`.
- **Evidence.** eda L53/L54: ISF is not identifiable in closed loop; the yardstick/settings ratio
  spans 0.41–2.69 and barely tracks lows (Spearman −0.13 with t<70).
- **Tuning.** A grid over ISF_W ∈ {0, 0.5, 1} showed no benefit at either end. **[J]**, open.
- **Interactions.** Sets the gap between what Loop believes and what the body does. That gap drives
  retrospective correction and the person's outcome.

### G3 Body weight
- **Form.** A log-blend of the age prior (CDC medians; adults 77 kg) and TDD ÷ an age-banded U/kg
  (0.75 under 13, 1.0 for 13–17, 0.6 for adults), plus lnN noise of 0.12.
- **Evidence.** eda L47: the profile age can belong to the account holder, so neither source is
  trusted alone. BDDP has no sex field, so sex is drawn 50/50 and is used only for the menstrual
  module.

### G4 Insulin balance
- **Form.** True basal = share × TDD/24, with share N(0.5, 0.07) clipped to [0.35, 0.7]. Carbs eaten
  per day = TDD·(1 − share)·CR_true.
- **Evidence.** eda L9: the scheduled basal share is 0.43–0.51. LESSONS 4: the measured fasting rate is
  not true basal, because fasting windows carry unannounced eating. It is kept as a validation quantity.
- **Interactions.** TDD is the measured constraint everything else must satisfy.

### G5 Settings
The donor's own ISF, CR, basal, target and maximums, scaled by the same jitter as the truth, so each
person keeps their donor's settings error. Suspend threshold 70.

### G6 Devices
- Sensor family: per-reading deviceId, dominant per month (Databricks `sensor_month.csv`).
- Pump and dosing strategy: from the donor.
- Formulation: from the recorded insulin brand. Unrecorded brands (twiist uploader) are drawn from the
  recorded mix: rapid 52 : ultra-rapid 20.
- The Loop insulin curve a person selects is a *setting*, `controller_insulin()`. The formulation is
  the body.

### G7 Carb sensitivity (CSF)
- **Form.** `CSF = CSF_PER_GEQ × ISF_yardstick × TDD/500 × lnN(0, 0.15)`, with `CSF_PER_GEQ = 1.73`.
  Bioavailability f = CSF·BW·VG/1000, clipped to [0.3, 1.0]. When f would exceed 1, VG shrinks instead.
- **Evidence.** ice L54: a meal pulse is 1.30 g-eq per entered gram. ice's g-eq is settings-free:
  ISF_tdd/(500/TDD).
- **Tuning.**
  - LESSONS 14: physics with f 0.9, a tracer-glucose figure, gave ~1.7× the donors' rise.
  - LESSONS 17: the 1.30 ratio must be read in g-eq units.
  - LESSONS 27: calibrated through the ice labeler itself. Simulated people at 1.30 read 0.91 against
    1.21 for the donors, because glucose effectiveness erodes the pulse before ICE sees it. Hence
    1.30 × 1.21/0.91 = 1.73.
- **Interactions.** Every carbohydrate path shares this calibrated f. Rescues and snacks use f × 1.25
  (LESSONS 18).

### G8 Effective-ISF calibration (`person.calibrate`)
1. Ib comes from the true basal rate.
2. The effect is split between EGP suppression and disposal, with the EGP share drawn U(0.3, 0.5),
   using probes on the *linear part*: SG, κ, risk and counter-regulation all off.
3. Both arms are scaled by bisection until the full body's effective ISF at ~180 mg/dL equals
   `isf_true`. The probe raises both arms to ~180 with the same fast carbs, then boluses one of them
   (`_probe_isf_effective`).

- **Evidence.** LESSONS 15: the yardstick ISF is measured at operating glucose in closed loop, so it
  already contains glucose effectiveness and renal loss. Calibrating on the linear part at rest made
  bodies 30% less responsive than Loop believed, and cohorts settled at a mean of ~200.
- **Notes.** Probe against a control body, never against an assumed rest level (LESSONS 6).

---

## 3. Physiology (`physiology.py`, `insulins.py`)

The spine is the identifiable minimal model of ReplayBG (Cappon 2023), with Hovorka's split of insulin
action into separate arms, plus named nonlinear terms for the low tail and long highs.

### A1 Glucose kinetics
- **Form.** One compartment: `dG = −SG(G − Gb) − [insulin uptake] + (EGP − EGP_b − exercise uptake +
  Ra)/VG − renal`.
- **Values.**
  - VG lnN(1.88 dL/kg, 0.15). The UVA/Padova value; ReplayBG's 1.45 doubles carb sensitivity.
  - SG lnN(0.003 /min, 0.5).
  - Gb N(119, 7.1), clipped to [95, 150].
  - Floor at 10 mg/dL.
- **Evidence.** 01 §1.2, §4.2. LESSONS 3: ReplayBG's identified SG (0.022) absorbs unmodelled dynamics.
  UVA/Padova impulse fits give 0.0013–0.0047.

### A2 Subcutaneous insulin PK
- **Form.** Each bolus gets its own depot: delay τ → Isc1 →kd→ Isc2 →ka2→ plasma (ke 0.127, VI
  0.126 L/kg). Basal shares one depot, settled to steady state at Ib.
- **Values.** kd lnN(0.030, 0.31); ka2 lnN(0.018, 0.21), at half ReplayBG's log-sd, because its prior is
  for identification, not a population. Constraint: ka2 < kd.
- **Tuning.** LESSONS 9: ka2 refit from 0.0137 to 0.018, to the lispro clamp profile.
- **Notes.** A bolus depot must not be garbage-collected while its dose is still in the delay line
  (LESSONS 6).

### A3 Insulin formulations (`insulins.py`)
- **Form.** Delay τ, multipliers on the person's kd/ka2, and a fast-route fraction ψ that reaches
  plasma at k_fast.
- **Values.**

  | Formulation | τ (min) | Fit |
  |---|---|---|
  | lispro / aspart | 8 | reference |
  | glulisine | 7 | — |
  | Fiasp | 4 | kd ×1.093, ka2 ×1.017, ψ 0.035 |
  | Lyumjev | 4 | kd ×1.159, ka2 ×1.131, ψ 0.033 |
  | regular | 10 | kd ×0.5, ka2 ×0.6 |

- **Evidence and tuning.** `fit_formulations` fits least squares to clamp contrasts, and the fit
  results are recorded in the code:
  - Lyumjev vs lispro (Clin Pharmacokinet 2020): AUC 0–15 ×7.2, AUC > 3 h ×0.60.
  - Fiasp vs aspart (Heise 2017): AUC 0–30 ×2.0, AUC > 3 h ×0.80.
  - Regular is **[unverified]** (Home 2015).
- **Interactions.** The Loop curve preset is chosen separately (`loop_preset`), so a mismatch between
  body and controller can be simulated.

### A4 Per-dose absorption jitter
Each bolus scales kd, ka2 and k_fast by ω ~ lnN, CV 15% (evidence/07: Heise 2017 repeat clamps, net of
the SI share). Basal gets no jitter.

### A5 Insulin action: disposal
- **Form.** `dX_D = −p2(X_D − SI_D·I)`. Uptake = `X_D·M(G)·risk(G) − SI_D·Ib·Gb`, where
  `M = Gb + κ(G − Gb)` above Gb and `M ∝ G` below Gb.
- **Values.** p2 0.05, p2E 0.018. κ lnN(0.15, 0.4). SI_D is calibrated (G8).
- **Tuning.**
  - LESSONS 2: Bergman's X·G (κ = 1) is a hidden glucose-effectiveness term that flattened every meal.
  - LESSONS 7: uptake must vanish with glucose, otherwise a stable hypoglycemic equilibrium appears.
  - LESSONS 20: the whole action tracks Loop's adult curve (13/51/77/91/99% at 1/2/3/4/6 h, against
    Loop's 17/50/76/91/100). Field forecast evidence outranks the 0.2 U/kg clamp for 2–5 U meal
    boluses; the clamp-fitted action made Loop stack insulin after every meal.

### A6 Insulin action: EGP suppression
- **Form.** `dX_E = −p2E(X_E − (I − Ib)/Ib)`, then
  `EGP = EGP_b·egp_mult·clip(1 − sE·si_mult·X_E, 0, 1 + sE)`.
- **Values.** EGP_b N(2.5, 0.33) mg/kg/min. sE comes from the EGP share (G8).
- **Evidence.** Hovorka 2004; 01 §4.1. The floor at 0 and the ~2× ceiling once insulin is gone are
  structural.

### A7 Renal excretion
`Rcl·(G − Rthr)` above Rthr; Rthr N(180, 25), Rcl lnN(0.003, 0.3). Evidence: 01 §4.3 (Johansen 1984).

### A8 S2013 hypoglycemia risk amplification
- **Form.** The published UVA/Padova S2013 term (Dalla Man 2014; 01 §4.5) is in the code at
  **λ = 0**.
- **Tuning.** LESSONS 10, ablation runs/a_*: with the term on, t<54 was 8.5% against the field's 0.13%.

### A9 Counter-regulation with HAAF
- **Form.** EGP boost `CRmax·h·σ((cr_g − G)/5)` with a 15-min time constant. The HAAF factor h falls
  while glucose is below 54 (2 h below → ×0.6, floor 0.3) and recovers over 60 h.
- **Values.** CRmax lnN(1.0, 0.5) mg/kg/min **[J]**; cr_g N(65, 5).
- **Evidence.** 01 §4.4: Cryer 2013, Dagogo-Jack 1993. No clamp-calibrated prior exists.
- **Tuning.** LESSONS 7: HAAF builds slowly, so it does not drain the response within the same low.

### A10 Gut: mixed meals
- **Form.** Each meal is a parcel Qsto1 → Qsto2 → Qgut, with kempt = kabs × a per-meal speed
  lnN(0, 0.4) and × 1/(1 + fat/60).
- **Values.** kempt = kabs = 0.045, giving a peak at 44 min and 90% absorbed by ~2 h.
- **Evidence.** ice meals tables, 116k pulses: peak 0.75 h, 90% by 1.83 h. Dalla Man 2006/2007.
- **Notes.** A slow-emptying tail (`meal_slow_frac`, Dalla Man kmin 0.008) exists and is OFF.

### A11 Gut: hypoglycemic acceleration
kempt × (1 + 1.5·σ((70 − G)/5)), about ×2.5 below ~60. Evidence: Schvarcz 1995; Russo 2005.

### A12 Fat and protein
- **Composition.** Per carb gram: meals 0.44 g fat and 0.45 g protein, snacks 0.2 each, ±50% per meal
  **[J; Snell-Bergeon 2009 split unverified]**.
- **Early fat effect.** Gastric emptying slows, as in A10.
- **Protein.** A late glucose parcel of 0.1 g per g protein, with a 90-min delay and 1/60 /min rates.
- **Late fat effect.** An SI dip `1 − ρ·min(fat, 80)/50`, ramping in over 2–3 h, full to 6 h, gone by
  10 h. ρ ~ U(0, 0.35) per person; the product is floored at 0.4.
- **Evidence.** Smart 2013, Wolpert 2013, Bell 2015/2020, Paterson 2016/2017 (01 §6.3).

### A13 Fast glucose (rescue, proactive snack, exercise carbs, grazing)
- **Form.** Fast parcels, kempt = kabs 0.06–0.08, plus A11. Bioavailability = the person's meal
  f × 1.25.
- **Tuning.** LESSONS 18: a fixed f = 1.0 made 1 g of rescue raise 13 mg/dL, against 3–4 in Brodows
  1984.

---

## 4. Time-varying modulators (`modulators.py`)

All modulators multiply SI or EGP and can be switched (`enabled`).

| Part | Form | Values | Evidence and tuning | Default |
|---|---|---|---|---|
| B1 Circadian SI | Visentin 7-class breakfast/lunch/dinner high/low profile; switches at 04/11/17 h with 1-h ramps; normalized to a daily mean of 1 | class probabilities 0.10/0.05/0.05/0.10/0.20/0.20/0.30; low/high ratio at **half** Visentin's swing | Visentin 2015. LESSONS 10: the full swing gave a 24-h amplitude of 0.23 against the field's 0.12. Visentin's per-day N(1, 0.2) is estimation precision (evidence/07), so `circ_noise = 0` | on |
| B2 Dawn | EGP ramp from onset U(02:00, 04:30) to a 07:00 peak, back to 0 by 10:00 | present in 52%; amplitude lnN(0.3, 0.6) × EGP_b **[J]** | Ostrovski 2020; Porcellati 2013 | on |
| B3 Day-level SI | independent per-day lognormal, changing at 04:00 with a 3-h ramp | CV 8% | evidence/07: repeat clamps 6–15% | on |
| B4 Intraday OU / slow drift | OU on log SI | — | no controlled-condition evidence (LESSONS 1) | **off** |
| B5 Menstrual | luteal SI dip, half-sine over the 14-day luteal phase; cycle N(28, 3) days; 63% respond | amplitude lnN(0.08, 0.5) | evidence/02 §3.1. Donors show no monthly rhythm (run:2026-10-11-ice-slow) | **off** (scenario) |
| B6 Illness | Poisson episodes (3/yr adults, 5/yr children), 1.5–15 days, ramps; SI drop 10–35%, EGP +0–15%; 20% gastrointestinal (SI up 5–15%, intake ×0.7) | — | Mehta 2010; Tinti 2025; ISPAD 2022 | on |
| B7–B11 | sleep loss, stress, alcohol, heat, prolonged-high resistance | — | evidence/02 | planned |

**Interactions.**
- `si_mult` scales disposal and EGP suppression together.
- Illness also cuts eating (`carb_scale` 0.7) for gastrointestinal episodes.
- Fat SI (A12) multiplies on top of all of these.

---

## 5. Exercise and daily activity (`exercise.py`, `behavior.py`)

ETH-style structure (Deichmann 2021/2023), with each mechanism named separately:

| Part | Form | Values | Evidence and tuning |
|---|---|---|---|
| C1 Acute uptake | insulin-independent uptake ∝ intensity × min(1, G/90) | ex_uptake lnN(3.0, 0.3) mg/kg/min at intensity 1 **[J]** | García-García 2015 (moderate ≈ −80 mg/dL/h in the lab) |
| C2 Acute SI | insulin action × (1 + 0.8·I) | α 0.8 **[J]** (Breton's 0.974 is on a filtered heart-rate state) | Breton 2008; Dalla Man 2009 |
| C2 Delayed SI | `dZ = 0.018·drive − Z/600`; drive = (I − 0.35)/(1 − 0.35) above 0.35 | τ_Z 600 min | Deichmann 2023 (sigmoid). LESSONS 23: walking built Z and held SI ~20% high around the clock (t<70 3.66 → 1.78 when removed) |
| C3 Absorption | SC absorption × (1 + 0.5·I) | **[J]** | Koivisto 1978 |
| C4 Anaerobic surge | EGP + surge × anaerobic share | 0 until calibrated | Marliss & Vranic 2002 |
| C5 Sessions | per-person 0–5/week; ~40 min lnN; intensity N(0.5, 0.12); time slot; pre-exercise carbs p 0.3 | — | T1DEXI (Riddell 2023), an active cohort, scaled down |
| C6 Light activity | walking bouts lnN(4/day), ~12 min, intensity ~0.25; half within 2 h after eating | **[J]**, sized against quiet-window step statistics (`quiet.py`) | evidence/00 D15 |

**Calibration targets (open).** T1DEXI's per-session glucose drop by starting glucose and by IOB, and
the rate of delayed nocturnal hypoglycemia.

---

## 6. Sensor (`sensor.py`)

**Structure.** Vettoretti 2019 / Facchinetti 2014. One parameter set per *session*, per family (G6,
G7, Libre 3, Libre 2, Medtronic).

```
IG     dIG/dt = (BG − IG)/τ
raw    gain(t)·IG + b0 + v(t)·h(IG) − compression(t)
gain   brand_gain·(a0 + slope·d + curve·d²)·(1 − d1·e^(−t/12h))
v      AR(2) on the 5-min grid, Student-t innovations
h(IG)  0.6 + 0.4·IG/130           (glucose-scaled noise)
out    EMA (Libre 3 only) → integer → clamp 39/401, or a gap
```

| Part | Values | Evidence and tuning |
|---|---|---|
| D1 Lag | τ lnN: G6 3.78, G7 3.5, Libre 3 1.8, Libre 2 2.4, Medtronic 8.4 min (log-sd 0.68) | Vettoretti 2019; device studies (03 §2.2) |
| D2 Calibration and drift | a0 N(0.95, 0.063); b0 N(6.35, 6.0); drift total N(0, 0.04) over the session, sampled jointly (linear + quadratic); day-1 deficit N(0.06, 0.05) decaying over 12 h; brand gain 1.0 (Medtronic 0.94) | Vettoretti 2019; Eichenlaub 2025 (brand sign vs YSI, within 1–3% of capillary) |
| D3 Noise | AR(2) (1.30, −0.42), Medtronic (1.367, −0.4816); σ: G6 N(3.19, 1), **G7 N(4.5, 1)**, Medtronic 1.59; Student-t df 4 (G6, G7); glucose scaling a = 0.6 | LESSONS 24: AR shape right, G7 rougher than G6 (eda L33). LESSONS 28: df 4 matches the donors' step kurtosis. LESSONS 29: constant-σ noise large enough for the excursions manufactures lows; the G7 accuracy tables (Garg 2022: ~8.5 mg/dL absolute error at 40–60, ~11.6 near 130, ~17 near 240) give the 0.6 + 0.4·IG/130 scaling |
| D4 Device smoothing | Libre 3 (twiist stream) EMA 0.35 **[J]** | eda L33 |
| D5 Compression lows | personal rate Gamma(2.37, 1/75.7) per night, asleep only; depth lnN(35, 0.4), duration lnN(45 min, 0.3); 72% gap / 25% dip / 3% floor | run:2026-10-11-ice-compression; Facchinetti 2016 shape |
| D6 Availability | warm-up per session (G7 27 min, G6 120, Libre 60); session 10/14/7 days (+ G7 grace 0.5 d); early failure 5% **[J]**; random gaps at measured per-family rates by length bin | runs/2026-10-15-additive-sensor/gaps.py (153 donors): G7 4.4 gaps/day, Libre 3 1.5, G6 1.7 |
| D7 Reporting | 5-min grid; integers; 39/401 clamps | eda L3, L6, L43 |

**Notes.**
- The CGM noise is never seen by the body. It reaches the controller and the person, and it changes
  outcomes only through their decisions.
- Compression withholds or dips readings; true glucose is unaffected.

**Under review (2026-10-15).** A literature review is in progress on how sensor error is built up:
fast noise, slower biases, on-device filtering and catch-up steps, and whether error scales with glucose
level. The donor data so far:
- Second differences of CGM grow with glucose level about as fast as the simulator's do.
- The donors carry more isolated jumps of 12 mg/dL or more than the simulator at 60–200 mg/dL
  (49–63 vs 33–45 per 1,000 steps). In donors these jumps sit inside quieter surroundings, and 12%
  reverse by more than half within 15 min, against 6% in the simulator. That is consistent with a
  bias process that resets or catches up (Pete's hypothesis), more than with white heavy-tailed
  innovations.

Fingersticks in the Tidepool pull cannot calibrate the slow components: 98.7% are mirrored CGM values,
leaving 346 real sticks from 70 donors, taken when the CGM was doubted.

---

## 7. Pump and infusion site (`device.py`)

The LoopEval trace records what was **commanded**; the body receives what was **delivered**. Loop never
sees the difference, so it shows up as phantom IOB.

| Part | Form and values | Evidence |
|---|---|---|
| E1 Pulses | patch-pump pulse truncation is done by LoopEval | ice L25 |
| E2 Basal flow error | per-device bias N(0, 1.5%) + AR(1) with τ 45 min; 1-h sd at 1 U/h: Omnipod 11%, Medtronic/Tandem 4.5%, twiist 3%; sd ∝ rate^−0.3 | Freckmann 2019; Ziegler 2021 (06 #2) |
| E3 Bolus error | sd = c/√U, floor 0.6%; Omnipod c 0.12, durable pumps 0.03, twiist 0.02 | 06 #3 |
| E4 Start-up transient | Omnipod N(+5%, 5%), Medtronic N(−5%, 5%), decaying over 4 h after each site change | 06 #4 |
| E5 Site life | absorption speed 0.9 → 1.15 by day 4 | Swan 2009 |
| E6 Failing site | p 0.15 per site **[J]**; absorbed fraction decays to 0.3 (τ 4 h); the person changes it after a long high | eda L52; Kanapka 2022 |
| E7 Silent partial occlusion | Poisson 0.4 per wear; delivered fraction U(0, 0.5) for ~1 h; releases part of the missed volume (≤ 1.2 U) on clearing | Gibney (06 #8, #10) |
| E8 Full occlusion + alarm | p 0.02 per wear **[J]**; delivery 0; alarm at V_alarm missed (Omnipod 3, Medtronic 2.5, twiist 0.5 U) | 06 #7 |
| E9 Bubble | p 0.2 per wear **[J]**; missed volume lnN(0.5 U) | 06 #9 |
| E10 Dislodgement | p 0.03 per wear; absorbed 0; never alarms | 06 #12 |
| E11 Lipohypertrophy | bioavailability 0.75–0.8 | Famulla 2016 (built, off) |
| E12 Leakage / backflow | not modelled: no quantitative source | 06 #11 |
| Site-change gap | 15 min without delivery **[unverified]** | 06 §4.2 |

**Interactions.**
- A failing site, dislodgement or full occlusion is only discoverable through glucose. While the person
  is awake and sees a reading above 250, they change the site with a 1/180 per-minute hazard (mean
  ~3 h). Occlusion alarms are answered at p 0.5 awake, or at the alarm wake probability asleep.
- Fix (LESSONS 30): the 1/180 hazard used to be checked only on reporting minutes, an effective rate
  of 1/900. Dislodged sites went unnoticed for ~15 waking hours, and two people spent 10+ hours at a
  true glucose of 500–1000 mg/dL.

---

## 8. Behavior: the person as a second controller (`behavior.py`)

Traits come from the person's donor template wherever ice measured them; otherwise from literature
priors (evidence/04). Behavior splits into **offense**, planned per day and blind to glucose, and
**defense**, which reacts only to what the person can *see*: the latest CGM reading (≤ 15 min old),
its 15-min trend, and Loop's IOB.

### F1 / F11 Eating
- **Form.** Three main meals (Camerlingo 2021 timing: breakfast lnN(2.078, 0.175) h, gaps drawn from
  Gumbel distributions; breakfast skipped with p 0.1) plus Poisson snacks at the person's measured
  pulse rate, placed on their own eating-hour distribution. Weekends shift by +60 min **[J]**.
- **Sizing.** Each event is sized against the person's *expected* day: carbs_day × share ÷ expected
  total share × lnN with the person's measured log-sd.
- **Tuning.**
  - LESSONS 16: eating comes as ~5.6 pulses/day of median 26 g-eq, not three big meals, so main meals
    are no larger than other events on average (`main_weight 1`).
  - LESSONS 30: sizing used to be renormalised to each day's actual event count, which coupled the
    Poisson snack count into meal size. Simulated p99.9 was 246 g against the donors' 156 g-eq.

### F2 Announcement and carb count
- P(entry) for meals and snacks comes from the measured entries per day.
- Count bias = ln(estimate_ratio/0.77) − 0.10.
- Per-meal count sd lnN(0.2, 0.3); big meals are under-counted (−0.1·ln(g/45)).
- Evidence: ice tables; Brazeau 2013.

### F3 Meal bolus
- P(bolus | entry) is measured.
- Timing class from the measured bolus lead: before / immediate / during / after.
- Calculator acceptance: 7.4% larger (×1.1–1.5), 6.9% smaller (×0.5–0.9).
- Evidence: Groat 2017; Datye 2018.

### F4 Corrections
- **Form.** A per-minute hazard while the person is awake, CGM is above their correction level (their
  measured correction glucose − 20), the trend is not falling, and nothing was bolused in the last
  120 min.
- **Tuning.** LESSONS 26: the hazard is sized by exposure, as the donor's correction rate over the
  donor's own time above 180.

### F5 Defense
- **Proactive snack.** Fires while awake when Loop-style projected glucose
  (CGM + 30·trend − ISF_setting·IOB) < onset N(80, 20), **and** CGM < onset + 50, **and** the trend is
  not rising. Size lnN(12 g); refractory 45 min. LESSONS 12: without the last two gates the person
  becomes a runaway snacker. ice L34/L69 measured the trait.
- **Rescue.** Fires when CGM < the person's measured rescue glucose − 5 (clipped to [55, 85]). Size is
  the measured rescue size × lnN(0, 0.3), after a latency of ~5 min. A re-check at 15 min leads to a
  re-treat with p ~0.34. Only 5% of rescues are logged **[J]**, following Pete's point that rescues
  are rarely logged.
- **Asleep.** Only an alarm (low alert ~76, urgent 55) can wake the person, with p_wake N(0.45, 0.2).
  Waking unaided with a low happens 1/16 of the time (Buckingham 2005; Schultes 2007).

### F6 Monitoring
Glances lnN(6/day); bedtime N(23:00, 50 min), wake N(07:00, 50 min). Evidence: Puhr 2020.

### F8 Site changes
Every N(3.0, 0.4) days at 19:30. Early changes follow a long high or an alarm (section 7). Evidence:
eda L52.

### F9 Grazing
Unlogged intake below the ice labeler's 12 g-eq gate: lnN(2/day) events of lnN(6 g), fast. **[J]**

### F10 Food dosed by hand
An un-entered eating event gets a bolus of the person's own gram estimate ÷ their CR setting, at the
person's measured rate. LESSONS 13: about 45% of "corrections" in the donor record are food dosed by
hand.

**Interactions.**
- Defense feeds rescue carbs into the gut (A13). Rescues are almost never logged, so Loop sees an
  unexplained rise; this is the rescue-carb confound the replay roles describe.
- Corrections and hand-dosed food boluses go to Loop as bolus requests. Loop computes the units from
  its recommendation, or takes absolute units for hand-dosed food.

---

## 9. Validation (`validate.py`, `meal_response.py`, `ice_check.py`, `quiet.py`, `vdips.py`)

- **Reference.** 206 pilot donors in 13-day blocks (`real_pilot.csv`). Glucose-shape statistics are
  split by sensor family.
- **Statistics.** eda's glucose features (`traits.block_features`), outcomes, low anatomy,
  delivered-insulin statistics and behavior rates, all computed by **one code path** for simulated
  people and donors.
- **Pass criterion.** KS p > 0.05 per statistic.
- **Twin.** Each simulated person is set against their own donor: median difference and rank
  agreement.
- **Meal response.** Run through the ice labeler on both sides (LESSONS 22).
- **Quiet windows.** Stretches with no labeled eating or bolus for 4 h are where the sensor dominates
  (LESSONS 24, 28).

**Status, cohort c24** (56 people × 14 days, f11386e): 19 of 42 statistics match.

Matching:
- Outcomes: mean 153 (donors 151); TIR 72.9 (71.7); t<70 1.55 (1.66); t<54 0.19 (0.23); lows per day.
- Insulin: TDD 36.9 (37.0).
- Behavior: user boluses 3.02 (3.45); carb entries.
- Twin rank agreement: TDD 0.91, entries 0.97, boluses 0.93. TIR rank agreement is only 0.25.

Failing:
- Distribution shape: CV 37.5 (34.6), skew 1.28 (0.89), Box-Cox λ −0.15 (−0.03; donors are close to
  lognormal).
- Time-series shape: Hurst exponents, autocorrelation dip and zero crossing, volatility clustering.
- Between-day fraction 0.24 (0.10), 24-h amplitude.
- Insulin distribution: median nonzero dose, p99.

The simulator's *true* glucose is already more skewed than lognormal (Box-Cox −0.28), so the excess
skew comes from the plant, not the sensor. Cohort c25 tests the two LESSONS 30 fixes, which remove the
500–1000 mg/dL episodes.

---

## 10. Switches (`cohort.py`)

- `--disable a,b`: modulators (circadian, dawn, day, illness), exercise, site_failure, pump_faults,
  compression, behavior_defense, fat, risk, counterreg.
- `--enable`: perfect_person (diagnostic: every meal entered exactly and bolused at the meal, no
  snacks, no exercise), menstrual, intraday, drift. `settings_mismatch=False` gives the controller the
  truth.
- `--set`: meal_k, meal_slow, meal_slow_k, isf_w, sensor_sigma, sensor_df, sensor_hetero, sensor_a1,
  sensor_a2.

Two diagnostic tests should be run for every new physiology or behavior path (LESSONS 18):
- Truth settings + perfect person + all disturbances off: the person must sit near their rest level.
- A two-arm probe against a control body (LESSONS 6).

---

## 11. Open items

1. **Distribution and time-series shape.** Excess skew and CV in true glucose; long-range persistence
   (Hurst 0.04 vs 0.24); volatility clustering; between-day spread.
2. **Sensor error structure.** A bias process with resets or catch-up versus white heavy-tailed
   innovations; log-scale versus affine glucose scaling. Literature review in progress.
3. **Meal response.** Rise 58 vs 72 mg/dL; peak 95 vs 111 min; +11 vs +36 at 3 h.
4. **Per-person drivers of TIR.** Twin rank agreement for TIR is 0.25.
5. **Calibration.** Exercise against T1DEXI; counter-regulation against donor low anatomy.
6. **Wear statistic.** Its definition differs between real and simulated data (real counts timestamps,
   so it always reads 1.0). Fix in `core_stats`.

---

## Key references

Full lists, with what was verified in each, are in `evidence/01 §8`, `02 References`, `03 §5`,
`04 References`, `06 References` and `07 References`.

- Bergman RN et al. Am J Physiol 1979;236:E667. doi:10.1152/ajpendo.1979.236.6.E667
- Hovorka R et al. Physiol Meas 2004;25:905. doi:10.1088/0967-3334/25/4/010
- Dalla Man C, Rizza RA, Cobelli C. IEEE TBME 2007;54:1740. doi:10.1109/TBME.2007.893506
- Dalla Man C et al. (UVA/Padova S2013) J Diabetes Sci Technol 2014;8:26. doi:10.1177/1932296813514502
- Visentin R et al. Diabetes Technol Ther 2015;17:1. doi:10.1089/dia.2014.0192
- Cappon G et al. (ReplayBG) IEEE TBME 2023;70:3105. doi:10.1109/TBME.2023.3286856
- Schiavon M et al. IEEE TBME 2018;65:2079. doi:10.1109/TBME.2017.2784101
- Heise T et al. (Fiasp) Clin Pharmacokinet 2017;56:551. doi:10.1007/s40262-017-0514-8
- URLi vs lispro. Clin Pharmacokinet 2020. doi:10.1007/s40262-020-00903-0
- Smart CE et al. Diabetes Care 2013;36:3897. doi:10.2337/dc13-1195
- Wolpert HA et al. Diabetes Care 2013;36:810. doi:10.2337/dc12-0092
- Dagogo-Jack SE et al. J Clin Invest 1993;91:819. doi:10.1172/JCI116302
- Brodows RG et al. JAMA 1984;252:3378
- Deichmann J et al. PLoS Comput Biol 2023;19:e1010289. doi:10.1371/journal.pcbi.1010289
- García-García F et al. Sports Med 2015;45:587. doi:10.1007/s40279-015-0302-2
- Riddell MC et al. (T1DEXI) Diabetes Care 2023;46:704. doi:10.2337/dc22-1721
- Ostrovski I et al. Can J Diabetes 2020;44:157. doi:10.1016/j.jcjd.2019.08.003
- Mehta NN et al. Diabetes 2010;59:172. doi:10.2337/db09-0367
- Facchinetti A et al. IEEE TBME 2014;61:620. doi:10.1109/TBME.2013.2284023
- Facchinetti A et al. Diabetes Technol Ther 2016;18:264. doi:10.1089/dia.2015.0250
- Vettoretti M et al. Sensors 2019;19:5320. doi:10.3390/s19235320
- Breton M, Kovatchev B. J Diabetes Sci Technol 2008;2:853
- Famulla S et al. Diabetes Care 2016;39:1486. doi:10.2337/dc16-0610
