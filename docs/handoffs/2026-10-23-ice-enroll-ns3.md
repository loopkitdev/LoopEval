# Request: add ns3 to the generator so it can score a settings change for her

From **simulator** to **ice**. At Pete's request. Evidence: `runs/2026-10-22-ns3-settings-replay/` (fixed-ICE replay
sweep and time-of-day arms), `runs/2026-10-21-ns3-settings-opt/` (additive twin sweep),
`runs/2026-10-21-tool-change/report.txt` (three-tool comparison).

## Why

On real settings edits and strategy switches, the generator was the best of the three tools at predicting change
(2026-10-21 tool comparison). Pete wants its answer for one concrete change: ns3's ISF ×0.8 from 12:00 to 24:00 local.
Today's estimate comes from fixed-ICE replay, plus the additive twin as a second check. Both tools agree on the
direction of TIR. Replay's Δt<54 is the axis the comparison found to be about 10× too large.

## What blocks it

`plant_v3` only runs people the checkpoint was trained on. It reads `ck["people"].index(alias)`, plus `constants[alias]`
and the per-person calibrations, and ns3 is not in the SKa checkpoint's pool. `DRAW_PERSON` would run her controller on a
drawn body, which says no more about her than the additive twin already did.

## What already exists

`~/.loop-eval/ice_ns3` is an ICE root in your layout, built by additive on 2026-10-21 for their template. It covers
about four months of her Nightscout history: `full/ns3`, `steps`, `meals`, `persons.csv`, `bolus_decisions`,
`loop_iob`. It was built from your extraction code, but please check its version before relying on it. Her deployed
config is in `PRIVATE.md`:
- Loop main, class-1 emulation (`--no-mid-absorption-isf --no-gradual-transitions-gate --legacy-rc-decay`);
- standard RC (never IRC);
- `rapidActingAdult`, autobolus, app factor 0.4;
- overrides on.

## The ask

1. Decide how to enrol her: fit a profile and per-person calibrations against a frozen SKa, or include her in a
   retrain. Keep it local, on gamepc or this Mac.
2. Check her held-out weeks against your acceptance levels, the same as for any trained person. She would be the first
   Nightscout donor, not BDDP, so any pipeline difference shows up here first.
3. If she passes, simulator runs the change. Plan: own settings vs ISF ×0.8 for 12–24 local, each across her last 90
   days, several seeds, with the deployed flags above. It is scored like the replay arms so the two can be compared
   directly.

Reply as a new file here, with the checkpoint path, or with why enrolment isn't sound.
