// ForecastMatchCommand.swift — `loop-eval forecast-match` subcommand
//
// Evaluate Loop's decision-time forecast + dose recommendation at an EXPLICIT list
// of timestamps (the field's real Loop decision times, from devicestatus), on the
// raw native CGM history — no uniform grid, no Kalman resampling. This lets us
// compare the sim's forecast curve and dose against devicestatus.predicted.values /
// automaticDoseRecommendation at the SAME instant the real Loop decided, removing
// the ~5-min grid phase offset that otherwise floors the comparison at ~1.5 mg/dL.

import ArgumentParser
import EvalCore
import Foundation

@available(macOS 10.15, macCatalyst 13, iOS 13, tvOS 13, watchOS 6, *)
struct ForecastMatchCommand: AsyncParsableCommand {

    static let configuration = CommandConfiguration(
        commandName: "forecast-match",
        abstract: "Evaluate the decision-time forecast + dose at explicit timestamps (field decision times) for bit-level comparison against devicestatus."
    )

    @Option(name: .long, help: "Nightscout base URL")
    var nightscoutUrl: String

    @Option(name: .long, help: "Data window start (ISO8601). Must be >= ~16h before the earliest evaluated time so the insulin/glucose history is complete.")
    var start: String

    @Option(name: .long, help: "Data window end (ISO8601).")
    var end: String

    @Option(name: .long, help: "CSV file with one ISO8601 timestamp per line (header 't' optional) — the times to evaluate at (the field's decision times).")
    var timesCsv: String

    @Option(name: .long, help: "Output JSON path.")
    var out: String

    @Option(name: .long, help: "Nightscout API secret (optional)")
    var apiSecret: String?

    @Option(name: .long, help: "Cache directory for fetched Nightscout data",
            transform: URL.init(fileURLWithPath:))
    var cacheDir: URL = URL(fileURLWithPath: NSHomeDirectory()).appendingPathComponent(".loop-eval/cache")

    @Option(name: .long, help: "Insulin model (default rapidActingAdult)")
    var insulinType: String = "rapidActingAdult"

    @Flag(name: .long, help: "Use integral retrospective correction (default: standard RC).")
    var integralRC: Bool = false

    @Option(name: .long, help: "Auto-bolus application factor (default 0.4).")
    var applicationFactor: Double = 0.4

    @Flag(name: .long, help: "Glucose-based application factor (Loop GBAF): ramp AF from gbaf-factor-low (at gbaf-low-anchor) to gbaf-factor-high (at gbaf-high-anchor). Loop's default: 110/200, 0.20/0.80.")
    var gbaf: Bool = false
    @Option(name: .long, help: "GBAF low anchor mg/dL (Loop: targetLow+10).")
    var gbafLowAnchor: Double = 110
    @Option(name: .long, help: "GBAF high anchor mg/dL (Loop: 200).")
    var gbafHighAnchor: Double = 200
    @Option(name: .long, help: "GBAF factor at/below low anchor (Loop: 0.20).")
    var gbafFactorLow: Double = 0.20
    @Option(name: .long, help: "GBAF factor at/above high anchor (Loop: 0.80).")
    var gbafFactorHigh: Double = 0.80

    @Option(name: .long, help: "ISF multiplier (default 1.0).")
    var sensitivityMultiplier: Double = 1.0

    @Flag(name: .long, help: "Treat a temp basal still running at the prediction instant as ENDED at t (clean going-forward design). Default off = project the running temp forward as FieldLoop does (field-faithful).")
    var clipInProgressTempBasal: Bool = false

    @Flag(name: .customLong("apply-overrides"), inversion: .prefixedNo, help: "Apply Loop Temporary Overrides to the therapy timeline (basal ×f, ISF ÷f, CR ÷f, target ← override range). DEFAULT ON; pass --no-apply-overrides to ignore overrides.")
    var applyOverrides: Bool = true

    @Flag(name: .customLong("mid-absorption-isf"), inversion: .prefixedNo,
          help: "Mid-absorption ISF: re-evaluate ALL active IOB at the CURRENT sensitivity (current LoopAlgorithm default). Pass --no-mid-absorption-isf for the OLD/deployed-Loop behavior: each dose keeps the sensitivity in effect at its delivery time for its lifetime (matters when ISF changes mid-absorption, e.g. a Temporary Override).")
    var midAbsorptionIsf: Bool = true

