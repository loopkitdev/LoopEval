<!-- Role overlay. Loaded via ROLE.md; see AGENTS.md → Roles. -->

# Role: trio

Evaluate **Trio's** dosing (oref: SMB, UAM, autosens, dynamic ISF) under LoopEval, and compare it
with Loop **on the same people**. The question is the shared one: does it raise TIR without
raising t<54, and how is that trade different from Loop's?

Read with **AGENTS.md** (shared) and **docs/agents/verification.md**. A Trio number is only worth
something if the oref engine reproduces Trio's own decisions on Trio data first (fidelity before
frontier).

## What this role owns, and what it doesn't

- **Owns:** oref/Trio fidelity on Trio donors, the oref configuration that stands for "a Trio
  user", the oref aggressiveness dial, and the Loop-vs-Trio comparison and its write-ups.
- **Doesn't own:** the engine and `OpenAPSAdapter` as shared code. Fixes land on `main` under the
  publishing rules in AGENTS.md, with the identity check re-run, and simulator is told about them.
  The candidate ledger belongs to frontier. **TIDEPOOL-6** (Loop-vs-oref frontier) is that
  ledger's entry for this work. Coordinate on it rather than run a parallel frontier.

## Where things are

| Where | What |
|---|---|
| `OpenAPSSwift/` (submodule) | oref port extracted from Trio's `feat/dev-oref-swift` (June 2026), JSON-in/JSON-out |
| `Sources/EvalCore/Engine/OpenAPSAdapter.swift` | Sim state → oref inputs (profile, IOB, meal, autosens, TDD, temp targets, smoothing) |
| `Sources/EvalCore/Engine/LoopMimicViaOpenAPSAdapter.swift` | Loop-like config run through the oref path (cross-engine control) |
| `Sources/LoopEvalCLI/SimulateFlags.swift` | `--candidate-openaps`, `--candidate-oaps-*`, `--oaps-preset-target`, `--candidate-oaps-prefs-json` |
| `scripts/oref-oracle/` | Golden master: Trio's real oref JS on raw NS data, to diff the Swift port |
| `docs/candidates/README.md` § C17 | Ledger state: fidelity only, no frontier number |
| `PRIVATE.md` | `orefuser`, `orefuser2` config (Trio NS sites); prefs under `~/.loop-eval/<alias>/` |

## Data

- **Trio Nightscout sites:** `orefuser` (validation still open) and `orefuser2` (validated
  2026-07-03 on the pre-counter-reg-fix sim, re-check owed). Trio uploads `openaps` devicestatus
  per cycle (suggested/enacted, IOB, COB, forecasts), which serves as Trio's recorded decision
  stream, in the role `dosingDecision` plays for Loop.
- **Tidepool pilot donors with Trio records:** app switchers **i030, i083, i130** (Loop and
  Trio on separate days, the same person under both algorithms) and same-day co-uploaders
  **i156, i105, i053, i042** (second-app doses, see `docs/handoffs/2026-10-11-ice-second-app-doses.md`;
  not usable as Trio periods). Trio periods carry no Loop dosing decisions. Whether they carry
  Trio's own decisions or settings is unchecked.

## Rules for this role

- **Faithful config per Trio donor**, as for Loop donors: insulin curve/peak, DIA, dynISF formula
  and adjustment factor (and its dated schedule), autosens limits, SMB/UAM enables and limits,
  temp-target presets, smoothing, profile timezone. Prefs go verbatim through
  `--candidate-oaps-prefs-json`, and the site's flags go in `replay_config.json`.
- **Same people, same substrate.** A Loop-vs-Trio comparison runs both engines as candidates on
  the same donor, window, ICE substrate and behavior mode, each on its own aggressiveness dial
  (Loop: insulin-needs; oref: profile percentage). Compare frontiers, never one point against
  another.
- **State the behavior mode.** Manual boluses are a confound across engines: oref's SMB/UAM
  covers what Loop leaves to the user. Report the hands-off regime and the user-scaled regime
  separately.
- **Safety axis first.** Report IOB-at-crossing-54 next to t<54. C17's summed IOB at the 54
  crossing was 8.6 for Loop vs 41.7 for oref on user1.
- **Host bias.** Loop donors' ICE was shaped by Loop's dosing, and Trio donors' by oref's. Check
  each engine on both kinds of host before reading a winner.

## Status (2026-10-24)

- **Loop vs oref, 40-donor v32 pilot** (39 scored; Loop-era ICE, manual boluses verbatim, oref = Trio
  1.0.2 defaults + SMB-always + UAM + dynISF log AF 0.8, dial = insulin-needs ×0.7…1.2). oref is
  dominated: no dial point reaches Loop's t<54 (×0.7: ΔTIR −15.9, Δt54 +0.25; ×1.0: −1.8 / +1.28).
  At Loop's t<70, oref's TIR is −14.4 [−17.6, −6.6]. Worst donor +6.6 t<54 at ×0.7. Summed IOB at
  the 54 crossing 289 U Loop vs 828 U oref ×1.0. oref's ΔTIR tracks scheduled basal (Spearman 0.67):
  SMB and temp caps scale with basal, so low-basal donors under-dose highs. SMB cap 30→120 min
  removes that pattern but lands on oref's own dial (×0.9 cap-120 ≈ ×1.2 default). Runs:
  `runs/2026-10-24-trio-pilot/` (`score.py`).
- **Trio → Loop candidates measured, none helps:** oref dynISF on Loop rides the dial (lift −0.05
  [−0.92, +0.58] at ×1.0, −2.57 at ×1.05); autosens and C14 were negative on bddp11; C38 (deviation
  autosens analog) was already NEUTRAL in the ledger.
- **Field, Tidepool 2026-05-15→10-13** (≥30 closed-loop days, single-app days): Trio users median
  TIR 81.5 vs Loop 74.8, t<54 equal (0.34 vs 0.36). Within 28 Loop→Trio switchers the gain is +1.45
  TIR [+0.22, +2.63], t<54 −0.05 [−0.18, +0.06]: most of the group gap is who chooses Trio, and the
  remainder is uncontrolled (season, settings changes at the switch). Runs:
  `runs/2026-10-24-trio-vs-loop-field/`.

## Status (2026-10-23)

- Pete approved the plan. First step under way: re-validate orefuser2 on the current simulator.
- **Trio overrides were not modelled.** Trio uploads each override as a Nightscout `Exercise`
  event carrying only the preset name and duration. The adapter read them as temp targets and
  dropped every preset whose target wasn't in the notes, so "No smbs" never turned SMB off. Fixed
  behind `--candidate-oaps-override-presets` (name → target / percentage / smbIsOff, inferred from
  devicestatus inside each preset's windows). Without the flag, behavior is byte-identical.
- **Tidepool Trio data** (census 2026-10-23): 613 users with `org.nightscout.Trio` records, 136
  with ≥90 days of basal + bolus + pumpSettings, uploads from 2026-03. Trio uploads doses (SMB =
  `automated` bolus), basal, pumpSettings and its version. It uploads no dosingDecision and no
  oref preferences (`controllerSettings` is an empty payload).
