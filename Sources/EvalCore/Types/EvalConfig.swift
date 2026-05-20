// EvalConfig.swift — configuration for an evaluation run

import Foundation
import LoopAlgorithm

/// Configuration parameters for a Loop prediction evaluation sweep.
public struct EvalConfig: Codable, Sendable {
    /// How often to advance the prediction start (seconds).  Default: 5 min.
    public var evalStep: TimeInterval

    /// Whether to include future-scheduled basal insulin in the dose window.
    /// `SimulateCommand` overrides to `false` by default (clean decision-time
    /// replay); pass `--oracle-future-inputs` for oracle/debug runs.
    public var includeFutureInsulin: Bool

    /// Whether to include future-entered carbs in the per-step input window.
    /// When false, carbs with entryDate > t are excluded (real-time replay).
    /// When true, all carbs whose meal time falls in the window are visible (oracle mode).
    public var includeFutureCarbs: Bool

    /// How far back to look for insulin doses (hours).  Default: 16.
    public var insulinLookbackHours: Double

    /// How far back to look for CGM readings (hours).  Default: 10.
    public var glucoseLookbackHours: Double

    /// Use Integral Retrospective Correction instead of standard RC.
    public var useIntegralRC: Bool

    /// Asymmetric IRC gains (only used when `useIntegralRC` is true). `ircDropGainScale`
    /// scales the correction when the discrepancy run is negative (BG dropping faster
    /// than predicted = sensitivity); `ircRiseGainScale` when positive (resistance).
    /// Default 1.0/1.0 == standard symmetric IRC.
    public var ircDropGainScale: Double
    public var ircRiseGainScale: Double

    /// Smooth actual CGM with a Kalman filter before comparison (not algorithm input).
    public var kalmanSmoothing: Bool

    /// Forecast horizons to evaluate, in seconds.
    /// Default: every 30 min from 30 min to 360 min.
    public var horizons: [TimeInterval]

    /// If false, only net negative momentum and RC effects will be used.
    /// Default: true (same as LoopAlgorithm default).
    public var includingPositiveVelocityAndRC: Bool

    /// Use mid-absorption ISF for insulin effects computation.
    /// Default: true — propagates per-future-time ISF schedule changes into
    /// the BG prediction, which is needed for `--candidate-isf-csv` oracles
    /// to actually affect Loop's forecast (not just the dose-calc sizing).
    public var useMidAbsorptionISF: Bool

    /// Carb absorption model.  Default: .piecewiseLinear.
    public var carbAbsorptionModel: CarbAbsorptionModel

    /// Multiplicative scalar applied to the ISF (sensitivity) timeline before
    /// passing to LoopAlgorithm.  1.0 = use values as-is from Nightscout.
    /// Values > 1.0 → larger ISF → MORE conservative dosing.
    /// Values < 1.0 → smaller ISF → MORE aggressive dosing.
    public var sensitivityMultiplier: Double

    /// Optional 24-element vector of per-local-hour ISF multipliers, applied
    /// on top of `sensitivityMultiplier`. Index = local hour [0, 23]. nil =
    /// no per-hour variation.
    public var sensitivityHourlyMultipliers: [Double]?

    /// Local timezone for interpreting hour-of-day for
    /// `sensitivityHourlyMultipliers`. Default: `TimeZone.current`.
    public var localTimezone: TimeZone

    /// Multiplier applied to carb ratios from Nightscout (default: 1.0).
    public var carbRatioMultiplier: Double

    /// Multiplier applied to basal rates from Nightscout (default: 1.0).
    public var basalRateMultiplier: Double

    /// Lower bound of the in-target BG range (mg/dL). OPR fires when actual BG < targetLow.
    public var targetLow: Double

    /// Upper bound of the in-target BG range (mg/dL). UPR fires when actual BG > targetHigh.
    public var targetHigh: Double

    /// Clinical hypoglycemia threshold (mg/dL). Default: 70.
    public var dangerLow: Double

    /// Clinical hyperglycemia threshold (mg/dL). Default: 180.
    public var dangerHigh: Double

    /// Use asymmetric EMA momentum instead of standard linear regression.
    /// Slow to build positive momentum (alphaSlow), fast to shed it (alphaFast).
    public var useAsymmetricMomentum: Bool

    /// Slow-rise alpha for asymmetric momentum EMA (default 0.15 ≈ 33 min time constant).
    public var momentumAlphaSlow: Double

    /// Fast-drop alpha for asymmetric momentum EMA (default 0.85 ≈ 1 reading response).
    public var momentumAlphaFast: Double

    /// Cap on positive CGM momentum velocity (mg/dL/min). nil = use LoopAlgorithm
    /// default (4.0 mg/dL/min).
    public var positiveVelocityCap: Double?

    /// How long to wait after `interval.start` before the first evaluated
    /// prediction (seconds). Default: `insulinLookbackHours` hours.
    public var evalWarmupHours: Double

