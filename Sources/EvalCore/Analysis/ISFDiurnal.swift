// ISFDiurnal.swift — hourly quantile-ISF with bootstrap CIs and day-type split
//
// More granular than the 2-hour bins in ISFExplorer.diurnalQuantileAnalysis.
// For each hour of the day (0–23), runs quantile regression on the subset
// of ISFSamples that fall in that hour and optionally bootstraps for 95%
// CIs. Optionally splits the dataset by weekday vs weekend.
//
// Intended for studying genuine diurnal insulin-sensitivity patterns —
// though see the "Limitations" section in EXPLORATION_NOTES.md: hourly
// swings are confounded with diurnal basal-schedule miscoverage and
// cannot be fully separated from CGM alone.

import Foundation

public enum ISFDayType: String, Sendable, Codable {
    case all
    case weekday
    case weekend
}

public struct HourlyISFPoint: Sendable, Codable {
    /// Local-time hour (0–23).
    public var hour: Int
    /// Number of samples in this hour.
    public var n: Int
    /// Quantile-regression slope (= ISF, mg/dL/U). NaN if fit failed.
    public var isfEstimate: Double
    public var intercept: Double
    public var pseudoR2: Double
    /// Bootstrap 2.5th percentile of slope. NaN if disabled.
    public var isfCILow: Double
    public var isfCIHigh: Double
}

public struct DiurnalResult: Sendable {
    public var dayType: ISFDayType
    public var quantile: Double
    public var bootstrapN: Int
    public var points: [HourlyISFPoint]  // 24 entries (hour 0..23)
}

public enum ISFDiurnal {

    /// Compute per-hour quantile ISF for the given day-type subset.
    public static func compute(
        samples: [ISFSample],
        timezone: String?,
        quantile tau: Double = 0.10,
        bootstrapN: Int = 0,
        bootstrapSeed: UInt64 = 42,
        dayType: ISFDayType = .all,
        minSamples: Int = 50
    ) async -> DiurnalResult {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = timezone.flatMap { TimeZone(identifier: $0) } ?? .current

        // Pre-bin samples by hour, filtered by day-type.
        var byHour: [[ISFSample]] = Array(repeating: [], count: 24)
        for s in samples {
            guard s.isfScheduled > 0 else { continue }
            let comps = cal.dateComponents([.hour, .weekday], from: s.time)
            guard let h = comps.hour, h >= 0, h < 24 else { continue }

            if dayType != .all {
                let wd = comps.weekday ?? 1  // Calendar weekday: 1=Sun .. 7=Sat
                let isWeekend = (wd == 1 || wd == 7)
                if dayType == .weekday, isWeekend { continue }
                if dayType == .weekend, !isWeekend { continue }
            }
            byHour[h].append(s)
        }

        // Parallelize across hours. Each hour does its own (optional) bootstrap.
        let cfgSamples = byHour
        let cfgTau = tau
        let cfgBN = bootstrapN
        let cfgSeed = bootstrapSeed
        let cfgMin = minSamples

        let points: [HourlyISFPoint] = await withTaskGroup(of: (Int, HourlyISFPoint).self) { group in
            for hour in 0..<24 {
                let samples = cfgSamples[hour]
                group.addTask {
                    let point = fitOneHour(
                        hour: hour, samples: samples,
                        quantile: cfgTau, bootstrapN: cfgBN,
                        bootstrapSeed: cfgSeed &+ UInt64(hour),
                        minSamples: cfgMin
                    )
                    return (hour, point)
                }
            }
            var out: [HourlyISFPoint?] = Array(repeating: nil, count: 24)
            for await (h, p) in group { out[h] = p }
            return out.map { $0! }
        }

        return DiurnalResult(
            dayType: dayType, quantile: tau, bootstrapN: bootstrapN, points: points
        )
    }

    // MARK: - Internal

    static func fitOneHour(
        hour: Int,
        samples: [ISFSample],
        quantile tau: Double,
        bootstrapN: Int,
        bootstrapSeed: UInt64,
        minSamples: Int
    ) -> HourlyISFPoint {
        guard samples.count >= minSamples else {
            return HourlyISFPoint(
                hour: hour, n: samples.count,
                isfEstimate: .nan, intercept: .nan, pseudoR2: .nan,
                isfCILow: .nan, isfCIHigh: .nan
            )
        }
        guard let fit = ISFExplorer.quantileRegression(
            samples: samples, quantile: tau, minSampleCount: minSamples
        ) else {
            return HourlyISFPoint(
                hour: hour, n: samples.count,
                isfEstimate: .nan, intercept: .nan, pseudoR2: .nan,
                isfCILow: .nan, isfCIHigh: .nan
            )
        }

        var ciLow = Double.nan, ciHigh = Double.nan
        if bootstrapN > 0 {
            var rng = SplitMix64(seed: bootstrapSeed)
            var slopes: [Double] = []
            slopes.reserveCapacity(bootstrapN)
            var resampled = [ISFSample]()
            resampled.reserveCapacity(samples.count)
            let n = samples.count
            for _ in 0..<bootstrapN {
                resampled.removeAll(keepingCapacity: true)
                for _ in 0..<n {
                    let idx = Int(rng.nextUInt() % UInt64(n))
                    resampled.append(samples[idx])
                }
                if let f = ISFExplorer.quantileRegression(
                    samples: resampled, quantile: tau, minSampleCount: minSamples
                ) {
                    slopes.append(f.isfEstimate)
                }
            }
            if !slopes.isEmpty {
                slopes.sort()
                let m = slopes.count
                func pct(_ p: Double) -> Double {
                    let idx = Int(Double(m - 1) * p + 0.5)
                    return slopes[min(max(idx, 0), m - 1)]
                }
                ciLow = pct(0.025)
                ciHigh = pct(0.975)
            }
        }

        return HourlyISFPoint(
            hour: hour, n: samples.count,
            isfEstimate: fit.isfEstimate,
            intercept: fit.intercept,
            pseudoR2: fit.pseudoR2,
            isfCILow: ciLow, isfCIHigh: ciHigh
        )
    }
}
