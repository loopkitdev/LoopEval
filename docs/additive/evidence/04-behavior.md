# 04 — Patient behaviour: evidence for the "second controller"

The simulated person is a second controller running alongside the AID algorithm. Each behaviour
below is a **per-person trait** (drawn once per virtual person from a between-person
distribution) plus **within-person noise** (drawn per event). Values are given as found in the
source; anything derived by us is labelled *derived*, and anything not checked against the
source text is marked **[unverified]**. "Checked" here means checked against the PubMed
abstract, or PMC full text where stated. It does not mean the full paper was read.

## Summary table

| Behaviour | Trait parameter(s) | Population value / distribution | Between-person spread | Ref |
|---|---|---|---|---|
| Eating events / day | `n_meals` (3 main) + `snack_rate` | 17,111 eating events / 4,874 days ≈ **3.5/day** (*derived*); 3 main meals; ≥1 snack on 71% of days; snack in ~12% of 3-h windows | Snack timing has "much more inter- and intra-subject variability" than main meals (not quantified) | Camerlingo 2021 (PMC full text) |
| Meal clock time | `t_breakfast`, `gap_BL`, `gap_LD` | Breakfast lognormal(μ 2.078, σ 0.175), median ≈ **08:00** (*derived*); breakfast→lunch GEV(μ 282.9, σ 79.98, ξ −0.32) min ≈ 4.7 h; lunch→dinner GEV(μ 374.9, σ 84.86, ξ −0.47) min ≈ 6.2 h | Fitted per subject, then pooled | Camerlingo 2021 |
| Carbs per meal | `cho_B/L/D/S` scale | Breakfast gamma(5.29, 7.70) mean ≈ 41 g; lunch lognormal(3.884, 0.518) median ≈ 49 g; dinner loglogistic median ≈ 53 g; snack gamma(2.06, 11.88) mean ≈ 25 g (*derived*). Observed medians: B 36, L 50, D 50 g; **190 g CHO/day** [IQR 159–231] | Brazeau's adults ate 72.4 ± 34.7 g/meal | Camerlingo 2021; Brazeau 2013 |
| Diet type (low-carb) | `diet_cho_scale` | VLCD community: **36 ± 15 g/day** | Mixture: most people near 190 g/day, a minority below 50 g/day | Lennerz 2018 |
| Meal announced / bolused | `p_bolus_meal`, `p_bolus_snack` | Adolescents: 38% missed >15% of the previous day's boluses. MDI pen adults: 25% → 14% of main meals missed. Children on HCL: days with ≥1 missed meal bolus **12% → 22%** over 72 weeks. Unbolused afternoon snacks: 94/195 (48%) in 9 youth | Strongly person-specific; missers bolus 3.8 vs 5.3 times/day | Olinder 2009; Adolfsson 2020; Coutant 2023; VanderWel 2010 |
| Low-bolus / near-"fully closed" users | `user_bolus_rate` | 24% of AID youth average ≤3 boluses/day (2.2 user-initiated/day). ~10% of Control-IQ users had a ≥7-day run with no user bolus | Heavy right tail | Chatty 2026; Polin 2024 (conference) [unverified] |
| Bolus timing | `bolus_offset` (min relative to meal) | Youth: 21% several minutes before, 44% immediately before, 10% during, 24% after. All ages: **32% during/after** | Categorical trait; post-meal dosers are younger and miss more doses (28% vs 14% miss ≥1/week) | Datye 2018; Peters 2017 |
| Carb-count error | `cho_bias`, `cho_sd` | Adults: mean error **15.4 ± 7.8 g = 20.9 ± 9.7%** per meal; **63% of meals under-estimated**. Youth: 67% of meals within 20%; 73% of estimates within 10–15 g | ±9.7% SD of the per-person error. Large meals are under-estimated and snacks over-estimated | Brazeau 2013; Deeb 2017; Smart 2010 |
| Bolus-calculator use | `p_accept`, `p_up`, `p_down`, `p_no_calc` | 85.7% accepted, 7.4% larger, 6.9% smaller, 13.0% given without the calculator; carbs entered for 66.6% of boluses | Acceptance 49–100% across people; no-calculator 0–53% | Groat 2017 (PMC full text) |
| Hypo treatment amount | `ht_grams` | **32 ± 24 g**; 73% of people over-treat (>20 g within 15 min). Guideline: 15–20 g | Over-treaters are younger and more fearful of hypoglycaemia | Savard 2016; ADA 2024 |
| Hypo treatment latency | `ht_delay` | 64% of episodes treated within 15 min | — | Savard 2016 |
| Repeat treatment | `ht_recheck`, `ht_repeat` | 16 g resolved only 38% of episodes at 15 min. A second dose was needed in 50% (16 g) vs 15% (32 g) at 3.0–3.5 mmol/L | — | Gingras 2018; Taleb 2023 |
| Post-hypo rebound | (emergent) | AID users: **2.08 ± 1.49 rebound events/week**; 39.6 ± 20.1% of lows lead to >180 within 2 h | SD ≈ ½ mean | Tidemand 2025 |
| Alert thresholds | `low_alert`, `high_alert`, `uls_on` | Low alert mean **74–78.5 mg/dL** (SD ~8–9) by age; high alert **218–266 mg/dL**; predictive Urgent-Low-Soon (≤55 within 20 min) on for 89.5–93% of users | Thresholds higher in the youngest and oldest users | Akturk 2021 (PMC); Puhr 2020 |
| Night alarm response | `p_wake_alarm` | Children: woke to **29% of alarms, 66% of alarm events**; ages 4–6: 17%, 7–11: 20%, adolescents: 53%, parents: 37%; 40% for the first alarm of the night vs 28% after | Age-driven | Buckingham 2005 |
| Waking from the low itself | `p_wake_hypo` | **1/16 T1D vs 10/16 controls** woke at 2.2 mmol/L without an alarm | — | Schultes 2007 |
| Hypo awareness | `aware` | Impaired awareness in 23.4% of adults; asymptomatic lows are 47% of all <3.0 readings with impaired awareness vs 14% with normal awareness | Binary trait | Ogundipe 2011; Schopman 2011 |
| Monitoring (glances) | `glances_per_day` | Dexcom G6 app trend-screen views (5-min de-dup): bottom quartile <3.30/day, top quartile >8.25/day. Libre scans: mean 16.3/day, median 14 [10–20] | Lognormal across people (*our choice*) | Puhr 2020 (PMC); Dunn 2018 |
| Correction boluses | `corr_hazard(CGM, ΔCGM, t_since_bolus, tod)` | Decision-tree model of post-meal correction timing (196 adults); accuracy 0.79, sensitivity 0.43 | — | Camerlingo 2022 |
| Exercise | `ex_rate`, `ex_type`, `ex_strategy` | Glucose change during a session: aerobic −18 ± 39, interval −14 ± 32, resistance −9 ± 36 mg/dL. Exercise nights: level-1 nocturnal hypo 15.6% vs 13.1% | — | Riddell 2023 (T1DEXI); Bisno 2026 |
| Infusion-set change | `set_wear_days` | Standard sets: labelled 2–3 days, real-world wear 3.6 ± 1.1 days; 7-day sets: 6.1 ± 2.3 days | — | Susuł 2026; Nieto de la Marca 2026 |
| AID engagement | `p_closed_loop` | Control-IQ median time in automation 94.2% [90.1–96.4]; Loop ≥83% [73–88]; 670G youth Auto Mode 65% → 51% at 6 months, 30% discontinued | — | Breton 2021; Lum 2021; Berget 2020; Messer 2020 |

