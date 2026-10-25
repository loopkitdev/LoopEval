# E1 — Multi-model ranking of the insulin-action curve (pre-registration)

Written 2026-10-25, before any forecast was computed. Board: TIDEPOOL-91.

## Question

CamAPS FX runs competing models that differ in SC insulin absorption and action, and combines
them by how well each has explained recent CGM (US 8,062,249; Hovorka 2004). Does doing the same
with Loop's insulin curve explain the glucose that followed better than the donor's fixed preset?
And is any gain *adaptation* (weights that move over time), or only *personalization* (one better
fixed curve per person)?

## Design

- **Beds:** the nine 2-month BDDP beds of the ledger (`run_sweep.py` BEDS: bddp01, 03, 05, 06,
  07, 08, 09, 10, 11). Same exports, flags, and window as there (2026-05-09 → 07-07).
- **Forecasts:** decision-time replay on the field's own history, forecast curve exported per step,
  `--oracle-future-inputs`. The forecast then sees the insulin and carbs that were actually given
  after t, which makes it a test of the *model* rather than a test of the future dosing. CamAPS fits
  its models the same way.
- **Variants:** controller insulin curve `custom`, duration 360 min, peak ∈ {45, 55, 65, 75, 90,
  105} min. The donor's preset (75 rapid-acting, 55 Fiasp) is one of them, and it is the stock arm.
- **Target:** raw CGM at t + h, for h ∈ {30, 60, 90, 120, 180} min. Steps where no reading falls
  within ±5 min of t + h are dropped.
- **Adaptive arm (primary):** at each step, every variant gets a score: the exponentially forgotten
  mean squared error of its *matured* forecasts (made at s, with s + h ≤ t), half-life 3 days. The
  prediction is the inverse-score-weighted mean of the variants. Secondary arms: pick the single
  best variant instead of weighting; half-lives of 1 and 7 days.
- **Personalized arm:** the one variant with the lowest RMSE over the first half (05-09 → 06-07),
  held fixed.
- **Scoring:** RMSE on the second half (06-08 → 07-07) only. The first half is warm-up for the
  adaptive arm and training for the personalized arm. h = 120 is primary and h = 60 secondary.

## Bar (fixed before running)

- **P1, it beats stock:** adaptive RMSE at 120 min ≤ 0.95 × stock on ≥ 7 of 9 beds.
- **P2, adaptation beats personalization:** adaptive RMSE at 120 min ≤ 0.98 × the personalized
  arm on ≥ 6 of 9 beds.
- **Reading:**
  - P1 and P2 both pass: CamAPS-style ranking is worth a closed-loop candidate.
  - Only P1 passes: the lever is one per-person curve, which is a settings change, not adaptation.
  - Neither passes: insulin-curve ranking is closed. Carb-absorption variants come next (E1b).
- Worst bed reported beside the counts.

## Limits that bound the claim

- A better forecast is not a therapy gain (C19, O1, Lee 2024 TBME). A pass leads to closed-loop
  scoring, not to a verdict.
- Replay cannot judge the body's insulin curve. In the 2026-10-20 insulin-peak runs, changing the
  plant's curve moved outcomes by ≤ 0.6 TIR, while the controller's belief moved them 2–15 TIR. The
  closed-loop test of a passing arm therefore needs a plant whose curve is independent (additive or
  ICE generator), not fixed-ICE replay.
- In closed-loop data, insulin timing and carb timing are confounded (eda lesson 53 for ISF). A
  variant can win by soaking up carb-model error. E1b and a check restricted to carb-free steps
  separate the two.

## Result (2026-10-25): FAILS, insulin-curve ranking closed

Run: `runs/2026-10-25-myloop-e1/` (`run_e1.py`, `score_e1.py`, `e1_rmse.csv`). 63 replays. Each donor's preset
reproduces its custom twin exactly (max |Δ| 0.0 mg/dL), so the stock arm is the deployed curve.

| | P1: adaptive ≤ 0.95 × stock | P2: adaptive ≤ 0.98 × personalized |
|---|---|---|
| h = 120, all steps | 0 / 9, worst 1.023 | 0 / 9, worst 1.053 |
| h = 120, carb-free | 0 / 9, worst 1.010 | 2 / 9, worst 1.027 |
| h = 60, all steps | 0 / 9, worst 1.010 | 0 / 9, worst 1.020 |

- **Adaptive ≈ stock:** median ratio 0.999 at 120 min (range 0.959–1.023) and 0.992 at 60 min. The
  1-, 3- and 7-day half-lives give the same answer to three digits. The select variant does no
  better (median 0.982–0.988).
- **Personalization is worth at most ~2 %:** the best fixed peak on the first half reaches a median
  0.977 of stock on the second half at 120 min. At long horizons the hands-off beds lean toward
  later peaks (90–105 min), the same direction as the GIR-curve arm of the 2026-10-20 insulin-peak
  runs. At 30–60 min they lean toward earlier peaks. No single curve wins at every horizon.
- **Why there is nothing to rank:** even with the actual future insulin and carbs, 120-min RMSE is
  35–133 mg/dL depending on the bed. The insulin curve moves it by a few percent. The error lives
  in the unmodelled appearance (meals, absorption, behaviour), not in insulin timing.
