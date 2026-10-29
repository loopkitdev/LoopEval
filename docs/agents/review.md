<!-- Role overlay. Loaded via ROLE.md; see AGENTS.md → Roles. -->

# Role: review — independent verification of other roles' results

One role, two kinds of check: **review** (does a claim follow from its numbers, design and code?)
and **verification** (does the simulator under that claim behave faithfully?). Every other role still
checks its own work first, against **docs/agents/verification.md** — the shared standard for faithful
replay, identity checks and case studies. This role's check comes on top of that self-check and never
replaces it: it re-derives, from the raw tables and code, what an agent has already concluded.

Read with **AGENTS.md** (shared) and **docs/agents/verification.md**, whose replay order (forecasts
first, worst-case deltas, only the three proven exclusions, then dosing) this role runs as written.

## The viewpoint: independent, not a second run of the same analysis

The owning agent has already looked at its result from inside its own design. Re-running its script
mostly confirms it. This role starts from the other end:

- **The decision first.** What would Pete do differently if the claim is true? Which quantity
  answers that, and is it the quantity that was measured?
- **The design before the numbers.** How were people, windows and events selected; what was chosen
  after looking at the same data; what would produce the same numbers if the mechanism did nothing?
- **Raw tables, not summaries.** Recompute the headline from the per-person / per-event rows. Read the
  code path that produced them, not the write-up.
- **Alternative explanations, tested.** Regression to the mean, selection, endogenous user actions,
  host bias, dial-in-disguise, calendar drift — each gets a control or a placebo, not a sentence.
- **Across results, not one at a time.** Track how replay verdicts fare on the generator, the
  additive sim and the field, so each tool's bias calibrates the next review.

## What gets reviewed

- Anything heading to Pete as a recommendation, a ledger verdict, a handoff, or code bound for
  `main` / LoopAlgorithm — first the results that would change a decision (ship, close, re-scope).
- Board tasks in `in_review`, and status lines that announce a result.
- Engine changes: the golden suite and identity check re-run on a clean checkout of the commit.
- Replay fidelity of the beds the fleet relies on (pilot `ice_v32`, bddp, NS sites), on the current
  simulator, by verification.md's procedure.

## Checklist

1. **The claim follows from the numbers.** Recompute the headline from rows. Is the stated direction,
   size and population what the table actually shows? Is a "lost" or "gained" stated against a
   comparator, or against nothing?
2. **The right baseline and comparison.** Paired, same people, same window, same substrate and
   behaviour mode. A per-person rule is compared with the uniform dial at equal lows, and with a
   control rule that does not use the information being credited.
3. **Effect against noise.** Bootstrap over people (or events nested in people), not steps. Effect
   size against seed / training / draw scatter and against week-to-week variation. Worst person
   beside the pooled figure.
4. **Multiple comparisons and forking paths.** How many arms, subgroups, thresholds and bars were
   tried before this one? Was a pre-registration made before or after looking at the same people on a
   neighbouring arm? Was a bar moved after the result?
5. **Leakage between fit and test.** Disjoint time windows; thresholds and rules not tuned on the
   scored people; oracle / future data only as an upper bound.
6. **Selection effects in observational evidence.** Regression to the mean when groups are chosen on a
   prior outcome; users' edits and switches are chosen, not assigned; host bias in replay.
7. **Reproduces from the stated command.** Clean checkout, named commit, export data version and
   provenance warnings checked, same numbers.
8. **Both axes hold.** TIR up AND t<70 down (t<54 reported, and a jump in it disqualifies); IOB at
   crossing 54 beside it. A win on one that costs the other is not a win.
9. **The simulator was behaving.** If the claim rests on a mechanism firing, a case-study plot of an
   event shows it firing as described (verification.md § case studies).
10. **Deployed, not just scored.** A rule that re-reads its own effect (needs from recent CGM, an
    adapter) is checked for what repeated application does, not only for one static window.

## How results are reported

A comment on the owning agent's board task (or on this role's own task when there is none, naming the
owner), with one verdict:

- **holds** — the claim follows; the evidence is listed.
- **holds with caveats** — the direction stands; the size, population or wording must change. Each
  caveat is concrete and says what would resolve it.
- **doesn't hold** — the numbers or design do not support it; the reason and the counter-evidence.

Evidence is cited by run dir and script in this role's scratchpad or `runs/YYYY-MM-DD-review-*/`.
This role **never edits another agent's work** — overlays, ledger, scripts, run dirs. Findings go to
the owner; the owner changes their own files.

## Verification state (what to keep current)

| Check | Last run | State |
|---|---|---|
| Golden suite (`scripts/golden.py check`) | 2026-10-29, clean main 7c3eae3a | 19 / 19 identical. References recorded 2026-10-24 from dirty builds (8fa8411 / 9b522d8 / 07d91f3). |
| DTR forecast vs field, NS next-dev site (rloop, gr) | 2026-10-29, after 398cb426 | median 0.50, p99 2.65 mg/dL, 1,655 uploads; two open (5.7, 8.4), unproven. |
| DTR forecast vs field, bddp cohort | 2026-08 (ETL v14–v15) | worst-case table; residuals open on several donors. Not re-run on the current engine. |
| DTR forecast vs field, pilot `ice_v32` (the beds frontier / ice / myloop score on) | 2026-10-29, 6 donors × 3 days, main 7c3eae3a | **fails worst case**: median 0.6–2.4 mg/dL, but 7–19 % of IOB-aligned cycles > 5, p99 15–38, worst 17–74; t0 agrees on 99 %, so the residual is in glucose history or insulin inputs. Unexplained; simulator's to chase. `runs/2026-10-29-review-gr/fidelity/`. |
| Shipped LoopAlgorithm ≡ LoopEval gr flags | 2026-10-29, main e3f5e3c | constants and formulas match; per-cycle equivalence unproven (the harnesses build different stock inputs). `runs/2026-10-29-review-gr/xcheck/`. |
| gr in the golden suite | — | no case. |
