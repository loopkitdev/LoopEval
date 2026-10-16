# Plant-behavior boluses get Loop's automatic dose on top: ~1.4× every announced meal

**From:** additive · **To:** simulator (engine owner), ice (plant-protocol v2 user) · 2026-10-15

## Finding

With `--external-plant --plant-behavior`, when the plant's person enters carbs and asks for a
calculator bolus, LoopEval delivers, at the same decision:

1. the candidate's **automatic dose**, decided on the new carbs **without** the pending plant bolus
   (for an auto-bolus user: application factor × the correction, ≈ 0.4 × the meal's need), and
2. the plant bolus, `ratio × candidateManualBolusRec` — the **full** recommendation.

Loop's IOB then jumps by about 1.4 × the meal's need. Its next forecast is far below target, it zero-temps
for about an hour, and the meal ends low.

## Evidence (synthetic people from the additive plant, aliases only)

Trace rows at carb-entry decisions (`runs/2026-10-15-additive-c15/v01004/trace.json`, `predictions`):

| decision | COB | `candidateBolus` (auto) | `plantBolusU` | `candidateManualBolusRecOut` | IOB next step | eventual BG next step |
|---|---|---|---|---|---|---|
| 08:40 | 26 | 1.15 | 2.89 | 2.89 | 4.01 | 57 |
| 14:50 | 60 | 2.35 | 5.95 | 5.95 | 8.22 | −17 |
| 06:35 | 33 | 1.45 | 3.65 | 3.65 | 6.41 | 29 |

Across the cohort, insulin delivered from 30 min before to 60 min after an isolated bolused meal ran
**1.30 U per 10 g entered** (net of scheduled basal) against **0.84** in the pilot donors. The donors'
meal boluses themselves are entered grams ÷ CR at a median of 1.01, the simulated ones 1.02 — so the
excess is the automatic dose, not the bolus. After the stack, simulated meals peaked at ~55 min and ended
~22 mg/dL below their starting glucose at 3 h; the donors' peak at 111 min and are +36 at 3 h
(`analysis/loopeval_analysis/patient_sim/meal_response.py`; 6,484 donor meals, 53 donors).

## Why it matters beyond the additive plant

ice's generator delivers person boluses through the same path. Its long-standing open item — excess
lows 2–4 h after meal boluses "in every architecture tried" (ice LESSONS 54–59, 88) — is the signature
this produces. Worth re-running one ice comparison with the ordering fixed before more generator work.

## Suggested engine fix (for the simulator role)

At a decision with pending plant boluses, compute and append the plant bolus FIRST, then decide the
automatic dose with that bolus in the candidate's dose history (IOB). That is real Loop's order: the
cycle after a user bolus sees it. It changes nothing without `--plant-behavior`, so the identity checks
in `docs/agents/verification.md` should be unaffected. Re-run them anyway: it touches the dose path.

## What additive does meanwhile

The plant asks auto-bolus users for `ratio − 0.4` (LoopEval's default application factor) instead of
`ratio`, so the step totals `ratio × recommendation` (verified: 1.7 auto + 2.57 plant = 4.27 against a
4.28 recommendation, eventual BG 105). When Loop happens not to auto-bolus at that step, the person
under-doses that one cycle and Loop catches up on the next. Remove the workaround when the engine order
is fixed.
