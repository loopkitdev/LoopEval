I've written the full literature review below, with citations (venue plus DOI or URL). One caveat on sourcing: I checked the major papers by web search during this session. References marked **[unverified]** come from memory and should be checked against PubMed or the publisher before you cite them.

---

# How the field evaluates insulin-dosing algorithm changes, compared with our replay and Pareto-lift method

## 1. Clinical outcome metrics and consensus

**Time-in-range (TIR) consensus.**
- **Battelino et al. 2019** (*Diabetes Care* 42(8):1593–1603) [details unverified] is the international consensus that standardised the CGM metrics: TIR 70–180 mg/dL, TBR <70 and <54, TAR >180 and >250, CV, and GMI.
  - Targets for most adults with T1D: TIR >70%, time <70 below 4%, time <54 below 1%.
  - Data sufficiency: at least 14 days with at least 70% of CGM readings captured.
- **Battelino et al. 2023**, "Continuous glucose monitoring and metrics for clinical trials: an international consensus statement," *Lancet Diabetes Endocrinol* 11(1):42–57, doi:10.1016/S2213-8587(22)00319-9 (https://pubmed.ncbi.nlm.nih.gov/36493795/).
  - It recommends CGM metrics as primary or secondary endpoints in all diabetes trials.
  - It treats hypoglycaemia (especially time <54) as an endpoint in its own right, not a by-product.
- **Beck et al. 2019** ("Validation of time in range as an outcome measure," *Diabetes Care*) [unverified] ties TIR to microvascular outcomes, which is why TIR gets used as a surrogate endpoint.

**Composite and risk indices.**
- **LBGI, HBGI and BGRI (Kovatchev).** These come from a symmetrising log transform of the BG scale, so hypo and hyper excursions carry comparable risk weight.
  - Kovatchev, Cox, Gonder-Frederick, Clarke, *Diabetes Care* 1997;20:1655–1658 [unverified].
  - LBGI predicts severe hypoglycaemia better than TBR does.
- **Magni risk.** I did not verify a separate "Magni risk" index. The Magni et al. 2008 paper defines CVGA (next item). The "Magni" risk function some toolkits use is a re-parameterisation of the Kovatchev risk function [unverified].
- **CVGA (Control Variability Grid Analysis).** Magni, Raimondo, Dalla Man, Breton, Patek, De Nicolao, Cobelli, Kovatchev, *J Diabetes Sci Technol* 2008;2(4):630–635 (https://pmc.ncbi.nlm.nih.gov/articles/PMC2769756).
  - Each subject is plotted as one point: minimum BG against maximum BG over a period.
  - The authors present it explicitly as a way to compare *different control laws and different tunings of one controller* on the same population.
  - It is the field's closest standard to our hypo-vs-hyper trade-off picture. But it works on extremes and zones, not on a frontier across a dial sweep.
- **Glycemia Risk Index (GRI).** Klonoff, Wang, Rodbard et al., *J Diabetes Sci Technol*, online March 2022; print 2023;17(5):1226–1242; doi:10.1177/19322968221085273.
  - Formula: GRI = 3.0·VLow + 2.4·Low + 1.6·VHigh + 0.8·High.
  - It has two components (hypo and hyper), shown on the "GRI Grid." The weights were calibrated against clinician ratings of AGP traces.
  - It is the best-known modern scalar composite. Its fixed weights are a value judgement that a Pareto approach avoids.

**Forecast accuracy (relevant to learned predictors).**
- MARD.
- Clarke Error Grid (Clarke et al. 1987, *Diabetes Care*) [unverified].
- Parkes or consensus grid (Parkes et al. 2000, *Diabetes Care*) [unverified].
- Surveillance Error Grid: Kovatchev, Wakeman, Breton, Kost, Louie, Tran, Klonoff, *J Diabetes Sci Technol* 2014;8(4):673–684, doi:10.1177/1932296814539590.
- Diabetes Technology Society Error Grid: Klonoff et al., *J Diabetes Sci Technol* 2024;18(6):1346–1361.
- For forecasts that drive dosing, the literature warns that point-accuracy metrics weight errors without regard to the dosing decision. That is why risk-zone grids exist.

**How the TIR vs hypoglycaemia trade-off is handled.**
1. **Hypo as a co-primary endpoint or safety constraint.** Pivotal AID trials report TIR as primary, with time <54, severe hypoglycaemia and DKA as safety endpoints, and often a non-inferiority bound on TBR.
2. **Scalar risk composites:** BGRI, GRI and LBGI-weighted costs. These are often used directly as controller-tuning objectives.
3. **2-D grids:** CVGA and the GRI grid.

I found no standard AID paper that sweeps an aggressiveness parameter for both arms and judges improvement by dominance of the TIR-vs-TBR frontier. In-silico tuning papers do report aggressive, conservative and adaptive variants (for example, MPC tuning work such as the HAL "Tuning of an artificial pancreas controller…", https://hal.archives-ouvertes.fr/hal-02908200). But they usually collapse the result to a single risk score or a lexicographic "no increase in hypo" rule. Multi-objective or Pareto MPC tuning exists in control-engineering venues, but not as an evaluation standard. **As far as I can tell, frontier dominance across a matched dial sweep is unusual and likely novel as a primary decision rule.**

## 2. How AID algorithm changes are evaluated

**In silico (preclinical).**
- **UVA/Padova simulator.**
  - Kovatchev, Breton, Dalla Man, Cobelli, "In Silico Preclinical Trials: A Proof of Concept in Closed-Loop Control of Type 1 Diabetes," *J Diabetes Sci Technol* 2009;3(1):44–55 [volume and pages unverified].
  - In January 2008 the FDA accepted it as a substitute for animal trials in preclinical testing of insulin strategies (Master File 1521).
  - Cohort: 100 adults, 100 adolescents and 100 children (a 10/10/10 subset is distributed with the commercial version).
- **2018 update.** Visentin et al., "The UVA/Padova Type 1 Diabetes Simulator Goes From Single Meal to Single Day," *J Diabetes Sci Technol* 2018;12(2):273–281, doi:10.1177/1932296818757747. It adds intraday insulin-sensitivity variability, dawn phenomenon and CGM error models.
- **Typical scenario design:**
  - Multi-day meal protocols with carb-count errors, missed or late boluses, exercise, and sensitivity changes.
  - Results reported as TIR, TBR, LBGI/HBGI and CVGA across the cohort.
- I found no formal multi-society consensus on in-silico testing protocols. Practice is set by the FDA master-file precedent and the JDRF Artificial Pancreas Consortium's habit of pre-testing controllers in silico [consortium detail from a Cobelli presentation, https://www.aifa.gov.it/documents/20142/1674533/2022.05.27_presentazione_Claudio-Cobelli.pdf].

**Replay or "digital-twin" simulation on real data.** These are the field's closest analogues to our method.
- **ReplayBG.** Cappon, Vettoretti, Sparacino, Del Favero, Facchinetti, *IEEE Trans Biomed Eng* 2023;70(11):3227–3238 (open source: https://github.com/gcappon/replay-bg).
  - Fits a personalised physiological model to insulin, carbohydrate and CGM data with Bayesian MCMC, then replays the same segment under an alternative therapy.
  - Validated on 100 UVA/Padova virtual subjects over five therapy-modification scenarios.
- **UVA replay methodology** (Patek, Breton et al.; 2020 *JDST* resimulation work [full citation unverified]).
- **Villa-Tamayo, Colmegna, Breton, "Validation of the UVA Simulation Replay Methodology Using Clinical Data: Reproducing a Randomized Clinical Trial,"** 2024 [venue unverified; PubMed ID 38662426, https://busqueda.bvsalud.org/portal/resource/es/mdl-38662426]. This is the most relevant validation study:
  - They replayed 64 subject/modality pairs from a hybrid vs fully closed-loop crossover RCT, swapping each subject to the other modality.
  - TIR, TAR, LBGI and HBGI were equivalent to what was observed. **TBR failed equivalence.**
  - This is direct evidence that replay methods are least reliable for exactly the hypoglycaemia axis we score on.

**Clinical evaluation.**
- **Pivotal RCTs and crossover trials.** Example: Brown et al. 2019, *NEJM*, iDCL/Control-IQ [unverified details]. These typically use TIR as primary with a pre-specified non-inferiority margin on time <54, run 3–6 months, and are pre-registered on ClinicalTrials.gov.
- **CREATE trial.** Burnside et al., *NEJM* 2022;387:869–881, doi:10.1056/NEJMoa2203913.
  - Open-label RCT in New Zealand (n=97) of AndroidAPS 2.8 running the OpenAPS 0.7.0 algorithm against sensor-augmented pump.
  - Primary endpoint: TIR over days 155–168. Adjusted difference about 14 points, with no increase in hypoglycaemia.
- **Jaeb Loop Observational Study.** Lum et al., "A Real-World Prospective Study of the Safety and Effectiveness of the Loop Open Source Automated Insulin Delivery System," *Diabetes Technol Ther* 2021;23(5):367–375, doi:10.1089/dia.2020.0535; NCT03838900.
  - Single-arm, n=558. TIR rose from 67% to 73%. Severe hypoglycaemia fell from 181 to 18.7 per 100 person-years.
  - It compares each participant against their own baseline, so there is no concurrent control.
- **Tidepool Loop FDA clearance.** K203689, cleared 23 January 2023 as an interoperable automated glycemic controller (iAGC, product code QJI).
  - Clinical evidence came mainly from the Jaeb observational dataset, restricted to an intended-use subgroup of about 175 [figure from secondary summaries; check the 510(k) summary at https://tidepool.org/documents].
  - FDA required post-market surveillance because the population was not representative.
  - Tidepool also published "The First Regulatory Clearance of an Open-Source Automated Insulin Delivery Algorithm" (https://pubmed.ncbi.nlm.nih.gov/37051947/).
  - Implication: real-world, single-arm evidence plus in-silico and hazard analysis was accepted for an algorithm-plus-guardrails product. Iterative algorithm changes after clearance go through change-control processes I did not investigate.
- **Clinical practice consensus.** Phillip et al. 2023, *Endocrine Reviews*, "Consensus recommendations for the use of AID technologies in clinical practice" [unverified].

## 3. Off-policy and counterfactual evaluation from observational data

**General methods.**
- **Importance sampling and per-decision IS** (Precup et al. 2000) [unverified].
- **Doubly robust OPE** (Jiang & Li, ICML 2016; Thomas & Brunskill, ICML 2016) [unverified].
- **Fitted-Q evaluation** (Le, Voloshin, Yue, ICML 2019) [unverified].
- **G-computation and g-methods for time-varying treatments** (Robins 1986; Hernán & Robins, *Causal Inference: What If*) [unverified].
- **Dynamic treatment regimes** (Murphy 2003, *JRSS-B*) [unverified].
- Shared assumptions:
  - Sequential ignorability (no unmeasured confounders of dose and outcome).
  - Positivity or overlap (the evaluated policy only takes actions the behaviour policy took with non-trivial probability).
  - Correct outcome or Q-models for DR and FQE.
  - Markov or stationarity assumptions in infinite-horizon settings.
- **Gottesman et al. 2019**, "Guidelines for reinforcement learning in healthcare," *Nature Medicine* 25:16–18, doi:10.1038/s41591-018-0310-5. Its warning: with limited state-action coverage and high-variance IS weights, OPE can confidently endorse policies that differ from clinicians' behaviour exactly where data are thin.

**Applied to diabetes.**
- **Luckett, Laber, Kahkoska, Maahs, Mayer-Davis, Kosorok**, "Estimating Dynamic Treatment Regimes in Mobile Health Using V-Learning," *JASA* 2020;115(530):692–706, doi:10.1080/01621459.2018.1537919. Applied to T1D glucose control.
- **Zhu, Li, Georgiou**, "Offline Deep Reinforcement Learning and Off-Policy Evaluation for Personalized Basal Insulin Control in Type 1 Diabetes," *IEEE JBHI* 2023, doi:10.1109/JBHI.2023.3303367.
  - Policy: TD3 plus behaviour cloning. Evaluation: FQE on UVA/Padova and OhioT1DM.
  - OPE was validated only by rank correlation with simulator ground truth.
- **Emerson, Guy, McConville**, "Offline reinforcement learning for safer blood glucose control in people with type 1 diabetes," arXiv:2204.03376 (*J Biomed Inform* 2023 [unverified]).
- **Emerson et al.**, PAINT (offline RL from human feedback), arXiv:2501.15972.
- Off-policy interval estimation on OhioT1DM (arXiv:2309.13278).
- In practice, most diabetes offline-RL papers **validate in a simulator** rather than trust OPE alone on real data.

**Contrast with replay using a fixed residual.**
- **What our approach assumes:**
  - Like ReplayBG and UVA replay, it is a *model-based* counterfactual: a physiological or pharmacodynamic model plus a residual or "net effect" signal inferred from observed data.
  - The residual (meals, exercise, sensitivity drift, model error) is assumed **invariant to the policy change**.
  - It needs no positivity condition and no propensity model. Its weakness is structural.
- **Where this can fail:**
  1. **Behavioural feedback.** People bolus, eat rescue carbs and override settings in response to the controller. Rescue carbs after a low are in the residual and would be "replayed" even when the candidate avoids the low. A more aggressive candidate also loses the rescue carbs the real user would have taken. Both effects bias TBR.
  2. **Misspecified insulin action and sensitivity** turn directly into counterfactual errors. These errors grow the further the candidate's insulin trajectory moves from what was observed.
  3. **The residual absorbs model error**, which is then treated as exogenous.
- The Villa-Tamayo validation result (TBR not equivalent) is the strongest empirical warning here.
- **Compared with OPE:** replay extrapolates more smoothly to policies far from the data, but its bias cannot be diagnosed from the data alone. OPE has diagnosable variance (effective sample size, weight diagnostics) but collapses when the policies differ substantially.
- I found no published work that combines replay with a doubly-robust correction. That could be a useful idea.

## 4. Statistical practice

- **Data length.** Riddlesworth, Beck et al., "Optimal Sampling Duration for Continuous Glucose Monitoring to Determine Long-Term Glycemic Control," *Diabetes Technol Ther* 2018 (https://pubmed.ncbi.nlm.nih.gov/29565197/) [author order unverified].
  - Data: 257 people with T1D over 3 months.
  - TIR and TAR correlations with the 3-month values plateau around 14 days (R² 0.84–0.86).
  - **Time <70 is weaker (R² 0.76).** Later error-based work suggests 14 days is too short for individual-level precision, especially for hypoglycaemia: about 29 days to keep TIR mean absolute error below 5% in 90% of patients (*BMJ Open Diabetes Res Care* 2025, https://drc.bmj.com/content/13/1/e004768).
  - Time <54 is a rare-event metric, and per-donor estimates over weeks are noisy.
- **Block bootstrap.**
  - Moving-block bootstrap (Künsch 1989, *Ann Stat*) and stationary bootstrap (Politis & Romano 1994, *JASA*) [both unverified].
  - These are standard for autocorrelated series. Weekly blocks respect circadian and weekly structure.
  - AID trials instead use mixed models or ANCOVA on per-participant summaries. Bootstrap CIs on paired within-donor differences are methodologically sound but uncommon in clinical AID papers.
- **Multiplicity and forking paths.**
  - Gelman & Loken 2014, "The statistical crisis in science," *American Scientist* [unverified].
  - Trials control multiplicity through pre-registration and hierarchical endpoint testing.
  - In algorithm search, repeatedly scoring candidates on the same donor pool overfits the evaluation set ("adaptive data analysis"; Dwork et al. 2015, *Science* [unverified]).
  - The field mostly handles this with simulator benchmarks and independent clinical trials. Offline-RL papers rarely address it.
- **Heterogeneity of treatment effect and personalisation.**
  - AID trials report subgroup analyses (age, baseline HbA1c, baseline TIR). The consistent finding is that larger gains come from worse baselines.
  - Personalised-policy evaluation in the dynamic-treatment-regime literature uses cross-fitting.
  - CVGA's per-subject points were partly designed to show heterogeneity.
- **Hold-out and leakage.** For forecasting, standard practice is a chronological split per patient (as in OhioT1DM's train/test split). Patient-level leakage, where the same patient appears in both training and test data, is a common criticism of glucose-prediction ML papers.

## 5. Public datasets

- **OhioT1DM.** Marling & Bunescu 2020, "The OhioT1DM Dataset for Blood Glucose Level Prediction: Update 2020," KDH@ECAI, CEUR-WS Vol-2675 (https://webpages.charlotte.edu/rbunescu/data/ohiot1dm/OhioT1DM-dataset.html).
  - 12 people, 8 weeks each, with CGM, insulin, meals and wearables. Available on request with a data-use agreement.
  - Too small for population claims, and the participants used pumps, not AID.
- **T1DEXI and T1DEXIP** (Jaeb / Helmsley): 4 weeks for about 500 adults, plus a pediatric cohort, with CGM, insulin, exercise and heart rate. Access is through Vivli. Primary paper: Riddell et al., *Diabetes Care* 2023 [author unverified].
- **Tidepool Big Data Donation Project** (launched 2017; https://tidepool.org/bigdata). Tens of thousands of donors, including DIY Loop users. Access is through partner agreements, with a subset free.
- **OpenAPS Data Commons and Nightscout Data Commons.** Community-donated data from DIY AID users. I could not find a recent formal descriptor paper (Lewis's OpenAPS Data Commons work [unverified]).
- **Jaeb public datasets.** REPLACE-BG, DCLP3 / iDCL (Control-IQ), the Loop Observational Study, and others are available on the Jaeb public-dataset site [unverified listing].
- **DiaData.** Cinar & Maleshkova, arXiv:2508.09160; Zenodo doi:10.5281/zenodo.16874128.
  - It integrates 13–15 public T1D CGM datasets (about 1,700 subjects) at 5-minute resolution.
  - **It is CGM-centric. Insulin data are largely absent, so it does not support dosing replay.**

## 6. Critical comparison with our methodology

**Standard practice:**
- TIR and time <54 as the outcome axes (Battelino 2019/2023).
- Paired within-subject comparison, as in crossover designs.
- Replay or digital-twin counterfactual simulation on real data (ReplayBG; UVA replay).
- Hold-out splits and leakage checks for learned predictors.
- Reporting a multi-subject mean.
- Oracle and upper-bound baselines (common in ML, less so in clinical work).

**Uncommon or novel:**
- **Matched aggressiveness sweeps with a frontier-dominance decision rule.**
  - This is not established practice. The nearest analogues are CVGA (designed for comparing tunings) and the GRI two-component grid.
  - Its main strength: it separates "a better algorithm" from "the same algorithm tuned more aggressively." Single-setting comparisons (including many RCTs and in-silico papers) cannot make that separation. A candidate can only "win" if it gives more TIR at equal hypo.
  - I consider this a real methodological contribution worth writing up.
- Weekly block-bootstrap CIs on the frontier lift.
- Using donated real-world DIY AID data (Tidepool, Nightscout) as the replay corpus, instead of a simulator cohort.

**Known weaknesses the literature warns about:**
1. **Replay is least valid for hypoglycaemia.** Villa-Tamayo et al. found TBR failed equivalence even with a mature replay method. With time <54 as one of our two axes, the lift estimate may be most biased exactly there.
   - Fixed-residual replay keeps rescue carbs and user overrides that were caused by the original policy. That likely makes aggressive settings look safer than they are, or penalises conservative ones, depending on direction.
   - **Recommendation:** validate the replay against a natural experiment, such as donors who changed settings or algorithm versions (the analogue of the UVA RCT reproduction). Also report how far each candidate's insulin trajectory moves from the observed one.
2. **Extrapolation without positivity diagnostics.** Unlike OPE, replay gives no built-in warning when the candidate moves far from the data (Gottesman 2019). A support or overlap metric per sweep point would help.
3. **Rare-event noise in time <54.** Riddlesworth 2018 and later error-based work show hypo metrics need more than 14 days, often around a month, for stable per-person estimates. Frontier dominance in a low-TBR operating band is especially sensitive to this.
   - Consider minimum-data thresholds per donor.
   - Consider LBGI as a smoother companion to time <54.
4. **Garden of forking paths.** Iterating candidates against the same donor pool, plus choosing the operating band, the dial range and the dominance definition after seeing results, inflates false "lifts."
   - The literature's remedy is pre-registration and a locked hold-out.
   - Recommendation: freeze a donor hold-out set used only for final confirmation, pre-specify the band and the dominance test, and count how many candidates were tried.
5. **Mean as headline hides heterogeneity.** The AID trial literature consistently reports heterogeneous benefit. A mean lift can hide harm to a subgroup, for example donors with low baseline TBR or children. Report the fraction of donors with positive lift and the worst decile, CVGA-style.
6. **Selection bias in the donor population.** Tidepool and Nightscout donors are self-selected, technically engaged DIY users. FDA flagged the same non-representativeness in the Jaeb Loop data when clearing Tidepool Loop.
7. **Oracles bound headroom only within the model.** If the replay model is misspecified, oracle headroom inherits that error.

**Bottom line.** The outcome metrics and the basic paired replay are standard and defensible. Frontier dominance across a matched aggressiveness sweep is a real improvement over the field's single-setting or scalar-composite comparisons. The biggest gap against the literature is that the replay is not validated for hypoglycaemia. Next comes hold-out and pre-registration discipline across repeated candidate searches. These, not the scoring rule, are what reviewers will most likely challenge.