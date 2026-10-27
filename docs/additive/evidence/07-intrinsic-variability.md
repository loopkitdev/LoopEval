# Evidence 07 — Intrinsic (controlled-condition) within-person variability

Scope: the project rule allows an intrinsic variability term only if its size comes from
**controlled-condition repeats** (same person, same protocol, measured more than once). This file
collects that evidence for insulin sensitivity (SI), meal response and absorption, overnight basal
need, subcutaneous insulin action and diurnal SI. Free-living variability is listed only as a
**target** that the named factors must reproduce. It is never an input.

**Verification legend.** A plain citation means the number was checked against the abstract or
full text during this review (Europe PMC, PMC or the publisher). **[unverified]** means it was not
checked against the primary text. **[derived]** means it was computed here from verified numbers,
or is a modelling proposal rather than a value from a paper.

**One reading rule for every row.** A test-retest CV is the sum of biological variability, assay
or estimation error, and residual uncontrolled factors such as diet the day before, activity,
sleep and the menstrual phase. It is therefore an **upper bound** on the intrinsic term, never a
point estimate of it.

---

## Summary table

| # | Quantity | Within-person CV / spread | Design | Population, n | Repeat interval | Ref |
|---|---|---|---|---|---|---|
| 1a | Clamp M / GIR (2 h, 60 µU/mL) | median **5.8 %** (range 2.6–22) | 3 clamps | Healthy, n = 7 | 48 h and 14 d | Soop 2000 |
| 1b | Clamp M (40 mU/m²/min) + tracer | **10.3 ± 8.5 %**. Basal EGP 6.7 %; clamp-suppressed EGP 54 % | 2 clamps, inpatient ward, double-blind | Healthy men, n = 10 | 3–4 d | Le 2009 |
| 1c | Clamp GIR₆₀₋₁₂₀/FFM (1 mU/kg/min) | **14.7 %** (r = 0.70) | 2 clamps | Healthy 60-y men, n = 32 | 2 wk | Bokemark 2000 |
| 1d | Clamp M at 120 and 180 min | **8 % and 6 %** (healthy); 14 % and 5 % (hypertensive) | 2 study days | Healthy n = 18; hypertensive n = 6 | not stated in abstract | Morris 1994 (MD thesis) |
| 1e | Clamp SI | **13.6 %** | 2 clamps | Healthy adults with a T2D parent, n = 90 | ~2 y (includes real drift) | James 2020 |
| 1f | IVGTT minimal-model SI | **20.2 ± 3.2 %** (range 6–44 %). SG 25 % | 3 FSIGTs, fixed diet, limited activity | Healthy men, n = 11 | over 12 d | Steil 1994 |
| 1g | IVGTT minimal-model SI | **14.4 %** (r = 0.78) | 2 tests after 3 d of standard diet | Healthy young men, n = 15 | 3 wk | Ferrari 1991 |
| 1h | IVGTT minimal-model SI (Scheen group) | **16.8 ± 3.4 %** | 2 tests | Healthy lean, n = 7 | 1 wk | Duysinx 1994 |
| 1i | **T1D** repeat SI (clamp or meal tracer) | **No study found** | — | — | — | gap |
| 2a | Time to postprandial peak, standard breakfast | within-person SD **38.9 min** vs between-person SD 18.5 min. ICC 0.18. Total TTP 104.5 ± 26.6 min | 6 home days, identical meal, same site, bolus 15 min pre-meal, dose by ICR | **T1D children** 8–15 y; 22 in variance analysis | consecutive days | Bell 2021 |
| 2b | iAUC to duplicate meals (CGM) | ICC **0.17–0.28**. Duplicate r ≈ 0.45. Within-subject variability ≈ variability between different meals | Ward-fed; each meal served twice | Healthy, n = 30 (1,189 responses) | ~1 wk | Hengist 2025 |
| 2c | PPGR to two standard meals, each eaten twice | Within-person r = 0.99; between-person CV ≈ 32 %. **No within-person CV reported** | Matched insulin | T1D adults, n = 120 | 4 occasions | Campbell & Ajjan 2020 (conference abstract) |
| 2d | Gastric-emptying T½ (breath test) | **21.0 %** | 3 tests | **T1D**, n = 20 (+ 10 healthy) | separate days | Aigner 2021 |
| 2e | Gastric-emptying T½ (scintigraphy) | intra **20 %** (inter 40 %). 12 % if normal GE, 28 % if rapid | 2 tests | Symptomatic patients (21 with diabetes), n = 60 | ~15 d | Desai 2018 |
| 2f | Gastric-emptying T½ (breath test) | **7.9 %**; lag 7.5 % | 2 tests | Overweight/obese men, n = 15 | 7 d | Horner 2014 |
| 2g | Meal Ra for identical meals (tracer) | **No repeat-day tracer study found.** Hinshaw 2013 found no B/L/D difference in meal Ra (each meal on a different day) | — | T1D, n = 19 | — | Hinshaw 2013 |
| 3a | Overnight i.v. insulin need to hold euglycaemia | "highly reproducible on three separate nights". **No CV given in the abstract** | Harvard-pump i.v. insulin, 3 nights | T1D, n = 114 (subset repeated) | separate nights | Perriello 1991 |
| 3b | Overnight EGP, glucose slope | Group means only: EGP at 3 am 18.6 vs 17.4 µmol/kg FFM/min; glucose slope 0.4 vs 0.3 mmol/L/h (P = 0.40). Within-subject spread not reported | 2 consecutive nights, standard dinner, usual basal | T1D CSII, n = 16 | 1 d | Mallad 2015 |
| 3c | Overnight closed-loop delivery, **free-living (TARGET)** | night CV **31 ± 4 %**, day 22 %, TDD **17 ± 3 %** | 12-wk home hybrid CL | T1D adults, n = 32 | daily | Ruan 2016 |
| 3d | Same, inpatients (not T1D, illness) | daily 30 %; overnight 56 % | Fully closed-loop in hospital | T2D / new hyperglycaemia, n = 67 | daily | Boughton 2021 |
| 4a | s.c. **aspart** PD (clamp) | AUC-GIR₀₋₁ₕ **21.6 %**, ₀₋₂ₕ 17.9 %, total **18.4 %**, GIRmax 21.0 % | 3 × 0.2 U/kg, clamp | **T1D**, n = 46 | 3–15 d washout | Heise 2017 |
| 4b | s.c. **faster aspart** PD (clamp) | AUC-GIR₀₋₁ₕ 25.5 %, ₀₋₂ₕ 20.4 %, total **18.3 %**, GIRmax 19.3 % | same | same | same | Heise 2017 |
| 4c | s.c. aspart vs regular human insulin PD | GIRmax 16 ± 10 %; t-max 11 ± 6 %; decline to half-max 11 ± 5 % (aspart). Overall 10–30 % | 4 × 0.2 U/kg, 600-min clamp | Healthy men, n = 10 (aspart) / 9 (RHI) | 4 study days | Heinemann 1998 |
| 4d | s.c. RHI PK/PD | AUC-INS ~26 %, Cmax ~42 %, AUC-GIR ~32 % [derived from table; column labels ambiguous] | 3 × 0.1 U/kg, clamp | **T1D**, n = 14 | separate days | Hompesch 2008 |
| 5a | Diurnal SI (B/L/D) | No group pattern in T1D (P = 0.34). Pattern "specific to the individual". Each meal tested **once, on a different day** | Triple-tracer, Latin square, 3 consecutive days | T1D, n = 19 | — | Hinshaw 2013 |
| 5b | Visentin's N(1, 0.2) SI multiplier | σ = 0.2 is set from the **SI estimation precision (~20 %)**, so that deviations up to 40 % count as random. It is not a measured biological repeat | Model choice on Hinshaw data (one virtual day per subject) | — | — | Visentin 2015 |
| 5c | Diurnal SI, healthy | SI higher at breakfast than lunch or dinner | Same design as 5a | Healthy, n = 20 | — | Saad 2012 |

