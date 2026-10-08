<!-- Role overlay. Loaded via ROLE.md; see AGENTS.md → Roles. -->

# Role: research

Literature research. Compare how blood-glucose (AID) control algorithms are developed, evaluated and optimized in the published and community literature with LoopEval's own work, and propose new research paths.

This role reads the other roles' output but does not change it. Candidate mechanisms belong to **frontier**, the engine to **simulator**, and observational findings to **eda**. A path proposed here becomes work only when the owning role takes it up.

## Where the work lives

- **`docs/research/LITERATURE_REVIEW.md`** is the deliverable. It places LoopEval against four bodies of literature: simulators, evaluation, algorithm design, and unannounced meals. §5 A–H gives prioritized new paths.
- **`docs/research/agent-reports/`** holds the full reports from the 2026-10-08 sweep that the review was built from:

  | File | Subject |
  |---|---|
  | `00` | Our work, summarized from the repo |
  | `01` | Simulators and replay |
  | `02` | Algorithm design and tuning |
  | `03` | Unannounced meals and fully closed loop (FCL) |
  | `04` | Metrics and counterfactual evaluation |
  | `05` | DIY Loop and oref practice |

  Each report has its own citation list. Anything tagged [unverified] has not been checked against its source.
- **`docs/research/sources/fda/`** holds text extracted from three FDA decision summaries: K203689 (Tidepool Loop), K234055 (DEKA Loop), and DEN190034 (the Control-IQ iAGC De Novo).

## What to read in the other roles

- **frontier:** `docs/candidates/README.md` (the ledger), `docs/GOALS.md`, `docs/FRONTIERS.md`. The current ledger lives on the `algo` branch (`~/dev/loopeval-algo`).
- **simulator:** `docs/simulator-guide/README.md`, `docs/loop-algo-classes.md`.
- **eda:** `docs/agents/eda.md` on the `eda` branch (`~/dev/loopeval-eda`).
- **Shared:** the working memory at `~/.claude/projects/-Users-pete-dev-LoopEval/memory/MEMORY.md`.

## Status (2026-10-08)

- The review is drafted. Pete has not reviewed it and it is not published.
- Two corrections are already folded into the review (§6):
  - Report 05 calls LoopEval dose-only. It also simulates counterfactual glucose.
  - Report 01 calls the counter-regulation term "a hard 54 floor". It is a gated defense-velocity term.
- Two key citations have been spot-verified: Vettoretti 2016 (doi:10.1089/dia.2016.0148) and Lee et al. 2024 TBME (doi:10.1109/TBME.2024.3424665). Other citations marked † should be checked before external use.

## Conventions

- Label every claim as measured, published, or hypothesized.
- Give a DOI or URL for every literature claim.
- Never cite an [unverified] item externally without checking it first.
- Refer to donors only by alias (bddp01–11, ns3, user1, user2). No Nightscout URLs, tokens or other PHI in `docs/research/`.
