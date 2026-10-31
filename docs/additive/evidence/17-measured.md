# Measured evidence — the donor-data basis of each component

This file holds the measurements on BDDP / donor data (and the cohort runs and fits on them) that set each component's
current parameters. Literature evidence is in `evidence/00`–`16`. "L N" cites `docs/additive/archive/LESSONS-001-547.md`
(full text, numbering unchanged). Scripts and run dirs live under `~/.loop-eval/runs` (`runs/` in the repo); a cohort
name (c135, lg12, sd3) is a run under the matching dated run dir. Values are the code defaults; where the reference run
**sd3** sets a component differently, the entry says so. A number in parentheses after a simulated value is the donors'.

---

## A. Physiology

- **A1 Glucose kinetics.** SG lnN(0.0045 /min, 0.5), inside UVA/Padova's 0.0013–0.0047 (Pete 2026-10-16: calibratable against slow structure
  in that range); VG lnN(1.88, 0.15); Gb N(119, 7) clipped 95–150. SG ×1.5 on the old 0.003 centre (c232) put the mean on
  the donors' (151.7 vs 151.4), CV 33.2 (34.8), breakfast tail +30 / 26 / 21 at 3–4 h (+27 / 22 / 16), lows 0.58 → 0.42 /
  day (L 208). Lower SG brings lows on but raises the level: `sg_mult` 0.7 / 0.5 (c349) t54 0.123 / 0.190% (0.190), but
  mean 160.9 / 163.9 and TIR 69.2 / 67.0 fail (L 349, 356). Gb stays drawn: `gb_own` (donor median quiet CGM 00–06 h,
  p25 / 50 / 75 109 / 121 / 136) tracked the level better (slope 0.44 → 0.68) but cost the score (0.371 → 0.398 / 0.413
  → 0.455); off, the level is carried by `resid_m` (L 504).
- **A2 Subcutaneous insulin PK.** kd lnN(0.030, 0.31), ka2 lnN(0.018, 0.21) (half the ReplayBG log-SD). ka2 centre from a
  grid refit of the ReplayBG prior chain (which gave 47% of a bolus's effect by 3 h) to the lispro clamp (GIR peak
  ~100 min, 50% by ~140, 90% by ~270); plasma tmax 51 min (literature 40–60) (L 9). Body probe at rest (0.2 U/kg): peak
  100 min lispro, 79 Fiasp, 98 Lyumjev; share of the drop by 60 min 0.29 / 0.41 / 0.35 (`ins_course.py`; L 201).
- **A4 Per-dose absorption jitter.** CV 15% (Heise 2017 net of SI). Wider does not help: `dose_cv` 0.3 (c233) within-person
  0–2 h drop SD 30.0 → 29.0 (36.7); 0.35 (c274) fast falls 0.49% (1.26), lows 0.92 → 0.83 / day (L 209, 257).
- **A4d Dose-dependent bolus absorption.** β 0.1 (Heise 2017). c440_db on c439_pr4: lows 1.00 / day (1.00), t54 0.223%
  (0.190), mean 155.6, 3-h meal change +16.9 (+21) (L 433, 437).
- **A4c Absorption-rate fluctuation.** `flow_sd` 0.5, τ 60 min [J] (code default); **sd3 sets 0.0**. On c417_st, 0.3 / 0.5:
  t54 0.123 / 0.175% (0.190), lows 0.83 / 0.92 (1.00), 3-h meal change +15.5 / +17.4 (c418_f5; L 417, 419). Added back
  to f4 after a level refit: score 0.402 / 0.477 vs f4 0.379 / 0.440 (L 517, 522).
- **A4b Posture.** p = 0.5 × U(0.19, 0.44) (`posture_mult` 0.5, Hildebrandt 1985 range). Half vs full (c187) vs off (c193):
  night share of lows 46 / 53 / 40% (22), 00–03 h median 140.5 / 134 / 146 (152), 37 matched for half (best) (L 163,
  169). Ablation c297: lows 0.67 vs 0.83 on (1.08), paired hypo-day OR 0.78; posture does not carry the fall-timing gap;
  kept (L 291).
- **A5 Insulin action — disposal.** p2 0.025 /min; κ lnN(1.0, 0.4); SI_D calibrated so the TOTAL linear-part drop per
  unit equals the ISF (`isf_total`).
  - p2: the lispro clamp fit (L 9). 15 U Humalog clamp (PMC7716902): 6.3% of the infused glucose in the first hour; body
    first-hour share p2 0.05 / 0.03 / 0.02 ~14 / 12 / 10% (Loop 22%). Field lone corrections cannot separate p2 0.02–0.05
    (`corr_ice.py`; L 113, 114). c365 `ins_p2` 0.025 / 0.03: 37 / 34 of 51, t54 0.128 / 0.117%, P(reach 54) 0.193 /
    0.167; mean 154.1, CV 34.2, TIR 71.7 pass (L 365).
  - κ: Best 1981 full text, insulin clamped at 1 / 18 / 46 µU/mL, insulin-mediated Rd ×2.52 / ×2.43 for glucose ×2.17 /
    ×2.31 → κ ≈ 1.3 / 1.1; c305 TIR 71.5 (71.7), CV 35.2. Lower κ (c350) meal rise p50 51 / 45 (58), mean fails (L 303, 350).
  - Total drop: under the old peak calibration the linear-part drop per unit was a median 2.16× the ISF (L 140, 143).
    Lone corrections 150–250 mg/dL, change per U per ISF at 60 / 90 / 120 / 180 min: donors −0.032 / −0.215 / −0.35 /
    −0.63, matched by the twins (`corr_fall_multi.py`; L 294). No dose saturation: 3 U ÷ 0.5 U per-unit drop 0.99 (L 276).
  - Superseded: p2 0.025 (L 9) → 0.04 (L 324) → 0.025 (L 365); κ 0.675 (L 165) → 1.0 (L 303).
- **A6 Insulin action — EGP.** EGP_b N(2.5, 0.33); p2E 0.012; saturating hepatic signal (`egp_sat`, v_eff = 2.57·v /
  (2.57 + v)) with offset rate 0.015; EGP share U(0.7, 0.9).
  - p2E: clamp replay on calibrated bodies, GIR peak at p2E 0.008 / 0.010 / 0.012 / 0.015: 120 / 116 / 109 / 101 min,
    first-hour share 7.1 / 7.5 / 7.9 / 8.4% (target ~100 min, ~6.3%) (L 197).
  - `egp_sat`: half / full suppression at v 0.62 / 1.64 from Rizza, Mandarino & Gerich 1981; offset from Gray 1982's R50s
    (0.012–0.020). On c219: low duration p90 66 (65), CV 34.8 (34.8), rise after a night Loop cut 22% (30%) (L 192, 193,
    196). Off on both draws: CV, zero_frac and minutes per low fail (L 478–482).
  - Share: per-person meal EGP nadir suppression (`egp_romeres2.py`) at U(0.5, 0.7) 0.34, 0.8 0.50, 0.9 0.61 vs Romeres
    2025 0.44 ± 0.17 at 160 ± 110 min; U(0.7, 0.9) gives 0.50 (median 0.45) (c218), with `egp_sat` 0.45 (c219) (L 195,
    196). Suppression still fades early; on the later references the meal EGP nadir is 0.83–0.84 of pre-meal at 250 min
    vs Romeres 0.56 at 160, held for the meal shape (L 478–482, 502).
  - No glucagon term: paradoxical glucagon at its evidenced size is ~0–10 mg/dL (Hinshaw 2016) (L 69–71).
  - Superseded: p2E 0.010 (L 70–75) → 0.006 (L 131, nadir depth) → 0.012 (L 197, clamp timing).
