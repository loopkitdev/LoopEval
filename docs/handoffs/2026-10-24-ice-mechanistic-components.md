# Proposal: move named physiology into the generator, one component at a time

From **simulator** to **ice**, cc **additive**, 2026-10-24. Pete approved the direction and wants it taken slowly and
iteratively. The additive simulator continues as it is; this changes nothing there.

## Why

The generator is already a hybrid. Glucose moves by `(ICE − ISF × insulin activity) × dt`:
- **Fixed:** insulin action (Loop's curve, ISF from TDD) and meal pulses.
- **Learned:** background ICE, the defense head and behavior.
- **Fitted after training, on closed-loop runs:** level offsets, glucose-band offsets, the meal kernel, the low and high
  kernels, the near-low offset, the spread shrink and compression.

The forces that pull glucose back toward baseline are glucose effectiveness, counter-regulation and recovery from lows.
All of them sit on the learned or post-hoc side. We read the per-person level offsets and the excess closed-loop
persistence (LESSONS 132, 135) as signs that those forces come out slightly wrong in closed loop. A learned model also
interpolates, and the change a candidate causes often lands in states the data rarely visited, such as deeper and
longer lows. A mechanism with evidenced parameters should extrapolate there better.

## How this differs from LESSONS 135 and 136

Damping (135) and the low-response kernel (136) were each added on top of a trained network. Neither was retrained. Here
each component goes into the plant **and** the training target: the network is retrained on ICE with the component's
modeled contribution removed. If it isn't retrained, the network still carries the effect and it gets counted twice. If
the component's parameters are fitted freely to the same data, the network and the component trade the effect between
them, and the split means nothing. So parameters come from evidence, not from a free fit. Additive's component
library, with its literature sources, is the place to take them from.

## Suggested order

1. **Glucose effectiveness** (insulin-independent uptake toward a baseline level). It is the simplest restoring force,
   and the research oracle worlds already showed it removes replay's +10 mg/dL bias in low response.
2. **Counter-regulation onset and gain below a threshold.** The generator's defense head would become a residual on top.
3. Later, and only if 1–2 pay off: ISF nonlinearity, and sensor lag and noise.

## Gates for keeping a component

Every gate is measured against the current base, with both trainings and the same enrolment procedure:
- the held-out acceptance levels in `docs/agents/ice.md`, with no regression on the worst donor;
- change prediction on the e-cohort edits (`runs/2026-10-23-ice-edit-pool/`) once they are exported. At about 700 edits
  the standard error of r is about 0.04, against 0.12 on the 62-edit test (LESSONS 133);
- the per-person calibrations shrink: level offsets, level bands and the low kernel move toward zero. That is the sign
  the component explains what they were covering. It also makes enrolling new donors cheaper;
- research's oracle worlds where available, for the extrapolation into deeper lows.

A component that passes the held-out check but leaves change prediction level is recorded and held, as 136 was.

## Side note

The ns3 enrolment and my ns3 ISF-change run used the SKa base. The base has since moved to `…SKaLK` (LESSONS 136). If ns3
is re-enrolled on the newer base, I will rerun the change (`runs/2026-10-23-ns3-gen-isf/`).
