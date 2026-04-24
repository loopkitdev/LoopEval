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

        // Drift analysis must NOT include future insulin: at each step we
        // simulate what Loop-now would have done given the information
        // available at that time. Seeing future boluses would inflate IOB
        // and systematically suppress Loop-now's recommendations.
        let config = EvalConfig(
            evalStep: TimeInterval(stepMinutes) * 60,
            includeFutureInsulin: false,
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

        // Three-way comparison: pump-side Loop vs Loop-now vs actual
        printStderr("Fetching pump-side Loop decisions (devicestatus)...\n")
        let decisions = try await Self.fetchPumpDecisions(
            client: client, from: startDate, to: endDate
        )
        let pumpCompare = Self.comparePumpDecisions(
            decisions: decisions,
            predictions: candidateResult.predictions,
            basalSchedule: basalSchedule,
            syntheticActual: syntheticPredictions,
            evalStep: evalStep
        )
        Self.printPumpComparison(pumpCompare)

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

    /// Insulin delivered in [t_start, t_end) relative to scheduled basal.
    /// Matches the semantics of `recommendedDeltaU`:
    ///   deltaU = bolus + (tempRate - scheduledRate) × evalStep/3600
    ///
    /// Only temp-basal-covered time contributes to the basal delta; for windows
    /// not covered by an explicit temp basal record, the pump was running
    /// scheduled basal and the delta is zero. Nightscout does not emit treatment
    /// records for pure scheduled-basal time, so uncovered intervals must not
    /// be charged against scheduled (doing so produces ~−1 U/hr phantom
    /// underdelivery for every uncovered hour).
    ///
    /// Manual (user-entered) boluses are excluded: Loop-now's simulated
    /// recommendation only covers automatic action, so manual boluses would
    /// only appear on the actual side and bias the comparison. We treat manual
    /// boluses as "given in both worlds" — they cancel out.
    static func actualDeliveryDelta(
        doses: [EvalInsulinDose],
        from t_start: Date, to t_end: Date,
        basalSchedule: [AbsoluteScheduleValue<Double>]
    ) -> Double {
        let ts_start = t_start.timestamp()
        let ts_end   = t_end.timestamp()

        var delta = 0.0
        for d in doses {
            let ds = d.startDate.timeIntervalSince1970
            let de = d.endDate.timeIntervalSince1970
            if ds >= ts_end { break }
            if de <= ts_start { continue }

            switch d.deliveryType {
            case .bolus:
                // Exclude manual boluses — they're "external input" assumed
                // identical in both sides of the comparison.
                guard d.automatic else { continue }
                // Bolus: fully attributed to the window containing its startDate.
                if ts_start <= ds && ds < ts_end {
                    delta += d.volume
                }
            case .basal:
                // Temp basal: contributes (tempRate - scheduledRate) × overlap.
                let duration = de - ds
                guard duration > 0 else { continue }
                let tempRate = d.volume / (duration / 3600.0)   // U/hr
                let overlapStart = max(ds, ts_start)
                let overlapEnd   = min(de, ts_end)
                let overlapSec = overlapEnd - overlapStart
                if overlapSec <= 0 { continue }

                let midpoint = Date(timeIntervalSince1970: (overlapStart + overlapEnd) / 2)
                let scheduledRate = Self.scheduledRate(at: midpoint, schedule: basalSchedule)
                delta += (tempRate - scheduledRate) * (overlapSec / 3600.0)
            }
        }
        return delta
    }

    /// Scheduled basal rate (U/hr) at a specific time.
    private static func scheduledRate(
        at t: Date,
        schedule: [AbsoluteScheduleValue<Double>]
    ) -> Double {
        if let entry = schedule.first(where: { $0.startDate <= t && $0.endDate > t }) {
            return entry.value
        }
        // Fall back to the closest prior entry if the lookup falls between
        // expanded schedule segments (shouldn't happen in practice).
        return schedule.last(where: { $0.startDate <= t })?.value
            ?? schedule.first?.value ?? 0
    }

    // MARK: – Pump-side Loop comparison

    /// One cycle of the pump-side Loop's decision, extracted from a
    /// Nightscout devicestatus record. We use `enacted` (what actually hit
    /// the pump) rather than `automaticDoseRecommendation` (what Loop said
    /// to do) because the latter is only serialised when a correction was
    /// recommended — carb-triggered and other auto-boluses are missing.
    struct PumpDecision {
        let timestamp: Date
        let autoBolus: Double      // enacted.bolusVolume (actually delivered)
        let enactedRate: Double?   // enacted.rate (U/hr); nil = no temp enacted
    }

    struct PumpComparison {
        let matchedSteps: Int
        let totalSteps: Int
        let pumpNetDelta: Double
        let nowNetDelta: Double
        let actualNetDelta: Double
        let nowOverPumpSteps: Int
        let nowUnderPumpSteps: Int
        let pumpOverActualSteps: Int
        let pumpUnderActualSteps: Int
    }

    static func fetchPumpDecisions(
        client: NightscoutClient,
        from start: Date,
        to end: Date
    ) async throws -> [PumpDecision] {
        // Pad by 5 min on each side so the first/last eval steps have a
        // matching devicestatus record.
        let statuses = try await client.fetchDeviceStatus(
            from: start.addingTimeInterval(-300),
            to: end.addingTimeInterval(300)
        )
        let fmt = ISO8601DateFormatter()
        fmt.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let fmtNoFrac = ISO8601DateFormatter()
        fmtNoFrac.formatOptions = [.withInternetDateTime]

        var out: [PumpDecision] = []
        out.reserveCapacity(statuses.count)
        for s in statuses {
            guard let loop = s.loop else { continue }
            let tsStr = loop.timestamp ?? s.created_at
            let ts = fmt.date(from: tsStr) ?? fmtNoFrac.date(from: tsStr)
            guard let t = ts else { continue }
            let autoBolus = loop.enacted?.bolusVolume ?? 0
            let enactedRate = loop.enacted?.rate
            out.append(PumpDecision(timestamp: t, autoBolus: autoBolus, enactedRate: enactedRate))
        }
        let sorted = out.sorted { $0.timestamp < $1.timestamp }

        // Loop sometimes uploads two devicestatus records per cycle: a
        // pre-dose one (predicted + recommendation, no `enacted`) and a
        // post-dose one (adds `enacted` after pump ACK). Nightscout viewers
        // show the later/enacted one. When two records sit within 60s of
        // each other, keep the one carrying enacted data (or, if both or
        // neither, the later one).
        var deduped: [PumpDecision] = []
        deduped.reserveCapacity(sorted.count)
        for d in sorted {
            if let last = deduped.last,
               d.timestamp.timeIntervalSince(last.timestamp) < 60 {
                let lastHasEnacted = last.enactedRate != nil
                let newHasEnacted  = d.enactedRate != nil
                if newHasEnacted || !lastHasEnacted {
                    deduped[deduped.count - 1] = d   // replace with later/enacted
                }
                // else: keep the earlier one (it has enacted, new one doesn't)
            } else {
                deduped.append(d)
            }
        }
        return deduped
    }

    /// Find the decision with timestamp closest to `t`, within `tolerance`.
    /// Binary search over the ascending-sorted `decisions` array.
    static func closestDecision(
        to t: Date,
        in decisions: [PumpDecision],
        tolerance: TimeInterval
    ) -> PumpDecision? {
        guard !decisions.isEmpty else { return nil }
        // Binary search for the first decision with timestamp >= t.
        var lo = 0, hi = decisions.count
        while lo < hi {
            let mid = (lo + hi) / 2
            if decisions[mid].timestamp < t { lo = mid + 1 }
            else { hi = mid }
        }
        // Candidates: decisions[lo-1] and decisions[lo]. Pick whichever is closer.
        var best: PumpDecision?
        var bestDist = TimeInterval.greatestFiniteMagnitude
        if lo > 0 {
            let d = decisions[lo - 1]
            let dist = abs(d.timestamp.timeIntervalSince(t))
            if dist < bestDist { best = d; bestDist = dist }
        }
        if lo < decisions.count {
            let d = decisions[lo]
            let dist = abs(d.timestamp.timeIntervalSince(t))
            if dist < bestDist { best = d; bestDist = dist }
        }
        return bestDist <= tolerance ? best : nil
    }

    static func comparePumpDecisions(
        decisions: [PumpDecision],
        predictions: [PredictionRecord],
        basalSchedule: [AbsoluteScheduleValue<Double>],
        syntheticActual: [PredictionRecord],
        evalStep: TimeInterval
    ) -> PumpComparison {
        var matched = 0
        var pumpSum = 0.0, nowSum = 0.0, actualSum = 0.0
        var nowOverPump = 0, nowUnderPump = 0
        var pumpOverActual = 0, pumpUnderActual = 0
        let tol = evalStep / 2

        for (i, p) in predictions.enumerated() {
            guard let pd = closestDecision(
                to: p.evaluatedAt, in: decisions, tolerance: tol
            ) else { continue }

            let schedRate = scheduledRate(at: p.evaluatedAt, schedule: basalSchedule)
            // Pump Loop's per-cycle ΔU = auto_bolus + (enactedRate − schedRate) × evalStep/3600.
            // If no temp was enacted this cycle, the rate in force is whatever
            // was running before — conservatively treat as scheduled (Δ=0).
            let pumpDelta = pd.autoBolus +
                ((pd.enactedRate ?? schedRate) - schedRate) * evalStep / 3600
            pumpSum += pumpDelta

            if let nowDelta = p.recommendedDeltaU {
                nowSum += nowDelta
                let diff = nowDelta - pumpDelta
                if diff >  0.01 { nowOverPump  += 1 }
                if diff < -0.01 { nowUnderPump += 1 }
            }
            if i < syntheticActual.count,
               let actDelta = syntheticActual[i].recommendedDeltaU {
                actualSum += actDelta
                let diff = pumpDelta - actDelta
                if diff >  0.01 { pumpOverActual  += 1 }
                if diff < -0.01 { pumpUnderActual += 1 }
            }
            matched += 1
        }

        return PumpComparison(
            matchedSteps: matched,
            totalSteps: predictions.count,
            pumpNetDelta: pumpSum,
            nowNetDelta: nowSum,
            actualNetDelta: actualSum,
            nowOverPumpSteps: nowOverPump,
            nowUnderPumpSteps: nowUnderPump,
            pumpOverActualSteps: pumpOverActual,
            pumpUnderActualSteps: pumpUnderActual
        )
    }

    static func printPumpComparison(_ c: PumpComparison) {
        let ruler = String(repeating: "━", count: 76)
        let sep   = String(repeating: "─", count: 76)

        print(ruler)
        print(" Three-way comparison: pump-side Loop vs Loop-now vs actual")
        print(sep)
        print(String(format: "   Steps matched to devicestatus: %d / %d", c.matchedSteps, c.totalSteps))
        print(sep)
        print("   Net ΔU over matched steps (U, vs scheduled basal)")
        print(String(format: "     Pump-side Loop (auto only):  %+.2f", c.pumpNetDelta))
        print(String(format: "     Loop-now       (auto only):  %+.2f", c.nowNetDelta))
        print(String(format: "     Actual delivery (auto only): %+.2f", c.actualNetDelta))
        print(sep)
        print("   Per-step agreement")
        let overPct  = 100.0 * Double(c.nowOverPumpSteps)  / Double(max(1, c.matchedSteps))
        let underPct = 100.0 * Double(c.nowUnderPumpSteps) / Double(max(1, c.matchedSteps))
        print(String(format: "     Loop-now > pump Loop:   %4d  (%.1f%%)", c.nowOverPumpSteps, overPct))
        print(String(format: "     Loop-now < pump Loop:   %4d  (%.1f%%)", c.nowUnderPumpSteps, underPct))
        let pOverPct  = 100.0 * Double(c.pumpOverActualSteps)  / Double(max(1, c.matchedSteps))
        let pUnderPct = 100.0 * Double(c.pumpUnderActualSteps) / Double(max(1, c.matchedSteps))
        print(String(format: "     Pump Loop > actual:     %4d  (%.1f%%)  (user's enacted != recommended)", c.pumpOverActualSteps, pOverPct))
        print(String(format: "     Pump Loop < actual:     %4d  (%.1f%%)", c.pumpUnderActualSteps, pUnderPct))
        print(" If pump-Loop and actual diverge, either the pump rejected some")
        print(" recommendation or devicestatus/treatments are out of sync.")
        print(ruler)
    }
}

private extension Date {
    func timestamp() -> TimeInterval { timeIntervalSince1970 }
}
