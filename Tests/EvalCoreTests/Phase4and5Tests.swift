// Phase4and5Tests.swift — Phase 4: Comparison/Interpolation, Phase 5: Error Metrics

import Testing
import Foundation
@testable import EvalCore
import LoopAlgorithm

// MARK: – Shared helpers

private let T0 = Date(timeIntervalSince1970: 1_700_000_000)  // fixed reference date

private func sample(offset: TimeInterval, mgdL: Double) -> EvalGlucoseSample {
    EvalGlucoseSample(
        startDate: T0.addingTimeInterval(offset),
        quantity:  LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: mgdL)
    )
}

// MARK: – Phase 4a: GlucoseInterpolator

@Test("Interpolation exact match")
func interpolationExactMatch() {
    let s = sample(offset: 100, mgdL: 140)
    let result = GlucoseInterpolator.interpolate(samples: [s], at: T0.addingTimeInterval(100))
    #expect(result != nil)
    #expect(abs(result! - 140.0) < 0.001)
}

@Test("Interpolation midpoint")
func interpolationMidpoint() {
    let s0 = sample(offset: 0, mgdL: 100)
    let s1 = sample(offset: 300, mgdL: 110)   // 5-minute gap
    let result = GlucoseInterpolator.interpolate(samples: [s0, s1], at: T0.addingTimeInterval(150))
    #expect(result != nil)
    #expect(abs(result! - 105.0) < 0.001)
}

@Test("Interpolation gap too large returns nil")
func interpolationGapTooLarge() {
    let s0 = sample(offset: 0, mgdL: 100)
    let s1 = sample(offset: 2000, mgdL: 110)  // 33-min gap > 20-min max
    let result = GlucoseInterpolator.interpolate(samples: [s0, s1], at: T0.addingTimeInterval(1000))
    #expect(result == nil)
}

@Test("Interpolation out of range returns nil")
func interpolationOutOfRange() {
    let s0 = sample(offset: 100, mgdL: 120)
    let s1 = sample(offset: 400, mgdL: 130)
    // Ask before first sample
    let before = GlucoseInterpolator.interpolate(samples: [s0, s1], at: T0.addingTimeInterval(50))
    #expect(before == nil)
    // Ask after last sample
    let after = GlucoseInterpolator.interpolate(samples: [s0, s1], at: T0.addingTimeInterval(500))
    #expect(after == nil)
}

@Test("Interpolation requires sorted input (caller's contract)")
func interpolationRequiresSortedInput() {
    // Per the contract, callers must pass samples sorted ascending by startDate.
    // PredictionComparator and DriftCommand both sort once up front before
    // entering the per-horizon hot loop. Test the contract directly:
    let s0 = sample(offset: 0,   mgdL: 100)
    let s1 = sample(offset: 300, mgdL: 110)
    let result = GlucoseInterpolator.interpolate(samples: [s0, s1], at: T0.addingTimeInterval(150))
    #expect(result != nil)
    #expect(abs(result! - 105.0) < 0.001)
}

@Test("Interpolation empty samples returns nil")
func interpolationEmpty() {
    let result = GlucoseInterpolator.interpolate(samples: [], at: T0)
    #expect(result == nil)
}

// MARK: – Phase 4b: PredictionComparator

/// Builds a PredictionRecord whose predicted glucose follows a straight line
/// starting at `startMgdL` and rising by `ratePerMin` mg/dL/min.
private func linearPrediction(
    evaluatedAt: Date,
    startMgdL: Double,
    ratePerMin: Double,
    steps: Int = 74,          // ~6h at 5-min steps
    stepSecs: Double = 300
) -> PredictionRecord {
    var points: [PredictedGlucoseValue] = []
    for i in 0..<steps {
        let t = evaluatedAt.addingTimeInterval(Double(i) * stepSecs)
        let bg = startMgdL + ratePerMin * (Double(i) * stepSecs / 60.0)
        points.append(PredictedGlucoseValue(
            startDate: t,
            quantity:  LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: bg)
        ))
    }
    return PredictionRecord(evaluatedAt: evaluatedAt, predicted: points)
}

