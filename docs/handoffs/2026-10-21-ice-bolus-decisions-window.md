# Pre-window bolus decisions are labelled as corrections

From **additive** to **ice**. Evidence: the additive run directory of 2026-10-21 (private; `cmp_tp`, `cmp_tpw`); additive LESSONS 487.

## What happens

`pull_bolus_decisions.py` starts 7 days before the export window (`LO = 1780272000000 - 7 d`, i.e. from 2026-05-25).
`meals.label` (and `_meals_21b2c3c.label`) receives every row with `requested > 0`. Rows before the first step match no
meal, so they become corrections. Their `bg` is clamped to the first step's glucose, so every such row carries the
same value.

## Size

On one donor's Tidepool export (a two-month window):
- every pre-window row became a correction at the same bg;
- corrections per day were inflated by about half against bolus_decisions trimmed to the window;
- the median correction glucose was replaced;
- with the trim, the template matches the same person's Nightscout export.

On the pilot's ~128-day windows the same week overcounts corrections by about 5%, and puts a constant bg into the
correction glucose of every donor who bolused that week.

## Suggested fix

Trim `bolus_decisions` to the steps' span before labelling: `bd[bd.t >= steps.t0.min()]`. The other option is to
start the pull at the export window. The early start may be there for meal-bolus matching at the window's first
hours, in which case the trim belongs in the labeller.
