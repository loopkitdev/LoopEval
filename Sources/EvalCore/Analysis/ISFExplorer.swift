// ISFExplorer.swift — pointwise local-ISF estimator.
//
// At each 5-minute CGM interval, computes:
//   local_ISF = ISF_scheduled × v_cgm_smoothed / v_insulin_modeled
// where v_cgm is derivative of Kalman-smoothed CGM and v_insulin is derivative
// of the cumulative modeled insulin effect (at configured schedule, no
// multiplier). Ratio ≈ 1 when neither meals nor exercise are active.
//
// Also classifies each sample as meal / exercise / neutral based on sustained
// ICE (insulin counteraction effect = v_cgm − v_insulin). User-entered carbs
// are NOT used — detection relies on ICE alone because many datasets are
// largely unannounced.

import Foundation
import LoopAlgorithm

public enum ISFClass: String, Codable, Sendable {
    case meal
    case exercise
    case neutral
}

public struct ISFSample: Codable, Sendable {
    /// Midpoint of the CGM interval used to compute v_cgm.
    public var time: Date
    /// Mean smoothed BG across the interval (mg/dL).
    public var bgSmoothed: Double
    /// Smoothed-CGM velocity over the interval (mg/dL/min).
    public var vCgm: Double
    /// Modeled insulin-effect velocity over the interval (mg/dL/min, negative when insulin lowers BG).
    public var vInsulin: Double
    /// Insulin counteraction effect = vCgm − vInsulin (mg/dL/min).
    public var ice: Double
    /// Centered rolling mean of ICE over `iceWindowMinutes` (mg/dL/min).
    public var rollingICE: Double
    /// Active insulin at `time` (units).
    public var iob: Double
    /// Schedule-configured ISF at `time` (mg/dL/U).
    public var isfScheduled: Double
    /// Implied local ISF = isfScheduled × vCgm / vInsulin (mg/dL/U).
    public var localISF: Double
    /// Weight for aggregation = |vInsulin| (mg/dL/min).
    public var weight: Double
    /// meal / exercise / neutral after run-length filtering + tail extension.
    public var classification: ISFClass
}

public struct ISFExploreOptions: Sendable {
    /// Discard points with |vInsulin| below this threshold (mg/dL/min).
    public var minInsulinVelocity: Double
    /// Discard points where |localISF| falls outside these bounds (mg/dL/U)
    /// — guards against numeric blow-ups from near-zero denominators that
    /// slipped past `minInsulinVelocity`.
    public var localISFClampLow: Double
    public var localISFClampHigh: Double

    // Classification
    /// Window (minutes) for centered rolling-mean of ICE.
    public var iceWindowMinutes: Double
    /// Rolling-ICE above this triggers MEAL (mg/dL/min).
    public var mealThreshold: Double
    /// Rolling-ICE below −this triggers EXERCISE (mg/dL/min).
    public var exerciseThreshold: Double
    /// Runs shorter than this collapse back to neutral (minutes).
    public var minRunMinutes: Double
    /// After a meal run ends, extend the class forward this long (minutes).
    public var mealTailMinutes: Double
    /// After an exercise run ends, extend the class forward this long (minutes).
    public var exerciseTailMinutes: Double

    /// IANA timezone name used to compute local time-of-day for the fasting
    /// benchmark. `nil` = system local.
    public var timezone: String?
    /// Inclusive start-hour for the fasting-window benchmark (local time, 0–23).
    public var fastingHourStart: Int
    /// Exclusive end-hour for the fasting-window benchmark.
    public var fastingHourEnd: Int

    /// Drop samples with mean BG below this (mg/dL). Protects against low-BG
    /// rescue-carb contamination — a systematic one-sided noise source the
    /// quantile estimator doesn't naturally handle. nil = no floor.
    public var bgMin: Double?
    /// Drop samples with mean BG at or above this (mg/dL). Protects against
    /// CGM sensor clipping at 400. nil = no ceiling.
    public var bgMax: Double?

    public init(
        minInsulinVelocity: Double = 0.05,
        localISFClampLow: Double = -500.0,
        localISFClampHigh: Double = 1000.0,
        iceWindowMinutes: Double = 30,
        mealThreshold: Double = 1.5,
        exerciseThreshold: Double = 1.0,
        minRunMinutes: Double = 20,
        mealTailMinutes: Double = 90,
        exerciseTailMinutes: Double = 60,
        timezone: String? = nil,
        fastingHourStart: Int = 1,
        fastingHourEnd: Int = 4,
        bgMin: Double? = nil,
        bgMax: Double? = nil
    ) {
        self.minInsulinVelocity = minInsulinVelocity
        self.localISFClampLow = localISFClampLow
        self.localISFClampHigh = localISFClampHigh
        self.iceWindowMinutes = iceWindowMinutes
        self.mealThreshold = mealThreshold
        self.exerciseThreshold = exerciseThreshold
        self.minRunMinutes = minRunMinutes
        self.mealTailMinutes = mealTailMinutes
        self.exerciseTailMinutes = exerciseTailMinutes
        self.timezone = timezone
        self.fastingHourStart = fastingHourStart
        self.fastingHourEnd = fastingHourEnd
        self.bgMin = bgMin
        self.bgMax = bgMax
    }
}

public struct ISFStats: Sendable {
    public var count: Int
    public var median: Double
    public var weightedMean: Double
    public var mean: Double
    /// 10/25/50/75/90 percentiles (unweighted).
    public var percentiles: [Double: Double]
}

/// Weighted-OLS line fit `local_ISF(rolling_ICE) ≈ intercept + slope × ICE`,
/// fit over the dense region of the ICE-bin plot.
public struct ISFLineFit: Sendable {
    public var intercept: Double  // mg/dL/U at ICE = 0
    public var slope: Double      // (mg/dL/U) per (mg/dL/min)
    public var rSquared: Double
    public var binsUsed: Int
}

/// One hour-of-day bucket of diurnal analysis.
public struct DiurnalBucket: Sendable {
    /// Local-time hour (0–23).
    public var hour: Int
    /// Total retained samples in this hour across the interval.
    public var n: Int
    /// Subset size: samples whose |rolling_ICE| stayed ≤ 0.3 for ±30 min.
    public var stableN: Int
    /// Median local_ISF over all retained samples in hour.
    public var medianISF: Double
    /// Median local_ISF over the stable subset (NaN if < 5 samples).
    public var stableMedianISF: Double
    /// Median rolling_ICE over all retained samples in hour.
    public var medianICE: Double
}

/// OLS regression of `v_cgm ~ activity × ISF + C` on a "stable-ICE"
/// subset. The subset is defined by: the sample and all its neighbors
/// within ±halfWindowMinutes of it have |rolling_ICE| ≤ thresholdMgdlMin.
/// Slope of `v_cgm` vs signed `activity` directly gives `ISF_true` — the
/// estimate does NOT depend on configured ISF (unlike the ICE-bin fit
/// whose intercept is tautological).
public struct ICEStableRegression: Sendable {
    public var thresholdMgdlMin: Double     // T
    public var halfWindowMinutes: Double    // M/2
    public var n: Int
    public var isfEstimate: Double          // slope (positive)
    public var intercept: Double            // residual C (mg/dL/min)
    public var rSquared: Double
}