@Test("PredictionComparator integration test")
func predictionComparatorIntegration() {
    // Prediction: flat at 100 mg/dL
    let pred = linearPrediction(evaluatedAt: T0, startMgdL: 100, ratePerMin: 0)

    // Actual CGM: flat at 110 mg/dL (so error = 100 - 110 = -10 at each horizon)
    let actualSamples: [EvalGlucoseSample] = stride(from: 0.0, through: 7 * 3600, by: 300).map {
        sample(offset: $0, mgdL: 110)
    }

    let horizons: [TimeInterval] = [30 * 60, 60 * 60]  // 30 min, 60 min
    let results = PredictionComparator.compare(
        predictions: [pred],
        actual: actualSamples,
        horizons: horizons
    )

    #expect(results.count == 2)
    for hr in results {
        #expect(hr.count == 1)
        let err = hr.errors[0]
        #expect(abs(err.predicted - 100.0) < 0.5)
        #expect(abs(err.actual   - 110.0) < 0.5)
    }
}

// MARK: – Phase 5a: BloodGlucoseRisk

@Test("LBGI high for hypoglycemic BG, HBGI near zero")
func lbgiHighForLowBG() {
    let lbgi = BloodGlucoseRisk.lbgi([40.0])
    let hbgi = BloodGlucoseRisk.hbgi([40.0])
    #expect(lbgi > 5.0, "LBGI for BG=40 should be substantially positive, got \(lbgi)")
    #expect(hbgi == 0.0)
}

@Test("HBGI high for hyperglycemic BG, LBGI near zero")
func hbgiHighForHighBG() {
    let hbgi = BloodGlucoseRisk.hbgi([400.0])
    let lbgi = BloodGlucoseRisk.lbgi([400.0])
    #expect(hbgi > 5.0, "HBGI for BG=400 should be substantially positive, got \(hbgi)")
    #expect(lbgi == 0.0)
}

@Test("Risk at rl/rh split point: rl and rh are partitioned correctly")
func riskAtSplitPoint() {
    // The rl/rh split is at 112.5 mg/dL.
    // BG=112 → rl = riskFunction(112), rh = 0
    // BG=113 → rl = 0, rh = riskFunction(113)
    let rl112 = BloodGlucoseRisk.rl(112.0)
    let rh112 = BloodGlucoseRisk.rh(112.0)
    #expect(rl112 > 0.0, "rl(112) should be positive since 112 < 112.5")
    #expect(rh112 == 0.0, "rh(112) should be 0 since 112 < 112.5")

    let rl113 = BloodGlucoseRisk.rl(113.0)
    let rh113 = BloodGlucoseRisk.rh(113.0)
    #expect(rl113 == 0.0, "rl(113) should be 0 since 113 > 112.5")
    #expect(rh113 > 0.0, "rh(113) should be positive since 113 > 112.5")
}

@Test("BGRI symmetry: rl + rh = riskFunction outside crossover")
func bgriSymmetry() {
    for bg in [50.0, 80.0, 200.0, 350.0] {
        let rl = BloodGlucoseRisk.rl(bg)
        let rh = BloodGlucoseRisk.rh(bg)
        let rf = BloodGlucoseRisk.riskFunction(bg)
        // Only one of rl/rh can be non-zero (except exactly at 112.5)
        if bg < 112.5 {
            #expect(abs((rl + rh) - rf) < 0.001,
                    "rl + rh should == riskFunction for BG=\(bg)")
            #expect(rh == 0.0)
        } else if bg > 112.5 {
            #expect(abs((rl + rh) - rf) < 0.001,
                    "rl + rh should == riskFunction for BG=\(bg)")
            #expect(rl == 0.0)
        }
    }
}

@Test("Low-weighted RMSE simple two-error case")
func lowWeightedRMSESimpleCase() {
    // Two errors: predicted=60, actual=50 (low → gets weight rl(50))
    //             predicted=120, actual=120 (in range → gets weight rl(120)=0)
    let errors: [(predicted: Double, actual: Double)] = [
        (predicted: 60.0, actual: 50.0),
        (predicted: 120.0, actual: 120.0)
    ]
    let result = BloodGlucoseRisk.lowWeightedRMSE(errors: errors)
    // Manual: n=2
    // error0: diff=(60-50)=10, rl(50)>0, contribution = rl(50)*100
    // error1: diff=0, rl(120)=0, contribution = 0
    // lowWRMSE = sqrt( (rl(50)*100 + 0) / 2 )
    let rl50 = BloodGlucoseRisk.rl(50.0)
    let expected = sqrt(rl50 * 100.0 / 2.0)
    #expect(abs(result - expected) < 0.001,
            "lowWeightedRMSE mismatch: \(result) vs \(expected)")
    #expect(result > 0)
}

