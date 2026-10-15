# 06 — Insulin pump delivery: from what the controller commands to what reaches the tissue

The simulator needs a model of the gap between the insulin the controller **commands** and the
insulin that **reaches the subcutaneous depot**. That gap comes from the mechanism (quantization,
flow noise, start-up transients), the environment (pressure and temperature), and the fluid path and
site (occlusion, kinking, bubbles, leakage, lipohypertrophy). The controller sees none of it. Loop
and oref build IOB from the commanded or pump-reported dose, so any non-delivery becomes **phantom
IOB**. That is the AID-specific hazard: the controller holds back insulin it believes is already
working.

Written 2026-10-15. This file complements `03-sensor-and-device.md` §3 (site age, heat, granularity),
which it does not repeat. `05-loopeval-findings.md` has the donor-pool measurements (site change and
site failure, Omnipod pulse truncation).

**Labels.** **[V]** = checked this session against the full text or the manufacturer document.
**[A]** = abstract or search snippet only. **[unverified]** = not checked against the source.
**[derived]** = my arithmetic on the cited numbers. **[03]** = taken from `03-sensor-and-device.md`
and not re-checked here.

---

## Summary table

| # | Issue | Proposed model form | Magnitude | Frequency | Key refs |
|---|---|---|---|---|---|
| 1 | Quantization / pulse schedule | Deliver whole pulses on the pump's schedule; carry the remainder (or drop it, as Omnipod temps do) | Omnipod 0.05 U pulse; 780G 0.025 U stroke; t:slim basal every 5 min | Every step | Omnipod 5 TUG [V]; 780G TG [V]; t:slim UG [V]; [03] |
| 2 | Short-window flow noise (basal) | Multiplicative AR(1) error on delivered volume, τ ≈ 30–60 min, sd by pump and rate; long-run bias ≈ 0 | 1-h sd: durable pumps 3–6% at 1 U/h; Omnipod 10–13% at 1 U/h, ~22% at 0.1 U/h. 72-h total within ±2% | Continuous | Freckmann 2019 [V]; Ziegler 2021 [V]; Mende 2022 [V]; Butterfield 2024 [V] |
| 3 | Small-bolus error | Per-bolus multiplicative error, sd shrinking with size | 0.05 U: 5–95% range ≈ 25–175%. 1 U: sd 2–4% (durable) vs 12–14% (Omnipod). ≥2.5 U: within ±5% in ≥94% | Every bolus | Omnipod 5 TUG, t:slim UG, 780G TG [V]; Freckmann 2019 [V] |
| 4 | Start-up transient (stiction, compliance, priming) after a new reservoir/pod | Additive deviation that decays over hours; sign and size are per-device draws | 780G 1 U/h: first hour −11% (median), 6 h −3%. Freckmann 2019 first 12 h: +0.1 to +9.9% (mean), back to ±1% at 12–72 h | Every reservoir/pod change | 780G TG [V]; Freckmann 2019 [V] |
| 5 | Pressure change (flight, altitude) | Bubble-driven displacement ∝ fill volume × ΔP: extra delivery on ascent, deficit on descent | 0.6–1.4 U extra on ascent (~0.6% of cartridge per 200 mmHg); 0.5–0.9 U deficit on descent | Per flight; mountain drives | King 2011 [V]; Fan/King EASD 2024 [A]; t:slim UG [V] |
| 6 | Temperature change → bubbles | Bubble nucleation event → later missed volume (see 8) | Bubbles form 4 → 37 °C; volume not quantified | Fridge-cold insulin, heat | Lopez 2014 [V] |
| 7 | Complete occlusion | Delivered = 0 from onset. Alarm when missed volume ≥ V_alarm (pump trait, 2–4.5 U). Optional release bolus if it clears | Latency = V_alarm / rate: ~3 h at 1 U/h, 20–35 h at 0.1 U/h, 7+ days at 0.025 U/h | ~3.3% of sets end with prolonged hyperglycaemia (≈4/yr); higher in youth | Mfr tables [V]; Ziegler 2021 [V]; Kanapka 2022 [A] |
| 8 | Partial / silent occlusion, kinked cannula | Delivered fraction f ∈ (0,1) for a duration; no alarm unless f is near 0 | Not quantified on bench; glucose +9 → +32 mg/dL over 6–12 h before an early change (donor data) | Silent occlusion events in 36–50% of standard-set wears (pressure-monitored study); kink at insertion 0.5–15% | Klonoff 2017 (Gibney) [V-secondary]; Brazg 2022 [V]; Patel 2014 [A]; eda L52 |
| 9 | Air bubble in tubing | Missed volume = bubble volume, delivered as a block once the pump pushes the bubble through | ≈1.3 U per 10 cm of tubing [derived]; review estimate "10 cm ≈ 1 U". Durable pumps and Omnipod deliver air with no alarm | Common (self-report); no per-wear rate | Heinemann & Krinelke 2012 [V]; Accu-Chek Insight Flex IFU [A]; Butterfield 2024 [V] |
| 10 | Release bolus after an occlusion clears | One-shot extra delivery ≤ missed volume | 780G mean 1.12 U; t:slim < 3 U (at 2 U/h); bench 0.04–0.68 U at 0.5 U/h | Each spontaneously clearing occlusion | 780G TG [V]; t:slim UG [V]; Borot 2014 [V] |
| 11 | Site leakage / backflow | Fraction of each bolus lost, rising with bolus size | **No quantitative source found** | Named in reviews; no rate | Heinemann & Krinelke 2012 [V] |
| 12 | Dislodgement / pull-out | Delivered to tissue = 0 from event until the user notices | Same as a complete occlusion, but the pump never alarms | 7.3% of 7-day sets; 10% of 3-day sets in a benchmark | Zhang 2022 [V]; Brazg 2022 [V] |
| 13 | Lipohypertrophic site | Per-site bioavailability ≈ 0.75–0.8 and higher variability | Cmax −25%, AUC −22% [derived]; postprandial glucose +26% | 26% of pump users self-report LH; 42% in a paediatric exam | Famulla 2016 [A]; Pickup 2014 [A]; Heinemann 2012 (Conwell) [V] |
| 14 | Site/pod change mechanics | Gap with no delivery; prime and cannula fill not delivered to tissue; new-site effects | Omnipod: 2.6 U prime + 0.5 U cannula-insertion bolus. Tubing prime 9–17 U. Gap of minutes [unverified] | Every 2–3 days (pods 72 h + 8 h) | OmniBLE `Pod.swift` [V]; Accu-Chek IFU [A]; eda L52 |
| 15 | Insulin degradation in reservoir | Potency multiplier and occlusion hazard that grow with wear time and temperature | No potency loss in 48 h at 37 °C; bench occlusion 0% before 48 h, 9–41% by day 5 (by analog) | Late wear, heat | Lougheed 1997 [03]; Kerr 2008 [A] |

