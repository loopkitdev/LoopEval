// LowResponse.swift — re-generate the low-driven upward response in a counterfactual.
//
// Field ICE carries everything that pushed glucose back up BECAUSE it went low: rescue carbs (mostly
// unlogged) and the body's own rebound. A replay that inherits them hands a candidate that PREVENTS the low a
// rebound it never earned. The research workflow subtracts the field's low responses from the substrate (a
// cleaned data dir) and, with this model, adds them back only where the COUNTERFACTUAL itself goes low.
//
// Each counterfactual step: with the counterfactual CGM under `gateBg` and no response started within
// `refractoryMin`, a response starts with probability h = logistic(beta · z),
//   z = [1, (85 - CGM)/10, -trend (mg/dL/min over 15 min), IOB / scheduled basal (U / U/h), night (local 00-06)].
// Its size (g-equivalent) is drawn from `doses`; its glucose effect is grams × CSF(at start) × kernel, where
// `kernel` is the per-minute rate per (g × CSF) on a 5-min grid starting at the response start. Draws come from
// a seeded generator, so a run is reproducible. When this model is on, the engine's counter-regulation term
// should be off: the response already includes the physiological rebound.

import Foundation

public struct LowResponseModel: Codable, Sendable {
    public var beta: [Double]            // [one, below85, falling, iobn, night]
    public var gateBg: Double            // no response at/above this counterfactual CGM
    public var refractoryMin: Double
    public var kernel: [Double]          // per-minute rate per (g × CSF), 5-min resolution
    public var doses: [Double]           // empirical response sizes (g-equivalent) to draw from
    public var seed: UInt64
    /// Gated subtraction: the field's own detected low responses. Each is kept with weight
    /// w = min(1, h(counterfactual state) / hField), decided at its start from the counterfactual,
    /// and the rest, (1 - w) of its effect, is removed. At identity w = 1, so the field is unchanged.
    public var fieldEvents: [FieldEvent]? = nil
    /// false = no stochastic add-back (gated subtraction only). nil = on.
    public var addBack: Bool? = nil
    /// true = the depth term is beta[1] * max(0, (85 - CGM)/10): no penalty above 85, so anticipation decides there.
    public var depthRelu: Bool? = nil
    /// Depth stops growing below this CGM: depth = min(depth, (85 - depthFloor)/10). Treatment rates level off in deep lows.
    public var depthFloor: Double? = nil
    /// How soon: + a * (p0 - P)/10 with projected glucose P = CGM + horizonMin * trend - ISF * IOB + CSF * COB
    /// (the candidate's own IOB and announced COB, scheduled ISF / CR: what the person's app shows).
    public var anticipation: Anticipation? = nil
    /// Glucose effect per gram-equivalent (mg/dL), replacing the app's CSF (ISF / CR): the person's real response
    /// strength. With it, `kernel` should integrate to 1.
    public var mgdlPerGram: Double? = nil
    /// - highSuppress × max(0, (CGM - 100)/10): nobody treats a low at 180.
    public var highSuppress: Double? = nil
    /// Overcorrection: grams × (1 + overcorrect × max(0, 80 - CGM)/20), clipped to 3...80 g.
    public var overcorrect: Double? = nil
    /// Expected-value difference form: no draws and no field events. Every step adds h(counterfactual) × meanSize
    /// and removes h(field) × meanSize, each convolved with `kernel` (hazards capped at one start per refractory
    /// period). Needs no detection of the field's own responses, and is exactly zero at identity.
    public var expected: Bool? = nil
    public var meanSize: Double? = nil
    /// HIGH-side mirror (research): the same machinery for defenses that pull glucose DOWN from highs (walks, glucosuria
    /// beyond GE, unlogged corrections). Features mirror: depth = max(0, (CGM - pivot)/10), trend enters as +trend,
    /// anticipation as a·(P - p0)/10, highSuppress suppresses BELOW 140, and the effect is subtracted. pivot default 180.
    public var mirror: Bool? = nil
    public var pivot: Double? = nil
    /// Effect per unit of size = scheduled ISF (insulin-like defenses: unlogged or regenerated corrections) instead of CSF.
    public var useISF: Bool? = nil

