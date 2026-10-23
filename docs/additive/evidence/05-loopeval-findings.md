# 05 — What LoopEval's subtractive roles have measured, for the additive simulator

Inputs digested: the ice role's lessons and overlay, its generator code (`ice_gen/`), the run directories
those cite, the cross-role handoffs, the eda lessons listed below, and the project memory notes on
physiology, behavior, sensors and devices. Everything below comes from Tidepool donors under aliases
(`i001`–`i207` pilot, `x001`–`x454` expansion, `bddpNN`, `pNN`). Written 2026-10-15.

**Source keys** (each row cites one):

| Key | Path |
|---|---|
| ice L*n* | `~/dev/loopeval-ice/docs/ice/LESSONS.md`, lesson *n* (branch `ice`) |
| ice-ov | `~/dev/loopeval-ice/docs/agents/ice.md` |
| ice-code:*f* | `~/dev/loopeval-ice/analysis/loopeval_analysis/ice_gen/`*f* |
| run:*d* | `~/.loop-eval/runs/`*d* (the fitted JSON/CSV a lesson or module points at) |
| eda L*n* | `docs/agents/eda.md`, lesson *n* (this worktree) |
| HO:*date-name* | `docs/handoffs/`*date-name*`.md` |
| mem:*name* | `~/.claude/projects/-Users-pete-dev-LoopEval/memory/`*name*`.md` |

**Status labels:** **M** = measured on donor data. **M-sim** = measured, but in a synthetic plant
(UVA/Padova), not on donors. **H** = hypothesis or design choice, not measured. **M?** = measured,
but the number is suspect for the reason given.

**Two conventions to read the numbers by.** *ICE* = CGM velocity + ISF × insulin absorbed, in mg/dL/h.
ICE uses ISF from TDD (`ISF = 688 / TDD^0.74`). *g-eq* = ISF_tdd / (500/TDD) mg/dL. "Field" outcome
numbers for the pilot are on **clean time**: they exclude pod/site changes, disruptions, compression,
sensor-limit steps and the 4.5 h after long exclusions. The 24 held-out pilot donors are scored over
one 28-day month (2026-09-08 → 10-06).

---

## 1. Measured quantities usable as simulator parameters

### 1a. Insulin, ISF, and need

