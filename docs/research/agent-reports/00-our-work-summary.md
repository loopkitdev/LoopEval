I've read the requested files and written the summary below. Paths are relative to `/Users/pete/dev/loopeval-algo/` unless absolute. "Ledger" means `docs/candidates/README.md`.

# LoopEval: technical summary for a literature comparison

## 1. The simulator

**What it is.** It is a data-driven counterfactual replay of real CGM, insulin and carb history. It is not a parametric physiological model (`docs/simulator-guide/README.md` §1–2, §6). It is written in Swift: the engine is `Sources/EvalCore/Engine/ClosedLoopSimulator.swift`. The controller is pluggable (`DosingEngine.swift`): either Loop's `LoopAlgorithm` (a loopkitdev fork) or oref/OpenAPS through `OpenAPSSwift`. The oref engine was matched to Trio's internals: weighted TDD, the dynISF schedule, temp-target presets, autosens over 24 h, and a JS golden-master oracle (§12). The design principle is "the user's real-day physiology, with different insulin."

**ICE, the insulin counteraction effect (§6).**
- `ICE(t) = v_BG_observed(t) − v_insulin_modelled(real doses)`, computed once from the real day.
- It contains everything that is not modelled insulin: carbs, EGP, exercise, dawn effect and sensor surprise. It is treated as independent of dosing.
- **Counterfactual step:** `counter[t+5min] = counter[t] + insulinEffect(candidate doses) + ICE(real) + counterReg`. Integration starts from a 6 h burn-in in which the real pump deliveries are used, so initial IOB is realistic.
- **Fidelity form (§10):** `counter[t+Δ] = counter[t] + realBGdelta + m·(candPhys − realPhys) + counterReg`. `candPhys` and `realPhys` are the physical insulin effects with EGP zeroed. When the candidate's doses equal the real doses, the m term is exactly zero, so identity is bit-exact. A mandatory identity check (max|Δ| = 0.0 on counter, delivery and per-cycle dose) gates every engine change.
- **Substrate (§4):** a 5-minute grid with two traces. An RTS-Kalman-smoothed `physGlucose` is used only to estimate physiology (ICE and m); this deliberately uses future samples. The raw noisy `simGlucose` is what the controller sees and what is scored. A sensor cap of 400 mg/dL applies to the controller input.
- **Decision-time replay (§7):** the controller sees only glucose and doses up to t, and carbs whose *entry* date is ≤ t.

**How it differs from UVA/Padova-style models.** There are no compartments and no virtual patients. The plant is the person's own residual, replayed. Strengths: no parameter identification, and real meals, exercise and noise are kept. Acknowledged weaknesses:
- **Rescue-carb confound:** the real rescue carbs are baked into ICE at a fixed time and amount. A candidate that prevents a low still inherits them and gets a spurious rebound; a candidate that causes a deeper low gets no extra rescue (§8; AGENTS.md traps).
- **Long divergence becomes fiction.** ICE cannot react to a different trajectory, so the method is most trustworthy exactly where candidates differ least (`runs/2026-08-22-eval-review/REVIEW.md` §1.3).
- **ICE cannot tell undelivered or ineffective insulin from extra carbs.** Field highs left uncorrected (occlusion, open loop, data gaps) get "corrected" by the counterfactual into fictional lows. This is mechanism A in memory `counterfactual-overcorrection-diagnosis`: on bddp10, 54% of counter lows follow a field 3 h mean BG above 200.
- **Free integration with no pull back toward the field.** A transient meal-time IOB deficit can lock in (mechanism C, heavy announcers, bddp04).
- **Gap handling (§11):** long CGM gaps of more than 30 min are re-anchored to the real CGM. Pump outages force delivery to 0. Only the disruption interval itself is excluded from scoring, not the recovery window (policy 2026-05-26).

**Counter-regulation floor (§8).** When the counterfactual is below the onset threshold, `crVelocity = defense(counter) − defense(real_BG)`, with `defense = min(gain·(onset−bg), max)`.
- It is gated on counter < onset (fix `876a08a`). Without the gate, high-running candidates were driven below the real trace.
- It is off by default. Whole-trace runs use onset 54 / gain 0.4 / max 8 (`docs/FRONTIERS.md` §3). The episodic meal evaluation leaves it off.
- The docs call it a crude rescue-carb proxy, not physiology: glucagon response is lost in T1D. Its shape is unphysical (an instantaneous ramp of about 5.6 mg/dL/min at 40, against an observed recovery maximum of 2.6–3.3). So it over-recovers deep lows and flatters candidates that dose more.
- Characterization: 243 real low episodes, median trough about 60 mg/dL.
- Planned replacement, not built: a BG-triggered rescue-carb model with the real rescue removed from ICE.

