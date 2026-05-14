// SimulateCommand.swift — `loop-eval simulate` subcommand for closed-loop
// counterfactual simulation.
//
// Differs from `bench` in that the candidate's per-step decisions are made
// against its own counterfactual BG history (with feedback) rather than the
// actual CGM. This corrects the linearization's drift bias for aggressive
// candidates like IRC/dynamic-ISF where dose-delta impact compounds.

import ArgumentParser
import EvalCore
import Foundation

@available(macOS 10.15, macCatalyst 13, iOS 13, tvOS 13, watchOS 6, *)
struct SimulateCommand: AsyncParsableCommand {

    static let configuration = CommandConfiguration(
        commandName: "simulate",
        abstract: "Closed-loop counterfactual simulation (full feedback) — slower than bench but accurate for aggressive candidates."
    )

    @Option(name: .long, help: "Nightscout base URL")
    var nightscoutUrl: String

    @Option(name: .long, help: "Start date — ISO8601")
    var start: String

    @Option(name: .long, help: "End date   — ISO8601")
    var end: String

    @Option(name: .long, help: "Nightscout API secret (optional)")
    var apiSecret: String?

    @Option(name: .long, help: "Cache directory", transform: URL.init(fileURLWithPath:))
    var cacheDir: URL = URL(fileURLWithPath: NSHomeDirectory())
        .appendingPathComponent(".loop-eval/cache")

    @Option(name: .long, help: "Insulin model")
    var insulinType: String = "rapidActingAdult"

    @Option(name: .long, help: "Eval step (minutes, default 5)")
    var stepMinutes: Int = 5

    @Flag(name: .long, help: "Use integral RC for baseline")
    var integralRC: Bool = false

    @Flag(name: .long, help: "Disable Kalman smoothing")
    var noKalman: Bool = false

    @Option(name: .long, help: "Baseline ISF multiplier")
    var sensitivityMultiplier: Double = 1.0

    @Flag(name: .long, help: "Use asymmetric momentum on baseline")
    var asymmetricMomentum: Bool = false

    @Option(name: .long, help: "Baseline label")
    var baselineLabel: String = "Baseline"

    @Option(name: .long, help: "Candidate label")
    var candidateLabel: String = "Candidate"

    // Candidate-side flags (subset of bench's; can extend as needed)
    @Flag(name: .long, help: "Use integral RC for candidate")
    var candidateIntegralRC: Bool = false

    @Flag(name: .long, help: "Use asymmetric momentum for candidate")
    var candidateAsymmetricMomentum: Bool = false

    @Flag(name: .long, help: "Use hybrid momentum for candidate (linear regression on rises, fast EMA on drops)")
    var candidateHybridAsymmetricMomentum: Bool = false

    @Option(name: .long, help: "Candidate asymmetric-momentum alpha-slow (default 0.15)")
    var candidateMomentumAlphaSlow: Double = 0.15

    @Option(name: .long, help: "Candidate asymmetric-momentum alpha-fast (default 0.85)")
    var candidateMomentumAlphaFast: Double = 0.85

    @Option(name: .long, help: "Candidate ISF multiplier")
    var candidateSensitivityMultiplier: Double?

    @Option(name: .long, help: "Per-hour candidate ISF multipliers (24 csv)")
    var candidateIsfHourly: String?

    @Flag(name: .long, help: "Enable dynamic-ISF on candidate")
    var candidateDynamicIsf: Bool = false

    @Option(name: .long, help: "Dyn-ISF lookback (h)")
    var candidateDynamicIsfWindowHours: Double = 2.0

    @Option(name: .long, help: "Dyn-ISF ICE threshold")
    var candidateDynamicIsfIceThreshold: Double = 0.5

    @Option(name: .long, help: "Dyn-ISF max boost")
    var candidateDynamicIsfMaxBoost: Double = 0.5

