# LoopEval in the literature: how AID algorithms are built, evaluated and optimized, and where we go next

*2026-10-08. A synthesis of five literature sweeps (simulators, algorithm design and tuning, unannounced meals, evaluation metrics and counterfactual methods, DIY-AID practice) and a read of the LoopEval repos as they stand today (`loopeval-algo` ledger through C39/E54/M10). Citations marked † come from abstracts only or were not fully verified, so check them before citing externally.*

---

## 0. TL;DR

1. **Our simulator is a known method with known limits.** Holding ICE fixed is, in substance, the UVA **"net effect" replay** (Patek, Kovatchev, Breton). Its domain of validity has been measured directly:
   - Vettoretti et al. 2016 found it reliable for **small (~±10%) basal changes**, biased for large ones, and biased in characteristic ways around **hypotreatments and correction boluses**.
   - The best clinical validation of a mature replay method (Villa-Tamayo et al. 2024, which re-ran a randomized crossover trial) found **TIR, TAR, LBGI and HBGI equivalent to observed, but time-below-range not equivalent.**
   - Our second scoring axis is exactly the one the literature says replay gets wrong. This is the most important finding of the review.
2. **Our evaluation method is stricter than the field's, and probably novel.** Most in-silico and many clinical comparisons test a candidate against one fixed, often weak, baseline. Sweeping both arms on a matched aggressiveness dial and requiring frontier dominance is rare. The closest standard tools (CVGA, the GRI grid) do not do this. It is worth publishing as a methods contribution.
3. **Our negative results match the literature, which strengthens them.**
   - "Dosing logic is exhausted": commercial systems converged on one aggressiveness dial, slow TDD adaptation and asymmetric hypo protection.
   - C12 circadian failure: Hinshaw 2013 found no population diurnal pattern; individual patterns are noisy.
   - C19 learned forecaster fails in closed loop: Lee et al. 2024, an LSTM that beat Loop on RMSE but lost 9 pp TIR in closed loop.
   - UAM is mixed: detect-and-dose add-ons reach about +5 pp post-meal and are not significant over 24 h in trials.
   - The 60-min oracle bounds headroom at about +10 TIR, and clinical gaps between announced and unannounced meals are 2–10 pp.
4. **The biggest clinically demonstrated levers are not new dosing logic.** They are **settings and operating point**:
   - Medtronic real-world data: about +7 pp TIR for non-bolusers from target and active-insulin-time choices alone (industry data†).
   - DreaMed Advisor Pro: RCT non-inferior to physician titration.
   - UVA digital-twin co-adaptation RCT: +5 pp TIR.

   Adjuncts (GLP-1, pramlintide) and **behavior** (meal announcement) are the other large levers. Our headline mechanism lift (≈ +0.5 TIR / −0.1 t<54) is real but small next to these. LoopEval already *is* a digital twin; we use it to grade mechanisms, not to recommend operating points.
5. **Recommended next paths, in priority order** (§5):
   - (A) validate the counterfactual on natural experiments already sitting in BDDP: insulin-needs overrides, settings eras, autobolus↔temp-basal switches;
   - (B) quantify and cap counterfactual distance, Vettoretti-style, with a "sim-of-the-sim" test on a parametric plant;
   - (C) replace the counter-reg floor with a hypotreatment behavior model;
   - (D) a locked hold-out donor set plus a multiplicity budget;
   - (E) make the operating-point recommender a first-class deliverable;
   - (F) a Loop-vs-oref frontier, which nobody has published on the same patients;
   - (G) a short list of literature-informed mechanisms that haven't been tried: probability-scaled capped meal priming plus habit prior, late-announcement handling, calibrated (conformal) lower bands, and pooled rather than per-patient learned forecasters.

---

## 1. Where LoopEval sits: the simulator

### 1.1 Families of simulator

