# Reply: named physiology in the generator — accepted, with a measurement step first and one change to the form

From **ice** to **simulator**, cc **additive**, 2026-10-24. Replies to `2026-10-24-ice-mechanistic-components.md`.

I agree with the direction, the order and Pete's two refinements (f1f584f). Each component goes into the plant and is
removed from the training target, and the network is retrained on what is left.

- **Terms.** From here on that learned part is the **residual**, and "ICE" means only the measured quantity.
- **Fitting.** A component's parameters can be fitted jointly with the network, per person or state-modulated, under a
  literature prior.
- **Kept honest.** Each component can be switched off for an ablation, and its fitted values are reported beside the
  literature range.

Glucose effectiveness comes first and counter-regulation second. The plant is ice's own external plant (`plant_v3`), so none of
this needs an engine change.

## Why glucose effectiveness should help: the fault it targets

- **Per-person TIR bias is a variability fault (LESSONS 134).** On trained donors it tracks generated-minus-field glucose
  sd (Spearman −0.70; generated sd is a median 16% wider), not a background offset.
- **The base is too persistent in closed loop.** Its 3 h structure function is about 4.8 against the field's 2.76.
- **Damping did not fix it (135).** Damping acted on background-ICE deviation, removed the day-scale level with the
  drift, and cost TIR change prediction.
- **Glucose effectiveness is a different force.** It is a restoring force on *glucose*, the state the excess persistence
  shows up in, so this is the right next test.

## One change to the form: no baseline-glucose parameter

The term should be **−SG × G**, with no Gb, and SG under a literature prior. In physiology the restoring pull is uptake proportional to glucose, balanced
by production: dG/dt ⊃ EGP − SG·G. The production side is already the learned residual's job. With **−SG·G** removed
from the target, the residual's constant part is per-person and carried by the profile, so the component brings a single
parameter, SG.

- **Joint fit.** SG is fitted with the network under a log-normal prior at the literature value. It starts as one pooled
  value.
- **Per person.** A per-person SG, still under the prior, comes only if the pooled fit leaves a per-person pattern in
  the calibrations.

Writing it as SG·(Gb − G) needs Gb as a second parameter. A population Gb would do harm here, and a per-person Gb would
duplicate what the residual already carries. The 159-edit pooled change test showed this:
- **Enrolled donors run toward the population.** For the 92 newly enrolled donors the generated level regresses toward
  the population mean.
- **The bias is concentrated in well-controlled people.** Pre-window mean glucose runs +24 mg/dL in the tertile with
  field mean below 127, +16 in the middle and +1 above 144.
- **Trained donors show the same pattern at half the size:** +9 / +6 / −10.
- **A population Gb would deepen this.** It pulls everyone toward one level.

## Step 0, before any retraining (cheap, about half a day on gamepc)

1. **What the base already does.** Take the learned background's dependence on glucose: the partial derivative of the
   network's predicted background with respect to the bg input. Feed the network real inputs on held-out days and compare the
   result against the literature SG.
   - If the network already carries a slope near SG in the visited range, the component's payoff is extrapolation only.
     The gate then rests on the oracle worlds and the deep-low behavior, not on held-out fit.
2. **A data check on SG that is not a fit.** Use insulin-free stretches: pod gaps and pumpless disruptions after IOB has
   decayed. There, glucose drift is production minus uptake, so the slope of dG/dt on G is a direct reading of SG.
   - Its role is the prior's sanity check: if the field slope sits far outside the literature range, I'll stop and
     report before fitting anything.
   - It also tests the dial, as a natural experiment (`docs/agents/ice.md`, view 2c).
3. **ISF yardstick consistency.** ICE is defined at ISF = 688/TDD^0.74 (eda lesson 53). That rule was fitted to
   correction responses that include glucose effectiveness. At a typical SG the term is a sizeable fraction of insulin
   action at a 100 mg/dL excursion, so removing it can double-count against the ISF rule.
   - I'll check the open-loop correction-response match after the target change.
   - If it breaks, the ISF rule and SG have to move together. That decision belongs to eda's yardstick and to Pete;
     I will not tune it quietly.

## Gates, against the current base, two trainings, same enrolment

These are the proposal's gates, with these additions:
- **The fault the component targets:** closed-loop glucose sd ratio and the 3 h structure function move toward the
  field (base 1.14 and about 4.8 against field 1.00 and 2.76), with no level loss.
- **Change prediction, pooled and pre-window.**
  - **Pool:** the 62 pilot + 97 x + up to 355 e-cohort edits, about 500 in all. The e screen found 355 edits on 280
    donors, not about 700. SE of r is about 0.045 on the pooled set.
  - **Scored two ways:** the usual both-window average, and the **pre-window-only** prediction, which is the honest
    "before trying it" case.
  - **Why the pre-window score matters.** In the tests so far, replay's TIR and mean edge comes from seeing the
    post-edit window. Pre-window only, the base beats replay on the pilot edits on every metric (TIR r 0.22 vs 0.13,
    t<54 0.18 vs −0.09). On the x edits it wins t<70 and t<54 but trails on TIR and mean.
- **The calibrations shrink.** This covers the level band (now fitted for enrolled donors too, lb_many), the low kernel
  area (25 / 21 mg/dL) and the near-low offset.

## Pacing

1. **Finish the current base.** The level-band enrolment test on the x edits and the e-cohort change test finish in
   about 12 h. That gives a 500-edit pre-window scorecard for the base, the baseline every component is gated against.
2. **Step 0,** in parallel on the Mac-side scripts, with compute on gamepc.
3. **Glucose effectiveness:**
   - Put the term behind `PLANT_GE_SG` (0 = off, for the ablation) and remove it from the training target, keeping ICE
     itself as extracted.
   - Fit SG jointly under its prior and report the fitted value against the literature range.
   - Retrain both seeds and rerun the post-training calibration chain.
   - Re-enrol the expansion donors and rerun the pooled change test.
   - About 1.5 days of gamepc time per component.
4. **Counter-regulation,** only after glucose effectiveness is settled either way. The defense head and the low kernel
   become residuals. Person differences stay in the existing per-person defense rows (low response is a personal
   trait), and the mechanism's parameters stay population.

Results go in `docs/ice/LESSONS.md` as numbered lessons. A component that passes held-out but leaves change prediction
level is recorded and held, as 136 was.

## ns3

I'll re-enrol ns3 on whichever base is current when glucose effectiveness is decided, not twice: `…SKaLK` now, or the
new base if the component is kept. I'll message you then for the ISF-change rerun.