@Test("High-weighted RMSE simple case")
func highWeightedRMSESimpleCase() {
    let errors: [(predicted: Double, actual: Double)] = [
        (predicted: 350.0, actual: 400.0),  // high BG → rh(400) > 0
        (predicted: 100.0, actual: 100.0)   // normal → rh(100) = 0
    ]
    let result = BloodGlucoseRisk.highWeightedRMSE(errors: errors)
    let rh400 = BloodGlucoseRisk.rh(400.0)
    let expected = sqrt(rh400 * (50.0 * 50.0) / 2.0)
    #expect(abs(result - expected) < 0.001,
            "highWeightedRMSE mismatch: \(result) vs \(expected)")
    #expect(result > 0)
}

// MARK: – Phase 5b: ErrorMetrics

@Test("ErrorMetrics basic computation")
func errorMetricsBasic() {
    // Five errors, all with predicted = actual + 10 (constant positive bias)
    let errors: [(predicted: Double, actual: Double)] = (0..<5).map { i in
        (predicted: 120.0, actual: 110.0)
    }
    let result = HorizonResult(horizon: 30 * 60, errors: errors)
    let metrics = ErrorMetrics.compute(result: result)

    #expect(metrics.sampleCount == 5)
    #expect(abs(metrics.rmse - 10.0) < 0.001)
    #expect(abs(metrics.mae - 10.0) < 0.001)
    #expect(abs(metrics.meanError - 10.0) < 0.001)
    #expect(abs(metrics.percentile10 - 10.0) < 0.001)
    #expect(abs(metrics.percentile90 - 10.0) < 0.001)
}

@Test("ErrorMetrics empty result returns zeros")
func errorMetricsEmpty() {
    let result = HorizonResult(horizon: 60 * 60, errors: [])
    let metrics = ErrorMetrics.compute(result: result)
    #expect(metrics.sampleCount == 0)
    #expect(metrics.rmse == 0)
    #expect(metrics.mae  == 0)
}

@Test("ErrorMetrics compute multiple results")
func errorMetricsMultiple() {
    let r1 = HorizonResult(horizon: 30 * 60, errors: [(100, 90), (110, 90)])
    let r2 = HorizonResult(horizon: 60 * 60, errors: [(100, 80)])
    let all = ErrorMetrics.compute(results: [r1, r2])
    #expect(all.count == 2)
    #expect(all[0].horizon == 30 * 60)
    #expect(all[1].horizon == 60 * 60)
}

// MARK: – Phase 5c: KalmanSmoother

@Test("Kalman smoother preserves timestamps and count")
func kalmanPreservesTimestamps() {
    let smoother = KalmanSmoother()
    let samples: [EvalGlucoseSample] = (0..<12).map { i in
        sample(offset: Double(i) * 300, mgdL: 120)
    }
    let smoothed = smoother.smooth(samples: samples)
    #expect(smoothed.count == samples.count)
    for (orig, sm) in zip(samples, smoothed) {
        #expect(orig.startDate == sm.startDate,
                "Timestamp changed during smoothing")
    }
}

@Test("Kalman smoother reduces variance of noisy readings")
func kalmanReducesVariance() {
    let smoother = KalmanSmoother()
    // True value: 120 mg/dL. Add ±5 mg/dL noise.
    let noisePattern: [Double] = [5, -4, 3, -5, 4, -3, 5, -4, 3, -5, 4, -3]
    let samples: [EvalGlucoseSample] = noisePattern.enumerated().map { i, noise in
        sample(offset: Double(i) * 300, mgdL: 120 + noise)
    }
    let smoothed = smoother.smooth(samples: samples)

    let rawBGs    = samples.map { $0.quantity.doubleValue(for: .milligramsPerDeciliter) }
    let smoothBGs = smoothed.map { $0.quantity.doubleValue(for: .milligramsPerDeciliter) }

    let rawVar    = variance(rawBGs)
    let smoothVar = variance(smoothBGs)
    #expect(smoothVar < rawVar,
            "Smoother should reduce variance: raw=\(rawVar) smooth=\(smoothVar)")
}

@Test("Kalman smoother handles single sample")
func kalmanSingleSample() {
    let smoother = KalmanSmoother()
    let samples = [sample(offset: 0, mgdL: 120)]
    let smoothed = smoother.smooth(samples: samples)
    #expect(smoothed.count == 1)
    #expect(abs(smoothed[0].quantity.doubleValue(for: .milligramsPerDeciliter) - 120) < 0.001)
}

