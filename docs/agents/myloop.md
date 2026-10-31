<!-- Role overlay. Loaded via ROLE.md; see AGENTS.md → Roles. -->

# Role: myloop — CamAPS FX as a source of ideas

CamAPS FX is the Cambridge (Hovorka group, CamDiab) adaptive model-predictive controller. It is
the algorithm inside mylife's **myLoop** (YpsoPump + CamAPS FX app + Dexcom or Libre CGM), and it
also ships on Dana pumps. This role studies it, sets it against Loop and LoopEval, and turns
the parts that might transfer into testable candidates. Those candidates are changes to Loop's
dosing, or to how LoopEval simulates and models a person.

Read with **AGENTS.md** (shared) and **docs/agents/verification.md**. A CamAPS idea counts as an
improvement only when the frontier harness says it is: TIR up AND t<70 down against the needs dial, run on top of
**gr** (guard + runway, now in Loop next-dev). Only experiments and candidates that can show lift over gr are considered
(Pete, 2026-10-31).
That a commercial system ships the idea is not evidence that it helps.

## What this role owns, and what it does not

| Owns | Does not own |
|---|---|
| The CamAPS evidence base: what the algorithm does, each claim sourced and labelled | The literature review as a whole (**research**, `docs/research/`) |
| CamAPS-inspired mechanisms: their design, offline studies (forecast fit), prototype flags | Candidate verdicts and the ledger (**frontier**). Ledger entries are written with frontier, as trio does with TIDEPOOL-6 |
| Hand-offs proposing CamAPS-derived plant or behavior components | The engine (**simulator**), the additive plant (**additive**), the ICE generator (**ice**) |

A mechanism that needs an engine change goes to **simulator** as a proposal, or is built behind a
`--candidate-*` flag on this branch and published under AGENTS.md → *Publishing back to main*, with
the identity check re-run.

## Where the work lives

- `docs/myloop/`: this role's lessons file and evidence notes.
- `analysis/loopeval_analysis/` (shared): any reusable module, e.g. a multi-model forecast scorer.
- `runs/YYYY-MM-DD-myloop-*/`: experiment outputs, with the driving script beside them.

## What CamAPS FX does (verified 2026-10-25)

Sources: the CamAPS FX user manual (camdiab S3 `user_manual_fx_mmoll_commercial.pdf`) [M]; FDA 510(k)
decision summary K232603 [F]; CamDiab Summary of Safety and Performance APCam-FX-D47 RevL [S]; US
patent 8,062,249 (Wilinska, Hovorka et al., Cambridge Enterprise / Abbott; an early overnight
variant) [P]; Hovorka 2004 *Physiol Meas* 25:905, doi:10.1088/0967-3334/25/4/010 [H04].

| Claim | Status | Source |
|---|---|---|
| Adaptive MPC on a compartment model; body weight sets glucose and insulin distribution volumes; TDD is the *initial* indicator of insulin sensitivity, then refined from CGM, insulin and meals | published | M §10, F, H04 |
| Competing models that differ in SC insulin absorption/action rates (and carb absorption) run in parallel and are combined into the model that best explains recent CGM. A Kalman filter updates a glucose-flux term (model misspecification) and carb bioavailability | published for the early variant; current internals not public | P, H04 (Bayesian estimation) |
| Learns at three levels: daily insulin needs, diurnal pattern, post-meal needs. Overall learning takes 1–3 weeks | manufacturer statement; mechanism, forgetting factor and time constants **not published** | M, F, DRWF 2023 slides |
| Post-meal learning: if meal boluses are persistently too big or small, it changes post-meal delivery. "MealAssist" does not appear in any primary source found | manufacturer statement | mylife web |
| An overestimated TDD at initialization raises hypoglycaemia risk for 24–72 h, so the TDD prior is reweighted over ~1–3 days | regulatory record (field safety notice) | S |
| Cycle every 8–12 min, delivered as 15–60 min temp basals and/or extended boluses; the pump must allow ≥ 10 U per 5–15 min cycle | published | M §11, spec sheet |
| Maximum infusion rate is "determined on individual basis"; delivery is cut further when CGM is low or falling fast. The early variant capped at 2–5× programmed basal depending on SG and suspended at 77 mg/dL. The brief's "500–700 %" figure is unverified | published (form), unverified (numbers) | M §10, P |
| "Total daily insulin dose exceeded" stops Auto mode (Dana); TDD entry is capped since 2023 | published | F, S |
| Target: default 5.8 mmol/L (104–105 mg/dL), personal target 80–198 mg/dL in 30-min segments. The early variant aimed at 5.8–7.3 depending on prediction accuracy | published | M, F, Tauschmann 2018 |
| Boost assumes ~35 % higher TDD, target unchanged. Ease-off raises the target and makes sensitivity more cautious. Both: > 9 h of use raises TBR (Boost) or TAR (Ease-off) | published | PMC7617696, M |
| Carbs flagged as "hypoglycaemia treatment" are shown but never covered with insulin; "slowly absorbed meal" insulin is given over 3–4 h, gated on rising glucose | published | M §7 |
| CamAPS Liberty = fully closed loop, no meal bolus, ages 13+, not in pregnancy (CamAPS HX in the trials) | published | M, mylife |
| Real world, 8,604 users: TIR falls as the target rises; t<54 < 1 % at every target | published (retrospective) | doi:10.1177/15209156251376010 |

