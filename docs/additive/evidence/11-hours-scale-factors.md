# 11 — Hours-scale glucose drift without food: named factors (literature review)

> **How this was used (2026-10-16).** Commissioned for the quiet-window drift gap (LESSONS 49). Its overnight part was a UTC artifact (LESSONS 51), so growth-hormone pulses were not built. Post-hypoglycaemic resistance (§4.4) was checked against donors and not needed (LESSONS 55). Claims are tagged [checked] / [unverified] / [derived] as found.

Scope: named physiological or behavioural factors that change glucose or insulin need over
**~1–8 h with no food intake** in T1D (healthy subjects where T1D data are missing). Purpose:
to find evidence-sized sources for the quiet-window gap in LESSONS 49:

| SD of glucose change in quiet windows (no eating or bolus for 4 h) | 1 h | 2 h | 3 h |
|---|---|---|---|
| Donors (CGM) | 25.2 | 37.4 | 46.4 |
| Simulator | 27.2 | 37.4 | 40.3 |

The structure-function Hurst exponent over 2–4 h lags is 0.24 for donors and 0.12 for the simulator.

This file complements evidence/02 §4 (stress, sleep, alcohol, caffeine, heat: first-pass sizes)
and evidence/07 (controlled-condition repeat variability). It does not repeat their tables. It
adds the time course and the hour-scale structure each factor would produce.

**Legend.**
- **[checked]**: the number was read this session in the abstract or full text, either directly
  or as quoted from the abstract by the search tool.
- **[unverified]**: from secondary sources or memory, not checked against the primary text.
- **[derived]**: computed here, or a modelling proposal.
- **Measured / inferred**: whether the paper measured the quantity or inferred it from a model or
  a correlation.

---

## 0. What the missing factor has to do: a variance budget [derived]

The extra variance the donors have over the simulator, by window length:

| Window | Donor² − sim² (mg/dL)² | Equivalent independent SD |
|---|---|---|
| 1 h | −105 | the simulator has *more* |
| 2 h | 0 | — |
| 3 h | **+529** | **≈ 23 mg/dL** |

Two consequences shape every recommendation below.

1. **Size.** Assume an independent forcing on the glucose rate, as an Ornstein–Uhlenbeck (OU)
   flux with correlation time τ of 2–8 h. Open loop, with no damping from glucose effectiveness
   or Loop, it needs σ_flux ≈ **0.14–0.16 mg/dL/min** to add 23 mg/dL SD to the 3-h change. That
   is ≈ **11–12 % of basal EGP** (2.5 mg/kg/min ÷ VG 1.88 dL/kg = 1.33 mg/dL/min). Glucose
   effectiveness and the controller damp it, so in closed loop the named factors together must
   produce net glucose-flux fluctuations of roughly **15–20 % of basal EGP, or of basal insulin
   need, persisting for hours**. One factor at 10 % adds well under 23 mg/dL.
2. **Shape.** Any smooth additive forcing adds variance to the 1-h and 2-h changes too. With
   τ = 2–8 h, adding 23 mg/dL at 3 h also adds ≈ 8–9 mg/dL at 1 h and ≈ 16 mg/dL at 2 h, so the
   simulator's 2-h SD would go to ≈ 40.6 against the donors' 37.4. The donors need extra variance
   at 3 h and none at 1–2 h. **No independent additive factor can produce that alone.**
   - This agrees with LESSONS 49: the restoring force is too strong. Simulated true glucose has a
     −0.34 ACF lobe at ~60 min, against the donors' −0.11.
   - The literature factors below can supply the slow, persistent component, but only together
     with a change that removes short-lag, rise-then-fall ringing.
   - Lagged, smooth, long-lasting factors (onset ≥ 1–2 h, duration ≥ 4 h) put proportionally the
     least variance at 1 h, so they are favoured over fast ones.

---

## 1. Ultradian rhythms

### 1.1 Ultradian glucose/insulin oscillations (80–150 min)

- **Healthy, constant glucose infusion:** glucose and insulin secretion oscillate with periods of
  **126 ± 5 min** (glucose) and **118 ± 3 min** (insulin secretion) [checked, measured]. Sturis J,
  Van Cauter E, Blackman JD, Polonsky KS. Entrainment of pulsatile insulin secretion by oscillatory
  glucose infusion. *J Clin Invest* 1991;87:439–445. doi:10.1172/JCI115015.
- **Mechanism: the β-cell feedback loop.** Oscillatory glucose infusion **entrained** both
  insulin secretion and glucose. The slow infusion (155 min) gave 155/150 min; the rapid one
  (103 min) gave 105 min. The authors conclude that the oscillations arise from the glucose–insulin
  feedback loop [checked, measured; the mechanism is inferred by the authors].