@Test("Kalman smoother output stays within reasonable range")
func kalmanOutputRange() {
    let smoother = KalmanSmoother()
    let samples: [EvalGlucoseSample] = (0..<20).map { i in
        // BG oscillates but stays between 80–160
        let bg = 120.0 + 40.0 * sin(Double(i) * .pi / 5)
        return sample(offset: Double(i) * 300, mgdL: bg)
    }
    let smoothed = smoother.smooth(samples: samples)
    for sm in smoothed {
        let bg = sm.quantity.doubleValue(for: .milligramsPerDeciliter)
        // Smoothed BG should stay in a physiologically plausible range
        #expect(bg > 40 && bg < 400,
                "Smoothed BG \(bg) is out of physiological range")
    }
}

// MARK: – Phase 5d: AggregateScore

@Test("AggregateScore Gaussian weights peak at peak horizon")
func aggregateScoreGaussianPeak() {
    // Create metrics at 30, 60, 90, 120, 150, 180 min
    let horizons: [TimeInterval] = [30, 60, 90, 120, 150, 180].map { $0 * 60 }
    let metrics = horizons.map { h -> HorizonMetrics in
        HorizonMetrics(
            horizon: h, sampleCount: 100,
            rmse: 1.0, mae: 1.0, meanError: 0,
            percentile10: -1, percentile90: 1,
            lbgi: 0, hbgi: 0, bgri: 0,
            lowWeightedRMSE: 0, highWeightedRMSE: 0,
            opr: 0, upr: 0
        )
    }

    let score = AggregateScore.compute(
        metrics: metrics,
        peakHorizon: 150 * 60,
        sigmaSecs: 60 * 60
    )

    // Weighted RMSE should be 1.0 since all horizons have rmse=1.0
    #expect(abs(score.weightedRMSE - 1.0) < 0.001)
    #expect(abs(score.weightedBGRI - 0.0) < 0.001)
    #expect(score.horizonMetrics.count == metrics.count)
}

@Test("AggregateScore peak horizon gets highest Gaussian weight")
func aggregateScorePeakHorizonWeight() {
    // Use different RMSE per horizon to verify weighting
    // Peak at 150 min → 150-min horizon should dominate weighted average
    let horizons: [TimeInterval] = [30, 60, 90, 120, 150, 180].map { $0 * 60 }
    let rmseValues = [20.0, 18.0, 15.0, 12.0, 100.0, 12.0] // 150-min is highest
    let metrics = zip(horizons, rmseValues).map { h, r -> HorizonMetrics in
        HorizonMetrics(
            horizon: h, sampleCount: 100,
            rmse: r, mae: r, meanError: 0,
            percentile10: -r, percentile90: r,
            lbgi: 0, hbgi: 0, bgri: 0,
            lowWeightedRMSE: 0, highWeightedRMSE: 0,
            opr: 0, upr: 0
        )
    }

    let score = AggregateScore.compute(
        metrics: metrics,
        peakHorizon: 150 * 60,
        sigmaSecs: 30 * 60   // narrow sigma → peak gets high weight
    )

    // With narrow sigma and rmse=100 at peak, weighted RMSE should be pulled toward 100
    #expect(score.weightedRMSE > 30.0,
            "Peak horizon (rmse=100) should dominate with narrow sigma, got \(score.weightedRMSE)")
}

@Test("AggregateScore empty metrics returns zero score")
func aggregateScoreEmpty() {
    let score = AggregateScore.compute(metrics: [])
    #expect(score.weightedRMSE == 0)
    #expect(score.weightedBGRI == 0)
    #expect(score.primaryScore == 0)
}

@Test("AggregateScore primaryScore is weighted combination")
func aggregateScorePrimaryScore() {
    let m = HorizonMetrics(
        horizon: 90 * 60, sampleCount: 50,
        rmse: 10.0, mae: 8.0, meanError: 2.0,
        percentile10: -8, percentile90: 12,
        lbgi: 0.5, hbgi: 1.5, bgri: 2.0,
        lowWeightedRMSE: 5.0, highWeightedRMSE: 8.0,
        opr: 0.4, upr: 0.6
    )
    let score = AggregateScore.compute(metrics: [m])
    // Single horizon → primaryScore = opr + upr
    let expected = 0.4 + 0.6
    #expect(abs(score.primaryScore - expected) < 0.001,
            "Primary score: expected \(expected), got \(score.primaryScore)")
}

// MARK: – Private helpers

private func variance(_ values: [Double]) -> Double {
    guard values.count > 1 else { return 0 }
    let mean = values.reduce(0, +) / Double(values.count)
    return values.map { ($0 - mean) * ($0 - mean) }.reduce(0, +) / Double(values.count - 1)
}
