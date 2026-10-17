# 15 — Hyperglycaemia-induced insulin resistance ("glucose toxicity"): time course, dose–response, reversal

> **How this was used (2026-10-16).** Commissioned for the fast fall of simulated night-time highs (LESSONS 79–80). Glucotoxicity at ~200 mg/dL is too small to explain it; the time course set an asymmetric onset/offset, and Del Prato 1997 (weak glucose effectiveness in T1D) motivated the SG test.

Written for the additive simulator's H term: SI × (1 − H), H → 0.26·clip((G−140)/220, 0, 1), τ = 12 h.
Problem being explained: simulated night highs (~200 mg/dL) fall faster under insulin than real ones (−82 vs −58 mg/dL over 3 h, so the real fall is ~29% slower).

Tags: **[checked]** means I read the abstract (Europe PMC / PMC full text) and the number comes from it. **[unverified]** means it comes from memory or secondary sources and was not confirmed. All effect sizes below were computed from the abstract values. DOIs and PMIDs were all confirmed via Europe PMC. Some volume:page numbers are from memory and should be treated as [unverified]; use the DOI.

---

## 1. Onset: how fast does resistance appear?

| Study | Population | Hyperglycaemia | Insulin-action readout | Effect | Tag |
|---|---|---|---|---|---|
| Fanelli et al. 1995, *Diabetes* 44:513, doi:10.2337/diab.44.5.513 | 7 healthy | **6 h** at ~13.5 mM (243 mg/dL), either 16:00–22:00 or 23:00–05:00, with glucose and insulin infused in both arms | GIR during a hyperinsulinaemic–hypoglycaemic clamp the **next morning** | **−15%** (36.7 → 31.2 µmol/kg/min; abstract pools the arms) | [checked] |
| same | 8 T1D | **15 h** at ~17 mM (306 mg/dL), identical insulin (~225 pmol/L), 16:00–07:00 | same | **−22%** (42.5 → 33.0) | [checked] |
| Yki-Järvinen, Helve, Koivisto 1987, *Diabetes* 36:892, doi:10.2337/diab.36.8.892 | 10 T1D on CSII | **24 h** at 281 mg/dL (15.6 mM) vs 99 mg/dL, same diet and insulin | 40 mU/m²/min clamp at ~140 mg/dL | **−18%** (10.1 → 8.3 mg/kg/min) | [checked] |
| Vuorinen-Markkola, Koivisto, Yki-Järvinen 1992, *Diabetes* 41:571, doi:10.2337/diab.41.5.571 | 8 T1D men | **24 h** at 20.0 mM (360 mg/dL) vs 7.1 mM | 300-min insulin infusion; uptake measured in the final normoglycaemic hour (240–300 min) | **−26%** whole body, −35% forearm, −54% nonoxidative disposal | [checked] |
| Fowelin et al. 1993, *Metabolism* 42:387, doi:10.1016/0026-0495(93)90092-3 | 7 well-controlled T1D | **44 h** at ~15 mM (270 mg/dL), similar insulinisation | Euglycaemic clamp 4 h after the period ended | **−32%** GIR; but the control (normoglycaemic) admission also fell −21% (NS), so the net effect is uncertain | [checked] |
| Boden et al. 1996, *Am J Physiol* 270:E251, doi:10.1152/ajpendo.1996.270.2.e251 | healthy | **68 h** at ~5, ~8.8, ~12.6 mM | Euglycaemic clamp with [6,6-²H₂]glucose | **12.6 mM: −55%** insulin-stimulated uptake. **8.8 mM: no significant change.** No hepatic effect reported | [checked] |
| Tripathy et al. 2019, *JCEM* 104:2842, doi:10.1210/jc.2018-02304 | 16 healthy (NGT) | **48 h** at +40 mg/dL (~136 mg/dL) | 3-step clamp with tracer | Peripheral disposal/insulin −37% (stated; the reported values give −45%). Hepatic IR index 20 → 52. Basal EGP 2.0 → 3.1. **Confounded** by endogenous hyperinsulinaemia, which causes resistance on its own (Del Prato 1994) | [checked] |
| Vaag et al. 1992, *Diabetes* 41:174, doi:10.2337/diab.41.2.174 | 11 T1D | **4 h** at 12.1 mM, replacement insulin | Muscle biopsies and tracer; no post-exposure clamp | Disposal **rose** (mass action). Glycogen-synthase fractional velocity fell 18 → 12%, but it also fell on the control day (26 → 20%). **No clear 4-h resistance signal** | [checked] |
| Richter, Hansen, Hansen 1988, *Biochem J* 252:733, doi:10.1042/bj2520733 | Perfused rat hindlimb | **5 h** at 12 mM with supramaximal insulin | Maximal insulin-stimulated uptake | **−67%** (34.8 → 11.5), described as "rapidly developing". Glucose alone gave 80% of that effect | [checked] |
| Hawkins et al. 1997, *JCI* 99:2173, doi:10.1172/jci119390 | Rats | Prolonged hyperglycaemia at 18 mM | 7-h clamp | Uptake "markedly impaired" via hexosamine flux (UDP-GlcNAc ×2.5) | [checked, magnitude for the glucose arm not in abstract] |

