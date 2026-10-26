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
47. **Scheduled sampling on the single exact channel trades the 5-min structure for the day level; not kept. One channel
    cannot carry both timescales.** Arm h = v3m6 + FREERUN 0.5 with the model's own previous draw in the exact channel
    (`runs/2026-10-14-ice-freerun/`, 3 seeds, per-donor random streams, held-out open-loop stage), against v3m6 seeds 0 / 1:
    day-to-day sd of the daily background level 23.5 / 18.8 -> 16.0 / 20.1 / 15.8 (field 11.1); TIR 62.8 / 64.2 -> 63.4 /
    65.4 / 66.0, mean 163 / 161 -> 162 / 156 / 160, t<54 1.89 / 1.87 -> 1.49 / 2.31 / 1.92 (field 74.1 / 152 / 0.12, all
    within training noise); but background-ICE lag-1 autocorrelation 0.42 / 0.54 -> 0.13-0.14 (field 0.48) and closed-loop /
    real predicted spread 0.95 / 0.85 -> 1.19-1.32. Taught to pull back from its own drift, it leans on its last value less,
    and the minutes structure goes. Next: an exact channel per timescale (last value; own 6-h and 24-h background means), so
    the day-level pull-back is learned from real days (1-day persistence 0.39) without touching the 5-min one.
    Dial check on v3m6 (2 seeds, `runs/2026-10-14-ice-dials/`): announcement 1 / 0.5 / 0 moves entries 5.3 / 2.5 / 0 and meal
    boluses with them, eating within 4% (279-290 g-eq/day) and day spread unchanged; compression 1 / 0 / 3 moves sensor
    events 0.52 / 0 / 2.07 per 28 days and nothing else; slow-state 0 / 1 / 2 moves day spread 20.0 / 22.8 / 25.6 and
    nothing else, but most of the (excess) day spread is the model's own. No monthly-cycle dial yet.
48. **Any input built from the person's own recent background ICE lets the generated level drift, even an exact one; the drift
    is in the model's own dynamics, not the closed loop.** Run open loop for 7 days on its own background-ICE draws with every
    other input real (glucose, meals, actions; no controller, `openloop_days.py`, 8 donors): v3m6 day-to-day sd of the daily
    level 20.2 and mean level 56.8 mg/dL/h against real 10.1 / 38.3; v3m7 (+ own 6-h and 24-h means, exact channels) 28.2 /
    76.9. Fed real history the same model predicts a mean level of 41.4 (i022); fed its own draws (wider and right-skewed:
    90th percentile 151 vs 116), the level it infers wanders day by day (25 -> 69 -> 68 -> 52 -> 70 -> 60 -> 50, real 20-51).
    Interpretation, not proven: the recurrent state estimates the person's current level from recent background ICE, and big
    positive draws read as "level up". Not kept: v3m7 (held-out TIR 64.9 / 64.7 / 65.3, t<54 1.35 / 1.57 / 2.11, day spread
    21.9 / 21.0 / 19.3, within noise of v3m6), and v3m7 + free-run scored on the day-level mean only (FR_MODE=level, weight
    30: day spread 25.8 / 23.0, t<54 2.80 / 3.61, worse). Next: background ICE from exogenous inputs and glucose level only
    (v3m8), step-to-step dependence from the plant's correlated draws fitted to real data, day level from the slow process:
    stationary by construction.
49. **Glucose history is an own-history channel too, but the lows need it; and the slow-level process now double-counts the
    day level.** v3m8 (background-ICE path from exogenous inputs plus glucose, no explicit own-history input; plant draws
    correlated by a fitted BGICE_RHO): the fitted normal-score lag-1 was only 0.07, because a recurrent net fed the glucose
    sequence recovers recent ICE by differencing it, and the closed-loop widening came back (spread ratio 1.55, t<54 4.75,
    seed 0). v3m9 (glucose out of the recurrent path, the current reading only at the output head): spread ratio 1.07, lag-1
    0.47 with the fitted draw correlation 0.40 (field 0.48), but t<54 6.16, TIR 53.8, lows lasting a median 80 min (field 35,
    v3m6 65); recovery from a low needs glucose history (how long it has been low, how fast it fell). Neither kept; v3m6
    stays. Day level, split (v3m9 seed 0, 12 donors, mg/dL/h day-to-day sd): generated total 20.7 = predicted mean on
    closed-loop inputs 9.9 + draws' deviation 10.7 + slow process 9.8; real total 12.3 = predicted mean (fed real history)
    5.8 + residual 10.5. The draws already carry the real residual day variation; the slow process, fitted when the model
    had none of its own, adds ~10 on top. Generated people's meals vary day to day as real ones do (CV 0.28 vs 0.30), and
    excluding glucose < 90 leaves the day spread unchanged, so neither behavior nor lows drive it. v3m9 run open loop with
    every input real: level 37.1 vs 38.3, day spread 6.8 (white draws, no slow process).
50. **Drop the slow-level process with the v3m6 generator; kept (harness setting).** The draws already carry the real residual
    day variation (LESSONS 49). v3m6 seeds 0 / 1 held-out, per-donor streams, slow process on -> off: TIR 62.8 / 64.2 -> 64.1 /
    65.6, t<54 1.89 / 1.87 -> 1.66 / 1.71, mean 163 / 161 -> 162 / 157, day-to-day sd of the daily background level about
    19-24 -> 18.4 / 18.9 (field 74.1 / 0.12 / 152 / 11.1). The remaining day excess is the predicted mean varying by day on
    closed-loop inputs (9.9 vs 5.8 real). Next: Pete's observation (2026-10-14) that ICE is the net of two larger streams that
    partly cancel, an outside stream that does not respond to glucose and a behavior stream that does; a model of the net
    cannot say how the cancellation shifts when the controller changes (the over-predicted edit effects of LESSONS 40 fit
    stronger real compensation). Two-stream generator: a latent outside stream with fitted persistence, generated rather than
    inferred from its own past, plus a memoryless reaction to observable state.
51. **The two-stream generator (v4) is not kept: the outside stream needs a slower component than one day-scale AR(1) can
    give.** v4 (exogenous level and scale from a recurrent net with no glucose or ICE input, a memoryless reaction to the
    observable glucose state, fast + slow latent AR(1), exact Kalman likelihood): seeds 0 / 1 held-out TIR 60.8 / 59.4, t<54
    2.22 / 2.64, day-to-day sd of the daily background level 19.5 / 19.7 (v3m6 64.1 / 65.6, 1.66 / 1.71, 18.4 / 18.9; field
    74.1 / 0.12 / 11.1). Fitted on 24-h windows the slow component cannot separate a day-to-day swing from a level offset
    between window and person (stationary sd 14.9 vs a real day-level residual of 12.1). Refitting its persistence over each
    donor's last 60 training days (networks frozen): a 5.6-h half-life, day spread 17.2, TIR 60.2, t<54 2.11, still not
    better than v3m6. Pooled real day variance against v4's predicted level: 6546 = predicted 1396 + residual 6192 + 2 cov
    -1042 (corr -0.18), a small cancellation, not the large one the two-stream idea expects at the day scale. Not pursued
    further until the shared outcome gap below is understood.
52. **Every variant shares one outcome gap (TIR 60-66 vs 74, t<54 1.5-2.6 vs 0.12, ~20% more insulin than the field); the
    plant's insulin response is not its cause.** PATIENT_INSULIN_GAIN (insulin away from the person's typical rate, TDD/24,
    acts at a gain) on v3m6 seed 0: gain 1 / 0.8 / 0.6 -> TIR 64.1 / 63.6 / 60.5, t<54 1.66 / 1.46 / 1.57, mean 162 / 164
    / 166, insulin unchanged (39.5-40.1 U/day). The overnight fasting slope of background ICE on ISF x insulin activity is
    +0.43 (163 donors), but closed-loop confounded, so not evidence of a gain below 1. What is too big is the generated ICE:
    total 9-14% above real, mostly in pulses (v3m6 seed 0, median donor-day: pulses 41.2 vs 35.4 mg/dL/h, background 34.0
    vs 32.8). By source: meal-head (unannounced) pulse starts 5.55 vs 4.21/day; entry-started 3.08 vs 2.93; size per pulse
    within ~9% once the 0.50/day labeled entries with an unfitted (unknown-size) pulse are allowed for; starts at glucose < 80
    0.62 vs 0.12 (more time low). The meal-start hazard runs ~1.3x the field at every glucose band 70-250+, so it is not the
    state distribution. Teacher-forced on real inputs the calibrated head is right (4.45 vs 4.50/day held-out), so the excess
    comes from closed-loop inputs. Swap test (meal_swap.py, 24 donors): expected starts 4.36/day on real inputs, 5.13 on
    the rollout's own; real inputs with only the background-ICE channels from the rollout 5.32. Why: the labeler starts a
    pulse where ICE begins to rise, so a real meal-head start is preceded by a background-ICE dip (-0.6 sd 10 min before
    onset, 40 donors); the behavior heads learned "dip -> meal" and in generation read it off the model's own draws.
53. **The behavior path no longer sees background ICE (v3m10); kept.** A person sees glucose, not ICE, and the only thing the
    behavior heads could learn from background ICE was the labeler's trough-then-rise onset (LESSONS 52). v3m10 = v3m6 with
    bgice / bgice_ok / bgice_ema masked from the behavior path (the ICE path unchanged). Seeds 0 / 1, held-out, kept harness:
    unannounced meal starts 4.33 / 4.43 per day (labeled 4.21; v3m6 5.55), entry-started 2.74 / 3.02 (2.93), generated
    pulse grams 241 / 236 per day (v3m6 282); calibration offsets shrink (meal +0.07 vs +0.15, entry +0.01 vs +0.16); the
    swap test's closed / real ratio 1.13 / 1.11 (v3m6 1.18), the rest from the pulse and glucose channels. Clean-time
    outcomes, v3m6 -> v3m10: TIR 64.1 / 65.6 -> 67.0 / 65.2, t<54 1.66 / 1.71 -> 1.95 / 1.58, mean 162 / 157 -> 159 / 158,
    insulin 39.7 / 37.4 -> 38.0 / 36.8 U/day (field 74.1 / 0.12 / 152 / 33.1), 5-min quantile distance 16.6 / 13.5 -> 13.8 /
    14.2, hourly 18.0 / 18.6 -> 17.3 / 17.6. Kept for the structure fix; outcome changes are within seed noise. The t<54
    gap (1.6-2.0 vs 0.12) is not from meal-start counts.
54. **Excess lows sit after boluses; refitted pulse shapes are right but not kept, and meal order is not the cause.** v3m10
    seed 0, held-out: low crossings within 3 h of a manual bolus 0.87 vs 0.39 per day, beyond 5 h 0.41 vs 0.51 (the
    generator has fewer lows away from boluses). A generated meal bolus is followed by glucose < 70 within 3 h 26% of the
    time, 8% in the field; per lone bolus 0.13 vs 0.08. Not the cause, each measured: entered grams (25 vs 25 per meal
    bolus), insulin in the first 30 min (+3.2 vs +3.1 U IOB), pulse grams per entered gram (generated 1.69, field 1.30),
    drawn pulse shapes (size-normalized mean kernel within 0.1/h of the labels at every hour), meal order (eating before
    the bolus in 27% of generated vs 26% of field meal boluses, and generated lows are 2-3x the field's in both orders).
    The labeler's pulse kernel was too slow (rebuilt from the peak and run length of 35-min smoothed excess it missed
    12 / 23 mg/dL/h at 15 / 30 min after onset; a per-meal least-squares fit leaves -2 / +3, meals.py fit_shapes,
    ice_v32f), but retraining v3m10 on those labels made outcomes worse, TIR 61.9 / 62.2, t<54 2.42 / 2.10 (v3m10 on the
    old labels 67.0 / 65.2, 1.95 / 1.58): the early meal ICE moved from background into the pulse, and the generator's
    pulses still rise no faster after a meal bolus (pulse ICE at 30 min 58-60 vs 71 labeled). The labeler keeps the fit;
    the models stay on ice_v32 until the post-bolus gap is understood. Background ICE response to glucose state (band x
    15-min trend, next 30 min) matches the field within a few mg/dL/h everywhere; total ICE quantiles match (median 58 vs
    52); the background is 5 mg/dL/h higher and wider above (90th 96 vs 87, sd of hourly means 41 vs 35), and Loop
    delivers ~15% more insulin. Excess lows come at every daily background level, not only low days (1.5 vs 0.95 per day
    in the middle half, 1.4 vs 0.65 in the 75-95th band).
55. **Background ICE needs memory, and fed its own draws the memory compounds: moving the previous value out of the
    recurrent path (v3m11) is not kept.** v3m10 is calibrated one step ahead (real values above its predicted 90 / 95 /
    99th percentiles 9.9 / 5.0 / 1.0% of the time, in every band of the previous value), but generated background stays
    correlated too long (0.08-0.10 at 35-60 min vs 0.04-0.06 real) and its hourly means spread wider (sd 41 vs 35). Swap
    test on the predicted mean (v3m10 seed 0): hourly sd 28.2 on real inputs, 33.5 on the rollout's own, 26.3 with only
    the previous value restored, 32.1 with only it taken from the rollout; the glucose, pulse, meal, entry, bolus and
    clock groups each move it < 1. v3m11 (the previous value at the output head only): seeds 0 / 1 clean-time t<54 1.24 /
    0.98 (v3m10 1.95 / 1.58), TIR 66.9 / 62.3, mean 155 / 167, but the 5-min distance fails its ceiling (36 / 41 vs
    ceiling 28; v3m10 14), the draws widen (1st / 99th percentile -124 / 192 vs -79 / 153 real), correlation is now too
    short (0.02-0.05 at 10-60 min) and hourly means spread wider still (46). Without memory the model covers what it
    cannot track with wider draws. The lows respond to the correlation structure (t<54 fell with it), so the target is
    memory that matches real persistence at 30-60 min, not less memory.
56. **The post-bolus low excess is the same in every architecture, so it is not background-ICE persistence; meal boluses
    are sized right.** Lows within 3 h per meal bolus: v3m6 / v3m10 / v3m11 / v4 0.16 / 0.16 / 0.16-0.19 / 0.17 against
    0.064 in the field, though v4 has the field's correlation at 30-60 min (0.04-0.06) and v3m11 too little. Delivered
    units per meal bolus 2.13 vs 2.22, per 10 g entered 0.95 vs 1.00 (median donor; per donor they track). Pulse grams
    track grams entered more loosely in generation (within-person Spearman 0.07 v3m10 / 0.12 v4 vs 0.19 field; sd of
    log(pulse / entered) 0.79 vs 0.65), a gap but a modest one. Shared by all: hourly-mean spread of background ICE ~40 vs
    35, and meal ICE after a meal bolus that rises slower (total ~100 vs 124 mg/dL/h at 30 min) and tails longer.
57. **Background ICE in the field is coupled to the field's own events; the early meal rise is not an insulin-timing
    artifact.** PLANT_REAL_BG=1 (diagnostic: the field's background ICE at the same time, meals and behavior generated),
    v3m10 seed 0: clean-time TIR 60.8, t<54 5.68 (generated background: 67.0 / 1.95), lows per meal bolus 0.24. After a
    generated meal bolus the real background stays flat (35 mg/dL/h), after a real one it rises to 69 at 30 min: the
    field's background carries components locked to its own meals, and with them out of step the controller fails worse.
    Not an insulin-model timing bump: after lone manual boluses (no entry within 90 min, no pulse starting -60..+120 min,
    7,793 boluses, all pilot donors) background ICE falls 20-25 mg/dL/h for 3 h after boluses under 3 U (given at highs
    that then ease) and stays near flat for larger ones; no positive bump while modeled insulin ramps up.
58. **The meal-locked rise in background ICE is learned and lost in closed loop; the loss is in the state the model brings
    to the meal, not in the meal's inputs.** Fed real held-out inputs, v3m10 predicts the rise after a meal bolus (mean 47
    -> 65 mg/dL/h by 30 min; real 45 -> 61). On its own rollout inputs it predicts 40 -> 36 at +10 min -> 52 at 30.
    Partial dependence on real events: holding glucose flat from the bolus raises the predicted rise (65 at 30 min), a
    larger pulse in progress (+0.12 scaled, the generated excess before the bolus) lowers it by 3; the same bolus and carb
    inputs move the prediction +3 from a real context and -3 from a generated one. The remaining difference is the
    recurrent state built from the model's own earlier draws (LESSONS 42-48), here at meals, where it matters for lows.
59. **Post-meal-bolus lows: not meal context, not onset timing.** v3m10 seed 0, held-out. Stratified, generated lows per
    meal bolus are 2.5-3x the field's in every stratum: pulse ICE already in progress at the bolus < 10 / 10-40 / > 40
    mg/dL/h 0.22 / 0.25 / 0.26 vs 0.09 / 0.09 / 0.08; glucose at the bolus < 120 / 120-180 / > 180 0.39 / 0.21 / 0.17 vs
    0.16 / 0.06 / 0.06. Halving the entry-to-pulse onset delay in the plant (PLANT_EOFF_SCALE=0.5, diagnostic) moved lows
    per meal bolus 0.162 -> 0.149 and clean-time TIR / t<54 67.0 / 1.95 -> 65.3 / 1.59, within noise. Drawn pulse shapes
    match their labels by source (entry-started and unannounced kernels within 0.05/h). Lone corrections (no entry within
    90 min, no pulse -60..+120 min) are not the problem: lows within 3 h 0.11 generated vs 0.16 field, background and
    glucose trajectories alike; but the generator gives 1.8x as many of them (427 vs 238 per 28-day run), a structure gap
    (corrections are rare on an automated system).
