# Loop algorithm classes (and how to configure our binary for each)

There are **three classes** of Loop dosing algorithm we care about. Both test users run **class 1 (Loop-main)** on their phones, so faithful *reproduction* targets class 1. Our `loopkitdev/LoopAlgorithm` fork's *default* is **class 2**. Class 3 is what we experiment with.

> **Active goal (2026-06-18):** use our LoopAlgorithm binary to **reproduce class 1 (Loop-main) exactly**. We are NOT done — the class 1→2 delta below is a *living, incomplete ledger*; we are still discovering differences by chasing the residual between our class-1-emulation and field. Exact reproduction is not yet achieved.

| # | Class | ISF timing | Gradual-transitions gate | IRC | GBAF |
|---|---|---|---|---|---|
| **1** | **Loop-main** (deployed DIY Loop app; user1 + user2 run this) | **dose-time** | **none** | optional, **fixed params** | optional, **fixed params** |
| **2** | **LoopAlgorithm** (new standard; not widely deployed) | **mid-absorption** | **on (40 mg/dL)** | symmetric standard | available |
| **3** | **LoopAlgorithm + candidates** (next-version experiments) | mid-absorption | on | **asymmetric** (drop/rise gain, low-memory carry, drop/rise duration) + UAM/early-rise/ICE-boost/sensitive-mode | tunable + variants |

Class 2 = class 1 with (a) ISF re-evaluated mid-absorption and (b) the gradual-transitions gate added. Class 3 = class 2 plus the experimental forecast/dosing terms we're evaluating for the next LoopAlgorithm version.

## The class 1 → 2 delta (TRACK THIS)

This is the running list of what changed from deployed Loop-main to the new LoopAlgorithm standard — the set our reproduction must *undo* to match the field, and whose therapy impact defines "what the new standard did." **INCOMPLETE / work-in-progress:** we are still identifying deltas by trying to reproduce class 1 exactly; add rows as found. Confirmation that the list is complete = our class-1 emulation matches field forecasts/doses to within noise (not yet true — see residual in Open items).

| # | Change (1 → 2) | What it does | Emulate class 1 with | Observed effect (so far) |
|---|---|---|---|---|
| D1 | **dose-time → mid-absorption ISF** | active IOB re-valued at current ISF instead of each dose's delivery-time ISF | `--no-mid-absorption-isf` | only differs when ISF changes mid-absorption (Temporary Override, ISF-schedule change); negligible when ISF is steady |
| D2 | **gradual-transitions gate added** (40 mg/dL) | suppresses **momentum (15-min win) AND RC (30-min win)** when any consecutive CGM step >40 mg/dL | `--no-gradual-transitions-gate` | **large**: on fast unannounced rises class-2 forecast collapses → under-doses; class 1 stays high + doses. Root cause of the 09-17 collapse (mean fcst err 116→24 when emulating class 1). |
| D3 | **momentum velocity cap** (~4.0 mg/dL/min) | caps upward momentum slope | *(no flag yet)* | limits early-rise projection on steep meals; magnitude TBD |

| **OFF-CYCLE decision replay** (FIXED — replay/methodology bug, minor) | forecast-match replays at EVERY field devicestatus timestamp, but ~0.3% are **user-triggered cycles between CGM readings** (manual bolus / carb log) on a 2-5 min STALE BG, where real Loop does NOT auto-dose (field devicestatus there: `enacted bolus=None`). Our sim auto-dosed there → spurious boluses on stale BG. user1 week: 6/1834 off-cycle, 5 spurious boluses (3.0 U) incl. 09-18 21:21 (1.35 U) and 09-16 21:48 (1.25 U). | **`--max-cgm-age-min 1.5`** (new forecast-match flag) drops decision times with stale CGM. **Effect is small**: bolus 181.8→178.6 U, exact 93.9→94.2%. | NOT the main residual — see below |
| **09-20 = a PUMP-SUSPEND DISRUPTION** (root-caused, not a delta) | a temp basal rate=0 / **duration 356 min (6 h, 05:47→11:44)** = a pump suspend (pod change). The DEFAULT forecast projects that in-progress 6h suspend forward → "no insulin for 6 h" → `insulinEffect360` flips POSITIVE (+98 at IOB +0.95) → eventualBG soars 111→401. BG then really climbs from 6 h of no basal and **pegs at 400**; pod change ~11:44 → recovery. So the "morning anomaly" AND the "sensor peg" are ONE disruption event. | `--clip-in-progress-temp-basal` makes it sane (evBG 401→117) and matches field (field clips the long suspend; its evBG stayed ~134). Exclude via the disruption/outage mask. **Fidelity note: for long in-progress suspends, CLIPPING is field-faithful — the flag's "default off = field-faithful" help is wrong for long suspends.** | most of the +14.6 U/week "residual" is this one disruption day |

