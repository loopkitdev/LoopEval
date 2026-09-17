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

**It is kept current, but it is not a log of the work.** Update it when the user asks for
it to be updated — a new finding is not itself a reason to touch the page (see *Working
style* in AGENTS.md). When you do publish, it goes to the SAME url (`Artifact` with
`url=`), never a fresh document beside it. What earns a place: something that says
what glucose IS. What does not: a result whose content is that some explanation
*fails*, a methods note, a robustness check. Those go in the lessons below.

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
    **Better remedy found 2026-08-28: the two sensors are labelled, and the ETL throws
    the label away.** Tidepool puts `manufacturer_model_localIdentifier` on EVERY cbg
    row's `deviceId`; p03's two sensors arrive as two upload paths — one via
    `com.apple.HealthKit` with no `deviceId`, one from `com.dekaresearch.twiist` — each
    a clean 277 readings/day at a 5-minute cadence, with increment SDs of 10.8 and 6.7
    mg/dL. Only their UNION shows the artefact. So split by `deviceId` and keep one
    stream rather than trimming two months off the record; the trim is a workaround for
    a field we discard in `etl.py`'s cbg query.

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
    **The check itself was broken from the day it was written until 2026-08-27**: every
    title in this study is `loc="left"`, and matplotlib keeps a left-aligned title on
    `ax._left_title`, not on `ax.title`. Reading `ax.get_title()` returned "" for every
    panel, so the loop skipped all of them and reported nothing, ever — which is why
    views 05, 11 and 12 shipped with titles under their own headings. A check that
    never fires looks exactly like a check that passes: **make a new check fail on
    purpose once before trusting it.** It now also tests titles against the figure
    heading, and flags a wide title only when it actually reaches a neighbouring panel —
    the gap between panels is there to be used.

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

31. **A KDE bandwidth chosen for the bulk is wrong in the tail, and a RATIO of two of
    them makes it visible.** View 02's rise/fall density ratio rippled on a roughly
    1-mg/dL scale. It is not the sensor's value lattice — dithering every delta off the
    grid removes only 6% of the wiggle for the 67 whole-mg/dL people (43% for the two
    on the 0.1 mmol/L grid, where it IS partly the lattice). It is kernel noise: the
    Silverman bandwidth is set by the bulk (median 0.64 mg/dL) and out in the sparse
    tail each isolated sample becomes its own bump, so the ripple's period tracks the
    bandwidth (median period 3.3 mg/dL, 4.7× the bandwidth, correlation 0.70 across
    people) and its size tracks how few samples are out there (corr(log wiggle,
    log tail count) = −0.78, and it grows like 1/√n on subsampling). Widening the
    bandwidth to 1.2 mg/dL halves it. Fixed by flooring the bandwidth AND stopping
    each line where that person has fewer than 40 samples left in the tail —
    **do not draw an estimate past the point where it is tracing individual readings.**
    Diagnosis method worth reusing: split-half correlation plus a subsample-scaling
    check separates a deterministic artefact from Monte-Carlo noise.
    **Then the panel stopped estimating densities at all**: it counts exceedances,
    rises ≥ x against falls ≥ x, evaluated on each person's own value grid. No kernel,
    no bandwidth, nothing to ripple, and the claim is the one the title makes. Prefer a
    counting statistic to a ratio of two smoothed ones wherever the question allows it.

