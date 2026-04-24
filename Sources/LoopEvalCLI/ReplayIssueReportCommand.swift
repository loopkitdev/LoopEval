// ReplayIssueReportCommand.swift — `loop-eval replay-issue-report`
//
// Reads a JSON bundle produced by scripts/parse_issue_report.py (which parses
// Loop's Issue Report .md file), runs LoopAlgorithm.generatePrediction on the
// exact inputs Loop saw, and emits a side-by-side diff vs the outputs Loop
// stored in the report. The one-shot apples-to-apples comparison.

import ArgumentParser
import EvalCore
import Foundation
import LoopAlgorithm

@available(macOS 10.15, macCatalyst 13, iOS 13, tvOS 13, watchOS 6, *)
struct ReplayIssueReportCommand: AsyncParsableCommand {

    static let configuration = CommandConfiguration(
        commandName: "replay-issue-report",
        abstract: "Replay a single Loop decision from an Issue Report JSON bundle and diff the result."
    )

    @Option(name: .long, help: "JSON bundle from parse_issue_report.py")
    var bundle: String

    @Option(name: .long, help: "Where to write the diff report (default: stdout)")
    var out: String?

    mutating func run() async throws {
        let url = URL(fileURLWithPath: bundle)
        let data = try Data(contentsOf: url)
        let b = try JSONDecoder().decode(IssueBundle.self, from: data)

        let anchor = try parseISO8601Date(b.forecast_start)
        let tz = TimeZone(secondsFromGMT: b.settings.timezone_seconds) ?? TimeZone(identifier: "UTC")!
        printStderr("Replaying forecast at \(b.forecast_start) (\(tz.identifier) offset \(b.settings.timezone_seconds)s)\n")
        printStderr("  Glucose samples: \(b.glucose.count)\n")
        printStderr("  Doses: \(b.doses.count)\n")

        // ── Build inputs ────────────────────────────────────────────────────
        let glucoseHistory: [EvalGlucoseSample] = b.glucose.map { g in
            let d = Self.parseIso(g.startDate)
            return EvalGlucoseSample(
                startDate: d,
                quantity: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: g.value),
                provenanceIdentifier: "replay",
                isDisplayOnly: g.isDisplayOnly,
                wasUserEntered: false
            )
        }.sorted { $0.startDate < $1.startDate }

        // Convert doses. For temp basal: `value` is U/hr, duration from endDate-startDate.
        // For bolus: `value` IS the volume.
        let insulinType: ExponentialInsulinModelPreset = .rapidActingAdult
        let doses: [EvalInsulinDose] = b.doses.map { d -> EvalInsulinDose in
            let start = Self.parseIso(d.startDate)
            let end = Self.parseIso(d.endDate)
            let volume: Double
            let deliveryType: InsulinDeliveryType
            if d.type == "tempBasal" {
                deliveryType = .basal
                // Prefer the pump-reported `deliveredUnits` (actual amount that
                // reached the tissue) over `value × duration` (the programmed
                // nominal) — short-duration temps are frequently interrupted
                // and pre-extraction Loop uses deliveredUnits.
                if let delivered = d.deliveredUnits {
                    volume = delivered
                } else {
                    let durHours = end.timeIntervalSince(start) / 3600.0
                    volume = d.value * durHours
                }
            } else {
                deliveryType = .bolus
                volume = d.deliveredUnits ?? d.value
            }
            return EvalInsulinDose(
                deliveryType: deliveryType,
                startDate: start,
                endDate: end,
                volume: volume,
                insulinType: insulinType,
                automatic: d.automatic
            )
        }.sorted { $0.startDate < $1.startDate }

        // Schedule expansion window must cover all doses + 8h forward for ISF coverage.
        let earliestDose = doses.first?.startDate ?? anchor.addingTimeInterval(-16 * 3600)
        let scheduleStart = min(earliestDose.addingTimeInterval(-1 * 3600), anchor.addingTimeInterval(-18 * 3600))
        let scheduleEnd = anchor.addingTimeInterval(8 * 3600)
        let interval = DateInterval(start: scheduleStart, end: scheduleEnd)

