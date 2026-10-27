# LoopEval docs

Guides for the two main workflows and the simulator internals. Everything here renders on
GitHub — no build step, no server.

- **[Overview](OVERVIEW.md)** — start here:
  - the three simulation mechanisms (measured-ICE replay, the ICE generator, the additive
    simulator) and when to use each;
  - fidelity checks, and the natural experiments that test each simulator against real changes;
  - how a candidate change earns a verdict.
- **[Goals](GOALS.md)** — what the project is currently trying to find.
- **[Candidate ledger](candidates/README.md)** — every candidate tried, with runs, numbers and verdicts.
- **[Handoffs](handoffs/)** — findings one role passes to another (natural-experiment results among them).
- **[Simulator guide](simulator-guide/)** — how the closed-loop counterfactual simulator works:
  the substrate, the physiological counterfactual, the sensitivity-fidelity model, disruption
  handling, candidate levers, and scoring. The deep reference.
- **[Frontier experiments](FRONTIERS.md)** — *"does this change actually help?"* The lift method:
  sweep a candidate against the insulin-needs reference and score TIR vs t<54.
- **[Case studies](CASE_STUDIES.md)** — *"is the simulator (and the candidate) behaving
  correctly?"* Multi-panel plots of one window to root-cause a surprising outcome number.
- **[Loop algorithm classes](loop-algo-classes.md)** — deployed-Loop vs LoopAlgorithm-package
  behavior classes and the emulation flags that reproduce each.
- **[Verification](agents/verification.md)** — faithful replay, identity checks and the golden suite.
- **[Additive simulator](additive/MODEL_GUIDE.md)** — the component model, its match targets and known limits.
- **[External plant protocol](ice/plant-protocol-v2.md)** — how a patient model plugs into `simulate`.

## Local preview

These render on GitHub as-is. To preview locally (or share on your LAN) with the same GitHub
rendering — Mermaid diagrams, alerts, images — run:

```
python3 scripts/docserve.py        # http://localhost:8080/docs/  (+ the LAN URL it prints)
```

Stdlib only; Markdown is rendered in-browser via marked + mermaid from a CDN (the viewing
machine needs internet), everything else is served as static files.
