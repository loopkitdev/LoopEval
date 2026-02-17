// KalmanSmoother.swift — 2D Kalman filter + RTS backward smoother for CGM
//
// State vector: x = [BG (mg/dL), velocity (mg/dL/s)]
// Only the BG component is observed.
// The velocity component is a latent rate-of-change, NOT mg/dL/min.
// (velocity noise in the same units: mg/dL/s^2)
//
// Design choice: applied ONLY to actual CGM used for comparison,
// NOT to algorithm input — keeps algorithm input representative of real-world use.

import Foundation

public struct KalmanSmoother {

    // MARK: – Tunable parameters

    /// Process noise for the BG state (mg/dL²). Default: 1.0.
    public var processNoiseQ: Double

    /// Process noise for the velocity state (mg/dL²/s²). Default: 1e-4.
    /// (corresponds to ~0.01 mg/dL/s velocity uncertainty per second step)
    public var velocityNoiseQ: Double

    /// Observation noise (mg/dL²). Default: 4.0 (≈ 2 mg/dL std dev).
    public var observationNoiseR: Double

    public init(
        processNoiseQ: Double   = 1.0,
        velocityNoiseQ: Double  = 1e-4,
        observationNoiseR: Double = 4.0
    ) {
        self.processNoiseQ      = processNoiseQ
        self.velocityNoiseQ     = velocityNoiseQ
        self.observationNoiseR  = observationNoiseR
    }

    // MARK: – 2×2 matrix helpers (inline, no external library)

    // A 2×2 matrix stored row-major: [[a,b],[c,d]]
    // Represented as a 4-tuple (a, b, c, d).

    typealias Mat2 = (Double, Double, Double, Double)  // (00, 01, 10, 11)
    typealias Vec2 = (Double, Double)                  // (x0, x1)

    @inline(__always)
    private func matMul(_ A: Mat2, _ B: Mat2) -> Mat2 {
        (
            A.0 * B.0 + A.1 * B.2,  A.0 * B.1 + A.1 * B.3,
            A.2 * B.0 + A.3 * B.2,  A.2 * B.1 + A.3 * B.3
        )
    }

    @inline(__always)
    private func matAdd(_ A: Mat2, _ B: Mat2) -> Mat2 {
        (A.0 + B.0, A.1 + B.1, A.2 + B.2, A.3 + B.3)
    }

    @inline(__always)
    private func matSub(_ A: Mat2, _ B: Mat2) -> Mat2 {
        (A.0 - B.0, A.1 - B.1, A.2 - B.2, A.3 - B.3)
    }

    @inline(__always)
    private func matScale(_ A: Mat2, _ s: Double) -> Mat2 {
        (A.0 * s, A.1 * s, A.2 * s, A.3 * s)
    }

    @inline(__always)
    private func matTranspose(_ A: Mat2) -> Mat2 {
        (A.0, A.2, A.1, A.3)
    }

    // 2×1 vector multiply: A * v
    @inline(__always)
    private func matVecMul(_ A: Mat2, _ v: Vec2) -> Vec2 {
        (A.0 * v.0 + A.1 * v.1,
         A.2 * v.0 + A.3 * v.1)
    }

    @inline(__always)
    private func vecAdd(_ a: Vec2, _ b: Vec2) -> Vec2 {
        (a.0 + b.0, a.1 + b.1)
    }

    @inline(__always)
    private func vecScale(_ v: Vec2, _ s: Double) -> Vec2 {
        (v.0 * s, v.1 * s)
    }

    @inline(__always)
    private func vecSub(_ a: Vec2, _ b: Vec2) -> Vec2 {
        (a.0 - b.0, a.1 - b.1)
    }

    // Identity matrix
    private let I: Mat2 = (1, 0, 0, 1)

    // MARK: – Smoother

