// DumpInputsCommand.swift — export per-cycle decision-time LoopPredictionInput JSONs
// for cross-harness replay (e.g. running the identical inputs through an upstream
// LoopAlgorithm build). One JSON per CGM-triggered decision time in the window,
// named input_<ISO8601>.json in --out-dir.

import ArgumentParser
import Foundation
import EvalCore

struct DumpInputsCommand: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "dump-inputs",
        abstract: "Export per-cycle decision-time algorithm inputs (fixture JSON) for cross-harness replay."
    )

    @Option(name: .long, help: "EvalCore data dir (glucose/doses/carbs/therapy JSONs).")
    var dataDir: String

    @Option(name: .long, help: "Window start (ISO8601).")
    var start: String

    @Option(name: .long, help: "Window end (ISO8601).")
    var end: String

    @Option(name: .long, help: "Output directory for input_<ISO>.json files.")
    var outDir: String

    @Option(name: .long, help: "Glucose lookback hours (default 24).")
    var glucoseLookbackHours: Double = 24

    @Option(name: .long, help: "Insulin lookback hours (default 24).")
    var insulinLookbackHours: Double = 24

    @Option(name: .long, help: "insulinType raw value stamped on exported doses (LoopKit raw: novolog=0). Default 0.")
    var insulinTypeRaw: Int = 0

    mutating func run() async throws {
        let startDate = try parseISO8601Date(start)
        let endDate = try parseISO8601Date(end)
        guard endDate > startDate else { throw ValidationError("--end must be after --start") }
        let interval = DateInterval(start: startDate, end: endDate)

        var config = EvalConfig()
        config.glucoseLookbackHours = glucoseLookbackHours
        config.insulinLookbackHours = insulinLookbackHours

        let dataSource = JSONFileDataSource(baseURL: URL(fileURLWithPath: dataDir))
        let engine = EvaluationEngine(dataSource: dataSource)
        let data = try await engine.prefetchData(for: interval, config: config)

        // Trigger model: one automatic dosing decision per new CGM reading.
        let times = data.glucose.map(\.startDate)
            .filter { $0 >= startDate && $0 < endDate }
            .sorted()

        try FileManager.default.createDirectory(
            atPath: outDir, withIntermediateDirectories: true)
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime]

        var written = 0, skipped = 0
        for t in times {
            guard let json = engine.loopPredictionInputJSON(
                at: t, data: data, config: config,
                insulinTypeRaw: insulinTypeRaw, useIntegralRC: false) else {
                skipped += 1; continue
            }
            let name = "input_" + iso.string(from: t)
                .replacingOccurrences(of: ":", with: "") + ".json"
            try json.write(to: URL(fileURLWithPath: outDir).appendingPathComponent(name))
            written += 1
        }
        printStderr("dump-inputs: \(written) cycles written, \(skipped) skipped → \(outDir)\n")
    }
}
