// InsulinInformedKalmanSmoother.swift — Kalman filter + RTS smoother with insulin control input
//
// State vector: x = [BG (mg/dL), velocity (mg/dL/s)]
// where velocity is the non-insulin velocity component.
//
// At each time step, the expected insulin glucose effect is computed from doses
// and ISF and used as a known control input u to the process model:
//   BG(t+dt) = BG(t-1) + (velocity + u/dt) * dt
//
// i.e., the transition adds the insulin effect on top of the velocity term.
// The RTS backward smoother logic is identical to KalmanSmoother.

import Foundation
import LoopAlgorithm

public struct InsulinInformedKalmanSmoother {

    // MARK: – Tunable parameters

    /// Process noise for the BG state (mg/dL²). Default: 1.0.
    public var processNoiseQ: Double

    /// Process noise for the velocity state (mg/dL²/s²). Default: 1e-4.
    public var velocityNoiseQ: Double

    /// Observation noise (mg/dL²). Default: 16.0 (4 mg/dL std dev).
    /// Higher than baseline smoother — trusts insulin-informed model more.
    public var observationNoiseR: Double

    public init(
        processNoiseQ: Double   = 1.0,
        velocityNoiseQ: Double  = 1e-4,
        observationNoiseR: Double = 16.0
    ) {
        self.processNoiseQ      = processNoiseQ
        self.velocityNoiseQ     = velocityNoiseQ
        self.observationNoiseR  = observationNoiseR
    }

    // MARK: – 2×2 matrix helpers (inline, no external library)

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
    private func matTranspose(_ A: Mat2) -> Mat2 {
        (A.0, A.2, A.1, A.3)
    }

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

    private let I: Mat2 = (1, 0, 0, 1)

    // MARK: – Smoother

