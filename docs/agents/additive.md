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
  general LoopEval code still go to Pete first. **Check the submodule pointer before every publish** — `git diff --cached
  --submodule` must show no `LoopAlgorithm` pointer change you did not mean, and the commit should build in a fresh
  worktree after `git submodule update`. A docs-only additive commit moved it back and broke clean checkouts of `main`
  (1d916cfa, restored by trio in 7668fbde) — the second such break on the trunk.

## Running and comparing a cohort

- **Reference run**: `python -m loopeval_analysis.patient_sim.cohort --n 112 --days 14 --templates
  templates_pilot_logs.csv --enable rc_own --out runs/<arm>`. What the step needs, whatever the hardware:
  **frozen code** (`git archive <sha> analysis` unpacked into a tree outside the checkout, so a later edit cannot change
  a running arm — `arm2.py` honours `ARM_TREE`); a host with enough cores for `--par`, and a session that survives a
  disconnect if the arm is launched remotely; and the **templates directory beside that tree**, since templates live
  outside the repo (`~/.loop-eval/runs/2026-10-15-additive-templates/`) and must be re-copied to a remote host after
  every change. Template columns are built by `templates.py` (`add_isf_yardstick`, `add_insulin_from_iob`,
  `add_delivered_profile`, …). The host this project actually uses, and how its long-running sessions are held, are
  recorded in the git-ignored `PRIVATE.md`.
- **Compute etiquette on a shared machine** (loopeval relaying for Pete, 2026-11-02): run CPU work **only through
  the jobq**, which is reniced to 10 so queued jobs inherit it, and cap each job at **8 parallel simulations** —
  `arm2.py`'s third argument and `cohort.py --par`, both of which are one simulation per worker. Nothing heavy
  outside the queue. Pete needs headroom for an iOS Simulator. Measured on job 172 for reference: 8 concurrent
  `simulate` processes, all at nice 10, ~4.2 of 18 cores including the plant servers.
- **Scoring**: `compare_runs.py` (eda's 51 statistics, KS against the donors; see Match targets below), `review.py` (each component against its own
  target), plus the measure scripts beside the run. A different draw of people (seed0) moves the count by up to 6 (LESSONS 444): score an arm whose
  effect is within that scatter on two draws (seed0 1000 and 5000) before adopting it.
- **Exercise-faithful configuration** (L 565; not the default, because every step toward it costs the weighted score):
  `--enable ex_abs --set ex_headroom=1.5,ex_surge_width=0.75` on the reference. It reproduces C4's own by-METs table —
  the ≥ 8 MET band reads +0.9 against the donors' +1.2 where the band has enough bouts — against the reference's +12.8 / −5.1.
  Use it whenever the response to a workout matters; the reference keeps the score-optimal settings.
- **rf2 on the prediction half: response SIZE replicated on two pools; RANKING consistent but not established**
  (L 612, 614, 616) — pooled by Fisher z over the 643 well-conditioned events (pilot + e; the x pool excluded for a
  NEGATIVE field t70 response), rf2 leads on all three correlations (mean 0.326 against 0.265, TIR 0.165 against
  0.132, t70 0.187 against 0.157) at 0.5-1.2 SE each: against ov0 it is better on all four
  response ratios and all three correlations — mean 1.35 [1.04, 1.69] against 1.60, TIR 1.27 against 1.37, **t70 1.14
  against 1.43** (the field is 1.0), rho 0.33 / 0.16 / 0.17 against 0.26 / 0.13 / 0.15 — and starts nearer the field's
  pre-edit level (+3.3 against +5.4). No single comparison is individually significant; the consistency across seven
  is. Caveat: t54 goes 0.91 -> 0.58, the one row moving away from the field. Ratios are pool-specific (the e pool's
  field t70 response is +2.00 against the pilot pool's +4.46) — quote them with their pool. **The x pool (152 events)
  replicates the ratio ordering but reverses the correlation ordering, and is poorly conditioned for change
  questions — its field responses are a third of the e pool's and its field t70 response is NEGATIVE (−0.57), so
  prefer the e pool and report a pool's FIELD response before using it (L 614).**

- **Judge adoptions on PAIRED per-person differences** (L 610): on the sum of |median(twin − its own donor)| over
  TIR, bg_mean, t70, t54 and TDD, **rf2 scores 2.28 against ov0's 5.36 — a 57% improvement**, where the cohort score
  called the same change level (0.372 → 0.370). Every rejection of 2026-11-01 holds on this instrument
  (`cr_tau_off` 2.34, joint fit 2.40, `sg_h_lo` 2.93/3.57, `pro_g_own` 5.41), and `unl_mult` 0.70 + refit is confirmed
  as the only real TDD lever (paired TDD +0.40 against +1.49) at the cost of the level (bg_mean −1.63).

- **The state docs drift from the code and my own checks cannot see it** (L 666). LESSONS and this overlay
  are written when a result lands, so they are right about results; COMPONENTS and MODEL_GUIDE describe state,
  which changes with no result to hang a note on. An outside read against the code found eight defects in one
  session — `ppr_a` 0.4 against a live 0.6, `day` re-enabled at ov0, a dead DOI, and five of the nine ablation
  switches undocumented. There is now an external instrument for it, `langerhans/tools/audit_status.py` in the
  AdventuresInDiabetes tree, which diffs a run's flags against the code's defaults and exits non-zero on
  disagreement; **run it when the reference changes.** And verify any claim about this model against the call
  site even when a peer is confident and their conclusion is right — in the same exchange a correct verdict
  came with a wrong reason that would have broken their audit, and I nearly recorded two live switches as dead
  because my grep matched `self.enable[name]` and they are read as `enable.get(name, default)`.

- **Read the reference's configuration from a run's own `cohort.json`, never from the prose** (L 657, 665,
  **679**): three switches have now differed silently from what the docs implied — `act_frag`, `day` from ov0
  onward, and **`day` on the WHOLE e pool, which runs it OFF while the cohort reference runs it ON (L 679)**.
  Arm-to-arm comparisons on that pool are still sound (all nine arms share it, so it is a control).
  **TESTED as job 191 (`dye1`) against a rule fixed in advance, and the answer is split by row (L 683):
  the MEAN ratio is unmoved (1.35 -> 1.34), so L 677's 0.68, L 680's 0.63 [0.39, 0.98] and L 678's
  arithmetic stand as quoted and the two halves keep their own configurations — but TIR goes 1.30 -> 1.11,
  t70 1.09 -> 1.42, t54 0.56 -> 0.93 and all three rankings get worse.** So quote `day`'s state beside any
  response ratio from this pool: "TIR 1.30, t70 1.09" describes a `day`-OFF body while the cohort reference
  runs `day` ON, where they are 1.11 and 1.42. My rule named only the mean row, which passed while the rows
  it was not watching moved more than most adopted arms — a single-row rule on a multi-row instrument can
  pass while the thing it protects changes underneath it. rf2 is, in
  full: templates `templates_pilot_resid_rf1.csv`; `--enable rc_own,night_pro,uls,resid,site_clock`;
  `--disable stress,illness,menstrual,steroid,act_frag`; `--set ex_sat=0.1,p_log_pro=0.12,p_log_rescue=0.12,`
  `graze_keep=0.0,flow_sd=0.0,resid_skew=0.7,resid_mult=0.0,si_norm=0.92`. Everything else runs its code
  default — which notably leaves **`day`, `circadian`, `dawn`, `sleep`, `gh` and `alcohol` ON** and `ppr_a` at
  **0.6** (not the 0.4 two docs carried until L 665).
- **Current reference** (2026-11-01): **rf2** (runs/2026-10-31-additive-gesplit; templates
  `templates_pilot_resid_rf1.csv`, `--set resid_mult=0.0`) — ov0 with the residual's DYNAMIC part off, keeping only its
  per-person level `resid_m` (L 592). Score **0.328 / 0.366 / 0.404** on the corrected donor meal labels (L 695; the
  stale-label pair was 0.332 / 0.371 / 0.406), mean **0.370** against ov0's 0.372 on the labels both were scored with — level —
  with **tier 1 better on all three draws** (0.135 / 0.209 / 0.178 against 0.178 / 0.218 / 0.197), twin-donor rho
  better on five of six outcome rows (TIR 0.815 / 0.830, bg_mean 0.885 / 0.896, t70 0.631 / 0.484, t54 0.526, bg_cv
  0.616), and the **t70 change response 3.51 -> 2.17 with its ranking +0.22 -> +0.34**, both the best of any arm. The
  dynamic residual was adopted for per-person spread and was doing the opposite, while contributing almost nothing to
  the volatility rows (bg_cv, sigma_disp, vol_cluster_60m all level without it). Costs: TDD a little worse on every
  draw, and draw 2 keeps a level drift the refit does not fully remove. Revert with `--set resid_mult=0.6` and the
  `ov1` templates.
- **Previous reference** **ov0** (runs/2026-10-31-additive-gesplit; templates
  `templates_pilot_resid_ov1.csv`) — ad3 with each Temporary Override class's duration fitted over the windows the
  model can actually produce, **plus, unrecorded until L 665, the `day` modulator coming back ON** (ad3 disabled
  it, ov0 does not, and it defaults to True) — **separated as job 178 and the gain is the override fit (L 668)**:
  rf2 with `--disable day` is inside the 0.01 floor on score (0.309 -> 0.313, 0.357 -> 0.349, split in sign) and on
  tier 2 (0.423 -> 0.427, 0.449 -> 0.452), with every pre-registered row landing on B3's own arithmetic — basal
  limb within-13d CV 0.170 -> 0.168 against a computed 0.168, `tdd_cv` and `between_day_frac` flat, the structure
  function unmoved, TDD split in sign at under half the 1.51 U/day draw sd. Tier 2's sign IS consistently worse with
  `day` off (0.004 / 0.003) at a twelfth of the gain it would have to explain, so `day` is small, not zero. The
  paired instrument improves (3.040 -> 2.946, 2.568 -> 1.985) almost entirely on TDD, which is the level-mediated
  row of L 604 / 629 on an unrefit arm, so it is not a gain — and `day` is evidenced, so it stays ON either way. A donor record under 5 min is a cancellation (the ETL keeps an edit-version per change),
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
- **(t70 / excess shallow lows REMOVED as a limit, L 607: bias −0.004 at five draws.)**
- twins of tight-control donors run high, and twins need **3.5–4.4%** more insulin than their donors — **measured
  paired against each twin's own donor on the current reference (L 598): +1.40 / +1.40 / +1.67 U/day at a matched
  glucose level, where the long-standing "5–8%" and a cohort-median "+10%" both overstate it.** Basal withholding is
  not the cause (delivered / scheduled basal 0.74 donors against 0.73 / 0.68 twins) (LESSONS 445–456) —
  **both now quantified and attributed (L 593)**: `resid_m`'s mean is a glucose SINK worth −3.0 U/day, masking half
  the core excess (observed +3.9 U/day, underlying ~+6.9 = +18%), and it is −4.47 mg/dL/h for the tight third of
  donors against 0.00 for the rest. The 8% `si_norm` cut predicts +3.1 U/day, essentially the whole observed
  excess — but **`si_norm` 1.0 is NOT the fix (L 597)**: the level refit raises `resid_m` to hold the donor's level
  and the insulin comes straight back (TDD 41.6 -> 42.1 with it on). A reference that fits `resid_m` to the level
  cannot improve TDD through a sensitivity scalar; it needs a mechanism that lowers insulin need AT that level;
- night lows build toward dawn: 31% of lows fall at night, against the donors' 22% (LESSONS 438–441, 458)
  — **ATTRIBUTED, and the limit's own statement needs correcting (L 684).** The grading is by `resid_m`, the
  one fitted term: night t70 by |`resid_m`| quartile is 0.54 / 0.21 / 1.29 / **7.58**% on draw 1 and 0.50 /
  1.00 / 1.51 / **5.12** on draw 2 (rho +0.374 / +0.371), because a negative drift can only be opposed by
  WITHHOLDING and that saturates — night zero-delivery share runs 24.5 → 39.6% and 28.8 → 40.4% across the
  same quartiles. And the twins' night share of lows is **29.4 / 29.7% POOLED** (reproducing the 31%) but
  **20.4 / 20.1% as a per-person MEDIAN**, which sits on the donors' 22%: lows concentrate in the large-drift
  tail (rho +0.437 / +0.420) so pooling weights it up. **ice has now measured both and "the typical twin's
  night is right" is WITHDRAWN (L 685)**: the donors are **27.4% pooled / 28.1% per person** and FLAT in low
  burden (rho −0.15), so the per-person median 20.4 / 20.1% is too FEW and the pooled 29.4 / 29.7% is about
  right — this is a **SPREAD defect**, the typical twin having too few night lows while a large-sink minority
  has far too many. The search for a measured CAUSE of `resid_m` came back null over 111 and 102 candidate
  columns, the largest correlate flipping sign partialled on t70 (L 686), so the next step was the residual's
  FORM. **TESTED as job 193 and the form that escapes L 678's identity is DECLINED (L 691)**: a TIME-keyed
  holder (`resid_m_diurnal` 0.9, the cosine already adopted at ad3) lands the GRADIENT on the donors —
  rho(|`resid_m`|, night share) +0.204 / +0.156 → **−0.013 / −0.208** against their −0.15, large-sink-quartile
  night t70 7.31 → 0.78% and 5.04 → 0.85% — and takes the LEVEL out the other side, the per-person median
  falling 20.4 / 20.1 → **8.4 / 9.2%** where it was registered to RISE toward 28.1. The cost is structural, not
  a coefficient: the multiplier is blind to `resid_m`'s SIGN while its distribution is strongly negative (84 of
  112, 310 of 408), so scaling every night drift toward zero removes net sink from the cohort at any k — the
  positive-drift quartile GAINS night lows (7.1 → 10.6, 7.9 → 18.2%) while the large-sink one loses them
  (34.7 → 5.5, 26.7 → 4.5). **The deviation-keyed fix L 691 named is now DECLINED on arithmetic with no arm
  spent, and it corrects L 691's reason (L 694)**: the templates' `resid_m` has median **0.000** (mean −7.694,
  p25 −17.63), so the only non-fitted centres are 0 — the arm already run — and the mean. Priced by fitting
  night share against drift on rf2 and retrodicting the declined arm out of sample (predicted 7.67 / 9.12
  against observed 8.38 / 9.20, gate passed), f(−7.694) = **7.55 / 15.93** against the donors' 28.1, and the
  r0 that would reach 28.1 is **−20.8 / −31.2 mg/dL/h** — past the cohort's own p25, i.e. a uniform night sink
  of 26–39% of basal hepatic output for every person. The binding reason is NOT the multiplier's sign-blindness
  but the CONVEXITY: f rises steeply in the negative tail (4.4% at −3.7, 13.0% at −14.7, 38.8% at −25.1), so
  **any** variance-narrowing night modulation of `resid_m` sends the cohort to f(r0) and cannot hold the level,
  because the level is carried by the tail the narrowing removes. No named candidate remains here. **The decline rests on that and on the level alone: on the complete row set the arm SCORES BETTER
  on both draws (0.332 → 0.325, 0.371 → 0.359) and the registered day-side cost did not appear** (`act_net20`
  gap 0.362 → 0.380 and 0.203 → **0.170**, `act_net20_hi` 0.160 → **0.042**) — the partial 37-row read that said
  "worse on both" had dropped the rows that carried the sign (L 692). Guard held (t54 0.124 → 0.136, 0.232 →
  0.235 against the donors' 0.190); lows/day 1.000 → 0.917 and 1.250 → 1.375, so some lows move from night into
  day. **Open for Pete: is a night-lows level three times too low a worse limit than the gradient it buys?**;
- **The low side's one defect is excursion DURATION, not depth or frequency** (L 600): rf2 already matches the donors'
  excursion count below 80 (1.67 against 1.75) and their penetration rate to 70 (60% against 57%); only the duration
  is wrong (25 min against 20). Every `sg_h_lo` variant fixes duration and breaks penetration, because a
  (Gb − G)-proportional term peaks AT the nadir and lifts it. **The requirement is a term acting AFTER the nadir,
  during the climb** — the same time-asymmetry L 575 and L 594 ask for. Do not propose level-proportional low-side
  terms; they cannot meet it. **There is now a candidate that is not level-proportional, and it is measured
  (L 640)**: ice L 140a's probe finds the donors' learned restoring force about **2x stronger when glucose is
  pushed DOWN (D = −40) than up, below 130** — a direction-dependent gain, which acts on the descent and the climb
  rather than at a level. Asked for by band, and whether it is direction or path dependence, in
  `docs/handoffs/2026-11-02-additive-ice-direction-asymmetry.md`; the two answers need different components.
  **ANSWERED, and the direction lead is mostly WITHDRAWN (L 641)**: binned by the midpoint of the span crossed, so
  both perturbations are compared over the same glucose levels, the asymmetry is ~**1.0 near lows** and 1.3-1.6x at
  90-180 — i.e. mostly the force's convexity in level, not direction. Near lows, which is where L 600 wants a
  post-nadir term, there is no sign gain at all. **But the requirement itself is now amended by a direct
  measurement (L 642): the nadir force has almost no leverage over t70, and the mid-band force has all of it.**
  Below Gb, `sg_kappa` 0.15 is bit-identical to the reference (0.270 /h at G 65 and at G 90) and its t70 still
  roughly DOUBLES — so every bit of that extra low time is bought by what the term does ABOVE Gb. The term that
  stops a descent becoming a low therefore acts in the **90-180 band on the way DOWN**, not at the bottom, and the
  model's existing linear SG is what supplies it today. This explains from the other side why every `sg_h_lo`
  variant fixed duration and broke penetration: a term peaking at the nadir acts where there is no leverage. Read
  L 600's requirement as "before or through the nadir, in the mid band", not "after it". **The force-PERSISTENCE line of
  L 644-645 is CLOSED and did not survive (L 646)**: matched on the instrument — our own sensor model put in the
  path, which for a CGM-derived rate is a closed-form addition (`ICE_cgm = F + 12*(eps(t+5) - eps(t))`), not a
  rerun — our `b_k` profile sits on the donors' at every lag (0.620 / 0.405 / 0.274 / 0.200 / 0.163 / 0.150
  against 0.56 / 0.33 / 0.30 / 0.26 / 0.22 / 0.19) and our sensor alone reproduces their fast part, including
  the ~90% night collapse, with no fast-returning force anywhere in the body. There is nothing to build here.
  **One small residual survives, it is nocturnal, and it is 0.6x — not the 3x the slopes
  suggested (L 647)**: `b_k` is a share of total variance, so the comparison must be made as `sqrt(b_k * var)` in
  mg/dL/h. In that metric the donors' persistent night component is **23.9** at 20 min, ice's generator **21.6**
  and our twins **14.4 / 15.2** — 0.61-0.62x. It survives ice's own explanation for it, because our night
  **short-lived** component is 60.6 / 61.0 against their 59.4 (1.02x): our night sensor noise is right, so the
  share effect cannot be what lowered our persistent part, and the nocturnal-lows limit (31% against 22%) is
  therefore NOT our sensor being noisier at night. Soft on size: both sides' ICE is a differenced series, which
  contributes negative covariance at every lag (our own truth-built value is 25.5 against the CGM-built 14.4, so
  the instrument removes ~43%), so the sign is established and the magnitude is not. **Do not build to it** until
  the short-lag structure function of the sensor error is matched on both sides. Persistence has no state
  dependence on either side, so A1e / `sg_rate` is a separate matter from all of this.
