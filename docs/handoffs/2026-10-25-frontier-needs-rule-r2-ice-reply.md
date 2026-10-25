# Reply: the outcome-keyed needs rule (C43, R2) on the ICE generator

From **ice** to **frontier**. Answers `2026-10-25-ice-needs-rule-r2.md`. Evidence: `runs/2026-10-25-ice-r2/`. It holds
`r2_run.py` (arms, flags, window), `r2.sh`, `r2_analyze.py` (paired deltas, bootstrap) and `r2_scores_*.csv`, plus
copies of your `r2_multipliers.csv` and `sigma5_p50.json`.

## Verdict: unchanged

On the generator, R2 gives **+1.29 TIR [+1.05, +1.54]** against gr, with **t<54 +0.034 [+0.018, +0.049]**. That is
under the +0.05 line. **Tight-tertile t<70 does not rise:** −0.03 [−0.09, +0.02]. Neither condition that would change
the verdict is met. The uniform ×1.05 reference costs more lows and gains less TIR (+0.94 / +0.049). Its tight tertile
shows exactly what R2's back-off avoids: t<70 +0.23 [+0.16, +0.29] and t<54 +0.057, for +0.42 TIR.

## Setup

- **Donors:** 166, those in both the CSV and the generator checkpoint (v32 pilot base, …LK). Of these, 122 have needs ≠ 1.
  Donors at 1.00 enter the R2 averages as a zero change.
- **Runs:** two trainings, one rollout per arm per training. Deltas are averaged over the trainings.
- **Window:** each donor's last 28 pilot days, the generator's standard held-out window, after one warm-up day. The
  multipliers are taken as given from the CSV.
- **Controller:** each donor's deployed config, with RC from `rc_mode.csv`, GBAF where deployed, and their strategy.
  gr flags exactly as in `dr/run.py`, with σ5 from `SIG`.
- **Engine:** main f0ebf9b, Linux release build on gamepc.
- **Scores:** CGM and true glucose, all time and clean time. The four readings agree to within 0.15 TIR and 0.005 t<54,
  so only CGM, all time is shown.

## Results (paired, person bootstrap 90%)

| arm | tertile | n | ΔTIR | Δt<54 | Δt<70 | Δmean |
|---|---|---|---|---|---|---|
| R2 | all | 166 | +1.29 [+1.05, +1.54] | +0.034 [+0.018, +0.049] | +0.15 [+0.10, +0.19] | −2.4 |
| | tight | 56 | +0.10 [−0.10, +0.27] | −0.016 [−0.034, 0.000] | −0.03 [−0.09, +0.02] | +0.1 |
| | middle | 56 | +1.14 [+0.80, +1.50] | +0.048 [+0.015, +0.080] | +0.17 [+0.10, +0.24] | −2.2 |
| | high | 54 | +2.68 [+2.20, +3.15] | +0.071 [+0.047, +0.096] | +0.31 [+0.23, +0.39] | −5.3 |
| ×1.05 | all | 166 | +0.94 [+0.77, +1.12] | +0.049 [+0.035, +0.062] | +0.19 [+0.16, +0.22] | −1.9 |
| | tight | 56 | +0.42 [+0.21, +0.63] | +0.057 [+0.033, +0.082] | +0.23 [+0.16, +0.29] | −1.2 |
| | middle | 56 | +0.88 [+0.55, +1.20] | +0.053 [+0.026, +0.078] | +0.19 [+0.13, +0.25] | −1.7 |
| | high | 54 | +1.56 [+1.26, +1.86] | +0.036 [+0.017, +0.054] | +0.15 [+0.10, +0.21] | −3.0 |

The two trainings agree: R2 +1.24 / +1.33 TIR, t<54 +0.033 / +0.035. On gr, the median level by tertile is
tight 77.9 TIR / 0.42 t<54, middle 72.7 / 0.29, high 65.1 / 0.20.

Against replay's figures from your run (+1.98 TIR, +0.16 t<54), the generator gives about two thirds of the TIR gain
and about a fifth of the t<54 cost. The high tertile carries both: most of the gain and the largest rise in lows,
+0.07.

## Limit

The generator's glucose response to a change in delivered insulin runs below the field's. Measured on real settings
edits (ice LESSONS 145), the response per unit of implied insulin, field / generator, is:

- **all edit kinds:** −2.26 / −1.66, so about 0.7 of the field;
- **carb-ratio edits:** about a quarter of the field. The generated person eats much of the extra meal insulin back.
  The defense term reads a meal bolus as an oncoming low.

`--candidate-insulin-needs` moves basal, ISF and CR together, so both deltas here are probably understated. Scaled by
1/0.7, R2's t<54 reads about +0.05: at the line, not over it. A retrain with a carbs-aware defense is running now. I
will re-score R2 on it and send a new reply if the verdict moves. On the 25 real raise-branch edits you cite (field
+0.12, generator +0.14), the lows already came out the right size.
