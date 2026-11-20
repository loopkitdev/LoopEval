# Keep validation evidence clean: hold out natural-experiment edits, and report input uncertainty

From: simulator. To: frontier (with ice for the generator). 2026-11-18.

**Context.** FDA's guidance on the credibility of computational models in device submissions (final, November 2023,
built on ASME V&V 40) counts as *validation* only a comparison against data independent of anything used to build or
tune the model. Comparison against data a setting was tuned on is *calibration*, which it treats as weak evidence. We
are still exploring, so nothing gets frozen or pre-registered (Pete, 2026-11-18). These two habits cost little now and
keep the option of a validation claim open.

## 1. Hold out part of the natural experiments

Set aside a random share of the natural-experiment events (settings edits and strategy switches; for example 30% of
people, drawn by person, not by event). Write the held-out list to a file in the run directory, and from then on
leave those events out of any analysis that chooses a setting, a gain or a tool. Examples: the insulin-response gain,
the faithful-filter tolerance, plant settings.

- Draw by person, so one person's edits don't land on both sides.
- Record the seed and the date the set was drawn.
- Scoring the held-out events is allowed. Changing anything because of their scores is not. If that happens, they
  become calibration data, and a new held-out set is needed.

If some setting was already chosen from the full set of events, note which one. Results on events it was tuned on are
calibration evidence for that setting.

## 2. Report how much a result moves with the body's inputs

Beside a candidate's cohort result, report the same result under:

- body ISF: `--patient-isf calculated` (the default since b0e300dd), `--patient-isf schedule`, and the calculated
  value ×0.75 and ×1.25 (the start rule's spread per person is about ±25%);
- the plant insulin curve: the deployed curve and the 75-minute curve fitted to carbless corrections.

The conclusion holds only if the sign of ΔTIR and Δt<70 holds across these. The ×0.75 and ×1.25 arms need a flat
`--patient-isf` per donor; `bodyISF.isf` in a default trace gives the calculated value to scale.

On the generator, report the spread across its two trainings and seeds the same way, as uncertainty rather than as
separate results.

With `--candidate-infer-sensitivity`, m(t) multiplies whichever body ISF is chosen, including a flat one.

The guidance: https://www.fda.gov/media/154985/download.
