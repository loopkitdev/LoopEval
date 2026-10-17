# 12 — Nightly factors in overnight insulin need: a literature budget

> **How this was used (2026-10-16).** Commissioned for the night-to-night overnight-insulin gap (LESSONS 55–56). Evidenced nightly factors cover roughly a third to half of the gap. The donor-side checks it suggested were run (LESSONS 56). Claims are tagged as found.

The gap: donors' quiet-night 00:00–06:00 delivered insulin has a within-person CV of about 30%
(lag-1 r 0.09). The simulator gives 17%. The missing variance is 0.30² − 0.17² ≈ 0.061, which
needs an extra independent nightly SD of about 25% in overnight need.

Tags: **[checked]** means I read the abstract (Europe PMC) or the stated text myself.
**[secondary]** means the number comes from a review or search summary that quotes the paper.
**[unverified]** means the item is cited from memory or the source is not read. **[derived]** means
it is my arithmetic on top of the cited numbers.

---

## 0. Bounding studies: how much of the variation is intrinsic?

| Study | Design | Result | Tag |
|---|---|---|---|
| Perriello 1991, *Diabetologia*, doi:10.1007/bf00404020 | i.v. insulin (Harvard pump) to hold euglycaemia overnight; T1D n = 114 | Need falls to a nadir of 0.102 ± 0.03 mU/kg/min at 02:40 and rises to 0.135 ± 0.06 at 06:40. Dawn rise +19.4% (present in 101 of 114). "Nocturnal insulin requirements and the dawn phenomenon were **highly reproducible on three separate nights**." No CV is given in the abstract | [checked] (abstract only; full-text CV not seen) |
| Ruan 2016, *Diabetes Care*, doi:10.2337/dc15-2623 | Home hybrid closed loop (Cambridge MPC), 32 adults, 12 wk, 1,918 nights | Overnight CV **31 ± 4%**, daytime 22 ± 4%, total daily 17 ± 3% | [checked] |
| Boughton 2021, *Diabetes Obes Metab*, doi:10.1111/dom.14396 | Inpatient fully closed loop, T2D / new hyperglycaemia, n = 67 | Overnight CV 56 ± 29%, daily 30 ± 16%. Not T1D, illness present | [checked] |
| Ruan 2017, *IEEE TBME*, doi:10.1109/tbme.2016.2590498 | Hierarchical Bayesian model on 12 weeks of home closed loop, n = 8 | Day-to-day SI CV **38–79%**, insulin time-to-peak 27–48%. A model residual that absorbs every unmodelled factor, so it is an upper bound, not an intrinsic value | [checked] |
| Mallad 2015 (in 07-intrinsic-variability.md) | Two consecutive standardized nights, n = 16 | Group means of EGP and slope did not differ. Within-subject spread not reported | [from existing evidence file] |

**Reading [derived]:** controlled i.v. nights are "highly reproducible", while free-living closed
loop gives 31%. Most of the free-living overnight CV is therefore extrinsic: life factors,
behaviour, sensor and delivery. Two caveats apply. First, *delivered* insulin under a controller is
not *need*: the controller turns sensor artefacts and start-of-night state into delivery variance.
This is already present in the simulator, because it runs Loop. Second, Ruan's nights are not
"quiet" (dinner tails and snacks are included), whereas the donor figure is for quiet nights only
and still reaches 30%.

---

## 1. Evening alcohol

**Effect and time course**

- **Turner 2001**, *Diabetes Care* 24:1888, doi:10.2337/diacare.24.11.1888 **[checked]**. Design:
  6 men with T1D; 0.75 g/kg (≈ 52 g ≈ 4 US drinks at 70 kg) of dry white wine at 21:00 over 90 min;
  fixed basal infusion from 23:00. Results:
  - **No significant difference in evening or overnight glucose.**
  - Fasting and post-breakfast glucose were lower (post-breakfast peak 8.9 vs 15 mmol/L), and 5 of
    6 needed hypo treatment from 10:00.
  - Nocturnal GH AUC 00:00–04:00 was 2.1 vs 6.5 µg·l⁻¹·h (P = 0.04).
  - So the effect lands **10–13 h after drinking**, mostly *after* 06:00.
