// AggregateScore.swift — Gaussian time-weighted aggregate score

import Foundation

/// Time-weighted aggregate score across all forecast horizons.
/// Uses a Gaussian weight centered on `peakHorizon` to emphasize
/// the most clinically important prediction windows.
public struct AggregateScore: Codable, Sendable {

    /// Metrics for each individual horizon.
    public let horizonMetrics: [HorizonMetrics]

    /// Gaussian-weighted average RMSE across horizons.
    public let weightedRMSE: Double

    /// Gaussian-weighted average BGRI across horizons.
    public let weightedBGRI: Double

    /// Gaussian-weighted average low-risk-weighted RMSE.
    public let weightedLowRMSE: Double

    /// Gaussian-weighted average high-risk-weighted RMSE.
    public let weightedHighRMSE: Double

    /// Gaussian-weighted Dangerous Over-prediction Score (DOS).
    /// Measures over-predictions when BG is below target — avoidable lows.
    public let weightedOverdeliveryRisk: Double

    /// Gaussian-weighted Dangerous Under-prediction Score (DUS).
    /// Measures under-predictions when BG is above target — avoidable highs.
    public let weightedUnderdeliveryRisk: Double

    /// **Primary optimization target: `weightedOverdeliveryRisk + weightedUnderdeliveryRisk`.**
    /// Lower is better.  Zero means no dangerous mispredictions outside target range.
    public let primaryScore: Double

    // MARK: – Factory

    /// Compute an aggregate score using Gaussian horizon weights.
    ///
    /// - Parameters:
    ///   - metrics: Per-horizon metrics (may be any order; all horizons contribute).
    ///   - peakHorizon: The horizon (seconds) that receives maximum weight. Default: 90 min
    ///                  (peak rapid insulin action — most consequential for dosing decisions).
    ///   - sigmaSecs: Standard deviation of the Gaussian kernel (seconds). Default: 60 min.
    public static func compute(
        metrics: [HorizonMetrics],
        peakHorizon: TimeInterval = 90 * 60,
        sigmaSecs: TimeInterval   = 60 * 60
    ) -> AggregateScore {
        guard !metrics.isEmpty else {
            return AggregateScore(
                horizonMetrics: [],
                weightedRMSE: 0, weightedBGRI: 0,
                weightedLowRMSE: 0, weightedHighRMSE: 0,
                weightedOverdeliveryRisk: 0, weightedUnderdeliveryRisk: 0,
                primaryScore: 0
            )
        }

        // Compute raw Gaussian weights
        let rawWeights = metrics.map { m -> Double in
            let diff = m.horizon - peakHorizon
            return exp(-(diff * diff) / (2.0 * sigmaSecs * sigmaSecs))
        }

        let totalWeight = rawWeights.reduce(0, +)
        guard totalWeight > 0 else {
            return AggregateScore(
                horizonMetrics: metrics,
                weightedRMSE: 0, weightedBGRI: 0,
                weightedLowRMSE: 0, weightedHighRMSE: 0,
                weightedOverdeliveryRisk: 0, weightedUnderdeliveryRisk: 0,
                primaryScore: 0
            )
        }

        // Normalize weights
        let weights = rawWeights.map { $0 / totalWeight }

        // Compute weighted averages
        var wRMSE: Double = 0
        var wBGRI: Double = 0
        var wLowRMSE: Double = 0
        var wHighRMSE: Double = 0
        var wODR: Double = 0
        var wUDR: Double = 0

        for (m, w) in zip(metrics, weights) {
            wRMSE     += w * m.rmse
            wBGRI     += w * m.bgri
            wLowRMSE  += w * m.lowWeightedRMSE
            wHighRMSE += w * m.highWeightedRMSE
            wODR      += w * m.odr
            wUDR      += w * m.udr
        }

        // Primary score = DOS + DUS: penalises only clinically dangerous
        // mispredictions outside the target BG range.
        let primary = wODR + wUDR

        return AggregateScore(
            horizonMetrics: metrics,
            weightedRMSE: wRMSE,
            weightedBGRI: wBGRI,
            weightedLowRMSE: wLowRMSE,
            weightedHighRMSE: wHighRMSE,
            weightedOverdeliveryRisk: wODR,
            weightedUnderdeliveryRisk: wUDR,
            primaryScore: primary
        )
    }
}
