# 03 — Sensor (CGM) and insulin-delivery device evidence

Evidence base for the CGM model and the delivery-device fault model of the additive patient
simulator. Each number carries a reference; the tags say how far it was checked:

- *(no tag)*: checked against the source's full text or abstract.
- **[secondary]**: checked only against a secondary source (manufacturer page, news summary,
  another paper quoting it). Confirm against the primary before relying on it.
- **[unverified]**: not checked against any source. Background knowledge or a derivation.
- **[derived]**: our own arithmetic on the cited numbers. The inputs are checked.

---

## 1. Summary tables

### 1.1 Per-sensor parameter table

Lag is the apparent sensor-vs-reference delay reported by the accuracy study. That delay already
includes the device's own filtering and lag compensation, so it is shorter than the physiological
BG-to-IG delay (§2.2).

| | Dexcom G6 | Dexcom G7 | FreeStyle Libre 2 | FreeStyle Libre 3 (/3 Plus) | Medtronic Guardian 3 / 4 (Simplera) | Eversense (E3 / 365) |
|---|---|---|---|---|---|---|
| Overall MARD vs YSI (pivotal) | 9.0% (Shah 2018 reprocessed FC) [secondary]; 10.0% (Wadwa 2018, n=262) | 8.2% arm / 9.1% abdomen (Garg 2022) | 9.2% adults / 9.7% peds (Alva 2022) | 7.8% (≥6 y; adults 7.5%) (Alva 2023) | G4: 10.6% adult / 11.6% peds [secondary]; Enlite-era model 11.7% (Biagi 2017) | 365: 8.8% [secondary] |
| Independent head-to-head MARD (Eichenlaub 2025; YSI / venous lab / capillary) | — | 12.0 / 9.9 / 10.1% | — | 11.6 / 9.5 / 9.7% | Simplera 11.6 / 13.9 / 16.6% | — |
| Systematic bias vs YSI (head-to-head) | — | +7.1% ± 13.9 | — | +8.4% ± 13.4 | Simplera −6.0% ± 13.3 | — |
| Day-1 accuracy | %20/20 day 1 88.6% vs day 10 90.6% (Wadwa 2018) | MARD day 1: 11.9% arm / 12.9% abd vs 6.9–8.6% days 2–10.5 (Garg 2022) | not extracted | MARD days 1–3 8.6% vs 6.4–7.0% days 9–14 (Alva 2023) | first 12 h vs capillary: Simplera bias −16.9% (Eichenlaub 2025) | — |
| First-12-h bias vs capillary (Eichenlaub 2025) | — | −7.8% | — | −5.9% | −16.9% (Simplera) | — |
| Hypo-range accuracy | — | 40–60 mg/dL: MAD 8.5 arm / 10.3 abd mg/dL; %15/15 85.1 / 77.1% | <70: 94.3% (adult) within 15 mg/dL | <54: MAD 16.1 mg/dL (n=15 pairs only); 54–69: 88.6% within 15 mg/dL | Simplera more accurate than FL3/G7 in hypo range (Eichenlaub 2025) | — |
| Apparent lag | 3.7 min; 23% of sensors <1 min (Calhoun, cited by Garg 2022) [secondary] | 3.5 min (arm 3.6, abd 3.4) | 2.4 ± 4.6 min adults | 1.8 ± 4.8 min | Enlite model τ 9.4 ± 6.5 min (Biagi 2017) | — |
| Model τ (BG→IG, error-model fit) | 3.78 min median [IQR 2.39–5.96] (Vettoretti 2019) | use G6 value [unverified carry-over] | — | — | 9.4 ± 6.5 min; median 8.4 (5th–95th 0.3–23.4) (Biagi 2017, Enlite) | — |
| Reporting cadence | 5 min (Vettoretti 2019) | 5 min [unverified]; backfill up to 24 h of missed data (Garg 2022) | 1 min to reader/app when alarms on (Alva 2022/2023); 15-min history [unverified] | 1 min (Alva 2023); 5-min auto-log [unverified]. Displayed "current" vs auto-logged values differ (§2.5) | 5 min [unverified] | 5 min [unverified] |
| Range / clamp | 40–400 mg/dL; out-of-range shows LOW/HIGH (Vettoretti 2019 drops values saturated at 40/400) | 40–400 [secondary] | 40–500 [unverified] | 40–500 [unverified] | 40–400 [unverified] | 40–400 [unverified] |
| Quantisation | integer mg/dL [unverified] | integer mg/dL [unverified] | integer mg/dL [unverified] | integer mg/dL [unverified] | integer mg/dL [unverified] | — |
| Warm-up | 2 h (Garg 2022) | 27 min (Garg 2022) | 1 h [unverified] | 1 h [unverified] | 2 h (Medtronic 780G flyer) [secondary] | 24 h, then 4 fingerstick calibrations within 36 h [secondary] |
| Session length | 10 d | 10 d + 12 h grace (Garg 2022); 15-d variant exists [unverified] | 14 d | 14 d (3 Plus 15 d + grace) [unverified] | 7 d [secondary] | 365 d; daily calibration to day 13, then weekly [secondary] |
| Survival to end of life (Eichenlaub 2025, small n) | — | 100% (n=48; worn ≤5 d by protocol, censored) | — | 91.7% (n=25; 1 sensor error, 1 adhesive) | Simplera 81.5% (n=49; all 9 failures sensor errors) | — |
| Interferents | acetaminophen ≤1 g q6h does not interfere; hydroxyurea reads high (Dexcom interference page) [secondary] | same as G6 [secondary] | vitamin C >500 mg/day may raise readings [secondary] | vitamin C >500 mg/day (Libre 3); >1000 mg/day (Libre 3 Plus) [secondary] | G3: acetaminophen raised positive bias in vitro (trial protocol NCT04378114) [secondary] | tetracyclines (forces calibration) [secondary] |

