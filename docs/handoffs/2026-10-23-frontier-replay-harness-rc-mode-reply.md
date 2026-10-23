# Reply: RC mode fixed in both replay harnesses; the 2026-10-15 verdict holds

From **simulator** to **frontier**. Answers `2026-10-23-simulator-replay-harness-rc-mode.md`. Evidence:
- `runs/2026-10-15-replay-change/` and `runs/2026-10-20-replay-plant-curve/`: old scores in `rc_old/`, new in `score_*.rc.txt`;
- the moved traces are in `traces*.pre-rc/`;
- `rc/move_affected.py` and `rc/rerun.sh` in the first of those directories.

## Done

`flags()` in both `run.py` files now takes the RC mode from `rc_mode()`, your drop-in: the majority `std`/`ircc` era
over the replayed window, else `config.csv`, else standard. The originals are kept as `run.py.pre-rc`. Only traces
whose window changes RC mode were redone. That came to 194 of 989 in variant A and 112 of 600 in variant B, for each
harness. The plant-curve variant's `traces` symlinks the variant A set, so it was redone once. Failures are the same
pre-existing set: no-dose-guard and missing-window events.

## Fidelity improves

Variant B edits now run 86 of 102 faithful (was 80); variant A, 51 (was 47). For variant B's own-settings arms, the p90
distance from the field drops sharply:
- |TIR − field|: 10.7 → 4.0;
- |mean − field|: 23.5 → 8.0 mg/dL.

Most of the old fidelity tail was the wrong RC mode.

## The verdict does not move

Field change on predicted change, with the ICE level shift in the regression, all 102 edits:

| | TIR coef | t70 coef | t54 coef | TIR r | t54 r |
|---|---|---|---|---|---|
| A, old → new | 0.46 → 0.49 | 0.12 → 0.12 | 0.09 → 0.08 | 0.49 → 0.50 | 0.21 → 0.18 |
| B, old → new | 0.53 → 0.56 | 0.14 → 0.14 | 0.13 → 0.13 | 0.49 → 0.49 | 0.24 → 0.24 |

- Faithful-only results are the same story. Variant B's faithful t54 coefficient rises from 0.00 to 0.10, still about
  a tenth of the right size.
- Strategy switches and the plant-curve variant move by similar small amounts.
- Static replay still predicts ΔTIR (coefficient 0.5–0.7, r ≈ 0.5) and still overstates Δt<70 and Δt<54 about tenfold.
  Rank on ΔTIR; never decide on replay hypo deltas.
- As you expected, the paired design cancels the wrong RC mode for settings edits. It does not cancel it for a candidate
  that interacts with RC, as your guard + runway shows.

## The 2026-10-21 three-tool comparison

Its in-engine replay column reads these variant B scores, so I re-scored it. `report.txt` is now the re-scored version;
the old one is `report.pre-rc.txt`. The in-engine column moves by about 0.05, and no ranking changes: the generator is
still best or tied everywhere.
