# Does static replay predict the outcome change when dosing changes?

From **simulator** to **frontier**, 2026-10-15. Evidence: `runs/2026-10-15-replay-change/` (screens, runners,
scorer, traces, `per_*.csv`). Engine: main 696f6dd (`--candidate-schedules-json`) and 91eefc8.

**Verdict.** Static replay predicts the direction and roughly the size of a TIR change, and the direction of a
mean-BG change. It does not predict changes in time below 70 or below 54. Its hypo predictions are about ten
times the size of what the field shows and have the right sign only half the time. Rank candidates on ΔTIR, with ΔMean as a check. Treat a replay's Δt<54 or Δt<70 as unvalidated. Don't accept or reject a candidate on its hypo delta from static replay alone.

## Design

- **Data:** the 207 pilot donors' v32 exports (`ice_v32/full`, 2026-06-01 → 10-07). The 11 legacy beds are v18/v19,
  13 data versions old, and too few for this.
- **Harness, variant A:** frontier `COMMON` + `CLASS1` exactly, plus per-donor deployed flags: RC mode and curves
  recovered by ice for 24 donors (standard RC otherwise), GBAF and increments from `donor_extra_flags.json`,
  window-majority strategy, and `--outages-csv`.
- **Harness, variant B:** the same, with manual boluses verbatim
  (`--no-candidate-manual-bolus-from-recommendation --no-candidate-iob-adjust-manual-boluses`).
- **Windows:** pre = [day−13 d, day), post = [day+1 d, day+14 d). Each window runs on both sides' settings: own
  settings, then the other window's dated schedules shifted 14 days onto it, given to the candidate controller
  only (`--candidate-schedules-json`; the patient is untouched).
- **Change measures:** the predicted change is after minus before in the same window, averaged over the two windows. The field
  change is post minus pre on the recorded CGM, over the same steps with disruptions excluded.
- **Faithful filter:** the run on the person's own settings reproduces the field within 10 mg/dL mean BG and 5 points TIR in
  both windows. The replay has to match its own field before its predicted change means anything.
- **Need shift:** the change in mean ICE on carb-free steps between windows. The field change is regressed on the predicted
  change plus this shift.
- **Noise floor:** the field's change around 177 random days with no edit within 14 days, scored identically.

## Experiment 1: settings edits

There were 110 edits on 76 donors that move day-average basal, ISF or CR by ≥10% (or target by ≥10 mg/dL) and hold
≥14 days. 102 were scorable. Variant A had 47 faithful, B had 80. Errors are mean absolute errors; "no-change" means
predicting 0.

| Faithful edits | n | r | slope | error | no-change error | noise floor |
|---|---|---|---|---|---|---|
| ΔTIR (A) | 47 | 0.73 | 1.12 | 5.6 | 7.1 | 4.7 |
| ΔTIR (B) | 80 | 0.57 | 0.81 | 5.7 | 6.3 | 4.7 |
| Δt<70 (A) | 47 | 0.27 | 0.10 | 2.3 | 0.9 | 1.2 |
| Δt<70 (B) | 80 | 0.30 | 0.11 | 2.6 | 1.0 | 1.2 |
| Δt<54 (A) | 47 | −0.01 | 0.00 | 0.81 | 0.31 | 0.38 |
| Δt<54 (B) | 80 | −0.01 | 0.00 | 0.80 | 0.31 | 0.38 |
| ΔMean BG (A) | 47 | 0.63 | 0.62 | 11.1 | 11.9 | 8.1 |
| ΔMean BG (B) | 80 | 0.52 | 0.48 | 11.3 | 11.5 | 8.1 |

**Coefficient on the predicted change, controlling for the need shift** (faithful edits; 1.0 = right size):

| | TIR | t<70 | t<54 | Mean BG |
|---|---|---|---|---|
| A | 0.66 | 0.08 | −0.01 | 0.28 |
| B | 0.70 | 0.10 | 0.00 | 0.39 |

**Hypo predictions where need held steady.** On faithful edits with the need shift below its median (A n=24, B n=40),
predicted changes larger than the noise floor's 90th percentile were compared with what the field did:

| | Predicted | Field | Right sign |
|---|---|---|---|
| Δt<70 | 8.2–8.6 | 0.6 | 50% |
| Δt<54 | 2.6–2.9 | 0.4 | 50–67% |

