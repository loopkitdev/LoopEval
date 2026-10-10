# Unannounced meals in automated insulin delivery: literature review for Loop/oref (Oct 2026)

**Bottom line:** across controlled trials that compare the same system with and without meal announcement, skipping announcement costs about **2–10 percentage points (pp) of 24-hour time in range (TIR)**. The cost is much larger after the meal itself: **15–33 pp over 4–6 hours**. Your 60-minute oracle bound of about 10 pp sits at the top of what the clinical evidence shows. Two levers have the clearest evidence for a no-bolus population: aggressive automatic correction settings, and drug adjuncts. Meal-pattern priors and detection-triggered priming boluses have reached clinical trials, but neither has shown a significant 24-hour TIR gain.

Unless noted, figures come from abstracts I retrieved. I mark industry-sponsored and unverified items.

## 1. Fully closed-loop (FCL) systems and trials

### Same system, announced vs unannounced (the most useful comparisons)

| Study | System / insulin | Population | TIR announced (HCL) | TIR unannounced (FCL) | Gap |
|---|---|---|---|---|---|
| Shalit 2023 | MiniMed 780G, no meal detection; 90 days per phase at home | 14 adults | 77.7% | 67.5% | **−10.2 pp**. Time below 54 mg/dL fell (0.7% → 0.3%) |
| Garcia-Tirado 2023 (DCLP6) | UVA RocketAP | 35 adults, supervised 24 h | 86% | 77% (77% with meal anticipation) | **−9 pp** over 24 h. Post-breakfast 5 h: 75% vs 58% (63% with anticipation, not significant) |
| Wilkinson 2026 (CLOSE IT) | Open-source AID (AndroidAPS); 12-week randomised phase after a 12-week announced run-in | 73 adults | 69% | 66% | **−2.2 pp** adjusted (95% CI −6.2 to +1.7). Non-inferiority met |
| Petruzelkova 2023 (Pancreas4ALL) | AndroidAPS | 16 adolescents, camp, 3 days per mode | 83.3% | 81.0% | About −2 pp, not significant. Time below 54 mg/dL: 1.05% vs 0% |
| Schumacher 2026 | McGill AID, Lyumjev | 12 adults | 75.4% (carb counting) | 71.0% (72.9% with qualitative meal size) | −4.4 pp, not significant |
| Tsoukas 2021 | Fiasp + pramlintide FCL vs Fiasp HCL | 24 adults | 78.1% | 74.3% | −3.8 pp. Non-inferiority **not** met |
| Wilkinson 2025 | Tandem "Freedom" FCL vs own pump with boluses | 10 adults, hotel, high-carb/high-fat meals | 56.3% | 61.0% | Not significant. Overnight 95.9% vs 69.6% |

**Single-meal challenges** show the post-meal cost directly:
- Grassi 2026 (780G, about 60 g carbohydrate): 4-hour TIR was 85.5% with a pre-meal bolus, 52.3% with no bolus, and **63.5% with a 50% bolus given 60 minutes late**.
- Santova 2026 compared three systems in 43 children with no pre-meal bolus. 4-hour glucose area under the curve was lowest with 780G, then Control-IQ, then CamAPS. At 50 g, time in level-2 hyperglycaemia was 21% vs 26% vs 42%.
- Lo Presti 2026: the 780G (PID) beat Tandem (MPC) on unannounced breakfasts in adolescents.

### FCL vs usual care (no announced comparator)

