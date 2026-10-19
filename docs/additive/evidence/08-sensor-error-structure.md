# 08 — CGM sensor error: structure, scaling with glucose, jumps, on-device processing

Compiled 2026-10-15 for the `additive` role, to sit alongside `docs/additive/evidence/`.

**Evidence labels used throughout**

- **[M] measured.** A number reported in a peer-reviewed paper or an FDA decision summary.
- **[C] computed.** My own arithmetic on [M] numbers, such as an implied MAD from a MARD table, an AR(2) variance, or a Johnson S_U moment. The method is given each time.
- **[P] patent.** Describes what a manufacturer *claims* or *may* do. It does not show what ships in a product.
- **[R] community reverse-engineering or anecdote.** From open-source code (G7SensorKit, xDrip, Juggluco, DiaBLE, simglucose) or blog posts.
- **[I] inferred.** My interpretation. It needs testing.

"Not found" means I searched for it and found no source.

The FDA decision-summary PDFs were downloaded and their text extracted. They are under
`runs/2026-10-15-additive-sensor/fda/` (not tracked) (K213919 = G7, DEN170088 and K200876 = G6, K212132 = Libre 3/2 combined, K193371 = Libre 2).

---

## 1. Structure of CGM error models

### 1.1 The Padova decomposition: lag, then time-varying calibration, then AR noise

**Facchinetti A, Del Favero S, Sparacino G, Castle JR, Ward WK, Cobelli C. "Modeling the glucose sensor error." *IEEE TBME* 2014;61(3):620–629. doi:10.1109/TBME.2013.2284023.**
- [M] The model has three parts: blood-to-interstitium diffusion, a linear time-varying calibration and drift term, and an autoregressive model for the *additive* measurement noise. It was identified from 36 datasets, each with n = 4 simultaneous Dexcom SEVEN Plus sensors plus frequent blood-glucose references (abstract).
- The AR order and parameter values were not retrievable. Only the abstract is open.

**Facchinetti A et al. "Model of glucose sensor error components: identification and assessment for new Dexcom G4 generation devices." *Med Biol Eng Comput* 2015;53(12):1259–69. doi:10.1007/s11517-014-1226-y.**
- [M] MARD was 11.1% for the G4 Platinum, 10.0% for the G4AP and 14.2% for the SEVEN Plus. Each error component was about 30% smaller in the G4 Platinum than in the SEVEN Plus.
- [M] Day-4 G4AP parameters as reused for priors in Battocchio's Padova thesis (below): τ mean 7.7 (SD 3) min, gain a0 1.05 (SD 0.15), offset b0 −2.6 (SD 14.9) mg/dL.

**Vettoretti M, Battocchio C, Sparacino G, Facchinetti A. "Development of an error model for a factory-calibrated CGM sensor with 10-day lifetime." *Sensors* 2019;19(23):5320. doi:10.3390/s19235320.** This is the Dexcom G6 model and the source of the current simulator structure.
- [M] Model: CGM(t) = (a0 + a1·t + a2·t²)·(BG ⊗ h)(t) + b0 + v(t), with h(t) = e^(−t/τ)/τ and t in days.
- [M] Noise is v(t) = α1·v(t−5) + α2·v(t−10) + w, where w is white Gaussian with constant SD σ.
- [M] Data: 79 G6 traces after exclusions (from 177 traces in 141 adults). Readings of 40 and 400 were removed. YSI was assumed to have a 2% CV.
- [M] Table 1, medians [IQR] from the single-step fit:

  | Parameter | Median [IQR] |
  |---|---|
  | τ | 3.78 [2.39–5.96] min |
  | a0 | 0.95 [0.86–1.03] |
  | a1 | 0.004/day |
  | a2 | 0.000/day² |
  | b0 | 6.35 [2.37–10.51] mg/dL |
  | α1 | 1.30 [1.15–1.37] |
  | α2 | −0.42 [−0.53 to −0.30] |
  | σ | 3.19 [2.47–3.85] mg/dL |

- [M] The noise is **additive with constant σ**. The paper **did not test** whether σ depends on glucose level. It did not report residual non-Gaussianity either.
- [C] Implied properties of this AR(2): the roots are 0.70 and 0.60, the marginal SD is 8.7 mg/dL, the lag-1 autocorrelation is 0.915, and the SD of the 5-min first difference is 3.6 mg/dL. Most of the marginal "noise" is slow, so the 5-min jumps are governed almost entirely by the innovation w.
- [M] The thesis behind the paper (Battocchio C, Univ. Padova, `thesis.unipd.it/…/Tesi_Cristina.pdf`, Table 4.7) gives the **innovation variance by wear day** (median, with 5th–95th percentile):

  | Wear day | σ² median (5th–95th) | σ |
  |---|---|---|
  | 1–2 | 10.27 (1.60–46.6) mg²/dL² | ≈3.2 mg/dL |
  | 4 | 7.03 (2.44–21.8) | ≈2.65 mg/dL |
  | 10 | 7.57 (2.10–63.7) | ≈2.75 mg/dL |

  The thesis says "σ̂ is greater in the first and in the last day". The between-sensor spread is wide and right-skewed: the 95th-percentile σ is about 6.8–8 mg/dL.

**Vettoretti M, Del Favero S, Sparacino G, Facchinetti A. "Modeling the error of factory-calibrated CGM sensors: application to Dexcom G6 sensor data." EMBC 2019. doi:10.1109/EMBC.2019.8856790.**
- [M] 11 subjects wore 2 parallel sensors each. The calibration error over the 10-day life is "well represented by … 2nd-order polynomials in time".

**Biagi L, Ramkissoon CM, Facchinetti A, Leal Y, Vehi J. "Modeling the error of the Medtronic Paradigm Veo Enlite glucose sensor." *Sensors* 2017;17(6):1361. doi:10.3390/s17061361.**
- [M] τ mean 9.4 ± 6.5 min (median 8.4, 5th–95th 0.3–23.4). a0 median 1.1. b0 median −0.5 mg/dL, with a 5th–95th range of −90.7 to 36.1.
- [M] The noise is split in two:
  - a component **common** to both sensors in a person, cc = 1.584·cc(−1) − 0.8842·cc(−2) + 0.1798·cc(−3) + w, with var(w) = 3.98;
  - a **sensor-specific** component, ssc = 1.367·ssc(−1) − 0.4816·ssc(−2) + w, with var(w) = 2.54 mg²/dL².
