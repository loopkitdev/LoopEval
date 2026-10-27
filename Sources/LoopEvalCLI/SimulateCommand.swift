// SimulateCommand.swift — `loop-eval simulate` subcommand for closed-loop
// counterfactual simulation.
//
// Differs from `bench` in that the candidate's per-step decisions are made
// against its own counterfactual BG history (with feedback) rather than the
// actual CGM. This corrects the linearization's drift bias for aggressive
// candidates like IRC/dynamic-ISF where dose-delta impact compounds.

import ArgumentParser
import EvalCore
import Foundation
import LoopAlgorithm

@available(macOS 10.15, macCatalyst 13, iOS 13, tvOS 13, watchOS 6, *)
struct SimulateCommand: AsyncParsableCommand {

    static let configuration = CommandConfiguration(
        commandName: "simulate",
        abstract: "Closed-loop counterfactual simulation (full feedback) — slower than bench but accurate for aggressive candidates.",
        discussion: """
        Settings can also come from a JSON config file, arranged by the sections below:
        data, mode, deployment, candidate, person, body, plant, loop-experiments, openaps.
        Keys are flag names; in candidate sections the "candidate-" prefix may be dropped.
        A file may "include" others. See SimulateConfig.swift.

        --config FILE.json: read settings from a file (repeatable, later files win).
        --set section.key=value: one setting (the value is parsed as JSON, else a string).
        --show-config: print the expanded command line and exit.

        Precedence, lowest first: the export's replay_config.json (with
        deployment.from-replay-config), config files, --set, command-line flags.
        """
    )

    // Flags, grouped by what they configure (SimulateFlags.swift). The group sections are what
    // `simulate --help` prints; the properties keep their old names through forwarding accessors.
    @OptionGroup(title: SimulateSection.data.title) var data: SimulateDataFlags
    @OptionGroup(title: SimulateSection.mode.title) var mode: SimulateModeFlags
    @OptionGroup(title: SimulateSection.deployment.title) var deployment: SimulateDeploymentFlags
    @OptionGroup(title: SimulateSection.candidate.title) var candidate: SimulateCandidateFlags
    @OptionGroup(title: SimulateSection.person.title) var person: SimulatePersonFlags
    @OptionGroup(title: SimulateSection.body.title) var body: SimulateBodyFlags
    @OptionGroup(title: SimulateSection.plant.title) var plant: SimulatePlantFlags
    @OptionGroup(title: SimulateSection.loopExperiments.title) var loopExperiments: SimulateLoopExperimentFlags
    @OptionGroup(title: SimulateSection.openaps.title) var openaps: SimulateOpenAPSFlags

