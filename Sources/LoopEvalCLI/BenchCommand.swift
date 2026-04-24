// BenchCommand.swift — `loop-eval bench` subcommand for settings comparison
//
// Runs two evaluation configurations on the same pre-fetched data to compare
// different settings (sensitivity, CR, basal multipliers, etc.) without
// requiring separate algorithm builds.

import ArgumentParser
import EvalCore
import Foundation

@available(macOS 10.15, macCatalyst 13, iOS 13, tvOS 13, watchOS 6, *)
struct BenchCommand: AsyncParsableCommand {

    static let configuration = CommandConfiguration(
        commandName: "bench",
        abstract: "Compare two evaluation configurations on the same data.",
        discussion: """
        Runs baseline and candidate configurations on the same pre-fetched data.
        Use this to test how settings changes (ISF, CR, basal multipliers) affect
        forecast accuracy without modifying the algorithm.

        Example:
          loop-eval bench \\
            --nightscout-url https://mysite.nightscout.io \\
            --start 2026-03-01 --end 2026-03-08 \\
            --baseline-label "Current" \\
            --candidate-label "Lower ISF" \\
            --candidate-sensitivity-multiplier 0.9 \\
            --html comparison.html
        """
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

    // MARK: – Baseline config (same as evaluate command)

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

    @Option(name: .long, help: "ISF multiplier for baseline (default: 1.0)")
    var sensitivityMultiplier: Double = 1.0

    @Option(name: .long, help: "Carb ratio multiplier for baseline (default: 1.0)")
    var crMultiplier: Double = 1.0

    @Option(name: .long, help: "Basal rate multiplier for baseline (default: 1.0)")
    var basalMultiplier: Double = 1.0

    // MARK: – Labels

    @Option(name: .long, help: "Label for the baseline configuration")
    var baselineLabel: String = "Baseline"

    @Option(name: .long, help: "Label for the candidate configuration")
    var candidateLabel: String = "Candidate"

    // MARK: – Candidate overrides

    @Option(name: .long, help: "Candidate ISF multiplier (default: same as baseline)")
    var candidateSensitivityMultiplier: Double?

    @Option(name: .long, help: "Candidate carb ratio multiplier (default: same as baseline)")
    var candidateCrMultiplier: Double?

    @Option(name: .long, help: "Candidate basal rate multiplier (default: same as baseline)")
    var candidateBasalMultiplier: Double?

    @Option(name: .long, help: "Candidate insulin model (default: same as baseline)")
    var candidateInsulinType: String?

    @Flag(name: .long, help: "Use integral RC for candidate")
    var candidateIntegralRC: Bool = false

    @Flag(name: .long, help: "Exclude future insulin for candidate")
    var candidateNoFutureInsulin: Bool = false

    // MARK: – Output

    @Option(name: .long, help: "Write a comparison HTML report to this path")
    var html: String?

    // MARK: – Run

    mutating func run() async throws {

        // 1. Parse dates
        let startDate = try parseISO8601Date(start)
        let endDate   = try parseISO8601Date(end)
        guard endDate > startDate else {
            throw ValidationError("--end must be after --start")
        }
        let interval = DateInterval(start: startDate, end: endDate)

        // 2. Parse insulin types
        let baselinePreset = try parseInsulinType(insulinType)
        // Validate candidate insulin type if provided (even though we use baselinePreset for data fetching)
        if let candType = candidateInsulinType {
            _ = try parseInsulinType(candType)
        }

        // 3. Build baseline config
        let baselineConfig = EvalConfig(
            evalStep: TimeInterval(stepMinutes) * 60,
            includeFutureInsulin: !noFutureInsulin,
            useIntegralRC: integralRC,
            kalmanSmoothing: !noKalman,
            sensitivityMultiplier: sensitivityMultiplier,
            carbRatioMultiplier: crMultiplier,
            basalRateMultiplier: basalMultiplier
        )

        // 4. Build candidate config (start from baseline, apply overrides)
        let candidateConfig = EvalConfig(
            evalStep: TimeInterval(stepMinutes) * 60,
            includeFutureInsulin: candidateNoFutureInsulin ? false : !noFutureInsulin,
            useIntegralRC: candidateIntegralRC || integralRC,
            kalmanSmoothing: !noKalman,
            sensitivityMultiplier: candidateSensitivityMultiplier ?? sensitivityMultiplier,
            carbRatioMultiplier: candidateCrMultiplier ?? crMultiplier,
            basalRateMultiplier: candidateBasalMultiplier ?? basalMultiplier
        )

        // 5. Create data source (use baseline insulin type for fetching)
        guard let baseURL = URL(string: nightscoutUrl) else {
            throw ValidationError("Invalid Nightscout URL: \(nightscoutUrl)")
        }
        let client = NightscoutClient(baseURL: baseURL, apiSecret: apiSecret)
        let cache  = try DataCache(cacheDir: cacheDir)
        let dataSource = NightscoutEvalDataSource(
            client: client,
            cache: cache,
            insulinType: baselinePreset
        )

        // 6. Create engine
        let engine = EvaluationEngine(dataSource: dataSource)

        // 7. Fetch data once
        let fetchStart = Date()
        printStderr("Fetching data...")
        let data = try await engine.prefetchData(for: interval, config: baselineConfig)
        let fetchDuration = Date().timeIntervalSince(fetchStart)
        printStderr("\rFetching data... done (\(String(format: "%.1f", fetchDuration))s)\n")

        // 8. Run baseline sweep
        printStderr("Running baseline...")
        let baselineResult = try await engine.runSweep(
            data: data,
            interval: interval,
            config: baselineConfig,
            progress: { fraction in
                let pct = Int(fraction * 100)
                printStderr("\rRunning baseline: \(pct)%  ")
            }
        )
        printStderr("\rRunning baseline: 100%\n")

        // 9. Run candidate sweep
        printStderr("Running candidate...")
        let candidateResult = try await engine.runSweep(
            data: data,
            interval: interval,
            config: candidateConfig,
            progress: { fraction in
                let pct = Int(fraction * 100)
                printStderr("\rRunning candidate: \(pct)%  ")
            }
        )
        printStderr("\rRunning candidate: 100%\n")

        // 10. Analyze results
        let smoother: KalmanSmoother? = noKalman ? nil : KalmanSmoother()
        let analyzer = EvaluationAnalyzer(smoother: smoother)
        let baselineScore = analyzer.analyze(result: baselineResult)
        let candidateScore = analyzer.analyze(result: candidateResult)

        // 10b. Delivery-based ODR/UDR (candidate vs baseline)
        let deliveryHorizons = baselineScore.horizonMetrics.map { $0.horizon }
        let deliveryScores = DeliveryScores.compute(
            baseline: baselineResult,
            candidate: candidateResult,
            horizons: deliveryHorizons,
            actualGlucose: baselineResult.actual,
            targetLow: baselineConfig.targetLow,
            targetHigh: baselineConfig.targetHigh
        )

        // 11. Print text comparison
        printComparison(
            baseline: baselineScore,
            candidate: candidateScore,
            baselineLabel: baselineLabel,
            candidateLabel: candidateLabel,
            delivery: deliveryScores
        )

        // 12. Write HTML report if requested
        if let htmlPath = html {
            let meta = ComparisonMeta(
                baselineLabel: baselineLabel,
                candidateLabel: candidateLabel,
                intervalStart: startDate,
                intervalEnd: endDate,
                runDate: Date()
            )
            try ComparisonHTMLGenerator.write(
                baseline: baselineScore,
                candidate: candidateScore,
                meta: meta,
                to: URL(fileURLWithPath: htmlPath),
                delivery: deliveryScores
            )
            printStderr("Comparison report written → \(htmlPath)\n")
        }
    }

    // MARK: – Text comparison output

    private func printComparison(
        baseline: AggregateScore,
        candidate: AggregateScore,
        baselineLabel: String,
        candidateLabel: String,
        delivery: DeliveryScores? = nil
    ) {
        let ruler = String(repeating: "━", count: 76)
        let sep   = String(repeating: "─", count: 76)

        print(ruler)
        print(" loop-eval bench")
        print(" Baseline:  \(baselineLabel)")
        print(" Candidate: \(candidateLabel)")
        print(ruler)

        print(" Weighted summary (Gaussian peak 90 min, σ=60 min)")
        print(sep)

        let rows: [(label: String, a: Double, b: Double, lowerBetter: Bool)] = [
            ("Primary  (OPR+UPR)", baseline.primaryScore,                candidate.primaryScore,                true),
            ("OPR (overprediction)", baseline.weightedOverpredictionRisk,  candidate.weightedOverpredictionRisk,  true),
            ("UPR (underprediction)", baseline.weightedUnderpredictionRisk, candidate.weightedUnderpredictionRisk, true),
            ("RMSE       (mg/dL)", baseline.weightedRMSE,               candidate.weightedRMSE,               true),
        ]

        for row in rows {
            print(summaryLine(row.label, valA: row.a, valB: row.b, lowerBetter: row.lowerBetter))
        }

        if let d = delivery {
            print(sep)
            print(" Delivery-based scores (candidate vs baseline Δdose, weighted by Clarke-Kovatchev risk)")
            print(sep)
            print(String(format: "   ODR (over-delivery at pre-low):   %6.4f U·√rl", d.weightedODR))
            print(String(format: "   UDR (under-delivery at pre-high): %6.4f U·√rh", d.weightedUDR))
            print(String(format: "   ODR + UDR:                        %6.4f", d.primaryDeliveryScore))
            print(" (positive ODR = candidate delivered MORE insulin at moments where actual BG ended low)")
            print(" (positive UDR = candidate delivered LESS insulin at moments where actual BG ended high)")
        }

        print(ruler)
    }

    private func summaryLine(
        _ label: String,
        valA: Double,
        valB: Double,
        lowerBetter: Bool
    ) -> String {
        let delta = valB - valA
        let pct   = valA != 0 ? (delta / abs(valA)) * 100 : 0
        let arrow = delta < 0 ? "▼" : (delta > 0 ? "▲" : "=")
        let improved = lowerBetter ? (delta < 0) : (delta > 0)
        let verdict  = abs(delta) < 1e-9 ? "  " : (improved ? "✓" : "✗")

        let fmt = abs(valA) >= 10 ? "%.2f" : "%.4f"
        let aStr = String(format: fmt, valA)
        let bStr = String(format: fmt, valB)
        let dStr = delta >= 0
            ? String(format: "+\(fmt)", delta)
            : String(format: fmt,       delta)
        let pStr = pct >= 0
            ? String(format: "+%.1f%%", pct)
            : String(format: "%.1f%%",  pct)

        let labelPad  = label.padding(toLength: 22, withPad: " ", startingAt: 0)
        let aPad      = String(repeating: " ", count: max(0, 8 - aStr.count)) + aStr
        let bPad      = bStr.padding(toLength: 8, withPad: " ", startingAt: 0)
        let dPad      = dStr.padding(toLength: 10, withPad: " ", startingAt: 0)
        let pPad      = pStr.padding(toLength: 7, withPad: " ", startingAt: 0)
        return "  \(labelPad)  \(aPad) → \(bPad)  Δ \(dPad)  \(arrow) \(pPad)  \(verdict)"
    }
}
