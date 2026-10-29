# Integral slow RC on gr, on the ICE generator

From **ice** to **frontier**. Evidence: `runs/2026-10-25-ice-r2/`. It holds `si_oc.sh` (the R2 harness on engine main
86e13c4c), arms `gr_si95` / `gr_si90` / `gr_e` in `r2_run.py`, `si_analyze.py` and `si_scores_v32oc{0,1}TcB2FGUCGLBGGSKaLK.csv`.
Setup as in `2026-10-27-frontier-slow-rc-c38-ice.md`: the same 166 donors, windows, deployed config, retrained generator
(oc) and both trainings. Flags: `--candidate-slow-rc-mode integral --candidate-slow-rc-gain 0.0010
--candidate-slow-rc-clip-mgdl 3 --candidate-slow-rc-postlow-freeze-min 720 --candidate-slow-rc-leak-min 2880`, with
`--candidate-slow-rc-min` 0.95 or 0.90. No needs form and no gate.

## Verdict: both pass the guard; small and clean

| arm vs gr | ΔTIR | Δt<70 | Δt<54 | ΔU/day |
|---|---|---|---|---|
| integral, min 0.95 | +0.13 [+0.02, +0.24] | +0.03 [−0.00, +0.06] | +0.018 [−0.004, +0.042] | +0.17 |
| integral, min 0.90 | +0.52 [+0.37, +0.67] | +0.09 [+0.06, +0.13] | +0.027 [+0.006, +0.048] | +0.49 |
| C38 (24 h, gain 0.05) | +0.91 [+0.73, +1.09] | +0.11 [+0.07, +0.14] | +0.035 [+0.013, +0.058] | +0.88 |
| uniform ×1.05 | +0.83 [+0.66, +0.99] | +0.29 [+0.25, +0.34] | +0.110 [+0.084, +0.136] | +1.06 |

CGM glucose, all time; paired, person bootstrap 90%, mean over two trainings. True glucose on clean time agrees to within
0.05 TIR and 0.01 t<70 at the population level.

Scaled lines are +0.118 and +0.098 (gr mean t<54 1.014 / 0.847). Per training, Δt<54 is +0.017 / +0.019 at min 0.95
and +0.042 / +0.012 at min 0.90, all far under the lines.

Per unit of extra insulin, the integral form at 0.90 buys about the same TIR as C38 (1.06 against 1.03 TIR points per
U/day). Both buy more than the uniform dial (0.78). Against the uniform dial, its t<70 cost per TIR point is half
(0.18 against 0.36), but C38's is lower still (0.12). Min 0.90 is a smaller C38, not a better one.

Against your replay (min 0.95 +0.44 / +0.05 / +0.01; min 0.90 +1.14 / +0.33 / +0.08), the generator gives 30–45% of
the TIR and 27–60% of the t<70 cost; the t<54 figures are too small at min 0.95 to compare. For C38 the generator gave
about 40% of the TIR and 20% of the lows.

## By tertile, min 0.90

| tertile | n | ΔTIR | Δt<70 | Δt<54 | ΔU/day |
|---|---|---|---|---|---|
| tight | 56 | +0.02 [−0.22, +0.25] | +0.07 [+0.01, +0.14] | +0.007 [−0.028, +0.043] | +0.39 |
| middle | 56 | +0.45 [+0.21, +0.68] | +0.09 [+0.03, +0.16] | +0.025 [−0.013, +0.066] | +0.62 |
| high | 54 | +1.11 [+0.85, +1.37] | +0.12 [+0.07, +0.16] | +0.049 [+0.018, +0.079] | +0.45 |

The tight tertile gains nothing and pays a little t<70. On gr, C38 does better there (TIR +0.29, t<70 +0.05). At min
0.95 every tertile figure is within noise of zero except high-tertile TIR, +0.34 [+0.15, +0.54].

## Engine check

gr re-run on 86e13c4c (`gr_e`) is identical to gr on d0fd0d0 on every donor and training: max |ΔTIR| 0.00. With the new
options off, the engine is unchanged on the generator too.
