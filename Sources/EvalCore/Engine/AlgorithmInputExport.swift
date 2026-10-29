// AlgorithmInputExport.swift — the exact input behind one replayed decision, as a LoopAlgorithm
// AlgorithmInputFixture (JSON), so the shipped package can be run on precisely what LoopEval scored.
//
// The fixture fields are the package's own (LoopAlgorithm main, AlgorithmInputFixture + experiments /
// volatilityBaseline); a decoder ignores the extra `loopEval` block, which carries the engine's own
// answer for this cycle and everything in the engine config the fixture cannot express. A stock
// cycle whose `loopEval.nonDefaultConfig` is empty should reproduce the engine's dose and forecast.

import Foundation
import LoopAlgorithm

extension EvaluationEngine {

    /// EvalConfig keys the fixture expresses directly (or that do not reach the decision), so they are
    /// left out of `nonDefaultConfig`.
    private static let fixtureRepresentedKeys: Set<String> = [
        "useIntegralRC", "includingPositiveVelocityAndRC", "useMidAbsorptionISF", "carbAbsorptionModel",
        "applicationFactor", "useTempBasalStrategy", "momentumGradualTransitionsThreshold",
        "decisionTimesAreAuthoritative", "glucoseLookbackHours", "insulinLookbackHours", "evalStep",
        // input construction (the exported input already reflects them) and the manual-bolus path
        "carbRevisionsPath", "includeFutureInsulin", "includeFutureCarbs", "manualBolusFromRecommendation",
        "bolusIncrement", "tempBasalIncrement",
    ]
    /// The guard + runway arm (dr arm_flags("gr")): the package's `.guardAndRunway` experiment.
    private static let guardAndRunwayKeys: Set<String> = [
        "sigmaBandK", "sigmaBandCobGate", "postlowRcRiseScale", "postlowWindowMin",
        "runwayFraction", "runwayCobGate", "runwayBgMin",
    ]

    static func fixtureInsulinType(_ p: ExponentialInsulinModelPreset) -> String? {
        switch p {
        case .rapidActingAdult: return "rapidActingAdult"
        case .rapidActingChild: return "rapidActingChild"
        case .fiasp: return "fiasp"
        case .lyumjev: return "lyumjev"
        case .afrezza: return "afrezza"
        case .lateShort90dia4, .custom, .custom2: return nil
        }
    }

    /// EvalConfig keys whose value differs from a default EvalConfig() and which the fixture cannot carry.
    static func nonDefaultConfigKeys(_ config: EvalConfig, guardAndRunway: Bool) -> [String] {
        let enc = JSONEncoder()
        guard let a = try? enc.encode(config), let b = try? enc.encode(EvalConfig()),
              let da = (try? JSONSerialization.jsonObject(with: a)) as? [String: Any],
              let db = (try? JSONSerialization.jsonObject(with: b)) as? [String: Any] else { return ["<config not encodable>"] }
        var out: [String] = []
        for k in Set(da.keys).union(db.keys).sorted() where !fixtureRepresentedKeys.contains(k) {
            if guardAndRunway && guardAndRunwayKeys.contains(k) { continue }
            let x = da[k].map { "\($0)" } ?? "nil", y = db[k].map { "\($0)" } ?? "nil"
            if x != y { out.append("\(k)=\(x)") }
        }
        return out
    }