---

## 1. Delivery accuracy at small volumes

### 1.1 How it is tested: IEC 60601-2-24 trumpet curves

- IEC 60601-2-24 uses a microgravimetric balance. The trumpet curve plots the maximum and minimum
  deviation within averaging windows of 15, 60, 150, 330, 570 and 930 min **[V, Kamecke 2018]**.
- The standard excludes the first 24 h as stabilization. Kamecke et al. argue this is clinically
  unrealistic because sets are changed every 48–72 h. Trumpet curves show only extremes, and longer
  windows make every pump look better. They propose 1-h windows over the whole run, with ±5% and
  ±15% markers **[V]**.
- At low rates, short windows contain only one or two pulses, so window error is mostly
  quantization **[V, Kamecke 2018]**. A simulator that delivers whole pulses already reproduces
  most short-window error at 0.05–0.1 U/h.
- Manufacturer label claims are **long-window** figures: ±5% for basal and ±5% for bolus ≥1 U
  (Omnipod; ±0.05 U below 1 U); 780G ±5% at 1 U/h, ±10% at 0.025 U/h, ±20% for boluses <0.1 U;
  t:slim ±5% **[V, manufacturer guides]**. They say nothing about 1-h behaviour.
- The cited studies "Jahn 2010" and "Zisser 2010" could not be found. The related papers are Zisser
  2011 (*JDST* 5:1509, optical Omnipod bolus method) and Jahn 2013 (*JDST* 7:1011, gravimetric
  durable vs patch). Neither was opened, so their numbers are not reported here. Borot 2014 appeared
  in *J Diabetes Sci Technol*, not *Diabetes Technol Ther*.

### 1.2 Basal delivery, per-window

**Freckmann 2019 (Ifdt Ulm; 1.0 U/h, 72 h, 9 runs; n = 693 1-h windows per pump) [V]**

| Pump | 1-h within ±5% | ±10% | ±15% | 0–12 h total | 12–72 h total |
|---|---|---|---|---|---|
| Accu-Chek Insight (2 sets) | 89–95% | 97–98% | 98% | +0.1 to +0.6% | −0.1 to +1.1% |
| Accu-Chek Spirit Combo (2 sets) | 81–95% | 92–99% | 94–99% | +3.0 to +3.7% | −1.3 to −0.3% |
| Animas Vibe | 85% | 96% | 98% | +4.7% | −0.9% |
| MiniMed 640G | 84% | 93% | 96% | **+9.9%** (6.5–13.0) | −0.9% |
| Paradigm Veo (3 sets) | 90–94% | 97–99% | 98–100% | +1.7 to +2.9% | −0.5 to +0.1% |
| Omnipod (Eros) | **47%** | 71% | 81% | +5.0% | +0.6% |

- Mean of all 1-h windows was within ±2% for every system. Omnipod showed large 1-h deviations in
  four of nine runs **[V]**.

**Low-rate and patch pumps**

| Pump | Rate | 1-h mean dev. | 1-h sd | 1-h within ±15% | Source |
|---|---|---|---|---|---|
| Accu-Chek Solo | 0.1 U/h | −5.3% | 25.0% | 51% | Ziegler 2021 [V] |
| Medtrum A6 | 0.1 U/h | +4.8% | 28.4% | 48% | Ziegler 2021 [V] |
| Omnipod Eros | 0.1 U/h | — | — | — (MARD 27.4%) | Ziegler 2021 [V] |
| Accu-Chek Solo | 1 U/h | −1.9% | 5.4% | 98% | Ziegler 2021 [V] |
| Medtrum A6 | 1 U/h | +3.4% | 17.0% | 60% | Ziegler 2021 [V] |
| Omnipod Eros | 1 U/h | — | — | — (MARD 8.2%) | Ziegler 2021 [V] |
| Omnipod DASH | 0.1 U/h | +7.9% | 21.7% | 52.7% | Mende 2022 [V] |
| Omnipod DASH | 1 U/h | +1.2% | 10.0% | 86.2% | Mende 2022 [V] |
| MiniMed 670G | 0.1 U/h | +10.6% | — | ~59% | ATTD 2020 abstract (Ziegler et al.) [A] |
| t:slim X2 | 0.1 U/h | +2.2% | — | ~63% | ATTD 2020 [A] |
| mylife YpsoPump | 0.1 U/h | +4.2% | — | ~67% | ATTD 2020 [A] |

- The **Butterfield 2024** bench comparison (twiist "ND" vs MiniMed 600/700, t:slim X2 and Omnipod;
  0.1/0.3/1.0 U/h; 557–1,649 h per pump) reported the following **[V]**:
  - Only ND kept every long-term error within ±5%.
  - The worst over-infusion was +21.4% (Omnipod, 0.1 U/h); the worst under-infusion was −10%
    (MiniMed, 0.1 U/h).
  - Short-term variability (pharmacokinetic CV with a 60-min half-life) at 0.1 U/h was about 7%
    for MiniMed, t:slim and ND, and 15% for Omnipod.
  - Per-pump values at each rate are in figures only.
- The twiist's per-pulse acoustic volume measurement (AVS, "iiSure") is described only in
  manufacturer material. No independent per-window accuracy table was found beyond Butterfield.
  A 0.05 U bench figure is **[unverified]**.

**Manufacturer 1/6/12-h tables (median [min, max] delivered)** **[V]**

