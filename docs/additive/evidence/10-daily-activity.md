# Everyday (non-structured) physical activity — evidence for the additive patient simulator

Compiled 2026-10-15 for the `additive` role. Scope: how much incidental and unstructured activity people with T1D do, in what bouts, at what time of day, and what it does to glucose, plus how published simulators represent it. It ends with a recommended model for the "walking bouts" component.

**Labels.** **[M]** = measured and reported in the cited source. **[I]** = my inference or arithmetic from measured numbers. **[J]** = judgement with no direct evidence. **[NF]** = searched for and not found.

**Why this file exists.** The simulator currently draws lnN(4 bouts/day), ~12 min each, at intensity ~0.25, with half of them within 2 h after a meal. The effects are insulin-independent uptake 3.0·I mg/kg/min, insulin sensitivity ×(1+0.8·I) and absorption ×(1+0.5·I), and the delayed sensitivity effect switches on only above I = 0.35. Donors have about 2× the simulator's rate of daytime lows not preceded by any bolus in 4 h (0.19 vs 0.09 per day).

---

## 1. How much daily activity, and in what shape

### 1.1 General population (accelerometry)

| Quantity | Value | Source |
|---|---|---|
| Steps/day, US adults (NHANES 2005–06, hip ActiGraph) | **6,540 ± 106** censored (counts <500 cpm removed); 9,676 uncensored **[M]** | Tudor-Locke C, Johnson WD, Katzmarzyk PT. *Med Sci Sports Exerc* 2009;41(7):1384–91. doi:10.1249/MSS.0b013e318199885c |
| Time by cadence, US adults | 0 spm 4.8 h; 1–59 spm 8.7 h; 60–79 spm 16 min; 80–99 spm 8 min; 100–119 spm 5 min; 120+ spm 2 min; **≥60 spm ≈ 30 min/day**. "Walking at 100+ spm was rare." **[M]** | Tudor-Locke C et al. *Prev Med* 2011;53(3):178–81. doi:10.1016/j.ypmed.2011.06.004 |
| Light "lifestyle" activity (760–2019 cpm) | **110.4 ± 1.6 min/day**, 3,476 steps/day; strongly correlated with MVPA minutes (r = 0.84) **[M]** | Camhi SM, …, Tudor-Locke C. *J Phys Act Health* 2011;8(3):382–9. doi:10.1123/jpah.8.3.382 |
| MVPA guideline adherence, adults | **<5%** meet 30 min/day (in ≥10-min bouts) by accelerometer **[M]** | Troiano RP et al. *Med Sci Sports Exerc* 2008;40(1):181–8. doi:10.1249/mss.0b013e31815a51b3 |
| Overall acceleration, UK Biobank (wrist, n ≈ 96,600) | 31.2 ± 9.1 mg at age 45–54; −7.5% per decade **[M]**. Between-person **CV ≈ 0.29** **[I]** (SD/mean) | Doherty A et al. *PLoS One* 2017;12(2):e0169649. doi:10.1371/journal.pone.0169649 |

### 1.2 T1D versus peers

| Quantity | Value | Source |
|---|---|---|
| Adults <3 months from diagnosis vs healthy | MVPA **37.4 vs 52.9 min/day** (adjusted). More light activity and less sedentary time in T1D. **No weekend difference** in MVPA **[M]** | Matson RIB et al. *Front Public Health* 2018;6:360. doi:10.3389/fpubh.2018.00360 |
| Youth with T1D vs peers (meta-analysis, 35 studies, 2,452 T1D) | **−12.7 min/day MVPA**, **+63 min/day sedentary**; OR 0.44 for meeting guidelines; lower fitness (d = −0.52) **[M]** | Huerta-Uribe N et al. *Diabetes Res Clin Pract* 2023;200:110697. doi:10.1016/j.diabres.2023.110697 |
| Adults with T1D, pedometer, 13 days (BETTER registry, n = 383) | **8,027 ± 3,512 steps/day** (between-person CV ≈ 0.44 **[I]**). 42% <7k, 33% 7–10k, 25% >10k. Group means 5,010 / 8,285 / 12,862 **[M]** | Garré TI et al. *Diabetes Obes Metab* 2026;28(4):2908–18. doi:10.1111/dom.70473 |
| Adults with T1D, steps (T1DEXI, n = 464) | Analysed by days <7k / 7–10k / >10k. Mean steps not in the abstract **[NF]** | Turner LV et al. *Diabetologia* 2024;67(6):1009–22. doi:10.1007/s00125-024-06127-2 |
| VO2max, T1D vs controls | **32 ± 9.2 vs 39 ± 7.9 mL/kg/min** (≈ 9.1 vs 11.1 METs) **[M]**. Romeres 2021 T1D group: 28.7 ± 10.4 **[M]** | Muñoz-Hernandez L et al. *J Diabetes* 2025;17(12):e70164. doi:10.1111/1753-0407.70164 |

