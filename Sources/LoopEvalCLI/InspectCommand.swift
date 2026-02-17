// InspectCommand.swift — `loop-eval inspect` subcommand

import ArgumentParser
import EvalCore
import Foundation

struct InspectCommand: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "inspect",
        abstract: "Run evaluation and generate an interactive HTML inspection report.",
        discussion: """
        Produces a self-contained HTML file with three interactive panels:
          1. Input data timeline (raw CGM, smoothed CGM, doses, carbs)
          2. Forecast error profile by horizon (RMSE, bias, P10/P90)
          3. Prediction detail — scrub through time to inspect individual
             prediction curves vs actual glucose
        """
    )

    // MARK: – Options (mirrors EvaluateCommand)

    @Option(name: .long, help: "Nightscout base URL (e.g. https://your-ns.example.com)")
    var nightscoutUrl: String

    @Option(name: .long, help: "Start date YYYY-MM-DD (local time, inclusive)")
    var start: String

    @Option(name: .long, help: "End date YYYY-MM-DD (local time, exclusive)")
    var end: String

    @Option(name: .long, help: "Insulin model: rapidActingAdult | rapidActingChild | fiasp | lyumjev | afrezza")
    var insulinType: String = "rapidActingAdult"

    @Flag(name: .long, help: "Disable Kalman smoothing on actual CGM")
    var noKalman: Bool = false

    @Flag(name: .long, help: "Use integral retrospective correction")
    var integralRc: Bool = false

    @Flag(name: .long, help: "Exclude future insulin from predictions")
    var noFutureInsulin: Bool = false

    @Option(name: .long, help: "Nightscout API secret (if auth required)")
    var apiSecret: String?

    @Option(name: .long, help: "Cache directory path")
    var cacheDirPath: String = NSHomeDirectory() + "/.loop-eval/cache"

    @Option(name: [.short, .long], help: "Output HTML file path (default: loop-eval-report.html)")
    var output: String = "loop-eval-report.html"

    // MARK: – Run

    func run() async throws {
        // ── Parse dates ──────────────────────────────────────────────────────────
        let startDate = try parseISO8601Date(start)
        let endDate   = try parseISO8601Date(end)
        guard startDate < endDate else {
            throw ValidationError("Start must be before end: \(start) – \(end)")
        }
        let cal = Calendar.current
        let interval = DateInterval(
            start: cal.startOfDay(for: startDate),
            end:   cal.startOfDay(for: endDate)
        )

        // ── Build config ──────────────────────────────────────────────────────────
        let preset = try parseInsulinType(insulinType)
        let config = EvalConfig(
            includeFutureInsulin: !noFutureInsulin,
            useIntegralRC: integralRc,
            kalmanSmoothing: !noKalman
        )

        // ── Build data source ─────────────────────────────────────────────────────
        guard let baseURL = URL(string: nightscoutUrl) else {
            throw ValidationError("Invalid Nightscout URL: \(nightscoutUrl)")
        }
        let client     = NightscoutClient(baseURL: baseURL, apiSecret: apiSecret)
        let cache      = try DataCache(cacheDir: URL(fileURLWithPath: cacheDirPath))
        let dataSource = NightscoutEvalDataSource(client: client, cache: cache,
                                                  insulinType: preset)
        let engine     = EvaluationEngine(dataSource: dataSource)

        // ── Prefetch ──────────────────────────────────────────────────────────────
        printStderr("Fetching data...")
        let t0 = Date()
        let preloaded = try await engine.prefetchData(for: interval, config: config)
        printStderr(String(format: " done (%.1fs)\n", Date().timeIntervalSince(t0)))

        // ── Evaluate ──────────────────────────────────────────────────────────────
        let result = try await engine.runSweep(
            data: preloaded,
            interval: interval,
            config: config,
            progress: { frac in
                let pct = Int(frac * 100)
                let bar = String(repeating: "█", count: min(20, pct / 5)) +
                          String(repeating: "░", count: 20 - min(20, pct / 5))
                printStderr("\rEvaluating: \(bar) \(pct)%  ")
            }
        )
        printStderr("\rEvaluating: done                          \n")

        // ── Analyse ───────────────────────────────────────────────────────────────
        let smoother: KalmanSmoother? = config.kalmanSmoothing ? KalmanSmoother() : nil
        let analyzer = EvaluationAnalyzer(smoother: smoother)
        let (score, smoothedActual) = analyzer.analyzeWithSmoothed(result: result)

        // ── Fetch Nightscout devicestatus for NS forecast overlay ─────────────────
        printStderr("Fetching Nightscout devicestatus...")
        let nsPredictions: [NsPrediction]
        do {
            let rawStatuses = try await client.fetchDeviceStatus(
                from: interval.start, to: interval.end)
            nsPredictions = rawStatuses.compactMap { NsPrediction.from(status: $0) }
                .sorted { $0.t < $1.t }
            printStderr(" \(nsPredictions.count) forecasts\n")
        } catch {
            printStderr(" skipped (\(error))\n")
            nsPredictions = []
        }

        // ── Build inspection bundle ───────────────────────────────────────────────
        let bundle = InspectionBundleBuilder.build(
            result: result,
            smoothed: config.kalmanSmoothing ? smoothedActual : nil,
            score: score,
            doses: preloaded.doses,
            carbs: preloaded.carbs,
            therapyTimeline: preloaded.therapyTimeline,
            sampleStride: 6,   // one snapshot per 30 min at 5-min steps
            nsPredictions: nsPredictions
        )

        // ── Generate HTML ─────────────────────────────────────────────────────────
        printStderr("Generating report...")
        let html = try HTMLReportGenerator.generate(bundle: bundle)
        let outputURL: URL
        if output.hasPrefix("/") || output.hasPrefix("~") {
            outputURL = URL(fileURLWithPath: output)
        } else {
            outputURL = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
                .appendingPathComponent(output)
        }
        try html.write(to: outputURL, atomically: true, encoding: .utf8)
        printStderr(" done\n")
        print("Report: \(outputURL.path)")
    }
}
