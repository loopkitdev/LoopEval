# Candidate ledger

The history of every algorithm-change candidate tried against the goal in
[docs/GOALS.md](../GOALS.md) — what it is, where it was run, the numbers, and the verdict.
**Add an entry (status `planned`) before running a candidate; update it when scored.**
A candidate that isn't here didn't happen. Aliases only — never a URL, token, or donor id.

Scoring rule: [docs/FRONTIERS.md → Scoring](../FRONTIERS.md) — insulin-needs dial, strict
dominance in the operating band (validated multiplier ±0.1), paired block-bootstrap CI
(`loopeval_analysis.band.band_report`; driver `runs/2026-08-24-unannounced/score_band.py`).
Verdicts: **IMPROVES** (band-lift CI > 0 and some in-band point strictly dominates the
reference), **NEUTRAL**, **WORSE**. "lift" is in-band mean lift unless marked
*whole-sweep* / *ISF-dial* (older runs — ISF-dial lift is known to overstate, see FRONTIERS §4).
`ΔTIR@op / Δt54@op` = candidate − reference at the operating multiplier.

Families: **dose-more** = act sooner/harder when a meal is under way; **pull-back** = withhold
in a situation class that makes lows (lets needs go up); **dial-like** = moves along the
reference; **learned** = fitted from patient history (must carry data-needed / drift /
hold-out / leakage audit — see GOALS); **oracle** = headroom bound, never deployable.

Pre-2026-07 run dirs were deleted when `runs/` went git-ignored; entries citing only a commit
hash have no surviving traces.

## Index

