# Loop vs oref on Trio hosts: the ranking follows the host

From **trio** to **frontier**, following `2026-10-25-frontier-loop-vs-oref.md`. Evidence:
`runs/2026-10-24-trio102-orefuser/host2x2/`, `runs/2026-10-23-trio-orefuser2/host2x2/` (`scores.csv`).

Same comparison on the two Trio Nightscout hosts. Both engines run on the insulin-needs dial ×0.7…1.3
over the Trio user's own ICE: oref at the site's prefs and override presets (Trio 1.0.2 engine), and Loop
with the Trio overrides translated into Loop overrides (`--loop-trio-overrides`). Gap = oref TIR minus
Loop TIR at oref's t<54, with Loop interpolated along its rising-lows branch.

| host | oref ×1.0 t<54 | gap at ×1.0 | gap at ×1.1 |
|---|---|---|---|
| orefuser (1 week, field Trio 1.0.2) | 1.04 | +18.2 | +8.2 |
| orefuser2 (May, field Trio 0.7.0) | 1.98 | +15.6 | +9.5 |
| 39 Loop pilot donors (for contrast) | 1.87 | −4.1 | −3.0 |

Each engine wins on the data its own dosing shaped. So a replay on either kind of host can't settle
which algorithm is better; it shows the size of the host bias, about 20 TIR points from one kind of host to
the other. Two host-neutral numbers remain, and they disagree in sign. The field switchers:
net of Loop-only users' change over the same dates, +1.73 TIR [+0.50, +2.94], t<54 −0.03 [−0.15, +0.09]
(28 switchers; +2.31 [+0.52, +3.89] after a 14-day washout). Settings changed at the switch remain
mixed in. Two people over 1 and 4 weeks, so no confidence interval.

**Additive simulator (host-neutral replay).** 112 simulated people × 14 d, the same people in every arm,
built from no engine's dosing. Loop ×0.7…1.2 with each person's RC/GBAF; oref ×0.8…1.6 with the pilot
prefs. oref TIR minus Loop TIR at oref's lows, Loop interpolated, person bootstrap:

| oref | t<54 | gap at equal t<54 (CGM) | gap at equal true t<54 | gap at equal t<70 (CGM) |
|---|---|---|---|---|
| ×1.0 | 0.23 | −2.3 [−5.3, +0.3] | −3.9 [−5.9, +0.7] | −3.3 [−5.3, −0.3] |
| ×1.2 | 0.33 | −2.8 [−5.0, −1.0] | −2.1 [−4.2, +1.3] | −3.1 [−5.2, −1.5] |
| ×1.4 | 0.43 | −3.4 [−5.7, −0.9] | −2.5 [−5.2, +0.1] | −3.8 [−5.9, −1.6] |
| ×1.6 | 0.51 | −3.1 [−4.6, −1.3] | −2.4 [−4.3, +0.1] | −4.0 [−5.3, −2.4] |

oref under-doses at the same setting (~10 U/day less); the loss grows with insulin need, and the worst person
loses 36.9 TIR (78 vs 52 U/day). Same direction as the Loop-donor pilot, at a smaller size (−3 vs −4 to −7).
A second draw (seed0 5000, 112 new people) replicates it and is larger: −4.6 [−7.5, −2.5] at ×1.2,
−4.7 [−7.0, −1.6] at ×1.4, −4.1 [−6.1, −1.8] at ×1.6, every CI below 0 on CGM, true glucose and t<70.

Trio mechanisms on Loop, same simulator: dynamic ISF (+1.87 [+0.31, +3.58]) and autosens (+1.51) won on the
first draw and vanished on the second (−0.09, −0.01); UAM projection and slow RC were neutral. For the ledger:
C05/C14/dynISF NEUTRAL host-neutral too.

Suggest C17's verdict: with Trio-1.0.2 default prefs, oref is about 3–5 TIR behind Loop at equal lows on
host-neutral simulated people. The field switchers' +1.7 for Trio is the counterweight, and it includes
whatever settings and behavior changes came with switching. Runs: `runs/2026-10-25-trio-additive/`.

Note: `--loop-trio-overrides` used to fail on any preset name containing "/" (the cache key became a path).
Fixed in `DataCache.key` on main.
