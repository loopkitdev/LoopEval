// DecisionTiming.swift — when the replay's controllers decide, which cycles they skip, and what
// state the system was in at each decision (disruptions, stale CGM).
//
// Step times come from, in order of precedence: the field's recorded decision times
// (--decision-times-csv), one per CGM sample (default), or a fixed grid. A step whose decision
// the field never made, or couldn't make, is skipped in both arms: no CGM near it, or the field
// controller refused to dose (no-dose guard) or had a bolus in flight.

import Foundation
import LoopAlgorithm

struct DecisionTiming {
    let stepTimes: [Date]
    let evalStep: TimeInterval
    let substrate: [EvalGlucoseSample]          // simGlucose: the field CGM the decisions run on
    let cgmStaleGuardSec: TimeInterval
    let noDoseGuardTimes: Set<Date>
    let bolusInProgressTimes: Set<Date>
    let tempStrategyTimes: Set<Date>
    let outages: [Outage]
    let outageBasalContinuesReasons: Set<String>
    let timeBasedAF: Bool
    /// The last COMPLETED loop, the deployed timeBasedDoseApplicationFactor's reference
    /// (errored and guard-skipped cycles don't advance it).
    private(set) var lastCompletedLoopT: Date? = nil

    init(decisionTimes: [Date], decisionsFromCgm: Bool, substrate: [EvalGlucoseSample],
         from evalStart: Date, to end: Date, evalStep: TimeInterval, cgmStaleGuardSec: TimeInterval,
         noDoseGuardTimes: Set<Date>, bolusInProgressTimes: Set<Date>, tempStrategyTimes: Set<Date>,
         outages: [Outage], outageBasalContinuesReasons: Set<String>, timeBasedAF: Bool) {
        // CGM-driven: one step per CGM sample in the window (irregular cadence). Grid: the
        // regular evalStep march. stepEnd - t is the interval to the NEXT step, used wherever a
        // step duration appears; a gap (stepDur >> evalStep) is capped for delivery by the pump.
        var times: [Date] = []
        if !decisionTimes.isEmpty {
            times = decisionTimes.sorted().filter { $0 >= evalStart && $0 <= end }
        } else if decisionsFromCgm {
            times = substrate.map { $0.startDate }.filter { $0 >= evalStart && $0 <= end }
        } else {
            var tt = evalStart
            while tt <= end { times.append(tt); tt = tt.addingTimeInterval(evalStep) }
        }
        self.stepTimes = times
        self.evalStep = evalStep
        self.substrate = substrate
        self.cgmStaleGuardSec = cgmStaleGuardSec
        self.noDoseGuardTimes = noDoseGuardTimes
        self.bolusInProgressTimes = bolusInProgressTimes
        self.tempStrategyTimes = tempStrategyTimes
        self.outages = outages
        self.outageBasalContinuesReasons = outageBasalContinuesReasons
        self.timeBasedAF = timeBasedAF
    }

    /// The end of step `i`: the next step's time, or one evalStep after the last.
    func stepEnd(_ i: Int) -> Date {
        i + 1 < stepTimes.count ? stepTimes[i + 1] : stepTimes[i].addingTimeInterval(evalStep)
    }

    /// Per-cycle dosing strategy for mixed-strategy donors: true = temp basal, nil = unchanged.
    func useTempBasalStrategy(at t: Date) -> Bool? {
        tempStrategyTimes.isEmpty ? nil : tempStrategyTimes.contains(t)
    }

    enum Skip { case noCGM, noDoseGuard }

