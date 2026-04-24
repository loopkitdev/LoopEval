// DeliveryScores.swift — delivery-based ODR/UDR
//
// Forecast-based OPR/UPR measure the ERROR of Loop's prediction against
// actual BG. Delivery-based ODR/UDR measure the DIFFERENCE in insulin
// delivery between two configurations, weighted by clinical risk at the
// actual future BG.
//
// Intuition: if a candidate algorithm delivers MORE insulin than baseline
// at moments where actual future BG ended up low → that's dangerous
// over-delivery (ODR). If it delivers LESS at moments where future BG
// ended up high → that's under-delivery that let the high persist (UDR).
//
// Unlike OPR/UPR which depend on forecast accuracy alone, these metrics
// capture what actually reached the patient — the clinical consequence.

import Foundation
import LoopAlgorithm

/// Per-horizon delivery-based risk scores.
public struct DeliveryHorizonScores: Codable, Sendable {
    /// Forecast horizon this was computed at (e.g., 90 min).
    public let horizon: TimeInterval
    /// Number of paired (baseline, candidate) decisions at which actual BG
    /// at horizon was in-range-low (for ODR) or in-range-high (for UDR).
    public let nODR: Int
    public let nUDR: Int
    /// Over-Delivery Risk: dangerous EXTRA delivery into pre-low moments.
    ///   ODR = √( Σ rl(actual) · max(Δdose, 0)² / nODR )
    /// where Δdose = candidate_deltaU − baseline_deltaU, sampled at decisions
    /// whose actual BG at `horizon` ended below `targetLow`.
    public let odr: Double
    /// Under-Delivery Risk: dangerous LESS delivery into pre-high moments.
    ///   UDR = √( Σ rh(actual) · max(−Δdose, 0)² / nUDR )
    /// sampled at decisions whose actual BG at `horizon` ended above `targetHigh`.
    public let udr: Double
}

/// Aggregate delivery-based scores across horizons (Gaussian-weighted like OPR/UPR).
public struct DeliveryScores: Codable, Sendable {
    public let horizonScores: [DeliveryHorizonScores]
    public let weightedODR: Double
    public let weightedUDR: Double
    public let primaryDeliveryScore: Double   // ODR + UDR

    public static func compute(
        baseline: EvaluationResult,
        candidate: EvaluationResult,
        horizons: [TimeInterval],
        actualGlucose: [EvalGlucoseSample],
        targetLow: Double = 100.0,
        targetHigh: Double = 115.0,
        peakHorizon: TimeInterval = 90 * 60,
        sigmaSecs: TimeInterval = 60 * 60
    ) -> DeliveryScores {
        // Pair predictions by evaluatedAt
        var baseByTime: [Date: PredictionRecord] = [:]
        for p in baseline.predictions { baseByTime[p.evaluatedAt] = p }

        var pairs: [(t: Date, deltaU: Double)] = []
        for pC in candidate.predictions {
            guard let pB = baseByTime[pC.evaluatedAt],
                  let dC = pC.recommendedDeltaU,
                  let dB = pB.recommendedDeltaU else { continue }
            pairs.append((pC.evaluatedAt, dC - dB))
        }

        // Sort actual glucose once for binary-search interpolation
        let sortedActual = actualGlucose.sorted { $0.startDate < $1.startDate }

        // Per-horizon scores
        var perHorizon: [DeliveryHorizonScores] = []
        for h in horizons {
            var sumODR = 0.0, sumUDR = 0.0
            var nODR = 0, nUDR = 0
            for pair in pairs {
                let tFuture = pair.t.addingTimeInterval(h)
                guard let actualBG = Self.interpolate(sortedActual, at: tFuture) else { continue }
                if actualBG < targetLow {
                    let over = max(pair.deltaU, 0)
                    if over > 0 {
                        sumODR += BloodGlucoseRisk.rl(actualBG) * over * over
                    }
                    nODR += 1
                } else if actualBG > targetHigh {
                    let under = max(-pair.deltaU, 0)
                    if under > 0 {
                        sumUDR += BloodGlucoseRisk.rh(actualBG) * under * under
                    }
                    nUDR += 1
                }
            }
            let odr = nODR > 0 ? sqrt(sumODR / Double(nODR)) : 0
            let udr = nUDR > 0 ? sqrt(sumUDR / Double(nUDR)) : 0
            perHorizon.append(DeliveryHorizonScores(
                horizon: h, nODR: nODR, nUDR: nUDR, odr: odr, udr: udr
            ))
        }

        // Gaussian-weighted aggregate
        let rawWeights = perHorizon.map { s -> Double in
            let diff = s.horizon - peakHorizon
            return exp(-(diff * diff) / (2.0 * sigmaSecs * sigmaSecs))
        }
        let totalW = rawWeights.reduce(0, +)
        guard totalW > 0 else {
            return DeliveryScores(
                horizonScores: perHorizon,
                weightedODR: 0, weightedUDR: 0, primaryDeliveryScore: 0
            )
        }
        let weights = rawWeights.map { $0 / totalW }
        var wODR = 0.0, wUDR = 0.0
        for (s, w) in zip(perHorizon, weights) {
            wODR += w * s.odr
            wUDR += w * s.udr
        }

        return DeliveryScores(
            horizonScores: perHorizon,
            weightedODR: wODR,
            weightedUDR: wUDR,
            primaryDeliveryScore: wODR + wUDR
        )
    }

    // MARK: - Helpers

    /// Linear interpolation of the nearest-bracketing actual glucose samples
    /// to get BG at an arbitrary time. Returns nil if outside the series
    /// or if the bracketing samples are more than 10 minutes apart.
    static func interpolate(_ samples: [EvalGlucoseSample], at t: Date) -> Double? {
        guard !samples.isEmpty else { return nil }
        if t < samples.first!.startDate || t > samples.last!.startDate { return nil }

        // Binary search for the first sample with startDate >= t
        var lo = 0, hi = samples.count - 1
        while lo < hi {
            let mid = (lo + hi) / 2
            if samples[mid].startDate < t { lo = mid + 1 } else { hi = mid }
        }

        if samples[lo].startDate == t {
            return samples[lo].quantity.doubleValue(for: .milligramsPerDeciliter)
        }
        // Interpolate between samples[lo-1] and samples[lo]
        guard lo > 0 else { return nil }
        let a = samples[lo - 1]
        let b = samples[lo]
        let gap = b.startDate.timeIntervalSince(a.startDate)
        guard gap > 0 && gap <= 10 * 60 else { return nil }   // gap too large to trust
        let frac = t.timeIntervalSince(a.startDate) / gap
        let va = a.quantity.doubleValue(for: .milligramsPerDeciliter)
        let vb = b.quantity.doubleValue(for: .milligramsPerDeciliter)
        return va + frac * (vb - va)
    }
}
