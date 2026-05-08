// SimulationScores.swift — TIR-style counterfactual metrics
//
// Delivery-based ODR/UDR/IDB/RDB measure the INTENSITY of dosing differences
// at risky moments. They don't capture DURATION of in-zone time, because
// they're paired against the same actual BG for both baseline and candidate.
//
// SimulationScores fills that gap with a linearized counterfactual:
//
//   counter_BG(t) = actual_BG(t) − Σ_{t' ≤ t} Δdose(t') · ISF(t') · (1 − P_rem(t−t'))
//
// where Δdose = candidate − baseline and P_rem is the insulin model's
// percent-effect-remaining curve. This propagates the candidate's
// dose-delta impact onto the actual CGM trajectory, so we can compute
// TIR (% time 70-180), time below 70, time above 180, and AUCs on the
// counterfactual trajectory and compare to actual.
//
// Linearized vs full forward simulation: this approach assumes the
// candidate's earlier decisions don't change its later decisions (no
// feedback loop) and assumes constant ISF response to insulin. Errors
// are bounded by the magnitudes of Δdose. For short-horizon (< few days)
// dose-delta impacts on a real CGM trace, this is sufficient and
// avoids the divergence problem of unanchored simulations.

import Foundation
import LoopAlgorithm

public struct SimulationScores: Codable, Sendable {

    // Time-in-range metrics, both for actual BG (a.k.a. baseline)
    // and the candidate's counterfactual BG.
    /// Fraction of time in 70–180 mg/dL.
    public let tirActual: Double
    public let tirCandidate: Double

    /// Fraction of time below 70 mg/dL.
    public let timeBelow70Actual: Double
    public let timeBelow70Candidate: Double

    /// Fraction of time above 180 mg/dL.
    public let timeAbove180Actual: Double
    public let timeAbove180Candidate: Double

    /// Severe hypo (< 54 mg/dL) fraction.
    public let timeBelow54Actual: Double
    public let timeBelow54Candidate: Double

    /// Severe hyper (> 250 mg/dL) fraction.
    public let timeAbove250Actual: Double
    public let timeAbove250Candidate: Double

    /// AUC below 70 mg/dL — units: (mg/dL · minutes).
    public let aucBelow70Actual: Double
    public let aucBelow70Candidate: Double

    /// AUC above 180 mg/dL — units: (mg/dL · minutes).
    public let aucAbove180Actual: Double
    public let aucAbove180Candidate: Double

    /// Mean BG.
    public let meanBGActual: Double
    public let meanBGCandidate: Double

    /// Total minutes of CGM data used.
    public let coverageMinutes: Double

