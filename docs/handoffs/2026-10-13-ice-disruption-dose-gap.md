# Handoff to simulator: a long disruption delivers almost nothing where the pump ran its schedule

**From:** ice · **Date:** 2026-10-13 · **Evidence:** `runs/2026-10-13-ice-v3m/` (rollouts of v3m4s0 and v3v28s0m on harness
b70ba36, training window)

## What happens

i061 has one disruption from 2026-08-16 21:25 to 08-30 20:25 (`disruptions.csv`, `tidepool/merged`, 20,100 min). Over
08-17 → 08-30:

| Source | Insulin |
|---|---|
| `doses.json` (the engine's dose input) | 2 records, 1.4 U basal |
| ICE `steps` (extract.py, gapcheck) | 253 U basal: schedule fill, because Loop's recorded IOB shows the pump ran |
| CGM | present at every step |

Since b70ba36 a disruption delivers what the pump recorded, so the closed loop gets about 0.1 U/day for 13 days. A replay
of measured ICE follows the field CGM there, so it does not show. A generated person does not: glucose ran to a
mean of 3,400 mg/dL (v3k) and 9,600 (v3m4) for the rest of the window, and i056 (several 1-4 day disruptions) does the
same at a smaller scale. Outcomes leave disrupted time out, but the runs feed every closed-loop calibration.

## What ice did

The external plant (`plant_v3`) now follows the field glucose through disrupted steps (`--no-follow-disrupted` turns it
off), as the replay plant does. That removes the contamination on ice's side; it does not make the dose input right.

## What simulator might do

Decide which record is right for these stretches and make the two agree: either the dose input carries the same schedule
fill gapcheck infers (IOB-confirmed delivery), or extract.py should stop counting it. A re-export is already owed for the
pump-clock fix (v31, 22 donors), so a fix could ride along.

## How widespread (ice_v30, all pilot donors)

187 disruptions longer than 24 h on 66 donors. In 93 of them, on 41 donors, the steps carry more than 10 U of basal that
`doses.json` does not: 32,773 h in all. The longest cover most of a donor's record (i110: 2,532 h, 2,561 U in steps, 0 in
the dose input; i160, i174, i191 over 2,200 h each), with CGM present throughout. Among the 24 held-out rollout donors,
10 miss more than 20 U over their last 56 days; i061 (262 U, 26% of the time) and i056 (224 U, 38%) are the large ones.