60. **Anatomy of the generated lows: a population-wide excess carried into the low by insulin, after meals; the response
    to the low itself matches.** v3m10 seed 0, held-out, per donor then median: 22 of 24 donors exceed 1% generated t<54
    (field at most 0.77% for every one; replay matches the field per donor). Per crossing below 70: chance of reaching 54
    0.45 vs 0.18, minutes below 70 30 vs 15, nadir 57 vs 62, crossings 1.08 vs 0.71 per day; at the crossing IOB above the
    overnight level 0.56 vs 0.15 U and insulin action (ISF x activity) 77 vs 57 mg/dL/h; ICE after the crossing 56 / 85
    vs 58 / 95 mg/dL/h at 0-30 / 30-60 min (the low response is close). In the 2 h before: automatic insulin over the
    overnight rate the same (+0.11 U), glucose the same (115 vs 114), a manual bolus before 40% vs 29% of lows, and ICE
    higher (48 vs 27 mg/dL/h): generated lows come after food and a bolus, field lows in quiet stretches. Per-person bar
    (field inside the range of 3 generated runs; 50% if faithful): TIR 12%, t<70 8-12%, t<54 8%, mean 21-29%, insulin 21%.
    Not a level bias: on the held-out month the model's predicted background mean is 0.2 mg/dL/h above the real one and its
    rollouts 1.4 above (median donor; real held-out 33.0, the 28 training days before it 39.1), so the extra insulin comes
    from how ICE moves, not from how much there is.
61. **Training noise of the kept recipe (v3m10, ice_v32, kept harness), three trainings.** Held-out clean-time TIR 67.0 /
    65.2 / 68.7, t<70 3.78 / 3.37 / 3.96, t<54 1.95 / 1.58 / 1.69, mean 159 / 158 / 152, insulin 38.0 / 36.8 / 37.2 U/day
    (field 74.1 / 0.86 / 0.12 / 152 / 33.1); 5-min quantile distance 13.8 / 14.2 / 12.3, hourly 17.3 / 17.6 / 17.3. Seed-
    to-seed sd: TIR ~1.8, t<54 ~0.19, mean ~4. A change is beyond training noise when it moves TIR by more than ~3 or t<54
    by more than ~0.4 on both of two seeds.
62. **Generalization check on v3m10: drawn people miss the population's tails and invert one co-variation; draw from
    real people, not a Gaussian.** DRAW_PERSON (a new person on each of the 24 hosts, 3 each, kept harness), against all
    168 trained people's field rates (held-out month): per-person entries / corrections per day, 10th / 50th / 90th
    percentile, real 0.12 / 3.09 / 6.94 and 0.10 / 1.07 / 4.25. A Gaussian over the profile and trait vectors drew 0.89 /
    2.59 / 6.14 and 0.54 / 1.71 / 5.82: the entry trait is bimodal (a group of non-announcers far below the rest), and a
    Gaussian puts drawn people in the gap. Now the plant draws a trained person other than the host, jittered by 0.3 x
    the population covariance (DRAW_MODE=kernel, the default; DRAW_MODE=gauss keeps the old draw): 0.58 / 2.88 / 5.0 and
    0.79 / 1.70 / 4.75, medians right, tails still pulled in. Co-variation among the 24 hosts: real people who enter
    more carbs have fewer severe lows (Spearman -0.31), drawn people more (+0.38 Gaussian, +0.13 kernel); drawn t<54
    median 2.2-3.1 vs 0.12. Rare correctors are not rare even for real people: teacher-forced on its own training days
    the model expects i056 (no lone boluses in 100 days) to make 0.62 a day, i033 (0.20) 0.68; the trait offset was fitted
    under a prior and step weights (LOWW) and cannot reach rare rates. Under test: traits refit by maximum likelihood on
    training days with the network frozen (fit_traits.py).
63. **Settings-edit natural experiments on v3m10 (tier 3c), two trainings, ice_v32, kept harness.** 70 edits (62 scored
    on 47 donors; 5 donors without meal labels drop out), replay + 3 runs per arm. The field's own change around a real
    edit is barely above its change around random days with no edit (TIR sd 11.4 vs 8.5, mean 16.3 vs 13.3), so per-
    edit correlations are bounded low. Predicted vs field change, seeds 0 / 1: mean glucose r 0.39 / 0.39, slope 0.85 /
    0.81 (replay r 0.32, slope 0.39); t<70 r 0.47 / 0.51, slope 0.80 / 0.73 (replay 0.48 / 0.48); TIR r 0.05 / 0.14,
    slope 0.16 / 0.52 (replay 0.24 / 0.49); t<54 r 0.21 / 0.26 (replay 0.15). With the need shift separated (field mean
    change ~ a x predicted edit effect + b x clean-ICE shift, 55 edits within 10 TIR of the field on replay): generator a =
    1.10 (replay 0.62), b ~1.0; on the steady-need half (28 edits) generator r 0.72, slope 1.46, replay r 0.71, slope 0.93.
    The generator sizes an edit's effect on mean glucose about right overall and a third small where need is steady;
    TIR and t<54 changes do not yet rank. Its own-settings level is off (TIR median -5.0 / -6.9 vs replay -0.2): the
    absolute gap of LESSONS 54-60.
64. **Refitting each person's behavior traits by maximum likelihood on their training days puts rare behavior right; kept
    (post-training step).** `fit_traits.py` (runs dir, beside calibrate_v3.py): network frozen, per person and head
    (meal, entry, b_with, b_alone) the logit shift d with sum sigmoid(logit + d) = events + 0.5 over the head's training
    steps, unweighted. Run after training, before calibrate_v3.py. Shifts are small for most people (median ~0, 90%
    within -0.4..+0.6) and large for the rare: non-announcers' entry -3 at the 5th percentile, i056's lone-bolus -4.6
    (no corrections in 100 training days, previously expected at 0.62 a day). The pooled calibration offsets then fall
    to ~0 (meal +0.03, entry 0.00, b_alone +0.05; before +0.15 / +0.16 / +0.33): what calibration did in bulk is now
    per person. v3m10 seeds 0 / 1, held-out: lone boluses per day for the rarest correctors i056 0.00 / 0.00 (field
    0.00; before 0.40), i033 0.19 / 0.12 (0.04; before 0.54), i039 0.64 / 0.52 (0.39; 1.11); outcomes within noise (TIR
    66.2 / 65.0 vs 67.0 / 65.2, t<54 1.77 / 1.52 vs 1.95 / 1.58); per-person pass rate (3 runs, 50% if faithful) mean
    glucose 29 -> 42 / 21 -> 33%, insulin 21 -> 29 / 21 -> 21%, t<54 8 -> 12 / 8 -> 12%, TIR 12% unchanged.
65. **Dial check on the kept generator (v3m10 seed 0, traits refit): all four dials move what they name.** 24 held-out
    donors, 2 runs per setting, median per day. Announcement 1 / 0.5 / 0: entries 3.90 / 1.90 / 0.00, boluses 4.65 / 3.51
    / 2.27, eating unchanged (pulses 7.2-7.3, 225-228 g-eq), day spread 20.9-22.4; TIR 66.0 / 65.6 / 61.3 and mean 160 /
    160 / 171 follow as consequences (unannounced meals go unbolused). Compression 0 / 1 / 3: sensor events 0 / 0.52 /
    2.07 per 28 days, all else within noise. Slow state off / 1 / 2: day-to-day sd of the daily background level 20.9 /
    22.7 / 25.6, behavior unchanged; t<54 1.88 / 2.19 / 3.79 (more day-level swing, more lows). Monthly cycle (new plant
    dial MONTH_CYCLE, off by default: a 28-day sinusoid in background ICE, amplitude x the person's ISF x TDD/24, random
    phase): at 0.2 the daily background level follows the cycle term (within-run correlation 0.41, sd of the term 10.5
    mg/dL/h) and so does daily insulin delivered (0.30); entries -0.04, meals -0.10, eating 218 vs 226 g-eq.
66. **Offense and defense (Pete, 2026-10-14), and the generator's missing anticipation.** Forces on glucose split into two
    teams: offense pushes glucose away from range (meals, exercise; mostly blind to glucose), defense brings it back
    (insulin, rescue carbs, a walk to bring a high down); the defense strengthens as excursions widen and how much it acts
    ahead of time is personal. Measured against that: the generator's offense matches (meal starts, sizes, shapes, timing;
    the dials leave eating alone) and its reactive defense at a low matches (ICE after a crossing below 70 close to the
    field), but its anticipatory defense is missing: generated lows start with 0.56 vs 0.15 U above basal and the model had
    no input that showed pending insulin (only glucose, its trend and a 30-min CGM projection; the old `eventual` input
    added labeled pulses still to absorb, a leak of food the person may not know of). Diagnostic PLANT_REAL_MEALS=1 (the
    person's real meals, entries and boluses replayed, background generated; v3m10 seed 0, traits refit): clean-time
    t<54 7.48, mean 125, lows per meal bolus 0.39; after a real meal bolus the generated background falls to ~2 mg/dL/h at
    60 min where the field's rises to 69 at 30: the field's background carries the defense in step with its own offense,
    and neither stream can be swapped in alone (with LESSONS 57). Under test: iob_net (ISF x IOB above the basal level,
    what Loop shows) as an input to both paths, FEATURES_M2I.
67. **Learning curve: more people do not close the outcome gap.** v3m10 kept recipe, traits refit, calibrated, scored on
    the same 24 held-out pilot donors (clean time, seeds 0 / 1). 84 donors (the 24 hosts + 60, 3k iterations): TIR 66.0 /
    64.3, t<54 2.28 / 1.68, mean 155 / 158. 168 (the pilot): 66.2 / 65.0, 1.77 / 1.52, 160 / 160. 527 (pilot + 359
    expansion donors labeled with the pilot's labeler version, 21b2c3c; 6k iterations): 60.3 / 61.8, 1.75 / 2.14, 171 /
    164 (field 74.1 / 0.12 / 152). Halving the people moves nothing beyond training noise; tripling them lowers TIR by
    4-5 and raises mean glucose by 4-11 on the pilot hosts, t<54 unchanged. Per-person pass rate on TIR 8-12% (84), 12%
    (168), 17-21% (527). Data volume is not what limits the lows; the gap is structural (LESSONS 60, 66). Expansion
    cohort (x001-x454, ETL v32, 452 exported, 359 with >= 56 clean days) is at ~/.loop-eval/ice_x32 (current labeler)
    and ice_x32o (pilot labeler); merged root ice_v32x; train_v3.py KEEP=<alias file>.
68. **Pending insulin as an input moves lows in the right direction; on both paths it is not kept.** v3m10 + FEATURES_M2I
    (iob_net to behavior and background paths), traits refit, seeds 0 / 1, held-out clean time: t<54 1.54 / 1.05 (v3m10
    refit 1.77 / 1.52), lows per meal bolus 0.138 / 0.124 (~0.16), IOB above basal at the start of a low 0.32 / 0.35 (0.56;
    field 0.15), chance a low reaches 54 0.42 / 0.40 (0.45; field 0.18); teacher-forced background NLL 0.581 / 0.551 (0.590
    / 0.591). But TIR 65.2 / 59.4 and mean 160 / 171 (v3m10 refit 66.2 / 65.0, 160 / 160): seed 1 runs high beyond
    training noise. Read as the background path taking high insulin as a reason for more ICE everywhere; under test:
    v3m12, the input on the behavior path only.
69. **The defense ramps with projected departure in everyone, and the generator squashes people toward the middle.** Per
    person, mean background ICE over the next 30 min (minus the person's mean) by PROJECTED glucose (glucose minus ISF x
    IOB above basal), held-out, v3m10 seed 0 traits refit vs field, 24 donors (defense_curves.py). Field median by band
    < 0 / 0-40 / 40-70 / 70-100 / 100-140 / 140-180 / 180-250 / > 250: +30 / +15 / +5 / -3 / -9 / -12 / -17 / -12;
    generated +23 / +14 / +7 / -1 / -5 / -8 / -12 / -10. The person-to-person spread at the low end is cut nearly in
    half: field 90th percentile person +57 / +40 / +22 / +13, generated +31 / +22 / +16 / +8. Per-person onset (highest
    projected band where the response first exceeds +20) agrees with the field at Spearman 0.25: the strong, early
    defenders are not the generator's early ones. Pete's frame (2026-10-14): how early each defense kicks in is personal,
    but with enough departure everyone's response ramps up. Next: a defense term on the background path, a learned ramp
    in projected departure that is zero heading into range or above (so it cannot become a resistance, LESSONS 68), with
    a per-person onset and strength refit by maximum likelihood on training days.
70. **Pending insulin on the behavior path only (v3m12): neutral, no regression.** Seeds 0 / 1, traits refit, held-out clean
    time: TIR 67.0 / 65.6, t<54 1.78 / 1.41, mean 157 / 160 (v3m10 refit 66.2 / 65.0, 1.77 / 1.52, 160 / 160); lows per
    meal bolus 0.145 / 0.136 (~0.16), IOB above basal at the start of a low 0.35 / 0.48 (0.56). Within training noise. The
    missing anticipation is not in logged or unannounced snacks (behavior) but in the background push (LESSONS 69); v3m13
    builds the per-person defense ramp on this base.
71. **A defense ramp keyed to projected glucose cuts severe lows by about half; kept (v3m13).** Background ICE gets a
    learned, monotone push in projected glucose (glucose - ISF x IOB above basal), zero heading into range or above, on
    top of v3m12 (pending insulin on the behavior path). Traits refit, calibrated, held-out clean time, seeds 0 / 1: t<54
    1.05 / 0.72 (v3m10 refit 1.77 / 1.52; beyond training noise on both), TIR 65.7 / 63.0 (66.2 / 65.0), mean 162 / 166
    (160 / 160), within noise though seed 1's mean is at its edge. Lows: chance of reaching 54 0.37 / 0.36 (0.45; field
    0.18), minutes below 70 20 / 20 (30; 15), IOB above basal at the start 0.06 / 0.20 (0.56; 0.15), lows per meal bolus
    0.135 / 0.135 (~0.16; 0.064). Learned ramp (seed 0): 0 at projected 120+, 4 / 7 / 14 mg/dL/h at 30 / 0 / -40. The
    median person's defense now matches the field (+32 / +31 vs +30 heading below 0); the strong end is still cut short
    (90th percentile person +39 / +42 vs +57) and the per-person onset still does not match (Spearman -0.16 / 0.05).
    The per-person onset and strength stayed at their starting values in training (rare lows, small gradient); refit by
    maximum likelihood on training days (fit_defense.py: onsets -12 to +34 mg/dL, strength 0.56-1.22) they change
    nothing beyond noise (seed 0: t<54 1.04, TIR 65.9, mean 159, 90th percentile person +38, onset agreement 0.19).
    Pete's frame (LESSONS 66, 69) holds: the missing piece was anticipation keyed to where glucose is heading. Still open:
    the individual spread of the defense, and the remaining post-bolus low excess (2x the field).
72. **After the defense ramp, the TIR gap is highs away from meals: background ICE wanders up too often.** v3m13 seed 0,
    held-out clean time, time above 180 as % of all time by context: within 3 h after an announced meal 13.1 vs 13.2
    (field), after an unannounced start 14.1 vs 14.0, otherwise 9.4 vs 4.3 (above 250: 3.9 vs 1.0). Highs that begin
    with no entry or pulse in the 3 h before: 0.71 vs 0.41 per day, median 30 vs 45 min, peak 194 vs 200, background ICE
    the hour before 46 vs 41 and during 66 vs 66 mg/dL/h, IOB above basal 0.4 vs 0.5 U. Post-meal highs match; the excess
    is the hour-scale wandering of the background (hourly-mean sd 41 vs 35, LESSONS 54-55), the model compounding its
    own draws. Under test: the two-stream generator (v4: outside stream from exogenous inputs and latent persistence, no
    own-draw memory; field persistence at 30-60 min, LESSONS 56) with its reaction seeing projected glucose (iob_net).
    Monthly-cycle dial at three settings (v3m13 seed 0, traits refit, 2 runs per setting): within-run correlation of the
    daily cycle term with the daily background level 0.34 / 0.41 / 0.81 and with daily insulin delivered 0.24 / 0.30 /
    0.67 at 0.1 / 0.2 / 0.4; with entries -0.01 / -0.04 / +0.05, meals 0.00 / -0.10 / -0.23; eating 224 / 218 / 225 vs
    228 g-eq a day at 0; day-to-day sd of the background level 19.9 / 23.1 / 30.2 vs 19.7. The dial scales and moves
    insulin need; t<54 0.93 / 1.16 / 2.26 follows as a consequence of the wider swing.
73. **The two-stream generator with a reaction that sees pending insulin (v4, FEATURES_M2V) is not kept.** Seeds 0 / 1,
    traits refit, held-out clean time: TIR 60.9 / 59.6, t<54 1.82 / 2.53, mean 167 / 168 (v3m13 65.7 / 63.0, 1.05 / 0.72,
    162 / 166). Time above 180 away from meals 7.2 / 6.6% of all time (v3m13 9.4, field 4.3) but after announced / un-
    announced meals 15.7-16.2 / 16.5-17.4 (13.1 / 14.1; field 13.2 / 14.0); lows per meal bolus 0.17 / 0.16. Background
    persistence matches the field at 30-60 min (0.04-0.07) but the 5-10 min lags run high (0.48 / 0.23 vs 0.40 / 0.11)
    and the hourly-mean sd stays wide (39.7-39.9 vs 35). Generating the outside stream without own-draw memory trims the
    non-meal highs a little; a free reaction network, even shown pending insulin, does not give the anticipatory defense
    that v3m13's shaped ramp does. v3m13 stays.
74. **Settings-edit test on v3m13 (seed 0, traits refit): on a par with v3m10, TIR changes begin to track.** Per edit,
    predicted vs field change: TIR r 0.22, slope 0.69 (v3m10 0.05 / 0.16 and 0.14 / 0.52); t<70 0.44 / 0.74; t<54 0.18
    / 0.15; mean 0.30 / 0.61 (v3m10 0.39 / 0.81-0.85). With the need shift separated: edit coefficient on mean glucose 0.87
    (v3m10 1.10, replay 0.62); the generator's own tracking run vs the field change r 0.54, slope 0.59 (v3m10 0.42 /
    0.51); steady-need half (28 edits) r 0.64, slope 1.41 (0.72 / 1.46). Own-settings level TIR -6.6 median (the absolute
    gap). One seed; a second is owed before reading the TIR gain as real.
