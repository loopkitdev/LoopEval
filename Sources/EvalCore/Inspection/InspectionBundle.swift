// InspectionBundle.swift — rich data bundle for visualization / debugging

import Foundation
import LoopAlgorithm

// MARK: – Supporting types

/// A single timestamped glucose value (raw or smoothed) for charting.
public struct GlucosePoint: Codable, Sendable {
    public let t: Double   // Unix timestamp (ms, for JS Date compatibility)
    public let v: Double   // mg/dL

    public init(date: Date, mgdl: Double) {
        self.t = date.timeIntervalSince1970 * 1000
        self.v = mgdl
    }
}

/// Compact representation of a bolus dose for charting.
public struct DosePoint: Codable, Sendable {
    public let t: Double        // start (Unix ms)
    public let tEnd: Double     // end   (Unix ms)
    public let units: Double    // total U
    public let isBolus: Bool    // always true — boluses only; basal uses BasalSegment

    public init(dose: EvalInsulinDose) {
        self.t       = dose.startDate.timeIntervalSince1970 * 1000
        self.tEnd    = dose.endDate.timeIntervalSince1970 * 1000
        self.units   = dose.volume
        self.isBolus = (dose.deliveryType == .bolus)
    }
}

/// One segment of the continuous delivered basal rate timeline.
///
/// Built by filling gaps between temp basals with the scheduled rate, so
/// the timeline covers the evaluation window without holes.
public struct BasalSegment: Codable, Sendable {
    public let t: Double        // start (Unix ms)
    public let tEnd: Double     // end   (Unix ms)
    public let rate: Double     // U/hr
    /// `true` = gap filled from scheduled basal; `false` = actual temp basal (or suspend = 0)
    public let isScheduled: Bool
}

/// Compact representation of a carb entry for charting.
public struct CarbPoint: Codable, Sendable {
    public let t: Double    // Unix ms
    public let g: Double    // grams

    public init(entry: EvalCarbEntry) {
        self.t = entry.startDate.timeIntervalSince1970 * 1000
        self.g = entry.quantity.doubleValue(for: .gram)
    }
}

/// A sampled prediction curve (one snapshot per sampled step).
public struct PredictionSnapshot: Codable, Sendable {
    /// Time the prediction was made (Unix ms).
    public let t: Double
    /// Predicted trajectory — array of [timestamp_ms, mgdl] pairs.
    public let curve: [[Double]]

    public init(evaluatedAt: Date, predicted: [PredictedGlucoseValue]) {
        self.t = evaluatedAt.timeIntervalSince1970 * 1000
        self.curve = predicted.map { p in
            [p.startDate.timeIntervalSince1970 * 1000,
             p.quantity.doubleValue(for: .milligramsPerDeciliter)]
        }
    }
}

/// Per-horizon summary for the error profile panel.
public struct HorizonSummary: Codable, Sendable {
    public let horizonMin: Int
    public let rmse: Double
    public let mae: Double
    public let bias: Double
    public let p10: Double
    public let p90: Double
    public let lbgi: Double
    public let hbgi: Double

    public init(from m: HorizonMetrics) {
        self.horizonMin = Int(m.horizon / 60)
        self.rmse  = m.rmse
        self.mae   = m.mae
        self.bias  = m.meanError
        self.p10   = m.percentile10
        self.p90   = m.percentile90
        self.lbgi  = m.lbgi
        self.hbgi  = m.hbgi
    }
}

// MARK: – InspectionBundle

/// Full data bundle for the HTML report.
public struct InspectionBundle: Codable, Sendable {
    /// Evaluation interval (ISO strings for readability).
    public let startISO: String
    public let endISO: String
    public let evalConfig: InspectionConfig

