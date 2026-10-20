# Component registry — the additive patient simulator

Every factor the simulator composes: its model form, its parameters, and where each value comes
from. A component is only as good as its evidence column: a literature source (`evidence/0x §n`,
full citations there) or a measurement on BDDP data (a `runs/` path and the script behind it).
**[J]** marks a judgement call waiting for evidence. Those are the first things to replace.

**No mystery terms.** A variability or offset term exists only if its size comes from its own
controlled-condition evidence. Free-living statistics are targets the named factors must reproduce
together (LESSONS 1).

Status: **built** (tested in isolation) · **wired** (runs in the closed loop through LoopEval) ·
**calibrated** (a named parameter set against a donor statistic) · **planned**.

Code: `analysis/loopeval_analysis/patient_sim/`.

---

## A. Physiology (`physiology.py`, `insulins.py`, calibration in `person.py`)

| Component | Model form | Parameters (population prior) | Evidence | Status |
|---|---|---|---|---|
| A1 Glucose kinetics | One compartment, insulin-independent glucose effectiveness SG(G−Gb) | VG lnN(1.88 dL/kg, 0.15); SG lnN(0.0045 /min, 0.5) (LESSONS 349: 0.5–0.7× brings lows on, raises level); Gb N(119, 7) | 01 §1.2, §4.2; UVA/Padova-plant impulse fits 0.0013–0.0047 /min (LESSONS 3) | wired |
| A2 SC insulin PK | Per-dose depot: delay τ → Isc1 →kd→ Isc2 →ka2→ plasma, ke 0.127 | kd lnN(0.030, 0.31), ka2 lnN(0.018, 0.21), VI 0.126 L/kg | 01 §3; ka2 centre refit to the lispro clamp profile (LESSONS 9) | calibrated |
| A3 Insulin formulations | τ, kd/ka2 multipliers, fast-route fraction ψ | lispro/aspart = reference; Fiasp and Lyumjev FITTED to clamp contrasts (Lyumjev AUC0–15 ×7.2, >3 h ×0.60; Fiasp AUC0–30 ×2.0, >3 h ×0.80); glulisine; regular human insulin | 01 §3.2; `insulins.fit_formulations` | calibrated |
| A4 Per-dose absorption jitter | ω per bolus scales kd, ka2, k_fast | lnN CV 15% | 07 (Heise 2017 repeat clamps, net of the SI share) | wired |
| A4b Posture | awake = upright: subcutaneous absorption × (1 − p); asleep supine (the clamp PK's posture) | p per person 0.5 × U(0.19, 0.44): half the sitting-vs-flat-supine contrast [J] (LESSONS 169) | Hildebrandt 1985 (supine → sitting: blood flow −29 to −47%, absorption −19 to −44%, 17 patients); LESSONS 163 | wired, default since 2026-10-18 (`posture`) |
| A5 Insulin action — disposal | X_D (rate p2) on absolute insulin; uptake X_D·M(G)·risk(G) − X_b·Gb; M = Gb + κ(G−Gb) above Gb, ∝ G below | p2 0.025 (lispro clamp fit; 0.04 from LESSONS 324 to 365), p2E 0.006 (post-meal EGP nadir depth 0.54 vs Romeres 2025's 0.56; LESSONS 131); EGP share U(0.7, 0.9) on the linear part (per-person tracer-comparable nadir 0.50 vs Romeres 0.44 ± 0.17; LESSONS 195, Pete 2026-10-18; was U(0.5, 0.7)); pump-site wear speeds absorption (A2/device); κ lnN(0.675, 0.4) (Best 1981 mid-insulin value; was 0.15, LESSONS 165); SI_D calibrated per person so the TOTAL drop per unit on the linear part equals the person's ISF (base since 2026-10-18, LESSONS 143; the earlier peak-probe calibration left action ~2.16× the ISF, LESSONS 140) | clamp: GIR peak ~100 min, 6.3% of a 15 U dose's effect in the first hour (PMC7716902); never fitted to Loop's curve (LESSONS 9, 114; LESSONS 20 superseded); κ (LESSONS 2); low end (LESSONS 7) | calibrated |
| A6 Insulin action — EGP | X_E (rate p2E) on relative insulin; EGP = EGP_b·c(t)·clip(1 − sE·X_E, 0, 1+sE) | EGP_b N(2.5, 0.33) mg/kg/min; p2E 0.010; sE from an EGP share U(0.5, 0.7) of ISF, centred on Romeres 2025's meal EGP nadir (44 ± 17%) (LESSONS 69–75) | 01 §4.1; Hovorka 2004; evidence/13 | wired |
| A7 Renal excretion | Rcl·(G − Rthr) above Rthr | Rthr N(180, 25); Rcl lnN(0.003, 0.3) | 01 §4.3 | wired |
| A8 Hypo risk amplification (S2013) | uptake × [1 + λ·10 r1 (ln G^r2 − ln Gb^r2)²] below Gb | **λ = 0**: at 0.5 it gave t<54 8.5% vs the field's 0.13% | 01 §4.5; ablation runs/a_norisk (LESSONS 10) | calibrated (off) |
| A9 Counter-regulation + HAAF | EGP boost CRmax·h·σ((cr_g − G)/5), τ 15 min; h falls while < 54 (2 h → ×0.6), recovers over 60 h | CRmax lnN(0.195, 0.5) mg/kg/min, refitted to the share of lows reaching 54 on the current body (LESSONS 360; 0.3 in LESSONS 272; LESSONS 166 gave 0.5; was 1.0 [J]); cr_g N(65, 5) | 01 §4.4 (no clamp-calibrated prior exists) | wired |
| A10 Gut — mixed meals | Per-meal parcel Qsto1 → Qsto2 → Qgut; saturating emptying in kcal E = Vmax·S/(Km + S) shared by everything in the stomach; per-meal speed lnN(0, 0.4) | Vmax 3 kcal/min, Km 60 kcal (kempt 0.05), kabs 0.05; f N(0.9, 0.05) | evidence/09 (Brener 1983, Hunt 1985, Calbet 1997, Elleri 2013); donors' lognormal shape (LESSONS 33) | calibrated; between-person Vmax (CV 30%, 28% delayed ×0.6–0.8) wired, default on (`--disable ge_var`; LESSONS 88); fast liquid share 0.2 varies per meal (Beta SD 0.25, Englyst 1999 rapidly available glucose; SD a judgement) and 15% of each meal empties in the Dalla Man slow late phase (kmin 0.008; share a judgement), default on (LESSONS 120) |
| A11 Gut — hypoglycaemic acceleration | kempt × (1 + 1.5·σ((70 − G)/5)) | ×2.5 below ~60 | 01 §6.4 (Schvarcz 1995) | wired |
| A12 Fat / protein | early: kempt × 1/(1 + fat/60); late: slow glucose parcel 0.3·protein g (Elleri 2013 LG meal ~0.49 g per g protein + fat; Paterson 2017 dose-dependent; was 0.1, LESSONS 373), chain 1/60, delay 90 min; fat SI dip 1 − ρ·fat/50 ramping in 0.5→1.5 h (Laxminarayan 2015; was 2→3 h, LESSONS 352), full to 6 h, gone by 10 h | per meal 0.44 g fat and 0.45 g protein per carb gram (snacks 0.2), ±50% (T1D adults, n = 470: fat 75 g, carbohydrate 162 g, protein 70 g/day → 0.46 / 0.43 per carb g; PMC11446970); ρ U(0, 0.35) per person | 01 §6.3 (Smart 2013, Wolpert 2013, Bell 2020, Paterson 2017) | wired; the fat SI term is absolute (Wolpert-sized, ρ U(0.1, 0.6)): with no fixed night bump it carries the evening's night need, varying night to night with the dinner (LESSONS 370; `fat_rel` normalisation off since 2026-10-19) |
| A10b Fast liquid phase | 35% of each meal's carbohydrate empties fast (0.08/min) outside the energy ceiling | share 0.35: 0.5 fits the donors' 5-min CGM step tail but overshoots CV; one share for all meals cannot fit both (a per-meal distribution is next) | Hunt 1985; Calbet 1997; LESSONS 44 (increment skew), 268, 270 | calibrated (0.2 → 0.35 on 2026-10-19) |
| A13 Rescue / fast glucose | fast parcel kempt = kabs ≈ 0.06–0.08, with A11; bioavailability = the person's calibrated meal f × 1.25 (never a fixed 1.0) | — | 01 §6.5 (Brodows 1984: ~3–4 mg/dL per g); LESSONS 18 | wired |
| A14 Circadian gastric emptying | emptying × 1.25 at 06–11 h, × 0.8 at 17–23 h, 1-h ramps (`ge_circ`) | — | Goo 1987 (same solid meal's half-time ~54% longer in the evening); night 00–03 h on the donors', circadian_amp passes (LESSONS 180, 339) | calibrated, default since 2026-10-19 |
| A15 Meal-slot composition | fat / protein per carb gram × 0.72 / 0.97 / 1.14 and 0.86 / 0.86 / 1.24 at breakfast / lunch / dinner (`slot_comp`) | — | Vetrani 2022 Diabetologia Table 1 (1,264 records, 25 adults on HCL); LESSONS 338 | wired, default (measured values since 2026-10-19; were [J] 0.6 / 1.0 / 1.35) |
| A16 Activity and the gut | emptying × up to 1.15 at walking intensity, × 0.5 by 0.8 VO2-reserve, on filtered intensity (`ex_gut`) | depth above 0.6 [J] | Franke 2008 (walking: half-emptying 123 → 107 min); PubMed 22517770 (> 70% VO2max, splanchnic flow ≥ −80%); LESSONS 344 | built, off (neutral) |

**Per-person calibration** (`person.calibrate`): Ib comes from the true basal rate; SI_D and sE are
solved so a 0.1 U probe on the *linear part* (A1 SG, A5 κ and low-end, A8, A9 all off) gives the
true ISF. ISF and CSF are defined on that linear part, the same bookkeeping ISF the eda yardstick
estimates (LESSONS 2).

## B. Time-varying modulators (`modulators.py`)

| Component | Model form | Parameters | Evidence | Status |
|---|---|---|---|---|
| B1 Circadian sensitivity | Visentin 7-class B/L/D profile, switches 04/11/17 h, 1 h ramps, normalised to a daily mean of 1 | class probabilities 0.10/0.05/0.05/0.10/0.20/0.20/0.30; low/high N(0.40, 0.23) at Visentin's **full** swing; no per-day noise (07) | 01 §5.1; LESSONS 38: 24-h amplitude 0.14 vs donors 0.13 | calibrated |
| B1b Basal-need profile | EGP × the donor's quiet-hour DELIVERED insulin shape (mean 1, full weight; `prof_deliv`); without it, the schedule shape^0.5. Loop's exported schedule uses the donor's schedule as is | per donor (templates.add_basal_profile, add_delivered_profile) | donor basal schedules and quiet-hour delivery in local time; LESSONS 48, 214, 250 (quiet daytime delivery / schedule donors 1.07–1.13 vs sim 1.31–1.36) | calibrated (delivered shape default since 2026-10-19; the fixed night bump from the donor's steady nights, `night_own` (LESSONS 251), is off since 2026-10-19: it made night insulin too regular, LESSONS 369–370) |
| B2 Dawn phenomenon | EGP ramp from onset U(02:00, 04:30) to a 07:00 peak, gone by 10:00 | present p 0.52; amplitude lnN(0.3, 0.6) of EGP_b [J] | 02 (Ostrovski 2020); 01 §5.1 | wired for people without a donor basal profile (the profile carries dawn; LESSONS 51) |
| B3 Intrinsic day-level SI | independent per-day lognormal | CV 8% | 07 (repeat clamps 6–15%) | wired |
| B4 Intraday OU / slow drift | — | **off**: no controlled-condition evidence | 07; LESSONS 1 | off |
| B5 Menstrual cycle | SI falls through the late luteal phase to a low at menses onset, holds 2 days, recovers by day 3 (shape "late"); cycle N(28, 3) d, 63% of people respond | amplitude lnN(0.08, 0.5) | 02; BDDP Dexcom G7 cycle logs (493 events, 125 users): glucose ~+2 to +4.7 mg/dL up to onset, ~−3.5 a week after (LESSONS 136); population-wide screens show no rhythm because cycles are unlogged and unaligned | wired, **on by default** (Pete 2026-10-18) |
| B6 Illness | Poisson episodes (3/yr adults, 5/yr children), 1.5–15 d; SI dip 10–35% with ramps, EGP +0–15%; 20% gastrointestinal (SI up 5–15%, intake ×0.7) | — | 02 illness (Mehta 2010; Tinti 2025) | wired |
| B14 Oral glucocorticoids | courses at 0.09/yr per person; 4–7 days, morning dose ~08:00; SI × (1 − loss·w(t)), w 0 to +2 h, ramps to 1 by +6 h, holds to +12 h, gone by +22 h; loss U(0.35, 0.60) on day 1, linear taper | — | 00 D13; Bevier 2008 (insulin +69%, 30–100%, from 6 h; baseline by day 4); Waljee 2017 (21.1% of adults per 3 years); PMC8157052 (afternoon–evening pattern); LESSONS 140 | wired, on at the population rate; `--enable steroid_course` forces one from day 3 |
| X9 Pregnancy (scenario) | SI ÷ need(week): +10% to week 9, 0.95 at 16, +5%/week to 36, falling after 37; settings titrated to the starting week | need shape; early sizes [J] | García-Patterson 2010 (n = 65 T1D); ADA Standards 2023 §15; J Perinatol 2021 (late fall); LESSONS 141 (SI form realizes ~90% of the need) | built, off (`--set preg_week=W`) |
| B11 Hyperglycaemia-induced resistance | SI × (1 − H), H → 0.26·clip((G − 140)/220, 0, 1), τ 12 h [J] | — | Vuorinen-Markkola 1992; Yki-Järvinen 1987 (LESSONS 43) | wired |
| B1c Per-donor circadian pattern | B / L / D SI levels drawn from the donor's posterior (`fit_body --segments`, reliability-shrunk mean + posterior SD), replacing the random Visentin class (`circ_own`) | split-half reliability B 0.53, L 0.08, D 0.37 | donors' true B/D log SD 0.56 vs Visentin-as-simulated 0.59; LESSONS 335 | built, off |
| X12 Thyrotoxicosis (scenario) | plasma insulin clearance ke × `thyro_clear` (1.41), settings kept euthyroid | — | PubMed 3887944 (MCR 1144 vs 812 ml/min); Arch Intern Med 1980 (+25–100% insulin); LESSONS 336 | built, off (scenario) |
| D14 Niacin (scenario) | SI × `niacin_si` (0.37) | — | Kahn 1989 (minimal-model SI ×0.37 at 2 g/day); Blond 2014; LESSONS 354 | built, off (scenario) |
| D34 Damaged insulin (scenario) | delivered bioactivity × `insulin_potency` | — | BMJ DRC 2022 e003105 (−14–18% at 28 d, 32–37 °C); LESSONS 354 | built, off (scenario) |

## C. Exercise (`exercise.py`)

| Component | Model form | Parameters | Evidence | Status |
|---|---|---|---|---|
| C1 Insulin-independent uptake | ex_uptake·gain·Y·G/Gb, Y = intensity through a 7-min lag | ex_uptake lnN(3.0, 0.3) [J] | 02 §1; evidence/10 (Dhaliwal 2025 glucose dependence); BDDP workouts by starting glucose (LESSONS 137) | wired |
| C2 Acute + delayed sensitivity | insulin action ×(1 + 2.0·gain·Y + Z); dZ = 0.134·gain·drive² − Z/600, drive above Y 0.12 (quadratic: walking at the old size, a 45-min moderate session McMahon-sized) | α 2.0 (Romeres 2021); threshold 0.12 (UVA, Deichmann); b 0.134 (McMahon 2007 late phase) | evidence/10 §7.3; LESSONS 34, 57; BDDP HealthKit workouts (LESSONS 243–246) | calibrated (default since 2026-10-19) |
| C3 Absorption during exercise | absorption ×(1 + 0.5 I) [J] | — | 02 §1 | wired |
| C4 Anaerobic EGP surge | EGP + surge × intensity × anaerobic share × ramp((I − 0.6)/0.4) | surge 28 mg/kg/min; threshold 60% of reserve | 02 §1 (Marliss & Vranic 2002); BDDP workouts ≥ 8 METs: rise ≥ 20 during in 46% (LESSONS 243, 247) | calibrated (default since 2026-10-19); session intensity from donors' workout METs (`ex_mets`) |
| C5 Sessions | per-person rate 0–5/week, ~40 min, time-of-day slot, pre-exercise carbs p 0.3 | — | 02 (T1DEXI, an active cohort); 04; **validated** against 18 k BDDP HealthKit workouts under Loop: excess ΔCGM at 45 min sim −12.5 vs donors −17.0, 6 h −6.5 vs −6.2, intervals overlap (LESSONS 137) | wired |
| C6 Everyday activity | episodes lnN(2/day, 0.55) × day gamma(3); duration lnN(18 min, 0.75); intensity (MET − 1)/(METmax − 1) × 0.7; UK Biobank day profile; waking background lnN(0.06, 0.4); per-person gain lnN(0, 0.5); intake covers the expected activity (clamp probe, median ~28 g/day) | METmax lnN(9, 0.25) | evidence/10 (T1DEXI, NHANES, UK Biobank, Compendium); LESSONS 34 | calibrated (lows) |
| C7 Fragmented waking movement | the waking background as alternating sitting lnN(12 min, 1.0) and light bouts lnN(4 min, 0.8) at the intensity that keeps the person's mean; the activity-carbs probe uses the same process | bout sizes [J] | Healy 2008 (breaks in sedentary time); LESSONS 161, 163 | wired, default since 2026-10-18 (`act_frag`) |

Calibration targets for C: T1DEXI's per-session drop by starting glucose and by IOB, and the
delayed-hypo night rate.

## D. Sensor (`sensor.py`)

One parameter set per session; per family (G6, G7, Libre 3, Libre 2, Medtronic).

| Component | Model form | Parameters | Evidence | Status |
|---|---|---|---|---|
| D1 BG→IG + device lag | first-order filter | τ lnN per family: G6 3.78, G7 3.5, Libre 3 1.8, Medtronic 8.4 min | 03 §2.2 (Vettoretti 2019; device studies) | wired |
| D2 Calibration drift | gain a0·(drift over the session, sampled jointly)·day-1 deficit + offset b0 | G7 a0 N(0.98, 0.04), b0 N(3, 3); G6 a0 N(0.96, 0.05), b0 N(2, 3); Libre 3 a0 N(0.965, 0.03), b0 N(0, 2); Libre 2 / Medtronic keep Vettoretti / Biagi values; day-1 deficit N(0.06, 0.05) decaying 12 h | FITTED to FDA iCGM bias/MARD by range and two-sensor PARD (sensor_fit.py; evidence/08; LESSONS 31) | calibrated |
| D3 Noise, sensor-specific | AR(2) on the reporting grid, Student-t df 4, scale √(q² + (1 − q²)(IG/130)²) (floor ⊕ proportional) | α (1.30, −0.42); σ G7 N(1.8, 0.8) (donors' high-frequency CGM noise and FDA K213919, LESSONS 269), G6 N(1.4, 0.8), Libre 3 N(1.5, 0.5); q 0.5 | Vettoretti 2019 shape; size fitted with D2 and D3b | calibrated |
| D3b Noise, common to co-located sensors | AR(3) (1.584, −0.884, 0.180), continuous across sessions (interstitial physiology) | σ G7 2.0, G6 2.5, Libre 3 3.0 | Biagi 2017 (Enlite: common var 3.98 > sensor-specific 2.54); raises YSI error without raising PARD | calibrated |
| D3c Transient biases | per-session rate lnN(median, 0.9) events/day; bias ±lnN(12, 0.4) mg/dL (55% low) appearing within one reading, first-order recovery τ 10 min | G7 8/day, G6 6, Libre 3 4 [J] | donor quiet-window reversals (quiet.jump_signature, reversal_events; LESSONS 32): G7 reversal 6.6 vs donors 6.8 per 1,000 quiet steps | calibrated (G7, G6) |
| D3d Noise-level wander | σ × exp(z − sd²), z log-OU sd 0.7 (G7 0.6), τ 8 h; G7 innovations df 30 | [J size] | Facchinetti 2011; LESSONS 42 (volatility clustering, Hurst, dispersion, jump anatomy) | calibrated |
| D4 Device smoothing | causal EMA on the reported stream | Libre 3 (twiist stream) 0.35 [J] | eda L33 (Libre stream is smoothed) | wired |
| D5 Compression lows | personal rate Gamma(2.37, 1/75.7)/day while asleep; depth lnN(35), 45 min; gap 72% / dip 25% / floor 3% | — | run:2026-10-11-ice-compression; 03 §2.6 (literature rate ~10× higher: the donor detector is strict) | wired |
| D6 Availability | warm-up per session; session length (+ grace); early failure 5% [J]; random gaps at the measured per-family rates by length | G7 4.4 gaps/day, Libre 3 1.5, G6 1.7 (wear ~96%) | runs/2026-10-15-additive-sensor/gaps.py (153 donors) | wired |
| D7 Reporting | 5-min grid, integer mg/dL, clamps 39 / 401 | — | eda L3, L6, L43 | wired |
| D-low Low-range noise scale | noise × √(q² + (1 − q²)(IG/130)²); q G7 0.7, G6 0.8 (was 0.5) | FDA accuracy tables via sensor_fit.score on the current bodies (LESSONS 361) | calibrated |

## E. Pump and infusion site (`device.py`)

LoopEval's trace records what was **commanded**. The body receives what the device **delivered**.
The difference is ground truth the plant logs, and Loop never sees it (phantom IOB).

| Component | Model form | Parameters | Evidence | Status |
|---|---|---|---|---|
| E1 Pulse delivery | whole pulses (Omnipod truncation) | — | handled by LoopEval (ice L25) | — |
| E2 Flow error | per-device bias N(0, 1.5%) + AR(1) τ 45 min, 1-h sd by family × rate^−0.3 | Omnipod 11%, Medtronic/Tandem 4.5%, twiist 3% at 1 U/h | 06 #2 (Freckmann 2019; Ziegler 2021) | wired; matches the bench 1-h sd |
| E3 Bolus error | per bolus sd = c/√U, floor 0.6% | Omnipod c 0.12, durable 0.03 | 06 #3 | wired |
| E4 Start-up transient | deviation after each site change, decays 4 h | Omnipod N(+5%, 5%), Medtronic N(−5%, 5%) | 06 #4 | wired |
| E5 Site life | absorption 0.9 → 1.15 by day 4 | — | 03 (Swan 2009) | wired |
| E5b Set-age efficacy | absorbed fraction × (1 − 0.025·max(0, age − 1 d)) | [I] | Sampson Perrin 2015; Simic 2021 (LESSONS 43) | wired |
| E6 Failing site | absorbed fraction decays to 0.3 (τ 4 h) from a random time; the person changes it after a long high | p 0.012 per site; with E8 and E10 sums to Kanapka 1.9% adults (youth ×3) [J split] | Kanapka 2022 (LESSONS 43) | calibrated |
| E7 Silent partial occlusion | delivered fraction U(0, 0.5) for ~1 h; releases part of the missed volume on clearing | Poisson 0.4 per wear | 06 #8, #10 | wired |
| E8 Full occlusion + alarm | delivery 0; alarm at V_alarm missed units (Omnipod 3, Medtronic 2.5, twiist 0.5) | p 0.003 per wear [J split] | 06 #7; Kanapka 2022 | wired |
| E9 Bubble | missed volume lnN(0.5 U) | p 0.2 per wear [J] | 06 #9 | wired |
| E10 Dislodgement | absorbed fraction 0, never alarms | p 0.004 per wear [J split] | 06 #12; Kanapka 2022 | wired |
| E11 Lipohypertrophy | person trait; LH sites at bioavailability 0.78, per-dose absorption CV 0.5 | prevalence 26% adults (Pickup 2014), 42% children (Heinemann & Krinelke 2012); half of sites [J] | 06 #13 | wired: 26% adults / 42% children, half their sites at bio 0.78, dose CV 0.5 (LESSONS 67) |
| E12 Leakage / backflow | — | no quantitative source | 06 #11 | not modelled |

## F. Behavior — the person as a second controller (`behavior.py`)

Traits come from the person's donor template: the ice pilot's per-person measured behavior (meal
pulses, entries, boluses, corrections, rescues) where present, else literature priors.

| Component | Model form | Source | Status |
|---|---|---|---|
| F1 Meal schedule | 3 main meals (Camerlingo timing; donor's own breakfast/lunch/dinner split and per-window announcement, LESSONS 51; breakfast skipped on the donor's own share of days with no morning pulse ≥ 10 g-eq, median 0.18, the day's grams carried by its other meals — `skip_own`, default since 2026-10-19, LESSONS 182, 368) + snacks at the person's measured pulse rate, placed on their own hour-of-day distribution; weekend shift [J] | ice meals tables; 04 (Camerlingo 2021) | wired |
| F2 Announcement and carb count | P(entry) from the donor's RAW entries/day (2.97 median); person bias N(−0.10, 0.10); per-meal sd lnN(0.2, 0.3); big meals under-counted | raw record (templates.add_raw_rates); Brazeau 2013; LESSONS 35–36 | wired |
| F3 Meal bolus + top-ups | P(bolus \| entry) from raw boluses-with-entry; timing class from the measured lead; calculator acceptance (7.4% up / 6.9% down); top-ups at the donor's raw rate, 20–60 min later if CGM > 120 and not falling [J] | raw record; Groat 2017; Datye 2018 | wired |
| F4 Corrections | at a glance, CGM above the person's measured correction level and not falling | ice corrections tables | wired; rate per glance [J] |
| F5 Low defense | proactive snack when projected glucose < onset, CGM near the low band and not rising; rescue at the person's measured threshold and size; re-check at 15 min, re-treat 34%; 5% of rescues logged | ice L34, L69 (trait and ramp); measured rescue size and glucose; 04 (Savard 2016) | wired; onset and size per person [J] |
| F6 Monitoring and sleep | glances lnN(6/day); alerts; asleep: alarm wakes with p ~0.45, unaided 1/16 | 04 (Puhr 2020; Buckingham 2005; Schultes 2007) | wired |
| F7 Exercise habits | C5 | 02; 04 | wired |
| F8 Site changes | every ~3 days in the evening; early on a long unexplained high or an occlusion alarm | eda L52; 06 | wired |
| F9 Grazing | small unlogged intake below the ice labeler's 12 g-eq gate: lnN(2)/day of lnN(6 g), fast | quiet-window evidence [J rates] | wired; absorbs as liquid sugar outside the energy ceiling (`graze_fast`, default since 2026-10-18; LESSONS 158) |
| F10 Hand-dosed food boluses | an un-entered eating event gets a bolus of the person's own grams estimate ÷ their CR, at the person's measured rate | pilot lone boluses above Loop's recommendation or below 140 mg/dL (templates._free); Groat 2017 | wired |
| F11 Eating pulses | carbs/day spread over the person's measured pulse count (~5.6/day) with their measured size spread | ice meals tables (LESSONS 16) | wired |
| F12 Temporary Overrides | less-insulin with activity episodes, lowered target before entries, raised target at random; donor rates and median factor / target / duration; exported to the therapy timeline (causal) | 19,732 donor windows; templates.add_override_rates; LESSONS 40 | wired (reactive more-insulin class pending plant-sent overrides) |
| F13 Settings edits | dated multiplicative edits to basal/ISF/CR at the donor's rate per setting; size lnN(3.6%, 1.06), random sign [J]; exported as schedule eras | donor therapy timelines (templates.add_edit_rates; LESSONS 41) | wired |
| F14 Per-window entry chance | each window's entry chance ∝ the donor's entered grams there (carbs.json) / the twin's eaten share, mean 1 (`entry_win`, under `entry_split`) | donors' carbs.json by local window (`templates.add_entry_windows`); evening no-entry share 33% → 25% (donors 17%); LESSONS 341, 345 | wired, default since 2026-10-19 |
| F15 Window grams from labelled load | each window's eaten grams = the donor's labelled g-eq ÷ their labelled-per-entered ratio there (`slot_true`), so body-made dawn rises are not eaten again | LESSONS 231, 343, 346 (hourly glucose RMS 9.6 → 7.7 mg/dL) | wired, default since 2026-10-19 |
| F16 Intake per donor load | intake budget × donor / twin labelled load (`intake_own`) | LESSONS 333: Loop absorbs it, level unmoved | built, off |

## G. Truth and settings (`person.py`)

| Component | Form | Evidence | Status |
|---|---|---|---|
| G1 Template | a real donor's row, jittered: eda cohort (156) or ice pilot (168, with behavior) | templates.py | wired |
| G2 True ISF | settings ISF × (yardstick / settings)^0.5 [weight open] | LESSONS 8; eda L53, L54 | wired |
| G3 Body weight | blend of the age prior and TDD at an age-banded U/kg | eda L47 (profile ages can be the account holder's) | wired |
| G4 Insulin balance | true basal = share × TDD/24, share = N(0.5, 0.07) clipped 0.35–0.7 then centred at 0.42 (clip 0.25–0.7); carbs eaten = TDD·(1 − share)·CR_true, covering ALL intake: meals and snacks get the budget less the person's expected grazing and the donor's measured rescue carbs (`budget_all`, base since 2026-10-18; LESSONS 143) | eda L9 (scheduled share 0.43–0.51; pilot median 0.45); centre below the schedule because donors' Loop trims overnight basal (zero delivery 12.5% of night bins; LESSONS 124–125); Pete 2026-10-17; TDD measured | wired |
| G7 Carb sensitivity | CSF = 1.18·[1.85·ISF_tdd·TDD/500]^0.5·[settings ISF/CR]^0.5 (each lnN 0.15); f = CSF·BW·VG/1000 (0.3–1.0) | ice L54 g-eq, re-read through the labeler (LESSONS 27, 33, 37); shrunk toward settings like ISF | calibrated |
| G7b Per-donor meal response | CSF × the donor's labelled g-eq per entered gram over the twin's (shrunk by reliability), intake budget held (`csf_geq`) | ice labeler on donor and twin (template csf_geq_mult); low-runners' twins 1.37 vs donors 0.99; LESSONS 358 | calibrated, default since 2026-10-19 |
| G8 Effective ISF | the person's ISF is the EFFECTIVE drop per unit at ~180 mg/dL on the full body, as the yardstick measures it | LESSONS 15 | calibrated |
| G5 Settings | the donor's own ISF, CR, basal, target and limits | templates | wired |
| G6 Devices | sensor family, pump, dosing strategy, formulation from the donor | sensor_month (Databricks per-reading deviceId) | wired |
| G6b Dosing strategy share | each twin runs autobolus with probability = its donor's share of autobolus days (`auto_day_share`; ≥ 5 automatic boluses, ≥ 20 dose records), own RNG stream | 40 of 50 'autobolus' pilot donors spent days in temp-basal mode; Loop's automated insulin then matches the donors' days 1.04× (LESSONS 331) | wired, default since 2026-10-19 |

---

## Coupling to LoopEval

`loopeval_io.py` writes a synthetic export (30 h of internally-driven history, then the sensor grid) and
runs `simulate --candidate-counterfactual --external-plant … --plant-behavior` as deployed Loop-main
(`--no-mid-absorption-isf --no-gradual-transitions-gate --legacy-rc-decay`). The plant delivers every
dose LoopEval sends from the current minute (a late dose is never dropped, LESSONS 19) and logs what it
received; validation reports delivered/received per person. LoopEval main ≥ f11386e delivers a plant bolus before
deciding the automatic dose and forwards it to the plant (8e86860 alone dropped it) (LESSONS 21); `PLANT_NET_AF=1` restores the ratio − 0.4 workaround for older binaries.

## Validation (the primary test)

`validate.py` computes, with **one code path for simulated people and real donors**, eda's glucose
features (`traits.block_features`), outcomes, delivered-insulin statistics, behavior rates and low
anatomy. For the pilot templates the reference is the pilot donors themselves in 13-day blocks
(`real_pilot.csv`), split by sensor family — scored one block per donor against each twin's one window (`compare_blocks`, `real_pilot_blocks.csv`, median KS p over 40 draws; LESSONS 330); for the eda templates it is the eda cohort tables.
`twin.csv` sets each simulated person against the donor it came from (median difference and rank
agreement). A gap means a missing or mis-specified component. It never means adding a fitted term.
| G9 Loop not acting | offline / merged windows run scheduled basal, pump errors keep the last command; written to the export's disruptions.csv, which LoopEval honours | donors' disruptions.csv: 0.9/day, lnN(32 min, 0.86) ≤ 6 h; errors 2.45/day × 3 min (LESSONS 60) | wired |
| B7–B10 Nightly factors | prior-night sleep loss (−5% SI/h lost, SD 77 min), nocturnal GH variability (CV 0.32 on a 20% dawn increment, mean-zero), evening alcohol (63% drink, 3–20% of nights; −12% SI, morning EGP ×0.85), stress (1/3 react, 40% of days, −10% SI 1–5 h) | Donga 2010; Messman 2022; Edge 1990; Campbell 1985; Kerr; Turner 2001; Riazi 2004; Moberg 1994; evidence/12 (LESSONS 77) | wired |
| B12 GLP-1 RA adjunct | per-person trait (agent, dose escalation, weeks on drug, injection weekday/hour); one-compartment PK → level (1 = maintenance steady-state mean); Emax effects: carbs eaten −25% (sema) / −32% (tirz), gastric emptying ÷(1.42 + 0.25 after a dose step), SI direct +10/+20% and weight-mediated +11% over ~20 wk; settings re-tuned after 11 wk | Pasqua 2025; ADJUST-T1D; TIRTLE1; Ozempic/Mounjaro labels; evidence/16 (LESSONS 87) | built, off (`--enable glp1`, agent `glp1_sema`/`glp1_tirz`/`glp1_lira`); semaglutide matches ADJUST-T1D dose split untuned; within-week rhythm derived from PK, unmeasured |
| B13 Entered absorption time | per entry: 0.5 h / 5 h / 3 h from the person's own shares, split ≤ 20 g vs larger | donor carbs.json absorptionTime (67,499 entries); rescues excluded | LESSONS 101–102 | wired (template columns abs_fast_s/l, abs_slow_s/l) |

## Physiology review against the goal (2026-10-19)

The goal sets the depth: beyond Loop's own effect model and Tidepool's SimpleMetabolismModel, short of maximal fidelity.

**Depth against the two reference models.** Loop's model and the Tidepool simulator act on glucose through two linear
effects — insulin by ISF along a fixed activity curve, carbohydrate by CSF along a fixed absorption curve. The additive
body replaces each with named mechanisms:

| Area | Loop / SimpleMetabolismModel | Additive body | Evidence |
|---|---|---|---|
| Insulin PK | one fixed activity curve per preset | per-dose depot chain (A2) with formulation-specific delay and fast route (A3), per-dose jitter (A4), posture (A4b), per donor formulation from Loop's IOB (LESSONS 248) | lispro / Fiasp / Lyumjev clamps (LESSONS 9), Heise 2017, Hildebrandt 1985 |
| Insulin action | ISF × activity | separate disposal (A5) and EGP suppression (A6) arms, saturating hepatic signal, glucose effectiveness (A1), renal loss (A7) | clamp fits, Romeres 2025 tracer EGP share, post-meal EGP nadir (LESSONS 193–196) |
| Lows | none | counter-regulation with HAAF (A9), gut acceleration in hypoglycaemia (A11), rescue glucose (A13) | donor low nadirs and durations (LESSONS 166), Schvarcz 1995, Brodows 1984 |
| Carbohydrate | CSF × absorption curve | stomach-gut chain with an energy-limited emptying ceiling (A10), fast liquid share (A10b), fat-slowed emptying and late protein parcel (A12), per-meal speed | Brener 1983, Hunt 1985, Calbet 1997, Bell 2020; donor labeled arrival shape (LESSONS 228) |
| Time-varying need | schedule only | circadian SI classes (B1), basal need from the donor's delivered shape and night level (B1b, LESSONS 250–252), dawn, GH, sleep, alcohol, stress, illness, cycle, glucocorticoids, hyperglycaemic resistance (B2–B14) | Visentin 2015, BDDP life-factor logs (LESSONS 136, 235), donor steady nights |
| Exercise | none | intensity filter, insulin-independent uptake, acute and delayed sensitivity, absorption, intensity-gated EGP surge (C1–C5) | Romeres 2021, McMahon 2007, Marliss & Vranic 2002; BDDP HealthKit workouts (LESSONS 243–247) |

Not built, by the goal's depth limit: separate liver glycogen stores, glucagon kinetics (counter-regulation is an EGP
boost, not a hormone), insulin degradation by site, ketones, multi-compartment glucose beyond one pool.

**Checks against the donors that the physiology passes** (reference c270 unless noted): meal arrival per entered gram
and its spread (LESSONS 228), insulin around meals (LESSONS 238/240), correction response time course at 60–180 min
(LESSONS 236), low nadirs and durations, overnight glucose profile and need (LESSONS 251–253), quiet-period motion away
from meals (LESSONS 241), exercise response by intensity (LESSONS 247), night-to-night insulin variability against
Ruan 2016 (LESSONS 241), illness and cycle sizes (LESSONS 235).

**Where physiology is still the suspect.** (1) Fast falls: falling readings > 3 mg/dL/min 0.49% vs donors 1.26%, the body
not the sensor (LESSONS 236), with glucose effectiveness, meal speed, early insulin action, carb sensitivity,
formulation, counter-regulation and absorption variability ruled out (LESSONS 238–239, 248, 257); in the donors these
falls come after unentered rises at below-usual IOB (LESSONS 249), so a mechanism that lowers need after a rise without
an insulin excess is missing. (2) Person-level level: twins do not inherit their donor's mean (Spearman 0.25), and
nothing measured in the body (ISF mismatch, night need) orders donors by level (LESSONS 233, 256). (3) The cycle's
post-onset low arrives earlier than the donors' (LESSONS 235): a follicular sensitivity term would need its own evidence.