### 1.2 Device-fault table

| Fault / effect | Size | Frequency | Source |
|---|---|---|---|
| Infusion-set failure with prolonged hyperglycaemia (CGM >250 for ≥2 h, >300 at removal) | glucose >250 mg/dL for 5.1 ± 3.7 h before removal | 3.3% of sets removed before 72 h (1.8% <48 h, 1.0% <24 h); 7.4% under a looser definition. Adults 1.9%, age 14–17 5.8%. 90° Teflon 4.0%, angled Teflon 1.3%, steel 1.9%. About 4 per year per user | Kanapka 2022 (22,741 sets, 263 participants) |
| Failure when a set is worn to 7 days | 30% of failures = hyperglycaemia plus failed correction | 64% failed by day 7 (steel and Teflon alike); 15% of Teflon sets failed at insertion (kinking). The individual was the strongest predictor of wear length | Patel 2014 (n=20, crossover) |
| Extended (7-day) set, unexplained hyperglycaemia | — | 0.1% (lispro) / 0.4% (aspart) of sets through day 7; 77.8% of sets survived to day 7 | Brazg 2022 (3041 sets, n=259) |
| Occlusions detected by direct volume-sensing pump | detected within 30 min of glucose starting to rise | 67 events in 15 of 20 adults over 8 weeks, about 0.4 per user-week or about 1.8 per user-month [derived] | Ruiz 2026 (twiist) |
| Occlusion-alarm latency, conventional pumps | Omnipod, MiniMed 600/700 and t:slim X2 took 5–22.5× longer than the volume-sensing pump on bench at 0.3–1.0 U/h. Absolute times are in a figure only. Air in the reservoir was delivered with no alarm by all three | — | Butterfield 2024 (bench) |
| Silent insulin non-delivery (all causes) | — | 40–50% of pump users have ≥1 event per year; up to once per month | quoted in Butterfield 2024 [secondary] |
| Self-reported set problems | — | ever experienced: kinking 64.1%, blockage 54.3% of 92 users; mean set use 3.2 d | Pickup 2014 [secondary] |
| Site-age absorption shift (PD) | day 4 (84 h) vs day 1 (12 h), 0.2 U/kg bolus: Tmax GIR 97→79 min; Ti50 51→38 min; Td50 195→153 min; glucose-infusion end 254→211 min; AUC GIR 948→847 (−11%, ns) | every site | Swan 2009 (clamp, n=17 youth) |
| Glucose rise with a set kept in place too long | daily mean glucose 122.7 → 163.9 mg/dL from day 2 to day 5; %>180 from 14.5% to 38.3% | every overdue site | Thethi 2010 (n=20, up to 100 h) |
| Glucose drift across a set's wear | faster aspart: mean SG 24 h before vs after a change 10.14 vs 9.39 mmol/L (+0.75 mmol/L ≈ +13.5 mg/dL by the end of wear) [derived]; insulin aspart: 9.48 vs 9.47 (none) | every change; mean wear 2.9–3.0 d | Gorst-Rasmussen 2022 (Onset 5 post hoc) |
| Heat exposure | lispro at 37 °C in pumps for 48 h kept full HPLC potency (Δ ≤4%); basal pens at 37 °C for 21 d showed no clinical or UHPLC loss | rare in practice; labels say discard reservoir at 6 d (aspart/lispro) or after >37 °C exposure [secondary] | Lougheed 1997; Kongmalai 2022 |
| Pulse quantisation (Omnipod) | 0.05 U steps; bolus 1.5 U/min. Temp basals deliver floor(rate·dur / 0.05) whole pulses, so 5-min re-temps lose the fraction | every temp | Omnipod spec sheet [secondary]; LoopEval internal measurement (engine `BasalAccumulator` already models it) |

---

## 2. CGM — sections

### 2.1 Published error-model structures

**Breton & Kovatchev 2008 (JDST 2:853).** FreeStyle Navigator, 136 T1D (≈20,600 SMBG pairs) plus
28 T1D with YSI every 15 min. This is the sensor model in the 2008 FDA-accepted UVA/Padova simulator.
- BG→IG: diffusion model `dIG/dt = −(1/τ)(IG − BG)`. Their empirical estimate is "a time lag of
  5 minutes (which produces a delay of approximately 15 minutes)". The rate-of-change analysis gave
  a 17-min delay on this dataset.
- Noise: `e_n = 0.7·(e_{n−1} + υ_n)`, with υ iid N(0,1), mapped through a Johnson S_U transform
  `ε_n = ξ + λ·sinh((e_n − γ)/δ)`, with **ξ = −5.471, λ = 15.96, δ = 1.6898, γ = −0.5444**.
  Sensor error mean 0.76 mg/dL, SD 11 mg/dL.
- Errors run positive when BG falls and negative when it rises, which is the lag signature.
- Caveat: Facchinetti, Sparacino & Cobelli 2010 (JDST 4:4) show that imperfect recalibration or
  BG-to-IG modelling creates spurious autocorrelation. Even a white sensor error can look AR(1)
  after reconstruction. So the AR(1) = 0.7 partly reflects how it was identified.

**Facchinetti et al. 2014 (IEEE TBME 61:620).** Uses n = 4 simultaneous Dexcom SEVEN Plus traces
plus frequent BG in 36 datasets. The structure became standard:
`CGM_i(t) = a(t)·[h_τ ∗ BG](t) + b(t) + cc(t) + ssc_i(t)`, where h_τ is the first-order BG→IG
kernel, a(t) and b(t) are time-varying calibration/drift polynomials, cc is a common AR noise and
ssc_i a sensor-specific AR noise. A secondary report puts the MARD decomposition at calibration
12.8%, kinetics 3.5% and noise 5.6% [secondary]. **Calibration error dominates.**

