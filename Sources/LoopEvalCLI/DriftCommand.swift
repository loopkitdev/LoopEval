// DriftCommand.swift — `loop-eval drift`: compare actual delivered doses
// against what the current LoopAlgorithm would recommend at each step.
//
// Where a normal bench compares two synthetic configurations (A and B) on
// the same historical BG, this compares the *actual* historical delivery
// (what the pump did at the time, as recorded in Nightscout) against what
// the current LoopAlgorithm build would recommend at each step.
//
// Useful for detecting algorithm drift: if the user's pump was running an
// older Loop version, the stored doses may differ materially from what a
// current Loop would do. This quantifies the difference in clinically
// meaningful terms (delivery-based ODR/UDR) rather than just raw dose
// deltas.

import ArgumentParser
import EvalCore
import Foundation
import LoopAlgorithm

@available(macOS 10.15, macCatalyst 13, iOS 13, tvOS 13, watchOS 6, *)
struct DriftCommand: AsyncParsableCommand {

    static let configuration = CommandConfiguration(
        commandName: "drift",
        abstract: "Compare actual Nightscout-recorded delivery against Loop-now's recommendations.",
        discussion: """
        Detects algorithm drift by re-deriving dose recommendations at every
        5-min step and comparing to what was actually delivered. Emits
        delivery-based ODR/UDR (same framework as bench) with the actual
        delivery treated as baseline and Loop-now's output as candidate.
          ODR > 0 → Loop-now would have delivered MORE insulin at moments
                    where actual BG ended low (more over-delivery risk)
          UDR > 0 → Loop-now would have delivered LESS at moments where
                    actual BG ended high (more under-delivery)
        """
    )

    @Option(name: .long, help: "Nightscout base URL")
    var nightscoutUrl: String

    @Option(name: .long, help: "Start date (ISO8601)")
    var start: String

    @Option(name: .long, help: "End date (ISO8601)")
    var end: String

    @Option(name: .long, help: "Nightscout API secret (optional)")
    var apiSecret: String?

    @Option(name: .long, help: "Cache directory",
            transform: URL.init(fileURLWithPath:))
    var cacheDir: URL = URL(fileURLWithPath: NSHomeDirectory())
        .appendingPathComponent(".loop-eval/cache")

    @Option(name: .long, help: "Insulin model: rapidActingAdult | rapidActingChild | fiasp | lyumjev | afrezza")
    var insulinType: String = "rapidActingAdult"

    @Option(name: .long, help: "Evaluation step in minutes (default: 5)")
    var stepMinutes: Int = 5

    @Flag(name: .long, help: "Use asymmetric momentum (slow rise, fast drop)")
    var asymmetricMomentum: Bool = false

    @Option(name: .long, help: "Positive v_cgm cap (mg/dL/min)")
    var momentumCap: Double?

    @Flag(name: .long, help: "Disable Kalman smoothing")
    var noKalman: Bool = false

    @Option(name: .long, help: "Write comparison HTML report to this path")
    var html: String?

