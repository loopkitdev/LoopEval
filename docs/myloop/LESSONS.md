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