    public struct Anticipation: Codable, Sendable {
        public var a: Double
        public var p0: Double
        public var horizonMin: Double
    }

    public struct FieldEvent: Codable, Sendable {
        public var t: Double                // Unix seconds of the response start
        public var gcsf: Double             // grams × CSF at the start (mg/dL)
        public var hField: Double           // the model hazard at the field's state (fallback when no field sample)
    }
}

final class LowResponseState {
    let model: LowResponseModel
    private var rng: UInt64
    private var active: [(start: Date, grams: Double, csf: Double)] = []
    private(set) var started: [(t: Date, grams: Double)] = []
    private var cum: [Double]                                     // cumulative effect per (g × CSF) at k × 5 min
    private var fieldNext = 0
    private(set) var gated: [(t: Date, w: Double)] = []

    init(_ model: LowResponseModel) {
        self.model = model
        self.rng = model.seed &+ 0x9E3779B97F4A7C15
        var c = [0.0]
        for r in model.kernel { c.append(c.last! + r * 5.0) }
        self.cum = c
    }

    private func uniform() -> Double {                             // SplitMix64
        rng = rng &+ 0x9E3779B97F4A7C15
        var z = rng
        z = (z ^ (z >> 30)) &* 0xBF58476D1CE4E5B9
        z = (z ^ (z >> 27)) &* 0x94D049BB133111EB
        z = z ^ (z >> 31)
        return Double(z >> 11) / Double(1 << 53)
    }

    private func hazard(bg: Double, trend: Double, iobn: Double, night: Bool, projected: Double = .nan) -> Double {
        if model.mirror ?? false {
            let depth = max(0, (bg - (model.pivot ?? 180)) / 10)
            var z = model.beta[0] + model.beta[1] * depth + model.beta[2] * (trend.isFinite ? trend : 0)
                + model.beta[3] * (iobn.isFinite ? iobn : 0) + model.beta[4] * (night ? 1 : 0)
            if let a = model.anticipation, projected.isFinite { z += a.a * (projected - a.p0) / 10 }
            if let hu = model.highSuppress { z -= hu * max(0, (140 - bg) / 10) }
            return 1 / (1 + exp(-max(-30, min(30, z))))
        }
        var depth = (model.depthRelu ?? false) ? max(0, (85 - bg) / 10) : (85 - bg) / 10
        if let f = model.depthFloor { depth = min(depth, (85 - f) / 10) }
        var z = model.beta[0] + model.beta[1] * depth + model.beta[2] * (trend.isFinite ? -trend : 0)
            + model.beta[3] * (iobn.isFinite ? iobn : 0) + model.beta[4] * (night ? 1 : 0)
        if let a = model.anticipation, projected.isFinite { z += a.a * (a.p0 - projected) / 10 }
        if let hu = model.highSuppress { z -= hu * max(0, (bg - 100) / 10) }
        return 1 / (1 + exp(-max(-30, min(30, z))))
    }

    /// Projected glucose for the anticipation term (nan when the model has none or an input is missing).
    func projected(bg: Double, trend: Double, iob: Double, cob: Double, isf: Double, cr: Double) -> Double {
        guard let a = model.anticipation, bg.isFinite, isf > 0, cr > 0 else { return .nan }
        return bg + a.horizonMin * (trend.isFinite ? trend : 0) - isf * (iob.isFinite ? iob : 0)
            + isf / cr * (cob.isFinite ? cob : 0)
    }