| id | mechanism | family | status | verdict so far |
|---|---|---|---|---|
| [C01](#c01-asymmetric-integral-rc-airc) | Asymmetric integral RC (aIRC) | pull-back | scored (band, 4 donors) | **IMPROVES** bddp11 90 d (+0.019 [+0.005,+0.029]); **NEUTRAL** on all four 2-mo hands-off beds (mean +0.005) |
| [C02](#c02-integral-rc-irc) | Integral RC (IRC) | dial-like (hotter) | scored | **WORSE** in band on bddp11 (hooks); gentle-end wins elsewhere |
| [C03](#c03-gbaf--application-factor) | GBAF / application factor | dial-like | scored, closed | rides the reference — don't re-sweep |
| [C04](#c04-package-flags--momentum-knobs) | Package flags / momentum knobs | dial-like | scored | gate ~orthogonal but NEUTRAL; others dial-like |
| [C05](#c05-uam-projection) | UAM projection | dose-more | scored (bddp11; bddp07/03/08 unannounced) | **WORSE** on hands-off bddp11 and unannounced bddp03/08; **IMPROVES on unannounced bddp07 (+16.6 TIR at ≈0 lows)** — patient-conditional: pays only where the regime is lows-free and delivery is capped |
| [C06](#c06-early-rise-projection) | Early-rise projection | dose-more | scored (bddp11) | **WORSE** (−0.05 / −0.76) |
| [C07](#c07-ice-rise-boost) | ICE rise-boost | dose-more | scored (bddp11; 3 unannounced) | NEUTRAL/WORSE on bddp11; unannounced: IMPROVES bddp07 only (same split as UAM) |
| [C08](#c08-sensitive-mode-double-low-prevention) | Sensitive mode / double-low prevention | pull-back | scored (bddp11) | **WORSE (marginal)** on bddp11; old: dominates on user2 (announcer) |
| [C09](#c09-predictive-sensitivity-damper) | Predictive sensitivity damper | pull-back | scored (bddp11) | **NEUTRAL** (inert, −0.001) |
| [C10](#c10-post-low-protector) | Post-low protector (ISF-mult / suppress / trend) | pull-back | scored (bddp11) | ISF-mult **WORSE** (−3.5…−8.3 TIR for −0.07 t54); suppress-20 NEUTRAL (+0.006) |
| [C11](#c11-uncertainty-cap-dosing) | Uncertainty-cap dosing | pull-back (risk-bounded) | scored (bddp11) | **WORSE** at every k (−0.11 … −0.16) — closed |
| [C12](#c12-learned-circadian-needs-schedule-hourly-insulin-needs) | Learned circadian needs schedule | learned | scored (bddp11, holdout) | **WORSE** in-sample and holdout (k=1: −5.3 TIR / +0.96 t54 on holdout) — closed |
| [C13](#c13-basal--isf-decoupling) | Basal × ISF decoupling | dial-like (2-D) | scored once (ns3) | small lift band (+0.056 max), unfollowed |
| [C14](#c14-autosens-term) | Autosens (multi-hour BG-vs-target) | learned (short memory) | built, unswept | — |
| [C15](#c15-rc-window-knobs) | RC window knobs (retro / duration) | dial-like | scored (panel) | no lift; dur120 harmful |
| [C16](#c16-manual-bolus-rec-scaling) | Manual-bolus rec scaling | announcer behaviour | scored | +0.185 ISF-dial → +0.036 needs-dial (cautionary case) |
| [C17](#c17-oref-as-candidate-engine) | oref/OpenAPS as candidate engine | engine | fidelity only | no frontier number |
| [C18](#c18-asymmetric-standard-rc) | Asymmetric **standard** RC (rise-cut without integral RC) | pull-back | scored (4 donors) | **NEUTRAL / dial-like** — closed |
| [C20](#c20-post-low-gated-rc-rise-cut) | Post-low-gated RC rise-cut (corner candidate) | pull-back, gated | scored (bddp11 90 d); 2-mo beds running | **IMPROVES** +0.014 [+0.001,+0.029] at (0.5, 720 min, 180) — first corner-gated lift |
| [O2](#o2-carb-foreknowledge-oracle) | Oracle: carbs visible 30 min early | oracle | scored | +6–8 TIR at ≈0 t54, gentle end (bddp07) |
| [C19](#c19-learned-causal-60-min-ice-forecaster) | Learned causal 60-min ICE forecaster (per patient) | learned (dose-more/pull-back) | scored (bddp11, holdout) | **WORSE on holdout** (R² 0.16 isn't enough; bar ≈ R² 0.7) — closed as built |
| [O1](#o1-future-ice-forecast-oracle-headroom-bound-not-deployable) | Oracle: perfect 60-min exogenous (ICE) forecast | oracle | scored (bddp11) | **+10.0 TIR / −0.31 t54 at op**; half-strength still +3.9 TIR; noisy R²=0.5 already WORSE |

---

## C01 · Asymmetric integral RC (aIRC)
`--candidate-integral-rc --candidate-irc-drop-scale 1.5 --candidate-irc-rise-scale 0.5`
Sign-dependent IRC gain: believe unexplained falls (×1.5) more than unexplained rises (×0.5)
→ doses less into a falling discrepancy. Decomposition (rc-mom-panel `panel_asym.py`) says
the **rise-cut is the active part**; the drop-boost is ≈ inert (one-sided actuation).

| date | bed | regime | window / dial | result | verdict |
|---|---|---|---|---|---|
| 2026-08-24 | bddp11 | natural (hands-off) | 90 d, needs, band 1.00±0.1 | band lift **+0.022 [+0.006,+0.036]** (in-band reference; +0.019 vs full reference), dom 1.00 (lo 0.60); @op ΔTIR −0.9 Δt54 −0.07 Δt70 −0.52; holds on both halves (in-sample +0.016, holdout +0.014, daily blocks) | **IMPROVES** (1 donor) |
| 2026-08-21 | bddp11 | natural | 90 d, needs (whole-sweep) | mean lift +0.012, frac_pos 0.7; event arm: min<54 520 vs std 555, 2/23 lows avoided | leads (old rule) |
| 2026-08-11 | bddp11 | natural | 2 mo, needs | below-right of ref from ×0.85 up, no blow-up | leads |
| 2026-08-04 | bddp01/02/04/05/06/07 | natural | `runs/2026-08-04-rc-mom-panel` `asym_rank_summary.csv` | irc-base mean rank 2.83 (best); airc-full 3.50; airc-drop −0.109 on bddp01 | **asymmetry did not beat plain IRC** on the panel (old scoring, ISF dial) |
| 2026-07-20 | orefuser2 substrate | natural | vs normal IRC | 1.5/0.5 −0.16, rise-only −0.16, drop-only ≈0 | hurts (non-announcer) |
| 2026-07-17 | ns3 | natural | 3 mo, needs | ≈ IRC for m ≤ 1.2; +0.8 TIR only at ×1.25–1.35 | no lift in band |
| 2026-07-17 | user2 | natural (announcer) | 3 mo, needs | m1.0: 85.42/0.712 vs ref 84.95/1.225 → **+0.47 TIR AND −0.51 t54** | strict dominance |
| 2026-07-16 | user2 | natural | 9 wk wide, needs | aIRC+DLP lift +0.10, positive everywhere | held up |

| 2026-08-24 | bddp11 / bddp10 / bddp01 / bddp09 | natural | 2 mo each, op ×1.00, 9 weekly blocks | E3 `cohort_band_e3.csv`: band lift +0.015 [−0.002,+0.031] / +0.010 [−0.005,+0.027] / −0.020 [−0.030,+0.013] / +0.015 [−0.004,+0.032] (t70 axis); **multi-donor mean +0.005**, frac-dominant 0.65; @op ΔTIR −0.2, Δt54 −0.01 | **NEUTRAL on every 2-mo bed** — the effect is real-looking but the same size as 2-month noise; on the runs-high donor (bddp01) it doses *more* (+1.1 TIR, +0.03 t54) |

Ceiling is low (+0.02 lift ≈ 1 TIR point at equal lows); needs ≥ 90 d per donor to clear the CI.

## C02 · Integral RC (IRC)
`--candidate-integral-rc [--candidate-integral-rc-clamp]`. Memory in RC. A hotter dial:
bddp11 90 d @op +5.3 TIR / +0.62 t54, hooks above ×1.05 (m1.2 → t54 3.31). Band verdict
2026-08-24 **WORSE** (−0.021 [−0.043,−0.003]). rc-mom-panel (6 donors, 2026-08-04): best
mechanism in that panel (mean rank 1.5, +0.130 bddp06, −0.059 bddp04). ns3 1 yr: ≈ +3 TIR at
matched t54 (needs dial). Clamp variants (settings / velocity 2/4/8 / none): curves
superimposed on ns3 and user2 — **no lever**. IRC low-memory carry
(`--candidate-irc-low-memory-scale`): plumbed, never swept.

## C03 · GBAF / application factor
`--candidate-gbaf …`, `--candidate-application-factor`. Every run (ns3 1 yr, user2 1 yr,
bddp05/09 ISF-dial, bddp11 2 mo + 90 d) rides the reference; on bddp11 mildly above-left.
Reparameterization of the dial — **closed**; only revisit combined with a state-dependent trigger.

## C04 · Package flags / momentum knobs
Per-flag decomposition vs the class-1 base (bddp11 90 d): midAbsorptionISF = main
aggressiveness driver (dial-like, whole-sweep −0.027); RC-decay dial-like; package-native
worse (m1.2 t54 2.00). The gradual-transitions **gate** is the only ~orthogonal arm: band
2026-08-24 +0.019 [−0.009,+0.061] → **NEUTRAL** (CI straddles 0), un-followed-up.
Momentum lookback/projection 30 (panel): no lift, −0.15/−0.12 on bddp04. Momentum cap 2:
slider. Asymmetric momentum: built (2026-05), never swept on the current stack.

## E1 · bddp11 90 d, natural regime — the built dose-more/pull-back set (2026-08-24)
`runs/2026-08-24-unannounced/b11_90d/` (band_table_e1.csv, frontier.png). Reference: std on
needs 0.70–1.20; band 1.00±0.1 (field 69.2/0.35 sits on std ×1.00 = 68.8/0.36). **Every
dose-more mechanism is WORSE than the dial** — each buys TIR only with more t<54 than the
reference pays for the same TIR (uam45/irb40 ≈ hotter dial slightly above the curve; er1
adds lows for no TIR; longer projections crater). The pull-back mechanisms are dial-
equivalent (sens) or inert (sdamp). Reading: on a hands-off non-announcer, Loop's RC already
extrapolates the unexplained rise for 60 min; projecting it further is late information
mis-sized as a forecast — the value-of-information wall from REVIEW §2.2. Next: find the
situation classes behind the sim's lows (event taxonomy) rather than sweeping more gains.

## C05 · UAM projection
`--candidate-uam-minutes N` — trailing (30 min slow-on / 10 min fast-off) mean of the
*unexplained* glucose appearance (retrospective discrepancy) projected forward as a
tapering absorption term over N min → eventualBG rises early on a real carb rise.
**Leakage audit 2026-08-24:** `LoopAlgorithm.uamProjectionEffects` filters discrepancies to
`startDate ≤ start` — causal. Dose-more. Never swept before E1.

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-08-24 | bddp11 | natural | 90 d, band 1.00±0.1 | E1 `runs/2026-08-24-unannounced/b11_90d`: N=45 lift **−0.066 [−0.108,−0.036]** (@op ΔTIR +4.9, Δt54 +0.62 — a hotter dial, above the curve); N=90 −1.115 (Δt54 +2.88); N=180 −5.9 (Δt54 +10.5, TIR −3.9); uam90+C08 −0.89 | **WORSE** at every N — projecting unexplained appearance forward over-doses a hands-off donor; longer projection = catastrophic |
| 2026-08-24 | bddp07 (tight-control announcer, maxBolus 3 U) | **announcement-suppressed** (`--no-carb-entries --no-user-boluses`) | 2 mo, op ×1.00, t70 axis | E4 `cohort_band_e4a.csv`: N=90 lift **+0.203 [+0.165,+0.237]**, dom 1.00 (lo 1.00); @op **ΔTIR +16.6 [+15.2,+18.0]**, Δt54 +0.05, Δt70 +0.26; N=45 +0.090 (ΔTIR +7.8). Regime context: std natural ×1.00 = 92.2 TIR → std unannounced = 51.7 | **IMPROVES** (re-scored with the reference extended to ×2.0 and restricted to the band: lift +0.244 [+0.202,+0.279], dom 1.00 lo 0.80) — recovers ~40 % of the TIR lost by not announcing, at ≈0 lows. Mechanism of the win (hypothesis, consistent with the data): low needs + maxBolus 3 U / temp-basal strategy cap how much the projection can stack, so the regime is lows-free at every multiplier |
| 2026-08-24 | bddp03 (heavy announcer) | announcement-suppressed | 2 mo, op ×1.00 | E4: N=45 lift **−0.380** (@op ΔTIR +7.1, Δt54 +1.30); N=90 −2.73 (ΔTIR +9.2, Δt54 +4.16) | **WORSE** (in-band re-score −2.82 [−4.63,−1.84]; the first pass wrongly called it dominant against the reference at ×1.5–2.0 — scorer fixed, FRONTIERS → Scoring) — where the unannounced reference already makes lows (t54 0.47 at ×1.00), the projection stacks into them |
| 2026-08-24 | bddp08 (announcer, autobolus by day / temp at night) | announcement-suppressed | 2 mo, op ×1.00 | E4 `cohort_band_e4v2.csv`: N=90 lift **−1.02 [−1.74,−0.56]** (@op ΔTIR +14.7, Δt54 +1.53); N=45 −0.019 [−0.076,+0.092] (ΔTIR +6.9, Δt54 +0.29) | **WORSE / NEUTRAL** — big TIR, paid in lows; 3-donor mean N=90 −1.20, N=45 −0.10 |

## C06 · Early-rise projection
`--candidate-early-rise-gain G --candidate-early-rise-minutes N` (BG band 70–140, slope
threshold 0.3 mg/dL/min). Low-normal AND rising → project the rise as a meal-shaped bump so
dosing starts on the ascending limb; off high, off flat. Dose-more. Never swept before E1.

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-08-24 | bddp11 | natural | 90 d, band 1.00±0.1 | E1: (1.0,60) lift **−0.052 [−0.068,−0.037]** (@op ΔTIR +0.2, Δt54 +0.24 — lows for nothing); (2.0,90) −0.76 (Δt54 +1.99) | **WORSE** — ascending-limb dosing on a non-announcer adds lows without TIR |
| 2026-08-24 | bddp07 / bddp03 | announcement-suppressed | 2 mo, op ×1.00 | E4: (1.0,60) lift −0.063 / +0.010; ΔTIR +0.6 / +0.4 | WORSE / NEUTRAL — too small to matter either way |

## C07 · ICE rise-boost
`--candidate-ice-rise-boost-gain G` (BG gate 170→250, trailing 45 min ICE rate,
`-sens-suppress k` couples to C08). Positive forecast offset when BG is high AND trailing
ICE positive (sustained, actively-driven high). Dose-more at the peak.

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-06-15 (`c66b4c7`) | user2 | natural | 90 d, ISF-dial | g30/suppress 0.2: **+0.4 TIR at matched t54 0.7–0.8**; g45/g60 worse | real, capped ("value-of-information wall") |
| 2026-08-24 | bddp11 | natural | 90 d, band 1.00±0.1 | E1: G=40 lift **−0.045 [−0.088,−0.006]** (@op ΔTIR +3.9, Δt54 +0.52) | **WORSE** — hotter dial, slightly above the curve |
| 2026-08-24 | bddp07 / bddp03 | announcement-suppressed | 2 mo, op ×1.00 | E4: G=40 lift +0.082 [+0.011,+0.137] (ΔTIR +7.5, Δt54 +0.04) / **−0.289** (ΔTIR +3.7, Δt54 +1.06) | IMPROVES (+0.098 in-band re-score) / WORSE; bddp08 WORSE (−0.302; ΔTIR +12.2, Δt54 +0.78) — same split as UAM; 3-donor mean −0.18 |

## C08 · Sensitive mode / double-low prevention
`--candidate-sensitive-mode-tau-min τ --candidate-sensitive-mode-gain k`. EWMA of recent
*negative* discrepancy raises effective ISF by (1 + k·R) → damps re-dosing into the rebound
after a low. Pull-back.

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-07-17 | user2 (announcer) | natural | 3 mo, needs | DLP+aIRC m1.0 85.40/0.636 vs ref 84.95/1.225 → **+0.45 TIR AND −0.59 t54**; DLP alone 85.24/0.949 | strict dominance |
| 2026-07-17 | ns3 (hands-off) | natural | 3 mo, needs | m1.0 52.62/0.027 vs ref 54.23/0.044 (left of curve) | no lift |
| 2026-07-16 | ns3 / user2 | natural | 1 yr | ns3 worse (39.0 vs 41.4 TIR); user2 DLP+aIRC 72.1/0.147 vs 76.3/0.483 | announcer yes / non-announcer no |
| 2026-06-12 (`e18a017`) | user2 | natural | 90 d, ISF-dial | +2.5 lift alone, +8.0 stacked on aIRC (old rule); costly on ns3 (mean BG +10) | regime-specific |
| 2026-08-24 | bddp11 | natural | 90 d, band 1.00±0.1 | E1: τ=120,k=0.02 lift **−0.007 [−0.012,−0.000]**, dom 0.20; @op ΔTIR −1.0, Δt54 −0.04, Δt70 −0.20 (gentler, on/just above the curve) | **WORSE (marginal)** — dial-equivalent on this hands-off donor, as on ns3 |
| 2026-08-24 | bddp11 | natural | 90 d, band 1.00±0.1 | E2: τ=240,k=0.05 lift −0.014 [−0.021,−0.006]; @op ΔTIR −3.0, Δt54 −0.07 | **WORSE** — stronger = more TIR cost, same lows |

## C09 · Predictive sensitivity damper
`--candidate-sens-damp-gain g` (threshold 0.4 mg/dL/min, window 45, max ×2.5). Causal ICE
more negative than threshold → ISF raised proactively before the low. Pull-back. Commit
`1cba461` (2026-05-28): "bounded by the suspend wall — the signal that reveals sensitivity IS
the drop"; kept as a research handle.

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-08-24 | bddp11 | natural | 90 d, band 1.00±0.1 | E1: g=1.0 lift −0.001 [−0.004,+0.003]; @op ΔTIR −0.1, Δt54 −0.01 | **NEUTRAL** — essentially inert (fires only where suspend already is) |

## C10 · Post-low protector
`--candidate-postlow-isf-mult / -suppress / -window / -threshold / -trend-gain`. Recency-
decaying ISF reduction (or forecast suppression) after a low. Trend-gain "validated
experimentally as ineffective — the descent is where Loop is already suspending" (`1cba461`).
ISF-mult form never swept on the current stack.

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-08-24 | bddp11 | natural | 90 d, band 1.00±0.1 | E2 (`band_table_e2.csv`): ISF-mult 1.5/180 lift −0.045 [−0.074,+0.003] (@op ΔTIR **−3.5**, Δt54 −0.07); 2.0/180 −0.064 (ΔTIR −4.4); 3.0/180 −0.089 (−5.1); 2.0/360 −0.120 (**−8.3** TIR for −0.07 t54); forecast-suppress 20/180 **+0.006 [−0.006,+0.020]**, dom 0.80, @op ΔTIR −0.5 Δt54 −0.05 | ISF-mult forms **WORSE** — a blunt post-low damper hits every legitimate correction after the ~2 %/day of <70 time and buys almost no t54; suppress-20 **NEUTRAL** (cheap, slightly positive, CI straddles 0) |
| 2026-08-24 | bddp11 / 10 / 01 / 09 | natural | 2 mo, op ×1.00 | E3: suppress-20 band lift +0.011 / −0.011 / −0.003 (WORSE, t54=0 donor) / −0.000; mean −0.001 | **NEUTRAL — nil effect across donors**; closed |

## C11 · Uncertainty-cap dosing
`--candidate-uncertainty-cap -k -low -fmax -decouple`. Replaces AF + predicted-min gate with
one state-derived cap: largest dose whose worst-case trajectory (insulin ×(1+k)) with max
suspension stays above the low threshold. Built + identity-verified (`c8058d0`, 2026-06-11).
REVIEW §4.3: orthogonal in principle (forecast variance is state-dependent).

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-08-24 | bddp11 | natural | 90 d, band 1.00±0.1 | E6 `band_table_e6.csv`: k=0.3 lift **−0.125 [−0.161,−0.089]** (@op ΔTIR +3.2, Δt54 +0.69); k=0.5 −0.113 (+2.3, +0.53); k=1.0 −0.155 (ΔTIR −4.4, Δt54 +0.22) | **WORSE at every k** — replacing the 0.4 application factor with a worst-case bound doses fully whenever the bound permits; the bound is not conservative enough where lows actually form (the insulin is already committed), and too conservative elsewhere. Closed |

## C12 · Learned circadian needs schedule (hourly insulin needs)
`--candidate-needs-hourly <24 csv|@file> --local-timezone UTC` (added 2026-08-24: basal × h,
ISF ÷ h, CR ÷ h per hour — the hourly form of the needs dial; `EvalConfig.needsHourlyMultipliers`,
`InputWindowBuilder.applyDoubleScaling`). Fitter `runs/2026-08-24-unannounced/fit_hourly_needs.py`:
hourly mean ICE (mg/dL/h, from the patient's REAL trace) over the fit window, demeaned (the mean
is the global dial's job), converted to U/h via the scheduled ISF and expressed relative to
scheduled basal: h = clip(1 + k·((ICE_h − mean)/ISF_h)/basal_h, 0.6, 1.6), 3-h circular smoothing.
The reference is the constant-dial family; this is a different policy class (autotune-like) —
"dose more when the patient's history says a meal is habitually under way", the goal's learned
lane. **Leakage audit:** fit uses only samples with t < fit_end; holdout scoring is on
t ≥ fit_end; sims run over the full window and are scored in-sample vs holdout separately.

bddp11 (fit 05-08→07-08, holdout 07-08→08-06): hourly ICE profile stability — fit-vs-holdout
r = 0.76, split-half (even/odd days) r = 0.76, month-1 vs month-2 fitted profile r = 0.86
(mean |Δh| 0.13). **Data needed:** profile from the last 4 wk r = 0.96 vs 8 wk; 2 wk 0.83; 1 wk
0.69. 8-wk profile: 0.60–0.65 overnight (02–06 UTC) → 1.32–1.42 (16–19 UTC).

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-08-24 | bddp11 | natural | 90 d; in-sample (61 daily blocks) vs holdout (29), band 1.00±0.1 | E5 `band_table_e5_{insample,holdout}.csv`: k=1/8w in-sample lift **−0.182 [−0.302,−0.107]** (@op ΔTIR −2.7, Δt54 +0.52), holdout **−0.297** (ΔTIR −5.3, Δt54 +0.96); k=1/4w −0.160 / −0.241; k=0.5/8w in-sample −0.004 (ΔTIR +1.2, Δt54 +0.03) → holdout **−0.069** (Δt54 +0.32) | **WORSE — fails even in-sample, and degrades further on holdout.** Pre-loading needs for habitual meal hours makes lows on the days/hours the meal doesn't come (the rise is present on only ~2/3 of days), and the 0.6× overnight cut makes highs. The residual ICE profile is a *meal* shape, not a basal-shaped need; a basal/ISF schedule is the wrong actuator for it |
| 2026-08-24 | bddp11 | natural | data-needed (k=1): 8w / 4w / 2w / 1w fits | holdout lift −0.297 / −0.241 / −0.317 / −0.278; in-sample −0.182 / −0.160 / −0.217 / −0.249 (Δt54 in-sample +0.52 / +0.39 / +0.76 / +1.00) | **WORSE at every history length**; shorter history = more lows (noisier profile), but even the 8-week profile loses. Not a data-quantity problem |

## C13 · Basal × ISF decoupling
`--candidate-basal-rate-multiplier` × `--candidate-sensitivity-multiplier`, CR fixed. ns3
30 d grid (`runs/2026-07-18-ns3-basal-isf-grid`): max lift +0.056 at B1.00/S0.80; every
"more basal" cell negative. Small real band, never followed on other donors.

## C14 · Autosens term
`--candidate-autosens-gain/-min/-max/-window-min`: scale ISF by (1 − gain·avg(BG−target)) over
a multi-hour window. Built (`c8058d0`), off by default, never swept. Learned-lite (hours of
memory, no fitting) — a natural "data-needed" baseline for C12.

## C15 · RC window knobs
`--candidate-rc-retrospection-min`, `--candidate-rc-effect-duration-min` (rc-mom-panel,
6 donors, 2026-08-04): retro270 rank 2.33 (bddp06 +0.131), retro90 uniformly slightly below
IRC, **dur120 harmful** (bddp01 −1.015). None beats plain IRC.

## C16 · Manual-bolus rec scaling
`--candidate-manual-bolus-rec-scale` (user2, 2026-07-14/16): lift +0.185 on the ISF dial →
+0.036 on insulin-needs. The canonical "lift evaporates under a fair baseline" case. Not an
unannounced-meal lever (needs a bolus to scale).

## C17 · oref as candidate engine
`--candidate-openaps …`. All surviving oref work is fidelity reproduction (orefuser/orefuser2);
UAM/SMB ablation flags exist (`bc52ede`) but only a single divergence case study survives —
no frontier number. Cross-engine: user1 90 d `iob_cross54_possum` 8.6 (Loop) vs 41.7 (OAPS).

## C18 · Asymmetric standard RC
`--candidate-asymmetric-std-rc --candidate-irc-drop-scale D --candidate-irc-rise-scale R`
(added 2026-08-24: `StandardRetrospectiveCorrection(dropGainScale:riseGainScale:)`, wired
through `EvalConfig.asymmetricStandardRC`). Scales the single 30-min discrepancy by R when
positive (unexplained rise) / D when negative before the 60-min projection. Motivation: the
rise-cut is the active part of aIRC (C01), and 9/11 donors deploy *standard* RC — this gives
them the mechanism without the IRC hook. Causal by construction (same inputs as deployed RC).
**Identity 2026-08-24:** new binary vs old on std ×1.00 max|Δcounter| = 0.0; flag on with
D=R=1 vs std = 0.0.

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-08-24 | bddp11 | natural | 90 d, band 1.00±0.1 | E3: R ∈ {0.3, 0.5, 0.7} (D=1), D1.5/R0.5 | running |
| 2026-08-24 | bddp11 | natural | 90 d, band 1.00±0.1 | E3 `band_table_e3.csv`: R0.7 lift −0.007 [−0.018,+0.010] (@op ΔTIR −2.6, Δt54 −0.14); R0.5 −0.013; D1.5/R0.5 −0.009 (drop-boost inert: identical to R0.5 at op); R0.3 −0.022 (ΔTIR −6.1) | **NEUTRAL — a gentler dial.** Unlike aIRC, the standard-RC rise-cut has no integral memory to shape; it just scales the correction |
| 2026-08-24 | bddp11 / 10 / 01 / 09 | natural | 2 mo, op ×1.00 | E3 multi-donor: R0.7 mean −0.003, R0.5 −0.007, D1.5/R0.5 −0.005; all NEUTRAL (bddp11 D1.5/R0.5 WORSE −0.020) | **NEUTRAL / dial-like across 4 donors** — closed |

## O2 · Carb-foreknowledge oracle
Entries visible 30 min early (bddp07, `runs/2026-08-22-eval-review/b07o2_m*.json`). **+6–8 TIR
at ≈0 t54 through the gentle end** (m0.7 55.6 vs 47.8; m0.8 77.5 vs 70.5), converging near ×1,
slightly worse at ×1.2 — and a *negative* whole-sweep mean lift (−0.043), which is what
forced the operating-band rule. Headroom for the dose-more family is real and large.

## C19 · Learned causal 60-min ICE forecaster
`runs/2026-08-24-unannounced/fit_ice_forecaster.py` → `--candidate-forecast-offset-csv`. Per-patient
GradientBoosting (300 trees, depth 3) predicting y(t) = Σ ICE over the next 60 min from strictly
causal features: trailing ICE means (10/30/60/120/180 min), BG, BG deltas (15/30/60), IOB, RC and
momentum marginals, hour-of-day (sin/cos), day-of-week, minutes since last <70. The forecast
offset is pred − (RC + momentum marginal already in Loop's forecast), clipped [−60, +100]; a
half-strength variant (×0.5) hedges false positives. **Leakage audit:** fit on t < 2026-07-08 only;
features are trailing windows ending at t; holdout 07-08→08-06 scored separately. Note the July
2026 precedent (`analysis/loopeval_analysis/ice_prediction.py`): a similar rhythm-level predictor
(Spearman 0.4–0.5) did not convert to a therapy win under the old scoring — this re-tests it under
band scoring with the oracle ceiling for context.

bddp11 skill: in-sample R² 0.30 / Spearman 0.56; **holdout R² 0.16 / Spearman 0.40** — versus
Loop's own RC+momentum extrapolation at R² −0.16 / Spearman 0.20 on the same target. Top features:
hour-of-day, BG, ICE last 10 min, ICE last 120 min.

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-08-24 | bddp11 | natural | 90 d; in-sample (61 daily blocks) vs holdout (29), band 1.00±0.1 | E8 `band_table_e8_{insample,holdout}.csv`: **fc60** in-sample −0.016 [−0.086,+0.033] (@op ΔTIR +4.0, Δt54 +0.44) → holdout **−0.316 [−0.679,−0.114]** (ΔTIR −0.5, Δt54 +1.35); **fc60h** (×0.5) in-sample +0.014 (ΔTIR +2.5, Δt54 +0.07) → holdout −0.038 [−0.079,+0.000] (Δt54 +0.33) | **WORSE / NEUTRAL-trending-worse on holdout.** Holdout R² 0.16 is nowhere near enough: the false-positive pressure makes lows faster than the true-positive pressure buys TIR. Same verdict as the July predictor, now with the skill requirement quantified (see O1 degraded oracles): a 60-min ICE forecaster must reach **R² ≳ 0.7 with unbiased errors** before an additive forecast offset pays |

## C20 · Post-low-gated RC rise-cut
`--candidate-postlow-rc-rise-scale S --candidate-postlow-window W --candidate-postlow-rc-bg-max B`
(added 2026-08-26). Corner-gated version of the rise-cut: only within W minutes of a <70 sample
AND while BG < B does standard RC scale its positive (unexplained-rise) discrepancy by S; above B
the high is treated as real and RC is normal; no gate → identical to std. Motivation — the corner map
(`runs/2026-08-24-unannounced/corner_map.py`, corner_map.csv): on bddp11 the post-low re-dose class is
40 % of severe-low minutes and the post-low rebound highs are the largest high class (2.4–2.8 % of
time >250); the rebounds are full unannounced meals (implied 90–300 g, median 157 g), Loop's first
bolus comes ~40 min after the nadir at BG ≈ 106 on RC/momentum projection, and the second low lands
when absorption ends with 2–5 U still on board. The blanket post-low ISF-mult (C10) lost 3.5–8 TIR
because it also damped the *real* high; this gate releases at B so the high still gets corrected.

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-08-26 | bddp11 | natural | 90 d, band 1.00±0.1 | E9 `band_table_e9.csv`: **(0.5,720,180) lift +0.014 [+0.001,+0.029], dom 1.00 (lo 0.60); @op ΔTIR −0.4 [−0.6,−0.3], Δt54 −0.05 [−0.10,−0.01], Δt70 −0.22**; (0,360,140) +0.007 [+0.002,+0.014], dom 0.60; (0.5,360,180) +0.007 [−0.001,+0.019]; (0,360,180) +0.007 [−0.007,+0.025] (ΔTIR −1.0) | **IMPROVES** (two settings clear the CI; longer window better, releasing at 180 better than cutting to zero). Small — recovers ~⅓ of the corner's t54 ceiling (0.14) — but a genuine corner-gated lift, cheaper in TIR than aIRC (−0.4 vs −0.9) for ~⅔ of its t54 effect |

## O1 · Future-ICE forecast oracle (headroom bound, not deployable)
`--candidate-forecast-offset-csv` with offset(t) = Σ true ICE over the next H min − (RC + momentum
marginal contributions already in Loop's forecast), from the std ×1.00 trace
(`hourly/b11_oracle{60,360}.csv`). A perfect H-minute forecast of the exogenous physiology
(every unannounced meal, exercise, sensor drift) applied as a constant shift of the predicted
trajectory (optimistic: also lifts the predicted min). Bounds the value of ALL forecast /
meal-detection work on a hands-off donor.

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-08-24 | bddp11 | natural | 90 d, band 1.00±0.1 | E7 `band_table_e7.csv`: **H=60 lift +0.314 [+0.224,+0.408], dom 1.00 (lo 1.00); @op ΔTIR +10.0 [+8.7,+11.2], Δt54 −0.31 [−0.63,−0.10], Δt70 −1.56**. H=360: −15.7 (Δt54 +26) — INVALID as built: a constant +127 mg/dL mean shift makes Loop dose 6 h ahead of meals; the constant-shift approximation only holds for short horizons | **Perfect 1-h exogenous forecast ≈ +10 TIR at fewer lows on the hardest hands-off donor** — the information ceiling is ~500× the best deployable mechanism (aIRC +0.019). The unannounced-meal problem on hands-off donors is a *forecasting* problem; next: how much of that 1-h ICE is causally predictable per patient (C19) |
| 2026-08-24 | bddp11 | natural | holdout 07-08→08-06 (29 daily blocks) | E8 value-vs-skill: perfect ×1 lift +0.237 (@op ΔTIR +9.7, Δt54 0.00); **perfect ×0.5 +0.133 [+0.095,+0.173] (ΔTIR +3.9, Δt54 −0.09)**; noise-matched **R²=0.5: −0.705 (ΔTIR +4.3, Δt54 +2.18)**; R²=0.25: −7.2 (Δt54 +12) | **A half-strength perfect forecast still dominates; a half-R² noisy one is already harmful.** Value of information is bounded by error *variance*, not signal: pre-dosing on wrong positives makes lows. Skill bar for an additive 60-min offset ≈ R² ≥ 0.7 |

## O3 · Perfect retrospective-ISF oracle
Planned in REVIEW Part 3, never run; bounds all adaptation/autotune (C12/C14).
