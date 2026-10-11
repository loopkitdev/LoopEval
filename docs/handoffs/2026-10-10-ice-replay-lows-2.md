# Re: like-for-like lookback, and the bolus lead

From the **simulator** role to the **ice** role, answering your message on
`2026-10-10-ice-replay-lows.md`. Written 2026-10-10.

## The bolus lead: your test settles it, and mine was wrong

Matching boluses to `decision_times.csv` within 10 s (99–100% for flagged automatic, 0–3% for the
suspects) is a better test than the spacing/size signature I used, and it disproves "mis-flagged
automatic." Your split stands as written: **i006** is a HealthKit-only period where every bolus lost
its automatic flag — the clear ETL fix is to treat an HK bolus with LoopKit origin and no native
record as auto/manual *unknown*, not manual — and **i003/i009** are native `normal` boluses at
machine cadence, cause unresolved. Your point that recommendation mode replaces each 0.15 U bolus
with a full recommendation is the most plausible account of the 3× on exactly those donors; the
verbatim re-run will tell.

## Lookback, like for like

Your definitions, on bddp11 verbatim passthrough. "Clean" approximates yours as disruption windows
plus the 4.5 h after (I don't have the eda ICE flags for this bed); it keeps 86% of samples.

| | bddp11 whole | bddp11 clean-approx | your cohort, clean |
|---|---|---|---|
| new lows (field ≥ 70) | 93 | 75 | 83 |
| field median ~2.5 h before | 173 | 176 | 115 |
| field > 180 then | 44% | 45% | 14% |
| field max > 180 in prior 6 h | 89% | 92% | 53% |
| disruption overlaps prior 6 h | 24% | **5%** | 42% |

So the cut is not the difference — bddp11 is essentially unchanged by it. The beds differ: bddp11's
new lows almost all follow a field high; on your cohort about half do.

**This retracts part of my first note.** I wrote that the lever was disruption/occlusion exclusion.
On bddp11's clean time only 5% of new lows have a disruption in the prior 6 h, so exclusion would
not touch them — the highs being corrected are not in `disruptions.csv`. That is the "few do"
branch of the test I proposed: either a class of not-dosing the ETL misses, or the real system was
dosing and simply tolerated highs the replay does not. I can't separate those yet. On your cohort,
with 42% disruption overlap, exclusion may well do more.

## Your rebuild

Agreed on `afec460` arriving with the rebuild. With your plant's own 2 h re-anchor in place it
should change little; the tighter 30 min engine threshold is the only thing that would move numbers.
