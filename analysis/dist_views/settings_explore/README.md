# Settings / aggressiveness exploration (2026-09-24 → 09-29)

Exploratory scripts behind EDA lessons 49–51: how Loop users configure ISF and the
max-basal cap relative to their insulin use, and how that relates to outcomes. They
add columns to `isf_rules.csv`, which `../settings_rules.py` builds. Run in this order:

1. `../delivery.py`, `../pull_age.py`, `../settings_rules.py` — base table
2. `gain.py`, `gain2.py` — delivery-vs-glucose response (automated delivery ÷ scheduled basal)
3. `iob.py` — IOB against current and recent glucose
4. `maxbasal_history.py` (needs Databricks) → `cap_changers.py` — within-person max-basal changes
5. `guide_map.py`, `dose_response_fig.py` — figures

Several analyses from the same week (the rule-of-X bins, the ISF × cap 2×2 and
interaction regression, the bolus-frequency and TDD crossings) ran inline and are
recorded only in the lessons. These are exploratory scripts, not study views: they
write into `runs/…/figs/` but nothing here feeds a published document yet.