| Quantity | Value / distribution | Population | Status | Source |
|---|---|---|---|---|
| ISF vs TDD (settings people choose) | ISF ≈ 688 / TDD^0.74. ISF×TDD median 1868, rising 1509 → 2032 across TDD quartiles | 157 Loop donors (schedules) | M | eda L49 |
| ISF, no-history start rule (yardstick) | ISF ≈ 1267 / TDD^0.90 (≈1874/TDD). LOO median error 24%; age adds nothing | eda cohort | M | eda L54; mem:ice-isf-yardstick |
| Per-person yardstick ISF ÷ TDD-rule ISF | median 1.15, p10 0.77, p90 1.73 | pilot | M | ice L28 |
| Yardstick month-to-month variation | two disjoint stretches differ 13–15% from 3 weeks on, and do not converge further | eda cohort | M | eda L54 |
| ISF by closed-loop regression | 0.50× schedule (0.43 bolus / 0.57 temp strategy). This is a **lower bound**, not the ISF | 159 | M (biased) | eda L53 |
| TDD | median 42 U/day (range 9–184). Under 13: 20.5 U; 13–17: 48.7; 18–25: 46.6; 26–49: 39.7; 50+: 42.7 | 156–159 | M | eda L45, L47 |
| TDD day-to-day | within-person CV 20% (9–45%). Lag-1 day corr 0.21, at 7 days 0.05 (no weekly rhythm). Weekly-block ICC 0.94 | 156 | M | eda L45 |
| TDD drift | cohort median +0.3%/30 d; 41 of 156 drift >5%/30 d | 156 | M | eda L45 |
| Delivery by clock | 00–06 runs at 0.72× the daily mean, 10–22 at 1.15×. Per-person day/night ratio 1.65× (1.20–2.46); no peak hour | 156 | M | eda L45 |
| Delivery burstiness | 33% of 5-min bins deliver 0 (2–65%). Nonzero bins: median 0.11 U, p99 1.6 U. Busiest 1% of bins carry 25% of insulin (7–59%), same for both strategies | 156 | M | eda L45 |
| Automated delivery vs glucose (controller fingerprint, not physiology) | 0.3× scheduled basal at 80 mg/dL, 1× at 110, 2.5× at 250. 13× higher rising than falling at the same glucose | Loop donors | M | eda L51 |
| Daily background-ICE level (need), between days | within-person sd ≈ 11 mg/dL/h (true-day sd 11.1–11.8). Between-person sd 11.4. Noise-corrected lag corr 0.43 / 0.32 / 0.27 / 0.14 at 1 / 2 / 3 / 7 days. Covariance 58 at 1 d, ~8 at 2 weeks. Site age, prior-day lows/highs and weekends explain ~1% | 168 pilot, 18,034 person-days | M | ice L19, L47; run:2026-10-11-ice-slow/diag_slow3.log, covcurve.csv |
| Two-timescale fit to that day level | fast var 69.7 (mg/dL/h)², τ 20 h; slow var 38.3, τ 182 h. Later dropped from the generator because its own draws already carry the day variation (L49–50) | pilot | M (fit) | run:2026-10-11-ice-slow/slow_fit.json |
| Monthly (24–36 d) rhythm in daily background ICE | none above chance: p<0.05 in 3.2%, p<0.01 in 1.6% of 125 people (5% / 1% expected). Override use: 4.4% of 2,177 donors (5% expected). Sex is not in the data | pilot ≥100 d; census | M (null) | run:2026-10-11-ice-slow/cycle_screen.csv, override_cycle.log; mem:bddp-no-sex-field |
| Mean ICE level | 66.4 mg/dL/h clean (68.5 all intervals). Background (non-meal) ≈ 33 mg/dL/h held-out (39.1 in the 28 days before). Overnight fasting background 23.7 | pilot | M | ice L1, L60, L76 |
| Background ICE vs insulin activity, overnight fasting | slope +0.43 on ISF × activity. Confounded by Loop reacting to ICE, so it is not evidence of an insulin-effect gain below 1 | 163 | M (confounded) | ice L52 |
| Insulin effect vs glucose level | per U vs scheduled ISF: 0.7–0.9× near 107 mg/dL, 1.3–2× near 200 | UVA/Padova plant | M-sim | mem:treatment-kernel-transient |
| Glucose effectiveness S_G | 0.0013–0.0047 /min per person (plant impulse fit); must be estimated from real data | UVA/Padova plant | M-sim | mem:treatment-kernel-transient |
| Insulin curve | deployed Loop's stock curve gives 370–395 min forecasts. ~12 pilot donors run a non-stock curve; 6 sit at a steady ~190 min (i009: 180 min, peak 80). That is a **controller** setting; the body keeps the insulin's own model | 207 pilot | M | ice L26 |
| Infusion-site change (routine, old site ≥48 h) | glucose rises over the last ~2 h, peaks about +28 mg/dL at 0–3 h (TIR ~49%), 1.5× insulin in the first hour, baseline by ~6 h. Interval median 72 h (p10–p90 19–120); changes cluster 17–22 h | 86 twiist people, 2,581 changes | M | eda L52 |
| Infusion-site failure (early change, <48 h; a quarter of changes) | glucose climbs +9 → +22 → +32 over 6–12 h with delivery flat (0.96–1.02×); +42 at the change; normal by ~6 h | 681 changes | M | eda L52 |
| Site wear-out | none on days 1–4 (largest shift +3 mg/dL, p=0.17). Last ~12 h before a routine change: +9 mg/dL | twiist | M | eda L52 |

### 1b. Meals (offense)

Meal = pulse of excess ICE, labeled by `ice-code:meals.py`. Pulse shape = lognormal in time (`ice-code:kernel.py`).

| Quantity | Value / distribution | Population | Status | Source |
|---|---|---|---|---|
| Meal-pulse starts | 6.2–6.5 /day labeled (6.21 held-out). Unannounced 4.21–4.50 /day; entry-started 2.93 /day | 24 held-out pilot | M | ice L17, L23, L29, L52, L53 |
| Pulses and grams eaten | about 7.2 pulses, 196–228 g-eq/day (field whole day 196; v3m10 runs 225–228) | 24 held-out | M | ice L65, L94 |
| Eating at night (00–06) | 23.5 g-eq/day. Unannounced night starts 0.96/day; night carb entries 0.04/day | 24 held-out | M | ice L94 |
| Announced share of meals | 0.43–0.45 | pilot | M | ice L29 |
| Pulse shape | lognormal rate(t) = size·f(t). Mode = peak; 90% of mass by duration (s² + 1.2816 s = ln(dur/peak)). Per-meal LS fit; duration clipped ≤10 h | pilot | M (model form) | ice-code:kernel.py, meals.py |
| Pulse speed (correction to the smoothed labeler) | raw meal ICE runs 12 / 23 mg/dL/h above the smoothed rebuild at 15 / 30 min, and 8–9 below at 75–105 min. Per-meal fit: peak 6 min earlier | 3,000 pulses, 30 donors | M | ice-code:meals.py (fit_shapes comment); ice L54 |
| Meal ICE after a meal bolus | total ~124 mg/dL/h at 30 min in the field. Background alone rises 45 → 61–69 at 30 min, locked to the meal | pilot | M | ice L56, L57, L58 |
| Multi-phase meals | a second rise in 22–26% of isolated announced meals (null 11%). Not size-dependent | pilot | M | ice L5 |
| Unannounced = tail of an announced meal | 33% observed vs 21% chance (same-hour-other-day null) | eda cohort | M | eda L53 |
| Grams entered vs pulse size | within-person corr 0.29 (L13); Spearman 0.19 (L56). Pulse g-eq per entered gram 1.30; sd of log(pulse/entered) 0.65 | pilot | M | ice L13, L54, L56 |
| Entry → pulse matching | 16–19% of entries have no labeled pulse within −60/+120 min (labeler misses: ICE still rises, about half as much) | pilot | M | ice L41 |
| Meal boluses | P(bolus \| entry) 0.67–0.76; 87% of entries bolused. Delivered 2.22 U per meal bolus, 1.00 U per 10 g entered. Meal-bolus insulin 6.0 U/day | pilot | M | ice L41, L56 |
| Order of eating and bolus | eating begins before the bolus in 26% of field meal boluses | pilot | M | ice L54 |
| Carb-entry window | entries logged from 60 min before to 90 min after onset (labeling rule) | — | H (rule) | ice-code:meals.py |

