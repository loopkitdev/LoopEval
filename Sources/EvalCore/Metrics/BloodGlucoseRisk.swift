// BloodGlucoseRisk.swift — Clarke-Kovatchev risk functions
//
// Reference: Clarke & Kovatchev (2009), "Statistical Tools to Analyze
// Continuous Glucose Monitor Data"

import Foundation

public struct BloodGlucoseRisk {

    // MARK: – Core risk transformation

    /// Transforms glucose (mg/dL) into risk space.
    /// Clarke & Kovatchev, 2009.
    public static func riskFunction(_ glucose: Double) -> Double {
        guard glucose > 0 else { return 0 }
        let f = 1.509 * (log(glucose) * 1.084 - 5.381)
        return 10.0 * f * f
    }

    // MARK: – Directional risk

    /// Low BG risk (hypoglycemia risk).
    /// Non-zero only when BG < 112.5 mg/dL (the crossover point where f(BG) = 0).
    public static func rl(_ glucose: Double) -> Double {
        glucose < 112.5 ? riskFunction(glucose) : 0
    }

    /// High BG risk (hyperglycemia risk).
    /// Non-zero only when BG > 112.5 mg/dL.
    public static func rh(_ glucose: Double) -> Double {
        glucose > 112.5 ? riskFunction(glucose) : 0
    }

    // MARK: – Aggregate indices

    /// Low Blood Glucose Index — mean low BG risk over a sequence.
    public static func lbgi(_ values: [Double]) -> Double {
        guard !values.isEmpty else { return 0 }
        return values.map { rl($0) }.reduce(0, +) / Double(values.count)
    }

    /// High Blood Glucose Index — mean high BG risk over a sequence.
    public static func hbgi(_ values: [Double]) -> Double {
        guard !values.isEmpty else { return 0 }
        return values.map { rh($0) }.reduce(0, +) / Double(values.count)
    }

    /// Blood Glucose Risk Index = LBGI + HBGI.
    public static func bgri(_ values: [Double]) -> Double {
        lbgi(values) + hbgi(values)
    }

    // MARK: – Risk-weighted RMSE (legacy — symmetric, no target range)

    /// RMSE where each squared error is weighted by `rl(actual)`.
    /// Answers: "are prediction errors worse when the patient is hypoglycemic?"
    public static func lowWeightedRMSE(errors: [(predicted: Double, actual: Double)]) -> Double {
        let n = Double(errors.count)
        guard n > 0 else { return 0 }
        let sumWeightedSqErr = errors.reduce(0.0) { acc, pair in
            let diff = pair.predicted - pair.actual
            return acc + rl(pair.actual) * diff * diff
        }
        return sqrt(sumWeightedSqErr / n)
    }

    /// RMSE where each squared error is weighted by `rh(actual)`.
    /// Answers: "are prediction errors worse when the patient is hyperglycemic?"
    public static func highWeightedRMSE(errors: [(predicted: Double, actual: Double)]) -> Double {
        let n = Double(errors.count)
        guard n > 0 else { return 0 }
        let sumWeightedSqErr = errors.reduce(0.0) { acc, pair in
            let diff = pair.predicted - pair.actual
            return acc + rh(pair.actual) * diff * diff
        }
        return sqrt(sumWeightedSqErr / n)
    }

    // MARK: – Directional danger scores (primary optimization target)

    /// **Dangerous Over-prediction Score (DOS)**
    ///
    /// Penalises forecasts that predict BG will be *higher* than it actually is,
    /// when the actual BG is *below* the target range.  This is the error that
    /// causes Loop to keep delivering insulin into a falling or already-low BG.
    ///
    /// - Cost is **zero** when `actual >= targetLow` (in-range or high: no danger).
    /// - Cost is **zero** for under-predictions (`predicted <= actual`): only
    ///   over-predictions in the low zone are dangerous here.
    /// - Weighted by `rl(actual)` so the cost grows rapidly as BG falls below
    ///   the target floor.
    ///
    /// Formula: `sqrt( Σ rl(actual) · max(predicted − actual, 0)² / n )`
    public static func overdeliveryRisk(
        errors: [(predicted: Double, actual: Double)],
        targetLow: Double
    ) -> Double {
        let n = Double(errors.count)
        guard n > 0 else { return 0 }
        let sum = errors.reduce(0.0) { acc, pair in
            guard pair.actual < targetLow else { return acc }          // in range or high → no cost
            let over = max(pair.predicted - pair.actual, 0.0)          // only over-predictions
            return acc + rl(pair.actual) * over * over
        }
        return sqrt(sum / n)
    }

    /// **Dangerous Under-prediction Score (DUS)**
    ///
    /// Penalises forecasts that predict BG will be *lower* than it actually is,
    /// when the actual BG is *above* the target range.  This is the error that
    /// causes Loop to withhold a correction it should have delivered.
    ///
    /// - Cost is **zero** when `actual <= targetHigh` (in-range or low: no danger).
    /// - Cost is **zero** for over-predictions (`predicted >= actual`): only
    ///   under-predictions in the high zone are dangerous here.
    /// - Weighted by `rh(actual)` so the cost grows rapidly as BG rises above
    ///   the target ceiling.
    ///
    /// Formula: `sqrt( Σ rh(actual) · max(actual − predicted, 0)² / n )`
    public static func underdeliveryRisk(
        errors: [(predicted: Double, actual: Double)],
        targetHigh: Double
    ) -> Double {
        let n = Double(errors.count)
        guard n > 0 else { return 0 }
        let sum = errors.reduce(0.0) { acc, pair in
            guard pair.actual > targetHigh else { return acc }         // in range or low → no cost
            let under = max(pair.actual - pair.predicted, 0.0)         // only under-predictions
            return acc + rh(pair.actual) * under * under
        }
        return sqrt(sum / n)
    }
}
