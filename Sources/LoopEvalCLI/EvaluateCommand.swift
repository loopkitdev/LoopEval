// EvaluateCommand.swift — `loop-eval evaluate` subcommand

import ArgumentParser
import EvalCore
import Foundation

@available(macOS 10.15, macCatalyst 13, iOS 13, tvOS 13, watchOS 6, *)
struct EvaluateCommand: AsyncParsableCommand {

    static let configuration = CommandConfiguration(
        commandName: "evaluate",
        abstract: "Run forecast evaluation over a historical period."
    )

    // MARK: – Required options

    @Option(name: .long, help: "Nightscout base URL (e.g. https://mysite.nightscout.io)")
    var nightscoutUrl: String

    @Option(name: .long, help: "Start date — ISO8601, e.g. 2026-01-01 or 2026-01-01T00:00:00Z")
    var start: String

    @Option(name: .long, help: "End date   — ISO8601, e.g. 2026-01-08 or 2026-01-08T00:00:00Z")
    var end: String

    // MARK: – Auth

    @Option(name: .long, help: "Nightscout API secret (optional; hashed before sending)")
    var apiSecret: String?

    // MARK: – Storage

    @Option(name: .long, help: "Cache directory for fetched Nightscout data",
            transform: URL.init(fileURLWithPath:))
    var cacheDir: URL = URL(fileURLWithPath: NSHomeDirectory())
        .appendingPathComponent(".loop-eval/cache")

    // MARK: – Algorithm config

    @Option(name: .long,
            help: "Insulin model: rapidActingAdult | rapidActingChild | fiasp | lyumjev | afrezza")
    var insulinType: String = "rapidActingAdult"

    @Option(name: .long, help: "Evaluation step in minutes (default: 5)")
    var stepMinutes: Int = 5

    @Flag(name: .long, help: "Use integral retrospective correction (default: standard RC)")
    var integralRC: Bool = false

    @Flag(name: .long, help: "Disable Kalman smoothing of actual CGM used for comparison")
    var noKalman: Bool = false

    @Flag(name: .long, help: "Exclude future-scheduled insulin (real-time simulation mode)")
    var noFutureInsulin: Bool = false

    @Option(name: .long, help: "ISF multiplier applied to Nightscout sensitivity values (default: 1.0). Values >1 raise ISF (less aggressive), <1 lower ISF (more aggressive).")
    var sensitivityMultiplier: Double = 1.0

    // MARK: – Output

    @Option(name: .long, help: "Output format: table | json | csv")
    var output: String = "table"

    // MARK: – Run

