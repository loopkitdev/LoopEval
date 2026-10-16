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

11. **LoopEval's trace delivery stream is consistent — the gap I once blamed on it was my plant.** Each step
    LoopEval sends ONE basal segment whose volume includes that step's auto-bolus; the trace splits it back
    into `basal` + automatic `bolus` records, so trace basal + trace auto = what the plant receives, exactly
    (2026-10-15 reconciliation: 8.5 + 29.5 = 38.0 U; manual 36.65 = 36.65). An earlier reading — "the trace
    double-counts auto-boluses" — was wrong: that discrepancy was the plant dropping late doses (lesson 19).
    Reconcile at the boundary before explaining a difference.

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

15. **Calibrate the ISF that is measured: effective, at operating glucose, on the full body.** The
    yardstick ISF comes from closed-loop data at the person's operating glucose, so it already contains
    glucose effectiveness and renal loss. Calibrating it onto the linear part at rest made the full
    body ~30% less responsive than Loop believed at 150–250 mg/dL (a unit delivered ~37 instead of 53);
    Loop forecast eventual BG at target with 4–7 U on board and under-dosed, and every cohort settled
    near a mean of 200 with ~11 U/day of disposal done by glucose effectiveness and the kidneys instead
    of insulin. The probe now raises both arms to ~180 with the same fast carbs and boluses one.

16. **Eating comes in pulses, not three big meals.** With every disturbance off and a perfect announcer
    (every meal entered exactly, bolused immediately), Loop still ran a mean of 197: an 80 g dinner
    sent glucose from 154 to an hourly mean of 358 while its 15 U bolus was still rising. Donors' eating
    arrives as ~5.6 pulses/day of median 26 g-eq (ice meals tables; a second rise in 22–26% of meals),
    so each person's carbs are now spread over their own measured pulse count with their own measured
    size spread, main meals no larger on average than any other event. Diagnostic switches that made
    this findable: `--disable` every disturbance and `--enable perfect_person`.

17. **Read a measured ratio in the units it was measured in.** ice's "pulse g-eq per entered gram 1.30"
    uses g-eq = ISF_tdd/(500/TDD) mg/dL (settings-free, ice_gen/meals.py), ~3.6 mg/dL/g at TDD 40.
    I applied it to the settings' ISF/CR (~4.9), overstating carb sensitivity by ~1.36×. The donor
    post-meal response exposed it: isolated bolused meals rise a median 17 mg/dL per 10 g entered
    (72 mg/dL, peak at 111 min, +36 at 3 h; 6,484 meals, 53 donors, meal_response.py) against the
    simulator's 34. Two lessons: check the definition behind every borrowed number, and measure the
    behavior that integrates the components (here, glucose after a bolused meal) directly.

Also (no lesson of its own): the candidate now runs as deployed Loop-main (`--no-mid-absorption-isf
--no-gradual-transitions-gate --legacy-rc-decay`, docs/loop-algo-classes.md); it changed no cohort
statistic here, but it is the controller donors ran.

18. **Every carbohydrate path must share the calibrated per-gram sensitivity.** Meal bioavailability is
    calibrated per person (f from the observed carb sensitivity, compensating a small glucose space),
    but rescue, proactive and exercise snacks were fixed at f = 1.0: on a 50-kg body with VG 1.52, one
    gram of rescue glucose raised 13 mg/dL (a 28 g rescue ≈ +370) against 3.95 per meal gram and 3–4 in
    Brodows 1984. Every defensive snack became a spike; even people dosed exactly to their own truth
    with no disturbances ran means of 158–185. Fast glucose now uses the person's f × 1.25. The test
    that caught it — truth settings, perfect person, every disturbance off, internal drive — should run
    for every new physiology or behavior path: a body dosed to its own truth must sit near its rest level.

19. **The plant dropped every bolus LoopEval sent — reconcile what crosses the boundary FIRST.** Between
    requests the world's clock sits one minute past the last t1, so each new dose (starting at t0) was
    already "in the past": the pump discarded boluses outright (start = end) and the first minute of
    every 5-min basal segment. One person received 94.6 U and delivered 46.7. Every cohort from c1 to c11
    ran with roughly half the insulin Loop gave, which explains why no behavior or physiology change
    moved the level (mean ~185, TDD ~25 vs 40) — and some of the "fixes" in lessons 13–17 were chasing
    this. A late dose is now delivered from the current minute, full volume and duration; the validation
    reports delivered/received per person. Rule: before reading any cohort statistic, reconcile the
    insulin that crosses each interface (controller → plant → pump → depot → plasma).

20. **For an AID simulator, the insulin action that matters is the one Loop's forecast is right about.**
    The clamp-fitted action (lesson 9; 0.2 U/kg doses) delivers ~4% of a bolus's effect in its first hour
    against Loop's 17%. After every bolused meal Loop then saw glucose climb faster than it forecast,
    added insulin (net +0.1 U per 10 g in the first 90 min, where donors' Loop net-REDUCES by 0.25), and
    the stack landed late: simulated meals peaked at 56 min and ended 25 below baseline at 3 h (donors:
    111 min, +36). The field evidence outranks the clamp for this purpose: replay found Loop's forecasts
    match real glucose closely in the first hour, with only a small insulin-tail residual (−3.5 mg/dL
    over 6 h), and meal boluses (2–5 U) absorb faster than 0.2 U/kg clamp doses. Action now tracks
    Loop's adult curve (13/51/77/91/99% at 1/2/3/4/6 h vs Loop's 17/50/76/91/100) with the PK unchanged.
    Check found by comparing insulin delivered around bolused meals, donors vs simulation, same windows.

21. **The protocol's order of operations is part of the plant.** At a decision where a plant bolus
    lands, LoopEval decides the automatic dose without it; an auto-bolus user then got 0.4 × the meal's
    need from Loop plus the full calculator bolus — ~1.4× every announced meal, then an hour of zero
    temps and a low. Found by comparing insulin around bolused meals with donors (1.30 vs 0.84 U per
    10 g) after ruling out the bolus itself (1.02 vs 1.01 of CR) — and only after the meal response had
    resisted two "physiology" explanations (absorption speed, insulin action). Workaround: the plant
    asks for ratio − AF. Engine fix proposed (docs/handoffs/2026-10-15-simulator-plant-bolus-autodose.md).

22. **Measure simulated and real with the same event definition, not just the same formula.** Donor
    meal responses were timed from the ice labeler's pulse onset; simulated ones from the true eating
    time. The labeler's onset lags eating by ~30 min, so the comparison read 53 vs 111 min to peak and
    −24 vs +36 at 3 h — and three model changes (absorption speed, insulin action, auto-dose stacking)
    "failed" to move it. Run through the labeler (ice_check.py → meal_response.simulated_labeled), the
    simulated meals read 50 mg/dL rise, 85 min, −4.5 at 3 h against 72, 111, +36: a smaller, real gap.

23. **Light activity must not build the post-exercise sensitivity state.** Ablations on the same 30
    people (runs/lo_*): switching exercise off brought t<70 3.66 → 1.78 (donors 1.66), t<54 0.72 → 0.29
    (0.23), lows/day 1.89 → 1.31 (1.08), minutes per low 25 → 20 (20) and the mean to 153 (151). Every
    walking bout fed the delayed state Z (glycogen repletion), so four walks a day held sensitivity ~20%
    high around the clock. The ETH model drives Z through a sigmoid of intensity; Z now builds only
    above moderate intensity (0.35). Light activity keeps its acute uptake and sensitivity effects.
