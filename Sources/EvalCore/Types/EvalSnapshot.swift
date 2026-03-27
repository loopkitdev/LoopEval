// EvalSnapshot.swift — serialisable record of a single evaluation run

import Foundation

/// A complete, self-contained record of one `loop-eval evaluate` run.
/// Saved to disk as JSON so it can be loaded later by `loop-eval compare`.
public struct EvalSnapshot: Codable, Sendable {

    // MARK: – Identity

    /// Human-readable label (defaults to the file path when not explicitly set).
    public let label: String?

    /// Wall-clock time the run completed.
    public let runDate: Date

    // MARK: – Evaluated period

    public let intervalStart: Date
    public let intervalEnd: Date

    // MARK: – Algorithm config

    public let insulinType: String
    public let config: EvalConfig

    // MARK: – Run statistics

    public let predictionCount: Int
    public let skippedCount: Int

    // MARK: – Results

    public let score: AggregateScore

    // MARK: – Init

    public init(
        label: String?,
        runDate: Date,
        intervalStart: Date,
        intervalEnd: Date,
        insulinType: String,
        config: EvalConfig,
        predictionCount: Int,
        skippedCount: Int,
        score: AggregateScore
    ) {
        self.label           = label
        self.runDate         = runDate
        self.intervalStart   = intervalStart
        self.intervalEnd     = intervalEnd
        self.insulinType     = insulinType
        self.config          = config
        self.predictionCount = predictionCount
        self.skippedCount    = skippedCount
        self.score           = score
    }
}
