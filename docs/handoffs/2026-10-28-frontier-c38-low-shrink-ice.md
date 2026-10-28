# C38 with a reset on lows, on gr, on the ICE generator

From **ice** to **frontier**. Evidence: `runs/2026-10-25-ice-r2/`, arms `gr_c38e` / `gr_c38z05` / `gr_c38z0` in `r2_run.py`
(engine main ca5bbfc4), `snz_analyze.py`, `snz_scores_v32oc{0,1}TcB2FGUCGLBGGSKaLK.csv`. Setup as in
`2026-10-27-frontier-slow-rc-c38-ice.md`: the same 166 donors, windows, deployed config, retrained generator (oc) and
both trainings. C38 is `--candidate-slow-rc-tau-min 1440 --candidate-slow-rc-gain 0.05`; the arms add
`--candidate-slow-rc-low-shrink` 0.5 or 0.

## Verdict: all pass the guard; the reset is a gentler C38, not a better trade

| arm vs gr | ΔTIR | Δt<70 | Δt<54 | ΔU/day | t<70 per TIR point | t<54 per TIR point |
|---|---|---|---|---|---|---|
| C38 | +0.91 [+0.73, +1.10] | +0.11 [+0.07, +0.15] | +0.035 [+0.012, +0.058] | +0.88 | 0.12 | 0.04 |
| C38, shrink 0.5 | +0.75 [+0.58, +0.93] | +0.09 [+0.06, +0.13] | +0.021 [−0.002, +0.046] | +0.69 | 0.12 | 0.03 |
| C38, shrink 0 | +0.69 [+0.54, +0.85] | +0.10 [+0.07, +0.13] | +0.045 [+0.023, +0.068] | +0.65 | 0.14 | 0.07 |

CGM glucose, all time; paired against gr on the same engine, person bootstrap 90%, mean over two trainings. True glucose
on clean time agrees to within 0.09 TIR and 0.02 t<70. C38 rerun on ca5bbfc4 is identical to the earlier run on
d0fd0d0 on every donor and training (max |ΔTIR| 0.00).

Scaled lines are +0.118 and +0.098 (gr mean t<54 1.014 / 0.847). Per training, Δt<54 is +0.037 / +0.032 for C38,
+0.025 / +0.018 at shrink 0.5 and +0.055 / +0.035 at shrink 0.

Shrink 0.5 sits on C38's curve: the same t<70 per TIR point, a little less t<54, about 80% of the TIR and insulin.
Shrink 0 costs more lows per TIR point than C38, on t<54 most of all. As in your replay, the reset acts like a lower
gain; here a full reset is slightly worse, not equal.

## By tertile

| arm | tertile | n | ΔTIR | Δt<70 | Δt<54 | ΔU/day |
|---|---|---|---|---|---|---|
| C38 | tight | 56 | +0.29 [+0.10, +0.49] | +0.05 [−0.02, +0.11] | +0.012 [−0.027, +0.051] | +0.54 |
| C38 | middle | 56 | +0.62 [+0.34, +0.90] | +0.15 [+0.09, +0.22] | +0.071 [+0.030, +0.116] | +1.18 |
| C38 | high | 54 | +1.85 [+1.49, +2.21] | +0.13 [+0.07, +0.18] | +0.021 [−0.013, +0.051] | +0.94 |
| shrink 0.5 | tight | 56 | +0.12 [−0.10, +0.34] | +0.04 [−0.02, +0.11] | −0.009 [−0.048, +0.029] | +0.49 |
| shrink 0.5 | middle | 56 | +0.54 [+0.28, +0.81] | +0.11 [+0.05, +0.19] | +0.045 [−0.003, +0.102] | +0.90 |
| shrink 0.5 | high | 54 | +1.63 [+1.31, +1.96] | +0.12 [+0.07, +0.16] | +0.028 [−0.004, +0.059] | +0.68 |
| shrink 0 | tight | 56 | +0.19 [−0.01, +0.40] | +0.07 [+0.02, +0.12] | +0.033 [+0.003, +0.063] | +0.39 |
| shrink 0 | middle | 56 | +0.50 [+0.27, +0.73] | +0.12 [+0.06, +0.18] | +0.077 [+0.031, +0.126] | +0.84 |
| shrink 0 | high | 54 | +1.41 [+1.13, +1.72] | +0.10 [+0.06, +0.14] | +0.024 [−0.008, +0.055] | +0.72 |

The full reset does not protect the tight tertile: it gets less insulin than under plain C38 (+0.39 against +0.54
U/day) yet more t<70 and t<54. On the integral ISF-only form the same reset left the tight tertile within noise
(`2026-10-27-frontier-needs-slow-rc-ice.md`), so the reset is clean with that form but does not clean up C38 (the integral form without the reset at that gain was not run).

## Against your replay

Replay vs gr: C38 +1.94 / +0.71 / +0.22, shrink 0.5 +1.54 / +0.44 / +0.12, shrink 0 +1.31 / +0.35 / +0.09. The
generator gives 47–53% of the TIR, 15–27% of the t<70 cost and 16–50% of the t<54 cost. In replay the reset lowers
lows faster than TIR; on the generator shrink 0.5 does slightly and shrink 0 does not.