- **Kerr 2007**, *Diabet Med* 24:312, doi:10.1111/j.1464-5491.2006.02054.x **[checked abstract]**.
  17 T1D on clamps at 0.4 g/kg. Alcohol attenuated GH (peak 14.3 vs 25.9 µg/L) and **reduced insulin
  sensitivity** at both euglycaemia and hypoglycaemia. The GIR numbers come from a review
  **[secondary]**: 150 vs 171 mL/h at euglycaemia, ≈ −12%. The acute phase while ethanol is present
  is mild *resistance*, not sensitisation.
- **Plougmann 2002/2003**, *Int J Med Inform*, doi:10.1016/s1386-5056(03)00038-8 **[checked]**.
  This is a model (DiasNet-Alcohol), not a measurement. Its mechanism: NADH-driven inhibition of
  gluconeogenesis plus glycogen depletion while alcohol is metabolised, then raised hepatic
  insulin sensitivity while glycogen is restored, returning to normal "after several hours".
- **Richardson 2005**, *Diabetes Care* 28:1801, doi:10.2337/diacare.28.7.1801. Free-living, with
  moderate alcohol at the evening meal. Mean interstitial glucose over 24 h was **1.2 mmol/L
  lower** (P = 0.02), with hypo symptoms 1.3 vs 0.6 **[secondary — no abstract; numbers from a
  systematic review]**.
- **Kerr 1990** (alcohol and hypoglycaemia unawareness) was not retrieved **[unverified]**.

**Frequency**

- T1D Exchange, Petry 2018, *Diabetes Educ*, doi:10.1177/0145721718799088 **[checked]**: n = 936,
  age 38 ± 16. Past-year use 79%, past-month 63%, daily or near-daily 9%, binge 19%, problem
  drinkers 11%.
- Alessi 2020, *Can J Diabetes*, doi:10.1016/j.jcjd.2020.06.005 **[checked]**: 11% never drinkers,
  9% former, 61% non-binge current, 19% binge.
- Drinking days per week are not reported for T1D **[NF]**. Population drinking clusters on
  Friday and Saturday **[unverified]**.

**Per-person variation:** Turner shows a range of morning nadirs (1.9–2.9 mmol/L in 5 of 6), and
one person was unaffected. Studies have n = 6–17, with no usable spread.

**Budget [derived]:**
- Assume 20% of nights carry ≥ 2 drinks, which is generous for a cohort where about a third drink
  less than monthly.
- The 00:00–06:00 net effect is small in the one controlled study: acute resistance early, then
  sensitisation and lower EGP late.
- Take Δ ≈ ±10% in window need. Variance ≈ p(1 − p)Δ² ≈ 0.2·0.8·0.01 = **0.0016**, an SD of about
  4%, or ~3% of the gap.
- Even at Δ = 25% (an unsupported upper case) it is about 0.010, ~17% of the gap.
- Alcohol mostly shifts **06:00–12:00**, which is outside the measured window.

---

## 2. Sleep duration and timing

**Effect**

- **Donga 2010, T1D**, *Diabetes Care*, doi:10.2337/dc09-2317 **[checked]**. n = 7; 4 h vs normal
  sleep (222 vs 469 min). Basal glucose, NEFA and **basal EGP unchanged**. Clamp GDR 22.0 vs 25.5
  (−14%), GIR **−21%**. The clamp was performed the *following day* (timing as in the healthy
  study).
- **Donga 2010, healthy**, *JCEM*, doi:10.1210/jc.2009-2430 **[checked]**. n = 9; sleep 01:00–05:00
  vs 23:00–07:30. Clamp at 11:30–14:30: GIR −25%, GDR −20%, clamp EGP 4.4 vs 3.6. **Basal EGP
  unchanged.**
