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

    /// Pre-fetch all data needed for an evaluation (with appropriate buffers).
    ///
    /// Exposed for reuse in parameter sweeps — fetch once, sweep many configs.
    public func prefetchData(
        for interval: DateInterval,
        config: EvalConfig
    ) async throws -> PreloadedData {
        // Add buffers large enough for any evaluation step in the window:
        //   glucose:  lookback from earliest possible t
        //   doses:    lookback + optional future insulin
        //   carbs:    8h back + 6h future
        //   therapy:  full range including ISF t+8h extension

        let glucoseBufferStart = interval.start.addingTimeInterval(
            -config.glucoseLookbackHours * 3600
        )
        let insulinBufferStart = interval.start.addingTimeInterval(
            -config.insulinLookbackHours * 3600
        )
        let carbBufferStart = interval.start.addingTimeInterval(-8 * 3600)
        let therapyBufferEnd = interval.end.addingTimeInterval(8 * 3600)
        let doseBufferEnd: Date
        if config.includeFutureInsulin {
            doseBufferEnd = interval.end.addingTimeInterval(6 * 3600)
        } else {
            doseBufferEnd = interval.end
        }

        let glucoseInterval  = DateInterval(start: glucoseBufferStart, end: interval.end.addingTimeInterval(10 * 60))
        let doseInterval     = DateInterval(start: insulinBufferStart, end: doseBufferEnd)
        let carbInterval     = DateInterval(start: carbBufferStart, end: interval.end.addingTimeInterval(6 * 3600))
        let therapyInterval  = DateInterval(start: insulinBufferStart, end: therapyBufferEnd)

        async let glucose  = dataSource.getGlucoseValues(interval: glucoseInterval)
        async let doses    = dataSource.getDoses(interval: doseInterval)
        async let carbs    = dataSource.getCarbEntries(interval: carbInterval)
        async let therapy  = dataSource.getTherapyTimeline(interval: therapyInterval)

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

        // Compute total steps for progress reporting
        let totalDuration = interval.duration
        let totalSteps = totalDuration > 0
            ? Int(totalDuration / config.evalStep) + 1
            : 1

        var stepIndex = 0
        var t = interval.start

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
                    // gradualTransitionsThreshold: use default (40.0)
                )
                predictions.append(
                    PredictionRecord(evaluatedAt: t, predicted: prediction.glucose)
                )
            } else {
                skippedCount += 1
            }

            t = t.addingTimeInterval(config.evalStep)
            stepIndex += 1
        }

        // Final progress
        progress?(1.0)

        // Actual CGM is the raw glucose within the evaluation interval
        let actualGlucose = data.glucose.filter {
            $0.startDate >= interval.start && $0.startDate <= interval.end
        }

        return EvaluationResult(
            interval: interval,
            config: config,
            predictions: predictions,
            actual: actualGlucose,
            skippedCount: skippedCount
        )
    }
}
