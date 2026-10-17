# 16 — GLP-1 RA / tirzepatide as adjunct in T1D: evidence for an additive-simulator component

> **How this was used (2026-10-16).** Requested by Pete ("add GLP-1 modeling; time of injection is an important factor"). It sizes `patient_sim/glp1.py`. The within-week rhythm comes from the kinetics; no study measured it.

Compiled 2026-10-16. Tags: **[checked]** = number read in the primary paper/label text this session;
**[abstract]** = read in abstract or registry; **[secondary]** = seen only in a secondary summary;
**[unverified]** = from memory or unconfirmed; **[derived]** = computed here from checked inputs.
Population is T1D unless labelled **(T2D)**, **(obesity)** or **(healthy)**.

---

## 1. Pharmacokinetics

| Agent | Schedule | tmax | t½ | Steady state | Escalation | Tag |
|---|---|---|---|---|---|---|
| Semaglutide s.c. (Ozempic/Wegovy) | weekly, any time of day, with or without food; missed dose OK within 5 d | 1–3 d | ~1 wk (165–184 h in PK trials) | 4–5 wk | 0.25 mg ×4 wk → 0.5 mg ×≥4 wk → 1 mg (→2 mg Ozempic; Wegovy 1.7 → 2.4 in 4-wk steps) | Ozempic label 2017 §2, §12.3 **[checked]**; Wegovy steps **[unverified]** |
| Semaglutide oral (Rybelsus) | daily, fasting | ~1 h (1–2 h) | ~1 wk (153–161 h) | 4–5 wk | 3 mg ×30 d → 7 → 14 mg | label text **[secondary]**; escalation **[unverified]** |
| Tirzepatide (Mounjaro/Zepbound) | weekly | 24 h median (8–72 h) | ~5 d (5–6 d in obesity) | 4 wk | 2.5 mg ×4 wk, then +2.5 mg every ≥4 wk to 5–15 mg | label **[secondary]** |
| Dulaglutide (Trulicity) | weekly | 48 h median (24–72 h) | ~5 d (4.7 d AusPAR) | 2–4 wk | 0.75 → 1.5 → 3 → 4.5 mg | label copies **[secondary]**; escalation **[unverified]** |
| Liraglutide (Victoza/Saxenda) | daily | 8–12 h | ~13 h | ~3 d | 0.6 → 1.2 → 1.8 mg weekly steps (Saxenda to 3.0 mg over 5 wk) | t½ label **[secondary]**; tmax review table **[secondary]** |

Semaglutide label extras **[checked]**: bioavailability 89%; Vd 12.5 L; CL 0.05 L/h; mean steady-state
concentration ~65 ng/mL (0.5 mg) and ~123 ng/mL (1 mg), dose-proportional; ~5 weeks to wash out.

**Within-week fluctuation.** No label or paper retrieved gives a steady-state peak/trough ratio.
One-compartment first-order-absorption model, absorption rate set from the labelled tmax **[derived]**:

| Agent | Assumed tmax | SS peak time after injection | Peak/trough | Concentration by day 0..7 relative to weekly mean |
|---|---|---|---|---|
| Semaglutide | 24 h | ~19 h | 1.82 | 0.71 1.28 1.17 1.06 0.96 0.87 0.78 0.71 |
| Semaglutide | 72 h (ka ≈ 0.029/h) | ~48 h | 1.40–1.45 | 0.79 1.08 1.14 1.10 1.03 0.95 0.87 0.79 |
| Tirzepatide | 24 h | ~20 h | 2.25 | 0.62 1.38 1.23 1.08 0.94 0.82 0.71 0.62 |
| Tirzepatide | 48 h | ~38 h | 1.89 | — |
| Dulaglutide | 48 h | ~38 h | 1.95 | 0.65 1.22 1.25 1.14 1.00 0.87 0.75 0.65 |
| Liraglutide (24 h interval) | 11 h | ~8 h | 1.63 | — |
| Oral semaglutide (daily) | 1 h | ~1 h | 1.11 | — |

So in plasma the weekly agents swing about ±20–40% around the mean, tirzepatide and dulaglutide more
than semaglutide. Oral semaglutide is effectively flat. Script:
`.../scratchpad/pk.py`. The population-PK absorption rates (Novo/Lilly popPK reports) were **not
retrieved**; semaglutide ka ≈ 0.03/h is from memory **[unverified]**.

