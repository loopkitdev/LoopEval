# Component registry — the additive patient simulator

Every factor the simulator composes, with its model form, its parameters and where each
parameter's value comes from. A component is **only as good as its evidence column**: a
literature reference (`evidence/0x §n`, with the citation there) or a measurement on BDDP data
(a `runs/` path and the script that produced it). Values marked **[J]** are judgement calls
waiting for evidence; they are the first things to replace.

Tiering follows `evidence/00-factor-catalog.md` §tiers (frequency × magnitude × survives AID
feedback). Status: **built** (code exists, tested in isolation) · **wired** (runs in the closed
loop) · **validated** (compared with the donor targets) · **planned**.

The code is `analysis/loopeval_analysis/patient_sim/`.

---

## A. Physiology (`physiology.py`, `insulins.py`)

| Component | Model form | Key parameters (population prior) | Evidence | Status |
|---|---|---|---|---|
| A1 Glucose kinetics | one compartment, glucose effectiveness SG(G−Gb) | VG 1.45 dL/kg; SG lognormal median 0.003 /min [J: lowered from ReplayBG's 0.022, see note 1]; Gb N(119, 7) | 01 §1.2, §4.2; ReplayBG code | built |
| A2 SC insulin PK | per-dose depot, delay τ → Isc1 → Isc2 → plasma; optional fast route | kd lnN(−3.51, 0.62), ka2 lnN(−4.29, 0.43), ke 0.127, VI 0.126 L/kg | 01 §1.3, §3.1 | built |
| A3 Insulin formulations | τ, kd/ka2 multipliers, fast fraction ψ per formulation | lispro/aspart reference; Fiasp, Lyumjev FITTED to clamp contrasts (Lyumjev: AUC0–15 ×7.2, >3 h ×0.60; Fiasp: AUC0–30 ×2.0); regular human insulin | 01 §3.2; `insulins.fit_formulations` | built |
| A4 Per-dose absorption variability | ω per bolus scales kd, ka2 (and k_fast) | lnN CV 20% (clamp) – 30% (free-living) | 01 §3.3 | built (sampler planned) |
| A5 Insulin action — disposal | X_D lag p2; uptake X_D·M(G)·risk(G), M saturating (Km 225) | p2 0.0121 /min; SI_D calibrated per person to the true ISF | 01 §1.2; UVA Km | built |
| A6 Insulin action — EGP suppression | X_E lag p2E on relative insulin (I−Ib)/Ib; EGP = EGP_b·c(t)·clip(1−sE·X_E, 0, 1+sE) | EGP_b 2.5 ± 0.33 mg/kg/min; p2E 0.008 [J]; sE calibrated from an EGP share of ISF [J, note 2] | 01 §4.1; Hovorka 2004 | built |
| A7 Renal excretion | Rcl·(G − Rthr) above Rthr | Rthr N(180, 25); Rcl 0.003 /min CV 30% | 01 §4.3 | built |
| A8 Hypo risk amplification (S2013) | insulin uptake × [1 + λ·10 r1 (ln G^r2 − ln Gb^r2)²] below Gb, frozen < 60 | r1 1.4407, r2 0.8124; **λ ∈ [0, 1] calibrated jointly with A9** | 01 §4.5 | built |
| A9 Counter-regulation + HAAF | EGP boost CRmax·h·σ((65−G)/5), τ 15 min; h drops while < 54, recovers over ~60 h | CRmax lnN(1.0 mg/kg/min, CV 50%) [J]; τ_rec 48–72 h | 01 §4.4 (no clamp-calibrated prior exists) | built |
| A10 Gut — carbohydrate | per-meal parcel, Qsto1 → Qsto2 → Qgut (linear Dalla Man), delay β, bioavailability f | mixed meal kempt 0.025, kabs 0.05 [J, chosen for Ra peak ~1 h, 3–4 h duration]; per meal kabs CV 40%, f 0.9 CV 15–20% | 01 §6.1–6.2 | built |
| A11 Gut — hypoglycaemic acceleration | kempt × (1 + 1.5·σ((70 − G)/5)) | ×2.5 below ~60 | 01 §6.4 (Schvarcz 1995) | built |
| A12 Fat / protein | early: kempt × 1/(1 + fat/60); late: slow parcel 0.1·protein g, k 1/120, delay 90 min; fat SI dip 1 − ρ·fat/50 at 3–6 h | ρ U(0, 0.35) | 01 §6.3 (Smart 2013, Wolpert 2013, Bell 2020, Paterson 2017) | planned |
| A13 Rescue carbohydrate | fast parcel: kempt 0.08, kabs 0.08, β 5, f 1.0; juice kabs × 0.6 | — | 01 §6.5 (Brodows 1984) | planned (params set, sampler pending) |

Note 1 — **glucose effectiveness**: ReplayBG's identified SG (median 0.022 /min) makes every
perturbation fade with a ~45 min time constant, which contradicts flat basal tests and eda's weak
closed-loop restoring force (+7 mg/dL/h at 50 → −2 above 300; eda lesson 44). UVA/Padova-plant
fits give 0.0013–0.0047 (memory: treatment-kernel-transient). Default 0.003; the restoring-force
and rescue-kernel targets decide it in closed loop.

Note 2 — **how insulin's effect splits between EGP and disposal**: with EGP_b/VG = 103 mg/dL/h,
the EGP arm alone gives ISF × basal-rate ≈ 103·sE, while the population rule
(ISF ≈ 1800/TDD, basal ≈ 45% of TDD) needs ≈ 34. So sE ≲ 0.3 unless EGP_b is much lower. Calibrate
sE from a share of ISF (prior U(0.3, 0.5) [J]) and check against the glucose rise after insulin
withdrawal (literature + donor suspensions; planned measurement).

## B. Time-varying modulators (`modulators.py`, planned)

All multiply A5/A6 sensitivity (`si_mult`) or basal EGP (`egp_mult`). Each is separately
switchable for ablation.

| Component | Model form | Parameters | Evidence | Status |
|---|---|---|---|---|
| B1 Circadian sensitivity | Visentin 7-class B/L/D profile, switches 04/11/17 h, smoothed 1 h; low = 0.4 × high; ×N(1, 0.2) | class probabilities 0.10/0.05/0.05/0.10/0.20/0.20/0.30 | 01 §5.1 (Visentin 2015) | planned |
| B2 Dawn phenomenon | EGP ramp from onset U(02:00, 04:30) to waking | present p 0.45–0.52; magnitude lnN median +1.0 mg/kg/min | 01 §5.1; 02 dawn | planned |
| B3 Day-to-day need | per-day lognormal multiplier + intraday OU on log SI | day CV ~15%, intraday σ 0.2, τ 3–6 h | 01 §5.2 (Ruan 2016: CV 31/22/17%); **target: ice L19 day-level sd ≈ 11 mg/dL/h, lag-1 day 0.4** | planned |
| B4 Slow drift | OU on log SI, τ 14–30 d, σ 0.1 | — | 01 §5.3; eda L45 (41/156 drift > 5%/30 d) | planned |
| B5 Menstrual cycle | luteal SI dip, cycle 28 ± 3 d | 61–65% of women affected; TDD +3–11% luteal (teens +10.5%) | 02 menstrual; 00 D30 | planned, **off by default** (no rhythm detected in donors: run:2026-10-11-ice-slow/cycle_screen.csv) |
| B6 Illness | episodes ~2–4 /yr, 3–14 d; SI ×(0.65–0.85) ramp in/out; GI illness: needs −24% | 02 illness; 00 D21a | planned |
| B7 Stress / sleep loss | short sleep: next-day SI −14 to −21%; acute stress: small post-meal effect | 02; 00 D20, D21b | planned (tier 2) |
| B8 Alcohol | delayed hypo risk 10–15 h: SI ↑ / EGP ↓ overnight | 02; 00 D6 | planned (tier 2) |
| B9 Heat | absorption ×1.5–5 (kd, ka2 multiplier) | 02; 00 D36 | planned (tier 2) |
| B10 Puberty / age | SI −25–30% in puberty | 02; 00 D31 | via person sampler |
| B11 Hyperglycaemia-induced resistance | after long highs, SI −26% / 24 h | 00 D29 | planned (tier 2) |

## C. Exercise (`exercise.py`, planned)

| Component | Model form | Parameters | Evidence | Status |
|---|---|---|---|---|
| C1 Acute aerobic | insulin-independent uptake ∝ intensity (A-ex_uptake) + acute SI boost; ETH-style states | calibrate to T1DEXI session drop vs start BG and IOB (+4 below 100, −61 at 250–300; +5 at IOB < 1 U, −30 at ≥ 3 U) | 02 exercise (Deichmann 2023; T1DEXI) | planned |
| C2 Anaerobic / HIIT | EGP surge (catecholamines), +41 mg/dL at 80% VO2max | — | 02; 00 D16 | planned |
| C3 Delayed sensitivity | SI multiplier τ ≈ 600 min; biphasic 7–11 h after late-afternoon exercise | overnight hypo 48% vs 28% of nights | 02; 00 X6 | planned |
| C4 Sessions | ~60% of days, ~5.7/week, mean 41 min (T1DEXI is an active cohort — scale down) | — | 02 | planned (behavior) |

## D. Sensor (`sensor.py`, planned)

One parameter set per sensor session, per family (G6, G7, Libre 3 via twiist, Libre 2, Guardian).

| Component | Model form | Parameters | Evidence | Status |
|---|---|---|---|---|
| D1 BG→IG lag | first-order filter | τ per session, median 3.8 min (G6), G7 3.5, Libre 3 1.8 | 03 | planned |
| D2 Calibration drift | gain a0 + a1·d + a2·d², offset b0 (d = wear day), sampled JOINTLY | Vettoretti 2019 (G6) + per-brand bias (Eichenlaub 2025: Libre 3, G7 +7–8%) | 03 | planned |
| D3 Noise | AR(2), φ ≈ (1.30, −0.42) | σ per family — **fit to eda lesson 33 paired-switcher statistics** (step SD, lag-1, flat share, implied noise) | 03; eda L33 | planned |
| D4 Device smoothing | causal smoother on the reported stream (twiist/Libre stream is smoothed: lag-1 0.64 vs G7 0.45) | per family | eda L33 | planned |
| D5 Compression lows | personal rate Gamma(2.37, 75.7)/day, night-weighted; depth median 24, 45 min; branches gap 72% / dip 25% / floor 3% | — | run:2026-10-11-ice-compression/compression_layer.json; 03 (Facchinetti 2016) | planned |
| D6 Availability | warm-up blanking, session length, early failure, Markov gaps | per family | 03; donor gap measurement (planned) | planned |
| D7 Reporting | cadence 5 min (Dexcom) / 1 min (Libre), mg/dL rounding with the mmol round-trip lattice, clamps 39/401 | — | eda L3, L6, L43 | planned |

## E. Pump and infusion site (`device.py`, planned)

| Component | Model form | Parameters | Evidence | Status |
|---|---|---|---|---|
| E1 Pulse delivery | whole 0.05 U pulses; Omnipod truncation | — | ice L25 | handled by LoopEval (delivery) |
| E2 Site life | change every ~72 h (19–120), 17–22 h local; absorption speeds up over days 1–3 | day 4 ≈ 18 min earlier action | eda L52; 03 (Swan 2009) | planned |
| E3 Site change event | routine: +28 mg/dL peak at 0–3 h, baseline by 6 h | — | eda L52 (2,581 changes) | planned |
| E4 Failing site | a quarter of sites; bioavailability decays over 6–12 h before an early change (+9 → +32 mg/dL with delivery flat) | 3.3% of sets end with > 250 for ~5 h (Kanapka 2022) | eda L52; 03 | planned |

## F. Behavior — the person as a second controller (`behavior.py`, planned)

Traits are drawn per person from REAL people (jittered), not Gaussians — rates are bimodal
(evidence/05 lesson 4).

| Component | Model form | Parameters | Evidence | Status |
|---|---|---|---|---|
| F1 Meal schedule | per-person meal slots (time, size, composition), weekday/weekend | ~3.5 eating events/day, ~190 g/day (Camerlingo 2021); donors: 6.2 meal pulses/day, 43% announced | 04; 05 §1b | planned |
| F2 Announcement & carb count | P(entry), count error = person bias + per-meal noise (−10%, 20%); big meals under-counted | 21% per-meal error, 63% under | 04 (Brazeau 2013); 05 (grams vs pulse r 0.2–0.3) | planned |
| F3 Meal bolus | P(bolus\|entry) 0.67–0.76; timing (a third during/after the meal); calculator acceptance 86% (49–100% per person) | — | 04; 05 | planned |
| F4 Corrections | lone manual boluses p10/50/90 0.10/1.07/4.25 per day | — | 05 (ice L62) | planned |
| F5 Low defense | anticipatory, keyed to projected glucose; personal onset/strength/overcorrection; 2nd treatment after ~15 min if not rising | rescue ~32 g (lit) / ~35 g (donors); 73% over-treat | 04; 05 (ice L34, L69, L71) | planned |
| F6 Monitoring & sleep | awake/asleep schedule; alarm response asleep 29–66% (children), unaided waking 1 in 16; app views < 3.3 to > 8.25 /day | — | 04 | planned |
| F7 Exercise habits | sessions, mitigation (temp targets 73%, ≥ 1 h ahead only 27%; pre-exercise carbs) | — | 02; 04 | planned |

## G. Settings — what the person tells Loop (`person.py`)

| Component | Model form | Parameters | Evidence | Status |
|---|---|---|---|---|
| G1 ISF setting vs truth | multiplicative error | settings ÷ yardstick: median 1.15, p10 0.77, p90 1.73 | 05 (ice L28) | planned |
| G2 Basal, CR settings vs truth | multiplicative error | to be measured (scheduled basal vs fasting need) | planned measurement | planned |
| G3 Dosing strategy, device bundle | autobolus ↔ Omnipod + Dexcom; temp basal ↔ twiist + Libre 3 | cohort shares | eda L49 | planned |
| G4 Insulin formulation | brand mix: rapid 52, ultra-rapid 20 of 72 recorded | — | eda L46 | planned |

---

## Validation targets (the primary test)

Computed on simulated CGM with eda's own code (`traits.block_features`, `delivery.py`), split by
sensor family and dosing strategy, against `runs/2026-08-25-distributions/{wholerecord,cohort,delivery}.csv`
and the ice targets in `evidence/05 §2`. A divergence is a missing or wrong component.
