// CandidateBody.swift — what turns the candidate's insulin into the candidate's glucose.
//
// simulateClosedLoop keeps the candidate's glucose as one value per substrate sample
// (`counterMgdl`, timestamps from `counterGlucose`), plus a "no reading" flag per sample
// (`counterMissing`). Only a body writes them. Two bodies exist:
//
//   ICEReplayBody          counterfactual mode: the field's own glucose change plus the
//                          modeled effect of candidate-minus-field insulin (ICE replay), with
//                          counter-regulation and the CGM-gap re-anchor.
//   ExternalPlantBody      --external-plant: a separate process integrates the candidate's
//                          doses and returns its CGM. It may also return the plant person's
//                          actions; applying them is the caller's job, not the body's.
//
// Without a counterfactual (decision-time replay, open-loop runs) there is no candidate body: the
// candidate never feeds back and its glucose is the field's.

import Foundation
import LoopAlgorithm

/// The CGM-gap re-anchor shared by both counterfactual bodies. Across a gap longer than the
/// threshold the one big advance is unreliable, so the gap-end LEVEL comes from the real CGM,
/// carrying only a significant (> 10 mg/dL) pre-gap divergence across. At candidate == field
/// the offset is 0, so identity holds.
enum GapReanchor {
    static func level(counterBeforeGap: Double, fieldBeforeGap: Double, fieldAfterGap: Double) -> Double {
        let gapOffset = counterBeforeGap - fieldBeforeGap
        return abs(gapOffset) > 10.0 ? fieldAfterGap + gapOffset : fieldAfterGap
    }
}

/// Counterfactual ICE replay: per sample interval (prev, next],
///   counter += realBGdelta + m·(E(candidate doses) − E(field doses)) + counter-regulation,
/// on ONE mid-absorption ISF timeline (E = physicalActiveEffectDelta, EGP credit zeroed).
/// realBGdelta carries all non-insulin physiology (EGP included) unscaled; m ≡ 1 unless
/// sensitivity is inferred. Identity: candidate doses == field ⇒ the counter reproduces the
/// substrate.
struct ICEReplayBody {
    let substrate: [EvalGlucoseSample]          // counterGlucose: timestamps + field values
    let realPhysDelta: [Double]                 // E(field doses) per substrate interval
    let m: [Double]                             // inferred sensitivity multiplier per interval
    let sensitivity: [AbsoluteScheduleValue<LoopQuantity>]   // the body's ISF
    let insulinModel: InsulinModel
    let patientInsulinType: ExponentialInsulinModelPreset?
    let counterRegOnsetMgdl: Double
    let counterRegGain: Double
    let counterRegMaxRate: Double
    let gapReanchorSec: TimeInterval
    let evalStep: TimeInterval
    // ABSOLUTE counter-regulation (research): apply the full rate whenever the counterfactual is below
    // onset, not the difference from the field's. For a substrate whose field low responses (rescue carbs
    // AND the physiological rebound) were subtracted beforehand, so the field ICE no longer carries them.
    var counterRegAbsolute = false
    // First-order lag (min) on the absolute rate; 0 = instantaneous. Absolute mode only.
    var counterRegTauMin = 0.0
    // Glucose effectiveness (research, 1/min): the body's own pull back toward its operating point. The field
    // trace already carries it at the field's glucose; a counterfactual at a different glucose gets the extra
    // -SG·(counter − field) per minute. Zero at identity. 0 = off.
    var glucoseEffectivenessPerMin = 0.0
    // LOW RESPONSE (research): low-driven upward effects (rescue carbs + physiological rebound) generated
    // where the counterfactual itself goes low (LowResponse.swift); the caller steps it each cycle. nil = off.
    var lowResponse: LowResponseState? = nil
    // HIGH-side defense (research): a mirrored LowResponseModel, stepped by the caller like `lowResponse`. nil = off.
    var highResponse: LowResponseState? = nil
    // Per-sample amounts (mg/dL, keyed by whole Unix seconds of the CGM sample) removed from the FIELD's
    // glucose change: the field's own low responses, subtracted as an ICE adjustment (never from absolute
    // CGM, which would drift). nil = off.
    var lowResponseSubtract: [Int: Double]? = nil
    var crLevel = 0.0                           // absolute counter-reg rate (mg/dL/min), lagged; state

