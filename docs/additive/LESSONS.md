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
