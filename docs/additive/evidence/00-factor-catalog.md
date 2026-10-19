# 00 — Factor catalog: what moves blood glucose in T1D

Master list of the factors an additive T1D patient simulator could compose, with the best
quantitative evidence found for each, and a ranking by expected contribution to real-world BG
variability over months.

**Seed list.** diaTribe's *42 Factors That Affect Blood Glucose* (Adam Brown, 2018 poster and
booklet; origin: *Bright Spots & Landmines*) [R1]. The diaTribe page itself returns 403; the list
below was taken from the booklet PDF hosted by LMC [R1]. Brown's arrows and his personal numbers
are **n = 1 anecdote**. They are quoted only where nothing better exists, and labelled as anecdote.
Factors the 42 miss are numbered **X1…**.

**Evidence labels (used on every magnitude).**

- **[P]** published, and I checked the number against the PubMed abstract (retrieved
  2026-10-15 via NCBI E-utilities). Abstract only, not full text.
- **[U]** unverified: taken from a secondary source (news, review snippet, guideline summary) or
  from memory, and not checked against the primary abstract.
- **[I]** my inference. That covers frequency estimates, tiering and the mapping onto simulator
  channels.
- Population tags: **T1D**, **T2D**, **ND** (non-diabetic), **peds** (children/adolescents).

---

## 1. Summary table

Direction: ↑ raises BG, ↓ lowers BG, ↕ either way, ~ adds noise or variance more than bias.
The "Freq." column is my estimate for a typical adult on AID, unless a source is cited in §3.