- [M] Anderson–Darling normality tests passed for only 86.5% (common) and 67.6% (sensor-specific) of series. **That is non-Gaussianity in one-third of the sensor-specific series.**
- [M] MARD by range: <70 = 16.6%, 70–180 = 12.6%, >180 = 9.6%. By component, calibration error accounts for 11.3% MARD, noise 4.2% and BG-IG kinetics 3.6%.

### 1.2 The UVA family: lag plus Johnson S_U-transformed AR noise, additive and then multiplicative

**Breton M, Kovatchev B. "Analysis, modeling, and simulation of the accuracy of continuous glucose sensors." *J Diabetes Sci Technol* 2008;2(5):853–862. PMC2740661.**
- [M] FreeStyle Navigator, about 20,600 sensor–reference pairs.
- [M] Noise: e_n = 0.7·(e_{n−1} + υ_n), with υ ~ N(0,1), on a **15-min** grid. The error is ε = ξ + λ·sinh((e − γ)/δ).
- [M] Johnson S_U parameters: λ = 15.96, ξ = −5.471, δ = 1.6898, γ = −0.5444. The PACF cuts off after lag 1, and the ACF stays non-zero "up to several hours".
- [M] Error: mean 0.76 mg/dL, SD 11 mg/dL, non-normal. A χ² test showed no difference between simulated and observed error (p > .46). The error is **additive**.
- [M] Spread of the sensor/reference pairs **increases with reference level**. Sensors read low above 200 and high below 110.
- [M] Mean discrepancy is linear in rate of change (R² = 0.995), consistent with about 17 min of total delay.
- [C] The marginal error implied by the published parameters (stationary e, var 0.96) has SD 11.7 mg/dL, skew +0.76 and **excess kurtosis +3.2**, with 1st/99th percentiles at −25 and +36 mg/dL. The heavy tail and right skew are therefore in the most-used simulator noise model. That model includes calibration error and is sampled every 15 min, so it is *total* error, not 5-min jitter.

**Breton MD, Hinzmann R, Campos-Nañez E, Riddle S, Schoemaker M, Schmelzeisen-Redeker G. "Analysis of the accuracy and performance of a CGM sensor prototype: an in-silico study using the UVA/Padova T1D simulator." *J Diabetes Sci Technol* 2017;11(3):545–552. doi:10.1177/1932296816680633.**
- [M] Error model: CGM = ((α·t + β)·BG(t − τ) + γ)·ε(t). This is **explicitly multiplicative**: "associated with a multiplicative error term". ε is a Johnson-transformed Gaussian ARMA, which was selected as AR(1) with PACF about 0.6.
- [M] τ = 4.5 / 12.1 / 11.4 min and β = 0.97 / 0.72 / 0.99 for three systems (Roche prototype, CGM-1, CGM-2). The paper does not label which values belong to which system, so this ordering is inferred.

### 1.3 Other model families

**Lunn DJ, Wei C, Hovorka R. "Fitting dynamic models with forcing functions: application to CGM in insulin therapy." *Stat Med* 2011;30(18):2234–50. doi:10.1002/sim.4254. PMC3201840.**
- [M] Bayesian hierarchical model on the mmol/L scale with **additive** residuals. Logs apply only to parameters, not to observations.
- [M] Calibration shift B and scale F are **step-changed at each 6-hourly calibration**. Population F ≈ 0.82 and B ≈ 1.6 mmol/L.
- [M] AR(1) residual, with ρ fixed at 0.8 because the posterior ran to 1; the two-stage fit gave 0.925. Residual SD is about 0.12 mmol/L, roughly 2.1 mg/dL. Lag is about 16–17 min.

**Zhou T, Dickson JL, Chase JG. "Autoregressive modeling of drift and random error to characterize a continuous intravascular glucose monitoring sensor." *J Diabetes Sci Technol* 2018;12(1):90–104. doi:10.1177/1932296817719089.** This is an intravascular device, not a subcutaneous one.
- [M] Errors are modeled as **fractional (relative)** errors.
- [M] Drift is AR(2) on a 30-min grid: γ = 0.9698, β = −0.0715.
- [M] Fluctuation is AR(2) on a 15-s grid: γ = 1.261, β = −0.261.
- [M] The model assumes **constant percentage error**, so the absolute error grows with BG. Recalibration resets the state.

**Rodbard D. "Characterizing accuracy and precision of glucose sensors and meters." *J Diabetes Sci Technol* 2014;8(5):980–985. doi:10.1177/1932296814541810.**
- [M] For synthetic data it uses a **mixed proportional + additive** form: 10% proportional Gaussian error plus 5.0 mg/dL additive Gaussian error plus a level-dependent bias.
- This is a methods paper. The parameters are illustrative, not fitted.

**Laguna/Bondia/Vehí** (Laguna AJ, Rossetti P, Ampudia-Blasco FJ, Vehí J, Bondia J, early-to-mid 2010s, SEVEN Plus and Enlite):
- The paper itself was not retrieved. Biagi 2017 summarizes it as modeling lag, stationarity, error distribution and time correlation.
- The parameters were not found.

**"Zhang & others":** I found no CGM *error* model by a Zhang. No 2021–2026 deep-learning or generative CGM-error simulator turned up in my searches (not found).

### 1.4 Error SD versus glucose level: FDA iCGM data

Tables below are from the FDA decision summaries for adults on the labeled site. Mean bias is CGM minus comparator. ARD by range is expressed as MAD for the ranges below 70.

**Dexcom G7 (K213919, adult arm, Study 1, N = 308, comparator = YSI)**

| Comparator range (mg/dL) | Pairs | %15/15 | %20/20 | Bias (mg/dL) | MARD |
|---|---|---|---|---|---|
| <54 | 732 | 91.0 | 93.7 | +4.0 | 14.0% |
| 54–69 | 4,530 | 92.0 | 97.0 | +1.1 | 10.7% |
| 70–180 | 17,910 | 84.6 | 92.6 | +1.1 | 8.6% |
| 181–250 | 5,905 | 89.9 | 95.0 | −1.9 | 7.4% |
| >250 | 10,116 | 92.8 | 97.1 | −6.6 | 6.4% |

