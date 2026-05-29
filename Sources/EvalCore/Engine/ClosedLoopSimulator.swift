// ClosedLoopSimulator.swift — full closed-loop counterfactual simulation
//
// The bench's linearized counterfactual computes counter_BG by propagating
// candidate's Δdose (computed against actual past CGM) onto the actual CGM
// trace. That has a known weakness: candidate keeps making decisions against
// actual BG, not its own resulting counterfactual BG. For aggressive
// candidates (e.g. IRC), the drift compounds without self-correction.
//
// This file implements true closed-loop replay: at each step t, candidate's
// inputs are substituted to use:
//   - counter_glucose: actual_glucose with cumulative Δdose impact applied
//   - candidate_doses: actual_doses + virtual entries from prior Δdose decisions
//
// The candidate's prediction at t therefore sees its own resulting BG and
// its own accumulated dose history. Δdose at t reflects feedback-corrected
// behavior. Forward-impact propagation updates counter_glucose for future
// steps, and a virtual dose entry is added so future IOB calculations
// include the candidate's extra/reduced delivery.
//
// Sequential by nature; cannot reuse the parallelized runSweep. Slower
// (~10x) but accurate for absolute trajectory estimates.

import Foundation
import LoopAlgorithm

/// Output of a closed-loop simulation. Per-step trace of the candidate's
/// behavior with feedback, plus the resulting counter_glucose timeline.
public struct ClosedLoopSimResult: Codable, Sendable {
    public struct Step: Codable, Sendable {
        public let t: Date
        public let actualBG: Double      // actual CGM at this time
        public let counterBG: Double     // candidate's effective BG (counterfactual)
        public let baselineDose: Double  // baseline's recommendedDeltaU at this t
        public let candidateDose: Double // candidate's recommendedDeltaU (with feedback)
        public let deltaDose: Double     // candidateDose - baselineDose
        public let isf: Double           // ISF used at this t (mg/dL/U)
        // Decomposition of candidate's delivery this step (automatic-bolus strategy):
        public let candidateBolus: Double       // auto-bolus units this step
        public let candidateTempRate: Double    // temp basal rate set this step (U/hr)
        // Decision diagnostics — the forecast/IOB that drove the dose. Baseline =
        // sim Loop on REAL BG (directly comparable to field devicestatus eventualBG/IOB);
        // candidate = sim Loop on the counterfactual (counter) BG. NaN if not computed.
        public var baselineEventualBG: Double = .nan
        public var baselineIOB: Double = .nan
        public var baselineCOB: Double = .nan
        public var baselineMomentum: Double = .nan   // net momentum contribution to forecast (mg/dL)
        public var baselineRC: Double = .nan          // net retrospective-correction contribution (mg/dL)
        public var baselineDiscrepancy: Double = .nan // latest 30-min RC discrepancy (mg/dL); drives IRC accumulation
        public var candidateEventualBG: Double = .nan
        public var candidateIOB: Double = .nan
        public var candidateCOB: Double = .nan
    }
    public let steps: [Step]
    public let baselineLabel: String
    public let candidateLabel: String
    public let intervalStart: Date
    public let intervalEnd: Date
}

extension EvaluationEngine {

