<!-- Role overlay. Loaded via ROLE.md; see AGENTS.md → Roles. -->

# Faithful replay and verification

Shared by the **frontier** and **simulator** roles. Nothing downstream of a failed
identity check or an unverified replay means anything.

### 2. Case studies — "is the simulator (and the candidate) behaving correctly?"

Plot a specific scenario — BG, insulin delivery (basal staircase + boluses,
auto vs manual), patient IOB, and algorithm state (COB, RC, momentum, forecast) — for a
window around an event, and verify the simulator and candidate are doing what they
should. See **[docs/CASE_STUDIES.md](docs/CASE_STUDIES.md)**; the renderer is
`loopeval_analysis.case_study.plot_case`.

---

## Methodology essentials

- **`simulate --candidate-counterfactual` is the primary tool** for outcome questions.
  Counterfactual physiology: `counter_BG[t+5m] = counter_BG[t] + insulin_effect(candidate
  doses) + observed_ICE(real)` — the person's non-insulin physiology (carbs, exercise,
  sensor noise) is carried into the counterfactual via ICE computed from the real trace.
  Add `--candidate-infer-sensitivity` (the fidelity model) for whole-algorithm sweeps.
  Full detail: `docs/simulator-guide/README.md`.
- **`--decision-time-replay`** replays decisions on the fixed real history without
  acting — for same-input dose comparison and single-decision anatomy (both arms see
  identical inputs; no feedback).
- **Replay-verification process (verify accurate replay in THIS order):**
  1. **Forecasts first.** Every DTR forecast must match the field's recorded `bgForecast`
     within a **few mg/dL**, ranked **worst-case (max point delta), not average**. Compare
     only IOB-aligned, same-dose-state cycles (a field record whose IOB is post-a-just-decided
     dose is not comparable to a pre-dose sim forecast). t0 agreement is meaningless (shared
     current CGM value).
  2. **The ONLY accepted uncorrectable exclusions** — a mismatch gets a pass *only when
     concretely proven* (never assumed) to be one of: **(a) cancelled/incomplete bolus**
     (field thought a bolus was in progress/complete but it failed/was cancelled →
     `requestedBolus` ≫ delivered `normal`, syncId amount ≠ delivered, transient IOB
     spike-and-revert); **(b) backfilled BG** (a reading Loop got late — undetectable
     directly, but shows as a missed loop cycle); **(c) CGM sub-second wobble** (timestamps
     stored at second precision → tiny only). Anything else is a **real discrepancy to fix**
     (decoding / settings / model), not an exclusion.
  3. **Then dosing.** Only after forecasts match, compare the dose computed from those
     forecasts: target **<= 0.05 U (bolus) or U/hr (temp basal)**, worst-case.
- **Identity checks are mandatory** after any simulator or dose-path change: identical
  baseline/candidate configs ⇒ Δdose ≈ 0 every step and counter == sanity. A failed
  identity test invalidates everything downstream.
- **Deployment-faithful config per dataset**: match the deployed insulin model, RC mode
  (`--integral-rc` for IRC eras), Loop-main emulation flags
  (`--no-mid-absorption-isf --no-gradual-transitions-gate`), overrides
  (`--apply-overrides`), and edited-carb reconstruction (`--carb-revisions-json`) —
  otherwise replay differences get misattributed to the candidate.
- **Disruption handling**: clamp delivery during pump outages (`--outages-csv`), skip
  cycles on stale CGM (`--cgm-stale-guard-min 5`), and score with the disruption
  *interval* excluded (`loopeval_analysis.scoring.score_counterfactual`, `post_hours=0`).
- **Hands-on is the default** (real boluses and carb entries pass through; manual
  boluses are IOB-resized by default so the candidate doesn't double-cover).
- Insulin actuation is **one-sided**: a controller can add or withhold insulin but never
  remove it. Lows prevention is therefore limited by how early delivery stops, and at
  the moment of most lows delivery is already at zero — keep this in mind when sizing
  the plausible benefit of any "dose less" mechanism.