32. **Sensor make and model are IN the source, per reading, and we drop them.** Every
    Tidepool `cbg` row carries `deviceId` as `manufacturer_model_localIdentifier`
    (`Dexcom_G7`, `AbbottFreeStyleLibre3-…`, `twiist_…`) plus `origin.name` for the
    uploading app; there is also a `cgmSettings` datum (12,392 people) with structured
    `manufacturers`/`model`/`name`/`softwareVersion`. The ETL's cbg query selects time
    and value only. Over the study window the sensor is identifiable for **52 of our 60
    donors** — 38 twiist, 10 Dexcom G7, 4 Dexcom G6 — and **15 donors change device
    family mid-window**, though most of those are duplicate overlapping streams (the
    HealthKit mirror) rather than switches; a real switch shows as one stream ending
    where another begins (p20 Libre 3 → twiist on 04-27, p55 twiist → Dexcom G7 on
    05-11). Prefer the per-reading `deviceId` to `cgmSettings`: it timestamps the
    change. **Caveat:** the trailing identifier is stable per person for months (median
    one distinct value over the four-month window), so it is NOT a sensor-session id —
    it cannot date sensor swaps or support a wear-age analysis.

33. **The sensor changes the numbers, and switchers prove it.** Comparing sensors
    across people confounds the instrument with whoever chose it; donors who switched
    mid-window wear both and are their own control (select them by hash of the id, and
    require a usable stretch on each). Paired, within-person, on raw source readings:

    | | Libre 3 (twiist) → Dexcom G7, n=18 | Dexcom G6 → G7, n=16 |
    |---|---|---|
    | SD of the 5-min step | +2.64 mg/dL (5.09 → 8.13), p<0.0001 | +0.87 (6.18 → 6.97), p=0.03 |
    | implied sensor noise | +0.32 (1.28 → 1.71), p=0.001 | −0.13, p=0.74 |
    | lag-1 of the increment | −0.21 (0.639 → 0.445), p<0.0001 | −0.09, p=0.13 |
    | share of flat steps | 10.7% → 8.1%, p=0.0001 | 10.1% → 9.1%, p=0.14 |
    | excess kurtosis | +1.08 paired, p=0.04 | −1.54 (4.51 → 3.30), p=0.002 |

    Read the direction: the twiist/Libre stream is SMOOTHED — more flat steps, higher
    lag-1, smaller steps — and a smoothed stream reports LOWER "sensor noise", because
    the structure-function intercept measures whatever roughness survives to the file.
    Our sigma_meas is a property of the reported stream, not of the sensor's physics.
    **Same person, different sensor, 60% difference in the SD of the five-minute step** —
    comparable to the whole between-person spread the study reports for these
    quantities. Roughness ranks G7 > G6 > Libre-via-twiist. Any cohort statistic about
    velocity, noise, momentum or tail weight is a mix of people and sensors until it is
    split by family, and our cohort is 38 Libre 3 / 13 G7 / 3 G6 / 8 unlabelled.

    Every headline statistic re-tested in the switchers, same person on both sensors:
    **holds** — Hurst at both ranges, the momentum zero-crossing (40–47 min), the
    volatility ACF at 30 min, CV, and SD/MAD, which moves 0.04 at most and stays in the
    Laplace neighbourhood. **Instrument-dependent** — the SD of the five-minute step,
    the implied sensor noise, the increment's lag-1, and the excess kurtosis (G6→G7
    alone: 4.47 → 3.32, p=0.001). The two-regime Hurst_short of 0.77 is partly
    smoothing: Libre→G7 takes it 0.80 → 0.72 (p<0.0001) while G6→G7 leaves it alone.

    **Caveat that limits the twiist contrast: leaving twiist means leaving the twiist
    AID, not just its sensor.** Its TIR (−8.8 points) and Box-Cox lambda changes are
    therapy and era, not optics — a paired design controls for the person, never for
    what else changed that day. The same-vendor G6→G7 contrast is the clean one.

34. **Describe glucose, never the person's success at managing it.** "They are well
    controlled" was cut from the study's opening (2026-09-01): judging people by their
    numbers reads as the opposite of patient-empowering, and the clause was doing no
    work — the numbers say it. Avoid "well/poorly controlled", "good control",
    "compliance", "adherence". Time in range, mean glucose and CV need no adjective.
    Same family as the "user-scaled, never compliance" rule for manual boluses.