- **A7 Renal excretion.** Rcl lnN(0.003, 0.3) (Hovorka). The UVA/Padova value (`rcl_mult` 0.167) left the 3-h fall from a
  quiet midnight > 200 mg/dL at −94 vs −91 (donors −65); default kept (L 93).
- **A8 Hypo risk amplification.** λ 0. Ablations on 42 people (runs/a_*): removing the term took t<54 8.5% → 0.27% (field
  0.13%), t<70 15.5 → 2.5 (1.4), TIR 48.8 → 64.9 (67), rescue carbs 166 → 55 g / day (L 10).
- **A9 Counter-regulation + HAAF.** CRmax lnN(0.137, 0.5) mg/kg/min, cr_g N(65, 5). Refitted on the FDA-held sensor
  (c395_joint): `cr_mult` 0.7 / 0.5 t54 0.092 / 0.089% (0.190), P(reach 54) 0.167 / 0.187 (0.212), share of lows < 54
  0.338 / 0.335 (0.370), nadir p10 43 / 42 (40); adopted 0.7 (0.195 × 0.7); depth moves little with CRmax (c396_cr7;
  L 383, 394). Superseded: 1.0 [J] → 0.5 (L 166) → 0.3 (L 272) → 0.195 (L 360) → 0.137 (L 394); the earlier fits read
  lows through a sensor that made false lows.
