// PumpModel.swift — the simulator's model of what the insulin pump can actually
// deliver. The controller computes a continuous dose request; the hardware can
// only deliver basal rates and bolus volumes on a supported grid. Routing every
// dose through this type makes the counter physics see exactly what would be
// delivered, instead of the controller's idealized request.
//
// Omnipod (user1 and user2 both run Omnipod) supports basal rates and bolus
// volumes on a 0.05 U(/hr) grid, and maps a request onto the grid by taking the
// LARGEST supported value <= the request (a FLOOR), via
// `roundToSupportedBasalRate` / `roundToSupportedBolusVolume`.
//
// Empirically confirmed on user1 Temporary Overrides (factor 0.81): the
// override-scaled neutral basal is delivered as the floor of the scaled rate —
//   scheduled 0.6 ×0.81 = 0.486 → delivered 0.45   (round-to-nearest would be 0.50)
//   scheduled 0.8 ×0.81 = 0.648 → delivered 0.60   (round-to-nearest would be 0.65)
//   scheduled 1.1 ×0.81 = 0.891 → delivered 0.85   (round-to-nearest would be 0.90)
// across three times of day — i.e. Loop/Omnipod FLOOR the rate, never round up.

import Foundation

public struct PumpModel: Sendable, Codable, Equatable {
    /// How a continuous request is mapped onto the supported delivery grid.
    public enum Rounding: String, Sendable, Codable {
        case down       // largest supported value <= request (Omnipod)
        case nearest    // nearest supported value
    }

    /// Supported basal-rate grid (U/hr). 0 = no quantization (continuous).
    public var basalRateIncrement: Double
    /// Supported bolus-volume grid (U). 0 = no quantization.
    public var bolusIncrement: Double
    /// Per-step delivered-amount pulse quantum (U): the pump delivers basal in
    /// discrete pulses and the per-cycle temp re-issue drops the in-progress
    /// sub-pulse remainder, so a step's delivered amount is floored to whole
    /// pulses. 0 = off. (Always floored — you cannot deliver a partial pulse.)
    public var pulseQuantum: Double
    /// How `basalRateIncrement` / `bolusIncrement` requests snap to the grid.
    public var rounding: Rounding

    public init(basalRateIncrement: Double, bolusIncrement: Double, pulseQuantum: Double, rounding: Rounding) {
        self.basalRateIncrement = basalRateIncrement
        self.bolusIncrement = bolusIncrement
        self.pulseQuantum = pulseQuantum
        self.rounding = rounding
    }

    /// Omnipod (DASH/Eros): 0.05 U(/hr) grid, floor.
    public static let omnipod = PumpModel(basalRateIncrement: 0.05, bolusIncrement: 0.05, pulseQuantum: 0.05, rounding: .down)
    /// Ideal continuous pump — no quantization (legacy micro-dosing behavior).
    public static let ideal = PumpModel(basalRateIncrement: 0, bolusIncrement: 0, pulseQuantum: 0, rounding: .down)

    // Snap `x` onto the `inc` grid. A small tolerance is added before flooring
    // because IEEE-754 makes exact grid multiples land just below the integer
    // (1.2 / 0.05 = 23.999999999999996), which would otherwise floor a clean
    // 1.2 U/hr down to 1.15. The tolerance (5e-8 U at inc=0.05) only rescues
    // values within FP noise of a grid point — genuine sub-increment requests
    // still floor down.
    private static let snapTol = 1e-6
    private func snap(_ x: Double, _ inc: Double) -> Double {
        guard inc > 0 else { return x }
        let q = x / inc
        switch rounding {
        case .down:    return (q + Self.snapTol).rounded(.down) * inc
        case .nearest: return q.rounded() * inc
        }
    }

    /// Supported basal rate for a continuous request (Omnipod: floor to grid).
    public func supportedBasalRate(_ rate: Double) -> Double { snap(rate, basalRateIncrement) }
    /// Supported bolus volume for a continuous request (Omnipod: floor to grid).
    public func supportedBolusVolume(_ volume: Double) -> Double { snap(volume, bolusIncrement) }
    /// Floor a per-step delivered amount to whole pulses (always floor).
    /// STATELESS — drops any sub-pulse remainder every call. Correct only when
    /// the temp basal is re-issued every step; for a continuing temp use
    /// `BasalAccumulator`, which carries the remainder. Kept for boluses / one-shot
    /// amounts.
    public func quantizeDelivery(_ amount: Double) -> Double {
        guard pulseQuantum > 0, amount > 0 else { return amount }
        return ((amount / pulseQuantum) + Self.snapTol).rounded(.down) * pulseQuantum
    }

    /// Stateful basal-pulse delivery for the closed-loop counter.
    ///
    /// A real pump delivers basal as discrete `pulseQuantum` pulses and CARRIES the
    /// sub-pulse remainder across time — EXCEPT when a temp basal is cancelled and
    /// re-issued at a NEW rate (Loop's per-cycle re-issue), which abandons the
    /// in-progress partial pulse and restarts accrual. So the remainder carries
    /// while the temp rate is unchanged and is dropped on a rate change. This
    /// reproduces the field ~1.1 U/day below rate×time. A stateless per-step floor
    /// over-penalizes (~2.8 U/day): it drops the partial pulse EVERY step, but
    /// only ~27% of steps are real rate changes; the rest continue the same temp
    /// and should keep accruing. (user1 ISF-72 window: nominal 29.7, per-step-floor
    /// 27.0, cancellation-aware 28.5 U/day; field ≈ −1.1/day.)
    public final class BasalAccumulator {
        public let quantum: Double
        private var remainder: Double = 0
        private var lastRate: Double? = nil
        public init(quantum: Double) { self.quantum = quantum }

        /// Whole-pulse basal units actually delivered over a step at `rate` (U/hr)
        /// for `seconds`. `quantum <= 0` ⇒ continuous (rate×time, no quantization).
        /// A change in `rate` from the previous call drops the in-progress pulse
        /// (temp re-issue/cancellation) before accruing this step.
        public func deliver(rate: Double, seconds: Double) -> Double {
            let nominal = rate * seconds / 3600.0
            guard quantum > 0 else { lastRate = rate; return nominal }
            if let lr = lastRate, abs(rate - lr) > 1e-9 { remainder = 0 }  // cancellation: drop partial pulse
            lastRate = rate
            remainder += nominal
            let pulses = ((remainder / quantum) + 1e-6).rounded(.down) * quantum
            remainder = Swift.max(0, remainder - pulses)
            return pulses
        }
    }

    /// A fresh basal-pulse accumulator for this pump's `pulseQuantum`.
    public func makeBasalAccumulator() -> BasalAccumulator { BasalAccumulator(quantum: pulseQuantum) }
}
