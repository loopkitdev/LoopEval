<!-- Role overlay. Loaded via ROLE.md; see AGENTS.md → Roles. -->

# Role: additive — a forward patient simulator built from named factors

The other simulation roles work **subtractively**: they take a real record, remove what they can
model (insulin, rescue carbs) and replay the residual. This role works the other way. It
**composes** a virtual person from named, separately-evidenced factors — physiology, meals,
exercise, illness, the menstrual cycle, the sensor, the pump, and the person's own behavior as a
second controller — and runs that person in closed loop against LoopEval's real controller.

What it buys that a replay cannot: people and situations no donor recorded, every factor
switchable (ablations: "what does exercise cost this algorithm?"), ground truth for every
quantity (true BG, true carbs, true sensitivity), and no inherited rescue-carb or residual
confound.

Read with **AGENTS.md** (shared) and **docs/agents/verification.md**.

## Goal (set 2026-10-15, Pete)

Build a patient simulator usable with LoopEval, by additive modeling.

- **Breadth of factors**, ranked by impact: start from the large lists (diaTribe's 42 factors)
  and model the big ones first — carbs, insulin, exercise, illness, menstrual cycle.
- **Physiology at the right depth**: beyond Loop's own effect model and Tidepool's
  SimpleMetabolismModel, but not maximal fidelity — past a point, physiology gains are tiny
  next to the real-world (behavior, sensor) errors.
- **Traits, not scripts**: much of the variation is the person — how closely they monitor,
  how proactively they act on a predicted low, how they eat and bolus. A virtual person is a
  trait vector drawn from population distributions.
- **Sensors simulated per model** (G6, G7, Libre 3 via twiist, …) from as much data as we have.
- **Evidence for every component**: a reference (literature) or a measurement (BDDP data) for
  each mechanism and parameter, kept in `docs/additive/evidence/` and the component registry.
- **Real-world comparison is the primary test**: the simulated cohort must reproduce eda's
  measured statistical shape of glucose (and insulin, and behavior). A divergence means a
  missing or wrong component.

## Where the work lives

| Path | What |
|---|---|
| `analysis/loopeval_analysis/patient_sim/` | The simulator (Python): components, person sampler, plant server. Shared code → `main` when a piece is finished. |
| `docs/additive/evidence/` | Literature notes per area (00–16) and `17-measured.md`, the donor-data measurements behind each component's parameters. |
| `docs/additive/COMPONENTS.md` | The component registry: every factor, its model form, parameters, evidence and status. |
| `docs/additive/LESSONS.md` | This role's standing lessons (original numbers; new ones from 548). The full record of 1–547 is `docs/additive/archive/LESSONS-001-547.md`, where every "LESSONS N" citation resolves. |
| `runs/YYYY-MM-DD-additive-*/` | Experiment outputs, with the driving script beside them. |

## How a virtual person runs in LoopEval

Through the existing external-plant protocol v2 (`Sources/EvalCore/Engine/ExternalPlant.swift`,
`docs/ice/plant-protocol-v2.md`) — no engine change. `simulate` takes its sample times from the
field glucose file, so the simulator first writes a synthetic data dir (therapy settings, a
burn-in history, the sensor's sample schedule), then `simulate --candidate-counterfactual
--external-plant '<plant server>' --plant-behavior` hands every step after burn-in to the plant:
LoopEval doses, the plant's body responds, the plant's person eats, boluses and treats lows.

## Calibration rules (Pete)

- **The body follows the data, not the user's entered settings** (2026-10-19). Where a donor has a data-fitted value —
  ISF from their own glucose response, basal-need shape and night level from their delivered insulin, insulin type from
  Loop's recorded IOB — the body takes it (ISF_W 1.0). Settings stay what the person's Loop is configured with.
- **Realism, not agreement with Loop** (2026-10-17): calibrate the body to physiological evidence and donor data, never
  to Loop's curves or forecasts.
- **Level on the measures but better explained is a win** (Pete 2026-11-01): a change that leaves the weighted score and
  the natural-experiment response unchanged, but removes a defect or keys a term to the quantity its evidence is measured
  in, is adopted. Record both sides and keep it revertible. (Extends LESSONS 303; the case is LESSONS 554, 556.)
- **The patient is independent of the controller** (2026-10-18): controller configuration (RC mode, GBAF, strategy) is
  never a patient trait; validation runs give each person their donor's deployed controller (`--enable rc_own`), the
  code default stays stock.
- **No mystery terms — except the residual layer** (Pete 2026-10-27): a divergence in the evidenced core is closed by fixing
  or adding a named component, never by an unnamed term. The variability the core cannot carry is modelled by the
  data-driven residual (`resid`), fitted per person to the donor's own data and kept separate from the core; the core is
  not retuned to chase a statistic.
- **Fit from literature first, then from our data** (2026-10-20): a named component's parameters come from the literature
  where it identifies them; where it does not, fitting them to the donor data is fine (the sensor included), kept inside
  the component's own evidence (e.g. a sensor fit keeps its FDA accuracy loss).
- **Publishing**: updates to this model are self-approved (merge to `main`, move the board task to Done); changes to
  general LoopEval code still go to Pete first.

## Running and comparing a cohort

- **Reference run**: `python -m loopeval_analysis.patient_sim.cohort --n 112 --days 14 --templates
  templates_pilot_logs.csv --enable rc_own --out runs/<arm>` on gamepc from frozen code (`git archive <sha> analysis` into
  `~/frozen/<sha>`, launched through an ssh held in a Mac `tmux -L fast` session). Templates live outside the repo
  (`~/.loop-eval/runs/2026-10-15-additive-templates/`) and must be copied to gamepc after every change; template columns
  are built by `templates.py` (`add_isf_yardstick`, `add_insulin_from_iob`, `add_delivered_profile`, …).
- **Scoring**: `compare_runs.py` (eda's 51 statistics, KS against the donors; see Match targets below), `review.py` (each component against its own
  target), plus the measure scripts beside the run. A different draw of people (seed0) moves the count by up to 6 (LESSONS 444): score an arm whose
  effect is within that scatter on two draws (seed0 1000 and 5000) before adopting it.
- **Exercise-faithful configuration** (L 565; not the default, because every step toward it costs the weighted score):
  `--enable ex_abs --set ex_headroom=1.5,ex_surge_width=0.75` on the reference. It reproduces C4's own by-METs table —
  the ≥ 8 MET band reads +0.9 against the donors' +1.2 where the band has enough bouts — against the reference's +12.8 / −5.1.
  Use it whenever the response to a workout matters; the reference keeps the score-optimal settings.
- **Current reference** (2026-11-01): **ov0** (runs/2026-10-31-additive-gesplit; templates
  `templates_pilot_resid_ov1.csv`) — ad3 with each Temporary Override class's duration fitted over the windows the
  model can actually produce. A donor record under 5 min is a cancellation (the ETL keeps an edit-version per change),
  and `_override` clips at 15 min, so including those in the per-class median systematically understated the length of
  every window the twins did run; dropping them lifts `ov_less_h` from 1.42 to 1.88 h and realized length from 72 to
  83 min against the donors' comparable 79 (L 586). Score **0.332 / 0.394 / 0.391** against ad3's 0.321 / 0.425 /
  0.410 — better on both fresh draws, worse only on draw 1, mean **0.372 against 0.385**; tier 2 improves on both
  (0.497 / 0.505 against 0.505 / 0.555). The gain is where the mechanism predicts: more time at reduced needs, so Loop
  commands less — bg_mean 0.263 → 0.119 and TDD 0.262 → 0.177 on draw 2. On the natural experiments it is level with
  ad3 within the sampling error (mean ratio 2.32 vs 2.25, t70 3.61 vs 3.38, t54 **4.64 vs 6.22**; the rho differences
  at n = 63 are inside their CIs). Revert by rebuilding the templates without the filter.
- **Previous reference** **ad3** (runs/2026-10-31-additive-gesplit) — ad2 with the residual's fast and block parts
  weighted to waking hours (`resid_diurnal` 0.9, LESSONS 568; variance-preserving, so the per-person amplitudes still hold).
  Score **0.321 / 0.425 / 0.410** on seed0 1000 / 5000 / 9000, tier 1 0.108 / 0.291 / 0.161. Against sd3 (0.370 / 0.454 / 0.420)
  the gain shrinks from the development draw to the fresh one — 0.049 / 0.029 / **0.010** — so the out-of-sample gain is
  ~0.010-0.029; tier 1 holds up better (0.135 / 0.110 / 0.075). Quote those, not draw 1's (L 580). **Decomposed on the fresh
  draw: the soundness adoptions (C4 keying + `ppr_a`) cost 0.010 of score while cutting tier 1 from 0.236 to 0.154; the
  distributional one (`resid_diurnal`) pays 0.020 and leaves tier 1 flat.** Components more correct, aggregate barely moved.
  On the natural experiments it is level with ad2 and clearly better than sd3: tight − rest TIR −1.63 and mean +0.93 (both the
  closest of any arm to the field's −7.18 / +1.65), t70 +0.74 [+0.12, +1.39] against ad2's +1.03 (L 568).
  Revert with `--set resid_diurnal=0`.
- **Previous reference** **ad2** (runs/2026-10-31-additive-gesplit) — ad0 with A12b's post-meal window at its own
  target (`ppr_a` 0.6, LESSONS 558): score 0.340 / 0.444, tier 1 0.146 / 0.312. The meal tail is now calibrated
  (meal_d3_p50 ratio 0.97) and the 3-h meal change 33 / 31 against the donors' 38; the cost is TIR 68.9 / 70.2 against
  71.9, because the twins' excess time below range is amplified as the spread grows. **Best arm yet on change prediction**:
  t70 tight − rest +1.03 [+0.40, +1.64] against the field's +4.27 (sd3 +0.51, ad0 +0.63), though the pooled t70 response is
  smaller (3.21× under vs 2.61×). Revert with `--set ppr_a=0.4`.
- **Previous reference** **ad0** (runs/2026-10-31-additive-gesplit) — st9 plus the three exercise fixes of LESSONS 554, 556:
  session intensity capped by its length with METmax raised to match (`ex_cap_fit`), and C4's surge keyed to 8 absolute METs
  (`ex_surge_mets`). Score 0.364 / 0.416, tier 1 0.229 / 0.294. Adopted on soundness: neutral on the cohort score AND on the natural experiments (L 556).
  Kept (Pete 2026-11-01: level on the statistics and on prediction power, but better explained, is a win). Revert with
  `ex_cap_fit` off and `--set ex_surge_mets=0`.
- **Previous reference** st9 — sd3 with C4's surge threshold at 0.9 of VO2-reserve (LESSONS 553): score 0.353 / 0.437,
  tier 1 0.203 / 0.353. sd3's own numbers now need `--set ex_surge_thr=0.6,ex_surge_mets=0` and `--disable ex_cap_fit`.
- **Previous reference** (2026-10-28): **sd3** (draw 2 sd3_5k; runs/2026-10-27-additive-natexp) — lg13's evidenced core with a
  data-driven residual (per-person level and fast drive) and each person's meal glucose fitted to their donor's spread
  (MODEL_GUIDE § 9–10, LESSONS 513–532). Score 0.370 / 0.454; held-out twin–donor TIR ρ 0.89, CV 0.63 (lg13 0.45 / 0.11).
  Natural experiments (pilot, x, e pools; 790 edits): twins start at their donor's pre-edit level and the tight / rest
  split has the field's sign, but the TIR response to an edit is ~2/3 of the field's and ranks no better than lg13 (L 532).
  Change-test arms need per-event seeds (ARM_EVSEED, L 531). For the SIZE of a change use lg13's settings (TIR field /
  twin 0.95 / 0.64 / 1.03 on pilot / x / e with the corrected scorer), or f4 (level-only residual, 0.76 / 1.27) when the
  twin must start at its donor's level; sd3 under-responds (1.32 / 1.29 / 1.39; L 542). Ruled out as the cause of sd3's smaller response: the residual, the correction habit, the
  sensitivity level (L 534–540); the spread fit damps it (L 534). Open: meal tail 24–27 (38), site-change cost.
- **Previous reference** lg13 (2026-10-25; runs/2026-10-25-additive-rebuild) — lg12's model on the engine that
  keeps delivering through skipped and sensor-less cycles (main 8fa8411 → 4c80c60c; LESSONS 505). Score 0.376 / 0.415,
  tier 1 0.233 / 0.305; mean 154.1 / 157.2, TIR 71.2 / 67.5, t54 0.180 / 0.208%, lows 0.92 / 0.96 per day.
- **lg12** (2026-10-23; runs/2026-10-23-additive-falls) — c446_npu with the saturating
  acute exercise sensitivity (C2, k 0.1; LESSONS 495) and treatment carbs logged at 0.12 (LESSONS 500). Score 0.371 / 0.400; lows 0.88 / 1.00 per day, t54
  0.197 / 0.176%, TIR 71.0 / 67.8. Open: the activity response (−4.2 / −4.8 vs −12.6 at high IOB; eating around sessions, LESSONS 497), entries ending in a fast
  fall (7 vs 14%), slow unlogged rises, dawn unexplained falls. Run additive cohorts on the Mac (Pete 2026-10-23).
- **Previous reference** (2026-10-20): c446_npu, rescored with delivery read by record rate as the donors' statistics are (LESSONS 455): 39 of 51 (draw 2, c447_rs: 34), zero_frac 29.6 vs 32.5%, TDD 41.8 vs 38.7 (twins command 8–14% more insulin than their donors). c446_npu — c440_db with the night alarm defence (LESSONS 442–443): a person an alarm has woken may act before the low (`night_pro`), and Dexcom's predictive Urgent Low Soon alert (`uls`): 40 of 51, minutes per low 20 vs 20 (passing), night share of lows 31% (donors 22), night low duration p50 35 min (35), t54 0.148 vs 0.190%, lows 0.79 vs 1.00 / day (passing), mean 155.5; open: night share, G7 short-scale, between-day share, zero_frac, the meal tail (+13.6 here, +16.9 on c440_db). c440_db — c439_pr4 with dose-dependent bolus absorption on (A4d, β 0.1, Heise 2017; LESSONS 437): 40 of 51, lows 1.00 / day on the donors', t54 0.223 vs 0.190%, mean 155.6, 3-h meal change +16.9 (donors +21); open: night share of lows (36 vs 22%), minutes per low, zero_frac, short-scale structure. c439_pr4 — c436_mofr with the post-meal insulin-action window relative to the person's own meals (`ppr_rel`, mean 1 over the planned days) at `ppr_a` 0.4 (LESSONS 435–436): 38 of 51, mean 155.7, 3-h meal change +17.9 (donors +21), lunch +21–25 over 60–150 min, t54 0.237 vs 0.190% and lows 1.13 vs 1.00 / day (passing, now slightly over), 03–06 h on the donors'; failing zero_frac, vol_cluster_60m. c436_mofr — c418_f5 with each person's own carb / fat / protein mix (`macro_own`, energy 30 kcal/kg, the rest 69 / 31% fat / protein; Pete: the mix is a personal trait) and the fat resistance relative to the person's own usual fat (`fat_rel`; LESSONS 432, 434): 39 of 51, mean 156.7, pre-dawn trough and 24-h amplitude on the donors', t54 0.181 vs 0.190%, 3-h meal change +13.6 (donors +21; the lunch tail is the main open meal gap). c418_f5 — c417_st with the within-curve subcutaneous absorption fluctuation on (A4c `flow_sd` 0.5, Heinemann 2002; LESSONS 419): 40 of 51, t54 0.175 vs 0.190%, lows 0.92 vs 1.00 / day, 3-h meal change +17.4 (+21); open: minutes per low, night share of lows (39 vs 22%), the fast-fall tail, short-scale structure. c417_st — c409_ps20 with stress SI −18% over 1–6 h (Moberg 1994 full text, LESSONS 415, 418): 39 of 51, 3-h meal change +18.2. c409_ps20 — c407_pp2 with the proactive-snack onset lowered to N(60, 20) mg/dL, fitted to the donors' lows (LESSONS 409): 39 of 51, 3-h meal change +17.5 (donors +21), t54 0.118 vs 0.190% and P(reach 54) passing, lows 0.79 vs 1.00 / day. c407_pp2 — c403_cl105 with the post-meal insulin-action window on (`ppr_a` 0.2; Pete: meal shape over lows, LESSONS 408): 37 of 51, 3-h meal change +17.6 (donors +21), t54 0.089 vs 0.190%, lows 0.71 vs 1.00 / day; next the low-side components (behavioural defense). c403_cl105, scored 40 of 51 since delivery is scored as pump records (LESSONS 406: zero-delivery share 36.9 vs 32.5% now failing, the twins' Loop withholding more as after meals) — c396_cr7 with meal glucose × 1.05 (`csf_lvl`, default), set between the labelled g-eq per gram and the post-meal ICE integral, which disagree by ~10% (LESSONS 401): 41 of 51, t54 0.118 vs 0.190%, P(reach 54) and lows passing. c396_cr7 — c395_joint with counter-regulation refitted on the honest sensor (CRmax median 0.137, LESSONS 394): 40 of 51; t54 0.092 vs 0.190% (passes narrowly), P(reach 54) and lows / day passing; true lows still about half the donors'. c395_joint — the G7 sensor refitted to its FDA accuracy tables with the donor-fitted wander kept where it fits both, G6 noise scale on its FDA table (LESSONS 393): 37 of 51. The CGM lows now come from true glucose and run short (t54 0.074 vs 0.190%, P(reach 54) 0.14 vs 0.21): the earlier references from c384 on matched the lows partly through false sensor lows (G7 CGM < 54 bias −23.5 vs FDA −9.3). Read absolute t < 54 as a lower bound; the open target is the body's true lows and fast motion. c391_flag — c390_trev with the G7 interstitial lag × 1.5 while glucose falls, sized on G7 MARD by rate of change (Garg 2022; LESSONS 391): 42 of 51, lows on the donors'; open as c390_trev. c390_trev — c384_sB with each sensor family's transient biases sized on its own donors' quiet reversals (G6 65% low first, G7 55%; LESSONS 390): 43 of 51, G6 step skew passing, every low statistic passing; failing G7 sd/mad and skew, acf_zero_min (LESSONS 385–389: no body lever moves it), sigma_disp, med_nonzero, and borderline Box-Cox λ / between-day / ac1. c384_sB — c382_gk25 with the sensors' noise-level wander (G6, G7) and G7 co-located error fitted to the donors' 5-min steps (LESSONS 384): 45 of 51, every low statistic passing with low depths on the donors', volatility clustering, ac1 and between-day share passing; failing G7 sd/mad, v_skew G6 / G7, acf_zero_min, sigma_disp, med_nonzero. c382_gk25 — c378_bpro with grazing at a quarter of its judged rate (`graze_keep` 0.25, LESSONS 382): unannounced labelled load 97.3 vs 94.7 g-eq/day, g-eq per entered gram 1.18 vs 1.19, 38 of 51, hourly RMS 6.2, circadian amplitude and minutes per low passing; P(reach 54) fails (p 0.039). c378_bpro — c376_miss with the TDD budget paying for protein glucose (`budget_pro`, LESSONS 378): mean 152.7 / TDD 38.75 / TIR 72.6 on the donors' (151.9 / 38.7 / 71.9), 34 of 51; t54 and P(reach 54) pass narrowly, minutes per low fails; 00–06 h −10 mg/dL. c376_miss — c374_pro3 with the donors' short missed Loop cycles (`missed_own`, LESSONS 377): 36 of 51, bg_mean 158.8 (p 0.045) now fails and minutes per low passes. c374_pro3 — c371_nofrel with protein glucose 0.3 g per g (LESSONS 373): 36 of 51, day / night and night CV passing, every low statistic passing, night trough halved (00–06 h −5 mg/dL), evenings on the donors', hourly RMS 8.1. c371_nofrel — c369_skip with no fixed night bump (`night_own` off) and the fat resistance absolute (`fat_rel` off), so the evening's own fat carries the night need (LESSONS 370): day / night insulin 2.02 and night CV 34.8 on the donors', dinners up +12–18 for 4.5 h, 3-h meal change +11.7 (donors +21), every low statistic passing, 35 of 51; open: 03–06 h 12–18 mg/dL under the donors', circadian_amp. c369_skip — c365_p2025 with each twin skipping breakfast on its donor's measured share of days (`skip_own`, LESSONS 368): lunches and dinners rise twice as far and stay up through 3 h, 3-h meal change +6.2 (donors +21), 35 of 51, every low statistic passing. c365_p2025 — c362_g6s with insulin action back at the lispro clamp fit (p2 0.025, LESSONS 365): 37 of 51, every low statistic passing. c362_g6s: c361_hq with G6 white noise 1.0 from the donors' measurement noise (LESSONS 362): 35 of 51, every low statistic passing. c361_hq: c360_cr065 with G6 / G7 low-range sensor noise refitted to their FDA tables (LESSONS 361): 35 of 51, every low statistic passing. c360_cr065: c359_csfp with counter-regulation refitted to the low depths (CRmax median 0.195, LESSONS 360): t54 and P(reach 54) pass, 33 of 51. c359_csfp: c358 with the per-donor carb sensitivity pooled over two rounds (LESSONS 359): 34 of 51. c358_csfgeq: c352_fat05 with each body's carb sensitivity set from its donor's measured meal response (`csf_geq`, LESSONS 358): 35 of 51, low-runners' day 6–11 mg/dL lower. c352_fat05: c346_st with fat-induced resistance starting 0.5 h after the meal (Laxminarayan 2015; LESSONS 352): 35 of 51. c346_st: c341_entwin with `slot_true` on by default (the donor's labelled morning load converted to grams, removing double-counted dawn rises; LESSONS 346): hourly profile RMS 7.7 mg/dL against the donors', night on the donors', 34 of 51. c341_entwin: c339_gecirc with each window's entry chance calibrated on the donor's entered grams (`entry_win`, LESSONS 341, 345): 36 of 51, evening entries and carb entries per day on the donors', day / night insulin 1.73 vs 2.0 fails. c339_gecirc: c338_slotv with circadian gastric emptying on by default (Goo 1987; 38 of 51, night level and 24-h amplitude on the donors'; LESSONS 339). c338_slotv: c331_strat with the meal-slot composition measured by Vetrani 2022 (LESSONS 338). c331_strat: each twin draws its donor's dosing strategy by the donor's share of autobolus days (`auto_day_share`, LESSONS 331; Loop then doses twins as it dosed their donors, automated total 1.04×); 37 of 51 under block scoring (LESSONS 330: donors scored one 13-day block at a time, `real_pilot_blocks.csv`). Before it c321_p2a — insulin disposal-action rate p2 0.04 (LESSONS 324): t54, p_reach54, CV, TIR and mean pass; 34 of 51 (38 re-scored). On c306_brz — Brazeau's size-dependent carb counting error on (LESSONS 304): TIR 72.4 vs 71.7, time > 180 and lows / day on the donors', 31 of 51, t54 0.09% vs 0.22%, CV 36.7 fails. On c305_k1 — κ median 1.0 from Best 1981 read in full (LESSONS 303; Pete: a sounder model may match fewer statistics), TIR 71.5 vs 71.7, mean / CV pass, 28 of 51, t54 0.09% vs 0.22% (lows under-read further). On c300_csfw0.5 — the body's carb sensitivity weighted halfway between the data branch and the settings (`csf_w` 0.5) while its ISF stays on the data (LESSONS 300); 32 of 51, p_reach54 on the donors', bg_mean 157 vs 151 now fails. Built on c289_split — carb entries split into meals and snacks as each donor does (LESSONS 280), and c287_wake's night alarm-wake chance from the donors' night lows (LESSONS 274), counter-regulation refitted (CRmax median 0.3, LESSONS 272), meal fast-emptying share 0.35 with per-meal SD 0.40, G7 white noise 1.8 (LESSONS 268–271), yardstick ISF × the body-model sensitivity fit (`fit_body --regression`), night need added on top of the day (`night_add`), delivered-shape basal need with the night level from steady
  nights, donor-MET exercise intensity with the C4 surge.

## Match targets

The primary test, kept in one place: **`docs/additive/MODEL_GUIDE.md` § 10** lists every scored row (51 statistics,
with the sensor-split rows), its tier and weight, the donors' value, the reference's value on both draws and the gap.
Runs are ranked by the weighted gap score (`score.py`, LESSONS 492). Tier 1 has weight 3: outcomes, what Loop sees, and
the activity response. Tier 2 has weight 2: dynamics, plus meal absorption, unlogged rises, falls and workouts
(LESSONS 494). Tier 3 has weight 1: the sensor fingerprint. The KS count is secondary. Update § 10's table when the
reference changes.

## Known limits of the current reference (read before using its numbers)

**Status (Pete 2026-10-20): usable with LoopEval.** The limits below are documented, not blocking. They are:
- twins of tight-control donors run high, and twins need 5–8% more insulin than their donors (LESSONS 445–456);
- night lows build toward dawn: 31% of lows fall at night, against the donors' 22% (LESSONS 438–441, 458);
- failing on both draws: G7 short-scale rows, acf_zero_min, sigma_disp, med_nonzero, ac1, day / night and Box-Cox λ
  (**read `ac1` against the independent-day null of −0.086, not 0**, and against **+0.118, not +0.18**: half the donors'
  persistence is their SETTINGS — a basal / ISF edit or a multi-day override persists by construction, and on day pairs
  free of both, the basal limb falls from +0.189 to +0.063 above null while the bolus limb stays at +0.166. A twin holding
  one era cannot and should not reproduce the rest. **CLOSED as a body target** (L 585): the twins carry +0.064 of the
  reproducible +0.118, the genuine remainder is day-level glucose persistence (donors +0.168 above null, twins +0.105,
  gap ~+0.06), and five mechanisms are null — the residual's day level, the life modulators with B3's own AR(1),
  everyday activity, `intake_rho` (carbs only) and `day_rho`, whose ceiling is **+0.02** of delivered-insulin persistence
  whatever ρ is, since the day factor is half of daily-mean SI variance and that series reaches delivered insulin at
  r −0.32. Closing it by amplitude would need a day-to-day SI CV near 25%, far outside the 6–15% clamp evidence; L 583–585)
  (LESSONS 457);
- **the shallow-low recovery gap is down to one named, unevidenced mechanism** (L 563): a glucose-dependent hepatic
  response below Gb, worth ~0.34 mg/kg/min at G 65. Insulin is ruled out (the twins carry LESS IOB at the nadir, 1.09 vs
  1.59 U, and still climb out slower), as are A9 and rescue behaviour. Bruce 2025 and Del Prato 1997 do NOT size it — both
  RAISE glucose above basal (they are A1b's and A1a's evidence); this needs a study that lowers glucose below basal at basal
  insulin in T1D, which only Mevorach 2000 approaches, under a hyperinsulinaemic clamp.
- **TDD, not bg_mean, is the diagnostic for a core sensitivity error** (L 577): `resid_m` is fitted to each donor's glucose
  level, so it absorbs core level errors — a potency deficit shows up as the insulin surplus, not as a level gap. Read
  `resid_m`'s size as what the core is missing. `si_norm` 1.0 + a level refit improves the mean score (0.372 vs 0.385),
  level and TIR on all three draws, and gives the LEAST DAMPED change response of any arm (t70 ratio 2.09 vs ad3's 3.32,
  L 577) — because resid_m does not scale with insulin. It hands back the TDD gain and some control-level heterogeneity.
  Awaiting Pete: the core carries how MUCH a person responds, resid_m sharpens WHO does. **It is bigger than one flag**:
  `si_norm` 0.92 stands in for the DISABLED life modulators, and those carry B3's day-to-day sensitivity persistence —
  whose absence was thought to explain `ac1` — **tested and refuted** (L 582): the package (modulators on + `si_norm` 1.0 +
  refit) leaves `ac1` unmoved, because `day_rho` is 0 so it restores day-to-day VARIATION without PERSISTENCE, and it scores
  0.386 against `si_norm` 1.0 alone at 0.372. It does give the best glucose level of any arm (bg_mean gap 0.015 / 0.094 /
  0.019). The si_norm choice is therefore unchanged and the modulators are a separate question.
  The trade is roughly LINEAR, so the
  intermediate (0.96) does not dominate and tuning the value will not settle it (L 577); 1.0 is the principled end, since
  `si_norm` only stands in for life modulators that are off in this reference and should be 1.0 if they are switched on.
- **superseded by L 577** (L 577): `si_norm` 1.0 (undoing the deliberate cohort-wide 8% sensitivity cut)
  improves TDD and TIR on all three draws, confirming that the post-meal potency deficit and the twins' 5–8% insulin surplus
  share one cause. It drops the glucose level because `resid_m` was fitted at 0.92, so it needs `lvl_resid.py` re-run after
  it (three rounds per draw, L 525) before it can be judged. One cause behind three documented limits.
- **the shallow post-meal trough is 72% potency, not dose** (L 575): after a meal peak the twins spend nearly the donors'
  insulin (1.78 against 1.98 U over 90 min) but fall 41 against 57 mg/dL — 80% of the donors' mg/dL per unit. Appearance
  (A10c), A12b, and κ (an 80% steepening leaves the fall unmoved and lowers the peak) are all ruled out, as are dose and Loop compensation
  (L 575: raising ppr_a made Loop spend LESS, not more). At MATCHED spend — ad0 and the donors both 1.98 U — the twins fall
  43 against 57, a pure 75% potency gap. Every GLUCOSE-localised lever lowers the peak instead of deepening the fall, so the
  effect must be TIME-localised — but p2 (action timing) is unmoved too, so EVERY candidate of L 512's list is eliminated.
  The sensor adds 24-35% of the apparent fall on BOTH sides (G7 most), so it inflates the level but NOT the gap: family-matched
  the deficit is 9-16 mg/dL in CGM terms and 10-13 in estimated truth terms, so the nulls are genuine (L 575). Always split
  this statistic by sensor family - G7 amplifies ~3x G6 on one draw and the family mixes differ. **The deficit is in the
  fall / rise RATIO: donors 0.89, every twin arm 0.70-0.78 whatever is changed** (L 575). Appearance scale, emptying speed,
  Vmax, uptake glucose-dependence, insulin-action timing, post-meal sensitivity and dose are all ratio-preserving. The
  missing term must act asymmetrically in TIME around the peak and not be mean-preserving. Read the RATIO, not the fall.
  The incretin / portal routes are set aside analytically (they point the wrong way in T1D, L 575), so start from measurement:
  the donors' own ratio by meal size, clock hour, bolus timing and insulin type. **It tracks BOLUS TIMING hard**: 0.90 when
  pre-bolused 20-60 min, 0.79 at the meal, 0.68 late, 0.62 unbolused — a spread of 0.28 against the twins' 0.11-0.19 deficit
  (L 575). Stratified, the gap is **essentially all physiology**: the twins' unbolused share is 5-6% against the donors' 3%
  (by `bolus_requests`; a delivered-stream threshold over-counted it as 11-13%), contributing ~0.004 of the 0.11-0.16 gap.
  The within-stratum residual at the meal is 0.71 / 0.67 against 0.79, so a ratio-breaking mechanism is genuinely needed —
  but the sensor amplifies the FALL (+27%) far more than the RISE (+7%) and more steeply the faster the fall, so the CGM
  comparison exaggerates the gap by an amount only donor truth could pin down. Size nothing to the CGM number (L 575).
- **Never detect boluses in a sim run from the delivered stream by threshold** — use `truth["bolus_requests"]` (L 575).
- **the excess lows are shallow ones that linger, and counter-regulation cannot fix them** (L 559, 560): at a 60–70 nadir
  the twins rise +21 in 30 min against the donors' +26 and dwell 15 min against 10. A9 can supply at most 2.4 mg/dL over
  that window, so the lever is the sub-basal shape of glucose disposal (A5's M(G) / κ below basal, or A1c brain sparing),
  not A9. Deep lows already rebound harder than the donors', so rescue behaviour is not it either.
- **the excess lows are the binding limit on TIR** (L 558): the meal tail is calibrated and CV is on the donors', so
  as the spread grows the twins' extra time below range (t70 1.97 / 2.16 vs 1.60) is what holds TIR at 68.9 / 70.2 against
  71.9. Work the low side next, not the meal shape.
- response to a settings change is damped (mean half the field's, lows 4–8× under) and twins of tight donors are not
  tight, so control-level heterogeneity is wrong in the tight group (frontier handoff 2026-10-24, LESSONS 493, 503).

**Score close calls on THREE draws — seed0 1000, 5000 and 9000 — and read the mean (L 567).** Draws 2 and 3 agree with each
other while draw 1 is the reference lineage's own development draw and scores anomalously well on it (ad2: 0.340 vs 0.444 /
0.430), so a candidate that gives up draw-1 fit looks worse than it is. Where the three disagree, discount 1000.
The two-draw rule (LESSONS 444) still rejects noise, but with 1000 as one of the two it also protects that fit.

Measured like for like against the donors (LESSONS 282–299); read a candidate's result against them.

- **Lows run short** (c395_joint: t54 0.074% vs 0.190%, P(reach 54) 0.14 vs 0.21, LESSONS 393). c384–c391 matched them partly through false sensor lows. Earlier: t54 0.147% vs 0.215%, lows 0.83 vs 1.08 / day. The missing part is the early low after a
  bolused meal from a steady start (< 70 within 60 min: 0.3% vs 3.3% of flat-start meals at 100–140 mg/dL) and a slower
  fall after any peak (matched-height fall in the hour after the maximum −26 vs −37 mg/dL). Treat absolute
  hypoglycaemia as a lower bound; rank candidates on deltas.
- **Faster insulin absorption removes lows under Loop.** Heat (B15) and posture-off both lower hypo-day odds (paired OR
  0.59–0.78). A candidate that speeds absorption will read safer here than the evidence may support.
- **The insulin response itself matches**: pooled lone corrections per U per ISF equal the donors' at 60–180 min
  (LESSONS 294).
- **Short-scale shape is now fitted on the sensor side** (LESSONS 384): the donors' fast 5-min moves could be body or
  co-located sensor error (LESSONS 299); the sensor's noise wander was fitted to them, so a candidate that only changes
  the body's fast motion will read against a sensor that already carries it. G6 skew, the ACF zero crossing and
  volatility dispersion still differ.
- **Meals still come down sooner than the donors'**: 3-h meal change +11.7 vs +21 (was +2 before breakfast skipping, the dinner fat carrying the night, LESSONS 368–370). Loop's delivery at each glucose band matches the donors' (LESSONS 368); adding meal glucose by carb sensitivity, slow share or protein is answered at the meal (LESSONS 366–367). The hourly profile runs 5 mg/dL low at 00–06 h and 8 high at 06–12 h (basal-need shape, LESSONS 371, 373); TDD day-to-day persistence (ac1) is ~0 against the donors' 0.09. Candidates acting after meals are read here as a second opinion.
- **Night-to-night insulin varies less** (night CV 29 vs 36) and does not follow evening entries as the donors' does
  (LESSONS 288–289).
- **The exercise side is limited by a missing measurement, not a missing mechanism** (L 551, 556, 557, 564): per-person
  aerobic capacity is a prior (METmax lnN(9, 0.25)), and without it C1 / C2's size at moderate intensity cannot be settled —
  the 6–8 MET band is still −13 against the donors' −21.5. C4's threshold and size ARE settled (8 absolute METs, 28
  mg/kg/min): the ≥ 8 MET band reads +1.8 against the donors' +1.2 once `ex_headroom` gives it enough bouts (L 554).
  The 6–8 shortfall is now understood as a REGIME SWITCH the smooth terms cannot make (L 565): the donors fall deepest at
  6–8 METs and rise at ≥ 8, so any setting that deepens one deepens the other. It needs a form change (a steeper anaerobic
  share), not a parameter.
- Off-by-default experiments with their verdicts: `ov_dur_own` (each override class's own log-duration SD, 0.70-0.78,
  instead of the fixed 0.6: score-neutral at mean 0.374 against 0.372, slightly worse on change prediction, and it
  halves the share of twins who never override — 42% to 27% against the donors' 42% — so better explained is not
  enough here, L 586), `day_rho` 0.45 (B3's intrinsic day-level sensitivity as AR(1):
  level on score and its delivered-insulin persistence ceiling is +0.02, a fifth of what `ac1` would need, L 585),
  `act_rho` 0.4 (day-to-day persistence of everyday activity: raises CARB persistence +0.04, no effect on insulin or
  `ac1`, L 584), `resid_day_ar` 0.35 (the residual's day level as AR(1):
  variance-preserving and level on score, but `ac1` does not move at all — TDD's day-to-day persistence is driven by eating
  and dosing, not by the residual, so the route to it is day-to-day persistence in EATING, L 581), `meal_wave2` (A10c delayed gastric pulse: preserves the peak where a slow
  tail destroys it and lifts the second rise, but the trough is unmoved — it is not limited by appearance, L 571),
  `meal_slow` 0.30 (A10's slow share cannot make the second wave — it lowers
  the peak instead of deepening the trough, because kmin 0.008 dribbles rather than pulsing, L 571), `resid_meal` (redistributing the residual across the meal cycle: null, and
  rise-skewed variance cannot reach a one-sided target, L 568), `resid_drop_p` (moves entry_fast_fall on all three draws but
  spends ~5 points of the nearly-closed meal tail to buy ~2.4 of it, L 568), `ex_abs` (C1 keyed to absolute work rate: the 6–8 MET band improves on both
  draws, −14 → −18 against the donors' −21.5, but the ≥ 8 band goes negative where the donors rise; the two bands trade, L 565),
  `ex_headroom` 1.5 (restores the session-intensity tail and validates C4's
  size of 28 — the ≥ 8 MET band reads +1.8 vs the donors' +1.2 at n 40; costs score on both draws, use it for
  exercise-focused work, L 554), `ge_spare` (A1c alone: buys t70 1.97 / 2.16 → 1.67 / 1.71 and TIR on both
  draws, costs the share of lows reaching 54, 0.212 → ~0.17, which A9 cannot refit; awaiting Pete, L 561–562), `ge_split` (glucose effectiveness from named parts; too many lows, and superseded by the C4 threshold fix on change prediction too, L 548, 555), `ex_dur_cap` (the cap without the METmax fit — leaves almost no hard session, L 554), `prof_deliv` off, `unent_light`, `unent_split`, `ge_var` off,
  `entry_size_b`, `heat_a`, posture off, `kappa_ins` (needs Best 1981's insulin levels), G7 common error 1.0.

## Analysis traps (each cost a session)

- **`truth["sent_overrides"]` is the REACTIVE override class only** (world.py:728). The person's PLANNED overrides
  reach the controller through `loopeval_io._override_windows`, which writes `beh.overrides` into the twin's own
  synthetic `therapy.json` — the same field a donor measurement reads, so compare there. Counting the pickle field
  against a donor record overstated the gap 4× (L 586). A donor override record under 5 min is a cancellation, not
  therapy: left in the fit it reads as a log-duration SD of 2.01 instead of 0.83.

- **A donor statistic must be measured over the twins' OWN window length.** A lag-1 autocorrelation over a 128-day donor
  record contains the drift between blocks and reads 3–4× the within-13-day value (TDD +0.251 against +0.085); chasing
  the long-record figure sent five mechanisms after a target that did not exist (L 585). Block the donor series to the
  twins' length first, and where the statistic can be moved by the donor's SETTINGS, split it by whether a settings
  change or override falls on those days (`resid_tools/tdd_clean_ac.py`) — a twin holds one era and runs no overrides.

- **Donor carb entries are keyed `grams` in `carbs.json`, not `carbInput`** — the wrong key gives 0 g for every entry, and
  any size filter then drops them all with no error (L 571).

- **A `score --detail` log's first arm is the first ARGUMENT, not the donors**, so fixed awk column indices are off by one
  arm and silently report the wrong arm's numbers (it happened three times on 2026-11-01). Read them with
  `resid_tools/score_read.py`, which keys on the header names.

- **`trace.json`'s md5 is NOT an identity check.** Two identical invocations of the same frozen code produce
  byte-different `trace.json` (key order and float formatting) with content and trajectory identical. Compare
  `truth.pkl`'s `truth.bg` series instead — that IS bit-stable, and it is stable across `--n` and `--par` too, since
  every person is drawn and seeded from `seed0 + i` alone. An md5 mismatch "proved" a reversal had failed (L 586).

- **A new template column needs adding to `person.BEHAVIOR_COLS`** — that allowlist is what reaches the person as
  `traits["template_rates"]`, so a column the templates carry and `sample_behavior_traits` reads is silently absent
  without it, and the arm runs as its own control (`ov_dur_own` scored bit-identical to its `--disable` control
  before this, L 586). Same signature as the `--enable k=v` trap: check a built person's trait, not the CSV.

- **An arm rerun into an existing output dir returns the CACHED previous run** (`v0… cached` in its log), so a fixed
  arm can come back byte-identical to the broken one it replaces. Use a fresh arm name, or clear the dir.
- **A numeric override passed to `--enable` is a switch named `k=v`, so the component keeps its default and the arm
  silently runs as its own control** (L 554). Numeric values go in `--set`; `cohort.py` now rejects `=` in `--enable`.
  An arm that reproduces its control exactly is the signature — check `cohort.json` in the run dir.

- `truth.pkl` `bolus_requests`: **+ = a ratio of Loop's recommendation, − = absolute units**. Count user boluses with
  `f > 0 or f <= -0.05`; `f > 0` drops every hand-dialled bolus.
- `meals_labeled.csv` onsets are datetimes from **world.EPOCH** (2026-01-05); convert as `(onset − EPOCH)` minutes, not
  from the first onset's midnight.
- **Like for like**: donors only show carb entries and labeled pulses — never compare them with the sim's true eating
  events. Donor ice steps carry a bolus from the start of its 5-min step.
- The templates' original `isf_true` was the 1800 rule on TDD, not a per-person fit (now the ICE yardstick, the TDD value
  kept as `isf_true_tdd`). Closed-loop data attenuates any insulin-effect estimate (Loop answers the glucose's own
  drivers): per-person fits carry the ranking, one cohort factor sets the level.

## Standing cautions

- **Statistical resemblance is the test, not the goal of a single knob.** Calibrate a component
  from its own evidence first; use cohort statistics to find what is missing, not to tune a
  free parameter until a number matches (see memory: *understand before patching*).
- **Compare like with like**: split every cohort comparison by sensor family (eda lesson 33) and
  by dosing strategy (lesson 9); compute statistics with eda's own functions (`traits.block_features`).
- **Review the existing components before adding another** (Pete 2026-10-18). Every component fitted to an emergent
  target (meal EGP nadir, low depths, meal outcomes, realized behaviour rates) drifts as other components change. After
  any adopted change, run `python -m loopeval_analysis.patient_sim.review <run>` against the donor targets
  (`review ... donors` builds them with the same code) and refit what drifted, each on its own evidence, before testing
  the next new component.
- **Lows are where simulators fail** (UVA S2008, replay validations): counter-regulation, rescue
  behavior and sensor bias in the low range get explicit evidence, and time-below results are
  reported with the uncertainty of those components.
