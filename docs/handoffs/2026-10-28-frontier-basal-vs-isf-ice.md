# Less insulin through basal or through ISF, on gr, on the ICE generator

From **ice** to **frontier**. Evidence: `runs/2026-10-25-ice-r2/`, arms `gr_B090` / `gr_S110` / `gr_D105` / `gr_D095` /
`gr_D090` in `r2_run.py` (engine main ca5bbfc4), `sbs_analyze.py`, `bs_matched.py`,
`sbs_scores_v32oc{0,1}TcB2FGUCGLBGGSKaLK.csv`. Setup as in `2026-10-27-frontier-slow-rc-c38-ice.md`: the same 166
donors, windows, deployed config, retrained generator (oc) and both trainings. B090 is
`--candidate-basal-rate-multiplier 0.90`, S110 is `--candidate-sensitivity-multiplier 1.10`. The dial moves both
together: basal ×0.95 with ISF ×1.05, ×0.90 with ×1.10, and ×1.05 with ×0.95.

## Verdict: basal leads ISF, as in your replay, but by a quarter as much, and neither beats the dial

| arm vs gr | ΔTIR | Δt<70 | Δt<54 | ΔU/day | t<70 per TIR point |
|---|---|---|---|---|---|
| basal ×0.90 | −1.12 [−1.28, −0.95] | −0.26 [−0.31, −0.22] | −0.080 [−0.102, −0.058] | −0.72 | 0.23 |
| ISF ×1.10 | −0.99 [−1.13, −0.85] | −0.09 [−0.12, −0.05] | −0.035 [−0.058, −0.013] | −0.59 | 0.09 |
| dial 0.95 / 1.05 | −1.05 [−1.20, −0.90] | −0.21 [−0.24, −0.17] | −0.068 [−0.088, −0.049] | −0.70 | 0.20 |
| dial 0.90 / 1.10 | −2.16 [−2.40, −1.92] | −0.39 [−0.44, −0.34] | −0.120 [−0.148, −0.092] | −1.31 | 0.18 |
| dial 1.05 / 0.95 | +0.82 [+0.68, +0.98] | +0.19 [+0.16, +0.23] | +0.072 [+0.046, +0.096] | +0.76 | 0.24 |

CGM glucose, all time; paired against gr (`gr_e3`, identical to gr), person bootstrap 90%, mean over two trainings. True
glucose on clean time agrees to within 0.09 TIR and 0.01 t<70. The two trainings agree to within 0.08 t<70 on every
arm. All arms lower t<54 or, for dial 1.05, stay inside the scaled lines (+0.118 / +0.098).

At about the same insulin cut, basal ×0.90 removes three times the t<70 of ISF ×1.10 for about the same TIR loss. The
dial at 0.95 / 1.05 sits between them, nearer basal.

## TIR at matched t<70, against each person's own dial

Each arm's TIR minus the TIR the person's dial (1.05, 1.00, 0.95, 0.90) gives at the arm's t<70, by linear
interpolation; positive means better than the dial.

| | n | basal ×0.90 | ISF ×1.10 | paired gap | your replay gap |
|---|---|---|---|---|---|
| all | 166 | −0.14 [−0.28, −0.01] | −0.33 [−0.49, −0.18] | +0.19 [−0.01, +0.38] | +0.78 |
| tight | 56 | −0.04 [−0.22, +0.14] | −0.12 [−0.28, +0.05] | +0.08 [−0.12, +0.27] | +0.28 |
| middle | 56 | −0.21 [−0.47, +0.02] | −0.37 [−0.64, −0.10] | +0.15 [−0.21, +0.51] | +0.52 |
| high | 54 | −0.17 [−0.43, +0.10] | −0.52 [−0.86, −0.16] | +0.35 [−0.08, +0.77] | +1.55 |

Your replay had basal +0.72 and ISF −0.03 against the dial. Here the order and the tertile pattern hold (gap growing
from tight to high), but the gap is about a quarter of replay's and its interval touches zero; basal does no better than
the dial, and ISF does worse. On true clean time the gap is +0.13 [−0.12, +0.39].

Limits on this reading: per person the dial is not monotone in t<70 on 216 of 332 person-trainings, and 21–27% of arm t<70 values fall outside the person's dial
range, where the interpolation holds the end value. The per-arm table above does not depend on either.

## By tertile

| arm | tertile | ΔTIR | Δt<70 | Δt<54 | ΔU/day |
|---|---|---|---|---|---|
| basal ×0.90 | tight | −0.61 [−0.87, −0.35] | −0.33 [−0.44, −0.24] | −0.100 [−0.141, −0.060] | −0.77 |
| basal ×0.90 | middle | −1.08 [−1.32, −0.84] | −0.29 [−0.35, −0.23] | −0.092 [−0.131, −0.055] | −0.68 |
| basal ×0.90 | high | −1.68 [−1.98, −1.40] | −0.16 [−0.21, −0.11] | −0.046 [−0.080, −0.013] | −0.71 |
| ISF ×1.10 | tight | −0.52 [−0.74, −0.30] | −0.11 [−0.17, −0.05] | −0.057 [−0.098, −0.018] | −0.51 |
| ISF ×1.10 | middle | −0.90 [−1.13, −0.68] | −0.06 [−0.13, +0.01] | −0.024 [−0.063, +0.020] | −0.65 |
| ISF ×1.10 | high | −1.57 [−1.83, −1.32] | −0.08 [−0.12, −0.04] | −0.025 [−0.064, +0.011] | −0.61 |

The tight tertile takes the largest t<70 cut from basal (−0.33) for the smallest TIR loss; there ISF ×1.10 loses
nearly as much TIR for a third of the t<70.

## Limit

The generator's response to delivered insulin is about 0.8 of the field's on real settings edits. On those edits it
carries no TIR signal for basal-only changes (field +2.0, generator 0), so its basal-lever TIR here is the part least
supported by the change test.
