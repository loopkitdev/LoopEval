// ISFRollingCommand.swift — `loop-eval isf-rolling` subcommand
//
// Rolling-window quantile-ISF estimator. Computes the τ=0.10 ISF estimate
// over sliding windows of the full dataset, producing a time series suitable
// for drift detection, periodogram analysis, and visual inspection.

import ArgumentParser
import EvalCore
import Foundation
import LoopAlgorithm

public struct DailyTDDPoint: Sendable {
    public var dayStart: Date
    public var dayEnd: Date
    public var tdd: Double  // units delivered in the day
}

struct ISFRollingCommand: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "isf-rolling",
        abstract: "Rolling-window quantile-ISF time series.",
        discussion: """
        Uses quantile regression at τ=0.10 (default) on sliding windows of
        the (activity, v_cgm) scatter. Each window emits one ISF estimate
        plus optional bootstrap 95% CI. Output is CSV and/or HTML — feed the
        CSV into a periodogram for hormonal / weekly / drift analysis.
        """
    )

    @Option(name: .long, help: "Nightscout base URL")
    var nightscoutUrl: String

    @Option(name: .long, help: "Start date YYYY-MM-DD (local time, inclusive)")
    var start: String

    @Option(name: .long, help: "End date YYYY-MM-DD (local time, exclusive)")
    var end: String

    @Option(name: .long, help: "Insulin model: rapidActingAdult | rapidActingChild | fiasp | lyumjev | afrezza")
    var insulinType: String = "rapidActingAdult"

    @Option(name: .long, help: "Nightscout API secret (if auth required)")
    var apiSecret: String?

    @Option(name: .long, help: "Cache directory path")
    var cacheDirPath: String = NSHomeDirectory() + "/.loop-eval/cache"

    @Option(name: .long, help: "Rolling window width (days)")
    var windowDays: Double = 7

    @Option(name: .long, help: "Step between window centers (days)")
    var stepDays: Double = 1

    @Option(name: .long, help: "Quantile τ used for the fit (default 0.10)")
    var quantile: Double = 0.10

    @Option(name: .long, help: "Minimum samples required in a window")
    var minSamples: Int = 100

    @Option(name: .long, help: "Bootstrap resamples for 95% CI (0 = skip; 200 gives tight CIs, slower)")
    var bootstrap: Int = 0

    @Option(name: .long, help: "Bootstrap seed (deterministic resampling)")
    var bootstrapSeed: UInt64 = 42

    @Option(name: .long, help: "Reference BG (mg/dL) for log-scale ISF output (default 150)")
    var logReferenceBg: Double = 150

    @Option(name: .long, help: "Minimum |v_insulin| to keep a sample (mg/dL/min)")
    var minInsulinVelocity: Double = 0.05

    @Option(name: .long, help: "Drop samples with BG below this (mg/dL). Excludes low-BG rescue-carb contamination. Default 80.")
    var bgMin: Double = 80

    @Option(name: .long, help: "Drop samples with BG at/above this (mg/dL). Excludes sensor clipping at 400. Default 395.")
    var bgMax: Double = 395

    @Option(name: .long, help: "IANA timezone (e.g. America/Chicago). Default: system local.")
    var timezone: String?

    @Option(name: .long, help: "Replace configured ISF schedule with a single constant value (mg/dL/U)")
    var overrideIsf: Double?

    @Option(name: .long, help: "Write CSV time series to this path")
    var csv: String?

    @Option(name: .long, help: "Write HTML report to this path")
    var html: String?

    func run() async throws {
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

        guard let baseURL = URL(string: nightscoutUrl) else {
            throw ValidationError("Invalid Nightscout URL: \(nightscoutUrl)")
        }

        let preset = try parseInsulinType(insulinType)
        let config = EvalConfig()

        let client     = NightscoutClient(baseURL: baseURL, apiSecret: apiSecret)
        let cache      = try DataCache(cacheDir: URL(fileURLWithPath: cacheDirPath))
        let dataSource = NightscoutEvalDataSource(client: client, cache: cache,
                                                  insulinType: preset)
        let engine     = EvaluationEngine(dataSource: dataSource)

        printStderr("Fetching data...")
        let t0 = Date()
        let preloadedRaw = try await engine.prefetchData(for: interval, config: config)
        printStderr(String(format: " done (%.1fs)\n", Date().timeIntervalSince(t0)))

        // Optional ISF override — same pattern as isf-explore. Long windows
        // with multi-entry ISF schedules hit a LoopAlgorithm performance cliff,
        // so override-isf is effectively required beyond ~2 months.
        let preloaded: PreloadedData
        if let isfValue = overrideIsf {
            let q = LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: isfValue)
            let first = preloadedRaw.therapyTimeline.sensitivity.first
            let last  = preloadedRaw.therapyTimeline.sensitivity.last
            let startDate = first?.startDate ?? interval.start
            let endDate   = last?.endDate   ?? interval.end
            let overrideSched = [AbsoluteScheduleValue(
                startDate: startDate, endDate: endDate, value: q
            )]
            let th = preloadedRaw.therapyTimeline
            let overrideTherapy = TherapySettings(
                basal: th.basal,
                sensitivity: overrideSched,
                carbRatio: th.carbRatio,
                target: th.target,
                suspendThreshold: th.suspendThreshold,
                maxBolus: th.maxBolus,
                maxBasalRate: th.maxBasalRate,
                insulinType: th.insulinType
            )
            preloaded = PreloadedData(
                glucose: preloadedRaw.glucose,
                doses: preloadedRaw.doses,
                carbs: preloadedRaw.carbs,
                therapyTimeline: overrideTherapy
            )
            printStderr(String(format: "  ⚠ ISF override active: %.1f mg/dL/U\n", isfValue))
        } else {
            preloaded = preloadedRaw
        }

        printStderr("Computing ISFSamples across full window...")
        let t1 = Date()
        let options = ISFExploreOptions(
            minInsulinVelocity: minInsulinVelocity,
            timezone: timezone,
            bgMin: bgMin,
            bgMax: bgMax
        )
        let explored = ISFExplorer.analyze(data: preloaded, interval: interval, options: options)
        printStderr(String(format: " done (%.1fs, %d samples)\n",
                           Date().timeIntervalSince(t1), explored.samples.count))

        let rollingCfg = ISFRollingConfig(
            windowDays: windowDays,
            stepDays: stepDays,
            quantile: quantile,
            minSamples: minSamples,
            bootstrapN: bootstrap,
            bootstrapSeed: bootstrapSeed
        )

        printStderr(String(
            format: "Rolling quantile fits (window=%.0fd, step=%.0fd, τ=%.2f, bootstrap=%d)...\n",
            windowDays, stepDays, quantile, bootstrap
        ))
        let t2 = Date()
        // Linear (current) and log-scale estimators in parallel — lets the
        // HTML overlay both so we can compare head-to-head. Log-scale is
        // reported as effective ISF at refBG so the two series are directly
        // comparable on the same axis.
        async let pointsLinearTask = ISFRolling.compute(
            samples: explored.samples, interval: interval, config: rollingCfg
        )
        let logCfg = ISFRollingConfig(
            windowDays: rollingCfg.windowDays, stepDays: rollingCfg.stepDays,
            quantile: rollingCfg.quantile, minSamples: rollingCfg.minSamples,
            bootstrapN: rollingCfg.bootstrapN, bootstrapSeed: rollingCfg.bootstrapSeed,
            scaleMode: .log(referenceBG: logReferenceBg)
        )
        async let pointsLogTask = ISFRolling.compute(
            samples: explored.samples, interval: interval, config: logCfg
        )
        let points = await pointsLinearTask
        let pointsLog = await pointsLogTask
        printStderr(String(format: "  → %d linear + %d log fits in %.1fs\n",
                           points.count, pointsLog.count, Date().timeIntervalSince(t2)))

        // Daily (windowDays=1) — both linear and log, no bootstrap for speed.
        printStderr("Per-day ISF (linear + log)...\n")
        let t3 = Date()
        let dailyCfgLinear = ISFRollingConfig(
            windowDays: 1, stepDays: 1,
            quantile: quantile, minSamples: 50, bootstrapN: 0,
            scaleMode: .linear
        )
        let dailyCfgLog = ISFRollingConfig(
            windowDays: 1, stepDays: 1,
            quantile: quantile, minSamples: 50, bootstrapN: 0,
            scaleMode: .log(referenceBG: logReferenceBg)
        )
        async let dailyLinearTask = ISFRolling.compute(
            samples: explored.samples, interval: interval, config: dailyCfgLinear
        )
        async let dailyLogTask = ISFRolling.compute(
            samples: explored.samples, interval: interval, config: dailyCfgLog
        )
        let dailyPoints = await dailyLinearTask
        let dailyPointsLog = await dailyLogTask
        printStderr(String(format: "  → %d daily linear + %d daily log fits in %.1fs\n",
                           dailyPoints.count, dailyPointsLog.count,
                           Date().timeIntervalSince(t3)))

        // Daily TDD — sum of delivered insulin per calendar day (local time).
        // Bolus volumes are U; temp-basal volumes are U (rate × duration).
        printStderr("Per-day TDD...\n")
        let tddPoints = Self.computeDailyTDD(
            doses: preloaded.doses,
            interval: interval,
            timezone: timezone
        )
        printStderr(String(format: "  → %d days\n", tddPoints.count))

        Self.printSummary(points: points, quantile: quantile)

        if let csvPath = csv {
            let csvData = Self.buildCSV(points: points)
            try csvData.write(to: resolvePath(csvPath), atomically: true, encoding: .utf8)
            printStderr("CSV: \(resolvePath(csvPath).path)\n")
        }

        if let htmlPath = html {
            let htmlData = ISFRollingHTMLGenerator.generate(
                points: points,
                pointsLog: pointsLog,
                dailyPoints: dailyPoints,
                dailyPointsLog: dailyPointsLog,
                tddPoints: tddPoints,
                interval: interval,
                config: rollingCfg,
                logReferenceBG: logReferenceBg
            )
            try htmlData.write(to: resolvePath(htmlPath), atomically: true, encoding: .utf8)
            printStderr("HTML: \(resolvePath(htmlPath).path)\n")
        }

        if csv == nil, html == nil {
            print(Self.buildCSV(points: points))
        }
    }

    private static func printSummary(points: [RollingISFPoint], quantile: Double) {
        let valid = points.filter { !$0.isfEstimate.isNaN }
        guard !valid.isEmpty else {
            printStderr("\n  (no valid fits — window too small or insufficient samples)\n")
            return
        }
        let isfs = valid.map { $0.isfEstimate }.sorted()
        let n = isfs.count
        let median = isfs[n/2]
        let mean   = isfs.reduce(0, +) / Double(n)
        let p10 = isfs[Int(0.10 * Double(n - 1))]
        let p90 = isfs[Int(0.90 * Double(n - 1))]
        let minV = isfs.first!, maxV = isfs.last!

        printStderr("\n── rolling ISF summary (τ=\(String(format: "%.2f", quantile))) ──\n")
        printStderr(String(format: "  fits:   %d valid / %d total\n", n, points.count))
        printStderr(String(format: "  ISF:    median=%.1f  mean=%.1f  P10/P90=%.1f/%.1f  min/max=%.1f/%.1f  (mg/dL/U)\n",
                           median, mean, p10, p90, minV, maxV))
        if let first = valid.first, let last = valid.last {
            let iso = DateFormatter()
            iso.dateFormat = "yyyy-MM-dd"
            printStderr(String(format: "  span:   %@ → %@  (%d windows)\n",
                               iso.string(from: first.centerTime),
                               iso.string(from: last.centerTime),
                               points.count))
        }
    }

    /// Bucket doses into local-calendar-day bins and sum `volume` per bin.
    /// Returns (dayDate, tddUnits) for every day in the interval — days with
    /// no doses produce tdd=0.
    static func computeDailyTDD(
        doses: [EvalInsulinDose],
        interval: DateInterval,
        timezone: String?
    ) -> [DailyTDDPoint] {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = timezone.flatMap { TimeZone(identifier: $0) } ?? .current
        let tz = cal.timeZone

        // Pre-build the day bins.
        var out: [DailyTDDPoint] = []
        var dayStart = cal.startOfDay(for: interval.start)
        while dayStart < interval.end {
            let dayEnd = cal.date(byAdding: .day, value: 1, to: dayStart) ?? dayStart.addingTimeInterval(86400)
            out.append(DailyTDDPoint(dayStart: dayStart, dayEnd: dayEnd, tdd: 0))
            dayStart = dayEnd
        }

        // Sum doses into bins by local-calendar-day.
        for d in doses {
            guard d.startDate >= interval.start, d.startDate < interval.end else { continue }
            // local-day index = days between interval.start-local-day and d.startDate-local-day
            let dStart = cal.startOfDay(for: d.startDate)
            let delta = cal.dateComponents([.day], from: cal.startOfDay(for: interval.start), to: dStart).day ?? 0
            if delta >= 0, delta < out.count {
                out[delta].tdd += d.volume
            }
        }
        _ = tz   // silence "unused let" if timezone unreachable
        return out
    }

    private static func buildCSV(points: [RollingISFPoint]) -> String {
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime]
        var out = "center_time,window_start,window_end,n_samples,isf_q,intercept,pseudo_r2,ci_low,ci_high\n"
        for p in points {
            out += "\(iso.string(from: p.centerTime)),"
            out += "\(iso.string(from: p.windowStart)),"
            out += "\(iso.string(from: p.windowEnd)),"
            out += "\(p.n),"
            out += p.isfEstimate.isNaN ? "," : String(format: "%.3f,", p.isfEstimate)
            out += p.intercept.isNaN ? "," : String(format: "%.4f,", p.intercept)
            out += p.pseudoR2.isNaN ? "," : String(format: "%.4f,", p.pseudoR2)
            out += p.isfCILow.isNaN ? "," : String(format: "%.3f,", p.isfCILow)
            out += p.isfCIHigh.isNaN ? "\n" : String(format: "%.3f\n", p.isfCIHigh)
        }
        return out
    }

    private func resolvePath(_ raw: String) -> URL {
        if raw.hasPrefix("/") || raw.hasPrefix("~") {
            return URL(fileURLWithPath: (raw as NSString).expandingTildeInPath)
        }
        return URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
            .appendingPathComponent(raw)
    }
}
