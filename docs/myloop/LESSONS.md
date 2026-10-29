# myloop lessons

1. **CamAPS-style ranking of insulin-action curves adds nothing to Loop's forecast (E1, 2026-10-25).**
   A forgetting-weighted blend of six peak variants (45–105 min) ran on nine 2-month beds with
   oracle future inputs. It lands within ±3 % of the donor's preset RMSE at every horizon, and the
   best fixed per-person curve within ~2 %. Error at 120 min is 35–133 mg/dL even when the future
   inputs are known. Insulin timing is not where Loop's forecast is wrong. See
   `E1-multimodel-forecast.md`.
2. **Rescue carbs are a minority habit, heavy in a few people (2026-10-25).** Pilot pool, 207 donors:
   3.1 % of entries are unbolused entries made below 70 mg/dL, or below 90 and falling (median 26 g).
   137 of 194 donors who enter carbs log at least one; 42 log one a week or more. Loop doses
   against all of them; CamAPS covers none. Script: `runs/2026-10-25-myloop-rescue/rescue_count.py`.
3. **Hiding rescue carbs from Loop is the needs dial in disguise (E2, 2026-10-25).** 40 frequent
   rescue loggers, gr harness. In the 3 h after a rescue: −0.92 t<70, −0.18 U per rescue. Across
   the window: t<70 flat, TIR −0.39, t<70 lift −0.40. Entries the glucose rule calls rescues are
   often unbolused food. Over 25 g they add 7–9 points above 180 in the hours after. A CamAPS-style
   flag only helps if it carries the user's intent, which no rule over glucose can recover. See
   `E2-rescue-carbs.md`.
4. **A time-of-day rise response is the dial again, even with no meal entries (E3, 2026-10-25).** 189 donors, gr harness,
   no carb entries and no user boluses. The same-clock habit adds +0.08 holdout R² to Loop's 2-h rise prediction (73 % of
   donors ≥ 0.03), but scaling the rise response by it adds nothing over an additive term (14 % ≥ 0.02, median 0).
   Closed loop, the additive term (C39 `habrelr`) costs 0.51 TIR for 0.04 points of t<54, no better than the needs dial.
   This reading of CamAPS Liberty's "recognises insulin need depending on time of day" has no lever in Loop. See
   `E3-liberty-mode.md`.
5. **The 780G's meal-time gate loosening has nothing to release in Loop (E4, 2026-10-26).** 189 donors, no entries,
   automatic bolus AF 0.4 + gr. Letting the automatic bolus through down to 30 mg/dL below the correction floor (or to the
   suspend threshold) while glucose rises: ΔTIR +0.06, t<54 lift +0.07, less than the same loosening applied at every cycle
   (+0.25, lift +0.21). The rise condition adds nothing. As bolus rules on Loop's forecast, Control-IQ's hourly 60 %
   correction is −12.8 TIR without its basal boost, and the 780G's full 5-min correction is −1.2 lift. See
   `E4-rise-gated-guard.md`.
6. **In replay, moving insulin within a meal is free on lows; adding it costs them (E5, 2026-10-28).** 36 same-binary
   contrasts, 340,200 meal-event contrasts. Each arm's low cost tracks its net added insulin (r 0.82–0.86); the insulin it
   moves earlier and repays by 4 h carries none (no-entry contrasts: −7 [−24, +12] min < 70 per U, against +47 per U
   added). Event-level regressions show added insulin with *more* time high, so read prices at the contrast level only.
   Past movers bought nothing: C39's habit term moved 0.48 U a meal at net −0.06 U and changed neither lows nor highs. A
   pure dial step moves ≈ 0.2 U a meal through feedback alone. See `E5-moved-vs-added.md`.
7. **Deliberately moved insulin beats the dial in replay, but carries insulin into some lows (E6, 2026-10-29).** One
   extra automatic bolus at each CGM rise (X / ISF, 3-h lockout), with no entries and Loop left to take it back: it does,
   98 %. At X = 60 mg/dL the primer gives +1.54 TIR for +0.06 t<54 (the dial gives +1.57 for +0.23), t<54 lift +1.03 [+0.76, +1.32].
   It fails the pre-registered bar on IOB at 54 crossings (+0.09 U [+0.05, +0.14]), probably because the detector also
   fires on rises that turn (not yet measured). This is the first mechanism on the meal track to beat the dial by a clear margin. The lever is timing,
   bought with a known dose, which E5's after-the-fact split could only hint at. See `E6-primer.md`.
8. **Making the primer retractable does not remove the insulin it carries into lows (E6 stage 2, 2026-10-29).** As a
   30-min temp basal cancelled when the rise stalls, 85 % of the primer is still delivered. IOB at 54 crossings is no
   lower than with the bolus form (−0.014 U [−0.056, +0.024]), and TIR falls 0.30. Rises that have already run 30 mg/dL
   rarely stall within 30 min, so this cancellation rule cannot sort the rises that will turn. See `E6-primer.md`.
9. **On the ice generator the primer is no better than the dial (E6, 2026-10-29).** `gr_p60` gives +0.79 TIR for
   +0.146 t<70 and +0.048 t<54, and it still mostly moves insulin (11 % kept, in a 12-donor sample). A needs-1.05 dial in
   the same no-entry setup gives +0.95 TIR for +0.206 t<70. At matched t<70 the primer is +0.12 TIR [−0.08, +0.31] over
   the dial line; at matched t<54 it is −0.11 [−0.54, +0.20]. Replay's large lift (+1.03) does not survive:
   replay treats moved insulin as nearly free on lows, while the generator charges it about the dial's rate. The dial
   comparison has to be run in the same regime: ice's deployed-regime dial gave a misleading edge. See `E6-primer.md`.
10. **On a body with a known answer, replay overstates low-side change about 8× (E7, 2026-10-29).** Generator reference
    runs, replayed as records under needs 1.05 and two primers, against the generator's own re-runs: slope of true on
    predicted Δt<70 0.12 [0.08, 0.17], Δt<54 0.06, ΔTIR 0.62. Replay adds almost no net insulin (+0.06 U/day for needs
    1.05, truth +0.76): Loop takes the change back, and the lows come from timing. On these records replay ranks the
    primer worse than the dial, so E6's donor-replay edge came from the records, not the method. Null-arm floors for one
    person on the generator: ΔTIR 1.75, Δt<70 0.43. See `E7-truth-test.md`.