    /// Decide at step `t` from the counterfactual's own state.
    func step(t: Date, bg: Double, trend: Double, iobn: Double, night: Bool, csf: Double,
              fieldBg: Double = .nan, fieldTrend: Double = .nan, projected P: Double = .nan,
              fieldIobn: Double = .nan, fieldProjected PF: Double = .nan, isf: Double = .nan) {
        if model.expected ?? false {
            guard let m = model.meanSize else { return }
            let unit = (model.useISF ?? false) ? isf : (model.mgdlPerGram ?? csf)
            guard unit.isFinite, unit > 0 else { return }
            let cap = 5.0 / max(5.0, model.refractoryMin)
            func size(_ bg: Double) -> Double {
                guard let oc = model.overcorrect, !(model.mirror ?? false) else { return m }
                return min(80, max(3, m * (1 + oc * max(0, 80 - bg) / 20)))
            }
            let k = unit * ((model.mirror ?? false) ? -1 : 1)
            if bg.isFinite && bg < model.gateBg {
                let h = min(cap, hazard(bg: bg, trend: trend, iobn: iobn, night: night, projected: P))
                active.append((t, h * size(bg), k)); started.append((t, h * size(bg)))
            }
            if fieldBg.isFinite && fieldBg < model.gateBg {
                let h = min(cap, hazard(bg: fieldBg, trend: fieldTrend, iobn: fieldIobn.isFinite ? fieldIobn : iobn,
                                        night: night, projected: PF))
                active.append((t, -h * size(fieldBg), k)); gated.append((t, h * size(fieldBg)))
            }
            return
        }
        let u = uniform(), u2 = uniform()                          // always consume two draws: stable streams
        if let ev = model.fieldEvents {
            while fieldNext < ev.count && ev[fieldNext].t <= t.timeIntervalSince1970 {
                let e = ev[fieldNext]; fieldNext += 1
                // The field hazard from the engine's own field samples (same IOB and night as the
                // counterfactual, so only depth and trend differ): exactly 1 at identity.
                let hF = fieldBg.isFinite ? hazard(bg: fieldBg, trend: fieldTrend, iobn: iobn, night: night) : e.hField
                let w = bg.isFinite && hF > 0 ? min(1, hazard(bg: bg, trend: trend, iobn: iobn, night: night) / hF) : 1
                gated.append((Date(timeIntervalSince1970: e.t), w))
                if w < 1 { active.append((Date(timeIntervalSince1970: e.t), -(1 - w) * e.gcsf, 1)) }
            }
        }
        guard model.addBack ?? true else { return }
        guard bg.isFinite, bg < model.gateBg, csf > 0 else { return }  // gateBg 400 = no gate
        if let last = started.last, t.timeIntervalSince(last.t) < model.refractoryMin * 60 { return }
        let h = hazard(bg: bg, trend: trend, iobn: iobn, night: night, projected: P)
        guard u < h, !model.doses.isEmpty else { return }
        var g = model.doses[min(model.doses.count - 1, Int(u2 * Double(model.doses.count)))]
        if let oc = model.overcorrect { g = min(80, max(3, g * (1 + oc * max(0, 80 - bg) / 20))) }
        active.append((t, g, model.mgdlPerGram ?? csf)); started.append((t, g))
    }

    private func cumAt(_ sec: Double) -> Double {
        guard sec > 0 else { return 0 }
        let k = sec / 300.0, i = Int(k)
        if i >= cum.count - 1 { return cum.last! }
        return cum[i] + (cum[i + 1] - cum[i]) * (k - Double(i))
    }

    /// Glucose added by all active responses over (from, to], mg/dL.
    func delta(from: Date, to: Date) -> Double {
        var d = 0.0
        let horizon = Double(model.kernel.count) * 300
        active.removeAll { from.timeIntervalSince($0.start) > horizon }
        for a in active {
            d += a.grams * a.csf * (cumAt(to.timeIntervalSince(a.start)) - cumAt(from.timeIntervalSince(a.start)))
        }
        return d
    }
}