- **Sondrup 2022** meta-analysis, *Sleep Med Rev*, doi:10.1016/j.smrv.2022.101594 **[checked]**.
  Sleep restriction lowers whole-body insulin sensitivity (OGTT/IVGTT/HOMA, clamp whole-body).
  Peripheral clamp sensitivity was **not** affected in pooled RCTs. Circadian misalignment and
  slow-wave-sleep suppression also lower insulin sensitivity.
- **Time course:** the measured effect is on the *next day*. No study measures overnight insulin
  need *during* a short or shifted night in T1D **[NF]**. Basal (fasting-state) EGP was unchanged
  in both Donga studies, which argues against a large same-night effect.

**Night-to-night spread:** Messman 2022, *J Sleep Res*, doi:10.1111/jsr.13680 **[checked]** pooled
8 datasets (N = 2,404, 26,121 nights). Within-person SD of sleep duration: **77 min** by actigraphy,
86 min by diary, 67 min by EEG. CV ≈ 19%, RMSSD 92–119 min (high RMSSD means mostly
alternating, not drifting). Younger adults vary more. Adolescents with T1D sleep 6.8–7.6 h with
"high night-to-night variability" (Juhi 2026 review **[checked abstract]**).

**Budget [derived]:**
- Linear extrapolation from −21% per ~4 h lost gives ~5%/h. With an SD of 1.3 h that is an SD of
  ~7% in next-day SI.
- The dose-response for mild loss is unknown and probably sub-linear, so this is an upper value.
- If applied to the *following* 00:00–06:00 window, variance ≈ 0.005 (≈ 8% of the gap).
- RMSSD > SD (alternation) predicts a **negative** lag-1 contribution. That is compatible with the
  donors' small lag-1 of 0.09.

---

## 3. Exercise and the delayed (overnight) sensitivity rise

**Effect**

- **McMahon 2007**, *JCEM*, doi:10.1210/jc.2006-2263 **[checked]**. 9 adolescents; 45 min at 95%
  of lactate threshold in the late afternoon vs rest. Insulin was given i.v. at matched levels. GIR was raised
  during and just after exercise, and **again 7–11 h after**, so biphasic. The magnitude (≈ +10 g
  i.v. glucose per 70 kg in the late phase) is **[secondary]**, from 02-life-factors.md.
- **Taplin 2010**, *J Pediatr* 157:784, PMID 20650471 **[secondary — abstract via search summary]**.
  16 youths on pumps after 60 min of afternoon exercise. A **20% basal cut for 6 h** at bedtime
  raised the nadir and cut hypoglycaemia, but produced *more* readings ≥ 250. So 20% is slightly
  above the average overnight need reduction for that dose of exercise.
- **Maran 2010**, *Diabetes Technol Ther*, doi:10.1089/dia.2010.0038 **[checked]**. 8 men; 30 min
  intermittent high-intensity vs moderate. Midnight–06:00 glucose was lower after the
  intermittent session, with 7 vs 2 hypos.
- **Mikines 1988**, *Am J Physiol*, doi:10.1152/ajpendo.1988.254.3.e248 **[checked]**. Healthy;
  60 min at 150 W. Insulin action rose (Km 52 → 40–43 µU/mL, Vmax +13%) and **lasted 48 h, not 5
  days**.
- **Free living, T1DEXI**:
  - Bisno 2026, *Diabetes Care*, doi:10.2337/dc26-0381 **[checked]**: 496 adults, 12,340 nights.
    Level-1 nocturnal hypo 15.6% after exercise days vs 13.1% after sedentary days. Hybrid closed
    loop about halves the rates (9.7% vs 20.3% for standard pump).
  - Riddell 2023, doi:10.2337/dc22-1721 **[checked]**: TIR in the 24 h after exercise 76% vs 70%.
  - The TDD drop on exercise days is ≈ 0.55 → 0.52 U/kg (≈ 5%) **[from evidence/10, not
    re-read]**.

**Frequency and spread:**
- T1DEXI (an active, self-selected cohort): a logged session on **60 ± 20% of days**, mean 41 min,
  21% of sessions 60–120 min (evidence/10, Dhaliwal 2025 **[checked abstract]**).
