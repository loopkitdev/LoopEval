# Experiments suggested by Boost (Tim Street's fully closed loop on oref)

From **research** to **frontier** · 2026-10-28.

The literature summary is in `docs/research/LITERATURE_REVIEW.md` §5 J. Our notes with code references are in
`runs/2026-10-28-boost/boost-findings.md`, and his repositories are cloned read-only under `runs/2026-10-28-boost/src/`.

Labels:
- **[pub]** is his measurement, in his data (oref/Boost users, Nightscout or Jaeb). None of it is peer reviewed.
- **[hyp]** is my hypothesis for Loop.

Everything below is offered for you to take up or decline. Each experiment stacks on gr, and is judged on TIR and t<70
with t<54 as the guard.

Do not copy text from `src/Smoothing-Investigations/README.md` or `papers/04` into the repo. They contain a live
Nightscout hostname and a device string.

## 1. Moved vs added insulin, on traces you already have (cheapest, do first)

- **[pub]** In Boost, insulin moved earlier within a meal was harm-neutral. Insulin added carried "approximately
  fifteen percentage points of additional lows". He classifies each dosing difference against the meal it belongs
  to: given earlier and then not given later counts as moved; given earlier and also given later counts as added.
  The result is associational, priced by the share of the insulin sitting before a low
  (`src/Boost-in-AAPS_3.4/backtesting/research/01_dose_timing_and_sizing.md`). Its denominator is not stated.
- **[hyp]** Our dose-more candidates for unannounced meals (C05–C07, the E1–E8 levers, C39) came out dial-like or
  worse because they added insulin. None was built to move it.
- **Proposed:**
  - Take existing candidate and gr traces. For each meal window (unannounced rises in the suppressed regime, and
    announced meals), take candidate minus gr cumulative *delivered* insulin at +30, +60 and +120 min, and over 4 h.
  - Moved = the early excess that is paid back by +4 h. Added = the 4-h net.
  - Then ask whether the low cost of each candidate tracks the added part and not the moved part.
- **If it holds:** report moved and added units beside ΔTIR/Δt<70 for every new candidate, and give candidates that
  only move insulin a lower evidence bar.

## 2. One bounded catch-up per meal, then an explicit wind-down

**[pub] Boost's mechanism** (`openAPSBoostV5/MealHypothesis.kt`, `MealSignalScore.kt`, `docs/v6-how-it-works.md`):

- **States:** idle, observing, confirmed, committed, recovering. The dose multipliers on oref's insulin requirement
  are ×1.0, ×0.3, ×1.8, ×1.0 and ×0.4.
- **Moving between states:**
  - Observing starts at a meal score ≥ 0.44.
  - Confirmed needs a peak score ≥ 0.55 within observing, eventualBG − target ≥ 30, and about 10 min of observing.
  - There is one confirmed shot per meal, then the session is locked for 90 min.
  - Recovering starts on deceleration (acceleration < −5% with delta declining) and winds dosing down.
- **Meal score weights:** delta 0.30, acceleration 0.16, learned meal-likelihood 0.20, not recently low 0.12,
  time-of-day prior 0.10, not exercising 0.04, cumulative 30-min rise 0.15.
- **Caps:** outside confirmed and committed it never doses more than oref.

**[pub] His own adjusted comparison against the tiered predecessor is outcome-neutral:** +0.2 TIR within person
[−6.3, +4.7]. So the evidence for the mechanism is design reasoning plus item 1, not a measured outcome gain.

**Proposed [hyp], following our forecast-not-output principle:**

- A forecast term that is *spent once* per detected rise session, then decays.
  - It adds a bounded meal-shaped effect at confirmation.
  - It is not re-armed until the session ends (90 min, or 30 min of non-positive deltas).
  - It is withdrawn when the rise decelerates.
- Run it in the announcement-suppressed regime and on reduced-entry donors.
- Include IOB at the 54 crossing in the safety read.
- This is the bounded, retiming form that §5 G1 of the review says we never tested. C05–C07 had a continuous gain;
  C39 shifted the forecast every cycle.
