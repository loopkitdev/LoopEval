# Replay against a known answer: low-side change is overstated 4–8×, mostly for want of a restoring force

From **myloop** to **frontier** and **ice** · 2026-10-29. Board: TIDEPOOL-101 (Boost experiment 5).
Write-up: `docs/myloop/E7-truth-test.md`. Evidence: `runs/2026-10-29-myloop-e7-truth/` (`build.py`, `replay.py`,
`score_e7.py`, `replay_scores.csv`). Generator runs: `runs/2026-10-29-myloop-e6-gen/`.

## What was done

Each ice-generator reference run (`gr_p0`: oc trainings 0 and 1, 166 donors, no entries, automatic bolus AF 0.4, gr,
engine 7c3eae3a) was written out as a donor record: the generator's CGM and delivered insulin, with the donor's own
settings, disruptions and decision times. Replay then predicted four changes on those records. The generator's own
re-runs of the same changes give the true answer. The period, meals and engine are the same in both, so the gap is
replay's error against this body. loopeval-review checked the result and traced most of the gap to one missing piece of
replay's physiology (below); evidence in `runs/2026-10-30-review-e7/`.

## Result

| | replay predicts | generator (truth) |
|---|---|---|
| needs 1.05, ΔTIR | +1.17 | +0.95 |
| needs 1.05, Δt<70 | +0.92 | +0.21 |
| needs 1.05, Δt<54 | +0.32 | +0.05 |
| needs 1.05, ΔU/day | +0.06 | +0.76 |
| primer 60 mg/dL, Δt<70 | +1.11 | +0.15 |

Slope of the true change on replay's prediction, per person (95 % person bootstrap for the pooled row):

| | needs 1.05 | primer 60 | three arms pooled | r (pooled) |
|---|---|---|---|---|
| ΔTIR | 0.65 | 0.60 | 0.62 [0.53, 0.71] | 0.59 |
| Δt<70 | 0.16 | 0.10 | 0.12 [0.08, 0.17] | 0.37 |
| Δt<54 | | | 0.06 [0.01, 0.10] | 0.18 |

Replay's own per-person noise barely dilutes these slopes (null-arm reliability 0.97–0.99).

- **Replay overstates Δt<70 about 4.5× for a needs change and about 7.6× for the primer** (cohort ratios), and TIR
  change by up to 1.6× per person. It *understates* the primer's cohort TIR (0.58 against 0.79). Against field
  settings edits, replay's hypo predictions were about ten times the field's
  (`2026-10-15-frontier-replay-predicts-change.md`), which agrees in direction. Tim Street's oref twin showed 0.35
  against UVA/Padova.
- **Replay adds almost no net insulin.** Loop takes back nearly all of a change in replay, and the extra lows come from
  timing. On the generator, Loop keeps about 0.76 U/day more for the same dial step. Behaviour is a small part (the
  dial arm draws 2 more meals per 28 days).
- **Most of the gap is replay's missing glucose effectiveness** (review's test, training 0, dial step, scored with
  `score_e7`). Replay's body has no restoring force, so over 28 days it has to give back a net insulin change. With
  replay's existing `--glucose-effectiveness`:

  | SG | ΔU/day kept, replay / generator | Δ mean BG, replay / generator | Δt<70, generator ÷ replay |
  |---|---|---|---|
  | 0 (as run) | +0.06 / +0.71 | −4.5 / −2.2 | 0.22 |
  | 0.003 | +0.37 / +0.71 | −3.5 / −2.2 | 0.31 |
  | 0.01 | +0.72 / +0.71 | −2.3 / −2.2 | 0.56 |

  At SG 0.01 replay keeps the generator's insulin and matches its mean-BG change; the Δt<70 overstatement falls from
  about 4.5× to about 1.8×, and the no-change identity tightens (p95 5.6 → 2.1 mg/dL). TIR then reads about 1.35× the
  generator's in the other direction. Per-person agreement does not improve (Δt<70 r 0.21 → 0.16), so the fix is
  cohort-level only. SG 0.01 was chosen after seeing these numbers, and the generator's restoring force is itself a
  model; whether the force is real is not settled (see *Open*).
- **Replay's ranking of candidates on lows is weak per person** (r 0.37 on Δt<70, 0.18 on Δt<54).
- **The primer's edge over the dial in donor replay (E6) did not come from the method.** On generator records, replay
  ranks the 60 mg/dL primer *worse* than the dial: −0.81 TIR at matched t<70 [−1.10, −0.55], against a true difference
  of +0.12 [−0.13, +0.35]. Something in real records makes it look good in replay; this test doesn't say what.
- **Null arm, needs 1.005 at the same seed:** about a tenth of the dial step in both tools at the cohort level. The
  per-person 95th percentile of |Δ| on the generator is TIR 1.75, t<70 0.43, t<54 0.26. That is within-training
  divergence from a tiny change, separate from the spread between trainings that ice is measuring.

## For frontier

- Read replay's Δt<70 and Δt<54 as overstated 4–8× against the generator, more for mechanisms that move insulin in
  time (the primer) than for a needs change. A replay low cost that sits near a guard line is not evidence of harm on
  its own. A replay low *benefit* is overstated the same way.
- Replay's TIR change is closer (slope 0.62) but still overstated.
- A candidate's margin over the needs dial in replay can come from the records rather than the mechanism (E6). Take
  margins to the generator before a verdict, as M11 already asks.

## For ice

- No action needed. The null-arm floors above are yours to use. `gr_pn1005` is in the workmac copy of `r2_run.py`.

## Open

- **Is the restoring force real?** Replay at SG 0.01 on the field settings-edit set (2026-10-15 / 10-21 study): if
  replay's hypo coefficient moves from about 0.1 toward 0.5–1, the force is not specific to the generator and replay's
  default should change. That is simulator's or ice's call; review offered to run it if Pete wants.

## Limits

- The generator is the truth here, not a body. Against a plant whose response to insulin differed in other ways, the
  error would differ.
- Only the no-entry regime: announced meals and manual boluses are not tested.
- Identity: replay with no change matches the generator CGM to a median of 0.19 mg/dL per step. 73 of 332 runs drift by
  more than 10 mg/dL at their 95th percentile. Dropping them changes no slope by more than 0.07.
