# MiniMed 780G and Control-IQ: how they handle meals nobody announces

Verified 2026-10-25. Board: TIDEPOOL-95. Labels: **[pub]** peer-reviewed or FDA; **[mfr]** manufacturer labeling;
**[pat]** Medtronic patent embodiment (matches the labeling, not confirmed as shipped code); **[3rd]** clinician fact sheet
or trade press; **[inf]** inference. Grosman 2024 (Medtronic's algorithm paper) and the Santova 2026 full text are paywalled;
the abstracts, FDA documents, patents and citing reviews were used instead.

## Side by side

| | MiniMed 780G (AHCL 4.3 / 5.3) | Control-IQ / Control-IQ+ | CamAPS FX (hybrid) / Liberty |
|---|---|---|---|
| Controller | PID with insulin feedback for basal [pub]; automatic correction logic from DreaMed [pub]; 5 min | UVA MPC on a 30-min prediction [pub]; 5 min | Adaptive MPC; 8–12 min |
| Automatic bolus fires when | SG > 120 **and** auto-basal is at its maximum (Umax) [mfr, 3rd] | 30-min predicted glucose > 180 [pub] | Never in hybrid mode; Liberty: none described |
| Its size | (SG − 120) / (1800 / TDD) − bolus IOB, then the safety scaler; skipped if < 10 % of Umax [pat] | 60 % of a correction to 110 with the user's correction factor, minus IOB [pub] | — (temp basal / extended bolus) |
| How often | Every 5 min | At most hourly; 60 min after any bolus [mfr] | — |
| Targets | 100 / 110 / 120; temp target 150, no corrections there [pub] | Basal range 112.5–160; Sleep 112.5–120 with no automatic bolus [pub] | Default 104, personal 80–198 |
| Meal detection | Yes: the slope over the last 3–7 readings; on detection the safety scaler's low threshold drops from 80 to 50 mg/dL, so less of the correction is removed [pat, pub Edd 2026]; real thresholds undisclosed | None in the product [pub] | None published |
| Adaptation | Daily at midnight from TDD (Umax, correction ISF); user cannot set basal or ISF [pub, 3rd] | User settings; TDI's later role undisclosed (sources conflict) | Daily, diurnal, post-meal |

**780G safety scaler** [pub Edd 2026 citing Grosman 2024; pat]: a 2-h glucose prediction is checked, and the correction is
stepped down 100 / 75 / 50 / 25 / 0 % until the prediction stays above the low threshold. Meal detection acts only on that
threshold. The correction formula itself is unchanged. A 2021 patent (US11806137B2) describes a learned detector (SG plus
modelled plasma insulin normalised by TDD, logistic regression or LSTM) that lowers the correction target or ISF on
detection; it is not known to be in the product.

**780G 5.3 (April 2025)** changed how automatic corrections and daily adaptation are calculated. The FDA called it "more
aggressive … through increased basal delivery rate and automated bolusing doses," with an increased risk of hypoglycaemia
[pub, P160017/S118].

## Outcomes with unannounced meals

| Study | Design | Result |
|---|---|---|
| Santova 2026 [pub, abstract] | 43 children; 30 / 50 g with no bolus; 4 h | Time > 250: 780G 5.0 / 21 %, Control-IQ 9.9 / 26 %, CamAPS 26 / 42 %. 30-g rise AUC 137 / 144 / 156 |
| CRUMB, Lo Presti 2026 [pub] | 20 adolescents; 30 g unannounced; 780G vs Control-IQ | 2-h rise 55.6 vs 87.3 mg/dL (p < 0.001); 4-h rise equal (both back to baseline). Time < 70 overall 0.6 vs 2.3 % |
| 780G pivotal, S091 [pub] | Dinner with no bolus; mean SG rise to 2 h | Ages 7–17: manual mode +115, AHCL +51–52. Adults: +78 vs +61–63 mg/dL |
| Shalit 2023 [pub] | 14 adults, 90 days unannounced vs 90 announced | TIR 67.5 vs 77.7 %; > 250 7.9 vs 3.6 %; < 54 0.3 vs 0.7 %. Up to 20 g unannounced made no TIR difference |
| Grassi 2026 [pub] | 32 people, 60 g, 4-h TIR | Pre-meal bolus 85.5 %, no bolus 52.3 %, half bolus at +60 min 63.5 % |
| Niu 2026 [pub, Medtronic] | Real world, 369,467 users | 54,553 had ≥ 10 days without a user bolus: TIR 70.9 %, < 54 0.2 %; on 100 target + 2 h active insulin time 76.3 %, automatic corrections 17.9 U/day |
| Polin 2024 [pub abstract, Tandem] | Real world, 291,769 Control-IQ users | 9.9 % went ≥ 7 days without a bolus; TIR 62 % on those days vs 57–60 % on bolus days; < 70 under 0.6 % |
| Laugesen 2024 [pub] | 141 Control-IQ, 48 780G | Each missed or late bolus per day cost 9.7 TIR points |

## Research systems aimed at no announcement (UVA and Tandem)

- **RocketAP** (Garcia-Tirado 2021 [pub]): adolescents, unannounced dinner; 6-h TIR 83 vs 53 % for the older UVA
  controller, with no time below range and less insulin.
- **Bolus priming** (Corbett 2022 [pub], in silico): a logistic model on the last 30 min of CGM (level, slope,
  acceleration) plus a Kalman disturbance estimate. Priming bolus 0 / 4 / 7 / 10 % of TDI at probability < 0.2 / 0.2–0.3 /
  0.3–0.4 / ≥ 0.4, minus the IOB of earlier primes.
- **Meal anticipation** (Garcia-Tirado 2023 [pub]): 5-h post-breakfast TIR HCL 75 %, FCL 58 %, FCL with anticipation
  63 %; anticipation not significant.
- **FCL@Home / AIDANET** (Moscoso-Vasquez 2026 [pub], n = 34): neural-net basal, priming boluses on meal-like patterns,
  aggressiveness adapted from recent time below and above range. TIR 57.9 → 63.6 %, < 54 0.3 → 0.2 %; most of the gain
  overnight.
- **Tandem Freedom** (Wilkinson 2025 [pub abstract], n = 10, 72 h, no meal boluses): TIR 61.0 vs 56.3 % on home
  Control-IQ with boluses (n.s.). Algorithm embargoed.
- **Medtronic Vivera** [3rd]: fully closed loop with optional announcement; US pivotal enrolled, launch aimed at H2 2027;
  no published description.

## Reading

- On missed meals the published order is 780G, then Control-IQ, then CamAPS. It follows how much correction insulin each
  system may give into a rise and how often: full correction every 5 min, 60 % hourly, none [inf; Lo Presti attribute
  the 780G–Control-IQ gap to the 60 % hourly rule]. The 780G's meal detector loosens its own hypo guard rather than
  enlarging the dose.
- Loop already auto-boluses a fraction of the correction every 5 min, so structurally it is nearest the 780G. Its
  application factor and guard (now guard + runway) are the levers the 780G turns on detection.
- No system's detector internals are public. The only quantitative detector is UVA's priming design (Corbett 2022).

## LoopEval candidates this suggests

1. **Rise-gated guard loosening (780G):** while a sustained rise is detected, relax the low threshold the dose is checked
   against. Dose formula unchanged. Scored on t<54 and IOB-at-crossing-54.
2. **Priming as a forecast term (UVA):** on a high-probability disturbance from CGM shape, add a phantom carb effect sized
   as a fraction of TDI, net of earlier primes. TDI only sizes it; the trigger is CGM shape.
3. **Reference arms:** "60 % to 110, hourly" (Control-IQ) and "100 % to 120 every 5 min, gated on max basal" (780G) on the
   same donors, which places Loop's application factor on a known curve.
4. **Overnight:** no automatic bolus and a tight basal range (Control-IQ Sleep).

Already scored and not repeated: rise projection C05–C07 (WORSE or patient-conditional), calm-high licence C23/C25 and
target shift C31 (IMPROVES in gated forms), guard + runway (frozen, landing in Loop).

## References

FDA: P160017/S091, S118, S124, S125 (780G); DEN190034, K200467 (Control-IQ). Patents: US10894126B2, US11806137B2, EP4420693.
Grosman 2024 DTT 26(S3):17 doi:10.1089/dia.2023.0446 · Grosman 2016 JDST doi:10.1177/1932296816631568 · Edd 2026 DOM
doi:10.1111/dom.70310 · Niu 2026 Diabetes Care doi:10.2337/dc25-2124 · Shalit 2023 DTT doi:10.1089/dia.2023.0139 · Tornese 2022
Diabetes Care doi:10.2337/dc21-2643 · Grassi 2026 DTT doi:10.1177/15209156251395010 · Petrovski 2023 Diabetes Care
doi:10.2337/dc22-1692 · Santova 2026 DTT doi:10.1177/15209156251415187 · Lo Presti 2026 Endocrine doi:10.1007/s12020-026-04705-5
· Laugesen 2024 DTT doi:10.1089/dia.2024.0022 · Breton & Kovatchev 2021 DTT doi:10.1089/dia.2021.0097 · Shah 2026 DOM
doi:10.1111/dom.70500 · Polin 2024 doi:10.33590/emj/OUZU9513 · Garcia-Tirado 2021 Diabetes Care doi:10.2337/dc21-0932 · Corbett
2022 JDST doi:10.1177/19322968211059159 · Garcia-Tirado 2023 Diabetes Care doi:10.2337/dc23-0119 · Moscoso-Vasquez 2026 Diabetes
Care doi:10.2337/dc25-1526 · Wilkinson 2025 JDST doi:10.1177/19322968251389966.

Unverified: Control-IQ "6 U per automatic bolus" (AGDT sheet only); how Control-IQ uses TDI after setup; the 780G
detector's thresholds; Santova's per-system TIR, lows and insulin.