/// Quantile regression results for one hour-of-day bin. Slope b of
/// `v_cgm ~ a + b × activity` at τ is the carb-robust ISF for that
/// block of the day; comparing across bins traces the diurnal shape
/// (cortisol dawn dip, post-exercise rise, etc.).
public struct DiurnalQuantileBucket: Sendable {
    /// Inclusive local-time start hour (0–23).
    public var binStartHour: Int
    /// Exclusive local-time end hour. For a 2-hour bin at 4am this is 6.
    public var binEndHour: Int
    public var n: Int
    public var quantile: Double
    public var isfEstimate: Double
    public var intercept: Double
    public var pseudoR2: Double
    /// Median of `isfScheduled` across samples in this bin — the
    /// clinician-configured ISF for comparison against the estimate.
    public var scheduledISF: Double
    /// Median `v_cgm` (mg/dL/min) across the stable-ICE subset of this bin.
    /// Since `v_insulin` is net-of-basal, this is a direct per-bin reading
    /// of scheduled-basal-vs-EGP mismatch: positive = basal under-covers,
    /// negative = basal over-covers. `.nan` if the stable subset is too
    /// small (< 10 samples).
    public var stableMedianVCgm: Double
    /// Number of stable-ICE samples used for `stableMedianVCgm`.
    public var stableN: Int
}

/// Quantile regression of `v_cgm ~ a + b × activity` at the τ-quantile.
/// Rationale: carbs are a one-sided noise source (v_carb ≥ 0 always), so
/// the LOWER envelope of v_cgm as a function of activity is (approximately)
/// carb-free. Quantile regression at a low τ estimates that envelope.
/// Sign convention matches `ICEStableRegression`: `v_insulin < 0` when
/// insulin is lowering BG, so `activity = v_insulin/ISF_sched < 0` during
/// active insulin, and the fitted line has `v_cgm ≈ ISF·activity + C`
/// with **ISF = +slope** (positive when the data is physically sensible).
public struct QuantileRegression: Sendable {
    public var quantile: Double       // τ
    public var n: Int
    public var slope: Double          // b (≈ ISF, positive for real data)
    public var intercept: Double      // a (mg/dL/min)
    public var isfEstimate: Double    // +slope
    /// Pseudo-R² for quantile regression:
    /// 1 − pinball_loss(model) / pinball_loss(intercept_only).
    public var pseudoR2: Double
}

public struct ISFExploreSummary: Sendable {
    public var samplesConsidered: Int
    public var samplesRetained: Int
    public var droppedInsufficientInsulin: Int
    public var droppedClamped: Int
    public var mealCount: Int
    public var exerciseCount: Int
    public var neutralCount: Int
    public var allStats: ISFStats
    public var neutralStats: ISFStats
    /// Local ISF stats restricted to a fasting clock-time window (no
    /// carb/bolus inspection — purely time-of-day).
    public var fastingStats: ISFStats
    /// Weighted-OLS fit of median local_ISF vs rolling_ICE across the dense
    /// ICE-bin region. `intercept` is the data-driven best single estimate
    /// of baseline ISF.
    public var lineFit: ISFLineFit?
    /// Primary stable-ICE regression result (at default T=0.3, halfM=30 min).
    public var primaryStableRegression: ICEStableRegression?
    /// Sweep over thresholds at fixed window.
    public var stableSweepT: [ICEStableRegression]
    /// Sweep over windows at fixed threshold.
    public var stableSweepM: [ICEStableRegression]
    /// Hour-of-day buckets (24 entries, index 0..23 = local hour).
    public var diurnal: [DiurnalBucket]
    /// Insulin delivery rate during stable-ICE windows (EGP proxy).
    public var egp: EGPEstimate?
    /// ISF-invariant: regressions on |activity| ≥ T_act subsets.
    /// Selection uses only `activity = v_insulin / ISF_sched` which is
    /// invariant to the ISF guess — so iteration should not drift.
    public var activitySweep: [ICEStableRegression]
    /// ISF-invariant: regression excluding samples in ±carb-absorption windows
    /// around user-entered carb entries. Independent of ISF guess.
    public var carbExcludedRegression: ICEStableRegression?
    /// Sanity: plain OLS of v_cgm on activity across ALL retained samples.
    /// Biased downward by meal-bolus/carb coupling but gives a fixed
    /// lower-bound reference.
    public var olsAllRegression: ICEStableRegression?
    /// ISF-invariant: quantile regressions at several τ. Low τ (e.g., 0.10)
    /// traces the carb-free lower envelope of v_cgm(activity), so the
    /// estimated slope is a less-biased ISF than OLS-all.
    public var quantileSweep: [QuantileRegression]
    /// Per-hour-of-day quantile regression at τ=0.10 in 2-hour bins.
    /// Traces the diurnal ISF shape (dawn phenomenon, post-exercise rise).
    public var diurnalQuantile: [DiurnalQuantileBucket]
    /// ISF-invariant stable regression: subset defined by |v_cgm| ≤ T
    /// for ±30 min (no reference to v_insulin, so selection does not
    /// drift under an ISF-guess iteration). Threshold sweep.
    public var vCgmStableSweepT: [ICEStableRegression]
}

/// Lightweight Sendable IOB sample (LoopAlgorithm's `InsulinValue` is not Sendable).
public struct IOBPoint: Sendable, Codable {
    public var time: Date
    public var iob: Double
}

public struct ISFExploreResult: Sendable {
    public var samples: [ISFSample]
    public var summary: ISFExploreSummary
    /// Full smoothed CGM (for the BG chart — covers gaps that `samples`
    /// drops when insulin activity is too low).
    public var smoothedCGM: [EvalGlucoseSample]
    /// Full IOB timeline at 5-min cadence over the evaluation window.
    public var iobTimeline: [IOBPoint]
}

/// One bin of the ICE-diagnostic plot.
public struct ICEBin: Sendable {
    /// Mid-point of the rolling-ICE bin (mg/dL/min).
    public var iceMid: Double
    /// Number of samples falling in this bin.
    public var count: Int
    /// |v_insulin|-weighted median of local_ISF within the bin.
    public var weightedMedian: Double
    /// |v_insulin|-weighted mean of local_ISF within the bin.
    public var weightedMean: Double
}

/// Insulin delivery rate during stable-ICE windows, where v_carb ≈ 0 by
/// construction. Treated as a proxy for the insulin needed to cover
/// endogenous glucose production (EGP). Subtract from TDD to isolate
/// carb-covering insulin, then multiply by CR for a carb-intake estimate
/// that doesn't depend on the fictional basal/bolus split.
public struct EGPEstimate: Sendable {
    public var thresholdMgdlMin: Double
    public var halfWindowMinutes: Double
    /// Number of stable-ICE samples contributing.
    public var stableSampleCount: Int
    /// Total observed stable time (minutes).
    public var stableMinutes: Double
    /// Sum of insulin delivered during stable windows (U).
    public var totalUDelivered: Double
    /// Delivery rate (U/min) during stable-ICE windows.
    public var deliveryRatePerMinute: Double
    /// Projected daily delivery rate (U/day) if every hour were stable-ICE.
    public var deliveryRatePerDay: Double
}

public enum ISFExplorer {