### 1.3 Bout structure

- **Walking is very fragmented.** In 10 employed adults over 14 days (StepWatch, 10-s windows), **60% of walking bouts lasted ≤30 s**, and a 2-min bout made up only 1% of bouts. 40% of bouts were <12 steps and 75% <40 steps. Half of all rest periods were ≤20 s **[M]**. Orendurff MS et al. *J Rehabil Res Dev* 2008;45(7):1077–89. doi:10.1682/jrrd.2007.11.0197
- **Continuous stepping ≥5 min happens less than once a day** on average in adults aged 50–74 (iDATA, activPAL, n = 814). The average person has >3 bouts ≥2 min per day. Over the 7 days, 97% had at least one bout ≥2 min, 65% one ≥6 min and 55% one ≥10 min **[M]**. Speirs C, Dunlop MD, Roper M, Granat M. *Sensors* 2023;23(14):6555. doi:10.3390/s23146555
- **Distribution shape.** Active-period durations follow a universal stretched-exponential (gamma-type) distribution once rescaled by each person's mean. Rest-period durations follow a power law **[M]**. Nakamura T et al. *Phys Rev Lett* 2007;99:138103. doi:10.1103/PhysRevLett.99.138103. Sedentary bouts are power-law distributed (Chastin SF, Granat MH. *Gait Posture* 2010;31(1):82–6. doi:10.1016/j.gaitpost.2009.09.002) **[M]**. Exponents for *active* bouts at a glucose-relevant time scale (5–30 min): **[NF]**.
- **What this means for the simulator [I]:** a "bout" of 12 continuous minutes is not how people move. What matters for glucose is activity accumulated over a 10–30 min window, such as an errand or a walk with short stops. Glucose responds with a 5–15 min lag (HR filter time constants of 5–10 min in Dalla Man 2009 and Jaloli 2023, §4), so sub-minute fragmentation does not need modelling. Model **"activity episodes"** whose duty cycle is below 100%, rather than continuous bouts.

### 1.4 Time of day and weekday/weekend

- **UK Biobank hourly profile** (women; men similar), mean acceleration by 6-hour block: **00–06 4.4 mg, 06–12 38.6, 12–18 44.3, 18–24 26.4** **[M]**. Normalised, that is **0.04 / 0.34 / 0.39 / 0.23** of the day's activity **[I]**. The afternoon is the peak, and age differences are largest in the afternoon and evening **[M]** (Doherty 2017).
- **Weekday vs weekend:** UKB weekday 28.5 vs weekend 28.0 mg (women), effect size d ≈ 0.10 **[M]**. Matson 2018 found no weekend MVPA difference between T1D and controls **[M]**. Seasonal effect d ≈ 0.21 (winter lower) **[M]**.
- **Coupling to meals:** **[NF]**. No source gives the share of incidental activity in the first 2 h after eating. The "half within 2 h after a meal" assumption stays **[J]**.
- **T1D-specific time-of-day distribution of unstructured sessions:** T1DEXI analyses use it as a predictor (Dhaliwal 2025), but the distribution itself was not in the retrieved text **[NF]**.

---

## 2. Unstructured activity in T1D: frequency, duration, intensity, glucose effect

### 2.1 T1DEXI adults: real-world, self-logged sessions ≥15 min (Dhaliwal 2025)

Dhaliwal M, Tang K, Aiello EM, Zaharieva DP, Lal RA, …, Riddell MC, Qin Y. "Variation in Hypoglycemia Risk During Real-World Physical Activity in Adults with Type 1 Diabetes: Insights from T1DEXI." *Diabetes Technol Ther* 2025 (online 3 Dec), 28(5):428–43. doi:10.1177/15209156251400209. Sample: 8,171 sessions from 404 pump users (55% AID), structured study sessions excluded. **All [M]:**

