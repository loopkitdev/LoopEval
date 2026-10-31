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

68. **Glucose effectiveness (SG) is not a dial for structure statistics.** Within its evidenced range it trades level
    and lows against long-range structure (×0.7: Hurst up, mean and TIR worse; ×1.5–2: shorter excursions, t<54 doubles,
    Hurst falls, L 98). Choosing it by cohort statistics is tuning a free parameter. ReplayBG's identified SG (median
    0.022) is not a population value: closed-loop identification loads unmodelled dynamics into damping (L 3).

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
