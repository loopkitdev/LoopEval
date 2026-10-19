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

## Update 2026-10-17 (late): EGP-suppression rate from the meal tracer

- `p2e` is now 0.006 (was 0.010), so insulin's suppression of liver output after meals matches the depth of the
  Romeres 2025 T1D tracer (LESSONS 131).
  - The cohort is 35 of 51 matched; long-range Hurst and overnight insulin variability now pass.
  - Lows read a little high (t70 2.45 vs 1.67).
- `--set ins_p2e=0.010` restores the previous rate.

## Update 2026-10-18: menstrual cycle on by default

- The menstrual cycle is now on by default (B5) for menstruating people, 63% of whom respond. Insulin sensitivity is
  lowest from the late luteal days to menses onset, the shape BDDP's G7 cycle logs show (LESSONS 136). Cohort
  statistics are unchanged within noise. `--disable menstrual` turns it off.

## Update 2026-10-18: glucocorticoid courses (B14), and a steroid scenario

- Oral glucocorticoid courses are on at the population rate (0.09 per person-year), so a 14-day cohort sees almost
  none; default statistics are unchanged. `--disable steroid` turns them off.
- `--enable steroid_course` gives every person one 4–7 day course from day 3: insulin sensitivity falls in the
  afternoon and evening after a morning dose (day 1 average ~+29% insulin need). Under stock Loop the first day runs
  +21 mg/dL (+48 from 14 to 22 h) with 12% more insulin (LESSONS 140). It is a test bed for how fast a candidate
  adapts to a sudden, days-long rise in insulin need.

## Update 2026-10-18: new base — total-drop ISF and a full intake budget

- Each body's ISF is now the TOTAL glucose drop per unit (Loop's own meaning of ISF), and the daily insulin budget pays
  for everything the person eats, unlogged grazing and hypo treatment included (LESSONS 143). The previous base's
  insulin acted ~2× its stated ISF and over-covered every meal.
- What changes for candidate testing: entered meals now plateau like the donors' (no dip below the start at 2–4 h),
  CV and TDD match, but the level runs ~+15 mg/dL and time below 70 is ~0.5% (donors 1.7%). Hypo-prevention
  candidates have less to prevent on this base; rank them on paired deltas, and re-run any earlier result whose
  verdict depended on post-meal lows.
- `--disable isf_total,budget_all` reproduces the previous base exactly.
- Also from 2026-10-18: fat-induced insulin resistance is relative to each person's usual diet (LESSONS 151), so the
  base no longer drifts upward through the day: mean ~159 (donors 151), TDD at the donors'.
- Also from 2026-10-18: insulin absorbs more slowly while the person is upright (posture, A4b) and everyday movement
  comes in short bouts (C7). Lows now sit at the donors' level (t<70 1.6%, ~1 low/day), so hypo-prevention candidates
  have real lows to prevent again on this base (LESSONS 163).
- Also from 2026-10-18: insulin acts harder at high glucose (κ ≈ 0.68, Best 1981; LESSONS 165). The glucose
  distribution now sits on the donors' at every percentile (mean ~149, TIR ~73), with lows unchanged.
- Also from 2026-10-18: counter-regulation is half as strong (CRmax median 0.5, fitted to the donors' low nadirs;
  LESSONS 166), so lows reach the donors' depth (t<54 ~0.15%, P(reach 54) ~0.19).

## Update 2026-10-19: aIRC on the current simulator — the positive lift is gone

The simulator's body has changed since 10-16 (κ ≈ 1 from Best 1981, Brazeau carb-count error, data-fitted ISF, carb
sensitivity weight; `docs/additive/LESSONS.md` 300–304). Re-run on the current reference (112 people × 14 days, each
with their donor's deployed RC; `runs/c311_*` on gamepc):

| aIRC vs baseline | value [95% CI over people] |
|---|---|
| ΔTIR | −1.13 [−1.63, −0.67] |
| Δt<54 | −0.02 [−0.07, +0.02] |
| Δt<70 | −0.17 [−0.29, −0.06] |
| lift over the insulin-needs dial, CGM | −0.68 [−1.64, +0.72] |
| lift over the dial, true glucose | +0.15 [−1.28, +2.29] |

aIRC now trades TIR for fewer lows at about the dial's rate: **neutral**, in line with the ledger on most replay beds.
The 10-16 "+1.43 lift" above should not be cited.

C30 and C31 re-run the same way, their per-person flags rebuilt from each simulated person's own baseline σ5 by the
ledger's recipes (C30: band k = min(1, 6.7 / σ_p50), calm-high σ max = σ_p50; C31: target −20 with the same σ max;
`runs/c312_*`):