- **A10 Gut — mixed meals.** Vmax 3 kcal/min, Km 60 kcal (kempt 0.05), kabs 0.05, f N(0.9, 0.05); per-meal speed
  lnN(0, 0.4); between-person Vmax CV 30%, 28% delayed ×0.6–0.8 (`ge_var`); slow late phase 15% at kmin 0.008.
  - Ceiling: fixed first-order emptying gave glucose skew 1.41, Box-Cox −0.25, 0.38% of time ≥ 400 (donors 0.89, −0.03,
    0.05%); Vmax 3 / Km 60 gave 0.93, −0.08; Vmax 6 1.13; Vmax 4 CV 37.8 (L 33, 53, 76). The ceiling sets the rise
    (`main_speed` 1.4 leaves onset-to-peak unchanged, L 512).
  - `ge_var` (Pete 2026-10-16): c100 vs c99_base 26 vs 21 of 51, CV 35.2 vs 37.2 (34.8) (L 88). Ablation c293: matched-
    height fall after the max −33.0 / −30.0 without, −26.0 / −27.0 with (−36.9 / −33.5), lows 0.67 vs 0.83 (1.08); kept
    as evidenced and carrying lows (`pulse_tail.py`; L 286).
  - Per-meal speed 0.4: Elleri 2013 high- vs low-GL t50 100 vs 175 min, log ratio 0.56 (L 200).
  - Slow phase 0.15 [J share]: c129 vs c124 31 vs 27 matched, glucose skew 0.85 (0.89), labelled g-eq per entered gram
    1.22 (1.21); 0.30 reads meals small (1.08) (L 120, 139); `meal_slow` 0.30 / 0.45 flatten meals and fail lows (L 364).
  - Appearance: twins' isolated entered meals 25 / 50 / 75% at 56 / 100 / 144 min (`ra_traj.py`; L 287), on Elleri 2013
    high-GL 56 / 100 / 153 as evidence/09 lists it (L 130's lesson text gives 72 / 130 / 197; unresolved).
- **A12 Fat / protein.**
  - Fat SI dip ρ U(0.1, 0.6): Wolpert 2013 +42% insulin (mean) after a 60 g-fat dinner; U(0, 0.35) gave the median person
    ~21%, U(0.1, 0.6) reproduces the mean; c50 time > 180 27.4% (27.3%) (L 46, 53).
  - Onset `fat_on` 0.5 h: c352 onset 1.0 / 0.5 dinner +2 to +10 through 2.5–4.5 h, lows 0.67 / 0.79, P(reach 54) 0.143 /
    0.167; 0.5 kept for the lows (L 352).
  - `macro_own` + `fat_rel`: energy 30 kcal/kg, carbs clipped 15–65%, rest 69 / 31% fat / protein (PMC11446970, 470 T1D
    adults: fat 75, carbohydrate 162, protein 70 g / day). c436_mofr: mean 156.7 (151.9), 03–06 h 140 / 133 / 129 / 128
    (141 / 136 / 130 / 127), circadian_amp 0.136 (0.128), t54 0.181% (0.190); absolute fat (c433_mo) mean 164.5, TIR
    62.1 (L 129, 151, 432, 434).
  - `pro_glc` 0.3 g / g (Elleri 2013 LG meal ~0.49 g per g protein + fat): c374 0.3 / 0.45 36 / 35 of 51, night_cv 34.2 /
    35.8 pass, 00–06 h error −5.3 / −1.8 (c371 −11.0); 0.4 raised the mean (L 366, 373).
  - `night_own` off: the evening's own fat carries the night need; with it off (c370) day / night 1.97, night_cv 34.5
    pass (L 369, 370).
- **A12b Post-meal insulin action.** `ppr_a` 0.4, relative (`ppr_rel`). No tracer study sizes it; sized on the donors'
  post-meal counteraction (ICE 60–120 / 120–180 min 124 / 104; L 321). Absolute 0.2 / 0.3 (c403_cl105): 3-h meal change
  +17.6 / +17.2 (+6.7 without; donors +21), lows 0.71 / 0.58 (Pete: meal shape over lows, L 407–408). `ppr_rel` 0.3 /
  0.4: mean 154.7 / 155.7 (151.9), 3-h change +14.2 / +17.9, lows 1.00 / 1.13 (1.00); 0.4 adopted (c439_pr4); 0.5
  rejected on two draws (L 435, 436, 444).
- **A10b Fast liquid phase.** Share 0.35 at 0.08 /min, per-meal Beta SD 0.40; 12% of main meals carry a sugary drink
  (`meal_drink_p`, BRFSS / survey rates, L 209). Donors' daytime G7 5-min steps |step| > 10 / 15 / 20: 15.3 / 6.3 / 2.5%
  (`step_tail.py`). Share 0.5 fits that tail but CV 37.0 (34.8) and hurst_long fail; 0.35 balances (CV 35.2). SD 0.25 →
  0.40 (c285): G7 v_kurtosis 1.90 → 2.48 (2.52) (L 268, 270, 271). Superseded: share 0.2 (L 44) → 0.35 (L 268–270).
- **A13 Rescue / fast glucose.** Bioavailability = meal f × 1.25. At f 1.0 on a 50-kg body 1 g of rescue glucose raised
  13 mg/dL vs 3.95 per meal gram and Brodows 1984's 3–4 (L 18).
- **A14 Circadian gastric emptying.** ×1.25 at 06–11 h, ×0.8 at 17–23 h (Goo 1987 ratio). c339: 00–03 h 157 / 146 / 141 /
  132 (158 / 152 / 147 / 141; off 151 / 132 / 127 / 127); circadian_amp p 0.17 (was 0.002); 38 of 51 (L 180, 339).
  Morning at 1.0 (c351, c375) puts dinner peaks at 4–5 h (+19 / +25 / +21 vs +10 / +6 / +1) (L 351, 375).
- **A15 Meal-slot composition.** Vetrani 2022 values. Neutral on the data: c338 meal shapes unchanged; removing it
  (c432_nosc) changes no slot shape (L 338, 431).
- **A11, A16.** Literature only (A11); `ex_gut` off, neutral (c345, 3-h meal change +0.2; L 344).

## B. Time-varying modulators

- **B1 Circadian sensitivity.** Code: seven Visentin classes drawn **equally likely**, low / high N(0.40, 0.23) at the
  **full** swing (`circ_swing` 1.0), breakfast level from **07:00** (`SEGMENTS` 07 / 11 / 17 h).
  - Full swing (c32circ): 24-h amplitude 0.14 (0.13) (L 38). Segment body fit (168 donors): B / D p50 0.93, no
    population pattern; true between-person SD of log(B/D) 0.56 vs Visentin as simulated 0.59 (L 334, 335).
  - Equal classes: 09 h glucose 143–145 (141) vs 153–157 with Visentin's mix (c61, c68; Hinshaw 2013) (L 52, 59).
  - 07:00 switch: with 04:00, quiet mornings rose +11 mg/dL 03 → 07 h on 1.25× insulin vs donors −7 on 0.92; c60 06 h
    130.5 (130.3), amplitude 0.136 (0.131) (L 51).
- **B1b Basal-need shape.** EGP × the donor's quiet-hour delivered-insulin shape, mean 1, full weight (`prof_deliv`).
  Quiet daytime delivered / scheduled p50 donors 1.13 (automatic) / 1.07 (temp); a schedule-shaped body 1.36 / 1.31;
  c266 vs c264: 31 vs 29 matched, day / night 1.95 → 2.08 (2.06) (`quiet_deliv.py`, `templates.add_delivered_profile`;
  L 250, 282). Hourly RMS on c371: delivered 8.8 vs schedule^0.5 7.5 (lows fail) vs flat 6.1 (t54 fails) (L 371). The
  profile carries dawn: c58 dawn off −5.6 mg/dL (L 51).
- **B2 Dawn phenomenon.** Literature; inert in templated cohorts (`--disable dawn` reproduces the base; L 207).
- **B3 Intrinsic day-level SI.** CV 8%, independent per day (repeat clamps); **off in sd3**. Like for like, day-to-day SD
  of the mean quiet-hour residual donors 8.4 mg/dL/h, twins 7.76; within-person true SI CV from all named factors 10%
  (`sim_daydrift.py`, `don_daydrift.py`; L 220). `day_rho` 0.4: ac1 0.006 / 0.024 (0.091), not adopted (L 457).
- **B4 Intraday OU.** Off. Night-to-night CV of 00–06 insulin / TDD twins 0.33 / 0.16, donors 0.40 / 0.17, Ruan 2016 0.31
  / 0.17 (`night_cv.py`; L 241).
- **B5 Menstrual cycle.** Shape "late", 63% respond, amplitude lnN(0.08, 0.5); on by default, **off in sd3**. BDDP
  "cycle" logs (493 events, 125 users), CGM vs the event's ±30-day mean (mean / median): −1 d +4.0 / +2.3; 0 d +4.7 /
  +3.4; +1..+2 −0.9 / −2.5; +7..+10 −3.3 to −3.6 / −5 (L 136). c256 responders +1.8 / +3.4 / −0.3 at −1 / 0 / +1..+2
  (`cycle_prof.py`; L 235).
- **B6 Illness.** Literature sizes; **off in sd3**. BDDP "illness" logs (994 events, 206 users): 24-h CGM median +3.1,
  mean +6.6; sim c145 +4.4 / +6.2 (L 136). Audit c254: 4.2 / person-year, duration p50 3.4 d, GI 28%, SI drop p50 20%
  (`audit_ill.py`; L 235).
- **B14 Oral glucocorticoids.** **Off in sd3.** Scenario c156_ster: day 3 Δmean +20.6, 14–22 h +47.6 (L 140).
- **X9 / X12 / D14 / D34 scenarios.** Pregnancy's SI form realizes ~90% of the need (L 141). Paired 48 × 10 d:
  `thyro_clear` 1.41 TDD ×1.11, mean +18.6; `niacin_si` 0.37 TDD ×1.27, mean +43; potency 0.85 TDD ×1.07, mean +10
  (L 336, 354).
- **B11 Hyperglycaemia-induced resistance.** H → 0.26·clip((G − 140)/220), builds τ 360 min, fades τ 1440 min (world.py).
  c92 vs c90 Hurst 0.153 → 0.190; off (c72) between-day 0.122 (0.102) but TIR, mean and time > 180 fail, so it stays
  (L 43, 62, 80, 81). `--disable glucotox` (c173) hurst_long 0.379 → 0.353 (0.247) (L 153).
- **B1c Per-donor circadian SI (`circ_own`, off).** Split-half reliability B 0.53, L 0.08, D 0.37; c336 34 of 51 (L 335).
- **B7–B10 Nightly factors.** Literature sizes; stress SI −18% over 1–6 h (Moberg 1994); **stress off in sd3**. BDDP
  `reportedState`: alcohol median −4.7 (95% CI −10.4..+0.9; 176 events), stress +1.8 (−0.7..+4.1; 445 events); sim c154
  alcohol −1.2, stress −1.0 (`sim_states.py`; L 136, 138). With all on (c89) quiet-night insulin CV 15.6% (30.3%) (L 77).
- **B12 GLP-1 RA (off).** Untuned semaglutide 26 wk: TDD −18.6%, bolus −25%, basal −16%, carbs −20.5% vs ADJUST-T1D −20
  to −23 / −30 / −12 to −16 / −22% (gamepc `~/additive/glp1_an.py`; L 87).
- **B13 Entered absorption time.** Per donor shares of 0.5 h and 5 h entries, split ≤ 20 g vs larger
  (`templates.add_absorption_rates`). 67,499 entries, 152 donors: 0.5 h 14%, 3 h 75%, 5 h 5%; per donor 0.5 h share
  median 2%, p90 40%; cohort-neutral (L 101, 102, 392).
- **`sleep_util` (world.py, no registry ID; on).** δ U(0.05, 0.12) (Van Cauter size). c239 night unentered rises 0.57 →
  0.61 (0.67), low duration p90 70 → 65 (65) (L 214).
- **No weekly or post-hypo term.** Donors' TDD by weekday 0.993–1.007 of the mean (L 56, 73); 2–4 h after a low the sim
  rebounds as the donors (+68 to +70 vs +65 to +73) (L 55).

## C. Exercise

- **C1 Insulin-independent uptake.** lnN(3.0, 0.3) [J]. ×3 gave −12.4 above 180 but as large at low IOB; not adopted (L 494).
- **C2 Acute + delayed sensitivity.** α 2.0, saturating `ex_sat` k 0.1, delayed threshold 0.12, b 0.134, `z_power` 2.
  Pemberton 2025's matched-window design on the donors' deduplicated HealthKit workouts (21 donors): start > 180 −19.7
  [−27, −13], IOB ≥ 3 U −20.0, IOB < 1 U −1.9, vs twins under the linear form −6.5 / −5.0 / +4.6; donors by METs < 4 /
  4–6 / ≥ 6 −7 / −13 / −9 (no intensity dependence). Adopted on both draws: lows 0.79 → 0.88 / 0.83 → 1.00 (1.00), t54
  0.148 → 0.197 / 0.149 → 0.176% (0.190), score 0.442 → 0.403 / 0.440 → 0.427; α 3 lies outside Romeres' 1.35–2.6
  (`lifestats.py`; runs/2026-10-23-additive-activity; L 494, 495). Delayed part: post-exercise nights 0.47 vs 0.29 lows
  per night (×1.6, DirecNet 2005 ×1.7) (L 34, 57, 458).
- **C4 Anaerobic EGP surge.** 28 mg/kg/min above 0.6 of reserve. BDDP HealthKit workouts with CGM (884, 37 donors;
  `workout_mets.py`): ≥ 8 METs rise ≥ 20 during in 46%, < 4 METs 16%; surge 20 / 40 gave 35 / 61%, 28 gave 49% (c264)
  (L 243, 247). Thresholds 0.75–0.8 did not improve the score (L 497).
- **C5 Sessions.** Intensity from donors' METs (`ex_mets`): person lnN(1.657, 0.357), session ± N(0, 1.5); 24,498
  workouts, per-donor median METs p10 / 50 / 90 3.4 / 5.1 / 8.6, within-donor SD 1.5 (L 247). Validated on 18 k workouts
  (76 users): excess ΔCGM vs same-person clock-time controls at 15 / 30 / 45 / 60 / 90 / 120 min donors −8.3 / −15.4 /
  −17.0 / −14.5 / −7.6 / −2.7, sim c154 −8.6 / −7.9 / −12.5 / −10.7 / −5.4 / −4.3, intervals overlap
  (runs/2026-10-18-additive-workouts, `sim_workout.py`; L 135, 137).
- **C6 Everyday activity.** lnN(2 / day, 0.55) × lnN(18 min, 0.75), METmax lnN(9, 0.25), gain lnN(0, 0.5); intake covers
  the expected activity (clamp probe median ~28 g / day). Motivated by donors' daytime no-bolus lows 0.19 vs sim 0.09 /
  day; c28 lows 1.10 (1.08), TDD 37.4 (37.0), TDD CV 17.6 (17.0) (L 34).
- **C7 Fragmented waking movement.** Sitting lnN(12, 1.0) / light lnN(4, 0.8) min [J]; on by default, **off in sd3**. With
  posture (c181 vs c177): t70 0.81 → 1.59 (1.67), lows 0.67 → 1.00 (1.08) (L 161, 163). Added back to f4: score 0.379 →
  0.352 but lows 1.08, t54 0.29 (L 517).
- **C3.** Literature [J].

## D. Sensor

- **D1 BG → IG lag.** τ G6 3.78, G7 3.5, Libre 3 1.8, Medtronic 8.4 min; G7 τ × 1.5 while falling. G7 MARD by true rate of
  change (`roc.py`) vs Garg 2022 Table 5 at < −2 / −2..−1 / −1..0 mg/dL/min: Garg 9.3 / 8.4 / 8.1, before 8.1 / 7.9 / 8.2,
  after 9.4 / 8.6 / 8.4 (c391_flag; L 391).
- **D2 Calibration drift.** G7 a0 N(0.98, 0.04), b0 N(3, 3); G6 a0 N(0.96, 0.05), b0 N(2, 3); Libre 3 N(0.965, 0.03),
  N(0, 2). G7 fit to K213919 (`sensor_fit.py`, two simulated sensors): bias 3.8 / 2.7 / 1.2 / −1.5 / −6.8 and MARD 13.7 /
  10.9 / 7.9 / 6.9 / 6.8 from < 54 to > 250, PARD 8.9, MAD elasticity 0.66 (FDA 0.69) (L 31). G6 a0 0.96 kept: 0.98 pushed
  181+ bias the wrong way (loss 10.99 vs 9.88) (L 213).
- **D3 Noise, sensor-specific.** AR(2) (1.30, −0.42); Student-t df G7 30 / G6 4 / Libre 3 4; σ G7 N(1.3, 0.8), G6
  N(1.0, 0.8), Libre 3 N(1.5, 0.5); q G7 0.55, G6 0.6, Libre 3 0.5.
  - G7 σ and q: the donor-fitted G7 (c391) read CGM < 54 at bias −23.5 / MARD 27.9% (K213919 −9.3 / 16.0), G6 −16.4 /
    19.8 (DEN170088 −6.9 / 13.8): false lows. Refit G7 q 0.7 → 0.55, σ 1.8 → 1.3: loss 2.3–3.8, PARD 8.8–9.0, CGM < 54
    bias ≈ −5; G6 q 0.8 → 0.6 (c395_joint; L 393).
  - G6 σ: the FDA tables do not identify it (loss falls to σ 0); set from the donors' sigma_meas: c362 p 0.010 → 0.662
    (1.56 vs 1.24) (L 362). G7 df not identified by the tables (loss 3.40 / 5.51 / 3.49 / 5.52 at df 30 / 8 / 4 / 3;
    L 363); df 4 double-counted tails once wander and transients were in (L 42).
  - Fast noise keeps an additive floor: CGM second differences grow 4.2 → 7.9 from 90 to 350 mg/dL in sim and donors
    (proportional noise ~16) (L 29, 30).
- **D3b Common (co-located) noise.** AR(3) (Biagi 2017), σ G7 2.2, G6 2.5, Libre 3 3.0. G7 2.8 → 2.2 in the L 393 refit.
  Paired-sensor check (p03, two CGMs, `pair_moves.py`): increment r 0.60, 15.8 shared fast moves / day; simulated G7 pairs
  r 0.65, 16.0 (L 296, 299).
- **D3c Transient biases.** Rates G7 6.5, G6 7.5, Libre 3 4 per day (session lnN SD 0.9); amplitude lnN(8, 0.4) G7 / G6,
  lnN(12, 0.4) Libre 3; τ 10 min; low first G7 62%, G6 72%, Libre 3 55%. Donor quiet-window reversals
  (`quiet.reversal_events`): G6 768, 65% low first, 5.6 per 1,000 steps; G7 6,455, 55%, 6.9 per 1,000 (c390_trev;
  L 390). Reversals ~15 mg/dL at every glucose, back in 2–3 readings, day and night alike (L 32). Amplitude 8 (was 12)
  from the FDA tables: G7 loss 3.97, CGM < 54 bias −9.1 (−9.3) (L 211, 213).
- **D3d Wander, slow bias, early noise.** Wander sd G7 0.45 / G6 0.7 / Libre 3 0.7, τ 2 / 2 / 8 h; slow bias sd 5 / 3 / 5,
  τ 180 min; early noise G7 c 1.35 τ 900 min, G6 c 1.0 τ 330 min.
  - Wander fitted on the donors' 5-min steps (`sensor_eda.py`): G6 0.2 / 480 → 0.7 / 120 min, 9 of 10 short-scale
    statistics, FDA loss 11.4 → 7.1 (L 384); kept 0.7 in the FDA refit (loss ≈ 9.7 vs 6.0 at 0.4; the donors' G6 step
    shape needs it); G7 0.5 → 0.45 (L 393).
  - Slow bias (Breton & Kovatchev 2008 form): G7 sd 5 loss 10.89 → 7.86; Libre 3 20.23 → 14.73; G6 sd 3 12.25 → 11.49
    (L 211, 213).
  - Early noise: G7 from Garg 2022 Table 2 (MARD day 1 11.9 / 12.9%, day 2 8.4 / 8.6%). Donors' G7 low onsets per CGM-day
    by session day 1..10 1.39 … 0.91 with median CGM flat; c244 twins +25% on day 1 (donors +33%) (`sess_lows.py`). G6
    from G6 Pro MARD 13.6 / 10.5 / 10.1% (DEN170088 loss 8.63). Libre 3 none (L 221, 222).
- **D5 Compression lows.** Gamma(2.37, 1/75.7) / day asleep, from the ice compression-low detector
  (run:2026-10-11-ice-compression).
- **D6 Availability.** Gap rates by length bin from the **pilot** donors for G6 / G7 (162), eda for Libre 3 (6 pilot
  donors) (L 45), scaled per donor by its own short / long rates (`gap_own`, default). Per-bin sums in
  `sensor.MEASURED_GAPS`: G7 4.11, G6 2.10, Libre 3 1.50 / day. c80: G7 gaps 2.75 / 1.02 / 0.28 at 7–15 / 15–30 / 30–60
  min vs 2.70 / 1.12 / 0.27; wear 0.972 (0.977) (L 45, 74). Donors' short gaps p10 / 50 / 90 0.6 / 2.7 / 8.6 / day, long
  0.06 / 0.18 / 0.47; c114 wear KS p 0.000 → 0.60 (`templates.add_gap_rates`; L 107). Outages ≥ 12 h are not modelled
  (L 74).
- **D-low.** Now the q of D3 (L 393). Donor target: crossings below 70 per day by duration ≤ 15 / 15–45 / > 45 min 0.58 /
  0.52 / 0.17 (`cross_dur.py`; L 361).
- **D4, D7.** eda lessons only.

## E. Pump and infusion site

- **E5 / E5b Site life and per-site speed.** Absorption 0.9 → 1.15 by day 4; efficacy −2.5% / day after day 1 [I];
  per-site speed lnN SD 0.27 (`site_cv`, Haidar 2013): c125 t54 0.165 → 0.209 (0.215), P(reach 54) 0.182 → 0.200 (0.200)
  (L 115, 199). Donor site-age check: 3 usable donors, TDD / mean flat over site days 0–3; stays on literature (L 376).
- **E6 / E8 / E10 Site failures.** p 0.012 failing per site, 0.003 full occlusion, 0.004 dislodgement per wear, summing to
  Kanapka 2022's 1.9% adults (youth ×3). At these rates between-day fraction 0.142 → 0.112 (0.105), daytime no-bolus lows
  0.183 (0.185) (L 30, 43, 80).
- **E11 Lipohypertrophy.** 26% adults, 42% children, half their sites at bio 0.78, dose CV 0.5 (Famulla 2016). c75 vs c74:
  mean 151.5 (151.4; was 147.2), TDD 37.2 (37.2; was 36.0) (L 67).
- **E1–E4, E7, E9.** Literature only (evidence/06).

## F. Behavior

- **F1 Meal schedule.** Main meals on the donor's own clock (`own_clock`; medians 8.79 / 12.77 / 19.04 h; c230 day /
  night 2.025 vs 2.057) (L 206, 207); window shares from the donor (`add_slot_rates`) (L 51); main meal 1.9× a snack
  (Camerlingo 2021; c52 grams per entry 32.3 vs 32.6) (L 47); GEV meal gaps (L 96); snacks only while awake (donors eat
  00–06 on 7% of nights) (L 56, 58). Breakfast skipped on the donor's own share (`skip_own`, column `skip_bfast`): median
  0.18, p10 / 90 0.07 / 0.36 (168 donors) (L 182); c369 3-h meal change +6.2 (+2.6 without) (L 368). Day total AR(1) CV
  0.22, ρ 0.29 (Tarasuk & Beaton 1992; Levitsky 2017); donors' entered carbs day-to-day CV 0.40 (L 39).