| # | Factor | Cat. | Dir. | Best magnitude (label) | Time course | Freq. [I] | Tier |
|---|---|---|---|---|---|---|---|
| D1 | Carb quantity + counting error | food | ↑ | mean error 15.4 g = 20.9 %/meal, 63 % underestimated [P, T1D] | 0–4 h | every meal | **1** |
| D2 | Carb type (GI, fibre, liquid vs solid) | food | ↕ | shape of appearance curve; no clean T1D % found [U] | peak 30–90 min | every meal | **1** (as absorption-profile variance) |
| D3 | Fat | food | ↑ (late) | 60 g vs 10 g fat: +40 % insulin (12.6 vs 9.0 U), still more hyper [P, T1D, n=7]; 35 g fat ↑ from 210 min [P, peds] | 3–18 h | several/week | **1** |
| D4 | Protein | food | ↓ early, ↑ late | 40 g protein: +2.4 mmol/L excursion from 180 min [P, peds]; dose-response 12.5–75 g, ↑ at 150–300 min [P] | 2.5–5 h | daily | **2** |
| D5 | Caffeine | food | ↑ | IV caffeine −15 % insulin sensitivity [P, **ND**, n=12] | ~hours | daily | **2** |
| D6 | Alcohol | food | ↓ (delayed), ↑ (mixers) | 0.75 g/kg evening wine → 5/6 next-morning hypos, post-breakfast peak 8.9 vs 15 mmol/L [P, T1D, n=6] | 10–15 h later | weekly (varies) | **2** |
| D7 | Meal timing (late, large dinner) | food | ↑ overnight | anecdote only [Brown n=1]; diurnal SI lower at dinner (ND) [U] | overnight | daily | **3** (captured by D1–D3 + X5) |
| D8 | Dehydration | food | ↑ | 4.1 % body-weight loss ↑ glucose during insulin withdrawal [P, T1D]; no magnitude with insulin present | hours | rare | **3** |
| D9 | Microbiome | food | ~ | large inter-person response spread to identical meals [P, **ND**] | chronic | — | **3** (fold into D2 per-person params) |
| D10 | Insulin dose / settings mismatch | med | ↕ | no single study; set by therapy settings [I] | persistent | continuous | **1** |
| D11 | Bolus timing (pre-bolus) | med | ↕ | 20-min pre-bolus vs at meal: lower 1 h/2 h BG and peak [P, T1D, n=23] | 0–2 h | every meal | **1** |
| D12 | Medication interactions (β-blockers, SGLT2i, GLP-1RA…) | med | ↕ | GLP-1RA in T1D: −9.2 U/day insulin [P, T1D overweight meta-analysis] | days–chronic | minority | **2** (adjuncts) / **3** (others) |
| D13 | Glucocorticoids | med | ↑↑ | recommended ≥30 % insulin increase (inpatients, mixed DM) [P/U]; afternoon–evening peak [U] | 4–12 h per dose; days | rare, episodic | **2** |
| D14 | Niacin | med | ↑ | modest FPG rise [U, T2D meta-analysis] | chronic | rare | **3** |
| D15 | Light exercise / walking | act. | ↓ | Brown: ~1 mg/dL/min walking [anecdote] | during + 1–2 h | daily | **1** (with D16) |
| D16 | Moderate / high-intensity exercise | act. | ↓ (aerobic), ↑ (anaerobic) | T1DEXI mean Δ during session −18 / −14 / −9 mg/dL (aerobic/interval/resistance), SD ≈ 35 [P, T1D, n=497]; 80 % VO2max → +41 mg/dL for 2 h [P, T1D, n=8] | during; ↑SI for up to 24 h; biphasic 7–11 h [P] | 2–5/week | **1** |
| D17 | Fitness / training level | act. | modifies D16 | anecdote only | weeks | chronic | **3** (parameter of D16) |
| D18 | Time of day of exercise | act. | modifies D16 | midday exercise: no biphasic pattern, GIR elevated to 11 h [U]; afternoon: biphasic [P] | — | — | **3** (parameter of D16) |
| D19 | Food/insulin timing around exercise | act./beh. | ↕ | covered by D1/D11/D16 interaction | — | — | (interaction, not a factor) |
| D20 | Insufficient sleep | bio | ↑ | 4 h sleep: −21 % glucose infusion rate (peripheral SI) [P, T1D, n=7] | next day | weekly | **2** |
| D21a | Illness / infection | bio | ↑↑ (↓ if vomiting) | bolus +39–42 % during infection week [U, preprint n=3]; guideline "increase insulin" [U] | days–2 weeks | 2–4 episodes/yr [I] | **1** |
| D21b | Psychological stress | bio | ↑ (small) | fasting: no effect; post-meal: 45-min delay in glucose fall [P, T1D, n=20+20] | hours | frequent | **2** |
| D22 | Recent hypoglycaemia | bio | ↓ (blunted defence) | antecedent hypo lowers glycaemic thresholds and epinephrine response (e.g. 1160 vs 2040 pmol/L) [P, T1D] | ~24 h | weekly–daily | **2** (via counter-regulation and awareness) |
| D23 | During-sleep BG → next day | bio | ↕ | no study found; Brown anecdote | next day | — | **3** (emergent, not a driver) |
| D24 | Dawn phenomenon | bio | ↑ | ~30 % ↑ hepatic glucose production, ~25 % ↓ peripheral uptake at dawn (GH-driven) [P, T1D, n=12]; 15–25 mg/dL rise [U] | 03:00–08:00 | daily, ~½ of people [U] | **1** (part of the circadian SI profile) |
| D25 | Infusion-set wear / failure | device | ↑↑ | day 2 → day 5 mean BG 123 → 164 mg/dL, >180 time 14.5 → 38.3 % despite TDD +14 % [P, T1D, n=20]; extended-wear set: TIR falls after day 3 [P] | days 3–7; failures acute | every set; failures ~monthly [I] | **1** |
| D26 | Lipohypertrophy | bio/device | ↑ + ~ | LHT: insulin AUC −21 %, CV 52 vs 11 %; post-meal BG ≥ 26 % higher [P, T1D, n=13]; prevalence 64 % of injectors [P] | per injection | common in MDI; pump sites [U] | **2** |
| D27 | Intramuscular delivery | device | ↓ | thigh IM absorption ≥ 50 % faster [P]; leg exercise +135 % absorption from a leg site [P] | 0–3 h | occasional | **2** (inside X3 variance) |
| D28 | Allergies | bio | ↑? | no study found (Brown says none) | — | seasonal | **3** |
| D29 | Hyperglycaemia-induced insulin resistance | bio | ↑ | 24 h at 20 mM: whole-body glucose uptake −26 % [P, T1D, n=8] | 24 h+ | after long highs | **2** |
| D30 | Menstrual cycle | bio | ↑ luteal | luteal SI −2.6 % vs early follicular +2.6 % (model-based) [P, T1D AID, n=77, 380 cycles]; teens TDD 1.05 vs 0.95 U/kg (+10.5 %), TIR −6.3 pts, mean +12.5 mg/dL [P, T1D AID peds, n=51] | ~7–10 days/cycle | monthly, ~half of users | **1** (for menstruating users) |
| D31 | Puberty | bio | ↑ | insulin response 25–30 % lower vs prepubertal [P, T1D] | years | peds only | **2** (population-dependent) |
| D32 | Coeliac disease | bio | ↓ (untreated) | prevalence 6.0 % (biopsy-confirmed) [P]; on GFD no difference in HbA1c, hypos or TDD [P, peds review] | chronic | 6 % of population | **3** |
| D33 | Smoking | bio | ↑ | impaired insulin action [P, **ND** smokers, n=7]; no % in abstract | chronic | minority | **3** |
| D34 | Expired / heat-damaged insulin | env | ↑ | 25–37 °C cycling for 4 weeks: <1 % activity loss [U]; 14–18 % potency loss at 32–37 °C for 28 d [U] | days | rare | **3** |
| D35 | Sensor (CGM) error | device | ~ | G7 MARD 8.2 % (arm) / 9.1 % (abdomen) [P]; G6 ≈ 9–10 % [U] | continuous | always | **1** |
| D36 | Ambient heat / sauna / hot bath | env | ↓ | sauna 2×25 min at 85 °C: insulin absorption +110 %, BG 54–60 mg/dL lower [U, abstract via secondary]; seasonal HbA1c higher in autumn/winter [P, peds] | hours; seasonal | seasonal | **2** |
| D37 | Sunburn | env | ↑? | no study found | — | rare | **3** |
| D38 | Altitude | env | ↕ | <5000 m: insulin −14 % (NS); >5000 m: glucose 7.5 → 9.5 mmol/L with AMS [P, T1D, n=8] | days | rare | **3** |
| D39–42 | Glucose-check frequency, defaults, decision biases, family/social pressure | beh. | ↕ | association with HbA1c only; not a physiological channel [I] | — | — | **3** as factors (they act through X1/X2/D1/D11) |
| **X1** | Rescue carbs / hypo over-treatment | beh./food | ↑ | mean 32 ± 24 g per hypo, 73 % over-treat (>20 g) [P, T1D, n=121]; 33 % of hypos followed by >180 mg/dL within 2 h [P, T1D, n=159] | 15–120 min | ~2–5 hypos/week [P/I] | **1** |
| **X2** | Missed / late / unannounced meal boluses | beh. | ↑ | ≥1 missed bolus/week ↔ HbA1c 8.8 vs 8.0 % [P, peds pump]; 780G compensates missed boluses up to ~30 g [P, review] | 0–4 h | weekly–daily | **1** |
| **X3** | Within-person variability of insulin absorption / action | biological/device | ~ | s.c. regular insulin: intra-individual CV 15–25 % of PD measures [P, ND clamp, review]; glargine GIR-AUC CV ≈ 35 % [U] | per dose | every dose | **1** |
| **X4** | Day-to-day variation of insulin need (unexplained residual) | biological | ~ | closed-loop CV of TDD 17 %, daytime 22 %, overnight 31 % [P, T1D, n=32, 12 weeks]; needs vary from ⅓ to 3× day to day [P, review statement] | daily | continuous | **1** |
| **X5** | Circadian insulin sensitivity (beyond dawn) | biological | ↕ | 7 distinct daily SI patterns in 20 T1D; in silico deviations ≤ 40 % [P]; breakfast EGP less suppressed [P] | 24 h cycle | daily | **1** |
| **X6** | Post-exercise late sensitivity / nocturnal hypo | act. | ↓ | overnight mean 131 vs 154 mg/dL; hypo on 48 % of exercise nights vs 28 % on sedentary nights [P, peds, n=50] | 6–24 h | after each session | **1** (part of D16) |
| **X7** | CGM compression artefacts, lag, dropouts | device | ↓ (false lows) | ~3 % of overnight CGM readings marked as pressure attenuations over 1125 nights [P]; physiological lag 5.3–6.2 min [P, ND] | min–hours | nightly risk | **1** (with D35) |
| **X8** | Loop not running / connectivity outage / pump suspend | device | ↑ | no literature found [I]; observed in this project's replays | min–hours | weekly | **1** for AID simulation [I] |
| **X9** | Pregnancy | bio | ↕↕ | peak week 9, nadir week 16, then +4–5 %/week to week 37 [P, T1D, n=65] | months | rare, scenario-specific | **2** (separate scenario) |
| **X10** | Menopause | bio | ↓ need | post- vs pre-menopausal: TDD lower (p<0.0001) [P, T1D registry]; % not in abstract | years | ~half of older women | **3** (settings drift) |
| **X11** | Gastroparesis | bio | ↓ early, ↑ late | 10-year cumulative incidence 5.2 % in T1D [P] | per meal | subgroup | **2** (subgroup) |
| **X12** | Thyroid dysfunction | bio | ↕ | prevalence raised in T1D [P, review]; no T1D magnitude found | chronic | ~15–30 % have autoimmune thyroiditis [U] | **3** (treated → settings) |
| **X13** | Impaired hypo awareness | bio/beh. | ↓ (delayed rescue) | 19.5 % of adults with T1D; 6× severe hypo rate [P] | — | 1 in 5 people | **2** (modifies X1 timing) |
| **X14** | Long-term drift: weight, season, fitness | bio/env | ↕ | seasonal HbA1c variation [P, peds] | weeks–months | continuous | **2** |
| **X15** | Correction-bolus / manual stacking behaviour | beh. | ↓ | rebound hypo (high → hypo within 2 h) = 29 % of hypos; correlated with rebound hyper (ρ 0.84), "behavioural trait" [P, T1D, n=159] | 1–4 h | weekly | **2** |
| **X16** | Cannabis / recreational drugs, fasting (Ramadan), travel and jet lag | beh. | ↕ | not searched in depth; no magnitude [I] | — | rare | **3** |

---

## 1b. Simulator coverage (2026-10-19)

Where each factor lives in the additive simulator. **On** = default; **switch** = built, off by default;
**scenario** = forced by a scenario switch; **implicit** = carried by a donor-measured trait or the TDD budget rather
than a named mechanism; **not built**. Component codes refer to `docs/additive/COMPONENTS.md`.

