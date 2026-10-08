I've finished the review. Every citation below was checked against Europe PMC, FDA decision summaries, GitHub, or the publisher's abstract, except where I mark it **[unverified]**.

**The main finding for LoopEval:** holding ICE fixed is, in effect, the UVA "net effect" replay method (Patek et al.). Its domain of validity has been measured directly (Vettoretti 2016, §2b). The field's answer to those limits has been to personalize the model first and then keep the residual (UVA), or to use a fully identified model with no residual (ReplayBG). It is also to validate against a randomized trial in which each person was observed under both treatments (Villa-Tamayo 2024).

---

## 1. Parametric population simulators

**Bergman minimal model.** Bergman RN, Ider YZ, Bowden CR, Cobelli C. *Am J Physiol* 1979;236:E667–77, doi:10.1152/ajpendo.1979.236.6.e667. This is the model all the later ones grew from. It is a small model with few parameters, fitted to frequently sampled IVGTT data. Even at this size, identifiability is a real problem (Chin & Chappell, *CMPB* 2011;104:120–134, doi:10.1016/j.cmpb.2010.08.012).

**UVA/Padova T1DM simulator.**
- **S2008.** It has 300 virtual subjects (100 adults, 100 adolescents, 100 children) sampled from a joint parameter distribution. FDA accepted it in January 2008 as a substitute for animal trials in preclinical testing of insulin treatment strategies.
  - Kovatchev, Breton, Dalla Man, Cobelli, *JDST* 2009;3(1):44–55.
  - Retrospective: Cobelli & Kovatchev, *JDST* 2023;17:1493–1505, doi:10.1177/19322968231195081.
  - The UVA–Padova multinational trial was designed entirely in silico (Kovatchev et al., *JDST* 2010;4:1374–81, doi:10.1177/193229681000400611).
- **S2013.** Dalla Man et al., *JDST* 2014;8(1):26–34. It was submitted to FDA in 2013 and added:
  - insulin action that becomes nonlinear (stronger) below a glucose threshold
  - glucagon kinetics and counter-regulation
  - new rules for setting CSII parameters and a new way of generating virtual subjects
  - The motivation was that clinical closed-loop trials showed far more hypoglycemia than S2008 predicted. The exact threshold values are **[unverified]** because I only read the abstract.
- **S2017 / "single-day."** Visentin et al., *JDST* 2018;12(2):273–281, doi:10.1177/1932296818757747. It adds time-varying insulin sensitivity across the day and the dawn phenomenon, which extends validity from single-meal to 24-hour scenarios. It also adds CGM/SMBG models and new insulin routes.
  - Builds on Visentin et al., *DT&T* 2015;17:1–7 (circadian insulin sensitivity) and on "one-day Bayesian cloning" (*IEEE TBME* 2016).
- **Exercise.**
  - Breton, *JDST* 2008;2:169–174 (doi:10.1177/193229680800200127)
  - Dalla Man, Breton, Cobelli, *JDST* 2009;3:56–67 (doi:10.1177/193229680900300107), which uses heart rate to drive the extension
  - The ETH exercise model (Deichmann et al., *Front Endocrinol* 2021, doi:10.3389/fendo.2021.723812)

**Cambridge/Hovorka model.**
- Hovorka et al., *Physiol Meas* 2004;25:905–920, doi:10.1088/0967-3334/25/4/010.
- Simulation environment: Wilinska et al., *JDST* 2010;4(1):132–144. It covers 18 synthetic subjects with intra- and inter-subject variability. It was validated against an overnight closed-loop MPC study in young people.
- OHSU variant with exercise and glucagon: Resalat et al., *PLoS ONE* 2019;14:e0217301, doi:10.1371/journal.pone.0217301. Virtual patients overestimated time in range compared with real AP users, though the difference was not significant.

**Other population platforms.**
- Medtronic-lineage "identifiable virtual patient" (IVP): Kanderian, Weinzimer, Steil, *JDST* 2012;6:371–379.
- McGill platform with 15 clinically parameterized patients: Smaoui et al., *PLoS ONE* 2020, doi:10.1371/journal.pone.0243139.
- DTU stochastic-differential-equation virtual trials: Ritschel et al., arXiv:2205.01332, 2022.

