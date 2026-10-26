# E4 — 780G-style rise-gated bolus gate, with Control-IQ and 780G reference arms (pre-registration)

Written 2026-10-25, after the identity check and before any arm ran. Board: TIDEPOOL-95. Evidence: `780g-controliq-unannounced.md`.

## Question

When the MiniMed 780G detects a meal nobody announced, it does not enlarge the correction. It lowers the low-glucose
threshold that its safety check holds the correction to, from 80 to 50 mg/dL, so less of each correction is trimmed (US10894126B2;
Edd 2026). Loop has the same kind of check: an automatic bolus is zeroed when the predicted minimum falls below the
correction-range floor. That happens on the classic early-meal forecast, which dips under insulin on board before the rise
carries it up. Does loosening that gate only while glucose is rising let Loop treat unannounced meals sooner, without adding
lows?

Second question, descriptive: where do Control-IQ's and the 780G's bolus rules, run on Loop's forecast, sit against
Loop's own needs dial?

## Mechanism (`--candidate-low-gate-rise-drop D`, this branch)

While the trailing 30-min glucose slope is ≥ 1.0 mg/dL/min and BG ≥ 120, the automatic bolus is gated off only when the
predicted minimum is more than D below the correction-range floor, and never below the suspend threshold. Loop's
forecast, its suspend guard, the σ band and the runway are unchanged. **Identity:** with the flag off, the new binary
reproduces merged main (c04a6630) bit for bit on i001, i003 and i005 (`runs/2026-10-25-myloop-e4/idcheck.py`).

## Design

- **Cohort:** frontier's 189-donor dosing harness, last 28 full days, 22 h warm-up, its per-donor flags.
- **Regime:** no carb entries, no user boluses (`--no-carb-entries --no-user-boluses`). All arms use the automatic-bolus
  strategy with a flat application factor (AF) of 0.4: the donor's `--temp-basal-strategy` (80 donors) and GBAF (3) are
  dropped. Guard + runway (`gr`) on in every arm. Binary `loop-eval-e4` (this branch at c04a6630 + the new flags).
- **Arms:**
  - `ab`: AF 0.4 at needs 0.90 / 0.95 / 1.00 / 1.05 / 1.10. This is the reference dial.
  - `rg30`, primary: `ab` + rise gate, D = 30.
  - `rgmax`: D = 999 (gate down to the suspend threshold during a rise).
  - `lg30`, control: D = 30 at every cycle, no rise condition (slope and BG conditions disabled).
  - `ciq`, reference: AF 0.6, correction target 110 (single value), automatic bolus only when the 30-min forecast
    exceeds 180 and never within 60 min of the last bolus.
  - `mdt`, reference: AF 1.0, correction target 120 (single value), every 5 min.

  Candidate and reference arms at needs 1.00.
- **Measures**, paired against `ab` at 1.00, 95 % person-bootstrap CI: ΔTIR, Δt<54, Δt<70, Δ mean, Δ insulin; the mean
  insulin on board at downward crossings of 54 mg/dL (IOB-at-crossing-54). Lift on t<54 = ΔTIR − slope × Δt<54, with the
  slope fitted through the five `ab` dial points.

## Bar (fixed before running)

**`rg30` passes (replay)** if all four hold:

1. ΔTIR CI lower bound > 0.
2. t<54 lift CI lower bound > 0.
3. Δ IOB-at-crossing-54 CI lower bound ≤ 0, i.e. no sign that more insulin is carried into severe lows.
4. Lift(`rg30`) > lift(`lg30`). The rise condition has to matter; otherwise it is a looser gate, i.e. a dial.

`rgmax` is read the same way, as the strong end of the dose–response. A pass goes to the ICE generator or the additive plant
before any verdict (M11). `ciq` and `mdt` have no bar: they are reported as ΔTIR, Δt<54 and lift against Loop's dial.

## Limits that bound the claim

- The rise detector (30-min slope, two thresholds) is a stand-in. The 780G's real detector thresholds are not public.
- `ciq` and `mdt` use their bolus rules on Loop's forecast, insulin model and guards. Control-IQ's basal increase above
  schedule, its 30-min MPC and the 780G's PID basal and 1800/TDD correction ISF are not modelled. They say where the
  rules sit, not how those systems would do.
- Replay's lows axis is unvalidated (ledger M11). The plant's response to extra insulin is the donor's measured ISF
  through counterfactual replay.