### 1c. Behavior traits: rates, defense, rescue

| Quantity | Value / distribution | Population | Status | Source |
|---|---|---|---|---|
| Carb entries /day per person | p10 / p50 / p90 = 0.12 / 3.09 / 6.94. **Bimodal**: a group of non-announcers sits far below the rest | 168 trained people | M | ice L62 |
| Corrections (lone manual boluses) /day per person | p10 / p50 / p90 = 0.10 / 1.07 / 4.25. Rare correctors are real (i056: 0 in 100 days). Field lone boluses ~2.0/day in the 24 held-out, 2.2 U/day | 168; 24 held-out | M | ice L41, L62, L64 |
| Rate stability | some people's rates change month to month (i010: 0.11 → 1.43 corrections/day), which their own history cannot predict | pilot | M | ice L39 |
| Hands-off stratum | announce <30 g/day, let automation bolus, TIR <65%: 1.4% of AID donors (110 of 8,026). Median TIR 57 vs 74 core | 8,026 | M | eda L35 |
| Bolus frequency vs TIR | boluses/day vs TIR partial r +0.54. TIR 58 (1–3/day) → 80 (8+/day); +0.20 t<70, no t<54 effect. Association, not cause | eda cohort | M | eda L51 |
| Trait co-variation | people who enter more carbs have fewer severe lows (Spearman −0.31) | 24 hosts | M | ice L62, L87 |
| Proactive defense (70–100 mg/dL and falling ≥1 mg/dL/min, or heading low) | background push above own level: p10–p90 −13 to +18 mg/dL/h. Snack starts 0.44–0.93 /h. Alternate-week reliability 0.76 (push) / 0.65 (snacks), the most stable trait found | 168 | M | ice L34 |
| Severe-low defense (<60) | push median +39 mg/dL/h (p10–p90 8–67), reliability 0.50. Snack starts ~0.5 /h, **no** person reliability (−0.01): everyone eats at a low | 168 | M | ice L34 |
| Defense ramp vs PROJECTED glucose (glucose − ISF × IOB above basal) | background ICE over the next 30 min minus own mean, field median by projected band <0 / 0–40 / 40–70 / 70–100 / 100–140 / 140–180 / 180–250 / >250 = +30 / +15 / +5 / −3 / −9 / −12 / −17 / −12 mg/dL/h. 90th-percentile person at the low end: +57 / +40 / +22 / +13 | 24 held-out | M | ice L69 |
| Defense ramp learned by the kept generator (v3m13) | 0 at projected ≥120; 4 / 7 / 14 mg/dL/h at 30 / 0 / −40. Per-person onset −12 to +34 mg/dL, strength 0.56–1.22 (ML refit; did not change outcomes) | model fit | M (fit) | ice L71 |
| Rescue snack in a low | ~35 g (generated 33). Time to peak below 70 ≈ 30 min. Rebound in the hour after crossing 70: 7–11 g-eq | pilot | M | ice L29, L30, L31 |
| Second rescue treatment | a second clear rise follows 34% of first rescues if glucose is not yet rising at 15 min (25% if it is). Pete: people treat, wait ~15 min, treat again | held-out lows | M | ice-code:meals.py (RESCUE_* comment) |
| Rescue labeling rule | unannounced pulse whose onset follows BG <70 within 30 min; rescue parts gated at 6 g-eq | — | H (rule) | ice-code:meals.py |
| ICE inside a low (field) | climbs to 61 / 84 mg/dL/h at 10–20 / 20–30 min. After a crossing below 70: 58 / 95 at 0–30 / 30–60 min | pilot | M | ice L30, L60 |
| Treatment kernel shape | a 15 g fast treatment peaks at 0.38–0.56 of grams × CSF at 70–110 min, is 0.06–0.25 at 5 h and ~0 by 10 h | UVA/Padova plant | M-sim | mem:treatment-kernel-transient |
| Interrupted automatic boluses (user cancels) | 1 in 709 pooled, 39 per person-year. Per person median 0.61/1000, 10 of 67 never, max 9.33. Top decile carries 42%. Rate ∝ size^1.67 (0.06/1000 at 0.05–0.15 U → 40.4 at ≥2.5 U). Cause: manual takeover 55%, suspend 27%, pump/pod fault 2–3% (a lower bound) | 67 Loop donors, 120 d | M | eda L40 |
| Settings edits | edits that move day-average basal/ISF/CR ≥10% and hold 14 d: 70 on the pilot, 110 on 76 donors (v32). The clean-ICE level shifts with them: ISF raised → ICE −3%, insulin −3%; lowered → +8%, +7% | pilot | M | ice L40; HO:2026-10-15-frontier-replay-predicts-change |
| Dosing-strategy switches (temp ↔ autobolus) | 41 switches on 37 donors held ≥14 d each side | 207 pilot | M | HO:2026-10-15-frontier-replay-predicts-change |

