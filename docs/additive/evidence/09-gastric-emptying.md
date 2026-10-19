# 09 — Gastric emptying and meal-glucose appearance vs meal size

Compiled 2026-10-15 for the additive patient simulator (gut model).

Tags: **[M]** a number measured in the cited study (read from its abstract or full text).
**[R]** a statement from a review, which cites primary work. **[I]** my inference or a
derivation, not stated by any source. **[S]** taken from a search-engine snippet or from
memory and not checked against the paper; verify before citing. Model simulations are in
a scratch simulation (not tracked).

---

## 0. Summary

- **The hypothesis is mostly right but needs one correction.** Nutrient emptying is regulated
  by calorie delivery to the duodenum. It runs at roughly 1–4 kcal/min overall, faster in the
  first 15–30 min, and the half-time grows with meal energy. It is **not strictly zero-order**:
  larger and denser loads empty at a *higher* kcal/min rate (Hunt 1985; Schirra 1996; Moore
  1984). So duration grows with meal size, but less than in proportion. A saturating
  (Michaelis–Menten-like) emptying law in kcal covers both regimes. First-order-like emptying
  applies to small loads and zero-order-like emptying to large ones.
- **The current model (first-order, size-independent) is contradicted by every size study
  found.** The Dalla Man 2006 nonlinear kempt does **not** fix this either. Its thresholds and
  slopes scale with the dose D, so the normalised time course is identical for every meal size
  ([I], derived from the equations and confirmed by simulation, §5).
- Hovorka's Cambridge simulator (Wilinska 2010) is the one published T1D simulator found with
  an explicit size limit: a ceiling on gut glucose flux, `U_G,ceil ~ U[0.02, 0.035]
  mmol/kg/min` [M-model]. That is ≈1.0–1.8 kcal/min of glucose at 70 kg [I], which sits inside
  the physiological kcal/min band.

---

## 1. Measured emptying rates and their dependence on size and energy