    /// Run a closed-loop simulation: baseline as a parallel reference sweep,
    /// candidate as a sequential per-step replay with glucose + dose-history
    /// feedback. Both use the same data source for actual past activity.
    public func simulateClosedLoop(
        data: PreloadedData,
        interval: DateInterval,
        baselineConfig: EvalConfig,
        candidateConfig: EvalConfig,
        baselineLabel: String = "Baseline",
        candidateLabel: String = "Candidate",
        isfMultiplierByStep: [Date: Double]? = nil,
        isfBoostActiveOnly: Bool = false,
        egpPhysicalDecomposition: Bool = false,
        isfBoostGateEventualMgdl: Double? = nil,
        isfBoostVetoIceRate: Double? = nil,
        outages: [Outage] = [],
        cgmStaleGuardSec: TimeInterval = 0,
        counterfactualMode: Bool = false,
        counterfactualBurnInSec: TimeInterval = 6 * 3600,
        excludeManualBoluses: Bool = false,
        suppressCarbs: Bool = false,
        counterRegOnsetMgdl: Double = 0,
        counterRegGain: Double = 0.2,
        counterRegMaxRate: Double = 6.0,
        inferSensitivity: Bool = false,
        inferSensitivityMax: Double = 2.0,
        inferSensitivityWindowSec: TimeInterval = 30 * 60,
        dumpNiePath: String? = nil,
        progress: (@Sendable (Double) -> Void)? = nil
    ) throws -> ClosedLoopSimResult {

        // 1. Set up mutable state.
        //
        // IMPORTANT: baseline and candidate must use the SAME code path so the
        // identity case (configs equal) gives Δdose = 0 at every step. Earlier
        // versions ran baseline through `runSweep` (precomputed-insulin path)
        // and candidate through an inline call (doses path); those two paths
        // are mathematically equivalent but numerically diverge, producing
        // non-zero Δdose at every step and compounding drift through the
        // feedback loop. Both sides now go through `Self.simStepDose(...)`
        // which uses one canonical doses-path generatePrediction call.
        let mgdlUnit = LoopUnit.milligramsPerDeciliter
        let insulinModel = data.therapyTimeline.insulinType.model
        let activityDuration = insulinModel.effectDuration

        // SUBSTRATE: the actual-BG trace the whole sim runs on. When
        // kalmanSmoothing is on (default), this is the RTS-smoothed CGM
        // resampled onto the 5-min sim grid (single missing samples
        // interpolated, ≥2-sample gaps left out). It is the basis for ICE, the
        // counter, Loop's decision-time input, and the outcome stats.
        //
        // NOTE (deliberate, see AGENTS.md "RTS substrate"): the smoother's RTS
        // backward pass uses FUTURE samples, so this is NOT decision-time-clean
        // — by design. We explore the algorithm in a low-noise "ground truth"
        // space; baseline and candidate share this identical substrate, so the
        // future information is the same on both sides and cancels in every
        // experiment-vs-sanity delta. Use --no-kalman for the raw substrate.
        let simGlucose: [EvalGlucoseSample] = candidateConfig.kalmanSmoothing
            ? Self.buildSmoothedGrid(raw: data.glucose,
                                     start: interval.start, end: interval.end,
                                     stepSec: candidateConfig.evalStep)
            : data.glucose

        // counter_glucose: starts as actual; modified as Δdose impacts accumulate.
        // We mutate values in place at sample indices, preserving original
        // timestamps and metadata.
        var counterGlucose = simGlucose
        var counterMgdl = simGlucose.map { $0.quantity.doubleValue(for: mgdlUnit) }
        // Baseline always reads from actual glucose; precomputed once for GBAF lookups.
        let baselineMgdl = simGlucose.map { $0.quantity.doubleValue(for: mgdlUnit) }


        // Virtual doses: candidate's accumulated extra/reduced deliveries.
        // Stored as bolus-type entries with volume = Δdose; insulin model
        // treats them like instantaneous deliveries at time t.
        var virtualDoses: [EvalInsulinDose] = []
        virtualDoses.reserveCapacity(1024)

        // Counterfactual mode state (only used if counterfactualMode == true).
        // counterfactualDoses replaces data.doses for the candidate's prediction
        // input — Loop sees only candidate's accumulated deliveries plus
        // pre-warmup real-pump seed + USER-INITIATED manual boluses from real
        // pump (preserved as pass-through user behavior; algorithm can't
        // predict these). Seeded with real-pump doses from
        // [evalStart - DIA, evalStart) so initial IOB at sim start matches
        // reality (otherwise candidate would start with 0 IOB).
        var counterfactualDoses: [EvalInsulinDose] = []
        counterfactualDoses.reserveCapacity(2048)
        // Per-step rasterized real-pump deliveries:
        //   - realAutoOnlyPerStep: AUTO-only deliveries (auto-boluses + basal
        //     entries). Used as deltaDose baseline so candidate's algorithm-
        //     vs-algorithm comparison is clean.
        //   - Manual boluses are passed through separately (added to
        //     counterfactualDoses as they occur, preserving user input).
        var realAutoOnlyPerStep: [Date: Double] = [:]
        // Manual boluses (user-initiated) sorted by startDate, for in-loop
        // pass-through into counterfactualDoses.
        var realManualBoluses: [EvalInsulinDose] = []
        var nextManualIdx = 0

        // Pre-scale sensitivity once per candidate config (timeline doesn't
        // depend on dose history).
        let scaledSensitivity = Self.applySensitivityScaling(
            data.therapyTimeline.sensitivity,
            globalMultiplier: candidateConfig.sensitivityMultiplier,
            hourlyMultipliers: candidateConfig.sensitivityHourlyMultipliers,
            timezone: candidateConfig.localTimezone
        )

        // PHYSIOLOGY sensitivity. In sensitivity-inference (fidelity) mode the
        // physiological insulin response is decoupled from the controller's ISF
        // belief: ICE and the counterfactual dose-effect run at the SCHEDULED
        // ISF (the body's baseline), and the inferred per-step multiplier m(t)
        // corrects it. The controller (generatePrediction) still uses the
        // candidate's `scaledSensitivity`. Outside inference mode this is just
        // `scaledSensitivity`, so all existing behavior is unchanged.
        let physiologySensitivity = inferSensitivity
            ? data.therapyTimeline.sensitivity
            : scaledSensitivity

        // 2. Sequential walk
        let evalStart = interval.start.addingTimeInterval(candidateConfig.evalWarmupHours * 3600)

        // Counterfactual setup: rasterize real pump (auto-only) per step,
        // collect manual boluses for pass-through, and seed pre-sim IOB +
        // burn-in. During the burn-in period (default 6h after evalStart),
        // the sim uses real-pump deliveries (deltaDose=0, no perturbation)
        // so candidate has a fully-realistic recent dose history when its
        // counterfactual decisions start to apply.
        let cfActiveStart = counterfactualMode
            ? evalStart.addingTimeInterval(counterfactualBurnInSec)
            : evalStart
        if counterfactualMode {
            let warmupStart = evalStart.addingTimeInterval(-activityDuration)
            // Seed with EVERYTHING from real pump up to cfActiveStart so
            // candidate's prediction at cfActiveStart sees a fully-real recent
            // history (pre-warmup + burn-in real pump deliveries).
            counterfactualDoses = data.doses.filter {
                $0.endDate > warmupStart && $0.startDate < cfActiveStart
            }
            // Rasterize only AUTO deliveries (auto boluses + basal entries) —
            // manual boluses are passed through as user actions and excluded
            // from the perturbation reference.
            let autoOnlyDoses = data.doses.filter { dose in
                !(dose.deliveryType != .basal && !dose.automatic)
            }
            realAutoOnlyPerStep = Self.rasterizeRealPumpPerStep(
                doses: autoOnlyDoses, start: cfActiveStart, end: interval.end,
                stepSec: candidateConfig.evalStep)
            // Collect user-initiated manual boluses that occur AFTER burn-in
            // ends, sorted by startDate, for pass-through into
            // counterfactualDoses as the sim progresses.
            //
            // excludeManualBoluses: drop them entirely so the sim's Loop owns ALL
            // dosing (meals covered only by its own COB-driven auto-bolusing).
            // Answers "how would the fully-automated system perform with NO user
            // intervention?". Burn-in seed (pre-cfActiveStart) still keeps real
            // manual boluses for IOB continuity; only post-burn-in ones are removed.
            realManualBoluses = excludeManualBoluses ? [] : data.doses
                .filter { dose in
                    dose.deliveryType != .basal && !dose.automatic
                    && dose.startDate >= cfActiveStart && dose.startDate < interval.end
                }
                .sorted { $0.startDate < $1.startDate }
        }

        // Pre-compute the REAL-BG-DERIVED Insulin Counteraction Effect (ICE)
        // timeline. In physiological-counterfactual mode this carries the
        // user's non-insulin BG dynamics (carb absorption, exercise, dawn
        // phenomenon, sensor surprise) into the counter trajectory. The
        // counterfactual is: "the user's real-day physiology with different
        // insulin decisions". Insulin response differs (computed from
        // candidate doses each step); everything else is borrowed from reality.
        let realICE: [GlucoseEffectVelocity]
        // Per-grid-step PHYSICAL active-insulin effect of the REAL doses (EGP
        // zeroed), for the sensitivity-inference application. Stays 0 outside
        // inference mode.
        var realPhysDelta = [Double](repeating: 0, count: simGlucose.count)
        if counterfactualMode {
            let iceStart = Date()
            FileHandle.standardError.write(Data("Sim setup: doses=\(data.doses.count) glucose=\(simGlucose.count)\n".utf8))
            // Filter doses to those covered by the sensitivity schedule —
            // LoopAlgorithm.glucoseEffects preconditions on closestPrior(...)
            // returning a non-nil entry for each dose.startDate.
            let firstSensDate = scaledSensitivity.first?.startDate ?? .distantPast
            let lastSensDate = scaledSensitivity.last?.endDate ?? .distantFuture
            let safeDataDoses = data.doses.filter {
                $0.startDate >= firstSensDate && $0.startDate <= lastSensDate
            }
            // useMidAbsorptionISF: true switches to the PARALLELIZED
            // glucoseEffectsMidAbsorptionISF (DispatchQueue.concurrentPerform
            // across cores). Single-threaded glucoseEffects took 17 minutes for
            // 60 days; parallel + release build → ~30s. Mid-absorption ISF is
            // also what Loop's default config uses.
            let precomp = PrecomputedInsulinInput.build(
                doses: safeDataDoses,
                basal: data.therapyTimeline.basal,
                sensitivity: physiologySensitivity,
                effectsFrom: simGlucose.first?.startDate.addingTimeInterval(-insulinModel.effectDuration),
                effectsTo: simGlucose.last?.startDate,
                useMidAbsorptionISF: true
            )
            let insulinEffects = precomp.insulinEffects ?? []
            FileHandle.standardError.write(Data("PrecomputedInsulinInput.build done in \(Int(Date().timeIntervalSince(iceStart) * 1000))ms (effects entries=\(insulinEffects.count))\n".utf8))
            realICE = simGlucose.counteractionEffects(to: insulinEffects)
            FileHandle.standardError.write(Data("ICE done (entries=\(realICE.count))\n".utf8))
            if inferSensitivity {
                let physStart = Date()
                for j in 1..<simGlucose.count {
                    realPhysDelta[j] = Self.physicalActiveEffectDelta(
                        doses: safeDataDoses, basal: data.therapyTimeline.basal,
                        sensitivity: physiologySensitivity,
                        from: simGlucose[j - 1].startDate, to: simGlucose[j].startDate,
                        insulinModel: insulinModel)
                }
                FileHandle.standardError.write(Data("realPhysActive precompute done in \(Int(Date().timeIntervalSince(physStart) * 1000))ms\n".utf8))
            }
        } else {
            realICE = []
        }

        // SENSITIVITY-INFERENCE m(t) timeline (fidelity mode). For each grid
        // sample, over a trailing window measure how much BG actually moved
        // (`bgDeltaWindow`) vs how much the scheduled-ISF insulin model
        // explains (`insReal = bgDeltaWindow - iceWindow`). If BG is still
        // DROPPING after subtracting modeled insulin (iceWindow < 0), the
        // insulin must have been more effective than scheduled — scale ISF up
        // by m = bgDelta/insReal, JUST enough to zero that negative residual
        // (never past it, so we never manufacture a spurious rise). Capped at
        // `inferSensitivityMax` (the "can't subtract more insulin than is
        // physically present" ceiling): when little insulin is active the cap
        // binds and the unexplained drop stays as additive ICE — the
        // exercise / low-IOB case, correctly left as non-insulin. Positive
        // residuals (carbs/EGP winning) are untouched (m = 1).
        var mByIndex = [Double](repeating: 1.0, count: simGlucose.count)
        if counterfactualMode && inferSensitivity {
            let velEps = 1.0  // mg/dL of modeled insulin over the window; below this we can't identify m
            var kStart = 0
            for j in 0..<simGlucose.count {
                let tEnd = simGlucose[j].startDate
                let tStart = tEnd.addingTimeInterval(-inferSensitivityWindowSec)
                while kStart + 1 < simGlucose.count && simGlucose[kStart + 1].startDate <= tStart { kStart += 1 }
                if simGlucose[kStart].startDate > tStart || simGlucose[kStart].startDate >= tEnd { continue }
                let bgDeltaWindow = simGlucose[j].quantity.doubleValue(for: mgdlUnit)
                    - simGlucose[kStart].quantity.doubleValue(for: mgdlUnit)
                let iceWindow = Self.integrateICE(realICE, from: simGlucose[kStart].startDate, to: tEnd)
                if iceWindow < 0 {
                    let insReal = bgDeltaWindow - iceWindow  // modeled insulin effect (negative)
                    if insReal < -velEps {
                        mByIndex[j] = min(bgDeltaWindow / insReal, inferSensitivityMax)
                    }
                }
            }
            let active = mByIndex.filter { $0 > 1.0 }
            let meanActive = active.isEmpty ? 0 : active.reduce(0, +) / Double(active.count)
            FileHandle.standardError.write(Data("sensitivity-inference: m>1 at \(active.count)/\(mByIndex.count) steps (\(String(format: "%.1f", 100*Double(active.count)/Double(max(1,mByIndex.count))))%), mean m|active=\(String(format: "%.3f", meanActive)), max m=\(String(format: "%.3f", mByIndex.max() ?? 1))\n".utf8))
            // DUMP per-step NIE (de-insulinized real BG change = realBGdelta −
            // m·real_physical_insulin) + m + substrate BG, for the offline
            // perfect-foresight dosing oracle. NIE is candidate-INDEPENDENT
            // (property of the real day), so this dump is valid from any
            // fidelity run. NIE_i covers [i-1, i].
            if let dumpPath = dumpNiePath {
                let isoFmt = ISO8601DateFormatter(); isoFmt.formatOptions = [.withInternetDateTime]
                var csv = "t,nie,m,bg\n"
                csv.reserveCapacity(simGlucose.count * 48)
                for i in 1..<simGlucose.count {
                    let bgPrev = simGlucose[i - 1].quantity.doubleValue(for: mgdlUnit)
                    let bgNow = simGlucose[i].quantity.doubleValue(for: mgdlUnit)
                    let nie = (bgNow - bgPrev) - mByIndex[i] * realPhysDelta[i]
                    csv += "\(isoFmt.string(from: simGlucose[i].startDate)),\(nie),\(mByIndex[i]),\(bgNow)\n"
                }
                try? csv.write(toFile: dumpPath, atomically: true, encoding: .utf8)
                FileHandle.standardError.write(Data("dumped NIE/m → \(dumpPath) (\(simGlucose.count - 1) rows)\n".utf8))
            }
        }

        // Pre-compute expected step count for progress reporting
        let totalDuration = max(0, interval.end.timeIntervalSince(evalStart))
        let totalSteps = max(1, Int(totalDuration / candidateConfig.evalStep) + 1)
        FileHandle.standardError.write(Data("sim setup done. totalSteps=\(totalSteps), realICE.count=\(realICE.count). entering main loop.\n".utf8))

        var steps: [ClosedLoopSimResult.Step] = []
        steps.reserveCapacity(totalSteps)

        // Hoist out of per-step loop: O(N) scan over 14k+ entries done once,
        // not 17k times. True if ANY map value departs from 1.0.
        let mapHasAnyBoost: Bool = isfMultiplierByStep.map {
            $0.values.contains(where: { abs($0 - 1.0) > 1e-9 })
        } ?? false

        var t = evalStart
        var stepIdx = 0

        while t <= interval.end {
            if let progress, totalSteps > 1 {
                progress(min(Double(stepIdx) / Double(totalSteps - 1), 1.0))
            }

            // ----- CGM-CYCLE GATING -----
            // Loop's loop is CGM-triggered: with no fresh CGM there is no
            // cycle — no forecast, no dose decision. When the staleness guard
            // is enabled, skip the entire step (no baseline/candidate dose, no
            // prediction, no recorded point) once we are more than the guard
            // interval away from ANY real CGM sample. This permits a single
            // missing sample to be "paved over" (the neighbouring real sample
            // is within the guard) and the post-gap resumption step to run
            // (the resumed sample is within the guard), but stops the sim from
            // continuing to generate forecast points deep inside a CGM outage.
            //
            // Scheduled basal during the gap contributes zero NET insulin
            // (delivered == scheduled ⇒ netBasalUnits 0), so nothing need be
            // added for IOB continuity. Manual boluses are physical events and
            // are still passed through so the candidate's dose history (and the
            // post-gap counter advance) account for them.
            if cgmStaleGuardSec > 0 {
                let nextIdx = EvaluationEngine.bestGlucoseIndex(at: t, in: simGlucose)
                let prevIdx = Self.latestGlucoseIndex(at: t, in: simGlucose)
                let dNext = abs(simGlucose[nextIdx].startDate.timeIntervalSince(t))
                let dPrev = abs(t.timeIntervalSince(simGlucose[prevIdx].startDate))
                if min(dNext, dPrev) > cgmStaleGuardSec {
                    if counterfactualMode && t >= cfActiveStart {
                        let stepEnd = t.addingTimeInterval(candidateConfig.evalStep)
                        while nextManualIdx < realManualBoluses.count {
                            let mb = realManualBoluses[nextManualIdx]
                            if mb.startDate >= stepEnd { break }
                            if mb.startDate >= t { counterfactualDoses.append(mb) }
                            nextManualIdx += 1
                        }
                    }
                    t = t.addingTimeInterval(candidateConfig.evalStep)
                    stepIdx += 1
                    continue
                }
            }

            // ----- BASELINE step: actual glucose, actual doses, baselineConfig.
            let baselineBuilder = InputWindowBuilder(
                glucose: simGlucose,
                doses: data.doses,
                carbs: suppressCarbs ? [] : data.carbs,
                therapyTimeline: data.therapyTimeline,
                config: baselineConfig
            )
            var baselineDose: Double
            var baselineEventualBG = Double.nan
            var baselineIOB = Double.nan
            var baselineCOB = Double.nan
            var baselineMomentum = Double.nan
            var baselineRC = Double.nan
            var baselineDiscrepancy = Double.nan
            if let baselineInput = baselineBuilder.buildInput(at: t) {
                let br = Self.simStepDose(
                    t: t,
                    input: baselineInput,
                    config: baselineConfig,
                    therapy: data.therapyTimeline,
                    glucoseMgdl: baselineMgdl,
                    glucoseSamples: simGlucose
                )
                baselineDose = br.dose
                baselineEventualBG = br.prediction.glucose.last?.quantity.doubleValue(for: mgdlUnit) ?? .nan
                baselineIOB = br.prediction.activeInsulin ?? .nan
                baselineCOB = br.prediction.activeCarbs ?? .nan
                func netMgdl(_ arr: [GlucoseEffect]) -> Double {
                    // Empty effect array = the effect was gated off / not produced ⇒ 0 contribution.
                    guard let f = arr.first, let l = arr.last else { return 0.0 }
                    return l.quantity.doubleValue(for: mgdlUnit) - f.quantity.doubleValue(for: mgdlUnit)
                }
                baselineMomentum = netMgdl(br.prediction.effects.momentum)
                baselineRC = netMgdl(br.prediction.effects.retrospectiveCorrection)
                baselineDiscrepancy = br.prediction.effects.retrospectiveGlucoseDiscrepancies.last?.quantity.doubleValue(for: mgdlUnit) ?? 0.0
            } else {
                baselineDose = 0
            }

            // ----- CANDIDATE step: counter glucose, doses, candidateConfig.
            // Normal mode: combined = real pump + virtual marginal deltas.
            // Counterfactual mode active (t >= cfActiveStart): candidate sees
            //   ONLY its own delivery history (real-pump warmup+burn-in seed
            //   + counterfactual deliveries so far).
            // Counterfactual burn-in (t < cfActiveStart): candidate sees real
            //   pump deliveries (counterfactualDoses already seeded with all
            //   real pump up to cfActiveStart, so it's equivalent).
            let cfActive = counterfactualMode && t >= cfActiveStart
            let combinedDoses: [EvalInsulinDose]
            if counterfactualMode {
                combinedDoses = counterfactualDoses
            } else {
                combinedDoses = EvaluationEngine.mergeSorted(data.doses, virtualDoses)
            }

            // Snapshot candidate glucose from counter_mgdl. Unchanged samples reuse
            // the original EvalGlucoseSample object; touched indices get a new one.
            let counterSamples = zip(counterGlucose, counterMgdl).map { (s, v) -> EvalGlucoseSample in
                if v == s.quantity.doubleValue(for: mgdlUnit) { return s }
                return EvalGlucoseSample(
                    startDate: s.startDate,
                    quantity: LoopQuantity(unit: mgdlUnit, doubleValue: v),
                    provenanceIdentifier: s.provenanceIdentifier,
                    isDisplayOnly: s.isDisplayOnly,
                    wasUserEntered: s.wasUserEntered,
                    condition: s.condition,
                    trendRate: s.trendRate
                )
            }
            let candidateBuilder = InputWindowBuilder(
                glucose: counterSamples,
                doses: combinedDoses,
                carbs: suppressCarbs ? [] : data.carbs,
                therapyTimeline: data.therapyTimeline,
                config: candidateConfig
            )
            guard let candidateInput = candidateBuilder.buildInput(at: t) else {
                t = t.addingTimeInterval(candidateConfig.evalStep)
                stepIdx += 1
                continue
            }
            // ----- CANDIDATE step: candidate's Loop sees the per-step ISF
            // schedule (if any) and emits a dose.
            var candidateDose: Double
            var candidateBolus: Double
            var candidateTempRate: Double
            var candidateEventualBG = Double.nan
            var candidateIOB = Double.nan
            var candidateCOB = Double.nan
            do {
                let csvIsfMult: Double
                if let m = isfMultiplierByStep, !m.isEmpty {
                    let rounded = Date(timeIntervalSince1970:
                        (t.timeIntervalSince1970 / candidateConfig.evalStep).rounded() * candidateConfig.evalStep)
                    csvIsfMult = m[rounded] ?? 1.0
                } else {
                    csvIsfMult = 1.0
                }
                let perStepMapForLoop = isfMultiplierByStep
                let csvIsfEnabled = abs(csvIsfMult - 1.0) > 1e-9 || mapHasAnyBoost
                func doStep(_ map: [Date: Double]?)
                    -> (dose: Double, bolus: Double, tempRate: Double, prediction: LoopPrediction<EvalCarbEntry>) {
                    Self.simStepDose(
                        t: t, input: candidateInput, config: candidateConfig,
                        therapy: data.therapyTimeline, glucoseMgdl: counterMgdl,
                        glucoseSamples: counterGlucose,
                        perStepIsfMultByTime: map,
                        isfBoostActiveOnly: isfBoostActiveOnly,
                        egpPhysicalDecomposition: egpPhysicalDecomposition)
                }
                // Forecast-gated boost (lows-protection): a boost (mult<1) is only
                // applied if the candidate's UNBOOSTED forecast PEAK (highest BG
                // expected over the horizon = real headroom) exceeds the gate. Fires
                // when BG is high OR climbing (TIR-useful, incl. unannounced-meal
                // rises); suppresses only the comfortable-and-falling case where the
                // boost would float into a developing low. NB: gating on EVENTUAL BG
                // is wrong — Loop drives eventual to target, so it rarely clears the
                // gate and over-suppresses. The damp direction (mult>=1) is always kept.
                // Primary lows-protection: an INTRADAY ICE veto. Suppress the boost
                // when the recent insulin-counteraction effect is sufficiently negative
                // — non-insulin drivers are currently pulling BG down (a sensitive
                // moment, ICE<0 ⟺ high local-ISF), so adding insulin would float into a
                // developing drop. Forecast-peak gate kept as a secondary option.
                let result: (dose: Double, bolus: Double, tempRate: Double, prediction: LoopPrediction<EvalCarbEntry>)
                let wantBoost = csvIsfMult < 1.0 - 1e-9
                if wantBoost, let iceR = isfBoostVetoIceRate {
                    let iceRate = Self.integrateICE(realICE, from: t.addingTimeInterval(-1800), to: t) / 30.0
                    result = (iceRate < -iceR) ? doStep(nil) : doStep(perStepMapForLoop)
                } else if wantBoost, let gate = isfBoostGateEventualMgdl {
                    let unboosted = doStep(nil)
                    let peak = unboosted.prediction.glucose.map {
                        $0.quantity.doubleValue(for: mgdlUnit)
                    }.max() ?? .nan
                    result = (peak.isFinite && peak > gate) ? doStep(perStepMapForLoop) : unboosted
                } else {
                    result = doStep(csvIsfEnabled ? perStepMapForLoop : nil)
                }
                candidateDose = result.dose
                candidateBolus = result.bolus
                candidateTempRate = result.tempRate
                candidateEventualBG = result.prediction.glucose.last?.quantity.doubleValue(for: mgdlUnit) ?? .nan
                candidateIOB = result.prediction.activeInsulin ?? .nan
                candidateCOB = result.prediction.activeCarbs ?? .nan
            }

            // ----- DELIVERABILITY / DATA-AVAILABILITY CLAMPS -----
            // Two structurally different conditions can override the sim's
            // dose decision at step t. Pump outage takes precedence over a
            // CGM gap (if the pump is physically off, CGM staleness is moot).
            let inOutage = !outages.isEmpty && outages.containing(t) != nil

            // CGM staleness: Loop refuses to issue a NEW dose when the latest
            // glucose is older than its inputDataRecencyInterval (15min,
            // LoopAlgorithm.swift). The sim's per-step dose path
            // (simStepDose → generatePrediction) bypasses that guard, so it
            // would otherwise keep dosing on stale data. When stale, Loop
            // makes no adjustment and scheduled basal continues delivering —
            // distinct from a pump outage where delivery stops entirely.
            var cgmStale = false
            if cgmStaleGuardSec > 0 && !inOutage {
                let idx = Self.latestGlucoseIndex(at: t, in: counterGlucose)
                let latestT = counterGlucose[idx].startDate
                if latestT <= t {
                    cgmStale = t.timeIntervalSince(latestT) > cgmStaleGuardSec
                }
            }

            if inOutage {
                // Physical pump outage: absolute delivery = 0. Real Loop's
                // recorded auto-deliveries during outages are already 0 (Loop
                // wrote 0 U/hr temps after pump failure), so real-pump
                // quantities (realPumpAutoAtStep, the ICE pipeline) need no
                // adjustment — only the simulator's own decisions do.
                let schedRate = data.therapyTimeline.basal.first(where: {
                    $0.startDate <= t && $0.endDate > t
                })?.value ?? data.therapyTimeline.basal.closestPrior(to: t)?.value ?? 0
                let schedStepU = schedRate * candidateConfig.evalStep / 3600.0
                // absolute delivery = scheduled_step + dose; want absolute = 0.
                candidateDose = -schedStepU
                baselineDose = -schedStepU
                candidateBolus = 0
                candidateTempRate = 0
            } else if cgmStale {
                // CGM gap: no NEW dose adjustment, scheduled basal continues.
                // dose ADJUSTMENT (delta over scheduled) = 0, so absolute
                // delivery = scheduled. candidateTempRate reports the
                // scheduled rate to reflect "running at schedule".
                let schedRate = data.therapyTimeline.basal.first(where: {
                    $0.startDate <= t && $0.endDate > t
                })?.value ?? data.therapyTimeline.basal.closestPrior(to: t)?.value ?? 0
                candidateDose = 0
                baselineDose = 0
                candidateBolus = 0
                candidateTempRate = schedRate
            }

            // deltaDose semantics depend on mode:
            //   - Normal: candidate's dose minus sim-Loop-alone's dose (rule's
            //     marginal effect on top of real-pump-history)
            //   - Counterfactual: candidate's absolute delivery minus real
            //     pump's absolute delivery for this step (rule REPLACES real
            //     pump; perturbs counter_BG accordingly)
            let deltaDose: Double
            if cfActive {
                // Scheduled basal at t (U over this step)
                let schedBasalRate = data.therapyTimeline.basal.first(where: {
                    $0.startDate <= t && $0.endDate > t
                })?.value ?? data.therapyTimeline.basal.closestPrior(to: t)?.value ?? 0
                let schedDeliveryThisStep = schedBasalRate * candidateConfig.evalStep / 3600.0
                let candidateAbsoluteDelivery = schedDeliveryThisStep + candidateDose
                // Use AUTO-ONLY real pump as the baseline. Manual boluses are
                // passed through (preserved in candidate's dose history) so
                // they cancel out and don't perturb counter_BG.
                let realPumpAutoAtStep = realAutoOnlyPerStep[t] ?? 0
                deltaDose = candidateAbsoluteDelivery - realPumpAutoAtStep
            } else if counterfactualMode {
                // Burn-in: no perturbation (counter = actual_BG during burn-in)
                deltaDose = 0
            } else {
                deltaDose = candidateDose - baselineDose
            }

            // ISF at this time (in mg/dL/U convention; stored as mg/dL unit per codebase quirk).
            let isfQty = scaledSensitivity.first(where: { $0.startDate <= t && $0.endDate > t })?.value
                ?? scaledSensitivity.closestPrior(to: t)?.value
            let isf = isfQty?.doubleValue(for: mgdlUnit) ?? 0

            // Apply Δdose impact to FUTURE counter_mgdl entries.
            //
            // Non-CF mode (rule evaluation): uses the legacy linear-PD
            // perturbation — counter = actual + small Δ × ISF × PD. Correct
            // for small per-step deltas; documented in [feedback_sim_linear_pd_limit].
            //
            // CF mode: handled separately below via PHYSIOLOGICAL ADVANCE
            // (counter steps forward = insulin effect from candidate doses +
            // observed ICE from actual BG). The Δ-perturbation path is
            // skipped in CF mode because the counter trajectory is no longer
            // a perturbation of actual — it's a fully integrated independent
            // simulation. (Fixed 2026-05-18.)
            if deltaDose != 0 && isf > 0 && !cfActive {
                for i in 0..<counterGlucose.count {
                    let futureT = counterGlucose[i].startDate
                    if futureT <= t { continue }
                    let τ = futureT.timeIntervalSince(t)
                    let pd: Double
                    if τ > activityDuration {
                        pd = 1.0
                    } else {
                        pd = max(0.0, min(1.0, 1.0 - insulinModel.percentEffectRemaining(at: τ)))
                    }
                    counterMgdl[i] -= deltaDose * isf * pd
                }
                // Append virtual dose entry. Treat Δdose as an instantaneous bolus
                // at time t. This makes IOB calculations on subsequent steps
                // include the candidate's extra (or reduced) delivery.
                virtualDoses.append(EvalInsulinDose(
                    deliveryType: .bolus,
                    startDate: t,
                    endDate: t,
                    volume: deltaDose,
                    insulinType: data.therapyTimeline.insulinType,
                    automatic: true
                ))
            }
            // Counterfactual mode (post-burn-in only): append candidate's full
            // absolute delivery for this step + pass-through any user manual
            // boluses that occurred in [t, t + stepSec). This builds the
            // candidate-only dose history that future prediction inputs need
            // so Loop sees both its own decisions AND user-input manual boluses.
            // During burn-in, counterfactualDoses was pre-seeded with real
            // pump deliveries up to cfActiveStart, so no per-step append needed.
            if cfActive {
                let schedBasalRate = data.therapyTimeline.basal.first(where: {
                    $0.startDate <= t && $0.endDate > t
                })?.value ?? data.therapyTimeline.basal.closestPrior(to: t)?.value ?? 0
                let schedDeliveryThisStep = schedBasalRate * candidateConfig.evalStep / 3600.0
                let candidateAbsoluteDelivery = schedDeliveryThisStep + candidateDose
                // Record as a TEMP BASAL segment covering this step, NOT a bolus.
                // LoopAlgorithm's IOB pipeline computes `netBasalUnits = volume
                // - scheduledRate × duration` for basal segments. Recording each
                // step as a .bolus would inflate IOB by the scheduled-basal
                // contribution that should be neutral (a 6h DIA pumping
                // 0.7 U/hr scheduled basal would accumulate ~2 U of spurious
                // "phantom IOB" — sim Loop then forecasts BG dropping and
                // suspends inappropriately). Bug found 2026-05-18.
                counterfactualDoses.append(EvalInsulinDose(
                    deliveryType: .basal,
                    startDate: t,
                    endDate: t.addingTimeInterval(candidateConfig.evalStep),
                    volume: candidateAbsoluteDelivery,
                    insulinType: data.therapyTimeline.insulinType,
                    automatic: true
                ))
                // Pass through any user-initiated manual boluses falling in
                // [t, t + stepSec). Preserves user behavior on top of the
                // candidate's algorithmic decisions.
                let stepEnd = t.addingTimeInterval(candidateConfig.evalStep)
                while nextManualIdx < realManualBoluses.count {
                    let mb = realManualBoluses[nextManualIdx]
                    if mb.startDate >= stepEnd { break }
                    if mb.startDate >= t {
                        counterfactualDoses.append(mb)
                    }
                    nextManualIdx += 1
                }

                // PHYSIOLOGICAL ADVANCE — step counter_BG forward to whatever
                // CGM samples fall in (t, t + stepSec]. counter_BG advance =
                //   insulin effect over [prev, next] from candidate dose history
                //   + ICE over [prev, next] from real-BG-derived timeline.
                // Per-step insulinEffectDelta uses binary search to slice only
                // the doses whose effect window overlaps the target interval —
                // bounded to ~70 doses (6h DIA × 1 dose per 5-min step + a few
                // historical), so each call is fast.
                var advIdx = 0
                while advIdx < counterGlucose.count && counterGlucose[advIdx].startDate <= t {
                    advIdx += 1
                }
                while advIdx < counterGlucose.count && counterGlucose[advIdx].startDate <= stepEnd {
                    let prevIdx = advIdx > 0 ? advIdx - 1 : advIdx
                    let prevT = counterGlucose[prevIdx].startDate
                    let nextT = counterGlucose[advIdx].startDate
                    let iceDelta = Self.integrateICE(realICE, from: prevT, to: nextT)
                    // Counter-regulation: as counter_BG falls below the onset
                    // threshold the body defends with surging hepatic glucose
                    // output (glucagon/epinephrine). Model it as a positive BG
                    // velocity that ramps with depth below onset, capped. The
                    // real ICE already carries counter-reg at the *real* BG
                    // level; this adds the EXTRA defense the counter's lower
                    // level would trigger — fires ~only where counter has
                    // diverged below the real range, so double-counting in the
                    // tracking regime is negligible (term is 0 above onset).
                    var crDelta = 0.0
                    if counterRegOnsetMgdl > 0 {
                        let below = counterRegOnsetMgdl - counterMgdl[prevIdx]
                        if below > 0 {
                            let rate = min(counterRegGain * below, counterRegMaxRate)
                            crDelta = rate * (nextT.timeIntervalSince(prevT) / 60.0)
                        }
                    }
                    let stepDelta: Double
                    if inferSensitivity {
                        // PHYSICAL / EGP-separated application. realBGdelta
                        // carries ALL non-insulin physiology — including EGP —
                        // unscaled. Only the PHYSICAL active-insulin delta
                        // between candidate and real doses is scaled by the
                        // inferred local sensitivity m. EGP is never magnified
                        // by m (it isn't in the physical term), so a candidate
                        // that suspends into sub-basal does NOT inherit a
                        // magnified "negative IOB raises BG" artifact — it just
                        // removes m × (the cut) of lowering and lets the real,
                        // unscaled EGP carry BG back up. Identity: candidate
                        // doses == real ⇒ candPhys == realPhysDelta ⇒ counter
                        // reproduces the substrate.
                        let realBGdelta = counterGlucose[advIdx].quantity.doubleValue(for: mgdlUnit)
                            - counterGlucose[prevIdx].quantity.doubleValue(for: mgdlUnit)
                        let candPhys = Self.physicalActiveEffectDelta(
                            doses: counterfactualDoses,
                            basal: data.therapyTimeline.basal,
                            sensitivity: physiologySensitivity,
                            from: prevT, to: nextT,
                            insulinModel: insulinModel)
                        let m = mByIndex[advIdx]
                        stepDelta = realBGdelta + m * (candPhys - realPhysDelta[advIdx])
                    } else {
                        let insulinDelta = Self.insulinEffectDelta(
                            doses: counterfactualDoses,
                            basal: data.therapyTimeline.basal,
                            sensitivity: physiologySensitivity,
                            from: prevT, to: nextT,
                            insulinModel: insulinModel)
                        stepDelta = insulinDelta + iceDelta
                    }
                    counterMgdl[advIdx] = counterMgdl[prevIdx] + stepDelta + crDelta
                    advIdx += 1
                }
            }

            // Record step. Use the latest-CGM-sample-at-or-before-t — the
            // counter perturbation loop only updates entries inside
            // (t_prev_step, t_step], so the *next-future* sample may not have
            // been advanced yet during a CGM gap and still holds its original
            // (unperturbed) actual_BG. The past sample has had all applicable
            // perturbations applied. This avoids spurious counter_BG spikes
            // at the step before a CGM gap closes. For the very first step
            // (no past sample) fall back to the first available sample.
            let actualLookupIdx = Self.latestGlucoseIndex(at: t, in: simGlucose)
            let counterLookupIdx = Self.latestGlucoseIndex(at: t, in: counterGlucose)
            let actualMgdl = simGlucose[actualLookupIdx].quantity.doubleValue(for: mgdlUnit)
            let counterMgdlAtT = counterMgdl[counterLookupIdx]
            steps.append(ClosedLoopSimResult.Step(
                t: t,
                actualBG: actualMgdl,
                counterBG: counterMgdlAtT,
                baselineDose: baselineDose,
                candidateDose: candidateDose,
                deltaDose: deltaDose,
                isf: isf,
                candidateBolus: candidateBolus,
                candidateTempRate: candidateTempRate,
                baselineEventualBG: baselineEventualBG,
                baselineIOB: baselineIOB,
                baselineCOB: baselineCOB,
                baselineMomentum: baselineMomentum,
                baselineRC: baselineRC,
                baselineDiscrepancy: baselineDiscrepancy,
                candidateEventualBG: candidateEventualBG,
                candidateIOB: candidateIOB,
                candidateCOB: candidateCOB
            ))

            t = t.addingTimeInterval(candidateConfig.evalStep)
            stepIdx += 1
        }

        progress?(1.0)

        return ClosedLoopSimResult(
            steps: steps,
            baselineLabel: baselineLabel,
            candidateLabel: candidateLabel,
            intervalStart: evalStart,
            intervalEnd: interval.end
        )
    }

