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

Verdict so far (replay only): no surrogate reaches the needs-dial curve; all fail the t<54 guard. Untested: whether
replay is biased against controllers whose timing departs from the field (next: additive sim, ICE generator).
