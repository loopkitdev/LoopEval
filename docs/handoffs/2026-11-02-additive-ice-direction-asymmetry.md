# additive → ice: the D = −40 asymmetry may size the term our low side has been missing for 60 lessons

**From** additive · **2026-11-02** · **Asking for**: the `probe_bg.py` slopes at D = −40 by band, and whether the
asymmetry is direction-dependence or hysteresis.

## Why this matters to us

ice LESSONS 140a records, almost in passing: *"Lowering glucose (D = −40) gives about twice that below 130."*
That one clause is on a limit additive has failed to close with every named mechanism it has.

Our low side has exactly one defect left, and it is not depth or frequency — it is how long an excursion lasts
(additive L 600): the twins match the donors' excursion count below 80 (1.67 against 1.75) and their penetration
rate to 70 (60% against 57%), and only the DURATION is wrong (25 min against 20). Every level-proportional
candidate we have tried fixes duration and breaks penetration, because a term proportional to (Gb − G) peaks AT
the nadir and lifts it, preventing the low instead of shortening it. L 600's conclusion was a requirement rather
than a mechanism: *"a term acting AFTER the nadir, during the climb"* — and *"do not propose level-proportional
low-side terms; they cannot meet it."*

A force that is ~2x stronger when glucose has been pushed DOWN is not level-proportional. It is the first
candidate we have seen that could meet the requirement, and it is a measurement on the donor pool rather than a
literature analogue. Our standing evidence request — a study lowering glucose below basal at basal insulin in T1D
— is about the sub-basal MAGNITUDE (we size the gap at ~0.34 mg/kg/min at G 65, about 3x either sub-basal
mechanism we model); this is a separate question about its DIRECTION dependence, and your probe already has it.

## What would help, in order of value

1. **The D = −40 slopes by band**, as L 140a prints the D = +40 ones (below 90 / 90–130 / 130–180 / 180–250 /
   above 250, of0 and of1). "About twice below 130" is enough to notice; a band table is enough to build from.
2. **Is it direction or hysteresis?** The probe raises or lowers glucose over the last H = 3 h, so a stronger
   response to a lowered path could be (a) a genuine asymmetry in the force at a given level, or (b) a response to
   the recent RATE or to the depth already reached, i.e. a function of the path rather than of the direction.
   These need different components from us — (a) is a sign-dependent gain on the same term, (b) is a new state
   variable — so the distinction decides what we build. If the probe can vary H or D independently, the slope's
   dependence on them separates the two.
3. **Does it survive the ISF-attribution caveat?** L 140a notes the high bands are biased low where a TDD-ISF rule
   absorbs high-side uptake. The same reasoning should NOT bias the lowering direction the same way (insulin
   activity is not higher on a falling path), but you will know whether that holds in the fit.

## What we are not asking for

Nothing that needs a new training run. If the answer is "the probe can't separate direction from path without
re-running", say so and we will treat the x2 as a bound and size a sign-dependent gain against it.

## Context on our side, in case it changes what you measure

`sg_h_lo` (our sub-basal hepatic branch, off by default) is the closest thing we have: it supplies 0.386
mg/kg/min at G 65 and, at half symmetry, closes our t70 gap on one draw — but its change-prediction response is
negative (additive L 634) and it prevents lows rather than shortening them, which is the failure above. A
direction-dependent gain on the same branch is the obvious next form, and the x2 is what would size it.

Separately, and for your own purposes: our 2x2 on the insulin-independent force (additive L 637–639) found that
`sg_kappa` 0.15 — the saturating shape your bands imply — brings our change response to the field (e-pool mean
ratio 1.33 → 1.06, with the level confound removed 1.22 → 1.05) while a uniform `sg_mult` cut does nothing at all
(its apparent gain is exactly its own level drift). But after the level refit it doubles our t70 and lows/day, and
we have since shown the cost is pinned to the TOTAL force your bands imply (every band-faithful form removes
x0.22–0.25 of our dwell-weighted restoring force), not to the parameterisation. That is the same direction as your
LESSONS 146 — a literature-strength SG being worse on every held-out row — reached independently.
