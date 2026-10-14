# ice — lessons

Method lessons from building the ICE generator. Each one cost time; the run directories under
`runs/2026-10-09-ice-*` hold the scripts that measured them.

1. **Score a rollout only where the real data was usable.** Real ICE has ~14% excluded intervals
   (pod changes, disruptions, compression lows) that cut episodes short; a rollout has none. Scored
   unmasked, v1 looked like it made meals 0.8 h too long and 8 g-eq too large; masked like the real
   held-out weeks it is +0.23 h and −0.9 g-eq, at the floor. The same mixing made the mean-ICE bias
   look twice its size (real ICE over all intervals is 68.5 mg/dL/h, over clean ones 66.4). Mask the
   rollout with the real record's `clean` at the same CGM timestamps before any comparison
   (`rollout.py`, `rescore.py`).

2. **5-min ICE is positively autocorrelated (lag-1 ≈ +0.5 to +0.6), not negatively.** CGM readings
   are already smoothed by the sensor, so differencing does not produce the alternating noise
   signature a white-noise sensor would. Measure the noise structure; don't derive it.

3. **The BG input is what produces rescue eating.** Removing BG and insulin inputs costs only
   0.012 nats/step one step ahead, but in closed loop the response to BG < 70 collapses (91 vs a real
   114 mg/dL/h) and lows rise to replay levels (t<54 1.73% vs 0.08% with the inputs, 0.16% field).
   One-step likelihood does not measure what matters for lows.

4. **v1 is calibrated one step ahead** (predicted mean ICE 66.1 vs actual 65.1 on held-out weeks).
   Parallel scheduled sampling (fine-tuned from v1, p ≤ 0.5, 2 passes) did not help: the free-run
   ICE level drifted further up (+6.9 vs +3.9 mg/dL/h) and most statistics got worse.

5. **Meal phases: test against a same-clock null.** A peak detector on smoothed excess ICE finds
   2+ "phases" in 66% of no-meal windows at low prominence. Calibrated so the null shows 11%, 22–26%
   of isolated announced meals show a second rise — real, in a minority, not size-dependent.

6. **The frozen-ICE replay over-produces lows under stock Loop** (t<54 1.24% vs field 0.16%, 24
   pilot donors), and runs ~9 mg/dL above the field on mean BG with real ICE — so about half of the
   generator's closed-loop mean-BG gap is the controller not matching each donor's deployed config.

7. **Check what `simulate --data-dir` already loads before calling a setting missing.** It reads
   `decision_times.csv` (the field's decision cadence, no-dose-guard cycles, and the per-cycle
   dosing strategy `mode`) and `disruptions.csv` (outage clamps) on its own. Only the
   retrospective-correction mode (std / IRC / IRC+clamp) and the application factor / GBAF have
   to be recovered and passed. I told Pete 10 of 24 rollout donors ran under the wrong strategy;
   they hadn't (`SimulateCommand.swift`, data-dir defaults).

8. **Mask with `zeros_like`, never `0 * y`.** A masked-out NaN target turned into `0 * NaN = NaN`
   inside `torch.where`; the excluded positions dropped out of the loss value but not out of the
   gradients, and the first v2 run was NaN from iteration 250 for 20 minutes. Training now stops
   on the first non-finite loss.

9. **A long-window ICE total is a habit signal, not satiety.** The v2 running budget (excess ICE
   over 1/3/6/24 h) was meant to say "absorbed a lot, less to come". In the data a high 24-h total
   marks a heavy-eating day, and heavy days come in runs, so the model learned the opposite: open
   loop at BG 120, i012's generated ICE drifted to 90-125 mg/dL/h (real 71) with the 24-h total
   at 400-535 g-eq; closed loop, 23-25 of 72 runs ran away. Held at the person's median BG with
   the budget frozen, the same model stayed near real levels.
10. **High BG reads as "meal under way" for some people.** With insulin inputs gone, BG is the
    remaining proxy: i005's generated ICE climbs over 48 h when BG is held at 350-400 (mean 72 ->
    107, p95 287 -> 496); i001 and i012 do not. Judge every variant with a held-BG probe
    (`probe_v2.py`) before the closed loop.
11. **Feed the plant's generator what training fed it, or its outputs shift.** The v3 plant fed
    back the predictive mean as the last background ICE — smoother than any training input — and
    with real inputs everywhere else that alone moved meal durations 1.9 -> 2.5 h and cut the
    meal rate (`runs/2026-10-10-ice-noise/feedback_check.py`). v3b feeds a causal 30-min EMA in
    both places; every ICE statistic then fell below the different-person ceiling.
12. **A recurrent state run past its training window drifts.** Trained on 48-h windows, run for
    29 days in the plant: teacher-forced on real data with one continuous state the meal rate is
    0.80-0.86 of labeled, with fresh 48-h windows 0.93-0.98 (`mealrate.py`). Score calibration
    the way the plant runs, and re-warm the state (`plant_v3 --rewarm-h`).
13. **Sample an event's attributes jointly.** v3 drew pulse size and logged grams independently
    given the state; entries came out unrelated to their meal (within-donor corr 0.11 vs real
    0.29) and over-logged meals drove lows (30% followed by a low within 4 h vs real 16%). v3j's
    staged heads: corr 0.24, lows after meals 25%.
14. **Two interleaved CGMs hide from a cadence-masked detector.** i171 interleaves two sensors
    ~40 mg/dL apart every 1.6 / 3.4 min for 26% of its record; `alternating` masked increments
    by the 5-min cadence and flagged none of it. Ten pilot donors carry >2% sawtooth; little of
    it reached `clean` (max 2.7%). It also passes for "compression" in a dip scan — screen it out
    before looking for sensor artifacts.