    mutating func run() async throws {
        var exportProvenance: (version: Int?, warnings: [String])? = nil
        let startDate = try parseISO8601Date(start)
        let endDate = try parseISO8601Date(end)
        guard endDate > startDate else { throw ValidationError("--end must be after --start") }
        let interval = DateInterval(start: startDate, end: endDate)
        let resolvedTz: TimeZone = localTimezone.flatMap { TimeZone(identifier: $0) } ?? .current

        // A Tidepool export ships its edited carbs' as-seen versions (carb_revisions.json,
        // ETL v25); replay them unless an overlay was given explicitly.
        if carbRevisionsJson == nil, let dir = dataDir {
            let p = URL(fileURLWithPath: dir).appendingPathComponent("carb_revisions.json").path
            if FileManager.default.fileExists(atPath: p) {
                carbRevisionsJson = p
                printStderr("Using the dataset's carb revisions (carb_revisions.json)\n")
            }
        }

        // Class-1 emulation: reproduce deployed Loop main's basal-IOB ripple (pre-PR#35).
        InsulinMathCompat.useLegacyBasalRippleIOB = legacyBasalIob

        let hourlyISF: [Double]?
        if let csv = candidateIsfHourly {
            let parts = csv.split(separator: ",").map { Double($0.trimmingCharacters(in: .whitespaces)) }
            guard parts.count == 24, parts.allSatisfy({ $0 != nil }) else {
                throw ValidationError("--candidate-isf-hourly requires exactly 24 comma-separated numbers")
            }
            hourlyISF = parts.map { $0! }
        } else { hourlyISF = nil }

        let baselinePreset = try parseInsulinType(insulinType)

        // App factor is a property of the real Loop deployment → both arms share it.
        // Candidate inherits unless explicitly overridden (negative sentinel = inherit).
        let effCandidateAppFactor = candidateApplicationFactor < 0 ? applicationFactor : candidateApplicationFactor
        var baselineConfig = EvalConfig(
            applicationFactor: applicationFactor,
            exportForecastCurve: exportForecastCurve,
            evalStep: TimeInterval(stepMinutes) * 60,
            includeFutureInsulin: oracleFutureInputs,
            includeFutureCarbs: oracleFutureInputs,
            insulinLookbackHours: insulinLookbackHours,
            glucoseLookbackHours: glucoseLookbackHours,
            useIntegralRC: integralRC,
            useIntegralRCClamp: integralRCClamp,
            bolusIncrement: candidateBolusIncrement,
            tempBasalIncrement: candidateTempBasalIncrement,
            basalPulseQuantum: basalPulseQuantum,
            kalmanSmoothing: !noKalman,
            simRawGlucose: simRawGlucose,
            clipInProgressTempBasal: clipInProgressTempBasal,
            useMidAbsorptionISF: midAbsorptionIsf,
            adaptiveCarbAbsorption: adaptiveCarbAbsorption,
            carbRevisionsPath: carbRevisionsJson,
            overrideTargetsPath: overrideTargetsJson,
            sensitivityMultiplier: sensitivityMultiplier,
            localTimezone: resolvedTz,
            momentumGradualTransitionsThreshold: noGradualTransitionsGate ? nil : 40,
            useLegacyRCDecay: legacyRcDecay,
            useAsymmetricMomentum: asymmetricMomentum
        )
        baselineConfig.useTempBasalStrategy = tempBasalStrategy
        baselineConfig.carbAbsorptionOverrun = carbAbsorptionOverrun

        let crHalfWidth: Double = (candidateTargetWidth ?? 0) / 2
        let crOverrideLow: Double? = candidateTargetMid.map { $0 - crHalfWidth }
        let crOverrideHigh: Double? = candidateTargetMid.map { $0 + crHalfWidth }
        var candidateConfig = EvalConfig(
            glucoseBasedApplicationFactor: candidateGbaf,
            gbafLowAnchor: candidateGbafLowAnchor,
            gbafHighAnchor: candidateGbafHighAnchor,
            gbafFactorLow: candidateGbafFactorLow,
            gbafFactorHigh: candidateGbafFactorHigh,
            gbafForecastKeyed: candidateGbafForecastKeyed,
            gbafForecastMinGuard: candidateGbafForecastMinGuard,
            softLowGate: candidateSoftLowGate,
            lowGateThresholdMgdl: candidateLowGateThreshold,
            iobAdjustManualBoluses: candidateIobAdjustManualBoluses,
            manualBolusFromRecommendation: candidateManualBolusFromRecommendation,
            manualBolusRecScale: candidateManualBolusRecScale,
            uamProjectionMinutes: candidateUamMinutes,
            earlyRiseMinutes: candidateEarlyRiseMinutes,
            earlyRiseGain: candidateEarlyRiseGain,
            earlyRiseBgLow: candidateEarlyRiseBgLow,
            earlyRiseBgHigh: candidateEarlyRiseBgHigh,
            earlyRiseSlopeThreshold: candidateEarlyRiseSlopeThreshold,
            dynIsfMultHigh: candidateDynisfMultHigh,
            dynIsfLowAnchor: candidateDynisfLowAnchor,
            dynIsfHighAnchor: candidateDynisfHighAnchor,
            uncertaintyCapEnabled: candidateUncertaintyCap,
            uncertaintyK: candidateUncertaintyK,
            uncertaintyFmax: candidateUncertaintyFmax,
            uncertaintyLow: candidateUncertaintyLow,
            autosensGain: candidateAutosensGain,
            autosensWindowMin: candidateAutosensWindowMin,
            autosensMin: candidateAutosensMin,
            autosensMax: candidateAutosensMax,
            uncertaintyDecoupleAutosens: candidateUncertaintyDecouple,
            applicationFactor: effCandidateAppFactor,
            highCorrectionEnabled: candidateHighCorrection,
            highCorrectionRiseGain: candidateHighCorrectionRiseGain,
            highCorrectionEffectDurationMinutes: candidateHighCorrectionEffectMin,
            highCorrectionFastOffVelocity: candidateHighCorrectionFastOffVelocity,
            oapsThresholdSetting: candidateOapsThreshold,
            oapsSmbDeliveryRatio: candidateOapsSmbRatio,
            oapsMaxSmbBasalMinutes: candidateOapsMaxSmbMin,
            oapsUseNewFormula: candidateOapsDynamicIsf ? true : nil,
            oapsSigmoid: candidateOapsSigmoid ? true : nil,
            oapsAdjustmentFactor: candidateOapsAdjustmentFactor,
            oapsAdjustmentFactorSigmoid: candidateOapsAdjustmentFactorSigmoid,
            oapsEnableUAM: candidateOapsNoUam ? false : nil,
            oapsEnableSMB: candidateOapsNoSmb ? false : nil,
            postlowSuppressMgdl: candidatePostlowSuppress,
            postlowWindowMin: candidatePostlowWindow,
            postlowThresholdMgdl: candidatePostlowThreshold,
            postlowTrendGain: candidatePostlowTrendGain,
            postlowIsfMult: candidatePostlowIsfMult,
            postlowRcRiseScale: candidatePostlowRcRiseScale,
            postlowRcBgMax: candidatePostlowRcBgMax,
            riseGateSlope: candidateRiseGateSlope,
            riseGateRcRiseScale: candidateRiseGateRcRiseScale,
            riseGateBgMax: candidateRiseGateBgMax,
            sigmaBandK: candidateSigmaBandK,
            sigmaBandHorizonMin: candidateSigmaBandHorizonMin,
            sigmaBandTaperMin: candidateSigmaBandTaperMin,
            sigmaScalingH: candidateSigmaH,
            sigmaEwmaLambda: candidateSigmaLambda,
            sigmaNoiseMgdl: candidateSigmaNoise,
            calmHighAfScale: candidateCalmHighAfScale,
            calmHighBgMin: candidateCalmHighBg,
            calmHighSigmaMax: candidateCalmHighSigmaMax,
            sigmaBandCobGate: candidateSigmaBandCobGate,
            calmHighCobGate: candidateCalmHighCobGate,
            calmHighMinSlope: candidateCalmHighMinSlope ?? -.infinity,
            calmHighTargetDelta: candidateCalmHighTargetDelta,
            runwayFraction: candidateRunwayFraction,
            sigmaPrior: candidateSigmaPrior,
            sigmaPriorSteps: candidateSigmaPriorSteps,
            runwayZ: candidateRunwayZ,
            runwayHorizonMin: candidateRunwayHorizonMin,
            runwayMaxMgdl: candidateRunwayMaxMgdl,
            runwayBgMin: candidateRunwayBgMin,
            runwayCobGate: candidateRunwayCobGate,
            splitCurvePeakMin: splitCurvePeakMin,
            splitCurveDurationMin: splitCurveDurationMin,
            splitCurvePart: splitCurvePart,
            splitRiseMgdl: splitRiseMgdl,
            descentRcRiseScale: candidateDescentRcRiseScale,
            sigmaBandDescentGate: candidateSigmaBandDescentGate,
            descentHighBgMin: candidateDescentHighBgMin,
            descentWindowMin: candidateDescentWindowMin,
            descentSlopeMax: candidateDescentSlopeMax,
            sigmaBandBaseline: candidateSigmaBandBaseline,
            sigmaBandFixedSigma: candidateSigmaBandFixedSigma,
            sigmaBandGuardOnly: candidateSigmaBandGuardOnly,
            negativeInsulinDamper: candidateNegativeInsulinDamper,
            nidAnchorAlpha: candidateNidAnchorAlpha,
            nidMarginalSlope: candidateNidMarginalSlope,
            nidLagMin: candidateNidLagMin,
            basalLockBg: candidateBasalLockBg,
            sensDampWindowMin: candidateSensDampWindow,
            sensDampThresholdRate: candidateSensDampThreshold,
            sensDampGain: candidateSensDampGain,
            sensDampMax: candidateSensDampMax,
            evalStep: TimeInterval(stepMinutes) * 60,
            includeFutureInsulin: oracleFutureInputs,
            includeFutureCarbs: oracleFutureInputs,
            glucoseLookbackHours: glucoseLookbackHours,
            useIntegralRC: candidateIntegralRC || integralRC,
            useIntegralRCClamp: candidateIntegralRCClamp || integralRCClamp,
            ircDropGainScale: candidateIrcDropScale,
            ircRiseGainScale: candidateIrcRiseScale,
            asymmetricStandardRC: candidateAsymmetricStdRc,
            ircLowMemoryScale: candidateIrcLowMemoryScale,
            ircDropDurationScale: candidateIrcDropDurationScale,
            ircRiseDurationScale: candidateIrcRiseDurationScale,
            sensitiveModeTauSec: candidateSensitiveModeTauMin * 60,
            sensitiveModeGain: candidateSensitiveModeGain,
            iceRiseBoostGain: candidateIceRiseBoostGain,
            iceRiseBoostBgLo: candidateIceRiseBoostBgLo,
            iceRiseBoostBgHi: candidateIceRiseBoostBgHi,
            iceRiseBoostTauSec: candidateIceRiseBoostTauMin * 60,
            iceRiseBoostThresh: candidateIceRiseBoostThresh,
            iceRiseBoostSensSuppress: candidateIceRiseBoostSensSuppress,
            iceRiseBoostIsfFadeLo: candidateIceRiseBoostIsfFadeLo,
            iceRiseBoostIsfFadeHi: candidateIceRiseBoostIsfFadeHi,
            bolusIncrement: candidateBolusIncrement,
            tempBasalIncrement: candidateTempBasalIncrement,
            basalPulseQuantum: basalPulseQuantum,
            correctionRangeOverrideLow: crOverrideLow,
            correctionRangeOverrideHigh: crOverrideHigh,
            kalmanSmoothing: !noKalman,
            simRawGlucose: simRawGlucose,
            clipInProgressTempBasal: candidateClipInProgressTempBasal,
            useMidAbsorptionISF: midAbsorptionIsf,
            adaptiveCarbAbsorption: adaptiveCarbAbsorption,
            carbAbsorptionTimeCapSec: candidateCarbAbsorptionCapMin * 60,
            carbRevisionsPath: carbRevisionsJson,
            overrideTargetsPath: overrideTargetsJson,
            sensitivityMultiplier: candidateSensitivityMultiplier ?? sensitivityMultiplier,
            sensitivityHourlyMultipliers: hourlyISF,
            localTimezone: resolvedTz,
            positiveVelocityCap: candidateMomentumCap,
            momentumGradualTransitionsThreshold: noGradualTransitionsGate ? nil : 40,
            useLegacyRCDecay: legacyRcDecay,
            useAsymmetricMomentum: candidateAsymmetricMomentum || asymmetricMomentum,
            momentumAlphaSlow: candidateMomentumAlphaSlow,
            momentumAlphaFast: candidateMomentumAlphaFast
        )
        // Slow (autosens-scope) RC: set post-construction for the same reason as the block below.
        candidateConfig.slowRcTauSec = candidateSlowRcTauMin * 60
        candidateConfig.slowRcGain = candidateSlowRcGain
        candidateConfig.slowRcMin = candidateSlowRcMin
        candidateConfig.slowRcMax = candidateSlowRcMax
        candidateConfig.slowRcIntegral = candidateSlowRcMode == "integral"
        candidateConfig.slowRcClipMgdl = candidateSlowRcClipMgdl
        candidateConfig.slowRcLeakSec = candidateSlowRcLeakMin * 60
        candidateConfig.slowRcPostlowFreezeSec = candidateSlowRcPostlowFreezeMin * 60
        candidateConfig.slowRcNeeds = candidateSlowRcNeeds
        if let path = candidateSlowRcGateJson {
            let obj = try JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: path))) as? [String: Any] ?? [:]
            let iso = ISO8601DateFormatter(); iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            let isoPlain = ISO8601DateFormatter()
            func date(_ v: Any?) -> Date? { (v as? String).flatMap { iso.date(from: $0) ?? isoPlain.date(from: $0) } }
            candidateConfig.slowRcGateWindows = (obj["windows"] as? [[String: Any]] ?? []).compactMap { w in
                guard let s = date(w["start"]), let e = date(w["end"]), let m = w["min"] as? Double else { return nil }
                return SlowRcGateWindow(start: s, end: e, min: m)
            }.sorted { $0.start < $1.start }
            candidateConfig.slowRcResets = (obj["resets"] as? [Any] ?? []).compactMap(date).sorted()
        }
        guard candidatePlateauUamMinutes >= 0, candidatePlateauUamGain >= 0 else { throw ValidationError("--candidate-plateau-uam-minutes/-gain must be >= 0.") }
        candidateConfig.plateauUamMinutes = candidatePlateauUamMinutes
        candidateConfig.plateauUamGain = candidatePlateauUamGain
        // Set post-construction to keep the EvalConfig(...) literal under the
        // Swift type-checker's expression-complexity limit. Property assignment is
        // also order-free — prefer adding NEW candidate flags here rather than
        // threading them into the positional EvalConfig(...) literal above.
        candidateConfig.useTempBasalStrategy = tempBasalStrategy
        candidateConfig.carbAbsorptionOverrun = carbAbsorptionOverrun
        candidateConfig.basalRateMultiplier = candidateBasalRateMultiplier
        // "Overall insulin needs" preset-style factor f: basal ×f, ISF ÷f, CR ÷f.
        // Composes multiplicatively with the individual multipliers set above/in the literal.
        if let needs = candidateInsulinNeeds {
            candidateConfig.basalRateMultiplier   *= needs
            candidateConfig.sensitivityMultiplier *= 1.0 / needs
            candidateConfig.carbRatioMultiplier   *= 1.0 / needs
        }
        if let spec = candidateNeedsHourly {
            let csv = spec.hasPrefix("@")
                ? ((try? String(contentsOfFile: String(spec.dropFirst()), encoding: .utf8)) ?? "")
                : spec
            let parts = csv.split(whereSeparator: { $0 == "," || $0 == "\n" })
                .map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }.map { Double($0) }
            guard parts.count == 24, parts.allSatisfy({ $0 != nil && $0! > 0 }) else {
                throw ValidationError("--candidate-needs-hourly requires exactly 24 positive comma-separated numbers")
            }
            let h = parts.map { $0! }
            candidateConfig.needsHourlyMultipliers = h
            let isfH = candidateConfig.sensitivityHourlyMultipliers ?? Array(repeating: 1.0, count: 24)
            candidateConfig.sensitivityHourlyMultipliers = zip(isfH, h).map { $0 / $1 }
        }
        let parsedPatientInsulinModel = try patientInsulinModel.map { try parseInsulinType($0) }
        let parsedControllerInsulinModel = try controllerInsulinModel.map { try parseInsulinType($0) }
        if parsedPatientInsulinModel == .custom || parsedControllerInsulinModel == .custom {
            guard let dur = customInsulinDurationMin, let peak = customInsulinPeakMin else {
                throw ValidationError("a `custom` insulin model needs --custom-insulin-duration-min and --custom-insulin-peak-min.")
            }
            guard peak > 0, dur > 2 * peak else {
                throw ValidationError("--custom-insulin-duration-min (\(dur)) must exceed twice --custom-insulin-peak-min (\(peak)); the exponential model is undefined otherwise.")
            }
            ExponentialInsulinModelPreset.customActionDuration = dur * 60
            ExponentialInsulinModelPreset.customPeakActivity = peak * 60
            printStderr("custom insulin model: peak \(Int(peak)) min, action duration \(Int(dur)) min (+10 min delay)\n")
        } else if customInsulinDurationMin != nil || customInsulinPeakMin != nil {
            throw ValidationError("--custom-insulin-duration-min/--custom-insulin-peak-min only apply with `--controller-insulin-model custom` or `--patient-insulin-model custom`.")
        }
        if splitCurvePeakMin > 0 {
            guard controllerInsulinSwitch.isEmpty else {
                throw ValidationError("--split-curve-peak-min uses the custom2 curve slot; it cannot be combined with --controller-insulin-switch.")
            }
            guard ["ice", "correction", "projection-cob", "projection-rise"].contains(splitCurvePart) else { throw ValidationError("--split-curve-part must be ice, correction, projection-cob or projection-rise.") }
            guard splitCurveDurationMin > 2 * splitCurvePeakMin else {
                throw ValidationError("--split-curve-duration-min must exceed twice --split-curve-peak-min.")
            }
            ExponentialInsulinModelPreset.custom2ActionDuration = splitCurveDurationMin * 60
            ExponentialInsulinModelPreset.custom2PeakActivity = splitCurvePeakMin * 60
        }
        // Dated controller curve changes. A `DURATION/PEAK` spec takes the first free custom slot.
        var insulinTypeChanges: [InsulinTypeChange] = []
        if !controllerInsulinSwitch.isEmpty {
            let iso = ISO8601DateFormatter()
            var slots: [(dur: Double, peak: Double, preset: ExponentialInsulinModelPreset)] = []
            if parsedPatientInsulinModel == .custom || parsedControllerInsulinModel == .custom,
               let d = customInsulinDurationMin, let p = customInsulinPeakMin {
                slots.append((d, p, .custom))
            }
            for raw in controllerInsulinSwitch {
                let parts = raw.split(separator: "=", maxSplits: 1).map(String.init)
                guard parts.count == 2, let start = iso.date(from: parts[0]) else {
                    throw ValidationError("--controller-insulin-switch expects ISO8601=SPEC (e.g. 2026-09-24T09:03:00Z=180/80); got '\(raw)'.")
                }
                let spec = parts[1]
                let preset: ExponentialInsulinModelPreset
                let dp = spec.split(separator: "/").map { Double($0) }
                if dp.count == 2, let d = dp[0], let p = dp[1] {
                    guard p > 0, d > 2 * p else {
                        throw ValidationError("--controller-insulin-switch \(spec): duration must exceed twice the peak.")
                    }
                    if let hit = slots.first(where: { $0.dur == d && $0.peak == p }) {
                        preset = hit.preset
                    } else {
                        let free: [ExponentialInsulinModelPreset] = [.custom, .custom2].filter { c in !slots.contains { $0.preset == c } }
                        guard let c = free.first else {
                            throw ValidationError("--controller-insulin-switch: at most two distinct custom curves per run.")
                        }
                        if c == .custom {
                            ExponentialInsulinModelPreset.customActionDuration = d * 60
                            ExponentialInsulinModelPreset.customPeakActivity = p * 60
                        } else {
                            ExponentialInsulinModelPreset.custom2ActionDuration = d * 60
                            ExponentialInsulinModelPreset.custom2PeakActivity = p * 60
                        }
                        slots.append((d, p, c)); preset = c
                    }
                } else {
                    preset = try parseInsulinType(spec)
                    if preset == .custom || preset == .custom2 {
                        throw ValidationError("--controller-insulin-switch: give a custom curve as DURATION/PEAK, not by name.")
                    }
                }
                insulinTypeChanges.append(InsulinTypeChange(start: start, preset: preset))
            }
            insulinTypeChanges.sort { $0.start < $1.start }
            for c in insulinTypeChanges {
                let m = c.preset
                printStderr("controller insulin curve from \(iso.string(from: c.start)): \(m) (peak \(Int(m.peakActivity / 60)) min, action duration \(Int(m.actionDuration / 60)) min)\n")
            }
        }
        if dataDir != nil && insulinType != "rapidActingAdult" && controllerInsulinModel == nil {
            printStderr("WARNING: --insulin-type is IGNORED with --data-dir (the model comes from therapy.json). Use --controller-insulin-model to override it.\n")
        }
        if let pm = parsedPatientInsulinModel, pm == baselinePreset {
            printStderr("note: --patient-insulin-model \(patientInsulinModel!) matches --insulin-type; plant and controller are the same model (a no-op).\n")
        }
        if insulinPhysicalPeak != nil || insulinPhysicalDia != nil {
            printStderr("WARNING: --insulin-physical-peak/--insulin-physical-dia only size the effect window; they do NOT change the plant's insulin curve. Use --patient-insulin-model.\n")
        }
        if let v = patientIsf, !(v > 0) {
            throw ValidationError("--patient-isf must be positive (mg/dL per U); got \(v).")
        }
        candidateConfig.oapsAutosensMax = candidateOapsAutosensMax
        candidateConfig.oapsAutosensMin = candidateOapsAutosensMin
        candidateConfig.oapsInsulinPeakTime = candidateOapsInsulinPeak
        candidateConfig.oapsDia = candidateOapsDia
        candidateConfig.insulinPhysicalPeakMin = insulinPhysicalPeak
        candidateConfig.insulinPhysicalDiaHours = insulinPhysicalDia
        candidateConfig.oapsCurve = candidateOapsCurve
        candidateConfig.oapsMaxIob = candidateOapsMaxIob
        candidateConfig.oapsSmoothGlucose = candidateOapsSmoothGlucose
        candidateConfig.oapsPumpPulse = candidateOapsPumpPulse
        if let pj = candidateOapsPrefsJson {
            candidateConfig.oapsPrefsJson = pj.hasPrefix("@")
                ? (try? String(contentsOfFile: String(pj.dropFirst()), encoding: .utf8)) ?? pj
                : pj
        }
        if let afc = candidateOapsAfCsv {
            candidateConfig.oapsAfScheduleCSV = (try? String(contentsOfFile: afc, encoding: .utf8)) ?? nil
        }
        candidateConfig.insulinLookbackHours = insulinLookbackHours
        // RC/momentum absolute windows (how far back / how far forward). nil ⇒ deployed defaults.
        candidateConfig.momentumProjectionMinutes = candidateMomentumProjectionMin
        candidateConfig.momentumDataIntervalMinutes = candidateMomentumLookbackMin
        candidateConfig.rcRetrospectionMinutes = candidateRcRetrospectionMin
        candidateConfig.rcEffectDurationMinutes = candidateRcEffectDurationMin

        let dataSource: any EvalDataSource
        if let dataDir {
            dataSource = JSONFileDataSource(baseURL: URL(fileURLWithPath: dataDir))
            let prov = Self.checkExportProvenance(dataDir: dataDir, arguments: SimulateConfig.effectiveArguments ?? CommandLine.arguments)
            exportProvenance = prov
            for w in prov.warnings {
                printStderr("\n*** PROVENANCE WARNING: \(w)\n")
            }
        } else {
            guard !nightscoutUrl.isEmpty, let baseURL = URL(string: nightscoutUrl) else {
                throw ValidationError("Provide --nightscout-url or --data-dir")
            }
            let client = NightscoutClient(baseURL: baseURL, apiSecret: apiSecret, token: token)
            let cache = try DataCache(cacheDir: cacheDir)
            var presetTargets: [String: Double] = [:]
            for spec in oapsPresetTarget {
                let parts = spec.split(separator: ":", maxSplits: 1).map { $0.trimmingCharacters(in: .whitespaces) }
                if parts.count == 2, let tgt = Double(parts[1]) { presetTargets[parts[0]] = tgt }
            }
            dataSource = NightscoutEvalDataSource(client: client, cache: cache, insulinType: baselinePreset, applyOverrides: applyOverrides, presetTargets: presetTargets)
        }
        let engine = EvaluationEngine(dataSource: dataSource)

        printStderr("Fetching data... ")
        var data = try await engine.prefetchData(for: interval, config: baselineConfig)  // swiftlint:disable:this let_var_whitespace
        printStderr("done\n")

        // CONTROLLER insulin-model override. The controller's belief lives in two
        // places: the therapy timeline (what new candidate doses get stamped with)
        // and the stamps already on the real dose history (what LoopAlgorithm reads
        // back for IOB/effects). Both must move together, or the arm believes two
        // different insulins at once. The PLANT is unaffected — it re-stamps these
        // same doses onto --patient-insulin-model inside the simulator.
        if let cm = parsedControllerInsulinModel {
            let was = data.therapyTimeline.insulinType
            var tl = data.therapyTimeline
            tl.insulinType = cm
            let restamped = data.doses.map { (d: EvalInsulinDose) -> EvalInsulinDose in
                var x = d; x.insulinType = cm; return x
            }
            data = PreloadedData(glucose: data.glucose, doses: restamped,
                                 carbs: data.carbs, therapyTimeline: tl)
            printStderr("controller insulin model: \(was) -> \(cm) (therapy belief + \(restamped.count) dose stamps); plant unaffected\n")
        }
        if !insulinTypeChanges.isEmpty {
            var tl = data.therapyTimeline
            tl.insulinTypeChanges = insulinTypeChanges
            data = PreloadedData(glucose: data.glucose, doses: data.doses,
                                 carbs: data.carbs, therapyTimeline: tl)
        }

        // Optional per-step ISF multiplier CSV (time → multiplier).
        let isfMultMap: [Date: Double]?
        if let path = candidateIsfCsv {
            isfMultMap = try Self.loadIsfMultiplierCSV(
                path: path,
                stepSeconds: TimeInterval(stepMinutes) * 60
            )
            printStderr("Loaded ISF CSV: \(isfMultMap?.count ?? 0) per-step multipliers; mean=\(isfMultMap.map { $0.values.reduce(0, +) / Double($0.count) } ?? 1.0)\n")
        } else {
            isfMultMap = nil
        }

        // Optional per-step forecast-offset CSV (time → mg/dL). Reuses the same
        // (time, value) loader as the ISF CSV; values are BG offsets, not multipliers.
        let forecastOffsetMap: [Date: Double]?
        if let path = candidateForecastOffsetCsv {
            forecastOffsetMap = try Self.loadIsfMultiplierCSV(
                path: path,
                stepSeconds: TimeInterval(stepMinutes) * 60
            )
            let vals = forecastOffsetMap.map { Array($0.values) } ?? []
            let mean = vals.isEmpty ? 0 : vals.reduce(0, +) / Double(vals.count)
            printStderr("Loaded forecast-offset CSV: \(forecastOffsetMap?.count ?? 0) per-step offsets; mean=\(String(format: "%.2f", mean)) mg/dL, max=\(String(format: "%.1f", vals.max() ?? 0))\n")
        } else {
            forecastOffsetMap = nil
        }

        let outages: [Outage]
        // Like decision_times.csv, disruption windows are a DATASET property: an
        // export that ships disruptions.csv (ETL v3+ — suspends, loop-offline gaps,
        // pump-error cycles) is simulated with delivery clamped in those windows.
        // Without the auto-detect, a closed-loop/CF run that forgot --outages-csv
        // silently dosed straight through pump-error windows where the field
        // delivered nothing. Explicit --outages-csv always wins.
        var effectiveOutagesCsv = outagesCsv
        if effectiveOutagesCsv == nil, let dir = dataDir {
            let candidate = URL(fileURLWithPath: dir).appendingPathComponent("disruptions.csv").path
            if FileManager.default.fileExists(atPath: candidate) {
                effectiveOutagesCsv = candidate
                printStderr("Using the dataset's disruption windows (disruptions.csv)\n")
            }
        }
        if let csv = effectiveOutagesCsv {
            outages = try OutageCSV.load(from: csv)
            printStderr("Loaded \(outages.count) outage(s) from \(csv)\n")
            let totalMin = outages.reduce(0.0) { $0 + $1.interval.duration / 60 }
            printStderr("  total outage time: \(String(format: "%.0f", totalMin)) min "
                        + "(\(String(format: "%.2f", totalMin / (interval.duration / 60) * 100))% of window)\n")
        } else {
            outages = []
        }

        var parsedDecisionTimes: [Date] = []
        var parsedNoDoseGuardTimes: Set<Date> = []
        var parsedBolusInProgressTimes: Set<Date> = []
        var parsedTempStrategyTimes: Set<Date> = []
        // Cadence is a DATASET property: an export that carries the field's recorded
        // decision instants (decision_times.csv, ETL v8+) is replayed on that cadence;
        // otherwise the CGM cadence + processing-delay estimate stands in. Explicit
        // --decision-times-csv always wins; --no-decisions-from-cgm disables both.
        var effectiveDecisionTimesCsv = decisionTimesCsv
        if effectiveDecisionTimesCsv == nil, decisionsFromCgm, let dir = dataDir {
            let candidate = URL(fileURLWithPath: dir).appendingPathComponent("decision_times.csv").path
            if FileManager.default.fileExists(atPath: candidate) {
                effectiveDecisionTimesCsv = candidate
                printStderr("Using the dataset's recorded decision cadence (decision_times.csv)\n")
            }
        }
        if let csvPath = effectiveDecisionTimesCsv {
            let iso = ISO8601DateFormatter()
            iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            let isoNoFrac = ISO8601DateFormatter()
            let text = try String(contentsOfFile: csvPath, encoding: .utf8)
            // NOT split(separator: "\n"): CRLF is ONE grapheme cluster in Swift, so a
            // "\n" separator never matches inside "\r\n" and a CRLF file parses as a
            // single line (observed: "Stepping at 0 recorded decision times").
            var guardIdx: Int? = nil
            var modeIdx: Int? = nil
            var bipIdx: Int? = nil
            for line in text.split(whereSeparator: { $0.isNewline }) {
                // first column = the instant; further columns (rec fields) are for scorers,
                // except `no_dose_guard` (ETL v13): cycles the field controller ran but
                // bailed before the dosing path (pumpDataTooOld / glucoseTooOld) — the
                // replay must skip those instants entirely.
                let cols = line.split(separator: ",", omittingEmptySubsequences: false)
                    .map { String($0).trimmingCharacters(in: .whitespaces) }
                let tok = cols[0]
                if tok.isEmpty { continue }
                if tok == "t" {
                    guardIdx = cols.firstIndex(of: "no_dose_guard")
                    modeIdx = cols.firstIndex(of: "mode")
                    bipIdx = cols.firstIndex(of: "bolus_in_progress")
                    continue
                }
                if let d = iso.date(from: tok) ?? isoNoFrac.date(from: tok) {
                    parsedDecisionTimes.append(d)
                    if let gi = guardIdx, gi < cols.count, cols[gi] == "1" {
                        parsedNoDoseGuardTimes.insert(d)
                    }
                    if let bi = bipIdx, bi < cols.count, cols[bi] == "1" {
                        parsedBolusInProgressTimes.insert(d)
                    }
                    if let mi = modeIdx, mi < cols.count, cols[mi] == "temp" {
                        parsedTempStrategyTimes.insert(d)
                    }
                }
            }
            printStderr("Stepping at \(parsedDecisionTimes.count) recorded decision times from \(csvPath)"
                        + (parsedNoDoseGuardTimes.isEmpty ? "" : " (\(parsedNoDoseGuardTimes.count) no-dose-guard cycles skipped)")
                        + (parsedBolusInProgressTimes.isEmpty ? "" : " (\(parsedBolusInProgressTimes.count) bolus-in-progress cycles skipped)")
                        + (parsedTempStrategyTimes.isEmpty ? "\n" : " (\(parsedTempStrategyTimes.count) temp-strategy cycles)\n"))
            // These instants ARE the controller's real decision timestamps — anchor
            // momentum/RC on them directly, not on the lastGlucose+7s estimate.
            baselineConfig.decisionTimesAreAuthoritative = true
            candidateConfig.decisionTimesAreAuthoritative = true
        }

        let plant: ExternalPlant?
        if let cmd = externalPlant {
            guard candidateCounterfactual else {
                throw ValidationError("--external-plant requires --candidate-counterfactual")
            }
            plant = try ExternalPlant(command: cmd)
            if plantBehavior { printStderr("Plant behavior: carb entries and manual boluses come from the plant\n") }
            printStderr("External plant: \(cmd)\n")
        } else {
            guard !plantBehavior else { throw ValidationError("--plant-behavior requires --external-plant") }
            plant = nil
        }
        printStderr("Running closed-loop simulation (sequential, ~10× slower than bench)...\n")
        var candidateTherapy: TherapyTimeline? = nil
        if let path = candidateSchedulesJson {
            let dec = JSONDecoder()
            dec.dateDecodingStrategy = .iso8601
            let other = try dec.decode(TherapyTimeline.self, from: Data(contentsOf: URL(fileURLWithPath: path)))
            var tl = data.therapyTimeline
            tl.basal = other.basal
            tl.sensitivity = other.sensitivity
            tl.carbRatio = other.carbRatio
            tl.target = other.target
            if !tl.rawBasal.isEmpty {
                tl.rawBasal = other.rawBasal.isEmpty ? other.basal : other.rawBasal
                tl.rawSensitivity = other.rawSensitivity.isEmpty ? other.sensitivity : other.rawSensitivity
                tl.rawCarbRatio = other.rawCarbRatio.isEmpty ? other.carbRatio : other.rawCarbRatio
                tl.rawTarget = other.rawTarget.isEmpty ? other.target : other.rawTarget
            }
            candidateTherapy = tl
        }
        let simResult = try await engine.simulateClosedLoop(
            data: data,
            interval: interval,
            baselineConfig: baselineConfig,
            candidateConfig: candidateConfig,
            baselineLabel: baselineLabel,
            candidateLabel: candidateLabel,
            isfMultiplierByStep: isfMultMap,
            forecastOffsetByStep: forecastOffsetMap,
            isfBoostActiveOnly: candidateIsfBoostActiveOnly,
            egpPhysicalDecomposition: candidateEgpPhysical,
            isfBoostGateEventualMgdl: candidateIsfBoostGateEventual,
            isfBoostVetoIceRate: candidateIsfBoostVetoIce,
            outages: outages,
            outageBasalContinuesReasons: Set((outageBasalReasons ?? "").split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }),
            cgmStaleGuardSec: cgmStaleGuardMin * 60,
            counterfactualMode: candidateCounterfactual,
            decisionTimeReplay: decisionTimeReplay,
            counterfactualBurnInSec: candidateCounterfactualBurnInHours * 3600,
            cfIdentity: cfIdentity,
            decisionsFromCgm: decisionsFromCgm,
            decisionTimes: parsedDecisionTimes,
            noDoseGuardTimes: parsedNoDoseGuardTimes,
            bolusInProgressTimes: parsedBolusInProgressTimes,
            enableTimeBasedAF: timeBasedAf,
            tempStrategyTimes: parsedTempStrategyTimes,
            excludeManualBoluses: noUserBoluses,
            suppressCarbs: noCarbEntries,
            counterRegOnsetMgdl: counterRegOnset,
            counterRegGain: counterRegGain,
            counterRegMaxRate: counterRegMax,
            cfGapReanchorSec: cfGapReanchorMin * 60,
            patientISF: patientIsf,
            patientInsulinType: parsedPatientInsulinModel,
            inferSensitivity: candidateInferSensitivity,
            inferSensitivityMax: candidateInferSensitivityMax,
            inferSensitivityWindowSec: candidateInferSensitivityWindowMin * 60,
            inferSensitivitySmoothSec: candidateInferSensitivitySmoothMin * 60,
            inferSensitivitySmoothPrior: candidateInferSensitivitySmoothPrior,
            dumpNiePath: candidateDumpNieCsv,
            useOpenAPSForCandidate: candidateOpenaps,
            useLoopMimicForCandidate: candidateLoopMimicOaps,
            sensorCapMgdl: sensorCapMgdl,
            externalPlant: plant,
            plantBehavior: plantBehavior,
            candidateTherapy: candidateTherapy,
            progress: Self.makeProgressReporter()
        )
        plant?.finish()
        printStderr("Progress: 100%\n")

        // Emit trace JSON in the same shape as bench --trace-out so the
        // existing python report script can consume it. Add a `closedLoop`
        // flag in the JSON so consumers can distinguish.
        try Self.writeTrace(
            simResult: simResult,
            data: data,
            to: URL(fileURLWithPath: traceOut),
            exportDataVersion: exportProvenance?.version,
            provenanceWarnings: exportProvenance?.warnings ?? []
        )
        printStderr("Closed-loop trace → \(traceOut)\n")
    }

    /// Oldest export DATA_VERSION validated against the field (bddp cohort, 2026-10-11: 9/11 donors
    /// match on lows and TIR at v18/v19). Older exports predate fidelity fixes the replay depends on --
    /// per-cycle strategy mode (v15), carb visibility (v16), basalType (v17), deployed maxBolus (v14) --
    /// and unversioned ones may predate the bolus dedup (e128da3) that stopped HealthKit mirrors
    /// replaying Loop's automatic boluses as manual. Bump deliberately when an ETL change matters.
    /// Raised to 22 (2026-10-11): manual temp basals (v21; i040's lows 13 -> 1, field 1),
    /// second-app dose records and unpaired status suspends (v22; month-long false disruptions).
    /// Raised to 23: dated max basal / max bolus / suspend threshold (61 of 206 pilot donors changed
    /// max basal in-window; i017 was capped at 2.0 U/h through months at 3.0).
    static let validatedExportDataVersion = 23

    /// Provenance check for a --data-dir export, run before the replay starts. Returns the export's
    /// data_version (nil if unstamped) and human-readable warnings; never throws, never blocks -- a
    /// sweep may override a donor flag on purpose, and other roles' scripts must not break.
    ///
    /// Two checks:
    ///  * `_export_manifest.json` -- missing, or a data_version below `validatedExportDataVersion`.
    ///  * `replay_config.json` (optional, next to the export) -- `{"required_flags": ["--flag",
    ///    "--flag value", ...], "notes": "..."}`: the flags that make THIS donor deployment-faithful.
    ///    Each entry must appear in the command line as that exact token sequence.
    static func checkExportProvenance(dataDir: String, arguments: [String]) -> (version: Int?, warnings: [String]) {
        var warnings: [String] = []
        var version: Int? = nil
        let dir = URL(fileURLWithPath: dataDir)
        let manifestURL = dir.appendingPathComponent("_export_manifest.json")
        if let raw = try? Data(contentsOf: manifestURL),
           let obj = try? JSONSerialization.jsonObject(with: raw) as? [String: Any] {
            version = (obj["data_version"] as? NSNumber)?.intValue
            if let v = version, v < validatedExportDataVersion {
                warnings.append("export data_version \(v) is older than \(validatedExportDataVersion), the oldest validated against the field -- re-export before trusting absolute outcomes")
            } else if version == nil {
                warnings.append("export manifest has no data_version -- cannot tell which ETL fixes it carries")
            }
        } else {
            warnings.append("no _export_manifest.json -- this export predates version stamping and may predate the bolus-dedup fix (Loop automatic boluses replayed as manual); re-export before trusting absolute outcomes")
        }
        let cfgURL = dir.appendingPathComponent("replay_config.json")
        if let raw = try? Data(contentsOf: cfgURL),
           let obj = try? JSONSerialization.jsonObject(with: raw) as? [String: Any],
           let req = obj["required_flags"] as? [String] {
            let joined = " " + arguments.joined(separator: " ") + " "
            let missing = req.filter { !joined.contains(" " + $0 + " ") }
            if !missing.isEmpty {
                let note = (obj["notes"] as? String).map { " (\($0))" } ?? ""
                warnings.append("replay_config.json requires flags not on this command line: \(missing.joined(separator: ", "))\(note) -- the replay is NOT deployment-faithful for this donor")
            }
        }
        return (version, warnings)
    }

    static func writeTrace(
        simResult: ClosedLoopSimResult,
        data: PreloadedData,
        to url: URL,
        exportDataVersion: Int? = nil,
        provenanceWarnings: [String] = []
    ) throws {
        let mgdlUnit = LoopUnit.milligramsPerDeciliter
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        struct Pred: Codable {
            let t: String
            let baselineDose: Double
            let candidateDose: Double
            let deltaDose: Double
            let isf: Double
            let candidateBolus: Double      // auto-bolus U this step
            let candidateTempRate: Double   // temp basal rate U/hr this step
            let candidateTempAction: String // temp-strategy ifNecessary action: set|cancel|none
            let baselineEventualBG: Double  // sim Loop forecast on REAL BG (vs field devicestatus)
            let baselineIOB: Double
            let baselineCOB: Double
            let baselineMomentum: Double    // net momentum contribution to forecast (mg/dL)
            let baselineRC: Double          // net retrospective-correction contribution (mg/dL)
            let baselineDiscrepancy: Double // latest 30-min RC discrepancy (mg/dL)
            let candidateEventualBG: Double // sim Loop forecast on counter BG (CF)
            let candidateIOB: Double
            let candidateCOB: Double
            let candidateMomentum: Double   // candidate's net momentum contribution IN ISOLATION (mg/dL)
            let candidateRC: Double         // candidate's net RC contribution IN ISOLATION (mg/dL); = asym-IRC when enabled
            let candidateMomentumMarginal: Double // MARGINAL effect on eventualBG (with - without momentum; accounts for blend)
            let candidateRCMarginal: Double       // MARGINAL effect on eventualBG (with - without RC)
            let candidateAutosensRatio: Double  // OAPS autosens ratio (nan for Loop)
            let candidateMinGuardBG: Double     // OAPS predicted-min BG gating SMB (nan for Loop)
            let candidateMinPredBG: Double      // OAPS predicted-min BG (nan for Loop)
            let candidateICE: Double            // raw insulin-counteraction effect, latest interval (mg/dL)
            let candidateCarbEffect: Double     // ICE portion absorbed by dynamic carbs (mg/dL)
            let candidateDiscrepancy: Double    // ICE − carbEffect = RC-bound remainder (mg/dL)
            let candidateSensModeMult: Double   // Sensitive Mode ISF multiplier (1.0 = inactive)
            let candidateManualBolusRecOut: Double // candidate recommended MANUAL bolus this step (pre-factor full correction)
            let plantBolusU: Double             // --plant-behavior: bolus delivered this step at the plant person's request
            let plantCarbsG: Double             // --plant-behavior: carbs the plant person entered during this step
            // PATIENT IOB — field dosing and candidate dosing through the SAME patient
            // insulin model (net-basal, scheduled-gap-filled). Independent of NS
            // devicestatus timing and of any candidate IOB-method changes. Use these
            // as the fair field-vs-candidate IOB comparison.
            let patientIOBField: Double
            let patientIOBCandidate: Double
            let baselinePredCurve: [Double]?       // full baseline forecast curve (mg/dL, 5-min spaced from t); nil unless --export-forecast-curve
        }
        struct ActualSample: Codable { let t: String; let bg: Double }
        struct CounterSample: Codable { let t: String; let bg: Double? }   // nil: the plant's CGM gave no reading
        struct CurvePoint: Codable { let tMin: Double; let percentRemaining: Double; let percentDelivered: Double }
        // Canonical insulin-delivery stream — uniform for both arms so a renderer
        // can plot ACTUAL delivery (basal rate + boluses, auto vs manual) without
        // reconstructing it from caches. `source` = "field" (real pump history) or
        // "candidate" (what the candidate controller delivered). `kind` = "basal"
        // or "bolus". For basal, `rateUhr` is the delivered rate and `amountU` the
        // units over [t, tEnd]; for bolus, `amountU` is the bolus and `rateUhr` nil.
        // NOTE: `Pred.baselineDose` is a decision-time RECOMMENDATION, NOT delivery —
        // use this stream (source=="field") for what the pump actually delivered.
        struct DeliveryRecord: Codable {
            let t: String
            let tEnd: String?
            let source: String
            let kind: String
            let automatic: Bool
            let amountU: Double
            let rateUhr: Double?
        }
        struct Trace: Codable {
            let baselineLabel: String
            let candidateLabel: String
            let intervalStart: String
            let intervalEnd: String
            let activityDurationMinutes: Double
            let predictions: [Pred]
            let actual: [ActualSample]
            let counter: [CounterSample]   // closed-loop trajectory (NEW)
            let delivery: [DeliveryRecord] // canonical actual-delivery stream (NEW)
            let insulinActivityCurve: [CurvePoint]
            let closedLoop: Bool
            let exportDataVersion: Int?          // --data-dir export's manifest version (nil = unstamped)
            let provenanceWarnings: [String]     // stale export / missing donor flags; empty = clean
        }

        let preds = simResult.steps.map {
            Pred(t: formatter.string(from: $0.t),
                 baselineDose: $0.baselineDose,
                 candidateDose: $0.candidateDose,
                 deltaDose: $0.deltaDose,
                 isf: $0.isf,
                 candidateBolus: $0.candidateBolus,
                 candidateTempRate: $0.candidateTempRate,
                 candidateTempAction: $0.candidateTempAction,
                 baselineEventualBG: $0.baselineEventualBG,
                 baselineIOB: $0.baselineIOB,
                 baselineCOB: $0.baselineCOB,
                 baselineMomentum: $0.baselineMomentum,
                 baselineRC: $0.baselineRC,
                 baselineDiscrepancy: $0.baselineDiscrepancy,
                 candidateEventualBG: $0.candidateEventualBG,
                 candidateIOB: $0.candidateIOB,
                 candidateCOB: $0.candidateCOB,
                 candidateMomentum: $0.candidateMomentum,
                 candidateRC: $0.candidateRC,
                 candidateMomentumMarginal: $0.candidateMomentumMarginal.isFinite ? $0.candidateMomentumMarginal : 0.0,
                 candidateRCMarginal: $0.candidateRCMarginal.isFinite ? $0.candidateRCMarginal : 0.0,
                 candidateAutosensRatio: $0.candidateAutosensRatio.isFinite ? $0.candidateAutosensRatio : -1.0,
                 candidateMinGuardBG: $0.candidateMinGuardBG.isFinite ? $0.candidateMinGuardBG : -1.0,
                 candidateMinPredBG: $0.candidateMinPredBG.isFinite ? $0.candidateMinPredBG : -1.0,
                 candidateICE: $0.candidateICE.isFinite ? $0.candidateICE : 0.0,
                 candidateCarbEffect: $0.candidateCarbEffect.isFinite ? $0.candidateCarbEffect : 0.0,
                 candidateDiscrepancy: $0.candidateDiscrepancy.isFinite ? $0.candidateDiscrepancy : 0.0,
                 candidateSensModeMult: $0.candidateSensModeMult.isFinite ? $0.candidateSensModeMult : 1.0,
                 candidateManualBolusRecOut: $0.candidateManualBolusRecOut.isFinite ? $0.candidateManualBolusRecOut : 0.0,
                 plantBolusU: $0.plantBolusU,
                 plantCarbsG: $0.plantCarbsG,
                 patientIOBField: $0.patientIOBField.isFinite ? $0.patientIOBField : 0.0,
                 patientIOBCandidate: $0.patientIOBCandidate.isFinite ? $0.patientIOBCandidate : 0.0,
                 baselinePredCurve: $0.baselinePredCurve.isEmpty ? nil : $0.baselinePredCurve)
        }
        let actualOut = data.glucose.sorted { $0.startDate < $1.startDate }.map {
            ActualSample(t: formatter.string(from: $0.startDate),
                         bg: $0.quantity.doubleValue(for: mgdlUnit))
        }
        let counterOut = simResult.steps.map {
            CounterSample(t: formatter.string(from: $0.t), bg: $0.counterBG.isFinite ? $0.counterBG : nil)
        }
        let insulinModel = data.therapyTimeline.insulinType.model
        let dur = insulinModel.effectDuration
        var curve: [CurvePoint] = []
        var τ: TimeInterval = 0
        while τ <= dur {
            let pr = insulinModel.percentEffectRemaining(at: τ)
            curve.append(CurvePoint(tMin: τ / 60.0, percentRemaining: pr, percentDelivered: 1.0 - pr))
            τ += 5 * 60
        }

        // ---- Canonical delivery stream (both arms, uniform schema) -------------
        var delivery: [DeliveryRecord] = []
        // FIELD: the real pump history that actually fed the field IOB.
        let dLo = simResult.intervalStart.addingTimeInterval(-6 * 3600)
        // Boluses: raw pump events (preserve the real automatic/manual flag).
        for d in data.doses
        where d.deliveryType == .bolus && d.startDate >= dLo && d.startDate <= simResult.intervalEnd {
            delivery.append(DeliveryRecord(
                t: formatter.string(from: d.startDate),
                tEnd: formatter.string(from: d.endDate),
                source: "field", kind: "bolus", automatic: d.automatic,
                amountU: d.volume, rateUhr: nil))
        }
        // Basal: the CONTINUOUS delivered rate — temp basal where a temp is active,
        // scheduled basal otherwise — via gap-filled annotation, so the field basal
        // staircase has no holes (raw dose entries only record temps, not the
        // scheduled basal that runs between them).
        let fieldBasalAnnotated = data.doses.annotated(with: data.therapyTimeline.basal, fillBasalGaps: true)
        for d in fieldBasalAnnotated {
            guard case .basal = d.type,
                  d.endDate > dLo, d.startDate <= simResult.intervalEnd else { continue }
            // Skip sub-minute segments: consecutive real temps have ~1-second
            // timestamp gaps, and gap-filling inserts a 1-second scheduled-basal
            // slice there — a spurious rate spike. Real basal segments are minutes.
            guard d.endDate.timeIntervalSince(d.startDate) >= 60 else { continue }
            let hours = max(d.endDate.timeIntervalSince(d.startDate), 0) / 3600.0
            let rate = hours > 0 ? d.volume / hours : 0.0
            delivery.append(DeliveryRecord(
                t: formatter.string(from: d.startDate),
                tEnd: formatter.string(from: d.endDate),
                source: "field", kind: "basal", automatic: true,
                amountU: d.volume, rateUhr: rate))
        }
        // CANDIDATE: what the candidate controller delivered each step — the temp
        // basal it set (rate) plus any auto-bolus. Emitted per 5-min step. In CF
        // mode all candidate delivery is automatic. Basal records are run-length
        // compacted (one span per unchanged rate) to keep the trace small.
        // amountU is what the pump DELIVERED (whole pulses), not the commanded rate × time --
        // this stream is documented as actual delivery and is compared against the field's
        // delivered volumes. rateUhr keeps the commanded rate for reference. Steps without a
        // recorded delivery (burn-in) fall back to rate × time.
        let stepDur: TimeInterval = 5 * 60
        var runStart: Date? = nil
        var runRate = Double.nan
        var runDelivered = 0.0
        var runAllMeasured = true
        func flushBasalRun(endingAt end: Date) {
            guard let s = runStart, runRate.isFinite else { return }
            let hours = max(end.timeIntervalSince(s), 0) / 3600.0
            delivery.append(DeliveryRecord(
                t: formatter.string(from: s), tEnd: formatter.string(from: end),
                source: "candidate", kind: "basal", automatic: true,
                amountU: runAllMeasured ? runDelivered : runRate * hours, rateUhr: runRate))
        }
        for step in simResult.steps {
            let r = step.candidateTempRate
            if !(r.isFinite && r == runRate) {
                flushBasalRun(endingAt: step.t)
                runStart = r.isFinite ? step.t : nil
                runRate = r
                runDelivered = 0; runAllMeasured = true
            }
            if step.candidateBasalDeliveredU.isFinite { runDelivered += step.candidateBasalDeliveredU }
            else { runAllMeasured = false }
            if step.candidateBolus > 0 {
                delivery.append(DeliveryRecord(
                    t: formatter.string(from: step.t), tEnd: nil,
                    source: "candidate", kind: "bolus", automatic: true,
                    amountU: step.candidateBolus, rateUhr: nil))
            }
        }
        if let last = simResult.steps.last { flushBasalRun(endingAt: last.t.addingTimeInterval(stepDur)) }
        // Candidate MANUAL boluses: the user's manual boluses are passed through
        // (and possibly resized) into the candidate's actual delivery. They live
        // in counterfactualDoses (automatic == false), NOT in candidateBolus
        // (auto-only). Emit them so the candidate stream is complete.
        for d in simResult.counterfactualDoses
        where d.deliveryType == .bolus && !d.automatic
              && d.startDate >= dLo && d.startDate <= simResult.intervalEnd {
            delivery.append(DeliveryRecord(
                t: formatter.string(from: d.startDate), tEnd: nil,
                source: "candidate", kind: "bolus", automatic: false,
                amountU: d.volume, rateUhr: nil))
        }

        let trace = Trace(
            baselineLabel: simResult.baselineLabel,
            candidateLabel: simResult.candidateLabel,
            intervalStart: formatter.string(from: simResult.intervalStart),
            intervalEnd: formatter.string(from: simResult.intervalEnd),
            activityDurationMinutes: dur / 60.0,
            predictions: preds,
            actual: actualOut,
            counter: counterOut,
            delivery: delivery,
            insulinActivityCurve: curve,
            closedLoop: true,
            exportDataVersion: exportDataVersion,
            provenanceWarnings: provenanceWarnings
        )

        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted]
        let json = try encoder.encode(trace)
        try json.write(to: url)
    }

    /// Parse a (time, isf_multiplier) CSV. Returns a per-step lookup keyed
    /// by step time (rounded to nearest `stepSeconds` grid). Header row is
    /// auto-skipped if its second column doesn't parse as a number.
    static func loadIsfMultiplierCSV(
        path: String,
        stepSeconds: TimeInterval
    ) throws -> [Date: Double] {
        let text = try String(contentsOfFile: path, encoding: .utf8)
        // Strict ISO8601 first, then a permissive fallback that accepts the
        // pandas-default "YYYY-MM-DD HH:MM:SS+00:00" (space separator instead
        // of 'T'). We lost a debugging session because pandas produced the
        // space form and ISO8601DateFormatter silently rejected every row.
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime]
        let isoFrac = ISO8601DateFormatter()
        isoFrac.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        var out: [Date: Double] = [:]
        for raw in text.split(separator: "\n", omittingEmptySubsequences: true) {
            let line = raw.trimmingCharacters(in: .whitespacesAndNewlines)
            if line.isEmpty { continue }
            let parts = line.split(separator: ",", maxSplits: 2).map { String($0).trimmingCharacters(in: .whitespaces) }
            guard parts.count >= 2 else { continue }
            guard let mult = Double(parts[1]) else { continue }
            // Normalize space-separator → 'T' before handing to ISO8601 parser
            let tsStr: String = {
                var s = parts[0]
                if s.count > 10, s[s.index(s.startIndex, offsetBy: 10)] == " " {
                    s.replaceSubrange(s.index(s.startIndex, offsetBy: 10)...s.index(s.startIndex, offsetBy: 10), with: "T")
                }
                return s
            }()
            guard let t = iso.date(from: tsStr) ?? isoFrac.date(from: tsStr) else { continue }
            let rounded = Date(timeIntervalSince1970:
                (t.timeIntervalSince1970 / stepSeconds).rounded() * stepSeconds)
            out[rounded] = mult
        }
        return out
    }

    /// Returns a `@Sendable` progress callback that prints a newline-per-event
    /// "Progress: X%  elapsed=…s  ETA=…s" line — at most every 2 seconds AND
    /// at every whole-percent change. Newlines so `tee` / log monitors see
    /// updates; the throttle keeps it from spamming on per-step calls.
    static func makeProgressReporter() -> @Sendable (Double) -> Void {
        let state = ProgressState()
        return { f in
            let pct = Int(f * 100)
            let now = Date()
            state.lock.lock()
            defer { state.lock.unlock() }
            let elapsed = now.timeIntervalSince(state.startedAt)
            let dueByPct = pct > state.lastPctReported
            let dueByTime = now.timeIntervalSince(state.lastReportAt) >= 2.0
            if dueByPct || dueByTime {
                let eta = pct > 0 ? Int(elapsed * (100.0 - Double(pct)) / Double(pct)) : 0
                printStderr("Progress: \(pct)%  elapsed=\(Int(elapsed))s  ETA=\(eta)s\n")
                state.lastPctReported = pct
                state.lastReportAt = now
            }
        }
    }

    private final class ProgressState: @unchecked Sendable {
        let lock = NSLock()
        let startedAt = Date()
        var lastReportAt = Date()
        var lastPctReported: Int = -1
    }

}