35. **The hash-ordered cohort matches the pool, which is exactly why it misses the cell
    we care about.** People who announce almost nothing, let automation bolus, and run a
    TIR under 65% are **1.4% of automated-system donors** (110 of 8,026) — so a faithful
    sample of 60 contained ONE of them. The fix is a second, deliberately over-sampled
    stratum, never dilution of the core: `pull_handsoff.py` selects, `EXPORT_ROOT`/
    `EXPORT_MAP` point `export_full.py` at a separate root, `build.py` tags `stratum`,
    and `style.cohort()` returns **core by default** so every figure and view 00's
    pool-matched claim stay true. 13 people qualified from a 24-donor batch.

    Three traps this walked into, all worth keeping:
    - **`manual_share = manual/(manual+auto)` is undefined when someone has no boluses,
      and `.fillna(0)` turns "no insulin data" into "automation does the bolusing".**
      10 of the 110 were that. Require a bolus stream.
    - **Screen on a 30-day window, get 114-day behaviour.** Two exports announced
      126–132 g/day across the full record. Confirm membership on the window you will
      analyse, not the one you screened on.
    - **Never define a stratum by the outcome you plan to measure.** The screen used TIR;
      the stratum does not. Membership is the behavioural half only (the study's own
      `archetype` cut, <30 g/day announced, plus a dose stream), so TIR is something
      these people HAVE rather than something they were chosen for. It lands at a median
      of 57% anyway, against 74% for the core.

    **And the payoff, once the instrument is controlled for.** The stratum is 12/13
    Dexcom G7 while the core is 70% Libre-via-twiist, so a raw stratum-vs-core
    comparison reads as a large difference in step SD (8.71 against 5.76) and
    Hurst_short (0.73 against 0.77) — both of which are exactly the sensor effect from
    lesson 33, and both of which VANISH within Dexcom G7 (8.86 against 8.03, p=0.22;
    0.71 against 0.72, p=0.46). Matched on sensor, every shape statistic agrees:
    SD/MAD 1.42 vs 1.43, excess kurtosis 3.02 vs 3.19, momentum zero at 40 min in both.
    **The distributional findings hold for people who announce nothing and run a TIR of
    57%** — which is what makes the stratum worth having in the document rather than
    only in the ledger.

36. **Age, sex and diagnosis date DO exist in Tidepool's model — just not in
    `device_data`** (checked 2026-09-03, all 132 columns: none demographic). The catalog
    has 29 tables, and the demographics live in `seagull_profiles` (**birthday**, gender,
    diagnosisType, diagnosisDate), `patients` / `patient_with_summary` (birthDate,
    diagnosisType) and `consent_records` (**ageGroup**). For our 84 donor ids: 45 have a
    birthday, giving a **median age of 27 (p10–p90 12–55), 14 under 18 and 5 under 13**;
    `consent_records` independently shows 26 adults, 5 aged 13–17, 8 under 13. Gender is
    empty for all 917,679 profile rows, so that one really is absent.

    **The cohort is young and includes children** — which nothing in the analysis had
    accounted for, and which the study had asserted was unknowable. Two cautions before
    using it: coverage is only about half the donors, and a Tidepool profile birthday can
    belong to the account holder rather than the wearer, so a child's record may carry a
    parent's date or vice versa. Treat an individual age as a hint and the distribution
    as approximate. Tables holding names, emails and MRNs sit beside these; select
    demographic columns only, never identity ones, and keep every result aggregate.

