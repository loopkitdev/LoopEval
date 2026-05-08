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

/// Distribution shape of |Δdose| within one (sign × pre-BG) bucket.
///
/// The RMS scores capture magnitude but blur the difference between "many
/// small persistent ticks" and "a few large spikes." These quantiles let
/// you tell those apart at a glance: high P99 with low P50 ⇒ rare-but-severe;
/// flat profile ⇒ small-but-persistent.
public struct MagnitudeQuantiles: Codable, Sendable {
    public let count: Int
    public let p50: Double
    public let p90: Double
    public let p99: Double
}

/// Per-horizon delivery-based risk scores.
///
/// Four signed metrics partition the (Δdose × pre-low/pre-high) space.
/// Acronyms: suffix `R` = Risk (cost), suffix `B` = Benefit.
///
/// ```
///                     pre-low (BG<70)     pre-high (BG>180)
///   over-delivers:    ODR  (cost)         IDB  (benefit)
///   under-delivers:   RDB  (benefit)      UDR  (cost)
/// ```
///
/// `Δdose = candidate_deltaU − baseline_deltaU`. Costs measure when the
/// candidate dosed in a dangerous direction; benefits measure when it dosed
/// in a beneficial direction. The cells come in three flavors:
///
///   • RMS magnitude (`odr`, `udr`, `idb`, `rdb`) — risk-weighted RMS, blind
///     to event duration; punishes a single big spike harder than many small
///     persistent ticks of equal total impact.
///   • Risk-weighted rate (`*Rate`) — `Σ risk · |Δ| / T_total`, in
///     risk-weighted U/hr. Linear in event duration, so duration-aware: a
///     1-hour hold-back counts ~12× a 5-min one of equal magnitude.
///   • Raw U/hr (`*URate`) — same as rate but un-weighted by risk;
///     interpretable as "average insulin units/hr the candidate
///     over-/under-delivered into pre-low / pre-high windows."
public struct DeliveryHorizonScores: Codable, Sendable {
    /// Forecast horizon this was computed at (e.g., 90 min).
    public let horizon: TimeInterval
    /// Number of paired (baseline, candidate) decisions at which actual BG
    /// at horizon was in-range-low (gates ODR & RDB) or in-range-high (gates UDR & IDB).
    public let nODR: Int
    public let nUDR: Int
    /// Over-Delivery Risk (cost): dangerous EXTRA delivery into pre-low moments.
    ///   ODR = √( Σ rl(actual) · max(Δdose, 0)² / nODR )
    public let odr: Double
    /// Under-Delivery Risk (cost): LESS delivery into pre-high moments.
    ///   UDR = √( Σ rh(actual) · max(−Δdose, 0)² / nUDR )
    public let udr: Double
    /// Increased Delivery Benefit: EXTRA delivery into pre-high moments — the
    /// candidate dosed more aggressively at moments that turned out to need it.
    ///   IDB = √( Σ rh(actual) · max(Δdose, 0)² / nUDR )
    public let idb: Double
    /// Reduced Delivery Benefit: LESS delivery at pre-low moments — the
    /// candidate held back at moments that turned out to be hypos.
    ///   RDB = √( Σ rl(actual) · max(−Δdose, 0)² / nODR )
    public let rdb: Double

    /// Time-integrated risk-weighted rates: `Σ risk · |Δ| / T_total` (units: risk-U/hr).
    /// Duration-aware counterpart to the RMS scores above.
    public let odrRate: Double
    public let udrRate: Double
    public let idbRate: Double
    public let rdbRate: Double

    /// Raw U/hr — un-weighted by risk. Clinically interpretable as
    /// "average insulin units per hour of analysis time the candidate
    /// over-/under-delivered, restricted to pre-low / pre-high windows."
    public let odrURate: Double
    public let udrURate: Double
    public let idbURate: Double
    public let rdbURate: Double

    /// Distribution of `|Δdose|` (in U) over the events that contributed
    /// to each cell. Tells you whether magnitude is concentrated in a few
    /// big spikes (high P99) or spread evenly across many ticks.
    public let odrQuantiles: MagnitudeQuantiles
    public let udrQuantiles: MagnitudeQuantiles
    public let idbQuantiles: MagnitudeQuantiles
    public let rdbQuantiles: MagnitudeQuantiles