75. **The defense's high side (v3m14) is neutral: the highs away from meals are not a weak defense.** v3m13 + a mirrored
    high-side ramp (downward push growing past projected 160-250). Seeds 0 / 1, traits refit, held-out clean time: TIR
    65.0 / 64.2, t<54 0.83 / 0.87, mean 161 / 162 (v3m13 65.7 / 63.0, 1.05 / 0.72, 162 / 166), within noise; time above
    180 away from meals 7.9 / 9.8% of all time (v3m13 9.4, field 4.3). The learned ramp acts above projected 250 (median
    -34 / -31 vs field -12 there, an overshoot) and leaves 180-250 at -12 / -14 vs the field's -17. The excess is in how
    often the background turns up away from meals (0.71 vs 0.41 episodes a day, LESSONS 72), not in how hard it is
    pushed back. v3m13 stays.
76. **The TIR gap is a closed-loop level excess of ~10 mg/dL/h, carried by the previous-value channel; it shows most
    overnight.** v3m13 seed 0, held-out. Overnight (00-06, nothing eaten since 21:00): background ICE 46.6 vs 23.7 mg/dL/h,
    glucose 164 vs 130, time above 180 29.8 vs 5.6%, night-to-night sd 31.9 vs 23.8. Time above 180 away from meals runs
    about double the field at every hour of the day. Model level on real inputs, matched steps: night 26.8 vs real 24.7,
    day 35.4 vs 36.1 (right); on the rollout's own inputs 35.2 / 46.3, the draws 34.2 / 45.0 (v3m10 alike: 33.1 / 42.3).
    Swap test on the level (matched clean steps): all real 33.9, all closed-loop 43.7; restoring the real previous
    background value alone 36.2; taking only it from the rollout 43.7; every other group (glucose, pending insulin, pulse,
    meal history, entries, boluses, clock) < 2. The model's own draws, read back as what background ICE just did, pull its
    level up (the drift of LESSONS 48, here as a steady offset). Under test: feeding back the predicted mean instead of the
    draw (PLANT_FEEDBACK=mean), to tell noise compounding from a biased mean.
77. **The level excess is noise compounding, not a biased mean.** v3m13 seed 0 with the plant feeding back the predicted
    mean instead of the draw (PLANT_FEEDBACK=mean, diagnostic): overnight background 18.8 vs field 23.7 (draw fed back:
    46.6), glucose mean 122, t<54 2.10, 5-min sd of background 20 vs 56, correlation 0.75 at 5 min and 0.39 at 30 (field
    0.40 / 0.07). Fed its mean, the model sits below the real level and turns sluggish; fed its draws, above. Its response
    to a previous value above the person's usual is stronger than to one below, so its own noise ratchets the level up.
    Under test: hiding the previous value on 30% of training steps (BGDROP), so the level is carried by context and the
    last value is only a local correction.
    Seed 1 does not confirm the TIR gain: TIR r 0.09, slope 0.29; t<70 0.32 / 0.67; t<54 0.07 / 0.07; mean 0.28 / 0.56;
    own-settings level TIR -5.2. On settings edits v3m13 is on a par with v3m10 (TIR r 0.22 / 0.09 vs 0.05 / 0.14), not
    better; the absolute level gap (LESSONS 76-77) is the larger obstacle to change prediction.
78. **Hiding the previous background value on 30% of training steps does not stop the ratchet; not kept.** v3m13 + BGDROP 0.3,
    seeds 0 / 1, traits refit, held-out clean time: TIR 63.5 / 65.1, t<54 0.96 / 0.48, mean 163 / 164 (v3m13 65.7 / 63.0,
    1.05 / 0.72, 162 / 166), within noise; overnight background 50.0 / 45.4 mg/dL/h (v3m13 46.6, field 23.7), time above
    180 away from meals 9.5 / 9.1% (9.4; 4.3). Taught to manage without its last value, the model still leans on it when
    it is there. For contrast, the two-stream generator (v4, LESSONS 73), whose outside stream never reads its own draws,
    holds the overnight background at 28.9 / 29.2 with night-to-night sd 23.2 / 25.6 (field 23.8), though its within-night
    hourly swings run wide (sd 19.7 / 22.8 vs 12.7) and its overnight glucose high (168 / 174 vs 130). Under test: v4r, the
    two-stream generator with v3m13's shaped defense ramp in its reaction.
79. **The two-stream generator with v3m13's defense ramp (v4r) is not kept.** Seeds 0 / 1, traits refit, held-out clean
    time: TIR 60.6 / 59.5, t<54 2.07 / 1.96, mean 167 / 168 (v3m13 65.7 / 63.0, 1.05 / 0.72, 162 / 166). Overnight
    background 31.0 / 35.5 mg/dL/h (field 23.7, v3m13 46.6) but overnight glucose 163 / 170 (130) and time above 180 there
    35%; within-night hourly swings 23.6 / 21.1 vs 12.7. The ramp learned weaker inside v4 (median person +22.5 / +23.8
    heading below 0 vs +32 in v3m13, field +30): beside a latent stream fitted by the Kalman likelihood, the defense
    shows up less in the background's mean. Next: v3m15, the exogenous level anchor inside v3m13.
80. **An exogenous baseline under v3m13 (v3m15) moves the level the right way on both seeds; kept as the base, a modest
    gain.** A small recurrent net on exogenous inputs only (clock, meals, entries, boluses, the person) adds a baseline to
    every background mixture mean; the background path reads its previous value as the deviation from the previous
    baseline. Seeds 0 / 1, traits refit, held-out clean time: TIR 65.2 / 66.8, t<54 0.83 / 0.95, mean 160 / 160 (v3m13
    65.7 / 63.0, 1.05 / 0.72, 162 / 166; field 74.1 / 0.12 / 152); overnight background 41.9 / 39.8 mg/dL/h (46.6; 23.7),
    overnight glucose 157 / 149 (164; 130), time above 180 away from meals 8.8 / 8.6% (9.4; 4.3); lows per meal bolus
    0.136 / 0.137; defense median +31 heading below 0 (field +30). Same direction on every level measure on both seeds, no
    regression; the TIR gain is near training noise. The level is still well above the field: the anchor holds part of it.
81. **With an exogenous baseline, taking the background's memory of its own values away fixes the level and breaks the
    5-minute shape (v3m16); not kept.** v3m15 with the previous deviation from the baseline at the output head only.
    Seeds 0 / 1, traits refit, held-out clean time: TIR 62.4 / 61.8, t<54 1.04 / 1.21, mean 165 / 164 (v3m15 65.2 / 66.8,
    0.83 / 0.95, 160 / 160). Closed-loop level excess +2.4 mg/dL/h (v3m15 +4.8, v3m13 +9.8), but the 5-min quantile
    distance 33.4 fails its ceiling (27.9; v3m15 12-14), background 5-min sd 89 vs 56, within-night hourly sd 28.7 vs
    12.7. As in v3m11 (LESSONS 55): without a memory of where the person currently stands relative to their baseline,
    the model widens every draw to cover it. Memory of the deviation is needed; it must not ratchet the level.
82. **A linear memory of recent deviations removes the level ratchet; without a deviation-aware shape the draws widen
    (v3m17); not kept, mechanism confirmed.** v3m15 with the recurrent background path blind to its own values and the last
    30 min of deviations from the baseline entering the mixture means linearly (learned AR). Seeds 0 / 1: closed-loop level
    excess +0.4 / +1.0 mg/dL/h (v3m15 +4.8, v3m13 +9.8); overnight background 28.6 / 30.4 (field 23.7), overnight glucose
    143 / 152 (130), time above 180 away from meals 6.8 / 6.8% (v3m15 8.8; field 4.3); TIR 65.8 / 65.4, t<54 1.41 / 1.09,
    mean 159 / 159. But the background's 5-min sd 110 / 99 vs 56, quantile distance 47.7 / 50.5 vs ceiling 27.9, hourly-
    mean sd 58 vs 35: blind to its own deviations, the shape cannot tell a calm stretch from a volatile one and every
    draw is wide. The ratchet is the asymmetric (nonlinear) response of the mean to the model's own values. Under test:
    v3m18, means from the exogenous path + linear memory, weights and scales from a path that sees the deviation.
83. **Means from the non-ratcheting parts but mixture weights from the deviation-aware path (v3m18): the ratchet returns
    through the weights; not kept.** Seeds 0 / 1: closed-loop level excess +4.3 / +5.8 mg/dL/h, overnight background
    45.9 / 36.1 (field 23.7); seed 0 has the shape right (5-min distance 15.9, background 5-min sd 75) but seed 1 does not
    (45.9, sd 106) and collapses (TIR 52.6, t<54 5.83); TIR 64.6 / 52.6. A mixture's mean is the weighted sum of its
    components, so a path that moves the weights moves the mean. Under test: v3m19, the mixture centred (its mean pinned
    to the exogenous mean + baseline + defense + linear memory; the deviation-aware path sets only weights, scales and
    component offsets relative to that mean, so it cannot move the level by construction).
84. **A centred mixture (v3m19) blows up in closed loop; not kept.** The mixture's mean pinned to the non-ratcheting parts,
    the deviation-aware path setting weights, scales and component offsets relative to it. Seed 0, held-out clean time:
    TIR 45.1, t<54 8.92, mean 181; background 5-min sd 275 vs 56, quantile distance 180 vs ceiling 27.9, within-night
    hourly sd 70 vs 13; closed-loop level excess +3.2. With the mean fixed the model fits the data by spreading its
    component offsets (far components at small weight), and in closed loop the deviation-aware weights move onto them.
    Summary of LESSONS 76-84: the level ratchet is the model's nonlinear response to its own recent values; a linear
    memory removes it (v3m17) but the shape then needs those values, and every route that lets them shape the
    distribution (weights, scales, offsets) has either brought the ratchet back (v3m18) or destabilized the mixture
    (v3m19). v3m15 (exogenous baseline, +4.8 residual excess) remains the base.
