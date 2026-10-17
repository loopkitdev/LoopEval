# 14 — Between-meal drift: literature for named drivers (2026-10-16)

> **How this was used (2026-10-16).** Commissioned for the between-meal drift (LESSONS 76–78). Its symmetry test confirmed unlogged intake by day (LESSONS 78). The day-level insulin-action variance it ranks first is measured only as unexplained between-occasion variance and is not built.

The gap being explained: in quiet windows (>4 h after any recorded eating or bolus), real
Loop/AID CGM steps keep positive autocorrelation out to about 40 min, while the simulator's go
to zero at 20–25 min. Night-to-night CV of 00–06 insulin on quiet nights is 30% in the donors
and about 16% in the simulator.

Tags: **[checked]** means I read the abstract or full text myself. **[unverified]** means it
came only from a search-engine summary, press release or secondary citation. **[derived]** is
my own arithmetic on checked numbers.

---

## 0. Two framing results

**The real 30% is typical. It is not a data artifact.**
- Ruan Y, Thabit H, …, Hovorka R. *Diabetes Care* 2016;39:830–832. doi:10.2337/dc15-2623
  **[checked, abstract]**. 32 adults, 12 weeks of free-living hybrid closed loop, 1,918 nights.
  Within-subject CV of overnight insulin was **31% (SD 4)**, against 22% for daytime and 17%
  for the total daily dose. The per-person spread is narrow: SD 4 points. A Healio summary says
  overnight needs ranged from about 50% to 300% of a person's mean **[unverified]**.
- Dovc K et al. *Diabetes Care* 2019;42:1344–1347. doi:10.2337/dc18-2625 **[checked,
  abstract]**. 114 people on hybrid closed loop. Night-time CV of insulin delivery was
  10.7 points higher in children aged 1–6 than in adults, and about 10 points higher than in
  adolescents.
- Castagna G et al. *Diabetes Obes Metab* 2025;27:3512–3514. doi:10.1111/dom.16319
  **[checked, full text]**. 55 adults on 780G, Control-IQ or DBLG1, 770 nights. CV of hourly
  overnight insulin across nights was **>63% in every participant**, with no difference by
  hour. In multivariable regression, overnight glycaemic CV was the only predictor of
  insulin-need CV.
- **Caveat:** none of these studies excluded nights with evening-meal carry-over. They also do
  not split the CV into causes, so they set the size of the effect but do not name its
  mechanism.

**People with diabetes show persistent glucose increments; healthy people show
anti-persistent ones.**
- Ogata H et al. *Am J Physiol Regul Integr Comp Physiol* 2006. doi:10.1152/ajpregu.00241.2006
  **[checked, abstract]**. Detrended fluctuation analysis on CGM, in the >2 h regime. Healthy:
  α = 1.25 ± 0.29, below the random-walk value of 1.5, so increments are negatively
  correlated. Diabetes: α = **1.65 ± 0.30**, so net flux persists "for many hours". This is the
  same signature as the 40-min step-ACF, but measured with meals included.
- Gough DA et al. *Ann Biomed Eng* 2003. doi:10.1114/1.1535411 **[checked, abstract]**. The
  blood-glucose band edge is about 1×10⁻³ Hz (a period of about 17 min). In other words, true
  glucose has little power faster than about 10–20 min. The real 40-min crossing therefore
  needs a driver with energy at periods of roughly 1–3 h.
- **[derived]** For a narrow-band wander of period P, the ACF of steps first crosses zero at
  about P/4. A 40-min crossing means components with periods around **2–3 h**. The simulator's
  20–25 min crossing corresponds to the sensor-noise band.

---

## 1. Unrecorded small intake between meals

| Claim | Number | Source |
|---|---|---|
| Share of US adults who snack on a given day | 97% (2003–06) | Piernas & Popkin, *J Nutr* 2010, doi:10.3945/jn.109.112763 **[checked]** |
| Energy from snacks | **24%** of daily energy; snack occasions rose by 0.97/day since 1977; sweetened beverages, candy and desserts gained most | same **[checked]** |
| Snack occasions per day | mean **2.2/day** (NHANES 2007–08); 1 in 6 men and 1 in 5 women snack ≥4 times/day | USDA What We Eat in America data brief **[unverified]** |
| Eating occasions per day | 5.6/day (NHANES 2009–10) | search summary **[unverified]** |
| Caloric coffee and tea add-ins | 67.5% of coffee drinkers and 33.4% of tea drinkers use them; +69 and +43 kcal/day; mostly sugar | An R, NHANES 2001–12, *Public Health* 2017 (press reports only) **[unverified]** |
| Night-time intake | 5.7% of energy and **6.8% of sugar** eaten between 22:00 and 05:59 | An R et al., *J Hum Nutr Diet* 2019, doi:10.1111/jhn.12671 **[checked]** |
| Night eaters | 36% ate between 23:00 and 05:00 on at least 1 of 3 days, taking about 15% of their energy then (ad-lib vending inpatient study, non-diabetic) | Gluck ME et al., *AJCN* 2008, doi:10.1093/ajcn/88.4.900 **[checked]** |
| Recording behaviour of T1D pump users | carbs documented on 76.6% (SD 31.7) of days; 13.0% (SD 16.9, range 0–53) of boluses given without the calculator; 2 of 19 people did this for about 50% of boluses | Groat D et al., *JDST* 2017;11:233, PMC5478025 **[checked, full text]** |
| Missed boluses in paediatric AID users | 2.2/day; each one costs about 10 TIR points | DT&T 2024, via a Medtronic press release **[unverified]** |
| Energy under-reporting | consistent and BMI-dependent; not all foods equally under-reported; which foods is unknown | Ravelli & Schoeller 2020 (search summary) **[unverified]** |

