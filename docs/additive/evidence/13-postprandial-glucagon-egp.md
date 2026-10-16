# 13 — Postprandial (paradoxical) glucagon in T1D: evidence and sizing for the additive simulator

> **How this was used (2026-10-16).** Commissioned for the post-meal plateau gap (LESSONS 66). Paradoxical glucagon at its evidenced size explains ~0–10 mg/dL, so no glucagon term is built. The tracer EGP-suppression data (Romeres 2025: nadir 44 ± 17% at ~160 min) set the share of insulin acting on EGP (LESSONS 69).

Written 2026-10-16. Tags: **[checked]** means I read the abstract or full text in this session. **[unverified]** means recalled or second-hand, not read here.
Unit conversion used throughout: 1 µmol/kg/min of glucose = 0.180 mg/kg/min. FFM = fat-free mass. FFM-normalized rates are about 1.3× BW-normalized rates for a typical adult.

## Bottom line

1. **The paradoxical rise is real but small in a bolused T1D meal.** After a mixed meal, plasma glucagon in T1D rises about +20–40 pg/mL. In non-diabetic (ND) people it falls or rises less early. The difference is concentrated in the first ~2 h.
2. **Measured EGP in T1D after a bolused mixed meal is suppressed about 45%, against about 60% in ND.** The 2025 triple-tracer study puts the T1D-adult nadir at about 160 min. Over 0–300 min, total EGP is about the same as in ND, because T1D adults started from a lower baseline.
3. **Removing the glucagon rise in T1D did not change EGP measurably.** In Hinshaw 2016, pramlintide cut the 2-h glucagon excursion by about 14 pg/mL, but EGP iAUC was unchanged. The glucose benefit came from slower meal Ra (gastric emptying). This is the most direct test of the hypothesis, and it is negative.
4. **A glucagon-EGP term sized to the evidence explains about 0–10 mg/dL of the gap, not 30–40.** It is too weak and too poorly identified to close the observed plateau gap on its own.
5. **Check these before adding glucagon:**
   - **(a) EGP suppression depth.** Compare the model's insulin-only EGP suppression with the measured T1D curve: about 45% mean suppression over 5 h, nadir about 44% at about 2.5 h. If the model suppresses 70–100% during 1.5–3 h, that alone is about 0.7 mg/kg/min ≈ +30 mg/dL over 90 min. The evidenced cause is hepatic under-insulinization from peripheral (SC) insulin.
   - **(b) Bioavailability of meal Ra.** Elleri's "meal Ra" is total Ra minus clamp-visit EGP, so any meal-induced EGP excess is already inside it. Matching only its cumulative *fractions* does not check its *magnitude*.
   - **(c) Fat and protein.** These have evidenced 3–5 h effects.

## 1. Magnitude

### Plasma glucagon after a mixed meal

| Study | Population | Meal / insulin | Glucagon finding | Tag |
|---|---|---|---|---|
| Sherr 2014, Diabetes Care 37:1741, doi:10.2337/dc13-2612 (DirecNet) | 25 youth, T1D 1.5–12 mo (restudied yr 2); 20 ND children | MMTT (liquid, **no prandial insulin**), sampled to 240 min | Peak increment: **T1D 21 pg/mL [IQR 16–30] (yr 1), 25 [16–30] (yr 2) vs ND 9 [5–16]**. Fasting similar (44–46 vs 50 pg/mL). Assay SD 4 pg/mL. | [checked, full text] |
| Brown, Sinaii, Rother 2008, Diabetes Care 31:1403, doi:10.2337/dc08-0575 | 23 children, new-onset T1D, followed 0–12 mo | Standard mixed meal, no insulin | Meal-stimulated glucagon AUC **+37% over 12 mo** while C-peptide fell 45%. Percent rise over fasting went from 63±12% to 82±9%. **Peak at 30 min.** Fasting 40→46 ng/L. | [checked, full text] |
| Fredheim 2015, Diabetologia (online 2014) | 129 children (Danish remission cohort), 40 followed to 60 mo | Liquid MMTT | Postprandial glucagon **+160% from 1 to 60 mo**. Doubling postprandial PG → +21% glucagon. Doubling GLP-1 → +33% glucagon. | [checked, abstract via search summary; DOI not confirmed] |
| Romeres, Ruchi, Breton, Basu, DeBoer 2025, JCEM 110:730, doi:10.1210/clinem/dgae585 | T1D adults 13, T1D adolescents 21, ND adults 14 | Breakfast: 50% CHO (75 g adult / 50 g adol), 15% protein, 30% fat. **Usual prandial bolus.** Triple tracer. | **T1D adult:** baseline 27→peak 66 pg/mL at 154±80 min. iAUC 0–120 = **+1908** vs ND −57 pg/mL·min. iAUC 0–300 = 6317 vs ND 4293. **ND** peaks late (238 min) at 69. **T1D adolescents** barely rise: 10→18 pg/mL. | [checked, full text tables] |
| Hinshaw 2013, Diabetes 62:2223, doi:10.2337/db12-1759 | 19 C-peptide-negative T1D on pump | ~50 g CHO mixed meal (eggs, ham) ×3/day, usual bolus | Glucagon iAUC (0–360) higher at breakfast than lunch or dinner. Peak did not differ. Same diurnal pattern as ND. Numbers only in figure. | [checked, full text] |

