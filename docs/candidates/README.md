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
| [C20](#c20-post-low-gated-rc-rise-cut) | Post-low-gated RC rise-cut (corner candidate) | pull-back, gated | scored (7 beds) | **IMPROVES on 3/7 beds** at (0.3,720,180) — b11_90d +0.019, bddp03 +0.014 (TIR up AND t54 down at op), bddp08 +0.008 — and positive on all 7 (mean ≈ +0.02); best multi-donor result so far |
| [C21](#c21-fast-rise-gated-rc-rise-cut) | Fast-rise-gated RC rise-cut (meal-rise-stacking corner) | pull-back, gated | scored (bddp11) | NEUTRAL (+0.007 best) — closed |
| [C22](#c22-σ-widened-lower-forecast-band) | σ-widened lower forecast band (volatility-aware min guard) | pull-back, state-gated | scored (7 beds) | **IMPROVES on hands-off donors** (bddp11 90 d +0.025, bddp11 +0.022, bddp09 +0.018); with the COB=0 gate the announcer harm disappears (bddp03/08 ≈ 0) |
| [C23](#c23-calm-high-licence) | Calm-high licence (AF ×2 when BG ≥ 180 AND σ5 ≤ donor median) | dose-more, state-gated | scored (7 beds + control) | **IMPROVES on 6/7 beds at zero lows cost** (bddp01 +1.4 TIR, bddp09 +0.8, bddp11 +0.6/+0.7, bddp10/08 +0.2; bddp03 NEUTRAL); no-gate control is dial-like → σ is the information. Strongest multi-donor result in the program |
| [C24](#c24-stack-c22--c23-disjoint-state-gates) | **Stack**: COB-gated σ band + calm-high licence (+ post-low RC rise-cut) | pull-back + dose-more, state-gated | scored (10 beds) | **stk3 multi-donor mean +0.022 [lo +0.001], 5 IMPROVES / 0 WORSE**; stk +0.015, 5/0 on 10 beds; +0.6…+2.1 TIR in unannounced-meal windows on 4/5 hands-off beds |
| [C25](#c25-cob-gate-on-the-calm-high-licence) | COB gate on the calm-high licence | dose-more, state-gated | scored (3 beds) | **Removes C23's only lows cost and is inert elsewhere** (bddp03 Δt54 +0.10 → −0.01; bddp11 gated == ungated to every digit) — adopt as C23's standard form |
| [C26](#c26-calm-high-licence-trend-gated) | Calm-high licence, trend-gated (only flat-or-rising highs) | dose-more, state-gated | scored (3 beds) | **WASH** — removes the descent cycles and ~15 % of the TIR gain, no better lows exchange rate; the descent correlation was not causal |
| [M1](#m1--method-a-mechanism-can-only-beat-an-expensive-dial) | *Method*: a mechanism only beats an EXPENSIVE dial | — | — | every `:ncnb` verdict scored at ×1.00 is provisional — the dial pays 83–434 TIR/t54 there vs 3 at a real operating point |
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

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-08-26 | bddp11 | natural | 90 d, band 1.00±0.1 | E11: RC effect duration 40 min: lift −0.019 [−0.035,+0.002] (@op ΔTIR −4.4, Δt54 −0.14); 30 min running | **NEUTRAL — a gentler dial.** Shortening the projection removes real near-term signal along with the overshoot (the 5–60 min regime trends, H 0.71); the win from discounting the projection is state-dependent (C20/C22), not a constant |
| 2026-08-26 | bddp11 | natural | 90 d | E11: RC effect duration 30 min: **WORSE** −0.029 [−0.043,−0.011] (ΔTIR −6.3) | closed |

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
| 2026-08-26 | bddp11 | natural | 90 d, band 1.00±0.1 | E9b `band_table_e9b.csv` gate grid: **(0.3,720,180) +0.019 [+0.006,+0.035]** (@op ΔTIR −0.7, Δt54 −0.07 — aIRC's t54 effect at 20 % less TIR cost); **(0.5,720,140) +0.013 [+0.006,+0.021], dom 1.00 (lo 0.80), @op ΔTIR −0.1 [−0.3,+0.0], Δt54 −0.04** (nearly free); (0.5,1440,180) = (0.5,720,180) +0.014 (window saturates at 12 h) | **IMPROVES** across the grid; stronger cut (0.3) buys more t54 for more TIR, lower release (140) makes it nearly free. Tunable along a cheap front |
| 2026-08-26 | bddp11 / bddp10 | natural | 2 mo, op ×1.00, 9 blocks | E9 `cohort_band_e9.csv`: (0.5,720,180) +0.020 [−0.002,+0.040] / +0.002 [−0.005,+0.008]; (0,360,140) +0.007 / +0.002; mean 0.011; aIRC 0.018 / 0.014 | **NEUTRAL** on 2-mo beds (bddp11 just misses; bddp10 has almost no post-low lows — the gate is inert outside its corner, by design). Needs a ≥90 d bed per donor and donors with the corner |
| 2026-08-26 | bddp03 / bddp08 / bddp05 / bddp06 | natural | 2 mo, op ×1.05 / 1.05 / 1.15 / 1.20, 9 blocks | E9c `cohort_band_e9c1.csv`, `_e9c2.csv` — (0.3,720,180): bddp03 **+0.014 [+0.006,+0.026]** (@op **ΔTIR +0.3, Δt54 −0.07** — better on both axes); bddp08 **+0.008 [+0.002,+0.012]** (ΔTIR +0.4, Δt54 −0.08); bddp05 **+0.026 [+0.004,+0.045]** (ΔTIR +0.1, Δt54 −0.07); bddp06 +0.020 [−0.047,+0.142] (band under-covered, extension running). (0.5,720,140): all NEUTRAL-positive | **IMPROVES on 3 of 7 beds, positive mean on every bed** — after extending bddp05/06 sweeps to ×1.30 so their bands are covered (`cohort_band_e9c2.csv`): bddp05 → NEUTRAL +0.015 [−0.004,+0.031]; bddp06 +0.051 [−0.030,+0.206] (aIRC IMPROVES on both; (0.5,720,140) IMPROVES on bddp06 +0.088). CI-clearing: b11_90d, bddp03, bddp08. First mechanism with a positive band lift on every bed tried; it *raises* TIR at op on the announcer beds (03/08) while cutting t54 — it removes only the corrections that were going to land after absorption. Announcer-bed ops sit at the top of the sweep (×1.15–1.20), so their verdicts move with reference extent — treat as supporting, not headline |

## C21 · Fast-rise-gated RC rise-cut
`--candidate-rise-gate-slope X --candidate-rise-gate-rc-rise-scale S --candidate-rise-gate-bg-max B`
(added 2026-08-26). Same actuator as C20, different gate: while the trailing 15-min slope ≥ X mg/dL/min
AND BG < B, standard RC scales its positive discrepancy by S. Targets the meal-rise-stacking low class
(corner map: bddp11 195 min, bddp08 200, bddp05 100, bddp03 70 of severe-low minutes) — corrections stacked
during an unannounced rise that land after absorption ends.

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-08-26 | bddp11 | natural | 90 d, band 1.00±0.1 | E10 `band_table_e10.csv`: (1.5,0.5,180) +0.007 [−0.001,+0.014]; (2,0.5,180) +0.004; (2,0,180) +0.001; (2,0.5,140) −0.000 | **NEUTRAL** — the gate is active only during the rise itself (~minutes), too brief to prevent the correction stack that lands hours later; the post-low window (C20) is the better gate for the same actuator. Closed |

## C22 · σ-widened lower forecast band
`--candidate-sigma-band-k k` (+ `-horizon-min 60`, `-taper-min 120`, `-h 0.71`, `-lambda 0.875`,
`-noise 1.4`), added 2026-08-26 from *The Shape of Glucose* (artifact 2026-08-25): σ5 = causal EWMA std
of the 5-min increment of the candidate's own glucose (26-min half-life, variance floored at 2·noise²);
each predicted point at τ min is lowered by k·σ5·(τ/5)^0.71 out to 60 min, tapering to 0 by 120 min.
The eventual BG is untouched — only the predicted *minimum* sees the volatility, so the min-guard /
suspend logic binds earlier in volatile states (the artifact's view 15: at matched level and trend, the
top-σ tercile carries 3.8× the 30-min hypo rate). "Modify the forecast, not the output." Laplace
quantile is folded into k. Causal by construction.

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-08-26 | bddp11 | natural | 90 d, band 1.00±0.1 | E11 `band_table_e11.csv`: **k=1 lift +0.025 [+0.009,+0.042], dom 1.00 (lo 0.60); @op ΔTIR −1.1 [−1.5,−0.7], Δt54 −0.07 [−0.12,−0.04], Δt70 −0.63**; k=2 −0.004 [−0.051,+0.057] (ΔTIR −9.0, Δt54 −0.31 — far too wide: median σ5 on this donor is 6.8 mg/dL/5 min, so k=2 lowers the 60-min point by ~80 mg/dL); k=3 −0.368 (ΔTIR −24.8) | **IMPROVES at k=1** — the largest single-donor band lift of any deployable mechanism so far (aIRC +0.022, C20 +0.019); k=0.5 and multi-donor running |
| 2026-08-26 | bddp11 | natural | 90 d, band 1.00±0.1 | E11b: **k=0.5 lift +0.009 [+0.002,+0.017], dom 1.00 (lo 0.60); @op ΔTIR −0.1 [−0.2,+0.0], Δt54 −0.03 [−0.06,−0.00]** | **IMPROVES, nearly free** — k is the width of the front: k=0.5 costs nothing, k=1 buys the full −0.07 t54 for −1.1 TIR |
| 2026-08-26 | bddp11 / 10 / 01 / 09 / 03 / 08 | natural | 2 mo, op ×1.00 (03/08: ×1.05), 9 blocks | E11 `cohort_band_e11.csv`, `_e11b.csv` — k=1: bddp11 **+0.022 [+0.001,+0.039]**, bddp09 **+0.018 [+0.009,+0.025]** (t70 axis), bddp10 +0.011 [−0.007,+0.029], bddp01 −0.004 (no lows to remove), **bddp03 −0.032 [−0.071,+0.001], bddp08 −0.030 [−0.043,−0.014] WORSE** (ΔTIR −3.5, Δt54 −0.40 — a gentler dial). k=0.5: bddp11 +0.006, bddp10 +0.014 IMPROVES; bddp03 −0.025 (Δt54 **+0.23**), bddp08 −0.008 WORSE | **Class-dependent: IMPROVES on hands-off donors with lows (bddp11, bddp09, bddp10 at k=0.5), inert where there are no lows (bddp01), WORSE on announcers (bddp03/08)** — on an announcer the widened lower band fires during the volatile *meal* rise and holds back meal coverage, and on bddp03 it even adds lows (the delayed correction lands later). Deployable only with a gate on announced carbs (COB = 0) or as a hands-off-only feature |
| 2026-08-26 | bddp03 / bddp08 / bddp11 | natural | 2 mo | E11e `cohort_band_e11e.csv` — **`--candidate-sigma-band-cob-gate`** (band only when COB = 0): k=1 bddp03 +0.002 [−0.003,+0.006] (was −0.032), bddp08 +0.005 [−0.002,+0.011] (was −0.030), bddp11 **+0.022 [+0.001,+0.040]** (unchanged) | **Gate works: announcer harm removed (NEUTRAL ≈ 0), hands-off lift intact.** The deployable form of C22 is k≈1 with the COB gate |

## C23 · Calm-high licence
`--candidate-calm-high-af-scale s` (+ `-bg 180`, `-sigma-max 3.5`): when BG ≥ 180 AND σ5 ≤ σmax, the
automatic-bolus application factor is scaled by s (capped at 1). The artifact's licence direction: a calm
high rarely becomes a low (high-σ highs are 2.6× more likely to end <70 within 2 h), so the fixed 0.4 AF
is most conservative exactly there. Addressable window is modest (3.6 % of samples median, 6–8 % for
runs-high donors). Dose-more, state-gated — the goal's "know when to dose more aggressively" lever.

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-08-26 | bddp11 | natural | 90 d, band 1.00±0.1 | E11 `band_table_e11.csv`: σmax 3.5 / 2.5 ≈ inert (+0.002 / +0.000 — this donor's σ5 is high: p33 5.5, p50 6.8, only 1.9 % of high samples are ≤3.5). At the donor's own percentiles: **s=2.0 @ σmax 5.5 (p33): +0.008 [+0.003,+0.012], dom 1.00 (lo 0.80); @op ΔTIR +0.3 [+0.1,+0.4], Δt54 +0.00 [−0.01,+0.01]**; s=1.5 @ 6.8 (p50): +0.008 [+0.004,+0.012], ΔTIR +0.4, Δt54 −0.01; s=1.5 @ 5.5: +0.002 | **IMPROVES — the first dose-MORE mechanism to clear the CI: pure TIR gain at zero lows cost.** Small on this volatile donor (addressable window 0.5 % of samples at p33); σ threshold must be donor-relative — per-donor percentiles (`sigma_pcts.csv`) sweep running on 7 beds |
| 2026-08-26 | bddp11 | natural | 90 d, band 1.00±0.1 | E11c (donor percentiles from `sigma_pcts.csv`): **s=2.0 @ σmax = donor p50 (6.7): +0.014 [+0.008,+0.020], dom 1.00 (lo 0.80); @op ΔTIR +0.6 [+0.4,+0.8], Δt54 −0.01 [−0.02,−0.00]**; s=1.5 @ p50 +0.009 [+0.005,+0.013] (ΔTIR +0.3); s=2.0 @ p33 +0.007 | **IMPROVES — widening the calm gate to the median doubles the gain, still at zero lows cost.** s=3 @ p50 and s=2/2.5 @ p67 queued |
| 2026-08-26 | bddp11 / bddp10 / bddp01 | natural | 2 mo, op ×1.00, 9 blocks | E11c `cohort_band_e11c.csv` — s=2 @ p50: bddp11 **+0.013 [+0.005,+0.020]** (@op ΔTIR +0.7, Δt54 −0.01); bddp10 **+0.006 [+0.002,+0.011]** (+0.2, +0.02); **bddp01 +0.012 [+0.003,+0.023] (@op ΔTIR +1.4 [+1.0,+1.8], Δt54 0.00)**; s=2 @ p33 and s=1.5 @ p50 IMPROVES on all three as well | **IMPROVES on every hands-off bed (4/4 incl. 90 d), zero lows cost, largest on the runs-high donor** — the goal's payoff target |
| 2026-08-26 | bddp09 / bddp08 / bddp03 | natural | 2 mo, op ×1.00 / 1.05 / 1.05 | E11c `cohort_band_e11c2.csv`, `_e11c3.csv` — s=2 @ p50: bddp09 **+0.011 [+0.007,+0.017]** (@op ΔTIR +0.8, t70 axis, Δt70 +0.01); bddp08 **+0.008 [+0.003,+0.012]** (+0.2 TIR, Δt54 −0.01); bddp03 NEUTRAL +0.005 [−0.019,+0.030] (ΔTIR −0.2, **Δt54 +0.10**) | **IMPROVES on 6 of 7 beds; NEUTRAL on the heavy announcer** (its highs are post-meal with insulin on board, so the extra AF adds lows there). Multi-donor mean band lift ≈ +0.010, ΔTIR@op +0.2…+1.4, Δt54 ≈ 0 everywhere but bddp03. Gate on COB = 0 would exclude the announcer case |
| 2026-08-26 | bddp11 | natural | 90 d, band 1.00±0.1 | E11d gate width: **s=2.5 @ p67: +0.027 [+0.014,+0.039], dom 1.00 (lo 0.80); @op ΔTIR +1.4 [+1.0,+1.9], Δt54 +0.00 [−0.02,+0.02]**; s=2 @ p67 +0.024 [+0.016,+0.031] (+1.1 TIR); s=3 @ p50 +0.012 (+0.7); s=2 @ p50 +0.014 (+0.6) | **IMPROVES — widening the σ gate (p33→p50→p67) is worth more than raising the scale; still zero lows cost.** Largest lift of any deployable mechanism in the program. Control below |
| 2026-08-26 | bddp11 | natural | 90 d, band 1.00±0.1 | E11f **CONTROL** `band_table_e11f.csv` — same AF boost with NO σ gate (σmax ∞): s=2 lift +0.009 [−0.004,+0.026] (@op ΔTIR +2.5, **Δt54 +0.11**); s=2.5 +0.007 [−0.010,+0.026] (ΔTIR +2.8, **Δt54 +0.22**); s=2.5 @ p90 +0.020 [−0.000,+0.039] (ΔTIR +2.0, Δt54 +0.09) | **NEUTRAL / dial-like without the gate.** The σ gate is what converts "more AF above 180" from a hotter dial into a dominant point: the calm-high subset takes the extra insulin without lows, the volatile subset pays for it in lows. Sweet spot ≈ donor p67; p90 already leaks lows |
| 2026-08-26 | 6 beds (bddp11/10/01/09/08/03) | natural | 2 mo | E11g `cohort_band_e11g{1,2,3}.csv` — s=2 @ p67: bddp11 **+0.022 [+0.012,+0.031]** (+1.2 TIR), bddp09 **+0.015 [+0.009,+0.022]** (+1.4), bddp08 **+0.009** (+0.3); bddp10 +0.002, bddp01 −0.003 (ΔTIR +2.2 but Δt54 +0.01), bddp03 +0.007 (Δt54 +0.06) NEUTRAL. s=2.5 @ p67: bddp11 +0.031 (+1.7 TIR), bddp09 +0.016 (+1.9), bddp08 +0.010; bddp01 −0.045 (Δt54 +0.03), bddp03 Δt54 +0.18. **Control s=2 no gate: NEUTRAL on 4/6** (Δt54 +0.03…+0.10), IMPROVES only on bddp09 (no lows to add) and bddp08 (Δt54 +0.07, borderline) | **Deployable default = s=2 @ donor p50: IMPROVES on 6/7 beds and never adds lows. p67 buys ~2× the TIR on donors whose highs are lows-free (bddp11/09/08) but starts leaking t54 on bddp01/bddp03 — a per-patient tune, not a default.** The gate, not the scale, is what separates this from the dial (control) |

## C24 · Stack: C22 + C23 (disjoint state gates)
`stk` = `--candidate-sigma-band-k 1.0 --candidate-sigma-band-cob-gate` **+**
`--candidate-calm-high-af-scale 2.0 --candidate-calm-high-sigma-max <donor p50 σ5>`.
`stk3` adds C20 (`--candidate-postlow-rc-rise-scale 0.3 --candidate-postlow-window 720`).
Rationale: the three gates fire on **disjoint states** — C22 only when the forecast is volatile
(and COB = 0), C23 only when BG ≥ 180 AND σ5 ≤ the donor median (calm), C20 only within 12 h of a
low while BG < 180. If they are genuinely orthogonal the band lifts should be ≈ additive; if the
stack under-performs the sum, they are competing for the same lows/highs and only one is real.
Each component's solo arm is already scored on the same beds, so the decomposition is free.

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-08-27 | bddp11 | natural | 2 mo, op ×1.00, 9 blocks | E12 `bddp11/band_points_e12pre.csv`: **stk +0.029 [+0.005,+0.050]**, dom 1.00 (@op ΔTIR −0.5 [−1.0,−0.1], Δt54 −0.08 [−0.14,−0.02], Δt70 −0.47); **stk3 +0.055 [+0.008,+0.092]**, dom 1.00 (@op ΔTIR −1.1, Δt54 **−0.24** [−0.43,−0.07], Δt70 −0.70). Components on the same bed: sb1cob +0.022 (ΔTIR −1.3, Δt54 −0.08), ch2p50 +0.013 (ΔTIR +0.7), C20 +0.019 (b11_90d) | **IMPROVES — and close to ADDITIVE.** stk3 +0.055 vs the component sum 0.054; stk +0.029 vs 0.035. The gates really are disjoint. The useful part is the *composition*: C23 pays back C22's TIR cost (−1.3 → −0.5 at the same Δt54 −0.08), and adding C20 triples the lows effect (Δt54 −0.24) for −1.1 TIR — a better exchange rate than any single mechanism. Remaining beds running |
| 2026-08-27 | b11_90d / bddp09 | natural | 90 d / 2 mo, op ×1.00 | E12: b11_90d **stk +0.032 [+0.012,+0.057]** (@op ΔTIR −0.4, Δt54 −0.07), **stk3 +0.045 [+0.012,+0.087]** (−1.0, **−0.17**) vs components sb1cob +0.025 / plrc3 +0.019 / ch2p50 +0.014 (Σ 0.058). bddp09 (t70 axis) **stk +0.014 [+0.009,+0.019]**, **stk3 +0.024 [+0.008,+0.041]** | **IMPROVES on both.** `sb1cob == sb1` exactly on b11_90d — the COB gate is inert on a hands-off donor (gate identity check) |
| 2026-08-27 | bddp10 / bddp01 | natural | 2 mo, op ×1.00 | E12: bddp10 stk +0.005 [−0.010,+0.027], stk3 +0.004 (@op ΔTIR −0.7); bddp01 stk +0.003 (@op **ΔTIR +0.8 at t54 0**), stk3 −0.005, and ch2p50 alone **+0.012 (+1.4 TIR)** | **NEUTRAL-positive on both — the two beds with little or no lows burden.** Restates the class rule: **C23 is the universal component** (the only one that pays on lows-free beds), **C22/C20 pay only where there are lows to trade**. Deployable default: C23 always, + C22/C20 where t54 ≳ 0.3 % |
| 2026-08-27 | b11_90d / bddp11 / bddp09 / bddp01 / bddp10 | natural | **meal windows** (`meal_window.py`), dial retuned to matched whole-window lows | ΔTIR in unannounced-meal windows [−30, +300 min]: **stk +0.79 / +1.23 / +1.83 / +1.23 / −0.11**; **stk3 +1.13 / +2.06 / +1.83 / +0.57 / −0.84**; ch2p50 +0.58 / +1.00 / +0.37 / +0.21 / −0.39. Meal-window Δt54 flat (−0.04…+0.02), Δ>250 −0.4…−1.4, peak −0.3…−2.0 mg/dL | **Improves meal-window glycemia on 4 of 5 beds** at unchanged lows — the goal's second criterion. bddp10 (smallest lows burden) is the exception |
| 2026-08-27 | bddp03 / bddp08 (announcers) | natural | 2 mo, op ×1.05 | E12 `cohort_band_e12_ann.csv`: bddp03 **stk3 +0.021 [+0.001,+0.047]** but dom 0.20 and @op Δt54 **+0.06**; stk/ch2p50 NEUTRAL with Δt54 **+0.10** (the heavy-announcer weakness of C23 — fixed by [C25](#c25-cob-gate-on-the-calm-high-licence)). bddp08 **stk3 +0.010 [+0.002,+0.018]** (Δt54 −0.11), **stk +0.007**, ch2p50 +0.008, plrc3 +0.008 | **IMPROVES on both for stk3**; on bddp08 every arm improves, on bddp03 only the RC rise-cut and the stack do |
| 2026-08-27 | bddp05 / bddp06 / bddp07 | natural | 2 mo, op ×1.15 / 1.20 / 1.00 | E12b `cohort_band_e12b.csv`: bddp05 **ch2p50 +0.039 [+0.027,+0.051] dom 1.00 (lo 1.00), @op ΔTIR +1.0, Δt54 −0.05** (largest single-bed C23 lift yet), stk +0.020, plrc3 +0.017, **sb1cob WORSE −0.012**; bddp06 ch2p50 +0.035, stk/sb1cob NEUTRAL (Δt54 +0.07); bddp07 all inert (ch2p50 exactly 0.000 — σ5 p50 3.5 and only 1.5 % of the record ≥180, so the gate never fires) | **Breadth confirmed for C23** (IMPROVES on both beds where it can fire, inert where it cannot). **C22 alone is NOT universally safe — WORSE on bddp05** |
| 2026-08-27 | **10 beds** (9 donors) | natural | 2 mo / 90 d | E12 consolidated `cohort_band_e12all.csv`, equal weight per bed: **stk3 (7 beds then) mean +0.022, CI-lo +0.001 — CORRECTED at 10 beds to +0.021, CI-lo −0.006, 6 IMPROVES / 0 WORSE**; **stk mean +0.015, 5/0 (10 beds)**; **ch2p50 mean +0.014, CI-lo +0.004, 8 IMPROVES / 0 WORSE, ΔTIR +0.48 at Δt54 +0.004**; C20 +0.020 (5 beds); sb1cob +0.006 with 1 WORSE | **CORRECTED (E14, 10 beds): only ch2p50's multi-donor mean lower CI clears zero** (stk3 read +0.001 on 7 beds, −0.006 once bddp05/06/07 were filled in; it keeps the most IMPROVES, 6/10, and no WORSE) — against previous program bests of aIRC +0.005 and C20 ≈ +0.02. C23 is the breadth mechanism, C20 the lows mechanism, C22 the one to gate per patient; stk3 gets both effects at once. stk3's row is 7/10 beds — E14 fills bddp05/06/07 |

## C25 · COB gate on the calm-high licence
`--candidate-calm-high-cob-gate` (added 2026-08-27, `EvalConfig.calmHighCobGate`): apply C23's
licence only while the candidate has no carbs on board. C23 IMPROVES on 8 of 10 beds and the one
place it costs lows is the heavy announcer — whose calm highs are *post-meal with the bolus still
working*, so the extra application factor stacks into insulin already committed. Same shape as the
announcer harm C22 had, so the same fix. **Identity 2026-08-27:** new binary with the flag OFF vs
the old binary, bddp03 ch2p50 ×1.00 — max|Δ| **0.0** on counter BG and candidate dose, 16,765 cycles.

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-08-27 | bddp03 (heavy announcer) | natural | 2 mo, op ×1.05, 9 blocks | E13 `cohort_band_e13_b03.csv`: ungated ch2p50 +0.005, @op ΔTIR −0.2, **Δt54 +0.10 [+0.00,+0.22]**, Δt70 +0.70 → gated **ch2p50cob +0.003, @op ΔTIR +0.1, Δt54 −0.01 [−0.02,+0.01]**, Δt70 +0.16 | **Gate works.** Lift stays NEUTRAL (small on this bed either way) but the lows cost is gone and ΔTIR flips positive. With it, **C23 has no bed on which it costs lows** — what a default needs. bddp08 + a bddp11 inertness check running |
| 2026-08-27 | bddp08 / bddp11 | natural | 2 mo | E13 `cohort_band_e13.csv`: bddp08 ch2p50 +0.008 (Δt54 −0.01) vs **ch2p50cob +0.007, Δt54 +0.00 [+0.00,+0.00]**; stk3 +0.010 = stk3cob +0.010. bddp11 **stkcob == stk and ch2p50cob == ch2p50 to every digit** | **Safe as a default: fixes the one harmful bed, inert everywhere else.** A hands-off donor has no COB, so the gate is a no-op by construction — the inertness is structural, not empirical luck. Adopt `--candidate-calm-high-cob-gate` as the standard form of C23 |

## C26 · Calm-high licence, trend-gated
`--candidate-calm-high-min-slope X` (added 2026-08-27, `EvalConfig.calmHighMinSlope`): require the
trailing 30-min glucose slope ≥ X mg/dL/min before licensing. Causal (candidate's own glucose).
**Measured motivation, not a theory** (`calmhigh_slope.py`): a steady 1 mg/dL/min fall is 5 mg/dL per
5 min, i.e. σ5 ≈ 5, which *passes* a donor-median σ gate — so "calm high" silently includes "high that
is already coming down". The licence fires on a falling BG on **31–56 %** of its cycles, and the
ordering across beds matches the verdicts exactly: bddp08:ncnb (WORSE) fires 56 % falling at median
slope −0.34, bddp03 natural (neutral, no harm) only 31 % falling at +0.08. Front-loading a correction
into a high that was already coming down lands the insulin after absorption ends — the same failure
C20 attacks from the other side.

| date | bed | regime | window | result | verdict |
|---|---|---|---|---|---|
| 2026-08-27 | bddp08:ncnb / bddp03:ncnb / bddp07:ncnb | announcement-suppressed | 2 mo, op ×1.00 | E15 `cohort_band_e15c.csv`: ch2p50 −0.032 WORSE → **ch2p50s0 −0.025 NEUTRAL but Δt54 +0.03 → +0.05**; bddp03 +0.009 → −0.001; bddp07 inert either way; stks0 −0.041 vs stk −0.035. 3-bed mean unchanged at −0.008 | **WASH — and the descent correlation was NOT causal.** The gate removes ~half the firing cycles and ~15 % of the TIR gain without improving the lows exchange rate; where it moves the lift it makes Δt54 *worse*. Recorded as a negative result; flag kept (identity max|Δ| 0.0 over 16,347 cycles, default off) |

## M1 · Method: a mechanism can only beat an EXPENSIVE dial
Not a candidate — a scoring correction that applies to every announcement-suppressed verdict in this
ledger, E4's UAM results included. Local exchange rate of the reference sweep (ΔTIR per point of t54)
at the scoring multiplier: **bddp08:ncnb at ×1.00 = 83→434** (501/261/192 below it), against
**bddp08 natural at ×1.05 = 3** and **bddp11 at ×1.00 = 18**.
bddp08:ncnb at ×1.00 is **28.9 % TIR** — nowhere near an operating point; its sweep does not reach the
elbow until ×1.40–1.50, where the rate falls to 3–4. C23 buys +1.5 TIR for +0.03 t54 there, an
exchange rate of 50 — good in absolute terms and still a *loss* against a dial paying 83–434.
**So E12c's "inversion" is not evidence that the licence fails for unannounced meals.** It is evidence
that scoring a suppressed bed at its *announced-era* multiplier pits a mechanism against the dial in
its cheap regime. Someone who stopped announcing would retune toward the elbow. E16 re-scores the
three ncnb beds at ×1.20–1.70. Until then, treat every `:ncnb` verdict at ×1.00 as provisional.

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
