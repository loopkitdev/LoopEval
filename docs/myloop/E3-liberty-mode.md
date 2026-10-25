# E3 — Time-of-day-scaled rise response with no meal entries (pre-registration)

Written 2026-10-25, before any no-entry trace was computed. Board: TIDEPOOL-95.

## Question

CamAPS Liberty is described as an "accelerated response to changing glucose trends" that "recognises insulin need
depending on time of day". It has no meal entries and no published meal detector. One reading of that is that the response to a rise
is stronger at the clock times when this person usually needs more insulin. Loop's rise response with no entries is
retrospective correction plus momentum (`known` below). Does the person's same-clock history on previous days tell us how
far a rise will run, beyond what `known` already says? And if it does, does it act through the *size* of the
rise response (multiplicative), or as a separate term (additive, the form C39 `habrelr` already scored)?

Already measured (lookback study part 6, `runs/2026-10-06-lookback/habit_rc.py`): with meal entries in place, on nine
90-day beds, the multiplicative form adds nothing to the additive one (holdout R² 0.13 vs 0.13). That study never ran the
regime Liberty is built for. With no entries, announcers' meals become unexplained appearance, so their habit should be far
stronger than it is with entries. The dial also becomes expensive there, because large unannounced rises produce lows at any
setting. Per M1 that is where forecast information can pay.

## Stage A — forecast check (offline)

- **Cohort:** frontier's 2026-10-23 dosing harness, the 189 donors with a `gr` trace. Same window (last 28 full days, 22 h of warm-up),
  same binary (`dr/loop-eval`) and flags.
- **Regime:** `gr` + `--no-carb-entries --no-user-boluses`, needs dial 1.00. The plant is the measured ICE, so every meal
  still happens. Only the controller is denied the entries.
- **Series**, per 5-min step: r = candidate ICE (no carb share: there are no entries); `known` = RC marginal + momentum
  marginal; target Y = Σ r over (t, t + 120 min]; habit = mean of Y at the same clock time on the previous 1–7 days, with at least three
  available (C39's definition, model-free and causal).
- **Rising states:** `known` > +10 mg/dL. Temporal holdout: fit the first 70 % of each donor's rising steps and score the
  last 30 %. A donor qualifies with ≥ 300 / 150 rising steps.
- **Models** (least squares per donor): `b·known`; `+habit` = a + b·known + c·habit; `×habit` = a + (b + d·habit)·known
  + c·habit.

### Bar (fixed before running)

- **A1, habit informs rises with no entries:** holdout R²(`+habit`) − R²(`b·known`) ≥ 0.03 on at least half the qualifying
  donors.
- **A2, the time-of-day scaling is its own lever:** holdout R²(`×habit`) − R²(`+habit`) ≥ 0.02 on at least a third of the
  qualifying donors, with median > 0.
- **Reading:**
  - A1 and A2 pass: build the multiplicative candidate (an RC rise scale driven by the habit) and score it closed-loop.
  - A1 passes, A2 fails: the time-of-day scaling collapses to the additive habit. Stage B scores the additive form, C39
    `habrelr`, in the no-entry regime.
  - A1 fails: no time-of-day lever with no entries. Closed.
- Also reported: the realised-to-known ratio Y / `known` by habit tercile (the "rise scale" the habit would imply), and the
  same for announcers vs hands-off donors (manual-bolus share from the field).

## Stage B — closed loop (outline; pre-registered in full once Stage A reads)

No-entry regime on the same 189 donors. Arms: `gr`; `gr` + the time-of-day lever from Stage A; each at needs 0.95 / 1.00 /
1.05 for the lift. The bar is the frontier one: ΔTIR > 0 and Δt<54 ≤ 0 at the operating point, plus positive lift against the dial.

## Limits that bound the claim

- This tests one reading of Liberty's description, not Liberty itself. Its internals are not public.
- Replay's lows axis is unvalidated (ledger M11). A Stage B pass goes to the ICE generator or the additive plant before any
  verdict.
- R² on closed-loop data is not therapy evidence (C19, O1). Stage A only decides what is worth simulating.