15. **A pooled rate can hide a per-person trait.** Fast no-carb V-dips show no overnight excess
    in the pool, yet 14 of 206 donors have one at p < 0.001 (0.2 expected by chance).
16. **Score closed-loop rollouts on clean time only.** The replay plant replays measured ICE on every
    interval, including excluded ones (a stretch pinned at the 401 HIGH ceiling has zero velocity, so its
    ICE omits the hidden rise; Loop doses into "401" and the plant credits all of it). Stretches with
    >= 50% excluded ICE plus the 4.5 h after them are 42% of replay time but held 83% of its time below
    54 (5.5% vs 0.83% elsewhere; one i056 episode sat at the 20 mg/dL floor for 60 h). On the remaining
    time the replay's excess over the field halves (t54 0.53 vs 0.12) and the generator's excess over the
    replay becomes the larger gap (1.70 vs 0.53) — `runs/2026-10-10-replay-lows/rescore_clean.py`.
17. **A start head's calibration is a training-run accident: calibrate it.** Fed real held-out
    inputs, the meal-start hazard's expected count ranged 3.3-5.7/day against a real 6.2 across nine
    trainings, under in-sample too. Comparisons between versions mostly compared that. One logit
    offset per start head, fitted on the 28 days before the hold-out (`calibrate.py`), brings v3g
    to 5.97 vs 6.21 held-out. Closed-loop rates still drift (calibrated v3g starts 7.5/day in its own
    rollouts vs 6.3 real, the excess at glucose > 120), so judge a change across replicate trainings.
18. **Insulin and state weighting did not buy the turnaround.** An insulin-aware projection input
    (v3h) and the low-state weight on background ICE (v3i) both left the push back up after
    entering 70-90 unchanged (48 vs 68 mg/dL/h real). Fed real inputs the model already expects the
    real background there (37.7 vs 39.9); the shortfall builds up in its own rollouts.
19. **Day-to-day variation is large, persistent and unexplained by the record.** Within a person the
    daily background level has sd ~11 mg/dL/h (between-person 11.4), covariance of daily means 58 at
    1 day and ~8 at 2 weeks. Site age, prior-day lows and highs and weekends explain ~1%. Generated
    days were independent. It must be generated (`slow.py`), not learned from inputs.
20. **Integrating across a CGM gap is not a replay.** Lesson 16's "i056 at the 20 mg/dL floor for
    60 h" was a 77 h no-CGM gap integrated in one plant step. Gaps over 2 h now re-anchor to the field
    in both plants; the generator's runaway runs went from 3 of 72 to 0.
21. **Measured-ICE replay is more variable than the field.** Clean-time replay glucose sd 58 vs field
    49 (median donor); the gap reverts within 3-6 h and is not the plant-vs-schedule ISF mismatch
    (rank corr -0.07). Hand-off to simulator: `runs/2026-10-10-replay-lows/HANDOFF.md`.
22. **Don't feed a generated persistent state back into the generator's own memory.** The slow level
    added to ICE *and* to the generator's background input came out ~6x too large (daily variance 611
    vs 174): the generator read the shifted day as its own persistent state and generated more of it.
    Kept out of that input, the day-level spread and persistence match (true-day sd 11.5 vs 11.5).
23. **Calibrate the start heads in closed loop, not only fed real inputs.** Calibrated teacher-forced
    (5.97 vs 6.21 meals/day), v3g still started 8.0/day in its own rollouts against 6.5 real, too many
    at every glucose level from 70 to 250. A second offset fitted on rollouts of the 28 days before
    the hold-out (`calibrate_closed.py`, log rate ratio) brings every band to the real rate (6.4 vs 6.5)
    and moves clean TIR 56.6 -> 62.9, mean 176 -> 165, t<54 unchanged (1.23 -> 1.28).