---

## 2. Effects and their size in T1D

### 2a. Insulin dose. The best data come from two semaglutide RCTs on AID and one tirzepatide RCT

**Pasqua et al. 2025, Nat Med 31:1239** (doi 10.1038/s41591-024-03463-z), double-blind crossover, n=24
completers, semaglutide titrated 0.25 ×4 wk → 0.5 ×4 wk → 1 mg (11 wk), then 4 wk on McGill AID
(Ypsomed pump + Dexcom G6). Semaglutide vs placebo **[checked]**:
- TIR 3.9–10: 74.2 vs 69.4% (+4.8 pp, P=0.006). TBR<3.9 1.2 vs 1.1% (P=0.19); <3.0 0.3 vs 0.3%. Mean glucose 8.4 vs 8.8 mmol/L.
- TDD 46.1 vs 62.1 U/d (−11.3 U); change from baseline −14.6% vs +7.7%; 0.64 vs 0.77 U/kg/d.
- Basal 30.6 vs 35.0 U (−3.5 U); **bolus 15.2 vs 23.5 U (−6.2 U)**; basal share 64 vs 58%.
- **Carbs entered 95 vs 142 g/d (−36 g, about −25 to −33%)**.
- Weight −5.3 kg (−5.1%) placebo-adjusted at ~15 wk.
- Nausea in 89% (25/28) vs 7%; any GI AE 82% vs 26%.
- Final dose: 1 mg 67%, 0.5 mg 25%, 0.25 mg 8%.
- Commercial Control-IQ subgroup (n=12, during titration): TIR +4.3 pp, insulin −12.2 U.

**Pasqua, Tsoukas, Haidar 2026, Diabetes Obes Metab 28:427** (doi 10.1111/dom.70213), post hoc analysis
of the titration weeks, n=26 **[abstract]**:
- TDD, bolus **and carb intake fell significantly by day 7**. Basal fell significantly only by day 32.
- By day 77 the clinicians' pump settings had moved: **CR +4.1%, correction factor (ISF) +11.2%, basal rates −7.9%**.
- The authors attribute the drop mainly to reduced food intake, not to improved sensitivity.

**ADJUST-T1D: Shah et al. 2025, NEJM Evid 4(8)** (doi 10.1056/EVIDoa2500173), 26 wk, n=72, BMI≥30,
all on AID, semaglutide up to 1 mg **[abstract/secondary]**:
- Composite endpoint (TIR>70, TBR<4, ≥5% weight loss) met by 36% vs 0%.
- HbA1c −0.3, TIR +8.8 pp, weight −8.8 kg.
- Severe hypoglycemia 2 vs 2. No DKA.

**ADJUST-T1D post hoc: Karakus et al. 2026, Diabetes Care 49** (doi 10.2337/dc25-2249) **[checked]**:
- TDD change: −17.7% at wk 4, −20.9% at wk 8, −19.1% at wk 20, −22.6% at wk 26. Placebo +7.1% by wk 26.
- **Bolus: −22.9% (wk 4), −29.1% (wk 8), −30.5% (wk 26)**.
- **Basal: −11.7% (wk 4), −12.4%, −9.8%, −15.6% (wk 26)**. Basal/TDD rose 0.56 → 0.60 by wk 4 and 0.62 from wk 8.
- U/kg/d: 0.72 → 0.61 at wk 4 → 0.60 at wk 26. The fall is not only weight.
- **Mediation: of the TDD gap vs placebo, the share explained by weight loss was 17% at wk 4 (−2.3 of −13.3 U), 31% at wk 8, 50% at wk 20 and 48% at wk 26 (−10.5 of −21.9 U).** The direct drug effect held steady at −8.9 to −11.4 U/d.
- **Carbs: 137 → 116 g/d (wk 4) → 99 (wk 8) → 106 (wk 20) → 107 (wk 26)**, i.e. −15% at wk 4 and −22% to −28% thereafter.
- User-initiated boluses: 4.6 → 3.9 → 3.8 → 3.6 → 3.4 per day (−26% by wk 26). Placebo stayed at ~4.1–4.4.
- AID automatic correction boluses dipped (4.3 → 3.4/d at wk 4) and returned to 4.0 by wk 20.
- Bolus fell more than carbs (−30% vs −22%). The authors leave the cause open: a sensitivity effect in T1D is unknown.

