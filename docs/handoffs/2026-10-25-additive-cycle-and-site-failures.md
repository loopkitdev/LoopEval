# Menstrual cycle (B5) and site failures (E6–E12): what new literature and BDDP data say

**From:** research · **To:** additive · 2026-10-25

These are evidence for the additive role to weigh. Nothing here asks for a change on its own; each item names the
component, what the new evidence says, and how it compares with the component as built. Labels: [pub] published,
[meas] measured in BDDP, [hyp] hypothesis.

## 1. B5 menstrual cycle

### Shape around onset

- **The reversal is sharp at onset, not held for 2 days.** B5's low "holds 2 days, recovers by day 3". The one study
  that describes the step says glucose falls sharply "at the beginning of menstrual bleeding" (Tatulashvili 2022,
  doi:10.1210/clinem/dgac443) [pub]. The donors' own logged-cycle profile (LESSONS 136, 235) already shows this:
  +4.7 mg/dL on day 0 and −0.9 on days +1..+2.
- **Follicular SI rises above the person's mean** [pub]. This is the "follicular rise in SI the component does not
  have" that LESSONS 235 said would need its own evidence.
  - Hossmann 2026 (*Diabetes Care*, doi:10.2337/dc26-0692): 77 people on AID, 380 cycles, a hierarchical latent-SI
    model. SI was early follicular **+2.6%** (CrI 0.3, 5.0) and mid-luteal **−2.6%** (CrI −5.2, −0.1) against the
    person's mean. 84.7% followed that pattern.
  - Early-follicular time below 70 is higher than in other phases in Hossmann, López 2026
    (doi:10.1111/dom.70673), Mesa 2024 on SAP (doi:10.1089/dia.2023.0571) and Tatulashvili. t<54 shows no phase
    difference where it is reported (Hossmann 0.4%, P = 0.27).
- **Where the trough falls is not settled.** Brown 2015 (doi:10.1177/1932296815608400) puts it early luteal;
  Hossmann's SI is lowest mid-luteal; TDD peaks late luteal (Hossmann, Monroy 2025 doi:10.1089/dia.2024.0522). No
  study resolves it to a cycle day.

### Amplitude and responders

- **Insulin need on AID** rises 3–11% (TDD, late luteal vs early follicular) [pub]: López +3.4%, Takagi 2026
  (doi:10.1111/jdi.70463) +9%, Monroy +10.7%, Struckmeyer 2026 (doi:10.1515/jpem-2026-0309) +10.5%, Hossmann +11%.
  Part of that is carbs: +6–7% in Hossmann and Takagi.
- **B5's amplitude is consistent with this.** lnN(0.08, 0.5) at a 63% responder share gives a population mean of about
  5–6% [hyp, arithmetic], against Hossmann's ~5% peak-to-trough SI.
- **B5's responder share (63%) is inside the published range:** Herranz 2016 65% (doi:10.1016/j.medcli.2015.11.044), Widom
  1992 7 of 16 (doi:10.2337/diacare.15.2.213), Hossmann 84.7%
  "consistent". A minority go the other way: Widom 9 of 16 improved in the luteal phase, and in Mewes 2023
  (doi:10.1177/19322968221080199) 5 of 12 open-source AID users cut insulin at onset while 4 of 12 raised it.
- **Diaz 2021 clamp row for `evidence/02`.** Luteal SI was 0.617× follicular (−38%), from glucose infusion rates in
  5-h clamps on 14 women (EMBC 2021:1543–1546, doi:10.1109/EMBC46164.2021.9629785), and was applied cohort-wide in
  UVA/Padova with no per-person variation. It is an upper reference, about 4× B5's median. LESSONS 235 already
  validated B5 closed loop against the donors, so this is not a reason to raise the amplitude.

### New BDDP evidence: Loop users' cycle overrides [meas]

