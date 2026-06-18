# Loop algorithm classes (and how to configure our binary for each)

There are **three classes** of Loop dosing algorithm we care about. Both test users run **class 1 (Loop-main)** on their phones, so faithful *reproduction* targets class 1. Our `loopkitdev/LoopAlgorithm` fork's *default* is **class 2**. Class 3 is what we experiment with.

> **Active goal (2026-06-18):** use our LoopAlgorithm binary to **reproduce class 1 (Loop-main) exactly**. We are NOT done — the class 1→2 delta below is a *living, incomplete ledger*; we are still discovering differences by chasing the residual between our class-1-emulation and field. Exact reproduction is not yet achieved.

| # | Class | ISF timing | Gradual-transitions gate | IRC | GBAF |
|---|---|---|---|---|---|
| **1** | **Loop-main** (deployed DIY Loop app; rloop + user2 run this) | **dose-time** | **none** | optional, **fixed params** | optional, **fixed params** |
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

Everything else (IRC presence, GBAF, pump quantization, per-point correction sampling) is shared or version/config-dependent, **not** part of the 1→2 algorithm delta. IRC *asymmetry* and the extra forecast terms are the 2→3 delta.

## Who runs what

| User | NS | Pump / insulin | Class | RC / extras |
|---|---|---|---|---|
| **rloop** | your-ns.example.com | Omnipod DASH / rapid-acting **adult (peak 75)** | **1 (Loop-main)** | **IRC ON ~2025-05→2026-04-24 eve CT, then standard RC** (one on→off; on predates our data — ≥11 mo). Inferred from data (not uploaded) — `runs/2026-06-18-irc-detect/`. App factor 0.40. Minimal meal announcement. |
| **user2 ("l")** | user2-ns.example.com (guest, may rotate) | Omnipod / **Fiasp/Lyumjev (peak 55)** | **1 (Loop-main)** | **IRC ON throughout.** Temporary Overrides, CR 7.5, heavy manual meal-announcer. |

The dosing-strategy / IRC flag is **not** uploaded to Nightscout → RC mode must be inferred (replay each mode, see which forecast curve matches field's uploaded `predicted.values`).

## Configuring our binary per class

Our binary defaults to **class 2** (LoopAlgorithm standard). To reproduce **class 1 (Loop-main)** — the deployment target:

| Difference (class 2 default → class 1) | Flag to match Loop-main |
|---|---|
| ISF timing: mid-absorption → **dose-time** | `--no-mid-absorption-isf` |
| Gradual-transitions gate: on → **off** (Loop-main has no gate; suppresses momentum + RC on >40 mg/dL steps) | `--no-gradual-transitions-gate` (a.k.a. `--loop393-momentum`) |
| RC mode: per user/period | `--integral-rc` for IRC periods (rloop pre-2026-04-24, user2 always); omit after |
| IRC params: fork constant 2.0/60/180 vs Loop-main fixed (DIY Loop-main historically **5.0/90/240**; LoopKit-dev 2.0/60/180) | version-dependent — verify per period |
| Momentum velocity cap (4.0 mg/dL/min) — present in our build; deployed Loop-main effectively uncapped | no flag yet (see Open items) |
| GBAF | `--gbaf` (Loop's fixed defaults 110/200, 0.20/0.80) only if that user ran it |
| Extra forecast terms (UAM/early-rise/ICE-boost/sensitive-mode) — class 3 only | leave off (default) |

Matches all classes by design: pump-floor quantization (PumpModel `.omnipod`), per-prediction-point correction-range sampling, decision-time input gating.

## Why this matters

Aggregate outcome matches (e.g. an ISF-sweep curve through the field point) can be hit with the **wrong** class via *compensating errors* (m/ISF absorbing a missing IRC integral or a too-aggressive gate). Decision-time **forecast** replay against field's uploaded `predicted.values` is the sharp fidelity test. Example: rloop 2025 field-curve validation ran IRC-OFF over an IRC-ON period yet "matched" the aggregate — compensating-error, not fidelity.

## Forecast collapse on fast unannounced rises (ROOT-CAUSED + FIXED 2026-06-18)

Our class-2 forecast dove to 0/negative at high IOB on fast unannounced rises (rloop 09-17 22:04–22:24) while class-1 field stayed elevated and dosed. Cause: the **gradual-transitions gate** suppresses **both momentum (15-min window) and RC (30-min grouping window)** whenever any consecutive CGM step exceeds 40 mg/dL — and a fast meal rise (09-17 21:54→21:59 = +42) always trips it. Class 1 (Loop-main) has no gate, so it doesn't collapse.

This is **correct class-2 behavior** (the gate is now standard LoopAlgorithm — keep it on by default). The bug was only that the *disable* flag didn't fully work: `--no-gradual-transitions-gate` set the threshold to `nil`, which disabled the momentum gate but **not** the RC gate (the RC gate used `gradualTransitionsThreshold ?? 40.0`, re-defaulting `nil`→40). Fixed both RC-gate sites in `LoopAlgorithm.swift` to gate only when the threshold is non-nil. With the gate fully off (class-1 emulation), rloop 09-17 mean |forecast − field| over the collapse window dropped **116 → 24 mg/dL** and boluses matched field. Default callers pass 40 (gate on) and are unaffected. See `runs/2026-06-18-dtr-0917/forecast_collapse_fixed.png`.

## Open items

- ~24 mg/dL residual after class-1 emulation (slight overshoot at rise onset) — likely IRC gain (2.0/60/180 vs 5.0/90/240); confirm which Loop version each period shipped.
- No CLI flag yet to disable the **momentum velocity cap** (4.0) — add one so class-1 emulation is a complete one-liner.