**[derived]** 24% of about 2,100 kcal over 2.2 occasions is about 230 kcal per occasion,
roughly 25–30 g of carbohydrate if half the energy is carbohydrate. Unannounced, that is far
too large to look like "quiet". So the drift-relevant part has to be the **small**
occasions: a coffee with sugar or milk (about 5–15 g), juice or soda sips, a handful of
something. Those are exactly what nobody logs.

**I found no study giving the rate or size of *unlogged* intake in AID users.** That number
has to come from the donor data, not from the literature.

**Diagnostic that would separate intake from physiology:** unlogged intake drives
**upward-first** excursions followed by a Loop response. Symmetric physiology (sensitivity,
EGP or clearance wander) does not. Two checks in quiet windows:

- skew of 30–60-min glucose changes;
- up-run versus down-run durations, real against simulated.

---

## 2. Within-day and day-to-day variation in delivered insulin's effect

| Mechanism | Evidence | Source |
|---|---|---|
| **Interoccasion aspart PK in pump users** | 70 pump users admitted twice, 1–6 weeks apart. tmax 66 (22) min. Intra-subject CV of tmax **27%** (healthy subjects 15%) and inter-subject CV 33%. Nearly **40% of tmax variance is between occasions**, which the authors attribute to cannula depth, site age and perfusion. Clearance MCR 16.8 (7.4) mL/kg/min with **13% of its variance between occasions**. Background plasma insulin: 28% of variance between occasions. | Haidar A et al., *Diabetes Care* 2013;36:e173–e174, doi:10.2337/dc13-0485 **[checked, full text]** |
| → Clearance CV between occasions | about **16%** (= 44% total CV × √0.13). At constant delivery, plasma insulin scales with 1/MCR, and the depot does not buffer this. | **[derived]** |
| **Day-to-day insulin action under a fasting clamp** | 50 T1D, two 24-h euglycaemic clamps at steady state on glargine-300. Within-subject CV of insulin exposure was 17.4%, but CV of **glucose-infusion AUC was 34.8%**, of GIRmax 27.9%. Effect varies more than exposure even with meals, activity and sensor removed. | Becker RHA et al., *Diabetes Obes Metab* 2015, doi:10.1111/dom.12416 **[checked, full text]** |
| → Converted to whole-body flux | GIR averaged 1.27 mg/kg/min. Total glucose use is roughly GIR plus residual EGP, about 3 mg/kg/min (assumption). An SD of 0.44 mg/kg/min is then about **10–15% of total flux** per day. | **[derived]** |
| Basal CSII bioavailability over 24 h | 24-h absorption within 3% of the dose delivered, on two consecutive days (8 patients) | Lauritzen T et al., *Diabetologia* 1983 **[unverified]** |
| Skin temperature | serum insulin at 30 and 45 min correlated with injection-site skin temperature (p<0.0008) and inversely with fat thickness. The abstract gives no slope. | Sindelka G et al., *Diabetologia* 1994, doi:10.1007/BF00408474 **[checked]** |
| | Sauna raises absorption by about 110%. A 30→37 °C site temperature gives about 2× serum insulin at 45 min. | Koivisto 1980 (*BMJ*) and a forum restatement of Sindelka **[unverified]** |
| Insulin degradation in the reservoir | potency within 95–105% over 6–7 days at 37 °C with agitation; lispro within 4% over 48 h | Senesh 2010 (PMC2825630) and Lougheed 1997 (*Diabetes Care*) **[unverified]** |
| Caffeine | IV caffeine lowered insulin sensitivity by **15%** (clamp, 12 healthy subjects); adrenaline 5×, FFA up | Keijzers GB et al., *Diabetes Care* 2002, doi:10.2337/diacare.25.2.364 **[checked]** |