- **F2 Announcement and carb count.**
  - Raw rates (`templates.add_raw_rates`): 2.97 entries / day, 4.59 manual boluses / day, 12.0 U / day by hand (L 36).
  - Bias N(−0.10, 0.10) (Brazeau 2013): the labeler alone spreads per-person medians ~0.46 log-SD, all of the donors'
    0.45, so the entered / pulse ratio is not a count bias (L 35).
  - Per-meal SD lnN(0.3, 0.3) (Pete 2026-10-18): labelled arrival ÷ entered grams donors p5 / 25 / 50 / 75 / 90 0.30 /
    0.64 / 1.06 / 1.66 / 2.43; count_sd ×1.5 (c251) 0.31 / 0.63 / 1.05 / 1.64 / 2.40 (`arrival_tail.py`; L 228).
  - Size term (`count_brazeau`): error 10.54 − 0.28 × g (PMC7594710), held at 20 g below. c306 TIR 72.4 (71.7), lows KS
    0.048 → 0.24 (L 146, 304).
  - `entry_split`: donors' meal entries p50 1.72 / day, snack 1.69, sizes 34 vs 25 g (130 donors); c289 entered g 99 (102)
    (L 280).
- **F3 Meal bolus and top-ups.** Timing at the donor's labelled median lead less +2 min labeler bias, `lead_sd` 23 min:
  labeler onset error SD 26, bolus-lead SD 28 (`lead_err.py`); lead IQR 50 min (51), t54 KS 0.24 → 0.50 (L 106, 121).
  Split second bolus: ratio median 0.93 (code lnN(log 0.93, 1.16)), 12 min later, 17,898 pairs (L 47). Top-up plans =
  donor rate / 0.485 (realized 0.167 vs 0.090 at 0.38, c240) (L 216). Check: automatic insulin 0–120 min after a bolused
  entry 0.97× the donor's, meal bolus 1.00× (`post_auto.py`; L 216, 238).
