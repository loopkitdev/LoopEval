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
- **Form.**
  `CSF = 1.18 × [1.85 × ISF_tdd × TDD/500 × lnN(0, 0.15)]^0.5 × [settings ISF/CR × lnN(0, 0.15)]^0.5`.
  The first factor is the population g-eq calibration; the second is the person's own settings. Both
  are blended with ISF's weight. Bioavailability f = CSF·BW·VG/1000, clipped to [0.3, 1.0]. When f
  would exceed 1, VG shrinks instead.
- **Evidence.** ice L54: a meal pulse is 1.30 g-eq per entered gram. ice's g-eq is settings-free:
  ISF_tdd/(500/TDD).
- **Tuning.**
  - LESSONS 14: physics with f 0.9, a tracer-glucose figure, gave ~1.7× the donors' rise.
  - LESSONS 17: the 1.30 ratio must be read in g-eq units.
  - LESSONS 27, 33, 37: the constants are always set *through* the ice labeler, because glucose
    effectiveness erodes the pulse before ICE sees it. It reads 1.15 against the donors' 1.21, and the
    labeled meal response is 17.0 mg/dL per 10 g (donors 17.1), peaking at 110 min (111).
  - LESSONS 37: drawn independently of the settings, the settings-CR / true-CR mismatch spread 2× and
    multiplied post-meal lows. People tune CR on their own body, as they tune ISF (G2).
- **Interactions.** Every carbohydrate path shares this calibrated f. Rescues and snacks use f × 1.25
  (LESSONS 18). The person's food also covers their expected activity (C7).

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

### A10 Gut: mixed meals and gastric emptying
- **Form.** Each meal is a parcel Qsto1 → Qsto2 → Qgut. The stomach empties *in energy terms*, and all
  parcels in it share the capacity: E = Vmax·S/(Km + S), with S the total kcal (carbohydrate 4,
  protein 4, fat 9 kcal/g). Small meals behave first-order at rate Vmax/Km; large meals approach
  zero-order at Vmax. Each meal also gets a speed multiplier lnN(0, 0.4) for composition.
- **Values.** Vmax 3 kcal/min, Km 60 kcal (kempt 0.05), kabs 0.05. A 25 g snack peaks at ~45 min; a
  121 g mixed meal reaches 50% at ~4 h, a carbohydrate-only one at ~2 h.
- **Evidence.**
  - Emptying is energy-rate limited: Brener 1983 (2.1 kcal/min), Hunt 1985 (2.5), Calbet 1997, Marathe
    2013 review (1–4).
  - Fat, protein and carbohydrate slow emptying equally per kcal (Hunt & Stubbs 1975).
  - Elleri 2013 (121 g, tracer, T1D): 50% appearance at 100–175 min.
  - Full write-up: evidence/09.
- **Tuning.**
  - LESSONS 33: fixed first-order emptying over-skewed glucose (1.41 vs 0.89). Saturating emptying gives
    the donors' lognormal shape (0.93). Carb sensitivity was re-read through the labeler afterwards.
  - LESSONS 44: a **fast liquid phase**. 20% of each meal's carbohydrate empties fast (kempt = kabs 0.08)
    outside the energy ceiling (Hunt 1985; Calbet 1997; share [J]). It turns true-glucose increment skew
    from −0.33 to −0.06 (meals rise faster than they fall).
- **Notes.**
  - Fat's early slowing of emptying is carried by its kcal; the separate 1/(1 + fat/60) factor applies
    only when the ceiling is off.
  - Hyperglycaemic slowing (`ge_hyper`; Schvarcz 1997, Fraser 1990) is built but off: at its [J] size
    it over-smoothed glucose (skew 0.60).
  - The slow-tail option (`meal_slow_frac`) is off.

### A11 Gut: hypoglycemic acceleration
kempt × (1 + 1.5·σ((70 − G)/5)), about ×2.5 below ~60. Evidence: Schvarcz 1995; Russo 2005.

### A12 Fat and protein
- **Composition.** Per carb gram: meals 0.44 g fat and 0.45 g protein, snacks 0.2 each, ±50% per meal
  **[J; Snell-Bergeon 2009 split unverified]**.