---

## 1. Meals

**Existing generators.**
- **T1D Patient Decision Simulator (T1D-PDS)** (Vettoretti 2018). Connects UVA/Padova with SMBG/CGM, patient-decision and insulin modules. Validated on 44 subjects: simulated vs real TIR 63.6 vs 61.75%, hypo 2.14 vs 3.17%.
- **Camerlingo 2021** replaced the T1D-PDS meal module with distributions fitted to 32 adults (SAP/AP, 4,874 days, 17,111 meals). Parameters are in the summary table, taken from PMC Table 3. The real and simulated meal distributions were not statistically different.
  - Snack occurrence is predicted by an SVM over 3-h windows: 12.2% of windows contain a snack, test AUROC 0.754.
  - Weekday/weekend is **not modelled**; the authors list it as future work.
  - An erratum exists (doi:10.1177/1932296821996137). We did not check whether it changes Table 3 **[unverified]**.
- **UVA/Padova single-day** (Visentin 2018) adds intraday insulin-sensitivity variability and the dawn phenomenon. It is a physiology upgrade and does not generate behaviour.
- **ReplayBG** (Cappon 2023) replays recorded meals and insulin through a personalised model. It is a counterfactual method, not a behaviour generator; the closest analogue to LoopEval's replay.
- **"Tidepool TRSET"**: no publication or public document found under that name **[unverified — ask for the source]**.

**Distributions (adults, free-living).**
- Medians: breakfast 36 g, lunch 50 g, dinner 50 g; total **190 g CHO/day** [IQR 159–231].
- Meal-to-meal gap: median 190 min [125–250].
- Brazeau's adults ate a larger 72.4 ± 34.7 g/meal (dietitian-assessed, 448 meals). Meal size depends on the cohort.

**Between-person diet differences.**
- A very-low-carb community (online, self-selected; Lennerz 2018) reported **36 ± 15 g/day** with HbA1c 5.67%.
- Adults with T1D eat less carbohydrate and more fat than controls (Snell-Bergeon 2009).
- 36.6% of FinnDiane adults follow some special diet (Ahola 2018). The abstract does not quantify low-carb.
- **Modelling:** a per-person `diet_cho_scale` drawn from a mixture: most people ~1.0, plus a low-carb component (≈0.2 of the 190 g reference). We did not find the weight of that component.