    @Flag(name: .long, help: "Enable asymmetric dynamic-ISF cap-and-lock for candidate. Layered on top of in-algorithm dynamic-ISF: once it fires, locks in the suppressed dose as a cap for the lock-hours window, preventing IOB-echo over-doses.")
    var candidateAsymmetricDynamicIsf: Bool = false

    @Option(name: .long, help: "Asymmetric dynamic-ISF MAX lockout hours (default 2.0)")
    var candidateAsymmetricDynamicIsfLockHours: Double = 2.0

    @Option(name: .long, help: "Asymmetric dynamic-ISF MIN lockout hours — boost holds at least this long after trigger (default 0.5)")
    var candidateAsymmetricDynamicIsfMinLockHours: Double = 0.5

    @Option(name: .long, help: "Asymmetric dynamic-ISF: BG (mg/dL) above which boost releases immediately (default 250)")
    var candidateAsymmetricDynamicIsfReleaseHighBG: Double = 250.0

    @Option(name: .long, help: "Asymmetric dynamic-ISF: BG (mg/dL) above which boost releases if sustained (default 180)")
    var candidateAsymmetricDynamicIsfSustainedHighBG: Double = 180.0

    @Option(name: .long, help: "Asymmetric dynamic-ISF: minutes BG must stay above sustained-high threshold (default 30)")
    var candidateAsymmetricDynamicIsfSustainedHighMinutes: Double = 30.0

    @Option(name: .long, help: "Asymmetric dynamic-ISF: BG (mg/dL) below which boost will NOT release regardless of other conditions (default 120)")
    var candidateAsymmetricDynamicIsfKeepActiveBelowBG: Double = 120.0

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

    @Option(name: .long, help: "Smooth-boost mode: path to CSV with (time,score) for risk-score-driven smooth ISF boost. Replaces binary trigger.")
    var candidateSmoothBoostCsv: String?

    @Flag(name: .long, help: "Smooth-boost mode: compute risk score INLINE from counter-state at each step (uses baked-in RiskScoreModel coefficients). Mutually exclusive with --candidate-smooth-boost-csv.")
    var candidateSmoothBoostInline: Bool = false

    @Option(name: .long, help: "When smooth-boost-inline is on, also dump per-step features to this CSV path for diagnostic comparison against Python.")
    var candidateSmoothBoostFeaturesOut: String?

    @Option(name: .long, help: "Smooth-boost: score at/below this → no boost (default 0.4)")
    var candidateSmoothBoostLowAnchor: Double = 0.4

    @Option(name: .long, help: "Smooth-boost: score at/above this → max boost (default 0.6)")
    var candidateSmoothBoostHighAnchor: Double = 0.6

    @Option(name: .long, help: "Smooth-boost: max ISF boost magnitude (default 0.5 = +50%)")
    var candidateSmoothBoostMax: Double = 0.5

    @Option(name: .long, help: "Bidirectional smooth-boost: score at/below this → max negative boost (more aggressive ISF). Default 0 (disabled).")
    var candidateSmoothBoostDownLowAnchor: Double = 0.0

    @Option(name: .long, help: "Bidirectional smooth-boost: max ISF reduction when score is confidently low (default 0 = unidirectional)")
    var candidateSmoothBoostMaxDown: Double = 0.0

    @Option(name: .long, help: "Local timezone identifier")
    var localTimezone: String?

    @Option(name: .long, help: "Optional: load baseline dose-per-timestamp from a previously-saved trace JSON. When provided, skips the baseline simStepDose calls — useful for sweeps where many cells share an identical baseline.")
    var baselineFromTrace: String?

    @Option(name: .long, help: "Output trace JSON path (compatible with tir_methodology_report.py)")
    var traceOut: String

