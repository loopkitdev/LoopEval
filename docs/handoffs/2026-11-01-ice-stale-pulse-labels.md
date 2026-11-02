# The donor pulse labels in `ice_v32/meals` are stale — they predate `fit_shapes`

**From:** additive · **To:** ice (and anyone scoring against `ice_v32/meals`) · 2026-11-01

## What is wrong

`ice_gen.meals.label()` has called `fit_shapes` since commit **ece70cb1**, which replaces each pulse's
`peak_h` with the mode of a lognormal fitted to the raw ICE over the 24-cell `FIT_MODES` grid, and its
`dur_h` with the fitted 90th percentile (keeping the labeller's run length as `run_h`).

**The stored per-donor meal parquets were written before that commit and never regenerated.** Their
`peak_h` is still the raw 5-min argmax and their `dur_h` is still the run length.

The signature is unambiguous, and it is uniform across all 168 donor files:

- **100%** of donor `peak_h` values are exact multiples of 5 min; **0%** are `FIT_MODES` grid cells.
- A run of the current labeller gives the opposite (99.9% grid cells), as the twin-side labels do.
- The donors' cell histogram has **exactly 0.0%** in cells 1, 3, 5 and 8 with neighbours at 2–8% —
  the raw 5-min lattice seen through the fitted grid.
- `<alias>_corrections.parquet` has no `peak_h` and is unaffected; a few donor files also predate the
  `rescue` column, which is a second symptom of the same staleness.

## Size of the error

Re-running the current `label()` on 42 donors (31.3k pulses; driver
`analysis/loopeval_analysis/patient_sim/resid_tools/relabel_donors.py`, in `main`):

| quantity | stored | current labeller | change |
|---|---|---|---|
| `peak_h` median | 0.750 h | **0.536 h** | −0.21 h; **all 42 donors move down, none up** |
| `dur_h` median | 1.833 h | **1.463 h** | −0.37 h |
| `size_g` median | 27.15 g | 26.56 g | ~unchanged — pulse detection is stable |

`size_g` barely moving is the control: this is the shape fit, not the labelling. The sample's stored `peak_h`
median is 0.750, which is exactly the value the additive scorer carries as the donor target, so this sample
reproduces the population statistic rather than a corner of it.

## Why it matters beyond additive

Anything that reads `peak_h` / `dur_h` from these files is mixing two definitions:

- **The additive cohort scorer** compares them against twin labels made with the current code. Scored against
  `meals_fit` (below), `pulse_peak_h`'s gap **vanishes** — donors and twins are both 0.622 — while `pulse_dur_h`
  becomes a real ~19% defect that the stale target scored as near-passing. Both are tier 2. Details in
  `docs/additive/LESSONS.md` § 625–626.
- **`ice_gen.plant_v3`** reads `ROOT/meals/<alias>.parquet` and passes `peak_h + 2.5/60` into
  `kernel.params` (lines 319, 327, 331), and `dataset_v3*.py` build `m_lpeak` / `m_ldur` features from
  the same columns. **This may well be self-consistent** and we are not claiming a generator defect:
  the `+ 2.5/60` reads both as the inverse of `fit_shapes`'s `peak_h = mode − 2.5/60` *and* as a
  bin-centre correction for a 5-min argmax, so code that only ever saw stale files is coherent. The
  risk is a **mix** — a model trained on stale labels and later driven from regenerated ones, or the
  reverse — because the shift is systematic (~20% in peak time, −0.39 h in duration), not noise. So
  the regeneration below is worth sequencing deliberately rather than done quietly.

## What we would like

1. **Regenerate `ice_v32/meals` with the current labeller** (and note the data version, so a stale set
   is detectable next time — the `_export_manifest.json` convention would do).
2. Confirm whether the generator's training sets were built from the stale columns.

We have deliberately not regenerated it ourselves: it is ice's data, shared with the generator, and a
silent change to the donor targets would move every role's numbers at once.

## Additive-side consequences, recorded

Until the labels are regenerated we are not fitting anything to those two rows, and any earlier
conclusion that leaned on them is marked unsupported. The twins' `run_h` is the like-for-like partner
for the donors' stored `dur_h` if a comparison is needed in the meantime.


## RESOLVED 2026-11-01 — thanks

ice regenerated all 168 donors as `ice_v32/meals_fit/` (code rev 67be7d92), leaving `../meals` in place so no
generator checkpoint is put into the mixed state, and confirmed that all three roots (`ice_v32`, `ice_v32x`,
`ice_e32`) share the one stale definition with no mixing. Additive now scores the affected rows against
`meals_fit`; `meals` can become the fitted set at ice's next re-export.

**Two corrections to the numbers above, for anyone reading them later:**

- **`peak_h` 0.536 was a non-representative sample.** On all 168 donors the fitted median is **0.622** (pooled and
  per-person medians agree exactly); the 0.536 came from the first 45 aliases in `persons.csv` order, and on a
  24-cell log grid a median hops a whole cell easily. So `pulse_peak_h`'s gap is **eliminated, not reversed**.
- **The rescue filter moves it too.** The scorer excludes rescue pulses (118,761 of them); including rescues gives
  125,128 pulses and a median of 0.558. State the sample and the filter beside any of these figures.
