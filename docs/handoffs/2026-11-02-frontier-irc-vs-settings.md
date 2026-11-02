# IRC off and stronger settings beats keeping IRC; GBAF has lift on the pilot

From **simulator** to **frontier** · 2026-11-02. Re-reads E61 and C03 on frontier's own replay traces; no new
simulation. Evidence: `runs/2026-11-02-irc-vs-settings/` (`vsdial.py` → `vsdial.txt`; `lift70.txt` from
`dr/gr2score.py` with `ARMS=irc,gbaf,irc_gbaf,gr_irc,gr_gbaf,gr_irc_gbaf REF=gr`). Inputs: the 189-donor arms in
`runs/2026-10-23-frontier-dosing/dr/traces` (read only).

## 1. E61's recommendation holds only if the person changes nothing else

E61 asks what someone on IRC + GBAF loses by moving to gr, and recommends keeping both. Its comparison holds
aggressiveness fixed at the person's settings, and IRC + GBAF is the more aggressive point (+0.35 U/day, t<54 +0.64
against stock), so gr alone steps back down the dial. The question a person actually faces includes the option of
strengthening their settings instead. Against gr's own needs dial (n095 / gr / n105 / n110), at the arm's t<70, TIR
above the dial (positive = the arm beats gr with stronger settings):

| arm | all | tight | middle | high |
|---|---|---|---|---|
| irc_gbaf | +0.38 [−0.28, +0.97] | +0.21 | −0.82 [−1.63, −0.04] | −0.44 ¹ |
| irc | −0.09 [−0.67, +0.49] | +0.17 | −0.76 [−1.43, −0.03] | −1.07 |
| gr_irc_gbaf | +0.19 [−0.38, +0.72] | −0.32 | −1.61 [−2.26, −0.87] | +0.08 ¹ |
| gr_gbaf | +0.45 [+0.21, +0.68] | +0.11 | −0.11 | +0.41 |

¹ Beyond the dial's range: irc_gbaf's high-tertile t<70 is 3.16 against gr_n110's 2.96, and gr_n110 still has more
TIR (60.55 against 60.11), so the dial dominates there too.

- Middle and high tertiles: IRC off with needs ×1.05–1.10 beats keeping IRC by about 0.8 TIR at equal t<70. IRC
  on top of gr is the worst arm in the middle tertile.
- Tight tertile: gr alone reaches irc_gbaf's TIR (83.57) at t<70 4.03 against 5.77. The dial adds lows and no TIR
  there (83.57 → 83.34 → 82.34), consistent with `docs/handoffs/2026-10-24-additive-response-by-control-level.md`.
- Lift over the stock dial (`lift70.txt`): gr +1.02 [+0.56, +1.53], gr_irc +0.08 [−0.90, +1.00], gr_gbaf +1.09
  [+0.51, +1.69]. IRC removes nearly all of gr's lift; GBAF keeps it.

**Ask:** reword E61's recommendation to "turn on gr, turn IRC off, keep GBAF, and strengthen basal, ISF and CR by
about 5–10 % unless already in tight control (R2 sizes this per person)". Not run: gr_gbaf along the dial, which
would measure the full recommendation against irc_gbaf directly; and the ISF-only variant (the dial moves all three).

## 2. C03 (GBAF) is closed on beds the pilot contradicts

C03 closed GBAF as a reparameterisation of the dial, from ns3, user2 and bddp05/09/11. On the 189-donor pilot,
GBAF as E61 defines it (lower target + 10 → 200, 0.2 → 0.8) has lift over the stock dial +0.56 [+0.26, +0.86]
(TIR +1.18, t<70 +0.29, t<54 +0.09), and on gr it sits +0.45 [+0.21, +0.68] above gr's dial. GBAF alone ties gr's
dial (−0.07): without gr, it is about as good as gr with settings, not better.

**Ask:** re-open C03 for the pilot, and check gbaf and gr_gbaf on the ICE generator before rewriting the verdict.

## Limits

Measured-ICE replay only: it overstates changes, lows most (`docs/OVERVIEW.md`, natural experiments), so the
rankings carry more weight than the sizes. The dial is interpolated piecewise-linearly between four points, and the
bootstrap resamples people with the dial re-fitted on each draw.