- **F4 Corrections.** Size (`corr_size_own`) lnN(corr_u_med, corr_u_lsd) as absolute units: donor lone boluses (44,906)
  per-donor median 1.45 U, within-person log-SD 0.83 (L 223, 224). Rate / threshold per person (`corr_p_mult`,
  `corr_thr_adj`) to the donor's lone boluses ≥ 0.5 U (median 1.07 / day at CGM 199); rounds reach 0.61–0.68 of it,
  opportunity-capped (L 224, 225). Trend (`corr_trend`): donors' no-entry bolus rate at 180–280 by 30-min trend falling /
  flat / +10–30 / > +30 relative 0.50 / 1 / 1.96 / 3.52 (`corr_hazard.py`); c257 0.37 / 1 / 1.49 / 3.22 (L 237). Wait
  10 min: 26% of no-entry boluses come within 20 min of the previous (L 47, 64).
- **F5 Low defense.** Proactive onset N(60, 20): `pro_shift` −20 / −40 on c407_pp2 t54 0.118 / 0.132% (0.190), P(reach
  54) 0.24 / 0.22 (0.21), lows 0.79 / 0.83 (1.00), 3-h meal change +17.5 / +14.1; −20 keeps meal shape (c409_ps20;
  L 409). The trigger needs CGM near the low band and not rising (projection alone fired at 220 mg/dL, L 12). Logging
  `p_log_pro` = `p_log_rescue` 0.12: like for like (`treat_log.py`) donors median 0.063 / mean 0.218 logged treatments
  per day; at 0.25 twins 0.333 / 0.418, at 0.12 0.209 / 0.217, carb entries 3.04 / 3.67 (2.96), score 0.380 → 0.371 /
  0.428 → 0.413 (lg12; L 500).
- **F6 Monitoring and sleep.** Alarm wake N(0.72, 0.2): donors' night low duration p50 / 90 20 / 70 min, 27% treated,
  rescue p50 12 min after start; wake ×1.6 (c287) gives low duration p90 65 (65) (`low_treat.py`; L 273, 274); higher
  rejected as beyond Buckingham 2005 (L 414). `night_pro` / `uls`: donors' night pre-emptive rises from < 100 0.222 per
  night (onset 88), flagged rescues 0.075; twins 0.149 / 0.115 before, 0.234 / 0.088 after (c446_npu); minutes per low
  p50 20 (20), night low duration p50 35 (35), night share 31% (22) (`night_rescue.py`; L 442, 443).
- **F8 Site changes.** Code default every N(3.0, 0.4) d as a continuous interval. **sd3 enables `site_clock`**: whole days
  round(N(3.0, 0.4)) ≥ 2 at the person's hour N(19.5, 1.5) clipped 16–23, ± N(0, 1) h. The continuous interval put changes
  at any hour (median 13.8 h) vs the field's 17–22 h (eda L 52, twiist); with it p10 / 50 / 90 17.1 / 19.5 / 21.7 h,
  score 0.375 / 0.457. Glucose cost still half the field's (+6 / +12 vs +28 at hours 0–3) (`site_sim.py`; L 513, 523).