**TIRTLE1: Snaith et al. 2026, Diabetes Care 49:161** (doi 10.2337/dc25-2379), phase 2, 12 wk,
tirzepatide 2.5 mg ×4 wk → 5 mg, n=24, mixed pump/MDI **[checked]**:
- TDD 67.4 → 43.2 U/d; ratio vs placebo 0.65 (**−35%**). Pump users −31%, MDI −34%.
- Basal 31.4 → 24.0 (ratio 0.75). **Bolus 33.8 → 15.8 (ratio 0.51)**.
- In pump users the drop was visible by wk 2. At wk 6 TDD was −42% vs placebo (exploratory).
- Energy intake −429 kcal/d vs placebo (P=0.05).
- TIR +8.4 pp (NS). TBR<54 +0.51 pp (NS). TBR<70 +1.8 pp (NS). MAGE −16.5.
- Weight −8.7 kg vs placebo. Nausea 50%, mostly after initiation or escalation.
- No severe hypoglycemia and no DKA. **Ketones were not reported.**

**Older and observational evidence:**
- **Karakus et al. 2024, Diabetes Ther** (doi 10.1007/s13300-024-01592-9), tirzepatide + Control-IQ, n=11, observational **[secondary]**:
  - TDD median 74 → 52 U within 2 mo, stable to 8 mo.
  - TIR +7%, A1c −0.5, weight −9%.
  - Suggests cutting TDD 25% at start.
- **ADJUNCT ONE: Mathieu 2016, Diabetes Care 39:1702** (doi 10.2337/dc16-0691), liraglutide, 52 wk, treat-to-target **[secondary]**:
  - At 1.8 mg: TDD −5% at wk 52 (−12% placebo-adjusted at wk 26, post hoc). Weight −4.9 kg. HbA1c ~−0.2 to −0.3.
  - Symptomatic hypo RR 1.31 (1.2 mg). Hyperglycemia-with-ketosis RR 3.96 (1.8 mg).
- **ADJUNCT TWO: Ahrén 2016, Diabetes Care** (doi 10.2337/dc16-0690 **[unverified DOI]**), 26 wk, insulin capped. At 1.8 mg: HbA1c −0.35, weight −4.8 kg, TDD −10% **[secondary]**.
- **Sarkar et al. 2014, Diabetes Care 37:666** (doi 10.2337/dc13-1473), exenatide 6 mo, crossover, clamp, n=13 **[checked]**:
  - Total 0.54 → 0.47 U/kg/d; meal insulin 0.26 → 0.18 U/kg/d; **basal unchanged**.
  - Postprandial glucose −7 mg/dL. Clamp insulin sensitivity improved (magnitude not extracted).
  - **No glucagon suppression.**

**Summary:**
- Semaglutide 1 mg on AID cuts TDD by ~15–23% (35% for tirzepatide 5 mg), within 1–2 weeks of starting.
- About two-thirds to three-quarters of the cut is bolus, tracking a 15–33% fall in entered carbs. Basal falls 8–16% (24% for tirzepatide), and later (significant by day 32).
- On AID, TIR rises 5–9 pp with no measurable rise in time below range.

### 2b. Gastric emptying