    @Flag(name: .long, help: "Use deployed Loop's adaptive carb absorption (.adaptiveRateNonlinear: adaptiveAbsorptionRateEnabled=true, initialAbsorptionTimeOverrun=1.0). Off by default = the .nonlinear non-adaptive deployed default.")
    var adaptiveCarbAbsorption: Bool = false

    // Momentum knobs (for Loop-3.9.3-compatibility experiments). Defaults = LoopAlgorithm.
    @Option(name: .long, help: "Momentum projection duration (minutes). Default 15 (LoopAlgorithm). Loop 3.9.3 used 30.")
    var momentumDurationMin: Double = 15

    @Option(name: .long, help: "Momentum velocity cap (mg/dL/min). Default 4.0 (LoopAlgorithm/LoopKit since 2020). Pass a large value (e.g. 1000) to disable.")
    var momentumCap: Double = 4.0

    @Flag(name: .long, help: "Disable the gradual-transitions gate (>40 mg/dL jump suppresses momentum). The gate is a LoopAlgorithm addition NOT in Loop 3.9.3 — pass this to match 3.9.3.")
    var noGradualTransitionsGate: Bool = false

    @Option(name: .long, help: "Drop decision times whose latest CGM is older than this many minutes — off-cycle / user-triggered devicestatus uploads (manual bolus, carb log) that fall BETWEEN CGM readings, where real Loop does NOT issue an automatic dose. 0 = keep all (default). Typical: 1.5 to keep only fresh-CGM auto-dose cycles.")
    var maxCgmAgeMin: Double = 0

    @Flag(name: .long, help: "Convenience: Loop-3.9.3-compatible momentum = disable the gradual-transitions gate only. (Verified from LoopKit dev source: deployed Loop uses 15-min duration + 4 mg/dL/min cap — same as default — and NO gradual-transitions gate.)")
    var loop393Momentum: Bool = false

    struct OutRow: Codable {
        let t: String
        let eventualBG: Double?
        let iob: Double?
        let cob: Double?
        let recommendedBolus: Double?      // auto-bolus this cycle (app factor + floor)
        let recommendedManualBolus: Double?  // full correction (app factor 1.0, clamped) = devicestatus recommendedBolus
        let recommendedDeltaU: Double?
        let recommendedTempBasalRate: Double?
        let insulinEffect90: Double?       // insulin effect Δ at +90min (mg/dL)
        let rcEffect90: Double?            // retrospective-correction effect at +90min (mg/dL)
        let momentumEffect30: Double?      // momentum effect at +30min (mg/dL)
        let carbEffect360: Double?         // carb effect t→+6h (mg/dL)
        let insulinEffect360: Double?      // insulin effect t→+6h (mg/dL)
        let rcEffect360: Double?           // RC effect t→+6h (mg/dL)
        let currentDiscrepancy: Double?    // latest 30-min summed discrepancy (ICE−carb) the RC integrates
        let curve: [Double]                // full forecast curve, mg/dL, 5-min spaced from t
    }

