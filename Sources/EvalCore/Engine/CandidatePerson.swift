// CandidatePerson.swift — the person's actions in the candidate arm: manual boluses, carb entries
// and Temporary Overrides that the controller doesn't decide.
//
// Two sources, never both after burn-in:
//   FieldManualBoluses  the field's own manual boluses, carried into the candidate's dose history
//                       verbatim, resized by the candidate-vs-field IOB difference, or replaced by
//                       the candidate's calculator recommendation. The field's carb entries stay in
//                       the candidate's carb store unchanged.
//   PlantPerson         --plant-behavior: the external plant's person enters carbs, asks for
//                       boluses and starts overrides; the field's post-burn-in carbs and manual
//                       boluses are dropped.

import Foundation
import LoopAlgorithm

/// The field's manual boluses after burn-in, in time order, consumed as the replay passes them.
struct FieldManualBoluses {
    let boluses: [EvalInsulinDose]
    /// The field's IOB at each bolus, excluding the bolus itself (only for IOB-adjusted resizing).
    let fieldIOB: [Double]
    private(set) var next = 0

    init(boluses: [EvalInsulinDose], fieldIOB: [Double]) {
        self.boluses = boluses
        self.fieldIOB = fieldIOB
    }

    /// The first not-yet-delivered bolus in [t, stepEnd), if any.
    func first(from t: Date, before stepEnd: Date) -> EvalInsulinDose? {
        boluses[next...].first(where: { $0.startDate >= t && $0.startDate < stepEnd })
    }

    /// A step the controller skipped (stale CGM, no-dose guard): its boluses still happened and
    /// go into the history verbatim. Not under --cf-identity, whose history was seeded with the
    /// whole real stream (appending again doubled them: 4 boluses, 14.4 U on bddp11).
    mutating func passThroughSkipped(t: Date, stepEnd: Date, identity: Bool, into doses: inout [EvalInsulinDose]) {
        while next < boluses.count {
            let mb = boluses[next]
            if mb.startDate >= stepEnd { break }
            if mb.startDate >= t && !identity { doses.append(mb) }
            next += 1
        }
    }

    /// Deliver the boluses in [t, stepEnd) at a decided step, by the configured policy.
    /// `committed` is the candidate insulin already given this cycle before each bolus (the
    /// automatic dose, then earlier boluses in the same step); the IOB resizing must see it, or
    /// it ignores the candidate's own same-cycle auto-bolus and can even up-size the bolus.
    mutating func deliver(t: Date, stepEnd: Date, config: EvalConfig, recommendation: Double,
                          candidateIOB: Double, maxBolus: (Date) -> Double,
                          committed: inout Double, into doses: inout [EvalInsulinDose]) {
        var recUsedThisStep = false
        while next < boluses.count {
            let mb = boluses[next]
            if mb.startDate >= stepEnd { break }
            if mb.startDate >= t {
                if config.manualBolusFromRecommendation {
                    // The candidate's OWN calculator recommendation at this step replaces the
                    // person's bolus (self-consistent, so no IOB-divergence amplification). One
                    // recommendation per step: further boluses in the step deliver 0.
                    let rec = (!recUsedThisStep && recommendation.isFinite)
                        ? recommendation * config.manualBolusRecScale : 0.0
                    recUsedThisStep = true
                    committed += rec
                    doses.append(EvalInsulinDose(
                        deliveryType: mb.deliveryType, startDate: mb.startDate, endDate: mb.endDate,
                        volume: rec, insulinType: mb.insulinType, automatic: mb.automatic))
                } else if config.iobAdjustManualBoluses && next < fieldIOB.count && candidateIOB.isFinite {
                    // x - (z - y): resize by the candidate-vs-field IOB difference, z being the
                    // candidate IOB at the moment of the bolus (step-start IOB + committed).
                    let y = fieldIOB[next]
                    let z = candidateIOB + committed
                    let adj = Swift.max(0, Swift.min(maxBolus(mb.startDate), mb.volume - (z - y)))
                    committed += adj
                    doses.append(EvalInsulinDose(
                        deliveryType: mb.deliveryType, startDate: mb.startDate, endDate: mb.endDate,
                        volume: adj, insulinType: mb.insulinType, automatic: mb.automatic))
                } else {
                    committed += mb.volume
                    doses.append(mb)
                }
            }
            next += 1
        }
    }
}

