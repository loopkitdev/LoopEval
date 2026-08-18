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
import LoopAlgorithm

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

    @Option(name: .long, help: "CSV file with one ISO8601 timestamp per line (header 't' optional) — the times to evaluate at (the field's decision times). Optional when --decisions-from-cgm is set.")
    var timesCsv: String?

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

    @Flag(name: .long, help: "Apply the deployed-LoopKit integral-correction clamp to IRC (only with --integral-rc). ON = faithful to deployed Loop-main.")
    var integralRCClamp: Bool = false

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

    @Flag(name: .customLong("clip-in-progress-temp-basal"), inversion: .prefixedNo, help: "Treat a temp basal still running at the prediction instant as ENDED at t (only elapsed counts; scheduled resumes after). DEFAULT ON — matches deployed Loop-main (trims non-bolus doses to basalDosingEnd=now() before forecasting). Pass --no-clip-in-progress-temp-basal to project forward (reproduces the untruncated recorded display forecast).")
    var clipInProgressTempBasal: Bool = true

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

    @Flag(name: .customLong("legacy-basal-iob"), help: "Deployed-Loop-main basal IOB: reproduce the delta-quantized basal-IOB \"ripple\" (pre-PR#35) that deployed Loop main still has and the LoopAlgorithm package fixed. Class-1 emulation flag for Loop-main forecast-matching.")
    var legacyBasalIob: Bool = false

    @Option(name: .long, help: "Drop decision times whose latest CGM is older than this many minutes — off-cycle / user-triggered devicestatus uploads (manual bolus, carb log) that fall BETWEEN CGM readings, where real Loop does NOT issue an automatic dose. 0 = keep all (default). Typical: 1.5 to keep only fresh-CGM auto-dose cycles.")
    var maxCgmAgeMin: Double = 0

    @Option(name: .long, help: "Outages CSV (start,end,... ISO8601 UTC header row) — drop decision times that fall inside a pump-outage / pod-off interval, where the loop cannot run (no pump to dose). Same CSV the outcome-scoring disruption mask uses (loopeval_analysis.outage from-nightscout).")
    var outagesCsv: String?

    @Flag(name: .long, help: "Convenience: Loop-3.9.3-compatible momentum = disable the gradual-transitions gate only. (Verified from LoopKit dev source: deployed Loop uses 15-min duration + 4 mg/dL/min cap — same as default — and NO gradual-transitions gate.)")
    var loop393Momentum: Bool = false

    @Option(name: .long, help: "Carb-revisions overlay JSON (from reconstruct_carb_history.py): splice edited carb entries into their as-seen revision sequences so replay matches what the deployed Loop saw at each moment (fixes edited-entry phantom COB). Default: use cached final grams from original entry time.")
    var carbRevisionsJson: String?

    @Option(name: .long, help: "Override-targets overlay JSON (from override_targets.py): fill named-preset override correction ranges (+multiplier) from devicestatus, which the NS treatment omits. Use for hands-on replay of users with overrides.")
    var overrideTargetsJson: String?

    @Option(name: .long, help: "Debug: export the EXACT decision-time LoopPredictionInput our engine builds at this ISO time, in deployed-LoopKit fixture JSON format (to --dump-loop-input-path), then exit. Lets the LoopWorkspace harness run the identical input through the actual deployed Loop.")
    var dumpLoopInputAt: String?

    @Option(name: .long, help: "Output path for --dump-loop-input-at.")
    var dumpLoopInputPath: String?

    @Flag(name: .long, help: "Derive decision times from the CGM samples themselves — one automatic dosing decision per new CGM reading — instead of the field devicestatus timestamps in --times-csv. This is the correct trigger model: the loop runs ONLY after a new CGM, never on user-triggered uploads (carb log / manual bolus) that land between readings. Overrides --times-csv and --max-cgm-age-min.")
    var decisionsFromCgm: Bool = false

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
        InsulinMathCompat.useLegacyBasalRippleIOB = legacyBasalIob
        let startDate = try parseISO8601Date(start)
        let endDate   = try parseISO8601Date(end)
        guard endDate > startDate else { throw ValidationError("--end must be after --start") }
        let interval = DateInterval(start: startDate, end: endDate)
        let preset = try parseInsulinType(insulinType)

        // Decision times. Default: read the field's devicestatus timestamps from
        // --times-csv. With --decisions-from-cgm: derive them from the CGM samples
        // instead (set after prefetch below) — one decision per new CGM reading.
        var times: [Date] = []
        if !decisionsFromCgm {
            guard let timesCsv else {
                throw ValidationError("--times-csv is required unless --decisions-from-cgm is set")
            }
            let raw = try String(contentsOfFile: timesCsv, encoding: .utf8)
            for line in raw.split(whereSeparator: { $0.isNewline }) {
                let s = line.trimmingCharacters(in: .whitespaces)
                if s.isEmpty || s.lowercased() == "t" { continue }
                let field = s.split(separator: ",").first.map(String.init) ?? s
                if let d = try? parseISO8601Date(field) { times.append(d) }
            }
            times = times.filter { $0 >= startDate && $0 <= endDate }.sorted()
            printStderr("Evaluating at \(times.count) timestamps\n")
        }

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
            // With --times-csv the evaluation instants ARE the field's recorded
            // dosingDecision timestamps, so anchor the forecast on them directly rather
            // than on the lastGlucose+7s estimate of `now`. --decisions-from-cgm derives
            // the times from CGM samples instead, where the estimate is all we have.
            decisionTimesAreAuthoritative: !decisionsFromCgm,
            useIntegralRC: integralRC,
            useIntegralRCClamp: integralRCClamp,
            kalmanSmoothing: false,        // raw native CGM (evaluate path uses data.glucose directly)
            clipInProgressTempBasal: clipInProgressTempBasal,
            useMidAbsorptionISF: midAbsorptionIsf,
            adaptiveCarbAbsorption: adaptiveCarbAbsorption,
            carbRevisionsPath: carbRevisionsJson,
            overrideTargetsPath: overrideTargetsJson,
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

        // CGM-driven decision times: one automatic dosing decision per CGM sample.
        // The loop runs ONLY after a new CGM reading — never on user-triggered
        // devicestatus uploads (carb log / manual bolus) that land between readings,
        // which would otherwise replay a spurious auto-bolus on a just-logged carb
        // before its covering manual bolus is in IOB.
        if decisionsFromCgm {
            times = data.glucose.map { $0.startDate }
                .filter { $0 >= startDate && $0 <= endDate }
                .sorted()
            printStderr("Decisions from CGM: \(times.count) CGM samples in window\n")
        }

        // CGM-aligned decision-time filter: deployed Loop auto-doses on CGM-reading
        // cycles, not on user-triggered devicestatus uploads (manual bolus / carb log)
        // that land between readings. Drop times whose latest CGM is staler than the
        // threshold so we don't replay an auto-dose on stale glucose.
        if maxCgmAgeMin > 0 && !decisionsFromCgm {
            let g = data.glucose  // sorted ascending by startDate
            let before = times.count
            times = times.filter { t in
                guard let last = g.last(where: { $0.startDate <= t }) else { return false }
                return t.timeIntervalSince(last.startDate) <= maxCgmAgeMin * 60
            }
            printStderr("CGM-aligned filter: kept \(times.count)/\(before) decision times (max CGM age \(maxCgmAgeMin) min)\n")
        }

        // Pod-outage filter: the loop cannot run while the pod is done and no new
        // pod is applied (no pump to dose). Drop decision times inside any outage
        // interval — the same data-level mask the outcome scorer uses.
        if let outPath = outagesCsv {
            let rawOut = try String(contentsOfFile: outPath, encoding: .utf8)
            var intervals: [(Date, Date)] = []
            for line in rawOut.split(whereSeparator: { $0.isNewline }) {
                let f = line.split(separator: ",", omittingEmptySubsequences: false).map { $0.trimmingCharacters(in: .whitespaces) }
                guard f.count >= 2, f[0].lowercased() != "start",
                      let a = try? parseISO8601Date(f[0]), let b = try? parseISO8601Date(f[1]) else { continue }
                intervals.append((a, b))
            }
            let before = times.count
            times = times.filter { t in !intervals.contains { $0.0 <= t && t <= $0.1 } }
            printStderr("Outage filter: kept \(times.count)/\(before) decision times (\(intervals.count) outage intervals)\n")
        }

        // Debug: export the exact decision-time LoopPredictionInput at a target time.
        if let atStr = dumpLoopInputAt, let outPath = dumpLoopInputPath {
            let target = try parseISO8601Date(atStr)
            guard let t = times.min(by: { abs($0.timeIntervalSince(target)) < abs($1.timeIntervalSince(target)) }) else {
                throw ValidationError("no decision times to match --dump-loop-input-at")
            }
            // InsulinType raw (LoopKit): novolog=0, humalog=1, apidra=2, fiasp=3, lyumjev=4.
            let itRaw: Int = insulinType.lowercased().contains("fiasp") ? 3
                : insulinType.lowercased().contains("lyumjev") ? 4 : 0
            guard let json = engine.loopPredictionInputJSON(
                at: t, data: data, config: config, insulinTypeRaw: itRaw, useIntegralRC: integralRC) else {
                throw ValidationError("could not build input at \(t)")
            }
            try json.write(to: URL(fileURLWithPath: outPath))
            printStderr("Dumped LoopPredictionInput at \(ISO8601DateFormatter().string(from: t)) → \(outPath)\n")
            return
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
