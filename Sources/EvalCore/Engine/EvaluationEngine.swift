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
                ircDropGainScale: config.ircDropGainScale,
                ircRiseGainScale: config.ircRiseGainScale,
                ircLowMemoryScale: config.ircLowMemoryScale,
                ircDropDurationScale: config.ircDropDurationScale,
                ircRiseDurationScale: config.ircRiseDurationScale,
                uamProjectionMinutes: config.uamProjectionMinutes,
                earlyRiseMinutes: config.earlyRiseMinutes,
                earlyRiseGain: config.earlyRiseGain,
                earlyRiseBgLow: config.earlyRiseBgLow,
                earlyRiseBgHigh: config.earlyRiseBgHigh,
                earlyRiseSlopeThreshold: config.earlyRiseSlopeThreshold,
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
                ircDropGainScale: config.ircDropGainScale,
                ircRiseGainScale: config.ircRiseGainScale,
                ircLowMemoryScale: config.ircLowMemoryScale,
                ircDropDurationScale: config.ircDropDurationScale,
                ircRiseDurationScale: config.ircRiseDurationScale,
                uamProjectionMinutes: config.uamProjectionMinutes,
                earlyRiseMinutes: config.earlyRiseMinutes,
                earlyRiseGain: config.earlyRiseGain,
                earlyRiseBgLow: config.earlyRiseBgLow,
                earlyRiseBgHigh: config.earlyRiseBgHigh,
                earlyRiseSlopeThreshold: config.earlyRiseSlopeThreshold,
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
                ircDropGainScale: config.ircDropGainScale,
                ircRiseGainScale: config.ircRiseGainScale,
                ircLowMemoryScale: config.ircLowMemoryScale,
                ircDropDurationScale: config.ircDropDurationScale,
                ircRiseDurationScale: config.ircRiseDurationScale,
                uamProjectionMinutes: config.uamProjectionMinutes,
                earlyRiseMinutes: config.earlyRiseMinutes,
                earlyRiseGain: config.earlyRiseGain,
                earlyRiseBgLow: config.earlyRiseBgLow,
                earlyRiseBgHigh: config.earlyRiseBgHigh,
                earlyRiseSlopeThreshold: config.earlyRiseSlopeThreshold,
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
        var manualBolusRec: Double = 0  // candidate's recommended MANUAL bolus at this step (full correction, clamped to maxBolus)
    }

    /// Runs Loop's dose-recommendation logic from a forecast, returning the
    /// total insulin Loop would deliver in the next evalStep window compared
    /// to continuing scheduled basal. Used to compute delivery-based ODR/UDR.
    ///
    /// Glucose-based application factor (GBAF): piecewise-linear ramp of the
    /// auto-bolus applicationFactor from `factorLow` (at/below `lowAnchor`) to
    /// `factorHigh` (at/above `highAnchor`). More aggressive dosing only when
    /// BG is heading high; near/below target it stays conservative.
    public static func glucoseBasedApplicationFactor(
        currentBG: Double, lowAnchor: Double, highAnchor: Double,
        factorLow: Double, factorHigh: Double
    ) -> Double {
        guard highAnchor > lowAnchor else { return factorLow }
        if currentBG <= lowAnchor { return factorLow }
        if currentBG >= highAnchor { return factorHigh }
        let frac = (currentBG - lowAnchor) / (highAnchor - lowAnchor)
        return factorLow + frac * (factorHigh - factorLow)
    }

    /// Suspension-mitigated, uncertainty-bounded maximum dose (units).
    ///
    /// Returns the largest additional dose `d` such that, for EVERY horizon τ, the worst-case
    /// trajectory — insulin effect amplified by (1+k) (sensitivity could be more effective than
    /// nominal) — WITH the maximum corrective basal suspension applied from now, still stays at or
    /// above `lowThreshold`:
    ///
    ///   P_nom(τ) + k·eIns(τ) + Suspend(τ) − (1+k)·d·ISF(τ)·delivered(τ)  ≥  L     for all τ
    ///
    /// where eIns(τ) is the (≤0) glucose effect of CURRENT IOB by τ, delivered(τ)=1−percentEffect
    /// Remaining(τ) is the acted fraction of a dose given now, and Suspend(τ) is the +BG credit
    /// from withholding scheduled basal over [0,τ] (grows with τ, so it's small early/low-BG and
    /// large far-out/high-BG — the recourse we have if a sensitivity surprise appears). Each term
    /// is linear in `d`, so the cap is closed-form: d ≤ min_τ (P_nom+k·eIns+Suspend−L)/((1+k)·ISF·delivered).
    /// This is a LEVEL cap on committed insulin (re-derived each cycle), so it does not wind up to
    /// full need at a persistent high the way repeated partial application does.
    static func uncertaintyMaxDose(
        predictedGlucose: [PredictedGlucoseValue],
        insulinEffect: [GlucoseEffect],
        sensitivity: [AbsoluteScheduleValue<LoopQuantity>],
        scheduledBasalRate: Double,
        insulinModel: InsulinModel,
        k: Double,
        lowThreshold: Double,
        // Decouple from autosens: when autosens lowered ISF (factor < 1, "resistant"), the cap's
        // WORST CASE should hedge that the resistance estimate is wrong and insulin is actually as
        // effective as nominal (or more). m = max(1, 1/factor) scales the worst-case insulin
        // effectiveness back up to nominal. 1.0 = coupled (use the adjusted ISF as-is).
        autosensFactor: Double = 1.0
    ) -> Double {
        let m = Swift.max(1.0, 1.0 / Swift.max(0.05, autosensFactor))
        let mgdl = LoopUnit.milligramsPerDeciliter
        guard let t0 = predictedGlucose.first?.startDate, predictedGlucose.count > 1 else { return 0 }
        // Raw cumulative insulin glucose effect at a date. The effect timeline starts at the
        // INPUT-window start (includes historical insulin), so anchor at t0 (now) to get the
        // FUTURE effect of current IOB only.
        func insCum(_ d: Date) -> Double {
            var v = insulinEffect.first?.quantity.doubleValue(for: mgdl) ?? 0
            for e in insulinEffect { if e.startDate <= d { v = e.quantity.doubleValue(for: mgdl) } else { break } }
            return v
        }
        let insAtT0 = insCum(t0)
        func insAt(_ d: Date) -> Double { insCum(d) - insAtT0 }   // effect from now → d (≤ 0)
        func isfAt(_ d: Date) -> Double {
            sensitivity.closestPrior(to: d)?.value.doubleValue(for: mgdl)
                ?? sensitivity.first?.value.doubleValue(for: mgdl) ?? 50
        }
        // acted fraction of a unit dosed `age` ago
        func delivered(_ age: TimeInterval) -> Double {
            age <= 0 ? 0 : Swift.max(0, Swift.min(1, 1 - insulinModel.percentEffectRemaining(at: age)))
        }
        let dtHr = predictedGlucose[1].startDate.timeIntervalSince(predictedGlucose[0].startDate) / 3600.0
        let dbg = ProcessInfo.processInfo.environment["CAPDEBUG"] != nil
        var dmax = Double.greatestFiniteMagnitude
        var bTau = 0.0, bP = 0.0, bE = 0.0, bS = 0.0
        for (i, p) in predictedGlucose.enumerated() {
            let tau = p.startDate.timeIntervalSince(t0)
            if tau <= 0 { continue }
            let del = delivered(tau)
            if del <= 1e-6 { continue }
            let isf = isfAt(p.startDate)
            // max-suspension credit available by τ: withheld scheduled basal micro-doses [0,τ]
            var suspend = 0.0
            for j in 0..<i {
                let s = predictedGlucose[j].startDate.timeIntervalSince(t0)
                suspend += scheduledBasalRate * dtHr * delivered(tau - s)
            }
            suspend *= isf
            let eIns = insAt(p.startDate)
            let pnom = p.quantity.doubleValue(for: mgdl)
            // Worst-case insulin effectiveness scaled by m (autosens-decouple): existing-IOB drop,
            // suspension rescue, and the new dose's drop all use ISF×m. Non-insulin part (pnom−eIns)
            // is unchanged. m=1 reduces to pnom + k·eIns + suspend − L over (1+k)·isf·del.
            let num = pnom + eIns * ((1 + k) * m - 1) + suspend * m - lowThreshold
            let cap = num / ((1 + k) * isf * m * del)
            if cap < dmax { dmax = cap; bTau = tau/60; bP = pnom; bE = eIns; bS = suspend }
        }
        if dbg {
            FileHandle.standardError.write("  bind τ=\(Int(bTau))m Pnom=\(Int(bP)) eIns=\(Int(bE)) suspend=\(Int(bS)) -> dmax=\(String(format: "%.2f", Swift.max(0,dmax)))\n".data(using: .utf8)!)
        }
        return Swift.max(0, dmax == .greatestFiniteMagnitude ? 0 : dmax)
    }

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
        applicationFactor: Double = 0.4,
        softLowGate: Bool = false,
        // Predicted-min cutoff (mg/dL) below which the auto-bolus gate engages. nil = the
        // correction-range floor (standard Loop). e.g. 80 keeps the full application factor for
        // predicted minimums down to 80 before gating — a small step toward the uncertainty cap.
        lowGateThreshold: Double? = nil,
        // Uncertainty-bounded dosing cap: when k >= 0 and enabled, REPLACES applicationFactor +
        // the predicted-min gate with the suspension-mitigated worst-case cap. nil = off.
        // autosensFactor decouples the cap's worst-case from the autosens ISF adjustment (see
        // uncertaintyMaxDose); 1.0 = coupled.
        uncertaintyCap: (k: Double, fmax: Double, low: Double, autosensFactor: Double)? = nil
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
        // Uncertainty-bounded cap: derive the effective application factor from the
        // suspension-mitigated worst-case dose, and disable the predicted-min gate (the cap
        // already encodes future low-risk via the worst-case-with-suspension constraint).
        var effAppFactor = applicationFactor
        var gateFloor: Double? = softLowGate ? suspend.doubleValue(for: LoopUnit.milligramsPerDeciliter) : nil
        if let uc = uncertaintyCap {
            let fullUnits = correction.asPartialBolus(partialApplicationFactor: 1.0,
                                                      maxBolusUnits: .greatestFiniteMagnitude)
            if fullUnits > 1e-9 {
                let lowThr = uc.low > 0 ? uc.low : suspend.doubleValue(for: LoopUnit.milligramsPerDeciliter)
                let dmax = Self.uncertaintyMaxDose(
                    predictedGlucose: prediction.glucose,
                    insulinEffect: prediction.effects.insulin,
                    sensitivity: input.sensitivity,
                    scheduledBasalRate: scheduledRate,
                    insulinModel: insulinType.model,
                    k: uc.k,
                    lowThreshold: lowThr,
                    autosensFactor: uc.autosensFactor)
                // k REPLACES the application factor: both hedge future uncertainty, and with the
                // suspension-recourse term the cap already covers "forecast too high → BG falls →
                // suspend", so a separate AF rate-limit is redundant. Dose up to the cap each
                // cycle; fmax is the optional <100%-of-need ceiling (default 1.0).
                effAppFactor = Swift.max(0, Swift.min(uc.fmax, dmax / fullUnits))
                if ProcessInfo.processInfo.environment["CAPDEBUG"] != nil {
                    let bg0 = prediction.glucose.first?.quantity.doubleValue(for: LoopUnit.milligramsPerDeciliter) ?? 0
                    let pmin = prediction.glucose.map { $0.quantity.doubleValue(for: LoopUnit.milligramsPerDeciliter) }.min() ?? 0
                    let pmax = prediction.glucose.map { $0.quantity.doubleValue(for: LoopUnit.milligramsPerDeciliter) }.max() ?? 0
                    FileHandle.standardError.write("CAP bg0=\(Int(bg0)) pmin=\(Int(pmin)) pmax=\(Int(pmax)) iob=\(String(format: "%.1f", activeInsulin)) low=\(Int(lowThr)) full=\(String(format: "%.2f", fullUnits)) dmax=\(String(format: "%.2f", dmax)) AF=\(String(format: "%.2f", effAppFactor))\n".data(using: .utf8)!)
                }
            } else {
                effAppFactor = 0
            }
            gateFloor = -1e9   // disable the predicted-min gate (ramp factor ≈ 1)
        }
        let recommendation = LoopAlgorithm.recommendAutomaticDose(
            for: correction,
            applicationFactor: effAppFactor,
            neutralBasalRate: scheduledRate,
            activeInsulin: activeInsulin,
            maxBolus: maxBolus,
            maxBasalRate: maxBasalRate,
            maxActiveInsulin: maxActiveInsulin,
            lowGateRampFloor: gateFloor,
            gateThreshold: uncertaintyCap == nil ? lowGateThreshold : nil
        )
        let bolus = recommendation.bolusUnits ?? 0
        let tempRate = recommendation.basalAdjustment.unitsPerHour

        let basalDeltaU = (tempRate - scheduledRate) * evalStep / 3600
        let deltaU = bolus + basalDeltaU

        // Candidate's recommended MANUAL bolus at this step: the full correction
        // (application factor 1.0) clamped to maxBolus — what Loop's bolus screen
        // would suggest given the candidate's own forecast/IOB/COB. Used by the
        // "manual bolus = candidate recommendation" injection mode.
        let manualBolusRec = correction.asManualBolus(maxBolus: maxBolus).amount
        return DoseOutput(
            bolus: bolus,
            tempBasalRate: tempRate,
            scheduledBasalRate: scheduledRate,
            deltaU: deltaU,
            manualBolusRec: manualBolusRec
        )
    }
}