**Day-to-day variability.** None of the checked sources partitions meal-size variance into within-person and between-person parts. **Modelling choice (ours):** draw the person's median per meal slot from the population distribution, then draw each meal from a lognormal with within-person CV ≈ 0.3–0.4. This is an assumption to calibrate against the donor pool.

**Weekday/weekend.** No checked source; a gap. Fit it from the donor data rather than the literature.

## 2. Meal announcement and bolusing

**Missed boluses.**

Before AID:
- 38% of Swedish adolescents on CSII missed >15% of the previous day's boluses (Olinder 2009). Those who missed doses bolused 3.8 vs 5.3 times/day and checked SMBG 2.4 vs 3.6 times/day. HbA1c values are given inconsistently between the abstract and secondary sources, so don't use them.
- In US youth, missing ≥1 meal bolus per week was associated with HbA1c 8.8% vs 8.0% (Burdick 2004). The often-quoted "65% miss ≥1/week" figure is from a secondary source **[unverified]**.
- MDI adults with a connected pen: missed main-meal boluses fell from 25% to 14% (Adolfsson 2020; assumes 3 meals/day).
- Missed and mistimed doses are widespread; 20–45% of people report mistiming (Robinson 2021, review).

On AID:
- In children on HCL, days with ≥1 missed meal bolus *rose* from 12% to 22% over 72 weeks (Coutant 2023). HCL recovered 15–17 TIR points relative to SAP on missed-bolus days.
- 24% of youth on Control-IQ/Omnipod 5 average ≤3 boluses/day, with 2.2 user-initiated boluses/day (Chatty 2026).
- Tandem t:connect (n = 291,769): ~10% of users had ≥7 consecutive days without a user bolus (Polin, ADA 2024; secondary write-up only) **[unverified]**.

Effect of a missed bolus under AID: on 780G, a 60 g meal with no bolus gave 4-h TIR 52% vs 86% with a pre-meal bolus; a late 50% bolus at +60 min gave 64% (Grassi 2026).

**Modelling:** a per-person Bernoulli `p_bolus_meal` (lower for snacks). Make it a hazard that rises with age into adolescence and falls with AID tenure, plus a separate "unannounced" persona with `p_bolus_meal` ≈ 0.

**Timing.** In the T1D Exchange registry (n = 21,533), 32% dose during or after the meal (Peters 2017). Youth <26 y (Datye 2018): 21% several minutes before, 44% immediately before, 10% during, 24% after. The optimum is 15–20 min before the meal (Cobry 2010; Slattery 2018).

**Modelling:** a categorical per-person trait with offsets of about −15 / 0 / +10 / +30 min (*our mapping of the categories to minutes*) and within-person jitter. Real-world minute-level distributions of pre-bolus time were not found; fit them from the data.

**Carb-counting error.**
- Adults: 15.4 ± 7.8 g (20.9 ± 9.7%) per meal, 63% under-estimated (Brazeau 2013).
- Youth on pumps: 67% of meals within 20% of the dietitian count. Under-estimated meals were mostly followed by highs (55/63) and over-estimated meals often by lows (12/19). Accuracy did not depend on meal size (Deeb 2017).
- Children and caregivers: 73% of estimates within 10–15 g. Large meals were under-estimated and snacks over-estimated; error *grew* with years of counting (Smart 2010).
- A ±10 g error around 60 g did not change post-prandial glucose (Smart 2009). This is the origin of the "±10 g tolerance".
- Dietitians estimating from photos: mean absolute error 14.9 ± 10.1 g, growing with meal size (Vasiloglou 2018).
- In the T1D-PDS sensitivity analysis, *systematic* (SI 2.05%) and *random* (1.35%) carb error were the top two behavioural drivers of time below range; bolus timing ranked fourth (1.09%) (Roversi 2024).

**Modelling:** `entered = true × exp(b_person + ε)`.
- Person bias `b_person` ~ N(−0.10, 0.10): mean under-estimation, from Brazeau's 63% under-estimated. The −0.10 is *derived*.
- Per-meal noise ε ~ N(0, 0.2): from |error| ≈ 21%, *derived*.
- Optional shrinkage toward the person's usual meal size, to reproduce "large under, small over" (Smart 2010).

**Rounding.** No checked source. Model entries rounded to 5 g (adults) and to the pump bolus increment **[assumption]**.

**Overriding the calculator.** In 19 adult Medtronic pump users (Groat 2017, PMC full text):
- 85.7% of boluses accepted as suggested, 7.4% larger, 6.9% smaller; 13.0% given without consulting the calculator.
- Carbs were entered for 66.6% of boluses.
- Between-person range: acceptance 49–100%, no-calculator 0–53%. Eight people accepted >90%.

**Modelling:** per-person Dirichlet over {accept, scale up, scale down, manual}, with scale factor ~ lognormal. This matches the project's "user-scaled" bolus ratio.

## 3. Hypoglycaemia treatment