- Within-person day-to-day CV of accelerometer activity is 18.8% for total acceleration and
  **35.4% for MVPA** (Brady 2023, *BMC Public Health*, doi:10.1186/s12889-023-16734-0
  **[secondary]**).

**Per-person variation:** large. Mikines-type responses are graded with duration and intensity,
and Maran shows intensity matters.

**Budget [derived]:**
- Treat the post-exercise night as Bernoulli(p ≈ 0.5) with a mean overnight need reduction of
  ~12% (Taplin's 20% basal cut, with the cut a little too large) and a session-to-session SD of
  ~8% (duration and intensity).
- Variance ≈ 0.25·0.0144 + 0.5·0.0064 ≈ **0.0068**, an SD of about 8% (≈ 11% of the gap).
- In a less active cohort (p ≈ 0.3) it is about 0.004.
- **Check against the simulator:** C2's slow state Z (τ 600 min) was tuned so a doubled-activity
  day lowers TDD ~5%. That calibration says nothing about how the effect is split across the
  *night*. Measure the simulator's 00:00–06:00 delivery on nights after a ≥ 40-min session vs none.
  Taplin and McMahon put the target at a ~10–20% reduction for a 45–60 min moderate afternoon
  session.

---

## 4. Psychological stress

- **Moberg 1994**, *Diabetologia*, doi:10.1007/bf00398050 **[checked]**. 10 T1D; 20 min Stroop
  test, then an insulin–glucose infusion test. Steady-state glucose 10.6 vs 8.7 mmol/L at fixed
  insulin, starting 1 h after stress and lasting **> 5 h**. That is insulin resistance of
  meaningful size for an acute lab stressor (adrenaline, cortisol and GH all rose).
- **Wiesli 2005**, *Diabetes Care*, doi:10.2337/diacare.28.8.1910 **[checked]**. TSST in 40 T1D.
  **No effect in the fasting state**; postprandially, a 45-min delay in the glucose fall.
- No study links day-level or evening stress to *overnight* insulin need in T1D **[NF]**.

**Budget [derived]:** acute stressors near bedtime are uncommon, and the fasting-state effect was
nil in Wiesli. Contribution is probably **≤ 0.001–0.002**. Too small to carry the gap, and the
parameters are unidentified.

---

## 5. Nocturnal growth hormone

**Effect**

- **Campbell 1985**, *NEJM*, doi:10.1056/nejm198506063122302 **[checked]**. 6 T1D at constant
  insulin. Glucose rose 98 → 225 mg/dL by 08:00 (EGP +65%, clearance −50%). Somatostatin blocked
  it, and GH pulses restored it. The glucose rise correlated with peak GH (r = 0.58).
- **Edge 1990**, *Clin Endocrinol*, doi:10.1111/j.1365-2265.1990.tb03910.x **[checked]**. 26
  adolescents on a variable-rate insulin clamp. Need was 15.22 (05:00–08:00) vs 12.42 (01:00–04:00)
  mU/kg/h (+23%), and the rise correlated with mean GH (r = 0.68). Pirenzepine cut GH 11–85% (17.6
  → 7.5 mU/L) and abolished the dawn rise. The fall in 05:00–08:00 need tracked the fall in GH
  (rs = 0.82).
- Acerini 2000, *Diabetologia*, doi:10.1007/s001250050008 **[checked]**: overnight GH relates to
  both SI (r = −0.40) and insulin clearance (r = −0.37).

**Night-to-night spread of GH:**
- Weill 1990, *Horm Res*, doi:10.1159/000181787 **[checked]**: two consecutive nights,
  significant within-subject variability in peak and mean.
- Ropelato 1996, doi:10.1515/jpem.1996.9.1.41 **[checked]**: repeat overnight GH parameters CV
  **≈ 30%**.
- Saini 1991, *Clin Endocrinol*, doi:10.1111/j.1365-2265.1991.tb00325.x **[checked]**: adults, 24-h
  mean GH within-person CV **35% (range 9–58%)**.
- Alcohol and sleep timing both act through GH (Turner 2001; slow-wave-sleep-linked secretion
  **[unverified]**), so part of the GH variance is the same variance as sections 1 and 2, not
  extra.

**Budget [derived]:**
- If GH drives the whole dawn increment (~20% in adults per Perriello, ~23% in adolescents per
  Edge) with elasticity ~1, a 30–35% GH CV gives ~6–7% SD in the 03:00–06:00 need. That is ~3–4%
  over the full 00:00–06:00 window.
- Variance ≈ **0.001–0.002**.
- This fits Perriello's "highly reproducible" overnight need. **Too small** on its own.

---

## 6. Other nightly factors

### 6a. Evening-meal composition and timing (the largest candidate)

- **Wolpert 2013**, *Diabetes Care*, doi:10.2337/dc12-0092 **[checked]**. Closed loop for 18 h
  after a dinner with 60 vs 10 g fat (same carbohydrate and protein). Insulin **12.6 vs 9.0 U
  (+40%)**, with more hyperglycaemia despite the extra insulin. **Marked inter-individual
  differences** (percent increase correlated with daily insulin, R² 0.64).
- Within-person day-to-day variation in fat intake is large: ~40–60% CV in 24-h recalls (Beaton
  1979, *AJCN*, doi:10.1093/ajcn/32.12.2546 **[unverified — no abstract retrieved]**).
- Meal timing is erratic: Gill & Panda 2015, *Cell Metab*, doi:10.1016/j.cmet.2015.09.005
  **[checked]**, found >35% of calories after 18:00, eating spread over ≥ 14.75 h for half the
  cohort, and weekday/weekend "metabolic jetlag".
- The **simulator's prior** (A12) is: fat SI dip ρ·fat/50 with ρ ~ U(0, 0.35), so mean 0.175;
  fat 0.44 g/g carb ±50%; full effect to 6 h, gone by 10 h.
  - Wolpert's +40% for +50 g fat implies an average ρ nearer 0.3–0.4 (if most of that insulin is
    fat-driven resistance).
  - Even at ρ = 0.175, a 22:00 cut-off means a 19:00–21:00 dinner's fat dip covers most of
    00:00–06:00.
