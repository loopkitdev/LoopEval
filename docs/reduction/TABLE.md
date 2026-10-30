# Surrogate comparison table

Bed: 35 pilot donors (`runs/2026-10-30-reduction-ec/subset36.csv`, i202 out), last 28 days, dr harness, deployed
config, entries on. Reference = LoopAlgorithm with guard + runway (`gr`), needs dial ×0.90–1.10. Δ = arm − gr,
paired, donor-bootstrap 95 % CI. "TIR @ t<70" = TIR gap to the needs-dial curve at the arm's t<70.

| Arm | Inputs (user-set) | Form | TIR | t<70 | t<54 | ΔTIR | Δt<70 | TIR @ t<70 | U/day | Failure mode |
|---|---|---|---|---|---|---|---|---|---|---|
| gr | full Loop input (all schedules) | LoopAlgorithm + guard/runway | 70.0 | 1.77 | 0.41 | — | — | 0 | 47.2 | — |
| tdd_pd ×1.0 | G, slope15, auto IOB; TDD (none) | predictive correction, TDD scales | 59.9 | 8.89 | 3.75 | −10.1 | +7.1 | below curve | 48.5 | fixed scale vs moving needs; late insulin |
| tdd_pd + carbs | + entered carbs | + COB at TDD carb ratio | 54.7 | 3.70 | 1.22 | −15.3 | +1.9 | −18.1 | 47.2 | same |