    mutating func run() async throws {
        let startDate = try parseISO8601Date(start)
        let endDate = try parseISO8601Date(end)
        guard endDate > startDate else { throw ValidationError("--end must be after --start") }
        let interval = DateInterval(start: startDate, end: endDate)
        let resolvedTz: TimeZone = localTimezone.flatMap { TimeZone(identifier: $0) } ?? .current

        let hourlyISF: [Double]?
        if let csv = candidateIsfHourly {
            let parts = csv.split(separator: ",").map { Double($0.trimmingCharacters(in: .whitespaces)) }
            guard parts.count == 24, parts.allSatisfy({ $0 != nil }) else {
                throw ValidationError("--candidate-isf-hourly requires exactly 24 comma-separated numbers")
            }
            hourlyISF = parts.map { $0! }
        } else { hourlyISF = nil }

        let baselinePreset = try parseInsulinType(insulinType)

        let baselineConfig = EvalConfig(
            evalStep: TimeInterval(stepMinutes) * 60,
            includeFutureInsulin: true,
            useIntegralRC: integralRC,
            kalmanSmoothing: !noKalman,
            sensitivityMultiplier: sensitivityMultiplier,
            localTimezone: resolvedTz,
            useAsymmetricMomentum: asymmetricMomentum
        )

        let candidateConfig = EvalConfig(
            evalStep: TimeInterval(stepMinutes) * 60,
            includeFutureInsulin: true,
            useIntegralRC: candidateIntegralRC || integralRC,
            kalmanSmoothing: !noKalman,
            sensitivityMultiplier: candidateSensitivityMultiplier ?? sensitivityMultiplier,
            sensitivityHourlyMultipliers: hourlyISF,
            localTimezone: resolvedTz,
            useAsymmetricMomentum: candidateAsymmetricMomentum || asymmetricMomentum,
            useHybridAsymmetricMomentum: candidateHybridAsymmetricMomentum,
            momentumAlphaSlow: candidateMomentumAlphaSlow,
            momentumAlphaFast: candidateMomentumAlphaFast,
            glucoseBasedApplicationFactor: candidateGbaf,
            gbafLowAnchor: candidateGbafLowAnchor,
            gbafHighAnchor: candidateGbafHighAnchor,
            gbafFactorLow: candidateGbafFactorLow,
            gbafFactorHigh: candidateGbafFactorHigh,
            dynamicISFMode: candidateDynamicIsf,
            dynamicISFWindowHours: candidateDynamicIsfWindowHours,
            dynamicISFICEThreshold: candidateDynamicIsfIceThreshold,
            dynamicISFMaxBoost: candidateDynamicIsfMaxBoost,
            asymmetricDynamicISF: candidateAsymmetricDynamicIsf,
            asymmetricDynamicISFLockHours: candidateAsymmetricDynamicIsfLockHours,
            asymmetricDynamicISFMinLockHours: candidateAsymmetricDynamicIsfMinLockHours,
            asymmetricDynamicISFReleaseHighBG: candidateAsymmetricDynamicIsfReleaseHighBG,
            asymmetricDynamicISFSustainedHighBG: candidateAsymmetricDynamicIsfSustainedHighBG,
            asymmetricDynamicISFSustainedHighMinutes: candidateAsymmetricDynamicIsfSustainedHighMinutes,
            asymmetricDynamicISFKeepActiveBelowBG: candidateAsymmetricDynamicIsfKeepActiveBelowBG
        )

        guard let baseURL = URL(string: nightscoutUrl) else { throw ValidationError("Invalid URL") }
        let client = NightscoutClient(baseURL: baseURL, apiSecret: apiSecret)
        let cache = try DataCache(cacheDir: cacheDir)
        let dataSource = NightscoutEvalDataSource(client: client, cache: cache, insulinType: baselinePreset)
        let engine = EvaluationEngine(dataSource: dataSource)

        printStderr("Fetching data... ")
        let data = try await engine.prefetchData(for: interval, config: baselineConfig)
        printStderr("done\n")

        // Load smooth-boost scores if provided.
        var smoothBoostScores: [(Date, Double)]? = nil
        if let csvPath = candidateSmoothBoostCsv {
            smoothBoostScores = try Self.loadScoresCSV(path: csvPath)
            printStderr("Loaded \(smoothBoostScores?.count ?? 0) smooth-boost scores from \(csvPath)\n")
        }

        // Load baseline dose cache if provided.
        var baselineDoseLookup: [(Date, Double)]? = nil
        if let tracePath = baselineFromTrace {
            baselineDoseLookup = try Self.loadBaselineDosesFromTrace(path: tracePath)
            printStderr("Loaded \(baselineDoseLookup?.count ?? 0) baseline doses from \(tracePath)\n")
        }

        printStderr("Running closed-loop simulation (sequential, ~10× slower than bench)...\n")
        let simResult = try await engine.simulateClosedLoop(
            data: data,
            interval: interval,
            baselineConfig: baselineConfig,
            candidateConfig: candidateConfig,
            baselineLabel: baselineLabel,
            candidateLabel: candidateLabel,
            progress: { f in
                let pct = Int(f * 100)
                printStderr("\rProgress: \(pct)%  ")
            },
            smoothBoostScores: smoothBoostScores,
            smoothBoostLowAnchor: candidateSmoothBoostLowAnchor,
            smoothBoostHighAnchor: candidateSmoothBoostHighAnchor,
            smoothBoostMaxBoost: candidateSmoothBoostMax,
            smoothBoostInline: candidateSmoothBoostInline,
            smoothBoostFeaturesOut: candidateSmoothBoostFeaturesOut,
            smoothBoostDownLowAnchor: candidateSmoothBoostDownLowAnchor,
            smoothBoostMaxBoostDown: candidateSmoothBoostMaxDown,
            baselineDoseLookup: baselineDoseLookup
        )
        printStderr("\rProgress: 100%\n")

        // Emit trace JSON in the same shape as bench --trace-out so the
        // existing python report script can consume it. Add a `closedLoop`
        // flag in the JSON so consumers can distinguish.
        try Self.writeTrace(
            simResult: simResult,
            data: data,
            to: URL(fileURLWithPath: traceOut)
        )
        printStderr("Closed-loop trace → \(traceOut)\n")
    }

