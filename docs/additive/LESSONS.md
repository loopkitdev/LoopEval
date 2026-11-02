# Lessons — additive role

The standing lessons: traps, method rules, Pete's rules and the dead ends not to retry. Each keeps its original
number. The full record of lessons 1–547 (the route, superseded fits, every number) is
`archive/LESSONS-001-547.md`; a citation "L N" or "LESSONS N" in code or docs resolves there. The measurements
behind each component's parameters are in `evidence/17-measured.md`, the literature in `evidence/00–16`.
New lessons continue from 548, newest last. Keep this file to what still changes how someone works; move
evidence to the evidence files.

1. **No mystery terms.** A variability or offset term exists only if its size comes from its own controlled-condition
   evidence; free-living variability (closed-loop TDD CV 17%, overnight 31%; Ruan 2016) is a target the named factors
   must jointly reproduce, never an input. When a statistic misses, re-check a named component or find the missing one.
   Intrinsic terms that pass: day-level SI CV ~8% (repeat clamps), per-dose absorption jitter ~15% (Heise 2017).
   (Pete 2026-10-15; the data-driven residual layer is the one exception, Pete 2026-10-27.)

4. **The measured fasting insulin rate is not the true basal.** Fasting periods carry unannounced eating and meal tails;
   taking that rate as truth left TDD − 24·basal ≈ 0 and diets of ~30 g/day. True basal comes from the TDD balance; the
   fasting rate is a validation quantity only.

10. **Ablate before tuning.** One ablation (runs/a_*) showed the S2013 hypo-risk term was nearly all of the excess lows
    (t<54 8.5% → 0.27%); λ stays 0. Switch a suspect component off on the same people before fitting anything to a miss.

17. **Read a borrowed ratio in the units it was measured in.** ice's "pulse g-eq per entered gram 1.30" uses
    g-eq = ISF_tdd/(500/TDD), not settings ISF/CR; applying it to settings overstated carb sensitivity ~1.36×. Check the
    definition behind every borrowed number, and measure the integrating behavior (glucose after a bolused meal) directly.

18. **Self-check every new physiology or behavior path: a body dosed to its own truth must sit near its rest level.**
    Truth settings, `--enable perfect_person`, every disturbance `--disable`d, internal drive, ~10 days. Test against a
    control body identical except the input, never an assumed rest level (L 6). The self-check must really switch off
    defense, grazing and fat resistance (L 40) and must use the same ISF/CSF definitions as the calibration (L 71–72). The `selfcheck.py` driver was removed
    2026-10-30 (unused since); recover it from git (b77f280a^) when a new path needs it.
    Every carbohydrate path (meals, rescues, snacks, exercise carbs) shares the person's calibrated per-gram sensitivity
    (fast glucose at f × 1.25).

19. **Reconcile the insulin that crosses every interface before reading any cohort statistic, and again after every
    engine change.** Controller → plant → pump → depot → plasma. A plant that dropped late doses delivered half of
    Loop's insulin for cohorts c1–c11; engine 8e86860 forwarded 0 of 44.8 U of person boluses (L 25). The plant's
    received-dose log and delivered/received per person (expect 0.94–1.04) catch this; a two-binary A/B on one person
    isolates it.

22. **Measure simulated and real with the same event definition, through the same pipeline.** Donor meals are timed by
    the ice labeler's pulse onset (~30 min after eating); compare simulated meals through the labeler too
    (`ice_check.py` → `meal_response.simulated_labeled`). Calibrate any labeler-measured ratio through the labeler, not
    on pre-erosion model quantities (L 27).

26. **Size a behavior's rate by the donor's exposure, not a guessed opportunity count.** A per-minute hazard while the
    qualifying condition holds, sized so the donor's measured rate is realized over the twin's own exposure; then check
    the realized rate (conditions such as "not falling, no bolus in N min" cut exposure, L 42).

30. **Look at the worst person-days, not the averages.** Two multi-day excursions were half the between-day spread and
    made a fake shared "dip". Tidepool fingerstick records are 98.7% mirrored CGM values (346 real sticks, 70 donors):
    they cannot calibrate sensor bias.

31. **Fit the sensor to sensor-only targets (FDA iCGM tables by range, two-sensor PARD), never to CGM shape.**
    Donors' 5-min roughness includes real glucose movement; a sensor fitted to it absorbs whatever the physiology lacks.
    Accuracy error without precision error needs an error common to co-located sensors (Biagi 2017). Noise must shrink
    at low glucose or a realistic noise level manufactures lows (L 29).

35. **A per-person trait read off a noisy labeler is mostly the labeler.** Run simulated people with a known trait
    through the same labeler first: it added ~0.46 log-sd of carb-count bias, all of the donors' 0.45. Person bias is
    small (Brazeau 2013 ±0.10).

36. **Count behavior from the raw record on both sides.** The labeled-pulse entry count (2.07/day) undercounted the raw
    record (2.97 entries/day, 4.59 manual boluses/day, 12.0 U/day by hand); built and validated on the undercount, the
    error was invisible.

38. **A compensation outlives its cause: re-test it when the cause is fixed.** Visentin's circadian swing had been
    halved to offset fixed-rate emptying spikes; once emptying was fixed the full swing fit (24-h amplitude 0.14 vs
    0.13).

42. **The FDA tables pin the sensor error's size, not its timescale; the CGM's own structure must pin that.**
    Stationary colored noise erased the donors' volatility clustering, Hurst and rate dispersion, which true glucose
    already carried; the noise level wanders (Facchinetti 2011).

51. **Donor exports are UTC with no zone.** Clock-hour statistics need the ice steps' local hour (`quiet.local_offset`,
    `to_local`). In UTC, day/night insulin read 1.38 (local 2.06) and an "overnight variance gap" that did not exist
    sent work toward growth-hormone pulses.

58. **Donors' night labeled "pulses" are mostly not eating.** Raw carb records show eating on 7% of nights; the labeler
    makes night pulses from post-low rebounds, sensor and drift. Snacks and grazing go in waking hours only.

63. **Cohort noise is large: a change must beat the seed-to-seed scatter.** One model on two seed sets moved mean ±3,
    between-day fraction ±0.025, Hurst ±0.015, zero-delivery ±2, night CV ±3, day/night ±0.13. KS pass/fail flips near
    p 0.05 are noise, and KS counts compare only at equal n (56 people pass more statistics than 112, L 57). Targets are
    failures that hold on both draws.

65. **Twin comparison separates model gaps from template sampling.** Compare each twin with its own donor: a cohort gap
    that vanishes twin-wise (e.g. zero-delivery time, entries per day) is which templates were drawn, not a missing
    component.

68. **Glucose effectiveness (SG) may be calibrated within its evidence range against slow structure (Pete
    2026-10-16, L 75).** It is a named parameter the evidence leaves unpinned, so choosing it inside the range is not a
    mystery term. It trades level and lows against long-range structure, so read every statistic it moves, not one:
    ×0.7 raises Hurst but worsens mean and TIR; ×1.4–2 shortens excursions, lowers Hurst and doubles t<54 (L 75, 98).
    The range in the code is UVA/Padova's 0.0013–0.0047 /min; ReplayBG's identified median 0.022 (L 75 used it as the
    top) comes from closed-loop identification, which loads unmodelled dynamics into damping (L 3).

83. **Candidate arms run paired on the same simulated people.** Same people, seeds and life events under the deployed
    controller and each candidate's flags (`cohort.py --flags-json`); σ-gated flags use each person's own σ5 median from
    the baseline run; `patient_sim/candidates.py` gives paired deltas with bootstrap CIs on CGM and true glucose and the
    lift over the insulin-needs dial (×0.95 / ×1.05). Stress scenarios inject one ground-truth event on day 4 into every
    arm (`--enable scenario_<name>`, `scenario_level`; L 85). A deep sensor false low costs pull-back candidates TIR
    (they believe it), a sensor-robustness cost replay cannot isolate (L 86).

88. **Donor quiet windows have labeler blind spots.** Half the pilot donors have a label-free stretch over 24 h (max 57
    days), holding sharp unlabeled rises. Restrict "quiet" to labeler coverage (inter-label gap ≤ 18 h).

91. **The gut alone cannot give the donors' meal shape.** Faster emptying (tracer pace, `ge_mult` ×1.4–1.6) restores the
    sharp first-hour rises but overshoots CV (39 vs 35) and the later falls; hyperglycaemic slowing of emptying at its
    published size, re-fitted through the labeler, caps highs and drops skew (L 33, 89–91). Bolus timing is ruled out
    (L 89). Any further gut change must be re-read through the labeler before scoring.

94. **Donor records hold long stretches of unknown insulin.** 5.5% of donor 3-h windows have < 2% of TDD recorded (60%
    no dose record, 40% zero temps; 58% overlap a listed disruption; 164 of 168 donors). Glucose still falls there, so it
    is unknown, not absent, insulin. Diluted by these nights, per-unit insulin at night-time highs looked 40% weaker in
    donors; with insulin recorded it matches the sim (about −8.7 mg/dL per 1% of TDD).

95. **Donor delivery statistics mask no-record stretches.** `validate.delivered_5min(..., mask_gaps=True)`: any stretch
    ≥ 30 min not covered by a basal record (zero-volume temps count as covered) is NaN; a block with no known insulin
    keeps only glucose statistics. `real_pilot.csv` is masked; `real_pilot_unmasked.csv` keeps the old version.

99. **Automatic boluses reach the plant inside that step's 5-min basal segment (engine design, not a bug).** LoopEval
    books the auto-bolus inside the temp-basal segment to keep Loop's net-basal IOB right; trace basal + trace auto =
    what the plant receives (L 11). Plant-side "bolus" counts exclude automatic boluses, and they take the basal depot's
    PK without the per-dose jitter. Shape statistics (step skew, ACF zero-crossing, day/night) do not follow the
    individual donor (rank ρ ~0.1): the sim reproduces the population spread of shape, not each person's own.

103. **`--set announce_mult=x` gives the same people announcing less, paired.** Each entry (meals and snacks) is kept
   with probability x on its own stream (seed + 1213), drawn after all other draws. A dropped meal is eaten unentered
   and unbolused, its pre-meal override goes with it, settings are unchanged. Use it for reduced-announcement candidates.

106. **The labeler cannot see within-person bolus timing; only the per-person median lead survives.** Labeled onset
   error SD 26 min makes the labeled within-person lead spread (27 min) almost all noise; ~200 meals average the median
   to ~2 min. So the bolus lead is the donor's median minus the labeler's 2-min bias (`lead_own`, default), and
   `lead_sd` 23 is set by matching the labeled lead IQR (50 vs donors 51), not measured directly.

107. **Count wear as distinct 5-min slots, and convert time with `as_unit("ns").asi8`.** 21% of G7 donors upload
   duplicate readings seconds apart, so counting readings over-states wear. `view("int64") / 1e9` assumes nanoseconds
   and gave ~10× circadian amplitudes under a microsecond pandas build.

114. **The body's insulin timing comes from clamp evidence, never from Loop's curve (Pete 2026-10-17).** p2 0.025 is
   the lispro clamp fit (15 U Humalog: 6.3% of the effect in the first hour, PMC7716902). Field correction boluses
   cannot pin p2: on steady-CGM lone corrections the signatures for p2 0.02–0.05 differ by ≤ 7 mg/dL/h per U, inside
   donor noise (`corr_ice.py`, L 113). Match counts that move 26–30 non-monotonically across a knob are noise.

117. **About four-fifths of the sim's sharp CGM rises (> 20 mg/dL / 5 min) are sensor noise.** Simulated true glucose
   rarely climbs faster than 4 mg/dL/min. Donors' extra sharp rises (+9.3 per 1,000 daytime steps, with falls
   matching) are real glucose: mostly from normal levels, sustained (81% keep climbing), mostly never labeled.

123. **`night_cv` is the night-to-night CV of overnight delivered insulin, not of glucose.** Simulated clean nights
   match the donors' glucose structure (`night_parts.py`). Measure dinner timing from entries ≥ 30 g
   (`dinner_entry.py`), not from labels: the largest labeled pulse per window mixes snacks and labeler noise.

125. **Donors' night insulin varies because their Loop trims a scheduled night basal set above need; the body's
   basal share centre is 0.42 (Pete 2026-10-17).** Loop's night gain matches (L 124). Giving each body its donor's
   night delivery (`basal_own`) made the sim's night delivery rise further. CGM t<54 is a joint test of body and
   sensor: at the time ~80% of the sim's CGM time < 54 was sensor error.

128. **Twins do not inherit their donor's variability; donor CV follows behaviour.** Twin Spearman (c135): TDD 0.90,
   mean 0.23, TIR 0.17, CV −0.06; donor CV correlates with announced share (−0.38) and rescues/day (+0.46), sim CV with
   neither. Split cohort gaps by dosing strategy: the CV gap sat with temp-basal twins, the day/night gap with
   automatic-bolus twins.

129. **Compare forecast drift like for like: donors' RC from a plain replay of their own record vs the sim trace's
   candidateRC.** It is a body statistic, not a fit to Loop (`rc_meal_donors.py`, `rc_hours.py`, `rc_since.py`).
   Donors run 3–4 mg/dL below Loop's forecast in the first 2 h after entries: real meals deliver less early than Loop
   expects.

130. **Anchor meal comparisons on carb entries, not labeled pulses** (`entry_traj.py`). Conditioning on labeled pulses
   selects meals that rose. It hid that simulated meals were over-covered while donors hold ~+5 mg/dL per 10 g for
   3–4 h. Not explained by carb counting (Brazeau regression), follow-on eating, detection, or appearance (L 101).

133. **No single ISF scalar fits both meal plateaus and levels, and dose size or bioavailability is not the cause.**
   Peak calibration got levels and over-covered meals; total-drop the reverse (L 132, 140). Heise 2017: action linear
   to 0.2 U/kg; Wilinska 2005: boluses relatively more bioavailable. A separate glucagon term would double-count the
   Romeres-calibrated EGP arm. The meal plateau and the ACF zero-crossing have separate causes.

136. **BDDP device_data holds donor evidence for life factors: `physicalActivity` (HealthKit workouts, no steps or
   heart rate) and `reportedState` (Dexcom G7 app logs of illness, stress, cycle, alcohol, symptoms).** Logs are
   voluntary and episodic, so read their effects as lower bounds. Logged workouts are not meal-coupled (L 135).

143. **The intake budget pays for all eating, grazing and hypo treatment included; total-drop ISF + `budget_all` is
   the base (Pete 2026-10-18; ac6b40e).** Donors' TDD paid for everything they ate; the old budget left the sim eating
   40–50 g/day beyond its insulin, hidden by the peak calibration's ~2.16× action (L 140). With no hidden excess, missing
   lows must come from named low-side components. `--disable isf_total,budget_all` restores the old base.

145. **A quarter of real lows start within 2 h of a carb entry** (`low_ctx.py`): donors 0.270 / 0.166 / 0.623 onsets
   per day at < 2 h / 2–4 h / 4 h + after an entry. Check per-person and per-tercile, not the cohort median: on the new
   base the meal response split by entries/day tercile in the sim but not in donors (L 144).

149. **The first-hour meal spread is within each person, and no per-meal random term sets it.** Count error, speed,
   lead, fast share, drink and emptying all leave the within-person 60-min IQR at 11.8–14.7 (donors 19.1). Insulin
   around meals already matches (L 148). Donors enter later relative to eating (22% vs 11% of entries arrive with CGM
   up > 15 mg/dL in 15 min). Do not widen a meal knob to chase it.

151. **Fat resistance is relative to the person's usual fat (`fat_rel`, default).** A12's SI dip booked on top of
   ISF / CR / TDD that were already tuned on the person's ordinary meals (mean SI × 0.92) made a day-long upward drift.
   `fat_rel` divides the term by its own mean over the planned days, so only fattier-than-usual meals dip SI (as caffeine
   treats habitual intake). (Pete 2026-10-18: `fat_rel` default.)

152. **The patient model is independent of the controller; validation runs use the donor's deployed controller.**
   Never tune the patient to close a gap that is a controller difference (e.g. integral RC donors). Validation cohorts
   run with `--enable rc_own`; the code default stays stock for candidate testing. (Pete 2026-10-18: "I want to avoid
   coupling the patient too strongly to Loop"; "keep the patient's side as accurate as possible, regardless of dosing
   method.")

157. **Insulin action matches the donors'; real rises end sooner.** Lone corrections 0.5–3 U from a flat CGM trend
   drop as fast in the sim as in donors (ΔCGM per U at 60 / 90 min −20.7 / −40.9 vs −26.1 / −35.7). The whole
   correction-timing gap is corrections given into a rise: real rises turn within ~30 min, the sim's kept climbing ~90.
   So dose-dependent absorption (`dose_beta`), a shorter action delay (p2 0.04) and a slow meal tail (L 155–156) were
   aimed at the wrong term; split correction profiles by trend at the bolus (`corr_drop.py`) before blaming insulin
   timing.

158. **Unlogged grazes absorb as liquid sugar outside the energy ceiling (`graze_fast`, default).** Evidenced form for
   the 5–15 g drinks-and-sweets share of unlogged intake (Calbet 1997, Hunt 1985); it shortens rising-trend corrections
   part of the way. A sugar-heavier snack share (`snack_fast` 0.5) did not pay. (Pete 2026-10-18: `graze_fast` default.)

160. **Real quiet daytime glucose wanders on a ~40-min scale; it is the body, not the sensor, and only while awake.**
   Quiet-period step-ACF zero-crossing: donors 40 min for G6 (37.5) and G7 (40) alike; sim CGM 20 (sensor noise; true
   glucose 130). By hour: donors night 15 / day 40, so the wander is waking-life only. Fast brief inputs do not make it:
   fragmented movement (`act_frag`), finer grazing (`graze_split` 3) and sugar-heavier snacks all leave it at 20–25
   (L 159, 161–162). Scripts `acfctx2.py`, `acfctx5.py`.

163. **Upright absorption (`posture`) and fragmented waking movement (`act_frag`) are defaults.** Clamps behind the
   sim's PK are supine; sitting cuts insulin absorption 19–44% (Hildebrandt 1985). Together they brought lows to the
   donors' at the time. Posture now runs at half its measured contrast (L 169). (Pete 2026-10-18: `posture` and
   `act_frag` default.)

167. **The sim's lows are misplaced toward the night, not too many; the cause is the overnight glucose balance.** Donors
   22% of low episodes at 00–06 h (0.16 per person-night) vs the sim ~half. Ruled out: timing of the day's insulin,
   basal share, the basal-need profile (`prof_w` 1.0), targets, circadian profile, sensor artefacts, missing night data
   (donor G7 coverage 0.971 night vs 0.948 day), night treatment behaviour, insulin delivery (night delivered ÷ scheduled
   donors 1.32, sim 1.24). On quiet nights (`quiet_nights.py`) the sim's body falls further on less insulin. Every
   night-holding lever found removes daytime lows too (L 193).

169. **Posture runs at half the measured contrast (`posture_mult` 0.5, default).** The full supine step at bedtime made
   glucose fall from bedtime (00–03 h donors +1, sim −16 vs mean) and carried the extra night lows; Hildebrandt
   compared sitting with flat supine, real evenings and sleep are not. `--set posture_mult=1.0` restores the full step.
   Self-approved (additive standing permission).

177. **The donors' extra first-hour meal variability is not the meal's own glucose.** Within-person IQR of the 0→60 min
   change is size-independent (donors ~63–69 mg/dL, sim ~50). Every meal-side lever (speed `meal_k`, `ceiling_speed`,
   `gi_cv`, fast share, drinks, count spread) adds first-hour spread only by moving the meal earlier, which empties the
   2–4 h plateau the donors keep. The sensor adds nothing in the sim (CGM 51.8 vs true 54.6) and G7 rate-dependent error
   is only ~1.15× overall (Garg 2022). Meal timing matches (time-to-peak median 101 vs 99 min, within-person SD 51 vs
   47; L 178); the gap is amplitude.

184. **Night unentered rises: donors 0.66 per night, and the sim's body makes ~0.08; the gut matches tracer data.**
   Same detector both sides (CGM +30 within 60 min from ≥ 80, no entry −60..+30 min): day rates match within 0.07/day;
   83% of the sim's night rises are sensor recoveries. Delivery disruptions explain ~0.02/night (L 190), smooth
   `sleep_util` none (L 189). Trap: donor series from `quiet._donor_series` are already local time; do not offset again.
   Scripts in `runs/2026-10-18-additive-workouts/`.

187. **Most donor "second boluses" belong to a neighbouring entry; genuine split meals are second helpings (9.5%).**
   Donors take Loop's full recommendation on a meal bolus (requested ÷ recommended p10–p90 1.00, L 186). Of two-bolus
   meals, the first came before the entry in 46% and another entry sat in the prior 90 min in 44%. LESSONS 47's
   `p_split` counts both. Giving meals the full recommendation (`split_full` v1–v3) does not add early lows; only
   insulin beyond the recommendation did.

188. **Per meal, the sim's post-bolus drop matches the donors'; the early-low shortfall is spread over several small
   parts.** 0–2 h nadir minus entry p10 / p50 / p90 −84 / −11 / +3 vs −85 / −12 / +2; between-person SD 16.7 vs 18.5.
   Shortfall parts: fewer lows per meal from ordinary starts, a higher start, fewer separate entries (donors ~0.5/day
   merged by `entries_raw`), no stacked multi-entry meals. Downward edits after entry are rare (0.4% of entries ≥ 15 g,
   L 185): real meals grow after entry rather than shrink.

193. **Every mechanism that holds the night up also removes daytime lows.** Posture off, `sleep_util`, `ge_circ`, faster
   p2E, `egp_sat` all act on falls everywhere; donors have more daytime lows AND fewer night lows. Adopting a night fix
   waits for a time-specific daytime-lows component.

195. **Compare the meal EGP nadir like for like.** Romeres 2025's 44 ± 17% is the mean of each subject's own nadir (time
   160 ± 110 min), not the minimum of a median curve; tracer EGP includes glucose-mediated hepatic suppression, which the
   sim carries inside SG (hepatic part ~0.7). Use `egp_romeres2.py` per person.

196. **Refit a drifted component to its own evidence, then refit what drifts after it.** (Pete 2026-10-18.) Doing so
   (EGP share U(0.7, 0.9), `egp_sat`) showed the old base's low count leaned on a liver too weak and too slow; matched
   count fell (40 → 28) and that is accepted.

198. **The missing meal variability is inside the meal, not the starting state.** Within-person SD of the bolused-meal
   0–2 h drop: donors 36.7, sim 26.7. Starting state (CGM at entry, trend, insulin) has the donors' spread and the same
   effect (joint R² 0.34 vs 0.41); the SD left after it is 31.5 vs ~20.5. In the sim the true SI and the eaten/entered
   ratio do not carry it within 2 h. Per-site absorption spread (`site_cv` 0.27) adds only a little (L 199).
   Scripts `meal_var.py`, `meal_var_don.py`.

204. **Insulin acts in the twins' bodies as in the donors', read by one quiet-hour regression.** Raw yardstick slope
   (hourly CGM change on Loop-absorbed insulin, quiet = no entry or user bolus in the prior 4 h; `sim_yardstick.py`,
   `don_yardstick.py`) ÷ isf_true: donors 0.56, twins 0.53. The total-drop ISF calibration is like for like with how the
   donors' ISF is measured; look for level gaps in intake vs bolus, not in the body's insulin response.

207. **B2 dawn is inert in templated cohorts.** It applies only to people without a donor basal profile (the donor shape
   carries dawn); `--disable dawn` reproduces a templated run exactly. Do not tune B2 to move a templated cohort's morning.