    /// Runs the pointwise local-ISF computation on pre-loaded data.
    public static func analyze(
        data: PreloadedData,
        interval: DateInterval,
        options: ISFExploreOptions = ISFExploreOptions()
    ) -> ISFExploreResult {

        // 1. Smooth CGM.
        let smoother = KalmanSmoother()
        let smoothed = smoother.smooth(samples: data.glucose)

        // 2. Modeled insulin-effect time series + IOB timeline.
        let precomputed = data.precomputedInsulinInput(
            for: interval,
            sensitivity: data.therapyTimeline.sensitivity,
            useMidAbsorptionISF: false
        )
        let insulinEffects = precomputed.insulinEffects ?? []

        let effectsStart = insulinEffects.first?.startDate
            ?? interval.start.addingTimeInterval(-15 * 60)
        let effectsEnd = insulinEffects.last?.startDate
            ?? interval.end.addingTimeInterval(15 * 60)
        let rawIOB = precomputed.annotatedDoses.insulinOnBoardTimeline(
            from: effectsStart,
            to: effectsEnd,
            delta: 5 * 60
        )
        let iobTimeline = rawIOB.map { IOBPoint(time: $0.startDate, iob: $0.value) }

        let minVelPerSec = options.minInsulinVelocity / 60.0
        let mgdl = LoopUnit.milligramsPerDeciliter

        var samples: [ISFSample] = []
        var considered = 0
        var droppedInsufficientInsulin = 0
        var droppedClamped = 0

        guard smoothed.count >= 2 else {
            return ISFExploreResult(
                samples: [],
                summary: Self.emptySummary(options: options),
                smoothedCGM: smoothed,
                iobTimeline: iobTimeline
            )
        }

        for i in 1..<smoothed.count {
            let s0 = smoothed[i - 1]
            let s1 = smoothed[i]
            let dt = s1.startDate.timeIntervalSince(s0.startDate)
            guard dt > 4 * 60, dt < 10 * 60 else { continue }
            guard s0.startDate >= interval.start, s1.startDate <= interval.end else {
                continue
            }

            considered += 1

            let bg0 = s0.quantity.doubleValue(for: mgdl)
            let bg1 = s1.quantity.doubleValue(for: mgdl)
            let vCgmPerSec = (bg1 - bg0) / dt

            guard let e0 = Self.interpolateEffect(insulinEffects, at: s0.startDate),
                  let e1 = Self.interpolateEffect(insulinEffects, at: s1.startDate) else {
                continue
            }
            let vInsPerSec = (e1 - e0) / dt

            guard abs(vInsPerSec) >= minVelPerSec else {
                droppedInsufficientInsulin += 1
                continue
            }

            let bgMid = (bg0 + bg1) / 2
            if let bgMin = options.bgMin, bgMid < bgMin { continue }
            if let bgMax = options.bgMax, bgMid >= bgMax { continue }

            let tMid = s0.startDate.addingTimeInterval(dt / 2)
            let isfScheduled = Self.isfAt(tMid, schedule: data.therapyTimeline.sensitivity)
            guard let isfScheduled else { continue }

            let localISF = isfScheduled * (vCgmPerSec / vInsPerSec)
            guard localISF >= options.localISFClampLow,
                  localISF <= options.localISFClampHigh else {
                droppedClamped += 1
                continue
            }

            let iob = Self.interpolateIOB(iobTimeline, at: tMid) ?? 0
            let vCgm = vCgmPerSec * 60
            let vInsulin = vInsPerSec * 60
            let ice = vCgm - vInsulin

            samples.append(ISFSample(
                time: tMid,
                bgSmoothed: (bg0 + bg1) / 2,
                vCgm: vCgm,
                vInsulin: vInsulin,
                ice: ice,
                rollingICE: 0,          // filled in below
                iob: iob,
                isfScheduled: isfScheduled,
                localISF: localISF,
                weight: abs(vInsulin),
                classification: .neutral  // filled in below
            ))
        }

        // 3. Classify each sample.
        Self.classify(samples: &samples, options: options)

        // 4. EGP-coverage delivery-rate estimate (actual doses during stable-ICE windows).
        let egpInterval = DateInterval(
            start: samples.first?.time ?? interval.start,
            end:   samples.last?.time ?? interval.end
        )
        let egp = Self.estimateEGP(
            samples: samples,
            doses: data.doses.filter {
                $0.endDate >= egpInterval.start && $0.startDate <= egpInterval.end
            }
        )

        return ISFExploreResult(
            samples: samples,
            summary: Self.summarize(
                samples: samples,
                considered: considered,
                droppedInsufficientInsulin: droppedInsufficientInsulin,
                droppedClamped: droppedClamped,
                options: options,
                carbs: data.carbs,
                egp: egp
            ),
            smoothedCGM: smoothed,
            iobTimeline: iobTimeline
        )
    }

    // MARK: - Classification

    static func classify(samples: inout [ISFSample], options: ISFExploreOptions) {
        guard !samples.isEmpty else { return }

        // 3a. Centered rolling mean of ICE.
        let halfWindow = options.iceWindowMinutes * 60 / 2
        for i in 0..<samples.count {
            let t = samples[i].time
            var sum = 0.0
            var n = 0
            // Expand left from i.
            var j = i
            while j >= 0, t.timeIntervalSince(samples[j].time) <= halfWindow {
                sum += samples[j].ice
                n += 1
                j -= 1
            }
            // Expand right from i+1.
            j = i + 1
            while j < samples.count, samples[j].time.timeIntervalSince(t) <= halfWindow {
                sum += samples[j].ice
                n += 1
                j += 1
            }
            samples[i].rollingICE = n > 0 ? sum / Double(n) : samples[i].ice
        }

        // 3b. Raw class from rolling ICE.
        var classes = [ISFClass](repeating: .neutral, count: samples.count)
        for i in 0..<samples.count {
            let r = samples[i].rollingICE
            if r > options.mealThreshold {
                classes[i] = .meal
            } else if r < -options.exerciseThreshold {
                classes[i] = .exercise
            }
        }

        // 3c. Min-run filter: collapse short runs back to neutral.
        let minRunSec = options.minRunMinutes * 60
        var i = 0
        while i < classes.count {
            if classes[i] == .neutral { i += 1; continue }
            let runClass = classes[i]
            var j = i
            while j < classes.count, classes[j] == runClass { j += 1 }
            let span = samples[j - 1].time.timeIntervalSince(samples[i].time)
            if span < minRunSec {
                for k in i..<j { classes[k] = .neutral }
            }
            i = j
        }

        // 3d. Tail extension: walk forward, tracking last non-neutral end time
        // for each class, and re-label neutral samples inside a tail window.
        // Priority: if sample falls inside both meal and exercise tail, the
        // more recently ended run wins (neither is neutral-worthy).
        let mealTail = options.mealTailMinutes * 60
        let exTail = options.exerciseTailMinutes * 60
        let base = classes
        var lastMealEnd: Date? = nil
        var lastExEnd: Date? = nil
        for idx in 0..<samples.count {
            let c = base[idx]
            if c == .meal {
                lastMealEnd = samples[idx].time
            } else if c == .exercise {
                lastExEnd = samples[idx].time
            } else {
                let t = samples[idx].time
                let mealActive: Bool = {
                    if let lme = lastMealEnd { return t.timeIntervalSince(lme) <= mealTail }
                    return false
                }()
                let exActive: Bool = {
                    if let lee = lastExEnd { return t.timeIntervalSince(lee) <= exTail }
                    return false
                }()
                if mealActive && exActive {
                    // More recent wins
                    if (lastMealEnd ?? .distantPast) >= (lastExEnd ?? .distantPast) {
                        classes[idx] = .meal
                    } else {
                        classes[idx] = .exercise
                    }
                } else if mealActive {
                    classes[idx] = .meal
                } else if exActive {
                    classes[idx] = .exercise
                }
            }
        }

        // 3e. Write back.
        for idx in 0..<samples.count {
            samples[idx].classification = classes[idx]
        }
    }

    // MARK: - ICE-bin diagnostic

