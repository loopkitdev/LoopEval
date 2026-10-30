# CamAPS and unannounced meals: what it does, and what LoopEval has already tested

Verified 2026-10-25. Board: TIDEPOOL-95.

## What CamAPS does about meals the user doesn't count

| Feature | What it does | Evidence | Source |
|---|---|---|---|
| **CamAPS Liberty** (fully closed loop; CamAPS HX in the trials) | Same learning as FX: total daily need and time-of-day/hourly needs. What differs is an "accelerated response to changing glucose trends within the same safety limits". It starts more cautious while it learns, and the guide warns of larger post-meal rises in the first weeks. The personal glucose target is "the central optimisation tool"; a target above 120 mg/dL costs TIR. An optional meal bolus 10–15 min before eating remains available | manufacturer (HCP guide); internals not published | mylife Liberty HCP 5-step guide (DE, v03) |
| Liberty / HX outcomes | Adults with suboptimal control: TIR 50.0 vs 36.2 % on pump + CGM (ultra-rapid lispro). Adolescents: 45 vs 32 % (Fiasp). Type 2: 66 vs 32 %. Hypoglycaemia unchanged. About 30 % of adolescents were dissatisfied with the slow response to post-meal highs | RCTs, crossover | Boughton 2023 *Diabetes Care* 46:1916; Kadiyala 2025 *DTT* 27:719 (PMC7618673); Daly 2023 *Nat Med* (PMC9873557) |
| Missed bolus, head to head (**hybrid FX, not Liberty**) | Children, 30 / 50 g with no bolus: 4-h AUC 780G < Control-IQ < CamAPS. Level-2 hyperglycaemia 26 / 42 % on CamAPS vs 5 / 21 % on 780G | prospective, n = 43 | Santova 2026 *DTT*, doi:10.1177/15209156251415187 |
| Missed bolus, fully closed loop with ultra-rapid insulin | 60 g with no bolus: TIR over 8 h 49 % on ultra-rapid lispro vs ~40 % on standard lispro; not significant at n = 17 | RCT, crossover | PMC12434446 |
| **Simplified meal announcement (SMA)** | The user taps a meal-size icon instead of counting. Sizes are personalised from a 3-day carb record: regular = the usual meal, snack 25 %, small 50 %, large 150 %. TIR 69.9 vs 70.7 % with carb counting, difference −0.6 pp [−2.4, +1.1], non-inferior. Time < 54 lower (p = 0.046). Extended highs slightly more frequent. TDD +2.4 U/day, all from automation | RCT, crossover, 46 youth, 2 × 3 months | SMASH, *Diabetologia* 2025, PMC11732900 |
| Post-meal learning | Learns from bolused meals and adds insulin after meals that are persistently under-covered. SMASH credits it for why coarse announcement holds up | manufacturer + trial discussion | PMC11732900; mylife |
| Slowly absorbed meal | Insulin for the flagged carbs goes in over 3–4 h, given only while glucose rises | published (manual) | user manual §7 |

## Liberty's meal handling: everything public, 2026-10-25

- **Mechanism, as the makers describe it:**
  - a "more proactive version" of the FX algorithm that "predicts what is about to happen and
    increases or decreases insulin delivery early enough to respond";
  - an "accelerated response to changing glucose trends within the same safety limits" that are
    pre-set in the pump;
  - learning that is the same as FX (total daily need and time-of-day needs), and it "recognises
    insulin need depending on time of day";
  - the personal target as the main lever.

  No meal detection, no automatic meal bolus and no meal model is described anywhere.
- **Sources searched:**
  - mylife and CamDiab pages, the Liberty HCP guide, and the 2026-03 launch release;
  - Breakthrough T1D UK coverage;
  - every open-access Cambridge FCL paper (CLEAR adults and adolescents, type 2, inpatient,
    ultra-rapid missed-bolus);
  - Google Patents: CamDiab's only filing is GB202510447D0, filed 2025-06 and unpublished.
    Hovorka's granted patents cover the 2006–2009 core MPC and nothing on FCL.
- **Outcomes:**
  - Liberty itself: none published. About 1,200 early-access users since 2026-05; European launch
    2026-09-01.
  - HX trials: TIR +13–14 pp against pump + CGM in people with suboptimal control. These are not
    comparisons with hybrid mode or with other FCL systems.
  - User reports are informal: "more aggressive" than hybrid, corrects faster, copes better with
    hard-to-count meals.

## What LoopEval has already tested along these lines

- **Faster response to rising trends:**
  - UAM projection (C05), early-rise (C06), ICE rise-boost (C07): WORSE or patient-conditional.
  - Calm-high licence (C23/C25) and target shift (C31): IMPROVES in their gated forms.
  - Guard + runway is frozen and on its way into Loop.
  - E57 (additive, 896 people): C31(−30) + guard is the pairing for reduced entry, +0.70 / +1.00 TIR at half / no entry.
- **Time-of-day needs:** C12, a learned hourly schedule, is closed on every bed type, hands-off beds included. C39 `habrelr` (same-clock habit, applied only once a rise is under way) is about as close to "time-of-day-aware trend response" as a model-free form gets. It is NEUTRAL on the cohort and IMPROVES only on bddp05.
- **The target:** this is the needs dial; it is not a mechanism.
- **Coarse announcement: never tested.** E57 varied *how often* meals are entered (all / half / none). It never varied *how precisely* they are entered.

## Reading

- The evidence does not show CamAPS handling unannounced meals better than others. Its one
  head-to-head (hybrid mode, children) puts it last. Liberty's published difference, a faster
  trend response tied to learned time-of-day needs, maps onto mechanisms LoopEval has already
  scored.
- The CamAPS meal idea with the strongest evidence that LoopEval has not tested is **SMA**.
  An RCT found it non-inferior on TIR, with fewer severe lows. It sits between full counting and
  no entry: the user still marks the meal, but nobody counts.
