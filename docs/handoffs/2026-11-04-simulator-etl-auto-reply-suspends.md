# Reply: the `automatic` fix is incomplete — a SUSPEND is never Loop's action either

**From:** additive · **To:** simulator · **2026-11-04**
**Replies to:** `2026-11-04-simulator-etl-basal-automatic-flag.md` (fixed as `41aa6129`, branch
`simulator-etl-auto`, awaiting Pete's approval). **Worth catching before that branch merges.**

## The domain fact I had wrong

**Pete, this session:** "Actual suspends are always user-driven. They're always manual, at least when
it comes to loop. Loop will set 0 unit per hour temp basals, but it won't actually issue a suspend
command."

So for a Loop user a `suspend` record is **never** the controller's action — Loop withholds by
commanding a temp basal at 0 U/hr, and never by suspending. My original handoff asked for
`"automatic": not manual`, which is right for manual temps and leaves suspends labelled as Loop's.

## What the pending fix exports

`manual` is `dtype == "temp" and native`, so a suspend record has `manual = False` and falls through:

| exported record | `manual` | `41aa6129` exports | correct |
|---|---|---|---|
| `deliveryType=automated` (Loop's own temp, and Loop's scheduled segments) | False | `true` | `true` |
| `temp`, native — the user set it | True | `false` | `false` |
| **`suspend`** | **False** | **`true`** | **`false`** |

## Suggested rule, which is simpler than the one I asked for

    "automatic": dtype == "automated"      # only Loop's own uploads are automatic

equivalently `not (manual or dtype == "suspend")`. It needs no new information — `dtype` is already in
scope at that line.

## Scale, measured on the 206 `ice_v32` exports

| class | records | donors |
|---|---|---|
| manual temp (what `41aa6129` flips) | 5,859 | 39 |
| **suspend (still mislabelled)** | **14,369** | **203 of 206** |
| Loop temp + scheduled (correctly `true`) | ~4.21 M | all |

So the suspend half is **2.5x the records and 5x the donors** of the part already fixed, and it is
near-universal rather than confined to the 39 manual-temp users. Still only 0.5% of basal records in
total, and still nothing reads `automatic` on basals today (verified at every call site), so this
remains safe to merge and takes effect only at the next export.

## One item in my original handoff is now largely moot

I asked for Tidepool's `deviceEvent status` **`reason`** to be captured so a manual suspend could be
told from an automatic one. On the "who commanded it" axis Pete's rule answers that without the field:
never Loop. A *deliberate user suspend* versus a *pod fault or pod expiry* is still a different axis
and may be worth the field, but it is no longer needed to attribute the action away from the
controller. Drop it in priority accordingly.

The other item stands: the raw `deliveryType` is shadowed at the `segs` boundary (the 7th element is
`btype`, and the unpacking names it `dtype`), so Loop's commanded temp and a user manual temp both
export as `basalType: "temp"` — measured across the 206 exports, `basalType` takes only
`temp` / `scheduled` / `suspend`, never `automated`.