    /// Bin samples by `rollingICE` and report the weighted median / mean of
    /// local_ISF per bin. A flat plateau near rolling_ICE = 0 identifies the
    /// true baseline ISF; the point where the plateau breaks identifies an
    /// empirical threshold for the meal/exercise classifier.
    ///
    /// Samples outside `[iceMin, iceMax)` are dropped (not clipped to edge
    /// bins, to avoid pile-up distortion).
    public static func iceBinDiagnostic(
        samples: [ISFSample],
        iceMin: Double = -5.0,
        iceMax: Double = 5.0,
        binWidth: Double = 0.2
    ) -> [ICEBin] {
        let nBins = max(1, Int(((iceMax - iceMin) / binWidth).rounded()))
        var buckets: [[(val: Double, wt: Double)]] = Array(repeating: [], count: nBins)
        for s in samples {
            let r = s.rollingICE
            guard r >= iceMin, r < iceMax else { continue }
            var idx = Int((r - iceMin) / binWidth)
            if idx < 0 { idx = 0 }
            if idx >= nBins { idx = nBins - 1 }
            buckets[idx].append((s.localISF, s.weight))
        }
        return buckets.enumerated().map { (i, bucket) in
            let mid = iceMin + (Double(i) + 0.5) * binWidth
            guard !bucket.isEmpty else {
                return ICEBin(iceMid: mid, count: 0, weightedMedian: .nan, weightedMean: .nan)
            }
            let sorted = bucket.sorted { $0.val < $1.val }
            let totalW = sorted.reduce(0.0) { $0 + $1.wt }
            let mean: Double = totalW > 0
                ? sorted.reduce(0.0) { $0 + $1.val * $1.wt } / totalW
                : .nan
            // Weighted median: first value where cumulative weight crosses 50%.
            var median = sorted.last!.val
            if totalW > 0 {
                let target = 0.5 * totalW
                var cum = 0.0
                for item in sorted {
                    cum += item.wt
                    if cum >= target {
                        median = item.val
                        break
                    }
                }
            }
            return ICEBin(iceMid: mid, count: bucket.count, weightedMedian: median, weightedMean: mean)
        }
    }

    // MARK: - Helpers

    static func interpolateEffect(_ effects: [GlucoseEffect], at date: Date) -> Double? {
        guard let first = effects.first, let last = effects.last else { return nil }
        guard date >= first.startDate, date <= last.startDate else { return nil }
        var lo = 0
        var hi = effects.count - 1
        while hi - lo > 1 {
            let mid = (lo + hi) / 2
            if effects[mid].startDate <= date { lo = mid } else { hi = mid }
        }
        let a = effects[lo]
        let b = effects[hi]
        let span = b.startDate.timeIntervalSince(a.startDate)
        let mgdl = LoopUnit.milligramsPerDeciliter
        if span <= 0 { return a.quantity.doubleValue(for: mgdl) }
        let t = date.timeIntervalSince(a.startDate) / span
        let va = a.quantity.doubleValue(for: mgdl)
        let vb = b.quantity.doubleValue(for: mgdl)
        return va + t * (vb - va)
    }

    static func interpolateIOB(_ values: [IOBPoint], at date: Date) -> Double? {
        guard let first = values.first, let last = values.last else { return nil }
        guard date >= first.time, date <= last.time else { return nil }
        var lo = 0
        var hi = values.count - 1
        while hi - lo > 1 {
            let mid = (lo + hi) / 2
            if values[mid].time <= date { lo = mid } else { hi = mid }
        }
        let a = values[lo]
        let b = values[hi]
        let span = b.time.timeIntervalSince(a.time)
        if span <= 0 { return a.iob }
        let t = date.timeIntervalSince(a.time) / span
        return a.iob + t * (b.iob - a.iob)
    }

    static func isfAt(
        _ date: Date,
        schedule: [AbsoluteScheduleValue<LoopQuantity>]
    ) -> Double? {
        let mgdl = LoopUnit.milligramsPerDeciliter
        for entry in schedule {
            if date >= entry.startDate && date < entry.endDate {
                return entry.value.doubleValue(for: mgdl)
            }
        }
        if let last = schedule.last, date >= last.startDate {
            return last.value.doubleValue(for: mgdl)
        }
        return nil
    }

    // MARK: - Summary

    static func summarize(
        samples: [ISFSample],
        considered: Int,
        droppedInsufficientInsulin: Int,
        droppedClamped: Int,
        options: ISFExploreOptions,
        carbs: [EvalCarbEntry] = [],
        egp: EGPEstimate? = nil
    ) -> ISFExploreSummary {
        let allStats = Self.stats(samples: samples)
        let neutral = samples.filter { $0.classification == .neutral }
        let neutralStats = Self.stats(samples: neutral)
        let fasting = Self.fastingFilter(samples: samples, options: options)
        let fastingStats = Self.stats(samples: fasting)
        let bins = Self.iceBinDiagnostic(samples: samples)
        let lineFit = Self.fitLineToBins(bins)

        // Stable-ICE regression — primary estimate + two sweeps.
        let primary = Self.iceStableRegression(
            samples: samples, threshold: 0.3, halfWindowMinutes: 30
        )
        let sweepT = Self.iceStableSweepT(
            samples: samples,
            thresholds: [0.1, 0.15, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5],
            halfWindowMinutes: 30
        )
        let sweepM = Self.iceStableSweepM(
            samples: samples,
            halfWindowMinutes: [10, 15, 20, 30, 45, 60, 90],
            threshold: 0.3
        )

        let diurnal = Self.diurnalAnalysis(samples: samples, options: options)

        // ISF-invariant regressions — selection logic does not depend on ISF.
        let actSweep = Self.activitySweep(
            samples: samples,
            thresholds: [0.001, 0.002, 0.003, 0.005, 0.008, 0.012, 0.018]
        )
        let carbExcluded = Self.carbExcludedRegression(
            samples: samples, carbs: carbs, preMinutes: 15, postMinutes: 240
        )
        let olsAll = Self.olsAll(samples: samples)
        let quantileSweep = Self.quantileSweep(
            samples: samples,
            quantiles: [0.05, 0.10, 0.15, 0.25, 0.50]
        )
        let diurnalQuantile = Self.diurnalQuantileAnalysis(
            samples: samples, options: options, binHours: 2, quantile: 0.10
        )
        let vCgmSweepT = Self.vCgmStableSweepT(
            samples: samples,
            thresholds: [0.1, 0.15, 0.2, 0.3, 0.5],
            halfWindowMinutes: 30
        )

        return ISFExploreSummary(
            samplesConsidered: considered,
            samplesRetained: samples.count,
            droppedInsufficientInsulin: droppedInsufficientInsulin,
            droppedClamped: droppedClamped,
            mealCount: samples.filter { $0.classification == .meal }.count,
            exerciseCount: samples.filter { $0.classification == .exercise }.count,
            neutralCount: neutral.count,
            allStats: allStats,
            neutralStats: neutralStats,
            fastingStats: fastingStats,
            lineFit: lineFit,
            primaryStableRegression: primary,
            stableSweepT: sweepT,
            stableSweepM: sweepM,
            diurnal: diurnal,
            egp: egp,
            activitySweep: actSweep,
            carbExcludedRegression: carbExcluded,
            olsAllRegression: olsAll,
            quantileSweep: quantileSweep,
            diurnalQuantile: diurnalQuantile,
            vCgmStableSweepT: vCgmSweepT
        )
    }

    /// Samples whose local-time hour falls in `[fastingHourStart, fastingHourEnd)`.
    /// No inspection of dose/carb history — purely time-of-day.
    static func fastingFilter(
        samples: [ISFSample],
        options: ISFExploreOptions
    ) -> [ISFSample] {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = options.timezone.flatMap { TimeZone(identifier: $0) } ?? .current
        let lo = options.fastingHourStart
        let hi = options.fastingHourEnd
        return samples.filter { s in
            let h = cal.component(.hour, from: s.time)
            return h >= lo && h < hi
        }
    }

    // MARK: - Stable-ICE regression

