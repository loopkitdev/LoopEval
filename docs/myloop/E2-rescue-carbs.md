# E2 — Rescue carbs hidden from the controller (pre-registration)

Written 2026-10-25, after the identity check and before the candidate arm ran. Board: TIDEPOOL-92.

## Question

CamAPS FX shows carbs the user flags as hypoglycaemia treatment, but never gives insulin for them
(user manual §7). Loop doses against every gram it is told about. A rescue entry therefore raises
Loop's forecast just as the person comes out of a low, and Loop resumes insulin into the recovery.
Does hiding those entries from Loop reduce lows after rescues, without costing TIR?

## Design

- **Cohort:** the 189 donors of frontier's 2026-10-23 dosing harness who log at least one rescue a
  week over 2026-06-01 → 10-07 (`runs/2026-10-25-myloop-rescue/per_donor.csv`): 40 donors. Each
  donor's window is frontier's: the last 28 full days, with 22 h of warm-up.
- **Rescue:** a carb entry with no manual bolus within ±15 min, made when the last CGM reading
  (≤ 10 min old) was < 70 mg/dL, or < 90 and falling ≥ 1 mg/dL/min over 15 min. Loop has no
  hypo-treatment flag, so this rule stands in for one. That is a limit: a real flag marks intent,
  this rule infers it.
- **Arms**, same binary as frontier's traces (`dr/loop-eval`, 2026-10-23):
  - **gr:** guard + runway, frontier's existing traces.
  - **gr_nr:** gr with the rescue entries removed from the controller's carbs (`carbs.json`, and
    their `carb_revisions.json` versions).
  - **gr_n095 / gr_n105:** frontier's needs-dial points around gr, used for the lift.

  The counterfactual plant does not read carbs: a rescue's glucose effect stays in the measured ICE.
  Only what the controller sees changes. **Identity:** an unfiltered mirror reproduces frontier's gr
  traces bit for bit on i001, i003 and i005.
- **Measures:** paired against gr, 95 % person-bootstrap CI.
  - Whole window: ΔTIR, Δt<70, Δt<54.
  - Local, in the 3 h after each rescue entry: Δt<70, Δt<54, and Δ insulin delivered.
- **Lift on the lows axis that fits the mechanism:** ΔTIR − slope × Δt<70, with the slope taken
  through the needs-dial points (gr_n095, gr, gr_n105). Positive lift means it is not just the
  dial.

## Bar (fixed before running)

**Pass (replay)** needs all three:

1. Whole-window Δt<70 < 0 with its CI below 0.
2. ΔTIR CI lower bound ≥ −0.3.
3. t<70 lift CI lower bound > 0.

**Mechanism check:** at least half of the whole-window Δt<70 lies in the 3 h after rescues. If it
doesn't, the effect is not doing what the mechanism claims.

## Limits that bound the claim

- **Replay's lows axis is unvalidated (ledger M11):** static replay predicts lows changes 4–5×
  too large. It also inherits the field's rescue carbs as fixed ICE, which is exactly the confound
  this mechanism touches. A pass goes to the ICE generator, whose rescues respond to the
  counterfactual glucose, before any verdict.
- **The binary predates 8fa8411** (unattended cycles deliver). That holds for both arms, so the
  paired delta stands; absolute levels may be off.

## Result (2026-10-25): FAILS, closed in this form

Run: `runs/2026-10-25-myloop-e2/` (`run_e2.py`, `score_e2.py`, `e2_per_donor.csv`). 40 donors, 483 rescues in
window (median 9 per donor in 28 days).

| | gr_nr − gr, 95 % CI | Bar |
|---|---|---|
| ΔTIR | −0.39 [−0.61, −0.20] | CI lo ≥ −0.3: **fails** |
| Δt<70 | +0.005 [−0.11, +0.12] | CI below 0: **fails** |
| Δt<54 | −0.015 [−0.05, +0.02] | — |
| Δ mean glucose | +1.1 mg/dL [+0.4, +2.1] | — |
| t<70 lift vs needs dial | −0.40 [−0.66, −0.17] | CI lo > 0: **fails** |
| Local, 3 h after rescues: Δt<70 | −0.92 [−1.81, −0.19] | — |
| Local: Δ insulin per rescue | −0.18 U [−0.39, −0.01] | — |

- **Locally it works as designed:** in the 3 h after a rescue, Loop gives less insulin and there are
  fewer lows.
- **Across the window there is nothing left:** whole-window t<70 is flat, so lows rise elsewhere
  by about as much as they fall after rescues. TIR drops by 0.4. Against the needs dial it is worse
  than simply backing off.
- **Exploratory, not pre-registered (`explore_e2.py`):** by entry size, time > 180 in the 0–3 h and
  3–8 h after rises by
  - ≤ 15 g (n 281): +1.2 / +1.4 points, against −0.75 below 70 in 0–3 h;
  - > 25 g (n 104): +7.3 / +9.0 points.

  Many large "rescues" are unbolused food eaten at low-normal glucose. Hiding them defers insulin,
  and Loop catches up hours later (+0.36 U in 3–8 h). Even small rescues trade highs for lows at
  about the needs dial's rate.
- **What this does not test:** a real hypo-treatment flag marks the user's intent. The glucose rule
  can only infer it, and it catches meals. Testing the CamAPS feature as it ships would need a flag
  in Loop and data from people using it. LoopEval has neither.
