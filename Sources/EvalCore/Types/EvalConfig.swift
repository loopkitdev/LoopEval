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
    /// Default: TRUE — this isn't a behavior change, it's the correct way to
    /// handle ISF-schedule transitions during a dose's absorption window.
    /// Without it, a dose given just before an ISF change uses the old ISF
    /// for its full absorption, which is just wrong.
    public var useMidAbsorptionISF: Bool

    /// Carb absorption model.  Default: .piecewiseLinear.
    public var carbAbsorptionModel: CarbAbsorptionModel

    /// Multiplicative scalar applied to the ISF (sensitivity) timeline before
    /// passing to LoopAlgorithm.  1.0 = use values as-is from Nightscout.
    /// Values > 1.0 make the algorithm more aggressive (lower ISF → more
    /// correction), values < 1.0 make it more conservative.
    /// Default: 1.0.
    public var sensitivityMultiplier: Double

    /// Multiplier applied to carb ratios from Nightscout (default: 1.0).
    /// Values > 1 make CR larger (less insulin per carb), < 1 make it more aggressive.
    public var carbRatioMultiplier: Double

    /// Multiplier applied to basal rates from Nightscout (default: 1.0).
    /// Values > 1 raise basal (more background insulin), < 1 lower it.
    public var basalRateMultiplier: Double

    /// Lower bound of the in-target BG range (mg/dL).  Forecast-error metric
    /// **OPR** fires when actual BG < targetLow (i.e., below target).  Default: 100.
    public var targetLow: Double

    /// Upper bound of the in-target BG range (mg/dL).  Forecast-error metric
    /// **UPR** fires when actual BG > targetHigh.  Default: 115.
    public var targetHigh: Double

    /// Clinical hypoglycemia threshold (mg/dL).  Delivery-based metric **ODR**
    /// fires only when actual BG at horizon < dangerLow.  Distinct from
    /// targetLow because ODR measures clinically dangerous over-delivery, not
    /// merely out-of-target.  Default: 70 mg/dL (standard ADA hypo cutoff).
    public var dangerLow: Double

    /// Clinical hyperglycemia threshold (mg/dL).  Delivery-based metric **UDR**
    /// fires only when actual BG at horizon > dangerHigh.  Default: 180 mg/dL
    /// (standard time-in-range high cutoff, ≈ 10 mmol/L).
    public var dangerHigh: Double

    /// Use asymmetric EMA momentum instead of standard linear regression.
    /// Slow to build positive momentum (alphaSlow), fast to shed it (alphaFast).
    public var useAsymmetricMomentum: Bool

    /// Slow-rise alpha for asymmetric momentum EMA (default 0.15 ≈ 33 min time constant).
    public var momentumAlphaSlow: Double

    /// Fast-drop alpha for asymmetric momentum EMA (default 0.85 ≈ 1 reading response).
    public var momentumAlphaFast: Double

    /// Cap on positive CGM momentum velocity (mg/dL/min).
    /// When set, limits the velocity term passed to `linearMomentumEffect` to
    /// this value.  `nil` = use LoopAlgorithm's built-in default (4.0 mg/dL/min).
    /// Example: set to 0.5 to compare an algorithm that limits upward momentum
    /// to 0.5 mg/dL/min.
    public var positiveVelocityCap: Double?

    /// Enable glucose-based application factor (GBAF).  When true, the
    /// auto-bolus applicationFactor scales with current BG via a piecewise-linear
    /// curve: factorLow at gbafLowAnchor (and below), factorHigh at gbafHighAnchor
    /// (and above), linear interpolation between.  Designed for the Priority-3
    /// safety case "reduce highs without increasing lows" — more aggressive
    /// dosing only when BG is heading high, not when it's near or below target.
    /// Default: false (use flat applicationFactor=0.4).
    public var glucoseBasedApplicationFactor: Bool

    /// GBAF curve: BG (mg/dL) at and below which applicationFactor = factorLow.
    public var gbafLowAnchor: Double

    /// GBAF curve: BG (mg/dL) at and above which applicationFactor = factorHigh.
    public var gbafHighAnchor: Double

    /// GBAF curve: applicationFactor when current BG ≤ gbafLowAnchor.
    public var gbafFactorLow: Double

    /// GBAF curve: applicationFactor when current BG ≥ gbafHighAnchor.
    public var gbafFactorHigh: Double

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
        useMidAbsorptionISF: Bool = true,
        carbAbsorptionModel: CarbAbsorptionModel = .piecewiseLinear,
        sensitivityMultiplier: Double = 1.0,
        carbRatioMultiplier: Double = 1.0,
        basalRateMultiplier: Double = 1.0,
        targetLow: Double = 100.0,
        targetHigh: Double = 115.0,
        dangerLow: Double = 70.0,
        dangerHigh: Double = 180.0,
        positiveVelocityCap: Double? = nil,
        useAsymmetricMomentum: Bool = false,
        momentumAlphaSlow: Double = 0.15,
        momentumAlphaFast: Double = 0.85,
        glucoseBasedApplicationFactor: Bool = false,
        gbafLowAnchor: Double = 140.0,
        gbafHighAnchor: Double = 220.0,
        gbafFactorLow: Double = 0.4,
        gbafFactorHigh: Double = 0.7,
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
        self.carbRatioMultiplier            = carbRatioMultiplier
        self.basalRateMultiplier            = basalRateMultiplier
        self.targetLow                      = targetLow
        self.targetHigh                     = targetHigh
        self.dangerLow                      = dangerLow
        self.dangerHigh                     = dangerHigh
        self.positiveVelocityCap            = positiveVelocityCap
        self.useAsymmetricMomentum          = useAsymmetricMomentum
        self.glucoseBasedApplicationFactor  = glucoseBasedApplicationFactor
        self.gbafLowAnchor                  = gbafLowAnchor
        self.gbafHighAnchor                 = gbafHighAnchor
        self.gbafFactorLow                  = gbafFactorLow
        self.gbafFactorHigh                 = gbafFactorHigh
        self.momentumAlphaSlow              = momentumAlphaSlow
        self.momentumAlphaFast              = momentumAlphaFast
        self.evalWarmupHours                = evalWarmupHours ?? insulinLookbackHours
    }

    // Custom decoder so snapshots written before `dangerLow`/`dangerHigh` were
    // added still decode cleanly (fall back to the clinical defaults).
    private enum CodingKeys: String, CodingKey {
        case evalStep, includeFutureInsulin, insulinLookbackHours, glucoseLookbackHours
        case useIntegralRC, kalmanSmoothing, horizons, includingPositiveVelocityAndRC
        case useMidAbsorptionISF, carbAbsorptionModel
        case sensitivityMultiplier, carbRatioMultiplier, basalRateMultiplier
        case targetLow, targetHigh, dangerLow, dangerHigh
        case positiveVelocityCap, useAsymmetricMomentum, momentumAlphaSlow, momentumAlphaFast
        case glucoseBasedApplicationFactor, gbafLowAnchor, gbafHighAnchor, gbafFactorLow, gbafFactorHigh
        case evalWarmupHours
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.evalStep             = try c.decode(TimeInterval.self, forKey: .evalStep)
        self.includeFutureInsulin = try c.decode(Bool.self,         forKey: .includeFutureInsulin)
        self.insulinLookbackHours = try c.decode(Double.self,       forKey: .insulinLookbackHours)
        self.glucoseLookbackHours = try c.decode(Double.self,       forKey: .glucoseLookbackHours)
        self.useIntegralRC        = try c.decode(Bool.self,         forKey: .useIntegralRC)
        self.kalmanSmoothing      = try c.decode(Bool.self,         forKey: .kalmanSmoothing)
        self.horizons             = try c.decode([TimeInterval].self, forKey: .horizons)
        self.includingPositiveVelocityAndRC = try c.decode(Bool.self, forKey: .includingPositiveVelocityAndRC)
        self.useMidAbsorptionISF  = try c.decode(Bool.self,         forKey: .useMidAbsorptionISF)
        self.carbAbsorptionModel  = try c.decode(CarbAbsorptionModel.self, forKey: .carbAbsorptionModel)
        self.sensitivityMultiplier = try c.decode(Double.self,      forKey: .sensitivityMultiplier)
        self.carbRatioMultiplier  = try c.decode(Double.self,       forKey: .carbRatioMultiplier)
        self.basalRateMultiplier  = try c.decode(Double.self,       forKey: .basalRateMultiplier)
        self.targetLow            = try c.decode(Double.self,       forKey: .targetLow)
        self.targetHigh           = try c.decode(Double.self,       forKey: .targetHigh)
        self.dangerLow            = try c.decodeIfPresent(Double.self, forKey: .dangerLow)  ?? 70.0
        self.dangerHigh           = try c.decodeIfPresent(Double.self, forKey: .dangerHigh) ?? 180.0
        self.positiveVelocityCap  = try c.decodeIfPresent(Double.self, forKey: .positiveVelocityCap)
        self.useAsymmetricMomentum = try c.decode(Bool.self,        forKey: .useAsymmetricMomentum)
        self.momentumAlphaSlow    = try c.decode(Double.self,       forKey: .momentumAlphaSlow)
        self.momentumAlphaFast    = try c.decode(Double.self,       forKey: .momentumAlphaFast)
        self.glucoseBasedApplicationFactor = try c.decodeIfPresent(Bool.self, forKey: .glucoseBasedApplicationFactor) ?? false
        self.gbafLowAnchor        = try c.decodeIfPresent(Double.self, forKey: .gbafLowAnchor)   ?? 140.0
        self.gbafHighAnchor       = try c.decodeIfPresent(Double.self, forKey: .gbafHighAnchor)  ?? 220.0
        self.gbafFactorLow        = try c.decodeIfPresent(Double.self, forKey: .gbafFactorLow)   ?? 0.4
        self.gbafFactorHigh       = try c.decodeIfPresent(Double.self, forKey: .gbafFactorHigh)  ?? 0.7
        self.evalWarmupHours      = try c.decode(Double.self,       forKey: .evalWarmupHours)
    }
}