    /// Load baseline (time, dose) pairs from a previously-emitted closed-loop
    /// trace JSON. Used to skip the baseline simStepDose call when many sweep
    /// cells share an identical baseline.
    static func loadBaselineDosesFromTrace(path: String) throws -> [(Date, Double)] {
        let url = URL(fileURLWithPath: (path as NSString).expandingTildeInPath)
        let data = try Data(contentsOf: url)
        struct Pred: Decodable { let t: String; let baselineDose: Double }
        struct Trace: Decodable { let predictions: [Pred] }
        let trace = try JSONDecoder().decode(Trace.self, from: data)
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let formatterNoFrac = ISO8601DateFormatter()
        formatterNoFrac.formatOptions = [.withInternetDateTime]
        var out: [(Date, Double)] = []
        out.reserveCapacity(trace.predictions.count)
        for p in trace.predictions {
            guard let date = formatter.date(from: p.t) ?? formatterNoFrac.date(from: p.t) else {
                continue
            }
            out.append((date, p.baselineDose))
        }
        out.sort { $0.0 < $1.0 }
        return out
    }

    /// Load (time, score) pairs from a CSV. Expects header row with `time` and
    /// `score` columns; ignores other columns. Times must be ISO-8601.
    static func loadScoresCSV(path: String) throws -> [(Date, Double)] {
        let url = URL(fileURLWithPath: (path as NSString).expandingTildeInPath)
        let text = try String(contentsOf: url, encoding: .utf8)
        let lines = text.split(separator: "\n", omittingEmptySubsequences: true)
        guard !lines.isEmpty else { return [] }
        let header = lines[0].split(separator: ",").map { String($0).trimmingCharacters(in: .whitespaces) }
        guard let timeIdx = header.firstIndex(of: "time"),
              let scoreIdx = header.firstIndex(of: "score") else {
            throw ValidationError("CSV must have 'time' and 'score' columns; got: \(header)")
        }
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let formatterNoFrac = ISO8601DateFormatter()
        formatterNoFrac.formatOptions = [.withInternetDateTime]
        var out: [(Date, Double)] = []
        out.reserveCapacity(lines.count)
        for line in lines.dropFirst() {
            let cells = line.split(separator: ",", omittingEmptySubsequences: false).map(String.init)
            guard cells.count > max(timeIdx, scoreIdx) else { continue }
            let timeStr = cells[timeIdx].trimmingCharacters(in: .whitespaces)
            let scoreStr = cells[scoreIdx].trimmingCharacters(in: .whitespaces)
            // Pandas writes either "2026-03-30 11:01:56" (no T) or with T.
            // Normalize to ISO format with T and Z if needed.
            var iso = timeStr.replacingOccurrences(of: " ", with: "T")
            if !iso.hasSuffix("Z") && !iso.contains("+") {
                iso += "Z"
            }
            guard let date = formatter.date(from: iso) ?? formatterNoFrac.date(from: iso),
                  let score = Double(scoreStr) else {
                continue
            }
            out.append((date, score))
        }
        out.sort { $0.0 < $1.0 }
        return out
    }

