// GlucoseInterpolator.swift — linear interpolation of actual CGM readings

import Foundation

public struct GlucoseInterpolator {

    /// Maximum gap between CGM readings before we refuse to interpolate.
    public static let maxGapForInterpolation: TimeInterval = 20 * 60 // 20 minutes

    /// Linear interpolation of actual CGM readings at a target date.
    ///
    /// - Returns: Interpolated mg/dL value, or `nil` if:
    ///   - `date` is before the first sample or after the last sample (no extrapolation)
    ///   - The gap between bracketing samples exceeds `maxGapForInterpolation`
    ///   - `samples` is empty
    public static func interpolate(
        samples: [EvalGlucoseSample],
        at date: Date
    ) -> Double? {
        guard !samples.isEmpty else { return nil }

        // Sort defensively
        let sorted = samples.sorted { $0.startDate < $1.startDate }

        // No extrapolation: date must be within the data range
        guard let first = sorted.first, let last = sorted.last else { return nil }
        guard date >= first.startDate && date <= last.startDate else { return nil }

        // Find last sample with startDate <= date
        guard let beforeIdx = sorted.lastIndex(where: { $0.startDate <= date }) else { return nil }
        let before = sorted[beforeIdx]

        // Find first sample with startDate >= date
        guard let afterIdx = sorted.firstIndex(where: { $0.startDate >= date }) else { return nil }
        let after = sorted[afterIdx]

        // Exact match
        if before.startDate == after.startDate {
            return before.quantity.doubleValue(for: .milligramsPerDeciliter)
        }

        // Check gap
        let gap = after.startDate.timeIntervalSince(before.startDate)
        guard gap <= maxGapForInterpolation else { return nil }

        // Linear interpolation
        let t = date.timeIntervalSince(before.startDate) / gap
        let v0 = before.quantity.doubleValue(for: .milligramsPerDeciliter)
        let v1 = after.quantity.doubleValue(for: .milligramsPerDeciliter)
        return v0 + t * (v1 - v0)
    }
}
