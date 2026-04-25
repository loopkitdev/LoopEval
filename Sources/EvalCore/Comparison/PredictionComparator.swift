// PredictionComparator.swift — compare predictions to actual CGM at each horizon

import Foundation

/// One horizon's worth of (predicted, actual) error pairs.
public struct HorizonResult: Sendable {
    public let horizon: TimeInterval
    public let errors: [(predicted: Double, actual: Double)] // mg/dL pairs

    public var count: Int { errors.count }

    public init(horizon: TimeInterval, errors: [(predicted: Double, actual: Double)]) {
        self.horizon = horizon
        self.errors  = errors
    }
}

/// Compares a set of `PredictionRecord`s against actual CGM samples
/// at multiple forecast horizons.
public struct PredictionComparator {

    /// Compare predictions to actual CGM at each forecast horizon.
    ///
    /// - Parameters:
    ///   - predictions: Prediction records from the evaluation sweep.
    ///   - actual: Actual CGM samples (raw or Kalman-smoothed — caller decides).
    ///   - horizons: Forecast horizons to evaluate, in seconds.
    /// - Returns: One `HorizonResult` per horizon (same order).
    public static func compare(
        predictions: [PredictionRecord],
        actual: [EvalGlucoseSample],
        horizons: [TimeInterval]
    ) -> [HorizonResult] {
        // Sort once up front — `interpolate` requires sorted input and that
        // contract is enforced here so the inner loop is O(log N) per call.
        let sortedActual = actual.sorted { $0.startDate < $1.startDate }
        return horizons.map { horizon in
            var errors: [(predicted: Double, actual: Double)] = []

            for record in predictions {
                let targetDate = record.evaluatedAt.addingTimeInterval(horizon)

                guard
                    let pred = record.predictedValue(atHorizon: horizon),
                    let act  = GlucoseInterpolator.interpolate(samples: sortedActual, at: targetDate)
                else { continue }

                errors.append((predicted: pred, actual: act))
            }

            return HorizonResult(horizon: horizon, errors: errors)
        }
    }
}