    static func writeTrace(
        simResult: ClosedLoopSimResult,
        data: PreloadedData,
        to url: URL
    ) throws {
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
        struct ActualSample: Codable { let t: String; let bg: Double }
        struct CounterSample: Codable { let t: String; let bg: Double }
        struct CurvePoint: Codable { let tMin: Double; let percentRemaining: Double; let percentDelivered: Double }
        struct Trace: Codable {
            let baselineLabel: String
            let candidateLabel: String
            let intervalStart: String
            let intervalEnd: String
            let activityDurationMinutes: Double
            let predictions: [Pred]
            let actual: [ActualSample]
            let counter: [CounterSample]   // closed-loop trajectory (NEW)
            let insulinActivityCurve: [CurvePoint]
            let closedLoop: Bool
        }

        let preds = simResult.steps.map {
            Pred(t: formatter.string(from: $0.t),
                 baselineDose: $0.baselineDose,
                 candidateDose: $0.candidateDose,
                 deltaDose: $0.deltaDose,
                 isf: $0.isf)
        }
        let actualOut = data.glucose.sorted { $0.startDate < $1.startDate }.map {
            ActualSample(t: formatter.string(from: $0.startDate),
                         bg: $0.quantity.doubleValue(for: mgdlUnit))
        }
        let counterOut = simResult.steps.map {
            CounterSample(t: formatter.string(from: $0.t), bg: $0.counterBG)
        }
        let insulinModel = data.therapyTimeline.insulinType.model
        let dur = insulinModel.effectDuration
        var curve: [CurvePoint] = []
        var τ: TimeInterval = 0
        while τ <= dur {
            let pr = insulinModel.percentEffectRemaining(at: τ)
            curve.append(CurvePoint(tMin: τ / 60.0, percentRemaining: pr, percentDelivered: 1.0 - pr))
            τ += 5 * 60
        }

        let trace = Trace(
            baselineLabel: simResult.baselineLabel,
            candidateLabel: simResult.candidateLabel,
            intervalStart: formatter.string(from: simResult.intervalStart),
            intervalEnd: formatter.string(from: simResult.intervalEnd),
            activityDurationMinutes: dur / 60.0,
            predictions: preds,
            actual: actualOut,
            counter: counterOut,
            insulinActivityCurve: curve,
            closedLoop: true
        )

        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted]
        let json = try encoder.encode(trace)
        try json.write(to: url)
    }
}