- **Budget [derived]:**
  - Dinner fat SD ~15 g × ρ 0.3/50 g ≈ 9% SI SD at full effect, ~6–7% over the window. Variance
    ≈ 0.004–0.005.
  - Adding dinner timing (SD ~1 h, moving the protein/fat tail in and out of the window) and dinner
    carb-count error tails gives perhaps **0.005–0.01** in total.
  - This is a **parameter question for an existing component**, not a new factor: check that the
    simulator's per-dinner fat, protein and timing spread, and ρ, match these numbers.

### 6b. Compression artefacts (sensor side, already wired)

- Facchinetti 2016, *Diabetes Technol Ther*, doi:10.1089/dia.2015.0250 **[checked]**: 72 subjects
  (G4P). Duration 45 (30–70) min, depth 24 (10–48) mg/dL, mostly at night.
- A false low makes Loop suspend or cut basal, so delivered insulin varies with no change in need.
- COMPONENTS D5 says the simulator's rate is **~10× below the literature rate**, because it was
  fitted to a strict donor detector.
- This is the one listed sensor term that adds nightly, independent delivery variance under AID.
  Check how much of the 30% the donors' own compression-flagged nights carry, by recomputing
  donor CV excluding them.

### 6c. Ambient temperature

No T1D study links night-to-night temperature to overnight need **[NF]**. Heat speeds s.c.
absorption **[unverified]**, but bedroom temperature varies little night to night. Probably
negligible.

### 6d. Menstrual cycle

The donors show no monthly rhythm, and B5 is off. A cycle effect would add lag-1 correlation,
not nightly variance. Excluded.

### 6e. Things that would raise lag-1 correlation

Infusion-site effects, illness and settings edits persist for 2–3 days, so they would raise lag-1
correlation well above 0.09. **They cannot be the missing term**; do not enlarge them.

---

## 7. Ranked recommendation