**Facchinetti et al. 2015 (Med Biol Eng Comput 53:1259).** Dexcom G4 Platinum vs G4AP, 12-h windows.
MARD: 7P 14.2%, G4P 11.1%, G4AP 10.0%. In G4AP the blood-to-interstitium component fell by a
further 20% because of the processing algorithm. Optimal calibration models were (poly1, poly0) on
day 1 and (poly0, poly0) on days 4 and 7. Previous-generation τ: G4P 9.7 min, G4AP 7.7 min (as
cited in Vettoretti 2019).

**Biagi et al. 2017 (Sensors 17:1361), Medtronic Paradigm Veo Enlite.** This is the closest
published model to the Guardian family.
- 37 inpatient sessions in 10 T1D. The linear calibration model was chosen.
- τ = 9.4 ± 6.5 min, median 8.4 (5th–95th 0.3–23.4).
- a0 = 1.1 ± 0.4 (median 1.1, 0.7–1.8); a1 = −0.0009 ± 0.0016 (time-unit label garbled in the text).
- Common noise: `cc(t) = 1.584·cc(t−1) − 0.8842·cc(t−2) + 0.1798·cc(t−3) + w`, with w ~ N(0, 3.98 mg²/dL²).
- Sensor-specific noise: `ssc(t) = 1.367·ssc(t−1) − 0.4816·ssc(t−2) + w`, with w ~ N(0, 2.54 mg²/dL²).
- MARD components: global 11.7%, BG-IG 3.6%, calibration 11.3%, noise 4.2%.
- Guardian 3/4 and Simplera use the same family of electrochemistry but newer algorithms;
  carrying these parameters over is **[unverified]**.

**Vettoretti, Battocchio, Sparacino & Facchinetti 2019 (Sensors 19:5320), Dexcom G6
factory-calibrated, 10 days.** This is the **reference model for factory-calibrated sensors.**
79 G6 traces with YSI sessions on days 1/2, 4 and 10. Values saturated at 40 and 400 mg/dL were
removed before fitting.
- Model: `IGs(t) = (a0 + a1·d + a2·d²)·[BG ∗ (1/τ)e^{−t/τ}](t) + b0` and
  `CGM(t) = IGs(t) + v(t)`, with `v(t) = α1·v(t−T) + α2·v(t−2T) + w(t)`, w ~ N(0, σ²), T = 5 min,
  d = days since insertion.
- BIC selected (poly2, poly0) out of 25 candidates (poly0–3 and an exponential for each of a and b),
  and AR(2) out of AR(1–10).
- Single-step estimates, median [IQR], one parameter set per sensor:

| Parameter | Median [IQR] | Normal-approx SD (IQR/1.349) [derived] |
|---|---|---|
| τ (min) | 3.78 [2.39–5.96] | skewed: use lognormal, μ = ln 3.78, σ ≈ 0.68 [derived] |
| a0 (–) | 0.95 [0.86–1.03] | 0.063 |
| a1 (day⁻¹) | 0.004 [−0.035–0.031] | 0.049 |
| a2 (day⁻²) | 0.000 [−0.003–0.003] | 0.0044 |
| b0 (mg/dL) | 6.35 [2.37–10.51] | 6.0 |
| α1 | 1.30 [1.15–1.37] | 0.16 |
| α2 | −0.42 [−0.53–−0.30] | 0.17 |
| σ (mg/dL) | 3.19 [2.47–3.85] | 1.0 |

  (Two-step estimates are similar: τ 3.10 [1.66–5.91], b0 7.30, α2 −0.46, σ 3.20.)
- Fit RMSE was 3.23 mg/dL (range 1.40–6.56). In the two-step fit, 7 of 79 sensors had τ < 1 min.
- **Simulator warning [derived]:** the paper reports marginals only, with no covariance. If a1 and
  a2 are sampled independently from these spreads, the gain spread at day 10 is
  √((10·0.049)² + (100·0.0044)²) ≈ 0.66. That is far wider than the observed day-10 MARD of
  about 8–9% allows. a1 and a2 must be strongly negatively correlated in reality. Either sample
  from a joint fit, or sample then reject sensors whose |a(d) − 1| over the session exceeds the
  bound implied by the per-day MARD (G7 / Libre 3 per-day tables below). Validate the generated
  population against per-day MARD and the %20/20 by range.
- The authors also note that the low τ (3.8 min, against the Schiavon 2015 equilibration time of
  11 min) reflects G6 processing that compensates part of the physiological delay.

**Later Padova work used here:**
- Facchinetti et al. 2016 (DTT 18:264): disconnection and compression models (§2.6, §2.7).
- Vettoretti et al. 2023 (CMPB 107700): six-state Markov model of G6 gaps (§2.7).
- Camerlingo et al. 2023 (Front Bioeng Biotechnol): colored, non-stationary CGM noise in a Bayesian
  denoiser. Not extracted.
- Cappon et al. 2019 (Diabetes Metab J 43:383): review of technologies.
- The "Zhang & Facchinetti" model named in the brief was **not found**. The nearest
  Facchinetti-group follow-ons are the three items above.

### 2.2 Blood-to-interstitium delay

- **Physiology.** Tracer appearance in ISF takes a mean 5.3–6.2 min in healthy adults
  (Basu 2013, Diabetes) and a median 6.8 min (range 4.8–9.8) in T1D (Basu 2015, JDST).
  Two-compartment "equilibration time" is 9.1 min (healthy) and 11.0 min (T1D) (Schiavon 2015,
  DTT 17:825).
