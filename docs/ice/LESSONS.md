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