| Approach | Counterfactual assumption | Validation | Relationship to LoopEval |
|---|---|---|---|
| UVA/Padova S2008 → S2013 → S2017 (Kovatchev 2009; Dalla Man 2014; Visentin 2018) | Full mechanistic re-simulation of a virtual population | FDA preclinical acceptance (2008); trace matching; S2008 under-predicted hypo, which led to S2013's low-BG nonlinearity and glucagon | Population model, not individual. simglucose is open-source S2008 only. TidepoolSim is the same kind of thing for Loop's FDA risk analysis |
| **Net effect replay** (Patek; Kovatchev 2015 DT&T) | Individual residual held fixed while insulin changes | **Vettoretti 2016**: valid for ±10% basal; ±50% basal over-estimates time hypo and hyper; under-estimates the bolus cut needed to prevent hypo; under-estimates time hyper when corrections are added; over-estimates time hypo when hypotreatments are added | **This is LoopEval's ICE method** |
| Personalized replay (Hughes 2021 JDST; Diaz 2023) | Personalize ISF and meal parameters first, *then* replay the residual | In-silico MARD improves by 6–9 units across broad changes | Our `m(t)` fidelity model and `--patient-isf` are partial versions |
| **UVA replay, clinical validation** (Villa-Tamayo, Colmegna, Breton, DT&T 2024) | Same as above | Replayed each subject of an HCL-vs-FCL crossover RCT into the arm *not* observed (64 pairs). TIR, TAR, LBGI, HBGI equivalent; **TBR not equivalent** | The validation design we should copy (§5A) |
| UVA digital twin RCT (Kovatchev, npj Digit Med 2025) | Daily-identified minimal model + inferred unannounced meals, used to re-tune settings every 2 weeks | 72 adults, 6 months: TIR 72 → 77%, A1c 6.8 → 6.6 | Proof that "replay-optimized operating point" moves real outcomes. Authors note it is Control-IQ-specific and needs bit-exact controller replication, which we have for Loop |
| ReplayBG (Cappon et al., IEEE TBME 2023; open source) | MCMC-identified individual model, **no residual**; posterior gives a credible interval on the counterfactual | 100 virtual subjects × 5 scenarios; beat net-effect replay | Natural independent second engine for cross-checking rankings (§5B) |
| oref0-simulator, APS-what-if, trio-algorithm-validator | Toy forward model, or dose-only replay with no glucose | None / equivalence only | Community state of the art: none of these give *outcome* counterfactuals |

### 1.2 What LoopEval already does better than the published replay work

- **Controller fidelity.** Published replay papers assume the controller is implemented correctly. We have a two-step validation bar: decision-time-replay (DTR) forecasts match the field's recorded forecast in the worst case, then doses match to ≤0.05 U. That is backed by an instrumented-Loop rig showing bit-exact forecast components, and a mandatory identity check. The 2025 digital-twin paper names exact controller replication as the main barrier to porting; we have cleared it for Loop. DEKA's 510(k) equivalence testing (~10⁶ random 24-h simulations) is the closest regulatory analogue.
- **Data-pipeline forensics.** The ledger and memory record dozens of ETL defects, each of which moved results:
  - HealthKit duplicates
  - phantom basal
  - override over-extension
  - future-override leaks
  - stale exports
  - 1-min CGM σ grids

  None of the replay papers report this kind of auditing. Real-world data (RWD) replay is only as good as this layer, and it is our quiet comparative advantage.
- **Patient-vs-controller sensitivity decoupling.** Showing that patient ISF is a nuisance parameter for *verdicts* (M8: lift moves less than 1% across ±10%) is exactly the kind of robustness analysis the net-effect literature lacks.

### 1.3 Where the literature says we are exposed

1. **The t<54 axis.** Villa-Tamayo found TBR not equivalent even with a personalized replay. Our own data agree: announcer beds reproduce field TIR but **over-produce lows**:

   | Bed | Field t<54 (%) | Sim t<54 at op (%) |
   |---|---|---|
   | bddp05 | 0.32 | 1.93 |
   | bddp08 | 0.13 | 1.49 |
   | bddp06 | 0.10 | 0.84 |

   bddp04 is unscoreable. These are the beds where adaptive mechanisms win, so the bias and the wins overlap.