---

## Notes

### 1. Insulin sensitivity, repeated in the same person

- **Clamp, healthy adults.** Repeat CV is **6–15 %** over days to weeks: Soop 5.8 %, Morris 6–8 %,
  Le 10.3 %, Bokemark 14.7 %. Over ~2 years it is 13.6 % (James 2020), and that figure includes
  real drift. Under the strictest condition (inpatient, 3–4 days apart), Le 2009 still saw M fall
  from the first clamp to the second, which the authors attribute to accumulated inactivity. Even a
  ward protocol therefore carries a residual named factor (activity), so an intrinsic CV is below
  ~10 %.
- **Minimal-model SI.** Repeat CV is higher, **14–20 %** (Ferrari 14.4 %, Duysinx 16.8 %, Steil
  20.2 %). Part of the excess over the clamp is estimation error: SI from a 12-sample protocol had
  a CV of 27.7 % against 20.2 % from 30 samples in the same subjects (Steil 1994). The SI
  estimation precision quoted by Padova (~20 %, Visentin 2015) is of the same size as the whole
  repeat CV. Minimal-model repeat CVs are therefore dominated by measurement and are not usable as
  the biological term.
- **T1D.** No repeat clamp or repeat meal-tracer SI study in T1D was found. The closest data are
  Faggionato 2024 (47 T1D adults, three 23-h visits with frequent plasma sampling), but the visits
  are not described as identical-meal repeats and no between-visit SI CV is reported. Steady-state
  EGP under a clamp is poorly repeatable (CV 54 %, Le 2009). This is mostly a tracer-precision
  problem at near-zero EGP, not evidence of a large biological term.