208. **Within-meal variability comes from named sources only (Pete 2026-10-18).** Per-meal emptying speed stays at its
   Elleri-sized lnN SD 0.4 (gi_cv 0.8 is needed to reach the donors' spread, twice the evidence); no lumped meal-state term.
   Hengist 2025's duplicate-meal ICC 0.17–0.28 is a target for the named factors together, not an input. A wider
   meal-speed spread only adds slow meals the bolus outruns, so it lowers the 3-h ending; it cannot widen both tails.
   Glucose effectiveness may be calibrated inside its evidence range 0.0013–0.0047 /min (Pete 2026-10-16).

213. **Sensors are fitted to their FDA tables on the current bodies, and the fit drifts when the bodies change.** Faster
   bodies turned the old G6 / Libre 3 / G7 fits into false lows (CGM < 54 MARD 26–31 vs FDA ~14). Refit each family with
   `sensor_fit.py` after body changes. When the FDA refit costs the donors' sensor texture (G6 step kurtosis 3.60 → 1.63),
   the FDA fit wins (LESSONS 31's rule); `trans_prop` does not separate the two, since both come from the noise-level wander.

215. **Recorded HealthKit workouts are too rare and too well managed to carry missing post-meal lows.** BDDP
   `physicalActivity` rows (duration, HKAverageMETs; `time` is `{"$date":{"$numberLong": ms}}`): median 0.03 workouts /
   donor-day; 2.5% of bolused meals overlap one, and those end < 70 no more often (9.2 vs 8.6%). Everyday movement is not
   in the record.

217. **Meal carbohydrate arrival is measured from real data with the ice labeler on both sides (Pete 2026-10-18).**
   Arrival per entered gram, time to peak, duration and their meal-to-meal spread match the donors' (`arrival.py`).
   Cohort statistics can match while individuals do not: the twin's 3-h meal change had r −0.01 with its own donor's.

219. **Per-person twin calibration through the body's ISF is the wrong lever for low-prone donors.** `--enable twin`
   (Pete 2026-10-18; off) fitted `twin_isf_mult` to each donor's time < 70; 24 of 78 hit the 2.5 cap, all low-prone, and a
   body 2.5× more sensitive than its own yardstick contradicts the measurement (donors' yardstick / settings ISF is
   unrelated to time < 70, Spearman −0.15). Keep any twin ISF multiplier inside the yardstick's uncertainty (~±25%).

223. **`bolus_decisions.parquet` holds requested, not delivered, boluses.** Rows are Loop's bolus-screen dosingDecision
   records (reason normalBolus): the person's requestedBolus and the recommendedBolus shown; cancellations count at the
   requested amount; "lone" = no carb entry within 30 min. Verified 192 / 192 rows against raw records for one donor.

225. **Correction frequency is capped by opportunity, not by the hazard.** The gates (above threshold, not falling, no
   bolus within corr_wait) bound the rate: raising `corr_p_mult` 1.32 → 2.5 left lone rate at 0.61–0.68 of the donors'.
   Raising the threshold removes opportunities. Every user-dosing behaviour (size, over-recommendation, frequency,
   stacking, top-ups) at donor size failed to make the donors' untreated daytime lows (LESSONS 223–226).

228. **Per-meal carb-count error is shaped from data: count_sd median 0.30 (Pete 2026-10-18).** Brazeau 2013's clinic
   error (log SD 0.20) cannot see meals left unfinished or added to at home; 1.5× puts the labeled arrival ÷ entry
   distribution on the donors'.

237. **`truth.pkl` `bolus_requests`: + = a ratio of Loop's recommendation, − = absolute units.** Count user boluses with
   `f > 0 or f <= −0.05`; `f > 0` drops every hand-dialled bolus (corrections, top-ups, free and stacked boluses).

240. **`meals_labeled.csv` onsets are datetimes from world.EPOCH (2026-01-05).** Convert as `(onset − EPOCH)` minutes;
   anchoring on the first onset's midnight put labeled onsets a day off in seven scripts. Like for like: donors show only
   carb entries and labeled pulses, never the sim's true eating events.

245. **Compare post-exercise glucose with a measure that does not condition on carb entries.** The sim's "entry-free"
   windows still hold ~49 g of unentered eating per session, which donors' entry-free windows cannot show. Use all
   workouts or labeled pulses around workouts. Deferring eating out of sessions (`ex_no_eat`) stays off.

254. **Daytime basal need cannot be read from delivered insulin the way night need can.** Drift-corrected need in
   entry-free daytime windows (1.25–1.42× schedule) still covers unentered eating, so it is an upper bound. Nights are the
   clean reference; the 24-h basal level stays set by the TDD balance.

256. **A per-person level cause must precede the glucose.** Donor features Loop or the person produce in answer to
   running high (night delivered / scheduled, CGM at corrections) correlate with a donor's mean but cannot carry it into
   a twin. The donors' measured ISF mismatch does not rank them by level (Spearman −0.13), so twins must not either.

257. **Ruled out for the missing fast falls:** glucose effectiveness, meal speed, early insulin action, carb sensitivity,
   formulation, counter-regulation, sensor share, per-dose absorption variability (dose_cv 0.3–0.35, Schiavon 2020, does
   nothing; stays 0.15), and too-small proactive snacks (LESSONS 236–239, 248, 257). The donors' fast falls are mostly real
   glucose; the sim's median fall rate matches, the > 3 mg/dL/min tail is a third of the donors'.

259. **The body takes the donor's data-fitted value over the entered setting: ISF_W 1.0 (Pete 2026-10-19: "Would take
   fitting to data over a users entered settings").** The data fit is the ICE yardstick × the body-model fit
   (`fit_body --regression`, Pete 2026-10-19: fit through the body's own model), not the 1800 rule on TDD that the
   templates' isf_true once held. A free 3-h replay grid on sensitivity degenerates (k at the floor): use the regression.

267. **Sensor white noise must not stand in for missing body motion.** The sim's large CGM steps had true BG moving ~6
   mg/dL; lowering the noise alone moves the CGM's motion under the donors'. Fix the body's fast motion first, then refit
   the noise to sensor evidence.

274. **Night lows end when people wake, not by faster counter-regulation.** A faster CR time constant makes night lows
   shallower but no shorter; the alarm-wake chance sets night low duration and rescue timing (p_wake_alarm N(0.72, 0.2),
   fitted to the mostly adult donors; Buckingham 2005's 29 / 53% were children and adolescents).

276. **The slow reversal (step-ACF zero crossing 50–55 vs 40 min) is in the body under Loop, not the sensor, and not insulin
   speed.** It is the same on true BG; the body's insulin action sits on the clamp literature (peak GIR ~100 min lispro, 79
   Fiasp). Turning-point counts cannot settle it, since donors' true glucose is unobserved; "more frequent small
   disturbances" is a hypothesis, not a finding.

285. **The labeler cannot size unbolused intake.** It reads an unbolused meal at ~0.43 of its grams and a bolused one at
   ~1.3, so labeled g-eq cannot recover donors' true unentered grams. The duration of unannounced rises is the like-for-like
   target. The insulin balance allows at most ~15 g/day of extra unentered intake in twins.

286. **At matched height, twins' rises peak later and fall slower than the donors', bolused or not.** Fall in the hour
   after the CGM max (40–80 mg/dL band): donors −37 / −34, twins −26 / −27. The evidenced between-person emptying spread
   (A10 `ge_var`, Samsom 2003) carries part of it but also makes lows; it stays on. Whether Samsom's delayed share fits an
   AID population is a literature question to settle before any change.

287. **Check the Elleri 2013 appearance figures before resizing the energy-limited emptying.** evidence/09 records
   56 / 100 / 153 min (25 / 50 / 75% appearance, 121 g meal), `ra_traj.py` quotes 72 / 130 / 197; the paper is paywalled.
   Appearance against meal size has no tracer measurement in T1D.

289. **Twin meal entry is drawn independently of meal size, so twins' night insulin does not follow their entered evening
   carbs** (donors +0.135 / +0.118 U per 10 g entered; twins ~0). `entry_size_b` moves it the right way but has no evidence
   of its own and removes lows; off. The donor's entry clock for snacks (`entry_clock`, `snack_entry_hours`) does not create
   evening snack entries either; off.

290. **Under Loop, faster insulin absorption removes lows; it does not make falls faster.** Heat (B15, absorption ×
     (1 + heat_a·max(0, T − 13))) at 25 °C: paired hypo-day OR 0.75 (heat_a 0.02) / 0.59 (0.04); posture off (A4b
     ablation, c297): OR 0.78, post-peak falls unchanged. So the heat–hypoglycaemia association (Diabetes Care 2026, OR 1.26
     at 25 vs 13 °C) needs another mechanism; B15 stays off and posture stays on. A candidate that speeds absorption reads
     safer here than the evidence may support.

294. **Correction-response comparisons depend on the subset; pool all lone corrections.** All lone corrections at
     150–250 mg/dL (473 twin vs 1463 donor) give change per U per ISF equal to or a little stronger than the donors' at
     60–180 min; only the flat-trend subset reads ~20% weaker. The body's insulin action is neither too late nor too small.
     Lone donor corrections are also confounded: they start in strong rises (ICE 132 vs 101; L 316).

298. **Body motion and co-located sensor error cannot be separated from CGM.** The twins' coherent fast moves (two 5-min
     steps of one sign ≥ 7 mg/dL) are within ~15% of the donors', two thirds made by the per-sensor AR(2) noise. The only
     paired-sensor record (p03, two CGMs; L 299) shares fast moves 0.75 / 0.69 vs simulated pairs 0.81 (increment r 0.60
     vs 0.65). Settling body vs sensor needs sensor-vs-reference series, not more donor CGM statistics; do not fit the
     sensor to CGM shape.

300. **`csf_w` sets the carb sensitivity's data weight separately from ISF_W, and the two use opposite conventions.** In
     `person.sample_person` ISF = settings × (data/settings)^w (w weights the data) but CSF = cal × CSF_data^(1−w) ×
     CSF_settings^w (w weights the settings). ISF_W 1.0 had silently put the CSF fully on the settings. `csf_w` default
     0.5; csf_w 1.0 (data alone) breaks the meals.

303. **Best 1981 (full text): insulin-mediated uptake is about proportional to glucose (κ ≈ 1).** The earlier 0.24 /
     0.68 / 0.78 were read from the total clearance fall, which fixed brain uptake makes; `kappa_ins` retired. κ median
     1.0. Pete (2026-10-19): weigh how important and how fundamental each match is, not the count — a sounder model may
     regress on it.

313. **Loop must be simulated exactly; a dosing difference means something is missing in the patient.** Pete
     (2026-10-19): "We should be able to simulate loop exactly ... If you see loop dosing more or less in our simulations
     than in the field, then we need to see what's missing in our simulation." Measured after meals: recorded COB and
     insulin effect match the donors'; the difference is the counteraction in hours 1–3. The replay COB over-absorption
     artefact (memory bddp07) does not apply to plant runs: the controller computes ICE live (L 307).

315. **The ice labeler's pulse g-eq under-reads long meals; use the unsegmented ICE integral.** A pulse ends early on a
     plateau, so it reads the twins' meals larger than the donors' (L 314) while the integral above the pre-meal baseline
     reads them ~15–20% smaller (donors 13.0 / 15.4 / 10.5 / 3.7 / 0.3 per 10 g over 0–6 h, total 47.4). Check the pre-meal
     baseline too (donors 53.4 vs twins 59.2 mg/dL/h; L 316).

318. **The late meal phase (TIDEPOOL-70) is this role's research, not a question for Pete.** (Pete 2026-10-19.) The gap is
     a roughly constant amount per meal across start glucose, trend and IOB (L 317–318).

330. **Score donors one 13-day block at a time, as each twin is.** A donor median over ~8 blocks has a narrower spread
     than any single window, making noisy statistics read "too wide" in the twins. `validate.compare_blocks` (used when
     `real_pilot_blocks.csv` sits beside `real_pilot.csv`): KS against one random block per donor, median p over 40
     draws. Donors' full-record TDD ac1 0.21 is 0.03–0.09 in 13-day windows.

331. **A donor's dosing strategy is per day, not per record; twins draw autobolus from `auto_day_share`.** 40 of 50
     "autobolus" donors spent ≥ 10% of days in temp-basal mode; matching strategy per day put Loop's automated total at
     1.04× the donors'. Compare dosing against the donors' same-strategy days. A noise-free sensor makes Loop's dosing
     worse, not better (the fitted noise is right for Loop).

333. **A person's level under Loop is set by what Loop aims at and cannot see in time, not by how much is eaten.**
     Cutting the low-runners' twins' intake to their donors' load (`intake_own`, Q4 meals 119 → 84 g/day) left their
     morning level unchanged (154 → 155 vs donors 124): Loop takes the difference out of the insulin.

337. **Every evidenced route to the donors' hours-2–3 meal counteraction has been tried; the late phase is the
     documented limit.** Not it (L 301–364): gastric speed and ceiling, energy accounting, fat timing and normalisation,
     protein glucose, slow share, carb sensitivity level and per donor, under-entry, unentered courses, solid speed, fast
     share, circadian classes and emptying split, activity on the gut, post-meal eating, eating by glucose, insulin speed,
     glucose effectiveness, κ, liver suppression (the twins' is shallower than Romeres', L 342). With carbs, insulin and
     labelled load matched the twins' meals still rise less (L 348). Settling it needs tracer appearance at 2–3 h for
     ordinary meals or sensor-vs-reference series. Added late glucose is answered by Loop (L 306, 320, 366).

338. **"Isolated meal" filters exclude only entered meals.** 45% of the twins' isolated breakfasts had an unentered meal
     2.5–5 h later, which made a spurious late hump. Check the truth log before reading a late meal feature.

340. **`slot_ann` is not an eating occasion's entry chance.** It is the share of the donor's labelled pulses per window
     that carry an entry, and labelled pulses include body-made rises (L 333). Calibrate entry chance on entered grams per
     window (carbs.json, both sides; `entry_win`).

359. **Refit per-donor multipliers by pooling rounds, not by iterating.** Each round re-fit on one twin's noisy ratio
     adds w × noise and widens the multipliers to the clip (naive round 2: 0.50 / 0.95 / 1.58). Pool: estimate the needed
     multiplier from every run (log(donor / twin) + log m of that run), average, clip.

363. **Fit the sensor only to sensor evidence; the FDA tables do not identify white noise or tails.** G6 FDA loss falls
     monotonically as white σ falls (set it from the donors' measurement noise, L 362); the Student-t df has no trend in
     FDA loss. The short-scale shape statistics (sd_over_mad, v_kurtosis, vol_cluster_60m, sigma_disp, acf_zero_min,
     hurst) fail together and stay the documented short-scale limit; the sensor stays as fitted (L 296–299).

364. **Spreading the same meal glucose over more hours makes meals flatter, not later.** The bolus covers the whole meal
     up front: a larger slow share or slower solid part over-covers early (lower peak, a dip), Loop doses the late part as
     it arrives, and no late rise appears (`meal_slow` 0.30 / 0.45: 3-h change ≈ 0, lows fail). The same holds for
     `ge_kcal_mult`, `ge_full_kcal` and `main_speed` (L 301, 305, 319).

368. **Loop is a fixed, known process: when patients behave differently from real life, change the patient side.** Pete
     (2026-10-19): "Loop is a fixed known process ... If patients don't behave the way in the simulator that we see in real
     life, then we need to update something on the patient side." Loop's automatic delivery / scheduled basal by CGM band
     matches the donors' (p50 0.31 / 1.06 / 1.51 / 1.84 / 2.22 / 2.62 vs 0.36 / 1.06 / 1.48 / 1.76 / 2.23 / 2.51).

370. **A fixed night term makes night insulin too regular in any form.** The donors' night need varies night to night
     with the evening (no persistence across nights, L 332); a fixed bump (`night_own`, `night_add`) or renormalised night
     level fails day / night insulin or night_cv (L 369, 373). `night_own` is off; the evening's own fat and protein
     carry the night. (fat_rel was turned off here and later restored — check current.)

376. **The donors' TDD day-to-day persistence is not in logged eating, the week or site age.** Per-day entered carbs ac1
     ≈ 0 both sides; no weekly TDD pattern; site age (3 donors with reservoirChange / prime uploads) shows no TDD trend.
     Exports carry no site-change records. TDD ac1 stays open with no named candidate (L 372, 376).

378. **The insulin budget must cover all glucose eaten.** Any glucose source added outside the intake budget (here
     protein glucose, ~12%) lifts level and TDD; `budget_pro` divides carbs eaten by (1 + pro_glc × 0.39). Add every new
     glucose source to the TDD budget.

384. **Fit a component from the literature first, then from our data (Pete 2026-10-20).** Where the literature does not
     identify a parameter (e.g. how the CGM noise level wanders over hours), fit it to the donors' data — but keep the
     component's own evidence as a constraint (see 393). (Pete 2026-10-20)

389. **The donors' 40-min CGM reversal resists every body lever tried; do not retry them.** Twins' true glucose turns at
     50–60 min whatever the body does: insulin speed (L 276), within-day SI / EGP oscillation (B4b `ultradian`, L 385),
     faster meal / bigger slow tail (L 386), longer movement bouts (L 388), loop gain (`isf_level`). The sensor's error
     processes reverse within 15 min, so cannot carry a 35-min persistence. Only a 5-min CGM-vs-YSI time series would
     decide body vs sensor.

392. **Loop sees the donors' carb absorption times.** Donor entries > 20 g: 3 h 78.6%, 0.5 h 8.6%, 5 h 5.4%; twins draw
     0.5 / 5 h on each donor's own shares (`templates.add_absorption_rates`). The 3-h meal-level gap does not come from
     Loop being told a shorter meal.

393. **A sensor fitted to donor steps must still pass its FDA accuracy tables, or it manufactures lows.** The donor-fitted
     G7 read CGM < 54 at bias −23.5 vs K213919 −9.3, so part of the matched lows were sensor error. Refit FDA-led (G7
     `hetero_q` 0.55, σ 1.3, wander 0.45, co-located σ 2.2; G6 `hetero_q` 0.6, wander 0.7 kept). A CGM that makes false
     lows biases every t < 54 comparison; check `sensor_fit` FDA cells after any sensor change.

398. **After the twins' meals Loop withholds longer; the missing lows and the low 3-h meal level are one gap.** Isolated
     bolused meals ≥ 15 g: zero-delivery 0–180 min p50 90 vs donors 65 min, Loop insulin 30–180 min 4.10 vs 4.71, low
     within 4 h 13.5 vs 16.8%. Meal glucose per entered gram and bolus per entered gram both match (L 395–396); real Loop
     runs as often after meals as at any time (decision share 0.936 vs 0.933, L 400), so it is not Loop offline. Real
     glucose 1–3 h after a meal stays higher against Loop's forecast.

402. **Adding meal glucose late does not fill the donors' 1–3 h counteraction.** Slow emptying, slow share (`meal_slow`),
     protein (`pro_glc` 0.4) all move glucose past 3 h or get answered by Loop (L 386, 399, 401–402). The tracer
     literature (Romeres 2025, Ruchi/Basu 2026) shows the liver suppressed and no late glucagon surge through 2–4 h, so no
     sized late source exists (L 403, 413).

408. **Pete: take the meal shape at the cost of the lows (2026-10-20).** The post-meal window (A12b) is on; this
     supersedes L 321 for this trade. Lows are then chased through the low-side components on their own evidence.
     (Pete 2026-10-20)

410. **A proactive defence shows as a fall that slows, not a pulse; measure it on falls (Pete).** Labelled low-side
     pulses cannot see it. On quiet falls the twins defend no more than donors; their falls reach 70 half as often
     (90–130 → < 70 in 30 min 2.0 vs 3.9%) because the fastest falls are missing (fast-fall gap, L 236–249).

416. **The fast-fall tail is not κ and not Prager's i.v. hepatic rate.** `kappa_mult` 1.5 (L 412) and `p2e_cal`
     0.025 / 0.035 leave the fall tail at p10 −25…−26 (donors −29). Prager's rates are for stepped i.v. insulin; under
     subcutaneous delivery absorption paces the hepatic signal.

434. **Once the diet is personal, every diet-driven resistance must be relative to the person's own diet.** The donor's
     TDD already paid for the donor's own diet: `macro_own` with absolute fat (or protein budget at the population ratio)
     over-reads low-carb people (mean 164.5). With `fat_rel` (and `budget_pro`, L 378) the pre-dawn trough and 24-h
     amplitude land on the donors'. Defaults on.

436. **The post-meal window likewise must move need, not add it (`ppr_rel`).** An absolute window (`ppr_a` 0.3) adds
     resistance the donor's TDD never paid for and raises the mean; normalised to mean 1 over the person's planned meals it
     gives the meal shape with the mean on the donors' (`ppr_a` 0.4 adopted).

441. **The night excess of lows is real glucose and no night-physiology lever moves it.** True glucose < 70 at 66% of
     night CGM lows (L 420). Tried and failed: night need bump `night_own` (L 421–422), GH pulses B2b (L 418, 420, 428),
     `ppr_end`, protein, evening emptying, `dawn_si` (L 439), `night_si` (L 441; adds lows). Twins' night SI climbs to 1.30
     of median by 05–06 h (no daytime resistance acts) and the night is too responsive (within-night SD 29.1 vs 23.8).
     Look at behaviour, not physiology (L 442–443).

443. **`night_pro` and `uls` are mechanisms, not fits: someone woken is awake, and Urgent Low Soon is on by default on
     Dexcom.** Without them a woken twin at 76 and falling went back to sleep (rescue only < `treat_thr` 70). With both:
     minutes per low 20 (donors 20), night pre-emptive rises 0.234 vs 0.222 per night (L 458). Defaults on.

444. **A different draw of people moves the matched count by up to 6; score close calls on two draws.** Single-draw
     differences of 1–3 are noise. An arm that changes the count or a statistic by less than the draw scatter is scored
     on seed0 1000 and 5000 before adoption; components adopted on mechanism and evidence stand on those.

445. **Twins regress toward the middle: tight-control donors' twins run 30–90 mg/dL above them on more insulin.** Twin vs
     donor mean corr ~0.4; gap rises with donor TIR (+0.50). Pooled statistics hide it because high and low gaps cancel.
     Behaviour volume is not missing (high-gap twins enter and bolus more than their donors).

451. **Donors' corrections look twice as strong as the twins' because donors correct at a peak about to end.** Donors
     correct during a rise (+14 mg/dL over the prior 15 min vs twins +5–7); Loop then withholds on the fall. Correction
     hazard by trend matches. Twins' labelled rises are ~15–20% flatter at the peak.

454. **The tight-donor level gap survives seven checks; do not repeat them.** Ruled out: per-donor body ISF (`lvl_own`,
     L 447: pins 43 of 121 donors at the 0.5 / 2.0 bounds, contradicting the yardstick), unlogged load (`unl_own`, L 448–450:
     Loop absorbs removed glucose but not added), correction rate and trend response (451), gut speed (452: twins at
     Elleri's fast end), sensor (453: noise steepens CGM climbs, ratio 1.69), the labeller's insulin term (454: the body's
     insulin acts later than Loop's model, share by 60 min 0.12 vs 0.22). Left: what donors do with no record.

455. **Score twin delivery by record rate, as eda reads the donors' records.** eda's delivery statistics read each
     record's RATE (`dists._effective_basal_rate`, `rate_uhr`), though Omnipod pods round short low temps to 0 pulses;
     `validate._record_delivery` now lays each record's rate over its span. Delivery rows in lessons 406–454 used volume
     scoring. Like for like the twins' Loop commands 8–14% more insulin than the donors'.

456. **The twins need ~5–8% more insulin than their donors; it is not meal glucose or rate-vs-volume TDD.** The ice
     extractor builds TDD from record volumes (`extract.insulin_grid`), so the body is built on what the donor received.
     `csf_lvl` 1.0 does not remove it. Open with the level gap (L 445).

457. **Persistent day-level SI (`day_rho` 0.4) does not move TDD persistence or volatility dispersion.** An 8% day-level
     SI is small next to eating in a day's insulin (same-day eaten–delivered corr 0.85). Default stays 0.

459. **Pete (2026-10-20): the simulator is usable with LoopEval.** Known gaps are documented limits, not blockers. On
     c446_npu no frontier candidate lifts (aIRC lift −0.92, C30 −0.55, C31 −0.05); handoff
     docs/handoffs/2026-10-16-additive-candidates-on-sim.md. (Pete 2026-10-20)

469. **The twins' insulin excess is small by volume and comes from the level gap.** Paired with its own donor by
   delivered volume (ice steps both sides, G7), the twin runs +3% (automatic +5.8%, manual −3.4%). The +7 / +12% read at
   record rate adds the twins' larger pulse-rounding loss (pods keep 90.5% of programmed basal vs the donors' 94.2%) and
   the draw. The intake budget closes (eaten ×1.02–1.03 of budget, L 467), and dividing out the modulators' SI mean
   (`si_norm`, L 468) lowered glucose but not insulin. So `med_nonzero`, `zero_frac` and `tdd` close with the level gap,
   not separately (L 465). Compare TDD like for like: same definition, same window.

473. **Loop's neutral glucose (where automatic delivery reaches scheduled basal) is set by the controller, not the body's
   basal need.** Fitting each body's basal share to its donor's neutral glucose (`basal_fit`, three rounds, both draws)
   drove the share to its bound with no change in the neutral gap or tracking; not adopted, switch off. The donors'
   higher, wider neutral points (128.9 / 136.8 / 142.5 by gap tercile vs twins ~117–122) are not bolus IOB, missed
   cycles, pump-clock shifts (L 474–476), and sensor noise covers 2–5 mg/dL of it (L 477). No body lever left there.

481. **The liver's meal EGP nadir and the 3-h meal level conflict; the nadir is held at ~0.84 for the meal shape.** The
   donors' post-meal rise (Pete's priority, L 408) needs meal-time resistance that reaches the liver; Romeres 2025's
   tracer nadir (0.56 at 160 min) needs the liver suppressed through the meal. Ruled out: `egp_share` 0.95 (raises
   the meal and level, L 479); `--disable egp_sat` (fixes level and TDD but discards Rizza 1981's evidenced cap, L 480);
   `ppr_periph` + `fat_periph` (nadir on time, meal tail collapses, L 481, 502); plus `meal_k` 0.7 (L 482). Switches
   kept, off.

486. **A Loop user's Nightscout record exports to the pilot spec and matches the same person's Tidepool export.**
   `loop-eval export` writes the four streams; `nightscout_export.py` adds the Tidepool-only parts (glucose
   representation, labelled temp / suspend, inferred scheduled basal marked `inferred: true`, schedules as set with
   override windows, decision times, disruptions, ICE side tables, manifest). On a two-month overlap: IOB MAE ~0.05 U,
   glucose / boluses / carbs identical, 32 of 34 donor statistics within 1%. Rules the comparison forced: keep schedules
   as set (not override-baked), trim override windows to the export window, merge contiguous equal-value schedule
   segments, keep Tidepool's mmol round trip, skip fill gaps under a minute. Nightscout reads ~⅓ more Loop-offline time
   (status uploads are not backfilled).

487. **Trap: the ICE pipeline counted a week of pre-window boluses as corrections.** pull_bolus_decisions starts 7 days
   early and the labeller clamped those rows to the first step's glucose, inflating corrections 8–20% on the pilot and
   moving the median correction glucose. Fixed in ice 9b2c009 (ice LESSONS 128) at its next relabel; the pilot
   templates' correction columns (corrections_per_day, corr_bg_med, corr_rate_d, corr_bg_d, corr_*) predate the fix.

488. **`sigma_meas` is fragile; read its KS result as weak evidence.** It is the intercept of the structure-function
   fit: dropping 9 of ~17,000 readings moves its block median by a quarter, and the mmol round trip moves it 15%.

489. **A twin can be fitted to one Nightscout user; read its meal response on like-sized entries.** Template from the
   Nightscout export, the correction fit in two rounds (L 249), 16 seeds × 14 days against the user's own 13-day blocks:
   about two thirds of statistics match. `csf_geq_mult` must compare entries ≥ 30 g: a full-meals-only user reads half
   the twins' g-eq per gram because twins also enter snacks. Age moves the twin through body weight (the U/kg prior
   changes at 18); a known weight (`bw_kg`) is better.

490. **A `--data-dir` export of a Nightscout site replays bit-identically to `--nightscout-url`.** JSONFileDataSource
   now keeps doses starting up to 2 h before the window, as the live source does. By design a data dir also loads
   decision_times.csv, disruptions.csv and carb_revisions.json. The live path's first replay differs from later ones
   (DataCache writes whole-second timestamps; IOB up to 0.1 U); `loop-eval export` keeps milliseconds.

491. **Entry chance by meal size must be normalised per eating window, not per day.** `entry_size_own` (column
   `entry_b`, off) makes entry chance ∝ (grams / usual grams for that kind and window)^entry_b, normalised once on a
   ≥ 90-day dry run of the plan; the whole-day form over-entered evenings. Off is bit-identical. Columns `bw_kg` (known
   weight, 3% spread) and `unl_mult` (per-person unlogged-eating multiplier; treat as a twin setting, not a fitted
   value). Cohort adoption needs `entry_b` fitted per donor and a two-draw check.

492. **Rank runs by the weighted gap score (`score.py`), not the KS count.** Gap = median difference in units of the
   donors' between-window spread (10–90% width / 2.563) plus half the log ratio of spreads, bootstrap SE; tiers weighted
   3 / 2 / 1 by how directly a mismatch moves a candidate's TIR / t<54 delta. The KS count's p 0.05 cut depends on
   sample size. The draw moves the score ~0.04 (tier 1 ~0.07): score close calls on two draws. The tier weights are a
   judgement; the check that would earn them is still owed.

493. **The change test: score the response to settings edits by the structural slope, not by regressing field change on
   predicted change.** OLS slope of the outcome change on the insulin index log(basal ratio) − log(ISF ratio), CR and
   target changes as covariates; on the field side also the need shift and pre level. A plain regression is attenuated
   by prediction noise and favours a noisy generator. The response is damped mainly by SG and κ (mean) and the proactive
   defence (lows). Use `beh_set` on `Person.traits` to override behaviour traits from a driver: the plant runs in its own
   process, so patching world in the driver never reaches it. Run dir runs/2026-10-22-additive-dial-damping/.

494. **The activity response is measured with Pemberton 2025's matched-window design, and the donors' workout extract
   must be deduplicated.** ΔCGM over a bout's first 20 min less matched windows of the same person (start ±15 mg/dL,
   ROC ±0.5 mg/dL/min, IOB ±0.5 U), excluding logged entries only on both sides. The extract repeats each workout up to
   7×: dedupe on (alias, start, duration). Rows `act_net20` / `act_net20_hi` (tier 1) and the life rows come from
   `lifestats.py`; they need the labelling step and `lifestats sim <run>` after a cohort. `ice_dip_*` (unexplained
   falls, 70 mg/dL/h threshold) cannot see an activity effect; fit everyday activity on the matched response rows.

497. **Activity rows: use the same IOB on both sides, and they cannot rank exercise changes on 112 twins.** The donors'
   bout IOB is the ice extractor's total IOB (basal included); the twins' must be too (bug fixed cc32d1f; Loop's
   net-of-basal `candidateIOB` halved it). The pooled rows move by their draw scatter (SE 0.2–0.4 in gap units) under
   every arm; read them pooled over both draws. Most donors with workouts record them rarely (median 0.15 / week), so
   habit rows use only consistent recorders (11 donors). Rejected or mixed: `ex_time`, a later C4 surge
   (`ex_surge_thr`), `ex_no_eat`. The twins' sessions are lifted by eating around them (60% of sessions).

499. **A change that moves its own target toward the donors often costs the outcome rows other components were fitted
   to.** Seen with `sleep_own`, `ex_time`, `ex_no_eat`, `sensor_act_k` (all off). Adopting one needs the component
   review (refit drifted components on their own evidence) before the two-draw comparison, not instead of it.

512. **The missing fast falls are on the fall side of the meal in the body, not the pulse, the sensor or a single SI
   term.** The twins' true glucose falls fast ~0.09 times a day; most of their CGM fast falls are sensor-made (they
   rebound), while the donors' are a mix, so adding sensor noise would recreate the false-lows trap (L 393, 510).
   Ruled out: single SI-chain levers (`ppr_a`, `ins_p2`, `sg_mult`, `ge_pm`, `ge_circ`, fat, `glucotox`, L 498), liver
   timing (L 502), slower late appearance (L 508), the meal end shape (L 509), exercise boost on insulin action
   (`ex_post`, L 507), `sensor_act_k` (one draw only, L 498). Matching pulse size (`csf_lvl` 1.2) raises fast falls only
   as the peak mix predicts; at a given pulse twins still fall fast half as often. The rise speed is set by the energy
   ceiling (Vmax 3 kcal/min), not the main parcel's rate constants.

513. **Twins drawing variability from cohort trait distributions put it on the wrong person; model the rest from the
   donor's own data (Pete 2026-10-27).** On lg13, cohort ICE amplitudes matched by time scale but per person only the
   level carried over (quiet mean ρ 0.85); volatility did not (block ρ 0.03, fast ρ 0.19), and volatility drives TIR and
   CV on both sides. Pete's direction: hold the well-evidenced components fixed and model the rest of the variability
   from the donors' own data, causal source or not. Matching the quiet ICE mean is no test of the level (it is mostly
   settings ISF × basal activity). Removing the replaced components barely lowers volatility: the twins' variability
   comes from the core (unlogged pulses, sensor, behaviour) (L 514). (Pete 2026-10-27.)

519. **Check per-person fits held out: fit on the donor's odd 13-day blocks, score on the even ones.** The residual level
   is a stable trait: held out, mean ρ 0.93 (ceiling 0.96; lg13 0.45), TIR 0.80. Use `LVL_BLOCKS=odd` and `heldout.py`
   before reading in-sample person-level ρ as prediction.

521. **The reference's short meal tail is a shift of the whole 3-h distribution, not a narrow spread; it trades against
   the lows.** Per-meal 3-h change on f4 sits ~10 mg/dL below the donors' at every percentile with the donors' IQR. An
   entry-anchored down drive (`resid_drop_*`, off) adds fast falls but takes the tail. Restoring A4c (L 522) or the
   replaced modulators (L 545) recovers part of the tail but pushes lows past the donors' even after a level refit:
   tail and lows trade through the same sensitivity variability. At 112 twins meal_d3h is noisy by several mg/dL (L 517):
   read it on two draws.

525. **Building twins for a new pool (x, e) takes, in order:** (1) per-donor sensor family and age from the warehouse
   (not in the ice extracts); (2) `templates.build_pilot` with the pool root; (3) the `add_*` chain on the pool root;
   (4) `fit_body --regression` and per-donor carb sensitivity (`csf_geq`, pooled over rounds); (5) the residual: a core
   run, `resid_tools/fit_resid.py`, three level rounds on two draws. Then `arm2.py` on the pool's edits. Only step 1
   needs the warehouse. (Tools: `resid_tools/pool/` — `pull_sensor_age.py`, `build_template.py`, `make_events.py`.)

531. **Trap: change-test arms must use per-event seeds.** `sample_person` jitters the donor row per seed (±10% TDD, ISF,
   …); running every event on seeds 1000–1003 gave every twin the same jitter, a common level bias (+9 to +27 mg/dL)
   that moved arms unequally. Use `arm2.py` ARM_EVSEED (seed offset by md5(eid), both arms share it) and `cohort`
   `tmpl_cycle` (twin i takes template row seed mod n) so a fitting round covers every donor once. Change tests before
   L 532 are unreliable on size and the control-level split.

540. **The twins' damped response to an edit is not their correction habit or the cohort sensitivity level.** Ruled
   out: the residual (L 532–535), gating corrections on Loop's recommendation (`corr_rec_gate`, L 538), a correction
   rate responding to the settings (`corr_x_beta`, L 539), and `isf_level` 1.3 (the intake budget is the donor's insulin
   total, so a more sensitive body eats more). The donors do hand over to Loop after a more aggressive edit (corrections
   −44% per log unit, L 537), but it is too small a share of insulin to matter. All switches off.

542. **Change-test scorer and which twin to use.** `score_change.py` adjusts the field for d_ice − 3.5·x (NEED_MECH):
   the field's need shift contains the ICE extractor's own +3–4 mg/dL/h per log unit that the twins share (ICE uses the
   settings ISF the edit changes, L 533, 541). With it (and per-event seeds, L 532), field / twin TIR per log unit is lg13
   0.95 / 0.64 / 1.03 on pilot / x / e, f4 (level-only residual) 0.76 / 1.27 on x / e, sd3 1.32 / 1.29 / 1.39. Use lg13
   for the size of a change, f4 when the twin must start at its donor's level, sd3 for each person's state and spread.
   The residual gives the control-level split the field's sign on all three pools but does not rank edits better.
   Harness in `patient_sim/resid_tools/` (arm2.py with ARM_EVSEED / ARM_EVM, score_change.py, twin_dice.py).

544. **With current components a twin's spread is carried faithfully only by meal size, and meal size damps its response
   to edits.** The twins' spread barely follows control level (tight donors' twins too wide, loose too narrow, L 528), so
   an additive per-person drive cannot fix the tight end (fast-residual CV fit L 524, `si_var_own` L 543). `csf_sd_mult`
   carries spread (SD ρ 0.92) but damps the TIR response (L 534); the hybrid keeps response and level but carries about
   half the spread (ρ 0.52). The replaced modulators carry change ranking (L 534). Next named candidate: tight donors'
   bolus timing and pre-meal dosing (F3).

547. **Fitting intake to the donor's labelled load (`intake_mult`, in1) sizes TIR and the control-level split best on
   the pilot but its lows barely answer an edit.** The twins eat 10–15% more labelled glucose than their donors at every
   control level (L 546). in1: TIR field / twin 0.84, tight − rest −1.87 (field −7.18), t54 response a tenth of the
   field's. Not adopted over sd3; a candidate twin for change work beside lg13.

**Lessons 548–579 were consolidated on 2026-11-01** (the session that produced them added 813 lines to a 734-line
file). Every standing finding and number is kept; the route was cut. Numbers merged into their neighbours, so older
citations resolve here: 549, 555 → 548 · 552 → 550 · 557 → 553 · 564 → 554 · 562 → 561 · 566 → 565 · 569, 570 → 568 ·
572, 573 → 571 · 574 → 575 · 576, 578, 579 → 577. The originals are in the commit history (548–579, 2026-11-01).

548. **Glucose effectiveness split into named parts (`ge_split`) is sounder but not adopted.** A1's lumped SG(G − Gb)
   replaced by A1a tissue uptake 0.0022 dL/kg/min both sides (Del Prato 1997 T1D at basal insulin), A1b the liver's own
   suppression above Gb only (UVA T1D kp2 lnN(0.0038, 0.40); absent at mild lows in T1D, Mevorach 2000), A1c brain uptake
   1 mg/kg/min falling ∝ G below 81 (Best 1981, Hovorka 2004). Paired on sd3: score 0.370 → 0.396 / 0.454 → 0.511; lows
   per day 1.08 → 1.38 / 1.21 → 1.58 (donors 1.00). Counter-regulation needs no refit — the share of lows reaching 54
   stays on the donors' and CRmax × 1.5 / 2.2 pushes it under. The extra lows are shallow, from the 81–Gb band, so the
   fix belongs in A1. It also read better than sd3 on the natural experiments, but that advantage does **not** survive
   the C4 fix (L 553, 556): on the new reference its cohort cost is larger (0.385 / 0.518) and its tight − rest
   contrasts are no better. Superseded; use the reference for low-side change work. Run dir
   runs/2026-10-31-additive-gesplit/. A1c ALONE is a live candidate — see L 561.

550. **Coupling audit (Pete 2026-10-31): counter-regulation and the pump / site chain are modulated by nothing but
   their own clock.** Every driver acts through a named channel; the matrix is COMPONENTS.md § Couplings. Tested and
   rejected, do not repeat: activity → emptying (`ex_gut`, L 344), hyperglycaemic slowing (`ge_hyper`, L 91 — it caps
   the peak), exercise → sensor error (`sensor_act_k`, L 498), post-hypoglycaemic resistance (L 55 — the rebound
   already matches), sleep → counter-regulation (`cr_sleep` 0.5: evidenced by Banarer 2003 but no benefit, its
   apparent tier-1 gain is in the unrankable activity rows and t54 worsens on both draws). Unmodelled and evidenced:
   exercise → counter-regulation, exercise → site failure, and the aerobic side of exercise → EGP.

551. **Entries do not measure eating during a workout, and the exercise gap is the SIZE of the fall.** Donors enter
   carbs during a workout at 0.18× the clock-hour rate (L 244), but exercise is where logging fails, so the statistic
   cannot say whether they ate. Measured on the shape every CGM shows (`donor_rev.py`, `match_rev.py`, `mets_rev.py`
   in runs/2026-11-01-additive-exeat): donors' entry-free workouts reverse after the nadir as often as the twins that
   EAT (≥ 15 mg/dL: 0.50 vs 0.52 / 0.56, against 0.35 / 0.37 for twins that eat nothing), and sessions with a logged
   entry are no different (0.56), so logged carbs are not what lifts them.
   **Match both sides or the number is meaningless** (C1's uptake is ∝ glucose). On identical filters — 25–60 min,
   3.5–7 METs, nothing eaten or entered — and twins pooled over both draws, drop to the mid-session nadir:

   | start | 70–120 | 120–160 | 160–200 | 200–400 | pooled |
   |---|---|---|---|---|---|
   | donors | 4 | **34** | 43 | 80 | **34** |
   | twins | 3 | **18** | 38 | 52 | **17** |
   | diff [95% CI] | +1 [−9, +10] | **+15 [+7, +35]** | +6 [−15, +36] | +28 [−18, +62] | **+17 [+6, +29]** |

   Insulin is not the explanation: at 120–160 delivery over the session is 1.03× usual for donors and 1.05–1.19× for
   twins, with IOB matched, so what is left is C1 / C2. By METs the gap is an INTENSITY one — none at 2–3.5
   (−8 [−22, +11]), +28 [+8, +47] at 5–7 and +28 [+8, +41] above 7. Twins also run 18% of sessions at ≥ 7 METs against
   the donors' 37%. Sizing C1 / C2 does not close it (α 2.6 leaves the pooled drop at 16 / 14, C1 × 1.5 reaches 22 / 21
   against 35; C1 ×3 and α 6 were already rejected in L 494 for breaking the measured insulin dependence).

553. **C4's surge threshold was firing at moderate effort; keyed in absolute METs at 8, with the session cap, it is
   settled.** 0.6 of VO2-reserve is ~5.8 METs at the median METmax — exactly where the twins' fall collapsed — while
   the donors' drop deepens through 7–9 METs and C4's own Pemberton table has them deepest at 6–8 (−21.5) and positive
   only at ≥ 8 (+1.2). Threshold 0.9 of reserve scored 0.353 / 0.437 against sd3's 0.370 / 0.454, better on both draws
   with no component drift. But %reserve CANNOT reproduce the ≥ 8 band once METmax is consistent (for METmax 11, 8 METs
   is 0.70 of reserve): keyed in absolute METs the sign flips, so `ex_surge_mets` 8.0 is the default. The size stays 28
   mg/kg/min — validated once the band has enough bouts (+1.8 against +1.2 at n 40); L 557's inconclusive refit was
   reading a band of 18–25 bouts whose value swings from +13 to +2 with n, not with the parameter.

554. **A quarter of simulated workouts were efforts no one can sustain.** `ex_mets` draws session METs from the donors'
   workouts but converts on THIS twin's METmax, drawn independently: 19% of sessions sat at 1.00 of aerobic reserve for
   a median 39 min, and a session that fires C4's surge does not fall at all (drop 0 against 20 below the threshold).
   `ex_cap_fit` (default) caps intensity by what a person holds for that length (`_sus`: ~0.87 at 20 min, 0.775 at 40,
   0.72 at 60) and raises METmax to what their own sessions need, since session METs are measured and METmax is only a
   prior. Capping alone leaves almost no hard session (3 bouts at ≥ 8 METs against the donors' 51 of 171), so the two
   go together. `ex_headroom` 1.5 (off) restores the session tail — tuning METmax to the MEAN clipped every session
   above it — and is needed whenever the ≥ 8 MET band is read.

556. **Adopted as one change, on soundness: `ex_cap_fit` with C4 keyed to 8 absolute METs.** Score 0.364 / 0.416 against
   st9's 0.353 / 0.437 — a wash, and neutral on the natural experiments too (t70 tight − rest +0.63 [−0.17, +1.59]
   against +0.83 [+0.11, +1.70]). Kept because it removes a demonstrated impossibility and keys a term to the units its
   evidence is measured in; the matched drop goes 20 / 16 → 27 / 24 (donors 35) with no component drift. **Pete
   2026-11-01: level on the statistics and on prediction power but better explained is a win.** The two-draw rule
   governs claims of IMPROVEMENT, not this.