**What onset speed the evidence supports.** No human study measures insulin action at 2, 4, 6, 8 and 12 h within one design. The only short-exposure human result is Fanelli 1995: about 15% after 6 h at 243 mg/dL in healthy subjects. That is the same size as the 24-h T1D effect at 281 mg/dL (18%). Under a single-τ model with τ = 12 h, the current formula predicts H ≈ 0.12·(1 − e^(−0.5)) ≈ 0.05 after 6 h at 243 mg/dL. Fanelli observed about 0.15, measured several hours *after* glucose had already returned to normal. The 4-h T1D study (Vaag) shows no clear resistance. The isolated-muscle rat study shows a large effect within 5 h.

Reading: onset is probably **on the order of 3–6 h**, faster than 12 h, and the effect is near its plateau by 15–24 h. The 15-h (22%), 24-h (18–26%) and 44-h (32%, control-confounded) T1D values are similar in size. This is an inference from a few small studies, and Fanelli measured the effect in a hypoglycaemic clamp.

## 2. Dose–response with glucose level

- **T1D, about 24 h of exposure:** 281 mg/dL → 18%; 306 mg/dL (15 h) → 22%; 360 mg/dL → 26%; 270 mg/dL (44 h) → 32% (confounded). The current form 0.26·(G−140)/220 predicts 0.17, 0.20, 0.26 and 0.15 for these. It fits the three clean points well. [checked inputs; fit is my arithmetic]
- **Healthy, 68 h:** no effect at 8.8 mM (158 mg/dL); −55% at 12.6 mM (227 mg/dL). Boden puts the threshold "between ~9 and ~12 mM" (162–216 mg/dL). [checked]
- No study tests **10 vs 15 vs 20 mM in T1D within one design**. The T1D points come from three groups at different durations. A threshold of 140 mg/dL is not contradicted, but anything in 140–180 mg/dL fits the data equally well.
- **At 200 mg/dL the evidence implies a small effect:** about 0.07 by the current formula, and possibly 0 if the threshold is near 180 (Boden). No paper measures it at 200 mg/dL.

## 3. Reversal after normoglycaemia

- **Hours:** the effect persists after glucose is lowered.
  - Vuorinen-Markkola 1992 measured −26% in the normoglycaemic hour that followed 150 min at 16.7 mM. [checked]
  - Fanelli 1995 measured −15% to −22% the morning after, which is roughly 3–10 h after the hyperglycaemic window ended, depending on arm. [checked; the gap is inferred from the stated clock times]
  - Fowelin 1993 measured −32% 4 h after a 44-h exposure. [checked]
  - **So offset is slower than onset; τ_off is at least several hours.**
- **Days:**
  - Hawkins et al. 2002, *Diabetes* 51:2179, doi:10.2337/diabetes.51.7.2179: in poorly controlled **T2D**, **72 h** of normoglycaemia fully restored glucose effectiveness (the effect of glucose itself on hepatic glucose production and uptake). [checked]
  - Lager et al. 1983, *BMJ* 287:1661, doi:10.1136/bmj.287.6406.1661: in T1D, insulin resistance under conventional treatment was "largely reversed" after **8 days** of CSII. [checked; abstract gives no magnitude]
- **Weeks to months:**
  - Yki-Järvinen & Koivisto 1986, *NEJM* 315:224, doi:10.1056/nejm198607243150404: insulin action at T1D diagnosis was −32% and returned to normal over **3 months** of treatment. Long-duration T1D averages −40%, inversely related to glycaemic control. [checked]
  - Revers et al. 1984, *JCEM* 58:353, doi:10.1210/jcem-58-2-353: well-controlled T1D had normal insulin dose–response; poorly controlled T1D was right-shifted with lower maximal disposal. [checked]
