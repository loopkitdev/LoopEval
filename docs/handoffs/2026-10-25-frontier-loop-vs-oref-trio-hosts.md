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
the other. Suggest C17's verdict says that and carries the field switchers (+1.45 TIR [+0.22, +2.63], t<54
flat) as the only host-neutral number. Two people over 1 and 4 weeks, so no confidence interval.

Note: `--loop-trio-overrides` used to fail on any preset name containing "/" (the cache key became a path).
Fixed in `DataCache.key` on main.