### 1d. Sensor (CGM)

| Quantity | Value / distribution | Population | Status | Source |
|---|---|---|---|---|
| Compression-low rate | 0.031 /person-day pooled (748 events, 23,893 person-days). Per person p10 / p50 / p90 0.014 / 0.027 / 0.056 /day. Gamma prior α 2.37, β 75.7. Median donor ~1 per 6 weeks, most prone ~weekly | 206 pilot | M | run:2026-10-11-ice-compression/compression_layer.json; ice L27 |
| Compression hour-of-day weights | 00–06 ≈ 1.2–1.67; 10–19 ≈ 0.54–0.70 (24-value table in the JSON) | pilot | M | run:2026-10-11-ice-compression/compression_layer.json |
| Compression branches | resumes after a sensor-withheld **gap** 72%; ICE-only **dip** 25%; pinned at the **40 floor** 3% | pilot | M | same JSON; ice L27 |
| Compression geometry | slide ≥40 mg/dL below a near-flat prior trend (\|slope\| ≤1 mg/dL/min), gap ≤90 min, return within 25 mg/dL of the old trend, no overshoot, window ≤45 min. Gap-branch precision ~0.75 against a mirror control | pilot | M (detector) | ice-code:sensor.py; ice L27 |
| Compression share of lows | holds 0.7% of time below 54 | pilot | M | ice L27 |
| Generator templates | each event replays a real offset trace (withheld readings marked missing); own trace library if ≥3 events, else the pool | — | design | ice-code:sensor.py (CompressionLayer) |
| CGM limits | interval-censored at 40 and 400. Ceiling (401): median donor 0.3 h/month | pilot | M | eda L6; ice L37 |
| SD of the 5-min CGM step, by sensor (paired switchers) | Libre 3 via twiist 5.09 → Dexcom G7 8.13 (+60%). G6 6.18 → G7 6.97. Increment lag-1: Libre 0.639, G7 0.445. Flat steps: 10.7% → 8.1%. Implied sensor noise 1.28 → 1.71 mg/dL. Excess kurtosis G6 4.51 → G7 3.30 | 18 + 16 switchers | M | eda L33 |
| Sensor-invariant statistics | Hurst exponents, momentum zero-crossing 40–47 min, volatility ACF at 30 min, CV, SD/MAD (≈1.42, Laplace-like) | switchers | M | eda L33, L35 |
| 5-min ICE autocorrelation | lag-1 +0.5 to +0.6 (positive: the sensor smooths) | pilot | M | ice L2 |
| Level noise e (CGM = BG + e), AR(2) | pooled fit a1 = 0.0, a2 = −0.99; per-person variance median 0, p90 57 mg/dL². a2 sits at the fit grid's edge, so the shape is unreliable | 24 donors | M? (grid edge) | run:2026-10-10-ice-noise/noise_v3b.json; ice-code:noise.py |
| Dual-CGM interleaving | i171 alternates two sensors ~40 mg/dL apart every 1.6/3.4 min for 26% of its record; 10 pilot donors >2% sawtooth. p03: two sensors 14 mg/dL apart, increment lag-1 −0.95, step SD 6.3 → 29.4, 576 readings/day | pilot; eda | M | ice L14; eda L21 |
| Late-arriving readings | some readings reach Loop late (after a forecasting cycle); Loop sees them only once received | i008 | M | mem:cgm-late-received-v32 |

