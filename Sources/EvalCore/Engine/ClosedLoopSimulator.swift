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
        /// Temp-basal-strategy ifNecessary action ("set" | "cancel" | "none"); "set" on the bolus path.
        public var candidateTempAction: String = "set"
        public var baselineTempAction: String = "set"
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
        public var candidateMomentum: Double = .nan  // candidate's net momentum contribution IN ISOLATION (mg/dL)
        public var candidateRC: Double = .nan         // candidate's net RC contribution IN ISOLATION (mg/dL); = asym-IRC when enabled
        public var candidateMomentumMarginal: Double = .nan // MARGINAL effect on eventualBG: with - without momentum (accounts for blend)
        public var candidateRCMarginal: Double = .nan       // MARGINAL effect on eventualBG: with - without RC
        public var candidateAutosensRatio: Double = .nan  // OAPS autosens ratio (nan for Loop)
        public var candidateMinGuardBG: Double = .nan     // OAPS predicted-min BG that gates SMB (nan for Loop)
        public var candidateMinPredBG: Double = .nan      // OAPS predicted-min BG (nan for Loop)
        // ICE→carb/RC attribution diagnostics (mg/dL over the latest ~5-min interval).
        // candidateICE = raw insulin-counteraction effect; candidateCarbEffect = portion the
        // dynamic carb model absorbed; candidateDiscrepancy = remainder that feeds RC.
        // By construction candidateICE ≈ candidateCarbEffect + candidateDiscrepancy.
        public var candidateICE: Double = .nan
        public var candidateCarbEffect: Double = .nan
        public var candidateDiscrepancy: Double = .nan
        // Sensitive Mode state: the ISF multiplier applied this step (1.0 = inactive;
        // >1 = active, raising effective ISF from accumulated recent negative discrepancies).
        public var candidateSensModeMult: Double = .nan
        public var candidateManualBolusRecOut: Double = .nan
        // PATIENT IOB — a single independent IOB view: field dosing and candidate
        // dosing each run through the SAME patient insulin model (net-basal,
        // fillBasalGaps) via insulinOnBoard(at:). Independent of NS devicestatus
        // timing and of any candidate-algorithm IOB changes. This is the fair
        // apples-to-apples IOB for field-vs-candidate visualization.
        public var patientIOBField: Double = .nan
        public var patientIOBCandidate: Double = .nan
        // Full baseline forecast curve (sim Loop on REAL BG), mg/dL, 5-min spaced from t.
        // For point-by-point comparison against field devicestatus predicted.values. Empty unless requested.
        public var baselinePredCurve: [Double] = []
    }
    public let steps: [Step]
    public let baselineLabel: String
    public let candidateLabel: String
    public let intervalStart: Date
    public let intervalEnd: Date
    /// The candidate's ACTUAL delivery history (burn-in real seed + candidate
    /// basal/auto-bolus + passed-through/resized user manual boluses). This is
    /// the ground-truth candidate delivery — use it for the delivery stream so
    /// manual boluses (automatic == false) are represented, not just auto-boluses.
    public var counterfactualDoses: [EvalInsulinDose] = []
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
        forecastOffsetByStep: [Date: Double]? = nil,
        isfBoostActiveOnly: Bool = false,
        egpPhysicalDecomposition: Bool = false,
        isfBoostGateEventualMgdl: Double? = nil,
        isfBoostVetoIceRate: Double? = nil,
        outages: [Outage] = [],
        // Outage reasons during which the PUMP keeps delivering SCHEDULED basal (e.g.
        // `loop_offline`: phone away — the pod runs its schedule; only NEW adjustments
        // stop). Default empty = legacy behaviour (every outage clamps delivery to 0).
        outageBasalContinuesReasons: Set<String> = [],
        cgmStaleGuardSec: TimeInterval = 0,
        counterfactualMode: Bool = false,
        // Decision-time replay: NOT a closed loop. Both arms see the IDENTICAL real
        // (glucose, doses, carbs, settings) at every step and emit a dose recommendation
        // without acting — the candidate's glucose/dose inputs are forced to the same real
        // data the baseline sees (no counter trajectory, no perturbation, no virtual doses).
        // For same-input Loop-vs-oref dose/forecast comparison. With candidate == Loop this
        // must yield baselineDose == candidateDose at every step (fairness identity test).
        decisionTimeReplay: Bool = false,
        counterfactualBurnInSec: TimeInterval = 6 * 3600,
        // CF-IDENTITY harness: force the candidate to deliver EXACTLY the real
        // dose history (no re-dosing) through the SAME physiological advance, so
        // `counter` MUST reproduce `actual` to within rounding. This isolates the
        // patient model from the controller — the only valid test of the CF
        // advance math (candidate doses == real ⇒ counter == actual). Requires
        // counterfactualMode.
        cfIdentity: Bool = false,
        // CGM-DRIVEN DECISIONS: trigger one automatic dosing decision per actual
        // CGM sample (the real, irregular ~5-min cadence) instead of a fixed
        // evalStep grid. The loop runs ONLY after a new CGM — never for any other
        // reason. The substrate is built on the raw CGM sample timestamps
        // (smoothed values for physiology, raw values for the controller) with
        // variable per-step dt = (next CGM − this CGM). Default (false) keeps the
        // regular 5-min substrate + grid march (byte-identical legacy path).
        decisionsFromCgm: Bool = false,
        // FIELD-CADENCE DECISIONS: step at exactly these instants — the real
        // controller's recorded dosingDecision times — instead of the CGM sample
        // cadence. Kills two divergence classes at once: synthetic steps the field
        // never made (a 1-min multi-source stream gives 5x the field's cycles, each
        // meal moment scored 2-5x), and steps DURING field skip-gaps whose state the
        // field never computed. Implies the instants are authoritative (the momentum
        // now-anchor uses them directly, not lastGlucose+7s). Empty = off.
        decisionTimes: [Date] = [],
        // Decision instants where the field controller RAN but bailed before the
        // dosing path (dosingDecision.errors pumpDataTooOld / glucoseTooOld — no
        // forecast, no recommendation stored). The guard's trigger state (pump-comms
        // freshness) is exogenous and not reconstructible from the export, but
        // Loop's own error record marks the exact cycles; the replay skips them the
        // same way it skips stale-CGM cycles. Subset of decisionTimes.
        noDoseGuardTimes: Set<Date> = [],
        // Model deployed timeBasedDoseApplicationFactor (min(1, sinceLastCompleted/5min)).
        // DEFAULT OFF: the deployed reference is the previous loop's COMPLETION instant
        // (15-40 s after its decision time), which the export does not record; the
        // decision-time approximation empirically HURT cohort match (-0.3 to -0.8 pts
        // across bolus donors, no improvements), so the approximation is opt-in for
        // study rather than default-on.
        enableTimeBasedAF: Bool = false,
        // Decision instants replayed with the TEMP-BASAL dosing strategy (mixed-
        // strategy donors switch AutomaticDosingStrategy mid-window; the per-cycle
        // mode comes from decision_times.csv `mode`, ETL v15 — detected from
        // INCREASE evidence only: rec_bolus>0 = bolus mode, rec_rate>scheduled
        // (outside raise-overrides) = temp mode; decrease cycles look identical in
        // both modes). Empty = use the configs' static useTempBasalStrategy.
        tempStrategyTimes: Set<Date> = [],
        excludeManualBoluses: Bool = false,
        suppressCarbs: Bool = false,
        counterRegOnsetMgdl: Double = 0,
        counterRegGain: Double = 0.2,
        counterRegMaxRate: Double = 6.0,
        // CGM-gap re-anchor: across a CGM gap longer than this, the counterfactual
        // has no ground truth and the single big-step physiological advance is
        // unreliable — manual boluses the user gave DURING the gap are in the field
        // side (realPhysDelta) but not in the candidate dose history (the per-step
        // passthrough only fires at CGM samples, of which there are none in a gap),
        // so the insulin asymmetry explodes (a 13.8h gap over meals ran the counter
        // to 700+). Re-anchor the counter to the real CGM at gap-end. Identity-safe:
        // at candidate==real, stepDelta==realBGdelta so the advance lands on the
        // actual anyway ⇒ no-op at identity. 0 disables (legacy).
        cfGapReanchorSec: TimeInterval = 1800,
        inferSensitivity: Bool = false,
        inferSensitivityMax: Double = 2.0,
        inferSensitivityWindowSec: TimeInterval = 30 * 60,
        inferSensitivitySmoothSec: TimeInterval = 0,
        inferSensitivitySmoothPrior: Double = 0,
        dumpNiePath: String? = nil,
        useOpenAPSForCandidate: Bool = false,
        useLoopMimicForCandidate: Bool = false,
        sensorCapMgdl: Double = 400.0,
        progress: (@Sendable (Double) -> Void)? = nil
    ) throws -> ClosedLoopSimResult {

        // Run in the USER's timezone (the profile's), so oref's INTERNAL
        // time-of-day lookups — which use Calendar.current (basal-schedule lookup
        // in IobHistory, autosens hour-binning) — match the field's phone, just
        // like the adapter's explicit schedule reconstruction already does. The
        // host TZ would otherwise shift them (e.g. Berlin profile on a US host).
        // Common to baseline and candidate ⇒ identity (Δdose=0) is preserved.
        if let tz = data.therapyTimeline.scheduleTimeZone {
            NSTimeZone.default = tz
        }

        // 1. Set up mutable state.
        //
        // IMPORTANT: baseline and candidate must use the SAME code path so the
        // identity case (configs equal) gives Δdose = 0 at every step. Earlier
        // versions ran baseline through `runSweep` (precomputed-insulin path)
        // and candidate through an inline call (doses path); those two paths
        // are mathematically equivalent but numerically diverge, producing
        // non-zero Δdose at every step and compounding drift through the
        // feedback loop. Both sides now go through the engine's `step(_:)`
        // which (for LoopAdapter) calls one canonical doses-path
        // generatePrediction. Identity sanity therefore requires baseline and
        // candidate to share the SAME engine instance.
        let baselineEngine: DosingEngine = LoopAdapter()
        let candidateEngine: DosingEngine
        if useLoopMimicForCandidate {
            candidateEngine = LoopMimicViaOpenAPSAdapter()
        } else if useOpenAPSForCandidate {
            candidateEngine = OpenAPSAdapter()
        } else {
            candidateEngine = LoopAdapter()
        }
        let mgdlUnit = LoopUnit.milligramsPerDeciliter
        // Physical insulin model: therapy preset, unless a peak/DIA override is set
        // (experiment — run the whole sim against a custom "true" insulin, e.g. peak 90).
        let insulinModel: InsulinModel
        if let pk = candidateConfig.insulinPhysicalPeakMin {
            let diaSec = (candidateConfig.insulinPhysicalDiaHours ?? 6.0) * 3600.0
            insulinModel = ExponentialInsulinModel(actionDuration: diaSec, peakActivityTime: pk * 60.0, delay: 600)
        } else {
            insulinModel = data.therapyTimeline.insulinType.model
        }
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
        // physGlucose: the PHYSIOLOGY substrate — RTS-smoothed CGM on the 5-min
        // grid. Low-noise "ground truth" used ONLY for patient-physiology
        // estimation: ICE and the sensitivity-multiplier m(t) ("k") inference.
        let physGlucose: [EvalGlucoseSample]
        if decisionsFromCgm {
            // CGM-driven: substrate lives on the RAW CGM sample timestamps (no
            // resample to a regular grid). Physiology values are RTS-smoothed in
            // place (smoother keeps the input timestamps); raw values feed the
            // controller via simGlucose below. One substrate sample == one CGM ==
            // one decision.
            let sortedRaw = data.glucose.sorted { $0.startDate < $1.startDate }
            physGlucose = candidateConfig.kalmanSmoothing
                ? KalmanSmoother().smooth(samples: sortedRaw)
                : sortedRaw
        } else {
            physGlucose = candidateConfig.kalmanSmoothing
                ? Self.buildSmoothedGrid(raw: data.glucose,
                                         start: interval.start, end: interval.end,
                                         stepSec: candidateConfig.evalStep)
                : data.glucose
        }

        // simGlucose: the SIMULATOR substrate — what Loop's decision-time glucose
        // input, the counter trajectory, and the outcome stats actually run on.
        // Default: the same smoothed trace as physGlucose (legacy behavior). With
        // simRawGlucose: the simulator runs on the ORIGINAL (noisy) CGM samples
        // resampled onto physGlucose's EXACT timestamps — so the per-grid m(t)
        // and realPhysDelta arrays (indexed against physGlucose) stay aligned —
        // while physiology estimation keeps using the smoothed physGlucose. This
        // lets us estimate sensitivity in low-noise space but evaluate the
        // controller against the real noisy CGM it would actually see. Identity
        // holds: candidate doses == real ⇒ the counter reproduces whichever
        // substrate the sim runs on.
        let simGlucose: [EvalGlucoseSample] = (candidateConfig.kalmanSmoothing && candidateConfig.simRawGlucose)
            ? Self.rawGridMatching(grid: physGlucose, raw: data.glucose, unit: mgdlUnit)
            : physGlucose

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
        var baselineConfig = baselineConfig
        var candidateConfig = candidateConfig
        var counterfactualDoses: [EvalInsulinDose] = []
        counterfactualDoses.reserveCapacity(2048)
        // Stateful pump basal-pulse delivery for the candidate's temp-basal stream
        // (carries the sub-pulse remainder across steps, drops it only on a temp
        // re-issue at a new rate). Advanced exactly once per cfActive step.
        let candidateBasalAcc = PumpModel.BasalAccumulator(quantum: candidateConfig.basalPulseQuantum)
        // Loop temp basals carry a 30-min duration. Normally the next CGM cycle
        // (~5min) overwrites them so duration never bites. Across a CGM gap there
        // is no overwriting cycle, so the temp must EXPIRE at 30 min and revert to
        // scheduled basal (exactly like the real pump). Used to cap the candidate's
        // temp delivery on the long pre-gap step. (user, 2026-06-23)
        let tempBasalDuration: TimeInterval = 30 * 60
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
        // REAL IOB at each manual bolus (excluding the bolus itself), for IOB-aware passthrough.
        var realManualBolusRealIOB: [Double] = []
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
            // CF-IDENTITY: seed the candidate with the FULL real dose history
            // (whole window, not just burn-in), and below we skip the per-step
            // candidate append. The advance then runs on real doses ⇒
            // candPhys == realPhysDelta ⇒ counter == actual (the test).
            if cfIdentity {
                counterfactualDoses = data.doses.filter {
                    $0.endDate > warmupStart && $0.startDate < interval.end
                }
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

            // IOB-aware passthrough: precompute the REAL IOB the user faced at each manual bolus
            // (from the real deployed dose stream, excluding the bolus itself). Later the bolus is
            // resized by (candidate IOB − this), so a candidate carrying more IOB delivers less.
            if candidateConfig.iobAdjustManualBoluses && !realManualBoluses.isEmpty {
                let realAnnotated = data.doses.annotated(with: data.therapyTimeline.basal, fillBasalGaps: true)
                realManualBolusRealIOB = realManualBoluses.map { mb in
                    Swift.max(0, realAnnotated.insulinOnBoard(at: mb.startDate) - mb.volume)
                }
            }
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
        var realPhysDelta = [Double](repeating: 0, count: physGlucose.count)
        if counterfactualMode {
            let iceStart = Date()
            FileHandle.standardError.write(Data("Sim setup: doses=\(data.doses.count) glucose=\(physGlucose.count)\n".utf8))
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
                effectsFrom: physGlucose.first?.startDate.addingTimeInterval(-insulinModel.effectDuration),
                effectsTo: physGlucose.last?.startDate,
                useMidAbsorptionISF: true
            )
            let insulinEffects = precomp.insulinEffects ?? []
            FileHandle.standardError.write(Data("PrecomputedInsulinInput.build done in \(Int(Date().timeIntervalSince(iceStart) * 1000))ms (effects entries=\(insulinEffects.count))\n".utf8))
            realICE = physGlucose.counteractionEffects(to: insulinEffects)
            FileHandle.standardError.write(Data("ICE done (entries=\(realICE.count))\n".utf8))
            // realPhysDelta is the field's PHYSICAL active-insulin effect on the
            // single mid-abs ISF timeline. ALWAYS precompute it (not just for
            // infer-sensitivity): the counter advance now uses the ONE patient
            // model `realBGdelta + m·(candPhys − realPhysDelta)` for every CF
            // comparison, with m≡1 when sensitivity isn't inferred. This is the
            // single ISF timeline used symmetrically to remove field doses and
            // add candidate doses.
            do {
                let physStart = Date()
                for j in 1..<physGlucose.count {
                    realPhysDelta[j] = Self.physicalActiveEffectDelta(
                        doses: safeDataDoses, basal: data.therapyTimeline.basal,
                        sensitivity: physiologySensitivity,
                        from: physGlucose[j - 1].startDate, to: physGlucose[j].startDate,
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
        var mByIndex = [Double](repeating: 1.0, count: physGlucose.count)
        if counterfactualMode && inferSensitivity {
            let velEps = 1.0  // mg/dL of modeled insulin over the window; below this we can't identify m
            var kStart = 0
            for j in 0..<physGlucose.count {
                let tEnd = physGlucose[j].startDate
                let tStart = tEnd.addingTimeInterval(-inferSensitivityWindowSec)
                while kStart + 1 < physGlucose.count && physGlucose[kStart + 1].startDate <= tStart { kStart += 1 }
                if physGlucose[kStart].startDate > tStart || physGlucose[kStart].startDate >= tEnd { continue }
                let bgDeltaWindow = physGlucose[j].quantity.doubleValue(for: mgdlUnit)
                    - physGlucose[kStart].quantity.doubleValue(for: mgdlUnit)
                let iceWindow = Self.integrateICE(realICE, from: physGlucose[kStart].startDate, to: tEnd)
                if iceWindow < 0 {
                    let insReal = bgDeltaWindow - iceWindow  // modeled insulin effect (negative)
                    if insReal < -velEps {
                        mByIndex[j] = min(bgDeltaWindow / insReal, inferSensitivityMax)
                    }
                }
            }
            // SMOOTHING (optional, `inferSensitivitySmoothSec > 0`). Physiology
            // belief: insulin sensitivity is a SLOWLY-varying latent state, not a
            // per-step spike. The raw per-step m is noisy (it's solved
            // independently each step to exactly zero that step's residual).
            // Smooth it with a Gaussian over a `smoothSec` timescale.
            // CRUCIAL: steps with m≈1 are "carbs/EGP masked the signal — NO
            // INFO", not "sensitivity is exactly scheduled". So they are treated
            // as MISSING (excluded from the weighted mean), and the elevated
            // latent is carried THROUGH meal windows. Where no identified
            // observation falls within the kernel support, m relaxes to 1
            // (no evidence of elevated sensitivity). This is the "carry-latent"
            // (Policy B) smoother. Identity is unaffected (m drops out when
            // candidate ≡ real), so this is pure patient-model fidelity.
            //
            // SHRINKAGE TOWARD 1 (`inferSensitivitySmoothPrior > 0`): pure
            // carry-latent over-attributes — it holds the elevated estimate as
            // long as ANY drop is within the kernel, so elevated m spreads to
            // ~84% of steps on user1. Adding a prior pseudo-observation at m=1
            // with weight w_prior (in "equivalent observations") shrinks the
            // estimate back toward 1 where identified drops are sparse:
            //   m = (Σ_obs w_k·m_k + w_prior·1) / (Σ_obs w_k + w_prior)
            // Dense drops → elevated m survives; isolated drops → pulled to 1.
            // w_prior = 0 reproduces pure carry-latent. Tune against field lows.
            if inferSensitivitySmoothSec > 0 {
                let stepSec = candidateConfig.evalStep
                let sigmaSteps = (inferSensitivitySmoothSec / stepSec) / 2.355  // FWHM → σ
                let half = max(1, Int((3.0 * sigmaSteps).rounded(.up)))
                let wPrior = max(0.0, inferSensitivitySmoothPrior)
                let raw = mByIndex
                let obs = raw.map { $0 > 1.0001 }   // identified observations only
                var smoothed = [Double](repeating: 1.0, count: raw.count)
                for i in 0..<raw.count {
                    let lo = max(0, i - half), hi = min(raw.count - 1, i + half)
                    var wsum = wPrior, vsum = wPrior   // prior pseudo-obs at m=1
                    var k = lo
                    while k <= hi {
                        if obs[k] {
                            let d = Double(k - i) / sigmaSteps
                            let w = exp(-0.5 * d * d)
                            wsum += w; vsum += w * raw[k]
                        }
                        k += 1
                    }
                    smoothed[i] = wsum > 0 ? min(vsum / wsum, inferSensitivityMax) : 1.0
                }
                mByIndex = smoothed
                FileHandle.standardError.write(Data("sensitivity-inference: smoothed m over \(Int(inferSensitivitySmoothSec/60))min (σ=\(String(format: "%.1f", sigmaSteps)) steps, prior=\(String(format: "%.1f", wPrior)))\n".utf8))
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
                csv.reserveCapacity(physGlucose.count * 48)
                for i in 1..<physGlucose.count {
                    let bgPrev = physGlucose[i - 1].quantity.doubleValue(for: mgdlUnit)
                    let bgNow = physGlucose[i].quantity.doubleValue(for: mgdlUnit)
                    let nie = (bgNow - bgPrev) - mByIndex[i] * realPhysDelta[i]
                    csv += "\(isoFmt.string(from: physGlucose[i].startDate)),\(nie),\(mByIndex[i]),\(bgNow)\n"
                }
                try? csv.write(toFile: dumpPath, atomically: true, encoding: .utf8)
                FileHandle.standardError.write(Data("dumped NIE/m → \(dumpPath) (\(physGlucose.count - 1) rows)\n".utf8))
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

        // Candidate carbs, optionally with each entry's absorptionTime capped
        // (diagnostic: raises the modeled absorption-rate ceiling — see
        // EvalConfig.carbAbsorptionTimeCapSec). Baseline always uses real carbs.
        let candidateCarbs: [EvalCarbEntry] = {
            let cap = candidateConfig.carbAbsorptionTimeCapSec
            guard cap > 0 else { return data.carbs }
            return data.carbs.map { c in
                var c2 = c
                let cur = c.absorptionTime ?? TimeInterval(3 * 3600)
                c2.absorptionTime = Swift.min(cur, cap)
                return c2
            }
        }()

        // Cross-cycle sensitive-mode level (EvalConfig.sensitiveMode*): EWMA of recent
        // NEGATIVE discrepancies that raises effective ISF on future cycles to prevent a
        // delayed second low. Off when tau==0 or gain==0.
        let sensModeDecay = candidateConfig.sensitiveModeTauSec > 0
            ? exp(-candidateConfig.evalStep / candidateConfig.sensitiveModeTauSec) : 0.0
        let sensModeOn = candidateConfig.sensitiveModeTauSec > 0 && candidateConfig.sensitiveModeGain > 0
        var sensModeLevel = 0.0

        // STEP TIMES. CGM-driven: one step per real CGM sample in the eval window
        // (irregular cadence). Default: the regular evalStep grid (stepDur ≡
        // evalStep ⇒ byte-identical to the legacy march). stepDur is the interval
        // to the NEXT step and is used wherever a step duration appears (scheduled
        // basal delivered, the candidate temp segment, the manual-bolus window,
        // sensitive-mode decay). A gap (stepDur ≫ evalStep) is capped for delivery
        // so a long CGM outage doesn't issue one giant temp.
        var stepTimes: [Date] = []
        if !decisionTimes.isEmpty {
            stepTimes = decisionTimes.sorted().filter { $0 >= evalStart && $0 <= interval.end }
        } else if decisionsFromCgm {
            stepTimes = simGlucose.map { $0.startDate }.filter { $0 >= evalStart && $0 <= interval.end }
        } else {
            var tt = evalStart
            while tt <= interval.end { stepTimes.append(tt); tt = tt.addingTimeInterval(candidateConfig.evalStep) }
        }
        let nSteps = stepTimes.count

        // Deployed timeBasedDoseApplicationFactor reference: the last COMPLETED loop
        // (errored/guard-skipped cycles don't advance it).
        var lastCompletedLoopT: Date? = nil
        for stepIdx in 0..<nSteps {
            let t = stepTimes[stepIdx]
            // Interval to the next decision (= next CGM in CGM-driven mode).
            let stepEnd = stepIdx + 1 < nSteps
                ? stepTimes[stepIdx + 1]
                : t.addingTimeInterval(candidateConfig.evalStep)
            let stepDur = max(1.0, stepEnd.timeIntervalSince(t))
            // Per-cycle dosing strategy (mixed-strategy donors).
            if !tempStrategyTimes.isEmpty {
                let tempMode = tempStrategyTimes.contains(t)
                baselineConfig.useTempBasalStrategy = tempMode
                candidateConfig.useTempBasalStrategy = tempMode
            }
            // Scheduled basal delivered over the actual interval (over a CGM gap,
            // scheduled basal really did run, so stepDur is correct). In default
            // mode stepDur == evalStep so every duration below is byte-identical.
            // Per-step sensitive-mode decay (default mode: stepDur == evalStep ⇒
            // equals the hoisted sensModeDecay constant).
            let sensModeDecayStep = candidateConfig.sensitiveModeTauSec > 0
                ? exp(-stepDur / candidateConfig.sensitiveModeTauSec) : 0.0
            _ = sensModeDecay  // hoisted constant kept for reference; per-step value used below
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
                        while nextManualIdx < realManualBoluses.count {
                            let mb = realManualBoluses[nextManualIdx]
                            if mb.startDate >= stepEnd { break }
                            if mb.startDate >= t { counterfactualDoses.append(mb) }
                            nextManualIdx += 1
                        }
                    }
                    continue
                }
            }

            // ----- FIELD NO-DOSE GUARD -----
            // The deployed controller ran this cycle but refused to dose on stale
            // inputs (pumpDataTooOld / glucoseTooOld): no forecast, no recommendation
            // stored. Skip the step exactly like a stale-CGM cycle — no dose, no
            // prediction point — so "recommended nothing" matches on both sides and
            // a closed-loop counterfactual doesn't dose through the same exogenous
            // pump-comms failure.
            if noDoseGuardTimes.contains(t) {
                if counterfactualMode && t >= cfActiveStart {
                    while nextManualIdx < realManualBoluses.count {
                        let mb = realManualBoluses[nextManualIdx]
                        if mb.startDate >= stepEnd { break }
                        if mb.startDate >= t { counterfactualDoses.append(mb) }
                        nextManualIdx += 1
                    }
                }
                continue
            }

            // Deployed timeBasedDoseApplicationFactor = min(1, sinceLastCompleted/5min):
            // a loop firing < 5 min after a COMPLETED loop applies proportionally less
            // of the correction (sub-5-min retries after FAILURES are not damped —
            // lastLoopCompleted doesn't advance on error). Completed here = the cycle
            // ran and wasn't inside a pump-error window.
            let timeBasedAFScale: Double = enableTimeBasedAF
                ? (lastCompletedLoopT.map { Swift.min(1.0, Swift.max(0.0, t.timeIntervalSince($0)) / 300.0) } ?? 1.0)
                : 1.0
            let stepCompletedLoop = outages.containing(t)?.reason != "pump_error"
            if stepCompletedLoop { lastCompletedLoopT = t }

            // ----- BASELINE step: actual glucose, actual doses, baselineConfig.
            // Apply sensor cap: real CGMs (Dexcom G6/G7, Libre) peg at ~400 mg/dL,
            // so the controller never sees BG above the cap. The counter / scoring
            // still uses uncapped values. When sensorCapMgdl <= 0, no cap is applied.
            let baselineGlucose = sensorCapMgdl > 0
                ? Self.capGlucoseToSensor(simGlucose, capMgdl: sensorCapMgdl, unit: mgdlUnit)
                : simGlucose
            let baselineBuilder = InputWindowBuilder(
                glucose: baselineGlucose,
                doses: data.doses,
                carbs: suppressCarbs ? [] : data.carbs,
                therapyTimeline: data.therapyTimeline,
                config: baselineConfig
            )
            var baselineDose: Double
            var baselineTempAction = "set"
            var baselineEventualBG = Double.nan
            var baselineIOB = Double.nan
            var baselineCOB = Double.nan
            var baselineMomentum = Double.nan
            var baselineRC = Double.nan
            var baselineDiscrepancy = Double.nan
            var baselinePredCurve: [Double] = []
            if let baselineInput = baselineBuilder.buildInput(at: t, decisionAnchor: t) {
                let br = baselineEngine.step(EngineStepRequest(
                    t: t,
                    input: baselineInput,
                    config: baselineConfig,
                    therapy: data.therapyTimeline,
                    glucoseMgdl: baselineMgdl,
                    glucoseSamples: simGlucose,
                    tddDoses: data.doses,
                    orefPumpHistoryDoses: data.doses,
                    timeBasedAFScale: timeBasedAFScale
                ))
                baselineDose = br.dose
                baselineTempAction = br.tempAction
                baselineEventualBG = br.prediction.glucose.last?.quantity.doubleValue(for: mgdlUnit) ?? .nan
                if baselineConfig.exportForecastCurve {
                    baselinePredCurve = br.prediction.glucose.map { $0.quantity.doubleValue(for: mgdlUnit) }
                }
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
                // Per-component forecast dump (diagnostic): FORECAST_COMPONENT_DUMP=<ISO-date-prefix>
                // dumps, for each cycle whose timestamp starts with that prefix, the total forecast
                // plus each component's ISOLATED contribution curve (predictGlucose with only that
                // effect), 5-min spaced from t, as one JSON line to stderr. Run the FULL window for
                // faithful IOB/RC state; the date filter limits output to the cycles under study.
                if let ddate = ProcessInfo.processInfo.environment["FORECAST_COMPONENT_DUMP"],
                   Self.isoNoFrac.string(from: t).hasPrefix(ddate),
                   let startG = br.prediction.glucose.first {
                    let eff = br.prediction.effects
                    func comp(_ mom: [GlucoseEffect], _ effs: [[GlucoseEffect]]) -> [Double] {
                        LoopMath.predictGlucose(startingAt: startG, momentum: mom, effects: effs.filter { !$0.isEmpty })
                            .map { ($0.quantity.doubleValue(for: mgdlUnit) * 10).rounded() / 10 }
                    }
                    let obj: [String: Any] = [
                        "t": Self.isoNoFrac.string(from: t),
                        "full": comp(eff.momentum, [eff.insulin, eff.carbs, eff.retrospectiveCorrection]),
                        "mom":  comp(eff.momentum, []),
                        "ins":  comp([], [eff.insulin]),
                        "carb": comp([], [eff.carbs]),
                        "rc":   comp([], [eff.retrospectiveCorrection]),
                    ]
                    if let d = try? JSONSerialization.data(withJSONObject: obj) {
                        FileHandle.standardError.write(d); FileHandle.standardError.write(Data("\n".utf8))
                    }
                }
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
            if decisionTimeReplay {
                combinedDoses = data.doses                 // identical real insulin history
            } else if counterfactualMode {
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
                    trendRate: s.trendRate,
                    receivedDate: s.receivedDate
                )
            }
            // Sensor cap (Dexcom-like 400) applied to what the candidate algorithm
            // sees. counterSamples / counterMgdl remain uncapped for advance + scoring.
            let candidateSensorSamples = decisionTimeReplay
                ? baselineGlucose                          // identical real glucose the baseline sees
                : (sensorCapMgdl > 0
                    ? Self.capGlucoseToSensor(counterSamples, capMgdl: sensorCapMgdl, unit: mgdlUnit)
                    : counterSamples)
            let candidateBuilder = InputWindowBuilder(
                glucose: candidateSensorSamples,
                doses: combinedDoses,
                carbs: suppressCarbs ? [] : candidateCarbs,
                therapyTimeline: data.therapyTimeline,
                config: candidateConfig
            )
            guard let candidateInput = candidateBuilder.buildInput(at: t, decisionAnchor: t) else {
                continue
            }
            // ----- CANDIDATE step: candidate's Loop sees the per-step ISF
            // schedule (if any) and emits a dose.
            var candidateDose: Double
            var candidateBolus: Double
            var candidateManualBolusRec = Double.nan
            var candidateTempRate: Double
            var candidateTempAction = "set"
            var candidateEventualBG = Double.nan
            var candidateIOB = Double.nan
            var candidateCOB = Double.nan
            var candidateMomentum = Double.nan
            var candidateRC = Double.nan
            var candidateMomentumMarginal = Double.nan
            var candidateRCMarginal = Double.nan
            var candidateAutosensRatio = Double.nan
            var candidateMinGuardBG = Double.nan
            var candidateMinPredBG = Double.nan
            var candidateICE = Double.nan
            var candidateCarbEffect = Double.nan
            var candidateDiscrepancy = Double.nan
            var candidateSensModeMult = Double.nan
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
                // Cross-cycle sensitive-mode ISF bump (>=1 damp; always safe to apply).
                let sensModeMult = sensModeOn ? Swift.min(2.0, 1.0 + candidateConfig.sensitiveModeGain * sensModeLevel) : 1.0
                candidateSensModeMult = sensModeMult
                // ICE RISE-BOOST (rise side of the unified ICE-response term): attack a
                // SUSTAINED, actively-driven high. A positive forecast offset when BG is
                // high AND the trailing ICE rate is positive (BG being pushed up = a real
                // persistent high, not a resolving spike). Skips transient/resolving highs
                // (where uniform GBAF causes lows). Forecast-side (§2). Causal: trailing
                // ICE uses only past samples.
                var iceRiseBoostOffset = 0.0
                // ANTICIPATION forecast offset (per-step, from the meal-anticipation
                // predictor CSV): a positive BG offset added to Loop's forecast so it
                // pre-doses for predicted-but-unannounced carb pressure. Forecast-side
                // (§2). Values already scaled conservatively by the CSV producer.
                let anticipationOffset: Double = {
                    guard let om = forecastOffsetByStep, !om.isEmpty else { return 0.0 }
                    let r = Date(timeIntervalSince1970:
                        (t.timeIntervalSince1970 / candidateConfig.evalStep).rounded() * candidateConfig.evalStep)
                    return om[r] ?? 0.0
                }()
                // ISF-fade: scale the boost gain by aggressiveness so the high-attack
                // auto-disables (→ pure smairc) as the lows budget tightens (ISF rises).
                var iceRiseBoostGainEff = candidateConfig.iceRiseBoostGain
                if candidateConfig.iceRiseBoostIsfFadeHi > candidateConfig.iceRiseBoostIsfFadeLo {
                    let isfM = candidateConfig.sensitivityMultiplier
                    let fade = Swift.max(0.0, Swift.min(1.0,
                        (candidateConfig.iceRiseBoostIsfFadeHi - isfM)
                        / (candidateConfig.iceRiseBoostIsfFadeHi - candidateConfig.iceRiseBoostIsfFadeLo)))
                    iceRiseBoostGainEff *= fade
                }
                if iceRiseBoostGainEff > 0 {
                    let bIdx = Self.latestGlucoseIndex(at: t, in: counterGlucose)
                    let curBgRB = counterMgdl[bIdx]
                    let lo = candidateConfig.iceRiseBoostBgLo, hi = candidateConfig.iceRiseBoostBgHi
                    let gate = hi > lo ? Swift.max(0.0, Swift.min(1.0, (curBgRB - lo) / (hi - lo)))
                                       : (curBgRB >= hi ? 1.0 : 0.0)
                    if gate > 0 {
                        let tau = candidateConfig.iceRiseBoostTauSec
                        let iceRate = Self.integrateICE(realICE, from: t.addingTimeInterval(-tau), to: t) / (tau / 60.0)
                        let driven = Swift.max(0.0, iceRate - candidateConfig.iceRiseBoostThresh)
                        iceRiseBoostOffset = iceRiseBoostGainEff * gate * driven
                        // Lows-coupling (unification): damp the high-attack when recently
                        // sensitive (sensMode level R elevated) — don't attack a high that
                        // may flip into a low. R is the same negative-ICE memory sensMode uses.
                        if candidateConfig.iceRiseBoostSensSuppress > 0 {
                            iceRiseBoostOffset *= Swift.max(0.0, 1.0 - candidateConfig.iceRiseBoostSensSuppress * sensModeLevel)
                        }
                    }
                }
                // Decision-time replay: candidate momentum/velocity reads the SAME real
                // glucose the baseline saw (not the counter trajectory).
                let candMomentumMgdl = decisionTimeReplay ? baselineMgdl : counterMgdl
                let candMomentumSamples = decisionTimeReplay ? simGlucose : counterGlucose
                // oref pump-history window (24h) for autosens: combinedDoses only reaches
                // back to warmupStart (evalStart - activityDuration), which for a cycle
                // early in the eval is < 24h. Before the candidate went active it used
                // REAL insulin, so prepend the real doses older than the candidate's
                // earliest entry to complete the 24h window (data.doses spans the full run).
                let orefHistDoses: [EvalInsulinDose]
                if let earliest = combinedDoses.first?.startDate {
                    orefHistDoses = EvaluationEngine.mergeSorted(
                        data.doses.filter { $0.startDate < earliest }, combinedDoses)
                } else {
                    orefHistDoses = data.doses
                }
                func doStep(_ map: [Date: Double]?) -> EngineStepResult {
                    candidateEngine.step(EngineStepRequest(
                        t: t, input: candidateInput, config: candidateConfig,
                        therapy: data.therapyTimeline, glucoseMgdl: candMomentumMgdl,
                        glucoseSamples: candMomentumSamples,
                        extraISFMultiplier: sensModeMult,
                        forecastOffsetMgdl: iceRiseBoostOffset + anticipationOffset,
                        perStepIsfMultByTime: map,
                        isfBoostActiveOnly: isfBoostActiveOnly,
                        egpPhysicalDecomposition: egpPhysicalDecomposition,
                        tddDoses: data.doses,
                        orefPumpHistoryDoses: orefHistDoses,
                        timeBasedAFScale: timeBasedAFScale))
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
                let result: EngineStepResult
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
                candidateManualBolusRec = result.manualBolusRec
                candidateTempRate = result.tempRate
                candidateTempAction = result.tempAction
                // Manual-bolus recommendation, same-transaction carb relaxation:
                // if this step contains a real manual bolus that was co-entered with a
                // carb (entry within ±carbTol of the bolus, and the bolus covers >=50%
                // of carbs/CR — i.e. a meal bolus), recompute the candidate's manual-bolus
                // recommendation with that carb made visible (entryDate just past the step
                // base would otherwise hide it). Manual-bolus path ONLY; auto-dosing above
                // stays strictly causal. No-op unless manualBolusFromRecommendation is on.
                if candidateConfig.manualBolusFromRecommendation && !realManualBoluses.isEmpty && !suppressCarbs {
                    let carbTol: TimeInterval = 30
                    let mbStepEnd = stepEnd
                    // first real manual bolus landing in this step
                    let mbHere: EvalInsulinDose? = realManualBoluses[nextManualIdx...].first(where: { $0.startDate >= t && $0.startDate < mbStepEnd })
                    if let mb = mbHere {
                        let visCut = mb.startDate.addingTimeInterval(carbTol)
                        let cr: Double = candidateInput.carbRatio.closestPrior(to: mb.startDate)?.value ?? 0
                        // a carb co-entered with this bolus but not yet visible at the step base,
                        // where the bolus covers >=50% of carbs/CR (i.e. it was a meal bolus)
                        // Use the TRUE entry time (entryDate, ObjectId) — the carb was
                        // co-logged with the bolus even though its normal-dosing gate
                        // (dosingVisibleDate) is deferred past it. Fire only if it's hidden
                        // at the step base (entryDate > t), within carbTol of the bolus, and
                        // the bolus covers >=50% of carbs/CR (a meal bolus).
                        var coEntered = false
                        for c in candidateCarbs {
                            let g: Double = c.quantity.doubleValue(for: LoopUnit.gram)
                            let dt: TimeInterval = abs(c.entryDate.timeIntervalSince(mb.startDate))
                            if c.entryDate > t && c.entryDate <= visCut && dt <= carbTol
                                && cr > 0 && g > 0 && mb.volume >= 0.5 * (g / cr) {
                                coEntered = true; break
                            }
                        }
                        if coEntered,
                           let relaxedInput = candidateBuilder.buildInput(at: t, carbVisibilityCutoff: visCut, decisionAnchor: t) {
                            let rr = EvaluationEngine.simStepDose(
                                t: t, input: relaxedInput, config: candidateConfig,
                                therapy: data.therapyTimeline, glucoseMgdl: candMomentumMgdl,
                                glucoseSamples: candMomentumSamples,
                                extraISFMultiplier: sensModeMult,
                                perStepIsfMultByTime: csvIsfEnabled ? perStepMapForLoop : nil,
                                isfBoostActiveOnly: isfBoostActiveOnly,
                                egpPhysicalDecomposition: egpPhysicalDecomposition)
                            candidateManualBolusRec = rr.manualBolusRec
                        }
                    }
                }
                candidateEventualBG = result.prediction.glucose.last?.quantity.doubleValue(for: mgdlUnit) ?? .nan
                candidateIOB = result.prediction.activeInsulin ?? .nan
                candidateCOB = result.prediction.activeCarbs ?? .nan
                func netEff(_ a: [GlucoseEffect]) -> Double {
                    guard let f = a.first, let l = a.last else { return 0.0 }
                    return l.quantity.doubleValue(for: mgdlUnit) - f.quantity.doubleValue(for: mgdlUnit)
                }
                candidateMomentum = netEff(result.prediction.effects.momentum)
                candidateRC = netEff(result.prediction.effects.retrospectiveCorrection)
                // MARGINAL contributions to eventualBG: recompute the forecast with the
                // component removed and diff the endpoint. This accounts for Loop's
                // momentum blend (LoopMath.predictGlucose blends momentum against the
                // sum of the other effects over the first 15 min) — so if the other
                // terms already imply the same near-term slope, momentum's marginal is
                // ~0 even though its isolated net is non-zero.
                if let startG = result.prediction.glucose.first {
                    let eff = result.prediction.effects
                    let withEventual = result.prediction.glucose.last?.quantity.doubleValue(for: mgdlUnit) ?? .nan
                    var nonMom: [[GlucoseEffect]] = []
                    if !eff.insulin.isEmpty { nonMom.append(eff.insulin) }
                    if !eff.carbs.isEmpty { nonMom.append(eff.carbs) }
                    if !eff.retrospectiveCorrection.isEmpty { nonMom.append(eff.retrospectiveCorrection) }
                    if !eff.momentum.isEmpty {
                        let woMom = LoopMath.predictGlucose(startingAt: startG, momentum: [], effects: nonMom)
                            .last?.quantity.doubleValue(for: mgdlUnit) ?? .nan
                        candidateMomentumMarginal = withEventual - woMom
                    }
                    if !eff.retrospectiveCorrection.isEmpty {
                        var noRC: [[GlucoseEffect]] = []
                        if !eff.insulin.isEmpty { noRC.append(eff.insulin) }
                        if !eff.carbs.isEmpty { noRC.append(eff.carbs) }
                        let woRC = LoopMath.predictGlucose(startingAt: startG, momentum: eff.momentum, effects: noRC)
                            .last?.quantity.doubleValue(for: mgdlUnit) ?? .nan
                        candidateRCMarginal = withEventual - woRC
                    }
                }
                candidateAutosensRatio = result.autosensRatio ?? .nan
                candidateMinGuardBG = result.minGuardBG ?? .nan
                candidateMinPredBG = result.minPredBG ?? .nan
                // TEMP DEBUG (minPredBG dig): dump oref reason for 06-09 cycles.
                if ProcessInfo.processInfo.environment["OREF_REASON_DUMP"] != nil,
                   let rsn = result.reason {
                    FileHandle.standardError.write(Data("RSN \(t) | \(rsn)\n".utf8))
                }
                // ICE→carb/RC split over the interval ENDING at the decision time t.
                // Read the carb attribution AUTHORITATIVELY from the carbEffects curve
                // (effects.carbs = the same cumulative curve subtracted to form RC), and ICE
                // from the counteraction curve — both matched to t. carbEffect = Δ(carbs) over
                // [t−Δ, t]; discrepancy (→RC) = ICE − carbEffect. (Deriving carbEffect as
                // ICE − model.discrepancy is unreliable: LoopMath.subtracting normalizes ICE to
                // a fixed 5-min effectInterval and trims to the carb grid, so its per-interval
                // discrepancy can exceed the raw ICE and flip the implied carb share negative.)
                let ceff = result.prediction.effects
                let tEps = t.addingTimeInterval(1)
                if let ki = ceff.carbs.lastIndex(where: { $0.startDate <= tEps }), ki > ceff.carbs.startIndex {
                    candidateCarbEffect = ceff.carbs[ki].quantity.doubleValue(for: mgdlUnit)
                        - ceff.carbs[ki - 1].quantity.doubleValue(for: mgdlUnit)
                }
                if let iceM = ceff.insulinCounteraction.last(where: { $0.endDate <= tEps }) {
                    candidateICE = iceM.effect.quantity.doubleValue(for: mgdlUnit)
                }
                if candidateICE.isFinite && candidateCarbEffect.isFinite {
                    candidateDiscrepancy = candidateICE - candidateCarbEffect
                }
                // Feed the sensitive-mode level: EWMA of the NEGATIVE part of this
                // step's discrepancy (mg/dL). Decays with sensitiveModeTauSec; raises ISF on
                // future steps via sensModeMult above (causal: this update affects t+1 onward).
                if sensModeOn && candidateDiscrepancy.isFinite {
                    sensModeLevel = sensModeDecayStep * sensModeLevel + (1.0 - sensModeDecayStep) * Swift.max(0.0, -candidateDiscrepancy)
                }
            }

            // ----- DELIVERABILITY / DATA-AVAILABILITY CLAMPS -----
            // Two structurally different conditions can override the sim's
            // dose decision at step t. Pump outage takes precedence over a
            // CGM gap (if the pump is physically off, CGM staleness is moot).
            let outageNow = outages.isEmpty ? nil : outages.containing(t)
            let basalContinues = outageNow.map { outageBasalContinuesReasons.contains($0.reason) } ?? false
            let inOutage = outageNow != nil && !basalContinues

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

            if inOutage && !decisionTimeReplay {
                // Physical pump outage: absolute delivery = 0. Real Loop's
                // recorded auto-deliveries during outages are already 0 (Loop
                // wrote 0 U/hr temps after pump failure), so real-pump
                // quantities (realPumpAutoAtStep, the ICE pipeline) need no
                // adjustment — only the simulator's own decisions do.
                //
                // DTR is exempt: nothing is ever delivered in decision-time
                // replay, so this clamp only ERASES the recommendation — and
                // the field records its recommendation during pump errors too
                // (bddp11 07-03 22:00-22:10: Loop recommended 0.25/0.35/0.15
                // through "Pod not connected" cycles while our clamp zeroed
                // ours, a fake three-cycle dose mismatch on an exactly-matched
                // forecast). Rec-vs-rec comparison needs both sides' outputs;
                // dose-vs-DELIVERED scoring already excludes clamped windows.
                let schedRate = data.therapyTimeline.basal.first(where: {
                    $0.startDate <= t && $0.endDate > t
                })?.value ?? data.therapyTimeline.basal.closestPrior(to: t)?.value ?? 0
                let schedStepU = schedRate * stepDur / 3600.0
                // absolute delivery = scheduled_step + dose; want absolute = 0.
                candidateDose = -schedStepU
                baselineDose = -schedStepU
                candidateBolus = 0
                candidateTempRate = 0
            } else if cgmStale || basalContinues {
                // CGM gap (or loop-offline gap): no NEW dose adjustment, scheduled basal continues.
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
            // Candidate's actual absolute delivery this cfActive step (pump basal
            // pulses for the temp-basal stream + auto-bolus). Computed ONCE here via
            // the stateful accumulator and reused for the counterfactualDoses append
            // below (so the deltaDose report and the counter physics never diverge).
            var cfAbsoluteDelivery: Double = 0
            // Split of the candidate's basal delivery for the counterfactualDoses
            // record: a temp segment [t, cfTempSegEnd] (the 30-min temp + auto-bolus)
            // and, only when the step spans longer than the temp duration (a CGM
            // gap), a SCHEDULED-basal remainder [cfTempSegEnd, stepEnd] (net-zero
            // IOB) so the candidate tracks the real pump through the gap.
            var cfTempVolume: Double = 0
            var cfSchedRemainderU: Double = 0
            var cfTempSegEnd: Date = stepEnd
            let deltaDose: Double
            if cfActive {
                // Temp basal expires after its 30-min duration. For a normal step
                // (stepDur ≤ 30min) tempSec == stepDur and this is unchanged. For a
                // long pre-gap step (stepDur ≫ 30min) the temp runs only 30 min,
                // then scheduled basal resumes — preventing a pre-gap suspend from
                // delivering 0 for the whole multi-hour gap (counter runaway).
                let tempSec = min(stepDur, tempBasalDuration)
                cfTempSegEnd = t.addingTimeInterval(tempSec)
                // Pump basal-pulse delivery for the temp RATE over its live window.
                // The accumulator carries the sub-pulse remainder while the rate is
                // unchanged and drops the in-progress pulse on a temp re-issue
                // (rate change) — reproducing the field ~1.1 U/day below rate×time.
                let basalDelivered = candidateBasalAcc.deliver(rate: candidateTempRate, seconds: tempSec)
                // Auto-bolus already floored to the bolus grid; delivered whole.
                cfTempVolume = basalDelivered + candidateBolus
                if stepDur > tempBasalDuration {
                    // Temp expired mid-step: scheduled basal for the remainder.
                    cfSchedRemainderU = Self.integrateScheduledBasal(
                        data.therapyTimeline.basal, from: cfTempSegEnd, to: stepEnd)
                }
                cfAbsoluteDelivery = cfTempVolume + cfSchedRemainderU
                // Use AUTO-ONLY real pump as the baseline. Manual boluses are
                // passed through (preserved in candidate's dose history) so
                // they cancel out and don't perturb counter_BG.
                let realPumpAutoAtStep = realAutoOnlyPerStep[t] ?? 0
                deltaDose = cfAbsoluteDelivery - realPumpAutoAtStep
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
              // CF-IDENTITY: skip the candidate's own dose append entirely;
              // counterfactualDoses was pre-seeded with the full REAL history.
              // The physiological advance below still runs, on real doses.
              if !cfIdentity {
                // Candidate's actual absolute delivery this step (pump basal pulses
                // + auto-bolus) — computed once above via the stateful accumulator.
                // Record as a TEMP BASAL segment, NOT a bolus.
                // LoopAlgorithm's IOB pipeline computes `netBasalUnits = volume
                // - scheduledRate × duration` for basal segments. Recording each
                // step as a .bolus would inflate IOB by the scheduled-basal
                // contribution that should be neutral (a 6h DIA pumping
                // 0.7 U/hr scheduled basal would accumulate ~2 U of spurious
                // "phantom IOB" — sim Loop then forecasts BG dropping and
                // suspends inappropriately). Bug found 2026-05-18.
                // The temp covers only [t, cfTempSegEnd] (≤30min); across a CGM gap
                // a second SCHEDULED-basal segment covers the remainder so the temp
                // doesn't run for the whole gap (net-zero, tracks the real pump).
                counterfactualDoses.append(EvalInsulinDose(
                    deliveryType: .basal,
                    startDate: t,
                    endDate: cfTempSegEnd,
                    volume: cfTempVolume,
                    insulinType: data.therapyTimeline.insulinType,
                    automatic: true
                ))
                if cfTempSegEnd < stepEnd {
                    counterfactualDoses.append(EvalInsulinDose(
                        deliveryType: .basal,
                        startDate: cfTempSegEnd,
                        endDate: stepEnd,
                        volume: cfSchedRemainderU,
                        insulinType: data.therapyTimeline.insulinType,
                        automatic: true
                    ))
                }
                // Pass through any user-initiated manual boluses falling in
                // [t, t + stepSec). Preserves user behavior on top of the
                // candidate's algorithmic decisions. (stepEnd hoisted above.)
                // Candidate insulin already committed THIS cycle before the manual bolus is
                // delivered: the auto-dose (candidateDose, issued at step start) plus any earlier
                // manual boluses passed through this same step. The manual-bolus IOB adjustment
                // must see this — using the step-start IOB alone ignores the candidate's own
                // same-cycle auto-bolus and would mis-size (even up-size) the manual bolus.
                var stepCandidateAdded = candidateDose
                var recUsedThisStep = false
                while nextManualIdx < realManualBoluses.count {
                    let mb = realManualBoluses[nextManualIdx]
                    if mb.startDate >= stepEnd { break }
                    if mb.startDate >= t {
                        if candidateConfig.manualBolusFromRecommendation {
                            // Replace the user's manual bolus with the candidate algorithm's OWN
                            // recommended manual bolus at this step (full correction vs its own
                            // forecast/IOB) — self-consistent, so no IOB-divergence amplification.
                            // One recommendation per step: first manual event takes it; any further
                            // events in the same step are already covered (deliver 0).
                            let rec = (!recUsedThisStep && candidateManualBolusRec.isFinite)
                                ? candidateManualBolusRec * candidateConfig.manualBolusRecScale : 0.0
                            recUsedThisStep = true
                            stepCandidateAdded += rec
                            counterfactualDoses.append(EvalInsulinDose(
                                deliveryType: mb.deliveryType, startDate: mb.startDate, endDate: mb.endDate,
                                volume: rec, insulinType: mb.insulinType, automatic: mb.automatic))
                        } else if candidateConfig.iobAdjustManualBoluses
                            && nextManualIdx < realManualBolusRealIOB.count
                            && candidateIOB.isFinite {
                            // x - (z - y): resize by the counterfactual-vs-real IOB difference,
                            // where z is the candidate IOB at the MOMENT of the bolus (step-start
                            // IOB + this cycle's own committed insulin).
                            let y = realManualBolusRealIOB[nextManualIdx]
                            let z = candidateIOB + stepCandidateAdded
                            let adj = Swift.max(0, Swift.min(data.therapyTimeline.maxBolus, mb.volume - (z - y)))
                            stepCandidateAdded += adj
                            counterfactualDoses.append(EvalInsulinDose(
                                deliveryType: mb.deliveryType, startDate: mb.startDate, endDate: mb.endDate,
                                volume: adj, insulinType: mb.insulinType, automatic: mb.automatic))
                        } else {
                            stepCandidateAdded += mb.volume
                            counterfactualDoses.append(mb)
                        }
                    }
                    nextManualIdx += 1
                }
              } // end !cfIdentity (skip candidate dose append in identity mode)

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
                    // SINGLE PATIENT MODEL (used for EVERY CF comparison and for
                    // --cf-identity). The advance is always the PHYSICAL /
                    // EGP-separated form on ONE mid-abs ISF timeline:
                    //   stepDelta = realBGdelta + m·(E(candidate) − E(field))
                    // where E(·) = physicalActiveEffectDelta (mid-abs ISF, EGP
                    // credit zeroed) and m = mByIndex (≡1 unless sensitivity is
                    // inferred). realBGdelta carries ALL non-insulin physiology
                    // (incl. EGP) UNSCALED, so m never magnifies EGP and a
                    // candidate that suspends into sub-basal just removes
                    // m·(the cut) of lowering while the real unscaled EGP carries
                    // BG back up. The SAME E(·) removes field doses (realPhysDelta)
                    // and adds candidate doses (candPhys) — one ISF timeline, both
                    // directions. Identity: candidate doses == real ⇒
                    // candPhys == realPhysDelta ⇒ counter reproduces the substrate.
                    let realBGdelta = counterGlucose[advIdx].quantity.doubleValue(for: mgdlUnit)
                        - counterGlucose[prevIdx].quantity.doubleValue(for: mgdlUnit)
                    let candPhys = Self.physicalActiveEffectDelta(
                        doses: counterfactualDoses,
                        basal: data.therapyTimeline.basal,
                        sensitivity: physiologySensitivity,
                        from: prevT, to: nextT,
                        insulinModel: insulinModel)
                    let m = mByIndex[advIdx]
                    let stepDelta = realBGdelta + m * (candPhys - realPhysDelta[advIdx])
                    // Counter-regulation: as counter_BG falls below the onset
                    // threshold the body defends with surging hepatic glucose
                    // output (glucagon/epinephrine) — a positive BG VELOCITY that
                    // ramps with depth below onset, capped. Because it is a
                    // velocity, it must integrate at the per-step cadence: a single
                    // advance that spans a skipped CGM gap (prevT..nextT can be
                    // 15-25 min, not 5) would otherwise multiply the velocity by the
                    // whole gap and inject a spurious BG jump on gap-close (the real
                    // recovery is already in baseDelta). Subdivide into <=1-step
                    // sub-intervals: distribute baseDelta linearly and recompute the
                    // counter-reg term against the rising counter level each
                    // sub-step (it stops once the level climbs back above onset).
                    // For a normal 5-min step nSub==1 and this reproduces the prior
                    // arithmetic exactly (identity preserved).
                    // INCREMENTAL counter-regulation. Like insulin and ICE, the
                    // counter-reg defense is applied as a DIFFERENCE from the real
                    // trajectory: realBGdelta already carries the real body's
                    // counter-regulation at the real lows, so adding the absolute
                    // defense counterreg(counter) on top would DOUBLE-COUNT it (and
                    // breaks the identity: candidate==real would then push counter
                    // above actual at every low). Instead add
                    //   counterreg(counter_BG) − counterreg(actual_BG)
                    // so at identity (counter==actual) the term is 0; a counter that
                    // goes genuinely LOWER than actual gets the EXTRA defense; a
                    // counter that ends HIGHER sheds the real-low defense it wrongly
                    // inherited via realBGdelta. actual_BG is the real substrate the
                    // advance runs on (counterGlucose), interpolated across sub-steps.
                    let totalSec = nextT.timeIntervalSince(prevT)
                    let nSub = Swift.max(1, Int((totalSec / candidateConfig.evalStep).rounded(.up)))
                    let subFrac = 1.0 / Double(nSub)
                    let aPrev = counterGlucose[prevIdx].quantity.doubleValue(for: mgdlUnit)
                    let aNext = counterGlucose[advIdx].quantity.doubleValue(for: mgdlUnit)
                    // GAP RE-ANCHOR: across a long CGM gap the single big-step advance
                    // is unreliable (manual boluses in the gap are on the field side
                    // but not the candidate history ⇒ runaway asymmetry). Take the
                    // gap-END LEVEL from the real CGM (discarding the unreliable
                    // big-step advance), but PRESERVE the candidate-vs-real divergence
                    // accumulated BEFORE the gap. Snapping straight to `aNext` zeroed
                    // that divergence in BOTH directions, so a candidate that
                    // legitimately drove BG away from real (e.g. an aggressive oref on
                    // a Loop dataset that over-doses a high) had its accumulated
                    // insulin effect wiped at every gap → it saw a high counter and
                    // re-dosed → runaway. Carrying the pre-gap offset fixes that while
                    // still resyncing the absolute level + gap-interval non-insulin
                    // physiology from real. Identity-safe: at candidate==real,
                    // counterMgdl[prevIdx]==aPrev, so the offset is 0 (⇒ = aNext).
                    if cfGapReanchorSec > 0 && totalSec > cfGapReanchorSec {
                        // Preserve only a SIGNIFICANT candidate-vs-real divergence; for
                        // small offsets snap straight to real (the original behavior) so
                        // the sub-step advance's tiny numerical drift (~1 mg/dL) can't
                        // accumulate across gaps and degrade the identity. The threshold
                        // sits well above that noise but far below any real over/under-
                        // dose divergence (e.g. an over-dosing oref runs 80-90 mg/dL
                        // below real before a gap).
                        let gapOffset = counterMgdl[prevIdx] - aPrev
                        counterMgdl[advIdx] = abs(gapOffset) > 10.0 ? aNext + gapOffset : aNext
                        advIdx += 1
                        continue
                    }
                    var bg = counterMgdl[prevIdx]
                    for k in 0..<nSub {
                        var crSub = 0.0
                        // Counter-regulation is a defense that fires only when the
                        // COUNTERFACTUAL itself is below onset — GATED on `belowC > 0`.
                        // Inside that gate it stays difference-based (rateC − rateA) so
                        // identity holds and a counter that inherited a DEEPER real-low
                        // defense via realBGdelta sheds the excess. But when the counter
                        // is at/above onset we apply NOTHING: a counterfactual running
                        // high must not shed the real low's defense (rateA), which used
                        // to subtract the full real-counter-reg rate and drive a
                        // high-running arm implausibly below the real substrate — a
                        // systematic downward bias against less-aggressive / lows-
                        // reducing candidates (they run high, so real lows crashed them).
                        // Cost: a high counter keeps a small inherited real-low lift;
                        // far preferable to a spurious plunge.
                        if counterRegOnsetMgdl > 0 {
                            let belowC = counterRegOnsetMgdl - bg
                            if belowC > 0 {
                                let rateC = Swift.min(counterRegGain * belowC, counterRegMaxRate)
                                let aSub = aPrev + (aNext - aPrev) * (Double(k) / Double(nSub))
                                let belowA = counterRegOnsetMgdl - aSub
                                let rateA = belowA > 0 ? Swift.min(counterRegGain * belowA, counterRegMaxRate) : 0.0
                                crSub = (rateC - rateA) * (totalSec * subFrac / 60.0)
                            }
                        }
                        bg += stepDelta * subFrac + crSub
                    }
                    counterMgdl[advIdx] = bg
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
                candidateTempAction: candidateTempAction,
                baselineTempAction: baselineTempAction,
                baselineEventualBG: baselineEventualBG,
                baselineIOB: baselineIOB,
                baselineCOB: baselineCOB,
                baselineMomentum: baselineMomentum,
                baselineRC: baselineRC,
                baselineDiscrepancy: baselineDiscrepancy,
                candidateEventualBG: candidateEventualBG,
                candidateIOB: candidateIOB,
                candidateCOB: candidateCOB,
                candidateMomentum: candidateMomentum,
                candidateRC: candidateRC,
                candidateMomentumMarginal: candidateMomentumMarginal,
                candidateRCMarginal: candidateRCMarginal,
                candidateAutosensRatio: candidateAutosensRatio,
                candidateMinGuardBG: candidateMinGuardBG,
                candidateMinPredBG: candidateMinPredBG,
                candidateICE: candidateICE,
                candidateCarbEffect: candidateCarbEffect,
                candidateDiscrepancy: candidateDiscrepancy,
                candidateSensModeMult: candidateSensModeMult,
                candidateManualBolusRecOut: candidateManualBolusRec,
                baselinePredCurve: baselinePredCurve
            ))
        }

        progress?(1.0)

        // PATIENT IOB — one independent computation applied to BOTH dose
        // histories. Re-stamp every dose with the PATIENT insulin model so the
        // result is invariant to any candidate insulin-model experiment, then
        // annotate (net-basal, scheduled-basal gaps filled) and evaluate
        // insulinOnBoard at each step. Field = real pump; candidate = the
        // candidate's actual delivery (counterfactualDoses).
        let patientType = data.therapyTimeline.insulinType
        // Split long basal segments into ≤5-min pieces so every basal takes the
        // SAME smooth path in insulinOnBoard. Loop's insulinOnBoard treats a
        // ≤1.05·delta segment as momentary but longer segments via a continuous
        // model whose integration bound is quantized to `delta` — which makes a
        // multi-delta segment (e.g. a 20-min suspend) produce lumpy IOB at its
        // boundaries. The candidate already delivers 5-min temp segments, so
        // splitting field basals the same way makes the two apples-to-apples.
        let splitSec: TimeInterval = 5 * 60
        func prep(_ doses: [EvalInsulinDose]) -> [EvalInsulinDose] {
            var out: [EvalInsulinDose] = []
            out.reserveCapacity(doses.count)
            for d0 in doses {
                var d = d0; d.insulinType = patientType
                let dur = d.endDate.timeIntervalSince(d.startDate)
                if d.deliveryType != .basal || dur <= 1.05 * splitSec {
                    out.append(d); continue
                }
                let rate = d.volume / dur   // U per second
                var s = d.startDate
                while s < d.endDate {
                    let e = Swift.min(s.addingTimeInterval(splitSec), d.endDate)
                    var piece = d
                    piece.startDate = s; piece.endDate = e
                    piece.volume = rate * e.timeIntervalSince(s)
                    out.append(piece)
                    s = e
                }
            }
            return out
        }
        // NB: the two-pointer iobSeries below REQUIRES start-sorted input. `annotated`
        // with gap-filling can interleave gap-fill basal segments out of start-order
        // (a later-dated fill can precede an earlier bolus), which makes `hi` stop early
        // and delays that bolus's IOB contribution by up to a fill span (~1h) — a
        // display-only artifact in patientIOBField, but a misleading one in case studies.
        // Sort defensively so the window is always correct.
        let fieldAnnotated = prep(data.doses)
            .annotated(with: data.therapyTimeline.basal, fillBasalGaps: true)
            .sorted { $0.startDate < $1.startDate }
        let candAnnotated = prep(counterfactualDoses)
            .annotated(with: data.therapyTimeline.basal, fillBasalGaps: true)
            .sorted { $0.startDate < $1.startDate }
        // Sliding-window IOB: doses are start-sorted and step times increase, so a
        // two-pointer window over the active-effect span keeps this O(N·W) instead
        // of the O(N²) whole-collection insulinOnBoard(at:) per step (which times
        // out once basal gaps are filled → ~17k dose entries).
        let effDur = data.therapyTimeline.insulinType.model.effectDuration
        let iobDelta = 5.0 * 60.0
        let iobBack = effDur + 12.0 * 3600.0   // conservative: covers long scheduled-basal segments
        let iobStepTimes = steps.map { $0.t }
        _ = iobDelta
        func iobSeries(_ ann: [BasalRelativeDose]) -> [Double] {
            var out = [Double](repeating: 0, count: iobStepTimes.count)
            let n = ann.count
            var lo = 0, hi = 0
            for (i, t) in iobStepTimes.enumerated() {
                let loBound = t.addingTimeInterval(-iobBack)
                while lo < n && ann[lo].startDate < loBound { lo += 1 }
                while hi < n && ann[hi].startDate <= t { hi += 1 }
                // public Collection method on the window slice (no copy) — internal
                // per-dose insulinOnBoard(at:delta:) isn't accessible cross-module.
                out[i] = ann[lo..<hi].insulinOnBoard(at: t)
            }
            return out
        }
        let fieldIOB = iobSeries(fieldAnnotated)
        let candIOB = iobSeries(candAnnotated)
        let stepsWithPatientIOB = steps.enumerated().map { (i, step) -> ClosedLoopSimResult.Step in
            var s = step
            s.patientIOBField = fieldIOB[i]
            s.patientIOBCandidate = candIOB[i]
            return s
        }

        return ClosedLoopSimResult(
            steps: stepsWithPatientIOB,
            baselineLabel: baselineLabel,
            candidateLabel: candidateLabel,
            intervalStart: evalStart,
            intervalEnd: interval.end,
            counterfactualDoses: counterfactualDoses
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
    /// Resample the RAW (unsmoothed) CGM samples onto the EXACT timestamps of
    /// `grid` (the smoothed grid) by linear interpolation. Produces a raw-valued
    /// series index-aligned 1:1 with `grid` — and therefore with the per-grid
    /// m(t) / realPhysDelta arrays — so the simulator can run on the original
    /// noisy CGM while physiology estimation stays on the smoothed grid. Every
    /// grid time falls between raw samples that are ≤ the grid's gap tolerance
    /// apart (same emission rule built it), so the interpolation is well-defined;
    /// before the first / after the last raw sample we clamp to the endpoint.
    fileprivate static func rawGridMatching(
        grid: [EvalGlucoseSample],
        raw: [EvalGlucoseSample],
        unit: LoopUnit
    ) -> [EvalGlucoseSample] {
        guard !grid.isEmpty else { return grid }
        let rs = raw.sorted { $0.startDate < $1.startDate }
        guard rs.count >= 2 else { return grid }
        let times = rs.map { $0.startDate.timeIntervalSince1970 }
        let vals  = rs.map { $0.quantity.doubleValue(for: unit) }
        var out: [EvalGlucoseSample] = []
        out.reserveCapacity(grid.count)
        var j = 0
        for g in grid {
            let tg = g.startDate.timeIntervalSince1970
            while j + 1 < times.count && times[j + 1] <= tg { j += 1 }
            let v: Double
            if tg <= times[0] {
                v = vals[0]
            } else if tg >= times[times.count - 1] {
                v = vals[times.count - 1]
            } else {
                let pT = times[j], nT = times[j + 1]
                let frac = (nT - pT) > 1e-9 ? (tg - pT) / (nT - pT) : 0.0
                v = vals[j] + frac * (vals[j + 1] - vals[j])
            }
            out.append(EvalGlucoseSample(
                startDate: g.startDate,
                quantity: .init(unit: unit, doubleValue: v),
                provenanceIdentifier: "raw-grid",
                receivedDate: g.receivedDate))
        }
        return out
    }

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
    /// Total scheduled-basal units delivered over [from, to], integrating across
    /// schedule segments. Used to fill the post-temp-expiry remainder of a long
    /// (CGM-gap) step with scheduled basal (net-zero IOB vs the schedule).
    fileprivate static func integrateScheduledBasal(
        _ basal: [AbsoluteScheduleValue<Double>], from: Date, to: Date) -> Double {
        guard to > from else { return 0 }
        var total = 0.0
        var covered = from
        for seg in basal where seg.endDate > from && seg.startDate < to {
            let s = Swift.max(from, seg.startDate)
            let e = Swift.min(to, seg.endDate)
            if e > s { total += seg.value * e.timeIntervalSince(s) / 3600.0; covered = Swift.max(covered, e) }
        }
        // Any uncovered tail (schedule didn't reach `to`): hold the last known rate.
        if covered < to, let r = basal.closestPrior(to: covered)?.value ?? basal.last?.value {
            total += r * to.timeIntervalSince(covered) / 3600.0
        }
        return total
    }

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
        // MID-ABSORPTION ISF (patient model): the counter advance MUST use the
        // same ISF treatment the ICE precompute uses (realICE is built with
        // useMidAbsorptionISF: true). Using dose-time `glucoseEffects` here left
        // the added candidate insulin and the removed field insulin on different
        // ISF timelines, so they did NOT cancel at equal doses and the counter
        // drifted tens of mg/dL/day on intraday-ISF datasets. Mid-abs on both
        // sides keeps the patient model self-consistent (candidate==field ⇒
        // counter==actual).
        let delta: TimeInterval = 5 * 60
        let effects = annotated.glucoseEffectsMidAbsorptionISF(
            longestEffectDuration: insulinModel.effectDuration,
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
        // MID-ABSORPTION ISF (patient model): same treatment as realICE /
        // realPhysDelta so candPhys and realPhysDelta cancel at equal doses.
        let effects = annotated.glucoseEffectsMidAbsorptionISF(
            longestEffectDuration: insulinModel.effectDuration,
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
        // Guard against an empty/inverted window (e.g. a run shorter than
        // warmup+burn-in makes cfActiveStart > interval.end): a negative stepCount
        // traps `for i in 0..<stepCount`. Nothing to rasterize ⇒ empty map.
        guard end > start else { return result }
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
    ///
    /// `internal` (was `fileprivate`) so `LoopAdapter` (in Engine/) can call
    /// it as the Loop-backed implementation of `DosingEngine.step(_:)`.
    internal static func simStepDose(
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
        timeBasedAFScale: Double = 1.0
    ) -> (dose: Double, bolus: Double, tempRate: Double, prediction: LoopPrediction<EvalCarbEntry>, manualBolusRec: Double, tempAction: String) {
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
        // Autosens (sustained-resistance integral action): scale ISF DOWN when BG has run
        // persistently ABOVE the correction target over a multi-hour window (sustained
        // resistance / under-counted carbs → need more insulin), UP when persistently below.
        // The multi-hour average ignores transient rises/rebounds — the discrimination fast
        // IRC lacks. Causal (candidate's own glucose history). Pairs with the uncertainty cap,
        // which is the anti-windup bound for this integral term.
        var autosensFactor = 1.0
        if config.autosensGain > 0, let lastG = input.glucose.last,
           let tgt = (input.target.closestPrior(to: t)?.value ?? input.target.first?.value) {
            let winSec = config.autosensWindowMin * 60.0
            let target = (tgt.lowerBound.doubleValue(for: unit) + tgt.upperBound.doubleValue(for: unit)) / 2.0
            var sum = 0.0, cnt = 0.0
            for s in input.glucose.reversed() {
                let age = lastG.startDate.timeIntervalSince(s.startDate)
                if age > winSec { break }
                sum += s.quantity.doubleValue(for: unit) - target
                cnt += 1
            }
            if cnt > 0 {
                let avgErr = sum / cnt                          // sustained BG − target (mg/dL)
                let f = 1.0 - config.autosensGain * avgErr      // resistant (avgErr>0) → f<1 → lower ISF
                autosensFactor = Swift.max(config.autosensMin, Swift.min(config.autosensMax, f))
            }
        }
        let effExtraISF = extraISFMultiplier * dampFactor * autosensFactor
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
        // Candidate correction-range override (study: sweep target midpoint/width
        // independent of ISF). When set, replace the profile target with a flat range.
        let effectiveTarget: [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>]
        if let lo = config.correctionRangeOverrideLow, let hi = config.correctionRangeOverrideHigh {
            let s = input.target.first?.startDate ?? Date.distantPast
            let e = input.target.last?.endDate ?? Date.distantFuture
            effectiveTarget = [AbsoluteScheduleValue(
                startDate: s, endDate: e,
                value: LoopQuantity(unit: unit, doubleValue: lo)...LoopQuantity(unit: unit, doubleValue: hi))]
        } else {
            effectiveTarget = input.target
        }
        // Post-low-gated RC rise-cut (corner candidate): within postlowWindowMin of a
        // <postlowThresholdMgdl sample AND while BG < postlowRcBgMax, scale the POSITIVE
        // (unexplained-rise) discrepancy in standard RC by postlowRcRiseScale — treat the
        // rebound rise as transient until BG proves it is a real high. Off = 1.0.
        var gatedRiseScale = config.ircRiseGainScale
        var gatedAsymStdRC = config.asymmetricStandardRC
        if config.postlowRcRiseScale != 1.0, let lastG = input.glucose.last {
            let mgdlU = LoopUnit.milligramsPerDeciliter
            if lastG.quantity.doubleValue(for: mgdlU) < config.postlowRcBgMax {
                let windowSec = config.postlowWindowMin * 60.0
                var recentLow = false
                for s in input.glucose.reversed() {
                    let age = lastG.startDate.timeIntervalSince(s.startDate)
                    if age > windowSec { break }
                    if s.quantity.doubleValue(for: mgdlU) < config.postlowThresholdMgdl { recentLow = true; break }
                }
                if recentLow { gatedRiseScale = config.postlowRcRiseScale; gatedAsymStdRC = true }
            }
        }
        // Fast-rise-gated RC rise-cut (meal-rise-stacking corner): trailing 15-min slope.
        if config.riseGateSlope > 0, let lastG = input.glucose.last {
            let mgdlU = LoopUnit.milligramsPerDeciliter
            let bgNow = lastG.quantity.doubleValue(for: mgdlU)
            if bgNow < config.riseGateBgMax {
                var slope = 0.0
                for s in input.glucose.reversed() {
                    let dt = lastG.startDate.timeIntervalSince(s.startDate)
                    if dt >= 15 * 60 { slope = (bgNow - s.quantity.doubleValue(for: mgdlU)) / (dt / 60.0); break }
                }
                if slope >= config.riseGateSlope { gatedRiseScale = config.riseGateRcRiseScale; gatedAsymStdRC = true }
            }
        }
        let effectiveInput = PredictionInput(
            glucose: input.glucose,
            doses: input.doses,
            carbs: input.carbs,
            basal: input.basal,
            sensitivity: effectiveSensitivity,
            carbRatio: input.carbRatio,
            target: effectiveTarget
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
        // start = last glucose + processing delay, so the momentum/RC windows now-anchor
        // like deployed Loop main (see EvalConfig.momentumProcessingDelay).
        let predStart = loopEvalPredictionStart(t: t, glucose: effectiveInput.glucose, config: config)
        // Hoist computed args to locals so the generatePrediction call stays under the
        // Swift type-checker's complexity heuristic (adding gradualTransitionsThreshold
        // tipped it into "unable to type-check in reasonable time").
        let clampTarget: [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>]? =
            (config.useIntegralRC && config.useIntegralRCClamp) ? effectiveInput.target : nil
        let rcRetroInterval: TimeInterval? = config.rcRetrospectionMinutes.map { $0 * 60 }
        let rcEffDuration: TimeInterval? = config.rcEffectDurationMinutes.map { $0 * 60 }
        let absorbOverrun: Double = config.adaptiveCarbAbsorption ? 1.0 : config.carbAbsorptionOverrun
        let maxAbsorbOverrun: Double = config.carbAbsorptionOverrun
        let momProjDuration: TimeInterval = config.momentumProjectionMinutes * 60
        let momDataIntervalSec: TimeInterval = config.momentumDataIntervalMinutes * 60
        var prediction: LoopPrediction<EvalCarbEntry> = LoopAlgorithm.generatePrediction(
            start: predStart,
            glucoseHistory: effectiveInput.glucose,
            doses: effectiveInput.doses,
            carbEntries: effectiveInput.carbs,
            basal: effectiveInput.basal,
            sensitivity: effectiveInput.sensitivity,
            scheduleBaselineSensitivity: scheduleBaseline,
            sensitivityDecomposition: decomposition,
            carbRatio: effectiveInput.carbRatio,
            target: clampTarget,
            algorithmEffectsOptions: .all,
            useIntegralRetrospectiveCorrection: config.useIntegralRC,
            ircDropGainScale: config.ircDropGainScale,
            ircRiseGainScale: gatedRiseScale,
            ircLowMemoryScale: config.ircLowMemoryScale,
            ircDropDurationScale: config.ircDropDurationScale,
            ircRiseDurationScale: config.ircRiseDurationScale,
            asymmetricStandardRC: gatedAsymStdRC,
            rcRetrospectionInterval: rcRetroInterval,
            rcEffectDuration: rcEffDuration,
            uamProjectionMinutes: config.uamProjectionMinutes,
            earlyRiseMinutes: config.earlyRiseMinutes,
            earlyRiseGain: config.earlyRiseGain,
            earlyRiseBgLow: config.earlyRiseBgLow,
            earlyRiseBgHigh: config.earlyRiseBgHigh,
            earlyRiseSlopeThreshold: config.earlyRiseSlopeThreshold,
            includingPositiveVelocityAndRC: config.includingPositiveVelocityAndRC,
                useLegacyRCDecay: config.useLegacyRCDecay,
            useMidAbsorptionISF: config.useMidAbsorptionISF,
            carbAbsorptionModel: config.carbAbsorptionModel.model,
            adaptiveCarbAbsorption: config.adaptiveCarbAbsorption,
            initialAbsorptionTimeOverrun: absorbOverrun,
            absorptionTimeOverrun: maxAbsorbOverrun,
            gradualTransitionsThreshold: config.momentumGradualTransitionsThreshold,   // WIRING FIX: was omitted → defaulted to 40 (gate always on), silently ignoring --no-gradual-transitions-gate in the dosing forecast
            momentumVelocityMaximum: momentumCap,
            momentumProjectionDuration: momProjDuration,
            momentumDataInterval: momDataIntervalSec,
            useAsymmetricMomentum: config.useAsymmetricMomentum,
            momentumAlphaSlow: config.momentumAlphaSlow,
            momentumAlphaFast: config.momentumAlphaFast
            // NB: `highCorrectionEnabled` / `*RiseGain` / `*EffectDurationMinutes`
            // / `*FastOffVelocity` came from the abandoned
            // `experiment/asymmetric-high-correction` LoopAlgorithm branch.
            // They are still in EvalConfig + CLI flags (dormant) but not
            // wired through here — the canonical `feat/asymmetric-momentum`
            // LoopAlgorithm fork does not accept them. Removing the EvalConfig
            // fields + CLI flags is a separate cleanup.
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

        // Causal volatility σ5 (EWMA std of the 5-min increment, candidate's own history).
        // Only computed when a σ candidate is on; identity otherwise.
        var sigma5 = Double.nan
        if config.sigmaBandK > 0 || config.calmHighAfScale != 1.0 {
            let unit = LoopUnit.milligramsPerDeciliter
            let g = effectiveInput.glucose.suffix(60)   // last ~5 h of samples
            let floorVar = 2.0 * config.sigmaNoiseMgdl * config.sigmaNoiseMgdl
            var v = Double.nan
            var prev: (Date, Double)? = nil
            for s in g {
                let bg = s.quantity.doubleValue(for: unit)
                if let (pt, pbg) = prev {
                    let dtMin = s.startDate.timeIntervalSince(pt) / 60.0
                    if dtMin > 2.0 && dtMin <= 7.0 {
                        let d5 = (bg - pbg) * (5.0 / dtMin)
                        v = v.isNaN ? max(d5 * d5, floorVar) : max(config.sigmaEwmaLambda * v + (1 - config.sigmaEwmaLambda) * d5 * d5, floorVar)
                    } else if dtMin > 7.0 {
                        v = Double.nan       // gap: restart the estimator
                    }
                }
                prev = (s.startDate, bg)
            }
            sigma5 = v.isNaN ? sqrt(floorVar) : sqrt(v)
        }
        // σ-widened LOWER band: lower each predicted point at τ min by k·σ5·(τ/5)^H up to
        // the horizon, tapering to 0 by taper — the eventual BG is untouched, the
        // predicted MINIMUM (min-guard / suspend logic) sees the volatility.
        let sigmaBandAllowed = !config.sigmaBandCobGate || (prediction.activeCarbs ?? 0) <= 0
        if config.sigmaBandK > 0, sigmaBandAllowed, sigma5.isFinite, let t0 = prediction.glucose.first?.startDate {
            let unit = LoopUnit.milligramsPerDeciliter
            let hz = config.sigmaBandHorizonMin, tp = max(config.sigmaBandTaperMin, hz + 1)
            let sHz = pow(max(hz, 5.0) / 5.0, config.sigmaScalingH)
            prediction.glucose = prediction.glucose.map { p in
                let tau = p.startDate.timeIntervalSince(t0) / 60.0
                var s = 0.0
                if tau <= 0 { s = 0 }
                else if tau <= hz { s = pow(max(tau, 5.0) / 5.0, config.sigmaScalingH) }
                else if tau < tp { s = sHz * (tp - tau) / (tp - hz) }
                let off = -config.sigmaBandK * sigma5 * s
                return PredictedGlucoseValue(startDate: p.startDate,
                                             quantity: LoopQuantity(unit: unit, doubleValue: p.quantity.doubleValue(for: unit) + off))
            }
        }

        // Application factor: flat config value (default 0.4), or glucose-based
        // (GBAF) ramp keyed on the current BG (latest glucose at/before t).
        let mgdl = LoopUnit.milligramsPerDeciliter
        let curBG = effectiveInput.glucose.last?.quantity.doubleValue(for: mgdl)
            ?? prediction.glucose.first?.quantity.doubleValue(for: mgdl) ?? 0
        var appFactor = config.applicationFactor
        if config.glucoseBasedApplicationFactor {
            var keyBG = curBG
            // Forecast-keyed GBAF: act on a rising/high FORECAST even when current BG is
            // still low-normal — but ONLY when the predicted minimum stays >= the guard,
            // so we never lift the throttle into a predicted dip (momentum/RC-inflated
            // rebound). keyBG = max(currentBG, eventualBG).
            if config.gbafForecastKeyed {
                let eventualBG = prediction.glucose.last?.quantity.doubleValue(for: mgdl) ?? curBG
                let predMin = prediction.glucose.map { $0.quantity.doubleValue(for: mgdl) }.min() ?? curBG
                if predMin >= config.gbafForecastMinGuard {
                    keyBG = Swift.max(curBG, eventualBG)
                }
            }
            appFactor = EvaluationEngine.glucoseBasedApplicationFactor(
                currentBG: keyBG,
                lowAnchor: config.gbafLowAnchor, highAnchor: config.gbafHighAnchor,
                factorLow: config.gbafFactorLow, factorHigh: config.gbafFactorHigh)
        }
        // Dynamic ISF (continuous): scale the sensitivity used for DOSE SIZING by a
        // linear ramp of current BG (1 at/below lowAnchor → multHigh at/above highAnchor).
        // multHigh < 1 ⇒ more insulin per mg/dL of correction when BG is high (insulin
        // resistance rises with glycemia). The forecast's ISF is unchanged.
        var doseInput = effectiveInput
        if abs(config.dynIsfMultHigh - 1.0) > 1e-9 {
            let span = Swift.max(1.0, config.dynIsfHighAnchor - config.dynIsfLowAnchor)
            let frac = Swift.max(0, Swift.min(1, (curBG - config.dynIsfLowAnchor) / span))
            let g = 1.0 + (config.dynIsfMultHigh - 1.0) * frac
            doseInput = PredictionInput(
                glucose: effectiveInput.glucose,
                doses: effectiveInput.doses,
                carbs: effectiveInput.carbs,
                basal: effectiveInput.basal,
                sensitivity: effectiveInput.sensitivity.map {
                    AbsoluteScheduleValue(startDate: $0.startDate, endDate: $0.endDate,
                        value: LoopQuantity(unit: mgdl, doubleValue: $0.value.doubleValue(for: mgdl) * g))
                },
                carbRatio: effectiveInput.carbRatio,
                target: effectiveInput.target
            )
        }
        // Deployed multiplies the (possibly GBAF) application factor by
        // timeBasedDoseApplicationFactor = min(1, timeSinceLastCompletedLoop/5min)
        // (LoopDataManager ~873): sub-5-min loops after a COMPLETED one dose
        // proportionally less. Known divergence: deployed's maxAutomaticBolus uses
        // the UNSCALED factor (maxBolus x min(AF,1)) while our package caps on the
        // scaled one - only visible on saturated sub-5-min retries, accepted.
        appFactor *= timeBasedAFScale
        // Calm-high licence: a high with low volatility takes a larger application factor.
        var calmHighAllowed = !config.calmHighCobGate || (prediction.activeCarbs ?? 0) <= 0
        // Trend gate: a high that is already coming down does not need the licence — and the calm
        // gate does not exclude it, because a steady fall reads as moderate σ5. Trailing 30-min
        // slope from the candidate's own glucose (causal).
        if calmHighAllowed, config.calmHighMinSlope.isFinite {
            let g = effectiveInput.glucose
            var slope = Double.nan
            if let last = g.last {
                let window = last.startDate.addingTimeInterval(-30 * 60 - 150)
                if let first = g.first(where: { $0.startDate >= window }) {
                    let dtMin = last.startDate.timeIntervalSince(first.startDate) / 60.0
                    if dtMin >= 20.0 {
                        slope = (last.quantity.doubleValue(for: mgdl)
                                 - first.quantity.doubleValue(for: mgdl)) / dtMin
                    }
                }
            }
            calmHighAllowed = slope.isFinite && slope >= config.calmHighMinSlope
        }
        if config.calmHighAfScale != 1.0, calmHighAllowed, sigma5.isFinite,
           curBG >= config.calmHighBgMin, sigma5 <= config.calmHighSigmaMax {
            appFactor = min(1.0, appFactor * config.calmHighAfScale)
        }
        let doseRec = EvaluationEngine.computeDoseRecommendation(
            prediction: prediction,
            at: t,
            input: doseInput,
            suspendThreshold: therapy.suspendThreshold,
            maxBolus: therapy.maxBolus,
            maxBasalRate: therapy.maxBasalRate,
            insulinType: therapy.insulinType,
            evalStep: config.evalStep,
            applicationFactor: appFactor,
            softLowGate: config.softLowGate,
            lowGateThreshold: config.lowGateThresholdMgdl,
            uncertaintyCap: config.uncertaintyCapEnabled
                ? (k: config.uncertaintyK, fmax: config.uncertaintyFmax, low: config.uncertaintyLow,
                   autosensFactor: config.uncertaintyDecoupleAutosens ? autosensFactor : 1.0)
                : nil,
            bolusIncrement: config.bolusIncrement,
            tempBasalIncrement: config.tempBasalIncrement,
            useMidAbsorptionISF: config.useMidAbsorptionISF,
            useTempBasalStrategy: config.useTempBasalStrategy,
            basalOverrideActive: therapy.overrideWindows.contains {
                $0.start <= t && t < $0.end && ($0.factor ?? 1.0) != 1.0
            }
        )
        return (
            dose: doseRec?.deltaU ?? 0,
            bolus: doseRec?.bolus ?? 0,
            tempRate: doseRec?.tempBasalRate ?? 0,
            prediction: prediction,
            manualBolusRec: doseRec?.manualBolusRec ?? 0,
            tempAction: doseRec?.tempAction ?? "set"
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
    /// Cap CGM samples at the sensor's report ceiling (Dexcom G6/G7 = 400 mg/dL;
    /// Libre similar). Real-world CGMs peg at this ceiling — the controller
    /// ISO8601 (no fractional seconds) for the FORECAST_COMPONENT_DUMP date filter.
    nonisolated(unsafe) fileprivate static let isoNoFrac: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter(); f.formatOptions = [.withInternetDateTime]; return f
    }()

    /// never sees BG above it — so the sim mirrors that for fairness across
    /// algorithms. Counter trajectory and outcome scoring use uncapped values.
    fileprivate static func capGlucoseToSensor(
        _ samples: [EvalGlucoseSample],
        capMgdl: Double,
        unit: LoopUnit
    ) -> [EvalGlucoseSample] {
        samples.map { s in
            let v = s.quantity.doubleValue(for: unit)
            if v <= capMgdl { return s }
            return EvalGlucoseSample(
                startDate: s.startDate,
                quantity: LoopQuantity(unit: unit, doubleValue: capMgdl),
                provenanceIdentifier: s.provenanceIdentifier,
                isDisplayOnly: s.isDisplayOnly,
                wasUserEntered: s.wasUserEntered,
                condition: s.condition,
                trendRate: s.trendRate,
                receivedDate: s.receivedDate
            )
        }
    }

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