/// --plant-behavior: the external plant's person. Its carbs and overrides apply as they arrive;
/// its bolus requests wait for the next decision, where they are sized from the calculator.
struct PlantPerson {
    private(set) var pendingBoluses: [ExternalPlant.Bolus] = []
    private(set) var carbCount = 0, carbsTotalG = 0.0
    private(set) var bolusCount = 0, bolusTotalU = 0.0
    private(set) var overrideCount = 0

    /// Apply one plant reply's actions. Carbs join the candidate's carb store (sorted by
    /// startDate for InputWindowBuilder), visible from the next decision. Overrides join the
    /// candidate's override windows, through the same decision-time gate as exported ones
    /// (InputWindowBuilder: start <= t); supersession as TemporaryOverrides.windows: a window
    /// running at the new start ends there, and the new one ends at the next window's start.
    /// Returns the grams of carbs entered.
    mutating func receive(_ reply: ExternalPlant.Reply, carbs: inout [EvalCarbEntry],
                          therapy: inout TherapyTimeline) -> Double {
        var carbsG = 0.0
        for c in reply.carbs {
            let e = EvalCarbEntry(startDate: c.t, entryDate: c.t, dosingVisibleDate: c.t,
                                  quantity: LoopQuantity(unit: .gram, doubleValue: c.grams),
                                  absorptionTime: c.absorption)
            let pos = carbs.firstIndex(where: { $0.startDate > c.t }) ?? carbs.count
            carbs.insert(e, at: pos)
            carbsG += c.grams; carbsTotalG += c.grams; carbCount += 1
        }
        pendingBoluses += reply.boluses
        for o in reply.overrides {
            // The override machinery reads the raw schedules; seed them as OverrideTargets does.
            if therapy.rawBasal.isEmpty       { therapy.rawBasal = therapy.basal }
            if therapy.rawSensitivity.isEmpty { therapy.rawSensitivity = therapy.sensitivity }
            if therapy.rawCarbRatio.isEmpty   { therapy.rawCarbRatio = therapy.carbRatio }
            if therapy.rawTarget.isEmpty      { therapy.rawTarget = therapy.target }
            var ws = therapy.overrideWindows.map { w -> OverrideWindow in
                guard w.start < o.start, w.end > o.start else { return w }
                return OverrideWindow(start: w.start, end: o.start, factor: w.factor,
                                      targetLo: w.targetLo, targetHi: w.targetHi, indefinite: false,
                                      revisionKey: w.revisionKey, visibleFrom: w.visibleFrom)
            }
            let end = min(o.end, ws.filter { $0.start > o.start }.map(\.start).min() ?? o.end)
            ws.append(OverrideWindow(start: o.start, end: end, factor: o.factor,
                                     targetLo: o.targetLo, targetHi: o.targetHi))
            therapy.overrideWindows = ws.sorted { $0.start < $1.start }
            overrideCount += 1
        }
        return carbsG
    }

    /// The pending requests as one bolus, sized from the calculator recommendation shown at this
    /// decision and capped at the max bolus; clears them. 0 when nothing is pending.
    mutating func takeBolus(recommendation: Double, maxBolus: Double) -> Double {
        guard !pendingBoluses.isEmpty else { return 0 }
        let rec = recommendation.isFinite ? Swift.max(0, recommendation) : 0
        let want = pendingBoluses.reduce(0.0) { acc, b in acc + (b.units ?? 0) + (b.ratio ?? 0) * rec }
        pendingBoluses.removeAll()
        return Swift.max(0, Swift.min(maxBolus, want))
    }

    mutating func recordDelivered(_ units: Double) {
        bolusTotalU += units; bolusCount += 1
    }
}