    /// Raw CGM readings.
    public let rawGlucose: [GlucosePoint]
    /// Kalman-smoothed CGM (empty if Kalman is disabled).
    public let smoothedGlucose: [GlucosePoint]
    /// Bolus doses in the evaluation window.
    public let doses: [DosePoint]
    /// Continuous delivered basal rate timeline (gaps filled with scheduled basal).
    public let basalTimeline: [BasalSegment]
    /// All carb entries in the evaluation window.
    public let carbs: [CarbPoint]
    /// Sampled prediction snapshots (≈ every 30 min).
    public let predictions: [PredictionSnapshot]
    /// Per-horizon error profile.
    public let horizonProfile: [HorizonSummary]

    /// Lightweight config summary for display.
    public struct InspectionConfig: Codable, Sendable {
        public let insulinType: String
        public let useIntegralRC: Bool
        public let includeFutureInsulin: Bool
        public let kalmanSmoothing: Bool
        public let predictionCount: Int
        public let skippedCount: Int
    }
}

// MARK: – Builder

public enum InspectionBundleBuilder {

    /// Build an `InspectionBundle` from evaluation outputs.
    ///
    /// - Parameters:
    ///   - result:      Output of `EvaluationEngine.evaluate`.
    ///   - smoothed:    Kalman-smoothed CGM samples (nil = no smoothing).
    ///   - score:       Aggregate score from `EvaluationAnalyzer.analyze`.
    ///   - sampleStride: Store one prediction snapshot per this many steps (default 6 → every 30 min at 5-min steps).
    public static func build(
        result: EvaluationResult,
        smoothed: [EvalGlucoseSample]?,
        score: AggregateScore,
        sampleStride: Int = 6
    ) -> InspectionBundle {
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime]

        let rawPoints = result.actual.map { s in
            GlucosePoint(date: s.startDate,
                         mgdl: s.quantity.doubleValue(for: .milligramsPerDeciliter))
        }

        let smoothedPoints = (smoothed ?? []).map { s in
            GlucosePoint(date: s.startDate,
                         mgdl: s.quantity.doubleValue(for: .milligramsPerDeciliter))
        }

        // Doses and carbs in evaluation window (±1h padding so context is visible)
        let winStart = result.interval.start.addingTimeInterval(-3600)
        let winEnd   = result.interval.end.addingTimeInterval(3600)

        // We can't access PreloadedData here, but doses/carbs are embedded in PredictionRecords
        // indirectly — so we leave them empty; the caller fills them from PreloadedData.
        // (See InspectCommand for how the caller provides these arrays.)

        // Sample prediction snapshots
        let sampledPredictions: [PredictionSnapshot] = stride(
            from: 0, to: result.predictions.count, by: max(1, sampleStride)
        ).map { i in
            let rec = result.predictions[i]
            return PredictionSnapshot(evaluatedAt: rec.evaluatedAt, predicted: rec.predicted)
        }

        let horizonProfile = score.horizonMetrics.map { HorizonSummary(from: $0) }

        let cfg = InspectionBundle.InspectionConfig(
            insulinType: result.config.carbAbsorptionModel.rawValue,
            useIntegralRC: result.config.useIntegralRC,
            includeFutureInsulin: result.config.includeFutureInsulin,
            kalmanSmoothing: result.config.kalmanSmoothing,
            predictionCount: result.predictionCount,
            skippedCount: result.skippedCount
        )

        _ = winStart; _ = winEnd  // used by caller, not here