    /// Returns `true` if the sample at `i` and all samples within
    /// ±halfWindowSec have `|rollingICE| ≤ threshold`.
    static func isIceStable(
        samples: [ISFSample],
        index i: Int,
        threshold: Double,
        halfWindowSec: Double
    ) -> Bool {
        if abs(samples[i].rollingICE) > threshold { return false }
        let t = samples[i].time
        // Walk backward.
        var j = i - 1
        while j >= 0, t.timeIntervalSince(samples[j].time) <= halfWindowSec {
            if abs(samples[j].rollingICE) > threshold { return false }
            j -= 1
        }
        // Walk forward.
        j = i + 1
        while j < samples.count, samples[j].time.timeIntervalSince(t) <= halfWindowSec {
            if abs(samples[j].rollingICE) > threshold { return false }
            j += 1
        }
        return true
    }

    /// Fit `v_cgm = slope × (v_insulin / isfScheduled) + intercept` on the
    /// "stable-ICE" subset. Slope is positive (equals ISF_true under the
    /// linear model v_cgm = activity_signed × ISF_true + C, where
    /// activity_signed = v_insulin / isfScheduled is < 0 under insulin action).
    public static func iceStableRegression(
        samples: [ISFSample],
        threshold: Double,
        halfWindowMinutes: Double
    ) -> ICEStableRegression? {
        let halfSec = halfWindowMinutes * 60
        var xs: [Double] = []
        var ys: [Double] = []
        xs.reserveCapacity(samples.count)
        ys.reserveCapacity(samples.count)
        for i in 0..<samples.count {
            guard Self.isIceStable(
                samples: samples, index: i,
                threshold: threshold, halfWindowSec: halfSec
            ) else { continue }
            // Activity in units-per-minute-ish (mg/dL/min) / (mg/dL/U) = U/min.
            // Signed: negative under normal insulin action.
            let s = samples[i]
            guard s.isfScheduled > 0 else { continue }
            xs.append(s.vInsulin / s.isfScheduled)
            ys.append(s.vCgm)
        }
        let n = xs.count
        guard n >= 10 else { return nil }

        let nD = Double(n)
        let meanX = xs.reduce(0, +) / nD
        let meanY = ys.reduce(0, +) / nD
        var cov = 0.0, varX = 0.0
        for k in 0..<n {
            cov  += (xs[k] - meanX) * (ys[k] - meanY)
            varX += (xs[k] - meanX) * (xs[k] - meanX)
        }
        guard varX > 1e-12 else { return nil }
        let slope = cov / varX
        let intercept = meanY - slope * meanX

        var ssTot = 0.0, ssRes = 0.0
        for k in 0..<n {
            ssTot += (ys[k] - meanY) * (ys[k] - meanY)
            let pred = slope * xs[k] + intercept
            ssRes += (ys[k] - pred) * (ys[k] - pred)
        }
        let r2 = ssTot > 0 ? 1 - ssRes / ssTot : 0

        return ICEStableRegression(
            thresholdMgdlMin: threshold,
            halfWindowMinutes: halfWindowMinutes,
            n: n,
            isfEstimate: slope,
            intercept: intercept,
            rSquared: r2
        )
    }

    /// Sweep over `thresholds` at fixed window; drops nil results.
    public static func iceStableSweepT(
        samples: [ISFSample],
        thresholds: [Double],
        halfWindowMinutes: Double
    ) -> [ICEStableRegression] {
        thresholds.compactMap {
            Self.iceStableRegression(
                samples: samples,
                threshold: $0,
                halfWindowMinutes: halfWindowMinutes
            )
        }
    }

    // MARK: - v_cgm-stable regression (ISF-invariant selection)

    /// Returns `true` if the sample at `i` and all samples within
    /// ±halfWindowSec have `|vCgm| ≤ threshold`. Unlike `isIceStable`,
    /// this selector does not reference `v_insulin` and therefore is
    /// independent of the ISF schedule — iteration cannot drift via
    /// subset reselection.
    static func isVCgmStable(
        samples: [ISFSample],
        index i: Int,
        threshold: Double,
        halfWindowSec: Double
    ) -> Bool {
        if abs(samples[i].vCgm) > threshold { return false }
        let t = samples[i].time
        var j = i - 1
        while j >= 0, t.timeIntervalSince(samples[j].time) <= halfWindowSec {
            if abs(samples[j].vCgm) > threshold { return false }
            j -= 1
        }
        j = i + 1
        while j < samples.count, samples[j].time.timeIntervalSince(t) <= halfWindowSec {
            if abs(samples[j].vCgm) > threshold { return false }
            j += 1
        }
        return true
    }

    /// Same OLS fit as `iceStableRegression` but restricted to samples
    /// whose neighbourhood has |v_cgm| ≤ threshold. Selection is ISF-
    /// invariant — iterating `ISF_guess → slope` should be a fixed
    /// point (up to noise), unlike the ICE-stable variant whose subset
    /// shifts with the guess.
    public static func vCgmStableRegression(
        samples: [ISFSample],
        threshold: Double,
        halfWindowMinutes: Double
    ) -> ICEStableRegression? {
        let halfSec = halfWindowMinutes * 60
        var xs: [Double] = []
        var ys: [Double] = []
        xs.reserveCapacity(samples.count)
        ys.reserveCapacity(samples.count)
        for i in 0..<samples.count {
            guard Self.isVCgmStable(
                samples: samples, index: i,
                threshold: threshold, halfWindowSec: halfSec
            ) else { continue }
            let s = samples[i]
            guard s.isfScheduled > 0 else { continue }
            xs.append(s.vInsulin / s.isfScheduled)
            ys.append(s.vCgm)
        }
        let n = xs.count
        guard n >= 10 else { return nil }

        let nD = Double(n)
        let meanX = xs.reduce(0, +) / nD
        let meanY = ys.reduce(0, +) / nD
        var cov = 0.0, varX = 0.0
        for k in 0..<n {
            cov  += (xs[k] - meanX) * (ys[k] - meanY)
            varX += (xs[k] - meanX) * (xs[k] - meanX)
        }
        guard varX > 1e-12 else { return nil }
        let slope = cov / varX
        let intercept = meanY - slope * meanX

        var ssTot = 0.0, ssRes = 0.0
        for k in 0..<n {
            ssTot += (ys[k] - meanY) * (ys[k] - meanY)
            let pred = slope * xs[k] + intercept
            ssRes += (ys[k] - pred) * (ys[k] - pred)
        }
        let r2 = ssTot > 0 ? 1 - ssRes / ssTot : 0

        return ICEStableRegression(
            thresholdMgdlMin: threshold,
            halfWindowMinutes: halfWindowMinutes,
            n: n,
            isfEstimate: slope,
            intercept: intercept,
            rSquared: r2
        )
    }

    public static func vCgmStableSweepT(
        samples: [ISFSample],
        thresholds: [Double],
        halfWindowMinutes: Double
    ) -> [ICEStableRegression] {
        thresholds.compactMap {
            Self.vCgmStableRegression(
                samples: samples,
                threshold: $0,
                halfWindowMinutes: halfWindowMinutes
            )
        }
    }

    // MARK: - Diurnal analysis