    /// Advance every sample in (substrate[advIdx-1], stepEnd]; returns the next unadvanced index.
    mutating func advance(from advIdx: Int, through stepEnd: Date, doses: [EvalInsulinDose],
                 basal: [AbsoluteScheduleValue<Double>], counter: inout [Double]) -> Int {
        let mgdlUnit = LoopUnit.milligramsPerDeciliter
        var advIdx = advIdx
        while advIdx < substrate.count && substrate[advIdx].startDate <= stepEnd {
            let prevIdx = advIdx > 0 ? advIdx - 1 : advIdx
            let prevT = substrate[prevIdx].startDate
            let nextT = substrate[advIdx].startDate
            let realBGdelta = substrate[advIdx].quantity.doubleValue(for: mgdlUnit)
                - substrate[prevIdx].quantity.doubleValue(for: mgdlUnit)
            let candPhys = EvaluationEngine.physicalActiveEffectDelta(
                doses: doses,
                basal: basal,
                sensitivity: sensitivity,
                from: prevT, to: nextT,
                insulinModel: insulinModel,
                patientInsulinType: patientInsulinType)
            let lrSub = lowResponseSubtract?[Int(nextT.timeIntervalSince1970.rounded())] ?? 0
            let stepDelta = realBGdelta - lrSub + m[advIdx] * (candPhys - realPhysDelta[advIdx])
                + (lowResponse?.delta(from: prevT, to: nextT) ?? 0) + (highResponse?.delta(from: prevT, to: nextT) ?? 0)
            // Counter-regulation (glucagon/epinephrine) is a BG velocity that ramps with depth
            // below onset, capped. It integrates at the step cadence: an interval spanning a
            // CGM gap is split into <= 1-step sub-intervals, the base change spread linearly,
            // so a gap doesn't multiply the velocity by its length. It is applied as a
            // DIFFERENCE from the real trajectory, counterreg(counter) − counterreg(actual)
            // (realBGdelta already carries the real body's defense), and only while the
            // counter itself is below onset: a counter running high must not shed the real
            // low's defense. Normal 5-min interval: nSub == 1.
            let totalSec = nextT.timeIntervalSince(prevT)
            let nSub = Swift.max(1, Int((totalSec / evalStep).rounded(.up)))
            let subFrac = 1.0 / Double(nSub)
            let aPrev = substrate[prevIdx].quantity.doubleValue(for: mgdlUnit)
            let aNext = substrate[advIdx].quantity.doubleValue(for: mgdlUnit)
            if gapReanchorSec > 0 && totalSec > gapReanchorSec {
                counter[advIdx] = GapReanchor.level(counterBeforeGap: counter[prevIdx],
                                                    fieldBeforeGap: aPrev, fieldAfterGap: aNext)
                advIdx += 1
                continue
            }
            var bg = counter[prevIdx]
            for k in 0..<nSub {
                var crSub = 0.0
                let aSub = aPrev + (aNext - aPrev) * (Double(k) / Double(nSub))
                if counterRegOnsetMgdl > 0 && counterRegAbsolute {
                    let dtMin = totalSec * subFrac / 60.0
                    let belowC = counterRegOnsetMgdl - bg
                    let target = belowC > 0 ? Swift.min(counterRegGain * belowC, counterRegMaxRate) : 0.0
                    let prevLevel = crLevel
                    crLevel = counterRegTauMin > 0
                        ? target + (crLevel - target) * exp(-dtMin / counterRegTauMin) : target
                    crSub = 0.5 * (prevLevel + crLevel) * dtMin
                } else if counterRegOnsetMgdl > 0 {
                    let belowC = counterRegOnsetMgdl - bg
                    if belowC > 0 {
                        let rateC = Swift.min(counterRegGain * belowC, counterRegMaxRate)
                        let belowA = counterRegOnsetMgdl - aSub
                        let rateA = belowA > 0 ? Swift.min(counterRegGain * belowA, counterRegMaxRate) : 0.0
                        crSub = (rateC - rateA) * (totalSec * subFrac / 60.0)
                    }
                }
                if glucoseEffectivenessPerMin > 0 {
                    crSub -= glucoseEffectivenessPerMin * (bg - aSub) * (totalSec * subFrac / 60.0)
                }
                bg += stepDelta * subFrac + crSub
            }
            counter[advIdx] = bg
            advIdx += 1
        }
        return advIdx
    }
}

/// --external-plant: forwards the candidate's doses to the plant process and writes its CGM
/// back into the candidate's glucose. Owns the bookkeeping of what the plant has been sent and
/// how far it has advanced; the plant's reply (with any person actions) goes back to the caller.
final class ExternalPlantBody {
    let plant: ExternalPlant
    let substrate: [EvalGlucoseSample]
    let gapReanchorSec: TimeInterval

    /// The end of the last interval whose doses were SENT. Steps that `continue` early (stale
    /// CGM, no-dose guard) never call the plant, but doses still start inside them -- passed-
    /// through manual boluses and, under --cf-identity, the real dose stream.
    private var dosesSentThrough: Date? = nil
    /// Doses appended during the run are forwarded by INSERTION, not by date: a dose can be
    /// appended dated before the last send's end (a plant bolus sits 1 s before its decision so
    /// the decision's input builder keeps it), and a date window drops it -- the plant never got
    /// any plant bolus in 8e86860 while Loop's IOB counted every one. The seeded history (the
    /// real doses before the run, or the whole window under --cf-identity) keeps the date window.
    private let seedCount: Int
    private var nextAppended: Int                   // first appended dose not yet considered
    private var heldAppended: [Int] = []            // appended doses starting at/after a send's end
    /// The end of the last interval the plant advanced over. A step that `continue`s early never
    /// calls the plant, so each call advances it from here and skipped intervals are covered.
    private(set) var advancedThrough: Date? = nil
    /// Candidate state from the last in-step call, for a catch-up call made before this step's
    /// own state exists.
    var lastState: [String: Double] = [:]