**Amount.**
- Guideline: 15–20 g glucose at <70 mg/dL, recheck at 15 min (ADA 2024).
- Real world (121 adults, 2-day logs; Savard 2016): **32 ± 24 g**; 73% over-treated (>20 g within 15 min); juice or sweet drinks 39%, mixed snacks 29%. Over-treaters were younger and more afraid of hypoglycaemia.
- The guideline amount often fails:
  - 16 g raised glucose by only 0.85 mmol/L in 15 min and resolved 38% of episodes (pump users; Gingras 2018).
  - At 3.0–3.5 mmol/L, 32 g needed a second dose in 15% of episodes vs 50% for 16 g (Taleb 2023).
  - A weight-based 0.3 g/kg dose resolved more episodes than the usual 15 g (adults) or 10 g (children) (McTavish 2018).
- **Modelling:** `ht_grams` per person ~ lognormal with population mean ~30 g and wide spread (CV ~0.75 from 32 ± 24), plus small within-person noise. Children: about 10 g or 0.3 g/kg.

**Threshold, delay, repeats.**
- 64% of episodes were treated within 15 min (Savard 2016).
- Low-alert settings average 74–78.5 mg/dL; this is where an *alerted* person is prompted.
- No checked source gives the CGM value at which people actually eat, or a minute-level delay distribution. That is a gap for donor-data fitting.
- Repeat rule: recheck after ~15 min; re-treat if still <70. Repeats are frequent (above).

**Proactive treatment of predicted lows.**
- The Dexcom Urgent-Low-Soon alert (forecast ≤55 mg/dL within 20 min) is enabled by >93% of G6 users. It is associated with less time <55 regardless of how often people look (Puhr 2020).
- In simulation, CGM-triggered "dynamic-risk" pre-emptive treatment cut time in hypo from 41 to 25 min with noisy CGM, and rebound peak from 174 to 137 mg/dL (Camerlingo 2019).
- **Modelling:** a per-person `anticipation` trait that sets treatment on predicted rather than current glucose (horizon 0–20 min).

**Rebound.** AID users have 2.08 rebound events per week; ~40% of lows are followed by >180 within 2 h. AID rebounds are shorter than MDI ones (122 vs 185 min) (Tidemand 2025). Use this as a validation target for the combined treatment-size and counter-regulation model.

**Nocturnal response.**
- Children with GlucoWatch alarms (video-verified; Buckingham 2005) woke to 29% of individual alarms and 66% of alarm events.
  - By age: 4–6 y 17%, 7–11 y 20%, adolescents 53%; parents 37%.
  - 40% response to the first alarm of the night vs 28% after.
  - They woke in all 11 confirmed ≤70 events, but 55% of alarm events were false.
- Without an alarm, only 1 of 16 adults with T1D woke from induced hypoglycaemia to 2.2 mmol/L (Schultes 2007).
- **No checked adult CGM-alarm wake rate was found** (gap).
- **Modelling:** `p_wake` per alarm event as a per-person trait, age-scaled, decaying with repeated alarms, with a carer channel for children.

**Awareness.** Impaired awareness affects 23.4% of adults (Ogundipe 2011). Asymptomatic lows make up 47% of <3.0 readings with impaired awareness vs 14% without (Schopman 2011). Use it as a binary trait that gates symptom-triggered treatment when no alarm sounds.

## 4. Hyperglycaemia and monitoring

**Correction boluses.** Camerlingo 2022 (196 adults, free-living) modelled whether a post-meal correction is given in the next window with a decision tree. The top predictors were CGM level and trend, time since the last bolus, and time of day. Use this hazard form directly.

On AID, user corrections compete with automatic ones. In older 780G users, auto-correction was 14–21% of insulin, and more user-initiated bolus insulin went with better time in tight range (Volčanšek 2026). Higher daily auto-correction predicted lower TIR (Castañeda 2022).

**"Rage bolusing"** (a large correction after a prolonged high, often stacked): **no peer-reviewed quantification found**. Model it as a per-person `corr_aggressiveness` multiplier and a `stacking_tolerance` (minimum minutes between user corrections). Calibrate both from donor data **[assumption]**.

**Monitoring frequency.**
- Dexcom G6 trend-screen views: bottom quartile <3.30/day, top quartile >8.25/day (Puhr 2020; quartile group means 2.5 and ~13–14/day).
- Libre (scan required to see data): mean 16.3/day, median 14 [10–20]. The lowest and highest ventiles averaged 4.4 and 48.1/day (Dunn 2018).
- Voice glucose queries: median 1.84/day (Akturk 2021).
- **Modelling:** `glances_per_day` ~ lognormal across people (median ~5, with quartile cut points 3.3 and 8.3 from Puhr) as a Poisson process modulated by time of day. A glance is the opportunity for any discretionary action (correction, pre-emptive carbs, temp target).

## 5. Other actions