85. **An unsigned scale from recent deviation sizes does not narrow v3m17's draws enough (v3m20); not kept.** v3m17 + a
    common log-scale shift on every mixture component from |deviation| over the last 30 min and the recurrent state (mean
    and weights untouched by construction). Seeds 0 / 1: level holds (closed loop 30.9 / 30.8 vs real 32.7 / 33.5),
    overnight background 33.8 / 30.1 (field 23.7), time above 180 away from meals 6.3 / 7.3% (4.3); but background 5-min
    sd 81 / 102 vs 56, quantile distance 47.3 / 58.7 vs ceiling 27.9, hourly-mean sd 62 / 64 vs 35; TIR 64.7 / 65.5,
    t<54 1.54 / 1.47. The learned linear memory is moderate (lag-1 0.50, sum 0.67-0.69; correlation by lag near the
    field's), so the excess is the per-step distribution's width, not the memory. The size of recent deviations does not
    carry what the recurrent net reads from their full signed history. v3m15 remains the base.
86. **One-step self-feeding (the previous-value input replaced by the model's own draw on 30% of training steps) does not
    stop the ratchet; not kept.** v3m15 + SELFFEED 0.3. Seeds 0 / 1: closed-loop level excess +5.7 / +9.3 mg/dL/h (v3m15
    +4.8), overnight background 35.7 / 50.4 (field 23.7), overnight glucose 166 / 181 (130); lag-1 correlation of the
    background 0.28 / 0.30 (field 0.40), 5-min quantile distance 36.9 / 37.0 (ceiling 27.9); TIR 61.7 / 62.0, t<54 1.24 /
    0.70, mean 165 / 169. As with multi-step scheduled sampling (LESSONS 43): taught that its own draws are less
    informative, the model weakens the 5-minute dependence, and the level excess stays.
87. **Generalization check on v3m15 (seed 0, kernel draw): severe lows and the behavior tails much closer; one co-variation
    still inverted.** Drawn people (3 per host, 24 hosts) vs the real population, 10th / 50th / 90th: t<54 0.0 / 0.75 /
    5.2% (v3m10 draws 0.46-0.5 / 2.2-3.1 / 7.7-8.1; real 0.0 / 0.12 / 0.55); entries 0.36 / 2.66 / 6.75 a day (all 168
    trained people 0.12 / 3.09 / 6.94); corrections 0.36 / 1.38 / 5.41 (0.10 / 1.07 / 4.25); TIR 35 / 61 / 76 (52 / 74 /
    89); mean 134 / 167 / 224 (127 / 152 / 188), the level excess again. Real people who enter more carbs have fewer
    severe lows (Spearman -0.31); drawn people slightly more (+0.23).
88. **Routing the offense through the exogenous baseline only (v3m21) helps on both seeds; kept, new base.** v3m15 with
    every outside-event input (meals, entries, boluses, clock) feeding only the exogenous baseline (128 wide), and the
    recurrent background path seeing only the glucose state and its own deviation from the baseline. Seeds 0 / 1, traits
    refit, held-out clean time: TIR 66.8 / 68.4, t<54 0.66 / 0.52, mean 162 / 162 (v3m15 65.2 / 66.8, 0.83 / 0.95, 160 /
    160; field 74.1 / 0.12 / 152); closed-loop level excess +1.6 / +2.1 mg/dL/h (v3m15 +4.8, v3m13 +9.8); lows per meal
    bolus 0.104 / 0.100 (0.136; field 0.064), meal boluses followed by a low within 3 h 15.3 / 16.3% (17.8; 7.8); 5-min
    quantile distance 13.5 / 15.3 (ceiling 27.9), hourly-mean sd 38 / 39 (field 35); defense median +29 / +25 heading
    below 0 (field +30). Still short: the background's rise after a meal bolus (+12 / +13 vs +38 in the field), time above
    180 away from meals (8.1 / 7.6% vs 4.3), overnight background 37 / 44 (24). Pete's frame again: offense is exogenous.
89. **A level offset on the fed-back draw overshoots; apply it after feedback.** First calibration (v3m15 seed 0): the
    offset subtracted from each draw before it was fed back as the previous value. Round 1 measured a median excess of
    +2.9 mg/dL/h on the training window; with it applied, round 2 measured -6.8 (the correction went round the same
    previous-value channel that ratchets, with a gain well above 1), and the two-round offset added level: held-out TIR
    47.4, mean 172 (uncalibrated 65.2 / 160). Now the plant feeds back the uncorrected draw and applies the offset only to
    the ICE the body sees, so the model's own dynamics are unchanged and one measurement on the training window suffices.
90. **Level calibration (after feedback) on v3m21 changes nothing: what is left is the daily profile, not the level.**
    v3m21 seeds 0 / 1, one training-window measurement: median level excess +1.3 / -1.8 mg/dL/h (v3m15 measured +2.9),
    so the per-person offsets are small; held-out with them: TIR 66.3 / 64.1, t<54 0.68 / 0.53, mean 162 / 167
    (uncalibrated 66.8 / 68.4, 0.66 / 0.52, 162 / 162). The overall level is about right, but overnight (00-06, nothing
    eaten since 21:00) background runs 43.7 / 47.1 vs 23.7 and glucose 165 / 186 vs 130, time above 180 overnight 29 /
    46% vs 5.6%; so the daytime level runs low. The baseline's clock dependence, or the closed-loop path at night, has
    the profile wrong; a per-person offset cannot fix a profile. Calibration not kept (no gain); v3m21 stays.
91. **In v3m21 the ratchet survives at night, through the deviation channel.** Seed 0, held-out, 00-06 steps: predicted
    background mean on real inputs 27.3 mg/dL/h (real 24.7), on the rollout's own 32.5, drawn 32.3; daytime 33.6 / 35.2 /
    36.1 vs real 36.1, so over the whole day the level looks right (+1.6). Night-only swap test: restoring the real previous
    value alone 26.1; taking only it from the rollout 33.8; glucose, pending insulin, meals, entries, boluses, clock each
    move it by less than 2 the other way. The recurrent path's nonlinear response to its own deviation from the baseline
    still ratchets when nothing exogenous anchors it (no meals overnight). The open structural problem, narrowed: the
    deviation memory must be symmetric (linear, v3m17) for the level and still let the shape follow calm vs volatile
    stretches (v3m17 / v3m20 widened, v3m18 / v3m19 brought the ratchet back or blew up).
    Settings-edit test on v3m15 (seed 0, 61 edits; one lost to a killed plant process): mean glucose r 0.34, slope 0.78;
    TIR r 0.16, slope 0.56; t<70 0.32; t<54 0.02; own-settings level TIR -5.0. On a par with v3m10 / v3m13 (LESSONS 63, 74).
92. **A deviation path exactly odd in the mean, even in the shape (v3m22), does not stop the night ratchet; not kept.**
    v3m21 with the recurrent background path run twice (deviation history as is and sign-flipped): component means half the
    difference (odd), weights and scales the average (even). Seeds 0 / 1, traits refit, held-out clean time: TIR 60.8 /
    66.7, t<54 1.38 / 1.23, mean 167 / 158 (v3m21 66.8 / 68.4, 0.66 / 0.52, 162 / 162). Night (00-06) level: real-input
    prediction 25.2 / 26.5, closed loop 31.2 / 31.0 (still +5-6); overnight glucose 187 / 170 (130). The draws are skewed,
    so the deviations do not average zero, and an odd response to a skewed input still shifts the level; the symmetry also
    takes away any glucose-only push from the recurrent path. v3m21 stays the base.
93. **Clock-band level calibration (after feedback) on v3m21 changes nothing; generated nights fall too slowly, not start
    too high.** Offsets by 6-h band from training-window rollouts (median, seeds 0 / 1: 00-06 +5.8 / +4.9, 06-12 +3.6 /
    +0.9, 12-18 +0.4 / -3.6, 18-24 -3.7 / -6.6 mg/dL/h). Held-out: TIR 66.0 / 65.9, t<54 0.62 / 0.61, mean 162 / 165
    (uncalibrated 66.8 / 68.4, 0.66 / 0.52, 162 / 162); overnight background 30.4 / 35.3 (from 37-44; field 23.7) but
    overnight glucose still 170 / 160 (130). Glucose by hour (seed 0, uncalibrated): at 22:00 generated 168 vs field 177,
    then 169 / 160 / 147 / 141 at 0 / 2 / 4 / 6 h vs 150 / 142 / 129 / 128, with more insulin activity from 2 h on (1.27 /
    1.12 / 1.06 vs 1.12 / 0.98 / 0.80 U/h). More ICE than the background level shows pushes up overnight: likely the long
    generated meal tails (pulse ICE 3 h after a meal bolus 49 vs 35, LESSONS 88) from evening meals. Calibration not
    kept; v3m21 stays.
94. **Generated people eat more at night; behavior calibration by clock band fixes the entry profile but not the nights.**
    v3m21 seed 0, held-out, 00-06: meal grams 32.9 vs 23.5 g-eq a day (whole day 229 vs 196), at ordinary-to-high glucose
    (120-180: 13.2 vs 8.3, > 180: 9.3 vs 5.7; not rescues), meal starts per 6 h ~1.4x the field in every glucose band below
    180; unannounced starts 1.26 vs 0.96 a day, carb entries 0.22 vs 0.04. Night swap test: the meal head's expected night
    rate is LOWER on the rollout's own inputs (1.15 / day) than on real ones (1.28; actual 0.96), so the excess is in the
    head's daily profile, not closed-loop inputs. Teacher-forced on the 28 days before the hold-out (168 people): night
    entries expected 971 vs actual 408, meal starts 5110 vs 4904. calibrate_band.py fits pooled logit offsets per 6-h band
    for the meal and entry heads (seed 0: meal -0.04 / -0.08 / -0.05 / +0.07, entry -0.87 / -0.12 / +0.03 / +0.18); the
    plant applies them by local hour. Held-out seeds 0 / 1: TIR 67.9 / 68.5, t<54 0.64 / 0.54, mean 162 / 161 (uncalibrated
    66.8 / 68.4, 0.66 / 0.52, 162 / 162), within noise; night glucose unchanged (170 / 157 / 147 / 142 at 0 / 2 / 4 / 6 h vs
    field 150 / 142 / 129 / 128). Kept as part of the base (behavior profile closer, no regression). Overnight the excess ICE
    is split between meal pulses (20.6 vs 15.9 mg/dL/h) and background (31.9 vs 24.9).
95. **Insulin-needs dial sanity check: the generator moves the right way and is damped relative to frozen-ICE replay, as the
    field is.** Stock Loop, --candidate-insulin-needs 0.9 / 1.0 / 1.1, v3m21 seed 0 + clock-band behavior calibration (3
    runs), 24 held-out donors, clean time, median donor. Generator: TIR 63.7 / 67.9 / 70.6, t<70 1.64 / 2.16 / 2.89, t<54
    0.47 / 0.64 / 0.99, mean 166 / 162 / 155. Replay: 67.1 / 74.1 / 77.2, 0.28 / 0.99 / 3.99, 0.03 / 0.13 / 1.08, 166 / 153 /
    138. Both monotone and correctly signed; the generator responds about 70% (TIR), 50% (t<54), 40% (mean) of replay's
    amount: its person reacts to the dosing (more food, a stronger defense) where replayed ICE is frozen. The settings-edit
    test (LESSONS 63, 74, 96) puts the field's real change about where the generator predicts (slope ~0.95 for mean and
    t<70) and well below replay's prediction (0.39 / 0.48), so frozen-ICE replay likely overstates how much a dosing change
    moves outcomes. Requested via loopeval-algo with Pete's go.
96. **On real settings edits, v3m21 (+ clock-band behavior calibration) predicts the SIZE of the change about right for TIR,
    t<70 and mean glucose, on both seeds; t<54 still does not.** 61-62 edits, seeds 0 / 1, field change regressed on
    predicted change (slope 1 = right size): mean glucose slope 0.95 / 0.89, r 0.38 / 0.35 (replay 0.39, r 0.32); t<70 0.95 /
    0.91, r 0.53 / 0.43 (replay 0.48, 0.48); TIR 0.75 / 0.90, r 0.22 / 0.25 (replay 0.49, 0.24); t<54 0.22 / 0.28, r 0.22 /
    0.27, mean error 0.46 / 0.48 vs 0.30 for predicting no change (replay 0.09, 0.15). Earlier generators had slopes 0.16-0.85
    and TIR r 0.05-0.22 with seed-to-seed swings (LESSONS 63, 74). Correlations stay modest because the field's own change
    at an edit is mostly noise (sd 11.4 at edits vs 8.5 at random days); per-edit error is near the no-change baseline for
    the same reason. Frozen-ICE replay overstates every effect (slopes 0.09-0.49); with the insulin-needs check (LESSONS 95)
    this says a reacting person, not frozen ICE, is the right reference for dosing changes. Own-settings level still off
    (TIR -4.9 / -6.2 median).
97. **Per-person behavior offsets by clock band (fit_traits_band.py) are neutral; not kept. The slow overnight fall is not a
    behavior-rhythm problem.** On top of the pooled band calibration (LESSONS 94, which brought night entries to 0.08 a day
    vs 0.22 before and field 0.04, night meal grams 28 vs 33 and 23.5, but left night unannounced starts at 1.26 vs 0.96),
    each person's meal and entry offsets per 6-h band fitted by maximum likelihood on their training days. Seeds 0 / 1,
    held-out clean time: TIR 67.7 / 67.5, t<54 0.73 / 0.55, mean 162 / 161 (pooled band 67.9 / 68.5, 0.64 / 0.54, 162 /
    161); per-person t<54 pass rate 42 / 46% (50% if faithful); night glucose unchanged (168 / 155 / 146 / 143 at 0 / 2 / 4 /
    6 h vs field 150 / 142 / 129 / 128). Together with LESSONS 90 and 93 (level offsets, overall and by band): neither the
    background level nor the behavior rhythm, adjusted alone, makes generated nights fall as fast as the field's.
98. **The base had lost its closed-loop start-head calibration (LESSONS 23); restored, kept. Generated people were starting
    ~20% too many unannounced meals at every hour, and that, not the night rhythm, kept nights high.** v3m21 + pooled band
    calibration was calibrated on real inputs only. Held-out, seed 0: unannounced meal starts 4.8 vs 3.9 a day (139 vs 106
    g-eq), in every 6-h band; announced meals, pulse size, duration and peak all match. Overnight insulin effect matches
    the field (78 vs 75 mg/dL/h at 23 h); the field's glucose falls 23-02 h because evening ICE drops off (86 -> 53) faster
    than insulin, the generator's stays ~10 mg/dL/h higher (meal pulse and background both). calibrate_closed.py on
    rollouts of the 28 days before the hold-out: meal 4.80 vs 4.01 a day (offset -0.18), standalone boluses 3.48 vs 2.96
    (-0.16), entries and meal boluses within 5%. Seeds 0 / 1, held-out clean time (before -> after): TIR 67.9 / 68.5 ->
    69.0 / 69.0, t<54 0.64 / 0.54 -> 0.59 / 0.60, mean 162 / 161 -> 158 / 159, night glucose 161 / 162 -> 150 / 146
    (field 130), night background ICE 43 / 42 -> 37 / 37 (field 24). Every new base needs the closed-loop step, not only
    the teacher-forced one; the remaining night gap is in the background level (37 vs 24), not in meal counts.
    Change test on this base (tier 3c, 62 edits / 47 donors), seeds 0 / 1: slope of field on predicted change TIR 0.62 /
    1.21, t<70 0.97 / 1.00 (Spearman 0.42 / 0.41, was 0.30 / 0.30), mean 1.11 / 0.88; t<54 0.23 / 0.19, still no rank.
    Own-settings level TIR -2.2 / -6.2 (was -4.9 / -6.2).
99. **The engine stacks Loop's automatic dose on a plant bolus at the same decision; real, but not the cause of the excess
    lows after boluses.** (additive's handoff, 2026-10-15-simulator-plant-bolus-autodose.) Auto-bolus donor i001, seed 0,
    held-out: 89% of the person's calculator boluses get an automatic dose at the same decision (88 U on 265 U over 28
    days, median step total 1.38x the recommendation). Sending the bolus one step later does not help: an auto-bolus user
    gets an automatic dose at nearly every step, so the bolus always lands on a decision made without it (63 U on 209 U).
    Stopgap until the engine orders them (simulator's): auto-bolus donors ask for ratio - 0.4 (PLANT_AUTO_AF via rollout
    NET_AF; approximate for the three GBAF donors). Seeds 0 / 1, clean time: TIR 69.0 / 69.0 -> 69.1 / 69.9, t<54 0.59 /
    0.60 -> 0.61 / 0.59, mean 158 / 159 -> 159 / 159, insulin 36.2 / 36.4 -> 35.8 / 36.3 U/day; lows within 3 h of a meal
    bolus 0.354 / 0.342 -> 0.329 / 0.333 a day (field 0.214). Loop takes the extra back on the next cycles and half the
    held-out donors use temp basal. Within noise; flag off by default, not in the base. The post-bolus low excess
    (1.6x the field) is elsewhere.
100. **The change test is robust to the donors' RC mode.** simulator recovered each pilot donor's RC mode by era (handoff
    2026-10-15-frontier-rc-switches): the 24 held-out donors already matched, but 15 of the change test's 70 edits sit in an
    integral-RC or switching era that was replayed as standard. change_run.py now takes the RC mode per edit window from
    rc_mode.csv. Rerun, seeds 0 / 1: model slope TIR 0.62 / 1.21 -> 0.58 / 1.01, t<70 0.97 / 1.00 -> 0.99 / 0.86, mean
    1.11 / 0.88 -> 1.08 / 0.68, t<54 0.23 / 0.19 -> 0.17 / 0.12; replay TIR 0.49 -> 0.48. Within seed noise: both arms of
    an edit share the mode, so it cancels from the predicted change, as the handoff expected.
101. **Making the baseline explain background ICE on its own (v3m23) buys the post-bolus rise at the cost of the level; not
    kept at either weight.** Teacher-forced, v3m21's meal-locked rise sits in the recurrent path (baseline -12 at 10 min after
    a meal bolus), so closed loop loses it (total ICE at 30 min 101 vs 124 field). v3m23 adds AUX x Gaussian loss of the
    baseline alone against background ICE. Full chain (traits, band, closed loop), held-out clean time, seeds 0 / 1 (base
    69.0 / 69.0, t<54 0.59 / 0.60, lows per meal bolus 0.111 / 0.108; field 74.1 / 0.12 / 0.064):
    AUX 0.5: TIR 65.8 / 66.9, t<54 0.67 / 0.79, lows per meal bolus 0.077 / 0.099; the rise is there (background 63-64 at
    15-30 min, field 47 / 69) but post-meal background stays high (52 vs 43.5 at 3 h, afternoons 171-179 vs ~160); fed real
    inputs it overshoots after meals (66 vs 61 at 30 min, 59 vs 49 at 75): baseline and recurrent path both add the rise.
    AUX 0.1: TIR 69.0 / 69.0, t<54 0.65 / 0.77, lows per meal bolus 0.098 / 0.103, rise 51 at 30 min. The post-bolus
    lows track the rise only weakly; t<54 does not follow them.
102. **Engine 11d1b77 (plant bolus before the automatic dose, 8e86860 + f11386e) adopted as the harness; outcomes within
    noise.** Verified on i001: plant received 285.65 U = trace 285.65 U of person boluses; automatic dose at those steps
    88 -> 0.35 U; automatic boluses still reach the plant (as basal-type entries). Base v32of{0,1}TcB2C held-out: TIR 69.0 /
    69.0 -> 69.2 / 69.6, t<54 0.59 / 0.60 -> 0.63 / 0.55, mean 158 / 159 -> 159 / 157, lows per meal bolus 0.111 / 0.108 ->
    0.105 / 0.106 (as LESSONS 99's stopgap predicted).
103. **The closed-loop background offset below 90 mg/dL, applied after feedback, roughly halves the severe-low excess on the
    v3m21 base; kept.** The step kept on v23 (calibrate_closed_bg.py, offsets above 90 zeroed) had dropped out of the v3m21
    chain. Fitted from training-window rollouts on engine 11d1b77: field minus generated background ICE by input glucose,
    seed 0, <60 / 60-70 / 70-80 / 80-90: +15.4 / +4.8 / +1.7 / +0.2 mg/dL/h (seed 1 +13.4 / +6.3 / +2.6 / +0.5). Applied
    to the ICE the body sees after the draw is fed back (PLANT_BGBAND_AFTER=1; before feedback it would ride the deviation
    channel, LESSONS 89). Held-out clean time, seeds 0 / 1: t<54 0.63 / 0.55 -> 0.44 / 0.31, t<70 2.23 / 1.90 -> 1.95 /
    1.67, TIR 69.2 / 69.6 -> 69.4 / 70.1, mean 159 / 157 -> 160 / 159; chance a crossing below 70 reaches 54 0.33 / 0.33
    -> 0.25 / 0.26 (field 0.18); worst donor i003 t<54 5.2 / 6.5 -> 2.6 / 3.6. Lows per meal bolus unchanged (0.11 vs
    0.064): the offset deepens the response once low, not how often a bolus leads to one. New base v32of{0,1}TcB2CG.
    Change test on the new base (engine 11d1b77, RC per edit window), seeds 0 / 1: slope TIR 0.76 / 0.65, t<70 1.10 / 1.28,
    mean 1.10 / 0.62, t<54 0.35 / 0.32 (was 0.17 / 0.12), t<54 mean |error| 0.36 / 0.38 (was 0.47 / 0.50; predicting no
    change 0.30). t<54 changes now move with the field at a third of their size, still not ranking.
104. **The generator compresses people's background spread toward the population's; a per-person spread factor fitted on
    the training window does not fix it, not kept.** Base v32of0TcB2CG, held-out, sd of hourly-mean background ICE, generated
    / real: calm low-insulin people too wide (i050 1.28, i003 1.23, i009 1.13), volatile ones too narrow (i012 0.72, i010 0.73,
    i017 0.75); median 0.94, Spearman of the ratio with TDD -0.47, people's order kept (generated vs real 0.74). The excess
    lows after boluses sit in the same people (i003 alone ~30% of the excess, then i040, i009, i050, i054, i004; replay
    matches the field for each), and lows away from boluses match (field 0.33, generated 0.35 a day). calibrate_spread_person.py
    scales each draw's deviation from its predicted mean by real / generated on the 28 days before the hold-out (0.78-1.38):
    seeds 0 / 1 TIR 69.4 / 70.1 -> 68.0 / 66.0, t<54 0.44 / 0.31 -> 0.69 / 0.46, lows per meal bolus 0.111 / 0.107 -> 0.139 /
    0.124; the widened people became the worst (i044, i017). Real spread is a fairly stable trait (training vs held-out
    Pearson 0.71; across people sd of log 0.23, within person 0.13), but the generated / real ratio is not (Spearman 0.38
    between periods), and the draw-level factor maps onto hourly spread only loosely. The fix belongs in the model's own
    per-person scale.
105. **Each person's one-step background spread is already right; the compression toward the population is a closed-loop
    effect. v3m24 (per-person log-scale) dropped.** Teacher-forced on the base (v32of0TcB2C), the likelihood-best per-person
    shift of every component's log-sd is within +-10% for the most compressed people, training and held-out alike (i003
    0.99 / 1.03, i050 1.04 / 1.09, i012 1.10 / 1.10, i017 1.07 / 1.05, i010 1.02 / 1.05; NLL gain <= 0.005 nats a step).
    v3m24's per-person scale embedding barely moved in training (|log| <= 0.008), like every per-person scalar table here:
    each person's row gets a step only when they are in the batch. With the one-step scale right, a calm person's hourly
    spread running 1.2-1.3x real (and a volatile one's 0.7x) comes from how the generator's own deviations persist and add
    up over an hour in closed loop, not from the width of each draw.
106. **Generated background ICE keeps too much 30-min memory, most for calm people; feeding back only part of each draw
    collapses the spread instead of shortening the memory, not kept.** Base v32of0TcB2CG, held-out, autocorrelation of
    5-min background ICE at 30 min: median 0.111 generated vs 0.072 field; calm donors 0.12-0.17 vs about 0 (i050 0.12 vs
    -0.02, i003 0.12 vs 0.00, i009 0.17 vs 0.02), and the excess tracks the hourly-spread excess (Spearman 0.67). Persistence
    is only partly a trait: between people sd 0.045, within a person across 28-day periods 0.041 (period-to-period Pearson
    0.63-0.81). PLANT_FB_LAMBDA=0.5 (the background path reads back mean + 0.5 x (draw - mean), the body gets the draw):
    seeds 0 / 1 TIR 77.5 / 75.0, t<54 0.06 / 0.07, lows per meal bolus 0.060 / 0.057 (field 74.1 / 0.12 / 0.064) because the
    draws lost their spread: 5-min sd 22 / 20 vs 67 / 59 (field 56), 30-min autocorrelation 0.42 / 0.41 (field 0.07), one donor
    at TIR 18. Fed its own smoothed history, the head predicts narrower draws, which feed back smoother still. Outcome
    matches that come from a generator too smooth to hold the shape bar are not wins.
107. **Free-running training on v3m21 (FREERUN 0.5) fixes the 30-60 min memory but loses the 5-min structure, and post-bolus
    lows get worse; not kept.** v32oj{0,1} through the base's full chain on engine 11d1b77, held-out clean time, against the
    base v32of{0,1}TcB2CG: TIR 69.4 / 70.1 -> 68.5 / 72.4, t<54 0.44 / 0.31 -> 0.60 / 0.58, mean 160 / 159 -> 159 / 153,
    lows per meal bolus 0.111 / 0.107 -> 0.122 / 0.139 (field 0.064). Background-ICE autocorrelation at 30 min 0.07 / 0.04
    (field 0.07, base 0.11) but at 5 min 0.14 / 0.11 (field 0.40, base ~0.36), 5-min sd 72 / 69 (field 56): the draws became
    nearly white. Seed 1's night background fell to 31.5 (base 37.7, field 24) and its TIR rose, yet severe lows rose on
    both seeds. With LESSONS 106: the excess lows after boluses follow the 5-min structure, not the 30-min memory.
108. **The generator's plant snapped onto field glucose at every field disruption, several times a day; it now follows the
    field only through disruptions of an hour or more (PLANT_FOLLOW_MIN=60), base refit, outcomes within noise.** Generated
    5-min glucose changes had heavy tails (sd 12.3 vs field 7.3, 99th percentile |change| 35 vs 23 mg/dL; robust sd 5.6 vs 5.2)
    although the generator's own net force matched the field's (99th percentile 22.9 vs 23.0): ~5 a day (up to 25) steps
    where glucose did not follow the force, each the plant re-anchoring to the field reading on a disrupted step. 85% of
    disruption runs in the held-out windows are under 30 min (median 10, ~3.6 a day; i035 15, i006 13), short enough to
    stay inside the 30-min clean-time windows, so field glucose leaked into the scored outcomes and Loop saw the snaps as
    real moves. Following only runs of >= 60 min (the long pumpless stretches the rule was written for): without refitting,
    lows per meal bolus rose (0.111 / 0.107 -> 0.124 / 0.118) - the snaps had been pulling generated people back onto the
    field's track, not causing the lows. With the closed-loop start and low-band calibrations refit under it (v32of{0,1}TcB2FG):
    TIR 69.6 / 68.4, t<54 0.40 / 0.38, mean 157 / 158, lows per meal bolus 0.113 / 0.107 (old base 69.4 / 70.1, 0.44 / 0.31,
    160 / 159, 0.111 / 0.107). Kept as the harness: the same outcomes, now reached without borrowing the field's glucose.
109. **Generated people overshoot large bolus recommendations, but that is not what drives the lows after boluses.** Field
    calculator ratios (requested / recommended, bolus decisions) depend on the recommendation's size: rec <= 0.3 U 34% deviate
    (median deviator x6, topping up), 0.3-1 U 25%, > 2 U 14-15% (median x0.76-0.84, trimming; 95th percentile x1.17 at 2-4 U,
    x1.0 above). The ratio head never sees the recommendation: generated share > x1.5 9.3% vs field 2.2% (rec > 0.3 U), 95th
    percentile x2.43 vs x1.0. A quantile map onto the field's ratio-by-recommendation (PLANT_RATIO_MAP) was not a valid test:
    the plant knows only Loop's recommendation at the start of the step, ~35% below the one the bolus meets at the end (i001
    1.0 vs 1.56 U, i039 1.35 vs 1.99), so boluses landed in the small-rec bands and overshoot rose to 16.7%. The bound test,
    every calculator ratio capped at x1.2 (PLANT_RATIO_CAP), base v32of{0,1}TcB2FG: lows per meal bolus 0.113 / 0.107 ->
    0.118 / 0.108, TIR 69.6 / 68.4 -> 70.2 / 68.6, t<54 0.40 / 0.38 -> 0.40 / 0.33. Ruled out as the cause; a faithful
    ratio rule would need the engine to apply it at the recommendation it computes.
