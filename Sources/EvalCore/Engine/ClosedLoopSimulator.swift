// ClosedLoopSimulator.swift — full closed-loop counterfactual simulation
//
// The bench's linearized counterfactual computes counter_BG by propagating
// candidate's Δdose (computed against actual past CGM) onto the actual CGM
// trace. That has a known weakness: candidate keeps making decisions against
// actual BG, not its own resulting counterfactual BG. For aggressive
// candidates (e.g. IRC), the drift compounds without self-correction.
//
// This file implements true closed-loop replay: at each step t, candidate's
// inputs are substituted to use:
//   - counter_glucose: actual_glucose with cumulative Δdose impact applied
//   - candidate_doses: actual_doses + virtual entries from prior Δdose decisions
//
// The candidate's prediction at t therefore sees its own resulting BG and
// its own accumulated dose history. Δdose at t reflects feedback-corrected
// behavior. Forward-impact propagation updates counter_glucose for future
// steps, and a virtual dose entry is added so future IOB calculations
// include the candidate's extra/reduced delivery.
//
// Sequential by nature; cannot reuse the parallelized runSweep. Slower
// (~10x) but accurate for absolute trajectory estimates.

import Foundation
import LoopAlgorithm

/// Output of a closed-loop simulation. Per-step trace of the candidate's
/// behavior with feedback, plus the resulting counter_glucose timeline.
public struct ClosedLoopSimResult: Codable, Sendable {
    public struct Step: Codable, Sendable {
        public let t: Date
        public let actualBG: Double      // actual CGM at this time
        public let counterBG: Double     // candidate's effective BG (counterfactual)
        public let baselineDose: Double  // baseline's recommendedDeltaU at this t
        public let candidateDose: Double // candidate's recommendedDeltaU (with feedback)
        public let deltaDose: Double     // candidateDose - baselineDose
        public let isf: Double           // ISF used at this t (mg/dL/U)
    }
    public let steps: [Step]
    public let baselineLabel: String
    public let candidateLabel: String
    public let intervalStart: Date
    public let intervalEnd: Date
}

extension EvaluationEngine {

