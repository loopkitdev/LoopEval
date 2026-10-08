I wrote this from my own knowledge and checked the key citations with web searches. Citations I could not confirm are marked **[unverified]**. Throughout, "clinical" means human outpatient or inpatient data, and "in-silico" mostly means the UVA/Padova simulator.

# How glucose-control algorithms are developed and tuned: a survey for our candidate mechanisms

## 1. Algorithm families and their key design ideas

**MPC family**
- **Cambridge (CamAPS FX)**
  - Nonlinear MPC built on a compartment model (Hovorka et al., 2004).
  - Model parameters are re-estimated in real time by Bayesian/Kalman-style adaptation, using several candidate models.
  - It learns total daily dose (TDD), a diurnal basal pattern and meal-related parameters over days.
  - The user sets only a target and weight/TDD at the start; there is no editable ISF or correction factor.
  - Clinical evidence comes from several RCTs: Tauschmann et al., 2018, Lancet; Ware et al., 2022, NEJM (very young children); Lee et al., 2023, NEJM (pregnancy).
- **UVA / Tandem Control-IQ**
  - Grew out of the UVA "DiAs"/inControl platform.
  - Predicts glucose about 30 minutes ahead and modulates basal against a target band (112.5–160 mg/dL).
  - Gives automatic correction boluses: 60% of the computed correction, at most once per hour.
  - A separate "safety supervisor" layer limits insulin when hypoglycemia risk is high.
  - The model is personalized from the user's own pump settings (basal, ISF, CR, weight, TDD).
  - Pivotal RCT: Brown et al., 2019, NEJM.
- **Harvard/UCSB zone-MPC (Doyle/Dassau)**
  - Penalizes deviation from a glucose *zone* rather than a setpoint (Grosman et al., 2010, JDST).
  - Later versions use periodic, time-of-day zones and asymmetric costs: insulin delivery above basal is penalized differently from suspension (Gondhalekar, Dassau & Doyle, 2016, Automatica).
  - Paired with a "Health Monitoring System" hypo-alarm layer.
- **Omnipod 5**
  - Personalized adaptive MPC. Each new pod re-estimates the adaptive basal from recent TDD, and the user can choose among targets (110–150 mg/dL).
  - The algorithm reportedly descends from the Insulet/Harvard–UCSB collaboration **[lineage partly unverified]**.
  - Pivotal trial: Brown et al., 2021, Diabetes Care (single-arm).
- **Diabeloop DBLG1**
  - MPC with expert-rule and learning layers. RCT: Benhamou et al., 2019, Lancet Digital Health.

**PID with insulin feedback (Medtronic 670G/780G SmartGuard)**
- PID control, plus subtracting a model-estimated plasma insulin term ("insulin feedback"). The feedback counters PID's tendency to stack insulin after meals (Steil et al., 2006, Diabetes; Steil, 2013, JDST).
- 780G adds automatic correction boluses, selectable targets of 100/110/120 mg/dL, and an adaptive gain tied to recent TDD.
- Evidence: Bergenstal et al., 2016, JAMA (670G, single-arm); FLAIR trial (Bergenstal et al., 2021, Lancet) and Collyns et al., 2021, Diabetes Care (780G).
- Key idea: the TDD-based gains are adaptive with no explicit model, and safety comes from insulin limits plus an "auto-mode exit."

**Fuzzy logic (DreaMed MD-Logic)**
- Rules that encode clinicians' reasoning, using glucose level and trend, plus learning of each patient's insulin parameters (Atlas et al., 2010, Diabetes Care; Phillip et al., 2013, NEJM, diabetes camp).
- Its commercial descendant is a settings *advisor* (Advisor Pro), not a controller.