- **CamAPS HX** (Cambridge FCL). In adults with suboptimal control (Boughton 2023, ultra-rapid lispro), TIR was 50.0% vs 36.2% on pump + CGM. In adolescents (Kadiyala 2025, Fiasp), 45.2% vs 32.3%. Hypoglycaemia was unchanged. These cohorts start very poorly controlled, so absolute TIR stays low.
- **Ultra-rapid lispro under FCL with a missed bolus** (Thabit 2025): 8-hour TIR 49.3% vs 39.9% (p=0.07). Insulin delivered was 10.7 vs 12.2 U.
- **UVA RocketAP** in adolescents (Garcia-Tirado 2021). In the 6 hours after an unannounced dinner, TIR was 83% vs 53% for the older UVA controller, with 0% time below range in both. A conference abstract suggests RocketAP's overall TIR was similar with or without a dinner bolus. That is unverified.
- **UVA AIDANET neural-network controller.** A 6-person pilot (Pryor 2025) gave 66.4% TIR vs 63.3% on usual care. In FCL@Home (Moscoso-Vasquez 2026, n=34, mostly prior HCL users), mean glucose fell from 178 to 164 mg/dL. The TIR gain was mainly overnight.
- **Bihormonal Inreda AP.** Blauw 2021: 86.6% vs 53.9% with no meal or exercise announcements. Adolescents (Booijink 2026): 74.9% vs 61.3%.
- **Cameron/Bequette multiple-model probabilistic controller (MMPPC)** (Cameron 2017; Forlenza 2018): 63.6% TIR and 2.9% below 70 mg/dL. Hyperglycaemia was common within 3 hours of meals. The authors concluded that FCL carries more hypoglycaemia risk than announced control.
- **iLet bionic pancreas** (Russell 2022, NEJM). The trial used qualitative meal announcements only and gave +11 pp TIR vs usual care. **I could not find a published no-announcement vs announcement comparison for the iLet.** In a cystic fibrosis trial, users announced only about 2.2 meals per day and still did well. The early bihormonal bionic pancreas gave fixed partial meal-priming boluses of 0.035–0.05 U/kg (Russell 2012).
- **Open-source FCL beyond CLOSE IT** is anecdotal:
  - a pig study where AndroidAPS/oref1 beat Loop on unannounced meals (Lal 2021);
  - an n=1 case report of Lyumjev with oref1 UAM (Diabettech);
  - a review of the open-source evidence (Lal, Braune, Lewis, de Bock et al., Diabetologia 2026).
  
  I could not verify CLOSE IT's exact settings, though SMB and UAM are presumably enabled. Its protocol is in BMJ Open 2024.

## 2. Meal detection algorithms

| Method | Delay | Accuracy | How detection becomes a dose |
|---|---|---|---|
| Dassau 2008, Diabetes Care (voting on CGM derivatives) | Mean 30 min. Glucose 21 mg/dL above baseline at detection; >90% of meals caught before a 40 mg/dL rise | — | Not tested |
| Harvey 2014 GRID (glucose rate increase detector, UCSB) | — | — | Fixed 75 g-equivalent bolus at detection, optionally reduced by recent insulin and glucose. In silico: +17% time in 80–180 mg/dL, with no rise in late post-meal hypoglycaemia |
| Turksoy 2016 / Samadi 2018 (Cinar group; model-state filter, fuzzy logic) | Glucose about 16 mg/dL above baseline at detection; about 35 ± 23 min (machine-learning abstract) | Meals 93.5%, snacks 68%; **20.8% of detections false** | Carbohydrate estimate × carb ratio, then adjusted for activity, sleep and hypo risk |
| Ramkissoon 2018 (Herrero/Bondia/Vehí) | — | Sensitivity 99%, 93% or 47% depending on tuning | Explicit sensitivity vs false-positive trade-off |
| Mahmoudi et al. (filter-based) | Median about 40 min (secondary citation, unverified) | 93% | — |
| Kölle 2020 (pattern recognition, no per-person tuning) | Earlier than threshold methods | Better at low false-alarm rates | Retrospective only; no numbers in abstract |
| Zheng/Kleinberg 2019 (JAMIA; simulation-based) | 25.7 min (vs 48.3 min for prior work) | 1.2 g carb error | Not dosed |
| Mosquera-Lopez/Jacobs 2023 (OHSU neural net, clinical) | 25.9 min | Sensitivity 83.3%; false discovery 16.6% | Neural network recommends a meal dose. Time >180 mg/dL −10.8 pp (p=0.04); TIR +9.1 pp (not significant) |

**Systematic review** (Ibrahim/Vehí 2026, 69 studies): median sensitivity 88%, precision 93%, detection at 25–40 minutes. In-silico studies report more false positives than clinical ones.

**UVA Bolus Priming System** (Moscoso-Vasquez 2025, n=11). It gives a fixed dose scaled by the probability that a meal has occurred, capped at about 6% of total daily insulin per meal (from the protocol). Results:
- Overall TIR 70.6% vs 65.7% (not significant).
- It fired for 24 of 43 eligible meals.
- When it fired, post-meal glucose area was lower (2530 vs 3228, p=0.047). 4-hour TIR was 51.2% vs 40.2% (not significant).
- No hypoglycaemia in either arm.

