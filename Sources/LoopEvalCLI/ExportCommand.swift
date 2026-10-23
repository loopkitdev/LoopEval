// ExportCommand.swift — `loop-eval export` subcommand
//
// Writes a Nightscout site's four EvalCore streams (glucose / doses / carbs / therapy JSON) into a data
// directory, through the SAME NightscoutEvalDataSource conversion `simulate --nightscout-url` replays, so a
// site's `--data-dir` export and its live replay cannot drift apart. The per-donor side files the ICE
// pipeline and the additive templates also need (decision times, disruptions, Loop's IOB, bolus decisions,
// time zone, the labelled schedule fill) are added on top by analysis/loopeval_analysis/nightscout_export.py.

import ArgumentParser
import EvalCore
import Foundation
import LoopAlgorithm

@available(macOS 10.15, macCatalyst 13, iOS 13, tvOS 13, watchOS 6, *)
struct ExportCommand: AsyncParsableCommand {

    static let configuration = CommandConfiguration(
        commandName: "export",
        abstract: "Write a Nightscout site's glucose/doses/carbs/therapy JSON into a --data-dir directory."
    )

    @Option(name: .long, help: "Nightscout base URL (e.g. https://mysite.nightscout.io)")
    var nightscoutUrl: String

    @Option(name: .long, help: "Start date — ISO8601, e.g. 2026-01-01")
    var start: String

    @Option(name: .long, help: "End date   — ISO8601, e.g. 2026-01-08")
    var end: String

    @Option(name: .long, help: "Output directory (receives glucose.json, doses.json, carbs.json, therapy.json)")
    var outDir: String

    @Option(name: .long, help: "Nightscout API secret (optional)")
    var apiSecret: String?

    @Option(name: .long, help: "Nightscout subject access token (optional; for ?token= role auth)")
    var token: String?

    @Option(name: .long, help: "Cache directory", transform: URL.init(fileURLWithPath:))
    var cacheDir: URL = URL(fileURLWithPath: NSHomeDirectory()).appendingPathComponent(".loop-eval/cache")

    @Option(name: .long, help: "Insulin model: rapidActingAdult | rapidActingChild | fiasp | lyumjev | afrezza")
    var insulinType: String = "rapidActingAdult"

    @Flag(name: .long, inversion: .prefixedNo,
          help: "Apply Loop Temporary Overrides to the therapy timeline (as simulate does by default).")
    var applyOverrides: Bool = true

    mutating func run() async throws {
        let startDate = try parseISO8601Date(start)
        let endDate = try parseISO8601Date(end)
        guard endDate > startDate else { throw ValidationError("--end must be after --start") }
        let interval = DateInterval(start: startDate, end: endDate)
        guard let baseURL = URL(string: nightscoutUrl) else { throw ValidationError("Invalid Nightscout URL") }

        let preset = try parseInsulinType(insulinType)
        let client = NightscoutClient(baseURL: baseURL, apiSecret: apiSecret, token: token)
        let cache = try DataCache(cacheDir: cacheDir)
        let source = NightscoutEvalDataSource(client: client, cache: cache, insulinType: preset,
                                              applyOverrides: applyOverrides)

        // Each stream is restricted to the window the way JSONFileDataSource reads it back; doses keep the
        // data source's own 2-h lookback so a temp running at the window start is complete.
        let glucose = try await source.getGlucoseValues(interval: interval)
        let doses = try await source.getDoses(interval: interval)
        let carbs = try await source.getCarbEntries(interval: interval)
        let therapy = try await source.getTherapyTimeline(interval: interval)

        let out = URL(fileURLWithPath: outDir)
        try FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)
        // milliseconds kept, as the Tidepool exports carry them (.iso8601 drops fractional seconds)
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .custom { date, enc in
            let iso = ISO8601DateFormatter()
            iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            var c = enc.singleValueContainer(); try c.encode(iso.string(from: date))
        }
        try encoder.encode(glucose).write(to: out.appendingPathComponent("glucose.json"), options: .atomic)
        try encoder.encode(doses).write(to: out.appendingPathComponent("doses.json"), options: .atomic)
        try encoder.encode(carbs).write(to: out.appendingPathComponent("carbs.json"), options: .atomic)
        try encoder.encode(therapy).write(to: out.appendingPathComponent("therapy.json"), options: .atomic)
        print("exported glucose \(glucose.count), doses \(doses.count), carbs \(carbs.count) -> \(out.path)")
    }
}