**Exercise.**
- In T1DEXI (497 adults), mean glucose change during a session was aerobic −18 ± 39, interval −14 ± 32, resistance −9 ± 36 mg/dL. TIR in the next 24 h was 76 vs 70% on non-exercise days (Riddell 2023).
- Exercise nights had more level-1 nocturnal hypo (15.6 vs 13.1%). HCL users had about half the rate of standard-pump and MDI users (Bisno 2026).
- The EASD/ISPAD position statements (Moser 2020 for CGM; Moser 2024 for AID) give practice points: raise the target or use exercise mode 1–2 h before, reduce the pre-exercise meal bolus, and take carbs when glucose is low or falling. The specific numbers (e.g. target ~150–160 mg/dL, bolus −25 to −75%) **[unverified — abstracts only]**.
- Real-world *uptake* of temp targets or exercise modes and of pre-exercise carbs was not found in checked sources (gap).

**Site and sensor changes.**
- Infusion sets: labelled 2–3 days. Real-world wear 3.6 ± 1.1 days on standard sets and 6.1 ± 2.3 days on 7-day sets (Nieto de la Marca 2026); 48% kept the full 7 days.
- Sensor wear follows the device label: Dexcom G6/G7 ~10 d, Libre 14 d **[unverified — labels]**.
- Model a change as a fixed-interval event with jitter, plus a disruption window (warm-up, set failure).

**Pump suspension / disconnection.** No checked quantification (gap). The project already detects suspends and loop-offline gaps from the data; use those empirical rates.

**System disengagement.**
- Time in automation: Control-IQ median 94.2% (Breton 2021); Loop modulating basal ≥83% (Lum 2021).
- The 670G in youth fell from 65% to 51% Auto Mode over 6 months, and 30% discontinued (Berget 2020; Messer 2020).
- Model `p_closed_loop` as a person trait.

## 6. Age and AID experience

| Behaviour | Children | Adolescents | Adults | Source |
|---|---|---|---|---|
| Missed boluses | 12–22% of days with ≥1 missed (HCL, 6–12 y) | 38% missed >15% of daily doses | 25% → 14% of meals (MDI pen) | Coutant 2023; Olinder 2009; Adolfsson 2020 |
| Bolus timing (pre-meal/at start) | 61% (<6 y), 72% (6–13 y) | 68% (13–18 y) | Post-meal dosers are younger | Mozzillo 2022 citing Datye 2018; Peters 2017 |
| Carb counting | 73% within 10–15 g (8–18 y, with caregivers) | Within 20%: 67% of meals (8–18 y) | 20.9% mean error | Smart 2010; Deeb 2017; Brazeau 2013 |
| Night alarm wake | 17–20% | 53% | not found | Buckingham 2005 |
| Low / high alert setting (mg/dL) | 78.5 / 266 (≤11 y) | 76.1 / 248 | 74.0 / 218 (25–59 y); 75.5 / 239 (≥60 y) | Akturk 2021 |
| Data sharing with followers | 94.5% | 95.3% | 51.1% (25–59 y) | Akturk 2021 |
| HbA1c (registry) | 65 mmol/mol at 5 y | peaks 78 mmol/mol at 15–18 y | 58–64 mmol/mol >30 y | Foster 2019 |
| AID TIR (Control-IQ, CLIO) | 61.2% (6–13 y) | 60.9% (14–17 y) | 70.1% | Graham 2024 |

**AID experience.**
- Missed meal boluses increase with HCL tenure in children (Coutant 2023).
- Youth Auto Mode use declines over months on first-generation HCL (Berget 2020).
- Control-IQ use stays flat over 12 months (Breton 2021).
- Children's carb-counting error grows with years of counting (Smart 2010).
- Model "behaviour drift" as a slow per-person trend toward fewer and less careful boluses, offset by the algorithm.

## Gaps (fit from the donor pool, not the literature)

- Weekday/weekend meal and sleep timing.
- Minute-level pre-bolus distribution.
- CGM value and delay at which people actually treat lows.
- Adult night-alarm wake rates on CGM.
- Rage-bolus and stacking behaviour.
- Real-world uptake of temp targets and pre-exercise carbs.
- Manual suspend frequency.
- Within- vs between-person variance of meal size.
- The source of "Tidepool TRSET".

---

## References

Status: **A** = checked against the PubMed abstract; **F** = checked against PMC full text; **U** = unverified.