- **`acf_zero_min` and the meal ratio are ONE defect, but NOT the same one as low-side recovery** (L 594, corrected
  by L 615): `cr_tau_off` fixes the recovery rows (t54 0.124/0.232 -> 0.175/0.177, nadir dwell 20 -> 15 min, the
  donors' exactly) and leaves `acf_zero_min` at 60 and the meal ratio at 0.61-0.65. So counter-regulatory TIMING
  moves recovery; only gastric emptying SHAPE has ever moved `acf_zero_min` (60 -> 55, `ge_beta`). Two targets,
  two levers, neither adoptable. The reversal rows need something in the APPEARANCE path that sharpens the finish
  without compressing the pulse — not `meal_lag` (shift-invariant, L 595) and not `ge_beta` (compressing, L 591).
- **(superseded framing)** `acf_zero_min` as a reversal-speed row (L 594): it is the ACF of the 5-min increments, so it measures when
  glucose MOMENTUM reverses — donors 40 min, twins 60, about 40% too slow — which is the same defect as the
  post-meal fall / rise ratio and the fast-fall tail. Of every arm run, only the Elashoff emptying shape moves it
  (60 -> 55, gap 1.59 -> 1.22), which corrects L 385–389's "no body lever moves it". Its blocker is that
  `ge_beta`'s score penalty is prohibitive, so look for a mechanism that speeds reversals WITHOUT compressing the
  meal pulse.
- **the short-scale deficit is now SPLIT FROM THE SENSOR and lag-resolved (L 648)**: on ice's structure function
  (rms of `cgm(t+k) − cgm(t)`, per person, median over people, CGM in 90–180) the twins land on the donors **at
  night** — 4.90 / 8.36 / 11.17 / 17.04 against 4.97 / 8.20 / 10.72 / 16.32 on draw 1, 6–18% jumpy on draw 2 — and
  are **18–19% too SMOOTH BY DAY at 5–15 min** (0.81 / 0.86 / 0.88, 2nd difference 0.74, both draws), recovering to
  0.91–0.96 by 30 min. Same sensor, same people, right at night: the missing variance is the BODY's daytime motion,
  not sensor noise, and it is the same defect as `acf_zero_min` read at a fixed lag. The missing 5-min rms is
  **4.31 mg/dL** (4.30 / 4.20 / 4.42 on three draws), and the lag growth now PARTLY pins the timescale (L 650):
  the missing component grows as `k^0.66` to 10 min, `k^0.60` to 15 and `k^0.43` by 30, against 0.50 for a random
  walk — super-diffusive at short lags and reverting by half an hour, i.e. a **mean-reverting component with a
  correlation time around 15–20 min**, not independent jitter (0.50 throughout) and not a slow drift (~1.0). The
  30-min column still scatters 7.8–12.0 across draws, so read 0.43 as soft. **Three draws agree to 0.02 on a 0.19
  deficit, so more draws are not the bottleneck — a mechanism is.** The one existing mechanism of the right shape
  is ruled out: `resid_mult` 0.6 (ad3, daytime-weighted) supplies **8–18%** of the missing variance and nothing at
  night, and closing the gap with it would need ≈ 1.5, well past what L 592 rejected. Split on time since the last
  carb entry, never on `ra`, which is never zero between meals (L 628, 648) — **and this re-bit on
  2026-11-03: I cited its neighbours in a pre-registration and stratified on `ra` anyway, emptying the very
  stratum the test rested on (L 684).** **LOCATED AND SPLIT IN TWO (L 651,
  652)**: against ice's donor table by time since the last entered carb (donors 8.86 / 8.31 / 7.23 / 6.83 / 6.65 /
  6.21 from 0-30m to >5h), the deficit is a POST-ENTRY TAIL — rf2 is flat after an hour where the donors stay
  1.14x their own floor at 1-2 h — and **the multi-step part IS the appearance dispersion**: `ge_order` 3 halves
  the five-bin gap (8.36 -> 5.08) and order 4 nearly removes it (2.35), while `meal_lag` 20, a pure time shift,
  does nothing (8.22). The price is an overshoot where nothing was missing: the night row goes 0.99 / 1.06 ->
  1.04 / 1.09 (order 3) -> 1.08 / 1.13 (order 4) and the night 30-min lag 1.04 / 1.18 -> 1.22 / 1.24 -> 1.34 /
  1.35, so **order 3 is the better of the two on this instrument**, agreeing with L 621's independent finding that
  3 is the fitted order. **The 2nd difference is a SEPARATE component and no appearance arm moves it** (0.74 ->
  0.76-0.82 against the donors' 1.00 while the multi-step lags swing 0.81-1.35): as an implied sigma the donors go
  2.13 at night to 2.65 by day (x1.24) and every arm here is flat at 1.02-1.05, so a sub-10-min daytime component
  is missing outright — rate-dependent sensor error beyond the G7 falling lag, or real fast body motion. Size the
  two separately; do not expect one mechanism to close both. **And do NOT size a rate term from a rate-binned CGM
  table (L 654)**: conditioning the 2nd difference on a CGM-derived rate manufactures the dependence, because the
  sensor's noise LEVEL wanders and a noisy stretch has both a larger apparent rate and a larger 2nd difference
  even with no sample shared. Our own CGM grows x1.31 binned that way and **x1.00 binned by TRUE rate**, with no
  rate term in the model. The artefact-free read is the UNCONDITIONAL 2nd difference — night 0.91, day 0.74 — and
  the FLAT bins, where the donors carry a day-over-night excess worth **1.41 mg/dL of sigma** against our 0.33.
  So the deficit is DAYTIME, not rate-dependent. `rate_k` exists, is off, and has no established size. **The
  nearest named candidate has now been MEASURED and it is not the answer (L 658)**: C7 `act_frag` (everyday
  fragmented waking movement, UK-Biobank-sized, and an adopted default the reference silently dropped) moves the
  day row only 0.81 / 0.86 / 0.88 → 0.83 / 0.88 / 0.91 on draw 1 and **not at all on draw 2**, with the 2nd
  difference 0.74 → 0.75 — at most ~15% of a 0.19 deficit on one draw and none on the other — while the night
  falsifier holds (0.99 → 0.97), so the arm is interpretable and the mechanism is ruled out rather than the
  wiring. `act_k` (Biagi 2018, wired) is 0.0 and now has nothing credible to drive it. **So there is no named
  candidate left for the sub-10-min flat-glucose daytime piece**, and ice L 168 shows CGM alone cannot separate a
  waking sensor artefact from real waking body motion in one person. **MEASURED ACROSS people, and the
  attribution is NOT DECIDABLE from this data (L 659)**: ice's donor 2nd difference split by sensor family (iNNN
  pool, my own `templates_pilot_resid_rf1.csv` `sensor` column as the map — it was on disk all along, no warehouse
  query needed) is **family-INDEPENDENT** — G7 n=135 → 1.233 [1.18, 1.26], G6 n=26 → 1.190 [1.08, 1.26], Libre 3
  n=6 → 1.117, families alike on carb entries. **But that excludes less than I first claimed**: it rules out a
  family-SPECIFIC sensor property (noise level, filtering, lag, calibration) and NOT a wear or motion artefact
  common to every CGM class, since all three sit in subcutaneous interstitium under tape. A cross-group test only
  excludes what VARIES across the groups. The within-family test that would separate them — the same ratio by
  insertion SITE, arm against abdomen — is unavailable: no donor record carries the site. So no further cut of
  this data will settle it, and **a candidate here must be judged on its own evidence, never on closing the row**,
  because closing it is consistent with both hypotheses. The live candidate is **D `act_k`** (Biagi 2018: CGM MARD
  9.5 → 16.5 → 9.3% before / during / 1 h after aerobic exercise), wired since L 498 and **at 0.0 against its own
  evidence** — awake-keyed by construction, acting at flat glucose, at the sub-10-min scale, family-independent.
  Sized against ice's table it falls SHORT of the row and that is the honest read: on G7 the awake-specific
  shortfall is ×1.177, needing `act_k` ≈ 2.95 against ≈1.48 implied by Biagi, and it cannot reach 1.00 at all
  because 9% of the day gap is an all-hours noise shortfall visible at night too (G7 night 0.919). **MEASURED as job 176, and it is the best-behaved
  candidate this lineage has run (L 664).** G7 day 2nd difference 0.780 -> **0.853** against a prediction of
  0.851 registered before the run, and 0.923 against 0.916 at the diagnostic 2.9 — a quantitative
  pre-registration landing to three decimals, derived from ice's table and Biagi with nothing fitted. The
  CEILING behaved as predicted too: at 2.9 the G7 day row (0.923) converges on its own NIGHT row (0.934), not
  on 1.00, so the awake-specific component is fully accounted for and the rest of this row is a flat
  noise-LEVEL shortfall belonging to another knob. Falsifier passed (pooled night 2nd diff 0.91 -> 0.91 /
  0.92; G7 night moves 0.005-0.015, inside the 0.027 draw difference) — though as registered it was too
  strong: in a closed loop a daytime term changes doses and so changes the next night, so state such a
  falsifier as "no more than draw noise". Score **better on both draws** (0.309 -> 0.294, 0.357 -> 0.339),
  carried by tier 3, its own evidence domain (0.464 -> 0.399, 0.442 -> 0.375). The GUARD, the registered risk,
  does not churn and improves: **t54 0.124 -> 0.176 and 0.232 -> 0.197, converging on the donors' 0.190 from
  both sides**, t70 and the TIR gap better on both draws, TDD and lows/day flat — because `act_k` scales
  measurement noise only and leaves insulin absorption alone, unlike `flow_sd` (rejected at L 522 with lows
  1.13-1.29/day). 2.9 is settled as NOT adoptable (t54 0.235 overshoots, TIR 70.93, tier 1 worse); only the
  evidenced 1.5 is in play. The G6 family-scaling caution is **not adjudicable** — rf2's own G6 cell scatters
  1.011 against 0.890 between draws, more than the `act_k` move, at n = 16-21. **The one open cost is paired
  per-person TIR** (SUM|dev| 3.040 -> 3.954, 2.568 -> 3.851, almost all of it that row; rankings level), and
  it is NOT yet a verdict: the arm is unrefit and moved its own level (bg_mean 148.20 -> 149.62 on draw 2),
  which L 597 says must be refitted out before judging and which L 658 already saw explain `act_frag`'s
  draw-1 paired number. **JOB 177 DECIDED IT AND THE ANSWER IS OFF (L 667).** The refit converged
  (|gap| p50 3.2 -> 1.8, better than L 639's 2.2) and **the aim survived it exactly as pre-registered** —
  G7 day 0.780 -> **0.841** and 0.784 -> **0.849** against the 0.851 derived before either arm ran, pooled
  day 2nd difference 0.74 -> 0.80 / 0.81, night flat within draw noise (0.004-0.009 against 0.027). The
  score still holds on both draws (0.309 -> **0.290**, 0.357 -> **0.338**, tier 3 carrying it). What fails
  is the two conditions the deferral existed to test. The refit DID hold the level — cohort bg_mean 148.20
  -> **150.17** toward the donors' 151.93, paired bg_mean deviation 0.210 -> 0.159 — **and the paired cost
  did not come back**: SUM|dev| 3.040 -> **4.791** and 2.568 -> **3.405** against a ~0.8 separability bar,
  with paired TIR the one row worse on both draws (0.141 -> 0.774, 0.937 -> 1.232) while the rankings held
  or improved (rho_t70 0.631 -> 0.666, 0.484 -> 0.508). The guard fails too: TDD 42.31 / 42.83 against the
  registered 41.9 / 42.6, and t54 lands almost exactly on the donors' 0.190 on draw 1 (0.124 -> 0.199) while
  moving away on draw 2 (0.232 -> 0.258). **So the one evidenced candidate for this row reproduces the row
  and is declined on per-person fidelity** — stated plainly as registered, not softened. Cohort TIR (72.15
  -> 70.67 against 71.25 -> 71.67) and `act_net20` (worse draw 1, better draw 2) are draw-split and
  adjudicate nothing. **Its change response was never measured** (job 177 was cohort-only; no e-pool arm
  exists for `act_k`), so never quote it as prediction-neutral — that is the claim L 655 had to withdraw for
  `ge_order` 3. Disposition is `ex_abs`'s: off on the reference, usable at the evidenced 1.5 where the
  daytime short-scale structure is the question, with its cohort and prediction costs stated. **Three
  candidates have now been measured against this row and it still has no adoptable mechanism**: `act_frag`
  (too small, L 658), `rate_k` (sizing withdrawn as an artefact, L 654), `act_k` (the right size, declined
  on paired fidelity).
- **the SLOW motion is too large, and it is the first account of the damped response that is not inside A1d
  (L 678).** The sustained insulin response of this body is `R = flux / lam` (insulin-mediated disposal at the
  operating point over the total restoring gain) and the spread is `sigma / sqrt(2*lam)`, so **response and
  dispersion are two readings of ONE number and cannot be traded** — k times the response means `lam/k` and
  spread x`sqrt(k)`. That retrodicts `sg_kappa`'s exchange rate exactly (bg_cv 34.2 -> 41.4 implies lam -> 0.68;
  its measured response gain was 1.16). Closing the response gap — **0.63 with its CI as of L 680, so R x1.59
  and spread x1.26** (the 1.47 / 1.21 here was L 677's 0.68) — asks for that spread against zero
  headroom (bg_cv 34.2, donors 34.6) — **unless the slow disturbance comes down with the force**, which is what
  the field must be doing. Registered as a crossover before any donor number existed and **CONFIRMED like for
  like** on the e pool's own 408 twin windows against ice's 273 donors (never on `rf2`/`rf2_5k`, which are the
  PILOT cohort — the cross-pool slip ice caught): twin / donor at 5 / 15 / 60 / 120 / 240 / 480 min is
  0.92 / 0.99 / 1.10 / **1.15** / **1.17** / 1.15 all-hours, crossing 1.0 at about 2 h — and **restated on
  the cohort reference's own `day`-ON configuration (job 191, the second registered read, confirmed) every
  slow row RISES: 1.20-1.21x all-hours at 2-4 h and 1.30-1.32x at night, so the published excess is
  conservative and the headroom before the twins fall below the donors widens from 14% to ~17% (L 683)** —
  with the day row's
  0.825 / 0.856 / 0.893 at 5-15 min reproducing L 648's 0.81 / 0.86 / 0.88 on a different pool and donor set.
  **The excess is NOCTURNAL — night 1.30 at 2 h and 1.27 at 4 h against the day's 1.00-1.03 — which was NOT
  predicted**, and which sits oddly beside the 31%-against-22% nocturnal lows limit and beside L 647's night
  persistent component at 0.61x ice's. So: load 1.10-1.14x the donors' (L 603), slow motion 1.15-1.17x, force
  ~1.8x too strong (L 635's bracket) — one picture in which too much slow disturbance and too much restoring
  force **cancel on the spread**, which is why bg_cv matches and why this was invisible, while the excess force
  damps the response. **REFUTED ON SIZING (L 681), without a single new simulation**: `unl_mult` 0.70 — a 30% cut in unlogged
  eating — moves the 2-8 h structure function only 0.93-0.98 (both draws, with and without the `resid_m`
  refit, so not a level artefact) where the identity needs sigma x0.79 and L 678's own excess allows 14%
  before the twins fall below the donors. The lever is short by a factor of 3-7, and it is near-uniform in
  lag, so unlogged eating is not a slow-scale lever at all. The twins' slow motion is not mostly driven by
  the part of the eating that is ours to cut, so with A1d's shape closed (L 642) and its magnitude priced by
  the same identity, **the pair has no sizing and is not queued**. **What DOES drive the night excess is now measured
  (L 684): `resid_m`'s constant drift.** At night our own `si` barely varies (within-window CV 2.25% at 2 h
  against 14.1% by day), so the one thing acting is the fitted drift, and the twin's night 2-h rms tracks
  |`resid_m`| at rho +0.313 (partial +0.325, DAY flat at −0.016) — 32.99 → 45.57 across its quartiles against
  the donors' 29.84, so ~65% of the night excess is the large-drift tail, all of it on the NEGATIVE side
  (rho +0.312 over 310 people, +0.034 over the 98 positive). The mechanism is Loop pinned at zero delivery
  23.9 → 42.8% of the night. **The tension to hold on to: L 642's glucose-dependent level-holder would raise
  `lam` and so damp the response further, which is this identity again — the escape is needing LESS residual,
  not a better form for it.** The idea was: **the PAIR, cut the load
  and the force together**, each a named
  lever with its own evidence (`unl_mult`, L 610's only real TDD lever; A1d's magnitude), and they should cancel
  on the LEVEL too — the force cut raising it, the load cut lowering it — which is what would stop `resid_m`
  handing the gain back as it did to five previous candidates (L 604, 629). Not adopted: the identity's own
  validation is job 190, and what is confirmed is a prediction derived from it, not the identity. Two code facts
  from the derivation: **`egp_share` is drawn `uniform(0.7, 0.9)` (`person.py:374`) and carries ~65% of each
  twin's insulin response through hepatic EGP suppression with NO evidence entry anywhere** — large and
  unevidenced, but a weak lever here, since `sg` is ~80% of `lam` and the split can only move the rest; and the
  ODE's deviation form (`egp - egp_b`) means **no knob raises the insulin-independent glucose INPUT**, so the
  only route to a larger `flux` is the glucose LOAD, the same lever the pair wants cut in the opposite direction.
- failing on both draws: G7 short-scale rows, acf_zero_min, sigma_disp, med_nonzero, ac1, day / night and Box-Cox λ
  (**read `ac1` against the independent-day null of −0.086, not 0**, and against **+0.118, not +0.18**: half the donors'
  persistence is their SETTINGS — a basal / ISF edit or a multi-day override persists by construction, and on day pairs
  free of both, the basal limb falls from +0.189 to +0.063 above null while the bolus limb stays at +0.166. A twin holding
  one era cannot and should not reproduce the rest. **CLOSED as a body target** (L 585): the twins carry +0.064 of the
  reproducible +0.118, the genuine remainder is day-level glucose persistence (donors +0.168 above null, twins +0.105,
  gap ~+0.06), and five mechanisms are null — the residual's day level, the life modulators with B3's own AR(1),
  everyday activity, `intake_rho` (carbs only) and `day_rho`, whose ceiling is **+0.02** of delivered-insulin persistence
  whatever ρ is, since the day factor is half of daily-mean SI variance and that series reaches delivered insulin at
  r −0.32. Closing it by amplitude would need a day-to-day SI CV near 25%, far outside the 6–15% clamp evidence; L 583–585).
  **The last named candidate is now measured and refuted too** (L 624, `resid_tools/twin_limb_ac.py`): the twins' basal
  is NOT near-constant — within 13-day blocks its day-to-day CV is 0.170 / 0.172 against the donors' 0.176, and the
  bolus limb varies MORE than the donors' (0.329 against 0.289). Amplitude is right in both limbs and the whole deficit
  is persistence, so there is nothing left to try (LESSONS 457);
- **the excess low-side EATING is downstream of this same gap, not a behaviour defect** (L 588): per low episode the
  twins' low-side eating is about the donors' (0.62 / 0.64 events against 0.50, two-or-more rare on both sides); what
  differs is the share of episodes treated at all (0.60 against 0.49), and that follows from episode DURATION — median
  25 min against 20, x1.25 against the treated-share's x1.23. Four arms on the eating side (size, refractory, onset
  −10 / −20) were all rejected. Do not spend more there.