110. **Generated people take lone boluses at the wrong glucose: the head is flat where real people correct when high. Bolus
    heads calibrated by glucose band; kept.** Base v32of0TcB2FG, held-out: at a lone bolus (no entry within 15 min) glucose
    median 147 vs 193 mg/dL field, trend +8 vs +26 per 30 min, 19% vs 7% taken below 100; within a glucose band the chance of
    a low in the next 3 h is the field's (100-250 mg/dL), so the excess came from where the boluses fall. Fed real inputs the
    lone-bolus rate is flat across glucose (0.10-0.12 an hour at <100 / 100-140 / 140-180 / 180-250 / >250) against the
    field's 0.11 / 0.09 / 0.10 / 0.13 / 0.26. calibrate_bolus_bg.py: pooled logit offsets per glucose band on the lone- and
    meal-bolus heads, teacher-forced on the 28 days before each hold-out (lone, seed 0: -0.45 / -0.43 / +0.02 / +0.53 / +0.85).
    Held-out seeds 0 / 1: lows per lone bolus 0.138 / 0.138 -> 0.099 / 0.105 (field 0.075), t<54 0.40 / 0.38 -> 0.37 / 0.31,
    TIR 69.6 / 68.4 -> 69.0 / 70.1, mean 157 / 158 -> 156 / 157; lone boluses 2.57 / 2.6 -> 2.85 / 3.13 a day (field 2.29)
    - more time high now draws more corrections; the closed-loop count calibration is refit on top. Meal boluses unchanged:
    0.114 / 0.105 lows per meal bolus vs 0.064, at the same glucose 1.5-2x the field's.
    Closed-loop start counts refit on top (v32of{0,1}TcB2FGUC): lone boluses 2.58 / 2.66 a day (field 2.29), TIR 69.8 / 70.0,
    t<54 0.42 / 0.35, mean 156 / 158, lows per lone bolus 0.106 / 0.112, per meal bolus 0.118 / 0.111; per-person t<54 pass
    rate 50 / 54% (was 38 / 50%, 50% if faithful). New base.
111. **After a meal bolus the field's meal hits early and fades; the generator's plateaus. A closed-loop meal-response kernel
    lowers post-bolus lows only through the food it adds; not kept.** Base v32of0TcB2FGUC, held-out, event average after a
    meal bolus: total ICE 86 / 123 / 122 / 110 / 103 mg/dL/h at 0 / 30 / 45 / 75 / 105 min (field) vs 85 / 100 / 106 / 108 /
    109 (generated); insulin action within 5 (ISF x activity 107 vs 112 at 60 min); field glucose +19 at 45 min and +24 at 75,
    generated +7 and +5. calibrate_meal_kernel.py (TOTAL=1): field minus generated total ICE after a meal bolus, 28 days
    before the hold-out, applied after each generated meal bolus to the ICE the body sees. Seeds' fitted shapes differ (seed
    0: +16 at 30 min then -5..-15 to 3 h; seed 1: +25 at 30 min, zero after 60). As fitted: lows per meal bolus 0.170 / 0.079
    (base 0.118 / 0.111, field 0.064), t<54 0.65 / 0.28 - the negative tail hurts. Early positive part only (first 60 min):
    0.099 / 0.079, t<54 0.35 / 0.30, t<70 1.74 / 1.47 (base 2.07 / 1.77), but TIR 69.2 / 68.0 (base 69.8 / 70.0), mean +2 / +3.
    The same early part with its area (6 / 11 mg/dL) taken back evenly over 1-4 h: 0.109 / 0.103, t<54 0.40 / 0.33, TIR 69.7 /
    68.8 - neutral. The low reduction came from net food per meal bolus, not the timing, at a TIR cost.
112. **Change test on the honest harness: effect sizes a little larger, glucose-band bolus calibration neutral; seed noise
    dominates.** Slope of the field change on the predicted, seeds 0 / 1 (TIR, t<70, mean, t<54): v32of TcB2CG (field
    snaps on) 0.76 / 0.65, 1.10 / 1.28, 1.10 / 0.62, 0.35 / 0.32; TcB2FG (follow-min 60) 0.89 / 0.54, 0.96 / 1.18, 0.80 /
    0.45, 0.39 / 0.15; TcB2FGUC (+ bolus heads by glucose band) 0.57 / 0.65, 0.93 / 1.20, 0.74 / 0.48, 0.24 / 0.30. The
    seed-to-seed range of a slope (~0.35) exceeds the differences between the two newer bases; against the old one, the mean
    slope falls (0.86 -> 0.61-0.63 averaged) and predicted spread rises (sd 5.9-7.4 -> 7.7-8.9 mg/dL): without the snaps
    onto the field, generated effects come out larger. t<54 mean |error| 0.40-0.42 vs 0.30 for predicting no change. The
    honest harness and the bolus calibration both stay; deciding between candidates on this bar needs more seeds per arm.
    Averaging the two seeds' predictions per edit (ensemble), slope TIR / t<70 / mean / t<54: snaps on 0.81 / 1.32 / 0.92 /
    0.49; honest 0.81 / 1.22 / 0.71 / 0.39; honest + bolus 0.75 / 1.15 / 0.71 / 0.33 (replay 0.50 / 0.47 / 0.44 / 0.10).
    t<54 changes come out 2-3x too large on every base, in step with generated t<54 running ~3x the field's level.
113. **A second pass of the low-band background calibration on the current base is close to a fixed point; small gain,
    kept.** Training-window rollouts of v32of0TcB2FGUC: field minus generated background below 90 mg/dL +2.2 / -0.9 / +2.6 /
    +0.9 (<60 / 60-70 / 70-80 / 80-90), added to the table. Held-out seeds 0 / 1: t<54 0.42 / 0.35 -> 0.39 / 0.27, t<70 2.07 /
    1.77 -> 1.79 / 1.64, TIR 69.8 / 70.0 -> 69.6 / 70.4, lows per meal bolus 0.118 / 0.111 -> 0.113 / 0.114. New base
    v32of{0,1}TcB2FGUCG. The same table shows background 10-12 mg/dL/h low above 250 (37 vs 30, 44 vs 33): left out, a
    high-band offset ran glucose away before (LESSONS ~33).
