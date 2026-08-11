// DoseFromForecastCommand.swift — harness: run LoopAlgorithm's insulinCorrection +
// recommendAutomaticDose on a GIVEN forecast curve. Lets us feed Loop's EXACT recorded
// bgForecast (dosingDecision) into the byte-equivalent dosing logic and see what dose it
// yields — isolating "does the recorded forecast produce the recorded dose?" from any
// forecast-reconstruction question.
import ArgumentParser
import Foundation
import LoopAlgorithm

struct DoseFromForecastCommand: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "dose-from-forecast",
        abstract: "Run insulinCorrection + recommendAutomaticDose on a forecast curve (mg/dL, 5-min spaced).")

    @Option(name: .long, help: "JSON: {curve:[mgdl...], isf, targetLow, targetHigh, suspend, iob, appFactor, scheduledBasal, maxBolus, maxBasalRate}")
    var input: String

    struct Params: Codable {
        var curve: [Double]
        var isf: Double
        var targetLow: Double
        var targetHigh: Double
        var suspend: Double
        var iob: Double
        var appFactor: Double
        var scheduledBasal: Double
        var maxBolus: Double
        var maxBasalRate: Double
    }

    func run() async throws {
        let p = try JSONDecoder().decode(Params.self, from: Data(contentsOf: URL(fileURLWithPath: input)))
        let u = LoopUnit.milligramsPerDeciliter
        let t0 = Date(timeIntervalSinceReferenceDate: 0)
        func q(_ v: Double) -> LoopQuantity { LoopQuantity(unit: u, doubleValue: v) }

        let pred = p.curve.enumerated().map {
            PredictedGlucoseValue(startDate: t0.addingTimeInterval(Double($0.offset) * 300), quantity: q($0.element))
        }
        let hiEnd = t0.addingTimeInterval(Double(p.curve.count) * 300 + 7200)
        let target: GlucoseRangeTimeline = [AbsoluteScheduleValue(
            startDate: t0.addingTimeInterval(-3600), endDate: hiEnd, value: q(p.targetLow)...q(p.targetHigh))]
        let sens = [AbsoluteScheduleValue(startDate: t0.addingTimeInterval(-3600), endDate: hiEnd, value: q(p.isf))]
        let model = ExponentialInsulinModelPreset.rapidActingAdult.model

        let correction = LoopAlgorithm.insulinCorrection(
            prediction: pred, at: pred[0].startDate, target: target,
            suspendThreshold: q(p.suspend), sensitivity: sens, insulinModel: model)

        let rec = LoopAlgorithm.recommendAutomaticDose(
            for: correction, applicationFactor: p.appFactor, neutralBasalRate: p.scheduledBasal,
            activeInsulin: p.iob, maxBolus: p.maxBolus, maxBasalRate: p.maxBasalRate,
            maxActiveInsulin: p.maxBolus * 2)

        var cdesc = "inRange"
        switch correction {
        case .aboveRange(let mn, let cor, let mt, let un):
            cdesc = "aboveRange min=\(Int(mn.quantity.doubleValue(for: u))) correcting=\(Int(cor.quantity.doubleValue(for: u))) minTarget=\(Int(mt.doubleValue(for: u))) fullUnits=\(String(format: "%.3f", un))"
        case .entirelyBelowRange(let mn, _, let un):
            cdesc = "belowRange min=\(Int(mn.quantity.doubleValue(for: u))) units=\(String(format: "%.3f", un))"
        case .suspend(let mn): cdesc = "suspend min=\(Int(mn.quantity.doubleValue(for: u)))"
        case .inRange: cdesc = "inRange"
        }
        print("curve: n=\(p.curve.count) first=\(Int(p.curve.first ?? 0)) min=\(Int(p.curve.min() ?? 0)) eventual=\(Int(p.curve.last ?? 0))")
        print("correction: \(cdesc)")
        print("→ bolus = \(String(format: "%.3f", rec.bolusUnits ?? 0))   tempRate = \(String(format: "%.3f", rec.basalAdjustment.unitsPerHour))   (appFactor \(p.appFactor))")
    }
}