- **the sub-basal gap was a missing CODE BRANCH, not missing evidence** (L 596): A1b's `hep` is gated on `g > gb`, so
  the liver never released extra glucose in a low. Extending it symmetrically below basal (`sg_h_lo`, off by default)
  supplies 0.386 mg/kg/min at G 65 against the ~0.34 L 589 derived independently, and at HALF symmetry it closes the
  t70 limit — draw 2 gap 0.325 -> **0.034** with the insulin suppression of L 599, draw 1 1.764 -> 1.319. **It must
  carry basal EGP's insulin suppression** (`sg_h_lo_ins`, default on): unsuppressed it acts on the DESCENT and prevents
  lows (counts 1.000 -> 0.750, t54 0.124 -> 0.091), suppressed it acts at the NADIR and shortens them (counts 0.833 /
  1.042, t54 0.181 against the donors' 0.190). Still not adopted: it helps where the reference is weak (draw 2) and
  overshoots where it is strong (draw 1, where rf2 is already near-perfect), so the weighted mean reads
  level-to-worse — a genuine which-row-to-spend question for Pete, not a defect. **Its CHANGE response is now MEASURED and
  NEGATIVE** (L 634, the e-pool re-run after L 632's no-op): the cohort gain does NOT transfer — the t70 response
  ratio is bit-flat at 1.15, while the mean response goes 1.33 -> 1.43 and TIR 1.28 -> 1.40 (more damped), all three
  correlations fall (+0.33 / +0.16 / +0.17 -> +0.26 / +0.13 / +0.12) and the pre-edit level drifts +3.3 -> +6.3. t54's
  ratio improves (0.56 -> 0.82) but t54 is a guard, not a target. **The cohort and the change response disagree, so
  `sg_h_lo` stays off on both halves** and the which-row-to-spend question above is settled against it.
- **the shallow-low recovery gap is down to one named, unevidenced mechanism** (L 563, sized L 589): a
  glucose-dependent hepatic response below Gb, worth ~0.34 mg/kg/min at G 65 — **about 3x either of the two sub-basal
  mechanisms the model has**, both now measured too small (A9 counter-regulation 2.4 mg/dL per 30 min, L 559–560; A1c
  sparing 3.7, L 589). Quote that bracket in any evidence request: the study needed lowers glucose below basal at basal
  insulin in T1D. Insulin is ruled out (the twins carry LESS IOB at the nadir, 1.09 vs
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
- **the fall / rise ratio has no named mechanism left** (L 591): absorption SHAPE was the last class on L 575's list
  and it is eliminated — the shape fix works and the ratio does not follow. What remains is a post-peak fall of 52
  against 57 mg/dL at a matched rise, about 5 mg/dL, with the sensor amplifying a fall ~27% against a rise ~7% on top.
  Treat it as artefact-bounded unless a mechanism OUTSIDE the meal pathway is proposed.
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

**Which limits are REAL — final state (L 602, 607, 609).** Over five draws (seed0 1000 / 5000 / 9000 / 13000 / 17000),
by bias / SE:

| row | bias | bias / SE | status |
|---|---|---|---|
| **TDD** | +3.36 U/day | **+4.98** | **the only robust outcome bias** — and unreachable by any body parameter (L 605) |
| TIR | −2.08 | −2.12 | **not a defect**: it is trait-draw sampling (L 609), between-draw sd 2.19 |
| t70 | −0.004 | −0.02 | **no bias — "excess shallow lows" is REMOVED as a limit** |
| t54 | −0.048 | −1.96 | twins slightly UNDER the donors |
| P(reach 54) | −0.028 | −2.61 | small, twins under |
| lows / day | −0.050 | −0.60 | nothing |

Three rules follow. **(1) Check bias / SE before building a mechanism** — at n = 3 a 0.2-point t70 gap and a zero gap
are indistinguishable, and every low-side arm of 2026-11-01 was chasing a gap that is not there. **(2) A band gap
cannot be decomposed by comparing medians**: `tir`, `t70` and `t180` are exhaustive per block but the scored values are
medians, which are not additive — that is why they do not sum to 100 and why TIR's deficit appeared unattributable
(L 608, 609). **(3) Prefer paired per-person differences** (`twin.csv`), which remove the trait-draw variance entirely
(L 610).

**Superseded, kept for the method (L 602).** Across seed0 1000 / 5000 / 9000 the reference's own tier-1 rows have a draw scatter
LARGER than their gap to the donors for **t54** (bias −0.022, sd 0.057), **t70** (+0.199, 0.306), **lows/day** (+0.042,
0.191) and **TIR** (−0.996, 1.484). Only **TDD** is a clear bias (+3.69 at 8x the sd; quote the paired +1.4–1.7 U/day
of L 598), and **it is a LOAD bias (L 603)**: the twins' labelled glucose load is 1.10 / 1.14 / 1.10 x the donors'
(against a +9.5% TDD excess), carried by the UNANNOUNCED part (104.2 / 101.8 / 110.5 against 94.7 g-eq/day) which
was calibrated at c378 and has DRIFTED. **REFUTED (L 604)**: load is level-mediated too. Cutting unlogged eating 30% brings TDD
within 0.9–2.1 U/day of the donors with the level 6 mg/dL low, and the refit restores the level and the insulin
both. **TDD cannot be moved by any component while `resid_m` is fitted to the level alone** — the fit restores
whatever net glucose a candidate removes (sensitivity, dynamics, the pair, load: four sightings). The limit's real
statement is an insulin-to-glucose EXCHANGE-RATE error of 3.5–4.4% paired. **SETTLED as unreachable, on five
sightings** (sensitivity, dynamics, the pair, load, and gut absorption — L 629, where `kabs` 0.057 improved paired TDD
on all three draws and the `resid_m` refit handed every bit of it back, as predicted before the run). **The
two-parameter fit is NOT the route left**: it was run in L 605 and rejected in L 606, because a fit pointed at an
unreachable target drove `twin_isf_mult` to its clips and cost `acf_zero_min`, `circadian_amp` and `night_cv` on all
three draws. **And no replacement target exists among the outcome rows** (L 630, `resid_tools/target_screen.py`):
t54's leverage is BELOW the draw noise (ratio 0.89) and TIR's high leverage (3.88) is 59% the level (r −0.768 with
`bg_mean`), which `resid_m` already owns. Do not spend further arms on TDD, and do not add a second fitted parameter. A fixed-magnitude term cannot improve a row whose scatter exceeds its bias — it helps on the heavy draw and
overshoots on the light one, which is what `sg_h_lo`, `cr_tau_off` and `pro_g_own` each did. **Do not spend further arms
on t54 / t70 / lows-per-day without more draws first**; three draws give an sd with two degrees of freedom, so this
means "not established as a bias at n = 3", not "zero".

**Glucose effectiveness is too high, by two independent lines, and it is the one structural term left on the damped
change response (L 635, 636).** SG is the insulin-INDEPENDENT share of disposal, so it bounds how much of a settings
edit glucose can respond to (dG/dI = −SI·G / (SG + SI·I·…)); the twins respond at 0.75 of the field with every other
named candidate eliminated (L 634). The draw is lnN(0.0045, 0.5), whose MEDIAN alone sits inside UVA/Padova's
0.0013–0.0047 — a range `evidence/05` records as PER PERSON, and 47% of the cohort is drawn above its top (p95 0.0102,
2.2x it). Read as a bracket the evidence implies median 0.00247 / log-sd 0.39 (1.8x too high, 1.3x too wide); ice's
learned background force says 0.0015/min (3x). **SG is not measurable from this pool** — the controller makes glucose
and insulin activity collinear at r +0.5–0.7 so an ICE-against-glucose slope comes out the wrong SIGN, and
`no_insulin` is a record flag, not an insulin-free state (ice L 140b) — so the prior rests on literature. **The error
is SHAPED, concentrated on the high side** (ice L 140a: ~10x below our prior above 180, but −0.17/h below 90), so the
fix is a SATURATING insulin-independent uptake (`sg_kappa`, L 637), NOT a uniform `sg_mult` cut, which would thin the low side that
L 563/589 want strengthened. Screened uniformly first (`sg_mult` 0.67 / 0.40, bracketing both estimates, 0.40
central); both prior rejections (L 208, L 349/356) were on the LEVEL and predate `resid_m`, so neither transfers. **The
shape has a named form and it already exists in the model for the other path (L 637)**: `kappa` 0.15 makes
insulin-mediated uptake saturate above Gb (LESSONS 7) while the insulin-INDEPENDENT term beside it is perfectly
linear, an unmotivated asymmetry. `sg_kappa` (new, default 0 = unchanged) gives it κ's treatment, and at `sg` 0.00247
(L 635's bracket median) with `sg_kappa` 0.15 it reproduces all five of ice's learned bands within 0.044 /h — 0.148 /
0.114 / 0.022 / 0.022 against 0.170 / 0.070 / 0.040 / 0.020 — with NEITHER parameter fitted to that table, against a
linear term that is wrong by 0.10–0.27 /h in every band. **A third line is a direct test: ice L 146** put a
literature-strength SG in the generator's plant and it was worse on every held-out row with no change-prediction gain
("a restoring force the TDD-ISF ICE already holds") — which transfers here because additive's ISF comes from the same
ICE yardstick on the same pool, and the +0.53–0.71 collinearity above is how that disposal loads onto a fitted insulin
effect. So the high side is plausibly double-counted with our own ISF. **MEASURED, and the 2x2 separates magnitude
from shape decisively (L 638).** On the e pool's 580 events, `sg_kappa` 0.15 alone (`sk1`) brings every response row
to the field — mean 1.33 -> **1.06**, TIR 1.28 -> **1.06**, t70 1.15 -> **1.08** — while the uniform cuts move
nothing structural: `sg_mult` 0.40's observed mean ratio is 1.25 against a LEVEL-ONLY expectation of 1.25, i.e. its
whole apparent gain is its own +15.5 mg/dL pre-edit drift, since dG/dI is proportional to G. Corrected the same way,
`sk1`'s 1.05 sits against an expectation of 1.22, so the FORM carries 1.22 -> 1.05 at a fixed level (1.16x more
response per unit glucose), and the magnitude arm reproducing its own confound to two decimals is what validates the
correction. `sk2` (plus `sg_mult` 0.55) OVERSHOOTS (mean 0.98, TIR 0.95) and puts the low-side damage back (t70 1.19),
so the pair brackets the field. (Note which arm the band evidence picks: L 637's match is at `sg` 0.00247 WITH
`sg_kappa` 0.15, and 0.00247 = 0.0045 x 0.55, so that is **`sk2`**, not `sk1`; `sk1` runs the sub-basal force 1.6x
stronger than ice's 0.17 /h — L 639.) **AND THE COHORT COST IS NOW MEASURED, AFTER THE REFIT, AND IT IS SEVERE
(L 639).** The refit converged (|gap| p50 12.7 -> 3.9 -> 2.2) and held the level exactly — bg_mean 151.8 / 150.9
against the donors' 151.9 on draws 1-2, TDD level or better — so none of the cost is the level. What the fit cannot
hold is DISPERSION: **bg_cv 34.2 -> 40.6 / 41.5 / 42.0** (donors 34.6), **t70 and lows/day roughly DOUBLED** (t70
3.38 / 3.76 / 2.58 against 1.76 / 2.12 / 1.51; lows 1.79 / 2.08 / 1.46 against 1.00 / 1.25 / 0.88), t54 1.5-2.5x,
score +0.11 worse on all three draws. The cause is the INSTRUMENT, not the sub-basal physiology: `sk1` leaves the
low side at full strength and its lows still doubled, TDD is flat so Loop is not over-dosing, and holding the mean
costs `resid_m` a mean of -20.43 mg/dL/h against rf2's -7.69 — ~12.7 mg/dL/h of extra CONSTANT downward drift, which
holds the mean and widens both tails. **So `sg_kappa` stays OFF and the choice is Pete's**: it is the only mechanism
that has ever closed the damped change response, and it doubles the lows, which is a safety axis AGENTS.md does not
let a change-prediction win buy. **The FORM route is closed too (L 640)**: a free-breakpoint Michaelis-Menten fits ice's bands
essentially exactly (RMS 0.0015 /h against the kink's 0.0251), but what sets the cost is the TOTAL force removed,
and that is pinned — every band-faithful configuration lands at x0.22-0.25 of the default dwell-weighted restoring
force, the best-fitting one LOWEST of all. So no parameterisation of A1d avoids the dispersion cost; do not spend
another arm on its shape. Remaining caveat: ice's high-side slope is biased LOW by their own confound, so if
anything the force should be stronger than their bands say. **That caveat was right, the corrected profile was
fitted, the second form was RUN, and the component is now CLOSED on measurement (L 641, 642).** ice's same-span
bands are 1.2-1.7x stronger than the D = +40 ones (0.235 / 0.118 / 0.053 / 0.024 /h) and a Michaelis-Menten
saturation in absolute glucose fits them at RMS 0.0008 /h (`sg_km` 63.2, `sg_g0` 80.4, `sg` 0.00403). Run as job
164, it replicates the change response on mean (1.21 -> 1.06) and TIR (1.16 -> 1.05) but moves **t70's the WRONG
way (1.01 -> 1.24)**, and the low side is worse than BOTH kinks on all three draws — t70 3.97 / 3.93 / 2.91
against the donors' 1.60, **t54 0.58 / 0.70 / 0.48 against 0.190**, 3-4.7x the reference on the guard row — with
bg_mean held at 151.3 / 150.8 and TDD flat. The prediction that it would cost LESS on the low side rested on a
false premise: `_sg_excess` returns `g - gb` UNCHANGED below Gb, so `sg_kappa` already leaves the sub-basal force
at the full default, and the smooth form's "0.242 near-low" is a LOCAL SLOPE — the force a low feels is the span
average from Gb, **0.177 at G 65**, making it the weaker of the two below 130. Ordered by the dwell-weighted force
kept (1.00 / 0.46 / 0.32 / 0.25) the cohort cost is monotone across two quite different shapes, so
band-faithfulness IS a constraint on the integral and **no parameterisation of A1d escapes it**. Both knobs stay
off; the only live direction left is outside this component — holding the donor's level with something
glucose-dependent instead of `resid_m`'s constant.

**There is an OUT-OF-REGIME test set in the donor records and this model has never been tested on it
(L 688).** Every number in this overlay is measured inside closed-loop operation, which is also where
`resid_m` was fitted, so the body is least constrained exactly where the controller never goes. The
donors' pump suspends go there: 412 windows of 2-24 h across 74 donors, **389 across 68 donors** after a
PRORATED zero-delivery filter (<0.10 U by dose-record overlap - never trust the `suspend` label, which sits
on windows with delivery inside them) and a no-carb-entry filter. Median dG/dt +12.0 mg/dL/h, 60% rising.
**Read the ZERO-DELIVERY EQUILIBRIUM off it, not SG**: the donors are flat at onset ~140-155 and rise
+23.6 mg/dL/h below 110, which constrains EGP, the restoring force and `resid_m` jointly with no estimator
and no exclusion restriction. SG itself is NOT yet extractable here - the within-window slope reads the IOB
tail and comes out anti-restoring, and the between-window slope gets the right sign at 2-6x every prior
because unlogged rescue carbs lift the low end and bolus-then-disconnect lowers the high end (glucose falls
12-47 mg/dL/h with zero delivery at onset >180). Doing it properly needs insulin action run forward through
`insulins.py`, not a delivery-total covariate, which moves the slope by 0.0002 /h. Two donors hold 35% of
the clean windows, so quote per person as well as pooled. **THE EQUILIBRIUM HAS NOW BEEN READ AND THE
MODEL PASSES IT (L 690).** Running the dose history forward through the model's own insulin chain on
BOTH sides (one kernel, population defaults, nothing fitted per side) and adding the committed insulin
back, the zero-delivery non-insulin net is **+74.3 mg/dL/h for the donors against +78.3 for the twins, a
per-person gap of +4.0**, stable across p2 0.015-0.040 (-4.6 / +2.3 / +3.3). So EGP, the restoring force
and `resid_m` are jointly about right where the controller never goes - the first out-of-regime check this
model has had. **It also WITHDRAWS L 689's -34 mg/dL/h core offset and its EGP read**: that gap was the
insulin TAIL, because the twins' insulin sits closer to onset (E / 6 h total 0.346 against 0.295) so they
carry 58-188 mg/dL/h of committed insulin against the donors' 45-87 at a matched 6 h TOTAL. L 689's
level-independence argument was a cancellation of two terms that both grow, not evidence of a constant
input - **a flat difference says nothing about structure until both sides are matched on the dominant
term**, and insulin here is 2-5x the gap. Still open where it always was: the 80-110 band keeps -47.6,
which is exactly where unlogged rescue carbs inflate the donor rate, and the 230-300 band reverses to
+67.2 on n=15.

**ACTIVITY, HR AND SLEEP ARE NOT IN THE DONATION AT ALL, so the exercise limit cannot be closed from this
cohort (L 688).** The exercise side is recorded above as blocked on measurement rather than mechanism
(L 551, 556, 557, 564, 631) - METmax is a prior, `met_own` reaches 22 of 168 donors and moves the cohort
mean by x1.0047. The activity record behind that is `com.apple.HealthKit` `physicalActivity` rows carrying a
workout duration and an `HKAverageMETs` payload fragment: 26,671 rows over **37 donors of 168**, with
**0 rows of heart rate, 0 of workout type, 0 of sleep, 0 of energy** and `reportedIntensity` non-null for 3
donors. So it is a PIPELINE limit, not a coverage one, and no warehouse query fixes it. `sleep_mid_h` is
likewise INFERRED from the quietest window in the donor's own carb-entry record (`templates.py:825`), not
measured - in a model whose worst region is the night. Closing the 6-8 MET band (-13 against the donors'
-21.5, a tier-1 row) or re-keying `act_k` to measured movement needs an external dataset or new collection.

**The natural-experiment half is limited by the FIELD, not by compute (L 611).** With 63 edit events the field / twin
response ratios carry CIs like [1.22, 3.79], so `rf2`'s t70 improvement (3.51 -> 2.17) is "best measured, not
established", and MORE DRAWS CANNOT HELP — the limiting variance is one noisy field response per event. Narrowing it
needs more EVENTS (the x and e pools, 790 edits, L 532). Do NOT try to replace `score_change.py`'s two-slope design
with a paired twin-on-field regression: the field change is a noisy regressor and the slope attenuates to ~0.00 for
every arm (regression dilution, L 611).

**POWER: three draws is not enough for the rows that matter (L 609).** Between-draw sd over five draws is 2.19 for
TIR, 0.358 for t70 and 1.51 U/day for TDD, so resolving a 1-point TIR effect needs **20 draws**, a 0.2-point t70 effect
**13**, and a 1 U/day TDD effect **10**. TDD is the only row whose bias (+3.36) exceeds its own between-draw sd. The
cheap alternative is to judge candidates on **paired per-person differences** (`twin.csv`), which remove the trait-draw
variance by construction. Also: `lvl_resid.py` / `tdd_isf.py` glob `v0*`, which misses seeds >= 10000 entirely.

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
- **`pulse_peak_h` and `pulse_dur_h`'s DONOR VALUES in the scorecard are the stale pre-`fit_shapes` definition**
  (L 625, 626): the stored donor labels carry the raw 5-min argmax peak and the run length, the twins' carry the fitted
  lognormal mode and 90th percentile. ice has regenerated all 168 donors as `ice_v32/meals_fit/`; scored like for like,
  **`pulse_peak_h` is EXACT** (0.622 both sides — the scored gap of 1.04 was entirely the definition) while
  **`pulse_dur_h` is a real ~19% defect** (donors 1.577, twins 1.876) that the stale target scored as near-passing, and
  `pulse_peak_per_g` (~10% low) was always real. **No appearance arm closes the duration gap** — `ge_order` 3 plus
  `kabs` 0.057 reaches 1.775 and is the worst-scoring arm tried (L 627). The labeller itself reads ~16% early against
  twin ground truth on isolated pulses, so **never calibrate the body's appearance to a labelled target** (L 628:
  the duration half of that instrument check is withdrawn — `ra` is never zero between meals, so a cumulative-90%
  measure is a statistic about the window).
- **the meal tail has a NAMED lever now** (L 617): the stomach's Erlang transit order. At order 3-4 `meal_d3h` goes
  31.0 -> 37.0-39.0 against the donors' 38.0 (gap 0.373 -> 0.053), `acf_zero_min` 60 -> 50 (its best ever) and the
  fall / rise ratio 0.63 -> 0.69 — four standing limits moving together, which is what a shared cause looks like. The
  cost is high-side: TIR 72.2 -> 68.6, t180 25.8 -> 28.1, because less dispersion delivers the same carbohydrate in a
  shorter window and Loop cannot cover the peak, so the score rejects it. **The appearance evidence is insulin-free (L 619)**: the labeller builds every pulse from `ice`,
  not glucose, so the donors' 60-min decay against the twins' 67 IS an appearance difference and `ge_order` 3-4 moves
  toward measured truth. **Re-judged on honest donor labels its score penalty roughly HALVES and is no longer
  what rejects it (L 696): 0.326 / 0.376 against rf2's 0.328 / 0.366 — score-level on draw 1, marginally worse
  on draw 2 — with `meal_d3h`'s tier-1 gap 0.373 -> 0.054 / 0.160 and `acf_zero_min` 1.734 -> 1.272. What
  rejects it is the GUARD and TIR: t54 0.124 -> 0.294 and 0.232 -> 0.275 against the donors' 0.190, t70 up,
  TIR 72.15 -> 68.49 and 71.25 -> 67.40, t180 up — a sharper pulse gives a bigger peak AND a deeper post-peak
  fall, the same thing that improves the fall/rise ratio. Plus L 656's damping, which no donor label touches.
  `ol85` (order 3 + `unl_mult` 0.85) recovers ~2 of the 3.7 TIR points and lands t180 on the donors while
  keeping the appearance gains, and is still blocked by t70/t54 — the first cohort evidence that the load lever
  offsets a sharper pulse's HIGH-side cost, a different job from the slow-scale one L 681 refuted it for.**
  The cost is therefore an INSULIN-ACTION mismatch: `p2` 0.025 is fitted to a 0.2 U/kg
  (~15 U) SUBCUTANEOUS lispro clamp while meal boluses are ~0.05 U/kg, and while A4d already dose-corrects
  ABSORPTION (normalised at that clamp dose), nothing dose-corrects the ACTION rate — a limitation `p2`'s own
  comment records as "direction known, size not found for analogues" (L 620). **ANSWERED and refuted (L 621)**: Gagnon-Auger 2010 (lispro 10 / 30 / 50 U under clamp) finds
  10 U comparable to controls with the delay appearing only at 30-50 U, in obese T2D — so there is no documented
  action delay between ~4 and 15 U in T1D and `p2` 0.025 is defensible for meal doses. **Order 3 is the fitted
  order** (labelled decay 59 min against the donors' 60) and costs 0.009 of score and 3.7 TIR points, which is no
  longer attributable to any evidenced component — so the open question is now why matching the donors' measured
  appearance dispersion costs time in range, which points at the controller's response rather than the body.
  **Its "prediction neutral" verdict is WITHDRAWN as UNMEASURED (L 655)**: the e-pool arm behind it passed
  `"ge_order": 3` as a JSON INTEGER into a guard testing `isinstance(v, float)`, so the knob was silently dropped —
  60/60 events bit-identical to the reference, all four response ratios equal to it to four decimals. The cohort
  arms used `--set`, which parses to float, so L 617's cohort numbers and L 652's structure-function result stand;
  only the change response was lost. Fixed (`_num` accepts int, rejects bool) and re-run as job 172 —
  **which settles it AGAINST the component (L 656)**: level-adjusted the change response is more DAMPED, mean
  1.35 → **1.57** and TIR 1.30 → **1.68** against the field's 1.0, with t70 the one gain (1.09 → **0.98**) and
  t54 flat. Not its level drift — the level-only expectation is 1.32 / 1.27 against the observed 1.57 / 1.68, so
  the form carries it — and the per-person rankings slip slightly too (mean rho 0.33 → 0.27). CIs overlap, so
  "best estimate clearly negative on mean and TIR, not individually significant". **The hypothesis that a
  too-smooth body carries the damped response is REFUTED**, and **Short-scale realism and change-response
  accuracy are not the same axis.** The MECHANISM first offered for that — dispersion lowers the post-meal
  peaks, so there is less high-side excursion for an edit to act on — **is itself withdrawn as measured false
  (L 662)**: `go3e2` sits with MORE high-side excursion than the reference (t180 24.7 against 21.4, sd 58.7
  against 51.8) and at a HIGHER level, both of which predict MORE response, and it damps anyway. The verdict
  stands and is strengthened; only the explanation is gone. **SETTLED at L 676, and it is ENTIRELY CONTROLLER-SIDE — not a
  body question at all.** Measured OPEN LOOP against `physiology.Body` with no Loop in the path, 60 people,
  each configuration bisected to a matched glucose level: `ge_order` 3's body responds to exogenous insulin at
  **1.013** of the reference and `sg_rate`'s at **0.993** — equal within 1-2% — against closed-loop damping of
  0.745 and 0.812. The gate passed (the force-cutters read 1.303 / 1.390 / 1.408, as the ODE requires), and
  the table splits cleanly: for every arm that genuinely changes the BODY the closed-loop ratio recovers the
  open-loop sensitivity almost exactly (1.303 against 1.313, 1.408 against 1.419), and for the two
  short-timescale arms it does not. **Adding short-timescale motion does not change how the body answers
  insulin; it changes how Loop answers the glucose it sees, so no body candidate will fix it** — which is why
  five successive accounts came up empty (L 670-675), all of them looking inside the body. It does NOT speak
  to the reference's own 1.35 damping against the FIELD — and that half is now measured from the other side
  (L 677): **our Loop's DELIVERY response to an edit matches the real deployment's**, +9.96 U/day per
  log-unit against the field's +9.14 at baselines of 36.41 and 36.66 (the donors' own `doses.json` over each
  event's own clear windows; the matched baseline is what makes the absolute comparison valid). So the
  baseline damping is not Loop failing to act on the edit — at matched delivery the twins' glucose moves
  about **0.68** of the field's, which is where L 635's SG indictment already pointed and why `sg_kappa` is
  the only thing that ever closed it. The two halves are therefore cleanly separated: an added
  short-timescale component's EXTRA damping is controller-side, while the reference's BASELINE damping is the
  glucose response per delivered unit. **MEASURED with a CI as job 189 and the limit is ESTABLISHED, at the
  registered level and marginally (L 680): per unit actually delivered the twins move 0.63 of the field's
  glucose, 90% CI [0.39, 0.98], from the ratio computed per event over the 588 e-pool events with both a
  donor dose record and a twin pair — field -2.788 mg/dL/U against -1.753, with TIR 0.65 and t70 0.77 the
  same direction.** The registered rule was the MEAN row's CI excluding 1.0, which makes the FORCE'S
  MAGNITUDE the target now that L 642 has closed its shape; the upper bound 0.98 means a 95% interval would
  include 1.0, so quote the sign and the direction, not the third decimal. L 677's 0.68 came from pairing a
  3-covariate field DOSE slope with a 5-covariate field OUTCOME slope: **a ratio of two regression slopes
  needs both conditioned on the same covariates**, and both pairings sit inside this CI. The closed-loop measurement behind it, for the record:
  on `truth["delivered"]` across eight arms, Loop delivers 3-19% MORE insulin per
  log-unit edit in every variant, and what differs is glucose moved per DELIVERED unit — 0.727 (`ge_order` 3),
  0.798 (`sg_rate`), 0.825 (`act_frag`), 0.944 (`act_k`) against 1.141 / 1.131 / 1.270 for the three arms that
  CUT the insulin-independent force. Perfect sign separation, and it SURVIVES the unequal-need artefact
  test — the motion-adders' dose response exceeds their baseline need by 5-15% and the fractional metric
  separates them more sharply (0.745 / 0.812 / 0.817 / 0.983 against 1.302 / 1.313 / 1.419, L 674).
  **But do NOT call the ratio `dG/dI` or a body property (L 674)**: the settings edit is the only exogenous
  variation and BOTH glucose and delivered insulin respond to it, so their ratio is a Wald/IV estimator whose
  exclusion restriction fails outright — an ISF/CR/target edit changes the TIMING and shape of delivery, not
  just its total. That is also why job 184 found no mechanism: there need not be one. `kappa`'s kink measures
  1.0000-1.0001 of curvature (the registered stop fired: cohort median kappa 1.003, 50% either side) and the
  renal term orders BACKWARDS inside the motion-adders. The live account is the COVARIANCE the probe held
  out — the insulin term `xact * mm(g)` is bilinear, so `cov(xact, mm(g))` is a delivery-to-need MATCH term
  and a controller property, not a body one (job 186). What stands regardless: Loop's delivery response is
  larger in every variant and glucose moves less in the motion-adders, so the controller is not
  under-delivering. So `ge_order` 3 is: four cohort rows
  better, against 3.7 TIR points, 2.3 t180 points, a night structure row that was correct, and a more damped
  response on both primary rows. **Stays off.**
  If yes, `ge_order` 3 + a faster `p2` is a pair of evidenced changes that close the meal tail,
  `acf_zero_min` and the fall / rise ratio together. **NOT a behaviour refit (L 618)**: `bolus_lead_min`, `p_bolus_ann` and
  `bolus_ratio` are already per-donor, so the twins already dose like their donors. The cost is a clash between two
  independently calibrated components — appearance dispersion against insulin action (`p2` 0.025, the lispro clamp)
  — which the cohort cannot adjudicate; it needs simultaneous appearance and insulin kinetics after a mixed meal.
- **Meals still come down sooner than the donors'**: 3-h meal change +11.7 vs +21 (was +2 before breakfast skipping, the dinner fat carrying the night, LESSONS 368–370). Loop's delivery at each glucose band matches the donors' (LESSONS 368); adding meal glucose by carb sensitivity, slow share or protein is answered at the meal (LESSONS 366–367). The hourly profile runs 5 mg/dL low at 00–06 h and 8 high at 06–12 h (basal-need shape, LESSONS 371, 373); TDD day-to-day persistence (ac1) is ~0 against the donors' 0.09. Candidates acting after meals are read here as a second opinion.
- **Night-to-night insulin varies less** (night CV 29 vs 36) and does not follow evening entries as the donors' does
  (LESSONS 288–289).
- **The exercise side is limited by a missing measurement, not a missing mechanism** (L 551, 556, 557, 564): per-person
  aerobic capacity is a prior (METmax lnN(9, 0.25)), and without it C1 / C2's size at moderate intensity cannot be settled —
  the 6–8 MET band is still −13 against the donors' −21.5. C4's threshold and size ARE settled (8 absolute METs, 28
  mg/kg/min): the ≥ 8 MET band reads +1.8 against the donors' +1.2 once `ex_headroom` gives it enough bouts (L 554).
  The 6–8 shortfall is now understood as a REGIME SWITCH the smooth terms cannot make (L 565): the donors fall deepest at
  6–8 METs and rise at ≥ 8, so any setting that deepens one deepens the other. **Both remaining routes are shut** (L 631).
  The obvious form change — plasma-glucose uptake falling off as the anaerobic share rises — is counter-evidenced:
  Romijn 1993 has plasma glucose uptake INCREASING across 25 / 65 / 85% VO2max, so the crossover is
  fat-versus-carbohydrate and the model's monotone-uptake structure is already right. And the missing per-person
  capacity IS measurable from the donors' own `HKAverageMETs` — p90 bout METs is a stable trait (split-half +0.790),
  while the MAX is frequency-confounded (+0.783) and must never be used — but it reaches only **22 of 168 donors**, so
  `met_own` moves 6 of 112 twins and the cohort mean METmax by ×1.0047: a measured no-op, not run. This band needs
  workout records for most of the cohort, not a new mechanism.
- Off-by-default experiments with their verdicts: **`act_frag` (C7, everyday fragmented waking movement) is the odd one out — it is ON by default in the CODE (`world.py:526`) and adopted as a default by Pete on 2026-10-18 (L 163), and the reference turns it OFF through its own `--disable` list, bundled in with four B-series LIFE modulators, with no lesson recording the decision. Measured at last as job 174 (L 658): as the daytime mechanism it FAILS (day row 0.81 / 0.86 / 0.88 -> 0.83 / 0.88 / 0.91 on draw 1, unmoved on draw 2, 2nd difference 0.74 -> 0.75 against a 0.19 deficit), with the night falsifier intact (0.99 -> 0.97) so the mechanism is ruled out and not the wiring. But the GUARD HOLDS, against both prior rejections — draw 1 t54 0.124 -> 0.177 TOWARD the donors' 0.190 with lows 1.000 -> 0.917, draw 2 t54 0.232 -> 0.263 — and it is score-LEVEL on both draws (complete row set: 0.332 -> 0.331, 0.371 -> 0.372; the published 0.309 -> 0.305 / 0.357 -> 0.355 was a reduced set and draw 2's sign flips, L 693) with TIR better on both and paired better on draw 2 (2.568 -> 2.056; draw 1's 3.040 -> 3.552 is mostly an unrefit level drift, 151.0 -> 150.1). So the open question is a CONFIGURATION one, not a mechanism one: should the reference run its own adopted default? **ANSWERED, and the reference's undocumented `--disable` is right: it STAYS OFF (L 661).** Job 175 (`afe1`, 580 e-pool events, real arm) drifts its level almost not at all — own pre-edit 143.3 against 143.5, so the level-only expectation IS the reference's own 1.34 / 1.28 / 1.11 and the whole move is the form — and level-adjusted it is **materially more damped: mean 1.35 -> 1.56, TIR 1.30 -> 1.57**, t70 1.09 -> 1.13, with mean rho 0.33 -> 0.31 and TIR rho 0.16 -> 0.14. t54 goes 0.56 -> 1.01, the one row toward the field, and t54 is a guard not a target, so it cannot buy the adoption. By the rule registered before the run it stays off with the measurement recorded, exactly as `ge_order` 3 did. The two halves disagree in full — a small cohort gain with the guard moving toward the donors, against one of the most damped prediction arms run — which is the clearest case yet that this reference has to be judged on both halves. L 657, 658, 661), `act_k` 1.5 (D, activity-keyed sensor error, Biagi 2018: the ONLY term that has moved the daytime sub-10-min deficit, and it hit a pre-registered number to three decimals — G7 day 0.780 -> 0.841 / 0.849 against 0.851 predicted, holding through a converged `resid_m` refit, night flat within draw noise, score better on both draws (0.309 -> 0.290, 0.357 -> 0.338) carried by tier 3, its own evidence domain. DECLINED on the two conditions registered before the run: paired SUM|dev| 3.040 -> 4.791 and 2.568 -> 3.405 against a ~0.8 separability bar — and NOT level drift, since the refit held the level and the paired bg_mean deviation actually fell — plus the guard, TDD 42.31 / 42.83 against 41.9 / 42.6 and t54 away from the donors on draw 2. **Change response MEASURED as job 179 (L 669)**: level-adjusted the MEAN ratio is EXACTLY unmoved (1.35 -> 1.35) while TIR goes 1.30 -> 1.48 and t70 1.09 -> 0.95 — and **why a measurement-only term does that is UNEXPLAINED** (L 670: smearing refuted by job 180, dispersion contra-indicated by L 662; it widens the CGM marginal sd by an iid-equivalent 13.6 mg/dL, almost all of it the trajectory rather than the sensor). Quote it as mean-neutral, TIR more damped, t70 / t54 nearer the field, TIR ranking halved (rho 0.16 -> 0.09); never as prediction-neutral. Off on the reference; usable at 1.5 for short-scale structure work as `ex_abs` is for exercise. L 659, 664, 667), `resid_m_diurnal` 0.9 (the residual LEVEL's time-keyed modulator, the same cosine adopted at ad3 for its fast and block parts: the first test of the residual's FORM and the one holder that escapes L 678's identity, since it has no glucose dependence and so cannot raise `lam`. Lands the night-lows GRADIENT on ice's donors and takes the LEVEL out the other side — per-person median night share 20.4 / 20.1 → 8.4 / 9.2% against their 28.1 — because the multiplier is blind to `resid_m`'s sign while its distribution is strongly negative, so no k separates the two. Level held on draw 1 (+0.55 mg/dL) and FAILED the registered ~1 on draw 2 (+1.77), guard held, score BETTER on both draws on the complete row set (0.332 -> 0.325, 0.371 -> 0.359), registered day-side cost did not materialise. Change response NEVER MEASURED — the e-pool arm was gated on the aim passing, and the `lam` argument alone is the claim L 655 / 667 had to withdraw. L 691), `sg_rate` 0.55 / 0.80 (A1e, the rate-keyed restoring force: **the one change that is MEAN-PRESERVING in a closed loop** - unrefit bg_mean 149.5 / 148.9 against the reference's 151.0 / 148.2, so the `resid_m` refit has nothing to undo, which no other low-side term has managed; it delivers ice's measured two states with nothing fitted, flat 0.114 / falling 0.246 / gain 2.16x against their 0.13 / 0.29 / 2.2-2.4x; and it confirms the descent brake, taking A1d's smooth form from t70 2.362 / 2.524 to 1.807 / 2.164 and t54 0.264 to 0.180. REJECTED on three counts: score 0.352 / 0.358 against 0.309 / 0.357 and paired 4.485 / 2.630 against 3.040 / 2.568; the draw split of L 602 for the fourth time (better where the reference's low side is weak, overshooting where it is strong); and MORE damped on the change half, level-adjusted mean 1.52 against 1.35 and TIR 1.46 against 1.30, which is forced because responding to an edit IS glucose moving. The decisive count is the SIGN: it suppresses fast motion (`fast_fall_share` G7 1.167 -> 1.011, `sigma_disp` 3.109 -> 3.058, `entry_fast_fall` 5.000 -> 4.762) and L 648 measures the twins as already 19% too smooth by day with the sensor exonerated. **Keep the keying though**: (G - G_slow) is how any future low-side term survives the level fit. L 643, 649), `sg_kappa` 0.15 (A1d, the saturating insulin-independent uptake: **the only mechanism that has ever closed the damped change response** — e-pool mean 1.33 -> 1.06, TIR 1.28 -> 1.06, t70 1.15 -> 1.08, and 1.22 -> 1.05 after its own level drift is taken out, where a uniform `sg_mult` cut carries nothing at all (observed 1.25 = its level-only expectation 1.25). After the `resid_m` refit held the mean exactly it costs bg_cv +6 points and doubles t70 and lows/day on all three draws, because the fit can only pay for a lost restoring force with a constant drift. **The second form settles it (L 642): the
  component is closed, not pending** — ordered by the dwell-weighted force kept, the cost is monotone across both
  shapes, so the choice is only (a) off, or (b) on for change-prediction work alone, as `ex_abs` is used for
  exercise, never on the cohort reference. L 637-639, 642), `sg_km` 63.2 / `sg_g0` 80.4 (A1d's SMOOTH form,
  Michaelis-Menten in absolute glucose, fitted to ice's corrected same-span bands at RMS 0.0008 /h: replicates the
  change response on mean (1.21 -> 1.06) and TIR (1.16 -> 1.05), moves **t70's the wrong way** (1.01 -> 1.24), and
  costs MORE on the low side than either kink — t70 3.97 / 3.93 / 2.91 against the donors' 1.60 and t54 0.58 / 0.70
  / 0.48 against 0.190 — with the level held exactly. Its premise was false: the kink leaves the sub-basal force at
  the full default by construction and this form is the weaker of the two below 130, because `excess = F(G) - F(Gb)`
  makes the force a low feels the SPAN AVERAGE from Gb (0.177 at G 65), not the local slope (0.242). L 642), `kabs_m` 1.14 (gut absorption at Dalla Man's identified 0.057
  instead of 0.05: a NULL on the labelled duration it was aimed at, x0.999, against a single-parcel prediction of
  x0.96 that two corrections could not rescue; scores marginally better than the reference on two draws of three and
  its one consistent gain — paired TDD on all three — is level-mediated and returns on refit, L 627, 629),
  `met_own` (per-person aerobic capacity from the donor's own p90 workout METs: sound for the 22 of 168 donors who
  record workouts, a measured no-op for the cohort, L 631), `csf_sd_w` 0.5 / 0.0 (a weight on the per-person meal-spread fit:
  **L 544's spread-versus-change-response trade does NOT exist on rf2** — weakening the fit moves the response ratios
  AWAY from the field (mean 1.33 -> 1.47 / 1.44, t70 1.15 -> 1.55 / 1.28, pre-edit level +3.3 -> +9.1 / +9.7) for a
  large per-person cost confirmed on both draws (paired SUM|dev| 3.040 -> 5.165 -> 10.168 and 2.568 -> 7.451 ->
  9.648; twin-donor TIR rho 0.815 -> 0.681 -> 0.425 and 0.830 -> 0.735 -> 0.456), while the weighted score barely
  separates the arms. L 544 measured the trade on sd3, whose DYNAMIC residual carried the damping; rf2 dropped it
  (L 592) and the spread fit is no longer the binding term. Stays at 1.0, L 634), `meal_lag` 10 / 20 (the gastric lag phase, genuinely missing — every
  carb parcel had delay 0 against Siegel 1988's ~20–30 min for solids. It works on an isolated parcel and does
  nothing on the cohort, because `peak_h` is onset-relative and so shift-invariant; the ratio drifts the wrong way,
  0.63 -> 0.59. Score level, tier 1 a little better at lag 20. L 595), `ge_beta` 1.3 / 1.6 (Elashoff power-exponential gastric emptying,
  with and without the mean emptying time kept: the twins' labelled pulses ARE the wrong shape — peak 37 min against
  the donors' 50, decay/peak 1.44 against 1.21 — and beta fixes that (1.25–1.33) while the fall / rise ratio does not
  follow at all (0.67 -> 0.70 against 0.89) and the score explodes (0.332 -> 0.43–0.55). Keeping the PARCEL's mean
  emptying time does not keep the GLUCOSE pulse's duration, which still falls to 102 min against 125. L 591), `pro_g_own` / `pro_carb_fix` / `pro_shift` (the low-side eating
  granularity: the twins' labelled low-onset pulses run 1.23x the donors' rate at 0.80x the size with the
  carbohydrate per hour below 80 already equal. Sizing from the donor improves TIER 1 on all three draws — t70
  1.803 -> 1.597 against the donors' 1.599, P(reach 54) and t54 toward them — and costs the dip-dynamics rows and
  the weighted score; the refractory does not bind at ~1 event per hour below 80, and lowering the onset only
  delays the response into a deeper low. The untried lever is how many events ONE low episode produces
  (`p_retreat` 0.34, the 20-min rescue gate), L 588), `ov_dur_own` (each override class's own log-duration SD, 0.70-0.78,
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
  exercise-focused work, L 554), `si_norm` 1.0 (**RESOLVED off, L 613**: its TDD rationale fell in L 597 and its change-response
  rationale fell on the e pool's 580 events — more damped on every outcome, mean 1.55 against the reference's 1.33,
  TIR 1.54 against 1.28, t70 1.33 against 1.15, TIR rho halved to 0.09. Stays at 0.92),
  `ge_spare` (A1c alone — **RESOLVED off, L 589**: re-run on the ov0 base it loses on
  score (mean 0.380 against 0.372; its L 561 t70 gain was on ad3, whose t70 ov0 has since partly fixed) and it does
  not move the target L 588 created for it — low-episode duration stays 25 min against the donors' 20, events per
  episode 0.62 → 0.61, low-side eating rate unchanged. At G 65 its sparing is 0.20 mg/kg/min, ~3.7 mg/dL per 30 min,
  the same too-small class as A9's 2.4; the missing hepatic term is ~3x either), `ge_split` (glucose effectiveness from named parts: rejected for too many lows and superseded by the C4 threshold
  fix on change prediction, L 548, 555. **It CANNOT carry the defense shape and is withdrawn as the route, L 637**:
  with it on the slope is `sg_p` below Gb and `sg_p + sg_h` above, because A1b is modelled as the liver WITHHOLDING
  output above basal, so the high side is ≥ the low side by construction — against ice's learned profile it is 2.4x
  too WEAK below Gb (0.070 /h against 0.170) and 15x too strong above it, which is exactly why L 548 found too many
  lows. Cutting `sg_h` alone only flattens it to that too-weak `sg_p`), `ex_dur_cap` (the cap without the METmax fit — leaves almost no hard session, L 554), `prof_deliv` off, `unent_light`, `unent_split`, `ge_var` off,
  `entry_size_b`, `heat_a`, posture off, `kappa_ins` (needs Best 1981's insulin levels), G7 common error 1.0.

## Analysis traps (each cost a session)

- **Never read a live parameter value from its dataclass default in `physiology.py`** (L 640). `person.py`
  overrides most of them per sampled person, and the two can disagree badly: `kappa` is declared 0.15 but drawn as
  `kappa_mult * exp(N(0, 0.4))` with `kappa_mult` 1.0, so the live median is **1.0** — L 303's adopted Bergman
  value, 6.7x the default. Reading the default suggested that `sg_kappa` left no disposal path scaling with
  glucose, which is false and nearly bought an arm. Check a built person's value, as the `--enable k=v` and
  `BEHAVIOR_COLS` traps already require.

- **A cross-group test only excludes what VARIES across the groups** (L 659). Splitting the donors' daytime
  2nd difference by SENSOR FAMILY came back family-independent, and I had told a peer that this meant the body.
  It does not: it rules out a family-SPECIFIC sensor property (noise level, filtering, lag, calibration) and
  leaves untouched a wear or motion artefact common to every CGM class, since G6, G7 and Libre 3 all sit in
  subcutaneous interstitium under tape and would all be affected alike. Before reading a null across groups as
  excluding a whole mechanism class, write down what the grouping actually varies — and look for the WITHIN-group
  cut that varies it (here, insertion site, which no donor record carries, so the attribution is simply not
  decidable from this data). When attribution is undecidable, a candidate must be judged on its own evidence and
  never on closing the row, because closing it is consistent with every surviving hypothesis.

- **The non-insulin force regressed on glucose velocity is the IDENTITY, not a response** (L 644). `dG/dt` is
  mostly made OF that force, so the slope comes out near 1 whatever the body does — measured, 0.88 of the velocity
  in 90-180, where 1.0 is what a constant insulin term alone would give. It cannot be compared with an
  interventional `d ICE / d r` from a probe that imposes the velocity exogenously. To ask how long a force drop
  lasts, measure the force's deviation from its OWN level-conditional mean and carry that forward a step
  (`momentum.py`); to ask how it responds to motion, impose the motion.

- **A force expressed as `excess(G)` is felt as the SPAN AVERAGE from Gb, not as its local slope** (L 642). Where
  a term applies `sg x excess(G)` and the excess is built as `F(G) - F(Gb)`, the restoring force at G is
  `sg x excess(G) / (G - Gb)` — an average over everything between Gb and G. So a form whose slope near lows is 90%
  of the default can still deliver only 66% of the force at G 65, if the span from Gb crosses a saturated region.
  Quoting the local slope as "the near-low defense" inverted a whole arm's low-side prediction. Compute the force
  profile from the real step path at the glucose levels that matter, and the dwell-weighted total beside it — that
  integral, not the shape, is what the cohort cost tracks.

- **State a falsifier as "no more than draw noise", never as "not at all", for anything measured downstream of
  the controller** (L 664). `act_k` is keyed to activity, which is identically 0 while asleep, so I registered
  "if the night row moves at all, the wiring is broken". That is wrong in a closed loop: a daytime-only term
  changes doses, which changes the following night, so a correctly wired arm still perturbs the night a little.
  The right standard is the arm's move against the draw-to-draw scatter of the same row — here G7 night moved
  0.005-0.015 against a 0.027 difference between the reference's own two draws, which passes. A falsifier
  stated absolutely would have thrown away a sound arm.

- **When a quantity is a RATIO OF TWO ENDOGENOUS OUTCOMES, stop hunting the mechanism and build the
  exogenous experiment** (L 674, 676). `g/dose` — the glucose response to a settings edit over the
  delivered-insulin response to the SAME edit — is a Wald estimator whose exclusion restriction fails, because
  an ISF/CR/target edit changes the timing and shape of delivery and not just its total. Six accounts of its
  variation were tested on closed-loop outcomes and all six failed (controller under-delivery, measurement
  smearing, unequal need, `kappa`'s kink, the renal term, the delivery-to-need covariance), because there was
  no structural quantity there to find. ONE open-loop measurement against `physiology.Body` — no controller,
  insulin varied exogenously, each configuration bisected to a matched glucose level — settled it in a single
  table. Smoke-test such a driver on two cases before queueing it: on this one that caught `sg_mult` not being
  a `BodyParams` field (`person.py:270` applies it at sampling) and an uncalibrated level of 216 mg/dL sitting
  ON the per-person renal threshold, either of which would have been read as a result.
- **An inference about an instrument is not a measurement of it, and I published one as the other** (L 669,
  refuted at sensor scale by L 670, **scale-resolved and CLOSED at L 671: the CGM's width moves the TIR ratio
  by only ~0.008 per mg/dL, so nothing in this record needs a TIR discount and the mean-row rule is right in
  principle and irrelevant in practice**). `act_k` 1.5 touches nothing but measurement error and yet moves
  TIR's level-adjusted ratio 1.30 -> **1.48** and t70's 1.09 -> **0.95** while leaving the mean's **exactly**
  at 1.35 (pre-registered, level-corrected — the observation stands). I explained it as threshold smearing by
  the added CGM noise and wrote the consequences into LESSONS, COMPONENTS and this overlay. **Job 180 refuted
  the mechanism**: adding synthetic iid noise to the reference's own saved CGM, 0 to 3 mg/dL, moves TIR's
  ratio 0.02 and its response +0.3% against `act_k`'s −13%, with t70 non-monotone and the mean flat (so the
  probe works). Withdrawn with it: any TIR discount on L 656 / 661 / 649, and the corollary that the twins'
  TIR under-response is "worse than 1.30" because the field's CGM is already smeared. What the probe DID find
  is that `act_k` widens the CGM marginal sd 48.95 -> 50.79, an iid-equivalent **13.6 mg/dL** where its noise
  term can add only 2-4 — so most of it is the BODY's trajectory changing through Loop's dosing, which makes a
  smaller TIR response a REAL consequence of the arm rather than an illusion. Job 181 swept to sd 20 and
  settled it (L 671): TIR's ratio rises monotonically to 1.43 and t70's falls to 0.82 with the mean flat, so
  the density argument including t70's sign is confirmed in FORM, while at `act_k`'s own 13.6 it accounts for
  only ~43% of its TIR move, over-explains t70 and gets t54's sign backwards. Residue still open; artefact
  bounded at <= 0.03 for any realistic sensor-noise difference. The rule: when an interpretation
  rests on an untested mechanism, register the test and quote the OBSERVATION as the finding until it returns,
  and never carry such a mechanism into a claim about the model's standing limits — a "held loosely" label
  does not make an inference a measurement.
- **Beyond the level, the pre-edit DISTRIBUTION does not carry the response ratio — so a damping result is a
  fact about the component** (L 662; its eight-arm null and matched pair are now ALSO what L 670's open observation has to be squared with). The obvious extension of L 638's level trap is that a wider or
  higher-excursion arm would respond differently for free, and it is measured FALSE: across eight real e-pool
  arms, level-adjusted damping correlates −0.17 to −0.43 with dispersion (the wrong sign for the story), and
  a matched pair settles it — **but NOT the pair quoted here, which does not reconcile (L 672): the saved
  canonical logs give `sk1_e` and `sr1_e` own levels 157.0 / 155.4 and responses 1.06 / 1.04, nearly identical,
  and both are force-CUTTERS, so they were never an informative pair. The verified pair is `afe1` and `akfe1` —
  level 143.3 / 142.8, sd 52.0 / 52.1, t180 20.6 / 20.9, matched to a tenth — responding 0.865 against 1.002,
  a 14% difference at matched dispersion.** Correct for the level, which is real, and
  then read the ratio as the mechanism's. This is also what refuted L 656's explanation of its own result.

- **Label an arm from its own `meta.json` / `cohort.json` IN the script that reads it, and print the labels
  beside the numbers** (L 672, extending L 663). A name is a hypothesis about an arm; the config is the arm.
  `sr1_e` is not the `sg_rate` arm — it is the smooth A1d form WITH `sg_rate` on top — and `sg_rate` alone is
  `rt1_e`, whose 1.52 / 1.46 the record correctly quotes. I picked `sr1_e` by name in the very script that
  cited L 663's rule against doing that, and only the meta.json check caught it. The same check found that
  L 662's matched pair names two force-cutters with near-identical responses, which cannot support the
  contrast it draws.
- **The no-op versions of corrected arms are still on disk, under the SHORTER and more obvious names** (L 663).
  `hl_e`, `sw0_e` and `sw5_e` are each bit-identical to the reference over 60/60 events; the real arms are
  `hl2_e`, `sw0b_e`, `sw5b_e`, which L 603's fresh-name rule created BECAUSE the first versions no-opped. The
  record is right and the directory is the trap: pick arms from the lesson that recorded the result, never
  from an `ls`, and run the bitwise `truth["cgm"]` check over every arm of an assembled table before reading a
  number from it.

- **A change-response ratio is meaningless without its arm's own PRE-EDIT LEVEL** (L 638). `dG/dI = -SI·G /
  (SG + SI·I·…)` is proportional to G, so an arm whose pre-edit level drifts up responds more to the same
  proportional edit with no mechanism at all. Every arm compared on the e pool before `sk1` drifted +3.3 to +9.7,
  small enough to ignore; `sk1` drifts +19.1, where the drift alone moves the mean ratio by 0.11. Read the
  level-only expectation — `ratio_ref x (level_ref / level_arm)` on the arms' own median pre-edit mean glucose —
  beside every ratio (`change_e/score_change_lvl.py`), and treat an arm whose observed ratio EQUALS that
  expectation as having no mechanism whatever its raw number looks like. That is exactly what the uniform
  `sg_mult` cut turned out to be (observed 1.25, expected 1.25) — **but that reading is now contradicted and
  the correction itself is the suspect (L 682)**: open loop at 60 people, `sg_mult` 0.40 responds at 1.399
  of the reference and 0.67 at 1.183, structurally x1.36 and x1.17 once their own 1-3% levels are taken out.
  `ratio_ref x (level_ref/level_arm)` is derived for a FIXED force and `sg_mult` changes the force, so for
  such an arm the level correction and the mechanism are not separable. Keep the correction for arms that
  leave the force alone; **do not cite `sg4_e` as its validation**, and quote L 638's `sg_mult` verdict with
  this attached.

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

- **Do not fit a parameter against an unreachable target** (L 606): it runs to its clip bounds and damages the rows it
  CAN affect. Re-targeting `twin_isf_mult` to TDD improved four tier-1 rows but widened the per-person ISF spread from
  [0.88, 1.33] to its clips [0.70, 1.43] and consistently worsened `acf_zero_min` (+0.243), `circadian_amp`, `night_cv`
  and `ice_dip_day_share` on all three draws. TDD is unreachable by a body parameter (L 605); t70, its current target,
  is reachable but noise-dominated (L 602). A second fitted parameter needs a target that is both.

- **Use `twin.csv`'s paired diff for anything per-person** (L 598): a cohort median compares 112 sampled twins with the
  206 donors who have step tables, so it measures composition, not the model — it inflated the insulin surplus from
  +1.4 U/day paired to +3.9, and a ratio of medians turned a matching basal-withholding ratio (0.74 against 0.73) into
  a fictitious 67%-against-83% defect.

- **Judge every candidate AFTER the `resid_m` refit, and expect level-mediated effects to vanish** (L 597): the refit
  holds the donor's glucose level, so any gain that runs through the mean is converted back. Three gains died this way
  — `rs0`'s TIR response (1.22 -> 1.69), `cb2`'s whole response, `si_norm`'s TDD. What survives is a change acting on
  something the level fit cannot see: dynamics (`rf2`'s t70 response) or the shape of excursions below a threshold
  (`sg_h_lo`'s t70).

- **A statistic conditioned on an event the candidate changes the INCIDENCE of cannot measure that candidate**
  (L 596): `sg_h_lo` prevents the easy lows, so nadir counts fell 1874 -> 1607 and the surviving 60-70 nadirs were a
  harder, insulin-driven subset — the recovery statistic moved the wrong way while the unconditional rows (t70,
  episode duration) showed the real effect. Prefer unconditional rows when a candidate changes event rates.

- **`peak_h` and `dur_h` in the labelled-meal tables are measured from the LABELLER'S detected onset, not from the
  carb entry**, so both are invariant to a pure time shift: a gastric lag moved them not at all (peak 43 min at lag 0,
  10 and 20 alike), and the twins' "peak at 43 against the donors' 50" is a RISE-SHAPE difference, not a timing offset
  (L 595). Check what a statistic is referenced to before building a component to move it.

- **Donor carb entries are keyed `grams` in `carbs.json`, not `carbInput`** — the wrong key gives 0 g for every entry, and
  any size filter then drops them all with no error (L 571).

- **`gap = |d50| + 0.5*|spread|`, so an arm can be charged on a row where its median is IDENTICAL** (L 696).
  On the corrected labels `pulse_peak_h` is 0.622 for the reference and every appearance arm while their gaps
  run 0.069 to 0.170 — entirely the spread half. A score difference attributed to a median is wrong whenever
  the medians agree, and my pre-registered arithmetic for `ge_order` 3 ignored it. The same derivation also
  **priced a row from a number belonging to a different arm** — L 627's 1.775 is `ge_order` 3 PLUS `kabs`
  0.057, while `go3`'s own duration is 1.863 — the L 663/672 trap inside a derivation rather than a directory
  listing. Read the arm's own row out of the log before predicting what it is worth.

- **When a candidate's whole effect flows through ONE scalar, price it from an already-failed arm before
  running a new one** (L 694). The deviation-keyed level holder collapses every person's night drift into a
  band around a single r0, so fitting night share against drift on the reference and retrodicting the
  declined r0 = 0 arm out of sample (predicted 7.67 / 9.12 against observed 8.38 / 9.20) priced the whole
  class for one read over saved pickles, and declined it. Register the retrodiction as a GATE, not a
  diagnostic: the fit is estimated ACROSS people and read as if it applied WITHIN one, and that gate is the
  only thing testing it. Quote the bracket across draws (here r0 −21 to −31), never a value.

- **A reference arm that does not reproduce its own published score means the ROW SET changed, not the arm**
  (L 692, 693). `score.py` scores a statistic only where it is present for BOTH runs. Job 193 omitted
  `meal_response` and `lifestats sim`, dropping nine rows (n 51 -> 37) including tier-1 `act_net20` — **and
  that reversed the arm's score sign**. Separately, nine arms carried a 13-column `life_stats.csv` against the
  reference's 17, because their jobs ran post-processing from their own frozen tree and four pulse rows had
  been added since: **a file's existence says nothing about which code version wrote its columns, and its
  mtime does not order code versions** (`af1`'s copy is NEWER and narrower). Check the COLUMNS a scorer needs,
  not the path — the `BEHAVIOR_COLS` signature one level up. **RESOLVED as job 196**: all thirteen arms are on
  one version at n 51 / 54, the reference's 0.332 / 0.371 survived regeneration unchanged, and of the four
  restated records only `act_frag` draw 2 changes sign (−0.002 -> +0.001, a tenth of the floor, so "level on
  both draws", not "marginally better"). **Then the donor meal labels themselves were corrected (L 695), so
  the current pairs are: reference 0.328 / 0.366 / 0.404 / 0.402 / 0.374, `act_k` 1.5 **0.307 / 0.339**, its
  refit **0.308 / 0.332**, `day` off **0.330 / 0.359**, `act_frag` **0.327 / 0.365**, `resid_m_diurnal`
  **0.321 / 0.352**.** No score from before 2026-11-04 compares with one after it. **Post-processing belongs
  on the current analysis tree, not the arm's frozen one — the simulation is frozen on purpose, the measurement
  is not.** Caveat on the complete set: `pulse_peak_h` and `pulse_dur_h` are scored against L 626's stale donor
  labels (gap 1.042 identical on both sides; donor `pulse_dur_h` 1.917 where like-for-like is 1.577), so quote
  score DIFFERENCES, never the absolute level, until the scorer reads ice's `ice_v32/meals_fit/`.

- **A `score --detail` log's first arm is the first ARGUMENT, not the donors**, so fixed awk column indices are off by one
  arm and silently report the wrong arm's numbers (it happened three times on 2026-11-01). Key on the header
  names, never on a column index. (This entry used to point at `resid_tools/score_read.py`; **that file no
  longer exists anywhere under `~/.loop-eval` as of 2026-11-03** — a run-dir tool lost to a cleanup while the
  instruction to use it stayed here, which is L 666's drift in miniature. Verify a tool this overlay names
  before building a job script around it; job 193's first draft called it and would have failed.)
  The scorer itself is a module: `python -m loopeval_analysis.patient_sim.score <ref> <arm> --detail`, one
  call per draw.

- **Keep the summary CSVs, drop the traces.** A cohort arm is ~814 MB, of which the `v0*` per-person directories are
  ~95%; `compare_pilot.csv`, `sim_stats.csv` and the other summaries are a few MB and are all `score.py` reads. A full
  Mac stops a running job mid-arm (`OSError: No space left on device` writing a person's `.err`), so clear superseded
  arms with `rm -rf <arm>/v0*` — every arm stays re-scorable and re-comparable, and the traces are reproducible from
  the frozen tree. This recovered 141 GB from one run dir (177 G to 36 G) on 2026-11-01. **The cost is that it
  turns every cleaned arm's NAME into a trap the cache rule does not cover (L 687)**: the dir has no `v0*` to
  cache, so the people re-simulate, while the summary CSVs the scorer reads are still there and days old — so a
  partial run gets scored on stale numbers, and the knob check reads the OLD `cohort.json` and reports the knob
  ABSENT for a correctly wired arm. Job 193's pre-flight caught `rm1` / `rm1_5k` held by the 2026-11-01
  `resid_meal` arm (L 568) on different templates. **Check a candidate arm name with `[ -e <dir> ]` before
  queueing, never by globbing `<arm>/v0*`**, and do not let two components share an abbreviation.

- **`trace.json`'s md5 is NOT an identity check.** Two identical invocations of the same frozen code produce
  byte-different `trace.json` (key order and float formatting) with content and trajectory identical. Compare
  `truth.pkl`'s `truth.bg` series instead — that IS bit-stable, and it is stable across `--n` and `--par` too, since
  every person is drawn and seeded from `seed0 + i` alone. An md5 mismatch "proved" a reversal had failed (L 586).

- **A new template column needs adding to `person.BEHAVIOR_COLS`** — that allowlist is what reaches the person as
  `traits["template_rates"]`, so a column the templates carry and `sample_behavior_traits` reads is silently absent
  without it, and the arm runs as its own control (`ov_dur_own` scored bit-identical to its `--disable` control
  before this, L 586). Same signature as the `--enable k=v` trap: check a built person's trait, not the CSV.

- **Removing a job from `jobq/pending` does NOT stop it** — the runner may already have moved it to `running/`. Check
  `jobq/running` and the runner log before assuming a pulled job did not execute: a hookless first version of an arm
  ran, populated its output dirs, and the corrected re-queue then read them from CACHE and scored bit-identical to its
  control (L 603). Use fresh arm names for the corrected run.

- **An arm rerun into an existing output dir returns the CACHED previous run** (`v0… cached` in its log), so a fixed
  arm can come back byte-identical to the broken one it replaces. Use a fresh arm name, or clear the dir.
  **Fourth sighting, and the second where the no-op carries the shorter name (L 681)**: `ul70` holds
  `unl_mult=0.70` in its own `cohort.json` and is bit-identical to `rf2`, its log reading `v01000 cached`;
  the arm that ran is `um70`, with `ur1` an exact duplicate of it. Picking `ul70` by name would have measured
  the load lever's gain as zero and killed the pair candidate for the wrong reason. The bitwise `truth.bg`
  check run BEFORE reading any number is what caught it, which is the whole point of the rule.
  **FIFTH sighting, and it is a different mechanism that this rule's own check would MISS (L 687)**: a dir
  whose `v0*` have been cleaned away (the disk rule above) has nothing to cache, so the people re-simulate
  and `truth.bg` differs — the arm passes the bitwise check — while the stale summary CSVs and `cohort.json`
  sit there ready to be scored. So state the rule as about the NAME, not the cache, and pre-flight it with
  `[ -e <dir> ]`. Job 193's `rm1` was held by the 2026-11-01 `resid_meal` arm (L 568).
- **A numeric knob must be verified as a NUMBER where it enters, and there are now THREE ways it silently is not**
  (L 554, 655). `--enable k=v` makes a switch named `k=v`; `--set` parses to float and is safe; an `ARM_ENABLE`
  JSON **integer** was dropped outright until 2026-11-02, because the guard tested `isinstance(v, float)` and
  `isinstance(3, float)` is False — which cost `ge_order` 3's whole change-response verdict. All three have the
  same signature, an arm that reproduces its control exactly, and all three are caught by the same two checks:
  compare `truth.pkl`'s `truth.bg` across the arm and its control, and look for identical `variant` values in
  `score_change.py`'s output. Run both on every arm; never read a ratio alone. **The 2026-11-02 fix was itself
  INCOMPLETE and the second pass is the lesson (L 660)**: it replaced 106 guards in `world.py` and left
  `cohort.py`'s 14 (`sg_mult`, `csf_mult`, `kappa_mult`, `csf_sd_w`, `basal_share`, `isf_level`, `csf_lvl`, …)
  and the entire residual block (`resid_m`, `resid_skew`, `resid_diurnal`, `resid_tf/tb`, `resid_meal`,
  `resid_day_ar`, `ppr_b/l/d`) — including **`resid_mult`**, where a JSON `0` would default to **1.0** and turn
  the dynamic residual back ON at full strength in an arm written to run the reference. **A fix counted in call
  sites is not a fix scoped to a class: the grep that found the bug must come back EMPTY over the whole package
  afterwards**, with the legitimate survivors enumerated so the empty result is checkable (today: a NaN guard in
  `person.py`, rounding in `insulins.py`, `_num`'s own docstring). Claiming a class closed on a partial sweep is
  worse than not claiming it, because the next reader stops looking.
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
