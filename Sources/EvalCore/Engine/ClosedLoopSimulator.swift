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
        progress: (@Sendable (Double) -> Void)? = nil
    ) throws -> ClosedLoopSimResult {

        // 1. Baseline: parallel sweep, used purely as reference for Δdose.
        let baselineResult = try runSweep(data: data, interval: interval, config: baselineConfig)
        var baselineDoseByTime: [Date: Double] = [:]
        baselineDoseByTime.reserveCapacity(baselineResult.predictions.count)
        for p in baselineResult.predictions {
            baselineDoseByTime[p.evaluatedAt] = p.recommendedDeltaU ?? 0
        }

        // 2. Set up mutable state for candidate
        let mgdlUnit = LoopUnit.milligramsPerDeciliter
        let insulinModel = data.therapyTimeline.insulinType.model
        let activityDuration = insulinModel.effectDuration

        // counter_glucose: starts as actual; modified as Δdose impacts accumulate.
        // We mutate values in place at sample indices, preserving original
        // timestamps and metadata.
        var counterGlucose = data.glucose
        var counterMgdl = data.glucose.map { $0.quantity.doubleValue(for: mgdlUnit) }

        // Virtual doses: candidate's accumulated extra/reduced deliveries.
        // Stored as bolus-type entries with volume = Δdose; insulin model
        // treats them like instantaneous deliveries at time t.
        var virtualDoses: [EvalInsulinDose] = []
        virtualDoses.reserveCapacity(1024)

        // Pre-scale sensitivity once per candidate config (timeline doesn't
        // depend on dose history).
        let scaledSensitivity = Self.applySensitivityScaling(
            data.therapyTimeline.sensitivity,
            globalMultiplier: candidateConfig.sensitivityMultiplier,
            hourlyMultipliers: candidateConfig.sensitivityHourlyMultipliers,
            timezone: candidateConfig.localTimezone
        )

        // 3. Sequential walk
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

            // Build candidate's effective dose history (actual + virtuals so far).
            // Virtuals are appended in chronological order as we go, so the
            // combined array can be merged without resorting.
            let combinedDoses = EvaluationEngine.mergeSorted(data.doses, virtualDoses)

            // Build candidate's effective glucose history from current counter_mgdl
            // (only values up to and including t matter for prediction input).
            // We mutate the EvalGlucoseSample array's quantities to reflect
            // counter_mgdl. To keep this efficient, we rebuild the array
            // lazily — or better, snapshot it once per step from counter_mgdl.
            // Snapshot is O(N) per step; for ~8K samples × ~8K steps = 64M ops
            // which is acceptable; could optimize with a thin GlucoseHistory
            // wrapper later.
            let counterSamples = zip(counterGlucose, counterMgdl).map { (s, v) -> EvalGlucoseSample in
                if v == s.quantity.doubleValue(for: mgdlUnit) { return s }
                return EvalGlucoseSample(
                    startDate: s.startDate,
                    quantity: LoopQuantity(unit: mgdlUnit, doubleValue: v),
                    provenanceIdentifier: s.provenanceIdentifier,
                    isDisplayOnly: s.isDisplayOnly,
                    wasUserEntered: s.wasUserEntered,
                    condition: s.condition,
                    trendRate: s.trendRate
                )
            }

            // Build the candidate input window using counter glucose & combined doses.
            // Note: we deliberately skip `precomputedInsulin` here because dose
            // history grows incrementally; the slow path is correct.
            let candidateBuilder = InputWindowBuilder(
                glucose: counterSamples,
                doses: combinedDoses,
                carbs: data.carbs,
                therapyTimeline: data.therapyTimeline,
                config: candidateConfig
            )

            guard let input = candidateBuilder.buildInput(at: t) else {
                t = t.addingTimeInterval(candidateConfig.evalStep)
                stepIdx += 1
                continue
            }

            // Compute candidate prediction (raw-dose path; supports any feature combo).
            let momentumCap: LoopQuantity? = candidateConfig.positiveVelocityCap.map {
                LoopQuantity(unit: .milligramsPerDeciliterPerMinute, doubleValue: $0)
            }
            let prediction: LoopPrediction<EvalCarbEntry> = LoopAlgorithm.generatePrediction(
                start: t,
                glucoseHistory: input.glucose,
                doses: input.doses,
                carbEntries: input.carbs,
                basal: input.basal,
                sensitivity: input.sensitivity,
                carbRatio: input.carbRatio,
                algorithmEffectsOptions: .all,
                useIntegralRetrospectiveCorrection: candidateConfig.useIntegralRC,
                includingPositiveVelocityAndRC: candidateConfig.includingPositiveVelocityAndRC,
                useMidAbsorptionISF: candidateConfig.useMidAbsorptionISF,
                carbAbsorptionModel: candidateConfig.carbAbsorptionModel.model,
                momentumVelocityMaximum: momentumCap,
                useAsymmetricMomentum: candidateConfig.useAsymmetricMomentum,
                useHybridAsymmetricMomentum: candidateConfig.useHybridAsymmetricMomentum,
                momentumAlphaSlow: candidateConfig.momentumAlphaSlow,
                momentumAlphaFast: candidateConfig.momentumAlphaFast
            )

            // Candidate dose recommendation. Reuse computeDoseRecommendation
            // (handles dynamic-ISF, two-pass scaling, etc.).
            let appFactor: Double
            if candidateConfig.glucoseBasedApplicationFactor {
                let currentBG = counterMgdl[EvaluationEngine.bestGlucoseIndex(at: t, in: counterGlucose)]
                appFactor = Self.glucoseBasedApplicationFactor(
                    currentBG: currentBG,
                    lowAnchor: candidateConfig.gbafLowAnchor,
                    highAnchor: candidateConfig.gbafHighAnchor,
                    factorLow: candidateConfig.gbafFactorLow,
                    factorHigh: candidateConfig.gbafFactorHigh
                )
            } else {
                appFactor = 0.4
            }
            let doseRec = Self.computeDoseRecommendation(
                prediction: prediction,
                at: t,
                input: input,
                suspendThreshold: data.therapyTimeline.suspendThreshold,
                maxBolus: data.therapyTimeline.maxBolus,
                maxBasalRate: data.therapyTimeline.maxBasalRate,
                insulinType: data.therapyTimeline.insulinType,
                evalStep: candidateConfig.evalStep,
                applicationFactor: appFactor,
                dynamicISFMode: candidateConfig.dynamicISFMode,
                dynamicISFWindowHours: candidateConfig.dynamicISFWindowHours,
                dynamicISFICEThreshold: candidateConfig.dynamicISFICEThreshold,
                dynamicISFMaxBoost: candidateConfig.dynamicISFMaxBoost
            )
            let candidateDose = doseRec?.deltaU ?? 0
            let baselineDose = baselineDoseByTime[t] ?? 0
            let deltaDose = candidateDose - baselineDose

            // ISF at this time (in mg/dL/U convention; stored as mg/dL unit per codebase quirk).
            let isfQty = scaledSensitivity.first(where: { $0.startDate <= t && $0.endDate > t })?.value
                ?? scaledSensitivity.closestPrior(to: t)?.value
            let isf = isfQty?.doubleValue(for: mgdlUnit) ?? 0

            // Apply Δdose impact to FUTURE counter_mgdl entries
            if deltaDose != 0 && isf > 0 {
                for i in 0..<counterGlucose.count {
                    let futureT = counterGlucose[i].startDate
                    if futureT <= t { continue }
                    let τ = futureT.timeIntervalSince(t)
                    if τ > activityDuration { break }
                    let pd = max(0.0, min(1.0, 1.0 - insulinModel.percentEffectRemaining(at: τ)))
                    counterMgdl[i] -= deltaDose * isf * pd
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

        return ClosedLoopSimResult(
            steps: steps,
            baselineLabel: baselineLabel,
            candidateLabel: candidateLabel,
            intervalStart: evalStart,
            intervalEnd: interval.end
        )
    }

    // MARK: – Helpers

    /// Find the index of the glucose sample closest to `t` (binary-search).
    private static func bestGlucoseIndex(at t: Date, in samples: [EvalGlucoseSample]) -> Int {
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

