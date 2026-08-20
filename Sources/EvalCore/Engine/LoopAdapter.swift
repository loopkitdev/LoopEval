// LoopAdapter.swift — DosingEngine implementation backed by LoopAlgorithm.
//
// Thin pass-through to `ClosedLoopSimulator.simStepDose(...)`. Keeps the
// existing canonical doses-path generatePrediction call intact so identity
// sanity (LoopAdapter on both legs, equal configs) stays bit-identical to
// pre-engine-refactor behavior.

import Foundation
import LoopAlgorithm

struct LoopAdapter: DosingEngine {
    func step(_ req: EngineStepRequest) -> EngineStepResult {
        // simStepDose lives on `EvaluationEngine` (see ClosedLoopSimulator.swift
        // which is an `extension EvaluationEngine`).
        let r = EvaluationEngine.simStepDose(
            t: req.t,
            input: req.input,
            config: req.config,
            therapy: req.therapy,
            glucoseMgdl: req.glucoseMgdl,
            glucoseSamples: req.glucoseSamples,
            extraISFMultiplier: req.extraISFMultiplier,
            forecastOffsetMgdl: req.forecastOffsetMgdl,
            perStepIsfMultByTime: req.perStepIsfMultByTime,
            isfBoostActiveOnly: req.isfBoostActiveOnly,
            egpPhysicalDecomposition: req.egpPhysicalDecomposition
        )
        return EngineStepResult(
            dose: r.dose,
            bolus: r.bolus,
            tempRate: r.tempRate,
            prediction: r.prediction,
            manualBolusRec: r.manualBolusRec,
            tempAction: r.tempAction
        )
    }
}