**[derived] Depot-buffering argument.** Under steady basal, a change in the absorption-rate
constant (from temperature, posture or blood flow) does not change the steady-state supply. It
only releases or retains a fraction of the depot once.

- With depot ≈ basal rate × mean residence time (about 1–1.5 h), a 20% rate change moves
  about 0.2–0.3 U over about 1 h.
- That is roughly 10–15 mg/dL at ISF 50, once per perturbation.
- Absorption-*rate* drivers are therefore second-order for an overnight CV. *Potency*-like
  drivers are not buffered: clearance, bioavailability and day-level sensitivity.

---

## 3. CGM lag variability and slow sensitivity drift

- Vettoretti M et al. *Sensors* 2019;19:5320 (Dexcom G6, factory-calibrated; 177 traces,
  36 people wearing two sensors; YSI reference) **[checked, full text via Europe PMC
  PMC6928894]**. Fitted model:
  `IGs = (a0 + a1·t + a2·t²)·(BG ⊗ e^{−t/τ}/τ) + b0 + AR(2)`.
  - τ: median **3.1–3.8 min**, IQR 1.7–6.0.
  - Gain a0 0.95 (IQR 0.87–1.03).
  - **Gain drift a1 0.002/day, IQR −0.034 to +0.027/day.** a2 ≈ 0 ± 0.003/day².
  - Offset b0 7.3 mg/dL.
  - Noise AR(2): α1 1.30, α2 −0.46, σ 3.2 mg/dL.
  - **[derived]** AR pole modulus √0.46 = 0.68 per 5-min sample, so the e-folding time is
    about 13 min and the stationary SD about 7.5 mg/dL.
- **[derived]** A gain drift of ±3%/day at 150 mg/dL is about **±0.2 mg/dL per hour**.
  Lag variability of a few minutes changes nothing at 40-min scales.
- Published CGM error models therefore have **no hours-scale component**. Calibration drift
  works on a scale of days, and the correlated noise decays within about 15 min. Literature
  models were built for 12-h calibration windows, and the G6 model extends to the 10-day
  sensor life.
- I found no paired-YSI or two-sensor study reporting an hours-scale correlated error for
  G6, G7 or Libre 3. One G7 study reports a mean lag of 3.5 min **[unverified]**.
- **Verdict: the sensor cannot supply the 40-min correlation or the insulin CV.** The
  insulin CV point holds because Loop would only respond to a slow sensor wander, and none is
  documented at this scale.

---

## 4. Controller-induced wander

- I found **no published spectral or ACF analysis of AID glucose** that separates
  controller-induced oscillation from disturbance. Searches came back empty, and Miller &
  Strange 2007 (doi:10.1177/193229680700100506) **[checked]** is a Fourier smoothing method,
  not a decomposition.
- The physiological analogue is real. Under constant glucose infusion, healthy people show
  glucose and insulin oscillations with periods of about 120–126 min, generated by the
  delayed glucose–insulin feedback loop itself.
  - Sturis J et al., *JCI* 1991 **[unverified, search summary]**.
  - In T1D the AID controller is that loop, with subcutaneous delays of tmax about 66 min.
- **Relevance to the simulator.** It runs the real Loop, so it already reproduces controller
  dynamics, but only for the virtual body's insulin timing.
  - If the virtual population's insulin action is closer to Loop's fixed model curve than
    real people's is, the simulator under-produces controller ringing.
  - Real people have between-subject tmax CV 33% and occasion-to-occasion CV 27% (Haidar 2013).
  - Mismatch between true and modelled insulin timing is a named, evidenced source of 2–3 h
    closed-loop wander.

---

## 5. Slow physiological rhythms without meals

- **Wilinska ME, …, Hovorka R.** *JDST* 2010;4:132, doi:10.1177/193229681000400117
  **[checked, full text PMC2825634]**.
  - The Cambridge simulator, validated against overnight closed loop in young people,
    represents intra-subject variability as **sinusoids of 5% amplitude and 3-h period** with
    random phase U[0,3 h].
  - These sit on EGP0, F01, k12, the three insulin sensitivities SID/SIE/SIT, and remote
    insulin-action rates.
  - **The paper gives no evidence for the 5% or the 3 h.** It is the kind of unnamed term the
    project rule excludes. It is also too small to make a 25% night-to-night CV.
  - The point to take from it: the most-validated overnight-CL simulator *needed* a 3-h
    variability component to match clinical data.
- Ultradian insulin and glucose oscillations in healthy people (100–150 min) are generated by
  beta-cell feedback (Sturis 1991 **[unverified]**), which T1D lacks. There is no evidence for
  an intrinsic beta-cell-independent ultradian EGP rhythm in T1D.