| Source | Meal | Finding |
|---|---|---|
| Hunt JN, Stubbs DF. *J Physiol* 1975;245:209–225. doi:10.1113/jphysiol.1975.sp010841 | Pooled 33 studies, 50–1250 ml, 0 to 2–3 kcal/ml | [M] Denser meals emptied less volume in 30 min, but **the energy delivery rate still rose with density** (slowing "not sufficient to prevent an increased rate of delivery of energy"). Initial volume did not set ml/min. Fat, protein and carbohydrate slow emptying equally **per kcal** (4 g fat ≈ 9 g CHO). Assumed exponential emptying for the fit. |
| Brener W, Hendrix TR, McHugh PR. *Gastroenterology* 1983;85:76–82 (PMID 6852464) | Glucose 0.05, 0.125, 0.25 g/ml | [M] After the stomach filled, glucose emptied at a **constant 2.13 kcal/min independent of concentration** (zero-order). Saline emptied exponentially. Duodenal glucose inhibited emptying by 0.46 min/kcal, the reciprocal, which they read as a closed-loop feedback. |
| Hunt JN, Smith JL, Jiang CL. *Gastroenterology* 1985;89:1326–1330. doi:10.1016/0016-5085(85)90650-x | Polycose 300–600 ml, 0.5–2.0 kcal/ml, n=1134 meals | [M] Mean **2.5 kcal/min**. The first 30 min were faster than 30–60 and 60–120 min. **Rate rose with load**: doubling volume added +0.72 kcal/min, and doubling density (0.7→1.3) added +0.62 kcal/min. This contradicts strict zero-order emptying. |
| Calbet JAL, MacLean DA. *J Physiol* 1997;498:553–559. doi:10.1113/jphysiol.1997.sp021881 | 600 ml, glucose 0.1 / peptide 0.2 / milk protein 0.7 kcal/ml | [M] t½ 9.4 (glucose), 16–17 (peptides), 26.4 min (milk protein). t½ was **linear in caloric density (r=0.96)**. Early-phase delivery was 46, 63, 63 and 114 cal/min/kg, which is [I] ≈3.2–8 kcal/min at 70 kg: **early emptying far exceeds 1–4 kcal/min**. The source of the calories mattered little. |
| Schirra J et al. *J Clin Invest* 1996;97:92–103. doi:10.1172/JCI118411 | 50 vs 100 g oral glucose | [M] Power-exponential emptying with a short lag. Duodenal delivery **declined exponentially, not constant**. **Doubling the load cut the fractional emptying rate by 27.5%** (so [I] the absolute kcal/min rose about 1.45×). |
| Moore JG et al. *Dig Dis Sci* 1984;29:513–519. doi:10.1007/BF01296271 | 50/300/900 g meals at 68/208/633 kcal | [M] Solid emptying in g/min rose with meal weight. **More kcal slowed solid emptying**, though not enough to overcome the weight effect. Liquid-phase rate was unaffected by kcal. |
| Moore JG, Christian PE, Coleman RE. *Dig Dis Sci* 1981 | Three meal sizes | [S] Solid-phase emptying was **linear**, with t½ 77 / 146 / 277 min for the 300 g / 900 g / "filling" meals. |
| Collins PJ, Horowitz M et al. *Gut* 1983;24:1117–1125. doi:10.1136/gut.24.12.1117 | Mixed solid + liquid (water, 10% or 25% dextrose) | [M] **Solids: lag period, then linear emptying.** Liquids: single exponential. More liquid kcal **slowed liquid emptying and prolonged the solid lag**. Day-to-day variation was not significant; between-subject differences were significant. |
| Gonlachanvit S et al. *Dig Dis Sci* 2001;46:2643–2650. doi:10.1023/a:1012758925461 | Muffin, 250 vs 350 kcal, breath test | [M] t½ **153 → 177 min** (+40% kcal gave +16% t½) [I: sublinear]. |
| Jackson SJ, Bluck LJ, Coward WA. *Rapid Commun Mass Spectrom* 2004;18:1003–1007. doi:10.1002/rcm.1440 | Egg meal, 1 / 2 / 3 MJ | [M] Going from 1 to 2 MJ added +0.77 h to t½ (significant). Going from 2 to 3 MJ added only +0.44 h (not significant). |
| Hellmig S et al. *J Gastroenterol Hepatol* 2006;21:1832–1838. doi:10.1111/j.1440-1746.2006.04449.x | 90 healthy, breath test | [M] Liquid t½ 80.5 ± 22.1 min. Solid t½ median **127 min (IQR 112–168)**, Tlag median 81.5 min. |
| Marathe CS et al. (lixisenatide placebo arm). *Diabetes Ther* 2022;13:1245–1249. doi:10.1007/s13300-022-01258-4 | 75 g glucose drink, scintigraphy, older adults | [M] Placebo: **1.45 ± 0.10 kcal/min** (healthy), **1.57 ± 0.06** (T2D). |
| Marathe CS, Rayner CK, Jones KL, Horowitz M. *Diabetes Care* 2013;36:1396–1405. doi:10.2337/dc12-1609 | Review | [R] "Gastric emptying of meals occurs at an overall rate of **1–4 kcal/min**" (citing Horowitz & Dent, *Baillieres Clin Gastroenterol* 1991;5:371–407). Gastric emptying explains about **35% of variance** in the glycaemic response (Horowitz 1993; Jones 1996). Glycaemia vs intraduodenal glucose is **nonlinear**: 1 kcal/min gives only a modest rise, and 2, 3 and 4 kcal/min give similar, larger rises. |
| Elashoff JD, Reedy TJ, Meyer JH. *Gastroenterology* 1982;83:1306–1312 | Methods | [M] Recommends the **power-exponential** retention curve `R(t)=exp(-(kt)^β)`. β>1 gives a lag or initial slow phase (solids); β<1 gives a fast initial phase (liquids). |

