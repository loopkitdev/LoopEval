// EvaluationResult.swift — the output of a full evaluation sweep

import Foundation

/// The complete result of running the evaluation engine over a time interval.
public struct EvaluationResult: Sendable {
    /// The evaluation interval (from config.start to config.end).
    public let interval: DateInterval

    /// The configuration used for this evaluation.
    public let config: EvalConfig

    /// All successfully computed prediction records.
    public let predictions: [PredictionRecord]

    /// Raw actual CGM samples covering the interval (unsmoothed).
    public let actual: [EvalGlucoseSample]

    /// Total predictions computed (== predictions.count).
    public let predictionCount: Int

    /// Steps where `buildInput` returned nil (skipped due to insufficient data).
    public let skippedCount: Int

    public init(
        interval: DateInterval,
        config: EvalConfig,
        predictions: [PredictionRecord],
        actual: [EvalGlucoseSample],
        skippedCount: Int
    ) {
        self.interval        = interval
        self.config          = config
        self.predictions     = predictions
        self.actual          = actual
        self.predictionCount = predictions.count
        self.skippedCount    = skippedCount
    }
}
