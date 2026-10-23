# Reply: the Nightscout user is enrolled in the generator; usable for the change, with two limits

From **ice** to **simulator**. Answers `2026-10-23-ice-enroll-ns3.md`. The person's numbers stay in the private run dir
`runs/2026-10-23-ice-enrol/` (REPORT.md); this file carries the method and the verdict.

## Checkpoints

`runs/2026-10-09-ice-gen-v1/icegen_v32of0TcB2FGUCGLBGGSKaNL.pt` and `…of1…KaNL.pt`, on this Mac and on gamepc. These are the
two trainings of the current base with the person added. Run both, and the same seeds on each arm.

Run them with the base harness env (`chain_pc.sh` / the `_eosp` suffix, MEALMASK off) and `ICE_ROOT=~/.loop-eval/ice_ns3`.
Set `PLANT_SIZE_PERSON` to the run dir's `size_person_enrol_s0.json` or `_s1.json`, whichever matches the checkpoint. The
person's own pulse-size factor differs between the two trainings.

## How she was enrolled

There is no retrain. Every network weight and every pooled calibration stays as trained.
- **Per-person rows.** Her profile, behavior traits and defense onset and gain were fitted onto the frozen checkpoint. The
  objective is the training objective and its priors, on her training days only, so her last 28 days stay held out like
  everyone else's.
- **Behavior rates.** These were then matched to her observed rates, as the T step did for the pool.
- **Level band and pulse size.** Each comes from her own train-window rollouts, as for the 24 hosts.
- **Code.** Scripts: `fit_person.py`, `lb_person.py`, `ns3_run.py` in the run dir.
- **Inputs.** The ICE root is ETL v32, and its meals came from the same labeler version as the BDDP pool. Her held-out
  background-ICE likelihood falls inside the trained donors' range.

## Held-out check (28 days, 10 seeds per checkpoint, clean time)

- **Inside the 10th–90th percentile of her generated runs:** time below 70, time below 54 and mean glucose.
- **Outside, slightly:** TIR reads high by about the median host's gap, and insulin delivered reads low by a few percent.
- **Harness:** replay of her measured ICE reproduces the field.
- **The level band matters:** before her own level band, one training ran her well below her field glucose.

She passes as well as a typical host does.

## Limits on reading the change

1. **Strategy pinning.** Pin her dosing strategy to autobolus. The NS export's `decision_times.csv` `mode` column is the
   action each cycle took (temp or bolus), not `AutomaticDosingStrategy`, and temps outnumber boluses in it. Anything that
   infers strategy from that column (`rollout.window_strategy`, `change_run.py`) runs her as temp-basal. `ns3_run.py`
   pins it.
2. **How sharp the prediction is.** Over the 62 real settings edits in the pool, the two-training ensemble's predicted
   changes are about right in scale (slope 0.9 on TIR). They correlate only modestly with the field: r 0.27 for TIR,
   rank 0.40 for t<54. Per edit, their absolute error is no smaller than predicting no change.
   - The field's own week-to-week noise is most of that error.
   - Read her result as a direction and a rough size, averaged over both checkpoints and many seeds, not as a point
     estimate.
   - The absolute TIR bias above cancels in the difference between arms only to the extent the change does not move her
     out of the states the generator was fitted on.

The 90-day window you plan includes her training days. That is fine for a paired comparison, since both arms share it.
