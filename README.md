# LoopEval

A Swift CLI that **evaluates and simulates insulin-dosing algorithms against real-world diabetes data** — to estimate the therapy impact of an algorithm or settings change *before* it is ever tried on a person. It is not tied to a single algorithm or a single data ecosystem.

## Algorithms & data sources

**Algorithms.** Per-step dosing decisions go through a pluggable engine, so the same evaluation and simulation harness runs against more than one controller:

- **Loop** — `LoopAlgorithm` (the [loopkitdev fork](https://github.com/loopkitdev/LoopAlgorithm))
- **oref / OpenAPS** — via the [OpenAPSSwift](https://github.com/loopkitdev/OpenAPSSwift) port of oref0 (the algorithm Trio runs)

**Data sources.** Input is read through a pluggable `EvalDataSource`:

- **Nightscout** (`NightscoutEvalDataSource`) — live fetch, regardless of the uploading app: instances populated by **Loop**, **Trio**, and other DIY closed-loop systems, with per-system quirks (carb-entry timestamps, dose/temp-basal conventions, glucose smoothing) handled in the loaders.
- **Tidepool** — the Python ETL (`loopeval_analysis.tidepool.export_donor`) extracts a donor's Tidepool `device_data` (Databricks) into the four EvalCore JSON files; `simulate --data-dir <dir>` then runs on them via `JSONFileDataSource`. Tidepool quirks (Mongo-wrapped numbers, mmol/L → mg/dL, bolus subType, basal deliveryType, food records) are handled in the ETL.
- **JSON files** (`JSONFileDataSource`) — any pre-exported `glucose/doses/carbs/therapy.json` directory, for offline replay.

## What it does

- Pulls CGM readings, insulin doses, carb entries, and therapy settings from Nightscout (Loop- or Trio-populated) or Tidepool (via the ETL)
- **Evaluate** — runs the algorithm's forecast at every 5-minute step across a date range and compares predictions at configurable horizons (30 min → 6 hours) against actual CGM; computes RMSE, MAE, bias, percentiles, LBGI/HBGI/BGRI risk metrics
- **Simulate** — closed-loop counterfactual replay: re-runs the chosen algorithm cycle-by-cycle on a person's history to estimate therapy outcomes (TIR, time-below-54, etc.) under a candidate change
- Parameter sweeps to find optimal therapy settings or algorithm tuning parameters
- Optional 2D Kalman / AAPS glucose smoothing (for comparison or to match a system's input pipeline)

## Requirements

- macOS 13+
- Swift 5.9+
- Xcode 15+ (or Swift toolchain)

## Build

```bash
git clone --recursive https://github.com/loopkitdev/LoopEval.git
cd LoopEval
swift build -c release
```

The binary lands at `.build/release/loop-eval`. The algorithm packages
([LoopAlgorithm](https://github.com/loopkitdev/LoopAlgorithm) and
[OpenAPSSwift](https://github.com/loopkitdev/OpenAPSSwift)) are git submodules —
if you cloned without `--recursive`, run `git submodule update --init`.

## The two main workflows

Most work with LoopEval is one of these — each has a full walkthrough:

**1. Frontier experiments — [docs/FRONTIERS.md](docs/FRONTIERS.md).** Run a candidate
algorithm/settings change through the closed-loop counterfactual simulator over real
data, score TIR and time-below-54, and compare against a stock-algorithm ISF sweep (the
*reference curve*). A change matters only if it has **lift** — better outcomes than
aggressiveness tuning alone reaches.

```bash
loop-eval simulate --nightscout-url $NS --start 2026-05-01 --end 2026-07-01 \
    --candidate-counterfactual --candidate-infer-sensitivity \
    --candidate-integral-rc --candidate-irc-drop-scale 1.5 --candidate-irc-rise-scale 0.5 \
    --candidate-label asym-irc --trace-out airc.json
python3 -m loopeval_analysis.frontier --ref 'm*.json' --cand airc.json:asym-IRC \
    --outages-csv outages.csv --field-from m1.00.json --out frontier.png
```

**2. Case studies — [docs/CASE_STUDIES.md](docs/CASE_STUDIES.md).** Zoom into a specific
scenario and plot BG, insulin delivery (basal staircase + boluses, auto vs manual),
patient IOB, and algorithm state (COB / RC / momentum / forecast) to verify the
simulator and candidate are behaving correctly — via
`loopeval_analysis.case_study.plot_case`.

Deep background on the simulator itself (substrate, counterfactual physiology, fidelity
model, disruption handling): [docs/simulator-guide/index.html](docs/simulator-guide/index.html).
LLM agents picking up the project should start with [AGENTS.md](AGENTS.md).

## Adding a Nightscout site

There is no registration step — a site is just a URL passed to the CLI (data is cached
in `~/.loop-eval/cache/` after the first fetch). Record the site's URL, token, and the
config below in **`PRIVATE.md`** (`cp PRIVATE.example.md PRIVATE.md` — it's git-ignored);
if you use an agent, `CLAUDE.md` imports it so the agent tracks your sites for you.

```bash
NS=https://my-site.example.com          # keep this in PRIVATE.md (git-ignored)
TOK=my-access-token                     # only if the site requires ?token= auth

# 1. Smoke test / warm the cache (run ONE window serially before any parallel
#    sweeps — small Nightscout hosts can 500 on parallel cold fetches)
.build/release/loop-eval simulate --nightscout-url $NS --token $TOK \
    --start 2026-06-01 --end 2026-06-08 \
    --candidate-counterfactual --candidate-label smoke --trace-out smoke.json
```

Then, before trusting any outcome numbers from the site:

2. **Match the deployed configuration** — insulin model (`--insulin-type`; verify IOB
   against devicestatus), retrospective-correction mode (`--integral-rc` for IRC
   periods), deployed-Loop emulation flags, Temporary Overrides, and edited carb
   entries. See [docs/FRONTIERS.md §2](docs/FRONTIERS.md).
3. **Generate the per-site disruption overlays** (pump outages, CGM gaps) and, where
   applicable, carb-revision / override overlays. See [docs/FRONTIERS.md §1](docs/FRONTIERS.md).
4. **Validate**: a stock ISF sweep's TIR-vs-t<54 curve should pass through the site's
   real deployment point. If it doesn't, the config in step 2 is wrong — fix that
   before evaluating candidates.

**Privacy**: Nightscout data is a real person's medical data. Keep URLs and tokens in the
git-ignored `PRIVATE.md`, out of the repo, reports, and issue trackers; refer to datasets
by an anonymous alias (`user1`, `user2`, …) and a placeholder URL in anything shareable.

## Usage

### Evaluate a date range

```bash
loop-eval evaluate \
  --nightscout-url https://your-ns.example.com \
  --start 2026-02-10 \
  --end 2026-02-17 \
  --output table
```

Sample output:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 loop-eval  2026-02-10 → 2026-02-17  (7 days)
 Insulin: rapidActingAdult  |  RC: Standard  |  Future insulin: on  |  Kalman: on
 Predictions: 1962  |  Skipped: 55  |  Eval time: 10.3s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Horizon │    N    │ RMSE  │  MAE  │  Bias  │  P10   │  P90   │ LBGI │ HBGI │ BGRI
─────────┼─────────┼───────┼───────┼────────┼────────┼────────┼──────┼──────┼──────
   30 min │    1889 │  39.1 │  27.5 │  -7.3  │ -53.8  │ +34.3  │ 2.03 │ 3.90 │ 5.93
   60 min │    1880 │  60.6 │  43.9 │ -22.8  │ -95.6  │ +39.4  │ 2.04 │ 3.88 │ 5.91
  150 min │    1841 │ 129.7 │  94.7 │ -76.9  │-212.1  │ +36.0  │ 2.08 │ 3.86 │ 5.93 ◀
  360 min │    1807 │ 268.8 │ 217.8 │-206.1  │-436.9  │  -3.2  │ 1.95 │ 4.05 │ 6.00
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Weighted score (peak 150 min, σ=60 min)
   RMSE:       129.5 mg/dL
   BGRI:        5.95
   Primary:    67.71  (BGRI×0.5 + RMSE×0.5 normalized)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Output formats

- `--output table` — human-readable terminal table (default)
- `--output json`  — machine-readable JSON
- `--output csv`   — one row per horizon, suitable for spreadsheets

### Cache management

Data is cached to `~/.loop-eval/cache/` to avoid re-fetching on repeated runs:

```bash
loop-eval cache list
loop-eval cache clear
```

### Key flags

| Flag | Default | Description |
|---|---|---|
| `--nightscout-url` | required | Base URL of your Nightscout instance |
| `--start` | required | Evaluation start date (YYYY-MM-DD, local time) |
| `--end` | required | Evaluation end date (YYYY-MM-DD, exclusive) |
| `--insulin-type` | `rapidActingAdult` | Insulin model: `rapidActingAdult`, `rapidActingChild`, `fiasp`, `lyumjev`, `afrezza` |
| `--no-future-insulin` | — | Exclude insulin delivered after evaluation time `t` |
| `--no-kalman` | — | Disable Kalman smoothing on actual CGM |
| `--integral-rc` | — | Use integral retrospective correction |
| `--output` | `table` | Output format: `table`, `json`, `csv` |

## Architecture

```
Sources/
  EvalCore/               # Library — all logic, no I/O
    Types/                # EvalGlucoseSample, EvalInsulinDose, TherapySettings, EvalConfig
    DataSource/           # EvalDataSource protocol (pluggable): NightscoutEvalDataSource,
                          #   JSONFileDataSource (Tidepool ETL / offline), DataCache
    Engine/               # DosingEngine protocol + LoopAdapter / OpenAPSAdapter,
                          #   EvaluationEngine, ClosedLoopSimulator, InputWindowBuilder
    Analysis/             # GlucoseInterpolator, BloodGlucoseRisk, KalmanSmoother, EvaluationAnalyzer
  LoopEvalCLI/            # CLI executable (ArgumentParser commands)

# Algorithm packages are git submodules (checked out by --recursive):
#   LoopAlgorithm/   (Loop)            OpenAPSSwift/   (oref/OpenAPS)

Tests/
  EvalCoreTests/          # 47 unit tests + fixture data
```

**Key design decisions:**

- **Pluggable algorithm + data source** — `DosingEngine` abstracts the controller (Loop vs oref) and `EvalDataSource` abstracts the input (Nightscout today), so a new algorithm or data backend is an adapter, not a rewrite
- **No NightscoutKit / LoopKit dependency** — uses native `URLSession`; those pull in HealthKit/CoreData which are iOS-only
- **`generatePrediction()` not `run()`** — supports future insulin without LoopAlgorithm changes
- **2D Kalman smoother** — applied only to the actual CGM used for comparison, not algorithm input; uses RTS backward pass for smooth reference trajectory
- **ISF/CR coverage** — `InputWindowBuilder` always extends therapy schedule entries to cover the full dose and carb windows before calling `generatePrediction()`

## Metrics

| Metric | Description |
|---|---|
| RMSE | Root mean squared error vs smoothed actual CGM |
| MAE | Mean absolute error |
| Bias | Mean signed error (negative = algorithm runs low) |
| P10/P90 | 10th/90th percentile of signed errors |
| LBGI | Low blood glucose index (Clarke-Kovatchev) |
| HBGI | High blood glucose index |
| BGRI | Blood glucose risk index (LBGI + HBGI) |
| Low/High WRMSE | Error weighted by actual-value risk (Approach B) |

The weighted summary uses a Gaussian weight function peaking at 150 minutes (the clinically most actionable horizon) with σ=60 minutes.

## License

MIT
