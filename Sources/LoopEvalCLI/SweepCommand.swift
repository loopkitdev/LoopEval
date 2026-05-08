// SweepCommand.swift — `loop-eval sweep` subcommand for multi-candidate evaluation
//
// Bench compares one baseline vs one candidate. Sweep extends that to one baseline
// vs N candidates, prefetching data once, running baseline once, and running each
// candidate once. Outputs a CSV/JSON table of per-candidate metrics.
//
// Designed for hyperparameter searches (e.g., per-hour ISF block-CD): the outer
// driver (Python or shell) calls sweep with a JSON candidates file and reads the
// CSV output to pick the best candidate for the next round.

import ArgumentParser
import EvalCore
import Foundation

/// JSON shape for a single candidate variant.
struct SweepCandidateSpec: Codable {
    let label: String
    let isfHourly: [Double]?
    let sensitivityMultiplier: Double?
    let carbRatioMultiplier: Double?
    let basalRateMultiplier: Double?
    let useIntegralRC: Bool?
    let useAsymmetricMomentum: Bool?
    let positiveVelocityCap: Double?
    // GBAF settings
    let glucoseBasedApplicationFactor: Bool?
    let gbafLowAnchor: Double?
    let gbafHighAnchor: Double?
    let gbafFactorLow: Double?
    let gbafFactorHigh: Double?
    // Dynamic-ISF settings
    let dynamicISFMode: Bool?
    let dynamicISFWindowHours: Double?
    let dynamicISFICEThreshold: Double?
    let dynamicISFMaxBoost: Double?
}

@available(macOS 10.15, macCatalyst 13, iOS 13, tvOS 13, watchOS 6, *)
struct SweepCommand: AsyncParsableCommand {

    static let configuration = CommandConfiguration(
        commandName: "sweep",
        abstract: "Run one baseline + N candidates on the same data; emit per-candidate metrics.",
        discussion: """
        Reads candidates from a JSON file:

        [
          {"label": "00-04 ISF*1.10", "isfHourly": [1.1,1.1,1.1,1.1,1.0, ... 1.0]},
          {"label": "00-04 ISF*1.20", "isfHourly": [1.2,1.2,1.2,1.2,1.0, ... 1.0]},
          ...
        ]

        Output is CSV (default) or JSON, written to stdout.
        """
    )

    @Option(name: .long, help: "Nightscout base URL")
    var nightscoutUrl: String

    @Option(name: .long, help: "Start date — ISO8601")
    var start: String

    @Option(name: .long, help: "End date — ISO8601")
    var end: String

    @Option(name: .long, help: "Nightscout API secret (optional)")
    var apiSecret: String?

    @Option(name: .long, help: "Cache directory", transform: URL.init(fileURLWithPath:))
    var cacheDir: URL = URL(fileURLWithPath: NSHomeDirectory())
        .appendingPathComponent(".loop-eval/cache")

    @Option(name: .long, help: "Insulin model")
    var insulinType: String = "rapidActingAdult"

    @Option(name: .long, help: "Eval step in minutes (default: 5)")
    var stepMinutes: Int = 5

    @Flag(name: .long, help: "Use integral retrospective correction for the baseline")
    var integralRC: Bool = false

    @Flag(name: .long, help: "Disable Kalman smoothing")
    var noKalman: Bool = false

    @Flag(name: .long, help: "Exclude future-scheduled insulin")
    var noFutureInsulin: Bool = false

    @Option(name: .long, help: "Baseline ISF multiplier (default 1.0)")
    var sensitivityMultiplier: Double = 1.0

    @Option(name: .long, help: "Baseline CR multiplier (default 1.0)")
    var crMultiplier: Double = 1.0

    @Option(name: .long, help: "Baseline basal multiplier (default 1.0)")
    var basalMultiplier: Double = 1.0

    @Flag(name: .long, help: "Use asymmetric momentum on baseline")
    var asymmetricMomentum: Bool = false

    @Option(name: .long, help: "Path to candidates JSON file")
    var candidatesFile: String

    @Option(name: .long, help: "Local timezone (default: system)")
    var localTimezone: String?

    @Option(name: .long, help: "Output format: csv | json (default: csv)")
    var output: String = "csv"