    /// Decompose the prediction at fixed lookahead horizons into its component
    /// Rasterize real-pump deliveries (boluses + temp basals) onto the
    /// 5-min step grid. Each step's value is the total U delivered in
    /// [step_t, step_t + stepSec). Boluses count as instant at startDate;
    /// basal entries spread their volume linearly across their duration.
    /// Used by counterfactual mode to know what real pump delivered at
    /// each step so the candidate's marginal effect can be computed.
    // ── Physiological counterfactual helpers ────────────────────────────────

    /// Build the RTS-smoothed actual-BG trace resampled onto the simulation grid.
    ///
    /// Runs the Kalman + RTS backward smoother on the raw CGM, then samples the
    /// smoothed estimate at each grid time (`start + k*stepSec`). A grid point is
    /// emitted only if it lies within a real-CGM gap of at most `maxMissing`
    /// samples (the bracketing real samples are ≤ (maxMissing+1) steps apart);
    /// larger gaps are omitted so the stale-guard / disruption-exclusion handle
    /// them, and no extrapolation occurs before the first / after the last
    /// sample. The RTS pass uses future samples by design (see the SUBSTRATE
    /// note in simulateClosedLoop).
    fileprivate static func buildSmoothedGrid(
        raw: [EvalGlucoseSample],
        start: Date,
        end: Date,
        stepSec: TimeInterval,
        maxMissing: Int = 1
    ) -> [EvalGlucoseSample] {
        guard raw.count >= 2, stepSec > 0 else { return raw }
        let unit = LoopUnit.milligramsPerDeciliter
        let smoothed = KalmanSmoother().smooth(samples: raw.sorted { $0.startDate < $1.startDate })
        let times = smoothed.map { $0.startDate.timeIntervalSince1970 }
        let vals  = smoothed.map { $0.quantity.doubleValue(for: unit) }
        let maxGap = Double(maxMissing + 1) * stepSec + 60.0   // ≤maxMissing missing ⇒ ≤(m+1) steps + slack
        let eps = 1e-6
        var out: [EvalGlucoseSample] = []
        out.reserveCapacity(Int((end.timeIntervalSince(start)) / stepSec) + 2)
        func emit(_ tg: Double, _ bg: Double) {
            out.append(EvalGlucoseSample(
                startDate: Date(timeIntervalSince1970: tg),
                quantity: .init(unit: unit, doubleValue: bg),
                provenanceIdentifier: "rts-grid"))
        }
        var j = 0
        var tg = start.timeIntervalSince1970
        let endSec = end.timeIntervalSince1970
        while tg <= endSec + eps {
            while j + 1 < times.count && times[j + 1] <= tg { j += 1 }
            if times[j] <= tg + eps {
                if j + 1 < times.count {
                    let pT = times[j], nT = times[j + 1]
                    if (nT - pT) <= maxGap {            // ≤1 missing sample between brackets
                        let frac = (nT - pT) > eps ? (tg - pT) / (nT - pT) : 0.0
                        emit(tg, vals[j] + frac * (vals[j + 1] - vals[j]))
                    }                                   // else: gap too large → skip
                } else if abs(times[j] - tg) <= stepSec * 0.5 {
                    emit(tg, vals[j])                   // last sample, grid point coincides
                }
            }                                           // else: before first sample → skip
            tg += stepSec
        }
        return out.isEmpty ? raw : out
    }