        return InspectionBundle(
            startISO: iso.string(from: result.interval.start),
            endISO:   iso.string(from: result.interval.end),
            evalConfig: cfg,
            rawGlucose: rawPoints,
            smoothedGlucose: smoothedPoints,
            doses: [],            // filled by caller
            basalTimeline: [],    // filled by caller
            carbs: [],            // filled by caller
            predictions: sampledPredictions,
            horizonProfile: horizonProfile
        )
    }

    /// Build with doses, carbs, and therapy timeline provided by the caller.
    public static func build(
        result: EvaluationResult,
        smoothed: [EvalGlucoseSample]?,
        score: AggregateScore,
        doses: [EvalInsulinDose],
        carbs: [EvalCarbEntry],
        therapyTimeline: TherapyTimeline,
        sampleStride: Int = 6
    ) -> InspectionBundle {
        let base = build(result: result, smoothed: smoothed, score: score, sampleStride: sampleStride)

        let winStart = result.interval.start
        let winEnd   = result.interval.end

        // Boluses only in the doses array; basal handled by basalTimeline
        let dosePoints = doses
            .filter { $0.deliveryType == .bolus }
            .filter { $0.startDate < winEnd && $0.endDate > winStart }
            .map { DosePoint(dose: $0) }

        let carbPoints = carbs
            .filter { $0.startDate >= winStart && $0.startDate <= winEnd }
            .map { CarbPoint(entry: $0) }

        let basalTimeline = buildBasalTimeline(
            doses: doses,
            scheduledBasal: therapyTimeline.basal,
            from: result.interval.start,
            to:   result.interval.end
        )

        return InspectionBundle(
            startISO: base.startISO,
            endISO:   base.endISO,
            evalConfig: base.evalConfig,
            rawGlucose: base.rawGlucose,
            smoothedGlucose: base.smoothedGlucose,
            doses: dosePoints,
            basalTimeline: basalTimeline,
            carbs: carbPoints,
            predictions: base.predictions,
            horizonProfile: base.horizonProfile
        )
    }

    // MARK: – Basal timeline builder

    /// Constructs a continuous delivered basal rate timeline by filling gaps
    /// between temp basals with the scheduled basal rate.
    ///
    /// - Temp basals: actual delivered rate (volume / duration)
    /// - Suspend Pump events: stored as 0-volume basal → rendered as 0 U/hr
    /// - Gaps (no temp basal): scheduled basal rate from `scheduledBasal`
    private static func buildBasalTimeline(
        doses: [EvalInsulinDose],
        scheduledBasal: [AbsoluteScheduleValue<Double>],
        from: Date,
        to: Date
    ) -> [BasalSegment] {

        // Only basal-type doses, clipped to window, sorted
        let tempBasals = doses
            .filter { $0.deliveryType == .basal && $0.startDate < to && $0.endDate > from }
            .sorted { $0.startDate < $1.startDate }

        var result: [BasalSegment] = []
        var cursor = from

        for dose in tempBasals {
            let segStart = max(dose.startDate, from)
            let segEnd   = min(dose.endDate,   to)
            guard segEnd > segStart else { continue }

            // Fill gap before this dose with scheduled basal
            if cursor < segStart {
                appendScheduled(from: cursor, to: segStart,
                                scheduled: scheduledBasal, into: &result)
                cursor = segStart
            }

            // This temp basal (or suspend = 0-volume)
            if cursor < segEnd {
                let duration = dose.endDate.timeIntervalSince(dose.startDate)
                let rate = duration > 0 ? dose.volume / (duration / 3600) : 0
                result.append(BasalSegment(
                    t: cursor.timeIntervalSince1970 * 1000,
                    tEnd: segEnd.timeIntervalSince1970 * 1000,
                    rate: rate,
                    isScheduled: false
                ))
                cursor = segEnd
            }
        }

        // Fill any remaining window with scheduled basal
        if cursor < to {
            appendScheduled(from: cursor, to: to,
                            scheduled: scheduledBasal, into: &result)
        }

        return result
    }

    private static func appendScheduled(
        from: Date,
        to: Date,
        scheduled: [AbsoluteScheduleValue<Double>],
        into result: inout [BasalSegment]
    ) {
        let segs = scheduled.filter { $0.endDate > from && $0.startDate < to }
        for seg in segs {
            let s = max(seg.startDate, from)
            let e = min(seg.endDate,   to)
            guard s < e else { continue }
            result.append(BasalSegment(
                t: s.timeIntervalSince1970 * 1000,
                tEnd: e.timeIntervalSince1970 * 1000,
                rate: seg.value,
                isScheduled: true
            ))
        }
    }
}
