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

## Update: bigger stress runs (LESSONS 86)

168 people at moderate event size, plus mild and severe at 56; * = interval excludes zero.
- **C31:** illness TIR +1.36*; with a severe missed bolus TIR +1.63* and >250 −1.03*; a small lows cost when the
  unbolused meal is small (t<54 +0.20*).
- **aIRC:** exercise t<54 −0.16* and t<70 −0.43*; severe missed bolus >250 +1.12*.
- **C30:** exercise t<70 −0.29*.
- **Deep false CGM low:** C30 −1.38* and aIRC −1.25* TIR. The pull-back mechanisms act on the false reading. Worth a
  sensor-robustness guard in the ledger.

## Update: new simulator defaults on main (7e4f0b7), and run hygiene

- **Defaults changed:**
  - per-person gastric emptying (LESSONS 88);
  - meal gaps from Camerlingo's GEV (LESSONS 96);
  - per-person entered absorption time (LESSONS 102; needs the `abs_*` template columns, otherwise 3 h as before).
  Candidate deltas from lessons 83–86 were measured on the earlier defaults. Re-check before carrying them over.
- **Those earlier runs are internally consistent.** An early and a late person per family (c98, arm_*, big_*, lvl*)
  reproduce exactly (max |Δbg| 0) on frozen snapshots of the code at the commits they ran on.
- **Run from a frozen copy.** Python imports per worker process, so code synced into a shared tree mid-run changes
  later people in the same cohort. Use `git archive <commit> analysis/loopeval_analysis` into `~/frozen/<commit>`
  and launch from there.
- **Validation reference.** Donor stretches with no dose record now count as unknown insulin, not zero (LESSONS 95).

## Update 2026-10-17: per-person bolus lead and CGM gaps are defaults

- **Bolus timing.** Each person boluses at their donor's own median bolus lead (bolus time relative to meal onset,
  less the labeler's 2-min bias). It varies from meal to meal with a normal SD of 23 min. This replaces the four
  fixed timing windows (LESSONS 106). `--disable lead_own` restores the windows.
- **CGM gaps.** Short and long gap rates are the donor's own (LESSONS 107). This needs the `gap_short` / `gap_long`
  template columns from `templates.add_gap_rates`; without them the family rate is used as before.
  `--disable gap_own` turns it off.
  - On gamepc the columns are in `templates_pilot_gap.csv` (also copied to `templates_pilot_abs.csv`).
    `templates_pilot.csv` there is untouched.
- **`wear` counts distinct 5-min slots.** The donor table `real_pilot.csv` was rebuilt with it; the previous one is
  `real_pilot_dupwear.csv`.
- **Cohort result.** 30 of 51 statistics matched (c114), against 27 before. Candidate deltas measured on earlier
  defaults need re-checking.

## Update 2026-10-17 (later): body insulin action from the clamp, not Loop's curve

- The body's insulin-action rate p2 is now 0.025, from the lispro clamp fit (LESSONS 9, 114). It was 0.05, fitted to
  Loop's adult curve. The body follows evidence about patients; Loop's model is what LoopEval tests, so it is never
  the reference (Pete). About 10% of a bolus's effect lands in the first hour, against Loop's 22%.
  - Effect: Loop sees glucose climb faster than it forecast after boluses, as the real field does.
  - Meals now rise more like donors', and lows stay at donor level (c124: t54 0.17, donors 0.215).
- `--set ins_p2=0.05` restores the old timing for comparison. Candidate deltas measured before this change need
  re-checking, especially for anything that acts on the forecast's insulin tail or on meal-time dosing.

## Update 2026-10-17 (evening): per-meal absorption spread and a slow late phase are defaults

- Each meal's fast share varies (Beta SD 0.25 around 0.2), and 15% of each meal empties in a slow late phase. Pete
  chose this (LESSONS 120); the cohort match went from 27 to 31 of 51, and glucose skew, step skew and TIR now pass.
- `--set meal_fast_sd=0.0,meal_slow=0.0` restores the previous meal model. Baselines from before this need re-running.

## Update 2026-10-17 (night): bodies need a little less than their basal schedule

- The true basal share prior is centred at 0.42 of TDD (was 0.5; schedules sit at 0.45). Pete chose this
  (LESSONS 125). Lows now match the donors (t54 0.23 vs 0.215; lows/day 1.08 vs 1.08), and so does night-to-night
  overnight insulin variation. Day/night moves 1.59 → 1.72. Glucose CV now reads high (37.4 vs 34.8).
- `--set basal_share=0.5` restores the previous centre. This shifts every candidate's low-side numbers, so re-run
  baselines.
