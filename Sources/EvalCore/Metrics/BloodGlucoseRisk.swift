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

    // MARK: – Risk-weighted RMSE

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
}