    /// Pre-compute the real-BG-derived Insulin Counteraction Effect timeline.
    /// ICE is observed BG slope minus modelled insulin slope. It captures all
    /// non-insulin BG dynamics (carb absorption, exercise, dawn, sensor noise).
    /// Returns velocities in mg/dL/sec, one per CGM-sample interval.
    fileprivate static func computeRealICE(
        glucose: [EvalGlucoseSample],
        doses: [EvalInsulinDose],
        basal: [AbsoluteScheduleValue<Double>],
        sensitivity: [AbsoluteScheduleValue<LoopQuantity>],
        insulinModel: InsulinModel
    ) -> [GlucoseEffectVelocity] {
        guard let firstGlucose = glucose.first, let lastGlucose = glucose.last else { return [] }
        guard let firstSens = sensitivity.first, let lastSens = sensitivity.last else { return [] }
        // Filter real doses to the relevant window plus lookback AND to the
        // sensitivity schedule's coverage (glucoseEffects preconditions on it).
        let lookbackStart = firstGlucose.startDate.addingTimeInterval(-insulinModel.effectDuration)
        let relevantDoses = doses.filter {
            $0.endDate >= lookbackStart && $0.startDate <= lastGlucose.startDate
            && $0.startDate >= firstSens.startDate && $0.startDate <= lastSens.endDate
        }
        // Trim basal schedule to the relevant window
        let trimmedBasal = basal.trimmed(from: lookbackStart, to: lastGlucose.startDate)
        let annotated = relevantDoses.annotated(with: trimmedBasal, fillBasalGaps: true)
        let insulinEffects = annotated.glucoseEffects(
            insulinSensitivityHistory: sensitivity,
            from: lookbackStart,
            to: lastGlucose.startDate
        )
        return glucose.counteractionEffects(to: insulinEffects)
    }