    /// Smooth a sequence of CGM samples using 2D Kalman filter + RTS backward smoother.
    ///
    /// Handles irregular time steps. Input is sorted by `startDate` before processing.
    /// Returns smoothed `EvalGlucoseSample` with same timestamps but smoothed BG values.
    public func smooth(samples: [EvalGlucoseSample]) -> [EvalGlucoseSample] {
        guard samples.count >= 2 else { return samples }

        let sorted = samples.sorted { $0.startDate < $1.startDate }
        let n = sorted.count

        // Storage for forward pass results
        var xs:     [Vec2] = Array(repeating: (0, 0), count: n)  // filtered states
        var Ps:     [Mat2] = Array(repeating: (0,0,0,0), count: n)  // filtered covariances
        var xpreds: [Vec2] = Array(repeating: (0, 0), count: n)  // predicted states
        var Ppreds: [Mat2] = Array(repeating: (0,0,0,0), count: n)  // predicted covariances
        var Fs:     [Mat2] = Array(repeating: (0,0,0,0), count: n)  // transition matrices

        // Observation model: H = [1, 0] (observe BG component only)
        // H * x = x.0,  H^T = (1, 0)^T
        let R = observationNoiseR

        // MARK: Forward pass

        // Initialise
        let firstBG = sorted[0].quantity.doubleValue(for: .milligramsPerDeciliter)
        xs[0]     = (firstBG, 0.0)         // [BG, velocity=0]
        Ps[0]     = (100.0, 0.0, 0.0, 1.0) // high initial uncertainty
        xpreds[0] = xs[0]
        Ppreds[0] = Ps[0]
        Fs[0]     = I

        for k in 1..<n {
            let dt = sorted[k].startDate.timeIntervalSince(sorted[k-1].startDate)
            let dt_safe = max(dt, 1.0) // guard against zero/negative dt

            // Transition matrix: F = [[1, dt], [0, 1]]
            let F: Mat2 = (1, dt_safe, 0, 1)
            Fs[k] = F
            let FT = matTranspose(F)

            // Process noise: Q = diag(q_bg, q_vel)
            let Q: Mat2 = (processNoiseQ, 0, 0, velocityNoiseQ)

            // Predict
            let xp = matVecMul(F, xs[k-1])
            let Pp = matAdd(matMul(matMul(F, Ps[k-1]), FT), Q)
            xpreds[k] = xp
            Ppreds[k] = Pp

            // Innovation: z is the observed BG
            let z = sorted[k].quantity.doubleValue(for: .milligramsPerDeciliter)
            let y = z - xp.0  // innovation = z - H * xp

            // Innovation covariance: S = H * Pp * H' + R  (scalar since H = [1,0])
            let S = Pp.0 + R // H * Pp * H^T = Pp[0,0]

            // Kalman gain: K = Pp * H' / S  (2×1 vector)
            // K = (Pp[0,0] / S, Pp[1,0] / S)
            let K: Vec2 = (Pp.0 / S, Pp.2 / S)

            // Update
            let xNew = vecAdd(xp, vecScale(K, y))
            // P = (I - K * H) * Pp  where K*H = [[K0, 0], [K1, 0]]
            let KH: Mat2 = (K.0, 0.0, K.1, 0.0)
            let IminusKH = matSub(I, KH)
            let PNew = matMul(IminusKH, Pp)

            xs[k] = xNew
            Ps[k] = PNew
        }

        // MARK: RTS Backward smoother

        var xSmooth = xs
        var PSmooth = Ps

        for k in stride(from: n - 2, through: 0, by: -1) {
            let F  = Fs[k + 1]
            let FT = matTranspose(F)

            // G = P[k] * F[k+1]^T * inv(P_pred[k+1])
            // inv of 2×2: [[a,b],[c,d]]^-1 = 1/(ad-bc) * [[d,-b],[-c,a]]
            let Pp = Ppreds[k + 1]
            let det = Pp.0 * Pp.3 - Pp.1 * Pp.2
            guard abs(det) > 1e-15 else { continue }  // singular — skip smoothing step
            let invPp: Mat2 = (Pp.3/det, -Pp.1/det, -Pp.2/det, Pp.0/det)

            let G = matMul(matMul(Ps[k], FT), invPp)
            let GT = matTranspose(G)

            let dx = vecSub(xSmooth[k + 1], xpreds[k + 1])
            xSmooth[k] = vecAdd(xs[k], matVecMul(G, dx))

            let dP = matSub(PSmooth[k + 1], Ppreds[k + 1])
            PSmooth[k] = matAdd(Ps[k], matMul(matMul(G, dP), GT))
        }

        // Build output samples
        return sorted.enumerated().map { idx, sample in
            let smoothedBG = xSmooth[idx].0
            return EvalGlucoseSample(
                startDate: sample.startDate,
                quantity: .init(unit: .milligramsPerDeciliter, doubleValue: smoothedBG),
                provenanceIdentifier: sample.provenanceIdentifier,
                isDisplayOnly: sample.isDisplayOnly,
                wasUserEntered: sample.wasUserEntered,
                condition: sample.condition,
                trendRate: sample.trendRate
            )
        }
    }
}