**Reading:**
- Without prandial insulin (MMTT), T1D glucagon rises about +20–25 pg/mL early, against about +9 in ND.
- With a usual bolus and a protein- and fat-containing meal, T1D adults still rise early (0–2 h), while ND stay flat early and rise late (protein/fat-driven).
- The T1D–ND *difference* is about +15–20 pg/mL on average over the first 2 h.
- Old RIA values (Raskin & Unger 1978: 182 pg/mL on insulin alone → 60 on somatostatin) are not comparable to modern assays.

### EGP after a bolused mixed meal in T1D (the quantity the model needs)

**Romeres 2025 [checked, Table 2], µmol/kg FFM/min, mean±SD:**

| | ND | T1D adult | T1D adolescent |
|---|---|---|---|
| Baseline | 16.5±2.1 | **12.8±2.5 (= 2.30 mg/kgFFM/min)** | 21.1±7.6 |
| Nadir | 2.1±2.2 | **4.2±2.4 (0.76 mg)** | 2.5±2.7 |
| Nadir time (min) | 99±66 | **160±110** | 126±72 |
| iAUC 0–300 | −2982 | **−1711** | −3233 |
| Suppression % | −60±13 | **−44±17** | −47±31 |

- T1D adults average suppression over 0–300 min is 1711/300 = 5.7 µmol/kgFFM/min = **1.03 mg/kgFFM/min, about 45% of basal**.
- Absolute EGP AUC 0–300 is about 2129 (T1D adult) against about 1968 (ND) µmol/kgFFM. The difference is about 0.1 mg/kgFFM/min, which is small.
- The suppression percentage did not differ significantly between groups (P > 0.1).

**Hinshaw 2016, JCEM, doi:10.1210/jc.2015-3952 [checked, abstract].** 12 T1D, triple tracer, crossover ± pramlintide, over 2 h.
- Pramlintide lowered the glucagon excursion (Δ iAUC **1731 pg/mL·min ≈ 14 pg/mL mean**, P = 0.015).
- **EGP iAUC did not differ** (Δ −105.5 µmol/kgFFM ≈ 0.16 mg/kgFFM/min, P = 0.58).
- Meal Ra was lower (Δ 1196 µmol/kgFFM, P = 0.03), and plasma glucose iAUC fell by 444 mM·min.
- Authors' conclusion: the reduction came "by delaying meal rate of glucose appearance".
- **This is the best available bound: a ~14 pg/mL glucagon change had no detectable EGP effect over 2 h in T1D.**

**Hinshaw 2013 [checked].** In T1D, EGP was less suppressed at breakfast than at lunch, even though breakfast had more insulin and a larger glucagon iAUC. Suppression % P = 0.09. Absolute values appear only in figures.

**Elleri 2015, DOM, doi:10.1111/dom.12549 [checked, abstract].**
- Closed loop with meal announcement in adolescents, stable-label tracers.
- Total Ra 26.3 against 25.4 µmol/kg/min with standard and with −25% boluses (NS).
- EGP was not reported separately in the abstract.

### Conditions where glucagon does move glucose a lot (ND/T2D, somatostatin clamps)

**Shah, Basu, Basu, Rizza 1999, Am J Physiol 277:E283, doi:10.1152/ajpendo.1999.277.2.e283 [checked, abstract].**
- Design: ND subjects on somatostatin, with a "diabetic" (delayed, limited) insulin profile and a prandial glucose infusion. One arm held glucagon at basal; the other let it fall transiently.
- Result: peak glucose **11.9 vs 8.9 mmol/L** (+54 mg/dL), and glucose area 927 vs 546 mmol·L⁻¹·6 h. Cause: impaired EGP suppression.
- With a *normal* insulin profile the effect was small (9.1 vs 8.4 mmol/L).
- So glucagon matters a lot only when hepatic insulin is limited.

