# The low-side target is now time below 70; t<54 is a guard

From **ice** to **frontier** (and every role). Pete's decision, 2026-10-26, now in `AGENTS.md` → *Optimization
target* and *Metrics*. Evidence: ice LESSONS 147; runs in `runs/2026-10-13-ice-change/` (`score_v32of*`,
`score_v32oc*`).

## What changed

- Candidates are judged on **TIR ↑ and t<70 ↓**. A win on one that costs the other is not a win.
- **t<54 is reported beside every result** and acts as a guard: an unusually large rise in it disqualifies a
  candidate, but it no longer ranks candidates.

## Why

Measured on real settings edits (pilot change test, 62 edits), predicting the change in t<54 does not beat predicting
no change for any tool: zero-change |err| 0.30, generator 0.31–0.37, replay 0.67. Its r swings between two trainings of
the same generator (0.20 / 0.37). Change in t<70 is predictable: zero-change |err| 1.41, generator 1.20–1.33, model r
0.48–0.62 on every training, replay 0.49.

## What it asks of frontier

- Rank and judge candidates on TIR and t<70; keep t<54 in every table as the guard.
- Set what counts as an "unusually large" t<54 rise for a verdict. Ice uses more than the spread between two trainings
  for model changes; the C-ledger's +0.05 line is the obvious candidate-level version.
- The plot convention (x TIR, y t<54, `plotting.tir_t54_axes`) is unchanged. Whether the y-axis moves to t<70 is
  yours and simulator's to decide.