- **Early fat effect.** Gastric emptying slows, as in A10.
- **Protein.** A late glucose parcel of 0.1 g per g protein, with a 90-min delay and 1/60 /min rates.
- **Late fat effect.** An SI dip `1 − ρ·min(fat, 80)/50`, ramping in over 2–3 h, full to 6 h, gone by
  10 h. ρ ~ U(0.1, 0.6) per person (mean 0.35 reproduces Wolpert 2013's +42% insulin at 60 g fat; LESSONS 46); the product is floored at 0.4.
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
| B1 Circadian SI | Visentin 7-class breakfast/lunch/dinner high/low profile; switches at 04/11/17 h with 1-h ramps; normalized to a daily mean of 1 | class probabilities 0.10/0.05/0.05/0.10/0.20/0.20/0.30; low/high ratio N(0.40, 0.23), Visentin's **full** measured swing (`circ_swing` 1.0) | Visentin 2015. LESSONS 38: 24-h amplitude 0.14 vs the donors' 0.13. The earlier halving (LESSONS 10) compensated for fixed-rate emptying. Visentin's per-day N(1, 0.2) is estimation precision (evidence/07), so `circ_noise = 0` | on |
| B1b Basal-need profile | EGP × the donor's local hourly basal-schedule shape^0.5 (Loop's schedule uses the shape as is) | per-donor, overnight ~0.91 | LESSONS 48: day/night insulin 1.40 vs donors 1.38 | on |
| B2 Dawn | EGP ramp from onset U(02:00, 04:30) to a 07:00 peak, back to 0 by 10:00 | present in 52%; amplitude lnN(0.3, 0.6) × EGP_b **[J]** | Ostrovski 2020; Porcellati 2013 | on |
| B3 Day-level SI | independent per-day lognormal, changing at 04:00 with a 3-h ramp | CV 8% | evidence/07: repeat clamps 6–15% | on |
| B4 Intraday OU / slow drift | OU on log SI | — | no controlled-condition evidence (LESSONS 1) | **off** |
| B5 Menstrual | luteal SI dip, half-sine over the 14-day luteal phase; cycle N(28, 3) days; 63% respond | amplitude lnN(0.08, 0.5) | evidence/02 §3.1. Donors show no monthly rhythm (run:2026-10-11-ice-slow) | **off** (scenario) |
| B6 Illness | Poisson episodes (3/yr adults, 5/yr children), 1.5–15 days, ramps; SI drop 10–35%, EGP +0–15%; 20% gastrointestinal (SI up 5–15%, intake ×0.7) | — | Mehta 2010; Tinti 2025; ISPAD 2022 | on |
| B11 Hyperglycaemia-induced resistance | state H → 0.26·clip((G − 140)/220, 0, 1), τ 12 h **[J]**; SI × (1 − H) | 24 h at 20 mM lowers uptake 26% | Vuorinen-Markkola 1992; Yki-Järvinen 1987 (LESSONS 43) | on |
| B7–B10 | sleep loss, stress, alcohol, heat | — | evidence/02 | planned |

**Interactions.**
- `si_mult` scales disposal and EGP suppression together.
- Illness also cuts eating (`carb_scale` 0.7) for gastrointestinal episodes.
- Fat SI (A12) multiplies on top of all of these.

---

## 5. Exercise and everyday activity (`exercise.py`, `behavior.py`)

ETH / UVA-style structure (Deichmann 2021/2023; Dalla Man 2009), with each mechanism named separately.
Intensity I is %VO2-reserve (≈ %HR-reserve; Swain 1997). It is filtered through a 7-min lag (Y) before
it acts. Evidence: evidence/02 §1 (structured exercise) and evidence/10 (everyday activity).

