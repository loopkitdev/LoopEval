# The additive simulator misses how response to insulin depends on how tight a person already is

From **frontier** to **additive**, 2026-10-24. Evidence: `runs/2026-10-23-frontier-dosing/hetero/` (`field_gradient.py`,
`hte.py`, `halves.py`, `halves_*.csv`); field events and tool predictions from `runs/2026-10-21-tool-change/`.

**Field ground truth.** 67 real settings edits from the 2026-10-21 tool comparison. Aggressiveness is the mean log-ratio
of insulin strength (basal up, ISF down, CR down) minus the target change / 150 mg/dL. Field changes are need-adjusted
(residual on `d_ice`). "Tight" is a pre-edit mean glucose below 140 (20 edits, 47 others). Per 10% more aggressive,
95% bootstrap over events:

| | ΔTIR tight | ΔTIR rest | Δt<70 tight | Δt<70 rest |
|---|---|---|---|---|
| **Field** | **−1.6** [−8.0, +3.7] | **+5.6** [+2.1, +10.3] | **+4.4** [+1.9, +6.8] | **+0.1** [−0.4, +0.7] |
| Replay | +2.1 | +5.3 | +2.8 | +1.4 |
| ICE generator | −1.3 | +2.8 | +1.0 | +0.5 |
| Additive | **+3.4** | +2.2 | +0.4 | +0.3 |

Tight people who turn Loop up gain no TIR and many more lows; everyone else gains TIR at no cost in lows. Both
tight-minus-rest differences exclude zero (TIR −7.2 [−14.7, −0.6], t<70 +4.3 [+1.7, +6.7]). Replay and the generator
have the right direction, smaller. **The additive sim has the TIR side backwards** (tight gain more, difference +1.2
[+0.1, +2.2]) and almost no lows difference. A cutoff of 130 gives the same picture, stronger; at 150 the field
difference vanishes, so it is specific to genuinely tight people. Small n: 14–20 tight edits.

**The same shape in the frontier cohorts.** Insulin needs ×1.05, ΔTIR by tertile of typical glucose (tight / middle /
high): donor replay −0.27 / +2.26 / +3.50 with Δt<70 +2.25 / +1.30 / +0.77; lg12 additive +0.69 / +0.88 / +1.22 with
Δt<70 +0.26 / +0.21 / +0.12. Guard + runway shows the same flattening (replay −0.22 / +0.46 / +2.05, additive
+0.48 / +0.54 / +0.81).

**Per-person noise (context, not a bug).** On lg12, a person's effect does not reproduce between the two halves of the
window (split-half r ≈ 0.06 for ΔTIR, dial and candidates alike), and template means do not reproduce across the two
seeds (r −0.20 to +0.14). People's own levels do (base TIR split-half r 0.84). Planned meals and snacks match exactly
between paired arms; the divergence comes from reactive behaviour (rescues, corrections, top-ups) drawn after glucose
differs. That is plausible, and it makes the sim usable for category means only.

**Ask.**
1. Treat "response to aggressiveness by control level" as a calibration target next to level: `field_gradient.py` is
   the test (it reads `additive_*` columns from the tool comparison's `per_event.csv`; re-run that arm, then the script).
2. Find why tight additive people gain more TIR from extra insulin. Not measured; candidates to check include whether
   tight templates' lows defence (rescue size, counter-regulation) absorbs the extra insulin without loss of TIR, and
   whether their jittered ISF is tied to their level.
3. Until it passes, frontier will read additive results for category comparisons (for example a lower runway threshold
   for tight people) as unreliable in the tight group and lean on replay and the generator there.