| Finding | Tag |
|---|---|
| Pooled scintigraphy, 5 RCTs (n=247), mostly T2D/obesity: T½ 138 vs 95 min (**+36 min, ×1.45**); I² 79%. Agent type and duration were not significant in meta-regression. Paracetamol tests (10 studies) showed no delay at AUC4h/5h. Hiramoto 2024, Am J Gastroenterol 119(6), PMID 38634551 | **[abstract]** |
| Semaglutide 1 mg, 12 wk (obesity): paracetamol AUC0–1h −27%, no change over 0–5 h. Delay is early-postprandial only. Hjerpsted 2018, DOM 20:610; label says "minor delay … early postprandial phase" | AUC figure **[secondary]**, label **[checked]** |
| Semaglutide 2.4 mg, 20 wk (obesity): paracetamol AUC0–5h +8%, no evidence of delay after weight adjustment. Friedrichsen 2021, DOM 23:754 (doi 10.1111/dom.14280) | **[secondary]** |
| Semaglutide, 12 wk, PCOS/obesity, scintigraphy: T½ 171 vs 118 min (+53 min) | **[abstract]** PMID 36511825 |
| Liraglutide 3 mg: solid T½ +70 min (median) at 5 wk, smaller at 16 wk (partial tachyphylaxis). Halawi 2017, Lancet Gastro Hep 2:890 (doi 10.1016/S2468-1253(17)30285-6). Maselli (n=136): 191.6 vs 105.9 min at 5 wk → 154.4 vs 111.4 at 16 wk | **[secondary]** |
| Tirzepatide: paracetamol Cmax −55% and tmax +1 h after the first 5 mg dose, "diminished after subsequent doses" (Zepbound label). Registry NCT04407234: Cmax 11,925 (none) → 5,314 (day 2 after 5 mg) → 8,099 ng/mL (day 37, 15 mg) | **[secondary]** |
| Tachyphylaxis, mechanism. Nauck 2011, Diabetes 60:1561 (doi 10.2337/db10-1318): IV GLP-1 slowed the 2nd meal 4 h later less than the 1st (healthy, n=9). Umapathysivam 2014, Diabetes 63:785 (doi 10.2337/db13-0951): continuous 24 h GLP-1 attenuated slowing; intermittent exposure preserved it. Vagal mechanism | **[abstract]** |
| Review: long-acting agents (lira, exenatide QW, sema) slow emptying with a declining effect; residual slowing persists at 4–8 wk; no data beyond ~16–21 wk; short-acting agents show no decline. GE explains ~1/3 of variance in the early (15–30 min) glucose rise. Jalleh et al. 2025, JCEM 110:1 (doi 10.1210/clinem/dgae719) | **[checked]** (qualitative) |
| T1D exenatide (Herold group; Ghazi 2014 Diabetes Care, doi 10.2337/dc13-1169): GE delayed and glucagon suppressed in a mixed meal. Raman 2010 (pediatric): GE delayed, no glucagon suppression | **[secondary]** |

**Summary:**
- The delay is largest after the first dose and after each escalation: T½ rises by ~+50 to +70 min, roughly ×1.5–1.7.
- With continuous weekly exposure it decays over weeks to a partial residual: ~+35–45 min at 12–16 wk on scintigraphy, a small early-phase-only effect on paracetamol.
- How much survives at 6+ months is **unknown**.

### 2c. Glucagon and postprandial glucose
- Semaglutide 1 mg **(T2D)**: fasting glucagon −8%, **postprandial glucagon −14–15%**, 24 h mean −12%. Counter-regulatory glucagon during induced hypoglycemia was not impaired. Ozempic label §12.2 **[checked]**.
- T1D: inconsistent. Exenatide shows suppression in Ghazi 2014 but none in Sarkar 2014 or Raman 2010. Liraglutide (Kuhadiya/Dandona 2016, Diabetes Care 39:1027) gave modest falls in mean glucose and "dose-dependent glucagon suppression" per press material **[secondary]**.
- Exenatide 6 mo in T1D: postprandial glucose −7 mg/dL **[checked]**.

### 2d. Appetite and energy intake
- Lab ad-libitum meals **(obesity)**:
  - Semaglutide 1 mg, 12 wk: total ad-lib intake −24% (Blundell 2017, DOM 19:1242, doi 10.1111/dom.12932) **[abstract]**.
  - Semaglutide 2.4 mg, 20 wk: lunch −35% (Friedrichsen 2021) **[secondary]**.
  - Tirzepatide 5 → 10 mg: lunch −59% (wk 3) and −72% (wk 6) from baseline; liraglutide −29 to −32% (Martin 2025, Nat Med 31:3141, doi 10.1038/s41591-025-03774-9) **[checked]**.
- **Free-living T1D on AID (the relevant number)**:
  - Entered carbs −15% at wk 4 and −22 to −28% at wk 8–26 (ADJUST post hoc).
  - −25 to −33% vs placebo at 15 wk (Pasqua).
  - Tirzepatide −429 kcal/d (TIRTLE1).
  - Lab single-meal reductions overstate free-living daily reductions.
- Meal events: user-initiated boluses −15% at wk 4, −26% at wk 26 (ADJUST). This is consistent with **fewer eating occasions as well as smaller ones**, but boluses ≠ meals.