| Part | Form | Values | Evidence and tuning |
|---|---|---|---|
| C1 Insulin-independent uptake | ex_uptake·gain·Y·G/Gb (mass action, fades as glucose falls) | ex_uptake lnN(3.0, 0.3) mg/kg/min at I = 1 **[J]** | García-García 2015; Dhaliwal 2025 (ΔCGM grows with starting glucose: −11 / −33 / −52) |
| C2 Acute SI | insulin action × (1 + 2.0·gain·Y) | α 2.0 | Romeres 2021 clamp: +81–155% insulin-dependent uptake at I ≈ 0.6 |
| C2 Delayed SI | `dZ = 0.018·gain·drive − Z/600`; drive = (Y − 0.12)/(1 − 0.12) above 0.12 | τ_Z 600 min | UVA / Deichmann thresholds at light intensity (evidence/10 §7.3). LESSONS 23 had it at 0.35; LESSONS 34 restored the evidence |
| C3 Absorption | SC absorption × (1 + 0.5·Y) | upper bound | Koivisto 1978; Pitt 2020 |
| C4 Anaerobic surge | EGP + surge × anaerobic share | 0 until calibrated | Marliss & Vranic 2002 |
| C5 Structured sessions | per-person 0–5/week; ~40 min lnN; intensity N(0.5, 0.12); time slot; pre-exercise carbs p 0.3 | — | T1DEXI (Riddell 2023), scaled down |
| C6 Everyday episodes | per person lnN(2/day, 0.55) × day gamma(3); duration lnN(18 min, 0.75) in 5–150; intensity (MET − 1)/(METmax − 1) × duty 0.7, MET lnN(3.0, 0.2), 10% brisk U(4.5, 6); start times on the UK Biobank day profile (0.04 / 0.34 / 0.39 / 0.23), awake only; 40% after eating **[J]** | METmax lnN(9, 0.25), lower with age | evidence/10 §7.2 (T1DEXI, NHANES, UK Biobank, 2024 Compendium) |
| C6b Waking background | intensity lnN(0.06, 0.4) while awake | **[J]** | NHANES light-activity minutes |
| C7 Energy balance | the person eats the glucose their expected activity uses: a clamp probe (one day, true basal, glucose at 140, active vs rest) added to daily carbs | 7–38 g/day, median ~28 | LESSONS 34: without it the mean fell to 136 and TDD to 33 |
| — Responsiveness | `gain` per person lnN(0, 0.5) on C1, C2 and the delayed state | — | Jaloli (ten-fold spread in 9 people) |

**Validation** (`activity_check.py`): ΔCGM over each episode by starting glucose and IOB, and the
episode low rate by duration, against Dhaliwal 2025. Lows now match the donors overall; daytime lows
with no bolus run 0.14 against the donors' 0.19 per day.

---

## 6. Sensor (`sensor.py`)

**Structure.** Vettoretti 2019 / Facchinetti 2014, extended with Biagi 2017's common component and a
transient-bias process. Most parameters are drawn once per *session*, per family (G6, G7, Libre 3, Libre 2,
Medtronic).

```
IG     dIG/dt = (BG − IG)/τ
raw    gain(t)·IG + b0 + [v(t) + c(t)]·h(IG) + trans(t) − compression(t)
gain   brand_gain·(a0 + slope·d + curve·d²)·(1 − d1·e^(−t/12h))
v      sensor-specific AR(2) on the 5-min grid, Student-t innovations (df 4)
c      error common to co-located sensors: AR(3), per person, continuous across sessions
h(IG)  √(q² + (1 − q²)·(IG/130)²)      additive floor ⊕ proportional, q 0.5
trans  transient biases: ±A in one reading, first-order recovery τ 10 min
out    EMA (Libre 3 only) → integer → clamp 39/401, or a gap
```

**How it is calibrated.** Only against sensor-only targets, never against donor CGM roughness
(LESSONS 31). Donor roughness also contains real glucose movement, so fitting to it would let the sensor
absorb missing physiology. `sensor_fit.py` runs two independent sensors over the same simulated true
glucose and scores them against:
- the FDA iCGM accuracy tables (bias and MARD by glucose range, binned by the comparator and by the CGM
  value);
- two-sensor precision (PARD);
- MAD-by-level elasticity.

Then `quiet.jump_signature` checks the jump anatomy against donors.

