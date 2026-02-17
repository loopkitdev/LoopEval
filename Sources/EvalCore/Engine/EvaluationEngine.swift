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
        config: EvalConfig = .default,
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

        var predictions: [PredictionRecord] = []
        var skippedCount = 0

        // First evaluated step is after the warmup period, so every prediction
        // has a full insulin/glucose history window behind it.
        let evalStart = interval.start.addingTimeInterval(config.evalWarmupHours * 3600)

        // Compute total steps for progress reporting (eval window only, not warmup)
        let evalDuration = interval.end.timeIntervalSince(evalStart)
        let totalSteps = evalDuration > 0
            ? Int(evalDuration / config.evalStep) + 1
            : 1

        var stepIndex = 0
        var t = evalStart

        while t <= interval.end {
            // Report progress
            if let progress, totalSteps > 1 {
                let fraction = Double(stepIndex) / Double(totalSteps - 1)
                progress(min(fraction, 1.0))
            }

            if let input = builder.buildInput(at: t) {
                let prediction = LoopAlgorithm.generatePrediction(
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
                    carbAbsorptionModel: config.carbAbsorptionModel.model
                )

                // When using future insulin, also compute the no-future-insulin
                // version so Panel 3 can overlay both curves for comparison.
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
                        carbAbsorptionModel: config.carbAbsorptionModel.model
                    )
                    noFuturePredicted = predNoFuture.glucose
                }

                predictions.append(
                    PredictionRecord(evaluatedAt: t, predicted: prediction.glucose,
                                     predictedNoFutureInsulin: noFuturePredicted,
                                     iob: prediction.activeInsulin, cob: prediction.activeCarbs)
                )
            } else {
                skippedCount += 1
            }

            t = t.addingTimeInterval(config.evalStep)
            stepIndex += 1
        }

        // Final progress
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
}