| **CGM-aligned residual over-bolus** (characterized — not a class delta) | sim auto-boluses **+14.6 U/week over field** across 23 CGM-aligned steps (ALL over-bolus, 21/23 COB≈0). Breakdown: **~half is 09-20 sensor artifact** — BG pegged at the 400 ceiling for ~2 h (11:29-13:29, sim forecasts 554→boluses 2.35×2 where true BG is unknown) plus a morning forecast anomaly (BG 140→evBG 400, +2 U); **~half is small scattered over-boluses (0.15-0.7 U) on rising/high BG** where sim's forecast is marginally more aggressive than field's actions. | sensor-ceiling artifacts → covered by a disruption/CGM-quality mask; the scattered part is sub-cycle forecast over-aggressiveness on rises (same family as the suspend-side residual). | **NOT a structural class delta** — sensor artifacts + small forecast-fidelity noise |

Everything else (IRC presence, GBAF, pump quantization, per-point correction sampling) is shared or version/config-dependent, **not** part of the 1→2 algorithm delta. IRC *asymmetry* and the extra forecast terms are the 2→3 delta.

**Validation status (user1, IRC-on period):** with class-1 flags (`--no-mid-absorption-isf --no-gradual-transitions-gate --integral-rc`), 09-17 (carb-free) dosing matches field **exactly** (auto-bolus 26.1 = 26.1, mean |Δ| 0.003 U). Over a week, auto-bolus mean |Δ| 0.012 U with **only 3.1% of steps off — and the misses are the D4 carb steps** (sim over-doses where it carries a larger carb-forecast than field). So D1+D2+IRC reproduce class-1 dosing except for the carb-model delta (D4). Carb *visibility* is correctly gated on `userEnteredAt` (not meal-time `created_at`); residual visibility error is ≤1 cycle.

## Who runs what

| User | NS | Pump / insulin | Class | RC / extras |
|---|---|---|---|---|
| **user1** | your-ns.example.com | Omnipod DASH / rapid-acting **adult (peak 75)** | **1 (Loop-main)** | **IRC ON ~2025-05→2026-04-24 eve CT, then standard RC** (one on→off; on predates our data — ≥11 mo). Inferred from data (not uploaded) — `runs/2026-06-18-irc-detect/`. App factor 0.40. Minimal meal announcement. |
| **user2 ("l")** | user2-ns.example.com (guest, may rotate) | Omnipod / **Fiasp/Lyumjev (peak 55)** | **1 (Loop-main)** | **IRC ON throughout.** Temporary Overrides, CR 7.5, heavy manual meal-announcer. |

