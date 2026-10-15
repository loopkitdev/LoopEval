# Evidence 02 — Non-food life factors as time-varying model inputs

Scope: the big non-meal disturbances an additive T1D patient simulator needs so it can evaluate AID
controllers closed-loop. Each factor gets its frequency, onset, magnitude, time course, between-person
spread, and a proposed modelling form. T1D human data come first; healthy-volunteer data are used
only where no T1D data exist, and are labelled as such.

**Verification legend.** A plain citation means the number was checked against the abstract or full
text (via Europe PMC / PMC / publisher) during this review. **[unverified]** means the number or
DOI comes from memory or a secondary source and was not checked against the primary paper.
**[derived]** means a value computed here from verified numbers, or a modelling choice proposed
here rather than a value taken from a paper.

**How to read magnitudes under AID.** In AID users the controller absorbs part of every
disturbance, so the field footprint is split between a glucose change and a delivered-insulin
change. A modest glucose shift (for example luteal mean glucose +6–12 mg/dL) can sit on top of a
larger rise in insulin need (TDD +3–11 %). The simulator should take the **physiological**
parameter change (SI, EGP, absorption) as its input and let the controller produce the footprint.
Field TDD changes are calibration targets for that footprint, not inputs.

---

## Summary table

| Factor | Model form (proposed) | Magnitude | Onset / duration | Frequency | Key refs |
|---|---|---|---|---|---|
| Moderate aerobic exercise (acute) | Additive insulin-independent uptake ∝ intensity·G (Breton βYG), plus SI multiplier (1+αZ), plus faster s.c. insulin absorption | Lab: −4.4 mmol/L/h vs rest (≈ −80 mg/dL/h) when insulinised. Real world: median −12 (15–30 min) to −24 (60–120 min) mg/dL per session; strongly depends on start BG and IOB | Starts within minutes (τ≈5 min HR filter); the uptake term stops within ~30 min of the end | Real-world logged PA on ~60 % of days, ~5.7 sessions/week, mean 41 ± 23 min (T1DEXI CSII users) | García-García 2015; Dhaliwal 2025; Riddell 2023; Breton 2008 |
| Post-exercise / nocturnal delayed effect | Slow SI multiplier state Z (τ ≈ 600 min; ETH model) | Glucose requirement still raised up to 11 h (midday exercise) or biphasic at 7–11 h (late afternoon; ≈ +10 g IV glucose per 70 kg). Nights with hypo ≤60 mg/dL: 48 % vs 28 % | Up to 11–17 h measured; models assume up to ~24–48 h | Follows every moderate/long session; more after afternoon/evening sessions | Davey 2013; McMahon 2007; Tsalikian 2005; Deichmann 2023 |
| Intense / HIIT / anaerobic | Additive catecholamine-driven EGP pulse (Ra ×7–8, Rd ×4) | Glucose rises during and after >80 % VO₂max; sustained hyperglycaemia in T1D without a post-exercise insulin rise | Pulse lasts the bout and 30–60 min after [unverified duration]; delayed SI rise still follows | A minority of sessions (73 % of AID sessions were aerobic in RAPPID) | Marliss & Vranic 2002; Purdon 1993; Sigal 1994 |
| Resistance | Smaller uptake term; little acute change | −9 ± 36 mg/dL per ~30 min session | As aerobic, smaller | ~8 % of real-world sessions (637/8171) | Riddell 2023; Dhaliwal 2025 |
| Febrile / respiratory illness (incl. COVID-19) | SI multiplier ≈ 0.65–0.9, plus EGP increase; ketosis flag | Endotoxin in healthy adults: SI −35 %. T1D CGM: mean glucose +8 (AID children) to +15 mg/dL (adults, COVID-19); auto-correction share 36 → 42 % | Mean episode ~3 days (children); COVID-19 effect lasts ~2 weeks, recovery within 2 weeks | Adults ~2–4 colds/yr [unverified]; symptomatic influenza 4.4 %/yr adults, 12.7 % children | Mehta 2010; Tinti 2025; Longo 2022; Kim 2025; Somes 2018 |
| Gastroenteritis | Lower carb Ra and intake, possible SI up; absorption disturbances | AID children: TDD −24 % (31.6 → 24.0 U), carbs −31 %, TIR up (72 → 81 %) | Days | Less common than respiratory illness (10 of 51 episodes) | Tinti 2025 |
| Menstrual cycle (luteal) | Periodic SI multiplier on a 24–35 d cycle, applied only to the ~2/3 of women who respond | Population SI ±2.6 % (early follicular vs mid-luteal, ≈5 % peak-to-trough). TDD +3 to +11 %; mean glucose +6 to +12 mg/dL; TIR −2 to −6 pts | Rises from ovulation to early/mid luteal and resolves at menses. Early follicular has more TBR | Every cycle; 61–65 % of women affected; 85 % follow the population trend in AID data | Hossmann 2026; Struckmeyer 2026; Monroy 2025; López 2026; Herranz 2016; Brown 2015 |
| Puberty | Slow SI multiplier (months–years) | Insulin-stimulated glucose metabolism 25–30 % lower in pubertal vs prepubertal T1D | Tanner 2–4 | All adolescents | Amiel 1986 |
| Pregnancy (note only) | Piecewise SI trend | Requirement peaks wk 9, nadir wk 16, then +4 %/week to wk 37 | Whole pregnancy | — | García-Patterson 2010 |
| Menopause | Small step-down in basal need | Postmenopausal pump users take less TDD and basal (registry); 42 % perceive higher glucose, 20 % lower | Years | — | Melmer 2021; Speksnijder 2025 |
| Acute psychological stress | Mostly null; postprandial SI multiplier slightly < 1 | Fasting: no effect (TSST). Postprandial: glucose decline delayed 45 min | Hours | Daily-life stress is common; effects are individual (BMI-moderated) | Wiesli 2005; Ozaslan 2018 |
| Short sleep (one night, 4 h) | Next-day SI multiplier ≈ 0.8–0.86 | Glucose disposal −14 %, GIR −21 % (T1D clamp, n = 7) | Next day; persistence beyond 1 day unknown | Short nights are common [unverified rate] | Donga 2010 (T1D) |
| Alcohol (evening) | Next-morning EGP decrease / SI increase (GH suppression) | 0.75 g/kg at 21:00 → breakfast peak 8.9 vs 15 mmol/L; 5/6 men needed hypo treatment from 10:00 | Delayed: 10–15 h after drinking | Weekly in many adults [unverified] | Turner 2001 |
| Caffeine | Small EGP increase / uptake damping | 6 mg/kg reduced the exercise glucose fall by 1.8 mmol/L; higher at bedtime, lower next morning | Hours | Daily for most adults | Zaharieva 2016 |
| Heat (ambient / skin temp, sauna, hot bath) | Insulin absorption rate multiplier on k_a | 35 vs 20 °C: absorption +50–60 %. Sauna: +110 %, glucose −3 mmol/L. 30 vs 10 °C: 3–5× absorption | While warm (minutes–hours) | Seasonal, showers, sauna | Koivisto 1980, 1981; Rönnemaa 1988; Sindelka 1994 |
| Altitude / flight | Mostly null below 5000 m | Trekking: insulin −14 % (NS) to 5000 m; above that glucose rises with mountain sickness. Simulated cabin: no glucose effect | Days | Rare | de Mol 2011; Fan 2025 |
| Glucocorticoids (prednisolone) | Dose-locked SI multiplier, afternoon/evening | Afternoon–evening hyperglycaemia after a morning dose; T1D-specific magnitude not found | 4–12 h after the morning dose [unverified] | Episodic courses | Elbelt 2009 (replacement dosing); T1D magnitude [unverified] |
| Dawn phenomenon | Diurnal EGP/SI profile (physiology module) | 52 % prevalence; onset ~03:00; insulin need +58 % (IQR 29–111 %) | Nightly, 03:00 → morning | Every night in affected people | Ostrovski 2020 |
| Season / weekday | Slow modulator; estimate per donor | HbA1c lower in spring/summer (children); weekday/weekend effects unquantified in the literature [unverified] | Months / weekly | — | Nordfeldt 2000 |

