// CacheCommand.swift — `loop-eval cache` subcommand

import ArgumentParser
import EvalCore
import Foundation

@available(macOS 10.15, macCatalyst 13, iOS 13, tvOS 13, watchOS 6, *)
struct CacheCommand: AsyncParsableCommand {

    static let configuration = CommandConfiguration(
        commandName: "cache",
        abstract: "Pre-fetch and cache Nightscout data for a date range."
    )

    // MARK: – Options

    @Option(name: .long, help: "Nightscout base URL (e.g. https://mysite.nightscout.io)")
    var nightscoutUrl: String

    @Option(name: .long, help: "Start date — ISO8601, e.g. 2026-01-01")
    var start: String

    @Option(name: .long, help: "End date   — ISO8601, e.g. 2026-01-08")
    var end: String

    @Option(name: .long, help: "Nightscout API secret (optional)")
    var apiSecret: String?

    @Option(name: .long, help: "Cache directory",
            transform: URL.init(fileURLWithPath:))
    var cacheDir: URL = URL(fileURLWithPath: NSHomeDirectory())
        .appendingPathComponent(".loop-eval/cache")

    @Option(name: .long,
            help: "Insulin model: rapidActingAdult | rapidActingChild | fiasp | lyumjev | afrezza")
    var insulinType: String = "rapidActingAdult"

    // MARK: – Run

    mutating func run() async throws {

        // Parse dates
        let startDate = try parseISO8601Date(start)
        let endDate   = try parseISO8601Date(end)
        guard endDate > startDate else {
            throw ValidationError("--end must be after --start")
        }

        let interval = DateInterval(start: startDate, end: endDate)
        let days = interval.duration / 86400
        let daysStr = String(format: "%.1f", days)

        // Parse insulin type
        let preset = try parseInsulinType(insulinType)

        // Build data source
        guard let baseURL = URL(string: nightscoutUrl) else {
            throw ValidationError("Invalid Nightscout URL: \(nightscoutUrl)")
        }
        let client     = NightscoutClient(baseURL: baseURL, apiSecret: apiSecret)
        let cache      = try DataCache(cacheDir: cacheDir)
        let dataSource = NightscoutEvalDataSource(
            client: client,
            cache: cache,
            insulinType: preset
        )

        print("Caching Nightscout data for \(daysStr) days …")
        print("  URL:   \(nightscoutUrl)")
        print("  Range: \(formatDate(startDate)) → \(formatDate(endDate))")
        print("  Cache: \(cacheDir.path)")
        print()

        // Use EvaluationEngine.prefetchData to trigger all fetches with their
        // buffers (this is the same call that evaluate makes internally).
        let config     = EvalConfig.default
        let engine     = EvaluationEngine(dataSource: dataSource)

        let t0 = Date()
        printStderr("Fetching glucose values …")
        _ = try await engine.prefetchData(for: interval, config: config)
        let elapsed = Date().timeIntervalSince(t0)
        printStderr("\r")

        print("✓ Data cached to \(cacheDir.path)")
        print("  Elapsed: \(String(format: "%.1f", elapsed))s")
    }
}

// MARK: – Helpers

private func formatDate(_ date: Date) -> String {
    let df = DateFormatter()
    df.dateFormat = "yyyy-MM-dd"
    df.locale = Locale(identifier: "en_US_POSIX")
    return df.string(from: date)
}