Binned by **iCGM** value instead, the <54 bin has bias **−9.3** and MARD 16.0%, and 54–69 has −2.3 and 9.1%. That is a regression-to-the-mean signature: when the CGM reads low, it is usually reading too low.

Pediatric arm (7–17 y): iCGM <54 bias **−17.7**, MARD 24.1%.

**FreeStyle Libre 3/2 combined (K212132, adults n = 200)**

| Comparator range (mg/dL) | Bias (mg/dL) | MARD |
|---|---|---|
| <54 | +7.4 | 15.5% |
| 54–69 | +1.4 | 10.3% |
| 70–180 | −4.5 | 9.7% |
| 181–250 | −7.3 | 7.5% |
| >250 | −11.5 | 6.9% |

By iCGM range: <54 has bias −6.7 and MARD 14.2%.

**Dexcom G6 (DEN170088, adults n = 159, binned by iCGM)**

| iCGM range (mg/dL) | Bias (mg/dL) | MARD |
|---|---|---|
| <54 | −6.9 | 13.8% |
| 54–69 | −0.5 | 11.5% |
| 70–180 | −2.8 | 10.9% |
| 181–250 | −10.0 | 9.3% |
| >250 | −3.8 | 7.1% |

The K200876 reprocessing, with the "optimized joint probability" algorithm, is nearly identical.

**[C] Implied mean absolute difference (MAD = MARD × range midpoint).** Midpoints used: 62, 125, 215 and 310 mg/dL.

| Device | MAD at 62 / 125 / 215 / 310 (mg/dL) | Elasticity d ln MAD / d ln G |
|---|---|---|
| G7 | 6.6 / 10.8 / 15.9 / 19.8 | 0.69 |
| Libre 3 | 6.4 / 12.1 / 16.1 / 21.4 | 0.73 |
| G6 | 7.1 / 13.6 / 20.0 / 22.0 | 0.72 |

- A pure additive error has an elasticity of 0 and a pure multiplicative (log-normal) error has 1.
- **Total CGM error versus YSI scales with glucose at about the 0.7 power.** It is mostly multiplicative above about 100 mg/dL, with a floor of roughly 6–7 mg/dL MAD in the 54–100 range.
- A mixed fit, MAD = √(a² + (b·G)²), gives:
  - G7: a ≈ 6.8 mg/dL, b ≈ 6.2%. As Gaussian-equivalent SD, that is about 8.5 mg/dL ⊕ 7.7%.
  - Libre 3: a ≈ 7.1 mg/dL, b ≈ 6.6%.
  - The fit over-predicts the 54–69 bin slightly.
- **Caveat:** this is *total* error (lag + calibration + noise), measured at 15-min reference intervals in clinic. It cannot be split into gain error versus noise.

**FDA precision (two sensors on the same subject and site) [M].** Because the physiology is shared, this approximates the sensor-specific error.

| Device | PARD | PAD | CV |
|---|---|---|---|
| G7 adults (K213919) | 8.9% | 13.8 mg/dL | 6.3% |
| G6 adults abdomen (K200876) | 9.0% | 14.2 mg/dL | 8.2% |
| Libre 3 adults (K212132, table) | 6.8% | 10.3 mg/dL | 4.8% |

- The Libre 3 text gives a second figure, PARD 5.9% with CV 4.2%.
- [C] If two sensors' errors are independent, each sensor's sensor-specific MARD is about PARD/√2: **≈6.3% for G7**. That is about 70% of G7's total MARD of 8.2–8.9%. Most G7 error is sensor-specific, not shared physiology.

**Other head-to-head data [M]**
- **Garg SK et al., *Diabetes Technol Ther* 2022;24(6):373–380, doi:10.1089/dia.2022.0011** (G7 pivotal paper):
  - arm MAD 8.5 mg/dL at 40–60 and 6.3 at 61–80;
  - MARD 8.9% at 81–180, 7.2% at 181–300, 5.4% at 301–400.
- **Eichenlaub M et al., *J Diabetes Sci Technol* 2026;20(4):1131–40, doi:10.1177/19322968251315459** (FL3 vs DG7 vs Simplera, 24 adults, YSI):
  - MARD 11.6 / 12.0 / 11.6%;
  - relative bias **+8.4% / +7.1% / −6.0%**.
- **Freckmann G et al., *Diabetes Care* 2025;48(7):1213–17, doi:10.2337/dc25-0129**, same participants over 14 days:
  - FL3 and DG7 read **14.2% and 11.2% higher than Simplera** on average;
  - median <54 events per 14 days: FL3 0, DG7 3, Simplera 3.
  - **Systematic between-device differences are proportional, not additive.**

### 1.5 Bottom line on additive versus multiplicative

- [M] The four Padova models (Facchinetti 2014/2015, Vettoretti 2019, Biagi 2017) and Lunn 2011 put the *noise* term in additive mg/dL with constant σ. Their multiplicative part is the **calibration gain** a(t).
- [M] Breton 2017, Zhou 2018 and the Tidepool iCGM generator (§6) put the error in a multiplicative or percentage form.
- [M] Breton 2008 observed that the spread grows with level. No paper I found tested σ_noise against glucose directly (not found).
- [I] Regulatory data show total-error elasticity of about 0.7. In a Vettoretti-type model, the multiplicative gain with IQR 0.86–1.03 already supplies much of that. Whether the **5-min innovation** also scales with G cannot be settled from the literature. It has to be measured on donor CGM data, for example 5-min-difference SD in quiet windows binned by level.

---

## 2. Time-varying bias: drift, sensitivity change, sudden recovery, steps

- **Calibration polynomial [M].**
  - G6 (Vettoretti 2019): a1 and a2 are near 0 at the median (a1 IQR −0.035 to +0.031/day). Drift is per-sensor and roughly symmetric about zero.
  - Enlite: a1 median −0.0005/min.
- **Day-1 deficit [M].**

  | Device / source | Day 1 | Later |
  |---|---|---|
  | G7 (Garg 2022) | MARD 11.9% (arm), 12.9% (abdomen) | 8.4% day 2; 7.2% day 4 |
  | G7 (FDA) | MARD 9.9% at beginning (%15/15 82.2%) | 7.1% middle (92.2%) |
  | G6 (FDA) | MARD 10.7% at beginning (%15/15 77.6%) | 9.2% middle |
  | Libre 3 (FDA) | MARD 9.6% on days 1–3 | 8.4% on days 7–8 |
  | G4AP (Garcia 2013) | 14.7% | 9.4% day 4 |

  - Hanson 2024 (Abbott-funded, contested): G7 MARD was worse in hours 12–24 (15.1%) than in hours 0–12.
