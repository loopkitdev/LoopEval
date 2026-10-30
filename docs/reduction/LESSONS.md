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
4. **An outcome-keyed scale fixes the high side; the lows are the control law's, not the settings' (iterations 2–5,
   2026-10-30).** Same 35 donors. A slow integral on glucose above a set point (faster down below 80) moves the
   TDD scale: at set point 140 TIR 69.2 vs gr 70.0 (−0.9 [−3.5, +1.9]), but t<70 8.5 vs 1.8 and t<54 +2.9. The
   set point is a dial (130 → 160: TIR 71.6 → 62.3, t<70 10.1 → 4.1); at 160 the arm sits 10.8 TIR below the needs
   dial at equal t<70. None of these moved t<70 off 5.7–8.6: entered carbs offsetting meal boluses, a fading
   meal-bolus discount, proportional basal, slope horizon 0/15/30, application factor 0.25, slope cap, bolus
   threshold, basal fraction 0.25/0.35, basal decoupled from the scale, 10× faster cut on lows. The excess is broad
   (28 of 35 donors), unrelated to manual-bolus share (r 0.04). Before a crossing of 70 the surrogate has given
   2.6 U automatic in the prior 1–3 h against gr's 1.75, and carries 0.54 U IOB at the crossing against 0.07.
   Case (i081, unannounced meal 100 → 249 mg/dL in 30 min): six consecutive 1.1–1.75 U boluses stack IOB from 3 to
   10.5 U, then 53 mg/dL two hours later; the adaptive scale had climbed to 1.5× and strengthened the correction ISF
   with it. Same daily insulin as gr, front-loaded. `it2..it5_cohort.txt`, `traces/i081_case7.*`.
5. **In replay, every settings-free form sits far above Loop's curve; the scale is not the cause (iterations 6–8,
   2026-10-30).** Same 35 donors. Oracle check (future data, diagnostic only): with each donor's true in-window TDD
   as a fixed scale the surrogate is 20–26 TIR below the needs dial at equal t<70 (×0.8: TIR 43.2 at t<70 1.7;
   gr ×1.0: 70.0 at 1.8). A net-IOB cap (2/3/4 h of average delivery) and a correction ISF held at TDD0 change
   nothing. Two real gaps found by case study (i018, Loop TIR 90): no retrospective correction (glucose held at
   220–240 for hours while the surrogate trusted its IOB) and a background rate set at 0.45 TDD/24 = 1.1 U/h against
   a person whose schedule is 1.7–2.4 U/h. Adding both (RC on the 30-min glucose change insulin did not explain;
   background rate = median pre-window hourly automatic delivery) moves the curve right: ×1.0 TIR 69.4, t<70 7.0;
   ×0.9 65.3 / 4.7 — still ~3× gr's t<70 at equal TIR. Across 55 arms, total insulin per arm stays within ±4 % of
   gr's: over days, any controller that keeps glucose bounded delivers what the person's ICE demands (mass
   balance), so arms differ only in timing. That every law, gain and cap leaves t<70 at 4–9 suggests a replay
   bias against controllers whose timing departs from the field's (myloop lesson 10); this is untested until the
   same arms run on a body with a known answer. `sweeps_t70.png`, `sweeps_t54.png`, `per_donor_all.csv`.
6. **Replay and the additive sim disagree by ~15 TIR points on the same settings-free surrogate (2026-10-30).**
   tdd_pd with background rate + RC (glucose, 15-min slope, own automatic IOB, 30-min unexplained glucose change,
   entered carbs at a TDD carb ratio; TDD and background rate learned, nothing user-set but limits). Replay, 35
   donors × 28 d: ~12 TIR below gr's needs dial at equal t<70. Additive sim (current reference, rc_own / gb_own /
   night_pro / uls / ex_sat 0.1; 112 people × 14 d, seed0 1000), at ×0.9: TIR 72.4, t<70 2.37, t<54 0.44, 44.7
   U/day; against gr's dial (σ-band k 1.0 flat: the twins have no σ5 baseline) **+3.4 TIR [+2.2, +4.9] at equal t<70,
   +2.4 [+1.5, +4.5] at equal t<54** (true glucose +3.1 / +2.3); against stock Loop +4.6 / +3.4. At the TDD of
   Loop ×1.1 it has more TIR and fewer lows. 20 % of people lose TIR, 49 % gain t<54; worst person +1.3 points t<54.
   The surrogate's ×1.0 and up, and both adaptive-scale forms, leave the dial's range on the lows side. Caveats:
   traits were read from Loop's delivery in the same 14 days (the simulated people are stationary, so this stands
   in for history, but it is not held out); the additive sim is known to reward added insulin more than the field
   (memory: response by control level) and the surrogate adds ~2.5 U/day. The ICE generator decides between them.
   `runs/2026-10-30-reduction-additive/` (`run_loop.sh`, `run_gr.sh`, `run_surr.sh`, `traits.py`, `score.py`,
   `score_gr.txt`).
7. **The ICE generator sides with the additive sim: the settings-free surrogate beats gr's needs dial at equal
   lows, on both trainings (2026-10-30).** Same surrogate as lesson 6 (TDD and background rate from the 14 days
   before each held-out window, ×0.9 / ×1.0), hands-off regime (no entries, no user boluses), 163 donors × 28 d,
   trainings v32oc{0,1}TcB2FGUCGLBGGSKaLK; gr dial = needs ×0.95–1.25 (the surrogate's lows lie past ×1.05, so the
   dial had to be extended to read the gap). At ×0.9: TIR +3.3 / +2.8 against gr ×1.0, t<70 +0.48 / +0.19, t<54
   +0.17 / +0.07 (training 0 / 1; gr t<54 baselines 0.54 / 0.38, guard lines ×1.26 / ×0.88), insulin within 1 %
   of gr's. **Against the dial: +1.4 TIR [+0.4, +2.3] / +1.9 [+0.9, +2.9] at equal t<70, +1.0 [−0.1, +2.2] / +1.4
   [+0.3, +2.5] at equal t<54**; true glucose identical. ×1.0, training 1: +2.4 [+1.6, +3.2] at equal t<70; on
   training 0 its t<70 (3.38) is just past ×1.25 (3.31). Per donor at ×0.9: 52–54 gain more than 5 TIR, 12–15
   lose more than 5; the losers are under-dosed, not over-dosed (i181: mean 181 vs 152 mg/dL, fewer lows, same
   insulin; i043 likewise) — the TDD-rule ISF is too weak for them. So two of three tools, including the one with
   the best record on change (memory: replay predicts change), say the surrogate is better than Loop at matched
   lows; replay's −12 is most likely its known bias against timing that departs from the field. Scale of the
   claim: ~+1.5–2 TIR on the generator, +3.4 on the additive sim. `runs/2026-10-30-reduction-gen/` (`spr.sh`,
   `r2/r2_run.py` arms sx_bh090/100, gr_pn095..125; jobs 57, 58), scored by `analysis/reduction/gen_score.py`. Engine: the run dir's `loop-eval-ec` (branch build before b06edb5e);
   reruns go through `scripts/gen/gen.py` with `arms.py` on frozen `~/frozen/a64013d`, which reproduces i090's scores
   exactly for gr_p0 and sx_bh090.
