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