### 2e. Weight
- T1D, semaglutide 1 mg: −5.3 kg at ~15 wk (Pasqua); −8.8 kg vs placebo at 26 wk (ADJUST).
- T1D, tirzepatide 5 mg: −8.7 kg vs placebo at 12 wk (TIRTLE1).
- Real-world 12 mo **[abstract]**: tirzepatide −10.9%, semaglutide −9.9%, liraglutide −7.1% (Dasman 2025, PMC12673458).
- Time course **(obesity, STEP-1)**: continued loss to a plateau at ~60 wk **[unverified]**.

---

## 3. Time since injection, and time of day

- **No study retrieved measures glucose, appetite, GE, nausea or insulin need as a function of days since a weekly injection.** All trials analyse by study week.
- Wharton 2022 (STEP 1–3, doi 10.1111/dom.14551) **[checked]**, analysed by study week only:
  - Nausea 44% vs 16%.
  - Prevalence rose during escalation, peaked ~wk 20 (2.4 mg escalates to wk 16), then fell.
  - Median nausea episode 8 d. Vomiting 2 d, diarrhoea 3 d.
- Consumer and clinic sources describe "worse 1–3 days after the shot" and "hunger returns on days 6–7". These are **anecdotal, no primary data**.
- Labels permit any time of day for weekly agents (Ozempic §2 **[checked]**) and daily liraglutide. **No outcome study comparing morning vs evening injection was found.**
- Physiological expectation **[derived, untested]**:
  - The weekly agents' plasma levels swing ±20–40% (§1).
  - Appetite and weight effects are dose-dependent but flatten at maintenance doses. SUSTAIN-1 weight was 0.5 mg −3.7 kg vs 1 mg −4.5 kg **[unverified]**.
  - That implies an Emax curve with EC50 ≈ 0.5× the 1 mg average concentration. The effect would then swing only about one-third as much as concentration: **±~7–12% of the effect, peaking days 1–3 and lowest on day 6–7**.
  - GE slowing may behave differently. Tachyphylaxis depends on continuous exposure (Umapathysivam), so a trough-to-peak rise may partly re-sensitize. This is mechanistically plausible but unmeasured for weekly agents.
- Daily liraglutide: the peak comes ~8–12 h post-dose. A morning dose peaks over the evening meal and an evening dose overnight/breakfast. No outcome data.
- **User report (Pete, 2026-10-16):** a person on tirzepatide (Mounjaro) noticed a difference on the day after the injection. This is
  one anecdote, but it is specific to the agent with the larger trough-to-peak swing (§1); see LESSONS 87 for what the model gives.
- Tirzepatide in T1D, phase 2 (Diabetes Care 49(1):161, doi via diabetesjournals.org/care/article/49/1/161) **[abstract only]**:
  - TDD −42% at 6 weeks in pump users (95% CI −59 to −18; exploratory, about 12 per arm). The drop was visible by week 2.
  - The drop is larger than Pasqua's real-world figure; the dose reached is the likely difference (not checked).

---

## 4. Hypoglycemia, ketosis, DKA

- On AID, no excess hypoglycemia:
  - Pasqua TBR unchanged, no severe hypoglycemia.
  - ADJUST severe hypo 2 vs 2; the post hoc recommends a **20–30% TDD cut at initiation** to avoid hypos.
  - TIRTLE1: TBR<54 +0.5 pp, NS.
- Without AID, liraglutide at 1.2 mg raised symptomatic hypo (RR 1.31) in ADJUNCT ONE. The ADJUST authors attribute this to the lack of a CGM/AID titration protocol (their discussion).
- Ketosis:
  - ADJUNCT ONE: hyperglycemia with ketosis RR 3.96 at 1.8 mg; DKA cases in the liraglutide arms only **[secondary]**.
  - Pasqua: **2/28 (7%) recurrent euglycemic ketosis without acidosis** on semaglutide; one judged drug-related, the other had food-borne illness plus pump failure **[checked]**.
  - ADJUST: no DKA; one high-ketone event and one infusion-site hyperglycemia.
- Observational:
  - OneFlorida+ target-trial emulation (medRxiv 2025, doi 10.1101/2025.11.10.25339908): DKA 13.5 vs 21.8 per 1,000 PY, HR 0.62 (0.33–1.17) **[abstract, preprint]**.
  - Single-centre: 0 DKA in 255 users over 1 yr **[secondary]**.