    /// Add a single dose's glucose-effect contribution to the cumulative
    /// timeline. `cum[j] - cum[i]` = insulin glucose effect over [grid[i], grid[j]].
    /// Uses Loop's exact `glucoseEffects` on a single-dose array (bounded cost
    /// per dose since the effects window is at most DIA wide).
    fileprivate static func addDoseContribution(
        dose: BasalRelativeDose,
        grid: [Date],
        cum: inout [Double],
        sensitivity: [AbsoluteScheduleValue<LoopQuantity>],
        insulinModel: InsulinModel
    ) {
        if cum.count != grid.count {
            cum = Array(repeating: 0, count: grid.count)
        }
        guard abs(dose.netBasalUnits) > 1e-12 else { return }
        // Single-dose effect timeline over [dose.startDate, dose.endDate + DIA].
        let from = dose.startDate
        let to = dose.endDate.addingTimeInterval(insulinModel.effectDuration)
        let stepSec: TimeInterval = 5 * 60
        let effects = [dose].glucoseEffects(
            insulinSensitivityHistory: sensitivity,
            from: from,
            to: to,
            delta: stepSec
        )
        guard !effects.isEmpty else { return }
        // Effects are CUMULATIVE; effects[k].quantity = total mg/dL change due to
        // this dose at effects[k].startDate (relative to baseline at first entry).
        let mgdl = LoopUnit.milligramsPerDeciliter
        // Binary search grid for first entry > dose.startDate
        var lo = 0, hi = grid.count
        while lo < hi {
            let mid = (lo + hi) / 2
            if grid[mid] <= dose.startDate { lo = mid + 1 } else { hi = mid }
        }
        // For each grid point past dose.startDate, look up the effect at that
        // point in the dose's effects timeline (linear interp), and add it.
        var effIdx = 0
        for i in lo..<grid.count {
            let target = grid[i]
            // Advance effIdx to last entry with startDate <= target
            while effIdx + 1 < effects.count && effects[effIdx + 1].startDate <= target {
                effIdx += 1
            }
            let v: Double
            if effIdx + 1 < effects.count {
                // Linear interp
                let a = effects[effIdx], b = effects[effIdx + 1]
                let span = b.startDate.timeIntervalSince(a.startDate)
                let frac = span > 0 ? target.timeIntervalSince(a.startDate) / span : 0
                v = a.quantity.doubleValue(for: mgdl) * (1 - frac)
                  + b.quantity.doubleValue(for: mgdl) * frac
            } else if effIdx < effects.count {
                v = effects[effIdx].quantity.doubleValue(for: mgdl)
            } else {
                v = 0
            }
            cum[i] += v
        }
    }