**Shah 2000, JCEM 85:4053, doi:10.1210/jcem.85.11.6993 [checked, abstract].**
- T2D, 50 g glucose. Glucagon was held at about 120 ng/L, or allowed to fall to about 70 ng/L for 2 h.
- Mean glucose was **10.9 vs 9.2 mmol/L (≈ +31 mg/dL)**, via glycogenolysis.
- Note: a ~50 pg/mL difference sustained for 2 h is 2–3× the T1D–ND meal difference.

**Rizza & Gerich 1979, JCEM 48:352, doi:10.1210/jcem-48-2-352 [checked, abstract].** Glucagon's EGP effect is **evanescent**.
- At 3 ng/kg/min, EGP rose from 1.8 to 2.5 mg/kg/min with a peak at 15 min, and was back to basal by 60 min despite sustained hyperglucagonemia.
- Stopping the glucagon dropped EGP below basal, so a sustained effect persists underneath.
- A model with a permanent glucagon gain would overstate the 1.5–4 h effect.

**Hinshaw 2015, AJP Endo, doi:10.1152/ajpendo.00236.2015 [checked, abstract].**
- In T1D, the EGP response to glucagon increased with dose and did not depend on euglycemia vs hypoglycemia.
- They built an in-silico glucagon action model from it. Parameter values were not read [unverified].

## 2. Time course

- **Glucagon onset and peak.** Without prandial insulin, the peak is at about 30 min (Brown 2008) [checked]. With a bolus and a mixed meal, T1D adults peak at about 154±80 min, with the early (0–120 min) excess the main T1D–ND difference (Romeres 2025) [checked]. Sherr sampled to 240 min; the peak timing there was not extracted.
- **EGP.** The T1D nadir is later than in ND (160 vs 99 min) [checked]. By 300 min EGP is still below basal in all groups (figure-only; [unverified] shape).
- **Glucagon → EGP lag.** S2013 models a delay [checked, abstract]. In humans the EGP response peaks within about 15 min of a glucagon step and wanes over about 60 min (Rizza & Gerich) [checked].
- **Fat and protein.** These act **late** (Paterson 2016, Smart 2013 below).
  - Protein-alone effects start at about 180 min and are still rising at 5 h.
  - The fat effect starts at about 210 min.
  - So they shape the 3–5 h period, not the 1–3 h plateau.

## 3. Dependence

**Protein.** Amino acids are a direct alpha-cell stimulus, and protein is also a gluconeogenic substrate.
- **Paterson 2016, Diabet Med, doi:10.1111/dme.13011 [checked, full text].** Whey alone, no insulin, 27 T1D.
  - 12.5–50 g: no significant excursion.
  - 75 g: +0.71 mmol/L at 180–240 min and **+1.65 mmol/L (≈ 30 mg/dL) at 240–300 min**.
  - 100 g: +1.06 at 180–240 and +1.72 at 240–300 mmol/L.
  - 25/75/100 g were *lower* than control at 60–120 min (about −1.1 mmol/L), consistent with an early protein-stimulated insulin/incretin effect or measurement setting.
- **Paterson 2019 systematic review, doi:10.1111/dme.14119 [checked, abstract].** Protein alone has an effect only at ≥ 75 g. With carbohydrate, ≥ 12.5 g protein changes the postprandial glucose. The effect window is 90–240 min. Fat added to high protein enhances it.

**Fat** acts through FFA-induced insulin resistance; the evidenced mechanism is not glucagon.
- **Smart 2013, Diabetes Care, doi:10.2337/dc13-1195 [checked, abstract].** Same carbs; 40 g vs 5 g protein; 35 g vs 4 g fat.
  - High protein: from 180 min, +2.4 vs +0.5 mmol/L.
  - High fat: from 210 min, +1.8 vs −0.5.
  - The two effects are additive.
- **Wolpert 2013, doi:10.2337/dc12-0092 [checked, abstract].** In closed loop, 60 g vs 10 g fat needed 12.6 vs 9.0 U (**+40%**) and still gave twice the AUC above 120 mg/dL over 18 h.

**Meal size and carbohydrate.** No dose-response of paradoxical glucagon to carbohydrate grams was found. Glucose itself paradoxically correlates *positively* with glucagon in T1D: a doubling of postprandial PG goes with +21% glucagon (Fredheim) [checked, abstract].

