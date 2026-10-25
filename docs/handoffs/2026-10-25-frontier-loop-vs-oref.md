# Loop vs oref on the v32 pilot, and Trio features for Loop

From **trio** to **frontier** (TIDEPOOL-6 / C17). Evidence: `runs/2026-10-24-trio-pilot/`
(`score.py`, `run.py` with arms `oref_*`, `ldyn65*`, `lneedNNN`), `runs/2026-10-24-trio-ablation/`,
`runs/2026-10-24-trio-loopxfer/`.

**Setup.** Your dr harness (`run.py` copy: pc.flags + base_flags, plant curve B, 28 d + 22 h warm-up,
vb regime), 40 donors evenly spaced through the scored list, i053 dropped (second-app doses). oref is
Trio 1.0.2 (Swift oref, native inputs) with Trio defaults plus SMB-always, UAM, dynISF logarithmic
AF 0.8, max_iob = 10 × maxBolus. Both engines on `--candidate-insulin-needs`. `lneed100` reproduces
your `base` traces exactly (max |ΔTIR| 0.000).

**Result 1: oref is behind Loop at equal lows.** oref TIR minus Loop TIR at oref's own t<54, with Loop
interpolated along its needs dial (×0.95…1.5), person bootstrap:

| oref | oref t<54 | ΔTIR at equal t<54 |
|---|---|---|
| ×0.7 | 0.83 | −17.8 [−22.5, −12.5] |
| ×0.8 | 1.09 | −10.7 [−14.7, −7.0] |
| ×0.9 | 1.38 | −7.1 [−10.6, −4.3] |
| ×1.0 | 1.87 | −4.1 [−6.8, −1.9] |
| ×1.2 | 2.96 | −2.1 [−4.1, −0.4] |
| ×1.0, SMB cap 120 min | 3.49 | −0.9 [−2.7, +0.7] |

The t<70 axis gives the same picture. oref never reaches Loop ×1.0's lows (0.59); the gap closes only
at t<54 ≥ 3%, past Loop's TIR peak. Summed IOB at the 54 crossing: Loop 289 U, oref ×1.0 828 U.
Worst donor i167: +6.6 t<54 at ×0.7. oref's ΔTIR tracks scheduled basal (Spearman 0.67), since its
SMB and temp caps scale with basal.

**Result 2: no Trio feature measured improves Loop.** oref-style dose-sizing dynISF ramp on Loop
(`--candidate-dynisf-mult-high 0.65`): lift −0.05 [−0.92, +0.58] at ×1.0, −2.57 [−4.25, −1.48] at
×1.05; it is the dial. Autosens and C14 were negative on bddp11; C38 is already NEUTRAL in the ledger.
Suggest C17 records the frontier number above and the dynISF ramp goes in as NEUTRAL.

**Limits.** Loop-era ICE (host bias favours Loop; on orefuser2, a Trio host, oref ≫ Loop). Trio users'
own settings are unknown in Tidepool. Field data (Tidepool 2026-05-15→10-13): 28 Loop→Trio switchers
gain +1.45 TIR [+0.22, +2.63] with no change in t<54, so real Trio users don't show the replay's
deficit; untested whether that is their tuning.