    mutating func run() async throws {
        let startDate = try parseISO8601Date(start)
        let endDate   = try parseISO8601Date(end)
        guard endDate > startDate else {
            throw ValidationError("--end must be after --start")
        }
        let interval = DateInterval(start: startDate, end: endDate)
        let preset = try parseInsulinType(insulinType)

        let config = EvalConfig(
            evalStep: TimeInterval(stepMinutes) * 60,
            kalmanSmoothing: !noKalman,
            positiveVelocityCap: momentumCap,
            useAsymmetricMomentum: asymmetricMomentum
        )

        guard let baseURL = URL(string: nightscoutUrl) else {
            throw ValidationError("Invalid Nightscout URL: \(nightscoutUrl)")
        }
        let client = NightscoutClient(baseURL: baseURL, apiSecret: apiSecret)
        let cache  = try DataCache(cacheDir: cacheDir)
        let dataSource = NightscoutEvalDataSource(
            client: client, cache: cache, insulinType: preset
        )
        let engine = EvaluationEngine(dataSource: dataSource)

        printStderr("Fetching data...")
        let t0 = Date()
        let data = try await engine.prefetchData(for: interval, config: config)
        printStderr(" done (\(String(format: "%.1fs", Date().timeIntervalSince(t0))))\n")

        printStderr("Running Loop-now sweep...\n")
        let candidateResult = try await engine.runSweep(
            data: data, interval: interval, config: config,
            progress: { fraction in
                let pct = Int(fraction * 100)
                printStderr("\rRunning: \(pct)%  ")
            }
        )
        printStderr("\rRunning: 100%\n")

        // Build a synthetic "baseline" EvaluationResult where each
        // PredictionRecord carries the ACTUAL delivered delta at that
        // evaluation step, instead of Loop-now's recommendation.
        printStderr("Computing actual-delivery deltas...\n")
        let evalStep = TimeInterval(stepMinutes * 60)
        let basalSchedule = data.therapyTimeline.basal
        var syntheticPredictions: [PredictionRecord] = []
        for record in candidateResult.predictions {
            let t = record.evaluatedAt
            let actualDelta = Self.actualDeliveryDelta(
                doses: data.doses,
                from: t, to: t.addingTimeInterval(evalStep),
                basalSchedule: basalSchedule
            )
            syntheticPredictions.append(PredictionRecord(
                evaluatedAt: t,
                predicted: record.predicted,
                predictedNoFutureInsulin: record.predictedNoFutureInsulin,
                iob: record.iob,
                cob: record.cob,
                recommendedDeltaU: actualDelta,
                recommendedBolus: nil,
                recommendedTempBasalRate: nil,
                scheduledBasalRate: record.scheduledBasalRate
            ))
        }
        let baselineResult = EvaluationResult(
            interval: candidateResult.interval,
            config: candidateResult.config,
            predictions: syntheticPredictions,
            actual: candidateResult.actual,
            skippedCount: candidateResult.skippedCount
        )

        // Compute delivery-based ODR/UDR
        let smoother: KalmanSmoother? = noKalman ? nil : KalmanSmoother()
        let analyzer = EvaluationAnalyzer(smoother: smoother)
        let candidateScore = analyzer.analyze(result: candidateResult)
        let horizons = candidateScore.horizonMetrics.map { $0.horizon }

        let deliveryScores = DeliveryScores.compute(
            baseline: baselineResult,
            candidate: candidateResult,
            horizons: horizons,
            actualGlucose: candidateResult.actual,
            targetLow: config.targetLow,
            targetHigh: config.targetHigh
        )

        // Summary delta stats
        var totalAbsDelta = 0.0
        var totalSignedDelta = 0.0
        var overN = 0, underN = 0
        for (c, b) in zip(candidateResult.predictions, syntheticPredictions) {
            guard let dc = c.recommendedDeltaU, let db = b.recommendedDeltaU else { continue }
            let d = dc - db
            totalAbsDelta += abs(d)
            totalSignedDelta += d
            if d > 0.01 { overN += 1 }
            else if d < -0.01 { underN += 1 }
        }

        printDriftSummary(
            deliveryScores: deliveryScores,
            totalAbsDelta: totalAbsDelta,
            totalSignedDelta: totalSignedDelta,
            overN: overN, underN: underN,
            totalSteps: candidateResult.predictions.count
        )

        // Optional HTML
        if let htmlPath = html {
            let meta = ComparisonMeta(
                baselineLabel: "Actual delivered (Nightscout)",
                candidateLabel: "Loop-now recommendation",
                intervalStart: startDate,
                intervalEnd: endDate,
                runDate: Date()
            )
            // We need a fake AggregateScore for baseline since we don't
            // have forecast error for the actual-delivery "side." Reuse
            // candidate scores in both slots (cheap hack; HTML just shows
            // forecast metrics alongside delivery).
            try ComparisonHTMLGenerator.write(
                baseline: candidateScore,
                candidate: candidateScore,
                meta: meta,
                to: URL(fileURLWithPath: htmlPath),
                delivery: deliveryScores
            )
            printStderr("Drift report written → \(htmlPath)\n")
        }
    }