- **F9 Grazing.** lnN(2 / day, 1.0) × lnN(10 g, 0.4), `graze_keep` 0.25, fast, on the donor's unannounced-pulse clock;
  **sd3 sets `graze_keep` 0.0**. `graze_keep` 0.5 / 0.25 (c382_gk25): unannounced labelled load 95.1 / 97.3 g-eq / day
  (94.7), g-eq per entered gram 1.28 / 1.18 (1.19) (L 382). Motivation: donors' quiet waking 30-min changes skew +0.76
  vs sim −0.12 (L 78). `graze_fast` c176: rising-trend corrections at 90 / 120 min −14.8 / −33.8 per U (−30.7 / −36.1)
  (L 158). Clock (`unann_hour.py`, L 230). Added back to f4: score 0.407 (L 517).
- **F10 Hand-dosed food boluses.** Pilot lone boluses median 1.85 U at median glucose 163, 22% below 140, mean ratio to
  Loop's recommendation 1.95; split per donor in `templates._free` (L 13).
- **F11 Eating pulses.** ~5.6 / day of median 26 g-eq; labelled pulses match at the meal level (phase mix 86 / 13% vs 87 /
  12%) (L 16, 93).
- **F12 Temporary Overrides.** 71% of pilot donors, median 0.36 / day; less insulin 45% (0.60, 1.4 h), more insulin 17%
  (1.33, 1 h, from ~210 and rising), target only 37% (~90, ~1 h) (`add_override_rates`); reactive c57 0.22 / day vs 0.195
  (L 40, 50).
- **F13 Settings edits.** 2,821 changes over 156 donors in ~4 months: median 0.03 / day basal, 0.016 ISF, 0.016 CR;
  |change| median 3.6%, p90 14%; corr 0.16 with the prior 3 days' glucose (`add_edit_rates`; L 41).
- **F14 Per-window entry chance.** Donors' entered grams 17–23 h p50 34.7 g / day, evenings with no entry 17%; c339 24.0 g /
  33%, c341 30.6 g / 25% (L 340, 341, 345).
- **F15 Window grams from labelled load.** Donors' labelled g-eq per entered gram 04–10:30 / 10:30–15:30 / 15:30–22 /
  rest 1.32 / 1.15 / 1.05 / 1.19 (`slot_ratio.py`, column `slot_lr`; L 231). c346: hourly RMS 9.6 → 7.7 mg/dL (L 346).
- **F16 Intake per donor load (off).** c333: Q4 morning 154 → 155 (124); Loop absorbs it (L 333).

## G. Truth and settings

- **G2 True ISF.** ISF_W 1.0 (Pete 2026-10-19): ICE yardstick (`templates.add_isf_yardstick`) × the body-model fit
  (`fit_body --regression`), clipped 0.5–2× settings. Yardstick fits 202 of 206 donors; vs the distribution cohort's on 14
  donors Spearman 0.84, ratio 1.04; ratio to settings p25 / 50 / 75 0.74 / 1.02 / 1.33. Body-fit multiplier p10 / 50 / 90
  0.90 / 1.00 / 1.28 (shrunk, τ 0.18). c276: t54 KS passes for the first time (L 259–262).
- **G3 Body weight.** A template `bw_kg` replaces the prior where known (L 489, 491).
- **G4 Insulin balance.** Basal share N(0.5, 0.07) clipped 0.35–0.7, shifted to centre 0.42, clipped 0.25–0.7 (Pete
  2026-10-17); the TDD budget pays for all intake (`budget_all`), pre-emptive carbs 0.08 with a 0.2 meal floor
  (`budget_tight`), protein glucose (`budget_pro`).
  - Centre: overnight automatic ÷ scheduled basal, donors 1.29 vs sim at 0.5 1.65; overnight zero-delivery 12.5% of bins
    (`ctrl_sat.py`). c135 at 0.42: night insulin CV 35.2 (36.0), t54 0.233 (0.215), lows 1.08 (1.08); `basal_own`
    rejected (L 124, 125, 134). `basal_fit` ran to its 0.25 bound with the gap unchanged; off (L 463, 471–473).
  - Budget: median person on the old base ate 256 g / day vs a 148 g budget (`budget.py`; L 143); 1.20× the budget
    (c223) (L 202). `budget_pro` (0.39 g protein per carb gram): c378 mean 152.7 (151.9), TDD 38.75 (38.70), TIR 72.6
    (71.9), lows 1.00 (L 378).
- **G7 Carb sensitivity.** CSF = 1.05 · [1.85 · ISF_data · TDD / 500]^0.5 · [settings ISF / CR]^0.5, `csf_w` 0.5. Unshrunk,
  settings ÷ true CR spread 0.79–2.05 with post-meal lows 0.51 vs 0.12 / day; shrunk 0.85–1.47, labelled response 17.0 per
  10 g (17.1) (L 27, 37). c300 `csf_w` 1.0 / 0.5: 23 / 32 matched, p_reach54 0.20 (0.20) (L 300). Constant 1.85 through
  the labeler (L 33); 1.08 → 1.05: g-eq per entered gram 1.208 → 1.247 vs 1.21 (L 197). Target 1.19 (automatic 1.16,
  temp 1.24; `geq_cmp.py`) (L 302, 347).
- **G7b Per-donor meal response.** `csf_geq` multiplier p10 / 50 / 90 0.60 / 0.96 / 1.44, two pooled rounds, clipped
  0.6–1.5: twin / donor g-eq per gram in the low-runner quartile was 1.37 / 0.99; c358 TDD 39.2 (38.7) (L 358, 359).
  `csf_lvl` 1.05: meal ICE above pre-meal per 10 g c396 total 42.8 vs donors 47.4 while g-eq per gram matched (1.18 vs
  1.19); at 1.05 ICE 45.6 and g-eq within ~5% (c403_cl105; L 401). 1.2 on lg13: ICE area 5.88 → 6.21 per g (6.41), score
  worse (L 511, 512, 516).
- **G6 Formulation from Loop's IOB.** Net-basal IOB at peak 75 vs 55 against loop_iob.parquet, 10 days per donor
  (`add_insulin_from_iob`): recorded Fiasp / Lyumjev match ultra-rapid 37 of 38 and 14 of 14; of 154 recorded rapid-acting
  118 match adult, 36 ultra-rapid (L 248).
- **G5 Suspend threshold (`suspend_own`).** Donors 80 (104 of 168), 70 (50), 90 (8), 100 (6) (L 232).
- **G6b Dosing strategy share.** Pilot `auto_day_share` p10 / 25 / 50 0.39 / 0.76 / 1.0; against the donors' autobolus
  days automatic 1.14×, basal 0.87×, automated total 1.04× (gamepc `~/additive/blocks/`; L 331).
- **G9 Loop not acting.** 168 pilot donors' `disruptions.csv`: offline 0.9 / day median, lnN(32 min, 0.86) (2.9% > 6 h
  left out); pump-error cycles ~3 min, 2.45 / day (`add_disruption_rates`; L 60, 61). `missed_own`: Loop decides in a
  median 92% of slots; with CGM present single 4.4 / day, 2–3-slot 0.5 / day (`add_missed_cycles`; L 377).
- **Controller GBAF (`rc_own`).** Pilot donors i003 / i056 / i010 get their deployed GBAF; no others in the screen (L 227).

## R. Data-driven residual (MODEL_GUIDE § 9; no COMPONENTS.md row yet)