    /// Run a closed-loop simulation: baseline as a parallel reference sweep,
    /// candidate as a sequential per-step replay with glucose + dose-history
    /// feedback. Both use the same data source for actual past activity.
    public func simulateClosedLoop(
        data: PreloadedData,
        interval: DateInterval,
        baselineConfig: EvalConfig,
        candidateConfig: EvalConfig,
        baselineLabel: String = "Baseline",
        candidateLabel: String = "Candidate",
        progress: (@Sendable (Double) -> Void)? = nil,
        smoothBoostScores: [(Date, Double)]? = nil,
        smoothBoostLowAnchor: Double = 0.4,
        smoothBoostHighAnchor: Double = 0.6,
        smoothBoostMaxBoost: Double = 0.5,
        smoothBoostInline: Bool = false,
        smoothBoostFeaturesOut: String? = nil,
        smoothBoostDownLowAnchor: Double = 0.0,
        smoothBoostMaxBoostDown: Double = 0.0,
        baselineDoseLookup: [(Date, Double)]? = nil
    ) throws -> ClosedLoopSimResult {

        // 1. Set up mutable state.
        //
        // IMPORTANT: baseline and candidate must use the SAME code path so the
        // identity case (configs equal) gives Δdose = 0 at every step. Earlier
        // versions ran baseline through `runSweep` (precomputed-insulin path)
        // and candidate through an inline call (doses path); those two paths
        // are mathematically equivalent but numerically diverge, producing
        // non-zero Δdose at every step and compounding drift through the
        // feedback loop. Both sides now go through `Self.simStepDose(...)`
        // which uses one canonical doses-path generatePrediction call.
        let mgdlUnit = LoopUnit.milligramsPerDeciliter
        let insulinModel = data.therapyTimeline.insulinType.model
        let activityDuration = insulinModel.effectDuration

        // counter_glucose: starts as actual; modified as Δdose impacts accumulate.
        // We mutate values in place at sample indices, preserving original
        // timestamps and metadata.
        var counterGlucose = data.glucose
        var counterMgdl = data.glucose.map { $0.quantity.doubleValue(for: mgdlUnit) }
        // Baseline always reads from actual glucose; precomputed once for GBAF lookups.
        let baselineMgdl = data.glucose.map { $0.quantity.doubleValue(for: mgdlUnit) }

        // Optional features dump for inline-mode diagnostic.
        var inlineFeaturesRows: [(Date, Double?, [Double]?)] = []

        // Per-step IOB history (for the rolling-max feature in RiskScoreModel).
        var pastIOBs: [(Date, Double)] = []
        pastIOBs.reserveCapacity(2048)

        // Asymmetric dynamic-ISF state. Boost applies to BOTH prediction and
        // dose recommendation. Release uses BG-aware conditions: hard to
        // release while BG is still low or sensitivity continues; easier to
        // release once BG indicates the user is safely out of hypo-risk zone.
        var asymISFBoost: Double = 1.0
        var asymBoostStartedAt: Date? = nil
        var asymBoostExpiresAt: Date? = nil
        var asymSustainedHighSince: Date? = nil

        // Virtual doses: candidate's accumulated extra/reduced deliveries.
        // Stored as bolus-type entries with volume = Δdose; insulin model
        // treats them like instantaneous deliveries at time t.
        var virtualDoses: [EvalInsulinDose] = []
        virtualDoses.reserveCapacity(1024)

        // Counter glucose samples: maintained as a single buffer across all
        // sim steps, updated in-place when counterMgdl[i] changes via the
        // forward-impact loop. This avoids a per-step O(N) zip/map rebuild
        // that was consuming ~10-15% of per-sim time on long sweeps.
        var counterSamples: [EvalGlucoseSample] = data.glucose

        // Pre-scale sensitivity once per candidate config (timeline doesn't
        // depend on dose history).
        let scaledSensitivity = Self.applySensitivityScaling(
            data.therapyTimeline.sensitivity,
            globalMultiplier: candidateConfig.sensitivityMultiplier,
            hourlyMultipliers: candidateConfig.sensitivityHourlyMultipliers,
            timezone: candidateConfig.localTimezone
        )

        // 2. Sequential walk
        let evalStart = interval.start.addingTimeInterval(candidateConfig.evalWarmupHours * 3600)

        // Pre-compute expected step count for progress reporting
        let totalDuration = max(0, interval.end.timeIntervalSince(evalStart))
        let totalSteps = max(1, Int(totalDuration / candidateConfig.evalStep) + 1)

        var steps: [ClosedLoopSimResult.Step] = []
        steps.reserveCapacity(totalSteps)

        var t = evalStart
        var stepIdx = 0

        while t <= interval.end {
            if let progress, totalSteps > 1 {
                progress(min(Double(stepIdx) / Double(totalSteps - 1), 1.0))
            }

            // ----- BASELINE step: either look up from cache or compute fresh.
            // Cache mode: avoid duplicating identical baseline work across a
            // parameter sweep. Provided lookup table is a sorted [(Date, Double)].
            let baselineDose: Double
            if let lookup = baselineDoseLookup,
               let cached = Self.lookupCachedDose(at: t, in: lookup) {
                baselineDose = cached
            } else {
                let baselineBuilder = InputWindowBuilder(
                    glucose: data.glucose,
                    doses: data.doses,
                    carbs: data.carbs,
                    therapyTimeline: data.therapyTimeline,
                    config: baselineConfig
                )
                if let baselineInput = baselineBuilder.buildInput(at: t) {
                    baselineDose = Self.simStepDose(
                        t: t,
                        input: baselineInput,
                        config: baselineConfig,
                        therapy: data.therapyTimeline,
                        glucoseMgdl: baselineMgdl,
                        glucoseSamples: data.glucose
                    ).dose
                } else {
                    baselineDose = 0
                }
            }

            // ----- CANDIDATE step: counter glucose, combined doses, candidateConfig.
            // Combined doses = actual + accumulated virtual deliveries (sorted by time).
            let combinedDoses = EvaluationEngine.mergeSorted(data.doses, virtualDoses)

            // counterSamples is maintained incrementally above (mutated in-place
            // when the forward-impact loop changes counterMgdl[i]). No per-step
            // rebuild needed.
            let candidateBuilder = InputWindowBuilder(
                glucose: counterSamples,
                doses: combinedDoses,
                carbs: data.carbs,
                therapyTimeline: data.therapyTimeline,
                config: candidateConfig
            )
            guard let candidateInput = candidateBuilder.buildInput(at: t) else {
                t = t.addingTimeInterval(candidateConfig.evalStep)
                stepIdx += 1
                continue
            }
            // ----- CANDIDATE step: three possible paths:
            //  (a) smooth-boost mode (continuous risk-score → ISF multiplier)
            //  (b) asymmetric persistent-boost (state-tracked binary mechanism)
            //  (c) normal candidate dose
            var candidateDose: Double
            if let scores = smoothBoostScores, !scores.isEmpty {
                // Smooth-boost via precomputed scores (Python-trained, CSV).
                // Look up nearest score within ±5 min of t.
                let score = Self.lookupScore(at: t, scores: scores)
                let boost = Self.smoothBoostFactor(
                    score: score,
                    lowAnchor: smoothBoostLowAnchor,
                    highAnchor: smoothBoostHighAnchor,
                    maxBoost: smoothBoostMaxBoost,
                    downLowAnchor: smoothBoostDownLowAnchor,
                    maxBoostDown: smoothBoostMaxBoostDown
                )
                candidateDose = Self.simStepDose(
                    t: t,
                    input: candidateInput,
                    config: candidateConfig,
                    therapy: data.therapyTimeline,
                    glucoseMgdl: counterMgdl,
                    glucoseSamples: counterGlucose,
                    extraISFMultiplier: boost
                ).dose
            } else if smoothBoostInline {
                // Smooth-boost computed INLINE from counter-state. We need the
                // candidate's unboosted prediction to extract features (past
                // ICE, insulin effects, etc.), then re-run with the computed
                // boost. Two simStepDose calls per step → slower but
                // deployable.
                let (_, unboostedPrediction) = Self.simStepDose(
                    t: t,
                    input: candidateInput,
                    config: candidateConfig,
                    therapy: data.therapyTimeline,
                    glucoseMgdl: counterMgdl,
                    glucoseSamples: counterGlucose,
                    extraISFMultiplier: 1.0
                )
                let curIOB = unboostedPrediction.activeInsulin ?? 0
                let features = RiskScoreModel.features(
                    at: t,
                    glucose: counterGlucose,
                    glucoseMgdl: counterMgdl,
                    prediction: unboostedPrediction,
                    currentIOB: curIOB,
                    pastIOBs: pastIOBs,
                    localTimezone: candidateConfig.localTimezone
                )
                pastIOBs.append((t, curIOB))
                let inlineScore: Double? = features.map { RiskScoreModel.score(features: $0) }
                let boost = Self.smoothBoostFactor(
                    score: inlineScore,
                    lowAnchor: smoothBoostLowAnchor,
                    highAnchor: smoothBoostHighAnchor,
                    maxBoost: smoothBoostMaxBoost,
                    downLowAnchor: smoothBoostDownLowAnchor,
                    maxBoostDown: smoothBoostMaxBoostDown
                )
                if smoothBoostFeaturesOut != nil {
                    inlineFeaturesRows.append((t, inlineScore, features))
                }
                candidateDose = Self.simStepDose(
                    t: t,
                    input: candidateInput,
                    config: candidateConfig,
                    therapy: data.therapyTimeline,
                    glucoseMgdl: counterMgdl,
                    glucoseSamples: counterGlucose,
                    extraISFMultiplier: boost
                ).dose
            } else if candidateConfig.asymmetricDynamicISF {
                // Step 1: unboosted candidate (gives us the past ICE).
                let (unboostedDose, unboostedPrediction) = Self.simStepDose(
                    t: t,
                    input: candidateInput,
                    config: candidateConfig,
                    therapy: data.therapyTimeline,
                    glucoseMgdl: counterMgdl,
                    glucoseSamples: counterGlucose,
                    extraISFMultiplier: 1.0
                )

                // Step 2: trigger detection.
                let triggerBoost = Self.boostFromPastICE(
                    t: t,
                    prediction: unboostedPrediction,
                    windowHours: candidateConfig.dynamicISFWindowHours,
                    threshold: candidateConfig.dynamicISFICEThreshold,
                    maxBoost: candidateConfig.dynamicISFMaxBoost
                )

                // Step 2.5: current counter-BG for release-condition checks.
                let currentBG = counterMgdl[EvaluationEngine.bestGlucoseIndex(at: t, in: counterGlucose)]

                // Step 2.6: update boost state.
                if triggerBoost > 1.0 + 1e-9 {
                    // Fresh sensitivity signal: activate or extend boost.
                    asymISFBoost = max(asymISFBoost, triggerBoost)
                    if asymBoostStartedAt == nil { asymBoostStartedAt = t }
                    asymBoostExpiresAt = t.addingTimeInterval(
                        candidateConfig.asymmetricDynamicISFLockHours * 3600)
                    // Reset sustained-high counter — fresh signal overrides BG-based release.
                    asymSustainedHighSince = nil
                } else if asymISFBoost > 1.0 + 1e-9, let startedAt = asymBoostStartedAt {
                    // Currently boosting, no fresh signal: check BG-aware release.
                    let elapsed = t.timeIntervalSince(startedAt)
                    let minHold = candidateConfig.asymmetricDynamicISFMinLockHours * 3600

                    // Track sustained-high streak.
                    if currentBG > candidateConfig.asymmetricDynamicISFSustainedHighBG {
                        if asymSustainedHighSince == nil { asymSustainedHighSince = t }
                    } else {
                        asymSustainedHighSince = nil
                    }

                    var shouldRelease = false
                    if elapsed >= minHold {
                        // Hold-floor on low BG: don't release while BG still low,
                        // regardless of other conditions.
                        if currentBG >= candidateConfig.asymmetricDynamicISFKeepActiveBelowBG {
                            // Hard ceiling
                            if let expires = asymBoostExpiresAt, t >= expires {
                                shouldRelease = true
                            }
                            // Immediate release on very high BG
                            if currentBG > candidateConfig.asymmetricDynamicISFReleaseHighBG {
                                shouldRelease = true
                            }
                            // Sustained-high release
                            if let since = asymSustainedHighSince,
                               t.timeIntervalSince(since) >= candidateConfig.asymmetricDynamicISFSustainedHighMinutes * 60 {
                                shouldRelease = true
                            }
                        }
                    }
                    if shouldRelease {
                        asymISFBoost = 1.0
                        asymBoostStartedAt = nil
                        asymBoostExpiresAt = nil
                        asymSustainedHighSince = nil
                    }
                }

                // Step 3: if boost active, re-run candidate with scaled ISF in
                // prediction + dose. Else use the unboosted dose we already have.
                if asymISFBoost > 1.0 + 1e-9 {
                    candidateDose = Self.simStepDose(
                        t: t,
                        input: candidateInput,
                        config: candidateConfig,
                        therapy: data.therapyTimeline,
                        glucoseMgdl: counterMgdl,
                        glucoseSamples: counterGlucose,
                        extraISFMultiplier: asymISFBoost
                    ).dose
                } else {
                    candidateDose = unboostedDose
                }
            } else {
                candidateDose = Self.simStepDose(
                    t: t,
                    input: candidateInput,
                    config: candidateConfig,
                    therapy: data.therapyTimeline,
                    glucoseMgdl: counterMgdl,
                    glucoseSamples: counterGlucose
                ).dose
            }

            let deltaDose = candidateDose - baselineDose

            // ISF at this time (in mg/dL/U convention; stored as mg/dL unit per codebase quirk).
            let isfQty = scaledSensitivity.first(where: { $0.startDate <= t && $0.endDate > t })?.value
                ?? scaledSensitivity.closestPrior(to: t)?.value
            let isf = isfQty?.doubleValue(for: mgdlUnit) ?? 0

            // Apply Δdose impact to FUTURE counter_mgdl entries.
            //
            // Within DIA, scale by the pharmacodynamic curve. PAST DIA, the
            // impact is the asymptote (= 1.0 × ISF × Δdose) — all the insulin
            // has eventually manifested. Earlier versions broke out of the
            // loop at τ > DIA, which dropped each step's contribution off a
            // cliff for samples that crossed the DIA boundary. That created
            // spurious jumps in counter_BG whenever clusters of prior Δdoses
            // expired in the same 5-min window.
            if deltaDose != 0 && isf > 0 {
                // Binary-search for the first sample with startDate > t. Past
                // samples (futureT <= t) get skipped wholesale instead of being
                // tested one-by-one — saves ~half the iterations late in the run
                // when most samples are in the past.
                let startIdx = Self.firstIndex(where: { counterGlucose[$0].startDate > t },
                                                in: 0..<counterGlucose.count)
                if startIdx < counterGlucose.count {
                    for i in startIdx..<counterGlucose.count {
                        let futureT = counterGlucose[i].startDate
                        let τ = futureT.timeIntervalSince(t)
                        let pd: Double
                        if τ > activityDuration {
                            pd = 1.0
                        } else {
                            pd = max(0.0, min(1.0, 1.0 - insulinModel.percentEffectRemaining(at: τ)))
                        }
                        let newMgdl = counterMgdl[i] - deltaDose * isf * pd
                        counterMgdl[i] = newMgdl
                        // Mirror the update into the maintained counterSamples buffer.
                        let s = counterSamples[i]
                        counterSamples[i] = EvalGlucoseSample(
                            startDate: s.startDate,
                            quantity: LoopQuantity(unit: mgdlUnit, doubleValue: newMgdl),
                            provenanceIdentifier: s.provenanceIdentifier,
                            isDisplayOnly: s.isDisplayOnly,
                            wasUserEntered: s.wasUserEntered,
                            condition: s.condition,
                            trendRate: s.trendRate
                        )
                    }
                }
                // Append virtual dose entry. Treat Δdose as an instantaneous bolus
                // at time t. This makes IOB calculations on subsequent steps
                // include the candidate's extra (or reduced) delivery.
                virtualDoses.append(EvalInsulinDose(
                    deliveryType: .bolus,
                    startDate: t,
                    endDate: t,
                    volume: deltaDose,
                    insulinType: data.therapyTimeline.insulinType,
                    automatic: true
                ))
            }

            // Record step
            let actualMgdl = data.glucose[EvaluationEngine.bestGlucoseIndex(at: t, in: data.glucose)].quantity.doubleValue(for: mgdlUnit)
            let counterMgdlAtT = counterMgdl[EvaluationEngine.bestGlucoseIndex(at: t, in: counterGlucose)]
            steps.append(ClosedLoopSimResult.Step(
                t: t,
                actualBG: actualMgdl,
                counterBG: counterMgdlAtT,
                baselineDose: baselineDose,
                candidateDose: candidateDose,
                deltaDose: deltaDose,
                isf: isf
            ))

            t = t.addingTimeInterval(candidateConfig.evalStep)
            stepIdx += 1
        }

        progress?(1.0)

        // Optional features dump
        if let featuresPath = smoothBoostFeaturesOut, !inlineFeaturesRows.isEmpty {
            let formatter = ISO8601DateFormatter()
            formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            let cols = [
                "time", "score",
                "f_peak_bg_90m", "f_peak_iob_90m", "f_recent_insulin",
                "f_bg_now", "f_iob_now", "f_v_cgm",
                "f_ice_w15", "f_ice_trend_60",
                "f_hour_sin", "f_hour_cos",
            ]
            var lines = [cols.joined(separator: ",")]
            for (t, score, feats) in inlineFeaturesRows {
                var cells = [formatter.string(from: t)]
                cells.append(score.map { String(format: "%.6f", $0) } ?? "")
                if let f = feats {
                    for v in f { cells.append(String(format: "%.6f", v)) }
                } else {
                    cells.append(contentsOf: Array(repeating: "", count: cols.count - 2))
                }
                lines.append(cells.joined(separator: ","))
            }
            let csv = lines.joined(separator: "\n") + "\n"
            try csv.write(to: URL(fileURLWithPath: featuresPath), atomically: true, encoding: .utf8)
        }

        return ClosedLoopSimResult(
            steps: steps,
            baselineLabel: baselineLabel,
            candidateLabel: candidateLabel,
            intervalStart: evalStart,
            intervalEnd: interval.end
        )
    }

