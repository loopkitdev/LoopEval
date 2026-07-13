// DosingEngine.swift — pluggable dose-recommendation protocol.
//
// The simulator delegates each per-step "what should the algorithm do here?"
// decision to a `DosingEngine`. Today the only adapter is `LoopAdapter`
// (Loop Algorithm via the local LoopAlgorithm package). Hosting the
// OpenAPSSwift fork (git submodule at ./OpenAPSSwift) is the next
// adapter — see `runs/2026-06-04-openapsswift-host/` for scope notes.
//
// The protocol is intentionally narrow: a single `step(_:)` call with the
// per-step request. Returns dose/bolus/tempRate plus an engine-specific
// payload. Identity sanity (same engine on both legs, equal configs)
// produces Δdose = 0 at every step — see ClosedLoopSimulator §1.
//
// IOB/COB/momentum/RC/etc. diagnostics currently come off the LoopPrediction
// inside EngineStepResult. When OpenAPSAdapter lands we'll either (a) move
// those into dedicated fields on EngineStepResult so consumers stop
// depending on Loop's concrete types, or (b) have the OpenAPS adapter
// synthesize a LoopPrediction-shaped object for diagnostic compatibility.
// Decision deferred until the OpenAPS adapter is real and we can see how
// its Determination object lines up.

import Foundation
import LoopAlgorithm

struct EngineStepRequest {
    let t: Date
    let input: PredictionInput
    let config: EvalConfig
    let therapy: TherapyTimeline
    let glucoseMgdl: [Double]
    let glucoseSamples: [EvalGlucoseSample]
    let extraISFMultiplier: Double
    let forecastOffsetMgdl: Double
    let perStepIsfMultByTime: [Date: Double]?
    let isfBoostActiveOnly: Bool
    let egpPhysicalDecomposition: Bool
    /// Full clipped dose history for the run, used ONLY to compute the oref
    /// weighted-TDD's 10-day average without needing a 240h input lookback
    /// (summing doses is cheap; inflating the input window's IOB/effects is not).
    /// Empty ⇒ adapter falls back to `input.doses` (the lookback slice).
    let tddDoses: [EvalInsulinDose]
    /// Full (un-windowed) dose history for building the oref pump-history JSON.
    /// oref's autosens computes deviations over 24h and each deviation's BGI needs
    /// IOB back to 24h+DIA, so `input.doses` (sliced to the insulin lookback, ~DIA)
    /// starves it and under-detects sensitivity. The adapter slices this to Trio's
    /// 24h `pumpHistoryLast1440Minutes` window. For the counterfactual candidate this
    /// MUST be the candidate's own dose history (not the real one). Empty ⇒ adapter
    /// falls back to `input.doses`.
    let orefPumpHistoryDoses: [EvalInsulinDose]

    init(
        t: Date,
        input: PredictionInput,
        config: EvalConfig,
        therapy: TherapyTimeline,
        glucoseMgdl: [Double],
        glucoseSamples: [EvalGlucoseSample],
        extraISFMultiplier: Double = 1.0,
        forecastOffsetMgdl: Double = 0.0,
        perStepIsfMultByTime: [Date: Double]? = nil,
        isfBoostActiveOnly: Bool = false,
        egpPhysicalDecomposition: Bool = false,
        tddDoses: [EvalInsulinDose] = [],
        orefPumpHistoryDoses: [EvalInsulinDose] = []
    ) {
        self.t = t
        self.input = input
        self.config = config
        self.therapy = therapy
        self.glucoseMgdl = glucoseMgdl
        self.glucoseSamples = glucoseSamples
        self.extraISFMultiplier = extraISFMultiplier
        self.forecastOffsetMgdl = forecastOffsetMgdl
        self.perStepIsfMultByTime = perStepIsfMultByTime
        self.isfBoostActiveOnly = isfBoostActiveOnly
        self.egpPhysicalDecomposition = egpPhysicalDecomposition
        self.tddDoses = tddDoses
        self.orefPumpHistoryDoses = orefPumpHistoryDoses
    }
}

struct EngineStepResult {
    let dose: Double
    let bolus: Double
    let tempRate: Double
    /// Loop-flavored prediction (forecast curves, IOB, COB, momentum/RC effects).
    let prediction: LoopPrediction<EvalCarbEntry>
    /// OpenAPS-only decision diagnostics (nil for Loop): why oref withholds dosing
    /// before a low — autosens sensitivity ratio + the predicted-minimum BG that
    /// gates SMB (minGuardBG/minPredBG vs threshold_setting).
    var autosensRatio: Double? = nil
    var minGuardBG: Double? = nil
    var minPredBG: Double? = nil
    var reason: String? = nil   // oref reason string (Dev/BGI/IOBpredBG/minPredBG diagnostics)
    /// Candidate's recommended MANUAL bolus at this step (full correction, clamped to maxBolus).
    var manualBolusRec: Double = 0
}

protocol DosingEngine: Sendable {
    func step(_ request: EngineStepRequest) -> EngineStepResult
}
