// ISFExploreCommand.swift — `loop-eval isf-explore` subcommand
//
// Pointwise implied-ISF estimator with meal/exercise classification driven
// by sustained ICE (insulin counteraction effect). User-entered carbs are
// only plotted for visual context — not used in the analysis.

import ArgumentParser
import EvalCore
import Foundation
import LoopAlgorithm

struct ISFExploreCommand: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "isf-explore",
        abstract: "Explore pointwise implied-ISF from smoothed CGM vs modeled insulin effect.",
        discussion: """
        At each 5-minute CGM interval, computes:
            local_ISF = ISF_scheduled × v_cgm_smoothed / v_insulin_modeled
        and classifies each sample as meal / exercise / neutral from sustained
        ICE (v_cgm − v_insulin). Neutral-only stats are the candidate baseline
        ISF. Meals are NOT detected from user-entered carbs — carbs are
        overlaid for visual reference only.
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

    @Option(name: .long, help: "Minimum |insulin velocity| to keep a sample (mg/dL/min)")
    var minInsulinVelocity: Double = 0.05

    @Option(name: .long, help: "ICE rolling-mean window (minutes)")
    var iceWindow: Double = 30

    @Option(name: .long, help: "Meal threshold on rolling ICE (mg/dL/min)")
    var mealThreshold: Double = 1.5

    @Option(name: .long, help: "Exercise threshold magnitude on rolling ICE (mg/dL/min) — fires when rolling ICE < −this")
    var exerciseThreshold: Double = 1.0

    @Option(name: .long, help: "Minimum run duration to keep a class (minutes)")
    var minRun: Double = 20

    @Option(name: .long, help: "After each meal run, extend class forward (minutes)")
    var mealTail: Double = 90

    @Option(name: .long, help: "After each exercise run, extend class forward (minutes)")
    var exerciseTail: Double = 60

    @Option(name: .long, help: "Latitude for sun-elevation background (degrees north)")
    var latitude: Double = 40.0

    @Option(name: .long, help: "Longitude for sun-elevation background (degrees east)")
    var longitude: Double = -93.0

    @Option(name: .long, help: "IANA timezone for fasting-window filter (e.g. America/Chicago). Default: system local.")
    var timezone: String?

    @Option(name: .long, help: "Fasting window start-hour (local time, 0–23)")
    var fastingHourStart: Int = 1

    @Option(name: .long, help: "Fasting window end-hour (exclusive, local time)")
    var fastingHourEnd: Int = 4

    @Option(name: .long, help: "Replace configured ISF schedule with a single constant value (mg/dL/U) — use to test the ISF-cancellation property")
    var overrideIsf: Double?

    @Option(name: .long, help: "Multiply the entire scheduled basal rate by this factor before computing v_insulin (default 1.0). Use to sensitivity-check ISF estimates against basal-schedule error.")
    var basalMultiplier: Double = 1.0

    @Option(name: .long, help: "Write CSV to this path")
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

        // Optional ISF override — replace the entire sensitivity schedule with
        // a single constant value spanning the original coverage. Lets the
        // LoopAlgorithm regenerate insulin effects (and therefore ICE) against
        // the hypothetical pump setting.
        let preloadedAfterIsf: PreloadedData
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
            preloadedAfterIsf = PreloadedData(
                glucose: preloadedRaw.glucose,
                doses: preloadedRaw.doses,
                carbs: preloadedRaw.carbs,
                therapyTimeline: overrideTherapy
            )
            printStderr(String(format: "  ⚠ ISF override active: all schedule entries replaced with %.1f mg/dL/U\n", isfValue))
        } else {
            preloadedAfterIsf = preloadedRaw
        }

        // Optional basal scalar — multiply each scheduled basal entry's rate.
        // `v_insulin` is computed from `netBasalUnits = delivered − scheduled·dt`,
        // so scaling the schedule directly perturbs the activity signal without
        // touching ISF. Lets us probe how ISF estimates respond to basal error.
        let preloaded: PreloadedData
        if basalMultiplier != 1.0 {
            guard basalMultiplier > 0 else {
                throw ValidationError("--basal-multiplier must be > 0 (got \(basalMultiplier))")
            }
            let th = preloadedAfterIsf.therapyTimeline
            let scaledBasal = th.basal.map {
                AbsoluteScheduleValue(
                    startDate: $0.startDate, endDate: $0.endDate,
                    value: $0.value * basalMultiplier
                )
            }
            let scaledTherapy = TherapySettings(
                basal: scaledBasal,
                sensitivity: th.sensitivity,
                carbRatio: th.carbRatio,
                target: th.target,
                suspendThreshold: th.suspendThreshold,
                maxBolus: th.maxBolus,
                maxBasalRate: th.maxBasalRate,
                insulinType: th.insulinType
            )
            preloaded = PreloadedData(
                glucose: preloadedAfterIsf.glucose,
                doses: preloadedAfterIsf.doses,
                carbs: preloadedAfterIsf.carbs,
                therapyTimeline: scaledTherapy
            )
            printStderr(String(format: "  ⚠ basal ×%.3f active (scheduled rates scaled)\n", basalMultiplier))
        } else {
            preloaded = preloadedAfterIsf
        }

        // Total insulin delivered over the evaluation interval (boluses + all
        // basal) — lets us pair the data-driven fit with a simple 1800-rule
        // ISF estimate for comparison.
        let intervalDoses = preloaded.doses.filter {
            $0.startDate >= interval.start && $0.startDate < interval.end
        }
        let totalInsulinU = intervalDoses.reduce(0.0) { $0 + $1.volume }
        let days = interval.duration / 86400.0
        let tdd = days > 0 ? totalInsulinU / days : 0
        let ruleISF = tdd > 0 ? 1800 / tdd : 0

        printStderr("Computing local ISF + classifying...")
        let options = ISFExploreOptions(
            minInsulinVelocity: minInsulinVelocity,
            iceWindowMinutes: iceWindow,
            mealThreshold: mealThreshold,
            exerciseThreshold: exerciseThreshold,
            minRunMinutes: minRun,
            mealTailMinutes: mealTail,
            exerciseTailMinutes: exerciseTail,
            timezone: timezone,
            fastingHourStart: fastingHourStart,
            fastingHourEnd: fastingHourEnd
        )
        let result = ISFExplorer.analyze(data: preloaded, interval: interval, options: options)
        printStderr(" \(result.samples.count) samples retained / \(result.summary.samplesConsidered) considered\n")

        Self.printSummary(result.summary)
        printStderr(String(
            format: "\n  insulin delivered in interval: %.1f U over %.1f days  →  TDD = %.1f U/day\n",
            totalInsulinU, days, tdd
        ))
        if tdd > 0 {
            printStderr(String(format: "  1800 rule: ISF ≈ 1800 / %.1f = %.1f mg/dL/U\n", tdd, ruleISF))
        }

        // Carb estimate from EGP-coverage subtraction.
        let avgCR = Self.timeWeightedAvgCR(
            schedule: preloaded.therapyTimeline.carbRatio,
            interval: interval
        )
        if let egp = result.summary.egp, tdd > 0, avgCR > 0 {
            let carbInsulinU = max(0, tdd - egp.deliveryRatePerDay)
            let carbsG = carbInsulinU * avgCR
            printStderr(String(
                format: "\n  EGP-coverage delivery rate (stable-ICE, T=%.2f): %.2f U/day (%.2f U/min × 1440)\n",
                egp.thresholdMgdlMin, egp.deliveryRatePerDay, egp.deliveryRatePerMinute
            ))
            printStderr(String(
                format: "    carb-covering insulin: TDD − EGP = %.2f − %.2f = %.2f U/day\n",
                tdd, egp.deliveryRatePerDay, carbInsulinU
            ))
            printStderr(String(
                format: "    avg CR (time-weighted): %.2f g/U  →  estimated carbs: %.0f g/day\n",
                avgCR, carbsG
            ))
        }

        if let csvPath = csv {
            try writeCSV(samples: result.samples, to: resolvePath(csvPath))
            printStderr("CSV: \(resolvePath(csvPath).path)\n")
        }

        if let htmlPath = html {
            let html = ISFExploreHTMLGenerator.generate(
                result: result,
                interval: interval,
                doses: preloaded.doses,
                carbs: preloaded.carbs,
                options: options,
                latitude: latitude,
                longitude: longitude,
                totalInsulinU: totalInsulinU,
                tdd: tdd,
                avgCR: avgCR
            )
            try html.write(to: resolvePath(htmlPath), atomically: true, encoding: .utf8)
            printStderr("HTML: \(resolvePath(htmlPath).path)\n")
        }

        if csv == nil, html == nil {
            printCSVToStdout(samples: result.samples)
        }
    }

    private static func printSummary(_ s: ISFExploreSummary) {
        printStderr("\n── local ISF summary ──\n")
        printStderr("  retained:  \(s.samplesRetained) / \(s.samplesConsidered)\n")
        printStderr("  dropped (|vInsulin| too small): \(s.droppedInsufficientInsulin)\n")
        printStderr("  dropped (clamp):                \(s.droppedClamped)\n")
        printStderr("  classes — meal: \(s.mealCount)  exercise: \(s.exerciseCount)  neutral: \(s.neutralCount)\n")

        func printRow(_ label: String, _ stats: ISFStats) {
            if stats.count == 0 {
                printStderr("  \(label): (no samples)\n")
                return
            }
            let p = stats.percentiles
            printStderr(String(
                format: "  %-16@ n=%5d  median=%.1f  wmean=%.1f  mean=%.1f  P10/P25/P75/P90=%.1f/%.1f/%.1f/%.1f\n",
                label as NSString,
                stats.count,
                stats.median, stats.weightedMean, stats.mean,
                p[0.10] ?? .nan, p[0.25] ?? .nan, p[0.75] ?? .nan, p[0.90] ?? .nan
            ))
        }
        printStderr("\n")
        printRow("ALL",     s.allStats)
        printRow("NEUTRAL", s.neutralStats)
        printRow("FASTING", s.fastingStats)
        if let reg = s.primaryStableRegression {
            printStderr(String(
                format: "\n  stable-ICE regression (|rolling_ICE| ≤ %.2f for ±%.0f min):\n",
                reg.thresholdMgdlMin, reg.halfWindowMinutes
            ))
            printStderr(String(
                format: "    v_cgm = %.1f × activity + %.3f   R²=%.3f   n=%d\n",
                reg.isfEstimate, reg.intercept, reg.rSquared, reg.n
            ))
            printStderr(String(
                format: "    → ISF estimate (slope, ISF-tautology-free): %.1f mg/dL/U\n",
                reg.isfEstimate
            ))
        }
        if !s.stableSweepT.isEmpty {
            printStderr("\n  Threshold sweep (halfM=30 min):\n")
            for r in s.stableSweepT {
                printStderr(String(
                    format: "    T=%.2f  n=%4d  ISF=%.1f  C=%.3f  R²=%.3f\n",
                    r.thresholdMgdlMin, r.n, r.isfEstimate, r.intercept, r.rSquared
                ))
            }
        }

        // ISF-invariant regressions — results should not depend on the ISF
        // that was plugged into the insulin model (verify via --override-isf).
        printStderr("\n  ISF-invariant estimators (selection does not depend on ISF_guess):\n")
        if let r = s.olsAllRegression {
            printStderr(String(
                format: "    OLS (all samples)          n=%5d  ISF=%.1f  C=%.3f  R²=%.3f\n",
                r.n, r.isfEstimate, r.intercept, r.rSquared
            ))
        }
        if let r = s.carbExcludedRegression {
            printStderr(String(
                format: "    carb-excluded (±15/+240m)  n=%5d  ISF=%.1f  C=%.3f  R²=%.3f\n",
                r.n, r.isfEstimate, r.intercept, r.rSquared
            ))
        }
        if !s.activitySweep.isEmpty {
            printStderr("    |activity| ≥ T_act sweep:\n")
            for r in s.activitySweep {
                printStderr(String(
                    format: "      T_act=%.3f U/min  n=%5d  ISF=%.1f  C=%.3f  R²=%.3f\n",
                    r.thresholdMgdlMin, r.n, r.isfEstimate, r.intercept, r.rSquared
                ))
            }
        }
        if !s.vCgmStableSweepT.isEmpty {
            printStderr("    |v_cgm| ≤ T_v for ±30 min sweep (flat-BG selector):\n")
            for r in s.vCgmStableSweepT {
                printStderr(String(
                    format: "      T_v=%.2f mg/dL/min  n=%5d  ISF=%.1f  C=%.3f  R²=%.3f\n",
                    r.thresholdMgdlMin, r.n, r.isfEstimate, r.intercept, r.rSquared
                ))
            }
        }
        if !s.quantileSweep.isEmpty {
            printStderr("\n  Quantile regression of v_cgm ~ a + b·activity (ISF = slope b):\n")
            printStderr("    low τ ≈ carb-free lower envelope (carbs are one-sided noise)\n")
            for r in s.quantileSweep {
                printStderr(String(
                    format: "      τ=%.2f  n=%5d  ISF=%.1f  a=%.3f mg/dL/min  pseudoR²=%.3f\n",
                    r.quantile, r.n, r.isfEstimate, r.intercept, r.pseudoR2
                ))
            }
        }
        if !s.diurnalQuantile.isEmpty {
            printStderr("\n  Diurnal ISF at τ=0.10 (2-hour bins, local time):\n")
            printStderr("    vCgm = median v_cgm (mg/dL/min) in stable-ICE windows of each bin.\n")
            printStderr("    v_insulin is net-of-basal, so vCgm>0 = basal under-covers EGP,\n")
            printStderr("    vCgm<0 = basal over-covers.\n")
            for b in s.diurnalQuantile {
                let isf = b.isfEstimate.isNaN
                    ? "    –"
                    : String(format: "%5.1f", b.isfEstimate)
                let r2 = b.pseudoR2.isNaN
                    ? "  –  "
                    : String(format: "%.3f", b.pseudoR2)
                let vcgm = b.stableMedianVCgm.isNaN
                    ? "     –"
                    : String(format: "%+6.3f", b.stableMedianVCgm)
                printStderr(String(
                    format: "      %02d:00–%02d:00  n=%4d  ISF=%@  pseudoR²=%@  vCgm=%@  (n_stable=%4d)\n",
                    b.binStartHour, b.binEndHour, b.n, isf, r2, vcgm, b.stableN
                ))
            }
        }
    }

    // MARK: - CSV output

    private func writeCSV(samples: [ISFSample], to url: URL) throws {
        let csv = buildCSV(samples: samples)
        try csv.write(to: url, atomically: true, encoding: .utf8)
    }

    private func printCSVToStdout(samples: [ISFSample]) {
        print(buildCSV(samples: samples))
    }

    private func buildCSV(samples: [ISFSample]) -> String {
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime]
        var out = "time,bg_smoothed,v_cgm_mgdl_min,v_insulin_mgdl_min,ice,rolling_ice,iob,isf_scheduled,local_isf,weight,class\n"
        for s in samples {
            out += "\(iso.string(from: s.time)),"
            out += String(format: "%.2f,%.4f,%.4f,%.4f,%.4f,%.3f,%.1f,%.2f,%.4f,%@\n",
                          s.bgSmoothed, s.vCgm, s.vInsulin,
                          s.ice, s.rollingICE,
                          s.iob, s.isfScheduled, s.localISF, s.weight,
                          s.classification.rawValue as NSString)
        }
        return out
    }

    /// Time-weighted mean of a carb-ratio schedule over `interval`,
    /// in grams per unit. Used to translate carb-covering insulin into grams.
    private static func timeWeightedAvgCR(
        schedule: [AbsoluteScheduleValue<Double>],
        interval: DateInterval
    ) -> Double {
        var num = 0.0
        var den = 0.0
        for e in schedule {
            let lo = max(e.startDate, interval.start)
            let hi = min(e.endDate, interval.end)
            let dur = hi.timeIntervalSince(lo)
            guard dur > 0 else { continue }
            num += e.value * dur
            den += dur
        }
        return den > 0 ? num / den : 0
    }

    private func resolvePath(_ raw: String) -> URL {
        if raw.hasPrefix("/") || raw.hasPrefix("~") {
            return URL(fileURLWithPath: (raw as NSString).expandingTildeInPath)
        }
        return URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
            .appendingPathComponent(raw)
    }
}
