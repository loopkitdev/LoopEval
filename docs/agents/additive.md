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
| `docs/additive/evidence/` | Literature + measured-evidence notes per area (factor catalog, physiology, life factors, sensor & device, behavior, LoopEval findings). |
| `docs/additive/COMPONENTS.md` | The component registry: every factor, its model form, parameters, evidence and status. |
| `docs/additive/LESSONS.md` | This role's lessons file. |
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
- **The patient is independent of the controller** (2026-10-18): controller configuration (RC mode, GBAF, strategy) is
  never a patient trait; validation runs give each person their donor's deployed controller (`--enable rc_own`), the
  code default stays stock.
- **No mystery terms**: a divergence is closed by fixing or adding a named, evidenced component, never by a fitted noise
  or offset term.
- **Publishing**: updates to this model are self-approved (merge to `main`, move the board task to Done); changes to
  general LoopEval code still go to Pete first.

## Running and comparing a cohort

- **Reference run**: `python -m loopeval_analysis.patient_sim.cohort --n 112 --days 14 --templates
  templates_pilot_logs.csv --enable rc_own --out runs/<arm>` on gamepc from frozen code (`git archive <sha> analysis` into
  `~/frozen/<sha>`, launched through an ssh held in a Mac `tmux -L fast` session). Templates live outside the repo
  (`~/.loop-eval/runs/2026-10-15-additive-templates/`) and must be copied to gamepc after every change; template columns
  are built by `templates.py` (`add_isf_yardstick`, `add_insulin_from_iob`, `add_delivered_profile`, …).
- **Scoring**: `compare_runs.py` (eda's 51 statistics, KS against the donors; see Match targets below), `review.py` (each component against its own
  target), plus the measure scripts beside the run. Arms of a neutral change scatter 27–31 matched: read differences
  inside that band as noise.