| vs baseline | C30 | C31 |
|---|---|---|
| ΔTIR | −0.66 [−1.09, −0.23] | −0.09 [−0.43, +0.26] |
| Δt<54 | −0.00 [−0.04, +0.04] | −0.00 [−0.03, +0.03] |
| lift over the dial, CGM | −0.57 [−1.40, +0.49] | −0.02 [−0.67, +0.91] |
| lift over the dial, true glucose | +0.01 | +0.37 |

**On the current body none of the three shows a lift outside its interval** (10-16: C30 +1.31, C31 +1.11, aIRC +1.43).
The simulator no longer supports the 10-16 positive readings for any of them.

**Read with the current limits** (role overlay, *Known limits*): the simulator's time < 54 under-reads the donors'
(0.09% vs 0.22%), real meals stay ~20 mg/dL higher at 3 h than simulated ones, and faster insulin absorption removes
lows under Loop — any candidate acting on post-meal or low-side behaviour is read here as a second opinion.

## Update 2026-10-19 (late): re-run on reference c339_gecirc — still neutral

The simulator gained circadian gastric emptying (Goo 1987), measured meal-slot composition (Vetrani 2022) and each
twin's donor dosing strategy by its share of autobolus days (`docs/additive/LESSONS.md` 331, 338–339; 38 of 51 eda
statistics). Same recipes as above (112 people × 14 days, donor-deployed RC, σ-gated flags from each person's own
baseline; `runs/c344_*` on gamepc), 95% CI over people:

| vs baseline | aIRC | C30 | C31 |
|---|---|---|---|
| ΔTIR | −0.89 [−1.41, −0.37] | −0.30 [−0.80, +0.16] | +0.12 [−0.43, +0.67] |
| Δt<54 | −0.03 [−0.08, +0.01] | −0.03 [−0.06, +0.01] | +0.00 [−0.04, +0.05] |
| Δt<70 | −0.19 [−0.33, −0.04] | −0.10 [−0.22, +0.03] | −0.02 [−0.14, +0.09] |
| lift over the dial, CGM | +0.08 [−1.43, +1.61] | +0.50 [−0.64, +1.65] | +0.01 [−1.26, +1.39] |
| lift over the dial, true glucose | −0.46 [−1.68, +1.17] | −0.31 [−1.43, +0.95] | −0.63 [−1.94, +0.78] |

No lift outside its interval for any of the three, as on c311/c312: the verdicts hold across the body changes since.

## Update 2026-10-19 (night): stress scenarios re-run on reference c362_g6s

Same five scenarios as LESSONS 85–86 (one ground-truth event on day 4, every arm alike), moderate size, 112 people × 8
days, each on their donor's deployed RC (`rc_own`); C30 / C31 flags rebuilt from each person's c362 baseline σ5
(`runs/s365_*` on gamepc). Δ vs baseline on TRUE glucose over 72 h, 95% bootstrap CI over people; * excludes zero.

| scenario | baseline TIR | C30 ΔTIR | C31 ΔTIR | aIRC ΔTIR | other |
|---|---|---|---|---|---|
| illness | 60.6 | −0.26 | +0.71 | **−1.61*** | C31 >250 **−0.88***, t70 +0.16* |
| exercise | 70.2 | **+1.47*** | **+1.37*** | +0.28 | t54 n.s. for all |
| missed bolus | 68.3 | **+1.49*** | **+1.33*** | −0.58 | C30 t70 −0.21 (n.s.) |
| site failure | 59.4 | −0.28 | +0.33 | −1.34 | aIRC t70 **−0.25*** |
| false CGM low | 67.6 | +1.01 | **+1.98*** | +0.05 | C31 >250 **−0.90*** |

Changes from the 10-16 readings (older body model): C30 and C31 now gain TIR on exercise and missed-bolus days with no
lows cost; the deep-false-low losses of C30 (−1.38*) and aIRC (−1.25*) are gone (C30 +1.01 n.s., aIRC +0.05); aIRC's
exercise-day lows benefit is gone and it costs TIR during illness. Read with the overlay's Known limits (post-meal late
phase, short-scale shape); the low side now matches the donors on every statistic (LESSONS 360–362).