- Mechanism of concern: lower carbs and lower insulin, especially basal, plus nausea or vomiting. The simulator's ketone risk is the low-insulin, low-carb, vomiting day.
- DTS consensus 2024 (J Diabetes Sci Technol 19:191, doi 10.1177/19322968241291512): GLP-1 RA add-on on AID without increased severe hypo or DKA risk **[abstract]**.

---

## 5. Prevalence in T1D adults

- Epic Cosmos EHR, 943k T1D: GLP-1 RA prescribing 0.3% (2010) → **6.6% (2023)**; semaglutide 4.4%; tirzepatide 1.3% within 1 yr of approval. Li et al., JAMA 2024, jamanetwork.com/journals/jama/fullarticle/2825312 **[secondary]**; DOI not captured.
- T1D Exchange Online Registry, self-report: **5.8%** (470/8,053), 67% of them on semaglutide (ADA 2024 abstract). Registry article: 3% at launch → **8% in 2025**, Ozempic > Mounjaro > Wegovy **[secondary]**.
- Use is concentrated in adults with overweight or obesity.
- A reasonable 2025–26 prior for US adult T1D is **~7–10% on a GLP-1-class drug**, higher among BMI≥30. This is an extrapolation.

---

## 6. Recommended component model

The model is a named factor with literature-sized parameters. It does not replace settings, because the
controller does not know the drug. Retitration of the controller is a separate behavior: AID users'
clinicians cut settings (Pasqua day 77: CR +4%, ISF +11%, basal −8%).

### Per-person trait
```
glp1: {
  on: bool                       # prior ~7–10% of adult T1D (JAMA 2024; T1DX 2025), ↑ with BMI≥30
  agent: semaglutide_sc | tirzepatide | dulaglutide | liraglutide | semaglutide_oral
  maintenance_dose, escalation: label schedule (4-wk steps; lira weekly steps); max tolerated ~67% reach 1 mg sema (Pasqua)
  start_day (weeks_since_start)  # drives escalation + tachyphylaxis + weight
  injection_weekday, injection_hour   # weekly agents; daily agents: injection_hour
  nausea_susceptibility          # per-person; 50–89% have nausea at some point in T1D trials
}
```

### PK → normalized exposure
- Use a one-compartment model with first-order absorption, per agent: ke = ln2/t½, and ka from the labelled tmax.
- Default parameters: semaglutide t½ 165 h, ka 0.03/h; tirzepatide 120 h, 0.05–0.14/h; dulaglutide 113 h, 0.05/h; liraglutide 13 h, 0.14/h.
- Normalize X(t) = C(t)/C̄ss at the person's maintenance dose (dose-proportional; Ozempic §12.3).
- Then the drive is D(t) = X/(EC50+X)·(1+EC50), so D = 1 at maintenance steady state.
- EC50 ≈ 0.5 **[derived from unverified dose-response]**. Within-week variation then follows from PK; nothing is fitted.

### Time-varying multipliers (relative to the person off-drug)