- **Frequency:** 20.2 ± 12.6 sessions per participant over 24.9 days, i.e. **≈ 0.8/day [I]**, with between-person CV ≈ 0.62 **[I]**. PA on **60% of days**, 1.3 sessions per PA day, 53.6 ± 18.6 min per PA day.
- **Duration:** mean 40.8 ± 22.8 min. 31% were 15–30 min, 48% 30–60 min and 21% 60–120 min. Sessions under 15 min were not counted.
- **Type:** **walking/dog walking accounts for 42% of sessions** (3,421). Aerobic 65%, mixed 21%, anaerobic 13%.
- **ΔCGM over the session:** overall **−20 ± 45 mg/dL**. Aerobic −24.5 (median −21), mixed −14, anaerobic −10. **Walking: median −18 mg/dL.** Outdoor chores: median −20.
- **By starting glucose (mean ΔCGM):** 50–100: **+8.6** (21% of sessions with hypo); 100–150: **−11** (4.1%); 150–200: **−33** (2.4%); 200–250: **−52**; 250–300: **−67**.
- **By IOB:** <1 U **+5.6**; 1–2 U **−7.5**; 2–3 U **−22.7**; ≥3 U **−32.3**. Hypo rates 3.0 / 5.3 / 6.1 / 7.5%.
- **Hypoglycemia** (≥15 min <70 during PA): 6.2% of sessions overall. By duration: 2.8% (15–30 min), 5.8% (30–60), 12.2% (60–120). Closed loop 5.7% vs open loop 6.9%. Sessions with hypo started at a median 93 mg/dL (vs 140 for those without).

### 2.2 T1DEXI / T1DEXIP: short 10–30 min bouts starting above 180 mg/dL (Pemberton 2025)

Pemberton JS, Russon CL, …, Andrews RC. *Diabet Med* 2025;42(12):e70146. doi:10.1111/dme.70146. Commentary: *Diabet Med* 2026;43(1):e70163. doi:10.1111/dme.70163. Design: 1,546 bouts from 482 people (363 adults, 119 adolescents), each matched within-person to a non-PA period on starting glucose, rate of change, IOB and CV. **All [M]:**

- Median bout **23 min** (IQR 20–30). Intensity: **light 50%, moderate 42%, vigorous 8%** (adults by accelerometer: 45 / 47 / 8).
- Over 20 min, PA **−2.2 mmol/L (≈ −40 mg/dL)** vs matched control −0.3, so the **net is −1.9 mmol/L (≈ −34 mg/dL) in 20 min**, about −1.7 mg/dL/min. With insulin or carbs in the window excluded: ≈ −2.0 mmol/L.
- **No significant difference by intensity or activity type.**
- Larger drops with: falling glucose at onset (−0.90 mmol/L per 0.1 mmol/L/min), higher start (−0.16 per mmol/L), higher IOB (−0.56 per 0.1 U/kg), longer duration (−0.05 per min), higher CV, higher BMI.
- Hypoglycemia within 20 min: 1.4% (vs 0.1% control). Not analysed below 180 mg/dL, and nothing measured beyond 20 min.
- **Caveat [I]:** this is observational, with residual confounding by choice of when to move. People may walk *because* they are high and have just corrected; matching on IOB and ROC reduces this but does not remove it.

### 2.3 Other real-world T1D data

- **T1DEXI structured sessions** (30 min, at home, 497 adults): ΔG **−18 ± 39 (aerobic), −14 ± 32 (interval), −9 ± 36 (resistance) mg/dL**, similar across closed loop, pump and MDI. TIR in the 24 h after exercise was 76% vs 70% on non-exercise days **[M]**. Riddell MC et al. *Diabetes Care* 2023;46(4):704–13. doi:10.2337/dc22-1721
- **T1DEXIP adolescents** (251 people, 3,738 logged activities over ~10 days, ≈ **1.5/day [I]**): glucose 163 ± 66 → 148 ± 66 mg/dL (**−15 mg/dL**). Median duration **40 min** (IQR 20–75). Mean/peak HR **109 / 130 bpm**. Bigger drops with IOB >0.05 U/kg, glucose already falling, start >150 mg/dL, prior-24h TIR >70% and "noncompetitive" activity **[M]**. Riddell MC et al. *Diabetes Care* 2024;47(1):132–9. doi:10.2337/dc23-1548
- **RAPPID** (86 adults on AID — 780G, Control-IQ, CamAPS — over 1 month, 954 logged sessions; inclusion required ≥2 sessions/week): mean 1.5 ± 1.1 h. Intensity low 27%, moderate 61%, high 9%. **20% of sessions had hypoglycemia**. TBR <70 was 1% pre-exercise, **6% during**, 5% early recovery (+3 h), 4% late recovery, vs **3% outside exercise periods**. A temp target was used in 73% of sessions, pre-exercise carbs in 36% (median 20 g) and intra-exercise carbs in 27% (median 25.5 g) **[M]**. No mg/dL change or IOB reported **[NF]**. Joubert M et al. *Diabetes Obes Metab* 2025;27(12):7221–31. doi:10.1111/dom.70122

### 2.4 Daily step count vs glycemia and lows

