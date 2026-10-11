<!-- Role overlay. Loaded via ROLE.md; see AGENTS.md → Roles. -->

# Role: LoopEval development

Building and maintaining the evaluator itself — the simulator, the dosing adapters, the CLI
and the Python analysis package — rather than drawing conclusions with it.

Read with **AGENTS.md** (shared) and **docs/agents/verification.md**: a change to the engine
is only correct if replay fidelity and the identity checks still hold, so those are the
acceptance criteria for this role's work.

| Where | What |
|---|---|
| `docs/simulator-guide/README.md` | Deep technical guide to the simulator |
| `docs/loop-algo-classes.md` | Deployed-Loop vs LoopAlgorithm-package behaviour classes and emulation flags |
| `Sources/EvalCore/Engine/ClosedLoopSimulator.swift` | Substrate, counterfactual, closed loop, fidelity, disruption clamps, patient IOB |
| `Sources/EvalCore/Engine/DosingEngine.swift` | Pluggable controller: `LoopAdapter` / `OpenAPSAdapter` |
| `analysis/loopeval_analysis/` | Scoring, frontier, case studies, IOB, carb reconstruction |

**Non-negotiable after any engine or dose-path change:** run the identity check
(identical baseline/candidate configs must give Δdose ≈ 0 at every step, counter == sanity)
and re-verify replay against a validated dataset. See `docs/agents/verification.md`.

**Interface changes ripple into the other roles.** A renamed flag, a changed trace field or a
new default silently invalidates the frontier ledger and the analysis scripts. Land those on
`main` with a note in the commit message so the other worktrees see it on their next merge.

## Current goal (set 2026-10-10, Pete)

**Understand every divergence between a deployment-faithful replay and the field.** At identity the
replay reproduces the recording exactly, so any gap has a cause — find it, measure it, and either fix
it or name it as an accepted, explained residual. Serves GOALS.md constraint 4 (fidelity before
frontier): absolute outcomes from a replay that doesn't match its own field can't be trusted.

Working decomposition, per decision, from three streams the data already holds — the field's
**recommendation** (`decision_times.csv`), the field's **delivery** (dose history), and **our
recommendation on the field's exact inputs** (DTR):

- ours − field recommendation → controller / input fidelity
- field recommendation − field delivery → what the real system didn't do that the replay does
- whatever survives both → feedback amplification

Seeds are ranked worst-case first, never by average. Input classification and config come before any
of that: a replay fed the wrong doses or the wrong flags diverges for reasons that aren't physics.
