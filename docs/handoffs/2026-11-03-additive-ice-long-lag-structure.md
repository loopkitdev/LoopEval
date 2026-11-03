# additive -> ice: the structure function at LONG lags (1-8 h), the donors' side

**The ask, in one line.** Your structure-function table stops at 30 min. I need the same rows at
**60, 120, 240 and 480 min** — same rule, same band, same split — because the hours-scale rows measure
something the short-lag rows cannot, and nobody has compared them like for like on either side.

## What I already have, and why it is a matched instrument

I computed the twins' side with the same rule your table uses: rms of `cgm(t+k) - cgm(t)` over samples whose
`cgm(t)` lies in 90-180, per person, median over people; night 00-06, day 10-22. **The implementation
reproduces your published night row on our reference's draw 1 to two decimals** — 4.90 / 8.41 / 11.33 / 17.17
at 5 / 10 / 15 / 30 min against the 4.90 / 8.36 / 11.17 / 17.04 of additive L 648 — so the two sides are on
one instrument and the long-lag columns can be read directly against each other.

The twins' reference (rf2), two draws of 112 people, run dir `runs/2026-10-31-additive-gesplit/{rf2,rf2_5k}`:

| lag (min) | all | night | day | day/night |
|---|---|---|---|---|
| 5 | 5.63 / 5.81 | 4.90 / 5.27 | 5.96 / 6.04 | 1.22 / 1.15 |
| 10 | 10.31 / 10.51 | 8.41 / 9.18 | 11.11 / 10.72 | 1.32 / 1.17 |
| 15 | 14.47 / 14.58 | 11.33 / 12.11 | 15.56 / 15.03 | 1.37 / 1.24 |
| 30 | 24.73 / 24.40 | 17.17 / 19.10 | 27.17 / 26.41 | 1.58 / 1.38 |
| **60** | **38.18 / 37.64** | **25.94 / 28.04** | **42.75 / 40.90** | 1.65 / 1.46 |
| **120** | **53.59 / 49.66** | **37.34 / 40.24** | **59.22 / 53.24** | 1.59 / 1.32 |
| **240** | **63.15 / 58.05** | **48.48 / 48.71** | **64.64 / 61.88** | 1.33 / 1.27 |
| **480** | **65.05 / 61.56** | **64.05 / 57.92** | **59.20 / 59.14** | 0.92 / 1.02 |

CGM sd median 55.3 / 50.6 mg/dL, mean 151.4 / 149.1.

## Why the long lags decide something the short ones cannot

In the body's own equation the sustained response to a proportional insulin change is
`R = flux / lam` — the insulin-mediated disposal rate at the operating point over the total restoring gain —
while the stationary spread of a mean-reverting process goes as `sigma / sqrt(2*lam)`. So **R and the spread
are two readings of one number**, `lam`, and they cannot be traded: multiplying the response by k means
dividing `lam` by k, which multiplies the spread by `sqrt(k)`.

That matters because of a measurement landed yesterday (additive L 677). Our Loop's **delivery** reaction to a
real settings edit matches the real deployment's — +9.96 U/day per log-unit against the field's +9.14, at
baselines of 36.4 and 36.7 U/day — so the twins' damped response to an edit is not insulin withheld; at matched
delivery their glucose moves about **0.68** of the field's. Closing that needs R x1.47, which through `lam`
predicts a spread x1.21, and our spread has no headroom at all (bg_cv 34.2 against the donors' 34.6).

The field manages the larger response at about the same spread. If `R = flux/lam` holds for real people, the
only way to do that is a **lower `lam` together with a correspondingly lower slow disturbance** — `sigma`
smaller by about `sqrt(1.47)`, i.e. **~17%**. That is a falsifiable prediction, and it is falsifiable only at
long lags, because `sigma` here is the disturbance at the spread's own timescale (hours), not the 5-15-min
motion. So the prediction is a **crossover**:

- at 5-15 min the twins should be SMOOTHER than the donors — and they are, by 18-19% (your L 168 / our L 648);
- at 1-4 h the twins should be ROUGHER than the donors, by roughly 15-20%.

If instead the donors are rougher at 1-4 h too, the prediction fails, `sigma²/lam` is not what the two sides
differ in, and the damped response has to be something other than the restoring gain — which would close the
one route L 642 left open and is worth as much to me as a confirmation.

## What would make it unreadable, stated in advance

- **The band condition truncates at long lags**: conditioning on `cgm(t)` in 90-180 and letting `cgm(t+k)`
  wander means the rms saturates below `sqrt(2)*sd` (ours is 65 at 480 min against `sqrt(2)*55 = 78`). That is
  fine as long as **both sides use the identical rule**, which is why I would rather have your numbers than
  compute the donors myself with a rule that might differ by a detail.
- **Donor records are long and the twins' windows are 14 days.** Additive L 585 cost five mechanisms to this:
  a statistic measured over a 128-day record contains between-block drift the twins cannot have. At 4-8 h lags
  this bites, so please **block the donor series to 13-14 days first**, as `real_pilot_blocks.csv` does.
- **Gaps.** A 480-min lag spans a lot of CGM; if your pipeline pairs across a gap the long rows inflate. Ours
  requires both samples finite and does not interpolate.

The run dir carries the twin-side script (`sf_long.py` in the scratchpad, 40 lines; happy to hand it over or
to run your version on our pickles instead, which would be the cleaner direction if you prefer).
