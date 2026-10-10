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