- Simon C, Brandenberger G, Follenius M. Ultradian oscillations of plasma glucose, insulin, and
  C-peptide in man during continuous enteral nutrition. *J Clin Endocrinol Metab* 1987;64:669–674.
  doi:10.1210/jcem-64-4-669. Coupled oscillations of **~50–110 min** in healthy men under
  continuous feeding [checked via a later paper's summary; glucose amplitude not checked].
- Oscillations are seen fasting, under constant infusion, with meals and with enteral feeding,
  with periods of ~80–180 min (Sturis 1995 summary) [checked: summary only].
- **T1D, C-peptide-negative: not found.** No study was found that shows ultradian glucose
  oscillations of endogenous origin under fixed insulin delivery. The generating loop (glucose
  → β-cell insulin → glucose) is absent in C-peptide-negative T1D [derived from Sturis 1991].
  Hepatic or glucagon-driven slow oscillations independent of the β-cell were not found.
- **Assessment.** This is not a factor to add. In T1D on AID the analogous loop is
  CGM → Loop → insulin, which the simulator already has. The donors' *weaker* 60-min ACF lobe
  argues against adding any oscillator.

### 1.2 Growth hormone (GH) pulses: delayed, prolonged insulin resistance

**Time course, healthy (measured):**
- GH infused for 1 h at three rates in 11 healthy subjects, under a euglycaemic clamp.
- The insulin-antagonistic effect **starts after 2–3 h, peaks at 4–5 h and lasts ~6–7 h**. It is
  dose-dependent, maximal at plasma GH ≥ ~50 mU/L.
- [checked: Springer abstract] Fowelin J, Attvall S, von Schenck H, Smith U, Lager I.
  Characterization of the insulin-antagonistic effect of growth hormone in man. *Diabetologia*
  1991;34:500–506. doi:10.1007/BF00403286. Author list and pages [unverified].
- The same group's 1991 review says glucagon and adrenaline act fast, while cortisol and GH act
  only after a lag of several hours [checked: snippet].

**T1D, pulsatile versus continuous GH (measured):**
- Overnight clamps in young adults with T1D: three GH pulses 180 min apart, a 12-h continuous GH
  infusion, or buffer.
- **Pulsatile GH raised insulin requirements; continuous GH did not.** The abstract reports
  **0.17 vs 0.09 mU/kg/min** against control. Whether these are increments or means is not clear
  from the truncated abstract.
- Cross-correlation places the rise in insulin requirement **135 min after a GH pulse**
  (r = 0.21, p < 0.001).
- A later thesis summarising this work says the rise lasts **~240 min** [checked: snippet;
  secondary].
- [checked: abstract] Pal BR, Phillips PE, Matthews DR, Dunger DB. Contrasting metabolic effects
  of continuous and pulsatile growth hormone administration in young adults with type 1
  (insulin-dependent) diabetes mellitus. *Diabetologia* 1992;35:542–549. doi:10.1007/BF00400482.

**T1D, dawn rise and nocturnal GH (measured, correlational and interventional):**
- Campbell PJ, Bolli GB, Cryer PE, Gerich JE. Pathogenesis of the dawn phenomenon in patients
  with insulin-dependent diabetes mellitus: accelerated glucose production and impaired glucose
  utilization due to nocturnal surges in growth hormone secretion. *N Engl J Med*
  1985;312:1473–1479. PMID 2859524. doi:10.1056/NEJM198506063122302 [title and PMID checked;
  DOI unverified].
- **Adolescents (Edge, Matthews & Dunger):**
  - insulin infusion rates were higher at 05:00–08:00 than at 01:00–04:00, and the rise
    correlated with mean overnight GH;
  - suppressing GH with pirenzepine (by 11–85 %) cut the pre-breakfast insulin requirement in
    proportion;
  - rhIGF-I lowered both overnight GH and insulin need;
  - T1D adolescents have higher overnight GH than healthy adolescents.
  - [checked: search summaries of the abstracts; individual citations unverified] Edge JA,
    Matthews DR, Dunger DB. The dawn phenomenon is related to overnight growth hormone release in
    adolescent diabetics. *Clin Endocrinol* 1990;33:729–737 [unverified].
- **GH-deficient T1D patients** needed a **46 % fall** in insulin infusion rate between 03:00 and
  08:00, against a **36 % rise** in controls [checked: snippet; citation not retrieved].
- **Relation to the existing model.** B2 (dawn) already carries part of the nocturnal GH effect.
  Dawn magnitude in T1D pumps is +58 % (IQR 29–111 %) in insulin need (Ostrovski 2020, in
  evidence/02). Perriello 1991 reports +19 % and calls dawn "highly reproducible" (evidence/07).

**Frequency (healthy), all [unverified]:**
- GH comes in ~6–12 pulses/day.
- In men ~60–70 % of daily secretion follows sleep onset, in the first slow-wave-sleep episode.
- Women have more frequent and larger daytime pulses.
- Source: Van Cauter E, Plat L. Physiology of growth hormone secretion during sleep. *J Pediatr*
  1996;128:S32–S37.
- In T1D, GH is hypersecreted (low portal insulin → low IGF-I → less feedback) [Edge 1990;
  mechanism unverified].

**Direction and between-person spread:**
- Each pulse is **one-signed** (raises need).
- The pulse train varies in timing and amplitude from night to night, and in daytime pulses.
  Around the person's mean profile, it is therefore a **two-signed fluctuation** [derived].
- Between-person spread is large: puberty, sex, age; GH falls ~14 %/decade in adults
  [unverified].

**Assessment: the best-evidenced hours-scale endogenous factor in T1D.** Its kernel
(onset 2–3 h, peak 4–5 h, 4–7 h duration) is exactly the slow and smooth shape §0 asks for.

### 1.3 Cortisol pulses and the cortisol rhythm

- **Healthy:** mimicking the nocturnal cortisol rise raised hepatic glucose output and lowered
  uptake after a meal [checked: abstract, measured]. Dinneen S, Alzaid A, Miles J, Rizza R.
  Metabolic effects of the nocturnal rise in cortisol on carbohydrate metabolism in normal
  humans. *J Clin Invest* 1993;92:2283–2290. doi:10.1172/JCI116832.
- **Timing (healthy, hydrocortisone at 05:00 or 17:00):**
  - acute fall in insulin secretion, the same at both times;
  - glucose rises from **4–6 h** after the dose and stays above placebo **≥ 12 h**;
  - the effect is much stronger in the evening, with insulin clearance −~30 %;
  - larger elevations cause insulin resistance from 4–6 h, lasting **> 16 h**.
  - [checked: abstract] Plat L, Leproult R, L'Hermite-Baleriaux M, et al. Metabolic effects of
    short-term elevations of plasma cortisol are more pronounced in the evening than in the
    morning. *J Clin Endocrinol Metab* 1999;84:3082–3092. doi:10.1210/jcem.84.9.5974 [DOI
    unverified].
- **T1D:** Dinneen S, et al. Effects of the normal nocturnal rise in cortisol on carbohydrate and
  fat metabolism in IDDM. *Am J Physiol* 1995;268:E595–E603 [title checked; numbers not
  retrieved].
- **Ultradian cortisol pulses** (~hourly) [unverified]. A 4–6 h onset with a ≥ 12 h duration
  low-pass filters hourly pulses almost completely [derived].
- **Assessment.** Cortisol is a **circadian** factor, already covered by B1/B2. Its hourly pulses
  add essentially nothing at 1–8 h. Stress-triggered cortisol is covered under §2.

### 1.4 Glucagon pulses

- Glucagon pulses are minutes-scale in healthy people [unverified]. In T1D glucagon is
  dysregulated, mainly in its meal and hypoglycaemia responses.
- **Not found:** any hours-scale glucagon oscillation in T1D in the fasting state.
- **Assessment:** not a factor at this timescale.

---

## 2. Acute psychological stress

| Study | Population, design | Finding | Kind |
|---|---|---|---|
| Moberg E, Kollind M, Lins PE, Adamson U. Acute mental stress impairs insulin sensitivity in IDDM patients. *Diabetologia* 1994;37:247–251. doi:10.1007/BF00398050 | 10 T1D; 20-min Stroop colour-word test vs rest; 6.5-h insulin–glucose infusion test | Adrenaline, cortisol, GH and BP rose. Steady-state glucose **10.6 ± 1.5 vs 8.7 ± 1.4 mmol/L (≈ +34 mg/dL)** at 3–6.5 h. Insulin resistance from **~1 h after peak stress, lasting > 5 h** | measured [checked: abstract] |
| Wiesli P, Schmid C, Kerwer O, et al. *Diabetes Care* 2005;28:1910–1915 (doi:10.2337/diacare.28.8.1910 [unverified]) | T1D, Trier Social Stress Test | **Fasting: no glucose change.** After food: delayed postprandial recovery | measured [title checked; numbers via evidence/02] |
| Gonder-Frederick LA, et al. Is psychological stress a factor for incorporation into future closed-loop systems? *J Diabetes Sci Technol* 2016;10:640–646. doi:10.1177/1932296816635199 | 33 T1D pump users, 1-week CGM, daily stress ratings | Daily stress related to BG variability indices (r = .17–.19, **r² ≈ 3 %**) and to % time in hypoglycaemia (r = .15). **No relation to mean daily glucose.** Less carbohydrate eaten on stressful days | measured, day-level [checked] |
| Riazi A, Pickup J, Bradley C. Daily stress and glycaemic control in type 1 diabetes: individual differences in magnitude, direction, and timing of stress-reactivity. *Diabetes Res Clin Pract* 2004;66:237–244 | 54 T1D, 21 days, hassles + 4×/day SMBG | ~1/3 stress-reactive. **20.4 % higher** same-day glucose with hassles; **3.7 % lower**. Individual r −0.79 to +0.58 | measured, day-level [checked: abstract] |
| Ozaslan B, Patek SD, et al., Gonder-Frederick L. *J Diabetes Sci Technol* 2018. doi:10.1177/1932296818758103 | 37 T1D, 1-week CGM | The stress × BMI interaction was significant for behaviour-independent glycaemic change (model "effectiveness index"). **No effect on mean glucose** | measured/inferred (model index) [checked] |
| AID vs SAP crossover with TSST + cold pressor + oral hydrocortisone, 14 T1D adults. *Diabetes Technol Ther* 2022;24:338–349 (authors include Kudva, Dassau [unverified list]) | in clinic | AID reduced glycaemic variability during stress (reported −13.4 % GVP [unverified figure]) | measured [partly checked] |

**Frequency in daily life:**
- In the US National Study of Daily Experiences, adults report **≥ 1 stressor on ~40–50 % of
  days**: 41 % heterosexual vs 48 % sexual-minority adults; ~50 % of days at age 25 and ~30 % at
  age 70 [checked: snippets of later NSDE analyses].
- Almeida DM. Resilience and vulnerability to daily stressors assessed via diary methods.
  *Curr Dir Psychol Sci* 2005;14:64–68 [unverified figure].

**Mechanism:**
- Fast: β-adrenergic → EGP ↑ and glucose uptake ↓, within minutes.
- Lagged: cortisol and GH, 1 h onward, lasting hours. Moberg's 1 h → > 5 h course matches this
  [derived from §1.2–1.3].

**Direction and spread:**
- Mostly **upward**, but individual and sometimes downward (Riazi: 3.7 % show lower glucose).
- Field effects on the *mean* are null (Gonder-Frederick, Ozaslan). The effect on *variability*
  is real but small (r² ~3 %).

**Assessment.** Moberg is the only fasting-like T1D measurement with an hours time course: a
large effect (+34 mg/dL at fixed insulin) after a strong laboratory stressor. Wiesli found none
in the fasting state. Everyday hassles are mostly milder.
- Plausible size: **SI −10 to −25 % for 1–6 h after a stress episode**, with per-person gain
  including ~0 (non-responders) and rare negative responders [derived].
- Evidence quality: moderate to weak, with conflicting fasting results.

---

## 3. Sleep

- **Within-night glucose, healthy, constant glucose infusion.** Glucose and insulin secretion
  **rise markedly in early sleep** and return toward presleep levels in late sleep. The authors
  relate this to slow-wave-sleep predominance early and REM/wake late. Under sleep deprivation
  glucose stays flat and then falls [checked: abstract; % rise not retrieved]. Scheen AJ, Byrne
  MM, Plat L, Leproult R, Van Cauter E. Relationships between sleep quality and glucose regulation
  in normal humans. *Am J Physiol* 1996;271:E261–E270. doi:10.1152/ajpendo.1996.271.2.E261.
- **No systematic link between glucose oscillations and individual REM–NREM cycles** is reported
  in the same literature (review statement) [checked: snippet]. The early-night rise is partly
  β-cell and GH mediated, so in T1D it maps onto §1.2.
- **T1D, real world.** 17 adults, CGM plus a wireless sleep monitor, 4 nights. Sleep 358 ± 48 min:
  REM 85, light 207, deep 66 min. More deep sleep went with lower HbA1c (R² = 0.42). Nocturnal
  glycaemia varied widely between and within subjects. **No per-stage glucose slope reported in
  the abstract** [checked]. Feupe SF, Frias PF, Mednick SC, McDevitt EA, Heintzman ND. *J Diabetes
  Sci Technol* 2013;7:1337–1345. doi:10.1177/193229681300700525.
- **Sleep restriction (next day, T1D).** One 4-h night lowered GIR by ~21 % (n = 7) [checked].
  Donga E, et al. *Diabetes Care* 2010;33:1573–1577. This is day-level, already in evidence/02.
- **Nocturnal awakenings and fragmentation:** effect on glucose within the night **not found**
  for T1D.
- **Assessment.** No sleep-stage term is justified. Sleep onset matters through the GH pulse
  (§1.2), whose timing is tied to the person's bedtime. A short night is a next-day SI factor.

---

## 4. Posture, temperature, hydration, caffeine, alcohol, smoking, post-hypoglycaemia

### 4.1 Skin temperature and blood flow → SC insulin absorption (two-signed, hours)

The first-pass sizes are in evidence/02 §4.5:
- ambient 35 vs 20 °C: absorption +50–60 % over 4 h, glucose 1–2 mmol/L lower (Koivisto 1981);
- skin 37 vs 30 °C: early serum insulin ~2× [secondary, weak] (Sindelka 1994, *Diabetologia*
  37:377–380).

New this session:
- Local heating raised tissue perfusion ~145 %, but absorption **did not correlate** with
  perfusion. Hexamer dissociation may be rate-limiting [checked: snippet; citation not
  retrieved]. The size of the effect for monomeric analogues is uncertain.
- **Frequency:** within-day skin-temperature excursions (clothing, sleep, hot shower, outdoors)
  are ubiquitous, but abdominal skin-temperature variability over hours in daily life was **not
  found** quantified.
- **Character [derived].**
  - Mean-neutral by construction: absorption-rate changes move the timing of the same insulin,
    so they cannot shift long-run mean glucose.
  - A basal depot of ≈ 1.5 U (1 U/h × (1/kd + 1/ka2) ≈ 90 min) sped up by 1.5× releases ~0.5 U
    early, about −25 mg/dL at ISF 50, then the reverse.
  - The effect is **transient**: it decays with the depot time constant (~1–1.5 h). It adds
    variance at 1 h, which the donors do not need, more than at 3 h.
- **Assessment:** real and two-signed, but the wrong spectral shape for this gap. Low priority
  for the Hurst/3-h target, though it matters for hypo risk after boluses (evidence/02).

### 4.2 Caffeine

- IV caffeine (healthy, n = 12, clamp): **SI −15 %**, adrenaline ×5 [checked: abstract].
  Keijzers GB, De Galan BE, Tack CJ, Smits P. Caffeine can decrease insulin sensitivity in
  humans. *Diabetes Care* 2002;25:364–369 (DOI 10.2337/diacare.25.2.364 [unverified]).
- T1D, oral caffeine 200 mg ×2/day [dose unverified], CGM:
  - nocturnal hypoglycaemia duration **49 vs 132 min** on placebo;
  - more mild and fewer moderate episodes.
  - [checked: abstract] Richardson T, Thomas P, Ryder J, Kerr D. *Diabetes Care*
    2005;28:1316–1320.
- Time course [unverified]: oral absorption peaks at 30–60 min; t½ ~5 h (range 2–10, a strong
  per-person trait from CYP1A2).
- Prevalence [unverified]: most adults drink caffeine daily, mostly in the morning.
- Long-term coffee intake does not change clamp SI over 24 weeks [checked: snippet].
- **Assessment.**
  - The effect is one-signed (SI ↓), regular (morning) and plausibly −10 to −15 % for ~3–6 h.
  - Its regular part belongs in the person's diurnal profile, where B1b basal shape already
    absorbs it. Only the day-to-day variation of dose and timing adds quiet-window variance.
  - **Low–moderate priority.** Morning coffee often comes with breakfast, so it is rarely in a
    quiet window.

### 4.3 Alcohol (delayed, one-signed down)

- 0.75 g/kg at 21:00 in T1D: no overnight difference; next-morning glucose much lower; 5/6
  treated for hypo from 10:00. Nocturnal GH suppressed between 00:00 and 04:00. Ethanol was
  undetectable by 08:00 [checked].
  - Turner BC, et al. *Diabetes Care* 2001;24:1888–1893. doi:10.2337/diacare.24.11.1888.
  - Richardson T, Weiss M, Thomas P, Kerr D. Day after the night before. *Diabetes Care*
    2005;28:1801–1802 [unverified].
- **Mechanism (inferred by the authors):** loss of the nocturnal GH pulse, so the alcohol effect
  is partly the **absence of §1.2**. Gluconeogenesis is also inhibited acutely.
- **Assessment.** Episodic, 10–15 h delay, lowers glucose. It matters for t<54 more than for the
  quiet-window SD. Planned as B9. If GH pulses are built (§1.2), suppressing the night's pulse
  amplitude on drinking nights gives the delayed morning effect with no separate kernel
  [derived].

### 4.4 Post-hypoglycaemic insulin resistance

- Healthy, after clamped hypoglycaemia: insulin resistance **2.5–3.5 h later**. Insulin's
  suppression of glucose appearance was impaired by **37 %** and its stimulation of disposal by
  **61 %**. Fully blocked by propranolol, so it is β-adrenergic [checked: abstract]. Attvall S,
  Fowelin J, von Schenck H, Lager I, Smith U. Early posthypoglycemic insulin resistance in man is
  mainly an effect of beta-adrenergic stimulation. *J Clin Invest* 1987;80:437–442.
  doi:10.1172/JCI113091.
- A companion study reports prolonged post-hypo resistance through splanchnic and peripheral
  routes (doi:10.1007/BF00296990) [checked: snippet; population not retrieved].
- T1D-specific duration and size: **not found** this session. The counter-regulatory adrenaline
  response is blunted in long-duration T1D and HAAF, which already exists as A9 [derived].
- **Assessment.**
  - Named and sizable, with the right kernel (lagged, hours).
  - Only follows lows, and rescue carbs usually exclude those windows from "quiet". It mainly
    explains rebound highs after lows.
  - Check whether A9 counter-regulation already outlasts the low. If it acts only while
    G < cr_g, this delayed component is missing.

### 4.5 Posture, sedentary periods, hydration, smoking, ambient temperature beyond absorption

- **Posture / sedentary bouts:**
  - Not found as fasting hours-scale glucose effects in T1D.
  - Standing moves plasma volume and haematocrit within minutes (lab artefact, not
    interstitial glucose) [unverified].
  - Muscle activity is already in C6 (everyday activity).
- **Hydration:** not found (no quantitative T1D fasting data).
- **Smoking:**
  - Acute smoking reduces SI in healthy people (Attvall S, et al. *J Intern Med* 1993;233:327–332
    [unverified: not retrieved this session]).
  - Chronic smoking aggravates insulin resistance in T2D clamps [checked: snippet].
  - Prevalence in T1D adults and the per-cigarette time course: not found.
- **Ambient temperature beyond absorption** (thermoregulatory EGP or SI): not found.

---

## 5. Insulin sensitivity variability *within* a day under controlled conditions

- **Diurnal pattern by meal slot:**
  - Hinshaw L, et al. Diurnal pattern of insulin action in type 1 diabetes: implications for a
    closed-loop system. *Diabetes* 2013;62:2223–2229. T1D n = 19, identical meals at 07/13/19 h
    over 3 days in a Latin square. **No significant B/L/D SI difference in T1D.** EGP was less
    suppressed at breakfast. The pattern was "specific to the individual" [checked].
  - Saad A, et al. *Diabetes* 2012;61:2691–2700: healthy people, SI higher at breakfast
    [unverified page and DOI].
  - Both test each slot once, on different days, so within-day and day-to-day variance are
    confounded (evidence/07 §5).
- **Visentin 2015/2018 (UVA/Padova S2017):**
  - intraday SI is modelled as 7 classes of B/L/D profiles with intra- and inter-subject
    variability "based on clinical T1D data";
  - the same work adds a dawn model;
  - the simulator "reproduces the intraday glucose variability observed in clinical data"
    [checked: abstract].
  - Visentin R, et al. The UVA/Padova Type 1 Diabetes Simulator goes from single meal to single
    day. *J Diabetes Sci Technol* 2018;12:273–281. doi:10.1177/1932296818757747.
  - The N(1, 0.2) term is SI **estimation precision**, not a biological repeat (evidence/07).
- **Repeat clamps measure day-level variance only [derived].**
  - Repeat clamps are done at the same clock time, so the 6–15 % (≈ 8 %) day-level CV says
    **nothing** about variance *within* a day. It neither supports nor bounds an intraday wander.
  - The controlled-condition measure that would bound intraday wander is the
    **hour-to-hour fluctuation of i.v. insulin requirement on control nights** in overnight
    euglycaemic clamp studies (Pal 1992 control arm; Edge; Perriello 1991; Biostator studies).
    These are named-factor-free conditions. **The hour-to-hour SD of insulin need on control
    nights was not found in any accessible abstract.**
  - Pal 1992's GH-pulse cross-correlation of r = 0.21 implies that **most** hour-to-hour
    insulin-need variance on those nights is *not* explained by GH [derived], and is therefore
    unexplained.
- **Autocorrelation / timescale of SI change.** Not found for T1D outside the ICU.
- **ICU stochastic SI (STAR/SPRINT, Chase group):**
  - SI is identified hourly; the model is a conditional distribution of SI(n+1) given SI(n), as
    5–95th percentile bands for the next 1–3 h. Variability is largest in the first 12–18 h of
    the stay and shrinks by −32 to −36 % from day 1 to day 2 [checked: Pretty et al.; Chase
    et al. abstracts].
  - Lin J, Lee D, Chase JG, et al. Stochastic modelling of insulin sensitivity and adaptive
    glycemic control for critical care. *Comput Methods Programs Biomed* 2008;89:141–152
    [checked: citation; numbers not retrieved].
  - Pretty CG, et al. *BioMed Eng OnLine* 2014;13:43. doi:10.1186/1475-925X-13-43.
  - **Not transferable:** critically ill patients on IV insulin and nutrition with stress
    hormones; the variance is dominated by acute illness.

---

## 6. Free-living "unexplained" variability, and simulator precedents

### 6.1 Measurements in T1D (targets, not inputs)

| Source | What | Number | Kind |
|---|---|---|---|
| Ruan Y, et al., Hovorka R. *Diabetes Care* 2016. doi:10.2337/dc15-2623 | Day-to-day CV of closed-loop insulin delivered, 12-wk home, 32 adults | **night 31 %**, day 22 %, TDD 17 % | measured [checked] |
| Castagna G, Lepore G, Borella ND, Trevisan R. *Diabetes Obes Metab* 2025;27:3512–3514. doi:10.1111/dom.16319 | Inter-night CV of **hourly** AID insulin, 00–07 h, 55 adults (780G, Control-IQ, DBLG1), nights with no manual bolus | **> 63 % in every participant**, no hour-of-night difference. Correlated only with glucose CV | measured [checked]. Includes the controller's own response to CGM noise, so an upper bound on physiological need variance |
| Ruan Y, Wilinska ME, Thabit H, Hovorka R. *IEEE Trans Biomed Eng* 2017;64:1412–1419, doi:10.1109/TBME.2016.2590498 | Day-to-day variability of model SI, hierarchical Bayesian, home CL | **SI 38–79 %**; time-to-peak insulin action 27–48 % | inferred (model absorbs every unmodelled factor) [checked: abstract] |
| Ogata H, Tokuyama K, Nagasaka S, et al. Long-range correlated glucose fluctuations in diabetes. *Methods Inf Med* 2007;46:222–226. doi:10.1055/s-0038-1625411 | DFA of 1-day CGM; 12 healthy, 15 diabetes | Healthy: crossover ≈ **2 h**, **negatively** correlated (anti-persistent) beyond. Diabetes: **positively** correlated long-range, α ≈ 1.65 | measured [checked] |
| Kohnert K-D, et al. *Front Physiol* 2018;9:1257. doi:10.3389/fphys.2018.01257 | DFA α1/α2, 22 T1D, 143 T2D, 12 controls | α highest in T1D (α1 ~1.94, α2 ~1.38, snippet) | measured [partly checked] |

Reading [derived]:
- Ogata's healthy anti-persistence beyond ~2 h comes from β-cell feedback.
- In diabetes, persistent multi-hour drift appears. That is the donors' higher 2–4 h Hurst. It
  includes meals, but the donors show it in quiet windows too.
- So T1D physiology has slow drifts that are **not** pulled back quickly. In the simulator the
  pull-back (glucose effectiveness, counter-regulation, controller) dominates (LESSONS 49).

### 6.2 How T1D simulators represent intraday variability (precedent, not evidence)

| Simulator | Form | Justification |
|---|---|---|
| Cambridge (Wilinska ME, Chassin LJ, Acerini CL, Allen JM, Dunger DB, Hovorka R. *J Diabetes Sci Technol* 2010;4:132–144. doi:10.1177/193229681000400117) | **±5 % sinusoid, 3-h period**, random phase U[0, 3 h], on F01, EGP0, k12, SID, SIE, SIT, kb1–3, ke, ka_int; carb bioavailability +20 % inter-occasion | **None cited** [checked: full text via WebFetch] |
| Haidar A, Wilinska ME, Graveston JA, Hovorka R. *IEEE Trans Biomed Eng* 2013;60:3524–3533 | Sinusoidal SI with random phase; absorption parameters ±30 % intra-subject | [secondary description; unverified] |
| UVA/Padova S2017 (Visentin 2018) | 7-class B/L/D SI profiles + dawn | Hinshaw-type single-day data; σ = estimation precision |
| ICU STAR (Lin 2008) | Empirical Markov transition of hourly SI | ICU data |

None of these grounds an hours-scale wander in a T1D controlled-condition measurement. That
supports keeping B4 off and using named factors instead.

---

## 7. Factor summary

Direction "two-signed*" means a one-signed pulse whose random timing and amplitude make it a
zero-mean fluctuation around the person's average profile, once that profile absorbs its mean.

| Factor | Size (SI/EGP or glucose) | Onset / duration | Frequency | Direction | Between-person | Evidence tier |
|---|---|---|---|---|---|---|
| GH pulse → insulin resistance | insulin need ↑ (Pal: 0.17 vs 0.09 mU/kg/min); dawn +19 % to +58 % | onset 2–3 h, peak 4–5 h, 4–7 h total; T1D lag 135 min | 1 large sleep-onset pulse/night + several smaller daytime pulses [unv] | two-signed* | large (age, sex, puberty; T1D hypersecretion) | **T1D measured** (Pal; Edge; Campbell) |
| Acute stress (sympathetic → cortisol/GH) | +34 mg/dL at fixed insulin after a strong stressor; fasting TSST: none | onset ~1 h, > 5 h | stressor on ~40–50 % of days | mostly ↑, some ↓, many 0 | very large (1/3 reactive) | T1D measured, conflicting |
| Post-hypo insulin resistance | Ra suppression −37 %, Rd −61 % (healthy) | 2.5–3.5 h after a low | after lows | ↑ | blunted in HAAF [derived] | healthy measured |
| Skin temperature → absorption | ×1.5–2 absorption rate | minutes; transient ~1–1.5 h | daily | two-signed | moderate | T1D measured (regular insulin) |
| Caffeine | SI −15 % (IV, healthy) | peak 0.5–1 h, t½ ~5 h | most adults daily | ↑ | t½ trait | healthy measured |
| Alcohol | morning hypos (5/6) | 10–15 h delay | per-person weekly | ↓ | large | T1D measured, n = 6 |
| Cortisol pulses | hourly pulses filtered out by the 4–6 h lag | ≥ 12 h | hourly | — | — | healthy measured; negligible at this scale |
| Ultradian oscillation | — | 80–150 min | — | — | — | absent in C-peptide-negative T1D |
| Sleep stages | early-night rise (healthy, β-cell/GH-mediated) | within night | nightly | ↑ then ↓ | — | not found for T1D |
| Posture, hydration, smoking | not found | — | — | — | — | — |

---

## 8. Ranked recommendation [derived]

Target: about **+10–15 % on the 3-h quiet-window SD** (40.3 → 44–46), with mean glucose unchanged.
Keep §0's shape caveat in mind: every option below also adds variance at 1–2 h. Pair them with
the restoring-force work from LESSONS 49, or the 2-h SD will overshoot.

**1. GH pulse train with a delayed insulin-resistance kernel (build first).**
- **Pulse times:**
  - one sleep-onset pulse per night, at bedtime + U(0.5, 1.5) h;
  - plus daytime pulses as a Poisson process at a per-person rate of ~2–6/day, women at the
    upper end [unverified rates: flag as J-sized until checked against Van Cauter & Plat 1996 or
    similar];
  - alcohol nights scale the sleep pulse by ~0.3–0.5 (Turner 2001: GH suppressed 00–04 h).
- **Amplitude:** per pulse lnN(0, 0.5–0.7), with a per-person GH gain trait.
- **Kernel on the SI multiplier** (or on EGP, split like B2): a gamma-shaped resistance with lag
  2–2.5 h, peak at 4–5 h after the pulse and ~6–7 h total. Fowelin 1991 for the shape; Pal 1992
  for T1D (135-min lag, ~240-min rise).
- **Size:** set the sleep-onset pulse's mean effect equal to the person's existing B2 dawn
  amplitude. B2's mean dawn rise is then *produced* by the GH kernel, not added on top, which
  avoids double counting. The night-to-night spread comes from the amplitude lognormal and the
  timing jitter.
- **Daytime pulses:** size from Pal 1992 per pulse.
- **Mean neutrality:** subtract each clock-hour's expected GH effect from B1b's basal-need shape,
  so the profile plus E[GH] equals the calibrated profile. Mean glucose and TDD are unchanged; only
  the fluctuations are new.
- **Expected yield:**
  - With dawn amplitude lnN(0.3, 0.6) of EGP, a per-night amplitude CV of ~0.6 alone gives an
    EGP-equivalent SD of ~15–20 % over a 4–6 h window. That is within the §0 requirement for the
    hours after sleep onset.
  - Daytime pulses add a smaller, all-day component.
  - This plausibly delivers most of the +10–15 % in night and morning quiet windows, which are a
    large share of quiet windows. Verify by splitting quiet windows by clock hour.

**2. Acute stress episodes as a sympathetic → cortisol/GH kernel (second).**
- **Episodes:** per-person daily probability 0.3–0.5 (NSDE), during waking hours.
- **Gain:** per-person, drawn from a mixture: ~2/3 near zero, ~30 % positive with SI −10 to −25 %,
  ~4 % negative (Riazi 2004).
- **Kernel:** onset ~1 h, plateau to ~5 h, then decay (Moberg 1994). Use the same lagged shape
  as GH, since the pathway is partly GH and cortisol.
- **Mean neutrality:** the expected effect is small and positive. Absorb it in the person's
  basal calibration, as for GH.
- **Evidence caveats:**
  - Moberg's stressor was strong and laboratory-induced; Wiesli found no fasting effect. Size the
    everyday gain at the lower end (≈ −10 %).
  - Report sensitivity results with the gain at 0 and at −25 %.

**3. Post-hypoglycaemic insulin resistance (third; mainly for rebound highs and t<54).**
- If A9 counter-regulation stops when glucose recovers, add a β-adrenergic resistance state
  triggered by G < ~60. Peak SI −30 to −50 % at ~1–2 h, decaying over 3–4 h (Attvall 1987,
  healthy), scaled by the HAAF state h, since blunted adrenaline gives less resistance.
- It will barely touch quiet windows if rescue carbs exclude them. It belongs with the
  low-response components.

**4. Caffeine (optional, low).**
- Morning dose events on most days, SI −10 to −15 %, PK with per-person t½ lnN(5 h, 0.4)
  [unverified].
- Mean-centred into the diurnal profile.
- Small yield: regular timing, mostly coincides with breakfast.

**Not recommended for this gap:**
- an endogenous ultradian oscillator (absent in T1D; the donors show a *weaker* hourly ACF lobe);
- cortisol pulses (filtered out);
- sleep stages (no T1D evidence);
- skin-temperature absorption (right sign symmetry, wrong spectrum; keep for hypo-risk
  scenarios);
- posture, hydration and smoking (no quantitative evidence);
- an unnamed SI OU (B4: no controlled evidence; precedents are unsourced).

**Evidence still to obtain** (would turn the J-sized parts into measured ones):
1. Pal 1992 and Edge 1990 full texts: hour-by-hour insulin requirement on control nights. This
   is the one controlled-condition measurement of hours-scale insulin-need fluctuation in T1D,
   and it bounds everything above.
2. GH pulse frequency and amplitude in adult T1D, day and night, by sex.
3. Moberg 1994 full text: glucose time course after stress.
4. A donor-side check that needs no literature: split the donors' quiet-window 3-h SD by clock
   hour.
   - If GH is the driver, the excess over the simulator should concentrate 2–8 h after typical
     sleep onset and in the morning.
   - If stress is the driver, it should sit in waking hours.