- **Free-living SI as a contrast.** Ruan 2017 (TBME) estimated a day-to-day CV of **38–79 %** for
  SI from 12 weeks of home closed-loop data (n = 8). That is free-living data passed through a
  model. It is a target the named factors must reproduce, not an input.

### 2. Identical meal with identical insulin

- **No T1D study was found that holds meal, insulin dose, timing and setting fixed and reports a
  within-person CV of glucose AUC or peak.** Bell 2021 is the closest: identical home breakfast on
  6 days, same site and timing, ICR dosing (dose therefore identical if the meal was finished).
  The within-person SD of time to peak, **39 min**, exceeded the between-person SD (18.5 min);
  ICC 0.18. This is semi-controlled, since the evening before, activity and sleep were not fixed.
- Healthy adults fed duplicate meals on a metabolic ward show **poor CGM reproducibility**
  (iAUC ICC 0.17–0.28; Hengist 2025). Within-subject variability for the same meal was about as
  large as between different meals. Part of this is CGM imprecision: for Dexcom G4 the imprecision
  index exceeded the duplicate-meal SD.
- The Campbell & Ajjan 2020 T1D abstract reports r ≈ 0.99 between repeats but no within-person CV.
  It cannot size a term [abstract only, not peer-reviewed in full].
- **Absorption.** No repeat-day tracer measurement of meal Ra for an identical meal was found.
  The usable proxy is gastric emptying: T1D T½ CV **21 %** across 3 tests (Aigner 2021, breath
  test, which carries its own analytic error). Scintigraphy CV is 20 % (Desai 2018). In
  overweight healthy men the breath-test CV is 7.9 % (Horner 2014). Aigner also found that
  day-to-day fasting-glucose swings of 4.8 mmol/L did **not** change GE. The variability is not
  explained by the glucose-level factor.

### 3. Overnight basal requirement under controlled conditions