### 1e. Devices and data gaps

| Quantity | Value / distribution | Population | Status | Source |
|---|---|---|---|---|
| Omnipod pulse truncation | temps deliver floor(rate × actual duration / 0.05) pulses. A pump re-temped every 5 min loses the fraction (i040: 388 of 566 U nominal, −31%) | pilot | M | ice L25; mem:omnipod-pulse-truncation |
| Excluded (unusable) intervals | ~14% of ICE intervals (pod changes, disruptions, compression, clamps) | pilot | M | ice L1 |
| Pumpless disruptions | Loop runs with CGM and no pump (99.7–100% of cycles are no-dose guards; Loop IOB ≈ 0). 41 pilot donors, 32,773 h; single episodes 335–2,532 h. Glucose stays normal, so dosing came from an unseen device or pens | pilot | M | HO:2026-10-13-ice-pumpless-disruptions; ice L41 |
| Second-app dose records | Trio co-uploads on Loop days for 4 of 207 pilot donors (+18% to +84% bolus); HealthKit mirrors are fine (within ~1%) | 207 | M | HO:2026-10-11-ice-second-app-doses |
| Dosing strategy ↔ pump ↔ sensor | temp basal: 86/93 twiist + Libre 3; autobolus: 62/64 Omnipod + Dexcom. Autobolus users have 2.5× t<54 (0.23% vs 0.09%) | eda cohort | M | eda L49 |
| Max-basal headroom (max ÷ scheduled) | → t<70 partial r +0.29, t<54 +0.24, not TIR. Within-person cap raises (+14%) → TIR +2.9, t<70 +0.6 | temp-basal users; 16 raises | M | eda L50 |

---

## 2. Validation targets (statistics simulated CGM / insulin / behavior must reproduce)

### 2a. Outcomes

| Target | Field value | Population | Source |
|---|---|---|---|
| Clean-time outcomes, 24 held-out pilot donors | TIR 74.1, t<70 0.86, t<54 0.12, mean 152 mg/dL, insulin 33.1 U/day (median donor) | pilot held-out | ice L38, L61 |
| Replay of measured ICE (harness ceiling) on the same donors | TIR 74.4, t<54 0.17; insulin within 0.8% of the field | pilot held-out | ice L29, L38 |
| Population spread per person (p10 / p50 / p90) | t<54 0.0 / 0.12 / 0.55%; TIR 52 / 74 / 89; mean 127 / 152 / 188 | 168 people | ice L87 |
| Per-person pass bar | the field inside the person's generated 10th–90th percentile; pooled bias < a typical person's week-to-week variation | — | ice-ov |
| Change bar | predicted change accurate to about half a typical candidate lift (a few TIR points, a few tenths of t<54) | — | ice-ov |
| Training-noise floor of the generator | seed-to-seed sd: TIR ~1.8, t<54 ~0.19, mean ~4. Beyond noise = TIR >3 or t<54 >0.4 on two seeds | v3m10 | ice L61 |
| Natural noise floor of change | the field's change around random no-edit days: ΔTIR sd 8.5 (real edits 11.4), Δmean 13.3 (16.3). Noise-floor MAE: ΔTIR 4.7, Δt<70 1.2, Δt<54 0.38, Δmean 8.1 | pilot | ice L63; HO:2026-10-15-frontier-replay-predicts-change |
| Infusion-site event, routine | +28 mg/dL peak at 0–3 h, TIR ~49%, baseline by 6 h | twiist | eda L52 |
| Strategy effect | autobolus t<54 0.23% vs temp 0.09% | eda cohort | eda L49 |

### 2b. Lows (anatomy)

| Target | Field value | Source |
|---|---|---|
| Crossings below 70 | 0.71 /day | ice L60 |
| Per crossing below 70 | P(reach 54) 0.18; minutes below 70: 15; nadir 62 mg/dL | ice L60 |
| At the crossing | IOB above overnight level 0.15 U; insulin action 57 mg/dL/h | ice L60 |
| 2 h before a low | glucose 114; manual bolus before 29% of lows; ICE 27 mg/dL/h (field lows come in quiet stretches) | ice L60 |
| Episodes below 70 | 0.78 /day; still below 70 at 15 min: 0.46; time in episodes >30 min: 11.9 min/day | ice L30, L31 |
| Entering 70–90 | goes below 70 in 29% of cases | ice L29 |
| Lows after meals | meal bolus followed by <70 within 3 h: 7.8–8% (0.064 lows per meal bolus). After a lone bolus: 0.08 (0.16 lows within 3 h) | ice L54, L56, L59, L88 |
| Lows after meals within 4 h | 16% of meals | ice L13 |
| Lows by proximity to boluses | within 3 h of a manual bolus 0.39 /day; beyond 5 h 0.51 /day | ice L54 |
| Replay lows on a faithful bed (bddp11) | 26 crossings below 54 vs field 26; TIR 67.3 vs 68.0; 88% of steps within 5 mg/dL | HO:2026-10-10-ice-replay-lows-3 |