- **T1DEXI, within person** (464 adults, 45% HCL). On days above 10k steps, TIR was 75% vs 73% on days below 7k. **TBR <70 was 3.1 ± 3.2% on >10k days**, 0.3 and 0.4 points higher than on 7–10k and <7k days (so roughly 2.8% and 2.7% **[I]**), i.e. ≈ **+15% relative TBR [I]**. TDD was 0.52 vs 0.55 U/kg (**−5%**). Effects were larger with HbA1c ≥7%. Between persons there was no TIR difference **[M]**. Turner 2024 (above). The ADA 2023 summary reported the TIR gains as significant only for standard pump and HCL users **[M]** (HCPLive conference report).
- **BETTER** (cross-sectional): no difference in level 1 or level 2 hypo frequency across step groups (~2.1 L1 per 3 days; ~8 L2 per month) **[M]** (Garré 2026). Only 13% of this cohort used AID.
- **Activity and glycemic variability:** in 311 adults (wrist accelerometer, 7 days), overall activity volume was **not associated** with any variability measure. The *intensity gradient* (more time at higher intensity) was associated with lower mean glucose (β −1.01), CONGA, J-index, HBGI and GRADE **[M]**. Al Kandari J, Al Ozairi E, Irshad M, Varghese A, Gray SR. *Eur J Sport Sci* 2024;24(2):210–6. doi:10.1002/ejsc.12062. A direct study of CV or TBR versus steps in AID users: **[NF]**.
- **Share of AID hypoglycemia events attributable to everyday activity:** **[NF]**.

---

## 3. Light activity and glucose: controlled studies

- **Post-meal walking at 1.2 mph** (≈ 1.9 km/h, about 3× basal metabolic rate). Inpatients walked 33.5 min then sat 26.5 min, for 5–6 h of walking a day. Over 270 min, T1D iAUC was **7.5 vs 18.4 mmol/L** after walking vs inactivity (−59%). In healthy controls it was 4.5 vs 9.6. T1D peak glucose was 14.5 vs 15.4 mmol/L. Hypoglycemia was not reported **[M]**. Manohar C, Levine JA, …, Kudva YC. *Diabetes Care* 2012;35(12):2493–9. doi:10.2337/dc11-2381
- **SIT-LESS:** 3-min self-paced walks every 30 min over a 7-h day (≈ 6 min/h, ~40 min in total), in 32 inactive adults with T1D. Mean glucose **8.2 → 6.9 mmol/L (≈ −23 mg/dL)**, TIR **71.5 → 85.1%**, with **no increase in hypoglycaemia** **[M]**. Campbell MD, Alobaid AM, Hopkins M, Dempsey PC, Pearson SM, Kietsiriroje N, Churm R, Ajjan RA. *Diabetes Obes Metab* 2023;25(12):3589–98. doi:10.1111/dom.15254
- **Step-informed bolus (UVA).** "Activity on board" is a weighted sum of 5-min step bins over ~13.5 h, with a decay shape taken from post-exercise glucose uptake. The population activity factor is **AF = 3,000 steps per U** of insulin-equivalent **[M]**. Ozaslan B, Patek SD, Fabris C, Breton MD. *Comput Methods Programs Biomed* 2020;197:105757. doi:10.1016/j.cmpb.2020.105757. Fabris C, Ozaslan B, Breton MD. *Sensors* 2019;19(24):5386. doi:10.3390/s19245386. Their simulation assumed **8 steps/min at rest** between 06:30 and 21:00 (35% between-subject variability) **[M]**. **[I]** With ISF ≈ 40–60 mg/dL/U, 1,000 steps above routine ≈ **13–20 mg/dL** of glucose lowering. A 20-min walk (~2,000 steps) gives ≈ −25 to −40 mg/dL, which agrees with Pemberton's net −34 in 20 min.
- **Insulin absorption during exercise** (Pitt JP et al. *Front Endocrinol* 2020;11:573275. doi:10.3389/fendo.2020.573275, reviewing small older studies) **[M]**:
  - regular insulin injected in the thigh, during leg cycling: **×1.6–1.7** (Ferrannini 1982; Kolendorf 1979);
  - abdomen: ×1.2, not significant;
  - aspart via pump in the abdomen during 30 min of moderate cycling: free insulin +6 pmol/L (McAuley 2016).
  - **[I]** For walking (I ≈ 0.25) with abdominal pump sites, the simulator's ×(1+0.5·0.25) = ×1.13 is plausible, and if anything an upper bound.

### 3.1 Mechanism magnitudes (tracer and clamp)