    mutating func run() async throws {

        // Parse dates / timezone
        let startDate = try parseISO8601Date(start)
        let endDate = try parseISO8601Date(end)
        guard endDate > startDate else {
            throw ValidationError("--end must be after --start")
        }
        let interval = DateInterval(start: startDate, end: endDate)
        let resolvedTz: TimeZone = localTimezone.flatMap { TimeZone(identifier: $0) } ?? .current

        // Load candidates
        let candidatesURL = URL(fileURLWithPath: candidatesFile)
        let candidatesData = try Data(contentsOf: candidatesURL)
        let candidates = try JSONDecoder().decode([SweepCandidateSpec].self, from: candidatesData)
        guard !candidates.isEmpty else {
            throw ValidationError("Candidates file contains no entries")
        }
        for c in candidates {
            if let h = c.isfHourly, h.count != 24 {
                throw ValidationError("Candidate '\(c.label)': isfHourly must have 24 values")
            }
        }

        // Build baseline config
        let baselinePreset = try parseInsulinType(insulinType)
        let baselineConfig = EvalConfig(
            evalStep: TimeInterval(stepMinutes) * 60,
            includeFutureInsulin: !noFutureInsulin,
            useIntegralRC: integralRC,
            kalmanSmoothing: !noKalman,
            sensitivityMultiplier: sensitivityMultiplier,
            localTimezone: resolvedTz,
            carbRatioMultiplier: crMultiplier,
            basalRateMultiplier: basalMultiplier,
            useAsymmetricMomentum: asymmetricMomentum
        )

        // Data source
        guard let baseURL = URL(string: nightscoutUrl) else {
            throw ValidationError("Invalid Nightscout URL: \(nightscoutUrl)")
        }
        let client = NightscoutClient(baseURL: baseURL, apiSecret: apiSecret)
        let cache = try DataCache(cacheDir: cacheDir)
        let dataSource = NightscoutEvalDataSource(client: client, cache: cache, insulinType: baselinePreset)
        let engine = EvaluationEngine(dataSource: dataSource)

        // 1. Prefetch ONCE
        printStderr("Fetching data... ")
        let data = try await engine.prefetchData(for: interval, config: baselineConfig)
        printStderr("done\n")

        // 2. Baseline ONCE
        printStderr("Running baseline... ")
        let baselineResult = try await engine.runSweep(data: data, interval: interval, config: baselineConfig)
        printStderr("done\n")

        let smoother: KalmanSmoother? = noKalman ? nil : KalmanSmoother()
        let analyzer = EvaluationAnalyzer(smoother: smoother)
        let baselineScore = analyzer.analyze(result: baselineResult)

        // 3. Run each candidate
        struct Outcome {
            let label: String
            let primaryScore: Double
            let opr: Double
            let upr: Double
            let rmse: Double
            let odr: Double
            let udr: Double
            let idb: Double
            let rdb: Double
            let cost: Double
            let benefit: Double
            let ratio: Double
            // Simulation/TIR metrics
            let tirA: Double
            let tirC: Double
            let pctBelow70A: Double
            let pctBelow70C: Double
            let pctAbove180A: Double
            let pctAbove180C: Double
            let aucBelow70A: Double
            let aucBelow70C: Double
            let aucAbove180A: Double
            let aucAbove180C: Double
            let meanBGA: Double
            let meanBGC: Double
        }
        var outcomes: [Outcome] = []

        for (i, spec) in candidates.enumerated() {
            printStderr("Running candidate \(i+1)/\(candidates.count): \(spec.label)... ")

            let candidateConfig = EvalConfig(
                evalStep: TimeInterval(stepMinutes) * 60,
                includeFutureInsulin: !noFutureInsulin,
                useIntegralRC: spec.useIntegralRC ?? integralRC,
                kalmanSmoothing: !noKalman,
                sensitivityMultiplier: spec.sensitivityMultiplier ?? sensitivityMultiplier,
                sensitivityHourlyMultipliers: spec.isfHourly,
                localTimezone: resolvedTz,
                carbRatioMultiplier: spec.carbRatioMultiplier ?? crMultiplier,
                basalRateMultiplier: spec.basalRateMultiplier ?? basalMultiplier,
                positiveVelocityCap: spec.positiveVelocityCap,
                useAsymmetricMomentum: spec.useAsymmetricMomentum ?? asymmetricMomentum,
                glucoseBasedApplicationFactor: spec.glucoseBasedApplicationFactor ?? false,
                gbafLowAnchor: spec.gbafLowAnchor ?? 140.0,
                gbafHighAnchor: spec.gbafHighAnchor ?? 220.0,
                gbafFactorLow: spec.gbafFactorLow ?? 0.4,
                gbafFactorHigh: spec.gbafFactorHigh ?? 0.7,
                dynamicISFMode: spec.dynamicISFMode ?? false,
                dynamicISFWindowHours: spec.dynamicISFWindowHours ?? 2.0,
                dynamicISFICEThreshold: spec.dynamicISFICEThreshold ?? 0.5,
                dynamicISFMaxBoost: spec.dynamicISFMaxBoost ?? 0.5
            )

            let candidateResult = try await engine.runSweep(data: data, interval: interval, config: candidateConfig)
            let candidateScore = analyzer.analyze(result: candidateResult)

            let horizons = baselineScore.horizonMetrics.map { $0.horizon }
            let delivery = DeliveryScores.compute(
                baseline: baselineResult,
                candidate: candidateResult,
                horizons: horizons,
                actualGlucose: baselineResult.actual,
                evalStep: baselineConfig.evalStep,
                dangerLow: baselineConfig.dangerLow,
                dangerHigh: baselineConfig.dangerHigh
            )

            let cost = delivery.primaryDeliveryScore
            let benefit = delivery.weightedIDB + delivery.weightedRDB
            let ratio = cost > 0 ? benefit / cost : (benefit > 0 ? .infinity : 0)

            let sim = SimulationScores.compute(
                baseline: baselineResult,
                candidate: candidateResult,
                actualGlucose: baselineResult.actual,
                insulinModel: data.therapyTimeline.insulinType.model,
                sensitivity: data.therapyTimeline.sensitivity
            )

            outcomes.append(Outcome(
                label: spec.label,
                primaryScore: candidateScore.primaryScore,
                opr: candidateScore.weightedOverpredictionRisk,
                upr: candidateScore.weightedUnderpredictionRisk,
                rmse: candidateScore.weightedRMSE,
                odr: delivery.weightedODR,
                udr: delivery.weightedUDR,
                idb: delivery.weightedIDB,
                rdb: delivery.weightedRDB,
                cost: cost,
                benefit: benefit,
                ratio: ratio,
                tirA: sim.tirActual,
                tirC: sim.tirCandidate,
                pctBelow70A: sim.timeBelow70Actual,
                pctBelow70C: sim.timeBelow70Candidate,
                pctAbove180A: sim.timeAbove180Actual,
                pctAbove180C: sim.timeAbove180Candidate,
                aucBelow70A: sim.aucBelow70Actual,
                aucBelow70C: sim.aucBelow70Candidate,
                aucAbove180A: sim.aucAbove180Actual,
                aucAbove180C: sim.aucAbove180Candidate,
                meanBGA: sim.meanBGActual,
                meanBGC: sim.meanBGCandidate
            ))
            printStderr(String(format: "ratio=%.2f tir=%.1f→%.1f%% below70=%.1f→%.1f%% above180=%.1f→%.1f%%\n",
                               ratio, 100*sim.tirActual, 100*sim.tirCandidate,
                               100*sim.timeBelow70Actual, 100*sim.timeBelow70Candidate,
                               100*sim.timeAbove180Actual, 100*sim.timeAbove180Candidate))
        }

        // 4. Emit
        if output.lowercased() == "json" {
            let payload: [String: Any] = [
                "baseline": [
                    "primaryScore": baselineScore.primaryScore,
                    "opr": baselineScore.weightedOverpredictionRisk,
                    "upr": baselineScore.weightedUnderpredictionRisk,
                    "rmse": baselineScore.weightedRMSE,
                ],
                "candidates": outcomes.map { o in
                    [
                        "label": o.label,
                        "opr": o.opr, "upr": o.upr, "rmse": o.rmse,
                        "odr": o.odr, "udr": o.udr, "idb": o.idb, "rdb": o.rdb,
                        "cost": o.cost, "benefit": o.benefit, "ratio": o.ratio
                    ] as [String: Any]
                }
            ]
            let json = try JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted])
            print(String(data: json, encoding: .utf8)!)
        } else {
            // CSV
            print("label,opr,upr,rmse,odr,udr,idb,rdb,cost,benefit,ratio,tir_act,tir_cand,below70_act,below70_cand,above180_act,above180_cand,auc_below70_act,auc_below70_cand,auc_above180_act,auc_above180_cand,meanBG_act,meanBG_cand")
            for o in outcomes {
                print(String(format: "%@,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.0f,%.0f,%.0f,%.0f,%.1f,%.1f",
                             o.label, o.opr, o.upr, o.rmse,
                             o.odr, o.udr, o.idb, o.rdb,
                             o.cost, o.benefit, o.ratio,
                             o.tirA, o.tirC,
                             o.pctBelow70A, o.pctBelow70C,
                             o.pctAbove180A, o.pctAbove180C,
                             o.aucBelow70A, o.aucBelow70C,
                             o.aucAbove180A, o.aucAbove180C,
                             o.meanBGA, o.meanBGC))
            }
        }
    }
}