1. Adolfsson P, Hartvig NV, Kaas A, Møller JB, Hellman J. Increased time in range and fewer missed bolus injections after introduction of a smart connected insulin pen. *Diabetes Technol Ther* 2020;22(10):709–718. doi:10.1089/dia.2019.0411 — A
2. Ahola AJ, Forsblom C, Groop PH. Adherence to special diets and its association with meeting the nutrient recommendations in individuals with type 1 diabetes. *Acta Diabetol* 2018;55(8):843–851. doi:10.1007/s00592-018-1159-2 — A
3. Akturk HK, Dowd R, Shankar K, Derdzinski M. Real-world evidence and glycemic improvement using Dexcom G6 features. *Diabetes Technol Ther* 2021;23(S1):S21–S26. doi:10.1089/dia.2020.0654 — F
4. American Diabetes Association Professional Practice Committee. 6. Glycemic goals and hypoglycemia: Standards of Care in Diabetes—2024. *Diabetes Care* 2024;47(Suppl 1):S111–S125. doi:10.2337/dc24-S006 — A (citation only; the 15–20 g rule is from the standard text, U)
5. Berget C, Messer LH, Vigers T, et al. Six months of hybrid closed loop in the real-world: an evaluation of children and young adults using the 670G system. *Pediatr Diabetes* 2020;21(2):310–318. doi:10.1111/pedi.12962 — A
6. Bisno DI, Turner LV, Gallop RJ, et al. Factors associated with nocturnal hypoglycemia after exercise in T1DEXI. *Diabetes Care* 2026;49(8):1404–1413. doi:10.2337/dc26-0381 — A
7. Brazeau AS, Mircescu H, Desjardins K, et al. Carbohydrate counting accuracy and blood glucose variability in adults with type 1 diabetes. *Diabetes Res Clin Pract* 2013;99(1):19–23. doi:10.1016/j.diabres.2012.10.024 — A
8. Breton MD, Kovatchev BP. One year real-world use of the Control-IQ advanced hybrid closed-loop technology. *Diabetes Technol Ther* 2021;23(9):601–608. doi:10.1089/dia.2021.0097 — A
9. Buckingham B, Block J, Burdick J, et al. Response to nocturnal alarms using a real-time glucose sensor. *Diabetes Technol Ther* 2005;7(3):440–447. doi:10.1089/dia.2005.7.440 — A
10. Burdick J, Chase HP, Slover RH, et al. Missed insulin meal boluses and elevated hemoglobin A1c levels in children receiving insulin pump therapy. *Pediatrics* 2004;113(3 Pt 1):e221–e224. doi:10.1542/peds.113.3.e221 — A
11. Camerlingo N, Vettoretti M, Del Favero S, et al. A real-time continuous glucose monitoring-based algorithm to trigger hypotreatments to prevent/mitigate hypoglycemic events. *Diabetes Technol Ther* 2019;21(11):644–655. doi:10.1089/dia.2019.0139 — A
12. Camerlingo N, Vettoretti M, Del Favero S, Facchinetti A, Sparacino G. Mathematical models of meal amount and timing variability with implementation in the type-1 diabetes patient decision simulator. *J Diabetes Sci Technol* 2021;15(2):346–359. doi:10.1177/1932296820952123 (erratum doi:10.1177/1932296821996137) — F
13. Camerlingo N, Vettoretti M, Del Favero S, et al. Generation of post-meal insulin correction boluses in type 1 diabetes simulation models for in-silico clinical trials. *Comput Methods Programs Biomed* 2022;221:106862. doi:10.1016/j.cmpb.2022.106862 — A
14. Cappon G, Vettoretti M, Sparacino G, Del Favero S, Facchinetti A. ReplayBG: a digital twin-based methodology to identify a personalized model from type 1 diabetes data and simulate glucose concentrations to assess alternative therapies. *IEEE Trans Biomed Eng* 2023;70(11):3227–3238. doi:10.1109/TBME.2023.3286856 — A
15. Castañeda J, Mathieu C, Aanstoot HJ, et al. Predictors of time in target glucose range in real-world users of the MiniMed 780G system. *Diabetes Obes Metab* 2022;24(11):2212–2221. doi:10.1111/dom.14807 — A
16. Chatty P, Gera S, Rearson A, et al. Effect of low bolus frequency on automated insulin delivery system performance in youth with type 1 diabetes. *Diabetes Care* 2026;49(2):303–307. doi:10.2337/dc25-2082 — A
17. Cobry E, McFann K, Messer L, et al. Timing of meal insulin boluses to achieve optimal postprandial glycemic control in patients with type 1 diabetes. *Diabetes Technol Ther* 2010;12(3):173–177. doi:10.1089/dia.2009.0112 — A
18. Coutant R, Bismuth E, Bonnemaison E, et al. Hybrid closed loop overcomes the impact of missed or suboptimal meal boluses on glucose control in children with type 1 diabetes compared to sensor-augmented pump therapy. *Diabetes Technol Ther* 2023;25(6):395–403. doi:10.1089/dia.2022.0518 — A
19. Datye KA, Boyle CT, Simmons J, et al. Timing of meal insulin and its relation to adherence to therapy in type 1 diabetes. *J Diabetes Sci Technol* 2018;12(2):349–355. doi:10.1177/1932296817728525 — A
20. Deeb A, Al Hajeri A, Alhmoudi I, Nagelkerke N. Accurate carbohydrate counting is an important determinant of postprandial glycemia in children and adolescents with type 1 diabetes on insulin pump therapy. *J Diabetes Sci Technol* 2017;11(4):753–758. doi:10.1177/1932296816679850 — A
21. Dunn TC, Xu Y, Hayter G, Ajjan RA. Real-world flash glucose monitoring patterns and associations between self-monitoring frequency and glycaemic measures. *Diabetes Res Clin Pract* 2018;137:37–46. doi:10.1016/j.diabres.2017.12.015 — A
22. Foster NC, Beck RW, Miller KM, et al. State of type 1 diabetes management and outcomes from the T1D Exchange in 2016–2018. *Diabetes Technol Ther* 2019;21(2):66–72. doi:10.1089/dia.2018.0384 — A
23. Gingras V, Desjardins K, Smaoui MR, et al. Treatment of mild-to-moderate hypoglycemia in patients with type 1 diabetes treated with insulin pump therapy: are current recommendations effective? *Acta Diabetol* 2018;55(3):227–231. doi:10.1007/s00592-017-1085-8 — A
24. Graham R, Mueller L, Manning M, et al. Real-world use of Control-IQ technology is associated with a lower rate of severe hypoglycemia and DKA than historical data (CLIO). *Diabetes Technol Ther* 2024;26(1):24–32. doi:10.1089/dia.2023.0341 — A
25. Grassi BA, Onetto MT, Mora G, et al. Mitigation strategies for a missed meal bolus in people with type 1 diabetes using the MiniMed 780G system. *Diabetes Technol Ther* 2026;28(4):374–380. doi:10.1177/15209156251395010 — A
26. Groat D, Grando MA, Soni H, et al. Self-management behaviors in adults on insulin pump therapy: what are patients really doing? *J Diabetes Sci Technol* 2017;11(2):233–239. doi:10.1177/1932296816666538 — F
27. Lennerz BS, Barton A, Bernstein RK, et al. Management of type 1 diabetes with a very low-carbohydrate diet. *Pediatrics* 2018;141(6):e20173349. doi:10.1542/peds.2017-3349 — A
28. Lum JW, Bailey RJ, Barnes-Lomen V, et al. A real-world prospective study of the safety and effectiveness of the Loop open source automated insulin delivery system. *Diabetes Technol Ther* 2021;23(5):367–375. doi:10.1089/dia.2020.0535 — A
29. McTavish L, Corley B, Weatherall M, Wiltshire E, Krebs JD. Weight-based carbohydrate treatment of hypoglycaemia in people with type 1 diabetes using insulin pump therapy: a randomized crossover clinical trial. *Diabet Med* 2018;35(3):339–346. doi:10.1111/dme.13576 — A
30. Messer LH, Berget C, Vigers T, et al. Real world hybrid closed-loop discontinuation: predictors and perceptions of youth discontinuing the 670G system in the first 6 months. *Pediatr Diabetes* 2020;21(2):319–327. doi:10.1111/pedi.12971 — A
31. Messer LH, Berget C, Pyle L, et al. Real-world use of a new hybrid closed loop improves glycemic control in youth with type 1 diabetes. *Diabetes Technol Ther* 2021;23(12):837–843. doi:10.1089/dia.2021.0165 — A
32. Moser O, Riddell MC, Eckstein ML, et al. Glucose management for exercise using CGM and isCGM systems in type 1 diabetes: EASD/ISPAD position statement. *Pediatr Diabetes* 2020;21(8):1375–1393. doi:10.1111/pedi.13105 — A (practice-point numbers U)
33. Moser O, Zaharieva D, Adolfsson P, et al. The use of automated insulin delivery around physical activity and exercise in type 1 diabetes: EASD/ISPAD position statement. *Horm Res Paediatr* 2026;99(3):391–418 (epub 2024). doi:10.1159/000542287 — A (practice-point numbers U)
34. Mozzillo E, Franceschi R, Di Candia F, et al. Optimal prandial timing of insulin bolus in youths with type 1 diabetes: a systematic review. *J Pers Med* 2022;12(12):2058. doi:10.3390/jpm12122058 — F
35. Nieto de la Marca MO, Fernández Velasco P, et al. Real-world safety, patient-reported outcomes, and glycemic metrics with a 7-day extended infusion set in adults with type 1 diabetes using AID systems. *Endocrine* 2026;91(1):284. doi:10.1007/s12020-026-04743-z — A
36. Ogundipe OO, Geddes J, Leckie AM, Frier BM. Impaired hypoglycaemia awareness and employment in people with type 1 diabetes. *Occup Med* 2011;61(4):241–246. doi:10.1093/occmed/kqr027 — A
37. Olinder AL, Kernell A, Smide B. Missed bolus doses: devastating for metabolic control in CSII-treated adolescents with type 1 diabetes. *Pediatr Diabetes* 2009;10(2):142–148. doi:10.1111/j.1399-5448.2008.00462.x — A
38. Peters A, Van Name MA, Thorsted BL, Piltoft JS, Tamborlane WV. Postprandial dosing of bolus insulin in patients with type 1 diabetes: a cross-sectional study using data from the T1D Exchange registry. *Endocr Pract* 2017;23(10):1201–1209. doi:10.4158/EP171813.OR — A
39. Polin MR, Johnson AK, Messer LH, Pinsker JE, Constantin A. What happens when people don't bolus for extended periods of time while using Control-IQ technology. ADA 84th Scientific Sessions, 2024 (EMJ symposium write-up). No DOI — U
40. Puhr S, Derdzinski M, Parker AS, Welsh JB, Price DA. Real-world hypoglycemia avoidance with a predictive low glucose alert does not depend on frequent screen views. *J Diabetes Sci Technol* 2020;14(1):83–86. doi:10.1177/1932296819840691 — F
41. Riddell MC, Li Z, Gal RL, et al. Examining the acute glycemic effects of different types of structured exercise sessions in type 1 diabetes in a real-world setting: T1DEXI. *Diabetes Care* 2023;46(4):704–713. doi:10.2337/dc22-1721 — A
42. Robinson S, Newson RS, Liao B, Kennedy-Martin T, Battelino T. Missed and mistimed insulin doses in people with diabetes: a systematic literature review. *Diabetes Technol Ther* 2021;23(12):844–856. doi:10.1089/dia.2021.0164 — A
43. Roversi C, Camerlingo N, Vettoretti M, et al. Risk of hypoglycemia in type 1 diabetes management: an in-silico sensitivity analysis to assess and rank the quantitative impact of different behavioral factors. *Comput Methods Programs Biomed* 2024;244:107943. doi:10.1016/j.cmpb.2023.107943 — A
44. Savard V, Gingras V, Leroux C, et al. Treatment of hypoglycemia in adult patients with type 1 diabetes: an observational study. *Can J Diabetes* 2016;40(4):318–323. doi:10.1016/j.jcjd.2016.05.008 — A
45. Schopman JE, Geddes J, Frier BM. Frequency of symptomatic and asymptomatic hypoglycaemia in type 1 diabetes: effect of impaired awareness of hypoglycaemia. *Diabet Med* 2011;28(3):352–355. doi:10.1111/j.1464-5491.2010.03203.x — A
46. Schultes B, Jauch-Chara K, Gais S, et al. Defective awakening response to nocturnal hypoglycemia in patients with type 1 diabetes mellitus. *PLoS Med* 2007;4(2):e69. doi:10.1371/journal.pmed.0040069 — A
47. Slattery D, Amiel SA, Choudhary P. Optimal prandial timing of bolus insulin in diabetes management: a review. *Diabet Med* 2018;35(3):306–316. doi:10.1111/dme.13525 — A
48. Smart CE, Ross K, Edge JA, et al. Children and adolescents on intensive insulin therapy maintain postprandial glycaemic control without precise carbohydrate counting. *Diabet Med* 2009;26(3):279–285. doi:10.1111/j.1464-5491.2009.02669.x — A
49. Smart CE, Ross K, Edge JA, et al. Can children with type 1 diabetes and their caregivers estimate the carbohydrate content of meals and snacks? *Diabet Med* 2010;27(3):348–353. doi:10.1111/j.1464-5491.2010.02945.x — A
50. Snell-Bergeon JK, Chartier-Logan C, Maahs DM, et al. Adults with type 1 diabetes eat a high-fat atherogenic diet that is associated with coronary artery calcium. *Diabetologia* 2009;52(5):801–809. doi:10.1007/s00125-009-1280-4 — A
51. Susuł K, Ucieklak D, Cyranka K, et al. Impact of Extended Wear infusion sets in adults with type 1 diabetes using the MiniMed 780G: a pilot RCT. *Endokrynol Pol* 2026 (online ahead of print). doi:10.5603/ep.112819 — A
52. Taleb N, Gingras V, Cheng R, et al. Non-severe hypoglycemia in type 1 diabetes: a randomized crossover trial comparing two quantities of oral carbohydrates at different insulin-induced hypoglycemia ranges. *Front Endocrinol* 2023;14:1186680. doi:10.3389/fendo.2023.1186680 — A
53. Tidemand KG, Laugesen C, Ranjan AG, Skovhus LB, Nørgaard K. Frequency of rebound hyperglycemia in adults with type 1 diabetes treated with different insulin delivery modalities. *Diabetes Technol Ther* 2025;27(1):60–65. doi:10.1089/dia.2024.0134 — A
54. VanderWel BW, Messer LH, Horton LA, et al. Missed insulin boluses for snacks in youth with type 1 diabetes. *Diabetes Care* 2010;33(3):507–508. doi:10.2337/dc09-1840 — A
55. Vasiloglou MF, Mougiakakou S, Aubry E, et al. A comparative study on carbohydrate estimation: GoCARB vs. dietitians. *Nutrients* 2018;10(6):741. doi:10.3390/nu10060741 — A
56. Vettoretti M, Facchinetti A, Sparacino G, Cobelli C. Type-1 diabetes patient decision simulator for in silico testing safety and effectiveness of insulin treatments. *IEEE Trans Biomed Eng* 2018;65(6):1281–1290. doi:10.1109/TBME.2017.2746340 — A
57. Visentin R, Campos-Náñez E, Schiavon M, et al. The UVA/Padova type 1 diabetes simulator goes from single meal to single day. *J Diabetes Sci Technol* 2018;12(2):273–281. doi:10.1177/1932296818757747 — A
58. Volčanšek Š, Vidmar P, Janež A, Skvarča A. Insulin delivery characteristics and glycemic control in older adults with type 1 diabetes using the MiniMed 780G system. *Front Endocrinol* 2026;17:1910192. doi:10.3389/fendo.2026.1910192 — A