Romeres D, Schiavon M, Basu A, Cobelli C, Basu R, Dalla Man C. *Am J Physiol Endocrinol Metab* 2021;321(1):E122–9. doi:10.1152/ajpendo.00084.2021. Protocol: 60 min at **65% VO2max** under clamp, 6 T1D and 6 non-diabetic adults. **All [M]:**

- **Insulin-independent disposal +53 to +82%** in T1D (+67 to +97% in non-diabetic), with an immediate on/off effect.
- **Insulin-dependent disposal +81 to +155%** in T1D. This was larger than in non-diabetic subjects (+10 to +40%, p < 0.05) and **delayed, persisting after exercise**.
- Best model: p1·(1 + p5·E), and SI·(1 + p6·Ea) with Ea a first-order lag of E. The parameter values are in the supplement **[NF]**.

---

## 4. How published simulators represent activity

| Model | Input | Structure and values | Notes |
|---|---|---|---|
| **UVA/Padova exercise** — Breton MD. *J Diabetes Sci Technol* 2008;2(1):169–74. doi:10.1177/193229680800200127. Dalla Man C, Breton MD, Cobelli C. *J Diabetes Sci Technol* 2009;3(1):56–67 (PMC2769836) | HR above basal (HRb = 70) | Y: dY/dt = −(Y − ΔHR)/T_HR with **T_HR = 5 min**. Insulin-independent utilisation Vm0·(1 + **β·Y**), **β = 0.01 /bpm**. Insulin action (1 + **α·Z**), α = 3×10⁻⁴. Z switches on through a Hill function f(Y) with threshold **a·HRb (a = 0.1, i.e. ~7 bpm)** and n = 4, has T_in = 1 min, and decays with **T_ex = 600 min** (slow-off). The γ term (10⁻⁷) lowers Km by the integrated ΔHR **[M]** | "Mild" = 1.5×HRb, "moderate" = 2×HRb. **The delayed sensitivity effect starts at very low intensity** (a few bpm above rest), unlike our 0.35 threshold **[I]** |
| **Jaloli & Cescon 2023** (arXiv 2307.07923) | HR − HRb | Dalla Man-type with τ_h = 10 min, τ_θ = 180 min, γ = 1.2, ε = 0.01. Individual β 0.014–0.166 /bpm. **HR→BG transfer function: K median 2.72 mg/dL per bpm (IQR 1.45–5.17), T 104 min (60–539), delay 15 min**, fitted on 9 adults doing 45 min at 50–55% VO2max fasting **[M]** | Ten-fold spread in β across 9 people **[M]**: between-person variability is large |
| **Resalat 2019 OHSU** — Resalat N et al. *PLoS One* 2019;14(7):e0217301. doi:10.1371/journal.pone.0217301 (exercise model from Hernández-Ordoñez 2008) | PVO2max from HR + accelerometer (MET/METmax) | Peripheral uptake multiplier MPGU = 1 + Γ·PAMM/35, MPIU = 1 + 2.4·PAMM, hepatic production MHGP = 1 + Γ·PAMM/155, with Γ̄ = 0.006·PVO2max² + 1.2264·PVO2max − 10.1958 and PAMM = 0.5 **[M]** | Validated only on 45 min at 60% VO2max. Γ̄ is negative below ~8% VO2max, so it has **no meaningful light-activity regime [I]** |
| **Deichmann 2023** — Deichmann J, Bachmann S, Burckhardt MA, Pfister M, Szinnai G, Kaltenbach HM. *PLoS Comput Biol* 2023;19(2):e1010289 | Accelerometer counts (ActiGraph) | Y = AC filtered with τ = 5 min. Rest/exercise switch at **a_Y = 1,500 counts/min** (Hill n = 20). Moderate ≥2,296 cpm. High ≥5,600 cpm (~75–80% VO2max). **%VO2max = 0.0135·AC + 1.72**. Insulin-independent uptake and production rise with Y; glycogen depletion term. **Prolonged sensitivity Z with τ_Z = 600 min (up to 48 h)** **[M]** | Fitted on 5 free-living children. Threshold 1,500 cpm ≈ 22% VO2max ≈ I ≈ 0.1–0.15 **[I]**, so even light-moderate activity triggers prolonged sensitivity |
| **Hobbs 2022** — Hobbs N, Samadi S, Rashid MM, …, Cinar A. *Comput Methods Programs Biomed* 2022;226:107153 | Intensity-driven (multivariable AP simulator) | Equations and values not retrieved **[NF]** | — |
| **UVA step-based "activity on board"** (Ozaslan 2020) | Steps in 5-min bins | Additive, decaying over ~13.5 h. AF 3,000 steps/U **[M]** | Dosing aid, not a body model |
| **Tidepool simple metabolism model / Loop effect model** | — | No activity term found **[NF]** | — |