| Pump | Rate | 1 h | 6 h | 12 h | Notes |
|---|---|---|---|---|---|
| Omnipod 5 (12 pods) | 0.05 U/h | 0.049 [0.00, 0.12] | 0.30 [0.13, 0.57] | 0.59 [0.34, 0.99] | no warm-up |
| Omnipod 5 | 1.00 U/h | 0.99 [0.65, 1.55] | 5.97 [5.06, 6.87] | 11.88 [10.53, 13.26] | no warm-up |
| t:slim X2 (32 pumps, half aged) | 0.1 U/h | 0.12 [0.09, 0.16] | 0.67 [0.56, 0.76] | 1.24 [1.04, 1.48] | **after a 1-h warm-up** |
| t:slim X2 | 2.0 U/h | 2.1 [2.1, 2.2] | 12.4 [12.0, 12.8] | 24.3 [22.0, 24.9] | no warm-up |
| MiniMed 780G (32 pumps, half aged) | 0.025 U/h | 0.041 [0.000, 0.094] | 0.219 [0.052, 0.364] | 0.518 [0.171, 0.695] | no warm-up |
| MiniMed 780G | 1.0 U/h | 0.89 [0.81, 0.98] | 5.81 [5.62, 6.03] | 11.79 [11.46, 12.11] | no warm-up |

Read as relative error **[derived]**:
- **Omnipod 5 at 1 U/h:** 1-h range −35% to +55%, 6-h range −16% to +15%.
- **t:slim at 0.1 U/h:** median +20% at 1 h and +12% at 6 h.
- **780G at 1 U/h:** median −11% at 1 h and −3% at 6 h. That is a systematic start-up deficit (§2).
- **780G at 0.025 U/h:** median +64% at 1 h and +73% at 12 h. Its labelled ±10% is a long-window
  claim.

### 1.3 Bolus accuracy

| Pump | Bolus | Mean | Spread | Source |
|---|---|---|---|---|
| Omnipod 5 (n = 5,987) | 0.05 U | 0.050 U | range 0–0.119; 18% within ±5%; 12% below 75%; 12% above 125% | TUG [V] |
| Omnipod 5 (n = 300) | 5.0 U | 5.01 U | 95.7% within ±5%; range 4.49–5.37 | TUG [V] |
| Omnipod 5 (n = 72) | 30 U | 30.05 U | range 29.56–30.62 | TUG [V] |
| t:slim X2 (n = 800) | 0.05 U | 0.050 U | range 0–0.114; 34% within ±5%; 12.5% below 75% | UG [V] |
| t:slim X2 (n = 800) | 2.5 U | 2.46 U | 94.1% within ±5%; **range 0.00–2.70** (1.1% of boluses <25%) | UG [V] |
| t:slim X2 (n = 256) | 25 U | 25.03 U | 98.4% within ±5% | UG [V] |
| MiniMed 780G (n = 800) | 0.025 U | 0.024 U | range 0.004–0.041; 17% within ±5% | TG [V] |
| MiniMed 780G (n = 800) | 2.5 U | 2.45 U | 96.8% within ±5% | TG [V] |
| MiniMed 780G (n = 320) | 25 U | 24.58 U | 100% within ±5%; mean −1.7% | TG [V] |
| Omnipod DASH (n = 225) | 0.1 / 0.2 / 1 U | +1.3 / −2.5 / −0.3% | sd 12.9 / 18.5 / 13.6% | Mende 2022 [V] |
| Omnipod Eros, Solo, A6 | 0.2 U | +1.5 / −3.3 / +3.3% | sd 20.8 / 8.4 / 23.3% | Ziegler 2021 [V] |
| Durable pumps (8 configs) | 1 U | −2.4 to +1.2% | sd 1.7–3.5% | Freckmann 2019 [V] |
| Omnipod Eros | 1 U | 0.0% | sd 12.5% (77% within ±15%) | Freckmann 2019 [V] |
| All 10 systems | 10 U | −0.9 to +0.4% | sd 0.6–1.1%; all within ±5% | Freckmann 2019 [V] |
| 670G / t:slim / YpsoPump | 0.1 U | — | ~85 / 96 / 88% within ±15% | ATTD 2020 [A] |

**Bolus speed** (matters for bolus-in-progress cycles) **[V]**:
- Omnipod 1.5 U/min.
- t:slim 2.97 U/min for 25 U and 1.43 U/min for 2.5 U.
- 780G 1.5 U/min standard and 15 U/min quick.
- Accu-Chek Insight/Combo deliver 10 U in 50 s, Animas Vibe in 20 s, 640G and Omnipod in about
  6.6 min (Freckmann 2019).

### 1.4 Model form (flow accuracy)

1. **Quantize first.** Deliver whole pulses on the pump's own schedule. That schedule is a 0.05 U
   pulse for Omnipod, a 5-min tick for t:slim, a 0.025 U stroke for 780G, a 3-min tick for Insight
   and a 4-min tick for Dana (Hammond 2019 slides, **[A]**). At 0.05–0.1 U/h most of the 1-h error
   in the tables is the quantization itself.
2. **Add a multiplicative, autocorrelated volume error** per pulse: `v_k = v_nom · (1 + b + e_k)`.
   - `b` is a per-device bias, ~N(0, 1–2%) (72-h totals are within ±2% for all pumps except one
     outlier).
   - `e_k` is AR(1) at the hourly scale, τ ≈ 30–60 min [assumption]. Its sd is set so the 1-h
     window sd matches the tables after quantization: durable pumps ~3–5% at 1 U/h; Omnipod ~10% at
     1 U/h and ~20% at 0.1 U/h; Medtrum A6 ~17%.
   - Twiist: bias ±1%, small e_k (volume-verified).
3. **Per-bolus error.** sd ≈ max(0.6%, c / √units), with c ≈ 3% for durable pumps and ≈ 12% for
   Omnipod [derived fit to the 1 U and 10 U rows]. Add a small probability (~1% on t:slim 2.5 U) of
   a large under-delivery (<25%), which is visible in the t:slim table. The cause of those rows is
   not stated.
4. **What it does to glucose.** A 10% 1-h error at 1 U/h is 0.1 U. For a 50 mg/dL/U ISF that is
   ±5 mg/dL, spread over the insulin action curve [derived]. Short-window noise is a **small**
   glucose term next to site and occlusion faults. Its main use is as realism for dose-fidelity
   checks. It should never be tuned to explain glucose variance.

---

## 2. Stiction, start-up, and the pressure/temperature environment

### 2.1 Stiction and start-up transients

