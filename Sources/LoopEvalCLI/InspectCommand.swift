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

    @Flag(name: .long, help: "Oracle mode: include future doses in Loop's prediction window. Default OFF since 2026-05-17.")
    var oracleFutureInputs: Bool = false

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
            includeFutureInsulin: oracleFutureInputs,
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

        // ── Insulin-informed Kalman smoothing (visualization only) ───────────────
        let insulinKalmanSmoothed: [EvalGlucoseSample]?
        if config.kalmanSmoothing {
            printStderr("Running insulin-informed Kalman smoother...")
            let insulinSmoother = InsulinInformedKalmanSmoother()
            insulinKalmanSmoothed = insulinSmoother.smooth(
                samples: result.actual,
                doses: preloaded.doses,
                isfSchedule: preloaded.therapyTimeline.sensitivity
            )
            printStderr(" done\n")
        } else {
            insulinKalmanSmoothed = nil
        }

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

        // ── Fetch Nightscout profile timezone ─────────────────────────────────────
        let nsTimezone: String?
        do {
            let profileRecord = try await client.fetchProfile()
            let profileName = profileRecord.defaultProfile ?? "Default"
            let profile = profileRecord.store?[profileName] ?? profileRecord.store?.values.first
            nsTimezone = profile?.timezone
        } catch {
            nsTimezone = nil
        }

        // ── Compute DTS risk timeline ─────────────────────────────────────────────
        // For every prediction × horizon, interpolate the actual CGM at the target
        // time and compute the signed DTS risk score (predicted as "measured",
        // actual as "reference").  Use the same smoothed-actual series that the
        // error metrics use so the risk scores are consistent with RMSE/bias.
        printStderr("Computing DTS risk timeline...")
        let actualForRisk = config.kalmanSmoothing ? smoothedActual : result.actual
        let horizons = result.config.horizons
        var dtsRiskPoints: [DtsRiskPoint] = []
        dtsRiskPoints.reserveCapacity(result.predictions.count * horizons.count)
        for record in result.predictions {
            let tMs = record.evaluatedAt.timeIntervalSince1970 * 1000
            for horizon in horizons {
                let targetDate = record.evaluatedAt.addingTimeInterval(horizon)
                guard
                    let predicted = record.predictedValue(atHorizon: horizon),
                    let actual    = GlucoseInterpolator.interpolate(
                                        samples: actualForRisk, at: targetDate)
                else { continue }
                let risk = CustomDTSRisk.signedRiskScore(reference: actual, measured: predicted)
                dtsRiskPoints.append(DtsRiskPoint(
                    t: tMs,
                    horizonMin: Int(horizon / 60),
                    risk: risk
                ))
            }
        }
        printStderr(" \(dtsRiskPoints.count) points\n")

        // ── Build inspection bundle ───────────────────────────────────────────────
        let bundle = InspectionBundleBuilder.build(
            result: result,
            smoothed: config.kalmanSmoothing ? smoothedActual : nil,
            insulinKalmanSmoothed: insulinKalmanSmoothed,
            score: score,
            doses: preloaded.doses,
            carbs: preloaded.carbs,
            therapyTimeline: preloaded.therapyTimeline,
            sampleStride: 1,   // every prediction — needed for click-to-navigate
            nsPredictions: nsPredictions,
            dtsRiskTimeline: dtsRiskPoints,
            nsTimezone: nsTimezone
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
