# ETL: every basal dose is exported `automatic: True`, including the user's own manual temps

**From:** additive · **To:** simulator (ETL / analysis package) · **2026-11-04**
**Asked for by Pete** in session: "we should make sure that the ETL layer is recording automatic
versus manual."

## The defect, in one line

`etl.py` writes every basal dose record with a hard-coded `"automatic": True` — including the temp
basals the USER set on the pump, which the same loop has already identified correctly two lines
earlier. The information is computed, used for one purpose, and then contradicted in the export.

```python
# etl.py ~1383, inside the basal segment loop — correct, and this is the right discriminator
manual = dtype == "temp" and str(getattr(r, "orig", "")) != "com.apple.HealthKit"
segs.append((st, st + dur_ms, rate, delivered, dur_ms, recv, btype, manual))
...
# etl.py ~1419, the same loop, `manual` in scope and unused
doses.append({**extra, "deliveryType": "basal", "startDate": _iso(st), "endDate": _iso(en),
              "volume": round(vol, 5), "tempRate": round(rate, 5),
              "insulinType": insulin_type, "automatic": True})      # <-- always True
```

`manual` is currently consumed only by `manual_iv` → the `tidepool/manual_temp_basal` rows in
`disruptions.csv`. So a consumer reading `doses.json` alone cannot tell Loop's dose from the
person's, and if it trusts `automatic` it gets the wrong answer for every manual temp.

**The bolus side already does this right** and is the precedent to match (`etl.py` ~1296):
`auto = (r.subType == "automated")` → `"automatic": auto`, with the HealthKit subType-stripping
caveat handled at ~1220.

## Suggested fix

1. **`"automatic": not manual`** in the basal append. One line, the flag is already in scope, and
   the field already exists in the schema, so **no consumer breaks** — they just stop being lied to.
2. **Keep the raw `deliveryType` as well, under its own key.** `extra["basalType"] = str(dtype)`
   looks like it writes the raw Tidepool type but does not: the 7th element of `segs` is `btype`
   (derived from `suppressed`-presence), and the unpacking at ~1391 names it `dtype`, shadowing the
   raw value out of scope. So Loop's commanded temp (`deliveryType='automated'`, suppressed set) and
   the user's manual temp (`deliveryType='temp'`) both export as `basalType: "temp"`. Measured over
   the 205 `ice_v32` exports: `basalType` takes only `temp` / `scheduled` / `suspend`, never
   `automated`. Either rename the inner variable and carry the raw type through, or add
   `"manual": manual` beside the flag — whichever you prefer; one of the two needs to survive.
3. **Capture the suspend reason, if Tidepool populates it.** `_suspends`'s status query (~606)
   selects `t_ms` and `status` only. Tidepool's `deviceEvent subType='status'` schema carries a
   `reason` payload that distinguishes a manual suspend from an automatic one — worth a bounded
   check against the warehouse, and capturing if present. Today a user pulling the pump and a pod
   fault are indistinguishable in everything we hold, which is the half of Pete's question that our
   exports genuinely cannot answer.

## Why it matters, measured

The scale, from `runs/2026-11-04-additive-suspendclass/` (205 `ice_v32` exports, additive LESSONS
699):

- **Manual temps reach 31 of the 168 scored donors** — 3007 episodes / 2118 h. While one runs, Loop
  logs recommendations and enacts none (i040 ran 0.05 U/hr manual temps through recommendations of
  2.35–3.0 U/hr).
- Any statistic that reads donor delivery as the *controller's* output is contaminated for those
  donors. In additive's scorecard that is `zero_frac`, `med_nonzero`, `conc1`, `day_night`,
  `night_cv`, `tdd_cv`, `ac1`, `p99` and `tdd`. Re-measured with the person's own pump actions
  removed, the targets move (`zero_frac` 32.49 → 31.54, `night_cv` 35.36 → 34.30) — small enough
  that additive is **not** re-basing its scorecard, each correction being under its row's own
  between-draw scatter, but the direction is only knowable because the ETL kept `manual` internally.
- It also bears on the replay side, which is yours: a replay that doses through a window where the
  field was running a user-commanded temp is measuring the sim against something Loop did not
  choose, the same class of problem as replaying through a suspend.

## Re-export, which is the real cost

The one-line flag fix changes no existing numbers — `automatic` on basals is not read by additive's
scorer today — so **it does not require a re-export on its own**. It needs a data-version bump and
should ride the next data-changing re-export, which the project already owes (memory:
*ICE pilot re-export owed (v32)* — re-export into a new root with the next data-changing change).
Batching it there is cheaper than a root of its own, and additive has no deadline on it.

Verification once it lands, cheap and specific: on a donor known to use manual temps (i040 is the
worked example, 6.4% of its time), `doses.json` should show `automatic: false` on basal records whose
spans coincide with that donor's `tidepool/manual_temp_basal` rows in `disruptions.csv`, and
`automatic: true` everywhere else. The counts should reconcile to the manifest's `manual_temps`.