    /// For each hour of local day (0–23), report sample count, median local_ISF,
    /// stable-subset median local_ISF, and median rolling_ICE. Timezone from
    /// options (defaults to system local).
    public static func diurnalAnalysis(
        samples: [ISFSample],
        options: ISFExploreOptions,
        stableThreshold: Double = 0.3,
        stableHalfWindowMinutes: Double = 30
    ) -> [DiurnalBucket] {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = options.timezone.flatMap { TimeZone(identifier: $0) } ?? .current
        let halfSec = stableHalfWindowMinutes * 60

        // Pre-compute stability mask (O(N) on average given bounded window).
        var stable = [Bool](repeating: false, count: samples.count)
        for i in 0..<samples.count {
            stable[i] = Self.isIceStable(
                samples: samples, index: i,
                threshold: stableThreshold, halfWindowSec: halfSec
            )
        }

        var isfByHour: [[Double]] = Array(repeating: [], count: 24)
        var stableIsfByHour: [[Double]] = Array(repeating: [], count: 24)
        var iceByHour: [[Double]] = Array(repeating: [], count: 24)
        for i in 0..<samples.count {
            let h = cal.component(.hour, from: samples[i].time)
            guard h >= 0, h < 24 else { continue }
            isfByHour[h].append(samples[i].localISF)
            iceByHour[h].append(samples[i].rollingICE)
            if stable[i] { stableIsfByHour[h].append(samples[i].localISF) }
        }

        func median(_ vs: [Double]) -> Double {
            guard !vs.isEmpty else { return .nan }
            let s = vs.sorted()
            let n = s.count
            return n.isMultiple(of: 2) ? (s[n/2 - 1] + s[n/2]) / 2 : s[n/2]
        }

        return (0..<24).map { h in
            DiurnalBucket(
                hour: h,
                n: isfByHour[h].count,
                stableN: stableIsfByHour[h].count,
                medianISF: median(isfByHour[h]),
                stableMedianISF: stableIsfByHour[h].count >= 5
                    ? median(stableIsfByHour[h]) : .nan,
                medianICE: median(iceByHour[h])
            )
        }
    }

    /// Sweep over `halfWindowMinutes` at fixed threshold; drops nil results.
    // MARK: - EGP delivery-rate estimator

    /// Sum actual insulin delivered during stable-ICE windows (where v_carb ≈ 0
    /// by selection) and divide by total stable minutes to get a U/min rate.
    /// Scaled to U/day gives the daily insulin needed to cover endogenous
    /// glucose production when carbs are absent.
    public static func estimateEGP(
        samples: [ISFSample],
        doses: [EvalInsulinDose],
        threshold: Double = 0.3,
        halfWindowMinutes: Double = 30,
        sampleWindowSec: Double = 300
    ) -> EGPEstimate? {
        let halfSec = halfWindowMinutes * 60
        let wHalf = sampleWindowSec / 2

        var stableIdx: [Int] = []
        stableIdx.reserveCapacity(samples.count / 8)
        for i in 0..<samples.count {
            if Self.isIceStable(
                samples: samples, index: i,
                threshold: threshold, halfWindowSec: halfSec
            ) {
                stableIdx.append(i)
            }
        }
        guard !stableIdx.isEmpty, !doses.isEmpty else { return nil }

        let sortedDoses = doses.sorted { $0.startDate < $1.startDate }
        // Running left pointer into sortedDoses; stable samples are time-sorted
        // too (since `samples` is chronological).
        var left = 0
        var totalU = 0.0

        for idx in stableIdx {
            let t = samples[idx].time
            let wLo = t.addingTimeInterval(-wHalf)
            let wHi = t.addingTimeInterval(wHalf)

            // Advance `left` past doses that end strictly before this window.
            while left < sortedDoses.count,
                  sortedDoses[left].endDate < wLo {
                left += 1
            }

            var j = left
            while j < sortedDoses.count,
                  sortedDoses[j].startDate <= wHi {
                let d = sortedDoses[j]
                let dur = d.endDate.timeIntervalSince(d.startDate)
                if dur <= 0 {
                    // Instantaneous bolus — count full volume if inside window.
                    if d.startDate >= wLo, d.startDate <= wHi {
                        totalU += d.volume
                    }
                } else {
                    let ovLo = max(d.startDate, wLo)
                    let ovHi = min(d.endDate, wHi)
                    let overlap = ovHi.timeIntervalSince(ovLo)
                    if overlap > 0 {
                        totalU += d.volume * overlap / dur
                    }
                }
                j += 1
            }
        }

        let stableMinutes = Double(stableIdx.count) * (sampleWindowSec / 60)
        let ratePerMin = stableMinutes > 0 ? totalU / stableMinutes : 0
        return EGPEstimate(
            thresholdMgdlMin: threshold,
            halfWindowMinutes: halfWindowMinutes,
            stableSampleCount: stableIdx.count,
            stableMinutes: stableMinutes,
            totalUDelivered: totalU,
            deliveryRatePerMinute: ratePerMin,
            deliveryRatePerDay: ratePerMin * 1440
        )
    }

    public static func iceStableSweepM(
        samples: [ISFSample],
        halfWindowMinutes: [Double],
        threshold: Double
    ) -> [ICEStableRegression] {
        halfWindowMinutes.compactMap {
            Self.iceStableRegression(
                samples: samples,
                threshold: threshold,
                halfWindowMinutes: $0
            )
        }
    }

    // MARK: - ISF-invariant regressions

    /// OLS of `v_cgm ~ activity` over a caller-supplied predicate.
    /// Unlike stable-ICE, the predicate does NOT have to depend on ISF
    /// — it can be a pure physical selection. `label` is written into
    /// `thresholdMgdlMin` for readability in sweeps.
    static func olsSelected(
        samples: [ISFSample],
        label: Double,
        halfWindowMinutes: Double = 0,
        keep: (ISFSample) -> Bool
    ) -> ICEStableRegression? {
        var xs: [Double] = []
        var ys: [Double] = []
        xs.reserveCapacity(samples.count)
        ys.reserveCapacity(samples.count)
        for s in samples {
            guard s.isfScheduled > 0, keep(s) else { continue }
            xs.append(s.vInsulin / s.isfScheduled)
            ys.append(s.vCgm)
        }
        let n = xs.count
        guard n >= 10 else { return nil }

        let nD = Double(n)
        let meanX = xs.reduce(0, +) / nD
        let meanY = ys.reduce(0, +) / nD
        var cov = 0.0, varX = 0.0
        for k in 0..<n {
            cov  += (xs[k] - meanX) * (ys[k] - meanY)
            varX += (xs[k] - meanX) * (xs[k] - meanX)
        }
        guard varX > 1e-12 else { return nil }
        let slope = cov / varX
        let intercept = meanY - slope * meanX

        var ssTot = 0.0, ssRes = 0.0
        for k in 0..<n {
            ssTot += (ys[k] - meanY) * (ys[k] - meanY)
            let pred = slope * xs[k] + intercept
            ssRes += (ys[k] - pred) * (ys[k] - pred)
        }
        let r2 = ssTot > 0 ? 1 - ssRes / ssTot : 0

        return ICEStableRegression(
            thresholdMgdlMin: label,
            halfWindowMinutes: halfWindowMinutes,
            n: n,
            isfEstimate: slope,
            intercept: intercept,
            rSquared: r2
        )
    }

    /// |activity| ≥ threshold selection. Activity = v_insulin / ISF_sched is
    /// ISF-invariant, so the subset and the resulting slope do not depend on
    /// which ISF was plugged into the insulin model.
    public static func activityRegression(
        samples: [ISFSample],
        minAbsActivity: Double
    ) -> ICEStableRegression? {
        olsSelected(samples: samples, label: minAbsActivity) { s in
            abs(s.vInsulin / s.isfScheduled) >= minAbsActivity
        }
    }

    public static func activitySweep(
        samples: [ISFSample],
        thresholds: [Double]
    ) -> [ICEStableRegression] {
        thresholds.compactMap {
            Self.activityRegression(samples: samples, minAbsActivity: $0)
        }
    }