- **Mechanism.** Static friction between plunger and barrel exceeds dynamic friction. At low drive
  speed, silicone-oil lubricant is squeezed out, producing stick-slip. Each burst under-delivers
  until the plunger breaks free, then over-delivers. This evidence comes from patents and a
  lubricant-vendor paper only. The vendor test reported syringes under-delivering for about the
  first 15 min, then compensating **[A, ONdrugDelivery 2017; US 9333297]**. No peer-reviewed
  insulin-pump stiction magnitude was found.
- **What the bench data show, without naming a cause:**
  - 780G at 1 U/h from a cold start: median −11% in the first hour and −3% over 6 h; the minimum
    pump delivered 0.81 U in hour 1 **[V]**. That is a deficit followed by catch-up, the stiction
    and compliance signature, but the guide gives no mechanism.
  - Freckmann 2019 found most pumps **over**-delivered in the first 12 h (640G +9.9%, Omnipod
    +5.0%, Animas +4.7%), while the Insight under-delivered early. All returned to ±1.3% over
    12–72 h **[V]**.
  - The t:slim guide reports 0.1 U/h accuracy only after a 1-h warm-up **[V]**, which suggests a
    start-up transient it chose not to show.
  - Note: the 640G infusion-set batch Freckmann used was later recalled.
- **Model form.** After each reservoir or pod start, add a transient
  `Δ(t) = A · exp(−t/τ)` to the delivered rate, where:
  - A ~ N(0, 8%) per start, either sign, slightly skewed to over-delivery for durable pumps;
  - τ ≈ 2–6 h;
  - the transient conserves volume over about 12 h where the bench shows catch-up (780G)
    [assumption fitted to the two sources].

  This adds at most about 0.5 U over the first hours [derived: 10% × 1 U/h × ~5 h], so it is a
  small term.
- **Clumping during long zero-temps.** AID controllers send many short zero or low temps. Whether
  stiction makes resumption after a suspend lumpy has **not been measured**. Do not model it
  separately; the per-pulse AR noise covers it.

### 2.2 Atmospheric pressure (flight, altitude)

**King 2011 [V]**: 5 Animas 2020 and 5 Paradigm pumps, 1 U/h, aspart, 25 °C.

| Condition | Animas | Medtronic |
|---|---|---|
| Chamber ascent 760 → 560 mmHg over 20 min (excess) | 0.78 U (0.65–1.04) | 0.71 U (0.34–0.99) |
| Chamber descent 560 → 760 (deficit) | 0.66 U (0.37–0.94) | 0.53 U (0.29–0.82) |
| Commercial flight, ascent (excess) | 1.37 U (0.685% of cartridge) | 1.01 U (0.561%) |
| Commercial flight, descent (deficit) | 0.87 U | 0.58 U |
| Rapid decompression 760 → 260 mmHg in 1 min | >8 U (plunger movement) | >8 U |

