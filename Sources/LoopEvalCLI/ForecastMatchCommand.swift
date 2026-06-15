// ForecastMatchCommand.swift — `loop-eval forecast-match` subcommand
//
// Evaluate Loop's decision-time forecast + dose recommendation at an EXPLICIT list
// of timestamps (the field's real Loop decision times, from devicestatus), on the
// raw native CGM history — no uniform grid, no Kalman resampling. This lets us
// compare the sim's forecast curve and dose against devicestatus.predicted.values /
// automaticDoseRecommendation at the SAME instant the real Loop decided, removing
// the ~5-min grid phase offset that otherwise floors the comparison at ~1.5 mg/dL.

import ArgumentParser
import EvalCore
import Foundation

@available(macOS 10.15, macCatalyst 13, iOS 13, tvOS 13, watchOS 6, *)
struct ForecastMatchCommand: AsyncParsableCommand {

    static let configuration = CommandConfiguration(
        commandName: "forecast-match",
        abstract: "Evaluate the decision-time forecast + dose at explicit timestamps (field decision times) for bit-level comparison against devicestatus."
    )

    @Option(name: .long, help: "Nightscout base URL")
    var nightscoutUrl: String

    @Option(name: .long, help: "Data window start (ISO8601). Must be >= ~16h before the earliest evaluated time so the insulin/glucose history is complete.")
    var start: String

    @Option(name: .long, help: "Data window end (ISO8601).")
    var end: String

    @Option(name: .long, help: "CSV file with one ISO8601 timestamp per line (header 't' optional) — the times to evaluate at (the field's decision times).")
    var timesCsv: String

    @Option(name: .long, help: "Output JSON path.")
    var out: String

    @Option(name: .long, help: "Nightscout API secret (optional)")
    var apiSecret: String?

    @Option(name: .long, help: "Cache directory for fetched Nightscout data",
            transform: URL.init(fileURLWithPath:))
    var cacheDir: URL = URL(fileURLWithPath: NSHomeDirectory()).appendingPathComponent(".loop-eval/cache")

    @Option(name: .long, help: "Insulin model (default rapidActingAdult)")
    var insulinType: String = "rapidActingAdult"

    @Flag(name: .long, help: "Use integral retrospective correction (default: standard RC).")
    var integralRC: Bool = false

    @Option(name: .long, help: "Auto-bolus application factor (default 0.4).")
    var applicationFactor: Double = 0.4

    @Option(name: .long, help: "ISF multiplier (default 1.0).")
    var sensitivityMultiplier: Double = 1.0

    // Momentum knobs (for Loop-3.9.3-compatibility experiments). Defaults = LoopAlgorithm.
    @Option(name: .long, help: "Momentum projection duration (minutes). Default 15 (LoopAlgorithm). Loop 3.9.3 used 30.")
    var momentumDurationMin: Double = 15

    @Option(name: .long, help: "Momentum velocity cap (mg/dL/min). Default 4.0 (LoopAlgorithm/LoopKit since 2020). Pass a large value (e.g. 1000) to disable.")
    var momentumCap: Double = 4.0

    @Flag(name: .long, help: "Disable the gradual-transitions gate (>40 mg/dL jump suppresses momentum). The gate is a LoopAlgorithm addition NOT in Loop 3.9.3 — pass this to match 3.9.3.")
    var noGradualTransitionsGate: Bool = false

    @Flag(name: .long, help: "Convenience: Loop-3.9.3-compatible momentum = disable the gradual-transitions gate only. (Verified from LoopKit dev source: deployed Loop uses 15-min duration + 4 mg/dL/min cap — same as default — and NO gradual-transitions gate.)")
    var loop393Momentum: Bool = false

    struct OutRow: Codable {
        let t: String
        let eventualBG: Double?
        let iob: Double?
        let cob: Double?
        let recommendedBolus: Double?      // auto-bolus this cycle (app factor + floor)
        let recommendedDeltaU: Double?
        let recommendedTempBasalRate: Double?
        let curve: [Double]                // full forecast curve, mg/dL, 5-min spaced from t
    }

    mutating func run() async throws {
        let startDate = try parseISO8601Date(start)
        let endDate   = try parseISO8601Date(end)
        guard endDate > startDate else { throw ValidationError("--end must be after --start") }
        let interval = DateInterval(start: startDate, end: endDate)
        let preset = try parseInsulinType(insulinType)

        // Read the timestamp list.
        let raw = try String(contentsOfFile: timesCsv, encoding: .utf8)
        var times: [Date] = []
        for line in raw.split(whereSeparator: { $0 == "\n" || $0 == "\r" }) {
            let s = line.trimmingCharacters(in: .whitespaces)
            if s.isEmpty || s.lowercased() == "t" { continue }
            let field = s.split(separator: ",").first.map(String.init) ?? s
            if let d = try? parseISO8601Date(field) { times.append(d) }
        }
        times = times.filter { $0 >= startDate && $0 <= endDate }.sorted()
        printStderr("Evaluating at \(times.count) timestamps\n")

        let durMin = momentumDurationMin   // deployed Loop = 15 (LoopKit dev momentumDuration); 30 only in stale master
        let gateThreshold: Double? = (loop393Momentum || noGradualTransitionsGate) ? nil : 40
        let config = EvalConfig(
            applicationFactor: applicationFactor,
            includeFutureInsulin: false,   // decision-time replay
            includeFutureCarbs: false,
            useIntegralRC: integralRC,
            kalmanSmoothing: false,        // raw native CGM (evaluate path uses data.glucose directly)
            sensitivityMultiplier: sensitivityMultiplier,
            positiveVelocityCap: momentumCap,
            momentumProjectionMinutes: durMin,
            momentumGradualTransitionsThreshold: gateThreshold
        )
        printStderr("momentum: duration=\(durMin)min cap=\(momentumCap)mg/dL/min gate=\(gateThreshold.map { "\($0)" } ?? "OFF")\n")

        guard let baseURL = URL(string: nightscoutUrl) else {
            throw ValidationError("Invalid Nightscout URL: \(nightscoutUrl)")
        }
        let client = NightscoutClient(baseURL: baseURL, apiSecret: apiSecret)
        let cache  = try DataCache(cacheDir: cacheDir)
        let dataSource = NightscoutEvalDataSource(client: client, cache: cache, insulinType: preset)
        let engine = EvaluationEngine(dataSource: dataSource)

        printStderr("Fetching data...\n")
        let data = try await engine.prefetchData(for: interval, config: config)

        let records = engine.forecastAtTimes(times, data: data, interval: interval, config: config)
        printStderr("Got \(records.count) forecast records\n")

        let mgdl = LoopUnit.milligramsPerDeciliter
        let fmt = ISO8601DateFormatter()
        fmt.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let rows = records.map { r in
            OutRow(
                t: fmt.string(from: r.evaluatedAt),
                eventualBG: r.predicted.last?.quantity.doubleValue(for: mgdl),
                iob: r.iob,
                cob: r.cob,
                recommendedBolus: r.recommendedBolus,
                recommendedDeltaU: r.recommendedDeltaU,
                recommendedTempBasalRate: r.recommendedTempBasalRate,
                curve: r.predicted.map { $0.quantity.doubleValue(for: mgdl) }
            )
        }
        let enc = JSONEncoder()
        enc.outputFormatting = [.prettyPrinted]
        let json = try enc.encode(rows)
        try json.write(to: URL(fileURLWithPath: out))
        printStderr("Wrote \(rows.count) rows → \(out)\n")
    }
}
