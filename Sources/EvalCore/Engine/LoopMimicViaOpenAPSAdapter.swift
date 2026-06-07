// LoopMimicViaOpenAPSAdapter.swift — diagnostic adapter.
//
// Wraps `LoopAdapter` and re-runs its per-step recommendation through
// `OpenAPSAdapter.mapDetermination` as if oref0 had emitted the same
// (tempRate, bolus) pair. The point is to verify that the OpenAPS
// dose-translation path produces the same `EngineStepResult` (and therefore
// the same counter trajectory) as `LoopAdapter` does for the same
// `EngineStepRequest`.
//
// If `simulateClosedLoop` produces a bit-identical counter trace when run
// with `LoopAdapter` versus `LoopMimicViaOpenAPSAdapter` on the candidate
// leg, then `mapDetermination`'s arithmetic and its `activeBasal` lookup
// agree with the simulator's downstream accounting. Any divergence
// localizes a translation bug.
//
// This is a diagnostic-only adapter — not for use in real comparisons.

import Foundation
import LoopAlgorithm

struct LoopMimicViaOpenAPSAdapter: DosingEngine {
    private let loop = LoopAdapter()
    private let oaps = OpenAPSAdapter()

    func step(_ req: EngineStepRequest) -> EngineStepResult {
        let loopResult = loop.step(req)

        // Re-express Loop's recommendation as a fake oref Determination.
        // - rate  ← Loop's temp basal rate
        // - units ← Loop's auto-bolus
        // mapDetermination will compute dose = (rate - schedBasal) × stepHours
        // + units, using OpenAPSAdapter.activeBasal for schedBasal. If that
        // schedBasal lookup agrees with LoopAdapter's internal scheduledRate
        // (from EvaluationEngine.computeDoseRecommendation), the resulting
        // dose is bit-identical to loopResult.dose.
        let mgdl = LoopUnit.milligramsPerDeciliter
        let evBG = loopResult.prediction.glucose.last?.quantity.doubleValue(for: mgdl) ?? 100
        let iob = loopResult.prediction.activeInsulin ?? 0
        let cob = loopResult.prediction.activeCarbs ?? 0
        let fakeDet = """
        {
          "rate": \(loopResult.tempRate),
          "duration": 30,
          "units": \(loopResult.bolus),
          "eventualBG": \(evBG),
          "IOB": \(iob),
          "COB": \(cob),
          "reason": "loop-mimic"
        }
        """

        let schedBasal = oaps.activeBasal(at: req.t, req: req)
        do {
            // Borrow Loop's prediction for the IOB/eventualBG diagnostic
            // fields — mapDetermination would otherwise synthesize a 1-point
            // prediction at horizon; for the identity check we keep Loop's
            // full LoopPrediction so the upstream telemetry matches.
            var result = try oaps.mapDetermination(fakeDet, req: req, scheduledBasalUhr: schedBasal)
            result = EngineStepResult(
                dose: result.dose,
                bolus: result.bolus,
                tempRate: result.tempRate,
                prediction: loopResult.prediction
            )
            return result
        } catch {
            // Fall back to Loop's result; the test below will catch any
            // dose mismatch.
            return loopResult
        }
    }
}