    // MARK: – Helpers

    /// Canonical "compute one step's recommended Δdose" used for BOTH baseline
    /// and candidate inside the closed-loop sim. Keeping the two sides on the
    /// same code path is what makes the identity case (configs equal) produce
    /// Δdose = 0 at every step. Uses the raw-doses `generatePrediction` path
    /// (not `precomputedInsulin`) because the candidate's dose history changes
    /// per step — precomputing wouldn't be valid for it.
    fileprivate static func simStepDose(
        t: Date,
        input: PredictionInput,
        config: EvalConfig,
        therapy: TherapyTimeline,
        glucoseMgdl: [Double],
        glucoseSamples: [EvalGlucoseSample],
        extraISFMultiplier: Double = 1.0
    ) -> (dose: Double, prediction: LoopPrediction<EvalCarbEntry>) {
        let momentumCap: LoopQuantity? = config.positiveVelocityCap.map {
            LoopQuantity(unit: .milligramsPerDeciliterPerMinute, doubleValue: $0)
        }

        // When asymmetric persistent-boost is active, scale sensitivity used
        // for BOTH the prediction and the dose recommendation. The prediction
        // matters: if the forecast also "knows" ISF is currently higher than
        // schedule, Loop's IOB-compensation expects less BG drop and doesn't
        // try to redistribute the under-delivered insulin forward.
        let effectiveSensitivity: [AbsoluteScheduleValue<LoopQuantity>]
        if abs(extraISFMultiplier - 1.0) > 1e-9 {
            let unit = LoopUnit.milligramsPerDeciliter
            effectiveSensitivity = input.sensitivity.map { entry in
                AbsoluteScheduleValue(
                    startDate: entry.startDate,
                    endDate: entry.endDate,
                    value: LoopQuantity(unit: unit,
                                        doubleValue: entry.value.doubleValue(for: unit) * extraISFMultiplier))
            }
        } else {
            effectiveSensitivity = input.sensitivity
        }
        let effectiveInput = PredictionInput(
            glucose: input.glucose,
            doses: input.doses,
            carbs: input.carbs,
            basal: input.basal,
            sensitivity: effectiveSensitivity,
            carbRatio: input.carbRatio,
            target: input.target
        )

        let prediction: LoopPrediction<EvalCarbEntry> = LoopAlgorithm.generatePrediction(
            start: t,
            glucoseHistory: effectiveInput.glucose,
            doses: effectiveInput.doses,
            carbEntries: effectiveInput.carbs,
            basal: effectiveInput.basal,
            sensitivity: effectiveInput.sensitivity,
            carbRatio: effectiveInput.carbRatio,
            algorithmEffectsOptions: .all,
            useIntegralRetrospectiveCorrection: config.useIntegralRC,
            includingPositiveVelocityAndRC: config.includingPositiveVelocityAndRC,
            useMidAbsorptionISF: config.useMidAbsorptionISF,
            carbAbsorptionModel: config.carbAbsorptionModel.model,
            momentumVelocityMaximum: momentumCap,
            useAsymmetricMomentum: config.useAsymmetricMomentum,
            useHybridAsymmetricMomentum: config.useHybridAsymmetricMomentum,
            momentumAlphaSlow: config.momentumAlphaSlow,
            momentumAlphaFast: config.momentumAlphaFast
        )

        let appFactor: Double
        if config.glucoseBasedApplicationFactor {
            let idx = EvaluationEngine.bestGlucoseIndex(at: t, in: glucoseSamples)
            let currentBG = glucoseMgdl[idx]
            appFactor = EvaluationEngine.glucoseBasedApplicationFactor(
                currentBG: currentBG,
                lowAnchor: config.gbafLowAnchor,
                highAnchor: config.gbafHighAnchor,
                factorLow: config.gbafFactorLow,
                factorHigh: config.gbafFactorHigh
            )
        } else {
            appFactor = 0.4
        }

        let doseRec = EvaluationEngine.computeDoseRecommendation(
            prediction: prediction,
            at: t,
            input: effectiveInput,
            suspendThreshold: therapy.suspendThreshold,
            maxBolus: therapy.maxBolus,
            maxBasalRate: therapy.maxBasalRate,
            insulinType: therapy.insulinType,
            evalStep: config.evalStep,
            applicationFactor: appFactor,
            dynamicISFMode: config.dynamicISFMode,
            dynamicISFWindowHours: config.dynamicISFWindowHours,
            dynamicISFICEThreshold: config.dynamicISFICEThreshold,
            dynamicISFMaxBoost: config.dynamicISFMaxBoost
        )
        return (dose: doseRec?.deltaU ?? 0, prediction: prediction)
    }

