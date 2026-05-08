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

    @Flag(name: .long, help: "Use asymmetric momentum for baseline (slow rise, fast drop)")
    var asymmetricMomentum: Bool = false

    @Option(name: .long, help: "Positive v_cgm cap for baseline (mg/dL/min). Unset = no cap.")
    var momentumCap: Double?

    @Option(name: .long, help: "Baseline asymmetric-momentum EMA alpha for building positive momentum (default 0.15)")
    var momentumAlphaSlow: Double = 0.15

    @Option(name: .long, help: "Baseline asymmetric-momentum EMA alpha for shedding positive momentum (default 0.85)")
    var momentumAlphaFast: Double = 0.85

    // MARK: – Labels

    @Option(name: .long, help: "Label for the baseline configuration")
    var baselineLabel: String = "Baseline"

    @Option(name: .long, help: "Label for the candidate configuration")
    var candidateLabel: String = "Candidate"

    // MARK: – Candidate overrides

    @Option(name: .long, help: "Candidate ISF multiplier (default: same as baseline)")
    var candidateSensitivityMultiplier: Double?

    @Option(name: .long, help: "Candidate per-hour ISF multipliers — 24 comma-separated doubles (e.g. \"1.0,1.0,1.1,...\"). Applied on top of --candidate-sensitivity-multiplier. Index 0 = local hour 00:00.")
    var candidateIsfHourly: String?

    @Option(name: .long, help: "Local timezone identifier for hour-of-day interpretation (default: system tz, e.g. America/Chicago)")
    var localTimezone: String?

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

    @Flag(name: .long, help: "Use asymmetric momentum for candidate (slow rise, fast drop)")
    var candidateAsymmetricMomentum: Bool = false

    @Option(name: .long, help: "Candidate positive v_cgm cap (mg/dL/min)")
    var candidateMomentumCap: Double?

    @Option(name: .long, help: "Candidate asymmetric-momentum alpha-slow (default: same as baseline)")
    var candidateMomentumAlphaSlow: Double?

    @Option(name: .long, help: "Candidate asymmetric-momentum alpha-fast (default: same as baseline)")
    var candidateMomentumAlphaFast: Double?

    @Flag(name: .long, help: "Enable glucose-based application factor (GBAF) for candidate — auto-bolus app-factor scales with current BG")
    var candidateGbaf: Bool = false

    @Option(name: .long, help: "GBAF curve: BG (mg/dL) at/below which factor=factorLow (default 140)")
    var candidateGbafLowAnchor: Double = 140.0

    @Option(name: .long, help: "GBAF curve: BG (mg/dL) at/above which factor=factorHigh (default 220)")
    var candidateGbafHighAnchor: Double = 220.0

    @Option(name: .long, help: "GBAF curve: applicationFactor at lowAnchor (default 0.4)")
    var candidateGbafFactorLow: Double = 0.4

    @Option(name: .long, help: "GBAF curve: applicationFactor at highAnchor (default 0.7)")
    var candidateGbafFactorHigh: Double = 0.7

    @Flag(name: .long, help: "Enable post-low conservative mode for candidate (suppresses dosing for a window after a low)")
    var candidatePostLow: Bool = false

    @Option(name: .long, help: "Post-low conservative window (hours, default 3.0)")
    var candidatePostLowWindow: Double = 3.0

    @Option(name: .long, help: "Post-low conservative applicationFactor (default 0.2)")
    var candidatePostLowAppFactor: Double = 0.2

    @Option(name: .long, help: "Post-low entry threshold (mg/dL, default 70)")
    var candidatePostLowEntryThreshold: Double = 70.0

    @Option(name: .long, help: "Post-low rise-rate gate (mg/dL/min, 0=disabled). Only fires post-low mode if recent CGM rise rate exceeds this.")
    var candidatePostLowRiseRateGate: Double = 0.0

    @Flag(name: .long, help: "Post-low IOB headroom gate: only fire when IOB > threshold")
    var candidatePostLowRequireIobHeadroom: Bool = false

    @Option(name: .long, help: "Post-low IOB gate threshold (U, default -0.5)")
    var candidatePostLowIobGateThreshold: Double = -0.5

    @Flag(name: .long, help: "Enable dynamic-ISF for candidate: scale ISF used for dose calc when recent rolling-mean ICE indicates elevated sensitivity (forecast unchanged)")
    var candidateDynamicIsf: Bool = false

    @Option(name: .long, help: "Dynamic-ISF rolling window for ICE averaging (hours, default 2.0)")
    var candidateDynamicIsfWindowHours: Double = 2.0

    @Option(name: .long, help: "Dynamic-ISF ICE threshold (mg/dL/min, default 0.5). Mean ICE more negative than -threshold triggers scaling.")
    var candidateDynamicIsfIceThreshold: Double = 0.5

    @Option(name: .long, help: "Dynamic-ISF max ISF scale-up (default 0.5 = +50%)")
    var candidateDynamicIsfMaxBoost: Double = 0.5

    // MARK: – Output

    @Option(name: .long, help: "Write a comparison HTML report to this path")
    var html: String?

    @Option(name: .long, help: "Write a per-timestep trace JSON (predictions, dose deltas, counterfactual BG) for analysis")
    var traceOut: String?

    // MARK: – Run

    mutating func run() async throws {

        // 1. Parse dates
        let startDate = try parseISO8601Date(start)
        let endDate   = try parseISO8601Date(end)
        guard endDate > startDate else {
            throw ValidationError("--end must be after --start")
        }
        let interval = DateInterval(start: startDate, end: endDate)

        // 1b. Parse hourly ISF multipliers + timezone
        let hourlyISF: [Double]?
        if let csv = candidateIsfHourly {
            let parts = csv.split(separator: ",").map { Double($0.trimmingCharacters(in: .whitespaces)) }
            guard parts.count == 24, parts.allSatisfy({ $0 != nil }) else {
                throw ValidationError("--candidate-isf-hourly requires exactly 24 comma-separated numbers")
            }
            hourlyISF = parts.map { $0! }
        } else {
            hourlyISF = nil
        }
        let resolvedTz: TimeZone = localTimezone.flatMap { TimeZone(identifier: $0) } ?? .current

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
            basalRateMultiplier: basalMultiplier,
            positiveVelocityCap: momentumCap,
            useAsymmetricMomentum: asymmetricMomentum,
            momentumAlphaSlow: momentumAlphaSlow,
            momentumAlphaFast: momentumAlphaFast
        )

        // 4. Build candidate config (start from baseline, apply overrides)
        let candidateConfig = EvalConfig(
            evalStep: TimeInterval(stepMinutes) * 60,
            includeFutureInsulin: candidateNoFutureInsulin ? false : !noFutureInsulin,
            useIntegralRC: candidateIntegralRC || integralRC,
            kalmanSmoothing: !noKalman,
            sensitivityMultiplier: candidateSensitivityMultiplier ?? sensitivityMultiplier,
            sensitivityHourlyMultipliers: hourlyISF,
            localTimezone: resolvedTz,
            carbRatioMultiplier: candidateCrMultiplier ?? crMultiplier,
            basalRateMultiplier: candidateBasalMultiplier ?? basalMultiplier,
            positiveVelocityCap: candidateMomentumCap ?? momentumCap,
            useAsymmetricMomentum: candidateAsymmetricMomentum || asymmetricMomentum,
            momentumAlphaSlow: candidateMomentumAlphaSlow ?? momentumAlphaSlow,
            momentumAlphaFast: candidateMomentumAlphaFast ?? momentumAlphaFast,
            glucoseBasedApplicationFactor: candidateGbaf,
            gbafLowAnchor: candidateGbafLowAnchor,
            gbafHighAnchor: candidateGbafHighAnchor,
            gbafFactorLow: candidateGbafFactorLow,
            gbafFactorHigh: candidateGbafFactorHigh,
            postLowConservativeMode: candidatePostLow,
            postLowWindow: candidatePostLowWindow,
            postLowAppFactor: candidatePostLowAppFactor,
            postLowEntryThreshold: candidatePostLowEntryThreshold,
            postLowRiseRateGate: candidatePostLowRiseRateGate,
            postLowRequireIOBHeadroom: candidatePostLowRequireIobHeadroom,
            postLowIOBGateThreshold: candidatePostLowIobGateThreshold,
            dynamicISFMode: candidateDynamicIsf,
            dynamicISFWindowHours: candidateDynamicIsfWindowHours,
            dynamicISFICEThreshold: candidateDynamicIsfIceThreshold,
            dynamicISFMaxBoost: candidateDynamicIsfMaxBoost
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
            evalStep: baselineConfig.evalStep,
            dangerLow: baselineConfig.dangerLow,
            dangerHigh: baselineConfig.dangerHigh
        )

        // 10c. Simulation-based TIR / AUC metrics on counterfactual BG
        let simScores = SimulationScores.compute(
            baseline: baselineResult,
            candidate: candidateResult,
            actualGlucose: baselineResult.actual,
            insulinModel: data.therapyTimeline.insulinType.model,
            sensitivity: data.therapyTimeline.sensitivity
        )

        // 11. Print text comparison
        printComparison(
            baseline: baselineScore,
            candidate: candidateScore,
            baselineLabel: baselineLabel,
            candidateLabel: candidateLabel,
            delivery: deliveryScores,
            simulation: simScores
        )

        // 12. Write trace JSON if requested. Used by external tools (Python) to
        // build methodology reports with per-timestep visibility.
        if let tracePath = traceOut {
            try Self.writeTrace(
                to: URL(fileURLWithPath: tracePath),
                baseline: baselineResult,
                candidate: candidateResult,
                actual: baselineResult.actual,
                sensitivity: data.therapyTimeline.sensitivity,
                insulinModel: data.therapyTimeline.insulinType.model,
                baselineLabel: baselineLabel,
                candidateLabel: candidateLabel
            )
            printStderr("Trace JSON written → \(tracePath)\n")
        }

        // 13. Write HTML report if requested
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
        delivery: DeliveryScores? = nil,
        simulation: SimulationScores? = nil
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
            print(" RMS magnitude (per-event, duration-blind):")
            print("                          pre-low (BG<70)        pre-high (BG>180)")
            print(String(format: "   over-delivers (Δ>0):     %6.4f  ← ODR (cost)    %6.4f  ← IDB (benefit)",
                         d.weightedODR, d.weightedIDB))
            print(String(format: "   under-delivers (Δ<0):    %6.4f  ← RDB (benefit)  %6.4f  ← UDR (cost)",
                         d.weightedRDB, d.weightedUDR))
            print(sep)
            print(String(format: "   primary cost (ODR + UDR):    %6.4f", d.primaryDeliveryScore))
            print(String(format: "   primary benefit (IDB + RDB): %6.4f", d.weightedIDB + d.weightedRDB))
            // Benefit-to-cost ratio: useful for ranking interventions like GBAF
            // where some over-delivery at hypos is "paid for" by extra coverage at hypers.
            let cost = d.primaryDeliveryScore
            let benefit = d.weightedIDB + d.weightedRDB
            if cost > 0 {
                print(String(format: "   benefit / cost:               %6.2f  (>1 ⇒ net safety-positive)", benefit / cost))
            } else if benefit > 0 {
                print("   benefit / cost:                  ∞   (no costs incurred — safety-positive)")
            }

            // Rate-form section — duration-aware. Linear in event duration so a
            // 1-hour hold-back counts ~12× a 5-min one of equal magnitude.
            print(sep)
            print(" Rate-form (duration-aware, normalized by total analysis time):")
            print("                          pre-low (BG<70)        pre-high (BG>180)")
            print(String(format: "   over-delivers, U/hr:    %7.4f  ← ODR (cost)    %7.4f  ← IDB (benefit)",
                         d.weightedODRURate, d.weightedIDBURate))
            print(String(format: "   under-delivers, U/hr:   %7.4f  ← RDB (benefit)  %7.4f  ← UDR (cost)",
                         d.weightedRDBURate, d.weightedUDRURate))
            let netDelta = d.weightedIDBURate + d.weightedODRURate
                         - d.weightedUDRURate - d.weightedRDBURate
            print(String(format: "   net candidate − baseline (risk-bucketed):  %+7.4f U/hr", netDelta))
            // Risk-weighted rate ratio — duration-aware analog of benefit/cost.
            let rateCost = d.weightedODRRate + d.weightedUDRRate
            let rateBenefit = d.weightedIDBRate + d.weightedRDBRate
            if rateCost > 0 {
                print(String(format: "   risk-weighted benefit/cost:  %6.2f  (rate-form, accounts for duration)",
                             rateBenefit / rateCost))
            } else if rateBenefit > 0 {
                print("   risk-weighted benefit/cost:     ∞   (no costs incurred — safety-positive)")
            }

            // Magnitude distribution at peak horizon (90 min).
            // Tells "rare big spikes vs many small persistent ticks" apart.
            if let peak = d.horizonScores.first(where: { abs($0.horizon - 90 * 60) < 1 })
                ?? d.horizonScores.first {
                print(sep)
                print(String(format: " |Δdose| distribution at %d-min horizon (U; n events in cell):",
                             Int(peak.horizon / 60)))
                func qLine(_ name: String, _ q: MagnitudeQuantiles) -> String {
                    if q.count == 0 {
                        return String(format: "   %@   (no events)", name.padding(toLength: 4, withPad: " ", startingAt: 0))
                    }
                    return String(format: "   %@   P50 %.4f   P90 %.4f   P99 %.4f   (n=%d)",
                                  name.padding(toLength: 4, withPad: " ", startingAt: 0),
                                  q.p50, q.p90, q.p99, q.count)
                }
                print(qLine("ODR", peak.odrQuantiles))
                print(qLine("RDB", peak.rdbQuantiles))
                print(qLine("IDB", peak.idbQuantiles))
                print(qLine("UDR", peak.udrQuantiles))
            }

            print(" Costs ↑ ⇒ candidate dosed in dangerous direction at risky moments.")
            print(" Benefits ↑ ⇒ candidate dosed in beneficial direction at risky moments.")
        }

        if let s = simulation {
            print(sep)
            print(" Counterfactual TIR (linearized: candidate's Δdose impact on actual CGM)")
            print(sep)
            print(String(format: "                                actual            candidate"))
            print(String(format: "   Time in 70–180:           %5.1f%%             %5.1f%%   (%+.1f pp)",
                         100 * s.tirActual, 100 * s.tirCandidate,
                         100 * (s.tirCandidate - s.tirActual)))
            print(String(format: "   Time below 70:            %5.1f%%             %5.1f%%   (%+.1f pp)",
                         100 * s.timeBelow70Actual, 100 * s.timeBelow70Candidate,
                         100 * (s.timeBelow70Candidate - s.timeBelow70Actual)))
            print(String(format: "   Time below 54 (severe):   %5.1f%%             %5.1f%%   (%+.1f pp)",
                         100 * s.timeBelow54Actual, 100 * s.timeBelow54Candidate,
                         100 * (s.timeBelow54Candidate - s.timeBelow54Actual)))
            print(String(format: "   Time above 180:           %5.1f%%             %5.1f%%   (%+.1f pp)",
                         100 * s.timeAbove180Actual, 100 * s.timeAbove180Candidate,
                         100 * (s.timeAbove180Candidate - s.timeAbove180Actual)))
            print(String(format: "   Time above 250:           %5.1f%%             %5.1f%%   (%+.1f pp)",
                         100 * s.timeAbove250Actual, 100 * s.timeAbove250Candidate,
                         100 * (s.timeAbove250Candidate - s.timeAbove250Actual)))
            print(String(format: "   Mean BG:                  %5.1f mg/dL        %5.1f mg/dL  (%+.1f)",
                         s.meanBGActual, s.meanBGCandidate,
                         s.meanBGCandidate - s.meanBGActual))
            print(String(format: "   AUC<70:                   %7.0f          %7.0f       (%+.0f mg·min)",
                         s.aucBelow70Actual, s.aucBelow70Candidate,
                         s.aucBelow70Candidate - s.aucBelow70Actual))
            print(String(format: "   AUC>180:                  %7.0f          %7.0f       (%+.0f mg·min)",
                         s.aucAbove180Actual, s.aucAbove180Candidate,
                         s.aucAbove180Candidate - s.aucAbove180Actual))
            print(" Caveat: linearized — assumes constant ISF response, no feedback loop.")
            print(" Bounded by Δdose magnitude; valid for short-horizon impact estimation.")
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

    // MARK: – Trace export

    /// Write a per-timestep trace JSON for methodology / debug analysis.
    /// Format is intentionally simple and self-documented so external tools
    /// (Python plotting scripts) can consume it without needing to parse Swift.
    static func writeTrace(
        to url: URL,
        baseline: EvaluationResult,
        candidate: EvaluationResult,
        actual: [EvalGlucoseSample],
        sensitivity: [AbsoluteScheduleValue<LoopQuantity>],
        insulinModel: InsulinModel,
        baselineLabel: String,
        candidateLabel: String
    ) throws {
        // Pair predictions by evaluatedAt
        var basePred: [Date: PredictionRecord] = [:]
        for p in baseline.predictions { basePred[p.evaluatedAt] = p }

        let mgdlUnit = LoopUnit.milligramsPerDeciliter
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        struct Pred: Codable {
            let t: String
            let baselineDose: Double
            let candidateDose: Double
            let deltaDose: Double
            let isf: Double
        }

        var preds: [Pred] = []
        for pC in candidate.predictions {
            guard let pB = basePred[pC.evaluatedAt],
                  let dC = pC.recommendedDeltaU,
                  let dB = pB.recommendedDeltaU else { continue }
            let isfQty = sensitivity.first(where: { $0.startDate <= pC.evaluatedAt && $0.endDate > pC.evaluatedAt })?.value
                ?? sensitivity.closestPrior(to: pC.evaluatedAt)?.value
            let isf = isfQty?.doubleValue(for: mgdlUnit) ?? 0
            preds.append(Pred(
                t: formatter.string(from: pC.evaluatedAt),
                baselineDose: dB,
                candidateDose: dC,
                deltaDose: dC - dB,
                isf: isf
            ))
        }

        struct ActualSample: Codable {
            let t: String
            let bg: Double
        }
        let actualOut = actual.sorted { $0.startDate < $1.startDate }.map {
            ActualSample(t: formatter.string(from: $0.startDate),
                         bg: $0.quantity.doubleValue(for: mgdlUnit))
        }

        // Sample the insulin activity curve at a 5-min grid for the duration
        struct CurvePoint: Codable {
            let tMin: Double
            let percentRemaining: Double
            let percentDelivered: Double
        }
        let dur = insulinModel.effectDuration
        var curve: [CurvePoint] = []
        var τ: TimeInterval = 0
        while τ <= dur {
            let pr = insulinModel.percentEffectRemaining(at: τ)
            curve.append(CurvePoint(tMin: τ / 60.0,
                                    percentRemaining: pr,
                                    percentDelivered: 1.0 - pr))
            τ += 5 * 60
        }

        struct Trace: Codable {
            let baselineLabel: String
            let candidateLabel: String
            let intervalStart: String
            let intervalEnd: String
            let activityDurationMinutes: Double
            let predictions: [Pred]
            let actual: [ActualSample]
            let insulinActivityCurve: [CurvePoint]
        }

        let trace = Trace(
            baselineLabel: baselineLabel,
            candidateLabel: candidateLabel,
            intervalStart: formatter.string(from: baseline.interval.start),
            intervalEnd: formatter.string(from: baseline.interval.end),
            activityDurationMinutes: dur / 60.0,
            predictions: preds,
            actual: actualOut,
            insulinActivityCurve: curve
        )

        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted]
        let json = try encoder.encode(trace)
        try json.write(to: url)
    }
}
