# CLAUDE.md — LoopEval Project Context

This is the **LoopEval** project: a Swift CLI tool for evaluating [LoopAlgorithm](https://github.com/tidepool-org/LoopAlgorithm) glucose forecast accuracy against real-world CGM data from Nightscout.

The goal is to measure how well the Loop automated insulin dosing algorithm predicts blood glucose, and to safely evaluate the effect of algorithm/settings changes before applying them to a real patient.

---

## ⚠️ Clinical Safety Philosophy — Read This First

**This is safety-critical software. Insulin dosing errors can cause hypoglycemia (lows), which can be immediately life-threatening.**

### Core Principle: Intentional Under-dosing Is a Feature

Loop systematically under-predicts future BG (negative bias). This is **intentional and correct**:
1. BG variability is enormous and largely unpredictable from inputs alone
2. Insulin effects are highly variable person-to-person and day-to-day
3. **Hypoglycemia is far more dangerous than hyperglycemia** — a severe low is immediately life-threatening; a high is uncomfortable but manageable

The large negative bias observed in forecasts (−8 mg/dL at 30 min, worsening to −35+ mg/dL at 90 min) is **expected and should NOT be corrected**. Correcting it would increase dosing and increase lows.

### Priority Order for Any Change

1. **Reduce hypos** — primary goal. Any change that increases hypoglycemia risk is always bad.
2. **Minimize effect on hypers** — don't make hyperglycemia worse.
3. **Reduce hypers without increasing hypos** — ideal, but must be validated.

### Validation Discipline

Any change intended to reduce hyperglycemia MUST:
- Run through all available historical data
- Check whether it would have increased dosing **shortly before a low**
- If yes → **reject the change** regardless of other improvements

This is exactly what LoopEval exists to do.

---

## Metrics Reference

### Primary Safety Metric: ODR (Overdelivery Risk)

**ODR (Dangerous Over-prediction Score)** — penalises over-predictions when actual BG is *below* the target range (< 100 mg/dL). Fires when Loop would have dosed too aggressively into a low. **This is the key safety signal.**

- Changes that **increase ODR** are dangerous — reject them.
- Target: minimize ODR.

### Informational Only: UDR (Underdelivery Risk)

**UDR (Dangerous Under-prediction Score)** — penalises under-predictions when actual BG is *above* the target range (> 115 mg/dL). Fires when Loop under-predicted during a high.

**UDR has a fundamental structural bias from unannounced future carbs.** When a person eats without announcing it, BG rises unexpectedly — Loop couldn't have known. This makes UDR fire frequently and makes it look large by design. **A large UDR is not a red flag.**

- Do NOT optimize to reduce UDR — doing so would mean predicting higher → more insulin → more lows.
- UDR is informational only.

### Primary Score = ODR + UDR

The combined primary score (`weightedOverdeliveryRisk + weightedUnderdeliveryRisk`) is **not a valid optimization target** because UDR is contaminated by the carb bias. Use ODR alone as the primary safety metric.

### Other Metrics

| Metric | Description |
|--------|-------------|
| RMSE | Root mean squared error vs Kalman-smoothed actual CGM |
| MAE | Mean absolute error |
| Bias | Mean signed error (negative = algorithm predicts low, which is expected/intentional) |
| P10/P90 | 10th/90th percentile of signed errors |
| LBGI | Low Blood Glucose Index (Clarke-Kovatchev) |
| HBGI | High Blood Glucose Index |
| BGRI | Blood Glucose Risk Index (LBGI + HBGI) |
| Low/High WRMSE | Error weighted by actual-value risk |

**Clarke-Kovatchev asymmetry:** `rl(50) ≈ 29.6` vs `rh(200) ≈ 3.0` — hypo errors get ~10× more weight than equivalent hyper errors.

**Target range for ODR/UDR:** 100–115 mg/dL (the in-range zone where neither fires).

**Gaussian weighting:** Aggregate scores weight horizons with a Gaussian peaked at **90 min** (σ=60 min), because 90 min is the peak of rapid insulin action — the most consequential horizon for dosing decisions.

---

## Project Structure

```
LoopEval/
├── Package.swift                  # Swift 6.0, macOS 13+
├── Sources/
│   ├── EvalCore/                  # Library — all logic, no I/O
│   │   ├── Types/                 # EvalConfig, EvalGlucoseSample, EvalInsulinDose,
│   │   │                          # EvalCarbEntry, TherapySettings, TherapyTimeline,
│   │   │                          # EvalSnapshot
│   │   ├── DataSource/            # EvalDataSource protocol, NightscoutClient,
│   │   │                          # NightscoutEvalDataSource, DataCache,
│   │   │                          # JSONFileDataSource, ScheduleExpander
│   │   ├── Engine/                # EvaluationEngine (actor), InputWindowBuilder,
│   │   │                          # PredictionComparator, EvaluationResult,
│   │   │                          # PredictionRecord, PreloadedData
│   │   ├── Metrics/               # ErrorMetrics (ODR/UDR/RMSE/etc.), BloodGlucoseRisk,
│   │   │                          # AggregateScore, EvaluationAnalyzer,
│   │   │                          # KalmanSmoother, InsulinInformedKalmanSmoother
│   │   ├── Comparison/            # GlucoseInterpolator, PredictionComparator
│   │   └── Inspection/            # InspectionBundle (for HTML report)
│   └── LoopEvalCLI/               # CLI executable
│       ├── EvaluateCommand.swift  # `loop-eval evaluate` — main eval
│       ├── CompareCommand.swift   # `loop-eval compare` — diff two snapshots
│       ├── BenchCommand.swift     # `loop-eval bench` — A/B on same data
│       ├── InspectCommand.swift   # `loop-eval inspect` — interactive HTML report
│       ├── CacheCommand.swift     # `loop-eval cache` — manage local cache
│       ├── HTMLReportGenerator.swift    # Inspect HTML (Chart.js, 3 panels)
│       ├── ComparisonHTMLGenerator.swift # Compare/bench HTML
│       ├── OutputFormatter.swift  # Table/JSON/CSV output for evaluate
│       ├── CustomDTSRisk.swift    # DTS risk scoring for inspect
│       └── LoopEvalCLI.swift      # Root command / subcommand registration
└── Tests/
    └── EvalCoreTests/
        ├── EvalCoreTests.swift    # Phase 1 unit tests
        ├── Phase2Tests.swift      # Data source / interpolation tests
        ├── Phase3Tests.swift      # Engine integration tests
        ├── Phase4and5Tests.swift  # Metrics & scoring tests
        └── Fixtures/              # JSON fixture data for tests
```

**Key design decisions:**
- **No NightscoutKit / LoopKit dependency** — uses native `URLSession`; those pull in HealthKit/CoreData (iOS-only)
- **`generatePrediction()` not `run()`** — enables future-insulin mode without LoopAlgorithm changes
- **Kalman smoother on actual CGM only** — not on algorithm input; used for cleaner error comparison
- **Swift 6 strict concurrency** — `EvaluationEngine` is an `actor`; all shared state is isolated

---

## Dependencies

```swift
// Package.swift
.package(path: "../LoopAlgorithm"),         // local sibling directory
.package(url: "https://github.com/apple/swift-argument-parser", from: "1.3.0")
```

`LoopAlgorithm` lives at `../LoopAlgorithm` relative to this repo — a sibling directory, **not** a remote package. When cloning into a fresh directory, this path must resolve. See setup script.

---

## CLI Commands

### `loop-eval evaluate` — Main evaluation

```bash
loop-eval evaluate \
  --nightscout-url https://<NS> \
  --start 2026-03-01 \
  --end 2026-03-08 \
  --output table

# Key flags:
# --sensitivity-multiplier 0.9   # ISF multiplier (< 1 = more aggressive)
# --carb-ratio-multiplier 1.1    # CR multiplier
# --basal-rate-multiplier 1.0    # Basal multiplier
# --momentum-cap 0.5             # Cap positive CGM velocity at 0.5 mg/dL/min
# --asymmetric-momentum          # Slow to build / fast to shed positive momentum
# --no-future-insulin            # Real-time simulation mode
# --integral-rc                  # Use integral retrospective correction
# --no-kalman                    # Disable Kalman smoothing on actual CGM
# --save baseline.json           # Save snapshot for later comparison
```

### `loop-eval compare` — Diff two snapshots

```bash
loop-eval evaluate ... --save before.json
# (edit LoopAlgorithm or settings, rebuild)
loop-eval evaluate ... --save after.json
loop-eval compare before.json after.json --detail --html comparison.html
```

### `loop-eval bench` — A/B test settings on same data

```bash
loop-eval bench \
  --nightscout-url https://<NS> \
  --start 2026-03-01 --end 2026-03-08 \
  --baseline-label "Current ISF" \
  --candidate-label "Lower ISF (0.9×)" \
  --candidate-sensitivity-multiplier 0.9 \
  --html bench-report.html
```

Fetches data once, runs two configs, produces an HTML comparison report.

### `loop-eval inspect` — Interactive HTML report

```bash
loop-eval inspect \
  --nightscout-url https://<NS> \
  --start 2026-03-01 \
  --end 2026-03-08 \
  --output report.html
```

Generates a self-contained HTML with:
1. Input data timeline (raw CGM, Kalman-smoothed CGM, doses, carbs)
2. Forecast error profile by horizon (RMSE, bias, P10/P90, ODR/UDR)
3. Prediction detail — scrub through time to inspect individual prediction curves vs actual glucose
4. Worst offenders panel — most dangerous misprediction moments
5. DTS risk timeline — color-coded heat map of over/under prediction danger

---

## Infrastructure

- **Test NS instance:** `https://<NS>`
- **Repo:** `https://github.com/loopkitdev/LoopEval`
- **GitHub config:** `GH_CONFIG_DIR=/Users/bot/loopdev/.gh-config gh ...`
- **Report server:** `http://macmini:8765/` (share HTML reports at this URL)
- **Build output:** `.build/debug/loop-eval` or `.build/release/loop-eval`
- **Data cache:** `~/.loop-eval/cache/` (Nightscout data cached to avoid re-fetching)

---

## Build & Test

```bash
# Build debug
swift build

# Build optimized
swift build -c release

# Run tests
swift test

# Quick eval against test NS
.build/debug/loop-eval evaluate \
  --nightscout-url https://<NS> \
  --start 2026-03-01 --end 2026-03-08
```

**For long-running builds/evals:** Use tmux — bare `exec` buffers all output until completion.

```bash
tmux new-session -d -s eval -x 220 -y 50
tmux send-keys -t eval "cd ~/loopalgo/LoopEval && .build/debug/loop-eval evaluate --nightscout-url https://<NS> --start 2026-03-01 --end 2026-03-08" Enter
tmux capture-pane -t eval -p | tail -20
```

Eval runs take ~60–90 seconds.

---

## EvalConfig — Key Parameters

All EvalConfig fields with their defaults:

| Field | Default | Description |
|-------|---------|-------------|
| `evalStep` | 300s (5 min) | How often to advance prediction start |
| `includeFutureInsulin` | true | Include future-scheduled insulin |
| `insulinLookbackHours` | 16h | Insulin history window |
| `glucoseLookbackHours` | 10h | CGM history window |
| `kalmanSmoothing` | true | Kalman-smooth actual CGM before comparison |
| `useIntegralRC` | false | Integral vs standard retrospective correction |
| `sensitivityMultiplier` | 1.0 | ISF scalar (>1 = more conservative) |
| `carbRatioMultiplier` | 1.0 | CR scalar |
| `basalRateMultiplier` | 1.0 | Basal scalar |
| `targetLow` | 100 mg/dL | Lower bound of target range (ODR threshold) |
| `targetHigh` | 115 mg/dL | Upper bound of target range (UDR threshold) |
| `positiveVelocityCap` | nil | Cap on positive CGM momentum velocity (mg/dL/min) |
| `useAsymmetricMomentum` | false | Asymmetric EMA: slow rise, fast drop |
| `momentumAlphaSlow` | 0.15 | EMA alpha for building positive momentum |
| `momentumAlphaFast` | 0.85 | EMA alpha for shedding positive momentum |

---

## Recent Work (April 2026)

The project has matured through several phases:

1. **Core engine** — NS data fetching, `generatePrediction()` sweep, RMSE/BGRI metrics
2. **Data pipeline** — Nightscout client, local cache, therapy settings expansion
3. **Advanced metrics** — ODR/UDR (dangerous over/under-prediction scores), Clarke-Kovatchev risk weighting
4. **HTML reports** — Interactive inspect report (3-panel Chart.js), comparison HTML
5. **Snapshot workflow** — `--save` + `compare` for before/after diffs
6. **Bench command** — A/B settings comparison on same data (no double-fetch)
7. **Asymmetric momentum** — `--asymmetric-momentum` flag: dampens positive momentum (slow to build, fast to shed) to reduce over-prediction during meal rises
8. **Momentum cap** — `--momentum-cap` to hard-limit positive CGM velocity

### ODR/UDR Decision History

ODR/UDR were introduced, briefly removed, then **reinstated in April 2026** with the explicit caveat that UDR is structurally biased by unannounced carbs and must not be optimized. The HTML comparison report now includes an ODR/UDR explainer panel explaining this.

### Current Known State of Forecasts

- Large negative bias is expected and intentional (see Clinical Philosophy above)
- NS forecasts in the inspect report (overlay) come from older Loop (pre-LoopAlgorithm package) — divergence from our reconstruction is expected and normal
- The Gaussian aggregate weight peaks at 90 min (not 150 min as in earlier versions) — 90 min is where rapid insulin action peaks

---

## What to Work on Next

Look at open GitHub issues and recent discussions. Potential areas:

- **Additional settings multipliers** — different ISF per time-of-day, etc.
- **Multi-patient support** — evaluating across multiple NS instances
- **More algorithm variants** — testing different LoopAlgorithm configurations
- **Better visualization** — improvements to inspect report panels
- **CI / automated regression testing** — snapshot-based regression detection

Always run through the safety validation checklist before shipping any change that affects dosing behavior.