    init(plant: ExternalPlant, substrate: [EvalGlucoseSample], gapReanchorSec: TimeInterval, seedCount: Int) {
        self.plant = plant
        self.substrate = substrate
        self.gapReanchorSec = gapReanchorSec
        self.seedCount = seedCount
        self.nextAppended = seedCount
    }

    /// Advance the plant over (advancedThrough, t1]: send the doses started since the last send,
    /// and write the plant's CGM -- or "no reading" -- into every sample in the interval.
    func advance(through t1: Date, now: Date, state: [String: Double], doses allDoses: [EvalInsulinDose],
                 counter: inout [Double], missing: inout [Bool]) throws -> ExternalPlant.Reply {
        let mgdlUnit = LoopUnit.milligramsPerDeciliter
        let t0 = min(advancedThrough ?? now, now)
        var sampleIdx: [Int] = []
        var k = EvaluationEngine.latestGlucoseIndex(at: t0, in: substrate)
        if k < substrate.count && substrate[k].startDate <= t0 { k += 1 }
        while k < substrate.count && substrate[k].startDate <= t1 {
            sampleIdx.append(k); k += 1
        }
        advancedThrough = t1
        // Everything that started since the last send, not just this step: a skipped cycle
        // before this one may hold doses (bddp11 under --cf-identity: 19 real doses, 26.3 U,
        // incl. a 5.8 U bolus, never reached the plant).
        let sendFrom = dosesSentThrough ?? now
        var doses = allDoses[..<seedCount].filter { $0.startDate >= sendFrom && $0.startDate < t1 }
        var held: [Int] = []
        for i in heldAppended + Array(nextAppended..<allDoses.count) {
            let d = allDoses[i]
            if d.startDate >= t1 { held.append(i); continue }
            // the plant integrates from t0: a bolus appended dated just before it lands at t0
            doses.append(d.deliveryType == .bolus && d.startDate < t0
                ? EvalInsulinDose(deliveryType: .bolus, startDate: t0, endDate: t0, volume: d.volume,
                                  insulinType: d.insulinType, automatic: d.automatic)
                : d)
        }
        heldAppended = held; nextAppended = allDoses.count
        doses.sort { $0.startDate < $1.startDate }
        dosesSentThrough = t1
        let reply = try plant.advance(
            t0: t0, t1: t1, doses: doses,
            samples: sampleIdx.map { substrate[$0].startDate }, state: state)
        for (j, idx) in sampleIdx.enumerated() {
            if let v = reply.bg[j] {
                counter[idx] = v; missing[idx] = false
            } else {
                missing[idx] = true
                counter[idx] = idx > 0 ? counter[idx - 1] : counter[idx]
            }
        }
        // GAP RE-ANCHOR, on the plant's behalf. The gap is a property of the DATA, not of the
        // plant's physiology (one measured case: a 77 h no-CGM gap taken as a single step pinned a
        // replay at 2,300 mg/dL), so the same rule as the ICE replay applies, with the same
        // identity guarantee. `--cf-gap-reanchor-min 0` disables it, for a plant that handles
        // gaps itself.
        if gapReanchorSec > 0 {
            for (j, idx) in sampleIdx.enumerated() {
                let prevIdx = idx > 0 ? idx - 1 : idx
                guard idx > 0, let plantBG = reply.bg[j] else { continue }
                let span = substrate[idx].startDate.timeIntervalSince(substrate[prevIdx].startDate)
                guard span > gapReanchorSec else { continue }
                let aPrev = substrate[prevIdx].quantity.doubleValue(for: mgdlUnit)
                let aNext = substrate[idx].quantity.doubleValue(for: mgdlUnit)
                let anchored = GapReanchor.level(counterBeforeGap: counter[prevIdx],
                                                 fieldBeforeGap: aPrev, fieldAfterGap: aNext)
                if abs(anchored - plantBG) > 0.5 {
                    FileHandle.standardError.write(Data(
                        "cf gap re-anchor (external plant): \(Int(span / 60))min gap at \(substrate[idx].startDate) — plant returned \(String(format: "%.0f", plantBG)), re-anchored to \(String(format: "%.0f", anchored)) mg/dL\n".utf8))
                }
                counter[idx] = anchored
            }
        }
        return reply
    }
}