The dosing-strategy / IRC flag is **not** uploaded to Nightscout → RC mode must be inferred (replay each mode, see which forecast curve matches field's uploaded `predicted.values`).

## Configuring our binary per class

Our binary defaults to **class 2** (LoopAlgorithm standard). To reproduce **class 1 (Loop-main)** — the deployment target:

| Difference (class 2 default → class 1) | Flag to match Loop-main |
|---|---|
| ISF timing: mid-absorption → **dose-time** | `--no-mid-absorption-isf` |
| Gradual-transitions gate: on → **off** (Loop-main has no gate; suppresses momentum + RC on >40 mg/dL steps) | `--no-gradual-transitions-gate` (a.k.a. `--loop393-momentum`) |
| RC mode: per user/period | `--integral-rc` for IRC periods (user1 pre-2026-04-24, user2 always); omit after |
| IRC params: fork constant 2.0/60/180 vs Loop-main fixed (DIY Loop-main historically **5.0/90/240**; LoopKit-dev 2.0/60/180) | version-dependent — verify per period |
| Momentum velocity cap (4.0 mg/dL/min) — present in our build; deployed Loop-main effectively uncapped | no flag yet (see Open items) |
| GBAF | `--gbaf` (Loop's fixed defaults 110/200, 0.20/0.80) only if that user ran it |
| Extra forecast terms (UAM/early-rise/ICE-boost/sensitive-mode) — class 3 only | leave off (default) |

Matches all classes by design: pump-floor quantization (PumpModel `.omnipod`), per-prediction-point correction-range sampling, decision-time input gating.

## The veracity test (use this)

NS `predicted.values` is **post-dose** (`predictedGlucoseIncludingPendingInsulin`) and `devicestatus.enacted` is a review snapshot — **don't** compare forecasts to them. On identical BG + dose history, the real test is: **does the sim's newly-computed dose equal the field's actual delivered dose from the DOSE HISTORY (treatments) at that timestamp** — and that means **bolus + temp basal** (field doses rising highs via temp as often as bolus). Use `effective_delivery_rate()` for the field rate (temps are recorded on-change and persist between — the §7 trap; nearest-event matching is wrong).

Aggregate outcome matches (e.g. an ISF-sweep curve through the field point) can be hit with the **wrong** class via *compensating errors*. The decision-time dose-vs-dose-history test is the sharp one.

**Result (user1 week 09-14..09-20, class-1 emulation, 1834 steps):** auto-bolus **93.9% exact** (mean |Δ| 0.012 U), temp rate **94.3% within 0.05 U/hr**, total/cycle delivery sim 266.5 vs field 248.1 U (+7%). The ~6% residual is **forecast-min-driven suspend/neutral disagreements** (sim runs scheduled where field suspended, and vice versa) at dynamic BG moments + the D4 carb steps — bidirectional, small, not a systematic class delta. IOB matches field (|Δ| 0.13 U).

## Forecast collapse on fast unannounced rises (ROOT-CAUSED + FIXED 2026-06-18)

Our class-2 forecast dove to 0/negative at high IOB on fast unannounced rises (user1 09-17 22:04–22:24) while class-1 field stayed elevated and dosed. Cause: the **gradual-transitions gate** suppresses **both momentum (15-min window) and RC (30-min grouping window)** whenever any consecutive CGM step exceeds 40 mg/dL — and a fast meal rise (09-17 21:54→21:59 = +42) always trips it. Class 1 (Loop-main) has no gate, so it doesn't collapse.

This is **correct class-2 behavior** (the gate is now standard LoopAlgorithm — keep it on by default). The bug was only that the *disable* flag didn't fully work: `--no-gradual-transitions-gate` set the threshold to `nil`, which disabled the momentum gate but **not** the RC gate (the RC gate used `gradualTransitionsThreshold ?? 40.0`, re-defaulting `nil`→40). Fixed both RC-gate sites in `LoopAlgorithm.swift` to gate only when the threshold is non-nil. With the gate fully off (class-1 emulation), user1 09-17 mean |forecast − field| over the collapse window dropped **116 → 24 mg/dL** and boluses matched field. Default callers pass 40 (gate on) and are unaffected. See `runs/2026-06-18-dtr-0917/forecast_collapse_fixed.png`.

## Cross-user validation: user2 (2026-06-18)

Same veracity test on user2 (Fiasp peak-55, IRC-always-on, overrides; in-cache week 2026-03-09..15, class-1 flags). **D1+D2+IRC transfer:** temp basal sim 104 / field 101 U (76% within 0.05, 43% suspend both), and at **application factor ≈ 0.15** (vs user1's 0.4) bolus sim 100 / field 106 and **total sim 204 / field 207 U**. So no new user2-specific *algorithm* delta — only a per-user config (AF, insulin model, IRC). The auto-bolus is a fraction of the dose and temp is set independently, so AF scales only the bolus (temp is AF-invariant).

**Tooling lesson (cost me a wrong "user2 over-doses 2.7×" reading):** the Python `effective_delivery_rate` field baseline uses a per-host **doses cache with a fixed epoch range**; if the test window is outside it (my first user2 try was June 2026, cache ended 2026-04-29) it silently returns the scheduled-basal fallback (constant 1.5) → bogus field temp. Always pick a window inside the cache range (or refresh it), and sanity-check that the field rate *varies* before comparing.

## Final residual after excluding pod outages (2026-06-18)

The loop cannot run when the pod is done and no new pod is applied — those intervals must be excluded (data-level outage mask, as in the outcome-scoring disruption policy). Applying the user1 week outage CSV (`loopeval_analysis.outage from-nightscout`, which caught both pod changes incl. 09-20 05:39→11:44 = 356-min suspend + dose gap):

| | auto-bolus sim/field | exact | total Δ |
|---|---|---|---|
| all steps | 178.6 / 165.1 (+13.5 U) | 94.2% | +15.4 U |
| **outage-excluded** | 171.3 / 165.1 (**+6.2 U**) | **94.5%** | **+7.7 U** |

So ~half the residual was the two pod outages. The remaining **+6.2 U/week (~3% of TDD)** is 2 carb steps (post-pod meal + a co-log) and the 09-14 scattered small over-boluses on rises (COB 0, forecast marginally aggressive) — sub-cycle forecast-fidelity floor, **no structural class delta**. The veracity test should apply the outage mask (and `--max-cgm-age-min`) before scoring.

## Open items

- ~24 mg/dL residual after class-1 emulation (slight overshoot at rise onset) — likely IRC gain (2.0/60/180 vs 5.0/90/240); confirm which Loop version each period shipped.
- No CLI flag yet to disable the **momentum velocity cap** (4.0) — add one so class-1 emulation is a complete one-liner.

### Week-long residual is mostly comparison artifacts, NOT new deltas (2026-06-18)

Validating class-1 emulation over a week (1834 steps), sim auto-bolus was +16 U vs field, in 25 steps. Decomposed:
- **3/25 = D4 carb-model** (real, small): sim over-forecasts the carb rise at equal COB.
- **~rest = measurement/comparison artifacts, not algorithm deltas:**
  - **IOB matches field exactly** (mean |Δ| 0.13 U) → no IOB/basal delta.
  - **pre-dose vs post-dose forecast variant**: field uploads `predictedGlucoseIncludingPendingInsulin` (post-dose); our `forecast-match` curve is pre-dose. At heavy-dosing moments the eventualBG gap is the pending insulin, not a model diff.
  - **bolus-vs-temp dosing channel**: field often doses a rising high via temp basal (en_bolus 0) where sim recommends a bolus → spurious auto-bolus "mismatch" (temp-rate mean |Δ| ~0.5 U/hr).
  - **sensor artifacts**: CGM pegged at 400, and occasional bad/duplicate devicestatus records.

**Cleaner comparison needed:** compare **total delivery (bolus + temp basal)** per step, and compare forecasts like-for-like (our pre-dose curve vs a reconstructed field pre-dose, or both post-dose). The auto-bolus-only + eventualBG comparison overstates the residual. Do this before declaring any further 1→2 delta.

### Residual root-caused (2026-06-18): small forecast-min noise, not a class delta

Drilling into the ~6% dose-decision residual (the dominant part is temp-rate disagreements): **59/76 are Type A — sim runs scheduled basal where field SUSPENDED** at falling low-normal BG (now ~100-114, trend −8, negative IOB), sim forecast-min ~85-96, field's min was <78 (suspendThreshold). BG **never actually went low** (future-min 91-141, 0% <70). So field's forecast dips ~10-15 mg/dL lower than ours near the threshold and flips the suspend decision; clinically inconsequential. Ruled out as causes: **suspendThreshold** (78, from cache = field's, correct); **`includingPositiveVelocityAndRC`** (forcing `false` is catastrophic — bolus 182→17 U, so field uses `true` like us); **IOB** (matches |Δ| 0.13); gate/ISF-timing (already applied). The residual is small forecast-*minimum* noise (likely momentum/RC magnitude at gentle falls) that **can't be attributed to a single class delta from NS data** (field's pre-dose forecast isn't uploaded). Net: confirmed 1→2 algo deltas = **D1 + D2** (+ small **D4** carb); the rest is sub-cycle forecast fidelity, not a class difference.