**Glycemia and insulin.** Shah 1999 shows the glucagon effect is large only when insulin is limited [checked]. Raskin & Unger 1978 (Am J Med companion) report that insulin restored a normal protein-glucagon response [unverified; from search snippet].

**Residual C-peptide and duration.** Abnormal responses are fully present in year 1 while C-peptide is still substantial (Sherr) [checked]. They grow with duration: +37% in year 1 (Brown) and +160% by 5 years (Fredheim) [checked].

**Age.** In Romeres 2025, T1D adolescents had almost no glucagon rise (peak 18 pg/mL) against 66 in adults [checked]. This conflicts with the pediatric MMTT studies, but those gave no insulin.

**Between-person spread.** CV is large:
- Romeres T1D-adult peak 66±33 pg/mL and iAUC 6317±3970 pg/mL·min (CV about 50–60%).
- EGP suppression 44±17% (CV about 40%).
- Hinshaw 2013: diurnal pattern is individual-specific [checked].

## 4. AID / adjunct studies: is postprandial hyperglycemia attributed to glucagon?

**Pramlintide.** Mechanisms are glucagon suppression plus slower gastric emptying.

| Study | Tag | Glucagon change | Glucose change | What separates the two mechanisms |
|---|---|---|---|---|
| Hinshaw 2016 | [checked] | −14 pg/mL mean | −444 mM·min iAUC | **Separated by tracer:** EGP unchanged, meal Ra lower. The glucose effect is gastric emptying. |
| Galderisi 2018, JCEM, doi:10.1210/jc.2017-02265 | [checked, abstract] | MMTT without bolus: peak increment 32±16 → 23±12 pg/mL | Glucose blunted (authors attribute to glucagon) | No tracer, so mechanisms not separated. Liraglutide: no glucagon or glucose change. |
| Heptulla 2005, Diabetes 54:1100, doi:10.2337/diabetes.54.4.1100 | [checked, abstract] | Suppressed (P < 0.02) | Reduced 0–180 min AUC | No tracer. A 60% bigger insulin bolus did not reduce early hyperglycemia. |

**Closed-loop studies.** Weinzimer 2012 (doi:10.2337/dc12-0330) and Sherr 2016 (doi:10.2337/dc16-0089) [checked, abstracts]:
- Pramlintide delayed the time to peak glucose: 1.5 → 2.5 h (Weinzimer) and 1.6 → 2.6 h (Sherr).
- It reduced excursions.
- Weinzimer did **not** measure glucagon and attributed the effect to gastric emptying.
- **No AID study found attributes the 2–4 h plateau specifically to glucagon.**

**Glucagon receptor antagonist.** Pettus 2022, Nat Med, doi:10.1038/s41591-022-02011-x [checked, abstract]:
- Volagidemab gave HbA1c −0.5% placebo-corrected and total daily insulin −7 U.
- This shows glucagon contributes to T1D glycemia overall, but it is not postprandial-specific.
- Boeder 2025 (dapagliflozin + volagidemab): mean glucose 131 vs 150 mg/dL [checked, abstract].

## 5. Existing simulator implementations

**UVA/Padova S2013.** Dalla Man et al. 2014, JDST 8:26, doi:10.1177/1932296813514502 [checked, abstract]:
- Glucagon kinetics: one compartment.
- **Secretion depends on plasma insulin, plasma glucose *below a threshold*, and the glucose rate of change.**
- Glucagon stimulates EGP with a delay.
- Hence **no postprandial paradoxical secretion**: above threshold, secretion is basal. The term is a counter-regulation (hypoglycemia) model.
- The equations from memory [unverified]:
  - EGP = k_p1 − k_p2·G_p − k_p3·I_d + ξ·X^H
  - dX^H/dt = −k_H·X^H + k_H·max(H − H_b, 0)
  - Static secretion ∝ σ·max(G_th − G, 0)/(I + 1)
  - Dynamic secretion ∝ δ·max(−dG/dt, 0)
- Parameter values were not read.

**S2017.** Visentin et al. 2018, JDST, doi:10.1177/1932296818757747 [checked, abstract]. It added intraday S_I variability, dawn phenomenon, new insulin PK and sensor error. It added **no meal-driven glucagon**.

## 6. What this means for the gap

The simulated drop at 2–3 h needs roughly 30–40 mg/dL of extra glucose held up over 1.5–4 h. A rough mass balance, before disposal and AID response, uses a glucose distribution volume of about 1.9 dL/kg. A 1 mg/kg/min appearance surplus for 1 h adds about 30 mg/dL.

