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
    /// ISF is mg/dL per unit of insulin, so HIGHER ISF means each unit drops
    /// BG more, which means Loop recommends FEWER units for a given correction.
    /// Values > 1.0 → larger ISF → MORE conservative dosing (less insulin).
    /// Values < 1.0 → smaller ISF → MORE aggressive dosing (more insulin).
    /// Default: 1.0.
    public var sensitivityMultiplier: Double

    /// Optional 24-element vector of per-local-hour ISF multipliers, applied
    /// on top of `sensitivityMultiplier`. Index = local hour [0, 23]. Each
    /// hour-aligned slice of the absolute sensitivity timeline gets multiplied
    /// by the matching hour's value. nil = behave like `sensitivityMultiplier`
    /// alone (no per-hour variation). Default: nil.
    /// Requires `useMidAbsorptionISF = true` for hourly changes to be applied
    /// at the time the change is needed (rather than ahead-of-effect).
    public var sensitivityHourlyMultipliers: [Double]?

    /// Local timezone for interpreting hour-of-day for
    /// `sensitivityHourlyMultipliers`. Default: `TimeZone.current`.
    public var localTimezone: TimeZone

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

    /// Use hybrid momentum: standard linear regression on rises, fast EMA on drops.
    /// Takes precedence over `useAsymmetricMomentum` when both are set.
    public var useHybridAsymmetricMomentum: Bool

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

    /// Enable post-low conservative mode.  When BG was below
    /// `postLowEntryThreshold` within the last `postLowWindow` hours, the
    /// auto-bolus applicationFactor is reduced to `postLowAppFactor` for the
    /// duration of the window. Designed to mitigate the "double-low" pattern:
    /// after a hypo, the user takes unannounced rescue carbs, BG rises
    /// rapidly, Loop misreads the rise as a normal meal rise and bolus,
    /// driving the user back into hypo while still in a sensitive regime.
    /// Default: false.
    public var postLowConservativeMode: Bool

    /// Hours after the most recent BG < entry threshold during which the
    /// conservative applicationFactor applies. Default: 3.0 hours.
    public var postLowWindow: Double

    /// applicationFactor used during post-low conservative window.
    /// Default: 0.2 (half of normal 0.4).
    public var postLowAppFactor: Double

    /// BG threshold (mg/dL) — readings below this trigger the post-low window.
    /// Default: 70 (clinical hypo cutoff).
    public var postLowEntryThreshold: Double

    /// If > 0, post-low conservative mode also requires the recent CGM rise
    /// rate (last 15 min) to exceed this threshold (mg/dL/min). Designed to
    /// detect rescue-carb signature specifically — sharp post-low rise
    /// strongly predicts the double-low pattern (15% double-rate at >2.4
    /// vs 4.8% below). 0 = disabled (any post-low cycle qualifies).
    /// Default: 0 (disabled).
    public var postLowRiseRateGate: Double

    /// If true, post-low mode additionally requires `prediction.activeInsulin`
    /// (IOB) to be above `postLowIOBGateThreshold`. Rationale: spontaneous
    /// lows in a moderate-IOB regime have ~10× higher double-rate than lows
    /// where Loop was already suspending heavily (negative IOB).
    /// Default: false.
    public var postLowRequireIOBHeadroom: Bool

    /// IOB threshold (U) for the post-low IOB gate. Active only when
    /// `postLowRequireIOBHeadroom` is true. Default: -0.5 U (above this =
    /// "less aggressive suspension" regime; below this = Loop already
    /// holding back, no need to add post-low protection).
    public var postLowIOBGateThreshold: Double

    /// Enable dynamic-ISF mode: scale the ISF used for dose recommendation
    /// based on recent rolling-mean insulin counteraction effect (ICE). When
    /// recent ICE is more negative than expected — meaning observed glucose is
    /// dropping faster than insulin alone explains, indicating elevated
    /// sensitivity — the ISF used for the correction calc scales up, making
    /// Loop more conservative. Designed to PREVENT lows by recognizing
    /// sensitivity in real time, addressing the root cause of the double-low
    /// pattern (Loop dosing into the rise from a non-suspended position
    /// because it didn't realize sensitivity was elevated).
    /// Forecast is unchanged; only the dose recommendation is scaled.
    /// Default: false.
    public var dynamicISFMode: Bool

    /// Rolling-window size for averaging ICE (hours). Default: 2.0.
    public var dynamicISFWindowHours: Double

    /// ICE threshold (mg/dL/min). When recent rolling-mean ICE is MORE
    /// NEGATIVE than -dynamicISFICEThreshold, scaling kicks in. Default: 0.5
    /// (i.e., ICE more negative than -0.5 mg/dL/min triggers).
    public var dynamicISFICEThreshold: Double

    /// Maximum ISF scale-up factor. Default: 0.5 (max +50% increase).
    public var dynamicISFMaxBoost: Double

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
        useHybridAsymmetricMomentum: Bool = false,
        momentumAlphaSlow: Double = 0.15,
        momentumAlphaFast: Double = 0.85,
        glucoseBasedApplicationFactor: Bool = false,
        gbafLowAnchor: Double = 140.0,
        gbafHighAnchor: Double = 220.0,
        gbafFactorLow: Double = 0.4,
        gbafFactorHigh: Double = 0.7,
        postLowConservativeMode: Bool = false,
        postLowWindow: Double = 3.0,
        postLowAppFactor: Double = 0.2,
        postLowEntryThreshold: Double = 70.0,
        postLowRiseRateGate: Double = 0.0,
        postLowRequireIOBHeadroom: Bool = false,
        postLowIOBGateThreshold: Double = -0.5,
        dynamicISFMode: Bool = false,
        dynamicISFWindowHours: Double = 2.0,
        dynamicISFICEThreshold: Double = 0.5,
        dynamicISFMaxBoost: Double = 0.5,
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
        self.useHybridAsymmetricMomentum    = useHybridAsymmetricMomentum
        self.glucoseBasedApplicationFactor  = glucoseBasedApplicationFactor
        self.gbafLowAnchor                  = gbafLowAnchor
        self.gbafHighAnchor                 = gbafHighAnchor
        self.gbafFactorLow                  = gbafFactorLow
        self.gbafFactorHigh                 = gbafFactorHigh
        self.postLowConservativeMode        = postLowConservativeMode
        self.postLowWindow                  = postLowWindow
        self.postLowAppFactor               = postLowAppFactor
        self.postLowEntryThreshold          = postLowEntryThreshold
        self.postLowRiseRateGate            = postLowRiseRateGate
        self.postLowRequireIOBHeadroom      = postLowRequireIOBHeadroom
        self.postLowIOBGateThreshold        = postLowIOBGateThreshold
        self.dynamicISFMode                 = dynamicISFMode
        self.dynamicISFWindowHours          = dynamicISFWindowHours
        self.dynamicISFICEThreshold         = dynamicISFICEThreshold
        self.dynamicISFMaxBoost             = dynamicISFMaxBoost
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
        case positiveVelocityCap, useAsymmetricMomentum, useHybridAsymmetricMomentum, momentumAlphaSlow, momentumAlphaFast
        case glucoseBasedApplicationFactor, gbafLowAnchor, gbafHighAnchor, gbafFactorLow, gbafFactorHigh
        case postLowConservativeMode, postLowWindow, postLowAppFactor, postLowEntryThreshold
        case postLowRiseRateGate, postLowRequireIOBHeadroom, postLowIOBGateThreshold
        case dynamicISFMode, dynamicISFWindowHours, dynamicISFICEThreshold, dynamicISFMaxBoost
        case sensitivityHourlyMultipliers, localTimezoneIdentifier
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
        self.useHybridAsymmetricMomentum = try c.decodeIfPresent(Bool.self, forKey: .useHybridAsymmetricMomentum) ?? false
        self.momentumAlphaSlow    = try c.decode(Double.self,       forKey: .momentumAlphaSlow)
        self.momentumAlphaFast    = try c.decode(Double.self,       forKey: .momentumAlphaFast)
        self.glucoseBasedApplicationFactor = try c.decodeIfPresent(Bool.self, forKey: .glucoseBasedApplicationFactor) ?? false
        self.gbafLowAnchor        = try c.decodeIfPresent(Double.self, forKey: .gbafLowAnchor)   ?? 140.0
        self.gbafHighAnchor       = try c.decodeIfPresent(Double.self, forKey: .gbafHighAnchor)  ?? 220.0
        self.gbafFactorLow        = try c.decodeIfPresent(Double.self, forKey: .gbafFactorLow)   ?? 0.4
        self.gbafFactorHigh       = try c.decodeIfPresent(Double.self, forKey: .gbafFactorHigh)  ?? 0.7
        self.postLowConservativeMode = try c.decodeIfPresent(Bool.self,   forKey: .postLowConservativeMode) ?? false
        self.postLowWindow        = try c.decodeIfPresent(Double.self, forKey: .postLowWindow)        ?? 3.0
        self.postLowAppFactor     = try c.decodeIfPresent(Double.self, forKey: .postLowAppFactor)     ?? 0.2
        self.postLowEntryThreshold = try c.decodeIfPresent(Double.self, forKey: .postLowEntryThreshold) ?? 70.0
        self.postLowRiseRateGate   = try c.decodeIfPresent(Double.self, forKey: .postLowRiseRateGate) ?? 0.0
        self.postLowRequireIOBHeadroom = try c.decodeIfPresent(Bool.self, forKey: .postLowRequireIOBHeadroom) ?? false
        self.postLowIOBGateThreshold = try c.decodeIfPresent(Double.self, forKey: .postLowIOBGateThreshold) ?? -0.5
        self.dynamicISFMode          = try c.decodeIfPresent(Bool.self,   forKey: .dynamicISFMode) ?? false
        self.dynamicISFWindowHours   = try c.decodeIfPresent(Double.self, forKey: .dynamicISFWindowHours) ?? 2.0
        self.dynamicISFICEThreshold  = try c.decodeIfPresent(Double.self, forKey: .dynamicISFICEThreshold) ?? 0.5
        self.dynamicISFMaxBoost      = try c.decodeIfPresent(Double.self, forKey: .dynamicISFMaxBoost) ?? 0.5
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
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(evalStep, forKey: .evalStep)
        try c.encode(includeFutureInsulin, forKey: .includeFutureInsulin)
        try c.encode(insulinLookbackHours, forKey: .insulinLookbackHours)
        try c.encode(glucoseLookbackHours, forKey: .glucoseLookbackHours)
        try c.encode(useIntegralRC, forKey: .useIntegralRC)
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
        try c.encode(useHybridAsymmetricMomentum, forKey: .useHybridAsymmetricMomentum)
        try c.encode(momentumAlphaSlow, forKey: .momentumAlphaSlow)
        try c.encode(momentumAlphaFast, forKey: .momentumAlphaFast)
        try c.encode(glucoseBasedApplicationFactor, forKey: .glucoseBasedApplicationFactor)
        try c.encode(gbafLowAnchor, forKey: .gbafLowAnchor)
        try c.encode(gbafHighAnchor, forKey: .gbafHighAnchor)
        try c.encode(gbafFactorLow, forKey: .gbafFactorLow)
        try c.encode(gbafFactorHigh, forKey: .gbafFactorHigh)
        try c.encode(postLowConservativeMode, forKey: .postLowConservativeMode)
        try c.encode(postLowWindow, forKey: .postLowWindow)
        try c.encode(postLowAppFactor, forKey: .postLowAppFactor)
        try c.encode(postLowEntryThreshold, forKey: .postLowEntryThreshold)
        try c.encode(postLowRiseRateGate, forKey: .postLowRiseRateGate)
        try c.encode(postLowRequireIOBHeadroom, forKey: .postLowRequireIOBHeadroom)
        try c.encode(postLowIOBGateThreshold, forKey: .postLowIOBGateThreshold)
        try c.encode(dynamicISFMode, forKey: .dynamicISFMode)
        try c.encode(dynamicISFWindowHours, forKey: .dynamicISFWindowHours)
        try c.encode(dynamicISFICEThreshold, forKey: .dynamicISFICEThreshold)
        try c.encode(dynamicISFMaxBoost, forKey: .dynamicISFMaxBoost)
        try c.encodeIfPresent(sensitivityHourlyMultipliers, forKey: .sensitivityHourlyMultipliers)
        try c.encode(localTimezone.identifier, forKey: .localTimezoneIdentifier)
        try c.encode(evalWarmupHours, forKey: .evalWarmupHours)
    }
}