37. **Heavy settings editing is the most engaged behaviour in the pool, not an artefact.**
    42 eligible donors record more than 50 therapy-editing sessions per 30 days (24 twiist,
    18 Omnipod), and I called them an upload pathology twice before checking. They are
    people: ISF lands on round mg/dL (41→35, 42→43→45), basal moves in 0.1 U/hr steps,
    schedule SEGMENTS are added and removed — which no adaptive algorithm does — and they
    edit LESS overnight than ordinary donors (9.6% of rows in 01:00–05:00 local against
    14.6%, uniform being 16.7%). Their outcomes are the best in the pool: median TIR
    **88.0% against 75.1%** (p<0.001), with time below 70 at 2.58% against 1.70%. The
    exemplar runs 89.3% TIR at 8.1% below 70, 17 boluses and 12 carb entries a day.
    Association, not effect — the capacity to tune and the result of tuning are not
    separable here.

    **Method note that made the difference:** the hour-of-day test only works in LOCAL
    time. Casting `deviceTime` returned nulls and scored 0.0% for every group, which reads
    as a result rather than a failure; `time + timezoneOffset` gives the real distribution.
    A zero that is identical across two very different groups is a broken measurement.

38. **Count the cohort from what exists on disk, never from what was selected.** The
    justification published N=107, which was wrong twice over: it counted donors whose
    exports had FAILED (selection lists are not cohorts), and it dropped the 11 bddp
    donors because their ids were not in any alias map, so they could not be screened.
    The real figure is 115. Derive N by joining `cohort.csv` to the screen and applying
    the gates — anything computed from an alias map counts intentions.

    **The bddp ids were recoverable all along.** Each export's `_export_manifest.json`
    carries `uid_fingerprint` = sha256(_userId)[:12], so hashing the ids already held
    locally matched all eleven with no query at all — written to `bddp_alias_map.json`.
    The manifest was designed for exactly this and I had forgotten it existed.

39. **`expectedNormal` cannot detect an interrupted AUTOMATIC bolus, in any uploader.**
    (2026-09-07, pool-wide ~1 year, `bolus/mutable` rows excluded — a mutable row carries
    the PROGRAMMED amount and reads as fully delivered.) Of 67.5 M automatic boluses, ZERO
    record `normal < expectedNormal`. That is silence, not a rate of zero, and the two
    uploaders fail in opposite ways: **Loop never writes the field at all** (0 of 56 M rows,
    automatic *and* manual) — an interrupted automatic bolus is written as a smaller
    automatic bolus, indistinguishable from an intended one; the **no-app-name uploader**
    (`deviceId` null, `origin` only a UUID; 2,044 auto-bolusing people) stamps it on 99.9%
    of rows *always equal to* `normal`, and never encodes a shortfall on those people's
    6.4 M manual boluses either. Only twiist populates it meaningfully — 45,489 of 2.1 M
    manual boluses (2.2%) — and twiist has no automatic bolus at all, it automates through
    basal. **The trap that cost a query**: a pool cross-tab reporting "2.6 M automated rows
    with expectedNormal, 29.7%" was entirely the mirroring uploader. Always check
    `normal < expectedNormal`, never mere presence of the field. For a Loop cohort the
    question has to go to `dosingDecision.recommendedBolus` matched forward to the bolus
    that follows.

