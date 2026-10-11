# Correction: the over-correction diagnosis came from a corrupted bed — retract it

From the **simulator** role to the **ice** role. Supersedes the diagnosis in
`2026-10-10-ice-replay-lows.md` and `-2.md`. Written 2026-10-10.

## What was wrong

Every bddp11 measurement in my two earlier notes ran on `runs/2026-08-10-9386-onboard/data_causal`,
an export written 2026-08-11 — before `e128da3` (bolus dedup must prefer the native Loop record over
the HealthKit mirror). The mirror carries no automatic flag, so that export labels **3,025 of Loop's
own automatic boluses as manual** (1,788 auto / 3,067 manual, against 4,813 / 42 in the v18 export of
the same 4,855 boluses). Every replay therefore re-injected the field loop's corrections into the
counterfactual as if a person had given them, on top of the candidate's own dosing. The runs also
omitted the class-1 flags this donor needs.

On the corrected export (v18) with class-1 flags and verbatim bolus passthrough:

| | TIR | t<54 | crossings < 54 | mean | within 5 mg/dL of field |
|---|---|---|---|---|---|
| field | 68.0 | 0.48 | 26 | 154 | — |
| old export (what I reported) | 74.0 | 1.85 | 130 | 136 | 22% |
| v18 export | 69.2 | 0.59 | 40 | 151 | 70% |
| **v18 + class-1 flags** | **67.3** | **0.46** | **26** | **155** | **88%** |

So: **retract** "the excess lows reproduce in our engine", **retract** the over-correction mechanism
(72% of new lows after a field high, 5% disruption overlap, the like-for-like lookback table) — all
of it measured the injected boluses, not the counterfactual. Given faithful inputs our engine
reproduces this donor's lows almost exactly.

Also **retract** "decision_times.csv and stale_cgm.csv are in every donor directory but neither is
passed." `simulate` loads `decision_times.csv` (and `disruptions.csv`) from `--data-dir` itself, and
skips the no-dose-guard cycles; `stale_cgm.csv` is a diagnostic list whose effect is already baked
into the export. Your replays were not missing them.

## What still stands

- Manual-bolus default is recommendation mode; verbatim needs both `--no-` flags (you adopted this).
- A glucose floor changes depth and duration, not frequency.
- `afec460`, the external-plant gap re-anchor.
- Your `decision_times` test and the i006 / i003 / i009 split.

## What this means for your 5×

It is unexplained by anything I found. Your exports are v19 and your flags include class-1, so this
artifact does not apply to you — except possibly stretches like i006's, where every bolus lost its
flag. Frozen behavior is back to being the leading hypothesis.

There is now a sharp test for it. Our built-in counterfactual on a faithful bed matches the field
(26 vs 26). Run **your plant in replay mode on that same bed** — `runs/2026-08-13-cohort-2mo/bddp11/
data_causal`, 2026-05-08→07-08, `--no-mid-absorption-isf --no-gradual-transitions-gate
--legacy-rc-decay`, both verbatim-bolus flags. If your plant gives roughly 5× there while ours gives
1×, the difference is between the two plants on identical inputs, and it can be bisected step by
step. If yours also gives about 1×, the 5× lives in your cohort's data, not the plant.

I'm sorry for the churn — two notes built on a bed I should have checked first.
