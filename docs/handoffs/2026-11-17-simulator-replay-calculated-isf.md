# Replay's body ISF should default to a calculated ISF, not the person's schedule

From: adaptive. To: simulator (engine default), frontier (`dr` harness). 2026-11-17.

**Decision (Pete, 2026-11-17):** "replay should default to a calculated ISF that is appropriate for them, not their
scheduled isf."

**Current behaviour.** In counterfactual replay the body's ISF, the gain that turns a candidate-vs-field dose difference
into glucose, comes from `ClosedLoopSimulator` `physiologySensitivity`:
1. `--patient-isf` set: a flat absolute ISF.
2. `--candidate-infer-sensitivity`: the person's scheduled ISF times an inferred m(t).
3. Otherwise: the controller's scaled ISF, so the body moves with every ISF or needs sweep.

The `dr` harness passes `--candidate-infer-sensitivity` (`pc.COMMON`), so every tier-A replay ran the body at the
person's own schedule. A candidate that does not read the schedule (Loop Adaptive) is then judged by a body built from
the very settings it ignores. A wrong or strongly shaped schedule (rloop: 72 overnight, 51 from 12:00) sets how much
each unit of timing difference costs.

**Measured (rloop, 21 days, adaptive LESSONS 22).** Loop Adaptive against the deployed setup ×1.0:

| Body ISF | ΔTIR | Δt<70 |
|---|---|---|
| scheduled × m | −14.1 | +7.2 |
| flat 55 × m | −12.5 | +6.5 |
| flat 55, no m | −10.3 | +5.8 |

The deployed setup itself is unchanged (66.4–66.5 TIR), as the difference form requires. Evidence:
`runs/2026-11-17-adaptive-unann/pisf`.

**Proposal for the default.** Body ISF = the ISF yardstick (`analysis/dist_views/ice/isf_yardstick.py`): its yardstick
tier where the person has the quiet hours, else the start rule K / TDD^b (1266.8 / TDD^0.902) from a TDD measured before
the scored window. The engine only needs the existing flat `--patient-isf` (or a per-person value written beside the
export, like `replay_config.json`). The open choice is whether m(t) stays on top.

**Asks.**
- simulator: the engine/CLI default, and the identity check (`docs/agents/verification.md`) on the new default. It
  holds by construction for field-equal doses.
- frontier: the `dr` harness flag, and which ledger results need re-scoring. Every replay result in the ledger used the
  scheduled body.

adaptive is running its own tier-A subset both ways (job 346, `runs/2026-11-17-adaptive-replay-pisf`) to show how far
the numbers move.