**How detection is turned into insulin across the literature:**
- a fixed partial priming bolus (bionic pancreas, BPS);
- a bolus from an estimated carbohydrate amount (Samadi, RAP);
- raised aggressiveness: oref1 UAM/SMB extrapolates the rise and front-loads insulin, and RocketAP's controller does something similar.

None has shown a significant 24-hour TIR gain over a strong baseline controller.

## 3. Meal-pattern priors and habit learning

- **Hughes, Patek, Breton & Kovatchev 2011:** a controller that anticipates the next meal from personal meal behaviour profiles. In silico only, qualitative results.
- **Corbett 2022 (UVA, in silico):** a controller that clusters past days, plus BPS. Post-meal TIR: plain controller 51.8%, + BPS 57.0%, + history clusters 54.8%, both combined 60.7%. Time below 70 mg/dL stayed under 0.5%. The two effects roughly add.
- **DCLP6 clinical test (Garcia-Tirado 2023):** anticipation did **not** significantly improve post-meal TIR (63% vs 58% after breakfast). When dinner was eaten 1.5 hours late, it **did not raise hypoglycaemia** and lowered post-dinner time below range (p=0.03). The prior is safe, but on its own its benefit is unproven.
- **Run-to-run adaptation** (Toffanin 2018, in silico): +11 pp TIR after about 2 months.
- **Adaptive biobehavioral control (Kovatchev group):**
  - Colmegna 2024 pilot: TIR not significantly different (74.6% vs 73.8%).
  - Kovatchev 2025 (npj Digital Medicine, n=72, 6 months): settings co-adapted on a digital twin raised TIR from 72% to 77%. Feedback to users added nothing.
- The MMPPC uses a time-of-day meal probability while the person is awake. I did not verify the details.

## 4. Adjuncts that shrink the meal problem

- **Faster insulins.** Ultra-rapid lispro under FCL: +9.4 pp (not significant, Thabit 2025). In HCL: +2.5 pp. In silico, making insulin 2–3× faster raised unannounced post-meal TIR from about 80% to 89–94% (Colmegna 2021). So an insulin much faster than today's would matter a lot. Fiasp and Lyumjev are only modestly faster.
- **Inhaled insulin (Technosphere/Afrezza).**
  - Zisser/Dassau ran a zone-MPC trial with a fixed 10 U inhaled pre-meal dose (2015, JDST). I could not retrieve its outcome numbers.
  - INHALE-1 in youth (2026) showed smaller post-meal excursions, but more hypoglycaemia in the paediatric arm (6% vs 2%).
  - Cengiz & Beck (DTT 2026) review inhaled insulin used alongside AID.
- **Pramlintide co-formulation (Haidar group).** Fiasp + pramlintide FCL came within about 4 pp of HCL (Tsoukas 2021), with nausea in 13%. In 2025 pilots, FCL with pramlintide at 10 µg/U reached 77–79% TIR, about matching carb counting. Haidar also had a Lyumjev + pramlintide FCL trial registered (NCT06046417); I could not confirm its status.
- **GLP-1 receptor agonists.**
  - Pasqua 2025 (Nature Medicine): +4.8 pp TIR.
  - ADJUST-T1D (NEJM Evidence 2025): about +8.8 pp TIR. Total insulin fell 23%, mostly bolus (bolus −31%, basal −16%) per the post-hoc analysis.
  - Two episodes of euglycaemic ketosis occurred with semaglutide.
  
  GLP-1s blunt meals specifically, which suits unannounced dosing.
- **SGLT2 inhibitors** (empagliflozin with HCL, Pasqua 2023): about +12 pp TIR. Ketoacidosis risk needs managing.
- **Glucagon / bihormonal.** Inreda FCL reaches 75–87% TIR. Glucagon mainly works as a hypoglycaemia safety net (Castle 2010), which is exactly what allows aggressive meal dosing.

## 5. Safety: post-meal hypoglycaemia and pull-back