- **"Dip and recover" [P].** This is a day-1 sensitivity attenuation, attributed to insertion trauma or local vasospasm. It appears "within the first day … most often in the first 12 hours, and normally resolves within 6–8 hours" (e.g., US 10,881,339 / 12,629,066 "Use of sensor redundancy to detect sensor failures"). US 11,259,842 (needle design) reports a "substantial reduction" of the failure mode. No frequency is given (not found).
- **Factory-calibrated sensitivity profile [P].**
  - Dexcom US 11,974,845 (Ma, Bhavaraju): sensitivity follows a single or dual exponential from m0 to mF with rate mR, "greatest in the first few days". The baseline has a break-in term B1(t) plus a physiological negative-bias term B2(t).
  - Dexcom US 10,335,075 "Advanced calibration": a priori distributions of sensitivity and baseline are updated to a Bayesian posterior using real-time inputs.
  - Dexcom US 12,383,173: drift is compensated from impedance and temperature.
  - The G6 510(k) K200876 lists "Optimized Joint Probability Algorithm", "Optimized Noise Management" and "Progressive Sensor Decline (PSD) detection".
  - [I] These describe a *continuous* correction of sensitivity, not discrete jumps. No document I found says whether such corrections produce visible steps (not found).
- **Calibration steps (calibrated sensors) [M].** Lunn 2011 models a discrete step in gain and offset at each calibration. Zhou 2018 resets the error state at calibration. Dexcom's consumer FAQ warns that "frequent calibrations … may cause exaggerated jumps and drops" (dexcom.com FAQ). How the G7 applies an optional calibration (a step or a ramp) is documented only by anecdote [R] (not found in primary sources).
- **Bias that suddenly recovers.** The best-documented example is the **pressure-induced sensor attenuation (PISA)** (§4): a negative bias with a fast onset, about 45 min long, that recovers when the pressure is released.
  - [M] Mensh 2013 found that most aberrations of more than 25 mg/dL from the median of 4 sensors coincided with lying on the sensor. "In rare cases" they were elevated values.
  - Other step or recovery processes (e.g., a bias relaxing after an algorithm sensitivity update) have **no published rate or amplitude** (not found).
- **Regime switching and time-varying noise [M].** Facchinetti, Sparacino & Cobelli, *IEEE TBME* 2011;58(9):2664–71 (doi:10.1109/TBME.2011.2161083) shows that SNR varies **within** a subject over time, not only between subjects. Their real-time filter re-estimates the noise variance continuously. A Senseonics patent (US 10,765,373) re-estimates its KF variances every 144 min on 6 h of data [P]. Together these argue for a slowly varying σ_noise per sensor rather than a fixed σ.
- **Long, large errors [M].** Garcia 2013 counted "level 3" errors lasting more than 1 h for the G4 and G4AP: 58 vs 62 min.

---

## 3. On-device signal processing

### 3.1 Dexcom

- **G4AP / "505" algorithm [M].** Garcia A et al., *J Diabetes Sci Technol* 2013;7(6):1436–45 (doi:10.1177/193229681300700604) describes it as a Dexcom–Padova "smart CGM" denoising and calibration layer (refs: Padova Kalman filtering).
  - MARD fell from 13.2% to 11.7%.
  - In a fast rise, the G4AP **led the G4 by more than 5 min**, i.e., less filter delay.
  - The paper gives no equations.
- **Bailey 2015, *J Diabetes Sci Technol* 9(2):209–14 [M].** The 505 algorithm on the G4: MARD 9.0%; lag 5–6 min; day 1/4/7 MARD 10.7/8.0/8.5%.
- **Padova Kalman denoiser [M].** Facchinetti, Sparacino & Cobelli, *IEEE TBME* 2010;57(3):634–41 (doi:10.1109/TBME.2009.2033264). It is self-tuning to the individual SNR. For comparable smoothing it adds about **35% less delay than a moving average**, which the paper calls "currently in use in likely all commercial CGM devices".
- **Artifact-replacement patent family [P].** US 7,935,057 "Systems and methods for replacing signal artifacts" (Dexcom; Goode, Brauker, Kamath et al.):
  - Raw counts are sampled every **30 s**.
  - The IIR filter passes cycles of 40 min. Its cutoff switches from a 30-min cycle normally to 60 min during artifacts, and a longer cycle means more lag.
  - **"Cone of Possibility"** physiological plausibility limits:
    - maximal sustained rate about **4–5 mg/dL/min**;
    - maximal acceleration about **0.1–0.2 mg/dL/min²**;
    - centreline projected from the previous 4 points;
    - **capped at 20 mg/dL per 5 min**;
    - the cone widens each 5 min for up to 30 min and is then re-seeded;
    - a change of more than **30 mg/dL in one 5-min interval** is a special case, after which the next accepted point may come 20–30 min later.
  - After multi-point data loss, the filter takes **about 25–40 min to recover**.
  - Reference matching assumes about 10 min of filter delay plus about 5 min of physiological delay.
  - [I] This is the clearest published mechanism for "not trusting a rise, then catching up". A step beyond the cone is held or replaced, and the trace snaps back once the new level has persisted. It is patent text from the SEVEN/G4 era. No source confirms it in the G6 or G7.
- **G7 wire format [R].** LoopKit/G7SensorKit, `G7GlucoseMessage.swift` and `AlgorithmState.swift`:
  - Each 5-min message carries `glucose`, a separate **`predicted`** glucose, `trend` (0.1 mg/dL/min resolution), `age` (seconds from reading to transmission) and a display-only flag.
  - Algorithm states include `excessNoise` (3), `temporarySensorIssue` (18) and `sensorFailedDueToProgressiveSensorDecline` (19).
  - Backfill messages carry glucose, state and trend only.
  - [I] The separate predicted value shows the sensor runs a forward model on board.
  - Whether backfilled or stored history values are revised relative to the live values was **not found** in any source. Garg 2022 states only that "up to 24 h of missing data can be requested".