        let basal = expandDailySchedule(
            items: b.settings.basal.map { (timeAsSeconds: $0.time_seconds, value: $0.value) },
            timeZone: tz, interval: interval
        )
        let sensitivity: [AbsoluteScheduleValue<LoopQuantity>] = expandDailySchedule(
            items: b.settings.sensitivity.map { (timeAsSeconds: $0.time_seconds, value: $0.value) },
            timeZone: tz, interval: interval
        ).map {
            AbsoluteScheduleValue(
                startDate: $0.startDate, endDate: $0.endDate,
                value: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: $0.value)
            )
        }
        let carbRatio = expandDailySchedule(
            items: b.settings.carbRatio.map { (timeAsSeconds: $0.time_seconds, value: $0.value) },
            timeZone: tz, interval: interval
        )

        // ── Run generatePrediction ─────────────────────────────────────────
        let emptyCarbs: [EvalCarbEntry] = []
        let useIntegralRC = b.integralRetrospectiveCorrectionEnabled
        printStderr("  Integral RC: \(useIntegralRC ? "ON" : "OFF")\n")
        let prediction = LoopAlgorithm.generatePrediction(
            start: anchor,
            glucoseHistory: glucoseHistory,
            doses: doses,
            carbEntries: emptyCarbs,
            basal: basal,
            sensitivity: sensitivity,
            carbRatio: carbRatio,
            algorithmEffectsOptions: .all,
            useIntegralRetrospectiveCorrection: useIntegralRC,
            includingPositiveVelocityAndRC: true,
            useMidAbsorptionISF: false
        )

        // ── Build diff report ──────────────────────────────────────────────
        var report = ""
        report += String(repeating: "=", count: 80) + "\n"
        report += " REPLAY DIFF — Loop (pump) vs LoopAlgorithm@HEAD\n"
        report += String(repeating: "=", count: 80) + "\n"
        report += "Source:            \(b.source_report)\n"
        report += "Forecast anchor:   \(b.forecast_start)  starting BG \(b.current_bg)\n\n"

        // IOB
        let expectedIOB = b.expected.insulinOnBoard
        let ourIOB = prediction.activeInsulin ?? 0
        report += "SCALARS\n"
        report += String(repeating: "-", count: 80) + "\n"
        report += diffRow("IOB (U)", expected: expectedIOB, actual: ourIOB, decimals: 4) + "\n\n"

        // Predicted glucose curve
        report += "PREDICTED GLUCOSE  (first 25 points — Loop vs Loop-now, Δ = now − pump)\n"
        report += String(repeating: "-", count: 80) + "\n"
        report += compareSeries(
            expected: b.expected.predictedGlucose,
            actual: prediction.glucose.map {
                ExpectedPoint(startDate: Self.iso($0.startDate),
                              value: $0.quantity.doubleValue(for: .milligramsPerDeciliter))
            },
            limit: 25,
            decimals: 2
        )

        // Insulin effect
        report += "\nINSULIN EFFECT  (first 25 points)\n"
        report += String(repeating: "-", count: 80) + "\n"
        report += compareSeries(
            expected: b.expected.insulinEffect,
            actual: prediction.effects.insulin.map {
                ExpectedPoint(startDate: Self.iso($0.startDate),
                              value: $0.quantity.doubleValue(for: .milligramsPerDeciliter))
            },
            limit: 25,
            decimals: 3
        )

        // Momentum
        report += "\nMOMENTUM EFFECT\n"
        report += String(repeating: "-", count: 80) + "\n"
        report += compareSeries(
            expected: b.expected.glucoseMomentumEffect,
            actual: prediction.effects.momentum.map {
                ExpectedPoint(startDate: Self.iso($0.startDate),
                              value: $0.quantity.doubleValue(for: .milligramsPerDeciliter))
            },
            limit: 10,
            decimals: 4
        )

        // RC effect
        report += "\nRETROSPECTIVE CORRECTION EFFECT  (first 25 points)\n"
        report += String(repeating: "-", count: 80) + "\n"
        report += compareSeries(
            expected: b.expected.retrospectiveGlucoseEffect,
            actual: prediction.effects.retrospectiveCorrection.map {
                ExpectedPoint(startDate: Self.iso($0.startDate),
                              value: $0.quantity.doubleValue(for: .milligramsPerDeciliter))
            },
            limit: 25,
            decimals: 3
        )

        report += "\n" + String(repeating: "=", count: 80) + "\n"

        if let out {
            try report.write(toFile: out, atomically: true, encoding: .utf8)
            printStderr("Wrote diff report → \(out)\n")
        } else {
            print(report)
        }
    }

    // MARK: – Helpers

    private static func makeIsoFormatter() -> ISO8601DateFormatter {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }

    private static func parseIso(_ s: String) -> Date {
        makeIsoFormatter().date(from: s) ?? Date(timeIntervalSince1970: 0)
    }

    private static func iso(_ d: Date) -> String {
        makeIsoFormatter().string(from: d)
    }

    private func diffRow(_ label: String, expected: Double, actual: Double, decimals: Int) -> String {
        let delta = actual - expected
        let marker = abs(delta) < 0.0001 ? "✓" : (abs(delta) < 0.01 ? "~" : "✗")
        let padLabel = pad(label, 20)
        let eStr = String(format: "%.\(decimals)f", expected)
        let aStr = String(format: "%.\(decimals)f", actual)
        let dStr = String(format: "%+.5f", delta)
        return " \(marker) \(padLabel)  expected=\(eStr)  actual=\(aStr)  Δ=\(dStr)"
    }

    private func compareSeries(
        expected: [ExpectedPoint],
        actual: [ExpectedPoint],
        limit: Int,
        decimals: Int
    ) -> String {
        var s = ""
        s += " \(pad("t", 22))\(pad("expected", 14))\(pad("actual", 14))Δ\n"
        let count = min(limit, max(expected.count, actual.count))
        // Index both by startDate for matching.
        var actualByDate = [String: Double]()
        for p in actual { actualByDate[p.startDate] = p.value }

        var totalAbs = 0.0
        var matched = 0
        for i in 0..<count {
            guard i < expected.count else { break }
            let e = expected[i]
            let aVal = actualByDate[e.startDate]
            let eStr = String(format: "%.\(decimals)f", e.value)
            let aStr = aVal.map { String(format: "%.\(decimals)f", $0) } ?? "—"
            let dStr = aVal.map { String(format: "%+.\(decimals)f", $0 - e.value) } ?? "—"
            if let a = aVal {
                totalAbs += abs(a - e.value)
                matched += 1
            }
            s += " \(pad(e.startDate, 22))\(pad(eStr, 14))\(pad(aStr, 14))\(dStr)\n"
        }

        // Aggregate across the full series (not just the shown slice).
        var fullAbs = 0.0
        var fullMatched = 0
        var maxDev = 0.0
        for e in expected {
            if let a = actualByDate[e.startDate] {
                let d = abs(a - e.value)
                fullAbs += d
                if d > maxDev { maxDev = d }
                fullMatched += 1
            }
        }
        if fullMatched > 0 {
            s += String(format: " ── aggregate across %d matched points: mean |Δ| = %.4f, max |Δ| = %.4f\n",
                        fullMatched, fullAbs / Double(fullMatched), maxDev)
        } else {
            s += " ── no matched points (likely timestamp mismatch)\n"
        }
        return s
    }

    private func pad(_ s: String, _ width: Int) -> String {
        s.count >= width ? s : s + String(repeating: " ", count: width - s.count)
    }
}