24. **Test the plant against the engine on a bed where the engine matches the field.** On the
    simulator's corrected bddp11 export the built-in counterfactual reproduced the field (27 vs 26
    crossings below 54) while the ice replay plant gave 34, and failed identity (51% of steps within
    5 mg/dL with the field's exact doses). Three causes, none visible on the pilot alone: the engine
    sent an external plant no doses that started in skipped cycles (fixed upstream, 60159cf); the
    plant re-anchored to the reading before t at every outage (a one-reading offset, median 5 mg/dL,
    carried to the next outage); and it carried the last ICE over missing-ICE steps. Fixed: identity
    93.8% within 1 mg/dL, replay 24 crossings, 96.5% within 5. Every earlier replay number on the pilot
    predates these fixes, including lesson 16's and lesson 21's.
25. **A pulse pump re-temped every cycle delivers less than it was told, and the engine knows.** Omnipod
    temps record a whole number of 0.05 U pulses, about floor(rate x actual duration / 0.05): a temp
    superseded after 5 min loses its fractional pulse (i040 delivered 388 of 566 U nominal, -31%). The
    engine's PumpModel.BasalAccumulator already truncates the same way; its trace reported the candidate's
    COMMANDS (rate x time), which made every replay-vs-field insulin comparison read high (i040 "+54%
    basal" was -0.5%; fixed upstream, 5345161). Compare insulin from what the plant received, never the
    trace's candidate delivery. i040's excess lows stand, with the same insulin: a timing / controller-
    fidelity question.
26. **Some donors run a Loop build with a non-stock insulin curve; it is a controller setting, not
    physiology.** The recorded bgForecast's length gives it away: stock curves give 370-395 min, a custom
    3 h curve about 190 (screen of all 207 pilot donors by month: `runs/2026-10-11-ice-isf/forecast_length.py`).
    i009 runs a 180 / peak-80 curve throughout; with it the simulator's forecast match went 27 -> 2 mg/dL
    and its replay from TIR 60 to 75.5 (field 77). i017 switched mid-hold-out (2026-09-24). About a dozen
    pilot donors show a non-stock length, six at a steady ~190 min. Pass the curve to the CONTROLLER
    only (`--controller-insulin-model custom`); ICE and the plant keep the insulin's own model, because the
    person's absorption did not change when they edited Loop's. Screen forecast length before trusting any
    donor's replay; a run-wide flag cannot follow a mid-window switch, so score only the stock part.
27. **A compression low is a break from the trend and a return to it, and the sensor often withholds
    readings at the bottom.** The old V-shape flag (< 70, 2 mg/dL/min down and up) caught 0.15% of time with
    no night excess and missed most artifacts. What works (`ice_gen/sensor.py`, tuned with Pete on random
    review sheets): a slide below a near-flat prior trend, then a return to that level and trend with no
    overshoot, the window grown over the slide in and the release. Three branches: readings resume after a
    GAP (the commonest form, 536 of 741 pilot events: the sensor algorithm flags the data), the reading pins
    at the LOW FLOOR, or neither (ICE well below its background, sharp return). A mirror control (sudden
    rises that return, which physiology rarely makes) measures precision: about 0.75 for the gap branch at a
    40 mg/dL slide. Rejected along the way: slides from a trend already falling (real lows), windows over
    45 min. Result: 0.03 events per person-day (the same as the drop-minus-rise excess), mostly overnight,
    a median donor about one in six weeks and the most prone about weekly. It holds only 0.7% of time below
    54. Fingersticks are too few to validate (47 at CGM < 70, 40 of them read >= 70, mostly CGM low-range
    lag around treated lows, not compression).
28. **The yardstick ISF does not beat the TDD rule in closed loop.** ICE rebuilt with the per-person
    yardstick ISF (median 1.15 × the TDD rule, p10 0.77, p90 1.73), three trainings each, scored on
    held-out clean time: TIR 62.7 / 60.1 / 62.1 against the rule's 62.9 / 61.7 / 59.2, time below 54
    1.69 / 2.33 / 1.60 against 1.28 / 1.41 / 1.66. TIR is level; lows lean worse but within the spread of
    trainings. The rule stays. (The two sets were replayed on harnesses C and D, so their replay rows
    differ; the model rows are what compare.)
29. **The generator under-produces each person's push back from a low, but correcting that near the low
    barely moves closed-loop lows.** v23 big fit, 3 trainings: field 74.2 TIR / 0.12 t<54, replay
    74.4 / 0.17, generator 59.2–63.7 / 1.27–2.21 (clean, median donor). What matches the field: meal
    starts per day (6.2 vs 6.4) and announced share (0.45 vs 0.43); snack starts per hour heading low
    or below 70; the rebound's size in the hour after crossing 70 (7–11 g-eq); short-lag BG structure
    (5-min rms 7.2 vs 7.3); inputs at entry into 70–90 (trend, background EMA, IOB). What does not:
    generated lows last 50 min against the field's 20, and from the same trend into 70–90 they go below
    70 in 43% of cases against 29%. Fed the real history up to a field entry, the network's next-30-min
    background is 36 mg/dL/h against the real 42 (34% vs 25% going below 70 in its free run), so the
    error is in the network's response itself, not built up in rollouts. It is a person trait: the
    near-low bias fitted on the 28 days before the hold-out predicts the held-out bias at r = 0.80–0.84
    (162 donors), between-person sd ~10 mg/dL/h, while the pooled bias changes sign across trainings
    (+3.6 / −2.9 / +1.1). A per-person offset in that state (split-half shrinkage, `calibrate_state.py`)
    halves the held-out error (median 6–8 to ~4) but in closed loop moves t<54 only −0.35 / +0.16 /
    −0.11 and TIR +0.3 / −0.3 / +0.15 (paired, by training): not beyond training noise, not kept.
    Generated lows mostly come from slow drifts that spend little time in the heading-low state, so a
    correction gated on that state rarely fires. Also measured: the slow day-level state costs 2.4 TIR
    (mean +4.7) and no lows. Same-step means by BG band mislead here: field readings below 70 sit mostly
    at the turnaround, generated ones deep in long lows (`runs/2026-10-11-ice-entries/`).
30. **Fit a state calibration from the generator's own runs, not from real inputs; and the snack rate by
    state is not what keeps generated lows long.** Excess generated time below 70 is all in long episodes
    (v3v23s0cc, min/day below 70 in episodes of > 30 min: field 11.9, model 54.8). The meal-start head is
    flat in glucose trend. Fed real inputs it starts 0.71–0.73× the labeled rate falling 1–2 mg/dL/min
    at 70–110 and 1.3–1.5× rising (`runs/2026-10-12-ice-lows/start_tf.py`). In its own rollouts the
    gap is about 2× (80–90 falling 1–2: 0.59 against 1.07 starts per hour). A per-cell offset (band
    × 15-min trend) fitted teacher-forced (`calibrate_meal_state.py`) flattens the teacher-forced
    ratios to 1.14–1.27, but the rollouts barely move (0.59 → 0.65), nor do the outcomes (TIR −0.6 /
    +0.3, t<54 +0.13 / −0.12, s0 / s1). The same table fitted from rollouts on the 28 days before the
    hold-out (`calibrate_closed_state.py`, as `calibrate_closed.py` does for the overall rate) does
    fix the structure on held-out weeks (90–110 falling 1–2: 0.53 → 0.71 against 0.84; rising
    0.23 → 0.15 against 0.11). Long lows still barely drop: 68 → 63 and 73 → 66 min/day, against 23 in
    the field. Outcomes do not move beyond training noise: TIR −0.7 / −1.1, t<70 −0.31 / −0.08,
    t<54 0.00 / −0.29, mean +2.9 / −0.3. One donor, i003, carries a third of the excess on the v23
    harness (GBAF unmodeled: model 236 min/day in long lows, replay 31, field 4), but 18 of 24 donors
    have > 10 min/day of excess. Inside a low the field's ICE climbs to 61 / 84 mg/dL/h at 10–20 / 20–30
    min against the generator's 48 / 62, then the two run level. The generator's snacks in a low are as
    large as the field's (33 vs 35 g) but peak later. The same holds in every band, 15–30%, in its own
    runs only (`peak_state.py`).
31. **Snack speed is not it either: generated lows are long before a snack could act.** A per-band shift
    on the sampled log time-to-peak, fitted from the pre-hold-out rollouts (`calibrate_closed_peak.py`;
    below 70 −0.29 / −0.34, 70–90 −0.20 / −0.23, above 110 −0.15 / −0.16), on top of lesson 30's
    table: held-out peaks now match in every band (below 70: 28.7 / 30.5 min against 30.0). Long lows
    (> 30 min) 49 → 48 and 56 → 61 min/day, against 12 in the field. Outcomes, cc → ccsp, s0 / s1:
    TIR −2.8 / −0.2, t<54 −0.21 / −0.20, mean +4.0 / +0.5. The share of episodes still below 70 at
    15 min is unchanged: 0.65 against the field's 0.46. Generated episodes are also too frequent
    (1.2–1.5 per day against 0.78). The remaining gap is in background ICE and how often the generator
    enters a low at all, not in the pulses. Both calibrations make the structure checklist match, so
    they go into the v28 pipeline and are judged there over three trainings.
32. **A smoothed slope of background ICE adds almost nothing to the meal-start head.** Teacher-forced,
    v3v28s0cc, ~200 donors: a logistic on the head's own logit plus the slope of the real background
    ICE (15-min minus 60-min causal EMA), known 0 / 10 / 15 min before the step, fitted on the 28 days
    before the hold-out. Held-out gain is +0.007 / +0.007 / +0.011 nats per start (+0.005 / +0.013 /
    +0.012 below 100 mg/dL). Where it says anything, the sign is the reverse of "the turn is the
    intervention starting": below 100, the steepest-rising fifth of steps has 0.5–0.65× the starts the
    head expects. Once background ICE has turned up, the push back from a low is already under way
    inside the background (counter-regulation, unlabeled rescues), and no labeled meal follows. The
    turn is the behavior to generate, not a cue to feed in (`runs/2026-10-12-ice-slope/`). Aside: the
    head's logit gets weight 1.36–1.45 in that fit, so the head is under-confident fed real inputs,
    which fits its flatness in glucose trend (lesson 30).
33. **A background-ICE offset by glucose band fixes most of the excess lows, but only below 90.** Background
    ICE in the generator's own runs sits too low in lows (60–70 mg/dL: 41 against the field's 54 mg/dL/h;
    below 60: 45 against 61), and teacher-forced it is nearly right, so the gap only opens in closed loop.
    `calibrate_closed_bg.py` fits, from the pre-hold-out rollouts, an additive offset per band of the input
    step's glucose: the median over donors of field minus generated background ICE, which the plant adds
    before its EMA feedback. Over every band (ccb) it overshoots: t<54 2.08 / 2.59 → 0.58 / 0.63, but mean
    glucose 166 → 224 / 206 and TIR −13, because the offsets above 90 feed back on themselves in highs.
    Kept below 90 only (ccbl: below 60 +24 / +23, 60–70 +11 / +17, 70–80 +9 / +10, 80–90 +6 / +10;
    0 above), v23 cc → ccbl, s0 / s1, model runs, per-donor means over 24 held-out donors: t<54 2.08 / 2.59
    → 0.77 / 0.92 (field 0.18), t<70 4.65 / 5.32 → 2.42 / 2.42 (1.23), TIR +1.8 / +2.8, mean +2.2 / +2.4,
    insulin +0.4 U/d. No donor loses more than 1 TIR point. Worst donor 10.5 / 7.9 → 3.0 / 2.9. Kept; it
    goes into the pipeline after lesson 30–31's calibrations, fitted on their rollouts. On v28 those two
    calibrations, judged the same way over three trainings, give t<54 −0.32 / −0.43 / −0.35 and t<70
    −0.54 / −0.73 / −0.50, with TIR −1.2 / −0.5 / −0.6 and mean +2.8 / +1.7 / +1.7: a consistent win on
    lows at a TIR cost about the size of training noise. (Score from the `model` arm only: the scores
    file also holds a `replay` row per donor, and averaging it in shrinks every generator gap by a quarter.)
    Confirmed on v28 over three trainings, v30 harness, ccsp → ccspbl (offsets refitted on each training's
    ccsp runs): t<54 2.63 / 2.15 / 1.77 → 0.71 / 0.78 / 0.87, t<70 5.24 / 4.54 / 3.98 → 1.91 / 2.08 / 2.07,
    TIR +2.9 / +2.0 / +1.7, mean +3.1 / +2.3 / +1.9; no donor loses more than 1.8 TIR points; worst donor
    3.9 / 2.9 / 3.3% below 54. Now the last step of the calibration pipeline.
34. **How early a person reacts to a falling glucose is a strong personal trait; the model flattens it.** Per donor,
    on the days before the hold-out, background ICE above the person's own steady 100–180 level and the
    meal-start rate, in three states of the input step (`runs/2026-10-12-ice-lowtrait/trait.py`, v3v28s0,
    168 donors). Proactive (70–100 and falling ≥ 1 mg/dL/min or heading low): push p10–p90 −13 to +18
    mg/dL/h, snack starts 0.44–0.93 per hour, alternate-week reliability 0.76 / 0.65, the most stable trait
    measured so far. Severe (< 60): push median +39 (p10–p90 8 to 67), reliability 0.50; snack starts
    0.5 per hour with no person-to-person reliability (−0.01): below 60 everyone eats at about the same
    rate, and the person shows in how early they act. Teacher-forced, the model's per-person values track
    the field only loosely in the proactive state (Spearman 0.40 push, 0.35 snack), with the spread
    squeezed (push −12 to +6, snacks 0.37–0.66), and its severe push is half the field's (19 vs 39).
    So the one-table background offset (lesson 33) gives every person the median's push: too much for
    the passive, too little for the proactive. The fix goes per person.
35. **A per-person background offset near lows does not beat the shared table.** `calibrate_closed_bg_person.py`
    (cells = band × {steady, falling or heading low}, 60–90 per person shrunk toward the population by
    n / (n + 100), below 60 shared; fitted on each training's pre-hold-out runs; the plant hook is not kept),
    v28 × 3 trainings, v30 harness, against the shared below-90 table: t<54 0.74 / 0.75 / 0.86 vs 0.71 /
    0.78 / 0.87, TIR within 0.2, and per person no closer to the field (median |t<70 gap| 0.99 / 0.92 /
    0.84 vs 0.76 / 0.86 / 0.81; rank correlation with the field's t<70 0.49 / 0.60 / 0.48 vs 0.52 / 0.67 /
    0.42). Per-person offsets ranged +3 to +28 at 70–90, yet the people's outcomes did not move with them:
    28 days of a person's own runs is too little to fit a personal offset that beats the median, and the
    offsets partly patch an under-trained model (lesson 36). The trait goes into the model instead.
36. **The pilot model was under-trained; 9000 batches is the length, and width does not help.** Same v28
    data and v3k recipe on the 4090, three seeds per arm, judged teacher-forced by background ICE per glucose
    band on the held-out month (`runs/2026-10-12-ice-capacity/`, `tf_band.py`; model minus field, median
    donor, mg/dL/h) and held-out NLL. 256 wide / 3000 batches (the pipeline's model): NLL 0.754–0.781, below
    60 −14, 70–90 −2 to −4. 512 / 3000: NLL 0.711–0.735, low bands still short. 256 / 9000: NLL 0.678–0.687,
    below 60 −6 to −7, 60–90 within ±2 except one seed at +5 (60–70), no band above 90 off by more than 2.
    256 / 27000: NLL 0.755 / 0.764 / 0.780, below 60 −8 to −13, and the training-day fit no better either
    (batch NLL over the last 3000 batches 0.72 vs 0.73 at 9000). The one-cycle schedule stretched to
    27000 batches spends far longer at its peak rate; why that loses held-out skill is not measured.
    512 / 9000: NLL 0.674–0.690, same as 256 / 9000, but two of three seeds run +3 to +7 high in every band
    above 90. So the shrinkage of the low tails (lesson 33's "missing push") was mostly under-training:
    the pipeline moves to 256 / 9000 and the calibrations are refitted to see how much is left for them.
    In closed loop it is not yet a win (`runs/2026-10-12-ice-i9k/`, full chain refitted per training, v30 harness,
    held-out, model arm, i010 and i012 left out of both arms): 3000 → 9000 batches gives t<54 0.70 / 0.85 / 0.89
    → 0.54 / 0.51 / 0.50 and t<70 1.95–2.26 → 1.57–1.68 (field 0.18 / 1.29), but TIR 66.2 / 65.0 / 67.1 → 63.5 /
    62.4 / 64.0 and mean +6 (field 72.6 / 152), and one training runs away (mean glucose in the thousands) on i012
    in every seed and on i010 once. The below-90 offset barely shrinks (below 60 about +21 to +25 at both lengths):
    the low push is still missing in the generator's own runs, not when it is fed real history.
37. **Feeding sensor-limit steps as training saw them makes runaways worse.** The 9000-batch training s1 runs away on
    i012 (glucose in the thousands for days): above 400 the CGM pins at the ceiling, extract.py flags those steps
    `clamp` and leaves their background ICE out of training, so the model never learned the state, and the plant fed
    its own +150 to +300 mg/dL/h draws back through the EMA while the controller sat at its delivery limit. A plant
    option fed limit steps as the data has them (`bgice_ok` 0, EMA held; `runs/2026-10-13-ice-clamp/`, six full-chain
    models, held-out): runaway runs (mean > 400) 0 / 0 / 0 / 0 / 4 / 0 → 0 / 0 / 1 / 2 / 7 / 7 (3000-batch s0–s2, then
    9000-batch s0–s2), mean glucose up 2–13 mg/dL on the 3000-batch models, TIR −0.4 to −0.5. Holding the EMA keeps the
    high level it had on the way up, and "ICE missing" with a high EMA is a combination the model saw rarely; the fix
    is not in how limit steps are fed. Not kept. About 30% of runs from every model spend over 2 h above 400 (field:
    a median donor 0.3 h a month at the ceiling); only some models fail to come back.
38. **Delivering a meal's calculator bolus no earlier than its carb entry lowers the mean but adds lows; not kept.**
    The plant drew a meal's carb-entry delay and its bolus delay independently, and a calculator bolus enacted before its
    own carb entry is visible to the controller delivers about nothing, so some generated meals went unbolused.
    `--couple-meal-bolus` delays a ratio bolus to its entry. With every closed-loop calibration refitted per arm on the v31
    harness (`runs/2026-10-13-ice-highs/chain_v31.sh`, three 3000-batch trainings, held-out, clean time; field 74.2 / 0.85
    / 0.12 / 152): TIR 63.7 / 64.3 / 65.9 → 64.2 / 64.3 / 67.2, mean −2.5 / −2.8 / −1.0 mg/dL, but t<54 0.37 / 0.43 / 0.72
    → 0.43 / 0.60 / 0.84 and t<70 up on two of three. The v30 A/B without refitting read the same. The extra meal insulin
    lands on a generator that already makes three times the field's severe lows, so the change waits until that is fixed;
    the ten-point TIR gap is not bolus timing (it moves TIR under a point) but behavior rates (next lesson's target: every
    person's announced meals, meal boluses and corrections are generated near the population middle).
    Harness v30 → v31 (disruptions deliver the field pump's insulin, b70ba36) moves the generator's outcomes by under
    0.2 TIR and 0.01 t<54; refitting the calibrations on v31 moves them by under 0.3 TIR. Replay insulin is 0.8% above the
    field (was 1.5%) on the shared clean CGM steps.
39. **Per-person behavior rates, fitted closed-loop, put each person's eating and correcting back where it was; kept.**
    The model ranks people roughly right but generates every person's rates near the population middle (corrections never
    below about 0.5 a day, on donors whose labels show 0.04). `calibrate_closed_rates_person.py` fits per-person logit
    offsets on the meal-start, announcement, meal-bolus and correction heads from the person's own 28 training days
    (WIN=train rollouts), shrunk toward no change by 7 days / 10 meals of prior (`runs/2026-10-13-ice-rates/`, v31 m-arm
    of three 3000-batch trainings, held-out; `rates_score.py`: per donor, generated vs labeled per day). Spearman over
    donors, before → after: meals 0.26–0.46 → 0.75–0.81, corrections 0.56–0.58 → 0.76–0.79, announced 0.81–0.90 →
    0.87–0.90, bolused meals 0.67–0.71 → 0.74–0.77; median miss (|log2| ratio) meals 0.20–0.27 → 0.11–0.12, corrections
    0.62–0.70 → 0.42–0.46, bolused meals unchanged. Outcomes on clean time move within training noise: TIR −0.5 / +1.2 /
    +1.2, t<54 +0.01 / +0.06 / 0.00, runaway runs 1 / 3 / 1 → 0 / 3 / 1. A second pass refitted on the calibrated model's
    own rollouts adds nothing (the rates do not feed back much through state), so one pass is the recipe. What is left:
    the top announcers still come out near 4 a day against 6 in the labels, and the worst misses are people whose rate
    changed between the training and held-out months (i010: 0.11 corrections a day in training, 1.43 held out), which
    a person's own history cannot predict.
40. **Settings edits are natural experiments only once the shift in need that prompted them is separated out.**
    Tier 3(c) test (`runs/2026-10-13-ice-change/`): 70 pilot edits that moved day-average basal, ISF or CR by >= 10% or
    the target by >= 10 mg/dL and then held 14+ days; 55 scored (on model people, replay within 10 TIR of the field's
    level). Each 13-day window either side runs with the before and the after settings (the other side's dated
    segments shifted 14 days), replay arm and the three 3000-batch v31 models with per-person rates (3 seeds); predicted
    change = after minus before in the same window. Taken at face value both arms overstate every edit 1.6-2.8x and
    get ISF raises backwards (11 edits: field mean -2.8 mg/dL, predicted +8 to +10). But edits answer a change: the
    clean-ICE level shifts with them (ISF raised: median ICE -3%, insulin -3%; lowered: +8%, +7%; i192 ISF x1.87 with
    ICE -23%), and the shift correlates -0.32 with the predicted edit effect. Regressing the field change on both,
    the edit's coefficient is about right for TIR (replay 0.79, generator 0.90) and mean (0.60 / 0.74); on the half
    of edits whose need held steady, TIR error 6.0 (replay) / 5.8 (generator) against 7.1 for predicting no change,
    slopes 1.05 / 1.46. Severe lows are where both fail: the t<54 coefficient is 0.18 / 0.25, so a predicted change in
    t<54 is 4-5x what the field shows, in the replay as much as the generator. The generator does not track the
    person's own shift from real history (its post-after minus pre-before run: r 0.43, error 12.2 vs 11.2 for no
    change); outcomes otherwise rank with replay (r 0.81-0.93). So for change prediction the generator so far adds
    little beyond replay; the t<54 response is the gap to chase. Config: donors outside config.csv run standard RC.
41. **Entries and boluses as their own events: each structural step fixed one coupling and exposed the next.**
    `runs/2026-10-13-ice-v3m/`, 3 trainings x 3000 batches on ice_v30 (PC), full closed-loop chain on the v31 harness.
    v3 tied a pulse to one summed entry and bolus, so the heaviest hands-on users were squeezed (i050: field 11 entries
    and 13 boluses a day, generated 3.7 and 5.8) and against the field record v3k generated 0.6x the entries, 2x the
    corrections and a quarter of the meal-bolus insulin (1.65 vs 6.0 U/day). In order:
    - **v3m** (entry and bolus heads apart from the pulse head, trained per-person logit offsets): held-out NLL 0.68-0.69
      vs v3k's 0.75-0.78 at the same length, entries per day right teacher-forced; closed loop 25% of entries have no
      pulse within -60/+120 min (field 16%), t<54 3.05. The field's unmatched 16-19% are labeler misses: ICE still rises
      after them, about half a matched entry's (Pete: an announced meal is almost always followed by a pulse).
    - **v3m2** (+ grams entered since the last pulse began, as input): orphans 20%, t<54 1.5 at the open-loop stage.
    - **v3m3** (an entry that starts a meal draws its pulse: delay, size | grams, peak, duration; eating-first pulses stay
      on the meal head): orphans 3%, delays / sizes / peaks / grams all within the field's quartiles. But one bolus head
      averaged over all steps learned P(bolus | entry) 0.23-0.38 where the data has 0.67-0.76 (entries are ~1% of steps),
      so 29% of generated entries were bolused vs 87%.
    - **v3m4** (bolus split: P(bolus | entry) scored on entry steps, P(bolus | no entry) on the rest, each its own trait):
      entries bolused 61%; manual insulin now matches the field (with an entry 6.8 vs 6.0 U/day, alone 2.6 vs 2.2,
      lone boluses 2.1 vs 2.0 a day); background ICE by glucose band matches (below-90 offsets 3-5 vs v3k's 13-23).
      Held-out clean t<54 still 2.38 / 2.10 (two trainings), TIR 62.4, mean 161-163. The lows sit 0-4 h after meal
      boluses (t<54 3.6-6.2% vs field 0.1%) and track the person's carb-entry ratio (Spearman 0.53): near-non-announcers
      get entries they never make (i012 212x, i056 59x, i010 11x), because the trained trait's prior (sd 1) cannot reach the
      logit offset of about -5 they need. Fixes under test: per-person closed-loop rates on top, and a prior of sd 3.
    Also found on the way: long field disruptions are Loop running with CGM and no pump (99.7-100% of cycles pump data too
    old; simulator handoff 2026-10-13-ice-pumpless-disruptions): the person dosed with a device Tidepool does not see, so
    insulin there is unknown. The extract fills them with scheduled basal (Loop's net IOB sits at 0: its assumption, not a
    measurement), the harness delivers nothing (41 pilot donors, 32,773 h; i061 262 U in its last 56 days), and generated
    glucose ran into the thousands and into every closed-loop calibration. The plant now follows the field through
    disrupted steps, and v3m4wp masks bolus targets on those runs (dataset_v3.pumpless_slots), which otherwise taught the
    behavior traits "this person does not bolus".
42. **The generator widens its own background ICE in closed loop: exposure bias through every own-ICE input.** Fed its own
    closed-loop inputs, the background-ICE head predicts a 30-65% wider spread than fed real history (median sd, v3m4:
    i001 52 vs 40, i005 103 vs 65, i022 89 vs 54; v3k smaller, 54-72 vs 53-61), so generated glucose is 1.3-2.3x rougher
    than real CGM at 5 min, crosses 70 twice as often and goes deeper. Tests (`runs/2026-10-13-ice-v3m/`, `swap_test.py`,
    `input_review.py`, plant input dump PLANT_XLOG): moving one input onto its closed-loop distribution in a real stretch,
    only the 15-min CGM trend matters (+13.8 mg/dL/h for v3m4, +5.6 for v3k; every other input < 3); meal activity and
    glucose level change nothing. A v3m5 with background ICE on its own path without the trend inputs still widened
    (60 / 84 / 75 vs 35 / 65 / 38); restoring the real 30-min background-ICE average into closed-loop inputs removed it all
    (34 / 64 / 38). Each input built from the person's own recent background ICE (trend, the EMA, the glucose sequence)
    carries the model's own near-independent draws back in generation but only real, smooth ICE in training; the model
    reads its draws as a volatile state. Removing one channel moves the loop to the next. Real hour-scale volatility
    structure is matched (persistence 0.43 vs 0.44 / 0.39, recovery after a top-10% hour alike); the fault is minutes.
    Measured with a plant factor shrinking each draw toward the predicted mean (BGICE_SPREAD, a gauge, not kept): at
    0.7 the v3k models' TIR 62 -> 66-70, t<54 0.49-0.83 -> 0.05-0.32, mean still 161-168 (field 74.2 / 0.12 / 152): about
    half the TIR gap and all the excess lows, and the low calibrations then overshoot (they were patching this).
    Correlated draws (an AR(1) quantile, BGICE_RHO) made it worse (lows x2-5): persistent errors integrate further.
    Fix to build: train the background-ICE path on its own draws (scheduled sampling), so training sees what
    generation feeds it.
43. **Training the background-ICE path on its own draws (scheduled sampling) weakens the loop but fixes nothing; not kept.**
    `runs/2026-10-14-ice-freerun/`, ice_v32, v3m4 recipe (wide trait prior, pumpless mask), 3 seeds each, held-out at the
    open-loop stage, swap test on the logged closed-loop inputs (`swap_v32.py`). FREERUN=0.5 (`freerun.py`): up to half the
    batches also run day 2 of the window on the model's own background-ICE draws (glucose = real + the running draw-minus-
    real difference, derived inputs rebuilt as the plant builds them) and score the real next value. Closed-loop / real
    predicted spread 1.41 / 1.39 / 1.28 (baseline) -> 1.24 / 1.23 / 1.14, but mostly by predicting wider everywhere (real-
    input sd 64.8 -> 70.3 on seed 0); lag-1 autocorrelation of generated background ICE 0.30-0.32 -> 0.24-0.25 (field 0.48),
    glucose 5-min sd 15.4 / 14.6 / 14.6 -> 14.3 / 13.9 / 13.2 (field 8.3); TIR 57.9 / 57.0 / 56.6 -> 56.3 / 59.1 / 56.2,
    t<54 2.06 / 1.71 / 1.20 -> 1.67 / 2.14 / 2.20 (field 74.1 / 0.12). Scored against the real next value while its own
    history has drifted, the best the model can do is trust that history less, which flattens the dependence instead of
    making it right. Real 5-min smoothness has to come from conditioning on its own previous value through a channel that is
    the same in training and generation: next, the background ICE of the last slot as an explicit input (FEATURES_M2A),
    fed back as the draw in generation.
    Also: v3m4's explicit trait offsets stayed near 0 (sd 0.02 against the 1.0-1.4 logit spread of people's entry and lone-
    bolus rates), ranked right (Spearman 0.81-0.86) but carried by the profile vector, so rates came out compressed; under
    test: traits initialized at the person's shrunk observed rates (TRAIT_INIT, sd 0.3-1.0).
44. **Initializing each person's trait offsets at their own shrunk observed rates puts per-person behavior right in the model
    itself; kept.** ice_v32, v3m4 recipe, held-out at the open-loop stage, `actions_score.py` against the field record
    (`runs/2026-10-14-ice-freerun/`). TRAIT_INIT=1: each person's meal / entry / meal-bolus / lone-bolus logit offset starts
    at logit(own rate, shrunk by 20 events toward the pool) minus logit(pool rate), then trains as before. Per-person
    Spearman, baseline -> trait init (seeds 0, 1): carb entries 0.52 -> 0.96 / 0.93, boluses 0.62 -> 0.94 / 0.90,
    corrections 0.69 -> 0.92 / 0.89; median generated / field entries 0.92 -> 1.00 / 1.04; the near-non-announcer i012
    1.96 -> 0.44 / 0.55 entries a day (field 0). This replaces the post-hoc per-person rate calibration of LESSONS 39.
    Outcomes move within training noise (TIR 63.4 / 56.5 vs baseline 56.6-57.9, t<54 1.67 / 1.62 vs 1.20-2.06, mean 164 /
    177 vs 170-174): with behavior right, the remaining outcome gap is the closed-loop widening of LESSONS 42 (spread ratio
    1.28 / 1.39, unchanged).
45. **Background ICE given its own history through one exact channel (its previous value) and no indirect own-ICE inputs:
    the closed-loop widening is gone; kept.** v3m6 (`model_v3m.ICEGenV3M6`, FEATURES_M2A): background ICE on its own
    recurrent path that sees the previous background-ICE value (the real one in training, the plant's draw in generation,
    PLANT_FEEDBACK=sample) and drops the CGM trend, 30-min projection, heading-low, minutes below 70 and the 30-min EMA;
    behavior heads keep every input. ice_v32, kept recipe (LESSONS 44), held-out at the open-loop stage, seeds 0 / 1:
    closed-loop / real predicted spread 0.95 / 0.85 (trait-init arm 1.20-1.39); background-ICE lag-1 / lag-2 autocorrelation
    0.42 / 0.10 and 0.54 / 0.25 (field 0.48 / 0.19; before 0.31-0.34 / 0.04-0.05). Per-step glucose change on clean time,
    split by source (sd, mg/dL per 5 min, median donor, seed 0): background 6.6 vs 6.2, pulses 4.5 vs 4.0, insulin 3.5 vs
    2.8, total 7.8 vs 6.8. Two half-measures before it were not enough: the exact channel alongside the indirect ones (arm a:
    the model follows its last value as real data does, slope 0.38 vs 0.38, yet closed-loop ratio 1.19-1.25), and dropping
    the trend alone (v3m5: the loop moved to the EMA). Outcomes at the open-loop stage: TIR 62.7 / 61.3, t<54 1.96 / 2.01,
    mean 164 / 167 (field 74.1 / 0.12 / 152): the excess lows are not the loop and not a missing push near lows (background
    ICE below 60: real 51, fed real history 51, generated 64); generated people spend 6.6x the field's time below 60.
46. **Two closed-loop level faults behind v3m6's remaining gap: shared random streams, and each person's background level
    drifting through the exact channel.** (a) The plant seeded every random stream from the rollout seed alone, so all donors
    on a seed shared one slow-level path and one stream of uniforms for their event draws: the slow level averaged +2.55
    mg/dL/h over 72 runs (standard error 0.26) and every generated person moved together. Seeding from seed and donor
    (plant_v3, default on): slow level -1.07 (sd 4.2 across runs); v3m6 seeds 0 / 1 TIR 62.7 / 61.3 -> 62.8 / 64.2, mean
    164 / 167 -> 163 / 161, t<54 1.96 / 2.01 -> 1.89 / 1.87 (field 74.1 / 152 / 0.12). Every earlier pooled result had 3
    shared paths per arm, not 72 independent ones. (b) Between meals generated background ICE (slow level removed) runs
    +6-9 mg/dL/h above real from 2 h after a meal on, while fed real history the model is within +2 at every interval; so
    people arrive at meals ~20 mg/dL high (165 vs 144), Loop adds automatic insulin (2.85 vs 2.51 U in the 3 h after a meal
    bolus, 27.9 vs 23.9 U/day), and the tail stacks into lows 2-4 h after meals (t<54 5.5% vs 0.06%). Reverse swap: putting
    back the real glucose level or real meal activity changes nothing; putting back the real previous background ICE
    returns the predicted mean to its real-input value for every donor (i008 47.5 -> 32.5, real 31.5; i005 42.0 -> 53.1,
    real 54.1). It is not a one-way bias: each generated person's level wanders off theirs and holds for the month (+16 to
    -12), because the model follows its own last value and was only ever shown real ones, so it never learned to pull back.
    Under test: scheduled sampling on the single exact channel (arm h).
