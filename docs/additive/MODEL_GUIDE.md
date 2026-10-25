# The additive patient simulator — model guide

A virtual person with type 1 diabetes, assembled from named, separately evidenced parts, run in closed loop with
LoopEval's real Loop algorithm. For every part this guide gives its **form**, its current **settings**, how each value
was **set** (literature, a fit, or a donor measurement), the **rationale**, and its **personal basis** — whether the value
is the twin's own (from its donor), drawn per person, redrawn per event, or one constant for everyone.

`COMPONENTS.md` is the compact registry; `evidence/0x` holds the full citations; `LESSONS.md` holds every test behind a
value (`L n` below). Code: `analysis/loopeval_analysis/patient_sim/`. Values are the code defaults at reference
**lg12** (2026-10-23): 112 people × 14 days, weighted match score 0.371 (0.400 on a second draw of people, lg12_5k) over
51 statistics, tier 1 0.237 / 0.278 (§ 10 lists every row, its tier and its gap). It is c446_npu (2026-10-20) with the
saturating acute exercise sensitivity (L 495) and treatment carbs logged at the donors' rate (L 500). The run carries:
- a personal meal mix with relative fat resistance (L 432);
- the relative post-meal window 0.4 (L 436);
- dose-dependent bolus absorption (L 437);
- the night alarm defence (L 443);
- the saturating exercise sensitivity (L 495).

Delivery is scored by record rate, as eda reads the donors' records (L 455). Mean, CV, TIR, TDD and every low statistic
are on the donors' or close (gap < 0.35).

**Personal basis legend**

| Tag | Meaning |
|---|---|
| **Donor** | Taken from the twin's own donor record: measured or fitted on that person's Tidepool data (template column). The twin carries its donor's value. |
| **Drawn** | Drawn per person from a population distribution (literature or cohort-fitted). Personal, but not from the donor. |
| **Event** | Redrawn per meal, dose, sensor session, site, day or episode. |
| **Cohort** | One value for everyone. |

**[J]** marks a judgement still waiting for evidence.

---

## 0. Ground rules

1. **No mystery terms** (L 1). A variability or offset term exists only if its size has its own controlled-condition
   evidence. Free-living statistics are targets the named parts must reproduce together, never inputs to a fit.
2. **Real-world data is the primary test.** Every twin is scored by the same code as the donors (`validate.py`).
3. **The body follows the data, not the user's entered settings** (Pete 2026-10-19). Where a donor has a data-fitted
   value (ISF from their glucose response, basal shape from delivered insulin, insulin type from Loop's recorded IOB,
   meal response per entered gram) the body takes it. The controller keeps the donor's own settings.
4. **Realism, not agreement with Loop** (Pete 2026-10-17): the body is calibrated to physiology and donor data, never to
   Loop's curves or forecasts.
5. **The patient is independent of the controller** (Pete 2026-10-18): RC mode, GBAF and strategy are controller
   configuration, never patient traits. Validation runs give each twin its donor's deployed controller (`--enable rc_own`).
6. **The person is a second controller.** Behaviour is a set of traits, mostly the donor's own.
7. **Truth and belief are separate.** Body, settings and the person's estimates are drawn separately; the gaps between
   them are simulated.
8. **Review before adding** (Pete 2026-10-18): after an adopted change, re-check every component against its own target
   (`review.py`) before adding the next.

---

## 1. Architecture

### 1.1 The minute loop (`world.py`, `World._minute`)

| # | Step | Code |
|---|---|---|
| 1 | Modulators → `si_mult`, `egp_mult` (circadian, day level, cycle, illness, nightly factors, steroids) | `modulators.Modulators.at` |
| 2 | Fat-induced insulin resistance and hyperglycaemic resistance multiply `si_mult` | `World._fat_si`, B11 |
| 3 | Exercise and everyday activity: intensity, uptake, acute + delayed SI, absorption | `exercise.Exercise.at` |
| 4 | Site state: absorption speed by site age, absorbed fraction (failing, dislodged, LH) | `device.Pump.site_state` |
| 5 | Pump delivers this minute's basal and bolus after its errors and faults | `device.Pump.deliver` |
| 6 | Insulin enters the body (basal depot; each bolus its own depot with jitter) | `physiology.Body.infuse` |
| 7 | Body integrates one minute (gut, glucose, insulin, EGP, counter-regulation) | `physiology.Body.step` |
| 8 | Sensor sees blood glucose; on a reporting minute returns a reading or a gap | `sensor.Sensor.step` |
| 9 | Behaviour: the day's plan, then defense and corrections on the latest visible reading | `behavior.Behavior.minute` |
| 10 | Truth is logged | `World.truth` |

Time is local minutes from `EPOCH` (Monday 2026-01-05 00:00).

### 1.2 Coupling to LoopEval (`loopeval_io.py`)

- **Export**: 30 h of internally driven history (an open-loop pump user at the person's settings), then the sensor grid.
  Only the candidate arm of the trace is meaningful.
- **Controller**: deployed Loop-main (`--no-mid-absorption-isf --no-gradual-transitions-gate --legacy-rc-decay`).
  Strategy (temp basal or automatic bolus) per twin from its donor's share of autobolus days (G6b). `rc_own` gives the
  donor's deployed RC mode (integral + clamp for 19 of 112); GBAF donors get their deployed GBAF.
- **Settings**: the donor's ISF / CR / basal schedule and eras, a correction range target ± 5 mg/dL (donors' median range
  width is 10, L 368), limits, suspend threshold (`suspend_own`), dated settings edits (F13), Temporary Overrides (F12).
