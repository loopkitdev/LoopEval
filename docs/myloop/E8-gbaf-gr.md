# E8 — Glucose-dependent delivery (CamAPS) as a glucose-based application factor, on gr (pre-registration)

Written 2026-10-31, before the cohort ran. Board: TIDEPOOL-101. Baseline: gr (Pete, 2026-10-31).

## Question

CamAPS sets how much it may deliver by glucose: it delivers more when glucose is high and cuts back when low or falling
(idea 5 in the overlay). Loop has a glucose-based application factor (GBAF): the share of each recommended correction
delivered as an automatic bolus rises with current BG. gr already covers the low side
through its guard, which frontier found should be left alone. Does GBAF on top of gr give lift over the needs dial?

## Design

- **Body:** ice generator, oc trainings 0 and 1, seed 0, 166 donors, no carb entries or user boluses, automatic bolus
  at AF 0.4 (REGIME=ab, which drops each donor's deployed GBAF). Engine and plant tree: frontier's gr2 run
  (`runs/2026-10-30-gr2-gen`, engine 03e0ce3), driver `scripts/gen/gen.py` (main 290c9b6, the same code as the 8a3a222
  copy used there). Reference and dial logs (`gr_p0`, `gr_pn105`, `gr_pn110`) come from that run, unchanged.
- **Arms:**
  - `gr_gbaf`: gr + the engine's default GBAF ramp, AF 0.4 at ≤ 140 mg/dL rising to 0.7 at ≥ 220. This is **not** the
    ramp Loop ships (below): it never delivers less than the flat 0.4, so it tests only the "more when high" half.
  - `gr_gbaf10`: steeper, 0.4 at ≤ 140 rising to 1.0 at ≥ 250.
  - Loop's deployed `GlucoseBasedApplicationFactorStrategy` ramps 0.2 at lower target + 10 to 0.8 at 200 mg/dL, keyed on
    current BG, and so also delivers less than 0.4 near target. It is run as `gr_gbafL` and `sl2_gbafL` (job 166), low
    anchor from each donor's scheduled lower target over the last 35 days.
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

## Result (2026-11-01): the default ramp on gr gives a small lift over the dial, in both trainings

Run: `runs/2026-10-31-myloop-e8-gbaf/` (`arms.py`, `scores_*.csv`). 166 donors × 2 trainings, all 664 new runs scored.
Change against `gr_p0`, mean of the two trainings, 95 % person bootstrap:

| | ΔTIR | Δt<70 | Δt<54 | Δ IOB at 54 (U) | ΔU/day |
|---|---|---|---|---|---|
| needs 1.05 (dial) | +1.02 [+0.84, +1.20] | +0.203 | +0.051 | +0.066 | +0.72 |
| needs 1.10 (dial) | +1.78 [+1.52, +2.05] | +0.415 | +0.112 | +0.127 | +1.54 |
| `gr_gbaf` (0.4→0.7, 140→220) | +0.60 [+0.44, +0.76] | +0.073 | +0.026 | +0.019 [−0.007, +0.046] | +0.52 |
| `gr_gbaf10` (0.4→1.0, 140→250) | +0.77 [+0.58, +0.97] | +0.107 | +0.037 | +0.054 | +0.80 |

TIR over the dial line at matched t<70:

| | lift | training 0 | training 1 |
|---|---|---|---|
| `gr_gbaf` | +0.23 [+0.04, +0.42] | +0.21 | +0.25 |
| `gr_gbaf10` | +0.24 [+0.03, +0.44] | +0.13 | +0.34 |

- **Bar 1 passes** for both arms: CI above 0, same sign in both trainings. At matched t<54 the lift is +0.08 and +0.02,
  CIs spanning 0.
- **Bar 2 passes:** Δt<54 is at or below the dial's at the same ΔTIR (dial ≈ 0.030 at +0.60 TIR; `gr_gbaf` 0.026).
- **Bar 3, borderline:** a lift of +0.23 sits at the bottom of the 0.2–0.4 band set from ice's training-to-training
  SD. The paired arms agree across trainings (+0.21 / +0.25), which that SD does not measure.
- The steeper form buys more TIR for proportionally more t<70; its lift is no larger. GBAF's edge is where it spends
  insulin (when glucose is high), not how much.
- Smaller than C38 slow RC on gr (+0.33 [+0.07, +0.56], frontier).

## On the ledger base, the default ramp adds nothing (2026-11-02)

Base: gr2 + stateless slow RC as shipped in LoopKit/LoopAlgorithm#16 (frontier's `g2w_t1440_g5_sl2`, engine 6b1969a,
35-day window; its logs symlinked in). New arms: `sl2_gbaf` (default ramp, as `gr_gbaf`) and `sl2_pn105` (needs 1.05,
the dial on this base). Change against the base, mean of two trainings, 95 % person bootstrap, 166 donors:

| | ΔTIR | Δt<70 | Δt<54 | Δ IOB at 54 (U) | Δ insulin |
|---|---|---|---|---|---|
| needs 1.05 (dial) | +0.56 [+0.39, +0.73] | +0.159 | +0.046 | +0.073 [+0.03, +0.12] | +2.8 % |
| `sl2_gbaf` | +0.29 [+0.12, +0.45] | +0.064 | +0.028 | +0.069 [+0.02, +0.12] | +3.1 % |

Lift over the dial at matched t<70: −0.03 [−0.27, +0.18], training 0 +0.03, training 1 −0.10. Bar 1 fails: the
default ramp's lift on gr is taken up by the slow RC. The dial line here is a straight line through two points.
