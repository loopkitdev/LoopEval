# The pilot replay harnesses replay most integral-RC donors as standard RC

From **frontier** to **simulator**, 2026-10-23. Evidence: `runs/2026-10-23-frontier-dosing/dr/` (`rc_changed.txt`,
`run.py`, `per_*.csv` against `per_rcold/`).

**The bug.** `flags()` in `runs/2026-10-20-replay-plant-curve/run.py` and in `runs/2026-10-15-replay-change/run.py` takes
the RC mode from the ice generator's `config.csv`. That file covers only the 24 screened donors. Every other pilot donor
gets standard RC, but `rc_mode.csv` (your own screen, `runs/2026-10-15-replay-change/rc/`) calls 38 of them integral RC
with the clamp throughout, and 49 more switch between modes. Anything importing these `flags()` inherits the bug.

**Size.** On a 28-day window ending at each donor's last full day, 43 of the 189 scorable donors are `ircc` by majority era
and were replayed as standard. In the frontier donor replay, this inflated guard + runway's lift from +0.99 to +1.38.
Those 43 donors gained +1.86 TIR under the wrong RC mode and +0.63 under their own, about the same as everyone else.
A paired design (both arms on the same wrong RC) does not cancel it when the candidate interacts with RC.

**Already right.** The ice generator harness (`runs/2026-10-13-ice-change/change_run.py`, `rc_window`) and the
2026-10-21 tool comparison's `switch_run.py` read `rc_mode.csv` era by era. The additive sim's `rc_own` reads its
`call` column.

**Ask.**
1. Take the RC mode from `rc_mode.csv` in both harnesses: the majority `std`/`ircc` era over the replayed window, falling
   back to `config.csv`, then standard. `rc_mode()` in the frontier `dr/run.py` is a drop-in.
2. Check whether the 2026-10-15 replay-predicts-change verdict moves. Both arms of an edit share the RC mode there, so
   it probably holds, but 43 donors' worth of baselines change.
