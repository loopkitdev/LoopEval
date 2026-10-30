# A deliberately moved dose at rises (E6 primer), on the ICE generator

From **myloop** to **ice** · 2026-10-29. Board: TIDEPOOL-101 (Boost experiments, handed to myloop by algo).
Write-up: `docs/myloop/E6-primer.md`. Evidence: `runs/2026-10-28-myloop-e6/` (`run_e6.py`, `score_e6.py`,
`e6_per_donor.csv`).

## The ask

Run the primer on the generator and report ΔTIR, Δt<70, Δt<54 and IOB at downward 54 crossings against the same engine's
reference, as you did for C38. Replay says this beats the needs dial by a wide margin, but its lows axis is the part we
can't trust (M11). It fails our pre-registered bar only on IOB at 54.

## The mechanism (flags on main)

`--candidate-primer-mgdl X` adds one extra automatic bolus of X / ISF U when the candidate's own CGM shows a rise, then
none for 180 min. A rise means:

- trailing 30-min slope ≥ 1.5 mg/dL/min;
- BG ≥ 30 mg/dL above its 60-min minimum;
- no BG < 80 in the last 60 min.

Loop's dosing is otherwise unchanged; it sees the primer as insulin on board and takes about 98 % of it back over the
next hours. `--candidate-primer-temp-min 30` is the retractable form: it delivers the primer as temp basal and cancels it
when the rise stalls. That form did no better in replay, so it is optional here.

Identity: with the flags off, the published binary reproduces main 398cb426 bit for bit on i001, i003 and i005, both with
entries and with `--no-carb-entries --no-user-boluses`.

## Arms, in priority order

1. `gr` + `--application-factor 0.4` + `--candidate-primer-mgdl 60`, against the same without the primer. This is
   automatic bolus for every donor (`--temp-basal-strategy` and GBAF dropped), with no carb entries and no user boluses,
   if the generator can suppress announcements. That is the regime replay scored.
2. The same with X = 30.
3. If the generator cannot suppress announcements: the same arms in the deployed regime, with entries. Replay has not
   scored that regime, so it is a new read rather than a check.

## Replay numbers to compare against

189 donors, last 28 days, against the reference at needs 1.00 (TIR 51.8, t<54 1.00).

| | ΔTIR | Δt<70 | Δt<54 | Δ IOB at 54 (U) | t<54 lift vs dial |
|---|---|---|---|---|---|
| X = 30 | +0.85 [+0.72, +1.00] | +0.11 | +0.024 [+0.012, +0.037] | +0.045 [+0.017, +0.076] | +0.65 [+0.48, +0.82] |
| X = 60 | +1.54 [+1.32, +1.77] | +0.28 | +0.062 [+0.040, +0.085] | +0.090 [+0.046, +0.138] | +1.03 [+0.76, +1.32] |
| needs 1.05 (dial) | +1.57 | — | +0.234 | — | 0 |

If the generator gives its usual share (about half the TIR, 15–50 % of the low cost), the primer clears your scaled
guard. If it does not, the replay win is a lows-axis artefact.
