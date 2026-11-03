# Slow RC's lift is mostly a settings correction; on gr2 it adds about +0.2 once settings are tailored

From **simulator** to **frontier** · 2026-11-03. Replay matrix: slow RC (`s24g05`) × {stock, IRC, GBAF, gr, gr2}
× the needs dial, on your dr harness. Evidence: `runs/2026-11-02-src-matrix/` (`score.py` → `score.txt`). Inputs:
the 189 donors in `runs/2026-10-23-frontier-dosing/dr/traces`, read only, plus 22 new arms run with a copy of
`run.py`. The gr2 arms use `loop-eval-gr2b`, which reproduces your `gr_Ws_Wgo_Wd20` trace exactly.

## The result

TIR above the stock dial at equal t<70, piecewise along the dial (n095 / base / n105 / n110). The tailored column
scores each control tertile (by stock mean glucose, 63 donors each) against that tertile's own dial, then averages
the three.

| arm | one dial for all | tailored | slow RC over own family's dial (one dial → tailored) | t<54 vs stock |
|---|---|---|---|---|
| slow RC | +1.47 [+1.11, +1.83] | +0.39 | | +0.22 |
| GBAF | +0.81 [+0.53, +1.08] | +0.45 | | +0.09 |
| IRC | +0.64 [+0.05, +1.19] | −0.24 | | +0.38 |
| gr | +1.22 [+0.63, +1.82] | +0.86 | | −0.02 |
| gr + slow RC | +1.95 [+1.36, +2.56] | +0.66 | +1.10 → +0.22 | +0.19 |
| gr + GBAF | +1.33 [+0.84, +1.84] | +0.75 | | +0.09 |
| gr2 | +1.53 [+0.93, +2.23] | +1.18 | | −0.05 |
| gr2 + slow RC | +1.99 [+1.34, +2.58] | +0.69 | +1.02 → +0.16 | +0.19 |
| gr2 + GBAF | +1.47 [+0.95, +2.01] | +0.93 | | +0.09 |
| gr2 + GBAF + slow RC | +1.67 [+0.96, +2.34] | +0.32 ¹ | +0.56 → +0.19 ¹ | +0.45 |

¹ The high tertile lies beyond its dial's last point; the last segment is extended.

- **The pooled number overstates slow RC.** Slow RC's pooled lift (+1.47) is above its lift in every tertile (tight
  +0.20 [+0.10, +0.30], middle +0.35, high +0.62). That pattern means it is moving each tertile toward that
  tertile's own best setting, which one shared dial cannot do. Against tailored settings it keeps about +0.4 on
  stock and about +0.2 on gr or gr2.
- **On gr2, slow RC adds little.** The increment over gr2's dial is +0.13 / +0.01 / +0.35 by tertile, at t<54
  +0.19 and +0.16 U/day. Adding slow RC or GBAF lowers gr2's tailored lift.
- **gr2 is the strongest arm:** +1.18 against tailored settings, +2.72 in the high tertile, with no rise in lows.
- **IRC loses in the middle tertile in every family** (−0.9 to −2.0). Stacking IRC, GBAF and slow RC raises t<54 by
  1.2–1.3.

## Ask

Check these on the ICE generator, scored per control tertile against each tertile's own needs dial as well as
pooled: gr2, gr2 + slow RC, gr2 + GBAF, gr + slow RC and slow RC alone, each with n095 / n105 / n110. The existing
generator figures for slow RC and gr2 are pooled, so they can carry the same between-tertile effect. If the
generator agrees, slow RC is best described as an automatic settings correction for people whose settings are off,
not an addition to gr2.

## Limits

Measured-ICE replay overstates changes, lows most, so the ranking carries more weight than the sizes. Tertile
dials have four points; bootstrap resamples people with the dial re-fitted on each draw.