    private func printDriftSummary(
        deliveryScores: DeliveryScores,
        totalAbsDelta: Double,
        totalSignedDelta: Double,
        overN: Int, underN: Int,
        totalSteps: Int
    ) {
        let ruler = String(repeating: "━", count: 76)
        let sep   = String(repeating: "─", count: 76)

        print(ruler)
        print(" loop-eval drift — algorithm drift: Loop-now vs actual delivery")
        print(ruler)

        print(" Dose-delta statistics (Loop-now − actual)")
        print(sep)
        print(String(format: "   Steps compared:              %d", totalSteps))
        print(String(format: "   Net ΔU (signed):             %+.3f U", totalSignedDelta))
        print(String(format: "   Total |ΔU| across all steps: %.3f U", totalAbsDelta))
        print(String(format: "   Steps Loop-now > actual:     %d (%.1f%%)", overN, Double(overN)/Double(max(1,totalSteps))*100))
        print(String(format: "   Steps Loop-now < actual:     %d (%.1f%%)", underN, Double(underN)/Double(max(1,totalSteps))*100))

        print(sep)
        print(" Delivery-based ODR/UDR (candidate=Loop-now, baseline=actual)")
        print(sep)
        print(String(format: "   ODR (Loop-now over-delivers at pre-low):   %6.4f", deliveryScores.weightedODR))
        print(String(format: "   UDR (Loop-now under-delivers at pre-high): %6.4f", deliveryScores.weightedUDR))
        print(String(format: "   ODR + UDR:                                 %6.4f", deliveryScores.primaryDeliveryScore))
        print(" Positive ODR → Loop-now would have caused worse lows vs what actually happened.")
        print(" Positive UDR → Loop-now would have left highs un-corrected longer vs reality.")
        print(ruler)
    }

    // MARK: – Actual delivery delta

    /// Total insulin delivered in [t_start, t_end) MINUS the scheduled basal
    /// that would have been delivered over the same window. Matches the
    /// semantics of `recommendedDeltaU` so the two are directly comparable.
    static func actualDeliveryDelta(
        doses: [EvalInsulinDose],
        from t_start: Date, to t_end: Date,
        basalSchedule: [AbsoluteScheduleValue<Double>]
    ) -> Double {
        let ts_start = t_start.timestamp()
        let ts_end   = t_end.timestamp()

        var actualU = 0.0
        for d in doses {
            let ds = d.startDate.timeIntervalSince1970
            let de = d.endDate.timeIntervalSince1970
            if ds >= ts_end { break }
            if de < ts_start { continue }
            let overlapStart = max(ds, ts_start)
            let overlapEnd   = min(de, ts_end)
            if overlapEnd <= overlapStart { continue }

            switch d.deliveryType {
            case .bolus:
                // Bolus delivered at startDate; include fully if startDate in window.
                if ts_start <= ds && ds < ts_end {
                    actualU += d.volume
                }
            case .basal:
                // Temp basal: pro-rate by overlap fraction.
                let duration = de - ds
                if duration > 0 {
                    actualU += d.volume * (overlapEnd - overlapStart) / duration
                }
            }
        }

        // Scheduled basal over the window — what would have been delivered
        // absent any overrides.
        var scheduledU = 0.0
        for entry in basalSchedule {
            let es = entry.startDate.timeIntervalSince1970
            let ee = entry.endDate.timeIntervalSince1970
            if es >= ts_end { break }
            if ee < ts_start { continue }
            let overlap = max(0.0, min(ee, ts_end) - max(es, ts_start))
            if overlap > 0 {
                scheduledU += entry.value * overlap / 3600.0
            }
        }

        return actualU - scheduledU
    }
}

private extension Date {
    func timestamp() -> TimeInterval { timeIntervalSince1970 }
}