**iLet bionic pancreas (Beta Bionics)**
- Initialized from body weight only; meals are announced only qualitatively ("usual/more/less").
- Internally it combines an MPC-like correction controller, an adaptive basal that learns from delivered insulin, and adaptive meal doses. There is no user-tunable ISF/CR, only a target setting.
- Evidence: El-Khatib et al., 2010, Science Translational Medicine; Russell et al., 2014, NEJM; Bionic Pancreas Research Group (Russell, Beck et al.), 2022, NEJM 387:1161. In that RCT, HbA1c fell from 7.9% to 7.3% versus no change on standard care.
- Severe hypoglycemia did not differ significantly between arms.

**Loop (LoopKit / Tidepool Loop)**
- Builds an explicit glucose prediction (about 6 hours) by summing effects:
  - insulin (exponential activity curves);
  - carbs, with dynamic absorption inferred from the gap between observed and predicted glucose;
  - momentum (short-term trend);
  - retrospective correction (RC), including an optional integral RC.
- It doses so the prediction's *minimum* stays above a suspend threshold and the eventual glucose reaches a correction range.
- Dosing is temp basal or automatic boluses (a "partial application" fraction).
- Evidence is observational: Lum et al., 2021, DTT (n=558) found TIR rising from 67% to 73% and a large drop in reported severe hypoglycemia (pre/post comparison, no control group).
- Tidepool Loop received FDA 510(k) clearance in 2023. I found no peer-reviewed RCT of Loop itself.
- Integral RC has, to my knowledge, no peer-reviewed evaluation. It is documented in LoopKit docs and forums **[unverified]**.

**oref0/oref1 (OpenAPS, AndroidAPS, Trio)**
- Computes several prediction curves: IOB-only, COB, UAM (unannounced meal, which extrapolates the deviation slope) and ZT (zero-temp).
- Doses on a blend of the minimum and eventual glucose.
- oref1 adds SMBs (super-micro-boluses, sized as a fraction of insulin required and capped by maxSMB/maxIOB).
- **Autosens** computes a ratio over about 8–24 hours of deviations and scales ISF and basal, bounded by 0.7–1.2.
- **Autotune** is an offline, nightly categorization of deviations into basal/ISF/CR, applied as bounded (about 20%) daily nudges.
- **Dynamic ISF** (AAPS 3.2+; Trio/iAPS) sets ISF from TDD and current glucose with a logarithmic formula (Trio also offers a sigmoid). Its TDD is a weighted mix of the 7-day average, yesterday and the last 8 hours.
- Clinical evidence: the CREATE RCT (Burnside et al., 2022, NEJM 387:869) used AndroidAPS with OpenAPS 0.7.0 (oref1/SMB). TIR difference versus sensor-augmented pump was +14 points, with no severe hypoglycemia or DKA.
- **Autotune, autosens and Dynamic ISF have no controlled trials.** Dynamic ISF is documented as "advanced users only / experimental."

## 2. How these systems were tuned and personalized