### 2c. Highs and daily profile

| Target | Field value | Source |
|---|---|---|
| Time >180 by context (% of all time) | within 3 h of an announced meal 13.2; after an unannounced start 14.0; otherwise 4.3 (>250: 1.0) | ice L72 |
| Highs with no meal in the 3 h before | 0.41 /day, median 45 min, peak 200; background ICE 41 the hour before, 66 during; IOB above basal 0.5 U | ice L72 |
| Overnight (00–06, nothing eaten since 21:00) | background ICE 23.7 mg/dL/h; glucose 130; time >180 5.6%; night-to-night sd 23.8; within-night hourly sd 12.7 | ice L76, L78 |
| Glucose by hour | 22:00 177; 00 / 02 / 04 / 06 = 150 / 142 / 129 / 128 mg/dL | ice L93 |
| Insulin activity by hour | 0 / 2 / 4 / 6 h = 1.12 / 0.98 / 0.80 U/h | ice L93 |

### 2d. Shape across timescales

| Target | Field value | Source |
|---|---|---|
| Background ICE autocorrelation | lag-1 (5 min) 0.48, lag-2 0.19 (median of 41 donors); 0.40 / 0.11 at 5 / 10 min in another fit; 0.04–0.06 at 35–60 min; 0.07 at 30 min | ice L45, L55, L73, L77; ice-code:plant_v3.py |
| Background ICE hourly-mean sd | 35 mg/dL/h; persistence of hourly volatility 0.43–0.44 | ice L42, L54 |
| Per-step glucose change sd by source (median donor, mg/dL per 5 min) | background 6.2, pulses 4.0, insulin 2.8, total 6.8 | ice L45 |
| Glucose 5-min rms | 7.2–7.3 mg/dL (8.3 in another fit) | ice L29, L43 |
| Total ICE quantiles | median 52 mg/dL/h; 90th percentile background 87 | ice L54 |
| Background-ICE draw tails | 1st / 99th percentile −79 / 153 mg/dL/h | ice L55 |
| Daily background level | day-to-day sd 11.1 (true-day 11.5–11.8); lag-1 day 0.39–0.43 | ice L19, L47; run:2026-10-11-ice-slow/diag_slow3.log |
| Meal hazard | P(new pulse in the next hour \| hours since the last ended), per person | ice-code:stats.py (`hazard`) |
| Statistic battery | quantiles at 5 and 30 min, ACF 5 min–24 h, hourly mean, daily sd, episodes (rate by hour, size, duration), hazard, next-hour ICE by BG and IOB band | ice-code:stats.py |
| Increment tail | excess kurtosis 2.71 raw → 2.88 conditioned; by state: daytime-fed 1.29, daytime-fasted 3.81, overnight-fasted 4.47 | eda L28 |
| Restoring force (closed system) | +7 mg/dL/h at 50 → −2 above 300. Set point median 152 (94–253); five-fold spread in stiffness. 156/159 have a crossing | eda L44 |
| Appearance vs glucose | slope 0.47 mg/dL/h per mg/dL, of which 0.39 is insulin action's own slope; residual 0.06 | eda L44 |

---

## 3. Structural lessons

**Must**

1. **Offense is exogenous; defense is a reaction to state.** Meals, stress and exercise push glucose
   out of range and are mostly blind to it. Insulin, rescue carbs, counter-regulation and walks bring
   it back. Routing every outside event through an exogenous path only (v3m21) improved both lows and
   level on both seeds. — M; mem:defense-team-anticipatory; ice L66, L88.
2. **The defense is anticipatory, keyed to projected glucose** (glucose − ISF × IOB above basal), not
   current depth. A shared ramp keyed to it halved generated t<54. Low-response models gated on
   current depth (<110, trough <85) miss the strong anticipators, who act above 100 while falling with
   insulin on board. — M; ice L69, L71; mem:defense-team-anticipatory.
3. **The low response is personal in how soon, how strong and how much it overcorrects; never fit it to
   counts.** Proactiveness (70–100, falling) is the most reliable trait measured (0.76). Below 60
   everyone responds at about the same rate. Treatment counts are an outcome of the simulated glucose:
   more lows must produce more treatments. — M (trait); Pete directive; ice L34; mem:low-response-*.
