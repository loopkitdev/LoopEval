I wrote the report below. Most of the evidence for algorithm features is community material (pull requests, chat, docs, blog posts, one-person screenshots), so I verified those against primary sources (GitHub, the FDA summary, PubMed) wherever I could. The **[UNVERIFIED]** tags mark what I couldn't confirm. I couldn't read Loop Zulip: the Zulip tool has no credentials (no `~/.zuliprc`).

# How the open-source AID community develops, evaluates and tunes Loop and oref

## 1. How the features came in, and what evidence backed them

**General pattern.** Almost no algorithm feature in Loop or oref arrived with a prospective evaluation. The usual path is:
- a developer writes it, often from a control-theory or physiology idea;
- they run it on themselves (n-of-1), sometimes with a few toy simulations;
- a dev-branch or forked build goes to self-selected testers who judge it from Nightscout or Tidepool screenshots and anecdotes;
- it is promoted behind a toggle ("Algorithm Experiments" in Loop, "experimental" in AAPS/Trio).

Peer-reviewed outcome evidence covers whole systems, not individual features.

**Loop: retrospective correction (RC) and Integral RC (IRC).**
- Standard RC compares the past 30 minutes of predicted glucose with actual glucose and projects the gap forward ([LoopDocs: prediction](https://loopkit.github.io/loopdocs/operation/algorithm/prediction/)).
- IRC was proposed by GitHub user **dm61** in March 2018 ([Loop issue #695](https://github.com/LoopKit/Loop/issues/695); [PR #726](https://github.com/LoopKit/Loop/pull/726)). It adds proportional, integral and derivative-like terms, plus integrator resets and limits.
- Its evidence was three simulated scenarios (basal needs +40%, −40%, and an unannounced 25 g meal) and the author's own use. No paper is cited.
- It entered Loop as an Algorithm Experiment in 3.3-dev ([PR #2008](https://github.com/LoopKit/Loop/pull/2008), 2023) and shipped in 3.4. The docs warn of more hypoglycemia and oscillation when ISF is set too low ([LoopDocs settings](https://loopkit.github.io/loopdocs/loop-3/settings/)).
- **[UNVERIFIED]** I found no Diabetes Technology & Therapeutics "Loop IRC" paper and no Kovatchev link. The feature's own docs reference no paper.
- An open PR adds a toggle to turn RC off entirely, because clinicians say RC "masks" poor ISF and carb-ratio settings ([#2310](https://github.com/LoopKit/Loop/pull/2310)).

**Loop: automatic bolus and GBPA.**
- An automatic-bolus dosing strategy was proposed in 2019 ([PR #1219](https://github.com/LoopKit/Loop/pull/1219)). In that thread, users worried that a per-cycle cap does little when the loop runs every 5 minutes.
- Released Loop 3 delivers 40% of the recommendation each cycle.
- Glucose-Based Partial Application (GBPA, Loop 3.4) ramps that fraction from 20% near the correction range to 80% at 200 mg/dL ([Loop PR #1988](https://github.com/LoopKit/Loop/pull/1988) and [LoopKit PR #477](https://github.com/LoopKit/LoopKit/pull/477), opened by Marion Barker in 2023; design discussion is in the Zulip topic "Dosing Strategy Linear Ramp").
- The only evidence statement in the docs is that "many people have tested these and like them." **[UNVERIFIED]** the original designer and any analysis on Zulip.

**Loop and Learn customizations** ([customization repo](https://github.com/loopandlearn/customization); [features in development](https://www.loopandlearn.org/loop-features-in-development/)).
- *Basal Lock* keeps scheduled basal running above a user threshold of 200–300 mg/dL.
- *Negative Insulin Damper* ([issue #2247](https://github.com/LoopKit/Loop/issues/2247), motinis, 2024) scales down the prediction when IOB is negative, to stop "double lows." Its scaling (α = 0.75 at Δ = 50 mg/dL) was hand-calibrated to "about an hour of withdrawn basal." The issue itself says "additional testing is necessary."
- None of these pages cite any testing or evidence.

**oref.**
- oref0 grew out of OpenAPS (Lewis and Leibrand).
- Autosens (2016) and Autotune (Jan 2017) were presented as ADA posters and blog posts, not outcome studies ([openaps.org Outcomes](https://openaps.org/outcomes/); [Autotune ADA 2017 poster](https://openaps.org/2017/06/10/automatic-estimation-of-basals-isf-and-carb-ratio-for-sensor-augmented-pump-and-hybrid-closed-loop-therapy-autotune-poster-presented-at-american-diabetes-association-scientific-sessions/)).
- oref1 (SMB and UAM; oref0 issues #262 and #297) went out with "test at your own risk" guidance ([oref1 docs](https://openaps.readthedocs.io/en/latest/docs/Customize-Iterate/oref1.html)). **[UNVERIFIED]** whether it launched in 2017 or 2018; the sources disagree.
- **Dynamic ISF.** Chris Wilson's TDD-based log model was fitted on "user data gathered by Chris Wilson," with the number of users and the fitting method undisclosed. It was tested by Tim Street and "one other beta tester" with screenshots ([Diabettech 2021](https://www.diabettech.com/automating-isf-in-open-source-aid-systems-experiments-with-androidaps/); [2022 update](https://www.diabettech.com/dynamicisf-an-update/)). It went into AAPS 3.2 as experimental ([AAPS docs](https://androidaps.readthedocs.io/en/3.2/DailyLifeWithAaps/DynamicISF.html)).
- Trio's docs say outright of the sigmoid variant: *"there has been no empirical data analysis to support the use of Sigmoid"* ([trio-docs dynamic-settings.md](https://github.com/nightscout/trio-docs)).
- **AutoISF** ([ga-zelle/autoISF](https://github.com/ga-zelle/autoISF)) is an AAPS add-on that changes ISF in response to acceleration or "stuck high" patterns. It is widely used for fully closed-loop (FCL) setups ([FCL guide](https://github.com/bernie4375/FCL-potential-autoISF)). Its evidence is self-experimentation, explicitly framed as "patient-driven self-responsible research."
- **[UNVERIFIED]** I could not find a primary source for the AAPS "Boost" fork or who wrote it.
- **Trio** is a FreeAPS X → iAPS → Trio fork under the Nightscout Foundation ([Trio](https://github.com/nightscout/Trio)). There are no Trio-specific outcome studies. FINESSE, a Loop vs. iAPS-AutoISF crossover trial without meal announcement in Vancouver, is planned ([protocol PDF](https://www.bcdiabetes.ca/wp-content/uploads/bcdpdfs/-FINESSE-study-T1D-non-declared-meals-.pdf)); I found no results.

**Feature-level evidence that does exist.**
- Staszak et al. (EMBC 2021) linked 13 custom features to self-reported outcomes. SMB, automatic Autotune and Superbolus showed differences, but the study is observational and confounded ([PMID 34891563](https://pubmed.ncbi.nlm.nih.gov/34891563/)).
- Lal et al. (2021) ran Loop and AAPS in diabetic pigs with no meal announcement. Time in range was 58% for AAPS vs. 35% for Loop; Loop had more post-meal lows ([Clin Transl Med, doi 10.1002/ctm2.387](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8087942/)).

## 2. Outcome evidence

**Randomized and prospective trials.**
- **CREATE** (Burnside et al., NEJM 2022;387:869; [doi 10.1056/NEJMoa2203913](https://doi.org/10.1056/NEJMoa2203913)): AAPS with oref (OpenAPS 0.7.0) vs. sensor-augmented pump, n = 97 aged 7–70. Time in range was 71.2% vs. 54.5%, an adjusted difference of 14 points, with no severe hypoglycemia or DKA.
- **CREATE continuation** ([DTT 2023, doi 10.1089/dia.2022.0484](https://doi.org/10.1089/dia.2022.0484)): 24 more weeks, 48 weeks in total.
- **CLOSE IT** (Wilkinson et al., DTT 2026; [record](https://oar.baker.edu.au/103754)): open-source AID without meal announcement vs. hybrid closed loop (HCL), n = 73. Time in range was 66% vs. 69%, adjusted difference −2.2 points (95% CI −6.2 to 1.7).
- **Pancreas4ALL**: AAPS in fully closed loop, adolescents at camp ([DTT 2023](https://doi.org/10.1089/dia.2022.0562)).

**Loop.**
- **Jaeb Loop Observational Study** (Lum et al., DTT 2021;23:367; [PMC8080906](https://pmc.ncbi.nlm.nih.gov/articles/PMC8080906/)): n = 558. Time in range rose from 67% to 73% and HbA1c fell 0.33%.
- Loop in type 2 diabetes: Bauza et al., DTT 2024.

**Tidepool Loop 510(k).** Cleared 23 Jan 2023 (K203689, iAGC product code QJI). The FDA decision summary ([PDF](https://www.accessdata.fda.gov/cdrh_docs/pdf20/K203689.pdf)) shows:
- *Clinical evidence* came from the same Jaeb DIY-Loop observational study (NCT03838900): 872 participants and 483 person-years.
- Effectiveness was re-analysed for an "intended use" subgroup (n = 175): aged ≥6, Humalog/Novolog only, and inside Tidepool guardrails (correction range 87–180, glucose safety limit 67–110) at least 90% of the time. In that subgroup, time in range went from 62% to 70% and HbA1c from 7.1% to 6.7%.
- No new RCT was run. Non-clinical evidence was an ISO 14971 hazard analysis, a 51-person human-factors study, and simulator and emulator verification.
- This is a precedent: guardrailed settings were justified by **retrospectively subsetting real-world data**. Your kind of analysis is directly regulator-relevant.
- Commentary: Braune, Hussain & Lal, JDST 2023 ([PMID 37051947](https://pubmed.ncbi.nlm.nih.gov/37051947/)).

**OpenAPS and AAPS real-world data.**
- Lewis & Leibrand, JDST 2016 ([PMC5094342](https://pmc.ncbi.nlm.nih.gov/articles/PMC5094342)).
- Melmer et al., Diabetes Obes Metab 2019: n = 80, 19,495 CGM days.
- OpenAPS Data Commons analyses: Shahid & Lewis, Nutrients 2022 ([PMC9101219](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9101219/)); Cooper et al., JDST, comparing it with the OPEN dataset of n = 75 and 36,827 days ([PMC12035276](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12035276/)).
- Degen et al., JMIRx Med 2024: unexpected temporal patterns in insulin needs, OpenAPS data, n = 29 ([PMID 39654139](https://pubmed.ncbi.nlm.nih.gov/39654139/)).

**OPEN project and consensus.** Braune, Lal et al., Lancet Diabetes Endocrinol 2022;10:58 ([doi](https://doi.org/10.1016/S2213-8587(21)00267-9)). Review of fully closed loop with open-source systems: Lal, Braune, Lewis et al., Diabetologia 2026 ([doi 10.1007/s00125-025-06644-8](https://doi.org/10.1007/s00125-025-06644-8)). Stanford's OpenAPS + GLP-1 RA report, which found meal announcement unnecessary: Akcan et al., Diabetes Care 2026 ([PMID 41511751](https://pubmed.ncbi.nlm.nih.gov/41511751/)).

**DIY vs. commercial.**
- CODIAC, AAPS → Control-IQ, n = 25: time in range 84.2% vs. 85.7%, not significant ([DOM 2024](https://doi.org/10.1111/dom.15289)). Its extension found more time in tight range on AAPS and less hypoglycemia on commercial systems ([DTT 2025](https://doi.org/10.1177/15209156251376013)).
- Wu et al., DTT 2025, n = 78: open-source AID non-inferior, time in range 78.3% vs. 71.2%, but time below range 3.9% vs. 1.8% ([PMID 40100927](https://pubmed.ncbi.nlm.nih.gov/40100927/)). Wu et al. also compared Loop with Control-IQ in DOM 2026 ([PMID 41873003](https://pubmed.ncbi.nlm.nih.gov/41873003/)).
- Schütz et al., JDST 2025: retrospective, commercial vs. open-source AID.
- The recurring signal: **open-source systems get more time in range but often more time below range.** That trade-off is what feature evaluation should quantify.

**Tidepool Big Data Donation Project.** More than 50,000 donors ([Tidepool](https://www.tidepool.org/category/research)). Its HCL150, PA50 and SAP100 datasets are available under DUA, including through MetaboNet. **[UNVERIFIED]** I found no peer-reviewed analysis of Loop-algorithm behaviour from donated data.

## 3. Tools for analysis and tuning

- **Tidepool `data-science-simulator`** ([repo](https://github.com/tidepool-org/data-science-simulator)): PyLoopKit inside a virtual-patient simulator, built for the **FDA risk analysis**. Its stated longer-term aims are "Loop performance analysis and evaluation of algorithms for settings optimization." Scenario configs are in `loop_risk_v2_0`, and there is a Streamlit wrapper ([loop-risk-simulator-gui](https://github.com/tidepool-org/loop-risk-simulator-gui)). It is scenario-based, not replay of real donor data.
- **LoopAlgorithm** Swift package (LoopKit, since Dec 2023): includes a `LoopAlgorithmRunner` command-line tool that runs a JSON scenario ([repo](https://github.com/LoopKit/LoopAlgorithm)).
- **trio-algorithm-validator** ([repo](https://github.com/nightscout/trio-algorithm-validator)): replays about 239k recorded oref inputs through two Trio branches and diffs the outputs. It is a regression/equivalence check, not an outcome evaluation.
- **APS-what-if** (ga-zelle; [repo](https://github.com/ga-zelle/APS-what-if)): a Python port of `determine-basal` that re-runs AAPS logs with changed settings and reports how dosing would have differed. **It does not simulate glucose**, so it gives counterfactual dosing, not counterfactual outcomes.
- **LoopEval** (loopkitdev): a Swift tool that evaluates forecasts against Nightscout CGM and runs a simulate mode. I found it only on mirror hosts. **[UNVERIFIED]** possibly your own tool.
- **Autotune**: OpenAPS docs. It tunes only the first ISF and carb-ratio entries and is capped by autosens limits.
- **In silico ports.** PyLoopKit in UVA/Padova (Armiger et al., JDST 2021, [PMC8875066](https://pmc.ncbi.nlm.nih.gov/articles/PMC8875066)). AAPS 2.6.4 ported to MATLAB, validated against oref unit tests and run about 1000× real time (Schmitzer et al., JDST 2021, [PMC8721541](https://pmc.ncbi.nlm.nih.gov/articles/PMC8721541/)). AAPS in silico (Toffanin et al., DTT 2020).
- **Forecasting evaluation.**
  - GluPredKit (Wolff et al., [JOSS 2024](https://joss.theoj.org/papers/10.21105/joss.06904); [arXiv 2406.08915](https://arxiv.org/abs/2406.08915)).
  - Wolff et al., IEEE RCAR 2024: real-time metrics disagree with real-world performance ([munin](https://munin.uit.no/handle/10037/36939)).
  - Wolff et al., DTT 2025;27:858: prediction needs clinically relevant criteria beyond accuracy ([PMID 40300777](https://pubmed.ncbi.nlm.nih.gov/40300777/)).
  - MetaboNet: Wolff, Calhoun (Jaeb), Royston et al., 3,135 subjects including the Jaeb Loop Observational Study, OpenAPS Commons and the Tidepool sets ([arXiv 2601.11505](https://arxiv.org/abs/2601.11505); JDST 2026).
  - **Most relevant to you:** Lee, Pop-Busui, Lee, Fleischer & Wiens, IEEE TBME 2024 ([PMC11724010](https://pmc.ncbi.nlm.nih.gov/articles/PMC11724010/)). An LSTM beat Loop's forecaster on held-out RMSE (11.6 vs. 18.5 mg/dL at 30 min) but **lost in closed loop** (time in range 77% vs. 86%). It failed on counterfactual carb–insulin pairs because carbs and boluses are confounded in observational data.
  - Namazi & Shakeri (arXiv 2605.00645, 2026): paired factual/counterfactual forecasting benchmark, but on UVA/Padova, not real data.
- **[UNVERIFIED]** "Loop Insights / LoopInsights": the name appears only as a feature bundled in a personal fork ([Loop-AllFeatures](https://github.com/TaylorJPatterson/Loop-AllFeatures)). I found no documentation or evaluation. I also found nothing published isolating Loop's "momentum" component on real data.

## 4. Settings optimization and user behaviour

- **Settings from data.** Lal et al. (ATTD 2021 abstract; [listing](https://cslide.ctimeetingtech.com/attd2021/attendee/person/334)) fitted basal, carb-ratio and ISF equations on an "aspirational" Loop-observational subgroup (219/743). Total-daily-dose formulas came out more aggressive for basal and carb ratio and less aggressive for ISF. Adding BMI and daily carbs improved the fit. **[UNVERIFIED]** whether a full paper followed.
- Tidepool's guardrails came out of the FDA process (§2).
- Age-dependent carb ratio and ISF: Reinauer et al., DTT 2025. Review: Nimri & Phillip, Horm Res Paediatr 2025.
- **"Settings matter less with AID."** This is widely asserted but not well tested for Loop. Loop's prediction depends directly on ISF and carb ratio. For oref, the docs warn that SMB/UAM "rely on your basals, ratios… being reasonably accurate." The RC-masking complaint in #2310 cuts the other way: adaptation hides wrong settings.
- **Behaviour.** Meal announcement is the best-studied (CLOSE IT, Pancreas4ALL, the pig study, the GLP-1 report; NOMAD is registered as [NCT07758647](https://clinicaltrials.gov/study/NCT07758647)). Qualitative work: Suttiratana et al., DTT 2022; Cleal et al., JMIR 2025. I found **no published quantitative analysis of override use, rescue-carb entry or unlogged treatments in Loop or Nightscout data.**

## 5. Open problems the community names

- "Stuck high" and slow adaptation, which motivated IRC, AutoISF and Basal Lock.
- Lows after accumulated negative IOB ("double lows"), which motivated the Negative Insulin Damper.
- Fast sensitivity changes around exercise, and lows after the system predicts a low (named in the Diabetologia 2026 review).
- RC masking wrong settings (#2310).
- Pathological predictions from carb-absorption bugs ([#2346](https://github.com/LoopKit/Loop/issues/2346): −141 mmol/L predicted).
- Tuning dynamic ISF parameters by Desmos sliders with no data behind them.
- Fully closed loop that needs expert configuration.
- Higher time below range than commercial systems.
- No feature-level evidence at all.

## 6. Missing evaluation infrastructure, and where your group fits

**What's missing:**
1. **Replay that predicts outcomes, not just doses.** APS-what-if, LoopEval's dosing mode and trio-algorithm-validator all answer "what would the algorithm have dosed." None estimates what *glucose* would have done. Tidepool's simulator is scenario-based, built for risk analysis, and not grounded in individual donor data.
2. **Feature-level comparison of IRC, GBPA, the damper, dynamic ISF, AutoISF and SMB settings** on a shared real-world corpus. Today each is backed by n-of-1 data, screenshots and "people like it."
3. **Cross-algorithm comparison (Loop vs. oref) on the same patients.** Only the pig study and the planned FINESSE trial do this.
4. **Validated counterfactual glucose models.** Lee et al. show observational forecast accuracy doesn't predict closed-loop performance, so you need to validate against natural experiments: setting changes, algorithm switches, version upgrades, missed announcements.
5. **Standard safety metrics and stratification.** Time below range, tight range and post-hypo rebound, broken down by settings quality, age, insulin type and meal announcement.
6. **Behaviour models** for overrides, rescue carbs and unlogged treatments, which confound every replay.

**Where you could contribute most:**
- **(a)** A public, versioned benchmark on MetaboNet, the Jaeb Loop Observational Study and the OpenAPS Commons that runs both LoopAlgorithm and oref through the same counterfactual engine.
- **(b)** Retrospective evaluations of the shipped Loop Algorithm Experiments and of oref dynamic ISF variants. These are the features with the most users and the least evidence.
- **(c)** Validating the counterfactual model itself, using within-user switches (e.g., automatic bolus on/off, GBPA toggles, Trio vs. Loop migrations) as quasi-experiments.
- **(d)** Settings robustness: how outcomes degrade under ±X% errors in ISF, carb ratio and basal for each algorithm. This would test "settings matter less" directly.
- **(e)** Hypoglycemia-focused analyses of the time-in-range vs. time-below-range trade-off.

The Tidepool 510(k) shows regulators will accept retrospective analysis of real-world subsets. A rigorous counterfactual pipeline could become the community's missing step between "it works for me" and an RCT.