---

## 5. Between-person variability

**Total activity [M]:**
- UKB acceleration CV ≈ 0.29 (Doherty 2017).
- Steps CV ≈ 0.44 in adults with T1D (BETTER, 8,027 ± 3,512) and ≈ 0.51 in the BCS70 cohort (9,210 ± 4,676, reported in the iDATA/activPAL literature search).
- Logged sessions per person CV ≈ 0.62 (T1DEXI, Dhaliwal 2025).
- The step categories split people roughly 40 / 35 / 25% into <7k, 7–10k and >10k (BETTER).

**Glucose response per activity:**
- Individual HR-to-uptake gain β ranges ten-fold (0.014–0.166 /bpm) across 9 adults **[M]** (Jaloli 2023).
- In T1DEXIP, drops were larger with lower HbA1c, shorter disease duration, less hypo fear and lower BMI **[M]**.
- In Pemberton 2025, drops were larger with higher BMI and slightly larger with older age **[M]**.

**Within-person day-to-day variability of activity:** T1DEXI participants had a logged session on 60 ± 20% of days **[M]**. A day-to-day CV of steps: **[NF]**.

**Activity and glucose variability:** volume is not associated with variability, and intensity distribution is weakly associated (Al Kandari 2024) **[M]**.

---

## 6. Reading the evidence against the current model

1. **Volume is about right [I].** The current model gives 4 × 12 ≈ 48 min/day at I ≈ 0.25. The evidence:
   - NHANES has ~30 min/day at ≥60 spm and ~110 min/day of "lifestyle" light activity.
   - T1DEXI has ~32 min/day of logged sessions ≥15 min (0.6 × 53.6) in an active, self-selected cohort.

   The shortfall in no-bolus lows is therefore unlikely to come from too few walking minutes. The likelier causes are listed below.
2. **The effect is zero-order where the evidence says it scales with glucose and insulin [I].**
   - Real drops scale steeply with starting glucose (Dhaliwal: −11 mg/dL from 100–150, −52 from 200–250) and with IOB (+6 at IOB <1 U, −32 at ≥3 U).
   - Romeres measured both pathways as *proportional* increases of disposal: GE·(1+·) and SI·(1+·).
   - A constant 3.0·I mg/kg/min under-states drops at high glucose and high insulin, and over-states them near hypoglycemia, where the body's own falling uptake protects.
3. **Delayed sensitivity is gated too high [I].** Both the UVA/Padova model (threshold ~7 bpm above rest) and Deichmann (≈22% VO2max ≈ I 0.12) let light-moderate activity start the slow-off sensitivity state, with τ 600 min. Our threshold of I > 0.35 means everyday walking never contributes to later lows. Corroboration:
   - T1DEXI TDD is −5% on >10k-step days;
   - TBR is +15% relative on those days;
   - RAPPID TBR stays above the non-exercise baseline for ≥3 h after sessions (5% early recovery and 4% late recovery, vs 3%) **[M]**.
4. **Acute insulin-dependent gain is low [I].** Romeres' T1D insulin-dependent increase at I ≈ 0.6 is +81 to +155%, i.e. ~1.4–2.6 per unit I if linear. The current 0.8 per unit I sits below that range. Linearity in I is itself **[J]**.
5. **Episodes are too uniform [I].** Real episodes come from a gamma/lognormal duration distribution with a long tail. In Dhaliwal 21% of logged sessions last 60–120 min, and hypo risk scales with duration (2.8 → 12.2%). Fixed ~12-min bouts miss the long errands, shopping, gardening and dog walks that produce most activity lows.

---

## 7. Recommended activity model

### 7.1 Intensity units

Define **I = %VO2-reserve = (MET − 1)/(METmax − 1)**. That equals %HR reserve, (HR − HRrest)/(HRmax − HRrest), per Swain DP, Leutholtz BC. *Med Sci Sports Exerc* 1997;29(3):410–4 **[M]**, with known divergence in prolonged exercise.

- **METmax** per person: T1D adults VO2max 32 ± 9 mL/kg/min → **METmax ≈ 9 ± 2.6** (Muñoz-Hernandez 2025) **[M→I]**. Draw lnN(median 9, σ 0.25) and lower it with age (UKB −7.5% activity per decade is a proxy) **[J]**.
- **Activity METs** (2024 Adult Compendium, pacompendium.com; Herrmann SD et al. *J Sport Health Sci* 2024;13(1):6–12, doi:10.1016/j.jshs.2023.10.010) **[M]**. The I value in brackets is for METmax 9 **[I]**:
  - household walking or strolling <2 mph: 2.3 (**I ≈ 0.16**)
  - 2.0–2.4 mph: 2.8 (**0.22**)
  - dog walking or 2.5 mph: 3.0 (**0.25**)
  - 2.8–3.4 mph: 3.8 (**0.35**)
  - brisk 3.5–3.9 mph: 4.8 (**0.47**)