- The older i.v. euglycaemia studies are the controlled design wanted. Perriello 1991 (Bolli
  group, n = 114) states that nocturnal insulin requirements and the dawn phenomenon were **"highly
  reproducible on three separate nights"**, but the abstract gives no CV. The full text is
  paywalled and not checked. Skor 1983 and 1985 (Biostator, n = 5) studied successive nights under
  different hormone infusions, not identical repeats. Dawn magnitude is +19 ± 0.5 % in 101 of 114
  subjects (Perriello 1991). The pattern is a repeatable, named diurnal factor, not noise.
- Mallad 2015 (two consecutive standardized nights, n = 16) reports only group means: EGP and the
  glucose slope did not differ between nights. Within-subject spread is not reported.
- The Cambridge overnight closed-loop CRC studies (Hovorka 2010, 2011) were crossover CL against
  CSII, not identical repeats. No overnight-requirement CV under CRC conditions was found in them.
- The free-living numbers are **targets**: overnight CL delivery CV 31 %, TDD 17 % (Ruan 2016);
  young children about +10 points (Dovc 2019). The fact that night CV is nearly twice the day CV in
  free living, while controlled i.v. nights are "highly reproducible", suggests most overnight
  variability comes from the named carry-over factors: the previous day's meals and fat, late
  boluses, exercise, alcohol and sleep [derived reading, not measured].

### 4. Subcutaneous insulin action repeatability (rapid analogues)

- **T1D clamp, aspart and faster aspart:** within-subject CV of total AUC-GIR **18 %**, early
  (0–1 h) **22–26 %**, GIRmax 19–21 % (Heise 2017, n = 46, 3 repeats, 3–15 d apart). The two
  analogues did not differ.
- Healthy volunteers, aspart (Heinemann 1998): **10–20 %** for the summary measures. PD
  variability exceeds PK variability. Heinemann's 2002 review puts regular insulin at 15–25 % and
  analogues as no better.
- A clamp GIR repeat includes **both** absorption and SI day-to-day variability. If SI
  contributes ~10 % (section 1), the absorption/PK share is about √(18² − 10²) ≈ **15 %**
  [derived]. Early-action CV (~22–25 %) is larger than total-action CV, which is consistent with
  timing (absorption rate) jitter rather than amount jitter.
- None of these used CSII boluses, the infusion-set wear day, or the site. Those are named device
  factors (file 03) and must not be folded into this term.

### 5. Diurnal SI under controlled conditions

- Hinshaw 2013 and Saad 2012 tested each meal slot **once**, on three consecutive days in a Latin
  square. The breakfast/lunch/dinner contrast is therefore confounded with day-to-day variability,
  and no repeat-day diurnal study was found. In T1D the group pattern was not significant
  (P = 0.34). The "individual-specific" patterns could be partly day-to-day noise plus SI
  estimation error, because "low" SI was 40 ± 23 % of "high".
