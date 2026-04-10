# LoopEval Cheatsheet

## Build
```bash
swift build                    # debug
swift build -c release         # optimized
swift test                     # run all tests
```

## Common Commands

```bash
NS=https://<NS>

# Basic eval
.build/debug/loop-eval evaluate --nightscout-url $NS --start 2026-03-01 --end 2026-03-08

# Save snapshot for comparison
.build/debug/loop-eval evaluate --nightscout-url $NS --start 2026-03-01 --end 2026-03-08 \
  --save before.json --label "Baseline"

# A/B settings comparison (same data, one fetch)
.build/debug/loop-eval bench --nightscout-url $NS --start 2026-03-01 --end 2026-03-08 \
  --baseline-label "Current" \
  --candidate-label "ISF 0.9x" \
  --candidate-sensitivity-multiplier 0.9 \
  --html bench.html

# Diff two snapshots
.build/debug/loop-eval compare before.json after.json --detail --html compare.html

# Interactive inspection report
.build/debug/loop-eval inspect --nightscout-url $NS --start 2026-03-01 --end 2026-03-08 \
  --output inspect.html

# Momentum experiments
.build/debug/loop-eval evaluate --nightscout-url $NS --start 2026-03-01 --end 2026-03-08 \
  --momentum-cap 0.5               # cap positive velocity at 0.5 mg/dL/min
  --asymmetric-momentum            # slow to build / fast to shed upward momentum
```

## Key Flags

| Flag | Default | What it does |
|------|---------|--------------|
| `--sensitivity-multiplier` | 1.0 | ISF scalar; <1 = more aggressive (risky!) |
| `--carb-ratio-multiplier` | 1.0 | CR scalar |
| `--basal-rate-multiplier` | 1.0 | Basal scalar |
| `--momentum-cap` | none | Cap positive CGM velocity (mg/dL/min) |
| `--asymmetric-momentum` | off | Slow-rise / fast-drop EMA momentum |
| `--no-future-insulin` | off | Exclude future insulin (real-time sim) |
| `--integral-rc` | off | Integral vs standard retrospective correction |
| `--no-kalman` | off | Disable Kalman smoothing on actual CGM |
| `--save FILE` | — | Save snapshot JSON for compare command |

## Metrics Quick Reference

| Metric | Lower = better? | Notes |
|--------|----------------|-------|
| **ODR** | ✅ Yes | **Primary safety metric.** Over-prediction during lows. |
| **UDR** | ⚠️ Misleading | Biased by unannounced carbs. Do NOT optimize. |
| **Primary (ODR+UDR)** | ⚠️ Misleading | Not a valid target. UDR contaminated. |
| RMSE | ✅ Yes | Overall forecast error |
| BGRI | ✅ Yes | Risk-weighted error (hypo-heavy) |
| Bias | — | Negative bias is expected and intentional |

## Safety Checklist Before Shipping

- [ ] ODR did not increase
- [ ] Did not increase dosing at any time shortly before a low
- [ ] Validated on full date range (not cherry-picked)
- [ ] If UDR increased, that's fine — it's biased anyway

## Report Server

Share HTML reports at `http://macmini:8765/<file>.html`

## GitHub

```bash
GH_CONFIG_DIR=/Users/bot/loopdev/.gh-config gh ...
# Repo: https://github.com/loopkitdev/LoopEval
```
