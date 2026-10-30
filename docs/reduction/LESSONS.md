# reduction lessons

1. **Loop's dose is roughly proportional to every schedule it reads, and its history beyond 3 h barely matters
   (ablation, 2026-10-30).** Shipped LoopAlgorithm (main e3f5e3c) on 3,765 exported decisions (6 pilot donors × 3
   days, simulator's fixture export), one channel perturbed at a time; insulin per 5 min = bolus + temp × 5/60, base
   mean 0.109 U (std) / 0.098 U (gr). Mean |Δ| relative to the base mean, gr: ISF ×0.8 46 %, basal ×1.2 47 %,
   target +10 24 %, CR ×1.2 19 %; carbs removed 28 %; momentum + RC off 54 %; glucose history cut to 60 min 52 %,
   to 180 min 9 %; doses older than 3 h dropped 24 %. A settings error passes almost one-for-one into the dose, so
   the settings are a large share of what the user is asked to get right; the glucose record that matters is the
   last ~3 h. Six donors and three days: a sizing, not a census. `runs/2026-10-30-reduction-ablation/`
   (`run_ablate.sh`, `summarize.py`, `summary.csv`).
2. **Per-decision imitation of Loop from reduced inputs is poor; that is not the bar (2026-10-30).** Same 3,765
   decisions (gr). Linear, leave-one-donor-out: Loop's eventual BG from glucose + 15-min slope R² 0.30, + insulin
   on board 0.38, + entered carbs 0.47 (TDD scales; the donor's own schedules do no better, 0.30–0.34). The dose
   itself, rectified fit: R² 0.22–0.24 for every set; even Loop's own eventual BG explains only 0.53 of it
   (0.4 × max(0, (eventual − target) / ISF)), the rest being guard/runway and the dose floors. Yet on one donor
   (i001, 28 d) a TDD-only controller on glucose, slope and automatic-insulin IOB came within 2 TIR points of gr in
   closed loop at the same daily insulin. Closed-loop outcomes, not dose fit, decide. `runs/2026-10-30-reduction-imitate/`.
3. **A fixed TDD scale fails across people: needs in the scored window are 0.1–4.6× the pre-window TDD (iteration 1,
   2026-10-30).** 35 pilot donors (fixed stratified subset, i202 dropped: no clean pre-window days), 28 days, dr
   harness. tdd_pd (glucose + 15-min slope + automatic-insulin IOB, every scale from pre-window TDD, meal-bolus IOB
   ignored) at TDD × 1.0 against gr: TIR 59.9 vs 70.0 (−10.1 [−15.3, −5.0]), t<70 8.9 vs 1.8 (+7.1 [+4.1, +10.6]),
   t<54 +3.3; no point of its TDD sweep (×0.8–1.25) or of the aggressive / half-meal-bolus / carbs variants reaches
   the needs-dial curve. Same total insulin as gr (feedback catches up), delivered late. The losses sit with the
   donors whose window need departs from their history (i018 31 → 64 U/day: −63 TIR; a broken-looking record,
   i050, 80 → 7: t<70 44 %). Loop survives these through RC and the person's own settings edits; a surrogate needs
   its own adaptation, keyed to glucose outcomes. Low announcers lose most (−20 TIR), high announcers least (−4).
   `runs/2026-10-30-reduction-ec/` (`batch.py`, `it1_cohort.txt`, `per_donor.csv`).
