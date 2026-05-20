// EvaluationEngine.swift — core sweep loop

import Foundation
import LoopAlgorithm

// MARK: – EvaluationEngine

/// Runs the core prediction sweep over a historical interval.
///
/// Pre-fetches all data once with appropriate buffers, then walks through
/// each evaluation step calling `LoopAlgorithm.generatePrediction()`.
public actor EvaluationEngine {

    // MARK: – Properties

    let dataSource: any EvalDataSource

    // MARK: – Init

    public init(dataSource: any EvalDataSource) {
        self.dataSource = dataSource
    }

    // MARK: – Public API

    /// Run a full evaluation over `interval`, fetching data as needed.
    ///
    /// - Parameters:
    ///   - interval: The time window to sweep.
    ///   - config:   Evaluation parameters (default: `EvalConfig.default`).
    ///   - progress: Optional callback receiving 0.0–1.0 progress values.
    public func evaluate(
        interval: DateInterval,
        config: EvalConfig = EvalConfig(),
        progress: (@Sendable (Double) -> Void)? = nil
    ) async throws -> EvaluationResult {
        let data = try await prefetchData(for: interval, config: config)
        return try runSweep(data: data, interval: interval, config: config, progress: progress)
    }

    /// Pre-fetch all data needed for an evaluation.
    ///
    /// `interval.start` is the beginning of the data collection window.
    /// Predictions are not generated until after `config.evalWarmupHours`
    /// have elapsed, so every scored forecast has a full history window.
    ///
    /// Exposed for reuse in parameter sweeps — fetch once, sweep many configs.
    public func prefetchData(
        for interval: DateInterval,
        config: EvalConfig
    ) async throws -> PreloadedData {
        // Data collection must start BEFORE interval.start so the first evaluated
        // step (at interval.start + evalWarmupHours) has a full history window.
        // evalWarmupHours == insulinLookbackHours by default, so the warmup window
        // exactly covers the insulin history. But doses can start slightly earlier
        // (e.g., a temp basal that started before midnight). We add a 3h buffer on
        // top of evalWarmupHours to make sure we capture any such carryover doses
        // and avoid the LoopAlgorithm activeInsulin = 0 fallback.
        let historyBuffer = config.insulinLookbackHours * 3600 + 3 * 3600   // lookback + 3h pad
        let dataStart = interval.start.addingTimeInterval(-historyBuffer)

        let doseEnd: Date = config.includeFutureInsulin
            ? interval.end.addingTimeInterval(6 * 3600)
            : interval.end

        let glucoseInterval = DateInterval(
            start: dataStart,
            end:   interval.end.addingTimeInterval(10 * 60)   // tiny pad for last step
        )
        let doseInterval = DateInterval(start: dataStart, end: doseEnd)
        let carbInterval = DateInterval(
            start: dataStart,
            end:   interval.end.addingTimeInterval(6 * 3600)
        )
        let therapyInterval = DateInterval(
            start: dataStart,
            end:   interval.end.addingTimeInterval(8 * 3600)  // ISF t+8h extension
        )

        async let glucose = dataSource.getGlucoseValues(interval: glucoseInterval)
        async let doses   = dataSource.getDoses(interval: doseInterval)
        async let carbs   = dataSource.getCarbEntries(interval: carbInterval)
        async let therapy = dataSource.getTherapyTimeline(interval: therapyInterval)

        return PreloadedData(
            glucose: try await glucose,
            doses: try await doses,
            carbs: try await carbs,
            therapyTimeline: try await therapy
        )
    }

    /// Run the sweep over pre-loaded data (no I/O).
    ///
    /// Exposed for parameter sweeps so data is loaded once and many configs
    /// can be evaluated without re-fetching.
    ///
    /// - Parameters:
    ///   - data:     Pre-fetched data from `prefetchData(for:config:)`.
    ///   - interval: The sweep interval.
    ///   - config:   Evaluation configuration.
    ///   - progress: Optional 0.0–1.0 progress callback.
    public func runSweep(
        data: PreloadedData,
        interval: DateInterval,
        config: EvalConfig,
        progress: (@Sendable (Double) -> Void)? = nil
    ) throws -> EvaluationResult {

        let builder = InputWindowBuilder(
            glucose: data.glucose,
            doses: data.doses,
            carbs: data.carbs,
            therapyTimeline: data.therapyTimeline,
            config: config
        )

        // Pre-compute annotation + insulin effects for the full sweep window.
        // Annotation is ISF-independent (done once regardless of sensitivityMultiplier).
        // Effects are computed once for the (possibly scaled) sensitivity timeline
        // and reused for every step — saving O(D×T) work per step.
        let sweepInterval = DateInterval(start: interval.start, end: interval.end)
        let scaledSensitivity = Self.applySensitivityScaling(
            data.therapyTimeline.sensitivity,
            globalMultiplier: config.sensitivityMultiplier,
            hourlyMultipliers: config.sensitivityHourlyMultipliers,
            timezone: config.localTimezone
        )
        let precomputed = data.precomputedInsulinInput(
            for: sweepInterval,
            sensitivity: scaledSensitivity,
            useMidAbsorptionISF: config.useMidAbsorptionISF
        )
        // First evaluated step is after the warmup period, so every prediction
        // has a full insulin/glucose history window behind it.
        let evalStart = interval.start.addingTimeInterval(config.evalWarmupHours * 3600)

        // Build the full list of step times up front so we can parallelize.
        var stepDates: [Date] = []
        do {
            var t = evalStart
            while t <= interval.end {
                stepDates.append(t)
                t = t.addingTimeInterval(config.evalStep)
            }
        }

        // Partition into chunks for parallel execution. Each chunk processes
        // its slice serially; chunks run concurrently. Pre-allocate per-chunk
        // result slots so each thread writes to a unique index (safe).
        let nThreads = max(1, min(8, ProcessInfo.processInfo.activeProcessorCount))
        let stepCount = stepDates.count
        let chunkSize = max(1, (stepCount + nThreads - 1) / nThreads)
        var chunkRanges: [Range<Int>] = []
        var i = 0
        while i < stepCount {
            chunkRanges.append(i..<min(i + chunkSize, stepCount))
            i += chunkSize
        }
        let nChunks = chunkRanges.count

        var chunkRecords: [[PredictionRecord]] = Array(repeating: [], count: nChunks)
        var chunkSkipped: [Int]                 = Array(repeating: 0,  count: nChunks)

        // Use UnsafeMutableBufferPointer so concurrentPerform can write to
        // distinct indices without Sendable hassles. The arrays are pre-sized
        // and never reallocated, so distinct-index writes are safe.
        chunkRecords.withUnsafeMutableBufferPointer { recsBuf in
            chunkSkipped.withUnsafeMutableBufferPointer { skipBuf in
                DispatchQueue.concurrentPerform(iterations: nChunks) { c in
                    var local: [PredictionRecord] = []
                    local.reserveCapacity(chunkRanges[c].count)
                    var skipped = 0
                    for idx in chunkRanges[c] {
                        let t = stepDates[idx]
                        if let rec = Self.computeStep(
                            t: t,
                            builder: builder,
                            precomputed: precomputed,
                            therapy: data.therapyTimeline,
                            config: config
                        ) {
                            local.append(rec)
                        } else {
                            skipped += 1
                        }
                    }
                    recsBuf[c] = local
                    skipBuf[c] = skipped
                }
            }
        }

        // Concatenate in chunk order — within-chunk records are already
        // chronological, and chunks were partitioned chronologically too.
        var predictions: [PredictionRecord] = []
        predictions.reserveCapacity(stepCount)
        for c in 0..<nChunks { predictions.append(contentsOf: chunkRecords[c]) }
        let skippedCount = chunkSkipped.reduce(0, +)
        progress?(1.0)

        // Actual CGM includes a lookback buffer before evalStart so that:
        //  • The Kalman smoother warms up on real data (not a cold start)
        //  • Panel 3's past-history window has data even for the first predictions
        // Pre-evalStart points don't affect metric computation: PredictionComparator
        // only matches against points that have a corresponding prediction (≥ evalStart).
        let evalInterval = DateInterval(start: evalStart, end: interval.end)
        let actualWarmupStart = evalStart.addingTimeInterval(-config.glucoseLookbackHours * 3600)
        let actualGlucose = data.glucose.filter {
            $0.startDate >= actualWarmupStart && $0.startDate <= interval.end
        }

        return EvaluationResult(
            interval: evalInterval,
            config: config,
            predictions: predictions,
            actual: actualGlucose,
            skippedCount: skippedCount
        )
    }

    // MARK: – Per-step body

    /// Runs the per-step prediction + dose-recommendation work for a single
    /// evaluation time `t`. Returns nil if the input window can't be built.
    /// Pure function — depends only on its arguments. Safe to call from
    /// `concurrentPerform` parallel contexts.
    static func computeStep(
        t: Date,
        builder: InputWindowBuilder,
        precomputed: PrecomputedInsulinInput,
        therapy: TherapyTimeline,
        config: EvalConfig
    ) -> PredictionRecord? {
        guard let input = builder.buildInput(at: t) else { return nil }

        let momentumCap: LoopQuantity? = config.positiveVelocityCap.map {
            LoopQuantity(unit: .milligramsPerDeciliterPerMinute, doubleValue: $0)
        }

        // Forecast generation. Use precomputed-insulin fast path when possible.
        let prediction: LoopPrediction<EvalCarbEntry>
        if config.includeFutureInsulin {
            let doseWindowStart = input.sensitivity.first?.startDate
                ?? t.addingTimeInterval(-config.insulinLookbackHours * 3600)
            let doseWindowEnd = t.addingTimeInterval(6 * 3600)
            let stepPrecomputed = precomputed.sliced(from: doseWindowStart, to: doseWindowEnd)
            prediction = LoopAlgorithm.generatePrediction(
                start: t,
                glucoseHistory: input.glucose,
                precomputedInsulin: stepPrecomputed,
                carbEntries: input.carbs,
                sensitivity: input.sensitivity,
                carbRatio: input.carbRatio,
                algorithmEffectsOptions: .all,
                useIntegralRetrospectiveCorrection: config.useIntegralRC,
                includingPositiveVelocityAndRC: config.includingPositiveVelocityAndRC,
                useMidAbsorptionISF: config.useMidAbsorptionISF,
                carbAbsorptionModel: config.carbAbsorptionModel.model,
                momentumVelocityMaximum: momentumCap,
                useAsymmetricMomentum: config.useAsymmetricMomentum,
                momentumAlphaSlow: config.momentumAlphaSlow,
                momentumAlphaFast: config.momentumAlphaFast
            )
        } else {
            prediction = LoopAlgorithm.generatePrediction(
                start: t,
                glucoseHistory: input.glucose,
                doses: input.doses,
                carbEntries: input.carbs,
                basal: input.basal,
                sensitivity: input.sensitivity,
                carbRatio: input.carbRatio,
                algorithmEffectsOptions: .all,
                useIntegralRetrospectiveCorrection: config.useIntegralRC,
                includingPositiveVelocityAndRC: config.includingPositiveVelocityAndRC,
                useMidAbsorptionISF: config.useMidAbsorptionISF,
                carbAbsorptionModel: config.carbAbsorptionModel.model,
                momentumVelocityMaximum: momentumCap,
                useAsymmetricMomentum: config.useAsymmetricMomentum,
                momentumAlphaSlow: config.momentumAlphaSlow,
                momentumAlphaFast: config.momentumAlphaFast
            )
        }

        // Optional no-future-insulin overlay (inspect report only).
        var noFuturePredicted: [PredictedGlucoseValue]? = nil
        if config.includeFutureInsulin,
           let inputNoFuture = builder.buildInput(at: t, includeFutureInsulin: false) {
            let predNoFuture = LoopAlgorithm.generatePrediction(
                start: t,
                glucoseHistory: inputNoFuture.glucose,
                doses: inputNoFuture.doses,
                carbEntries: inputNoFuture.carbs,
                basal: inputNoFuture.basal,
                sensitivity: inputNoFuture.sensitivity,
                carbRatio: inputNoFuture.carbRatio,
                algorithmEffectsOptions: .all,
                useIntegralRetrospectiveCorrection: config.useIntegralRC,
                includingPositiveVelocityAndRC: config.includingPositiveVelocityAndRC,
                useMidAbsorptionISF: config.useMidAbsorptionISF,
                carbAbsorptionModel: config.carbAbsorptionModel.model,
                momentumVelocityMaximum: momentumCap,
                useAsymmetricMomentum: config.useAsymmetricMomentum,
                momentumAlphaSlow: config.momentumAlphaSlow,
                momentumAlphaFast: config.momentumAlphaFast
            )
            noFuturePredicted = predNoFuture.glucose
        }

        let doseRec = Self.computeDoseRecommendation(
            prediction: prediction,
            at: t,
            input: input,
            suspendThreshold: therapy.suspendThreshold,
            maxBolus: therapy.maxBolus,
            maxBasalRate: therapy.maxBasalRate,
            insulinType: therapy.insulinType,
            evalStep: config.evalStep,
            applicationFactor: 0.4
        )

        // Per-component effect samples for drift diagnostics.
        let insEff = prediction.effects.insulin
        let rcEff  = prediction.effects.retrospectiveCorrection
        let momEff = prediction.effects.momentum
        let rcBase  = rcEff.first?.quantity.doubleValue(for: .milligramsPerDeciliter)
        let momBase = momEff.first?.quantity.doubleValue(for: .milligramsPerDeciliter)
        let insBaseT = Self.sampleEffect(insEff, at: t)
        let ins60   = Self.sampleEffect(insEff, at: t.addingTimeInterval(60 * 60)).flatMap { v in
            insBaseT.map { v - $0 }
        }
        let ins90   = Self.sampleEffect(insEff, at: t.addingTimeInterval(90 * 60)).flatMap { v in
            insBaseT.map { v - $0 }
        }
        let rc60    = Self.sampleEffect(rcEff, at: t.addingTimeInterval(60 * 60)).flatMap { v in
            rcBase.map { v - $0 }
        }
        let rc90    = Self.sampleEffect(rcEff, at: t.addingTimeInterval(90 * 60)).flatMap { v in
            rcBase.map { v - $0 }
        }
        let mom30   = Self.sampleEffect(momEff, at: t.addingTimeInterval(30 * 60)).flatMap { v in
            momBase.map { v - $0 }
        }

        return PredictionRecord(
            evaluatedAt: t,
            predicted: prediction.glucose,
            predictedNoFutureInsulin: noFuturePredicted,
            iob: prediction.activeInsulin,
            cob: prediction.activeCarbs,
            recommendedDeltaU: doseRec?.deltaU,
            recommendedBolus: doseRec?.bolus,
            recommendedTempBasalRate: doseRec?.tempBasalRate,
            scheduledBasalRate: doseRec?.scheduledBasalRate,
            insulinEffectΔ60: ins60,
            insulinEffectΔ90: ins90,
            rcEffect60: rc60,
            rcEffect90: rc90,
            momentumEffect30: mom30
        )
    }

    // MARK: – Sensitivity scaling

    /// Apply global + per-hour ISF multipliers to an absolute sensitivity timeline.
    ///
    /// If `hourlyMultipliers` is provided (24 elements), each entry is split at
    /// local-hour boundaries (per `timezone`) and the per-hour multiplier is
    /// applied on top of the global one. With `useMidAbsorptionISF = true`
    /// downstream, this means the ISF active at the time the insulin effect
    /// fires is what gets used for that effect (not ahead-of-effect).
    static func applySensitivityScaling(
        _ sensitivity: [AbsoluteScheduleValue<LoopQuantity>],
        globalMultiplier: Double,
        hourlyMultipliers: [Double]?,
        timezone: TimeZone
    ) -> [AbsoluteScheduleValue<LoopQuantity>] {
        // Fast path: nothing to do
        if globalMultiplier == 1.0 && hourlyMultipliers == nil {
            return sensitivity
        }
        // Fast path: global only, no hour split
        if hourlyMultipliers == nil {
            return sensitivity.map { entry in
                let unit = entry.value.unit
                return AbsoluteScheduleValue(
                    startDate: entry.startDate,
                    endDate: entry.endDate,
                    value: LoopQuantity(
                        unit: unit,
                        doubleValue: entry.value.doubleValue(for: unit) * globalMultiplier
                    )
                )
            }
        }
        // Per-hour: split each entry at local-hour boundaries — but only
        // where the resulting scaled VALUE would differ from the previous
        // segment. When several consecutive hours share the same multiplier
        // and the underlying base ISF doesn't change, we coalesce. This keeps
        // the output schedule small (matters because downstream `glucoseEffects*`
        // is O(doses × schedule_entries) per step).
        guard let hourly = hourlyMultipliers, hourly.count == 24 else {
            return sensitivity
        }
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = timezone
        var out: [AbsoluteScheduleValue<LoopQuantity>] = []
        out.reserveCapacity(sensitivity.count * 4)
        let eps = 1e-9
        for entry in sensitivity {
            let unit = entry.value.unit
            let baseValue = entry.value.doubleValue(for: unit)
            var t = entry.startDate
            while t < entry.endDate {
                let localHour = cal.component(.hour, from: t)
                let comps = cal.dateComponents([.year, .month, .day, .hour], from: t)
                guard let topOfHour = cal.date(from: comps) else { break }
                let nextHour = cal.date(byAdding: .hour, value: 1, to: topOfHour) ?? entry.endDate
                let chunkEnd = min(nextHour, entry.endDate)
                let mult = globalMultiplier * hourly[localHour]
                let scaledValue = baseValue * mult
                // Coalesce with previous segment if value matches and timeline is contiguous
                if let last = out.last,
                   last.endDate == t,
                   abs(last.value.doubleValue(for: unit) - scaledValue) < eps {
                    out[out.count - 1] = AbsoluteScheduleValue(
                        startDate: last.startDate,
                        endDate: chunkEnd,
                        value: last.value
                    )
                } else {
                    out.append(AbsoluteScheduleValue(
                        startDate: t,
                        endDate: chunkEnd,
                        value: LoopQuantity(unit: unit, doubleValue: scaledValue)
                    ))
                }
                t = chunkEnd
            }
        }
        return out
    }

    // MARK: – Effect sampling

    /// Linear-interpolate a GlucoseEffect time-series at an arbitrary date.
    /// Returns nil outside the series range.
    static func sampleEffect(_ effects: [GlucoseEffect], at t: Date) -> Double? {
        guard !effects.isEmpty else { return nil }
        if t <= effects.first!.startDate {
            return effects.first!.quantity.doubleValue(for: .milligramsPerDeciliter)
        }
        if t >= effects.last!.startDate {
            return effects.last!.quantity.doubleValue(for: .milligramsPerDeciliter)
        }
        // Binary search for first index with startDate >= t.
        var lo = 0, hi = effects.count
        while lo < hi {
            let mid = (lo + hi) / 2
            if effects[mid].startDate < t { lo = mid + 1 } else { hi = mid }
        }
        guard lo > 0, lo < effects.count else { return nil }
        let a = effects[lo - 1], b = effects[lo]
        let span = b.startDate.timeIntervalSince(a.startDate)
        guard span > 0 else { return a.quantity.doubleValue(for: .milligramsPerDeciliter) }
        let frac = t.timeIntervalSince(a.startDate) / span
        let va = a.quantity.doubleValue(for: .milligramsPerDeciliter)
        let vb = b.quantity.doubleValue(for: .milligramsPerDeciliter)
        return va + (vb - va) * frac
    }

    // MARK: – Dose recommendation

    struct DoseOutput {
        let bolus: Double
        let tempBasalRate: Double
        let scheduledBasalRate: Double
        let deltaU: Double  // total insulin delivered in next evalStep vs scheduled
    }

    /// Runs Loop's dose-recommendation logic from a forecast, returning the
    /// total insulin Loop would deliver in the next evalStep window compared
    /// to continuing scheduled basal. Used to compute delivery-based ODR/UDR.
    ///
    /// Uses the `.automaticBolus` recommendation path (equivalent to Loop's
    /// default automatic dosing). A more complete implementation would switch
    /// based on config, but most deployed configurations use automaticBolus.
    static func computeDoseRecommendation<C: CarbEntry>(
        prediction: LoopPrediction<C>,
        at t: Date,
        input: PredictionInput,
        suspendThreshold: LoopQuantity?,
        maxBolus: Double,
        maxBasalRate: Double,
        insulinType: ExponentialInsulinModelPreset,
        evalStep: TimeInterval,
        applicationFactor: Double = 0.4
    ) -> DoseOutput? {
        guard let scheduledBasalEntry = input.basal.first(where: { $0.startDate <= t && $0.endDate > t })
            ?? input.basal.closestPrior(to: t) else { return nil }
        let scheduledRate = scheduledBasalEntry.value

        let suspend = suspendThreshold ?? input.target.closestPrior(to: t)?.value.lowerBound
        guard let suspend else { return nil }

        // Use the FULL sensitivity schedule from input, not just the at-t value.
        // The schedule may include per-future-time ISF boosts (e.g., from
        // --candidate-isf-csv) that Loop's dose-calc must see across its 6h
        // forecast horizon — otherwise the boost only affects the prediction
        // but not the correction sizing, and the oracle is silently no-op.
        guard !input.sensitivity.isEmpty else { return nil }
        let maxActiveInsulin = maxBolus * 2
        let activeInsulin = prediction.activeInsulin ?? 0

        let correction = LoopAlgorithm.insulinCorrection(
            prediction: prediction.glucose,
            at: t,
            target: input.target,
            suspendThreshold: suspend,
            sensitivity: input.sensitivity,
            insulinModel: insulinType.model
        )
        let recommendation = LoopAlgorithm.recommendAutomaticDose(
            for: correction,
            applicationFactor: applicationFactor,
            neutralBasalRate: scheduledRate,
            activeInsulin: activeInsulin,
            maxBolus: maxBolus,
            maxBasalRate: maxBasalRate,
            maxActiveInsulin: maxActiveInsulin
        )
        let bolus = recommendation.bolusUnits ?? 0
        let tempRate = recommendation.basalAdjustment.unitsPerHour

        let basalDeltaU = (tempRate - scheduledRate) * evalStep / 3600
        let deltaU = bolus + basalDeltaU

        return DoseOutput(
            bolus: bolus,
            tempBasalRate: tempRate,
            scheduledBasalRate: scheduledRate,
            deltaU: deltaU
        )
    }
}
