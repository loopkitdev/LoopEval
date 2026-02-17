// PreloadedData.swift — all data pre-fetched for an evaluation run

import Foundation
import LoopAlgorithm

/// All data required for a sweep, pre-fetched once and shared across all
/// evaluation steps (or all configs in a parameter sweep).
///
/// Designed to be pre-loaded with generous buffers so individual
/// `buildInput(at:)` calls can slice without additional I/O.
public struct PreloadedData: Sendable {
    public let glucose: [EvalGlucoseSample]
    public let doses: [EvalInsulinDose]
    public let carbs: [EvalCarbEntry]
    public let therapyTimeline: TherapyTimeline

    public init(
        glucose: [EvalGlucoseSample],
        doses: [EvalInsulinDose],
        carbs: [EvalCarbEntry],
        therapyTimeline: TherapyTimeline
    ) {
        self.glucose         = glucose
        self.doses           = doses
        self.carbs           = carbs
        self.therapyTimeline = therapyTimeline
    }
}
