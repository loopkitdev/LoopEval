import Foundation

/// The counterfactual body's insulin sensitivity: how much glucose one unit of insulin moves in the
/// simulated person, as distinct from the ISF the controller believes (its configured schedule).
///
/// Default `.calculated` (Pete 2026-11-17): a candidate that does not read the person's schedule
/// must not be judged by a body built from that schedule, and a wrong or strongly shaped schedule
/// would otherwise set what each unit of dosing difference costs (handoff
/// docs/handoffs/2026-11-17-simulator-replay-calculated-isf.md).
public enum BodyISF: Sendable, Equatable {
    /// Flat ISF from the ISF yardstick's start rule, K / TDD^b, with TDD measured from the delivered
    /// insulin (boluses + basal of every kind) over the clean days among the `tddDays` before the simulated
    /// interval (`EvaluationEngine.measuredTDD`).
    /// Falls back to the interval's own TDD when there is too little history, then to `.schedule`.
    case calculated
    /// A flat ISF in mg/dL/U, referencing no therapy setting.
    case flat(Double)
    /// The person's configured ISF schedule (the body ISF of every replay before 2026-11-17 that ran
    /// with --candidate-infer-sensitivity).
    case schedule
    /// The controller's ISF after the candidate's sensitivity / insulin-needs scaling, so the body
    /// moves with the dial (the body of every replay before 2026-11-17 without
    /// --candidate-infer-sensitivity).
    case controller

    /// ISF yardstick start rule (analysis/dist_views/ice/isf_yardstick.py `start_rule`; parameters
    /// from isf_start_rule.py, fitted on 159 cohort members). About ±25% per person.
    public static let startRuleK = 1266.76
    public static let startRuleB = 0.902
    public static let tddDays: Double = 10
    public static let minTDDDays: Double = 2

    public static func startRule(tdd: Double) -> Double { startRuleK / pow(tdd, startRuleB) }

    /// Parses the --patient-isf value: `calculated`, `schedule`, `controller` or a positive number.
    public init?(argument: String) {
        switch argument.lowercased() {
        case "calculated": self = .calculated
        case "schedule": self = .schedule
        case "controller": self = .controller
        default:
            guard let v = Double(argument), v > 0 else { return nil }
            self = .flat(v)
        }
    }
}

/// What the body ran at, written to the trace (`bodyISF`) so a result says which body it used.
public struct BodyISFInfo: Codable, Sendable, Equatable {
    public let source: String      // calculated | flat | schedule | controller | schedule (no TDD)
    public let isf: Double?        // mg/dL/U when flat or calculated
    public let tdd: Double?        // U/day behind a calculated ISF
    public let tddDays: Double?    // days of delivery the TDD averages
    public let tddWindow: String?  // "before" the interval, or the interval itself ("window")
}

extension EvaluationEngine {
    /// Mean delivered insulin per day over the whole 24-hour blocks of [from, to), counted back from `to`.
    /// Insulin is counted as the body counts it: the dose record annotated with the scheduled basal and its
    /// gaps filled with scheduled basal (`annotated(with:fillBasalGaps:)`, as the counterfactual strips the
    /// field's insulin), since an export leaves scheduled basal that ran implicit. A block counts only when
    /// at least 22 of its 24 hours hold a dose record, so the days before an export starts and days with no
    /// pump (pumpless disruptions) are left out rather than read as scheduled basal alone.
    /// nil under `BodyISF.minTDDDays` clean blocks.
    static func measuredTDD(doses: [EvalInsulinDose], basal: [AbsoluteScheduleValue<Double>],
                            from: Date, to: Date) -> (tdd: Double, days: Double)? {
        let nBlocks = Int((to.timeIntervalSince(from) / 86400).rounded(.down))
        guard nBlocks > 0 else { return nil }
        let lo0 = to.addingTimeInterval(-Double(nBlocks) * 86400)
        let inRange = doses.filter { $0.endDate > lo0 && $0.startDate < to }
        guard !inRange.isEmpty else { return nil }
        // Hours holding a dose record (a bolus, or any part of a recorded basal segment).
        var hourSeen = [Bool](repeating: false, count: nBlocks * 24)
        func hour(_ t: Date) -> Int { min(nBlocks * 24 - 1, max(0, Int((t.timeIntervalSince(lo0) / 3600).rounded(.down)))) }
        for d in inRange {
            let h0 = hour(max(d.startDate, lo0))
            let h1 = d.deliveryType == .basal ? hour(min(d.endDate, to).addingTimeInterval(-0.001)) : h0
            for h in h0...max(h0, h1) { hourSeen[h] = true }
        }
        // Units per block from the gap-filled record.
        let sched = basal.trimmed(from: lo0, to: to)
        let filled = inRange.sorted { $0.startDate < $1.startDate }.annotated(with: sched, fillBasalGaps: true)
        var units = [Double](repeating: 0, count: nBlocks)
        for d in filled {
            let full = d.endDate.timeIntervalSince(d.startDate)
            if full <= 0 {
                if d.startDate >= lo0 && d.startDate < to { units[hour(d.startDate) / 24] += d.volume }
                continue
            }
            var a = max(d.startDate, lo0)
            let end = min(d.endDate, to)
            while a < end {
                let k = hour(a) / 24
                let b = min(end, lo0.addingTimeInterval(Double(k + 1) * 86400))
                units[k] += d.volume * b.timeIntervalSince(a) / full
                a = b
            }
        }
        let clean = (0..<nBlocks).filter { k in (0..<24).filter { hourSeen[k * 24 + $0] }.count >= 22 }
        guard Double(clean.count) >= BodyISF.minTDDDays else { return nil }
        let tdd = clean.map { units[$0] }.reduce(0, +) / Double(clean.count)
        return tdd > 0 ? (tdd, Double(clean.count)) : nil
    }
}
