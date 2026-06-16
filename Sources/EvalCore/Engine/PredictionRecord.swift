// PredictionRecord.swift — a single prediction made at a point in time

import Foundation
import LoopAlgorithm

/// A single prediction made at a point in time.
public struct PredictionRecord: Sendable {
    /// The time at which this prediction was generated.
    public let evaluatedAt: Date

    /// The predicted glucose trajectory (from LoopAlgorithm.generatePrediction).
    /// Sorted ascending by startDate, starting at or very near `evaluatedAt`.
    public let predicted: [PredictedGlucoseValue]

    /// Prediction without future insulin (doses after `evaluatedAt` excluded).
    /// `nil` when `includeFutureInsulin` was false (would be identical to `predicted`).
    public let predictedNoFutureInsulin: [PredictedGlucoseValue]?

    /// Insulin on board (units) at the time of prediction.
    public let iob: Double?
    /// Carbs on board (grams) at the time of prediction.
    public let cob: Double?

    /// Recommended dose at this decision point. Total insulin delivery Loop
    /// would produce in the immediate next evalStep window, measured as the
    /// delta vs continuing the scheduled basal rate.
    ///
    /// = `bolusUnits + (temp_basal_rate_U_hr − scheduled_basal_rate_U_hr) × evalStep/3600`
    ///
    /// Positive values mean "Loop would deliver more than scheduled basal"
    /// (a correction bolus or high-temp-basal); negative means "less than
    /// scheduled" (low-temp or suspend). `nil` when dose recommendation
    /// couldn't be computed.
    public let recommendedDeltaU: Double?

    /// Bolus volume recommended at this step (U), if any. `nil` if not computed.
    public let recommendedBolus: Double?

    /// Full correction bolus (application factor 1.0, clamped to maxBolus) — the
    /// upstream "recommendedBolus" Loop computes every cycle before applying the
    /// auto-bolus application factor. Directly comparable to devicestatus
    /// `loop.recommendedBolus`. `nil` if not computed.
    public let recommendedManualBolus: Double?

    /// Temp basal rate recommended at this step (U/hr), if any. `nil` if
    /// recommendation was to continue scheduled basal.
    public let recommendedTempBasalRate: Double?

    /// Scheduled (baseline) basal rate at this moment (U/hr).
    public let scheduledBasalRate: Double?

    /// Per-effect-component contributions to the forecast, measured as the
    /// change from `evaluatedAt` to the horizon. Used by drift analysis to
    /// isolate which forecast component drives divergence between Loop-now
    /// and pump-side Loop. All values in mg/dL. `nil` when not computed or
    /// when the effect array is empty at that horizon.
    ///
    /// For RC and momentum we report the cumulative effect value at the
    /// horizon directly (since both are defined as effects projected from
    /// `evaluatedAt` forward).
    public let insulinEffectΔ60: Double?   // insulin_effect(t+60) − insulin_effect(t)
    public let insulinEffectΔ90: Double?
    public let rcEffect60: Double?
    public let rcEffect90: Double?
    public let momentumEffect30: Double?

    public init(evaluatedAt: Date, predicted: [PredictedGlucoseValue],
                predictedNoFutureInsulin: [PredictedGlucoseValue]? = nil,
                iob: Double? = nil, cob: Double? = nil,
                recommendedDeltaU: Double? = nil,
                recommendedBolus: Double? = nil,
                recommendedManualBolus: Double? = nil,
                recommendedTempBasalRate: Double? = nil,
                scheduledBasalRate: Double? = nil,
                insulinEffectΔ60: Double? = nil,
                insulinEffectΔ90: Double? = nil,
                rcEffect60: Double? = nil,
                rcEffect90: Double? = nil,
                momentumEffect30: Double? = nil) {
        self.evaluatedAt               = evaluatedAt
        self.predicted                 = predicted
        self.predictedNoFutureInsulin  = predictedNoFutureInsulin
        self.iob                       = iob
        self.cob                       = cob
        self.recommendedDeltaU         = recommendedDeltaU
        self.recommendedBolus          = recommendedBolus
        self.recommendedManualBolus    = recommendedManualBolus
        self.recommendedTempBasalRate  = recommendedTempBasalRate
        self.scheduledBasalRate        = scheduledBasalRate
        self.insulinEffectΔ60          = insulinEffectΔ60
        self.insulinEffectΔ90          = insulinEffectΔ90
        self.rcEffect60                = rcEffect60
        self.rcEffect90                = rcEffect90
        self.momentumEffect30          = momentumEffect30
    }

    // MARK: – Horizon lookup

    /// Returns the interpolated predicted glucose value (mg/dL) at a specific
    /// forecast horizon relative to `evaluatedAt`.
    ///
    /// Uses linear interpolation between adjacent predicted points.
    /// Returns `nil` if the prediction curve doesn't reach the requested horizon.
    public func predictedValue(atHorizon horizon: TimeInterval) -> Double? {
        guard !predicted.isEmpty else { return nil }

        let targetDate = evaluatedAt.addingTimeInterval(horizon)

        // Fast path: exact match on first or last
        if let first = predicted.first, targetDate <= first.startDate {
            guard targetDate == first.startDate else { return nil }  // before curve → out of range
            return first.quantity.doubleValue(for: .milligramsPerDeciliter)
        }
        if let last = predicted.last, targetDate >= last.startDate {
            guard targetDate == last.startDate else {
                // Clamp to last value only if within one 5-min step (rounding tolerance)
                let gap = targetDate.timeIntervalSince(last.startDate)
                if gap <= 5 * 60 + 1 {
                    return last.quantity.doubleValue(for: .milligramsPerDeciliter)
                }
                return nil
            }
            return last.quantity.doubleValue(for: .milligramsPerDeciliter)
        }

        // Find the two adjacent points that bracket targetDate
        for i in 0..<(predicted.count - 1) {
            let p0 = predicted[i]
            let p1 = predicted[i + 1]
            guard p0.startDate <= targetDate && targetDate <= p1.startDate else { continue }

            let interval = p1.startDate.timeIntervalSince(p0.startDate)
            guard interval > 0 else {
                return p0.quantity.doubleValue(for: .milligramsPerDeciliter)
            }

            let t = targetDate.timeIntervalSince(p0.startDate) / interval
            let v0 = p0.quantity.doubleValue(for: .milligramsPerDeciliter)
            let v1 = p1.quantity.doubleValue(for: .milligramsPerDeciliter)
            return v0 + t * (v1 - v0)
        }

        return nil
    }
}