| Part | Values | Evidence and tuning |
|---|---|---|
| D1 Lag | τ lnN: G6 3.78, G7 3.5, Libre 3 1.8, Libre 2 2.4, Medtronic 8.4 min (log-sd 0.68) | Vettoretti 2019; Garg 2022; Alva 2020. Commercial outputs are already lag-compensated: do not add the 5–6 min physiological delay (Basu 2013) |
| D2 Calibration | G7 a0 N(0.98, 0.04), b0 N(3, 3); G6 a0 N(0.96, 0.05), b0 N(2, 3); Libre 3 a0 N(0.965, 0.03), b0 N(0, 2); drift N(0, 0.04) over the session; day-1 deficit N(0.06, 0.05) decaying over 12 h | Fitted (LESSONS 31). The G6 Vettoretti spread (b0 sd 6, a0 sd 0.063) gave a G7 PARD of 14% against 8.9% |
| D3 Sensor-specific noise | AR(2) (1.30, −0.42); σ G7 N(2.8, 0.8), G6 N(2.5, 0.8), Libre 3 N(1.5, 0.5); t df 30 for G7 (near-Gaussian), 4 for G6 / Libre 3; q 0.5 | Shape from Vettoretti 2019; tails from Breton & Kovatchev 2008 (Johnson S_U); size fitted |
| D3b Common error | AR(3) (1.584, −0.884, 0.180); σ G7 2.0, G6 2.5, Libre 3 3.0 | Biagi 2017: in co-located Enlites the common component (var 3.98) exceeds the sensor-specific one (2.54). It adds accuracy error that two-sensor precision does not see, which is what the FDA tables require |
| D3c Transient biases | per-session rate lnN(median, 0.9) events/day: G7 8, G6 6, Libre 3 4 **[J]**; amplitude lnN(12, 0.4) mg/dL; 55% read low first; τ 10 min | Donor quiet-window reversals (LESSONS 32): G7 6.6 vs donors 6.8 per 1,000 steps; whole jump anatomy matched |
| D3d Noise-level wander | σ × exp(z − sd²), z log-OU with sd 0.7 (G7 0.6), τ 8 h **[J size]**; variance-preserving | Facchinetti 2011 (SNR varies within a sensor). LESSONS 42: stationary noise erased the CGM's volatility clustering, Hurst and dispersion; with the wander, the jump anatomy matches the donors class by class |
| D4 Device smoothing | Libre 3 (twiist stream) EMA 0.35 **[J]** | eda L33 |
| D5 Compression lows | personal rate Gamma(2.37, 1/75.7) per night, asleep only; depth lnN(35, 0.4), duration lnN(45 min, 0.3); 72% gap / 25% dip / 3% floor | run:2026-10-11-ice-compression; Facchinetti 2016 shape. Published rates are ~0.3/day (Idi 2025; Lobo 2026); the donor detector is stricter |
| D6 Availability | warm-up per session (G7 27 min, G6 120, Libre 60); session 10/14/7 days (+ G7 grace 0.5 d); early failure 5% **[J]**; random gaps at the measured per-family rates by length bin | runs/2026-10-15-additive-sensor/gaps.py (153 donors) |
| D7 Reporting | 5-min grid; integers; 39/401 clamps | eda L3, L6, L43 |

**Fit quality** (adult FDA arms):

| Family | Bias / MARD by range | PARD | Loss |
|---|---|---|---|
| G7 | 3.9 / 4.1 / 0.9 / −2.4 / −6.6 and 13.3 / 11.7 / 8.2 / 7.4 / 7.2% (FDA 4.0 / 1.1 / 1.1 / −1.9 / −6.6 and 14 / 10.7 / 8.6 / 7.4 / 6.4) | 9.5% (8.9) | 1.35 |
| Libre 3 | — | 6.6% (6.8) | 3.5 |
| G6 | — | 9.9% (9.0) | 7.1 |

Libre 3 reads too little high at a true value below 54. G6 is fitted only to the CGM-binned table,
whose pattern is irregular.

**How sensor error scales with glucose.** Total error versus YSI grows at about the 0.7 power of glucose
(FDA tables: G7 0.69, Libre 3 0.73, G6 0.72). That sits between additive error (0) and lognormal error
(1): proportional above ~100 mg/dL, with an additive floor of ~6–7 mg/dL below. In the model, most of
the proportional part comes from the per-session calibration gain. The fast noise keeps its floor.

**Notes.**
- The CGM error is never seen by the body. It reaches the controller and the person, and changes
  outcomes only through their decisions.
