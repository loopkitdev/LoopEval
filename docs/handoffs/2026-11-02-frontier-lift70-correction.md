# Correction: lift70's straight-line dial understates lift for arms that add insulin

From **simulator** to **frontier** · 2026-11-02. Corrects the lift figures in
`2026-11-02-frontier-irc-vs-settings.md`. Evidence: `runs/2026-11-02-irc-vs-settings/` (`piecewise.py` →
`piecewise.txt`). Inputs: the same 189-donor traces in `runs/2026-10-23-frontier-dosing/dr/traces` (read only).

## What is wrong

`dr/gr2score.py` scores lift70 as ΔTIR − slope · Δt<70, where the slope is a straight line fitted through the stock
dial's points (n095 / base / n105). The dial is concave. Per point of t<70 it gains about 3.9 TIR below ×1.00 and
about 1.3 above, against the fitted line's 2.2. An arm with more lows than stock is charged about 2.2 TIR per point
of t<70 when the dial itself only gains about 1.3 there. Arms that add insulin are under-scored and arms that pull
back are over-scored. Reading the dial piecewise between its points removes the bias.

| arm | lift70 (straight line) | piecewise |
|---|---|---|
| gr | +1.02 [+0.57, +1.51] | +1.22 [+0.63, +1.85] |
| irc | −0.46 [−1.25, +0.29] | +0.64 [−0.01, +1.25] |
| gbaf | +0.56 [+0.26, +0.86] | +0.81 [+0.56, +1.05] |
| irc_gbaf | −0.89 [−2.03, +0.11] | +0.70 [−0.13, +1.42] ¹ |
| gr_irc | +0.08 [−0.98, +0.98] | +1.00 [+0.19, +1.73] |
| gr_gbaf | +1.09 [+0.48, +1.63] | +1.33 [+0.84, +1.83] |
| gr_irc_gbaf | −1.00 [−2.34, +0.12] | +0.55 [−0.36, +1.47] ¹ |
| s24g05 | +0.78 [+0.30, +1.24] | +1.47 [+1.09, +1.84] |
| gr_s24g05 | +1.42 [+0.70, +2.08] | +1.95 [+1.33, +2.53] |

Dial points (t<70, TIR): n095 (1.88, 66.00), base (2.74, 69.36), n105 (4.18, 71.19). Person bootstrap 1000, with
the dial re-fitted on each draw.

¹ Beyond n105's t<70 (4.18): the last segment is extended. A stock n110 arm is running
(`runs/2026-11-02-src-matrix/`) and will replace the extension.

## What changes in the earlier handoff

- **Withdrawn:** "IRC removes nearly all of gr's lift." On the piecewise dial, gr_irc keeps most of it (+1.00
  against gr's +1.22).
- **Withdrawn:** IRC and IRC + GBAF score negative. On their own they sit at or above the stock dial: irc +0.64,
  irc_gbaf +0.70 ¹.
- **Revised:** GBAF's lift over the stock dial is +0.81 [+0.56, +1.05], not +0.56. The ask to re-open C03 stands.
- **Unchanged:** the E61 table in section 1 and the advice drawn from it. Those already read gr's own dial piecewise,
  and the advice is unchanged: turn IRC off, keep GBAF, and strengthen settings 5–10 % outside the tight tertile.

**Ask:** score E61 (and any wording that quotes these lifts) piecewise before it goes into the ledger, and check
which other ledger rows were scored with lift70's straight line. `analysis/loopeval_analysis/frontier.lift` already
interpolates along the dial in multiplier order.
