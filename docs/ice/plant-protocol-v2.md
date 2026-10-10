# External plant protocol v2: plant-generated carb entries and manual boluses

**Status:** proposal from the ice role to the simulator role, 2026-10-09. Nothing implemented.

## Why

The ICE generator drives `simulate --candidate-counterfactual --external-plant`. Today the plant
returns only BG, and the person's carb entries and manual boluses are the *real* ones, replayed at
their real times (boluses re-sized to the simulated Loop's recommendation). In a generated world
that breaks the person:

- a generated high the real person never had gets no correction. Heavy manual correctors run away:
  pilot donor i012 (temp-basal only) really bolused 31 U/day by hand; the simulation delivered
  5.5 U/day and BG climbed without bound in every seed;
- real boluses land where the generated world may not need them, and real carb entries announce
  meals the generator didn't produce (or miss ones it did).

v2 lets the plant return the person's *actions* — carb entries and manual boluses — generated in
response to the simulated state, so behavior and physiology come from one consistent world.

## Protocol (backward compatible)

**Request** — unchanged, plus an optional `state` object describing the candidate at decision `t0`:

```json
{"t0": ISO, "t1": ISO, "doses": [...], "samples": [ISO, ...],
 "state": {"rec_bolus": U, "iob": U, "cob": g, "bg": mg/dL}}
```

`rec_bolus` is `candidateManualBolusRec` before any rec-scale (full correction, AF 1, clamped to
`maxBolus`) — what the bolus calculator would show. A v1 plant ignores `state`.

**Reply** — `bg` as now, plus optional action lists for events in `(t0, t1]`:

```json
{"bg": [...],
 "carbs":   [{"t": ISO, "grams": g, "absorption_s": s}],
 "boluses": [{"t": ISO, "ratio": x} | {"t": ISO, "units": u}]}
```

- `ratio` — the person gives `ratio ×` Loop's recommendation at the moment they act (the
  calculator habit; the generator learns this per person). `units` — an absolute amount (identity
  tests, or a plant that models units directly).

## Semantics

1. **Carbs.** Each returned carb is appended to the candidate arm's carb list (`candidateCarbs`
   becomes a `var`, inserted in `startDate` order) with `startDate = entryDate = dosingVisibleDate
   = t`. First visible to the decision at `t1` (the next step). Carb effects are recomputed every
   cycle (`simStepDose`), so nothing precomputed goes stale. The baseline arm is untouched.

2. **Boluses act at the next decision.** A bolus returned for `(t0, t1]` is delivered at the next
   decision instant `t1`:
   - `ratio`: compute the manual-bolus recommendation at `t1` on the candidate state, with any carbs
     returned in the same reply visible (the existing meal-carb relaxation pattern:
     `buildInput(at: t1, carbVisibilityCutoff: …)` → `simStepDose(...).manualBolusRec`), deliver
     `clamp(ratio × rec, 0, maxBolus)`;
   - `units`: deliver `clamp(units, 0, maxBolus)`.
   The delivered dose is appended to `counterfactualDoses` at `t1` and sent to the plant in the
   next request's `doses` like any other. The simulator stays the single source of truth for what
   was delivered; the plant never assumes its own bolus was given.
   Timing cost: a person's bolus lands at most one decision interval (~5 min) after the plant
   chose it. Acceptable for behavior; noted for identity tests.
   If several boluses come back for one step, they are summed (ratio boluses: sum the ratios).

3. **Real actions off for the candidate only.** New flag `--plant-behavior` (requires
   `--external-plant`): from `cfActiveStart` on, the candidate ignores real carb entries and real
   manual boluses (`realManualBoluses = []` for the candidate; real carbs after `cfActiveStart`
   dropped from `candidateCarbs`). Burn-in history stays real. Not `suppressCarbs` /
   `--no-carb-entries`, which blank both arms.

4. **Skipped steps** (stale CGM, no-dose-guard, nil input): the plant is not advanced, as today.
   Actions are only returned for advanced steps, so nothing is lost — but a decision-time gap means
   the person's action waits for the next advanced step. Log a count.

5. **Field-trace features.** The ICE rise-boost and ISF-boost veto read `realICE` from the field
   trace and will not see plant-generated meals. Warn (or refuse) when combined with
   `--plant-behavior`.

6. **Trace output.** Record generated carbs and boluses (source `plant`, requested ratio/units,
   recommendation, delivered amount) in the trace, so behavior can be scored from the trace alone.

## Acceptance tests

- **v1 compatibility:** with a plant that never returns actions and without `--plant-behavior`,
  traces are content-identical to the current binary (as `6da7849` checked for the plant itself).
- **Replay-behavior identity:** a plant in replay mode that returns the *real* carb entries at their
  `dosingVisibleDate` and the real manual boluses as `units`, run with `--plant-behavior
  --cf-identity`, reproduces the field CGM within the plant's current identity bound (median
  0.4 / max 1.15 mg/dL, i004, 2 days) plus whatever the one-cycle bolus delay costs — measure and
  report that delay cost separately.
- **Ratio path:** a plant that returns `ratio = 1.0` at each real bolus time reproduces today's
  default `--candidate-manual-bolus-from-recommendation` run, up to the one-cycle shift.

## Ice-side work that pairs with this

The generator gains two outputs per 5-min step — P(carb entry) with grams and absorption time,
P(manual bolus) with a ratio to the recommendation — trained on the recorded entries and the
recommendation on screen at each real bolus (`recommended_bolus` extractor). The plant fills
`carbs` / `boluses` from them and reads `state.rec_bolus` only for logging.
