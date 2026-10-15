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

7. **Uptake must vanish with glucose, and HAAF must not act within the episode it is measured in.**
   The first closed-loop cohort pinned true glucose at the 10 mg/dL floor for hours in half the people
   with delivery at zero. Two terms made a stable hypoglycaemic equilibrium: κ-form insulin-mediated
   uptake kept ~85% of its basal value at 10 mg/dL (fixed: proportional to G below Gb, as Bergman and
   UVA's Michaelis–Menten do), and the S2013 risk multiplier (×3.6 frozen below 60) on top. HAAF had
   been draining counter-regulation within the same low; it now builds slowly (2 h below 54 → ×0.6).
   λ_risk is provisional 0.5 until its joint calibration with counter-regulation on donor low anatomy.

8. **People's ISF/CR settings are not physical carb sensitivities, and neither settings nor the
   yardstick is the truth — TDD is the measured constraint.** Settings imply a carb sensitivity of
   median 4.9 mg/dL/g; a body with the literature distribution volume gives ~6.5 for an adult and
   ~28 for an 18-kg child. Taking settings as physics produced impossible bodies; taking the yardstick
   ISF as truth turned its estimation noise into 2× settings errors and crashes. The truth is now:
   ISF = settings moved halfway (log) toward the yardstick (weight open); body weight blends the age
   prior with TDD at an age-banded U/kg; carb sensitivity from the body; true basal = a share of TDD;
   carbs eaten = what the rest of TDD covers at the true CR. The donor's own outcomes then become a
   per-person (twin) validation target.

9. **ReplayBG's prior medians make insulin act far slower than a clamp says.** On the linear part, the
   chain kd 0.030 / ka2 0.0137 / p2 0.0121 / p2e 0.008 delivered 47% of a bolus's effect by 3 h and
   88% by 6 h, against Loop's 76% / 100% and the lispro clamp's GIR peak at 90–120 min. Loop then reads
   the missing drop as resistance (retrospective correction adds insulin) and the stacked insulin
   lands later — a low-generating mismatch far larger than the field shows. The earlier probe hid it
   because it was normalised to the PEAK drop while glucose effectiveness eroded the tail: always
   compare the cumulative effect on the linear part. Refit (grid) to GIR peak ~100 min, 50% by ~140,
   90% by ~270: ka2 0.018, p2 0.025, p2e 0.012 (plasma tmax 51 min, inside the 40–60 literature).

10. **Ablate before tuning: the S2013 hypo-risk term was nearly all of the excess lows.** Four runs on
    the same 42 people (2026-10-15, runs/a_*): removing the risk term took t<54 8.5% → 0.27% (field
    median 0.13%), t<70 15.5 → 2.5 (field 1.4), TIR 48.8 → 64.9 (field 67), rescue carbs 166 → 55 g/day.
    Telling Loop the truth (settings = truth) changed nothing; switching the circadian profile off
    moved t<54 8.5 → 6.2 and the 24-h amplitude 0.23 → 0.08 against the field's 0.12. The risk term
    stays in the code at λ = 0; Visentin's swing is halved. Both remain open to the joint low-anatomy
    and circadian-amplitude calibration — as named parameters, not as new terms.

11. **Read delivered insulin from the plant, never by summing the trace's delivery stream.** The trace
    lists each auto-bolus as its own record AND folds it into that step's basal segment, so the sum
    double-counts automatic boluses (i114: trace 67 U/day vs 45 U the plant received and absorbed).
    That mis-read looked like a 30–60% site loss for an hour. The plant's log is the truth.

12. **A projected-glucose trigger alone makes a runaway snacker.** Proactive snacking keyed only to
    CGM + 30·trend − ISF·IOB fired at 220 mg/dL whenever Loop's IOB was large: snacks → highs → more
    IOB → more snacks (one person: 48 g/day of meals, 106 g/day of "defense"). The measured defense
    state is near the low band and not rising (ice L34/L69); the trigger now requires both.

13. **"Corrections" in the donor record are partly food dosed by hand.** Simulated people received
    ~11 U/day less insulin than their donors and ran ~45 mg/dL higher; the gap was manual insulin
    (donors 12.9 U/day by hand, simulated 7.5) with carb entries matched. The pilot's lone boluses
    have a median of 1.85 U at a median glucose of 163, 22% below 140, and often exceed Loop's
    recommendation (mean ratio 1.95): food bolused without a carb entry (Groat 2017: carbs entered
    for 2/3 of boluses). That is now its own named behavior (`free_bolus`: own grams estimate over own
    CR), split from true corrections per donor (`templates._free`).

14. **Physics carb sensitivity overshoots donors by ~1.7×: bioavailability per LABELED gram is a person
    parameter.** f·1000/(BW·VG) with Dalla Man's f 0.9 (a tracer-glucose figure) gave a 55-kg adult
    9.5 mg/dL/g; her settings imply 4.4. A 76 g meal took her from 265 to 601 mg/dL in 90 min under a
    calculator bolus that covered less than half the body's need — every meal overwhelmed Loop, which
    then held 4–7 U of IOB it could not use fast enough. Donors' meal pulses run 1.30× what entered grams
    predict at the settings' carb sensitivity (ice L54), so CSF = 1.30 × settings CSF (sd 0.15) and the
    body's f follows (0.3–1.0). Labeled carbohydrate is not all glucose appearance.
