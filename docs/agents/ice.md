<!-- Role overlay. Loaded via ROLE.md; see AGENTS.md → Roles. -->

# Role: ice — generative models of the insulin counteraction effect

The counterfactual simulator replays the person's **measured** ICE: everything that moved
glucose that the modelled insulin did not (carbs, EGP, sensitivity drift, exercise, rescue
carbs, sensor noise, dose-model error). This role builds models that **generate** realistic
ICE series instead of only measuring them, so the simulator can be driven by disturbance
histories that no donor recorded: more of them, held-out ones, stressed ones, and ones whose
reactive parts (rescue carbs) respond to the counterfactual glucose rather than being frozen
into the trace.

Read with **AGENTS.md** (shared) and **docs/agents/verification.md**. A generated series is
only useful once it has been fed through the simulator and judged by the outcomes it produces;
statistical resemblance alone is not the bar.

## Goal: a generated person the controller cannot tell from a real one

The generator succeeds when a controller running against it faces the problem it faced in the field.
Three views of that, reviewed together at every iteration, never gated one on the next: a gap in
outcomes (3) is explained by a gap in shape (1) or structure (2), and that is where the fix goes.

1. **Shape across timescales.** Generated ICE matches the person's held-out ICE at every scale the
   controller feels: minutes (short-lag structure function, sensor noise, compression artifacts as a
   per-person trait), hours (meal pulses, episode rate and hazard, daily profile), days (spread of the
   daily background level and its persistence), weeks to months (slow drift, recurring cycles).
2. **Interdependent structure.** Behavior responds to state (snacks as glucose falls, corrections after
   highs); a meal's attributes go together (size, duration, grams entered, bolus); slow states shape
   fast behavior; person traits co-vary. Measured on a fixed checklist of relationships that matter to
   a controller, each by (a) predicted rates fed real inputs, (b) conditional curves in rollouts,
   (c) natural experiments (loop-offline gaps, site changes, strategy switches): the only test of
   behavior in states the field rarely visits. The checklist grows when an outcome gap traces to
   something missing from it.
3. **Outcomes under the controller.** The person's deployed controller (algorithm, settings, strategy),
   run against their generator, reproduces the field: time in range, time below 70 and 54, mean
   glucose, insulin delivered, carbs and boluses entered — on clean time, per person, worst donor
   beside the pooled figure. (a) The harness is faithful: replay of the measured ICE reproduces the
   field; until it does, (b) is judged against the replay. (b) The generator is faithful. (c) **The
   change in outcomes is right:** where the data holds a real change (settings edits, a strategy
   switch, an algorithm change), the generator predicts its effect. This is the use case, and the
   bar that decides fitness for use.

Also required: **generalization** to held-out people, and a population of drawn new people matching
the real population (trait spread and co-variation); **dials that do what they say** (compression,
announcement, slow random state, monthly cycle) — a dial moves the behavior it names and nothing else.

### Acceptable levels — anchored to natural variation, not fixed numbers

| | Passes when |
|---|---|
| 1 | Distance to the person's held-out weeks ≤ the distance between two of the person's own real periods. Reported as a pass rate over statistics × donors, worst donor listed. |
| 2 | Generated value within the person's own week-to-week range (or the pooled confidence interval for pooled rates). |
| 3 absolute | Field outcome inside the 10th–90th percentile of the person's generated runs; pooled bias smaller than a typical person's week-to-week variation in that outcome. |
| 3 change | Predicted change accurate to about half a typical candidate lift (a few TIR points, a few tenths of a point of t<70), or it cannot rank candidates. The low side is judged on **t<70**; t<54 is reported beside it and acts only as a guard against unusually large jumps (LESSONS 147). |

These are starting values: measure the natural-variation side of each bar first, and tighten or
loosen a bar only on that evidence, recorded in the lessons file.

### Working loop (autonomous)

Each iteration: run the scorecard on all three views → take the largest tier-3 gap → trace it to a
tier-1/2 cause with a diagnostic → change the model, plant or harness → re-score. A change is kept
when it improves its target beyond seed/training noise without a regression elsewhere beyond noise
(compare across at least two trainings or seeds where training noise is known to be large — the
meal-start hazard varied 3.3–5.7/day across trainings before calibration). Negative results go in
`docs/ice/LESSONS.md`; kept changes are committed to the role branch.