4. **Behavior rates are personal and must stay that way at the extremes.** Carb entries are bimodal:
   draw new people from real people (jittered), not from a Gaussian, which fills the gap. Rare
   correctors must stay rare: corrections are much rarer on AID than on pump therapy. — M; ice L39,
   L44, L62, L64; mem:behavior-rates-personal-trait.
5. **Rescue and treatment effects are transient.** Glucose effectiveness makes them fade, fastest near
   lows. A permanent grams × CSF step leaves hours-long deficits and oscillation. ICE-measured g-eq per
   low sees only the transient. — M-sim; mem:treatment-kernel-transient.
6. **Rescues come in steps.** Treat, wait ~15 min, treat again if not rising (34% vs 25%). — M;
   ice-code:meals.py.
7. **Sample a meal's attributes jointly** (pulse size, logged grams, bolus, timing). Drawn independently,
   entries decoupled from meals (corr 0.11 vs 0.29) and over-logged meals drove lows (30% vs 16%). An
   announced meal is almost always followed by a pulse. A calculator bolus must not precede its own entry,
   or it delivers ~0. — M; ice L13, L38, L41.
8. **Draw entry and bolus as their own events with their own traits**, P(bolus | entry) separate from
   P(bolus | no entry). Entries are ~1% of steps; one shared bolus head learned 0.23–0.38 against
   0.67–0.76. — M; ice L41.
9. **The day-level need state is large, persistent and not explained by anything recorded.** It must be
   generated, at a day-to-day sd ≈ 11 mg/dL/h with ~0.4 lag-1 day correlation. A persistent state must not
   be fed back into what generates it (6× amplification). — M; ice L19, L22.
10. **Compression lows are a sensor-layer artifact**: added to what the CGM reports, true BG untouched, a
    personal rate, mostly overnight, often with sensor-withheld readings. A dial must move only what it
    names. — M; ice L27, L47, L65; ice-code:sensor.py.
11. **Sensor family changes the 5-min statistics by up to 60%** (step SD, lag-1, kurtosis, implied noise).
    Hurst, momentum zero-crossing and SD/MAD hold. Model the sensor per family, or validate only on the
    sensor-invariant statistics. — M; eda L33, L35.
12. **The pump delivers whole pulses.** Omnipod truncation loses up to 31% when re-temped every cycle.
    Take simulated insulin from what the body received, never from commands. — M; ice L25.
13. **Insulin curve: the controller's model can differ from the body's.** A custom Loop curve is a
    setting, not physiology. — M; ice L26.
14. **Score on clean time only**, mask simulated data where real data was unusable, and compare insulin over
    identical intervals. Excluded stretches hold most replay lows (83% of t<54 in 42% of time). — M; ice L1,
    L16; HO:2026-10-13-ice-insulin-score-cgm-gaps.
15. **Long data gaps re-anchor; they are not integrated.** A 77 h CGM gap integrated in one step produced
    60 h at the 20 mg/dL floor. Pumpless disruptions are insulin-unknown: never fill them with scheduled
    basal. — M; ice L20; HO:2026-10-13-ice-pumpless-disruptions.
16. **Seed random streams per person.** Shared streams made every generated person move together (slow
    level +2.55 ± 0.26). — M; ice L46.
17. **Judge outcomes in closed loop, not by one-step likelihood.** Removing BG/insulin inputs cost 0.012
    nats/step yet raised t<54 from 0.08 to 1.73%. — M; ice L3.
18. **Judge per person, worst donor beside the pooled number.** A pooled rate hid a trait 14 of 206 donors
    have (fast overnight no-carb V-dips, p<0.001). — M; ice L15; ice-ov.

**Must not**

19. **The tail mixture is latent, not scheduled.** Time of day × COB × insulin tertile removes none of the
    increment's excess kurtosis, and the tail is fattest in the calmest (fasted overnight) state. Don't model
    the tail with a circadian or meal-state schedule. — M; eda L28.
20. **Don't build any input from the model's own recent outputs through a nonlinear path.** Every channel
    built from own background ICE (CGM trend, EMA, glucose sequence, previous value) produced closed-loop
    widening or a level ratchet, because the response is asymmetric to its own noise. A linear memory removes
    the ratchet. Real 5-min smoothness and the day level cannot share one channel. — M; ice L42–L49,
    L76–L86, L91.
21. **Don't let behavior see ICE.** A person sees glucose, not ICE; behavior heads that saw background ICE
    learned the labeler's trough-then-rise and over-generated meals. — M; ice L52, L53.
22. **Don't use a constant monthly cycle as default.** No donor-level 24–36 day rhythm shows above chance,
    and sex is not in the data. A monthly-cycle dial is a stress scenario, not a population default. —
    M (null); run:2026-10-11-ice-slow/cycle_screen.csv.