- Visentin 2015's seven-class SI patterns are each built from one subject-day. The multiplicative
  N(1, 0.2) noise is justified by SI **estimation precision** ("estimated with a precision of 20 %,
  on average"; "a 40 % difference is imputable to a fortuitous variation"), **not** by repeated
  measurement. **It is a measurement-error allowance, not a measured biological variability.**
  S2017 (Visentin 2018) carries the same patterns and states that long-term SI variability is
  future work.
- The Cambridge simulator (Wilinska 2010) uses ±5 % sinusoidal SI and flux oscillations with a 3 h
  period, and 20 % inter-occasion variability of carbohydrate bioavailability. **No source is
  given for either.**

### What the evidence can justify as an intrinsic term [derived proposal]

| Term | Size | Basis | Caveat |
|---|---|---|---|
| Day-level SI multiplier (lognormal, held for ~a day) | CV **≈ 8 %** (defensible range 6–15 %) | Repeat clamps, healthy, days to weeks apart | Upper bound: includes assay error and residual activity/diet. No T1D repeat |
| Per-dose s.c. absorption-rate jitter | CV **≈ 15 %** on rate/timing | T1D repeat clamp GIR 18 % minus the SI share | Injection, not CSII. Early-action CV ~22–25 % |
| Per-meal gastric-emptying jitter | CV **≈ 10–20 %** on T½ | GE repeats: 7.9 % (healthy, breath), 20–21 % (T1D/patients) | Includes test error. No repeat-day Ra tracer study exists |
| Diurnal SI pattern | **No intrinsic random term justified.** Model as a named, per-person deterministic profile; dawn rise ~+19 % | Hinshaw/Saad single-day designs; Perriello reproducible dawn | Visentin σ = 0.2 is estimation error |
| Overnight basal noise | **None beyond the SI term** | Controlled i.v. nights "highly reproducible" | Number not verified (paywall) |

Check against the free-living target: an 8 % day-level SI CV alone would give a TDD CV of roughly
8 %, about half of the 17 % TDD and a quarter of the 31 % overnight CV observed in home closed
loop. The remainder must come from named factors [derived].

---

## References

- Aigner L, Becker B, Gerken S, Quast DR, Meier JJ, Nauck MA. Day-to-day variations in fasting
  plasma glucose do not influence gastric emptying in subjects with type 1 diabetes. *Diabetes
  Care* 2021. doi:10.2337/dc20-1660
- Bell E, Binkowski S, Sanderson E, et al., Davis EA. Substantial intra-individual variability in
  post-prandial time to peak in controlled and free-living conditions in children with type 1
  diabetes. *Nutrients* 2021;13:4154. doi:10.3390/nu13114154
- Bokemark L, Frödén A, Attvall S, Wikstrand J, Fagerberg B. The euglycemic hyperinsulinemic clamp
  examination: variability and reproducibility. *Scand J Clin Lab Invest* 2000.
  doi:10.1080/00365510050185010
- Boughton CK, Daly A, Thabit H, et al. Day-to-day variability of insulin requirements in the
  inpatient setting: observations during fully closed-loop insulin delivery. *Diabetes Obes Metab*
  2021. doi:10.1111/dom.14396
- Campbell M, Ajjan R. Significant interpersonal postprandial glucose variability in type 1
  diabetes. *Diabet Med* 2020;37(S1) (conference poster). doi:10.1111/dme.21_14245 (supplement
  DOI)
- Desai A, O'Connor M, Neja B, et al., Bharucha AE. Reproducibility of gastric emptying assessed
  with scintigraphy in patients with upper GI symptoms. *Neurogastroenterol Motil* 2018.
  doi:10.1111/nmo.13365
- Dovc K, Boughton C, Tauschmann M, et al. Young children have higher variability of insulin
  requirements: observations during hybrid closed-loop insulin delivery. *Diabetes Care* 2019.
  doi:10.2337/dc18-2625
- Duysinx BC, Scheen AJ, Gerard PL, Letiexhe MR, Paquot N, Lefebvre PJ. Measurement of insulin
  sensitivity by the minimal model method using a simplified IVGTT: validity and reproducibility.
  *Diabete Metab* 1994. PMID 7843475 (no DOI)
- Faggionato E, Schiavon M, Ekhlaspour L, Buckingham BA, Dalla Man C. The minimally-invasive oral
  glucose minimal model… *IEEE Trans Biomed Eng* 2024. doi:10.1109/tbme.2023.3324206
- Ferrari P, Alleman Y, Shaw S, Riesen W, Weidmann P. Reproducibility of insulin sensitivity
  measured by the minimal model method. *Diabetologia* 1991. doi:10.1007/bf00403291
- Heinemann L, Weyer C, Rauhaus M, Heinrichs S, Heise T. Variability of the metabolic effect of
  soluble insulin and the rapid-acting insulin analog insulin aspart. *Diabetes Care* 1998.
  doi:10.2337/diacare.21.11.1910
- Heinemann L. Variability of insulin absorption and insulin action. *Diabetes Technol Ther* 2002.
  doi:10.1089/152091502320798312
- Heise T, Stender-Petersen K, Hövelmann U, et al., Haahr H. Pharmacokinetic and pharmacodynamic
  properties of faster-acting insulin aspart versus insulin aspart across a clinically relevant
  dose range in subjects with type 1 diabetes. *Clin Pharmacokinet* 2017;56:649–660.
  doi:10.1007/s40262-016-0473-5
- Hengist A, Ong JA, McNeel K, Guo J, Hall KD. Imprecision nutrition? Intraindividual variability
  of glucose responses to duplicate presented meals in adults without diabetes. *Am J Clin Nutr*
  2025;121:74–82. doi:10.1016/j.ajcnut.2024.10.007
- Hinshaw L, Dalla Man C, Nandy DK, et al., Basu A. Diurnal pattern of insulin action in type 1
  diabetes: implications for a closed-loop system. *Diabetes* 2013. doi:10.2337/db12-1759
- Hompesch M, McManus L, Pohl R, et al., Heinemann L. Intra-individual variability of the metabolic
  effect of a novel rapid-acting insulin (VIAject) in comparison to regular human insulin.
  *J Diabetes Sci Technol* 2008. doi:10.1177/193229680800200406
- Horner KM, Byrne NM, Cleghorn GJ, King NA. Reproducibility of gastric emptying in overweight and
  obese males. *Clin Nutr* 2014. doi:10.1016/j.clnu.2013.09.002
- James D, Umekwe N, Edeoga C, Nyenwe E, Dagogo-Jack S. Multi-year reproducibility of
  hyperinsulinemic euglycemic clamp-derived insulin sensitivity… POP-ABC. *Metabolism* 2020.
  doi:10.1016/j.metabol.2020.154263
- Le DS, Brookshire T, Krakoff J, Bunt JC. Repeatability and reproducibility of the
  hyperinsulinemic-euglycemic clamp and the tracer dilution technique in a controlled inpatient
  setting. *Metabolism* 2009. doi:10.1016/j.metabol.2008.09.029
- Mallad A, Hinshaw L, Dalla Man C, Cobelli C, Basu R, et al., Basu A. Nocturnal glucose
  metabolism in type 1 diabetes: a study comparing single versus dual tracer approaches.
  *Diabetes Technol Ther* 2015;17:587–595. doi:10.1089/dia.2015.0011
- Morris AD. Studies of insulin sensitivity using the euglycaemic hyperinsulinaemic clamp. MD
  thesis, University of Glasgow, 1994. https://theses.gla.ac.uk/id/eprint/75661 (abstract only)
- Perriello G, De Feo P, Torlone E, et al., Bolli GB. The dawn phenomenon in type 1 diabetes:
  magnitude, frequency, variability, and dependency on glucose counterregulation and insulin
  sensitivity. *Diabetologia* 1991. doi:10.1007/bf00404020 (three-night reproducibility statistic
  [unverified]: full text not read)
- Ruan Y, Thabit H, Leelarathna L, et al., Hovorka R. Variability of insulin requirements over 12
  weeks of closed-loop insulin delivery in adults with type 1 diabetes. *Diabetes Care* 2016.
  doi:10.2337/dc15-2623
- Ruan Y, Wilinska ME, Thabit H, Hovorka R. Modeling day-to-day variability of glucose-insulin
  regulation over 12-week home use of closed-loop insulin delivery. *IEEE Trans Biomed Eng* 2017.
  doi:10.1109/tbme.2016.2590498
- Saad A, Dalla Man C, Nandy DK, et al. Diurnal pattern to insulin secretion and insulin action in
  healthy individuals. *Diabetes* 2012. doi:10.2337/db11-1478
- Skor DA, White NH, Thomas L, Shah SD, Cryer PE, Santiago JV. Examination of the role of the
  pituitary-adrenocortical axis… in variable nocturnal insulin requirements in insulin-dependent
  diabetes. *Diabetes* 1983. doi:10.2337/diab.32.5.403
- Soop M, Nygren J, Brismar K, Thorell A, Ljungqvist O. The hyperinsulinaemic-euglycaemic glucose
  clamp: reproducibility and metabolic effects of prolonged insulin infusion in healthy subjects.
  *Clin Sci* 2000. doi:10.1042/cs0980367
- Steil GM, Murray J, Bergman RN, Buchanan TA. Repeatability of insulin sensitivity and glucose
  effectiveness from the minimal model. *Diabetes* 1994. doi:10.2337/diab.43.11.1365
- Visentin R, Dalla Man C, Kudva YC, Basu A, Cobelli C. Circadian variability of insulin
  sensitivity: physiological input for in silico artificial pancreas. *Diabetes Technol Ther*
  2015. doi:10.1089/dia.2014.0192
- Visentin R, Campos-Náñez E, Schiavon M, et al. The UVA/Padova type 1 diabetes simulator goes
  from single meal to single day. *J Diabetes Sci Technol* 2018. doi:10.1177/1932296818757747
- Wilinska ME, Chassin LJ, Acerini CL, Allen JM, Dunger DB, Hovorka R. Simulation environment to
  evaluate closed-loop insulin delivery systems in type 1 diabetes. *J Diabetes Sci Technol* 2010.
  doi:10.1177/193229681000400117

## Day-to-day persistence of insulin sensitivity (searched 2026-10-19)

No study measures the lag-1-day autocorrelation of insulin sensitivity in people with T1D. Found: variability spreads
only — model-estimated day-to-day SI variability 38–79% over 12 weeks of home closed loop (8 adults; Cambridge
repository 1810/257036), overnight insulin requirement CV 31% vs total daily 17% (32 adults, multicentre closed-loop
trial); OpenAPS Autosens estimates a sensitivity ratio from the last 8–24 h of CGM deviations, without published
validation of its persistence. `day_rho` stays 0 (no evidence); the donors' TDD ac1 (0.09 in 13-day blocks) and night CV
are targets the named multi-day factors (illness, menstrual cycle, intake persistence, settings edits) must reproduce
together (LESSONS 330, 363).

- **Heinemann L. Variability of insulin absorption and insulin action. *Diabetes Technol Ther* 2002;4:673–682** **[checked,
  full text, 2026-10-20]**: rapid-acting / regular insulin intra-individual CV 10–20% for summary measures (healthy, clamps),
  inter-individual 5–20% higher; GIR at each time 60–360 min CV 25–30% across occasions; daily-life T1D identical meals:
  post-meal excursion CV 48–79%. Basis of A4c (LESSONS 417).

- **Heise T, Stender-Petersen K, Hövelmann U, et al. Pharmacokinetic and pharmacodynamic properties of faster-acting insulin
  aspart versus insulin aspart across a clinically relevant dose range in subjects with type 1 diabetes. *Clin Pharmacokinet*
  2017;56:649–660. doi:10.1007/s40262-016-0473-5** **[checked, ESM Table S2, 2026-10-20]**: 46 T1D, clamps, insulin aspart at
  0.1 / 0.2 / 0.4 U/kg: tmax 65.7 / 72.1 / 75.2 min, t(early 50% Cmax) 29.9 / 32.0 / 36.1 min, onset of appearance 10.0 / 8.8 / 7.3
  min, Cmax 155 / 287 / 691 pmol/L (slightly more than dose-proportional). Larger doses peak later, weakly: time ∝ dose^~0.1
  (0.13 for 0.1→0.2, 0.06 for 0.2→0.4). Sizes A4's dose dependence (`dose_beta`) at β ≈ 0.1 (LESSONS 155 tested 0.25 / 0.4).