114. **The generator's remaining TIR and low gap belongs to people who log carbs; drawn people with their host's settings
    match the population's spread.** (a) Drawn people (DRAW_PERSON) ran a random other person's vector on the host's Loop
    settings and ISF, so they were mis-set: t<54 10/50/90th 0 / 0.44 / 3.04 (real 0 / 0.12 / 0.55), TIR 35 / 68 / 81 (52 /
    74 / 89). DRAW_MODE=self (a new person jittered around the host, settings fitting them as a real person's do): t<54 0 /
    0.36 / 1.38, TIR 58 / 70 / 84, insulin 9.6 / 34 / 53 (9.5 / 33 / 51), and TIR-insulin / mean-insulin co-variation now the
    field's (-0.36 / +0.30 vs -0.40 / +0.32). Still inverted: carb entries vs t<54 +0.29 (real -0.31), vs TIR -0.01 (+0.36).
    (b) The same holds for the real people's own runs (base v32of0TcB2FGUCG, thirds by field entries a day): few (1.0) field
    t<54 0.30 / TIR 66.8 vs generated 0.50 / 71.8; middle (5.5) 0.09 / 78.9 vs 0.56 / 68.5; many (9.9) 0.10 / 74.5 vs 0.33 /
    66.8. TIR shortfall vs entries Spearman -0.56. Non-announcers are already slightly too easy; the whole gap is in
    announced meals (entry, bolus, and the meal ICE behind them).
115. **Announced meals arrived too late and too big for their entries; mapping the entry-to-food delay onto the field's and
    scaling each person's meal size to their own entries closes the mean and half the TIR gap; kept.** Field announced meals
    (held-out, 24 hosts): logged before eating 51% (food a median 19 min after the entry, 90th percentile 50), after 49%
    (median 20 min late). Generated: entry-started meals 62%, food a median 34 min after the entry (90th 119); entries
    joining a meal already started 17% (median 35 min late); the delay head models only offsets >= 0 and draws them wide.
    Pulse size / entered grams is a personal trait (per-donor medians 1.2 over all donors, 1.46 for these hosts) and the
    generator's runs ~1.3x it (median 1.93). PLANT_EOFF_MAP (build_eoff_map.py): drawn delay quantile-mapped onto the field's
    delays for meals logged first (pre-hold-out, median 21.6, 90th 51). Alone, seeds 0 / 1: lows per meal bolus 0.113 /
    0.114 -> 0.096 / 0.099, but TIR 69.6 / 70.4 -> 69.7 / 68.2 (meals now land on time and are too big). A pooled size map
    (all donors, median 1.18) shrank these hosts' meals too far: TIR 74.9 / 75.3, mean 148 / 150, lows per meal bolus 0.153 /
    0.129. Per person instead (PLANT_SIZE_PERSON, build_size_person.py: field / generated median ratio on the 28 days before
    the hold-out, clip [0.5, 2], median x0.95): TIR 72.2 / 72.2, mean 152 / 153 (field 152), t<54 0.36 / 0.31, t<70 1.75 /
    1.79, lows per meal bolus 0.114 / 0.106; per-person TIR pass rate 8 / 17% -> 25 / 29%. New base: v32of{0,1}TcB2FGUCG +
    PLANT_EOFF_MAP + PLANT_SIZE_PERSON. Not yet modeled: eating before logging (49% of field announced meals vs 17%).
    Change test on the new base (two seeds' predictions averaged per edit): slope TIR 0.72, t<70 1.33, mean 0.73, t<54
    0.52 (previous base 0.75 / 1.15 / 0.71 / 0.33), t<54 |error| 0.36 vs 0.30 for no change. Per-person size factors exist
    only for the 24 test hosts; the change test's other donors ran at 1.0.
116. **Turning a share of logged-first meals into eat-first meals (food now, entry and bolus after the field's lag) makes
    both highs and lows worse; not kept.** Field announced meals: 49% logged after eating starts (lag median 24 min, 90th
    percentile 62, pre-hold-out); generated 17% (entries joining a meal already started). PLANT_EATFIRST=0.35 on entry-started
    meals, new base: seeds 0 / 1 TIR 72.2 / 72.2 -> 70.6 / 70.3, t<54 0.36 / 0.31 -> 0.42 / 0.37, lows per meal bolus 0.114 /
    0.106 -> 0.123 / 0.112, mean 152 / 153 -> 153 / 155. Real eat-first meals differ from logged-first ones in more than
    timing (field, pre-hold-out, medians, logged-first vs eat-first): pulse 36 vs 37 g-eq, entry 35 vs 30 g, pulse / entry
    1.08 vs 1.31, glucose at onset 129 vs 118, peak 40 vs 50 min, bolus 3.45 vs 2.90 U - started lower, logged smaller,
    dosed less. A timing-only swap keeps the logged-first meal's entry and bolus.
117. **The remaining TIR gap is in middle loggers, with a different cause per donor; a per-person background level offset
    trades it for lows again, not kept.** New base by thirds of field entries a day: heavy loggers now match (TIR 73.7 / 75.0
    vs 74.5), few-entry people a little easy, middle (5.5 a day) 66.2 / 68.8 vs 78.9, mean 161 / 160 vs 141; replay matches
    every one. Worst three: i008 background 43.7 vs 27.5 mg/dL/h; i017 meal food 368 vs 280 g-eq a day (size factor 1.25);
    i061 carbs entered 59 vs 117 g a day. calibrate_level.py on the 28 days before the hold-out (offset median +2.2, i008
    +16.7, i061 +10.2), applied after feedback: TIR 72.2 / 72.2 -> 74.8 / 71.9, t<54 0.36 / 0.31 -> 0.53 / 0.41, lows per
    meal bolus 0.114 / 0.106 -> 0.150 / 0.134. As in LESSONS 90, lowering a person's background level buys TIR with lows.
    Some per-donor gaps are the person changing between periods: i061 entered 52 g a day in its training window (generated
    68) and 117 in the held-out month. Grams per entry match the person in the training window (Spearman 0.87 over donors,
    generated / field median 0.97); there is nothing to calibrate there.
118. **Night level offsets by clock band work once the low-band background is refit on top of them; kept, with a cost in
    time below 70.** On the new base, per-person clock-band offsets after feedback (calibrate_level_band.py, 28 days before
    the hold-out; median -7.5 / -2.6 / -1.0 / +5.3 mg/dL/h at 00-06 / 06-12 / 12-18 / 18-24) bring nights to the field's
    (2 / 4 am 142-146 / 135-138 vs field 142 / 129; base 153-158 / 147-149), but alone t<54 rises 0.36 / 0.31 -> 0.49 / 0.38:
    the low-band offsets were fitted at the old level. Two more passes of calibrate_closed_bg (below 90) on top (shift after
    the second +1..+6, offsets settle at <60 / 60-70 / 70-80 / 80-90 +21 / +10 / +8 / +8 and +28 / +8 / +5 / +5): seeds 0 /
    1 TIR 72.2 / 72.2 -> 74.1 / 72.7, mean 152 / 153 -> 148 / 151, t<54 0.36 / 0.31 -> 0.37 / 0.25, t<70 1.75 / 1.79 -> 1.87 /
    2.08, lows per meal bolus 0.114 / 0.106 -> 0.133 / 0.122; per-person pass rate mean 21 / 25% -> 38 / 42%, TIR 25 / 29%
    -> 33 / 29%, t<54 38 / 50% -> 42 / 46%. Kept on the primary pair (TIR up, t<54 level or down); t<70 and post-meal-bolus
    lows are worse. New base v32of{0,1}TcB2FGUCGLBGG (+ PLANT_EOFF_MAP, PLANT_SIZE_PERSON).
    Change test on the new base (two seeds averaged per edit): slope TIR 0.63, t<70 1.34, mean 0.62, t<54 0.48, t<54 |error|
    0.34 (previous base 0.72 / 1.33 / 0.73 / 0.52, 0.36; no-change baseline 0.30). Within seed noise of the previous base.
119. **On the new base the early meal surge still trades TIR for lows; not kept.** After a meal bolus the base now matches
    the field's insulin action (ISF x activity 106 vs 107 at 60 min) and the meal's tail, but not the early surge (ICE 98 /
    106 vs 123 / 122 at 30 / 45 min; glucose +10 vs +24 at 75 min; 22% vs 14% of meal boluses below 70 within 4 h). The
    early-positive kernel of LESSONS 111 on v32of{0,1}TcB2FGUCGLBGG: per-seed fits (6 / 11 mg/dL of food) TIR 74.1 / 72.7 ->
    73.4 / 69.7, t<54 0.37 / 0.25 -> 0.31 / 0.23, lows per meal bolus 0.133 / 0.122 -> 0.111 / 0.084; averaged kernel (8.3
    mg/dL) for both seeds: TIR 72.4 / 70.8, t<54 0.33 / 0.18, t<70 1.74 / 1.72 (base 1.87 / 2.08), lows per meal bolus 0.106 /
    0.090, mean 152 / 155; per-person TIR pass 33 / 29% -> 29 / 12%. t<54 moves toward the field and TIR away from it by the
    same food.
120. **The refitted meal-shape labels (ice_v32f) make the current architecture worse too; not kept.** v3m21 trained on
    ice_v32f (v32fl0) through the base's whole chain on the current harness, held-out seed 0: TIR 72.2 (base 74.1), t<70
    3.65 (1.87), t<54 0.64 (0.37), mean 146 (148), lows per meal bolus 0.190 (0.133). Pulse ICE after a meal bolus now rises
    early (57 / 67 / 69 mg/dL/h at 30 / 45 / 60 min) but falls off by 105 min (52), and the background carries no early rise
    (37 at 30 min): the meal's ICE ends sooner than the bolus insulin. Same direction as on v3m10 (LESSONS 54, two seeds);
    seed 1's chain was interrupted and not rerun given the size of the effect (t<70 2x, post-meal-bolus lows +43%).
121. **Generated people's eating barely responds to glucose falling, and they eat too often while it rises; the meal-start
    head calibrated by glucose band x trend in closed loop, kept.** Base v32of0TcB2FGUCGLBGG, held-out, meal starts per hour
    by glucose and 15-min change (> 10 mg/dL down / flat / up): 80-100 field 0.83 / 0.29 / 0.09, generated 0.54 / 0.34 /
    0.24; < 80 1.03 / 0.44 / 0.14 vs 0.67 / 0.50 / 0.40; 100-130 0.60 / 0.23 / 0.06 vs 0.44 / 0.28 / 0.20; 130-180 rising 0.04
    vs 0.18. Falling raises the field's rate 2.3-2.8x, the generator's 1.3-1.6x. calibrate_closed_state.py (already in the
    plant, absent from the chain): shifts on the 28 days before the hold-out, falling > 2 mg/dL/min at 70-110 +0.46-0.48,
    rising 70-110 -0.83 to -1.0. Held-out seeds 0 / 1: t<54 0.37 / 0.25 -> 0.31 / 0.21, t<70 1.87 / 2.08 -> 1.66 / 1.80, TIR
    74.1 / 72.7 -> 73.1 / 73.1, mean 148 / 151 -> 149 / 152, lows per meal bolus 0.133 / 0.122 -> 0.131 / 0.121. New base
    v32of{0,1}TcB2FGUCGLBGGS. Lows after meal boluses still ~2x: the fall-response fix helps lows elsewhere.
    A second pass does not converge (shifts again +0.40 falling / -0.84 rising at 70-90) and is within noise: TIR 73.8 /
    73.6, t<54 0.31 / 0.21, t<70 1.83 / 2.01, lows per meal bolus 0.135 / 0.123; not kept. The field's starts include
    logged meals while the offset moves only the unannounced-meal head, so the gap it measures is not all its own to close.
122. **Counting only unannounced starts on both sides gives a cleaner trend calibration but loses the low improvement; the
    all-starts version stays.** UNANN=1 (calibrate_closed_state.py): smaller shifts (fall > 2 at 70-90 +0.31, rising -0.41 to
    -0.81; < 70 already matched). Held-out seeds 0 / 1: TIR 74.7 / 73.3, t<54 0.38 / 0.24, t<70 1.96 / 2.13, mean 146 / 152
    (all-starts version 73.1 / 73.1, 0.31 / 0.21, 1.66 / 1.80; none 74.1 / 72.7, 0.37 / 0.25). The stronger shift works by
    making unannounced eating while falling stand in for falling-glucose eating the generator under-draws among announced
    snacks too; a cleaner fix would condition the entry head on trend as well.
    Carb entries are also under-drawn while falling (< 100 mg/dL: field 0.40 / 0.22 an hour falling / flat, generated 0.27 /
    0.20; 70-90 falling fast 0.89 vs 0.26). The entry head calibrated by glucose x trend (HEAD=entry; shift +1.0 / +0.87 at
    70-90 / 90-110 falling fast, plant calib_entry_state) on top of the unannounced-only meal shifts: seeds 0 / 1 TIR 73.9 /
    74.0, t<54 0.44 / 0.28, t<70 1.89 / 1.87 - TIR up, lows up; not kept. Entries made below 100 mg/dL while falling: field
    232, median 15 g, 24% with a bolus within 15 min; generated (base, seed 0) 517, 16 g, 39% bolused. More entries while
    falling add bolused ones; the bolus-given-entry head needs the same state dependence.
    The bolus-given-entry head by glucose x trend as well (calibrate_bwith_state.py; field entries made falling fast are
    bolused 13-30%, flat or rising above 90 mg/dL 75-82%; shifts -0.39 to -0.91 falling, up to +0.5 otherwise), with the
    entry and unannounced-meal shifts: TIR 73.5 / 73.5, t<54 0.39 / 0.27, t<70 2.04 / 1.95 - still behind the all-starts
    meal-head shift alone (73.1 / 73.1, 0.31 / 0.21, 1.66 / 1.80); not kept. Of the trend calibrations tried, the cruder
    one is the best on lows; the per-head versions do not add up to it.
    Change test on the new base (two seeds averaged per edit): slope TIR 0.88, t<70 1.27, mean 0.68, t<54 0.63 (Spearman
    0.32), t<54 |error| 0.33 (no-change baseline 0.30); previous base 0.63 / 1.34 / 0.62 / 0.48 (0.23), 0.34. Best t<54
    change prediction so far.
123. **On the falling-glucose meal-start base the averaged early meal surge no longer costs TIR; kept.** The averaged
    kernel of LESSONS 119 (8.3 mg/dL of food, both seeds) on v32of{0,1}TcB2FGUCGLBGGS, held-out clean time, seeds 0 / 1
    (base in brackets; field TIR 74.1, t<54 0.12, t<70 0.86, mean 152): TIR 73.4 / 72.5 (73.1 / 73.1), t<54 0.24 / 0.16
    (0.31 / 0.21), t<70 1.57 / 1.50 (1.66 / 1.80), mean 152 / 153 (149 / 152), lows per meal bolus 0.103 / 0.094 (0.131 /
    0.121; field 0.064). Per-person pass TIR 29 / 21% (29 / 33), t<54 25 / 46% (33 / 33), mean 33 / 38% (29 / 33); the
    worst TIR donor, i044 (field 83, generated 62-66), is the same in both. Change test, two seeds averaged per edit: slope
    TIR 0.91, t<70 1.29, mean 0.68, t<54 0.66 (Spearman 0.40), t<54 |error| 0.32, t<70 |error| 1.20 (base 0.88 / 1.27 /
    0.68 / 0.63 (0.32), 0.33, 1.23; no-change 0.30, 1.41). On the old base the falling-glucose eating the generator lacked
    left meal-surge food to land on top of lows; with it calibrated, the surge's food fills the early rise instead.
    New base v32of{0,1}TcB2FGUCGLBGGSKa. Ensemble scorer: runs/2026-10-13-ice-change/score_ens.py.
124. **The per-person glucose gap is persistent and pulls people toward the population, but the meal labels' blind time
    explains little of it; three corrections, none kept.** Base v32of{0,1}TcB2FGUCGLBGGSKa, held-out clean time: generated
    minus field mean glucose per person correlates 0.93 between seeds (sd 14, |gap| 10.5 mg/dL), and its train-window value
    predicts the held-out one (Pearson 0.74-0.78, slope 0.85-0.92), so it is the generator, not the person changing. It
    tracks the total-ICE gap (0.75) and the hourly ICE spread (generated / field sd of 1-h means vs glucose gap 0.47-0.53;
    across people generated on field slope 0.52-0.54), not the background level, which calibrate_level_band already
    matches. One cause found: the meal target is 0 on every slot, but meals are labeled only where ICE is observed, so
    excluded time (i056 66% of its training window, i012 49%) reads as no meal; labeled pulses on observed slots are 1.0-2.8x
    their all-time mean. (Comparing pulses on observed slots only, as a first cut did, wrongly showed most people under-fed:
    generated meal food per day matches the labels, Pearson 0.86, slope 0.84.) Tests, seeds 0 / 1, against the base (TIR
    73.4 / 72.5, t<54 0.24 / 0.16, t<70 1.57 / 1.50, |gap| 10.5): (a) per-person unannounced meal-start rate matched on
    observed slots from train-window rollouts (calibrate_meal_seen_person.py; i012 +0.68, i056 +0.47, i039 -0.47): TIR 74.0
    / 72.5, t<54 0.25 / 0.15, t<70 1.73 / 1.76, |gap| 8.9 (i012 -17 -> +6) - the cuts for mostly-observed people add lows;
    (b) the meal trait refit by maximum likelihood on observed training steps, delta added (trait_meal_seen.py; median
    +0.14, up to +1.4 for the least observed): TIR 72.1 / 71.4, t<54 0.18 / 0.20, mean 152 / 154, |gap| 9.8; (c) (b) with the
    median removed: TIR 73.2 / 71.9, t<54 0.26 / 0.23, |gap| 9.9. The proper fix (meal target unknown where ICE is not
    observed, retrain) is owed on the next retrain; on these numbers it will not close the gap.
125. **A ratio bolus meeting a zero recommendation delivers nothing; turning it into the units draw is neutral, not kept.**
    The bolus mode label is the recommendation on screen (ratio only above 0.05 U, dataset_v3m), which the bolus head does
    not see: on the base v32of0TcB2FGUCGLBGGSKa 17% of generated person boluses are ratio boluses at a zero recommendation
    and deliver 0 U (field: every recorded bolus delivers; 23% of field boluses and 20% of generated are units-mode).
    PLANT_ZERO_UNITS=1 gives those the head's own units draw. Held-out seeds 0 / 1 against the base (TIR 73.4 / 72.5,
    t<54 0.24 / 0.16, t<70 1.57 / 1.50): as is 74.4 / 71.4, 0.27 / 0.23, 1.63 / 1.74; with the low band refit under it
    (calibrate_closed_bg below 90, offsets +21 / +16 / +8 / +8 and +28 / +13 / +5 / +5) 74.1 / 72.2, 0.23 / 0.18, 1.50 /
    1.71, lows per lone bolus 0.112 / 0.144 (base 0.115 / 0.132; field 0.075). Method note: counting field boluses from
    steps.bolus_manual_u > 0 overcounts several-fold (i044 11.6 a day against 2.2 recorded decisions; i003 26.8 vs 25.7);
    against bolus_decisions.parquet generated attempts match the field per person, so the "fewer, larger boluses" seen
    with the step count was the count, not the generator.
126. **Generalization on the current base: drawn people's lows now near the real spread, one co-variation still inverted;
    the post-bolus low excess is time spent near low, not the bolus.** (a) DRAW_MODE=self on v32of{0,1}TcB2FGUCGLBGGSKa (72
    drawn per seed vs the 24 real hosts), 10th / 50th / 90th: t<54 0 / 0.23 / 0.89 and 0 / 0.12 / 1.36 (real 0 / 0.12 /
    0.55; LESSONS 114 base 0 / 0.36 / 1.38), TIR 55 / 72 / 88 and 45 / 67 / 86 (52 / 74 / 89), insulin 9.5 / 34 / 53 (9.5 /
    33 / 51); corrections a day 0.3 / 1.5 / 5.5 (0.4 / 1.1 / 3.6). Real people who enter more carbs have fewer severe lows
    and more time in range (Spearman -0.31, +0.36); drawn +0.17-0.20 and -0.08-+0.03; the hosts' own runs are in between
    (t<54 -0.06-0.04, TIR +0.21-0.25). (b) Lone person boluses (no entry within 15 min), seed 0, against bolus_decisions:
    fewer than the field in every glucose band (1.4 vs 2.4 a day), smaller (median 0.21 vs 0.60 U below 90), as often near a
    meal start (below 90: 49% vs 58% within -30..+60 min), but followed by a low within 3 h more often (below 90 58% vs 20%,
    90-120 32% vs 22%). The chance of going below 70 within an hour from a given band matches the field (70-80 0.40 vs 0.38,
    80-90 0.18 vs 0.18, 90-100 0.09 vs 0.08), while generated people spend 36% more time at 70-90. So the excess lows come
    from how often a person is near low - the calm-people spread of LESSONS 104-106 (i003 alone t<70 12.5 vs 3.6) - not from
    what a bolus does or from the defense once there.
127. **The background path's excess 1-3 h persistence is its own, not closed loop's, and it is not the previous-value
    channel feeding back draws.** Open loop (openloop_vt.py): the background path run 7 held-out days on its own draws with
    every other input real, variance-time ratio Var(sum of k steps) / (k Var) on observed slots, 24 donors, base
    v32of0TcB2FGUCGLBGGSKa, three sampling seeds: 30 min 2.25 / 2.04 / 2.04 (field 2.03), 1 h 2.74 / 2.79 / 2.67 (2.13), 3 h
    4.81 / 4.98 / 5.15 (3.60); 5-min sd 69-76 (79); closed-loop rollouts 4.65 at 3 h against the closed-loop field's 2.76.
    Per-donor values move by up to +-1.5 at 3 h between sampling seeds, so single-seed per-donor reads are noise. Feeding the
    previous-value channel the predicted mean instead of the draw (8 donors) raises the 3 h ratio from 3.9 to 8.7 and halves
    the sd (37 vs 70): the draw's noise decorrelates the path rather than building persistence. The EMA channel is not an
    input of the background path (ICE_DROP), so ema_mean equals draw exactly. The excess therefore sits in the recurrent
    state's own slow drift beyond an hour.
128. **Pre-window bolus decisions were labelled as corrections at a clamped glucose (additive handoff 2026-10-21).**
    bolus_decisions.parquet starts 7 days before the export window; meals.label turned every unmatched row before the first
    step into a correction with bg = the first step's glucose. Fixed in meals.label (unmatched rows outside the steps are
    skipped; a pre-window bolus that matches a meal still attaches). Against HEAD: meals unchanged; corrections i003 502 ->
    463, i044 123 -> 109, i012 361 -> 290 (62 rows at one bg), median correction glucose i044 151 -> 185, i012 90 -> 234.
    Takes effect on the next relabel and retrain, with the meal-target mask owed from LESSONS 124.
    The v3m21 training targets do not read the correction labels: the fix reaches only the plant and calibrate_closed.
129. **Correcting 127: feeding the background path its own draws through the previous-value input does build the excess
    persistence.** openloop_vt.py OL_MODE=tf (teacher forcing: the previous-value input gets the real value, the path still
    draws) against draw on the same base and donors: the deviation part's 3 h variance-time ratio 5.06 -> 3.01, the total
    4.81 -> 2.51 (field 3.60). The exogenous baseline alone (3 h ratio 8.77, sd 19) moves too slowly to carry it. 127's
    prev_mean test swapped the draw for the predicted mean, which removes the draw's noise as well, so it could not separate
    the two. The persistence is therefore the closed recursion through the previous value, the same family as LESSONS 86
    (self-feeding 30%) and 107 (FREERUN), both not kept; a fix has to train the path on its own draws without losing the
    level, not drop the channel.
130. **Meal-target mask (MEALMASK=1, LESSONS 124) through the full chain: not kept; change prediction worse.** v3m21
    retrained with meal = unknown wherever ICE is unobserved (v32om0/1, gamepc), then the base's 13-step calibration
    chain (side files rebuilt from om0 train-window rollouts). Held-out, clean time, seeds 0 / 1 against the base (TIR 73.4
    / 72.5, t<70 1.57 / 1.50, t<54 0.24 / 0.16, mean 152 / 153): 72.0 / 71.9, 1.47 / 1.85, 0.22 / 0.28, 152 / 150; median
    per-person |mean gap| 10.2 / 10.0 against 7.8 / 6.1. The donors it targets move unevenly: i056 -27 -> -21, i012 -16 ->
    +15; i044 +30 unchanged. Settings-edit change test (62 edits), two-seed ensemble, r against the base ensemble: TIR 0.16
    (0.27), t<70 0.51 (0.55), t<54 0.22 (0.26; Spearman 0.21 against 0.40), mean 0.30 (0.32); per seed TIR r 0.14 / 0.15
    against the base's 0.30 / 0.21. The calibration chain absorbs the meal-rate difference (generated 5.43 vs labeled 4.01
    a day before F), so what the mask changes is where meals fall, and the net loses rank on t<54. Method: the chain now
    runs on gamepc (chain_pc.sh, engine 11d1b77 built for Linux); one donor's replay reproduces the Mac's bit for bit and
    its model run within 0.001 mg/dL, so PC and Mac arms compare directly.
131. **Averaging more trainings does not sharpen change prediction: past two, the error is the model's, not training
    noise.** Two more trainings of the base recipe (v32of2/3, same v3m21 recipe, seeds 2-3) through the full 13-step chain
    on gamepc, then the 62-edit change test. Held-out clean time: TIR 74.1 / 74.6, t<70 2.04 / 1.90, t<54 0.39 / 0.35, mean
    149 / 149, |mean gap| 7.9 / 6.2 (of0/1: 73.4 / 72.5, 1.57 / 1.50, 0.24 / 0.16, 152 / 153, 7.8 / 6.1), so t<54 spread
    between trainings of one recipe is about 2x. Change test, r against the field averaged over every subset of the four
    trainings, by subset size 1 / 2 / 3 / 4: TIR 0.23 / 0.25 / 0.26 / 0.26, t<70 0.52 / 0.55 / 0.56 / 0.57, t<54 0.24 /
    0.24 / 0.25 / 0.25 (Spearman 0.30 / 0.34 / 0.36 / 0.36), mean 0.34 / 0.35 / 0.36 / 0.36; TIR slope 0.80 / 0.91 / 0.96 /
    0.99, mean |error| 7.91 / 7.86 / 7.86 / 7.85 (zero 7.78). Yet the predictions are stable: two-training averages agree
    with each other at r 0.84 (TIR), 0.87, 0.81, 0.84 (single trainings 0.69, 0.76, 0.55, 0.78). Averaging removes the
    training noise and leaves the field correlation flat at about 0.26 against a field-noise ceiling near 0.66 (LESSONS
    change-test notes), so what limits it is shared by every training of the recipe: the model's structure or calibration,
    not its seed. Two trainings stay the working ensemble; the next lever is structural (the previous-value recursion,
    LESSONS 129).
132. **Change prediction is limited by per-person level error on donors who never got a level band; and a caveat on 129.**
    (a) On the 62-edit change test (of0/1 ensemble), 57 edits are on trained donors who are not among the 24 hosts and so run
    on calib_level_band['_median']: their own-settings arm misses the field's pre-window TIR by a median 7.5 points (hosts
    3.4; replay 0.6), the miss is the same in both trainings (r 0.95 across of0/of1), and their predicted change correlates
    with the field at r 0.11 against 0.66 on the five host edits. Over all edits, |level error| and |change error| correlate
    (Spearman 0.24); the half with the smaller level error predicts at r 0.40, the other half 0.19. Edits with larger settings
    moves predict better (r 0.36 vs 0.06). Field TIR change itself tracks the edit only weakly (Spearman 0.15 with a
    more-insulin axis log basal - log ISF/2 - log CR/2, against 0.54 for the model's prediction): most of what moves the
    field across an edit is not the settings. Next: a level band for every change-test donor from their own train-window
    rollouts, as the hosts have (runs/2026-10-23-ice-lball/). (b) 129's teacher-forced comparison is weaker evidence than
    it read: fed the real previous value, the output is a one-step prediction series, whose long-lag variance is below
    the real series' even for a perfect model (the real series carries the covariance between past innovations and later
    means that independent draws drop). So tf below the field (2.51 vs 3.60) is expected, and only free-running against the
    field (4.81 vs 3.60) shows the excess; the excess is the free-running dynamics, which 129's conclusion still holds.
