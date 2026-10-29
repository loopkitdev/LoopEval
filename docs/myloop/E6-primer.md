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

## Result (2026-10-29): it moves insulin and beats the dial, but fails the IOB-at-54 condition

Run: `runs/2026-10-28-myloop-e6/` (`run_e6.py`, `score_e6.py`, `e6_per_donor.csv`, per-run `*.primer.txt`). 189 donors,
378 sims, none failed. Reference `ab` @ 1.00: TIR 51.8, t<54 1.00, t<70 3.07.

| vs `ab` @ 1.00, 95 % CI | `pr30` | `pr60` | dial 1.05 (for scale) |
|---|---|---|---|
| Primer delivered | 1.60 U/day | 3.23 U/day | — |
| Net Δ insulin | +0.04 U/day (2 % kept) | +0.08 U/day (2 % kept) | — |
| ΔTIR | +0.85 [+0.72, +1.00] | +1.54 [+1.32, +1.77] | +1.57 |
| Δt<54 | +0.024 [+0.012, +0.037] | +0.062 [+0.040, +0.085] | +0.234 |
| Δt<70 | +0.11 [+0.07, +0.15] | +0.28 [+0.21, +0.35] | — |
| Δ mean glucose | −3.0 mg/dL | −5.9 mg/dL | — |
| t<54 lift | +0.65 [+0.48, +0.82] | +1.03 [+0.76, +1.32] | 0 by definition |
| t<70 lift | +0.56 [+0.37, +0.73] | +0.75 [+0.45, +1.04] | — |
| Δ IOB-at-crossing-54 | +0.045 U [+0.017, +0.076] | +0.090 U [+0.046, +0.138] | −0.068 U |

- **Bar 1 passes:** Loop takes back 98 % of the primer. This is moved insulin.
- **Bar 2 fails on its third condition:** ΔTIR and t<54 lift pass with wide margins, but more insulin is on board when
  glucose crosses 54 (CI lower bound > 0). Under the pre-registered reading the arm fails.
- **Against the dial:**
  - `pr60` buys the same TIR as needs 1.05 at about a quarter of its t<54 cost.
  - Its t<54 lift is the largest of any no-entry candidate in this role (E3 `nc_hab` −0.19, E4 `lg30` +0.21).
- **Likely source of the IOB-at-54 signal (not yet measured):** the detector fires on any rise, not only on meals, and
  some rises turn back down while the primer is still on board.

## Stage 2 — retractable primer (pre-registration)

Written 2026-10-29, before the cohort ran.

- **Mechanism (`--candidate-primer-temp-min 30`):**
  - Same detector and size as `pr60`.
  - The primer is delivered as extra temp basal at X / ISF per 30 min, on top of Loop's rate.
  - It is cancelled for good at the first cycle where CGM rose < 5 mg/dL over the last 15 min.
  - Loop sees what was delivered.
- **Identity and smoke:**
  - With the new flag off, the binary reproduces `ab` and `pr60` bit for bit on i001, i003 and i005.
  - i001: 46 detections; 88 % of the bolus form's primer insulin was delivered before cancellation or the 30 min ran out.
- **Arm:** `pr60t`, scored against `ab` and the dial exactly as stage 1, with the same bar 1 and bar 2.
- **Also against `pr60`:** Δ IOB-at-crossing-54 and Δt<54 for `pr60t` − `pr60`, paired. The retractable form is meant to
  carry less insulin into lows.

### Stage 2 result (2026-10-29): the retractable form fails the same way, with less TIR

189 donors, none failed. 2.73 U/day of primer delivered (85 % of the bolus form's), net +0.07 U/day (2 % kept).

| `pr60t`, 95 % CI | vs `ab` @ 1.00 | vs `pr60` (paired) |
|---|---|---|
| ΔTIR | +1.25 [+1.06, +1.44] | −0.30 [−0.39, −0.20] |
| Δt<54 | +0.035 [−0.017, +0.070] | −0.027 [−0.075, +0.004] |
| Δt<70 | +0.21 [+0.14, +0.29] | −0.07 [−0.12, −0.01] |
| Δ IOB-at-crossing-54 | +0.058 U [+0.026, +0.094] | −0.014 U [−0.056, +0.024] |
| t<54 lift | +0.96 [+0.58, +1.45] | — |

- Bar 1 passes, and bar 2 fails on IOB at 54, as for `pr60`.
- Against `pr60` it carries no detectably less insulin into lows. It gives up TIR roughly in proportion to the smaller
  primer it delivers.
- The cancellation rarely bites: a rise that has already run 30 mg/dL keeps going for the next 30 min. Retracting a
  primer that has already been confirmed does not separate the rises that turn.

## Generator check (2026-10-29): half replay's TIR, the same insulin into lows, little better than the dial

Run on workmac with ice's generator as frozen for `docs/handoffs/2026-10-28-frontier-basal-vs-isf-ice.md` (plant
ice-cobt-nb, checkpoints `v32oc{0,1}TcB2FGUCGLBGGSKaLK`, the same 166 donors, windows and deployed config), engine main
7c3eae3a. Arms `gr_p30` and `gr_p60` (primer 30 / 60 mg/dL) against `gr_p0`, with no carb entries and no user boluses.
Run dir `runs/2026-10-29-myloop-e6-gen/` (`spr.sh`, `analyze.py`, `r2/spr_scores_*.csv`). 996 runs, none failed. Paired,
person bootstrap 90 %, mean over two trainings. Reference: TIR 68.6, t<70 2.00, t<54 0.46, 32.9 U/day.

| vs `gr_p0` | `gr_p30` | `gr_p60` | replay `pr60` |
|---|---|---|---|
| ΔTIR (CGM) | +0.39 [+0.28, +0.51] | +0.79 [+0.64, +0.95] | +1.54 |
| ΔTIR (true glucose, clean time) | +0.41 [+0.25, +0.57] | +0.75 [+0.57, +0.93] | — |
| Δt<70 | +0.085 [+0.063, +0.108] | +0.146 [+0.115, +0.178] | +0.28 |
| Δt<54 | +0.024 [+0.011, +0.038] | +0.048 [+0.032, +0.064] | +0.062 |
| Δ IOB at downward 54 crossings | +0.027 U [+0.000, +0.053] | +0.088 U [+0.051, +0.126] | +0.090 U |
| Δ insulin | +0.27 U/day | +0.58 U/day | +0.08 U/day |

- **Still moved insulin, less completely.** In a 12-donor sample of `gr_p60` (training 0, primer logged) the primer
  delivered 3.6 U/day and net insulin rose 0.40 U/day: 11 % kept (per donor −9 % to 39 %). Bar 1 (≤ 25 %) holds.
- **Δt<54 is inside the scaled guard lines** (+0.118 / +0.098) for both arms.
- **IOB at 54 crossings rises as in replay.** This is the body's insulin on board in the generator and the controller's
  in replay, so the two are not the same measure, but both fail bar 2's third condition by the same amount.
- **Against the dial** (ice's 2026-10-28 run: same donors, trainings and generator, engine ca5bbfc4), needs 1.05 gives
  +0.82 TIR for +0.19 t<70 and +0.76 U/day. `gr_p60` buys the same TIR for about three quarters of the t<70: t<70 per
  TIR point 0.18 against the dial's 0.23–0.24. In replay the primer's margin over the dial was several times larger.