---

## 1. Exercise

### 1.1 Mechanisms to model separately

1. **Insulin-independent muscle glucose uptake.** This term scales with intensity, starts within
   minutes and stops soon after exercise. In Breton (2008) it is an additive term −β·Y·G, where
   Y is low-pass-filtered ΔHR (τ_HR = 5 min) and β = 3.39·10⁻⁴ (population mean). Because the term
   is proportional to G, the fall is larger when exercise starts high. T1DEXI shows exactly this
   (§1.3).
2. **Increased insulin action**, acute and prolonged. Breton: insulin action ×(1+αZ) with
   α = 0.974, where Z is a slow state driven by a sigmoid of Y. Deichmann et al. (2023, ETH model):
   the multiplier (1+Z) on insulin action, dZ/dt = b·f(Y)·Y − (1/τ_Z)(1−f(Y))·Z, with
   **τ_Z = 600 min**, chosen so that sensitivity stays raised for up to 48 h. Z decays only when
   activity stops.
3. **EGP response.** Moderate exercise roughly doubles both Ra and Rd in non-diabetic people
   (Kreisman 2003). In T1D, fixed peripheral insulin blunts the normal hepatic adaptation. The ETH
   model also includes **glycogen depletion**: after an intensity-dependent t_depl, glucose
   production falls toward a floor, which accelerates the late fall in long sessions.
4. **Intense / anaerobic catecholamine surge.** Above 80 % VO₂max, Ra rises 7–8× and Rd 4×,
   so glucose rises. In T1D, without the physiological post-exercise insulin rise, the
   hyperglycaemia persists into recovery (Purdon 1993; Sigal 1994; Marliss & Vranic 2002).
   Infusing norepinephrine plus epinephrine during moderate exercise reproduces the response
   (Kreisman 2003).
5. **Faster subcutaneous insulin absorption** from exercising tissue. Leg exercise speeds
   absorption from a leg site (Koivisto & Felig 1978 [unverified]). Exercise raised plasma insulin
   22–28 % at both 10 °C and 30 °C (Rönnemaa 1988). This term interacts with IOB at the start of
   exercise.

### 1.2 Existing simulator models

| Model | Structure | Notes |
|---|---|---|
| Breton 2008, JDST | Bergman minimal model + Y (ΔHR, τ 5 min) + Z (slow). Uptake −βYG; insulin action ×(1+αZ) | Fit to 21 T1D under clamp, 15 min at 50 % VO₂max. τ_Z and n not reported in the paper |
| Dalla Man, Breton, Cobelli 2009, JDST | Breton's terms inside the UVA/Padova meal model | Added intensity and duration dependence; in-silico 15/30 min mild–moderate exercise |
| Resalat et al. 2019, PLoS ONE (OHSU) | Multipliers on 3 sensitivities (Hernández-Ordóñez & Campos-Delgado 2008): M_PGU = 1+Γ·PAMM/35, M_PIU = 1+2.4·PAMM, M_HGP = 1+Γ·PAMM/155; dΓ/dt = (Γ̄−Γ)/30; Γ̄ = 0.006·PVO₂max²+1.2264·PVO₂max−10.1958 | PAMM = 50 % (treadmill). **No post-exercise effect**: sensitivities reset when exercise ends. Virtual population samples SI. Inputs: METs from HR + accelerometry |
| Deichmann et al. 2023, PLoS Comput Biol (ETH) | Minimal model + accelerometer-count input (5 min delay); separate insulin-independent uptake (rGU) and production (rGP) states; high-intensity switch above 5800 counts/min; glycogen depletion; prolonged Z (τ 600 min) | The most complete open model. T1D parameters from clamp data at 65 % VO₂max; validated on 6 studies; personalised to children (DiaActive) |
| Deichmann et al. 2021, Front Endocrinol | Uses the above to compare treatment adjustments (basal/bolus reduction, carbs) | Good source of scenario definitions |
| Hobbs et al. 2019, JDST (Cinar group) | Adds HR as an input to a glucose-dynamics prediction model for active adolescents | Prediction rather than full physiology. The related Illinois Tech mGIPsim couples exercise to the Hovorka model with HR/EE/accelerometer [unverified details] |

**Proposed form (derived).** Use the ETH structure: a fast uptake state, an EGP state with a
high-intensity sign flip and glycogen depletion, and a slow Z multiplier on SI with τ_Z ≈ 600 min.
Add an absorption multiplier on k_a during activity. Inputs are intensity (%VO₂max or METs) and
duration. Sample per person: β (uptake gain), α or b (sensitivity gain), τ_Z, and the
catecholamine gain. The between-person SD in T1DEXI is large (−18 ± 39 mg/dL), so these should
be wide distributions, not point values.