- **G7 lag [M].** 3.5 min (SE 0.13), from Garg 2022: the lag minimizing MARD after interpolating CGM to 1 min.
- **G7 versus G6 roughness [R].** Heller D, Gluroo blog, 2023-09-20, one person wearing both:
  - one G7 run read 131, 115, 106, 115, 117, 98, 94, 89 while the G6 read 137 → 118 monotonically;
  - "G7 trends often reversed about 30 minutes after appearing to start".
  - This is an anecdote, but it is consistent with the trend data below.

### 3.2 Abbott (Libre 2/3)

- [M] The FDA K212132 summary says the Libre 3 provides glucose "every minute", and that "the real-time glucose measurements and glucose arrows are calculated by the Sensor software".
- **Two streams [R].** DiaBLE discussion #22 (gui-dos) and the Juggluco FAQ:
  - a 1-min real-time "clinical" stream (about the last 120 values retrievable);
  - 5-min historical values with a **latency of about 17 min** (Juggluco says at least 20 min).
  - [I] The latency implies the history stream is retrospectively processed (smoothed or centred). No source documents its exact filter (not found).
- **Libre 2 1-min data [R].** Diabettech, 2023-11-14, "A close up view of Libre CGM data via Diabox" reports "many microspikes", which the official app does not show. xDrip's patched-Libre source applies about a 25-min weighted average (a commenter's claim). AAPS documentation advises 10–25 min of smoothing for Libre 2.
- **Lag-compensation patents [P].**
  - US 9,462,970 "Methods of lag-compensation for analyte measurements" (Abbott; Budiman, Li):
    - G_comp = y(k) + a1/(N1)·[y(k) − y(k−N1)] + a2/(N2)·[y(k) − y(k−N2)], with N1 and N2 of about 1–45 min, fitted offline on population data.
    - A **primary (fast) bank and a delayed secondary bank** run in parallel. A noise metric is formed from the moving average of their difference. The weight on the fast bank → 0 when that metric is large, sharpened by an exponent such as P = 4.
    - A third, more smoothed bank is the fallback.
    - [I] This is a second documented "distrust a transient, then catch up" mechanism. A sudden step makes the banks disagree, the output follows the slow bank, and it returns to the fast bank once the step persists. Released product behavior is unconfirmed.
  - US 9,907,492 / 11,896,371 / 12,343,140 (Budiman): **the amount of lag correction depends on recent glycemic variability**, set from the distribution of rates of change. Variability and range set the trade-off between correction and noise amplification.
- **Libre lag [M].** Alva S et al., *J Diabetes Sci Technol* 2020/2022, Libre 2: 2.4 ± 4.6 min in adults, against 4.5 ± 4.8 min for Libre 1.

### 3.3 Medtronic

- [M] Bequette BW, *J Diabetes Sci Technol* 2010;4(2):404–18 (doi:10.1177/193229681000400222), citing Medtronic CGMS patents:
  - 10-s raw samples become 1-min values by **dropping the highest and lowest of 6 and averaging 4**;
  - 5-min values drop the highest and lowest of five 1-min values and average 3.
  - A trimmed mean like this acts as **spike rejection**, similar to a median.
  - Rate-of-change "clipping limits" are described generically.
  - A 5-sample moving average has about 2.5 samples of delay.
  - Keenan et al. put physiological lag at 3–12 min and electrochemical lag at 1–2 min.
- Guardian 4 / Simplera on-device algorithm: EIS-based diagnostics are mentioned only in vendor patent-landscape blogs. **No primary detail found.**
- [M] Simplera's rate-dependent bias is strongly **asymmetric** (Eichenlaub 2026, Table 4, relative bias versus YSI rate of change):

  | YSI rate of change (mg/dL/min) | FL3 | DG7 | Simplera |
  |---|---|---|---|
  | <−2 | +15.5% | +13.9% | +1.0% |
  | ≥−1 to ≤+1 | +9.9% | +6.8% | −4.5% |
  | >+2 | −2.2% | −0.6% | −19.9% |

  - [C] Relative to each device's flat-glucose bias:
    - DG7 is roughly symmetric: +7.1% on falls, −7.4% on rises;
    - FL3: +5.6% on falls, −12.1% on rises;
    - Simplera: **+5.5% on falls, −15.4% on rises**. It lags rises much more than falls.

### 3.4 Delay versus filtering, and rate attenuation in the FDA trend tables

- [M] Schmelzeisen-Redeker G et al., *J Diabetes Sci Technol* 2015;9(5):1006–15 (doi:10.1177/1932296815590154):
  - raw-signal delay of a Roche prototype: 9.5 ± 3.7 min (median 9), and patient-specific;
  - prediction reduced it by about 4 min (9.5 → 5.9 min);
  - total technological delay in commercial systems is reported as "3 to 12 minutes";
  - delay is reported to be "**longer during phases of rising rather than … declining BG**".
- [M] Basu A et al., *Diabetes* 2013;62(12):4083–7 (doi:10.2337/db13-1132): physiological plasma-to-ISF delay of **5.3–6.2 min**, measured with tracer.
- [M] Pleus S et al., *J Diabetes Sci Technol* 2015;9(4):801–7: for Dexcom G4, MARD rose from 12.6%/11.3% in slow falls and rises (±1 mg/dL/min) to **24.9% at < −3 and 29.6% at ≥ +3 mg/dL/min**.
- [C] **Rate attenuation from the FDA concurrence tables.** I recomputed the tables column-wise, giving the CGM rate distribution for a given comparator rate. Rates are per pair, from points about 15 min apart.

  | When comparator rate is… | Device | CGM shows the same bin | CGM shows the opposite or flat side |
  |---|---|---|---|
  | **< −2** mg/dL/min | G6 | 56.2% | 1.5% at ≥0 |
  | | G7 | 34.5% | 11.4% at ≥0 |
  | | Libre 3 | 31.8% | 14.6% at ≥0 |
  | **> +2** mg/dL/min | G6 | 71.8% | 6.7% at ≤0 |
  | | G7 | 58.8% | 14.6% at ≤+1 |
  | | Libre 3 | **36.1%** | **42.7% at ≤+1** |

  - [I] G7 and Libre 3 report fast swings with a *smaller* slope than G6 does, and Libre 3 sharply attenuates fast rises. Two explanations fit: stronger smoothing or rate-limiting in the newer algorithms, or more per-reading noise scrambling the rate.
  - [I] The counts cannot separate these. They are a quantitative **validation target**: the simulator's sensor model, run on true-BG rates, should reproduce these concurrence matrices per device.

