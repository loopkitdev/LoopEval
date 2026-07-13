# AGENTS.md — LoopEval project context

LoopEval evaluates **insulin-dosing algorithms** (Loop's LoopAlgorithm, oref/OpenAPS via
OpenAPSSwift) and candidate changes to them, by replaying real-world CGM + insulin data.
The goal is to estimate the therapy impact of an algorithm or settings change **before it
is ever tried on a person**. It is safety-critical work: insulin dosing errors cause
hypoglycemia, which can be immediately dangerous.

**Optimization target: TIR ↑ (70–180 mg/dL) AND time-below-54 ↓.** A win on one metric
that costs the other is not a win.

**Privacy:** Nightscout data is a real person's medical data. Never commit or publish a
Nightscout URL, hostname, token, or anything identifying. Use placeholders
(`https://YOUR-NS.example.com`) in anything written to the repo. Keep real URLs in a
local, untracked file.

---

## The two main workflows

Almost all work is one of these:

### 1. Frontier experiments — "does this change actually help?"

Run a candidate algorithm/settings change through the closed-loop counterfactual
simulator over weeks–months of real data, score **TIR and t<54**, and compare against a
**reference curve** (the stock algorithm swept over ISF multipliers). A change matters
only if it has **lift** — more TIR at equal severe-lows than aggressiveness tuning alone
reaches. See **[docs/FRONTIERS.md](docs/FRONTIERS.md)**; the scorer is
`python -m loopeval_analysis.frontier`.

**Current frontier picture (qualitative — regenerate numbers per dataset/window):**

- **Leading with lift:** **Asymmetric Integral RC** (`--candidate-integral-rc
  --candidate-irc-drop-scale/-rise-scale` — weight the drop side of retrospective
  correction more than the rise side) and **double-low prevention**
  (`--candidate-sensitive-mode-tau-min/-gain` — an EWMA of recent negative discrepancy
  that raises effective ISF on subsequent cycles, damping re-dosing into the rebound
  after a low).
- **Sliders (no lift, still available):** flat ISF multiplier, application factor, and
  **GBAF** (`--candidate-gbaf`, glucose-based application factor). These move along the
  reference curve, not above it. GBAF in particular has *not* shown lift under the
  current fidelity stack — don't present it as a frontier lever.
- Meal announcement dominates everything: an announcing user's real-world point sits far
  above anything hands-off automation reaches. The residual gap is a forecasting
  problem (anticipating carbs), not a dosing-logic problem.

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
  Full detail: `docs/simulator-guide/index.html`.
- **`--decision-time-replay`** replays decisions on the fixed real history without
  acting — for same-input dose comparison and single-decision anatomy (both arms see
  identical inputs; no feedback).
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

## Metrics

- **Primary:** TIR 70–180, time <54. Secondary: time <70, time >180/>250, AUC<70,
  AUC>180, mean BG, dose deltas, `kept_frac`.
- **IOB-at-crossing-54** (`iob_cross54_*` from `score_counterfactual`): committed insulin
  carried into severe lows — a danger axis t<54 duration can't see (rescue carbs
  truncate lows in real data, the counter-reg floor truncates them in sim).
- **Plot convention:** x = TIR (right = better), y = t<54 (0–1.5, up = worse), dotted
  budget line at 1.0, better = lower-right. Use `loopeval_analysis.plotting.tir_t54_axes`.
- `bench` linearized TIR and `evaluate` forecast metrics are diagnostics — never therapy
  evidence.

## Design principle: modify the forecast, not the output

Loop is a feedback controller. A rule that overrides the *output* (e.g. "cut the basal
Loop wanted") gets compensated on later cycles — Loop's forecast still says BG is heading
high, so it adds the insulin back. Change what the controller *believes* instead: adjust
the forecast (ISF, BG offset, model term) so the computed dose shrinks naturally. First
question for any candidate: *"what part of the model is wrong, and what forecast change
expresses that?"* Corollary for datasets from Loop users: a persistent forecast residual
is evidence the **model** was wrong at that step — the leverage is in inputs and model,
not in second-guessing the dose.

## Traps (each of these has burned a session)

- `predictions[].baselineDose` is a **recommendation**, not delivery. For what was
  actually delivered use the trace's **`delivery[]`** stream (both arms, basal + bolus,
  auto/manual) or real dose history.
- Nightscout `devicestatus` is a **post-dose** snapshot (its dose fields are residuals
  after the just-enacted dose). For dose fidelity compare against dose history
  (treatments), not devicestatus.
- `rate_uhr` NaN in a basal timeline means *scheduled basal running*, *not* suspend.
  `.fillna(0)` fabricates suspends. Use `effective_delivery_rate()`.
- **Rescue-carb confound:** counterfactuals inherit the rescue carbs the person actually
  ate (via ICE), which biases against hypo-prevention candidates (spurious post-hypo
  high) and makes the field's t<54 read lower than an untreated trajectory would.
- Compression lows / the CGM 40-floor inflate absolute t<54 (common-mode: deltas and
  rankings hold, absolutes are overstated). The counter isn't floored at 40, so its lows
  can read deeper than the field trace during a floored event.
- `insulin_hole` / oracle metrics use **future** data — evaluation upper-bounds only,
  never deployable signals.
- Single-window wins frequently disappear on the full date range; re-run wide before
  believing anything.

## Repo map

| Path | What |
|---|---|
| `Sources/EvalCore/Engine/ClosedLoopSimulator.swift` | The core sim: substrate, counterfactual, closed loop, fidelity, disruption clamps, patient IOB |
| `Sources/EvalCore/Engine/DosingEngine.swift` | Pluggable controller: `LoopAdapter` / `OpenAPSAdapter` |
| `analysis/loopeval_analysis/` | Python: scoring, frontier, case_study, iob, disruption CSVs, carb reconstruction |
| `docs/FRONTIERS.md` | Frontier-experiment walkthrough |
| `docs/CASE_STUDIES.md` | Case-study walkthrough |
| `docs/simulator-guide/index.html` | Deep technical guide to the simulator |
| `docs/loop-algo-classes.md` | Deployed-Loop vs LoopAlgorithm-package behavior classes and emulation flags |

## Build & smoke

```bash
swift build -c release          # binary at .build/release/loop-eval
.build/release/loop-eval simulate --help
```

`swift test` requires a toolchain with the Swift `Testing` module; when unavailable,
verify via identity sims and smoke runs instead.