    /// O(log N) lookup of cumulative insulin effect at a target date.
    /// Linear-interpolates between adjacent grid points.
    fileprivate static func lookupCumEffect(
        target: Date,
        grid: [Date],
        cum: [Double]
    ) -> Double {
        guard !grid.isEmpty else { return 0 }
        if target <= grid.first! { return cum.first! }
        if target >= grid.last! { return cum.last! }
        var lo = 0, hi = grid.count - 1
        while hi - lo > 1 {
            let mid = (lo + hi) / 2
            if grid[mid] <= target { lo = mid } else { hi = mid }
        }
        let span = grid[hi].timeIntervalSince(grid[lo])
        let frac = span > 0 ? target.timeIntervalSince(grid[lo]) / span : 0
        return cum[lo] * (1 - frac) + cum[hi] * frac
    }

    /// Integrate ICE velocities over a time interval to get total mg/dL change.
    fileprivate static func integrateICE(_ ice: [GlucoseEffectVelocity],
                                          from: Date, to: Date) -> Double {
        guard to > from, !ice.isEmpty else { return 0 }
        let perSecUnit = GlucoseEffectVelocity.perSecondUnit
        var total = 0.0
        // ICE entries are sorted by startDate. Linear scan; could binary search.
        for entry in ice {
            if entry.endDate <= from { continue }
            if entry.startDate >= to { break }
            let overlapStart = Swift.max(entry.startDate, from)
            let overlapEnd = Swift.min(entry.endDate, to)
            let overlapSec = overlapEnd.timeIntervalSince(overlapStart)
            if overlapSec > 0 {
                total += entry.quantity.doubleValue(for: perSecUnit) * overlapSec
            }
        }
        return total
    }

    /// Compute the insulin glucose effect delta over [from, to] from the
    /// candidate dose history. Result is in mg/dL (negative = BG drop from
    /// insulin). Uses Loop's public glucoseEffects timeline and diffs the
    /// cumulative value at the two boundary times.
    ///
    /// `doses` is assumed sorted ascending by startDate (counterfactualDoses
    /// always is). We binary-search the upper bound on startDate (<= to) and
    /// then walk back to find the lower bound (endDate >= lookback). This
    /// limits per-call cost to O(log N + DIA-window size) instead of O(N).
    fileprivate static func insulinEffectDelta(
        doses: [EvalInsulinDose],
        basal: [AbsoluteScheduleValue<Double>],
        sensitivity: [AbsoluteScheduleValue<LoopQuantity>],
        from: Date, to: Date,
        insulinModel: InsulinModel
    ) -> Double {
        guard to > from else { return 0 }
        let lookback = from.addingTimeInterval(-insulinModel.effectDuration)
        // Binary search for first index where startDate > to.
        var lo = 0, hi = doses.count
        while lo < hi {
            let mid = (lo + hi) / 2
            if doses[mid].startDate <= to { lo = mid + 1 } else { hi = mid }
        }
        let upperIdx = lo  // first index with startDate > to
        if upperIdx == 0 { return 0 }
        // Walk back to find the first index whose endDate >= lookback.
        // Doses are sorted by startDate; doses earlier than lookback - DIA can't
        // possibly overlap. Stop scanning once startDate < lookback - DIA.
        let scanFloor = lookback.addingTimeInterval(-insulinModel.effectDuration)
        var lowerIdx = upperIdx - 1
        while lowerIdx > 0 && doses[lowerIdx - 1].startDate >= scanFloor {
            lowerIdx -= 1
        }
        let relevantDoses = doses[lowerIdx..<upperIdx].filter { $0.endDate >= lookback }
        if relevantDoses.isEmpty { return 0 }
        guard let firstSens = sensitivity.first, let lastSens = sensitivity.last else { return 0 }
        let safeDoses = relevantDoses.filter {
            $0.startDate >= firstSens.startDate && $0.startDate <= lastSens.endDate
        }
        if safeDoses.isEmpty { return 0 }
        let trimmedBasal = basal.trimmed(from: lookback, to: to)
        let annotated = safeDoses.annotated(with: trimmedBasal, fillBasalGaps: true)
        // Compute cumulative glucose effects timeline that covers [from, to].
        // Use 5-min delta so the timeline lands at the boundaries we want.
        let delta: TimeInterval = 5 * 60
        let effects = annotated.glucoseEffects(
            insulinSensitivityHistory: sensitivity,
            from: from.addingTimeInterval(-delta),
            to: to.addingTimeInterval(delta),
            delta: delta
        )
        let mgdl = LoopUnit.milligramsPerDeciliter
        let valueAt: (Date) -> Double = { target in
            // Find the entry closest to target; effects are monotonically spaced
            // by `delta`. Linear interp between neighbors.
            guard !effects.isEmpty else { return 0 }
            if target <= effects.first!.startDate { return effects.first!.quantity.doubleValue(for: mgdl) }
            if target >= effects.last!.startDate { return effects.last!.quantity.doubleValue(for: mgdl) }
            for i in 0..<(effects.count - 1) {
                let a = effects[i], b = effects[i + 1]
                if a.startDate <= target && target <= b.startDate {
                    let span = b.startDate.timeIntervalSince(a.startDate)
                    let frac = span > 0 ? target.timeIntervalSince(a.startDate) / span : 0
                    return a.quantity.doubleValue(for: mgdl) * (1 - frac)
                         + b.quantity.doubleValue(for: mgdl) * frac
                }
            }
            return effects.last!.quantity.doubleValue(for: mgdl)
        }
        return valueAt(to) - valueAt(from)
    }

    /// PHYSICAL active-insulin glucose effect over [from, to]: the always-
    /// lowering effect of ABSOLUTE delivered insulin (volume), with the
    /// EGP-credit term zeroed (scheduleBaselineSensitivity = 0 ⇒ only the
    /// `volume × -activeSensitivity` term survives the .physicalDelivery split).
    /// Used by sensitivity-inference so the inferred multiplier scales ONLY the
    /// physical insulin; EGP stays in the dose-independent residual and is never
    /// magnified by m (avoids the net-basal "negative IOB raises BG" artifact).
    /// mg/dL, negative = drop. Same dose-slicing as `insulinEffectDelta`.
    fileprivate static func physicalActiveEffectDelta(
        doses: [EvalInsulinDose],
        basal: [AbsoluteScheduleValue<Double>],
        sensitivity: [AbsoluteScheduleValue<LoopQuantity>],
        from: Date, to: Date,
        insulinModel: InsulinModel
    ) -> Double {
        guard to > from else { return 0 }
        let lookback = from.addingTimeInterval(-insulinModel.effectDuration)
        var lo = 0, hi = doses.count
        while lo < hi {
            let mid = (lo + hi) / 2
            if doses[mid].startDate <= to { lo = mid + 1 } else { hi = mid }
        }
        let upperIdx = lo
        if upperIdx == 0 { return 0 }
        let scanFloor = lookback.addingTimeInterval(-insulinModel.effectDuration)
        var lowerIdx = upperIdx - 1
        while lowerIdx > 0 && doses[lowerIdx - 1].startDate >= scanFloor { lowerIdx -= 1 }
        let relevantDoses = doses[lowerIdx..<upperIdx].filter { $0.endDate >= lookback }
        if relevantDoses.isEmpty { return 0 }
        guard let firstSens = sensitivity.first, let lastSens = sensitivity.last else { return 0 }
        let safeDoses = relevantDoses.filter {
            $0.startDate >= firstSens.startDate && $0.startDate <= lastSens.endDate
        }
        if safeDoses.isEmpty { return 0 }
        let trimmedBasal = basal.trimmed(from: lookback, to: to)
        let annotated = safeDoses.annotated(with: trimmedBasal, fillBasalGaps: true)
        let delta: TimeInterval = 5 * 60
        // Zero baseline-sensitivity ⇒ the EGP-credit term (egpRaise × baseline)
        // vanishes; only the physical active term (volume × -activeSensitivity)
        // remains. EGP is instead carried, unscaled, by realBGdelta.
        let zeroBaseline = sensitivity.map {
            AbsoluteScheduleValue(startDate: $0.startDate, endDate: $0.endDate,
                                  value: LoopQuantity(unit: $0.value.unit, doubleValue: 0))
        }
        let effects = annotated.glucoseEffects(
            insulinSensitivityHistory: sensitivity,
            scheduleBaselineSensitivityHistory: zeroBaseline,
            from: from.addingTimeInterval(-delta),
            to: to.addingTimeInterval(delta),
            delta: delta,
            decomposition: .physicalDelivery
        )
        let mgdl = LoopUnit.milligramsPerDeciliter
        let valueAt: (Date) -> Double = { target in
            guard !effects.isEmpty else { return 0 }
            if target <= effects.first!.startDate { return effects.first!.quantity.doubleValue(for: mgdl) }
            if target >= effects.last!.startDate { return effects.last!.quantity.doubleValue(for: mgdl) }
            for i in 0..<(effects.count - 1) {
                let a = effects[i], b = effects[i + 1]
                if a.startDate <= target && target <= b.startDate {
                    let span = b.startDate.timeIntervalSince(a.startDate)
                    let frac = span > 0 ? target.timeIntervalSince(a.startDate) / span : 0
                    return a.quantity.doubleValue(for: mgdl) * (1 - frac)
                         + b.quantity.doubleValue(for: mgdl) * frac
                }
            }
            return effects.last!.quantity.doubleValue(for: mgdl)
        }
        return valueAt(to) - valueAt(from)
    }