- Bubbles appeared in every cartridge once pressure dropped 50 mmHg. Existing bubbles expanded by
  about 36% on ascent. Excess volume is linear in ΔP and in fill volume (Henry's law). The authors
  recommend filling only 1.5 mL for a flight.
- Clinical picture: hypoglycaemia 60–90 min after take-off in a 10-year-old. The authors knew of
  50 similar patients.
- **2024 replication (EASD; Fan, King et al.; 780G, t:slim X2, Omnipod DASH; 26 pumps) [A]:** full
  cartridges over-delivered about 0.60 U over a 20-min ascent and under-delivered about 0.51 U on
  descent. The effect did not depend on brand.
- **t:slim venting [V, UG]:** the pump vents automatically. During a gradual elevation change of
  about 1,000 ft (305 m), "delivery accuracy can vary up to 15% until 3 units have been delivered".
  A mountain drive is therefore a smaller, but real, version of the flight effect.
- **Bubbles form at small pressure changes.** Bubbles formed with only −22 mmHg (300 m, a tall
  building) **[V, Lopez 2014]**.
- **Operating limits [V]:** Omnipod 5 700–1,060 hPa; 780G 70.3–106.2 kPa.
- **Model form.**
  - Scenario lever `pressure_event(ΔP, fill_mL)`. Ascent adds a bolus of `k · fill_mL · ΔP`,
    spread over the ascent duration. With k ≈ 0.6% of fill volume per 200 mmHg, a 2 mL cartridge
    with 200 mmHg gives about 1.2 U [derived].
  - Descent applies a deficit of about 0.75 × that amount over the descent.
  - Neither is visible to the controller.
  - Default off. Use it in the travel scenario only.

### 2.3 Temperature

- **Bubble formation.** Insulin filled at 4 °C and warmed to 37 °C formed bubbles in cartridges and
  tubing. The volume was not measured, and the authors say any delivery effect is "currently
  unknown" **[V, Lopez 2014]**.
- **Thermal expansion of the fluid.** No direct bench measurement of over-delivery was found
  **[unverified]**. Order of magnitude: water expands about 0.03%/°C near 30 °C, so a 2 mL
  reservoir warming 10 °C displaces about 0.6 µL ≈ 0.06 U [derived]. That is negligible; bubbles
  are the real path.
- **Model form.**
  - Cold-filled reservoir: raise the bubble-event hazard for the first day (see §3.3).
  - No direct thermal-expansion term.
  - Heat effects on potency: see §4.3 and `03` §3.4.

---

## 3. Cannula and site faults

### 3.1 Complete occlusion: what alarms, and when

The alarm is **volume-triggered**. A pressure threshold corresponds to an accumulated volume of
missed insulin. Latency is therefore about V_alarm / commanded rate, and it is very long at basal
rates typical of children and of AID suspends.

| Pump | Missed volume at alarm | Bolus | 1 U/h (2 U/h for t:slim) | Low rate | Source |
|---|---|---|---|---|---|
| Omnipod Eros / 5 | "average 3–5 U" | 5 U bolus: 33 min typical, 35 max | 3.0 h typical, 5.5 h max | 0.05 U/h: 51 h typical, 80 h (pod expiry) max | UK Eros guide, Omnipod 5 TUG [V] |
| Omnipod DASH (bench) | — | — | 3 h 16 min (3:06–4:40) | 0.1 U/h: 27 h 37 min | Mende 2022 [V] |
| MiniMed 780G | 2.98 U (standard bolus), 2.45 U (quick) | 10 U standard: 124 s (77–173) | 3 h 21 min (2:27–4:21) | 0.025 U/h: 181 h (131–212) | 780G TG [V] |
| t:slim X2 | — (≥3 U boluses alarm) | ≥3 U: 1 min 2 s typical, 3 min max | 2 U/h: 1 h 4 min typical, 2 h max | 0.1 U/h: 19 h 43 min typical, 36 h max | t:slim UG [V] |
| Accu-Chek Solo | — | — | 2 h 57 min | 0.1 U/h: 35 h 11 min | Ziegler 2021 [V] |
| Medtrum A6 | — | — | 7 h 26 min | 0.1 U/h: no alarm in 9/9 runs within 72 h | Ziegler 2021 [V] |
| Paradigm / Combo / Animas (bench) | bolus: 1.15 / 3.0 / 1.59 U missed | — | 0.5 U/h: 143 / 58 / 90 min median | — | Borot 2014 [V] |
| Omnipod (bench, n = 1) | bolus: 4.7 U missed | — | — | — | Borot 2014 [V] |
| twiist (AVS) | not reported | — | 5× faster than conventional pumps | up to 22.5× faster at low rates | Butterfield 2024 [V] |

- Missed volume implied by the timing **[derived]**:
  - t:slim: 2 U/h × 1.07 h ≈ 2.1 U (max 4 U); 0.1 U/h × 19.7 h ≈ 2.0 U.
  - Omnipod: 1 U/h × 3 h = 3 U; 0.05 U/h × 51 h = 2.6 U.
  - 780G: 3.4 U at 1 U/h; 4.5 U at 0.025 U/h.
  - Solo: about 3 U at both rates.

  So V_alarm ≈ 2–4.5 U and roughly independent of rate.
- Across five brands at 20 flow-rate × tubing-length combinations, alarm latency ran from 1.5 to
  24 h, mostly 2–4 h, and doubled from 1.0 to 0.5 U/h **[V-secondary, Klonoff 2017 citing ref 11]**.
- **Occlusion pressure [V]:**
  - Butterfield 2024: Omnipod 23.6, t:slim 20.8, MiniMed 14.3 and ND 6.5 psi.
  - 780G threshold: ≤13.15 psi (25 psi during tubing fill).
  - t:slim maximum and alarm threshold: 30 psi.
  - Omnipod maximum: 35 psi.
- Air in the fluid path delays occlusion alarms (780G TG note) **[V]**.
- **AID-specific consequence [derived].** Pressure builds only while the controller commands insulin.
  - When an occlusion drives glucose up, Loop and oref increase delivery, which shortens the time
    to alarm. A Loop auto-bolus of ≥3 U would alarm a t:slim within minutes.
  - When glucose is low or falling, a zero temp builds no pressure at all.
  - So the simulator must accumulate **commanded-but-undelivered volume**, not wall-clock time.
- **Release bolus.** If an occlusion clears by itself, part of the missed volume is delivered at
  once **[V]**:
  - 780G: average 1.12 U on clearing.
  - t:slim: <3 U at 2 U/h basal.
  - Omnipod: "would not exceed the volume programmed".
  - Bench at 0.5 U/h: 0.04–0.68 U (Borot 2014).

  This is also the hypo hazard after a kink is relieved (Klonoff 2017).

### 3.2 Partial occlusion, kinking, silent occlusion

- **Silent occlusions are common in pressure-monitored studies.** Gibney et al., as cited by
  Klonoff 2017 **[V-secondary]**:
  - Pilot (n = 25): silent occlusions in 50% of standard-set wears after manual insertion vs 13.6%
    with a side-ported set; after mechanical insertion, 36% vs 8.3%.
  - Second study: flow interruptions in 10.2% vs 2.6%.

  These are short pressure events, not hours of zero delivery. Their insulin cost is not reported.
- **Kinking:**
  - 0.5% of 7-day Medtronic extended-wear sets kinked at insertion **[V, Brazg 2022]**.
  - Earlier Teflon-cannula data cited there: kinking contributed to 15% of failures, and 18.7% of
    cannulas were found kinked.
  - Patel 2014: 15% initial failure of Teflon Quick-Set, attributed to kinking on insertion. 64% of
    both set types had failed by day 7, 30% of them from hyperglycaemia not corrected by a bolus
    **[A]**.
  - Pickup 2014 (n = 92): 64% of patients had ever had a blockage or kink **[A]**.
  - Liebner (paediatric surveillance): obstruction was 33.9% of 1,404 events; 10.1% of patients had
    a bent cannula **[V-secondary, Heinemann & Krinelke 2012]**.
- **Set failure with hyperglycaemia:**
  - **Kanapka 2022** (two trials, 263 participants aged 6–71, 22,741 sets): 3.3% of sets removed
    before 72 h with prolonged hyperglycaemia, about 4 per user-year. Adults 1.9%, ages 14–17 5.8%,
    ages 6–13 4.4%. By set type: 90° Teflon 4.0%, angled Teflon 1.3%, steel 1.9% **[A]**.
  - Hyperglycaemia had run >250 mg/dL for about 5 h before the user acted **[03]**.
  - Older trials **[V-secondary, Klonoff 2017]**:
    - Raskin 2001: 36% of hyperglycaemia episodes were from occlusion.
    - Bode 2002: 22–36% of subjects had ≥4 clogs in 16 weeks, but only 6–9% of clogs coincided
      with hyperglycaemia.
    - van Bon 2011: 61–68% of users had ≥1 unexplained hyperglycaemia or occlusion over 39 weeks.
- **Real-world silent non-delivery:**
  - 40–50% of pump users have ≥1 event per year, and it may be as frequent as monthly; it is
    detected more often from hyperglycaemia or DKA than from alarms **[V-secondary: Butterfield
    2024 citing Hughes et al.]**.
  - The twiist volume-sensing pump detected 67 occlusions in 15 of 20 adults over 8 weeks, about
    1.8 per user-month, within 30 min of glucose starting to rise **[03; Ruiz 2026 not re-checked
    here]**. The trial registry hit for twiist found this session is a 307-person type 2 trial
    (NCT06853990). Confirm which cohort the 20-adult numbers come from before relying on them.
- **Donor-pool measurement** (eda L52, twiist users, 2,581 changes; see `05` §1a):
  - A quarter of site changes come early (<48 h).
  - Before those early changes, glucose climbs +9 → +22 → +32 mg/dL over 6–12 h while delivery
    stays flat (0.96–1.02×), and +42 mg/dL at the change.
  - This is the observable signature of a partial or complete site failure under AID. It is the
    best calibration target available.
- **Model form (§3.1 and §3.2 combined).** A per-site fault process:
  1. **Onset.** Hazard per site-hour, h(age) = h0 · g(age).
     - h0 is set so P(failure within 72 h) ≈ 2–4% for adults and 4–6% for youth (Kanapka).
     - g rises after 48 h (Kerr 2008 bench: no occlusions before 48 h).
     - At insertion: P(kink) ≈ 0.5–2% for Teflon (soft) cannulas and ≈ 0 for steel; Omnipod has a
       soft cannula.
  2. **Severity.** Delivered fraction f drawn from a mixture: full occlusion (f = 0) or partial
     (f ~ U(0.2, 0.8)) [assumption; no source gives the split].
     - Calibrate so donor glucose rises about 30 mg/dL over 6–12 h with flat commanded delivery
       (eda L52).
  3. **Alarm.** Accumulate `U_miss += (1 − f) · commanded`. Alarm when U_miss ≥ V_alarm.
     - V_alarm per pump: Omnipod 3–5 U, 780G 2.5–3.5 U, t:slim 2–4 U.
     - A partial occlusion may never reach the threshold.
     - twiist: detect at about 30 min from onset.
  4. **Resolution.** Ends at whichever comes first:
     - alarm → site change (behaviour model: response delay);
     - the user notices hyperglycaemia (behaviour trait; Kanapka ~5 h >250);
     - spontaneous clearing with probability p_clear, which releases min(U_miss, R_max), with R_max
       ≈ 1–3 U.
  5. **Controller view.** Throughout, the controller's dose history records commanded delivery.
     Phantom IOB = ∫(1 − f) · commanded.

### 3.3 Air bubbles in the fluid path

- **Volume per length.** The Accu-Chek Insight Flex tubing prime is 9 / 13 / 17 U for 40 / 70 /
  100 cm **[A, IFU]**. That gives ≈0.13 U per cm of tubing [derived], so a 10 cm bubble ≈ 1.3 U.
  This is consistent with the review's estimate "a 10 cm air bubble ≈ 1 U" **[V, Heinemann &
  Krinelke 2012]**.