---

## 4. Spikes, dropouts, PISA, noise flags and artifact rates

| Artifact | Evidence | Numbers |
|---|---|---|
| PISA / compression (G4P) | [M] Facchinetti A et al., *Diabetes Technol Ther* 2016;18(4):264–72 (doi:10.1089/dia.2015.0250), 72 subjects | Duration median **45 (5th–95th 30–70) min**; amplitude **24 (10–48) mg/dL**; mostly at night; equally likely on all 7 days. Shape: first-order lag G(s) = −P/(1 + τs) driven by a rectangle of duration D, so A_max = P(1 − e^(−D/τ)); τ is about ⅓ of the recovery time. |
| PISA rate (G6) | [M] Idi E et al., *IEEE JBHI* 2025;29(2):1383–96 (doi:10.1109/JBHI.2024.3465893), 72 dual-sensor G6 traces manually labelled | **0.33 PISA/day** (real). The in-silico generator draws episodes/subject ~N(3,3) truncated to [1,10] over 10 days, about 0.42/day. |
| PISA rate | [M] Lobo B, *J Diabetes Sci Technol* 2026 (doi:10.1177/19322968261469536) | 846 PISAs in 59,122 h, **≈0.34/day** [C]; 325 in 26,890 h, ≈0.29/day [C] |
| PISA share | [M] Baysal N et al., *J Diabetes Sci Technol* 2014;8(6):1091–6 | About **3% of overnight readings** labelled PISA (1,125 nights) |
| Sleeping position | [M] Mensh BD et al., *J Diabetes Sci Technol* 2013;7(4):863–70 | Aberrations of more than 25 mg/dL from the 4-sensor median correlate with lying on the sensor; mostly falls, rarely rises |
| Disconnections (G4P) | [M] Facchinetti 2016 | About **90% last less than 20 min**; mostly daytime; 3-state Markov model |
| Gaps (G6) | [M] Vettoretti M et al., *Comput Methods Programs Biomed* 2023;240:107700 (doi:10.1016/j.cmpb.2023.107700); Drecogna M et al., EMBC 2021 | 6-state Markov model (2 normal + 4 gap states) on 167 adults and 205 children. Gap counts and durations not in the abstract (not retrieved). |
| Data availability | [M] FDA | G7 99.4% overall, falling from 99.5% on day 1 to 98.1% on day 10 (clinic, Study 1). Libre 3 capture 99.5–100% per day. |
| Early sensor shutoff | [M] FDA | G7: 14.3% of 460 sensors; 79% lasted to day 10. G6: 9.6% early shutoff; 84% lasted to day 10. Libre 3: 87.2% raw, 94.4% corrected survival to day 14. |
| LOW readings | [M] K213919 | When G7 read "LOW" (<40), the comparator was <55 in only 33% and <70 in 78% of 298 pairs. A LOW reading is mostly an over-reading of a real low. |
| Noise flags | [R] G7SensorKit; AAPS docs | G7 reports `excessNoise` and `temporarySensorIssue` algorithm states. xDrip native mode exports noise levels, and AAPS suppresses SMBs when noise is high. No published flag rates (not found). |
| Isolated spikes or jumps on factory-calibrated sensors | — | **No published rate per day found**, nor the rate of ≥12 mg/dL 5-min steps in quiet windows. |

---

## 5. Noise characteristics that matter on a 5-min grid

- **Autocorrelation [M].**
  - G6 AR(2) (1.30, −0.42), roots 0.70 / 0.60 [C].
  - Enlite: sensor-specific AR(2) (1.367, −0.482) plus a common AR(3).
  - Navigator: AR(1) 0.7 at 15 min.
  - Lunn: AR(1) ρ about 0.8–0.93 at 5 min.
  - In the G6 thesis, AR order 2 was BIC-selected in most segments on days 1–2, 4 and 10 (Battocchio Fig. 4.15).
- **Heavy tails and skew.**
  - [M] Breton 2008 calls the error non-normal. [C] Its Johnson S_U implies excess kurtosis of about +3.2 and skew of about +0.8 in total error.
  - [M] Biagi 2017: one-third of sensor-specific noise series fail Anderson–Darling.
  - [C] An AR(2) with σ = 3.19 and Gaussian innovations gives P(|Δ5min| ≥ 12 mg/dL) from noise alone of about **0.8 per 1,000**. With t(df 4) innovations at the same SD it gives about **7.3 per 1,000** (1M-step simulation).
  - [I] The gap between the simulated 22 and the real 54 per 1,000 in quiet windows is therefore unlikely to close by tail shape alone at G6-sized σ. A larger G7 per-step σ, or a separate jump/recovery process, is needed.
- **Heteroscedasticity.**
  - [M] Total error elasticity is about 0.7 (§1.4). Breton 2008: the spread grows with level.
  - [M] Within-sensor σ varies over time (Facchinetti 2011). Between sensors the spread is wide: the G6 innovation variance runs from 1.6 to 46.6 mg²/dL² (5th–95th, days 1–2).
  - The level-dependence of the 5-min innovation itself was **not found**.
- **Rate-of-change dependence [M].**
  - G7 MARD by rate (Garg 2022, arm): 9.3% (< −2), 8.1–7.8% (−1..+1), 9.7% (> +2).
  - G4: 24.9–29.6% at ±3 (Pleus 2015).
  - Bias is lag-like: positive on falls, negative on rises (Breton 2008; Eichenlaub 2026).
- **Asymmetry, rises versus falls [M].** The delay is longer during rises (Schmelzeisen-Redeker 2015, citing reports). Simplera shows much larger rise bias than fall bias (§3.3). [C] DG7 is nearly symmetric. FL3 is about 2× worse on rises.
- **Sensor day [M].** Accuracy is worst on day 1 (§2). The G6 innovation σ² is about 46% higher on days 1–2 than on day 4 (10.3 vs 7.0), and also higher on day 10. **Noise, not only gain, has a day effect.**
- **Device differences [M].** G7 sensor-specific error (PARD 8.9%) is larger than Libre 3's (6.8%) and similar to G6's (9.0%). [R] G7 looks rougher than G6 at 5 min (Heller). [C] G7's trend concurrence is worse than G6's (§3.4).