- **Current reference** (2026-10-19): c371_nofrel — c369_skip with no fixed night bump (`night_own` off) and the fat resistance absolute (`fat_rel` off), so the evening's own fat carries the night need (LESSONS 370): day / night insulin 2.02 and night CV 34.8 on the donors', dinners up +12–18 for 4.5 h, 3-h meal change +11.7 (donors +21), every low statistic passing, 35 of 51; open: 03–06 h 12–18 mg/dL under the donors', circadian_amp. c369_skip — c365_p2025 with each twin skipping breakfast on its donor's measured share of days (`skip_own`, LESSONS 368): lunches and dinners rise twice as far and stay up through 3 h, 3-h meal change +6.2 (donors +21), 35 of 51, every low statistic passing. c365_p2025 — c362_g6s with insulin action back at the lispro clamp fit (p2 0.025, LESSONS 365): 37 of 51, every low statistic passing. c362_g6s: c361_hq with G6 white noise 1.0 from the donors' measurement noise (LESSONS 362): 35 of 51, every low statistic passing. c361_hq: c360_cr065 with G6 / G7 low-range sensor noise refitted to their FDA tables (LESSONS 361): 35 of 51, every low statistic passing. c360_cr065: c359_csfp with counter-regulation refitted to the low depths (CRmax median 0.195, LESSONS 360): t54 and P(reach 54) pass, 33 of 51. c359_csfp: c358 with the per-donor carb sensitivity pooled over two rounds (LESSONS 359): 34 of 51. c358_csfgeq: c352_fat05 with each body's carb sensitivity set from its donor's measured meal response (`csf_geq`, LESSONS 358): 35 of 51, low-runners' day 6–11 mg/dL lower. c352_fat05: c346_st with fat-induced resistance starting 0.5 h after the meal (Laxminarayan 2015; LESSONS 352): 35 of 51. c346_st: c341_entwin with `slot_true` on by default (the donor's labelled morning load converted to grams, removing double-counted dawn rises; LESSONS 346): hourly profile RMS 7.7 mg/dL against the donors', night on the donors', 34 of 51. c341_entwin: c339_gecirc with each window's entry chance calibrated on the donor's entered grams (`entry_win`, LESSONS 341, 345): 36 of 51, evening entries and carb entries per day on the donors', day / night insulin 1.73 vs 2.0 fails. c339_gecirc: c338_slotv with circadian gastric emptying on by default (Goo 1987; 38 of 51, night level and 24-h amplitude on the donors'; LESSONS 339). c338_slotv: c331_strat with the meal-slot composition measured by Vetrani 2022 (LESSONS 338). c331_strat: each twin draws its donor's dosing strategy by the donor's share of autobolus days (`auto_day_share`, LESSONS 331; Loop then doses twins as it dosed their donors, automated total 1.04×); 37 of 51 under block scoring (LESSONS 330: donors scored one 13-day block at a time, `real_pilot_blocks.csv`). Before it c321_p2a — insulin disposal-action rate p2 0.04 (LESSONS 324): t54, p_reach54, CV, TIR and mean pass; 34 of 51 (38 re-scored). On c306_brz — Brazeau's size-dependent carb counting error on (LESSONS 304): TIR 72.4 vs 71.7, time > 180 and lows / day on the donors', 31 of 51, t54 0.09% vs 0.22%, CV 36.7 fails. On c305_k1 — κ median 1.0 from Best 1981 read in full (LESSONS 303; Pete: a sounder model may match fewer statistics), TIR 71.5 vs 71.7, mean / CV pass, 28 of 51, t54 0.09% vs 0.22% (lows under-read further). On c300_csfw0.5 — the body's carb sensitivity weighted halfway between the data branch and the settings (`csf_w` 0.5) while its ISF stays on the data (LESSONS 300); 32 of 51, p_reach54 on the donors', bg_mean 157 vs 151 now fails. Built on c289_split — carb entries split into meals and snacks as each donor does (LESSONS 280), and c287_wake's night alarm-wake chance from the donors' night lows (LESSONS 274), counter-regulation refitted (CRmax median 0.3, LESSONS 272), meal fast-emptying share 0.35 with per-meal SD 0.40, G7 white noise 1.8 (LESSONS 268–271), yardstick ISF × the body-model sensitivity fit (`fit_body --regression`), night need added on top of the day (`night_add`), delivered-shape basal need with the night level from steady
  nights, donor-MET exercise intensity with the C4 surge.

## Match targets: eda's statistics

The goal's primary test. `validate.py` scores every simulated person with the eda study's own functions
(`traits.block_features` on the reported CGM, `delivery.py` on the delivered insulin, ice's low-event definitions) and
compares the distribution across people with the donors' (206 pilot donors) by a two-sample KS test, per sensor family
where the statistic depends on the instrument (eda lesson 33). Each cohort run writes `compare_pilot.csv`;
`python -m loopeval_analysis.patient_sim.compare_runs RUN_A RUN_B` sets two runs side by side. **Matched = KS p > 0.05** against one 13-day block per donor (median p over 40 draws, LESSONS 330);
51 rows (37 statistics, 7 of them split by G6 / G7 / Libre 3).** Status at the reference c284 (donor p50 / sim p50):

| Area | Statistic | What it measures | c284 |
|---|---|---|---|
| Level and spread | `bg_mean`, `bg_cv`, `bg_skew`, `tir`, `t70`, `t180` | mean, CV, skew, time in 70–180, < 70, > 180 | pass (CV 34.8 / 35.2) |
| | `boxcox_lambda` | distribution shape | fail |
| Lows | `t54`, `lows_per_day`, `p_reach54`, `min_below70` | time < 54, crossings below 70 per day, share reaching 54, minutes per low | fail (0.22 / 0.09%; 1.08 / 0.75 per day) |
| Short-scale motion (per sensor) | `v_sd`, `sd_over_mad`, `v_kurtosis`, `v_skew`, `hurst_short`, `sigma_meas`, `acf_min` | 5-min velocity spread, tails and asymmetry, short persistence, measurement noise, ACF minimum | Libre 3 all pass, G6 most pass; G7 only `sigma_meas` passes (v_sd 7.02 / 6.56, kurtosis 2.52 / 1.90: the large 5-min moves, LESSONS 268) |
| Long-scale structure | `hurst_long`, `wear` | long-range persistence, sensor coverage | pass |
| | `acf_zero_min`, `vol_cluster_60m`, `sigma_disp`, `between_day_frac`, `circadian_amp` | ACF zero crossing, volatility clustering, dispersion, between-day share, 24-h amplitude per person | fail |
| Insulin delivered | `tdd`, `zero_frac`, `p99`, `conc1`, `day_night` | daily total, zero-delivery share, peak, concentration, day / night split | pass (day / night 2.06 / 1.90) |
| | `tdd_cv`, `med_nonzero`, `ac1`, `night_cv` | day-to-day CV and autocorrelation, typical delivery, night-to-night CV | fail |
| Behaviour | `carb_entries_per_day`, `user_boluses_per_day`, `manual_u_day` | entries, user boluses, hand-dosed units | pass |

c284: 29 of 51; c285_sd40 31; c286_cr06 32 (low depths on the donors', LESSONS 272); c287_wake 30 (night low duration on the donors', LESSONS 274) (G7 kurtosis, volatility clustering, lows/day and TDD CV now pass; bg_skew and hurst_long now fail, LESSONS 271). Neutral changes move the count within 27–31; read single-statistic changes against that band, and check
the lows by dosing strategy (temp-basal vs automatic-bolus twins against their own donors) beside the cohort count.

## Known limits of the current reference (read before using its numbers)

Measured like for like against the donors (LESSONS 282–299); read a candidate's result against them.

- **Lows run a little short.** t54 0.147% vs 0.215% (passes KS since p2 0.04, LESSONS 324), lows 0.83 vs 1.08 / day. The missing part is the early low after a
  bolused meal from a steady start (< 70 within 60 min: 0.3% vs 3.3% of flat-start meals at 100–140 mg/dL) and a slower
  fall after any peak (matched-height fall in the hour after the maximum −26 vs −37 mg/dL). Treat absolute
  hypoglycaemia as a lower bound; rank candidates on deltas.
- **Faster insulin absorption removes lows under Loop.** Heat (B15) and posture-off both lower hypo-day odds (paired OR
  0.59–0.78). A candidate that speeds absorption will read safer here than the evidence may support.
- **The insulin response itself matches**: pooled lone corrections per U per ISF equal the donors' at 60–180 min
  (LESSONS 294).
- **Short-scale shape is partly unresolvable**: the donors' fast 5-min moves could be body or co-located sensor error;
  the simulated sensor pair matches the one real paired record (LESSONS 299). Do not tune the sensor to CGM shape.
- **Real meals keep counteracting for 1–3 h after the bolus** (ICE above pre-meal at 120–180 min ~2× the twins'; 3-h change +21 vs ~−2), with Loop's COB, IOB and the insulin effect matched (LESSONS 313–319); no evidenced component reproduces it yet. Real lunches and dinners rise slowly to ~4 h (Vetrani 2022); the twins' fall back by 2–3 h with intake, entries, meal-time and post-meal insulin and labelled load per gram all matched (LESSONS 338–348); gut speed, composition, liver suppression, activity, glucose effectiveness and κ each fail to restore it (LESSONS 342–350). Candidates acting after meals are read here as a second opinion.
- **Night-to-night insulin varies less** (night CV 29 vs 36) and does not follow evening entries as the donors' does
  (LESSONS 288–289).
- Off-by-default experiments with their verdicts: `prof_deliv` off, `unent_light`, `unent_split`, `ge_var` off,
  `entry_size_b`, `heat_a`, posture off, `kappa_ins` (needs Best 1981's insulin levels), G7 common error 1.0.

## Analysis traps (each cost a session)

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