**Synthesis.** [I] Duration rises with energy, but sublinearly. Over the range of everyday
meals, doubling energy raises t½ by about 1.15–1.5×, not 2×. Nutrient liquids empty with an
early fast phase and an exponentially declining delivery. Solids have a lag (typically 20–80
min) followed by near-linear (zero-order-like) emptying.

## 2. Gastric emptying in type 1 diabetes

- **Prevalence.** [R] Emptying of solids and/or nutrient liquids is delayed in **30–50%** of
  people with long-standing T1D or T2D, and is sometimes abnormally rapid (Marathe 2013,
  citing Chang 2010 and Kashyap & Farrugia 2010). [M] In an unselected cohort (186
  patients, 106 with T1D), **28% were delayed**: solid T50 99.5 ± 35.4 vs 76.8 ± 21.4 min in
  controls, and 120-min retention 30.6% vs 20.4% (Samsom M et al. *Diabetes Care*
  2003;26:3116–3122, doi:10.2337/diacare.26.11.3116; breath test). [M] Emptying changes
  little over up to 25 years (Chang J et al. *Diabetes Care* 2012;35:2594, cited in Marathe
  2013).
- **Hyperglycaemia slows emptying.**
  - [M] Schvarcz E et al. *Gastroenterology* 1997;113:60–66 (PMID 9207262), clamp at 8 vs 4
    mmol/L. Solid retention at 100 min was 44.2% vs 35.7% in T1D and 55.2% vs 36.7% in
    controls. Liquid T50 in controls was ~57 vs 32 min [S for liquid].
  - [M] Fraser RJ et al. *Diabetologia* 1990;33:675–680 (doi:10.1007/BF00400569), 16–20 vs 4–8
    mmol/L in T1D. Solid lag, solid T50 and liquid T50 were all prolonged.
  - [R] At ~15 mmol/L the delay is "substantial" (Marathe 2013).
- **Hypoglycaemia accelerates emptying.**
  - [M] Russo A et al. *J Clin Endocrinol Metab* 2005;90:4489–4495 (doi:10.1210/jc.2005-0513):
    20 people with long-standing T1D, ~2.6 mmol/L clamped from 15 min before to 45 min after
    the meal. **Both solids (P<0.001) and liquids (P<0.05) emptied faster.** The acceleration
    was greater in slower emptiers (liquid T50, r = −0.82) and was present even with autonomic
    neuropathy.
  - [S] A later study in healthy people found the effect depends on the depth of hypoglycaemia
    and on the baseline emptying rate.
  - Absolute effect sizes in minutes: not found in the abstracts.
- **Implication for T1D dosing.** [R] What matters is predictability. Gastroparesis likely
  raises the risk of early postprandial hypoglycaemia (Horowitz et al. *Neurogastroenterol
  Motil* 2006;18:405, "gastric hypoglycaemia").
- **Normal limits.** [S] The consensus low-fat egg-white scintigraphy defines delayed emptying
  as >60% retained at 2 h or >10% at 4 h (Abell TL et al. *Am J Gastroenterol*
  2008;103:753–763, doi:10.1111/j.1572-0241.2007.01636.x). The thresholds are not in the
  abstract, so verify them.

## 3. Rate of appearance (Ra) of meal glucose vs meal size (tracer)