The best cycle signal in BDDP is Loop override presets named for the cycle ("period", "PMS", "luteal", "pre period
120%", …).

- **Who:** 177 Loop users have used one. 64 people have 193 runs of at least 3 days with at least 6 h/day under an
  insulin-up cycle preset.
- **Factor:** median ×1.2. 28% of "period"-named uses are insulin *down* (×0.5–0.9).
- **Run shape:** runs last a median 5 days. Start-to-start the median is 25.5 days, but timing is irregular: the
  per-person gap SD is a median 10 days.

Glucose and insulin, person-weighted, each against the same person's days without an override within ±35 days.
Brackets are 95% bootstrap CIs over persons.

| Days from switch-on | Δ mean glucose (mg/dL) | Δ TDD | Override factor (day mean) |
|---|---|---|---|
| −3..−2 | +4.1 [2.0, 6.4] | +3% | 1.00 |
| −1 | +11.5 [8.1, 14.9] | +12% | 1.02 |
| +1..+5 | +1.3 [−0.7, 3.3] | +11.5% | 1.09 |

| Days from switch-off | Δ mean glucose (mg/dL) | Δ TDD | Override factor (day mean) |
|---|---|---|---|
| −7..−4 | +6.6 [4.5, 9.0] | +10.5% | 1.06 |
| +1..+7 | +0.9 to +0.5 | +1–4% | 1.01 |

What this means for B5:

- **Loop absorbs only part of the change.** On the day before switching on, Loop already delivers +12% and glucose
  still runs +11.5 mg/dL.
  - This is a closed-loop target for B5 responders, if additive wants one beyond the logged-cycle profile.
  - Selection inflates day −1: people switch on after a high day.
- **The need is still rising late in a run** (+6.6 mg/dL under ×1.06). That fits a late-luteal peak.
- **Switching off brings no lows.** t<70 and t<54 stay flat over the following 7 days. Switch-off is user-timed and
  presumably at onset; we do not know where it falls relative to bleeding.

### The Dexcom G7 "cycle" profile depends on the method

Re-run person-weighted (first log after a ≥15-day gap as onset; ±35-day baseline; bootstrap over persons; 119
people, 247 onsets), no window around onset differs from zero:

| Window | Δ mean glucose (mg/dL) |
|---|---|
| days −1..0 | −0.8 [−4.0, +2.4] |
| days +3..+6 | −2.9 [−5.5, −0.3] |

LESSONS 136's +4.7 on day 0 is event-weighted on every log. Either way the onset excess in logged cycles is small and
fragile. The override cohort gives a stronger cycle anchor.

**Evidence:** `runs/2026-10-25-cycle/`, with `cycle-bddp-findings.md`, `cycle-lit-report.md` (68 verified
references) and the scripts (`profiles.py`, `windows.py`). uids stay there.

## 2. Site failures: Howsmon 2018

Howsmon DP et al., *J Diabetes Sci Technol* 2018, doi:10.1177/1932296818755173 [pub]. 19 adults, 2 weeks closed
loop and 2 weeks SAP, sets worn up to 7 days on purpose, failures actively searched for.

- **Rate:** 40 failures in 76 patient-weeks. Set survival was about 0.8–0.85 by day 3 and 0.65–0.72 by day 7, read
  from their Fig. 3.
  - That is roughly 10× E6 + E8 + E10 (1.9% per adult wear, Kanapka 2022).
  - Read it as an upper bound: small n, extended wear, a liberal definition (failure to correct counts) and an active
    search. It is not a reason to change the rate.
- **Alarmed share:**
  - Howsmon: 1 occlusion alarm in 40 failures, 2.5% (95% CI roughly 0.1–13%).
  - E8's share of the modelled failures: 0.003 / 0.019 ≈ 16%.
  - Small n, but it points to fewer alarmed failures than the model has.
- **E12 leakage now has a frequency:** 8 leakage failures in 76 patient-weeks, about 0.1 per week. Howsmon gives no
  magnitude (fraction of the dose lost), so E12 still lacks a size.
- **Silent failures dominate:** failure to correct was 70% of the 40, leakage 20%, infection 2.
- **Detection:** mean glucose at detection was 260–300 mg/dL. Under SAP, the median was 92 min above 250 in the 4 h
  before the person found the failure. This is a possible check on E6's "changes it after a long high" rule.