- **Insulin feedback** (Steil 2011; Ruiz 2012): hypoglycaemic events fell from 8 to 0, but mean glucose rose (133 → 153 mg/dL).
- **Insulin-on-board (IOB) constraints in MPC** (Ellingsen 2009): simulated runs with hypoglycaemia fell from 50% to 10%.
- **Caps on detection-triggered doses:** BPS caps each priming dose at about 6% of total daily insulin. Glucose-rate-increase-detector doses shrink according to recent insulin.
- **Cost of aggressive FCL:**
  - The MMPPC reported more hypoglycaemia than announced systems.
  - The open-source review flags the hard problems: quickly cutting insulin as glucose plateaus, CGM artefacts, and exercise after a front-loaded dose.
  - Paediatric AndroidAPS users in a registry had 5% time below range vs 2–3% on commercial systems (Santova 2023), though TIR was higher.
- **Counter-evidence:** several trials found *less* hypoglycaemia without announcement (Shalit; Pancreas4ALL; DCLP6 with anticipation). Over-sized user boluses cause many lows. A well-capped automatic response can be safer than human dosing.

## 6. Real-world bolus behaviour and its cost

- **Laugesen 2024** (DTT; Control-IQ and 780G, 189 young people): on average **2.2 missed or late meal boluses per day**. Each extra one per day cost **−9.7 pp TIR**. The worst quartile had 22.9 pp less TIR than the best.
- **Tandem real-world data** (Polin/Messer, ADA 2024 poster; industry): **about 10% of 291,769 Control-IQ users** had stretches of 7+ days with no boluses, averaging 61 such days. Median TIR was 62% on no-bolus days vs 57–60% on bolus days. This is likely reverse-causal: people bolus more on bad days. In simulation, Control-IQ reached about 62% TIR if users skipped boluses only for meals up to 40 g.
- **Medtronic real-world data** (Niu 2026, Diabetes Care; industry): **about 15% of 369,467 780G users** had 10 or more no-bolus days. On those days, users with a **100 mg/dL target and 2-hour active insulin time** reached **76.3% TIR** vs 69.3% for others. Time below range was 0.8–0.9% in both. **Changing settings alone was worth about 7 pp**, as much as most algorithm changes.
- **Youth trajectories** (Hooven-Davis 2026, n=713): fewer user-initiated boluses predicted membership in the lowest-TIR group (odds ratio 2.46).
- **Children on HCL** (Coutant 2023): days with at least one missed bolus rose from 12% to 22% over 72 weeks.
- **Loop observational study** (Lum 2021, n=558): TIR rose from 67% to 73%. The abstract does not break this down by bolus behaviour.

## Quantitative bounds: FCL vs HCL

1. **24-hour TIR penalty for not announcing**, from controlled comparisons of the same system:
   - 9–10 pp for MPC/PID systems without strong unannounced-meal logic (780G, Shalit 2023; RocketAP in DCLP6);
   - **2–4 pp for systems built for it**: open-source AID with oref-style SMB/UAM (CLOSE IT, Pancreas4ALL), and pramlintide or Lyumjev FCL (Haidar group).
   
   Those small gaps come from cohorts whose HCL TIR was only about 70%. Users who announce well lose more.
2. **Post-meal penalty** over 4–6 hours: 15–33 pp. A late 50% bolus at 60 minutes recovers about a third of it (Grassi 2026).
3. **Ceiling of today's detect-and-dose add-ons on a good controller:** about +5 pp TIR, not significant in trials (BPS, meal anticipation, RAP), with no extra hypoglycaemia.
4. **Bounds outside the algorithm:**
   - optimised settings for non-bolusers: about +7 pp (observational);
   - GLP-1: +5 to +9 pp;
   - digital-twin settings co-adaptation: +5 pp;
   - SGLT2: about +12 pp in poorly controlled users.

All of this is consistent with your findings. The algorithm headroom is about 10 pp at most, and meal-announcement behaviour dominates.

## Most promising unexplored or under-tested ideas

