<!-- Role overlay. Loaded via ROLE.md; see AGENTS.md → Roles. -->

# Role: reduction — surrogate dosing functions with far fewer inputs

LoopAlgorithm reads more than 24 h of glucose, every dose, every carb entry and a full set of
schedules, and returns one number: the insulin for the next 5 minutes. This role looks for much
simpler functions g of a small input set — the recent glucose trajectory, a long-term scale such as
TDD, a variability measure, a little insulin state, carbs only as an optional extra — that reach the
same or better outcomes. Mandate: Pete's brief, `REDUCTION-BRIEF.md` in this checkout (git-ignored).

Read with **AGENTS.md** (shared) and **docs/agents/verification.md**. A surrogate is judged by what it
does in closed loop, never by how closely its doses match Loop's: TIR up AND t<70 down, t<54 as the
guard, on the same suite and the same dial as the reference.

## The reference and the bar

- **Reference = LoopAlgorithm as the fleet now scores it: the `gr` arm** (guard + runway, frozen
  2026-10-24) with each donor's deployed config, run through the `dr` harness
  (`runs/2026-10-23-frontier-dosing/dr/run.py`). Stock Loop is reported beside it.
- **A surrogate's own scale is its dial.** It is swept on its TDD / gain scale and compared against
  the reference swept on insulin-needs, by the ledger's scoring rule (docs/FRONTIERS.md → Scoring,
  `loopeval_analysis.band.band_report`). Matching or beating the reference curve in the operating
  band is the claim; movement along it is not.
- **Low-side change is judged on the ICE generator**, not replay alone: replay overstates the change
  in t<70 about 8× (myloop lesson 10) and flags only.

## Evaluation suite (fixed; reused, not rebuilt)

| Tier | Bed | What it tests |
|---|---|---|
| A | Donor replay, pilot `ice_v32`, `dr` harness windows (last 28 days + warm-up), entries on | Outcomes on real people under deployed config |
| A′ | Same, `--no-carb-entries --no-user-boluses` | Missing meal information |
| B | ICE generator (gr reference trainings) | Change in outcomes on a body with a known answer; t<54 guard |
| C | Additive sim (`patient_sim.cohort`, current reference) | Ground truth, sensor noise, exercise, settings mismatch, larger / delayed meals |

Iteration runs on a fixed stratified subset of tier A; a surrogate that survives goes to the full
pool, then B and C. Every result names its commit, binary, command and run dir so review can rerun it.

## How a surrogate plugs in

LoopEval has no hook for a non-Loop controller: `DosingEngine` hosts only `LoopAdapter` and
`OpenAPSAdapter`. Surrogates run through an **external-controller adapter** (proposed to Pete
2026-10-30, branch-only until he approves): each cycle the engine sends a process the candidate's own
state and gets back a dose — the same pattern as `--external-plant`. Delivery is shaped as automatic
boluses with the temp basal used only to withhold (Pete 2026-10-29: no basal controller).

## Where the work lives

- `docs/reduction/LESSONS.md` — this role's lessons file; `docs/reduction/TABLE.md` — the living
  comparison table (inputs, form, metrics, failure modes) once there is something to put in it.
- `analysis/reduction/` — surrogate definitions, feature extraction, fitting and scoring drivers.
- `runs/YYYY-MM-DD-reduction-*/` — experiment outputs, with the driving script beside them.

## Standing cautions

- **Inputs that read delivered insulin are circular.** TDD rises with the insulin the controller
  gives; a gain keyed to it can run away. Fit scales on a window before the scored one, and test what
  repeated application does.
- **Imitation is a diagnostic, not a target.** Fitting g to Loop's own decisions measures how
  low-dimensional Loop's map is; the candidate is then tuned and ranked on outcomes.
- **One-sided actuation.** Insulin cannot be removed: safety at the low side comes from stopping
  early, so every form is checked for dosing under falling or low glucose, and out of its training
  range (bounded, monotone in glucose and insulin state).
- **Narrow-distribution wins are flagged**: a form tuned on the iteration subset is re-scored on
  people and weeks it never saw.