558. **A12b was mis-calibrated against its own target; `ppr_a` 0.4 → 0.6.** `meal_d3_p50` is A12b's donor-fitted target
   and sat at ratio 0.58; 0.6 puts it at 0.97. meal_d3h 25 / 26 → 33 / 31 (donors 38) on both draws, bg_mean closer on
   both; 0.8 overshoots and is worse on both. **Costs TIR on both draws** (0.136 → 0.246, 0.030 → 0.181) and the net
   score is mixed (0.340 / 0.444). **Best arm of its series on change prediction**: t70 tight +1.29 [+0.68, +1.86] and
   tight − rest +1.03 [+0.40, +1.64] against the field's +4.35 / +4.27, with the pooled response slightly smaller — it
   sharpens WHO responds more than HOW MUCH. **Caveat (L 573):** the two 3-h meal statistics disagree about it — the
   scored row improves 25 → 33 toward 38 while the per-entry 3-h change moves away, 26 / 23 → 32 / 30 against the
   donors' 28, because the labeller selects meals that rose. Read the tail claim as definition-dependent.

559. **The excess time below 70 is shallow lows that linger, and the depth mix is already right.** Like for like on the
   reported CGM (`depth.py`, `recover.py` in runs/2026-11-01-additive-lows): minutes/day < 70 donors 35.0, twins
   45.0 / 56.2; excursions 1.36 vs 1.57 / 1.79; median length 17.5 vs 21.8 / 22.6; share never reaching 60 matched
   (0.60 vs 0.59 / 0.61). Matched on nadir depth the defect is confined to the shallow end: at a 60–70 nadir the rise
   30 min out is donors +26, twins +21, and the excursion lasts 10 min against 15 — **about +5 mg/dL of missing
   recovery**. At 54–60 recovery agrees; below 54 the twins rebound HARDER (+55 against +41), so rescue behaviour is
   not the lever. The fall INTO a low is gentler at every depth (L 494, 512).

560. **A9 cannot supply it, in either direction: the term is worth at most 2.4 mg/dL over 30 min.** CRmax lnN(0.137,
   0.5) mg/kg/min at FULL activation for 30 min is 0.137 × 30 ÷ V_G 1.68 = 2.4 mg/dL, against the +5 needed, and it is
   not fully activated at 60–70 at any threshold. `cr_g` 65 → 70 / 72 moves the 30-min rise +21 → +22 and leaves the
   length at 15 min; `cr_mult` 0.7 / 0.5 on top of `ge_spare` leaves `p_reach54` at 0.17–0.18 against 0.212. CRmax is
   fitted to the low DEPTHS (L 394), which match, so it is not free either. **Check whether a term is large enough
   before tuning where it switches on.**

561. **`ge_spare` (A1c alone) fixes the excess time below 70 but not the recovery, and trades duration for depth —
   PETE'S CALL.** The one part of L 548's split aimed at L 559, on the lumped SG, with the liver's support below Gb
   untouched. Sized first: 3.5 mg/dL over 30 min at G 65.

   | | Donors | ad3-era | `ge_spare` |
   |---|---|---|---|
   | t70 | 1.60 | 1.97 / 2.16 | **1.67 / 1.71** |
   | tir | 71.9 | 68.9 / 70.2 | **69.8 / 71.0** |
   | lows per day | 1.00 | 1.04 / 1.17 | 1.00 / 1.04 |
   | p_reach54 | 0.212 | 0.200 | **0.167 / 0.170** |
   | rise 30 min from a 60–70 nadir | +26 | +21 / +20 | +21 / +20 (unchanged) |

   It works for a different reason than intended — at 0.118 mg/dL/min it resists the DESCENT more than it speeds the
   climb out. Three draws favour it (better on 2 of 3 and on the mean), and A9 cannot refit the depth it costs (L 560).
   A genuine duration-vs-depth choice on the safety-relevant side, not a pending calibration. Off meanwhile.

563. **The missing shallow-low recovery is not insulin, and points at a glucose-dependent hepatic response below Gb.**
   Through the ice extractor's total IOB on both sides (`resid_tools/iob_at_peak.py` family): at a 60–70 nadir the
   donors hold 1.59 U and rise +26 in 30 min; the twins hold **1.09 U** and rise +20. With a third less insulin aboard
   they should climb out FASTER. In net appearance the gap is **0.34 mg/kg/min at G 65**. A6's EGP answers insulin only;
   nothing raises hepatic output when glucose falls below Gb, and A1b was deliberately built as suppression above Gb
   citing Mevorach 2000 — measured under a hyperinsulinaemic clamp, not at basal insulin. **Correction to an earlier
   draft:** Bruce 2025 (Diabetes 74(6):898, PMID 39508871, closed) and Del Prato 1997 (Diabetologia 40(6):687, PMID
   9222649, closed) both RAISE glucose above basal — they are A1b's and A1a's evidence and would NOT size this. It
   needs a study that lowers glucose below basal at basal insulin in T1D.

