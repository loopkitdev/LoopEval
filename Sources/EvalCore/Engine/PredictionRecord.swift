// PredictionRecord.swift — a single prediction made at a point in time

import Foundation
import LoopAlgorithm

/// A single prediction made at a point in time.
public struct PredictionRecord: Sendable {
    /// The time at which this prediction was generated.
    public let evaluatedAt: Date

    /// The predicted glucose trajectory (from LoopAlgorithm.generatePrediction).
    /// Sorted ascending by startDate, starting at or very near `evaluatedAt`.
    public let predicted: [PredictedGlucoseValue]

    /// Insulin on board (units) at the time of prediction.
    public let iob: Double?
    /// Carbs on board (grams) at the time of prediction.
    public let cob: Double?

    public init(evaluatedAt: Date, predicted: [PredictedGlucoseValue],
                iob: Double? = nil, cob: Double? = nil) {
        self.evaluatedAt = evaluatedAt
        self.predicted   = predicted
        self.iob         = iob
        self.cob         = cob
    }

    // MARK: – Horizon lookup

    /// Returns the interpolated predicted glucose value (mg/dL) at a specific
    /// forecast horizon relative to `evaluatedAt`.
    ///
    /// Uses linear interpolation between adjacent predicted points.
    /// Returns `nil` if the prediction curve doesn't reach the requested horizon.
    public func predictedValue(atHorizon horizon: TimeInterval) -> Double? {
        guard !predicted.isEmpty else { return nil }

        let targetDate = evaluatedAt.addingTimeInterval(horizon)

        // Fast path: exact match on first or last
        if let first = predicted.first, targetDate <= first.startDate {
            guard targetDate == first.startDate else { return nil }  // before curve → out of range
            return first.quantity.doubleValue(for: .milligramsPerDeciliter)
        }
        if let last = predicted.last, targetDate >= last.startDate {
            guard targetDate == last.startDate else {
                // Clamp to last value only if within one 5-min step (rounding tolerance)
                let gap = targetDate.timeIntervalSince(last.startDate)
                if gap <= 5 * 60 + 1 {
                    return last.quantity.doubleValue(for: .milligramsPerDeciliter)
                }
                return nil
            }
            return last.quantity.doubleValue(for: .milligramsPerDeciliter)
        }

        // Find the two adjacent points that bracket targetDate
        for i in 0..<(predicted.count - 1) {
            let p0 = predicted[i]
            let p1 = predicted[i + 1]
            guard p0.startDate <= targetDate && targetDate <= p1.startDate else { continue }

            let interval = p1.startDate.timeIntervalSince(p0.startDate)
            guard interval > 0 else {
                return p0.quantity.doubleValue(for: .milligramsPerDeciliter)
            }

            let t = targetDate.timeIntervalSince(p0.startDate) / interval
            let v0 = p0.quantity.doubleValue(for: .milligramsPerDeciliter)
            let v1 = p1.quantity.doubleValue(for: .milligramsPerDeciliter)
            return v0 + t * (v1 - v0)
        }

        return nil
    }
}