    /// Smooth CGM using insulin effect as a control input.
    ///
    /// - Parameters:
    ///   - samples: Raw CGM samples (will be sorted internally)
    ///   - doses: Insulin doses covering the window (bolus + basal)
    ///   - isfSchedule: ISF schedule as [(startDate, value in mg/dL per unit)]
    /// - Returns: Smoothed GlucosePoint array (same timestamps as input)
    public func smooth(
        samples: [EvalGlucoseSample],
        doses: [EvalInsulinDose],
        isfSchedule: [AbsoluteScheduleValue<LoopQuantity>]
    ) -> [EvalGlucoseSample] {
        guard samples.count >= 2 else { return samples }

        let sorted = samples.sorted { $0.startDate < $1.startDate }
        let n = sorted.count

        // Precompute insulin effect (mg/dL) delivered in each CGM step
        // insulinEffects[k] = expected BG drop (positive = lowering) from t[k-1] to t[k]
        var insulinEffects = Array(repeating: 0.0, count: n)
        let insulinModel = ExponentialInsulinModelPreset.rapidActingAdult.model

        for k in 1..<n {
            let tStart = sorted[k - 1].startDate
            let tEnd   = sorted[k].startDate
            let isf    = isfAt(time: tEnd, schedule: isfSchedule)

            // Sum effect from all doses
            var totalEffect = 0.0
            for dose in doses {
                let effect = insulinEffectIncrement(
                    dose: dose,
                    from: tStart,
                    to: tEnd,
                    isf: isf,
                    model: insulinModel
                )
                totalEffect += effect
            }
            insulinEffects[k] = totalEffect
        }

        // Storage for forward pass results
        var xs:     [Vec2] = Array(repeating: (0, 0), count: n)
        var Ps:     [Mat2] = Array(repeating: (0,0,0,0), count: n)
        var xpreds: [Vec2] = Array(repeating: (0, 0), count: n)
        var Ppreds: [Mat2] = Array(repeating: (0,0,0,0), count: n)
        var Fs:     [Mat2] = Array(repeating: (0,0,0,0), count: n)

        let R = observationNoiseR

        // MARK: Forward pass

        let firstBG = sorted[0].quantity.doubleValue(for: .milligramsPerDeciliter)
        xs[0]     = (firstBG, 0.0)
        Ps[0]     = (100.0, 0.0, 0.0, 1.0)
        xpreds[0] = xs[0]
        Ppreds[0] = Ps[0]
        Fs[0]     = I

        for k in 1..<n {
            let dt = sorted[k].startDate.timeIntervalSince(sorted[k-1].startDate)
            let dt_safe = max(dt, 1.0)

            // Transition matrix: F = [[1, dt], [0, 1]]
            let F: Mat2 = (1, dt_safe, 0, 1)
            Fs[k] = F
            let FT = matTranspose(F)

            // Process noise: Q = diag(q_bg, q_vel)
            let Q: Mat2 = (processNoiseQ, 0, 0, velocityNoiseQ)

            // Predict with control input:
            // xp = F * x + B * u
            // where B = [1, 0]^T and u = -insulinEffect (negative because insulin lowers BG)
            let xp_no_control = matVecMul(F, xs[k-1])
            let u = -insulinEffects[k]  // mg/dL BG change due to insulin
            let xp: Vec2 = (xp_no_control.0 + u, xp_no_control.1)

            let Pp = matAdd(matMul(matMul(F, Ps[k-1]), FT), Q)
            xpreds[k] = xp
            Ppreds[k] = Pp

            // Innovation
            let z = sorted[k].quantity.doubleValue(for: .milligramsPerDeciliter)
            let y = z - xp.0

            // Innovation covariance
            let S = Pp.0 + R

            // Kalman gain
            let K: Vec2 = (Pp.0 / S, Pp.2 / S)

            // Update
            let xNew = vecAdd(xp, vecScale(K, y))
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

            let Pp = Ppreds[k + 1]
            let det = Pp.0 * Pp.3 - Pp.1 * Pp.2
            guard abs(det) > 1e-15 else { continue }
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

    // MARK: – Helpers

    /// Get ISF at a given time from the schedule (uses most recent entry).
    private func isfAt(time: Date, schedule: [AbsoluteScheduleValue<LoopQuantity>]) -> Double {
        // Find the entry that covers this time, or the most recent one before it
        let applicable = schedule.filter { $0.startDate <= time }
        guard let entry = applicable.max(by: { $0.startDate < $1.startDate }) else {
            // Fallback: use first entry if time is before schedule start
            return schedule.first?.value.doubleValue(for: .milligramsPerDeciliter) ?? 50.0
        }
        return entry.value.doubleValue(for: .milligramsPerDeciliter)
    }

    /// Compute the expected BG effect (mg/dL) delivered by a dose in the interval [from, to].
    ///
    /// insulinEffect = dose.volume * isf * (IOB_fraction_at_from - IOB_fraction_at_to)
    ///
    /// This represents the glucose that was "used up" during this time step.
    private func insulinEffectIncrement(
        dose: EvalInsulinDose,
        from: Date,
        to: Date,
        isf: Double,
        model: InsulinModel
    ) -> Double {
        // Time since dose delivery started
        let tFrom = from.timeIntervalSince(dose.startDate)
        let tTo   = to.timeIntervalSince(dose.startDate)

        // If the interval is entirely before the dose, no effect yet
        if tTo <= 0 { return 0.0 }

        // If the interval is entirely after the dose duration, no more effect
        if tFrom >= model.effectDuration { return 0.0 }

        // Clamp times to valid range [0, effectDuration]
        let clampedFrom = max(0, tFrom)
        let clampedTo   = min(model.effectDuration, tTo)

        // IOB fractions
        let iobAtFrom = model.percentEffectRemaining(at: clampedFrom)
        let iobAtTo   = model.percentEffectRemaining(at: clampedTo)

        // Effect delivered in this step = volume * isf * (change in IOB fraction)
        let effectFractionDelivered = iobAtFrom - iobAtTo
        return dose.volume * isf * effectFractionDelivered
    }
}