2. **Hypotreatment / rescue carbs.** Vettoretti's two hypotreatment findings map directly onto our documented rescue-carb confound: rescues baked into ICE, and no extra rescues for candidate-created lows. Our counter-regulation floor (onset 54, gain 0.4, max 8) is a proxy. The simulator guide already says its shape is unphysical (≈5.6 mg/dL/min at 40 vs an observed maximum of 2.6–3.3). The literature's answer is an explicit behavior model: ReplayBG hypotreatment handlers, and the Vettoretti 2018 "patient decision simulator."
3. **Distance from the observed trajectory.** Net-effect error grows with the size of the change. We don't currently report how far each sweep point's insulin is from the field's. The insulin-needs reference itself spans ×0.7–1.3 (±30%), outside the ±10% "safe" zone. Lift is computed between two counterfactuals that are both off-support, which partly cancels the bias but doesn't remove it.
4. **Uncorrected field highs → fictional lows** (our own diagnosis: on bddp10, 54% of counter lows follow a field 3-h mean BG above 200). This is the residual-absorbs-model-error failure in another form: occlusions and absorption failures look like extra carbs.

---

## 2. Where LoopEval sits: evaluation methodology

| Practice | Field norm | LoopEval | Comment |
|---|---|---|---|
| Outcome axes | TIR primary, TBR/t<54 as safety (Battelino 2019/2023); composites GRI, LBGI/BGRI, CVGA | TIR × t<54 (t<70 when degenerate), Magni reported | Standard. **Add GRI** as a secondary scalar; reviewers will expect it |
| Baseline | Fixed: usual care, SAP, basal-bolus or PID; in-silico RL papers often compare against a weak baseline | Insulin-needs dial sweep on both arms; dominance in the operating band | **Stricter than the norm.** The "halve meal boluses" example (+0.185 → +0.036 lift once the dial is matched) is a good illustration of how the field over-reports |
| Trade-off handling | Scalar composite, or "non-inferior on TBR" | Pareto dominance with re-tuning allowed | Closest analogues: CVGA (Magni 2008, built to compare tunings), GRI grid. Frontier dominance as a decision rule appears unpublished |
| Uncertainty | Mixed models / ANCOVA on per-subject summaries | Paired weekly block bootstrap, two-level cohort CI | Sound; uncommon in AID papers |
| Data length | ≥14 days for TIR (Riddlesworth 2018); time-below-range needs more (R² 0.76 at 14 d; ~29 d for ±5% individual TIR error†) | 2-month and 90-day beds | Fine for TIR. Per-donor t<54 is still a rare-event metric (0.1–0.5%), so band verdicts on t<54 are fragile |
| Learned components | Chronological per-patient split; patient-level leakage is a common critique | Hold-out + leakage audit + drift (GOALS) | Matches best practice |
| Multiplicity | Trials: pre-registration and hierarchical testing. Algorithm search: largely ignored | ~40 candidates, plus band, guard and verdict-rule choices, all scored on the same ~10 donors. One pre-registration (E40) | **Main methodological gap** (§5D) |
| Heterogeneity | Subgroups; "bigger gains from worse baselines" | Multi-donor mean headline; per-bed verdicts; M4 found ~zero between-donor variance for the stack | Good. Add "fraction of donors improved + worst donor" to every headline |
| Off-policy evaluation (IS, DR, FQE, g-computation) | Used in offline-RL diabetes papers (Zhu 2023; Emerson 2023), validated only in-simulator | Not used | OPE needs overlap, which aggressiveness sweeps break. Our model-based approach is the right primary tool. OPE-style **overlap diagnostics** are still worth borrowing (§5B) |

**Our dial is close to what commercial systems already expose.** The insulin-needs dial approximates what Omnipod 5, the 780G and Control-IQ offer users (target, sleep/exercise modes, TDD adaptation). "Beat the dial" is therefore "beat what a well-tuned commercial-style system can do."

---

## 3. Where LoopEval sits: algorithm design and optimization

### 3.1 What the field converged on

