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
    Its outcome effect is small: Loop takes most of the extra back on later cycles (ice measured no change
    beyond noise on 24 donors; ice LESSONS 99). Count it as a correctness fix, not an outcome lever.

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

24. **Calibrate the sensor where the sensor dominates: quiet windows, same family, same code.** In stretches
    with no labeled eating or manual bolus for 4 h, pilot G7 donors show a step SD of 5.5 with positive
    step autocorrelation out to 20 min (0.48 / 0.21 / 0.15 / 0.14) and kurtosis 6.2; the simulator with the
    G6-derived noise gave 4.0 and a G7 smoother than its G6 — the reverse of eda's switchers. A grid
    (runs/sg_*) fixed the size (G7 σ 4.0) and showed the Vettoretti AR(2) shape is right (a less
    oscillatory shape took lag-5 autocorrelation 0.45 → 0.09). Larger noise does NOT supply the heavy
    tail or the 15–20 min persistence — it lightens the tail and adds false lows. Those need rare,
    large, persistent events (compression lows at their true rate; other named disturbances).

25. **Reconcile at the boundary after every engine change, not just once.** main 8e86860 (plant bolus
    decided before the automatic dose, dated t − 1 s) passed its own checks, but the earlier date fell
    outside LoopEval's forwarding window (doses dated ≥ the previous step's end), so the plant received
    0 of 44.8 U of person boluses while Loop's IOB counted all of them. The cohort swung to mean 179,
    TDD 31 and looked like a physiology result. Caught by the plant's received-dose log (lesson 19's
    reconciliation) and a two-binary A/B on one person (identical without --plant-behavior). Reported to
    simulator, fixed in main f11386e (doses forwarded by insertion). On f11386e with no workaround (cohort
    c20) the cohort matches the workaround run within noise (mean 148 vs 148, TDD 41.3 vs 40.9, t<54 0.38
    vs 0.47) and delivered/received is 0.94–1.04 per person. Cohort c19 void.

26. **Size a behavior's rate by the donor's exposure, not by a guessed opportunity count.** Corrections
    were a per-glance probability (measured rate ÷ 4 glances): simulated people corrected 0.20 a day
    against their donors' 0.95. Few glances land on a qualifying high. Corrections are now a per-minute
    hazard while awake and above the person's correction level, sized so the donor's measured rate is
    reached over the donor's own time above 180. User boluses per day: 2.82 → 2.86 median, KS p 0.11 →
    0.77 (cohort c21); free (food) boluses already matched (0.47 vs 0.41, Spearman 0.93).

27. **Calibrate a measured ratio through the measuring pipeline, not around it.** Carb sensitivity was
    set so the body's PRE-erosion pulse matched ice's 1.30 g-eq per entered gram; ice's labeler run on
    simulated people (ice_check.py) read 0.91 against 1.21 on pilot donors — glucose effectiveness erodes
    the pulse before ICE sees it. Meals then rose ~10 mg/dL per 10 g entered against the donors' 17. The
    constant is now set by the labeler (1.73). Grids that did not help, kept for the record: a slow
    gastric-emptying tail (runs/ms_*: lowers the rise, leaves the 3-h change at −4; off by default) and
    ISF_W (runs/iw_*: twin TIR rank 0.15 / 0.17 / 0.07 at 0 / 0.5 / 1; stays 0.5). Real per-person TIR is
    carried by something not yet individualized. Result (cohort c22): 16 of 42
    statistics match the pilot donors (KS p > 0.05), every outcome statistic among them (mean 153 vs 151,
    TIR 74.7 vs 71.7, t<70 1.50 vs 1.66, t<54 0.30 vs 0.23, lows/day 1.02 vs 1.08, TDD 37.8 vs 37.0);
    labeled meals rise 58 (72), peak 95 min (111), +11 at 3 h (+36). What still fails is the shape of the
    signal: heavy tail, volatility switching, short-lag smoothness, long-range persistence.

28. **The quiet-window tail is mostly real glucose movement, not sensor glitches.** Donor quiet stretches
    (no labeled eating or bolus for 4 h) hold 54 steps of ≥ 12 mg/dL per 1,000 (G7); only 6% are
    up-then-down spikes, 45% persist for several readings, and they go up as often as down. A Gaussian
    with the donors' quiet step SD would give ~29. Heavy-tailed sensor innovations (Student-t; Breton &
    Kovatchev 2008 use Johnson S_U) fix the SHAPE — df 4 matches whole-record kurtosis (2.39 vs 2.48) —
    but not the RATE of big moves (22 vs 54 per 1,000) nor the quiet step SD (4.6 vs 5.5). The missing
    piece is frequent, sustained, symmetric glucose movement in unlogged time: more and stronger
    activity, intake below the labeler's 12 g-eq gate, or a latent state not yet named. Full cohort with df 4 (c23):
    20 of 42 statistics match the pilot donors, up from 16 — step kurtosis, CV, 24-h amplitude, insulin
    burstiness and day-to-day insulin CV join the outcomes.

29. **Sensor noise must shrink at low glucose, or a realistic noise level manufactures lows.** Donors'
    quiet windows hold fast excursions (≥ 12 mg/dL in 5 min, ±28 over ~15 min) at 0.35–0.61 per quiet
    hour, at night as much as by day — sensor, not activity. Constant-σ noise big enough to reproduce them
    (σ 4.5–5.0) pushed t<70 to 2.2–2.4% (donors 1.66). The G7 accuracy tables say absolute error is
    ~8.5 mg/dL at 40–60, ~11.6 near 130, ~17 near 240; scaling the noise by 0.6 + 0.4·IG/130 at σ 4.5
    gives night excursions 0.38 (0.35), quiet step SD 5.23 (5.48), t<70 1.62 (1.66), t<54 0.27 (0.23),
    TIR 72.2 (71.7), kurtosis 2.36 (2.48) — grid runs/nh_*, runs/ns_*.

30. **Look at the worst person-days, not the averages: a few multi-day excursions were half the
    between-day spread.** Simulated daily means showed a dip shared across people (days 8–9, t −3.5 and
    −4.8), and between-day variance was 0.24 of the total against the donors' 0.10. The shared "dip" was
    an artifact of centering each person on a mean that two outliers had dragged down: true glucose
    held at 500–1000 mg/dL for 10–30 h. There were two causes.
    - A dislodged site was noticed only on reporting minutes. The 1/180 per-minute hazard became 1/900,
      so the site went unnoticed for ~15 waking hours while the CGM read 401.
    - Eating events were renormalised to each day's actual count, which coupled the Poisson snack count
      into meal size. Simulated p99.9 was 246 g against the donors' 156 g-eq pulses; one meal was
      297 g, unannounced.
    After both fixes (cohort c25), between-day fraction is 0.118 (donors 0.105) and day-to-day TDD CV
    is 16.6 (17.0). Skew did not move (1.32 vs 0.89). The donors' log-glucose is symmetric (median
    log-skew 0.01: glucose is lognormal); the simulator's is 0.17, with a body slightly too low (median
    137 vs 142) and a top tail too long (p99 335 vs 317). The excess lives in the true glucose (Box-Cox
    −0.28), not in the sensor.
    Two side results:
    - The fingerstick records in the Tidepool pull are 98.7% mirrored CGM values. The 346 real sticks
      (70 donors) cannot calibrate sensor bias.
    - CGM second differences grow with glucose level about as fast in the simulator as in donors (sd
      4.2 → 7.9 from 90 to 350 mg/dL). Fully proportional (log-scale) sensor noise would give ~16 at
      350, so the sensor's fast noise is not proportional to glucose.

31. **Fit the sensor to sensor-only targets, or it absorbs whatever the physiology is missing.**
    The G7 noise had been sized to donors' 5-min roughness (lesson 29), but that roughness includes real
    glucose movement. Run against the FDA iCGM tables (sensor_check.py, sensor_fit.py: two independent
    sensors over the same simulated true glucose, daytime, 15-min pairs), the simulated G7 was far less
    accurate than the real one:
    - MARD 22 / 17 / 10.6% at <54 / 54–69 / 70–180, against 14 / 10.7 / 8.6;
    - two-sensor PARD 14%, against 8.9;
    - bias −14.6 above 250, against −6.6.
    The noise σ hardly mattered: halving it moved the low-end MARD by less than one point. The
    per-session calibration did matter: the G6 offset N(6.35, 6) and gain sd 0.063 (Vettoretti 2019).
    The fitted G7 has:
    - innovation σ 2.5 with an additive floor ⊕ proportional scale;
    - gain N(0.98, 0.04) and offset N(3, 3);
    - an error COMMON to co-located sensors (Biagi 2017 AR(3), σ 2.0), which raises accuracy error
      without raising precision error, as the FDA tables require.
    It gives bias 3.8 / 2.7 / 1.2 / −1.5 / −6.8, MARD 13.7 / 10.9 / 7.9 / 6.9 / 6.8, PARD 8.9 and MAD
    elasticity 0.66 (FDA 0.69). The whole-record step SD barely moved (7.7 → 7.3). On scaling: total
    sensor error grows with glucose at about the 0.7 power, between additive (0) and lognormal (1). Most
    of the proportional part is the calibration gain; the fast noise keeps an additive floor (evidence/08).

32. **Donors' excess big CGM steps are transient sensor biases that recover, not catch-ups.** Quiet-window
    jumps ≥ 12 mg/dL, classified by what surrounds them (quiet.jump_signature), per 1,000 steps:

    | | Reversal | Catch-up | Step | Lead-in |
    |---|---|---|---|---|
    | Donors, G7 | 6.8 | 2.2 | 2.2 | 11.6 |
    | Simulator, fitted G7 | 1.6 | 2.4 | 1.3 | 8.1 |

    A reversal is undone within 15 min. Donor reversals:
    - 55% read low first;
    - about 15 mg/dL (p90 23), the same at every glucose level;
    - back within 2–3 readings;
    - day and night alike, so not compression;
    - per-person rates spread widely, 1–321 events over the record.

    Blood glucose cannot move like that. The sensor now has a transient-bias process: per session
    lnN(8/day, 0.9), amplitude lnN(12, 0.4) mg/dL, 55% negative, first-order recovery with τ 10 min.
    Fitted offline to the donor classes: total 30.3 (29.4), reversal 6.6 (6.8), step 2.0 (2.2),
    catch-up 3.4 (2.2). The FDA fit holds (G7 loss 1.35, PARD 9.5). Catch-ups need no added mechanism.
    The rise-suppression filters in Dexcom/Abbott patents are not visible in these data.

33. **Glucose is lognormal because the stomach is energy-limited; fixed-rate emptying hid a volatility
    deficit.** Donor log-glucose is symmetric (median log-skew 0.01). With fixed first-order emptying,
    every meal reached the gut within ~2 h whatever its size, and simulated glucose ran over-skewed (skew
    1.41, Box-Cox −0.25; donors 0.89, −0.03) with sharp spikes (0.38% of time ≥ 400 vs 0.05).
    Saturating emptying in energy terms, E = Vmax·S/(Km + S), at the review's central values (Vmax 3
    kcal/min, Km 60 kcal; Hunt 1985, Brener 1983, Calbet 1997, Elleri 2013; evidence/09), gave skew
    0.93 and Box-Cox −0.08 (112 people).
    - Vmax 6 gave skew 1.13.
    - Hyperglycaemic slowing at the [J] size over-smoothed (skew 0.60), so it stays off.
    - Carb sensitivity was re-read through the labeler (lesson 27): 1.73 read 1.13 against 1.21, and
      1.85 reads 1.20.
    - The labeler's pulse duration grows with size even under fixed-rate emptying (elasticity 0.49 vs
      the donors' 0.44): it is a detection effect, not evidence for size-dependent emptying.

    With the shape right (cohort c26), the remaining gap is that the simulated people are too well
    controlled:

    | | c26 | Donors |
    |---|---|---|
    | TIR | 77 | 72 |
    | CV | 31.8 | 34.6 |
    | t<54 | 0.06 | 0.23 |
    | Lows per day | 0.59 | 1.08 |
    | Volatility clustering | 0.05 | 0.12 |
    | Long-range Hurst | 0.10 | 0.24 |

    The oversized meal spikes had been standing in for real sources of rough, low-prone hours that the
    model still lacks.

34. **Everyday activity had the right volume and the wrong physics, and a body that moves must eat for
    it.** The donors' extra daytime lows with no bolus in 4 h (0.19 vs 0.09 per day) pointed at activity.
    The literature (evidence/10) put the simulated volume about right (~48 min/day at intensity ~0.25)
    but the effect model wrong:
    - Uptake did not scale with glucose. Dhaliwal 2025 (T1DEXI) reports −11 / −33 / −52 mg/dL from starts
      of 100–150 / 150–200 / 200–250.
    - The acute insulin-sensitivity gain was low (Romeres 2021: about 2 per unit of intensity, not 0.8).
    - Delayed sensitivity started at 0.35; the UVA and Deichmann models start it at about 0.12.
    - Bouts were uniform.

    Now, from the evidence:
    - episodes lnN(2/day), duration lnN(18 min, 0.75), MET-based intensity over a per-person METmax, on
      the UK Biobank day profile, plus a waking background;
    - uptake ∝ G, acute gain 2.0, delayed state from 0.12, per-person gain lnN(0, 0.5).

    That alone (c27) brought lows to the donors' level but dropped the mean to 136 and TDD to 33. Each
    person's food had been set from an insulin balance at rest, while their donor's TDD was spent in an
    active life. A clamp probe now measures the glucose a person's expected activity uses (7–38 g/day,
    median ~28) and adds it to what they eat. Cohort c28 (112 × 14 d) matches 20 of 42 statistics:

    | | c28 | Donors |
    |---|---|---|
    | Lows per day | 1.10 | 1.08 |
    | t<54 | 0.20 | 0.23 |
    | t<70 | 1.9 | 1.7 |
    | CV | 33.6 | 34.6 |
    | TDD | 37.4 | 37.0 |
    | TDD day-to-day CV | 17.6 | 17.0 |
    | Mean | 143.5 | 151 |
    | TIR | 77 | 72 |
    | Lows after a meal bolus | 0.37/day | 0.12/day |

    Open: the high side and post-meal lows.

35. **A per-person trait read off a noisy labeler is mostly the labeler.** Each person's carb-count bias
    came from their donor's labeled entered/pulse ratio. Run through the same labeler, simulated people
    with a known true count bias showed a per-person spread of 0.67 log-sd for a true 0.49. So the
    labeler alone adds ~0.46, which is all of the donors' 0.45. The donors' real per-person bias is
    therefore small, as Brazeau 2013 measured (±0.10). The imported spread made some people
    systematically over-bolus. Now N(−0.10, 0.10). Per-meal labeled spread had told the same story
    (labeler noise ~0.84 log-sd against the donors' total 0.83).

    Cohort c29 (112 × 14 d) matches 19 of 42 statistics:

    | | c29 | Donors |
    |---|---|---|
    | Skew | 0.82 | 0.89 |
    | Box-Cox λ | 0.00 | −0.03 |
    | Lows per day | 0.94 | 1.08 |
    | t<54 | 0.17 | 0.23 |
    | TDD | 36.3 | 37.0 |
    | Mean | 144 | 151 |
    | TIR | 77 | 72 |
    | Lows within 4 h of a meal bolus | 0.32/day | 0.12/day |

    Skew and Box-Cox now pass the KS test. Post-meal lows barely moved. Two related fixes to the
    self-check: it runs 10 days and switches off fat-induced resistance, a disturbance that a perfect
    carb bolus does not cover.

36. **Count behavior from the raw record on both sides.** The template's carb_entries_per_day was ice's
    count of labeled pulses that carry an entry, 2.07/day median. The donors' raw records hold 2.97
    entries/day (merged within 30 min) and 4.59 manual boluses/day: 3.02 with an entry, 0.26 top-ups,
    0.81 lone, 12.0 U/day by hand. The simulator was built on the labeled undercount and validated
    against it, so the error was invisible: 1.96 vs 2.07 "matched". Behavior and validation now use the
    raw rates (templates.add_raw_rates; validate counts delivered person boluses). Top-ups are a new
    behavior. The insulin-burstiness statistic followed (top-1% share 27.6% vs 27.9%; manual
    11.0 vs 12.0 U/day). Still short: 3.3 vs 4.6 boluses/day.

37. **Shrink the body's carb sensitivity toward the settings, exactly as ISF.** Body CSF came from a
    TDD formula independent of the person's own ISF/CR. Settings CR ÷ true CR then spread 0.79–2.05
    (p10–p90), and many meals were mis-bolused by ~2×. Post-meal lows ran 4× the donors' (0.51 vs 0.12
    per day). People tune their carb ratio on their own body, the reason ISF is shrunk (ISF_W 0.5,
    lesson 8). CSF now uses the same weight: settings CR ÷ true CR 0.85–1.47. Re-read through the
    labeler afterwards (×1.18; 1.15 vs 1.21). Labeled meal response: 17.0 mg/dL per 10 g (donors 17.1),
    peak 110 min (111). Post-meal lows are at 0.32/day, still 3×.

38. **A compensation outlives its cause: re-test it when the cause is fixed.** Lesson 10 halved
    Visentin's measured circadian swing because the 24-h amplitude came out at 0.23 against the field's
    0.12. That was under fixed-rate emptying, whose meal spikes were the excess. At the full measured
    swing (c32circ, 112 × 14 d), against donors:

    | | Full swing | Donors |
    |---|---|---|
    | 24-h amplitude | 0.14 | 0.13 |
    | TIR | 74.9 | 71.7 |
    | Time above 180 | 23.1 | 25.6 |
    | t<54 | 0.17 | 0.23 |
    | CV | 35.2 | 34.6 |
    | TDD | 37.5 | 37.0 |

    21 of 50 statistics match. Full swing is the default.

    Still open:

    | | Simulator | Donors |
    |---|---|---|
    | Long-range Hurst | 0.11 | 0.24 |
    | Volatility clustering | 0.06 | 0.12 |
    | Rate dispersion | 2.5 | 3.6 |
    | Between-day fraction | 0.17 | 0.10 |
    | Day/night insulin ratio | 1.21 | 1.38 |

39. **Day-to-day structure: regulate daily intake, but Loop absorbs it, so the persistence must come from
    insulin need.** Donor days are steadier and persist; simulated days were irregular and independent:

    | | Donors | Simulator before |
    |---|---|---|
    | Entered carbs, day-to-day CV | 0.40 | 0.52 |
    | Daily-mean glucose, lag-1-day correlation | 0.23 | −0.02 |
    | Between-day fraction | 0.10 | 0.16 |

    Daily intake is now regulated over 24 h (AR(1) on log scale: CV 0.22, Tarasuk & Beaton 1992 and
    dietary-record studies; ρ 0.29, Levitsky 2017), shared by the day's events. Eaten CV 0.24, event
    p99.9 146 g.

    It did not move glucose persistence (lag-1 0.01) or the between-day fraction (0.155). Loop absorbs
    intake swings within the day. Entered-carb CV stayed 0.54, because which events get entered is still
    independent per event.

    Ablations (c33) also clear the existing day-level terms: day-level SI off moves the between-day
    fraction only 0.159 → 0.145, and illness not at all. The donors' persistence must come from
    multi-day changes in insulin need. Named candidates: menstrual phases (off: no monthly rhythm in
    donors), stress, sleep debt, sensor-session bias, site age. Cohort c34: 21 of 50 statistics match.
    Scoring now starts at the first midnight after burn-in (whole days only; 0.174 → 0.165).

40. **Temporary Overrides are a large, measured behavior; and the simulator's "true CR" is linear-part
    bookkeeping, not what a body-consistent dose would use.**
    - **Overrides.** 71% of pilot donors use Temporary Overrides: median 0.36/day, 0.6 h/day, p90
      6.6 h/day. They come in three classes:
      - less insulin (45%): median factor 0.60 for 1.4 h, target ~130, starting ~126 and falling,
        mostly afternoon;
      - more insulin (17%): factor 1.33 for 1 h, starting ~210 and rising;
      - target only (37%): mostly a lowered target ~90 for ~1 h, i.e. pre-meal.

      The plan-able classes are now planned with the events they serve, at each donor's rates and
      settings: less-insulin with activity episodes, pre-meal targets with entries
      (templates.add_override_rates). They are written into the exported therapy timeline, which
      LoopEval gates causally (applied from start). Every day is planned up front, so the plant's
      re-simulation sees the same plan. The reactive more-insulin class needs plant-sent overrides
      (handoff to simulator). Effect in cohort c35: lows 1.17 → 1.08/day; nothing else moves beyond noise.
    - **Units.** ISF is calibrated as the effective drop on the full body (lesson 15), but the true CR was
      ISF ÷ the linear-part CSF. A person dosed exactly to that CR, with defense off, runs 20–50 below
      rest: glucose effectiveness erodes a meal's rise as it erodes a bolus's drop. Two alternatives
      failed on the cohort's TDD anchor:
      - the effective peak-probe CSF (_probe_csf_effective) fed people for 42 U/day against the donors'
        37 (cohort c36: mean 157, TIR 67, labeled pulse 0.91 vs 1.21);
      - a whole-excursion balance is degenerate, because glucose effectiveness clears a meal by itself
        over 6 h (CR up to 149 g/U).

      The linear-part CR stays as the intake bookkeeping. The self-check doses with the body-consistent
      effective CR instead.
    - **Self-check isolation.** The self-check had been passing for the wrong reason: its perfect person
      still rescued and grazed, because `behavior_defense` had never been wired. It now really switches
      off defense, grazing and fat resistance, and doses each meal's own carbs without netting the
      previous bolus as IOB.
    - **Side result.** c36's heavier meals raised long-range Hurst to 0.19 (donors 0.24). Meal-driven
      variability is part of what the slow structure lacks.

41. **Settings edits are real but too small to show in 14 days.** Donors' daily schedule means change
    2,821 times across 156 donors in ~4 months:
    - per setting, median 0.03/day basal, 0.016 ISF, 0.016 CR;
    - median |change| 3.6%, p90 14%;
    - only weakly reactive (corr 0.16 with the previous 3 days' glucose).

    They are now dated eras in the exported basal/ISF/CR schedules (templates.add_edit_rates; 1.6 per
    person per 14 days), with random sign. Cohort c37 moves nothing beyond noise. Edits accumulate over
    months, the slow component of the donors' daily-mean autocorrelation, which a 14-day run barely
    samples.

42. **Stationary sensor noise erases the CGM's structure; real noise level wanders.** Simulated true
    glucose already carries the donors' process structure:

    | | True glucose | Simulated CGM (before) | Donors' CGM |
    |---|---|---|---|
    | Volatility clustering | 0.16 | 0.05 | 0.12 |
    | Long-range Hurst | 0.21 | 0.12 | 0.24 |
    | Rate dispersion | 4.5 | 2.4 | 3.6 |
    | Step kurtosis | 2.3 | 1.5 | 2.5 |

    Offline ablation (sens_struct): the colored noise (AR terms, transients) erased the structure. With
    all of it removed, clustering and dispersion return to the donors' values, but step SD falls to 4.1
    against 7.0. So the noise is real, just not constant: SNR varies within a sensor over time
    (Facchinetti 2011; evidence/08 §B). The noise level now wanders, variance-preserving: σ·exp(z − sd²),
    z a log-OU with sd 0.7 and τ 8 h (G7 0.6 with σ 2.8). Cohort c38:
    - jump anatomy matches class by class (28.1 / 7.2 / 2.2 / 1.4 / 11.3 / 5.0 vs 29.4 / 6.8 / 2.2 /
      2.2 / 11.6 / 5.0);
    - SD/MAD passes for G7 (1.417 vs 1.410), step kurtosis for G6 and Libre 3;
    - rate dispersion 3.46 vs 3.61; FDA loss G7 1.4–1.7.

    The FDA tables constrain the size of the error, not its timescale. That freedom has to be pinned by
    the CGM's own structure.

    Also: corrections ran at half the donors' rate. The hazard was sized by the donor's time above 180,
    but corrections fire above the person's own level and only when CGM is not falling and nothing was
    bolused in 2 h (46% of minutes). Planned top-ups executed 38% of the time. Both are now sized to
    realize the donor's rate.

43. **A [J] prior six times the literature made whole days of highs; three evidenced insulin-delivery and
    physiology terms now carry the high side.**
    - **Site failures.** Failing absorption, full occlusion and dislodgement had been set to 15% + 2% + 3%
      of sites. Kanapka 2022 (22,741 wears) puts sets ending in prolonged hyperglycaemia at 3.3% all causes
      (adults 1.9%, ages 14–17 5.8%). At the literature rates (youth ×3), the between-day fraction fell
      0.142 → 0.112 (donors 0.105), and daytime no-bolus lows matched (0.183 vs 0.185). But TIR rose to 77
      and time above 180 fell to 19.6 (donors 25.6): the excess failures had been supplying the highs.
    - **Attribution of highs.** By context, the shortfall is in highs with no eating in the past 4 h
      (2.8% vs 6.1% of readings) and in late announced meals.
    - **Two named terms** went in for that:
      - Hyperglycaemia-induced insulin resistance: 24 h at 20 mM lowers insulin-stimulated uptake 26% in
        T1D (Vuorinen-Markkola 1992; Yki-Järvinen 1987). A state with τ 12 h [J].
      - Absorbed fraction falling with set age: fasting glucose 126 / 133 / 147 on days 1 / 3 / 5 with
        insulin unchanged (Sampson Perrin 2015); extent down, rate up (Simic 2021). −2.5% per day after
        day 1 [I].

      Cohort c45 (112 × 14 d): every outcome statistic passes KS (mean p 0.08, TIR 0.31, time above 180
      0.17, t<70 0.27, t<54 0.13, CV 0.13, TDD 0.74). 21 of 50 overall.
    - **Still failing.** The process statistics. Increment skew is the clearest: true-glucose increments
      skew −0.33 (falls sharper than rises), against the donors' CGM +0.34.

44. **Meals rise faster than they fall: the liquid phase empties first.** In simulated true glucose,
    5-min increments skewed −0.33: falls sharper than rises. The donors' CGM increments skew +0.34. The
    energy-limited gastric model (lesson 33) had no early fast phase. Nutrient liquids empty fastest in
    the first 15–30 min (Hunt 1985; Calbet 1997: early delivery 3–8 kcal/min, glucose t½ ~9 min), and a
    mixed meal's liquid share leaves first.

    A share of each meal's carbohydrate now empties fast (kempt = kabs 0.08) outside the energy
    ceiling. The share is a [J], chosen between 0.2 and 0.35 by cohort; 0.2 (c46_f0.2, 112 × 14 d)
    matches 27 of 50 statistics, the most so far:

    | | Fast phase 20% | Donors |
    |---|---|---|
    | Skew | 0.895 | 0.893 |
    | Box-Cox λ | 0.00 | −0.03 |
    | CV | 34.3 | 34.6 |
    | G7 step kurtosis | 2.55 | 2.48 |
    | True-glucose increment skew | −0.06 | — |
    | Labeled meal rise per 10 g | 18.7 | 17.1 |

    Every outcome passes. The 35% share overshoots the rise (22.2 per 10 g) and the skew.

45. **Two statistics compared different things, and one input came from the wrong population.**
    - `wear` read `cgm.notna().mean()`. A donor series holds only readings that exist, so it was always
      1.0, while the simulated series has NaN for withheld slots. It is now coverage of the span on the
      5-min grid for both: donors 0.977, simulator 0.960, a real gap.
    - The simulator's CGM gap rates had been measured on the eda cohort (153 donors), but it is compared
      with the pilot donors. Their G7 long gaps (≥ 90 min) run at about half the eda rate. G6 and G7
      gaps now come from the pilot donors; Libre 3 keeps the eda rates, with only 6 pilot donors.
    - Cohort c47 (all defaults through lesson 44) reproduces c46_f0.2 exactly (same seeds, same
      configuration): 27 of 50.

46. **Check every effect size against its own source.** The 2-to-4-hour structure function saturated
    early:

    | Lag | 2 h | 3 h | 4 h | 6 h |
    |---|---|---|---|---|
    | Simulator, SD of glucose change (c48) | 63.8 | 66.5 | 68.6 | 71.9 |
    | Donors | 61.4 | 69.3 | 73.5 | 75.3 |

    Simulated excursions resolved by ~2 h. A slower solid phase (Vmax 2.5) shrank every lag instead of
    shifting variance to the longer ones. The late-acting term that was undersized was fat-induced
    insulin resistance:
    - Wolpert 2013 measured +42% insulin (mean) after a 60 g-fat dinner;
    - per-person ρ ~ U(0, 0.35) gave the median person ~21%;
    - ρ ~ U(0.1, 0.6) (mean 0.35) reproduces the measured mean with a wide spread.

    Cohort c50:
    - mean 149.1 (p 0.57), TIR 73.7 (p 0.64), time above 180 24.4 (p 0.73);
    - total time above 180 27.4% vs the donors' 27.3%, with announced-meal highs matching by context;
    - 4-h SD of change 70.7, long-range Hurst 0.12;
    - highs with no eating in the past 4 h are still half the donors'.

    The structure function by lag (median person SD of Δ at 5 min–6 h) is now a standard check, done
    the same way on both sides.

47. **Donors bolus more than once per meal, and they enter their bigger meals.** Classified the same way
    (an entry within 30 min / a top-up within 60 min of a bolus / lone):

    | Per day (median) | Simulator | Own donor |
    |---|---|---|
    | Carb entries | 2.75 | 2.80 |
    | Boluses with an entry | 2.58 | 3.05 |
    | Lone boluses | 0.50 | 0.78 |
    | Entered grams | 72.7 | 93.8 |
    | Grams per entry | 27.8 | 32.6 |

    Three corrections followed:
    - Boluses per entry (1.09 median, 1.22 mean) had been clipped to one. The excess is now a split
      meal bolus: 60% at the entry, then Loop's recommendation 10–30 min later [J split].
    - Corrections are sized for the 36% of intended corrections that deliver 0 U, because Loop's
      recommendation is already covered by IOB.
    - Main meals are 1.9× snacks (Camerlingo 2021: B 41 / L 49 / D 53 vs snack 25 g). Lesson 16's
      flattening to 1.0 compensated for fixed-rate emptying, which is gone.

    Cohort c52_w1.9:
    - grams per entry 32.3 (32.6); manual 10.5 U/day (12.0); boluses 3.8/day (4.6);
    - top-1% insulin share 26.0 (27.9; passes); day/night insulin 1.32 (1.38);
    - labeled pulse-size distribution matches by bin (≤ 15 g 14% vs 14%; 50–70 g 10.4% vs 10.4%);
    - meal response 17.2 mg/dL per 10 g (17.1);
    - all outcomes pass; 24 of 50 statistics match.

48. **The donor's basal schedule is a per-person measurement of their daily need; flattening it lost the
    day/night split.** In local time, donors deliver much less insulin overnight than the simulator did:

    | Local hours | 00–03 | 03–06 | 12–15 | 18–21 |
    |---|---|---|---|---|
    | Donors, relative to daily mean | 0.68 | 0.56 | 1.34 | 1.33 |
    | Simulator | 0.82 | 0.78 | 1.12 | 1.17 |

    The day/night ratio was 1.32 vs 1.38. The model's overnight sensitivity was an extrapolation of
    Visentin's dinner segment (Hinshaw 2013 found no population daily pattern). Each donor's hourly raw
    basal schedule, in local time via the ice steps' local hour (templates.add_basal_profile;
    overnight ~0.91, day ~1.03, within-person SD 11%), now drives both sides:
    - Loop's exported schedule uses it hour by hour;
    - the body's basal need (EGP) follows it shrunk halfway in log terms, the ISF / CSF weight.

    Cohort c53: day/night 1.396 (1.38), t<54 0.19 (0.23), 25 of 50 statistics match. The 24-h glucose
    amplitude is now a little high (0.165 vs 0.129), with Visentin's meal-time swing and the basal profile
    both acting.

49. **The slow-structure gap is a restoring force that is too strong, even with no eating; no evidenced
    dial closes it without breaking the levels.**
    - **True glucose oscillates too cleanly.** Simulated true glucose (no sensor) has a strong negative
      step-ACF lobe: minimum −0.34, zero crossing 62.5 min. Donors' CGM reads −0.11 and 42.5 min; the
      simulated CGM −0.14 and 55. Sensor variants barely move it, so excursions are too regularly
      rise-then-fall.
    - **Quiet windows show the same saturation.** With no eating or bolus for 4 h:

      | SD of change over | 1 h | 2 h | 3 h |
      |---|---|---|---|
      | Donors | 25.2 | 37.4 | 46.4 |
      | Simulator | 27.2 | 37.4 | 40.3 |

      Real glucose keeps drifting; simulated glucose is pulled back.
    - **Tested and not adopted:**
      - Day-level SI variance (CV 8%) as a smooth OU process (τ 6 h, 12 h): repeat clamps size the
        variance, not its shape in time. Hurst unchanged; between-day fraction 0.138 → 0.124–0.127.
      - Glucose effectiveness at the low end of its evidence range (UVA/Padova fits 0.0013–0.0047).
        ×0.5 raised Hurst 0.12 → 0.18 and lengthened the structure function, but the mean went to 159,
        TIR to 68 and t<54 to 0.09; ×0.7 gave Hurst 0.15 with the same direction of damage.

      Restoring force governs the slow structure, but the dial moves the levels with it.
    - **What the missing factor must look like.** It acts over hours with no meal: it raises the 3-h
      drift without raising mean glucose, so either it varies in sign or it is offset by something
      else. Candidates still unbuilt: stress / sleep (evidence 02 §4.1–4.2, small or day-level),
      intraday SI wander (no controlled-condition evidence, LESSONS 1), real-world sensor sensitivity
      drift beyond the clinic tables.
    - **Also tested and not adopted:** an hours-scale OU sensor bias (Breton & Kovatchev 2008: error
      autocorrelated for hours), within the FDA error budget. It lowered offline Hurst (0.197 → 0.175),
      clustering and dispersion: variance added evenly past τ flattens the structure function rather
      than tilting it. Left in the code at sd 0 (`slow_bias`).

50. **Reactive overrides need the plant to speak, and the engine now lets it.** The simulator role added
    plant-sent Temporary Overrides (main 14b2d58; trace `isf` reflects them from ce2cd7f) on the
    2026-10-16 handoff.
    - The additive person now starts the more-insulin class while awake when CGM is above 180 and
      rising, at the donor's rate, factor, target and duration.
    - A paired run (reactive on/off, same seed) gives identical candidate doses before the first
      override and up to 0.25 U differences inside it.
    - Planned (exported) overrides are now clipped at the next window's start, so a new override
      replaces the running one as in Loop; the engine otherwise kept the earlier window.
    - Cohort c57 (14b2d58): 0.22 reactive overrides/day against the matched donors' 0.195. Outcomes all
      pass (TIR p 0.88, time above 180 0.84, t<54 0.58); process statistics unchanged.

51. **Donor clock hours were UTC; in local time the sim's day had the wrong shape.** The exports carry UTC with no
    zone. Three measures read donors 4–7 h off: the quiet-window CGM series, the day/night insulin ratio and the
    waking-hour correction exposure. All three now use the ice steps' local hour (`quiet.local_offset`, `to_local`).
    In local time:
    - Day/night insulin is 2.06 for donors (it read 1.38). The sim was at 1.41.
    - Overnight quiet-window 3-h SD matches (32.4 vs 33.1). The "overnight variance gap" that motivated growth-hormone
      pulses was the UTC artifact, so GH pulses are not built.
    - Donors are lowest at 05–07 h (130) and highest at 20–23 h (166). The sim peaked at dawn (158 at 06 h).
    - On quiet mornings (no event 23–07 h) donors' insulin falls slightly from 01–03 to 05–07 h (0.92) and glucose
      drifts −7 mg/dL from 03 to 07 h. The sim rose +11 with 1.25× insulin.

    Ablations (c58, 56 people each): dawn off −5.6; Visentin circadian off −1.6 but loses real variance (TIR 75.8,
    t<54 0.09, amplitude 0.09); both off −7.9. Changes:
    - **Dawn is carried by the donor's basal profile** (B1b) when there is one; the separate dawn bump (B2) stays for
      people without a profile.
    - **Visentin's breakfast SI starts at 07:00, not 04:00.** His levels are breakfast meal-test SI; the 04:00 switch
      turned them into a pre-dawn rise in fasting need for the 70% with low breakfast SI. The dinner level holds
      overnight. [J boundary]
    - **Meals by the donor's own windows** (`templates.add_slot_rates`): through the same labeler the sim ate the
      donors' lunch and dinner grams but announced breakfast more and lunch and dinner less (entered 17/19/23 vs
      10/27/31 g/day). Main-meal shares now follow the donor's breakfast/lunch/dinner grams and each meal's entry
      chance follows the donor's relative announcement in that window (median 0.26/0.52/0.48 announced); snacks keep
      the donor's total entry rate.

    Cohort c60 (112): 06 h glucose 130.5 (130.3); quiet-morning insulin 1.02 (0.92), 03→07 h −0.2; amplitude 0.136
    (0.131); day/night 1.62 (2.06); outcomes all pass (TIR 72.9 vs 71.7). Open: the 09 h post-breakfast peak (157 vs
    141) and a flat evening (149–152 vs 159–166).

    Two dead ends: the quiet-window comparison through the labeler leaves the sim almost no quiet windows (0.5 vs
    1.7 h/day), so it can't test daytime drift. The sim's automatic boluses reach the plant inside each step's
    5-min basal record. The delivered insulin is the same, but the pump model gives them basal flow error rather
    than per-bolus error.

52. **Announced meals respond about 0.7× the donors' from the first hour on, at every meal; the B/L/D class mix is
    not the cause.** Isolated announced bolused meals (no eating in the 3 h before), through the same labeler, median
    glucose above onset (mg/dL; `mealcurve` in the run scratch):

    | | 1 h | 1.5 h | 2 h | 3 h |
    |---|---|---|---|---|
    | Donors breakfast / lunch / dinner | 30 / 33 / 29 | 44 / 40 / 34 | 45 / 40 / 35 | 35 / 35 / 36 |
    | Sim c60 (Visentin classes) | 26 / 20 / 20 | 35 / 26 / 24 | 39 / 27 / 21 | 31 / 20 / 18 |
    | Sim c61 (classes equally likely) | 25 / 23 / 23 | 33 / 29 / 27 | 34 / 27 / 24 | 24 / 21 / 21 |

    Entered grams (34–41) and grams per bolus unit (9–10) match the donors. Equal class probabilities (Hinshaw 2013
    found no population B/L/D SI difference in T1D; Visentin 2015 classifies against each person's own maximum, which
    noise inflates) move the shape toward the donors' mild breakfast > lunch > dinner, but leave the amplitude, the
    flat evening and day/night (1.56) unchanged; statistics 12 vs 13 of 29 — kept Visentin's published probabilities,
    `--set circ_uniform=1` stays as the switch. Not yet measured: whether the gap is meal-side (absorption shape, the
    eaten/entered ratio, composition of later meals) or insulin-side (bolus coverage of the body's effective CR —
    the bookkeeping CR is 0.69× the setting and says nothing about coverage, LESSONS 40). Next: the same curve on
    TRUE glucose with eaten grams, to split the two.

53. **The meal-response gap is a timing problem of big meals; emptying form, fat and coverage are ruled out.** By
    entered grams (labeled, isolated announced meals), the sim matches donors up to 25 g. From 40 g it falls back
    toward baseline at 1.5–3 h while donors plateau (+36 to +39), and above 60 g it dips to ~0 at 2 h and surges late
    (+45 at 4 h, +72 at 5 h vs donors +37/+30). On true glucose the big-meal appearance rate is a plateau (~4 mg/kg/min
    from 1 to 2 h, 2.8 at 4 h) while bolus insulin peaks at 1 h: insulin wins mid-meal, the carbohydrate wins late.
    - **Coverage matches** at every size (entered ÷ pulse 0.47/0.89/1.21/1.85 vs 0.48/0.89/1.22/1.89; g/U within 0.7,
      the sim doses slightly less per gram).
    - **Power-law emptying** (`ge_gamma` 0.5: kcal/min ∝ load^0.5, Schirra 1996 / Hunt 1985; c62) half-empties an
      80 g meal at 108 vs 132 min open loop, but closed-loop big meals still dip (h2 10 vs 36) and t<54 fell to
      0.107 (p 0.048). Option kept, off.
    - **Fat resistance off** (c63): big meals still dip and surge (+52 at 5 h); mean falls to 141 and Hurst to 0.07.
      Fat stays.
    Elleri 2013 (T1D, 121 g evening meal) bounds the appearance: 50% by 100 min (high GL) or 175 (low GL); the default
    model sits near the low-GL value for meals that size. Open: what front-loads big-meal appearance relative to the
    bolus in real people, or what holds their insulin back mid-meal (Loop's own response to a plateau is the same
    code in both).

54. **A second bolus on the same entry is the person's planned remainder, not a fresh recommendation.** Simulated
    people realized fewer manual boluses than their templates (median 3.58 vs 4.17/day). Split remainders dosed
    at Loop's recommendation came out 0 U 36% of the time, and top-ups 58% (already sized for, LESSONS 42). In the
    donors' raw records (17,898 pairs of boluses within ±30 min of one entry, ≤ 60 min apart), the second dose is about
    as big as the first (second/first median 0.93, quartiles 0.42–2.0) and comes a median 12 min later (10–90%: 2–26).
    So the split is drawn from that ratio, and the rest goes as units (the world reads the delivered first part; it
    looks again after 5 min if LoopEval has not delivered it yet; skipped when CGM < 80 [J]).
    Cohort c64: zero-delivery time 31.3% (34.4; was 29.2), manual 11.0 U/day (12.0; was 10.7), boluses 3.67/day
    (4.59). Outcomes unchanged. The big-meal mid-meal dip remains (LESSONS 53).
    Around isolated announced meals donors also spread meal insulin wider than the sim: 25% more than 15 min before onset
    (sim 20%) and 16–27% from 1 to 3 h after (sim 12–25%). In −1…3 h they give 1.26–1.95 U per 10 g entered against
    the sim's 1.03–1.64. Their labeled big-meal pulses are also ~10% larger (47 vs 42 g-eq above 60 g entered).

55. **Night-to-night insulin, and why post-low resistance is not added.**
    - Overnight (00–06 local) delivered insulin varies 30.3% night to night on donors' quiet nights (no eating or
      manual bolus 22–06; 124 donors), which is Ruan 2016's 31%. Over all nights it is 40%. Midnight glucose explains
      ~10% of it, and successive nights barely correlate (lag-1 0.09), so the variation is nightly, not multi-day.
      The sim gives 17% on quiet nights (31 people, ~3 nights each) and 30% over all nights. `night_cv` (all
      nights, 13-day blocks) is now a standing statistic: donors 37.2, c64 33.7 (p 0.11).
    - Post-hypoglycaemic insulin resistance (Attvall 1987) is not added. 2–4 h after a low's nadir the sim already
      rebounds as high as donors (+68 to +70 vs +65 to +73 mg/dL) and goes above 180 within 4 h more often (54% vs
      46%). Only the first hour of recovery is slower in the sim (+45 vs +56 at 1 h): rescue timing, not resistance.

56. **Most of donors' night-to-night insulin variation is unexplained by evidenced physiology; it stays
    unexplained.** Literature budget (evidence/12): the evidenced nightly factors add 0.02–0.035 of variance
    against the 0.06 gap. The top ones are post-exercise overnight sensitivity, dinner fat and its spread,
    short sleep (Donga 2010: −21% SI after 4 h), alcohol (Turner 2001: effect mostly after 06 h) and nocturnal
    GH. Together they take a quiet-night CV of 17% to about 22–26%, against 30%. Perriello 1991 calls
    overnight need "highly reproducible" under i.v. control, so most free-living variation is outside the body.
    Donor-side checks (c64, local time):
    - **Weekend:** Friday/Saturday nights take 1.036× a person's mean overnight insulin, other nights 0.986×.
      A real 5% effect; the sim shows 0.9%.
    - **Evening carry-over:** evening carbs, boluses, midnight glucose, recorded night carbs and the weekend
      together cut donors' night CV only from 40.9% to 36.5%. In the sim the same covariates take 31.5% to
      20.1%, mostly night eating: simulated people eat between 00 and 06 h on 48% of nights. That eating
      follows the donors' own labeled pulses by hour, and some of those night pulses may not be eating.
    No noise term is added. The all-nights statistic passes (37.2 vs 33.7, p 0.11).

57. **The delayed exercise effect is a third of McMahon's size, but sizing it up adds lows the donors don't show.**
    Paired runs on the same 56 people with the same planned sessions (`truth.ex_boost` now logged):
    - **Default** (linear drive, b 0.018): on nights after an afternoon or evening session the delayed state is
      0.16 vs 0.02, but overnight insulin is 1.03× the exercise-off arm and glucose only −1.9 mg/dL. At basal
      insulin the model's insulin-driven disposal is ~1.1 mg/kg/min, so 0.16 adds ~0.18. McMahon 2007 measured
      ≈ +0.6 mg/kg/min of glucose need 7–11 h after a 45-min moderate session; Taplin 2010 puts overnight need
      10–20% lower.
    - **b 0.055** (McMahon-sized): overnight insulin −6%, glucose −9 mg/dL; hypo-below-60 nights after
      sessions 17.3% vs 13.4% (×1.29; Tsalikian 2005 ×1.7 without closed loop). But everyday walking gets 3× too:
      t<54 0.39 (0.22) and t<70 2.6 (1.7) fail.
    - **Quadratic drive** (`z_power` 2, b 0.134: walking at its old size, sessions McMahon-sized; glycogen use
      rises steeply with intensity): overnight −2.5%, glucose −6.8, t<54 0.30, reaching 54 0.233 (p 0.047). It
      scores 17 of 30 statistics against the default's 20 on the same people.
    The default stays; `ex_b` / `ex_zp` remain switches. Session frequency and intensity are [J] and donors carry
    no activity record, so neither side is pinned. A 56-person cohort passes more statistics than a 112-person one
    (20 vs 14 for nearly the same model) because KS loses power: compare scores at equal n only.

58. **Donors' night "pulses" are mostly not eating: snacks go in waking hours only.** Snack times followed each
    donor's labeled-pulse clock, ~18% of which starts 00–06, so simulated people ate between 00 and 06 h on 48% of
    nights. Donors' raw carb records show eating on 7%. With snacks restricted to the person's waking hours
    (c66), the labeler still finds 1.23 night-window pulses a day in the sim against the donors' 1.21. The labeler
    makes them from non-eating rises: post-low rebounds, the sensor, overnight drift. Day/night insulin
    1.64 → 1.82 (donors 2.06); overnight delivery 0.59–0.72 of the daily mean (donors 0.55–0.72). Outcomes are
    unchanged. 12 vs 14 of 30 statistics (n = 112, within cohort noise); the 24-h amplitude rises to 0.157 (0.131)
    and 06 h glucose falls to 125 (130).

59. **The seven Visentin patterns are now equally likely.** Visentin 2015's mix (70% low breakfast SI, 65% high
    dinner SI) plus the 07:00 breakfast switch gave simulated glucose 153–157 at 09 h against donors' 141. With
    equal classes it is 143–145, in two independent tests (c61, c68), at the same number of matched statistics (13
    vs 13 of 30). Hinshaw 2013 (T1D, triple tracer, same meals B/L/D) found no population difference, with patterns
    specific to the individual; Visentin classifies each person against their own maximum, which noise inflates.
    Two checks that did not help:
    - Netting expected snack grams out of each main-meal window (c67) left breakfast-window labeled grams at 51.6
      (39.2). The excess is the morning response, not double counting. The netting stays for consistency.
    - Letting the body follow the donor's basal profile fully (`prof_w` 1.0 instead of 0.5, c69) left 06 h glucose at
      124 (130) and raised dawn-hour insulin (0.80 vs 0.75; donors 0.59). Option only.
    Open: the pre-breakfast trough (123–124 at 06 h vs 130) with more dawn insulin than donors, and the flat evening.

60. **Loop not acting is a measured component, and the first named one that moves long-range persistence.**
    Donors' `disruptions.csv` (168 pilot donors):
    - **Offline gaps and merged mixed windows:** 0.9/day median (1.04 mean). Duration lnN(32 min, 0.86): quartiles
      22/29/50 min, p99 4.6 h; 2.9% run longer than 6 h, mostly pumpless stretches with unknown insulin, left out.
    - **Pump-error cycles:** ~3 min each, 2.45/day median.
    - **Timing:** both daytime-heavy (5–6%/h from 15 to 21 h, 1.7% at 03–04).
    The plant plans these per person at its donor's rates (`templates.add_disruption_rates`,
    `world.plan_outages`) and writes them to the export's `disruptions.csv`. LoopEval auto-loads that file and
    delivers what the pump would: scheduled basal while offline (checked: 0.305 U/h over a 20-min window, then
    dosing resumes), the last command through a pump error. Loop's IOB follows.
    Cohort c70 vs c68 (n 112):
    - Long-range Hurst 0.137 → 0.167 (donors 0.247); volatility clustering 0.148 → 0.135 (0.124).
    - Zero-delivery share 30.5 → 28.9 (34.4) and night-to-night CV 34.1 → 31.2 (37.2) move away, since offline
      stretches run scheduled basal.
    - Outcomes unchanged. 12 vs 13 of 30 statistics.
    Suspends (0.18/day, median 2 min) are not modelled: a synthetic export has no field record to deliver zero from.

61. **Loop's stale-CGM guard is on in plant runs.** Real Loop issues no new dose once its latest glucose is more than
    15 min old. Donors skip 0.9% of decision cycles this way (median; mean 3.3%, 0.4 runs/day). Plant runs
    did not pass `--cgm-stale-guard-min`, so LoopEval dosed on stale CGM through every simulated sensor gap. They
    now pass 15. Cohort c71 vs c70: about neutral (13 vs 12 of 30; Hurst 0.154 vs 0.167 and between-day 0.145 vs 0.124
    within cohort noise). Kept for fidelity to Loop.

62. **What drives day-to-day spread in the sim, and why glucotoxicity stays.** Within a person, simulated
    daily mean CGM varies 17.9 mg/dL (SD). Logged sensitivity explains 30% of it (r −0.55), daily carbs 11%,
    unannounced grams 9%, rescues and exercise days ~1%. Logged sensitivity includes the glucotoxicity state, which a
    high day itself raises. With glucotoxicity off (c72), the between-day fraction is 0.122 (c71 0.145, donors 0.102),
    but TIR (p 0.009), mean and time above 180 fail. The term has its own clamp evidence (Vuorinen-Markkola 1992), so
    it stays. Between-day fraction moved 0.124 → 0.145 between c70 and c71 for a nearly neutral change, so cohort
    noise in it is ~±0.02; single-cohort differences that small are not evidence.

63. **Cohort noise, measured: one model, two seed sets (c71, c71b; 112 people × 14 d each).** Both match 13 of 30
    statistics, but not the same 13. Seed-to-seed differences in the medians:
    - mean glucose ±3; between-day fraction ±0.025; long-range Hurst ±0.015;
    - zero-delivery share ±2; night-to-night CV ±3; day/night insulin ±0.13; manual U/day ±1.2.
    A change must beat these to count, and single pass/fail flips near p 0.05 are noise. Failures that hold in
    both seed sets are the real targets:
    - long-range Hurst 0.14–0.15 (0.25); ACF zero-crossing 55 (42.5 min); volatility clustering 0.14–0.15 (0.124);
    - 24-h amplitude 0.16 (0.13); TDD CV 14.6–15.1 (16.4) and lag-1 (−0.03 to 0.06 vs 0.11);
    - day/night 1.73–1.86 (2.06); p99 5-min dose 1.19–1.29 (1.67 U); user boluses 3.6–4.0 (4.6);
    - minutes below 70 per episode; wear.

64. **Corrections come soon after the last bolus; the 120-min wait was wrong.** In 44,777 donor boluses without a
    carb entry, 26% come within 20 min of the previous manual bolus, 23% at 20–60, 18% at 60–120 and 34% later.
    Donors' top-ups (≤ 60 min, no entry) come at high glucose (CGM median 202; 79% above 120 and not falling) and are
    small (median 0.5 U).
    - The correction rule waited 120 min after any bolus [J], which forbade two-thirds of that behavior. It now
      waits 10 min, against a double press.
    - Top-ups may now be several per meal bolus (Poisson, for the 24% of donors above one per meal), but under the
      running-high condition that alone moved little.
    Cohort c74 vs c73: lone boluses 0.75/day vs the person's own donor 0.78 (was 0.58), top-ups 0.25 vs 0.22 (median),
    user boluses 3.75 (4.59; p 0.095) and manual U/day (p 0.19) now pass; 14 of 30; outcomes unchanged. The
    hazard's sizing constants did not need refitting. Heavy top-up donors are still under-reproduced on average
    (mean 0.38 vs 0.80/day).

65. **Twin comparison separates model gaps from template sampling.** Each simulated person against their own donor
    (c74, n 112):
    - **Sampling:** zero-delivery time matches the person's own donor (difference +0.0). Its cohort gap (29.4 vs
      34.4) is which 112 templates were drawn; the same holds for entries per day (ratio 1.00 per person).
    - **Real twin gaps:** p99 5-min dose 1.33 vs 1.85 U; TDD −1.4 U/day; mean glucose −6; TIR +2.2; day/night −0.30;
      long-range Hurst −0.10; night-to-night CV −4; 24-h amplitude +0.03.
    - **The dose-tail gap is bolus count, not size:** boluses ≥ 1.67 U run 2.42/day against the own donor's 3.18,
      while manual bolus sizes match or exceed the donors' (p50/p90/p99 1.9–2.7 / 5.3–6.6 / 8.3–9.2 U vs
      2.2–2.5 / 5.2 / 7.8–8.0).
      Boluses with an entry run 12% short of their donors' (2.67 vs 3.05/day) with entries matched.
    Whole-cohort KS against all donors still decides pass/fail, but a gap that vanishes twin-wise is sampling, not
    a missing component.

66. **The failing structure statistics are the meal-scale shape, not missing variance.** The SD of glucose change
    by lag matches the donors at every scale from 1 h to 4 days (sim/donor 1.01, 1.09, 1.03, 1.00, 1.00, 1.00, 0.98,
    0.97 at 1, 2, 3, 6, 12, 24, 48, 96 h; c74 vs one 13-day block per donor). eda's `hurst_long` is the log-log
    slope of that SD between 2 and 4 h. The sim's +9% at 2 h with a match at 3–4 h flattens the slope (0.15 vs 0.25).
    `acf_zero_min` (5-min steps stay positively correlated 55 vs 42.5 min) says the same: simulated excursions build
    faster and are pulled back sooner, where donors rise more slowly and hold to 3–4 h. That is the big-meal plateau
    gap (LESSONS 53) seen cohort-wide.
    The gut is within its evidence:
    - The model's 121 g mixed meal appears 25/50/75% at 95/178/270 min, Elleri 2013's low-glycaemic-load meal
      (88/175/270); a lower-fat one falls between Elleri's two meals (72/130/197).
    - Ferrannini 1985's 73% at 3.5 h after 75 g oral glucose is systemic appearance after splanchnic first pass, so
      it does not pin the gut's own tail.
    The open lever is what returns glucose after the peak: insulin action timing (set to Loop's curve on field
    forecast evidence, LESSONS 20), glucose effectiveness (halving it traded level for structure, LESSONS 49), and
    Loop's response to a plateau. Any change there must keep the first-hour forecast match that LESSONS 20 rests on.

67. **Lipohypertrophy, wired at its evidenced prevalence, closes the level gaps.** The component had been built but
    left off "until a prevalence is assigned". Prevalence: 26% of pump users self-report LH (Pickup 2014); 42–47% of
    children on examination (Heinemann & Krinelke 2012). Famulla 2016 (lispro, n = 13) measured, in LH vs normal
    tissue: insulin AUC −21%, Cmax −23%, within-subject AUC CV 52 vs 11%, post-meal glucose ≥ 26% higher. A person
    with LH places half their sites in LH tissue [J, rotation]. An LH site has bioavailability 0.78 and a per-dose
    absorption CV of 0.5 (vs 0.15), for the whole wear.
    Cohort c75 vs c74 (n 112):
    - mean glucose 151.5 (donors 151.4; was 147.2); TDD 37.2 (37.2; was 36.0); TIR 71.1 (71.7); time above 180 25.7
      (25.6); TDD lag-1 0.05 (0.11; was −0.01). This matches the twin gaps of LESSONS 65 (TDD −1.4, mean −6).
    - 16 of 30 statistics, the most at n = 112.
    - t<54 0.135 (0.215, p 0.105) is lower, so watch it.
    `--disable lipohypertrophy` switches it off.
    Second seed set (c75b vs c71b, seeds 2000+): 14 vs 13 of 30; mean glucose 145.9 → 147.7; long-range Hurst
    0.139 → 0.157 (both seed sets +0.016–0.018 since c70/c71); user boluses 4.58/day vs donors 4.59. The level gain is
    smaller here than in c75 (+1.9 vs +4.3 mg/dL), within the noise of LESSONS 63.

68. **Glucose effectiveness at ×0.7, with the levels now right, still trades rather than wins.** c76 vs c75 (n 112):
    - Long-range Hurst 0.162 → 0.195 (0.247) and volatility clustering passes (0.135).
    - Mean 151.5 → 155.6, TIR 71.1 → 68.9, t<54 0.135 → 0.121 and ACF zero-crossing 55 → 60 min (42.5) move away.
    - 16 vs 16 of 30.
    The evidence leaves SG unpinned: UVA/Padova fits 0.0013–0.0047/min (the model sits inside, 0.003 plus an
    insulin-dependent part via κ); ReplayBG's prior median is 0.022. Choosing it by cohort statistics would be tuning a
    free parameter to a target, so the default stays. That is a decision for Pete, raised on the board.
    LESSONS 49's quiet-window evidence for "restoring force too strong" mixed daytime windows with unlabeled eating
    (LESSONS 51). What still stands is the true-glucose step ACF (minimum −0.34) and the 2-h excess of LESSONS 66.

69. **Post-meal EGP suppression set from T1D tracer data; meals plateau more.** The share of insulin's effect through
    EGP suppression was U(0.3, 0.5) [J]. Around isolated bolused meals the model's EGP bottomed at 70% of pre-meal at
    ~2 h (30% suppression) and averaged 88% over 5 h. Romeres 2025 (T1D adults, triple-tracer mixed meal, usual bolus)
    measured a nadir of 44 ± 17% at ~160 min (evidence/13). Paradoxical glucagon at its evidenced size accounts for
    ~0–10 mg/dL (Hinshaw 2016: pramlintide lowered glucagon without changing EGP), so no glucagon term.
    - **Probes** (56 people): share 0.65 gives a 53% nadir, 0.8 gives 72%. Higher shares flatten post-meal curves
      toward the donors' plateau (0.8: dinner 25/31/33/30 at 1/1.5/2/3 h vs donors 29/34/35/36) because more of
      insulin's effect acts through the slower EGP arm. Mean glucose rises (156, 161).
    - **Adopted:** U(0.5, 0.7) (centre from Romeres, width [J]). The nadir is now 40%.
    - **Both seed sets (c78/c78b vs c75/c75b):** mean 152.8/148.3 (151.4); day/night 1.79/1.88 (was 1.70/1.83;
      2.06); Hurst 0.170/0.170 (0.162/0.157; 0.247); dinner on true onsets 22/21/10/19 (was 14/3/0/13).
      ACF zero-crossing 60 (55; 42.5) moves away. 13 + 16 of 30 vs 16 + 14.
    - **Still unmatched:** Romeres' suppression is sustained (~45% averaged over 5 h); the model's recovers by
      4 h (5-h mean 17%).

70. **The EGP arm acts more slowly (p2E 0.018 → 0.010/min).** After LESSONS 69 the model's meal EGP suppression
    still bottomed at ~2 h and recovered by 4 h. Romeres 2025's is sustained, with its nadir at ~160 min; ReplayBG's
    prior for the hepatic action rate is 0.008. At 0.010:
    - suppression is still 23% at 2–2.5 h;
    - seed set A (c79 vs c78): Hurst 0.170 → 0.200, night-to-night CV 33.3 → 36.5 (37.2), dinner on true onsets
      27/26/20/22 at 1/1.5/2/3 h (was 22/21/10/19; donors 29/34/35/36), 13 → 16 of 30;
    - seed set B (c79b vs c78b): Hurst 0.170 → 0.178, 16 = 16;
    - levels unchanged (mean 152.9/148.2).
    LESSONS 20 fitted whole-body action to Loop's curve with 0.018; the EGP arm adds little in the first hour, so the
    first-hour forecast match it rests on should hold. Not re-checked.

71. **The tracer-matched EGP arm fails the units self-check; reverted pending a calibration change.** After LESSONS
    69–70 the self-check (truth settings, perfect person, disturbances off, open loop) failed 3 of 8 bodies: nights 64–73
    against rest levels 121–129. The bisection blames both changes: share U(0.5, 0.7) at p2E 0.018 fails 1 of 4, and
    adding p2E 0.010 fails 3 of 4.
    The cause is the calibration, not a fault in either value. Effective ISF and CSF are calibrated on the PEAK
    difference at ~180 mg/dL, and glucose effectiveness erodes a slower effect's peak more. With more of insulin
    acting through the slow EGP arm, the calibration scales insulin up until the peak matches, so its whole-excursion
    effect grows. The self-check doses with peak-ISF ÷ peak-CSF and so over-covers. Its whole-excursion ratio
    (`_probe_cr_true`) is 2–4× the peak ratio for some bodies (41 vs 125, 10.7 vs 40.8) and passes 6 of 8, but stays
    degenerate where glucose effectiveness erodes the excursion (LESSONS 40).
    Closed loop, Loop's corrections hide this, which is why the cohort statistics improved (LESSONS 69–70).
    Defaults are back to U(0.3, 0.5) and 0.018, and the self-check passes 8 of 8. `--set egp_share` and
    `--set ins_p2e` remain. Using the tracer-matched values needs a calibration whose ISF does not depend on action
    timing, which turns on what ISF means for the body; that question is for Pete.

72. **Total-drop ISF calibration, prototyped as an option (`--set isf_total=1`).** It calibrates each arm on the
    linear part (glucose effectiveness, κ, risk and counter-regulation off), so ISF is the total per-unit drop, Loop's
    meaning, and does not depend on how fast either arm acts. The default still matches the full body's peak drop at
    ~180 mg/dL. Self-check with total ISF and linear CSF dosing (consistent definitions):
    - Current EGP arm (share 0.4, p2E 0.018): 8 of 8 pass.
    - Tracer-matched (share 0.6, p2E 0.010): 6 of 8. The two failures are nights −47 and −43 mg/dL below rest (limit
      40): the slow EGP tail of the dinner bolus lands in the post-absorptive night.
    Pairing total ISF with the peak-based self-check CR leaves days high (means 140–245), so each calibration needs
    its own matching self-check. Not adopted; the definition is Pete's call (TIDEPOOL-18).

73. **The weekly cycle is not the missing day-to-day TDD variance.** Donors in local time (168): TDD by weekday,
    relative to each person's mean, is 0.993–1.007. Removing each person's weekday means cuts the day-to-day TDD CV
    only from 19.0% to 18.6% over full records (16.4% in 13-day blocks; sim 14.7%). Entered carbs by weekday are
    0.91 (Friday) to 0.99 (Sunday). No weekly component is added.

74. **Sensor gaps were drawn the right number of times but the wrong length (fixed).** A gap of interval L withheld
    readings until minute + L − cadence, unrounded. In isolation, 37% of the 7–12-min bin came out as 15-min intervals,
    two readings missed instead of one. Simulated G7 then had 1.64 short (7–15 min) and 1.98 medium (15–30) gaps a day
    against the donors' 2.70 and 1.12. A gap now withholds max(1, round(L/cadence) − 1) whole readings.
    Cohort c80: G7 gaps 2.75 / 1.02 / 0.28 a day at 7–15 / 15–30 / 30–60 min (donors 2.70 / 1.12 / 0.27); wear 0.967 →
    0.972 (0.977). The rest of the wear gap is ≥ 12 h gaps (2.6 vs 9.5 min/day). Other statistics are within the noise
    of LESSONS 63 (12 vs 16 of 30, flips at p ≈ 0.05).
    Long CGM outages, measured over donors' full records: G7 has 0.0084/day at 6–12 h, 0.0029 at 12–24 h and 0.0023 at
    ≥ 24 h (≈ 19 min/day missing); G6 0.0012/day ≥ 24 h; Libre 3 0.0065/day. Durations ≥ 12 h: median 22 h, p90 6.4 days,
    p99 27 days, which are stretches without a sensor or without uploads. In a 14-day record that is ~0.03 events per person,
    and donor blocks under 70% coverage are dropped from scoring, so they are not modelled; they are what remains of
    the wear gap.

75. **Pete's calls (2026-10-16): peak ISF calibration with the tracer-matched EGP arm; SG calibrated within its range.**
    - **Total-drop ISF was tried first and breaks the levels.** With the tracer-matched arm and total-drop calibration
      the cohort ran high: mean 171 at SG ×1.0 (donors 151), TIR 61, t<54 0.03. That held even after carb sensitivity
      was re-read through the labeler (CSF_BLEND_CAL 1.25 → 1.08 brought pulse/entered from 1.40 to 1.21): mean 169,
      TIR 62. Glucose effectiveness erodes the slow effect, so a body with total ISF = settings responds more weakly
      than its settings near 180, and Loop under-corrects. Donors run near target on their own settings, which is
      field evidence that effective ISF ≈ settings.
    - **Defaults now:** peak-calibrated ISF, EGP share U(0.5, 0.7), p2E 0.010, CSF_BLEND_CAL 1.25. The self-check
      doses with peak ISF ÷ peak CSF and accepts night-to-night scatter under the slow EGP arm (not drift). Total-drop
      calibration stays as `--set isf_total=1`, needing CSF_BLEND_CAL 1.08.
    - **SG within its range (0.0013–0.022/min), c85–c87 (n 112):**

      | SG | mean | TIR | Hurst | matched |
      |---|---|---|---|---|
      | ×0.7 | 155 | 67.9 | 0.206 | 14 |
      | ×1.0 | 150 | 71.7 | 0.198 | 16 |
      | ×1.4 | 144 | 75.3 | 0.151 | 11 |

      The calibration keeps ×1.0 (0.003/min plus the insulin-dependent part).
    - **Model now (c85):** 16 of 30; levels at donor values; long-range Hurst 0.198 (0.247; was 0.16 before the
      EGP arm). Still failing: ACF zero-crossing 60 (42.5), volatility clustering, between-day fraction, 24-h amplitude,
      day/night 1.77 (2.06), p99 dose, TDD CV and lag-1.

76. **The ACF zero-crossing gap splits by context: meal rises too long, quiet stretches too still.** Step ACF
    zero-crossing (eda's `_acf` on 5-min steps), c85 vs donors, split by time since the last eating or bolus event:
    - **Within 3 h of an event:** sim 55 min, donors 40. Simulated meal-driven moves stay correlated longer; real
      rises are shorter.
    - **More than 4 h after:** sim 20 min, donors 40. Simulated glucose is nearly still between events, so sensor
      noise sets the decorrelation. Donors keep a slow physiological wander there: the between-meal and night-to-night
      variation that the evidenced factors do not explain (LESSONS 49, 56).
    - **Whole record:** sim 60, donors 40.
    Both halves point at known open items, not at a new factor.
    Faster gastric emptying within its evidence range (Vmax 3 → 4 kcal/min, towards Elleri's high-GL meal; c88)
    leaves post-event decorrelation at 55 min and moves away elsewhere: Hurst 0.198 → 0.128, CV 35.0 → 37.8 (34.8),
    Box-Cox −0.10. Vmax stays 3 (LESSONS 33).

77. **Four evidenced nightly factors, built at their literature sizes; too small to move the statistics (as
    budgeted).** Pete chose more named factors over a residual term (2026-10-16). Added to `modulators.py`, each
    switchable (sleep, gh, alcohol, stress) and quiet in the self-check:
    - **Prior-night sleep loss:** nightly duration SD 77 min (Messman 2022); next-day SI −5% per lost hour, waking
      hours (Donga 2010, −21% after 4 h, T1D).
    - **Nocturnal GH:** night-to-night CV 0.32 (Edge 1990, Campbell 1985); the dawn EGP increment of ~20% follows
      it, mean-zero (the mean dawn is in the basal profile).
    - **Evening alcohol:** 63% of adults drink, on 3–20% of nights [J within the ≤ 20% bound]; SI −12% while ethanol
      is present (Kerr); next morning 06–12 h EGP ×0.85 (Turner 2001) [I size].
    - **Stress:** a third of people react (Riazi 2004), on 40% of days, SI −10% from 1 to 5 h after onset (Moberg 1994,
      low end).
    Cohort c89 vs c85: quiet-night insulin CV 15.6% (donors 30.3%); quiet-period ACF zero-crossing 25 vs 20 min
    (donors 40); everything else within cohort noise (15 vs 16 of 30; Hurst 0.156 vs 0.198). evidence/12 budgeted these
    at ≤ 0.02 of the 0.06 variance gap. The between-meal drift stays unexplained.

78. **Unlogged small intake is real, under-sized, and heavy-tailed across people.** Pete: grazing and sugary
    drinks are "definitely a thing for some people". The test from evidence/14 is symmetry of quiet-window changes:
    unlogged intake skews them upward, a physiological drift is symmetric.
    - **Donors (> 4 h from any logged event):** waking-hour 30/60-min changes skew +0.76/+0.59, with rises above 15
      mg/dL 0.88× as common as falls; overnight skew is +0.23/+0.06, about symmetric. The simulator skewed −0.12/−0.45
      by day.
    - **Change:** grazing rate per person lnN(2/day, 1.0) (was 0.7: same median, a long tail of frequent grazers) and
      size lnN(10 g, 0.4), the middle of the evidenced 5–15 g for drinks and sweets (was 6 g). Sources: Piernas &
      Popkin 2010 (97% of adults snack daily, 24% of energy); Groat 2017 (pump users logged carbs on 77% of days).
    - **Cohort c90 vs c89:** quiet-period ACF zero-crossing 20–25 → 35 min (donors 40); daytime rise/fall ratio 0.44 →
      0.59 (0.88); night-to-night insulin CV passes (38.9 vs 37.2); mean 151.8 (151.4); 16 of 30. CV 37.2 (34.8) now
      fails.
    - **Still open:** simulated quiet changes skew downward day and night (−0.23, −0.44): simulated falls are sharper
      than rises, where donors fall slowly. That is the insulin and controller pull-back, not intake.
    A per-person grazing count from donors' small rises does not discriminate (median 0.55 vs 0.53 per quiet hour;
    sensor noise triggers it too), so the rate stays a distribution, not a per-donor value.

79. **The sim's downward-leaning quiet-time changes are in true glucose, in both dosing strategies, and not from insulin
    speed.** After LESSONS 78 the sim's quiet-window changes still skew down (day −0.23, night −0.44 at 30 min) where
    donors skew up by day (+0.76) and are near-symmetric at night (+0.23).
    - **Not the sensor:** the sim's true glucose skews the same way, more strongly at night (−0.99 at 30 and 60 min).
    - **Not the controller strategy:** temp-basal −0.46/−0.74 and automatic-bolus −0.37/−0.49 at night; donors of both
      strategies +0.21 to +0.26.
    - **Not insulin speed:** a slower disposal arm (p2 0.05 → 0.03, inside the clamp range 0.012–0.05; c91) leaves the
      night skew at −0.42/−0.60. It flattens meal rises toward the donors' plateau (dinner 34/34/28 at 1/1.5/2 h) but
      scores 14 vs 16 of 30 and gives up the first-hour forecast fit of LESSONS 20, so the default stays.
    Open: what raises simulated glucose slowly overnight and lets insulin bring it down fast. The candidates are the
    dinner-fat resistance and late protein tails, and dawn ramps. Next: decompose true quiet-night dG into gut, EGP and
    insulin terms.
    **Decomposition (c90, 8,941 quiet-night 30-min windows of true glucose, skew −1.58):** the sharpest 5% of falls
    (median −30 mg/dL) start high (median 208), with absorbed insulin at 1.68× the night mean and EGP suppressed to 0.63,
    while Loop already delivers less (0.53×): insulin from earlier corrections is pulling a night-time high down. The
    sharpest rises (+17) start near 116 with low insulin and EGP at 1.15×. So the lean is how fast the sim corrects
    nighttime highs. From midnight glucose ≥ 200 the sim falls −82 mg/dL in 3 h against donors' −58 (LESSONS 51 data).
    In real people a night high often has a cause insulin cannot fully work through: a failing site, prolonged-high
    resistance, fat, illness. Next: whether those are under-sized at night.

80. **Night-time highs fall as fast with evidence-timed glucotoxicity or lower SG: the fall is insulin-driven.**
    Evidence/15 sizes hyperglycaemia-induced resistance at ≤ ~7% near 200 mg/dL. Onset is ~3–6 h (Fanelli 1995: −15%
    after 6 h at 243), persistence 1.5–10 h after normoglycaemia, and the 0.26 at 360 mg/dL fits the T1D points.
    - **Change:** the glucotoxicity state builds over 6 h and fades over 24 h, inside the studies' bounds (was 12 h both
      ways).
    - **Cohort c92 vs c90:** Hurst 0.153 → 0.190; mean 153.7 (151.4); 14 vs 16 of 30 (noise). The fall from a midnight
      glucose ≥ 200 is unchanged: −113 mg/dL at 3 h vs donors −58.
    - **SG ×0.5 (c93, toward Del Prato 1997's weaker T1D glucose effectiveness):** Hurst 0.248 (donors 0.247), but
      mean 166.5, TIR 60.7 and 6 of 30. The fall from highs is still −117. Rejected.
    So night-time highs come down by insulin, through Loop's corrections, faster than in donors. Open candidates: real
    corrections working less well than settings imply (site, absorption at the actual site, selection of nights that
    are high because insulin is not working), and donors' controller limits (max basal, correction range).
    **Split of the fast fall (c92):** after a quiet midnight at ≥ 200 mg/dL (median ~245), over 00–03 h:

    | | delivered, % of TDD | ΔG at 3 h | ΔG per 1% TDD |
    |---|---|---|---|
    | Donors (355 nights) | 6.6 | −65 | −10.2 |
    | Sim (112 nights) | 7.9 | −114 | −14.3 |

    The simulated Loop delivers 20% more into a night-time high, and each unit lowers glucose 40% more, which together
    is the 1.75× faster fall. The donors' −10.2 per 1% TDD is close to the 1800-rule ISF over 3 h. So simulated insulin
    (with glucose effectiveness on top) works harder at night-time highs than real insulin does. Real high nights also
    over-sample nights when insulin is not working (a poor site, resistance), which a healthy simulated body does not.
    Next: per-unit effect at night-time highs vs at normal glucose in donors, and the simulated site states on high
    nights.
    A within-person regression of 3-h ΔG on insulin delivered, by midnight glucose band, gives positive slopes in
    every band for donors and sim (Loop delivers more when glucose stays high). Observational dose-response is
    confounded by the controller and cannot show whether real insulin is weaker at highs.
    **Site selection does not explain it (c94; site states now logged in `truth.pump`).** 26% of simulated high nights
    (≥ 200 at a quiet midnight) are on a lipohypertrophic or failing site, against 20% of all nights. Those nights fall
    −107 mg/dL in 3 h against −114 on healthy sites, because Loop delivers more and overcomes the weaker site. That
    leaves per-unit insulin strength at high glucose (−14.3 vs −10.2 mg/dL per 1% TDD), which no evidence found so far
    sizes: κ = 0.15 fits the clamp literature (evidence/15), and Del Prato's weaker glucose effectiveness moves the
    levels (LESSONS 80). Open.

81. **Neither named term Pete allowed for night-time highs calibrates them without breaking the levels.** Target: the
    donors' −10.2 mg/dL per 1% of TDD delivered in the 3 h after a quiet midnight at ≥ 200 (sim −14.3; LESSONS 80).

    | Change (n 112) | per-unit at highs | mean | TIR | matched |
    |---|---|---|---|---|
    | none (c92) | −14.3 | 154 | 69 | 14 |
    | κ ×0.5 (c95) | −13.3 | 158 | 67 | 13 |
    | κ ×0, linear (c96) | −14.7 | 158 | 65 | 10 |
    | glucotoxicity size 0.26 → 0.52 (c97; Boden 1996 −55% bounds it) | −12.7 | 158 | 66 | 6 |

    κ barely touches the per-unit effect; doubled glucotoxicity moves it only a sixth of the way while lows fall to a
    third (t<54 0.06 vs 0.22). Defaults stay (κ ×1, size 0.26); `kappa_mult` and `glucotox_max` remain switches. The
    per-unit gap is open. Whatever makes real insulin weaker at night-time highs is not a uniform body parameter;
    a per-night or per-situation cause (a site that works poorly that night, missed insulin, unlogged late food) fits
    better than any global term.

82. **Grazing on the person's own eating clock turns the daytime quiet-time skew positive; late unlogged food is not the
    night-high answer.** Grazes were placed uniformly over waking hours. They now follow the donor's labeled eating
    clock over the person's waking hours, as snacks do: 21% fall after 20:00, 1% between 00 and 06.
    - **Cohort c98 vs c92:** daytime quiet-window 30-min skew −0.23 → +0.09 (donors +0.76), the first time the sim
      leans the donors' way by day; night-time-high fall per 1% TDD −14.3 → −13.3 (donors −10.2).
    - **Also:** Hurst 0.205, mean 155, TIR 66.6, CV 37.2; 11 vs 14 of 30, within the noise of LESSONS 63.
    - Late unlogged eating explains only a sliver of the night-high gap; the per-unit question of LESSONS 81 stays open.

83. **First use in LoopEval: paired candidate arms on simulated people (Pete: "use it in LoopEval").** The same 112
    people, seeds and life events run under the deployed controller (c98) and under each candidate's flags
    (`cohort.py --flags-json`); σ-gated flags use each person's own σ5 median from their baseline run (4.6–7.2
    mg/dL/5 min, p10–p90). `patient_sim/candidates.py` reports paired deltas with bootstrap CIs, on CGM and on true
    glucose, and the lift over the insulin-needs dial (×0.95 / ×1.05 arms):

    | | ΔTIR | Δt<54 | Δmean | lift over dial (CGM) | (true) |
    |---|---|---|---|---|---|
    | dial ×0.95 | −1.76 | −0.148 | | | |
    | dial ×1.05 | +1.53 | +0.028 | | | |
    | C30 stack | −0.25 [−0.86, +0.39] | −0.09 [−0.19, −0.01] | +1.0 | +1.31 [−0.09, +2.60] | +1.47 |
    | aIRC (C01) | −0.40 [−1.06, +0.27] | −0.11 [−0.19, −0.04] | +1.8 | +1.43 [+0.18, +2.48] | +0.96 |

    - **C30's reduction in lows matches replay** (Δt<54 at the operating point −0.087), and true glucose agrees
      (−0.10). The lows come off temp-basal people (−0.22); automatic-bolus people barely change (−0.03). The
      licence's TIR gain does not appear.
    - **aIRC** is the dial's pull-back with a smaller TIR price: positive lift where replay rated it neutral on most
      beds.
    - **Caveats:** 112 people × 14 days gives wide intervals. The sim's remaining shape gaps (meal plateau,
      night-high falls; LESSONS 66, 80–82) bear on exactly the situations these candidates act in.

84. **C30's parts, separately, behave as the ledger says; C31 is the sim's clearest dose-more result.** Same 112
    people and dial as LESSONS 83:

    | | ΔTIR | Δt<54 | Δmean | lift over dial (CGM) |
    |---|---|---|---|---|
    | C20 post-low rise-cut | −0.13 | −0.06 [−0.12, −0.01] | +0.2 | +0.85 [−0.15, +1.77] |
    | C29 σ band | −0.24 | −0.06 (true −0.10 [−0.20, −0.01]) | +1.3 | +0.81 [−0.96, +2.16] |
    | C23/C25 calm-high licence | +0.32 [−0.22, +0.86] | +0.00 | −0.7 | +0.31 [−0.62, +1.31] |
    | C31 calm-high target −20 | +0.64 [+0.09, +1.23] | −0.03 | −1.0 | +1.11 [−0.04, +2.22] |

    - **C20 and C29** are pull-backs that take the lows off at a smaller TIR price than the dial.
    - **The licence** adds TIR at zero lows cost, the ledger's verdict, but small here.
    - **C31** raises TIR significantly with lows unchanged.
    - **C30** (LESSONS 83) is the pull-backs' lows cut plus a licence gain too small to show.

85. **Stress scenarios: where each candidate earns or costs (Pete: "stress scenarios").** On day 4 one ground-truth
    event is injected into every arm alike (`--enable scenario_<name>`, `world._scenarios`):
    - illness: SI −30%, EGP +10%, 3 days;
    - exercise: 60 min at intensity 0.6, 17:00;
    - missed bolus: dinner eaten with no entry and no bolus;
    - site failure: dislodged at 14:00, until the person notices;
    - sensor fault: a 45-min false low of 40 mg/dL at 02:00.

    56 people × 8 days per arm; true glucose over the 72 h from day 4; Δ vs the baseline controller on the same
    scenario (95% bootstrap):

    | scenario (baseline) | C30 | C31 (−20) | aIRC |
    |---|---|---|---|
    | illness (TIR 53, >250 19%) | neutral | TIR **+1.9** [+0.6, +3.4], >250 **−1.3** [−2.5, −0.1] | neutral |
    | exercise (t<54 0.94) | t<70 **−0.48** [−0.96, −0.01] | neutral | t<54 **−0.27** [−0.51, −0.04], t<70 **−0.67** |
    | missed bolus | neutral | TIR +1.1 [−0.9, +2.7] | >250 **+1.1** [+0.3, +2.0] |
    | site failure (TIR 55) | TIR +2.0 [−0.3, +4.3], >250 −1.9 | neutral | neutral |
    | sensor false low | t<54 +0.14 [−0.05, +0.36] | >250 **−0.96**, max −19 | t<54 −0.08 |

    - **C31** pays where the person is resistant or under-dosed (illness; a missed bolus by trend), with no lows cost
      anywhere.
    - **aIRC** protects after exercise, the lows-prone case, but leaves an unbolused meal high longer: its weaker
      response to rising glucose.
    - **C30**'s lows protection shows on the exercise day; it trends toward helping on a failed site.
    - **During the false low** no candidate shows clear harm.
    - **Limits:** 56 people each, one event per person, so many intervals still include zero. The scenario sizes are
      single representative values from the component ranges.

86. **Bigger stress runs (Pete): 168 people at moderate size, plus mild (×0.5) and severe (×1.5) at 56.** True
    glucose, 72 h from day 4, Δ vs baseline on the same scenario; * = 95% bootstrap interval excludes zero.
    - **C31 (calm-high target −20):**
      - illness TIR **+1.36*** at moderate (168) and **+1.25*** severe;
      - missed bolus, growing with the unbolused meal: severe TIR **+1.63***, >250 **−1.03***;
      - one small cost: with a small unbolused meal (×0.5), t<54 **+0.20*** (it doses into a high that would have come
        down by itself).
    - **aIRC:**
      - exercise t<54 **−0.16*** and t<70 **−0.43*** (168);
      - missed bolus severe: >250 **+1.12***, confirming the cost of its weaker response to rising glucose.
    - **C30:** exercise t<70 **−0.29***; site failure TIR +1.54 [−0.09, +3.03].
    - **Deep false low** (60 mg/dL for 45 min): the pull-backs lose TIR, C30 **−1.38*** and aIRC **−1.25***. They believe
      the false reading and hold insulin back. This is a sensor-robustness cost replay cannot isolate.
    - **Severity:** where an effect exists it mostly grows with event size (C31 on missed boluses; aIRC's cost there).
      The mild events are mostly inside the noise.
    Analysis ran on gamepc (`stress2_an.py`); runs in `~/additive/runs/big_*`, `lvl*_*`.

87. **GLP-1 RA validation and injection timing.** 112 people, 14 days, against the same people off the drug (c98);
    true glucose; * = 95% bootstrap interval excludes zero.
    - **Semaglutide at 26 weeks reproduces ADJUST-T1D without tuning:**

      | | sim | ADJUST-T1D |
      |---|---|---|
      | TDD | −18.6%* | −20 to −23% |
      | bolus | −25%* | −30% |
      | basal | −16%* | −12 to −16% |
      | carbs eaten | −20.5%* | −22% |
      | carbs entered | −22.6%* | — |

      TIR +7.2*, mean −12 mg/dL*, t<54 −0.09*. The first two weeks on 0.25 mg do little: TDD −1.7%, TIR +1.1*.
    - **Tirzepatide:** TDD −22.8%, bolus −31%, carbs −26%, TIR +9.9*. The cost is lows: t<70 +0.66* and t<54 +0.09*,
      because rescue carbs go up 6.6 g/day. The phase-2 T1D trial's −42% TDD (6 weeks, pump users, exploratory) is larger than
      the model gives. Our escalation stops at 5 mg, and the dose reached in that trial was not checked.
    - **Hour of injection: no effect,** for weekly semaglutide (20:00 − 08:00: TIR +0.4, CI spans 0) and for daily
      liraglutide (TIR 5.9 vs 6.0). The saturating dose response (EC50 0.5, inferred) flattens even liraglutide's
      daily level swing to about ±7% of effect.
      Carbs scale by day, at the noon level. Within a day only gastric emptying and SI follow the drug level.
    - **Days since a weekly injection: a rhythm, larger for tirzepatide** (Pete: a Mounjaro user reports a difference the day
      after the injection).

      | | day 1 (peak) | day 6 (trough) |
      |---|---|---|
      | tirzepatide: effect | 1.09 | 0.86 |
      | tirzepatide: carbs | −57 g | −45 g |
      | tirzepatide: TIR vs baseline | +11.3 | +7.4 (±0.9 per day) |
      | tirzepatide: t<70 vs baseline | +0.6 to +1.1 on days 1–3 | — |
      | semaglutide: TIR vs baseline | ~+8 | +6.4 |

      The sizes follow from the inferred EC50 and the PK alone. No study measures outcomes by day since injection
      (evidence/16 §3). Treat them as a hypothesis the donor data could test, for donors on a known weekly agent.
    Scripts on gamepc: `~/additive/glp1_an.py`, `glp1_week.py`; runs `~/additive/runs/glp1_*`.

88. **The 5-min step-skew gap is the first hour of real meals, and per-person gastric emptying is an evidenced
    component that was never wired.** Donors' G7 step skew is +0.33; c98 reads +0.01 (KS p 1e-27, the worst-matched
    statistic).
    - **True glucose is not the problem:** the sim's true glucose skews +0.27. Its sensor noise is symmetric and
      carries about 60% of the step variance (CGM step SD 7.4 vs true 4.7), which dilutes the skew.
    - **Where the gap sits.** Each person's skew splits into additive shares by context: Σz³/N, by time since the last
      labeled pulse or manual bolus, with the ice labeler on both sides. Time shares match within a few percent.

      | Context | Donors | Sim |
      |---|---|---|
      | day, 0–1 h after an event | +0.35 | +0.18 |
      | day, 1–3 h | −0.01 | −0.06 |
      | night, 1–3 h | −0.01 | −0.04 |
      | quiet, > 4 h | ±0.02 | ±0.01 |
      | total | +0.37 | +0.05 |

      Real meals rise more sharply in the first hour and come down more gently.
    - **The median meal matches; single meals do not.** Isolated, announced, bolused meals, median Δ from onset: donors
      42 vs sim 42 at 120 min, within 1–2 mg/dL per 10 g at every 10-min point to 4 h. First-hour steps: donors skew
      +0.67, p99 24 mg/dL; sim +0.05, p99 19. Real meal-to-meal and person-to-person spread in rise speed is larger.
    - **Per-meal fast-liquid share (Beta, mean 0.2, `--set meal_fast_sd`):** SD 0.15 gives step skew +0.03 and SD 0.25
      gives +0.08. Paired outcomes are unchanged (TIR +0.15 [−0.44, +0.80]). Not the lever; the switch stays at 0.
      (Englyst 1999: rapidly available glucose explains 70% of glycaemic-response variance; no per-meal spread found.)
    - **Per-person gastric emptying (`--enable ge_var`).** Evidence/09 gives Vmax lognormal CV 30% (Samsom 2003,
      Hellmig 2006) and 28% of T1D adults delayed at ×0.6–0.8. It had never been wired: every person had Vmax 3.
      c100 vs same-code baseline c99_base (= c98 exactly):

      | | Baseline | ge_var | Donors |
      |---|---|---|---|
      | Statistics matched | 21 of 51 | 26 | — |
      | Glucose CV | 37.2 (fails) | 35.2 (passes) | 34.8 |
      | Glucose skew | 0.79 | 0.75 | 0.89 |
      | Box-Cox λ | 0.00 | 0.10 (now fails) | 0.00 |
      | Step skew, G7 | 0.01 | 0.00 | 0.33 |

      Paired outcomes are unchanged (TIR −0.1). Slow emptiers flatten their peaks, so CV improves while glucose skew
      falls. **Adopted as the default (Pete, 2026-10-16);** `--disable ge_var` turns it off. The skew and Box-Cox
      shortfall is now a lead for what is still missing. The units self-check keeps unit emptying (timing, not units).
    - **Donor quiet windows have labeler blind spots.** Half the pilot donors have at least one label-free stretch
      over 24 h (the max is 57 days). Sharp sustained daytime rises (> 20 mg/dL per 5 min, median +132 mg/dL to a
      peak of 290) with no label sit in those stretches and in disruption windows (generic disruption 18% vs 7% at
      random). With quiet limited to coverage (inter-label gap ≤ 18 h), donors still show 14 such rises per 1,000
      quiet daytime steps against the sim's 5 (labeler-defined). They are rare (about 0.1 per donor-day) and add
      little to the whole-record skew. Earlier quiet-window results (LESSONS 76, 78) used uncovered stretches; the
      daytime skew changes little with the coverage filter (+0.75 → +0.77).
    Scripts: `runs/2026-10-16-additive-vskew/` (vskew, quiet_dn, quiet_ctx, rise_*); on gamepc `~/additive/`
    `skew_contrib.py`, `meal_traj.py`, `sim_labeled_quiet.py`.

89. **Faster emptying cannot give the donors' meal shape; the default emptying centre stays at 3 kcal/min.** With
    per-person emptying on (c100), meals rise too slowly early but reach the right height. Raising the centre inside
    evidence/09's 2–5 kcal/min range (`--set ge_mult`, which scales Vmax and kempt) fixes the early rise and overshoots
    the plateau. Isolated, announced, bolused meals, labeler onsets, median Δ in mg/dL:

    | | 30 min | 60 min | 120 min | First-hour step skew | Step skew, whole record | Matched |
    |---|---|---|---|---|---|---|
    | Donors | 7 | 27 | 42 | +0.67 | +0.37 | — |
    | c100, centre 3.0 | 4 | 18 | 36 | +0.41 | +0.03 | 26 |
    | ×1.2 (3.6) | 5 | 23 | 49 | +0.16 | +0.08 | 22 |
    | ×1.4 (4.2) | 6 | 25 | 58 | −0.11 | +0.12 | 21 |

    Faster emptying also costs glucose CV (37.2 and 38.6 vs donors 34.8). Real meals rise early and plateau low: more
    glucose appears early and less in total, or insulin acts sooner at meals. No emptying speed reproduces both. Next
    candidates: bolus timing relative to eating, and early insulin action at meals.
    **Bolus timing is ruled out.** In the sim the labeler places onsets a median 3 min before true eating (IQR −24 to
    +12). Against labeled onsets, simulated boluses come later than the donors' (bolus − onset: +5 vs −0.5 min). A
    later bolus would raise the sim's early rise, which is already too low, so timing cannot explain the shape.

90. **The sim lacks sharp rises, not sharp falls, and its meals appear at a low-glycaemic-load pace; tracer-paced
    emptying brings the rises back but makes glucose too variable.** Daytime 5-min steps, labeler contexts, G7, per
    1,000 steps (c100 vs donors):

    | | 0–1 h | 1–2 h | 2–3 h | 3–4 h |
    |---|---|---|---|---|
    | rises > 15, donors | 63 | 32 | 25 | 24 |
    | rises > 15, sim | 36 | 22 | 16 | 14 |
    | falls < −15, donors | 30 | 33 | 27 | 23 |
    | falls < −15, sim | 24 | 31 | 27 | 22 |

    So the skew gap of LESSONS 88 comes from missing rises; the falls already match.
    - **Appearance timing against T1D tracer data.** Elleri 2013, 121 g evening meal: high-GL 25/50/75% appeared at
      56/100/153 min, low-GL 88/175/270. The sim's isolated mixed meals of 100–200 g run 100/176/260 (n 4), the low-GL
      pace; 40–70 g run 69/122/187. Mallad 2015 (T1D, mixed meal with 75 g glucose) peaks at 87.7 µmol/kg FFM/min at
      57 min, about 10 mg/kg/min of body weight; the sim peaks at 2.4–4.5.
    - **Faster emptying with carb sensitivity re-fitted** to the labeler's 1.21 g-eq per entered gram
      (`--set ge_mult=…,csf_mult=…`):

      | | Labeler | 70–100 g t25/t50/t75 | Rises > 15, 0–1 h | Step skew | Glucose skew | Box-Cox | CV | t<54 | Matched |
      |---|---|---|---|---|---|---|---|---|---|
      | Donors | 1.21 | — | 63 | 0.33 | 0.89 | 0.00 | 34.8 | 0.22 | — |
      | c100, ×1.0 | 1.19 | 66/123/184 | 36 | 0.00 | 0.75 | 0.10 | 35.2 | 0.15 | 26 |
      | ×1.4, CSF ×0.895 | 1.29 | 66/110/159 | 49 | 0.06 | 0.91 | −0.05 | 38.5 | 0.27 | 24 |
      | ×1.6, CSF ×0.84 | 1.24 | 58/100/149 | 54 | 0.09 | 0.89 | 0.00 | 39.2 | 0.37 | 21 |

      At ×1.6 the timing matches Elleri's high-GL meal, sharp rises reach 86% of the donors', and glucose skew and
      Box-Cox match. Glucose CV then overshoots (39 vs 35), and falls in hours 1–2 overshoot too (44 vs 33). Real
      people take fast meal appearance with less swing than the sim.
    - **Reading.** The gut evidence and the donors' sharp rises agree on faster appearance. What the sim cannot yet
      reproduce is the damping of the swing that follows. Candidates: insulin acting sooner at meals than the
      clamp-fitted curve; real meals split or spread (grazing through a meal); post-meal hyperglycaemic slowing of
      emptying (evidence/09 m_BG, built but off). Defaults are unchanged (centre 3.0, CSF_BLEND_CAL 1.25).

91. **Hyperglycaemic slowing of emptying, at its published size, does not survive carb-sensitivity re-fitting.**
    Setup: emptying ×1.6 (tracer pace, LESSONS 90) plus `ge_hyper` 0.45 (×0.74 at 8 mmol/L, Schvarcz 1997; ×0.56 at
    15–20, Fraser 1990).

    | Arm | Labeler g-eq/entered | Matched | Mean | CV | Glucose skew | Box-Cox | Meal Δ at 2 h | Rises > 15, 0–1 h |
    |---|---|---|---|---|---|---|---|---|
    | Donors | 1.21 | — | 151 | 34.8 | 0.89 | 0.00 | 42 | 63 |
    | c100 baseline | 1.19 | 26 | 155 | 35.2 | 0.75 | 0.10 | 36 | 36 |
    | c103, CSF ×0.84 | 1.09 | 33 | 151 | 33.5 | 0.67 | 0.15 | 31 | 35 |
    | c104, CSF ×0.93 | 1.13 | 30 | 154 | 34.0 | 0.67 | 0.13 | 34 | 35 |
    | c104, CSF ×1.0 | 1.19 | 26 | 155 | 33.8 | 0.68 | 0.15 | 33 | 38 |

    The 33 of 51 in c103 comes from meals the labeler reads as too small (1.09 vs 1.21). Calibrated to 1.19 it is back
    at 26. The slowing caps every high excursion, so glucose skew falls (0.68) and meals plateau low (33 vs 42). This
    repeats LESSONS 33 at the faster emptying. Defaults are unchanged. The gut alone cannot give the donors' shape
    (fast rises, a high but brief plateau, CV 35); the damping must come from elsewhere (insulin timing and action at
    meals, or how meals are eaten).

92. **Insulin around meals is close to the donors'; it does not explain the swing.** Isolated, announced, bolused meals
    (labeler onsets). Insulin delivered above the person's median 5-min delivery, per 10 g entered, mean (c100, 600
    meals, vs 7,470 donor meals):

    | Window (min from onset) | Bolus | −30–0 | 0–30 | 30–60 | 60–120 | 120–240 | Total |
    |---|---|---|---|---|---|---|---|
    | Donors | 1.30 | 0.37 | 0.36 | 0.31 | 0.32 | 0.52 | 1.88 |
    | Sim | 1.25 | 0.28 | 0.38 | 0.31 | 0.29 | 0.44 | 1.70 |

    Donors take about 10% more insulin per entered gram, mostly before the meal and as Loop's response after 2 h. The
    timing profile is otherwise the same. A 10% difference cannot turn the tracer-paced meals of LESSONS 90 (CV 39)
    into the donors' CV 35 at full meal height. The open question stays the shape of a real meal excursion: fast, high
    and brief (ACF zero-crossing 42 vs 55–60 min). Script: `meal_insulin.py` (gamepc `~/additive/`, scratch copy in the
    run dir).

93. **Tracer-paced emptying gives the donors' within-meal climb; renal clearance is not why highs fall fast.**
    - **Fastest 15-min rise per isolated, announced meal** (labeler onsets):

      | | p25 | p50 | p75 | p90 |
      |---|---|---|---|---|
      | Donors | 19 | 29 | 42 | 55 |
      | c100 default | 13 | 22 | 34 | 46 |
      | Emptying ×1.6, CSF ×0.84 | 17 | 28 | 39 | 53 |

      At the meal level, labeled pulses already match: size, duration, time to peak, phase mix (86/13% one/two phases
      vs 87/12%) and about 5.7 per day. So eating patterns are not the gap. The climb within a meal is, and tracer-paced
      emptying fixes it (LESSONS 90). What breaks at that pace is the swing that follows.
    - **Renal clearance at the UVA/Padova value** (`--set rcl_mult=0.167`; evidence/01 §4.3 corrected: Hovorka's
      0.67 and UVA's 0.11 mg/kg/min at 300 mg/dL disagree 6×). The 3-h fall from a quiet midnight at > 200 mg/dL is
      −94 vs −91 at the default, donors −65. Loop doses more into the longer highs and compensates. 23 of 51 matched;
      with emptying ×1.6, 21 (CV 41.7). The default stays Hovorka's. The 140–200 band already matches (sim −32,
      donors −33); only the > 200 band falls too fast.
    Script: `highins_sim.py` (gamepc), donor side `highins2.py`.

94. **Correction to LESSONS 80–81: per-unit insulin at night-time highs matches the donors once nights without
    recorded insulin are set aside.** After a quiet midnight at > 200 mg/dL, delivery 00–03 h as % of TDD:

    | | p10 | p25 | p50 | p75 | p90 | Nights < 2% |
    |---|---|---|---|---|---|---|
    | Donors | 0.0 | 0.0 | 6.6 | 10.1 | 14.7 | 30% |
    | Sim (c100) | 3.5 | 6.7 | 9.1 | 12.6 | 15.9 | 4% |

    - On donor nights with < 3% recorded, glucose falls only −31 mg/dL in 3 h.
    - With insulin recorded (≥ 3%): donors get 8.2% of TDD and fall −72; the sim gets 9.6% and falls −82. That is
      about −8.7 mg/dL per 1% of TDD in both.
    - So the "insulin 40% stronger at highs" of LESSONS 80 was the donor median diluted by nights with no recorded
      insulin. The sim delivers about 17% more into these highs; per unit it is right. κ and glucotoxicity tests
      (LESSONS 81) were chasing this artifact; their defaults stay.
    - **Recorded-insulin gaps are common in donors.** Of all donor 3-h windows (164,228), 5.5% have < 2% of TDD
      recorded. Of those, 60% have no dose record at all and 40% are zero temps; 58% overlap a listed disruption
      (generic disruption 3,171, loop offline 1,212). 164 of 168 donors have some; the top ten hold 38%. Glucose still
      falls on those nights, which a truly insulin-free T1D night would not do, so most are **unknown**, not absent,
      insulin (memory: pumpless disruptions).
    - **Consequence for validation.** The donor delivery statistics (zero_frac, p99, TDD CV, day/night, ac1) count
      unknown insulin as zero. Next: mask no-record stretches in `real_stats` and re-score.
    Scripts: `highins2.py` / `highins_sim.py`, `zero_nights.py` (run dir).

95. **Donor delivery statistics now treat no-record stretches as unknown insulin.** `validate.delivered_5min(...,
    mask_gaps=True)` (on for donors): any stretch of 30 min or more not covered by a basal record (zero-volume temps
    count as covered) is NaN. A block with no known insulin keeps only its glucose statistics; i032 has no dose
    records at all and had been scored as delivering nothing.
    - **Reference, before → after (p50 of 206 donors):**

      | Statistic | Before | After |
      |---|---|---|
      | TDD | 37.2 | 38.8 |
      | TDD CV | 16.4 | 15.7 |
      | p99 5-min dose | 1.67 | 1.87 |
      | zero_frac | 34.4 | 33.3 |
      | ac1 | 0.11 | 0.08 |
      | night_cv | 37.2 | 36.0 |
      | day/night | 2.06 | 2.06 |

      Worst single donor (i001): TDD 27.1 → 37.3, which matches its template (37.6; the templates' TDD comes from ice
      and was always gap-aware).
    - **Re-scored:** c99_base 22 of 51, c100 (per-person emptying, the default) 26. TDD now passes (KS p 0.91).
    - **Day/night is a real gap, not missing records** (sim 1.70 vs 2.06). The p99 5-min dose gap widens (1.38 vs
      1.87).
    - `real_pilot.csv` is the masked version; `real_pilot_unmasked.csv` keeps the old one (local and gamepc).

96. **Meal gaps now follow Camerlingo's GEV; the day/night gap is meal-time insulin concentration.** Hourly delivery
    (fraction of the person's mean hour, median over people; donors masked per LESSONS 95):

    | Hour | 04–05 | 12–13 | 18–20 |
    |---|---|---|---|
    | Donors | 0.52 | 1.35 / 1.30 | 1.29 / 1.35 / 1.30 |
    | c100 | 0.61 / 0.62 | 1.20 / 1.15 | 1.09 / 1.21 / 1.11 |

    - Labeled eating by hour matches (pulse grams within ±0.01 per hour). Donors' announced meals cluster tighter at
      lunch (8% and 7% of entries at 12 and 13 h) and dinner (7/8/7% at 18–20 h); the sim's are flatter.
    - **Fix:** `plan_day` drew the breakfast→lunch and lunch→dinner gaps from a Gumbel × 0.9 (ξ 0, no source for the
      0.9). Camerlingo 2021, the cited source, fits GEV with ξ −0.32 / −0.47, a bounded late tail. Draws: SD 92 →
      78 min, max 1,149 → 528 min. Now the default (`meal_gap_gev`; `--disable meal_gap_gev` restores the old draw).
    - **Cohort c106 vs c100:** day/night 1.70 → 1.74 (donors 2.06); dinner entries peak 7% at 19 h; 27 of 51 (noise);
      paired TIR +0.04, t<54 −0.10*.
    - **Still open:** donors put more of their insulin at meal hours and less before dawn. Bolus per entered gram
      matches (LESSONS 92), so the open items are the meal-time share of daily insulin and the night share.

97. **Delivered ÷ scheduled basal by hour: the sim is 5–20% higher before dawn; the body's basal shape is not why.**
    Median over people, c106 vs donors (masked):

    | Hour | 03 | 04 | 05 | 12 | 19 |
    |---|---|---|---|---|---|
    | Donors | 1.30 | 1.27 | 1.25 | 2.62 | 2.57 |
    | c106 (`prof_w` 0.5) | 1.39 | 1.39 | 1.51 | 2.46 | 2.43 |
    | c107 (`prof_w` 1.0) | 1.38 | 1.27 | 1.47 | 2.35 | 2.49 |

    - Under `prof_w` 0.5 the sim body needs 1.15× its schedule at night and 1.04× by day.
    - Following the schedule's shape fully (`prof_w` 1.0) flattens that to 1.06× but leaves pre-dawn delivery, and
      day/night (1.72 vs 2.06), where they were. 25 of 51 matched (noise); the default stays 0.5.
    - This repeats c69 (LESSONS 59) under the current model.
    - The gap is spread across hours, each of a few tenths: donors deliver more over schedule at meal hours and less
      before dawn. No single component accounts for it yet.
    **p99 5-min dose (sim 1.36 vs donors 1.87).** Donor delivery books each bolus whole at its start minute; the sim's
    `truth.delivered` spreads it at pump speed. Rebuilt from the sim's received records, the way donors are scored, p99
    is 1.42: the asymmetry is real but small. The rest is count: donors take 4.6 user boluses and 3.0 carb entries per
    day against the sim's 4.0 and 2.6, so they have more large 5-min bins.
    **Per-person counts match their donors** (c106, twin comparison against each template's raw rates): carb entries
    2.75 vs 2.86 per day (mean; corr 0.96) and user boluses 4.17 vs 4.17 (median; corr 0.91, mean 4.54 vs 5.36, the
    heaviest bolusers a little short). The cohort-level shortfall in the validation table comes from which templates the
    112 people drew, so the remaining p99 gap is mostly template sampling, not a component.

98. **Higher glucose effectiveness with tracer-paced meals shortens excursions at the cost of lows and long memory.**
    Emptying ×1.6, CSF ×0.84, SG ×1.5 / ×2 (0.0045 / 0.006, inside the 0.0013–0.022 range Pete allowed); vs c106 and
    donors:

    | | ACF zero-crossing | Hurst | t<54 | Mean | CV | Matched |
    |---|---|---|---|---|---|---|
    | Donors | 42.5 | 0.247 | 0.22 | 151 | 34.8 | — |
    | c106 default | 60 | 0.221 | 0.15 | 155 | 34.6 | 27 |
    | SG ×1.5 | 52.5 | 0.114 | 0.39 | 147 | 37.9 | 19 |
    | SG ×2 | 50 | 0.086 | 0.48 | 140 | 36.3 | 17 |

    Glucose effectiveness pulls every excursion back toward the rest level, including the slow wander the donors keep
    (Hurst) and the approach to lows. Rejected, as at the default meal pace (LESSONS 68). The shorter real excursions
    need a mechanism that acts on meal excursions specifically, not on all deviations.

99. **Person-by-person diagnosis of the failing statistics.** Each c106 person against the donor it was drawn from
    (`twin_fail.py`):

    | Statistic | Sim − own donor (median) | Spearman |
    |---|---|---|
    | step skew | −0.31 | −0.07 |
    | ACF zero-crossing | +15 min | +0.05 |
    | day/night | −0.29 | +0.12 |
    | Hurst | −0.01 | +0.13 |
    | p99 dose | −0.29 | +0.76 |

    - **Universal gaps:** step skew and decorrelation are short by about the same in every group (sensor, dosing
      strategy, announcer tercile), so their cause is structural, not tied to a kind of person.
    - **Shape statistics do not follow the individual donor** (rank correlation about 0.1). The sim reproduces the
      population spread of shape, not each person's own.
    - **Day/night splits by dosing strategy:** autobolus people run too flat (−0.49; sim 1.70 vs donors 2.09) and
      temp-basal people slightly peaked (+0.27; sim 1.90 vs donors 1.96). The day/night gap is the autobolus people's.
    - **How automatic boluses reach the plant (engine design, not a bug).** The candidate's automatic bolus is booked
      inside that step's temp-basal segment (`ClosedLoopSimulator`: keeps Loop's net-basal IOB accounting right), so
      the plant receives it as `basal`. One autobolus person's trace: 465 automatic boluses (29.3 U) after hand-over,
      all inside received 5-min basal segments; the delivered total is right.
      - Plant side, automatic boluses take the basal depot's PK without the 15% per-dose jitter. That is small.
      - Any plant-side "bolus" count excludes them. A first hourly bolus split here read as no overnight autoboluses,
        which was this artifact.
    Scripts: `twin_fail.py`, `hourly.py` (run dir and gamepc).

100. **Day/night follows meal speed: one mechanism behind three of the failing statistics.** Delivered insulin,
     day (10–22 h) ÷ night (00–06 h), median per person, by dosing strategy:

     | | c100 default | c102 tracer-paced meals (×1.6, CSF ×0.84) | c103 = c102 + hyperglycaemic slowing | Donors |
     |---|---|---|---|---|
     | temp basal | 1.79 | 1.93 | 1.86 | 1.96 |
     | autobolus | 1.65 | 1.83 | 1.66 | 2.09 |

     - When meals appear at the tracer pace, Loop's dosing lands at meal hours instead of trailing into evening and
       night. That closes most of the temp-basal gap and about 40% of the autobolus gap.
     - Together with LESSONS 90 and 93 (sharp rises, the within-meal climb), the donors' data point three ways to the
       same thing: meals appear faster than the default model lets them.
     - What blocks adopting the tracer pace is the swing that follows (CV 39 vs 35, more lows). The open component is
       what keeps a real fast-appearing meal from overshooting. It is meal-specific, since the global terms (glucose
       effectiveness, LESSONS 98; hyperglycaemic slowing, LESSONS 91) both fail.

101. **Entered absorption time is a measured per-person trait the sim does not have; it is not the meal brake.** The
     sim tells Loop 3 h for every entry (`absorption_entry_h`). Donors (67,499 entries, 152 donors):

     | Entered | Share | Median g | Bolused | Glucose < 80 at entry |
     |---|---|---|---|---|
     | 0.5 h | 14% | 15 | 75% | 14% |
     | 1–2.5 h | 6% | 20–32 | 90–99% | 2–7% |
     | 3 h | 75% | 25 | 90% | 6% |
     | 5 h | 5% | 30 | 79% | 7% |

     - The 0.5 h entries are mostly small fast-carb snacks, not rescues.
     - Per donor the 0.5 h share is a median 2%, p75 15%, p90 40%; 29 donors exceed 20%.
     - It is a candidate behavior trait (traits, not scripts): per-person shares of fast and slow entries, drawn by
       entry size.
     - It cannot be what damps the swing after main meals, which nearly all use 3 h. Not built yet.
     **Literature check for a meal-specific brake on appearance: none found.**
     - First-pass splanchnic extraction of oral glucose is about 10–25% (healthy; 16.4% intraduodenal vs 12.8% iv,
       n.s.). It depends mainly on prevailing glucose, so it acts like glucose effectiveness, which already fails
       (LESSONS 98). In T1D with insulin and glucagon matched it equals the non-diabetic value (Vella, Shah, Basu &
       Rizza 2008, Diabetes Care 31:2230).
     - Prandial insulin 20 min before the meal leaves T1D meal-glucose appearance unchanged (Pennant et al. 2008, as
       reported there). Insulin lowers the excursion mainly through EGP suppression, which the sim already times to
       tracer data (LESSONS 69–70, 75).
     So the brake is not in appearance or liver physiology. What remains are behavior (how much is eaten when glucose
     rises fast, corrections) and the controller's response.
     **Top-up boluses are not the missing brake.** Extra user boluses 15–120 min after isolated announced meals:

     | | Meals with a top-up | Extra U per 10 g | First top-up |
     |---|---|---|---|
     | Donors (7,351 meals) | 55% | 0.57 | 40–52 min |
     | c106 | 57% | 0.68 | 37–45 min |
     | c102 tracer-paced | 64% | 0.68 | 35–48 min |

     In both, top-ups rise with the meal's fastest 15-min climb. The sim tops up at least as often and a little more.
     With appearance, liver, renal, glucose effectiveness, bolus timing, meal insulin and top-ups all checked, the
     brake on fast real meals remains unidentified (`topups.py`).

102. **Entered absorption time is now per person; it does not move the cohort.** `templates.add_absorption_rates`
     gives each donor's shares of fast (≤ 1 h) and slow (≥ 4 h) entries, for small (≤ 20 g) and larger entries,
     leaving out entries made below 80 mg/dL. Rescues stay the sim's own 0.5 h log. Donors:

     | | Small entries (≤ 20 g) | Larger entries |
     |---|---|---|
     | Fast, median share | 5% | 1% |
     | Fast, p75 | 34% | 9% |
     | Slow, median share | 0% | 2% |

     - Each entry draws from the person's own shares on its own RNG stream, so all other draws are unchanged. The
       person enters 0.5 h, 5 h or the default 3 h.
     - **c109 vs c106 (paired, n 112):** TIR −0.07 [−1.12, +1.03], t<54 −0.08 [−0.19, +0.03]; 25 of 51 matched (noise).
     - It stays as a behavior trait because Loop's dosing after an entry depends on the entered absorption time
       (candidates that change carb modelling see it).
     - Templates: `templates_pilot.csv` locally carries the new columns (the old file is
       `templates_pilot_pre_abs.csv`). On gamepc they are in `templates_pilot_abs.csv`, leaving the file other roles
       read untouched.

103. **`--set announce_mult=x`: the same people announcing less, paired (frontier request, for reduced-announcement
     candidates).**
     - Every carb entry the person would have made (meals and snacks) is kept with probability x, on its own RNG
       stream (seed + 1213), drawn after all of the meal's other draws. Eating, activity, overrides, hand-dosed boluses
       and every other plan item stay identical to the baseline arm (checked on three people at x = 0.5 and 0).
     - A dropped entry's meal is eaten unentered and unbolused, and its pre-meal target override is dropped with it.
       No hand-dosed bolus replaces it.
     - Settings are unchanged, so the person's Loop sees the same therapy with less announced carbohydrate.
     - Runtime behavior (corrections, top-ups, rescues) responds to the resulting glucose, as it would in a real person.

104. **The G7 sensor cannot lose step noise without breaking its FDA fit; the skew gap is not a sensor fix.**
     Pete resumed shape matching (2026-10-17). Lesson 88 found the sim's sensor dilutes the step skew, and quiet-night
     steps hint the sensor is too noisy: SD 5.32 vs donors 4.75, lag-5 autocorrelation 0.38 vs 0.44. Variants
     re-sensored offline over c94 true glucose (`sensor_fit`, 30 people) and scored against FDA K213919 (bias and
     MARD by range, PARD 8.9%):

     | Variant | Step SD | MARD 70–180 | PARD | Fit loss |
     |---|---|---|---|---|
     | base (σ 2.8) | 7.24 | 7.1 | 9.3 | 2.9 |
     | σ 1.6 | 6.49 | 6.3 | 7.9 | 2.8 |
     | σ 1.6 + shared error 3.0 | 7.41 | 7.3 | 8.4 | 3.1 |
     | σ 1.6 + slow bias 5–7 | 6.9–7.0 | 8.3–8.9 | 9.4–10.4 | 5.6–6.0 |
     | smoothing 0.2 / 0.35 (`sensor_smooth`, new override) | 6.7 / 6.2 | 7.2 / 7.4 | 9.2 / 9.0 | 3.8 / 5.8 |

     - Lowering the fast noise loses in-range MARD.
     - Moving the error into the shared component restores MARD and the step noise with it.
     - A slow bias or device smoothing breaks accuracy in the low ranges: CGM-binned < 54 MARD rises to 17–23 (FDA
       16.0).
     - The G7 model already sits at its best FDA fit. The quiet-night difference is then more likely in true night
       glucose than in the sensor. Defaults are unchanged; `sensor_smooth` stays as an override.

105. **Bolus timing is not the missing piece: shifting every bolus 6.5 min earlier leaves the cohort shape unchanged,
     and does not damp the overshoot from tracer-paced meals.**
     - The labeler reads the sim's announced-meal boluses later relative to meal onset than donors' (labeled bolus
       time − labeled onset):

       | | p10 | p25 | median | p75 | ≥ 20 min early | −10 to −3 |
       |---|---|---|---|---|---|---|
       | donors (157, 35k meals) | −46 | −27 | −2.1 | +25 | 30.6% | 7.9% |
       | sim c106 | −40 | −20 | +5 | +30 | 20.6% | 11.7% |
       | sim `lead_shift=-6.5` (c110_lead) | −40 | −20 | 0 | +25 | 22.9% | 12.6% |

     - The shift moves the middle of the distribution, but not the early tail. Each person draws a category from the
       donor's median lead ("before" if < −5 min) and then a fixed window (before = −20 to −5 min). A donor whose
       typical pre-bolus is 30–40 min early gets at most 20 in the sim. That window has no per-person evidence and is
       a defect. Lesson 106 finds a second one (the windows quantize each donor's median).
     - Paired cohorts on frozen eefe53e (112 people, 14 days, against c109_abs):
       - **c110_lead:** 25 → 25 matched. t54 0.164 → 0.209 (donors 0.215), p_reach54 0.179 → 0.200 (0.200), lows/day
         0.92 → 0.83 (1.08). Step skew, ACF zero-crossing, day/night and p99 are unchanged.
       - **c110_lead_ge** (adds tracer pace `ge_mult=1.6, csf_mult=0.84`): 24 matched. The skew, Box-Cox and
         v_skew gains of tracer pace hold. CV is still 39.4 (c102_gem1.6 39.2, donors 34.8), and Hurst long-range
         still collapses (0.155 vs 0.247). t54 0.37 → 0.33: earlier boluses take off a little, not the overshoot.
       - Labeler g-eq per entered gram: c110_lead 1.19, c110_lead_ge 1.37 (c102 1.24, donors 1.21). The tracer arm
         without the shift (c102) reads at the donors' size, so its CV of 39.2 is not a carb-size miscalibration. The
         1.37 appears only once boluses move earlier, so it is how the labeler reads the meal.
     - Default stays `lead_shift = 0`. The timing windows are replaced in lesson 106.

106. **The labeler cannot see within-person bolus timing; give each person the donor's own median lead.**
     - Labeler error on sim meals (`lead_err.py`; labeled onset vs true eating start, c106 and c110, 2,190 meals):
       - onset error SD 26 min, so bolus-lead error SD 28 min, median bias +1 to +3 min;
       - within-person lead SD is 3.5 min true and 27 labeled.
     - Labeled within-person spread is therefore almost all labeler noise. It reads the same for the sim (median
       33 min) as for donors (35), so donors' true within-person spread cannot be measured this way.
     - The per-person median survives: about 200 meals average the noise down to about 2 min.

       | Per-person median lead (labeled, min) | q10 | q25 | median | q75 | q90 |
       |---|---|---|---|---|---|
       | donors (151) | −14.6 | −5.9 | −0.1 | +6.0 | +9.8 |
       | sim c106 | −10 | −5 | +5 | +15 | +19 |

     - The sim is too late at the top. The four windows map the donor's median to a category: 58 of 168 templates
       fall in "during", with medians +1 to +15, and every one of them gets 3–15 min (mean 9). "after" gets 15–45.
     - `--enable lead_own` (commit 5581b12) times every entered-meal and hand-dosed bolus at the donor's median
       minus the labeler's 2 min bias, ±4 min uniform. The ±4 min within-person spread is a placeholder: no
       measurement can see it, per the above.
     - Templates without a lead (11) keep the category draw. The draw count is unchanged, so the default reproduces
       HEAD exactly: planned events are identical on five people, and lead_own moves only bolus entries.
     - Paired cohort c111_leadown queued on frozen 5581b12.
     - **Result (c112, frozen 21d49eb, against c111):** at 15 min, 25 matched. At 23 min, 27 matched, and the
       labeled lead IQR is 50 min (donors 51). Lows moved to the donors: t54 KS p 0.24 → 0.50, p_reach54 0.10 → 0.36,
       CV 34.8 (34.75). Step skew, ACF zero-crossing, day/night and p99 are unchanged.
     - A −4.6 min shift on top (c113, for the per-person bias of +6.6 min against the +2 assumed) matched 26. The
       early tail gains a little (25.7% ≥ 20 min early, donors 30.6%), but 16.9% of sim boluses still label ≥ 45 min
       late (donors 12%). That late excess is not bolus timing: it is where the labeler puts the onset when glucose
       was already rising. Kept at no shift.

107. **Wear: duplicate donor readings, then per-person gap rates; 30 of 51 matched.**
     - **Definition fix.** 21% of G7 donors have > 5% of intervals under 2 min, the same reading uploaded twice
       seconds apart. `wear` counted readings, so those donors read up to 1.08 coverage. It now counts distinct 5-min
       slots (validate.core_stats; donors and sim alike). Donor median 0.977 → 0.974.
       - Step statistics were never affected: `runs_from_series` breaks a run at a short interval.
     - **Shared bug found on the way.** `traits._circadian_amplitude` turned the index into seconds with
       `view("int64") / 1e9`, which assumes nanoseconds. Under a pandas build that parses to microseconds, every
       donor's amplitude came out ~10× too large. It now uses `as_unit("ns").asi8`. With the fix, the donor table
       reproduces the old one exactly except `wear` (`real_pilot.csv` replaced; the previous one kept as
       `real_pilot_dupwear.csv`).
     - **The remaining wear gap is between-person.** Corrected G7 wear q10/50/90: donors 0.927 / 0.975 / 0.993,
       sim 0.947 / 0.971 / 0.981. Donors' short gaps (7–32 min) run 0.6 / 2.7 / 8.6 a day at p10/50/90, and long
       gaps (32 min–12 h) 0.06 / 0.18 / 0.47. The sim gave everyone the family rate.
     - **`--enable gap_own`** (453c0ba) scales the family's short and long bins by the donor's own whole-record
       rates (`templates.add_gap_rates`, `templates_pilot_gap.csv`). The family table equals the donor means
       (G7 3.88 / 0.23 a day), so the cohort mean is unchanged.
     - **c114** (lead_own + lead_sd 23 + gap_own, against c112_sd23 rescored with slot wear): 27 → 30 matched.
       wear KS 0.000 → 0.60, hurst_long 0.03 → 0.17, G6 v_sd 0.07 → 0.54, t54 KS 0.87. Gaps set where runs break,
       and the run-based statistics read through them.
     - **Still failing:** step skew (G7 0.01 vs 0.33), ACF zero-crossing 60 (42.5), day/night 1.69 (2.06), p99,
       TDD CV, lag-1 autocorrelation, between-day fraction, circadian amplitude, sigma_disp, volatility clustering.

108. **The sim's heavy 180–240 band is extra unannounced daytime appearance, not announced meals.**
     - **Where the extra CV sits.** Per-person median glucose percentiles, p25/p75/p90/p95/p98:
       - donors 112 / 181 / 226 / 255 / 289;
       - c114 114 / 189 / 236 / 264 / 291;
       - tracer pace (c102) 111 / 194 / 249 / 284 / 323.
       Even the baseline is too heavy at p75–p95, and faster emptying lifts the peaks further.
     - **Labeled meals, like for like** (ice labeler on both). Meal size matches: g-eq q25/50/75/90/98 18/26/41/61/93
       donors, 17/26/41/61/94 c114. Daily appearance does not: 182 g-eq donors vs 203 c114 (twin +6%), and 233 under
       tracer pace (twin +21%).
     - **The announced side matches** (per person, median): labeled announced g-eq per entered gram 0.87 donors vs
       0.90 sim; entered grams matched to a labeled meal 0.77 vs 0.80; g-eq per matched gram 1.15 vs 1.13.
       - The template's `carb_g_day` counts only entries the labeler matched to a meal, so it reads 23% below the
         grams entered. That is not an excess.
     - **The excess is unannounced and daytime.** Unannounced labeled appearance is 117 g-eq/day vs 93 (twin +19%;
       tracer +36%). By clock quarter, g-eq/day for donors → sim:

       | 00–06 | 06–12 | 12–18 | 18–24 |
       |---|---|---|---|
       | 22.3 → 23.1 | 23.0 → 33.8 | 26.5 → 32.2 | 31.0 → 35.0 |

       Nights match. Announced appearance runs 7–10% short in every daytime quarter.
     - **Sources of the sim's unannounced pulses** (nearest true event within −45/+30 min of the labeled onset):
       - no eating event: 58 g-eq/day, 2.3 pulses. Within 3 h of eating, 30 g-eq/day, mostly afternoons and
         evenings (meal tails read as second pulses). More than 3 h after, 28 g-eq/day, of which 15 at night.
       - unentered meals 13, grazes 16, snacks 13, proactive carbs 16 g-eq/day.
       - Proactive carbs are 1.6 a day, 21 g, eaten at a median CGM of 89 while falling 13 mg/dL per 15 min; 14% are
         taken above 120.
     - **Meal tails are not it.** After an announced meal of ≥ 20 g with no other entry within 3 h:
       - P(an unannounced pulse 45 min–3 h later) is 0.30 for donors (25,181 meals) and 0.32 for the sim (1,764).
       - Its size is 11.5 vs 11.9 g-eq, and the match holds in every entered-size band (20–40, 40–70, ≥ 70 g).
     - **Open.** The excess is in separate unannounced eating occasions (labeled 4.3/day vs 3.5). By g-eq, grazes,
       proactive carbs, snacks and unentered meals each contribute about 13–16 a day. Grazing is the least-evidenced
       of them (rate lognormal around 2/day, a judgement). Next: find a measurement of unlogged small eating, or of
       the donors' proactive carbs, before changing any of them.

109. **Grazing is not the excess, and fast emptying still fails without it.** `--set graze_keep=x` (eb785d3) thins
     planned grazes on their own stream; every other plan item is unchanged (checked on four people). Paired against
     c114 (30 matched), frozen eb785d3, defaults:

     | Arm | Matched | Mean | CV | TIR | t54 | Hurst long | p75/p95/p98 | Unannounced g-eq 06–12 |
     |---|---|---|---|---|---|---|---|---|
     | c114 (grazes 1.0) | 30 | 154.8 | 35.6 | 69.2 | 0.22 | 0.223 | 189/264/291 | 33.8 |
     | c117 (0.5) | 30 | 152.7 | 35.4 | 70.6 | 0.15 | 0.184 | 186/249/278 | 33.4 |
     | c116_g0 (0) | 31 | 148.9 | 33.8 | 72.4 | 0.21 | 0.185 | 181/244/269 | 31.6 |
     | donors | | 151.4 | 34.8 | 71.7 | 0.215 | 0.247 | 181/255/289 | 23.0 |

     - **Grazes move the total, not the shape.** Fewer grazes lower the level and the upper percentiles together, and
       long-range Hurst gets worse: small unlogged eating adds slow wander. Match counts differ within noise.
       Literature does not pin the rate either: unbolused snacks are common in youth on pumps (2009, n = 9), and AID
       youth miss 2.2 boluses a day (Laugesen 2024, via a press release). Neither separates nibbles from unentered
       snacks. Default stays at 1.0.
     - **The morning excess is not grazing.** Morning unannounced appearance stays 32–34 g-eq vs 23 in every arm.
       Its sources (lesson 108) are rises more than 3 h after eating (7.5 g-eq/day, from waking until breakfast),
       unentered meals (6.9) and proactive carbs (4.8). Announced morning appearance already matches (25.0 vs
       23.3–25.1). Next lead: the size of the waking rise before breakfast (the modulators' dawn component).
     - **Fast emptying fails on lows, not on highs.** With no grazes and tracer pace (c116_g0_ge), the upper tail
       matches (p95 254, donors 255; p98 294, donors 289), and skew passes (G6 v_skew KS 0.28). But t54 is 0.315,
       lows/day 1.50 (1.08), p_reach54 0.25 (0.20), and CV is 38.0. At half grazes (c116_g5_ge): CV 38.9, t54 0.35.
       Faster appearance makes Loop and the person dose into steeper rises, and the excess comes back as lows.
       Vmax stays 3.
     - **Where the morning excess sits** (c114 vs donors, unannounced g-eq/day 06–12, by time since the previous
       labeled pulse ended):
       - after an unannounced pulse: < 15 min 6.8 vs 4.1; 15 min–1 h 4.9 vs 5.2; 1–3 h 9.2 vs 5.0; > 3 h 5.5 vs 4.6;
       - after an announced pulse: within 0.7 g-eq/day of donors in every bin.
       - The first rise of the day (03–12, > 3 h without a pulse) is +2 g-eq/day (9.5 vs 7.4). The sim's are
         larger at 06–07 (median 27–31 vs 18–20 g-eq).
       The excess is chained unannounced rises in the morning. Their true sources: no eating and no low 6.8
       g-eq/day, unentered meals 4.6 (the labeler splits them), grazes 2.8, proactive carbs 2.5, snacks 2.3.
     - The dawn EGP bump is already off for anyone with a basal profile (LESSONS 51). The non-eating morning rises
       come from the remaining morning modulators: Visentin breakfast-hour SI, GH night-to-night variation, stress
       episodes, sleep-loss SI. Next: ablate each, measure the morning chain table, and compare each with its own
       evidence.

110. **The morning modulators do not make the chained rises.** Paired ablations against c114, frozen eb785d3
     (`--disable circadian | gh | stress | sleep`). Morning chained unannounced appearance (after an unannounced pulse,
     ≤ 3 h, g-eq/day):

     | Arm | Morning chained g-eq/day | Matched |
     |---|---|---|
     | c114 | 20.9 | 30 |
     | no circadian | 20.3 | 30 |
     | no GH | 20.6 | 29 |
     | no stress | 20.8 | 30 |
     | no sleep | 21.6 | 29 |

     - Every quarter's unannounced total is within 1 g-eq/day of c114 in every arm.
     - **Circadian classes and the 24-h amplitude.** Without the Visentin classes, `circadian_amp` matches (0.135 vs
       donors 0.131, KS 0.002 → 0.64), and mean, CV and TIR improve. Long-range Hurst falls (0.223 → 0.194). The
       classes add a daily shape that donors' records do not show at this amplitude. They are evidenced (Visentin
       2016), but a donor's tuned basal profile already carries their own diurnal need (LESSONS 48), so the two may
       double-count. Kept on: not a cohort-fit decision.
     - **Not the controller's rebound either.** Delivered insulin around unannounced labeled rises, as a share of
       the person's mean rate (median; −2 to −1 h / last hour / first hour after the onset; `pre_ins.py`):
       - chained: donors 0.77 / 0.60 / 0.78 (46,756 rises), sim 0.79 / 0.59 / 0.92 (3,818);
       - other: donors 0.77 / 0.52 / 0.71, sim 0.71 / 0.44 / 0.76.
       Insulin is cut before a rise as much in donors as in the sim. The chained share of unannounced rises is the
       same, 0.62 in both. The excess is a uniform surplus of daytime unannounced rises (lesson 108), not a chaining
       mechanism. The sim answers rises a little harder in the first hour (0.92 vs 0.78), the autobolus response.
       Open: the surplus has no single source; its parts are unentered meals, proactive carbs, grazes, snacks, and
       non-eating rises that no modulator ablation removes.

111. **Caffeine, built at its evidence, is too small to show (as budgeted).** `--enable caffeine` (0d64b90, off by
     default; modulators._caffeine):
     - **Who:** 64% daily drinkers [unverified]; about 2 cups/day of 95 mg; first cup ~07:30, later ones 10–16 h;
       10% of days skipped.
     - **PK:** one-compartment oral absorption at 3/h (peak 30–60 min); per-person t½ lognormal around 5 h (2–10).
     - **Effect:** SI −15% at the peak of a 200 mg dose (Keijzers 2002), linear in concentration, capped at −30%.
       Applied as the deviation from the person's own mean daily profile, since the habitual part lives in the
       donor's basal shape (evidence/11 §4.2), as with GH.
     - Drinkers' SI moves 9–24% around their own mean by day and dose. Every draw is on its own stream (seed + 202).
     - **c119** (frozen 0d64b90): the same-commit baseline reproduces c114 exactly. With caffeine: 29 vs 30 matched
       (noise). Morning unannounced appearance 33.9 vs 33.8 g-eq/day, chained 21.0 vs 20.9. Between-day fraction
       0.117 → 0.125 (donors 0.102); hurst_long 0.223 → 0.230 (0.247).
     - evidence/14 budgeted 5–10% of the daytime ACF gap. It is not the morning surplus. Kept as a switch.

112. **The sim's meals rise too slowly, and a bigger fast phase is not the fix.**
     - **Isolated announced meals** (G7, ≥ 10 g, nothing else within 4 h; `meal_trajectory.py` on c114 vs donors).
       Median CGM change from onset:

       | min | 30 | 60 | 90 | 120 | 150 | 180 | 210 | 240 |
       |---|---|---|---|---|---|---|---|---|
       | donors (5,484 meals) | +7 | +27 | +39 | +42 | +40 | +38 | +31 | +22 |
       | sim (437 meals) | +4 | +13 | +22 | +27 | +32 | +30 | +33 | +20 |

       - Per 10 g at 120 min: 10.9 vs 8.4. First-hour steps: SD 7.17 vs 5.78, skew 0.67 vs 0.32.
       - Biggest 15-min rise, median: 29 vs 20 mg/dL, at 45 vs 55 min.
       - Donors climb fast, plateau at 90–180 min, then fall. The sim climbs slowly into the third hour.
       - Uniformly faster emptying gets the climb but shortens the tail, and the lows overshoot (LESSONS 89, 109).
     - **A larger fast liquid phase** (`meal_fast`, LESSONS 44's 0.2), paired against c119_base (30 matched), frozen
       0d64b90:

       | Fast share | Matched | Skew | CV | TIR | t54 | Labeled g-eq / entered g |
       |---|---|---|---|---|---|---|
       | 0.2 (base) | 30 | 0.76 | 35.6 | 69.2 | 0.22 | 1.21 |
       | 0.3 | 25 | 0.80 | 35.7 | 66.0 | 0.18 | 1.18 |
       | 0.4 | 25 | 0.85 | 37.1 | 66.2 | 0.24 | 1.36 |

       Skew moves a little, but TIR falls and CV rises.
     - **What the donors' shape asks for.** A fast early climb, then a sustained plateau of 1.5–2 h at ~10 mg/dL
       per 10 g. Meals that are fast and also long imply more total appearance per gram over the first 3 h than the
       sim gives, with insulin not cutting it short. Candidates:
       - glucose appearance per gram (CSF) vs insulin action in the first 2 h: the labeler matches the pulse size
         per gram (1.21) but not its timing;
       - the meal-bolus insulin peaking too early relative to appearance in the sim.
     - **Lead: the body's insulin action, bounded on both sides.** The labeler's pulse is ΔG plus Loop's modeled
       insulin effect. The sim's body acts exactly on Loop's curve (LESSONS 20), so in the sim the modeled and real
       effects coincide. If real meal-bolus insulin acts later than Loop's curve, donors' CGM climbs faster early
       while the labeled pulse size stays the same. That is the observed pattern.
       - Lesson 20 bounds the other side: clamp-speed action (4% of the effect in the first hour) made Loop stack
         insulin and crash meals at 56 min.
       - Test an intermediate action (first-hour share ~10%, between clamp 4% and Loop 17%) against three things:
         this trajectory table, the first-hour forecast residual from replay (memory: forecast-residual =
         insulin tail), and insulin delivered around meals (LESSONS 92).

113. **Slower body insulin action brings the meal shape to the donors; the cohort statistics split.** `--set
     ins_p2=x` (disposal-action rate; default 0.05 fits Loop's adult curve, LESSONS 20). Timing only; the steady-state
     effect is unchanged. Paired against c119_base, frozen 0d64b90, 112 × 14 d.

     | | Donors | p2 0.05 | 0.03 | 0.02 |
     |---|---|---|---|---|
     | Isolated meal ΔCGM at 60 / 90 / 120 / 150 / 240 min | 27/39/42/40/22 | 13/22/27/32/20 | 19/34/37/43/24 | 17/31/39/39/20 |
     | First-hour step skew | 0.67 | 0.32 | 0.23 | 0.58 |
     | Matched | | 30 | 30 | 27 |
     | hurst_long (KS p) | 0.247 | 0.223 (0.17) | 0.200 (0.02) | 0.245 (0.23) |
     | ACF zero-crossing, min | 42.5 | 60 | 65 | 70 |
     | TIR | 71.7 | 69.2 | 68.7 | 67.3 |
     | t54 / p_reach54 | 0.215 / 0.20 | 0.22 / 0.20 | 0.17 / 0.20 | 0.18 / 0.20 |
     | Labeled g-eq / entered g | 1.21 | 1.21 | 1.25 | 1.22 |

     - The plateau and the tail now sit on the donors' at both slower rates: +37–43 at 120–170 min, +20–24 at 240.
       The first hour is still short (+17–19 vs +27). The labeled pulse size is unchanged, consistent with the
       labeler adding back Loop's modeled insulin.
     - **The cost is decorrelation.** Slower insulin lengthens positively correlated runs: the ACF zero-crossing
       goes 60 → 70 (donors 42.5), the opposite of what donors need. Hurst long is fixed at 0.02.
     - **Not adopted yet.** Lesson 20's constraint has to be re-checked first: replay found Loop's first-hour
       forecasts match real glucose closely. Under p2 0.02–0.03, the sim's Loop would see glucose climb faster than
       it forecast after every bolus. Next:
       - compare the sim's forecast residual at 30/60 min after meal boluses with the donors' (dosingDecision
         bgForecast vs CGM, same windows);
       - and insulin delivered around meals (LESSONS 92).
       Then decide with Pete: the meal shape argues for slower action, the ACF zero-crossing against it.
     - **The field correction test cannot separate these rates.** ICE after isolated correction boluses, using
       ice's step tables and extraction on both sides (`corr_ice.py`):
       - Selection: manual ≥ 1 U at BG ≥ 150, no carb entry from −3 h to +4 h, no other manual bolus within 4 h.
       - With all such corrections, ICE falls sharply afterwards in donors (−17 to −25 mg/dL/h per U, n = 711),
         because people correct during rises that then end.
       - Requiring steady CGM before the bolus (±10 mg/dL/h over 30 min) leaves 71 donor events, with ICE change
         per U near zero in every 30-min bin (median −3.9 to +2.8, SE 3.3–5.1). The sim has only ~9 such events
         per cohort.
       - Expected signatures on the linear body (ISF 55): Loop's curve minus the body's effect is +6 / +3–6 /
         −1 to −5 / −7 to −8 … mg/dL/h per U for p2 0.05 / 0.03 / 0.02. They differ by ≤ 7 per bin, inside the
         donors' noise.
       So lesson 20's field constraint does not pin p2 between 0.02 and 0.05. Its evidence was Loop over-dosing
       into meals at clamp speed (4% in the first hour); p2 0.03 still gives 12% at 60 min (Loop 22%).
     - **Appearance is not the slow part.** True Ra after isolated entered meals (c119_base; ≥ 20 g, median 48 g,
       nothing else eaten from −3 h to +6 h; `ra_traj.py`):
       - cumulative share at 30/60/90/120/180 min: 0.09 / 0.26 / 0.45 / 0.61 / 0.87;
       - t25/50/75 of 58/99/148 min, faster than Elleri 2013's high-GL meal (72/130/197; low-GL 95/178/270);
       - Ra peak at 58 min.
       The sim's CGM climbs half as fast as donors' in the first hour despite this, so what holds the rise back
       is removal: insulin action timing (p2), glucose effectiveness, or the meal bolus's absorption. With
       appearance at its evidence, the slower action rate becomes the leading explanation (the 121 g meal of
       LESSONS 89 sat at the low-GL pace because the energy ceiling binds large meals).

114. **Body insulin timing from evidence, not from Loop: clamp-speed action no longer crashes meals, and the meal
     shape gap is only partly timing.** Pete (2026-10-17): the simulator is calibrated to real patients, never to
     what Loop believes. LESSONS 20 broke that by fitting p2 to Loop's adult curve after Loop over-dosed meals
     against a clamp-speed body.
     - **Evidence for meal-sized doses.** Humalog 15 U (T2D, PMC7716902):
       - onset 45 min; early 50% tRmax 56 min; late 50% tRmax 269 min; duration 405 min;
       - glucose infused in the first hour 42 of 670 mg/kg, **6.3%** of the total.
     - **The body's first-hour share** (linear part): p2 0.05 ~14%, 0.03 ~12%, 0.02 ~10%; Loop's model 22%.
     - **Translating the clamp to real life.**
       - Pump sets speed absorption with wear: plasma tmax 55 → 45 min from day 0 to day 4 (Clausen 2009); onset and
         offset are earlier on day 4 than day 1 in T1D adolescents. Already modeled (device.site_state `abs_slope`,
         LESSONS 43).
       - Smaller doses absorb faster, but the evidence found is second-hand only (volume effect). Not modeled.
     - **Cohorts** (paired against c119_base, frozen 0d64b90):

       | p2 (p2e) | Matched | Meal ΔCGM 60/120 min (donors 27/42) | t54 | TIR | hurst_long |
       |---|---|---|---|---|---|
       | 0.05 (0.018) | 30 | 13/27 | 0.22 | 69.2 | 0.223 |
       | 0.04 | 26 | 15/32 | 0.19 | 66.4 | 0.234 |
       | 0.03 | 30 | 19/37 | 0.17 | 68.7 | 0.200 |
       | 0.025 (0.012), lesson 9's clamp fit | 26 | 18/32 | 0.23 | 68.0 | 0.192 |
       | 0.02 | 27 | 17/39 | 0.18 | 67.3 | 0.245 |

       - The match count moves non-monotonically across p2 (26–30): cohort noise, not a timing signal.
       - Lesson 20's crash (meals ending 25 mg/dL below baseline at 3 h) does not recur at clamp speed. The
         behavior, meal and defense components added since carry it.
       - Slower action moves the shape toward the donors': 60 min +13 → +17–19, 120 min +27 → +32–39. The first
         hour is still a third short of the donors' at every evidenced speed.
     - **Open.** The first-hour climb needs another component, not more insulin delay. Appearance runs at the
       high-GL tracer pace (lesson 113), so the remaining suspects are glucose effectiveness at meal onset, the
       sensor's lag, and what donors' isolated meals really are (larger true carbs than entered).
     - **Adopted (Pete, 2026-10-17): p2 0.025 by default** (78fcf44; p2E stays at its tracer value 0.010). The person's
       sensitivity is recalibrated end to end at the new timing, so the default cohort differs from the override arm.
       c124 (frozen 78fcf44, against c119_base):
       - 27 matched (within the 26–30 band);
       - meal ΔCGM 60/120 min +19/+35 (was +13/+27; donors +27/+42); first-hour step skew 0.48 (0.32; donors 0.67);
       - t54 0.17 (KS 0.63), lows/day 0.83, p_reach54 0.18; TIR 67.3, mean 156; labeled g-eq per entered g 1.22.
       - The self-check fails the same 4 of 8 bodies before and after (night below rest: the dinner tail in the
         night window accepted in LESSONS 75; failing since at least bcb5be0).
     - **What is left of the meal gap is a ~10-min delay, not a size.** Per 10 g entered (c124 vs donors):

       | min | 30 | 40 | 50 | 60 | 90 | 120 | 130 |
       |---|---|---|---|---|---|---|---|
       | donors | 1.9 | 3.4 | 5.2 | 6.8 | 10.2 | 10.9 | 10.8 |
       | sim | 1.4 | 2.7 | 3.8 | 5.0 | 8.9 | 11.5 | 11.7 |

       The plateau now matches. The sim reaches each early level ~10 min after donors (sim 60 ≈ donors 50).
       Lower glucose effectiveness is not the lever (SG ×0.5: mean 166, LESSONS 92). Candidates for a 10-min lead:
       - the gut's onset (first appearance in the sim at 9% by 30 min);
       - eating before the logged/bolused time in donors (meal start vs entry time);
       - sensor lag (sim G7 uses Vettoretti's G6 lag, median 3.8 min).
     - **Neither the sensor nor meal-time dosing makes the 10 minutes.**
       - The sim's G7 lag is 3.5 min, the G7's own apparent device lag (evidence/03).
       - Delivered insulin around announced meals ≥ 20 g, as a share of the person's mean rate (mean over meals;
         −1 h–0 / 0–30 / 30–60 min / 1–2 h / 2–3 h): donors 1.96 / 2.13 / 1.79 / 1.04 / 1.01 (31,475 meals);
         c124 1.72 / 2.22 / 1.89 / 0.98 / 0.79.
       Donors take more insulin before the onset and still climb faster. The remaining lead is in when the labeler
       places onsets relative to true eating. In the sim it is 2–3 min before eating (lesson 106). In donors it is
       unobservable: a meal that starts slowly (a drink, a first course) would put the labeled onset later and the
       measured climb steeper.

115. **Per-site absorption speed is real but does not move the decorrelation.** `--set site_cv=x` (6517b83, off by
     default): each infusion set draws its own absorption-speed multiplier, lognormal with SD x, on its own stream.
     Haidar 2013 measured a per-site tmax CV of ~27% (evidence/14 candidate 3; per-person spread A2 and set-wear
     acceleration were already built). c125 at 0.27 against c124 (frozen 6517b83):
     - 25 vs 27 matched (noise).
     - ACF zero-crossing 65 → 65 (donors 42.5); lag-1 ACF 0.041 → 0.032 (0.080).
     - Lows move to the donors: t54 0.165 → 0.209 (0.215), p_reach54 0.182 → 0.200 (0.200).
     - Between-day fraction 0.108 → 0.123 (0.102); hurst_long 0.233 → 0.251 (0.247).
     Kept as a switch. With evidence/14 candidates 3–7 built or measured, the remaining named candidate for the
     daytime decorrelation is unlogged small intake. Its rate is unknown for AID users, and lesson 109 found grazing
     moves the level, not the shape. The ACF zero-crossing stays the largest open structural gap.

116. **Quiet nights match; donors' quiet days hold more sharp rises, of which the labeler misses only a small part.**
     Labeler-quiet 5-min steps (no labeled pulse or manual bolus within 4 h; donors limited to labeler coverage
     ≤ 18 h; G7), c124 against the donors:

     | | donors night | sim night | donors day | sim day |
     |---|---|---|---|---|
     | step SD | 4.75 | 4.38 | 6.65 | 5.23 |
     | skew (median person) | +0.07 | −0.04 | +0.77 | +0.22 |
     | rises > 10 / falls > 10 per 1,000 steps | 19.4 / 26.9 | 15.3 / 20.5 | 51.9 / 41.1 | 23.9 / 29.3 |
     | rises > 20 per 1,000 steps | 3.6 | 1.8 | 14.4 | 3.6 |

     - Nights now match. Lesson 79's sim night skew of −0.44 was before the clamp-speed insulin and the grazing clock.
     - Sustained unlabeled daytime rises (≥ 30 mg/dL within 30 min, events ≥ 60 min apart): donors 0.35/day
       (median person 0.29), sim 0.19/day (0.17). Some donor eating escapes the labeler and sits in "quiet"; the
       sim's cleaner records get labeled more completely.
     - That asymmetry is +0.16/day, about a fifth of the sim's labeled unannounced surplus (+0.8/day, lesson 108).
       The rest of the surplus is real, and so is the donors' upward daytime quiet skew.
     - The daytime quiet gap is in sharp rises (4× at > 20), the signature of fast unlogged sugar, not of slow wander.
       With the surplus in labeled unannounced eating, the sim seems to have **too many medium unannounced eating
       events and too few small, sharp, quick ones** (juice, sweets). That points to the shape of unlogged intake
       (size, speed), not its total.

117. **Fast grazes do not make donors' quiet-day rises; those rises are real, sustained, and mostly never labeled.**
     - `--enable graze_fast` (8539793, off by default): grazes absorb as liquid sugar (kempt = kabs 0.08, as rescues).
       c126 against c124: 29 vs 27 matched (noise); quiet-day rises > 20 per 1,000 steps 3.6 → 3.3 (donors 14.4).
       Fast grazes are labeled as pulses, so they never sit in "quiet".
     - **Donors' sharp quiet-day rises** (> 20 mg/dL in 5 min, 3,333 steps, G7, labeler coverage ≤ 18 h):
       - not sensor jumps: 1% reverse on the next reading, 81% keep climbing (median next step +18);
       - not post-low: 4% start below 80; median start 162 mg/dL, 39% above 180;
       - mostly not a pulse whose onset the labeler placed late: the next labeled onset is a median 72 min later
         (25% within 30 min).
     - So donors have fast, sustained climbs, often from already-high glucose, that the labeler does not count as
       eating. The sim produces a quarter as many. Candidates to test next:
       - intake during an ongoing high, which the labeler cannot separate from the excursion (its pulse model needs
         a baseline);
       - absorption bursts from the pump site (bubbles, release of an occlusion: device `bubble_left`,
         `release_pending`);
       - stress or adrenaline surges.
     - **Whole-day sharp rises, and where the sim's come from.** All daytime 5-min steps (08–22, G7), per 1,000:

       | | rises > 10 | rises > 20 | falls > 10 | falls > 20 |
       |---|---|---|---|---|
       | donors CGM (136, 2.57 M steps) | 94.5 | 20.0 | 72.2 | 11.4 |
       | sim CGM (c124) | 68.6 | 10.7 | 62.2 | 9.1 |
       | sim TRUE glucose | 32.2 | 2.0 | 22.7 | 1.2 |

       - Donors' rises > 20 by starting level: 15.9 / 19.6 / 24.5 / 24.0 at < 120 / 120–180 / 180–250 / ≥ 250. Sim:
         6.6 / 8.5 / 13.0 / 22.6. The deficit is at normal levels.
       - About four-fifths of the sim's sharp CGM rises are sensor noise. Its true glucose almost never climbs faster
         than 4 mg/dL/min.
       - Donors' falls > 20 nearly match the sim's (11.4 vs 9.1), so their extra sharp rises (+9.3 per 1,000 against
         +2.3 for falls) are real glucose, not a noisier sensor. The sensor model sits at its FDA fit (LESSONS 104).
       - The step-skew, first-hour and quiet-day gaps are one deficit: **real glucose sometimes rises at > 4 mg/dL/min
         from normal levels, and simulated glucose does not.** A 10 g fast parcel (kempt 0.08) peaks near
         2–2.5 mg/dL/min in a 70 kg body.
     - **Next, against evidence:** the fastest real appearance. Liquid glucose and high-GI foods (juice, soda, white
       bread) have early gastric delivery bursts (Calbet 1997) and peak Ra in 15–30 min. The sim's meals give their
       liquid share no per-food spread, and fast unlogged drinks are labeled as pulses (graze_fast above). The open
       question is which real foods produce > 4 mg/dL/min rises from euglycaemia, and how often per day.

118. **Per-meal spread of rapidly available glucose makes real fast rises, and brings fast falls with them.**
     `--set meal_fast_sd=x`: each meal's fast-liquid share is Beta with mean 0.2 and SD x. Englyst 1999: rapidly
     available glucose explains 70% of glycaemic-response variance and ranges widely between foods; no per-meal
     SD is published. Paired against c124, frozen 8539793:

     | | c124 | SD 0.25 | SD 0.35 | donors |
     |---|---|---|---|---|
     | true rises > 20 / 1,000 daytime steps | 2.0 | 5.1 | 8.3 | — |
     | CGM rises > 20 / falls > 20 | 10.7 / 9.1 | 12.8 / 10.1 | 15.4 / 11.6 | 20.0 / 11.4 |
     | glucose skew (KS p) | 0.75 (0.000) | 0.84 (0.26) | 0.92 (0.02) | 0.89 |
     | G6 step skew (KS p) | 0.089 (0.06) | 0.133 (0.28) | 0.063 (0.03) | 0.238 |
     | CV | 35.4 | 36.8 | 38.3 | 34.8 |
     | t54 | 0.17 | 0.21 | 0.28 | 0.215 |
     | hurst_long | 0.233 | 0.188 | 0.187 | 0.247 |
     | matched | 27 | 28 | 26 | |

     - At SD 0.25, glucose skew and G6 step skew pass for the first time at normal emptying pace. Labeled pulse per
       entered gram stays 1.21.
     - **The cost is the same as every faster-meal arm** (LESSONS 89, 109, 112): CV rises and long memory weakens.
       Donors gain sharp rises without the falls (falls > 20 match at 11.4); the sim adds both. A high-fast meal
       in the sim has little slow carbohydrate left, so it runs out early while Loop's insulin is still acting.
       That suggests real fast meals keep a sustained tail: total meal size or fat/protein slowing, not a
       smaller slow share.
     - Not adopted. Next: let the fast share add to the meal instead of displacing its slow part (e.g. a sugary
       drink with the meal), and compare falls.

119. **A sugary drink with the meal, food intact, is weaker than the per-meal spread and costs the same.**
     `--set meal_drink_p=x` (631df2f, off by default): on that share of main meals, a drink takes
     `meal_drink_share` (0.4) of the carbohydrate as the fast phase; the food keeps its own 20% fast share and its
     slow tail. c128 against c124:

     | | c124 | p 0.2 | p 0.4 | donors |
     |---|---|---|---|---|
     | matched | 27 | 24 | 23 | |
     | true rises > 20 / 1,000 | 2.0 | 3.0 | 3.8 | — |
     | CGM rises / falls > 20 | 10.7 / 9.1 | 11.4 / 9.6 | 12.5 / 10.0 | 20.0 / 11.4 |
     | CV | 35.4 | 36.4 | 37.3 | 34.8 |
     | hurst_long | 0.233 | 0.189 | 0.191 | 0.247 |

     - Keeping the food's tail does not stop the falls. In every faster-meal arm so far (emptying ×1.6, fast phase
       0.3–0.4, per-meal spread, drink), CV rises and long memory weakens together.
     - The common factor is not meal composition but what follows a fast rise in the sim: Loop and the person's
       response to it. Donors gain fast rises with no extra falls. Next: compare insulin delivered in the hour after
       a sharp rise (> 20 mg/dL / 5 min), donors vs sim (c127_fsd25). Then compare what glucose does 1–3 h later.
     - **What follows a sharp rise** (first daytime CGM step > 20 mg/dL / 5 min within 60 min, starting < 180;
       `after_sharp.py`):

       | | events | insulin / mean rate 0–30 / 30–60 / 60–120 min | ΔCGM +30 / +60 / +120 / +180 |
       |---|---|---|---|
       | donors | 19,512 | 2.89 / 1.20 / 1.01 | +42 / +32 / +19 / +16 |
       | c124 | 543 | 2.63 / 1.50 / 1.17 | +30 / +37 / +24 / −1 |
       | c127_fsd25 | 617 | 2.67 / 1.60 / 1.10 | +37 / +45 / +23 / −1 |

       Donors' fast rises peak within 30 min and hold +16 at 3 h. The sim's keep climbing to 60 min, Loop doses into
       the late climb (+25–35% more insulin at 30–60 min), and glucose returns to its start by 3 h. The missing
       shape is fast-early and held-late together (as LESSONS 66). Next: the Dalla Man slow late emptying phase
       (`meal_slow`, kmin 0.008) combined with the per-meal fast spread.

120. **Fast spread plus a slow late phase: 31 matched, with the CV cost gone.** Per-meal fast share (Beta SD 0.25,
     LESSONS 118) combined with the Dalla Man slow late emptying phase (`meal_slow`, share emptied at kmin 0.008).
     c129 against c124, frozen 631df2f:

     | | c124 | spread + slow 0.15 | spread + slow 0.30 | donors |
     |---|---|---|---|---|
     | matched | 27 | **31** | 23 | |
     | glucose skew (KS p) | 0.75 (0.000) | 0.85 (0.08) | 0.81 (0.02) | 0.89 |
     | G6 step skew (KS p) | 0.089 (0.06) | 0.118 (0.14) | 0.113 (0.02) | 0.238 |
     | CV (KS p) | 35.4 (0.12) | 35.8 (0.14) | 34.2 (0.82) | 34.8 |
     | TIR (KS p) | 67.3 (0.006) | 67.9 (0.09) | 69.8 (0.25) | 71.7 |
     | t54 / lows/day | 0.17 / 0.83 | 0.15 / 0.83 | 0.15 / 0.83 | 0.215 / 1.08 |
     | hurst_long | 0.233 | 0.204 | 0.212 | 0.247 |
     | CGM rises / falls > 20 | 10.7 / 9.1 | 11.8 / 9.8 | 10.5 / 9.0 | 20.0 / 11.4 |
     | labeled g-eq / entered g | 1.22 | 1.22 | 1.08 | 1.21 |

     - At 0.15 the faster-meal CV cost is gone, and skew, step skew and TIR pass. At 0.30 the labeler reads meals
       smaller (1.08), which is off-calibration.
     - Still open: after a sharp rise glucose returns to its start by 3 h (−6 vs donors +16), and the ACF
       zero-crossing stays 60–65. Sharp rises are still half the donors'.
     - Evidence status: the per-meal spread is qualitative (Englyst 1999, no per-meal SD published); the slow phase
       is in Dalla Man 2006's meal model (kmax/kmin), but the 0.15 share is a judgement. Default decision: Pete.

121. **The 3-h hold after fast rises splits by entry; the entered ones are over-insulinized up front.** After a
     sharp daytime rise (> 20 mg/dL / 5 min, start < 180), by whether a carb entry falls within ±30 min:

     | | share | insulin / mean rate 0–30 / 30–60 / 60–120 | ΔCGM +30 / +60 / +120 / +180 |
     |---|---|---|---|
     | donors, entered | 0.33 | 3.76 / 0.85 / 0.86 | +50 / +37 / +20 / +17 |
     | donors, not entered | 0.67 | 2.46 / 1.37 / 1.09 | +37 / +30 / +19 / +16 |
     | c129_s15, entered | 0.22 | 4.57 / 1.31 / 0.63 | +56 / +57 / +10 / −25 |
     | c129_s15, not entered | 0.78 | 2.20 / 1.58 / 1.25 | +31 / +30 / +17 / −3 |

     - Entered fast meals in the sim get 22% more insulin in the first 30 min, peak later, and end 25 below their
       start. Unentered rises get Loop's later insulin (30–120 min) and also don't hold.
     - Night highs (> 200 at midnight, no event within 3 h) now fall −75 over 3 h with insulin (was −92 on old
       timing; donors' per-unit matched in LESSONS 94). The general "highs fall too fast" gap of LESSONS 81–92 has
       mostly closed with the clamp insulin timing.
     - Next: the entered-meal bolus in fast meals. Candidates are the person's bolus size against what they ate
       (count bias, calculator over-ride) for high-fast meals, and whether donors' entered sharp rises are late
       entries (bolus after the rise).
     - **Not late entries in donors.** The entry falls a median 7 min before the sharp rise in donors (quartiles −19 /
       +6) and at 0 min in the sim (−16 / +14). The sim's fast meals start rising at or before their bolus; together
       with 22% more insulin in the first 30 min, that points at Loop's automatic dosing stacking on the meal
       bolus while glucose is already climbing. Next: split the 0–30 min insulin into the person's bolus and
       Loop's automatic delivery, donors vs sim.
     - **Split of the insulin after entered fast rises** (manual vs automatic, each per person mean rate, windows
       −30–0 / 0–30 / 30–60 / 60–120 min; `split_ins.py`):
       - donors (6,377): manual 2.70 / 2.39 / 0.42 / 0.41; automatic 0.53 / 1.45 / 0.44 / 0.46;
       - c129_s15 (123): manual 1.62 / 2.79 / 0.70 / 0.18; automatic 0.80 / 1.34 / 0.49 / 0.40.
       Loop's automatic delivery matches; the stacking guess above is wrong. The difference is the person's bolus
       timing around fast meals. Donors deliver more of it before the rise, the sim at or after it, so the sim's
       bolus acts later into a meal whose fast carbohydrate is used up early. The sim's bolus timing is one
       per-person distribution for every meal (lead_own, LESSONS 106). Donors' fast-rising entered meals carry
       earlier boluses than their meals overall (labeled median lead −2 min), so people may pre-bolus more for
       fast foods, or fast foods may be the ones eaten after a pre-bolus. Open: whether bolus lead depends on the
       food in donors (lead by first-30-min rise size).
     - **Donors do not pre-bolus by food.** Median labeled bolus lead by within-person meal-speed quartile (peak
       appearance per g-eq): donors −4.1 / −1.9 / −0.3 / −1.8 min, slowest to fastest (35,373 meals). So no
       food-dependent timing to model. The sim runs 0 / +5 / +5 / 0, i.e. 3–5 min later in every quartile. That is
       the labeler-bias residue of LESSONS 106 (+6.6 per person vs the +2 subtracted); correcting it (c113,
       lead_shift −4.6) was neutral on the cohort statistics. With faster meals now in the default, that late
       residue meets fast appearance. Worth re-testing the −4.6 correction on the new meal defaults.
     - **The lead correction does not fix it** (c130, frozen 81b1865; the base reproduces c129_s15 exactly, 31).
       lead_shift −4.6: 27 matched; entered fast rises still end −28 at 3 h (base −25; donors +17); sim lead medians
       −5 / +5 / +5 / −2.5 by speed quartile. Not adopted.
     - What remains: the sim's entered fast meals are over-insulinized for the carbohydrate they deliver. The
       person's bolus is sized to the entry (CR × entered grams), and so are donors'. The difference is what the
       entry covers: if donors' fast-rising entered meals carry more total carbohydrate or a slower tail than
       their entries (under-counting, fat/protein), they hold; the sim's high-fast meals end. Next: compare labeled
       g-eq per entered gram for fast-rising entered meals only, donors vs sim.
     - **Per-meal size and duration match at every speed.** Announced meals (entry ≥ 10 g) by within-person
       meal-speed quartile, slowest → fastest (donors 38,558 meals vs c130_base 2,462):
       - labeled g-eq per entered g: 1.62 / 1.35 / 1.02 / 0.65 vs 1.48 / 1.37 / 1.12 / 0.68;
       - duration: 3.25 / 2.50 / 1.67 / 1.08 h vs 3.64 / 2.48 / 1.77 / 1.07;
       - bolus ratio 1.0 throughout in both.
       The meal model now reproduces the donors' meal-to-meal spread of speed and size. The −25 at 3 h after entered
       sharp rises is a narrow selection (~120 sim events vs 6,377), not a per-meal mismatch. Left open.

122. **Day/night on the new defaults: too much pre-dawn insulin and a late dinner.** Hourly delivered insulin as a
     share of the person's mean (c130_base vs donors, `hourly.py`):
     - **Night:** 04–05 h is 0.58–0.68 (donors 0.52); 06 h is 0.75–0.77 (0.60). LESSONS 57's excess dawn-hour insulin
       is still there.
     - **Evening:** 17–18 h is 1.0–1.1 (donors 1.14 / 1.29); 19–20 h is 1.26–1.29 / 1.1 (1.35 / 1.30). The sim's
       dinner insulin starts an hour later.
     - The ratio is 1.59 (temp 1.66, autobolus 1.57) vs donors 2.04; the gap splits about evenly between pre-dawn
       and early evening.
     - Leads:
       - the sim's dinner clock (GEV lunch → dinner gap, LESSONS 96) against the donors' bolus clock at 17–18 h;
       - the pre-dawn excess against the body's dawn need (basal profile shrunk halfway, LESSONS 48) and Loop's
         reaction to it.
     - **Not the meal clock.** Per-person median hour of the largest labeled pulse in each window (B 04–10.5,
       L 10.5–15.5, D 15.5–22), q25/50/75:
       - donors 7.58/8.00/8.34, 12.71/13.00/13.25, 18.71/19.08/19.50;
       - c130_base 7.67/8.04/8.52, 12.61/13.17/13.58, 18.58/19.08/19.50.
       Dinner is on time. The donors' larger 17–18 h insulin is not a dinner bolus at a different hour. Open:
       pre-dinner dosing (Loop on afternoon rises or evening basal, the donor's own schedule) against the sim's.
     - **Manual vs automatic by hour** (share of the person's mean hourly total, median over people; `hour_split.py`):

       | | 00–05 auto | 12 manual | 19 manual | 08–22 auto |
       |---|---|---|---|---|
       | donors (168) | 0.64 → 0.49 | 0.61 | 0.62 | 0.58–0.73 |
       | c130_base (112) | 0.72 → 0.59 | 0.46 | 0.43 | 0.63–0.74 |

       - The sim takes less of its insulin as lunch and dinner boluses and more as Loop's night delivery. Night manual
         is ~0 in both.
       - The slow late emptying phase adopted in LESSONS 120 moved some of this: day/night 1.68 (c124) → 1.59
         (c129_s15). 15% of each dinner now absorbs into the night, and Loop covers it there.
       - Two open pieces:
         - meal bolus size at the main meals (0.43–0.46 vs 0.61–0.62 at the peaks, with daily manual units
           matching);
         - the night share of what dinner leaves behind.
         Neither is a single knob: the slow phase helps the cohort count (27 → 31) while it costs day/night.

123. **Night entries come from late main meals, not snacks; the donors' own meal clock is too blurred to fix it.**
     - **`--enable entry_clock`** (12b96af, off by default; `templates.add_entry_hours`, `templates_pilot_entry.csv`):
       snack entry chance by the donor's own entry-vs-eating clock. c131 against c130_base: 29 vs 31 matched;
       entered-gram shares night / B / L / D 0.08 / 0.18 / 0.32 / 0.39 (base 0.07 / 0.18 / 0.33 / 0.38; donors
       0.04 / 0.15 / 0.34 / 0.44); day/night 1.589 (1.594). No effect.
     - **What the sim's night entries are:** 201 of 280 belong to main meals and 70 to snacks. 7.6% of simulated main
       meals are eaten 22–04 h (5.8% 22–24 h, 1.8% after midnight). The dinner time is lunch + GEV gap with lunch
       = breakfast + GEV gap (LESSONS 96), and two summed gaps give a long late tail.
     - **`--enable own_clock`** (built, off; `templates.add_meal_clock`, `templates_pilot_clock.csv`): main meals
       around the donor's own median hour. Medians match the sim already (B 8.07, L 13.05, D 19.13 h). The
       within-person SDs (B 1.67, L 1.33, D 1.75 h) are near a uniform spread over each window (D 1.9 h): the
       largest pulse per window mixes snacks and labeler noise. A normal at 19.1 ± 1.75 h puts ~5% of dinners
       after 22:00, as now, so it was not run.
     - Open: a clean measurement of dinner-time spread. Candidates are bolus times with entries ≥ 30 g, which need
       no labeler, and evidence (Camerlingo's day-to-day dinner SD).
     - **Clean dinner timing, from entries** (day's largest entry ≥ 30 g after 15:30; `dinner_entry.py`):
       - donors (138): median hour q25/50/75 18.37 / 19.04 / 19.72; within-person SD 1.56 h; 5.4% of dinners
         after 22:00;
       - c130_base (51): 19.10 / 19.67 / 20.22; SD 2.13 h; 15.3% after 22:00.
       The summed GEV gaps make the sim's dinners late and wide.
     - **`own_clock` from entries** (19ac07c; `add_meal_clock` now uses the largest entry per window: B ≥ 15 g,
       L ≥ 20 g, D ≥ 30 g; NaN windows keep the population draw). c132 against c130_base:
       - fixed: dinner SD 1.55 h (donors 1.56); night entered share 0.03 (0.04); day/night 1.59 → 1.73 (2.06);
         hurst_long 0.204 → 0.245 (0.247); glucose skew 0.85 → 0.89 (0.89);
       - broken: 24 vs 31 matched; t54 0.149 → 0.118 (KS 0.009; donors 0.215); lows/day KS 0.02; night CV
         31.9 → 29.3 (36.0); circadian amplitude 0.152 → 0.160 (0.131); lunch share of entered grams 0.38 (0.34).
     - **Correction: night glucose is not too quiet.** `night_cv` is the night-to-night CV of overnight delivered
       insulin (LESSONS 55), not glucose. On clean nights (no entry 22–06 h, 00–06 h CGM; `night_parts.py`):

       | | g0 median | SD of g0 | SD of 0→6 h change | within-night SD | min < 70 | max > 250 |
       |---|---|---|---|---|---|---|
       | donors (15,924) | 150 | 50.7 | 56.5 | 22.6 | 18.9% | 18.5% |
       | c130_base | 154 | 48.4 | 55.7 | 27.2 | 18.9% | 25.2% |
       | c132_clock | 161 | 49.5 | 55.5 | 25.9 | 18.3% | 24.8% |

       Simulated nights already match the donors' glucose structure, with a few more highs. What the own clock
       removes:
       - night-to-night variation in overnight insulin (late dinners had supplied it; 29 vs donors 36%);
       - some of the overall lows (t54 0.12 vs 0.215).
       Not adopted. The next leads are night-to-night insulin variation (overnight overrides, site and absorption
       days) and daytime lows.
       Breakfast from entries (8.8 h) is later than from labels (8.1 h): early breakfasts go unentered.

124. **Night-to-night overnight insulin: donors' Loop answers night glucose more strongly.** Per person, overnight
     (00–06 h) delivered insulin per night against mean night CGM (`night_ins.py`; donors' unknown-insulin bins
     masked):

     | | insulin CV | R² on night glucose | CV explained (r·CV) | residual CV |
     |---|---|---|---|---|
     | donors (168) | 0.393 | 0.61 | 0.31 | 0.231 |
     | c130_base (112) | 0.286 | 0.51 | 0.20 | 0.177 |

     - Night glucose varies alike in both (lesson 123's clean-night table), but donors' overnight insulin moves
       ~1.5× as much with it, and also varies more independently of it.
     - The controller is the same Loop and the settings come from the same donors. So either the sim's glucose
       varies on time scales Loop answers less (slow drifts vs donors' sharper night moves), or the settings Loop
       acts on differ (ISF, max basal, override use at night). Next: the controller's own gain on both sides,
       overnight insulin above scheduled basal per mg/dL of forecast excess, using dosingDecision forecasts for
       donors and the trace for the sim.
     - **Not the controller's gain.** Overnight (00–06 h, 30-min bins, CGM 120–300) delivered minus scheduled basal
       (manual boluses excluded), regressed on CGM; slope × mean ISF (`ctrl_gain.py`):
       - donors (167): 0.264/h (q25/75 0.19 / 0.35); excess at 200 mg/dL 0.53 U/h;
       - c130_base (103): 0.281/h (0.17 / 0.40); 0.65 U/h.
       Loop's response per unit of night glucose matches; if anything the sim gives a little more at 200. So the
       donors' wider night-to-night insulin is about how their nights unfold, not the gain. More nights spend time
       where Loop's output saturates (zero at lows, max basal at highs), and the 0.23 residual CV is variation not
       tied to the night mean (overrides, sleep-time changes). Open.
     - **Saturation runs the other way** (overnight 30-min bins, per-person median; `ctrl_sat.py`):

       | | zero delivery | < 25% of schedule | ≥ 90% max basal | CGM < 70 |
       |---|---|---|---|---|
       | donors | 12.5% | 18.9% | 1.6% | 1.9% |
       | c130_base | 9.7% | 11.8% | 3.5% | 1.4% |

       Donors' Loop cuts overnight insulin to near zero far more often, without more time low. Their scheduled night
       basal exceeds what their nights need, so Loop trims it, and that trimming is what makes their overnight
       insulin vary. The sim's Loop instead pushes to max basal more often, which fits its extra nights above 250
       (25% vs 18.5%).
     - The sim's body night need (true basal share N(0.5, 0.07), donor profile shrunk halfway, LESSONS 48) sits
       closer to or above the schedule than donors' does. Lead: the night-time settings mismatch, i.e. how far donors'
       scheduled night basal exceeds the basal their Loop actually delivers on quiet nights. Measure it per donor,
       give each simulated body that donor's own night ratio, and compare.
     - **The sim's bodies need more at night than their schedule.** Overnight automatic delivery ÷ scheduled basal,
       per person median (q25/75):
       - donors 1.29 (1.07 / 1.59);
       - c124 (no slow phase) 1.52; c130_base 1.65 (1.23 / 2.10); c132_clock 1.56.
       The slow phase adds a little (1.52 → 1.65) and late dinners a little; the rest is the body's own night need.
       The body's basal is the true basal share N(0.5, 0.07) × TDD (LESSONS 48), a judgement prior around the
       population's scheduled share. It is not the donor's own, so the sim's Loop runs above schedule at night
       ~25% more than donors' Loop does. That lowers day/night and pushes nights to max basal.
     - **Next (evidence-based):** set each body's basal share from its donor's measured overnight delivery on quiet
       nights (delivered ÷ scheduled × scheduled basal, as an upper bound of night need: it includes night
       corrections), keeping the TDD balance (carbs = the rest). Test as a switch, then compare day/night, night
       saturation and the cohort count.

125. **The donor's own night delivery as the body's basal makes it worse: the extra night insulin is not a basal
     level.** `--enable basal_own` (ef1f52f, off; template column `night_ratio`, `templates_pilot_night.csv`, donor
     median 1.30, q25/75 1.09 / 1.63, max 9.8, capped at 3). The body's basal share = scheduled basal × night_ratio
     × 24 / TDD, clipped 0.30–0.75, with carbs balancing TDD. c133 (same-code base reproduces c130, 31):

     | | base | basal_own | donors |
     |---|---|---|---|
     | matched | 31 | 24 | |
     | overnight delivered ÷ scheduled | 1.65 | 1.73 | 1.29 |
     | day/night | 1.59 | 1.51 | 2.06 |
     | night insulin CV / R² on night glucose | 0.29 / 0.51 | 0.23 / 0.39 | 0.39 / 0.61 |
     | t54 / lows per day | 0.15 / 0.83 | 0.09 / 0.58 | 0.215 / 1.08 |
     | manual U/day | 12.3 | 10.8 | 12.0 |

     - A body built to need what the donor's Loop delivers makes the sim's Loop deliver more again, and lowers the
       carbohydrate the TDD balance leaves (fewer boluses and lows). The sim's 1.65 is not a too-high basal prior.
       Something in simulated nights calls for insulin above schedule: evening carbohydrate carried into the night
       (fat/protein late parcel, slow phase, late dinners) or the 25% of nights above 250 (donors 18.5%).
     - Next: decompose the sim's night above-schedule insulin by what preceded it (time since last eating event,
       carbohydrate still absorbing at midnight), and compare donors' carb-free nights.
     - **The excess is the same on clean nights.** Overnight automatic ÷ scheduled per night, by whether a carb entry
       falls 20:00–06:00 (median of person medians; `night_split.py`, entries only on both sides):
       - donors: clean 1.16 (57% of nights), evening-carb 1.31;
       - c133_base: clean 1.41 (53%), evening-carb 1.53.
       Counting all simulated eating, 87% of sim nights have an event 20:00–06:00, mostly unentered.
       The sim's Loop runs ~0.2 × schedule above the donors' on every kind of night, including nights with no
       entered carbohydrate. Removing grazes did not help (c116_g0 day/night 1.635), and a higher body basal made it
       worse (basal_own). Remaining candidates:
       - what the sim's Loop forecasts at night: momentum and RC on the sim's sensor noise vs real G7 smoothing;
       - an EGP night level above the schedule's assumption (the tracer EGP arm, LESSONS 75).
     - **Sensor noise is a third of it** (c134, sensor_sigma and sensor_common 0.3, against c133_base):
       - overnight delivered ÷ scheduled 1.65 → 1.49 (donors 1.29); clean nights 1.41 → 1.33 (1.16);
       - day/night 1.59 → 1.62. Loop does answer noise asymmetrically at night, but the rest of the excess
         (~0.17 × schedule on clean nights) is in the body.
       - **Side finding:** CGM t54 0.149 → 0.029. About 80% of the sim's CGM time below 54 is sensor error, not true
         glucose; the FDA-fitted G7 noise is what puts its lows near the donors'. A CGM t<54 comparison is a joint
         test of body and sensor (AGENTS.md trap: compression and the 40 floor).
     - Still open: ~15% of schedule overnight that the sim's bodies need and donors' don't, on nights without entered
       carbohydrate, not explained by basal level, evening eating or sensor noise.
     - **Centre of the true basal share prior** (`--set basal_share=x`, 251224c; the same draw, shifted). c135 at
       0.42 against c133_base (0.5): 31 vs 31 matched, with a different set passing.
       - Now passing: night insulin CV 31.9 → 35.2 (36.0, KS 0.53); t54 0.149 → 0.233 (0.215); lows/day
         0.83 → 1.08 (1.08); conc1 26.4 → 27.8 (27.8); mean 155 → 152 (151).
       - Closer: day/night 1.59 → 1.72 (2.06); p99 1.33 → 1.46 (1.87); TDD CV 14.2 → 15.2 (15.7).
       - Now failing: CV 35.8 → 37.4 (34.8).
       - Overnight delivered ÷ scheduled 1.65 → 1.45; zero-delivery night bins 9.7 → 10.6% (donors 12.5%).
       Simulated bodies that need less than their schedule at night (as donors' Loop behaviour implies) bring the
       insulin structure and lows to the donors'. The 0.5 centre was a judgement prior around the scheduled share.
       c136 at 0.46 queued to locate the CV trade-off.
     - c136 at 0.46: 29 matched; CV 36.5 (fails); t54 0.206, lows 1.00, night insulin CV 33.6 (passes); day/night 1.68.
       The CV cost appears as soon as the centre moves down. The choice is between 0.5 (CV passes; lows, night insulin
       and day/night fail) and 0.42 (the reverse, same count). Pete to decide.
     - **Adopted (Pete, 2026-10-17): centre 0.42 by default** (63831f6). The default reproduces c135's people exactly
       (112 / 112). Open: glucose CV 37.4 vs 34.8.

126. **Where the CV now fails: both tails, from two separate causes.** Per-person median glucose percentiles
     5 / 10 / 25 / 50 / 75 / 90 / 98:
     - donors 83 / 94 / 112 / 141 / 181 / 226 / 289;
     - c133 (share 0.5) 83 / 93 / 115 / 143 / 188 / 233 / 292;
     - c135 (0.42, default) 79 / 88 / 109 / 138 / 188 / 231 / 301.

     The basal centre pulls the lower half 3–6 mg/dL down. The upper band (p75 188 vs 181) is the old heavy
     shoulder of unannounced daytime appearance (LESSONS 108), unchanged. Low-side carbohydrate per person-day
     (c133 → c135):
     - proactive 1.54 → 1.68 (21 → 23 g);
     - rescue 0.41 → 0.47 (10.5 → 12 g);
     - grazes 2.8 (35 g); snacks 2.5 (45 → 50 g).
     About 35 g/day goes to defence. Its rate is a per-person trait whose onset and size are judgements (proactive
     onset N(80, 20) mg/dL, 12 g; LESSONS 41). Donors' proactive eating is not observable directly; it is part of the
     unannounced labeled appearance whose daytime surplus lesson 108 measured. Next: whether lowering proactive
     carbs toward a measured rate closes the shoulder without losing the lows.
     Candidate evidence: donors' labeled pulses that start within 30 min of a falling CGM (< 110, falling ≥ 1
     mg/dL/min) without reaching 70.
     - **Proactive defence is not the shoulder.** Measured like for like, donors have 0.25 pulses/day after a fall
       (labeled unannounced pulse starting at CGM < 110, ≥ 15 mg/dL lower than 15 min before, no reading < 70 in the
       prior hour), 7.9 g-eq/day (median person). c135 has 0.33/day, 10.3 g-eq; `pro_shift.py`.
       `--set pro_shift=-10.0` (c8bc385, proactive onset 10 mg/dL lower):
       - pulses after a fall unchanged (0.33/day); CV 37.3 (unchanged); upper percentiles unchanged
         (p75 188, p90 236);
       - matched 33 vs 31, without moving its own target, so that is noise. Not adopted.
       The pulses after a fall are mostly not the proactive snack (meals and other eating that happen to follow a
       fall). The upper shoulder and CV stay open: unannounced daytime appearance (lesson 108).

127. **Fewer snacks do not reduce the labeled unannounced surplus.** The snack rate is the donor's labeled
     pulses/day − 3, and labeled pulses include non-eating rises, so it may double-count. c135 per person against
     its own donor: labeled meals/day 1.02×, unannounced meals 1.08×, unannounced g-eq 1.11×.
     `--set snack_minus=0.4` (0f5098e; snack rate 0.4/day lower, entry probability recomputed):
     - twin unannounced meals 1.10×, g-eq 1.12× (unchanged); CV 37.7 (37.4); p75 186 (188); TIR 70.7;
       lows/day 1.25 (1.08);
     - 32 vs 31 matched (noise). Not adopted.
     The snack count is not what the labeler sees as surplus. With grazing (lesson 109), proactive defence (126),
     fast intake (117–119) and snacks (here) each neutral, the sim's extra unannounced daytime appearance is not one
     eating component. What is left is the labeler's reading of the sim's own non-eating rises (2.3/day, LESSONS 108),
     whose sources the morning-modulator ablations did not find (110).

128. **The CV and day/night failures are two strategy-specific defects, found by pairing people with their own
     donors.**
     - **Persons do not inherit their donor's variability.** Twin Spearman (sim person vs own donor, c135): TDD
       0.90, mean 0.23, TIR 0.17, CV −0.06. Donor CV follows behaviour, and the sim does not reproduce any of it:

       | trait | ρ with donor CV | ρ with sim CV |
       |---|---|---|
       | announced share | −0.38 | +0.04 |
       | carb entries/day | −0.32 | +0.02 |
       | manual boluses/day | −0.26 | +0.04 |
       | rescues/day | +0.46 | +0.06 |
       | TDD | +0.30 | +0.14 |

     - **Temp-basal people carry the CV gap.** Twin median CV difference (sim − own donor): temp +5.0 / +5.4 / +3.9
       / +6.8 in c114 / c124 / c133 / c135, against automatic-bolus −0.4 / 0.0 / −0.8 / +1.3. Medians in c135, sim
       (own donors):
       - temp: CV 38.3 (32.6); t70 1.69 (0.73); manual U/day 14.1 (12.5); conc1 30.4 (25.5); day/night 1.76 (1.76);
       - automatic: CV 36.8 (35.3); t70 1.75 (1.11); manual U/day 12.2 (11.0); day/night 1.69 (2.15).
       Simulated temp-basal people take 13% more manual insulin than their donors and spend 2.3× the time below 70.
     - **The day/night gap is the automatic-bolus group's** (temp matches at 1.76). That fits LESSONS 99.
     - Next: split temp people's manual insulin into meal boluses and corrections against their donors, and compare
       their correction bolus size (temp-basal Loop users have no automatic boluses, so hand corrections carry the
       highs).
     - **The temp-basal excess is meal boluses, not corrections.** c135 manual boluses matched to the behaviour event
       that triggered them (per day, count / U, median person; `bolus_kinds.py`):
       - automatic: entry 2.50 / 8.18, correction 0.58 / 0.36, free 0.25 / 0.58, split 0.08 / 0.14;
       - temp: entry 2.33 / 9.42, correction 0.50 / 0.69, free 0.08 / 0.33, split 0.17 / 0.20.
       Temp-basal people's correction count matches their donors' (ratio 0.99; automatic 0.66). Their meal boluses
       are ~15% larger than automatic-bolus people's, which takes their manual total 1.6 U/day above their donors'.
       Lead: the meal bolus amount the sim's temp-basal person takes, against Loop's recommendation and their donor's
       bolus ratio. A temp-basal Loop's recommendation carries the correction for current glucose and the forecast,
       which automatic-bolus users leave to Loop's own boluses.
     - **Meal bolus against the carb-only amount** (labeled announced meals ≥ 10 g, bolus ÷ (entered g / CR),
       median person; `bolus_vs_cr.py`):
       - donors: automatic 1.00, temp 1.00 (BG at onset 129 in both);
       - c135: automatic 1.02 (134), temp 1.07 (128).
       Donors' meal boluses land on the carbs at the median, whatever Loop's recommendation carried. The sim's
       temp-basal people take ~7% more: the calculator recommendation includes the correction and forecast terms,
       and the person takes it (calc_up/down around 1). That is about half of their 13% manual excess. The other
       half is meal count and size. Lead: whether donors adjust a temp-basal recommendation back toward the carbs, or
       their recommendation is lower because their pre-meal forecast is lower. Measure it from the donors'
       recommended vs delivered boluses (bolus_decisions).
     - **Both sides take Loop's recommendation; the sim's Loop recommends more.** Requested ÷ recommended manual
       boluses (rec > 0.3 U), median of person medians:
       - donors (bolus_decisions): automatic 1.00, temp 1.00; 84% / 81% within 5%;
       - c135 (trace): 1.00 / 1.00; 76% / 75%.
       So the 7% is in the recommendation. At similar BG at onset (128 vs 129), the temp-basal sim's Loop asks for
       more than the carbs; the donors' asks for about the carbs. The recommendation's other terms are the forecast
       above target and IOB, so the sim's temp-basal people come to meals with less IOB or a higher forecast. Next:
       IOB and forecast at meal-bolus time, donors (dosingDecision) vs sim (trace), for temp-basal people.
     - **Not IOB.** Loop's IOB just before a meal bolus (manual bolus with an entry within ±15 min), in hours of
       scheduled basal, median person (`iob_at_meal.py`; donors loop_iob, sim trace candidateIOB from the step
       before the bolus; the bolus step's own value includes the bolus):
       - donors: automatic 1.82, temp 1.37;
       - c135: automatic 2.21, temp 1.40.
       Temp-basal people come to meals with the donors' IOB. Their extra 7% must be in the forecast term: the sim's
       temp-basal people are predicted higher at bolus time (a rise already under way, or momentum on sensor noise).
       Automatic-bolus people carry 20% more IOB into meals than their donors, which fits their lower day/night
       (more automatic insulin around meals). Next: the forecast at meal-bolus time against the donors' bgForecast.
     - **Not the CGM trend either.** 15-min CGM change before the meal bolus (median person; share > +10):
       - donors: automatic +4.0 (0.36), temp +2.5 (0.31);
       - c135: automatic +1.0 (0.26), temp +2.5 (0.28).
       For temp-basal people, IOB and momentum match the donors, but the recommendation is 7% higher. The remaining
       forecast terms are retrospective correction (glucose above Loop's prediction just before the meal) and COB
       from earlier entries. Comparing them needs the donors' dosingDecision bgForecast and RC, which are in
       Databricks only (the local exports carry decision times, not forecasts). Next: pull dosingDecision forecasts
       at meal-bolus times for the 56 temp-basal pilot donors.
     - **The sim's Loop carries a positive retrospective correction into meals.** Trace candidateRC from the step
       before meal boluses, median person (c135):
       - temp 9.0 mg/dL (all cycles 3.9), 0.21 U at the settings ISF;
       - automatic 13.4 mg/dL (all cycles 7.5), 0.25 U.
       On a ~4 U meal bolus, 0.21 U is ~5%, most of the temp-basal 7%. Simulated glucose sits persistently above Loop's
       prediction. Two contributors, both partly by design:
       - the body's insulin acts slower than Loop's model (clamp timing, LESSONS 114), so the predicted drop runs
         ahead of the real one;
       - unannounced eating raises glucose with no carbohydrate in the forecast.
       Whether donors' Loop carries the same positive RC into meals is the check that decides whether the sim
       overstates it. It needs dosingDecision RC/bgForecast from Databricks (Pete's U2M login).

129. **Real glucose follows Loop's forecast by day; simulated glucose runs above it all day.** Donors' Loop
     retrospective correction comes from a plain replay of their own record: no counterfactual, decisions on real
     BG, class-1 flags, the donor's recorded RC mode (rc_mode.csv), 2026-07-01..07-15, 167 pilot donors. Earlier
     work matched the replay's RC to Loop's recorded values. The sim's comes from its trace; both are candidateRC,
     mg/dL. Script `rc_meal_donors.py`, `rc_hours.py` (scratch).

     | | RC at meal bolus | all cycles | 00–06 | 06–12 | 12–18 | 18–24 |
     |---|---|---|---|---|---|---|
     | donors temp (42/52) | +4.3 | +0.3 | +4.8 | +0.8 | −0.5 | +0.6 |
     | sim temp (c135) | +9.0 | +3.9 | +2.3 | +3.6 | +4.6 | +4.5 |
     | donors automatic (86/104) | +7.8 | +2.8 | +8.3 | +1.5 | +0.4 | +4.4 |
     | sim automatic | +13.4 | +7.5 | +9.2 | +6.0 | +5.5 | +6.5 |

     - This compares how far each side's glucose drifts from the same forecast, a like-for-like statistic of the
       body, not a fit to Loop.
     - **Daytime:** donors' glucose follows Loop's prediction (RC ≈ 0–1.5). The sim's runs 3.6–6 mg/dL above it from
       06 to 24 h: more glucose enters that Loop is not told about. That is lesson 108's unannounced daytime
       surplus, measured here with no labeler.
     - **Night:** donors run above the forecast (dawn and night EGP rises); simulated temp-basal people less so
       (+2.3 vs +4.8).
     - **Not insulin timing:** the sim's all-cycles RC was +5.1 / +10.3 at p2 0.05 (c119), +5.1 / +9.4 at 0.025
       (c124) and +3.9 / +7.5 now.
     - It explains the temp-basal meal-bolus excess (the recommendation carries 0.21 U vs donors' 0.07 U of RC) and
       part of the CV gap.
     - Next: find the daytime unmodelled input by RC contribution, i.e. which simulated events precede positive-RC
       hours (unentered meals, grazes, snacks, proactive carbs, non-eating rises).
     - **What the daytime offset is not, and a lead.** Daytime RC (06–24 h) in the source ablations moves little:
       - no grazes −1.0 to −1.7 (c116_g0 vs c119_base);
       - half grazes, fast grazes, proactive onset −10, 0.4 fewer snacks, own meal clock: each within ±1.
       No single eating source carries the +4–5. True ÷ setting per simulated body (c135, median, q25/75):
       - ISF 0.98 (0.85 / 1.05);
       - CR 0.69 (0.62 / 0.80);
       - basal 0.87 (0.70 / 1.12).
       The bookkeeping CR (LESSONS 40) is 31% below the setting. If the effective CR is too, every entered meal is
       under-dosed in Loop's eyes and glucose runs above its forecast after each one. That is the daytime RC
       pattern, and it would leave the labeler's per-entry pulse (1.21 = donors) unchanged, because the labeler uses
       the TDD yardstick, not settings. Next: the effective CR (ISF_eff ÷ CSF_eff, the self-check's cr_eff) against
       the setting, and the donors' implied mismatch from their own RC after entered meals.
     - **Correction: the CR lead is wrong.** Effective CR (true ISF ÷ effective CSF, the self-check's cr_eff) ÷
       setting is 1.11 (q25/75 0.97 / 1.36, 60 people). Bodies need slightly less insulin per gram than their
       settings, which would put glucose below Loop's forecast after meals, not above. The 0.69 is the linear-part
       bookkeeping CR. The daytime +4–5 RC remains unexplained by settings, eating sources or insulin timing.
       Next: per-event RC around simulated meals (entered vs unentered) against donors' RC around their entered
       meals, to see whether it is meal-bound or continuous.
     - **The offset is meal-bound, and late.** Daytime RC by hours since the last carb entry, median person
       (`rc_since.py`), bins 0–1 / 1–2 / 2–3 / 3–4 / 4–6 / 6+ h:
       - donors temp −2.6 / −3.8 / −0.6 / +6.4 / +4.7 / +3.2;
       - sim temp −0.8 / 0.0 / +1.5 / +8.6 / +11.3 / +7.7;
       - donors automatic −3.6 / −4.0 / −0.7 / +8.0 / +10.2 / +6.3;
       - sim automatic −0.5 / 0.0 / +3.4 / +16.4 / +18.3 / +12.2.
       Two differences:
       - In the first 2 h after an entry, donors' glucose runs below Loop's forecast (−3 to −4) and the sim's tracks
         it (0). Real meals deliver less early than Loop's absorption model expects; the sim's deliver about what it
         expects.
       - From 3 h on, both run above the forecast, the sim about twice as much.
       The late excess does not depend on the meal model: c124 / c127 (spread, no slow phase) / c129_s15 / c129_s30
       all give 3–6 h RC of +10 to +13 (temp) and +15 to +23 (automatic). So it is not the slow phase. It is what
       happens 3–6 h after an entry in the sim: unentered eating between meals (grazes −1 to −1.7 earlier) and the
       fat/protein late parcels (A12; 0.1 g glucose per g protein, delayed 90 min).
       Next: a fat/protein ablation (`--disable fat`) on this RC table.
     - **Fat/protein is part of the automatic group's late excess** (`--disable fat`, c139 vs c135):
       - 3–4 / 4–6 h RC: automatic +16.4 / +18.3 → +10.6 / +14.3 (donors +8.0 / +10.2); temp +8.6 / +11.3 →
         +7.7 / +10.9 (donors +6.4 / +4.7);
       - 25 vs 31 matched; hurst_long 0.219 → 0.193; mean 152 → 148.
       The component is evidenced (Smart 2013, Wolpert 2013, Bell 2020) and stays. Its size per gram of fat and
       protein (A12, a [J] split of 0.44 / 0.45 g per carb gram) may be large for automatic-bolus people's meals. The
       temp-basal late excess (+11 vs +5 at 4–6 h) is not fat; that leaves unentered eating 3–6 h after meals.
     - **The fat and protein amounts are evidenced.** 470 T1D adults ate fat 75 ± 31 g, carbohydrate 162 ± 63 g and
       protein 70 ± 24 g a day (PMC11446970): 0.46 g fat and 0.43 g protein per carb gram, against the sim's
       0.44 / 0.45 (registry A12 updated). If the automatic group's late RC is too large, it is in the effect sizes:
       - the fat SI dip ρ U(0, 0.35) per 50 g, 2–6 h;
       - the protein parcel, 0.1 g glucose per g, delayed 90 min.
       Not in the amounts.

130. **Anchored on entries, not labels: simulated meals are over-covered; donors' plateau.** CGM change per 10 g after
     carb entries ≥ 20 g with no other entry from −3 h to +6 h. No labeler is involved, so this is observed data on
     both sides (`entry_traj.py`, G7). Median ΔCGM per 10 g at 30 / 60 / 120 / 180 / 240 / 360 min:
     - donors automatic (6,062): +3.2 / +4.3 / +4.3 / +5.4 / +3.7 / −0.3;
     - donors temp (2,517): +4.7 / +6.4 / +5.2 / +5.5 / +4.0 / +1.0;
     - c135 automatic (609): +1.3 / +1.7 / −3.0 / −4.1 / −1.0 / +1.7;
     - c135 temp (272): +1.4 / +2.7 / −2.3 / −3.1 / −0.7 / +0.8;
     - c139 (no fat/protein): the same shape.
     For a 45 g meal, donors hold a plateau ~20–25 mg/dL above their start for 3 h; the sim's meals end 15–18 mg/dL
     below it by 2–3 h. Earlier meal comparisons conditioned on labeled pulses, i.e. meals that rose, and missed this.
     The CSF calibration (labeled g-eq per entered gram 1.21, LESSONS 89) had the same bias.
     - In sim truth, entered ÷ eaten grams is 0.96 (q25/75 0.81 / 1.13), entry vs eating start −3 min (q10/90 −34 /
       +27). The miss is not counting. Effective CR ÷ setting is 1.11: meals are bolused ~11% above need, and Loop
       adds its own dosing.
     - Fit target (Pete: fit to observed data, never to Loop): this entry-anchored trajectory. Arms queued:
       csf_mult 1.2 and 1.4 (c140). More glucose per gram with the TDD balance means fewer grams eaten for the same
       insulin, so meals rise more and the bolus covers less.
     - **CSF alone does not fix it** (c140, csf_mult 1.2 / 1.4 against c135):
       - 60 / 120 / 180 min per 10 g: temp +2.6 / −0.6 / −0.9 and +4.3 / +0.4 / −0.5; automatic +2.4 / −1.6 / −2.2 and
         +2.8 / −1.3 / −3.0 (donors temp +6.4 / +5.2 / +5.5, automatic +4.3 / +4.3 / +5.4);
       - 28 and 32 matched; TIR falls to 66.
       Meals still go below their start after 2 h: the insulin outlasts the carbohydrate.
     - **Correction to LESSONS 113.** The sim's meal appearance (t25/50/75 58/99/148 min) is FASTER than both of
       Elleri 2013's tracer meals (high-GL 72/130/197, low-GL 95/178/270). "At or above tracer pace" is not a match:
       the late absorption is too short, which explains this trajectory. Arms queued: ge_mult 0.7 and 0.55, inside
       evidence/09's Vmax 2–5 kcal/min. Target: this entry-anchored trajectory and the tracer t50/t75.
     - **Slower emptying makes it worse** (c141, ge_mult 0.7 / 0.55): entry-anchored ΔCGM per 10 g at 120–180 min
       −6.5 to −9.6, against c135's −2 to −4; appearance t50 unchanged (98 min). The dip is insulin acting ahead of
       the carbohydrate: donors rise faster early (60 min +4.3 / +6.4 per 10 g vs the sim's +1.7 / +2.7), hold a
       plateau, and come back by 5–6 h. Next arms (c142): slower insulin action p2 0.015 (the 15 U clamp's 6.3% in
       the first hour is below the body's ~10% at p2 0.025) and faster early emptying ×1.4.
     - **c142: neither lever gives the donors' shape.** Entry-anchored ΔCGM per 10 g at 60 / 150 / 180 min:
       - p2 0.015: temp +2.5 / −0.8 / −2.4, automatic +2.4 / −2.9 / −3.6 (31 matched);
       - emptying ×1.4: temp +5.4 / +1.2 / +0.7, automatic +4.1 / −0.5 / −0.7 (26 matched; CV 40.3);
       - donors: temp +6.4 / +5.5 / +5.5, automatic +4.3 / +5.0 / +5.4.
       Faster emptying gets the first hour right but is back at the start by 2.5 h. Donors hold +5 per 10 g to 4 h and
       come back by 6 h. Slower insulin changes little.
     - What a held plateau needs is glucose still arriving, or insulin acting less, between 2 and 4 h after a
       covered meal. The candidates are now components, not knobs:
       - follow-on eating within 6 h that donors do not enter (dessert, a second helping; the selection excludes
         only entered food);
       - a meal that is under-covered in effect although the entry is right. Real CR settings are tuned on whole
         days, not on the 2–4 h window.
       Next: the sim's unentered eating within 6 h of an isolated entry against what donors' labeled pulses show in
       the same window.
     - **Not follow-on eating.** Unannounced labeled pulses 0.5–6 h after an isolated entry: donors 1.10 per entry
       (72% with ≥ 1, 9,215 entries) vs c135 1.02 (74%, 942). The donors' 2–4 h plateau belongs to the entered meal
       itself: in effect it is under-covered between 2 and 4 h. The sim's meals are over-covered: effective CR ÷
       setting 1.11, plus Loop's own dosing on the forecast's carb effect. The shape needs:
       - an early rise like fast emptying (×1.4 matched the first hour);
       - glucose still arriving 2–4 h, or less insulin acting then, without the CV cost every faster-meal arm paid
         (CV 38–40).
       Open; the levers tried (CSF, emptying both ways, insulin speed, fat, slow phase, fast-share spread) each move
       one part.
     - **Not carb counting.** Brazeau 2013's 692 meals, re-analysed in PMC7594710: 63% under-estimated; error =
       10.54 − 0.28 × CHO g (−2 g at 45 g, −12 g at 80 g, −17 g at 100 g). The sim's bias (person N(−0.10, 0.10),
       meal-size term −0.1·ln(g/45), noise; entered ÷ eaten median 0.96) is at that evidence. The 2–4 h plateau
       is not an under-count.
     - **Not detection, not pre-meal momentum.**
       - Share of isolated entries (≥ 20 g) with a labeled announced pulse within ±30 min: donors 0.45 (by size
         0.43 / 0.46 / 0.52), c135 0.48 (0.45 / 0.45 / 0.58). The labeled calibration was not conditioned on a
         different subset.
       - ΔCGM per 10 g at −60 / −30 / 0 min: donors temp +0.4 / 0 / 0 (flat); sim temp +1.2 / +0.8 / 0 (drifting
         down into the meal).
       The plateau is after the entry, with matched delivered insulin (LESSONS 122). Real meals raise glucose more
       per entered gram in the 1–4 h window than the sim's, by ~5–8 mg/dL per 10 g at 2–3 h. This is the open
       physiological gap; the lever is not yet identified.

131. **The sim's EGP suppression after meals is deeper and earlier than the tracer evidence.** True EGP ÷ pre-meal
     after isolated entries (≥ 20 g, no entry −3 h / +6 h; c135, 1,150 meals), 0 / 30 / 60 / 90 / 120 / 150 / 180 /
     240 / 360 min: 1.01 / 0.91 / 0.59 / 0.41 / 0.42 / 0.52 / 0.66 / 0.83 / 0.95.
     The nadir is −59% at 90–120 min. Romeres 2025's T1D meal tracer study gives −44% at ~160 min (the evidence the
     EGP arm was built on, LESSONS 69 / 75, calibrated before the clamp insulin timing and the meal changes). Too
     deep and too early removes glucose in exactly the 1.5–3 h window where simulated meals fall below baseline and
     donors' hold (lesson 130). Fit targets: the tracer nadir (depth and time) first, then the entry-anchored CGM
     trajectory. Arms (c143): p2e 0.006 (was 0.010; ReplayBG prior 0.008) and egp_share 0.4 (was U(0.5, 0.7)).
     - **c143.** p2e 0.006: EGP nadir 0.54 at 120 min (Romeres 0.56 at ~160). Entry-anchored temp ΔCGM per 10 g at
       90 / 150 min: +3.0 / −1.9 (c135 +0.7 / −3.3; donors +5.9 / +5.5). 34 vs 31 matched; hurst_long 0.267
       (passes); day/night 1.80; CV 38.7 (fails). egp_share 0.4: nadir 0.64 but the trajectory is worse (−4.3 at
       150 min); 28. The timing matters, not the share. Queued p2e 0.005 / 0.004 (c144) for the tracer nadir time.
     - **c144.** p2e 0.005: nadir 0.60 at 120 min, 32 matched, night insulin CV 43.9 (fails). p2e 0.004: 0.66 at
       120 min, 31. The nadir time stays at 120 min for every p2e; slower rates only make it shallower than the
       tracer's. 0.006 matches the depth (0.54 vs 0.56) and gives the best count (34). The remaining 40-min timing
       difference is in the insulin PK and meal timing, not the EGP rate. Default decision: Pete.
     - **Adopted (Pete, 2026-10-17): p2e 0.006 by default** (9513d5a). c145 is the validation cohort: every person is
       recalibrated at the new rate, against c135.
       - **35 vs 31 matched**, the best default so far. New passes: hurst_long (KS 0.20), sigma_disp, zero_frac,
         TDD CV, night insulin CV, Box-Cox.
       - EGP nadir 0.51 at 120 min (Romeres 0.56 at ~160).
       - Now failing: t70 2.45 (1.67) and lows/day 1.42 (1.08). The recalibration leaves the bodies a little more
         insulin-sensitive at night.
       - The entry-anchored meal trajectory is back to temp −3.3 per 10 g at 150 min (the override arm c143 had
         −1.9; donors +5.5). The recalibration undoes most of the meal-shape gain, so the post-meal plateau stays open.
     - **Basal share re-fit on the new EGP rate** (c146 against c145, frozen 9513d5a):

       | centre | 0.42 (default) | 0.46 | 0.50 | donors |
       |---|---|---|---|---|
       | matched | 35 | 32 | 27 | |
       | t70 | 2.45 | 2.30 | 1.81 | 1.67 |
       | lows/day | 1.42 | 1.25 | 1.13 | 1.08 |
       | TDD CV (KS p) | 15.0 (0.14) | 14.9 (0.04) | 14.1 (0.001) | 15.7 |
       | hurst_long (KS p) | 0.217 (0.20) | 0.234 (0.23) | 0.223 (0.03) | 0.247 |

       A trade between the lows and day-level insulin variation, with no centre that passes both. The default stays
       0.42; the low-side overshoot (t70, lows/day) is a known limit of the c145 defaults.

132. **Total-drop ISF calibration gets the meal plateau right, and the levels wrong.** `--enable isf_total` on the
     current defaults (c147 vs c145; frozen 9513d5a). Entry-anchored ΔCGM per 10 g at 60 / 90 / 120 / 180 min:
     - temp +4.4 / +6.3 / +7.0 / +5.5 (donors +6.4 / +5.9 / +5.2 / +5.5);
     - automatic +3.0 / +3.7 / +3.0 / +2.8 (donors +4.3 / +4.0 / +4.3 / +5.4).
     This is the first arm whose meals hold the donors' plateau. But the whole cohort runs high: mean 180.6 (151.4),
     TIR 53.6 (71.7), t54 0.03 (0.215), TDD 43.6 (38.8); 23 matched. That is LESSONS 75's result again.
     - Peak calibration (default): insulin is too strong around meals (they fall below baseline at 2–3 h) but the
       level is right.
     - Total calibration: meals are right but every other hour runs too high.
     So the per-unit effect real insulin has at meals is smaller than the effect that keeps the level right
     between meals. One ISF cannot do both. Candidates (physiology, not fitting):
     - postprandial insulin resistance beyond fat: meal-induced, hyperglycaemia-induced (B11 is a slow 6 h state);
     - the EGP arm's share of the effect being larger in fasting than after meals (glucagon is not suppressed after
       mixed meals in T1D, so EGP suppression is weaker exactly then).
     The second is evidenced in T1D (paradoxical postprandial glucagon rise). Next: evidence for its size, then
     model the meal-time EGP suppression deficit as its own named component.
     - **The glucagon candidate is already inside the EGP arm.**
       - T1D postprandial glucagon is higher, from secretion (stable glucagon tracer, 75 g mixed meal, 16 + 16;
         Diabetes 2026).
       - EGP suppression after mixed meals is impaired in T1D at similar insulin exposure, with similar
         insulin-dependent disposal and not always a larger glucagon rise (mixed-meal tracer study).
       The sim's EGP arm is calibrated to a T1D meal tracer (Romeres 2025), and its post-meal nadir is close (0.51 vs
       0.56), so a separate glucagon term would double-count. The meal-time over-coverage then sits in disposal:
       insulin-mediated uptake around meals acts more per unit than the level between meals allows. Open: whether the
       ISF peak-probe calibration (a 0.5 U probe at 180 mg/dL on the linear part) misstates the uptake that acts on
       a meal bolus at post-meal glucose.

133. **No single ISF calibration fits both meals and levels; the gap is meal-specific insulin action.**
     `--set isf_blend=w` (52bc2fc; k^(1−w), 0 = peak, 1 = total). c148 against c145:

     | | peak (c145) | w 0.3 | w 0.5 | total (c147) | donors |
     |---|---|---|---|---|---|
     | matched | 35 | 30 | 25 | 23 | |
     | mean | 148 | 156 | 163 | 181 | 151 |
     | TIR | 70.1 | 67.0 | 63.8 | 53.6 | 71.7 |
     | t70 | 2.45 | 1.65 | 1.20 | 0.47 | 1.67 |
     | temp meal per 10 g, 120 / 180 min | −2.3 / −3.3 | +1.2 / 0.0 | +2.4 / +0.3 | +7.0 / +5.5 | +5.2 / +5.5 |

     Weakening insulin enough to hold the meal plateau raises every hour's level. The donors combine both: their
     meals stay up and their levels stay down. So insulin acts less per unit at and after meals than it does on
     basal and corrections, a meal-specific action deficit no scalar ISF expresses. Evidence to find:
     - postprandial insulin action in T1D: mixed-meal clamps, insulin action under hyperglycaemia and
       hyperinsulinaemia;
     - absorption of meal-sized boluses: larger depots absorb more slowly and less completely (volume effect,
       lesson 114, second-hand only).
     The second is the more direct candidate. Default unchanged (peak, 35/51); switch off.
     - **Not dose size.** Heise 2017 (faster aspart vs aspart, 0.1 / 0.2 / 0.4 U/kg, T1D): the total glucose-lowering
       effect is ~2× at 0.2 vs 0.1 U/kg, i.e. linear through ~7–14 U for 70 kg. It turns less than proportional only
       at 0.3–0.4 U/kg, presumably from saturation of insulin-stimulated disposal (2019 review, PMC7007438). Lispro:
       PK linear to 0.2 U/kg; 7–30 U gives less than proportional glucose infused (Leohr 2020); bioavailability
       55–77% (label). Typical meal boluses (2–8 U) sit in the linear range, so dose saturation does not make meal
       insulin act less per unit. The meal-specific deficit remains unexplained; the remaining lead is postprandial
       insulin action itself.
     - **Not bolus bioavailability either.** Wilinska 2005 (IEEE TBME 52:3–12; lispro, bolus and CSII, 7 T1D, 12 h,
       11 models): the best model has two absorption channels (67% slow, 33% fast) and saturable Michaelis–Menten local
       degradation. Saturable degradation removes a larger share of small, basal-sized depots than of a bolus, so
       boluses come out relatively MORE bioavailable, the opposite of the meal-time deficit. The device literature's
       "large bolus volumes absorb poorly" is patent rationale, not measurement.
     - Every candidate found so far is ruled out by evidence or by test. The post-meal plateau is an open gap with no
       evidenced mechanism. Options:
       - keep searching (mixed-meal clamp studies of postprandial insulin action in T1D);
       - accept it as a documented limit of the simulator for meal-time candidates.
     - **Post-meal activity (Pete's question: do people move more after eating?).** In the sim, activity episodes
       ignore meals: 37% of entries ≥ 20 g have one within 3 h, the random expectation at 2.6 episodes/day being 38%.
       Moving after a meal lowers glucose (walks are a known way to blunt rises), so more post-meal activity would
       deepen the dip. The useful question is the reverse: whether adults sit more after meals than the sim assumes.
       `--disable exercise` (c149 vs c145; it also removes activity carbs, so meals are a little smaller):
       - temp ΔCGM per 10 g at 60 / 90 / 150 / 180 min: +4.1 / +3.4 / −1.6 / −2.9 (c145 +2.1 / +0.7 / −3.3 / −3.1;
         donors +6.4 / +5.9 / +5.5 / +5.5);
       - 31 matched, TIR 65.
       Activity after meals accounts for ~+1–2 mg/dL per 10 g in the first 90 min, not the 2–4 h plateau. If
       accelerometer evidence shows adults are less active in the 1–3 h after meals, meal-coupled activity timing is a
       real component (part of the early gap). Children may well be the opposite.
     - **Evidence for meal-coupled activity timing: effect yes, base rate no.**
       - Post-meal activity lowers post-meal glucose: Singapore free-living study, 789 adults, accelerometer + CGM;
         cycling 45 min after a meal (MDPI 2018); post-meal sedentary time delays the peak in older adults.
       - Lab studies of spontaneous movement are mixed (Otago, n = 17).
       No source gives the activity level in the 1–3 h after meals relative to other waking hours, which is the
       quantity a meal-coupled schedule needs. Not built. A BDDP measurement is possible where donors carry
       step or workout data (HealthKit physicalActivity records in device_data) and is the way to get it.
     - **The structure statistics move the other way.** ACF zero-crossing across the calibration arms: peak (c145)
       and blend 0.3 at 65 min, blend 0.5 at 70, total at 75 (donors 42.5). Between-day fraction (0.125 → 0.155) and
       circadian amplitude (0.167 → 0.200) worsen with weaker insulin too. Donors combine long meal plateaus with fast
       reversal of 5-min steps, which points to a fast-reverting (~40 min) source of step variance in real glucose
       that the sim lacks. Lesson 76 measured simulated quiet stretches decorrelating at 20 min (sensor noise)
       against the donors' 40 (physiological wander). The two failures, meal plateau and ACF zero-crossing, have
       separate causes; fixing the first with insulin strength worsens the second.

134. **On the current defaults the night side of day/night has nearly closed.** c145 overnight automatic ÷ scheduled,
     median of person medians:
     - clean nights 1.29 (c135 1.41; donors 1.16); evening-carb nights 1.35 (1.53; donors 1.31);
     - zero-delivery night bins 13.2% (donors 12.5%); < 25% of schedule 16.8% (18.9%).
     The basal share at 0.42 and the slower EGP rate brought the nights to the donors'. The remaining day/night gap
     (1.75 vs 2.06) is on the daytime side: smaller meal-time peaks of manual insulin (lesson 122: 0.43–0.46 vs
     0.61–0.62 of the mean hourly rate), with daily manual units matching. The sim spreads its bolus insulin more
     evenly across the day than donors, who concentrate it at lunch and dinner. Next: bolus size per meal by
     slot, sim vs own donor (twin), and the per-slot share of entered grams (dinner 0.38 vs 0.44, lesson 123).

135. **Donors' logged workouts are not meal-avoiding; the meal clock trades day/night against CV.**
     - **Workouts in BDDP.** device_data has `physicalActivity` records: HealthKit workouts with name, duration and
       energy; time is epoch ms in a JSON string. Overall 5.25 M records from ~5,200 users. For the pilot, 30 of 168
       donors have any (24,595 records), and 18 have workouts inside their export window (669; median 22 per donor
       over 4 months; median 35 min; yoga, pilates, strength, running). No step counts, so everyday activity is
       not measurable this way.
     - **Workout start time since the last carb entry, against random times at the same local hours** (same donors,
       same window): 0–1 h 18% vs 23%; 1–2 h 22% vs 18%; 2–3 h 11% vs 11%; 3–6 h 13% vs 15%. Start hours 06–12 /
       12–18 / 18–24: 50% / 29% / 21%. At most a slight shift out of the first hour after eating, within noise.
       Intentional exercise is not meal-coupled. The sim's independent timing is consistent with it.
     - **own_clock on the current defaults** (c150, templates_pilot_clock.csv; base reproduces c145, 35):
       - 30 matched; day/night 1.83 (passes, KS 0.06; donors 2.06); night entered share 0.03 (0.04);
       - CV 39.2 (38.3), lows/day 1.50, TDD CV fails.
       It fixes the meal timing statistics and moves others further off, as on the earlier defaults. Off.

136. **CSF ×1.3 on the current defaults does not fix the lows; BDDP holds self-reported states.**
     - **c151 (csf_mult 1.3 vs c145).** Temp entry-anchored ΔCGM per 10 g at 60 / 90 / 150 min: +4.1 / +3.0 / −0.1
       (c145 +2.1 / +0.7 / −3.3). Lows and CV get worse: t70 2.53, t54 0.33, CV 40.0. Twin CV gap: temp +8.6 (c145
       +8.1), automatic +4.2 (+2.9). 26 vs 35 matched. Not the lever.
     - **On c145 the temp-basal CV gap is +8.1 against own donors**, with t70 2.31 vs 0.73 (3×); automatic +2.9,
       2.47 vs 1.11. The lows and the missing meal plateau look like one problem: meals over-covered at 2–4 h, and
       temp-basal Loop can only suspend.
     - **What BDDP device_data has** (types by records / users):
       - CGM 6.33 B / 39 k; basal, dosingDecision, bolus, food, …;
       - physicalActivity 5.25 M / 5.2 k, nearly all HealthKit workouts (name, duration, energy, distance,
         reportedIntensity);
       - no heart-rate type and no step counts.
     - **`reportedState`: events logged in the Dexcom G7 app** (`states` column; records / users):
       - illness 1,181 / 248;
       - stress 2,266 / 172;
       - cycle 1,377 / 141;
       - alcohol 354 / 101;
       - hyperglycaemia symptoms 3,786 / 116;
       - hypoglycaemia symptoms 1,219 / 177;
       - 26,601 / 1,248 with no state.
       This is the first measured donor evidence for the illness, stress, menstrual and alcohol components, which are
       sized from literature today. Next: per-state frequency and the glucose / delivered-insulin response around
       logged events, against the sim's component sizes.
     - **First donor evidence for the life factors** (reportedState, all G7 loggers whatever their controller).
       CGM mean in the 24 h after a logged event minus the same person's mean on days −14..−2 and +2..+14
       (≥ 200 readings in the event window, ≥ 1,500 in the baseline; time stored as epoch ms or ISO, value as plain
       or BSON numbers; mg/dL = mmol/L × 18.016):

       | state | events | users | median Δ | mean Δ | Δ time > 180 (median, pts) |
       |---|---|---|---|---|---|
       | illness | 994 | 206 | +3.1 | +6.6 | +1.1 |
       | cycle | 461 | 112 | +3.5 | +5.0 | +1.6 |
       | stress | 445 | 145 | +1.8 | +4.9 | +0.9 |
       | alcohol | 176 | 76 | −4.7 | −4.1 | −2.0 |
       | hypoglycaemia symptoms | 1,042 | 147 | −6.9 | −5.7 | −3.5 |
       | hyperglycaemia symptoms | 3,658 | 97 | +0.9 | +2.0 | +3.4 |

       - **Illness checks out.** The sim's illness episodes measured the same way (c145, first 24 h vs ±2–14 days,
         16 episodes): median +4.4, mean +6.2. That matches the donors' +3.1 / +6.6, a first data validation of the
         component's size (it is sized from literature).
       - **Cycle.** The menstrual component is off by default (stress scenarios only), yet donors who log "cycle"
         run +3.5 / +5.0 mg/dL in the next 24 h. Logged cycle is probably period onset; the component's luteal SI dip
         (8%) peaks before it. Worth a matched test: phase timing against these logs.
       - **Alcohol lowers next-day glucose** (−4.7), the direction of the sim's alcohol term (EGP ×0.85 the morning
         after). Stress raises it a little (+1.8), consistent with the reactive-third SI −10% term.
       - Logging is voluntary and episodic (one log per event), so these are lower bounds on a day-level effect.
     - **The cycle has a shape in the donors who log it.** Daily CGM mean relative to the same event's ±30-day mean,
       days around a logged "cycle" (493 events, 125 users; mean / median):
       - days −10..−2 about +2 / ~0;
       - −1 +4.0 / +2.3; 0 +4.7 / +3.4;
       - +1..+2 −0.9 / −2.5; +3..+6 about +2 / ~0;
       - +7..+10 −3.3 to −3.6 / −5.
       Elevated before and on the log day (late luteal into menses onset) and low a week after (follicular): a
       6–8 mg/dL swing under Loop's compensation. The sim's luteal dip peaks mid-luteal and is gone at menses, a
       different timing. The ice screen's "no monthly rhythm" was population-wide (unlogged cycles average out);
       loggers show it.
     - Next (evidence-based component): enable the cycle for menstruating people with a shape from these logs (SI
       lower through the late-luteal days, recovering by day ~3 after onset; follicular baseline), sized so the
       simulated logged-day profile matches. A default-on decision for Pete.
     - **`--enable menstrual_late`** (4e6c263; menstruating responders as before: 63%, amplitude lnN(0.08, 0.5)).
       c152 vs c145: 33 vs 35 matched (noise); t70 2.34 (2.45), hurst_long 0.239 (0.217), TDD CV 14.9, night insulin
       CV 38.7. The simulated onset profile (269 responder-days, ~12 per offset in 14-day windows) is too thin to
       compare: day 0 +6.8, consistent with the donors' +4.7, with single offsets swinging −18 to +30. A dedicated
       check needs menstruating people over full cycles (≥ 60 days). The shape is now evidence-based (BDDP logs).
       Default-on is Pete's call; the cohort cost is nil.

137. **Structured exercise checks out against BDDP workouts, under Loop, at the same measurement.** First data
     validation of the exercise component (C1–C5), which is sized from literature.
     - **Donors.** HealthKit workouts (`physicalActivity`, 10–180 min) of Loop users in a hashed 1-in-20 user sample:
       18 k workouts, 76 users, median 33 min, ~5 kcal/min. "Clean" means no carb entry or bolus in the 2 h before
       the start. Control instants are the same person at the same clock time ±2/5/9 days, clean, with no workout in
       the 24 h before or 10 h after. The excess is the workout's ΔCGM from the 15 min before the start minus the
       same person's control ΔCGM in the same 20 mg/dL starting band (start-glucose matching removes regression to
       the mean, which dominates the raw split). Value: median user.
     - **Sim.** The default people over 56 days (c154, frozen 17c4c51; 1,827 sessions, 546 clean with matched
       controls, 51 people), measured with the same script logic on the sim CGM (`sim_workout.py`).

       | min from start | 15 | 30 | 45 | 60 | 90 | 120 | 240 | 360 | 480 |
       |---|---|---|---|---|---|---|---|---|---|
       | donors | −8.3 | −15.4 | −17.0 | −14.5 | −7.6 | −2.7 | +0.7 | −6.2 | −7.2 |
       | sim | −8.6 | −7.9 | −12.5 | −10.7 | −5.4 | −4.3 | −8.1 | −6.5 | +3.4 |

       95% bootstrap intervals over users overlap at every bin: 45 min donors −21.1..−12.6, sim −19.0..−7.3;
       360 min donors −9.7..−3.2, sim −16.3..+3.0. The acute drop, its recovery by 2 h and the size of the late
       after-effect (6–8 h, delayed sensitivity) are all in the donors' range; the sim's acute drop sits at the
       weak end (~70% of the donors' median at 30–60 min).
     - **Glucose dependence (C1 mass action).** Donor excess at 45 min by starting glucose: < 120 −2.3, 120–180
       −18.2, > 180 −31.1 (the shape Dhaliwal 2025 reports). Sim: −7.4, −10.6, −61.3 (14 people above 180).
       Steeper in the sim at high starts, on few people; not acted on.
     - Logged workouts are deliberate exercise (HIIT, strength, elliptical, cycling, yoga), so this validates C5
       sessions, not everyday activity (C6). By type the donors' acute drop is largest for aerobic (−19.8 at 45 min)
       and smallest for HIIT (−7.9, 8 users), consistent with the anaerobic EGP surge (C4, built, 0 until
       calibrated); strength and yoga run −13 to −16 and carry a longer tail. No change to the defaults.
     Data and scripts: `runs/2026-10-18-additive-workouts/`.

138. **Alcohol and stress, measured the donors' way, are inside the donors' (wide) range.** Sim twin of the
     reportedState check (LESSONS 136): CGM mean in the 24 h after an alcohol evening (anchored at 21:00; the donors
     log at 18–03 local) or a stress onset, minus the same person's mean on days −14..−2 and +2..+14. c154 (56 days,
     default people), episodes reconstructed from the person's seeded draws (`sim_states.py`):

     | | sim events / people | sim median Δ | donor events | donor median Δ (95% CI, events) |
     |---|---|---|---|---|
     | alcohol | 371 / 56 | −1.2 | 176 | −4.7 (−10.4 .. +0.9) |
     | stress | 912 / 43 | −1.0 | 445 | +1.8 (−0.7 .. +4.1) |

     - Alcohol: the evening SI loss (−12%) and the morning-after EGP ×0.85 nearly cancel in the sim. Donors lean
       lower, the direction of the morning effect, but the interval holds the sim's value. Logged drinking is
       probably heavier than an average drinking night, so the donors' size is an upper bound on the typical night.
     - Stress: the sim sits just below the donors' interval. Its stress days are 40% of days, so its baseline
       carries stress too; donors' baselines carry unlogged stress the same way. Logged stress is selective
       (a remembered, larger stressor), which would make the donors' +1.8 an upper bound as well.
     Neither is evidence for a change. With illness (LESSONS 136), cycle (B5) and exercise (LESSONS 137), every
     life factor that BDDP records now has a data check alongside its literature size.

139. **The "slow" late phase is not slower than a saturated stomach; the post-meal dip happens with the meal half
     absorbed.** `--set meal_slow=0.25 / 0.35` (c155, frozen 17c4c51) against the default 0.15 (c153):

     | | 0.15 | 0.25 | 0.35 |
     |---|---|---|---|
     | true appearance t25 / t50 / t75, min (`ra_traj.py`, isolated meals ~55 g) | 62 / 111 / 164 | 60 / 105 / 152 | 58 / 99 / 156 |
     | temp ΔCGM per 10 g at 60 / 120 / 180 min | +2.6 / −2.8 / −3.3 | +2.5 / −2.9 / −3.2 | +2.4 / −3.3 / −2.9 |
     | automatic, same | +1.1 / −2.6 / −4.4 | +0.9 / −3.5 / −4.2 | +0.8 / −3.5 / −4.2 |
     | matched | 33 | 29 | 32 |

     Donors: temp +6.4 / +5.2 / +5.5, automatic +4.3 / +4.3 / +5.4 (lesson 130).
     - A larger slow share speeds appearance. The slow parcel empties at a fixed kmin 0.008 /min outside the energy
       ceiling, while the main parcel of a 50–60 g meal is held by the ceiling (A10) more slowly than that. The
       share is not a tail lever at these meal sizes.
     - At 120 min only 55% of the meal has appeared, yet simulated glucose is already below its start. The dip is
       insulin outrunning a meal that is still arriving, not a meal that has finished. Donors take ~10% more
       insulin per entered gram (lesson 92) and hold +5 per 10 g, so in effect each real unit of meal insulin lowers
       glucose less, or each real gram raises it more, than in the sim, in the 1.5–4 h window.
     - Tracer evidence does not ask for a slower meal: a T1D mixed-meal triple-tracer study (6 lean adults; secondary
       report, primary not read) puts 50% of meal glucose at ~55 min with or without prandial insulin, faster than
       the sim's 111; Elleri 2013's
       121 g meals 130 / 178 min. Appearance stays at its default.
     Default unchanged (0.15).

140. **Glucocorticoid courses (B14) built; and the ISF semantics trade, re-measured with the right constant.**
     - **B14, oral glucocorticoids** (catalog D13, the largest unbuilt effect). Per person 0.09 courses/year (Waljee
       2017: 21.1% of US adults had ≥ 1 short course in 3 years; half were a 6-day dose pack). A course lasts U(4, 7)
       days with a morning dose N(08:00, 45 min). SI loss is zero until 2 h after the dose, ramps in to 6 h, holds to
       12 h and is gone by 22 h: fasting near normal, highs in the afternoon and evening (hospital guidance,
       PMC8157052). The peak loss is U(0.35, 0.60) on day 1, tapering linearly; Bevier 2008 needed +69% insulin
       (30–100%) from 6 h after the first prednisone dose, back to baseline by day 4 [J for the peak]. Day 1 averages
       SI 0.78 (about +29% insulin need, the guidance's "≥ 30%"), with a 0.51 peak. On its own stream (seed + 303).
       The default cohort is unchanged (c156 = c153: 33 matched, same people).
     - **Scenario `--enable steroid_course`** (one course from day 3; c156_ster paired with c156_base, 112 people):

       | window | Δ mean | Δ t>180, pts | Δ t<70, pts | insulin ratio |
       |---|---|---|---|---|
       | day 3 | +20.6 | +10.1 | 0.0 | 1.12 |
       | day 3, 14–22 h | +47.6 | +22.2 | 0.0 | 1.12 |
       | days 3–8 | +11.1 | +5.7 | −0.45 | 1.06 |
       | days 9–13 | +0.3 | +0.1 | 0.0 | 1.00 |

       Loop's own feedback adds 12% insulin on day 1, against Bevier's 69%. The rest shows as afternoon-evening
       highs, the clinical pattern. People who raise basal or set an override for a course are not modeled
       (no steroid-aware behavior); a candidate that adapts faster should show its gain here.
     - **ISF semantics, re-measured.** The `isf_total` switch had run with the peak calibration's labeler constant
       (1.25); lesson 75 requires 1.08 under total-drop, now wired (df55f5e). c157 against c156:
       - temp entry-anchored ΔCGM per 10 g at 60 / 120 / 180 min: +2.8 / +3.3 / +1.5 (peak +2.6 / −2.8 / −3.3;
         donors +6.4 / +5.2 / +5.5); automatic +2.2 / +1.6 / +0.6 (+1.1 / −2.6 / −4.4; donors +4.3 / +4.3 / +5.4);
       - CV 35.0 passes (peak 38.4; donors 34.8); but mean 177.6, TIR 56, t70 0.44, TDD 46.0 (38.8); 23 vs 33 matched.
       The constant was not why lesson 132's arm ran high: total-drop semantics still under-insulinise the bodies.
     - **The self-check reads the same trade from the other side.** A perfect person (every gram entered and
       bolused, disturbances off) on the default: nights 50 below rest (median), 3 of 8 within 40. Under total-drop
       with the linear CR, all 8 pass (−16 to −27). On the default bodies the linear-part total drop per unit is a
       median 2.16× the calibrated (peak) ISF (q25/75 1.82 / 2.49; 24 people), while the intake balance (carbs =
       non-basal TDD × ISF ÷ linear CSF) books that ISF as a total. That is lesson 40's bookkeeping gap: it is kept
       because it alone holds the cohort's TDD (38.9 vs 38.8). The failing self-check is that known gap, deeper since
       the slower EGP arm (p2e 0.010 gives nights −45; 0.006 −50), not a B14 regression (identical at 17c4c51).
     - Reading: peak semantics give the levels and TDD and over-cover meals; total semantics give the meal plateau
       and CV and under-insulinise everything. The donors have both, so the missing piece acts at meals only and is
       not a scalar on insulin action (lesson 133). Scripts: `runs/2026-10-18-additive-workouts/`.

141. **Pregnancy (X9) as a scenario: falling need early raises lows; the SI form realizes ~90% of the target need.**
     `--set preg_week=W`: menstruating people are pregnant at week W on day 0, with no menstrual cycle. Insulin need
     ÷ pre-pregnancy follows García-Patterson 2010's three changes of direction: up to week 9 (+10% [J]), down to a
     week-16 nadir (0.95 [J]), +5%/week linear to week 36 (ADA Standards 2023 §15), falling after 37 (J Perinatol
     2021). The body's SI is divided by the need. Settings start titrated to the need at week W (basal, max basal ×
     need; ISF, CR ÷ need), so only the change within the window is new to the controller. Paired with the same
     people in c156_base (49 pregnant of 112; c159, frozen ba1a923):

     | arm | window | Δ mean | Δ t<70 (median / mean, pts) | Δ t<54 mean | insulin ratio |
     |---|---|---|---|---|---|
     | week 9 (need 1.10 → 1.03) | days 2–5 | −2.6 | +0.35 / +0.57 | +0.18 | 1.08 |
     | | days 10–13 | −5.1 | +0.43 / +0.66 | +0.32 | 1.06 |
     | week 28 (1.52 → 1.67) | days 2–5 | −7.2 | +0.27 / +1.07 | +0.28 | 1.44 |
     | | days 10–13 | −5.1 | +0.46 / +1.04 | +0.27 | 1.45 |

     - Week 9: the falling need pulls glucose down across the window and lows rise under stock Loop, the direction of
       the clinical first-trimester risk (most severe hypoglycaemia before week 16, García-Patterson 2010).
     - Week 28: with settings ×1.52, glucose runs 5–7 lower and Loop delivers ×1.44, so SI ÷ 1.52 makes the body
       need only ~×1.4 insulin. Insulin-independent uptake (SG) is untouched, so a need ratio expressed through SI
       alone comes out ~10% short; the titration then over-doses a little. Known limit of the scenario; mapping the
       need to SI exactly would take a per-person probe.
     - A first version without titration (c158, settings left at pre-pregnancy) put week 28 at +26 to +31 mg/dL
       on day 0, which no clinic would leave; titrated starts are the scenario's definition.
     Off by default; for candidate testing on a steadily changing need.

142. **Under total-drop ISF the excess is daytime, not basal; the basal share does not move it.** c160 (`--enable
     isf_total --set basal_share=0.50 / 0.55`, frozen ba1a923) against c156_base and c157_total (share 0.42):

     | | default (peak) | total 0.42 | total 0.50 | total 0.55 | donors |
     |---|---|---|---|---|---|
     | temp ΔCGM per 10 g at 60 / 120 / 150 / 180 min | +2.6 / −2.8 / −3.5 / −3.3 | +2.8 / +3.3 / +2.3 / +1.5 | +3.5 / +3.6 / +4.3 / +2.4 | +4.2 / +3.6 / +3.9 / +3.1 | +6.4 / +5.2 / +5.5 / +5.5 |
     | mean / TIR | 148 / 70 | 178 / 56 | 179 / 55 | 175 / 57 | 151 / 72 |
     | CV | 38.4 | 35.0 | 33.8 | 32.5 | 34.8 |
     | t70 / lows per day | 2.34 / 1.42 | 0.44 / 0.42 | 0.34 / 0.29 | 0.26 / 0.25 | 1.67 / 1.08 |
     | TDD | 38.9 | 46.0 | 43.0 | 43.1 | 38.8 |
     | matched | 33 | 23 | 22 | 19 | |

     Median glucose by 3-h local block (default / total 0.42 / total 0.50): 00–03 150 / 182 / 182; 03–06 129 / 151 /
     152; 06–09 130 / 136 / 140; 09–12 151 / 170 / 169; 12–15 158 / 185 / 188; 15–18 159 / 186 / 187; 18–21 155 /
     191 / 194; 21–24 157 / 197 / 196.
     - The fasting morning is near the default's (+6 to +10); the excess builds through the waking day (+19 by noon,
       +36 to +40 in the evening) and drains overnight. So total-drop bodies under Loop fail to clear the day's
       intake, not to hold the basal state; a larger basal share (fewer grams eaten for the same TDD) leaves it.
     - The meal shape improves further with the share (temp +4.2 / +3.6 / +3.9 / +3.1 at 0.55, the closest to the
       donors yet), and CV goes below the donors'.
     - Reading with lesson 140: the per-unit effect that holds the day's level (corrections, Loop's automatic dosing
       on unannounced intake) is the peak calibration's; the per-unit effect after an entered meal is the total's.
       Next: split the total arm's daytime excess by source (entered meals, unannounced eating, rescues) with the
       labeled-event attribution, to see which intake the bodies fail to clear.
     - **Not per-event handling.** Sim CGM change per 10 g after isolated eating events (nothing else eaten −2 h /
       +4 h; `src_traj.py`), default vs total 0.50, at 60 / 120 / 240 min: entered meals +4.3 / +3.3 / −1.5 vs
       +4.3 / +4.6 / +0.7; unentered meals +5.3 / +8.7 / +2.8 vs +5.4 / +7.8 / +3.9; snacks +6.1 / +4.7 / −10.4 vs
       +5.1 / +3.0 / −7.0. Single events are handled about alike, within ~1–2 mg/dL per 10 g. The total arm's
       daytime excess lies in the overlapping, busy hours the isolation filter drops, or in the grams eaten (the
       intake balance books ISF ÷ CSF the same way under both semantics while the bodies' insulin action differs by
       ~2×, lesson 140). The next measurement is the daily grams-in vs insulin-effect budget per arm.

143. **The intake budget leaves out grazing and hypo treatment; with all intake inside it, total-drop ISF holds the
     donors' meal plateau at the donors' TDD.**
     - **The surplus.** Grams eaten per day, median person (`budget.py`, c156 default): meals 122, snacks 47, grazes
       21.5, proactive 20.5, rescues 7.9; total 256 against a TDD-derived budget of 148 (+ ~28 activity). Meals and
       snacks share the budget; grazes ("never entered, never bolused") and the defense carbs are added outside it.
       The donors' TDD paid for all of their eating, unlogged grazing and hypo treatment included, so the sim's
       people eat 40–50 g/day more than their insulin was sized for. The peak calibration's ~2× insulin action
       (lesson 140) absorbs it, at the cost of extra lows whose treatment adds to the surplus.
     - **`--enable budget_all`** (3076b72; off): the budget also pays for the person's expected grazing and the
       donor's measured rescue carbs (template rescues_per_day × rescue_size_med), floored at half. c161 against
       c156 (first launch at efb9033 did not reach the Behavior and reproduced its controls exactly; fixed):

       | | default (peak) | total + budget 0.42 | total + budget 0.50 | peak + budget | donors |
       |---|---|---|---|---|---|
       | temp ΔCGM per 10 g at 60 / 90 / 120 / 150 / 180 min | +2.6 / +0.4 / −2.8 / −3.5 / −3.3 | +4.3 / +5.2 / +4.7 / +4.3 / +3.8 | +5.4 / +5.4 / +6.8 / +5.9 / +4.3 | +4.3 / +1.8 / −0.8 / −1.5 / −1.9 | +6.4 / +5.9 / +5.2 / +5.5 / +5.5 |
       | automatic, 60 / 120 / 180 | +1.1 / −2.6 / −4.4 | +2.8 / +2.7 / +0.9 | +3.3 / +3.1 / +2.3 | +1.6 / −2.0 / −4.3 | +4.3 / +4.3 / +5.4 |
       | mean / TIR | 148 / 70 | 167 / 62 | 166 / 64 | 145 / 72 | 151 / 72 |
       | CV (KS p) | 38.4 (0.000) | 35.2 (0.55) | 33.4 (0.04) | 38.2 (0.000) | 34.8 |
       | TDD (KS p) | 38.9 (0.99) | 40.4 (0.68) | 39.3 (0.90) | 35.7 (0.22) | 38.8 |
       | t70 / lows per day | 2.34 / 1.42 | 0.54 / 0.50 | 0.35 / 0.33 | 2.78 / 1.67 | 1.67 / 1.08 |
       | hurst_long | 0.239 | 0.400 | 0.376 | 0.183 | 0.247 |
       | grams eaten / day | 256 | 209 | 183 | 226 | |
       | matched | 33 | 21 | 18 | 25 | |

     - Total-drop ISF with the whole intake inside the budget is the first configuration whose entered meals hold
       the donors' plateau (temp within ~1–2 mg/dL per 10 g through 3 h), at the donors' TDD and CV. Under the peak
       calibration, closing the budget only deepens the over-insulinisation (lows 1.67/day, mean 145): the
       calibration and the budget are one design.
     - Still wrong on that configuration: the level (+15 mean; 3-h blocks +10 overnight to +20–28 by day), too few
       lows (t70 0.35–0.54 vs 1.67), long-range Hurst 0.38–0.40 (0.25). The bodies now have no hidden insulin
       excess, so the donors' lows must come from components the sim lacks or under-sizes on the low side
       (over-boluses, exercise, insulin action variability), not from a calibration surplus.
     - A default change (ISF semantics and the intake budget together) is Pete's call; the evidence for both halves
       is the donors' TDD covering all intake and the entry-anchored meal trajectory.
     - **Adopted (Pete, 2026-10-18): total-drop ISF + the full intake budget are the base** (ac6b40e; `--disable
       isf_total,budget_all` restores the previous base). The self-check now doses at the linear truth CR, the
       semantics' consistent ratio: nights at rest for 8 of 8 bodies (the effective peak-probe CR under total-drop
       under-doses: median night +32). Three bodies still fail the day guard on open-loop meal extremes in both
       directions: highs to ~720 and, after stacked entries (~96 g within 15 min, bolused at once), falls to the
       10 mg/dL floor. A quiet body reaching 10 mg/dL despite counter-regulation is an open physiology item for the
       low end (A9), separate from units.

144. **On the new base the level excess belongs to the heavy enterers and the automatic-bolus group; it is not their
     carb ratio.** c162_base (= c161_tb42, verified identical) against c156 (old base), per person minus own donor
     (`twin_split.py`), median:

     | group | old base Δ mean / Δ TIR / Δ CV | new base Δ mean / Δ TIR / Δ CV |
     |---|---|---|
     | automatic bolus | −2.1 / −1.0 / +2.6 | +16.1 / −10.1 / −1.4 |
     | temp basal | −2.6 / −5.0 / +9.3 | +7.8 / −8.2 / +5.4 |
     | donor entries/day, low tercile | −4.6 / −0.2 / +2.3 | +7.9 / −4.3 / −1.1 |
     | mid | −5.1 / +0.2 / +3.1 | +8.5 / −9.0 / +0.7 |
     | high | +8.1 / −8.3 / +8.8 | +25.9 / −13.5 / +4.4 |

     - The temp-basal CV gap halves (+9.3 → +5.4); the heavy enterers' excess, already the worst on the old base
       (+8), grows to +26.
     - **Not their CR.** Settings ÷ body CR (`cr_cover.py`): low / mid / high tercile 1.30 / 1.21 / 1.18 (old base
       1.51 / 1.40 / 1.37); ISF ratio 0.99–1.07 in every tercile. The heavy enterers are the best covered in the
       ratio sense.
     - Heavy enterers are the hands-on, tight-control donors (many small entries and boluses). Next: what those
       donors do that the sim's people do not, per meal (pre-bolus lead, bolus per gram, top-ups), on the new base.
     - **The meal response splits by tercile in the sim, not in the donors.** Entry-anchored ΔCGM per 10 g at 60 /
       120 / 180 / 240 / 360 min (`entry_traj_t.py`; donors G7 all strategies, sim c162 G7):

       | tercile | donors | sim (new base) |
       |---|---|---|
       | low | +5.1 / +4.0 / +4.4 / +2.0 / −1.5 | +2.8 / +3.0 / +1.8 / +2.1 / +0.3 |
       | mid | +4.9 / +5.1 / +5.6 / +4.1 / +0.3 | +2.4 / +1.0 / +0.5 / +0.3 / −0.4 |
       | high | +5.3 / +4.1 / +5.9 / +4.4 / +0.4 | +5.2 / +8.6 / +7.3 / +3.7 / +0.7 |

       Real meals respond alike whoever enters them. The sim's heavy enterers rise twice the donors' at 2 h (under-
       covered in effect, the +26 level) and the mid tercile barely holds (over-covered). The cohort median hid two
       opposite per-person errors, so the per-person carb sensitivity (CSF blended halfway toward settings ISF ÷ CR,
       ISF_W 0.5) or the per-person intake budget is the suspect, not a population constant. Next: per person,
       body CSF and grams eaten per entry against the tercile.
     - **Not the CSF match, and meal size is real.** By tercile (low / mid / high): body CSF ÷ settings ISF/CR 1.30 /
       1.16 / 1.06; median entry 38.5 / 27 / 21.5 g; entries per day 1.2 / 2.7 / 4.6 (`csf_tercile.py`). The heavy
       enterers' bodies match their settings best. By entry size, ΔCGM per 10 g at 60 / 120 / 180 / 240 min:

       | size | donors | sim (new base) |
       |---|---|---|
       | 20–30 g | +8.3 / +7.4 / +7.0 / +2.2 | +5.4 / +6.8 / +6.2 / +1.9 |
       | 30–45 g | +6.1 / +6.0 / +6.6 / +4.9 | +3.5 / +3.9 / −0.3 / +0.5 |
       | 45–70 g | +3.8 / +3.5 / +4.8 / +4.4 | +3.2 / +4.2 / +3.7 / +2.9 |
       | 70 g + | +2.7 / +2.8 / +4.1 / +3.4 | +1.5 / +0.4 / −0.1 / +1.1 |

       Real meals rise more per gram when small (the saturating emptying the sim models), and the sim follows that
       ordering. What it misses is the 2–4 h hold of the 30–45 g and the large meals, which fall back early. The
       heavy enterers' over-rise at 2 h is their small-entry mix (their donors' tercile rises less at 2 h than the
       donors' 20–30 g bin, so part of the comparison is composition). Open: the 2–4 h hold of mid-size and large
       meals on the new base.

145. **The new base's missing lows are mostly after meals.** Low onsets (CGM crosses below 70 after ≥ 30 min at or
     above 70) per person-day, by time since the last carb entry ≥ 5 g and since the last manual bolus ≥ 0.3 U (a
     meal bolus has an entry within 15 min); G7 people, donors' own records against the sim (`low_ctx.py`):

     | | entry < 2 h | 2–4 h | 4 h + | total | meal bolus < 2 h | lone bolus < 2 h |
     |---|---|---|---|---|---|---|
     | donors (16,492 days) | 0.270 | 0.166 | 0.623 | 1.059 | 0.227 | 0.087 |
     | old base (c156) | 0.331 | 0.303 | 0.809 | 1.442 | 0.286 | 0.108 |
     | new base (c162) | 0.080 | 0.081 | 0.426 | 0.588 | 0.068 | 0.029 |

     - A quarter of real lows start within 2 h of a carb entry, and four in ten within 4 h. The old base made them
       from over-insulinised bodies (and too many 2–4 h after: 0.30 vs 0.17); the new base, consistent in its
       units, makes a third of them. Lows more than 4 h after eating are 68% of the donors' rate.
     - So the early post-meal lows are a real-world mismatch the sim does not yet produce: meals that deliver less,
       or later, than the person dosed for. Candidates with evidence to size, not knobs: per-meal carb-count error
       in the over-count direction (Brazeau 2013 spread, the sim has the under-count mean), food entered and not
       all eaten, within-person meal-to-meal emptying variability, and the bolus lead when eating is delayed.
       Lesson 129's donor RC (glucose 3–4 below Loop's forecast in the first 2 h after entries) is the same signal
       seen through the forecast.

146. **Real meals vary more in their first hour; at the same starting glucose they end in a low 2–4× as often.**
     - **Donors' early lows follow ordinary meals.** Low onsets within 2 h of an entry, per day, by that entry's
       size (5–15 / 15–30 / 30–60 / 60+ g): donors 0.054 / 0.093 / 0.098 / 0.026, new base 0.010 / 0.015 / 0.028 /
       0.027; by minutes since the entry (0–30 / 30–60 / 60–120): donors 0.058 / 0.071 / 0.141, sim 0.021 / 0.010 /
       0.048 (`low_ctx2.py`). Not proactive treatment entries: most follow 15–60 g meals, at 1–2 h. Large meals
       already match.
     - **Brazeau's size-dependent count error is a small part.** `--enable count_brazeau` (771d9ad; off): the mean
       log count error follows estimate − actual = 10.54 − 0.28·g (Brazeau 2013, 692 T1D meals), held at the 20-g
       value below 20 g [J: ×1.75 at 10 g is outside the data]; entered ÷ eaten by size 1.20 (15–30 g), 0.96
       (30–60), 0.85 (60+), against the default's 0.98 / 0.89 / 0.85. c163: early lows 0.080 → 0.093/day, all lows
       0.59 → 0.61, 21 → 25 matched; mean 166 unchanged.
     - **Not the starting level.** P(low within 2 h | BG at a ≥ 15 g entry), by band < 90 / 90–110 / 110–130 /
       130–160 / 160–200 / 200+ (`low_ctx3.py`): donors 0.196 / 0.142 / 0.106 / 0.102 / 0.088 / 0.050; sim 0.126 /
       0.037 / 0.044 / 0.045 / 0.018 / 0.023. The sim's meals start higher (median 159 vs 138), but at equal start
       real meals go low 2–4× as often, even from 160–200.
     - **The first-hour spread is short.** Entry-anchored ΔCGM per 10 g, p10 / p25 / p50 / p75 / p90: at 60 min
       donors −13.9 / −3.8 / +5.0 / +15.2 / +27.3 (IQR 18.9), sim −9.7 / −2.2 / +3.2 / +10.0 / +21.4 (IQR 12.1); at
       120 and 180 min the spreads are close (IQR 23.3 / 23.3 vs 20.6 / 22.6). Real meals differ more from one
       another in their first hour, both ways. Per-meal sources that set that spread: the bolus-to-eating offset
       (lead, SD 23 min), the meal's own emptying speed (lnN 0.4) and fast share (Beta SD 0.25), absorption jitter
       (15%). Next: which of them is under-sized against its evidence, not a wider knob.

147. **The sim's per-meal variance sources do not set the first-hour spread.** One at a time on the new base (c164,
     frozen ecffc99; `--set gi_cv`, `lead_sd`, `meal_fast_sd`), entry-anchored ΔCGM per 10 g IQR at 60 / 120 /
     180 min and low onsets per day:

     | arm | IQR 60 / 120 / 180 | lows / day |
     |---|---|---|
     | new base (c162) | 12.1 / 20.6 / 22.6 | 0.588 |
     | emptying speed fixed (gi_cv 0) | 13.3 / 20.3 / 21.0 | 0.576 |
     | emptying speed wider (gi_cv 0.7) | 12.7 / 20.8 / 22.3 | 0.599 |
     | bolus lead fixed (lead_sd 0) | 14.7 / 21.4 / 23.1 | 0.557 |
     | fast share fixed (meal_fast_sd 0) | 11.8 / 19.3 / 23.8 | 0.561 |
     | donors | 18.9 / 23.3 / 23.3 | 1.059 |

     Switching any of them off or widening the emptying spread moves the 60-min IQR by ≤ 2.6 and the lows by ≤ 0.03
     per day. P(low within 2 h | BG at entry) moves within noise in every band.
     - **Entries are made later in real meals.** ΔCGM over the 15 min before a ≥ 20 g entry, p10 / p25 / p50 / p75 /
       p90 (`entry_traj_pre2.py`): donors −16.7 / −7.4 / +0.7 / +13.6 / +31.6, sim −16.7 / −7.6 / −0.4 / +8.5 / +18.0.
       A quarter of donor entries come with glucose already rising (eating begun before the entry); the pre-entry
       trend barely predicts the next hour (corr −0.08 donors, +0.15 sim).
     - Absolute ΔCGM 0 → 60 min: donors p10 / p90 −52 / +101 (IQR 79), sim −40 / +88 (IQR 58). The real spread is
       wider on both sides, not from momentum, and not from the meal's own speed, count error or lead spread at
       their current sizes. What differs per meal remains open: candidates are the meal composition actually eaten
       (the share of the entry that is glucose-available, per meal rather than per person) and Loop's own dosing
       response, which differs between real and simulated bodies early in a meal.

148. **The people's own meal insulin matches; what is left is Loop's automatic dosing after meals.** Bolus insulin
     per 10 g entered around isolated entries ≥ 20 g (no other entry ±3 h; `meal_bolus_iso.py`), mean:
     - manual, −15 to +60 min: donors 1.15 (p10 / p90 0.57 / 2.14 including automatic), new base 1.14 (0.47 / 1.90);
     - manual, +60 to +180 min: donors 0.12, new base 0.05;
     - automatic, +60 to +180 min: donors 0.21 (p90 0.70); the sim books automatic boluses inside its temp-basal
       segments (lesson 99), so they do not appear in this count.
     Top-up events realize at the donors' rate on the new base (cohort 84.7 vs 90.1/day). Meal-time behavior is not
     where the first-hour spread or the early lows come from. The open comparison is Loop's own automatic insulin in
     the first 3 h after meals, measured as delivery above the scheduled rate on both sides (lesson 92's method,
     last run on the old base).
     - **Loop's dosing matches too.** All delivered insulin (basal + bolus, manual + automatic) above the person's
       median 5-min delivery, U per 10 g around isolated entries, windows −30–0 / 0–60 / 60–180 / 180–300 min
       (`meal_deliv.py`; donor bins outside dose-timeline coverage dropped, ≥ 90% coverage per entry):
       - donors (15,978 meals): 0.109 / 1.245 / 0.352 / 0.703, total 2.41; 60–180 p10 / p90 −0.18 / 1.14;
       - new base (1,164): 0.093 / 1.170 / 0.351 / 0.644, total 2.26; p10 / p90 −0.19 / 1.17;
       - old base (1,287): 0.096 / 1.165 / 0.229 / 0.611, total 2.10; p10 / p90 −0.24 / 0.89.
       On the new base the insulin around meals is the donors', in level and in spread, so the wider first-hour
       glucose spread and the early lows are on the glucose side: how much glucose a real meal delivers per
       entered gram, meal by meal (composition: fibre, fructose, fat, protein, what is actually eaten). The sim
       varies that per person (f, CSF) and in timing per meal, not in amount per meal. Next: evidence for the
       meal-to-meal spread of glucose appearance per labeled gram, and a named per-meal bioavailability term.

149. **The first-hour spread is within each person, and none of the per-meal random terms sets it.**
     - Per-meal count spread off / doubled (`--set count_sd_mult=0 / 2`, c165 on c7fd7b8): 60-min IQR 12.2 / 11.9
       (new base 12.1); lows 0.55 / 0.61 per day; 22 / 22 matched. With lesson 147 (speed, lead and fast-share
       spreads), every per-meal random term leaves the 60-min IQR within 11.8–14.7.
     - **Within, not between.** Entry-anchored ΔCGM per 10 g at 60 min, people with ≥ 5 isolated entries: donors
       (117) between-person IQR of person medians 7.5, median within-person IQR 19.1; sim (52) 5.9 and 12.2. Real
       people's own meals differ from one another more, by about the whole gap.
     - The one measured per-meal difference is when the entry is made: ~22% of donor entries arrive with CGM up
       more than 15 mg/dL over the previous 15 min (eating begun before the entry), ~11% in the sim (lesson 147). A
       late entry anchors the window on a rise already under way, then Loop doses into it. Next: the share and the
       delay of late entries per donor, against the sim's entry-vs-eating offset (median −3 min, q10 / q90 −34 / +27),
       as its own named behavior.
     - **Faster first hours do not widen it either.** On the new base (c166, c7fd7b8): a sugary drink with 30% of
       main meals (`meal_drink_p 0.3`) / meal emptying ×1.4 (`meal_k 1.4`, towards the T1D tracer's ~55-min half
       appearance): temp ΔCGM per 10 g at 60 / 90 min +6.2 / +7.9 and +5.3 / +7.6 (new base +4.3 / +5.2; donors
       +6.4 / +5.9); within-person 60-min IQR 12.9 / 12.7 (donors 19.1); lows 0.62 / 0.64 per day; CV 35.8 / 36.3;
       24 / 23 matched (21). The first-hour median moves to the donors', the spread does not, and the cost in CV and
       falls of the old base (lesson 119) is now small. Not adopted: no gain on the spread or the lows.
     - Every meal-side term tried (count error, speed, lead, fast share, drink, emptying) leaves the within-person
       spread at 11.8–14.7. The term that sets it in the sim is not on the meal side; candidates are the state each
       meal starts from (circadian sensitivity slot, IOB, Loop's temp at the entry) and how far each real meal's
       eating extends after the entry (second helpings and desserts inside the window, which the isolation filter
       cannot see because they are not entered).

150. **Real first hours vary by the same absolute amount whatever the meal size; letting a meal's speed set its own
     emptying ceiling is part of it, not most.**
     - **Size-independent spread.** Within-person IQR of the absolute CGM change 0 → 60 min after isolated entries,
       by entry size 20–30 / 30–45 / 45–70 / 70+ g: donors 67 / 63 / 69 / 64 mg/dL (112 / 99 / 87 / 36 people), new
       base 42 / 35 / 59 / 54. Both sides' median first-hour rise is roughly size-independent too (donors ~+21 to
       +24 mg/dL, sim ~+13 to +18), the saturating-emptying signature.
     - **Why the sim's per-meal terms had no effect.** The stomach's energy ceiling was one per person: `scale =
       cap / (cap + kcal)` takes outflow to `cap` once a meal saturates it, so the meal's own speed (lnN 0.4, carried
       in each parcel's kempt) vanished for typical meals. Physiologically the outflow rate depends on what is in the
       stomach (liquid vs solid, fibre, viscosity, fat through its kcal).
     - **`--enable ceiling_speed`** (4368a05; off): the ceiling scales with the energy-weighted speed of the meals in
       the stomach. c167 against c162: within-person 60-min IQR per 10 g 12.2 → 13.1 (gi_cv 0.4) / 13.7 (0.6), donors
       19.1; absolute within-person IQR by size 43 / 47 / 55 / 59 and 48 / 48 / 59 / 59; lows 0.60 / 0.58 per day;
       22 / 23 matched (21). A real but small part of the missing spread; not adopted alone.
     - What is left is a meal-to-meal variance of ~±30 mg/dL in the first hour that does not scale with grams and
       is not the sim's composition, count, lead or speed terms. Sources not in the sim that would behave that way:
       how much of a meal is actually eaten (half-finished or second helpings, independent of the entry), and
       non-meal glucose moves coinciding with meals (activity or stress around mealtime). Neither is yet measured.

151. **Most of the new base's level excess is the fat resistance booked on top of the person's usual diet.**
     - **Not the settings.** Settings set to the body's truth (`--disable settings_mismatch`, c168 on c08976a):
       3-h profile within 1–4 mg/dL of the base (06–09 131, 21–24 181), mean 165, 25 matched.
     - **The fat term.** `--disable fat` (c169): mean 167 → 157, TIR 62 → 69, CV 34.8 (donors 34.8), TDD 39.9,
       lows 0.67/day; twin Δ mean automatic +16 → +3.4, temp +7.8 → +1.5, entries tercile low / mid / high
       −1.4 / +0.8 / +17.5; the excess that built from 09 h to midnight shrinks by 4–12 mg/dL per block; 24 matched.
     - **Why.** A12 dips SI by ρ·fat/50 from 2 to 10 h after every meal (ρ U(0.1, 0.6), sized to Wolpert 2013's
       high- vs low-fat dinner, an increment). The person's ISF, CR and TDD were tuned on their ordinary meals, fat
       included, but the term's average (a mean SI multiplier of 0.92 over the window, 0.82–0.96 across people) was
       booked on top of them. Under the peak calibration the ~2× insulin action hid it; under total-drop it shows as
       a day-long drift.
     - **`--enable fat_rel`** (44dcae1; off): the fat term divided by its own mean over the planned days, so a
       person's usual meals leave their sensitivity at its calibrated value and fattier-than-usual meals still dip it
       (the caffeine term's treatment of habitual intake). c170: mean 159, TIR 65.4, TDD 39.1, lows 0.58/day (onsets
       0.70), 24 matched; twin Δ mean automatic +12.9, temp +2.4, high-entries tercile +18.4.
     - Left after fat_rel: ~+8 mean, carried by automatic-bolus people and the heavy enterers. The protein parcel
       (0.1 g glucose per g protein, ~4.5% of carbohydrate grams) also sits outside the TDD budget, the same
       bookkeeping question; fat off entirely (157) bounds the two together.
     - **Adopted (Pete, 2026-10-18): `fat_rel` is the default** (`--disable fat_rel` restores the absolute term).

152. **Every simulated person ran standard RC; running their donor's deployed RC mode halves the automatic-bolus
     gap.** The plant export passed only the dosing strategy, so the 29 template donors who deployed integral RC with
     the clamp (rc_mode.csv, DTR forecast match per day; 20 automatic-bolus, 9 temp-basal; 36 "mixed" stay standard)
     were simulated with a weaker controller than their own. `--enable rc_own` (4141fbf; off) adds
     `--candidate-integral-rc --candidate-integral-rc-clamp` for them (19 people in the 112). c172 against c171:
     - twin Δ mean automatic +12.9 → +7.7, temp +2.4 → 0.0; entries tercile low / mid / high +5.7 / +2.2 / +18.4 →
       +3.2 / +2.0 / +16.5;
     - mean 159.0 → 158.8, TIR 65.4 → 66.6, lows 0.58 → 0.63/day (onsets 0.70 → 0.72), TDD 39.7; 24 → 24 matched.
     It is the deployment-faithful configuration, the same rule the replays follow (AGENTS: RC mode per dataset).
     What remains of the level excess is the heavy enterers (+16.5).
     - **Not adopted (Pete, 2026-10-18):** "Whether or not a patient runs IRC is a choice on the controller side
       where the session is about building a patient model that responds appropriately regardless of the dosing
       strategy. I want to avoid coupling the patient to strongly to loop." The patient model stays independent of
       the controller's configuration. For validation this means the twin gap of the 29 integral-RC donors
       partly measures a controller difference, not a patient one: compare like with like by reading those people's
       gaps with that in mind (or `rc_own` for a validation-only arm), never by tuning the patient to close them.
     - **Validation convention (Pete, 2026-10-18):** "it's perfectly fine to run simulations using a patient's real
       dosing model, to see how closely our patient simulator is working ... keep the patient's side as accurate as
       possible, regardless of dosing method." Validation cohorts against donors run with `--enable rc_own` from here
       on (the controller as the donor deployed it); the code default stays stock, for candidate testing.

153. **Hyperglycaemia-induced resistance is a small part of the long-range persistence.** `--disable glucotox`
     (B11 off; c173 on 4141fbf) against c171: hurst_long 0.379 → 0.353 (donors 0.247); mean 159 → 158; t70 0.73 →
     1.17, lows 0.58 → 0.75/day; twin Δ mean automatic +12.9 → +6.4, temp +2.4 → −2.7; 3-h blocks −1 to −11
     (largest 00–03 h); 26 vs 24 matched. B11's size is evidenced (Vuorinen-Markkola 1992, Fanelli 1995) and its
     24-h fade lies within those studies' bounds, so it stays; the persistence the sim adds over the donors (Hurst
     +0.13) is mostly elsewhere. The other slow terms on the new base are the day-level SI (B3, CV 8%), the late
     overnight carry-over of daytime excess, and the illness and menstrual states.

154. **Real corrections act sooner than the sim's; the total matches.** CGM change per unit after isolated manual
     corrections (≥ 0.5 U, no entry −2 h..+3 h, no other manual bolus −1 h..+3 h; G7; `corr_drop.py`), at 30 / 60 /
     90 / 120 / 180 min. Donors 4,146 corrections (median 2.0 U, BG 213, 15-min pre-trend +11.7); sim c172_rc 135
     (1.2 U, BG 220, +13.0):

     | dose | donors | sim |
     |---|---|---|
     | 0.5–1.5 U | −5.8 / −29.0 / −45.5 / −55.6 / −67.3 | −3.8 / −11.2 / −32.0 / −46.0 / −68.8 |
     | 1.5–3 U | −3.1 / −15.4 / −24.5 / −28.3 / −30.6 | +0.4 / −5.0 / −7.8 / −24.2 / −29.8 |
     | 3 U + | +0.3 / −1.8 / −4.8 / −7.0 / −9.5 | 0.0 / −3.2 / −11.2 / −15.8 / −21.4 |

     - For correction-sized doses the real drop is 2–3× the sim's at 60–90 min and the same by 3 h: same size,
       earlier timing. Starting glucose and pre-trend match, so it is not where the corrections are given.
     - The sim's insulin timing (p2 0.025, A2 kd/ka2) was set from a 15 U lispro clamp (lesson 114) and applies to
       every dose. Small subcutaneous depots absorb faster than large ones (depot surface-to-volume; established for
       regular insulin, Binder 1984; the Humalog label's 30–90 min peak range across 0.1–0.4 U/kg allows it for
       analogs), and corrections and Loop's automatic doses are 0.05–3 U. The 3 U+ band is confounded by unentered food
       behind large "corrections" (smaller than the sim per unit).
     - This is the timing that sets how fast every excursion is reversed, so it bears on the ACF zero-crossing (70 vs
       42.5) and long-range Hurst gaps. Next: dose-dependent absorption as a named A2 term, fitted to this observed
       correction timing by dose band (Pete: fit to observed data), checked against the 15 U clamp it must still match.

155. **Faster absorption of small doses does not give the real correction timing, and it re-opens the meal dip.**
     `--set dose_beta=β` (bc4b07a; off): each bolus depot absorbs at (dose / 15 U)^(−β), capped 0.7–3, so the 15-U clamp
     fit is unchanged (1 U at β 0.3: plasma insulin peak 56 → 33 min, 50% of exposure 85 → 45 min). c174 with rc_own,
     against c172_rc:
     - corrections 0.5–1.5 U, ΔCGM per U at 60 / 90 / 180 min: β 0.25 −12.8 / −26.0 / −60.0, β 0.4 −16.0 / −35.1 /
       −63.0 (base −11.2 / −32.0 / −68.8; donors −29.0 / −45.5 / −67.3). Plasma insulin arrives sooner but the effect
       still lags it through the action compartment (p2 0.025, ~40 min).
     - meals: automatic ΔCGM per 10 g at 120 / 150 min −1.0 / −1.2 (β 0.25) and −1.5 / −1.7 (β 0.4), against +1.1 /
       +0.5 — meal boluses of 2–8 U absorb faster too and the plateau goes.
     - acf_zero 70 / 65, hurst_long 0.370 / 0.374, lows 0.67 / 0.67 per day; 24 / 25 matched (24). Not adopted.
     - Reading: real corrections take effect sooner while real meals hold for 2–4 h. Faster insulin action alone
       cannot give both; together they say the late part of a real meal keeps glucose arriving after the bolus has
       acted (a longer appearance tail than the sim's energy-limited stomach produces, lesson 139), or that the
       action delay itself (p2) is shorter than the clamp fit and the meal tail longer. Both are candidates for one
       joint, evidence-bounded fit to two observed targets: the correction timing by dose and the entry-anchored
       meal trajectory.

156. **Neither a shorter action delay nor a slow meal tail gives the two targets, alone or together.** c175 (rc_own,
     bc4b07a) against c172_rc; corrections 0.5–1.5 U ΔCGM per U at 60 / 90 / 180 min (donors −29.0 / −45.5 / −67.3)
     and temp entry-anchored ΔCGM per 10 g at 60 / 120 / 180 min (donors +6.4 / +5.2 / +5.5):

     | arm | corrections | meals (temp) | CV | lows / day | hurst_long | acf_zero | matched |
     |---|---|---|---|---|---|---|---|
     | base (c172_rc) | −11.2 / −32.0 / −68.8 | +3.6 / +3.2 / +2.6 | 35.6 | 0.63 | 0.368 | 70 | 24 |
     | p2 0.04 | −14.0 / −18.5 / −46.3 | +3.7 / +2.3 / +2.4 | 35.7 | 0.63 | 0.362 | 65 | 25 |
     | slow tail (30% at kmin 0.003) | −17.6 / −30.7 / −55.2 | +3.6 / +2.5 / +0.7 | 32.1 | 0.46 | 0.350 | 65 | 24 |
     | both | −20.0 / −38.5 / −64.2 | +2.9 / +0.5 / +0.6 | 31.6 | 0.42 | 0.339 | 60 | 19 |

     - A shorter action delay moves the small-correction drop only part of the way (−11 → −14 at 60 min) and costs the
       total by 3 h; the slow tail, taken out of the meal's main parcel, lowers its 2–3 h hold rather than raising it,
       and it smooths the trace (CV 32, fewer lows, day/night 1.63). Together: closest correction timing yet (−20) but
       no meal hold and 19 matched. Not adopted.
     - Every insulin-timing and meal-shape lever tried so far moves the correction timing, the meal hold and the
       spread in fixed proportion to one another; the donors' combination (fast corrections, held meals, wide
       first-hour spread, more lows) is not on that line. That points at something the model lacks rather than a
       parameter: a source of glucose that rises during the 1–4 h after real meals and is independent of the bolus
       (food eaten after the entry and not entered; lesson 130's follow-on check counted labeled pulses, not their
       size), or real insulin action that is faster at corrections because correction-time glucose is falling from a
       peak the CGM has not shown yet.
     - **Not follow-on eating by size either.** Unannounced, non-rescue labeled pulses starting 0.5–4 h after an
       announced meal ≥ 20 g, g-eq per 10 g entered (`followon_size.py`; ice labeler on both sides): donors (31,549
       meals) mean 3.66, p75 5.87, 38% of meals with any; c172_rc (2,001) 3.24, 5.09, 39%. The meal's own labeled pulse
       9.82 vs 9.97 g-eq per 10 g. Follow-on intake is ~12% short in size and matched in frequency: not the gap. Of
       lesson 156's two candidates this leaves real insulin action at correction time; the next measurement is the
       donors' correction drop split by the CGM trend at the bolus (rising, flat, falling), against the sim's, to
       separate faster action from boluses given at a peak.

157. **Insulin action matches; real rises end sooner.** Corrections 0.5–3 U split by the 15-min CGM trend at the bolus,
     ΔCGM per U at 30 / 60 / 90 / 120 / 180 min (`corr_drop.py`):

     | trend at bolus | donors | sim (c172_rc) |
     |---|---|---|
     | flat (−5..+5; 19% / 24%) | −9.8 / −26.1 / −35.7 / −44.2 / −53.3 | −11.6 / −20.7 / −40.9 / −44.9 / −62.8 |
     | rising (> +5; 68% / 70%) | 0.0 / −17.7 / −30.7 / −36.1 / −41.8 | +3.1 / 0.0 / −4.8 / −27.0 / −41.7 |
     | falling (< −5; 13%) | −14.8 / −30.9 / −43.7 / −53.1 / −58.1 | (too few) |

     - From a flat start the sim's insulin lowers glucose as fast as real insulin, so lesson 154's gap is not insulin
       timing (and lessons 155–156's absorption and action-delay arms were aimed at the wrong term).
     - The gap is entirely in corrections given into a rise: real rises turn within ~30 min of the bolus, the sim's keep
       climbing ~90 min. Real glucose rises are briefer because what drives them stops sooner: the same signature as
       lesson 119 (real sharp rises peak within 30 min) and the ACF zero-crossing (42.5 vs 70 min).
     - Most rises that draw a lone correction are unannounced intake. In the sim, unentered snacks and grazes go through
       the energy-limited stomach and keep arriving for over an hour; real unlogged intake includes drinks and sweets
       that absorb within ~30 min. Next: the `graze_fast` and fast-snack arms on the current base, judged on the
       rising-trend correction profile and the ACF zero-crossing.

158. **Fast unlogged sugar shortens the sim's rises part of the way.** `--enable graze_fast` now empties grazes as
     liquid sugar outside the energy ceiling (5f44dee; before, "fast" grazes still shared the ceiling with any meal in
     the stomach). c176 (rc_own) against c172_rc:
     - rising-trend corrections 0.5–3 U, ΔCGM per U at 60 / 90 / 120 / 180 min: −4.1 / −14.8 / −33.8 / −52.1 (base
       0.0 / −4.8 / −27.0 / −41.7; donors −17.7 / −30.7 / −36.1 / −41.8); flat-trend unchanged (−20.5 / −30.0);
     - 27 vs 24 matched: day/night passes (1.83, KS 0.05), hurst_long 0.368 → 0.336, lows 0.63 → 0.67/day, TIR 67.98;
       CV 35.6 → 36.8 now fails; acf_zero stays 70; mean 157.8.
     - evidence/14 §2 sizes unlogged intake as 5–15 g of drinks and sweets; liquid sugar empties at ~3–8 kcal/min
       with glucose t½ ~9 min (Calbet 1997, Hunt 1985), so `graze_fast` is the evidenced form for that share. The rest
       of the rising-trend gap belongs to the other unentered intake (snacks and meals eaten without an entry), which
       still empties as solid food.
     - **Adopted (Pete, 2026-10-18): `graze_fast` is the default** (`--disable graze_fast` restores solid grazes).

159. **A sugar-heavier snack does not pay.** `--set snack_fast=0.5` (adf9ba2; snacks' fast-emptying share, default as
     meals 0.2): c178 (rc_own) against c177_base: rising-trend corrections ΔCGM per U at 60 / 90 min −7.1 / −16.1 (base
     −4.1 / −14.8; donors −17.7 / −30.7); CV 36.8 → 37.8, TIR 68.0 → 65.8, day/night 1.83 → 1.96 (donors 2.06),
     night insulin CV 42.4; 26 vs 27 matched. Not adopted (Piernas & Popkin give the direction, not a share).
     - The ACF zero-crossing has stayed at 65–70 min through every arm of lessons 147–159 (meal speed, ceiling, count
       spread, insulin absorption, action delay, meal tail, fast grazes, fast snacks). It is set by something none of
       those terms touches; lesson 76's split (meal rises too long, quiet stretches too still) on the current base is
       the next measurement.

160. **The ACF zero-crossing is still lesson 76's two-sided gap, on both bases.** Step-ACF zero-crossing (eda's
     `_acf`) split by time since the last eating or bolus event (`acfctx2.py`), median person:

     | | ≤ 3 h after an event | > 4 h after (quiet) | whole record |
     |---|---|---|---|
     | donors (168) | 40 | 40 | 40 |
     | new base (c177, rc_own) | 60 | 20 | 70 |
     | old base (c156) | 60 | 20 | 65 |

     - After events the sim's moves stay correlated 60 min against 40 (real rises turn sooner, lesson 157); in quiet
       stretches the sim's glucose is nearly still, so sensor noise sets a 20-min decorrelation where real quiet
       glucose keeps a ~40-min wander. Both halves are unchanged by the calibration and intake changes of lessons
       140–159, so neither is an insulin or meal-shape parameter.
     - Next for the quiet half: whether that wander is in true glucose or in the sensor. Compare the sim's quiet-period
       ACF of true glucose with its CGM's, and the donors' quiet ACF by sensor family (G6 / G7 / Libre 3): a sensor
       origin would differ by family, a physiological one would not.
     - **The quiet wander is not the sensor.** Donors' quiet-period zero-crossing by sensor family: G6 37.5 (26
       people), G7 40 (136), Libre 3 62.5 (6; its heavier smoothing). Two Dexcom generations with different noise agree
       on ~40 min. The sim's TRUE glucose in quiet stretches crosses at 130 min (CGM 20: the sensor noise sets it), so
       the simulated body is nearly still between events where real glucose keeps a ~40-min wander large enough to
       dominate CGM noise. No named component of the sim acts on that timescale (B4's intraday OU is off for lack of
       controlled-condition evidence, and its τ 240 min is the wrong scale). This is a missing physiological or
       closed-loop process, to be identified from evidence (candidates: ultradian hepatic glucose output, pump-delivery
       pulsing, Loop's own temp-basal cycling against a real body), not a fitted noise term.
     - **It is a daytime wander.** Quiet-period zero-crossing split by local hour (`acfctx5.py`): donors night (00–06)
       15, day (≥ 08) 40; sim CGM 15 / 25; sim true glucose 140 / 75. Real quiet nights are as still as the sim's
       (sensor noise sets both at 15); the ~40-min wander exists only while people are awake. That rules out a
       hepatic rhythm or the closed loop as its source (both run at night) and points at waking life: fragmented
       everyday movement (the sim has a constant waking background of 0.06 plus ~2 walks/day) and small sips and
       bites. Next: a fragmented light-activity component built from accelerometry bout structure, mean-preserving
       against the current background.

161. **Fragmented everyday movement adds lows, not the daytime wander.** `--enable act_frag` (0cdf8b9; off): the waking
     background as alternating sitting lnN(12 min, 1.0) and light bouts lnN(4 min, 0.8) at the intensity that keeps
     the person's mean [J sizes; Healy 2008 bout structure]; the activity-carbs probe uses the same process. c179
     (rc_own) against c177_base:
     - quiet daytime zero-crossing 25 → 25 (donors 40); whole-record 70 → 65; post-event 60;
     - lows 0.67 → 0.83/day (now passes, KS 0.06), t70 0.81 → 1.18 (donors 1.67), mean 157.8 → 155.6, TDD 38.6;
       day/night 1.83 → 1.81 (now fails, KS 0.03), night insulin CV 42.4; 26 vs 27 matched.
     - Minute-scale bouts, smoothed by the 7-min activity lag, move glucose too little and too fast to make a 40-min
       wave; they reach the low side because bouts above the 0.12 threshold build delayed sensitivity. Not adopted.
       The daytime wander needs a process that varies on a ~30–60 min scale while awake: candidates are the size of
       unlogged sips and bites over the day (the sim's grazing is 2/day of ~10 g), posture and meal-adjacent activity
       on that scale, or waking stress hormones.

162. **Smaller, more frequent sips do not make the wander either.** `--set graze_split=3` (54c29db; same daily grazing
     grams as 3× as many grazes of ⅓ the size): c180 against c177_base: quiet daytime zero-crossing 25 → 20 (donors
     40), mean 157.8 → 161.6, lows 0.67 → 0.58/day, hurst_long 0.369; 24 vs 27 matched. Not adopted.
     - With lessons 159 and 161, three waking-life candidates built on the sim's existing pieces (sugar-heavier snacks,
       fragmented movement, finer grazing) leave the daytime quiet wander at 20–25 min. Each is a fast, brief input;
       the donors' wander is slower (~40 min half-cycles) and present only while awake. What varies on that scale in
       waking T1D life and is not yet in the sim needs evidence before another arm: candidates are waking
       counter-regulatory tone (cortisol / catecholamine swings with activity and posture, cf. the dawn and stress
       terms), insulin absorption changes with skin temperature and posture over the day (A2 has site and exercise
       terms only), and meal-time-adjacent behavior on the 30–60 min scale.

163. **Upright absorption plus fragmented movement brings the lows to the donors': 32 of 51.** `--enable posture`
     (e0c9f6c; off): insulin clamps, the reference for the sim's PK, are done supine; sitting up cuts subcutaneous blood
     flow 29–47% and insulin absorption 19–44% (Hildebrandt 1985, 17 patients with diabetes). Awake = upright:
     absorption × (1 − p), p per person U(0.19, 0.44) on its own stream; asleep supine. c181 (rc_own) against
     c177_base:

     | | c177 | posture | posture + act_frag | donors |
     |---|---|---|---|---|
     | t70 (KS p) | 0.81 (0.002) | 1.13 (0.21) | 1.59 (0.91) | 1.67 |
     | lows / day (KS p) | 0.67 (0.001) | 0.83 (0.10) | 1.00 (0.77) | 1.08 |
     | t54 | fails | fails | passes | 0.215 |
     | mean (KS p) | 157.8 (0.009) | 162.5 (0.003) | 158.5 (0.04) | 151.4 |
     | CV | 36.8 | 38.4 | 39.2 | 34.8 |
     | day/night (KS p) | 1.83 (0.05) | 1.97 (0.15) | 1.93 (0.31) | 2.06 |
     | night insulin CV | 40.5 | 43.7 | 46.5 | 36.0 |
     | TDD | 39.6 | 40.1 | 38.9 | 38.8 |
     | matched | 27 | 25 | **32** | |

     - Gained with both: skew, t70, t54, lows/day, G7 sd/MAD, G7 measurement sigma; lost Libre 3 sd/MAD (6 people).
     - Slower daytime absorption leaves daytime insulin acting later (day/night up, toward the donors), and bouts of
       movement both speed absorption (exercise term) and build delayed sensitivity: together a daytime insulin action
       that swings with what the person is doing. The lows they add are where the donors' are.
     - The quiet daytime zero-crossing still reads 20 (donors 40), and CV (39.2) and night insulin CV (46.5) move away;
       still failing: mean, CV, TIR, t180, G7 step shape, hurst_long, acf_zero, volatility clustering, between-day,
       circadian amplitude, p_reach54, min below 70, zero fraction, p99, lag-1, night insulin CV.
     - **Adopted (Pete, 2026-10-18): `posture` and `act_frag` are defaults** (`--disable posture,act_frag`).

164. **The sim does not tighten control with hands-on behavior; donors do.** c182_base (32 of 51), by donor carb-entry
     tercile (low / mid / high entries per day 0.8 / 2.0 / 3.3), medians:
     - glucose CV: donors 36.7 / 33.8 / 33.0, sim 39.1 / 39.1 / 39.8; mean donors 164 / 150 / 144, sim 161 / 153 / 162;
       t70 donors 1.17 / 0.93 / 1.33, sim 1.83 / 1.68 / 1.33. Twin Δ CV by strategy: automatic +2.8, temp +6.5.
     - The behavior rates track each donor's own: correction attempts per day sim 0.67 / 1.17 / 1.50 vs donors' true
       corrections 0.50 / 0.86 / 1.45; top-ups 0.08 / 0.42 / 0.67 vs 0.10 / 0.25 / 0.64; free boluses 0.08 / 0.25 / 0.25.
     - So the hands-on donors' tighter glucose does not come from how often they act. What the frequency match leaves
       out is how well each act lands: entry accuracy per person (count error is a population distribution,
       Brazeau), bolus timing against eating per person (lead from the labeler), and how tuned their settings are to
       their body (the body is drawn halfway between settings and the TDD yardstick for every person alike, ISF_W 0.5).
       The last is the most direct suspect: a hands-on donor who edits settings often (eda edit rates are in the
       templates) plausibly runs settings closer to their body. Next: twin CV gap against the donor's settings-edit
       rate.
     - **Not settings tuning.** Twin Δ CV against the donor's settings-edit rate (basal + ISF + CR edits/day, median 0.09):
       Spearman 0.07; by tercile few / some / many +4.3 / +3.4 / +3.9; donors' own CV does not follow edits either
       (−0.03). The CV excess (~+4) is universal across people, not a hands-on or tuning effect: a population-wide
       component adds variance (or a missing one removes it). The posture pair raised CV 36.8 → 39.2 while fixing
       the lows; the next check is which part of the posture pair's added variance falls outside the lows.

165. **The high tail was κ, read from the wrong study.** The new base's CV excess is all in the high tail: per-person
     median percentiles p75 / p90 / p95 / p98, donors 181 / 226 / 255 / 289, c182_base 194 / 241 / 268 / 313 (low end
     matches: p2 72 vs 71, p5 83 vs 80). κ (A5: insulin-mediated uptake ∝ Gb + κ(G − Gb) above Gb) was set at 0.15
     on Del Prato 1997, but that clamp held insulin at basal and measures the glucose dependence of disposal without
     added insulin (the SG term). Best 1981 sizes κ itself: at fixed insulin, doubling glucose raised disposal ×1.24 /
     ×1.68 / ×1.78 at low / mid / high insulin (κ ≈ 0.24 / 0.68 / 0.78). `--set kappa_mult` against c182_base (rc_own):

     | | κ ×1 (0.15) | ×2 | ×3 | ×4.5 (≈ 0.68, Best mid) | donors |
     |---|---|---|---|---|---|
     | p75 / p90 / p98 | 194 / 241 / 313 | 187 / 232 / 301 | 185 / 233 / 293 | **179 / 224 / 284** | 181 / 226 / 289 |
     | mean (KS p) | 158.5 (0.04) | 154.1 (0.06) | 153.7 (0.12) | 149.4 (0.09) | 151.4 |
     | TIR (KS p) | 66.7 (0.003) | 69.5 (0.09) | 70.4 (0.09) | 73.2 (0.74) | 71.7 |
     | CV | 39.2 | 37.9 | 38.0 | 36.5 | 34.8 |
     | t70 / lows per day | 1.59 / 1.00 | 1.68 / 1.00 | 1.67 / 1.04 | 1.46 / 0.92 | 1.67 / 1.08 |
     | t54 (KS p) | 0.12 (0.11) | 0.12 (0.001) | 0.09 (0.001) | 0.12 (0.007) | 0.215 |
     | hurst_long | 0.360 | 0.336 | 0.319 | 0.297 | 0.247 |
     | night insulin CV | 46.5 | 44.6 | 43.1 | 41.6 | 36.0 |
     | matched | 32 | 33 | 33 | 33 | |

     - At Best's mid-insulin κ the whole glucose distribution sits on the donors' (every percentile within 6), the
       level and TIR pass, the lows stay, and long-range Hurst and night insulin CV move most of the way. Highs now
       come down as fast as real ones because insulin acts harder the higher glucose is, which the clamp evidence
       measured and the sim had at a fifth of its size.
     - Still failing at ×4.5: CV 36.5 (KS 0.012), t54 0.12 (donors 0.215: the lows are as frequent but shallower),
       acf_zero 65, the quiet daytime wander (25 vs 40). evidence/15 corrected. Default decision: Pete.
     - **Adopted (Pete, 2026-10-18): κ median 0.675** (= 0.15 × 4.5, the same draws), lnN σ 0.4 kept; registry A5.

166. **Counter-regulation fitted to the donors' low depths: half the judged gain, 36 of 51.** On c185_base the lows were
     as frequent as the donors' but shallower and longer (`nadir.py`, G7 episodes < 70 for ≥ 15 min): nadir p10 / p25 /
     p50 donors 41 / 50 / 58, sim 47 / 54 / 60; share reaching < 54 0.35 vs 0.24; duration p90 75 vs 91 min. A9's
     CRmax lnN(1.0 mg/kg/min, 0.5) is a judgement, and evidence/01 §4.4 prescribes fitting it to exactly this nadir
     distribution (T1D loses the glucagon response early; adrenaline remains). `--set cr_mult` (4dc802d), c186
     (rc_own) against c185_base:

     | | ×1 | ×0.5 | ×0.25 | donors |
     |---|---|---|---|---|
     | nadir p10 / p25 / p50 | 47 / 54 / 60 | 46 / 52 / 59 | 43 / 51 / 59 | 41 / 50 / 58 |
     | share reaching < 54 | 0.24 | 0.30 | 0.32 | 0.35 |
     | t54 (KS p) | 0.117 (0.007) | 0.148 (0.26) | 0.177 (0.74) | 0.215 |
     | lows / day | 0.92 | 1.00 | 1.08 | 1.08 |
     | TIR / mean | 73.2 / 149.4 | 71.6 / 149.6 | 71.8 / 149.5 | 71.7 / 151.4 |
     | CV | 36.5 | 36.8 | 37.3 | 34.8 |
     | matched | 33 | **36** | 34 | |

     - ×0.5 passes t54, p_reach54, lows/day, TIR and mean together; ×0.25 fits the depth best but adds CV. The donors'
       deepest nadirs include compression lows and the 40-mg/dL floor (common-mode, AGENTS), so the depth target is
       itself a little deep; ×0.5 is the fit that does not chase it.
     - Durations stay long at p90 (95 vs 75 min): recovery from a low is still slower than real (rescue timing or size).
     - **Adopted (Pete, 2026-10-18): CRmax median 0.5** (0.5 × the same draws); registry A9.

167. **Half the sim's lows are at night; the donors' are 22%.** Low episodes (< 70 for ≥ 15 min, G7) split by local
     night (00–06) vs day (`lowdur.py`): donors 22% at night (2,613 of 11,835; duration p90 night 80, day 60 min); sim
     c187_base 53% (465 of 884; p90 93 / 50). It was already 45% before posture (c177); posture moves lows into the
     night (c181_po 56%), fragmented movement adds them by day (c179 57% day).
     - **Not the timing of the day's insulin:** hours from the last manual bolus to a night low, median 6.4 sim vs 6.8
       donors; from the last entry 7.0 vs 7.8 (`nightlow.py`).
     - **Not the basal share:** 0.47 / 0.52 (c188) leave the night share at 51% / 50% and trade lows against CV,
       Hurst and night insulin CV (CV 35.0 / 34.3 and night insulin CV 39.6 / 36.0 pass; lows 0.88 / 0.67 per day;
       34 / 31 matched).
     - **Not the movement bouts' delayed sensitivity:** act_frag's 4-min bouts ran at intensity 0.28 to keep the
       waking mean, above the 0.12 threshold, so everyday movement built the post-exercise state (night ex_boost 0.15
       vs 0.03 before). Light-intensity bouts (`--set frag_on=9.6`: bouts at 0.15, ~40% of waking time, the
       accelerometry share of light activity) bring it to 0.10, but the night share stays 52% (c189; 35 matched).
     - **Not targets:** 7% of donors set a night target ≥ 5 higher (median night − day 0).
     Next: the body's basal-need profile, which follows the donor's schedule shape only halfway (B1b, prof_w 0.5 [J])
     while Loop runs the full schedule.
     - **Not the basal-need profile either:** the body following the donor's full schedule shape (`--set prof_w=1.0`,
       c190) leaves the night share at 54%; 35 matched.
     - In rates, the sim has 0.44 night lows per person-night against the donors' 0.16 (2.8×) and 0.40 daytime lows
       per day against 0.56: its lows are misplaced, not too many. Five candidates on the insulin and settings side are
       now ruled out. Open: what keeps real nights out of lows. Candidates not yet measured are the overnight
       defense (urgent-low-soon alarms waking the person, and bedtime snacks taken against a predicted fall; the
       sim's p_wake_alarm N(0.45, 0.2) is a judgement), and how the donors' own CGM data cover nights (phones out of
       range overnight remove night readings and with them night lows).
     - **Not missing night data:** donors' G7 coverage (share of 5-min slots with a reading, median person, 60
       donors) is 0.971 at night and 0.948 by day. Real nights are measured as fully as days, so the donors' low night
       share is real. Left: the overnight defense (alarms, bedtime snacks) and whatever keeps real overnight glucose
       up that the sim's night lacks.
     - **Not the circadian profile** (B1 off, c191): night share 54%. **Not sensor artefacts:** 28% of the sim's night
       CGM lows and 36% of its day ones have no true low behind them (sensor error in the low range, both periods);
       on true glucose the lows are still 56% nocturnal.

168. **The circadian sensitivity profile carries the long-range persistence excess.** `--disable circadian` (c191,
     rc_own) against c187_base: hurst_long 0.287 → 0.247 (donors 0.247; KS 0.42), CV 36.8 → 36.3 (passes, KS 0.051),
     mean 148.4, TIR 72.3, lows unchanged (1.00/day), 36 matched. B1 is a fixed daily pattern of three Visentin
     segments at the full measured swing (lesson 38 set the full swing when the old base's 24-h amplitude matched);
     on the new base the sim's circadian amplitude has run ~0.18 against the donors' 0.131, and the fixed daily
     structure reads as long memory. Evidenced and stays; its swing is the question (next: `circ_swing 0.5`).
     - **Half the swing** (`--set circ_swing=0.5`, c192): hurst_long 0.259 (passes, KS 0.14), CV 36.5, day/night 2.01;
       between-day fraction now fails (0.105, KS 0.04) and P(reach 54) narrowly (KS 0.045); 36 matched, unchanged.
       Circadian amplitude 0.181 → 0.165, and with B1 off it is 0.174: the sim's 24-h amplitude (donors 0.131) is
       not B1's swing but the day's other structure (meal clock, activity, dawn). Default unchanged; the amplitude
       gap is open.

169. **The night lows are mostly posture's bedtime step; half the measured contrast gives 37 of 51.** Median glucose by
     3-h local block relative to each side's mean (donors 151, c187 150): 00–03 donors +1, sim −16; 03–06 −17 / −30;
     09–12 −5 / +12. Real glucose holds through the first half of the night; the sim's falls from bedtime, which is
     where its extra night lows are. Posture (A4b) switches absorption from upright to supine at bedtime.
     - `--disable posture` (c193): night share of lows 53% → 40%, 00–03 134 → 146 (donors 152), CV 34.4 (passes),
       hurst_long 0.259 (passes), lows 0.83/day; 35 matched.
     - `--set posture_mult=0.5` (c194, 9f2fd79): night share 46%, 00–03 140.5, CV 35.6 (passes), hurst_long 0.267
       (passes), TIR 72.6, lows 0.92/day; t54 0.106 and P(reach 54) 0.148 now fail; **37 matched**.
     - Posture went in at 32 (lesson 163) before κ and counter-regulation were refitted (lessons 165–166); those now
       carry the lows it supplied, and its full step at bedtime overstates the night/day contrast. Hildebrandt
       compared sitting with flat supine; real evenings include reclining and real sleep is not constant flat supine.
     - **Adopted as default: posture at half the measured contrast** (0.5 × the same draws; `--set posture_mult=1.0`
       restores the full step). Self-approved under Pete's standing permission for additive-model updates
       (2026-10-18). Remaining night excess 46% vs 22%.

170. **Real dinners rise a second time; the sim's do not, and neither meal composition nor evening grazing alone
     fixes the night.** Entry-anchored CGM change after isolated dinners (≥ 20 g, local 17–21 h, no other entry −3 h /
     +8 h; `dinner_traj.py`), median mg/dL at 1–8 h:
     - donors (3,301): +15 / +13 / **+26** / +19 / +9 / +1 / −6 / −11 — a second rise at 3–4 h;
     - c195_base (221): +14 / +12 / +10 / +7 / +2 / −4 / −15 / −22.
     Unannounced labeled intake 1.5–5 h after announced meals (g-eq per 10 g entered; share with any) by slot
     breakfast / lunch / dinner: donors 3.08 (0.31) / 2.90 (0.33) / 4.34 (0.50); sim 3.32 (0.39) / 3.63 (0.42) /
     3.82 (0.49) (`followon_slot.py`). Real unlogged eating concentrates after dinner; the sim's is spread evenly.
     - `--enable slot_comp` (0331771; fat and protein per carb gram ×0.6 / 1.0 / 1.35 by slot [J sizes]): dinner hump
       appears at 4 h (+6 → +10), night share of lows 46% → 43%, circadian amplitude 0.169 → 0.159; day/night now fails;
       36 vs 37 matched.
     - `--enable graze_eve` (112c642; graze timing ×2 at 19–23 h [J]): dinner +20 / +19 / +16 / +19 at 1–4 h, night
       share 49%; hurst_long 0.295 and CV 36.1 fail again; 32 matched. Both together: 34.
     - Not adopted. The dinner shape moves toward the donors' in both arms, yet the night share of lows does not: what
       keeps real nights out of lows is not the post-dinner glucose level alone. The open question stays lesson 167's.

171. **Real Loops deliver more insulin overnight than the sim's, and their nights still stay out of lows.** Insulin
     delivered ÷ scheduled basal, median person over nights (`night_ratio.py`; sim received doses vs settings; donors
     doses.json vs the therapy basal timeline, local time): night 00–06 donors 1.32 (80 people), c195_base 1.24; afternoon
     12–18 (boluses included) 2.67 vs 2.32.
     - The sim's Loop is not over-dosing its nights; the simulated body reaches lows on less insulin than real bodies
       take without them. So real nights carry something that keeps glucose arriving or insulin acting less than the
       sim's night does, and it is not the post-dinner level (lesson 170), the basal share or profile (167), the
       circadian profile (168) or settings and targets (167).
     - The one lever that moved the night share was posture's bedtime step (off: 40%; half: 46%; full: 53%), i.e. how
       fast insulin acts once the person lies down. Candidates now: overnight insulin resistance that the sim lacks
       (sleep-phase GH surges are mean-zero in the sim, B8; real early-night GH peaks raise EGP and lower SI for hours),
       and the timing of the supine switch relative to the evening's insulin.
     - **Evidence check on overnight resistance (not built).** In T1D, insulin requirements fall from ~00:00–03:00 and
       rise only toward dawn, 05:00–08:00 (dawn-phenomenon reviews, Diabetes Care 2013 "Thirty years of research");
       nocturnal GH influences overnight requirements, not the early-night period's direction (Edge 1990; Campbell /
       Diabetes 1985; GH-antagonist study, Diabetologia 2003: overnight requirements fell with GH blockade, clamp SI
       unchanged). So real bodies are, if anything, more sensitive in the early night, the opposite of a missing
       resistance. The donors' held early night (lesson 169) then points away from body-side physiology toward
       behaviour or the controller's interplay with a real body; it stays open.
     - **Not night-time treatment behaviour.** Labeled pulses at local 00–06 per person-night (`night_rescue.py`):
       flagged rescues donors 0.075, sim (c172_rc) 0.081; unannounced pulses starting below 100 mg/dL (pre-emptive
       eating, or dawn rises) 0.222 vs 0.160, onset BG 88 on both sides. A 0.06/night shortfall in pre-emptive pulses is
       far smaller than the 0.28/night excess of night lows (0.44 vs 0.16). With insulin delivery (1.24 vs 1.32 ×
       schedule) and treatment matched, the sim's nights fall into lows that real nights do not, on less insulin: the
       difference is in the overnight glucose balance itself, and the posture step (the only lever found) acts there.

172. **A gradual evening transition does not move the night either.** `--enable posture_ramp` (7efbc53; off): the
     upright absorption reduction fades linearly over the last 3 h before bedtime [J shape]. c198 (rc_own) against
     c195_base: at half posture night share of lows 46% → 45%, 00–03 140.5 → 142.4, 36 matched (37); at full posture
     with the ramp 46%, 00–03 136.5, 37 matched. Not adopted.
     - Across lessons 167–172, twelve candidates leave the sim's night share of lows between 40% and 54% against the
       donors' 22%; only removing posture reaches 40%. Insulin delivery, treatment behavior, CGM coverage, dinner
       shape, composition and grazing timing all match or were tested. The remaining measurement is the overnight
       glucose balance with no controller in the way: true-glucose drift across quiet nights in the sim against the
       donors' CGM drift on quiet nights, per unit of insulin delivered.

173. **On quiet nights the sim's body falls further on less insulin; sleep-lowered glucose use puts it on the donors'
     balance, and exposes a shortage of daytime lows.** Quiet nights (no entry or manual bolus 21:00–06:00 local;
     `quiet_nights.py`), by glucose at 00:00 — drift 00→06 / insulin delivered ÷ scheduled / share of nights with a low:

     | start | donors (3,879 nights) | c195_base (489) | sleep_util (c199, 494) |
     |---|---|---|---|
     | < 120 | +8.3 / 0.98 / 0.34 | +9.3 / 0.91 / 0.56 | +12.0 / 0.95 / 0.44 |
     | 120–160 | −24.3 / 1.17 / 0.15 | −35.3 / 1.04 / 0.25 | **−28.0 / 1.15 / 0.15** |
     | ≥ 160 | −72.0 / 1.55 / 0.10 | −89.0 / 1.32 / 0.19 | −89.0 / 1.38 / 0.16 |

     - Without sleep_util, in every band the simulated body falls further while Loop gives it less insulin: its
       overnight glucose balance tilts downward. Real bodies hold.
     - **`--enable sleep_util`** (a2efdd2; off): sleep lowers glucose utilisation (Van Cauter 1991, 1997: at constant
       glucose infusion glucose rises 20–30% during sleep, about two-thirds from sleep itself through lower brain and
       peripheral use). While asleep, net glucose rises by δ × ~1 mg/kg/min of insulin-independent (mostly brain)
       uptake, δ per person U(0.05, 0.12) [J within those studies], ramping in over 30 min. It reproduces the donors'
       quiet-night balance in the 120–160 band (drift, insulin and nights with a low all within 4) and moves the < 120
       band most of the way.
     - Whole cohort: night share of lows 46% → 42%, night insulin CV 40.9 → 38.9, CV 34.6 and Hurst 0.264 pass; but
       lows 0.83/day and t70 1.14 now fail, day/night 1.79 and zero-delivery fraction fail; 32 vs 37 matched. The sim
       loses night lows without the daytime lows it was already short of (by day sim 0.40 vs donors 0.56 per day).
     - Not adopted alone: the night is now right on its own evidence and the count shows the next missing piece is a
       daytime source of lows. Next: what produces real daytime lows that the sim lacks (by context: post-meal,
       post-correction, activity, afternoon).
     - **Where the missing lows are, with sleep_util on** (`low_ctx2.py`, per person-day, by time since the last entry
       < 2 h / 2–4 h / 4 h +): sim 0.127 / 0.175 / 0.581, donors 0.270 / 0.166 / 0.623. Every context matches except
       the first two hours after a meal, the same deficit as lessons 145–150 (15–30 g: 0.032 vs 0.093; 30–60 g: 0.030 vs
       0.098 per day; 60 g +: 0.042 vs 0.026). With the night balanced by sleep_util, the one remaining source of the
       low-count gap is the unexplained first-hour variability of real meals; closing it would be the daytime half that
       sleep_util needs to be adopted.

174. **The first-hour meal spread is not the sensor.** The donors' extra within-person spread is size-independent
     (lesson 150), as a sensor error would be, so: sim within-person IQR of the absolute 0→60 min change after isolated
     entries (`spread_true.py`, c195_base, 73 people) CGM 51.8 vs true glucose 54.6 — the sim's sensor adds nothing;
     donors ~63–69 on CGM. Closing it with sensor error would need an extra per-reading error sd of ~20 mg/dL (~11% at
     180) during rises. The G7 accuracy study (Garg 2022, 316 adults): MARD at rapid rises (> 2 mg/dL/min) 9.7% (arm)
     / 10.3% (abdomen) against 8.2% / 9.1% overall — about 1.15× the overall error. Rate-dependent CGM error is far too
     small; the extra first-hour spread of real meals is in true glucose. Still open, with the meal-side terms
     (lessons 147–150), late entries (149) and sensor (here) ruled out.

175. **Treatment carbs entered in the app: 40 of 51.** Isolated entries ≥ 20 g split by a manual bolus within ±30 min
     (`entry_bolus_split.py`): bolused donors 92.4% (BG at entry 138, 0→60 change +20, P(low < 2 h) 0.10), sim 97.9%
     (145, +12, 0.10); unbolused donors 7.6% (109, +64), sim 2.1% (144, +15). Donors log carb treatments (pre-emptive
     and rescue carbs) about 3.6× as often as the sim's people, who entered rescues at p 0.05 [J, flagged "very
     under-represented"] and proactive snacks never.
     - `--set p_log_pro=0.25,p_log_rescue=0.25` (3ab1bb4; c200, rc_own) against c195_base: t54 0.106 → 0.147 (passes),
       P(reach 54) 0.148 → 0.167 (passes), hurst_long 0.262, CV 35.1, TIR 72.0, carb entries 2.67 → 3.08/day (donors
       2.97); **40 vs 37 matched**. The ≥ 20 g unbolused share does not move (most treatments are under 20 g); the
       effect is on Loop: a logged treatment shows Loop the carbs, so it doesn't suspend and hold glucose up after
       the treatment.
     - **Adopted as default: p_log_pro and p_log_rescue 0.25** [J share; direction from the donors' treatment logging],
       self-approved under Pete's standing permission. A per-donor logging rate from the templates is the evidence step
       still to take.
     - **sleep_util re-tested on this base** (c202 against c201_base): night insulin CV 40.7 → 38.4 (passes), night-low
       duration p90 96 → 80 min (donors 80), quiet-night 120–160 band −31 / 1.10 / 0.16 (donors −24 / 1.17 / 0.15); but
       lows 0.92 → 0.75/day, t70, t54, day/night and zero-delivery fraction fail: 35 vs 40. Still the same trade
       (lesson 173): the night is right with it, and the daytime lows it removes have no counterpart until the
       first-hour spread of real meals is found. Stays off.

176. **Faster emptying on the matched-lows base: a better first hour, a lost plateau, no net gain.** `--set meal_k=1.3`
     (c203 on 67ee10b, rc_own) against c201_base: bolused-meal 0→60 change +12 → +16 (donors +20); temp ΔCGM per 10 g at
     60 / 90 / 180 min +5.0 / +7.1 / +0.6 (donors +6.4 / +5.9 / +5.5); t54 0.147 → 0.176; within-person first-hour IQR
     48 (donors 71); 39 vs 40 matched. As on every earlier base (lessons 130, 149, 166), faster appearance moves the
     first hour toward the donors' and empties the 2–4 h plateau the real meals keep; the within-person spread does not
     respond to meal speed. Not adopted. The two observations together still ask for real meals that arrive both faster
     early and longer late, with their extra variability from outside the meal itself.

177. **A wide meal-specific emptying ceiling moves the lows the donors' way and loses the meals.** `--enable
     ceiling_speed --set gi_cv=0.8` (c204, rc_own) against c201_base: bolused first-hour within-person IQR 52 → 59
     (donors 71); night share of lows 45% → 40%, day low episodes 431 → 480; hurst_long 0.240 (donors 0.247), t54
     0.178; but temp meals fall below their start by 3–4 h (−1.2 per 10 g at 4 h; donors +4.0), CV 36.3 and day/night
     1.75 fail: 33 vs 40 matched. Not adopted.
     - Read with lessons 147–150 and 174–176: every mechanism that adds first-hour spread through the meal itself
       (speed, ceiling, fast share, drink, count, sensor) also empties the 2–4 h plateau, because it acts by moving the
       meal's own glucose earlier. The donors keep both, so their first-hour variability is not the meal's: it is
       glucose that moves in the hour after eating for reasons that leave the meal's late arrival intact. Within the
       data available (no steps, heart rate or stress signals in BDDP), the sim cannot identify that source; it is
       recorded as the main open gap, with the activity and stress-hormone candidates for literature or a dataset that
       carries them.

178. **Meal timing variability matches; the first-hour gap is in how far meals rise.** CGM time-to-peak within 3 h of
     isolated entries ≥ 20 g with a rise ≥ 15 (`ttp.py`): donors (118 people, 10,820 meals) median 101 min, within-
     person SD 51.2, between-person SD of person medians 25.1; c201_base (72, 783) 99 min, 47.4, 34.1. Bell 2021
     (Nutrients; children with T1D, identical controlled breakfast): within-person time-to-peak SD 38.9 min against
     18.5 between persons, the same ordering. The sim reproduces when meals peak and how much that varies within a
     person; the remaining first-hour gap (lessons 146–150, 174–177) is in amplitude: how far a real meal rises,
     size-independently, while its timing and its late plateau stay as the sim has them. The sim's people also differ
     more from one another in timing than the donors do (between-person SD 34 vs 25).

179. **Per-donor treatment logging undercounts with this proxy.** Donor logged treatments per day = carb entries with no
     manual bolus within ±30 min and CGM < 130 at the entry (`treat_log_rate.py`; column `treat_log_day` in
     templates_pilot_logs.csv): median 0.073, p25 / p75 0.008 / 0.37, p90 0.86; 44% under 0.05/day. Mapped to a
     per-person probability as rate ÷ 1.4 (the sim's median treatments per day), `--enable log_own` (62e789c; c205)
     against c201_base: t54 0.147 → 0.093 and P(reach 54) 0.167 → 0.146 fail again, carb entries 3.08 → 2.75/day (donors
     2.97); 36 vs 40 matched. The proxy misses treatments entered above 130 or alongside a bolus, so its level is low
     even if its spread is real. The 0.25 constant stays; a per-person version needs a better treatment-entry
     detector (for example the ice labeler's rescue flag joined to entries).
     - **A direct per-donor measure scores the same.** The labeler's rescue flag marks only unannounced pulses, so the
       usable measure is the share of a donor's labeled pulses starting below 75 mg/dL that were entered: median
       0.28, mean 0.32, p25 / p75 0.09 / 0.50, p90 0.67 (161 donors with ≥ 5; column `low_entered_share`). As each
       person's logging probability (`log_own`, 3874d0c; c206): t54 0.118 and P(reach 54) 0.162 fail narrowly, carb
       entries 3.21/day; 36 vs 40. The donors' spread of logging, at a mean above the constant's, makes the lows
       shallower overall: frequent loggers lose more deep lows than rare loggers gain. The 0.25 constant stays the
       default and `log_own` an experiment switch.

180. **Real lunches rise like breakfasts; the sim's barely rise. Circadian gastric emptying fixes the night level, not
     lunch.** Isolated entries ≥ 20 g (no other entry −3 h / +4 h), ΔCGM every 30 min to 4 h (`slot_traj.py`):

     | slot | donors | c201_base |
     |---|---|---|
     | breakfast 06–10 | +18 / 41 / 42 / 35 / 29 / 27 / 22 / 16 | +12 / 26 / 39 / 37 / 36 / 30 / 28 / 26 |
     | lunch 11–15 | +18 / 34 / 36 / 35 / 33 / 31 / 26 / 18 | +1 / 7 / 10 / 2 / −3 / −8 / −4 / −2 |
     | dinner 17–21 | +16 / 16 / 11 / 15 / 22 / 27 / 23 / 20 | +8 / 12 / 12 / 9 / 4 / 10 / 9 / 3 |

     - Not the circadian SI profile (B1 off: lunch +4 / 12 / 16, c191) and not post-meal activity (a walk within 2 h of
       28% / 33% / 31% of breakfasts / lunches / dinners in the sim).
     - **`--enable ge_circ`** (f8e6737; off): gastric emptying ×1.25 at 06–11 h, ×1.0 at midday, ×0.8 at 17–23 h, on the
       energy ceiling and the parcels' rates (Goo 1987: the same solid meal's emptying half-time ~54% longer in the
       evening) [J shape]. c207 against c201_base: 00–03 140.6 → 152.5 (donors 152), night share of lows 45% → 39%,
       circadian amplitude 0.169 → 0.139 (donors 0.131), breakfast +14 / 41 / 58 at 0.5–1.5 h with a shorter tail; but
       lunch still +3 / 11 / 15, dinner sags (−4 to −7 at 2–3 h), lows 0.75/day, t54, P(reach 54) and day/night fail:
       31 vs 40. Not adopted.
     - The lunch gap is the sharpest single meal-level divergence: real lunches rise ~35, the sim's ~10. With breakfast
       and dinner in the right range and activity and SI ruled out, what is particular about simulated lunches (their
       entries, boluses and pre-lunch state) is the next measurement. As with sleep_util, holding the night up costs
       the low count; the night and the daytime lows have to move together.

181. **Simulated lunches start 26 mg/dL higher; the late-morning bulge is breakfast's long tail.** Isolated entries
     ≥ 20 g by slot (`slot_state.py`), medians — BG at entry / 30-min pre-trend / manual bolus U per 10 g within ±30 min
     / bolus minus entry (min):
     - donors: breakfast 122 / +2.6 / 1.13 / 0.1; lunch **128** / −1.8 / 1.08 / 0.1; dinner 138 / −1.0 / 1.01 / 0.1;
     - c201_base: breakfast 122 / +2.0 / 0.98 / 2; lunch **154** / −2.9 / 1.03 / 2; dinner 144 / −2.0 / 0.95 / 2.
     Boluses, timing and trends match; lunches begin high, so Loop's correction and κ's mass action blunt their rise
     (lesson 180). Breakfast and dinner start at the donors' levels. The 3-h profile's 09–12 block is 158–162 against
     the donors' 146 in every arm, and the sim's breakfasts keep +26–28 at 3.5–4 h against the donors' +16–22. With the
     circadian SI profile off (c191) lunch starts at 145 and 09–12 reads 158: B1 explains a third. Next: what lengthens
     the simulated breakfast tail (morning fat and protein, the dawn part of the basal-need profile, and the Visentin
     breakfast level each acting after 2 h).

182. **Real people skip breakfast twice as often as the sim's; matching it shortens the breakfast tail and lowers the
     lunch start, at a cost elsewhere.** Pete asked whether breakfast skipping is modelled: as a flat 10% of days for
     everyone (`skip_breakfast`). Donors' share of days with no labeled pulse ≥ 10 g-eq at 05:00–10:30 local: median 0.18,
     p25 / p75 0.12 / 0.27, p10 / p90 0.07 / 0.36 (168 donors); the same measure on the sim reads 0.08 (its true 0.10), so
     the measure under-reads slightly on both sides.
     - **`--enable skip_own`** (cedeb80; off; per-donor share as the person's `skip_breakfast`, column `skip_bfast` in
       templates_pilot_logs.csv; the day's other meals carry the skipped grams): c209 against c201_base: lunch starts 154 →
       143 (donors 128) and rises +10 → +15 at 1.5 h (donors +36); breakfast's 3.5–4 h tail +26–28 → +18–19 (donors
       +16–22); but 09–12 stays 154.7 (donors 146), CV 36.5, Hurst and t54 fail: 32 vs 40 matched.
     - Breakfast-tail arms on the same base (c208): body basal profile at the full schedule shape (`prof_w` 1.0) lunch
       starts 148, 34 matched; slot composition 147.5, 36 matched; breakfast tails barely move in either.
     - None adopted. The lunch gap now reads as two parts: a higher start (breakfast eaten more often and lasting longer
       in the sim) and a smaller rise from that start. Skipping is real, evidenced behaviour; the cost comes from the
       skipped grams moving into larger lunches and dinners, which a real skipper may not do (part of the day's intake
       simply not eaten). Next: skip_own with the skipped breakfast's grams dropped rather than redistributed.

183. **Dropping the skipped breakfast instead of redistributing it repairs CV but not the count.** `--enable skip_drop`
     (with skip_own; 33093c7; off): on a skipped day the planned grams scale by (full share − breakfast share) / full
     share, applied after the day's intake regulation. The first version scaled the share before regulation, which
     renormalises to the day total, so c210 came out identical to c209. Planned intake 181.0 → 175.7 g/day. c210 against
     c201_base: CV 36.5 → 35.6 (KS p 0.02 → 0.13, matched again), Hurst p 0.15, t54 p 0.08; lunch starts 148 (skip_own
     alone 143, base 154, donors 128) and rises +16 at 1.5 h (donors +36); 09–12 153.1 (donors 146); night share of lows
     unchanged at 0.45. 36 vs 40 matched: Box-Cox λ (p 0.22 → 0.02), the G7 split of one shape statistic, between-day
     fraction and zero fraction drop out, the last three from p 0.053–0.061 in the base. Not adopted. Skipping on its own
     moves the lunch start by under half the gap, so most of the late-morning excess is the second part from lesson 182:
     the breakfast that is eaten lasts longer in the sim than in the donors.

184. **The day's unentered rises match the donors'; nights lack about 0.2 body-driven rises for nearly everyone, and the
     gut and the sensor are not the cause.** Measured on c201_base with Dexcom G7 people on both sides (scripts in
     runs/2026-10-18-additive-workouts/: hour1*, slot_decomp, gut_check, slot_clean, unent_rise, night_rise_cause,
     vd_depth, night_pre_ins).
     - **Hourly profile** (median over people of each hour's mean CGM; donor series from `quiet._donor_series` are
       already local, so they take no further offset): the sim runs 10–13 mg/dL below the donors from 00 to 06 h (117
       vs 130 at 06 h) and 8–13 above them from 09 to 12 h. From 06 to 10 h it climbs 41 against the donors' 15,
       entered morning carbs being equal (06–09 h 11.3 vs 10.2 g/day).
     - **The gut matches tracer data**: the default parcels for a 37 g breakfast with its fat and protein appear 25 /
       50 / 75% at 53 / 91 / 146 min, 87% by 3.5 h; 121 g carbohydrate 58 / 101 / 158 (Elleri 2013 high-GL 56 / 100 /
       153); ~75 g glucose 91% by 3.5 h (Ferrannini 1985: 73%, so if anything the model is fast). The 3–4 h appearance
       after an isolated breakfast (~1.9 mg/kg/min) is mostly other eating: in 46% of isolated breakfasts and 59% of
       lunches, ≥ 15 g of unentered snacks, grazes and pre-emptive carbs follow within 4 h.
     - **Unentered rises** (CGM +30 within 60 min from ≥ 80 mg/dL, one per 3 h, no entry from −60 to +30 min; same code
       both sides): per day donors 3.46 vs sim 3.08, unentered share 0.78 vs 0.77, median peak 70 vs 74 mg/dL; by
       3-h block 06–24 h within 0.07/day. **00–06 h: donors 0.66 per night, sim 0.48**. Night rises look alike (start
       113 vs 110, after a low 10% vs 12%, 60-min gain 34 vs 35, peak 49 vs 50, time to peak 80 vs 85 min) and follow
       a Loop insulin cut (< 50% of the person's own 90-min night delivery) in 31% vs 25% of cases. Per person the
       night rate is shifted across the whole distribution (p10 / p50 / p90: 0.33 / 0.68 / 0.98 vs 0.17 / 0.42 /
       0.86), not concentrated in a minority (the 9.7% of 714 T1D/T2D adults eating > 25% of calories after supper, Morse 2006 Diabetes Care 29:1800,
       would have shown as a tail).
     - **In the sim, 83% of night unentered rises have no carb event behind them and the body moves +6 mg/dL in the
       hour**: they are sensor recoveries. Body-driven night rises are ~0.08 per night.
     - **Sensor dips are right at night**: `vdips` per hour the detector can see, drop ≥ 20: 0.97 vs donors 1.11 per 6 h,
       depths identical (median 24, p90 36–37); the sim's true glucose has none. Per all hours (as `vdips._summ`
       reports) the sim read 2× the donors, an artefact of the donors' nights being blocked more by detected meals.
     - So the night gap is in the body: real nights carry about 0.2 more upward excursions of ~50 mg/dL each, for nearly
       everyone, after Loop cuts and without them. This is the same balance as LESSONS 173 (quiet nights fall further on
       less insulin; sleep_util) seen as events rather than drift. Candidates with a mechanism for everyone: nocturnal
       growth-hormone surges at sleep onset and the cortisol rise toward waking, as pulses rather than sleep_util's
       smooth level; sleep arousals. Each needs its own evidence before a switch.

185. **The missing daytime lows are bolused meals that go low about an hour later, at twice the sim's rate.** Low onsets
     (`low_ctx2b.py`, G7, c201_base vs donors): 0.943 vs 1.059 per day, and the whole shortfall sits within 2 h of an
     entry (0.138 vs 0.270; 0–30 / 30–60 / 60–120 min: 0.033 / 0.021 / 0.083 vs 0.058 / 0.071 / 0.141). After entries ≥ 15
     g, the early lows are bolused meals in both: sim 0.113 per day vs donors 0.210, BG at the entry p25 / p50 / p75 84 /
     122 / 164 vs 95 / 119 / 154, a median 76 vs 67 min after it; unbolused entries add 0.002 vs 0.029 (treatments). So
     real bolused meals outrun their carbohydrate about twice as often, from ordinary starting glucose. With lesson
     178 (real meals also rise further), both tails of the real meal response are wider than the sim's: the per-meal
     match of carbohydrate arriving to insulin given varies more in life. Not the per-dose absorption spread, whose
     values are evidenced (A4 15% net of Heise 2017's 18–26% clamp CV; 50% at lipohypertrophic sites, Famulla 2016),
     and not count spread alone (count_sd ×2 left the first hour unchanged, lesson 150). Untested, with a mechanism
     for this: the meal eaten later than or partly instead of what was entered (pre-bolus timing, unfinished meals);
     each needs a measured rate before it becomes a switch.
     - **Unfinished meals, as far as edits show them, are rare**: of entries ≥ 15 g, those revised downward more than 5
       min after entry are 0.4% per donor on average (p90 1%; 253 across 193 donors; to a median 0.70 of the entry,
       34 min later), against 1,641 revised upward. Edits under-record (most people never edit), but where the record
       speaks, real meals grow after entry rather than shrink. Pre-bolus timing has no record in the donor data.

186. **Real people take Loop's full recommendation on the first of two meal boluses; the sim halves it, but matching
     that does not by itself bring the missing lows.** Requested ÷ recommended at the bolus nearest an entry ≥ 15 g
     (`bolus_ratio.py`; donors from `bolus_decisions.parquet`, 34,161 bolused entries; sim from `bolus_requests`):
     donors p10–p90 all 1.00, < 0.95 in 6%, > 1.05 in 4%; c201_base < 0.95 in 32% (p10 0.42, p25 0.74). The gap is the
     split bolus (LESSONS 47, 54), which the sim draws as f = 1/(1 + ratio) of the recommendation first and the rest in
     units ~12 min later. In donors, 23% of bolused entries have a second bolus within 30 min; the first is 1.00 of the
     recommendation in 96%, the second is its own fresh recommendation (median 1.00; 0.78 of the first in units; rec ≈ 0
     in 14%); 41% of second boluses follow more carbohydrate entered or an upward edit (median 20 g), 59% no recorded
     carbohydrate. Lows within 2 h follow 10.5% of donor bolused meals vs the sim's 5.7%.
     - **`--enable split_full`** (f7f2ca3, off), full recommendation first, the planned remainder on top: ratios match
       (< 0.95 in 7%); lows 1.083/day (donors 1.077, KS 0.97), t54 KS 0.80, TDD 38.7 (38.8), early lows after bolused
       meals 0.150/day (0.210); but bg_mean 147.5 fails, with σ_meas G7, Libre sd/MAD and between-day fraction (all
       marginal in the base): 37 vs 40. Split meals get ~1.9× their recommendation with no extra carbohydrate.
     - **split_full v2** (eed8ebd, same switch, `split_more_p` 0.41): second dose = Loop's fresh recommendation, after a
       second helping (lnN median 20 g, eaten and entered) in 41%: ratios match, but Loop recommends ~0 twelve minutes
       after a full dose with no new carbohydrate, so lows 0.833/day, early lows 0.108; hurst_long, t54, day/night fail:
       35 vs 40. Not adopted; the switch stays off.
     - So the lows of the first arm came from insulin real people do not take as drawn. The open fact is the donors'
       59% of second boluses with no recorded carbohydrate for which Loop still recommended ~0.8 of the first dose: what
       made the forecast rise (a carb entry before the first bolus missed by the ±15 min window, a pre-bolus taken on a
       correction-only recommendation, the first dose capped) decides how the sim should draw them. Measure that next.

187. **Most of the donors' "second boluses" are a neighbouring entry's; real split meals are second helpings, and
     modelling them so does not bring the early lows.** For donor bolused entries ≥ 15 g with two boluses within
     −15..+30 min and no new carbohydrate recorded between them (6,298), the first bolus came before the carb entry in 46%
     (1% for single-bolus meals) and another entry sat in the prior 90 min in 44% (16%): mostly the previous entry's dose or
     a correction taken before entering, not half of this meal's. The genuine split is the 9.5% with more carbohydrate
     entered (or edited up) between the doses: first dose 0.99 U per 10 g entered (single meals 1.03), the second 0.67 of
     the first, 12.7 min later. LESSONS 47's p_split (boluses per entry − 1) counts both.
     - **split_full v3** (21b6d8c, `--enable split_full`, off): every meal bolus is the full recommendation (the halved
       split dropped); 9.5% of bolused meals ≥ 25 g are eaten as two helpings (the second lnN median 20 g, ≤ 60% of the
       meal, ~13 min later, entered and bolused on its own; grams taken from the meal, so intake is unchanged). c213 against
       c201_base: ratios match (< 0.95 in 7%), bg_mean 150.5 and TDD pass; lows 0.833/day, early lows after bolused meals
       0.097 (donors 0.210), t54 0.119 and P(reach 54) fail, user boluses 3.83/day (donors 4.59) fail, zero-delivery
       fraction 27.6% (donors 33.3%, base 30.1%) fails: 35 vs 40. Not adopted.
     - Across v1–v3, giving the meal its full recommendation up front does not add early lows; only insulin beyond the
       recommendation did (v1). The donors' early post-meal lows (0.21/day, BG at entry ~120, ~67 min later) and their
       larger zero-delivery share are the same signature: the meal's recommendation outruns the body more often in life
       than in the sim, and Loop then withholds. The settings-to-body carb ratio is the coupling that sets this
       (person.py, LESSONS 37: an independent draw gave 4× the donors' post-meal lows; the half-weight blend now gives
       half). Its spread is the next measurement: the donors' per-meal rise per entered gram against their CR.

188. **Per meal, the sim's post-bolus drop matches the donors'; the missing early lows are spread thin.** Bolused isolated
     entries ≥ 15 g (`meal_out.py`, G7; 13,175 donor meals, 1,249 sim): nadir over 0–2 h minus entry CGM p10 / p50 / p90
     −84 / −11 / +3 vs −85 / −12 / +2; drop ≥ 40 in 25.7% vs 27.1%; SD of person medians 16.7 vs 18.5, within-person SD
     36.6 vs 31.4. So the carb-ratio setting's mismatch to the body (LESSONS 37's half-weight blend) has the donors' spread.
     Ending below 70 within 2 h: 9.7% vs 7.7% of meals; by entry BG < 100 / 100–140 / ≥ 140: 21.3 / 8.5 / 6.4% vs 20.6 /
     6.6 / 4.7%; entry BG median 133 vs 140.
     - **Meal occasions**: paired with their own donors (`bol_occ.py`, 86 people), the simulated people make 2.88 carb
       entries/day against 3.45 in the donors' exports, ≥ 15 g 2.17 vs 2.82, and bolus all of them (donors 92%). The
       sim reproduces its template (entries_raw 2.95, 0.95–0.98 by tercile); entries_raw merges entries < 30 min apart
       (templates.add_raw_rates), and donors make ~0.5/day of those (courses, second helpings, amount corrections) where
       the sim makes almost none.
     - The early-low shortfall (0.11 vs 0.21/day, LESSONS 185) is therefore several small parts multiplied: ~25% fewer
       lows per isolated meal from ordinary starts, a slightly higher meal start, fewer separate entries, and the stacked
       multi-entry meals the sim lacks. No single mechanism carries it; each part is a measurement for its own component.

189. **sleep_util holds the night level but adds no night rises.** The unentered-rise statistic (LESSONS 184) on c202_su
     (sleep_util on c201_base): 0.50 per person-night at 00–06 h (base 0.48, donors 0.66), not-V 0.33 (0.33; donors
     0.44), per-person p10 / p50 / p90 0.17 / 0.42 / 0.86 (unchanged); 87% still sensor recoveries with no carbohydrate
     behind them. With night CV above the donors' (40.7 vs 36.0), the sim's nights vary as much as real ones but mostly
     downward, real ones more often upward. A smooth change in utilisation moves the level, not the excursions; the
     missing component makes discrete upward events of ~50 mg/dL over ~80 min for nearly everyone, and must not be a
     fitted noise term (no mystery terms). Unrecorded night eating, rebound after Loop's night suspensions (31% of donor
     night rises follow a cut, LESSONS 184) and insulin-delivery interruptions are the named candidates to measure.

190. **Delivery disruptions are not the donors' extra night rises.** Of donor night (00–06 h) unentered rises, 23% have a
     disruption window (`disruptions.csv`) in the 2 h before (0.15 per night: pump_error 0.069, loop_offline 0.039,
     disruption 0.034, suspend 0.017; `night_disr.py`), but against random night moments the enrichment is 1.00 for pump
     errors and 1.11–1.28 for the rest. The attributable excess is ~0.02 per night of the 0.18 the sim lacks. Of the
     LESSONS 189 candidates, unrecorded night eating and rebounds after Loop's own night suspensions remain.

191. **After Loop cuts insulin at night, real bodies turn upward sooner; the EGP arm's speed carries part of it.**
     Night (00–06 h) cut episodes (`cut_rebound.py`: 30-min delivery < 30% of the person's own night median, after ≥ 60 min
     uncut): donors 1.08 per night, c201_base 1.19, from similar CGM (median 125 vs 120). An unentered rise follows within
     2 h in 29.7% vs 20.2%; CGM change at +2 h from onsets ≥ 120: −21 vs −35 (from 90–120: +2 vs −1). Loop withdraws
     insulin as often; the simulated body keeps falling longer.
     - **Diagnostic `--set ins_p2e=0.012`** (c214; default 0.006, Pete 2026-10-17, set on the meal-tracer EGP nadir,
       LESSONS 131): rise after a cut 23.0%, +2 h from ≥ 120 −29, night unentered rises 0.54 (donors 0.66), night share of
       lows 45% → 40%, night CV 38.4 (passes); lows 0.75/day, day/night and circadian amplitude fail: 35 vs 40. Not a
       candidate as is: a faster X_E also deepens and advances the meal EGP nadir the tracer data fixed.
     - Evidence lead, unverified: in lean non-diabetic people, hepatic glucose output returned halfway to basal 59 min
       after a 40 mU/m²/min insulin infusion stopped and 119 min after 120 (deactivation study, abstract only; Prager,
       Wallace & Olefsky 1986 JCI doi:10.1172/JCI112599 report activation and deactivation rates of HGO and peripheral
       action). The sim's single X_E rate gives ~115 min both ways. An onset/offset asymmetry in insulin's hepatic action
       is the named form to check against the full papers before any switch.

192. **The deactivation evidence (Gray 1982) needs a saturating hepatic dose-response before it can set a rate.** Gray
     RS, Scarlett JA, Griffin JW, Olefsky JM, Kolterman O. *Diabetes* 1982;31:929 (doi:10.2337/diab.31.10.929), 10 lean
     non-diabetic, euglycaemic clamp: after 40 / 120 mU/m²/min (insulin 126 / 350 µU/mL, falling with t½ 7–8 min), HGO
     stayed fully suppressed 50 / 80 min, then reached half of basal at 59 ± 8 / 119 ± 6 min; peripheral uptake halved at
     42 / 78 min. Deactivation lags insulin and is faster after lower insulin.
     - Replaying the protocol on the default EGP arm (X_E linear in (I − Ib)/Ib, EGP = 1 − se·X_E clipped at 0, se 1, so
       full suppression at 2× basal): at 126 µU/mL X_E settles ~11× past full suppression, so even p2e_off 0.02 keeps
       HGO at zero 117 min and gives R50 151 min (Gray 50 / 59); 0.006 never recovers within 6 h. The linear arm
       cannot use supraphysiological clamp data: real suppression saturates in insulin (half-maximal near ~2× basal,
       Rizza 1981 [S: verify]), so the state does not have that far to unwind.
     - Named upgrade for the EGP arm, both parts evidenced before any switch: (1) a saturating (Michaelis–Menten)
       hepatic response to insulin, so clamp data map onto it; (2) separate on / off rates, onset kept on the meal tracer
       nadir (Romeres 2025, p2e 0.006), offset fitted to Gray's R50s through (1). LESSONS 191's p2e 0.012 diagnostic
       is the direction; this is the form.

193. **A saturating hepatic signal with a faster offset holds nights and loses daytime lows.** `--enable egp_sat` (2978edc,
     off): the hepatic insulin signal saturates, v_eff = 2.57·v/(2.57 + v) in suppression units v = sE·(I − Ib)/Ib (half
     / full HGO suppression at 0.62 / 1.64, Rizza, Mandarino & Gerich 1981 Am J Physiol 240:E630: 29 / ~60 µU/mL), and
     X_E relaxes at 0.015/min when the signal falls (onset stays 0.006; Gray 1982's R50s through this form give 0.012–0.020,
     LESSONS 192); people recalibrated (sE 0.20 → 0.31 for v01000, total ISF unchanged). c215 against c201_base: rise
     within 2 h of a night Loop cut 20% → 24% (donors 30%), +2 h from ≥ 120 −35 → −29 (−21), night unentered rises 0.48 →
     0.54 (0.66), night CV 35.8 (passes; donors 36.0), hurst_long KS 0.91; meal EGP nadir 0.75 at 120 min (base 0.77; Romeres
     0.56 at ~160, which the base itself no longer meets after the total-drop ISF recalibration — a separate open item);
     but lows 0.67/day, t70 0.81, t54 0.088, day/night and zero-delivery fraction fail: 31 vs 40. Not adopted.
     - The pattern across lessons 169–193: every mechanism that holds the night up (posture off, sleep_util, ge_circ,
       p2e 0.012, egp_sat) also removes daytime lows, because it acts on falls everywhere. The donors have more daytime
       lows than the sim AND fewer night lows. The components still missing are therefore time-specific in opposite
       directions: something that makes days fall more (LESSONS 185–188: bolused meals going low, spread over several
       small parts) and something that makes nights rise more. Adopting a night fix waits for the daytime-lows half.

194. **First component review: the meal EGP arm has drifted, and neither of its parameters refits it alone.**
     `review.py` (22d78c4; donor targets in runs/2026-10-18-additive-workouts/review_targets.json, the same code both
     sides) on c201_base, run / target: A5 meal EGP nadir 0.77 at 130 min / 0.56 at ~160 (fitted at 0.54 before the
     total-drop ISF recalibration and κ); A9 low nadir p10 / p25 / p50 43 / 51 / 58 vs 40 / 50 / 57 (holds), duration p90
     75 vs 65; bolused-meal 0–2 h drop p10 −85 vs −84 (holds), ending < 70 7.5% vs 9.7%, 3-h change +6.7 vs +21; entries
     2.81 vs 3.28 (LESSONS 188); night rises 0.48 vs 0.67; rise after a night cut 20% vs 30%.

     | arm (recalibrated) | EGP nadir | 3-h change | meals < 70 | low dur p90 | cut rise | matched |
     |---|---|---|---|---|---|---|
     | base (p2e 0.006, share U(0.5, 0.7)) | 0.77 @130 | +6.7 | 7.5% | 75 | 20% | 40 |
     | p2e 0.010 (c216) | 0.69 @120 | −0.4 | 7.4% | 70 | 24% | 35 |
     | p2e 0.015 | 0.62 @110 | −3.0 | 8.0% | 75 | 24% | 34 |
     | share 0.8 (c217) | 0.66 @130 | +16.4 | 4.4% | 90 | 19% | 29 |
     | share 0.9 | 0.62 @120 | +23.0 | 4.0% | 90 | 16% | 28 |
     | donors / tracer | 0.56 @160 | +21 | 9.7% | 65 | 30% | |

     - The rate deepens the nadir by making it earlier, and meals end lower; the share deepens it and makes meals end
       right (+23 vs +21) but lows longer and post-meal lows rarer, since a liver-heavy insulin effect acts slowly. Low
       depths hold in every arm. No single-parameter refit restores A5 without breaking another target, so the EGP arm
       (share, rate, and the nadir's 30–50 min early timing, which no arm moves) is refitted jointly with what it
       trades against, or its form revisited (egp_sat, LESSONS 193). Base unchanged.

195. **Read like-for-like, the base under-suppresses meal EGP and share ≈ 0.8 fits the tracer nadir.** Two corrections to
     the A5 check (`egp_romeres2.py`): Romeres 2025's 44 ± 17% is the mean of each subject's own nadir (time 160 ± 110 min,
     SD), not the minimum of a median curve; and tracer EGP includes the liver's glucose-mediated suppression, which the
     model carries inside its lumped SG term (UVA/Padova kp2 ≈ 0.0021/min of the sim's sg 0.003, so ~0.7 hepatic). Per
     person (mean curve over their isolated meals ≥ 20 g; pre-meal EGP ≥ 30% of basal), SG hepatic part 0.7:

     | arm | nadir suppression mean (p50) | mean 0–5 h | nadir time p50 |
     |---|---|---|---|
     | c201_base (share U(0.5, 0.7)) | 0.34 (0.29) | 0.16 | 120 |
     | c217 share 0.8 | 0.50 (0.47) | 0.27 | 120 |
     | c217 share 0.9 | 0.61 (0.60) | 0.38 | 120 |
     | Romeres 2025 T1D adults | 0.44 ± 0.17 | ~0.45 [verify: evidence/13 summary] | 160 ± 110 |

     (SG hepatic part 0.5 moves each nadir by ≤ 0.05.) Insulin action timing still meets its clamp target on today's
     bodies (GIR peak 105 min vs ~100, 6.6% of the effect in the first hour vs 6.3%). So A5's share drifted low, not its
     rate; its evidence now asks for ~0.8, at the cost lesson 194 shows (low duration p90 90 vs 65, meals ending < 70 4.4%
     vs 9.7%: 29 matched). Suppression also fades too early at every share (5-h mean 0.27 vs ~0.45). Refitting A5 to its
     evidence means re-reviewing what then drifts (A9's low durations, the meal-low rate) on that base.

196. **Review loop, step 1–2: A5 refitted to its tracer evidence, then its offset; the old base's lows partly came from a
     liver too weak and too slow.** (Pete 2026-10-18: adopt the evidence refit, then refit what drifts.)
     - **Step 1, EGP share U(0.7, 0.9)** (9f73045, default): c218 against c201_base: per-person meal EGP nadir suppression
       0.50 (median 0.45; Romeres 0.44 ± 0.17), but bg_mean 155.8, CV 37.4, TIR 68.5, hurst_long 0.349 (donors 0.247), low
       duration p90 80 (65), meals ending < 70 4.7% (9.7%), rise after a night cut 18% (30%): 31 matched. A liver-weighted
       insulin effect that relaxes at one slow rate makes every excursion persist.
     - **Step 2, egp_sat on that base** (Rizza 1981 saturation, Gray 1982 offset 0.015; recalibrated; now default): c219:
       nadir suppression mean 0.45 (0.44), low duration p90 66 (65), CV 34.8 (34.8), night CV 37.2 (passes), night rises
       0.53 and rise after a night cut 22% (both toward the donors'); low nadirs 44 / 51 / 58 (40 / 50 / 57); but lows
       0.58/day (1.08), t70 0.73, t54 0.06, P(reach 54) and day/night fail: 28 matched (vs 31 at step 1, 40 on the old
       base).
     - Every physiology component now on its own evidence removes lows; the old base's low count leaned on the
       under-suppressing, slow liver. Next in the loop: the components that make lows (meal-insulin mismatch,
       LESSONS 185–188; anticipatory defense, whose carbs prevent lows; counter-regulation, fitted to depths only),
       each against its own target, on this base.

197. **Review loop, steps 3–4: insulin timing and carb sensitivity refitted; the missing lows are within-person meal
     variability, not any fitted constant.** On the share-0.8 + egp_sat base:
     - **A5 clamp timing drifted**: a 0.2 U/kg clamp replay (glucose held at Gb) on calibrated bodies gives a GIR peak at
       125 min (old base 108; target ~100) with the same 6.7% in the first hour (6.3%): most of the effect now runs
       through the liver's slow onset. Onset rate p2e 0.008 / 0.010 / 0.012 / 0.015: peak 120 / 116 / 109 / 101 min, first
       hour 7.1 / 7.5 / 7.9 / 8.4%. **Default p2e 0.012** (offset 0.015 under egp_sat).
     - **G7 carb sensitivity drifted slightly**: labeler g-eq per entered gram 1.208 (c201_base) → 1.247 (c219; donors
       1.21). **CSF_BLEND_CAL_TOTAL 1.08 → 1.05.**
     - c220 (both): review unchanged within noise — per-person meal EGP nadir 0.49 at 110 min (Romeres 0.44 ± 0.17 at 160 ±
       110), low depths and durations on target, meals ending < 70 3.8% (9.7%), 27 matched (28).
     - **ISF_W** (settings-to-body blend, open since LESSONS 37) 0.7 / 0.85 (c221): meals ending < 70 4.1 / 4.5%, drop p10
       −74 / −77 (−84), between-person SD of the 0–2 h drop 13.4 / 17.3 (16.7), within-person SD 28.9 / 30.8 (36.6); 27 /
       25 matched. Stays 0.5: the between-person spread is the donors' at 0.5–0.85, the within-person spread is short
       at every w.
     - With the physiology on its evidence the low deficit (0.67 vs 1.06/day, mostly within 2 h of meals) is the
       within-person variability of real meals (LESSONS 146–150, 174–178): the same person's meals ending in lows more
       often. That is the component to find, and it is not a constant in the existing ones.

198. **The missing meal variability is not the starting state: what happens inside a real meal varies 1.5× more.**
     Bolused isolated entries ≥ 15 g, G7, within-person (each person demeaned), 0–2 h CGM drop (`meal_var.py` on c220,
     `meal_var_don.py`):

     | | donors (12,991 meals, 120 people) | sim c220 (1,162, 78) |
     |---|---|---|
     | within-person SD of the drop | 36.7 | 26.7 |
     | SD of CGM at entry / its correlation with the drop | 45.7 / −0.58 | 47.8 / −0.59 |
     | 30-min trend SD / correlation | 28.8 / −0.14 | 24.7 / +0.01 |
     | insulin state / correlation | Loop IOB SD 1.50 U / −0.33 | delivered prior 3 h SD 1.83 U / −0.44 |
     | joint R² of the starting state | 0.34 | 0.41 |
     | **SD left after the starting state** | **31.5** | **~20.5** |

     - Meals start from the donors' spread of states and respond to them the same way. The remainder, what happens within
       the 2 h, is ~1.5× wider in life.
     - Sim ground truth also says what does *not* carry it within 2 h: the true SI multiplier at the meal (within-person
       log SD 0.31, correlation with the drop −0.06) and the eaten/entered ratio (log SD 0.20, +0.07). Loop and the meal's
       own timing absorb them over this window.
     - Candidates that act inside 2 h, each to be sized from evidence: per-dose insulin absorption in real pump use
       (A4 15% net, from clamps; real-life site-to-site and wear variability larger, Heinemann 2002 review [verify]);
       per-meal carbohydrate appearance speed (GI and composition; gi_cv tested as a whole-meal ceiling, LESSONS 177);
       post-meal activity. The lunch, early-low and first-hour gaps (LESSONS 150, 180, 185) are the same remainder.

199. **Per-site absorption spread on by default; it adds part of the inside-the-meal variability.** `site_cv` 0.27
     (Haidar 2013 per-site tmax CV ~27%; lesson 115 left it a switch on an older base) on the current defaults (share 0.8,
     egp_sat, p2e 0.012, CSF 1.05; c222, bc28aeb): lows 0.50 → 0.58/day (donors 1.08), t54 0.031 → 0.059 (0.215),
     P(reach 54) 0.128 → 0.182 (0.200, passes), low share < 54 0.30 → 0.34 (0.37); within-person SD of the bolused-meal
     drop 28.9 → 29.7 (36.7); low duration p90 70 → 80 (65); 26 → 28 matched. **Default 0.27.** The remainder after
     the starting state (LESSONS 198) stays most of the gap: per-site speed varies across a set's 2–3 days, the
     real variation is meal to meal.

200. **Re-testing earlier-rejected switches on the evidence base: none closes the inside-the-meal remainder at its
     evidenced size.** Current defaults (share 0.8, egp_sat, p2e 0.012, CSF 1.05, site_cv 0.27), c223/c224 (43f5f08):

     | arm | within-person SD of drop | meals < 70 | drop p10 | 3-h change | t54 | lows/day | matched |
     |---|---|---|---|---|---|---|---|
     | base | 29.7 | 4.1% | −79 | +14 | 0.059 | 0.58 | 28 |
     | ceiling_speed, gi_cv 0.4 (evidenced) | 30.2 | 4.1% | −80 | +7 | 0.088 | 0.54 | 27 |
     | ceiling_speed, gi_cv 0.6 | 31.4 | 4.3% | −78 | +5 | 0.059 | 0.58 | 28 |
     | ceiling_speed, gi_cv 0.8 [J, LESSONS 177] | 34.6 | 5.6% | −88 | +2 | 0.088 | 0.58 | 29 |
     | sleep_util | 28.2 | 4.0% | −79 | +12 | 0.059 | 0.42 | 27 |
     | ge_circ | 28.6 | 4.3% | −78 | +9 | 0.058 | 0.50 | 29 |
     | dose_beta 0.5 | 32.9 | 5.2% | −90 | +8 | 0.045 | 0.42 | 26 |
     | donors | 36.7 | 9.7% | −84 | +21 | 0.215 | 1.08 | |

     - Per-meal emptying speed reaches the donors' spread only at gi_cv 0.8, twice what Elleri 2013's high- vs low-GL
       contrast supports (t50 100 vs 175 min, log ratio 0.56). Not adopted; the rest as before.
     - Every arm that widens the spread also lowers the 3-h ending (+21 in the donors): a wider meal-speed spread adds
       slow meals that the bolus outruns, never faster ones that rise higher. The remainder needs variation in both
       directions within 2 h: meals larger than entered (the donors' upward edits, LESSONS 185) alongside smaller ones,
       and insulin that acts faster or slower dose to dose. Base level +9 (160 vs 151) is also open on this base.

201. **On the evidence base the night profile matches; the waking day runs 10–20 mg/dL high.** Hourly median-over-people CGM
     (`hour1*.py`, local clock), c223_base minus donors: 00 h +8, 01–03 h +2 / 0 / −1, 04–07 h −8 to −3, 08 h +6, 09–12 h
     +17 to +21, 13–15 h +7 to +10, 16–20 h +10 to +17, 21–23 h +6 to +10 (mean 160 vs 151). The night that every earlier
     base had 10–13 low (LESSONS 184) now sits on the donors' through 03 h. The excess is daytime, peaking late morning.
     - A mechanism to measure, not yet a finding: under egp_sat the hepatic signal saturates, so the large insulin
       levels of meal boluses suppress EGP less per unit than the small probe dose each person's ISF is calibrated on;
       meal insulin then works less than the settings assume, by day. Check: per person, the effect of a meal-size
       bolus against the probe ISF under egp_sat, and whether the evidence (Rizza 1981 healthy, portal) carries to
       peripheral insulin in T1D.
     - **Checked: not dose saturation.** Linear-part total drop per unit from 250 mg/dL, 3 U ÷ 0.5 U: 0.99 with egp_sat
       (1.17 without), so meal-size boluses act per unit as the probe says. (Full-body peak ratios, 4 U ÷ 0.5 U at 180:
       0.75 vs 0.84, are the restoring terms, and a 2-U probe from rest hits the 10 mg/dL floor.) The daytime excess has
       another cause.

202. **The daytime excess is intake, not insulin: the TDD budget leaked; closing it helps, the day stays high.**
     - B1b basal-need profile at the donor schedule's full shape (`prof_w` 1.0, c225): daytime unchanged (+15–25), low
       depths exactly the donors' (40 / 50 / 57), lows 0.50/day: 26 matched. Not adopted.
     - Delivered insulin by local hour (`ins_hour.py`, G7): the sim gives MORE by day (1.8–2.1 U/h at 08–22 h vs donors
       1.1–1.8; G7 TDD median 39.8 vs 36.1), nights equal. Paired with their own donors, TDD ratio 1.00, but people eat
       1.20× their carbohydrate budget (c223; c201_base 1.27×): the budget (LESSONS 143) subtracted grazing and the donor's
       rescues but not pre-emptive carbohydrate (8% of the budget on average) and floored meals at half the budget, so
       heavy grazers ate over it. The old base's weak liver hid the leak.
     - **`budget_tight`** (acfac34; now default): the budget also pays for pre-emptive carbohydrate at the sim's own
       mean share (0.08 of carbs_day, an accounting value from c223, not fitted to donors) and floors meals at 0.2. c226:
       mean 160 → 157 (151), CV 34.5, hurst_long 0.327 → 0.304, daytime +13–18 (was +15–21), lows 0.54/day: 29 matched (28).
     - Open: the remaining daytime excess with donor-level insulin; a per-person pre-emptive expectation (not the mean
       share) when the defense team's own rates are measured on donors.

203. **The daytime excess is not the circadian sensitivity swing.** B1 at half / zero of Visentin's swing on the
     budget_tight base (c227): hourly CGM 09–23 h 158–171 / 156–175 (donors 142–168, the base 156–173); 24-h amplitude
     0.159 / 0.164 (base ~0.17; donors 0.131); hurst_long 0.303 / 0.284; lows 0.50 / 0.42 per day; 27 / 30 matched.
     The amplitude and the daytime level come from the day's other structure (deeper pre-dawn trough at 04–06 h,
     119–125 vs 131–134, and a steeper morning climb, 121 → 166 by 11 h vs 130 → 148). B1 keeps its evidenced full
     swing. The morning climb and the intake per unit of daytime insulin are next.

204. **Insulin acts in the simulated bodies as in the donors', read by the same quiet-hour regression.** Raw yardstick
     slope (hourly CGM change on Loop-absorbed insulin, intercept; quiet = no entry or user bolus in the prior 4 h;
     `sim_yardstick.py`, `don_yardstick.py`) divided by the person's isf_true (the donor yardstick ISF the body is
     calibrated to): donors 0.56 (p25 / p75 0.43 / 0.70; 168 donors, median 934 quiet hours); c226_bt 0.53 (0.40 / 0.67;
     107 people, 113 hours); c201_base 0.52. Against the settings ISF: 0.52 vs 0.51. The total-drop calibration
     (LESSONS 143) is like-for-like with how the donors' ISF is measured, on the evidence-fit liver as on the old one.
     With quiet-hour insulin action, carb rise per entered gram (labeler 1.21) and paired TDD all at the donors', the
     daytime excess (+13–18) sits in what is eaten relative to what is bolused for, not in the body's response to either.

205. **Paired with their own donors, the level is close; what is off is the day's shape.** Each simulated person against
     the donor their template came from (`pair_hour_sim.py` / `pair_hour_don.py`, 108 people): mean CGM difference median
     +4.2 mg/dL (c226_bt), +2.8 (c228); by hour, 02–06 h −6 to −11 and 09–11 h +14 to +20, 16–20 h +7 to +11. The cohort-
     level +6 (157 vs 151) is mostly which donors the templates sample; the person-level gap is the 24-h amplitude
     (0.18 vs 0.13): nights too low, late mornings too high.
     - Entered grams: 73.7 vs 91.7 g/day (median ratio 0.84), short at 09–12 and 17–20 h. **`entry_own`** (91f4e83, off):
       entry probabilities scaled on a dry-run plan to the donor's raw entered grams (new template column
       entered_g_raw); ratio 0.84 → 0.87 only, since most people already enter nearly every meal (probability capped at
       1); the gap is grams per entry (donors ~26.6, sim ~24). c228: mean 157.8, the same day shape, 30 matched (29).
       Not adopted.
     - Next, on the amplitude: what moves glucose from night to late morning in the simulated body with donor-level
       insulin by hour (paired insulin by hour still to compute; the donor column of pair_hour_don.py is wrong and
       must not be used).

206. **Each donor's own meal clock, on by default: insulin by time of day now matches, and the excess moves to the
     afternoon.** Paired insulin by hour (fixed donor column: per-step rate, `pair_hour_don.py`): daily 0.975 of the
     donor's, but 00–06 h 0.92× and 06–11 h 1.24–1.52× while the sim's first morning entry came ~1 h earlier (median
     8.67 vs 9.65 h; `bfast_time.py`). The templates had lost the meal-clock columns (`templates.add_meal_clock`,
     LESSONS 123; restored to templates_pilot_logs.csv: breakfast / lunch / dinner medians 8.79 / 12.77 / 19.04 h), and
     `own_clock` was off (LESSONS 135: 30 vs 35 on an older base). c229 (columns, switch off) reproduced c226 exactly.
     - **`own_clock` on** (c230, now default): day/night insulin ratio 2.025 (donors 2.057, KS 0.79; failed on every
       earlier base); 09–11 h 148–165 (was 156–166; donors 142–148); 12–15 h 173–179 (donors 151–165); 24-h amplitude
       0.193 (0.131); lows 0.58/day; 26 matched (29). Adopted as each person's own measured behaviour; the afternoon
       excess after correctly timed lunches is the next measurement (lunch response amplitude per entered gram and the
       insulin given for it, paired).

207. **On the own-clock base, small lunches follow long breakfast tails, and no morning EGP component carries it.**
     Isolated entries ≥ 20 g, CGM change at 0.5–4 h (c231_base): breakfast +15 / 34 / 43 / 44 / 49 / 36 / 30 / 23 (donors
     +18 / 41 / 42 / 35 / 29 / 27 / 22 / 16, LESSONS 181), lunch +5 / 16 / 20 / 14 / 10 / 13 / 13 / 10 (donors +18 / 34 /
     36 / 35 / 33 / 31 / 26 / 18). Breakfast rises right and falls too slowly; lunch then starts high under Loop's
     correction.
     - Not B1 (zero swing, c227_s0: lunch +6 / 15 / 15, breakfast tail +31 / 26 / 31). Not B1b (`prof_w` 0, c231: breakfast
       +42 / 33 / 27 at 2.5–3.5 h, lunch unchanged, lows 0.42/day, 29 matched). B2 dawn is inert in templated cohorts
       (it applies only to people without a donor basal profile; `--disable dawn` reproduced the base exactly).
     - Morning truth (c226): EGP 0.93–0.95 of basal at 06–08 h against 0.70 at midday; insulin delivered 1.13–1.76 U/h.
       Next: the breakfast bolus's own timing relative to eating under the own clock, and the overnight-to-morning IOB
       the sim starts breakfast with (paired, the sim delivers 0.92× the donor's insulin at 00–06 h).
     - **The breakfast's starting state matches** (`bfast_state.py`, first entry ≥ 15 g at 04:00–10:30, paired, 44 people
       with ≥ 5 breakfasts): insulin delivered in the prior 3 h 0.93× the donor's, manual bolus per 10 g ratio 1.00
       (median 1.04 vs 1.19 U), CGM at entry +7. With the same bolus for the same entry from a similar state, the
       longer tail (+8 at 3–4 h) is the body's handling of breakfast: what is eaten beyond what is entered at
       breakfast, or how fast it appears.

208. **Glucose effectiveness at the top of its evidence range puts the level on the donors'.** Real meals and
     excursions return faster than the sim's (donors have more unentered rises after meals, 0.47 vs 0.38 per isolated
     breakfast, `post_slot_rises.py`, yet lower tails; the breakfast's starting state matches). SG ×1.5 (median
     0.0045/min; evidence range 0.0013–0.0047, UVA/Padova; Pete 2026-10-16: calibratable within it), c232 on the own-clock
     base: mean 151.7 (donors 151.4, passes), CV 33.2 (passes), low duration p90 65 (65), hurst_long 0.322 → 0.299,
     afternoon 12–19 h 162–168 (donors 151–166), breakfast tail +30 / 26 / 21 at 3–4 h (+36 / 30 / 23 before; donors
     +27 / 22 / 16); but lows 0.58 → 0.42/day (1.08), t54 0.031, low share < 54 0.25: 28 matched (26). **Default median
     0.0045.** Lows remain the largest open gap: every component that brings a body back toward Gb faster removes
     some of them, so the missing lows need their own source (LESSONS 198: within-meal variability).
     - **Decision (Pete, 2026-10-18): keep searching named sources** for the within-meal variability; gi_cv stays at its
       Elleri-sized 0.4 and no lumped meal-state term is added (Hengist 2025's duplicate-meal ICC 0.17–0.28 is a target for
       the named factors together, not an input). Checked so far: carb-count error is already at Brazeau 2013's size
       (log N(−0.10, 0.20) gives ~19% mean absolute error vs 20.9 ± 9.7%); real-world pre-bolus timing has no measured
       distribution in the literature found (a 2019 review: timing matters less than dose), and the sim already takes
       bolus-vs-entry timing from each donor. Remaining named candidates: per-dose insulin absorption in free living
       (beyond A4's clamp-net 15% and site_cv), post-meal activity (frequency and timing against HealthKit workouts where
       BDDP holds them), and meals larger than entered (the donors' upward edits).

209. **A free-living per-dose absorption spread does not carry the within-meal variability.** Evidence for a wider A4
     than its clamp-net 0.15: Schiavon et al. ATTD 2020 (abstract, 10 youths on hybrid closed loop: meal-to-meal intra-
     individual CV of model-derived absorption parameters 34–94%, estimation noise included); CSII inter-occasion
     variance ~40% of the total (depth, site age, perfusion). `--set dose_cv=0.3` (047975b, off) on the SG-0.0045 own-clock
     base (c233): within-person SD of the 0–2 h drop 30.0 → 29.0 (donors 36.7), meals ending < 70 3.0 → 2.8%, lows 0.42 →
     0.42/day, low duration p90 65 → 80 (65); 28 matched either way. Kept at 0.15: the drop within 2 h is set by early
     insulin against early carbohydrate, which a per-dose speed spread barely moves. Of the named candidates, post-meal
     activity (needs HealthKit workouts from BDDP, a Databricks login) and meals larger than entered remain.
     - **Sugary drink with 20% of main meals** (`meal_drink_p` 0.2, LESSONS 119; c234): lows 0.42 → 0.50/day, lunch +21 / 25
       at 1–1.5 h (+18 / 18), within-person drop SD 27.6 (30.0), 29 matched (28). Kept off: its rate is general-population
       (about half of US adults drink a sugar-sweetened beverage on a given day, NHANES data briefs); a T1D-specific
       per-meal rate is the evidence step before a default.

210. **Reference base after the review loop (c235_base, f725660): 28 of 51.** Defaults since c201_base: EGP share U(0.7,
     0.9), egp_sat, p2e 0.012, CSF cal 1.05, site_cv 0.27, budget_tight, own_clock (templates_pilot_logs.csv now carries the
     clk_* and entered_g_raw columns), SG median 0.0045, meal_drink_p 0.12. Against donors: mean 150.5 (151.4), CV 33.3
     (34.8), day/night insulin 2.051 (2.057), hurst_long 0.278 (0.247), low nadirs 47 / 53 / 58 (40 / 50 / 57), low
     duration p90 70 (65), per-person meal EGP nadir on the tracer's; open: lows 0.50/day (1.08) and t54 0.031 (0.215),
     24-h amplitude 0.187 (0.131), night unentered rises 0.49 (0.67), within-person meal drop SD 30.4 (36.7), lunch rise
     +19 / 22 at 1–1.5 h (+34 / 36). Validation convention unchanged (`--enable rc_own`).

211. **An hours-scale sensor bias for G7, on its own sensor evidence.** `slow_bias` (OU, sd at 130 mg/dL, τ 180 min;
     Breton & Kovatchev 2008: CGM error autocorrelated "up to several hours") was left at sd 0 in LESSONS 49 because it
     lowered an already-low Hurst. On the c235 bodies the G7 fit to its own FDA targets (sensor_fit.py, K213919) has
     drifted: loss 10.89 (in-range MARD 6.75 vs 8.6, < 54 MARD 26.1 vs 14.0, elasticity 0.53 vs 0.70). sd 5: loss 7.86
     (in-range MARD 8.56, < 54 12.6, elasticity 0.69; PARD 10.6 vs 8.9 worse); sd 8: 14.70.
     - c236 cohorts on the c235 defaults, sd 5 / 8: hurst_long 0.280 / 0.274 (KS 0.16 / 0.25, now pass; donors 0.247), low
       nadirs 44 / 51 / 57 (40 / 50 / 57), share of lows reaching < 54 0.35 / 0.34 (0.37), night unentered rises 0.51 /
       0.57 (0.67), lows 0.54/day either way, 27 matched each (28). **G7 default sd 5.0, τ 180** (the sensor-target
       optimum). G6 and Libre 3 stay at 0 until each is refitted against its own FDA table on these bodies.
     - **Other families on the same bodies** (sensor_fit, base / sd 5): G6 loss 23.65 / 27.59 (stays 0); Libre 3 20.23 /
       14.73 (**sd 5 adopted**). Both have drifted far from their fitted losses (G6 7.4, LESSONS 31): CGM-binned < 54
       MARD 31.4 (G6, FDA 13.8) and 26–30 (Libre 3, 14.2) — readings below 54 too often have true glucose higher, i.e.
       too many false lows on these faster-moving bodies. A full sensor refit per family against its FDA table is the
       next review item; it will remove CGM lows, so the lows gap may widen when it is done.