- **Detection.** Omnipod, MiniMed and t:slim delivered 0.2 mL of reservoir air (≈20 U-equivalent
  [derived]) with **no alarm**. The twiist delivered no air **[V, Butterfield 2024]**.
- **Sources.** Cold insulin warming up, pressure drops (§2), and filling technique (Lopez 2014;
  manufacturer warnings). Vibration does not create bubbles, though it may move them.
- **Frequency.** Common in surveys. No per-wear rate was found **[unverified]**.
- **Model form.** Bubble event with hazard per reservoir.
  - Raise the hazard on the first day of a reservoir and for cold-filled insulin.
  - Size ~ lognormal, median 0.3 U, p95 2 U [assumption].
  - When it reaches the cannula: commanded volume equal to the bubble is not delivered, and the
    pump never alarms.
  - Patch pumps have no tubing, but air in the reservoir behaves the same way.

### 3.4 Leakage and backflow at the site

- Leakage at the set head, linked to cannula movement and insulin backflow, is recognised. Past
  small leaks caused DKA cases. **No prevalence or volume is published** in the sources reviewed
  **[V, Heinemann & Krinelke 2012]**.
- Butterfield 2024 argues that lower occlusion pressure means "lower potential for site leakage".
  That is an inference, not a measurement.
- The Omnipod 5 cannula-tear early alert (insulin leaking into the pod instead of the user) shows
  that a fault mode of total non-delivery with no alarm exists **[A, FDA early alert; date not
  checked]**.
- **Model form.** Optional per-site trait λ_leak: a fraction of each bolus lost, rising with bolus
  size, e.g. λ = λ0 · min(1, units/5) [assumption, no evidence]. Default λ0 = 0. Flag as
  evidence-free; prefer to fold any leakage into the partial-occlusion f of §3.2.

### 3.5 Dislodgement

- 7-day extended set: accidental pull-out 7.3% and adhesive failure 6.2% of sets. Benchmark 3-day
  set: 10% and 5% **[V, Zhang 2022]**.
- Mechanically this is a complete non-delivery that **never alarms**: the pump pushes freely into
  air or skin.
- **Model form.** Hazard per site-hour (≈ 0.1%/h [derived: 7.3% / 168 h]). f = 0, no alarm, ended
  only by the user noticing (behaviour model).

### 3.6 Lipohypertrophy at the site

- Prevalence:
  - 26% of pump users self-report lipohypertrophy **[A, Pickup 2014]**.
  - 42% on examination in 50 children; 45–47% in preschool and school-age children
    **[V-secondary, Heinemann & Krinelke 2012]**.
- Effect:
  - Famulla 2016 (n = 13, lispro, clamp + meal): reduced and **more variable** absorption from LH
    tissue, and postprandial glucose ≥26% higher **[A]**.
  - An earlier aspart study (n = 9): Cmax −25%, AUC0–240 −22% [derived from the reported
    pmol/L means] **[A]**.
- **Model form.** Per-person trait p_LH. For sites drawn on LH tissue (probability = fraction of
  sites on LH), apply bioavailability F ≈ 0.75–0.85 and inflate the absorption-rate variance.
  Otherwise a site is normal.

---

## 4. Site and pod change mechanics

### 4.1 Prime, cannula fill, and what is counted

- **Omnipod (Eros/DASH/5).**
  - Pairing primes 2.6 U into the pod's fluid path; this never reaches tissue.
  - Then a 0.5 U cannula-insertion bolus, partly filling the cannula and partly reaching tissue.
  - Both run at the prime pulse timing **[V, OmniBLE `Pod.swift`: `primeUnits = 2.6`,
    `cannulaInsertionUnits = 0.5`, configurable extra]**.
  - Prime rate 0.05 U/s, so the 2.6 U prime takes about 52 s [derived from the Omnipod 5 TUG,
    **V**].
  - Reservoir 200 U; minimum fill 85 U (the pod beeps at 85 U); 72 h nominal life, 80 h hard stop
    **[V]**.
