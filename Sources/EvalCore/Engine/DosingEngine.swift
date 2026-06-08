// DosingEngine.swift — pluggable dose-recommendation protocol.
//
// The simulator delegates each per-step "what should the algorithm do here?"
// decision to a `DosingEngine`. Today the only adapter is `LoopAdapter`
// (Loop Algorithm via the local LoopAlgorithm package). Hosting the
// OpenAPSSwift fork (sibling Swift package at ../OpenAPSSwift) is the next
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
        egpPhysicalDecomposition: Bool = false
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
}

protocol DosingEngine: Sendable {
    func step(_ request: EngineStepRequest) -> EngineStepResult
}
