# E6 — A deliberately moved dose at unannounced rises (pre-registration)

Written 2026-10-29, after the identity check and a one-donor smoke run, before the cohort ran. Board: TIDEPOOL-101.

## Question

E5 classified, after the fact, the insulin that existing candidates happened to move or add, and found that moved insulin
carried no low cost. That is an association across changes built for other purposes. E6 moves insulin on purpose: an
extra automatic bolus at the start of each unannounced rise, which Loop then sees as insulin on board and takes back
out of its later dosing. Does insulin moved earlier this way raise TIR without lows, beyond what the needs dial can do?

## Mechanism (`--candidate-primer-mgdl X`, this branch)

At a cycle where the candidate's own CGM shows a rise, one extra automatic bolus of X / ISF U (rounded to 0.05 U) is
delivered on top of Loop's dose. Then no further primer for 180 min. A rise means:

- trailing 30-min slope ≥ 1.5 mg/dL/min;
- BG ≥ 30 mg/dL above its 60-min minimum;
- no BG < 80 in the last 60 min.

Loop's forecast, guards and dosing are unchanged; the primer enters its dose history, so later cycles withhold against
it. That is the "moved" path: nothing stops Loop giving it back except the meal itself.

**Identity:** with the flag off, the new binary reproduces the E4 `ab` traces bit for bit on i001, i003 and i005.
**Smoke (i001):** 46 primers in 28 days, 0.60–0.65 U each; net delivery +0.04 U/day against about 1 U/day primed.

## Design

- **Cohort, regime, window:** as E4. 189 donors, the last 28 days, no carb entries and no user boluses.
  - Every arm uses automatic bolus at AF 0.4, with gr on.
  - Binary `loop-eval-e6`.
- **Arms:** `pr30` (X = 30 mg/dL) and `pr60` (X = 60), against the E4 `ab` reference and its needs dial
  (0.90–1.10). The dial is reused from E4; the identity check above makes it the same reference.
- **Measures:**
  - Paired against `ab` at 1.00, with 95 % person-bootstrap CIs: ΔTIR, Δt<54, Δt<70, Δ mean, Δ insulin per day, and
    IOB at downward crossings of 54.
  - t<54 and t<70 lift against the dial.
  - Primer units per day, and the share of them still net delivered at the day level.

## Bar (fixed before running)

1. **It moves insulin:** net Δ insulin per day ≤ 25 % of the primer units delivered per day. This is a precondition.
   If it fails, the arm is adding insulin and is read as the dial.
2. **It pays,** with all three holding, for `pr30` or `pr60`:
   - ΔTIR CI lower bound > 0;
   - t<54 lift CI lower bound > 0;
   - Δ IOB-at-crossing-54 CI lower bound ≤ 0.

**Reading:**

- 1 and 2 hold: deliberately moved insulin buys TIR in replay. Boost experiment 2 (a detector-driven catch-up) is worth
  building. Any pass goes to the ICE generator before a verdict (M11).
- 1 holds, 2 fails with Δt<54 CI upper bound < +0.05: moved insulin is harm-neutral but buys nothing. Experiment 2 is
  not run.
- 1 holds and lows rise: moving insulin earlier is not free in replay, against E5's association.

## Limits that bound the claim

- The rise detector is a simple stand-in. It fires on non-meal rises too (dawn, stress, compression recovery).
- The primer is an output change, against the forecast-first principle. That is on purpose: the test needs a known amount
  of insulin moved, not a forecast change whose dose is unknown.
- Replay's lows axis is unvalidated (ledger M11).