    fileprivate static func rasterizeRealPumpPerStep(
        doses: [EvalInsulinDose], start: Date, end: Date, stepSec: TimeInterval
    ) -> [Date: Double] {
        var result: [Date: Double] = [:]
        let stepCount = Int((end.timeIntervalSince(start) / stepSec).rounded(.up)) + 1
        // Initialize all step bins to 0
        for i in 0..<stepCount {
            let bin = start.addingTimeInterval(Double(i) * stepSec)
            result[bin] = 0
        }
        let gridStartSec = start.timeIntervalSince1970
        let gridEndSec = end.timeIntervalSince1970 + stepSec
        for dose in doses {
            let dStart = dose.startDate.timeIntervalSince1970
            let dEnd = dose.endDate.timeIntervalSince1970
            if dEnd < gridStartSec || dStart > gridEndSec { continue }
            // Bolus (instant) — treat anything with duration < step as instant
            if dose.deliveryType != .basal || (dEnd - dStart) < 1 {
                let s = max(dStart, gridStartSec)
                let binIdx = Int((s - gridStartSec) / stepSec)
                if binIdx >= 0 && binIdx < stepCount {
                    let bin = start.addingTimeInterval(Double(binIdx) * stepSec)
                    result[bin, default: 0] += dose.volume
                }
                continue
            }
            // Basal entry: distribute volume across overlapping bins
            let dur = dEnd - dStart
            if dur <= 0 { continue }
            let uPerSec = dose.volume / dur
            var cur = max(dStart, gridStartSec)
            let stop = min(dEnd, gridEndSec)
            while cur < stop {
                let binIdx = Int((cur - gridStartSec) / stepSec)
                if binIdx < 0 { cur += stepSec; continue }
                if binIdx >= stepCount { break }
                let bin = start.addingTimeInterval(Double(binIdx) * stepSec)
                let binEndSec = gridStartSec + Double(binIdx + 1) * stepSec
                let segEnd = min(binEndSec, stop)
                result[bin, default: 0] += uPerSec * (segEnd - cur)
                cur = segEnd
            }
        }
        return result
    }

    // MARK: – Helpers

    /// Canonical "compute one step's recommended Δdose" used for BOTH baseline
    /// and candidate inside the closed-loop sim. Keeping the two sides on the
    /// same code path is what makes the identity case (configs equal) produce
    /// Δdose = 0 at every step. Uses the raw-doses `generatePrediction` path
    /// (not `precomputedInsulin`) because the candidate's dose history changes
    /// per step — precomputing wouldn't be valid for it.
    fileprivate static func simStepDose(
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
    ) -> (dose: Double, bolus: Double, tempRate: Double, prediction: LoopPrediction<EvalCarbEntry>) {
        let momentumCap: LoopQuantity? = config.positiveVelocityCap.map {
            LoopQuantity(unit: .milligramsPerDeciliterPerMinute, doubleValue: $0)
        }

        // When asymmetric persistent-boost is active, scale sensitivity used
        // for BOTH the prediction and the dose recommendation. The prediction
        // matters: if the forecast also "knows" ISF is currently higher than
        // schedule, Loop's IOB-compensation expects less BG drop and doesn't
        // try to redistribute the under-delivered insulin forward.
        let unit = LoopUnit.milligramsPerDeciliter
        // Sustained post-low ISF reduction: within the post-low window, model
        // insulin as MORE effective (ISF × factor, decaying with recency) so
        // Loop sizes the rebound correction down at the source. Folded into the
        // effective ISF multiplier used to build effectiveSensitivity below.
        var dampFactor = 1.0  // ISF-up (dose-down) factor: post-low and/or predictive
        // Post-low: recent low → size the rebound correction down (recency-decay).
        if config.postlowIsfMult > 1.0, let lastG = input.glucose.last {
            // Scan the candidate's OWN glucose history up to t (input.glucose),
            // NOT the static substrate — its last element is the current step.
            let windowSec = config.postlowWindowMin * 60.0
            var recency = 0.0
            for s in input.glucose.reversed() {
                let age = lastG.startDate.timeIntervalSince(s.startDate)
                if age > windowSec { break }
                if s.quantity.doubleValue(for: unit) < config.postlowThresholdMgdl {
                    recency = max(0.0, 1.0 - age / windowSec); break
                }
            }
            dampFactor = max(dampFactor, 1.0 + (config.postlowIsfMult - 1.0) * recency)
        }
        // Predictive pre-low: strict-causal sustained-sensitivity trigger.
        // causal ICE = v_bg − v_insulin over a trailing window (from the
        // candidate's OWN glucose + dose history). When BG is dropping faster
        // than the candidate's modeled insulin explains, raise ISF proactively.
        if config.sensDampGain > 0, let lastG = input.glucose.last {
            let winSec = config.sensDampWindowMin * 60.0
            let nowBG = lastG.quantity.doubleValue(for: unit)
            var vbg = 0.0; var have = false
            for s in input.glucose.reversed() {
                let dt = lastG.startDate.timeIntervalSince(s.startDate)
                if dt >= winSec {
                    vbg = (nowBG - s.quantity.doubleValue(for: unit)) / (dt / 60.0); have = true; break
                }
            }
            if have {
                let insEff = Self.insulinEffectDelta(
                    doses: input.doses, basal: therapy.basal, sensitivity: therapy.sensitivity,
                    from: lastG.startDate.addingTimeInterval(-winSec), to: lastG.startDate,
                    insulinModel: therapy.insulinType.model)
                let vins = insEff / (winSec / 60.0)        // mg/dL/min, negative = drop
                let causalICE = vbg - vins                 // negative = sensitive (faster than insulin)
                if causalICE < -config.sensDampThresholdRate {
                    let f = min(1.0 + config.sensDampGain * (-causalICE - config.sensDampThresholdRate),
                                config.sensDampMax)
                    dampFactor = max(dampFactor, f)
                }
            }
        }
        let effExtraISF = extraISFMultiplier * dampFactor
        let effectiveSensitivity: [AbsoluteScheduleValue<LoopQuantity>]

        // Fast-path: even if a map is set, if no boost falls within [t, t+DIA]
        // the schedule is effectively unchanged for this step's prediction.
        // Probe the map for any non-1.0 mult in the forecast window before
        // doing the (relatively expensive) segment expansion.
        let stepSec = config.evalStep
        let horizonEnd = t.addingTimeInterval(therapy.insulinType.model.effectDuration + stepSec)
        let mapHasBoostInWindow: Bool = {
            guard let perStepMap = perStepIsfMultByTime, !perStepMap.isEmpty else { return false }
            var probeT = Date(timeIntervalSince1970:
                (t.timeIntervalSince1970 / stepSec).rounded() * stepSec)
            while probeT < horizonEnd {
                if let m = perStepMap[probeT], abs(m - 1.0) > 1e-9 { return true }
                probeT = probeT.addingTimeInterval(stepSec)
            }
            return false
        }()

        if let perStepMap = perStepIsfMultByTime, !perStepMap.isEmpty, mapHasBoostInWindow {
            // Expand sensitivity into per-step segments ONLY over the forecast
            // horizon [t, t + DIA]. Outside that window keep the original
            // (unboosted) schedule entries — they're not consulted by the
            // dose calc (insulinCorrection only filters segments overlapping
            // the prediction's absorption window).
            //
            // CRITICAL: only apply the mult to FUTURE segments (segEnd > t).

            var fineEntries: [AbsoluteScheduleValue<LoopQuantity>] = []
            fineEntries.reserveCapacity(96)   // ~6h × 12 segs/h × bit of slack

            for entry in input.sensitivity {
                let baseVal = entry.value.doubleValue(for: unit) * effExtraISF
                // Three regions:
                //   1) entirely before t — pass through as-is (mult=1.0)
                //   2) overlaps [t, horizonEnd] — expand into 5-min segments with per-future mult
                //   3) entirely after horizonEnd — pass through as-is (no boost lookup needed)
                if entry.endDate <= t || entry.startDate >= horizonEnd {
                    // Region 1 or 3: no expansion needed, scaled by extraISFMultiplier
                    fineEntries.append(AbsoluteScheduleValue(
                        startDate: entry.startDate, endDate: entry.endDate,
                        value: LoopQuantity(unit: unit, doubleValue: baseVal)))
                    continue
                }
                // Region 2: split entry at t and horizonEnd boundaries, expand the middle.
                if entry.startDate < t {
                    fineEntries.append(AbsoluteScheduleValue(
                        startDate: entry.startDate, endDate: t,
                        value: LoopQuantity(unit: unit, doubleValue: baseVal)))
                }
                // Coalesce consecutive 5-min segments with the same mult.
                // CSV is mostly 1.0 (60-75% of entries); merging runs cuts
                // Loop's sensitivity-iteration cost (it's O(N) in schedule
                // length per dose × per prediction sample, so this matters).
                var cursor = max(entry.startDate, t)
                let expandEnd = min(entry.endDate, horizonEnd)
                var runStart = cursor
                var runMult: Double? = nil
                while cursor < expandEnd {
                    let segEnd = min(cursor.addingTimeInterval(stepSec), expandEnd)
                    let rounded = Date(timeIntervalSince1970:
                        (cursor.timeIntervalSince1970 / stepSec).rounded() * stepSec)
                    let mult = perStepMap[rounded] ?? 1.0
                    if runMult == nil {
                        runMult = mult
                        runStart = cursor
                    } else if abs(mult - runMult!) > 1e-9 {
                        // Flush previous run
                        fineEntries.append(AbsoluteScheduleValue(
                            startDate: runStart, endDate: cursor,
                            value: LoopQuantity(unit: unit, doubleValue: baseVal * runMult!)))
                        runMult = mult
                        runStart = cursor
                    }
                    cursor = segEnd
                }
                if let m = runMult {
                    fineEntries.append(AbsoluteScheduleValue(
                        startDate: runStart, endDate: cursor,
                        value: LoopQuantity(unit: unit, doubleValue: baseVal * m)))
                }
                if entry.endDate > horizonEnd {
                    fineEntries.append(AbsoluteScheduleValue(
                        startDate: horizonEnd, endDate: entry.endDate,
                        value: LoopQuantity(unit: unit, doubleValue: baseVal)))
                }
            }
            effectiveSensitivity = fineEntries
        } else if abs(effExtraISF - 1.0) > 1e-9 {
            effectiveSensitivity = input.sensitivity.map { entry in
                AbsoluteScheduleValue(
                    startDate: entry.startDate,
                    endDate: entry.endDate,
                    value: LoopQuantity(unit: unit,
                                        doubleValue: entry.value.doubleValue(for: unit) * effExtraISF))
            }
        } else {
            effectiveSensitivity = input.sensitivity
        }
        let effectiveInput = PredictionInput(
            glucose: input.glucose,
            doses: input.doses,
            carbs: input.carbs,
            basal: input.basal,
            sensitivity: effectiveSensitivity,
            carbRatio: input.carbRatio,
            target: input.target
        )

        // Phase-1 decomposition: when `isfBoostActiveOnly` is on, pass the
        // UNBOOSTED schedule as `scheduleBaselineSensitivity` so the
        // EGP-credit term (negative netBasalUnits — implicit endogenous
        // glucose production from suspending below scheduled basal) keeps
        // using the scheduled ISF, while the dose-rec and active-insulin
        // glucose-effect use the boosted `effectiveSensitivity`. When the
        // step has no boost (effectiveSensitivity == input.sensitivity by
        // content), Phase 1's decomposed formula is bit-identical to legacy.
        // The post-low ISF reduction is also a boost-active case: hold EGP at
        // the scheduled ISF (physicalDelivery split) so the reduction scales
        // ONLY the active-insulin term — never amplifies the sub-basal EGP
        // credit (per the asym-IRC low-side "preserve EGP separately" design).
        let postlowActive = abs(effExtraISF - extraISFMultiplier) > 1e-12
        let scheduleBaseline: [AbsoluteScheduleValue<LoopQuantity>]? =
            (isfBoostActiveOnly || postlowActive) ? input.sensitivity : nil
        // Phase-2: with `egpPhysicalDecomposition`, the active-insulin term is
        // computed over PHYSICAL delivered insulin (volume) rather than
        // net-basal-units, so an active-ISF boost amplifies real insulin even
        // when delivery is below scheduled basal. Only meaningful alongside
        // isfBoostActiveOnly (a non-nil scheduleBaseline). Default keeps the
        // classic net-basal-units split.
        let decomposition: SensitivityDecomposition =
            ((egpPhysicalDecomposition && isfBoostActiveOnly) || postlowActive) ? .physicalDelivery : .netBasalUnits
        var prediction: LoopPrediction<EvalCarbEntry> = LoopAlgorithm.generatePrediction(
            start: t,
            glucoseHistory: effectiveInput.glucose,
            doses: effectiveInput.doses,
            carbEntries: effectiveInput.carbs,
            basal: effectiveInput.basal,
            sensitivity: effectiveInput.sensitivity,
            scheduleBaselineSensitivity: scheduleBaseline,
            sensitivityDecomposition: decomposition,
            carbRatio: effectiveInput.carbRatio,
            algorithmEffectsOptions: .all,
            useIntegralRetrospectiveCorrection: config.useIntegralRC,
            ircDropGainScale: config.ircDropGainScale,
            ircRiseGainScale: config.ircRiseGainScale,
            includingPositiveVelocityAndRC: config.includingPositiveVelocityAndRC,
            useMidAbsorptionISF: config.useMidAbsorptionISF,
            carbAbsorptionModel: config.carbAbsorptionModel.model,
            momentumVelocityMaximum: momentumCap,
            useAsymmetricMomentum: config.useAsymmetricMomentum,
            momentumAlphaSlow: config.momentumAlphaSlow,
            momentumAlphaFast: config.momentumAlphaFast,
            highCorrectionEnabled: config.highCorrectionEnabled,
            highCorrectionRiseGain: config.highCorrectionRiseGain,
            highCorrectionEffectDurationMinutes: config.highCorrectionEffectDurationMinutes,
            highCorrectionFastOffVelocity: config.highCorrectionFastOffVelocity
        )

        // Sustained-sensitivity (post-low) forecast SUPPRESSION: a SELECTIVE
        // lows-protector. When a recent low occurred (strong evidence of elevated
        // sensitivity, and the repeat-low/rebound regime), LOWER the forecast so
        // Loop backs off / holds the suspend through the rebound — preventing the
        // redose that drives the next low. Decays linearly over the window
        // (slow-off). Forecast-side, BG-subtraction (EGP-safe, no ISF/EGP coupling).
        var postlowOffset = 0.0
        if config.postlowSuppressMgdl > 0 || config.postlowTrendGain > 0,
           let lastT = effectiveInput.glucose.last?.startDate {
            let windowSec = config.postlowWindowMin * 60.0
            let mgdl = LoopUnit.milligramsPerDeciliter
            var recency = 0.0  // 1 just after a recent low, decaying to 0 over the window
            for s in effectiveInput.glucose.reversed() {
                let age = lastT.timeIntervalSince(s.startDate)
                if age > windowSec { break }
                if s.quantity.doubleValue(for: mgdl) < config.postlowThresholdMgdl {
                    recency = max(0.0, 1.0 - age / windowSec); break
                }
            }
            if recency > 0 {
                // Trend augmentation: current downtrend (causal velocity over the
                // last ~20 min). Suppress MORE when BG is dropping again toward the
                // second low; nothing extra while recovering (velocity ≥ 0).
                var dropRate = 0.0  // mg/dL per minute, positive = dropping
                if config.postlowTrendGain > 0 {
                    let g = effectiveInput.glucose
                    if let last = g.last {
                        let lastV = last.quantity.doubleValue(for: mgdl)
                        // find a sample ~20 min before the last
                        for s in g.reversed() {
                            let dt = last.startDate.timeIntervalSince(s.startDate)
                            if dt >= 20 * 60 {
                                let v = (lastV - s.quantity.doubleValue(for: mgdl)) / (dt / 60.0)
                                dropRate = max(0.0, -v); break
                            }
                        }
                    }
                }
                postlowOffset = -recency * (config.postlowSuppressMgdl
                                            + config.postlowTrendGain * dropRate)
            }
        }

        // Classifier-gated forecast modifier: shift the predicted glucose
        // trajectory by `forecastOffsetMgdl` (+ any post-low suppression) before
        // the dose calc. A true forecast modification — Loop's correction logic
        // and suspend-zone detection both see it. AGENTS.md "modify the forecast,
        // not the dose".
        let totalForecastOffset = forecastOffsetMgdl + postlowOffset
        if abs(totalForecastOffset) > 1e-9 {
            let unit = LoopUnit.milligramsPerDeciliter
            prediction.glucose = prediction.glucose.map { p in
                PredictedGlucoseValue(
                    startDate: p.startDate,
                    quantity: LoopQuantity(unit: unit,
                                           doubleValue: p.quantity.doubleValue(for: unit) + totalForecastOffset)
                )
            }
        }

        // Application factor: flat config value (default 0.4), or glucose-based
        // (GBAF) ramp keyed on the current BG (latest glucose at/before t).
        var appFactor = config.applicationFactor
        if config.glucoseBasedApplicationFactor {
            let curBG = effectiveInput.glucose.last?.quantity.doubleValue(for: LoopUnit.milligramsPerDeciliter)
                ?? prediction.glucose.first?.quantity.doubleValue(for: LoopUnit.milligramsPerDeciliter) ?? 0
            appFactor = EvaluationEngine.glucoseBasedApplicationFactor(
                currentBG: curBG,
                lowAnchor: config.gbafLowAnchor, highAnchor: config.gbafHighAnchor,
                factorLow: config.gbafFactorLow, factorHigh: config.gbafFactorHigh)
        }
        let doseRec = EvaluationEngine.computeDoseRecommendation(
            prediction: prediction,
            at: t,
            input: effectiveInput,
            suspendThreshold: therapy.suspendThreshold,
            maxBolus: therapy.maxBolus,
            maxBasalRate: therapy.maxBasalRate,
            insulinType: therapy.insulinType,
            evalStep: config.evalStep,
            applicationFactor: appFactor
        )
        return (
            dose: doseRec?.deltaU ?? 0,
            bolus: doseRec?.bolus ?? 0,
            tempRate: doseRec?.tempBasalRate ?? 0,
            prediction: prediction
        )
    }

