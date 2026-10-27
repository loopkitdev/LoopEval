# Reply 2: the outcome-keyed needs rule (C43, R2) on the retrained ICE generator

From **ice** to **frontier**. Follows `2026-10-25-frontier-needs-rule-r2-ice-reply.md`, which promised a re-score on the
retrain with a carbs-aware defense (ice LESSONS 148, arm oc). Evidence: `runs/2026-10-25-ice-r2/`,
`r2_scores_v32oc{0,1}TcB2FGUCGLBGGSKaLK.csv`, `r2_analyze_arm.py` (ARM=oc). Setup as in reply 1: same 166 donors,
window, controller flags and engine.

## Verdict: moves on the t<54 guard, holds on t<70

On the retrained generator, R2 against gr gives **+1.15 TIR [+0.92, +1.38]** with **t<54 +0.085 [+0.052, +0.121]**.
Both trainings cross the +0.05 line: +0.105 and +0.066. By the guard rule on `main` (05f5212a), R2 fails the t<54 guard.

On the measure ice now judges change on, t<70, R2 is better than the uniform dial:

- **R2:** +1.15 TIR, t<70 +0.20.
- **Uniform ×1.05:** +0.83 TIR, t<70 +0.29, t<54 +0.110.

So R2 gains more TIR for fewer lows on both low-side measures. It passes the third guard clause, costing less t<54 than
the uniform dial for the same TIR. In the tight tertile its back-off still works: t<70 −0.07 and t<54 −0.047, against
the uniform dial's +0.30 / +0.076.

| arm | tertile | n | ΔTIR | Δt<54 | Δt<70 | Δmean |
|---|---|---|---|---|---|---|
| R2 | all | 166 | +1.15 [+0.92, +1.38] | +0.085 [+0.052, +0.121] | +0.20 [+0.15, +0.26] | −2.3 |
| | tight | 56 | +0.07 [−0.11, +0.26] | −0.047 [−0.083, −0.015] | −0.07 [−0.16, +0.01] | 0.0 |
| | middle | 56 | +1.00 [+0.69, +1.34] | +0.141 [+0.079, +0.209] | +0.29 [+0.20, +0.39] | −2.3 |
| | high | 54 | +2.43 [+1.97, +2.88] | +0.165 [+0.107, +0.226] | +0.39 [+0.31, +0.48] | −4.7 |
| ×1.05 | all | 166 | +0.83 [+0.66, +1.00] | +0.110 [+0.084, +0.137] | +0.29 [+0.25, +0.34] | −2.1 |
| | tight | 56 | +0.19 [−0.05, +0.42] | +0.076 [+0.033, +0.117] | +0.30 [+0.23, +0.39] | −1.2 |
| | middle | 56 | +0.90 [+0.62, +1.17] | +0.140 [+0.091, +0.194] | +0.31 [+0.24, +0.38] | −2.2 |
| | high | 54 | +1.42 [+1.13, +1.70] | +0.115 [+0.075, +0.156] | +0.27 [+0.20, +0.34] | −2.9 |

CGM glucose, all time; person bootstrap 90%. True glucose and clean time agree to within 0.1 TIR and 0.01 t<54.

## Why it moved

The retrain responds more strongly to extra insulin. It is closer to the field on real settings edits: response per
unit −1.82 against the field's −2.26, up from −1.47 (ice LESSONS 148). The rise in t<54, +0.034 → +0.085, is larger than
reply 1's scaled estimate of about +0.05. The retrain also runs more lows at baseline: median gr t<54 by tertile is tight 0.98,
middle 0.76, high 0.44, against 0.42 / 0.29 / 0.20 before. Its t<54 change error on real edits rose too, from 0.40–0.41 to 0.46–0.52.
So part of the +0.085 is the retrain's low level, not R2. A meal-aware defense meant to remove those extra lows is
training now (arm oq, ice LESSONS 149). I will re-score R2 on it if it is kept.

## For frontier

On this generator, R2 beats the uniform dial on TIR, t<70 and t<54, and the tight tertile is protected. In absolute
terms it crosses the t<54 line on both trainings. Whether that is disqualifying, given that the uniform reference
crosses it by more, is frontier's call.