- ISF glucose is a distorted mirror of BG, not a pure shift: the apparent delay depends on the BG
  trajectory (Cobelli 2016, DTT 18:505). A first-order filter reproduces this; a pure time-shift
  does not.
- **Apparent device lag** (physiology plus the device algorithm): G7 3.5 min; G6 3.7 min; Libre 2
  2.4 min; Libre 3 1.8 min; Enlite-era τ 9.4 min.
- **Recommendation.** Use a first-order filter with τ_eff drawn per sensor: Dexcom/Libre current
  generation lognormal with median about 3.8 min, Medtronic about 8–9 min. A separate explicit
  "physiological 6–11 min plus device lead compensation" layer is only needed if the device filter
  is modelled explicitly. The published τ estimates already net the two together.
- **Rate-of-change bias**, which the model must reproduce (Eichenlaub 2025, Table 4, bias vs YSI by
  YSI RoC):

| YSI RoC (mg/dL/min) | FL3 bias | G7 bias | Simplera bias |
|---|---|---|---|
| < −2 | +15.5% | +13.9% | +1.0% |
| −2 to −1 | +11.7% | +12.3% | −0.5% |
| −1 to +1 | +9.9% | +6.8% | −4.5% |
| +1 to +2 | +2.7% | +2.3% | −12.1% |
| > +2 | −2.2% | −0.6% | −19.9% |

  The lag shows up as over-reading on falling glucose. Simplera's lag signature sits on top of a
  negative offset. Note that YSI itself read below the venous lab analyser by 5.2% in that study, so
  the absolute biases depend on the comparator.

### 2.3 Accuracy by glucose range and by wear day

**G7 by day** (Garg 2022, Table 2). Values are MARD (%20/20).

| | Day 1 | Day 2 | Day 4 | Day 7 | Day 10 | Day 10.5 |
|---|---|---|---|---|---|---|
| Arm | 11.9 (87.4) | 8.4 (95.5) | 7.2 (97.2) | 7.2 (97.5) | 7.6 (96.4) | 6.9 (97.4) |
| Abdomen | 12.9 (84.5) | 8.6 (94.9) | 7.7 (96.6) | 8.1 (95.3) | 9.3 (92.9) | 8.8 (93.1) |

**G7 by CGM range** (Garg 2022, Table 3). MAD is shown at ≤80 mg/dL and MARD above.

| | 40–60 | 61–80 | 81–180 | 181–300 | 301–400 |
|---|---|---|---|---|---|
| Arm | MAD 8.5 mg/dL | MAD 6.3 mg/dL | MARD 8.9% | MARD 7.2% | MARD 5.4% |
| Abdomen | MAD 10.3 mg/dL | MAD 7.3 mg/dL | MARD 9.6% | MARD 8.3% | MARD 6.2% |

**Libre 3 by range** (Alva 2023, Table 4):

| Range (mg/dL) | Pairs | Within 15/15% | MAD (mg/dL) or MARD |
|---|---|---|---|
| <54 | 15 | 66.7% | MAD 16.1 |
| 54–69 | 105 | 88.6% | "1.1 mg/dL" as printed, likely a mean difference [check] |
| 70–180 | — | — | MARD 8.4% |
| 181–250 | — | — | MARD 6.3% |
| 250–350 | — | — | MARD 4.9% |

The study induced no glucose excursions, so the hypo range is thin. An independent critique argues
that the pivotal design under-represented lows (about 2–3% of readings below 70 vs about 7% in the
Libre 2 study) [secondary: Diabettech].

**Libre 3 by wear period** (Alva 2023, Table 5). MARD: days 1–3 8.6%, days 7–8 8.7%,
days 9–12 6.4%, days 13–14 7.0%.

**Hypo detection.** A systematic review of 22 studies found average sensitivity for hypoglycaemia
of 85.7% and specificity of 95.3%. No device met ISO 15197 ±15 mg/dL in ≥95% of hypo readings
(Dávila-Ruales 2024).

**Implication for the model.** The calibration polynomial alone does not reproduce the larger
relative error in the hypo range. Absolute error is roughly flat at about 8–16 mg/dL below
80 mg/dL. That is consistent with an additive offset (b0 ≈ 6 mg/dL) plus AR noise with σ ≈ 3, which
is large relative to 55 mg/dL. Keep the additive terms and check the generated MAD in the 40–80 band
against the tables above.

### 2.4 Device sign: Dexcom/Libre read high, Medtronic reads low

In the only same-subject comparison (Eichenlaub 2025, 24 T1D, all three sensors in parallel):
- FL3 and G7 read **high** vs YSI (+8.4%, +7.1%) and close to unbiased vs capillary (−1.1%, −2.5%).
- Simplera reads **low** (−6.0% vs YSI, −14.5% vs capillary).
- Freckmann 2025 (Diabetes Care) shows these offsets move TIR and TBR metrics enough to change
  therapy recommendations.

The sensor model should therefore carry a **per-brand mean offset**, not just zero-mean error. For
t<54 that offset matters as much as the noise.

### 2.5 Cadence, smoothing, quantisation, clamps

- **Dexcom G6/G7.** 5-min values. 40/400 saturation is confirmed for G6 by Vettoretti 2019
  (values outside are shown as LOW/HIGH). G7 can backfill up to 24 h of missed data, so a loop
  sees gaps live that later fill in (Garg 2022). The device output is already filtered: the low
  τ_eff and G4AP's 20% kinetics reduction come from processing.