**Sensitivity inference / fidelity model (§9–10).**
- `m(t) = clamp(v_BG / v_insulin, 1, 2.0)` over a trailing 30 min, applied only where insulin is active. m never goes below 1, on the argument that a downward residual is almost always insulin.
- m scales only the physical-insulin term; EGP is kept separate and unscaled.
- The controller doses on its believed ISF (scheduled or candidate); the plant responds at the true ISF (scheduled × m). The two are deliberately decoupled.
- Field check: in the period the device actually ran IRC, the fidelity sim reproduced the real low time, while the plain sim (m ≡ 1) under-counted it by about 40%. Raw per-step m beat smoothed variants, which over-attribute.
- Since 2026-09-22, `--patient-isf` pins the plant independently of the controller. Measured result (memory `patient-vs-controller-isf-decoupled`, ledger M8):
  - The plant term is about 2.2% of a matched ISF sweep's effect on bddp11.
  - Lift moves by less than 1% across ±10% assumed patient ISF.
  - Verdicts are stable to ≤0.35 TIR / ≤0.10 t<54 on the highest-ISF donors (bddp05 ISF 149, bddp08, bddp11).
  - Patient ISF is therefore a nuisance parameter. Only the absolute operating point moves, by up to 1.1 TIR / 0.2 t<54.

