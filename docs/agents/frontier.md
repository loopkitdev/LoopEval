<!-- Role overlay. Loaded via ROLE.md; see AGENTS.md → Roles. -->

# Role: frontier / algorithm improvement

Read with **AGENTS.md** (shared) and **docs/agents/verification.md** (faithful replay,
identity checks, case studies) — every frontier claim rests on those.

### 1. Frontier experiments — "does this change actually help?"

Run a candidate algorithm/settings change through the closed-loop counterfactual
simulator over weeks–months of real data, score **TIR and t<54**, and compare against a
**reference curve** (the stock algorithm swept over ISF multipliers). A change matters
only if it has **lift** — more TIR at equal severe-lows than aggressiveness tuning alone
reaches. See **[docs/FRONTIERS.md](docs/FRONTIERS.md)**; the scorer is
`python -m loopeval_analysis.frontier`.

**Lift — the definition (in `frontier.lift`):** the signed, **axis-normalized closest
distance** from a candidate `(TIR, t<54)` point to the reference-sweep polyline. Both axes
are scaled by the reference sweep's span (TIR ≈ tens of %, t<54 ≈ fraction of a %) so
neither dominates — a raw Euclidean distance would be swamped by TIR. Sign is **+** when
the point is **below-and-right** of the sweep (better: more TIR / less t<54) and **−** when
above-left (worse). **Greatest positive lift = best.** (This replaced an older "TIR gap at
matched t<54", which blew up wherever the reference curve runs flat.)

**Two things lift is fragile about — both have produced confidently wrong rankings:**

- **Compare on ONE dial.** Sweeping the candidate over ISF while the reference sweeps
  insulin-needs measures the *dial* as much as the mechanism — the two trace different
  paths through (TIR, t<54). Sweep the candidate over **insulin-needs too**, or include a
  plain (mechanism-off) control swept on the candidate's dial to subtract the dial's share.
- **Lift is span-normalized, so it is NOT comparable across reference extents.** Extending
  a reference (e.g. needs ×1.3 → ×2.0) grows the t<54 span and silently shrinks *every*
  lift value — 6.6× on one dataset. Only rank within one reference; never compare lift
  magnitudes across runs whose reference differs.

**Never read a lift number without looking at the plot.** Lift is a scalar summary of a
geometric fact; if the sign disagrees with where the point sits relative to the gray line,
believe the plot. That check is what caught both hooked-curve bugs (fixed 2026-07-17).

**Sweep the candidate, rank by mean.** A candidate parameterization is a *mechanism*; sweep
it over its own ISF multipliers and rank mechanisms by the **mean (or median) lift across
the sweep** (`frontier.summarize_mechanisms`) — not by any single point. Best-of-sweep max
is optimistically biased (it grabs the highest jitter point); report the peak multiplier
only as a secondary "where it peaks". The multiplier that pairs best with a mechanism is
**dataset-dependent**: a non-announcer may want *lower* ISF (dose more aggressively, let the
mechanism catch the added lows), a heavy announcer *higher* ISF (gentler automation, since
meal boluses already carry TIR). **Canonical scoring definition now lives in [docs/FRONTIERS.md → Scoring](docs/FRONTIERS.md)**:
a candidate improves iff, with the needs dial free to move, it reaches an operating point
better on BOTH axes (TIR up AND t<54 down; t<70 when t<54≈0) than the reference curve —
strict dominance, judged in the operating band, re-tuning allowed. That section supersedes
any other scoring guidance here or elsewhere.

**Current frontier picture (qualitative — regenerate numbers per dataset/window):**

- **Leading with lift:** **Asymmetric Integral RC** (`--candidate-integral-rc
  --candidate-irc-drop-scale/-rise-scale` — weight the drop side of retrospective
  correction more than the rise side) and **double-low prevention**
  (`--candidate-sensitive-mode-tau-min/-gain` — an EWMA of recent negative discrepancy
  that raises effective ISF on subsequent cycles, damping re-dosing into the rebound
  after a low).
- **Sliders (no lift, still available):** flat ISF multiplier, application factor, and
  **GBAF** (`--candidate-gbaf`, glucose-based application factor). These move along the
  reference curve, not above it. GBAF in particular has *not* shown lift under the
  current fidelity stack — don't present it as a frontier lever.
- **NO LIFT — tested and rejected 2026-08-25:** **volatility-scaled
  forecast band** (`--candidate-vol-band-k`, plus `--candidate-vol-band-licence-scale`
  for the calm side) and **VBAF** (`--candidate-vbaf-scale-calm/-volatile`). σ is a causal
  EWMA of recent 5-min glucose increments (`Sources/EvalCore/Engine/GlucoseVolatility.swift`),
  exported per step as `candidateVolSigma` / `candidateVolBandMgdl`. Rationale: σ is a
  **second-moment** quantity the forecast has no representation of, where GBAF/dynISF key
  on level, which the forecast already contains — that is the structural reason to expect
  it to behave unlike an aggressiveness dial. Evidence behind it in
  `analysis/loopeval_analysis/volatility.py` + `analysis/dist_views/`.
  **VERDICT 2026-08-25: NO USABLE LIFT, and the premise is inverted.** Dense frontier on
  both validated real-lows beds (bddp11 + bddp10, 2 mo, insulin-needs dial ×0.80–1.10,
  **11 reference points** with 0.025 steps through the elbow, k ∈ {0.25, 0.5, 1, 2};
  run dir `runs/2026-08-25-distributions/ksweep/`).
  *Interior* mean lift (endpoints excluded — see the endpoint note below):
  bddp11 +0.004/+0.008/−0.000/+0.002 and bddp10 −0.000/−0.009/−0.037/−0.066 for
  k = 0.25/0.5/1/2. bddp11 does show a **genuine localized positive band at needs
  0.925–1.025** (k=0.5: +0.015/+0.015/+0.061/+0.054, visible on the plot as the candidate
  line dipping under the reference around TIR 64–67) — this only appeared once the elbow
  was densified, so coarse sweeps can hide structure as well as invent it. **But it does
  not replicate:** bddp10 is *negative* in that same region at every k (k=1: −0.062/−0.087),
  and its own small positive band sits somewhere else entirely (0.85–0.925). Treat the
  bddp11 band as reference-curvature idiosyncrasy until a third bed reproduces it.
  **ROOT CAUSE — σ LAGS the low, it does not lead it.** Mean σ profile around every
  downward crossing of 70 on the stock counterfactual peaks at **+50 to +95 min AFTER the
  crossing**, on all 6 bed×dial combinations; an hour *before* the crossing σ is only
  +0.1…+0.3 SD above its mean (`vsb_leadlag.py`, `leadlag.png`). σ is an EWMA of recent
  |Δ| and the largest |Δ| are the fall itself and its rebound, so it is diagnostic, not
  predictive. Operationally: P(low within 2h | σ in top quintile) = 13.5–17% vs a base rate
  of 12–14% (ratio **1.09–1.31**); only 22–25% of lows are preceded by a spike; 5 false
  alarms per true positive. Case studies (`ksweep/cases/`) show the failure concretely —
  the band saturates during the *rebound* and suppresses dosing into the climb, and where
  it "helped" the help came from a level offset set hours earlier, not timely action
  (mean dose delta −0.009 U/step where it fires, **+0.006 where it does not** — Loop just
  adds the insulin back). It does cut lows (1478→1210, severe 548→318 at ×1.00) but at the
  dial's own exchange rate. **The licence side** is worse: mean −0.077, frac_pos 0.00.
  **Any revival needs a LEADING signal, not a bigger gain on this one.**
  **TWO METHOD WARNINGS, both cost real time here:**
  (a) **Coarse references manufacture false positives.** The first pass used 4 reference
  points and reported *positive* mean lift at k=0.25/0.5 on both beds. That is polyline
  chord bias — lift is distance to the reference POLYLINE, these references are strongly
  convex in t<54, and a chord across a convex curve sits ABOVE it. Measured, same points
  and same span: **+0.010→+0.021 in mean lift**, flipping frac_pos from 0.91 to 0.27.
  **Use ≤0.05 dial steps, and ≤0.025 through the elbow.**
  (b) **Endpoint projections are distorted.** At the first/last sweep point the reference
  polyline does not extend further, so the closest-point projection collapses onto the
  endpoint and exaggerates: the ×0.80 point scored −0.05…−0.28 in every arm and dominated
  the raw mean. Report the **interior** mean, or extend the reference past the candidate
  range. `score_ksweep.py` prints both.
  **Two traps this mechanism has already fallen into, both fixed — do not undo them:**
  (a) keyed on ABSOLUTE σ it is dominated by σ's level and becomes a constant downward
  forecast shift, i.e. an aggressiveness dial in disguise (−54% TDD at k=0.25); it is
  therefore keyed on σ's deviation from the person's own 24 h median
  (`--candidate-vol-band-relative`, the default) so it is mean-zero by construction.
  (b) the band must stop widening at a horizon cap (`--candidate-vol-band-horizon-cap-min`,
  default 60 min) — a genuine 1σ band is ~100 mg/dL wide at 6 h, and without the cap the far
  end of the forecast always becomes the predicted minimum and the mechanism suspends
  everything.
- Meal announcement dominates everything: an announcing user's real-world point sits far
  above anything hands-off automation reaches. The residual gap is a forecasting
  problem (anticipating carbs), not a dosing-logic problem.
