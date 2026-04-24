// LombScargle.swift — Lomb-Scargle periodogram for irregularly-sampled data
//
// Detects sinusoidal signals in time series where samples don't need to be
// uniformly spaced. For each angular frequency ω, computes a power P(ω)
// proportional to how much variance is explained by sine/cosine at ω.
//
// Reference: Scargle 1982, "Studies in astronomical time series analysis. II.
// Statistical aspects of spectral analysis of unevenly spaced data."
//
// For this project: input is the rolling-ISF time series (one ISF per day),
// output is power vs period so we can inspect for cyclic signals at e.g.
// ~7 days (weekly) or ~28 days (menstrual).

import Foundation

public struct LombScarglePoint: Sendable, Codable {
    /// Period in days (= 1 / frequency).
    public var periodDays: Double
    /// Frequency in cycles/day (= 1 / periodDays).
    public var frequency: Double
    /// Normalised power. Higher = stronger signal at this frequency.
    public var power: Double
    /// False-alarm probability (0–1). Small = significant signal.
    public var fap: Double
}

public struct LombScargleResult: Sendable {
    public var points: [LombScarglePoint]
    /// Peaks sorted by power descending (after a simple local-max filter).
    public var peaks: [LombScarglePoint]
    /// Number of samples actually used in the fit.
    public var nSamples: Int
    /// Effective number of independent frequencies (for FAP computation).
    public var nEffectiveFrequencies: Int
}

public enum LombScargle {

    /// Compute the periodogram over a range of periods.
    ///
    /// - Parameters:
    ///   - times: sample times (any epoch; converted to days since first sample).
    ///   - values: sample values. NaN entries are dropped.
    ///   - minPeriodDays: smallest period to scan (default 3d — avoid extreme
    ///     high-frequency noise).
    ///   - maxPeriodDays: largest period to scan (default = half the sample span).
    ///   - oversample: frequency-grid density multiplier (default 5 × Nyquist).
    public static func compute(
        times: [Date],
        values: [Double],
        minPeriodDays: Double = 3,
        maxPeriodDays: Double? = nil,
        oversample: Double = 5
    ) -> LombScargleResult {
        precondition(times.count == values.count, "times/values length mismatch")

        // 1. Filter to (t, y) pairs with finite y. Convert t to days-since-first.
        var pairs: [(t: Double, y: Double)] = []
        pairs.reserveCapacity(times.count)
        var t0: Date?
        for i in 0..<times.count {
            if values[i].isNaN || values[i].isInfinite { continue }
            if t0 == nil { t0 = times[i] }
            let tDays = times[i].timeIntervalSince(t0!) / 86400
            pairs.append((t: tDays, y: values[i]))
        }
        guard pairs.count >= 8 else {
            return LombScargleResult(points: [], peaks: [], nSamples: pairs.count, nEffectiveFrequencies: 0)
        }

        // 2. Centre and scale.
        let yMean = pairs.reduce(0) { $0 + $1.y } / Double(pairs.count)
        var yVar = 0.0
        for p in pairs { yVar += (p.y - yMean) * (p.y - yMean) }
        yVar /= Double(pairs.count - 1)
        guard yVar > 0 else {
            return LombScargleResult(points: [], peaks: [], nSamples: pairs.count, nEffectiveFrequencies: 0)
        }
        let yCentered = pairs.map { $0.y - yMean }

        // 3. Frequency grid.
        let span = pairs.last!.t - pairs.first!.t
        let pMax = maxPeriodDays ?? (span / 2)
        let fMin = 1.0 / pMax
        let fMax = 1.0 / minPeriodDays
        // Number of frequencies: ~ span × fMax × oversample (standard choice)
        let nFreq = max(64, Int(ceil(span * fMax * oversample)))
        let df = (fMax - fMin) / Double(nFreq - 1)

        var out: [LombScarglePoint] = []
        out.reserveCapacity(nFreq)

        // Effective independent frequencies for FAP (Horne & Baliunas 1986):
        let np = Double(pairs.count)
        let mReal = -6.362 + 1.193 * np + 0.00098 * np * np
        let nIndep = max(1, Int(mReal))

        for k in 0..<nFreq {
            let f = fMin + Double(k) * df
            let omega = 2 * Double.pi * f

            // Compute τ such that Σ sin(2ω(t-τ)) cos(2ω(t-τ)) = 0
            var s2 = 0.0, c2 = 0.0
            for p in pairs {
                s2 += sin(2 * omega * p.t)
                c2 += cos(2 * omega * p.t)
            }
            let tau = atan2(s2, c2) / (2 * omega)

            var cc = 0.0, ss = 0.0, cy = 0.0, sy = 0.0
            for i in 0..<pairs.count {
                let arg = omega * (pairs[i].t - tau)
                let c = cos(arg); let s = sin(arg)
                cc += c * c
                ss += s * s
                cy += yCentered[i] * c
                sy += yCentered[i] * s
            }

            let power = 0.5 * ((cy * cy) / max(cc, 1e-12) + (sy * sy) / max(ss, 1e-12))
            // Normalise by variance to get dimensionless power in [0, N/2]
            let pNorm = power / yVar

            // False-alarm probability (asymptotic, Scargle 1982 + Horne-Baliunas):
            // P(peak ≤ P*) ≈ (1 - exp(-P*))^M, so FAP ≈ 1 - (1 - exp(-P*))^M
            let fap = 1 - pow(1 - exp(-pNorm), Double(nIndep))

            out.append(LombScarglePoint(
                periodDays: 1.0 / f,
                frequency: f,
                power: pNorm,
                fap: fap
            ))
        }

        // 4. Peak detection: simple local max (higher than both neighbours).
        //    Skip peaks at the ends. Sort by power descending, return top 10.
        var peaks: [LombScarglePoint] = []
        for i in 1..<(out.count - 1) {
            if out[i].power > out[i-1].power && out[i].power > out[i+1].power {
                peaks.append(out[i])
            }
        }
        peaks.sort { $0.power > $1.power }
        let topPeaks = Array(peaks.prefix(10))

        return LombScargleResult(
            points: out, peaks: topPeaks,
            nSamples: pairs.count, nEffectiveFrequencies: nIndep
        )
    }
}