    /// Compute the asymmetric-dynamic-ISF boost factor for time `t` given a
    /// candidate prediction. Returns 1.0 if no sensitivity event is detected.
    /// Uses the same ICE-based trigger logic as in-algorithm dynamic-ISF: the
    /// most-negative 30-min rolling mean ICE in `windowHours` lookback.
    fileprivate static func boostFromPastICE(
        t: Date,
        prediction: LoopPrediction<EvalCarbEntry>,
        windowHours: Double,
        threshold: Double,
        maxBoost: Double
    ) -> Double {
        let lookbackStart = t.addingTimeInterval(-windowHours * 3600)
        let pastICE = prediction.effects.insulinCounteraction.filter {
            $0.endDate <= t && $0.startDate >= lookbackStart
        }
        let subWindowSec: TimeInterval = 30 * 60
        var minRollingMean = Double.infinity
        for i in 0..<pastICE.count {
            let endT = pastICE[i].endDate
            let windowStart = endT.addingTimeInterval(-subWindowSec)
            var sum = 0.0
            var count = 0
            for j in stride(from: i, through: 0, by: -1) {
                if pastICE[j].endDate <= windowStart { break }
                sum += pastICE[j].quantity.doubleValue(for: .milligramsPerDeciliterPerMinute)
                count += 1
            }
            guard count >= 4 else { continue }
            let mean = sum / Double(count)
            if mean < minRollingMean { minRollingMean = mean }
        }
        if minRollingMean < -threshold {
            let excess = -minRollingMean - threshold
            return 1.0 + min(maxBoost, excess / threshold)
        }
        return 1.0
    }

