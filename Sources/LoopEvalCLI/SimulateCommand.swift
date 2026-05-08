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

    @Option(name: .long, help: "Local timezone identifier")
    var localTimezone: String?

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
            dynamicISFMode: candidateDynamicIsf,
            dynamicISFWindowHours: candidateDynamicIsfWindowHours,
            dynamicISFICEThreshold: candidateDynamicIsfIceThreshold,
            dynamicISFMaxBoost: candidateDynamicIsfMaxBoost
        )

        guard let baseURL = URL(string: nightscoutUrl) else { throw ValidationError("Invalid URL") }
        let client = NightscoutClient(baseURL: baseURL, apiSecret: apiSecret)
        let cache = try DataCache(cacheDir: cacheDir)
        let dataSource = NightscoutEvalDataSource(client: client, cache: cache, insulinType: baselinePreset)
        let engine = EvaluationEngine(dataSource: dataSource)

        printStderr("Fetching data... ")
        let data = try await engine.prefetchData(for: interval, config: baselineConfig)
        printStderr("done\n")

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
            }
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