| # | Factor | Component | Status | Data check |
|---|---|---|---|---|
| D1 | Carb quantity + counting error | behavior entries, count bias (person + meal, Brazeau) | on; `count_brazeau` switch | entry-anchored meals (LESSONS 130, 144) |
| D2 | Carb type | A10 per-meal speed, fast share, slow phase; `ceiling_speed` | on (speed, fast share); switches | first-hour spread open (LESSONS 147–150, 174) |
| D3 | Fat | A12 fat SI dip relative to the usual diet (`fat_rel`), kcal-slowed emptying | on | dinner second rise open (LESSONS 170) |
| D4 | Protein | A12 late glucose parcel | on | — |
| D5 | Caffeine | B-modulator, mean-zero around habit | switch | — |
| D6 | Alcohol | B9 evening SI, morning-after EGP | on | BDDP logs (LESSONS 138) |
| D7 | Meal timing | donor eating clock; `own_clock`, `graze_eve` | on (clock); switches | LESSONS 123, 135, 170 |
| D8 | Dehydration | — | not built (Tier 3) | — |
| D9 | Microbiome | per-person meal response spread | implicit | — |
| D10 | Settings mismatch | settings = donor's (incl. glucose safety limit, `suspend_own`); body halfway to the TDD yardstick (ISF_W); twins bounded to the measured ISF | on | LESSONS 144, 164, 232–233 |
| D11 | Bolus timing | per-person lead from the labeler (`lead_own`) | on | LESSONS 106 |
| D12 | Adjunct medication | B12 GLP-1 RA | switch | ADJUST-T1D split (LESSONS 87) |
| D13 | Glucocorticoids | B14 courses | on (population rate); scenario | Bevier 2008 (LESSONS 140) |
| D14 | Niacin | — | not built (Tier 3) | — |
| D15 | Light activity | C6 episodes + C7 fragmented bouts (`act_frag`) | on | — |
| D16 | Exercise | C1–C5 sessions (intensity from donors' workout METs), uptake, acute and McMahon-sized delayed SI, absorption, C4 surge above 60% effort | on | BDDP HealthKit workouts (LESSONS 243–247); post-moderate-session fall still short of donors' |
| D17–18 | Fitness, exercise timing | per-person gain; session slot | on (as parameters) | — |
| D20 | Insufficient sleep | B7 prior-night sleep loss; `sleep_util` (sleep-lowered glucose use) | on; switch | quiet-night balance (LESSONS 173) |
| D21a | Illness | B6 episodes | on | BDDP logs (LESSONS 136); rate, duration, size re-checked (LESSONS 235) |
| D21b | Stress | B10 reactive third | on | BDDP logs (LESSONS 138) |
| D22 | Recent hypoglycaemia | A9 HAAF | on | — |
| D24 | Dawn phenomenon | B1b basal-need profile (donor schedule), B2 dawn, B8 GH | on | LESSONS 48, 51 |
| D25 | Infusion-set wear / failure | device site age, failures, occlusion | on | — |
| D26 | Lipohypertrophy | device LH sites | on | — |
| D27 | Intramuscular delivery | absorption jitter A4 | implicit | — |
| D29 | Hyperglycaemia resistance | B11 | on | LESSONS 153 |
| D30 | Menstrual cycle | B5 late-luteal shape | on | BDDP cycle logs (LESSONS 136); onset size checked over full cycles, post-onset low earlier than donors' (LESSONS 235) |
| D31 | Puberty | age-banded U/kg | implicit | — |
| D35 | CGM error | sensor families (G6, G7, Libre 3, Medtronic) | on | LESSONS 45, 174 |
| D36 | Heat / sauna | B15 absorption speed above 13 °C (`heat_a`) | built, off: absorption alone lowers lows under Loop (paired OR 0.59–0.75 vs observed 1.26, Diabetes Care 2026) | LESSONS 290 |
| D38 | Altitude | — | not built (Tier 3) | — |
| D33 | Smoking | implicit: chronic smoker resistance is in each donor's data-fitted ISF (body follows data, 2026-10-19) | no acute term: nicotine infusion impaired insulin sensitivity in T2D but not in healthy controls (Axelsson 2001); T1D smokers have lower eGDR (PoProStu 2018, doi:10.5603/DK.2018.0007) — a chronic level, not a within-day driver | — |
| D32, D34, D37, D39–42 | Coeliac, damaged insulin, sunburn, decision biases | — | not built (Tier 3) or implicit in behavior | — |
| X1 | Rescue carbs / over-treatment | defense: per-person threshold and size from donors | on | LESSONS 166 |
| X2 | Missed / unannounced boluses | per-person announcement and bolus rates | on | LESSONS 127, 145 |
| X3 | Insulin absorption variability | A4 jitter, posture A4b | on | LESSONS 163, 169 |
| X4 | Day-to-day need variation | B3 day SI, named nightly factors | on | — |
| X5 | Circadian SI | B1 Visentin classes | on | LESSONS 168 |
| X6 | Post-exercise late sensitivity | C2 delayed state, McMahon-sized (quadratic drive) | on | LESSONS 57, 246 |
| X7 | Compression / dropouts | sensor compression, gaps | on | LESSONS 45, 167 |
| X8 | Loop not running | outages, pump faults | on | — |
| X9 | Pregnancy | X9 need by gestational week | scenario (`preg_week`) | LESSONS 141 |
| X10 | Menopause | — | not built (settings drift) | — |
| X11 | Gastroparesis | between-person emptying, 28% delayed | on | — |
| X12 | Thyroid | — | not built (treated → settings) | — |
| X13 | Impaired hypo awareness | rescue timing per donor | implicit | — |
| X14 | Long-term drift | — | not built (14-day cohorts) | — |
| X15 | Correction stacking | per-person corrections, size, top-ups; hazard by CGM trend (`corr_trend`) | on | LESSONS 164, 224, 237 |
| X16 | Insulin formulation | body and Loop curve per donor, ultra-rapid inferred from Loop's recorded IOB | on | LESSONS 248 |

### Fit against the donors (reference c268, 2026-10-19)

112 simulated people × 14 days against the eda statistics of their own donors (`cmp_full.py`, `review.py`): 29 of 51
statistics matched (KS) at c264, 31 at c266 (body basal need from the donor's delivered shape, LESSONS 250, which adds lows/day and t70 to the matched set) and 29 at c268 (night need level from the donor's steady nights, LESSONS 251: automatic-bolus t70 1.11 vs 1.20, overnight profile on the donors'; day/night insulin now fails). Numbers below are c264's unless noted. Matched: mean, CV, hurst_long, day/night insulin, low depth and duration, meal arrival shape,
quiet-period motion, night-to-night insulin, correction behaviour by trend, exercise response by intensity. Open, in
order of size:
- **Lows:** 0.58/day vs 1.08, time < 70 0.75 vs 1.67%. Temp-basal twins match their donors; the gap is in
  automatic-bolus people (time < 70 0.67 vs 1.20%), after unentered rises: same insulin, same rise, but real glucose
  falls through the start level faster and further (LESSONS 236, 242).
- **Fast falls:** falling readings > 3 mg/dL/min 0.4–0.5 vs 1.26%; not glucose effectiveness, meal speed, early insulin,
  carb sensitivity or formulation (LESSONS 238–239, 248).
- **Per person:** twins do not inherit their donor's mean (Spearman 0.26) or low-proneness (0.12); low-prone donors are
  not measurably more insulin-sensitive than their settings (LESSONS 233).
- **Breakfast intake** ~8 g-eq/day above the donors' (LESSONS 231).

## 2. Ranking and justification

The ranking score is **frequency × typical magnitude × how much of it survives AID feedback**
[I]. AID compensates slow, persistent offsets well, for example a 2.6 % luteal shift in SI or a
slow drift. It compensates poorly for fast, large, unannounced disturbances: a meal without a
bolus, a failed set, exercise with insulin already on board, or rescue carbs. Over months the
variance comes mostly from events that happen often and arrive faster than the controller's
effective time constant.

### Tier 1: must model

Each of these is either daily, or weekly and large, and each one produces t<54 or TIR deltas of a
size that can flip a candidate comparison [I].

1. **Meals: carb quantity and counting error (D1), absorption profile (D2/D3), bolus timing
   (D11), missed/late/unannounced boluses (X2).** These happen at every meal. The counting error
   alone is about 21 % per meal and is biased towards underestimation [P]. Fat at 60 g raises
   insulin need by about 40 % [P]. Pre-bolus timing changes peak BG [P]. Missed boluses are
   associated with +0.8 pp HbA1c [P]. This is the largest source of variance [I].
2. **Rescue carbs (X1).** Hypos happen several times a week, and the mean treatment is 32 g
   against a recommended 15–20 g [P]. A third of hypos rebound above 180 mg/dL [P]. The rescue
   arm also shapes t<54 itself, because it truncates lows. This matches the AGENTS.md
   rescue-carb confound.
3. **Exercise, acute and delayed (D15/D16/X6).** The mean drop per session is −9 to −18 mg/dL
   with SD ≈ 35 [P]. The 6–24 h late effect doubles the rate of nocturnal hypos (48 vs 28 % of
   nights) [P]. Anaerobic bouts *raise* BG [P].
4. **Insulin absorption and action variability (X3), the day-to-day residual in insulin need
   (X4), and circadian SI including dawn (X5/D24).** Per-dose PD CV is 15–25 % [P]. Total daily
   need has a CV of 17 % and overnight need a CV of 31 % even under closed loop [P]. These are
   the "noise floor" processes. Without them a simulator is too predictable, and any controller
   looks better than it is [I].
5. **Infusion-set wear and failure (D25), and loop/pump outages (X8).** Wear affects every set.
   Mean BG rose 41 mg/dL from day 2 to day 5 [P]. Occlusions and kinks give large acute highs
   [U]. Outages are device events specific to AID [I].
6. **Sensor error (D35, X7).** It is always present: MARD 8–9 % [P], pressure artefacts in about
   3 % of overnight readings [P], and a 5–6 min physiological lag [P]. The controller acts on the
   sensor, so sensor error feeds straight into dosing. It also inflates measured t<54. This is
   the compression-low trap in AGENTS.md.
7. **Illness (D21a).** It happens a few times a year [I], but each episode is large: about +40 %
   bolus [U] and multi-day resistance. Severity is high, and ketosis risk comes with it.
8. **Menstrual cycle (D30), for people who menstruate.** It recurs monthly. The adult
   population effect is small (±2.6 % SI) [P], but teens show +10 % TDD and −6 pts TIR in the
   luteal phase [P], with large heterogeneity between people [P].
9. **Settings mismatch (D10).** This is the baseline bias that every other factor sits on. For
   replay-driven work it is a property of the donor, not a stochastic factor [I].

### Tier 2: model when the use case calls for it, or as a per-person trait

These carry a published magnitude, but they are either infrequent, specific to a population, or
small relative to Tier 1.

- Alcohol (D6), sleep loss (D20), psychological stress (D21b), caffeine (D5, ND evidence only),
  late-protein effects (D4), glucotoxic resistance after long highs (D29).
- Recent hypoglycaemia (D22) and impaired awareness (X13): these change the counter-regulation
  and rescue-timing parameters rather than adding glucose directly [I].
- Lipohypertrophy (D26: large for MDI, unclear for pumps), IM delivery and heat-accelerated
  absorption (D27/D36). These are best expressed as widening the X3 absorption distribution [I].
- Glucocorticoids (D13): rare but very large, so treat them as a scenario.
- Pregnancy (X9) and puberty (D31): run them as separate cohorts or scenarios, not as background
  noise.
- Gastroparesis (X11: 5 % of T1D over 10 years), adjunct drugs (D12: GLP-1RA, SGLT2i), slow
  drift (X14), correction-stacking behaviour (X15).

### Tier 3: negligible, or not worth modelling separately

- No usable evidence of an effect: dehydration (D8), microbiome (D9), niacin (D14), allergies
  (D28), sunburn (D37), altitude (D38), smoking (D33, ND evidence only), expired insulin (D34:
  modern data suggest little potency loss).
- Treated coeliac disease (D32), thyroid disease (X12), menopause (X10): once treated, these
  become slow settings drift that AID and settings edits absorb.
- Modifiers of other factors rather than factors: fitness (D17), exercise time of day (D18),
  meal timing (D7).
- Emergent outcomes: overnight BG → next day (D23).
- Behavioural items D39–D42. They matter, but only through the behaviour channels (X1, X2, D1,
  D11), so model them there as per-person behaviour traits.

### How the Tier 1 factors map onto simulator channels [I]

| Channel | Factors |
|---|---|
| Carb appearance: amount, shape, timing, announced vs not | D1, D2, D3, D4, D11, X2, X1, X11 |
| Insulin PK: absorption-rate multiplier and noise | X3, D25, D26, D27, D36 |
| Insulin sensitivity: slow multiplier (days–weeks) | D30, D21a, D31, X9, X14, D29, D20 |
| Insulin sensitivity: fast multiplier (hours) | D16/X6, D5, D21b, D13 |
| Circadian SI/EGP profile | X5, D24 |
| Endogenous glucose production | D6 (suppression), D16 anaerobic (rise), D24 |
| Sensor model | D35, X7 |
| Device and controller availability | X8, D25 (failure) |
| Behaviour traits per person | X1, X2, X13, X15, D39–42 |

---

## 3. Per-factor notes

Each entry gives mechanism, direction, magnitude with its label, time course, frequency, and
reference.

### Food

**D1 Carbohydrate quantity and counting error.** Mechanism: exogenous glucose appearance, dosed
from an estimate. Direction: ↑.

- Real-life error is 15.4 ± 7.8 g per meal, or 20.9 ± 9.7 % of a 72 g meal. 63 % of 448 meals
  were underestimated, and larger errors predicted higher MAGE and SD and lower time at
  4–10 mmol/L (R² ≈ 0.11) [P, T1D adults, n=50] [R2].
- A ±10 g error on a 60 g meal made no difference over 2.5 h. A +10 g under-dosed meal (70 g)
  read +1.9 mmol/L at 3 h [P, peds, n=31] [R3].
- Modelling: per-meal multiplicative error, roughly lognormal and biased low, around 20 % [I].

Frequency: 3–5 eating events per day [I].

**D2 Carbohydrate type: GI, fibre, liquid vs solid.** Mechanism: rate of gastric emptying and
absorption. Direction: ↕ in timing, ↑ in peak.

- No clean T1D magnitude was retrieved. Response to *identical* meals varies widely between
  people (46,898 meals, 800 people) [P, **ND**] [R10].
- Modelling: a per-meal absorption-time distribution, with per-person shape parameters [I].

**D3 Fat.** Mechanism: FFA-induced insulin resistance and delayed gastric emptying. Direction: ↑,
late.

- 60 g vs 10 g fat at identical carbohydrate: 12.6 vs 9.0 U under closed loop, CR 9 vs 13 g/U,
  and AUC>120 doubled despite the extra insulin. The effect varied widely between individuals
  [P, T1D, n=7] [R4].
- 35 g fat raised glucose from 210 min onward. Fat and protein effects were additive [P, peds,
  n=33] [R5].

Time course: 3–18 h. Frequency: high-fat meals several times a week [I].

**D4 Protein.** Mechanism: gluconeogenic substrate and glucagon. Direction: slightly ↓ early, ↑
late.

- 40 g protein: excursion 2.4 vs 0.5 mmol/L from 180 min, and lower hypo risk [P, peds] [R5].
- Whey 12.5–75 g added to 30 g carbohydrate: a negative dose-response at 30–60 min that turned
  positive at 150–300 min [P, T1D 10–40 y, n=27] [R6].

**D5 Caffeine.** Mechanism: adenosine antagonism and epinephrine. Direction: ↑.

- IV caffeine: −15 % insulin sensitivity and a 5× rise in epinephrine [P, **ND**, n=12] [R7].
- No T1D clamp data were retrieved.
- Brown reports +20–30 mg/dL after a large coffee [anecdote].

**D6 Alcohol.** Mechanism: suppresses hepatic gluconeogenesis and nocturnal GH. Direction: ↓,
delayed; ↑ from carbohydrate mixers.

- 0.75 g/kg wine at 21:00 left overnight BG unchanged. Next-morning fasting and post-breakfast BG
  were lower (peak 8.9 vs 15 mmol/L), and 5 of 6 participants needed treatment for hypoglycaemia
  (nadir 1.9–2.9 mmol/L) [P, T1D men, n=6] [R8].

Time course: 10–15 h lag.

**D7 Meal timing.** Only anecdote exists [R1]. A diurnal SI pattern exists (X5). Fold into
D1–D3 + X5 [I].

**D8 Dehydration.** Mechanism: vasopressin and haemoconcentration.

- Dehydration of 4.1 % of body weight raised plasma glucose during 5 h of insulin withdrawal
  relative to control [P, T1D, n=15] [R9].
- There is no evidence for an effect with insulin present.

Tier 3.

**D9 Microbiome.** A predictor of inter-person response in ND [P] [R10]. It is not a dynamic
factor at simulator timescales [I].

### Medication

**D10 Dose / settings.** Mechanism: insulin delivered vs insulin needed. A literature magnitude
does not apply: in replay the settings are donor-specific. Thabit et al. state that daily
insulin needs can vary from one-third to threefold [P, review claim] [R64].

**D11 Bolus timing.**

- A glulisine bolus 20 min before the meal gave lower glucose at 60 and 120 min than a bolus at
  the meal or 20 min after it. Glycaemic AUC was 159.5 vs 187.0 vs 184.5 mg/dL [P, T1D, n=23]
  [R11].
- A 780G review reports comparable TIR for pre-meal and at-meal bolusing, but worse excursions
  when the bolus comes >30 min after the meal [P, review] [R61].

**D12 Interactions and adjunct drugs.**

- GLP-1RA in overweight T1D: −9.24 U/day insulin, HbA1c −0.25 %, OR for hypos raised [P,
  meta-analysis of 13 studies] [R57].
- SGLT2i in T1D lowers insulin need and carries DKA risk [U].
- β-blockers mask hypo symptoms [U].

**D13 Glucocorticoids.** Mechanism: hepatic glucose output and peripheral resistance. Direction:
↑↑.

- Inpatients on ≥20 mg/day prednisolone were started at 130 % of their usual insulin dose, and
  the insulin dose had to be increased further over 3 days [P, mixed diabetes, n=50] [R44].
- The pattern is an afternoon–evening peak with a morning dose [U] [R44 review context].
- No T1D-only magnitude was found. This is a **gap**.

**D14 Niacin.** A meta-analysis reports lipid effects and FPG [P for existence; FPG magnitude
truncated, so **[U]**; T2D] [R43].

### Activity

**D15/D16 Exercise, acute.** Mechanism: insulin-independent muscle uptake, faster insulin
absorption, catecholamines when intense. Direction: ↓ aerobic, smaller ↓ resistance, ↑
sprint/anaerobic.

- T1DEXI (real world, 497 adults): change during exercise −18 ± 39, −14 ± 32 and −9 ± 36 mg/dL
  for aerobic, interval and resistance sessions. This was similar across closed-loop, pump and
  MDI users. TIR was higher over the next 24 h [P] [R13].
- Exercise at 80 % VO2max in the fasted state: glucose 86 → 127 mg/dL, sustained for 2 h [P,
  T1D on CSII, n=8] [R16].
- Leg exercise increased absorption from a leg injection site by 135 % in the first 10 min, and
  by 50 % at 60 min. Arm or abdominal sites cut exercise-induced hypoglycaemia by 57 % and 89 %
  [P] [R17].
- Consensus: hypoglycaemia within about 45 min if insulin is not reduced [U] [R12].

Frequency: 2–5 sessions a week in T1DEXI-type users [I]. Walking is daily.

**X6 Exercise, delayed.**

- Afternoon exercise at 95 % of lactate threshold: glucose requirement raised during and just
  after exercise, then again at **7–11 h** [P, peds, n=9] [R14].
- Overnight mean 131 vs 154 mg/dL. Overnight hypos on 48 % of exercise nights (26 % + 22 %)
  vs 28 % (6 % + 22 %) on sedentary nights [P, peds, n=50] [R15].
- Midday exercise: GIR elevated for up to 11 h, but not biphasic [U] (Davey 2013, via
  secondary).

**D17 / D18 / D19.** These are modifiers of D16: fitness, time of day, and timing of food and
insulin around exercise. No separate magnitudes. Model them as parameters [I].

### Biological

**D20 Sleep loss.**

- One night of 4 h sleep: glucose infusion rate about −21 % and glucose disposal 25.5 → 22.0
  µmol/kg LBM/min. EGP unchanged [P, T1D, n=7] [R19].
- Brown reports ~25 % more insulin after <7 h of sleep [anecdote].

**D21a Illness and infection.** Mechanism: cortisol, catecholamines, cytokines, causing insulin
resistance. Direction: ↑↑, or ↓ with vomiting or poor intake.

- Three adults in a preprint: bolus +42 % and +39 % vs the weeks before and after, with BG still
  higher [U] [R62].
- Guidelines: raise insulin, never omit basal. The ISPAD "+10–20 % of TDD" rule was not verified
  [U] [R63].
- **Major evidence gap.** No adequately sized CGM + pump study quantifying ISF change by illness
  type was found.

**D21b Psychological stress.**

- Trier Social Stress Test while fasting: no effect on glucose.
- The same test 75 min after a meal: a **45-min delay** in the post-meal glucose fall [P, T1D,
  n=20+20] [R20].

The effect is small and context-dependent.

**D22 Recent hypoglycaemia.**

- Afternoon hypoglycaemia lowered the glucose thresholds for, and the size of, the next
  morning's epinephrine and symptom responses (1,160 vs 2,040 pmol/L at 2.8 mmol/L) [P, T1D]
  [R21].
- This changes counter-regulation and awareness rather than adding glucose. It also links to
  X13.

**D23 Overnight BG → next day.** No study was found. It is an emergent outcome, not a driver [I].

**D24 Dawn phenomenon.**

- With insulin waning removed: about +30 % hepatic glucose production and −25 % peripheral
  utilisation at 06:00–08:00 vs 00:00–02:00, caused by nocturnal GH spikes [P, T1D, n=12] [R22].
- A rise of 15–25 mg/dL from the nocturnal nadir [U, Porcellati review via secondary] [R23].
- Found in 8.6 % of youth (DPV) and about 50 % of adults (Ostrovski 2019) [both U].

**D25 Infusion set.**

- Lines left unchanged for up to 100 h: mean BG 122.7 → 163.9 mg/dL from day 2 to day 5, fasting
  120 → 155, >180 time 14.5 → 38.3 %, with TDD 48.5 → 55.3 U [P, T1D, n=20] [R24].
- 7-day SteadiSet: TIR rose to day 3 and then fell to day 7. TDD rose from day 4. The broad
  7-day survival estimate was 84 % [P, n=260] [R25].
- Two kinds of event to model: a gradual efficacy decay over days of wear, and a hazard of acute
  failure [I].

**D26 Lipohypertrophy.**

- Lispro into LHT vs normal tissue: insulin AUC 131 vs 165, Cmax 61 vs 79; within-subject CV of
  AUC 52 vs 11 %; post-meal BG ≥26 % higher (2 h BG 150 vs 104 mg/dL) [P, T1D, n=13] [R26].
- Prevalence 64.4 % in insulin injectors. Unexplained hypos in 39 % of those with LH vs 6 %
  without [P] [R27].
- Prevalence at pump sites was not established [U].

**D27 Intramuscular delivery.** Absorption from superficial thigh muscle is ≥50 % faster than
from subcutaneous tissue (t½ 123 vs >180 min) [P, n=10] [R28]. For exercise, see D16.

**D28 Allergies.** No study found. Tier 3.

**D29 Hyperglycaemia-induced resistance.** After 24 h at 20 mM vs 7 mM: total glucose uptake
−26 %, forearm uptake −35 %, non-oxidative disposal −54 % [P, T1D, n=8] [R29]. This supports a
state-dependent SI reduction after prolonged highs [I].

**D30 Menstrual cycle.**

- Adults on AID (77 people, 380 cycles, real-world Tidepool data): TDD and carbohydrate intake
  peak in the luteal phase. Model-derived SI is +2.6 % in the early follicular phase and −2.6 %
  in the mid-luteal phase. 84.7 % of people follow the trend, with large heterogeneity [P] [R30].
- Adolescents on AID (51 people, 459 cycles): luteal TDD 1.05 vs 0.95 U/kg/day; TIR −6.3 pts;
  TAR +5.5 pts; mean glucose +12.5 mg/dL; CV 39.4 vs 35.0 %. TBR and carbohydrate intake did not
  differ [P] [R31].
- Note: the adult SI change is small, yet TDD visibly changes. AID absorbs part of the effect,
  and carbohydrate intake also changes [I].

**D31 Puberty.** Insulin-stimulated glucose metabolism is 25–30 % lower in pubertal than
prepubertal T1D, inversely related to GH [P] [R32]. The diaTribe figure of "30–50 % more insulin"
is [U].

**D32 Coeliac disease.**

- Prevalence 6.0 % (95 % CI 5.0–6.9); 6.2 % in children vs 2.7 % in adults [P] [R33].
- On a gluten-free diet: no difference in HbA1c, hypos or TDD [P, systematic review] [R34].
- Undiagnosed coeliac disease may cause erratic absorption [U].

**D33 Smoking.** Smoking (but not snuff) impaired insulin action in a clamp [P, ND smokers, n=7]
[R35].

### Environmental

**D34 Insulin degradation.** Insulin kept 4 weeks at 25–37 °C (cycling) retained potency by HPLC
and bioassay, with <1 % loss [U] [R36]. An older study found 14–18 % loss at 32–37 °C for 28
days [U]. Tier 3, except as a rare scenario.

**D35 CGM accuracy.**

- Dexcom G7: MARD 8.2 % (arm) / 9.1 % (abdomen); %20/20 = 95.3 % (arm) [P] [R37].
- Dexcom G6: factory-calibrated, about 9–10 % [U] [R38].
- Error is larger on day 1 and at low glucose [U].

**X7 CGM artefacts and lag.**

- Pressure-induced sensor attenuations were about 3 % of CGM readings over 1,125 nights of
  low-glucose-suspend trial data [P] [R39].
- Physiological blood → ISF lag is 5.3–6.2 min [P, ND, n=8] [R40]. Device filtering adds more
  [U].

**D36 Temperature.**

- Sauna, 2 × 25 min at 85 °C: insulin absorption +110 % and BG 3.0–3.3 mmol/L lower [U: abstract
  numbers via secondary; the PubMed record has no abstract] [R18].
- Seasonal effect: HbA1c lower in spring/summer and higher in autumn/winter [P, peds, n=114]
  [R41].

**D37 Sunburn.** No study found.

**D38 Altitude.** Below 5,000 m: insulin −14 % (NS) and glucose stable. Above 5,000 m: glucose
7.5 → 9.5 mmol/L, correlated with acute mountain sickness (r = 0.86) [P, T1D, n=8] [R42].

### Behavioural

**D39–D42.** These are glucose-check frequency, defaults, decision biases, and family/social
pressure [R1]. They act through dosing and eating behaviour (X1, X2, D1, D11), so represent them
as per-person behaviour traits [I].

**X1 Rescue carbohydrates.**

- 271 events in 121 adults. Mean treatment 32 ± 24 g. 73 % of people over-treated (>20 g within
  15 min). Over-treaters were younger and more fearful [P] [R45].
- 10,977 isCGM hypo events: 33 % were followed by >180 mg/dL within 2 h. Median 3.0 rebound highs
  per person per 14 days [P, n=159] [R46].
- Over-treaters report more stress and depressed mood [P] [R47].

**X2 Missed / late / unannounced boluses.**

- Pump youth missing ≥1 meal bolus per week: HbA1c 8.8 vs 8.0 % [P, n=48] [R48].
- 780G compensates for missed boluses up to about 30 g [P, review] [R61].
- This is the project's own central topic (unannounced meals) [I].

**X13 Impaired hypoglycaemia awareness.** 19.5 % of adults with T1D, with a 6× higher rate of
severe hypos [P, n=518] [R56]. It delays rescue (X1) [I].

**X15 Correction behaviour.** Rebound hypos (high → low within 2 h) make up 29 % of hypo events
and correlate with rebound highs (ρ 0.84). The authors interpret this as a behavioural trait of
intensive correction [P] [R46].

### Added biological and device factors

**X3 Absorption and action variability.** For regular s.c. insulin under clamp conditions, the
intra-individual CV of PD measures is 15–25 % [P, ND, review] [R49]. For glargine 300, the
within-subject CV of 24 h exposure is 17 % and of GIR-AUC about 35 % [U] [R59]. Lipohypertrophy
raises the CV to about 50 % (D26).

**X4 Day-to-day variation in need.** Over 12 weeks of hybrid closed loop: the within-person CV of
TDD was 17 %, daytime 22 %, overnight 31 % [P, n=32] [R50]. This is the best single number for
the "unexplained" daily SI noise term. Part of it is meals and exercise, so it is an upper bound
on pure SI noise [I].

**X5 Circadian SI.**

- In C-peptide-negative T1D, identical meals at 07:00, 13:00 and 19:00 led to higher insulin and
  less EGP suppression at breakfast. No *uniform* diurnal pattern in SI was found [P, n=19] [R51].
- Seven distinct daily SI patterns were identified across 20 people, giving the UVA/Padova
  circadian SI model with deviations of up to 40 % [P] [R52].

The pattern is per person, not one population curve [P/I].

**X8 Loop / pump outage.** No literature quantifies this. The AGENTS.md project traps (loop
offline, pump errors) show it is frequent in field data [I]. This is a **gap** for a cited
magnitude.

**X9 Pregnancy.** Insulin requirement peaks at week 9, reaches a nadir at week 16, then rises
4.1 %/week (U/kg) to a second peak at week 37. 8 of 9 severe hypos occurred early in pregnancy
[P, n=65] [R53].

**X10 Menopause.** 548 post- vs 630 pre-menopausal pump users: TDD, U/kg and basal all differ
(p < 0.0001); the abstract excerpt does not give the direction or % [P, partial] [R54].

**X11 Gastroparesis.** The 10-year cumulative incidence is 5.2 % in T1D vs 0.2 % in controls
[P] [R55]. It slows and adds variance to carbohydrate appearance [I].

**X12 Thyroid.** The association with T1D is established [P, review] [R58]. The prevalence
figure and any T1D insulin-dose effect are [U].

**X14 Slow drift.** This covers season [R41], weight and fitness. AID and settings edits absorb
it [I].

**X16 Other.** Cannabis, Ramadan fasting, travel and jet lag: not searched in depth. Tier 3 [I].

---

## 4. Biggest evidence gaps

1. **Illness.** There is no adequate quantitative study of SI and ISF change by illness type and
   day in pump/AID users. The best figure is a 3-person preprint.
2. **Infusion-set failure hazard.** The wear-day decay is measured (Thethi, SteadiSet), but the
   rate and magnitude of acute occlusion or kink events in real use is not.
3. **Glucocorticoids in T1D.** Available dosing data come from mixed inpatient populations.
4. **Exercise in AID users at the level of the individual session.** T1DEXI gives means with
   SD ≈ 35 mg/dL. Mapping intensity, duration and IOB to an SI/absorption model remains
   simulator-calibration work.
5. **Caffeine, smoking and dawn magnitude in T1D**: the evidence is in ND people, or [U].
6. **Pure day-to-day SI noise vs behaviour.** The closed-loop TDD CV (17–31 %) mixes the two.
   No study separates them.
7. **Loop/pump outages.** There is no literature. This must be measured from the project's own
   donor data.

---

## 5. References

- [R1] Brown A. *42 Factors That Affect Blood Glucose.* diaTribe, 28 Oct 2018 (booklet PDF).
  https://www.lmc.ca/wp-content/uploads/2023/08/42FactorsPDF-October-28-2018.pdf ; original page
  https://diatribe.org/diabetes-management/42-factors-affect-blood-glucose
- [R2] Brazeau AS et al. Carbohydrate counting accuracy and blood glucose variability in adults
  with T1D. *Diabetes Res Clin Pract* 2013;99:19–23. doi:10.1016/j.diabres.2012.10.024
- [R3] Smart CE et al. Children and adolescents on intensive insulin therapy maintain postprandial
  glycaemic control without precise carbohydrate counting. *Diabet Med* 2009;26:279–85.
  doi:10.1111/j.1464-5491.2009.02669.x
- [R4] Wolpert HA et al. Dietary fat acutely increases glucose concentrations and insulin
  requirements in patients with T1D. *Diabetes Care* 2013;36:810–6. doi:10.2337/dc12-0092
- [R5] Smart CE et al. Both dietary protein and fat increase postprandial glucose excursions in
  children with T1D, and the effect is additive. *Diabetes Care* 2013;36:3897–902.
  doi:10.2337/dc13-1195
- [R6] Paterson MA et al. Increasing the protein quantity in a meal results in dose-dependent
  effects on postprandial glucose in T1D. *Diabet Med* 2017. doi:10.1111/dme.13347
- [R7] Keijzers GB et al. Caffeine can decrease insulin sensitivity in humans. *Diabetes Care*
  2002;25:364–9. doi:10.2337/diacare.25.2.364
- [R8] Turner BC et al. The effect of evening alcohol consumption on next-morning glucose control
  in T1D. *Diabetes Care* 2001;24:1888–93. doi:10.2337/diacare.24.11.1888
- [R9] Burge MR et al. Differential effects of fasting and dehydration in the pathogenesis of DKA.
  *Metabolism* 2001;50:171–7. doi:10.1053/meta.2001.20194
- [R10] Zeevi D et al. Personalized nutrition by prediction of glycemic responses. *Cell*
  2015;163:1079–94. doi:10.1016/j.cell.2015.11.001
- [R11] Cobry E et al. Timing of meal insulin boluses to achieve optimal postprandial glycemic
  control in T1D. *Diabetes Technol Ther* 2010;12:173–7. doi:10.1089/dia.2009.0112
- [R12] Riddell MC et al. Exercise management in T1D: a consensus statement. *Lancet Diabetes
  Endocrinol* 2017;5:377–90. doi:10.1016/S2213-8587(17)30014-1
- [R13] Riddell MC et al. Acute glycemic effects of different types of structured exercise in T1D
  (T1DEXI). *Diabetes Care* 2023. doi:10.2337/dc22-1721
- [R14] McMahon SK et al. Glucose requirements after moderate-intensity afternoon exercise in
  adolescents with T1D are increased in a biphasic manner. *JCEM* 2007;92:963–8.
  doi:10.1210/jc.2006-2263
- [R15] Tsalikian E et al. (DirecNet). Impact of exercise on overnight glycemic control in
  children with T1D. *J Pediatr* 2005. doi:10.1016/j.jpeds.2005.04.065
- [R16] Mitchell TH et al. Hyperglycemia after intense exercise in IDDM subjects during CSII.
  *Diabetes Care* 1988;11:311. doi:10.2337/diacare.11.4.311
- [R17] Koivisto VA, Felig P. Effects of leg exercise on insulin absorption in diabetic patients.
  *NEJM* 1978;298:79–83. doi:10.1056/NEJM197801122980205
- [R18] Koivisto VA. Sauna-induced acceleration in insulin absorption. *BMJ* 1980;281:621.
  doi:10.1136/bmj.281.6240.621-a
- [R19] Donga E et al. Partial sleep restriction decreases insulin sensitivity in T1D. *Diabetes
  Care* 2010;33:1573–7. doi:10.2337/dc09-2317
- [R20] Wiesli P et al. Acute psychological stress affects glucose concentrations in T1D following
  food intake but not in the fasting state. *Diabetes Care* 2005;28:1910. doi:10.2337/diacare.28.8.1910
- [R21] Dagogo-Jack SE, Craft S, Cryer PE. Hypoglycemia-associated autonomic failure in IDDM.
  *J Clin Invest* 1993. doi:10.1172/JCI116302
- [R22] Perriello G et al. Nocturnal spikes of growth hormone secretion cause the dawn phenomenon
  in T1D. *Diabetologia* 1990. doi:10.1007/BF00586461
- [R23] Porcellati F et al. Thirty years of research on the dawn phenomenon. *Diabetes Care*
  2013;36:3860–2. doi:10.2337/dc13-2088
- [R24] Thethi TK et al. Consequences of delayed pump infusion line change in T1D. *J Diabetes
  Complications* 2010. doi:10.1016/j.jdiacomp.2009.03.002
- [R25] Lal RA et al. A multicenter study of an investigational extended wear insulin infusion set
  in adults with T1D. 2026 (PMID 40780817). doi:10.1177/19322968241233607 (the DOI is as listed
  in PubMed)
- [R26] Famulla S et al. Insulin injection into lipohypertrophic tissue: blunted and more variable
  insulin absorption and action. *Diabetes Care* 2016;39:1486–92. doi:10.2337/dc16-0610
- [R27] Blanco M et al. Prevalence and risk factors of lipohypertrophy in insulin-injecting
  patients. *Diabetes Metab* 2013. doi:10.1016/j.diabet.2013.05.006
- [R28] Frid A et al. Effects of accidental intramuscular injection on insulin absorption in IDDM.
  *Diabetes Care* 1988;11:41. doi:10.2337/diacare.11.1.41
- [R29] Vuorinen-Markkola H et al. Mechanisms of hyperglycemia-induced insulin resistance in T1D.
  *Diabetes* 1992;41:571. doi:10.2337/diab.41.5.571
- [R30] Hossmann S et al. Effects of menstrual cycle on insulin sensitivity in T1D: individuals
  using AID. *Diabetes Care* 2026;49:1673–80. doi:10.2337/dc26-0692
- [R31] Struckmeyer N et al. Menstrual cycle-related variations in insulin requirements during AID
  in adolescents with T1D. *J Pediatr Endocrinol Metab* 2026;39:990–9. doi:10.1515/jpem-2026-0309
- [R32] Amiel SA et al. Impaired insulin action in puberty. *NEJM* 1986;315:215–9.
  doi:10.1056/NEJM198607243150402
- [R33] Elfström P et al. Systematic review with meta-analysis: associations between coeliac
  disease and T1D. *Aliment Pharmacol Ther* 2014;40:1123–32. doi:10.1111/apt.12973
- [R34] Mozzillo E et al. Impact of gluten-free diet in youth with T1D and coeliac disease:
  systematic review. *Diabetes Res Clin Pract* 2022. doi:10.1016/j.diabres.2022.110032
- [R35] Attvall S et al. Smoking induces insulin resistance. *J Intern Med* 1993.
  doi:10.1111/j.1365-2796.1993.tb00680.x
- [R36] Kaufmann B et al. Heat-stability study of various insulin types in tropical temperature
  conditions. *PLoS ONE* 2021 [U].
  https://uswest2.scienceportal.msf.org/assets/heat-stability-study-various-insulin-types-tropical-temperature-conditions-new-insights-towards-improving-diabetes-care
- [R37] Garg SK et al. Accuracy and safety of Dexcom G7 CGM in adults. *Diabetes Technol Ther*
  2022. doi:10.1089/dia.2022.0011
- [R38] Wadwa RP et al. Accuracy of a factory-calibrated real-time CGM during 10 days of use.
  *Diabetes Technol Ther* 2018. doi:10.1089/dia.2018.0150
- [R39] Baysal N et al. A novel method to detect pressure-induced sensor attenuations (PISA) in an
  artificial pancreas. *J Diabetes Sci Technol* 2014. doi:10.1177/1932296814553267
- [R40] Basu A et al. Time lag of glucose from intravascular to interstitial compartment in
  humans. *Diabetes* 2013. doi:10.2337/db13-1132
- [R41] Nordfeldt S, Ludvigsson J. Seasonal variation of HbA1c in intensive treatment of children
  with T1D. *J Pediatr Endocrinol Metab* 2000. doi:10.1515/jpem.2000.13.5.529
- [R42] de Mol P et al. Increased insulin requirements during exercise at very high altitude in
  T1D. *Diabetes Care* 2011. doi:10.2337/dc10-2015
- [R43] Ding Y et al. Effect of niacin on lipids and glucose in T2D: meta-analysis. *Clin Nutr*
  2015. doi:10.1016/j.clnu.2014.09.019
- [R44] Radhakutty A et al. Treatment of prednisolone-induced hyperglycaemia in hospitalized
  patients. *Diabetes Obes Metab* 2017. doi:10.1111/dom.12859
- [R45] Savard V et al. Treatment of hypoglycemia in adult patients with T1D: an observational
  study. *Can J Diabetes* 2016. doi:10.1016/j.jcjd.2016.05.008
- [R46] Hansen et al. Rebound hypoglycemia and hyperglycemia in T1D. *J Diabetes Sci Technol*
  2024. doi:10.1177/19322968231168379
- [R47] Martyn-Nemeth P et al. Hypoglycaemic treatment adherence in adults with T1D. *Nurs Open*
  2019. PMID 31367410
- [R48] Burdick J et al. Missed insulin meal boluses and elevated HbA1c in children on pump
  therapy. *Pediatrics* 2004;113:e221. doi:10.1542/peds.113.3.e221
- [R49] Heinemann L. Variability of insulin absorption and insulin action. *Diabetes Technol Ther*
  2002;4:673. doi:10.1089/152091502320798312
- [R50] Ruan Y et al. Variability of insulin requirements over 12 weeks of closed-loop insulin
  delivery in adults with T1D. *Diabetes Care* 2016;39:830. doi:10.2337/dc15-2623
- [R51] Hinshaw L et al. Diurnal pattern of insulin action in T1D. *Diabetes* 2013.
  doi:10.2337/db12-1759
- [R52] Visentin R et al. Circadian variability of insulin sensitivity: physiological input for
  in silico artificial pancreas. *Diabetes Technol Ther* 2015. doi:10.1089/dia.2014.0192
- [R53] García-Patterson A et al. Insulin requirements throughout pregnancy in women with T1D:
  three changes of direction. *Diabetologia* 2010. doi:10.1007/s00125-009-1633-z
- [R54] Melmer A et al. Differences in insulin dosing in women with T1D before and after the
  menopause. *Swiss Med Wkly* 2021. doi:10.4414/smw.2021.w30025
- [R55] Choung RS et al. Risk of gastroparesis in subjects with type 1 and 2 diabetes in the
  general population. *Am J Gastroenterol* 2012. doi:10.1038/ajg.2011.310
- [R56] Geddes J et al. Prevalence of impaired awareness of hypoglycaemia in adults with T1D.
  *Diabet Med* 2008. doi:10.1111/j.1464-5491.2008.02413.x
- [R57] Purcell et al. GLP-1RA treatment in overweight/obesity and T1D: systematic review and
  meta-analysis. *Diabetes Obes Metab* 2026. doi:10.1111/dom.70188
- [R58] Biondi B et al. Thyroid dysfunction and diabetes mellitus. *Endocr Rev* 2019.
  doi:10.1210/er.2018-00163
- [R59] Becker RHA et al. (glargine 300 within-subject variability, 24 h clamps) [U].
  https://pmc.ncbi.nlm.nih.gov/articles/PMC4674964
- [R61] Narrative review of meal management with MiniMed 780G. *Diabetes Obes Metab* 2026
  (PMID 41311224).
- [R62] Glucose and insulin during infection weeks in 3 adults with T1D (JMIR preprint) [U].
  https://preprints.jmir.org/preprint/18911
- [R63] Phelan H et al. ISPAD 2022 guidelines: sick day management. *Pediatr Diabetes*
  2022;23:912–25 [U, not retrieved].
- [R64] Thabit H, Hovorka R. Coming of age: the artificial pancreas for T1D. 2016 (PMID 27364997).