**Known limitations and critiques.**
- S2008 underpredicted hypoglycemia, which is what triggered S2013 (Visentin et al., *DT&T* 2014;16:428–434, doi:10.1089/dia.2013.0377).
- Single-meal validity held until S2017.
- Behavior was missing until the "patient decision simulator" added it: Vettoretti et al., *IEEE TBME* 2018;65:1281–90; Camerlingo et al., *JDST* 2021 (meal timing and amount variability).
- Controllers can rank differently depending on which simulator they are run on: Colmegna & Sánchez-Peña, *CMPB* 2014;113:371–382.

## 2. Replay / data-driven / digital-twin simulators

**a) UVA "net effect" replay (Patek et al.), the closest analogue to LoopEval.** A population model is inverted by regularized deconvolution to get an additive residual, the "net effect," that reproduces observed CGM exactly. Counterfactuals are then run by changing insulin inputs while the residual stays fixed.
- It was first used to set CGM accuracy requirements for non-adjunctive use: Kovatchev, Patek, Ortiz, Breton, *DT&T* 2015;17:177–186, doi:10.1089/dia.2014.0272.
- I could not find the original Patek chapter itself **[unverified]**. Hughes 2021 describes it this way.

**b) Domain of validity of the net effect method.** Vettoretti, Facchinetti, Sparacino, Cobelli, "Predicting Insulin Treatment Scenarios with the Net Effect Method: Domain of Validity," *DT&T* 2016;18:694–704, doi:10.1089/dia.2016.0148. They used UVA/Padova as the ground truth:
- **Basal ±10%:** predicted well.
- **Basal ±50%:** overestimated time in hypo- and hyperglycemia.
- **Bolus reduction to prevent a hypo:** underestimated how much reduction was needed.
- **Added correction boluses:** underestimated time in hyperglycemia.
- **Added hypotreatments:** overestimated time in hypoglycemia.

The mechanism is that the residual absorbs model mismatch: wrong insulin sensitivity or insulin action time, nonlinear insulin action at low glucose, and counter-regulation. That error does not change when insulin changes. Rescue carbs and counter-regulation that happened in the observed hypos also stay in the residual when the counterfactual avoids those hypos. **LoopEval has the same failure modes.** Its 54 mg/dL floor addresses only one side of the problem.

**c) UVA replay with a personalized model.** Hughes, Gautier, Colmegna, Fabris, Breton, *JDST* 2021;15:1326–1336, doi:10.1177/1932296820973193.
- Insulin sensitivity and meal-absorption parameters are personalized before the residual is reconstructed.
- In silico, MARD improved by 9.08 for basal changes and 6.07 for bolus changes over the original method (units not shown in the abstract). Overall MARD was under 10% with more than 95% of readings in Clarke zones A–B, across broad changes.
- That the residual is still retained on top of the personalized model is my reading of the abstract ("similar approach") **[full text not verified]**.
- Identify–Replay–Optimize for Control-IQ: Diaz C et al., *CMPB* 2023;242:107830, doi:10.1016/j.cmpb.2023.107830. It also infers unannounced meals and adjusts announced meal times.

**d) Clinical validation of UVA replay.** Villa-Tamayo, Colmegna, Breton, *DT&T* 2024, doi:10.1089/dia.2023.0595.
- They took a randomized crossover trial of hybrid vs fully closed loop (64 subject/modality pairs), replayed each subject under the arm they were not observed in, and compared with what was actually observed.
- TIR, TAR, LBGI and HBGI were equivalent. For example, HCL simulated TIR was 84.89% vs 84.31% observed.
- **Time below range failed the equivalence test.** That is the same weak point as the net effect method.

**e) The 2025 "digital twin" trial.** Kovatchev, Colmegna, Pavan, … Brown, "Human-machine co-adaptation to automated insulin delivery: a randomised clinical trial using digital twin technology," *npj Digit Med* 2025;8:253, doi:10.1038/s41746-025-01679-y (NCT05610111).
- 72 adults on Control-IQ for 6 months. The twin is a subcutaneous minimal model identified daily from CGM, insulin and meals, with unannounced meals inferred.
- Settings were optimized every two weeks, and users could replay "what-if" scenarios.
- TIR rose from 72% to 77% (p<0.01) and HbA1c fell from 6.8% to 6.6%.
- The authors say the system is specific to Control-IQ. Porting it to another algorithm requires replicating that algorithm exactly. That is LoopEval's situation with Loop and oref.