    /// Piecewise-linear smooth boost from risk score:
    ///   score ≤ downLowAnchor          → boost = 1 − maxBoostDown   (aggressive)
    ///   downLowAnchor < score < lowAnchor → linear ramp up to 1.0
    ///   score = lowAnchor              → boost = 1.0 (no change)
    ///   lowAnchor < score < highAnchor → linear ramp up to 1 + maxBoost
    ///   score ≥ highAnchor             → boost = 1 + maxBoost (conservative)
    ///
    /// When downLowAnchor=0 and maxBoostDown=0 (defaults), the negative-side
    /// branch is inert and the function behaves identically to the original
    /// one-sided mapping.
    fileprivate static func smoothBoostFactor(
        score: Double?,
        lowAnchor: Double,
        highAnchor: Double,
        maxBoost: Double,
        downLowAnchor: Double = 0.0,
        maxBoostDown: Double = 0.0
    ) -> Double {
        guard let s = score else { return 1.0 }
        // Up-side
        if s >= lowAnchor {
            let span = highAnchor - lowAnchor
            guard span > 1e-9 else { return 1.0 }
            let clipped = max(0.0, min(1.0, (s - lowAnchor) / span))
            return 1.0 + maxBoost * clipped
        }
        // Down-side (only active if maxBoostDown > 0 and anchors are valid)
        let downSpan = lowAnchor - downLowAnchor
        guard maxBoostDown > 1e-9, downSpan > 1e-9 else { return 1.0 }
        // s < lowAnchor; clamp ratio in [0, 1]
        let aggression = max(0.0, min(1.0, (lowAnchor - s) / downSpan))
        return 1.0 - maxBoostDown * aggression
    }

