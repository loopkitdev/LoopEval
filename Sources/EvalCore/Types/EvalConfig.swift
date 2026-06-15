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
    /// IRC low-memory carry ("remember the low"): when > 0, a positive (rebound)
    /// discrepancy run carries the immediately-preceding negative (low) run across
    /// the sign flip instead of resetting, scaled by this factor. 0 == off.
    public var ircLowMemoryScale: Double
    /// IRC asymmetric PERSISTENCE ("remember the low longer than the high"): scales how
    /// long the correction lingers in the forecast by discrepancy sign. drop>1 = a
    /// negative-discrepancy (sensitivity) correction turns off slowly/persists; rise<1 =
    /// a positive-discrepancy (resistance) correction turns off fast. 1.0/1.0 == standard.
    public var ircDropDurationScale: Double
    public var ircRiseDurationScale: Double
    /// Cross-cycle SENSITIVE MODE ("remember the low to prevent a SECOND low").
    /// A level R (EWMA of recent NEGATIVE retrospective discrepancies, mg/dL) decays
    /// with time constant `sensitiveModeTauSec` and raises effective ISF by
    /// (1 + sensitiveModeGain · R) on FUTURE cycles — so after a sensitivity event Loop stays
    /// conservative for hours, preventing a delayed second low. Input-side, EGP-safe,
    /// fires on discrepancy SIGN (not BG level). tau=0 or gain=0 == off.
    public var sensitiveModeTauSec: TimeInterval
    public var sensitiveModeGain: Double
    /// ICE RISE-BOOST ("attack a SUSTAINED, actively-driven high"). The rise side of
    /// the unified ICE-response term: at high BG with sustained POSITIVE trailing ICE
    /// (BG being actively pushed up = a real persistent high, not a resolving spike),
    /// add a POSITIVE forecast offset so Loop doses harder. Offset =
    /// gain · gate(BG) · max(0, trailingICErate − thresh), where gate ramps 0→1 over
    /// [bgLo, bgHi] and trailingICErate (mg/dL/min) is the mean ICE over the last
    /// iceRiseBoostTauSec. Forecast-side (§2 "modify the forecast"); gated to high BG
    /// and persistence so it skips transient/resolving highs (where uniform GBAF
    /// causes lows). gain=0 == off.
    public var iceRiseBoostGain: Double
    public var iceRiseBoostBgLo: Double
    public var iceRiseBoostBgHi: Double
    public var iceRiseBoostTauSec: TimeInterval
    public var iceRiseBoostThresh: Double
    /// Lows-coupling of the rise-boost (the unification): suppress the high-attack
    /// when the SENSITIVE-MODE level R (recent negative-ICE memory) is elevated — i.e.
    /// don't attack a high during a recently-sensitive period (it may flip into a low).
    /// rise-boost ×= max(0, 1 − iceRiseBoostSensSuppress · R). 0 = off (uncoupled).
    public var iceRiseBoostSensSuppress: Double
    /// ISF-fade of the rise-boost: scale the boost gain by how AGGRESSIVELY the
    /// therapy is run, so the high-attack auto-disables as you tighten the lows
    /// budget. gain ×= clamp((isfFadeHi − sensitivityMultiplier)/(isfFadeHi − isfFadeLo), 0, 1)
    /// — full boost at ISF ≤ isfFadeLo (aggressive, budget region), zero at ISF ≥
    /// isfFadeHi (conservative, deep-low region) where the config collapses to pure
    /// smairc. So an ISF sweep traces the UPPER ENVELOPE of smairc and the coupled
    /// rise-boost. isfFadeHi ≤ isfFadeLo == off (no fade, full gain always).
    public var iceRiseBoostIsfFadeLo: Double
    public var iceRiseBoostIsfFadeHi: Double
    /// Pump dose quantization: round the auto-bolus / temp-basal-rate to the pump's
    /// supported increment (real Loop delivers on this grid — e.g. Omnipod 0.05U /
    /// 0.05 U/hr — and drops sub-increment doses; the sim otherwise emits continuous
    /// micro-boluses that never match a real pump). 0 = no rounding (legacy continuous).
    /// Default 0.05 (Omnipod). See project_field_stock_match.
    public var bolusIncrement: Double
    public var tempBasalIncrement: Double
    /// Candidate correction-range override (mg/dL). When set, the candidate's dose
    /// decision targets this range instead of the profile's; lets us sweep target
    /// midpoint & width independently of ISF. nil = use profile target.
    public var correctionRangeOverrideLow: Double?
    public var correctionRangeOverrideHigh: Double?

    /// Smooth actual CGM with a Kalman filter before comparison (not algorithm input).
    public var kalmanSmoothing: Bool

    /// Run the SIMULATOR (Loop's decision-time glucose input, the counter
    /// trajectory, and the outcome stats) on the ORIGINAL noisy CGM samples while
    /// keeping the smoothed trace for patient-physiology estimation (ICE + the
    /// sensitivity-multiplier m(t)). Requires kalmanSmoothing; no effect with
    /// --no-kalman (already all-raw). Default TRUE: the simulator runs on the
    /// real noisy CGM while physiology stays smoothed. Set false for the legacy
    /// all-smoothed sim.
    public var simRawGlucose: Bool

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

    /// Diagnostic: cap every carb entry's absorptionTime to at most this many
    /// seconds (0 = no cap). Shortening the logged absorption time raises the
    /// modeled absorption-rate ceiling, so a fast rise is absorbed into carbs
    /// instead of spilling into RC. Used to confirm the ICE→carb/RC mechanism.
    public var carbAbsorptionTimeCapSec: TimeInterval

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
    /// Forecast-keyed GBAF: key the application-factor ramp on max(currentBG, eventualBG)
    /// instead of currentBG, so Loop acts on a rising/high FORECAST even when current BG is
    /// still low-normal — but only when the predicted minimum is >= gbafForecastMinGuard
    /// (don't lift the throttle into a predicted dip). false = standard current-BG GBAF.
    public var gbafForecastKeyed: Bool
    public var gbafForecastMinGuard: Double
    /// Soft low-gate: replace Loop's hard 'predicted-min < range-floor -> zero auto-bolus'
    /// cliff with a graded ramp from the suspend threshold up to the range floor. false = original cliff.
    public var softLowGate: Bool
    /// Predicted-min cutoff (mg/dL) below which the auto-bolus gate engages. nil = the
    /// correction-range floor (standard Loop). e.g. 80 keeps the full application factor for
    /// predicted minimums down to that value before gating (a step toward the uncertainty cap).
    public var lowGateThresholdMgdl: Double?
    /// IOB-aware manual-bolus passthrough: when true, a real user bolus of `x` units delivered at
    /// real IOB `y` is resized to `x - (z - y)` (clamped to [0, maxBolus]) where `z` is the
    /// counterfactual IOB at that moment — i.e. if the candidate already carries more IOB, the user
    /// would have bolused less (Loop's bolus calc subtracts IOB), and vice versa. false = pass the
    /// real bolus through verbatim (original behavior).
    public var iobAdjustManualBoluses: Bool
    /// Manual-bolus mode: when true, REPLACE each real manual bolus with the candidate
    /// algorithm's OWN recommended manual bolus at that step (full correction vs the
    /// candidate's forecast/IOB/COB, clamped to maxBolus). Self-consistent with the
    /// candidate state, so it avoids the IOB-divergence amplification of the x−(z−y)
    /// resize. Takes precedence over `iobAdjustManualBoluses`. false = use the iobAdjust
    /// (or verbatim) passthrough.
    public var manualBolusFromRecommendation: Bool
    /// UAM projection (minutes): project recent unexplained glucose appearance (ICE minus
    /// modeled carbs) forward as ongoing absorption with a linear taper over this many
    /// minutes. Continuous unannounced-meal forecast term. 0 = off.
    public var uamProjectionMinutes: Double
    /// Early-ascending-limb projection (continuous complement of GBAF). When BG is low-normal
    /// AND rising, project the rise forward as a tapering meal-shaped forecast bump so the
    /// existing dosing logic covers the meal on its ascending limb (not at the peak). Active
    /// only when earlyRiseGain > 0 AND earlyRiseMinutes > 0.
    public var earlyRiseMinutes: Double
    public var earlyRiseGain: Double
    public var earlyRiseBgLow: Double
    public var earlyRiseBgHigh: Double
    public var earlyRiseSlopeThreshold: Double
    /// Dynamic ISF (continuous): the sensitivity used for DOSE SIZING is scaled by a
    /// linear ramp of current BG — g(BG)=1 at/below dynIsfLowAnchor, dynIsfMultHigh at/above
    /// dynIsfHighAnchor. multHigh<1 = more insulin per mg/dL gap when high (insulin
    /// resistance rises with glycemia). 1.0 = off (identity). Forecast ISF unchanged.
    public var dynIsfMultHigh: Double
    public var dynIsfLowAnchor: Double
    public var dynIsfHighAnchor: Double
    /// Uncertainty-bounded dosing cap. When enabled, REPLACES the flat/GBAF application factor
    /// AND the predicted-min bolus gate with a single state-derived cap: deliver the largest dose
    /// such that, for every horizon, the WORST-CASE trajectory (insulin effect amplified by
    /// 1+uncertaintyK) WITH maximum basal suspension stays ≥ the low threshold. A LEVEL cap on
    /// committed IOB (no wind-up), bounded at uncertaintyFmax × nominal need.
    public var uncertaintyCapEnabled: Bool
    /// k: sensitivity-uncertainty multiplier (worst case = insulin effect ×(1+k)). 0 = no buffer.
    public var uncertaintyK: Double
    /// Hard ceiling on the effective application factor (allowed dose / nominal need). Default 1.
    public var uncertaintyFmax: Double
    /// Low threshold (mg/dL) the worst-case-with-suspension must stay above. 0 = use suspendThreshold.
    public var uncertaintyLow: Double
    /// Autosens (sustained-resistance integral action). Scales the dose-sizing AND forecast ISF by
    /// (1 − gain × avg(BG − target) over autosensWindowMin): BG persistently ABOVE target ⇒ ISF↓
    /// (more insulin, resistant/under-counted-carbs); persistently below ⇒ ISF↑. Multi-hour average
    /// ignores transient rises/rebounds (the discrimination fast IRC lacks). 0 = off. Pairs with the
    /// uncertainty cap (anti-windup bound). Folds into RC eventually; separate effect for now.
    public var autosensGain: Double
    public var autosensWindowMin: Double
    public var autosensMin: Double
    public var autosensMax: Double
    /// Decouple the uncertainty cap's worst-case ISF from the autosens adjustment: the cap hedges
    /// that the resistance estimate could be wrong (insulin as effective as nominal). false = coupled.
    public var uncertaintyDecoupleAutosens: Bool

    /// Flat (global) auto-bolus application factor — fraction of the recommended
    /// correction applied per cycle when GBAF is off. Loop default 0.4. The auto-bolus
    /// is FLOORED to the pump increment AFTER this factor (see EvaluationEngine), which
    /// matches real devicestatus auto-boluses (~89% rloop / ~87% user2 exact) — do not
    /// lower this factor to compensate for round-to-nearest, that was a fitting artifact.
    public var applicationFactor: Double

    /// Asymmetric HIGH correction: rise-only BG-addition (positive-discrepancy driven)
    /// with a fast-off velocity gate. Off by default.
    public var highCorrectionEnabled: Bool
    public var highCorrectionRiseGain: Double
    public var highCorrectionEffectDurationMinutes: Double
    public var highCorrectionFastOffVelocity: Double

    /// OpenAPSAdapter-specific knobs. When non-nil, override the corresponding
    /// oref Preferences field. Nil = use oref defaults.
    /// - `oapsThresholdSetting`: oref's `threshold_setting` (mg/dL). The
    ///   minimum predicted-BG safety floor — SMB is gated off when minGuardBG
    ///   drops below it. Default 60.
    /// - `oapsSmbDeliveryRatio`: fraction of needed correction delivered as
    ///   SMB on each cycle. Default 0.5.
    /// - `oapsMaxSmbBasalMinutes`: cap on single-SMB size in minutes of
    ///   current basal. Default 30.
    public var oapsThresholdSetting: Double?
    public var oapsSmbDeliveryRatio: Double?
    public var oapsMaxSmbBasalMinutes: Double?
    /// `useNewFormula`: enable oref's Dynamic ISF (auto-scales ISF based on
    /// current BG — lower ISF at high BG = more aggressive, higher at low
    /// BG = less aggressive). oref's analog of Loop's GBAF.
    public var oapsUseNewFormula: Bool?
    /// `sigmoid`: use the sigmoid-shaped Dynamic ISF curve instead of the
    /// power-law one. Used together with useNewFormula.
    public var oapsSigmoid: Bool?
    /// `adjustmentFactor`: aggression of Dynamic ISF when useNewFormula is on
    /// (power-law form). Default 0.8.
    public var oapsAdjustmentFactor: Double?
    /// `adjustmentFactorSigmoid`: aggression of the sigmoid Dynamic ISF.
    /// Default 0.5.
    public var oapsAdjustmentFactorSigmoid: Double?
    /// Ablation: when false, set `enableUAM` off (no UAM forecast/SMB on unannounced rises).
    /// nil = leave default (on). Isolates oref's UAM forecast contribution from SMB delivery.
    public var oapsEnableUAM: Bool?
    /// Ablation: when false, disable all SMB (enableSMB_always/with_COB/after_carbs/UAM off),
    /// leaving temp-basal-only dosing. nil = leave default (on). Isolates the SMB delivery cadence.
    public var oapsEnableSMB: Bool?

    /// Post-low (sustained-sensitivity) forecast suppression: when a recent low
    /// (< postlowThresholdMgdl within postlowWindowMin) occurred, lower the
    /// forecast by up to postlowSuppressMgdl (decaying over the window) so Loop
    /// backs off — a SELECTIVE lows-protector for the repeat-low/rebound regime.
    public var postlowSuppressMgdl: Double
    public var postlowWindowMin: Double
    public var postlowThresholdMgdl: Double
    /// Trend augmentation: within the post-low window, ADD this many mg/dL of
    /// forecast suppression per mg/dL/min of current DOWNTREND (causal velocity
    /// over the last ~20 min). Targets the rebound's second drop with lead time;
    /// fires only while BG is actually dropping again (not while recovering), so
    /// it adds lows-protection without the blanket-window TIR cost. 0 = off
    /// (≡ the plain recency-decay post-low protector).
    public var postlowTrendGain: Double
    /// Sustained post-low ISF REDUCTION (input-side). Within the post-low window
    /// scale Loop's effective ISF by up to this factor (>1 = insulin modeled MORE
    /// effective = Loop sizes the rebound CORRECTION down at the source, not just
    /// nudges the forecast — so it doesn't saturate at the suspend wall the way
    /// pure forecast-suppression does). Decays with recency (slow-off). EGP-safe
    /// in practice (acts at the rebound's super-basal dosing where net~physical).
    /// 1.0 = off.
    public var postlowIsfMult: Double

    /// PREDICTIVE pre-low damper: a strict-causal sustained-sensitivity trigger.
    /// Over a trailing window compute causal ICE = v_bg − v_insulin (BG dropping
    /// faster than the candidate's OWN insulin explains = a sensitivity
    /// excursion, selective vs a normal bolus drawdown where ICE≈0). When that
    /// rate is below −`sensDampThresholdRate`, raise effective ISF (dose less)
    /// PROACTIVELY — before the low, while still super-basal — so the IOB that
    /// would later crash BG never accumulates. Input-side, EGP-safe (shares the
    /// post-low ISF path). `sensDampGain` = ISF-mult increase per mg/dL/min of
    /// negative ICE beyond threshold; capped at `sensDampMax`. gain 0 = off.
    public var sensDampWindowMin: Double
    public var sensDampThresholdRate: Double
    public var sensDampGain: Double
    public var sensDampMax: Double

    // MARK: – Defaults

    /// A config with all defaults. Convenience used widely by tests and callers.
    public static var `default`: EvalConfig { EvalConfig() }

    public init(
        glucoseBasedApplicationFactor: Bool = false,
        gbafLowAnchor: Double = 140.0,
        gbafHighAnchor: Double = 220.0,
        gbafFactorLow: Double = 0.4,
        gbafFactorHigh: Double = 0.7,
        gbafForecastKeyed: Bool = false,
        gbafForecastMinGuard: Double = 85.0,
        softLowGate: Bool = false,
        lowGateThresholdMgdl: Double? = nil,
        iobAdjustManualBoluses: Bool = true,   // veracity default: resize passed-through user boluses by counterfactual−real IOB
        manualBolusFromRecommendation: Bool = false,
        uamProjectionMinutes: Double = 0,
        earlyRiseMinutes: Double = 0,
        earlyRiseGain: Double = 0,
        earlyRiseBgLow: Double = 70,
        earlyRiseBgHigh: Double = 140,
        earlyRiseSlopeThreshold: Double = 0.3,
        dynIsfMultHigh: Double = 1.0,
        dynIsfLowAnchor: Double = 100,
        dynIsfHighAnchor: Double = 200,
        uncertaintyCapEnabled: Bool = false,
        uncertaintyK: Double = 0.5,
        uncertaintyFmax: Double = 1.0,
        uncertaintyLow: Double = 0,
        autosensGain: Double = 0,
        autosensWindowMin: Double = 360,
        autosensMin: Double = 0.7,
        autosensMax: Double = 1.3,
        uncertaintyDecoupleAutosens: Bool = false,
        applicationFactor: Double = 0.4,
        highCorrectionEnabled: Bool = false,
        highCorrectionRiseGain: Double = 1.0,
        highCorrectionEffectDurationMinutes: Double = 60.0,
        highCorrectionFastOffVelocity: Double = 0.5,
        oapsThresholdSetting: Double? = nil,
        oapsSmbDeliveryRatio: Double? = nil,
        oapsMaxSmbBasalMinutes: Double? = nil,
        oapsUseNewFormula: Bool? = nil,
        oapsSigmoid: Bool? = nil,
        oapsAdjustmentFactor: Double? = nil,
        oapsAdjustmentFactorSigmoid: Double? = nil,
        oapsEnableUAM: Bool? = nil,
        oapsEnableSMB: Bool? = nil,
        postlowSuppressMgdl: Double = 0.0,
        postlowWindowMin: Double = 120.0,
        postlowThresholdMgdl: Double = 70.0,
        postlowTrendGain: Double = 0.0,
        postlowIsfMult: Double = 1.0,
        sensDampWindowMin: Double = 45.0,
        sensDampThresholdRate: Double = 0.4,
        sensDampGain: Double = 0.0,
        sensDampMax: Double = 2.5,
        evalStep: TimeInterval = 5 * 60,
        includeFutureInsulin: Bool = true,
        includeFutureCarbs: Bool = false,
        insulinLookbackHours: Double = 16,
        glucoseLookbackHours: Double = 10,
        useIntegralRC: Bool = false,
        ircDropGainScale: Double = 1.0,
        ircRiseGainScale: Double = 1.0,
        ircLowMemoryScale: Double = 0.0,
        ircDropDurationScale: Double = 1.0,
        ircRiseDurationScale: Double = 1.0,
        sensitiveModeTauSec: TimeInterval = 0,
        sensitiveModeGain: Double = 0,
        iceRiseBoostGain: Double = 0,
        iceRiseBoostBgLo: Double = 170,
        iceRiseBoostBgHi: Double = 250,
        iceRiseBoostTauSec: TimeInterval = 45 * 60,
        iceRiseBoostThresh: Double = 0,
        iceRiseBoostSensSuppress: Double = 0,
        iceRiseBoostIsfFadeLo: Double = 0,
        iceRiseBoostIsfFadeHi: Double = 0,
        bolusIncrement: Double = 0.05,
        tempBasalIncrement: Double = 0.05,
        correctionRangeOverrideLow: Double? = nil,
        correctionRangeOverrideHigh: Double? = nil,
        kalmanSmoothing: Bool = true,
        simRawGlucose: Bool = true,
        horizons: [TimeInterval] = stride(from: 30.0, through: 360.0, by: 30.0)
            .map { $0 * 60 },
        includingPositiveVelocityAndRC: Bool = true,
        useMidAbsorptionISF: Bool = true,
        carbAbsorptionModel: CarbAbsorptionModel = .piecewiseLinear,
        carbAbsorptionTimeCapSec: TimeInterval = 0,
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
        self.gbafForecastKeyed              = gbafForecastKeyed
        self.gbafForecastMinGuard           = gbafForecastMinGuard
        self.softLowGate                    = softLowGate
        self.lowGateThresholdMgdl           = lowGateThresholdMgdl
        self.iobAdjustManualBoluses         = iobAdjustManualBoluses
        self.manualBolusFromRecommendation  = manualBolusFromRecommendation
        self.uamProjectionMinutes           = uamProjectionMinutes
        self.earlyRiseMinutes               = earlyRiseMinutes
        self.earlyRiseGain                  = earlyRiseGain
        self.earlyRiseBgLow                 = earlyRiseBgLow
        self.earlyRiseBgHigh                = earlyRiseBgHigh
        self.earlyRiseSlopeThreshold        = earlyRiseSlopeThreshold
        self.dynIsfMultHigh                 = dynIsfMultHigh
        self.dynIsfLowAnchor                = dynIsfLowAnchor
        self.dynIsfHighAnchor               = dynIsfHighAnchor
        self.uncertaintyCapEnabled          = uncertaintyCapEnabled
        self.uncertaintyK                   = uncertaintyK
        self.uncertaintyFmax                = uncertaintyFmax
        self.uncertaintyLow                 = uncertaintyLow
        self.autosensGain                   = autosensGain
        self.autosensWindowMin              = autosensWindowMin
        self.autosensMin                    = autosensMin
        self.autosensMax                    = autosensMax
        self.uncertaintyDecoupleAutosens    = uncertaintyDecoupleAutosens
        self.applicationFactor              = applicationFactor
        self.highCorrectionEnabled          = highCorrectionEnabled
        self.highCorrectionRiseGain         = highCorrectionRiseGain
        self.highCorrectionEffectDurationMinutes = highCorrectionEffectDurationMinutes
        self.highCorrectionFastOffVelocity  = highCorrectionFastOffVelocity
        self.oapsThresholdSetting           = oapsThresholdSetting
        self.oapsSmbDeliveryRatio           = oapsSmbDeliveryRatio
        self.oapsMaxSmbBasalMinutes         = oapsMaxSmbBasalMinutes
        self.oapsUseNewFormula              = oapsUseNewFormula
        self.oapsSigmoid                    = oapsSigmoid
        self.oapsAdjustmentFactor           = oapsAdjustmentFactor
        self.oapsAdjustmentFactorSigmoid    = oapsAdjustmentFactorSigmoid
        self.oapsEnableUAM                  = oapsEnableUAM
        self.oapsEnableSMB                  = oapsEnableSMB
        self.postlowSuppressMgdl            = postlowSuppressMgdl
        self.postlowWindowMin               = postlowWindowMin
        self.postlowThresholdMgdl           = postlowThresholdMgdl
        self.postlowTrendGain               = postlowTrendGain
        self.postlowIsfMult                 = postlowIsfMult
        self.sensDampWindowMin              = sensDampWindowMin
        self.sensDampThresholdRate          = sensDampThresholdRate
        self.sensDampGain                   = sensDampGain
        self.sensDampMax                    = sensDampMax
        self.evalStep                       = evalStep
        self.includeFutureInsulin           = includeFutureInsulin
        self.includeFutureCarbs             = includeFutureCarbs
        self.insulinLookbackHours           = insulinLookbackHours
        self.glucoseLookbackHours           = glucoseLookbackHours
        self.useIntegralRC                  = useIntegralRC
        self.ircDropGainScale               = ircDropGainScale
        self.ircRiseGainScale               = ircRiseGainScale
        self.ircLowMemoryScale              = ircLowMemoryScale
        self.ircDropDurationScale           = ircDropDurationScale
        self.ircRiseDurationScale           = ircRiseDurationScale
        self.sensitiveModeTauSec               = sensitiveModeTauSec
        self.sensitiveModeGain                 = sensitiveModeGain
        self.iceRiseBoostGain                  = iceRiseBoostGain
        self.iceRiseBoostBgLo                  = iceRiseBoostBgLo
        self.iceRiseBoostBgHi                  = iceRiseBoostBgHi
        self.iceRiseBoostTauSec                = iceRiseBoostTauSec
        self.iceRiseBoostThresh                = iceRiseBoostThresh
        self.iceRiseBoostSensSuppress          = iceRiseBoostSensSuppress
        self.iceRiseBoostIsfFadeLo             = iceRiseBoostIsfFadeLo
        self.iceRiseBoostIsfFadeHi             = iceRiseBoostIsfFadeHi
        self.bolusIncrement                    = bolusIncrement
        self.tempBasalIncrement                = tempBasalIncrement
        self.correctionRangeOverrideLow     = correctionRangeOverrideLow
        self.correctionRangeOverrideHigh    = correctionRangeOverrideHigh
        self.kalmanSmoothing                = kalmanSmoothing
        self.simRawGlucose                  = simRawGlucose
        self.horizons                       = horizons
        self.includingPositiveVelocityAndRC = includingPositiveVelocityAndRC
        self.useMidAbsorptionISF            = useMidAbsorptionISF
        self.carbAbsorptionModel            = carbAbsorptionModel
        self.carbAbsorptionTimeCapSec       = carbAbsorptionTimeCapSec
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
        case useIntegralRC, ircDropGainScale, ircRiseGainScale, ircLowMemoryScale, ircDropDurationScale, ircRiseDurationScale, sensitiveModeTauSec, sensitiveModeGain, iceRiseBoostGain, iceRiseBoostBgLo, iceRiseBoostBgHi, iceRiseBoostTauSec, iceRiseBoostThresh, iceRiseBoostSensSuppress, iceRiseBoostIsfFadeLo, iceRiseBoostIsfFadeHi, bolusIncrement, tempBasalIncrement, correctionRangeOverrideLow, correctionRangeOverrideHigh, kalmanSmoothing, simRawGlucose, horizons, includingPositiveVelocityAndRC
        case useMidAbsorptionISF, carbAbsorptionModel, carbAbsorptionTimeCapSec
        case sensitivityMultiplier, carbRatioMultiplier, basalRateMultiplier
        case targetLow, targetHigh, dangerLow, dangerHigh
        case positiveVelocityCap, useAsymmetricMomentum, momentumAlphaSlow, momentumAlphaFast
        case sensitivityHourlyMultipliers, localTimezoneIdentifier
        case evalWarmupHours
        case glucoseBasedApplicationFactor, gbafLowAnchor, gbafHighAnchor, gbafFactorLow, gbafFactorHigh, gbafForecastKeyed, gbafForecastMinGuard, softLowGate, lowGateThresholdMgdl, iobAdjustManualBoluses, manualBolusFromRecommendation, uamProjectionMinutes, earlyRiseMinutes, earlyRiseGain, earlyRiseBgLow, earlyRiseBgHigh, earlyRiseSlopeThreshold, dynIsfMultHigh, dynIsfLowAnchor, dynIsfHighAnchor, uncertaintyCapEnabled, uncertaintyK, uncertaintyFmax, uncertaintyLow, autosensGain, autosensWindowMin, autosensMin, autosensMax, uncertaintyDecoupleAutosens
        case applicationFactor
        case highCorrectionEnabled, highCorrectionRiseGain, highCorrectionEffectDurationMinutes, highCorrectionFastOffVelocity
        case oapsThresholdSetting, oapsSmbDeliveryRatio, oapsMaxSmbBasalMinutes
        case oapsUseNewFormula, oapsSigmoid, oapsAdjustmentFactor, oapsAdjustmentFactorSigmoid
        case oapsEnableUAM, oapsEnableSMB
        case postlowSuppressMgdl, postlowWindowMin, postlowThresholdMgdl, postlowTrendGain, postlowIsfMult
        case sensDampWindowMin, sensDampThresholdRate, sensDampGain, sensDampMax
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
        self.ircLowMemoryScale    = try c.decodeIfPresent(Double.self, forKey: .ircLowMemoryScale) ?? 0.0
        self.ircDropDurationScale = try c.decodeIfPresent(Double.self, forKey: .ircDropDurationScale) ?? 1.0
        self.ircRiseDurationScale = try c.decodeIfPresent(Double.self, forKey: .ircRiseDurationScale) ?? 1.0
        self.sensitiveModeTauSec     = try c.decodeIfPresent(TimeInterval.self, forKey: .sensitiveModeTauSec) ?? 0
        self.sensitiveModeGain       = try c.decodeIfPresent(Double.self, forKey: .sensitiveModeGain) ?? 0
        self.iceRiseBoostGain        = try c.decodeIfPresent(Double.self, forKey: .iceRiseBoostGain) ?? 0
        self.iceRiseBoostBgLo        = try c.decodeIfPresent(Double.self, forKey: .iceRiseBoostBgLo) ?? 170
        self.iceRiseBoostBgHi        = try c.decodeIfPresent(Double.self, forKey: .iceRiseBoostBgHi) ?? 250
        self.iceRiseBoostTauSec      = try c.decodeIfPresent(TimeInterval.self, forKey: .iceRiseBoostTauSec) ?? (45*60)
        self.iceRiseBoostThresh      = try c.decodeIfPresent(Double.self, forKey: .iceRiseBoostThresh) ?? 0
        self.iceRiseBoostSensSuppress = try c.decodeIfPresent(Double.self, forKey: .iceRiseBoostSensSuppress) ?? 0
        self.iceRiseBoostIsfFadeLo = try c.decodeIfPresent(Double.self, forKey: .iceRiseBoostIsfFadeLo) ?? 0
        self.iceRiseBoostIsfFadeHi = try c.decodeIfPresent(Double.self, forKey: .iceRiseBoostIsfFadeHi) ?? 0
        self.bolusIncrement = try c.decodeIfPresent(Double.self, forKey: .bolusIncrement) ?? 0.05
        self.tempBasalIncrement = try c.decodeIfPresent(Double.self, forKey: .tempBasalIncrement) ?? 0.05
        self.correctionRangeOverrideLow  = try c.decodeIfPresent(Double.self, forKey: .correctionRangeOverrideLow)
        self.correctionRangeOverrideHigh = try c.decodeIfPresent(Double.self, forKey: .correctionRangeOverrideHigh)
        self.kalmanSmoothing      = try c.decode(Bool.self,         forKey: .kalmanSmoothing)
        self.simRawGlucose        = (try? c.decode(Bool.self,       forKey: .simRawGlucose)) ?? false
        self.horizons             = try c.decode([TimeInterval].self, forKey: .horizons)
        self.includingPositiveVelocityAndRC = try c.decode(Bool.self, forKey: .includingPositiveVelocityAndRC)
        self.useMidAbsorptionISF  = try c.decode(Bool.self,         forKey: .useMidAbsorptionISF)
        self.carbAbsorptionModel  = try c.decode(CarbAbsorptionModel.self, forKey: .carbAbsorptionModel)
        self.carbAbsorptionTimeCapSec = try c.decodeIfPresent(TimeInterval.self, forKey: .carbAbsorptionTimeCapSec) ?? 0
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
        self.gbafForecastKeyed    = try c.decodeIfPresent(Bool.self, forKey: .gbafForecastKeyed) ?? false
        self.gbafForecastMinGuard = try c.decodeIfPresent(Double.self, forKey: .gbafForecastMinGuard) ?? 85.0
        self.softLowGate          = try c.decodeIfPresent(Bool.self, forKey: .softLowGate) ?? false
        self.lowGateThresholdMgdl = try c.decodeIfPresent(Double.self, forKey: .lowGateThresholdMgdl)
        self.iobAdjustManualBoluses = try c.decodeIfPresent(Bool.self, forKey: .iobAdjustManualBoluses) ?? true
        self.manualBolusFromRecommendation = try c.decodeIfPresent(Bool.self, forKey: .manualBolusFromRecommendation) ?? false
        self.uamProjectionMinutes = try c.decodeIfPresent(Double.self, forKey: .uamProjectionMinutes) ?? 0
        self.earlyRiseMinutes        = try c.decodeIfPresent(Double.self, forKey: .earlyRiseMinutes) ?? 0
        self.earlyRiseGain           = try c.decodeIfPresent(Double.self, forKey: .earlyRiseGain) ?? 0
        self.earlyRiseBgLow          = try c.decodeIfPresent(Double.self, forKey: .earlyRiseBgLow) ?? 70
        self.earlyRiseBgHigh         = try c.decodeIfPresent(Double.self, forKey: .earlyRiseBgHigh) ?? 140
        self.earlyRiseSlopeThreshold = try c.decodeIfPresent(Double.self, forKey: .earlyRiseSlopeThreshold) ?? 0.3
        self.dynIsfMultHigh       = try c.decodeIfPresent(Double.self, forKey: .dynIsfMultHigh) ?? 1.0
        self.dynIsfLowAnchor      = try c.decodeIfPresent(Double.self, forKey: .dynIsfLowAnchor) ?? 100
        self.dynIsfHighAnchor     = try c.decodeIfPresent(Double.self, forKey: .dynIsfHighAnchor) ?? 200
        self.uncertaintyCapEnabled = try c.decodeIfPresent(Bool.self, forKey: .uncertaintyCapEnabled) ?? false
        self.uncertaintyK          = try c.decodeIfPresent(Double.self, forKey: .uncertaintyK) ?? 0.5
        self.uncertaintyFmax       = try c.decodeIfPresent(Double.self, forKey: .uncertaintyFmax) ?? 1.0
        self.uncertaintyLow        = try c.decodeIfPresent(Double.self, forKey: .uncertaintyLow) ?? 0
        self.autosensGain      = try c.decodeIfPresent(Double.self, forKey: .autosensGain) ?? 0
        self.autosensWindowMin = try c.decodeIfPresent(Double.self, forKey: .autosensWindowMin) ?? 360
        self.autosensMin       = try c.decodeIfPresent(Double.self, forKey: .autosensMin) ?? 0.7
        self.autosensMax       = try c.decodeIfPresent(Double.self, forKey: .autosensMax) ?? 1.3
        self.uncertaintyDecoupleAutosens = try c.decodeIfPresent(Bool.self, forKey: .uncertaintyDecoupleAutosens) ?? false
        self.applicationFactor    = try c.decodeIfPresent(Double.self, forKey: .applicationFactor) ?? 0.4
        self.highCorrectionEnabled = try c.decodeIfPresent(Bool.self, forKey: .highCorrectionEnabled) ?? false
        self.highCorrectionRiseGain = try c.decodeIfPresent(Double.self, forKey: .highCorrectionRiseGain) ?? 1.0
        self.highCorrectionEffectDurationMinutes = try c.decodeIfPresent(Double.self, forKey: .highCorrectionEffectDurationMinutes) ?? 60.0
        self.highCorrectionFastOffVelocity = try c.decodeIfPresent(Double.self, forKey: .highCorrectionFastOffVelocity) ?? 0.5
        self.oapsThresholdSetting = try c.decodeIfPresent(Double.self, forKey: .oapsThresholdSetting)
        self.oapsSmbDeliveryRatio = try c.decodeIfPresent(Double.self, forKey: .oapsSmbDeliveryRatio)
        self.oapsMaxSmbBasalMinutes = try c.decodeIfPresent(Double.self, forKey: .oapsMaxSmbBasalMinutes)
        self.oapsUseNewFormula = try c.decodeIfPresent(Bool.self, forKey: .oapsUseNewFormula)
        self.oapsSigmoid = try c.decodeIfPresent(Bool.self, forKey: .oapsSigmoid)
        self.oapsAdjustmentFactor = try c.decodeIfPresent(Double.self, forKey: .oapsAdjustmentFactor)
        self.oapsAdjustmentFactorSigmoid = try c.decodeIfPresent(Double.self, forKey: .oapsAdjustmentFactorSigmoid)
        self.oapsEnableUAM = try c.decodeIfPresent(Bool.self, forKey: .oapsEnableUAM)
        self.oapsEnableSMB = try c.decodeIfPresent(Bool.self, forKey: .oapsEnableSMB)
        self.postlowSuppressMgdl = try c.decodeIfPresent(Double.self, forKey: .postlowSuppressMgdl) ?? 0.0
        self.postlowWindowMin = try c.decodeIfPresent(Double.self, forKey: .postlowWindowMin) ?? 120.0
        self.postlowThresholdMgdl = try c.decodeIfPresent(Double.self, forKey: .postlowThresholdMgdl) ?? 70.0
        self.postlowTrendGain = try c.decodeIfPresent(Double.self, forKey: .postlowTrendGain) ?? 0.0
        self.postlowIsfMult = try c.decodeIfPresent(Double.self, forKey: .postlowIsfMult) ?? 1.0
        self.sensDampWindowMin = try c.decodeIfPresent(Double.self, forKey: .sensDampWindowMin) ?? 45.0
        self.sensDampThresholdRate = try c.decodeIfPresent(Double.self, forKey: .sensDampThresholdRate) ?? 0.4
        self.sensDampGain = try c.decodeIfPresent(Double.self, forKey: .sensDampGain) ?? 0.0
        self.sensDampMax = try c.decodeIfPresent(Double.self, forKey: .sensDampMax) ?? 2.5
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
        try c.encode(ircLowMemoryScale, forKey: .ircLowMemoryScale)
        try c.encode(ircDropDurationScale, forKey: .ircDropDurationScale)
        try c.encode(ircRiseDurationScale, forKey: .ircRiseDurationScale)
        try c.encode(sensitiveModeTauSec, forKey: .sensitiveModeTauSec)
        try c.encode(sensitiveModeGain, forKey: .sensitiveModeGain)
        try c.encode(iceRiseBoostGain, forKey: .iceRiseBoostGain)
        try c.encode(iceRiseBoostBgLo, forKey: .iceRiseBoostBgLo)
        try c.encode(iceRiseBoostBgHi, forKey: .iceRiseBoostBgHi)
        try c.encode(iceRiseBoostTauSec, forKey: .iceRiseBoostTauSec)
        try c.encode(iceRiseBoostThresh, forKey: .iceRiseBoostThresh)
        try c.encode(iceRiseBoostSensSuppress, forKey: .iceRiseBoostSensSuppress)
        try c.encode(iceRiseBoostIsfFadeLo, forKey: .iceRiseBoostIsfFadeLo)
        try c.encode(iceRiseBoostIsfFadeHi, forKey: .iceRiseBoostIsfFadeHi)
        try c.encode(bolusIncrement, forKey: .bolusIncrement)
        try c.encode(tempBasalIncrement, forKey: .tempBasalIncrement)
        try c.encodeIfPresent(correctionRangeOverrideLow, forKey: .correctionRangeOverrideLow)
        try c.encodeIfPresent(correctionRangeOverrideHigh, forKey: .correctionRangeOverrideHigh)
        try c.encode(kalmanSmoothing, forKey: .kalmanSmoothing)
        try c.encode(simRawGlucose, forKey: .simRawGlucose)
        try c.encode(horizons, forKey: .horizons)
        try c.encode(includingPositiveVelocityAndRC, forKey: .includingPositiveVelocityAndRC)
        try c.encode(useMidAbsorptionISF, forKey: .useMidAbsorptionISF)
        try c.encode(carbAbsorptionModel, forKey: .carbAbsorptionModel)
        try c.encode(carbAbsorptionTimeCapSec, forKey: .carbAbsorptionTimeCapSec)
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
        try c.encode(gbafForecastKeyed, forKey: .gbafForecastKeyed)
        try c.encode(gbafForecastMinGuard, forKey: .gbafForecastMinGuard)
        try c.encode(softLowGate, forKey: .softLowGate)
        try c.encodeIfPresent(lowGateThresholdMgdl, forKey: .lowGateThresholdMgdl)
        try c.encode(iobAdjustManualBoluses, forKey: .iobAdjustManualBoluses)
        try c.encode(manualBolusFromRecommendation, forKey: .manualBolusFromRecommendation)
        try c.encode(uamProjectionMinutes, forKey: .uamProjectionMinutes)
        try c.encode(earlyRiseMinutes, forKey: .earlyRiseMinutes)
        try c.encode(earlyRiseGain, forKey: .earlyRiseGain)
        try c.encode(earlyRiseBgLow, forKey: .earlyRiseBgLow)
        try c.encode(earlyRiseBgHigh, forKey: .earlyRiseBgHigh)
        try c.encode(earlyRiseSlopeThreshold, forKey: .earlyRiseSlopeThreshold)
        try c.encode(dynIsfMultHigh, forKey: .dynIsfMultHigh)
        try c.encode(dynIsfLowAnchor, forKey: .dynIsfLowAnchor)
        try c.encode(dynIsfHighAnchor, forKey: .dynIsfHighAnchor)
        try c.encode(uncertaintyCapEnabled, forKey: .uncertaintyCapEnabled)
        try c.encode(uncertaintyK, forKey: .uncertaintyK)
        try c.encode(uncertaintyFmax, forKey: .uncertaintyFmax)
        try c.encode(uncertaintyLow, forKey: .uncertaintyLow)
        try c.encode(autosensGain, forKey: .autosensGain)
        try c.encode(autosensWindowMin, forKey: .autosensWindowMin)
        try c.encode(autosensMin, forKey: .autosensMin)
        try c.encode(autosensMax, forKey: .autosensMax)
        try c.encode(uncertaintyDecoupleAutosens, forKey: .uncertaintyDecoupleAutosens)
        try c.encode(applicationFactor, forKey: .applicationFactor)
        try c.encode(highCorrectionEnabled, forKey: .highCorrectionEnabled)
        try c.encode(highCorrectionRiseGain, forKey: .highCorrectionRiseGain)
        try c.encode(highCorrectionEffectDurationMinutes, forKey: .highCorrectionEffectDurationMinutes)
        try c.encode(highCorrectionFastOffVelocity, forKey: .highCorrectionFastOffVelocity)
        try c.encodeIfPresent(oapsThresholdSetting, forKey: .oapsThresholdSetting)
        try c.encodeIfPresent(oapsSmbDeliveryRatio, forKey: .oapsSmbDeliveryRatio)
        try c.encodeIfPresent(oapsMaxSmbBasalMinutes, forKey: .oapsMaxSmbBasalMinutes)
        try c.encodeIfPresent(oapsUseNewFormula, forKey: .oapsUseNewFormula)
        try c.encodeIfPresent(oapsSigmoid, forKey: .oapsSigmoid)
        try c.encodeIfPresent(oapsAdjustmentFactor, forKey: .oapsAdjustmentFactor)
        try c.encodeIfPresent(oapsAdjustmentFactorSigmoid, forKey: .oapsAdjustmentFactorSigmoid)
        try c.encodeIfPresent(oapsEnableUAM, forKey: .oapsEnableUAM)
        try c.encodeIfPresent(oapsEnableSMB, forKey: .oapsEnableSMB)
        try c.encode(postlowSuppressMgdl, forKey: .postlowSuppressMgdl)
        try c.encode(postlowWindowMin, forKey: .postlowWindowMin)
        try c.encode(postlowThresholdMgdl, forKey: .postlowThresholdMgdl)
        try c.encode(postlowTrendGain, forKey: .postlowTrendGain)
        try c.encode(postlowIsfMult, forKey: .postlowIsfMult)
        try c.encode(sensDampWindowMin, forKey: .sensDampWindowMin)
        try c.encode(sensDampThresholdRate, forKey: .sensDampThresholdRate)
        try c.encode(sensDampGain, forKey: .sensDampGain)
        try c.encode(sensDampMax, forKey: .sensDampMax)
    }
}
