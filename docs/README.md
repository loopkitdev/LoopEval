# LoopEval docs

Guides for the two main workflows and the simulator internals. Everything here renders on
GitHub — no build step, no server.

- **[Simulator guide](simulator-guide/)** — how the closed-loop counterfactual simulator works:
  the substrate, the physiological counterfactual, the sensitivity-fidelity model, disruption
  handling, candidate levers, and scoring. The deep reference.
- **[Frontier experiments](FRONTIERS.md)** — *"does this change actually help?"* The lift method:
  sweep a candidate against the insulin-needs reference and score TIR vs t<54.
- **[Case studies](CASE_STUDIES.md)** — *"is the simulator (and the candidate) behaving
  correctly?"* Multi-panel plots of one window to root-cause a surprising outcome number.
- **[Loop algorithm classes](loop-algo-classes.md)** — deployed-Loop vs LoopAlgorithm-package
  behavior classes and the emulation flags that reproduce each.
