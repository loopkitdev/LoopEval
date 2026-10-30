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

## Result (2026-10-29): replay overstates low-side change 4–8× on a known body; the primer edge came from the records

Run: `runs/2026-10-29-myloop-e7-truth/` (`build.py`, `replay.py`, `score_e7.py`, `replay_scores.csv`). 166 donors × 2
trainings × 5 arms, 1,660 replays and 332 null-arm generator runs, none failed.

**Identity.** Replay `gr_p0` against the generator CGM it was built from: per-run median |difference| 0.19 mg/dL, p95
5.6 (median run), 19 at the 95th-percentile run, worst 43. Dropping the 73 runs with p95 > 10 mg/dL changes no slope by
more than 0.07.

**Cohort mean change** (mean over trainings, 95 % person bootstrap):

| | replay | generator (truth) | replay ÷ truth |
|---|---|---|---|
| needs 1.05, ΔTIR | +1.17 [+0.99, +1.36] | +0.95 [+0.77, +1.14] | 1.2 |
| needs 1.05, Δt<70 | +0.92 [+0.84, +1.02] | +0.21 [+0.17, +0.25] | 4.5 |
| needs 1.05, Δt<54 | +0.32 [+0.28, +0.37] | +0.05 [+0.03, +0.07] | 6.5 |
| needs 1.05, ΔU/day | +0.06 | +0.76 | 0.08 |
| primer 60, ΔTIR | +0.58 [+0.41, +0.75] | +0.79 [+0.62, +0.98] | 0.7 |
| primer 60, Δt<70 | +1.11 [+0.98, +1.25] | +0.15 [+0.11, +0.18] | 7.6 |
| primer 60, Δt<54 | +0.53 [+0.45, +0.61] | +0.05 [+0.03, +0.07] | 11 |
| primer 30, Δt<70 | +0.40 | +0.09 | 4.7 |

**Per person** (slope of the generator's change on replay's, the three real arms pooled, 95 % person bootstrap):

| | slope | r |
|---|---|---|
| ΔTIR | 0.62 [0.53, 0.71] | 0.59 |
| Δt<70 | 0.12 [0.08, 0.17] | 0.37 |
| Δt<54 | 0.06 [0.01, 0.10] | 0.18 |
| Δ mean glucose | 0.60 [0.47, 0.72] | 0.56 |

- **Bar 1 holds:** replay overstates low-side change on a body whose answer is known. Δt<70 slope 0.12, CI upper bound
  0.17 (per arm: needs 1.05 0.16, primer 60 0.10). TIR is overstated far less (0.62). Same period, same meals, same
  engine, with the generator as the body. Tim Street's oref twin showed 0.35 against UVA/Padova.
- **Replay barely changes the insulin delivered** (+0.06 U/day for needs 1.05, against +0.76 on the generator). Loop takes
  back almost all of a change in replay, and the lows come from timing within that near-zero net. The behaviour channel
  is small: the dial arm draws 2 more meals (73 g) per 28 days.
- **Most of the gap is replay's missing glucose effectiveness** (loopeval-review, 2026-10-30,
  `runs/2026-10-30-review-e7/`). Re-running the dial step on training 0 with replay's `--glucose-effectiveness`:

  | SG | ΔU/day kept, replay / generator | Δ mean BG, replay / generator | Δt<70, generator ÷ replay | ΔTIR, generator ÷ replay |
  |---|---|---|---|---|
  | 0 | +0.06 / +0.71 | −4.5 / −2.2 | 0.22 | 0.89 |
  | 0.003 | +0.37 / +0.71 | −3.5 / −2.2 | 0.31 | 1.02 |
  | 0.01 | +0.72 / +0.71 | −2.3 / −2.2 | 0.56 | 1.35 |

  At SG 0.01 replay keeps the generator's insulin and matches its mean-BG change, and the identity tightens (p95 5.6 →
  2.1 mg/dL). Per-person Δt<70 agreement does not improve (r 0.21 → 0.16). SG 0.01 was picked after seeing the numbers,
  and the generator's force is a model. On the field settings-edit set (ice, 2026-10-30, ice LESSONS 152) SG 0.01
  brings replay's TIR coefficient to 0.95 but its t<70 coefficient only to 0.21 (from 0.13; the generator's is 1.35).
  On real records the low-side gap is mostly something else.
- **Bar 2: the primer's edge is not replay's method.** On generator records replay prices the primer *worse* than the
  dial, against a generator answer of no difference:

  | TIR at matched … | replay on generator records | generator (truth) |
  |---|---|---|
  | t<70, `gr_p60` | −0.81 [−1.10, −0.55] | +0.12 [−0.13, +0.35] |
  | t<54, `gr_p60` | −1.32 [−1.77, −0.96] | −0.11 [−0.62, +0.28] |
  | t<70, `gr_p30` | −0.06 [−0.18, +0.04] | +0.00 [−0.18, +0.19] |

  So the large edge in E6's donor replay came from the donor records, not from the method. What in real records makes
  the primer look good to replay (real meal shapes, rescue carbs, CGM character) is not separated here.
- **Bar 3, null arm (needs 1.005):** cohort mean ΔTIR +0.14 in replay and +0.11 on the generator, about a tenth of the
  dial step in each, as expected. Per-person noise floor (95th percentile of |Δ|, one training):

  | | replay | generator |
  |---|---|---|
  | ΔTIR | 0.47 | 1.75 |
  | Δt<70 | 0.36 | 0.43 |
  | Δt<54 | 0.18 | 0.26 |

  A single person's generator change below these is not readable. Replay's own floor is lower, but its per-person
  changes track the truth weakly (r 0.37 on Δt<70).
