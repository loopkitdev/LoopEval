# Cycle-override cohort: Loop does not recover the override; slow RC recovers a third

From **frontier** to **research**, answering TIDEPOOL-96. Ledger entry
[E62](../candidates/README.md#e62--cycle-override-cohort-what-loop-recovers-without-the-override). Evidence:
`runs/2026-10-25-cycle-replay/` (`score_stock.txt`, `score_gr.txt`, `screen_decisions.csv`).

## What was run

Your cycle-override cohort, exported at v32: 194 cycle runs from 61 people, each from 10 days before switch-on to 8
days after release. Each person's deployed config (GBAF, RC mode, insulin) was recovered by matching recorded
recommendations; the as-recorded replay sits within 0.5 mg/dL and 0.5 TIR of the field in every phase. Arms: as
recorded; the insulin-up cycle override removed (other overrides kept); removed + slow RC (C38, τ 6 h / 24 h); the
same on guard + runway.

## Results

- **Field run-up:** in the 3 days before switch-on, mean +3.7 mg/dL and TIR −2.1 against the person's own pre days.
  With the override on, TIR is still −1.8. After release, t<70 +0.39.
- **Without the override**, override days lose 7.6 TIR [−10.3, −5.5] (mean +18 mg/dL). Loop's feedback does not make
  it up. On guard + runway: −7.0.
- **Slow RC recovers about a third**: 24 h −5.2 (+0.55 TIR in the run-up), t<70 +0.1–0.3 on non-override days;
  6 h −4.7 but t<54 +0.12 on every non-override phase (a replay guard flag).

## For research

A generic multi-day adapter is not a substitute for the override. The openings are the predictable run-up and a
cycle-aware needs schedule (or prompting the person to switch on earlier). Frontier is scoping algorithm options next.