- **Plant**: protocol v2 (`--external-plant --plant-behavior`): LoopEval sends doses; the plant returns CGM, carb
  entries and bolus requests (a ratio of Loop's recommendation, or absolute units for food dosed by hand).
- **Loop not acting** (G9): offline windows and pump errors at the donors' measured rates are written to
  `disruptions.csv`, which LoopEval honours.

### 1.3 Seeds and streams

`(person, seed)` fixes everything. Independent RNG streams (modulators, behaviour, sensor, pump, absorption, misc, and
per-trait streams such as the strategy draw, gastric-emptying draw and circadian draw) keep every `--disable` arm a
paired comparison on the same people.

---

## 2. The person — truth, settings, devices (`person.py`, `templates.py`)

The template is one of 168 ice pilot donors (DIY Loop, BDDP). `templates.py` builds its columns from the donor's
`ice_v32` export (steps, meals, therapy); `templates_pilot_logs.csv` lives outside the repo.

| Component | Form | Settings | How set | Rationale / evidence | Personal basis |
|---|---|---|---|---|---|
| G1 Template | a donor row, lightly jittered | TDD, ISF, basal ×lnN(0, 0.10) each | — | a twin stands for one ~2-week window of its donor | **Donor** |
| G2 True ISF | body ISF = the donor's data-fitted ISF | ISF_W 1.0 (fully on the data); clip 0.5–2× settings | ICE ISF yardstick (fasting OLS of glucose change on insulin absorbed, shrunk to the basal rule) × the body-model fit (`fit_body --regression`) | body follows data (rule 3); L 261 | **Donor** |
| G3 Body weight | ½ log age prior + ½ log TDD / U-per-kg(age), ×lnN(0, 0.12) | clip 15–160 kg | — | a profile age can belong to the account holder (eda L47) | **Donor** (age, TDD) + Drawn |
| G4 Insulin balance | true basal = share × TDD / 24; carbs eaten = TDD (1 − share) CR_true, covering all intake (meals, snacks, grazing, rescues, protein glucose) | share N(0.5, 0.07) shifted to centre 0.42, clip 0.25–0.7 | judgement centre below the scheduled share (donors' Loop trims night basal) | TDD is the measured constraint; L 124–125, 143 | **Donor** (TDD) + Drawn (share) |
| G5 Settings | the donor's own ISF, CR, basal schedule, target, limits, suspend threshold | — | donor therapy.json (eras) | Loop runs what the donor ran | **Donor** |
| G6 Devices | sensor family, pump, insulin formulation | formulation from the recorded brand, relabelled from Loop's recorded IOB (`add_insulin_from_iob`); unrecorded: rapid 52 : ultra-rapid 20 | IOB-curve RMSE per donor (51 of 52 recorded ultra-rapid matched) | L 248 | **Donor** |
| G6b Dosing strategy | autobolus with probability = donor's share of autobolus days | own stream | donor dose records | 40 of 50 "autobolus" donors spent days in temp mode; Loop's automated total then 1.04× (L 331) | **Donor** |
| G7 Carb sensitivity (CSF) | CSF = 1.05 · [1.85 · ISF_data · TDD / 500]^0.5 · [settings ISF/CR]^0.5, each ×lnN(0, 0.15); f = CSF·BW·VG/1000 | `csf_w` 0.5 (half data, half settings) | constant 1.05 calibrated to the labeler's g-eq per entered gram (1.21 vs donors 1.19) | ice L54; L 197, 300 | Donor + Drawn |
| G7b Per-donor meal response | CSF × the donor's labelled g-eq per entered gram over its twin's, reliability-shrunk, pooled over two rounds; intake grams held | multiplier p10 / 50 / 90 0.60 / 0.96 / 1.44 | ice labeler on donor and twin (`csf_geq_mult`); cohort level × 1.05 (`csf_lvl`) set between the labelled g-eq per gram and the post-meal ICE integral | L 358–359, 401 | **Donor** |
| G8 Effective-ISF calibration | SI_D and the EGP-arm gain solved so the TOTAL drop per unit on the linear body equals the true ISF; Ib from true basal | EGP share of the effect U(0.7, 0.9) | per-person probe; share centred on Romeres 2025 (meal EGP nadir 44 ± 17%) | L 143, 195 | Derived per person |
| G9 Loop not acting | offline windows run scheduled basal; pump errors and short missed cycles keep the last command | offline 0.9 / day, lnN(32 min, 0.86); errors 2.45 / day × 3 min; missed cycles with CGM present, single 4.4 / day and 2–3-slot 0.5 / day (median) | donors' disruptions.csv; decision_times.csv (`add_missed_cycles`) | Loop decides in 92% of donors' 5-min slots (L 60, 377) | **Donor** rates, Event draws |

---

## 3. Physiology (`physiology.py`, `insulins.py`)

| Component | Form | Settings | How set | Rationale / evidence | Personal basis |
|---|---|---|---|---|---|
| A1 Glucose kinetics | one pool; insulin-independent glucose effectiveness SG(G − Gb) | VG lnN(1.88 dL/kg, 0.15); SG lnN(0.0045 /min, 0.5); Gb N(119, 7) | SG inside the UVA/Padova range 0.0013–0.0047 | 0.003 left the level +6 (L 208); 0.5–0.7× raised the level (L 349) | **Drawn** |
| A2 Subcutaneous insulin PK | per-dose depot: delay → Isc1 →kd→ Isc2 →ka2→ plasma, ke 0.127 | kd lnN(0.030, 0.31), ka2 lnN(0.018, 0.21), VI 0.126 L/kg | ka2 centre refit to the lispro clamp profile; half the ReplayBG log-SD | L 9 | **Drawn** |
| A3 Formulations | delay, kd/ka2 multipliers, fast-route share | lispro/aspart reference; Fiasp, Lyumjev fitted to clamp contrasts; glulisine; regular | `insulins.fit_formulations` | evidence/01 §3.2 | **Donor** (via G6) |
| A4 Per-dose absorption jitter | ω scales kd, ka2, fast route per bolus | lnN CV 15% | Heise 2017 repeat clamps net of the SI share | evidence/07 | **Event** |
| A4d Dose-dependent bolus absorption | bolus depot rate × (dose / 15 U)^(−β), capped 0.7–3 | β 0.1 | Heise 2017 (aspart tmax 65.7 / 72.1 / 75.2 min at 0.1 / 0.2 / 0.4 U/kg) | L 433, 437 | **Event** |
| A4c Absorption-rate fluctuation | absorption rate × exp(log-OU), along each dose's curve | sd 0.5, τ 60 min [J] | Heinemann 2002: GIR at each time varies 25–30% across occasions vs 10–20% for summary measures (local blood flow) | L 417, 419 | **Event** |
| A4b Posture | upright absorption × (1 − p), asleep supine | p = 0.5 × U(0.19, 0.44) [J half-size] | Hildebrandt 1985 | L 163, 169 | **Drawn** |
| A5 Insulin action — disposal | X_D (rate p2) on absolute insulin; uptake X_D·M(G) − X_b·Gb; M = Gb + κ(G − Gb) above Gb, ∝ G below | p2 0.025 /min; κ lnN(1.0, 0.4) | p2: 0.2 U/kg lispro clamp (GIR peak ~100 min); κ: Best 1981 full text (uptake ∝ glucose) | L 303, 365 | Cohort p2; **Drawn** κ |
| A6 Insulin action — EGP | X_E (rate p2E) on relative insulin through a saturating hepatic signal; EGP = EGP_b · c(t) · clip(1 − sE·X_E) | EGP_b N(2.5, 0.33) mg/kg/min; p2E 0.012, faster offset 0.015; sE from G8's share | clamp GIR peak 108 min; post-meal EGP nadir vs Romeres 2025 | L 131, 193–196 | **Drawn** |
| A7 Renal excretion | Rcl(G − Rthr) above Rthr | Rthr N(180, 25); Rcl lnN(0.003, 0.3) | literature | evidence/01 §4.3 | **Drawn** |
| A8 Hypo risk amplification | S2013 form | λ 0 (off) | at 0.5 gave t<54 8.5% vs 0.13% | L 10 | Cohort (off) |
| A9 Counter-regulation + HAAF | EGP boost CRmax · h · σ((cr_g − G)/5), τ 15 min; h falls under 54 and recovers over 60 h | CRmax lnN(0.137, 0.5) mg/kg/min; cr_g N(65, 5) | fitted to the share of donor lows reaching 54 and nadir depths | L 166, 272, 360, 394 (on the FDA-held sensor) | **Drawn** |
| A10 Gut — mixed meals | per-meal parcels through stomach 1 → stomach 2 → gut; saturating energy ceiling (Vmax 3 kcal/min, Km 60 kcal) shared by everything in the stomach | f N(0.9, 0.05); per-meal speed lnN(0, 0.4); between-person Vmax lnN CV 30% and 28% delayed ×0.6–0.8 | Brener 1983, Hunt 1985, Calbet 1997; Samsom 2003 | evidence/09; L 33, 88 | **Drawn** person, **Event** meal |
| A10b Fast liquid phase | a share of each meal empties fast (0.08 /min) outside the ceiling | mean 0.35, per-meal Beta SD 0.40; 12% of main meals carry a sugary drink | donors' 5-min CGM step tail and G7 velocity kurtosis | L 268–271 | **Event** |
| A10c Slow late phase | 15% of each meal empties at Dalla Man kmin 0.008 /min | share [J] | Dalla Man 2007 | L 120; raising it flattens meals (L 364) | Cohort |
| A11 Hypoglycaemic acceleration | emptying × (1 + 1.5σ((70 − G)/5)) | ×2.5 below ~60 | Schvarcz 1995 | evidence/01 §6.4 | Cohort |
| A12 Fat and protein | early: fat slows emptying (via the energy ceiling); late: protein glucose 0.3 g / g, delay 90 min, chain 1/60; fat SI dip 1 − ρ·fat/50 from 0.5 h, full 1.5–6 h, gone by 10 h, relative to the person's own usual fat | fat / protein per carb gram from the person's carb share of energy (30 kcal/kg, rest 69 / 31% fat / protein), ±50% per meal; ρ U(0.1, 0.6) | Wolpert 2013 (+42% insulin after a high-fat dinner); Laxminarayan 2015 onset; Elleri 2013 LG meal (~0.49 g glucose per g protein + fat); Paterson 2017 | L 151, 352, 370, 373, 432 | **Personal** mix, **Drawn** ρ, **Event** composition |
| A12b Post-meal insulin action | SI × (1 − a·w) after each main meal; w in over 30–60 min, full 60–180, out by 240; relative to the person's own meals (mean 1 over the days) | a 0.4 | fitted to the donors' post-meal counteraction; no tracer study sizes it | L 321, 407, 408 (Pete: meal shape over lows), 436 | Cohort |
| A13 Fast glucose | rescue, proactive snack, exercise carbs, grazing: fast parcel, bioavailability f × 1.25 | — | Brodows 1984 (~3–4 mg/dL per g) | L 18 | Derived per person |
| A14 Circadian gastric emptying | emptying ×1.25 at 06–11 h, ×0.8 at 17–23 h, 1-h ramps | Goo 1987 ratio 1.54; split [J] | the split with the morning at 1.0 breaks dinner (L 375) | L 180, 339, 351 | Cohort |
| A15 Meal-slot composition | fat ×0.72 / 0.97 / 1.14, protein ×0.86 / 0.86 / 1.24 at breakfast / lunch / dinner | — | Vetrani 2022 (1,264 records, HCL) | L 338 | Cohort |

---

## 4. Time-varying modulators (`modulators.py`)

| Component | Form | Settings | How set | Rationale / evidence | Personal basis |
|---|---|---|---|---|---|
| B1 Circadian sensitivity | one of Visentin's 7 B/L/D classes, switches 04 / 11 / 17 h with 1-h ramps, daily mean 1 | classes equally likely; low/high N(0.40, 0.23) at half the swing | equal classes put 09 h on the donors' (L 59); swing from circadian_amp | Hinshaw 2013 (pattern individual) | **Drawn** |
| B1b Basal-need shape | EGP × the donor's quiet-hour delivered-insulin shape (mean 1) | quiet = no entry / manual bolus in 4 h, not disrupted | `add_delivered_profile` | donors' schedule shape over-states quiet need (L 214, 250); flat or schedule^0.5 shapes trade the lows (L 371) | **Donor** |
| B1c Per-donor circadian SI | the donor's own B / L / D SI posterior (`circ_own`) | — | `fit_body --segments` | reliability B 0.53, L 0.08, D 0.37 (L 335) | Donor, **off** |
| B2 Dawn phenomenon | EGP ramp to a 07:00 peak | p 0.52; amp lnN(0.3, 0.6) [J] | Ostrovski 2020 | only for people without a donor basal shape (the shape carries dawn, L 51) | Drawn (mostly unused) |
| B3 Day-level SI | independent lognormal per day | CV 8%, no persistence | repeat clamps 6–15% (evidence/07) | no measured day-to-day persistence (evidence/07) | **Event** (day) |
| B5 Menstrual cycle | SI falls through the late luteal phase to a low at onset, recovers by day 3 | 63% respond; amp lnN(0.08, 0.5); cycle N(28, 3) d | BDDP G7 cycle logs (493 events): +2 to +4.7 mg/dL to onset | L 136 | **Drawn** (F 13–50) |
| B6 Illness | Poisson episodes 1.5–15 d; SI −10 to −35%, EGP +0–15%; 20% GI (SI up, intake ×0.7) | 3 / yr adults, 5 / yr children | Mehta 2010; Tinti 2025 | evidence/02 | **Event** |
| B7–B10 Nightly factors | sleep loss (−5% SI / h), nocturnal GH (CV 0.32 on a 20% dawn increment), evening alcohol (63% drink, 3–20% of nights), stress (1/3 react; −18% SI 1–6 h, Moberg 1994) | — | Donga 2010, Edge 1990, Turner 2001, Riazi 2004 | evidence/12; L 77 | **Drawn** + Event |
| B11 Hyperglycaemic resistance | SI × (1 − H), H → 0.26·clip((G − 140)/220), τ 12 h [J τ] | — | Vuorinen-Markkola 1992; Yki-Järvinen 1987 | L 43 | Cohort |
| B14 Oral glucocorticoids | courses 0.09 / yr; morning dose; SI loss U(0.35, 0.60) tapering | — | Bevier 2008; Waljee 2017 | L 140 | **Event** |
| Scenarios (off) | pregnancy (X9), thyrotoxicosis (X12), niacin (D14), damaged insulin (D34), GLP-1 RA (B12) | `--set` / `--enable` | per factor catalog | L 87, 141, 336, 354 | — |

---

## 5. Exercise and everyday activity (`exercise.py`, `behavior.py`)

| Component | Form | Settings | How set | Rationale / evidence | Personal basis |
|---|---|---|---|---|---|
| C1 Insulin-independent uptake | ex_uptake · gain · Y · G/Gb, Y = intensity through a 7-min lag | ex_uptake lnN(3.0, 0.3) [J] | Dhaliwal 2025 glucose dependence | evidence/10 | **Drawn** |
| C2 Acute + delayed sensitivity | action × (1 + 2.0·(0.6 + k)·gain·Y/(Y + k) + Z): saturating in intensity, equal to the linear 2.0·Y at Y 0.6, ×2.5 at walking; Z driven above Y 0.12, decays τ 600 min | α 2.0, k 0.1, b 0.134 | Romeres 2021 (size at 0.6); Pemberton 2025 and the donors' workouts (no intensity dependence: METs < 4 / 4–6 / ≥ 6 net −7 / −13 / −9) for the shape; McMahon 2007 | L 34, 57, 243–246, 494–495 | Cohort |
| C3 Absorption during exercise | × (1 + 0.5 I) [J] | — | evidence/02 §1 | — | Cohort |
| C4 Anaerobic EGP surge | EGP + 28 mg/kg/min × intensity × anaerobic share above 60% of reserve | — | BDDP workouts ≥ 8 METs (rise ≥ 20 in 46%) | L 243, 247 | Cohort; **Drawn** anaerobic share |
| C5 Sessions | 0–5 / week, ~40 min, slot, pre-exercise carbs p 0.3; intensity from donors' workout METs (`ex_mets`) | — | validated against 18 k BDDP HealthKit workouts (L 137) | evidence/02, 04 | **Drawn** |
| C6 / C7 Everyday activity | episodes lnN(2 / day, 0.55), lnN(18 min, 0.75); waking background as alternating sitting and light bouts; intake covers the expected activity | METmax lnN(9, 0.25) age-adjusted; gain lnN(0, 0.5) | T1DEXI, NHANES, UK Biobank; Healy 2008 | L 34, 161, 163 | **Drawn** |
| C8 Activity and the gut | emptying up to ×1.15 walking, ×0.5 hard | — | Franke 2008 | L 344 (neutral) | off |

---

## 6. Sensor (`sensor.py`)

Per family (G6, G7, Libre 3, Libre 2, Medtronic); the twin wears its donor's family. Each session draws its own
calibration, noise level and transient rate.

| Component | Form | G7 / G6 / Libre 3 | How set | Personal basis |
|---|---|---|---|---|
| D1 BG → IG lag | first-order filter; G7 τ × 1.5 while glucose falls | τ 3.5 / 3.78 / 1.8 min | Vettoretti 2019; device studies; the fall factor sized on G7 MARD by rate of change (Garg 2022 Table 5; Cengiz & Tamborlane 2009; L 391) | **Event** (session) |
| D2 Calibration | gain a0 × drift × day-1 deficit + offset b0 | a0 N(0.98, 0.04) / N(0.96, 0.05) / N(0.965, 0.03); b0 N(3, 3) / N(2, 3) / N(0, 2) | fitted to FDA accuracy by range and two-sensor PARD (`sensor_fit.py`) | **Event** |
| D3 Sensor-specific noise | AR(2) (1.30, −0.42), Student-t (df 30 / 4 / 4), scale √(q² + (1 − q²)(IG/130)²) | σ N(1.3, 0.8) / N(1.0, 0.8) / N(1.5, 0.5); q 0.55 / 0.6 / 0.5 | G7 σ and q from the FDA accuracy tables by range (K213919, L 393); G6 q from DEN170088 (L 393), σ from donors' measurement noise (L 362) | **Event** |
| D3b Common (interstitial) noise | AR(3), continuous across sessions | σ 2.2 / 2.5 / 3.0 | Biagi 2017 form; G7 σ fitted jointly to the FDA tables and the donors' 5-min steps (L 384, 393) | **Drawn** (one process per person) |
| D3c Transient biases | ±lnN(8 mg/dL, 0.4), τ 10 min; low first 62% / 72% / 55% | 6.5 / 7.5 / 4 per day, session lnN(0.9) | each family's own donor quiet-window reversals (L 32, 390) | **Event** |
| D3d Noise wander, slow bias, early noise | noise level × exp(log-OU); slow bias (τ 3 h); day-1 extra noise | wander sd 0.45 / 0.7 / 0.7, τ 2 / 2 / 8 h; slow bias sd 5 / 3 / 5 | form Facchinetti 2011; wander fitted to the donors' 5-min step tails, clustering and dispersion where the FDA tables do not identify it (`sensor_eda.py`, L 384); Breton & Kovatchev 2008; G6 Pro day-1 MARD | **Event** |
| D4 Device smoothing | causal EMA | Libre 3 0.35 [J] | eda L33 | Cohort |
| D5 Compression lows | while asleep; depth lnN(35), 45 min | rate Gamma(2.37, 1/75.7) / day | donor detector (ice compression run) | **Drawn** |
| D6 Availability | warm-up, session length, early failure 5% [J], random gaps | gaps 4.4 / 1.7 / 1.5 per day | 153 donors | **Event** |
| D7 Reporting | 5-min grid, integer, 39 / 401 clamps | — | eda L3, L6 | Cohort |

The sensor is fitted only to sensor evidence (FDA tables, donors' measurement noise), never to CGM shape (L 299, 363).

---

## 7. Pump and infusion site (`device.py`)

LoopEval records what was commanded; the body receives what the device delivered. Loop computes insulin on board from
the commanded doses, so any insulin lost on the way (flow error, a failing or occluded site, a dislodged cannula,
lipohypertrophy) is still counted by Loop. This is phantom IOB: insulin Loop believes is acting but the body never got.
The simulator logs commanded, delivered and absorbed insulin for every dose, so phantom IOB is known exactly. Real donor
records carry only the commanded side.

| Component | Form | Settings | Evidence | Personal basis |
|---|---|---|---|---|
| E2 Flow error | device bias N(0, 1.5%) + AR(1) τ 45 min | 1-h sd Omnipod 11%, durable 4.5%, twiist 3% at 1 U/h | Freckmann 2019; Ziegler 2021 | **Drawn** (device) |
| E3 Bolus error | sd c/√U, floor 0.6% | Omnipod c 0.12, durable 0.03 | evidence/06 | **Event** |
| E4 Start-up transient | after each site change, decays 4 h | Omnipod N(+5%, 5%) | evidence/06 | **Event** |
| E5 / E5b Site life | absorption 0.9 → 1.15 by day 4; efficacy −2.5% / day after day 1; per-site speed lnN CV 27% | site change every N(3.0, 0.4) d | Swan 2009; Sampson Perrin 2015; Haidar 2013 | **Event** (site), Drawn interval |
| E6 Failing site | absorbed fraction → 0.3 (τ 4 h) | p 0.012 per site | Kanapka 2022 | **Event** |
| E7–E10 Occlusion, bubble, dislodgement | partial (0.4 / wear), full + alarm (0.003), bubble (0.2), dislodge (0.004) | splits [J] | evidence/06; Kanapka 2022 | **Event** |
| E11 Lipohypertrophy | half of LH people's sites at bioavailability 0.78, dose CV 0.5 | 26% adults, 42% children | Pickup 2014; Famulla 2016 | **Drawn** |

---

## 8. Behaviour: the person as a second controller (`behavior.py`)

Traits come from the donor wherever the ice pilot measured them; otherwise from literature priors.

| Component | Form | Settings | How set | Personal basis |
|---|---|---|---|---|
| F1 Meal schedule | 3 main meals on the donor's own window clock (median and SD per window), snacks on the donor's eating clock; breakfast skipped on the donor's own share of days (`skip_own`, median 0.18), its grams carried by the other meals; weekend shift [J] | — | donor meals tables; L 51, 182, 368 | **Donor** |
| F1b Meal sizes | carbs/day split by the donor's window shares, the labelled morning load converted to grams (`slot_true`); per-event log SD = the donor's pulse spread; day total AR(1) CV 0.22, ρ 0.29 | — | Tarasuk & Beaton 1992; Levitsky 2017; L 39, 231, 346 | **Donor** + Event |
| F2 Announcement | per-window entry chance so entered grams follow the donor's window shares (`entry_win`); meals vs snacks entries split as the donor does (`entry_split`) | entries/day from the donor's raw record | carbs.json; L 280, 341, 345 | **Donor** |
| F2b Carb count | entered = eaten × exp(bias + per-meal error + size error) | bias N(−0.10, 0.10); per-meal sd lnN(0.3, 0.3); Brazeau 2013 size regression | Brazeau 2013 (692 meals) | **Drawn** + Event |
| F3 Meal bolus and top-ups | bolus with entry, timing class, split second bolus, top-ups 20–60 min later if high | rates from the donor's raw boluses-with-entry and top-ups; timing from the donor's measured lead | raw record; L 42, 47, 64, 216 | **Donor** |
| F4 Corrections | hazard per awake minute above the donor's correction level, weighted by CGM trend; size from the donor's | rate from the donor's exposure-normalised corrections, iterated per person (`corr_p_mult`) | ice corrections; L 225, 237 | **Donor** |
| F5 Low defense | proactive snack on a projected low; rescue at the donor's threshold and size; re-check 15 min, re-treat 34%; 12% of rescues and proactive snacks entered in the app (sized on the donors' logged treatments, L 500) | onset N(60, 20) (fitted to the donors' lows, L 409); proactive lnN(12 g) | ice L34, L69; Savard 2016 | **Donor** (rescue) + Drawn |
| F6 Monitoring and sleep | glances lnN(6 / day); alerts 76 / 240, Dexcom Urgent Low Soon (projected 55 in 20 min); alarm wakes p N(0.72, 0.2); woken, the person may act proactively | bed / wake N(23 h / 7 h, 50 min) | Puhr 2020; Dexcom user guides; donors' night rescues and pre-emptive carbs (L 274, 442) | **Drawn** |
| F9 Grazing | unlogged small intake on the donor's unannounced-pulse clock, absorbed fast | lnN(2 / day, 1.0) × lnN(10 g, 0.4), a quarter kept (`graze_keep` 0.25) | rate set by the donors' unannounced labelled load (97.3 vs 94.7 g-eq / day) and g-eq per entered gram (1.18 vs 1.19); Piernas & Popkin 2010; L 78, 158, 230, 382 | Drawn rate, **Donor** clock |
| F10 Food dosed by hand | an unentered eating event bolused from the person's estimate ÷ CR | the donor's lone-bolus rate × its food share | pilot lone boluses; Groat 2017 | **Donor** |
| F12 Temporary Overrides | less-insulin with activity, lowered target before entries, raised target, reactive more-insulin on rising highs | the donor's rates, factor, target and duration per class | 19,732 donor windows; L 40 | **Donor** |
| F13 Settings edits | dated multiplicative edits to basal / ISF / CR | the donor's rate per setting; size lnN(3.6%, 1.06) [J] | donor therapy timelines; L 41 | **Donor** rate |
| B13 Entered absorption time | 0.5 / 3 / 5 h by the donor's own shares, split ≤ 20 g vs larger | — | donor carbs.json (67,499 entries); L 101 | **Donor** |
| F7 / F8 Exercise habits, site changes | §5, §7 | — | — | Drawn |

---

## 9. What is personal, at a glance

**From the donor (the twin's own):** TDD, settings and their eras, true ISF (data-fitted), insulin formulation, sensor
family, pump, dosing strategy share, controller RC mode (validation), basal-need shape, per-donor meal response (carb
sensitivity), meal clock and window shares, breakfast skipping, snack and entry rates per window, absorption-time
choices, bolus habits (with-entry rate, timing, splits, top-ups), corrections (level, rate, size), food dosed by hand,
rescue threshold and size, grazing clock, Temporary Override habits, settings-edit rates, suspend threshold.

**Drawn per person (population distributions):** body weight, basal share, glucose effectiveness, volumes, insulin PK
rates, κ, EGP level and share, counter-regulation, renal threshold, gastric-emptying speed (incl. delayed emptying),
fat-resistance ρ, posture, circadian class, dawn, cycle response, alcohol and stress traits, exercise and activity
traits, compression-low rate, lipohypertrophy, carb-count bias, sleep times, glances and alarm waking.

**Redrawn per event:** per-meal size, speed, fast share, composition, count error; per-dose absorption jitter; per-day SI;
illness and steroid episodes; per-sensor-session calibration, noise and transients; per-site absorption, failures and
occlusions.

**Cohort constants:** insulin action rate p2, slow late phase share, circadian emptying factors, meal-slot composition,
exercise sensitivity sizes, hyperglycaemic resistance, protein-to-glucose 0.3 g / g, the CSF calibration constant.

---

## 10. Validation: the weighted match score (`validate.py`, `lifestats.py`, `score.py`)

**How a run is scored.**
- **Reference:** 206 pilot donors, one 13-day block per donor against each twin's 14-day window (`real_pilot_blocks.csv`,
  `life_blocks.csv`; L 330).
- **Same code on both sides:** every row is computed by one function on a donor's block and on a twin's window. The
  glucose rows use eda's code on the CGM the sensor reported. The insulin rows read delivery by record rate (L 455). The
  meal rows use the ice labeller, and the activity rows use the HealthKit workouts against the twins' sessions.
- **Sensor split:** rows that depend on the instrument are split by sensor family (G6, G7, Libre 3; eda L33).
- **Gap per row** (`score.py`, L 492): the median difference in units of the donors' between-person spread (S = 10–90%
  width / 2.563), plus half the log ratio of the two spreads. A gap within 2 bootstrap SEs is draw noise. Below 0.25
  counts as close.
- **Tiers and weights** (L 492): rows are ranked by how directly a mismatch would change a candidate algorithm's TIR /
  t<54 delta.
  - **Tier 1, weight 3:** outcome and what Loop sees. Level, time in ranges, lows, insulin total, carb entries, the meal's
    3-h change, and the activity response.
  - **Tier 2, weight 2:** dynamics the controller reacts to. CV, 5-min rate spread, day-to-day and circadian
    structure, delivery shape, user boluses. Also **what moves glucose** (L 494): meal absorption shape, unlogged rises,
    fast falls, unexplained falls, workout frequency, duration, intensity and timing after meals.
  - **Tier 3, weight 1:** the sensor's fingerprint and the distribution's shape.

  The score is the weighted mean gap (lower is better). The tiers are a judgement. The test that would earn each weight
  is whether a candidate's delta moves on twins that differ in that row alone, and it has not been run yet.
- **The activity response** is pooled over bouts, because a window holds a handful. It is Pemberton 2025's design: ΔCGM
  over a bout's first 20 min, less matched windows of the same person (start ±15 mg/dL, ROC ±0.5 mg/dL/min, IOB
  ±0.5 U, no logged entry). The workout habit rows use only donors who record a workout in at least half their blocks,
  and their twins (11 donors). Most donors with any workout record one rarely, so for them the count measures a
  recording habit (L 496).
- **The KS count** ("matched of 51", KS p > 0.05) is still written to `compare_pilot.csv` / `compare_life.csv`. Its
  cut depends on the sample size, so the weighted score ranks runs.
- **Two draws of people:** draw 1 is seed 1000, draw 2 is seed 5000. The draw moves the score by about 0.04 and tier 1 by
  about 0.07, so adopt a change only when it holds on both draws (L 444, 492).
- **Running it:** cohort, then `python -m loopeval_analysis.patient_sim.meal_response <run>` (the labeller), then
  `python -m loopeval_analysis.patient_sim.lifestats sim <run>`, then `python -m loopeval_analysis.patient_sim.score
  <run> [<run> ...] --detail`. Scores from before L 494's rows do not compare with later ones.

**Status at the reference lg12 (draw 1) / lg12_5k (draw 2):**

| | Tier 1 | Tier 2 | Tier 3 | Score | Close (of 51) |
|---|---|---|---|---|---|
| draw 1 | 0.237 | 0.456 | 0.413 | 0.371 | 22 |
| draw 2 | 0.278 | 0.473 | 0.471 | 0.400 | 16 |

The workout duration, METs and after-meal rows have too few twins on draw 1 (4 of 112 have a consistently recording
donor), so they drop out of this joint table. On draw 2 they pass (35 vs 45 min, 5.6 vs 5.5 METs, 0.50 vs 0.33).

| Tier | Statistic | What it measures | Donors p50 | Twins draw 1 / 2 | Gap draw 1 / 2 |
|---|---|---|---|---|---|
| 1 | `act_net20` | activity response: 20-min ΔCGM of a bout less matched windows (mg/dL), pooled over bouts | -5.71 | -1.82 / 0.133 | 0.45 / 0.67 |
| 1 | `act_net20_hi` | the same, bouts from > 150 mg/dL with IOB ≥ 2 U | -12.6 | -5.26 / -7.13 | 0.78 / 0.58 |
| 1 | `bg_mean` | mean glucose (mg/dL) | 151.9 | 154.9 / 156.5 | 0.15 / 0.30 |
| 1 | `carb_entries_per_day` | carb entries per day | 2.96 | 3.04 / 3.67 | 0.09 / 0.38 |
| 1 | `lows_per_day` | crossings below 70 per day | 1.00 | 0.917 / 1.00 | 0.24 / 0.12 |
| 1 | `meal_d3h` | bolused isolated meal: glucose change at 3 h (mg/dL) | 38.0 | 31.5 / 36.0 | 0.35 / 0.11 |
| 1 | `min_below70` | minutes per low | 20.0 | 20.0 / 20.0 | 0.02 / 0.03 |
| 1 | `p_reach54` | share of lows that reach 54 | 0.212 | 0.200 / 0.192 | 0.10 / 0.16 |
| 1 | `t180` | time > 180 (%) | 25.9 | 27.2 / 29.9 | 0.10 / 0.32 |
| 1 | `t54` | time < 54 (%) | 0.190 | 0.186 / 0.204 | 0.23 / 0.14 |
| 1 | `t70` | time < 70 (%) | 1.60 | 1.72 / 1.71 | 0.17 / 0.15 |
| 1 | `tdd` | total daily dose (U) | 38.7 | 42.3 / 44.8 | 0.31 / 0.37 |
| 1 | `tir` | time 70–180 (%) | 71.9 | 70.6 / 68.0 | 0.11 / 0.28 |
| 2 | `ac1` | day-to-day autocorrelation of TDD | 0.091 | -0.033 / -0.008 | 0.48 / 0.34 |
| 2 | `between_day_frac` | share of glucose variance between days | 0.105 | 0.125 / 0.120 | 0.50 / 0.44 |
| 2 | `bg_cv` | coefficient of variation (%) | 34.6 | 35.0 / 36.1 | 0.19 / 0.29 |
| 2 | `bg_skew` | skew of the glucose distribution | 0.873 | 0.827 / 0.818 | 0.19 / 0.19 |
| 2 | `circadian_amp` | 24-h amplitude, per person | 0.128 | 0.135 / 0.152 | 0.20 / 0.41 |
| 2 | `conc1` | share of insulin in the busiest 1% of bins (%) | 28.0 | 26.7 / 28.2 | 0.23 / 0.22 |
| 2 | `day_night` | day / night insulin per hour | 2.00 | 1.68 / 1.87 | 0.49 / 0.26 |
| 2 | `entry_fast_fall` | carb entries followed within 2 h by a fast fall (%) | 14.3 | 7.41 / 7.28 | 0.76 / 0.70 |
| 2 | `fast_fall_share` Dexcom G6 | falling 15-min windows faster than 2.5 mg/dL/min (%) | 2.41 | 1.71 / 1.85 | 0.71 / 0.34 |
| 2 | `fast_fall_share` Dexcom G7 | falling 15-min windows faster than 2.5 mg/dL/min (%) | 2.80 | 1.62 / 1.98 | 0.66 / 0.46 |
| 2 | `fast_fall_share` Libre 3 | falling 15-min windows faster than 2.5 mg/dL/min (%) | 2.63 | 3.81 / 2.99 | 0.65 / 0.20 |
| 2 | `ice_dip_day` | unexplained falls per day (ICE 70 mg/dL/h below the window median, ≥ 20 min) | 0.692 | 1.42 / 1.71 | 1.22 / 1.70 |
| 2 | `ice_dip_day_share` | share of unexplained falls between 08 and 22 h | 0.660 | 0.523 / 0.470 | 0.69 / 1.09 |
| 2 | `manual_u_day` | hand-dosed units per day | 12.2 | 11.7 / 14.5 | 0.12 / 0.30 |
| 2 | `med_nonzero` | typical nonzero 5-min delivery (U) | 0.085 | 0.098 / 0.100 | 0.30 / 0.35 |
| 2 | `night_cv` | night-to-night CV of night insulin (%) | 35.4 | 31.6 / 34.1 | 0.28 / 0.20 |
| 2 | `p99` | 99th percentile of 5-min delivery (U) | 1.83 | 1.51 / 1.96 | 0.33 / 0.21 |
| 2 | `pulse_dur_h` | meal pulse: duration (h) | 1.92 | 1.86 / 1.84 | 0.20 / 0.22 |
| 2 | `pulse_peak_h` | meal pulse: time to peak appearance (h) | 0.750 | 0.622 / 0.622 | 1.04 / 1.15 |
| 2 | `pulse_peak_per_g` | meal pulse: peak g-eq/h per g | 1.18 | 1.06 / 1.07 | 0.85 / 0.79 |
| 2 | `sigma_disp` | dispersion of volatility across days | 3.57 | 3.03 / 3.13 | 1.06 / 0.89 |
| 2 | `tdd_cv` | day-to-day CV of TDD (%) | 15.9 | 15.8 / 15.2 | 0.09 / 0.34 |
| 2 | `unann_pulses_day` | unannounced meal pulses per day (ice labeller) | 3.46 | 4.00 / 4.04 | 0.52 / 0.52 |
| 2 | `unl_rise_rate` | unlogged rise: climb rate (mg/dL/h) | 54.9 | 47.8 / 50.9 | 0.52 / 0.27 |
| 2 | `unl_rises_day` | unlogged CGM rises ≥ 40 mg/dL per day | 1.62 | 1.96 / 1.75 | 0.41 / 0.32 |
| 2 | `user_boluses_per_day` | user boluses per day | 4.58 | 4.75 / 5.42 | 0.08 / 0.28 |
| 2 | `v_sd` Dexcom G6 | SD of the 5-min CGM change | 6.37 | 6.10 / 6.35 | 0.39 / 0.20 |
| 2 | `v_sd` Dexcom G7 | SD of the 5-min CGM change | 7.19 | 6.45 / 6.81 | 0.59 / 0.39 |
| 2 | `v_sd` Libre 3 | SD of the 5-min CGM change | 5.72 | 6.43 / 5.91 | 0.58 / 0.28 |
| 2 | `vol_cluster_60m` | volatility clustering at 60 min | 0.122 | 0.109 / 0.122 | 0.37 / 0.09 |
| 2 | `workouts_week` | workouts per week (consistent recorders and their twins) | 1.62 | 1.75 / 2.33 | 0.13 / 0.54 |
| 2 | `zero_frac` | share of 5-min bins with no insulin (%) | 32.5 | 30.2 / 30.6 | 0.28 / 0.34 |
| 3 | `acf_min` Dexcom G6 | minimum of the step autocorrelation | -0.110 | -0.114 / -0.115 | 0.19 / 0.24 |
| 3 | `acf_min` Dexcom G7 | minimum of the step autocorrelation | -0.110 | -0.128 / -0.129 | 0.34 / 0.44 |
| 3 | `acf_min` Libre 3 | minimum of the step autocorrelation | -0.143 | -0.269 / -0.112 | 2.17 / 0.89 |
| 3 | `acf_zero_min` | minutes until the step autocorrelation first crosses zero | 40.0 | 55.0 / 60.0 | 1.28 / 1.59 |
| 3 | `boxcox_lambda` | distribution shape (0 = log-normal) | 0.000 | 0.050 / 0.050 | 0.18 / 0.26 |
| 3 | `hurst_long` | long-range persistence | 0.253 | 0.249 / 0.270 | 0.10 / 0.15 |
| 3 | `hurst_short` Dexcom G6 | short-range persistence | 0.746 | 0.771 / 0.770 | 0.67 / 0.58 |
| 3 | `hurst_short` Dexcom G7 | short-range persistence | 0.735 | 0.764 / 0.772 | 0.50 / 0.67 |
| 3 | `hurst_short` Libre 3 | short-range persistence | 0.800 | 0.832 / 0.793 | 1.10 / 0.46 |
| 3 | `sd_over_mad` Dexcom G6 | tail weight of 5-min changes | 1.44 | 1.43 / 1.42 | 0.31 / 0.52 |
| 3 | `sd_over_mad` Dexcom G7 | tail weight of 5-min changes | 1.41 | 1.38 / 1.38 | 0.81 / 1.01 |
| 3 | `sd_over_mad` Libre 3 | tail weight of 5-min changes | 1.38 | 1.43 / 1.38 | 2.04 / 0.62 |
| 3 | `sigma_meas` Dexcom G6 | measurement noise | 1.24 | 1.14 / 1.42 | 0.33 / 0.37 |
| 3 | `sigma_meas` Dexcom G7 | measurement noise | 1.36 | 1.22 / 1.36 | 0.25 / 0.01 |
| 3 | `sigma_meas` Libre 3 | measurement noise | 1.27 | 1.31 / 1.72 | 0.43 / 1.40 |
| 3 | `v_kurtosis` Dexcom G6 | kurtosis of 5-min changes | 3.30 | 3.36 / 3.41 | 0.09 / 0.16 |
| 3 | `v_kurtosis` Dexcom G7 | kurtosis of 5-min changes | 2.51 | 2.66 / 2.48 | 0.17 / 0.14 |
| 3 | `v_kurtosis` Libre 3 | kurtosis of 5-min changes | 2.35 | 3.72 / 2.27 | 1.71 / 0.76 |
| 3 | `v_skew` Dexcom G6 | rises vs falls asymmetry | 0.257 | 0.222 / 0.379 | 0.37 / 0.51 |
| 3 | `v_skew` Dexcom G7 | rises vs falls asymmetry | 0.331 | 0.259 / 0.271 | 0.33 / 0.29 |
| 3 | `v_skew` Libre 3 | rises vs falls asymmetry | 0.086 | 0.215 / -0.039 | 0.78 / 1.75 |
| 3 | `wear` | sensor coverage | 0.974 | 0.976 / 0.972 | 0.09 / 0.10 |

**Where the gaps are** (gap ≥ 0.5 on both draws, or tier 1 ≥ 0.4):
- **Activity response:** the twins' sessions fall less in their first 20 min, most of all from high glucose and IOB.
  Sessions with no eating fall like the donors' workouts; 60% of the twins' sessions have eating from 30 min before to the
  end, mostly the unlogged pre-exercise carbs (RAPPID's 36% of sessions). Session timing, the C4 threshold and deferring
  eating out of sessions do not move it beyond the draw scatter (L 497). IOB is the ice extractor's total insulin on board
  on both sides.
- **Meals:**
  - Entries ending in a fast fall: 7 vs 14%.
  - Labelled pulses peak earlier and lower: 0.62–0.67 vs 0.75 h, 1.05 vs 1.18 g-eq/h per g.
  - Unlogged rises climb slower: 45–50 vs 55 mg/dL/h (L 494).
- **Fast falls:** the twins have two thirds of the donors' (0.97 vs 1.47 / day), all of the gap at 12–24 h and at short
  scales (15–30 min); their true glucose almost never falls faster than 2.5 mg/dL/min. No single body component restores
  it (L 498).
- **Unexplained falls:**
  - The twins have about twice the donors' rate, all of the surplus at 00–12 h, peaking 04–08 h. That is the dawn /
    night-lows limit (L 438, 495). The afternoon and evening match.
  - About a third of the twins' night dips are sensor-made, mostly the co-located AR(3) error (D3b). Quiet-night CGM
    wander still matches the donors'.
- **Level, on draw 2:** donors who keep tight control get twins that run high on more insulin (L 445–456).
- **G7 short-scale motion and the ACF zero crossing:** the twins' 5-min moves are a little smaller and turn later
  (55–60 vs 40 min). No body lever moves the turn (L 385–389).
- **Day-to-day structure:** `sigma_disp`, `between_day_frac`, `ac1` (L 372, 376, 457).
- **Delivery shape:** `med_nonzero` (larger nonzero deliveries) and `day_night` (1.7–1.9 vs 2.0).

**Component targets** (`review.py`) check each component against the donors with the same code: low nadirs and depths,
meal drops and the 3-h change, behaviour rates. The measure scripts sit beside each run.

## 11. Switches (`cohort.py`)

`--enable a,b` / `--disable a,b` / `--set k=v`. On by default (`--disable` to ablate): `isf_total`, `egp_sat`,
`prof_deliv`, `suspend_own`, `csf_geq`, `ge_var`, `ge_circ`, `fat`, `slot_true`, `entry_split`, `entry_win`,
`skip_own`, `missed_own`, `macro_own`, `fat_rel`, `ppr_rel`, `night_pro`, `uls`, `posture`, `act_frag`, `lipohypertrophy`, `outages`, `overrides`, `edits`, `counterreg`, `glucotox`.
Off by default (`--enable`): `rc_own` (on in every validation run), `night_own`, `circ_own`, `intake_own`,
`prof_np`, `csf_lvl`, scenarios. Numeric: `ins_p2`, `pro_glc`, `meal_slow`, `ge_am` / `ge_pm`, `cr_mult`, `sg_mult`,
`kappa_mult`, `csf_lvl`, `ex_sat` (C2 saturation, default 0.1; 0 = linear), `ex_alpha`, `ex_up_mult`, `ex_surge_thr` (C4 threshold, default 0.6), `sensor_act_k` (activity-dependent CGM noise, off), `sleep_own` (donor-own sleep window, off), sensor fit
parameters (`sensor_*`).

## 12. Open items

**Status (Pete 2026-10-20): usable with LoopEval.** The items below are documented limits, not blockers.

1. **Twins of tight-control donors run high, and twins need 5–8% more insulin than their donors** (L 445–456).
2. **Night lows build toward dawn:** 31% of lows fall at night, against the donors' 22%. Night treatment and
   post-exercise nights now match (L 438–443, 458).
3. **Meals:** the 3-h meal change is +13 to +18 against +21 (L 429–436).
4. **Reversal time and G7 short-scale motion** (§ 10).
5. **Day-to-day structure:** `sigma_disp`, `ac1` (§ 10).
6. **What moves glucose** (§ 10, L 494–497): the activity response at high IOB, entries ending in a fast fall (7 vs
   14%), slower unlogged rises, flatter meal pulses, and twice the donors' unexplained falls at 00–12 h.

## Key references

Full lists in `evidence/01 §8`, `02`, `03 §5`, `04`, `06`, `07`, `09`, `10`.

- Bergman RN et al. Am J Physiol 1979;236:E667 · Hovorka R et al. Physiol Meas 2004;25:905 · Dalla Man C et al. IEEE TBME
  2007;54:1740 · Visentin R et al. DTT 2015;17:1 · Romeres D et al. 2025 (meal EGP) · Best JD et al. 1981 (κ)
- Heise T et al. Clin Pharmacokinet 2017;56:551 · Hildebrandt P 1985 (posture) · Famulla S et al. Diabetes Care
  2016;39:1486 · Swan KL et al. 2009 (site life) · Kanapka LG et al. 2022 (site failures)
- Smart CE et al. Diabetes Care 2013;36:3897 · Wolpert HA et al. Diabetes Care 2013;36:810 · Elleri D et al.
  Diabetologia 2013;56:1108 · Paterson MA et al. Diabet Med 2017 · Laxminarayan S et al. DTT 2015 · Vetrani C et al.
  Diabetologia 2022 · Goo RH et al. 1987 (circadian emptying) · Samsom M et al. 2003 · Brazeau AS et al. 2013
- Romeres D et al. 2021 · McMahon SK et al. 2007 · Riddell MC et al. (T1DEXI) Diabetes Care 2023;46:704 · Marliss &
  Vranic 2002
- Mehta NN et al. Diabetes 2010;59:172 · Bevier WC et al. 2008 · Ostrovski I et al. Can J Diabetes 2020;44:157
- Vettoretti M et al. Sensors 2019;19:5320 · Biagi L et al. 2017 · Facchinetti A et al. 2011, 2014 · Breton M,
  Kovatchev B. JDST 2008;2:853 · FDA DEN170088 (G6), K213919 (G7), K212132 (Libre 3)