### 1.3 Acute magnitudes

- **Lab meta-analysis (García-García 2015, 10 studies).** Rate of glucose change during
  exercise vs rest: continuous moderate −4.43 mmol/L/h (95 % CI −6.06 to −2.79); intermittent
  high-intensity −5.25 mmol/L/h; resistance −2.61 mmol/L/h (NS). Recovery rates were slightly
  positive and NS.
- **T1DEXI structured sessions (Riddell 2023, n = 497, ~30 min video sessions).** Mean change
  during exercise: aerobic −18 ± 39, interval −14 ± 32, resistance −9 ± 36 mg/dL, similar across
  closed-loop, pump and MDI users. TIR over the next 24 h was 76 % vs 70 % on non-exercise days;
  TBR may rise slightly.
- **T1DEXI real-world sessions (Dhaliwal 2025, 404 CSII adults, 8,171 sessions, 45 activity
  types).** Median ΔCGM [IQR] and hypo rate by subgroup:
  - by duration: 15–30 min −12 [−31, 5] mg/dL, hypo 2.8 %; 30–60 min −20 [−49, 6], 5.8 %;
    60–120 min −24 [−60, 11], 12.2 %;
  - by start glucose: 50–100 mg/dL +4; 100–150 −12; 150–200 −31.5; 200–250 −49;
    250–300 −61.5 mg/dL;
  - by IOB: <1 U +5; 1–2 U −7; 2–3 U −20; ≥3 U −30 mg/dL. Hypo rate 3.0 % → 7.5 % across the
    same IOB bands.

  Overall, 6.2 % of sessions had a hypo event. **The start-glucose and IOB gradients are key
  calibration targets**: a G-proportional uptake term combined with an insulin-dependent term
  should reproduce both.
- **Pemberton 2025 (T1DEXI + T1DEXIP, matched pairs).** Bouts of 10–30 min started above
  10 mmol/L lowered glucose by −2.2 mmol/L by 20 min after the bout, vs −0.3 mmol/L in matched
  non-activity periods. Hypo rate 1.4 %. No difference by age, type, intensity or AID use.
- **AID-specific lab data (Tagougui 2020).** 60 min at 60 % VO₂max, 90 min after a meal with
  full meal-bolus IOB. Time <3.9 mmol/L during exercise and the 1 h after: unannounced 13 %,
  announced (raised target) 7 %, announced with a 33 % meal-bolus cut 2 %. This bolus-IOB
  scenario is the hardest for AID.

### 1.4 Delayed and nocturnal effect

- **Midday exercise (Davey 2013, 10 adolescents, clamp).** 45 min of moderate exercise. GIR
  rose from 9.8 to 30.6 g/h during exercise (3×), fell within 1 h, and **stayed raised until
  11 h after exercise**. Not biphasic.
- **Late-afternoon exercise (McMahon 2007).** Glucose requirement rose in a **biphasic** pattern:
  early recovery, then 7–11 h after exercise, about +10 g IV glucose per 70 kg in the late phase
  (figure from a secondary source [unverified]).
- **DirecNet (Tsalikian 2005, 50 youths, 60 min afternoon treadmill).** Overnight mean glucose
  131 vs 154 mg/dL. Hypo on the exercise night only: 26 % of participants; sedentary night only:
  6 %; both: 22 %. That gives 48 % vs 28 % of nights (≤60 mg/dL threshold per secondary sources).
- **Children (T1DEXIP).** More nocturnal hypo after ≥60 min/day of activity: 17 % vs 8 % of
  nights (secondary summary [unverified]).
- **Proposed form (derived).** Z with τ ≈ 600 min (ETH) fits an effect that lasts about 11 h at
  roughly 1/e decay. Persistence to 24–48 h is what the ETH model allows, but in T1D it is
  supported mainly by healthy-volunteer data [unverified for T1D]. Add per-person variation in τ_Z.
  An optional second bump at 7–11 h reproduces McMahon's biphasic pattern.

### 1.5 Frequency, duration, type and mitigation

- **Frequency and duration (T1DEXI CSII adults).** Real-world sessions averaged 20.2 ± 12.6 per
  24.9 ± 5.0 days, i.e. activity on **60 % of days**, ≈5.7 sessions/week [derived]. Duration
  41 ± 23 min. Sessions with a hypo had median 50 min, vs 32 min without. Most common types:
  walking/dog walking (42 %), cycling (9 %), running (8 %), strength (8 %). T1DEXI recruited
  active people (75 % female, median age 33), so the general population is less active:
  >2/3 of people with T1D are insufficiently active per narrative review (Basset-Sagarminaga
  2026). The DPV registry stratifies 18,028 adults into inactive / 1–2× per week / >2× per week
  (Bohn 2015), but the abstract gives no shares [unverified].
- **Barrier.** Fear of hypoglycaemia is the strongest barrier to activity (Brazeau 2008).
- **Mitigation in AID users (RAPPID, Joubert 2025, 86 adults, 954 sessions).** 73 % of
  sessions were aerobic and 61 % moderate intensity. Temp targets were used in 73 % of sessions,
  but started ≥1 h before activity in only 27 %. Carbohydrates before or during exercise were
  common but often poorly timed or dosed. Clinical hypo occurred in 20 % of sessions; 38 % of
  participants had at least one event <54 mg/dL. Anaerobic and high-intensity sessions carried
  lower hypo risk.
- **Guideline strategies** (Riddell 2017 consensus; Moser 2020 EASD/ISPAD CGM position):
  - pre-exercise bolus reductions of ~25–75 % and basal reduction ~90 min before
    [unverified exact figures];
  - ~0.5 g/kg/h carbohydrate for prolonged exercise on MDI (secondary source);
  - for AID, a raised target 60–120 min before exercise (Basset-Sagarminaga 2026).
- **Caffeine** as mitigation: see §4.4.
- **Simulator implication.** The behaviour model needs three per-person mitigation traits:
  probability of announcing exercise, lead time of the temp target, and rescue/pre-exercise carb
  dose. The no-announcement case (Tagougui U-FB) is a key stress test.

---

## 2. Illness and infection