The marginal effect of CamAPS adaptation has never been isolated in a trial. The RCTs test the
whole system against pump + CGM (research report 02 §3.1).

## What LoopEval already has that overlaps

- **Daily-needs adaptation:** C43 outcome-keyed needs rule (static per window, 28-day lookback;
  promising, ICE check pending), C38 slow RC (6–24 h; NEUTRAL, wins only on two-sided beds), C14 autosens.
- **Diurnal learning:** C12 learned hourly needs, closed on every bed type (E54). C39 habit term NEUTRAL.
- **Learned forecast correction:** C19, closed on hands-off beds, reopened for announcers.
- **Model-misspecification term:** Loop's RC/IRC plays the role of CamAPS's Kalman glucose flux;
  dynamic carb absorption plays the role of carb bioavailability.
- **Hovorka physiology:** the additive plant is already a ReplayBG/Hovorka hybrid (EGP floor with
  insulin suppression, F01c brain uptake, renal loss). See `docs/additive/evidence/01-physiology-core.md`.

## Data

No CamAPS or myLoop user data exists in LoopEval (Pete, 2026-10-25). CamAPS behaviour cannot be
replayed or checked for fidelity. Every CamAPS idea is tested as a mechanism on Loop donors.

## Standing cautions

- **ISF is not identifiable in closed loop** (eda lesson 53). Ranking insulin-action models by fit
  on closed-loop data is the same problem. Check any learned parameter against natural experiments
  before you trust it.
- **Forecast-fit bar:** a learned forecaster has to clear about R² 0.7 on the exogenous part to
  help in closed loop (C19, O1; Lee 2024 TBME). Judge forecasts by closed-loop counterfactual,
  never by RMSE alone.
- **Learners that read TDD can be circular:** more insulin delivered raises TDD, which raises
  gain. Key learners to outcomes or residuals, not to delivered insulin alone.
- Modify the forecast, not the output (AGENTS.md). Most CamAPS ideas already work that way.

## Status

- 2026-10-25: role started; Pete approved the plan. First step: an offline forecast study of
  multi-model ranking (idea 1) with a bar fixed before the run, plus a count of carbs entered at or
  near a low (idea 4).
- Ideas in order: (1) multi-model forecast ranking with forgetting; (2) a daily-updated needs
  multiplier with forgetting (C43 made continuous); (3) per-person post-meal learning for
  announcers; (4) a rescue-carb flag; (5) a glucose-dependent cap on delivery rate. Not pursued:
  diurnal learning (C12 closed), gains keyed to weight or TDD, Boost / Ease-off, segmented targets, basal-modulating
  controllers (Pete 2026-10-29: Loop is phone-remote, a high temp runs on for 30 min after a disconnect; automatic
  boluses can shape the same delivery).