On in sd3 (`--enable resid`), off in the code default. Tools in `patient_sim/resid_tools/`; runs
runs/2026-10-27-additive-natexp.

- **`resid_m` level.** Constant mg/dL/h per person, rounds of `lvl_resid.py` (slope 0.86 → 0.58 mg/dL per mg/dL/h, gain
  1.2); p10 / 50 / 90 −53 / 0 / +20. Twin–donor mean ρ 0.39 → 0.77–0.88, |gap| p50 16.3 → 2.9–3.4 mg/dL; held out (odd
  blocks fit, even scored) mean ρ 0.93 (ceiling 0.96; lg13 0.45), TIR 0.80 (`heldout.py`; L 515, 516, 519).
- **`resid_f`, `resid_skew`, `resid_mult`.** OU τ 20 min; code skew 0.0, mult 1.0, **sd3 0.7 and 0.6**. `fit_resid.py`:
  donor medians of the `ice_var.py` statistics, shrunk by block reliability 0.82 / 0.65 / 0.34, NNLS on target² − core²
  through the bare process's transfer; resid_f median 28 mg/dL/h, 0 for 21%. Gaussian at full size: fast-SD ρ 0.15 →
  0.73 but lows 1.33 / day, t54 0.39; the core has the donors' lower ICE tail (5th pct −68 vs −72) but not the upper (95th
  70 vs 79), hence the skew. At 0.6× with si_norm 0.92: lows 0.83, t54 0.156, t70 1.55 (1.60) (L 514, 516).
- **`si_norm`.** Code 1.0, **sd3 0.92**: the old life-factor modulators' combined SI multiplier over 80 c446_npu twins
  had mean 0.919 (median 0.892) against the yardstick (L 468, 516).
- **`csf_sd_mult` (person.py).** Each meal's glucose ×, grams held; p10 / 50 / 90 0.50 / 1.00 / 1.64 (pilot). `sd_fit.py`
  × (donor SD / twin SD)^1.5 per round, step 0.8–1.25, total 0.4–2.5, alternating with the level, three rounds on both
  draws: SD ρ 0.26 → 0.93; held out CV ρ 0.63 (ceiling 0.92; f4 0.03), TIR 0.89. sd3 score 0.370 / 0.454 (Pete
  2026-10-28). It damps the TIR response to edits (L 528–530, 534).
- **What it replaced.** The core without B3, stress, B6, B5, B14, C7, F9 and A4c barely lowers volatility (quiet fast SD
  45.8 → 43.3); all back on sd3 lows 1.29–1.75 / day and score sum 0.922 / 0.845 vs 0.824 (L 514, 517, 522, 545).

---

## Targets

The 51 scored rows, their tiers and the donors' values are in MODEL_GUIDE § 10. Below are the donor measurements behind
them and the component targets (`review.py`). G7 unless stated; "labelled" = ice labeller.

**Outcomes and lows**
- Time < 70 p25 / 50 / 75 0.65 / 1.15 / 3.83% (143 donors); post-meal low share tracks it (Spearman +0.79) (L 218).
- Low onsets 1.059 / day: < 2 h after an entry 0.270 (0–30 / 30–60 / 60–120 min 0.058 / 0.071 / 0.141), 2–4 h 0.166,
  4 h + 0.623; P(low within 2 h) by entry BG < 90 … 200+ 0.196 … 0.050 (`low_ctx*.py`; L 145, 146, 212). By 3-h block
  00–21 h 0.121 / 0.105 / 0.108 / 0.121 / 0.132 / 0.164 / 0.178 / 0.137 (L 278).
- After meal boluses: lows within 2 h 0.080 per meal bolus (L 395); bolused entries ≥ 15 g ending < 70 within 2 h 9.7%
  (entry < 100 / 100–140 / ≥ 140: 21.3 / 8.5 / 6.4%) (L 188); flat entries 100–140 < 70 within 60 min 3.3% (L 291).
- Minutes below 70 per crossing p50 20.0 (p10 / 90 11.3 / 27.5) (L 329). Night share 22%, night duration p50 / 90 35 /
  80 min, night onsets falling toward dawn (L 167, 414, 438, 443). Untreated lows 0.611 / day (L 240).
- Recovery after a low +56 at 1 h, +65 to +73 at 2–4 h (L 55). Quiet falls at 90–130 reaching < 70 in 30 min 3.9% (L 410).

**Meals**
- 3-h meal change, bolused isolated ≥ 15 g: median +21.2 (per donor p50 +20.1); by size tercile +12 / +23 / +34
  (`meal_traj6.py`; L 301, 302). The scored `meal_d3h` row is block-based (donors 38.0).
- By slot every 30 min to 3 h: breakfast 0 / 16 / 29 / 33 / 28 / 25 / 21, lunch 0 / 17 / 27 / 27 / 28 / 27 / 26, dinner 0 /
  13 / 10 / 5 / 9 / 14 / 17 (`meal_traj_tod.py`; L 338, 429).
- Entry-anchored ΔCGM per 10 g (≥ 20 g) at 60 / 120 / 180 min: automatic +4.3 / +4.3 / +5.4, temp +6.4 / +5.2 / +5.5
  (`entry_traj.py`; L 130, 144).
- Within-person SD of the 0–2 h drop 36.7, between 16.7 (L 188, 198). Time to peak median 101 min (L 178).
- Post-meal counteraction (`ice_integral.py`): ICE above pre-meal per 10 g at 0–1 / 1–2 / 2–3 / 3–4 / 4–6 h 13.0 / 15.4 /
  10.5 / 3.7 / 0.3, total 47.4 (L 316, 401). Meal pulse ICE area 0–4 h 6.41 mg/dL per entered g, onset-to-peak 30–40 min
  (26,761 meals; L 509, 511). Arrival: peak per entered g per h 1.10, time to peak 0.75 h, duration 2.08 h (L 217).
- Meal insulin, U per 10 g, user / automatic −15..120 min 1.19 / 0.74, 120..240 min 0.11 / 0.77 (`meal_ins3.py`; L 306).
  Bolus ÷ (entered g / CR) median 1.00; requested ÷ recommended 1.00 (L 128, 186).

**Unannounced motion**
- Labelled load: 182 g-eq / day, unannounced 94.7 (by 3-h block 11.3 / 8.8 / 10.2 / 10.3 / 12.6 / 10.9 / 12.8 / 15.4;
  `unann_hour.py`) (L 108, 230). Unentered rises 3.46 / day, 0.66 per night; 31% follow a Loop cut (L 184).
- Matched-height fall in the hour after the max: unannounced −36.9 / −33.5 (automatic / temp) (`pulse_tail.py`; L 286).
- Fast falls (< −150 mg/dL/h over 15 min): 1.47 / day; entries ending in one 14.3% (L 494, 498, 510). Unexplained falls
  (`ice_dip_day`) by 4-h block 0.20 / 0.24 / 0.31 / 0.30 / 0.38 / 0.29 (L 495). Unexplained drive (`ice_var.py`):
  day-mean SD 11.6, 4-h block 23.0, fast 55 mg/dL/h (L 514).
- Unlogged rise rate median 55 mg/dL/h (L 494); far-from-meal unlogged load p50 47.7 g-eq / day (L 449).

**Corrections**
- Lone corrections ≥ 0.5 U (4,146), ΔCGM per U at 60 / 120 / 180 min: flat −26.1 / −44.2 / −53.3, rising −17.7 / −36.1 /
  −41.8, falling −30.9 / −53.1 / −58.1 (`corr_drop.py`; L 154, 157).

**Night, circadian, delivery**
- Hourly median CGM 00–23 h: 158 152 147 141 136 130 127 127 135 140 146 146 151 161 161 158 157 158 156 160 161 165 166
  165 (`hour_bg.py`; L 323).