- **A within-subject tracer study varying carbohydrate dose (for example 25/50/100 g), in T1D
  or in healthy people: NOT FOUND.** The closest evidence:
  - [M] Schirra 1996: emptying (not Ra) at 50 vs 100 g glucose, see §1.
  - [M] Ferrannini E et al. *Diabetes* 1985;34:580–588 (doi:10.2337/diab.34.6.580), 1 g/kg oral
    glucose (55–93 g), double tracer. Ra of ingested glucose **peaked at 15–30 min but was still
    2.47 mg/kg/min at 3.5 h**. Only **73 ± 4%** had appeared systemically by 3.5 h.
    [I] This means a long tail. It is inconsistent with "90% absorbed by 2 h" for a ~75 g load.
  - [M] Elleri D et al. *Diabetologia* 2013;56:1108–1117 (doi:10.1007/s00125-013-2852-x), T1D,
    **121 g carbohydrate** evening meal, tracer-derived meal Ra:

    | Meal | 25% appeared | 50% appeared | 75% appeared |
    |---|---|---|---|
    | High glycaemic load | 56 ± 12 min | 100 ± 25 min | 153 ± 39 min |
    | Low glycaemic load | 88 ± 21 min | 175 ± 39 min | 270 ± 54 min |

    Peak Ra was 50% higher for the high-GL meal. Apparent bioavailability was 15% higher for
    the low-GL meal. Mixed carbohydrate appeared about 20 min later than dietary glucose
    (high-GL meal), and about twice as slowly in the low-GL meal.
    [I] A 121 g meal reaching 50% at 100 min, versus 59 min for any size under the current
    model, is direct T1D evidence that large meals appear more slowly than the current model
    allows.
- Dalla Man 2006/2007 parameters were fitted to triple-tracer data at a single meal size per
  subject [S: verify the meal sizes in the 2006 paper]. They therefore cannot identify size
  dependence.

## 4. Fat and protein

- [M] Per kcal, fat, protein and carbohydrate slow emptying about equally (Hunt & Stubbs 1975).
- [M] The nature of the calories "plays a minor role" (Calbet & MacLean 1997, protein vs
  glucose).
- [M] A **specific fat effect beyond kcal**: 30 ml olive oil taken **30 min before** a potato
  meal slowed emptying much more than the same oil mixed into the meal (Gentilcore D et al.
  *J Clin Endocrinol Metab* 2006;91:2062–2067, doi:10.1210/jc.2005-2644; T2D, n=6).
  [I] Fat already in the duodenum brakes emptying. Timing matters, not only total kcal.
- [M] T1D adolescents, 2 vs 38 g fat (320 vs 640 kcal), same carbohydrate (Lodefalk M, Aman J,
  Bang P. *Diabet Med* 2008;25:1030–1035, doi:10.1111/j.1464-5491.2008.02530.x):
  - Glucose and paracetamol AUC over 0–2 h were lower after the high-fat meal.
  - Paracetamol peak was at 120 vs 60 min (P=0.051).
  - Glucose peak was at 210 vs 120 min (P=0.08).
- **Fat and protein also raise late glucose by routes other than emptying.**
  - [M] Wolpert HA et al. *Diabetes Care* 2013;36:810–816 (doi:10.2337/dc12-0092): a high-fat
    dinner (60 vs 10 g fat) needed 12.6 vs 9.0 U insulin under closed loop and still caused
    more hyperglycaemia. The authors attribute this to FFA-induced insulin resistance.
  - [M] Smart CE et al. *Diabetes Care* 2013;36:3897–3902 (doi:10.2337/dc13-1195): 35 g fat
    and 40 g protein each raised glucose from 3–5 h, additively. High protein lowered the risk
    of hypoglycaemia (OR 0.16).
  - [R] Bell KJ et al. *Diabetes Care* 2015;38:1008–1015 (doi:10.2337/dc15-0100): late
    hyperglycaemia is the main effect of fat. Early glucose is sometimes reduced, "possibly
    due to delayed gastric emptying".
  - [I] A simulator should model fat and protein in two parts. One is their kcal contribution
    to emptying. The other is separate late effects on insulin sensitivity and glucose
    production, which are not gut factors.

## 5. Simulators and how they treat meal size

