// DoseSetInspector.swift — expose the per-cycle dose set for ground-truth comparison
//
// Matching a dose is not the same as matching the dose SET a controller held at a given
// instant. Loop trims the in-progress temp basal at `now` (its `basalDosingEnd`) and
// `annotated(with: basal)` then SPLITS doses at basal-schedule boundaries, so the array
// that reaches `getGlucoseEffects` is not the array of uploaded records. A reconstruction
// can reproduce every uploaded record exactly and still hand the algorithm a different
// set at decision time.
//
// The instrumented rig captures Loop's own post-annotation array per cycle, so the
// comparison is available — this type produces our side of it through the SAME code path
// the simulator uses (`InputWindowBuilder.buildInput` then `annotated(with:)`), rather
// than a reimplementation that could agree or disagree for its own reasons.

import Foundation
import LoopAlgorithm

/// One dose as the algorithm sees it, after windowing, trimming and basal annotation.
public struct InspectedDose: Sendable {
    public let type: String            // "bolus" | "tempBasal" | "basal"
    public let startDate: Date
    public let endDate: Date
    public let volume: Double          // units actually attributed to this segment
    public let netBasalUnits: Double   // units relative to scheduled basal

    public init(type: String, startDate: Date, endDate: Date, volume: Double, netBasalUnits: Double) {
        self.type = type
        self.startDate = startDate
        self.endDate = endDate
        self.volume = volume
        self.netBasalUnits = netBasalUnits
    }
}

/// Rebuilds the dose set our controller would hold at an arbitrary instant.
///
/// `at:` must be the instant the real controller made its decision — on a device whose CGM
/// arrives late, the triggering sample can be many minutes older, and anchoring on the
/// sample instead of `now` silently trims the running temp short.
public struct DoseSetInspector: Sendable {
    private let builder: InputWindowBuilder

    public init(glucose: [EvalGlucoseSample],
                doses: [EvalInsulinDose],
                carbs: [EvalCarbEntry],
                therapy: TherapyTimeline,
                config: EvalConfig) {
        self.builder = InputWindowBuilder(glucose: glucose, doses: doses, carbs: carbs,
                                          therapyTimeline: therapy, config: config)
    }

    /// The annotated dose set at `t`, or nil when there is too little data to decide
    /// (same guard the simulator applies).
    public func doseSet(at t: Date) -> [InspectedDose]? {
        guard let input = builder.buildInput(at: t, decisionAnchor: t) else { return nil }
        guard !input.basal.isEmpty else { return [] }
        return input.doses.annotated(with: input.basal).map { d in
            let kind: String
            switch d.type {
            case .bolus: kind = "bolus"
            case .basal: kind = "basal"
            }
            return InspectedDose(type: kind, startDate: d.startDate, endDate: d.endDate,
                                 volume: d.volume, netBasalUnits: d.netBasalUnits)
        }
    }
}