    /// Drop samples inside `[carb_time − preMinutes, carb_time + postMinutes]`
    /// of any user-entered carb entry. Selection is physical — no ISF
    /// dependence at all — so iteration on ISF cannot drift this estimate.
    /// Unannounced meals remain as carb-contamination noise.
    public static func carbExcludedRegression(
        samples: [ISFSample],
        carbs: [EvalCarbEntry],
        preMinutes: Double = 15,
        postMinutes: Double = 240
    ) -> ICEStableRegression? {
        let preSec = preMinutes * 60
        let postSec = postMinutes * 60
        let sortedCarbs = carbs.sorted { $0.startDate < $1.startDate }

        // For each sample, O(log + k) lookup of nearby carbs via running
        // left pointer (samples are chronological).
        var left = 0
        return olsSelected(samples: samples, label: postMinutes) { s in
            // Advance `left` past carbs whose post-window ends before this sample.
            while left < sortedCarbs.count,
                  s.time.timeIntervalSince(sortedCarbs[left].startDate) > postSec {
                left += 1
            }
            var j = left
            while j < sortedCarbs.count {
                let dt = s.time.timeIntervalSince(sortedCarbs[j].startDate)
                if dt < -preSec { break }          // carb is too far in the future
                if dt >= -preSec && dt <= postSec {
                    return false                    // inside exclusion window
                }
                j += 1
            }
            return true
        }
    }

    /// Plain OLS on all retained samples. Biased downward by meal-bolus/carb
    /// coupling; useful as a fixed lower-bound reference.
    public static func olsAll(samples: [ISFSample]) -> ICEStableRegression? {
        olsSelected(samples: samples, label: 0) { _ in true }
    }

    // MARK: - Quantile regression

    /// Quantile regression of `v_cgm` on `activity = v_insulin / ISF_sched`
    /// at a single quantile τ. Minimises the pinball loss
    ///   ρ_τ(r) = r·(τ − 𝟙[r<0])
    /// by exploiting that, for any fixed slope b, the optimal intercept a
    /// is the τ-quantile of `y_i − b·x_i`. The problem reduces to a 1-D
    /// convex search over b, solved by grid + refinement.
    ///
    /// At low τ (e.g., 0.10) the fit traces the lower envelope of
    /// v_cgm(activity) — which approximates the carb-free scenario because
    /// `v_carb ≥ 0` is one-sided noise. Using this codebase's sign
    /// convention (`v_insulin < 0`, `activity < 0` when insulin active),
    /// the fitted line is `v_cgm ≈ ISF·activity + C` and **ISF = +slope**.
    /// So τ=0.10 gives a carb-robust ISF estimate that (unlike
    /// carb-exclusion) doesn't depend on carbs being announced.
    public static func quantileRegression(
        samples: [ISFSample],
        quantile tau: Double,
        minSampleCount: Int = 50
    ) -> QuantileRegression? {
        precondition(tau > 0 && tau < 1, "quantile must be in (0,1)")
        var xs: [Double] = []
        var ys: [Double] = []
        xs.reserveCapacity(samples.count)
        ys.reserveCapacity(samples.count)
        for s in samples {
            guard s.isfScheduled > 0 else { continue }
            xs.append(s.vInsulin / s.isfScheduled)
            ys.append(s.vCgm)
        }
        guard xs.count >= minSampleCount else { return nil }
        return Self.solveQuantileRegression(xs: xs, ys: ys, tau: tau)
    }

    /// Quantile regression in log-BG space. Fits `d(ln BG)/dt = k · activity`,
    /// then scales by `refBG` so the slope is expressed as an effective ISF
    /// at that reference glucose level.
    ///
    /// Equivalently: `y_i = v_cgm_i × refBG / bgSmoothed_i`, x_i = activity_i.
    /// When every sample has `bgSmoothed == refBG`, the output matches the
    /// linear estimator exactly. The log model captures the multiplicative
    /// nature of insulin action (same U drops more mg/dL at high BG than low
    /// BG) by removing that BG-dependence from the noise term.
    ///
    /// - Parameter referenceBG: BG level at which the slope is reported
    ///   (default 150 mg/dL — middle of the 70–180 target range).
    public static func quantileRegressionLog(
        samples: [ISFSample],
        quantile tau: Double,
        referenceBG: Double = 150,
        minSampleCount: Int = 50
    ) -> QuantileRegression? {
        precondition(tau > 0 && tau < 1, "quantile must be in (0,1)")
        precondition(referenceBG > 0, "referenceBG must be positive")

        var xs: [Double] = []
        var ys: [Double] = []
        xs.reserveCapacity(samples.count)
        ys.reserveCapacity(samples.count)
        for s in samples {
            guard s.isfScheduled > 0, s.bgSmoothed > 0 else { continue }
            xs.append(s.vInsulin / s.isfScheduled)
            ys.append(s.vCgm * referenceBG / s.bgSmoothed)
        }
        guard xs.count >= minSampleCount else { return nil }
        return Self.solveQuantileRegression(xs: xs, ys: ys, tau: tau)
    }

    public static func quantileSweep(
        samples: [ISFSample],
        quantiles: [Double]
    ) -> [QuantileRegression] {
        quantiles.compactMap {
            Self.quantileRegression(samples: samples, quantile: $0)
        }
    }

    /// Shared solver for pinball-loss minimisation on (xs, ys) at τ.
    /// Uses the fact that for fixed slope b, the optimal intercept is the
    /// τ-quantile of (y − b·x), so the problem reduces to a 1-D convex
    /// search over b. Grid + zoom-refine covers ISF in ~[−100, +500].
    static func solveQuantileRegression(
        xs: [Double], ys: [Double], tau: Double
    ) -> QuantileRegression? {
        let n = xs.count
        guard n >= 20 else { return nil }

        var scratch = [Double](repeating: 0, count: n)

        func tauQuantile(_ buf: inout [Double]) -> Double {
            buf.sort()
            let idx = Int(tau * Double(n - 1))
            let frac = tau * Double(n - 1) - Double(idx)
            if idx >= n - 1 { return buf[n - 1] }
            return buf[idx] * (1 - frac) + buf[idx + 1] * frac
        }

        func lossForSlope(_ b: Double) -> (loss: Double, a: Double) {
            for i in 0..<n { scratch[i] = ys[i] - b * xs[i] }
            let a = tauQuantile(&scratch)
            var loss = 0.0
            for i in 0..<n {
                let r = ys[i] - a - b * xs[i]
                loss += r >= 0 ? tau * r : (tau - 1) * r
            }
            return (loss, a)
        }

        // Coarse grid over the physically plausible ISF range (in this
        // codebase's sign convention, ISF ≈ +slope; allow negative for
        // robustness to degenerate fasting/exercise windows).
        var best: (b: Double, a: Double, loss: Double) = (0, 0, .infinity)
        var b = -100.0
        while b <= 500.0 {
            let r = lossForSlope(b)
            if r.loss < best.loss { best = (b, r.a, r.loss) }
            b += 20
        }
        // Refine in four zoom passes: step shrinks by 5× each pass.
        var step = 20.0
        for _ in 0..<4 {
            step /= 5
            let center = best.b
            var bb = center - 5 * step
            while bb <= center + 5 * step {
                let r = lossForSlope(bb)
                if r.loss < best.loss { best = (bb, r.a, r.loss) }
                bb += step
            }
        }

        // Null (intercept-only) loss for pseudo-R².
        for i in 0..<n { scratch[i] = ys[i] }
        let nullA = tauQuantile(&scratch)
        var nullLoss = 0.0
        for i in 0..<n {
            let r = ys[i] - nullA
            nullLoss += r >= 0 ? tau * r : (tau - 1) * r
        }
        let pseudo = nullLoss > 0 ? max(0, 1 - best.loss / nullLoss) : 0

        return QuantileRegression(
            quantile: tau,
            n: n,
            slope: best.b,
            intercept: best.a,
            isfEstimate: best.b,
            pseudoR2: pseudo
        )
    }

    // MARK: - Diurnal quantile regression