1. **Set aggressiveness from each user's announcement behaviour.** Estimate a user's meal-announcement rate from history. For habitual non-announcers, automatically tighten target, active insulin time and partial-application settings, the analogue of Medtronic's 100 mg/dL / 2-hour recommendation. No trial has done this adaptively.
2. **Handle late announcements as a first-class case.** A late partial bolus still recovers a lot. Credit the insulin the system has already delivered automatically, then dose the remainder. Pair this with CGM-triggered missed-meal prompts (Loop's missed-meal notification; I did not re-verify its documentation).
3. **Pull back by situation class.** Learn which classes of state end in lows, for example a falling trend after an automatic correction, or an evening after exercise. Apply IOB caps only there. The aim is to reallocate safety margin rather than add a global brake. Ellingsen and the insulin-feedback studies show global brakes cost mean glucose.
4. **Combine priors with probability-scaled priming.** Corbett's simulation shows the two effects add. Clinically, each alone was safe but not significant. No adequately powered combined trial exists.
5. **Detect meals from non-CGM signals.** Wrist-gesture detection (Klue) and similar signals could beat CGM's 25–40 minute delay. That delay is the main limit, as faster-insulin simulations show.
6. **Exploit drug adjuncts in the algorithm.** If a user is on a GLP-1 or pramlintide, deliberately retune meal-response aggressiveness; no system does this yet.

## References

- Shalit R, …, Tirosh A. *Diabetes Technol Ther* 2023;25:579. doi:10.1089/dia.2023.0139
- Garcia-Tirado J, …, Breton MD. *Diabetes Care* 2023;46:1652. doi:10.2337/dc23-0119
- Garcia-Tirado J, et al. *Diabetes Care* 2021. doi:10.2337/dc21-0932
- Wilkinson T, …, Cohen ND. CLOSE IT. *Diabetes Technol Ther* 2026;28:941. doi:10.1177/15209156261423558
- Petruzelkova L, …, Sumnik Z. Pancreas4ALL. *Diabetes Technol Ther* 2023;25(5). doi:10.1089/dia.2022.0562
- Lal R, Braune K, Lewis DM, et al. *Diabetologia* 2026. doi:10.1007/s00125-025-06644-8
- Schumacher C, …, Haidar A. *Diabetes Technol Ther* 2026. doi:10.1177/15209156261456440
- Tsoukas MA, …, Haidar A. *Lancet Digit Health* 2021;3:e723. doi:10.1016/S2589-7500(21)00139-4
- Odabassian M, …, Haidar A. *J Diabetes Sci Technol* 2025;19:1457. doi:10.1177/19322968251371046
- Wilkinson TM, …, Pinsker JE. *J Diabetes Sci Technol* 2025. doi:10.1177/19322968251389966
- Boughton CK, …, Hovorka R. *Diabetes Care* 2023;46:1916. doi:10.2337/dc23-0728
- Kadiyala N, …, Hovorka R. *Diabetes Technol Ther* 2025;27:719. doi:10.1089/dia.2025.0062
- Thabit H, …, Leelarathna L. *Diabet Med* 2025. doi:10.1111/dme.70122
- Moscoso-Vasquez M, et al. FCL@Home. *Diabetes Care* 2026;49:401. doi:10.2337/dc25-1526
- Moscoso-Vasquez M, …, Breton MD. *Diabetes Technol Ther* 2025;27:93. doi:10.1089/dia.2024.0315
- Pryor EC, …, Breton MD. *J Diabetes Sci Technol* 2025. doi:10.1177/19322968251364283
- Corbett JP, …, Breton MD. *J Diabetes Sci Technol* 2022;16:52. doi:10.1177/19322968211059159
- Colmegna P, et al. *J Diabetes Sci Technol* 2021. doi:10.1177/1932296820928067
- Blauw H, …, DeVries JH. *Diabetes Care* 2021. doi:10.2337/dc20-2106
- Booijink RS, …, van Bon AC. *Pediatr Diabetes* 2026. doi:10.48130/pedi-0026-0009
- Russell SJ, et al. *N Engl J Med* 2022. doi:10.1056/NEJMoa2205225
- Russell SJ, et al. *Diabetes Care* 2012. doi:10.2337/dc12-0071
- Cameron FM, …, Bequette BW. *Diabetes Technol Ther* 2017;19:527. doi:10.1089/dia.2017.0078
- Forlenza GP, et al. *Diabetes Technol Ther* 2018;20:335
- Dassau E, Bequette BW, Buckingham BA, Doyle FJ. *Diabetes Care* 2008;31:295. doi:10.2337/dc07-1293
- Harvey RA, Dassau E, Zisser H, Seborg DE, Doyle FJ. *J Diabetes Sci Technol* 2014;8:307. doi:10.1177/1932296814523881
- Samadi S, …, Cinar A. *Diabetes Technol Ther* 2018;20:235. doi:10.1089/dia.2017.0364
- Turksoy K, et al. *IEEE J Biomed Health Inform* (meal detection module; PMC4713125)
- Ramkissoon CM, Herrero P, Bondia J, Vehí J. *Sensors* 2018;18:884. doi:10.3390/s18030884
- Kölle K, …, Stavdahl Ø. *IEEE J Biomed Health Inform* 2020;24:594. doi:10.1109/JBHI.2019.2908897
- Zheng M, Ni B, Kleinberg S. *JAMIA* 2019;26:1592. doi:10.1093/jamia/ocz159
- Mosquera-Lopez C, …, Jacobs PG. *npj Digit Med* 2023;6:39. doi:10.1038/s41746-023-00783-1
- Ibrahim M, Beneyto A, Contreras I, Vehí J. *PLOS Digit Health* 2026;5(7). doi:10.1371/journal.pdig.0001492
- Hughes CS, Patek SD, Breton M, Kovatchev BP. *Comput Methods Programs Biomed* 2011;102:138. doi:10.1016/j.cmpb.2010.04.011
- Toffanin C, et al. *IEEE Trans Biomed Eng* 2018;65:479. doi:10.1109/tbme.2017.2652062
- Colmegna P, …, Kovatchev B. *Diabetes Technol Ther* 2024;26:644. doi:10.1089/dia.2023.0399
- Kovatchev BP, et al. *npj Digit Med* 2025;8:253. doi:10.1038/s41746-025-01679-y
- Ellingsen C, et al. *J Diabetes Sci Technol* 2009;3:536. doi:10.1177/193229680900300319
- Ruiz JL, et al. *J Diabetes Sci Technol* 2012;6:1123
- Steil GM, et al. *J Clin Endocrinol Metab* 2011;96:1402
- Castle JR, et al. *Diabetes Care* 2010. doi:10.2337/dc09-2254
- Laugesen C, et al. *Diabetes Technol Ther* 2024;26:897
- Niu F, …, McVean JJF. *Diabetes Care* 2026;49:419. doi:10.2337/dc25-2124 (industry)
- Polin MR, et al. ADA 2024 poster; *EMJ* 2024. doi:10.33590/emj/OUZU9513 (industry)
- Grassi BA, et al. *Diabetes Technol Ther* 2026. doi:10.1177/15209156251395010
- Santova A, et al. *Diabetes Technol Ther* 2026. doi:10.1177/15209156251415187
- Santova A, et al. *Front Endocrinol* 2023. doi:10.3389/fendo.2023.1283181
- Lo Presti D, et al. *Endocrine* 2026. doi:10.1007/s12020-026-04705-5
- Hooven-Davis J, et al. *Diabetes Care* 2026. doi:10.2337/dc26-0634
- Coutant R, …, Renard E. *Diabetes Technol Ther* 2023;25:395. doi:10.1089/dia.2022.0518
- Lum JW, et al. *Diabetes Technol Ther* 2021;23:367. doi:10.1089/dia.2020.0535
- Pasqua MR, et al. *Nat Med* 2025 (semaglutide with AID)
- ADJUST-T1D. *NEJM Evidence* 2025
- Karakus KE, et al. *Diabetes Care* 2026. doi:10.2337/dc25-2249
- Pasqua MR, …, Haidar A. *Diabetes Care* 2023. doi:10.2337/dc22-0490 (empagliflozin)
- Zisser H, Dassau E, et al. *J Diabetes Sci Technol* 2015 (PMID 25901023; outcome numbers not retrieved)
- Ekhlaspour L, et al. INHALE-1. *Diabetes Technol Ther* 2026. doi:10.1177/15209156261432138
- Lal RA, et al. *Clin Transl Med* 2021. doi:10.1002/ctm2.387 (pig study)

## What I could not verify

- Any iLet trial comparing no announcement with announcement.
- Outcome numbers for the Zisser Afrezza closed-loop trial.
- CLOSE IT's exact AndroidAPS settings (SMB, UAM, dynamic ISF, insulin type).
- The Mahmoudi detector's latency figure (secondary citation only).
- Details of the MMPPC meal-time prior.
- Loop's missed-meal notification documentation.
- RocketAP's overall TIR with vs without a dinner bolus (ATTD 2021 abstract only).

The Medtronic and Tandem real-world analyses are industry-authored and observational.