**f) ReplayBG (Padova).** Cappon, Vettoretti, Sparacino, Del Favero, Facchinetti, *IEEE TBME* 2023;70:3227–3238, doi:10.1109/TBME.2023.3286856. Code: github.com/gcappon/replay-bg (GPL-3.0) and the Python port py-replay-bg.
- A personalized UVA/Padova-derived model is identified by MCMC: unknown parameters get posterior distributions, and the rest are fixed to population values.
- **Replay is pure model simulation with no residual.** The counterfactual gets a credible interval from the parameter posterior.
- It has pluggable bolus calculator, basal controller, hypotreatment and correction handlers.
- Validated on 100 UVA/Padova subjects across 5 insulin/carb modifications. It beat the "state of the art" (net effect) in almost all of them.
- The README notes that only the single-meal model is extensively validated; the multi-meal model is still in development.
- Web front-end: Cossu et al., *JDST* 2026.

**g) Learned and hybrid models.**
- Miller, Foti, Fox, "Learning Insulin-Glucose Dynamics in the Wild," MLHC 2020 (arXiv:2008.02852): a physiological model whose dynamics vary over time via a sequence model.
- Hybrid neural ODE causal models (arXiv:2402.17233) use T1DEXI.
- These target forecasting more than validated counterfactuals.

**h) Community and industry tools.**
- **oref0.** `oref0-simulator.sh` in openaps/oref0 is a forward simulator, not a counterfactual replay. Each step sets next BG = bg + BGI + (a random fraction of the current deviation) + uniform noise. The rest of oref0 (autosens, the deviation split) runs on the simulated history. Autotune (`oref0-autotune-prep/core`) splits deviations into carb, ISF and basal buckets and recommends settings without simulating counterfactuals.
- **Tidepool.** github.com/tidepool-org/data-science-simulator ("TRSET", BSD-2) was built for FDA risk analysis of Tidepool Loop. It uses a `SimpleMetabolismModel` virtual patient, with PyLoopKit or the Swift LoopAlgorithm as controller, and scenario configs `tidepool_risk_v2`.
- **Tidepool Loop K203689.** The FDA decision summary relies clinically on the Loop Observational Study, a real-world, virtual, observational study. The text I extracted does not describe any in-silico performance study; it mentions only hardware simulators and emulators used for software testing.
- **DEKA Loop K234055.** Equivalence to Tidepool Loop was shown by 25 input vectors, 15 targeted 24-hour scenarios with a body model (meals, exercise, CGM bias, CGM loss), and about 1 million random 24-hour simulations (24 million simulated hours). 99.76% were equivalent; the rest were explained by floating-point threshold crossings.
- **Medtronic.** The IVP lineage is documented (§1). Medtronic's and Insulet's current in-silico practice for 780G and Omnipod 5 is **[unverified]**.
- **Tandem.** Control-IQ descends from UVA algorithms that were designed in silico. Tandem's own regulatory in-silico evidence is **[unverified]**: the DEN190034 summary I extracted mentions only the iDCL trial and human factors work.

## 3. Open-source tools

- **simglucose** (jxx123/simglucose, MIT). Python implementation of UVA/Padova **S2008**. 30 subjects (10 adults, 10 adolescents, 10 children), a gym-style reinforcement-learning interface, no S2013 counter-regulation.
- **ReplayBG / PyReplayBG** (see §2f).
- **LoopInsighT1 / LT1** (hpeuscher/loopinsight1, MIT, lt1.org). A TypeScript in-browser closed-loop simulator. The related paper is Schmitzer … Peuscher, *JDST* 2022;16:61–69, doi:10.1177/19322968211032249, which re-implemented AndroidAPS inside UVA/Padova T1DMS. That builds on Toffanin et al., *DT&T* 2020;22:112–120 (AndroidAPS in silico).
- **PyLoopKit + UVA/Padova:** Armiger et al., *JDST* 2022, doi:10.1177/19322968211060074. A Loop vs BiAP head-to-head; PyLoopKit is now unmaintained.
- **GluPredKit:** Wolff, Royston, Volden, *JOSS* 2024;9(101):6904, doi:10.21105/joss.06904. It is for prediction benchmarking, not closed-loop simulation. Related: Wolff et al., *DT&T* 2025 argue prediction algorithms need clinically relevant criteria beyond accuracy.
- **Other simulators:** APS_TestBed (UVA-DSA, includes fault injection), CGMSIM (teaching), CarbMetSim. Index: github.com/gcappon/awesome-diabetes-software.
- **T1DEXI:** Riddell et al., *Diabetes Care* 2023, doi:10.2337/dc22-1721. Real-world exercise data on 497 adults, available via Vivli. It is a dataset; I found no published T1DEXI-specific simulator, only proposed modeling projects.
- **PyGlucose:** I could not find any such tool **[unverified/not found]**.