- **Mechanism and magnitude.** Inflammation causes insulin resistance. Human endotoxemia
  (3 ng/kg LPS, healthy adults) lowered FSIGT S_I by **35 %** (Mehta 2010). No clamp-quantified
  S_I change during natural febrile illness in T1D was found. The ISPAD 2022 sick-day guideline
  (Pediatr Diabetes 2022, 10.1111/pedi.13415) notes that infections, including
  COVID-19 and even COVID-19 vaccination, can raise insulin needs for days to weeks. Its extra
  correction-dose rules (commonly 10–20 % of TDD, depending on ketones) are [unverified].
- **CGM and AID data.**
  - **Tinti 2025** (MiniMed 780G, 113 children, 51 episodes in 35 children, mean 3.2 days):
    - fever/respiratory: mean glucose 150.5 → 158.9 mg/dL; TIR 71.1 → 67.0 %; TBR down;
      auto-correction share 36 → 42 %; TDD unchanged because carb intake fell 160 → 141 g/day.
      Insulin per gram of carbohydrate therefore rose ~13 % [derived];
    - gastrointestinal: TDD 31.6 → 24.0 U (−24 %); carbs 205 → 142 g; TIR 72 → 81 %.
  - **Longo 2022** (32 home-isolated adults with COVID-19, CGM): TIR 60.1 → 55.4 %; TAR>250
    10.1 → 16.7 %; mean glucose 160 → 176 mg/dL during the 2 infection weeks. No change in
    controls.
  - **Kim 2025** (18 children, mild COVID-19): GMI 7.1 → 7.7 %, back to baseline within
    2 weeks; the rise was smaller with CSII than MDI.
  - **Vaccination** (Gouda 2022): no change in TIR or TDD in the week after COVID-19 vaccination
    in children.
- **Frequency.**
  - Symptomatic lab-confirmed influenza per season, unvaccinated: adults 4.4 % (95 % CI
    3.0–6.3), children 12.7 %, ≥65 y 7.2 % (Somes 2018).
  - Common colds: adults ~2–4/yr, children ~6–8/yr (Heikkinen & Järvinen 2003 [unverified
    numbers]).
- **Ketosis.** Insulin deficiency plus counter-regulatory hormones drives ketosis. The simulator
  should flag it (a ketone state is optional) but need not model DKA dynamics. Note that
  hypo-/normoglycaemic ketosis exists (ISPAD).
- **Proposed form (derived).** Draw an episode process: ~2–3 respiratory/febrile episodes per
  adult-year, 0.3–0.5 GI episodes [unverified rate]. Each febrile episode applies an SI
  multiplier ramping to 0.65–0.9 within ~1 day, held for 3–7 days (COVID-19 up to 14), then
  recovering over ~1 week. Add appetite suppression (carbs −10 to −30 %). GI episodes: carbs
  −30 %, possible malabsorption (lower carb bioavailability) and hypo risk. Make the multiplier
  per-episode random; the evidence for any central value is weak.

---

## 3. Menstrual cycle, puberty, pregnancy, menopause

### 3.1 Menstrual cycle

- **Systematic review** (Gamarra & Trimboli 2023, 14 studies, n = 4–124): no conclusive
  evidence overall, but a subset of women show luteal hyperglycaemia and lower SI. Definitions,
  metrics and SI methods vary widely, and risk of bias is high.
- **Prevalence.** 65.4 % of 26 CSII women had a "cycle phenomenon", defined as early-follicular
  to late-luteal mean BG up >0.8 mmol/L in more than 2/3 of cycles (Herranz 2016). 61 %
  self-report glycaemic change (Lunt & Brown 1996). In AID data, 84.7 % followed the
  population-level trend (Hossmann 2026).
- **Timing.**
  - Brown 2015 (12 women, 36 ovulation-confirmed cycles; Kalman-filter SI): hyperglycaemia risk
    rose through the periovulatory phase to a peak in the **early luteal** phase, then fell;
    nocturnal SI was lower in the luteal than the early follicular phase.
  - Tatulashvili 2022: TIR fell progressively, lowest in the late luteal phase.
  - TBR is higher in the early/mid-follicular phase (Tatulashvili 2022; López 2026; Mesa 2024).
- **Magnitudes in AID users (recent cohorts).**

  | Study | n / cycles | Luteal vs follicular |
  |---|---|---|
  | Hossmann 2026, Diabetes Care (donated real-world AID data) | 77 / 380 | Latent SI (Bayesian state-space): +2.6 % early follicular vs −2.6 % mid-luteal; TDD and carbs peak in luteal |
  | Struckmeyer 2026 (adolescents, AID) | 51 / 459 | TDD 0.95 → 1.05 U/kg/d (+10.5 %); TIR −6.3 pts; mean glucose +12.5 mg/dL; CV 35 → 39 % |
  | Monroy 2025 (780G) | 12 / 36 | TDD 33.6 → 37.2 U (+10.7 %); mean glucose 131.5 → 139.5 mg/dL; TIR NS |
  | López 2026 (780G) | 17 / 48 | TDD 32.0 → 33.1 U (+3.4 %, mostly prandial); mean glucose 135 → 141; TIR 82.7 → 80.7 % |
  | Rama Chandran 2026 (780G) | 15 / 118 | Pre-menses week: TDD +0.029 U/kg; carbs +0.16 g/kg; TIR −3.5 pts |
  | Levy 2022 (Control-IQ, iDCL) | 16 / ≥3 each | No change in insulin or CGM metrics |
  | Trout 2007 (clamp) | 6 | SI +24 % follicular vs luteal (NS) |

- **Carbohydrate confound.** Several cohorts show luteal carb intake rising together with TDD
  (Hossmann; Rama Chandran). Part of the TDD rise is behavioural, not SI.
- **Proposed form (derived).** For "responders" (Bernoulli p ≈ 0.6–0.85), apply
  SI(t) = SI₀·[1 − a·φ(cycle day)], where φ is a smooth bump that rises after ovulation
  (day ~14 of 28), plateaus through the mid/late luteal phase and returns to 0 within 1–2 days
  of menses. Use a ≈ 0.03–0.15 per person; the population mean is ~0.05 from Hossmann, and TDD
  +10 % is the AID footprint. Cycle length ~ N(28, 3) days, ovulation ~14 days before menses.
  Add an optional luteal carb-intake multiplier (+5–10 % [unverified magnitude]). Oral
  contraceptive users are unresolved; default to non-responder [derived].

### 3.2 Puberty / growth hormone

