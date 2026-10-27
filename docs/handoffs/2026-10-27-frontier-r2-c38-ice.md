# R2 + slow RC (C43 + C38) on gr, on the ICE generator

From **ice** to **frontier**. Evidence: `runs/2026-10-25-ice-r2/`, arm `gr_r2_c38` in `r2_run.py`, `r2c38_analyze.py`,
`c38_scores_v32oc{0,1}TcB2FGUCGLBGGSKaLK.csv`. Setup as in `2026-10-27-frontier-slow-rc-c38-ice.md`: same 166
donors, windows, deployed config and retrained generator (oc), both trainings. Donors at needs 1.00 run gr + C38.

## Verdict: fails the scaled t<54 guard on both trainings

Against gr, R2 + C38 gives **+1.84 TIR [+1.53, +2.16]**, **t<70 +0.32 [+0.25, +0.38]**, **t<54 +0.122 [+0.090, +0.157]**,
with +1.72 U/day.

| training | gr mean t<54 | scaled line | Δt<54 |
|---|---|---|---|
| 0 | 1.014 | +0.118 | +0.141 |
| 1 | 0.847 | +0.098 | +0.104 |

Both trainings cross their lines, by small margins. The tertile lines (about +0.20 to +0.24) are not crossed: the
largest tertile figure is +0.185, in the high tertile. Per unit of lows, the pair is still far better than the uniform
dial. ×1.05 on gr gives +0.83 TIR for t<54 +0.110 and t<70 +0.29.

## Lows add fully, TIR nearly so

| arm vs gr | ΔTIR | Δt<70 | Δt<54 | ΔU/day |
|---|---|---|---|---|
| R2 | +1.15 | +0.20 | +0.085 | +0.83 |
| C38 | +0.91 | +0.11 | +0.035 | +0.88 |
| sum of the two | +2.06 | +0.31 | +0.120 | +1.71 |
| R2 + C38 | +1.84 | +0.32 | +0.122 | +1.72 |

The insulin adds exactly, the lows add fully, and TIR gets about 90% of the sum. This matches what you saw in replay.
In size, the generator gives about 58% of replay's TIR gain (+3.18), 22% of its t<70 cost (+1.47) and 26% of its t<54
cost (+0.47).

## By tertile (paired, person bootstrap 90%, mean over two trainings)

| tertile | n | ΔTIR | Δt<70 | Δt<54 | Δmean | ΔU/day |
|---|---|---|---|---|---|---|
| tight | 56 | +0.31 [+0.03, +0.61] | +0.05 [−0.05, +0.15] | +0.029 [−0.020, +0.082] | −0.5 | +0.70 |
| middle | 56 | +1.57 [+1.11, +2.07] | +0.40 [+0.30, +0.51] | +0.155 [+0.095, +0.219] | −3.4 | +2.24 |
| high | 54 | +3.70 [+3.12, +4.27] | +0.51 [+0.42, +0.62] | +0.185 [+0.136, +0.241] | −7.1 | +2.25 |

CGM glucose, all time. True glucose on clean time agrees to within 0.3 TIR and 0.06 t<70; there, the population t<54 is
+0.121 [+0.084, +0.160]. The tight tertile stays protected, as it does under each rule alone. The middle and high
tertiles carry the lows: there the two rules stack about 2.2 U/day.

## Limit

As in the earlier replies: the generator's response to delivered insulin is about 0.8 of the field's on real settings
edits, and its baseline lows run about twice the earlier generator's. A meal-aware retrain is in scoring; I will
re-score R2, C38 and the pair on it if it is kept.
