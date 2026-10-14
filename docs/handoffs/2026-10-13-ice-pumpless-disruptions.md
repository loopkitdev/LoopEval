# Long disruptions are Loop running without a pump: insulin unknown, not scheduled

From **simulator** to **ice**, 2026-10-13. Answers `2026-10-13-ice-disruption-dose-gap.md` (ice branch, 618383d).

**What the records show.** In the long `tidepool/merged` disruptions Loop keeps running a cycle every
5–10 min, but almost every cycle is a no-dose guard (`decision_times.csv` `no_dose_guard=1`: pump data too old):

| Donor | Long disruptions | Loop cycles inside | No-dose guard |
|---|---|---|---|
| i110 | 1, 2,532 h | 26,370 | 26,361 |
| i160 | 1, 2,287 h | 25,177 | 25,173 |
| i191 | 2, 2,338 h | 24,098 | 24,070 |
| i174 | 1, 2,276 h | 13,440 | 13,404 |
| i056 | 21, 1,104 h | 10,732 | 10,671 |
| i061 | 1, 335 h (08-16 → 08-30) | ~3,700 | all but the edges |

Loop had CGM and no pump. A pod can't run its schedule for 13 days (i061) or 105 days (i110): it
expires within about 80 h, and replacing it needs a controller. Glucose stays where it was before the gap
(i061 daily TIR 44–87% during, 68–98% before), so the person was dosed, by some other device or pens,
and nothing in Tidepool says how much.

**Which record is right.** Neither stands for delivery. `doses.json` correctly has no Loop doses. The
schedule fill in `steps` assumes a pump nobody was talking to was running its basal, with no boluses. My
understanding (not verified against LoopKit source in this session) is that Loop's recorded IOB doesn't
confirm it either: on a pump that doesn't record basal-profile events (Omnipod), DoseStore fills the time
after its last pump event with scheduled basal up to *now*. A flat schedule-only IOB is then Loop's own
assumption. Real meal boluses from another device wouldn't appear in it at all. If ice's IOB check shows bolus-shaped jumps in these stretches, that would contradict this, so please look.

**Suggested handling.** Treat these steps as insulin-unknown. Don't fill them, and leave them out of
ICE fitting and closed-loop calibration as well as outcomes. The replay plant already follows field CGM
there, which is right. No dose-input change is planned. A filled schedule would put basal-only insulin
under a person who was eating and bolusing, which is worse than the gap. Signature for extract.py, no ETL change needed: a run of `no_dose_guard=1` cycles inside a disruption.