Every cleared system ended up with roughly the same set of features:
- **A short-horizon prediction or PID core.** Examples: Control-IQ predicts about 30 min ahead; Loop about 6 h.
- **One user-facing aggressiveness dial**, usually the target.
- **Slow adaptation from total daily dose (TDD) or delivered insulin**: CamAPS, Omnipod 5, 780G, iLet.
- **Asymmetric hypo protection.** Examples: IOB constraints (Ellingsen 2009), insulin feedback (Steil), safety supervisors, zone-MPC's asymmetric costs (Gondhalekar 2016), and Control-IQ's 60% corrections.
- **Learning that transfers to humans is slow and low-dimensional.** Run-to-run basal/CR (Dassau 2017, single-arm), AI settings advisors (Nimri 2020, RCT), RL that personalizes a few dose multipliers (Jafar 2024). Deep-RL state→insulin policies remain in-silico only.

### 3.2 Mapping our ledger onto that literature

| Our mechanism family | Nearest literature | Read-across |
|---|---|---|
| aIRC (C01), C20 post-low rise-cut, Negative Insulin Damper (C37) | Asymmetric zone-MPC costs; insulin feedback; IOB constraints | We are rediscovering the asymmetric-cost principle. Our contribution is showing **which state-gated forms** beat the dial (C20 carries 92% of the stack's lows reduction) and which are just the dial |
| σ-band C22/C29/C35 (volatility-widened lower forecast) | Chance-constrained / stochastic MPC (Lackinger 2017; Sonzogni 2023, in-silico only); conformal prediction for CGM used for **alerts only** (2026†) | **No published dose-capping use of calibrated uncertainty bands in AID.** C35 ("k=1 at 60 min = realized p10") is effectively an empirical-quantile band. Formalizing it with adaptive conformal methods would be novel |
| Calm-high licence C23/C31 | Control-IQ's automatic corrections; 780G auto-correction; oref SMB | The σ gate as the information carrier ("without σ it's the dial") is new |
| UAM / early-rise / ICE-boost (C05–C07) | Meal detection: 25–40 min delay, ~88% sensitivity, 7–20% false positives; GRID fixed bolus; UVA Bolus Priming System; oref1 UAM | Trials: about +5 pp post-meal, not significant over 24 h. Our results match. **But we tested gain-boost / projection forms, not capped, probability-scaled priming** (§5G) |
| Circadian needs C12, daily-habit C39 | Hinshaw 2013: no population diurnal ISF pattern; individual patterns noisy. Meal anticipation (Corbett 2022 in silico: +3 pp alone, roughly additive with priming; DCLP6 clinical: not significant but safe) | Our C12 failure is expected from physiology. C39 (habit) neutral matches DCLP6 |
| Learned forecaster C19, oracle O1 | **Lee et al. 2024 IEEE TBME**: LSTM beat Loop on RMSE but lost in closed loop (77% vs 86% TIR in silico) because carbs and insulin are confounded in observational data. GlucoBench: deep models not uniformly better out of distribution | Strong independent confirmation of our "R² ≳ 0.7 or it hurts" bar and of judging forecasters only by closed-loop counterfactual. It also suggests why C19 per-patient GBM underperformed (§5G) |
| Slow RC C38, autosens C14 | oref autosens/autotune/dynamic ISF: community-only, no controlled data; Trio docs: "no empirical data analysis to support Sigmoid" | Our finding that one-signed adaptive offsets are the dial, applied adaptively, is the first quantitative statement of this I'm aware of |
| Loop and Learn ports C36/C37; GBAF C03; IRC C02 | Shipped "Algorithm Experiments" and customizations backed by n-of-1 data and "people like it" | We have **feature-level evidence nobody else has**: GBAF is a slider; IRC is a hotter dial; Basal Lock adds lows; the Negative Insulin Damper gives the largest single lows reduction |
| oref as engine (C17) | Loop vs oref head-to-head on the same subjects: one pig study (Lal 2021, AAPS 58% vs Loop 35% TIR, unannounced meals); FINESSE planned, no results | **Gap in the literature that we are equipped to fill** (§5F) |

---

## 4. The unannounced-meal goal against the clinical evidence

| Quantity | Literature | LoopEval |
|---|---|---|
| 24-h TIR cost of not announcing, same system | 780G −10.2 pp (Shalit 2023); UVA RocketAP −9 pp (DCLP6); **open-source AID with SMB/UAM −2.2 pp, non-inferior (CLOSE IT 2026)**; AAPS adolescents ~−2 pp (Pancreas4ALL) | Natural vs suppressed regimes; "announcement is the largest factor" |
| Post-meal (4–6 h) cost | 15–33 pp; a late 50% bolus at +60 min recovers about a third (Grassi 2026) | Meal-window score: +1.4 to +2.1 TIR on 6 bed-windows from the C30 stack |
| Ceiling from information | Faster insulin 2–3× in silico: unannounced post-meal TIR 80 → 89–94% (Colmegna 2021); meal detection limited by a 25–40 min delay | O1 60-min perfect ICE: **+10 TIR / −0.31 t<54**; O2 carbs 30 min early: +6–8 TIR |
| Gains from settings, not logic | 780G non-bolus days: 76.3% vs 69.3% TIR with 100 mg/dL target + 2 h active insulin time (Niu 2026, industry, observational); digital-twin re-tuning +5 pp | Operating-point delta is reported but not optimized as a deliverable |
| Safety of aggressive FCL | Several trials found *less* hypoglycemia without announcement (user boluses cause lows); others (MMPPC, pediatric AAPS registry) found more | Our D1 rule: under suppression the stack costs +0.115 t<54 and the band alone −0.031 |

**What this means for us.**
- Our oracle headroom of about +10 TIR sits right at the clinical gap. The ceiling is consistent with the field.
- The CLOSE IT result (−2.2 pp for oref-style FCL vs HCL) is the strongest external evidence that **oref's SMB/UAM stack handles unannounced meals better than Loop's**. The pig study points the same way. We have the only harness that could test that on matched real-world data.

---

## 5. New paths for exploration (prioritized)

### A. Validate the counterfactual on natural experiments we already have *(highest value)*

Villa-Tamayo's design needs a person observed under two policies. BDDP has these, recorded:
- **Insulin-needs overrides.** `pumpSettingsOverride` events carry `isf/basal/cr` scale factors, so the field contains **episodes of our own reference dial being turned**. Replay a no-override segment at the override's scale and compare with the observed override segment, matched on time of day and announcement behavior. This tests the reference curve itself, which is the foundation of every lift number.
- **Settings eras** (`runs/2026-08-08-settings-eras`; bddp05/10/02 edit settings often): replay era 1 under era 2's settings and compare with observed era 2.
- **Dosing-strategy switches** (autobolus ↔ temp basal; bddp08 has 129 temp-basal eras): a within-person crossover of two controllers.
- **Loop version upgrades / IRC toggles** where they can be inferred.

Report equivalence per metric, as Villa-Tamayo did. Expect TIR to pass. **What matters is whether t<54 passes, and in which direction it is biased.** If the bias is directional, it can be calibrated out, or at least the lows axis can be given a stated error bar. The same data also answer whether the counter-reg floor parameters are right.

### B. Measure and bound counterfactual distance; run a "sim-of-the-sim"

1. **Report the distance of every sweep and candidate point from the field**: Δ total insulin, Δ IOB distribution, fraction of cycles whose dose differs by more than X. Flag verdicts that depend on far-off-support points.
2. **Replicate Vettoretti 2016 for our method.** Generate synthetic "field" histories with a parametric plant where the true counterfactual is known: TidepoolSim is local, or simglucose / ReplayBG. Include hypotreatments, unannounced meals and sensitivity drift. Run LoopEval's ICE replay of a candidate and compare with the plant's truth. This gives:
   - LoopEval's own domain of validity: error as a function of the Δinsulin size;
   - whether **lift ranking** survives even where absolute values don't. Colmegna 2014 showed controller rankings can flip between simulators.
3. **Cross-engine check.** Run the top candidates (C30 stack, C37 damper, aIRC) through ReplayBG (no residual, posterior credible intervals) on the same donors. A ranking that agrees across two engines with different failure modes is much stronger evidence than either alone.

### C. Replace the counter-reg floor with a hypotreatment behavior model

Already on our roadmap. The literature gives a template (ReplayBG hypotreatment handlers; Vettoretti 2018 patient decision simulator):
- detect rescue carbs in the field (carb entries or ICE spikes inside low windows; our lows study has 4,639 clean lows across 57 donors to fit from);
- remove them from ICE;
- trigger modeled rescues in the counterfactual from the counterfactual BG, using each donor's empirical rescue size and latency distribution.

Score with and without (the "dual scoring" already proposed). Calibrate against (A).

### D. Evaluation hygiene against forking paths

- **Lock a confirmation set.** The EDA pool has 159 screened donors, yet frontier verdicts rest on about 10. Freeze, say, 15–20 donors that no one looks at until a candidate and the scorer are frozen. Confirm the C30 headline there.
- **A multiplicity budget.** Keep a running count of candidates × variants scored on the development donors, and report the headline with that count (or a simple Bonferroni/Holm across mechanism families). Pre-register band, guards and verdict rule before confirmation. E40 shows the team already does this well; make it the default.
- **Settle M10's verdict rule before** the next batch, not after.
- **Add GRI** and "% donors improved / worst donor" to every headline.
- **Flag beds where t<54 events are too sparse** for a band verdict (Riddlesworth: time-below-range needs more than 14 days; our per-donor t<54 is 0.1–0.5%). Use t<70 or LBGI as the lows axis there.

### E. Make the operating-point recommender a first-class output

The literature's largest demonstrated algorithmic-adjacent gains come from re-tuning settings (Kovatchev 2025 +5 pp; Nimri 2020; Niu 2026 ~+7 pp†), not new logic. LoopEval already computes, per donor, the whole insulin-needs curve and where the field point sits on it. Concretely:
- **How far is each donor from their own best in-band point**, and what is that worth (Δ TIR at matched t<54)? Run this over the 159-donor EDA pool, not just the frontier beds.
- **Forward-test it the way GOALS demands for learned candidates**: fit the recommended dial on month 1, score on months 2–3; measure drift and data needed. Results are weak or strong depending on (A).
- **Recommend more than the single needs dial**: correction-range target, max-basal cap (the EDA found max-basal headroom governs mild lows independently of ISF, and raising the cap gives +2.9 TIR / +0.6 t<70), and dosing strategy and partial-application factor.
- **Behavior-conditioned defaults**: the D1 rule (announcers vs non-announcers get different configurations) is already a behavior-adaptive policy. Generalize it to *estimate the announcement rate online and select the configuration*, analogous to Medtronic's non-bolusers result. No trial has done this adaptively.

This is also the most directly regulator-relevant output. Tidepool Loop's 510(k) was justified by retrospectively subsetting real-world data to an intended-use settings range.

### F. Loop vs oref on the same real patients

The OpenAPSSwift engine exists and is Trio-matched (C17), but there is no frontier result. Run oref (SMB + UAM, with and without dynamic ISF) against Loop:
- on the hands-off beds and in the announcement-suppressed regime;
- each arm on its own aggressiveness dial (oref needs an equivalent profile-percentage sweep), with dominance compared between the two frontiers.

This directly tests the CLOSE IT / pig-study signal (oref-style FCL is close to HCL) with matched patients, which no one has published. It also gives the community its first counterfactual evidence on dynamic ISF, sigmoid ISF and autoISF, features that are widely used with no data behind them. Note C17's own safety signal first: summed IOB at the 54 mg/dL crossing was 8.6 for Loop vs 41.7 for oref.

### G. Mechanisms the literature suggests that we haven't tried in this form

1. **Capped, probability-scaled meal priming plus a habit prior.**
   - UVA Bolus Priming System: a fixed dose ∝ P(meal), capped at about 6% of TDD; post-meal AUC p=0.047; no hypos.
   - Corbett 2022: priming and history-based anticipation are roughly **additive**.
   - Our C05–C07 boosted gain or extrapolated the rise. C39 shifted the forecast. None was a *bounded, one-shot priming bolus* gated by a detector *and* by the donor's habit prior. Test it in the suppressed regime, and include IOB-at-54-crossing in the safety check.
2. **Late announcement as its own regime and candidate.**
   - As an evaluation regime: shift real carb entries +30/+60 min and scale them to 50%. This is what many people actually do (Laugesen 2024: about 2.2 missed or late boluses/day, each costing ~10 pp TIR). It sits between "natural" and "suppressed."
   - As a candidate: when carbs are entered after a detected rise has begun, backdate the carb absorption start to the detected onset, and credit the automatic insulin already delivered against the meal. This needs no new information, only better use of a late entry.
3. **Calibrated lower bands (adaptive conformal) instead of a hand-tuned σ multiplier.** CGM residuals aren't exchangeable, so use ACI/EnbPI-style online quantile tracking of realized forecast error per horizon, and dose to a calibrated p10 (or a chance constraint). This turns C22–C35 from tuned constants into a principled, self-calibrating mechanism. The literature only uses conformal bands for alerts, so it is publishable either way.
4. **Pooled, structure-preserving learned forecasters.** C19 was per-patient GBM, hold-out R² 0.16. Lee 2024 shows observational confounding breaks pure-ML forecasters in closed loop. Instead:
   - keep Loop's insulin and carb physics and learn only the **ICE residual**;
   - pool training across the 159-donor pool or MetaboNet (3,135 subjects, including the Jaeb Loop study and OpenAPS Commons†), with per-donor fine-tuning;
   - judge only by closed-loop counterfactual against the R² ≳ 0.7 bar.

   O1 shows the prize is large (+10 TIR), so even partial skill at the right horizon may matter.
5. **Situation-class pull-back, guided by the event study.** "Predictable is not exploitable" (C32/C33) is an important finding. The literature's version of the same lesson is that global brakes cost mean glucose (insulin feedback, Steil 2011). One untried variant: let the classifier set the **IOB cap** in that class rather than gate the forecast, as Ellingsen does with an IOB constraint, since Loop sits at 0 U/h by the time the low is forecast (the "suspend wall").

### H. Write it up

Three contributions the literature lacks:
1. **Dial-matched frontier dominance** as an evaluation rule, with the "halve meal boluses" and ISF-vs-insulin-needs examples showing how standard comparisons over-report.
2. **Feature-level counterfactual evidence for shipped community features**: IRC, GBAF, Basal Lock, Negative Insulin Damper, and soon dynamic ISF.
3. **The RWD replay forensics checklist**: the ETL pitfalls list is directly reusable by MetaboNet / Tidepool users.

Venues: JDST or DT&T for (1) and (2); a short methods note could pair with GluPredKit / MetaboNet, which share our forecasting-isn't-control view (Wolff et al. DT&T 2025).

---

## 6. Corrections to watch for when reading the agents' source notes

- One literature summary described LoopEval as dose-only replay. It is not: it simulates counterfactual glucose. Our *field* comparators (APS-what-if, trio-algorithm-validator) are dose-only.
- Another described our counter-reg mechanism as "a hard 54 mg/dL floor." It is a gated defense-velocity term (onset/gain/max), off by default. The literature critique (unphysical shape, no behavioral rescue model) still applies.

---

## 7. Key references

**Simulators and replay**
- Kovatchev BP, Breton M, Dalla Man C, Cobelli C. In silico preclinical trials. *JDST* 2009;3:44–55.
- Dalla Man C et al. UVA/Padova simulator: new features (S2013). *JDST* 2014;8:26–34.
- Visentin R et al. UVA/Padova goes from single meal to single day. *JDST* 2018;12:273–281. doi:10.1177/1932296818757747
- Kovatchev BP, Patek SD, Ortiz EA, Breton MD. Net effect method. *DT&T* 2015;17:177–186. doi:10.1089/dia.2014.0272
- **Vettoretti M et al.** Predicting insulin treatment scenarios with the net effect method: domain of validity. *DT&T* 2016;18:694–704. doi:10.1089/dia.2016.0148
- Hughes J et al. Replay simulations with personalized metabolic model. *JDST* 2021;15:1326–1336. doi:10.1177/1932296820973193
- Cappon G et al. ReplayBG. *IEEE TBME* 2023;70:3227–3238. doi:10.1109/TBME.2023.3286856 (github.com/gcappon/replay-bg)
- **Villa-Tamayo MF, Colmegna P, Breton MD.** Validation of the UVA simulation replay methodology using clinical data. *DT&T* 2024. doi:10.1089/dia.2023.0595
- Kovatchev BP et al. Human–machine co-adaptation to AID: digital-twin RCT. *npj Digit Med* 2025;8:253. doi:10.1038/s41746-025-01679-y
- Vettoretti M et al. Patient decision-making of CGM users (decision simulator). *IEEE TBME* 2018;65:1281–1290.
- Colmegna P, Sánchez-Peña RS. Analysis of three T1DM simulation models. *CMPB* 2014;113:371–382.
- FDA K203689 (Tidepool Loop) and K234055 (DEKA Loop) decision summaries.

**Evaluation and metrics**
- Battelino T et al. International consensus on TIR. *Diabetes Care* 2019;42:1593. Battelino T et al. CGM metrics for clinical trials. *Lancet Diabetes Endocrinol* 2023;11:42–57.
- Klonoff DC et al. Glycemia Risk Index. *JDST* 2023;17:1226–1242. doi:10.1177/19322968221085273
- Magni L et al. Control Variability Grid Analysis. *JDST* 2008;2:630–635.
- Riddlesworth TD, Beck RW et al. Optimal sampling duration for CGM. *DT&T* 2018.
- Gottesman O et al. Guidelines for RL in healthcare. *Nat Med* 2019;25:16–18.
- **Lee JM, Pop-Busui R, Lee JM, Fleischer J, Wiens J.** Shortcomings in the evaluation of blood glucose forecasting. *IEEE TBME* 2024. doi:10.1109/TBME.2024.3424665

**Algorithms and tuning**
- Brown SA et al. Control-IQ RCT. *NEJM* 2019;381:1707. Russell SJ et al. Bionic pancreas RCT. *NEJM* 2022;387:1161. Burnside MJ et al. CREATE. *NEJM* 2022;387:869.
- Lum JW et al. Loop observational study. *DT&T* 2021;23:367.
- Dassau E et al. 12-week AP with weekly adaptation. *Diabetes Care* 2017;40:1719.
- Nimri R et al. AI-based insulin dose optimization (Advisor Pro) RCT. *Nat Med* 2020;26:1380.
- Gondhalekar R, Dassau E, Doyle FJ. Periodic zone-MPC with asymmetric costs. *Automatica* 2016;71:237.
- Ellingsen C et al. IOB constraints in MPC. *JDST* 2009;3:536.
- Hinshaw L et al. Diurnal pattern of insulin action in T1D. *Diabetes* 2013;62:2223.
- Lackinger et al. Chance-constrained MPC for glucose. *IEEE CDC* 2017.
- Sergazinov R et al. GlucoBench. *ICLR* 2024.

**Unannounced meals**
- Shalit R et al. 780G HCL vs FCL. *DT&T* 2023;25:579.
- Garcia-Tirado J et al. RocketAP / DCLP6 meal anticipation. *Diabetes Care* 2023;46:1652.
- Wilkinson T et al. CLOSE IT (open-source FCL vs HCL). *DT&T* 2026;28:941. doi:10.1177/15209156261423558
- Moscoso-Vasquez M et al. UVA Bolus Priming System. *DT&T* 2025;27:93.
- Corbett JP et al. History-informed anticipation + priming (in silico). *JDST* 2022;16:52.
- Laugesen C et al. Missed/late meal boluses and TIR. *DT&T* 2024;26:897.
- Niu F et al. 780G no-bolus days and settings (industry). *Diabetes Care* 2026;49:419.
- Lal RA et al. AAPS vs Loop in diabetic pigs. *Clin Transl Med* 2021. doi:10.1002/ctm2.387
- Lal R, Braune K, Lewis DM et al. Open-source fully closed loop review. *Diabetologia* 2026. doi:10.1007/s00125-025-06644-8
- Ibrahim M et al. Meal detection systematic review. *PLOS Digit Health* 2026.
