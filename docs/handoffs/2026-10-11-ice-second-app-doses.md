# A second app records doses on the same days as Loop for four pilot donors

From the **simulator** role, for the **ice** role. Written 2026-10-11. Pilot aliases.

## Summary

For **i156, i105, i053 and i042**, Trio (`org.nightscout.Trio`) uploads bolus and basal records on
the same days that Loop records its own and makes every dosing decision. Most Trio boluses copy a Loop
bolus a few seconds to two minutes later. The ETL's dedup keys on the exact second, so those copies
survive into `doses.json`. The rest match no Loop record at all, and nothing in the data says whether
they reached this person's body. **The recorded insulin on these donor-days is unreliable, by tens of
percent, in a direction we can't resolve.** Exclude the days below from ICE extraction and scoring.

| donor | overlap days (UTC) | Trio boluses matching a Loop bolus (±2 min, same U) | export bolus vs Loop's own, overlap months |
|---|---|---|---|
| i156 | 93: 2026-07-06 → 10-06 | 86.5% (1,939 U duplicated) | +28% to +49% per month |
| i105 | 29: 2026-08-25 → 09-22 | 94.3% (467 U) | +72% (Sept) |
| i053 | 29: 2026-09-08 → 10-06 | 90.5% (225 U) | +109% (Sept), +112% (Oct) |
| i042 | 6: 2026-08-03 → 08-19 | 46.0% (12 U) | +84% (Aug) |

Day lists: `~/.loop-eval/runs/2026-10-11-dose-apps/overlap_days.csv`.

## What is fine

- **HealthKit mirrors (34 donors).** Export bolus totals equal Loop's own within about 1% in almost
  every donor-month. The large jumps (i006 July, i151 June, i206 June, i113 September, i182 October)
  are months where Loop's native records are missing and the export equals the HealthKit total: the
  mirror filled a gap rather than doubling one.
- **App switchers (i030, i083, i130, i171).** Loop and the other app (Trio, or twiist for i171) never
  record on the same day, so the export joins two periods correctly. Separately, those Trio and
  twiist periods carry no Loop dosing decisions, so a Loop-controller replay of them isn't
  deployment-faithful.
- **Single-app donors (159).** Their exports hold a median 4.8% less bolus insulin than a raw sum of
  Loop's records. That gap is Loop uploading some boluses twice under one syncIdentifier, which the
  ETL collapses correctly; checked record by record on i001.

## Evidence

`~/.loop-eval/runs/2026-10-11-dose-apps/`: `bolus_by_app_active.csv` (active records per donor and
app), `bolus_excess.csv` (export vs Loop, whole window), `overlap_months.csv` (per month, multi-app
donors), `overlap_days.csv`.

## Not done

There's no ETL change. Dropping the Trio rows would remove the copies but also the unmatched doses,
which may be real. Keeping them double-counts. Which is right needs the person's setup, not the data.