- **Population-first, then a few individual anchors.** All commercial systems set gains from population simulation plus one to three personal anchors (weight, TDD, or the user's existing settings). They then adapt slowly from TDD or delivered insulin. The user-facing "dials" are almost always just target or aggressiveness: Control-IQ's sleep/exercise modes, Omnipod targets, 780G targets, iLet targets.
  - **This matches our framing.** The commercial answer to personalization is essentially "one aggressiveness dial plus slow TDD adaptation." Any candidate mechanism has to beat that.
- **Run-to-run (R2R) control.** Day-to-day updates of basal and CR from glucose metrics of the previous run.
  - Palerm et al., 2008, J Process Control; Toffanin et al., 2017/2018, IEEE TBME (in-silico R2R-MPC).
  - The main clinical evidence is Dassau et al., 2017, Diabetes Care: a 12-week, 24/7 single-arm trial in 30 adults with weekly basal and four-weekly CR adaptation. HbA1c went from 7.0% to 6.7%, and daytime time-below-range from 5.0% to 1.9%. A Padova one-month R2R extension in 18 adults also exists **[final outcomes unverified]**.
- **Iterative learning control.** Wang, Dassau & Doyle, 2010, IEEE TBME (MPC + ILC). In-silico only.
- **Bayesian optimization (BO).** Shi, Dassau & Doyle, CDC 2018 and a later paper (PMC6336673) on multivariate BO for long-term adaptation of CR and controller parameters, tested on the 111-adult UVA/Padova cohort. In-silico only. I found no clinical trial of BO-tuned controllers.
- **Case-based reasoning.** The ABC4D bolus advisor (Herrero et al., Imperial) adapts bolus parameters from similar past cases. It has had small clinical feasibility studies **[details unverified]**.
- **Automated settings advisors.** The strongest clinical evidence for "automatic settings optimization":
  - DreaMed Advisor Pro: Nimri et al., 2020, Nature Medicine 26:1380. A 6-month multinational non-inferiority RCT in youths found AI-generated pump-setting changes every 3 weeks non-inferior to physician titration.
  - In a 2020 JDST study, 17 physicians reviewing 15 datasets did not differ significantly from the AI in the direction or size of their dose changes.
  - Tidepool/Loop does not ship an automated settings recommender that I can confirm **[unverified]**. Autotune is the community equivalent, with no trials.
- **Safety layers.** These dominate in practice:
  - IOB constraints (Ellingsen et al., 2009, JDST "IOB constraints" for MPC; oref maxIOB; Loop max basal/bolus);
  - insulin feedback (Medtronic);
  - hypo-safety supervisors (UVA's Safety Supervision Module; Harvard's Health Monitoring System);
  - predictive low-glucose suspend.
  - Asymmetric costs that make insulin *removal* cheap and *addition* expensive are a deliberate, widespread design pattern (zone-MPC; Control-IQ's 60% corrections). This bears directly on our asymmetric-IRC and post-low-protection candidates: they rediscover a known principle. The open question is whether they add anything beyond the aggressiveness dial.

## 3. Reinforcement learning and ML for insulin dosing

**In-silico RL (large literature, essentially all UVA/Padova or its open-source clone simglucose):**
- Daskalaki, Diem & Mougiakakou, 2016, PLoS ONE: actor-critic that updates basal/CR daily, i.e. RL as run-to-run.
- Fox, Lee, Pop-Busui & Wiens, 2020, MLHC (PMLR 126:508). Deep RL beat baseline controllers on simulated risk and adapted to new patients with little data.
- Zhu, Li, Herrero & Georgiou, 2021, IEEE JBHI 25(4):1223. Double-Q plus dilated RNN, trained on the population then personalized. Adolescent TIR rose from 55.5% to 65.9% (insulin only).
- Zhu et al., 2023, IEEE JBHI: offline deep RL with off-policy evaluation.
- Lim, Lee, Jeon & Kim, 2021, IEEE Access 9:105756. Soft actor-critic initialized from PID, with an "adaptive safe actor" that can suspend or add insulin. Performance was *comparable* to PID, not better.
- Emerson, Guy & McConville, 2023, J Biomed Inform 142:104376. Offline RL (BCQ/CQL/TD3+BC) trained from logged data on 30 virtual patients beat a standard basal-bolus/PID-style baseline. It was most useful for children, and robust to bolus errors, irregular meals and sensor compression artifacts.
- Hettiarachchi et al., 2024, Biomed Signal Process Control (doi:10.1016/j.bspc.2023.105839), **G2P2C**. PPO augmented with a learned glucose model and short-horizon planning, with no meal announcement. TIR was 73% in adults and 64% in adolescents in silico.
- Later work includes offline RL from human feedback (arXiv 2501.15972) and "ABBA," an adaptive basal-bolus advisor (arXiv 2505.14477) that the authors say is ready for a first human trial.

**What transferred to humans (all small and uncontrolled):**
- Jafar, Kobayati, Tsoukas & Haidar (McGill), 2024, Nature Communications. RL *decision support* for high-fat meals and post-meal exercise in 15 adults on multiple daily injections, single-arm over 16 weeks. Post-meal time below 3.9 mmol/L fell from about 5.3% to about 1.4–1.8%. **Note:** the RL personalizes a few dose multipliers, and the authors call for RCTs. (Author list from memory; the search confirmed the paper but not the authors **[partly unverified]**.)
- Wang G et al., 2023, Nature Medicine 29:2633. **RL-DITR**, model-based RL for inpatient insulin titration in *type 2* diabetes. In a single-arm trial of 16 patients, mean glucose fell from 11.1 to 8.6 mmol/L with no severe hypoglycemia.
- **No deep-RL closed-loop controller for T1D has, to my knowledge, completed a published outpatient trial.**

The pattern that *does* transfer is RL or learning used as a slow, low-dimensional parameter adapter (dose multipliers, basal/CR, weekly R2R), wrapped in conventional safety constraints. Learning a direct state-to-insulin policy has not transferred.

**Learned forecasters:**
- GluNet (Li, Liu, Zhu, Herrero & Georgiou, 2020, IEEE JBHI).
- Gluformer (Sergazinov, Armandpour & Gaynanova; arXiv 2209.04526, probably ICASSP 2023 **[venue unverified]**). A transformer that outputs a mixture distribution.
- GlucoBench (Sergazinov et al., ICLR 2024). Benchmarks across public CGM datasets found deep models are not uniformly better than simple and physiological models, and that gains shrink out of distribution.
- Data-driven predictors inside MPC have been studied in silico, e.g. Sonzogni et al., CDC 2023 (CHoKI learned model with chance-constrained MPC). I am not aware of a commercial AID that uses a black-box neural forecaster as its dosing model. Diabeloop's ML components are proprietary **[unverified]**.

## 4. Handling uncertainty

- **Chance-constrained / stochastic MPC:**
  - Lackinger et al., CDC 2017: the controller keeps the *probability* of leaving euglycemia below a threshold rather than tracking a setpoint, and spends the freed margin to minimize insulin.
  - Sonzogni et al., CDC 2023: chance-constrained MPC with a learned CHoKI model.
  - Nandi & Singh, 2019, IEEE JBHI: sampling-based chance constraints, open loop.
  - All in-silico.
- **Robust/min-max MPC and zone-MPC** handle uncertainty implicitly, through zones and asymmetric penalties.
- **CamAPS** is the clinically deployed system closest to "probabilistic." Its Bayesian parameter estimation and model averaging propagate uncertainty, and dosing is reportedly more conservative when model confidence is low **[mechanism detail partly unverified]**.
- **Conformal prediction for CGM** is very recent and limited to forecasting and alerting, not dosing:
  - Lops et al., CoDIT 2026: split-conformal, horizon-specific intervals feeding a hypo/hyper alert layer.
  - Maqsood et al., IEEE Access 2026: conformal risk control with a deferral policy **[venue/details from abstract only]**.
  - Caveat: CGM series are autocorrelated and drift, so exchangeability fails. Adaptive conformal methods (ACI, EnbPI) would be needed. I found **no published work** using conformal bands to cap insulin doses.
  - So our "uncertainty-band dose cap" candidate is novel in AID specifically. Its nearest analogues are chance-constrained MPC and Loop/oref's "dose to the minimum predicted glucose."
- **Risk-aware cost functions.** Symmetrized risk indices (Kovatchev's LBGI/HBGI) are used as MPC costs and RL rewards (e.g. Fox et al.). This is standard practice, not new.

## 5. Adaptive and time-varying sensitivity

- **Circadian ISF.** Hinshaw et al., 2013, Diabetes 62:2223 (n=19, triple-tracer, identical meals) found **no population-level difference in insulin sensitivity between meals in T1D**. The diurnal pattern was individual-specific and differed from that of healthy people. Visentin et al. (JDST 2015/2016) built individual circadian insulin-sensitivity variability into the UVA/Padova simulator.
  - **Implication for us:** a population-level circadian schedule is not supported. Only individually learned schedules make sense, and they need enough data to beat noise.
  - Clinical systems handle this mostly through user-set time-of-day profiles (Loop, oref, Control-IQ), learned diurnal basal (CamAPS), or periodic zones (Harvard).
- **Adaptive basal / TDD-based gains.** These are deployed in CamAPS, Omnipod 5, 780G and iLet, so the evidence is the pivotal trials. But adaptation is never isolated as a randomized factor, so its *marginal* benefit is unproven. Dassau et al., 2017 is the closest isolated test (single-arm).
- **Autosens / Dynamic ISF.** No controlled outcome data; community anecdote and documentation only.
- **Exercise:**
  - Castle et al., 2018, Diabetes Care: randomized outpatient trial with exercise detection from heart rate and accelerometer. Dual-hormone reduced hypoglycemia, and single-hormone TIR was similar.
  - Jacobs et al., 2023, Lancet Digital Health: crossover trial of exercise-aware MPC (continuous METs input) versus exercise-aware APD (suspend). TIR and time-below-range were similar between algorithms, and both beat no exercise algorithm on time-below-range **[headline numbers from a secondary summary]**.
  - Commercial systems rely on manual exercise modes and temporary targets.
  - Evidence that *automatic* exercise adaptation beats manual announcement is weak.
- **Menstrual cycle.** A secondary analysis of 16 women in the iDCL Control-IQ trial (DTT, 2022) found insulin delivery and CGM metrics stable across cycle phases. A Spanish observational study (NCT06338072) is ongoing. There is no evidence for cycle-specific algorithm adaptation.
- **Illness.** Essentially no algorithmic literature. Handled by users (temporary targets, profile percentages) and by slow adaptation such as autosens and TDD tracking. **[No trials found]**

## 6. Clinical versus in-silico evidence

| Idea | Evidence level |
|---|---|
| Hybrid closed loop overall (MPC, PID-IFB, iLet, oref1/AndroidAPS) | **Strong clinical: multiple RCTs** |
| Loop specifically | Clinical **observational only** (Lum et al., 2021); FDA cleared |
| TDD- or weight-based slow adaptation (CamAPS, Omnipod 5, 780G, iLet) | Clinical as part of whole systems; **marginal effect not isolated** |
| Automated pump-settings optimization | **RCT** (Nimri et al., 2020, non-inferiority vs physicians) |
| Weekly run-to-run basal/CR | **Single-arm clinical** (Dassau et al., 2017); otherwise in-silico |
| IOB constraints, insulin feedback, hypo supervisors, asymmetric zone costs | Deployed in every cleared system (strong engineering evidence), but rarely isolated |
| Autosens, autotune, Dynamic ISF, Loop integral RC | **Community use only; no controlled data** |
| Bayesian optimization / ILC of controller parameters | **In-silico only** |
| Deep RL closed-loop controllers (online or offline) | **In-silico only** for T1D |
| RL as a slow dose-parameter personalizer | **Small single-arm human trials** (Jafar et al., 2024 in T1D, multiple daily injections; Wang et al., 2023 in T2D) |
| Learned / transformer forecasters inside dosing | **In-silico or retrospective only**; benchmarks show modest out-of-distribution gains |
| Chance-constrained / stochastic MPC | **In-silico only** (CamAPS Bayesian adaptation is the partial clinical exception) |
| Conformal prediction | Forecast intervals and alerts only; **no dosing use found** |
| Circadian sensitivity | Physiology says individual-specific (Hinshaw et al., 2013); **no evidence for population schedules** |
| Exercise detection | Randomized feasibility trials; gains mainly in hypo reduction; automatic not clearly better than manual |
| Menstrual or illness adaptation | **No evidence**; one small analysis shows AID already copes |

### What this means for our evaluation
1. The commercial field has converged on a few knobs: target/aggressiveness, slow TDD adaptation, IOB caps, and asymmetric hypo protection. Our "beat the aggressiveness-dial Pareto frontier" test is the right bar.
2. Almost no published work isolates a single mechanism against a re-tuned baseline. Most in-silico RL and MPC papers compare against a fixed, often weak baseline (basal-bolus or PID), which inflates gains. Our frontier-based comparison is stricter than the literature norm.
3. Watch for simulator overfitting. UVA/Padova results on circadian, exercise and illness handling depend heavily on how variability is injected. Replay on real donor data has a different weakness: counterfactual validity of the physiological model. Neither substitutes for prospective data.

## References
- Atlas E et al. 2010. MD-Logic artificial pancreas system. *Diabetes Care* 33:1072.
- Benhamou PY et al. 2019. Closed-loop insulin delivery in adults with T1D in real-life conditions (Diabeloop). *Lancet Digital Health* 1:e17.
- Bergenstal RM et al. 2016. Safety of a hybrid closed-loop insulin delivery system (670G). *JAMA* 316:1407.
- Bergenstal RM et al. 2021. FLAIR trial. *Lancet* 397:208.
- Bionic Pancreas Research Group; Russell SJ, Beck RW et al. 2022. *NEJM* 387:1161. doi:10.1056/NEJMoa2205225.
- Brown SA et al. 2019. Six-month RCT of closed-loop control (Control-IQ). *NEJM* 381:1707.
- Brown SA et al. 2021. Omnipod 5 pivotal. *Diabetes Care* 44:1630.
- Burnside MJ et al. 2022. Open-source AID in T1D (CREATE). *NEJM* 387:869. doi:10.1056/NEJMoa2203913.
- Castle JR et al. 2018. Randomized outpatient trial of single- and dual-hormone closed-loop systems that adapt to exercise using wearable sensors. *Diabetes Care* 41:1471.
- Collyns OJ et al. 2021. 780G advanced hybrid closed loop. *Diabetes Care* 44:969.
- Daskalaki E, Diem P, Mougiakakou S. 2016. Model-free machine learning in biomedicine. *PLoS ONE*. https://pmc.ncbi.nlm.nih.gov/articles/PMC4956312
- Dassau E et al. 2017. 12-week 24/7 ambulatory AP with weekly adaptation of insulin delivery settings. *Diabetes Care* 40:1719.
- El-Khatib FH et al. 2010. Bihormonal closed-loop. *Sci Transl Med* 2:27ra27.
- Ellingsen C et al. 2009. Safety constraints in an AP system: IOB. *J Diabetes Sci Technol* 3:536.
- Emerson H, Guy M, McConville R. 2023. Offline RL for safer blood glucose control. *J Biomed Inform* 142:104376. arXiv:2204.03376.
- Fox I, Lee J, Pop-Busui R, Wiens J. 2020. Deep RL for closed-loop blood glucose control. *MLHC*, PMLR 126:508. https://proceedings.mlr.press/v126/fox20a.html
- Gondhalekar R, Dassau E, Doyle FJ. 2016. Periodic zone-MPC with asymmetric costs. *Automatica* 71:237.
- Grosman B et al. 2010. Zone MPC. *J Diabetes Sci Technol* 4:961.
- Hettiarachchi C et al. 2024. G2P2C. *Biomed Signal Process Control*. doi:10.1016/j.bspc.2023.105839.
- Hinshaw L et al. 2013. Diurnal pattern of insulin action in T1D. *Diabetes* 62:2223. doi:10.2337/db12-1759.
- Hovorka R et al. 2004. Nonlinear MPC to regulate glucose in T1D. *Physiol Meas* 25:905.
- Jacobs PG et al. 2023. Exercise-aware MPC vs APD (iPancreas). *Lancet Digital Health*. [details partly unverified]
- Jafar A, Kobayati A, Tsoukas MA, Haidar A. 2024. Personalized insulin dosing using RL for high-fat meals and aerobic exercise: proof-of-concept trial. *Nat Commun* 15. NCT05041621. [author list from memory]
- Lackinger et al. 2017. Chance-constrained MPC for blood glucose management. *IEEE CDC*. doi:10.1109/CDC.2017.8264354.
- Lee TTM et al. 2023. Automated insulin delivery in pregnancy (AiDAPT). *NEJM* 388:2217.
- Li K et al. 2020. GluNet. *IEEE JBHI* 24:414.
- Lim MH, Lee WH, Jeon B, Kim S. 2021. RL blood-glucose control with safety and interpretability. *IEEE Access* 9:105756. doi:10.1109/ACCESS.2021.3100007.
- Lum JW et al. 2021. Real-world prospective study of Loop. *Diabetes Technol Ther* 23:367. https://pmc.ncbi.nlm.nih.gov/articles/PMC8080906
- Nandi S, Singh T. 2019. Probabilistic constraints for insulin infusion. *IEEE JBHI*.
- Nimri R et al. 2020. Insulin dose optimization using an automated AI-based decision support system in youths with T1D. *Nat Med* 26:1380. doi:10.1038/s41591-020-1045-7.
- Palerm CC et al. 2008. Run-to-run basal adjustment. *J Process Control* 18:258.
- Phillip M et al. 2013. Nocturnal glucose control with an AP at a diabetes camp. *NEJM* 368:824.
- Russell SJ et al. 2014. Outpatient glycemic control with a bionic pancreas. *NEJM* 371:313.
- Sergazinov R et al. 2024. GlucoBench. *ICLR*. arXiv:2410.05780.
- Sergazinov R, Armandpour M, Gaynanova I. Gluformer. arXiv:2209.04526 (ICASSP 2023 [unverified]).
- Shi D, Dassau E, Doyle FJ. 2018. Multivariate Bayesian optimization for long-term AP adaptation. *IEEE CDC*; extended version https://pmc.ncbi.nlm.nih.gov/articles/PMC6336673
- Sonzogni et al. 2023. CHoKI-based MPC with probabilistic constraints. *IEEE CDC*.
- Steil GM et al. 2006. Feasibility of automating insulin delivery. *Diabetes* 55:3344. Steil GM 2013, *J Diabetes Sci Technol* 7:1621.
- Tauschmann M et al. 2018. Closed-loop insulin delivery in suboptimally controlled T1D. *Lancet* 392:1321.
- Toffanin C et al. 2018. Toward a run-to-run adaptive AP: in silico results. *IEEE TBME* 65:479.
- Wang G et al. 2023. Optimized glycemic control of T2D with RL (RL-DITR). *Nat Med* 29:2633. doi:10.1038/s41591-023-02552-9.
- Wang Y, Dassau E, Doyle FJ. 2010. MPC + iterative learning control for AP. *IEEE TBME* 57:211.
- Ware J et al. 2022. Cambridge hybrid closed loop in very young children. *NEJM* 386:209.
- Zhu T, Li K, Herrero P, Georgiou P. 2021. Basal glucose control in T1D using deep RL. *IEEE JBHI* 25:1223. doi:10.1109/JBHI.2020.3014556.
- iDCL menstrual-cycle secondary analysis. 2022. *Diabetes Technol Ther* (n=16) [authors unverified]; NCT06338072 (ongoing).
- Community documentation: AndroidAPS DynamicISF (https://androidapsdocs.readthedocs.io/en/latest/Usage/DynamicISF.html); Trio autosens/dynamic docs (https://iaps.readthedocs.io/en/dev/settings/configuration/concepts/autosens-dynamic.html).

Page numbers for the classic citations (Hovorka 2004, Steil 2006, Palerm 2008, Ellingsen 2009, etc.) are from memory. Check them before reusing in a formal document.