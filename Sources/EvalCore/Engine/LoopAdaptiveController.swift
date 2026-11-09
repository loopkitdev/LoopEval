// LoopAdaptiveController.swift — the Loop Adaptive Algorithm in-process, as a candidate controller.
//
// --candidate-loop-adaptive '<json params>': the same decision as
//   --candidate-external-controller "python analysis/reduction/adaptive.py tdd_pd '<json params>'"
// computed by the LoopAdaptive module of the LoopAlgorithm package instead of a Python process (parity-tested
// there against adaptive.py). The params are adaptive.py's names and defaults; the request is the one
// ExternalControllerAdapter would send, so everything around the decision is unchanged.
//
// LoopAdaptive implements the evaluated candidate's form only. Params outside it (prop_temp 0, ad_isf ≠ 0,
// ad_basal ≠ 1, manual_w, manual_tau, iob_cap_h) are refused rather than silently ignored.

import Foundation
import LoopAlgorithm
import LoopAdaptive

public final class LoopAdaptiveController: @unchecked Sendable {
    private let parameters: AdaptiveParameters
    private let profile: AdaptiveProfile
    private let useTarget: Bool, useOverride: Bool, ownManual: Bool
    private var state = AdaptiveState()

    public struct ParameterError: Error, CustomStringConvertible { public let description: String }

    /// adaptive.py TddPD.defaults: a param missing from the JSON takes the reference's default, as it does there.
    static let defaults: [String: Double] = [
        "tdd": 40, "isf_k": 688, "isf_e": 0.74, "basal_frac": 0.45, "target": 110, "t_low": 80, "t_bolus": 120,
        "h": 30, "slope_cap": 3, "rise_cap": 80, "af": 0.4, "fall_gate": -1, "withhold_u": 0.3, "peak": 75,
        "manual_w": 0, "cr_k": 0, "manual_tau": 0, "prop_temp": 0, "temp_floor_bg": 80,
        "basal_uh": 0, "ad_basal": 1, "ad_isf": 1, "iob_cap_h": 0, "rc_k": 0, "rc_cap": 150,
        "ad_sp": 0, "ad_k": 0.0139, "ad_lo": 80, "ad_klo": 3, "ad_min": 0.33, "ad_max": 3, "ad_brake_h": 0,
        "use_target": 0, "use_override": 0, "target_min": 87, "own_manual": 0,
        "gsl": 0, "gsl_settings": 1, "gsl_h": 180,
        "hab_k": 0, "hab_ref": 0.3, "hab_days": 7, "hab_min_days": 3, "hab_hl": 7, "hab_lo": -60, "hab_hi": 80,
    ]
    /// Params LoopAdaptive fixes at the candidate's value.
    static let fixed: [String: Double] = ["prop_temp": 1, "ad_isf": 0, "ad_basal": 1, "manual_w": 0, "manual_tau": 0, "iob_cap_h": 0]

