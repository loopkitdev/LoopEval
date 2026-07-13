# Frontier experiments

*Does an algorithm or settings change actually improve outcomes — or does it just slide
along the aggressiveness trade-off?*

Every dosing algorithm has one obvious dial: overall aggressiveness (ISF, application
factor, targets). Turning it trades time-in-range against severe lows along a smooth
curve. Most "improvements" turn out to be points on that same curve. A change only
matters if it sits **above** the curve — more TIR at the same t<54. We call that
**lift**, and measuring it is the frontier workflow.

## 0. Prerequisites

- A Nightscout site (or exported JSON data) with weeks–months of CGM + insulin history.
  **Keep the URL private** — parameterize scripts with `NS=$YOUR_NS_URL`, never commit it.
- Build: `swift build -c release` → `.build/release/loop-eval`.
- Python: `pip install pandas numpy matplotlib pytz` and put `analysis/` on `PYTHONPATH`
  (or `pip install -e analysis`).

## 1. Generate the per-dataset overlays (once per dataset/window)

```bash
NS=https://YOUR-NS.example.com
python3 -m loopeval_analysis.outage   from-nightscout --host $NS \
    --start 2026-05-01 --end 2026-07-01 --tz America/Chicago --out outages.csv
# cgm_gaps reads the glucose cache — run one simulate first to warm it, then:
python3 -m loopeval_analysis.cgm_gaps from-cache --host YOUR-NS.example.com \
    --start 2026-05-01 --end 2026-07-01 --tz America/Chicago --out cgm_gaps.csv
# If the user edits carb entries after logging (check!), reconstruct what Loop saw:
python3 -m loopeval_analysis.reconstruct_carb_history from-nightscout --host $NS \
    --start 2026-05-01 --end 2026-07-01 --tz America/Chicago --out carbrev.json
# If the user runs Temporary Overrides:
python3 -m loopeval_analysis.override_targets from-nightscout --host $NS \
    --start 2026-05-01 --end 2026-07-01 --tz America/Chicago --out overrides.json
```

Pump outages are clamped *in* the sim (`--outages-csv`) and excluded from scoring;
CGM gaps skip the dosing cycle (`--cgm-stale-guard-min 5`) and are excluded from scoring.

## 2. Establish the deployment-faithful base config

The reference sweep must reproduce what the deployed system actually does, or replay
error gets misattributed to candidates. Per dataset, determine:

- **Insulin model** (`--insulin-type`): check IOB against devicestatus; Fiasp/Lyumjev
  users are peak-55, not the rapid-acting-adult default.
- **RC mode**: `--integral-rc [--integral-rc-clamp]` for periods the user ran Integral
  Retrospective Correction. The flag isn't uploaded — infer from data if unknown.
- **Deployed-Loop emulation**: `--no-mid-absorption-isf --no-gradual-transitions-gate`
  matches the shipping Loop app (see `docs/loop-algo-classes.md`).
- **Overrides / carb edits**: `--apply-overrides --override-targets-json overrides.json`,
  `--carb-revisions-json carbrev.json` where applicable.

A good validation that the config is right: the stock sweep's curve should pass through
(or very near) the **field point** — the real deployment's own TIR/t54.

## 3. Run the reference sweep + candidates

```bash
BIN=.build/release/loop-eval
CR="--counter-reg-onset 54 --counter-reg-gain 0.4 --counter-reg-max 8.0 \
    --cgm-stale-guard-min 5 --glucose-lookback-hours 24 --insulin-lookback-hours 24"
BASE="--candidate-counterfactual --candidate-infer-sensitivity \
      --no-mid-absorption-isf --no-gradual-transitions-gate $CR \
      --outages-csv outages.csv --nightscout-url $NS \
      --start 2026-05-01 --end 2026-07-01"
# ... plus your per-dataset flags from step 2 (insulin type, IRC, overrides, carbrev)

# reference curve: ISF multipliers (run ONE serially first to warm caches,
# then the rest in parallel — cold parallel fetches can 500 a small NS host)
$BIN simulate $BASE --candidate-sensitivity-multiplier 1.00 \
    --baseline-label S --candidate-label m1.00 --trace-out m1.00.json
for M in 0.70 0.80 0.90 1.10 1.20 1.30 1.40; do
  $BIN simulate $BASE --candidate-sensitivity-multiplier $M \
      --baseline-label S --candidate-label m$M --trace-out m$M.json &
done; wait

# candidates (examples)
$BIN simulate $BASE --candidate-integral-rc --candidate-irc-drop-scale 1.5 \
    --candidate-irc-rise-scale 0.5 --candidate-label airc --trace-out airc.json
$BIN simulate $BASE --candidate-sensitive-mode-tau-min 180 \
    --candidate-sensitive-mode-gain 0.02 --candidate-label dlp --trace-out dlp.json
```

The counter-regulation floor (`--counter-reg-*`) models the body's endogenous response
below 54, keeping counterfactual lows physiologic instead of unbounded.

## 4. Score, compute lift, plot

```bash
python3 -m loopeval_analysis.frontier \
    --ref 'm*.json' \
    --cand airc.json:asym-IRC --cand dlp.json:double-low-prevention \
    --outages-csv outages.csv --cgm-gaps-csv cgm_gaps.csv \
    --field-from m1.00.json --out frontier.png
```

This prints the reference curve, each candidate's TIR / t<54 / **lift**, and the field
point, and renders the standard plot (x = TIR right-is-better, y = t<54 up-is-worse,
dotted 1% budget line; better = lower-right).

**Reading lift:**

- **lift ≈ 0** — the change is a slider. Equivalent outcomes were available by tuning
  ISF. Not an improvement (not necessarily useless — it may be a nicer *parameterization*
  — but it's not frontier).
- **lift > 0** (beyond run-to-run noise, ~±0.3 on multi-week windows) — structural
  improvement; verify it holds at 2–3 points along the curve (re-run the candidate at
  ×0.9/×1.1) and on the full available date range.
- **lift < 0** — the change is worse than doing nothing but tuning.

## 5. Believe it only after robustness

- **Full-range re-run** — single-window wins usually evaporate.
- **Both directions of the curve** — a lows-reducer must be tested at the aggressive end
  (low ISF multipliers) where lows exist to reduce.
- **Second dataset** if available — ranking transfer matters more than absolute numbers.
- **Safety detail**: check `iob_cross54_*` (committed insulin into severe lows) and AUC<70
  alongside t<54; check delivery shortly before lows didn't increase.
- **Known confounds**: rescue carbs bias against hypo-prevention candidates; compression
  lows inflate absolute t<54 on both arms (deltas hold).

## Current picture (qualitative)

Regenerate numbers for your dataset — they do not transfer as absolutes. As of the last
broad re-baseline:

- **Asymmetric IRC** (drop-scale > rise-scale) — genuine lift; the drop side of
  retrospective correction cleans up developing lows without amplifying rise-chasing.
- **Double-low prevention** (`sensitive-mode`) — genuine lift; damps re-dosing into the
  post-low rebound, preventing the delayed second low.
- **GBAF, flat ISF, application factor** — sliders. Useful dials, no lift.
- The largest factor by far is **meal announcement** (user behavior, not algorithm):
  announcing users operate far above anything hands-off automation reaches.