    /// Bin samples by local time-of-day into contiguous `binHours`-wide
    /// blocks and fit quantile regression per bin at τ. Gives a per-hour
    /// carb-robust ISF curve, exposing the diurnal shape (dawn dip, etc.).
    public static func diurnalQuantileAnalysis(
        samples: [ISFSample],
        options: ISFExploreOptions,
        binHours: Int = 2,
        quantile tau: Double = 0.10,
        stableThreshold: Double = 0.30,
        stableHalfWindowMinutes: Double = 30
    ) -> [DiurnalQuantileBucket] {
        precondition(binHours >= 1 && 24 % binHours == 0,
                     "binHours must be a divisor of 24")
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = options.timezone.flatMap { TimeZone(identifier: $0) } ?? .current

        let nBins = 24 / binHours

        // Precompute stable-ICE membership once (same criterion as the
        // primary stable-ICE regression). Traversing samples[] once lets
        // the per-bin stable-median v_cgm be computed cheaply.
        let halfSec = stableHalfWindowMinutes * 60
        var isStable = [Bool](repeating: false, count: samples.count)
        for i in 0..<samples.count {
            isStable[i] = Self.isIceStable(
                samples: samples, index: i,
                threshold: stableThreshold, halfWindowSec: halfSec
            )
        }

        var xsByBin: [[Double]] = Array(repeating: [], count: nBins)
        var ysByBin: [[Double]] = Array(repeating: [], count: nBins)
        var schedByBin: [[Double]] = Array(repeating: [], count: nBins)
        var stableVCgmByBin: [[Double]] = Array(repeating: [], count: nBins)
        for (i, s) in samples.enumerated() {
            guard s.isfScheduled > 0 else { continue }
            let h = cal.component(.hour, from: s.time)
            guard h >= 0, h < 24 else { continue }
            let bin = h / binHours
            xsByBin[bin].append(s.vInsulin / s.isfScheduled)
            ysByBin[bin].append(s.vCgm)
            schedByBin[bin].append(s.isfScheduled)
            if isStable[i] {
                stableVCgmByBin[bin].append(s.vCgm)
            }
        }

        func median(_ vs: [Double]) -> Double {
            guard !vs.isEmpty else { return .nan }
            let s = vs.sorted()
            let n = s.count
            return n.isMultiple(of: 2) ? (s[n/2 - 1] + s[n/2]) / 2 : s[n/2]
        }

        var out: [DiurnalQuantileBucket] = []
        out.reserveCapacity(nBins)
        for bin in 0..<nBins {
            let startHour = bin * binHours
            let endHour = startHour + binHours
            let schedISF = median(schedByBin[bin])
            let stableN = stableVCgmByBin[bin].count
            let stableMedian = stableN >= 10 ? median(stableVCgmByBin[bin]) : .nan

            guard let qr = Self.solveQuantileRegression(
                xs: xsByBin[bin], ys: ysByBin[bin], tau: tau
            ) else {
                out.append(DiurnalQuantileBucket(
                    binStartHour: startHour, binEndHour: endHour,
                    n: xsByBin[bin].count, quantile: tau,
                    isfEstimate: .nan, intercept: .nan, pseudoR2: .nan,
                    scheduledISF: schedISF,
                    stableMedianVCgm: stableMedian, stableN: stableN
                ))
                continue
            }
            out.append(DiurnalQuantileBucket(
                binStartHour: startHour, binEndHour: endHour,
                n: qr.n, quantile: tau,
                isfEstimate: qr.isfEstimate,
                intercept: qr.intercept,
                pseudoR2: qr.pseudoR2,
                scheduledISF: schedISF,
                stableMedianVCgm: stableMedian, stableN: stableN
            ))
        }
        return out
    }

    /// Weighted-OLS line fit of `bin.weightedMedian = a + b × bin.iceMid`,
    /// restricted to bins with sample count ≥ 5 and |iceMid| ≤ 2.0.
    /// Weight is the bin count.
    static func fitLineToBins(_ bins: [ICEBin]) -> ISFLineFit? {
        let usable = bins.filter { bin in
            bin.count >= 5 &&
            abs(bin.iceMid) <= 2.0 &&
            !bin.weightedMedian.isNaN
        }
        guard usable.count >= 3 else { return nil }

        let W = usable.reduce(0.0) { $0 + Double($1.count) }
        let meanX = usable.reduce(0.0) { $0 + Double($1.count) * $1.iceMid } / W
        let meanY = usable.reduce(0.0) { $0 + Double($1.count) * $1.weightedMedian } / W
        let cov = usable.reduce(0.0) {
            $0 + Double($1.count) * ($1.iceMid - meanX) * ($1.weightedMedian - meanY)
        }
        let varX = usable.reduce(0.0) {
            $0 + Double($1.count) * pow($1.iceMid - meanX, 2)
        }
        guard varX > 0 else { return nil }
        let slope = cov / varX
        let intercept = meanY - slope * meanX

        // R² using weighted total / residual SS.
        let ssTot = usable.reduce(0.0) {
            $0 + Double($1.count) * pow($1.weightedMedian - meanY, 2)
        }
        let ssRes = usable.reduce(0.0) { acc, bin in
            let pred = intercept + slope * bin.iceMid
            return acc + Double(bin.count) * pow(bin.weightedMedian - pred, 2)
        }
        let r2 = ssTot > 0 ? 1 - ssRes / ssTot : 0

        return ISFLineFit(
            intercept: intercept,
            slope: slope,
            rSquared: r2,
            binsUsed: usable.count
        )
    }

    static func stats(samples: [ISFSample]) -> ISFStats {
        guard !samples.isEmpty else {
            return ISFStats(count: 0, median: .nan, weightedMean: .nan, mean: .nan, percentiles: [:])
        }
        let values = samples.map { $0.localISF }
        let weights = samples.map { $0.weight }
        let totalWeight = weights.reduce(0, +)
        let weightedSum = zip(values, weights).map(*).reduce(0, +)
        let weightedMean = totalWeight > 0 ? weightedSum / totalWeight : .nan
        let mean = values.reduce(0, +) / Double(values.count)
        let sorted = values.sorted()
        func pct(_ p: Double) -> Double {
            let rank = p * Double(sorted.count - 1)
            let lo = Int(floor(rank))
            let hi = Int(ceil(rank))
            if lo == hi { return sorted[lo] }
            let f = rank - Double(lo)
            return sorted[lo] + f * (sorted[hi] - sorted[lo])
        }
        return ISFStats(
            count: samples.count,
            median: pct(0.50),
            weightedMean: weightedMean,
            mean: mean,
            percentiles: [
                0.10: pct(0.10),
                0.25: pct(0.25),
                0.50: pct(0.50),
                0.75: pct(0.75),
                0.90: pct(0.90)
            ]
        )
    }

    static func emptySummary(options: ISFExploreOptions = ISFExploreOptions()) -> ISFExploreSummary {
        let empty = ISFStats(count: 0, median: .nan, weightedMean: .nan, mean: .nan, percentiles: [:])
        return ISFExploreSummary(
            samplesConsidered: 0,
            samplesRetained: 0,
            droppedInsufficientInsulin: 0,
            droppedClamped: 0,
            mealCount: 0,
            exerciseCount: 0,
            neutralCount: 0,
            allStats: empty,
            neutralStats: empty,
            fastingStats: empty,
            lineFit: nil,
            primaryStableRegression: nil,
            stableSweepT: [],
            stableSweepM: [],
            diurnal: [],
            egp: nil,
            activitySweep: [],
            carbExcludedRegression: nil,
            olsAllRegression: nil,
            quantileSweep: [],
            diurnalQuantile: [],
            vCgmStableSweepT: []
        )
    }
}