- **Tubed pumps.**
  - Tubing prime: 9–17 U by length (Insight Flex 40–100 cm) **[A]**.
  - Cannula fill: Insight Flex 0.7 U **[A]**; t:slim 0.1–1.0 U **[V]**; 780G 0.025–5.1 U,
    user-set **[V]**.
  - t:slim leaves about 15 U unusable in the cartridge **[V]**.
- **What reaches the body.** Prime is never delivered to the person. Cannula fill is meant to equal
  the cannula's dead volume. If the user sets a larger fill, the excess is an **uncounted bolus**.
- Whether Loop records the Omnipod 0.5 U insertion bolus in IOB was **not checked**
  **[unverified]**. Model it as delivered to tissue minus a dead volume of about 0.3–0.5 U
  [assumption], and expose a flag for whether the controller counts it.

### 4.2 The gap during a change, and the new-site effect

- **Delivery gap.** From removing or deactivating the old set to the first basal pulse on the new
  one; the duration is a behaviour trait.
  - **Omnipod.** Deactivate, fill (≥85 U), pair (prime about 1 min), apply, insert. A gap of
    5–20 min is plausible **[unverified]**.
  - **Tubed sets.** The reservoir change and the site change can be separate events.
  - **Measurement in place of assumption.** The donor pool has pod-change timestamps. Measure the
    gap there (see `05`, eda L52).
- **New-site and old-site effects (donor data, eda L52; see `05` §1a).**
  - Routine change: glucose rises over the last ~2 h, peaks about +28 mg/dL at 0–3 h after the
    change, insulin runs 1.5× in the first hour, and glucose is back to baseline by ~6 h.
  - Wear-out: none on days 1–4; +9 mg/dL in the last ~12 h before a routine change.
  - These are measured outcomes. The simulator should produce them from the following components,
    not paste them in as a glucose offset:
    - the delivery gap;
    - lost depot when the old site is removed;
    - prime/insertion handling;
    - a new-site absorption lag or bioavailability dip, if the first three fall short.
- **Lost depot.** Removing a site stops further absorption of insulin still in the local depot only
  if the depot leaks out. In standard PK models the depot is already in the tissue and keeps being
  absorbed. Default: no lost depot [assumption]; optional leak-at-removal fraction.

### 4.3 Insulin in the reservoir over the wear period

- Potency: lispro at 37 °C in pumps for 48 h kept full HPLC potency (Δ ≤4%) **[03, Lougheed
  1997]**. Labels: discard at 6 days (aspart/lispro) or 9 days (Lyumjev in pump), or after
  >37 °C **[03]**.
- Bench occlusion (24 pumps, 32–36 °C, 5-day runs) **[A, Kerr 2008]**:
  - No occlusions before 48 h.
  - Early occlusions (≤72 h) did not differ by analog.
  - 5-day occlusion probability: glulisine 40.9%, lispro 15.7%, aspart 9.2%.
- Preservative loss promotes aggregates and cannula occlusion (porcine model, no numbers) **[V,
  Zhang 2022]**. This is the mechanism behind the 7-day set's insulin-chemistry work.
- Brazg 2022 (7-day extended set, 3,041 wears) **[V]**:
  - Unexplained-hyperglycaemia failure was only 0.06–0.4% by day 6–7.
  - Earlier standard-set extended-wear studies reported 19–35%.
  - So late-wear occlusion is a property of set and insulin design, not of time alone.
  - Mean SG rose 150 → 156 mg/dL from day 1 to day 7.
- **Model form.** Use g(age) in the §3.2 hazard: flat to 48 h, then rising, with a slope that
  depends on set type and insulin. Apply a potency multiplier only for the heat scenario (`03`
  §3.4).

---

## 5. Recommended simulator structure

Build the pump as a separate stage between the controller's command stream and the body's depot:

```
controller command ─► [A] quantizer/scheduler (pump-specific pulses, bolus speed)
                     ─► [B] mechanism: per-device bias + AR(1) pulse noise + start-up transient
                     ─► [C] environment: pressure/temperature bubble events (scenario-only)
                     ─► [D] fluid-path/site state machine:
                              OK → {bubble, kink, partial occl., full occl., dislodged}
                              tracks U_miss → alarm at V_alarm (pump trait) / release bolus
                     ─► [E] site absorption: bioavailability F (LH), site-age PK (03 §3.2)
                     ─► depot (physiology)
pump-reported history = output of [A] (commanded/"delivered" as the pump believes)
controller IOB built from pump-reported history  ⇒ phantom IOB = reported − delivered
```

- **Per-person traits:** youth vs adult hazard scale, LH fraction, set type (steel / angled Teflon /
  90° Teflon / pod), insulin analog, site wear length, alarm-response delay, and the
  hyperglycaemia-noticing threshold. Behaviour lives in `04`.
- **Per-pump parameters:** pulse quantum and schedule, 1-h noise sd by rate, bolus sd, V_alarm, R_max,
  air detection, and the twiist's fast-detect flag.
- **Calibration targets, in priority order:**
  1. eda L52 early-change glucose signature (+9 → +32 mg/dL over 6–12 h, flat delivery) and the 25%
     early-change share.
  2. Kanapka failure rates (3.3% of sets, about 4 per year).
  3. Manufacturer and bench per-window tables, for [A]–[B] only.
- **Report ablations.** A delivery-fault run should report with faults on and off. Faults affect
  TIR (hyperglycaemia) far more than t<54. The exceptions are release boluses and flight ascent
  over-delivery, which are the only routes to fault-driven lows here.

---

## References

