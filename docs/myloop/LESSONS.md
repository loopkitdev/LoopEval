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
