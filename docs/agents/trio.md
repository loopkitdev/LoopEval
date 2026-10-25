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
  1.0.2 defaults + SMB-always + UAM + dynISF log AF 0.8; both on the insulin-needs dial, oref ×0.7…1.2,
  Loop ×0.95…1.5). **At equal t<54, oref's TIR is lower** (Loop interpolated along its dial at
  oref's lows): ×0.7 −17.8 [−22.5, −12.5] at t<54 0.83; ×0.9 −7.1 [−10.6, −4.3] at 1.38;
  ×1.0 −4.1 [−6.8, −1.9] at 1.87; ×1.2 −2.1 [−4.1, −0.4] at 2.96. The gap closes only where both
  run t<54 ≥ 3%, past Loop's TIR peak (Loop ×1.2 = 73.4 / 2.67). oref never reaches Loop's ×1.0
  lows (0.59). Worst donor i167 +6.6 t<54 at ×0.7. Summed IOB at the 54 crossing 289 U Loop vs
  828 U oref ×1.0. oref's ΔTIR tracks scheduled basal (Spearman 0.67): SMB and temp caps scale
  with basal, so low-basal donors under-dose highs. SMB cap 30→120 min removes that pattern and
  moves oref along a slightly better curve (×0.9 −2.1, ×1.0 −0.9 [−2.7, +0.7]), but only at t<54
  3–3.5%. Runs: `runs/2026-10-24-trio-pilot/` (`score.py`; Loop dial arms `lneedNNN`).
- **Host bias decides the winner.** On the two Trio hosts (Trio-era ICE, oref at the site's own
  prefs and presets, Loop with the Trio overrides as Loop overrides), oref leads at equal t<54 by
  as much as Loop leads on Loop hosts, the other way round: oref ×1.0 +18.2 TIR on orefuser
  (1 week, Trio 1.0.2 field) and +15.6 on orefuser2 (May, field 0.7.0); +7 to +10 at ×1.1. Each
  engine wins on data its own dosing shaped, so replay on either kind of host gives no ranking. Runs:
  `runs/2026-10-24-trio102-orefuser/host2x2/`, `runs/2026-10-23-trio-orefuser2/host2x2/`.
- **Host-neutral: the additive simulator** (112 simulated people × 14 d, seed0 1000, patient components
  night_pro / uls / ex_sat 0.1; Loop with each person's own RC and GBAF, oref with the pilot prefs; both on
  the insulin-needs dial, Loop ×0.7…1.2, oref ×0.8…1.6). **At equal lows oref's TIR is about 3 lower**
  across the whole range where the dials overlap: at equal t<54, −2.3 to −4.1 on CGM (×1.2 −2.8
  [−5.0, −1.0], ×1.5 −4.0 [−5.6, −1.8]) and −1.6 to −4.3 on true glucose (CIs touch 0 at ×1.0–1.4); at equal
  t<70, −3.0 to −4.7 on CGM, every CI below 0. At the same oref setting oref delivers about 10 U/day less;
  it needs ×1.4 to reach Loop ×1.0's lows (0.43 vs 0.41), and there it is −3.0 TIR (median −2.5; 68% of people
  worse). The loss grows with insulin need (Loop-TDD terciles −1.5 / −3.6 / −4.1). Worst person −36.9 TIR:
  78 U/day under Loop, 52 under oref, runs high. Worst true t<54 +1.7. Only at the gentle end (oref ×1.0 vs
  Loop ×0.7, t<54 0.23 vs 0.21) do they tie (+0.06). These people aren't shaped by either engine's dosing,
  so this direction is not host bias, within the simulator's own known limits. **A second draw of 112
  people (seed0 5000) replicates it, larger:** at equal t<54 ×1.2 −4.6 [−7.5, −2.5], ×1.4 −4.7 [−7.0, −1.6],
  ×1.6 −4.1 [−6.1, −1.8]; every CI below 0 on CGM, true glucose and t<70. Worst person −38.6 TIR, worst true
  t<54 +4.3 (×1.6). Runs: `runs/2026-10-25-trio-additive/` (`score.py`; `score_cand.py`, `SUF=_5k` for the
  second draw).
- **Trio mechanisms on Loop, host-neutral (additive sim, ×1.0 against Loop's dial):** none survives a second
  draw. Dynamic ISF ramp (×0.65 at 200 mg/dL) +1.87 [+0.31, +3.58] at equal t<54 on seed 1000, −0.09
  [−1.26, +0.95] on seed 5000; autosens (gain 0.004, 6 h) +1.51 [−0.16, +3.10] then −0.01 [−1.51, +1.56];
  UAM projection 45 min +0.42 and slow RC 6 h +0.38, both CIs across 0, first draw only.
- **Field switchers** (below) are the other host-neutral evidence: +1.73 TIR for Trio, t<54 flat, settings
  changes at the switch mixed in.
- **Trio → Loop candidates on donor replay, none helps:** oref dynISF on Loop rides the dial (lift −0.05
  [−0.92, +0.58] at ×1.0, −2.57 at ×1.05); autosens and C14 were negative on bddp11; C38 (deviation
  autosens analog) was already NEUTRAL in the ledger.
- **Field, Tidepool 2026-05-15→10-13** (≥30 closed-loop days, single-app days): Trio users median
  TIR 81.5 vs Loop 74.8, t<54 equal (0.34 vs 0.36). Within 28 Loop→Trio switchers the gain is +1.45
  TIR [+0.22, +2.63], t<54 −0.05 [−0.18, +0.06]: most of the group gap is who chooses Trio, and the
  remainder, net of the calendar change Loop-only users show over the same dates
  (difference-in-differences), is **+1.73 TIR [+0.50, +2.94]** with t<54 −0.03 [−0.15, +0.09];
  +2.31 [+0.52, +3.89] after a 14-day washout (25 switchers). Worst switcher −6.2 TIR, +0.78 t<54.
  Switchers' daily insulin barely changed (Trio/Loop median ratio 1.02; basal share 0.34 → 0.28,
  automatic-bolus share 0.34 → 0.36), and the gain doesn't track it (Spearman 0.16). Among the 14
  whose insulin stayed within ±10%: +1.0 [−0.7, +2.7]. Not controlled: selection into switching.
  Runs (`did.py`, `tdd.py`):
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