- **Libre 2/3.** The sensor sends a reading every minute (Alva 2022/2023). Libre 3's "current"
  displayed value and its auto-logged value differ (Witthauer 2025, 24 participants):
  - mean difference −1.2 ± 6.4 mg/dL, lower in hypoglycaemia;
  - |Δ| > 10 mg/dL in about 10% of pairs;
  - MARD 10.1% (current) vs 9.7% (auto-log);
  - display errors (no value shown) in 3.9% of attempts, more often at high glucose and fast
    change.

  Which stream an AID consumes matters. Whether twiist (Libre 3 Plus, 1-min) smooths before Loop
  is **[unverified]**: no public documentation was found.
- **Quantisation** to integer mg/dL is **[unverified]** for all brands. It is harmless to model.
  mmol/L displays round to 0.1.
- **Clamp behaviour.** Below 40 the CGM reports LOW, not a number. The LoopEval field traces' "40
  floor" inflates absolute t<54 (see AGENTS.md traps). The simulator should emit LOW/HIGH flags at
  the clamp rather than a fabricated value, and the controller adapter should treat them the way
  the real app does [unverified per app].

### 2.6 Compression lows (pressure-induced sensor attenuation, PISA)

| Source | Sensor | Duration | Depth | Frequency |
|---|---|---|---|---|
| Mensh 2013 (JDST), 4 non-diabetic adults, 4 sensors each, video of sleep position | Dexcom SEVEN | 30–60 min, up to 90 min; recovery 15–30 min after turning | one example ≈40 mg/dL below the other sensors | Readings >25 mg/dL from the median of the other sensors in 21% of overnight time points (149/694). Left sensors: 32.4% while lying on the left vs 13.4% otherwise. Mostly decreases; rare increases |
| Facchinetti 2016 (DTT 18:264), 72 subjects, 7 days | Dexcom G4 Platinum | median 45 min (5th–95th 30–70) | median 24 mg/dL (10–48) | mostly at night. Modelled as the output of a first-order linear system driven by a rectangular pulse, which gives the observed asymmetric shape |
| Baysal 2014 (JDST), 1125 nights | Medtronic Enlite (Veo) | ends ≥15 min after onset | — | ≈3% of overnight CGM readings (3267 of ≈108,000) labelled PISA |

Derived rate **[derived]**: 3% of overnight readings, with events lasting about 45 min (9 samples)
over a night of about 96 samples, is about 0.3 events per night. Treat that as a starting prior and
calibrate it against donor-pool nights.

Recommended generator: Poisson onset at night (rate about 0.3 per night, posture-dependent),
rectangular "pressure" input of 30–70 min passed through a first-order filter, amplitude
drawn from 10–48 mg/dL (lognormal, median 24), subtracted from IGs. Upward artefacts are rare and
can be omitted. Closed-loop relevance: PISA triggers suspends and then rebound highs (Baysal 2014;
Altnickel 2026 case report).

### 2.7 Gaps and dropouts

- Facchinetti 2016 (G4P): about 90% of disconnections last less than 20 min. They happen more
  often by day, and as often on any of the 7 days. A three-state Markov chain describes a single
  disconnection.
- Vettoretti 2023 (CMPB 107700): a six-state Markov model (2 normal-operation states plus 4 gap
  states) fitted to Dexcom G6 in 167 adults and 205 children. It reproduces the number of gaps per
  sensor, their distribution over wear days and their durations (KS test not significant).
  **Parameter values not extracted [unverified]**. Obtain them from the paper, or fit the same
  structure to the donor pool, which records gaps natively.
- Witthauer 2025: Libre 3 shows no value in 3.9% of attempts, concentrated at high glucose and fast
  change.
- G7 backfill (Garg 2022) means "gap seen by the loop" ≠ "gap in the downloaded record". Model the
  live view.

### 2.8 Warm-up, session end, early failure

- Warm-up times are in table 1.1.
- Day-1 accuracy is worse on every sensor with day-level data: G7 MARD about 12–13% on day 1 vs
  7–9% after. The first-12-h bias is negative (Eichenlaub 2025: −5.9 / −7.8 / −16.9% vs capillary).
  So day 1 needs **both** a gain drop (a0 < 1, a1 > 0 recovers it) and higher variance. The
  Vettoretti poly2 gain can express this.
- Early failure: Simplera 9/49 sensors (all sensor errors), FL3 2/25, G7 0/48 (only 5 days each).
  Large-scale survival curves for G6/G7/Libre were not found in peer-reviewed form. Forum reports
  are anecdotal and were not used. Pending better data, use a hazard of about 2–10% per session,
  with a modest excess on day 1 **[unverified prior]**.

### 2.9 Interference and spurious readings

- Acetaminophen: no interference on G6/G7 at ≤1 g every 6 h. Hydroxyurea reads high
  (Dexcom interference page) [secondary].
- Vitamin C: Libre 2/3 readings may run high above 500 mg/day; Libre 3 Plus above 1000 mg/day
  (Abbott safety information) [secondary].
- Salicylates may lower some Libre readings [secondary].
- A Schiavon et al. 2018 EMBC model of acetaminophen PK and its effect on CGM exists (cited in
  Vettoretti 2019). Not extracted.
- Exercise: FL3 read about 16 mg/dL above YSI during cycling (Cuerda-Del Pino 2025). FL2 had poor
  trend accuracy during exercise (Lundemose 2023). Use these only for an optional exercise
  scenario.

---

## 3. Insulin-delivery device — sections

### 3.1 Silent occlusion and infusion-set failure

- **Base rate.** The best large dataset is Kanapka 2022: 3.3% of sets end early with prolonged
  hyperglycaemia, about 4 per user-year, about 3× higher in teenagers. The hyperglycaemia had run
  >250 mg/dL for about 5 h before the user acted.