---

## 6. Simulators and how they parameterize sensor noise

| Simulator | Sensor model | Source |
|---|---|---|
| UVA/Padova S2008 | Breton–Kovatchev: lag + Johnson-S_U-transformed AR(1). Navigator, Guardian RT and Dexcom STS 7-day; additive. | Kovatchev BP et al., *J Diabetes Sci Technol* 2009;3(1):44–55 [M] |
| UVA/Padova S2013 | Same CGM model family (sensor model not changed in Dalla Man 2014 per abstract) | Dalla Man C et al., *J Diabetes Sci Technol* 2014 [M] |
| UVA/Padova S2017 ("single day") | **Dexcom G5**: first-order BG→IG; **linear** time-varying calibration error; **additive AR(2)** noise; parameters drawn **per virtual sensor from day-specific multivariate pdfs** (76 subjects × 7 days). Values not published in the paper. | Visentin R et al., *J Diabetes Sci Technol* 2018;12(2):273–81, doi:10.1177/1932296818757747 [M] |
| simglucose (Python) | `sensor_params.csv`: Dexcom, GuardianRT and Navigator all share **PACF 0.7, γ = −0.5444, λ = 15.9574, δ = 1.6898, ξ = −5.47**, i.e., Breton 2008 for every sensor. They differ only in sample_time (3/5/1 min); min 39 (Navigator 32), max 600. Noise is generated every 15 min, **cubic-interpolated** to the sample grid, **added** to subcutaneous glucose, glucose-independent, then clamped. No lag beyond the patient's Gsub. | github.com/jxx123/simglucose (`sensor/noise_gen.py`, `cgm.py`) [R] |
| Tidepool data-science-simulator | `NoisySensor`: `int(np.random.normal(true_bg, 5.0))`, a placeholder i.i.d. 5 mg/dL | github.com/tidepool-org/data-science-simulator `models/sensor.py` [R] |
| Tidepool iCGM sensitivity analysis | Per-sensor initial bias ~ Johnson S_U; default **`bias_type="percentage_of_value"` (multiplicative)**; drift multiplier none/linear/random within e.g. [0.95, 1.05]; Gaussian noise "noise_coefficient"; **delay 5 min (G6, citing Vettoretti 2019) or 10 min**. Parameters searched so that simulated sensor batches pass the iCGM special controls. | github.com/tidepool-org/icgm-sensitivity-analysis (`src/simulator_functions.py`, branch jameno/DATA-194) [R] |
| Breton 2017 Roche prototype | Multiplicative Johnson-transformed ARMA, τ = 4.5 min | §1.2 [M] |
| Lunn 2011 | Additive AR(1) ρ 0.8, calibration steps | §1.3 [M] |
| Padova fault models | PISA (first-order + rectangle); Markov disconnections; 6-state Markov gaps | Facchinetti 2016; Vettoretti 2023 [M] |

---

## Implications for the simulator

These are concrete, evidence-tied changes. Where a number is not in the literature, the recommendation says to measure it on the BDDP/eda donor data. Inventing it would break the "evidence for every component" rule.

### A. Additive versus multiplicative: move the *total* error toward elasticity ≈ 0.7 and keep a floor

- **Evidence.**
  - FDA MAD by range gives elasticity 0.69 (G7), 0.73 (Libre 3) and 0.72 (G6) [C §1.4].
  - Mixed fits: G7 ≈ 6.8 mg/dL ⊕ 6.2% MAD, i.e., about 8.5 mg/dL ⊕ 7.7% SD-equivalent.
  - Between-device offsets are proportional (Freckmann 2025: +11–14%).
  - Breton 2017 and Tidepool use multiplicative error.
- **The current model already has multiplicative structure in the gain** a0 + a1·d + a2·d² (G6 a0 IQR 0.86–1.03), plus a noise scale of 0.6 + 0.4·IG/130. That scale has an elasticity of only 0.4 at 130 mg/dL. **Don't add more multiplicative structure by intuition. Check the composite first.**
  - Run the sensor model on synthetic true-BG.
  - Compute MARD, MAD, bias and %15/15 per FDA range, binned both by true value and by sensor value.
  - Compare with the G7 adult tables above. Both binnings matter. The **iCGM-binned <54 bias of −9.3 mg/dL** and the comparator-binned +4.0 mg/dL are a sharp test of tail and selection behavior near the low end, which is where t<54 is decided.
- **If the composite elasticity falls short of about 0.7, the change the evidence favours** is to put the innovation in log space with an additive floor:
  - ε_t = AR(2) in **ln(IG)** units, with σ_log ≈ cv_noise;
  - plus an independent additive term σ_add for the low end.
  - Equivalently, keep it additive with σ(G) = √(σ_add² + (cv·G)²).
  - Fit cv and σ_add so the composite matches the FDA tables **and** the 5-min-difference SD by level in quiet windows of the BDDP G7 data. The latter is a measurement eda can make. The literature has no level-resolved 5-min-noise curve.
- The user's "glucose is lognormal" intuition is **consistent with the regulatory data above about 100 mg/dL**. It is **not** consistent below about 70, where MAD is flat at about 6–7 mg/dL rather than shrinking proportionally.

### B. Per-sensor and per-day σ, not one σ

- **Evidence:**
  - G6 innovation variance by day has median 10.3 / 7.0 / 7.6 on days 1–2 / 4 / 10, with a 5th–95th of about 2–47 [M Battocchio].
  - SNR varies within a subject over time [M Facchinetti 2011].
  - G7 PARD (8.9%) > Libre 3 (6.8%) [M].
- **Recommendation:**
  - Draw σ per sensor from a log-normal fitted to that spread.
  - Multiply it by a day factor of about 1.2 in SD (√(10.3/7.0)) on days 1–2 and at end of life, so the day-1 deficit is not carried by the gain alone.
  - Optionally let σ follow a slow log-random-walk within a sensor.
  - **The G7 σ should not be the G6 value of 3.19.** Lesson 29's 4.5 is in the direction the G7 evidence points: rougher than G6 by anecdote [R] and by trend concurrence [C].

### C. Replace "more t-tail" with an explicit jump-and-recovery (transient-bias) process