565. **C1 keyed to absolute work rate improves the 6–8 MET band but breaks the ≥ 8 one: the donors' curve is a regime
   switch smooth terms cannot make.** Muscle glucose uptake follows the work done, not the strain relative to the
   ceiling, so %reserve gave a fit person LESS uptake for the same 7 METs (×0.55 at METmax 12 against ×1.00 at 7).
   `ex_abs` (off) moves the 6–8 band −14.4 / −6.1 → −17.8 / −7.4 (donors −21.5) on both draws but drives ≥ 8 to
   −13.3 / −7.1 where the donors RISE. The donors fall deepest at 6–8 and rise at ≥ 8 — a switch inside two METs — so
   any smooth setting that deepens one deepens the other. A narrower surge ramp is the form that serves both:
   `ex_surge_width` 0.75 with `ex_abs` and `ex_headroom` reads **+0.9 against the donors' +1.2** at n 38.
   **Exercise-faithful configuration** (not the default, since every step toward C4's table costs the weighted score):
   `--enable ex_abs --set ex_headroom=1.5,ex_surge_width=0.75`. Use it whenever the response to a workout matters.
   Still short: the 6–8 band, which is C1 / C2's size at moderate intensity and needs a measured per-person capacity.

567. **Score close calls on THREE draws — seed0 1000, 5000 and 9000 — and read the mean.** Every arm of 2026-11-01
   scored better on draw 1 than draw 2, and nearly every candidate read worse on draw 1 and better on draw 2; ten
   changes failing the same way on the same draw are not ten independent facts. Draws 2 and 3 agree with each other
   and **draw 1 is the outlier** (ad3: 0.321 against 0.425 / 0.430), because the reference lineage was developed on
   seed0 1000. L 444's two-draw rule still rejects noise, but with 1000 as one of the two it also protects that fit.
   Where the three disagree, discount 1000. Several rejections of 2026-11-01 were rejecting draw-1 overfit.

568. **The residual's diurnal shape was flat and wrong; weighting it to waking hours is the reference's largest single
   gain and the only change of the day better on all three draws.** The worst tier-2 row was `ice_dip_day`
   (unexplained falls: twins 1.42 / 1.67 against 0.692) and its diagnostic was the clock — only 44.9% of the twins'
   dips by day against the donors' 66%, so the excess is at NIGHT, which rules out everyday activity (the row's
   designated target, L 494). `resid_diurnal` weights the fast and block parts by sqrt(1 + k·cos(2π(t − 15 h)/24 h));
   cos has zero mean, so **mean(w²) = 1 exactly** and each person's fitted amplitudes still hold — only WHEN the
   variance appears changes. At k 0.9 (reference **ad3**): score 0.340 / 0.444 / 0.430 → **0.321 / 0.425 / 0.410**,
   ice_dip_day → 1.42 / 1.50 / 1.33, day share 0.449 → 0.472 / 0.469 / 0.500, t70 1.97 / 2.16 → 1.72 / 1.90, tir
   68.9 / 70.2 → 69.8 / 71.1, night insulin CV 30.3 / 33.3 → 30.7 / 34.6. On the natural experiments it takes the
   tight − rest TIR and mean contrasts (−1.63, +0.93 against the field's −7.18, +1.65) with t70 +0.74 [+0.12, +1.39].
   - **Why it worked where a dozen size changes were level: it fixed a DISTRIBUTION, not a magnitude.** Nothing was
     re-sized, so nothing had to be traded. **Look for distributional errors before reaching for a size.**
   - **But the trick only reaches symmetric statistics.** Redistributing the residual across the MEAL cycle
     (`resid_meal`, off) is a null — the residual is skewed toward RISES (`resid_skew` 0.7), so moving it into the
     post-meal window makes post-meal rises, not falls, and `entry_fast_fall` is one-sided. **Check a target's sign
     structure before redistributing variance at it.** The asymmetric version, `resid_drop_p` 0.3, does move it
     (4.8 / 5.6 / 5.7 → 7.1 / 7.9 / 5.9 against 14.3) but spends ~5 points of the nearly-closed meal tail to buy ~2.4
     of it, on all three draws. L 521's rejection stands.

571. **The meal-shape gap is a SECOND WAVE, not elevation at 3 h, and it is sized.** Per carb entry ≥ 20 g over the
   following 4 h, same code both sides (`resid_tools/meal_shape2.py`; 37,694 donor entries):

   | | peak at | rise to peak | fall in the 90 min after | second rise | both limbs |
   |---|---|---|---|---|---|
   | donors | 85 min | 64.0 | **57.0** | **28.0** | **0.43** |
   | twins | 90–95 | 63 / 61 | 47 / 43 | 18 / 20 | 0.28 / 0.29 |

   The rise and peak timing already match; the second oscillation does not — donors fall 10–14 mg/dL further then rise
   8–10 further. **This dissolves the apparent contradiction** between fast falls and the meal tail: on this statistic
   the donors are NOT higher at 3 h (28 against the twins' 30–32; the scored `meal_d3h` is a per-person median over
   LABELLED meals, a different measurement), so nothing contradictory is being asked — the model needs more amplitude
   in one oscillation, and one mechanism can serve both limbs.
   - **Neither existing hook supplies it.** A10's slow share (`meal_slow` 0.30) lowers the peak to 57 instead of
     deepening the trough — mass at kmin 0.008 dribbles out under the whole curve. A10c, a delayed pulse at the MAIN
     rate (`meal_wave2`, off), preserves the peak (64) and lifts the second rise (22 / 23), and its delay must be
     sized off the measured curve — at 100 min it lands ON the peak and the 3-h change overshoots to 34 / 36, at 180
     min it lands after the trough (31 / 31). But **the trough never moves** (46 / 43), so it is not
     appearance-limited.
   - **Trap:** donor carb entries are keyed `grams` in `carbs.json`, not `carbInput`; the wrong key gives 0 g for every
     entry and a size filter then drops them all with no error.

575. **At MATCHED insulin spend the post-meal trough is a pure 75% potency gap — and the closed loop does not absorb a
   body change in that window.** Through the ice extractor on both sides (`resid_tools/iob_at_peak.py`, entries
   ≥ 20 g):

   | 90 min after the meal peak | IOB spent | fall | mg/dL per U |
   |---|---|---|---|
   | donors | **1.98 U** | **57.0** | **28.8** |
   | ad0 (`ppr_a` 0.4) | **1.98 U** | 43.0 | 21.7 |
   | pp6 (`ppr_a` 0.6) | 1.68 U | 41.5 | 24.7 |

   ad0 spends exactly the donors' 1.98 U and falls 43 against 57 — pure potency, no dose difference, at a similar peak
   height. Raising `ppr_a` (LOWERING post-meal sensitivity) made Loop spend **less**, not more, so the
   compensation hypothesis is refuted and the trough IS reachable from the body side. Ruled out in that window:
   appearance (A10c, ~1 mg/dL), A12b (a 30% effective-sensitivity swing, ~1 mg/dL), dose (matched), Loop's response.
   What remains is the body's glucose-lowering per unit of insulin ACTION — A5's disposal chain or the ISF the body is
   given. This is the quantified form of L 512, and the direction is that the twins need MORE post-meal potency.
   - **κ is NOT the channel** (diagnostic, `run_kp.sh`): κ scales insulin-mediated uptake with (G − Gb), so it acts
     only at high glucose and would have dodged the `si_norm` trade entirely. At `kappa_mult` 1.8 — an 80% steepening
     — the fall after the peak is 45 / 43 against ad3's 47 / 43 and the donors' 57, i.e. **unmoved**, while the rise to
     the peak drops to 58 / 56 from 63 / 61 (donors 64). Scores 0.353 / 0.412 / 0.414 against 0.321 / 0.425 / 0.410.
   - **The pattern across every failure on this gap, and the constraint it gives:** anything that adds glucose-lowering
     at high glucose (κ) or removes appearance (A10c, `meal_slow`) **lowers the PEAK instead of deepening the FALL**.
     A GLUCOSE-localised effect cannot steepen the descent, because it acts just as strongly during the ascent. Only a
     TIME-localised one can — more insulin action after the peak specifically. A12b is time-localised but
     mean-preserving, so Loop doses against the new baseline and it nets out (L 573). **So the remaining candidate is
     insulin action peaking LATER — A5's p2, the one lever of L 512's list never tested against this statistic.**
     p2 0.025 is the lispro clamp fit, so a slower value needs its own justification; tested as a diagnostic, 0.018 /
     0.015 leave the fall at 46 / 44 / 46 against 47 / 43 — **also unmoved**. So every candidate of L 512's list is now
     eliminated by measurement: appearance, glucose-dependence (κ), post-meal sensitivity (A12b), dose, the
     controller's response, and action timing (p2).
   - **The sensor inflates the fall on BOTH sides and does not dilute the comparison** (`resid_tools/true_vs_cgm.py`,
     `meal_shape2.py` split by family). Our sensor adds 24–35% of apparent fall (G7 most: +11.5 / +11.9; G6
     +8.5 / +4.0; twins' CGM 48 / 45 against their TRUE 37.9 / 34.2). The donors' falls show the SAME family ordering
     — G7 58.0, G6 54.0, Libre 3 45.0 — consistent with similar amplification on their side. Family-matched the gap
     is G6 10–16 and G7 9–12 mg/dL in CGM terms, and applying the twins' own per-family amplification to the donors'
     CGM puts it at 10–13 in estimated truth terms. **So the gap is real, body-side, and about the same size however
     it is read.** An earlier draft of this lesson claimed the sensor diluted a 9 mg/dL body change to ~7 and so
     explained the null levers — that was wrong: the amplification is similar on both sides, so a body change
     propagates to the CGM comparison roughly intact. The nulls are genuine nulls.
     Always split this statistic by sensor family: the twins' G7 share differs from the donors', and G7 amplifies
     about three times as much as G6 on one draw.
   - **The sharpest form: the deficit is in the fall / rise RATIO, which is invariant to every lever tested.** Donors
     fall 57 on a rise of 64 — a ratio of **0.89**. Every twin arm sits at **0.70–0.78** whatever was changed:

     | | rise | fall | ratio |
     |---|---|---|---|
     | donors | 64 | 57 | **0.89** |
     | ad3 | 63 / 61 | 47 / 43 | 0.75 / 0.70 |
     | κ 1.8 | 58 | 45 | 0.78 |
     | p2 0.018 | 61 | 46 | 0.75 |
     | `meal_k` 1.35 | 63 | 48 | 0.76 |
     | Vmax × 1.2 / × 1.35 | 68 / 71 | 49 / 51 | 0.72 / 0.72 |
     | A10c wave, 180 min | 64 | 46 | 0.72 |
     | `meal_slow` 0.30 | 57 | 43 | 0.75 |

     The energy ceiling (the lever L 512 names for the rise, and the only one that moves the fall at all) scales BOTH
     limbs, so it raises the rise past the donors' (68 / 71 against 64) and the 3-h change with it (33 / 34 against 28)
     while the ratio stays at 0.72. `meal_k` does nothing because the ceiling is rate-limiting for a normal meal, as
     L 512 already said — that run should not have been made.
     **So the missing mechanism must break the ratio: more fall for the SAME rise.** Appearance scale, emptying speed,
     uptake's glucose-dependence, insulin-action timing, post-meal sensitivity and dose are all ratio-preserving, which
     is why six families of lever each read as null. A ratio-breaking term has to act asymmetrically in TIME around
     the peak and not be mean-preserving (A12b is, so Loop doses against its baseline and it nets out). Nothing in the
     model does that. **Read this ratio, not the fall, when testing the next candidate.**
   - **Candidate physiology considered and set aside analytically, so it is not re-derived:** a meal-induced reduction
     in hepatic output confined to the post-peak window would break the ratio, and the incretin route (GLP-1 / GIP
     suppressing glucagon, peaking 60–90 min after the meal) has the right timing. But it points the WRONG way for
     T1D: post-meal glucagon is inappropriately HIGH in T1D (lost alpha-cell suppression), and with subcutaneous
     insulin there is no portal insulin gradient, so the donors should have LESS post-meal hepatic suppression than a
     non-diabetic, not more. The same objection rules out a portal-signal term. So the ratio-breaking mechanism is
     **not** identified, and the search should start from what is measurable rather than from a named hormone: the
     donors' own fall / rise ratio by meal size, time of day, bolus timing relative to the meal, and insulin type
     (the per-donor models differ, L 445's cohort). **Measured (`resid_tools/ratio_by.py`, 33,138 donor meals ≥ 20 g
     with a rise ≥ 20 mg/dL, 190 donors): the ratio is a DOSING-TIMING statistic as much as a physiological one.**

     | bolus offset from the entry | n | rise | fall | ratio |
     |---|---|---|---|---|
     | 20–60 min BEFORE | 1,477 | 63 | 59 | **0.90** |
     | 5–20 before | 906 | 66 | 59 | 0.85 |
     | at the meal (± 5) | 24,554 | 69 | 57 | 0.79 |
     | 5–20 after | 2,078 | 80 | 60 | 0.74 |
     | 20–60 after | 2,976 | 97 | 65 | 0.68 |
     | no bolus within an hour | 1,141 | — | — | **0.62** |

     Pre-bolusing raises the ratio to 0.90 and late or absent bolusing drops it to 0.62–0.68 — a spread of 0.28, which
     dwarfs the twins' 0.11–0.19 deficit. Meal size matters too (0.82 at 20–35 g falling to 0.64 above 75 g); the clock
     hour does not (0.76–0.79 throughout).
     **So before any mechanism is built, the twins' bolus-timing and meal-size distributions must be compared with the
     donors' and the ratio read WITHIN those strata.** A twin population that boluses later or eats larger meals than
     its donors would show this whole deficit with no physiological difference at all — and F3 draws bolus timing from
     each donor's measured lead, so the test is whether that reproduction is faithful in the tail, not on average.
     **Method note:** 0.89 is the ratio OF MEDIANS (57 / 64) while the per-meal median ratio here is 0.78 on the same
     donors. Both are valid, they are not the same number, and the twin comparison must use whichever is quoted —
     mixing them would invent or hide a gap.
   - **Stratified (`resid_tools/ratio_twin.py`): the gap is roughly 60% physiology and 40% a behaviour-reproduction
     defect, and the defect is specific.** Bolus-timing shares, twins against donors:

     | | pre (−60, −5] | at (−5, 5] | late (5, 60] | **none within an hour** |
     |---|---|---|---|---|
     | donors | 0.07 | **0.74** | 0.15 | 0.03 |
     | twins | 0.06 / 0.07 | 0.61 / 0.59 | 0.19 / 0.17 | 0.055 (corrected) |

     Meal size matches (34 / 33 g against 35), so size is not involved. Within the dominant "at the meal" stratum the
     twins read 0.71 / 0.67 against the donors' 0.79 — **a residual gap of about 0.08–0.12.**
   - **The composition explanation was a detection artifact, and checking it reversed the split**
     (`resid_tools/bol_check.py`). A delivered-stream threshold (> max(0.2 U, 4× basal) in a minute) said 11–13% of
     the twins' meals ≥ 20 g had no bolus; `bolus_requests`, which records user boluses directly, says **5–6%**
     against the donors' 3%. So the threshold over-counted by about two-fold by missing small boluses. With the
     corrected share the composition contributes (0.055 − 0.03) × (0.79 − 0.62) ≈ **0.004 of the pooled 0.11–0.16 gap,
     about 3% — not the 40% an earlier draft of this lesson claimed.** The within-stratum 0.08–0.12 is essentially the
     whole deficit, so **the post-meal ratio gap IS physiology**, and a ratio-breaking mechanism is genuinely needed.
     **Trap:** never detect boluses in a sim run from the delivered stream by threshold — basal, small boluses and
     pump quantisation make it unreliable. Use `truth["bolus_requests"]` (f > 0 is a ratio of Loop's recommendation,
     f ≤ −0.05 absolute units).
   - **How big the gap really is, and the one thing that cannot be settled from our data.** The sensor amplifies the
     two limbs VERY unequally: on the twins, rise CGM 64 / 61 against truth 59.8 / 56.9 (+7%), fall CGM 48 / 45
     against truth 37.9 / 34.2 (+27 / +32%). So the sensor ADDS 0.12–0.14 to the ratio (truth 0.63 / 0.60 → CGM
     0.75 / 0.74), and because G7 lengthens its lag ×1.5 while glucose falls (D1), the amplification GROWS with fall
     rate. The donors fall steeper, so their sensor adds more than 0.12, putting their TRUE ratio below 0.77 against
     the twins' 0.63 — a true gap of under 0.14 and plausibly nearer 0.06–0.11, against the 0.14 the CGM comparison
     shows. **The CGM comparison therefore exaggerates this gap by an unknown amount, and it cannot be pinned down
     without donor truth, which does not exist.** Quote the gap as 0.08–0.12 at the meal with that caveat attached;
     do not size a mechanism to the CGM number.

577. **TDD, not bg_mean, is the diagnostic for a core sensitivity error: `resid_m` absorbs core level errors.**
   `si_norm` is a deliberate cohort-wide 8% cut in sensitivity (L 468, 516: the yardstick averages over the donor's
   real life, so the life modulators should average 1 around it, and 0.92 reproduces the level they held while
   disabled) — about a third of L 575's potency gap, and deliberate. Raising it to 1.0 improves TDD and TIR on all
   three draws (the first confirmation that the potency deficit and the twins' standing 5–8% insulin surplus, L 445–456,
   share one cause) but drops the level, because `resid_m` was fitted at 0.92. Three rounds of `lvl_resid.py`
   (converging to twin–donor mean ρ 0.99) restore it:

   | | donors | ad3 (0.92) | 0.96 + refit | 1.0 + refit |
   |---|---|---|---|---|
   | mean score | — | 0.385 | **0.373** | **0.372** |
   | bg_mean gap | — | 0.092 / 0.263 / 0.076 | **0.055 / 0.090 / 0.031** | 0.072 / 0.073 / 0.052 |
   | tir gap | — | 0.208 / 0.112 / 0.309 | **0.057 / 0.070 / 0.173** | 0.072 / 0.070 / 0.149 |
   | tdd gap | — | **0.169 / 0.262 / 0.201** | 0.115 / 0.255 / 0.237 | 0.202 / 0.290 / 0.209 |
   | t70 | 1.599 | **1.72 / 1.90 / 1.49** | 2.14 / 2.17 / 1.82 | 2.14 / 2.11 / 1.84 |
   | t70 edit-response ratio | 1.0 | 3.32 | — | **2.09** |

   - **The architecture.** `resid_m` is fitted per person to the donor's glucose level, so it absorbs whatever the
     core gets wrong about level — including a core sensitivity error. The 8% returned to the core came straight back
     out as residual drive. So a potency deficit does not show in the level statistics; it shows in **TDD**. Read
     `resid_m`'s size as a measure of what the core is missing.
   - **And `resid_m` does not scale with insulin, so it damps the response to a settings edit.** Carrying the 8% in
     the core gives the **least damped change response of any arm measured** (t70 ratio 2.09 against ad3's 3.32, mean
     ratio back to 1.97) while ad2 / ad3's residual-heavy form keeps the better control-level contrasts. The core
     carries how MUCH a person responds; `resid_m` sharpens WHO does.
   - **PETE'S CALL, and tuning will not settle it:** the trade is roughly linear, so 0.96 does not dominate (mean
     score 0.373 against 1.0's 0.372). **1.0 is the principled end** — the only value with no unexplained cohort-wide
     cut, and `si_norm` exists only to stand in for life modulators that are OFF in this reference; if they are ever
     switched on it should be 1.0 by construction. All three are one flag and one template apart, so keeping two arms
     for the two uses (L 542) costs a template file.

580. **An adopted default that could not be switched off, and the session's gain re-stated on three draws.** Checking
   that sd3 was still recoverable (it is asserted in the overlay and in L 556) found that **`--disable ex_cap_fit` was
   a silent no-op**: the trait defaults True since 2026-11-01 while `world.py` had a set-True-only branch, so there
   was no path to False and the "sd3 reversal" still ran with the session cap on, scoring 0.350 instead of 0.370.
   Fixed to honour an explicit False; the reversal now reproduces sd3 bit-for-bit on draw 1. The other three adopted
   defaults (`resid_diurnal`, `ppr_a`, `ex_surge_mets`) are floats with an `else` default and revert correctly —
   `ex_cap_fit` was the only boolean and the only broken one. **When adopting a boolean default, check the revert path
   runs, not just that the flag exists.**
   - **The completed comparison** (sd3 had never been run on draw 3, which was introduced mid-session):

     | | d1 (1000) | d2 (5000) | d3 (9000) | mean |
     |---|---|---|---|---|
     | sd3 | 0.370 | 0.454 | 0.420 | 0.415 |
     | **ad3** | **0.321** | **0.425** | **0.410** | **0.385** |
     | gain | 0.049 | 0.029 | **0.010** | 0.030 |
     | tier-1 gain | 0.135 | 0.110 | 0.075 | — |

     ad3 is better on all three draws, **but the margin shrinks from the development draw to the fresh one: 0.049 →
     0.029 → 0.010.** That is L 567's draw-1 effect visible in the session's own result, so quote the out-of-sample
     gain as **~0.010–0.029, not 0.049**. Tier 1 holds up far better than the aggregate (0.075 on the fresh draw),
     which is the more meaningful claim: the rows that carry physiological meaning improved, the weighted total much
     less than draw 1 suggested.
   - **Decomposed on the fresh draw, the two kinds of change behave completely differently** (all three runs already
     existed; no new compute):

     | draw 3 (seed0 9000, never used for development) | score | tier 1 |
     |---|---|---|
     | sd3 | 0.420 | 0.236 |
     | + C4 keying fix + `ppr_a` 0.6 (= ad2) | **0.430** | **0.154** |
     | + `resid_diurnal` 0.9 (= ad3) | **0.410** | 0.161 |

     The two SOUNDNESS adoptions — C4 keyed to absolute METs with the session cap, and A12b at its own target — cost
     **0.010 of weighted score** on a draw they were never tuned on, while cutting **tier 1 from 0.236 to 0.154**.
     The one DISTRIBUTIONAL adoption (`resid_diurnal`) pays 0.020 of score and leaves tier 1 flat. So the whole
     aggregate gain on the fresh draw comes from the distributional fix, and the soundness adoptions buy tier-1
     accuracy at a small aggregate cost — exactly what L 556 and L 558 said they were doing, now confirmed
     out-of-sample rather than on the development draw. **That is the honest summary of 2026-11-01: the components
     are more correct and the weighted score is barely moved; only the distributional fix improved both.**
581. **The day-level AR(1) does not reach `ac1`: TDD's day-to-day persistence is not driven by the residual, which
   bounds L 568's distributional lesson.** The residual's day part was drawn independently per day, so nothing carried
   across days and TDD had no persistence (`ac1` −0.02 / −0.03 / −0.04 against the donors' +0.091, failing on both
   draws). `resid_day_ar` 0.35 makes it AR(1) — verified exactly variance-preserving (SD 1.009, lag-1 +0.356) — so
   only the dependence changes. The control reproduces ad3 exactly and the arm does change the traces (score 0.321 →
   0.326 on draw 1), but **`ac1` does not move at all: −0.022 → −0.022, −0.029 → −0.029, −0.044 → −0.044.**
   Score 0.326 / 0.421 / 0.407 against ad3's 0.321 / 0.425 / 0.410 — level on the mean (0.385 both), tier 1 marginally
   better on all three (0.105 / 0.287 / 0.156). Not adopted.
   - **Why, and the boundary it draws.** TDD's day-to-day variation is dominated by what the person eats and how Loop
     answers it, not by the residual's day level, whose amplitude is small beside that. So **a distributional fix only
     reaches a statistic the residual actually drives** — the diurnal fix worked because unexplained ICE dips ARE the
     residual's own signature (L 568), while `ac1` is a property of the eating-and-dosing loop. Before redistributing
     the residual at a target, check that the residual is what moves that target: `resid_meal` failed on the sign
     structure (L 568) and this one fails on attribution. The remaining route to `ac1` is day-to-day persistence in
     EATING (F1's meal sizes or F2's entry rates), which is a behaviour trait, not a residual property.
582. **The "principled package" (life modulators on + `si_norm` 1.0) does NOT fix `ac1` and scores worse than
   `si_norm` 1.0 alone: restoring day-to-day sensitivity VARIATION without persistence buys nothing for TDD.**
   Tested as L 581 specified — `day, stress, illness, menstrual` enabled, `si_norm` 1.0, three rounds of the level
   refit (converging to twin–donor mean ρ 0.98):

   | | donors | ad3 | `si_norm` 1.0 (lv3) | **package (lf3)** |
   |---|---|---|---|---|
   | score d1 / d2 / d3 | — | 0.321 / 0.425 / 0.410 | 0.333 / 0.373 / 0.409 | 0.341 / 0.402 / 0.416 |
   | **mean score** | — | 0.385 | **0.372** | 0.386 |
   | bg_mean gap | — | 0.092 / 0.263 / 0.076 | 0.072 / 0.073 / 0.052 | **0.015 / 0.094 / 0.019** |
   | tir gap | — | 0.208 / 0.112 / 0.309 | 0.072 / 0.070 / 0.149 | **0.074 / 0.035 / 0.230** |
   | tdd gap | — | **0.169 / 0.262 / 0.201** | 0.202 / 0.290 / 0.209 | 0.213 / 0.305 / 0.225 |
   | **ac1** | **+0.091** | −0.022 / −0.029 / −0.044 | — | −0.072 / −0.014 / −0.051 |
   | night_cv | 35.36 | 30.7 / 34.6 / 31.2 | — | 30.4 / 33.3 / 29.2 |

   - **`ac1` is unmoved**, which was the package's whole motivation. `day_rho` defaults to 0, so switching `day` on
     restores day-to-day sensitivity VARIATION but not its PERSISTENCE — flagged before the run, and confirmed. TDD
     persistence needs persistence, and the code comment on `day_rho` says the field's lag-1 of 0.4 "must come from
     named factors", so raising it would be fitting an unevidenced parameter to a target. **`ac1` stays open and its
     route is NOT this.**
   - **It gives the best glucose LEVEL of any arm** (bg_mean gaps 0.015 / 0.094 / 0.019 — essentially exact) and the
     best TIR on two draws, but costs TDD on all three and night_cv on two, and its mean score (0.386) is WORSE than
     `si_norm` 1.0 alone (0.372) and level with ad3 (0.385).
   - **So the "principled" configuration is not the better one.** Switching the modulators on costs score without the
     benefit it was run for. Pete's `si_norm` choice therefore stands exactly as L 577 and L 579 framed it — core
     versus residual, trade roughly linear — and the life modulators are a SEPARATE question with their own cost,
     not a reason to prefer 1.0. L 581's unification was wrong: the two items do not resolve together.
583. **`ac1` must be read against −0.086, not 0, and on that basis the twins sit exactly at the independent-day null
   while the donors carry a real +0.18 of persistence.** A lag-1 autocorrelation of 13–14 INDEPENDENT daily values has
   expectation **−0.086** (short-series bias), not zero, with SD 0.27 per block. The scored row is a median over ~200
   donor blocks, so its SE is ~0.019 and the medians are well determined — the row IS informative, contrary to a
   hypothesis I was about to record.

   | | `ac1` | vs the independent-day null (−0.086) |
   |---|---|---|
   | donors | **+0.091** | **+0.18** |
   | twins (ad3, three draws) | −0.022 / −0.029 / −0.044 | +0.06 / +0.06 / +0.04 |

   So the twins have essentially no day-to-day persistence, which is exactly what the model implies (the residual's
   day level is independent and `day_rho` is 0), and the donors have a real one. **The target is +0.18 in correlation
   units, not the 0.13 the raw difference suggests**, and a candidate must be read against −0.086 or it will look
   better than it is. This also explains why `resid_day_ar` 0.35 (L 581) should have shown up and did not: the day
   level does not drive TDD, so the persistence never reached the statistic.
   - **Where the persistence can come from, by what persists in the model:** illness episodes (1.5–15 days) and the
     menstrual cycle (21–38 days) both persist but are too rare or too slow to carry lag-1 within a 14-day window,
     and enabling them changed nothing (L 582). Site life (E5, a 3-day sawtooth in absorption) is already on and also
     changed nothing. So the model's existing multi-day structure is insufficient, and `day_rho` is unevidenced. The
     honest reading is that **`ac1` needs a named multi-day factor the model does not have**, and the code comment on
     `day_rho` says exactly that — the field's lag-1 of 0.4 "must come from named factors".
   - **And `intake_rho` is NOT the bug — it works, and delivers about half of what is needed**
     (`resid_tools/intake_ac.py`, measured directly on the twins' own daily totals):

     | lag-1 autocorrelation | measured | above the −0.086 null |
     |---|---|---|
     | twins' daily CARBS | +0.069 / +0.043 | **+0.155 / +0.129** |
     | twins' daily INSULIN | +0.020 / −0.042 | +0.106 / +0.044 |
     | donors' TDD row | +0.091 | **+0.177** |

     A true ρ of 0.29 on 13 days reads about 0.15 after the short-series bias, so the carb figure confirms
     `intake_rho` (Levitsky 2017) is doing its job.
   - **But intake persistence does NOT propagate to TDD, which corrects the reading above and closes the row.**
     `act_rho` 0.4 (L 584: day-to-day persistence of everyday activity, Gaussian copula keeping the gamma marginal
     exactly, aimed at need via C2's 600-min delayed sensitivity) raised CARB persistence by +0.04 on both draws
     (+0.069 / +0.043 → +0.108 / +0.073) — activity drives the intake budget, so that coupling is real — and produced
     **no systematic change in insulin persistence** (+0.020 / −0.042 → −0.034 / −0.008) or in `ac1`
     (−0.022 / −0.029 / −0.044 → −0.061 / −0.012 / −0.037). Score level on the mean (0.385 both).
     So a +0.04 rise in carb persistence buys nothing in TDD, and the earlier inference that `intake_rho` supplies
     "about half" the donors' persistence was wrong — it supplies the carb persistence, which does not reach the
     insulin total. Most likely TDD is dominated by components with no day-to-day structure at all (basal is roughly
     half of it), diluting any day-level driver below detection in a 13-day block.
   - **The donors' persistence is in BOTH limbs, and their BASAL carries the most of it**
     (`resid_tools/tdd_decomp.py`, 204 donors, a median 128 days each — long enough that the short-series bias is
     negligible):

     | donors' daily insulin | share of TDD | day-to-day CV | lag-1 autocorr |
     |---|---|---|---|
     | basal | 0.37 | **0.230** | **+0.303** |
     | bolus | 0.63 | 0.348 | +0.265 |
     | total | — | — | +0.251 |

     So day-to-day persistence is not a meal phenomenon the twins are missing: the donors' **basal** varies with a CV
     of 0.23 and persists at +0.30, and it is 37% of their TDD. (Their delivered basal is Loop-modulated, so part of
     that variation is the controller answering glucose rather than need — which is itself reproducible, since the
     twins run the same controller.) **The four null twin-side mechanisms all acted on meals, activity or the
     residual; none of them touched basal.**
   - **Verdict on `ac1`: not reachable through the day-level drivers tried, and the next step is the basal split.**
     Four mechanisms null (the residual's day level, L 581; the life modulators with B3's own AR(1), L 582; everyday
     activity, above; and `intake_rho`, which moves carbs but not insulin). The measurement that would close it is the
     twins' own basal/bolus decomposition against the table above — their basal CV and its lag-1 — which needs the
     delivery split from `trace.json` or the plant stream, NOT a threshold on `truth["delivered"]` (L 575's trap).
     If the twins' basal CV is far below 0.23, that is the defect and it is a named one.
585. **`ac1`'s target was measured over 128-day records and is three times too large; the part a fixed-settings twin
   could reproduce is +0.118, the twins already carry +0.064 of it, and the remaining gap is in the bolus limb.**
   L 584's basal/bolus table (+0.303 / +0.265 / +0.251) is a **long-record** lag-1: it contains the drift between
   13-day blocks — settings eras, seasonal need — which a 14-day twin neither can nor should reproduce. Measured like
   for like, within 13-day blocks (`resid_tools/tdd_blocks.py`, 205 donors, a median 9 blocks each):

   | donors' daily insulin | long record | within 13 days | drift removed |
   |---|---|---|---|
   | basal | +0.305 | **+0.075** | +0.115 |
   | bolus | +0.265 | **+0.066** | +0.084 |
   | total | +0.253 | **+0.085** | +0.104 |

   The within-block total (+0.085) is the scored row's donor value (+0.091), which confirms the score was always
   measuring within-block and that **three quarters of what I decomposed was drift**. L 584's qualitative reading
   survives (the persistence is in both limbs, about equally); its sizes do not.
   - **Half of what remains is the donors' SETTINGS, not their bodies.** A basal or ISF edit persists by construction
     — every day after it shares the new level — and an override lasting days does the same. Pooled over
     block-demeaned adjacent day pairs (`resid_tools/tdd_clean_ac.py`; demeaning inside a 13-day block puts this
     estimator's null at about −0.083 too), split by whether either day carries a settings change or >30 min of
     override:

     | limb | all pairs | clean pairs | edit / override pairs |
     |---|---|---|---|
     | basal | +0.111 above null | **+0.063** | +0.189 |
     | bolus | +0.177 | **+0.166** | +0.191 |
     | total | +0.139 | **+0.118** | +0.169 |

     The **basal** limb's persistence is three times smaller on clean days: it is mostly the schedule changing, which
     is why no body mechanism reached it. The **bolus** limb is untouched by the cut, so it is genuine. **The honest
     target for a twin holding one era and running no overrides is +0.118, against the +0.177 recorded in L 583.**
   - **The genuine part is day-level glucose, and the twins already carry 60% of it.** It is not entered carbs
     (donors' daily carbs persist at only +0.066 above null within a block, while their bolus persists at +0.166 —
     the twins have that inversion the other way round, carbs +0.155 and insulin +0.106). It shows instead as a day
     that runs high being followed by a day that runs high: donors' daily mean glucose **+0.168** above null on clean
     days, twins **+0.105** (ad3) and +0.094 (dr2). Remaining gap about +0.06.
   - **And no sensitivity-amplitude arm can close it, because the transmission is capped.** `day_rho` 0.45 on B3's
     intrinsic day factor (`day_sd` 0.08, the 6–15% repeat-clamp evidence) scored level with ad3 (0.338 / 0.387 /
     0.427 against 0.321 / 0.425 / 0.410, mean 0.384 vs 0.385) and moved twin basal persistence by +0.031 / −0.018.
     The chain, measured on the twins' own `truth` (scratchpad `trans.py`): the day factor is about half the variance
     of the daily-mean SI series, so a ρ of 0.45 realizes a lag-1 of +0.051 there; that series reaches delivered
     insulin at **r −0.32**, i.e. 10% of variance. A day-level sensitivity driver can therefore contribute at most
     about **+0.02** of delivered-insulin persistence whatever ρ is — below the +0.05 gap. Reaching it by amplitude
     would need a day-to-day SI CV near 25%, far outside the clamp evidence.
   - **Verdict: `ac1` is closed as a body target.** Five mechanisms null (residual day level L 581, life modulators
     L 582, `act_rho` and `intake_rho` L 584, `day_rho` here); the target is a third of what was recorded; two thirds
     of the reproducible part is already carried; and the obvious lever's ceiling is below the remainder. The row
     stays on the scorecard as a known limit, not a defect to chase. `day_rho` stays 0 (unevidenced), `act_rho` 0.

586. **Measure a donor statistic the same way on both sides, or it will invent a defect: five times in one thread a
   measurement of mine, not the model, was the thing that was wrong.** Chasing the L 585 question — which scored statistics
   the donors' settings contaminate — produced one real negative and one lesson about measurement.
   - **Settings contamination does NOT explain the other failing rows.** `resid_tools/clean_blocks.py` dates every
     block in `real_pilot_blocks.csv` by replaying `real_stats`' walk and flags edit days and override hours. A
     clean-versus-contaminated median split looked dramatic (`acf_zero_min` 45.0 clean against 40.0, −0.33 block IQR;
     `hurst_short`, `night_cv`, `med_nonzero`, `bg_cv` all past 0.15), **but within-donor every effect is |r| ≤ 0.10**
     — the split was comparing different people, since the donors who edit and override are not the same donors. Only
     override HOURS carry anything, weakly: v_sd +0.10, t70 +0.09, lows/day +0.08, zero_frac +0.08 (overrides get used
     in weeks with more lows, plausibly reacting to them). So **retargeting the scorecard to clean blocks is not
     justified**, and `ac1`'s basal limb stays the one place settings matter, where the effect is within-person and
     structural — a level change persists by construction, which a block-median split cannot see.
   - **Then the override thread, and the three errors in order.** (1) Counting `truth["sent_overrides"]` against the
     donors' full record gave a twin median of 0.0 against 6.0: **that field is the REACTIVE class only**
     (world.py:728). The planned windows reach the controller through `loopeval_io._override_windows`, which writes
     `beh.overrides` into the twin's own synthetic `therapy.json` — the same field the donor measurement reads.
     (2) Dividing a donor's window count by the span of their override RECORDS instead of their export span inflated
     the donor rate by ~1.5× for anyone whose overrides cluster in part of the record. (3) Taking the donors'
     "never override" share over their whole ~128-day record (19%) and comparing it with a 14-day twin (38%) is the
     L 585 error again — over 14-day blocks the donors' share is 42%.
   - **(4) And a median over per-person medians that folded in the people with NO window as length 0** — 43 of 112
     twins — which read 41 min where the correct figure is 72. Four errors, one family: both sides of a comparison
     must be built the same way, over the same window length, with the same denominator and the same empty handling.
   - **Measured properly, blocked to 14 days, the rate is right and the length is 9% short, not 60%:**

     | per 14 days | donors (1791 blocks) | twins (ad3) |
     |---|---|---|
     | all windows | median 2.0, mean 12.0 | median 3.0, mean 8.9 |
     | windows > 30 min | 1.0, mean 8.4 | 2.0, mean 7.1 |
     | override hours | 2.0, mean **26.0** | 3.3, mean **14.0** |
     | median window length | 65 min all / **79 min over >= 5 min** | **72 min** |
     | blocks with no override at all | 42% | 38% |

     Counts, hours at the median and the zero share all match or slightly exceed the donors — the trait is already the
     donor's own (18% of templates have all three class rates zero against the donors' 19%, rate median 5.0 per 14 d
     against 3.9). Two real gaps remain. **Length, by 9%**: the right donor figure is the one over windows the model
     could produce, since `_override` clips at 15 min and can never emit a sub-5-min record — 79 min, against the
     twins' 72. **And the long tail**: mean override hours 14.0 against 26.0, with 8% of donor windows over 4 h.
     (`_override_windows` also clips 15% of twin windows at a following window's start, halving them to 31 min from 68
     — that one is faithful to Loop, where a new override replaces the running one, and is not a defect.)
   - **The fix that pays is the comparability one, not the spread.** Dropping sub-5-min records from the per-class
     duration fit lifts `ov_less_h` from 1.42 to 1.88 h, and that alone (`ov0`) scores **0.332 / 0.394 / 0.391**
     against ad3's 0.321 / 0.425 / 0.410 — better on both fresh draws, worse only on draw 1, mean **0.372 against
     0.385**. The gain lands where the mechanism predicts: more time at reduced needs, so Loop commands less —
     bg_mean 0.263 -> 0.119 and TDD 0.262 -> 0.177 on draw 2. Realized length goes 72 -> 83 min against the donors' 79.
   - **(5) And one more, verifying the adoption: `trace.json`'s md5 is not an identity check.** Two identical
     invocations of the same frozen code give byte-different `trace.json` — key order and float formatting — with
     every section's content and the whole trajectory identical. Compare `truth.pkl`'s `truth.bg`, which is bit-stable
     and also invariant to `--n` and `--par` (each person is drawn and seeded from `seed0 + i` alone). On that
     instrument the reversal is exact: the new default with the new templates reproduces `ov0` to 0.00e+00 on true BG.
   - **`ov_dur_own` (each class's own log-duration SD, 0.70-0.78, instead of the fixed 0.6) is score-neutral**:
     0.324 / 0.391 / 0.408, mean 0.374 against `ov0`'s 0.372. It is better explained, but it moves the share of twins
     with no window at all from 42% to 27% on draw 2 against the donors' 42%, so it is not free. Judge it on the
     natural experiments.

587. **The person already sees what the controller shows, and the obvious next use of it — displayed IOB as a brake on
   correcting — is contradicted by the donors.** (Pete asked whether the behaviour model should have visibility of the
   forecast or IOB a controller presents.)
   - **What it already sees.** `Behavior.minute(m, reading, state)` is handed `state["iob"]` and `state["rec_bolus"]`.
     IOB is used in the proactive snack, which projects `cgm + 30 * trend − ISF * IOB` — a one-step forecast built from
     what Loop displays. Loop's recommendation scales every meal bolus (`bolus_requests` is a ratio of it) and gates
     corrections under `corr_rec_gate`. So the identified display channels are in.
   - **Where there is no term at all: the correction decision.** It fires on `cgm > corr_thr`, trend, a refractory
     `corr_wait` and the person's own `p_correct` — nothing about IOB. The prior worth testing is anti-stacking: a user
     who sees 4 U on board and a forecast coming down withholds. That prior also predicts relief for two documented
     limits, the twins' 5–8% insulin surplus and their excess lows.
   - **Measured, it is false** (`resid_tools/corr_vs_iob.py`). Manual-correction hazard by IOB tercile, compared inside
     a cell of (donor, glucose band, 2-h mean glucose tercile, trend sign), away from meals and from any recent manual
     bolus:

     | controls | 150–180 | 180–220 | 220–300 | paired |
     |---|---|---|---|---|
     | ≥ 60 min since last manual bolus | 4.1× | 4.5× | 6.0× | p 5e-60 |
     | + waking 08–22, ≥ 180 min since | 1.8× | 5.5× | 3.0× | p 9e-24, +0.73 corrections/day |

     At matched glucose, trajectory and time of day the donors correct **2–5× MORE** with insulin on board, not less.
     Adding an IOB brake would move the model away from the data; adding the amplifier the data shows would raise a TDD
     that is already 5–8% too high. The model's current silence sits between the two.
   - **Why the observational test cannot settle it, and what that implies.** IOB is endogenous: at the same glucose and
     the same 2-h history, more IOB means the controller has been dosing harder, which marks unannounced food or a
     stubborn high — exactly the occasions a person notices and tops up. So in donor data IOB is a proxy for an active
     situation, and its sign is dominated by that, not by what the display does to the decision. **A display effect is
     only identifiable where the displayed quantity is the thing being responded to**, which is the recommendation
     (accepted as a fraction) — and that channel is already modelled. A forecast term would face the same problem:
     Loop's eventual-BG is a function of the same glucose and insulin the behaviour already reads, so fitting a
     response to it from donor data would re-fit the trajectory, not the display.
   - **So: no new IOB or forecast term in the correction limb on this evidence.** What would settle it is data where
     the display varies independently of the situation — a controller change that alters what is shown without altering
     the dosing, or a donor's own before/after at a display change.

588. **The twins' low-side eating carries the donors' carbohydrate but in finer grain, and the one low-side size never
   fitted to the donor is the proactive snack.** Reached from the post-meal fall / rise ratio: it tracks bolus timing
   over a 0.28 spread (L 575), so the twins' timing MIX could reproduce the whole 0.11–0.19 deficit with identical
   physiology. Four measurements, each narrowing it, and two of them wrong first.
   - **The timing mix matches.** On the donors' own strata (`ratio_by.py` counts automatic boluses too, so the twin
     side must — which rules out `bolus_requests`, the person's requests only; boluses come from `trace.json`'s tagged
     `delivery[]`, never a threshold on `truth["delivered"]`): at-the-meal share 0.77 / 0.72 against 0.74, pre 0.03
     against 0.07, late 0.10 / 0.09 against 0.15. Within every stratum the twins still sit below the donors (at the
     meal 0.74 / 0.68 against 0.79), which is L 575's residual, so the ratio is not a timing artefact.
   - **But "no bolus within ±60 min of a ≥ 20 g meal" is 0.10 / 0.16 against the donors' 0.03** — and that stratum has
     the donors' lowest ratio (0.62), so it is a genuine composition term. Of the twins' meals that requested a bolus
     and received nothing (6%), **97% asked for Loop's recommendation at ratio 1.00 and 67% were entered below
     100 mg/dL** (49% below 80), against 17% / 5% for the delivered ones. Loop was right to give nothing: the carbs
     were covering a low. So the composition term is low-glucose eating, not a dosing fault.
   - **Exposure removed, the divergence is one band.** Carb entries per HOUR spent in each band — donors 0.084 /
     0.122 / 0.123 / 0.144 for < 80 / 80–120 / 120–180 / > 180, twins 0.189 / 0.133 / 0.123 / 0.111 and 0.255 / 0.163 /
     0.149 / 0.139. The donors' eagerness is nearly flat in glucose; the twins have a spike below 80 and match
     everywhere else. (Entries per day match overall, 3.04 / 3.62 against 3.29 — the band mix is what differs.)
   - **Two errors on the way, both the L 586 family.** A per-donor rate taken over only the donors with ≥ 10 low-glucose
     entries selected on the very quantity being compared and read 0.30/day where all 182 donors give 0.11. And
     comparing the twins' TRUE eating events with the donors' LABELLED pulses mixes granularities: the labeller merges
     acts, so it showed low-side eating "1.9–2.1× too frequent at half the size" where labelled-to-labelled gives
     **1.23× and 0.80×**. Compare labelled with labelled (`meals_labeled.csv` is the same labeller).
   - **What survives, like for like:** labelled pulses starting below 80 run 0.672 / 0.690 per hour below 80 against
     the donors' 0.548, at 24 / 26 g against 30 g, with the rescue share matching (0.37 / 0.40 against 0.34) and the
     carbohydrate per hour below 80 **identical** (16.1 / 17.9 against 16.4 g). The right amount, in finer grain.
   - **The lever is `pro_grams`, a fixed `lj(12, 0.4)` for everyone**, while `treat_grams` has always come from the
     donor (`rescue_size_med`). The donors' labelled non-rescue low-onset pulses are **31 g** (p25 28, p75 36); a
     twin's 12 g snack reads 24–26 g through the same labeller, so eaten grams per labelled gram at a low onset is
     **0.49** and the donor value corresponds to ~15 g eaten. `pro_g_own` sets it per person from the new template
     column `low_pro_g` (p50 15.3 g, p10 11.2, p90 21.1 — a spread where there was one constant).
   - **Result: the low side moves as predicted, and the carbohydrate is the cost.** `pro_g_own` (size only, 12 ->
     ~15 g) improves **tier 1 on all three draws** — 0.178 / 0.218 / 0.197 to 0.155 / 0.210 / 0.181 — with the low
     rows moving exactly where the mechanism says: draw 1 **t70 1.803 -> 1.597 against the donors' 1.599** (gap 0.139
     -> 0.040) and P(reach 54) 0.200 -> 0.217 against 0.212 (0.112 -> 0.056); draw 3 t54 gap 0.114 -> 0.074 and
     P(reach 54) 0.367 -> 0.261. **But it does not pay for itself**: carbohydrate per hour below 80 rises ~25%, so
     TDD goes 0.103 -> 0.230 and 0.239 -> 0.304, bg_mean with it, tier 2 degrades and the weighted score loses
     (0.359 / 0.394 / 0.411, mean 0.388 against 0.372). `pg0` reproduced `ov0` exactly, so the template column is
     inert with the switch off — a clean control.
   - **Where tier 2 pays, and it is coherent:** the dip-dynamics rows. On draw 3, `ice_dip_day` 1.052 -> 1.401,
     `ice_dip_day_share` 0.693 -> 0.801, `night_cv` 0.378 -> 0.529. A bigger low-side pulse amplifies a dip signature
     the twins ALREADY over-produce, so sizing alone trades the outcome rows for the dynamics rows.
   - **`pro_carb_fix` (stretch the refractory so grams per hour below 80 are conserved) does not bite**, and the
     reason names the real knob: the realized rate moved only 1.154 -> 1.091/h and the score got worse again
     (0.352 / 0.402 / 0.425, mean 0.393 against pg1's 0.388 and ov0's 0.372). At ~1 event per hour BELOW 80, with only
     ~1.2 h/day spent there, a 45 -> 56 min refractory almost never binds — **the rate is set by the firing CONDITION
     (`pro_onset`), not the refractory.**
   - **So the twins' low-side eating is too FREQUENT, not too small**, and the two measured donor quantities must be
     matched together: size from `low_pro_g` and rate via `pro_shift` on the onset (L 409 fitted that onset to the
     donors' lows, but to their ONSET distribution, not to their pulse RATE). Under test at −10 and −20 mg/dL. The
     weighted score has now rejected this direction twice while **tier 1, the outcome tier at weight 3, preferred it
     on all three draws**.
   - **`pro_onset` does not control the rate either, and lowering it is clearly bad.** −10 mg/dL: score 0.337 / 0.414,
     tier 1 0.193 / 0.289. −20: 0.401 / 0.433, tier 1 **0.352** / 0.343. The true rate fell only 1.154 -> 1.107 ->
     0.963 against the donors' 0.548, so a 20 mg/dL shift buys 17% of rate for a doubling of the tier-1 gap — it does
     not stop the eating, it delays it into a deeper low.
   - **Verdict and the one path left.** Four arms: size (tier 1 better on all three draws, tier 2 worse, score worse),
     refractory (no effect on rate), onset −10 and −20 (worse everywhere). None reaches the donors' 0.548 pulses/h
     below 80. Since neither the threshold nor the refractory sets the rate, what does is **how many events one low
     episode produces**: the proactive snack, the rescue at `treat_thr` on a 20-min gate, and the retreat at
     `p_retreat` 0.34 can all fire inside a single episode, and the twins' 2x rate per hour below 80 is about what
     two events per episode against the donors' one would give. That repeat-treatment path is the next lever and the
     only one not yet tried; it is also the one that would lower the rate WITHOUT delaying the first response, which
     is what wrecked pg3 and pg4.
   - **And the repeat-treatment lever is wrong too — the excess low-side eating is a SYMPTOM, not a cause.** Events
     per low episode (a run below 80 joined across gaps under 15 min; labelled pulses both sides,
     `resid_tools/per_episode.py`): donors mean 0.50, twins 0.62 / 0.64, with two-or-more events rare on both sides
     (0.01 against 0.02 / 0.03). So nothing fires repeatedly inside an episode. What differs is the share of episodes
     treated at all — the donors leave **51%** of their low episodes alone, the twins 40% — and that share follows
     from how long an episode lasts:

     | | low episodes / day | median duration | share of episodes treated |
     |---|---|---|---|
     | donors | 1.75 | **20 min** | 0.49 |
     | twins | 1.92 / 2.17 | **25 min** | 0.60 |

     Duration x1.25 against treated-share x1.23: the twins' lows last longer, so more of them cross a treatment
     condition. **This is the sub-basal recovery gap of L 559–560 seen from the eating side** (at a 60–70 nadir the
     twins rise +21 in 30 min against +26 and dwell 15 min against 10), which is blocked on evidence — a study that
     LOWERS glucose below basal at basal insulin in T1D (L 563).
   - **Nothing adopted.** `pro_g_own`, `pro_carb_fix` and `pro_shift` all stay off; `ov0` remains the reference. Two
     findings stand. The measurement: the twins' low-side eating carries the donors' carbohydrate per hour below 80 at
     1.23x the labelled pulse rate and 0.80x the size, the outcome rows respond to its granularity and the
     dip-dynamics rows respond the other way. And the redirection: **low-side eating is not a behaviour defect to
     fix — it is approximately right per low episode, and its excess is downstream of lows that run too long.** Do
     not spend further arms on the eating side; the lever is the body's recovery from a shallow low.

589. **A1c brain sparing does not shorten a shallow low either, and it is quantitatively in the same too-small class
   as A9 — which sizes the missing hepatic term at about 3x both.** L 588 traced the twins' excess low-side eating to
   episodes that run too long (median 25 min against the donors' 20), and `ge_spare` (A1c: insulin-independent uptake
   falling proportionally to glucose below `g_ii` 81 mg/dL, `f_ii` 1 mg/kg/min from Best 1981, the fall from
   Hovorka 2004's F01c) is the evidenced mechanism that should shorten one — the brain stops taking glucose, so the
   low recovers. It was flagged to Pete on a t70-vs-reach-54 trade (L 561) and **episode duration is the direct target
   it had never been measured against**.
   - **It does not move the target at all.** Median low-episode duration stays **25 min** on every arm, episodes per
     day 1.92 -> 1.83, events per episode 0.62 -> 0.61, share of episodes treated 0.40 -> 0.41, and the low-side eating
     rate is unchanged (1.051 -> 1.050 per hour below 80). On the ov0 base it also loses on score (0.339 / 0.386 /
     0.415, mean 0.380 against 0.372) — its L 561 gains were measured on ad3, whose t70 ov0 has since partly fixed.
   - **The arithmetic says why, and it is the useful part.** At G 65 the sparing is `f_ii x (1 − 65/81)` = 0.20
     mg/kg/min, about **3.7 mg/dL over 30 min** — the same order as the A9 counter-regulation bound of 2.4 mg/dL/30 min
     that L 559–560 rejected as too small. **Both named sub-basal mechanisms are now measured too small by the same
     margin**, and L 563's missing term (a glucose-dependent hepatic response below Gb, ~0.34 mg/kg/min at G 65) is
     about **3x** either of them. That is the number an evidence request should carry: not "something is missing" but
     "a term 3x the size of A1c sparing, at basal insulin, below basal glucose".
   - `ge_spare` stays off. The two sub-basal levers the model HAS are exhausted; the gap is one unimplemented term
     whose size is now bracketed from below by two independent mechanisms.

590. **`si_norm` 1.0 buys the change-response SIZE and spends the RANKING — the trade Pete reserved in L 577, now
   measured on the ov0 reference and in exactly the terms he framed it.** L 577 left it open as "the core carries how
   MUCH a person responds, `resid_m` sharpens WHO does", on the ad3 base. Re-run on ov0 with the level refit (two
   rounds), on the cohort and on the same 108 natural experiments as `ad3_s` and `ov0_s`:

   | | cohort score (3 draws) | tier 1 | edit response field/twin: mean · TIR · t70 | t70 rho |
   |---|---|---|---|---|
   | ov0 (reference) | 0.332 / 0.394 / 0.391, mean **0.372** | 0.178 / 0.218 / 0.197 | 2.32 · 1.82 · 3.61 | +0.22 |
   | `si_norm` 1.0 | 0.335 / 0.376 / 0.416, mean 0.376 | **0.134 / 0.201 / 0.176** | **1.84 · 1.37 · 2.54** | **−0.01** |

   - **Size: the least damped response of any arm.** The standing limit is that a settings change is damped to about
     half the field's mean response with lows 4–8x under; this takes the mean ratio 2.32 -> **1.84** and t70
     3.61 -> **2.54**, the closest to the field (1.0) yet measured, and TIR 1.82 -> 1.37. (The t54 ratio's CI is
     [−70.7, +85.2] — uninformative, and AGENTS.md says t < 54 change is too rare to rank candidates on.)
   - **Ranking: t70's across-event correlation collapses**, +0.22 -> −0.01, and the strategy pool's t70 rho 0.39 ->
     0.31. So the twins respond by about the right AMOUNT but no longer rank WHICH donor responds — which is the
     core-versus-residual trade stated precisely: `resid_m` is fitted per person and does not scale with insulin, so
     carrying the 8% in it sharpens who responds while carrying it in the core sizes how much.
   - **On the cohort it is level** (mean 0.376 against 0.372, inside the 0.04 draw scatter) with **tier 1 better on all
     three draws** and the glucose level nearly exact (bg_mean gap 0.076 -> 0.015 on draw 3, TIR 69.29 -> 71.34 against
     71.88 on draw 1), paid for in lows (t54 0.149 -> 0.259 on draw 3).
   - **CORRECTION, same session: there is no size-versus-ranking trade — I read a noise wobble as a collapse.** The
     t70 edit-response rho is one correlation at **n = 63**, where a single rho's SE is 0.13: +0.22 -> −0.01 is
     Fisher z 1.28, **p 0.20**, and the other two edit rhos do not move at all (TIR +0.15 -> +0.17, p 0.91; mean
     +0.31 -> +0.33, p 0.90). Meanwhile the well-powered ranking evidence — the per-person twin-donor correlations at
     **n = 112**, in each run's `twin.csv` — moves the OTHER way on every outcome row:

     | twin-donor rho | TIR | bg_mean | t70 | t54 | bg_cv |
     |---|---|---|---|---|---|
     | ov0 | 0.795 / 0.805 | 0.850 / 0.846 | 0.593 / 0.421 | 0.471 / 0.438 | 0.545 / 0.535 |
     | `si_norm` 1.0 | **0.813 / 0.838** | **0.882 / 0.890** | **0.671 / 0.492** | **0.520 / 0.555** | **0.610 / 0.609** |

     So `si_norm` 1.0 ranks WHICH donor a twin resembles better on every outcome, AND sizes the response closer to the
     field. L 577's framing — the core sizes how much, `resid_m` sharpens who — is not what the data show.
   - **The real trade is lows.** Against all of that, the low rows get worse: t70 1.803 -> 2.013 (donors 1.599) on
     draw 1 and 1.490 -> 1.728 on draw 3, t54 0.224 -> 0.264 and 0.149 -> 0.259 — the twins' t70 was already OVER the
     donors, so this is worse low-side fidelity, and it is why the weighted score reads level-to-slightly-worse.
   - **Still Pete's call** (he reserved it in L 577), but the basis of the reservation no longer holds, so it is now:
     better level, TIR, tier 1, per-person fidelity on every row, and the least damped change response — against worse
     low-side fidelity. Recommendation: adopt 1.0, since the low side is dominated by the unimplemented sub-basal
     hepatic term (L 589) rather than by `si_norm`, and 1.0 is the principled end of a parameter that only stands in
     for life modulators this reference disables.
   - **Method note:** quote an edit-response rho with its n. At n = 63 nothing smaller than about 0.26 is separable.

591. **The post-meal fall / rise ratio is NOT reachable through absorption SHAPE — the last named class on L 575's
   list, now eliminated by measurement and by a literature-sized implementation.** L 575 required a time-asymmetric,
   non-mean-preserving mechanism and ruled out every rate-like lever; this session also ruled out the bolus-timing mix
   (L 588). Gastric emptying SHAPE was the remaining candidate, and it had never been measured.
   - **The twins' pulses really are the wrong shape.** Labelled both sides at a matched 35 g
     (`resid_tools/pulse_shape.py`, decay phase = end − peak): the donors peak at **50 min** and decay for 60
     (decay/peak **1.21**, total 125); the twins peak at **37** and decay for 66 (**1.44**, total 120). They rise too
     early and trail 19% too long — exactly the asymmetry the ratio deficit implies.
   - **The model's tail was the wrong form.** The gut empties first-order from Qsto2, so a parcel trails off
     exponentially. Elashoff 1982 gives emptying as `exp(−(k·t)^beta)` with beta ~1.5–2, whose hazard is
     `beta·(k·t)^(beta−1)`: flatter start, sharper finish — the one shape that steepens the post-peak fall without
     lowering the peak. Implemented as `ge_beta` (default 1.0, which skips the branch and is bit-identical).
   - **The shape moves as designed and the RATIO DOES NOT FOLLOW.** decay/peak 1.44 -> 1.33 (beta 1.3) -> 1.25-1.29
     (beta 1.6), against the donors' 1.21; the fall / rise ratio goes **0.67 -> 0.67 -> 0.70** against the donors'
     0.89. Four arms (beta 1.3 / 1.6, with and without the mean kept) and the ratio never leaves 0.66–0.70.
   - **And it cannot be made score-neutral.** Score 0.332 -> 0.443 / 0.554 (speed-confounded) and 0.434 / 0.547
     (mean kept) on draw 1, with tier 1 0.178 -> 0.54. **Keeping the parcel's mean emptying time does not keep the
     glucose pulse's duration** — scaling k by `Gamma(1+1/beta)` holds the emptying mean, but the Weibull hazard still
     concentrates appearance earlier, so the labelled total falls 120 -> 112 -> 102 against the donors' 125. That is
     the same conserved-quantity trap as L 588's carb total, one level deeper: the quantity I conserved was not the
     one the statistic measures.
   - **Right-sizing what is left.** The ratio deficit is a post-peak fall of 52 against 57 mg/dL at a matched rise
     (68 against 69) — about **5 mg/dL**, with L 575's sensor caveat on top (the CGM amplifies a fall ~27% against a
     rise ~7%, so the truth-side gap is smaller still). Every named class is now eliminated: rate, timing mix,
     appearance shape, dose, Loop compensation, potency localisation. Either the residual 5 mg/dL is sensor and
     labeller artefact, or the mechanism is not in the meal pathway at all.
   - `ge_beta` stays at 1.0. The code and the measurement stay, since the pulse-shape gap is real and any future meal
     work should know the tail is the wrong form AND that fixing it does not pay here.

592. **The residual's DYNAMIC part was damping the change response and degrading per-person fidelity; the level-only
   residual is the new reference (rf2).** `resid_mult` scales only `resid_f` / `resid_b` / `resid_d` and leaves
   `resid_m` (the per-person level) alone, so `resid_mult` 0 is a level-only residual — the shape the role doc already
   recorded as responding better (f4: TIR field/twin 0.76 / 1.27 against sd3's 1.32 / 1.29 / 1.39).

   | | cohort score (3 draws) | tier 1 | edit response: mean · TIR · t70 | t70 rho |
   |---|---|---|---|---|
   | ov0 | 0.332 / 0.394 / 0.391, mean 0.372 | 0.178 / 0.218 / 0.197 | 2.35 · 1.74 · 3.51 | +0.22 |
   | `resid_mult` 0, no refit | 0.327 / 0.378 | 0.140 / 0.221 | 2.12 · **1.22** · 3.47 | +0.30 |
   | **rf2** (0, refitted) | 0.332 / 0.371 / 0.406, mean **0.370** | **0.135 / 0.209 / 0.178** | 2.28 · 1.69 · **2.17** | **+0.34** |

   - **The refit separated a real gain from an artefact, and both halves of that matter.** Unrefitted, the arm looked
     better on everything — but `resid_m` was fitted with the dynamics present, so removing them drops the glucose
     level (bg_mean gap 0.119 -> 0.242 on draw 2) and a model running low responds more to an insulin edit for trivial
     reasons. After the refit the **TIR gain vanishes** (1.22 -> 1.69, i.e. ov0's 1.74) — it WAS level drift — while
     the **t70 gain survives** (3.51 -> 2.17, the best of any arm, past `si_norm` 1.0's 2.55) with its ranking
     improving (+0.22 -> +0.34, also the best). `cb2` had already shown a refit can re-absorb these gains entirely
     (mean 2.76, worse than either lever alone), which is why the unrefitted number could not be trusted.
   - **And the component was not doing what it was adopted for.** The dynamic residual was taken on for per-person
     spread; removing it IMPROVES twin-donor rho on five of six outcome rows (TIR 0.795 -> 0.815 and 0.805 -> 0.830,
     bg_mean 0.850 -> 0.885 and 0.846 -> 0.896, t70 0.593 -> 0.631 and 0.421 -> 0.484, t54 0.471 -> 0.526,
     bg_cv 0.545 -> 0.616; only TDD is marginally worse), and it contributes almost nothing to the volatility rows it
     was meant to hold (bg_cv, sigma_disp, vol_cluster_60m all level without it).
   - **Costs, honestly:** TDD a little worse on every draw (41.2 -> 42.6 on draw 2), and draw 2 keeps a level drift the
     refit does not fully remove (148.2 against the donors' 151.9) with t70 2.12 against ov0's 1.97. Draws 1 and 3 are
     clean (draw 3's bg_mean gap 0.076 -> 0.018, nearly exact).
   - **Adopted** on the documented criteria: level on the weighted score, better tier 1 on all three draws, better
     per-person fidelity, substantially better change response on the metric change prediction is judged on (TIR and
     t < 70, Pete 2026-10-26), and one fewer active component — the model carries LESS unnamed dynamics, which is the
     direction the residual rule points. **The two prediction levers do not compose** (L 590's `si_norm` 1.0 plus this
     one gives mean 2.76), so `si_norm` remains a separate question, now against a reference whose t70 response is
     already 2.17.

593. **The twins' excess insulin is quantitatively explained, and `resid_m` was masking half of it.** With the
   level-only residual (L 592) `resid_m` is the ONLY residual term — a constant per-person glucose drive in mg/dL/h —
   so for the first time the insulin surplus decomposes. Converting each person's `resid_m` at their own fitted ISF
   (`resid_m` x 24 / `isf_true`, 168 templates):

   | | U/day |
   |---|---|
   | observed TDD excess (42.6 against the donors' 38.7) | **+3.9** |
   | masked by `resid_m`'s mean (−7.69 mg/dL/h, i.e. a glucose SINK) | **+3.0** |
   | underlying core excess | **about +6.9, or +18%** |
   | predicted by `si_norm` 0.92 — an 8% sensitivity cut on 38.7 U | **+3.1** |

   - **`resid_m` is not a small correction.** Its median is 0.00 but its mean is −7.69 mg/dL/h (sd 25, p10 −38.5,
     min −135.5): a heavy negative tail worth −3.00 U/day on average. A −38 mg/dL/h drive is ~920 mg/dL of glucose
     removed per day, which is no one's "unlogged load" — it is core error being absorbed, exactly as L 577 said
     qualitatively and now with a size.
   - **The negative tail is the tight-donor limit.** Split by the donor's own control, `resid_m` is 0.00 for the loose
     and middle thirds and **−4.47 mg/dL/h (−1.24 U/day) for the tight third**, with corr(donor TIR, `resid_m`) =
     −0.17. "Twins of tight-control donors run high" (L 445–456) is therefore not an unexplained limit but a measured
     one: the core runs them high and the residual buys it back as a glucose sink.
   - **And the arithmetic names the fix.** `si_norm` 0.92 is a deliberate cohort-wide 8% sensitivity cut; a body 8%
     less sensitive needs 8% more insulin, which on the donors' 38.7 U/day is **+3.1 U/day** — essentially the whole
     observed excess (+3.9). So the standing limit "twins need 5–8% more insulin than their donors" is not a mystery
     to be chased: it is the 8% cut, and `si_norm` 1.0 is its removal. L 577 found that 1.0 improves TDD on all three
     draws; this says why, and by how much.
   - **Which strengthens the `si_norm` case on grounds the L 590 measurements did not cover.** It is no longer only
     "better explained" plus a level-versus-lows trade: the parameter is arithmetically the right size for a documented
     defect. Against that, its cost is low-side fidelity, and the low side is dominated by the unimplemented sub-basal
     hepatic term (L 589). Recommendation unchanged and now quantitative: adopt 1.0.

594. **`acf_zero_min`, the fall / rise ratio and "slow falls / missing fast moves" are ONE defect — the twins' glucose
   reverses direction too slowly — and gastric-emptying SHAPE is the only lever that touches it.** `acf_zero_min` is
   the ACF of the 5-min INCREMENTS (`traits.py`: `_acf(steps, ...)`, "momentum crosses zero"), so it is the lag at
   which glucose MOMENTUM first turns negative: the donors reverse at **40 min**, the twins at **60** — momentum
   persists about 40% too long. Read that way it is not an isolated tier-3 sensor curiosity but the short-scale view
   of the same thing the post-meal ratio measures at the peak (L 575, 591) and the fast-fall tail measures after it.
   - **Measured across every arm this session, exactly one moved it:**

     | arm | `acf_zero_min` | gap |
     |---|---|---|
     | donors | 40 | — |
     | rf2 / ov0 / `resid_mult` 0 / `pro_g_own` | 60 | 1.59–1.73 |
     | `si_norm` 1.0 | 57.5 | 1.46 |
     | **`ge_beta` 1.3 / 1.6** | **55** | **1.22** |

     So the Elashoff emptying shape (L 591) closes about a quarter of the gap — and it is the ONLY lever found, which
     **corrects L 385–389's "no body lever moves it"**: those levers were everything except emptying shape.
   - **Why this matters more than the ratio did.** The ratio deficit is small in amplitude (a post-peak fall of 52
     against 57 mg/dL, ~5 mg/dL, and sensor-inflated), which is why L 591 left it artefact-bounded. The TIMESCALE
     deficit is large (+40%) and is not an amplitude artefact, so the defect is better stated as *reversal speed* than
     as *fall depth*. Three rows move together and should be read together, not chased separately.
   - **And the blocker is named.** The one lever that touches it is the one whose score penalty is prohibitive
     (`ge_beta` takes the score 0.332 -> 0.43–0.55, because concentrating appearance earlier also shortens the glucose
     pulse to 102 min against the donors' 125). So the open question is not "what moves `acf_zero_min`" — emptying
     shape does — but whether anything speeds glucose reversals WITHOUT compressing the meal pulse. A faster
     counter-regulation or glucose-effectiveness response would qualify and is where to look next; both are
     sub-basal terms, and both are currently measured too small (L 589).

595. **The gastric lag phase was genuinely missing, and it cannot fix the peak-timing gap, because that statistic is
   shift-invariant.** Every carb parcel had `delay = 0` (only protein glucose carried one, 90 min), so appearance began
   the instant food was eaten — a real omission against Siegel 1988's ~20–30 min lag for solids. `meal_lag` adds it,
   applied to the meal parcels only (not the rescue or exercise carbs, where delaying a low treatment would be wrong
   and unsafe). On an isolated 35 g parcel it behaves exactly as intended: peak 55 -> 65 -> 75 min at lag 0 / 10 / 20
   with the decay phase UNCHANGED at 111 and decay/peak 2.02 -> 1.71 -> 1.48 — the property `ge_beta` lacked.
   - **On the cohort it moves the labelled shape not at all.** peak **43 min and decay 67 for lag 0, 10 AND 20**,
     byte-for-byte the same, with decay/peak 1.44 -> 1.48 and the fall / rise ratio drifting the wrong way
     (0.63 -> 0.61 -> 0.59 against the donors' 0.89). Score level (0.334 / 0.362 and 0.330 / 0.367 against rf2's
     0.332 / 0.371), tier 1 a little better at lag 20 (0.127 / 0.142 against 0.135 / 0.209).
   - **Why, and it is the lesson: `peak_h` is measured from the LABELLER'S OWN detected onset, not from the carb
     entry.** A pure time shift moves the onset and the peak together, so peak-minus-onset is invariant to it. The
     statistic cannot see a lag, by construction — which also **corrects this lesson's own framing**: the twins'
     "peak at 37 against the donors' 50" is not a delay deficit, it is a difference in the RISE SHAPE after onset, and
     no lag can address it. I should have checked what the statistic was referenced to before building the component.
   - **A side observation worth keeping:** rf2 is already closer to the donors on pulse shape than ov0 was (peak 43
     against 37, total 128 against 120, donors 50 / 125) — the dynamic residual was adding fast motion that moved the
     labeller's onset detection, so dropping it (L 592) improved the meal shape as a by-product.
   - `meal_lag` stays at 0. The code and the evidence note stay, because the omission is real and a future meal model
     that measures appearance against the ENTRY (not the detected onset) will need it.

596. **A1b was one-sided, and extending it below basal fixes the t70 excess — the sub-basal gap was a missing code
   branch, not missing evidence.** `hep` is gated on `g > p.gb`, so the liver withheld glucose when high and never
   released extra when low; below basal the whole hepatic response fell to A9, whose magnitude the donors' low DEPTHS
   pin (`cr_max` walked 0.5 -> 0.137 across L 166/272/360/394, supplying ~2.6 mg/dL per 30 min). That is why L 589
   found both sub-basal mechanisms too small: the third was absent by construction. Glucose autoregulation of hepatic
   output is bidirectional in the literature (Cherrington/Moore: HGP rises as glucose falls, independent of hormones);
   only the above-basal direction is quantified, so symmetry is the modelling assumption — and it lands on the
   requirement, `sg_h` 0.0038 below Gb giving **0.386 mg/kg/min at G 65** against L 589's independently derived ~0.34.
   - **At half symmetry (`sg_h_lo` 0.0019) it closes the t70 limit:**

     | | t70 (donors 1.599) | TIR (71.88) | lows/day (1.00) | P(reach 54) (0.212) |
     |---|---|---|---|---|
     | rf2 | 1.764 / **2.119** | 72.15 / 71.25 | 1.000 / 1.250 | 0.195 / 0.194 |
     | `sg_h_lo` 0.0019 | **1.528 / 1.621** | 72.95 / 72.94 | 0.750 / 0.923 | 0.167 / 0.172 |

     Draw 2's t70 gap goes 0.325 -> **0.012**. The cost is the low COUNTS: `lows_per_day` and `P(reach 54)` were
     already at or under the donors and go further under, which is why the weighted score reads worse
     (0.354 / 0.360 against 0.332 / 0.371). Full symmetry (0.0038) overshoots further (t70 1.203 / 1.156).
   - **The diagnosis the arm sharpens:** at rf2 draw 1 the twins already have exactly the donors' NUMBER of lows
     (1.000) with too much TIME below 70 (1.764) — their lows last too long, which is the 25-against-20-min episode
     duration of L 588 seen on the scorecard. `sg_h_lo` shortens lows AND prevents some, because it acts on
     `(Gb − G)` and so is already working on the way down. A term acting only once low would shorten without
     preventing, but that is a different claim and needs its own evidence; symmetry is what the literature supports.
   - **Two of my hypotheses died here, both worth recording.** (1) Controller compensation does NOT explain why
     doubling the term did not double the recovery: insulin delivered in the 30 min after a nadir is unchanged
     (0.040 / 0.040 / 0.038 U). (2) The nadir-recovery statistic is **selection-confounded** — the intervention
     prevents the easy lows, so nadir counts fall 1874 -> 1607 and the surviving 60-70 nadirs are a harder,
     insulin-driven subset. A statistic conditioned on an event whose incidence the candidate changes cannot measure
     that candidate. Read the unconditional rows (t70, episode duration) instead.
   - **Not adopted** — the weighted score is worse and the low counts overshoot — but this is the first mechanism to
     move the t70 limit at all, it is a named component with a literature-supported form, and its magnitude was
     derived before the run rather than swept. It belongs with `si_norm` as a judgement about which row to spend.

597. **`resid_m`'s refit re-absorbs any change whose effect runs through the glucose LEVEL — which retracts L 593's
   recommendation and explains three dead gains at once.** Testing `si_norm` 1.0 together with `sg_h_lo` 0.0019,
   whose costs on the low counts have opposite signs and which act on different physiology (insulin need vs hepatic
   output):

   | | t70 (1.599) | lows/day (1.00) | P(reach 54) (0.212) | TDD (38.7) | score |
   |---|---|---|---|---|---|
   | rf2 | 1.764 / 2.119 | 1.000 / 1.250 | 0.195 / 0.194 | 41.9 / 42.6 | 0.332 / 0.371 |
   | `sg_h_lo` alone | 1.528 / 1.621 | 0.750 / 0.923 | 0.167 / 0.172 | 41.6 / 42.0 | 0.354 / 0.360 |
   | both | 1.279 / 1.509 | **0.750 / 0.917** | 0.176 / 0.174 | **42.1 / 43.0** | 0.350 / 0.358 |

   - **The costs did not cancel and TDD went the WRONG WAY.** `si_norm` 1.0 restored none of the low count (0.750,
     unchanged) and made TDD worse (41.6 -> 42.1, 42.0 -> 43.0) where L 593's arithmetic predicted −3.1 U/day.
   - **Because the level refit converts a sensitivity gain back into insulin.** With `si_norm` 1.0 the body needs less
     insulin for the same glucose, so `lvl_resid` raises `resid_m` to hold the donor's level — and covering that extra
     drive takes the insulin straight back. **L 593's +3.1 U/day is real only if `resid_m` is NOT refitted**, and a
     reference that fits `resid_m` to the donor's level cannot improve TDD through a cohort-wide sensitivity scalar.
     Recommendation retracted: `si_norm` 1.0 is not the fix for the insulin surplus.
   - **The general law, and this is its third sighting.** Any candidate whose effect runs through the mean glucose
     level is re-absorbed by the refit: `rs0`'s TIR-response gain (L 592, 1.22 -> 1.69 after refit), `cb2`'s whole
     response gain (mean 2.76, worse than either lever), and now `si_norm`'s TDD gain. What SURVIVES a refit is a
     change that acts on something other than the mean — `rf2`'s t70 response gain did (3.51 -> 2.17), because it
     changes the DYNAMICS the level fit does not see, and `sg_h_lo`'s t70 gain did, because it changes the shape of
     excursions below a threshold rather than the average.
     **Judge a candidate after the refit, and expect level-mediated effects to vanish.**
   - So the insulin surplus needs a mechanism that makes the twins need less insulin AT their donor's level — not a
     sensitivity scalar, which the refit neutralises by construction. The decomposition of L 593 stands as a
     measurement (`resid_m` masks 3.0 U/day of it, and its negative tail is the tight-donor limit); its proposed fix
     does not.

598. **Paired against its OWN donor, the insulin surplus is +1.4 to +1.7 U/day (3.5-4.4%), not the 10% a cohort
   median shows — and basal withholding is not the cause.** L 597 said the surplus needs a mechanism that lowers
   insulin need AT the donor's level, so I went looking for which limb carries it. Three measurement errors later,
   this is what survives.
   - **The matched number** (`twin.csv`, each twin against the donor it was built from, three draws): TDD paired diff
     **+1.40 / +1.40 / +1.67 U/day** with rho 0.913 / 0.791 / 0.877, against a paired bg_mean diff of
     −1.38 / +0.21 / +1.77 — i.e. the twins sit at their donors' glucose level and need 3.5-4.4% more insulin to do
     it. **The standing limit is documented as 5-8%; on the current reference, measured paired, it is 3.5-4.4%.**
   - **Basal withholding is NOT the defect.** Delivered basal as a share of each person's own SCHEDULED basal:
     donors median **0.74** (p25 0.59, p75 1.12), twins **0.73 / 0.68**. The twins' Loop suspends and reduces basal
     just as the donors' did.
   - **What I got wrong on the way, all one family.** (1) A limb-by-limb U/day table (basal 16.3 against 13.3, "the
     excess is 23% basal") compares **different populations** — 112 twins drawn from 168 templates against the 206
     donors with step tables — so it measures cohort composition, not the model. (2) Within that, "donors deliver 67%
     of schedule, twins 83%" was a **ratio of medians**; the median of per-person ratios is 0.74 against 0.73.
     (3) TDD first read 47 U/day because I divided a 14-day delivery stream by the 12-day scored window.
     **Use `twin.csv`'s paired diff for anything per-person; a cohort median mixes populations and cannot localise a
     per-person defect.**
   - So the surplus is modest, spread across limbs rather than concentrated in one, and coexists with a matched
     level — which is consistent with L 597 (no sensitivity scalar can fix it, because the level is held by the refit)
     and means the remaining work is worth less than the "5-8%" headline implied. Re-state the limit at 3.5-4.4%.

599. **The below-basal hepatic term must carry basal EGP's insulin suppression — unsuppressed it PREVENTS lows,
   suppressed it SHORTENS them.** L 596's `sg_h_lo` closed the t70 limit but cost the low counts (1.000 -> 0.750), and
   the reason was a flaw in my implementation rather than in the mechanism: hepatic glucose output is
   insulin-suppressed and the autoregulatory increase was not, so it acted at full strength on the way INTO a low
   while IOB was still high. It now carries the same factor basal EGP uses, `min(max(1 − sE·xE, 0), 1 + sE)`
   (`sg_h_lo_ins`, default on, inert while `sg_h_lo` is 0).

   | | lows/day (1.00) | t54 (0.190) | t70 (1.599) | score |
   |---|---|---|---|---|
   | rf2 | 1.000 / 1.250 | 0.124 / 0.232 | 1.764 / 2.119 | 0.332 / 0.371 |
   | unsuppressed (`hl19`) | 0.750 / 0.923 | 0.091 / 0.147 | 1.528 / 1.621 | 0.354 / 0.360 |
   | **suppressed (`hi19`)** | **0.833 / 1.042** | **0.181 / 0.166** | **1.319 / 1.586** | 0.354 / 0.373 |

   - **The mechanism check passes:** suppression recovers a third of the lost low count and nearly all of t54
     (0.181 against the donors' 0.190, where unsuppressed gave 0.091), i.e. the term stops intervening on the descent
     and acts at the nadir, where insulin has fallen. That is the behaviour the physiology implies, and it is a
     correctness fix regardless of whether `sg_h_lo` is ever switched on.
   - **It is still not an adoption, and the reason is draw-dependence worth noting.** On draw 2, where rf2 is poor
     (t70 gap 0.325), it is excellent (0.034). On draw 1, where rf2 is already near-perfect (t70 gap 0.086,
     lows/day exactly 1.000), any intervention overshoots (t70 1.319). So the candidate helps where the reference is
     weak and hurts where it is strong, which the weighted mean reads as level-to-worse. A smaller magnitude would fit
     both, but choosing it from these curves is tuning on the scorecard, not evidence.
   - **Adopted: the suppression itself** (`sg_h_lo_ins` default on). **Not adopted: `sg_h_lo`**, which stays 0 and
     remains the "which row do we spend" question for Pete — now with the term behaving as intended, so the question
     is cleaner: at half symmetry it trades ~0.17 of draw-1 t70 gap and ~0.16 of lows/day for ~0.29 of draw-2 t70 gap.

600. **The low-side defect, stated exactly: excursions below 80 last too long while penetrating to 70 at the right
   rate — so the missing mechanism must act during RECOVERY, not at the nadir, which rules out every
   (Gb − G)-proportional term including `sg_h_lo`.** The scored `lows_per_day` counts excursions below **70**
   (`validate.py`: `while vals[e] < 70`); `resid_tools/per_episode` counts runs below **80**. Reading both together
   separates how OFTEN the twins go low from how DEEP and how LONG:

   | | episodes/day < 80 | of those, reach 70 | median duration < 80 |
   |---|---|---|---|
   | donors | 1.75 | **57%** | **20 min** |
   | rf2 (reference) | 1.67 | **60%** | 25 min |
   | `sg_h_lo` 0.0019 unsupp. | 1.75 | 43% | 21 min |
   | `sg_h_lo` 0.0019 supp. | 1.58 | 47% | 22 min |
   | `sg_h_lo` 0.0038 supp. | 1.58 | 44% | 20 min |

   - **rf2 already matches the penetration rate** (60% against 57%) and the excursion count; its single low-side
     defect is DURATION, 25 min against 20. Every `sg_h_lo` variant fixes the duration (20-22 min) and breaks the
     penetration rate (43-47% against 57%), which is what the scored `lows_per_day` 1.000 -> 0.750 was reporting.
   - **Why, and it is a timing requirement not a magnitude one.** `hep_lo` is proportional to (Gb − G), so it is
     strongest exactly at the nadir: it LIFTS the nadir rather than shortening the tail. Insulin suppression (L 599)
     helps because it quiets the term on the descent, but it cannot stop it peaking at the bottom. **What is needed is
     a term that acts AFTER the nadir, during the climb** — which no glucose-proportional term can be, and which
     counter-regulation's own 15-min time constant (`cr_tau`) already has the shape of, but at a magnitude the depth
     fit pins (L 589, 596).
   - **So the low-side thread ends with a specification rather than a candidate**: shorten the recovery limb of an
     80-excursion without raising its nadir. That is the same time-asymmetry requirement L 575 wrote for the post-meal
     ratio and L 594 for reversal speed — three limits, one missing shape, now stated in three independent ways.
     A delayed (rate-of-change or time-since-nadir) hepatic or counter-regulatory response is the form to try; a
     level-proportional one is not, and this lesson is the reason to stop proposing them.

601. **An asymmetric counter-regulatory decay is the first low-side mechanism that improves the outcome rows without
   trading one for another — tier 1 better on BOTH draws, t54 nearly exact, the low-episode count preserved.** L 600
   specified the shape: shorten the recovery limb WITHOUT raising the nadir, which no (Gb − G)-proportional term can
   do. `self.cr` relaxed toward its target with a single time constant, so the counter-regulatory EGP effect faded as
   fast as it built. `cr_tau_off` gives the OFF limb its own constant — the glycogenolytic response outlasts the
   catecholamine / glucagon pulse that triggers it (clearance plus post-receptor effects run 20-60 min). Verified
   before running: on a V-shaped 90-62-90 excursion the peak `cr` is IDENTICAL at `cr_tau_off` 0 / 30 / 60 (0.3971 at
   min 47) while the climb-phase mean rises 0.2511 -> 0.3050 -> 0.3446.

   | | t54 (0.190) | t70 (1.599) | lows/day (1.00) | dwell < 70 (15) | tier 1 | score |
   |---|---|---|---|---|---|---|
   | rf2 | 0.124 / 0.232 | 1.764 / 2.119 | 1.000 / 1.250 | 20 min | 0.135 / 0.209 | 0.332 / 0.371 |
   | `cr_tau_off` 60 | **0.175 / 0.177** | **1.688 / 1.843** | 0.958 / 1.126 | **15 min** | **0.132 / 0.201** | 0.334 / 0.383 |

   - **t54's gap goes 0.146 -> 0.090 and 0.134 -> 0.038**, t70 improves on both draws, the low-episode count is
     preserved (2978 -> 2980 against every `sg_h_lo` variant's drop), and the nadir dwell under 70 matches the donors
     exactly. **Tier 1, weight 3, improves on both draws** — the first low-side candidate to do that.
   - **It works on a different window than I predicted.** The 80-excursion duration is UNCHANGED at 25 min, so
     L 600's stated target is untouched: `cr_g` is 65, so counter-regulation acts below ~70 and shortens the sub-70
     portion, not the 70-80 band. The L 600 specification should therefore read "shorten the time below 70", which
     this does, and the 70-80 band remains unaddressed.
   - **Cost:** tier 2/3 damage is draw-INCONSISTENT (ac1 +0.154 on draw 1 but −0.093 on draw 2; `between_day_frac`
     the reverse), i.e. mostly noise, with one consistent exception — `ice_dip_day_share` (+0.100, +0.116), the
     expected signature of counter-regulation persisting into the climb. The weighted score is level on draw 1 and
     worse on draw 2 (mean 0.359 against 0.352), so draw 3 decides it under the three-draw rule and is running.

602. **Of the outcome rows, only TDD is a real bias — t54, t70, lows/day and TIR have a draw-to-draw scatter LARGER
   than their gap to the donors, which is why six low-side candidates all failed the same way.** `cr_tau_off` 60 lost
   on draw 3 (score 0.424 against rf2's 0.406, tier 1 0.193 against 0.178) after winning tier 1 on draws 1 and 2, so
   it is rejected on the three-draw rule (mean 0.380 against 0.370). Looking at WHY turned up the structural point.
   The reference's own tier-1 rows across seed0 1000 / 5000 / 9000:

   | row | twin mean | bias vs donors | sd across draws | |
   |---|---|---|---|---|
   | t54 | 0.168 | −0.022 | **0.057** | scatter 2.6x the bias |
   | t70 | 1.798 | +0.199 | **0.306** | scatter 1.5x the bias |
   | lows / day | 1.042 | +0.042 | **0.191** | scatter 4.5x the bias |
   | TIR | 70.886 | −0.996 | **1.484** | scatter 1.5x the bias |
   | P(reach 54) | 0.184 | −0.028 | 0.019 | small real bias |
   | **TDD** | 42.390 | **+3.690** | 0.440 | **real: 8x the sd** |

   - **A fixed-magnitude term cannot improve a row whose draw scatter exceeds its bias** — it helps on the heavy draw
     and overshoots on the light one. That is precisely what `sg_h_lo` (suppressed and not), `cr_tau_off` and
     `pro_g_own` each did, and it is a property of the TARGET, not of the mechanisms. Six candidates, one explanation.
   - **So "the twins run excess shallow lows" is not established as a bias at three draws.** t70's +0.199 sits inside
     a 0.306 scatter; on draw 3 the reference is already BELOW the donors on both t54 (0.148 against 0.190) and t70
     (1.510 against 1.599). The limit as written overstates what the data support.
   - **TDD is the exception and the one genuinely systematic outcome defect**: +3.69 U/day at 8x the across-draw sd,
     i.e. +9.5% on the cohort medians (and +1.4 to +1.7 U/day paired per person, L 598 — the paired figure is the one
     to quote). Combined with L 597, it needs a mechanism that lowers insulin need at the donor's level and is NOT
     level-mediated, since the `resid_m` refit neutralises anything that is.
   - **Caveat on the method:** three draws give an sd with two degrees of freedom, so "noise-dominated" means "not
     established as a bias at n = 3", not "proven zero". The right response is more draws before spending another arm
     on those rows — not another mechanism.

603. **The one real outcome bias is a LOAD bias, not a sensitivity one: the twins' labelled glucose load is 1.10x the
   donors' and their TDD excess is +9.5%.** L 602 left TDD as the only tier-1 row whose gap exceeds its across-draw
   scatter (+3.69 U/day at 8x the sd) and L 597 showed a sensitivity scalar cannot fix it, because the `resid_m` refit
   converts any such gain back into insulin. Load is the mechanism the refit CANNOT absorb: excess glucose in raises
   the level, the refit cancels the level with a negative `resid_m`, and the insulin that covered the excess stays.
   - **`resid_m`'s negative mean is the fingerprint.** L 593 measured it at −7.69 mg/dL/h — a glucose SINK worth
     −3.0 U/day. That is what a refit produces when the load is too high, and it matches the TDD excess in size.
   - **Measured, same labeller both sides:** total labelled load 210.6 / 214.8 / 209.0 g-eq/day against the donors'
     189.2 — **1.10 / 1.14 / 1.10**, tight across draws where the low rows scatter. Split by the labeller's classes:

     | | announced | rescue | UNannounced | total |
     |---|---|---|---|---|
     | donors | 93.6 | 6.3 | **94.7** | 189.2 |
     | rf2 (three draws) | 95.2 / 106.5 / 94.5 | 5.9 / 8.4 / 7.3 | **104.2 / 101.8 / 110.5** | 210.6 / 214.8 / 209.0 |

     The announced load matches on draws 1 and 3 (1.02, 1.01); the **unannounced load is high on all three**
     (1.10 / 1.08 / 1.17).
   - **And it is DRIFT, not a missing component.** The unannounced labelled load was calibrated at c378 —
     97.3 against the donors' 94.7 (L 382) — and now reads 102-110. This is exactly the standing caution that a
     component fitted to an emergent target drifts as others change, so the prescribed response is to refit
     `unl_mult` against its own evidence (the donor's far-from-meal unannounced load, L 449), not to add a mechanism.
   - **Trap found doing it:** `unl_mult` was readable only through the off-by-default `unl_own` experiment and only
     from the template, so `--set unl_mult` was a silent no-op — the fourth instance of that shape this session, after
     `ex_cap_fit`, `ov_dur_own` and the `BEHAVIOR_COLS` allowlist. A direct hook is now wired.

604. **TDD is structurally unfixable by any component while `resid_m` is fitted to the glucose level alone — the fix
   belongs in the FITTING PROCEDURE, not in a mechanism.** L 603 argued that a LOAD reduction is the one thing the
   refit cannot absorb. It is wrong, and the test was clean:

   | | TDD (donors 38.7) | bg_mean (151.9) | t70 (1.599) |
   |---|---|---|---|
   | rf2 | 41.883 / 42.610 | 151.0 / 148.2 | 1.764 / 2.119 |
   | `unl_mult` 0.70, NO refit | **39.592 / 40.828** | 145.0 / 143.9 | 1.748 / 1.983 |
   | same + two-round refit | 41.312 / 42.463 | 148.7 / 149.0 | 1.216 / **1.597** |

   Cutting unlogged eating by 30% takes TDD within 0.9-2.1 U/day of the donors while the level falls 6 mg/dL below
   them; refitting `resid_m` restores the level and **TDD returns to the reference's value**.
   - **The law in its general form, now on its fourth sighting:** `resid_m` is fitted per person to the donor's
     glucose LEVEL, so it will restore whatever net glucose a candidate removes — sensitivity (`si_norm`, L 597),
     dynamics-via-level (`rs0`, L 592), the pair (`cb2`), and now load. **At a matched level, TDD is pinned by the
     model's insulin-to-glucose exchange rate, and the fit guarantees the level matches.** No component that changes
     net glucose input can move TDD; the fit is doing its job and the job precludes the fix.
   - **What this makes the real statement of the limit:** to reproduce a donor's glucose level with that donor's own
     settings, the model needs 3.5-4.4% more insulin than the donor used (paired, L 598). That is an exchange-rate
     error, not an excess of any one input, and it is invisible to every single-component arm.
   - **The structural fix, well posed:** fit `resid_m` AND a per-person sensitivity factor JOINTLY against TWO
     observables, the donor's level and the donor's TDD — two parameters, two targets — instead of one parameter
     against the level alone. That is a change to `lvl_resid`, not to the body, and it would make TDD a fitted
     quantity rather than a free one. It also predicts what today's arms showed: with one parameter and one target,
     TDD is whatever the level fit leaves it.
   - **Worth noting on the side:** the refitted arm has the best t70 of any arm on draw 2 (**1.597** against the
     donors' 1.599, gap 0.055) — the load cut plus the level refit lands it almost exactly, where every low-side
     mechanism overshot. The score still reads worse (0.353 / 0.365 / 0.415 against 0.332 / 0.371 / 0.406) on tier 1
     draws 1 and 3, so it is not an adoption, but it is the second independent route to t70 after `cr_tau_off`.

605. **The joint fit does not move TDD either, and the reason closes the question: Loop doses from the SETTINGS ISF,
   not the body\'s, so the body\'s sensitivity is not the exchange rate that sets TDD. What the joint fit DOES buy is
   the level and the low rows.** L 604 proposed two parameters against two observables; `twin_isf_mult` already exists
   (iterated against each donor\'s t70, L 219) and L 602 showed t70 is noise-dominated while TDD is the real bias, so
   re-targeting it needed no new parameter: `resid_m` <- level, `twin_isf_mult` <- TDD (`tdd_isf.py`, two rounds).

   | | tier 1 | bg_mean gap | t54 gap | t70 gap | TIR gap | TDD | score |
   |---|---|---|---|---|---|---|---|
   | rf2 | 0.135 / 0.209 / 0.178 | 0.037 / 0.175 | 0.146 / 0.134 | 0.086 / 0.325 | 0.053 / 0.070 | 41.9 / 42.6 | 0.332 / 0.371 / 0.406 |
   | joint fit | **0.148 / 0.167 / 0.130** | **0.014 / 0.079** | **0.100 / 0.062** | **0.071 / 0.261** | **0.027 / 0.035** | 41.4 / 43.3 | 0.344 / 0.373 / 0.407 |

   - **TDD is immovable**: the twin / donor ratio went 1.070 -> 1.092 across two rounds while `twin_isf_mult` spread
     to its clip bounds [0.70, 1.43]. The parameter moved as hard as it can and the target did not follow.
   - **Why: Loop computes its doses from the person\'s SETTINGS (therapy.json `isf`, `cr`), not from the body\'s true
     sensitivity.** Changing the body\'s ISF changes how far glucose moves per unit, so the trajectory changes and the
     level fit compensates — but the insulin TOTAL is set by the settings against the glucose Loop sees. With
     `resid_m` holding the level, the total glucose is pinned, so TDD is pinned with it and is invariant to how that
     glucose is split between pulsed load and smooth drive (which is also why L 604\'s load cut returned). **TDD is a
     consequence of the level fit plus the donor\'s own settings, and no body parameter is upstream of it.**
   - **But the joint fit improves four tier-1 rows on both draws** — bg_mean (gap 0.037 -> 0.014 and 0.175 -> 0.079,
     nearly exact), t54 (0.146 -> 0.100, 0.134 -> 0.062), t70 (0.086 -> 0.071, 0.325 -> 0.261) and TIR (0.053 -> 0.027,
     0.070 -> 0.035) — and **tier 1 overall is better on the mean (0.148 against 0.174)** and on draws 2 and 3. The
     score is level (0.3747 against 0.3697) because tier 2/3 degrade. Fitting the per-person multiplier against TDD
     rather than t70 therefore spends its freedom on signal and lands the level and the low rows better, even though
     the row it now targets is the one it cannot reach.
   - **So the honest end state for TDD:** it is not a body defect and not reachable by a body parameter. To make it a
     fitted quantity one would have to let the fit touch the twin\'s SETTINGS — which the role forbids, since settings
     are what the person\'s Loop is configured with (calibration rules) — or accept it as the price of matching the
     level with the donor\'s own settings. Recommend accepting it and re-stating the limit that way.

606. **Do not fit a parameter against a target it cannot reach — it runs to its bounds and spends the damage on the
   rows it CAN affect.** The joint fit of L 605 is rejected, and the way it fails is the lesson. Re-targeting
   `twin_isf_mult` from t70 to TDD improved four tier-1 rows on both draws and tier 1 overall (0.148 against rf2\'s
   0.174), but the tier 2/3 cost is **consistent on all three draws**, not noise:

   | row | change in gap, draws 1 / 2 / 3 | mean |
   |---|---|---|
   | `acf_zero_min` | +0.032 / +0.366 / +0.330 | **+0.243** |
   | `circadian_amp` | +0.123 / +0.225 / +0.068 | +0.139 |
   | `night_cv` | +0.176 / +0.184 / +0.030 | +0.130 |
   | `ice_dip_day_share` | +0.061 / +0.106 / +0.027 | +0.065 |
   | `zero_frac` | +0.036 / +0.047 / +0.056 | +0.046 |

   - **The mechanism of the failure:** TDD is unreachable by a body parameter (L 605 — Loop doses from the SETTINGS
     ISF, and `resid_m` pins total glucose), so the fit pushed `twin_isf_mult` to its clip bounds trying anyway. Its
     per-person spread went from [0.88, 1.33] to [0.70, 1.43], and a cohort of more extreme sensitivities has more
     extreme dynamics — which is exactly where the damage appears (`acf_zero_min`, `circadian_amp`, `night_cv`).
   - **So the diagnosis is not "the joint fit is a bad idea" but "TDD is the wrong target for it".** A second fitted
     parameter needs a target that is both REACHABLE and signal-bearing. TDD is signal-bearing and unreachable; t70,
     its current target, is reachable and noise-dominated (L 602). Neither is right, and finding one that is both is
     the open question — the per-person t54 or TIR are candidates, since the low rows did respond to body parameters
     all session.
   - **`twin_isf_mult` therefore stays on its t70 target** (the status quo), with the caveat recorded that the target
     is noise-dominated, which bounds how much that fit can be trusted. Fitting to noise at least keeps the parameter
     near 1.0 on average; fitting to an unreachable target does not.

607. **At five draws the "excess shallow lows" limit DOES NOT EXIST — t70's bias is −0.004 — and the real outcome
   biases are TDD and TIR.** L 602 showed the low rows\' three-draw scatter exceeded their bias and prescribed more
   draws before another arm. Two more (seed0 13000, 17000) of the reference and of `cr_tau_off` 60:

   | row | twin mean (5 draws) | bias vs donors | sd | bias / SE | verdict |
   |---|---|---|---|---|---|
   | **t70** | 1.595 | **−0.004** | 0.358 | −0.02 | **no bias** (read +0.199 at n = 3) |
   | t54 | 0.142 | −0.048 | 0.054 | −1.96 | suggestive, twins UNDER the donors |
   | lows / day | 0.950 | −0.050 | 0.185 | −0.60 | no bias |
   | P(reach 54) | 0.184 | −0.028 | 0.019 | −2.61 | small real bias, twins under |
   | **TIR** | 69.804 | **−2.078** | 2.189 | **−2.12** | **real, and was NOT on the limits list** |
   | **TDD** | 42.059 | **+3.359** | 1.508 | **+4.98** | **real and robust** |

   - **"The twins run excess shallow lows" is removed from the limits.** It was three-draw noise: draws 4 and 5 came
     in at t70 1.199 and 1.385, pulling the five-draw mean to 1.595 against the donors\' 1.599. Every low-side arm
     this session — `pro_g_own`, `pro_carb_fix`, `pro_shift`, `sg_h_lo` suppressed and not, `cr_tau_off` — was
     chasing a gap that is not there, and if anything the twins now sit slightly BELOW the donors on t54, lows/day
     and P(reach 54). The rejections were right; the stated reason was wrong.
   - **TIR is a real bias nobody had listed**: −2.08 points (t = −2.12). It is marginal and partly driven by draw 4
     (66.5), so it needs confirmation, but it belongs on the list where t70 used to be.
   - **TDD is confirmed as the one robust outcome bias** (t = +4.98) — and L 605 showed it is not reachable by any
     body parameter, since Loop doses from the SETTINGS ISF and `resid_m` pins total glucose.
   - **`cr_tau_off` 60 is properly rejected**: five-draw mean 0.393 against the reference\'s 0.380, losing on draws
     3, 4 and 5 after winning tier 1 on 1 and 2.
   - **The method point, which is the transferable part:** a limit quoted from three draws can be pure scatter. Before
     building a mechanism for a gap, check `bias / SE` over the draws available — at n = 3 the SE is large enough that
     a 0.2-percentage-point t70 gap and a zero gap are indistinguishable. Six arms and most of a session went into a
     gap with bias/SE = −0.02.

608. **Do not promote TIR to a limit yet — its decomposition does not close.** L 607 found TIR the second real
   outcome bias (−2.08 points, t = −2.12 over five draws). Decomposed over the same five draws:

   | row | twin mean | donors | bias | bias / SE |
   |---|---|---|---|---|
   | t70 | 1.595 | 1.599 | −0.004 | −0.02 |
   | t180 | 26.835 | 25.884 | +0.951 | +1.06 |
   | TIR | 69.804 | 71.882 | **−2.078** | **−2.12** |

   - **Neither tail accounts for it.** t70's bias is zero and t180's is not significant, yet TIR is down 2.08. And the
     three bands do not sum to 100 on either side — twins 97.3-99.7, donors 99.4 — so some time is in none of them.
   - **It is not sensor coverage:** `wear` matches on every draw (0.970-0.980 against the donors' 0.974).
   - So there is a bookkeeping subtlety in how the bands are computed (different denominators, or a band boundary that
     is not shared) that I have not resolved, and TIR's −2.08 cannot be attributed to a glucose-distribution defect
     until it is. **Reconcile the bands before treating TIR as a limit**; on the numbers as they stand it is marginal
     (t = −2.12) and partly driven by draw 4 (TIR 66.5, t180 29.7).
   - The one outcome bias that is both significant and attributable remains TDD (t = +4.98), and L 605 showed it is
     not reachable by a body parameter.

609. **The band sums were a median artefact, the TIR "bias" is trait-draw sampling, and the session\'s real constraint
   is statistical power: the cohort needs 10-20 draws to resolve the effects candidates produce.** Finishing L 608\'s
   reconciliation:
   - **Why the bands do not sum to 100: medians.** `tir`, `t70` and `t180` are mutually exclusive and exhaustive on
     the same vector (`traits.py`: 70 <= v <= 180, v < 70, v > 180), so they sum to exactly 100 PER BLOCK. The scored
     values are medians across blocks and people, and medians are not additive. Nothing is wrong, and a band gap can
     never be decomposed by comparing medians — use paired per-person differences.
   - **The TIR deficit is between DRAWS, not a defect.** Paired per-person TIR diff by draw: −0.14 / −0.94 / −0.44 /
     **−4.50 / −4.48**. Two candidate explanations, both tested and rejected: the level fit\'s coverage (draws 3-5 all
     have the SAME ~28% of people on templates `lvl_resid` never saw, yet differ 10x in TIR) and fitted-vs-unfitted
     within a draw (rf2_13k: −5.25 fitted against −6.18 unfitted — the deficit is in both). What remains is the trait
     draw itself: the per-person trait sampling moves cohort TIR by ~5 points.
   - **So the real constraint is power.** Between-draw sd and the draws needed for 2 SE to fall under a typical
     candidate effect:

     | row | sd across 5 draws | bias | draws needed |
     |---|---|---|---|
     | TIR | 2.189 | −2.078 | **20** (to resolve 1.0 point) |
     | t70 | 0.358 | −0.004 | **13** (to resolve 0.2) |
     | t54 | 0.054 | −0.048 | 5 (to resolve 0.05) |
     | TDD | 1.508 | +3.359 | **10** (to resolve 1.0 U/day) |

     **TDD is the only row whose bias exceeds its own between-draw sd.** Everything else this session was judged at
     n = 2-3 draws where 2 SE is 2-4x the effect being tested — which is why candidates kept winning on some draws and
     losing on others, and why six low-side arms produced six different-looking answers to the same question.
   - **Practical upshot for the next session:** either run 10+ draws for any candidate touching TIR / t70 / TDD, or
     judge candidates on paired per-person differences (which remove the trait-draw variance by construction, `twin.csv`)
     rather than on cohort medians. The second is far cheaper and is what `twin.csv` already computes.
   - **A latent bug found doing this:** `lvl_resid.py` and `tdd_isf.py` glob `v0*`, which matches seeds 1000-9999 but
     NOT seeds >= 10000 (v13000, v17000). Any fit run on a high seed silently sees zero people.

610. **Re-judged on paired per-person differences — the instrument L 609 says to use — `rf2`\'s adoption was a 57%
   improvement, not the "level" the cohort score reported, and every rejection this session holds.** Sum of
   |median(twin − its own donor)| over TIR, bg_mean, t70, t54 and TDD, averaged over the available draws
   (`twin.csv`; this removes the trait-draw variance that L 609 showed dominates cohort medians):

   | arm | TIR | bg_mean | t70 | t54 | TDD | total |
   |---|---|---|---|---|---|---|
   | **rf2 (adopted)** | −0.51 | +0.20 | −0.03 | −0.05 | +1.49 | **2.28** |
   | `cr_tau_off` 60 | −0.26 | −0.54 | −0.06 | −0.06 | +1.42 | 2.34 |
   | joint fit | −0.77 | +0.13 | −0.04 | −0.06 | +1.40 | 2.40 |
   | `unl_mult` 0.70 + refit | +0.61 | −1.63 | −0.21 | −0.07 | **+0.40** | 2.92 |
   | `sg_h_lo` suppressed | +0.48 | −0.95 | −0.10 | −0.07 | +1.32 | 2.93 |
   | `sg_h_lo` unsuppressed | +0.50 | −1.73 | −0.11 | −0.07 | +1.15 | 3.57 |
   | ov0 (previous reference) | −2.03 | +1.66 | +0.07 | −0.05 | +1.56 | 5.36 |
   | `pro_g_own` | −1.84 | +1.73 | −0.05 | −0.04 | +1.75 | 5.41 |

   - **`rf2` is the best arm on the low-variance instrument and by a wide margin over ov0** — 2.28 against 5.36, a
     57% cut, carried by TIR (−2.03 → −0.51) and the glucose level (+1.66 → +0.20). The cohort score read that change
     as "level" (0.372 → 0.370) because the trait-draw variance swamps it. **Dropping the residual\'s dynamic part was
     a much bigger win than it was credited with**, and the per-person rho table of L 592 was pointing at the same
     thing.
   - **Every rejection holds.** `cr_tau_off` (2.34) and the joint fit (2.40) sit just behind the reference, and the
     `sg_h_lo` variants and `pro_g_own` are clearly worse. None was rejected on trait-draw noise.
   - **And the load cut is confirmed as the only real TDD lever:** `unl_mult` 0.70 + refit gives paired TDD **+0.40**
     against the reference\'s +1.49, a 73% reduction of the one bias that exceeds its own between-draw sd — at the cost
     of the level (bg_mean −1.63). That is L 604\'s trade stated on the right instrument: the level and TDD cannot both
     be matched, and which to spend is a judgement, not a measurement.
   - **Standing guidance:** quote paired per-person differences for any adoption decision. Three of this session\'s
     conclusions (`rf2` level-vs-large, the TIR "bias", the low-side limits) came out differently on cohort medians
     than on paired diffs, and the paired ones are right by construction.

611. **The paired-instrument lesson does NOT transfer to the natural experiments, and the prediction half is limited by
   the FIELD\'s measurement error, which no number of draws can fix.** L 610 showed paired per-person differences are
   the right instrument for cohort adoptions. The obvious next step was to apply it to change prediction — regress
   each twin\'s change directly on its own event\'s field change, one regression instead of `score_change.py`\'s two.
   - **It gives slopes of +0.00 to +0.03 for every arm**, including the reference and all candidates, which is not a
     finding about the model: the field change is a NOISY regressor (one person\'s real two-week difference either side
     of one edit), so regressing twin on field attenuates the slope toward zero — textbook regression dilution.
     `score_change.py` regresses each side on the KNOWN, noiseless insulin index x = log(basal ratio) − log(ISF ratio)
     and compares slopes, which is the correct design and is why it reports ratios near 2 rather than 50.
   - **So the existing natural-experiment methodology is right and should not be "improved" this way.** The paired
     trick works for cohort statistics because a donor\'s own 13-day block statistic is a low-noise quantity; it fails
     here because a single edit\'s field response is not.
   - **And it bounds what the prediction half can show.** With 63 edit events, each contributing one noisy field
     response, the field / twin response ratios carry CIs like [1.22, 3.79] (ad3) and [1.41, 9.72] (ov0 on t70). The
     reference\'s improvement — t70 ratio 3.51 -> 2.17 — sits inside those intervals. **More simulation draws cannot
     narrow this**: the limiting variance is in the field, which has one realisation per event. Narrowing it needs more
     EVENTS (the x and e pools exist, 790 edits, L 532) or edits with larger settings changes, not more compute on the
     108 already used.
   - **Honest status of the prediction half:** `rf2` is the best arm measured (t70 response 2.17 against ad3\'s 3.38
     and ov0\'s 3.51, with the least damped mean and TIR of the adopted lineage), and that improvement is not
     separable from noise at n = 63 events. Quote it as "best measured, not established", and spend the next effort on
     the larger event pools rather than on another candidate.

612. **On 580 events the adopted change is confirmed on the prediction half: `rf2` beats ov0 on all four response
   ratios and all three correlations, with the t70 response at 1.14 against the field\'s 1.0.** L 611 showed the pilot
   pool\'s 108 events cannot separate the arms (CIs like [1.41, 9.72]) and that only more EVENTS can narrow them. The
   e pool (built 2026-10-28, its own templates, field reference and harness) has 588; run with the two arms identical
   but for the single adopted flag:

   | | mean | TIR | t70 | t54 | rho mean / TIR / t70 | level vs field pre |
   |---|---|---|---|---|---|---|
   | ov0 (`resid_mult` 0.6) | 1.60 [1.24, 2.00] | 1.37 [0.93, 1.91] | 1.43 [0.77, 2.22] | 0.91 | 0.26 / 0.13 / 0.15 | +5.4 |
   | **rf2 (`resid_mult` 0.0)** | **1.35 [1.04, 1.69]** | **1.27 [0.92, 1.76]** | **1.14 [0.56, 1.90]** | 0.58 | **0.33 / 0.16 / 0.17** | **+3.3** |

   - **Seven comparisons, all favouring rf2**: four ratios closer to 1.0, three correlations higher, plus a starting
     level nearer the field\'s pre-edit value (+3.3 against +5.4). The CIs overlap, so no single comparison is
     individually significant — but the consistency across seven is the evidence, and the e pool\'s intervals are
     about **twice as tight** as the pilot pool\'s ([1.24, 2.00] against [1.22, 3.79] on the mean), exactly as L 611\'s
     event-count argument predicted.
   - **The t70 response is now 1.14 — the field\'s own, within 14%** — on the metric change prediction is judged by
     (TIR and t < 70, Pete 2026-10-26), against the standing limit that a settings change is damped to about half the
     field\'s. The mean ratio 1.35 is the least damped of any arm measured on any pool.
   - **One caveat recorded honestly:** t54 goes 0.91 -> 0.58, i.e. the twins now OVER-respond on t54. With the t54
     change too rare to rank candidates on (AGENTS.md) and its CI [0.28, 1.05] wide, this is a flag rather than a
     finding, but it is the one row where the change moved away from the field.
   - **Absolute levels differ by pool and only the ordering transfers:** the e pool\'s field t70 response is +2.00
     against the pilot pool\'s +4.46, so the pilot pool\'s ratios (rf2 2.17, ov0 3.51) and the e pool\'s (1.14, 1.43)
     are not comparable in level — but both rank the arms the same way. Quote ratios with their pool.

613. **(⚠ HALF RETRACTED — L 632: the `sg_h_lo` arm (`hl_e`) was a silent NO-OP, because the change harness pinned
   an Oct-28 frozen tree that has no `sg_h_lo`. Its "neutral on change prediction" verdict is an artifact of the arm
   not running, and sg_h_lo's change response is UNMEASURED pending the re-run. The `si_norm` half STANDS — that knob
   is in the pinned tree and `sn_e`'s numbers genuinely differ.)**
   **Both pending decisions resolve on 580 events: `si_norm` 1.0 is NO, and `sg_h_lo` is neutral on change
   prediction so its case rests entirely on the cohort trade.** Both had been judged on the pilot pool\'s 108 events,
   where L 611 showed the CIs cannot separate arms. On the e pool, all three arms on the rf2 baseline:

   | | mean | TIR | t70 | t54 | rho mean / TIR / t70 | level vs field pre |
   |---|---|---|---|---|---|---|
   | **rf2 (reference)** | **1.33 [1.03, 1.68]** | **1.28 [0.87, 1.76]** | 1.15 | 0.56 | **0.33 / 0.16 / 0.17** | +3.3 |
   | `si_norm` 1.0 | 1.55 [1.12, 2.03] | 1.54 [1.07, 2.27] | 1.33 | 0.75 | 0.31 / **0.09** / 0.14 | +1.6 |
   | `sg_h_lo` 0.0019 | 1.36 [1.06, 1.67] | 1.29 [0.90, 1.77] | **1.10** | 0.59 | 0.33 / 0.16 / 0.17 | +3.3 |

   - **`si_norm` 1.0: decided NO.** Its TDD rationale was withdrawn in L 597 (the level refit converts the sensitivity
     gain straight back into insulin) and its ONLY remaining case was the change response — "the least damped of any
     arm" on the ad3 base, t70 ratio 2.09 against 3.32. At 5.4x the events it is **more** damped on every outcome
     (mean 1.55 against 1.33, TIR 1.54 against 1.28, t70 1.33 against 1.15) and its TIR ranking is halved (rho 0.09
     against 0.16). Both rationales are now refuted on the better-powered pool, so the decision does not need Pete:
     **it stays at 0.92.** What remains in its favour — better per-person rho and "better explained" — does not
     outweigh worse low-side fidelity AND a worse change response.
   - **`sg_h_lo`: neutral on change prediction** — within rounding of the reference on all four ratios and all three
     correlations, which is expected since it acts inside lows rather than shifting the response to an edit. So its
     case is exactly the cohort trade and nothing else: it closes the t70 cohort gap (draw 2, 0.325 -> 0.034) and
     overshoots the low counts (lows/day 1.000 -> 0.833, P(reach 54) 0.195 -> 0.200/0.176). **Still Pete\'s call, but
     now cleanly scoped to one trade with no hidden cost on the prediction side.**
   - **Method note:** this is what the event pools are for. Two decisions sat open for a session on 108 events; 580
     settled one outright and scoped the other. Judge a candidate\'s change response on the e pool before asking Pete.

614. **The x pool partially replicates L 612: the RATIO improvement holds, the CORRELATION improvement is e-pool
   only, and the x pool is too weakly conditioned to settle either.** L 612 confirmed rf2 over ov0 on the e pool\'s
   580 events across seven comparisons; that rested on one pool, so the same two arms (identical but for
   `resid_mult`) were run on the x pool — 152 events, different donors, its own templates and field reference.

   | | mean | TIR | t70 | TIR rho | t70 rho |
   |---|---|---|---|---|---|
   | ov0 | 0.64 [0.05, 1.34] | 0.62 [0.11, 1.36] | −0.39 | **0.28** | **0.22** |
   | **rf2** | **0.70 [0.06, 1.54]** | **0.74 [0.14, 1.57]** | −0.58 | 0.19 | 0.05 |

   - **Ratios replicate** (closeness to the field\'s 1.0): rf2 is better on mean (|1 − 0.70| = 0.30 against 0.36) and
     on TIR (0.26 against 0.38). **Correlations do not**: TIR rho 0.19 against 0.28, t70 rho 0.05 against 0.22 — the
     opposite of the e pool, where rf2 led on all three.
   - **But the x pool is poorly conditioned for this question.** Its field responses are a third of the e pool\'s
     (mean −8.41 against −23.50) and two are NEGATIVE — field t70 **−0.57**, i.e. across these edits more insulin was
     followed by FEWER lows in the field — so the ratios have the twins over-responding (< 1) and the low-side ratios
     come out negative with CIs spanning zero ([−2.82, 1.40] and [−14.06, 11.56]). A pool whose field response has
     the unexpected sign on t70 cannot adjudicate a candidate\'s t70 response.
   - **So the honest status of rf2\'s prediction claim:** the response-SIZE improvement replicates across two
     independent pools; the response-RANKING improvement is e-pool only and reverses on the x pool. **Quote it as
     "size replicated, ranking e-pool only"**, not as confirmed outright, and prefer the e pool for change questions —
     it has 4x the events and a field response of the expected sign and magnitude.
   - **Pool conditioning is itself worth checking before using a pool:** report the FIELD response per log-unit
     insulin first. The e pool\'s −23.50 mean / +2.00 t70 are sensible; the x pool\'s −8.41 / −0.57 are not, and that
     explains why every x-pool ratio in the role doc\'s history reads below 1 while every e-pool and pilot-pool one
     reads above.

615. **L 594\'s unification is too strong, and the correction is useful: low-side RECOVERY and REVERSAL SPEED are two
   defects with two different levers, not one.** L 594 read `acf_zero_min`, the post-meal fall / rise ratio and the
   fast-fall tail as one defect — the twins\' glucose reverses too slowly — on the grounds that only gastric emptying
   shape moved any of them. `cr_tau_off` (L 601) is the time-asymmetric mechanism L 600 specified, and it was judged
   on the low rows and the cohort score but never on the reversal rows it was ultimately aimed at. Measured now:

   | | `acf_zero_min` (donors 40) | fall / rise ratio (0.89) | low-side rows |
   |---|---|---|---|
   | rf2 | 60 / 55 | 0.63 | t54 0.124 / 0.232, dwell < 70 20 min |
   | `cr_tau_off` 60 | 60 / **60** | 0.65 / 0.61 | **t54 0.175 / 0.177, dwell 15 min** |

   - **It moves the recovery rows and not the reversal rows.** t54 goes from 0.124 / 0.232 to 0.175 / 0.177 against the
     donors\' 0.190, and the nadir dwell under 70 lands exactly on the donors\' 15 min — while `acf_zero_min` does not
     move (and is worse on draw 2) and the meal ratio stays at 0.61-0.65.
   - **So the two are separable**, and L 594\'s "three limits, one missing shape" over-claimed. Low-side recovery
     responds to counter-regulatory TIMING; the reversal-speed rows respond only to gastric emptying SHAPE (`ge_beta`,
     the one lever that ever moved `acf_zero_min`, 60 -> 55). Neither is adoptable — `cr_tau_off` loses on five draws
     and `ge_beta` compresses the meal pulse — but they are two targets, not one, and a mechanism aimed at one should
     not be expected to pay on the other.
   - **The practical consequence:** the "three limits rest on one study" framing of L 589 / 594 should read as TWO
     threads. The sub-basal evidence request covers the low-side recovery rows. `acf_zero_min` and the meal ratio need
     something in the APPEARANCE path that sharpens the finish without compressing the pulse — which `meal_lag` could
     not be (shift-invariant, L 595) and `ge_beta` was not (compressing, L 591).
   - **And the method point, again:** judge a mechanism on the row it was built for. `cr_tau_off` was specified by
     L 600 from the low-episode duration gap, tested on the low rows, and its headline rejection came from the cohort
     score — the reversal rows it was nominally aimed at went unmeasured for three turns.

616. **Pooled over the two well-conditioned pools, rf2 leads on all three change-response correlations — but by
   0.5-1.2 SE, so "consistent, not established" is the accurate phrasing.** L 612 confirmed the ranking on the e pool
   and L 614 found the x pool reverses it, leaving the claim resting on one pool. Combining the pilot pool (63 events)
   and the e pool (580) by Fisher z weighted by n − 3 — the x pool excluded because its field t70 response is −0.57,
   the unexpected sign (L 614) — over **643 events**:

   | row | ov0 | rf2 | difference in z | SE | z / SE |
   |---|---|---|---|---|---|
   | mean | 0.265 | **0.326** | +0.067 | 0.056 | +1.20 |
   | TIR | 0.132 | **0.165** | +0.034 | 0.056 | +0.60 |
   | t70 | 0.157 | **0.187** | +0.031 | 0.056 | +0.55 |

   - **rf2 leads on all three, none individually significant.** The three rows are not independent, so the
     consistency is weaker evidence than three separate tests would be — but the direction is the same on both pools
     for every row, which is the strongest statement the data support.
   - **So the final phrasing for rf2\'s prediction claim:** response SIZE replicated on two independent pools
     (L 612, 614); response RANKING leads on all three correlations pooled over 643 well-conditioned events at
     0.5-1.2 SE — **consistent, not established**. Neither "confirmed" nor "e-pool only" was right.
   - **And the pooling itself is the reusable part:** the pools can be combined by Fisher z on their correlations and
     by inverse-variance on their ratios, as long as poorly-conditioned pools are excluded on their FIELD response
     rather than on their results. That is how to get the most out of 790 edits without letting one bad pool dominate.

617. **The stomach\'s transit DISPERSION is one defect behind four standing limits: raising the Erlang order closes
   the 3-hour meal change, gives `acf_zero_min` its best value ever and moves the fall / rise ratio furthest — at the
   cost of running high.** L 615 specified a mechanism in the appearance path that sharpens the finish without
   compressing the pulse. The stomach has been Erlang-2 (Dalla Man / UVA-Padova); `ge_order` raises the transit order
   with `kempt` scaled by order / 2, so the MEAN transit is unchanged by construction and only the dispersion falls.
   Order 2 is bit-identical to the previous model.

   | | meal_d3h (38.0) | `acf_zero_min` (40) | fall / rise (0.89) | TIR (71.9) | t180 (25.9) | score |
   |---|---|---|---|---|---|---|
   | rf2 | 31.0 / 31.0 | 60 / 55 | 0.63 | 72.2 / 71.3 | 25.8 / 24.3 | 0.332 / 0.371 |
   | order 3 | **37.0 / 35.0** | 55 / 55 | 0.63 | 68.5 / 67.4 | 28.6 / 27.1 | 0.336 / 0.385 |
   | order 4 | **39.0 / 36.0** | 55 / **50** | **0.69** | 68.6 / 67.1 | 28.1 / 28.0 | 0.412 / 0.442 |

   - **The meal tail is closed.** "Meals come down sooner than the donors\'" has stood since L 368-370: meal_d3h 31.0
     against 38.0 (gap 0.373). Order 3 gives 37.0 and order 4 gives 39.0 — gap **0.053**. Every previous attempt
     (`meal_wave2`, `meal_slow`, `ppr_a`, `csf_lvl`, protein) moved it by a point or two or traded the peak.
   - **`acf_zero_min` reaches 50** (gap 1.320 -> 0.739 on draw 2), its best value in the model\'s history; `ge_beta`
     managed 55 and nothing else moved it at all. The fall / rise ratio reaches 0.69, also the furthest yet.
   - **So transit dispersion unifies four rows** — the meal tail, the reversal-speed pair, and the pulse decay shape.
     This is the unification L 594 claimed on weaker grounds and L 615 had to retract: here one parameter moves all
     four in the right direction at once, which is what a shared cause looks like.
   - **The cost is a high-side one and it is large**: TIR 72.2 -> 68.6 and t180 25.8 -> 28.1 (donors 25.9), because
     less dispersion delivers the same carbohydrate in a shorter window and Loop cannot cover the peak. The score
     rejects it (0.412 / 0.442 at order 4). **Not adopted.**
   - **Where it points:** the twins\' appearance is too dispersed AND their dosing cannot cover a sharper one. If the
     transit order is right at 3-4, the missing partner is on the dosing side — earlier or larger meal boluses — which
     is a behaviour trait (`bolus_lead_min`, `p_bolus_ann`) fitted per donor, not a physiology change. **Test
     `ge_order` 3 together with the donors\' own bolus timing before judging either.**
   - **Method note, third instance:** the labelled `peak_h` moved 43 -> 37 while the isolated-parcel peak did not move
     at all, because `peak_h` is onset-relative (L 595) and a sharper rise shifts the detected onset later. Measure
     absolute appearance time on the parcel; measure `peak_h` only against another `peak_h`.

618. **Correction to L 617\'s next step: the dosing side is ALREADY per-donor, so the high-side cost of a sharper
   transit is a clash between two independently calibrated components, not a missing behaviour fit.** L 617 proposed
   testing `ge_order` 3 "with the donors\' own bolus timing". That premise is false — `bolus_lead_min`, `p_bolus_ann`
   and `bolus_ratio` are all in `person.BEHAVIOR_COLS` and read per donor (`behavior.py` 323, 328), so each twin
   already boluses at its donor\'s own lead time, announces at its donor\'s rate and doses at its donor\'s ratio. The
   test as stated would have been a no-op, and checking the premise cost two minutes against a 20-minute arm.
   - **What the cost therefore means.** With the donors\' own dosing habits AND a less dispersed appearance, the twins
     run high (TIR 72.2 -> 68.6, t180 25.8 -> 28.1). The donors do not. So either their appearance is not actually
     sharper than the model\'s — and the labelled decay evidence (67 against 60 min) misled me — or the twins\' insulin
     cannot cover a sharper peak that the donors\' insulin does.
   - **The second reading names a specific clash:** `ge_order` would be fitted to the donors\' labelled pulse shape,
     while insulin action is fitted to the lispro clamp (`p2` 0.025, L 362-365). If appearance sharpens at fixed
     insulin speed, the mismatch shows up exactly as a high-side cost. **Both parameters are independently calibrated
     to their own evidence, so the clash says one of the two calibrations is wrong, and the cohort cannot say which.**
     That is a genuine evidence question, not a tuning one: it needs a study with simultaneous appearance and insulin
     kinetics after a mixed meal.
   - **So `ge_order` stays at 2** with its result recorded: it is the only lever that moves four limits at once
     (L 617) and its cost is diagnostic rather than disqualifying. Anyone revisiting the meal tail should start here
     and should pair it with the insulin-action question, not with a behaviour refit.

619. **The labelled pulse shape is ICE-based, so the appearance evidence is insulin-free — which resolves L 618\'s two
   readings into one: the model\'s insulin action is too slow for the donors\' appearance, or its appearance is right
   and the insulin fit is wrong.** L 618 left two possibilities for `ge_order`\'s high-side cost. The first — that the
   donors\' appearance is not really sharper and the labelled decay misled me — is refuted by what the labeller
   measures: `ice_gen/stats.py` builds every pulse from **`g.ice`**, the insulin counteraction effect, with the
   insulin effect already removed (`base` from the quiet median, `ex = ice − base` smoothed, `size_g` the ICE integral
   over `geq_mgdl`). So `dur_h`, `peak_h` and `size_g` are appearance quantities, not glucose ones.
   - **Therefore the donors\' appearance IS less dispersed than the model\'s** (labelled decay 60 min against the
     twins\' 67, both through the same ICE labeller), and `ge_order` 3-4 moves the model toward the measured truth.
   - **And the high-side cost is then specifically an insulin-action mismatch.** The donors carry the sharper
     appearance without running high; the twins, at their donors\' own bolus timing, rate and ratio (L 618), cannot.
     With appearance now evidenced, the remaining free component is insulin action speed — `p2` 0.025, fitted to a
     lispro CLAMP (L 362-365), which is an intravenous steady-state setting rather than a meal one.
   - **So the evidence request narrows usefully:** not "simultaneous appearance and insulin kinetics" in general, but
     **is clamp-derived insulin action too slow for meal-time action?** That is a specific, answerable literature
     question, and if the answer is yes, `ge_order` 3 plus a faster `p2` is a pair of evidenced changes that between
     them close the meal tail, `acf_zero_min` and the fall / rise ratio without the high-side cost.
   - **Until then `ge_order` stays at 2** — but it is now the only open limit-cluster with a named mechanism on BOTH
     sides and a single literature question standing between it and an adoption. That is the most actionable state any
     of this session\'s limits reached.

620. **Correction and sharpening of L 619: the clamp behind `p2` is SUBCUTANEOUS at 15 U, not intravenous, the
   absorption dose-dependence is already modelled, and the un-modelled part — dose-dependence of the ACTION rate — is
   a limitation the code already flagged. `ge_order`\'s cost is the first quantitative evidence that it bites.**
   - **Factual correction:** `p2` 0.025 comes from a 0.2 U/kg (~15 U) lispro clamp with GIR peak ~100 min (L 9), a
     subcutaneous dose, not an IV steady state as L 619 said.
   - **The absorption side is already dose-corrected.** A4d (`dose_beta`, β 0.1 by default, Heise 2017, L 437) makes a
     depot absorb at `(dose / 15 U)^(−β)`, normalised to 1 AT the clamp dose — so meal-sized boluses already absorb
     faster than the clamp in this model.
   - **What is not corrected is the ACTION rate**, and `p2`\'s own comment says so: "typical boluses and Loop\'s
     automatic doses are ~0.05 U/kg and act sooner (smaller s.c. doses act earlier — direction known, size not found
     for analogues)". So the model carries an action rate fitted at 15 U and applies it to ~4 U doses, with the bias
     in the known direction (too slow) and the magnitude unmeasured.
   - **`ge_order` supplies the first cohort-level evidence that this matters.** Sharpening appearance to the donors\'
     measured dispersion closes four limits and produces a high-side cost (TIR 72.2 -> 68.6, t180 25.8 -> 28.1)
     exactly where an action rate that is too slow for meal-sized doses would produce one. The two are independently
     evidenced and jointly inconsistent, which is a stronger statement than either alone.
   - **So the evidence request is now specific and small:** the dose-dependence of insulin ACTION (not absorption) for
     rapid analogues between ~4 U and ~15 U. If it is found, `ge_order` 3 and a dose-scaled `p2` are a pair that close
     the meal tail, `acf_zero_min` and the fall / rise ratio together. Until then both stay at their fitted values,
     and this lesson is the reason to look for that one number rather than to try another mechanism.

621. **The literature answers L 620\'s question and refutes its hypothesis: the dose-dependent action delay for rapid
   analogues appears at 30-50 U, not between 4 and 15, so `p2`\'s clamp dose does NOT explain `ge_order`\'s cost. And
   order 3 is the data-fitted value, with a 3.7-point TIR cost that is now unexplained.**
   - **The evidence** (Gagnon-Auger et al., *Diabetes Care* 2010;33(12):2502-7, lispro at 10 / 30 / 50 U under
     euglycaemic clamp): at **10 U absorption and glucose-lowering were comparable to controls**; Tmax and GIR_max
     were delayed only at the **higher doses (30 and 50 U)**, and that in OBESE TYPE 2 subjects, where subcutaneous
     depot effects are largest. Supporting: URLi vs lispro across 7 / 15 / 30 U found the formulation difference
     (onset 7-9 min earlier) rather than a dose one. **So between ~4 U and the 15 U clamp dose, in T1D, there is no
     documented action delay** — L 620\'s proposed mismatch is not there, and `p2` 0.025 is defensible for meal doses.
   - **Which leaves `ge_order`\'s high-side cost unexplained.** Appearance dispersion is evidenced (ICE-based labelled
     decay, L 619), dosing is per-donor (L 618), and insulin action is now defensible at meal doses — yet sharpening
     appearance to the donors\' measured dispersion costs TIR. One of those three is still wrong, or the cost is in
     Loop\'s response to a sharper rise rather than in the body at all.
   - **Order 3 is the FITTED order, not a sweep point.** Its labelled decay is 59 min against the donors\' 60
     (order 2 gives 67, order 4 gives 55), so 3 is what the donors\' dispersion implies. At order 3: `meal_d3h`
     37.0 / 35.0 against the donors\' 38.0 (gap 0.373 -> 0.054), `acf_zero_min` 55 / 55, score 0.336 / 0.385 against
     0.332 / 0.371 — **0.009 worse on the mean, where order 4 was 0.060 worse.** The cost is concentrated in TIR
     (68.5 / 67.4 against 72.2 / 71.3) and t180.
   - **So the honest final state of this cluster:** the fitted transit order closes the longest-standing meal limit
     and improves the reversal rows for about 0.009 of score and 3.7 points of TIR, with the TIR cost no longer
     attributable to any evidenced component. **That is a sharper open question than the session started with** —
     "why does matching the donors\' measured appearance dispersion cost time in range?" — and it is a question about
     the controller\'s response, which is where to look next.

622. **`ge_order` 3\'s TIR cost is a DISTRIBUTION effect, not a dosing failure: TDD is flat, so the same insulin meets
   more peaked glucose — and three other rows improve markedly, two of them to near-exact.** Closing out L 621\'s
   question about the controller\'s response:

   | at the fitted order 3 | rf2 | order 3 | donors |
   |---|---|---|---|
   | TDD | 41.88 / 42.61 | **41.88 / 42.61** | 38.70 |
   | bg_mean (gap) | 151.0 / 148.2 (0.037 / 0.175) | 151.5 / **151.5** (0.037 / **0.062**) | 151.9 |
   | zero_frac (gap) | 30.2 / 32.9 (0.238 / 0.092) | **32.5** / 36.2 (**0.061** / 0.313) | 32.5 |
   | meal_d3h (gap) | 31.0 / 31.0 (0.373) | 37.0 / 35.0 (**0.054**) | 38.0 |
   | `acf_zero_min` (gap) | 60 / 55 (1.734 / 1.320) | 55 / 55 (1.272 / 1.165) | 40 |
   | TIR (gap) | 72.2 / 71.3 (0.053 / 0.070) | 68.5 / 67.4 (0.237 / 0.346) | 71.9 |

   - **Loop does not dose more for a sharper meal** — TDD is unchanged to two decimals on both draws — because its
     dose comes from the carb ENTRY and its own absorption model, not from the realised appearance. So the TIR loss is
     the same insulin meeting a more peaked glucose curve, which is a distributional consequence of a more correct
     appearance rather than a failure of any component.
   - **And the same change takes two rows to near-exact:** bg_mean on draw 2 (gap 0.175 -> 0.062) and zero_frac on
     draw 1 (0.238 -> 0.061, 32.5 against the donors\' 32.5). With meal_d3h (0.373 -> 0.054) and `acf_zero_min` that
     is four rows improving, two of them essentially closed, against TIR and t180.
   - **So the honest characterisation of the fitted transit order:** it is a more correct appearance model that costs
     3.7 points of TIR, with the cost mechanically attributable (flat TDD, peakier glucose) and not fixable on the
     body side. Whether to take it is a judgement about which rows the model is FOR — and worth putting to Pete with
     the table above rather than deciding on the weighted score, which reads it as 0.009 worse.
   - **Two further sub-hypotheses for the TIR cost, both closed.** (1) `ge_order` 3 is **neutral on change
     prediction** on the e pool's 580 events (mean 1.35 against rf2's 1.33, TIR 1.27 against 1.28, t70 1.14 against
     1.15, all three rho identical) — so the cost does not extend to the prediction half, and the judgement is four
     cohort rows against TIR with prediction unchanged. (2) The entered CARB ABSORPTION TIME is not the lever: Loop
     doses from it, but the twins draw it from each donor's own `abs_fast` / `abs_slow` shares (77% at 10800 s pooled,
     against the donors' dominant 3-h default), so both sides give Loop the same 3-h assumption against a sharp real
     appearance. The donors cope with that mismatch at TIR 71.9 and the twins do not.
   - **This closes the thread as far as measurement can take it.** The appearance dispersion is evidenced (L 619), the
     dosing is per-donor (L 618), insulin action is defensible at meal doses (L 621), and the residual TIR cost is now
     explained in mechanism if not resolved in value.

623. **The "two compensating errors" hypothesis is REFUTED: cutting the twins' excess glucose load does not pay for
     `ge_order` 3's TIR cost, because the two defects live in different moments of the distribution.** The hypothesis
     (run script `run_ol.sh`, job 152) was that order 2 matches TIR with the wrong appearance dispersion while order 3
     has the right dispersion and the wrong TIR — two errors cancelling in one row — and that L 603's measured 1.10×
     labelled-load excess was the other one. Tested as `ge_order` 3 + `unl_mult` 0.85 / 0.70 on `rf2`, two draws:

     | arm | score d1 / d2 | tier1 d1 / d2 | TIR | bg_mean | t180 | t70 |
     |---|---|---|---|---|---|---|
     | rf2 (order 2) | 0.332 / 0.371 | 0.135 / 0.209 | 72.2 / 71.3 | 151.0 / 148.2 | 25.8 / 24.3 | 1.76 / 2.12 |
     | go3 (order 3) | 0.336 / 0.385 | 0.162 / 0.225 | 68.5 / 67.4 | **151.5 / 151.5** | 28.6 / 27.1 | 2.39 / 2.06 |
     | ol85 | 0.337 / 0.399 | 0.166 / 0.245 | 70.7 / 70.1 | 150.7 / 149.6 | 26.3 / 25.7 | 2.35 / 2.24 |
     | ol70 | 0.361 / 0.397 | 0.204 / 0.257 | **72.8 / 71.7** | 147.5 / 145.9 | 23.7 / 22.6 | **2.51 / 2.50** |
     | donors | — | — | 71.9 | 151.9 | 25.9 | 1.60 |

     - **The load cut DOES recover TIR** (ol70 72.8 / 71.7, the donors' 71.9) **and still scores worse than order 3
       alone on both draws.** Every arm in the ladder is worse than the one before it on score and on tier 1, so the
       two errors are not compensating in any useful sense.
     - **Why: order 3 widens the distribution at a CORRECT mean; the load cut moves the MEAN.** go3 has the best
       bg_mean of any arm (151.5 both draws, gap 0.037 / 0.062 — essentially exact) with t180 AND t70 both raised
       (28.6 / 2.39 against the donors' 25.9 / 1.60). That is a spread defect. `unl_mult` is a level lever: it buys
       the highs back (t180 23.7) by pushing glucose down 4.4 mg/dL and spending the low side (t70 2.51, the worst of
       any arm tested; t54 up too). ol70's TIR is a coincidence of that trade netting out, not a repair.
     - **Read TIR with bg_mean and t70 beside it, never alone.** On this ladder TIR is non-monotonic in load while
       every structural row degrades monotonically — an arm can land on the donors' TIR from a distribution that is
       wrong on both sides at once.
     - A level refit (L 525) would re-absorb the mean drop, but it cannot help: it would restore the level and hand
       back the highs, returning to go3. The lever for a spread defect at a correct mean is not load.
     - **`ge_order` stays at 2** and the judgement posted to Pete (four cohort rows better vs 3.7 TIR points,
       prediction neutral, L 622) stands unchanged — this test adds no third option.

624. **L 584's hanging question is answered and its suspicion refuted: the twins' basal is NOT near-constant. Its
     day-to-day AMPLITUDE is near-exact; the whole deficit is persistence.** L 584 closed with "if the twins' basal
     CV is far below 0.23, that is the defect and it is a named one" — and 0.23 was itself a long-record figure
     (the L 585 trap again). Measured like for like, within 13-day blocks on both sides
     (`resid_tools/twin_limb_ac.py`, new, and `tdd_blocks.py` + its CV counterpart), basal reconstructed as a
     per-minute last-writer-wins assignment from `trace.json`'s tagged `delivery[]`:

     | limb | donor CV (within 13 d) | twin CV (rf2 / rf2_5k) | donor ac1 (within 13 d) | twin ac1 |
     |---|---|---|---|---|
     | basal | 0.176 (long record 0.229) | **0.170 / 0.172** | +0.075 | −0.038 / −0.035 |
     | bolus | 0.289 (long record 0.348) | 0.329 / 0.313 | +0.066 | −0.010 / +0.028 |
     | total | 0.173 | — | +0.085 | +0.002 / −0.013 |

     - **Basal day-to-day variation is already right** (0.170 against 0.176) and the bolus limb varies slightly MORE
       than the donors' (0.329 against 0.289). There is no missing day-to-day basal-need amplitude to add.
     - **Both limbs are short of the donors' persistence by a similar absolute amount** (basal 0.11, bolus 0.06–0.08
       in correlation units), which is the same "variation without persistence" signature L 582 found when the life
       modulators were switched on with `day_rho` 0 — now confirmed in the delivered insulin itself, limb by limb.
     - This is consistent with, and does not reopen, L 586's closure: the remaining reproducible `ac1` gap is day-level
       glucose persistence, and `day_rho`'s transmission ceiling (+0.02) is below it. The value of this measurement is
       negative and worth having — it **removes the last named candidate** that was still written as a next step, so no
       future session spends an arm on a day-to-day basal-need driver.
     - The donors' basal share of TDD (0.37) is reproduced too: twins 0.40 / 0.35.
     - **`tdd_blocks.py`'s footer previously hardcoded twin figures from the superseded `dr2` arm.** Twin-side numbers
       now come from `twin_limb_ac.py` on the current reference; never read a hardcoded comparison figure as current.

625. **Two scored rows compare two different quantities: the donors' stored pulse labels are STALE and carry the raw
     argmax peak and the run length, while the twins' carry the fitted lognormal mode and the fitted 90th percentile.
     Measured like for like, `pulse_peak_h`'s gap REVERSES SIGN and `pulse_dur_h` goes from near-passing to a 30%
     defect.** Found by pulling the thread on `pulse_peak_h` being **0.622 for every arm tested** — order 2, order 3
     and both load cuts, identical to three decimals, while the appearance dispersion underneath them changed
     materially (L 622). A row invariant to the mechanism it is supposed to measure is measuring something else.

     - **The signature.** `ice_gen.meals.fit_shapes` (commit ece70cb1) fits each pulse's lognormal over a 24-cell log
       grid `FIT_MODES`, so a fitted `peak_h` is one of 24 values. **100% of donor `peak_h` values are exact multiples
       of 5 min and 0% are grid cells; 99.9% of the twins' are exact grid cells and 0.1% are 5-min multiples.** The
       donors' numbers are `label()`'s raw `pk * 5/60` argmax; the twins' are `fit_shapes`'s `mode`. All 168 donor
       files are stale — a uniform version skew, not a mixture. Their lumpy cell histogram (exactly 0.0% in cells 1,
       3, 5 and 8, neighbours at 2–8%) is the raw 5-min lattice seen through the fitted grid, not physiology.
     - **Re-running the CURRENT labeller on the donors moves every one of them the same way** (42 donors, 31.3k
       pulses; `resid_tools/relabel_donors.py`): peak_h median 0.750 → **0.536**, dur_h 1.833 → **1.463**, while
       `size_g` barely moves (27.1 → 26.6), so pulse detection is stable and the change is specifically the shape
       fit. **All 42 donors move down and none up**, and the sample's STORED median is 0.750 — exactly the scored
       donor target — so the sample reproduces the population statistic and the shift is the whole story.

       | row | donors as scored | donors, current labeller | twins (rf2) | verdict |
       |---|---|---|---|---|
       | `pulse_peak_h` | 0.750 | 0.536 ⚠ | 0.622 | ⚠ **SUPERSEDED by L 626: on all 168 donors it is 0.622 and the gap VANISHES**, it does not reverse — 0.536 is the first 45 aliases only |
       | `pulse_dur_h` | 1.917 | 1.463 ⚠ | 1.885 | ⚠ L 626: 1.577 on all 168; the direction holds, twins ~19% too long |

     - **The scored median was additionally quantization-pinned**, which is why no arm could move it: the grid spacing
       near the twins' value is 3.4–5.9 min, so a sub-cell shift never changes the median. The MEAN is not pinned and
       did move — rf2 0.878, go3 0.853, ol70 0.840 — so the mechanisms were acting all along, invisibly.
     - **It changes the `ge_order` reading in its favour.** Order 3 shortens and advances the labelled pulse
       (mean 0.878 → 0.853, decay 67 → 59), which the stale target scored as moving away from the donors. Against
       correctly-labelled donors the twins' pulses are too LATE and too LONG, so order 3 moves toward them on this
       axis as well as closing `meal_d3h`. Pete's pending judgement should be read with this correction.
     - **Do not re-fit anything to these two rows until the donor labels are regenerated**, and treat any past
       conclusion that leaned on them as unsupported. The twins' own `run_h` (the run length, 100% 5-min multiples)
       is already in `meals_labeled.csv` and is the like-for-like partner for the donors' stored `dur_h`.
     - Regenerating `ice_v32/meals` is the **ice** role's data, shared with the generator, so it goes out as a
       handoff rather than a unilateral change.
     - **General trap**: when a statistic is identical across arms that should move it, suspect the measurement, not
       the model — and check the two sides' values for a lattice (are they all multiples of something? all members of
       a fitted grid?). That one test found this in a minute after four arms had been spent around it.

626. **Correction to L 625, and the corrected appearance picture: `pulse_peak_h`'s gap does not reverse — it
     VANISHES. The real appearance defects are DURATION (19% too long) and PEAK HEIGHT PER GRAM (10% low), with
     time-to-peak already exact.** ice regenerated all 168 donors with the current labeller
     (``~/.loop-eval/ice_v32/meals_fit/``, code rev 67be7d92, `../meals` left in place), so the two rows can be scored
     like for like instead of estimated. Scored in the scorer's own convention — per-person median, then cross-person,
     non-rescue pulses only:

     | row | donors STALE (scored) | donors FITTED | twins rf2 / rf2_5k | go3 / go3_5k | corrected verdict |
     |---|---|---|---|---|---|
     | `pulse_peak_h` | 0.750 | **0.622** | 0.622 / 0.622 | 0.622 / 0.622 | **exact — no gap at all** |
     | `pulse_dur_h` | 1.917 | **1.577** | 1.876 / 1.863 | 1.853 / 1.803 | twins **~19% too long** (scored as near-passing) |
     | `pulse_peak_per_g` | 1.175 | 1.190 | 1.043 / 1.056 | 1.072 / 1.090 | ~10% low; unaffected by staleness, always real |

     - **Where L 625's "reverses sign" came from: a non-representative sample, not a convention.** Pooled and
       per-person medians agree exactly on all 168 donors (0.622 both ways), but the **first 45 aliases give 0.536** —
       `relabel_donors.py` walked `persons.csv` in order, and on a 24-cell log grid a median hops a whole cell easily.
       Two thirds of a cohort is not a cohort. ice's independently reported 0.536 is a third variant: its 125,128
       pulses **include rescue pulses**, which the scorer excludes (118,761); with rescues in, the figure is 0.558.
       Three numbers, one statistic, all arithmetically right — state the sample AND the filter beside any of them.
     - **The corrected picture is coherent and it is NOT about timing**: the twins' pulses start rising on time and
       reach their peak on time, then spread the same carbohydrate over a longer window at a lower peak. Duration and
       peak height are one defect with one sign, which is exactly what too LOW an Erlang transit order looks like.
     - **It supports `ge_order` 3 for a better reason than L 625 gave.** Order 3 moves both real rows toward the
       corrected targets (dur_h 1.876 → 1.853 / 1.803 against 1.577; peak_per_g 1.043 → 1.072 / 1.090 against 1.190)
       and leaves the matched row untouched at 0.622. It does not overshoot anything. The TIR cost (L 622, 623) is
       unchanged and still the reason it is Pete's call, but the appearance case for it is now measured against
       correct targets rather than stale ones.
     - **Even at order 3 the duration gap is only a sixth closed** (1.876 → 1.803 against a target of 1.577), so
       order alone is not the whole mechanism.
     - **Instrument check, with the ground truth only this role has** (`resid_tools/label_vs_truth.py`): on
       **isolated** pulses the labeller reads peak 58.1 min against the twins' TRUE `ra` peak of 69.2 — about 16%
       early. (The duration half of this check, "184 against 204", is **WITHDRAWN** — see L 628: it is a window
       statistic, not a pulse duration.) So the labelled peak is not the body's, on either side; the rows are fair
       labelled-to-labelled, and **a labelled target must never be used to calibrate the body's appearance
       directly.**
     - **That check itself nearly produced a phantom**: measured over ALL pulses the apparent instrument bias was
       37.3 against 66.8 min (−44%), because a second pulse inside the 4-hour window owns the true-`ra` argmax. The
       isolation filter cut it to −16%. Any statistic that integrates forward over hours needs an overlap filter
       before it means anything. Note also that the scored median (0.622 = 37.3 min) is dominated by clustered
       pulses — isolated ones label at 58 min.

627. **`kabs` at the literature value is a NULL on the duration row it was aimed at — the appearance TAIL is not
     what the labelled `dur_h` measures — and my single-parcel sizing over-predicted it by ~20x. An unrelated,
     consistent TDD improvement came out of it, which needs the level refit before it means anything.** The arm:
     `kabs_m` 1.14 (0.05 -> Dalla Man's identified 0.057; UVA/Padova 0.21 +/- 0.21) alone (`ka1`) and with
     `ge_order` 3 (`ka2`), two draws, against the CORRECTED donor labels of L 626.

     | arm | dur_h (donors 1.577) | peak_per_g (1.190) | peak_h (0.622) | score d1 / d2 | paired SUM\|dev\| d1 / d2 |
     |---|---|---|---|---|---|
     | rf2 | 1.876 | 1.043 | 0.622 ✓ | 0.332 / 0.371 | 3.040 / 2.568 |
     | ka1 | **1.874** | 1.057 | 0.622 ✓ | **0.329 / 0.355** | 3.656 / **1.754** |
     | go3 | 1.853 | 1.072 | 0.622 ✓ | 0.336 / 0.385 | 5.137 / — |
     | ka2 | 1.814 / 1.775 | 1.076 / 1.099 | 0.622 ✓ | 0.350 / 0.427 | 4.462 / 8.500 |

     - **The stated hypothesis is refuted.** `kabs` 0.057 moved the labelled duration by **x0.999** (1.876 ->
       1.874). The single-parcel integration in the run script predicted x0.96, and correcting it twice did not
       rescue it: using the actual per-person `kempt` (0.037, not the 0.05 class default) still predicts x0.97, and
       adding the energy ceiling (`ge_kcal_max` 3) still predicts x0.98. `ge_order` 3 under-delivered the same way
       (predicted x0.92, observed x0.988), so the attenuation is shared and is not about which first-order rate binds.
     - **No appearance arm closes the duration gap.** The best is `ka2` at 1.775 against a target of 1.577, a third
       of the way, and it is the WORST-scoring arm of the four on both draws (0.350 / 0.427) and on the paired
       instrument (4.462 / 8.500). Treat `pulse_dur_h` as not addressable by the appearance path.
     - **`ka1` scores better than the reference on both draws** (0.329 / 0.355 against 0.332 / 0.371) **for a reason
       other than its rationale** — t70 (1.666 / 1.754 against 1.764 / 2.119) and t180 improve, TIR holds. The
       paired instrument SPLITS, though (3.656 against 3.040 on draw 1, 1.754 against 2.568 on draw 2), so it is not
       established; draw 3 and a refit are needed before any adoption.
     - **The one consistent effect is paired TDD**: 1.404 -> 0.824 and 1.399 -> 0.982, ~0.4-0.6 U/day on both draws,
       on the only row documented as a genuine outcome bias (L 602, 607). That is in apparent tension with L 605
       ("TDD is unreachable by a body parameter while `resid_m` is fitted to the level") — **but `bg_mean`'s paired
       deviation moves too** (1.378 -> 2.252 on draw 1, 0.210 -> 0.021 on draw 2), so on draw 1 the TDD gain may
       simply be the level drifting down. Per L 597 this cannot be judged until `lvl_resid.py` is re-run. Queued.
     - **A parameter at its literature value, replacing one fitted to a target since corrected, is worth keeping on
       the table even when its mechanism story fails** — but on the measures, not on the story.

628. **My own `label_vs_truth.py` duration column is INVALID and L 626's "~10% short" instrument claim with it: a
     twin's true `ra` is never zero between meals, so "minutes until 90% of cumulative appearance in a window" is a
     statistic about the WINDOW, not about a pulse.** Widening the window from 240 to 480 min moves the "true
     duration" from ~204 to ~410 min — it simply tracks the window — and the isolation filter then leaves 16-24
     pulses across 4-7 people, so the wide setting cannot adjudicate either. The PEAK column survives (an argmax
     inside the window, on isolated pulses: labelled 58.1 min against a true 69.2), but read it as window-sensitive
     too. **Withdraw the duration half of L 626's instrument finding**; the labeller may or may not read durations
     short, and this script cannot say. A pulse-duration measure needs a defined end (a return to a local
     appearance floor), not a share of a window's integral.

629. **The `kabs` TDD gain was the level, exactly as predicted: the `resid_m` refit hands it straight back. Fifth
     sighting of L 605, and `kabs` 0.057 is NOT adopted.** The prediction was recorded in `run_kr.sh` before the
     run — "if the TDD gain is level-mediated it returns to ~1.4 after the refit" — and it did, on both draws:

     | arm | paired TDD dev | paired bg_mean dev | SUM\|dev\| | score |
     |---|---|---|---|---|
     | rf2 / rf2_5k / rf2_9k | 1.404 / 1.399 / 1.670 | 1.378 / 0.210 / 1.769 | 3.040 / 2.568 / 4.128 | 0.332 / 0.371 / 0.406 |
     | ka1 (no refit) | **0.824 / 0.982 / 1.445** | 2.252 / 0.021 / 0.530 | 3.656 / 1.754 / 3.647 | 0.329 / 0.355 / 0.413 |
     | ka1 REFITTED (3 rounds) | **1.330 / 1.381** | 1.767 / 0.341 | 3.227 / 2.488 | — |

     - **Unrefitted, `kabs` 0.057 improved paired TDD on all three draws** (0.4–0.6 U/day) — the most consistent
       signal any single parameter has produced on that row. **Refitted, it is back at 1.330 / 1.381 against the
       reference's 1.404 / 1.399.** The refit raises `resid_m` to hold each donor's level and Loop re-commands the
       insulin. So the gain was never a lower insulin NEED at the donor's level; it was a lower level.
     - **L 605 now has five independent sightings** (sensitivity, dynamics, the pair, load, and gut absorption).
       Treat it as settled: **no single body parameter can move TDD while `resid_m` is fitted to the level alone.**
       (**Correction to this lesson as first written**: I called the two-parameter fit "the only route left". It is
       not a route at all — it was already run in L 605 (`resid_m` <- level, `twin_isf_mult` <- TDD, `tdd_isf.py`)
       and rejected in L 606, because TDD is unreachable by a body parameter, so the fit drove `twin_isf_mult` to its
       clip bounds and cost `acf_zero_min`, `circadian_amp` and `night_cv` consistently on all three draws. The real
       open question is L 606's: a second fitted parameter needs a target that is both REACHABLE and signal-bearing,
       and neither TDD (signal-bearing, unreachable) nor t70 (reachable, noise-dominated) is.)
     - **`kabs` 0.057 is not adopted.** It is a null on the duration row it was aimed at (L 627), its one consistent
       gain is the level, and everything else is inside the draw scatter (score mean 0.366 against 0.370, paired mean
       3.019 against 3.245 — better on two draws of three, which L 444 rejects as noise). The literature argument for
       0.057 over 0.05 stands on its own, but it buys nothing measurable, so the reference keeps 0.05 and `kabs_m`
       stays available as a documented null.
     - **Method, and it nearly cost a false finding: always run the SAME-DRAW control before reading a rho.**
       `ka1_9k`'s per-person TIR rho is 0.467 against 0.815 / 0.850 on draws 1 and 2, which looks like the candidate
       destroying the ranking. It is not — `rf2_9k` on the same draw reads **0.450**. Draw 3 is simply a bad draw for
       per-person ranking across every row (bg_mean 0.556, t70 0.406). A rho compared across draws is meaningless.
     - Housekeeping: a frozen tree archived before a new script exists cannot run it — `paired_dev.py` failed inside
       the job and had to be re-run from the live tree. Freeze AFTER adding the tooling the job calls, or call such
       tools from the live tree deliberately.

630. **L 606's open question has a negative answer on the obvious candidates: none of the five outcome rows is both
     reachable-independently-of-the-level and signal-bearing, so a second fitted parameter has no good target and
     `twin_isf_mult` should stay on t70.** L 606 asked for a target that is both REACHABLE (body parameters move it,
     or the fit runs to its clips) and SIGNAL-BEARING (not dominated by the draw), and named per-person t54 and TIR
     as candidates. Both are now measured from arms already on disk — 39 draw-3 arms for leverage, the reference's
     three draws for noise, all on `twin.csv`'s paired deviation (`resid_tools/target_screen.py`):

     | row | leverage (IQR across 39 arms) | noise (ref sd across draws) | ratio | r with `bg_mean` | verdict |
     |---|---|---|---|---|---|
     | `tir` | 1.557 | 0.402 | **3.88** | **−0.768** | highest leverage, but **59% of it is the level** |
     | `bg_mean` | 2.662 | 1.573 | 1.69 | — | `resid_m` already owns this |
     | `tdd` | 0.320 | 0.156 | 2.05 | +0.491 | known false positive — see below |
     | `t70` | 0.126 | 0.115 | 1.10 | −0.053 | reachable, noise-dominated (confirms L 602) |
     | `t54` | 0.033 | 0.037 | **0.89** | +0.175 | **RULED OUT: the draw moves it as much as any body parameter** |

     - **t54 is eliminated as a fitting target** — leverage BELOW the draw noise. That half of L 606's question is
       settled: a fit against it would chase the draw.
     - **TIR, the other candidate, fails for the opposite reason.** Its raw leverage-to-noise is the best of the five
       (3.88), but it correlates at −0.768 with the level, so 59% of that leverage is `bg_mean`'s, which `resid_m`
       already fits. Its level-independent leverage is 0.654 against a noise of 0.402 — ratio ~1.6, no better than
       t70's position.
     - **The screen's own limitation, stated because it produces one known false positive**: leverage across arms
       cannot tell genuine from level-mediated reach. `tdd` reads 2.05 "usable" here, yet L 629 showed by refit that
       the one parameter that moved it did so entirely through the level. So read this screen WITH the `bg_mean`
       column, and treat a high ratio with a high |r| as unproven. (`tdd`'s r of +0.491 is the screen's weakest
       point: the refit test is decisive where this projection is not.)
     - **Leverage here is an UPPER BOUND for any single parameter**, since the 39 arms carry different mechanisms.
       A row no heterogeneous set of 39 arms can move beyond the draw noise certainly cannot be moved by one
       parameter; the converse does not follow.
     - **Consequence: do not add a second fitted parameter.** The status quo (`resid_m` <- level, `twin_isf_mult`
       <- t70) is not obviously improvable on these five rows, and L 606 already measured what happens when a fit is
       pointed at an unreachable target. If this is revisited, the target should come from OUTSIDE the outcome rows —
       something with mechanism-specific leverage and low draw noise — not from this list.

631. **The exercise limit's "missing measurement" exists but covers 13% of donors, so it cannot close a cohort band —
     and the mechanism I was going to add instead is refuted by the literature. Both routes to the 6-8 MET band are
     now shut.** L 551, 556, 564 record the 6-8 MET activity band at −13 against the donors' −21.5, blamed on
     per-person aerobic capacity being a prior (`metmax` lnN(9, 0.25) with an age decline, uncorrelated with the
     person). Two things were checked.

     - **The form change I proposed is counter-evidenced.** L 565 says the band trade needs a form change, and the
       obvious one was to let plasma-glucose uptake fall off as the anaerobic share rises (a substrate crossover), so
       that raising C1 could deepen 6-8 without fighting the surge at >= 8. **Romijn 1993 says the opposite**: at 25 /
       65 / 85% VO2max, plasma glucose tissue uptake INCREASES with intensity, as does muscle glycogen oxidation —
       the crossover is fat-versus-carbohydrate, not plasma-glucose-versus-glycogen. So uptake genuinely keeps rising
       and the model's structure (uptake monotone, EGP surge above threshold) is right. Not implemented.
     - **Per-person capacity IS measurable, from `HKAverageMETs` on the donors' own workout bouts** — and which
       statistic matters:

       | statistic | corr with log bout count | split-half (22 donors, >= 20 bouts) | verdict |
       |---|---|---|---|
       | max bout METs | **+0.783** | — | **unusable — it measures how OFTEN they exercise** |
       | p90 bout METs | +0.350 | **+0.790** | usable: a stable person trait, spread 4.6-9.8 METs |
       | median bout METs | +0.114 | — | least confounded, but it is habit not ceiling |

     - **But coverage kills it: only 22 of 168 donors (13%) have >= 5 bouts with METs.** Implemented anyway as
       `templates.add_metmax_own` + `--enable met_own` (off by default), and then measured before spending a run:
       **6 of 112 twins change and the cohort mean metmax moves x1.0047.** A predictable no-op, so no arm was run.
       Do not re-run it expecting an effect; the facility is there for a future cohort with better workout coverage.
     - **The wiring is deliberately one-sided** (`max(draw, anchor)`), because the p90 is the intensity CHOSEN and so
       a lower bound on capacity: a donor whose p90 is 4.6 METs may be unfit or merely unmotivated, and the data
       cannot tell. Setting `metmax = anchor` would use the full per-person signal for those 22 donors but would
       understate capacity for the sedentary — an identifiability problem, not a tuning choice.
     - **Reclassify the limit**: the 6-8 MET band is not "awaiting a measurement" — the measurement exists, is sound
       for the donors who have it, and reaches too few of them to move a cohort statistic. Closing it needs either
       workout records for most of the cohort or an intensity prior conditioned on something every donor has.

632. **The change harness silently ignored every `--set` knob added after 2026-10-28, so an e-pool arm could be a
     perfect no-op that the scorer still printed a plausible ratio for. L 613's `sg_h_lo` half is RETRACTED.**
     `arm2.py` did `sys.path.insert(0, HERE.parent / "frozen2/analysis")` — a hard-coded frozen tree that takes
     precedence over `PYTHONPATH`, so the tree a change run actually executed was fixed at Oct 28 whatever the
     launcher set. A newer knob rides along in `enable`, the old `cohort.py` never reads it, and **both arms of the
     comparison run identically**.

     | arm | knob | in `frozen2`? | variant tir / t70 | real? |
     |---|---|---|---|---|
     | `rf2e_s` | (reference) | — | +7.53 / +1.80 | — |
     | `sn_e` | `si_norm` 1.0 | yes (world.py) | +6.32 / +1.54 | **real** |
     | `hl_e` | `sg_h_lo` 0.0019 | **no** | +7.53 / +1.80 | **NO-OP** |
     | `sw5_e` / `sw0_e` | `csf_sd_w` | **no** | identical | **NO-OP** (60/60 events byte-identical on `truth.bg`) |

     - **What is retracted**: L 613 resolved two pending decisions on 580 events. The `si_norm` half stands —
       `frozen2` has `si_norm`, `sn_e`'s numbers genuinely differ, and the conclusion (NO) is unaffected. The
       `sg_h_lo` half — "neutral on change prediction" — is an **artifact of the arm not running**, and sg_h_lo's
       change response is now simply **unmeasured**. Its cohort result (closes t70 on draw 2, overshoots on draw 1)
       was run through `cohort.py` on a current tree and is unaffected.
     - **Detection, since the scorer gives no warning**: the printed `variant` values are identical between a no-op
       arm and the reference (and `mean BG median` too), while the ratio still differs in the second decimal —
       `score_change.py`'s point ratio is stochastic enough to move without any input change, so **the ratio alone
       cannot reveal a no-op**. Compare `truth.pkl`'s `truth.bg` across the two arms; that is bit-stable (L 586).
     - **Fixed**: `arm2.py` now honours `ARM_TREE` (defaulting to `frozen2`), and the re-run builds `frozen3` from
       HEAD. The re-run script checks for the no-op BEFORE scoring, so a repeat is caught rather than interpreted.
     - **The general shape — a frozen tree is a silent version pin.** It has now bitten three ways in one session: a
       tree frozen before a script existed could not run it (L 629), a tree frozen before a knob existed ignored it
       here, and a stale `.done` sentinel from an earlier job made a watcher fire before its job had started. **Any
       harness that pins its own code must say so where the launcher can see it, and any new knob needs a positive
       control — an arm that MUST differ — before its result is read.**

633. **`git add -A` stages a STALE SUBMODULE POINTER, and that broke clean builds of `main`.** Commit 1d916cfa
     (a C4 threshold change, LESSONS 553) also moved `LoopAlgorithm` from c35b73b back to 9b5f3e5, because this
     worktree's submodule checkout was behind and `git add -A` at the repo root stages that difference as a real
     change. The engine's `generatePrediction` call needs c35b's `iceDoses` parameters, so a clean checkout of `main`
     stopped building; the trio role found it and restored the pointer in 7668fbde.

     - **Nothing in my own workflow would have caught it.** This role's commits are documentation and Python under
       `analysis/`; the submodule is invisible to every check I run, and `git status` reads CLEAN once the stale
       pointer is committed, because the index then agrees with the stale checkout. The regression is only visible
       as `git ls-tree HEAD LoopAlgorithm` against `origin/main`'s.
     - **Practice, from now on:** stage explicit paths — `git add docs analysis` — not `-A`, in any worktree with a
       submodule. Before a commit that used `-A` anyway, check `git ls-tree HEAD LoopAlgorithm` against
       `git ls-tree origin/main LoopAlgorithm` and run `git submodule update` if they differ.
     - **The `--ff-only` publish rule is what limits the damage** (AGENTS.md): my branch recorded 9b5f3e5 while
       `main` had c35b73b, so the next `git -C <main> merge --ff-only` would have REFUSED rather than silently
       regressing the fix. The rule earns its keep here — do not work around a refusal by merging the other way.
     - Recovered by merging `origin/main` (bringing 7668fbde) and then `git submodule update --init`, which checked
       out c35b73b; `git status` clean and `git ls-tree HEAD LoopAlgorithm` now matches `main`.

634. **Both open arms of 2026-11-01 come back negative on the real harness: `sg_h_lo`'s cohort t70 gain does NOT
     transfer to the change response, and the per-person meal-spread fit is NOT what damps it (L 544's trade does not
     exist on `rf2`).** Job 156 re-ran the three e-pool arms that L 632 found to be silent no-ops, with `arm2.py`
     honouring `ARM_TREE` and `frozen3` built from HEAD. The no-op check passed first: all three differ from `rf2e_s`
     on 60 of 60 events, so these are real arms (`runs/.../noop_check_sw2.log`, `score_sw2_epool.log`, 580 scored
     events).

     **`hl2_e` — `sg_h_lo` 0.0019 with its insulin suppression. Field / variant ratios (field = 1.0, higher = more
     damped), against the reference `rf2e_s`:**

     | row | rf2e_s | hl2_e | rho rf2e_s | rho hl2_e |
     |---|---|---|---|---|
     | mean | 1.33 | **1.43** | +0.33 | **+0.26** |
     | TIR | 1.28 | **1.40** | +0.16 | **+0.13** |
     | t70 | 1.15 | **1.15** | +0.17 | **+0.12** |
     | t54 | 0.56 | 0.82 | +0.04 | +0.16 |

     Pre-edit level +3.3 -> **+6.3** mg/dL against the field. So the cohort and the change response **disagree**, which
     `run_sw2.sh` recorded in advance as the interesting outcome: the mechanism closes the t70 LEVEL row on the cohort
     (L 596: draw-2 gap 0.325 -> 0.034) and leaves the t70 RESPONSE ratio bit-flat at 1.15 while costing the mean and
     TIR response, all three correlations, and the starting level. t54's ratio moves toward 1.0, but t54 is a guard,
     not a target. **`sg_h_lo` stays off, now on both halves**, and L 632's "change response UNMEASURED" is closed.
     L 613's retracted claim was right in substance on t70 and too kind elsewhere: the honest statement is *neutral on
     t70, worse on mean, TIR and every correlation*.

     **`sw5b_e` / `sw0b_e` — `csf_sd_w` 0.5 / 0.0, weakening the per-person meal-spread fit.** The prediction was that
     the ratios move toward 1.0 as the fit is weakened. **Refuted — they move AWAY:**

     | row | rf2 (1.0) | sw5b (0.5) | sw0b (0.0) |
     |---|---|---|---|
     | mean ratio | **1.33** | 1.47 | 1.44 |
     | TIR ratio | **1.28** | 1.25 | 1.28 |
     | t70 ratio | **1.15** | 1.55 | 1.28 |
     | pre-edit level | **+3.3** | +9.1 | +9.7 |

     And the cohort cost is the one already measured, confirmed on both draws: paired SUM|dev| 3.040 -> 5.165 ->
     10.168 (d1) and 2.568 -> 7.451 -> 9.648 (d2); twin-donor TIR rho 0.815 -> 0.681 -> 0.425 (d1), 0.830 -> 0.735 ->
     0.456 (d2). **A large per-person cost for no response gain: `csf_sd_w` stays at 1.0.** L 544 measured its trade on
     the sd3 lineage, where the DYNAMIC residual was on; `rf2` dropped that residual and took the damping with it
     (L 592: t70 response 3.51 -> 2.17), so the spread fit is no longer the binding term. **A finding about a damping
     source does not survive the removal of another damping source — re-read it on the current reference, which is why
     this arm was run rather than quoted.**

     **Method note, a third sighting of L 610.** The weighted cohort score barely separates these arms — d1 0.309 /
     0.334 / 0.304 (sw0 nominally the BEST), d2 0.357 / 0.365 / 0.372 — while the paired instrument moves by 3x and
     the twin-donor TIR rho halves. A change that destroys per-person fidelity can read level or better on the
     weighted score. Judge per-person changes on `twin.csv`, never on the score alone.

635. **The glucose-effectiveness draw is out of its own evidence range on the high side: 47% of the cohort is drawn
     above the top of a range the evidence base records as PER PERSON.** Found while setting up the SG arm, and it is
     a soundness defect independent of any target. `person.py` draws `sg` as lnN(0.0045 /min, 0.5) and
     `evidence/17` called that "inside UVA/Padova's 0.0013-0.0047". But `evidence/05` records that range as
     **0.0013-0.0047 per person** (a plant impulse fit) — the spread of individual values, not a bracket on the
     centre. The lognormal puts **47% of people above 0.0047**, with p95 at **0.0102, 2.2x the top of the range**.
     The claim was true of the median alone. Read as a per-person bracket the evidence implies

     | | current draw | implied |
     |---|---|---|
     | median | 0.00450 | **0.00247** = sqrt(0.0013 x 0.0047), i.e. `sg_mult` **0.55** |
     | log-sd | 0.50 | **0.39** = ln(3.615) / (2 x 1.645), the range as 5-95% |

     so the draw is **1.8x too high and 1.3x too wide**. **Corroborated independently and more strongly by ice's
     LEARNED background force at 0.0015/min = 3x too high, which also shows the error is concentrated on the HIGH
     side — see L 636, and read `sg_mult` 0.40 as the central estimate rather than the extreme.**
     `evidence/15` independently carries a standing unactioned
     check pointing the same way — Del Prato 1997 has T1D mass-action self-correction at ~1/3 of healthy, with the
     note "check that the sim's SG / GEZI term is T1D-sized". **Rule: a lognormal whose MEDIAN sits inside a
     per-person range is not inside that range.** Check the coverage, not the centre, whenever a draw is justified by
     a measured spread — and check whether the cited range is a range of per-person values or of reported centres,
     because the two license completely different distributions.

     **Why it matters beyond bookkeeping.** SG is the insulin-INDEPENDENT share of glucose disposal, so it sets how
     much of a settings change glucose can respond to at all: holding appearance, dG/dI = −SI·G / (SG + SI·I·…). The
     twins respond at 0.75 of the field on the e pool (L 634 left mean 1.33, TIR 1.28, t70 1.15 with every named
     candidate eliminated), i.e. an effective denominator ~1.33x too large, and SI is fitted per donor from their own
     glucose response. **SG is the one structural term with slack, and the algebra fixes its sign in advance** — the
     first candidate on this gap for which that is true. Queued as a two-value screen, `sg_mult` 0.67 (0.0030,
     mid-range) and 0.40 (0.0018, near the floor), bracketing the evidenced 0.55, with the e-pool arms deliberately
     run on UNREFIT templates so the level drift works AGAINST a positive result (`run_sg.sh` records the asymmetric
     reading rule: better-despite-drift is real, flat-or-worse is ambiguous and needs the refit).

     **Both prior SG rejections were on the LEVEL, and both predate `resid_m`.** L 208 raised the centre off 0.003
     because it "left the level +6 and its excursions too persistent"; L 349 / 356 rejected `sg_mult` 0.7 / 0.5 at
     c349 for mean 160.9 / 163.9 and TIR 69.2 / 67.0 — while t54 went to **0.190% against the donors' 0.190%,
     exactly**. A level objection is exactly what the residual-level refit now absorbs (L 597), so neither rejection
     transfers to the current reference. Neither was ever run on the change response.

636. **SG cannot be measured from this donor pool — three routes are closed, one of them already by ice — but ice's
     LEARNED background force corroborates L 635 independently, at 3x rather than 1.8x, and says the defect is a
     SHAPE error concentrated on the high side.** Two routes tried here before finding ice lesson 140 had done the
     third:

     - **ICE against glucose in quiet closed-loop windows** (clean, undisrupted, no carb entry or manual bolus in the
       prior 4 h, outside labelled pulses + 120 min, G in [100, 180]). The slope comes out **positive** — the wrong
       sign for self-correction — because `ice` carries the insulin model's residual and Loop's dosing makes glucose
       and insulin activity collinear at **r +0.5 to +0.7**. At high glucose Loop has dosed hard, so the modelled
       insulin effect is strongly negative and ICE must be positive to reconcile.
     - **The same regression controlling for insulin activity and IOB** is WORSE, not better (slope +0.56 -> +2.07
       mg/dL/h per mg/dL, implied SG −0.02 to −0.07 /min, physiologically impossible). With that collinearity the
       controls absorb the signal. **A control cannot rescue a regressor the controller determines.**
     - **Insulin-free windows.** `no_insulin` is a LOCAL-DAY, RECORD-based flag (`ice_gen/extract.py`: a day with CGM
       and zero recorded insulin), not a physiological one. Over 21,098 h on 32 donors the mean glucose inside those
       windows is only **+3.3 mg/dL** above each donor's own rest, and NEGATIVE for 11 of 32 — i130 averages 111
       mg/dL over 575 h of "no insulin". A genuinely insulin-deprived T1D rises to 300-400 within hours, so these are
       overwhelmingly delivery off the record (pumpless Loop). Only i056 (+151, mean 379) and i068 (+80, mean 247)
       look real, and selecting windows BY glucose level biases the very regression they would feed.

     **ice got there first and cleaner** (ice LESSONS 140b, `sg_free.py`): 2,503 stretches, 19,013 h on 33 pilot
     donors, **median velocity 0.0 mg/dL/h at median glucose 156** — the decisive diagnostic, better than the
     level-delta above — concluding "no SG reading is possible from these data, so SG's prior rests on the
     literature". Check the other roles' lessons for a measurement before building the instrument.

     **The corroboration (ice LESSONS 140a) is the valuable half.** The generator's learned glucose-dependent
     background force, probed by raising the glucose input 40 mg/dL and reading the slope of the predicted mean
     background, has a sustained slope b/(1−a) of **−0.09/h = 0.0015/min**, against additive's prior of 0.0045/min =
     **−0.27/h**. Two independent lines now say the same thing, and they bracket it:

     | line | implied SG median | vs the 0.0045 draw |
     |---|---|---|
     | L 635, the per-person range read as a bracket | 0.00247 (`sg_mult` 0.55) | 1.8x too high |
     | ice 140a, learned background force | 0.0015 (`sg_mult` 0.33) | 3.0x too high |

     The queued screen's bracket (`sg_mult` 0.67 and 0.40) spans both, so **0.40 is the central estimate, not the
     extreme** — read it that way. Both are plausibly bounds rather than points: ice flags the same confound that
     closed the routes above ("where Loop doses to glucose, the TDD ISF rule likely absorbed any high-side uptake"),
     which biases a LEARNED slope LOW, while the literature centre is biased high; the truth sits between, which is
     where L 635's 0.00247 falls.

     **The shape finding, which reframes the mechanism.** The learned force is not a smaller version of ours, it is a
     differently shaped one — by glucose band: below 90 **−0.17/h**, 90-130 −0.07, 130-180 −0.04, 180-250 −0.02,
     above 250 ~0. "Defense-shaped: large near lows, about **10x below the prior above 180**." A linear −SG·(G − Gb)
     gives one slope everywhere, so **a uniform `sg_mult` cut is the wrong correction**: it would thin the low-side
     force, which is already the weakest part of the model (L 563/589 want MORE sub-basal response, sized ~3x either
     existing mechanism). What the shape asks for is a weaker HIGH side and an intact-or-stronger low side — and the
     model already has those as separate named components: `ge_split`'s A1b hepatic autoregulation (`sg_h`, above Gb
     only) against A1a peripheral mass action (`sg_p`), with `sg_h_lo` extending below. **That is the adoption arm:
     cut the high-side term, not the scalar.** It also predicts the change-response gain the uniform cut is being
     screened for, and for the right reason — most of a settings edit's glucose response happens in 130-250, exactly
     where the learned force is ~10x below the prior. The uniform screen still answers "does SG magnitude move the
     response at all", which is the question worth one job; the split is the follow-up.

637. **`ge_split` CANNOT make the shape L 636 asked for — its high side is structurally stronger than its low side.
     The measured shape is a SATURATING insulin-independent uptake, which is the same treatment κ already gives the
     insulin-mediated path, and at the evidenced parameters it reproduces all five of ice's learned bands without
     fitting anything to them.** L 636 concluded "cut the high-side term (`sg_h`), not the scalar" and named `ge_split`
     as the adoption arm. Reading the code settles that it is the wrong arm, and the right one is cheaper.

     - **Why `ge_split` cannot do it** (`physiology.py` 431-434): with it on, the insulin-independent slope is `sg_p`
       below Gb and `sg_p + sg_h` above, because A1b is modelled as the liver WITHHOLDING output above basal — an
       ADDITION to disposal. So the high side is ≥ the low side by construction, whatever `sg_h` is set to, while the
       measured profile falls 8x from the low band to 180-250. Cutting `sg_h` to zero does not make the shape; it only
       flattens `ge_split` back to its own `sg_p`, which at 0.0022 / vg = **0.00117 /min (0.070 /h)** is 2.4x WEAKER
       than the measured low band. Tabulated against ice L 140a's learned slopes, `ge_split` is wrong in BOTH
       directions — 2.4x too weak below Gb and 15x too strong above it — which is exactly why L 548 rejected it for
       too many lows. The "now the indicated route again" of L 636 is withdrawn.

     - **What the shape actually is.** A force whose slope FALLS with glucose is a saturating uptake, and the model
       already has that form — for the other path. `kappa` 0.15 makes the glucose that insulin-mediated uptake acts
       on rise at only 15% of the excursion above Gb, with `low_prop` keeping it proportional below (LESSONS 7,
       Bergman / UVA Michaelis-Menten). The insulin-INDEPENDENT term next to it is `sg * (g - gb)`, perfectly linear
       in both directions. That asymmetry is unmotivated: both are glucose-driven uptake into the same tissues.

     - **At the evidenced parameters it fits, with nothing fitted to the target.** `sg_kappa` (new, default 0 =
       unchanged) applies κ's treatment to the insulin-independent term. Slope per hour, by ice's own bands:

       | band | ice learned (of0) | current (`sg` 0.0045, linear) | `sg` 0.00247 + `sg_kappa` 0.15 |
       |---|---|---|---|
       | below 90 | 0.170 | 0.270 | 0.148 |
       | 90-130 | 0.070 | 0.270 | 0.114 |
       | 130-180 | 0.040 | 0.270 | 0.022 |
       | 180-250 | 0.020 | 0.270 | 0.022 |
       | above 250 | 0.000 | 0.270 | 0.022 |

       Neither parameter was chosen against this table: `sg` 0.00247 is L 635's bracket median from the per-person
       literature range, and 0.15 is the κ the insulin path already carries. The current linear term is wrong by
       0.10-0.27 /h in every band and has no gradient at all; the shaped form tracks the profile within 0.044 /h at
       its worst band. Two parameters from elsewhere landing on a five-band profile is the strongest evidence in this
       thread so far.

     - **Third independent line, and it is a DIRECT test: ice lesson 146.** A literature-strength SG (0.0045, our
       prior median) was added to the generator's plant and the network retrained on both seeds: held-out TIR bias
       -5.3 / -6.5 against -0.7 / -3.0, t70 +1.24 / +1.73 against +0.45 / +0.36, own-settings level -4.9 / -6.2
       against +1.6 / -2.7, and no change-prediction gain on 62 edits or 52 switches. ice's reading: "a
       literature-strength SG adds a restoring force the TDD-ISF ICE already holds." **That transfers to additive,
       because additive's ISF comes from the same ICE yardstick on the same closed-loop pool** — and L 636 measured
       the mechanism in our own data: corr(G, insulin activity) is +0.53 to +0.71 across donors, which is exactly how
       glucose-dependent disposal loads onto a fitted insulin effect. So the high-side term is plausibly
       DOUBLE-COUNTED with our own fitted ISF, and a weak insulin-independent high side is what a model with a
       data-fitted ISF should have. The double-count argument and the shape argument point the same way.

     - **The honest caveat, stated before the run.** ice flags that the TDD-ISF rule may have absorbed high-side
       uptake, which biases their LEARNED high-side slope low — and the high bands are where `sg_kappa` mostly acts,
       so the shape claim rests partly on a lower bound. It is also a KINK at Gb, not a smooth saturation, and it
       over-predicts the 90-130 band (0.114 against 0.070) for that reason; a Michaelis-Menten form would fit better
       and needs its own evidence, so it is not built. If the cohort prefers a bigger high side, `sg_kappa` should be
       larger, not the form abandoned.

     - **The arms, nested with the queued uniform screen.** Job 160 runs `sg_mult` 0.67 / 0.40 at `sg_kappa` 0, so
       with `sk1` = `sg_kappa` 0.15 alone (shape only, magnitude untouched) and `sk2` = `sg_kappa` 0.15 + `sg_mult`
       0.55 (both, the table's column), the four arms SEPARATE magnitude from shape, which neither alone can do.
       Prediction recorded now: the uniform cut buys change response and spends the low side (its cancellation guard
       covers that); `sk1` buys the same response with LESS low-side cost, because it cuts only where a settings
       edit's glucose response lives (130-250) and leaves the sub-basal force L 563/589 want strengthened. If `sk1`
       beats both uniform arms on the e pool AT a smaller low-side cost, the shape reading is right and the scalar
       reading is wrong.
     - **Verified to bite in the full step path, not just the CSV** (the L 554 / 633 trap): a body held open-loop from
       G 200 for 6 h reaches 329 at `sg_kappa` 0 and 431 at 0.15, so the weaker high side is doing what it says. That
       also previews the cohort cost — highs become less self-correcting, so expect t180 to rise and Loop to spend
       more, and expect the `resid_m` refit to reabsorb the LEVEL part of it (L 597). The change response is a dG/dI
       effect, not a level one, so that is the part which should survive the refit.
     - **The obvious physiological account of the saturation is RULED OUT by arithmetic, so `sg_kappa` has no
       mechanistic derivation and must not be presented as having one.** The tempting story is that part of SG is
       glucose-induced suppression of hepatic output, which is bounded because EGP cannot fall below zero, so its
       contribution to the slope must die out at high glucose. It does not die out anywhere near the right place: at
       `egp_b` 2.5 mg/kg/min and VG 1.88, exhausting EGP at ice's own low-band strength needs (G − Gb) = **469
       mg/dL**. The same number is why `ge_split`'s one saturating element is inert — its EGP floor
       `min(sg_h·VG·(G−Gb), max(EGP, 0))` binds only at **G 469**, i.e. never in the physiological range, which is a
       second and independent reason cutting `sg_h` cannot make the shape. So the physiological content of the
       measured saturation is non-linear hepatic autoregulation and/or saturating uptake, which this model does not
       express and the literature in hand does not size. `sg_kappa` rests on the structural symmetry with κ and on
       ice's measured profile, and on nothing else.
     Code: `sg_kappa` in `physiology.py` (`_sg_excess`), plumbed in `world.py` from `--set`; default 0, so every
     existing run is bit-unchanged. Registry: A1d in COMPONENTS.md; evidence in `evidence/17-measured.md` § A1.

**638. The damped change response is a SHAPE error in glucose effectiveness, not a magnitude error — and the
magnitude arm's apparent gain was entirely its own level drift.** Jobs 160 and 161 ran the 2x2 L 637 designed:
`sg_mult` 0.67 / 0.40 at `sg_kappa` 0 (magnitude), and `sg_kappa` 0.15 with and without `sg_mult` 0.55 (shape).
All six arms verified real (no-op and knob checks). On the e pool's 580 edit events, field / variant, field = 1.0,
higher = more damped:

| arm | what it changes | mean | tir | t70 | t54 | pre-edit level |
|---|---|---|---|---|---|---|
| rf2e_s | — | 1.33 | 1.28 | 1.15 | 0.56 | +3.3 |
| sg7_e | sg x0.67, both sides | 1.29 | 1.18 | 1.27 | 0.80 | +10.1 |
| sg4_e | sg x0.40, both sides | 1.28 | 1.18 | 1.26 | 0.57 | +15.5 |
| **sk1_e** | **`sg_kappa` 0.15, high side only** | **1.06** | **1.06** | **1.08** | 0.76 | +19.1 |
| sk2_e | `sg_kappa` 0.15 + sg x0.55 | 0.98 | 0.95 | 1.19 | 0.82 | +20.5 |

- **The magnitude route is dead, and it is dead for a reason worth keeping: its gain was its own level drift.**
  `dG/dI = -SI·G / (SG + SI·I·…)` is PROPORTIONAL TO G, so an arm whose pre-edit level sits higher must respond
  more to the same proportional edit with no mechanism at all. `score_change_lvl.py` (in `change_e/`) decomposes
  it — the level-only expectation is `ratio_ref x (level_ref / level_arm)` on the arms' own median pre-edit mean
  glucose (rf2e_s 143.5, sg4_e 153.5, sk1_e 157.0). **sg4's observed mean ratio is 1.25 and its level-only
  expectation is 1.25**: the whole apparent gain is the drift, to two decimals. On TIR, 1.16 observed against
  1.20 expected — the same. And on t70 it is WORSE than level predicts (1.27 against 1.04), which is the uniform
  cut thinning the sub-basal force L 563/589 want strengthened, exactly as job 160's cancellation guard said it
  would. A magnitude cut has no structural effect on the response.
- **The shape route is real at a FIXED level.** sk1's observed mean ratio is 1.05 against a level-only expectation
  of 1.22, TIR 1.07 against 1.17, so the form carries 1.22 -> 1.05 and 1.17 -> 1.07 after the drift is taken out.
  Per unit of glucose the response rises 1.16x (slope / level 0.1425 against rf2's 0.1226). Re-fitting each arm's
  slope with its OWN pre-edit mean as a covariate gives the same answer (sk1 1.06, sg4 1.27), so the conclusion
  does not depend on which correction is used. **The magnitude arm reproducing its own confound to two decimals
  is what validates the correction** — it is an internal control, not an assumption.
- **And the form alone is right: `sk2` OVERSHOOTS.** Adding the uniform cut on top takes mean to 0.98 and TIR to
  0.95 — past the field — and puts the low-side damage back (t70 1.19 against a 1.00 level expectation). So the
  pair BRACKETS the field, `sg_kappa` 0.15 alone is the configuration, and the extra magnitude cut is not wanted.
  Two independent reasons now say the same thing: the e pool brackets it, and ice L 140a's bands are matched at
  `sg_kappa` 0.15 with `sg` left where it is.
- **160's own saturation was the first sign, misread at first.** `sg_mult` 0.67 and 0.40 are indistinguishable on
  every ratio despite one cut being 1.5x and the other 2.5x. That looked like "the high side is exhausted"; it was
  "there is no mechanism here at all, only level", and the two readings were separated by the decomposition above
  rather than by more compute. The discriminator had been recorded before 161 ran (sk1's mean ratio below ~1.22 =
  shape is a real further lever) and 1.05 settles it.
- **Still unmeasured: the cohort cost.** 161's cohort arms ran on the UNREFIT templates, so sk1 carried a +13
  mg/dL level error and every level-fed row collapsed (score 0.309 -> 0.440 / 0.357 -> 0.434, bg_mean 151 -> 164,
  t180 25.8 -> 36.9, TIR 72.2 -> 61.6, TDD 41.9 -> 45.8). None of that is interpretable before the `resid_m` refit
  (L 597). Refit round 1 ran inside 161; job 162 runs rounds 2-3 and scores the converged arm on three draws.
  Two rows are NOT level-fed and are the real cost to watch: **bg_cv** 34.2 -> 38.8 (donors 34.6) and
  **`acf_zero_min`** 60 -> 70 (donors 40). The low side is already fine unrefit — t70 1.973 / 1.920 against sg4's
  2.362 / 3.043, `min_below70` exactly the donors' 20.0, lows/day 1.083 against rf2_5k's 1.250 — which is the
  shape's whole point. Paired per-person ranking was better even at the wrong level (rho_tir 0.856 / 0.843 against
  0.815 / 0.830; rho_t70 0.665 against 0.631).
- **`acf_zero_min` moved on an SG arm**, which L 594 / 617 said only gastric-emptying shape does: 60 -> 67.5 /
  70 as the high-side force weakens. Job 160's header had predicted it would be unmoved and that this would void
  L 208's second objection ("excursions too persistent"); it is corroborated instead. Confounded with the level
  until job 162, but the direction is what a weaker restoring force must do.

**Trap this produced: a change-response ratio is meaningless without its arm's own pre-edit level.** Every arm
compared on the e pool before this one drifted +3.3 to +9.7, small enough that the ratios could be read directly;
`sk1` drifts +19.1, and at that size the drift alone moves the mean ratio by 0.11. Read `score_change_lvl.py`'s
level-only expectation beside every ratio from now on, and treat an arm whose observed ratio equals that
expectation as having NO mechanism whatever its raw number looks like.

**639. `sg_kappa` closes the change response and wrecks the distribution, and the cause is the LEVEL FIT, not the
physiology — the two clauses of the goal now disagree on one component.** Job 162 ran refit rounds 2-3 (|gap| p50
12.7 -> 3.9 -> 2.2, twin-donor rho 0.99) and scored the converged arm against rf2 on three draws. All three arms
verified real.

| row | donors | rf2 (1000 / 5000 / 9000) | skf |
|---|---|---|---|
| bg_mean | 151.9 | 151.0 / 148.2 / 152.1 | 151.8 / 150.9 / 157.9 |
| tdd | 38.7 | 41.9 / 42.6 / 42.7 | 41.4 / 43.8 / 43.0 |
| **bg_cv** | 34.6 | 34.2 / 35.4 / 35.1 | **40.6 / 41.5 / 42.0** |
| **t70** | 1.60 | 1.76 / 2.12 / 1.51 | **3.38 / 3.76 / 2.58** |
| **t54** | 0.190 | 0.124 / 0.232 / 0.148 | **0.396 / 0.479 / 0.282** |
| **lows/day** | 1.00 | 1.00 / 1.25 / 0.88 | **1.79 / 2.08 / 1.46** |
| tir | 71.9 | 72.2 / 71.3 / 69.3 | 68.5 / 68.9 / 65.4 |
| acf_zero_min | 40 | 60 / 55 / 60 | 65 / 65 / 70 |
| score | — | 0.309 / 0.357 / 0.397 | 0.427 / 0.477 / 0.510 |

- **The level prediction held exactly, so none of the cost is the level.** bg_mean lands on the donors' on draws
  1-2 (and closer than rf2 on draw 2) and TDD is level or better. What the refit could not hold is DISPERSION:
  CV +6 points, t70 and lows/day roughly DOUBLED, t54 1.5-2.5x, score +0.11 worse, on every draw. `acf_zero_min`
  is worse at a held level too, so L 208's second objection is confirmed as a real effect and not a level artefact.
- **The cause is the instrument.** Two candidates are ruled out by arms in hand. It is NOT the sub-basal force:
  `sk1` leaves `sg` at its default below Gb and cuts only the high side, and its lows still doubled. It is NOT the
  controller over-dosing runaway highs: TDD is flat (41.4 / 43.8 / 43.0 against 41.9 / 42.6 / 42.7). What is left
  is the level fit. Holding the donor's mean after removing 85% of the restoring force above Gb costs `resid_m` a
  mean of **-20.43 mg/dL/h against rf2's -7.69** (median -12.03 against 0.00) — ~12.7 mg/dL/h of extra CONSTANT
  downward drift per person. **A constant drift is not a restoring force**: it holds the mean and widens both
  tails, highs because nothing pulls them back and lows because the drift keeps pulling after the insulin has
  landed. Mean right, CV +6, both tails up is exactly that signature.
- **This is the converse of L 597 and belongs beside it.** L 597: a gain that runs through the mean is handed back
  by the refit. This: a change to the RESTORING FORCE is converted by the refit into a distributional cost,
  because the only instrument the fit has is a constant. `resid_m` can hold a level; it cannot stand in for a
  feedback term. Any future candidate that alters SG, κ, or anything else that acts proportionally to the glucose
  excess must be judged on CV and the tails after refit, never on the mean.
- **The evidenced configuration would cost MORE, not less — and L 638's phrasing needs this correction.** L 637's
  band match is at `sg` 0.00247 WITH `sg_kappa` 0.15, and 0.00247 = 0.0045 x 0.55, so the ice-band-matched arm is
  **`sk2`**, not `sk1`. `sk1` runs the sub-basal force at 0.27 /h against ice's 0.17, 1.6x too strong. So the arm
  that landed on the field's change response is not the one the band evidence picks, and the one it picks weakens
  the sub-basal side as well — `sk2`'s unrefit t70 was already 2.332 / 2.317 against `sk1`'s 1.973 / 1.920. Its
  refit was not run: it starts further from the donors on the row that already fails.
- **Verdict: `sg_kappa` stays off by default, and the choice goes to Pete.** It is the only mechanism ever found
  that closes the damped change response (L 638, mean 1.33 -> 1.06 with the level confound removed), and at a held
  level it doubles the lows. t54 and lows/day are safety axes, where AGENTS.md's rule is that a win on one metric
  costing the other is not a win — so this is not a case the 2026-11-01 "level but better explained" rule covers,
  and it is not mine to decide. Both sides are on record and the arm is one `--set sg_kappa=0.15` away.

**640. Three results that close the form route on SG, correct a parameter I had misread, and turn up the first
sizing of the post-nadir term L 600 asked for.** All from arithmetic and reading, no new cohort arms.

- **A smoother saturation cannot buy back L 639's cost, and that is settled without running it.** L 637 left the
  form open ("a kink at Gb, not a smooth saturation; a Michaelis-Menten form would fit better and needs its own
  evidence"), and ice L 140a's four bands are that evidence. Fitting forms to them (band-averaged over the Gb
  prior, `runs/2026-10-31-additive-gesplit/fit_sgkm*.py`): the kink reaches RMS 0.0251 /h, MM anchored at Gb is WORSE at 0.0319, and
  **MM with a free breakpoint fits essentially exactly, RMS 0.0015** (0.170 / 0.072 / 0.038 / 0.020 against ice's
  0.17 / 0.07 / 0.04 / 0.02) — with the breakpoint running to the bottom of the range, i.e. the saturation is in
  ABSOLUTE glucose with no basal anchor. So a 17x better form exists. **It does not help**, because what sets
  L 639's cost is not the shape but the total force removed, and that is pinned: weighted by the twins' own
  glucose dwell distribution (806,440 min of ground truth, mean 149), the restoring force is x0.25 of the default
  for `sk2`, x0.25 for the best kink, x0.25 for MM-at-Gb and **x0.22 for the near-perfect free-breakpoint fit** —
  every band-faithful configuration lands within x0.22-0.25, and all of them below `sk1`'s x0.46, which already
  cost 12.7 mg/dL/h of constant drift and doubled the lows. **ice's profile pins the dwell-weighted
  insulin-independent force to about a quarter of our prior; the dispersion cost follows from that quantity, so no
  parameterisation of A1d avoids it.** Do not spend another arm on the shape of this term.
- **κ's live median is 1.0, not 0.15 — I misread the dataclass default, and the "both disposal paths saturate"
  idea it suggested is void.** `physiology.py` declares `kappa: float = 0.15`, but `person.py:285` draws
  `kappa = kappa_mult * exp(N(0, 0.4))` with `kappa_mult` 1.0, so every sampled person gets κ median 1.0 — L 303's
  adopted Bergman value, from Best 1981 read in full. The insulin-mediated path therefore ALREADY scales fully
  with glucose, and the tempting story for L 639's runaway highs (that `sg_kappa` leaves nothing removing glucose
  faster as glucose rises) is simply false. **Trap: never read a live parameter from the dataclass default** —
  `person.py` overrides most of them per person, and the two disagree by 6.7x here. Check a built person's value,
  as the `--enable k=v` and `BEHAVIOR_COLS` traps already require for template columns.
- **ice's bands ARE the insulin-independent force, so L 635-639's comparison is sound.** ICE is observed change
  minus the modelled insulin effect, so the force ice fits to it has insulin removed. Their own caveat is the one
  already recorded in L 637: where Loop doses to glucose, a TDD-ISF rule that absorbs high-side uptake biases the
  HIGH bands low. Checked because κ 1.0 means our total restoring force is SG + X·κ, and had their profile been
  the TOTAL, three lessons would have been comparing unlike quantities. It is not.
- **NEW, and on a different limit: the learned force is DIRECTION-dependent, and that sizes the term L 600 said
  was required.** ice L 140a's probe raises glucose by D = +40 to get the band profile above, and records that
  **lowering it (D = −40) gives about TWICE that slope below 130**. So the donors' restoring force is roughly 2x
  stronger when glucose has been pushed DOWN than when it has been pushed up, at the same level. L 600 states the
  open requirement exactly: "the requirement is a term acting AFTER the nadir, during the climb", and every
  `sg_h_lo` variant failed because a (Gb − G)-proportional term "peaks AT the nadir and lifts it". A
  direction-dependent force is not level-proportional, so it is NOT excluded by that rule — it acts on the way
  down and during the climb and not at a level, which is the shape L 575 and L 594 also ask for. This is the first
  quantitative sizing of it (x2 below 130) from a measurement rather than a literature search, and it comes from
  the same probe that produced the SG bands, so it costs nothing to ask for in more detail. Handoff written:
  `docs/handoffs/2026-11-02-additive-ice-direction-asymmetry.md`. It does NOT resolve the standing evidence
  request (a study lowering glucose below basal at basal insulin in T1D), which is about the sub-basal
  MAGNITUDE; this is about its direction dependence.