// MARK: – JSON bundle types

private struct ExpectedPoint: Codable {
    let startDate: String
    let value: Double
}

private struct IssueBundle: Codable {
    let source_report: String
    let forecast_start: String
    let current_bg: Double
    let integralRetrospectiveCorrectionEnabled: Bool
    let glucose: [GlucoseSample]
    let doses: [Dose]
    let settings: Settings
    let expected: Expected

    struct GlucoseSample: Codable {
        let startDate: String
        let value: Double
        let isDisplayOnly: Bool
    }

    struct Dose: Codable {
        let type: String     // "bolus" | "tempBasal"
        let startDate: String
        let endDate: String
        let value: Double
        let unit: String     // "units" | "unitsPerHour"
        let deliveredUnits: Double?
        let automatic: Bool
    }

    struct Settings: Codable {
        let basal: [Segment]
        let sensitivity: [Segment]
        let carbRatio: [Segment]
        let target: [TargetSegment]
        let suspendThreshold: Double?
        let maxBolus: Double?
        let maxBasalRate: Double?
        let insulinModel: InsulinModelParams
        let timezone_seconds: Int
    }

    struct Segment: Codable {
        let time_seconds: Int
        let value: Double
    }

    struct TargetSegment: Codable {
        let time_seconds: Int
        let min: Double
        let max: Double
    }

    struct InsulinModelParams: Codable {
        let actionDuration: Double
        let peakActivityTime: Double
        let delay: Double
    }

    struct Expected: Codable {
        let insulinOnBoard: Double
        let predictedGlucose: [ExpectedPoint]
        let insulinEffect: [ExpectedPoint]
        let carbEffect: [ExpectedPoint]
        let glucoseMomentumEffect: [ExpectedPoint]
        let retrospectiveGlucoseEffect: [ExpectedPoint]
    }
}