1. Freckmann G, Kamecke U, Waldenmaier D, Haug C, Ziegler R. Accuracy of bolus and basal rate delivery of different insulin pump systems. *Diabetes Technol Ther* 2019;21(4):201–208. doi:10.1089/dia.2018.0376. PMC6477586. [V]
2. Ziegler R, Oliver N, Waldenmaier D, Mende J, Haug C, Freckmann G. Evaluation of the accuracy of current tubeless pumps for continuous subcutaneous insulin infusion. *Diabetes Technol Ther* 2021;23(5):350–357. doi:10.1089/dia.2020.0525. PMC8080918. [V]
3. Mende J, Eichenlaub M, Waldenmaier D, Haug C, Freckmann G, Ziegler R. Evaluation of the accuracy and reliability of a tubeless insulin infusion system under laboratory conditions (Omnipod DASH). *J Diabetes Sci Technol* 2022. doi:10.1177/19322968211070815. PMC9294567. [V]
4. Kamecke U, Waldenmaier D, Haug C, Ziegler R, Freckmann G. Establishing methods to determine clinically relevant bolus and basal rate delivery accuracy of insulin pumps. *J Diabetes Sci Technol* 2019;13(1):60–67. doi:10.1177/1932296818788349. PMC6313283. [V]
5. Borot S, Franc S, Cristante J, et al. Accuracy of a new patch pump based on a microelectromechanical system (MEMS) compared to other commercially available insulin pumps: results of the first in vitro and in vivo studies. *J Diabetes Sci Technol* 2014;8(6):1133–1141. PMC4455475. [V]
6. Ziegler R, et al. Accuracy of three durable insulin pumps (MiniMed 670G, t:slim X2, mylife YpsoPump). ATTD 2020 abstract. [A — numbers via search snippet; the abstract page returned 403]
7. Butterfield RD, Sims NM. Performance of a CSII pump with acoustic volume and flow sensing in simulated high-consequence situations. *IEEE Open J Eng Med Biol* 2024;5:593–599. doi:10.1109/OJEMB.2024.3408092. PMC11329218. [V]
8. King BR, Goss PW, Paterson MA, Crock PA, Anderson DG. Changes in altitude cause unintended insulin delivery from insulin pumps: mechanisms and implications. *Diabetes Care* 2011;34(9):1932–1933. doi:10.2337/dc11-0139. PMC3161261. [V]
9. Lopez PE, King BR, Goss PW, Chockalingam G. Bubble formation occurs in insulin pumps in response to changes in ambient temperature and atmospheric pressure but not as a result of vibration. *BMJ Open Diabetes Res Care* 2014;2:e000036. PMC4212562. [V]
10. Fan KS, King BR, et al. In-flight insulin pump delivery (hypobaric chamber; 780G, t:slim X2, Omnipod DASH). EASD 2024, Madrid; press coverage (Medscape/MDedge, Dagens Diabetes). [A — authorship differs between reports]
11. Klonoff DC, Freckmann G, Heinemann L. Insulin pump occlusions: for patients who have been around the (infusion) block. *J Diabetes Sci Technol* 2017;11(3):451–454. PMC5505439. [V; cites Gibney, Raskin 2001, Bode 2002, van Bon 2011]
12. Heinemann L, Krinelke L. Insulin infusion set: the Achilles heel of continuous subcutaneous insulin infusion. *J Diabetes Sci Technol* 2012;6(4):954–964. PMC3440169. [V]
13. Kanapka LG, Lum JW, Beck RW. Insulin pump infusion set failures associated with prolonged hyperglycemia: frequency and relationship to age and type of infusion set during 22,741 infusion set wears. *Diabetes Technol Ther* 2022;24(6):396–402. doi:10.1089/dia.2021.0548. [A]
14. Brazg R, Garg SK, Bhargava A, et al. Evaluation of extended infusion set performance in adults with type 1 diabetes: infusion set survival rate and glycemic outcomes from a pivotal trial. *Diabetes Technol Ther* 2022;24(8):535–543. doi:10.1089/dia.2021.0540. [V]
15. Zhang G, Cohen O, Chattaraj S. Development of the extended infusion set and its mechanism of action. *J Diabetes Sci Technol* 2024;18(2):454–459 (online 2022). PMC10973872. [V]
16. Patel PJ, Benasi K, Ferrari G, et al. Randomized trial of infusion set function: steel versus Teflon. *Diabetes Technol Ther* 2014;16(1):15–19. [A]
17. Pickup JC, Yemane N, Brackenridge A, Pender S. Nonmetabolic complications of continuous subcutaneous insulin infusion: a patient survey. *Diabetes Technol Ther* 2014;16(3):145–149. PMC3934434. [A]
18. Kerr D, Morton J, Whately-Smith C, Everett J, Begley JP. Laboratory-based non-clinical comparison of occlusion rates using three rapid-acting insulin analogs in continuous subcutaneous insulin infusion catheters using low flow rates. *J Diabetes Sci Technol* 2008;2(3):450–455. doi:10.1177/193229680800200314. [A]
19. Famulla S, Hövelmann U, Fischer A, et al. Insulin injection into lipohypertrophic tissue: blunted and more variable insulin absorption and action and impaired postprandial glucose control. *Diabetes Care* 2016;39:1486–1492. doi:10.2337/dc16-0610. [A]
20. Ruiz A, Mcdonough A, Snow K, Bode B, Mitri J. Clinical utility of the twiist automated insulin delivery system: first study with twiist. *BMJ Open Diabetes Res Care* 2026. [03 — not re-checked; cohort size unclear]
21. Insulet. Omnipod 5 Automated Insulin Delivery System Technical User Guide (Canada, EN), appendix: specifications, delivery performance, blockage detection. [V]
22. Insulet. Omnipod (Eros) UK user guide (mmol/L, PDM with built-in meter), appendix: delivery accuracy and occlusion detection (Rev 12-20). [V]
23. Medtronic. MiniMed 780G System Technical Guide (US), pump specifications: basal/bolus delivery performance, occlusion detection, cannula fill. [V]
24. Tandem Diabetes Care. t:slim X2 Insulin Pump with Control-IQ Technology User Guide, ch. 33 Technical Specifications. [V]
25. Roche. Accu-Chek Insight Flex infusion set instructions for use (tubing and cannula fill amounts). [A — the training chart gives lower tubing values]
26. LoopKit/OmniBLE, `OmniBLE/OmnipodCommon/Pod.swift` (dev branch): `primeUnits`, `cannulaInsertionUnits`, `serviceDuration`. [V]
27. Hammond P. Technology update (pump feature comparison table). DTN 2019 slides, ABCD. [A]
28. ONdrugDelivery (TriboFilm) 2017. How lubricant choice affects dose accuracy in insulin pumps; US Patent 9,333,297 (stiction in drug-delivery pumps). [A — vendor and patent sources]
29. LoopEval internal: eda lesson 52 (site change and early-change signature, twiist donors) and Omnipod pulse truncation; summarized in `05-loopeval-findings.md`.
