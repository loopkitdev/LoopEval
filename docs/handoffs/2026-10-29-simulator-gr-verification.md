# Guard + runway verification: three gaps in what LoopEval can show

From **review** to **simulator** · 2026-10-29. Board: TIDEPOOL-104 (review of guard + runway, now in LoopAlgorithm
main e3f5e3c and on its way to Loop next-dev). Evidence: `runs/2026-10-29-review-gr/` (`xcheck/`, `fidelity/`, `i058/`).

Guard + runway holds up on the ICE generator: against stock, TIR +0.58 [+0.26, +0.93] and t<70 −0.31 [−0.39, −0.24],
in both trainings and every tertile. What LoopEval cannot yet show is that the replay underneath is faithful, and that
the shipped code is the code that was scored. Three asks, in order of importance.

## 1. Replay forecasts on the pilot beds fail verification.md step 1 in the worst case

Six pilot donors (i001, i040, i091, i071, i065, i058) × 3 days, `simulate --decision-time-replay --export-forecast-curve`
at deployed config, on main 7c3eae3a:
- class-1 flags;
- IRC + clamp for i058, temp strategy for i040, i001's time-based AF and increments;
- `--no-clip-in-progress-temp-basal`.

Compared against the field's `reason='loop'` `bgForecast`, using the max point delta over the whole forecast (t0
excluded), on IOB-aligned cycles (|ΔIOB| ≤ 0.1 U): 2,809 of 3,766 cycles.

| donor | median | share > 5 mg/dL | p99 | worst |
|---|---|---|---|---|
| i001 | 0.58 | 12 % | 38.9 | 61.2 |
| i040 | 2.38 | 20 % | 28.6 | 68.8 |
| i058 | 0.82 | 8 % | 37.8 | 56.2 |
| i065 | 0.61 | 11 % | 37.3 | 73.8 |
| i071 | 0.99 | 9 % | 15.6 | 30.7 |
| i091 | 1.34 | 10 % | 17.4 | 25.7 |

- Starting glucose agrees on 99.3 % of cycles, and only 6 % of the cycles off by more than 5 mg/dL start from a
  different value. So the residual is in the glucose history behind momentum and RC, or in the insulin inputs.
- Carbs don't explain it: cycles with COB = 0 fail as often.
- Example: i001 2026-09-19 08:36. t0 is 87 on both sides, but our momentum is +57 against a falling field forecast.
- Ours also floors nothing below zero, where Loop floors its forecast at 0 (the i058 compression low, RC −149). That is
  representation only, and the comparison floors it.

Under verification.md each of these is a real discrepancy until proven to be one of the three exclusions. A related
gap: the pilot exports have no `replay_config.json`, so `simulate`'s provenance guard cannot warn on them.

Script: `fidelity/compare.py`. Field forecasts: `fidelity/field_dd.pkl`, a bounded pull of 6 users × 3 days.

## 2. Export the exact algorithm input behind each DTR cycle

Running LoopAlgorithm main on the same cycles needed `dump-inputs` plus a converter (`xcheck/convert.py`). That
rebuilds a different stock input from the one DTR scores: package-std and LoopEval-baseline agree on only 11–28 % of
cycles, with eventual BG a median 1.4–2.3 mg/dL apart.

An `AlgorithmInputFixture` written per DTR cycle would let the shipped package run on exactly what was scored. Every
residual would then have to be 0 (stock) or explained (gr).

Today's state:
- The constants and formulas match.
- The gr effect on eventual BG agrees (p99 0.02 mg/dL).
- On the 679 cycles where stock does agree, 9 gr doses differ by more than 0.05 U. One is explained: floating-point
  COB of 1.9e-15 closes the package's carb gates.

## 3. Add a guard + runway case to `scripts/golden.py`

The suite has no gr case, so a change that moves gr alone would pass `check`. The frozen flags are those of
`runs/2026-10-23-frontier-dosing/dr/run.py` `arm_flags("gr")`, with k = min(1, 6.7 / σ5 median).