- Compression withholds or dips readings; true glucose is unaffected.
- Rise-suppression and catch-up filters exist in manufacturer patents (Dexcom's "cone of possibility",
  Abbott's dual-bank weighting). Donor catch-ups already match the model without them (LESSONS 32), so
  they are not modelled.
- Medtronic and Libre 2 keep their published models (Biagi 2017, Vettoretti) and are not FDA-fitted.

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
| E6 Failing site | p 0.012 per site; with E8 and E10 it sums to Kanapka's 1.9% of adult sets ending in prolonged hyperglycaemia (youth ×3, 5.8%) **[J split]**; absorbed fraction decays to 0.3 (τ 4 h) | Kanapka 2022 (LESSONS 43: the earlier 15% + 2% + 3% was ~6× the literature) |
| E5b Set-age efficacy | absorbed fraction × (1 − 0.025·max(0, age − 1 day)) **[I]** | Sampson Perrin 2015 (fasting 126 / 133 / 147 on days 1 / 3 / 5); Simic 2021 (extent down, rate up) |
| E7 Silent partial occlusion | Poisson 0.4 per wear; delivered fraction U(0, 0.5) for ~1 h; releases part of the missed volume (≤ 1.2 U) on clearing | Gibney (06 #8, #10) |
| E8 Full occlusion + alarm | p 0.003 per wear **[J split]**; delivery 0; alarm at V_alarm missed (Omnipod 3, Medtronic 2.5, twiist 0.5 U) | 06 #7 |
| E9 Bubble | p 0.2 per wear **[J]**; missed volume lnN(0.5 U) | 06 #9 |
| E10 Dislodgement | p 0.004 per wear (prolonged-hyperglycaemia endings) **[J split]**; absorbed 0; never alarms | 06 #12; Kanapka 2022 |
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
- **Sizing.** Daily intake is regulated over 24 h. A day total = carbs_day × exp(z_d) (+ activity
  intake, C7), with z AR(1) across days (CV 0.22, ρ 0.29; Tarasuk & Beaton 1992, Levitsky 2017). It
  is shared by the day's events in proportion to their drawn sizes (the person's measured log-sd), with
  full 24-h compensation (`intake_comp` 1 [J]).
- **Tuning.**
  - LESSONS 16, 47: eating comes as ~5.6 pulses/day; main meals are 1.9× a snack (`main_weight`,
    Camerlingo 2021). Entered grams per entry then match the donors (32.3 vs 32.6), and so does the
    labeled pulse-size distribution.
  - LESSONS 30: unregulated renormalization fattened the size tail; the AR day total keeps it at p99.9
    146 g.
  - LESSONS 39: eaten CV is 0.24. Entered-carb CV is still 0.54 against the donors' 0.40, because entry
    choices are independent per event.

### F2 Announcement and carb count
- P(entry) for meals and snacks comes from the donor's **raw** entries per day (`entries_raw`: 2.97
  median, entries within 30 min merged), not ice's labeled count (2.07) (LESSONS 36).
- Person count bias N(−0.10, 0.10) (Brazeau 2013: 63% under-estimated). The donor's labeled
  entered/pulse ratio is mostly labeler noise per person (LESSONS 35).
- Per-meal count sd lnN(0.2, 0.3); big meals are under-counted and snacks over-counted
  (−0.1·ln(g/45)).

### F3 Meal bolus and top-ups
- P(bolus | entry) = the donor's raw boluses with an entry ÷ raw entries.
- Timing class from the measured bolus lead: before / immediate / during / after. Labeled lead times
  match the donors' through the same labeler.
- Calculator acceptance: 7.4% larger (×1.1–1.5), 6.9% smaller (×0.5–0.9). Evidence: Groat 2017;
  Datye 2018.
- **Split boluses:** when the donor gives more than one bolus per entry (1.09 median), the excess is the
  chance of a split dose: 60% at the entry and Loop's recommendation 10–30 min later [J split]
  (LESSONS 47).
- **Top-ups:** with the donor's raw top-up rate per meal bolus (0.26/day median), a second bolus at
  Loop's recommendation 20–60 min later, if CGM is above 120 and not falling **[J on the condition]**.

### F4 Corrections
- **Form.** A per-minute hazard while the person is awake, CGM is above their correction level (their
  measured correction glucose − 20), the trend is not falling, and nothing was bolused in the last
  120 min.
- **Tuning.** LESSONS 26: the hazard is sized by exposure, as the donor's correction rate over the
  donor's own time above 180. The rate is the donor's raw lone-bolus rate, split into corrections and
  hand-dosed food (F10) by the donor's own labeled split (LESSONS 36).

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

### F13 Settings edits
Dated multiplicative changes to the basal / ISF / CR schedules at the donor's measured rate per setting
(median 0.03/day basal, 0.016 ISF / CR). Size lnN(3.6%, σ 1.06), random sign **[J]**. They are written as
eras into the exported schedules (LESSONS 41).