- **Dalla Man, Camilleri & Cobelli. *IEEE TBME* 2006;53:2472–2478 (doi:10.1109/TBME.2006.883792)**,
  used in Dalla Man 2007 (doi:10.1109/TBME.2007.893506) and the UVA/Padova simulator.
  - Structure: a two-compartment stomach (solid → liquid), then a gut compartment, then
    `Ra = f·kabs·Qgut/BW`.
  - `kempt(Qsto) = kmin + (kmax−kmin)/2·{tanh[α(Qsto−b·D)] − tanh[β(Qsto−c·D)] + 2}`, with
    α = 5/(2D(1−b)) and β = 5/(2Dc). Emptying runs at kmax early and late, and dips to kmin in
    mid-meal. The equation is confirmed in the simglucose implementation (`t1dpatient.py`).
  - Adult parameters in simglucose `vpatient_params.csv` (min / median / max):

    | Parameter | Min | Median | Max |
    |---|---|---|---|
    | kmax | 0.022 | 0.041 | 0.058 /min |
    | kmin | 0.003 | 0.006 | 0.015 /min |
    | kabs | 0.021 | 0.155 | 0.58 /min |
    | b | 0.63 | 0.79 | 0.96 |
    | d | 0.09 | 0.18 | 0.34 |
    | f | 0.9 | 0.9 | 0.9 |

  - **[I] The model is dose-invariant.** All states are linear in D, the thresholds are fractions
    of D, and α and β scale as 1/D. Ra(t)/D is therefore identical for every meal size.
    Simulated with the median adult parameters, t50 is 101 min and t90 245 min for 25, 50, 75,
    100 and 121 g alike. Its nonlinearity shapes the curve but does **not** make big meals
    slower.
- **Hovorka 2004 / Wilinska ME et al. *J Diabetes Sci Technol* 2010;4:132–144
  (doi:10.1177/193229681000400117)** (Cambridge simulator).
  - Structure: a two-compartment chain, `U_G = G2/tmax`.
  - Parameters: tmax lognormal with median 40 min (`1/tmax ~ exp N(−3.689, 0.25²)`), plus 20%
    inter-occasion variability. Bioavailability ~ U(70, 120)%.
  - **Size dependence**: "the glucose flux from the gut is assumed to be a saturable process."
    If U_G > U_G,ceil, then tmax = G2/U_G,ceil, with **U_G,ceil ~ U[0.02, 0.035] mmol/kg/min**
    [M-model, from the full text].
  - [I] At 70 kg that ceiling is 0.25–0.44 g glucose/min ≈ 1.0–1.8 kcal/min. It is a hard
    zero-order cap on appearance. It is the closest published analogue of the energy-limit
    hypothesis, but it caps carbohydrate only and ignores fat and protein.
- **Other size-dependent simulators** (MM emptying, kcal-based stomach) in a T1D simulator:
  **not found** in this search. Physiology modelling tradition (Elashoff power-exponential;
  Brener/Hunt feedback) supports a kcal-feedback form.

## 6. Recommended model form and parameters

**Form** [I, built from §1–5]:

1. **Stomach in kcal.** `S` holds the meal's energy: CHO 4, protein 4, fat 9 kcal/g, per Hunt &
   Stubbs's equal-per-kcal finding.
2. **Saturating emptying.** `E(t) = Vmax · S/(Km + S) · m_BG(t)` (kcal/min) after a lag
   `t_lag`.
   - Small meals behave first-order, with rate constant Vmax/Km.
   - Large meals behave zero-order at Vmax. This reproduces "kcal/min rises with load but
     saturates" (Hunt 1985; Schirra 1996).
3. **Carbohydrate leaves in proportion to its share of stomach kcal.** Then it passes through
   the existing intestinal step(s) at `kabs ≈ 0.045/min` (keep the current value) to give Ra,
   scaled by bioavailability `f`.
4. **Blood-glucose modifier `m_BG`.** About 1 at euglycaemia, <1 when hyperglycaemic, >1 when
   hypoglycaemic.
5. **Separate from the gut model.** Fat and protein late effects (insulin resistance, extra
   glucose production) belong in another component, not in emptying.

**Parameters** (central value, range, source):

