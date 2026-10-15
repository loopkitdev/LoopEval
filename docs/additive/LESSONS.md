# Lessons — additive role

Things that cost time or would have produced a wrong simulator. Newest last.

1. **No mystery terms** (Pete, 2026-10-15). A variability or offset term may exist only if its size
   comes from its own controlled-condition evidence. Free-living variability (closed-loop TDD CV 17%,
   overnight 31%; Ruan 2016) is a TARGET the named factors must jointly reproduce, never an input. When
   a simulated statistic misses, re-check a named component or find the missing one. Intrinsic terms
   that pass the bar (evidence/07): day-level SI CV ~8% (repeat clamps), per-dose absorption jitter ~15%
   (Heise 2017). Visentin 2015's N(1, 0.2) circadian noise is SI estimation precision, not biology.

2. **A minimal model's X·G insulin action is also a glucose-effectiveness term.** At basal insulin it
   clears glucose at SI·Ib per minute. Calibrating SI to a person's ISF on top of that gave 0.01–0.08
   /min of extra glucose effectiveness, which flattened every meal (carb sensitivity 0.7–3 mg/dL/g
   against the ~5 people's settings imply) and fed back into the calibration (the probe's drop
   saturates, so SI ran away 11× for slow absorbers). Fix: the glucose-dependence of insulin-mediated
   uptake is its own parameter κ (κ = 1 Bergman, 0 Loop-linear), and ISF and CSF are DEFINED on the
   linear part (glucose effectiveness, hypo risk term, counter-regulation off) — the same bookkeeping
   ISF the eda yardstick estimates.

3. **ReplayBG's identified SG (median 0.022 /min) is not a population glucose effectiveness.** It
   makes every perturbation fade in ~45 min, which contradicts flat basal tests and the weak closed-loop
   restoring force eda measured. UVA/Padova-plant impulse fits give 0.0013–0.0047. Identification in
   closed-loop free-living data loads unmodelled dynamics into whatever damping term exists.

4. **The measured fasting insulin rate is not the true basal.** Taking it as truth left people with
   TDD − 24·basal ≈ 0 and diets of ~30 g/day. Fasting periods carry unannounced eating and meal tails
   (ice: 4.2 unannounced pulses/day). True basal now follows from TDD − carbs/CR_true, carbs from the
   person's own entries (regular announcers) or the literature distribution; the fasting rate is kept
   as a validation quantity.

5. **LoopEval's first plant request time depends on the data** (16 h on one person, 22 h on another),
   not only on the warm-up and burn-in defaults. Export a generous burn-in history (30 h) and have the
   plant refuse to start past it, rather than predicting the time.

6. **A bolus's own depot must not be garbage-collected before its delayed dose arrives.** Boluses
   silently did nothing for the first test because the depot list dropped empty depots while the
   dose was still in the delivery delay line. Test every new physiology path against a control body
   (identical except the input), never against an assumed rest level — the delay line also starts
   empty unless primed, which looked like a formulation difference.
