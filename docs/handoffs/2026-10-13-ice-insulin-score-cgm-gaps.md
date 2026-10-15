# i056 held-out insulin gap: field counts insulin from hours the replay cannot run

From **simulator** to **ice**, 2026-10-13.

ice's v30 held-out scores (`rollout_scores_v3v28s1ccsp_cfg_rw24_slow3_v30.csv`) show i056 at
33.9 U/day in the field against 24.5 U/day in the replay, the only large insulin gap among the 24
donors. TIR and t<54 match. It is a scoring mismatch, not a replay error.

**What the numbers are.** i056 has about 400 of the window's 672 hours inside disruptions
(`disruptions.csv`: merged disruption windows of 10–76 h, plus loop_offline). In most of those
hours there is no CGM at all, so neither arm is stepped there. In a deployment-faithful closed-loop
run of the v30 export (held-out window, i056's GBAF and IRC+clamp flags):

| Delivery (U, 09-08..10-06) | Replay | Field |
|---|---|---|
| Outside disruptions | 630.8 | 627.7 |
| Inside disruptions, CGM-less | 7.2 | 138.3 |
| Inside disruptions, at the edges of CGM | 0 | 176.2 |

Outside disruptions the replay delivers what the field did, to 0.5%. The rest of the field's
insulin is scheduled basal (about 21 U per day) that the pump ran while Loop was off and no
CGM was recorded.

**Why the score differs.** `rollout.py score()` takes the field's `insulin_u` from every step in
the window (`te`, including long gap-spanning steps) over the full 28 days. The replay's comes
from the plant's dose log, which only has entries where the plant ran, over the span of its own
BG log (26.4 days for i056, since the window opens inside a 51-hour disruption).

**Suggested fix.** Score both arms' insulin over the same intervals: the field's insulin restricted
to steps where the replay arm also has a step, or both restricted to `clean` steps. With
that, i056 should read about 24 U/day in both arms. Other donors with long disruptions
will shift a little the same way.

**Residual worth knowing.** In the first 1–2 h after a long gap the replay can run up to ~35 mg/dL
lower than the field (i056 09-16 12:24, after a 10 h disruption). It closes within four hours. It
doesn't affect the insulin totals.

Evidence: replay trace in the simulator session's scratchpad (`i056/cl30.json`). It reproduces with
`loop-eval simulate` at main c81ed2a on `ice_v30/full/i056`.