Euglycaemic clamp: insulin-stimulated glucose metabolism was **25–30 % lower** in pubertal than
prepubertal T1D children, and 33–42 % lower in diabetic than non-diabetic children at each stage.
It correlated inversely with 24-h GH (Amiel 1986). Model as a slow SI multiplier ~0.7–0.75 for
adolescents. Nocturnal GH pulses also add to the dawn rise [unverified magnitude].

### 3.3 Pregnancy (note only)

Insulin requirement peaks at week 9, falls to a nadir at week 16 (with severe hypos concentrated
before week 16), then rises ~4 %/week (U/kg) to week 37 (García-Patterson 2010, n = 65). Out of
scope for routine scenarios.

### 3.4 Menopause

Registry data (DPV, 630 pre- vs 548 postmenopausal CSII women): postmenopausal women had lower
TDD, U/kg and basal; bolus was similar (Melmer 2021; cross-sectional, so confounded by age and
eGFR). In a survey, 67 % perceived changes after menopause: 42 % higher glucose, 20 % lower, 55 %
more variability (Speksnijder 2025). Model as a per-person static shift. The cycle term switches
off.

---

## 4. Other factors

### 4.1 Acute psychological stress

Trier Social Stress Test, 20 + 20 T1D (Wiesli 2005):
- fasting: **no** glucose change;
- postprandial: glucose decline delayed by **45 min**.

In a 37-patient CGM week with daily stress ratings (Ozaslan 2018), stress-related glycaemic
changes, both behavioural and behaviour-independent, depended on BMI. Proposed form [derived]: a
small, person-specific postprandial SI multiplier (0.8–1.0) or EGP increase over the stress
window, with sign and gain sampled per person. Low priority: effects are inconsistent and small
next to meals and exercise.

### 4.2 Sleep deprivation

One night of 4 h sleep vs normal sleep in 7 T1D (Donga 2010, clamp):
- next-day glucose disposal −14 %;
- GIR about **−21 %**;
- EGP unchanged (in healthy volunteers, hepatic resistance also appeared).

Proposed form: next-day SI multiplier ≈ 0.8–0.86 after a short night [derived], decaying within
~1 day [unverified]. The night itself is also a CGM-artefact window (compression lows), which is
a separate sensor-model concern.

### 4.3 Alcohol

Turner 2001 (6 men, 0.75 g/kg wine at 21:00):
- no overnight difference;
- next-morning fasting and post-breakfast glucose much lower (peak 8.9 vs 15.0 mmol/L);
- 5/6 needed hypo treatment from 10:00 (nadir 1.9–2.9 mmol/L);
- nocturnal GH secretion suppressed.

Proposed form [derived]: an alcohol event lowers EGP (gluconeogenesis inhibition) acutely, plus a
delayed SI increase or EGP decrease in a window **~10–15 h** after drinking, with gain scaled by
grams per kg. The acute carb content of drinks goes to the meal module. Frequency is a
per-person trait (weekly drinkers vs none) [unverified rates].

### 4.4 Caffeine

6 mg/kg caffeine before 45 min at 60 % VO₂max with basal insulin only (Zaharieva 2016, n = 13):
- glucose drop during exercise attenuated by 1.8 ± 2.8 mmol/L (P = 0.056);
- higher glucose at bedtime;
- lower glucose early the next morning.

In healthy people caffeine lowers SI ~15 % (Keijzers 2002 [unverified]). Low priority; an
optional small EGP/SI term.

### 4.5 Heat and insulin absorption

| Study | Condition | Effect |
|---|---|---|
| Koivisto 1981 (6 T1D) | 35 vs 20 °C ambient | Absorption +50–60 % over 4 h; glucose 1–2 mmol/L lower |
| Koivisto 1980 (8 T1D) | Sauna, 2 × 25 min at 85 °C | Absorption +110 %; glucose 3.0–3.3 mmol/L lower |
| Rönnemaa 1988 (9 T1D) | 30 vs 10 °C ambient | Absorption 3–5× higher; exercise added +22–28 % plasma insulin |
| Sindelka 1994 (50 healthy) | Skin temperature | Early serum insulin correlated with skin temperature; inversely with fat thickness |

These are regular/human insulin data; analog sensitivity is likely smaller [unverified].
Proposed form [derived]: k_a(t) = k_a0·exp(c·ΔT_skin) with c chosen to give ~1.5× at +15 °C
ambient (≈ +3–5 °C skin [unverified]), plus explicit sauna/hot-bath events at ~2×. This also
gives a seasonal summer effect.

### 4.6 Altitude and flight

- 8 T1D, Kilimanjaro trek (de Mol 2011): insulin dose −14 % (NS) and stable glucose up to
  5000 m; above that, glucose and insulin need rose with acute mountain sickness (r = 0.78–0.86).
- Hypobaric chamber at cabin pressure, dual isotope (Fan 2025): postprandial Rd ↑, but no change
  in the glucose profile; no evidence that pump use is a risk in flight.

Proposed form: ignore by default; optional "trek" scenario combining exercise days with a
mountain-sickness SI decrease above 5000 m.

### 4.7 Glucocorticoids

- No T1D cohort quantifying prednisolone's effect on insulin need was found in this review.
- Clinical pattern (mixed populations): a morning dose causes hyperglycaemia mainly in the
  afternoon and evening, with little effect next morning [unverified primary].
- T1D on hydrocortisone replacement (Elbelt 2009, n = 10) needed much more insulin per carb at
  noon and evening (2.0 vs 1.1 and 2.1 vs 1.3 U/10 g).

Proposed form [derived]: a dose-locked SI multiplier, about 0.5–0.7 at high prednisolone doses
[unverified magnitude], onset 4 h, peak 6–10 h, gone by ~24 h. Episodic courses (e.g. 5 days).
Use as a stress scenario, not a background process.

### 4.8 Dawn phenomenon

- Prevalence 52 % among 33 pump users (definition: insulin need up >20 % for ≥90 min).
- Onset ~**03:00** (IQR 03:00–04:15).
- Magnitude +58 % (IQR 29–111 %) increase in insulin requirement in the derivation set; +66 %
  in the confirmation set (Ostrovski 2020).

This belongs in the physiology module as a per-person diurnal EGP or SI profile. It is listed
here so it is not double-counted.

### 4.9 Weekly and seasonal patterns

- **Season.** Children had lower HbA1c in spring/summer and higher in autumn/winter
  (Nordfeldt 2000, n = 114). Mechanisms are plausibly activity, temperature (absorption, §4.5)
  and illness season (§2).