    /// Glucose-based application factor (GBAF): when true, the auto-bolus
    /// applicationFactor scales with current BG via a piecewise-linear curve
    /// (factorLow at/below gbafLowAnchor, factorHigh at/above gbafHighAnchor).
    /// More aggressive dosing only when BG is heading high. Default false.
    public var glucoseBasedApplicationFactor: Bool
    public var gbafLowAnchor: Double
    public var gbafHighAnchor: Double
    public var gbafFactorLow: Double
    public var gbafFactorHigh: Double

    // MARK: – Defaults

    /// A config with all defaults. Convenience used widely by tests and callers.
    public static var `default`: EvalConfig { EvalConfig() }

    public init(
        glucoseBasedApplicationFactor: Bool = false,
        gbafLowAnchor: Double = 140.0,
        gbafHighAnchor: Double = 220.0,
        gbafFactorLow: Double = 0.4,
        gbafFactorHigh: Double = 0.7,
        evalStep: TimeInterval = 5 * 60,
        includeFutureInsulin: Bool = true,
        includeFutureCarbs: Bool = false,
        insulinLookbackHours: Double = 16,
        glucoseLookbackHours: Double = 10,
        useIntegralRC: Bool = false,
        ircDropGainScale: Double = 1.0,
        ircRiseGainScale: Double = 1.0,
        kalmanSmoothing: Bool = true,
        horizons: [TimeInterval] = stride(from: 30.0, through: 360.0, by: 30.0)
            .map { $0 * 60 },
        includingPositiveVelocityAndRC: Bool = true,
        useMidAbsorptionISF: Bool = true,
        carbAbsorptionModel: CarbAbsorptionModel = .piecewiseLinear,
        sensitivityMultiplier: Double = 1.0,
        sensitivityHourlyMultipliers: [Double]? = nil,
        localTimezone: TimeZone = .current,
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
        evalWarmupHours: Double? = nil   // nil → use insulinLookbackHours
    ) {
        self.glucoseBasedApplicationFactor  = glucoseBasedApplicationFactor
        self.gbafLowAnchor                  = gbafLowAnchor
        self.gbafHighAnchor                 = gbafHighAnchor
        self.gbafFactorLow                  = gbafFactorLow
        self.gbafFactorHigh                 = gbafFactorHigh
        self.evalStep                       = evalStep
        self.includeFutureInsulin           = includeFutureInsulin
        self.includeFutureCarbs             = includeFutureCarbs
        self.insulinLookbackHours           = insulinLookbackHours
        self.glucoseLookbackHours           = glucoseLookbackHours
        self.useIntegralRC                  = useIntegralRC
        self.ircDropGainScale               = ircDropGainScale
        self.ircRiseGainScale               = ircRiseGainScale
        self.kalmanSmoothing                = kalmanSmoothing
        self.horizons                       = horizons
        self.includingPositiveVelocityAndRC = includingPositiveVelocityAndRC
        self.useMidAbsorptionISF            = useMidAbsorptionISF
        self.carbAbsorptionModel            = carbAbsorptionModel
        self.sensitivityMultiplier          = sensitivityMultiplier
        if let h = sensitivityHourlyMultipliers, h.count != 24 {
            preconditionFailure("sensitivityHourlyMultipliers must have exactly 24 entries")
        }
        self.sensitivityHourlyMultipliers   = sensitivityHourlyMultipliers
        self.localTimezone                  = localTimezone
        self.carbRatioMultiplier            = carbRatioMultiplier
        self.basalRateMultiplier            = basalRateMultiplier
        self.targetLow                      = targetLow
        self.targetHigh                     = targetHigh
        self.dangerLow                      = dangerLow
        self.dangerHigh                     = dangerHigh
        self.positiveVelocityCap            = positiveVelocityCap
        self.useAsymmetricMomentum          = useAsymmetricMomentum
        self.momentumAlphaSlow              = momentumAlphaSlow
        self.momentumAlphaFast              = momentumAlphaFast
        self.evalWarmupHours                = evalWarmupHours ?? insulinLookbackHours
    }

