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

## Roles

This repo is worked by several agents with different jobs, each in its own worktree. This
file is the part they all share; the role-specific context lives in an overlay that
`CLAUDE.md` imports through **`ROLE.md`** — a git-ignored one-line file naming the overlay
for that checkout (copy `ROLE.example.md`, exactly like `PRIVATE.md`).

| Role | Overlay | Job |
|---|---|---|
| frontier | `docs/agents/frontier.md` | Does a candidate change actually help? Lift, scoring, the ledger. |
| simulator | `docs/agents/simulator.md` | Building LoopEval itself — engine, adapters, CLI, analysis package. |
| eda | `docs/agents/eda.md` | Observational analysis of the data; the live distribution study. |
| — | `docs/agents/verification.md` | Faithful replay and identity checks; read by frontier **and** simulator. |

**Keep to your own overlay.** One file, one owner: roles never edit each other's overlay, so
merging between worktrees stays conflict-free. Anything that turns out to matter to every
role gets promoted into *this* file deliberately, as its own commit.

**Shared work lands on `main`.** Tooling, the engine and the analysis package are common
property; commit them to `main` and the other worktrees pick them up on their next merge.
Findings stay in the role's own files.

---

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