- **Weekday/weekend.** No peer-reviewed T1D quantification was checked [unverified].
- **Recommendation [derived].** Do not import literature magnitudes. Instead, drive the season
  and weekday structure from the components above (activity rate, illness hazard, temperature,
  alcohol/sleep on weekends) and check it against donor data. The donor pool can measure
  weekday/weekend and seasonal TDD/TIR directly.

---

## 5. Cross-cutting modelling notes [derived]

- **Common interface.** Each factor writes into one or more of:
  - SI multiplier m_SI(t);
  - EGP additive/multiplier;
  - insulin-independent uptake U_ii(t) (mg/kg/min);
  - absorption multiplier m_ka(t);
  - behaviour modifiers (carb intake, rescue carbs, temp-target use).

  Multipliers compose multiplicatively; additive terms sum.
- **Between-person spread** dominates every factor here: exercise SD ≈ 2× the mean drop; cycle
  responders vs non-responders; stress sign varies. Sample per-person gains from wide
  distributions and keep them fixed per virtual person (trait), with episode-level noise on top.
- **Calibration targets that the field (Loop/Trio donor data) can supply:**
  - TDD and TIR change on exercise vs non-exercise days, and their dependence on start BG and IOB
    (compare with Dhaliwal 2025 tables);
  - luteal TDD shift (+3 to +11 %);
  - illness-period auto-correction share;
  - dawn basal profile.
- **Safety relevance for AID evaluation:**
  - The two dangerous factors are exercise with IOB on board and its delayed nocturnal SI rise,
    and alcohol's next-morning effect. Both push toward t<54 hours after the trigger, when the
    controller has no signal.
  - Illness and luteal SI decreases mainly cost TIR.
  - Absorption speed-up (heat) is a short-latency hypo risk after boluses.

---

## References