    private enum CodingKeys: String, CodingKey {
        case evalStep, includeFutureInsulin, includeFutureCarbs, insulinLookbackHours, glucoseLookbackHours
        case useIntegralRC, ircDropGainScale, ircRiseGainScale, kalmanSmoothing, horizons, includingPositiveVelocityAndRC
        case useMidAbsorptionISF, carbAbsorptionModel
        case sensitivityMultiplier, carbRatioMultiplier, basalRateMultiplier
        case targetLow, targetHigh, dangerLow, dangerHigh
        case positiveVelocityCap, useAsymmetricMomentum, momentumAlphaSlow, momentumAlphaFast
        case sensitivityHourlyMultipliers, localTimezoneIdentifier
        case evalWarmupHours
        case glucoseBasedApplicationFactor, gbafLowAnchor, gbafHighAnchor, gbafFactorLow, gbafFactorHigh
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.evalStep             = try c.decode(TimeInterval.self, forKey: .evalStep)
        self.includeFutureInsulin = try c.decode(Bool.self,         forKey: .includeFutureInsulin)
        self.includeFutureCarbs   = try c.decodeIfPresent(Bool.self, forKey: .includeFutureCarbs) ?? false
        self.insulinLookbackHours = try c.decode(Double.self,       forKey: .insulinLookbackHours)
        self.glucoseLookbackHours = try c.decode(Double.self,       forKey: .glucoseLookbackHours)
        self.useIntegralRC        = try c.decode(Bool.self,         forKey: .useIntegralRC)
        self.ircDropGainScale     = try c.decodeIfPresent(Double.self, forKey: .ircDropGainScale) ?? 1.0
        self.ircRiseGainScale     = try c.decodeIfPresent(Double.self, forKey: .ircRiseGainScale) ?? 1.0
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
        self.sensitivityHourlyMultipliers = try c.decodeIfPresent([Double].self, forKey: .sensitivityHourlyMultipliers)
        if let h = self.sensitivityHourlyMultipliers, h.count != 24 {
            throw DecodingError.dataCorruptedError(forKey: .sensitivityHourlyMultipliers, in: c,
                debugDescription: "sensitivityHourlyMultipliers must have exactly 24 entries")
        }
        if let tzId = try c.decodeIfPresent(String.self, forKey: .localTimezoneIdentifier),
           let tz = TimeZone(identifier: tzId) {
            self.localTimezone = tz
        } else {
            self.localTimezone = .current
        }
        self.evalWarmupHours      = try c.decode(Double.self,       forKey: .evalWarmupHours)
        self.glucoseBasedApplicationFactor = try c.decodeIfPresent(Bool.self, forKey: .glucoseBasedApplicationFactor) ?? false
        self.gbafLowAnchor        = try c.decodeIfPresent(Double.self, forKey: .gbafLowAnchor)  ?? 140.0
        self.gbafHighAnchor       = try c.decodeIfPresent(Double.self, forKey: .gbafHighAnchor) ?? 220.0
        self.gbafFactorLow        = try c.decodeIfPresent(Double.self, forKey: .gbafFactorLow)  ?? 0.4
        self.gbafFactorHigh       = try c.decodeIfPresent(Double.self, forKey: .gbafFactorHigh) ?? 0.7
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(evalStep, forKey: .evalStep)
        try c.encode(includeFutureInsulin, forKey: .includeFutureInsulin)
        try c.encode(includeFutureCarbs, forKey: .includeFutureCarbs)
        try c.encode(insulinLookbackHours, forKey: .insulinLookbackHours)
        try c.encode(glucoseLookbackHours, forKey: .glucoseLookbackHours)
        try c.encode(useIntegralRC, forKey: .useIntegralRC)
        try c.encode(ircDropGainScale, forKey: .ircDropGainScale)
        try c.encode(ircRiseGainScale, forKey: .ircRiseGainScale)
        try c.encode(kalmanSmoothing, forKey: .kalmanSmoothing)
        try c.encode(horizons, forKey: .horizons)
        try c.encode(includingPositiveVelocityAndRC, forKey: .includingPositiveVelocityAndRC)
        try c.encode(useMidAbsorptionISF, forKey: .useMidAbsorptionISF)
        try c.encode(carbAbsorptionModel, forKey: .carbAbsorptionModel)
        try c.encode(sensitivityMultiplier, forKey: .sensitivityMultiplier)
        try c.encode(carbRatioMultiplier, forKey: .carbRatioMultiplier)
        try c.encode(basalRateMultiplier, forKey: .basalRateMultiplier)
        try c.encode(targetLow, forKey: .targetLow)
        try c.encode(targetHigh, forKey: .targetHigh)
        try c.encode(dangerLow, forKey: .dangerLow)
        try c.encode(dangerHigh, forKey: .dangerHigh)
        try c.encodeIfPresent(positiveVelocityCap, forKey: .positiveVelocityCap)
        try c.encode(useAsymmetricMomentum, forKey: .useAsymmetricMomentum)
        try c.encode(momentumAlphaSlow, forKey: .momentumAlphaSlow)
        try c.encode(momentumAlphaFast, forKey: .momentumAlphaFast)
        try c.encodeIfPresent(sensitivityHourlyMultipliers, forKey: .sensitivityHourlyMultipliers)
        try c.encode(localTimezone.identifier, forKey: .localTimezoneIdentifier)
        try c.encode(evalWarmupHours, forKey: .evalWarmupHours)
        try c.encode(glucoseBasedApplicationFactor, forKey: .glucoseBasedApplicationFactor)
        try c.encode(gbafLowAnchor, forKey: .gbafLowAnchor)
        try c.encode(gbafHighAnchor, forKey: .gbafHighAnchor)
        try c.encode(gbafFactorLow, forKey: .gbafFactorLow)
        try c.encode(gbafFactorHigh, forKey: .gbafFactorHigh)
    }
}
