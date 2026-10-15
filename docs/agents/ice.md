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
