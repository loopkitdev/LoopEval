// ErrorMetrics.swift — per-horizon prediction error statistics

import Foundation

/// Comprehensive error metrics for a single forecast horizon.
public struct HorizonMetrics: Codable, Sendable {
    /// Horizon in seconds.
    public let horizon: TimeInterval

    /// Number of (predicted, actual) pairs used to compute metrics.
    public let sampleCount: Int

    /// Root-mean-square error (mg/dL).
    public let rmse: Double

    /// Mean absolute error (mg/dL).
    public let mae: Double

    /// Mean signed error, i.e. prediction bias.  Positive = predicting too high.
    public let meanError: Double

    /// 10th percentile of signed errors (predicted − actual).
    public let percentile10: Double

    /// 90th percentile of signed errors (predicted − actual).
    public let percentile90: Double

    /// Low Blood Glucose Index of actual values at this horizon.
    public let lbgi: Double

    /// High Blood Glucose Index of actual values at this horizon.
    public let hbgi: Double

    /// Blood Glucose Risk Index (LBGI + HBGI) of actual values.
    public let bgri: Double

    /// RMSE weighted by the low-BG risk of each actual value.
    public let lowWeightedRMSE: Double

    /// RMSE weighted by the high-BG risk of each actual value.
    public let highWeightedRMSE: Double

    /// **Dangerous Over-prediction Score (DOS)**
    /// Penalises over-predictions when actual BG is below `targetLow`.
    /// Zero when BG is in-range or high.  Primary safety metric for avoidable lows.
    public let dos: Double

    /// **Dangerous Under-prediction Score (DUS)**
    /// Penalises under-predictions when actual BG is above `targetHigh`.
    /// Zero when BG is in-range or low.  Primary safety metric for avoidable highs.
    public let dus: Double

    /// Combined primary danger score: `dos + dus`.
    public var dangerScore: Double { dos + dus }
}

public struct ErrorMetrics {

    // MARK: – Single horizon

    public static func compute(
        result: HorizonResult,
        targetLow: Double = 100.0,
        targetHigh: Double = 115.0
    ) -> HorizonMetrics {
        let errors = result.errors
        let n = errors.count
        guard n > 0 else {
            return HorizonMetrics(
                horizon: result.horizon, sampleCount: 0,
                rmse: 0, mae: 0, meanError: 0,
                percentile10: 0, percentile90: 0,
                lbgi: 0, hbgi: 0, bgri: 0,
                lowWeightedRMSE: 0, highWeightedRMSE: 0,
                dos: 0, dus: 0
            )
        }

        let dN = Double(n)
        let diffs = errors.map { $0.predicted - $0.actual }
        let rmse  = sqrt(diffs.map { $0 * $0 }.reduce(0, +) / dN)
        let mae   = diffs.map { abs($0) }.reduce(0, +) / dN
        let mean  = diffs.reduce(0, +) / dN

        // Percentiles via linear interpolation
        let sorted = diffs.sorted()
        let p10 = percentile(sorted, 0.10)
        let p90 = percentile(sorted, 0.90)

        let actuals = errors.map { $0.actual }
        let lbgi = BloodGlucoseRisk.lbgi(actuals)
        let hbgi = BloodGlucoseRisk.hbgi(actuals)
        let bgri = lbgi + hbgi

        let lowWRMSE  = BloodGlucoseRisk.lowWeightedRMSE(errors: errors)
        let highWRMSE = BloodGlucoseRisk.highWeightedRMSE(errors: errors)

        let dos = BloodGlucoseRisk.dangerousOverpredictionScore(errors: errors, targetLow: targetLow)
        let dus = BloodGlucoseRisk.dangerousUnderpredictionScore(errors: errors, targetHigh: targetHigh)

        return HorizonMetrics(
            horizon: result.horizon,
            sampleCount: n,
            rmse: rmse,
            mae: mae,
            meanError: mean,
            percentile10: p10,
            percentile90: p90,
            lbgi: lbgi,
            hbgi: hbgi,
            bgri: bgri,
            lowWeightedRMSE: lowWRMSE,
            highWeightedRMSE: highWRMSE,
            dos: dos,
            dus: dus
        )
    }

    // MARK: – Multiple horizons

    public static func compute(
        results: [HorizonResult],
        targetLow: Double = 100.0,
        targetHigh: Double = 115.0
    ) -> [HorizonMetrics] {
        results.map { compute(result: $0, targetLow: targetLow, targetHigh: targetHigh) }
    }

    // MARK: – Helpers

    /// Linear-interpolation percentile on a pre-sorted array.
    private static func percentile(_ sorted: [Double], _ p: Double) -> Double {
        guard !sorted.isEmpty else { return 0 }
        guard sorted.count > 1 else { return sorted[0] }
        let idx    = p * Double(sorted.count - 1)
        let lo     = Int(idx)
        let hi     = min(lo + 1, sorted.count - 1)
        let frac   = idx - Double(lo)
        return sorted[lo] + frac * (sorted[hi] - sorted[lo])
    }
}
