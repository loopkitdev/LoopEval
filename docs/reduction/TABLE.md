# Surrogate comparison table

Bed: 35 pilot donors (`runs/2026-10-30-reduction-ec/subset36.csv`, i202 out: no clean pre-window days), last 28 days,
dr harness, deployed config, entries on, replay (ICE counterfactual). Reference = LoopAlgorithm with guard + runway
(`gr`), insulin-needs dial ×0.90–1.10. Δ = arm − gr, paired, donor-bootstrap 95 % CI. All surrogate inputs below
are learned from the 14 days before the window; the user sets nothing but the safety limits.

| Arm | Inputs | TIR | t<70 | t<54 | ΔTIR | Δt<70 | U/day | Failure mode |
|---|---|---|---|---|---|---|---|---|
| gr ×0.90 / ×1.00 / ×1.10 | full Loop input, all schedules | 62.8 / 70.0 / 73.1 | 0.89 / 1.77 / 4.19 | 0.15 / 0.41 / 0.90 | — | — | 47.2 | — |
| fixed TDD ×1.0 | G, 15-min slope, automatic IOB; TDD | 59.9 | 8.89 | 3.75 | −10.1 [−15.3, −5.0] | +7.1 [+4.1, +10.6] | 48.5 | scale wrong where needs moved (0.1–4.6× history) |
| adaptive scale, set point 140, + carbs | + entered carbs; scale integrates glucose error | 69.8 | 7.48 | 2.68 | −0.2 [−3.0, +2.7] | +5.7 [+4.2, +7.3] | 48.4 | IOB stacking on fast rises; no caps or gains move it |
| adaptive, set point 160 | same | 62.3 | 4.13 | 1.43 | −7.7 | +2.4 | 47.8 | 10.8 TIR below the dial at equal t<70 |
| background rate + RC ×1.0 | + RC on unexplained 30-min glucose change; background rate from history | 69.4 | 6.96 | 2.37 | −0.7 [−3.9, +2.6] | +5.2 [+3.1, +7.4] | 48.0 | same |
| background rate + RC ×0.9 | same | 65.3 | 4.73 | 1.49 | −4.7 | +3.0 | 47.5 | ~3× gr's t<70 at equal TIR |
| oracle TDD ×1.0 (diagnostic) | true in-window TDD (future data) | 58.6 | 4.45 | 1.46 | −11.4 | +2.7 | 47.5 | not the scale |

Replay places every surrogate above Loop's curve; the two simulators with a known answer place the best one below it.

## Across the three tools: background rate + RC, scale ×0.9

The same surrogate on each bed, against gr swept on insulin-needs. Gap = surrogate TIR minus the dial's TIR at the
surrogate's t<70 (or t<54); positive = more TIR at equal lows. 95 % donor-bootstrap CI.

| Bed | People × days | TIR / t<70 / t<54, gr ×1.0 | same, surrogate ×0.9 | Gap at equal t<70 | Gap at equal t<54 |
|---|---|---|---|---|---|
| Replay (tier A) | 35 × 28 | 70.0 / 1.77 / 0.41 | 65.3 / 4.73 / 1.49 | ~−12 | below |
| ICE generator, training 0 (tier B) | 163 × 28 | 68.1 / 2.16 / 0.54 | 71.4 / 2.65 / 0.71 | **+1.4 [+0.4, +2.3]** | +1.0 [−0.1, +2.2] |
| ICE generator, training 1 (tier B) | 163 × 28 | 68.8 / 1.80 / 0.38 | 71.6 / 1.99 / 0.44 | **+1.9 [+0.9, +2.9]** | +1.4 [+0.3, +2.5] |
| Additive sim (tier C) | 112 × 14 | 68.7 / 2.30 / — | 72.4 / 2.37 / 0.44 | **+3.4 [+2.2, +4.9]** | +2.4 [+1.5, +4.5] |

The generator runs hands-off (no meal entries, no user boluses); the replay and additive beds have entries on.
Failure mode on the generator: 12–15 of 163 people lose more than 5 TIR, all under-dosed (high mean, few lows) —
the TDD-rule correction factor is too weak for them. The person sets nothing but the safety limits.