1. Breton MD. Physical activity—the major unaccounted impediment to closed loop control. *J Diabetes Sci Technol* 2008;2:169–174. doi:10.1177/193229680800200127
2. Dalla Man C, Breton MD, Cobelli C. Physical activity into the meal glucose–insulin model of type 1 diabetes: in silico studies. *J Diabetes Sci Technol* 2009;3:56–67. doi:10.1177/193229680900300107
3. Resalat N, El Youssef J, Tyler N, Castle J, Jacobs PG. A statistical virtual patient population for the glucoregulatory system in type 1 diabetes with integrated exercise model. *PLoS ONE* 2019;14:e0217301. doi:10.1371/journal.pone.0217301
4. Deichmann J, Bachmann S, Burckhardt MA, Pfister M, Szinnai G, Kaltenbach HM. New model of glucose-insulin regulation characterizes effects of physical activity and facilitates personalized treatment evaluation in children and adults with type 1 diabetes. *PLoS Comput Biol* 2023;19:e1010289. doi:10.1371/journal.pcbi.1010289
5. Deichmann J, Bachmann S, Burckhardt MA, Szinnai G, Kaltenbach HM. Simulation-based evaluation of treatment adjustment to exercise in type 1 diabetes. *Front Endocrinol* 2021;12:723812. doi:10.3389/fendo.2021.723812
6. Hobbs N, Hajizadeh I, Rashid M, Turksoy K, Breton M, Cinar A. Improving glucose prediction accuracy in physically active adolescents with type 1 diabetes. *J Diabetes Sci Technol* 2019;13:718–727. doi:10.1177/1932296818820550
7. Riddell MC, Li Z, Gal RL, et al. Examining the acute glycemic effects of different types of structured exercise sessions in type 1 diabetes in a real-world setting: the T1DEXI. *Diabetes Care* 2023;46:704–713. doi:10.2337/dc22-1721
8. Dhaliwal M, Tang K, Aiello EM, et al. Variation in hypoglycemia risk during real-world physical activity in adults with type 1 diabetes: insights from T1DEXI. *Diabetes Technol Ther* 2025/2026. doi:10.1177/15209156251400209
9. Pemberton JS, Russon CL, Pulsford RM, et al. Glucose-lowering effects of physical activity in type 1 diabetes: a causal modelling and matched-pair analysis approach. *Diabet Med* 2025;42:e70146. doi:10.1111/dme.70146
10. García-García F, Kumareswaran K, Hovorka R, Hernando ME. Quantifying the acute changes in glucose with exercise in type 1 diabetes: a systematic review and meta-analysis. *Sports Med* 2015;45:587–599. doi:10.1007/s40279-015-0302-2
11. Riddell MC, Gallen IW, Smart CE, et al. Exercise management in type 1 diabetes: a consensus statement. *Lancet Diabetes Endocrinol* 2017;5:377–390. doi:10.1016/S2213-8587(17)30014-1
12. Moser O, Riddell MC, Eckstein ML, et al. Glucose management for exercise using CGM and isCGM in type 1 diabetes: EASD/ISPAD position statement. *Diabetologia* 2020;63:2501–2520. doi:10.1007/s00125-020-05263-9
13. McMahon SK, Ferreira LD, Ratnam N, et al. Glucose requirements to maintain euglycemia after moderate-intensity afternoon exercise in adolescents with type 1 diabetes are increased in a biphasic manner. *J Clin Endocrinol Metab* 2007;92:963–968. doi:10.1210/jc.2006-2263
14. Davey RJ, Howe W, Paramalingam N, et al. The effect of midday moderate-intensity exercise on postexercise hypoglycemia risk in individuals with type 1 diabetes. *J Clin Endocrinol Metab* 2013;98:2908–2914. doi:10.1210/jc.2013-1169
15. Tsalikian E, Mauras N, Beck RW, et al. (DirecNet). Impact of exercise on overnight glycemic control in children with type 1 diabetes mellitus. *J Pediatr* 2005;147:528–534. doi:10.1016/j.jpeds.2005.04.065
16. Tagougui S, Taleb N, Legault L, et al. A single-blind, randomised, crossover study to reduce hypoglycaemia risk during postprandial exercise with closed-loop insulin delivery. *Diabetologia* 2020;63:2282–2291. doi:10.1007/s00125-020-05244-y
17. Joubert M, Meyer L, Bekka S, et al. Hypoglycemia incidence and behavioural adjustments during free-living unstructured physical activity in adults with type 1 diabetes using AID systems: RAPPID. *Diabetes Obes Metab* 2025. doi:10.1111/dom.70122
18. Basset-Sagarminaga J, De Block C, Nørgaard K, et al. Safety and glycaemic control during exercise with the MiniMed 780G: a narrative review. *Diabetes Obes Metab* 2026. doi:10.1111/dom.70211
19. Bohn B, Herbst A, Pfeifer M, et al. Impact of physical activity on glycemic control and prevalence of cardiovascular risk factors in adults with type 1 diabetes: 18,028 patients. *Diabetes Care* 2015;38:1536–1543. doi:10.2337/dc15-0030
20. Brazeau AS, Rabasa-Lhoret R, Strychar I, Mircescu H. Barriers to physical activity among patients with type 1 diabetes. *Diabetes Care* 2008;31:2108–2109. doi:10.2337/dc08-0720
21. Marliss EB, Vranic M. Intense exercise has unique effects on both insulin release and its roles in glucoregulation: implications for diabetes. *Diabetes* 2002;51(Suppl 1):S271–S283. doi:10.2337/diabetes.51.2007.s271
22. Purdon C, Brousson M, Nyveen SL, et al. The roles of insulin and catecholamines in the glucoregulatory response during intense exercise and early recovery in insulin-dependent diabetic and control subjects. *J Clin Endocrinol Metab* 1993;76:566–573. doi:10.1210/jcem.76.3.8445012
23. Sigal RJ, Purdon C, Fisher SJ, et al. Hyperinsulinemia prevents prolonged hyperglycemia after intense exercise in insulin-dependent diabetic subjects. *J Clin Endocrinol Metab* 1994;79:1049–1057. doi:10.1210/jcem.79.4.7962273
24. Kreisman SH, Halter JB, Vranic M, Marliss EB. Combined infusion of epinephrine and norepinephrine during moderate exercise reproduces the glucoregulatory response of intense exercise. *Diabetes* 2003;52:1347–1354. doi:10.2337/diabetes.52.6.1347
25. Koivisto VA, Felig P. Effects of leg exercise on insulin absorption in diabetic patients. *N Engl J Med* 1978;298:79–83. doi:10.1056/NEJM197801122980205 [unverified]
26. Zaharieva DP, Miadovnik LA, Rowan CP, et al. Effects of acute caffeine supplementation on reducing exercise-associated hypoglycaemia in individuals with type 1 diabetes. *Diabet Med* 2016;33:488–496. doi:10.1111/dme.12857
27. Mehta NN, McGillicuddy FC, Anderson PD, et al. Experimental endotoxemia induces adipose inflammation and insulin resistance in humans. *Diabetes* 2010;59:172–181. doi:10.2337/db09-0367
28. Tinti D, Nobili C, Bettin G, et al. Sick days glycaemic outcomes in a cohort of children and adolescents with type 1 diabetes using an AID system—a preliminary report. *Diabetes Obes Metab* 2025;27:3997–4000. doi:10.1111/dom.16377
29. Longo M, Scappaticcio L, Petrizzo M, et al. Glucose control in home-isolated adults with type 1 diabetes affected by COVID-19 using continuous glucose monitoring. *J Endocrinol Invest* 2022;45:445–452. doi:10.1007/s40618-021-01669-3
30. Kim HY, Shin SH, Lee H, Kim J. Changes in metrics of continuous glucose monitoring during COVID-19 in Korean children and adolescents with type 1 diabetes. *Ann Pediatr Endocrinol Metab* 2025. doi:10.6065/apem.2448036.018
31. Gouda N, Dimitriadou M, Sotiriou G, Christoforidis A. The impact of COVID-19 vaccination on glycaemic control in children and adolescents with T1DM on CGM. *Acta Diabetol* 2022. doi:10.1007/s00592-022-01968-y
32. Phelan H, et al. [author list unverified] ISPAD Clinical Practice Consensus Guidelines 2022: Sick day management in children and adolescents with diabetes. *Pediatr Diabetes* 2022;23:912–925. doi:10.1111/pedi.13415
33. Somes MP, Turner RM, Dwyer LJ, Newall AT. Estimating the annual attack rate of seasonal influenza among unvaccinated individuals: a systematic review and meta-analysis. *Vaccine* 2018;36:3199–3207. doi:10.1016/j.vaccine.2018.04.063
34. Heikkinen T, Järvinen A. The common cold. *Lancet* 2003;361:51–59. doi:10.1016/S0140-6736(03)12162-9
35. Gamarra E, Trimboli P. Menstrual cycle, glucose control and insulin sensitivity in type 1 diabetes: a systematic review. *J Pers Med* 2023;13:374. doi:10.3390/jpm13020374
36. Brown SA, Jiang B, McElwee-Malloy M, Wakeman C, Breton MD. Fluctuations of hyperglycemia and insulin sensitivity are linked to menstrual cycle phases in women with T1D. *J Diabetes Sci Technol* 2015;9:1192–1199. doi:10.1177/1932296815608400
37. Herranz L, Saez-de-Ibarra L, Hillman N, Gaspar R, Pallardo L. Glycemic changes during menstrual cycles in women with type 1 diabetes. *Med Clin (Barc)* 2016;146:287–291. doi:10.1016/j.medcli.2015.11.044
38. Lunt H, Brown LJ. Self-reported changes in capillary glucose and insulin requirements during the menstrual cycle. *Diabet Med* 1996;13:525–530. doi:10.1002/(SICI)1096-9136(199606)13:6<525::AID-DIA123>3.0.CO;2-D
39. Trout KK, Rickels MR, Schutta MH, et al. Menstrual cycle effects on insulin sensitivity in women with type 1 diabetes: a pilot study. *Diabetes Technol Ther* 2007;9:176–182. doi:10.1089/dia.2006.0004
40. Tatulashvili S, Julla JB, Sritharan N, et al. Ambulatory glucose profile according to different phases of the menstrual cycle in women living with type 1 diabetes. *J Clin Endocrinol Metab* 2022;107:2793–2800. doi:10.1210/clinem/dgac443
41. Levy CJ, O'Malley G, Raghinaru D, et al. Insulin delivery and glucose variability throughout the menstrual cycle on closed loop control for women with type 1 diabetes. *Diabetes Technol Ther* 2022;24:357–361. doi:10.1089/dia.2021.0431
42. Diaz CJL, Fabris C, Breton MD, Cengiz E. Insulin replacement across the menstrual cycle in women with type 1 diabetes: an in silico assessment of the need for ad hoc technology. *Diabetes Technol Ther* 2022;24:832–841. doi:10.1089/dia.2022.0154
43. Hossmann S, Friedman M, Lizoain A, et al. Effects of menstrual cycle on insulin sensitivity in type 1 diabetes: an observational study of individuals using an AID system. *Diabetes Care* 2026. doi:10.2337/dc26-0692
44. Struckmeyer N, Landsberg S, Biester T, et al. Menstrual cycle-related variations in insulin requirements and glycemic control during AID in adolescents with type 1 diabetes. *J Pediatr Endocrinol Metab* 2026. doi:10.1515/jpem-2026-0309
45. Monroy G, Picón-César MJ, García-Alemán J, Tinahones FJ, Martínez-Montoro JI. Glycemic control across the menstrual cycle in women with T1D using the MiniMed 780G: the 780MENS prospective study. *Diabetes Technol Ther* 2025. doi:10.1089/dia.2024.0522
46. López TR, Acosta DL, Alcalá BB, et al. Glycemic control during the menstrual cycle in women with type 1 diabetes: performance of an AID system. *Diabetes Obes Metab* 2026. doi:10.1111/dom.70673
47. Rama Chandran S, Ang WM, Lim GH, Sng GGR, Gardner D. Impact of menstrual cycle phases on carbohydrate intake, insulin delivery and glycaemia in women with T1D using MiniMed 780G. *Diabetes Obes Metab* 2026. doi:10.1111/dom.71234
48. Mesa A, Solà C, Vinagre I, et al. Impact of an advanced hybrid closed-loop system on glycemic control throughout the menstrual cycle in women with T1D prone to hypoglycemia. *Diabetes Technol Ther* 2024. doi:10.1089/dia.2023.0571
49. Amiel SA, Sherwin RS, Simonson DC, Lauritano AA, Tamborlane WV. Impaired insulin action in puberty: a contributing factor to poor glycemic control in adolescents with diabetes. *N Engl J Med* 1986;315:215–219. doi:10.1056/NEJM198607243150402
50. García-Patterson A, Gich I, Amini SB, Catalano PM, de Leiva A, Corcoy R. Insulin requirements throughout pregnancy in women with type 1 diabetes mellitus: three changes of direction. *Diabetologia* 2010;53:446–451. doi:10.1007/s00125-009-1633-z
51. Melmer A, Zürrer I, Kopp F, et al. Differences in insulin dosing in women with type 1 diabetes before and after the menopause. *Swiss Med Wkly* 2021;151:w30025. doi:10.4414/smw.2021.w30025
52. Speksnijder EM, Simsek S, Bisschop PH, et al. Perceived blood glucose regulation after menopause: a cross-sectional survey in women with type 1 diabetes in the Netherlands. *Diabetologia* 2025. doi:10.1007/s00125-025-06518-z
53. Wiesli P, Schmid C, Kerwer O, et al. Acute psychological stress affects glucose concentrations in patients with type 1 diabetes following food intake but not in the fasting state. *Diabetes Care* 2005;28:1910–1915. doi:10.2337/diacare.28.8.1910
54. Ozaslan B, Patek SD, Grabman JH, et al. Body mass index effect on differing responses to psychological stress in blood glucose dynamics in patients with type 1 diabetes. *J Diabetes Sci Technol* 2018;12:1105–1112. doi:10.1177/1932296818758103
55. Donga E, van Dijk M, van Dijk JG, et al. Partial sleep restriction decreases insulin sensitivity in type 1 diabetes. *Diabetes Care* 2010;33:1573–1577. doi:10.2337/dc09-2317
56. Turner BC, Jenkins E, Kerr D, Sherwin RS, Cavan DA. The effect of evening alcohol consumption on next-morning glucose control in type 1 diabetes. *Diabetes Care* 2001;24:1888–1893. doi:10.2337/diacare.24.11.1888
57. Keijzers GB, De Galan BE, Tack CJ, Smits P. Caffeine can decrease insulin sensitivity in humans. *Diabetes Care* 2002;25:364–369. doi:10.2337/diacare.25.2.364 [unverified]
58. Koivisto VA. Sauna-induced acceleration in insulin absorption from subcutaneous injection site. *Br Med J* 1980;280:1411–1413. doi:10.1136/bmj.280.6229.1411
59. Koivisto VA, Fortney S, Hendler R, Felig P. A rise in ambient temperature augments insulin absorption in diabetic patients. *Metabolism* 1981;30:402–405. doi:10.1016/0026-0495(81)90122-0
60. Rönnemaa T, Koivisto VA. Combined effect of exercise and ambient temperature on insulin absorption and postprandial glycemia in type I patients. *Diabetes Care* 1988;11:769–773. doi:10.2337/diacare.11.10.769
61. Sindelka G, Heinemann L, Berger M, Frenck W, Chantelau E. Effect of insulin concentration, subcutaneous fat thickness and skin temperature on subcutaneous insulin absorption in healthy subjects. *Diabetologia* 1994;37:377–380. doi:10.1007/BF00408474
62. de Mol P, de Vries ST, de Koning EJ, et al. Increased insulin requirements during exercise at very high altitude in type 1 diabetes. *Diabetes Care* 2011;34:591–595. doi:10.2337/dc10-2015
63. Fan KS, Shojaee-Moradie F, Jeivad F, et al. A dual stable isotope study of the effect of altitude and simulated flight on glucose metabolism in type 1 diabetes. *Diabetes* 2025. doi:10.2337/db25-0004
64. Elbelt U, Hahner S, Allolio B. Altered insulin requirement in patients with type 1 diabetes and primary adrenal insufficiency receiving standard glucocorticoid replacement therapy. *Eur J Endocrinol* 2009;160:919–924. doi:10.1530/EJE-08-1003
65. Ostrovski I, Lovblom LE, Scarr D, et al. Analysis of prevalence, magnitude and timing of the dawn phenomenon in adults and adolescents with type 1 diabetes. *Can J Diabetes* 2020;44:157–162. doi:10.1016/j.jcjd.2019.08.003
66. Nordfeldt S, Ludvigsson J. Seasonal variation of HbA1c in intensive treatment of children with type 1 diabetes. *J Pediatr Endocrinol Metab* 2000;13:529–535. doi:10.1515/jpem.2000.13.5.529

Page ranges and volume numbers not shown in the abstracts checked are [unverified]. DOIs were
checked via Europe PMC except for refs 25 and 57.
