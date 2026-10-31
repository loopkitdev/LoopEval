# E8 — Glucose-dependent delivery (CamAPS) as Loop's GBAF, on gr (pre-registration)

Written 2026-10-31, before the cohort ran. Board: TIDEPOOL-101. Baseline: gr (Pete, 2026-10-31).

## Question

CamAPS sets how much it may deliver by glucose: it delivers more when glucose is high and cuts back when low or falling
(idea 5 in the overlay). Loop already has the high-side half as the glucose-based application factor (GBAF): the share
of each recommended correction delivered as an automatic bolus rises with current BG. gr already covers the low side
through its guard, which frontier found should be left alone. Does GBAF on top of gr give lift over the needs dial?

## Design

- **Body:** ice generator, oc trainings 0 and 1, seed 0, 166 donors, no carb entries or user boluses, automatic bolus
  at AF 0.4 (REGIME=ab, which drops each donor's deployed GBAF). Engine and plant tree: frontier's gr2 run
  (`runs/2026-10-30-gr2-gen`, engine 03e0ce3), driver `scripts/gen/gen.py` (main 290c9b6, the same code as the 8a3a222
  copy used there). Reference and dial logs (`gr_p0`, `gr_pn105`, `gr_pn110`) come from that run, unchanged.
- **Arms:**
  - `gr_gbaf`: gr + Loop's shipped GBAF, AF 0.4 at ≤ 140 mg/dL rising to 0.7 at ≥ 220.
  - `gr_gbaf10`: steeper, 0.4 at ≤ 140 rising to 1.0 at ≥ 250.
- **Run dir:** `runs/2026-10-31-myloop-e8-gbaf/` (`arms.py`).

## Measures

ΔTIR, Δt<70, Δt<54, IOB at downward 54 crossings and U/day against `gr_p0`, mean of the two trainings, 95 % person
bootstrap, and each training on its own. Lift: TIR at matched t<70 against the dial line through `gr_p0`, `gr_pn105`
and `gr_pn110`.

## Bar (fixed before running)

1. **Lift:** TIR at matched t<70 over the dial, CI lower bound > 0, and the same sign in both trainings (ice LESSONS
   153). Otherwise GBAF is the dial in another form.
2. **Guard:** Δt<54 no more than the dial's at the same ΔTIR.
3. A lift under about 2× ice's training-to-training SD for TIR error (≈ 0.2–0.4) is reported as not separable from
   training noise, whatever its CI.

## Limits

- Only the no-entry regime with automatic bolus for everyone. Announced meals and temp-basal users are not tested.
- The generator's body uses each donor's deployed insulin curve, so this tests delivery timing and amount, not curve
  shape.