| Channel | Form | Value at maintenance (1 mg sema) | Time course | Source |
|---|---|---|---|---|
| **Daily carb intake** | carbs × (1 − a·D) | a = 0.22–0.28 (sema 1 mg); tirzepatide ~0.30–0.35 **[derived from −429 kcal]** | Starts week 1 (day 7 significant), −15% at wk 4, full by wk 8 | ADJUST post hoc; Pasqua; TIRTLE1 |
| ↳ split | fewer eating occasions (×1 − 0.26·D on announced meals) plus smaller meals; the split is not identified, so pick ~half each | — | — | ADJUST bolus counts |
| **Gastric emptying** (carb appearance time-stretch in the plant's absorption model) | τ_abs × (1 + g·D·T(t)) | g ≈ 0.5–0.7 acute (T½ +50–70 min on ~100 min); T(t) decays to r ≈ 0.4–0.6 (+35–45 min at 12–16 wk) with time constant ~4–8 wk; reset toward 1 at each dose escalation | acute after first dose and escalations, partial tachyphylaxis | Hiramoto 2024; Halawi/Maselli; Jalleh 2025; Zepbound label |
| ↳ shape | apply mostly to the **early** phase (first 60 min). Paracetamol 0–1 h −27% with 0–5 h unchanged at 12 wk means a delayed onset, not a smaller total | — | — | Hjerpsted 2018; label |
| **Postprandial glucagon / EGP** | meal-time EGP rise × (1 − 0.15·D) | 0.15 is T2D; T1D evidence is contradictory. **Default off**, sensitivity arm only | — | Ozempic label (T2D) |
| **Insulin need, direct** (patient insulin-sensitivity multiplier, not via carbs) | S × (1 + s·D) | s ≈ 0.08–0.12 (basal −8 to −12% by wk 4–8; ISF setting +11% at day 77); tirzepatide s ≈ 0.15–0.25 (basal ratio 0.75) | develops over ~2–5 wk (basal significant by day 32) | ADJUST post hoc; Pasqua 2026; TIRTLE1 |
| **Insulin need, via weight** | S × (W0/W(t))^k, k ≈ 1 | W(t) = W0·(1 − w·(1 − e^(−t/τw))); sema 1 mg w ≈ 0.10–0.12, τw ≈ 15–25 wk; tirz w ≈ 0.12–0.15. Weight mediates ~half the TDD fall by wk 20–26 | slow | ADJUST mediation (48% at 26 wk); Pasqua; TIRTLE1 |
| **GI events** (behavior) | episodes with per-week hazard that peaks in escalation weeks and decays after maintenance; ~8 d median duration | during an episode: meal skip/shrink; vomiting after a bolused meal (carbs lost → hypo) | escalation-locked | Wharton 2022; Pasqua 89% nausea; TIRTLE1 50% |
| **Ketosis risk flag** | no glucose effect; log low-insulin × low-carb × GI-episode days | EU-ketosis 7% of users in 15 wk (Pasqua) | — | Pasqua; ADJUNCT ONE |

**Consistency check:** with a = 0.25 and s = 0.10, the sim should reproduce ADJUST's bolus −30%, basal −12 to −16% and TDD −20 to −23% at wk 26 under AID. Bolus falling more than carbs requires the s term, or reduced post-meal EGP. If the sim cannot reproduce this, a component is missing; do not tune.

### Honest gaps
1. **Within-week dynamics: no measured data** for any channel. The day-of-week swing follows only from PK plus an assumed Emax. Use it as a test hypothesis: does it show in BDDP? Users who log dose day could reveal a weekly periodicity in TDD/carbs.
2. GE tachyphylaxis for weekly agents past ~16–21 wk is unmeasured. Whether trough-to-peak re-sensitizes GE each week is unknown.
3. Whether the direct effect in T1D is true insulin sensitivity, glucagon/EGP, GE or residual C-peptide is unresolved (ADJUST authors). Its split into s vs glucagon is not identified from the TDD data.
4. Meal-frequency vs meal-size split of the intake drop.
5. Effects at higher doses (sema 2–2.4 mg, tirzepatide 10–15 mg) in T1D: there are no RCT data. Obesity-trial intake reductions are lab single-meal values and overstate free-living ones.
6. Missed or late doses, and the drug holidays common with supply shortages, are unstudied in T1D.
7. Nausea/vomiting interaction with bolus timing (pre-bolus then vomit) has no quantitative T1D data. It is the plausible hypo mechanism.
8. Liraglutide time-of-day effects: none measured.

### Primary DOIs
- Pasqua 2025 Nat Med: 10.1038/s41591-024-03463-z
- Pasqua 2026 DOM: 10.1111/dom.70213
- Shah 2025 NEJM Evid: 10.1056/EVIDoa2500173
- Karakus 2026 Diabetes Care: 10.2337/dc25-2249
- Snaith 2026 Diabetes Care: 10.2337/dc25-2379
- Karakus 2024 Diabetes Ther: 10.1007/s13300-024-01592-9
- Mathieu 2016: 10.2337/dc16-0691
- Sarkar 2014: 10.2337/dc13-1473
- Jalleh 2025 JCEM: 10.1210/clinem/dgae719
- Nauck 2011: 10.2337/db10-1318
- Umapathysivam 2014: 10.2337/db13-0951
- Halawi 2017: 10.1016/S2468-1253(17)30285-6
- Blundell 2017: 10.1111/dom.12932
- Friedrichsen 2021: 10.1111/dom.14280
- Martin 2025 Nat Med: 10.1038/s41591-025-03774-9
- Wharton 2022: 10.1111/dom.14551
- DTS consensus: 10.1177/19322968241291512
- Hiramoto 2024: PMID 38634551
- Garg 2024 DTT: 10.1089/dia.2023.0490 (not read)