- The upper bound for a direct-sensing pump is about 1.8 occlusion alerts per user-month (twiist,
  Ruiz 2026). That is far higher than failures users notice on conventional pumps, which implies
  most partial occlusions on conventional pumps are silent or self-resolving [derived inference].
- Conventional pumps alarm only after pressure builds. At low basal rates that takes hours (bench:
  5–22.5× slower than volume sensing, Butterfield 2024). Air in the reservoir is delivered silently
  by Omnipod, MiniMed and t:slim.
- **Simulator model.** Draw occlusion onset per site, with a hazard that rises with site age
  (§3.2). Delivered fraction steps to 0 (hard) or ramps down (partial). There is no controller
  feedback until either (a) the pump alarms (pressure model: alarm after k·U undelivered,
  k ≈ 1–3 U **[unverified]**), or (b) the simulated user notices hyperglycaemia (Kanapka: about 5 h
  >250). The controller keeps believing the insulin was delivered: phantom IOB is the whole hazard
  for AID.

### 3.2 Absorption change with site age

- **PD speeds up with site age** (Swan 2009): peak 18 min earlier and half-offset 42 min earlier at
  84 h vs 12 h, with total effect unchanged (−11%, ns). Model: compress the insulin action curve's
  time axis by about 0.8 at day 4, interpolated linearly from day 1 [derived].
- **Effectiveness falls late in wear** (Thethi 2010: mean glucose +41 mg/dL from day 2 to 5 without
  a line change; Gorst-Rasmussen 2022: about +13.5 mg/dL by the end of a 3-day wear with faster
  aspart, nothing with aspart). This is insulin- and person-specific.
- **Recommended model:** an effective-insulin multiplier `m(site_age)` = 1.0 for days 0–2, then
  declining to about 0.85–0.9 by day 3–4 (faster aspart) and steeper after day 4. Calibrate the
  slope so glucose drift matches Onset 5 and Thethi. Patel 2014 found no glycaemic worsening in the
  25 sets that survived 7 days, so make the decline a per-person trait, consistent with
  "individual was the strongest predictor".

### 3.3 Glucose disturbance around site and pod changes

- Direct evidence is thin. Onset 5 shows glucose **lower** in the 24 h after a change than in the
  24 h before it (faster aspart), which fits wear-related degradation rather than a post-change
  spike.
- Clinically reported effects at site change are **[unverified]** (no controlled source found):
  - a transient rise in the first hours after insertion (cannula "settling", tissue trauma);
  - lost IOB from a pod or reservoir removed mid-delivery;
  - a prime or cannula-fill dose not counted as IOB.

  Model them only as optional scenario levers, until measured from the donor pool (site-change
  timestamps are in the dose records).
- Change frequency: about 3 days for standard sets (mean wear 2.9–3.2 d in Onset 5 and Pickup
  2014), 6.1 ± 2.3 d with 7-day extended sets in real use (Nieto de la Marca 2026), 3 d (72 h + 8 h
  grace) for Omnipod pods [unverified].

### 3.4 Heat degradation

- Peer-reviewed evidence for clinically relevant potency loss under normal pump use is weak.
  Lispro at 37 °C in pumps for 48 h showed Δ ≤ 4% (Lougheed 1997). Basal pens at 37 °C for 21 d
  showed no loss (Kongmalai 2022).
- Labels cap reservoir use at 6 days (NovoLog, Humalog) and 9 days (Lyumjev in pump), and after
  exposure above 37 °C [secondary].
- Recommendation: no default heat term. Offer a scenario lever (potency multiplier 0.7–0.9 after an
  exposure event **[unverified magnitude]**).

### 3.5 Delivery granularity, pulses, suspends

- **Omnipod.** 0.05 U increments, basal up to 30 U/h, bolus 1.5 U/min (Insulet spec sheet)
  [secondary]. LoopEval's own Tidepool records show temp basals delivering floor(rate·duration /
  0.05) whole pulses. Five-minute re-temps lose the fractional pulse, worth up to −31% of nominal
  at low rates for one donor. The engine's `PumpModel.BasalAccumulator` already models this
  (internal measurement).
- Bolus delivery takes time (about 2 s per 0.05 U pulse at 1.5 U/min [derived]). A 10 U bolus
  takes about 7 min, which matters for "bolus in progress" cycles.
- **Tandem t:slim / Medtronic.** Increments of 0.01 U (t:slim) and 0.025 U (Medtronic) for bolus
  and basal are **[unverified]**. Use each pump's documented increment and round toward delivery
  as the pump does.
- **Flow accuracy.** Bench long-term flow error and short-term CV are reported for Omnipod,
  MiniMed and t:slim at 0.1–1.0 U/h (Butterfield 2024). Values are in figures only and were not
  extracted.
- **Suspends** to model, from LoopEval internal findings on donor data:
  - manual suspends;
  - pump-error windows (Loop logs recommendations, delivers nothing);
  - loop-offline gaps (phone out of range, with no suspend record);
  - pumpless periods (CGM running, no pump).

  The donor pool is the best source for their rates and durations. No literature rate was found.

---

## 4. Recommended sensor model structure

Per simulated sensor session s (brand b), sample a parameter set once. Then, at the device's
internal 1-min clock:

1. **IG**: `IG = h_τs ∗ BG`, first-order with τ_s ~ lognormal(brand median: Dexcom/Libre ≈ 3.8,
   Medtronic ≈ 8.4 min).