    /// Look up the risk score nearest to `t` within a ±5 min tolerance.
    /// Returns nil if no score is within range. Assumes scores sorted by time.
    fileprivate static func lookupScore(at t: Date, scores: [(Date, Double)]) -> Double? {
        guard !scores.isEmpty else { return nil }
        // Binary search for closest index
        var lo = 0, hi = scores.count - 1
        while lo < hi {
            let mid = (lo + hi) / 2
            if scores[mid].0 < t { lo = mid + 1 } else { hi = mid }
        }
        // Check lo and lo-1
        let toleranceSec: TimeInterval = 5 * 60 + 1
        var best: (Date, Double)? = nil
        var bestDelta = Double.infinity
        for cand in [lo - 1, lo, lo + 1] where cand >= 0 && cand < scores.count {
            let delta = abs(scores[cand].0.timeIntervalSince(t))
            if delta < bestDelta {
                bestDelta = delta
                best = scores[cand]
            }
        }
        guard let b = best, bestDelta <= toleranceSec else { return nil }
        return b.1
    }

    /// Look up the baseline dose at time `t` from a sorted `[(Date, Double)]`
    /// cache. Requires exact-or-near-exact timestamp match (within 1ms). Used
    /// to skip recomputing baseline across cells in a sweep.
    fileprivate static func lookupCachedDose(at t: Date, in cache: [(Date, Double)]) -> Double? {
        guard !cache.isEmpty else { return nil }
        var lo = 0, hi = cache.count - 1
        while lo < hi {
            let mid = (lo + hi) / 2
            if cache[mid].0 < t { lo = mid + 1 } else { hi = mid }
        }
        // Check lo and lo-1 for closest match
        for cand in [lo - 1, lo, lo + 1] where cand >= 0 && cand < cache.count {
            if abs(cache[cand].0.timeIntervalSince(t)) < 0.001 {
                return cache[cand].1
            }
        }
        return nil
    }