| Parameter | Value (range) | Basis |
|---|---|---|
| Vmax | **3.0 kcal/min (2–5)** | Overall 1–4 kcal/min [R Marathe 2013]. Constant 2.1 [M Brener]. 2.5 mean [M Hunt 1985]. 1.5 for a 75 g drink in older adults [M Marathe 2022]. Early phase 3–8 [M/I Calbet]. Elleri's high-GL meal needs ≥3–4. |
| Km | **60 kcal (30–120)** | [I] Gives a 25 g snack an initial k = Vmax/Km ≈ 0.05/min, which matches the current kempt for small loads. Calibrated so that 50→100 g cuts the fractional rate by about 30% (Schirra: 27.5%). |
| t_lag (solid or mixed meals) | **10 min (0–40)**; 0 for liquids | Lag then linear [M Collins 1983]. Breath-test Tlag is longer (~80 min, Hellmig) but includes post-gastric steps. The lag grows with liquid kcal [M Collins]. |
| Between-person Vmax | lognormal, **CV ≈ 30%** | [I] From the SDs in Samsom 2003 (28% in controls, 36% in diabetes) and Hellmig. |
| Gastroparesis subgroup | **~25–30% of T1D** with Vmax ×0.6–0.8 | [M] 28% delayed (Samsom). [I] T50 1.3× the control mean. 30–50% in long-standing T1D [R].  DCCT/EDIC year-20 breath test (Bharucha 2015, n 78): 50% normal, 47% delayed, 3% rapid; scintigraphy reviews 25–55% in T1D. The model's 28% is at the low end; LESSONS 286 (c293 ablation) found the spread carries part of the twins' slow post-peak fall, but no evidence argues for a smaller share. |
| Day-to-day (within person) | small, **CV ~10–20%** | Not significant in Collins 1983 [M]. Wilinska uses 20% inter-occasion variability on tmax [M-model]. A precise figure: not found. |
| m_BG | 1 at 4–6 mmol/L; about **0.75 at 8 mmol/L**; **~0.5–0.6 at 15–20 mmol/L**; **~1.3–1.5 below 3 mmol/L** | Retention 44 vs 36% in T1D at 8 vs 4 mmol/L [M Schvarcz]. Delay "substantial" at 15 [R]. Acceleration [M Russo]. Every magnitude here is [I]; the effect sizes are poorly pinned. |
| Bioavailability f | 0.9 (0.7–1.0) | Dalla Man / simglucose 0.9. Wilinska U(0.7, 1.2). |

**What this gives** ([I], simulated with Vmax 3, Km 60, kabs 0.045, carbohydrate-only meals,
50% appearance time):

| Meal | Current model | Proposed model |
|---|---|---|
| 25 g | 59 min | **53 min** |
| 50 g | 59 min | **70 min** |
| 100 g | 59 min | **103 min** |
| 121 g | 59 min | **117 min** |

The proposed 121 g figure compares with 100 min [M] for Elleri's high-GL meal and 175 min [M]
for the low-GL meal. Peak Ra for 100 g falls from 1.22 to 0.59 g/min. Adding 60% more energy
as fat and protein moves 100 g to t50 = 143 min.

**Calibration targets** for unit tests:

- Brener 2.13 kcal/min plateau.
- Hunt 1985: +0.7 kcal/min per volume doubling.
- Schirra: −27.5% fractional rate at 100 vs 50 g.
- Elleri 121 g, 25/50/75% appearance times: 56/100/153 min (high GL) and 88/175/270 min (low GL).
  **Unverified:** `ra_traj.py` (run dir) quotes 72/130/197 (high GL) and 95/178/270 (low GL) for the same study; the
  full text (doi:10.1007/s00125-013-2852-x) is paywalled and the discrepancy is unresolved (LESSONS 287). Check the
  paper before using either set as a calibration target.
- Ferrannini: ~73% appeared by 3.5 h at ~1 g/kg.

**Caveat.** Ra-vs-dose has not been measured directly by tracer in T1D (§3). The size scaling
rests on gastric-emptying studies plus one 121 g T1D tracer study.

- Bharucha AE et al. Delayed gastric emptying is associated with early and long-term hyperglycemia in type 1 diabetes
  mellitus. *Gastroenterology* 2015 (DCCT/EDIC; https://pmc.ncbi.nlm.nih.gov/articles/PMC4516593).