- **Evidence that tails alone are not enough.**
  - [C] At G6 σ, t(df 4) innovations give only about 7 per 1,000 |Δ| ≥ 12 from noise, against the 32 per 1,000 that are missing.
  - Every documented large-step mechanism is a **transient bias with structured onset and recovery**, not an i.i.d. outlier:
    - PISA: about 0.3/day, 45 min long, 24 mg/dL deep, first-order shape, nocturnal [M];
    - dip-and-recover on day 1: resolves in 6–8 h [P];
    - Mensh's rare *elevated* aberrations [M].
- **Recommendation.** Add a marked point process of transient biases, b(t) = Σ A_k·g(t − t_k).
  - Use the Facchinetti 2016 kernel: a rectangle of duration D through a first-order filter with τ.
  - Allow both signs.
  - For the negative, compression class, use the published parameters: 0.33/day, mainly at night; D gives a 30–70 min episode; amplitude 10–48 mg/dL.
  - For **short daytime transients of either sign**, the literature has **no rate or amplitude** (not found). Estimate them from the BDDP G7 quiet windows with the same kernel. Fit the rate, the amplitude distribution and τ_recovery to:
    - the count of |Δ| ≥ 12 steps (54 per 1,000);
    - the fraction followed by a reversal within 1–3 steps;
    - the fraction followed by persistence.
  - This tests the user's two hypotheses separately:
    - a "bias suddenly recovering" event produces a **reversal pair** (big step, then an opposite step);
    - a "catch-up" (C below) produces a **run of under-trend steps followed by one big same-sign step**.

### D. Rise-suppression and catch-up filter: plausible, documented in patents, unconfirmed in product

- **Evidence.**
  - [P] Dexcom's Cone of Possibility: rate limit 4–5 mg/dL/min, acceleration 0.1–0.2 mg/dL/min², ≤20 mg/dL per 5 min, a 30 mg/dL/5-min special rule, a cone widening for up to 30 min, and 25–40 min recovery after data loss.
  - [P] Abbott's dual-bank weighting suppresses the fast bank when it disagrees with a delayed bank (power-4 weighting).
  - [P] Abbott's variability-dependent lag correction.
  - [C] G7 and Libre 3 attenuate fast rates in the FDA trend tables. Libre 3 shows a slope of ≤ +1 for 42.7% of comparator rises faster than 2 mg/dL/min.
  - [M] Delay is longer on rises (Schmelzeisen-Redeker 2015). Simplera's rise bias is −15% net against +5.5% on falls.
- **Recommendation: implement as an optional, switchable sensor-algorithm stage** after noise and before rounding:
  - (1) the output follows a lag-compensated estimate when consecutive innovations are consistent;
  - (2) a step that exceeds a plausibility bound gets reduced weight, and the output moves only part of the way;
  - (3) once the new level persists for k samples, the weight recovers and the output catches up.
- **Parameter sources:**
  - the bound is the Dexcom cone (≤20 mg/dL per 5 min; rate 4–5 mg/dL/min);
  - the suppression weight w = 1/(1 + (disagreement/K)^4) follows Abbott's P = 4;
  - the persistence k (1–6 samples, from the 30-min cone horizon) and K are **free and must be fit to BDDP data**, not tuned to a single statistic.
- **Validation targets:** the FDA trend-concurrence matrices per device (§3.4), the run/step signature in C, and the per-device rate-bias asymmetry (§3.3).
- Keep it **off for G6**: its concurrence is the least attenuated. Give it **device-specific settings for G7 and Libre 3**.

### E. Lag

- **Evidence:**
  - τ 3.8 min (G6, Vettoretti) [M];
  - G7 3.5 min effective lag [M];
  - Libre 2 2.4 min [M];
  - physiological lag 5–6 min [M Basu];
  - raw delay about 9.5 min, before prediction [M].
- **Recommendation:** the current lognormal τ ≈ 3.8 min is right for the *displayed* signal of current devices. Do not add the 5–6 min physiological delay on top, because commercial outputs are already lag-compensated (Abbott patents, G7 `predicted` field, Schmelzeisen-Redeker's 4-min reduction).
- If D is implemented, its lag compensation should replace part of τ rather than add to it.

### F. Low-end and failure details

- **Clamps:** G7 and G6 report 40–400, with LOW/HIGH outside. Libre 3 reports 40–400 in FDA testing; Eichenlaub lists 40–500.
- **LOW readings:** keep 39/401 as LOW/HIGH codes. Validate that when the simulator emits LOW, true BG is <55 in about 33% and <70 in about 78% of cases (G7 FDA).
- **Gaps:** use the Vettoretti 2023 6-state Markov structure. Disconnections are about 90% <20 min (G4P). Availability is about 99.4% per day (G7 clinic); real-world loss is larger and should be measured from BDDP.
- **Sensor end:**
  - G7 14% early shutoff and 79% survival to day 10 [M];
  - G6 84% to day 10 [M];
  - treat a sensor session ending as a gap and a re-warmup, with day-1 noise and gain restarting.

### G. What remains "not found" and must come from donor data

- The level dependence of the 5-min innovation σ.
- The rate, amplitude and recovery-time distribution of daytime transient jumps.
- Whether G7/Libre history values are revised relative to live values.
- The actual shipped G7 smoothing or plausibility logic.
- Medtronic Guardian 4 / Simplera on-device processing.
- Per-day rates of noise flags (`excessNoise`).

Each needs an eda measurement on BDDP CGM data, split by sensor family (eda lesson 33). The literature above supplies the structure and the validation tables, not these parameters.

## Body vs co-located sensor error at the 5–15 min scale (LESSONS 298–299)

- The donors' fast coherent CGM moves cannot be assigned to body or sensor from CGM alone; one donor's two simultaneous
  sensors (p03) share 69–75% of them, as simulated G7 pairs share 81% — body plus co-located interstitial error.
- Separating the two needs a CGM-vs-reference (YSI / venous) time series with frequent sampling. Searched 2026-10-19:
  no public raw dataset found; FDA submissions (e.g. PRECISION / PRECISE II tables, https://fda.gov/media/112139/download)
  and trial SAPs (e.g. NCT03710083) give per-range agreement summaries only; a Zenodo hypoglycaemia error-grid repository
  (https://zenodo.org/records/6979569) pairs CGM with SMBG, not a lab reference. Open: access to a manufacturer or
  academic in-clinic dataset.