    /// Find the index of the glucose sample closest to `t` (binary-search).
    fileprivate static func bestGlucoseIndex(at t: Date, in samples: [EvalGlucoseSample]) -> Int {
        var lo = 0, hi = samples.count - 1
        while lo < hi {
            let mid = (lo + hi) / 2
            if samples[mid].startDate < t { lo = mid + 1 } else { hi = mid }
        }
        return min(max(lo, 0), samples.count - 1)
    }

    /// Largest index with `samples[idx].startDate <= t`; if none, returns 0.
    /// Differs from `bestGlucoseIndex` (which returns the *first* sample at
    /// or after t). For the closed-loop trace writer, the "past sample" is
    /// what carries advanced counter perturbations; the "next future"
    /// sample may sit in an unprocessed CGM gap and still hold its
    /// un-advanced original value.
    fileprivate static func latestGlucoseIndex(at t: Date, in samples: [EvalGlucoseSample]) -> Int {
        guard !samples.isEmpty else { return 0 }
        if samples[0].startDate > t { return 0 }
        var lo = 0, hi = samples.count - 1
        while lo < hi {
            let mid = (lo + hi + 1) / 2  // upper bisect
            if samples[mid].startDate <= t { lo = mid } else { hi = mid - 1 }
        }
        return lo
    }

    /// Merge two sorted dose arrays in O(N+M).
    private static func mergeSorted(_ a: [EvalInsulinDose], _ b: [EvalInsulinDose]) -> [EvalInsulinDose] {
        if b.isEmpty { return a }
        if a.isEmpty { return b }
        var out: [EvalInsulinDose] = []
        out.reserveCapacity(a.count + b.count)
        var i = 0, j = 0
        while i < a.count && j < b.count {
            if a[i].startDate <= b[j].startDate {
                out.append(a[i]); i += 1
            } else {
                out.append(b[j]); j += 1
            }
        }
        while i < a.count { out.append(a[i]); i += 1 }
        while j < b.count { out.append(b[j]); j += 1 }
        return out
    }
}

