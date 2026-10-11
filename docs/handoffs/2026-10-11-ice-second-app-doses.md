# A second app records doses on the same days as Loop for four pilot donors

From the **simulator** role, for the **ice** role. Written 2026-10-11. Pilot aliases.

## Summary

For **i156, i105, i053 and i042**, Trio (`org.nightscout.Trio`) uploads bolus and basal records on
the same days that Loop records its own and makes every dosing decision. Most Trio boluses copy a Loop
bolus. The rest match nothing Loop recorded (Trio-only automatic boluses, and some larger manual
ones), and nothing in the data says whether they reached this person's body. Those unmatched boluses
are the whole excess: exports read +18% to +74% over Loop's own bolus total in the overlap months.

**Handled in the ETL from DATA_VERSION 22 (dfd5b3a).** It drops second-app copies (bolus within ±2 min
at the same units; basal on days the controller recorded basal). It keeps the unmatched boluses and
lists their days in each export's **`dose_doubt.csv`**. Exclude those days wherever insulin must be
known. They aren't in `disruptions.csv`, because the pump was delivering and the replay must not clamp
it. Re-export the four donors to get the file.

| donor | doubt days (v22) | export bolus vs Loop's own, overlap months |
|---|---|---|
| i156 | 91 | +18% to +33% |
| i105 | 26 | +67% (September) |
| i053 | 29 | +64% to +74% |
| i042 | 6 days in August (not yet re-exported) | +84% (August) |

The same export fixes a second bug on these donors: an unpaired `suspended` status event held i156 in a
disruption from 06-06 to the window end, and similar windows ran for weeks on i105, i053 and i130. A
suspend with no `resumed` edge now ends at the first delivery after it.

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
donors), `overlap_days.csv` (days both apps recorded boluses).
