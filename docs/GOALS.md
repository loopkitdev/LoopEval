# GOALS.md — what LoopEval is trying to find right now

Set 2026-08-24 (Pete). Supersedes any implicit direction in older run dirs.

## The goal

**Find algorithm-change candidates that improve outcomes when meals are unannounced.**

Improvement can come from either side of the dial:

- **knowing when to dose more aggressively** (an unannounced meal is under way and the
  forecast doesn't know it yet), and
- **knowing when to pull back** (a situation class where Loop reliably produces lows).

The second is not a consolation prize: fixing a *kind* of situation that produces too many
lows lets the user raise their insulin-needs setting safely, which buys TIR. A candidate
that removes lows at fixed TIR is therefore a TIR candidate too — score it with the dial
free to move (docs/FRONTIERS.md → Scoring: strict dominance in the operating band).

## Constraints on what counts

1. **Data-driven / learned strategies are allowed**, but every such candidate must report:
   - **data needed before it becomes effective** (days/weeks of history — sweep it);
   - **reliability of the tuning over time** (does a parameter fitted on month 1 still
     hold in month 3? drift across settings-eras?);
   - **hold-out evaluation**: fit on one period, score on a disjoint later period; never
     score on the fitting window;
   - **leakage audit**: an explicit statement of what information the mechanism used at
     each decision time and proof it is all ≤ that time (no future CGM, no future carbs,
     no end-of-window settings). `--oracle-*` modes are for bounding headroom only, never
     for a deployable candidate.
   - all of the above **across multiple patients**, not one.
2. **Breadth**: we want improvement across a variety of patients. But the **payoff is
   greatest for those starting with lower TIR and higher t<54** — weight the headline that
   way (bddp11 / bddp10 / bddp01 / bddp05 class before bddp07 / bddp06 class), and never
   accept a candidate that helps the easy donors by hurting the hard ones.
3. **Safety axis is non-negotiable**: TIR ↑ AND t<54 ↓ (t<70 when t<54 ≈ 0). A win on
   one that costs the other is not a win (AGENTS.md).
4. **Fidelity before frontier**: a candidate result on a donor whose deployment-faithful
   replay isn't validated is a hypothesis, not a result.

## How to evaluate (binding — see docs/FRONTIERS.md → Scoring for the full definition)

- Sweep reference and candidate on the **same dial** (`--candidate-insulin-needs`).
- Verdict = **dominance in the operating band** (validated multiplier ±0.1), with
  **block-bootstrap CIs**; the **multi-donor mean** is the only headline.
- For the *unannounced-meal* question specifically, run two regimes per donor:
  - **natural** — the donor's real announcement behaviour passes through (hands-off
    donors are already ~unannounced);
  - **announcement-suppressed** — `--no-carb-entries` (+ `--no-user-boluses` for fully
    automated) so announcers are scored as if they hadn't announced. This is also the
    burden axis for tight-control donors.
- Report the operating-point delta alongside lift ("what changes for THIS user as tuned").

## Where the history lives

Every candidate tried — including the ones that failed — is recorded in
**[docs/candidates/](candidates/README.md)**: one entry per mechanism, with the runs it
was tried in, the numbers, and the verdict. Add an entry *before* running a new
candidate (status `planned`), and update it when the numbers are in. A candidate that
isn't in the ledger didn't happen.