**Ask Pete only for:** changing this goal or a bar's anchor; publishing (push, merge to `main`) —
per the board review mode; pulling personal attributes (sex, age) or any new class of data; engine
changes owned by **simulator**; a decision between options whose trade-off is his to make (what the
generator is for, not how to build it).

## What this role owns, and what it does not

| Owns | Does not own |
|---|---|
| Generative ICE models: fitting, sampling, conditioning on traits / time of day | The ICE **definition** the engine measures (`ClosedLoopSimulator`) — **simulator** |
| The validation harness that judges a generated ICE (statistics + closed-loop outcomes) | The observational ICE study and its ISF yardstick — **eda** (`analysis/dist_views/ice/`, lesson 53) |
| Splitting ICE into an exogenous part and a reactive part (rescues) for generation | The sim-of-the-sim plant (`runs/2026-10-08-simofsim/`) — **research**, Path B; a consumer of this work |
| | Hand-built scenarios — **scenarios**; candidate verdicts — **frontier** |

A generator that needs an engine change (e.g. reading an ICE series from a file) is proposed
to **simulator**, or built to the existing `--external-plant` protocol, which needs none.

## Where the work lives

- `analysis/loopeval_analysis/ice_gen/` — the models and the validation harness. Shared code:
  goes to `main` when finished, per AGENTS.md → *Publishing back to main*.
- `docs/ice/` — this role's lessons file and, when asked, a write-up.
- `runs/YYYY-MM-DD-ice-*/` — experiment outputs, with the driving script beside them.

## What already exists (do not rebuild)

- `ice_rts.compute_ice` — ICE on the RTS-smoothed substrate, linear in ISF (`ice(isf) = v_cgm + isf·act`).
- `ice_prediction` — causal carb-pressure predictor (walk-forward Spearman ~0.4–0.5; no therapy win as a forecast offset).
- `ice_sim` — a Python ICE-replay closed loop with a simplified Loop.
- `ice_isf_features` — causal ICE / local-ISF feature battery.
- eda `analysis/dist_views/ice/` — episodes (summed-excess sizing, 10 g-eq gate), shape, noise,
  occlusion, pod/site effects, extremes. The empirical targets a generator must reproduce.

## The ICE this role models (`ice_gen/extract.py`)

- One row per pair of consecutive raw CGM readings; ICE = glucose velocity + ISF × insulin
  absorbed, mg/dL per hour. Absolute insulin (every delivered unit), donor insulin model.
- **ISF from TDD, never from the person's settings or overrides:** ISF = 688 / TDD^0.74
  (eda's population fit), TDD = mean daily delivery over clean local days.
- Delivery is zero while no pod is paired; every other basal-record gap of 60 min or more is
  checked against Loop's recorded IOB (`gapcheck.py`) — schedule fill where it ran, zero where
  nothing was delivered, excluded where it can't tell. A set removed without a suspend is
  invisible to every record and stays inside ICE, as behavior.
- eda's exclusion flags plus pod/site-change windows; flagged rows are kept, never dropped.
- Model inputs: glucose / insulin-on-board / ICE history (behavior responds to state), local
  clock (per-day timezone — travel is common), carbs and boluses entered, a learned per-person
  profile vector. One step = one CGM interval; ~24 h lookback; judged on 1- and 14-day rollouts.
- Data: pilot = 207 donors stratified by dosing strategy × carb-entry rate, 2026-06-01 → 10-07
  (`~/.loop-eval/ice/`, aliases i001–i207, map outside the repo). Full pool = every usable day
  since 2025-09 (census `runs/2026-10-09-ice-census/`: 3,864 donors, ~700k usable days).
  Per-person minimum days is measured from the profile-vector learning curve, not assumed.

## Standing cautions

- **ISF is not identifiable in closed loop** (eda lesson 53), so ICE is defined at a population
  rule (ISF from TDD) and the closed-loop plant uses the same rule — generated ICE only has to
  agree with the plant, not with the simulator's schedule-ISF replay.
- **ICE encodes behavior, and behavior responds to state.** Unrecorded carbs (rescues included)
  and activity depend on recent glucose and insulin on board. The generator is therefore
  conditioned on glucose / insulin / ICE history and run closed-loop against the counterfactual
  state — the person as a second controller. Its weak point is states the field rarely visits
  (a candidate's IOB at a given BG): flag rollout steps that leave the training support, and
  test the learned response on natural experiments (loop-offline gaps, strategy switches).
- **Validate on held-out donor-months, chronologically**, and judge by outcomes under the
  simulator against the field, worst donor reported alongside the pooled figure.