- **No study measures the reversal time course after a single acute 6–24 h exposure.** The plausible structure has two compartments:
  - an acute one: on in hours, off over about a day (hexosamine flux and GLUT4 transport are the proposed mechanisms; Yki-Järvinen & Mäkimattila 1997, doi:10.1007/s001250051431);
  - a chronic one: weeks, tracking HbA1c.

## 4. Correction-insulin effectiveness at high vs normal glucose in T1D

- **No controlled study measures the correction-bolus ISF at different starting glucose levels in T1D.** I searched Europe PMC and the web for this specifically.
- Blanc et al. 2019, *IEEE EMBC*, doi:10.1109/embc.2019.8857170 (Diabeloop data) report that "the insulin sensitivity factor depends on the current level of glycaemia" ("hyperglycemia induces insulin resistance" on a short-term basis in well-controlled patients). [checked abstract; **no magnitudes in the abstract**, full text not obtained]
- Aronson et al. 2019, FIT study, *Diabetes Care* 42:10, doi:10.2337/dc18-1475: after HIIT, starting from ~12.7 mM, corrections at 100% and 150% of the usual ICF lowered PG by 4.7 and 5.3 mM, and 50% lowered it by 2.3 mM. The usual ICF was roughly adequate from a high start, and 150% gave no proportional extra fall. This is the closest controlled correction-from-high datum, but it is post-exercise. [checked]
- Hegab 2022, *Front Pediatr*, doi:10.3389/fped.2022.854972: real-life ISF shows **diurnal variation**, with higher correction requirements in the morning. [checked]
- Davidson et al. 2008, *Endocr Pract* 14:1095, doi:10.4158/ep.14.9.1095: CF = 1700/TDD is derived from well-controlled patients, and the authors found the poorly controlled group's constants differed significantly. [checked; direction not in abstract]
- **Practitioner heuristics** [unverified, not evidence]:
  - oref/Trio "dynamic ISF" scales ISF ∝ 1/ln(BG/divisor + 1). With divisor 75 this makes ISF at 200 mg/dL about 65% of ISF at 100. It encodes the community belief that highs need more insulin per mg/dL, but it is not a measured physiology.
  - Walsh-style pump guidance suggests extra correction for persistent highs.

### Mass action: insulin's effect vs glucose level

- Best et al. 1981, *Diabetes* 30:847, doi:10.2337/diab.30.10.847: metabolic clearance falls as glucose rises. At fixed insulin, doubling glucose cut MCR by 38/16/11% at low/mid/high insulin. Disposal therefore rises **less than proportionally** with glucose, especially at low insulin. [checked]
- Verdonk et al. 1981, *Diabetes* 30:535, doi:10.2337/diab.30.6.535: at fixed ~18 µU/mL insulin, utilisation rose linearly (+0.4 mg/kg/min per +35 mg/dL) while clearance fell. [checked]
- **Del Prato et al. 1997**, *Diabetologia* 40:687, doi:10.1007/s001250050735 ("glucose resistance" in IDDM): with insulin clamped at basal, raising glucose by +11.2 mM raised disposal in controls by +13.2 µmol/kg/min but in **T1D by only +4.4**. That is about one-third of the normal mass-action effect. NEFA was also not suppressed by hyperglycaemia in T1D. [checked]
  - **Direct relevance:** any glucose-effectiveness (SG) term calibrated to healthy minimal-model values over-states how fast T1D highs self-correct.
- The sim already uses κ = 0.15 (weak glucose dependence above Gb), which is consistent with this literature.

### Other mechanisms that slow correction of highs

- **FFA / insulin-deficiency lipolysis** (named mechanism, time course known; healthy subjects, lipid infusion):
  - Roden et al. 1996, *JCI* 97:2859, doi:10.1172/jci118742: at FFA ~1.9 mM, uptake was **unchanged for 3.5 h, then fell to ~54% of control by 6 h** (−46%). [checked]
  - Boden et al. 1994, *JCI* 93:2438, doi:10.1172/jci117252: uptake fell dose-dependently with FFA (~9 → ~4 mg/kg/min from 50 → 750 µM). Hepatic glucose output under insulin rose ~50%. [checked]
  - **Why it matters here:** a night high caused by under-insulinisation (site failure, missed basal) carries raised FFA and ketones. That gives resistance with a **2–4 h lag** that resolves as insulin re-suppresses lipolysis. This is a candidate for the night-fall gap, distinct from glucose toxicity.
