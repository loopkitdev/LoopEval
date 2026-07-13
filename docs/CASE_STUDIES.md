# Case studies

*Zoom into a specific window and verify — is the simulator operating correctly, and is
the candidate doing something sensible?*

A case study is a multi-panel plot of one scenario: BG (real + counterfactual), insulin
**delivery** (basal staircase + boluses, automatic vs manual), **patient IOB**, and
algorithm internal state (COB, retrospective correction, momentum, forecast). Use them
to root-cause every surprising outcome number before believing it — most "algorithm
findings" turn out to be data or replay artifacts until they survive a case study.

The renderer is `loopeval_analysis.case_study.plot_case`. It reads a
`simulate --trace-out` JSON.

## What the trace gives you

`simulate --candidate-counterfactual ... --trace-out trace.json` emits:

- **`actual`** — the real CGM series; **`counter`** — the candidate's counterfactual BG.
- **`delivery[]`** — the canonical delivery stream, uniform for both arms:
  `{t, tEnd, source: field|candidate, kind: basal|bolus, automatic, amountU, rateUhr}`.
  *Field* = the real pump history (real basal rates with scheduled-basal gaps filled,
  real auto/manual flags). *Candidate* = what the candidate delivered (5-min temp
  segments, auto-boluses, and passed-through manual boluses — resized by the IOB-aware
  passthrough, so they are generally *not* identical to the field's).
- **`predictions[]`** — per-step decision internals for both arms: `candidateIOB/COB/
  RC/Momentum/EventualBG/ICE/...` and `baseline*` equivalents, plus:
  - **`patientIOBField` / `patientIOBCandidate`** — the *patient IOB*: each arm's
    delivered doses run through the **same** patient insulin model (net-basal, gap-filled,
    ripple-free). This is the fair IOB comparison — independent of Nightscout
    devicestatus timing and of any candidate IOB-computation experiments.

Two labeling rules learned the hard way:

- `baselineDose` is the baseline arm's *recommendation*, *not* delivery — never plot it
  as "field dosing". Use `delivery[]`.
- `baseline*` state columns are **our reconstruction** of the deployed algorithm on real
  inputs, not the deployed app's recorded state. Where deployed Loop *did* record state
  (IOB, COB, predicted BG in devicestatus), overlay that as ground truth instead;
  RC and momentum have no recorded ground truth.

## Standard plot

```python
import pandas as pd, pytz
from loopeval_analysis.case_study import (
    load_trace, plot_case, panel_field_vs_candidate, fetch_devicestatus_state)
from loopeval_analysis.outage import read_outages_csv
from loopeval_analysis.cgm_gaps import read_cgm_gaps_csv

TZ = pytz.timezone("America/Chicago")
HOST = "https://YOUR-NS.example.com"          # keep private — don't commit
tr = load_trace("trace.json", label="candidate", tz=TZ)
center = TZ.localize(pd.Timestamp("2026-07-02 23:04"))

ds = fetch_devicestatus_state(HOST, center - pd.Timedelta(hours=4),
                              center + pd.Timedelta(hours=4), TZ)   # real recorded state
extra = [
    panel_field_vs_candidate("candidateCOB", None, "COB", "g", fill=True,
                             ground_truth=ds.get("cob")),
    panel_field_vs_candidate("candidateRC", None, "RC effect", "mg/dL"),
    panel_field_vs_candidate("candidateMomentum", None, "momentum", "mg/dL"),
    panel_field_vs_candidate("candidateEventualBG", None, "eventual BG", "mg/dL",
                             ground_truth=ds.get("eventualBG")),
]
plot_case([tr], center, window_hours=6.0, nightscout_host=HOST, out="case.png",
          outages=read_outages_csv("outages.csv"),
          cgm_gaps=read_cgm_gaps_csv("cgm_gaps.csv"),
          extra_panels=extra)
```

Standard panels:

1. **BG** — real CGM and counterfactual, as points; 54/70/180 lines; carb annotations;
   outage/CGM-gap shading.
2. **Delivery** — one shared numeric axis (basal U/hr and boluses U). Basal is a
   staircase (vertical connectors at rate changes; 0 U/hr sits visibly above the axis);
   boluses are stems — filled circle = automatic, hollow diamond = manual. Field black,
   candidate colored, both semi-transparent so overlap reads.
3. **Patient IOB** — `patientIOBField` vs `patientIOBCandidate` (same model, both arms),
   with devicestatus IOB as a dotted reference.
4. **Extra panels** — anything from `predictions[]` via `panel_field_vs_candidate`
   (candidate state ± devicestatus ground truth), or fully custom callables
   (`(ax, traces, win_start, win_end, t_center) -> label`).

To find windows worth studying, `case_study.enumerate_lows(trace)` lists counterfactual
low events (nadir, duration); `build_case_report` renders a multi-event HTML gallery.

## Interpreting what you see

- **Compression lows / CGM 40-floor**: a sharp overnight drop that pegs at exactly
  40 then bounces is sensor pressure, not physiology. Both arms inherit the drive (it's
  in ICE), but the *counter* isn't clamped at 40 and can read deeper than the field
  trace. Don't count these against a candidate.
- **Counterfactual divergence**: the counter's BG level drifts from the real trace
  wherever cumulative dosing differed; at matched IOB a lower counter simply *started*
  the event lower. Check patient-IOB before attributing a low to "dosing more".
- **Rescue carbs**: a real low is followed by real carbs, and the counterfactual inherits
  them via ICE even if the counter never went low (spurious post-low rise on the
  candidate). Symmetrically, a candidate's low that the field avoided gets *no* rescue.
- **Manual boluses differ by design**: the IOB-aware passthrough shrinks/grows the
  user's manual boluses by the candidate-vs-real IOB difference. Zeroed diamonds on the
  candidate mean it already carried the insulin, not that the bolus was dropped.
- **One-sided actuation**: during a fall the algorithm can only stop delivery; if
  delivery is already zero there is nothing left for a candidate to improve at that
  moment — the difference has to come from earlier decisions.

## Verifying the sim itself

When a case study looks wrong, check in this order: identity sim (identical configs ⇒
counter == actual, Δdose ≈ 0); delivery stream vs raw dose history for the window;
patient IOB vs devicestatus IOB; then the candidate logic. The bugs are usually in
inputs and replay fidelity, not the controller.