    /// Compute counterfactual TIR/AUC metrics given paired baseline+candidate
    /// predictions and the actual BG trajectory.
    public static func compute(
        baseline: EvaluationResult,
        candidate: EvaluationResult,
        actualGlucose: [EvalGlucoseSample],
        insulinModel: InsulinModel,
        sensitivity: [AbsoluteScheduleValue<LoopQuantity>]
    ) -> SimulationScores {

        // 1. Pair predictions by evaluatedAt and build (t, Δdose, ISF) events
        var basePred: [Date: PredictionRecord] = [:]
        for p in baseline.predictions { basePred[p.evaluatedAt] = p }

        struct DoseEvent {
            let t: Date
            let deltaDose: Double  // U  (candidate - baseline)
            let isfMgdlPerU: Double
        }
        var events: [DoseEvent] = []
        events.reserveCapacity(candidate.predictions.count)

        // Convention in this codebase: ISF schedule values are stored with
        // unit .milligramsPerDeciliter (numeric value IS the mg/dL/U scalar).
        // Read with the unit they're stored in; treat the double as mg/dL/U.
        let mgdlUnit = LoopUnit.milligramsPerDeciliter

        for pC in candidate.predictions {
            guard let pB = basePred[pC.evaluatedAt],
                  let dC = pC.recommendedDeltaU,
                  let dB = pB.recommendedDeltaU else { continue }
            let delta = dC - dB
            // Skip events with no delta — they contribute nothing.
            if delta == 0 { continue }
            // Find ISF active at the dose decision time
            let isfQty = sensitivity.first(where: { $0.startDate <= pC.evaluatedAt && $0.endDate > pC.evaluatedAt })?.value
                ?? sensitivity.closestPrior(to: pC.evaluatedAt)?.value
            let isf = isfQty?.doubleValue(for: mgdlUnit) ?? 0
            events.append(DoseEvent(t: pC.evaluatedAt, deltaDose: delta, isfMgdlPerU: isf))
        }
        // Events should already be in chronological order via candidate.predictions
        events.sort { $0.t < $1.t }

        // 2. For each actual CGM sample, compute counter_BG by walking back through events
        let actualSorted = actualGlucose.sorted { $0.startDate < $1.startDate }
        let activityDuration = insulinModel.effectDuration
        var actualValues: [Double] = []
        var counterValues: [Double] = []
        actualValues.reserveCapacity(actualSorted.count)
        counterValues.reserveCapacity(actualSorted.count)

        // Two-pointer: for each sample t, advance an "active window" in events
        // covering [t - activityDuration, t]. Events outside have zero contribution.
        var lo = 0  // first event with t' > t - activityDuration
        for sample in actualSorted {
            let t = sample.startDate
            let actual = sample.quantity.doubleValue(for: mgdlUnit)
            // Advance lo: drop events too old to contribute
            let earliest = t.addingTimeInterval(-activityDuration)
            while lo < events.count && events[lo].t < earliest { lo += 1 }
            // Sum impacts for events in [earliest, t]
            var impact = 0.0
            var i = lo
            while i < events.count && events[i].t <= t {
                let τ = t.timeIntervalSince(events[i].t)
                if τ >= 0 && τ <= activityDuration {
                    let percentRemaining = insulinModel.percentEffectRemaining(at: τ)
                    let percentDelivered = max(0.0, min(1.0, 1.0 - percentRemaining))
                    impact += events[i].deltaDose * events[i].isfMgdlPerU * percentDelivered
                }
                i += 1
            }
            // Counterfactual: if candidate gave more insulin, BG goes lower
            let counter = actual - impact
            actualValues.append(actual)
            counterValues.append(counter)
        }

        // 3. TIR / AUC metrics. Treat each sample as representing the time interval
        //    until the next sample (CGM is ~5 min cadence). Bound interval to 10 min
        //    to avoid overlong gaps inflating durations.
        var tirA = 0, tirC = 0
        var below70A = 0, below70C = 0
        var below54A = 0, below54C = 0
        var above180A = 0, above180C = 0
        var above250A = 0, above250C = 0
        var aucBelow70A = 0.0, aucBelow70C = 0.0
        var aucAbove180A = 0.0, aucAbove180C = 0.0
        var sumA = 0.0, sumC = 0.0
        var totalMinutes = 0.0

        for i in 0..<actualValues.count {
            let dtMin: Double
            if i + 1 < actualSorted.count {
                let gap = actualSorted[i+1].startDate.timeIntervalSince(actualSorted[i].startDate) / 60
                dtMin = min(10.0, max(0.5, gap))
            } else {
                dtMin = 5.0
            }
            totalMinutes += dtMin

            let a = actualValues[i]
            let c = counterValues[i]
            sumA += a * dtMin
            sumC += c * dtMin

            // Bin counters
            if a >= 70 && a <= 180 { tirA += 1 }
            if c >= 70 && c <= 180 { tirC += 1 }
            if a < 70 { below70A += 1; aucBelow70A += (70 - a) * dtMin }
            if c < 70 { below70C += 1; aucBelow70C += (70 - c) * dtMin }
            if a < 54 { below54A += 1 }
            if c < 54 { below54C += 1 }
            if a > 180 { above180A += 1; aucAbove180A += (a - 180) * dtMin }
            if c > 180 { above180C += 1; aucAbove180C += (c - 180) * dtMin }
            if a > 250 { above250A += 1 }
            if c > 250 { above250C += 1 }
        }

        let n = max(1, actualValues.count)
        let dN = Double(n)
        return SimulationScores(
            tirActual: Double(tirA) / dN,
            tirCandidate: Double(tirC) / dN,
            timeBelow70Actual: Double(below70A) / dN,
            timeBelow70Candidate: Double(below70C) / dN,
            timeAbove180Actual: Double(above180A) / dN,
            timeAbove180Candidate: Double(above180C) / dN,
            timeBelow54Actual: Double(below54A) / dN,
            timeBelow54Candidate: Double(below54C) / dN,
            timeAbove250Actual: Double(above250A) / dN,
            timeAbove250Candidate: Double(above250C) / dN,
            aucBelow70Actual: aucBelow70A,
            aucBelow70Candidate: aucBelow70C,
            aucAbove180Actual: aucAbove180A,
            aucAbove180Candidate: aucAbove180C,
            meanBGActual: sumA / max(1.0, totalMinutes),
            meanBGCandidate: sumC / max(1.0, totalMinutes),
            coverageMinutes: totalMinutes
        )
    }
}