### F12 Temporary Overrides
- **Form.** Planned with the events they serve, at the donor's own rates and median settings
  (`templates.add_override_rates`):
  - less-insulin overrides start 0–30 min before an activity episode;
  - lowered-target overrides start 15–60 min before a carb entry (pre-meal);
  - raised-target-only overrides go at random waking times.

  Durations are lnN(donor median, 0.6), 0.25–12 h. They are written into the exported therapy timeline
  (`overrideWindows`); LoopEval applies each from its start, causally.
- **Evidence.** 19,732 donor windows (LESSONS 40): less insulin 45% (factor 0.60, 1.4 h), more
  insulin 17% (1.33, 1 h, reactive to highs), target only 37% (~90, 1 h).
- **Not modelled.** The reactive more-insulin class needs plant-sent overrides
  (`docs/handoffs/2026-10-16-additive-plant-overrides.md`).
- **Notes.** Every day is planned at World construction, so the export and the plant's re-simulation
  agree (`Behavior.plan_all`).

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

**Status, cohorts c32circ / c34** (112 people × 14 days, f11386e): 21 of 50 statistics match.

Matching (KS p > 0.05, or within a few percent):
- Outcomes: TIR 74.9 (donors 71.7); time above 180 23.1 (25.6); t<70 1.7 (1.7); t<54 0.17 (0.23);
  lows per day 1.02 (1.08).
- Distribution: CV 35.2 (34.6); skew 0.93 (0.89; KS just fails); Box-Cox −0.05 (−0.03).
- 24-h amplitude: 0.14 (0.13).
- Insulin: TDD 37.5 (37.0); TDD day-to-day CV 17.2 (17.0); manual U/day 10.8 (12.0); top-1% share.
- Behavior: carb entries; short-range Hurst; CGM jump anatomy.
- Sensors: FDA accuracy tables.
- Meal response: 17.0 mg/dL per 10 g (17.1); peak 110 min (111).

Failing:
- Long-range Hurst 0.11 (0.24); volatility clustering 0.06 (0.12); rate dispersion 2.5 (3.6).
- Between-day fraction 0.17 (0.10); day/night insulin ratio 1.21 (1.38).
- Step kurtosis and skew; user boluses 3.3 (4.6).
- Post-meal lows 3× the donors'.
- Twin TIR rank agreement ~0.25.

---

## 10. Switches (`cohort.py`)

- `--disable a,b`: modulators (circadian, dawn, day, illness), exercise, site_failure, pump_faults,
  compression, behavior_defense (rescues, proactive snacks), graze, overrides, fat, risk, counterreg.
- `--enable`: perfect_person (diagnostic: every meal entered exactly and bolused at the meal, no
  snacks, no exercise), menstrual, intraday, drift. `settings_mismatch=False` gives the controller the
  truth.
- `--set`: meal_k, meal_slow, meal_slow_k, isf_w, csf_mult, ge_kcal, ge_hyper, ins_p2, ins_p2e,
  circ_swing, sensor_sigma, sensor_df, sensor_hetero, sensor_hq, sensor_a0(sd), sensor_b0(sd),
  sensor_common, sensor_trate, sensor_tamp, sensor_ttau, sensor_a1, sensor_a2.

The sensor can be fitted offline, without a closed loop: `sensor_fit.py` (FDA tables) and
`quiet.sim_jumps(..., resensor=...)` (jump anatomy).

Two diagnostic tests should be run for every new physiology or behavior path (LESSONS 18):
- `selfcheck.py`: truth settings + perfect person + all disturbances off, with fat resistance and the
  emptying ceiling off. The post-absorptive night (00–06) must sit within 30 of the rest level, and no
  day may run away.
- A two-arm probe against a control body (LESSONS 6).

---

## 11. Open items

1. **Slow structure.** Long-range persistence, volatility clustering and rate dispersion are about
   half the donors'. Between-day spread is larger than the donors'. Candidate named factors from the
   catalog, not yet modelled: stress, sleep loss, prolonged-high insulin resistance.
2. **Post-meal lows** 3× the donors'; meal-time dosing against slow emptying.
3. **Bolus count** 3.3 vs 4.6/day: lone and top-up boluses short.
4. **Per-person drivers of TIR.** Twin rank agreement ~0.25.
5. **Calibration.** Counter-regulation against donor low anatomy; G6 and Libre 3 sensor tails.
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