- Night-to-night insulin CV: quiet nights 30.3% (Ruan 2016 31%); 12-day blocks p50 35.8 / 32.6 (automatic / temp)
  (L 55, 288). Night means: SD 32.2, no persistence (lag-1 −0.04) (L 332).
- Quiet nights by 00:00 glucose < 120 / 120–160 / ≥ 160: drift +8.3 / −24.3 / −72.0, delivered ÷ scheduled 0.98 / 1.17 /
  1.55 (L 173). Night delivered / scheduled 00–06 h 1.32 (L 171).
- Delivery by record rate: zero_frac 32.5%, TDD 38.7, day / night 2.00, med_nonzero 0.085 (L 455). Loop delivery /
  schedule by CGM band < 100 … > 260: 0.31 … 2.62 (`loop_resp.py`; L 368). Autobolus days: 71 boluses, 14.7 U / day
  (L 377).

**Sensor and short scale**
- Structure function lag 5 / 15 / 30 / 60 / 120 / 240 min: 7.1 / 18.4 / 31.3 / 49.0 / 64.5 / 77.2 (`structfn.py`; L 238).
- Step ACF zero-crossing 40 min (G6 37.5, Libre 3 62.5) (L 160, 275); sigma_disp 3.62, between_day_frac 0.102 (L 276).
- Night / day high-frequency noise 3.40 / 4.12 (L 267). Wear: donor median 0.974 (L 107).

**Exercise and edits**
- Activity response `act_net20` / `act_net20_hi`: donors −5.7 / −12.6 mg/dL over a bout's first 20 min (L 494). Workout
  habit (11 consistent recorders): 1.62 / week, 48% within 2 h after a carb entry (L 494, 496, 497).
- Settings-edit response (`resid_tools/score_change.py`): e pool (580 edits) mean −23.5 / TIR +9.6 per log unit; tight −
  rest TIR per +10% insulin pilot −7.18, x −1.25, e −1.55 (L 493, 533, 536, 541, 542). Site changes (twiist): +28 mg/dL at
  hours 0–3, change hour 17–22 h (L 523).

---

## Literature not yet in evidence/00–16

Each confirmed absent by a grep of `docs/additive/evidence/`.

- Hildebrandt P 1985: sitting cuts subcutaneous blood flow 29–47%, insulin absorption 19–44% vs supine (17 patients). A4b
  (L 163).
- Healy GN et al. 2008 (breaks in sedentary time): C7 bout structure (L 161).
- Goo RH et al. 1987: the same solid meal empties ~54% slower in the evening. A14 (L 180).
- Gray RS et al., Diabetes 1982;31:929, doi:10.2337/diab.31.10.929: HGO half of basal at 59 ± 8 / 119 ± 6 min after 40 /
  120 mU/m²/min. A6 offset (L 192).
- Rizza RA, Mandarino LJ, Gerich JE 1981, Am J Physiol 240:E630: half / full HGO suppression at ~29 / ~60 µU/mL. A6
  `egp_sat` (L 193).
- Laxminarayan S et al. 2015, DTT, doi:10.1089/dia.2015.0118: SI 17% lower in the dinner window after a high-fat dinner;
  appearance peak 102 vs 71 min. A12 onset (L 352).
- Vetrani C et al. 2022, Diabetologia, doi:10.1007/s00125-021-05587-0: 25 HCL adults, 1,264 meals; slot composition.
  A15 (L 338).
- Scidà 2025, JDST, doi:10.1177/19322968241256475: 120 AID adults, same response whatever the carbohydrate / fat-protein
  ratio (L 338).
- PMC11446970: 470 T1D adults, fat 75 ± 31, carbohydrate 162 ± 63, protein 70 ± 24 g / day. A12 `macro_own` (L 129).
- PMC7716902: 15 U Humalog clamp, 6.3% of the glucose infused in the first hour, duration 405 min. A5 (L 113).
- Franke 2008, J Gastrointestin Liver Dis 17:27 (walking after a meal: half-emptying 123 → 107 min); PubMed 22517770
  (liquid emptying reduced above ~70% VO2max). A16 (L 344).
- Sampson Perrin 2015 (fasting glucose 126 / 133 / 147 on set days 1 / 3 / 5); Simic 2021. E5b (L 43).
- Tarasuk & Beaton 1992 (intake CV ~0.22); Levitsky 2017 (next-day correlation 0.29). F1b (L 39).
- Waljee 2017 (21.1% of US adults ≥ 1 short steroid course in 3 years); PMC8157052 (afternoon–evening highs). B14 (L 140).
- J Perinatol 2021: need falls after week 37. X9 (L 141).
- Endocrine Abstracts 2006 ea0011p401: insulin need ~31% higher in hyperthyroidism. X12 (L 336).
- G6 Pro real-world accuracy (no author / year in the lesson): MARD 13.6 / 10.5 / 10.1% at 0–12 h / 12–24 h / after.
  D3d (L 222).
- Aleppo G et al. 2017; Pettus & Edelman 2017: trend-arrow dosing. F4 `corr_trend` (L 237). (evidence/13's Pettus 2022 is
  a different paper.)
- Van Cauter 1991, 1997: glucose rises 20–30% in sleep at constant infusion, ~2/3 from sleep itself. `sleep_util`
  (L 173). (evidence/11 cites other Van Cauter papers.)
- Asplin et al. 1989, JCEM 69:239: T1D GH pulses 7.2 / 11.1 per 24 h (men / women), acrophase ~01:00. B2b (off) (L 417).
- PMC5872070: CGM MARD 9.5 → 16.5 → 9.3% before / during / after aerobic exercise. `sensor_act_k` (off) (L 498).
- Morse 2006, Diabetes Care 29:1800: 9.7% of 714 adults eat > 25% of calories after supper (L 184).
- King 1994; Schubert 2013: exercise appetite suppression (L 244). PMC2827497: missed boluses most common for snacks
  (L 284).
- NHANES data briefs (about half of US adults drink a sugar-sweetened beverage on a given day); BRFSS 2013 (22% of adults
  with diabetes ≥ 1 / day). A10b `meal_drink_p` (L 209).
- Negative meal-brake searches (L 101, 114, 118, 133, 139): Vella, Shah, Basu & Rizza 2008 (splanchnic extraction
  10–25%, equal in T1D); Pennant 2008 (pre-bolus leaves meal Ra unchanged); Clausen 2009 (set-wear tmax 55 → 45 min);
  Englyst 1999 (rapidly available glucose explains 70% of glycaemic-response variance; basis of the A10b spread);
  Leohr 2020 (lispro less than dose-proportional); PMC7007438 (disposal saturation at 0.3–0.4 U/kg).

---

## Code defaults and the sd3 reference

- A6 `ins_p2e`: no doc states a default for it. `ins_p2` / `ins_p2e` (world.py:166–168) rescale the body *after*
  per-person calibration, while `p2e_cal` (cohort.py:42 → person.py:380) recalibrates every person at the new rate.
- `graze_keep` 0.25 (behavior.py:117), `flow_sd` 0.5 (world.py:672), `si_norm` 1.0 (world.py:667) and `resid_skew` /
  `resid_mult` 0.0 / 1.0 (world.py:696, 682) are code defaults that the sd3 command overrides (0.0 / 0.0 / 0.92 / 0.7 / 0.6).
- `act_frag` (world.py:468) and B3 `day`, `stress`, `illness`, `menstrual`, `steroid` (modulators.py:58–61) are on in the
  code and off in sd3. The G4 basal share and the G7 constants (1.85, 1.05) match their docs.