2. **Calibration/drift**: `IGs = (a0 + a1·d + a2·d²)·IG + b0 + β_b`, with d = days since insertion.
   Use Vettoretti 2019 marginals with a joint or rejection constraint (§2.1 warning). β_b is a brand
   offset (Eichenlaub 2025: Dexcom/Libre about +7–8% vs YSI, Simplera about −6%). Day-1 behaviour
   comes from the polynomial.
3. **Noise**: AR(2) with α ≈ (1.30, −0.42) and σ ≈ 3.2 mg/dL per 5-min step. Re-identify for a
   1-min cadence before using it there. Optionally use a common-plus-specific split from
   Biagi/Facchinetti for multi-sensor scenarios.
4. **Artefacts**: night-time PISA (Poisson, first-order-filtered rectangular pulse, 24 mg/dL median
   depth, 45 min median duration). Optional interferent offsets as scenario levers.
5. **Availability**: warm-up blanking; Markov gap process (Vettoretti 2023 structure, fitted to the
   donor pool); per-session early-failure hazard; live-vs-backfilled distinction.
6. **Output stage**: brand cadence (5 min Dexcom/Medtronic, 1 min Libre), integer rounding, LOW/HIGH
   flags at 40 and 400 (500 for Libre [unverified]).

**Validate the generated population, not the parameters:**
- per-day MARD (G7/FL3 tables);
- MAD in the 40–80 band;
- bias by rate of change (Eichenlaub table);
- PISA count per night;
- gap-duration distribution against the donor pool.

Breton–Kovatchev (Johnson S_U plus AR(1) 0.7) is kept only as a legacy comparator. It was fitted to
the 2008 Navigator and has no wear-day structure.

---

## 5. References

