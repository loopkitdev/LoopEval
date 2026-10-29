# E5 — Insulin moved vs insulin added at meals (pre-registration)

Written 2026-10-28, before any trace was scored. Board: TIDEPOOL-101 (Boost experiment 1). Source:
`docs/handoffs/2026-10-28-frontier-boost-experiments.md` §1.

## Question

Tim Street reports, in Boost data, that insulin moved earlier within a meal is harm-neutral while insulin added to it
carries extra lows. If the same holds in replay, the unannounced-meal "dose more" candidates may have failed because they
added insulin rather than moved it, and a candidate that only moves insulin would deserve a lower bar. Does a candidate's
low cost in replay track the insulin it adds at meals, and not the insulin it moves?

## Data (existing traces, no new sims)

Three same-binary sets, each scored against its own reference arm at needs 1.00:

| Set | Regime | Reference | Contrasts |
|---|---|---|---|
| E4 | no entries, automatic bolus AF 0.4 + gr | `ab` | dial 0.90 / 0.95 / 1.05 / 1.10, `rg30`, `rgmax`, `lg30`, `ciq`, `mdt` |
| E3 | no entries, gr | `nc` | dial 0.95 / 1.05, `nc_hab` |
| c47 | donor's deployed regime, gr | `gr_B100_S100` | basal × ISF grid, 24 arms (B, S ∈ 0.80–1.25) |

189 donors, the last 28 days, frontier's dosing harness.

## Definitions

- **Meal event:** a field-CGM rise of ≥ 50 mg/dL from a local minimum within 2 h (frontier's `rises.py` rule); t0 = the
  minimum. **Logged** if a carb entry ≥ 5 g falls within −30 / +60 min of t0, otherwise **unlogged**. The plant is the
  measured ICE, so the meal happens in every arm at the same time.
- **Delivered insulin:** automatic + manual delivery per step from the trace (basal included). d(τ) = candidate minus
  reference cumulative delivery over (t0, t0 + τ].
- **Early excess** E = max(0, max d(τ) for τ ≤ 120 min). **Net** N = d(240 min).
  **Moved** M = E − clip(N, 0, E): early insulin paid back by 4 h. **Added** A = N, split into A⁺ = max(N, 0) and
  A⁻ = min(N, 0) (withheld).
- **Outcome per event:** candidate minus reference minutes below 70 over (t0, t0 + 6 h]; also minutes below 54 and
  above 180.

## Analysis

Pooled over every event and contrast in all three sets: Δmin<70 = βM·M + βA⁺·A⁺ + βA⁻·A⁻ + donor fixed effects.
95 % CI from a donor bootstrap. The same model on Δmin>180 shows what each unit buys. Per contrast, mean M and A per
event are reported beside its ΔTIR and Δt<70.

## Bar (fixed before scoring)

- **H1, added insulin costs lows:** βA⁺ CI lower bound > 0.
- **H2, moved insulin is harm-neutral:** βM CI upper bound < βA⁺ / 3.
- **Reading:**
  - H1 and H2 hold: the Boost finding replicates in replay. Report M and A beside every new candidate. Boost experiment 2
    (one bounded catch-up per meal) goes ahead.
  - H1 holds, H2 fails: in replay, moving insulin costs lows like adding it. Experiment 2 is not run.
  - H1 fails: the decomposition does not explain low cost in replay. Closed.

## Limits that bound the claim

- Associational within closed loop: moved and added insulin are what the controller did in response to each meal, not
  assigned doses.
- Replay's lows axis is unvalidated (ledger M11), and replay overstates low changes (the ice generator shows 15–50 %).
  A pass says how replay prices the two forms, not how a body would.
