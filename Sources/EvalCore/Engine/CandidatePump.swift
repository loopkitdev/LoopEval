// CandidatePump.swift — what the candidate's pump actually delivers, given what its controller
// commanded and what state the pump was in.
//
// A temp basal lasts 30 min unless re-issued. Basal goes out in whole pulses (the accumulator
// carries the sub-pulse remainder while the rate holds, drops it on a re-issue). Inside a
// disruption the controller's command never reaches the pump: the pump delivers the field's
// recorded basal (suspend, Loop offline, open loop, manual temp), keeps running its last command
// until that expires (pump error), or runs the schedule (stale CGM, Loop-offline gap).

import Foundation
import LoopAlgorithm

struct CandidatePump {
    /// Loop temp basals carry a 30-min duration. The next CGM cycle normally overwrites them;
    /// across a CGM gap nothing does, so the temp expires and scheduled basal resumes.
    static let tempBasalDuration: TimeInterval = 30 * 60

    private let basalAcc: PumpModel.BasalAccumulator
    /// The candidate's last temp basal that actually reached the pump, and when.
    private(set) var lastIssuedRate: Double? = nil
    private(set) var lastIssuedT: Date = .distantPast

    init(pulseQuantum: Double) {
        basalAcc = PumpModel.BasalAccumulator(quantum: pulseQuantum)
    }

    static func scheduledRate(at t: Date, in schedule: [AbsoluteScheduleValue<Double>]) -> Double {
        schedule.first(where: { $0.startDate <= t && $0.endDate > t })?.value
            ?? schedule.closestPrior(to: t)?.value ?? 0
    }

    /// The controller's command reached the pump.
    mutating func issued(rate: Double, at t: Date) {
        lastIssuedRate = rate; lastIssuedT = t
    }

    /// Field delivery (a disruption other than a pump error): the pump runs what the field
    /// recorded, and the controller's earlier command must not resume afterwards (a pump error
    /// right after the window would otherwise continue it). Returns (rate, scheduled rate).
    mutating func fieldRecordRate(at t: Date, fieldDoses: [EvalInsulinDose],
                                  fieldSchedule: [AbsoluteScheduleValue<Double>]) -> (rate: Double, scheduled: Double) {
        let fieldRate = fieldDoses.last(where: {
            $0.deliveryType == .basal && $0.startDate <= t && $0.endDate > t
        })?.tempRate
        let sched = Self.scheduledRate(at: t, in: fieldSchedule)
        lastIssuedRate = nil
        return (fieldRate ?? sched, sched)
    }

    /// Pump error: a cycle whose command never reached the pod ("Pod not connected", comms
    /// timeout). The pod is not off: it keeps running its last command until that expires, then
    /// the schedule. (bddp11: every one of 1,723 pump-error windows is covered by a temp that
    /// started before it; treating them as outages removed 59 U the real pump delivered.)
    func lastCommandRate(at t: Date, schedule: [AbsoluteScheduleValue<Double>]) -> (rate: Double, scheduled: Double) {
        let sched = Self.scheduledRate(at: t, in: schedule)
        if let r = lastIssuedRate, t.timeIntervalSince(lastIssuedT) < Self.tempBasalDuration {
            return (r, sched)
        }
        return (sched, sched)
    }

    /// One step's delivery: a temp segment [t, tempSegEnd] (basal pulses at `rate` + the
    /// auto-bolus) and, when the step outlasts the temp (a CGM gap), scheduled basal for the rest.
    struct StepDelivery {
        let tempSegEnd: Date
        let basalDelivered: Double     // temp-segment basal
        let tempVolume: Double         // temp-segment basal + bolus
        let schedRemainder: Double     // scheduled basal after the temp expired
        var absolute: Double { tempVolume + schedRemainder }
        var basal: Double { basalDelivered + schedRemainder }
    }

    /// `fieldRecord` non-nil: the pump delivers what the field pump delivered over [t, stepEnd)
    /// (auto-only doses: manual boluses pass through on their own), integrated over the step's
    /// own interval -- steps are decision/CGM times, not a fixed grid.
    mutating func deliver(from t: Date, to stepEnd: Date, rate: Double, bolus: Double,
                          fieldRecord: [EvalInsulinDose]?, fieldSchedule: [AbsoluteScheduleValue<Double>],
                          schedule: [AbsoluteScheduleValue<Double>]) -> StepDelivery {
        let stepDur = max(1.0, stepEnd.timeIntervalSince(t))
        let tempSec = fieldRecord != nil ? stepDur : min(stepDur, Self.tempBasalDuration)
        let tempSegEnd = t.addingTimeInterval(tempSec)
        let basalDelivered = fieldRecord.map {
            EvaluationEngine.integrateFieldDelivery($0, schedule: fieldSchedule, from: t, to: stepEnd)
        } ?? basalAcc.deliver(rate: rate, seconds: tempSec)
        var schedRemainder = 0.0
        if stepDur > Self.tempBasalDuration {
            schedRemainder = EvaluationEngine.integrateScheduledBasal(schedule, from: tempSegEnd, to: stepEnd)
        }
        return StepDelivery(tempSegEnd: tempSegEnd, basalDelivered: basalDelivered,
                            tempVolume: basalDelivered + bolus, schedRemainder: schedRemainder)
    }
}