    /// One decision's AlgorithmInputFixture JSON. `input` is the input the forecast was generated from
    /// (effective sensitivity and target, before any runway target shift); doses are clipped at the
    /// prediction start, as the package requires of an automated recommendation.
    static func algorithmInputFixtureJSON(
        t: Date, predictionStart: Date, input: PredictionInput, config: EvalConfig, therapy: TherapyTimeline,
        applicationFactor: Double, prediction: LoopPrediction<EvalCarbEntry>,
        bolus: Double, tempRate: Double, deltaU: Double, tempAction: String
    ) -> Data? {
        let iso = ISO8601DateFormatter(); iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        func ds(_ d: Date) -> String { iso.string(from: d) }
        let mg = LoopUnit.milligramsPerDeciliter
        var notes: [String] = []

        let glucose: [[String: Any]] = input.glucose.map { g in
            var o: [String: Any] = ["date": ds(g.startDate), "value": g.quantity.doubleValue(for: mg)]
            if g.isDisplayOnly { o["isDisplayOnly"] = true }
            if g.wasUserEntered { o["wasUserEntered"] = true }
            return o
        }
        var clipped = 0, dropped = 0
        var doses: [[String: Any]] = []
        for d in input.doses {
            if d.startDate >= predictionStart && d.deliveryType == .basal { dropped += 1; continue }
            var end = d.endDate, vol = d.volume
            if d.deliveryType == .basal && end > predictionStart {
                let full = end.timeIntervalSince(d.startDate)
                vol = full > 0 ? d.volume * predictionStart.timeIntervalSince(d.startDate) / full : d.volume
                end = predictionStart; clipped += 1
            }
            var o: [String: Any] = ["type": d.deliveryType == .bolus ? "bolus" : "basal",
                                    "startDate": ds(d.startDate), "endDate": ds(end), "volume": vol]
            if let it = fixtureInsulinType(d.insulinType) { o["insulinType"] = it } else { notes.append("dose insulin model \(d.insulinType.rawValue)") }
            doses.append(o)
        }
        if clipped > 0 && !config.clipInProgressTempBasal {
            notes.append("engine projected an in-progress temp past the decision; the fixture clips it")
        }
        let carbs: [[String: Any]] = input.carbs.map { c in
            var o: [String: Any] = ["date": ds(c.startDate), "grams": c.quantity.doubleValue(for: .gram)]
            if let a = c.absorptionTime { o["absorptionTime"] = a }
            return o
        }
        func sched(_ s: [AbsoluteScheduleValue<Double>]) -> [[String: Any]] {
            s.map { ["startDate": ds($0.startDate), "endDate": ds($0.endDate), "value": $0.value] }
        }
        let sens: [[String: Any]] = input.sensitivity.map {
            ["startDate": ds($0.startDate), "endDate": ds($0.endDate), "value": $0.value.doubleValue(for: mg)]
        }
        let target: [[String: Any]] = input.target.map {
            ["startDate": ds($0.startDate), "endDate": ds($0.endDate),
             "lowerBound": $0.value.lowerBound.doubleValue(for: mg), "upperBound": $0.value.upperBound.doubleValue(for: mg)]
        }
        let preset = therapy.insulinType(at: t)
        let recIns = fixtureInsulinType(preset)
        if recIns == nil { notes.append("recommendation insulin model \(preset.rawValue)") }
        if config.momentumGradualTransitionsThreshold == nil {
            notes.append("gradual-transitions gate off: the fixture decoder reads a missing threshold as 40")
        }
        // Standing engine-vs-package differences, measured on 6 pilot donors x 3 days (2026-10-29): with these
        // the stock package reproduces the engine's forecast to 1e-9 mg/dL and every dose but these cases.
        if config.anchorsCorrectionAtFirstGlucose {
            notes.append("engine sizes the correction from the forecast's first point (the CGM reading); run() from predictionStart")
        }
        if config.bolusIncrement > 0 || config.tempBasalIncrement > 0 {
            notes.append("engine floors doses to the pump's increments (bolus \(config.bolusIncrement), temp \(config.tempBasalIncrement)); the package returns them unrounded")
        }
        let gr = config.sigmaBandK > 0 && config.sigmaBandCobGate && config.runwayFraction > 0
            && config.runwayCobGate && config.postlowRcRiseScale != 1
        var root: [String: Any] = [
            "predictionStart": ds(predictionStart),
            "glucoseHistory": glucose, "doses": doses, "carbEntries": carbs,
            "basal": sched(input.basal), "sensitivity": sens, "carbRatio": sched(input.carbRatio), "target": target,
            "maxBolus": therapy.maxBolus(at: t), "maxBasalRate": therapy.maxBasalRate(at: t),
            "useIntegralRetrospectiveCorrection": config.useIntegralRC,
            "includePositiveVelocityAndRC": config.includingPositiveVelocityAndRC,
            "useMidAbsorptionISF": config.useMidAbsorptionISF,
            "carbAbsorptionModel": config.carbAbsorptionModel.rawValue,
            "recommendationInsulinType": recIns ?? "rapidActingAdult",
            "recommendationType": config.useTempBasalStrategy ? "tempBasal" : "automaticBolus",
            "automaticBolusApplicationFactor": applicationFactor,
        ]
        if let s = therapy.suspendThreshold(at: t) { root["suspendThreshold"] = s.doubleValue(for: mg) }
        if let g = config.momentumGradualTransitionsThreshold { root["gradualTransitionsThreshold"] = g }
        if gr {
                root["experiments"] = ["guardAndRunway"]
            // The package's depth is min(1, 6.7 / baseline); a missing baseline is full depth.
            if config.sigmaBandK < 1 { root["volatilityBaseline"] = 6.7 / config.sigmaBandK }
        }
        let curve = prediction.glucose.map { $0.quantity.doubleValue(for: mg) }
        func num(_ x: Double?) -> Any { x.flatMap { $0.isFinite ? $0 : nil } ?? NSNull() }
        root["loopEval"] = [
            "decisionTime": ds(t),
            "engine": ["bolus": bolus, "tempRate": tempRate, "deltaU": deltaU, "tempAction": tempAction,
                       "eventualBG": num(curve.last), "minBG": num(curve.min()),
                       "iob": num(prediction.activeInsulin), "cob": num(prediction.activeCarbs)] as [String: Any],
            "dosesClippedAtPredictionStart": clipped, "basalDosesDroppedAfterPredictionStart": dropped,
            "nonDefaultConfig": nonDefaultConfigKeys(config, guardAndRunway: gr),
            "notes": notes,
        ] as [String: Any]
        return try? JSONSerialization.data(withJSONObject: root, options: [.sortedKeys])
    }
}