**Validation bar** (memory `replay-verification-process`, Pete's canonical two steps):
1. Decision-time-replay (DTR) forecasts must match the field's recorded `bgForecast` within a few mg/dL, ranked by **worst case, not average**. Only three proven exclusions are accepted: cancelled or incomplete boluses, backfilled BG, and sub-second CGM timestamp wobble.
2. Only then must doses match within ≤0.05 U or U/hr.

The ground truth is delivered dose history, not recommendations or devicestatus (devicestatus is a post-dose snapshot).

**Fidelity achieved:**
- **Instrumented real Loop 3.14.2 rig** (iPhone, virtual pump, per-cycle component dumps; memory `instrumented-loop-ground-truth-rig`): forecast assembly, RC decay, momentum and insulin effect are bit-exact on basal-only data. Assembly worst 0.0013 mg/dL; momentum 0.000 over 1155 cycles; insulin effect 0.00000000 over 21/21 cycles. Carbs and boluses are unverified on the rig. The rig also showed that Loop freezes ICE live while LoopEval recomputes from final history (memory `ice-frozen-live-proven`), which is an open fidelity gap.
- **Forecast fidelity is gated by IOB reconstruction** (bddp09; memory `forecast-fidelity-gated-by-iob`): corr(forecast max|Δ|, |ΔIOB|) = 0.86. With IOB matched within 0.05 U, median max|Δ| is 2.0 mg/dL.
- **user1 week** (class-1 emulation flags; `docs/loop-algo-classes.md`): auto-bolus 93.9–94.5% exact, temp basal 94.3% within 0.05 U/hr, residual +6.2 U/week (~3% of TDD) after outage exclusion.
- **bddp09:** auto-bolus 78% bit-exact, 95% within 0.05 U, worst 0.300 U, zero signed bias.
- **Cohort recommendation-vs-recommendation (ETL v14):** bddp11 96.6% exact (worst 0.65 U) down to bddp02 61.3%. Temp-basal donors scored 43% / 26% exact, later 75–96% action-match.
- **Tidepool PR #40 "loop-1.0" emulation** (`runs/2026-09-24-tl10-screen/VALIDATION.md`): bit-identical to the fork. Against field: 94.3% within 0.1 U/hr, unbiased ±0.003.
- **Deployed Loop vs LoopAlgorithm deltas** (`docs/loop-algo-classes.md`): dose-time vs mid-absorption ISF, the gradual-transitions gate, the momentum cap, and RC `decayEffect`. Without these, class-2 forecasts collapse on fast unannounced rises (mean forecast error 116 → 24 mg/dL once corrected).

**Validated vs not.** Hands-off beds reproduce the field point at insulin-needs ×1.00:

| bed | field TIR / t<54 | sim at ×1.00 TIR / t<54 |
|---|---|---|
| bddp11 | 68.5 / 0.48 | 68.3 / 0.50 |
| bddp10 | 73.6 / 0.13 | 73.7 / 0.13 |

Source: `runs/2026-08-24-unannounced/cohort_ops.csv`. Announcers do not reproduce field lows at the operating point:

| bed | field t<54 | sim t<54 at operating point |
|---|---|---|
| bddp05 | 0.32 | 1.93 |
| bddp08 | 0.13 | 1.49 |
| bddp06 | 0.10 | 0.84 |

bddp04 is excluded: its sim t<54 runs 2.5–12.2% and never reaches the field's 1.32.

## 2. Data

**Sources:**
- **Tidepool Big Data Donation Project (BDDP)**, via a Databricks ETL (`analysis/loopeval_analysis/tidepool/`).
- **Main cohort:** donors bddp01–bddp11, all Loop users. 10 of 11 are scoreable; bddp04 is out. The 2-month window is 2026-05-08 → 07-08 and the 90-day window is 2026-05-08 → 08-06.
- **Wider EDA pools:** 159 donors (core plus an oversampled hands-off stratum, drawn from 8,026 automated-system donors). The lows study used 56 donors plus ns3 (4,639 clean lows). The interrupted-bolus study used 67 donors over 120 days.
- **Nightscout aliases:**
  - user1: Omnipod, IRC until 2026-04-24, minimal announcing.
  - user2: Fiasp, IRC throughout, overrides, heavy announcer. Used for 9-week to 1-year runs.
  - ns3: standard RC, hands-off. 90 days (06-30 → 09-28) and 1 year.
  - orefuser / orefuser2: Trio users, fidelity work only.
  - tl10a: Tidepool Loop 1.0, used for the PR #40 validation.

**Bed types:**
- Hands-off non-announcers: bddp11, 10, 01, 09 (01 and 09 have ~0 severe lows).
- Announcers: bddp03, 08 (heavy), 05, 06, 07 (tight control, 97% TIR).
- Pure temp-basal strategy: bddp02 (fully manual doser), bddp07.
- bddp03 uploads 1-minute CGM.

**Data pitfalls found** (each changed results; memory notes and simulator-guide §3):
- **Duplicates and mirrors:** HealthKit bolus double-count (2× TDD). Carb absorption time lost in the HealthKit-mirror dedup (worst forecast error 90 mg/dL).
- **Schedules:** expanded at UTC midnight instead of local midnight (6–7 h shift). An end-of-window settings snapshot was applied to the whole window. Traveller timezone anchoring (ETL v19).
- **Insulin model:** hard-coded per donor until inferred by IOB match.
- **Overrides:** early cancels over-extended (forecast RMSE 20 → 8 after the fix). Missing-end overrides (v18; bddp10 bolus exact 84.8 → 89.4%). A future-override target leak. Loop applies an active override's target flat across the whole forecast.
- **Delivery reconstruction:** phantom basal from dropped suspends; stale pre-fix exports carried 21–88 h of phantom basal. Delivery limits hard-coded to 12 U / 8 U/hr when real limits span 3–30 U and 0.8–10.8 U/hr (v14). Dosing strategy switching mid-window (v15; bddp08 has 129 nightly temp-basal eras). Temp "cancel" (rate 0, duration 0) misread as a suspend. Commanded vs delivered running temp (a +0.06 U/hr bias).
- **Loop state and cadence:** loop-offline gaps (bddp11: +24 gaps / 15.9 h). Cancelled boluses (24.25 U requested, 0.40 delivered). IOB recorded on a floored 5-min grid. devicestatus is post-dose. The Databricks snapshot is frozen.
- **CGM:** 1-minute CGM corrupting the σ fit (M5). Dual CGMs interleaved.
- **Privacy:** the Databricks credential is production PHI, and a Nightscout bolus list de-anonymized a BDDP donor 686/686.

## 3. Evaluation method

Sources: `docs/FRONTIERS.md` → Scoring; `docs/GOALS.md`; `analysis/loopeval_analysis/{band,frontier,scoring}.py`.

- **Reference curve.** Stock Loop is swept on the **insulin-needs dial** f (basal ×f, ISF ÷f, CR ÷f), a preset-style single aggressiveness knob. An ISF-only dial was rejected because it overstates lift. Canonical example: a "halve meal boluses" lever showed +0.185 lift against the ISF dial and +0.036 against insulin needs.
- **Lift.** Signed, axis-normalized closest distance from a candidate (TIR, t<54) point to the reference polyline. Positive means below-and-right (more TIR, fewer lows); about 0 means the change is a slider on the dial.
- **Operating band.** Candidate points within the donor's validated multiplier ±0.1 are judged against the reference within ±0.2. Lows are capped at the worst in-band reference value. The lows axis falls back to t<70 when t<54 ≈ 0. The band rule was adopted because whole-sweep mean lift scored a clearly valuable oracle (O2) negative.
- **Statistics.** Paired weekly (or daily) block bootstrap gives a CI on every number. Verdicts: IMPROVES (CI > 0 and some in-band point strictly dominates), NEUTRAL, WORSE.
- **Multi-donor mean is the only headline.** It uses a two-level bootstrap (`cohort_ci.py`, M2); the earlier "mean of per-bed lower bounds" was wrong.
- **Scorer guards:** UNDER-COVERED (fewer than 3 in-band points); DEGENERATE-REF (reference TIR span under 1 point, lows span under 0.05, or lows at op under 0.10); matched denominators across arms (E39).
- **M10, newer per-setting dominance:** does some candidate setting strictly beat the person's own setting, with a margin of ≥0.5 TIR or ≥0.05 t<54? Requires densifying to 0.025 steps. This reorders the ledger, and the verdict rule is still Pete's open decision.
- **Regimes.** *Natural* (real announcing passes through) and *announcement-suppressed* (`--no-carb-entries --no-user-boluses`). M1: suppressed beds must be scored at a re-tuned operating point (matched lows), because the dial is "cheap" at ×1.00 there (83–434 TIR per point of t<54, against 3–18 at real operating points).
- **Meal-window score.** Unannounced-meal windows [−30, +300 min] with the dial re-tuned to matched lows. The episodic evaluation scores AUC>180 and AUC<70 over [T−2h, T+8h].
- **Metrics:** TIR, t<54, t<70, t>180/250, AUCs, IOB at the 54 crossing (a danger axis the duration hides), and Magni risk (M6). Magni's minimum is at 138.9 mg/dL, so it favours pull-back mechanisms; it is reported but not adopted.
- **Learned candidates (GOALS):** must report data needed, drift, a hold-out on a disjoint later period, and a leakage audit, across multiple donors. `--oracle-*` modes are for headroom only.
- **Oracles:**
  - O1, perfect 60-min ICE forecast.
  - O2, carbs visible 30 min early.
  - O3, perfect retrospective ISF (planned, never run).

## 4. Candidate mechanisms

Lift is band lift unless noted.

**Dosing-logic / gain tweaks (closed, dial-like)**
- **C03 GBAF / application factor:** rides the reference.
- **C04 package flags / momentum:** midAbsorptionISF is the main aggressiveness driver; the gradual-transitions gate is the only roughly orthogonal one (+0.019, NEUTRAL).
- **C15 RC window and duration:** dur120 harmful; 40 min NEUTRAL; 30 min WORSE.
- **C13 basal × ISF decoupling:** +0.056 at most on ns3, not followed up.
- **C11 uncertainty-cap dosing:** WORSE at every k (−0.11 to −0.16).
- **C34 soft low gate (ramp instead of the min-guard cliff):** not a default; Δt54 ≥ 0 on the mean (bddp08 +0.14).

**Retrospective correction variants**
- **C01 asymmetric integral RC (aIRC):**
  - bddp11 90 d: IMPROVES, +0.022 [+0.006, +0.036].
  - 2-month beds: NEUTRAL, mean +0.005.
  - ns3: NEUTRAL, +0.006.
  - user2: strict dominance.
  - Best by Magni (−0.52, 8/8 beds) and under M10 (beats the person's setting on 5/8).
- **C02 IRC:** a hotter dial; WORSE in band on bddp11.
- **C18 asymmetric standard RC:** NEUTRAL, closed.
- **C20 post-low-gated RC rise-cut** (S 0.3, 12 h window, release at 180):
  - IMPROVES on 3/7 beds and positive on all 7.
  - Carries 92% of the final stack's lows reduction (E38).
  - The 12 h window saturates (5/5 beds); S = 0.2 is the lows-priority option.
- **C21 fast-rise gate:** NEUTRAL.
- **C32 descent rise-cut:** looked good on b11_90d; over 9 beds +0.001, 1 IMPROVES / 1 WORSE. Closed.
- **C38 slow (autosens-scope) RC:**
  - Cohort +0.038 [+0.001, +0.090], but on one-signed beds it is just the dial applied adaptively.
  - IMPROVES with margin only where the residual changes sign: bddp06 +0.215, bddp05 +0.074 (corr 0.73).

**σ-band / uncertainty (volatility-aware forecast)**
- **C22 σ-widened lower band:** σ5 is a causal EWMA of the SD of 5-min increments; the forecast is lowered by k·σ5·(τ/5)^0.71 out to 60 min.
  - bddp11 90 d +0.025.
  - WORSE on announcers until a COB = 0 gate was added; WORSE on bddp05.
  - Fixed-σ control (E19): depth and σ modulation together are much more than either alone.
- **C27 baselined, C28 depth-normalized:** C27 removes the harm and the lift together; C28 fails.
- **C29 depth-capped:** +0.004, 2 IMPROVES / 0 WORSE.
- **C35 guard-only band with the measured plateau** (M7: k = 1 at 60 min equals the realized 10th-percentile downside; on the lows donors the downside plateaus at about 5–6 σ5 out to 6 h):
  - 2.6× the severe-lows reduction on 6 beds.
  - A wash on 9 beds: bddp06, an announcer, gets +0.08 t<54 under every band form.
- **C33 descent-gated band:** REJECTED. Every gated arm is worse than the ungated band, so the band's benefit is diffuse.

**Calm-high licence (dose more)**
- **C23** (application factor ×2 when BG ≥ 180 and σ5 ≤ the donor's median σ5):
  - IMPROVES on 6/7 then 7/9 beds at about zero lows cost: +0.0122 to +0.0142 [+0.0057, …].
  - Without the σ gate (control) it is dial-like, so σ is the information.
  - 62% between-donor heterogeneity.
- **C25 COB gate:** fixes bddp03's lows cost.
- **C26 trend gate:** a wash.
- **E41 BG threshold:** flat across 160–190; lows appear below 160.
- **S1:** inert on temp-basal donors.
- **C31 target-shift form:** reaches temp-basal donors (cht10 2 IMPROVES / 0 WORSE). Which actuator wins is donor-dependent; a pre-registered discriminator was refuted.

**Stacks and deployment**
- **C24 stack:** components roughly additive (stk3 +0.055 against a component sum of 0.054 on bddp11).
- **C30 deployable stack** (C29 + C23/C25 + C20) is the headline, below.
- **D1 deployment rule:**
  - Announcers get the full stack.
  - Non-announcers get the band alone. Under suppression the stack reads +0.052 at Δt54 **+0.115**; the band alone reads +0.059 at Δt54 −0.031.
- **E50:** aIRC + damper + stack gives the largest polyline lift, +0.044 [+0.010, +0.088], but no additional per-setting dominance. It trades TIR for lows (−0.76 / −0.25 at the operating point).

**Dose-more / unannounced-meal detection**
- **C05 UAM projection:**
  - WORSE on hands-off bddp11 at every N (N = 45: −0.066).
  - On announcement-suppressed bddp07 it first read +16.6 TIR. At a re-tuned operating point that halves to +4.6 TIR (N = 45, IMPROVES).
  - WORSE on bddp03 and bddp08 (Δt54 +1.0 to +3.1).
- **C06 early-rise:** WORSE.
- **C07 ICE rise-boost:** WORSE/NEUTRAL; wins only on bddp07.

**Post-low / sensitivity damping**
- **C08 sensitive mode / double-low prevention:** dominated on user2. With the feed corrected (E52) it is WORSE on the cohort (sens2 −0.029) and is closed.
- **C09 predictive sensitivity damper:** inert ("the suspend wall").
- **C10 post-low ISF multiplier:** WORSE (−3.5 to −8.3 TIR).
- **C14 autosens term:** built, never swept.

**Loop and Learn ports**
- **C36 Basal Lock:** NEUTRAL/dial-like; adds lows (bddp08 +0.17). Closed.
- **C37 Negative Insulin Damper:**
  - Largest single-mechanism lows reduction: Δt54 −0.079 at −0.17 TIR.
  - +0.0225 [−0.0014, +0.0608], P 0.91.
  - No announcer harm (bddp06 −0.15).
  - E48 (the damper on the stack and on the 90-day beds) is not recorded as finished in the ledger.

**Learned / circadian / habit**
- **C12 hourly-needs schedule:**
  - WORSE in-sample and on hold-out (k = 1 hold-out: −5.3 TIR / +0.96 t<54).
  - WORSE at every history length (1–8 weeks), although the profile is stable (r 0.76–0.86).
  - E54 confirmed it on every bed type.
- **C19 per-patient gradient-boosting 60-min ICE forecaster:**
  - bddp11 hold-out R² 0.16: WORSE.
  - Hands-off beds: a dial in disguise (offset positive 63–92% of the time).
  - Announcers (residual target, half strength, hold-out): +0.55 TIR / −0.19 t<54 at the operating point, setting beaten on 4/5, +0.071 [−0.037, +0.195]. The drift audit has not been run.
- **C39 daily-habit term:** cohort NEUTRAL; wins on bddp05 only. The absolute form is WORSE (−0.107).
- **C16 manual-bolus scaling:** the cautionary dial case above.
- **C17 oref as engine:** fidelity work only, no frontier number. IOB-at-crossing-54 summed exposure was 8.6 (Loop) vs 41.7 (oref).

**Headline (ledger HEADLINE, M9/E46 regeneration)**
- C30 `final`, 2 months, 8 donors: **+0.0203 [+0.0042, +0.0366]**, P 0.978, 5 IMPROVES / 0 WORSE.
- 90 days, 6 beds: **+0.0395 [+0.0127, +0.0656]**, 3 / 0.
- Mean Δt54 at the operating point −0.06 to −0.087.
- Typical effect "about +0.5 TIR and −0.1 t<54."
- Four beds improve both axes with no re-tuning (bddp05 +0.6 / −0.15; bddp03; bddp08; bddp09 on the t<70 axis).
- Unannounced-meal windows: CI-clearing TIR gains on 6 bed-windows, for example bddp11 +2.06 and bddp03 90 d +1.37 TIR with −0.10 t<54.
- Hold-out of the σ constants changes no verdict (E25).
- M4: between-donor variance about 0 for the stack.
- **Goal status (2026-08-28):** all criteria marked "met," with limits stated: 8–10 Loop donors from one pool, the suppressed-regime evidence rests on 3 beds plus a judgement about re-tuning, and effects are modest.

## 5. Key negative results and lessons

- **Dosing logic is exhausted.** Gain schedules (GBAF, AF, IRC, flags, uncertainty cap) are re-parameterizations of the dial. REVIEW.md puts it at "about 60% reality, 40% evaluation."
  - Feedback compensates changes to the output, so "modify the forecast, not the output."
  - The suspend wall: Loop is already at 0 U/hr at most lows. In the event study, the best mechanism avoided 2 of 23 lows.
- **Information headroom dwarfs logic.**
  - O1 (perfect 60-min ICE forecast) on bddp11: **+10.0 TIR / −0.31 t<54** at the operating point, lift +0.314. That is about 500× aIRC's +0.019. Half strength still gives +3.9 TIR.
  - A noisy forecast with R² = 0.5 is already harmful (Δt54 +2.18). The skill bar for an additive offset is R² ≳ 0.7.
  - O2 (carbs 30 min early): +6–8 TIR at about 0 t<54.
  - The simulator guide quotes a perfect-foresight bound of ~95% TIR at ~0 lows, with the gap mostly a forecasting problem roughly 85 min ahead.
  - Lookback study: 3–24 h levels add nothing beyond the last 3 h. Only the same clock window on previous days adds skill, with hold-out R² 0.18 at 3 h. Loop's own RC + momentum extrapolation scores −0.06 / −0.37 / −0.80 at 1/3/6 h.
- **Predictable is not exploitable.** The descent-off-a-high class is 23% of lows and 35% of severe lows, with a 3.01× prospective lift, yet C32 and C33 both failed. Do not derive a mechanism's gate from a classifier.
- **Lift does not scale with lows burden** (E40, pre-registered): r = −0.03. bddp10 and bddp02 have the same burden and lifts 18× apart. No substitute variable was fitted afterwards.
- **One-signed adaptive offsets are the dial** (C19 on hands-off beds, C38, C39 absolute). Predictive skill pays only where the dial is expensive (bddp09 is the strongest-habit bed and gains nothing).
- **Recurring traps:** single-window wins vanish across beds; scoring at the wrong operating point; under-covered or degenerate references; σ fitted on the wrong sampling grid; a patch that never landed (identity passed while the arm was a no-op); found bugs blamed for anomalies without testing the link (M5).

## 6. Open problems and stated limitations

- **Engine:**
  - The counter-regulation floor needs replacing with a BG-triggered rescue-carb model.
  - Occlusion / uncorrected-high exclusion and a hard floor on the counter are both unbuilt.
  - Live-vs-final ICE gap.
  - Momentum-cap flag missing.
  - Replay should follow Loop's recorded cycle cadence.
- **Validation gaps:**
  - Carbs and boluses are unverified on the rig.
  - Announcer beds over-produce lows relative to the field (bddp05/06/08, mostly the ones where adaptive mechanisms "win").
  - bddp04 is unscoreable.
  - Temp-mode DTR residuals remain.
  - The simulator guide was last reviewed 2026-08-04, so it predates the patient-ISF and fidelity work.
- **Evaluation:**
  - The M10 verdict rule and its margins are undecided.
  - Rescue-window dual scoring is proposed, not built.
  - O3 has not been run.
  - Absolute t<54 is confounded by compression lows, the CGM floor and the counter-reg floor; deltas and rankings are what hold.
- **Mechanism next steps:**
  - E48 (damper on the stack and on 90-day beds).
  - Mean-zero slow RC.
  - C19 rolling re-fit with a drift audit, or a small state-conditional bias table (IOB × BG × RC sign) on announcers.
  - Why bddp10 is weak and why the actuator choice differs by donor, both explicitly unexplained.
- **Scope:** about 10 BDDP Loop donors plus a few Nightscout users. Loop only for the headline; oref has no frontier result.

## Sibling repos

- **`/Users/pete/dev/loopeval-eda`** (eda branch of LoopEval): an observational distribution study published as four documents. Findings in `docs/agents/eda.md` lessons 1–53:
  - **Cohort:** 159 donors, BDDP-only. Median age 35 (16–60), 27 under 18. Strategy is confounded with hardware: temp-basal users are on twiist + Libre 3, autobolus users on Omnipod + Dexcom.
  - **Settings vs outcomes:** ISF × TDD median 1868, but ISF falls as TDD^0.74 rather than TDD^1. Rule-of-X vs TIR −0.46 with controls and no link to lows. The max-basal headroom governs mild lows (t<70 +0.29) independently of ISF (no interaction). Raising the cap: +2.9 TIR / +0.6 t<70.
  - **Behaviour and outcomes:** boluses/day vs TIR +0.54. Autobolus users have 2.5× the t<54. Heavy settings editors have the best TIR (88 vs 75).
  - **Insulin and sensors:** daily insulin is a stable trait (ICC 0.94) but day-to-day lag-1 is only 0.21. Sensor brand changes the step SD by up to 60%. ICE's ISF is not identifiable by regression in a closed loop.
- **`/Users/pete/dev/loopalgo`:** Tidepool's `LoopAlgorithm`. Pete's PR #40 adds a "loop-1.0" emulation preset (legacy RC decay, no gradual-transitions gate, max active insulin), validated bit-identical to the LoopEval fork.
- **`/Users/pete/dev/TidepoolSim`:** Tidepool Data Science Simulator in Python, built for FDA risk analysis of Tidepool Loop. It uses a parametric `VirtualPatient` with a `SimpleMetabolismModel` and iCGM sensor models. It is the scenario-based contrast to LoopEval's data-driven replay.
- **`/Users/pete/dev/LoopSight`:** a self-hostable Node + SQLite server compatible with the Nightscout API, for monitoring and review (live view, AGP, clinician links). Data infrastructure, not research.

I didn't publish anything or change any files. If you want this as a shareable page for the literature comparison, I can make one.