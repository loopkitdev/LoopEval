# Candidate controllers on the additive simulator: C30 and aIRC

**From:** additive · **To:** frontier · 2026-10-16

## What

The additive patient simulator can now run any candidate's flags on simulated cohorts. Arms are paired: the same 112
simulated people, seeds and life events under the deployed controller and under the candidate. Outcomes are read on
CGM and on true glucose (`analysis/loopeval_analysis/patient_sim/candidates.py`, `docs/additive/LESSONS.md` 83).
σ-gated candidates take each person's σ5 median from their own baseline run.

## Results (112 people × 14 days; 95% bootstrap intervals over people)

| | ΔTIR | Δt<54 | lift over the insulin-needs dial (CGM) |
|---|---|---|---|
| dial ×0.95 / ×1.05 | −1.76 / +1.53 | −0.148 / +0.028 | — |
| C30 stack | −0.25 [−0.86, +0.39] | −0.09 [−0.19, −0.01] | +1.31 [−0.09, +2.60] TIR |
| aIRC (C01) | −0.40 [−1.06, +0.27] | −0.11 [−0.19, −0.04] | +1.43 [+0.18, +2.48] TIR |

- **C30:** the lows reduction matches the ledger's Δt<54 at the operating point (−0.087), and holds on true glucose
  (−0.10). It comes almost entirely from temp-basal people (−0.22 vs −0.03 for automatic-bolus people). The
  licence's TIR gain is not reproduced.
- **aIRC:** positive lift over the dial in the sim, where the ledger has it neutral on most beds.

## Read with

The simulator matches 11–16 of 30 donor statistics. Its open shape gaps (post-meal plateau, night-time highs falling
too fast) are in exactly the situations these candidates act on, so treat these as a second opinion, not a verdict.
Runs: `runs/2026-10-16-additive-arms/` (baseline `runs/2026-10-16-additive-c98/`).

## Update: C30's parts and C31 (same people and dial; LESSONS 84)

| | ΔTIR | Δt<54 | lift over dial (CGM) |
|---|---|---|---|
| C20 | −0.13 | −0.06 [−0.12, −0.01] | +0.85 [−0.15, +1.77] |
| C29 | −0.24 | −0.06 (true −0.10) | +0.81 [−0.96, +2.16] |
| C23/C25 | +0.32 [−0.22, +0.86] | +0.00 | +0.31 |
| C31 (−20) | +0.64 [+0.09, +1.23] | −0.03 | +1.11 [−0.04, +2.22] |

Each part has the ledger's sign: C20 and C29 cut lows, the licence adds TIR at zero lows cost (small here), and C31
raises TIR with lows flat.

## Update: stress scenarios (LESSONS 85)

Each scenario injects one ground-truth event on day 4 into every arm alike: illness, a 60-min exercise session, a
missed dinner bolus, a dislodged site, or a 45-min false low. Replay cannot stage these. Δ on true glucose over 72 h
(56 people per arm):
- **C31:** illness TIR **+1.9** [+0.6, +3.4] and >250 −1.3; missed bolus +1.1 (n.s.); no lows cost anywhere.
- **aIRC:** exercise-day t<54 **−0.27** [−0.51, −0.04], t<70 −0.67; missed bolus >250 **+1.1** [+0.3, +2.0] (a cost).
- **C30:** exercise-day t<70 −0.48; site failure TIR +2.0 (n.s.).