    /// Why the field had no decision at `t`, if it had none.
    /// - noCGM: Loop is CGM-triggered; more than the stale guard from ANY CGM sample there is no
    ///   cycle. One missing sample is paved over (a neighbour is within the guard), and the
    ///   post-gap step runs, but no decisions are generated deep inside a CGM outage.
    /// - noDoseGuard: the field controller ran but refused to dose on stale inputs
    ///   (pumpDataTooOld / glucoseTooOld), or a bolus was in flight (in both arms). A bolus-in-
    ///   progress cycle outside a pump error still completed, for the time-based AF clock.
    mutating func skip(at t: Date) -> Skip? {
        if cgmStaleGuardSec > 0 {
            let nextIdx = EvaluationEngine.bestGlucoseIndex(at: t, in: substrate)
            let prevIdx = EvaluationEngine.latestGlucoseIndex(at: t, in: substrate)
            let dNext = abs(substrate[nextIdx].startDate.timeIntervalSince(t))
            let dPrev = abs(t.timeIntervalSince(substrate[prevIdx].startDate))
            if min(dNext, dPrev) > cgmStaleGuardSec { return .noCGM }
        }
        if noDoseGuardTimes.contains(t) || bolusInProgressTimes.contains(t) {
            if bolusInProgressTimes.contains(t) && outages.containing(t)?.reason != "pump_error" {
                lastCompletedLoopT = t
            }
            return .noDoseGuard
        }
        return nil
    }

    /// Deployed timeBasedDoseApplicationFactor = min(1, sinceLastCompleted / 5 min): a loop
    /// firing < 5 min after a COMPLETED loop applies proportionally less of the correction
    /// (retries after failures are not damped). Records this cycle as completed unless it sat in
    /// a pump-error window. 1 when the factor is off.
    mutating func timeBasedAFScale(at t: Date) -> Double {
        let scale: Double = timeBasedAF
            ? (lastCompletedLoopT.map { Swift.min(1.0, Swift.max(0.0, t.timeIntervalSince($0)) / 300.0) } ?? 1.0)
            : 1.0
        if outages.containing(t)?.reason != "pump_error" { lastCompletedLoopT = t }
        return scale
    }

    /// The system's state at a decision, which decides what the candidate's pump can do.
    struct Conditions {
        let outage: Outage?
        /// A disruption whose reason continues scheduled basal (e.g. a Loop-offline gap).
        let basalContinues: Bool
        /// Any other disruption, manual temps excepted.
        let inOutage: Bool
        /// The pump runs the field's record (suspend, Loop offline, open loop, manual temp): the
        /// controller enacted nothing. Every disruption but a pump error.
        let fieldDelivery: Bool
        /// A cycle whose command never reached the pump.
        let pumpError: Bool
        /// The candidate's latest CGM reading is older than the guard: no NEW dose (Loop's
        /// inputDataRecencyInterval, which the replay's dose path otherwise bypasses).
        let cgmStale: Bool
    }

    /// `counterGlucose`/`counterMissing`: the candidate's CGM so far (a plant can withhold
    /// readings; staleness is judged on what the candidate's CGM actually gave).
    func conditions(at t: Date, counterGlucose: [EvalGlucoseSample], counterMissing: [Bool]) -> Conditions {
        let outageNow = outages.isEmpty ? nil : outages.containing(t)
        let basalContinues = outageNow.map { outageBasalContinuesReasons.contains($0.reason) } ?? false
        // MANUAL TEMP: the user set a temp on the pump; it runs whatever Loop decides (i040 09-10:
        // 0.05 U/h for 4 h through recommendations of 2.35-3.0 U/h). Not an outage: the pump
        // delivers, just not what the controller asks.
        let manualTemp = outageNow?.reason == "manual_temp"
        let inOutage = outageNow != nil && !basalContinues && !manualTemp
        // Zero delivery in these windows dropped real insulin: i056's open-loop days (~21 U of
        // scheduled basal per 2-3 day window) replayed as no basal at all.
        let fieldDelivery = manualTemp || (inOutage && outageNow?.reason != "pump_error")
        var cgmStale = false
        if cgmStaleGuardSec > 0 && !inOutage {
            var idx = EvaluationEngine.latestGlucoseIndex(at: t, in: counterGlucose)
            while idx > 0 && counterMissing[idx] { idx -= 1 }   // the latest reading the CGM gave
            let latestT = counterGlucose[idx].startDate
            if latestT <= t {
                cgmStale = t.timeIntervalSince(latestT) > cgmStaleGuardSec
            }
        }
        return Conditions(outage: outageNow, basalContinues: basalContinues, inOutage: inOutage,
                          fieldDelivery: fieldDelivery,
                          pumpError: inOutage && outageNow?.reason == "pump_error", cgmStale: cgmStale)
    }
}
