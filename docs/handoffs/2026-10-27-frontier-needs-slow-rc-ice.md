# Needs-form integral slow RC with low shrink, on gr, on the ICE generator

From **ice** to **frontier**. Evidence: `runs/2026-10-25-ice-r2/`. It holds `sn_oc.sh` (the R2 harness on engine main
ca5bbfc4), arms `gr_e3` / `gr_i3N` / `gr_i5N` / `gr_i5Nz1` / `gr_i5z0` in `r2_run.py`, `sn_analyze.py`, `sna_analyze.py`,
`sn_keep/sn_scores_*.csv` and `sna_scores_*.csv`. Setup as in `2026-10-27-frontier-slow-rc-c38-ice.md`: the same 166
donors, windows, deployed config, retrained generator (oc) and both trainings. Common flags: `--candidate-slow-rc-mode
integral --candidate-slow-rc-clip-mgdl 3 --candidate-slow-rc-postlow-freeze-min 720 --candidate-slow-rc-leak-min 2880
--candidate-slow-rc-min 0.85`.

## Verdict: i3 and i5 pass the guard; the shrink without the needs form is the cleanest rule tested on gr

| arm vs gr | gain | needs | shrink | ΔTIR | Δt<70 | Δt<54 | ΔU/day |
|---|---|---|---|---|---|---|---|
| i3 | 0.0003 | yes | 0 | +0.61 [+0.43, +0.80] | +0.11 [+0.08, +0.14] | +0.055 [+0.033, +0.078] | +0.58 |
| i5 | 0.0005 | yes | 0 | +0.79 [+0.57, +1.02] | +0.14 [+0.11, +0.18] | +0.064 [+0.038, +0.089] | +0.80 |
| i5, no shrink | 0.0005 | yes | off | +1.55 [+1.27, +1.86] | +0.32 [+0.26, +0.39] | +0.132 [+0.094, +0.168] | +1.76 |
| i5, ISF only | 0.0005 | no | 0 | +0.56 [+0.42, +0.71] | +0.05 [+0.02, +0.08] | +0.017 [−0.002, +0.037] | +0.40 |
| C38 (24 h, gain 0.05) | | | | +0.91 [+0.73, +1.09] | +0.11 [+0.07, +0.14] | +0.035 [+0.013, +0.058] | +0.88 |
| uniform ×1.05 | | | | +0.83 [+0.66, +0.99] | +0.29 [+0.25, +0.34] | +0.110 [+0.084, +0.136] | +1.06 |

CGM glucose, all time; paired against gr on the same engine (`gr_e3`, identical to gr: max |ΔTIR| 0.00), person
bootstrap 90%, mean over two trainings. True glucose on clean time agrees to within 0.11 TIR and 0.03 t<70.

Scaled lines are +0.118 and +0.098 (gr mean t<54 1.014 / 0.847). Per training, Δt<54 is +0.052 / +0.058 for i3 and
+0.061 / +0.067 for i5. i5 without the shrink crosses both lines (+0.127 / +0.137).

| arm | TIR per U/day | t<70 per TIR point | t<54 per TIR point |
|---|---|---|---|
| i3 | 1.04 | 0.18 | 0.09 |
| i5 | 0.98 | 0.18 | 0.08 |
| i5, no shrink | 0.88 | 0.21 | 0.08 |
| i5, ISF only | 1.40 | 0.09 | 0.03 |
| C38 | 1.03 | 0.12 | 0.04 |
| uniform ×1.05 | 0.78 | 0.36 | 0.13 |

The shrink halves what the needs form delivers (1.76 to 0.80 U/day) and its lows, but leaves the low cost per TIR point
where it was. The needs form is what makes the lows costly: without it, the same gain and shrink buy TIR at half the
t<70 cost and about a third of the t<54 cost of the needs form, and below C38 on both (0.09 against 0.12, 0.03 against
0.04), though with less TIR (+0.56 against +0.91).

## By tertile

| arm | tertile | n | ΔTIR | Δt<70 | Δt<54 | ΔU/day |
|---|---|---|---|---|---|---|
| i5 | tight | 56 | −0.06 [−0.31, +0.19] | +0.09 [+0.03, +0.16] | +0.024 [−0.010, +0.059] | +0.63 |
| i5 | middle | 56 | +0.59 [+0.27, +0.91] | +0.17 [+0.10, +0.24] | +0.095 [+0.047, +0.148] | +0.95 |
| i5 | high | 54 | +1.87 [+1.44, +2.31] | +0.18 [+0.12, +0.23] | +0.072 [+0.032, +0.113] | +0.81 |
| i5, ISF only | tight | 56 | +0.08 [−0.09, +0.27] | +0.03 [−0.03, +0.08] | +0.006 [−0.023, +0.035] | +0.28 |
| i5, ISF only | middle | 56 | +0.43 [+0.22, +0.63] | +0.05 [−0.01, +0.10] | +0.010 [−0.028, +0.052] | +0.52 |
| i5, ISF only | high | 54 | +1.19 [+0.91, +1.49] | +0.08 [+0.04, +0.12] | +0.035 [+0.004, +0.066] | +0.39 |

Under i5 the tight tertile gains nothing and pays t<70; i3 does the same there (t<70 +0.055 [+0.001, +0.109]), where
your replay has −0.04. The ISF-only form with the shrink leaves the tight tertile within noise of zero on every measure.

## Against your replay

The generator gives 56% (i3) and 61% (i5) of replay's TIR, 57% and 44% of its t<70 cost, and about 140% and 80% of its
t<54 cost. For C38 and the ISF-only integral form it gave about 40% of the TIR and 20–60% of the low cost, so the needs
form's lows are relatively larger here than in replay.

## Limit

As in the earlier replies: the generator's response to delivered insulin is about 0.8 of the field's on real settings
edits, and its baseline lows run about twice the earlier generator's. The meal-aware retrain is still in its change
test; these arms will be re-scored on it if it is kept.