133. **The change test is near its noise ceiling on insulin and underpowered on TIR.** Per edit, field change in insulin
    delivered (U/day, CGM steps outside disruptions, post - pre) has sd 6.35 across the 62 edits against 5.79 across 162
    pseudo-edits on the same donors: the edits carry about 2.6 U/day of signal, so a perfect predictor correlates at about
    0.41. The base predicts it at r 0.24 / 0.32 (of0 / of1; slope 0.74 / 0.55; insulin_change.py), carbs entered r 0.07 /
    0.23 (field sd 26 g/day against a predicted 3-4: entries move with things the settings are not). TIR's ceiling is about
    0.67, and with 62 edits r has a standard error near 0.12, so variants within about 0.15 of each other cannot be told
    apart on this test. Only 5 of the 70 screened edits fall on the 38 untrained pilot donors; a sharper test needs more
    edits (a wider donor pull) or longer windows, not more seeds.
134. **A level band for every change-test donor does not fix their level or their change prediction, not kept; the
    per-person TIR bias is excess glucose variability, not a background offset.** lb_rollouts.py + lb_many.py
    (runs/2026-10-23-ice-lball/): train-window rollouts (3 seeds) for the 43 change-test donors without a band, offsets set
    as for the hosts (median shift from '_median' -0.4 / +2.7 / -5.1 / -0.3 and +4.7 / +1.5 / +0.1 / +2.0 by clock band,
    10-90% about +-15), then the change test on v32of{0,1}…SKaP. Pre-window |level error| median 7.4 -> 7.6; ensemble r
    TIR 0.27 -> 0.25, t<70 0.55 -> 0.53, t<54 0.26 -> 0.34 (Spearman 0.40 -> 0.22), mean 0.32 -> 0.36; paired bootstrap of
    the TIR gain 5/50/95% -0.15 / -0.02 / +0.10. On the 30 edits whose windows do not overlap the calibration window, TIR r
    0.41 -> 0.44, mean 0.62 -> 0.59. The bias is a stable trait (a donor's train-window TIR gap against their edit
    pre-window gap: r 0.83 / 0.79 by training) but not a level: per donor (88 donor-trainings, train window) the TIR gap
    tracks the generated-minus-field glucose sd (Spearman -0.70; generated sd a median 16% wider) and the ICE mean gap
    (-0.65), with insulin within 6-8% and carbs unrelated (+0.01). The background-ICE offset the band corrects was already
    near zero. The excess slow variability of LESSONS 127-129 is the cause to fix; under test: mean reversion of the
    background's slow drift (runs/2026-10-23-ice-damp/).
135. **Damping the background's slow drift narrows glucose a little but makes TIR change prediction worse; not kept.
    The closed-loop excess persistence is not mostly background drift.** plant_v3 PLANT_DAMP_K / _TAU / _SLOW_H
    (runs/2026-10-23-ice-damp/) subtracts kappa times an exponential mean (tau minutes) of the background's deviation from
    its exogenous base. Plain damping pulled mean glucose down about 22 mg/dL and raised lows: it removes the day-scale
    level along with the drift. The band-pass form (fast mean minus a 24 h mean) keeps the level. At kappa 0.25, tau 180,
    on the 24 held-out hosts (3 seeds, clean time), of0 / of1: TIR 73.4 / 72.5 -> 73.9 / 71.3, t<54 0.24 / 0.16 -> 0.17 /
    0.19, mean 152 / 153 -> 152 / 155 (field 74.1 / 0.12 / 152), glucose sd ratio 1.14 -> 1.09 / 1.12, closed-loop 3 h vt
    4.8 -> 4.07 / 4.41 (field 2.76). Stronger is worse: on of0, kappa 0.6 gives TIR 72.2, t<54 0.32, |mean gap| 14.5;
    kappa 1.0 gives 66.7, 0.47, 17.1, with two donors running away high (mean 305 and 325). Vt reaches only 3.8 at kappa 1.0.
    Change test (62 edits, two-training ensemble against the base): TIR r 0.27 -> 0.16 (paired bootstrap of the change, 90%
    interval -0.18 to -0.03), t<70 0.55 -> 0.55, t<54 0.26 -> 0.38 (-0.05 to +0.25), mean 0.32 -> 0.35. The TIR loss is
    outside noise, and the t<54 gain is not. The remaining closed-loop persistence (about 4 against the field's 2.76) has to
    come from elsewhere in the closed loop: behavior and defense responses, or how the model's state feeds back. Damping
    the background past what keeps the level does not reach it.
136. **A closed-loop low-response kernel brings held-out lows to the field without a TIR cost, but does not improve change
    prediction; adopted as the base (Pete, 2026-10-23).** Event average on held-out clean time after glucose enters < 70 (from
    >= 70), base v32of{0,1}TcB2FGUCGLBGGSKa: total ICE at 15 / 30 / 45 / 60 min 105 / 146 / 120 / 81 mg/dL/h (field) vs
    79-83 / 82-87 / 76-85 / 67-69 (generated), glucose at 60 min 132 vs 96-99. Same-step background ICE by glucose band
    matches the field in every band (calibrate_closed_bg on the train-window rollouts: shifts within +-6 above 60), so the
    gap is the time course: the defense ramp follows projected glucose and stops once Loop's suspension lifts the
    projection, while a rescue, once eaten, absorbs for an hour. Generated background rises about 62 at 15 min and fades;
    its pulses build to about 33 by 45 min. After a crossing of 250 the generated ICE runs about 10-20 above the field for
    3 h (glucose 200-206 vs 182 at 3 h), the smaller gap. calibrate_low_kernel.py (runs/2026-10-09-ice-gen-v1/): field
    minus generated total ICE after each entry, 2 h refractory, from the 28 days before the hold-out; both trainings agree
    (+44 / +41 and +54 / +38 at 30 / 45 min, zero after 60 min; area 25 / 21 mg/dL). The plant adds it after feedback
    (plant_v3 calib_low_kernel). Held-out clean time, of0 / of1 (base 73.4 / 72.5, 1.57 / 1.50, 0.24 / 0.16, 152 / 153;
    field 74.1 / 0.86 / 0.12 / 152): TIR 74.5 / 72.9, t<70 1.14 / 1.32, t<54 0.13 / 0.10, mean 153 / 153; glucose at 60
    min after a low 118 / 113; per-person pass t<54 25 -> 50% / 46 -> 62%, TIR 29 -> 33% / 21 -> 25%, insulin 33 -> 21%
    / 33 -> 29%. Persistence barely moves (3 h bgice vt 4.81 -> 4.69 / 4.72 -> 4.49; sd ratio 1.14 -> 1.11 / 1.13). Change
    test, ensemble (base): TIR r 0.21 (0.27; paired bootstrap of the change, 90% -0.12 to -0.00), t<70 0.57 (0.55), t<54
    0.29 (0.26; Spearman 0.38 vs 0.40), mean 0.28 (0.32). The ensemble's predicted changes correlate 0.94 / 0.89 / 0.65 /
    0.98 with the base's: a state-triggered rescue moves the level of lows, and both arms of an edit carry it. Better
    absolute fidelity on the primary safety metric, change prediction level to slightly worse (within the test's power,
    LESSONS 133); Pete chose it as the base. New base v32of{0,1}TcB2FGUCGLBGGSKaLK, checkpoints icegen_v32of{0,1}TcB2FGUCGLBGGSKaLK.pt on both machines.
137. **Strategy switches (temp basal <-> autobolus) are the generator's best change test so far: it ranks them better than
    replay, and the size of the strategy effect is right within noise; a high-side kernel is not needed.** 55 switches on 47
    pilot donors (switches.csv in runs/2026-10-13-ice-change/, from the per-cycle mode in the decision log; a switch is a
    lasting flip of the automatic-bolus share, two near an edit dropped), 37 on 32 donors scored (7 donors lack a meals
    file), same pre/post windows as the edit test. The engine takes the dosing strategy cycle by cycle from the export's
    decision_times.csv `mode` column, which overrides `--temp-basal-strategy`, so a first run predicted no change for most
    switches; each arm now gets its own copy of the export with that column set to its strategy (change_run.py
    EVENTS=switch, `_build_sw`). Field TIR change at a switch sd 14.4 vs 9.5 at 141 pseudo-switches, so the switches carry
    real effect. Predicted vs field change, two-training ensemble (replay): TIR r 0.66 (0.63), donor-cluster bootstrap 90%
    0.29 to 0.83 (0.03 to 0.82), Spearman 0.55 (0.27), mean |err| 7.75 (8.53; zero 8.30); mean glucose r 0.61 (0.49),
    |err| 12.8 (16.3; zero 13.1); t<54 r 0.24 (0.08), Spearman negative for both. Pearson is carried by one switch to temp
    basal with a field TIR drop of 69 points (both tools predict a large drop there); without it, TIR r 0.45 (0.32),
    Spearman 0.51 (0.21), |err| 6.70 (7.62). Within direction, the generator ranks switches to temp basal (r 0.60, replay
    0.28) but not switches to autobolus (0.08, replay -0.09). The level: signed strategy effect (autobolus minus temp basal, per
    switch) +4.4 TIR field vs +5.5 generated (replay +5.7); overstatement +1.0, donor-cluster bootstrap 90% -2.0 to +4.0.
    Without the largest switch, +2.6 vs +5.0 (90% -0.0 to +4.7), borderline. The simulator adds less insulin at a switch
    to autobolus than the field did (+1.0 vs +2.0 U/day, medians), so any excess gain would come from dose timing, not
    amount. Around a switch the field's behavior barely moves (manual boluses, carb entries and the share of meals bolused
    flat); the per-switch residual tracks the change in need (field minus predicted TIR vs change in mean clean ICE,
    Spearman -0.64; vs change in total insulin -0.58), lesson 40's unseen shifts again. Single trainings: TIR r 0.70 / 0.60.
    No model change follows; the switch set is a second change test beside the edits, scored the same way. Separately, a mirror of the low kernel after each crossing
    above 250 (plant_v3 calib_high_kernel, PLANT_HIGH_KERNEL_SCALE) finds no gap on the train window (area 0.7-2.6 mg/dL,
    both trainings), against the 10-20 mg/dL/h excess seen on held-out time, so it is not calibrated in; the hook stays and
    does nothing unless a checkpoint carries the kernel.

138. **Labelling every delivered manual bolus fixes the meal-bolus share but does not improve change prediction; held as a
    candidate, base unchanged.** The bolus labels came only from bolus decisions (requested > 0), so a manual bolus
    delivered with no decision near it read as "no bolus"; about a quarter of delivered manual boluses pool-wide, and
    nearly all of them for a few donors. The ice_v32b root adds each such bolus (>= 0.05 U, no decision within 15 min) as
    a decision with the delivered amount, and the base recipe was retrained on it (two seeds, same chain plus the low
    kernel). Share of carb entries bolused within 40 min on the donors where the gap was largest: field 0.91-1.00, base
    0.24-0.67, new 0.88-1.00, so the behavior now matches. Held-out clean-time level, seed 0 / 1 (base): TIR 75.8 / 74.4
    (74.5 / 72.9), t<70 1.19 / 1.38 (1.14 / 1.32), t<54 0.14 / 0.17 (0.13 / 0.10), mean 151 / 151 (153 / 153), field
    74.1 / 0.86 / 0.12 / 152; pass rates move both ways by seed, within noise. Change prediction, two-seed ensemble r
    (base): edits TIR 0.21 (0.21), t<70 0.53 (0.57), t<54 0.17 (0.29), mean 0.36 (0.28); switches TIR 0.73 (0.66),
    Spearman 0.49 (0.55), |err| 7.53 (7.75), t<54 0.14 (0.24), mean 0.57 (0.61). Paired bootstrap over edits/switches of the
    ensemble r difference, 90%: every interval spans zero (edit t<54 -0.40 to +0.06, the nearest to a loss; both seeds
    lower than both base seeds there, 0.16 / 0.13 vs 0.20 / 0.37). Not adopted: no change metric gains beyond noise and
    edit t<54 leans worse. The labels are more faithful, so the root stays available (mk_v32b.py) for a retrain once a
    larger edit pool can separate the two.
139. **The pooled change test (159 edits, then 194) and a level band for enrolled donors: the band is kept as an enrolment
    step; the generator beats replay on lows from the pre-edit window alone.** Expansion donors with a settings edit
    (edits_x.csv, screen2.py on ice_v32x: 114 edits on 95 donors) were enrolled in the frozen base v32of{0,1}…SKaLK by
    fit_many.py, a batched fit_person: network and pooled calibrations fixed; profile, trait and defense rows fitted on
    training days under fit_person's prior ratio, then the T step. Three donors were skipped for non-finite inputs (no TDD).
    97 edits scored on both trainings. (a) Enrolled donors ran high: pre-window own-settings mean glucose +15.5 mg/dL
    (median), t>180 +8 points, TIR -8 to -13, concentrated where the field is well controlled (+24 / +16 / +1 by tertile
    of field mean, cuts 127 / 144; trained donors +9 / +6 / -10). It is regression toward the population level plus an
    upward shift. Their profiles sit outside the trained cloud (Mahalanobis median 7.2 vs 3.8; enrolment has no profile
    prior), but distance tracks the bias only weakly (Spearman 0.19). (b) Per-person level band and pulse-size factor from
    train-window rollouts (lb_many.py, 3 seeds; band shift median +8 to +10 mg/dL/h, size factor median 0.87) ->
    v32of{0,1}…SKaLKXL. Two-training ensemble r, without -> with: TIR 0.17 -> 0.31 (per training 0.16 / 0.17 -> 0.28 /
    0.30), mean 0.23 -> 0.38 (0.16 / 0.30 -> 0.37 / 0.38), t<70 0.48 -> 0.46, t<54 0.32 -> 0.26 (0.18 / 0.38 -> 0.28 /
    0.21). Paired bootstrap of the r difference, 90%: TIR +0.03 to +0.23, mean +0.05 to +0.24, t<70 -0.17 to +0.11, t<54
    -0.22 to +0.10. Mean |error| TIR 6.47 -> 5.68 (zero 6.08, replay 5.76), mean 11.33 -> 9.95 (zero 10.68, replay
    11.02), t<54 0.30 -> 0.36 (+0.00 to +0.12). Level: mean-glucose bias +15.5 -> -0.7, but own-settings t<70 +1.1 and
    t<54 +0.33 above the field; the band trades the high bias for excess lows. Kept for enrolment: TIR and mean gain on both
    trainings beyond noise, the low side within it. Unlike 134 (trained donors, bias was variability), enrolled donors
    carry a real background offset. (c) Scored by window, predicted change from the pre-edit window alone (the honest
    "before trying it" case) against both windows averaged: replay gains most from seeing the post-edit window. Pre-window
    r, replay vs generator, pilot 62 edits (base): TIR 0.13 vs 0.22, t<70 0.30 vs 0.51, t<54 -0.09 vs 0.18, mean 0.27 vs
    0.34; x 97 edits (with band): TIR 0.28 vs 0.29, t<70 0.23 vs 0.45, t<54 0.06 vs 0.29, mean 0.42 vs 0.36. Field change
    at a real edit is barely wider than at a pseudo-edit (x: TIR sd 8.1 vs 9.3, t<54 0.46 vs 0.43), so per-edit r stays
    noise-limited. Next: the e-cohort edits (355 on 280 donors, ice_e32, pilot labeler 21b2c3c; enrolled in three chained
    chunks of about 94 plus the band, …SKaLKEL) for a ~500-edit pooled scorecard; then the excess lows left after the band.
    Runs: runs/2026-10-23-ice-enrol/ (fit_many.py, lb_many.py, enrol_x.sh, lb_x.sh, enrol_e.sh, change_e.sh),
    runs/2026-10-13-ice-change/ (score_pool.py, score_win.py, pboot.py, lvl.py).
140. **Glucose effectiveness, step 0 (docs/handoffs/2026-10-24-simulator-ice-mechanistic-reply.md): the base already has
    a strong restoring force near lows and almost none at high glucose; the field's insulin-free stretches cannot read SG.**
    (a) probe_bg.py (runs/2026-10-24-ice-ge/): held-out points on 60 trained donors (1,363 points), real inputs. The glucose
    input is raised D mg/dL over the last H hours, the rest held, including the teacher-forced previous value. Slope of the
    predicted mean background on glucose (1/h), D = +40, H = 3, of0 / of1, by glucose band: below 90 -0.17 / -0.16, 90-130
    -0.07 / -0.06, 130-180 -0.04 / -0.03, 180-250 -0.02 / -0.01, above 250 0.00 / -0.03. Lowering glucose (D = -40) gives
    about twice that below 130. The AR slope on the previous value is 0.37; the sustained median b/(1-a) is -0.09/h
    (0.0015/min). A linear -SG*G gives one slope everywhere; additive's prior (median 0.0045/min, UVA/Padova 0.0013-0.0047)
    is -0.27/h. The learned force is defense-shaped: large near lows, about 10x below the prior above 180. Where Loop
    doses to glucose, the TDD ISF rule likely absorbed any high-side uptake (insulin activity rises with glucose), so the
    ISF consistency check (step 0c) decides whether a literature-strength term double-counts. (b) sg_free.py: steps flagged
    no_insulin, insulin activity < 0.1 U/h, no carbs or labeled meal within 3 h, stretches >= 1 h. That is 2,503 stretches,
    19,013 h on 33 pilot donors (e: 379, 3,010 h), with median velocity 0.0 mg/dL/h at median glucose 156. A real
    zero-insulin stretch drifts up, so most of these are delivery off the record (pumpless Loop), not zero insulin. The
    within-stretch slope is -0.23/h against glucose at the same reading (biased negative by the CGM noise the velocity
    shares) and -0.69/h against glucose 15 min earlier. That this is steeper, not shallower, shows excursion dynamics, not
    uptake. No SG reading is possible from these data, so SG's prior rests on the literature. Next: step 0c, the eda ISF
    yardstick with an SG term removed.