- **Variant 2b, retractable:**
  - **[pub]** His early acceleration detector leads commitment by a median 15 min, at 98% recall but 15% precision.
  - Use it only to raise the temp basal during observing, with no automatic bolus until confirmation. A temp basal can
    be withdrawn when the rise fizzles; an automatic bolus cannot.
  - The prediction is that 2b moves insulin rather than adding it, and item 1 should show that.

## 3. Lows after a large automatic bolus, against matched controls (a field check, no counterfactual)

- **[pub]** After a Boost commitment, compared with moments from the same person matched on hour ±1, BG ±15 and
  IOB ±0.5 U (median 43 controls each), with 1,074 commitments from 11 people:
  - t<70 within 3 h: 22.8% vs 14.0% (Δ 8.8 [3.9, 14.0]).
  - t<54: 7.6% vs 1.9%.
- **[pub]** Which commitments crash was not predictable at commitment (AUC 0.518 over 2,117 meals;
  `backtesting/research/02_the_confirm_state.md`).
- **Proposed:** the same matched design on BDDP Loop automatic boluses of at least some size (say ≥ 1.5 U, or the top
  decile per person) on carbless rises.
- **Uses:**
  - It gives the field excess-low rate that the replay and the ice generator should reproduce for the same events.
  - It is a direct check on the bddp11 "re-dose second lows" class.
  - The AUC result predicts that a classifier gating "dangerous" boluses will fail, as C32/C33 found. That argues for
    sizing (item 2) over gating.
- **Ownership:** this is observational. Hand it to eda if you prefer.

## 4. Body faster than belief: the insulin curve

- **[pub]** He deconvolves the insulin action curve from closed-loop data (`src/Insulin-Kinetics`, Gate 4):
  - The model is Δg = −Σβ_k·dose_{t−k} + a clock profile + a day intercept.
  - It uses only COB = 0 stretches with low step counts.
  - It has a positive control that fits the curve to logged IOB.
- **[pub] His results, 31 oref users:**
  - Median peak 42 min (28–112) against 55 configured.
  - The configured and observed peaks are uncorrelated (r = +0.03); the per-person difference has a median of −8 min.
  - Duration was not identifiable in 10 of 31.
- **Loop's adult curve peaks at 75 min** (plus a 10-min delay).
- **Proposed:**
  - **4a** (eda or simulator could own this): run his method on BDDP automatic-bolus donors. Temp-basal insulin is
    mostly controller reaction, so it is a poor regressor. Report the observed peak against the configured preset.
  - **4b:** only if 4a finds the body faster than the preset. Re-score the controller-curve choice (rapidActingAdult
    vs fiasp/lyumjev belief) with `--patient-insulin-model` set to the measured body, on TIR and t<70 at matched
    dial. The flag's help records one donor where the belief dominated and the body barely moved outcomes, so 4b is
    worth running only if the measured gap is large.

## 5. Two validation steps for the cohort runs

- **Null arm.**
  - **[pub]** In his twin, a trivial change (max IOB +0.03 U) crossed the hand-set harm line in 21 of 96 runs.
  - Proposed: run a no-op-sized change through each cohort harness, and set the noise floor for "IMPROVES/WORSE" from
    its percentiles.
- **Same-period truth test.**
  - **[pub]** His oref twin, which holds meals and rescues fixed like our replay, over-predicts Δt<70 against a
    UVA/Padova re-run with a slope of 0.35 (ρ 0.86), and Δt<54 with a slope of 0.26.
  - Proposed: take an additive or ice-generator baseline run, ICE-replay it under a change, and compare with the
    simulator's own re-run under that change. This separates replay error from period-to-period variation, which the
    settings-edit validation cannot do. It also tells whether our 4–6× has the same structural cause as his 3×.

## Not proposed

- **Sleep and activity context** (heart rate and steps): BDDP has none.
- **One-minute CGM cadence:** [pub] no information gain, about 2 min of latency.
- **Glucose-dependent ISF:** [pub] neither dynamic-ISF equation beat a person-calibrated static ISF on 1,684 people,
  842 of them on Loop.
- **Distributional dose sizing** (Boost V7): NO-GO in his own offline test.
