# The excess lows reproduce without the ICE plant — and without frozen behavior

From the **simulator** role, replying to the **ice** role's
`runs/2026-10-10-replay-lows/HANDOFF.md`. Written 2026-10-10. Measurements are on `bddp11` (a
curve-validated bed), 59 days, deployed config, built-in counterfactual. The evidence CSVs and
traces stay in that run directory; this file is the argument.

## Summary

Your replay's setup is not the problem. I checked the three config infidelities it has and none of
them tracks the outcome, using your own per-donor data and two tests stronger than the ones in the
handoff. The excess lows then reproduced in **our** engine, on a validated bed, with no ICE plant
involved and with the person's own boluses delivered verbatim: **130 crossings below 54 against the
field's 26**.

The mechanism is the one already in the project notes, now with numbers: **the counterfactual
corrects field highs the real system left standing, and the correction lands 2–3 h later as a low
that never happened.** 72% of our excess lows follow a field high.

Frozen behavior may still explain your *spread* result — ours does not inflate spread, so our
engine neither confirms nor refutes that part. But the *frequency* result, which is the headline,
has a simpler cause that sits upstream of your plant.

## What I ruled out, and how

**ISF_tdd vs schedule ISF.** Your `isf_ratio.py` correlates against the signed ratio. A mismatch in
*either* direction widens spread, so a signed test can read ~0 while magnitude drives everything. On
`|log ratio|` the correlations are −0.13 / +0.22 / −0.28 (sd_ratio / dt54 / dtir), all p > 0.19 —
your conclusion survives the stronger test. The cleaner argument is in your own table: **i039 and
i001 have ratios of 0.991 and 0.985 — essentially no mismatch — and still show 30% spread
inflation.**

**Overrides.** `--apply-overrides` is not passed and 19 of your 24 pilot donors have override
windows in the held-out 28 days (median 7.4% of the window). Spearman against the excess: −0.10 /
−0.05 / −0.03. The pattern is actively against it — **i002 sits at 96% override exposure with
+0.50 t<54 and −0.16 TIR (nearly clean), while i040, i066, i006 and i012 have zero overrides and
are among your worst donors.** Worth closing as a fidelity gap; not the cause.

**Unused per-donor inputs.** `decision_times.csv` and `stale_cgm.csv` are in every donor directory
and neither is passed. So `no_dose_guard` cycles — 865 of 48,890 (1.8%) for i001, where the field's
Loop issued nothing *by design* — get dosed on, and `--cgm-stale-guard-min` is left at 0 despite
`verification.md` prescribing 5. Real, small, worth fixing.

## What it is

On bddp11 at deployed config, varying only the manual-bolus mode:

| mode | manual insulin | boluses zeroed | t<54 | crossings <54 |
|---|---|---|---|---|
| field | 915 U | — | 0.48 | 26 |
| recommendation (the default) | 915 → 1075 U (+17%) | 1542 / 2989 | 1.94 | 126 |
| IOB-resize fallback | 915 → 372 U (−59%) | 1480 / 2989 | 0.91 | 70 |
| **verbatim passthrough** | **915 → 915 U** | **0** | **1.85** | **130** |

With the person's exact doses, unaltered, the excess is undiminished. Total insulin is only +4%.
Mean runs 18 mg/dL below the field.

Where the lows come from:

```
130 counter crossings below 54
  field also low at the crossing:   37 (28%)
  field NOT low:                    93 (72%)  — field median 91 mg/dL, counter 40 lower
  2 h before a new low:  field median 171 mg/dL,  above 180 in 43% of cases
  3 h before a new low:  field median 166 mg/dL,  above 180 in 44% of cases
```

The real system left those highs standing — pump comms, an occlusion, open-loop time, or the person
simply not acting — and the replay corrects them. This is the same shape as your finding 2 (field
median 81 with the replay 14 lower); ours is the same phenomenon at larger amplitude.

## Three things this changes for you

**1. A glucose floor would mask this, not fix it.** I initially suggested one, on the grounds that
your plant's only defense is `max(..., 20.0)` at `plant.py:234` — no defense anywhere in the 20–54
band the metric measures. That is still true and still worth knowing, but it cannot be the cause of
*more frequent* lows, because a floor changes a low's depth and duration and never how often one
starts. Measured on our bed: turning the floor off moved crossings **126 → 89** while t<54 went
1.94 → 4.20. It trades duration for frequency. Pete made this point and he was right.

**2. The manual-bolus default is not passthrough, in your runs either.** `SimulateCommand` defaults
`--candidate-manual-bolus-from-recommendation` to **true**, so every hands-on replay substitutes the
candidate's own recommended bolus for the person's. Verbatim passthrough needs **both**
`--no-candidate-manual-bolus-from-recommendation` **and** `--no-candidate-iob-adjust-manual-boluses`
(the precedence is `fromRecommendation → iobAdjust → verbatim`, first match wins). This is not the
cause of the lows, but it does mean your delivered-insulin numbers describe a dosing pattern that is
not the donor's. Now documented in the simulator guide §12.

**3. Several of your donors' "manual" boluses are Loop's automatic ones, mis-flagged.** i003 shows
20.4/day at 27-minute median spacing and 0.15 U median; i006 shows 22.7/day at 10 minutes. No person
boluses like that. Those three donors (with i009) have 3× the median t<54 excess and 3.3× the TIR
loss of the rest — suggestive at n=3, p=0.13 on the continuous test, so treat it as a lead rather
than a result. It is an ETL question, upstream of both harnesses.

## Engine change you will pick up on your next merge

`--external-plant` bypassed the counterfactual's CGM-gap re-anchor: the guard lives inside
`while externalPlant == nil` in `ClosedLoopSimulator.swift`, so a plant never saw it. That is the
bug you hit (77 h gap → 2,300 mg/dL) and fixed in `72a9cfd`. The harness now applies the same rule
to the plant's returned samples, because the gap is a property of the data rather than of the
plant's physiology: it takes the gap-end level from the real CGM and carries any pre-gap divergence
over 10 mg/dL across, and logs when it fires. `--cf-gap-reanchor-min 0` disables it.

Your plant re-anchors at 2 h and the engine now does so at 30 min, so **this will change your
numbers** — both guards firing is harmless (re-anchoring twice to the same value is idempotent), but
the engine's threshold is tighter and fires more often. Re-run before comparing against anything
from before the merge.

## Two smaller notes

- **i056 has `sd_ratio` 8.00** against a cohort median near 1.1, and it is inside your pooled
  medians. Worth excluding or explaining before the cohort numbers travel.
- **Your suggested spread metric is a good idea and I did not add it**, because on our engine it
  would not have caught anything: our sd ratio is 0.91 with the floor on and 0.96 with it off, i.e.
  narrower than the field in every configuration, while still producing 5× the low events. Spread
  and low-frequency came apart here. If it goes into `score_counterfactual`, the crossing *count*
  belongs beside it — that is the statistic that moved.

## Where I would look next

Disruption and occlusion coverage, not the generator. If the replay is correcting highs the real
system could not correct, the fix is knowing when the real system was unable to act. Your
`disruptions.csv` already carries suspends, loop-offline and pump errors; the question is whether it
covers the windows preceding these specific crossings. A direct test: take the 93 new-low crossings,
look 2–3 h back, and check what fraction of those field highs sit inside a disruption window already
in the CSV. If most do, exclusion fixes it; if few do, there is a class of "real system was not
dosing" that the ETL is not yet detecting.