40. **Interrupted automatic boluses are a user behaviour, and they scale with dose size**
    (2026-09-07, `cancel_rates.py` / `cancel_cause2.py` / `cause3.py`; 67 Loop donors,
    120 days, 546,718 matched automatic boluses, 19.6 person-years). Loop records only the
    delivered amount, so the signature is `delivered < recommendedBolus` from the matched
    `dosingDecision` — see [[lesson 39]] for why `expectedNormal` cannot do this. Pooled
    rate **1 in 709 boluses**, 39 per person-year, and strongly heterogeneous: per person
    0.61 per 1,000 at the median, 0.00 at p10 (10 of 67 interrupt nothing in four months),
    9.33 at the max, with the top decile of donors carrying 42% of all events. Exposure
    does not explain it — automatic boluses per day varies 3×, the rate 15×.

    **The rate rises with the size of the bolus far faster than duration explains**:
    0.06 per 1,000 at 0.05–0.15 U against 40.4 at 2.5 U+, a log-log slope of **1.67** where
    a constant-hazard, time-at-risk process (occlusion, a comms drop) would give 1.0. A
    person reacts to a big number; a fault does not know how many units were programmed.

    **Attribution needs a matched control** — "66% had a deviceEvent nearby" was meaningless
    until the same window was measured around boluses that completed, and controls must be
    matched on donor AND recommended size, because size drives the rate that hard. Against
    3,809 such controls: a manual bolus takes over 55.3% (base 11.2%), an outright suspend
    26.6% (base **0.2%**, a 143× lift), both 3.4%, no marker 12.2%. Pump/pod faults are
    **2–3%**: the pod-change lift decays as the window opens but the excess plateaus at
    13–16 events, and pump alarms independently give 12–14; 10 of the 12 tight-window fault
    events also show a suspend, which is the fault signature (alarm → suspend → pod swap).

    **The window has to fit the mechanism.** A pod change was invisible at −2/+5 min — the
    user has to notice, fetch a pod, fill and prime it. Sweep the forward window and read
    the EXCESS COUNT, not the rate: a real signal's excess plateaus while its lift decays,
    a spurious one's excess grows as the window swallows the ordinary three-day pod change.
    (The "no delivery for >1 h afterwards" test is worthless here for the reason Pete gave:
    people replace a pod quickly and dosing resumes. It caught 2.3%.)

    **Limit that bounds all of it: this sees only interruptions Loop KNOWS about.** A cancel
    and a suspend go through the app, so Loop writes the reduced amount. If a pod occludes
    mid-bolus and the phone is never told how much reached the body, Loop writes what it
    believes was delivered and the shortfall does not exist in the record — which is the
    likely reason **zero** of 1,545 occlusion alarms sit near an interrupted bolus. The 2–3%
    fault share is a LOWER bound.

    Method notes: `bolus/mutable` rows are duplicates, not unfinalized boluses — 99–100%
    have a finalized twin within 60 s and the amount is identical every time, so dropping
    them changes the unmatched rate by 0.001 points. The whole decision-to-bolus match runs
    in one SQL query (`first_value(...) IGNORE NULLS` over a union of decisions and boluses,
    ties ordered decision-first), which is what makes a 67-donor 120-day window affordable
    where a per-donor loop took hours.

41. **The Databricks credential is Tidepool PRODUCTION PHI, not a de-identified research
    extract** (inventoried 2026-09-16). It authenticates as a `@tidepool.org` user against
    `prod.default` — 29 tables, of which `device_data` is one. The identity tables sit in the
    same schema and join on the same `_userId`: `users` / `all_users` (email, first/last name),
    `seagull_profiles` (fullName, mrn, birthday, gender, diagnosisType, diagnosisDate,
    targetTimezone), `patients` / `patient_with_summary` (fullName, email, birthDate, mrn,
    clinic linkage), `consent_records` (ageGroup, ownerName), `c2c_create_history` (patient
    fullName + email), `device_data_sets` (device serial, upload client, `provenanceSourceIP`),
    plus `redox` and `xealth_order`, which are raw EHR/HL7 message tables carrying patient name,
    DOB, sex, race, religion, marital status, street address, phone, email and provider NPI for
    the clinic population. Coverage for donors is effectively total: of the 34 donor ids in the
    local alias maps, **34 of 34 resolve to an email address and a full name**, 33 to a birthday
    and a diagnosis date, and 24 are linked as a clinic's patient (5 with an MRN).

    **So `_userId` is a direct identifier, not a pseudonym** — the alias discipline is what
    stands between an export and a named person, and nothing about the query surface enforces
    it. Never join `device_data` to an identity table, and select demographic columns only when
    a demographic question requires them (see [[lesson 36]]), never identity ones.

    **The clinical stream is not de-identifiable by dropping the id, either.** What we export
    carries full-resolution timestamps, `timezone` (10.2 M donor rows), device serial numbers
    (6,479) and transmitter ids (2,183) — dates finer than a year and device identifiers are
    each HIPAA Safe Harbor identifiers on their own. And the trace itself is a fingerprint: a
    Nightscout (time, amount) bolus list located one person in an "anonymized" BDDP extract at
    686/686 exact matches. Treat a donor export as identifiable data that happens to lack a
    name, which is why they live under `~/.loop-eval/` and never in the repo. The manifest's
    `uid_fingerprint` is sha256(`_userId`)[:12] — a join key for us, and a confirmation oracle
    for anyone who already holds the id list, so it is not an anonymisation measure.