Variance targets: gap ≈ **0.061**. Each line gives the [derived] variance at evidence-supported
parameters.

| Rank | Factor (new or re-parameterised) | Parameters the evidence supports | Var. added | Share of gap |
|---|---|---|---|---|
| 1 | **Post-exercise overnight sensitivity (C2) — check the night split** | After a 45–60 min moderate afternoon session, overnight need −10% to −20% (Taplin, McMahon), on 40–60% of days, session SD ~8% | 0.004–0.007 | 7–11% |
| 2 | **Dinner composition and timing (A12 re-parameterisation)** | ρ centred ~0.3 (Wolpert +40% for +50 g fat, wide per-person spread); per-dinner fat CV ~50%; dinner time SD ~1 h | 0.005–0.010 | 8–16% |
| 3 | **Prior-night sleep loss (B7, new)** | Next-day SI −5%/h of lost sleep (Donga T1D −21% at −4 h; likely sub-linear); nightly duration SD 77 min, alternating | ≤ 0.005 | ≤ 8% |
| 4 | **Compression-artefact rate (D5)** | Literature rate is ~10× the current one, mostly at night; affects delivery, not need | unknown — measure in the simulator | — |
| 5 | Evening alcohol (B9, new) | ≥ 2 drinks on ≤ 20% of nights; 00:00–06:00 net Δ ±10% (Turner: no overnight difference; effect 06:00–12:00); acute −12% SI while ethanol is present (Kerr) | 0.002 (0.01 at an unsupported ±25%) | 3% (≤ 17%) |
| 6 | Nocturnal GH variability | GH night CV 30–35%; dawn increment ~20%, elasticity ~1 | 0.001–0.002 | 2–3% |
| 7 | Evening stress | lab-stress resistance > 5 h (Moberg), no fasting effect (Wiesli) | ≤ 0.002 | ≤ 3% |
| — | Temperature, menstrual, site, illness | — | ~0 nightly / adds lag-1 | excluded |

**Bottom line (honest):**
- With evidence-supported parameters, factors 1, 2, 3, 5, 6 and 7 together add about **0.02–0.035**
  of variance. That raises the simulated CV from 17% to roughly **22–26%**, short of 30%.
  - Taking every factor at the top of its range gets near 0.04 (CV ≈ 27%).
  - The literature does not justify closing the full 0.06 with named physiology.
- The two biggest levers are existing components whose *night-time* behaviour has not been checked
  against these numbers: C2's overnight split and A12's dinner-fat spread.
- The most likely home for the remainder is not physiology:
  - **Behaviour and sensor terms in the donors' "quiet" nights:** unlogged snacks and rescue
    carbohydrate, compression lows, and overnight Temporary Overrides or manual suspends.
  - **Controller–state interaction:** IOB and glucose at 22:00 rather than at midnight, and the
    dinner bolus error tail.
  - Ruan's 31% under a different controller, with no quiet-night filter, suggests the CV is a
    property of free living plus closed loop, not of the body.
- Before adding physiology, run three cheap **donor-side tests**:
  1. **Day-of-week:** Friday/Saturday vs Sunday–Thursday overnight delivery. Alcohol and sleep
     timing predict a weekend signal; its size bounds factors 3 and 5 directly.
  2. **Compression-flagged nights:** recompute the donor CV after excluding them.
  3. **22:00 IOB and COB residual:** regress night delivery on 22:00 IOB/COB and dinner time, not
     midnight glucose.

  Whatever survives those tests is the real physiology target.
- Per the no-mystery-terms rule, if a residual of ~15–20% CV remains after these, report it as
  unexplained rather than adding a nightly noise term.

## Not found [NF]

- Overnight insulin need measured *during* a short or shifted night in T1D.
- Drinking-days-per-week distribution in T1D adults.
- A CV from Perriello's three-night repeats (full text paywalled).
- A free-living AID study of overnight delivery on exercise vs non-exercise nights (T1DEXI reports
  hypo rates, not overnight insulin).
- Any T1D study linking night-to-night ambient temperature to overnight need.
