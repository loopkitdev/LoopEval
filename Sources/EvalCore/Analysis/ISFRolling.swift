// ISFRolling.swift — rolling-window quantile-ISF estimator
//
// Steps through a long dataset in fixed-size windows and runs quantile
// regression at τ=0.10 (default) on each window. Output is a time series
// of ISF estimates suitable for drift detection, diurnal analysis, and
// periodogram-based cycle detection (hormonal, weekly, etc.).
//
// Bootstrap 95% CIs are optional (`config.bootstrapN > 0`); they resample
// the window's ISFSample array with replacement and return the 2.5/97.5
// percentile of the slope estimates.

import Foundation

public enum ISFScaleMode: Sendable, Codable {
    /// Linear: regress v_cgm on activity. Slope is ISF in mg/dL/U.
    case linear
    /// Log (multiplicative): regress v_cgm × refBG / bgSmoothed on activity.
    /// Slope is the *effective* ISF at refBG; true multiplicative-model
    /// ISF varies with BG as ISF(B) = slope × B / refBG.
    case log(referenceBG: Double)
}

public struct ISFRollingConfig: Sendable {
    /// Rolling-window width (days).
    public var windowDays: Double
    /// Advance between consecutive window centers (days).
    public var stepDays: Double
    /// Quantile used for each window's fit.
    public var quantile: Double
    /// Minimum samples required in a window to produce a fit.
    public var minSamples: Int
    /// Number of bootstrap resamples for 95% CI (0 = skip).
    public var bootstrapN: Int
    /// Seed for the bootstrap RNG (deterministic output).
    public var bootstrapSeed: UInt64
    /// Linear (default) or log-scale ISF estimator.
    public var scaleMode: ISFScaleMode

    public init(
        windowDays: Double = 7,
        stepDays: Double = 1,
        quantile: Double = 0.10,
        minSamples: Int = 100,
        bootstrapN: Int = 0,
        bootstrapSeed: UInt64 = 42,
        scaleMode: ISFScaleMode = .linear
    ) {
        self.windowDays = windowDays
        self.stepDays = stepDays
        self.quantile = quantile
        self.minSamples = minSamples
        self.bootstrapN = bootstrapN
        self.bootstrapSeed = bootstrapSeed
        self.scaleMode = scaleMode
    }
}

public struct RollingISFPoint: Sendable, Codable {
    /// Centre time of the window.
    public var centerTime: Date
    public var windowStart: Date
    public var windowEnd: Date
    /// Number of ISFSamples inside the window.
    public var n: Int
    /// Slope of the quantile fit, in mg/dL/U (ISF estimate). NaN if fit failed.
    public var isfEstimate: Double
    public var intercept: Double
    public var pseudoR2: Double
    /// Bootstrap 2.5th percentile of the slope. NaN if bootstrap disabled.
    public var isfCILow: Double
    /// Bootstrap 97.5th percentile of the slope.
    public var isfCIHigh: Double
}

public enum ISFRolling {

    /// Compute a rolling quantile-ISF time series over the input sample array.
    ///
    /// - Parameters:
    ///   - samples: pre-computed ISFSample array covering the full analysis
    ///     window. Expected to be sorted by `time`.
    ///   - interval: analysis interval; windows are centred between
    ///     `interval.start + windowDays/2` and `interval.end − windowDays/2`.
    ///   - config: window/quantile/bootstrap parameters.
    /// - Returns: one RollingISFPoint per window, in chronological order.
    public static func compute(
        samples: [ISFSample],
        interval: DateInterval,
        config: ISFRollingConfig = ISFRollingConfig()
    ) async -> [RollingISFPoint] {
        let halfWindowSec = config.windowDays * 86400 / 2
        let stepSec = config.stepDays * 86400
        let firstCenter = interval.start.addingTimeInterval(halfWindowSec)
        let lastCenter  = interval.end.addingTimeInterval(-halfWindowSec)

        guard lastCenter >= firstCenter else { return [] }

        var centers: [Date] = []
        var t = firstCenter
        while t <= lastCenter {
            centers.append(t)
            t = t.addingTimeInterval(stepSec)
        }

        // Parallelize across windows.
        return await withTaskGroup(of: (Int, RollingISFPoint).self) { group in
            for (idx, center) in centers.enumerated() {
                let start = center.addingTimeInterval(-halfWindowSec)
                let end   = center.addingTimeInterval( halfWindowSec)
                let windowSamples = sliceSamples(samples, start: start, end: end)
                let cfg = config
                group.addTask {
                    let point = fitOneWindow(
                        windowSamples: windowSamples,
                        center: center, start: start, end: end,
                        config: cfg,
                        seedOffset: UInt64(idx)
                    )
                    return (idx, point)
                }
            }
            var results = [(Int, RollingISFPoint)]()
            for await r in group { results.append(r) }
            results.sort { $0.0 < $1.0 }
            return results.map { $0.1 }
        }
    }

    // MARK: - Internal

