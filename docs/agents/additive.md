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
- **Scoring**: `cmp_full.py` (eda's 51 statistics, KS against the donors), `review.py` (each component against its own
  target), plus the measure scripts beside the run. Arms of a neutral change scatter 27–31 matched: read differences
  inside that band as noise.
- **Current reference** (2026-10-19): c277 — yardstick ISF × the body-model sensitivity fit (`fit_body --regression`), delivered-shape basal need with the night level from steady
  nights, donor-MET exercise intensity with the C4 surge; 29 of 51; t70 1.73 vs 1.67%, t54 passes.

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