    /// Binary-search the smallest index `i` in `range` for which `predicate(i)`
    /// is true. Predicate must be monotonic — false then true. Returns
    /// `range.upperBound` if no element satisfies it.
    fileprivate static func firstIndex(where predicate: (Int) -> Bool, in range: Range<Int>) -> Int {
        var lo = range.lowerBound
        var hi = range.upperBound
        while lo < hi {
            let mid = lo + (hi - lo) / 2
            if predicate(mid) { hi = mid } else { lo = mid + 1 }
        }
        return lo
    }

    /// Find the index of the glucose sample closest to `t` (binary-search).
    fileprivate static func bestGlucoseIndex(at t: Date, in samples: [EvalGlucoseSample]) -> Int {
        var lo = 0, hi = samples.count - 1
        while lo < hi {
            let mid = (lo + hi) / 2
            if samples[mid].startDate < t { lo = mid + 1 } else { hi = mid }
        }
        return min(max(lo, 0), samples.count - 1)
    }

    /// Merge two sorted dose arrays in O(N+M).
    private static func mergeSorted(_ a: [EvalInsulinDose], _ b: [EvalInsulinDose]) -> [EvalInsulinDose] {
        if b.isEmpty { return a }
        if a.isEmpty { return b }
        var out: [EvalInsulinDose] = []
        out.reserveCapacity(a.count + b.count)
        var i = 0, j = 0
        while i < a.count && j < b.count {
            if a[i].startDate <= b[j].startDate {
                out.append(a[i]); i += 1
            } else {
                out.append(b[j]); j += 1
            }
        }
        while i < a.count { out.append(a[i]); i += 1 }
        while j < b.count { out.append(b[j]); j += 1 }
        return out
    }
}