- **Counter-regulatory hormones during hyperglycaemia:** Fowelin 1993 found epinephrine, norepinephrine, cortisol, GH and NEFA **unchanged** by 44 h of hyperglycaemia in T1D (GH pattern abnormal). Hyperglycaemia itself does not raise counter-regulation. [checked] GH-driven nocturnal resistance (dawn phenomenon) is a separate, circadian factor and is not glucose-driven.
- **Dehydration / hemoconcentration:** Waldhäusl et al. 1979, *Diabetes* 28:577, doi:10.2337/diab.28.6.577 showed rehydration alone lowers BG and counter-regulatory hormones in **severe** hyperglycaemia. [checked citation; no abstract online; magnitude unverified] At ~200 mg/dL, osmotic diuresis is minimal, so this is irrelevant to the night-high case.
- **Glycosuria** speeds the fall above the renal threshold (~180–200 mg/dL). It is negligible at 200 and works in the opposite direction. [unverified magnitude]
- **Hepatic insulin action:**
  - Revers 1984: hepatic glucose output was ~100% suppressed at clamp insulin even in poorly controlled T1D. [checked]
  - Del Prato 1994, *Diabetologia* 37:1025, doi:10.1007/bf00400466: 72 h of mild hyperglycaemic hyperinsulinaemia left hepatic suppression unaltered. [checked]
  - Tripathy 2019 found hepatic insulin resistance (confounded, see above).
  - **Conclusion:** there is no consistent evidence for a separate hepatic glucose-toxicity term in T1D.

---

## 5. Recommended parameters

- **Magnitude / dose–response:** keep H_max = 0.26 at 360 mg/dL with a linear ramp. The T1D points are consistent with threshold 140. A threshold of 160–180 is equally consistent with the healthy data (Boden: no effect at 158 even after 68 h). Report the threshold as a range: **140 (current) to 180**.
- **Time constants:** make H asymmetric, because the evidence supports faster onset than offset.
  - **τ_on ≈ 6 h** (plausible 3–12 h; Fanelli 6 h already gives ~15% at 243 mg/dL; Vaag 4 h shows none).
  - **τ_off ≈ 24 h** (plausible 12–72 h; persists ≥4–10 h after normalisation; glucose-effectiveness defects reverse within 72 h).
  - These are judgment values bounded by the studies, not fitted.
- **Double-counting caution:** donor-derived ISF already embeds each person's habitual glycaemia, which is the chronic component (Yki-Järvinen 1986: −40% in long-duration T1D, tracking control). Treat H as the acute deviation and consider referencing it to the person's own mean glucose rather than to 140.

## 6. Honest bottom line on the night-fall gap

**Glucose toxicity cannot size the observed gap.** The real fall from ~200 mg/dL is ~29% slower than simulated. Even with instantaneous onset, the evidence-sized H at 200 mg/dL is about 0.07 (0 if the threshold is ~180). That would slow the fall by ≤7%, and by ~2% at the current τ = 12 h over a 3-h excursion. Speeding τ_on to 6 h does not change this materially. To reach ~30% at 200 mg/dL, H would need roughly 4× the magnitude any T1D study reports at that level.

The gap therefore points at other named components, which can be tested by ablation:
1. **Impaired glucose effectiveness ("glucose resistance") in T1D.** The mass-action self-correction is ~1/3 of healthy (Del Prato 1997). Check that the sim's SG / GEZI term is T1D-sized.
2. **FFA / ketone resistance after under-insulinisation.** About 3–4 h lag, up to ~45% at high FFA (Roden 1996; Boden 1994).
3. **Circadian / dawn nocturnal resistance** (Hegab 2022: higher morning correction need).
4. **Selection.** Night highs in real data are conditioned on being high, which over-samples low-sensitivity nights and people. The sim reproduces this only if it carries day-to-day sensitivity variability. Compare falls in sim vs real conditioned the same way before attributing the gap to physiology.

No study directly measures correction-bolus ISF as a function of starting glucose in T1D with magnitudes I could verify. Blanc 2019 asserts that the dependence exists but I could not obtain its numbers.
