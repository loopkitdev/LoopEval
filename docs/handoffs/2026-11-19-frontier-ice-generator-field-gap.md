# The generator runs better than the field: too few bad days, and ordinary days too good

From **frontier** to **ice** · 2026-11-19. Evidence: `runs/2026-11-19-gap/` (`diag.py`, `ablate.py`,
`spread.py`, `check2.py` and their CSVs) and the generator arms in `runs/2026-11-13-gen-ifit2/` (jobs 418–420:
`an_stock`, `stock`, `an_stockG1`, `an_stockDep`). The replay traces it compares against are the stock base traces
in `runs/2026-10-23-frontier-dosing/dr/traces` (read only).

## Setup

The generator is the ifit2 base: `gen-v32-ifit2` donors, `PLANT_BASE_IOB_OWN=1`, `PATIENT_INSULIN_GAIN=1.25`,
`plant_pss`, both trainings (S=0/1), with entries (`ANNOUNCE=1`, `PLANT_NO_BOLUS=0`). The controller is each
person's own Loop with GBAF off. All of it is scored on the generator's own 28-day window and clean-time mask, for
166 people. The fixed-ICE replay is the same stock Loop on the same people, re-scored on exactly that window and
mask (163 people with at least 20 days covered). The replay's field column matches the steps' field to within
±0.3 TIR (IQR), so the two comparisons are like for like.

## 1. The gap is the generator, not the controller

Per-person differences from the field:

| | TIR | t<70 | t>250 | mean BG |
|---|---|---|---|---|
| Fixed-ICE replay − field | median −0.2, IQR [−1.2, +0.2] | +0.05 | +0.02 | +0.5 |
| Generator − field | median +2.4, IQR [−2.4, +7.4]; mean +3.1 | +0.63 (mean +1.04) | −0.10 (mean −0.92) | −3.7 (mean −5.2) |

The controller reproduces the field when the body is the person's real ICE, so the difference comes from the
generated body and behaviour. The generator gives about 6% less insulin than the field and still runs about
5 mg/dL lower.

## 2. Insulin gain ×1.25 accounts for about half the lows gap, but not the level

| Generator − field (means) | gain 1.25 | gain 1.0 |
|---|---|---|
| TIR | +3.35 | +2.79 |
| t<70 | +0.94 | +0.47 |
| t<54 | +0.73 | +0.25 |
| t>250 | −1.1 | −0.3 |
| mean BG | −5.5 | −5.6 |

## 3. The TIR gap splits into missing bad days (about a third) and ordinary days running better (about two-thirds)

Days with at least 144 readings, averaged per person:

| | Field | Replay | Generator | Generator, gain 1.0 |
|---|---|---|---|---|
| % of days with TIR < 50 | 11.7 | 12.3 | 7.5 | 7.5 |
| % of days with > 20% of time above 250 | 8.1 | 10.0 | 5.5 | 7.0 |
| Mean TIR of the worst 3 days | 55.1 | 54.1 | 58.8 | — |
| Mean daily TIR | 74.9 | — | 78.5 | — |
| Mean TIR on days with TIR ≥ 50 | 79.1 | — | 81.3 | — |

The daily-TIR gap is +3.5. Restricted to days with TIR ≥ 50 it is +2.4 (mean) and +1.7 (median). The replay
reproduces the field's bad days and the generator has about a third fewer. The gain does not change the bad-day
rate.

Related observations:

- **The generator is smoother.** The SD of 5-minute changes is 7.6–7.9 against the field's 8.8.
- **Its distribution sits lower in the middle and upper range.** p50 is 3–7 mg/dL lower and p75 about 8 lower.
- **It ranks people's variability poorly.** Per-person correlation with the field is 0.84 for TIR but only 0.53 for
  glucose SD and 0.33 for CV.

## What I'd ask ice to look at

1. **Bad days.** What produces the field's TIR < 50 days, and why the generator has about a third fewer. Candidate
   causes are site failures or late site life, illness, missed boluses and sensor trouble. All of them are
   untested. A site-age split of field days (`runs/2026-11-18-site-age`) would test the first cheaply.
2. **Ordinary days.** Whether the +2.4 on ordinary days comes from the body or from the behaviour model. An
   open-loop, body-only check would tell them apart: real recorded insulin and real carb entries through the
   plant, no controller, compared with the field CGM. Does `plant_v3` support that mode?
3. **A `gen.py` trap, so the help text can be fixed.** `REGIME=ab` is described as "automatic bolus 0.4 for
   everyone", but it does not switch temp-basal users. The engine takes each cycle's strategy from the `mode` in
   `decision_times.csv`, which overrides the static flag. `ab` only drops GBAF (3 of 166 people). `an_stockDep`
   (without `REGIME`) is byte-identical to `an_stock`.
4. **Unresolved.** The plant's `doses.json` shows only basal rows, even for automatic-bolus users, so it is not
   clear where automatic boluses are logged.

## What this means for frontier's use of the generator

Candidate deltas on the generator stand as they are: every arm shares the same body, and frontier scores lift
against the gr2 dial on that same body. Absolute levels do not. The generator reads TIR high, lows high and highs
low against the field. Real-vs-generator plots carry that bias in their footnote.