- **Sleep stages:**
  - REM/NREM-locked glucose effects in T1D are only described in small or preliminary
    studies.
  - One Diabetologia study (20 pump users, up to 15 nights each) found worse objective sleep
    linked to higher overnight glucose SD and CV, with no change in TIR (search summary,
    **[unverified]**, doi:10.1007/s00125-021-05500-9).
  - A claimed "REM about 5% lower" figure comes from a consumer blog. Not usable.
- **Day-to-day insulin sensitivity under strict control.** Becker 2015 (§2) is the cleanest
  evidence: fasting, bed rest, constant insulin, and still a 35% CV in glucose-infusion AUC.
  The authors do not name a cause.

---

## Ranked buildable components

Shares are my judgement of how much of each gap a component could plausibly close. They are
not measurements.

**1. Day-level insulin-action multiplier: interoccasion clearance, bioavailability and
sensitivity.**
- **Form:** a lognormal multiplier on plasma insulin effect, redrawn per day or per infusion
  site, with optional AR(1) carry-over between days.
- **Parameters:** log-SD about **0.15–0.20**, built from clearance (about 16% CV,
  Haidar 2013 [derived]) and clamp glucose-flux (about 10–15% of total flux,
  Becker 2015 [derived]). Ruan 2016 gives the outcome to check against: night insulin CV 31%.
- **Overnight CV gap:** the missing variance is √(30² − 16²) ≈ 25% CV. This component could
  supply **most of it, perhaps 50–80%**.
- **ACF gap:** modest. It produces a slow controller-tracked drift after each change, and
  with a per-site redraw the changes come every 2–3 days.
- **Rule caveat:** in the literature this is *measured interoccasion variance*, not a
  mechanism. It is named only at the level of "insulin clearance and absorption vary between
  occasions". Pete should rule on whether that counts as a named component.

**2. Unlogged small intake.**
- **Form:** a per-person rate and size of unlogged occasions, sitting on top of the logged
  meals, made of small fast-sugar items (coffee add-ins, juice, sweets).
- **Parameters:** about 5–15 g each. The rate is unknown for AID users and is the key
  quantity to measure from the donors (the upward-skew test above). The general-population
  ceiling is about 2.2 snack occasions/day and 24% of energy, mostly not small.
- **Daytime ACF gap:** potentially the **largest** contributor, because a 10-g unannounced
  carb plus Loop's response is a 1.5–3 h excursion, which matches P/4 ≈ 40 min.
- **Overnight:** small. 22:00–06:00 carries about 6–7% of sugar intake, so perhaps 5–15% of
  the overnight gap.

**3. Per-person and per-occasion insulin timing that differs from Loop's model curve.**
- **Form:** per-person tmax drawn with between-subject CV about 33% around 66 min, and
  per-site CV about 27% (Haidar 2013).
- **Effect:** sets the size of controller-induced 2–3 h ringing. Could supply some of the ACF
  gap (perhaps 10–30%) and a little of the insulin CV.
- **Check first:** whether the current simulator already does this.

**4. Caffeine (daytime).**
- **Form:** −15% insulin sensitivity per dose (Keijzers 2002, IV, healthy subjects), decaying
  with the roughly 5-h caffeine half-life, given to coffee drinkers (about 50% of adults per
  day [unverified]).
- **Effect:** small but real, and only in morning and midday quiet windows: perhaps 5–10% of
  the daytime ACF gap and about 0 overnight.

**5. Absorption-rate transients (skin temperature, posture, warm shower).**
- Depot buffering limits each event to about 10–15 mg/dL.
- **No usable per-°C slope exists**: Sindelka gives a correlation only, and Koivisto's sauna
  result is extreme heat.
- Probably under 5% of either gap.

**6. Sensor slow drift and lag variability.** Quantified as about 0.2 mg/dL/h and a few
minutes. **About 0%.** Do not build.

**7. Reservoir insulin degradation.** Under 5% over days. **About 0%.**

---

## Can named evidence close the gap? Partly.

- The **size** of real overnight insulin variability is well established and matches the
  donors: Ruan 31%, Castagna, Dovc. So the 30% is real.
- The **causes** are not established. The best evidence is clamp and PK interoccasion
  variance (Becker, Haidar), which is itself unexplained variance at the mechanism level.
- For the **daytime 40-min ACF**, the most plausible named cause is unlogged small intake.
  There is no AID-specific rate in the literature, so it has to be measured from the donors.
- If donor quiet windows show **symmetric** drift, intake is not the answer. What is left
  would be day- and hours-scale insulin-action variability, which the literature measures
  only as unexplained interoccasion variance. Then the rule "named mechanisms only" cannot be
  fully met from current evidence.
