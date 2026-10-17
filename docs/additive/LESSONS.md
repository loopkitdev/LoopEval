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