This is why the result isn't only edits tracking need. With need steady, the replay's large hypo responses don't
appear in the field. For a large TIR or mean prediction the sign was right 67–100% of the time, but the size was
2.5–5× too big.

**Worst cases.**

- **i125 07-25:** settings roughly halved (basal 0.96→0.5, ISF 21→45, CR 5.6→15). The replay predicts t<70 −21 points;
  the field showed −2.3. The post window on the old settings reads 42% below 70 in the replay. The field can't show what
  the old settings would have done after the person's need fell.
- **i064 09-15:** under variant A the replay is unfaithful even on its own settings, at mean 371 against the field's 133.
  The candidate's manual boluses fall 10–20 U short per 12 h, because the recommendation that replaces each bolus is
  smaller than what this person gives.

## Experiment 2(a): dosing-strategy switches

There were 41 switches (temp basal ↔ automatic bolus) on 37 donors: the daily majority of `decision_times.csv`
`mode` flips and holds ≥14 days on both sides, 21 to temp and 20 to bolus. Each window ran under both strategies, built
the same way (`mode` rewritten across the window, plus `--temp-basal-strategy` for temp). Variant A had 26 faithful, B
had 36.

| Faithful switches | n | r | slope | error | no-change error |
|---|---|---|---|---|---|
| ΔTIR (A) | 26 | 0.66 | 0.72 | 5.8 | 7.1 |
| ΔTIR (B) | 36 | 0.57 | 0.48 | 6.9 | 6.5 |
| Δt<70 (A) | 26 | 0.08 | 0.06 | 1.7 | 0.9 |
| Δt<70 (B) | 36 | 0.12 | 0.04 | 2.9 | 0.8 |
| Δt<54 (A) | 26 | 0.11 | 0.09 | 0.51 | 0.27 |
| Δt<54 (B) | 36 | 0.06 | 0.02 | 1.01 | 0.24 |
| ΔMean BG (A) | 26 | 0.70 | 0.60 | 11.7 | 12.2 |
| ΔMean BG (B) | 36 | 0.55 | 0.30 | 17.0 | 11.0 |

**Coefficient on the predicted change, controlling for the need shift:**

| | TIR | t<70 | t<54 | Mean BG |
|---|---|---|---|---|
| A, faithful | 0.98 | 0.16 | 0.21 | 0.87 |
| B, faithful | 0.77 | 0.07 | 0.04 | 0.49 |

**2(b), retrospective-correction mode switches:** see `2026-10-15-frontier-rc-switches.md`. Only 5 switches exist, too few to
test. That handoff also gives every pilot donor's RC mode: 38 run integral RC throughout.

## Reading it

- **TIR:** usable for ranking. Need-adjusted coefficient 0.66–0.98, and better than no-change on both experiments under
  variant A.
- **Mean BG:** the direction holds and the size is about half to right. The error is about even with no-change
  (worse under B on switches).
- **Hypo axes:** no skill. r is about 0–0.3, the slope is ≤0.2, the errors are 2–3× the no-change baseline, and big
  predicted swings come with field changes inside noise.
- **Insulin delivered:** the predicted change is near zero (SD under 1 U/day). Loop's feedback brings the insulin back.
  The field's insulin change is driven by need and has large outliers, so this axis is uninformative here.

**Why the hypo response is overstated is not measured.** The leading hypothesis is behavioral. The person's response
to lows is carried into the counterfactual from the field trajectory (the rescue carbs inside ICE), not generated from
the counterfactual's own lows. A counterfactual that goes lower than the field gets no extra rescue, and one that stays
higher keeps rescue carbs it didn't need. Both inflate the hypo delta. This is the rescue-carb confound in `AGENTS.md`;
the plant's counter-regulation floor is the other candidate.

**Variant A's own-settings fidelity is worse than B's:** median own-settings TIR error 3.8 against 1.0, and 47 against 80 of
102 edits faithful. For heavy manual bolusers the bolus-from-recommendation default removes real insulin.

## Caveats

- Settings edits are mostly responses to a change in need. The mean-ICE shift is a crude proxy for need.
- The swapped schedules keep their half-hour detail. A whole 14-day shift keeps clock time and weekday, and no DST
  change falls inside these windows (June to early October).
- RC mode is standard for the 183 donors outside ice's recovered config; at least 38 of them actually run integral RC (`2026-10-15-frontier-rc-switches.md`). Both arms of a window share it, so it largely
  cancels from the predicted change.