| Candidate | Evidenced size | Plausible glucose effect | Verdict |
|---|---|---|---|
| Paradoxical glucagon → EGP | ≤ ~0.1–0.2 mg/kg/min over 0–2 h (Hinshaw 2016 null; Romeres absolute-EGP difference ≈ 0.1); evanescent | ~0–10 mg/dL, mostly early | Too small and the wrong timing to be the main term |
| EGP under-suppression from peripheral insulin (T1D 45% vs ND 60%; depends on the model's current depth) | 0.3–0.7 mg/kg/min **if** the model suppresses toward 70–100% | 15–35 mg/dL over 1.5–3 h | **Check first.** Calibrate against Romeres 2025 / Hinshaw 2013 EGP (evidenced, named: hepatic under-insulinization, Gregory 2020 doi:10.2337/dbi19-0026 [checked, abstract]) |
| Meal-Ra magnitude / "apparent bioavailability" (Elleri Ra_meal = Ra_total − clamp EGP, so it already contains any meal-driven EGP excess; LG +15%) | Unknown absolute value [unverified] | Up to about 15% more appearance in the tail | Check how the model normalizes total appearance |
| Fat / protein late effects | +1.5–2.4 mmol/L from 180–210 min on high-fat or high-protein meals | 30–40 mg/dL, but at 3–5 h | Relevant to the late tail, not the 1.5–3 h plateau |

## 7. Recommended model form (if a glucagon term is added at all)

Add it only as a **named, evidenced, small** component. It should not be tuned to close the gap.

```
ΔH(t)    = A_H · γ(t; k=2, peak t_p)            # meal-driven glucagon increment, pg/mL
             A_H scales with meal protein: A_H = A_0 + a_p·protein_g (see below)
dX/dt    = (ΔH(t) − X)/τ_H                       # hepatic action delay
EGP_gcg  = ξ · X · (1 − suppression_by_insulin)   # gated by hepatic insulin (Shah 1999: large only when insulin limited)
             with evanescence: multiply by exp(−t_since_rise/τ_ev), τ_ev ≈ 60 min (Rizza & Gerich 1979)
```

| Parameter | Value | Evidence |
|---|---|---|
| A_0 | ~20 pg/mL; per-person log-normal, CV ~0.6 | T1D–ND difference 12–20 pg/mL (Sherr; Romeres iAUC 0–120); spread from Romeres. Should rise with diabetes duration (+37% yr 1, +160% at 5 yr) and be near 0 in adolescents (Romeres). |
| t_p | 30 min (no/low insulin) to ~150 min (bolused) | Brown 2008; Romeres 2025 |
| Duration | ~4–5 h | Sampling windows 240–360 min |
| τ_H | ~15–30 min | Rizza & Gerich EGP peak at 15 min. S2013 delay value [unverified]. |
| ξ | ≤ 0.01 mg/kg/min per pg/mL (upper bound) | Hinshaw 2016: a 14 pg/mL change gave < 0.16 mg/kgFFM/min (NS). Shah 2000: ~50 pg/mL ↔ glycogenolysis-driven +31 mg/dL under limited insulin. |
| a_p | Not sizeable | Protein dose-response of *glucagon* in T1D was not found; Paterson measured glucose only. Use protein instead via a separate late gluconeogenic/glucose term if needed. |

**Implied size.** 20 pg/mL × 0.01 gives **≤ 0.2 mg/kg/min**, about 10% of basal EGP, and it wanes. That is about ≤ 10 mg/dL.

**Honest verdict.** Evidence is **too weak to size a meal-driven glucagon EGP term**, and the direct tracer test (Hinshaw 2016) is null. The plateau gap is better pursued through:
1. **Checking the model's insulin-driven EGP suppression depth and timing** against the T1D tracer EGP curves (about 44% nadir at about 160 min, about 45% mean over 5 h, SD about 17 points between persons). This is a calibration of an existing named component from its own evidence.
2. **Checking the absolute meal-Ra magnitude** that Elleri implies.
3. **Adding fat and protein late terms** (Smart 2013, Wolpert 2013, Paterson 2016) for the 3–5 h tail.

## Sources not read here [unverified]
- Raskin & Unger 1978 NEJM (only an abstract snippet via search); Gerich 1975 NEJM (somatostatin); Dobbs 1975 Science.
- Levetan 2003 and Fineman 2002 (pramlintide glucagon, T1D).
- Hinshaw 2015 parameter values.
- S2013 equation and parameter values.
- Elleri 2013 absolute bioavailability.
- Full text of Romeres Fig 2B (EGP time course).
