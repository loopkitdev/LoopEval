// ISFDiurnalCommand.swift — `loop-eval isf-diurnal` subcommand
//
// Per-hour quantile-ISF with bootstrap CIs and optional weekday/weekend split.

import ArgumentParser
import EvalCore
import Foundation
import LoopAlgorithm

struct ISFDiurnalCommand: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "isf-diurnal",
        abstract: "Per-hour quantile-ISF with bootstrap 95% CIs."
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

    @Option(name: .long, help: "Quantile τ (default 0.10)")
    var quantile: Double = 0.10

    @Option(name: .long, help: "Bootstrap resamples for 95% CI (0 = skip)")
    var bootstrap: Int = 0

    @Option(name: .long, help: "Minimum samples required per hour")
    var minSamples: Int = 50

    @Option(name: .long, help: "Also split by weekday vs weekend")
    var splitWeekday: Bool = false

    @Option(name: .long, help: "Minimum |v_insulin| to keep a sample (mg/dL/min)")
    var minInsulinVelocity: Double = 0.05

    @Option(name: .long, help: "Drop samples with BG below this (mg/dL). Default 80.")
    var bgMin: Double = 80

    @Option(name: .long, help: "Drop samples with BG at/above this (mg/dL). Default 395.")
    var bgMax: Double = 395

    @Option(name: .long, help: "IANA timezone (e.g. America/Chicago). Default: system local.")
    var timezone: String?

    @Option(name: .long, help: "Replace configured ISF schedule with a single constant value (mg/dL/U)")
    var overrideIsf: Double?

    @Option(name: .long, help: "Write HTML report to this path")
    var html: String?

    @Option(name: .long, help: "Write CSV to this path")
    var csv: String?

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
                basal: th.basal, sensitivity: overrideSched, carbRatio: th.carbRatio,
                target: th.target, suspendThreshold: th.suspendThreshold,
                maxBolus: th.maxBolus, maxBasalRate: th.maxBasalRate,
                insulinType: th.insulinType
            )
            preloaded = PreloadedData(
                glucose: preloadedRaw.glucose, doses: preloadedRaw.doses,
                carbs: preloadedRaw.carbs, therapyTimeline: overrideTherapy
            )
            printStderr(String(format: "  ⚠ ISF override: %.1f mg/dL/U\n", isfValue))
        } else {
            preloaded = preloadedRaw
        }

        printStderr("Computing ISFSamples...")
        let t1 = Date()
        let options = ISFExploreOptions(
            minInsulinVelocity: minInsulinVelocity, timezone: timezone,
            bgMin: bgMin, bgMax: bgMax
        )
        let explored = ISFExplorer.analyze(data: preloaded, interval: interval, options: options)
        printStderr(String(format: " done (%.1fs, %d samples)\n",
                           Date().timeIntervalSince(t1), explored.samples.count))

        printStderr(String(format: "Hourly quantile fits (τ=%.2f, bootstrap=%d)...\n",
                           quantile, bootstrap))
        let t2 = Date()

        let all = await ISFDiurnal.compute(
            samples: explored.samples, timezone: timezone,
            quantile: quantile, bootstrapN: bootstrap,
            dayType: .all, minSamples: minSamples
        )

        var weekday: DiurnalResult?
        var weekend: DiurnalResult?
        if splitWeekday {
            weekday = await ISFDiurnal.compute(
                samples: explored.samples, timezone: timezone,
                quantile: quantile, bootstrapN: bootstrap,
                dayType: .weekday, minSamples: minSamples
            )
            weekend = await ISFDiurnal.compute(
                samples: explored.samples, timezone: timezone,
                quantile: quantile, bootstrapN: bootstrap,
                dayType: .weekend, minSamples: minSamples
            )
        }
        printStderr(String(format: "  done (%.1fs)\n", Date().timeIntervalSince(t2)))

        Self.printTable(label: "all days", result: all)
        if let wd = weekday { Self.printTable(label: "weekdays", result: wd) }
        if let we = weekend { Self.printTable(label: "weekends", result: we) }

        if let csvPath = csv {
            let csvStr = Self.buildCSV(all: all, weekday: weekday, weekend: weekend)
            try csvStr.write(to: resolvePath(csvPath), atomically: true, encoding: .utf8)
            printStderr("CSV: \(resolvePath(csvPath).path)\n")
        }

        if let htmlPath = html {
            let htmlStr = ISFDiurnalHTMLGenerator.generate(
                all: all, weekday: weekday, weekend: weekend,
                interval: interval
            )
            try htmlStr.write(to: resolvePath(htmlPath), atomically: true, encoding: .utf8)
            printStderr("HTML: \(resolvePath(htmlPath).path)\n")
        }

        if csv == nil, html == nil {
            print(Self.buildCSV(all: all, weekday: weekday, weekend: weekend))
        }
    }

    private static func printTable(label: String, result: DiurnalResult) {
        printStderr("\n── \(label) (τ=\(String(format: "%.2f", result.quantile))) ──\n")
        for p in result.points {
            let isf = p.isfEstimate.isNaN ? "   -" : String(format: "%5.1f", p.isfEstimate)
            let ci: String
            if p.isfCILow.isNaN {
                ci = ""
            } else {
                ci = String(format: " [%.1f, %.1f]", p.isfCILow, p.isfCIHigh)
            }
            printStderr(String(format: "  %02d:00  n=%5d  ISF=%@%@\n",
                               p.hour, p.n, isf, ci))
        }
    }

    private static func buildCSV(
        all: DiurnalResult, weekday: DiurnalResult?, weekend: DiurnalResult?
    ) -> String {
        var out = "hour,day_type,n,isf,ci_low,ci_high,intercept,pseudo_r2\n"
        func emit(_ r: DiurnalResult) {
            for p in r.points {
                out += "\(p.hour),\(r.dayType.rawValue),\(p.n),"
                out += p.isfEstimate.isNaN ? "," : String(format: "%.3f,", p.isfEstimate)
                out += p.isfCILow.isNaN ? "," : String(format: "%.3f,", p.isfCILow)
                out += p.isfCIHigh.isNaN ? "," : String(format: "%.3f,", p.isfCIHigh)
                out += p.intercept.isNaN ? "," : String(format: "%.4f,", p.intercept)
                out += p.pseudoR2.isNaN ? "\n" : String(format: "%.4f\n", p.pseudoR2)
            }
        }
        emit(all)
        if let wd = weekday { emit(wd) }
        if let we = weekend { emit(we) }
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
