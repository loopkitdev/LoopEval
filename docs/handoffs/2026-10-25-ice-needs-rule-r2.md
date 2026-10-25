# Request: score the outcome-keyed needs rule (C43, R2) on the ICE generator

From **frontier** to **ice**. At Pete's request. Evidence: `runs/2026-10-23-frontier-dosing/` — `hetero/needs_rules.md`
(the pre-registered rules), `hetero/rules.py` (replay scoring), `hetero/r2_multipliers.csv` (each donor's multiplier),
`dr/run.py` (`arm_flags`, the gr flags). Ledger entry: C43 in `docs/candidates/README.md`.

## Why

R2 picks a per-person insulin-needs multiplier, on top of guard + runway (gr), from the person's own CGM over the 28 days
before the window:

- ×1.10 if t<70 < 2 % and mean ≥ 160;
- else ×1.05 if t<70 < 4 % and mean ≥ 140;
- ×0.95 if t<70 ≥ 5 %;
- otherwise ×1.00.

On fixed-ICE replay (189 v32 pilot donors, 28 d) it gives +1.98 TIR [+1.59, +2.40] against gr, with t<54 +0.16
[+0.08, +0.24]. That fails the replay bar set before the run (Δt<54 ≤ +0.02), but it is about 1.2 TIR ahead of a
uniform needs change at the same t<54, and the tight tertile is flat on both axes. Replay's t<54 change is the axis
the 2026-10-21 three-tool comparison found about 10× too large on real edits; your generator was the only tool whose
hypo changes came out the right size. On the 25 real edits that match R1's raise branch, the field showed t<54 +0.12,
the generator predicted +0.14 and replay +0.68. The lows side of this verdict therefore rests on your tool.

## The ask

1. For every pilot donor in your checkpoint who is also in `r2_multipliers.csv`, run two arms over the same window and
   seeds:
   - **gr**: guard + runway at the frozen constants. Flags as in `dr/run.py`, which reads each donor's σ5 median from
     `SIG`:
     - `--candidate-sigma-band-k min(1, 6.7/σ5 median) --candidate-sigma-band-cob-gate`
     - `--candidate-postlow-rc-rise-scale 0.3 --candidate-postlow-window 720`
     - `--candidate-runway-fraction 0.7 --candidate-runway-cob-gate --candidate-runway-bg-min 150`
   - **gr_r2**: gr plus `--candidate-insulin-needs <needs>` from the CSV, on donors whose multiplier is not 1.00.
   - Use each donor's deployed controller config, as for any generator run: RC mode from `rc_mode.csv`, GBAF where
     deployed, and their strategy.
2. If the budget allows, add **gr_n105**: a uniform ×1.05 for everyone. It is the dial reference that the lift claim
   is measured against.
3. Report, against gr, paired and with a person bootstrap: ΔTIR, Δt<54, Δt<70, overall and by the `tertile` column in
   the CSV. Use both CGM and true glucose if your scorer has both.

What would change the verdict: Δt<54 overall above about +0.05, or tight-tertile t<70 rising. Either would mean the
rule needs its back-off branch tightened before it goes further.

Run it on gamepc. Reply as a new file here.