    mutating func run() async throws {
        let startDate = try parseISO8601Date(start)
        let endDate   = try parseISO8601Date(end)
        guard endDate > startDate else { throw ValidationError("--end must be after --start") }
        let interval = DateInterval(start: startDate, end: endDate)
        let preset = try parseInsulinType(insulinType)

        // Read the timestamp list.
        let raw = try String(contentsOfFile: timesCsv, encoding: .utf8)
        var times: [Date] = []
        for line in raw.split(whereSeparator: { $0 == "\n" || $0 == "\r" }) {
            let s = line.trimmingCharacters(in: .whitespaces)
            if s.isEmpty || s.lowercased() == "t" { continue }
            let field = s.split(separator: ",").first.map(String.init) ?? s
            if let d = try? parseISO8601Date(field) { times.append(d) }
        }
        times = times.filter { $0 >= startDate && $0 <= endDate }.sorted()
        printStderr("Evaluating at \(times.count) timestamps\n")

        let durMin = momentumDurationMin   // deployed Loop = 15 (LoopKit dev momentumDuration); 30 only in stale master
        let gateThreshold: Double? = (loop393Momentum || noGradualTransitionsGate) ? nil : 40
        let config = EvalConfig(
            glucoseBasedApplicationFactor: gbaf,
            gbafLowAnchor: gbafLowAnchor,
            gbafHighAnchor: gbafHighAnchor,
            gbafFactorLow: gbafFactorLow,
            gbafFactorHigh: gbafFactorHigh,
            applicationFactor: applicationFactor,
            includeFutureInsulin: false,   // decision-time replay
            includeFutureCarbs: false,
            useIntegralRC: integralRC,
            kalmanSmoothing: false,        // raw native CGM (evaluate path uses data.glucose directly)
            clipInProgressTempBasal: clipInProgressTempBasal,
            useMidAbsorptionISF: midAbsorptionIsf,
            adaptiveCarbAbsorption: adaptiveCarbAbsorption,
            sensitivityMultiplier: sensitivityMultiplier,
            positiveVelocityCap: momentumCap,
            momentumProjectionMinutes: durMin,
            momentumGradualTransitionsThreshold: gateThreshold
        )
        printStderr("momentum: duration=\(durMin)min cap=\(momentumCap)mg/dL/min gate=\(gateThreshold.map { "\($0)" } ?? "OFF")\n")

        guard let baseURL = URL(string: nightscoutUrl) else {
            throw ValidationError("Invalid Nightscout URL: \(nightscoutUrl)")
        }
        let client = NightscoutClient(baseURL: baseURL, apiSecret: apiSecret)
        let cache  = try DataCache(cacheDir: cacheDir)
        let dataSource = NightscoutEvalDataSource(client: client, cache: cache, insulinType: preset, applyOverrides: applyOverrides)
        let engine = EvaluationEngine(dataSource: dataSource)

        printStderr("Fetching data...\n")
        let data = try await engine.prefetchData(for: interval, config: config)

        // CGM-aligned decision-time filter: deployed Loop auto-doses on CGM-reading
        // cycles, not on user-triggered devicestatus uploads (manual bolus / carb log)
        // that land between readings. Drop times whose latest CGM is staler than the
        // threshold so we don't replay an auto-dose on stale glucose.
        if maxCgmAgeMin > 0 {
            let g = data.glucose  // sorted ascending by startDate
            let before = times.count
            times = times.filter { t in
                guard let last = g.last(where: { $0.startDate <= t }) else { return false }
                return t.timeIntervalSince(last.startDate) <= maxCgmAgeMin * 60
            }
            printStderr("CGM-aligned filter: kept \(times.count)/\(before) decision times (max CGM age \(maxCgmAgeMin) min)\n")
        }

        let records = engine.forecastAtTimes(times, data: data, interval: interval, config: config)
        printStderr("Got \(records.count) forecast records\n")

        let mgdl = LoopUnit.milligramsPerDeciliter
        let fmt = ISO8601DateFormatter()
        fmt.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let rows = records.map { r in
            OutRow(
                t: fmt.string(from: r.evaluatedAt),
                eventualBG: r.predicted.last?.quantity.doubleValue(for: mgdl),
                iob: r.iob,
                cob: r.cob,
                recommendedBolus: r.recommendedBolus,
                recommendedManualBolus: r.recommendedManualBolus,
                recommendedDeltaU: r.recommendedDeltaU,
                recommendedTempBasalRate: r.recommendedTempBasalRate,
                insulinEffect90: r.insulinEffectΔ90,
                rcEffect90: r.rcEffect90,
                momentumEffect30: r.momentumEffect30,
                carbEffect360: r.carbEffect360,
                insulinEffect360: r.insulinEffect360,
                rcEffect360: r.rcEffect360,
                currentDiscrepancy: r.currentDiscrepancy,
                curve: r.predicted.map { $0.quantity.doubleValue(for: mgdl) }
            )
        }
        let enc = JSONEncoder()
        enc.outputFormatting = [.prettyPrinted]
        let json = try enc.encode(rows)
        try json.write(to: URL(fileURLWithPath: out))
        printStderr("Wrote \(rows.count) rows → \(out)\n")
    }
}
