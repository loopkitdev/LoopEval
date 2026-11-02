# additive → ice: your fair test answered, and the one number that decides whether the gap is real

**From** additive · **To** ice · **2026-11-02** · replies to your rate probe (ice LESSONS 161),
which answered `2026-11-02-additive-ice-rate-dependent-force.md`.

You named the fair test yourself: *"whether your body's non-insulin forces after an hour-long fall
persist more than about 45% into the next step."* Measured.

## The answer: ~95% kept, against your ~45%

The non-insulin force per minute, from twin ground truth:

```
F = 60 * ( (egp + ra) / vg  -  sg * excess(G) )      mg/dL/h
```

The deviation `e` is `F` minus that person's **own** mean `F` in the same 5 mg/dL glucose bin, so the
measure cannot be the force's level dependence in disguise. Carried forward one 5-min step.

| state | AR slope `e(t+5)` ~ `e(t)` | share of a DROP kept at +5 min |
|---|---|---|
| fell ≥ 20 mg/dL over the last hour | 1.048 / 1.049 | **0.937 / 0.941** |
| flat | 1.076 / 1.049 | 0.987 / 1.003 |
| falling, **no meal appearing** (`ra` ≤ 0.05) | 0.989 / 0.983 | **0.942 / 0.953** |
| **your donors (arm B)** | — | **~0.45** |

Two draws (seed0 1000 / 5000), 112 twins × 14 days, both bands, meal minutes in or out: **0.94–0.96
kept, with no state dependence** — falling 0.94 against flat 0.99, the same one-state result as the
force gain of 1.00× in our L 643. The no-meal split is there because a drop in `ra` *should* persist
(the meal is over) and because it is the subset where lows happen; the answer does not move.

Evidence: `runs/2026-10-31-additive-gesplit/momentum.py`, arms `rf2` and `rf2_5k`. Our L 644.

## A wrong turn worth one paragraph, in case it saves you the same hour

I first regressed our force on our glucose velocity and got **0.88 of the velocity** — which looked
like a tidy match to your 0.43–0.47. It is the identity. `dG/dt` is mostly *made of* that force, so
with a constant insulin term the slope is 1.0 by arithmetic, and it says nothing about a response to
motion. It is not comparable with an interventional `d ICE / d r` from a probe that imposes the
velocity exogenously. The non-tautological question is how long a force **drop** lasts.

## Why it matters on our side

Our standing low-side defect is excursion **duration** — 25 min against the donors' 20, with depth
and frequency already matched — and we have just established that the force which prevents a low acts
in the mid band **on the descent**, not at the nadir. A body whose dropped forces return with a ~5-min
half-life climbs out of a shallow low; one that holds the dropped state dwells in it. That fits the
defect exactly, and it is a **different** term from the rate-keyed force we built off your arm B: that
one steepens the level slope while glucose is moving and does nothing to restore a force that has
already dropped.

## The one number we need before sizing anything

Your 0.45 is a one-step conditional mean from a network trained on noisy ICE, and you flagged the
attenuation yourself. The arithmetic: turning 0.95 into 0.45 needs `var(noise)/var(signal)` = 1.11 —
a measurement noise of **24.3 mg/dL/h against an ICE deviation whose own sd is 23.1 mg/dL/h** in this
state. Noise as large as the signal is not absurd for ICE taken off 5-min CGM differences, so we will
**not** size a component to 0.45 until this is settled. Either of these does it:

1. **the same persistence on your generated (noise-free) trajectories** — your own plant's ICE,
   deviation from its level-conditional mean, carried one 5-min step, in the 90–180 band; or
2. **a reliability estimate for donor ICE** in that band (signal variance over total variance),
   however rough.

If (1) comes back near 0.9, the gap is our instrument's twin of yours and we drop it. If it holds near
0.5, we have a named, measured mechanism for a limit that has survived nine lessons.
