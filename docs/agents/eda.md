<!-- Role overlay. Loaded via ROLE.md; see AGENTS.md → Roles. -->

# Role: exploratory data analysis

Observational, summative, factual. Candidate mechanisms and therapy proposals are the
**frontier** role's job — findings go to the live document, not to a dosing change.

## The distribution study — a LIVE document

**[The Shape of Glucose](https://claude.ai/code/artifact/6b061d95-1172-41a8-b048-1a567e2c533c)**
is the standing description of what the data looks like: distributions of glucose, of its
velocity and of insulin activity; which properties are stable traits of a person versus
weekly states; and the measurement limits that bound all of it. Built by
`analysis/loopeval_analysis/{dists,volatility,traits}.py` + `analysis/dist_views/`, outputs
under `runs/2026-08-25-distributions/`.

**It is kept current, not finished.** New data or a new finding ⇒ update it and republish to
the SAME url (`Artifact` with `url=`), never a fresh document beside it.

**It is an EXTERNAL SUMMARY OF FINDINGS — not a lab notebook.** The reader wants the shape of
glucose, not the story of how it was measured. Therefore:

- **No revision history in the document.** No "revised at N people", no "an earlier version
  said", no correction boxes. When a number changes, state the current number as fact and
  move on. The history lives in git and in this file.
- **No method provenance for its own sake.** Method appears only where it changes how a
  finding must be *read* — sensor censoring bounds what the tails mean, so it stays; "computed
  from raw samples rather than an interpolated grid" is how we got it right, so it goes.
- **No debugging anecdotes, no work plans, no "what to try next".** Findings only.
- **Lessons learned belong HERE**, in the section below, so they change future behaviour
  instead of decorating the page.
- **Define every symbol at first use, in words, and keep a short glossary near the top.**
  The reader is not assumed to know σ, λ, kurtosis, SD/MAD, Hurst, ICC or Q-Q. Never overload
  a symbol: σ was doing three jobs (sensor noise, local volatility, a plain SD multiplier) and
  had to be split into named quantities. Ledger/summary cells use words, not bare symbols.

### Method lessons from this study (keep — these are the traps)

1. **Never compute a process statistic from an interpolated grid.** Interpolation is a moving
   average: it inflates the lag-1 autocorrelation of the increment and hides measurement
   noise. Use raw samples at the sensor's own cadence. Measured impact: one person's implied
   sensor noise moved 0.44 → 2.01 mg/dL.
2. **A volatility window must be causal.** A window *centred* on the increment it scales
   contains that increment; scored that way the data appears to lose 88% of its excess
   kurtosis, against 26% for the honest causal estimate.
3. **Cadence is per-dataset, never assumed.** At least one donor reports every minute, with
   consecutive samples that are not independent measurements. Express every lag in MINUTES and
   convert per dataset.
4. **Floor a fitted variance at 2σ²_measurement.** Otherwise σ collapses on flat stretches,
   ε/σ explodes, and standardising *adds* tail.
5. **Small samples get the centre right and the spread too narrow.** Going 15 → 73 people left
   every median roughly intact and widened every range. Treat any range from a small cohort as
   a lower bound on the population's.
6. **CGM is interval-censored at 40 and 400.** Any tail statistic computed through the limit
   describes the hardware. Mark the censored region rather than fitting through it.
7. **Window length is part of a tail statistic.** Kurtosis over 7 days ≠ over 4 months. State
   the window with the number.
8. **`_userId` leaks through tooling.** `etl.export_donor` prints it to stdout; scrub before
   any log is kept. Aliases only, everywhere.
9. **"Basal share" has two definitions and the dosing strategy decides which you got.**
   Delivered basal (`ia_basal`) includes temp basals — for a temp-basal-strategy user that
   is every correction Loop made. The quantity "a basal-relative forecast books at zero"
   is the SCHEDULED stream only: `(ia_abs − ia_net) / ia_abs`. Delivered share is mostly a
   restatement of the strategy: median **0.26** for autobolus users against **0.71** for
   temp-basal ones, a gap of 0.45. Scheduled share is much less strategy-dependent but
   **not invariant** — 0.43 against 0.51, a gap of 0.08 (corrected 2026-08-26; the earlier
   "0.47/0.48, strategy-invariant" came from a smaller, strategy-skewed cohort). Use
   `ia_sched_share`, and still report it by strategy rather than pooling.
10. **The 11 validated donors are unrepresentative on strategy.** 13 of the original 15
    were bolus-strategy; the wide cohort is 16 bolus / 40 temp. Any result that could
    depend on how automated insulin arrives must be checked on both.
11. **Insulin brand is missing for most donors.** `export_donor` reads
    `insulinFormulation.brand`; 38 of 56 wide donors have none and default to
    `rapidActingAdult`. Timing-sensitive insulin statistics from them carry that error.
12. **Verify exports by inspecting files, with floors that fit the data.** The ETL exits 0
    on transient failures and writes nothing; and `therapy.json` is ~1 KB for a
    single-era donor, so a 5 KB floor falsely failed four complete exports.
13. **Four donor ids fail the ETL deterministically** (one has no `pumpSettings`; three hit
    a null field → `TypeError` in `_therapy`). Retrying is wasted time; fix the ETL or drop.
14. **`pgrep -f <script>` matches your own polling shell.** A wait-loop whose command line
    contains the script name reports the script as running forever. Match on the
    interpreter + path (`"python3 -u /tmp/x.py"`) or use the pid.
15. **Cohort selection: order by a hash of the id, never by record volume.** Volume ordering
    selects multi-device duplicate uploaders (duplicate ratio up to 3×).
16. **Check every grid-searched parameter for pinning at the grid edge — every time the
    cohort changes.** The EWMA λ grid started at 0.80; 32 of 70 people fit exactly 0.80 and
    the reported half-life was biased upward by it. Widening to 0.55 freed those 32 — but six
    people then pinned to *that* bound, so it was widened again to 0.30. A fit sitting on a
    boundary is not a fit, and a bound that was clear on one cohort can bind on the next.
17. **Per-person bar charts and labelled forests stop working past ~30 people.** Draw a
    distribution across people instead (jittered strip + median + p10–p90), and sorted rows
    without labels where per-person order matters. Figures 14/15 had to be redesigned at 70;
    figures 07 and 10 were missed in that pass and had to be redone later, so **sweep every
    figure when the cohort grows, not just the ones you are editing**. Two forms carry most
    cases: a **1-D strip with a KDE behind it** for "where does this statistic sit across
    people" (fig 07's Box-Cox λ), and a **paired strip — one faint line per person between
    two or three conditions, medians marked** — for "does this change hold for everybody"
    (fig 07 raw→log→own-λ, fig 10 short-horizon vs long-horizon Hurst). The paired form is
    strictly better than grouped bars: it shows the per-person change, not just two levels.
    Per-person identity belongs in the ledger table, not on an axis.
    A third case: a per-person *unbinned pmf over a discrete support* (fig 09's value
    grid) is a comb thicket at any cohort size — plot the support instead, one point
    per grid value with the spread across people.
18. **Line-per-person panels: everyone faint, a fixed representative sample in colour.** At
    70+ people, one coloured line each is hair. `style.line_style(co, a)` draws non-sample
    people in faint grey and the sample in group colour; `style.sample_for(co)` is a
    deterministic stratified sample (≥2 per behaviour group, evenly spaced quantiles of TIR
    within group, n=12) so the SAME twelve appear in every figure and span the cohort. Grids
    of per-person panels (the phase plane) show the sample only. State the convention once,
    in the doc's glossary, not per figure.
19. **The wide cohort exists twice on disk under the same aliases.** `~/.loop-eval/trait-cohort/p<NN>.pkl`
    (glucose-only) and `~/.loop-eval/trait-cohort/full/p<NN>/` (four-stream) are the same
    people. Any script that unions the pkl glob with `style.datasets()` must dedupe by alias
    or it counts every wide donor twice — that produced a "126-person" cohort once.
20. **"Not Loop" and "unknown" are different labels.** `style.group_of` used to return
    "oref/Trio" for any row whose `algo` was not "Loop" — including rows with no cohort
    entry at all (glucose-only people), which made four Loop users look like oref after the
    oref sites were dropped. Unknown returns "" (grey). Never let a fallback branch assert a
    positive fact.

21. **Some people wear TWO CGMs at once, and the upload interleaves them.** One donor
    (p03, from 2026-06-03) uploads two independent sensors sitting a median 14 mg/dL apart,
    so consecutive samples alternate between them. The damage is silent and large: the
    increment's lag-1 autocorrelation goes to **−0.95** (alternating sign, the signature) and
    its SD from 6.3 to **29.4** mg/dL; the merged stream's median cadence rounds to 4 min, so
    cadence detection misfires and `raw_runs` returns **zero runs** — the person vanishes from
    every process statistic without an error. The 5-min panel does NOT protect you: it
    interpolates the merged stream, so the inter-sensor offset enters as pseudo-noise
    (p03's panel v_kurtosis 6.77 → 1.52, v_sd 7.98 → 6.43 once the dual period is cut).
    **Screen for it**: fraction of sub-2-min gaps together with the median |Δbg| across those
    pairs — a genuine 1-min sensor shows ~1 mg/dL there, an exact re-upload 0, two sensors
    ~14. Handle it by trimming the record to its single-sensor period
    (`style.WINDOW_OVERRIDE` / `style.clip_window`), which is applied in `style.load`,
    `style.raw_runs` and `build.py` — not by deduplicating, which would silently mix sensors.
    Sample count per day is the cheap tell: 576/day where 288 is expected.
    The clip only protects code that goes through those helpers: fig 09's delta panel
    called `D._load_glucose` directly and silently mixed both sensors until 2026-08-27.
    **Never load a glucose path directly in a view** — go through `style`.

22. **A stale intermediate table degrades everything downstream in silence.** `vol_fit`/
    `vol_cache` read each person's sensor noise from `fundamentals.csv` to set the variance
    floor (lesson 4) — but that file was an ad-hoc 15-person artefact from an early pass,
    still listing the dropped oref sites. `NOISE.get(alias, 1.0)` then handed 58 of 69 people
    a flat default floor of 2.0 instead of their own 0.04–11.96. No error, no warning, wrong
    fits. **Two rules follow**: every derived table must be written by a *named script* that
    regenerates with the cohort (that is why `wholerecord.py` and `window_check.py` now
    exist), and any per-person lookup with a `.get(key, default)` fallback across a cohort
    must assert its coverage rather than defaulting quietly.

23. **Figures regenerate from data; prose does not.** After any cohort change, re-verify
    *every* numeric claim in the document, not just the ones you expect to have moved. A
    sweep of the narrative found "1,495 person-days" (actually 7,528), a slope of 0.45
    (0.40), sensor coverage of 98% (96%), "four of the 73" at the ceiling (21 of 73), and
    "eleven of the original fifteen" — all left over from the 15-person era, sitting beside
    figures that had been redrawn correctly. Extract every sentence containing a digit and
    recompute it; the ones that read as settled background are exactly the ones that rot.

24. **One quantity, one definition, document-wide.** The long-range Hurst exponent was fitted
    on 120–240 min in `traits._hurst_and_noise` (median 0.30) but on 120–480 min in
    `fundamentals.py` (median 0.20), and the ledger column was *labelled* 2–8 h while printing
    the 2–4 h numbers. Three places, two definitions, one wrong label — and every value was
    individually correct, so nothing looked broken. When a statistic appears in prose, a
    figure and a table, fit it in ONE place and read it from there.

25. **Panel titles overrun silently, so `style.save` checks them now.** A title is written
    when a figure has three columns and still sits there when it has six; it then runs into
    the panel next door, off the right edge, or under the figure's own subtitle. Three
    shipped that way (fig 10's subtitle, two collisions in fig 14) because nothing errors —
    the PNG just renders wrong, and figures are rarely re-opened after the numbers are
    right. `style._check_titles` draws the figure and compares each title's rendered extent
    against its panel and its neighbours, printing a warning; it runs on every `save`.
    **Look at the rendered PNG after any figure change** — the check catches overruns, not
    a panel that is merely wrong.

26. **The artifact publishes `web/`, not `figs/` — and nothing links them.** `make_artifact.py`
    inlines the downsampled copies under `runs/.../web`; if a figure is rebuilt and the
    downsample is not, the page republishes its stale predecessor with no error and a
    correct-looking build log. That is exactly how the redrawn figures 07/10/14/15 stayed
    unpublished: `figs/` was 2026-08-26 21:03, `web/` 16:54, and `report.html` was rebuilt
    from the old copies. The downsample is now a named script — **run
    `python3 analysis/dist_views/web_figs.py` after any figure change, before
    `make_artifact.py`** (1650 px, 192 colours: ~4.6 MB for the set, ~6.2 MB once base64
    inflates it, against the 16 MB artifact limit — full-resolution copies blow through it).
    Check `figs/` vs `web/` mtimes before believing a republish.

27. **Fitting one quantity against another set's baseline inflates it.** The document
    claimed causal conditioning "removes 40% of the excess kurtosis", from 3.05 raw to
    1.71 — but 3.05 is the WHOLE-RECORD kurtosis (view 09, 73 people) and 1.71 is the
    EWMA's on the HELD-OUT span (view 14, 69 people). Within one set the honest numbers
    are 2.71 raw → 2.12 rolling / 1.79 EWMA / 1.46 GARCH, a per-person 23/28/36%. Two
    correct numbers, one invalid ratio; lesson 24's failure in its subtler form — same
    quantity, same definition, different *sample*. State the window AND the cohort with
    any before/after.

28. **Named states do not explain the increment's tail** (2026-08-27, `modality_kurtosis.py`).
    Time of day × carbs-on-board × insulin-activity tertile removes NOTHING of the excess
    kurtosis (2.71 → 2.88) and explains 4% of the squared increment against the causal
    volatility estimate's 16%. The tail is fattest in the calmest state: excess kurtosis
    1.29 daytime-fed, 3.81 daytime-fasted, 4.47 overnight-fasted. Compression lows are not
    the cause (BG ≥ 80 overnight: 4.25) and it holds among heavy announcers, for whom COB
    is meaningful. **So the mixture is latent, not scheduled** — don't reach for a
    circadian or meal-state schedule to model the tail.

29. **The strip+KDE form now lives in `style.strip_kde`.** Lesson 17 named it; four more
    panels were still per-person labelled bars at 69 people (view 11's noise and noise
    share, view 12's velocity shift and SD ratio) because the form was written inline in
    view 07 and nothing pointed the others at it. It is one call now — reach for it
    whenever the question is "where does this number sit across the cohort".

30. **View 11 refit a quantity the ledger already had.** `noise_and_insulin` fitted its own
    structure-function intercept over its own lag set, so the figure said σ median 1.12
    (69 people) while the ledger and the volatility variance floor said 1.27 (73, from
    `traits._hurst_and_noise` via `wholerecord.csv`) — lesson 24 again, and neither number
    looked wrong. The view reads `wholerecord.csv` now. Note the two cohorts are both
    legitimate: **73 people have glucose, 69 have all four streams**, so a glucose-only
    statistic should run over 73 and say so. `style.color_for` greys out anyone the
    four-stream cohort does not describe rather than raising.

**Scope:** observational, summative, factual, and **Loop users only** — the two oref/Trio sites
are excluded in `build.py` (`SKIP_ALIASES`) since 2026-08-26: a different controller shapes the
trace differently and two people cannot characterise that difference. Candidate mechanisms and
therapy proposals go to `docs/candidates/README.md`, not here.
