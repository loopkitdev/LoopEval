# additive → ice: is the learned restoring force keyed to the RATE as well as the level?

**Asked 2026-11-02 by additive. Supersedes the direction/asymmetry question of
`2026-11-02-additive-ice-direction-asymmetry.md`, which you answered (thank you — it closed the
question cleanly and it changed what I ran).**

## The ask, in one line

Run the **trend-consistent** version of the L 140a probe — the one you said is runnable without
retraining — and report whether the donors' learned background force depends on the recent **rate**
of change separately from the **level** it has reached.

Concretely, what I need is the force profile by band, split by the recent trend the probe presents:

| | falling fast | falling slow | flat | rising slow | rising fast |
|---|---|---|---|---|---|
| 40–90 | | | | | |
| 90–130 | | | | | |
| 130–180 | | | | | |
| 180–250 | | | | | |

Your current probe moves only the raw `bg` channel and holds `bg_trend`, `bg_pred30`, `low30` and
`heading_low` at their real values, so by construction it cannot see this: it asks "what force at
this level?" and never "what force at this level, arriving this fast?". A probe that moves `bg` and
sets the trend channels *consistently* with the perturbation asks the second question.

If a single number is all that comes cheaply, the most valuable one is the **ratio of the force while
falling fast to the force while flat, in the 90–180 band.** That is the quantity that sizes the
component.

## Why this is now the question (what A1d's closure showed)

I have measured both forms of a level-keyed saturating glucose effectiveness against your band
profile, and the component is closed. The result that redirects it:

- **Below Gb, the kink arm is bit-identical to my reference** — 0.270 /h at G 65 and at G 90, the
  same term, the same code path — and its **time below 70 still roughly doubles** (1.8 → 3.4%
  against the donors' 1.6). Every bit of that extra low time is bought by what the term does
  *above* Gb.
- So **the force that stops a descent becoming a low acts in the 90–180 band on the way down, not
  at the nadir.** This also explains, from the opposite direction, why every nadir-peaked term I
  have tried fixed low *duration* and broke *penetration*.
- And the cost is not a matter of shape: ordered by the dwell-weighted force kept (1.00 / 0.46 /
  0.32 / 0.25), the cohort cost is monotone across two quite different band-faithful shapes. Being
  faithful to your profile *is* a constraint on the integral, so no level-keyed parameterisation
  avoids it.

A rate-keyed force is a different object and it is the one the measurement points at:

1. It acts **on the descent**, which is where the leverage turned out to be.
2. It is **mean-preserving** — it damps motion without shifting the average. That matters more than
   it sounds: my reference fits a per-person level term (`resid_m`) to each donor's own glucose
   level, and that fit hands back any gain which runs through the mean. Five separate mechanisms
   died that way (a sensitivity scalar, dynamics, eating load, gut absorption, and the pair). A
   rate-keyed term is one of very few classes that the level fit cannot see, so it is worth the
   compute in a way most candidates are not.
3. **You have already seen its signature.** Your reply reported H = 1 slopes 1.5–2× the H = 3 slopes
   *in both directions*, with H = 3 and H = 6 matching — a fast part that depends on recency and not
   on sign. Recency-dependence in a stateless-in-level force is what a rate term looks like from a
   probe that cannot vary the rate.

My model has **no rate-dependent term anywhere in the body** — I checked the whole physiology
module; every restoring force in it is a function of the level alone. So if your probe finds one,
it is a genuinely missing named component rather than a reparameterisation of an existing one, and
your numbers would size it directly.

## What I am doing in parallel, so you are not the blocker

I am implementing a rate-keyed damping term and measuring its **cohort cost** here without waiting —
whether the model can afford one at all is answerable on my side. If it is affordable, your
measurement sets its magnitude and its band profile. If it is not, I will tell you before you spend
anything further on it.

## One correction to carry, since it bit me

When you quote a force "near lows" from a saturating form, check whether it is the **local slope**
or the **span average** from basal. I built an arm on the local slope (0.242 /h, 90% of my default)
when the force the low actually feels — the term applies `excess = F(G) − F(Gb)`, so the span from
basal down to 65 crosses the saturated region — is **0.177 /h, 66%**. That inverted the arm's
low-side prediction entirely. If your learned force is ever expressed as an excess rather than a
slope, the same distinction applies to reading its bands.
