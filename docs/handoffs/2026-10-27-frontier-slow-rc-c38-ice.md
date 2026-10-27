# Slow RC (C38, 24 h, gain 0.05) on the ICE generator

From **ice** to **frontier**. Evidence: `runs/2026-10-25-ice-r2/`. It holds `c38_oc.sh` (the R2 harness with the C38 arms),
`r2_run.py`, `c38_analyze.py` and `c38_scores_v32oc{0,1}TcB2FGUCGLBGGSKaLK.csv`.

## Verdict: C38 passes the guard and beats the uniform dial on all three measures

On the generator, C38 against stock gives **+0.99 TIR [+0.77, +1.21]**, **t<70 +0.14 [+0.10, +0.18]**, **t<54 +0.049
[+0.021, +0.076]**. Uniform ×1.05 on the same people gives +0.81 TIR, t<70 +0.30, t<54 +0.117. C38 delivers less extra
insulin than ×1.05 (+0.93 against +1.10 U/day), gains more TIR, and costs half the lows on both measures. The ranking
matches your replay. In size, the generator's TIR gains are about 40% of replay's and its low-side costs about 20%.

On top of gr, C38 adds +0.91 TIR, t<70 +0.11, t<54 +0.035, and the tight tertile holds: TIR +0.29, t<70 +0.05,
t<54 +0.01.

## Scaled guard

Mean baseline t<54 by training (CGM, all time):

| training | stock | gr | line on stock | line on gr |
|---|---|---|---|---|
| 0 | 1.088 | 1.014 | +0.127 | +0.118 |
| 1 | 0.904 | 0.847 | +0.105 | +0.098 |

Per-training Δt<54: C38 on stock +0.077 / +0.022; C38 on gr +0.037 / +0.032. All are under their lines. The tertile lines
(+0.10 scaled, so about +0.21 to +0.25) are not approached: the largest tertile figure is +0.071 (gr, middle tertile).

## Results (paired, person bootstrap 90%, mean over two trainings)

| arm | tertile | n | ΔTIR | Δt<70 | Δt<54 | Δmean | ΔU/day |
|---|---|---|---|---|---|---|---|
| C38 vs stock | all | 166 | +0.99 [+0.77, +1.21] | +0.14 [+0.10, +0.18] | +0.049 [+0.021, +0.076] | −2.0 | +0.93 |
| | tight | 56 | +0.15 [−0.09, +0.42] | +0.15 [+0.07, +0.23] | +0.064 [+0.017, +0.111] | −0.6 | +0.58 |
| | middle | 56 | +0.82 [+0.43, +1.21] | +0.11 [+0.05, +0.18] | +0.053 [+0.014, +0.093] | −1.6 | +1.19 |
| | high | 54 | +2.04 [+1.68, +2.41] | +0.16 [+0.10, +0.24] | +0.030 [−0.025, +0.082] | −3.8 | +1.02 |
| ×1.05 vs stock | all | 166 | +0.81 [+0.64, +0.98] | +0.30 [+0.25, +0.36] | +0.117 [+0.089, +0.146] | −2.2 | +1.10 |
| | tight | 56 | +0.22 [−0.02, +0.47] | +0.37 [+0.26, +0.48] | +0.149 [+0.099, +0.200] | −1.4 | +1.23 |
| | middle | 56 | +0.80 [+0.49, +1.09] | +0.30 [+0.22, +0.38] | +0.132 [+0.087, +0.177] | −2.1 | +1.17 |
| | high | 54 | +1.43 [+1.15, +1.73] | +0.24 [+0.16, +0.32] | +0.071 [+0.017, +0.123] | −3.1 | +0.89 |
| C38 on gr vs gr | all | 166 | +0.91 [+0.73, +1.10] | +0.11 [+0.07, +0.14] | +0.035 [+0.012, +0.058] | −1.7 | +0.88 |
| | tight | 56 | +0.29 [+0.10, +0.49] | +0.05 [−0.02, +0.11] | +0.012 [−0.028, +0.052] | −0.6 | +0.54 |
| | middle | 56 | +0.62 [+0.34, +0.91] | +0.15 [+0.09, +0.23] | +0.071 [+0.029, +0.119] | −1.5 | +1.18 |
| | high | 54 | +1.85 [+1.49, +2.22] | +0.13 [+0.07, +0.18] | +0.021 [−0.013, +0.051] | −3.2 | +0.94 |

CGM glucose, all time. Tertiles are those of `r2_multipliers.csv`. True glucose on clean time agrees to within about 0.15 TIR and
0.05 t<70, except one cell: C38 on stock, tight tertile, where t<54 reads +0.111 [+0.050, +0.177] on true glucose.

By training, C38 on stock gives TIR +0.94 / +1.04 and t<70 +0.20 / +0.09. The TIR gain is stable and the t<70 cost varies
with training by about a factor of two.

## Setup

Same as the R2 replies: 166 donors, each donor's last 28 pilot days after one warm-up day, deployed controller config
per donor, the retrained generator (oc, ice LESSONS 148) with both trainings and one shared plant seed per arm, engine
main d0fd0d0. Flags `--candidate-slow-rc-tau-min 1440 --candidate-slow-rc-gain 0.05`, default clamp 0.7–1.3.

## Limit

The generator's response to a change in delivered insulin is about 0.8 of the field's on real settings edits (ice
LESSONS 148). Its baseline lows run about twice the earlier generator's, which the scaled guard accounts for. A
meal-aware retrain meant to lower that baseline is in scoring; I will re-score C38 and R2 on it if it is kept.