42. **The post-ETL export is already a limited data set; the hazard is what sits NEXT to it**
    (audited 2026-09-16, 56 exports under `~/.loop-eval/trait-cohort/full/`). Every field the
    ETL writes is numeric or temporal — `glucose.json` is `startDate` + `quantity`; `doses.json`
    adds volume/rate/type/automatic; `carbs.json` is grams + three timestamps + absorptionTime
    with **no food name**; `therapy.json` is the four schedules, limits, suspendThreshold and
    `overrideWindows` with **no preset name**; `disruptions.csv`'s `notes` is a generated
    `"<reason> <N>min"` string, not user text; `pNN.pkl` is one `bg` column on a UTC index.
    Tested directly: **not one file under `full/` or `logs/` contains any of the 115 real
    userIds.** Everything identifying in `device_data` — deviceId, serials, `payload`, `origin`,
    free-text names, named timezone — is gone because the ETL selects only what the simulator
    needs. Two residues: the manifest's `uid_fingerprint`, and absolute full-resolution
    timestamps (therapy.json's local-midnight schedule boundaries also leak the UTC offset,
    which is what `offsets.csv` infers).

    **The linkage sits one directory up.** `trait-cohort/cohort_userids.csv` has a `userId`
    column beside the alias and every screening metric, and there are eight `*alias_map.json`
    files next to it. Sharing `trait-cohort/` ships the key; sharing `trait-cohort/full/` does
    not. And **`~/.loop-eval/cache/` is the dirtiest thing on disk** — 4,353 files whose
    *filenames* embed the Nightscout hostname (20 distinct hosts, some personally named), even
    though the contents are clean. `runs/` is clean: aliases only, no host in any filename
    across 58 run dirs, and no id-shaped token in the distribution CSVs.

43. **A fresh PNG mtime is not a fresh figure, and `claims.py` now exists because prose
    cannot be re-derived** (cohort 73 -> 159, 2026-09-16). Four things this pass taught:

    - **Figure 15 READS `vol_lows.csv`/`vol_highs.csv`.** Redrawing it after a cohort change
      stamps a new mtime on a panel still showing 51- and 68-person numbers. Lesson 22's
      stale-intermediate failure survives a figure rebuild, so check a view's *inputs*, not
      its output timestamp. Regenerate the table, then the figure, then `web_figs.py`, then
      `make_artifact.py` — in that order.
    - **Write the claims script.** `analysis/dist_views/claims.py` prints every published
      number beside what the current tables and raw samples give, so a rewrite is a
      transcription instead of a recollection. It immediately caught four definitions that
      had drifted apart: person-days (cohort.csv vs wholerecord.csv), the EWMA half-life
      (`lam` is the decay, so ln2/-ln(lam), not ln2/-ln(1-lam)), the value lattice (spacing,
      not integrality), and figure 15's "enough events" floor (100 for lows, 30 for highs —
      using `ci_lo.notna()` instead gave 142/105 people where the figure says 108/82).
    - **The CGM clamps are 39 and 401 mg/dL, not 40 and 400** — the values round-trip
      through mmol/L. An exact `v <= 40` finds 4 people at the floor where 80 are there, and
      an integrality test finds no value lattice at all. Also `coverage_pct` in `cohort.csv`
      is the share of the PANEL surviving cleaning, not sensor coverage; wear is
      `screen.csv`'s `wear` (median 96.4%). The study had been quoting one as the other.
    - **`style.cohort("core"/"targeted")` does NOT apply the eligibility gate**, only
      `"modelling"` does. Figure 00 printed 109 targeted people where 96 pass the gates.
      Take strata as `co[co.stratum.eq(...)]` off the gated frame.

    **What actually moved, for the record:** despiking took excess kurtosis 3.05 -> 2.30 and
    the increment's ICC **0.12 -> 0.49**, so increment kurtosis is no longer "the least
    personal feature" — volatility memory (0.27) is. The momentum zero-crossing went 40 ->
    45 min, between-day variance 14% -> 17.5%, Hurst_long 0.30 -> 0.32. The trait space's gap
    statistic now clearly prefers ONE cluster (1.063 vs 0.887) while its dominant axis still
    separates dosing strategy, 143 of 158 people on the consistent side. And the two
    Nightscout sites fell out of the cohort silently — they have no `wear`/`loop_frac` in
    `screen.csv`, so the eligibility gate drops them on missing data rather than on a
    decision. The study is now BDDP-only; that was not chosen.