    /// Total analysis duration (seconds) used as the rate denominator.
    public let analysisDuration: TimeInterval
}

/// Aggregate delivery-based scores across horizons (Gaussian-weighted like OPR/UPR).
public struct DeliveryScores: Codable, Sendable {
    public let horizonScores: [DeliveryHorizonScores]
    public let weightedODR: Double
    public let weightedUDR: Double
    public let weightedIDB: Double
    public let weightedRDB: Double
    public let primaryDeliveryScore: Double   // ODR + UDR (costs only)

    /// Gaussian-weighted aggregate of the per-horizon risk-weighted rates.
    public let weightedODRRate: Double
    public let weightedUDRRate: Double
    public let weightedIDBRate: Double
    public let weightedRDBRate: Double

    /// Gaussian-weighted aggregate of the per-horizon raw U/hr rates.
    public let weightedODRURate: Double
    public let weightedUDRURate: Double
    public let weightedIDBURate: Double
    public let weightedRDBURate: Double

    /// Compute delivery-based ODR/UDR scores.
    ///
    /// ODR and UDR are gated on the CLINICAL DANGER thresholds (defaults
    /// 70 / 180 mg/dL), not the target range. A mildly-below-target BG of
    /// 95 mg/dL isn't "dangerous" — these metrics are about meaningful hypo
    /// (< 70) and hyper (> 180) events. For the legacy target-range gating
    /// used by OPR/UPR, pass `targetLow`/`targetHigh` from the eval config.
    public static func compute(
        baseline: EvaluationResult,
        candidate: EvaluationResult,
        horizons: [TimeInterval],
        actualGlucose: [EvalGlucoseSample],
        evalStep: TimeInterval = 300,
        dangerLow: Double = 70.0,
        dangerHigh: Double = 180.0,
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

        // Total analysis duration used as denominator for rate metrics.
        // pairs.count · evalStep handles gaps cleanly (only counts steps we actually evaluated).
        let analysisDuration = Double(pairs.count) * evalStep
        let analysisHours = max(analysisDuration / 3600.0, 1e-9)

        // Per-horizon scores
        var perHorizon: [DeliveryHorizonScores] = []
        for h in horizons {
            // RMS accumulators (existing behaviour)
            var sumODR = 0.0, sumUDR = 0.0, sumIDB = 0.0, sumRDB = 0.0
            // Linear (risk-weighted) accumulators for *Rate fields
            var linODR = 0.0, linUDR = 0.0, linIDB = 0.0, linRDB = 0.0
            // Raw (un-weighted) U accumulators for *URate fields
            var rawODR = 0.0, rawUDR = 0.0, rawIDB = 0.0, rawRDB = 0.0
            // Magnitude samples per cell, for quantiles
            var magsODR: [Double] = [], magsUDR: [Double] = []
            var magsIDB: [Double] = [], magsRDB: [Double] = []
            var nODR = 0, nUDR = 0
            for pair in pairs {
                let tFuture = pair.t.addingTimeInterval(h)
                guard let actualBG = Self.interpolate(sortedActual, at: tFuture) else { continue }
                if actualBG < dangerLow {
                    let over = max(pair.deltaU, 0)
                    let under = max(-pair.deltaU, 0)
                    let rl = BloodGlucoseRisk.rl(actualBG)
                    if over > 0 {
                        sumODR += rl * over * over
                        linODR += rl * over
                        rawODR += over
                        magsODR.append(over)
                    }
                    if under > 0 {
                        sumRDB += rl * under * under
                        linRDB += rl * under
                        rawRDB += under
                        magsRDB.append(under)
                    }
                    nODR += 1
                } else if actualBG > dangerHigh {
                    let over = max(pair.deltaU, 0)
                    let under = max(-pair.deltaU, 0)
                    let rh = BloodGlucoseRisk.rh(actualBG)
                    if under > 0 {
                        sumUDR += rh * under * under
                        linUDR += rh * under
                        rawUDR += under
                        magsUDR.append(under)
                    }
                    if over > 0 {
                        sumIDB += rh * over * over
                        linIDB += rh * over
                        rawIDB += over
                        magsIDB.append(over)
                    }
                    nUDR += 1
                }
            }
            let odr = nODR > 0 ? sqrt(sumODR / Double(nODR)) : 0
            let rdb = nODR > 0 ? sqrt(sumRDB / Double(nODR)) : 0
            let udr = nUDR > 0 ? sqrt(sumUDR / Double(nUDR)) : 0
            let idb = nUDR > 0 ? sqrt(sumIDB / Double(nUDR)) : 0
            perHorizon.append(DeliveryHorizonScores(
                horizon: h, nODR: nODR, nUDR: nUDR,
                odr: odr, udr: udr, idb: idb, rdb: rdb,
                odrRate: linODR / analysisHours,
                udrRate: linUDR / analysisHours,
                idbRate: linIDB / analysisHours,
                rdbRate: linRDB / analysisHours,
                odrURate: rawODR / analysisHours,
                udrURate: rawUDR / analysisHours,
                idbURate: rawIDB / analysisHours,
                rdbURate: rawRDB / analysisHours,
                odrQuantiles: Self.quantiles(magsODR),
                udrQuantiles: Self.quantiles(magsUDR),
                idbQuantiles: Self.quantiles(magsIDB),
                rdbQuantiles: Self.quantiles(magsRDB),
                analysisDuration: analysisDuration
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
                weightedODR: 0, weightedUDR: 0, weightedIDB: 0, weightedRDB: 0,
                primaryDeliveryScore: 0,
                weightedODRRate: 0, weightedUDRRate: 0, weightedIDBRate: 0, weightedRDBRate: 0,
                weightedODRURate: 0, weightedUDRURate: 0, weightedIDBURate: 0, weightedRDBURate: 0
            )
        }
        let weights = rawWeights.map { $0 / totalW }
        var wODR = 0.0, wUDR = 0.0, wIDB = 0.0, wRDB = 0.0
        var wODRRate = 0.0, wUDRRate = 0.0, wIDBRate = 0.0, wRDBRate = 0.0
        var wODRURate = 0.0, wUDRURate = 0.0, wIDBURate = 0.0, wRDBURate = 0.0
        for (s, w) in zip(perHorizon, weights) {
            wODR += w * s.odr
            wUDR += w * s.udr
            wIDB += w * s.idb
            wRDB += w * s.rdb
            wODRRate += w * s.odrRate
            wUDRRate += w * s.udrRate
            wIDBRate += w * s.idbRate
            wRDBRate += w * s.rdbRate
            wODRURate += w * s.odrURate
            wUDRURate += w * s.udrURate
            wIDBURate += w * s.idbURate
            wRDBURate += w * s.rdbURate
        }

        return DeliveryScores(
            horizonScores: perHorizon,
            weightedODR: wODR,
            weightedUDR: wUDR,
            weightedIDB: wIDB,
            weightedRDB: wRDB,
            primaryDeliveryScore: wODR + wUDR,
            weightedODRRate: wODRRate,
            weightedUDRRate: wUDRRate,
            weightedIDBRate: wIDBRate,
            weightedRDBRate: wRDBRate,
            weightedODRURate: wODRURate,
            weightedUDRURate: wUDRURate,
            weightedIDBURate: wIDBURate,
            weightedRDBURate: wRDBURate
        )
    }

    // MARK: - Quantile helper

    /// Empirical quantiles of `vals` at P50/P90/P99. Linear-time-ish:
    /// sorts then indexes — fine for the volumes we see (one sweep ≈ 2k events).
    static func quantiles(_ vals: [Double]) -> MagnitudeQuantiles {
        guard !vals.isEmpty else {
            return MagnitudeQuantiles(count: 0, p50: 0, p90: 0, p99: 0)
        }
        let sorted = vals.sorted()
        func q(_ p: Double) -> Double {
            let n = sorted.count
            let idx = min(n - 1, max(0, Int((p * Double(n - 1)).rounded())))
            return sorted[idx]
        }
        return MagnitudeQuantiles(count: sorted.count, p50: q(0.5), p90: q(0.9), p99: q(0.99))
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