- **Cross-check [I]:** T1DEXIP mean HR 109 bpm during activity, with assumed rest ~75 and max ~200, gives %HRR ≈ 0.27.

### 7.2 Two layers of daily activity

#### (A) Activity episodes: walks, errands, chores — a Poisson process per person

| Parameter | Recommendation | Basis |
|---|---|---|
| Rate λ (episodes/day, waking hours) | Person-level **lnN(median 2.0, σ_log 0.55)**, giving CV ≈ 0.6. Day-level gamma noise with shape 3, so ~35–40% of days have 0–1 episodes | T1DEXI 0.8 logged ≥15-min sessions/day (CV 0.62) and T1DEXIP ~1.5/day. Shorter 5–15-min episodes are unlogged but present (NHANES ~30 min/day ≥60 spm) **[I]** |
| Duration | **lnN(median 18 min, σ_log 0.75)**, truncated to 5–150 min. That puts ~20% above 40 min and ~5% above 60 min | T1DEXI logged mean 41 min (≥15 only, IQR roughly 25–55); Pemberton bouts 20–30; T1DEXIP median 40 (20–75); iDATA shows continuous stepping ≥5 min is rare, so episodes are discontinuous **[I]** |
| Duty cycle within an episode | **0.6–0.8** (fraction of minutes actually moving), or equivalently intensity × duty | Orendurff: walking bouts are mostly ≤30 s with rests ≤20 s **[M→I]** |
| Intensity per episode | **I = (MET − 1)/(METmax − 1)** with MET ~ lnN(median 3.0, σ 0.2), i.e. 2.3–4.0 at ±1.5σ. **I ≈ 0.25 median for METmax 9**, ranging 0.15–0.40. A 10% subset of episodes is "brisk/active" at MET 4.5–6 | Compendium; Pemberton intensity mix 50% light, 42% moderate, 8% vigorous **[M]** |
| Time of day | Sample start times from the **block weights 0.04 / 0.34 / 0.39 / 0.23** (00–06 / 06–12 / 12–18 / 18–24), smoothed and shifted by each person's wake time | UKB **[M]** |
| Meal coupling | Keep **~30–50% within 2 h after a meal [J]**, flagged as unevidenced. Post-meal timing matters a lot for glucose (Manohar; SIT-LESS) | **[NF]** for prevalence |
| Weekday/weekend | ±5% at most, or ignore | UKB d ≈ 0.1; Matson **[M]** |
| Season | Optional: winter −5 to −10% | UKB d ≈ 0.2 **[M]** |

#### (B) Background light activity (new)

A low, smoothly varying waking-hours level: **I_bg(t) = b_person × profile(t)**, with b_person ~ lnN(median 0.06, σ_log 0.4), giving roughly 0.03–0.12 **[J]**. It is anchored on:
- NHANES 8.7 h/day at 1–59 spm plus 110 min/day of light activity **[M]**;
- UVA's 8 steps/min "rest" assumption **[M]**.

Its job is to give daytime glucose disposal a realistic small daily rhythm. It is also where most of the between-person "sedentary vs active" difference lives (activity CV 0.3–0.5). Only add it if the effect model is glucose-proportional (§7.3). With the current zero-order uptake it would simply add a constant daytime glucose sink.

### 7.3 Effect model (per minute, driven by filtered intensity Y)

Filter Y = I through a first-order lag with τ = 5–10 min (Dalla Man T_HR 5; Jaloli τ_h 10) **[M]**.

1. **Insulin-independent disposal:** multiply glucose effectiveness by **(1 + a·Y)**. Romeres measured +53 to +82% at I ≈ 0.6 in T1D, so **a ≈ 1.0–1.4 [I, linear extrapolation]**. If the existing zero-order term is kept, make it proportional to G/G_ref so it fades as glucose falls.
2. **Acute insulin-dependent disposal:** SI × **(1 + b·Y)** with **b ≈ 1.5–2.5** (Romeres +81 to +155% at I ≈ 0.6 in T1D) **[I]**. That replaces the current 0.8.
3. **Delayed sensitivity:** a slow state Z with fast rise and slow off (**τ_off ≈ 600 min**, Dalla Man / Deichmann), **driven by Y above a low threshold I ≈ 0.10–0.15** instead of 0.35 **[M→I]**. Its gain is set so a day with roughly double the episode-minutes lowers AID insulin delivery ~5% (T1DEXI TDD 0.55 → 0.52 U/kg) **[M]**.
4. **Absorption:** keep ×(1 + 0.5·Y) as an upper bound for abdominal sites (Pitt 2020) **[M→I]**.
5. **Between-person gain:** multiply a and b by a person factor lnN(0, σ ≈ 0.5). Jaloli's β spread is ten-fold in 9 people **[M]**, so σ 0.5–0.7 is defensible **[I]**.

