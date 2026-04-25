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
        // Caller must pass samples sorted ascending by startDate. We binary-search
        // and skip the defensive `.sorted()` — re-sorting inside a hot loop made
        // the analyze step quadratic-in-samples and stalled long benches.
        guard let first = samples.first, let last = samples.last else { return nil }
        guard date >= first.startDate && date <= last.startDate else { return nil }

        // Binary search for the first index with startDate >= date.
        var lo = 0, hi = samples.count
        while lo < hi {
            let mid = (lo + hi) / 2
            if samples[mid].startDate < date { lo = mid + 1 } else { hi = mid }
        }
        // `lo` is now the first index with startDate >= date. The "before" sample
        // is at lo-1 unless there's an exact match at lo.
        let after = samples[lo]
        if after.startDate == date {
            return after.quantity.doubleValue(for: .milligramsPerDeciliter)
        }
        guard lo > 0 else { return nil }
        let before = samples[lo - 1]

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
