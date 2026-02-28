// EvalConfig.swift — configuration for an evaluation run

import Foundation
import LoopAlgorithm

/// Configuration parameters for a Loop prediction evaluation sweep.
public struct EvalConfig: Codable, Sendable {
    /// How often to advance the prediction start (seconds).  Default: 5 min.
    public var evalStep: TimeInterval

    /// Whether to include future-scheduled basal insulin in the dose window.
    public var includeFutureInsulin: Bool

    /// How far back to look for insulin doses (hours).  Default: 16.
    public var insulinLookbackHours: Double

    /// How far back to look for CGM readings (hours).  Default: 10.
    public var glucoseLookbackHours: Double

    /// Use Integral Retrospective Correction instead of standard RC.
    public var useIntegralRC: Bool

    /// Smooth actual CGM with a Kalman filter before comparison (not algorithm input).
    public var kalmanSmoothing: Bool

    /// Forecast horizons to evaluate, in seconds.
    /// Default: every 30 min from 30 min to 360 min.
    public var horizons: [TimeInterval]

    /// If false, only net negative momentum and RC effects will be used.
    /// Default: true (same as LoopAlgorithm default).
    public var includingPositiveVelocityAndRC: Bool

    /// Use mid-absorption ISF for insulin effects computation.
    /// Default: false (same as LoopAlgorithm default).
    public var useMidAbsorptionISF: Bool

    /// Carb absorption model.  Default: .piecewiseLinear.
    public var carbAbsorptionModel: CarbAbsorptionModel

    /// Multiplicative scalar applied to the ISF (sensitivity) timeline before
    /// passing to LoopAlgorithm.  1.0 = use values as-is from Nightscout.
    /// Values > 1.0 make the algorithm more aggressive (lower ISF → more
    /// correction), values < 1.0 make it more conservative.
    /// Default: 1.0.
    public var sensitivityMultiplier: Double

    /// How long to wait after `interval.start` before the first evaluated
    /// prediction (seconds).  Default: `insulinLookbackHours` hours.
    ///
    /// Data is always fetched starting from `interval.start`.  Predictions
    /// are only generated and scored after this warmup has elapsed, ensuring
    /// every reported forecast has a full insulin/glucose history window.
    public var evalWarmupHours: Double

    // MARK: – Defaults

    public static var `default`: EvalConfig { EvalConfig() }

    public init(
        evalStep: TimeInterval = 5 * 60,
        includeFutureInsulin: Bool = true,
        insulinLookbackHours: Double = 16,
        glucoseLookbackHours: Double = 10,
        useIntegralRC: Bool = false,
        kalmanSmoothing: Bool = true,
        horizons: [TimeInterval] = stride(from: 30.0, through: 360.0, by: 30.0)
            .map { $0 * 60 },
        includingPositiveVelocityAndRC: Bool = true,
        useMidAbsorptionISF: Bool = false,
        carbAbsorptionModel: CarbAbsorptionModel = .piecewiseLinear,
        sensitivityMultiplier: Double = 1.0,
        evalWarmupHours: Double? = nil   // nil → use insulinLookbackHours
    ) {
        self.evalStep                       = evalStep
        self.includeFutureInsulin           = includeFutureInsulin
        self.insulinLookbackHours           = insulinLookbackHours
        self.glucoseLookbackHours           = glucoseLookbackHours
        self.useIntegralRC                  = useIntegralRC
        self.kalmanSmoothing                = kalmanSmoothing
        self.horizons                       = horizons
        self.includingPositiveVelocityAndRC = includingPositiveVelocityAndRC
        self.useMidAbsorptionISF            = useMidAbsorptionISF
        self.carbAbsorptionModel            = carbAbsorptionModel
        self.sensitivityMultiplier          = sensitivityMultiplier
        self.evalWarmupHours                = evalWarmupHours ?? insulinLookbackHours
    }
}