141. **Engine basal gaps (main 8fa8411) in plant rollouts sit on no-dose-guard cycles, not on compression nulls; small,
    common to both arms of an edit.** The engine skipped steps without sending basal, so the external plant received no
    insulin over those spans. runs/2026-10-24-ice-ge/basal_gaps.py, 668 change-test rollouts (x and pilot, build 11d1b77),
    spans of 10 min or more with no basal: a withheld compression reading in 0% of gap steps. About 35 min/day (2.4-2.5% of
    time) where most field cycles are no_dose_guard. The field delivered 0.40-0.50 U/h there on average; some are truly
    pumpless (x334, 0.05 U/h), others ran the schedule. Field basal running outside guard spans: 2-3 min/day, 0.02-0.03
    U/day missed. Under 1% of TDD pooled, but 10-60 h stretches for a few donors, and both arms of an edit share them, so
    change deltas are mostly unaffected. The engine fix (last command 30 min, then schedule) would add insulin in truly
    pumpless spans; reported to simulator. Adopt with the next frozen build, not under running chains.
142. **extract.py's pumpless rule zeroed recorded basal; fixed to block only the schedule fill.** Raised by simulator from
    lesson 141: inside x334's guard span, steps.basal_u read 2.45-6.97 U/day against the record's 7.77-9.31. The rule (>=
    90% no_dose_guard cycles over >= 1 h -> basal 0) was meant to stop a schedule fill where no record exists (i061). It
    also overwrote delivery the record covers: the pump kept running and logging (suspends, boluses) while Loop read its
    data as too old. pumpless_zeroed.py (runs/2026-10-24-ice-ge): recorded basal zeroed is 0.65% of all insulin on the
    pilot, 0.80% on x and 0.17% on e. 15 / 23 / 3 donors lost > 2% of their insulin, up to 36% (x432, months of guard
    cycles). The record was real (pumpless_real.py). Inside those spans, mean ICE with the record's basal vs zeroed, against
    the person's clean mean: i126 +61 / +10 vs +79, i171 +83 / +24 vs +61, x334 +59 / +51 vs +62, and i061 (the rule's own
    case) +42 / +1 vs +70. Zeroing is the worse reading everywhere. The record is a lower bound where some doses are unseen,
    so the `unrecorded` flag and its one-insulin-duration tail stay. Re-extracting x334 / x001 / x432 with the fix leaves
    clean steps, clean ICE and TDD identical. Training targets do not move; insulin inputs (iob, activity, basal) inside
    the spans and in the lookback after them do, as does the plant's warm-up IOB. Adopt at the next re-extraction, with the
    GE base retrain, not under the running chains.
143. **The 496-edit pooled change test: on the e cohort replay beats the generator, and the loss tracks enrolment level
    error.** Base …SKaLK with enrolled donors plus level band (…LKXL, …LKEL), ensemble of two trainings. 62 pilot + 97 x +
    337 e edits; 9 e edits on unenrolled donors drop out. Pre-window r, model / replay, paired bootstrap 90% of the
    difference (pool3.py):
    - **Pooled:** TIR 0.25 / 0.27 (-0.10 to +0.05), t70 0.34 / 0.35 (-0.11 to +0.07), t54 0.15 / 0.20 (-0.13 to +0.05),
      mean 0.36 / 0.44 (-0.16 to -0.01).
    - **e alone:** TIR 0.25 / 0.31, t70 0.29 / 0.41 (-0.24 to -0.02), t54 0.12 / 0.26 (-0.23 to -0.04), mean 0.36 / 0.48
      (-0.20 to -0.03).
    - **Both windows, pooled:** replay ahead on all four (TIR 0.24 / 0.31, t70 0.36 / 0.45, t54 0.20 / 0.28, mean 0.34 /
      0.46).
    The pilot and x lead on lows (lesson 139) does not carry to e. The model's |error| is lower than replay's everywhere
    (t70 1.40 vs 2.44), but its predictions are compressed (sd 0.16-0.64 of replay's), and on t54 its |error| of 0.39 is
    worse than predicting no change (0.31). The e edits carry little signal: field TIR change sd 8.7 at real edits vs 8.3
    at pseudo-edits. **The loss tracks enrolment fidelity** (e_diag.py). By tertile of the model's own-settings pre-window
    TIR level error, t70 r model / replay is 0.57 / 0.58 (low error), 0.25 / 0.35 and 0.08 / 0.30 (high); on x 0.72 / 0.45
    down to 0.19 / 0.06. The model's level error is a median 7.4 TIR points on e against replay's 1.0, after the level band.
    Lesson 134 ties per-person TIR bias to glucose-sd excess, not offset, so this is the variability fault glucose
    effectiveness targets. The GE arm's gate now includes the e pool and, per set, the tertile split by level error.
144. **Enrolling the level on the pre-window fixes the level but not the change prediction; level corrections add lows.**
    Test of lesson 143's lead. Per edit, the model's own-settings level is shifted by Δ = d_mean / 1.40 mg/dL/h of ICE
    offset (closed-loop sensitivity, pw_sens.py: +1 mg/dL/h → mean −1.40, q10 −1.98 / q90 −0.75), measured on the 13 days
    before the edit only (LEVEL_ADD in plant_v3, pw.sh, pw_score.py; |Δ| median 7.5-8.6). The level then sits right:
    |TIR err| median 4.5 (x) / 4.6 (e), mean err median −0.3 / −0.5. Pre-window r, shifted / unshifted / replay, 90% of
    shifted − unshifted:
    - **x (97 edits):** TIR 0.25 / 0.29 / 0.28, t70 0.37 / 0.45 / 0.23, t54 0.10 / 0.29 / 0.06 (−0.35 to −0.03), mean
      0.37 / 0.36 / 0.42. |err| up on t54, 0.37 → 0.46.
    - **e (337 edits):** TIR 0.20 / 0.25 / 0.31, t70 0.32 / 0.29 / 0.41, t54 0.17 / 0.12 / 0.26, mean 0.35 / 0.36 / 0.48;
      no difference beats noise, and replay stays ahead of the shifted model on all four.
    Not kept. The level error marks the edits the model gets wrong but is not their cause. The held-out check of the level
    band (…LKX vs …LKXL, 88 x donors, 3 seeds, two trainings) reads the same way: the band takes the mean bias from +13.5 /
    +18.1 to +0.3 / +1.9 and TIR bias from −5.4 / −9.2 to −1.8 / −4.2, but t70 bias goes from −0.3 / −0.5 to +1.1 / +1.0
    and t54 |bias| from 0.23 / 0.16 to 0.44 / 0.41 (worst 29.9). Pulling a too-wide distribution down to the right mean
    pushes its lower tail into lows. Splitting the change test by the generated / field glucose sd ratio (sd_diag.py)
    finds the high-ratio third poor for replay as well (x t54 r −0.11 / −0.15), and e's model deficit in every third, so
    spread error marks hard people too, not the e gap. The x switch test (52 strategy switches) agrees: replay leads on TIR
    (0.57 vs 0.47 / 0.38) and mean (0.61 vs 0.49 / 0.43); on t70 / t54 neither predicts (r < 0), the field change at a
    switch being no larger than at a pseudo-edit.
145. **The generated person cancels a carb-ratio change: the defense reads every meal bolus as an oncoming low.** Over a
    window, the model's mean ICE change is ≈ 0.97 × the change in ISF × insulin activity for every edit kind (cancel.py);
    the generated person eats the extra insulin back. The instrument is replay's pre-window Δ(ISF·activity) (replay_dins,
    gain.py); glucose response per unit, field / replay / model: all edits −2.26 (90% −2.86 to −1.75) / −3.77 / −1.66;
    CR edits −2.28 / −3.83 / −0.63; basal −1.30 / – / −2.02; ISF −2.38 / – / −1.81; target −5.23 / – / −3.63. Replay
    overshoots everywhere; the model is close except on CR edits, where it gives a quarter of the field response.
    Cause, by ablation of the pending-insulin input the network sees (iob_net, PLANT_IOBNET_SCALE, iob.sh, iob_score.py;
    113 CR-dominant edits, x + e, pre window, two trainings agreeing within 0.1 on every figure). The v3m13 defense
    projects bg − iob_net and ignores carbs on board, so the insulin of a meal bolus looks like a low on its way. Base /
    hidden (iob0) / net of entered carbs on board (cob1, PLANT_IOBNET_COB, linear 3 h absorption at the person's g-eq):
    - **response per unit:** −0.54 / −2.46 / −1.53 (field −2.28); cancellation 0.99 / 0.68 / 0.94;
    - **pre-window r vs field:** mean 0.15 / 0.41 / 0.32, TIR −0.01 / 0.08 / 0.20, t70 0.18 / 0.35 / 0.16;
    - **|err|:** mean 10.7 / 10.0 / 9.9, TIR 6.7 / 6.5 / 6.1;
    - **own-settings level vs field pre-window (lvl_check.py):** mean bias +8.7 / −14.5 / −8.8, |.| median 13.2 / 18.4 /
      13.1; TIR bias −7.0 / −7.4 / −4.7.
    Hiding the input fixes the response but drops the level 23 mg/dL; netting carbs out keeps the level error the same
    size and gets two thirds of the response, without retraining. Not kept yet. Both are test-time edits to an input the
    network was trained on. The fix to keep is a carbs-aware projection in the dataset (dataset_v3m), retrained on both
    seeds.
    On all 434 edits (pw_score.py on the cob1 runs; x 97 / e 337 scored), cob1 against base, pre-window r:
    - **mean:** 0.41 / 0.36 (x) and 0.42 / 0.36 (e), both 90% intervals −0.01 to +0.13; |err| 9.8 / 10.0 and 10.0 / 10.5.
    - **TIR and t70:** no difference beyond noise on either set.
    - **t54:** r 0.31 / 0.29 (x) and 0.07 / 0.12 (e), but |err| rises 0.37 → 0.50 and 0.40 → 0.68. Predicting no change
      scores 0.30 / 0.31.
    - **own-settings level:** mean error median −11 mg/dL on both sets, against near zero for base.
    As a test-time switch, cob1 lowers glucose across the board and adds lows. The calibrations after training (level
    band, low band, low kernel) were fit with the old input, so they no longer offset it. Not kept as a switch. The
    retrain, with the whole calibration chain rerun on the new input, is the test (arm oc, `runs/2026-10-25-ice-cob/`).
146. **Glucose effectiveness, arm A (SG 0.0045/min, the prior median), does not beat the base; not kept.** The of recipe was
    retrained with GE_SG on both seeds (gb arm, chain_ge.sh in runs/2026-10-24-ice-ge/, frozen ice-ge). The plant subtracts
    60·SG·G and the network learns the residual. Results, gb vs of, seed 0 / 1:
    - **held-out (88 pilot donors, 3 seeds):** TIR bias −5.3 / −6.5 vs −0.7 / −3.0; t70 bias +1.24 / +1.73 vs +0.45 /
      +0.36; mean +6.4 / +3.4. Worse on both trainings.
    - **pilot change test (62 edits), model r:**

      | metric | gb | of |
      |---|---|---|
      | TIR | 0.23 / 0.21 | 0.24 / 0.16 |
      | t70 | 0.54 / 0.48 | 0.51 / 0.62 |
      | t54 | 0.51 / 0.20 | 0.20 / 0.37 |
      | mean | 0.39 / 0.36 | 0.40 / 0.17 |

      Each gap is smaller than the gap between the two of trainings (mean 0.40 vs 0.17), and the |err| figures match to
      within 0.4. The own-settings level check is worse: TIR median −4.9 / −6.2 vs +1.6 / −2.7.
    - **switch test (52 switches), model r:** TIR 0.69 / 0.65 vs 0.70 / 0.60; mean 0.49 / 0.60 vs 0.58 / 0.62; t54
      0.25 / 0.20 vs 0.20 / 0.26. No difference.
    A literature-strength SG adds a restoring force the TDD-ISF ICE already holds, as lesson 140 suspected. It pulls the
    distribution's level and tails out of place without making changes any more predictable. GE stays off (GE_SG 0, the
    default) until the ISF yardstick check (step 0c) says how much uptake the TDD ISF absorbed. The change-prediction
    gap that matters is lesson 145's cancellation, which GE does not touch.

147. **The low side of change prediction is judged on t<70; t<54 is a guard only (Pete, 2026-10-26).** On the pilot
    change test (62 edits) no model beats predicting zero change on t<54: zero |err| 0.30, of 0.33 / 0.31, oc 0.37 /
    0.33, replay 0.67. Its model r runs 0.12–0.37 and swings between two trainings of one recipe (of 0.20 / 0.37), so it
    cannot separate two models. t<70 carries signal: zero |err| 1.41, of 1.25 / 1.20, model r 0.48–0.62 on every
    training. Keep/drop and candidate ranking now read TIR and t<70; t<54 is still reported, and a change is flagged when
    it raises predicted or scored t<54 by more than the spread between two trainings. t<54 stays the safety target in
    AGENTS.md. On the switch test (52 switches) t<70 is near r 0 for replay and both of trainings, so strategy switches
    remain a gap on the low side.

148. **The carbs-aware iob_net retrain (oc) is kept: change prediction improves on both trainings and the response to
    insulin moves toward the field.** oc = the of recipe retrained with IOBNET_COB=1 (lesson 145; chain_cob.sh and
    pool_oc.sh in runs/2026-10-25-ice-cob/, frozen ice-cobt), scored against of on both trainings, seed 0 / 1, judged on
    TIR and t<70 with t<54 as a guard (lesson 147).
    - **Glucose response per unit of implied insulin** (iob_oc.py, replay d ISF·act as instrument; ensemble, s0 / s1):
      CR edits (113) −0.54 → **−1.59** (−1.77 / −1.40), field −2.28; all edits (434) −1.47 → **−1.82** (−1.91 / −1.74),
      field −2.26. The meal-bolus share of the cancellation was the defense reading a bolus as a low; with carbs on board
      netted out, about two thirds of the CR gap closes.
    - **Change test, model r, of → oc:**

      | | x (97) | e (337) | pilot (62) | switches (52) |
      |---|---|---|---|---|
      | TIR | 0.28 / 0.30 → 0.35 / 0.39 | 0.25 / 0.20 → 0.31 / 0.32 | 0.24 / 0.16 → 0.25 / 0.20 | 0.70 / 0.60 → 0.70 / 0.67 |
      | t70 | 0.50 / 0.39 → 0.48 / 0.38 | 0.30 / 0.28 → 0.29 / 0.31 | 0.51 / 0.62 → 0.57 / 0.48 | 0.07 / 0.00 → 0.29 / 0.02 |
      | mean | 0.37 / 0.38 → 0.44 / 0.42 | 0.41 / 0.28 → 0.48 / 0.38 | 0.40 / 0.17 → 0.37 / 0.38 | 0.58 / 0.62 → 0.66 / 0.57 |

      TIR |err| on e 6.18 / 6.24 → 5.89 / 5.90, below zero-change (6.21) and replay (6.27); the first TIR change
      prediction that beats both on the large pool. t<70 is flat everywhere.
    - **Guard and costs.** t<54 |err| on e 0.40 / 0.41 → 0.52 / 0.46 (zero 0.31): predicted t<54 changes spread wider
      (sd 0.46 → 0.72) with r unchanged, the expected side of a larger insulin response; flagged, not disqualifying.
      Held-out (24 donors): t70 bias +0.45 / +0.36 → +1.32 / +0.71, TIR bias −0.7 / −3.0 → −2.1 / −2.7. Own-settings
      level before the edit, TIR median, e: −3.0 / −6.6 → −6.0 / −5.3. The low-side calibrations (level band, defense
      gain) were fit on the old input; refitting them on oc is the next step, aimed at the held-out t70 bias.

149. **The generator's extra lows sit 1–4 h after meals, where the field catches its falls; next arm: the defense nets
    the meal glucose still to come (IOBNET_COB=2).** Held-out rollouts (24 donors, both trainings, 3 seeds), isolated
    meals (≥15 g, none 2 h before or 6 h after; low_where.py, abs_gen.py, meal_spread.py in runs/2026-10-25-ice-cob/):
    - **t<70 by hours since the last entry:** field is flat, 0.9–1.7 % in every bin. of reaches 3.2–3.8 % at 2–4 h and
      oc 3.5–4.9 %; beyond 6 h of matches the field (1.6 vs 1.5). The excess lows are a post-meal feature.
    - **per isolated meal, low within 1–4 h:** field 6.8 % (<54 1.6 %), of 14.5 % (4.6 %), oc 15.1 % (5.8 %). The field's
      glucose change at +2 h is wider than the generator's (q10/q90 −78/+149 vs −64/+114), so the generator's falls are
      not larger; they are caught less. Its lows concentrate where the drawn meal is small against the entry (low
      tercile of drawn size / entered g: 19–21 % vs 7–11 % in the high tercile).
    - **absorption:** field ICE excess per entered g runs about flat for 2 h and reaches zero by 3–3.25 h (per-donor time
      to 90 %, median 2.25 h), so the 3 h linear window of IOBNET_COB=1 has the right length. ICE excess per g over the
      first 3 h matches (field 3.3, of 3.4, oc 3.5 mg/dL per g); insulin activity 1.5–4 h after the meal is higher in
      the generator (per 100 g, 2.17/1.69/1.17/0.71 vs field 1.96/1.30/0.69/0.26).
    With IOBNET_COB=1 the defense subtracts the entered carbs whether or not the drawn meal delivers them, so a meal
    smaller or later than its entry leaves a fall the defense does not see; oc deepened what of already had. The arm
    under test, oq (chain_cob2.sh / pool_oq.sh in runs/2026-10-26-ice-cob2/, frozen ice-cob2 at eaa6da04): the pending
    insulin net of the glucose still to come from the meal pulses, reconstructed pulses in training and drawn pulses
    in the plant. On i001's training data it nets more than mode 1 (mean 0.29 vs 0.41, corr 0.72), since unannounced
    meals count too. (The arm name od was already taken by a 10-15 checkpoint; train_v32od0.log was overwritten.)
