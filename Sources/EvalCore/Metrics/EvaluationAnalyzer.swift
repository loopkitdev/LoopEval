// EvaluationAnalyzer.swift — convenience struct tying Phase 4+5 together

import Foundation

/// Ties together Kalman smoothing, prediction comparison, error metric computation,
/// and aggregate scoring into a single high-level API.
public struct EvaluationAnalyzer {

    /// Optional Kalman smoother for actual CGM.  `nil` means no smoothing.
    public let smoother: KalmanSmoother?

    public init(smoother: KalmanSmoother? = KalmanSmoother()) {
        self.smoother = smoother
    }

    /// Analyse an `EvaluationResult` and return a time-weighted `AggregateScore`.
    ///
    /// - Parameters:
    ///   - result: The output of `EvaluationEngine.evaluate(...)`.
    ///   - horizons: Horizons to evaluate; defaults to `result.config.horizons`.
    /// - Returns: Aggregate score with per-horizon metrics attached.
    public func analyze(
        result: EvaluationResult,
        horizons: [TimeInterval]? = nil
    ) -> AggregateScore {
        analyzeWithSmoothed(result: result, horizons: horizons).score
    }

    /// Analyse and also return the smoothed CGM series used for comparison.
    ///
    /// - Returns: `(score, smoothedActual)` — smoothedActual is the (possibly
    ///   Kalman-filtered) CGM array that predictions were compared against.
    public func analyzeWithSmoothed(
        result: EvaluationResult,
        horizons: [TimeInterval]? = nil
    ) -> (score: AggregateScore, smoothedActual: [EvalGlucoseSample]) {
        let effectiveHorizons = horizons ?? result.config.horizons

        let actualForComparison: [EvalGlucoseSample]
        if let smoother {
            actualForComparison = smoother.smooth(samples: result.actual)
        } else {
            actualForComparison = result.actual
        }

        let horizonResults = PredictionComparator.compare(
            predictions: result.predictions,
            actual: actualForComparison,
            horizons: effectiveHorizons
        )

        let metrics = ErrorMetrics.compute(
            results: horizonResults,
            targetLow: result.config.targetLow,
            targetHigh: result.config.targetHigh
        )
        return (AggregateScore.compute(metrics: metrics), actualForComparison)
    }
}
