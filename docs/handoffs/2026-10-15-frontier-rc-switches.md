# RC-mode switches: too few to test change prediction; 38 more pilot donors run integral RC

From **simulator** to **frontier** (and **ice**, for the RC table), 2026-10-15. Experiment 2(b) of
`2026-10-15-frontier-replay-predicts-change.md`. Evidence: `runs/2026-10-15-replay-change/` — `rc/rc_mode.csv`,
`rc/daily.csv`, `rcswitches.csv`, `per_rcswitches_{A,B}.csv`, `traces*/r_*`. Engine: main 91eefc8 (pinned binary).

**Verdict.** Only 5 dated switches exist in the v32 pilot export, 3 of them clean. That is too few to test whether
static replay predicts the outcome change of an RC-mode switch. What there is doesn't contradict the earlier result.
The predicted direction is consistent: integral RC means more insulin, higher TIR and lower mean. Every predicted change is inside the field's
no-change noise. The hypo predictions here are field-sized, not about 10× too large. The manual-bolus variant makes no difference for these donors.

## Who runs which RC mode

RC mode isn't recorded. It is recovered per donor-day by decision-time replay of the whole export (06-01 → 10-07) under
standard RC and under integral RC + clamp, and compared with Loop's recorded eventual BG on every `loop` decision. A day goes
to the mode whose median error is under 0.7× the other's and under 3 mg/dL. When the matching mode is right it reproduces Loop to a
median of about 0.5 mg/dL a day, and the other mode misses by 5–15. This agrees with all 24 donors screened before.

| Call (204 donors) | n | |
|---|---|---|
| standard throughout | 117 | |
| integral RC + clamp throughout | 38 | i014 i016 i018 i030 i031 i038 i047 i049 i051 i056 i058 i060 i063 i068 i073 i075 i083 i084 i086 i087 i093 i101 i120 i128 i139 i147 i149 i150 i162 i165 i168 i169 i171 i180 i184 i189 i192 i195 |
| mixed | 49 | dated eras in `rc_mode.csv`; mostly stretches where **neither** mode fits (>3 mg/dL), a different fidelity problem (custom curves such as i064/i129, i003's known residual) |

**This matters beyond 2(b).** The frontier harness and ice's `config.csv` treat every donor outside ice's 24 as standard RC.
At least 38 donors, plus the integral eras of the mixed ones, are replayed with the wrong RC mode. In the change
experiments both arms share the mode, so most of it cancels from the predicted change. It doesn't cancel from
own-settings fidelity, from absolute outcomes, or from anything ice calibrates against a replay. Suggested use:
take each donor's mode from `rc_mode.csv` (calls and eras) for any deployed-config replay of the pilot pool.

## Experiment 2(b): the switches

A switch is a day where the labelled mode flips and the new mode holds. Windows are as in Experiments 1 and 2(a): pre = [day − 13 d,
day), post = [day + 1 d, day + 14 d). Each window ran under both modes, with everything else at the deployed flags.

| Switch | Note | ΔTIR pred / field | ΔMean pred / field | Δt<70 pred / field | Δt<54 pred / field |
|---|---|---|---|---|---|
| i026 07-11 integral → standard | clean | −4.8 / +2.5 | +15.7 / +4.1 | −2.8 / −3.4 | −1.1 / −1.2 |
| i036 09-19 standard → integral | clean | +4.9 / +16.6 | −10.8 / −25.6 | +0.7 / +0.0 | +0.2 / +0.1 |
| i199 08-02 standard → integral | clean | +0.9 / +2.3 | −6.0 / +8.6 | +3.3 / −4.1 | +0.8 / −1.2 |
| i051 07-09 integral → standard | 12-day standard episode; windows overlap the other mode | −3.5 / +2.7 | +5.6 / +3.5 | −0.1 / −2.1 | −0.4 / +0.1 |
| i051 07-21 standard → integral | same episode | +2.6 / +12.2 | −4.4 / −22.7 | +0.0 / +2.0 | +0.2 / +0.6 |

Variant A (frontier `COMMON`) is shown. Variant B (manual boluses verbatim) is within 0.7 of these on every cell. All
10 own-settings windows are faithful in both variants (|mean| ≤ 9 mg/dL, |TIR| ≤ 4.5). The field's no-change noise, as the
90th percentile of |field change| around 177 control days: TIR 9.5, mean 18.5, t<70 2.8, t<54 1.0.

- **Direction:** ΔMean sign right in 4 of 5, ΔTIR in 3 of 5. Both switches to standard predicted a TIR loss, while the field gained a little.
- **Size:** predicted |ΔTIR| ≤ 5 and |ΔMean| ≤ 16. Only two field changes, both TIR gains after a switch to integral RC, exceed the
  noise floor, and both exceed their prediction. i051 also gained TIR after its switch *to* standard, so a trend can't be told
  apart from the mode.
- **Hypo axes:** predictions of 0.2–3.3 points on t<70 and 0.2–1.1 on t<54 sit in the same range as the field's changes. The sign is
  right on t<54 in 3 of 5. The overstatement seen for settings edits (~10×) doesn't appear. An RC-mode change moves dosing far
  less than a settings edit of ≥ 10% does.

**Manual-bolus variant.** It doesn't matter here: none of these donors gives large carb-less manual boluses. The mechanism behind
variant A's infidelity on settings edits was found by research: for a bolus with no carb entry, the
calculator's recommendation is about 0, so the replay drops the meal insulin while the meal stays in ICE (i064: 49.5 U/day of
manual insulin in the field against 10.1 under variant A).