## 4. Validation against clinical outcomes, and the regulatory view

**Concordance studies:**
- Kanderian 2012: IVP predictions matched a separate pediatric PID study on peak postprandial glucose and rescue-carb use.
- Wilinska 2010: Cambridge model vs an overnight MPC study.
- Visentin 2014: S2008 matched glucose traces of a clinical trial, but missed the frequency of hypoglycemia.
- Resalat 2019: virtual patients vs real AP users.
- Villa-Tamayo 2024: the strongest replay validation, because each subject's counterfactual arm was actually observed. Time below range still failed.

**FDA framework:**
- **iCGM:** 21 CFR 862.1355 (De Novo DEN170088, Dexcom G6, 2018).
- **ACE pump:** 21 CFR 880.5730.
- **iAGC:** 21 CFR 862.1356 (De Novo DEN190034, Control-IQ, Dec 2019).
- The iAGC special controls require design verification and validation with clinical data from the intended-use population in clinically relevant use scenarios. They also require human factors work, safe behavior on communication loss, traceability from risk to control, critical event logs, iCGM/ACE-only connections, and labeling of clinical performance.
- **The regulation text does not explicitly call for in-silico evidence** (based on the Cornell LII text).
- In practice, simulation has served as preclinical evidence (UVA/Padova's 2008 acceptance), risk analysis (Tidepool), and porting equivalence (DEKA). Clinical evidence came from trials (iDCL) or observational data (the Loop Observational Study), plus post-market surveillance studies.

## 5. Known pitfalls

- **Identifiability.** CGM, insulin and carb data alone cannot separate insulin sensitivity, carb ratio and meal absorption well. ReplayBG responds with MCMC posteriors and fixed population priors; UVA identifies a reduced set of parameters (insulin sensitivity and meal parameters).
- **Model mismatch dumped into the residual.** This is the core net-effect problem: counterfactual error grows with the size of the change (Vettoretti 2016).
- **Rescue carbs.** Unlogged hypotreatments stay in the residual, so replays that avoid the observed hypo show spurious highs. In the other direction, new hypos created by the counterfactual need a hypotreatment model; ReplayBG and the decision simulator include one.
- **Counter-regulation.** S2008 underpredicted hypoglycemia. S2013 added nonlinear low-glucose insulin action and glucagon. Even replay methods fail on time below range (Villa-Tamayo 2024). A hard 54 mg/dL floor is not a published approach I found; it should be treated as a modeling assumption and sensitivity-tested.
- **Sensor error.** Observed CGM includes sensor error and time lag. A replay treats them as true glucose unless it deconvolves them. Error models: Facchinetti, Sparacino, Cobelli, *JDST* 2010;4:4–14; Vettoretti et al., *Sensors* 2019;19:5320 (factory-calibrated 10-day sensor).
- **Meal models.** Announced vs actual meal times and amounts, unannounced meals, and the single-meal vs multi-meal validity of the model all matter (Camerlingo 2021; the ReplayBG README).
- **Intraday variability and time-varying sensitivity.** Addressed in S2017 and by UVA's daily re-identification.
- **Exercise.** Seen in the data only through the residual unless it is logged.
- **Algorithm fidelity.** Faithful replay needs the exact controller code (npj 2025; DEKA's equivalence testing).

## Comparison table

| Approach | Inputs | Counterfactual assumption | Validation | Strengths | Weaknesses |
|---|---|---|---|---|---|
| UVA/Padova S2008/S2013/S2017 | Population parameter distributions, scenario | Full mechanistic model, re-simulated | FDA preclinical acceptance; trace matching (Visentin 2014) | Accepted by regulators; counter-regulation (S2013); intraday variability (S2017) | Not individual; little behavior; underpredicted hypos before S2013; licensed (simglucose only implements S2008) |
| Cambridge/Hovorka, OHSU | Population parameters | Mechanistic re-simulation | Overnight MPC study; real AP users | Simple, extensible (glucagon, exercise) | Small cohorts; tends to overestimate TIR |
| Net effect replay (Patek) ≈ **LoopEval ICE** | Individual CGM, insulin, carbs + population model | Residual held fixed | In silico domain-of-validity study (Vettoretti 2016) | Reproduces real data exactly; keeps real behavior and variability | Valid only for small changes (about ±10% basal); hypo/rescue-carb bias |
| UVA personalized replay / digital twin | Individual data; meals inferred | Personalized model + residual (likely) | In silico (Hughes 2021); crossover RCT replay (Villa-Tamayo 2024); 6-month RCT (npj 2025) | Best clinical validation; works across broad changes | Time below range not equivalent; tied to one controller; code not public |
| ReplayBG | Individual data | Identified model, no residual; MCMC posterior | 100 UVA/Padova subjects × 5 scenarios | Open source; uncertainty bands; hypotreatment handlers | Fit error is not replayed; multi-meal model still in development; no clinical validation found |
| oref0-simulator | Current oref0 state | BG + BGI + random part of deviation + noise | None found | Built into oref0 | Toy forward model, not a counterfactual |
| Tidepool TRSET | Scenario configs | Simple metabolism model | Used for FDA risk analysis | Runs the real Loop algorithm | Scenario-based, not individual replay |
| ML / hybrid (neural ODE etc.) | Large datasets | Learned dynamics | Forecasting metrics | Flexible | Causal validity not established |

## The 13 most important papers

1. Kovatchev, Breton, Dalla Man, Cobelli. In silico preclinical trials. *JDST* 2009;3:44–55.
2. Dalla Man et al. UVA/Padova simulator: new features (S2013). *JDST* 2014;8:26–34.
3. Visentin et al. UVA/Padova goes from single meal to single day (S2017). *JDST* 2018;12:273–281.
4. Cobelli & Kovatchev. Developing the UVA/Padova simulator (review). *JDST* 2023;17:1493–1505.
5. Wilinska et al. Simulation environment (Cambridge). *JDST* 2010;4:132–144.
6. Visentin et al. Simulator matches the glucose traces of a clinical trial. *DT&T* 2014;16:428–434.
7. Kovatchev, Patek, Ortiz, Breton. Net effect for non-adjunctive CGM. *DT&T* 2015;17:177–186.
8. **Vettoretti et al. Net effect method: domain of validity. *DT&T* 2016;18:694–704.** Most directly relevant to LoopEval.
9. Hughes et al. Replay with a personalized metabolic model. *JDST* 2021;15:1326–1336.
10. Cappon et al. ReplayBG. *IEEE TBME* 2023;70:3227–3238.
11. Villa-Tamayo, Colmegna, Breton. Validation of UVA replay with RCT data. *DT&T* 2024, doi:10.1089/dia.2023.0595.
12. Kovatchev et al. Digital-twin co-adaptation RCT. *npj Digit Med* 2025;8:253.
13. Kanderian, Weinzimer, Steil. IVP: simulation vs clinical. *JDST* 2012;6:371–379.

Also worth reading: Vettoretti 2018 (patient decision simulator), Facchinetti 2010 (sensor error), the FDA K203689 and K234055 decision summaries, and Armiger 2022 (PyLoopKit in UVA/Padova).

**Not verified:** Patek's original net-effect chapter; whether Hughes 2021 keeps the residual; the exact S2013 hypoglycemia thresholds; Medtronic, Tandem and Insulet in-silico regulatory practice; PyGlucose.

**Suggested next steps for LoopEval** (my inference from the above, not from the papers):
- Report the size of each counterfactual change, and flag runs beyond roughly ±10–20% of the observed insulin.
- Remove or model hypotreatments separately from ICE.
- Consider personalizing insulin sensitivity before computing ICE, as UVA does.
- Validate on crossover-like real data, for example people who changed settings, the way Villa-Tamayo did.

The text extracted from the FDA decision summaries is in `docs/research/sources/fda/` (`k203689.txt`, `k234055.txt`, `den.txt`).