### 7.4 Expected glucose effect per episode (validation targets, not fitting targets)

Run the simulator's own episodes through the published designs and compare.

| Test | Target | Source |
|---|---|---|
| 20-min episode, start >180 mg/dL, matched non-activity control | **Net ≈ −34 mg/dL** (95% CI −38 to −32). Minimal intensity dependence | Pemberton 2025 **[M]** |
| ~40-min episode, ΔCGM by start glucose (raw, not net) | 100–150: **−11**; 150–200: **−33**; 200–250: **−52** mg/dL | Dhaliwal 2025 **[M]** |
| ΔCGM by IOB | <1 U ≈ **0 to +6**; ≥3 U ≈ **−32** mg/dL | Dhaliwal 2025 **[M]** |
| Walking sessions (median ~30–40 min) | Median ΔCGM **≈ −18 mg/dL** | Dhaliwal 2025 **[M]** |
| Hypo during episode (≥15 min <70) | **~3% for 15–30 min, ~6% for 30–60, ~12% for 60–120** | Dhaliwal 2025 **[M]** |
| Hypo during episode by start glucose | 50–100: **~21%**; 100–150: **~4%** | Dhaliwal 2025 **[M]** |
| Steps-day effect | TBR on high-activity days **≈ +15% relative** vs low days; TIR +2 pts; TDD −5% | Turner 2024 **[M]** |
| Recovery TBR | TBR in the 3 h after episodes **≈ 1.5× non-activity TBR** (AID users) | RAPPID **[M]** |
| Repeated light breaks | 3 min every 30 min over 7 h post-meal → mean glucose ≈ −23 mg/dL, no added lows | SIT-LESS **[M]** |

**Two cautions.** The real-world targets carry rescue behaviour: RAPPID users took carbs in 27–36% of sessions and set temp targets in 73%. They also carry selection of *when* to move. The simulated person's own pre-activity behaviour (temp target, pre-carbs) is a behaviour trait and must be on when comparing. And CGM lag of ~5–10 min shortens apparent drops over 20-min windows.

### 7.5 What should close the donor gap (0.19 vs 0.09/day no-bolus daytime lows) [I — prediction, to test]

Ranked by expected contribution:

1. **Delayed sensitivity triggered by everyday walking** (threshold 0.35 → ~0.12), which creates lows hours after activity when no bolus is on board.
2. **Long-tailed episode durations**: hypo risk triples from 15–30 min to 60–120 min episodes.
3. **Stronger acute insulin-dependent gain** (b ≈ 2), which bites when basal or AID-raised IOB is high.
4. **Background light activity layer**: small per hour, but it adds between-person spread.

Do not tune any one of these to hit 0.19. Set them from §7.3 evidence first, then check the gap. Per *understand before patching*, if the gap persists, look at other no-bolus low sources (AID basal over-delivery, sensor low bias, compression lows) before raising activity gains.

---

## 8. Not found / open

- **[NF]** Exponents or shape of *active*-bout distributions at a 5–30 min scale in adults (only sedentary and rest power laws, and Nakamura's rescaled stretched-exponential for active periods).
- **[NF]** Day-to-day within-person CV of steps in T1D; T1DEXI mean steps/day.
- **[NF]** Time-of-day distribution of unstructured sessions in T1D, and share of activity occurring after meals.
- **[NF]** Fraction of AID hypoglycemia events attributable to unannounced everyday activity.
- **[NF]** Direct measurement in T1D that *light* walking (≤3 METs) induces prolonged (>2 h) insulin sensitivity. The threshold choice in §7.3 rests on model conventions (Dalla Man, Deichmann) plus T1DEXI TDD and TBR, not on a clamp study.
- **[NF]** Hobbs 2022 parameter values; Romeres 2021 numeric p4/p5/p6 (in its figshare supplement, doi:10.6084/m9.figshare.14178941).
- Pemberton analysed only starts >180 mg/dL. The euglycemic per-minute effect comes from Dhaliwal's raw (unmatched) ΔCGM.