    mutating func run() async throws {

        // 1. Parse dates
        let startDate = try parseISO8601Date(start)
        let endDate   = try parseISO8601Date(end)
        guard endDate > startDate else {
            throw ValidationError("--end must be after --start")
        }
        let interval = DateInterval(start: startDate, end: endDate)

        // 2. Parse insulin type
        let preset = try parseInsulinType(insulinType)

        // 3. Build EvalConfig
        let config = EvalConfig(
            evalStep: TimeInterval(stepMinutes) * 60,
            includeFutureInsulin: !noFutureInsulin,
            useIntegralRC: integralRC,
            kalmanSmoothing: !noKalman,
            sensitivityMultiplier: sensitivityMultiplier
        )

        // 4. Create data source
        guard let baseURL = URL(string: nightscoutUrl) else {
            throw ValidationError("Invalid Nightscout URL: \(nightscoutUrl)")
        }
        let client = NightscoutClient(baseURL: baseURL, apiSecret: apiSecret)
        let cache  = try DataCache(cacheDir: cacheDir)
        let dataSource = NightscoutEvalDataSource(
            client: client,
            cache: cache,
            insulinType: preset
        )

        // 5. Create engine
        let engine = EvaluationEngine(dataSource: dataSource)

        // 6. Fetch data with progress
        let fetchStart = Date()
        printStderr("Fetching data...")
        let data = try await engine.prefetchData(for: interval, config: config)
        let fetchDuration = Date().timeIntervalSince(fetchStart)
        printStderr("\rFetching data... done (\(String(format: "%.1f", fetchDuration))s)\n")

        // 7. Run sweep with progress
        let result = try await engine.runSweep(
            data: data,
            interval: interval,
            config: config,
            progress: { fraction in
                let pct    = Int(fraction * 100)
                let filled = Int(fraction * 20)
                let empty  = 20 - filled
                let bar    = String(repeating: "█", count: filled)
                           + String(repeating: "░", count: empty)
                printStderr("\rEvaluating: \(bar) \(pct)%  ")
            }
        )
        printStderr("\rEvaluating: ████████████████████ 100%\n")

        // 8. Analyze
        let smoother: KalmanSmoother? = noKalman ? nil : KalmanSmoother()
        let analyzer = EvaluationAnalyzer(smoother: smoother)
        let score = analyzer.analyze(result: result)

        let totalDuration = Date().timeIntervalSince(fetchStart)

        // 9. Output
        switch output.lowercased() {
        case "json":
            try OutputFormatter.printJSON(score: score)
        case "csv":
            OutputFormatter.printCSV(score: score)
        default: // "table"
            OutputFormatter.printTable(
                score: score,
                interval: interval,
                config: config,
                insulinTypeName: insulinType,
                predictionCount: result.predictionCount,
                skippedCount: result.skippedCount,
                durationSeconds: totalDuration
            )
        }
    }
}

// MARK: – Helpers (package-internal, shared with CacheCommand)

/// Parse an ISO8601 date string, accepting both date-only and full datetime.
func parseISO8601Date(_ string: String) throws -> Date {
    // Try full ISO8601 with fractional seconds
    let fmt1 = ISO8601DateFormatter()
    fmt1.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    if let d = fmt1.date(from: string) { return d }

    // Try full ISO8601 without fractional seconds
    let fmt2 = ISO8601DateFormatter()
    fmt2.formatOptions = [.withInternetDateTime]
    if let d = fmt2.date(from: string) { return d }

    // Try date-only: interpret as midnight UTC
    let fmt3 = ISO8601DateFormatter()
    fmt3.formatOptions = [.withFullDate]
    fmt3.timeZone = .current
    if let d = fmt3.date(from: string) { return d }

    // Try "2026-01-01" → midnight local
    let df = DateFormatter()
    df.dateFormat = "yyyy-MM-dd"
    df.locale = Locale(identifier: "en_US_POSIX")
    df.timeZone = .current
    if let d = df.date(from: string) { return d }

    throw ValidationError(
        "Cannot parse date '\(string)'. Use ISO8601 format, e.g. 2026-01-01 or 2026-01-01T00:00:00Z"
    )
}

/// Map an insulin type name string → ExponentialInsulinModelPreset.
func parseInsulinType(_ string: String) throws -> ExponentialInsulinModelPreset {
    switch string.lowercased().replacingOccurrences(of: "-", with: "").replacingOccurrences(of: "_", with: "") {
    case "rapidactingadult":  return .rapidActingAdult
    case "rapidactingchild":  return .rapidActingChild
    case "fiasp":             return .fiasp
    case "lyumjev":           return .lyumjev
    case "afrezza":           return .afrezza
    default:
        throw ValidationError(
            "Unknown insulin type: '\(string)'. Valid: rapidActingAdult, rapidActingChild, fiasp, lyumjev, afrezza"
        )
    }
}

/// Print to stderr without a newline.
func printStderr(_ message: String) {
    var standardError = StandardErrorOutputStream()
    print(message, terminator: "", to: &standardError)
}

/// A TextOutputStream that writes to stderr.
struct StandardErrorOutputStream: TextOutputStream {
    mutating func write(_ string: String) {
        FileHandle.standardError.write(Data(string.utf8))
    }
}