    /// Binary-search slice: returns `[ISFSample]` whose `time` ∈ [start, end).
    /// Assumes `samples` is sorted ascending by time.
    static func sliceSamples(
        _ samples: [ISFSample], start: Date, end: Date
    ) -> [ISFSample] {
        guard !samples.isEmpty else { return [] }
        let lo = lowerBound(samples, time: start)
        let hi = lowerBound(samples, time: end)
        guard lo < hi else { return [] }
        return Array(samples[lo..<hi])
    }

    static func lowerBound(_ samples: [ISFSample], time: Date) -> Int {
        var lo = 0, hi = samples.count
        while lo < hi {
            let m = (lo + hi) / 2
            if samples[m].time < time { lo = m + 1 } else { hi = m }
        }
        return lo
    }

    /// Fit one window. Point estimate always; bootstrap CI if configured.
    static func fitOneWindow(
        windowSamples: [ISFSample],
        center: Date, start: Date, end: Date,
        config: ISFRollingConfig,
        seedOffset: UInt64
    ) -> RollingISFPoint {
        let n = windowSamples.count
        guard n >= config.minSamples else {
            return RollingISFPoint(
                centerTime: center, windowStart: start, windowEnd: end,
                n: n, isfEstimate: .nan, intercept: .nan, pseudoR2: .nan,
                isfCILow: .nan, isfCIHigh: .nan
            )
        }

        guard let fit = runFit(
            samples: windowSamples,
            quantile: config.quantile,
            minSamples: config.minSamples,
            scaleMode: config.scaleMode
        ) else {
            return RollingISFPoint(
                centerTime: center, windowStart: start, windowEnd: end,
                n: n, isfEstimate: .nan, intercept: .nan, pseudoR2: .nan,
                isfCILow: .nan, isfCIHigh: .nan
            )
        }

        var ciLow = Double.nan, ciHigh = Double.nan
        if config.bootstrapN > 0 {
            (ciLow, ciHigh) = bootstrapCI(
                samples: windowSamples,
                quantile: config.quantile,
                bootstrapN: config.bootstrapN,
                minSampleCount: config.minSamples,
                scaleMode: config.scaleMode,
                seed: config.bootstrapSeed &+ seedOffset
            )
        }

        return RollingISFPoint(
            centerTime: center, windowStart: start, windowEnd: end,
            n: n,
            isfEstimate: fit.isfEstimate,
            intercept: fit.intercept,
            pseudoR2: fit.pseudoR2,
            isfCILow: ciLow,
            isfCIHigh: ciHigh
        )
    }

    /// Dispatch to linear or log-scale regression per `scaleMode`.
    static func runFit(
        samples: [ISFSample],
        quantile: Double,
        minSamples: Int,
        scaleMode: ISFScaleMode
    ) -> QuantileRegression? {
        switch scaleMode {
        case .linear:
            return ISFExplorer.quantileRegression(
                samples: samples, quantile: quantile, minSampleCount: minSamples
            )
        case .log(let refBG):
            return ISFExplorer.quantileRegressionLog(
                samples: samples, quantile: quantile,
                referenceBG: refBG, minSampleCount: minSamples
            )
        }
    }

    /// Bootstrap the τ-quantile slope. Returns (2.5%, 97.5%) percentiles.
    static func bootstrapCI(
        samples: [ISFSample],
        quantile: Double,
        bootstrapN: Int,
        minSampleCount: Int,
        scaleMode: ISFScaleMode,
        seed: UInt64
    ) -> (Double, Double) {
        let n = samples.count
        var rng = SplitMix64(seed: seed)
        var slopes: [Double] = []
        slopes.reserveCapacity(bootstrapN)

        var resampled = [ISFSample]()
        resampled.reserveCapacity(n)

        for _ in 0..<bootstrapN {
            resampled.removeAll(keepingCapacity: true)
            for _ in 0..<n {
                let idx = Int(rng.nextUInt() % UInt64(n))
                resampled.append(samples[idx])
            }
            if let fit = runFit(
                samples: resampled,
                quantile: quantile,
                minSamples: minSampleCount,
                scaleMode: scaleMode
            ) {
                slopes.append(fit.isfEstimate)
            }
        }

        guard !slopes.isEmpty else { return (.nan, .nan) }
        slopes.sort()
        let m = slopes.count
        func pct(_ p: Double) -> Double {
            let idx = Int((Double(m - 1)) * p + 0.5)
            return slopes[min(max(idx, 0), m - 1)]
        }
        return (pct(0.025), pct(0.975))
    }
}

// MARK: - Deterministic RNG

/// SplitMix64 — small, fast, deterministic PRNG used for reproducible
/// bootstrap resampling. Not cryptographic; we only need uniform ints.
struct SplitMix64 {
    var state: UInt64
    init(seed: UInt64) { self.state = seed }
    mutating func nextUInt() -> UInt64 {
        state = state &+ 0x9E3779B97F4A7C15
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58476D1CE4E5B9
        z = (z ^ (z >> 27)) &* 0x94D049BB133111EB
        return z ^ (z >> 31)
    }
}