1. Breton M, Kovatchev B. Analysis, modeling, and simulation of the accuracy of continuous glucose sensors. *J Diabetes Sci Technol* 2008;2(5):853–862. PMC2740661.
2. Facchinetti A, Sparacino G, Cobelli C. Modeling the error of continuous glucose monitoring sensor data: critical aspects discussed through simulation studies. *J Diabetes Sci Technol* 2010;4(1). doi:10.1177/193229681000400102.
3. Facchinetti A, Del Favero S, Sparacino G, Castle JR, Ward WK, Cobelli C. Modeling the glucose sensor error. *IEEE Trans Biomed Eng* 2014;61:620–629. doi:10.1109/TBME.2013.2284023.
4. Facchinetti A, Del Favero S, Sparacino G, Cobelli C. Model of glucose sensor error components: identification and assessment for new Dexcom G4 generation devices. *Med Biol Eng Comput* 2015;53:1259–1269. doi:10.1007/s11517-014-1226-y.
5. Facchinetti A, Del Favero S, Sparacino G, Cobelli C. Modeling transient disconnections and compression artifacts of continuous glucose sensors. *Diabetes Technol Ther* 2016;18:264–272. doi:10.1089/dia.2015.0250.
6. Biagi L, Ramkissoon CM, Facchinetti A, Leal Y, Vehi J. Modeling the error of the Medtronic Paradigm Veo Enlite glucose sensor. *Sensors* 2017;17:1361. doi:10.3390/s17061361.
7. Vettoretti M, Battocchio C, Sparacino G, Facchinetti A. Development of an error model for a factory-calibrated continuous glucose monitoring sensor with 10-day lifetime. *Sensors* 2019;19:5320. doi:10.3390/s19235320.
8. Vettoretti M, Drecogna M, Del Favero S, Facchinetti A, Sparacino G. A Markov model of gap occurrence in continuous glucose monitoring data for realistic in silico clinical trials. *Comput Methods Programs Biomed* 2023;107700. doi:10.1016/j.cmpb.2023.107700.
9. Camerlingo N, Siviero I, Vettoretti M, Sparacino G, Del Favero S, Facchinetti A. Bayesian denoising algorithm dealing with colored, non-stationary noise in CGM timeseries. *Front Bioeng Biotechnol* 2023. doi:10.3389/fbioe.2023.1280233.
10. Cappon G, Vettoretti M, Sparacino G, Facchinetti A. Continuous glucose monitoring sensors for diabetes management: a review of technologies and applications. *Diabetes Metab J* 2019;43:383–397.
11. Basu A, et al. Time lag of glucose from intravascular to interstitial compartment in humans. *Diabetes* 2013. doi:10.2337/db13-1132.
12. Basu A, et al. Time lag of glucose from intravascular to interstitial compartment in type 1 diabetes. *J Diabetes Sci Technol* 2015. doi:10.1177/1932296814554797.
13. Schiavon M, et al. Modeling plasma-to-interstitium glucose kinetics from multitracer plasma and microdialysis data. *Diabetes Technol Ther* 2015;17:825–831. doi:10.1089/dia.2015.0119.
14. Cobelli C, Schiavon M, Dalla Man C, Basu A, Basu R. Interstitial fluid glucose is not just a shifted-in-time but a distorted mirror of blood glucose. *Diabetes Technol Ther* 2016;18:505–511.
15. Wadwa RP, Laffel LM, Shah VN, Garg SK. Accuracy of a factory-calibrated, real-time CGM system during 10 days of use in youth and adults with diabetes. *Diabetes Technol Ther* 2018. PMC6110124.
16. Shah VN, et al. Performance of a factory-calibrated real-time CGM system utilizing an automated sensor applicator. *Diabetes Technol Ther* 2018. doi:10.1089/dia.2018.0143. [secondary]
17. Garg SK, et al. Accuracy and safety of Dexcom G7 continuous glucose monitoring in adults with diabetes. *Diabetes Technol Ther* 2022;24. doi:10.1089/dia.2022.0011. PMC9208857.
18. Alva S, et al. Accuracy of a 14-day factory-calibrated CGM system with advanced algorithm in pediatric and adult population with diabetes (FreeStyle Libre 2). *J Diabetes Sci Technol* 2022. PMC8875061.
19. Alva S, Brazg R, Castorino K, Kipnes M, Liljenquist DR, Liu H. Accuracy of the third generation of a 14-day CGM system (FreeStyle Libre 3). *Diabetes Ther* 2023;14. doi:10.1007/s13300-023-01385-6.
20. Eichenlaub M, et al. Performance of three continuous glucose monitoring systems in adults with type 1 diabetes (FL3, G7, Simplera). *J Diabetes Sci Technol* 2025/2026. doi:10.1177/19322968251315459. PMC11795573.
21. Freckmann G, et al. A comparative analysis of glycemic metrics derived from three CGM systems. *Diabetes Care* 2025. doi:10.2337/dc25-0129.
22. Witthauer L, et al. Discrepancies between current displayed and auto-logged glucose values in FreeStyle Libre 3. *Diabetes Obes Metab* 2025. doi:10.1111/dom.70140.
23. Dávila-Ruales V, et al. Evaluating the precision and reliability of real-time CGM systems: a systematic review. *Ther Adv Endocrinol Metab* 2024. doi:10.1177/20420188241304459.
24. Lundemose SB, et al. Factory-calibrated CGM systems in type 1 diabetes: accuracy during in-clinic exercise and home use. *Sensors* 2023;23:9256.
25. Cuerda-Del Pino A, et al. Accuracy of FreeStyle Libre 3 during moderate-intensity aerobic exercise. *Diabetes Technol Ther* 2025. doi:10.1089/dia.2024.0558.
26. Mensh BD, Wisniewski NA, Neil BM, Burnett DR. Susceptibility of interstitial CGM performance to sleeping position. *J Diabetes Sci Technol* 2013;7(4). PMC3879750.
27. Baysal N, et al. A novel method to detect pressure-induced sensor attenuations (PISA) in an artificial pancreas. *J Diabetes Sci Technol* 2014. PMC4455457.
28. Altnickel N. Caregiver burden and an artifact-associated glycemic instability cycle in pediatric hybrid closed-loop therapy. *Cureus* 2026. doi:10.7759/cureus.106803.
29. Garcia A, et al. Dexcom G4AP: an advanced CGM for the artificial pancreas. *J Diabetes Sci Technol* 2013;7(6).
30. Dexcom. Interfering substances and risks. dexcom.com/interference. [secondary]
31. Abbott. FreeStyle Libre important safety information. freestyle.abbott/us-en/safety-information. [secondary]
32. Diabetes Consumer Guide, Guardian 4 and Eversense 365 product entries; Medtronic MiniMed 780G Guardian 4 training flyer; Eversense 365 FAQ. [secondary]
33. Kanapka LG, Lum JW, Beck RW. Insulin pump infusion set failures associated with prolonged hyperglycemia: frequency and relationship to age and type of infusion set during 22,741 infusion set wears. *Diabetes Technol Ther* 2022;24. doi:10.1089/dia.2021.0548.
34. Patel PJ, et al. Randomized trial of infusion set function: steel versus Teflon. *Diabetes Technol Ther* 2014;16:15–19. PMC3887416.
35. Brazg R, et al. Evaluation of extended infusion set performance in adults with type 1 diabetes: infusion set survival rate and glycemic outcomes from a pivotal trial. *Diabetes Technol Ther* 2022. PMC9353978.
36. Ruiz A, Mcdonough A, Snow K, Bode B, Mitri J. Clinical utility of the twiist automated insulin delivery system: first study with twiist. *BMJ Open Diabetes Res Care* 2026. doi:10.1136/bmjdrc-2026-006307.
37. Butterfield RD, Sims NM. Performance of a CSII pump with acoustic volume and flow sensing in simulated high-consequence situations. *IEEE Open J Eng Med Biol* 2024;5:593–599. PMC11329218.
38. Pickup JC, Yemane N, et al. Nonmetabolic complications of CSII: a patient survey. *Diabetes Technol Ther* 2014. PMC3934434. [secondary]
39. Swan KL, Dziura JD, Steil GM, et al. Effect of age of infusion site and type of rapid-acting analog on pharmacodynamic parameters of insulin boluses in youth with type 1 diabetes receiving insulin pump therapy. *Diabetes Care* 2009;32:240–244. PMC2628686.
40. Thethi TK, et al. Consequences of delayed pump infusion line change in patients with type 1 diabetes treated with CSII. *J Diabetes Complications* 2010;24. PMC2854665.
41. Gorst-Rasmussen A, Sturis J, Ekelund M. CGM sensor glucose levels and insulin pump infusion set wear-time during treatment with fast-acting insulin aspart: a post hoc analysis of onset 5. *Diabetes Technol Ther* 2022;24. PMC8783624.
42. Nieto de la Marca MO, et al. Real-world safety, PROs and glycemic metrics with a 7-day extended infusion set in adults using AID. *Endocrine* 2026. doi:10.1007/s12020-026-04743-z.
43. Lougheed WD, et al. Stability of insulin lispro in insulin infusion systems. *Diabetes Care* 1997;20:1061.
44. Kongmalai T, et al. The effect of high temperature on the stability of basal insulin in a pen. *BMJ Open Diabetes Res Care* 2022. PMC9809263.
45. Insulet. Omnipod product specification sheet (0.05 U increments; bolus 1.5 U/min). [secondary]
46. LoopEval internal: Omnipod pulse truncation in Tidepool basal records and `PumpModel.BasalAccumulator`; suspend, pump-error and loop-offline disruption detection in the ETL.
