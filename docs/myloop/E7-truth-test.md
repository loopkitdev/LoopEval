# E7 — Replay against a known answer, and a null arm (pre-registration)

Written 2026-10-29, after the converter and identity check on one donor, before the cohort ran. Board: TIDEPOOL-101
(Boost experiment 5, `docs/handoffs/2026-10-28-frontier-boost-experiments.md` §5).

## Question

Replay and the ice generator disagree about the same change: E6's primer beat the needs dial by a wide margin in replay
and not at all on the generator. Replay was run on donor records, and the generator on its own simulated periods, so the
gap mixes replay's method error with differences between periods and plants. Here the generator's own run is the record.
Replay sees exactly what happened and is asked to predict a change whose true answer the generator gives.

1. How well does replay predict a change on a body whose answer is known? Tim Street's oref twin over-predicts Δt<70
   with a slope of 0.35 against a UVA/Padova re-run.
2. Is the primer's edge over the dial a replay artifact? If replay shows the edge on generator data, where the true
   answer has none, the edge comes from replay's method.
3. How large is the noise from a change too small to matter, in each tool?

## Design

- **Truth:** the E6 generator runs (`runs/2026-10-29-myloop-e6-gen/`).
  - 166 donors, trainings 0 and 1, seed 0, engine 7c3eae3a, no carb entries or user boluses, automatic bolus AF 0.4, gr.
  - True change = arm − `gr_p0` on the generator, same training and seed.
- **Record for replay:** each donor's `gr_p0` generator run, written as a data dir (`build.py`).
  - From the generator log's start: the generator's CGM and its delivered insulin.
  - Before it: the real record.
  - Everything else (settings, disruptions, decision times) is the donor's own, as in the generator run.
  - The generator writes each cycle's automatic bolus as a short basal segment; these go back in as automatic boluses.
- **Replay:** the same binary, flags and window as the generator run, without the external plant, plus
  `--no-carb-entries --no-user-boluses` (`replay.py`). Predicted change = replay arm − replay `gr_p0`.
- **Arms:**
  - `gr_pn105`: needs 1.05.
  - `gr_p60` and `gr_p30`: primer 60 / 30 mg/dL.
  - `gr_pn1005`: needs 1.005, the null arm. It is run on the generator too.
- **Scoring:** both tools on the same steps after the window cut: the generator's clean mask, with steps where the
  baseline CGM carries a compression artifact excluded (`r2_run.score_one`). Replay is scored on its counterfactual
  CGM. Insulin per day in both.
- **Identity:** replay `gr_p0` against the generator log it was built from: CGM difference per step, delivered insulin.
  i001: insulin read 940.7 U against 940.7 recorded; replay delivers 925.9 U; CGM |difference| median 0.1, p95 2.6 mg/dL.

## Measures

- Per arm, cohort mean Δ in each tool (TIR, t<70, t<54, mean glucose, U/day), mean over trainings, 95 % person
  bootstrap. Ratio of replay's to the generator's.
- Per person and arm: slope of generator Δ on replay Δ (OLS through all person-arm points of the three real arms, and per
  arm), Pearson and Spearman r. Slope < 1 means replay overstates the change.
- Primer against the dial line (`gr_p0` → `gr_pn105`) in each tool: TIR at matched t<70 and at matched t<54, as in E6.
- Null arm: cohort mean Δ in each tool, and the 90th and 95th percentiles of per-person |Δ| (the noise floor for a
  per-person reading).

## Bar (fixed before running)

1. **Replay overstates change on a known body** if the pooled slope of generator Δt<70 on replay Δt<70 has its 95 % CI
   upper bound below 0.8.
2. **The primer's edge is a replay artifact** if replay-on-generator shows `gr_p60` TIR at matched t<70 with CI lower
   bound > 0, while the generator's own figure (E6: +0.12 [−0.12, +0.35] at 95 %) includes 0. If replay-on-generator
   also shows no edge, the edge in E6's donor replay came from the records (real behaviour, rescue carbs, the period),
   not from replay's method.
3. **Null arm:** the cohort mean Δ should be within the size of a tenth of a dial step in each tool. Its per-person
   percentiles set the floor below which a single person's change is not read.

## Limits that bound the claim

- The generator is the truth here, not a body. The test measures replay's error against one plant whose response to
  insulin is learned from these donors. A plant that differed from Loop's insulin model in other ways would give a
  different error.
- Only changes Loop makes in this no-entry regime. Meals announced by the person, and manual boluses, are not tested.
- One seed per training. The generator's behaviour sampling responds to glucose, so a changed arm can draw different
  meals and rescues. That is part of the truth being predicted, and part of the null arm's noise.