44. **The study is FOUR documents now, and the split found a bug that the single page had
    hidden** (2026-09-16). `page.py` holds the shared chrome and a companion-link strip;
    `doc_glucose.py` / `doc_insulin.py` / `doc_conditioning.py` / `doc_counteraction.py` each
    own one body; `make_artifact.py` builds all four. Still run `web_figs.py` first.

    **Figures 03 and 04 were measuring the mirror image of their own captions.**
    `panel["v"]` is `bg.diff()` — the increment that ARRIVED at the current reading — so
    `E[v | bg]` answers "how did I get here", which for a mean-reverting series rises with
    glucose because you reach a high level by rising. The restoring force is the increment
    that LEAVES. Both curves cross zero near the same place, which is exactly why two years
    of captions saying "it slopes downward" sat above a panel sloping upward without anyone
    noticing. Corrected (`style.restoring_force`), the force falls from about +7 mg/dL/hr at
    a glucose of 50 to −2 above 300, **156 of 159 people** have a crossing inside their
    observed range, and the set point runs 94–253 mg/dL (median **152**) with a five-fold
    independent spread in stiffness — a far better result than the broken version, whose
    third panel put one person's set point at −60,000 mg/dL. **Condition the forward
    increment on the PREVIOUS reading**, not the one it starts from: sharing a reading puts
    its sensor error inside both terms and biases the slope toward zero. When a figure and
    its caption disagree about a SIGN, believe neither until you have recomputed it.

    Three more of the same family, all found by looking at rendered PNGs beside the data:
    - **Figure 06's panel title said "falls steeply as glucose rises" while its lines rose.**
      Appearance does rise, at 0.47 mg/dL/hr per mg/dL — but **84% of that is insulin action's
      own slope** (0.39), which the identity `appearance = velocity + action` then requires
      appearance to offset. The residual is 0.06. An "apparent dose-response of endogenous
      appearance to glucose" is mostly the reflection of the dose.
    - **Hardcoded figure subtitles rot exactly like prose.** Fig 05 announced "3% to 81%,
      median 48%" above a panel printing 47% from 159 people; fig 24 announced "2.71 raw,
      2.88 conditioned" above panels showing 2.57 and 2.71; fig 12 claimed "roughly one
      velocity SD" for what is 0.44 of it and "one person (bddp08)" for what is now five.
      All three now compute from the same arrays the panels draw.
    - **Don't quote another cohort's rate in a document.** The insulin page had lesson 40's
      "1 in 709 interrupted automatic boluses" in it, measured on 67 donors over 120 days —
      a different sample entirely (lesson 27). Made qualitative instead.

**Scope:** observational, summative, factual, and **Loop users only** — the two oref/Trio sites
are excluded in `build.py` (`SKIP_ALIASES`) since 2026-08-26: a different controller shapes the
trace differently and two people cannot characterise that difference. Candidate mechanisms and
therapy proposals go to `docs/candidates/README.md`, not here.