23. **Don't calibrate a gap before understanding it.** Swap and ablation tests first. — Pete directive;
    mem:understand-before-patching.
24. **Don't read controller fingerprints as physiology.** The restoring force, set point (152), delivery
    vs glucose (13× rising vs falling), and the appearance slope are closed-loop AID + person. They
    are validation targets for the whole loop, not plant parameters. — M; eda L44, L51.
25. **Don't normalise delivery or IOB by TDD when correlating with outcomes** (circular). Normalise by
    scheduled basal instead. — M; eda L51.

---

## 4. Open questions and disagreements between roles

1. **Which ISF defines ICE?** ice defines ICE and its plant with the TDD rule (688/TDD^0.74, eda L49's fit
   to *schedules*). eda and Pete adopted the yardstick (1267/TDD^0.90 start rule, eda L54) for all ICE
   analysis. In closed loop the yardstick did not beat the TDD rule (ice L28; lows leaned worse within
   noise). An additive plant has to pick one and stay consistent with the ICE it is validated against
   (ice-ov). **Unresolved.**
2. **Is the insulin effect state-dependent?** In the synthetic plant, the effect per U is 0.7–0.9× near
   107 and 1.3–2× near 200 (M-sim, research). On donors, the overnight slope of 0.43 and the ISF
   regression of 0.50× are confounded by the loop (ice L52, eda L53). A gain dial moved no outcome
   (ice L52). No donor measurement separates these yet.
3. **Why does replay overstate hypo changes?** Static replay predicts ΔTIR (coefficient 0.66–0.98) but not
   Δt<70 / Δt<54 (r ≈ 0–0.3, ~10× the field). The simulator role leans **H**: frozen rescue carbs. Research
   names the counter-regulation floor (HO:2026-10-15). But the ice generator, whose rescues react to its
   own glucose, also fails Δt<54 (coefficient 0.25, r 0.21–0.26; ice L40, L63). So reactive behavior alone
   has not fixed it. The cause is **unmeasured**.
4. **The generator's remaining absolute gap.** It runs TIR 63–68 vs 74 and t<54 0.5–2.0 vs 0.12, with ~15%
   more insulin (ice L60–L61, L88). Excess lows come 2–4 h after meal boluses (0.10–0.16 vs 0.064 per
   bolus) in every architecture tried. Meal-bolus sizing, entered grams, pulse shapes, meal order and
   background persistence are each ruled out (ice L54, L56, L59). The meal-locked rise of the field's
   background (+38 vs generated +12 at 30 min, ice L57, L88) is the leading lead. **Open.**
5. **Day-level variation: generate it, or let it emerge?** ice L19 says generate it (slow process). L49–50
   dropped the slow process because the model's own draws already carried it. For an additive simulator
   with no learned draws, L19's measured sd ≈ 11 and lag structure are the target. The mechanism is
   unknown: the record explains ~1%.
6. **How much do compression lows inflate t<54?** AGENTS.md calls compression a common-mode inflator of
   absolute t<54. ice's strict detector puts compression at 0.7% of time below 54 (ice L27), and it
   deliberately misses some. The true share is bounded below only. Fingersticks are too few to validate
   (47 at CGM <70).
7. **Was the replay's excess variability real?** ice L21 (replay glucose sd 58 vs field 49) and L16 predate
   the plant fixes of L24. The simulator's over-correction diagnosis was retracted as a stale-export
   artifact (HO:2026-10-10-ice-replay-lows-3). On a faithful bed the engine matches the field (26 vs 26
   crossings). Treat pre-L24 replay numbers as superseded.
8. **The level-noise AR(2) fit is suspect.** a2 = −0.99 sits at the grid edge and the per-person variance
   median is 0 (run:2026-10-10-ice-noise/noise_v3b.json). eda L16 warns against exactly this. Sensor noise
   for an additive simulator should come from eda's per-family table (eda L33), not this fit.
9. **The defense's strong end and per-person onset are unmatched.** The field's 90th-percentile person
   pushes +57 heading below 0; the generator reaches ~+40. Per-person onset agrees at Spearman ≤0.25
   (ice L69, L71). The trait is measured; nobody has a generator that reproduces its spread.
10. **Overnight highs.** Generated nights fall too slowly (ice L93). Night eating is 1.4× the field's
    (ice L94). The excess is split between meal pulses and background; the cause is **H** (long evening
    meal tails).
11. **Exercise, illness and menstrual effects have no measurement in these roles.** Their only trace is
    inside background ICE and its day-level variation. The day level is unexplained by the record (ice
    L19) and shows no monthly rhythm. Any additive factor for them must be sourced from literature and
    validated only against the aggregate day-level spread and the outcome targets above.
