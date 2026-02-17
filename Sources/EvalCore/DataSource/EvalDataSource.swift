// EvalDataSource.swift — abstract data source protocol for evaluation
//
// Conforms to Sendable so implementations can be passed across actors.
// All methods are async to support both live Nightscout HTTP calls and
// cached/file-based implementations.

import Foundation
import LoopAlgorithm

/// Abstract data source used by the evaluation engine.
/// All implementations must be `Sendable` so they can be stored in actors.
public protocol EvalDataSource: Sendable {
    /// CGM readings within `interval` (filtered to SGV entries only).
    func getGlucoseValues(interval: DateInterval) async throws -> [EvalGlucoseSample]

    /// Insulin deliveries overlapping or near `interval`.
    func getDoses(interval: DateInterval) async throws -> [EvalInsulinDose]

    /// Carbohydrate entries within `interval`.
    func getCarbEntries(interval: DateInterval) async throws -> [EvalCarbEntry]

    /// All therapy settings expanded as absolute schedule values covering `interval`.
    func getTherapyTimeline(interval: DateInterval) async throws -> TherapyTimeline
}