    public init(json: String) throws {
        guard let obj = try JSONSerialization.jsonObject(with: Data(json.utf8)) as? [String: Any] else {
            throw ParameterError(description: "--candidate-loop-adaptive: params must be a JSON object")
        }
        var q = Self.defaults
        for (k, v) in obj {
            guard Self.defaults[k] != nil else { throw ParameterError(description: "--candidate-loop-adaptive: unknown param \(k)") }
            guard let n = (v as? NSNumber)?.doubleValue, n.isFinite else {
                throw ParameterError(description: "--candidate-loop-adaptive: \(k) must be a number")
            }
            q[k] = n
        }
        for (k, v) in Self.fixed where q[k] != v {
            throw ParameterError(description: "--candidate-loop-adaptive: LoopAdaptive implements \(k) = \(v) only (got \(q[k]!)); run adaptive.py through --candidate-external-controller for other forms")
        }
        var p = AdaptiveParameters()
        p.target = q["target"]!; p.lowStop = q["t_low"]!; p.bolusThreshold = q["t_bolus"]!
        p.momentumMinutes = q["h"]!; p.slopeCap = q["slope_cap"]!; p.riseCap = q["rise_cap"]!
        p.applicationFactor = q["af"]!; p.fallGate = q["fall_gate"]!; p.tempFloor = q["temp_floor_bg"]!
        p.targetMinimum = q["target_min"]!
        p.isfK = q["isf_k"]!; p.isfExponent = q["isf_e"]!; p.carbRatioK = q["cr_k"]!; p.insulinPeak = q["peak"]!
        p.retrospectiveGain = q["rc_k"]!; p.retrospectiveCap = q["rc_cap"]!
        p.adaptRate = q["ad_k"]!; p.adaptLowThreshold = q["ad_lo"]!; p.adaptLowMultiplier = q["ad_klo"]!
        p.adaptMinimum = q["ad_min"]!; p.adaptMaximum = q["ad_max"]!; p.adaptBrakeHours = q["ad_brake_h"]!
        p.adaptEnabled = q["ad_sp"]! > 0
        p.glucoseSafetyLimit = q["gsl"]!; p.glucoseSafetyLimitFromSettings = q["gsl_settings"]! != 0
        p.glucoseSafetyHorizon = q["gsl_h"]!
        p.habitGain = q["hab_k"]!; p.habitSkillReference = q["hab_ref"]!
        p.habitDays = Int(q["hab_days"]!); p.habitMinimumDays = Int(q["hab_min_days"]!)
        p.habitSkillHalfLifeDays = q["hab_hl"]!; p.habitLow = q["hab_lo"]!; p.habitHigh = q["hab_hi"]!
        parameters = p
        let tdd = q["tdd"]!
        profile = AdaptiveProfile(totalDailyDose: tdd,
                                  basalRate: q["basal_uh"]! > 0 ? q["basal_uh"]! : q["basal_frac"]! * tdd / 24,
                                  setPoint: q["ad_sp"]!)
        useTarget = q["use_target"]! != 0; useOverride = q["use_override"]! != 0; ownManual = q["own_manual"]! != 0
    }

    func decide(_ req: EngineStepRequest) -> (bolus: Double, tempRate: Double, manualRec: Double?) {
        let mg = LoopUnit.milligramsPerDeciliter
        let t = req.t
        func at<T>(_ s: [AbsoluteScheduleValue<T>]) -> T? {
            s.first(where: { $0.startDate <= t && $0.endDate > t })?.value ?? s.last(where: { $0.startDate <= t })?.value
        }
        var userTarget: ClosedRange<Double>? = nil
        if useTarget, let r = at(req.therapy.rawTarget.isEmpty ? req.therapy.target : req.therapy.rawTarget) {
            userTarget = r.lowerBound.doubleValue(for: mg)...r.upperBound.doubleValue(for: mg)
        }
        var override: AdaptiveOverride? = nil
        if useOverride, let w = OverrideWindow.resolved(req.therapy.overrideWindows, at: t).last(where: { $0.start <= t && t < $0.end }) {
            var range: ClosedRange<Double>? = nil
            if let lo = w.targetLo, let hi = w.targetHi { range = min(lo, hi)...max(lo, hi) }
            override = AdaptiveOverride(targetRange: range, insulinNeedsFactor: w.factor)
        }
        let input = AdaptiveInput(
            now: t,
            glucose: req.input.glucose.map { AdaptiveGlucoseSample(date: $0.startDate, value: $0.quantity.doubleValue(for: mg)) },
            doses: req.input.doses.map {
                AdaptiveDose(start: $0.startDate, end: $0.endDate, units: $0.volume,
                             kind: $0.deliveryType == .bolus ? .bolus : .basal, automatic: $0.automatic)
            },
            carbs: req.input.carbs.map {
                AdaptiveCarbEntry(date: $0.startDate, grams: $0.quantity.doubleValue(for: .gram), absorptionTime: $0.absorptionTime)
            },
            limits: AdaptiveLimits(maximumBolus: req.therapy.maxBolus(at: t), bolusIncrement: req.config.bolusIncrement,
                                   suspendThreshold: req.therapy.suspendThreshold(at: t)?.doubleValue(for: mg)),
            userTarget: userTarget, override: override)
        let r = LoopAdaptive.recommend(input, profile: profile, state: &state, parameters: parameters)
        return (r.automaticBolus, r.tempBasalRate, ownManual ? r.manualBolus : nil)
    }
}
