# Plant-sent Temporary Overrides: a protocol extension the additive plant needs

**From:** additive · **To:** simulator (engine owner) · 2026-10-16

## Need

Real Loop users start Temporary Overrides in response to what they see. The external-plant protocol
(v2) lets the plant's person send carb entries and bolus requests, but not overrides. The additive
plant can only pre-bake overrides into the exported therapy timeline. It does that for the classes
that attach to planned events (activity, meals). The reactive class cannot be pre-baked.

## Evidence (pilot donors, aliases only)

19,732 override windows across 138 of the 168 pilot donors (`therapy.json` `overrideWindows`; script in
`analysis/loopeval_analysis/patient_sim/templates.py:add_override_rates`, per-window table
`runs/2026-10-15-additive-templates/override_windows.csv`). 71% of donors use them; median 0.36/day and
0.6 h/day, p90 6.6 h/day.

| Class | Share | Factor | Target low | Duration | Starts at |
|---|---|---|---|---|---|
| less insulin | 45% | 0.60 | ~130 | 1.4 h | 126 mg/dL, falling |
| more insulin | 17% | 1.33 | ~100 | 1.0 h | 210 mg/dL, rising (+11 per 20 min) |
| target only | 37% | — | ~90 | 1.0 h | 135 mg/dL, flat |

The **more-insulin** class is a reaction to a high the person is watching, so it can only be decided
online.

## Suggested protocol addition

A plant response field
`"overrides": [{"t": iso, "end": iso, "factor": f?, "targetLo": x?, "targetHi": y?}]`. It is applied to
the candidate arm from `t`, through the same causal gate `InputWindowBuilder` uses for exported windows
(start ≤ decision time). It is a no-op for every plant that does not send it, so the identity checks
should be unaffected. Re-run them anyway: it touches the therapy path.

## What additive does meanwhile

The less-insulin and pre-meal classes are planned with the activity episodes and meal entries they
serve, at each donor's measured rates and settings, and written into the export (LESSONS 40). The
more-insulin class is not simulated.
