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

## Result (2026-10-26): `rg30` and `rgmax` FAIL bar 4, closed

Run: `runs/2026-10-25-myloop-e4/` (`run_e4.py`, `score_e4.py`, `e4_per_donor.csv`). 189 donors, 1,890 sims, none failed.
Reference (`ab`, needs 1.00): TIR 51.8, t<54 1.00, t<70 3.07, 41.3 U/day. Dial, ΔTIR / Δt<54: 0.90 −4.73 / −0.40;
0.95 −2.24 / −0.21; 1.05 +1.57 / +0.23; 1.10 +2.89 / +0.50.

| vs `ab` @ 1.00, 95 % CI | `rg30` | `rgmax` | `lg30` (control) |
|---|---|---|---|
| ΔTIR | +0.06 [+0.03, +0.11] | +0.07 [+0.03, +0.12] | +0.25 [+0.18, +0.33] |
| Δt<54 | −0.002 [−0.008, +0.003] | −0.002 [−0.009, +0.003] | +0.004 [−0.012, +0.019] |
| Δt<70 | −0.006 [−0.030, +0.009] | −0.007 [−0.033, +0.010] | +0.063 [+0.025, +0.100] |
| Δ insulin (U/day) | +0.001 | +0.001 | +0.010 |
| Δ IOB-at-crossing-54 (U) | +0.001 [−0.004, +0.007] | +0.002 [−0.004, +0.008] | +0.010 [−0.009, +0.031] |
| t<54 lift | +0.07 [+0.01, +0.17] | +0.08 [+0.02, +0.20] | +0.21 [+0.06, +0.40] |
| t<70 lift | +0.08 [+0.01, +0.19] | +0.08 [+0.01, +0.21] | +0.07 [−0.07, +0.24] |

- Bars 1–3 pass for both; bar 4 fails: the always-on looser gate earns more t<54 lift than the rise-gated one. The rise
  condition does not matter, so per the pre-registration this is a looser gate, not a meal mechanism.
- The effect is a few hundredths of a TIR point. Depth is not the constraint (`rgmax` ≈ `rg30`): Loop's automatic bolus
  is rarely held back by this gate during a rise, so the 780G's threshold drop has almost nothing to release.

### Reference arms (descriptive)

| vs `ab` @ 1.00 | ΔTIR | Δt<54 | Δt<70 | Δ insulin (U/day) | t<54 lift |
|---|---|---|---|---|---|
| `ciq` | −12.8 [−14.5, −11.3] | −0.43 [−0.56, −0.32] | −1.22 | −0.91 | −9.2 [−10.6, −7.9] |
| `mdt` | +0.11 [−0.45, +0.73] | +0.16 [+0.09, +0.24] | +0.32 | +0.08 | −1.2 [−2.0, −0.5] |

- Control-IQ's bolus rule alone (hourly, only above a 180 forecast) leaves unannounced meals far undertreated (median
  Δ mean glucose +43 mg/dL). Its basal increase, which is not modelled here, is what carries Control-IQ between boluses.
- The 780G's full correction every 5 min buys no TIR over Loop's AF 0.4 and adds lows and IOB at 54 crossings
  (+0.10 U [+0.03, +0.16]): on Loop's forecast it sits below the dial.
