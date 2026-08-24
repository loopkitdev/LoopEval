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
(`https://YOUR-NS.example.com`) and anonymous aliases (`user1`, `user2`, …) in anything
written to the repo. Keep real URLs, tokens, and per-dataset config in the git-ignored
**`PRIVATE.md`** — see *Private site config* below.

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

**Lift — the definition (in `frontier.lift`):** the signed, **axis-normalized closest
distance** from a candidate `(TIR, t<54)` point to the reference-sweep polyline. Both axes
are scaled by the reference sweep's span (TIR ≈ tens of %, t<54 ≈ fraction of a %) so
neither dominates — a raw Euclidean distance would be swamped by TIR. Sign is **+** when
the point is **below-and-right** of the sweep (better: more TIR / less t<54) and **−** when
above-left (worse). **Greatest positive lift = best.** (This replaced an older "TIR gap at
matched t<54", which blew up wherever the reference curve runs flat.)

**Two things lift is fragile about — both have produced confidently wrong rankings:**

- **Compare on ONE dial.** Sweeping the candidate over ISF while the reference sweeps
  insulin-needs measures the *dial* as much as the mechanism — the two trace different
  paths through (TIR, t<54). Sweep the candidate over **insulin-needs too**, or include a
  plain (mechanism-off) control swept on the candidate's dial to subtract the dial's share.
- **Lift is span-normalized, so it is NOT comparable across reference extents.** Extending
  a reference (e.g. needs ×1.3 → ×2.0) grows the t<54 span and silently shrinks *every*
  lift value — 6.6× on one dataset. Only rank within one reference; never compare lift
  magnitudes across runs whose reference differs.

**Never read a lift number without looking at the plot.** Lift is a scalar summary of a
geometric fact; if the sign disagrees with where the point sits relative to the gray line,
believe the plot. That check is what caught both hooked-curve bugs (fixed 2026-07-17).

**Sweep the candidate, rank by mean.** A candidate parameterization is a *mechanism*; sweep
it over its own ISF multipliers and rank mechanisms by the **mean (or median) lift across
the sweep** (`frontier.summarize_mechanisms`) — not by any single point. Best-of-sweep max
is optimistically biased (it grabs the highest jitter point); report the peak multiplier
only as a secondary "where it peaks". The multiplier that pairs best with a mechanism is
**dataset-dependent**: a non-announcer may want *lower* ISF (dose more aggressively, let the
mechanism catch the added lows), a heavy announcer *higher* ISF (gentler automation, since
meal boluses already carry TIR). **Canonical scoring definition now lives in [docs/FRONTIERS.md → Scoring](docs/FRONTIERS.md)**:
a candidate improves iff, with the needs dial free to move, it reaches an operating point
better on BOTH axes (TIR up AND t<54 down; t<70 when t<54≈0) than the reference curve —
strict dominance, judged in the operating band, re-tuning allowed. That section supersedes
any other scoring guidance here or elsewhere.

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

## Private site config (`PRIVATE.md`)

Real Nightscout URLs, tokens, and each dataset's replay config live in **`PRIVATE.md` at
the repo root — git-ignored, never committed**. `CLAUDE.md` imports it, so you have this
context automatically. On a fresh checkout it won't exist yet: copy the template with
`cp PRIVATE.example.md PRIVATE.md`.

**When the user tells you about a Nightscout site — or a config fact about one — record it
in `PRIVATE.md`** (one row per dataset), capturing what deployment-faithful replay needs
(see *Deployment-faithful config per dataset* above):

- alias (`user1`, `user2`, `orefuser`, …), base URL, and token if the site requires one;
- pump + insulin model (`--insulin-type …`; verify IOB against devicestatus);
- RC mode and era (`--integral-rc` while IRC was on — note the switch date);
- deployed-Loop emulation flags for Loop users; oref / dynISF prefs for Trio users;
- override handling (`--apply-overrides`), edited-carb handling (`--carb-revisions-json`),
  app factor / GBAF, meal-announcement level;
- any dated settings changes (target, ISF, CR).

Then **validate** before trusting numbers from a new site: a stock ISF sweep's TIR-vs-t<54
curve should pass through the site's real deployment point; if it doesn't, the recorded
config is wrong — fix it first (see `docs/FRONTIERS.md`).

**Privacy is absolute:** never put a real URL, host, token, or identifying detail into the
repo, a report, a PR, an issue, or a plot — use the alias and a placeholder URL there. Data
is cached under `~/.loop-eval/cache/` after the first fetch; creds for a private site may
instead live fully outside the repo in `~/.loop-eval/<alias>/site.json`.

## Metrics

- **Primary:** TIR 70–180, time <54. Secondary: time <70, time >180/>250, AUC<70,
  AUC>180, mean BG, dose deltas, `kept_frac`.
- **IOB-at-crossing-54** (`iob_cross54_*` from `score_counterfactual`): committed insulin
  carried into severe lows — a danger axis t<54 duration can't see (rescue carbs
  truncate lows in real data, the counter-reg floor truncates them in sim).
- **Plot convention:** x = TIR (right = better), y = t<54 (0–1.5, **up = worse** — never
  `invert_yaxis()`), dotted budget line at 1.0, better = lower-right. Use
  `loopeval_analysis.plotting.tir_t54_axes`.
- **Dose panels must say whether bars are RECOMMENDATIONS or DELIVERED doses** — never an
  unlabeled "dose". They are different streams that legitimately diverge (Loop records its
  recommendation straight through "Pod not connected" cycles while delivering nothing; DTR
  never delivers at all). Convention: bars = recommendations (field `dosingDecision` vs
  replay output), black ▼ markers = delivered (dose history). Comparing across streams
  produced fake mismatches twice (bddp11 22:00 pump-error window; bddp03 meal takeovers).
- **Sweep plots — order lines by ISF multiplier, never by TIR.** A candidate/reference
  sweep is a curve *parameterized by ISF multiplier*; connect its points in multiplier
  order (adjacent vertices = adjacent ISF). Sorting by TIR makes the line zig-zag on any
  non-monotonic sweep (e.g. an announcer's hooked curve). **Don't hand-roll sweep plots —
  call `loopeval_analysis.frontier.plot_sweeps`**, which orders by multiplier and applies
  `tir_t54_axes` for you. (`frontier.lift` likewise interpolates the reference in
  multiplier order.)
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
| `docs/simulator-guide/README.md` | Deep technical guide to the simulator (GitHub-rendered) |
| `docs/loop-algo-classes.md` | Deployed-Loop vs LoopAlgorithm-package behavior classes and emulation flags |
| `PRIVATE.example.md` | Template for `PRIVATE.md` — your private per-site config (copy it; `PRIVATE.md` is git-ignored) |

## Build & smoke

```bash
swift build -c release          # binary at .build/release/loop-eval
.build/release/loop-eval simulate --help
```

`swift test` requires a toolchain with the Swift `Testing` module; when unavailable,
verify via identity sims and smoke runs instead.
