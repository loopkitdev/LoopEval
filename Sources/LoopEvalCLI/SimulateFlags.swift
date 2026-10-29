// SimulateFlags.swift — `simulate`'s flags, grouped by the part of the simulation they configure.
//
// Each group is one section of `simulate --help`. SimulateCommand holds the groups and forwards
// every flag under its old property name (extension at the end), so `run()` reads them unchanged.

import ArgumentParser
import EvalCore
import Foundation
import LoopAlgorithm

// Data and output
struct SimulateDataFlags: ParsableArguments {
    @Option(name: .long, help: "Nightscout base URL (omit when using --data-dir)")
    var nightscoutUrl: String = ""

    @Option(name: .long, help: "Directory of pre-exported EvalCore JSON files (glucose/doses/carbs/therapy) — uses JSONFileDataSource instead of Nightscout. For non-Nightscout datasets (e.g. Tidepool BDDP exported via loopeval_analysis.tidepool.etl).")
    var dataDir: String?

    @Option(name: .long, help: "Start date — ISO8601")
    var start: String

    @Option(name: .long, help: "End date   — ISO8601")
    var end: String

    @Option(name: .long, help: "Nightscout API secret (optional)")
    var apiSecret: String?

    @Option(name: .long, help: "Nightscout subject access token (optional; for ?token= role auth)")
    var token: String?

    @Option(name: .long, help: "Cache directory", transform: URL.init(fileURLWithPath:))
    var cacheDir: URL = URL(fileURLWithPath: NSHomeDirectory())
        .appendingPathComponent(".loop-eval/cache")

    @Option(name: .long, help: "Baseline label")
    var baselineLabel: String = "Baseline"

    @Option(name: .long, help: "Candidate label")
    var candidateLabel: String = "Candidate"

    @Option(name: .long, help: "Local timezone identifier")
    var localTimezone: String?

    @Option(name: .long, help: "Output trace JSON path (compatible with tir_methodology_report.py)")
    var traceOut: String

    @Flag(name: .long, help: "Export the full baseline and candidate forecast curves per step (baselinePredCurve, candidatePredCurve) into the trace, for point-by-point comparison against field devicestatus predicted.values.")
    var exportForecastCurve: Bool = false
}

// Run mode and decision timing
struct SimulateModeFlags: ParsableArguments {
    @Flag(name: .long, help: "Disable Kalman smoothing")
    var noKalman: Bool = false

    @Flag(name: .long, inversion: .prefixedNo, help: "Run the SIMULATOR (Loop decision-time glucose input, the counter trajectory, and outcome stats) on the ORIGINAL noisy CGM samples, while keeping the RTS-smoothed trace for patient-physiology estimation (ICE + sensitivity multiplier m(t)). Raw samples are resampled onto the smoothed grid's exact timestamps so the per-grid m(t) stays aligned. Requires Kalman smoothing (no effect with --no-kalman). DEFAULT ON; pass --no-sim-raw-glucose for the legacy all-smoothed sim.")
    var simRawGlucose: Bool = true

    @Option(name: .long, help: "Eval step (minutes, default 5)")
    var stepMinutes: Int = 5

    @Flag(name: .long, help: "Oracle mode: let sim Loop see future doses in its prediction dose window (legacy backward-compat default behavior). Causes sim Loop to forecast based on insulin it hasn't 'delivered yet' — produces dramatically over-suspended decisions. Default OFF — clean real-time replay.")
    var oracleFutureInputs: Bool = false

    @Flag(name: .long, help: "Counterfactual sim mode: candidate's recommendations REPLACE real-pump deliveries (not just add as marginal delta vs sim Loop alone). Required for evaluating candidates that fundamentally diverge from real Loop's dosing. Loop's prediction sees only candidate's accumulated deliveries (warm-up-seeded with real pump for the DIA preceding sim start so initial IOB matches reality).")
    var candidateCounterfactual: Bool = false

    @Flag(name: .long, help: "Decision-time replay (NOT a closed loop): both arms see the IDENTICAL real glucose/insulin/carb history at every step and emit a dose recommendation WITHOUT acting. For same-input Loop-vs-oref dose & forecast comparison against the insulin-hole oracle. Neither arm's recommendation feeds back. With candidate == Loop, baselineDose must equal candidateDose at every step (fairness identity check). Do not combine with --candidate-counterfactual or --candidate-infer-sensitivity.")
    var decisionTimeReplay: Bool = false

    @Flag(name: .long, help: "CF-IDENTITY harness (requires --candidate-counterfactual): force the candidate to deliver EXACTLY the real dose history through the physiological advance (no re-dosing). The counter MUST then reproduce the actual CGM to within rounding. Tests the patient-model advance in isolation from the controller.")
    var cfIdentity: Bool = false

    @Flag(name: .long, inversion: .prefixedNo, help: "CGM-driven decisions: trigger ONE automatic dosing decision per real CGM sample (irregular ~5-min cadence), never on a fixed grid or any other event. The substrate is built on the raw CGM timestamps with variable per-step dt. DEFAULT ON — the faithful CF substrate (validated 2026-06-23 to reproduce field within ~0.5 TIR with exact cf-identity and NO CGM-gap masking, since the counter runs on the real CGM at real times and temp basals expire at 30 min across gaps). Pass --no-decisions-from-cgm for the legacy fixed 5-min grid march (resamples raw CGM onto the grid → smooths lows, needs gap masking). Physiology (ICE/sensitivity) is RTS-smoothed in place at the CGM times.")
    var decisionsFromCgm: Bool = true

    @Option(name: .customLong("decision-times-csv"),
            help: "CSV of ISO8601 instants (header 't' optional) — step the replay at EXACTLY the real controller's recorded dosingDecision times instead of the CGM cadence. Removes synthetic steps the field never made (multi-source 1-min streams) and steps inside field skip-gaps. Marks the instants authoritative for the momentum/RC now-anchor.")
    var decisionTimesCsv: String? = nil

    @Option(name: .long, help: "Counterfactual burn-in hours (default 6.0): real-pump deliveries drive the sim for this period before counterfactual divergence starts. Gives candidate's prediction a fully-realistic recent dose history at the moment CF mode activates.")
    var candidateCounterfactualBurnInHours: Double = 6.0

    @Option(name: .long, help: "Hours of glucose history fed to the controller each step. Default 10. oref's autosens wants ~24h — raise to 24 for a representative OpenAPS autosens (Loop only uses recent glucose for momentum/RC, so it's ~insensitive).")
    var glucoseLookbackHours: Double = 10.0

    @Option(name: .long, help: "Hours of insulin (dose) history fed to the controller each step. Default 16. oref needs ≥24h to compute IOB (DIA up to ~9h), autosens, and TDD (Dynamic ISF) — raise to 24+ for a faithful OpenAPS replay. Loop is ~insensitive beyond its DIA.")
    var insulinLookbackHours: Double = 16.0

    @Option(name: .long, help: "CGM stale-data guard (minutes). Loop refuses to issue a new dose when the latest glucose is older than its inputDataRecencyInterval (15min). The sim's per-step dose path bypasses that guard, so set this to 15 to apply it: at any step where the latest CGM sample is older than N minutes, the sim makes NO dose adjustment (candidate and baseline keep delivering scheduled basal — unlike a pump outage, basal still flows during a CGM gap). 0 = disabled (legacy behavior; dose on stale data). Single missed samples (~10min) stay under 15min and are 'paved over'; 2+ missed samples cross the threshold and are treated as a gap.")
    var cgmStaleGuardMin: Double = 0
}

// Deployed system (the donor's Loop; both arms)
struct SimulateDeploymentFlags: ParsableArguments {
    @Option(name: .long, help: "Insulin model")
    var insulinType: String = "rapidActingAdult"

    @Flag(name: .long, help: "Use integral RC for baseline")
    var integralRC: Bool = false

    @Flag(name: .long, help: "Apply the deployed-LoopKit integral-correction clamp to baseline IRC (only with --integral-rc). ON = faithful to deployed Loop-main; OFF (default) = legacy unclamped IRC.")
    var integralRCClamp: Bool = false

    @Flag(name: .customLong("apply-overrides"), inversion: .prefixedNo, help: "Apply Loop Temporary Overrides to the therapy timeline over their active windows (basal ×f, ISF ÷f, CR ÷f, target ← override range; f = insulinNeedsScaleFactor). Fidelity feature — applies to BOTH arms. DEFAULT ON; pass --no-apply-overrides to ignore overrides.")
    var applyOverrides: Bool = true

    @Option(name: .customLong("loop-trio-overrides"), help: "Trio override presets as Loop Temporary Overrides, for a Loop replay of a Trio user. Same JSON as --candidate-oaps-override-presets (inline or @path); each preset's target becomes the correction range and its percentage the insulin-needs factor, over the windows of the Nightscout `Exercise` events naming it. Applies to both arms, like --apply-overrides. Not with --candidate-openaps, which reads the presets itself.")
    var loopTrioOverrides: String?

    @Flag(name: .customLong("mid-absorption-isf"), inversion: .prefixedNo,
          help: "Mid-absorption ISF: re-evaluate ALL active IOB at the CURRENT sensitivity (current LoopAlgorithm default). Pass --no-mid-absorption-isf for the OLD/deployed-Loop behavior: each dose keeps the sensitivity in effect at its delivery time for its lifetime (matters when ISF changes mid-absorption, e.g. a Temporary Override). Applies to BOTH arms.")
    var midAbsorptionIsf: Bool = true

    @Flag(name: .customLong("legacy-basal-iob"),
          help: "Deployed-Loop-main basal IOB: reproduce the delta-quantized basal-IOB \"ripple\" (pre-PR#35), which deployed Loop main still has and the LoopAlgorithm package fixed. Biggest on long basal segments (overnight temp basals/suspends). Class-1 emulation flag for Loop-main users. Applies to BOTH arms.")
    var legacyBasalIob: Bool = false

    @Option(name: .long, help: "Pump pulse size (U) for the candidate BASAL delivery in the counter. Models a real pump: delivers whole pulses, CARRIES the sub-pulse remainder while the temp rate is unchanged, drops the in-progress pulse on a temp re-issue (rate change) — reproduces the field ~1.1 U/day below rate×time. Default 0.05 (Omnipod). 0 = off (ideal continuous rate×time). Applies to BOTH arms.")
    var basalPulseQuantum: Double = 0.05

    @Flag(name: .long, help: "Use deployed Loop's adaptive carb absorption (.adaptiveRateNonlinear). Off by default. Applies to BOTH arms.")
    var adaptiveCarbAbsorption: Bool = false

    @Option(name: .long, help: "Carb-revisions overlay JSON (from reconstruct_carb_history.py): splice edited carb entries into their as-seen revision sequences so the sim sees carbs as the deployed Loop saw them at each moment. Data-level (applies to BOTH arms → identity-preserving). Default: the --data-dir export's carb_revisions.json when present (Tidepool ETL v25), else cached final grams from original entry time.")
    var carbRevisionsJson: String?

    @Option(name: .long, help: "Override-targets overlay JSON (from override_targets.py): fill named-preset override correction ranges (+multiplier) from devicestatus (omitted by the NS treatment). Data-level (both arms → identity-preserving). Use for hands-on sim of override users.")
    var overrideTargetsJson: String?

    @Option(name: .long, help: "Baseline ISF multiplier")
    var sensitivityMultiplier: Double = 1.0

    @Flag(name: .long, help: "Use asymmetric momentum on baseline")
    var asymmetricMomentum: Bool = false

    @Flag(name: .customLong("clip-in-progress-temp-basal"), inversion: .prefixedNo,
          help: """
          BASELINE arm: clip the in-progress temp basal at the decision instant (default on           = what Loop DOSES on). Pass --no-clip-in-progress-temp-basal to project it to its           commanded end instead, reproducing Loop's insulinEffectIncludingPendingInsulin — the           variant Loop RECORDS as dosingDecision.predictedGlucose / the uploaded bgForecast.           Use this when comparing forecasts against recorded field data; leave it on when           comparing doses.
          """)
    var clipInProgressTempBasal: Bool = true

    @Flag(name: .long, help: "Disable the gradual-transitions gate (>40 mg/dL jump suppresses momentum AND RC) in BOTH arms. The gate is a LoopAlgorithm (class-2) addition NOT in deployed Loop-main (class-1) — pass this to reproduce class-1. Applies to baseline + candidate so identity is preserved.")
    var noGradualTransitionsGate: Bool = false

    @Flag(name: .long, help: "Emulate Loop-main: use the pre-#33 step-by-step RC decayEffect (a small discontinuity at delta boundaries for unaligned CGM) instead of the LoopAlgorithm continuous-quadratic reformulation (LoopKit#556). Pass for donors whose deployed Loop predates that change. Applies to both arms.")
    var legacyRcDecay: Bool = false

    @Flag(name: .long, help: "Replay with Loop's TEMP-BASAL dosing strategy (AutomaticDosingStrategy.tempBasal): every correction is a 30-min temp basal, never an automatic bolus. Deployment-faithful for donors whose loop cycles record recommendations only in recommendedBasal (a temp-only deployment records ZERO recommendedBolus over months). Applies to both arms.")
    var tempBasalStrategy: Bool = false

    @Option(name: .long, help: "Carb absorption-time overrun (stock Loop = 1.5). The remaining-carb min-rate window is entered x overrun; some custom builds differ (bddp04's field slope matches 2.0). Applies to both arms.")
    var carbAbsorptionOverrun: Double = 1.5

    @Flag(name: .long, help: "Model deployed timeBasedDoseApplicationFactor (sub-5-min loops after a completed loop dose proportionally less). OFF by default: the deployed reference is the previous loop's COMPLETION instant, which exports don't record; the decision-time approximation measurably hurt cohort match.")
    var timeBasedAf: Bool = false

    @Option(name: .long, help: "Path to an outage CSV (start,end,reason,source,notes) describing windows where the physical pump could not deliver insulin (pod failure, occlusion, manual disconnect). During each outage the sim clamps both candidate and baseline absolute delivery to 0 so counter_BG isn't contaminated by phantom basal. Generate with `analysis/case-study` tooling: `python -m loopeval_analysis.outage from-nightscout ...`")
    var outagesCsv: String?

    @Option(name: .long, help: "Auto-bolus application factor for BOTH arms (baseline + candidate inherit unless --candidate-application-factor is set) — fraction of recommended correction applied per cycle. Property of the real Loop deployment. Loop default 0.4 (the auto-bolus is floored to the pump increment AFTER this, matching real devicestatus).")
    var applicationFactor: Double = 0.4

    @Option(name: .long, help: "Comma-separated outage REASONS (from the outages/disruptions CSV) during which the pump keeps delivering SCHEDULED basal instead of nothing — e.g. 'loop_offline' (phone away: the pod runs its schedule, only new adjustments stop). Default: none (every outage clamps delivery to 0).")
    var outageBasalReasons: String?

    @Option(name: .long, help: "CONTROLLER-side INSULIN MODEL — what the ALGORITHM believes insulin does, overriding the therapy timeline for BOTH arms. RA (rapid-acting): rapidActingAdult peak 75min, rapidActingChild peak 65min. URA (ultra-rapid): fiasp, lyumjev -- peak 55min, and IDENTICAL to each other in this preset set (same peak/DIA/delay), so picking one over the other is a no-op. Also afrezza (inhaled, peak 29min), lateShort90dia4 (experimental, peak 90min/DIA 4h) and custom (see --custom-insulin-duration-min). All RA/URA presets share DIA 6h -- the class difference is PEAK TIME, not duration. Works on every data source, unlike --insulin-type, which only reaches the Nightscout path and is silently ignored with --data-dir. Pair with --patient-insulin-model to vary the body and the belief independently. Measured on one donor, the belief dominates: RA->URA belief traded about +3 TIR for +0.3-0.4 t<54 in either body, while the body's model barely moved outcomes.")
    var controllerInsulinModel: String?

    @Option(name: .long, help: "Action duration (MINUTES) of the `custom` insulin model, for a Loop build shipped with a modified insulin curve. Required with `--controller-insulin-model custom` or `--patient-insulin-model custom`; both sides share one custom curve. Detect it from the recorded forecasts: deployed Loop's bgForecast runs about this long plus the 10-min delay (stock models: ~370-390 min), and the recorded insulinOnBoard decays on this curve. Must exceed twice the peak.")
    var customInsulinDurationMin: Double?

    @Option(name: .long, help: "Peak activity time (MINUTES) of the `custom` insulin model. Required with a `custom` insulin model; see --custom-insulin-duration-min.")
    var customInsulinPeakMin: Double?

    @Option(name: .long, help: "A DATED change of the controller's insulin curve, for a user who rebuilt Loop with a different curve mid-window: `ISO8601=SPEC`, where SPEC is a preset name (e.g. rapidActingAdult) or a custom curve `DURATION/PEAK` in minutes (e.g. 2026-09-24T09:03:00Z=180/80). Repeatable. Before the first change the controller uses --controller-insulin-model (else the therapy timeline). From the change on, every decision evaluates its WHOLE dose history on the new curve, as Loop does (it maps insulin type to curve when it computes, not when it delivers). At most two distinct custom curves per run, counting --custom-insulin-*. The plant keeps its own model: --patient-insulin-model, else the curve in force before the first change.")
    var controllerInsulinSwitch: [String] = []

    @Option(name: .long, help: "Sensor cap on glucose reported to the controller (mg/dL). Real CGMs (Dexcom G6/G7, Libre) peg at ~400 — the algorithm never sees BG above this. Counter trajectory + outcome scoring use uncapped values. Default 400 (Dexcom-realistic). Pass 0 to disable.")
    var sensorCapMgdl: Double = 400.0
}

// Candidate: controller and settings
struct SimulateCandidateFlags: ParsableArguments {
    // Candidate-side flags (subset of bench's; can extend as needed)
    @Flag(name: .long, help: "Use integral RC for candidate")
    var candidateIntegralRC: Bool = false

    @Flag(name: .long, help: "Apply the deployed-LoopKit integral-correction clamp to candidate IRC (only with integral RC). ON = faithful to deployed Loop-main; OFF (default) = legacy unclamped IRC.")
    var candidateIntegralRCClamp: Bool = false

    @Option(name: .long, help: "Candidate ISF multiplier")
    var candidateSensitivityMultiplier: Double?

    @Option(name: .long, help: "Candidate basal-rate multiplier: scale the candidate's scheduled basal profile (0.8 = 80% basal). Changes the belief (delivered basal AND the forecast's net-basal reference), not just the output. Baseline arm keeps 1.0. Default 1.0.")
    var candidateBasalRateMultiplier: Double = 1.0

    @Option(name: .long, help: "Candidate 'overall insulin needs' scale factor f (Loop preset-style): ONE knob scaling basal ×f, ISF ÷f, CR ÷f together. f=0.5 → half basal, double ISF, double CR (less insulin overall); f=1.2 → 20% more insulin. Composes multiplicatively with the individual --candidate-{sensitivity,basal-rate}-multiplier flags. Unset = no scaling. This is the realistic single-dial aggressiveness axis (matches an insulin-needs Temporary Override) — sweep it for the reference frontier.")
    var candidateInsulinNeeds: Double?

    @Flag(name: .customLong("candidate-clip-in-progress-temp-basal"), inversion: .prefixedNo, help: "Candidate: treat a temp basal still running at the decision instant as ENDED at t (only the elapsed portion counts; scheduled resumes after). DEFAULT ON — this matches deployed Loop-main, which trims non-bolus doses to basalDosingEnd=now() before forecasting. Pass --no-candidate-clip-in-progress-temp-basal to project it forward (reproduces the UNTRUNCATED recorded dosingDecision.bgForecast, not Loop's dosing forecast). Honored for per-dose tempRate sources too (fixed 2026-08-16).")
    var candidateClipInProgressTempBasal: Bool = true

    @Option(name: .long, help: "Per-hour candidate ISF multipliers (24 csv)")
    var candidateIsfHourly: String?

    @Option(name: .long, help: "Per-local-hour INSULIN-NEEDS multipliers for the candidate (24 csv, or @file): basal × h, ISF ÷ h, CR ÷ h per hour — the hourly form of --candidate-insulin-needs (a learned circadian needs schedule). Hours are interpreted in --local-timezone. Composes with --candidate-insulin-needs and --candidate-isf-hourly.")
    var candidateNeedsHourly: String?

    @Option(name: .long, help: "A therapy.json whose basal/ISF/CR/target schedules (and their raw, un-override forms) the CANDIDATE controller runs instead of the field's: a settings edit replayed in a window that ran the other settings. The candidate's pump runs this basal wherever it falls back to scheduled basal. Limits, overrides and insulin model stay the field's; the patient is unchanged. Composes with the candidate multipliers.")
    var candidateSchedulesJson: String?

    @Option(name: .long, help: "Candidate correction-range target MIDPOINT (mg/dL) override. With --candidate-target-width, replaces the profile correction range for the candidate's dose decision. Lets us sweep target independent of ISF.")
    var candidateTargetMid: Double?

    @Option(name: .long, help: "Candidate correction-range WIDTH (mg/dL) override. Range = [mid-width/2, mid+width/2]. Width 0 = single-value target. Requires --candidate-target-mid.")
    var candidateTargetWidth: Double?

    @Flag(name: .long, help: "Enable glucose-based application factor (GBAF) for candidate — auto-bolus app-factor ramps from factorLow (at/below lowAnchor) to factorHigh (at/above highAnchor) with current BG. More aggressive only when BG is high.")
    var candidateGbaf: Bool = false

    @Option(name: .long, help: "GBAF: BG at/below which factor=factorLow (default 140)")
    var candidateGbafLowAnchor: Double = 140.0

    @Option(name: .long, help: "GBAF: BG at/above which factor=factorHigh (default 220)")
    var candidateGbafHighAnchor: Double = 220.0

    @Option(name: .long, help: "GBAF: applicationFactor at lowAnchor (default 0.4)")
    var candidateGbafFactorLow: Double = 0.4

    @Option(name: .long, help: "GBAF: applicationFactor at highAnchor (default 0.7)")
    var candidateGbafFactorHigh: Double = 0.7

    @Flag(name: .long, help: "Forecast-keyed GBAF: key the application-factor ramp on max(currentBG, eventualBG) instead of currentBG, so Loop acts on a rising/high forecast even when current BG is low-normal — gated on the predicted minimum >= --candidate-gbaf-forecast-min-guard.")
    var candidateGbafForecastKeyed: Bool = false

    @Option(name: .long, help: "Predicted-minimum guard (mg/dL) for forecast-keyed GBAF: only key on the forecast when the predicted minimum stays >= this (don't dose into a predicted dip). Default 85.")
    var candidateGbafForecastMinGuard: Double = 85.0

    @Option(name: .long, help: "Candidate flat (global) auto-bolus application factor — overrides --application-factor for the candidate arm only. Negative = inherit --application-factor. Only used when GBAF is off.")
    var candidateApplicationFactor: Double = -1

    @Option(name: .long, help: "Pump bolus increment (U): round the auto-bolus to this grid (real Loop delivers on the pump's increment, e.g. Omnipod 0.05U, and drops sub-increment doses). 0 = no rounding (legacy continuous micro-dosing). Default 0.05.")
    var candidateBolusIncrement: Double = 0.05

    @Option(name: .long, help: "Pump temp-basal-rate increment (U/hr): round temp basal to this grid. 0 = none. Default 0.05.")
    var candidateTempBasalIncrement: Double = 0.05

    @Option(name: .long, help: "Diagnostic: cap every candidate carb entry's absorptionTime to at most this many MINUTES (0 = no cap). Shorter time raises the modeled carb-absorption-rate ceiling, absorbing fast rises into carbs instead of RC.")
    var candidateCarbAbsorptionCapMin: Double = 0

    @Flag(name: .long, help: "Candidate engine = OpenAPS (oref0-Swift) instead of Loop. Baseline always stays Loop. Lets you compare 'how would OpenAPS dose on this data?' against Loop's behavior on the same trace. Most Loop-specific candidate flags (asym momentum, IRC, ISF boost, etc.) are ignored on the OpenAPS leg.")
    var candidateOpenaps: Bool = false

    @Flag(name: .long, help: "DIAGNOSTIC: candidate engine = Loop's recommendation re-routed through the OpenAPSAdapter dose-translation path. If the resulting counter trace matches a plain Loop CF run, the OpenAPS translation is sound and any Loop-vs-OpenAPS divergence is genuine algorithm differences, not framework artifacts.")
    var candidateLoopMimicOaps: Bool = false
}

// Person: manual boluses and carbs
struct SimulatePersonFlags: ParsableArguments {
    @Flag(name: .long, help: "No user boluses: do NOT pass through user-initiated manual boluses (post burn-in). The sim's Loop owns ALL dosing, covering meals only via its own COB-driven auto-bolusing. Tests how the fully-automated system performs with no user intervention.")
    var noUserBoluses: Bool = false

    @Flag(name: .long, help: "Unannounced meals: hide carb entries from BOTH baseline and candidate forecasts (no COB), so Loop can only react to the BG rise. The meal's BG-raising effect REMAINS in the ICE/counter (it's the real trace, not subtracted), so the meal still happens — Loop just doesn't know about it. Use with --no-user-boluses for a true fully-unannounced, fully-automated test.")
    var noCarbEntries: Bool = false

    @Flag(name: .long, inversion: .prefixedNo, help: "IOB-aware manual-bolus passthrough (DEFAULT ON — a simulation-veracity correction, not an algorithm change). Resize each real user bolus by the IOB difference between the counterfactual and reality: a real bolus of x U delivered at real IOB y becomes x-(z-y) (clamped to [0,maxBolus]) where z is the candidate's IOB at that moment — if the candidate already carries more IOB, the user would have bolused less (Loop's calc subtracts IOB), and vice versa. Pass --no-candidate-iob-adjust-manual-boluses to disable (verbatim passthrough, the old behavior).")
    var candidateIobAdjustManualBoluses: Bool = true

    @Flag(name: .long, inversion: .prefixedNo, help: "Manual-bolus mode (DEFAULT ON): REPLACE each real user manual bolus with the candidate algorithm's OWN recommended manual bolus at that step (full correction vs the candidate's forecast/IOB/COB, clamped to maxBolus). Self-consistent with the candidate state, so it avoids the IOB-divergence amplification of the IOB-aware x-(z-y) resize, and makes the reference/insulin-needs sweep behave physically (lows fall monotonically). Takes precedence over --candidate-iob-adjust-manual-boluses. Pass --no-candidate-manual-bolus-from-recommendation for the old IOB-resize passthrough (more field-faithful for single-decision fidelity work).")
    var candidateManualBolusFromRecommendation: Bool = true

    @Option(name: .long, help: "Scale applied to the recommended manual bolus in --candidate-manual-bolus-from-recommendation mode (1.0 = full algo dose, 0.5 = half). Models deliberate meal under-bolusing. No effect unless that mode is on.")
    var candidateManualBolusRecScale: Double = 1.0
}

// Body: ICE replay and patient
struct SimulateBodyFlags: ParsableArguments {
    @Option(name: .long, help: "Counter-regulation onset (mg/dL). When the counterfactual BG falls below this, model the body's defensive hepatic glucose output as a positive BG velocity that ramps with depth below onset (capped). Prevents the counter running to unphysical negatives. 0 = off (default). ~65 is a reasonable physiological onset.")
    var counterRegOnset: Double = 0

    @Option(name: .long, help: "Counter-regulation gain (mg/dL/min per mg/dL below onset). Default 0.2.")
    var counterRegGain: Double = 0.2

    @Option(name: .long, help: "Counter-regulation max rate (mg/dL/min), the saturating defense ceiling. Default 6.0.")
    var counterRegMax: Double = 6.0

    @Flag(name: .customLong("counter-reg-absolute"), help: "Research: apply the counter-regulation rate in full whenever the counterfactual is below onset, instead of its difference from the field's. Only for a substrate whose field low responses (rescue carbs and physiological rebound) were subtracted (--low-response-subtract-csv).")
    var counterRegAbsolute: Bool = false

    @Option(name: .customLong("counter-reg-tau-min"), help: "Research: first-order lag (min) on the absolute counter-regulation rate; 0 = instantaneous. With --counter-reg-absolute.")
    var counterRegTauMin: Double = 0

    @Option(name: .customLong("glucose-effectiveness"), help: "Research: glucose effectiveness SG (1/min). The counterfactual relaxes toward the field trace at -SG·(counter − field) per minute, the body's own pull the frozen trace carries only at the field's glucose. Zero at identity. 0 = off.")
    var glucoseEffectiveness: Double = 0

    @Option(name: .customLong("low-response-model"), help: "JSON LowResponseModel (research): re-generate low-driven upward effects — rescue carbs and the physiological rebound — only where the COUNTERFACTUAL goes low, by a seeded hazard on its own CGM / trend / IOB / local night (LowResponse.swift). Meant for a substrate whose field low responses were subtracted beforehand; turn the counter-regulation term off with it (--counter-reg-onset 0). Requires --candidate-counterfactual.")
    var lowResponseModel: String? = nil

    @Option(name: .customLong("high-response-model"), help: "JSON LowResponseModel with mirror: true (research): the high-side defense (walks, unlogged corrections) in the expected-value difference form — h(counterfactual) minus h(field), subtracted. Requires --candidate-counterfactual.")
    var highResponseModel: String? = nil

    @Option(name: .customLong("low-response-subtract-csv"), help: "CSV (t ISO8601, delta mg/dL) of the FIELD's low-response effect per CGM sample (change since the previous sample), removed from the field's glucose change in the counterfactual advance — an ICE adjustment, never an absolute-CGM edit. Pair with --low-response-model. Requires --candidate-counterfactual.")
    var lowResponseSubtractCsv: String? = nil

    @Option(name: .long, help: "CGM-gap re-anchor threshold (minutes). Across a CGM gap longer than this the counterfactual has no ground truth and the single big-step physiological advance is unreliable (manual boluses given during the gap are on the field side but not the candidate history ⇒ runaway asymmetry that blew the counter to 700+). Re-anchor the counter to the real CGM at gap-end. Identity-safe. Default 30. 0 disables (legacy).")
    var cfGapReanchorMin: Double = 30

    @Option(name: .long, help: "PATIENT-side ISF as an ABSOLUTE FLAT value (mg/dL/U), referencing NO therapy configuration — not the donor's schedule shape, not its time-of-day variation, not its dated settings eras. The simulated body becomes an independent object from the settings the controller runs, which still uses the real configured schedule. Unset = the plant is COUPLED to the controller's ISF belief (the historical behavior, so existing sweeps are unchanged). Set it when the patient's insulin sensitivity must be a free parameter — e.g. sweeping it to ask how much a result depends on the assumed patient.")
    var patientIsf: Double?

    @Option(name: .long, help: "PATIENT-side INSULIN MODEL — the pharmacodynamics of the simulated BODY. RA (rapid-acting): rapidActingAdult peak 75min, rapidActingChild peak 65min. URA (ultra-rapid): fiasp, lyumjev -- peak 55min, and IDENTICAL to each other in this preset set (same peak/DIA/delay), so picking one over the other is a no-op. Also afrezza (inhaled, peak 29min) and lateShort90dia4 (experimental, peak 90min/DIA 4h). All RA/URA presets share DIA 6h -- the class difference is PEAK TIME, not duration. The controller keeps believing its own model, so this decouples 'how fast insulin really acts' from 'how fast the algorithm thinks it acts'. Unset = the body uses the controller's model too (coupled; the historical behavior). Identity-safe: the same curve removes the field's doses and adds the candidate's, so an unchanged candidate still reproduces the recording exactly.")
    var patientInsulinModel: String?

        @Flag(name: .long, help: "Sim-FIDELITY: infer a local insulin-sensitivity multiplier m(t) from the residual. When BG is still dropping after subtracting the PD-modeled (scheduled-ISF) insulin, the insulin was more effective than scheduled, so scale ISF UP just enough to zero that negative residual (never past it). Applied to the PHYSIOLOGY (ICE + counterfactual dose-effect run at scheduled ISF × m), DECOUPLED from the controller's ISF belief. Capped by --candidate-infer-sensitivity-max. Default OFF.")
    var candidateInferSensitivity: Bool = false

    @Option(name: .long, help: "Cap on the inferred sensitivity multiplier m ('can't subtract more insulin than is physically present'). Default 2.0. Set 1.0 for an identity check (≡ off when sensitivity-multiplier is 1).")
    var candidateInferSensitivityMax: Double = 2.0

    @Option(name: .long, help: "Trailing window (min) over which the residual/insulin velocities are measured to infer m(t). Default 30.")
    var candidateInferSensitivityWindowMin: Double = 30.0

    @Option(name: .long, help: "Smooth m(t) over this timescale (min, Gaussian FWHM, carry-latent: m≈1 steps treated as missing). Models sensitivity as a slow latent state instead of a per-step spike. 0 = off (default). Try 90.")
    var candidateInferSensitivitySmoothMin: Double = 0.0

    @Option(name: .long, help: "Shrinkage prior weight (equivalent observations at m=1) for the smoother. Pulls the smoothed m back toward 1 where identified drops are sparse, countering carry-latent over-attribution. 0 = pure carry-latent (default). Try 1–6.")
    var candidateInferSensitivitySmoothPrior: Double = 0.0

    @Option(name: .long, help: "Dump per-step NIE (de-insulinized real BG change = realBGdelta − m·real_physical_insulin) + m + substrate BG to this CSV (requires --candidate-infer-sensitivity). Feeds the offline perfect-foresight dosing oracle.")
    var candidateDumpNieCsv: String? = nil

    @Option(name: .long, help: "DEPRECATED — use --patient-insulin-model. This only sizes the effect LOOKBACK WINDOW; it does NOT reshape the plant's insulin curve, because Loop's glucoseEffects reads each dose's own stamped insulinType rather than a model passed alongside. Measured: peak 75→150 and DIA 6→9 move the counterfactual by 0.0001 mg/dL. Kept so existing invocations still parse.")
    var insulinPhysicalPeak: Double?

    @Option(name: .long, help: "DEPRECATED — see --insulin-physical-peak. Window sizing only; use --patient-insulin-model to change the body's insulin curve.")
    var insulinPhysicalDia: Double?
}

// Body: external plant
struct SimulatePlantFlags: ParsableArguments {
    @Option(name: .customLong("external-plant"), help: "Shell command for an external patient model (sim-of-the-sim). Requires --candidate-counterfactual. The candidate's glucose advance — normally the ICE replay — is replaced by the plant: each cycle's delivered candidate doses are sent to the command's stdin as a JSON line and its CGM at the next sample time(s) is read back from stdout (protocol in ExternalPlant.swift). Decisions, enactment and timing are the unchanged simulator, so a plant-coupled run differs from an ordinary one ONLY in the physiology.")
    var externalPlant: String? = nil

    @Flag(name: .customLong("plant-behavior"), help: "With --external-plant (protocol v2): the plant's person makes the carb entries and manual boluses. From the end of burn-in the candidate ignores the REAL carb entries and manual boluses; carbs the plant returns enter the candidate's carb store (visible from the next decision) and each bolus it returns is delivered at the next decision as ratio x the bolus-calculator recommendation there (or as absolute units), and the automatic dose at that decision is decided with the bolus already in the dose history. Temporary Overrides it returns join the candidate's override windows, applied from their start like exported ones. The baseline arm is unchanged. Spec: docs/ice/plant-protocol-v2.md; overrides in ExternalPlant.swift.")
    var plantBehavior: Bool = false
}

// Candidate Loop experiments
struct SimulateLoopExperimentFlags: ParsableArguments {
    @Flag(name: .long, help: "Use asymmetric momentum for candidate")
    var candidateAsymmetricMomentum: Bool = false

    @Option(name: .long, help: "Candidate asymmetric-momentum alpha-slow (default 0.15)")
    var candidateMomentumAlphaSlow: Double = 0.15

    @Option(name: .long, help: "Candidate asymmetric-momentum alpha-fast (default 0.85)")
    var candidateMomentumAlphaFast: Double = 0.85

    @Flag(name: .long, help: "C33: gate the sigma band on the DESCENT state (BG reached --candidate-descent-high-bg-min within --candidate-descent-window-min AND trailing 60-min slope <= --candidate-descent-slope-max) instead of on sigma's own level. Combine with --candidate-sigma-band-fixed-sigma to make the displacement a pure function of state.")
    var candidateSigmaBandDescentGate: Bool = false

    @Option(name: .long, help: "C32 descent rise-cut: scale the POSITIVE RC discrepancy by this when BG reached --candidate-descent-high-bg-min within --candidate-descent-window-min AND the trailing 60-min slope is <= --candidate-descent-slope-max. Targets the descent off a corrected high, which carries 35% of severe lows. 1.0 = off (default).")
    var candidateDescentRcRiseScale: Double = 1.0

    @Option(name: .long, help: "C32: BG level that counts as the preceding high (mg/dL). Default 180.")
    var candidateDescentHighBgMin: Double = 180

    @Option(name: .long, help: "C32: how far back to look for that high (minutes). Default 120.")
    var candidateDescentWindowMin: Double = 120

    @Option(name: .long, help: "C32: trailing 60-min slope (mg/dL/min) at or below which the gate opens. Default -1.0.")
    var candidateDescentSlopeMax: Double = -1.0

    @Option(name: .long, help: "Positive momentum velocity cap (mg/dL/min). LoopAlgorithm default is 4 mg/dL/min, which limits rising-BG momentum extrapolation. Real-deployed Loop in this user's case had NO cap; pass a high value (e.g., 100) to effectively disable.")
    var candidateMomentumCap: Double?

    @Option(name: .long, help: "Per-step ISF multiplier CSV: (time, isf_multiplier) pairs. At each sim step, scales ISF by the value from the CSV nearest to step time (default 1.0 = no change). Use values >1 to make Loop see ISF as higher (less BG drop per U → recommends less dose, DAMP direction). Use <1 to make Loop see ISF as lower (more dose, BOOST direction). Steps with no matching CSV row are unchanged.")
    var candidateIsfCsv: String?

    @Option(name: .long, help: "Per-step FORECAST OFFSET CSV: (time, offset_mgdl) pairs. At each sim step the candidate ADDS the matching offset (mg/dL) to Loop's predicted-glucose trajectory, so Loop pre-doses for anticipated (unannounced) carb pressure. The meal-anticipation predictor produces this; values should be pre-scaled conservatively. Steps with no matching row get 0. Forecast-side modifier (AGENTS.md §2).")
    var candidateForecastOffsetCsv: String?

    @Option(name: .long, help: "Time-matching tolerance for --candidate-isf-csv (seconds, default 150 = ±2.5min)")
    var candidateIsfCsvToleranceSec: Double = 150.0

    @Option(name: .long, help: "Lows-protection gate for the ISF BOOST (mult<1 from --candidate-isf-csv). At each step, a boost is applied ONLY if the candidate's UNBOOSTED forecast PEAK (highest BG expected over the horizon = real headroom) exceeds this mg/dL threshold. Fires when BG is high or climbing (incl. unannounced-meal rises); suppresses the comfortable-and-falling case so the boost can't float into a developing low. The DAMP direction (mult>=1) is always kept. Unset = no gate.")
    var candidateIsfBoostGateEventual: Double?

    @Option(name: .long, help: "Intraday ICE veto on the ISF BOOST (mult<1). Suppress the boost when the recent (last 30min) insulin-counteraction-effect RATE is below this magnitude (mg/dL/min) — i.e. non-insulin drivers are currently pulling BG down (a sensitive moment, ICE<0 ⟺ high local-ISF), so adding insulin would float into a developing drop. Takes precedence over the forecast gate. DAMP (mult>=1) always kept. e.g. 0.5 = veto boost when ICE rate < -0.5 mg/dL/min.")
    var candidateIsfBoostVetoIce: Double?

    @Flag(name: .long, help: "Apply candidate ISF boost (multiplier and/or per-step CSV) ONLY to the active-insulin term: dose-recommendation sizing and the positive-net-units glucose-effect. The EGP-credit term (negative netBasalUnits — implicit endogenous glucose production from suspending below schedule) continues to use the unmodulated scheduled ISF via Phase-1's scheduleBaselineSensitivity parameter. Default OFF preserves the legacy conflated behavior so pre-Phase-1 results stay reproducible.")
    var candidateIsfBoostActiveOnly: Bool = false

    @Option(name: .long, help: "Asymmetric IRC: gain scale on the retrospective correction when BG is dropping faster than predicted (negative discrepancy = sensitivity). >1 responds more strongly/faster to drops (lows-protective). Only used with --candidate-integral-rc. Default 1.0 (symmetric).")
    var candidateIrcDropScale: Double = 1.0

    @Option(name: .long, help: "Asymmetric IRC: gain scale when BG is rising faster than predicted (positive discrepancy = resistance). <1 responds more weakly/slower to rises. Only used with --candidate-integral-rc. Default 1.0 (symmetric).")
    var candidateIrcRiseScale: Double = 1.0

    @Flag(name: .long, help: "Asymmetric STANDARD RC (candidate): apply --candidate-irc-drop-scale / --candidate-irc-rise-scale to the standard (non-integral) retrospective correction — the deployed RC mode on most Loop users. Scales the single 30-min discrepancy before it is projected 60 min forward. Off = deployed symmetric RC.")
    var candidateAsymmetricStdRc: Bool = false

    @Option(name: .long, help: "IRC low-memory carry ('remember the low'): when >0 and the current discrepancy run is positive (a rebound), the integral carries the immediately-preceding negative (low) run across the sign flip instead of resetting, scaled by this factor, so the low's memory offsets the rebound's upward dosing. One-sided (only +run carries a preceding -run). Only used with --candidate-integral-rc. Default 0 (off).")
    var candidateIrcLowMemoryScale: Double = 0.0

    @Option(name: .long, help: "Asymmetric IRC persistence ('remember the low longer'): scales how long a NEGATIVE-discrepancy (sensitivity) correction lingers in the forecast. >1 = turns off slowly / persists. Only used with --candidate-integral-rc. Default 1.0.")
    var candidateIrcDropDurationScale: Double = 1.0

    @Option(name: .long, help: "Asymmetric IRC persistence: scales how long a POSITIVE-discrepancy (resistance) correction lingers. <1 = turns off fast. Only used with --candidate-integral-rc. Default 1.0.")
    var candidateIrcRiseDurationScale: Double = 1.0

    @Option(name: .long, help: "RC 'how far back': retrospection integration window (MINUTES) over which discrepancies are gathered/summed. Default: deployed 180. Applies to standard and integral RC.")
    var candidateRcRetrospectionMin: Double?

    @Option(name: .long, help: "RC 'how far forward': correction-effect duration / persistence (MINUTES). Sets the base effect duration and (for IRC) the persistence cap. Default: deployed (60 base / 180 cap).")
    var candidateRcEffectDurationMin: Double?

    @Option(name: .long, help: "Candidate momentum projection duration (MINUTES): how far forward CGM momentum is extrapolated. Default 15.")
    var candidateMomentumProjectionMin: Double = 15

    @Option(name: .long, help: "Candidate momentum lookback (MINUTES): the glucose window the momentum slope is fit over ('how far back' momentum looks). Default 15.")
    var candidateMomentumLookbackMin: Double = 15

    @Option(name: .long, help: "Cross-cycle sensitive-mode time constant (MINUTES): an EWMA of recent NEGATIVE discrepancies decays at this tau and raises effective ISF on future cycles to prevent a delayed SECOND low. 0 = off. Try 60-360.")
    var candidateSensitiveModeTauMin: Double = 0

    @Option(name: .long, help: "SLOW (autosens-scope) RC time constant, minutes: EWMA of the SIGNED per-step forecast residual (the quantity RC integrates over 3 h) over hours to a day. 0 = off. Try 360 (6 h) or 1440 (24 h).")
    var candidateSlowRcTauMin: Double = 0

    @Option(name: .long, help: "Slow RC gain: controller ISF multiplier = clamp(1 - gain * level, min, max), level in mg/dL per 5-min step. Sustained +1 mg/dL/step (BG above forecast = resistance) at gain 0.1 -> ISF x0.9. Try 0.1-0.2.")
    var candidateSlowRcGain: Double = 0

    @Option(name: .long, help: "Slow RC ISF-multiplier floor (default 0.7, oref autosens_min).")
    var candidateSlowRcMin: Double = 0.7

    @Option(name: .long, help: "Slow RC ISF-multiplier ceiling (default 1.3; oref autosens_max is 1.2).")
    var candidateSlowRcMax: Double = 1.3

    @Option(name: .long, help: "Slow RC form: ewma (default; multiplier = clamp(1 - gain*level)) or integral (log multiplier steps by -gain*residual every cycle until the residual averages zero, so it does not settle short of the shift; gain is per mg/dL per 5-min step, try 0.0005-0.002).")
    var candidateSlowRcMode: String = "ewma"

    @Option(name: .long, help: "Slow RC: clip each step's residual to +/- this many mg/dL before it enters the level, so meal and rescue excursions count as at most this (0 = off). Try 2-3.")
    var candidateSlowRcClipMgdl: Double = 0

    @Option(name: .long, help: "Slow RC integral form: leak the log multiplier back toward 1 with this time constant, minutes (0 = no leak). A long leak (e.g. 10080 = 7 d) keeps it to day-scale shifts and leaves the person's level to settings.")
    var candidateSlowRcLeakMin: Double = 0

    @Option(name: .long, help: "Slow RC: freeze the level for this many minutes after glucose was below 70, so rescue carbs are not read as resistance (0 = off). Try 720 (C20's window).")
    var candidateSlowRcPostlowFreezeMin: Double = 0

    @Option(name: .long, help: "Slow RC timing gate: JSON {\"windows\": [{\"start\", \"end\", \"min\"}], \"resets\": [ISO dates]}. Inside a window the multiplier's lower clamp is that window's min, outside it --candidate-slow-rc-min; at each reset the level returns to 0 (a user switching the adjustment off).")
    var candidateSlowRcGateJson: String?

    @Flag(name: .long, help: "Slow RC needs form: the multiplier scales basal and carb ratio as well as ISF, like an insulin-needs override (basal x 1/m, ISF x m, CR x m).")
    var candidateSlowRcNeeds = false

    @Option(name: .long, help: "Slow RC: at the onset of each low (glucose below 70 after at least 30 min above), multiply the level by this factor, so a multiplier pushed toward more insulin backs off when lows start (1 = off, 0 = reset to no adjustment).")
    var candidateSlowRcLowShrink: Double = 1

    @Option(name: .long, help: "Cross-cycle sensitive-mode gain k: effective ISF is scaled by (1 + k*R) where R is the EWMA of recent negative discrepancy (mg/dL). 0 = off. Try 0.01-0.05.")
    var candidateSensitiveModeGain: Double = 0

    @Option(name: .long, help: "ICE RISE-BOOST gain: attack a SUSTAINED, actively-driven high. Adds a POSITIVE forecast offset = gain * gate(BG) * max(0, trailingICErate - thresh) so Loop doses harder when BG is high AND trailing ICE is positive (real persistent high, not a resolving spike). The rise side of the unified ICE-response term. 0 = off. Try 20-80.")
    var candidateIceRiseBoostGain: Double = 0

    @Option(name: .long, help: "ICE rise-boost BG gate low (mg/dL): offset ramps from 0 at this BG. Default 170.")
    var candidateIceRiseBoostBgLo: Double = 170

    @Option(name: .long, help: "ICE rise-boost BG gate high (mg/dL): offset gate saturates at 1.0 at/above this BG. Default 250.")
    var candidateIceRiseBoostBgHi: Double = 250

    @Option(name: .long, help: "ICE rise-boost trailing window (MINUTES) for the mean-ICE-rate (persistence). Default 45.")
    var candidateIceRiseBoostTauMin: Double = 45

    @Option(name: .long, help: "ICE rise-boost threshold (mg/dL per min): trailing ICE rate must exceed this to fire. Default 0.")
    var candidateIceRiseBoostThresh: Double = 0

    @Option(name: .long, help: "ICE rise-boost lows-coupling: suppress the high-attack when recently sensitive (sensMode level R high). offset *= max(0, 1 - k*R). 0 = uncoupled. Try 0.05-0.3.")
    var candidateIceRiseBoostSensSuppress: Double = 0

    @Option(name: .long, help: "ICE rise-boost ISF-fade LOW: boost is full at ISF multiplier <= this (aggressive). Default 0 (off).")
    var candidateIceRiseBoostIsfFadeLo: Double = 0

    @Option(name: .long, help: "ICE rise-boost ISF-fade HIGH: boost fades to 0 at ISF multiplier >= this (conservative); config collapses to smairc. isfFadeHi<=Lo = off.")
    var candidateIceRiseBoostIsfFadeHi: Double = 0

    @Flag(name: .long, help: "Soft low-gate: replace Loop's hard 'predicted-min < range-floor -> zero auto-bolus' cliff with a graded ramp from the suspend threshold up to the range floor (bolus scaled by how far the predicted minimum sits between them). GBAF's low-BG factor still applies on top.")
    var candidateSoftLowGate: Bool = false

    @Option(name: .long, help: "Predicted-min gate threshold (mg/dL): the predicted-minimum BG below which the auto-bolus is gated off. Default (unset) = the correction-range floor (standard Loop). Set lower (e.g. 80) to KEEP the full application factor for predicted minimums down to that value before gating — 'continue the application factor down to <value>'. A small step toward the uncertainty cap (which disables the gate entirely). Composes with --candidate-soft-low-gate (ramp below the threshold) and is overridden by --candidate-uncertainty-cap.")
    var candidateLowGateThreshold: Double?

    @Option(name: .long, help: "UAM projection (minutes): treat recent unexplained glucose appearance (ICE minus modeled carbs, last 30 min) as ongoing absorption, projected forward with a linear taper over this many minutes. Continuous unannounced-meal forecast term; raises eventualBG early on genuine carb rises so the existing dosing logic acts sooner. 0 = off.")
    var candidateUamMinutes: Double = 0

    @Option(name: .long, help: "Early-ascending-limb projection (minutes): the continuous complement of GBAF. When BG is in the low-normal band AND rising, project the current rise forward as a tapering, meal-shaped forecast bump over this many minutes, so the existing dosing logic covers an unannounced meal on its ascending limb instead of at the peak. Off at high BG (never piles onto the peak) and off when flat/falling. Needs --candidate-early-rise-gain > 0. 0 = off.")
    var candidateEarlyRiseMinutes: Double = 0

    @Option(name: .long, help: "Early-rise gain: dimensionless multiplier on the projected rise rate (mg/dL per min of forecast appearance = gain x bandGate x max(0, slope - threshold)). 0 = off. Try ~0.5-2.0.")
    var candidateEarlyRiseGain: Double = 0

    @Option(name: .long, help: "Early-rise BG band lower edge (mg/dL): the gate ramps 0->1 over [low, low+15]; term is off below this (never push the forecast up near a low). Default 70.")
    var candidateEarlyRiseBgLow: Double = 70

    @Option(name: .long, help: "Early-rise BG band upper edge (mg/dL): the gate ramps 1->0 over [high-15, high]; term is off above this (never pile onto the peak). Default 140.")
    var candidateEarlyRiseBgHigh: Double = 140

    @Option(name: .long, help: "Early-rise slope threshold (mg/dL per min): rise slope at/below this contributes nothing (no firing while flat/falling or on a post-low rebound's reversal). Default 0.3.")
    var candidateEarlyRiseSlopeThreshold: Double = 0.3

    @Option(name: .long, help: "Dynamic ISF: multiplier applied to the dose-sizing ISF at/above --candidate-dynisf-high-anchor (linear ramp from 1.0 at the low anchor). <1 = more insulin per mg/dL gap when BG is high (continuous insulin-resistance-with-glycemia model). Default 1.0 = off.")
    var candidateDynisfMultHigh: Double = 1.0

    @Option(name: .long, help: "Dynamic ISF low anchor (mg/dL): at/below this the dose-sizing ISF is unchanged. Default 100.")
    var candidateDynisfLowAnchor: Double = 100

    @Option(name: .long, help: "Dynamic ISF high anchor (mg/dL): at/above this the full multiplier applies. Default 200.")
    var candidateDynisfHighAnchor: Double = 200

    @Flag(name: .long, help: "Uncertainty-bounded dosing cap: REPLACE the flat/GBAF application factor AND the predicted-min bolus gate with a single state-derived cap — deliver the largest dose whose WORST-CASE trajectory (insulin effect ×(1+k)) WITH max basal suspension stays above the low threshold. A level cap on committed IOB (no wind-up).")
    var candidateUncertaintyCap: Bool = false

    @Option(name: .long, help: "Uncertainty cap k: sensitivity-uncertainty multiplier (worst case = insulin effect ×(1+k)). Larger = more buffer / less dosing. Default 0.5.")
    var candidateUncertaintyK: Double = 0.5

    @Option(name: .long, help: "Uncertainty cap fmax: hard ceiling on effective application factor (allowed dose / nominal need). <1 keeps a margin even when the worst-case is safe. Default 1.0.")
    var candidateUncertaintyFmax: Double = 1.0

    @Option(name: .long, help: "Uncertainty cap low threshold (mg/dL) the worst-case-with-suspension must stay above. 0 = use the suspend threshold.")
    var candidateUncertaintyLow: Double = 0

    @Option(name: .long, help: "Autosens gain: scale dose-sizing AND forecast ISF by (1 − gain × avg(BG−target) over the autosens window). Sustained high → ISF↓ (more insulin, resistance/under-counted carbs); sustained low → ISF↑. Multi-hour average ignores transient rises (the discrimination IRC lacks). 0 = off. Try ~0.002-0.006.")
    var candidateAutosensGain: Double = 0

    @Option(name: .long, help: "Autosens window (minutes) for the sustained BG−target average. Default 360 (6h). Longer = slower/more-sustained.")
    var candidateAutosensWindowMin: Double = 360

    @Option(name: .long, help: "Autosens min ISF ratio (most resistant). Default 0.7.")
    var candidateAutosensMin: Double = 0.7

    @Option(name: .long, help: "Autosens max ISF ratio (most sensitive). Default 1.3.")
    var candidateAutosensMax: Double = 1.3

    @Flag(name: .long, help: "Decouple the uncertainty cap's worst-case from autosens: when autosens lowers ISF (resistant), the cap still hedges that insulin could be as effective as nominal (the resistance estimate may be wrong) — refuses dangerous doses while letting autosens be aggressive where it's safe even if wrong.")
    var candidateUncertaintyDecouple: Bool = false

    @Flag(name: .long, help: "Enable candidate asymmetric HIGH correction: rise-only BG-addition driven by the positive retrospective discrepancy, with a fast-off velocity gate (turns off fast on a downtrend).")
    var candidateHighCorrection: Bool = false

    @Option(name: .long, help: "High-correction rise gain (scale on the rise-side BG-addition). Default 1.0.")
    var candidateHighCorrectionRiseGain: Double = 1.0

    @Option(name: .long, help: "High-correction effect duration (min). Default 60.")
    var candidateHighCorrectionEffectMin: Double = 60.0

    @Option(name: .long, help: "High-correction fast-off velocity (mg/dL/min): gate ramps to 0 as recent glucose velocity drops to -this. Smaller = turns off on a gentler downtrend. Default 0.5.")
    var candidateHighCorrectionFastOffVelocity: Double = 0.5

    @Option(name: .long, help: "Post-low forecast SUPPRESSION (mg/dL): when a recent low occurred, lower the candidate forecast by up to this (decaying over the window) so Loop backs off — selective lows-protector for the repeat-low regime. 0 = off (default).")
    var candidatePostlowSuppress: Double = 0.0

    @Option(name: .long, help: "Post-low suppression window / slow-off duration (min). Default 120.")
    var candidatePostlowWindow: Double = 120.0

    @Option(name: .long, help: "Post-low trigger threshold (mg/dL): a sample below this counts as a 'low'. Default 70.")
    var candidatePostlowThreshold: Double = 70.0

    @Option(name: .long, help: "Post-low TREND gain (mg/dL of extra forecast suppression per mg/dL/min of current downtrend, within the post-low window). Targets the rebound's second drop with lead time; fires only while BG is dropping again. 0 = off (plain recency-decay protector).")
    var candidatePostlowTrendGain: Double = 0.0

    @Option(name: .long, help: "Sustained post-low ISF REDUCTION factor (>1 = insulin modeled more effective, so Loop sizes the rebound correction DOWN at the source; decays with recency over the post-low window; EGP-safe via physical-delivery split). 1.0 = off.")
    var candidatePostlowIsfMult: Double = 1.0

    @Option(name: .long, help: "Post-low-GATED standard-RC rise-cut (corner candidate): within --candidate-postlow-window minutes of a sample below --candidate-postlow-threshold AND while BG < --candidate-postlow-rc-bg-max, scale the POSITIVE (unexplained-rise) RC discrepancy by this (0 = ignore rebound rises entirely). 1.0 = off.")
    var candidatePostlowRcRiseScale: Double = 1.0

    @Option(name: .long, help: "BG ceiling (mg/dL) for the post-low RC rise-cut gate: above it the high is treated as real and RC is normal. Default 180.")
    var candidatePostlowRcBgMax: Double = 180.0

    @Option(name: .long, help: "Fast-rise-GATED standard-RC rise-cut (meal-rise-stacking corner): while the trailing 15-min BG slope is at least this (mg/dL/min) AND BG < --candidate-rise-gate-bg-max, scale the positive RC discrepancy by --candidate-rise-gate-rc-rise-scale. 0 = off.")
    var candidateRiseGateSlope: Double = 0.0

    @Option(name: .long, help: "Rise scale applied while the fast-rise gate is active (0 = ignore the unexplained rise). Default 1.0.")
    var candidateRiseGateRcRiseScale: Double = 1.0

    @Option(name: .long, help: "BG ceiling (mg/dL) for the fast-rise gate. Default 180.")
    var candidateRiseGateBgMax: Double = 180.0

    @Option(name: .long, help: "σ-widened LOWER forecast band (candidate): each predicted point at τ min is lowered by k·σ5·(τ/5)^H up to --candidate-sigma-band-horizon-min, tapering to 0 by --candidate-sigma-band-taper-min; σ5 = causal EWMA std of the 5-min increment (λ --candidate-sigma-lambda per step, variance floored at 2·noise²). Eventual BG unchanged; the predicted minimum sees the volatility. 0 = off.")
    var candidateSigmaBandK: Double = 0.0

    @Option(name: .long, help: "σ band horizon (min) over which the band widens as (τ/5)^H. Default 60.")
    var candidateSigmaBandHorizonMin: Double = 60.0

    @Option(name: .long, help: "σ band taper end (min): the widening returns to 0 here. Default 120.")
    var candidateSigmaBandTaperMin: Double = 120.0

    @Option(name: .long, help: "Short-range scaling exponent H for the σ band (0.5 = random walk; measured 0.71). Default 0.71.")
    var candidateSigmaH: Double = 0.71

    @Option(name: .long, help: "EWMA λ per 5-min step for σ5 (0.875 ≈ 26-min half-life). Default 0.875.")
    var candidateSigmaLambda: Double = 0.875

    @Option(name: .long, help: "Per-reading sensor noise σ (mg/dL) used as the σ5 variance floor (2·noise²). Default 1.4.")
    var candidateSigmaNoise: Double = 1.4

    @Option(name: .long, help: "Calm-high LICENCE (candidate): when BG >= --candidate-calm-high-bg AND σ5 <= --candidate-calm-high-sigma-max, scale the application factor by this (capped at 1.0). 1.0 = off.")
    var candidateCalmHighAfScale: Double = 1.0

    @Option(name: .long, help: "Calm-high licence BG threshold (mg/dL). Default 180.")
    var candidateCalmHighBg: Double = 180.0

    @Option(name: .long, help: "Calm-high licence σ5 ceiling (mg/dL per 5 min). Default 3.5.")
    var candidateCalmHighSigmaMax: Double = 3.5

    @Flag(name: .long, help: "Apply the σ band only when the candidate has no carbs on board (COB = 0): unexplained volatility only, so an announced meal's rise does not trigger it.")
    var candidateSigmaBandCobGate: Bool = false

    @Flag(name: .long, help: "Apply the calm-high licence only when the candidate has no carbs on board (COB = 0): a heavy announcer's calm highs are post-meal with the bolus still working, so the extra application factor stacks into it and adds lows.")
    var candidateCalmHighCobGate: Bool = false

    @Option(name: .long, help: "Calm-high licence TREND gate: require the trailing 30-min glucose slope (mg/dL/min) to be at least this. 0 licenses only flat-or-rising highs; a calm DESCENT passes the sigma gate otherwise (a 1 mg/dL/min fall is sigma5 ~ 5). Omit for no trend gate.")
    var candidateCalmHighMinSlope: Double?

    @Option(name: .long, help: "Calm-high TARGET shift (mg/dL): in the calm-high state, lower the correction target range by this much. Reaches temp-basal donors, where the application-factor form is inert (they issue no automatic boluses). Suspend threshold untouched. 0 = off.")
    var candidateCalmHighTargetDelta: Double = 0

    @Option(name: .long, help: "Rise-gated low gate (780G meal detection): while glucose rises steadily, let the predicted minimum sit this many mg/dL below the correction-range floor before the automatic bolus is gated off (never below the suspend threshold). 0 = off.")
    var candidateLowGateRiseDrop: Double = 0

    @Option(name: .long, help: "Rise-gated low gate: trailing 30-min glucose slope (mg/dL/min) that counts as a rise.")
    var candidateLowGateRiseSlope: Double = 1.0

    @Option(name: .long, help: "Rise-gated low gate: current BG (mg/dL) at or above which it may engage.")
    var candidateLowGateRiseBgMin: Double = 120.0

    @Option(name: .long, help: "Control-IQ reference arm: no automatic bolus within this many minutes of the candidate's last bolus. 0 = off.")
    var candidateAutoBolusMinIntervalMin: Double = 0

    @Option(name: .long, help: "Control-IQ reference arm: automatic bolus only when the 30-min forecast exceeds this (mg/dL). 0 = off.")
    var candidateAutoBolusPred30Min: Double = 0

    @Option(name: .long, help: "E6 primer: one extra automatic bolus of this many mg/dL / ISF at a rise seen on the candidate's CGM (slope >= primer-slope, rise >= primer-rise over the 60-min minimum, no BG < 80 in 60 min), then a lockout. 0 = off.")
    var candidatePrimerMgdl: Double = 0
    @Option(name: .long, help: "E6 primer: trailing 30-min slope threshold, mg/dL/min.")
    var candidatePrimerSlope: Double = 1.5
    @Option(name: .long, help: "E6 primer: rise above the 60-min minimum, mg/dL.")
    var candidatePrimerRise: Double = 30
    @Option(name: .long, help: "E6 primer: minutes before another primer.")
    var candidatePrimerLockoutMin: Double = 180
    @Option(name: .long, help: "E6 primer, retractable form: deliver it as extra temp basal over this many minutes, cancelled when CGM rises < 5 mg/dL over 15 min. 0 = bolus.")
    var candidatePrimerTempMin: Double = 0

    @Option(name: .long, help: "Runway reserve (C40): spend this fraction of the extra correction that suspending scheduled basal could still take back before a plausible fall (forecast minus z*sigma5 band) reaches the suspend threshold. Delivered as an internal lowering of the correction aim; the user's target is not changed. 0 = off.")
    var candidateRunwayFraction: Double = 0

    @Option(name: .long, help: "sigma5 cold-start PRIOR (mg/dL per 5 min): until sigma-prior-steps valid increments have accrued since the start or the last CGM gap, pull sigma5 UP toward this value (linear ramp); with no usable CGM sigma5 = prior. Only ever raises sigma5. 0 = off (sigma5 starts at the noise floor).")
    var candidateSigmaPrior: Double = 0

    @Option(name: .long, help: "sigma5 cold-start prior: number of 5-min increments over which the prior fades out (default 12 = 1 h).")
    var candidateSigmaPriorSteps: Double = 12

    @Option(name: .long, help: "Runway reserve: band width in sigma5 units for the plausible fall (default 1).")
    var candidateRunwayZ: Double = 1.0

    @Option(name: .long, help: "Runway reserve: horizon (min) over which the plausible fall must stay above the suspend threshold (default 180).")
    var candidateRunwayHorizonMin: Double = 180

    @Option(name: .long, help: "Runway reserve: cap on the aim offset (mg/dL, default 60).")
    var candidateRunwayMaxMgdl: Double = 60

    @Option(name: .long, help: "Runway reserve: only when current BG is at least this (mg/dL, default 0 = no level gate).")
    var candidateRunwayBgMin: Double = 0

    @Flag(name: .long, help: "Runway reserve only with no carbs on board.")
    var candidateRunwayCobGate: Bool = false

    @Option(name: .long, help: "Curve-split diagnostic: peak (min) of a second curve used by one part of the controller only (see --split-curve-part). 0 = off.")
    var splitCurvePeakMin: Double = 0

    @Option(name: .long, help: "Curve-split diagnostic: duration (min) of the second curve (default 360).")
    var splitCurveDurationMin: Double = 360

    @Option(name: .long, help: "Curve-split diagnostic: which part uses the second curve: ice (counteraction → RC, carb absorption), correction (dose sizing), projection-cob or projection-rise (forward projection of past doses, only while carbs are on board / glucose is rising).")
    var splitCurvePart: String = "ice"

    @Option(name: .long, help: "Curve-split projection-rise: glucose rise over the last 15 min (mg/dL) that counts as rising (default 3).")
    var splitRiseMgdl: Double = 3
    @Option(name: .long, help: "Experiment: plateau UAM (minutes). Project recent unexplained appearance (ICE minus modeled carbs) forward as tapering absorption, but only while BG is flat or falling (15-min slope ramps the term from full at <= 0.2 to off at >= 0.5 mg/dL/min) and BG >= 100 (ramp 100-130). 0 = off.")
    var candidatePlateauUamMinutes: Double = 0
    @Option(name: .long, help: "Experiment: plateau UAM gain on the projected appearance rate. Default 1.")
    var candidatePlateauUamGain: Double = 1

    @Option(name: .long, help: "sigma-band BASELINE (mg/dL per 5 min): widen by k*max(0, sigma5 - baseline) instead of k*sigma5. Set to the donor's own median sigma5 so the band is zero in their typical state and carries no per-donor level offset. 0 = original absolute-sigma behaviour.")
    var candidateSigmaBandBaseline: Double = 0

    @Option(name: .long, help: "CONTROL for the sigma band: replace sigma5 with this CONSTANT, so the band carries no volatility signal. Set to the donor's median sigma5 to reproduce the average band the absolute-sigma form applies. 0 = off.")
    var candidateSigmaBandFixedSigma: Double = 0

    @Flag(name: .long, help: "GUARD-ONLY sigma band: the sigma-widened curve feeds only the predicted-minimum guard and the suspend check; the UNBANDED curve sizes the correction. Separates the tail question (guard) from the point question (dose) that Loop otherwise reads off one curve, so the band can be held at its measured plateau (taper 360) without lowering eventualBG. Requires --candidate-sigma-band-k > 0.")
    var candidateSigmaBandGuardOnly: Bool = false

    @Flag(name: .long, help: "NEGATIVE INSULIN DAMPER (candidate; Loop and Learn 'negative_insulin' customization, ported from nextdev_negative_insulin.patch): the predicted future rise from insulin delivered below scheduled basal (up to --candidate-nid-lag-min ago) sets a damper in [0, 0.95]; every positive 5-min delta of the assembled forecast is multiplied by (1 - damper). 25% at the anchor (0.8 x peak-activity hours x basal x ISF of predicted rise). Targets re-dosing into the rebound after a treated low.")
    var candidateNegativeInsulinDamper: Bool = false

    @Option(name: .long, help: "NID anchor alpha: the fraction of a positive delta that survives when the negative-insulin rise equals the anchor point. Loop's value 0.75 (= 25% damping).")
    var candidateNidAnchorAlpha: Double = 0.75

    @Option(name: .long, help: "NID marginal slope beyond the linear region; also the floor of alpha (damper cap = 1 - slope). Loop's value 0.05.")
    var candidateNidMarginalSlope: Double = 0.05

    @Option(name: .long, help: "NID lag (minutes): insulin delivered more recently than this is not yet counted. Loop's value 15.")
    var candidateNidLagMin: Double = 15

    @Option(name: .long, help: "BASAL LOCK (candidate; Loop and Learn 'basal_lock' customization, ported from nextdev_basal_lock.patch): while the latest glucose is above this (mg/dL), a recommended temp basal below the scheduled rate is raised to the scheduled rate; boluses untouched. Loop's guardrail is 200-300, recommended >= 220. 0 = off.")
    var candidateBasalLockBg: Double = 0

    @Option(name: .long, help: "PREDICTIVE pre-low damper GAIN: causal sustained-sensitivity trigger (causal ICE = v_bg - v_insulin over a trailing window). ISF-mult increase per mg/dL/min of negative ICE beyond the threshold; raises ISF proactively before the low. 0 = off.")
    var candidateSensDampGain: Double = 0.0

    @Option(name: .long, help: "Predictive damper: causal-ICE rate (mg/dL/min) below which the damper engages (BG dropping this much faster than insulin explains). Default 0.4.")
    var candidateSensDampThreshold: Double = 0.4

    @Option(name: .long, help: "Predictive damper: trailing window (min) for the causal ICE estimate. Default 45.")
    var candidateSensDampWindow: Double = 45.0

    @Option(name: .long, help: "Predictive damper: cap on the ISF multiplier. Default 2.5.")
    var candidateSensDampMax: Double = 2.5

    @Flag(name: .long, help: "Phase 2: compute the active-insulin glucose-effect over PHYSICAL delivered insulin (volume) rather than net-basal-units, so a candidate ISF boost amplifies real insulin even when delivery is below scheduled basal. Requires --candidate-isf-boost-active-only. Without it, sub-basal insulin sits in the EGP-credit term and the boost can't reach it (the Mar-29 'negative insulin' case). Default OFF (classic net-basal-units).")
    var candidateEgpPhysical: Bool = false
}

// Candidate OpenAPS (with --candidate-openaps)
struct SimulateOpenAPSFlags: ParsableArguments {
    @Option(name: .customLong("oaps-preset-target"), help: "Map a Trio Exercise preset NAME to a target (mg/dL) for presets whose target is carried only in the preset name, not the treatment fields/notes (e.g. a \"Dienst\" shift preset → 110). Format NAME:TARGET, repeatable. Matched case-insensitively against the Exercise note.")
    var oapsPresetTarget: [String] = []

    @Option(name: .long, help: "OpenAPS threshold_setting (mg/dL) — oref's minGuardBG safety floor. SMB is gated off when minGuardBG drops below this. Default 60 (oref stock). Raising it directly suppresses SMB-firing into the suspend zone.")
    var candidateOapsThreshold: Double?

    @Option(name: .long, help: "OpenAPS smb_delivery_ratio (0..1). Fraction of computed needed-correction delivered as SMB each cycle. Default 0.5. Lower = smaller SMBs, less aggressive bolus pathway.")
    var candidateOapsSmbRatio: Double?

    @Option(name: .long, help: "OpenAPS maxSMBBasalMinutes / maxUAMSMBBasalMinutes — single-SMB size cap in minutes of current basal. Default 30. Lower = smaller per-SMB cap.")
    var candidateOapsMaxSmbMin: Double?

    @Flag(name: .long, help: "OpenAPS useNewFormula — enable Dynamic ISF (auto-scales ISF with current BG — analog of Loop's GBAF). Off by default in oref stock.")
    var candidateOapsDynamicIsf: Bool = false

    @Flag(name: .long, help: "OpenAPS sigmoid — sigmoid-shaped Dynamic ISF curve (alternative to power-law). Use with --candidate-oaps-dynamic-isf.")
    var candidateOapsSigmoid: Bool = false

    @Option(name: .long, help: "OpenAPS adjustmentFactor (power-law Dynamic ISF aggression). Default 0.8. Higher = more aggressive scaling with BG.")
    var candidateOapsAdjustmentFactor: Double?

    @Option(name: .long, help: "OpenAPS adjustmentFactorSigmoid (sigmoid Dynamic ISF aggression). Default 0.5.")
    var candidateOapsAdjustmentFactorSigmoid: Double?

    @Option(name: .long, help: "OpenAPS autosens_max — upper clamp on the sensitivity/Dynamic-ISF ratio. Trio stock 1.2; match the user's 'Dynamic limit' (e.g. 1.9).")
    var candidateOapsAutosensMax: Double?

    @Option(name: .long, help: "OpenAPS autosens_min — lower clamp on the sensitivity/Dynamic-ISF ratio. Trio stock 0.7.")
    var candidateOapsAutosensMin: Double?

    @Option(name: .long, help: "OpenAPS insulin peak time (min) — drives the IOB curve AND Dynamic ISF insulinFactor (=120−peak). Uses an ultra-rapid curve so peaks <50 are allowed. Match the user's insulin (~41–45 Lyumjev/ultra-rapid). Default: rapid-acting (insulinFactor 55).")
    var candidateOapsInsulinPeak: Double?

    @Option(name: .long, help: "OpenAPS DIA (hours) = insulin_action_curve = insulin curve END time. Set to the user's profile DIA (e.g. 9); adapter otherwise hardcodes 6, which decays IOB too fast.")
    var candidateOapsDia: Double?

    @Option(name: .long, help: "OpenAPS insulin curve PRESET, no custom peak ('ultra-rapid' | 'rapid-acting'). ultra-rapid = Lyumjev/Fiasp: IOB peak 55 AND dynISF insulinFactor 70 (decoupled). Use instead of --candidate-oaps-insulin-peak.")
    var candidateOapsCurve: String?

    @Option(name: .long, help: "OpenAPS max_iob (U) — the user's real safety cap. Not uploaded by Trio; set for faithful reproduction (else a non-binding maxBolus×10 fallback is used).")
    var candidateOapsMaxIob: Double?

    @Option(name: .long, help: "OpenAPS preferences JSON (object) merged over the adapter defaults — supply a user's complete Trio settings verbatim. Inline JSON or @path/to/file.json.")
    var candidateOapsPrefsJson: String?

    @Option(name: .long, help: "Path to a CSV of time-varying dynISF adjustmentFactor: rows 'ISO8601,af' ascending. Per decision cycle the adapter uses the last row whose start <= t, overriding the prefs AF (reproduces a user who re-tuned AF over the replay period).")
    var candidateOapsAfCsv: String?

    @Option(name: .long, help: "Trio override presets, JSON object (inline or @path): preset name → {\"target\": mg/dL, \"percentage\": 100, \"smbIsOff\": false, \"isfAndCr\": true}. Reads Nightscout `Exercise` events as Trio overrides (latest started wins, active for its duration) instead of temp targets, and feeds the active one to oref. Infer each preset's settings from the field's devicestatus during its windows.")
    var candidateOapsOverridePresets: String?

    @Flag(name: .long, help: "Apply Trio's AAPS double-exponential glucose smoothing to the oref candidate's glucose feed (matches Trio's smoothGlucose; oref doses on smoothed, NS stores raw).")
    var candidateOapsSmoothGlucose: Bool = false

    @Option(name: .long, help: "Pump basal-pulse increment (U) for the oref TDD (floors each temp-basal segment). Omnipod 0.05 (default); 0.025/0.1 for other pumps.")
    var candidateOapsPumpPulse: Double = 0.05

    @Flag(name: .long, help: "OpenAPS ablation: disable UAM (enableUAM=false) — drop the unannounced-meal forecast/SMB while keeping SMB on the base forecast. Isolates UAM's forecast contribution.")
    var candidateOapsNoUam: Bool = false

    @Flag(name: .long, help: "OpenAPS ablation: disable all SMB (temp-basal-only delivery). Isolates the SMB delivery cadence from the forecast.")
    var candidateOapsNoSmb: Bool = false
}

extension SimulateCommand {
    // Data and output
    var nightscoutUrl: String { get { data.nightscoutUrl } set { data.nightscoutUrl = newValue } }
    var dataDir: String? { get { data.dataDir } set { data.dataDir = newValue } }
    var start: String { get { data.start } set { data.start = newValue } }
    var end: String { get { data.end } set { data.end = newValue } }
    var apiSecret: String? { get { data.apiSecret } set { data.apiSecret = newValue } }
    var token: String? { get { data.token } set { data.token = newValue } }
    var cacheDir: URL { get { data.cacheDir } set { data.cacheDir = newValue } }
    var baselineLabel: String { get { data.baselineLabel } set { data.baselineLabel = newValue } }
    var candidateLabel: String { get { data.candidateLabel } set { data.candidateLabel = newValue } }
    var localTimezone: String? { get { data.localTimezone } set { data.localTimezone = newValue } }
    var traceOut: String { get { data.traceOut } set { data.traceOut = newValue } }
    var exportForecastCurve: Bool { get { data.exportForecastCurve } set { data.exportForecastCurve = newValue } }
    // Run mode and decision timing
    var stepMinutes: Int { get { mode.stepMinutes } set { mode.stepMinutes = newValue } }
    var oracleFutureInputs: Bool { get { mode.oracleFutureInputs } set { mode.oracleFutureInputs = newValue } }
    var candidateCounterfactual: Bool { get { mode.candidateCounterfactual } set { mode.candidateCounterfactual = newValue } }
    var decisionTimeReplay: Bool { get { mode.decisionTimeReplay } set { mode.decisionTimeReplay = newValue } }
    var cfIdentity: Bool { get { mode.cfIdentity } set { mode.cfIdentity = newValue } }
    var decisionsFromCgm: Bool { get { mode.decisionsFromCgm } set { mode.decisionsFromCgm = newValue } }
    var decisionTimesCsv: String? { get { mode.decisionTimesCsv } set { mode.decisionTimesCsv = newValue } }
    var candidateCounterfactualBurnInHours: Double { get { mode.candidateCounterfactualBurnInHours } set { mode.candidateCounterfactualBurnInHours = newValue } }
    var glucoseLookbackHours: Double { get { mode.glucoseLookbackHours } set { mode.glucoseLookbackHours = newValue } }
    var insulinLookbackHours: Double { get { mode.insulinLookbackHours } set { mode.insulinLookbackHours = newValue } }
    var cgmStaleGuardMin: Double { get { mode.cgmStaleGuardMin } set { mode.cgmStaleGuardMin = newValue } }
    // Deployed system (the donor's Loop; both arms)
    var insulinType: String { get { deployment.insulinType } set { deployment.insulinType = newValue } }
    var integralRC: Bool { get { deployment.integralRC } set { deployment.integralRC = newValue } }
    var integralRCClamp: Bool { get { deployment.integralRCClamp } set { deployment.integralRCClamp = newValue } }
    var applyOverrides: Bool { get { deployment.applyOverrides } set { deployment.applyOverrides = newValue } }
    var loopTrioOverrides: String? { get { deployment.loopTrioOverrides } set { deployment.loopTrioOverrides = newValue } }
    var midAbsorptionIsf: Bool { get { deployment.midAbsorptionIsf } set { deployment.midAbsorptionIsf = newValue } }
    var legacyBasalIob: Bool { get { deployment.legacyBasalIob } set { deployment.legacyBasalIob = newValue } }
    var basalPulseQuantum: Double { get { deployment.basalPulseQuantum } set { deployment.basalPulseQuantum = newValue } }
    var adaptiveCarbAbsorption: Bool { get { deployment.adaptiveCarbAbsorption } set { deployment.adaptiveCarbAbsorption = newValue } }
    var carbRevisionsJson: String? { get { deployment.carbRevisionsJson } set { deployment.carbRevisionsJson = newValue } }
    var overrideTargetsJson: String? { get { deployment.overrideTargetsJson } set { deployment.overrideTargetsJson = newValue } }
    var sensitivityMultiplier: Double { get { deployment.sensitivityMultiplier } set { deployment.sensitivityMultiplier = newValue } }
    var asymmetricMomentum: Bool { get { deployment.asymmetricMomentum } set { deployment.asymmetricMomentum = newValue } }
    var clipInProgressTempBasal: Bool { get { deployment.clipInProgressTempBasal } set { deployment.clipInProgressTempBasal = newValue } }
    var noGradualTransitionsGate: Bool { get { deployment.noGradualTransitionsGate } set { deployment.noGradualTransitionsGate = newValue } }
    var legacyRcDecay: Bool { get { deployment.legacyRcDecay } set { deployment.legacyRcDecay = newValue } }
    var tempBasalStrategy: Bool { get { deployment.tempBasalStrategy } set { deployment.tempBasalStrategy = newValue } }
    var carbAbsorptionOverrun: Double { get { deployment.carbAbsorptionOverrun } set { deployment.carbAbsorptionOverrun = newValue } }
    var timeBasedAf: Bool { get { deployment.timeBasedAf } set { deployment.timeBasedAf = newValue } }
    var outagesCsv: String? { get { deployment.outagesCsv } set { deployment.outagesCsv = newValue } }
    var applicationFactor: Double { get { deployment.applicationFactor } set { deployment.applicationFactor = newValue } }
    var outageBasalReasons: String? { get { deployment.outageBasalReasons } set { deployment.outageBasalReasons = newValue } }
    var controllerInsulinModel: String? { get { deployment.controllerInsulinModel } set { deployment.controllerInsulinModel = newValue } }
    var customInsulinDurationMin: Double? { get { deployment.customInsulinDurationMin } set { deployment.customInsulinDurationMin = newValue } }
    var customInsulinPeakMin: Double? { get { deployment.customInsulinPeakMin } set { deployment.customInsulinPeakMin = newValue } }
    var controllerInsulinSwitch: [String] { get { deployment.controllerInsulinSwitch } set { deployment.controllerInsulinSwitch = newValue } }
    var sensorCapMgdl: Double { get { deployment.sensorCapMgdl } set { deployment.sensorCapMgdl = newValue } }
    // Candidate: controller and settings
    var candidateIntegralRC: Bool { get { candidate.candidateIntegralRC } set { candidate.candidateIntegralRC = newValue } }
    var candidateIntegralRCClamp: Bool { get { candidate.candidateIntegralRCClamp } set { candidate.candidateIntegralRCClamp = newValue } }
    var candidateSensitivityMultiplier: Double? { get { candidate.candidateSensitivityMultiplier } set { candidate.candidateSensitivityMultiplier = newValue } }
    var candidateBasalRateMultiplier: Double { get { candidate.candidateBasalRateMultiplier } set { candidate.candidateBasalRateMultiplier = newValue } }
    var candidateInsulinNeeds: Double? { get { candidate.candidateInsulinNeeds } set { candidate.candidateInsulinNeeds = newValue } }
    var candidateClipInProgressTempBasal: Bool { get { candidate.candidateClipInProgressTempBasal } set { candidate.candidateClipInProgressTempBasal = newValue } }
    var candidateIsfHourly: String? { get { candidate.candidateIsfHourly } set { candidate.candidateIsfHourly = newValue } }
    var candidateNeedsHourly: String? { get { candidate.candidateNeedsHourly } set { candidate.candidateNeedsHourly = newValue } }
    var candidateSchedulesJson: String? { get { candidate.candidateSchedulesJson } set { candidate.candidateSchedulesJson = newValue } }
    var candidateTargetMid: Double? { get { candidate.candidateTargetMid } set { candidate.candidateTargetMid = newValue } }
    var candidateTargetWidth: Double? { get { candidate.candidateTargetWidth } set { candidate.candidateTargetWidth = newValue } }
    var candidateGbaf: Bool { get { candidate.candidateGbaf } set { candidate.candidateGbaf = newValue } }
    var candidateGbafLowAnchor: Double { get { candidate.candidateGbafLowAnchor } set { candidate.candidateGbafLowAnchor = newValue } }
    var candidateGbafHighAnchor: Double { get { candidate.candidateGbafHighAnchor } set { candidate.candidateGbafHighAnchor = newValue } }
    var candidateGbafFactorLow: Double { get { candidate.candidateGbafFactorLow } set { candidate.candidateGbafFactorLow = newValue } }
    var candidateGbafFactorHigh: Double { get { candidate.candidateGbafFactorHigh } set { candidate.candidateGbafFactorHigh = newValue } }
    var candidateGbafForecastKeyed: Bool { get { candidate.candidateGbafForecastKeyed } set { candidate.candidateGbafForecastKeyed = newValue } }
    var candidateGbafForecastMinGuard: Double { get { candidate.candidateGbafForecastMinGuard } set { candidate.candidateGbafForecastMinGuard = newValue } }
    var candidateApplicationFactor: Double { get { candidate.candidateApplicationFactor } set { candidate.candidateApplicationFactor = newValue } }
    var candidateBolusIncrement: Double { get { candidate.candidateBolusIncrement } set { candidate.candidateBolusIncrement = newValue } }
    var candidateTempBasalIncrement: Double { get { candidate.candidateTempBasalIncrement } set { candidate.candidateTempBasalIncrement = newValue } }
    var candidateCarbAbsorptionCapMin: Double { get { candidate.candidateCarbAbsorptionCapMin } set { candidate.candidateCarbAbsorptionCapMin = newValue } }
    var candidateOpenaps: Bool { get { candidate.candidateOpenaps } set { candidate.candidateOpenaps = newValue } }
    var candidateLoopMimicOaps: Bool { get { candidate.candidateLoopMimicOaps } set { candidate.candidateLoopMimicOaps = newValue } }
    // Person: manual boluses and carbs
    var noUserBoluses: Bool { get { person.noUserBoluses } set { person.noUserBoluses = newValue } }
    var noCarbEntries: Bool { get { person.noCarbEntries } set { person.noCarbEntries = newValue } }
    var candidateIobAdjustManualBoluses: Bool { get { person.candidateIobAdjustManualBoluses } set { person.candidateIobAdjustManualBoluses = newValue } }
    var candidateManualBolusFromRecommendation: Bool { get { person.candidateManualBolusFromRecommendation } set { person.candidateManualBolusFromRecommendation = newValue } }
    var candidateManualBolusRecScale: Double { get { person.candidateManualBolusRecScale } set { person.candidateManualBolusRecScale = newValue } }
    // Body: ICE replay and patient
    var noKalman: Bool { get { mode.noKalman } set { mode.noKalman = newValue } }
    var simRawGlucose: Bool { get { mode.simRawGlucose } set { mode.simRawGlucose = newValue } }
    var counterRegOnset: Double { get { body.counterRegOnset } set { body.counterRegOnset = newValue } }
    var counterRegGain: Double { get { body.counterRegGain } set { body.counterRegGain = newValue } }
    var counterRegMax: Double { get { body.counterRegMax } set { body.counterRegMax = newValue } }
    var counterRegAbsolute: Bool { get { body.counterRegAbsolute } set { body.counterRegAbsolute = newValue } }
    var counterRegTauMin: Double { get { body.counterRegTauMin } set { body.counterRegTauMin = newValue } }
    var glucoseEffectiveness: Double { get { body.glucoseEffectiveness } set { body.glucoseEffectiveness = newValue } }
    var lowResponseModel: String? { get { body.lowResponseModel } set { body.lowResponseModel = newValue } }
    var highResponseModel: String? { get { body.highResponseModel } set { body.highResponseModel = newValue } }
    var lowResponseSubtractCsv: String? { get { body.lowResponseSubtractCsv } set { body.lowResponseSubtractCsv = newValue } }
    var cfGapReanchorMin: Double { get { body.cfGapReanchorMin } set { body.cfGapReanchorMin = newValue } }
    var patientIsf: Double? { get { body.patientIsf } set { body.patientIsf = newValue } }
    var patientInsulinModel: String? { get { body.patientInsulinModel } set { body.patientInsulinModel = newValue } }
    var candidateInferSensitivity: Bool { get { body.candidateInferSensitivity } set { body.candidateInferSensitivity = newValue } }
    var candidateInferSensitivityMax: Double { get { body.candidateInferSensitivityMax } set { body.candidateInferSensitivityMax = newValue } }
    var candidateInferSensitivityWindowMin: Double { get { body.candidateInferSensitivityWindowMin } set { body.candidateInferSensitivityWindowMin = newValue } }
    var candidateInferSensitivitySmoothMin: Double { get { body.candidateInferSensitivitySmoothMin } set { body.candidateInferSensitivitySmoothMin = newValue } }
    var candidateInferSensitivitySmoothPrior: Double { get { body.candidateInferSensitivitySmoothPrior } set { body.candidateInferSensitivitySmoothPrior = newValue } }
    var candidateDumpNieCsv: String? { get { body.candidateDumpNieCsv } set { body.candidateDumpNieCsv = newValue } }
    var insulinPhysicalPeak: Double? { get { body.insulinPhysicalPeak } set { body.insulinPhysicalPeak = newValue } }
    var insulinPhysicalDia: Double? { get { body.insulinPhysicalDia } set { body.insulinPhysicalDia = newValue } }
    // Body: external plant
    var externalPlant: String? { get { plant.externalPlant } set { plant.externalPlant = newValue } }
    var plantBehavior: Bool { get { plant.plantBehavior } set { plant.plantBehavior = newValue } }
    // Candidate Loop experiments
    var candidateAsymmetricMomentum: Bool { get { loopExperiments.candidateAsymmetricMomentum } set { loopExperiments.candidateAsymmetricMomentum = newValue } }
    var candidateMomentumAlphaSlow: Double { get { loopExperiments.candidateMomentumAlphaSlow } set { loopExperiments.candidateMomentumAlphaSlow = newValue } }
    var candidateMomentumAlphaFast: Double { get { loopExperiments.candidateMomentumAlphaFast } set { loopExperiments.candidateMomentumAlphaFast = newValue } }
    var candidateSigmaBandDescentGate: Bool { get { loopExperiments.candidateSigmaBandDescentGate } set { loopExperiments.candidateSigmaBandDescentGate = newValue } }
    var candidateDescentRcRiseScale: Double { get { loopExperiments.candidateDescentRcRiseScale } set { loopExperiments.candidateDescentRcRiseScale = newValue } }
    var candidateDescentHighBgMin: Double { get { loopExperiments.candidateDescentHighBgMin } set { loopExperiments.candidateDescentHighBgMin = newValue } }
    var candidateDescentWindowMin: Double { get { loopExperiments.candidateDescentWindowMin } set { loopExperiments.candidateDescentWindowMin = newValue } }
    var candidateDescentSlopeMax: Double { get { loopExperiments.candidateDescentSlopeMax } set { loopExperiments.candidateDescentSlopeMax = newValue } }
    var candidateMomentumCap: Double? { get { loopExperiments.candidateMomentumCap } set { loopExperiments.candidateMomentumCap = newValue } }
    var candidateIsfCsv: String? { get { loopExperiments.candidateIsfCsv } set { loopExperiments.candidateIsfCsv = newValue } }
    var candidateForecastOffsetCsv: String? { get { loopExperiments.candidateForecastOffsetCsv } set { loopExperiments.candidateForecastOffsetCsv = newValue } }
    var candidateIsfCsvToleranceSec: Double { get { loopExperiments.candidateIsfCsvToleranceSec } set { loopExperiments.candidateIsfCsvToleranceSec = newValue } }
    var candidateIsfBoostGateEventual: Double? { get { loopExperiments.candidateIsfBoostGateEventual } set { loopExperiments.candidateIsfBoostGateEventual = newValue } }
    var candidateIsfBoostVetoIce: Double? { get { loopExperiments.candidateIsfBoostVetoIce } set { loopExperiments.candidateIsfBoostVetoIce = newValue } }
    var candidateIsfBoostActiveOnly: Bool { get { loopExperiments.candidateIsfBoostActiveOnly } set { loopExperiments.candidateIsfBoostActiveOnly = newValue } }
    var candidateIrcDropScale: Double { get { loopExperiments.candidateIrcDropScale } set { loopExperiments.candidateIrcDropScale = newValue } }
    var candidateIrcRiseScale: Double { get { loopExperiments.candidateIrcRiseScale } set { loopExperiments.candidateIrcRiseScale = newValue } }
    var candidateAsymmetricStdRc: Bool { get { loopExperiments.candidateAsymmetricStdRc } set { loopExperiments.candidateAsymmetricStdRc = newValue } }
    var candidateIrcLowMemoryScale: Double { get { loopExperiments.candidateIrcLowMemoryScale } set { loopExperiments.candidateIrcLowMemoryScale = newValue } }
    var candidateIrcDropDurationScale: Double { get { loopExperiments.candidateIrcDropDurationScale } set { loopExperiments.candidateIrcDropDurationScale = newValue } }
    var candidateIrcRiseDurationScale: Double { get { loopExperiments.candidateIrcRiseDurationScale } set { loopExperiments.candidateIrcRiseDurationScale = newValue } }
    var candidateRcRetrospectionMin: Double? { get { loopExperiments.candidateRcRetrospectionMin } set { loopExperiments.candidateRcRetrospectionMin = newValue } }
    var candidateRcEffectDurationMin: Double? { get { loopExperiments.candidateRcEffectDurationMin } set { loopExperiments.candidateRcEffectDurationMin = newValue } }
    var candidateMomentumProjectionMin: Double { get { loopExperiments.candidateMomentumProjectionMin } set { loopExperiments.candidateMomentumProjectionMin = newValue } }
    var candidateMomentumLookbackMin: Double { get { loopExperiments.candidateMomentumLookbackMin } set { loopExperiments.candidateMomentumLookbackMin = newValue } }
    var candidateSensitiveModeTauMin: Double { get { loopExperiments.candidateSensitiveModeTauMin } set { loopExperiments.candidateSensitiveModeTauMin = newValue } }
    var candidateSlowRcTauMin: Double { get { loopExperiments.candidateSlowRcTauMin } set { loopExperiments.candidateSlowRcTauMin = newValue } }
    var candidateSlowRcGain: Double { get { loopExperiments.candidateSlowRcGain } set { loopExperiments.candidateSlowRcGain = newValue } }
    var candidateSlowRcMin: Double { get { loopExperiments.candidateSlowRcMin } set { loopExperiments.candidateSlowRcMin = newValue } }
    var candidateSlowRcMax: Double { get { loopExperiments.candidateSlowRcMax } set { loopExperiments.candidateSlowRcMax = newValue } }
    var candidateSlowRcMode: String { get { loopExperiments.candidateSlowRcMode } set { loopExperiments.candidateSlowRcMode = newValue } }
    var candidateSlowRcClipMgdl: Double { get { loopExperiments.candidateSlowRcClipMgdl } set { loopExperiments.candidateSlowRcClipMgdl = newValue } }
    var candidateSlowRcLeakMin: Double { get { loopExperiments.candidateSlowRcLeakMin } set { loopExperiments.candidateSlowRcLeakMin = newValue } }
    var candidateSlowRcPostlowFreezeMin: Double { get { loopExperiments.candidateSlowRcPostlowFreezeMin } set { loopExperiments.candidateSlowRcPostlowFreezeMin = newValue } }
    var candidateSlowRcGateJson: String? { get { loopExperiments.candidateSlowRcGateJson } set { loopExperiments.candidateSlowRcGateJson = newValue } }
    var candidateSlowRcNeeds: Bool { get { loopExperiments.candidateSlowRcNeeds } set { loopExperiments.candidateSlowRcNeeds = newValue } }
    var candidateSlowRcLowShrink: Double { get { loopExperiments.candidateSlowRcLowShrink } set { loopExperiments.candidateSlowRcLowShrink = newValue } }
    var candidateSensitiveModeGain: Double { get { loopExperiments.candidateSensitiveModeGain } set { loopExperiments.candidateSensitiveModeGain = newValue } }
    var candidateIceRiseBoostGain: Double { get { loopExperiments.candidateIceRiseBoostGain } set { loopExperiments.candidateIceRiseBoostGain = newValue } }
    var candidateIceRiseBoostBgLo: Double { get { loopExperiments.candidateIceRiseBoostBgLo } set { loopExperiments.candidateIceRiseBoostBgLo = newValue } }
    var candidateIceRiseBoostBgHi: Double { get { loopExperiments.candidateIceRiseBoostBgHi } set { loopExperiments.candidateIceRiseBoostBgHi = newValue } }
    var candidateIceRiseBoostTauMin: Double { get { loopExperiments.candidateIceRiseBoostTauMin } set { loopExperiments.candidateIceRiseBoostTauMin = newValue } }
    var candidateIceRiseBoostThresh: Double { get { loopExperiments.candidateIceRiseBoostThresh } set { loopExperiments.candidateIceRiseBoostThresh = newValue } }
    var candidateIceRiseBoostSensSuppress: Double { get { loopExperiments.candidateIceRiseBoostSensSuppress } set { loopExperiments.candidateIceRiseBoostSensSuppress = newValue } }
    var candidateIceRiseBoostIsfFadeLo: Double { get { loopExperiments.candidateIceRiseBoostIsfFadeLo } set { loopExperiments.candidateIceRiseBoostIsfFadeLo = newValue } }
    var candidateIceRiseBoostIsfFadeHi: Double { get { loopExperiments.candidateIceRiseBoostIsfFadeHi } set { loopExperiments.candidateIceRiseBoostIsfFadeHi = newValue } }
    var candidateSoftLowGate: Bool { get { loopExperiments.candidateSoftLowGate } set { loopExperiments.candidateSoftLowGate = newValue } }
    var candidateLowGateThreshold: Double? { get { loopExperiments.candidateLowGateThreshold } set { loopExperiments.candidateLowGateThreshold = newValue } }
    var candidateUamMinutes: Double { get { loopExperiments.candidateUamMinutes } set { loopExperiments.candidateUamMinutes = newValue } }
    var candidateEarlyRiseMinutes: Double { get { loopExperiments.candidateEarlyRiseMinutes } set { loopExperiments.candidateEarlyRiseMinutes = newValue } }
    var candidateEarlyRiseGain: Double { get { loopExperiments.candidateEarlyRiseGain } set { loopExperiments.candidateEarlyRiseGain = newValue } }
    var candidateEarlyRiseBgLow: Double { get { loopExperiments.candidateEarlyRiseBgLow } set { loopExperiments.candidateEarlyRiseBgLow = newValue } }
    var candidateEarlyRiseBgHigh: Double { get { loopExperiments.candidateEarlyRiseBgHigh } set { loopExperiments.candidateEarlyRiseBgHigh = newValue } }
    var candidateEarlyRiseSlopeThreshold: Double { get { loopExperiments.candidateEarlyRiseSlopeThreshold } set { loopExperiments.candidateEarlyRiseSlopeThreshold = newValue } }
    var candidateDynisfMultHigh: Double { get { loopExperiments.candidateDynisfMultHigh } set { loopExperiments.candidateDynisfMultHigh = newValue } }
    var candidateDynisfLowAnchor: Double { get { loopExperiments.candidateDynisfLowAnchor } set { loopExperiments.candidateDynisfLowAnchor = newValue } }
    var candidateDynisfHighAnchor: Double { get { loopExperiments.candidateDynisfHighAnchor } set { loopExperiments.candidateDynisfHighAnchor = newValue } }
    var candidateUncertaintyCap: Bool { get { loopExperiments.candidateUncertaintyCap } set { loopExperiments.candidateUncertaintyCap = newValue } }
    var candidateUncertaintyK: Double { get { loopExperiments.candidateUncertaintyK } set { loopExperiments.candidateUncertaintyK = newValue } }
    var candidateUncertaintyFmax: Double { get { loopExperiments.candidateUncertaintyFmax } set { loopExperiments.candidateUncertaintyFmax = newValue } }
    var candidateUncertaintyLow: Double { get { loopExperiments.candidateUncertaintyLow } set { loopExperiments.candidateUncertaintyLow = newValue } }
    var candidateAutosensGain: Double { get { loopExperiments.candidateAutosensGain } set { loopExperiments.candidateAutosensGain = newValue } }
    var candidateAutosensWindowMin: Double { get { loopExperiments.candidateAutosensWindowMin } set { loopExperiments.candidateAutosensWindowMin = newValue } }
    var candidateAutosensMin: Double { get { loopExperiments.candidateAutosensMin } set { loopExperiments.candidateAutosensMin = newValue } }
    var candidateAutosensMax: Double { get { loopExperiments.candidateAutosensMax } set { loopExperiments.candidateAutosensMax = newValue } }
    var candidateUncertaintyDecouple: Bool { get { loopExperiments.candidateUncertaintyDecouple } set { loopExperiments.candidateUncertaintyDecouple = newValue } }
    var candidateHighCorrection: Bool { get { loopExperiments.candidateHighCorrection } set { loopExperiments.candidateHighCorrection = newValue } }
    var candidateHighCorrectionRiseGain: Double { get { loopExperiments.candidateHighCorrectionRiseGain } set { loopExperiments.candidateHighCorrectionRiseGain = newValue } }
    var candidateHighCorrectionEffectMin: Double { get { loopExperiments.candidateHighCorrectionEffectMin } set { loopExperiments.candidateHighCorrectionEffectMin = newValue } }
    var candidateHighCorrectionFastOffVelocity: Double { get { loopExperiments.candidateHighCorrectionFastOffVelocity } set { loopExperiments.candidateHighCorrectionFastOffVelocity = newValue } }
    var candidatePostlowSuppress: Double { get { loopExperiments.candidatePostlowSuppress } set { loopExperiments.candidatePostlowSuppress = newValue } }
    var candidatePostlowWindow: Double { get { loopExperiments.candidatePostlowWindow } set { loopExperiments.candidatePostlowWindow = newValue } }
    var candidatePostlowThreshold: Double { get { loopExperiments.candidatePostlowThreshold } set { loopExperiments.candidatePostlowThreshold = newValue } }
    var candidatePostlowTrendGain: Double { get { loopExperiments.candidatePostlowTrendGain } set { loopExperiments.candidatePostlowTrendGain = newValue } }
    var candidatePostlowIsfMult: Double { get { loopExperiments.candidatePostlowIsfMult } set { loopExperiments.candidatePostlowIsfMult = newValue } }
    var candidatePostlowRcRiseScale: Double { get { loopExperiments.candidatePostlowRcRiseScale } set { loopExperiments.candidatePostlowRcRiseScale = newValue } }
    var candidatePostlowRcBgMax: Double { get { loopExperiments.candidatePostlowRcBgMax } set { loopExperiments.candidatePostlowRcBgMax = newValue } }
    var candidateRiseGateSlope: Double { get { loopExperiments.candidateRiseGateSlope } set { loopExperiments.candidateRiseGateSlope = newValue } }
    var candidateRiseGateRcRiseScale: Double { get { loopExperiments.candidateRiseGateRcRiseScale } set { loopExperiments.candidateRiseGateRcRiseScale = newValue } }
    var candidateRiseGateBgMax: Double { get { loopExperiments.candidateRiseGateBgMax } set { loopExperiments.candidateRiseGateBgMax = newValue } }
    var candidateSigmaBandK: Double { get { loopExperiments.candidateSigmaBandK } set { loopExperiments.candidateSigmaBandK = newValue } }
    var candidateSigmaBandHorizonMin: Double { get { loopExperiments.candidateSigmaBandHorizonMin } set { loopExperiments.candidateSigmaBandHorizonMin = newValue } }
    var candidateSigmaBandTaperMin: Double { get { loopExperiments.candidateSigmaBandTaperMin } set { loopExperiments.candidateSigmaBandTaperMin = newValue } }
    var candidateSigmaH: Double { get { loopExperiments.candidateSigmaH } set { loopExperiments.candidateSigmaH = newValue } }
    var candidateSigmaLambda: Double { get { loopExperiments.candidateSigmaLambda } set { loopExperiments.candidateSigmaLambda = newValue } }
    var candidateSigmaNoise: Double { get { loopExperiments.candidateSigmaNoise } set { loopExperiments.candidateSigmaNoise = newValue } }
    var candidateCalmHighAfScale: Double { get { loopExperiments.candidateCalmHighAfScale } set { loopExperiments.candidateCalmHighAfScale = newValue } }
    var candidateCalmHighBg: Double { get { loopExperiments.candidateCalmHighBg } set { loopExperiments.candidateCalmHighBg = newValue } }
    var candidateCalmHighSigmaMax: Double { get { loopExperiments.candidateCalmHighSigmaMax } set { loopExperiments.candidateCalmHighSigmaMax = newValue } }
    var candidateSigmaBandCobGate: Bool { get { loopExperiments.candidateSigmaBandCobGate } set { loopExperiments.candidateSigmaBandCobGate = newValue } }
    var candidateCalmHighCobGate: Bool { get { loopExperiments.candidateCalmHighCobGate } set { loopExperiments.candidateCalmHighCobGate = newValue } }
    var candidateCalmHighMinSlope: Double? { get { loopExperiments.candidateCalmHighMinSlope } set { loopExperiments.candidateCalmHighMinSlope = newValue } }
    var candidateCalmHighTargetDelta: Double { get { loopExperiments.candidateCalmHighTargetDelta } set { loopExperiments.candidateCalmHighTargetDelta = newValue } }
    var candidateLowGateRiseDrop: Double { get { loopExperiments.candidateLowGateRiseDrop } set { loopExperiments.candidateLowGateRiseDrop = newValue } }
    var candidateLowGateRiseSlope: Double { get { loopExperiments.candidateLowGateRiseSlope } set { loopExperiments.candidateLowGateRiseSlope = newValue } }
    var candidateLowGateRiseBgMin: Double { get { loopExperiments.candidateLowGateRiseBgMin } set { loopExperiments.candidateLowGateRiseBgMin = newValue } }
    var candidateAutoBolusMinIntervalMin: Double { get { loopExperiments.candidateAutoBolusMinIntervalMin } set { loopExperiments.candidateAutoBolusMinIntervalMin = newValue } }
    var candidateAutoBolusPred30Min: Double { get { loopExperiments.candidateAutoBolusPred30Min } set { loopExperiments.candidateAutoBolusPred30Min = newValue } }
    var candidatePrimerMgdl: Double { get { loopExperiments.candidatePrimerMgdl } set { loopExperiments.candidatePrimerMgdl = newValue } }
    var candidatePrimerSlope: Double { get { loopExperiments.candidatePrimerSlope } set { loopExperiments.candidatePrimerSlope = newValue } }
    var candidatePrimerRise: Double { get { loopExperiments.candidatePrimerRise } set { loopExperiments.candidatePrimerRise = newValue } }
    var candidatePrimerLockoutMin: Double { get { loopExperiments.candidatePrimerLockoutMin } set { loopExperiments.candidatePrimerLockoutMin = newValue } }
    var candidatePrimerTempMin: Double { get { loopExperiments.candidatePrimerTempMin } set { loopExperiments.candidatePrimerTempMin = newValue } }
    var candidateRunwayFraction: Double { get { loopExperiments.candidateRunwayFraction } set { loopExperiments.candidateRunwayFraction = newValue } }
    var candidateSigmaPrior: Double { get { loopExperiments.candidateSigmaPrior } set { loopExperiments.candidateSigmaPrior = newValue } }
    var candidateSigmaPriorSteps: Double { get { loopExperiments.candidateSigmaPriorSteps } set { loopExperiments.candidateSigmaPriorSteps = newValue } }
    var candidateRunwayZ: Double { get { loopExperiments.candidateRunwayZ } set { loopExperiments.candidateRunwayZ = newValue } }
    var candidateRunwayHorizonMin: Double { get { loopExperiments.candidateRunwayHorizonMin } set { loopExperiments.candidateRunwayHorizonMin = newValue } }
    var candidateRunwayMaxMgdl: Double { get { loopExperiments.candidateRunwayMaxMgdl } set { loopExperiments.candidateRunwayMaxMgdl = newValue } }
    var candidateRunwayBgMin: Double { get { loopExperiments.candidateRunwayBgMin } set { loopExperiments.candidateRunwayBgMin = newValue } }
    var candidateRunwayCobGate: Bool { get { loopExperiments.candidateRunwayCobGate } set { loopExperiments.candidateRunwayCobGate = newValue } }
    var splitCurvePeakMin: Double { get { loopExperiments.splitCurvePeakMin } set { loopExperiments.splitCurvePeakMin = newValue } }
    var splitCurveDurationMin: Double { get { loopExperiments.splitCurveDurationMin } set { loopExperiments.splitCurveDurationMin = newValue } }
    var splitCurvePart: String { get { loopExperiments.splitCurvePart } set { loopExperiments.splitCurvePart = newValue } }
    var splitRiseMgdl: Double { get { loopExperiments.splitRiseMgdl } set { loopExperiments.splitRiseMgdl = newValue } }
    var candidatePlateauUamMinutes: Double { get { loopExperiments.candidatePlateauUamMinutes } set { loopExperiments.candidatePlateauUamMinutes = newValue } }
    var candidatePlateauUamGain: Double { get { loopExperiments.candidatePlateauUamGain } set { loopExperiments.candidatePlateauUamGain = newValue } }
    var candidateSigmaBandBaseline: Double { get { loopExperiments.candidateSigmaBandBaseline } set { loopExperiments.candidateSigmaBandBaseline = newValue } }
    var candidateSigmaBandFixedSigma: Double { get { loopExperiments.candidateSigmaBandFixedSigma } set { loopExperiments.candidateSigmaBandFixedSigma = newValue } }
    var candidateSigmaBandGuardOnly: Bool { get { loopExperiments.candidateSigmaBandGuardOnly } set { loopExperiments.candidateSigmaBandGuardOnly = newValue } }
    var candidateNegativeInsulinDamper: Bool { get { loopExperiments.candidateNegativeInsulinDamper } set { loopExperiments.candidateNegativeInsulinDamper = newValue } }
    var candidateNidAnchorAlpha: Double { get { loopExperiments.candidateNidAnchorAlpha } set { loopExperiments.candidateNidAnchorAlpha = newValue } }
    var candidateNidMarginalSlope: Double { get { loopExperiments.candidateNidMarginalSlope } set { loopExperiments.candidateNidMarginalSlope = newValue } }
    var candidateNidLagMin: Double { get { loopExperiments.candidateNidLagMin } set { loopExperiments.candidateNidLagMin = newValue } }
    var candidateBasalLockBg: Double { get { loopExperiments.candidateBasalLockBg } set { loopExperiments.candidateBasalLockBg = newValue } }
    var candidateSensDampGain: Double { get { loopExperiments.candidateSensDampGain } set { loopExperiments.candidateSensDampGain = newValue } }
    var candidateSensDampThreshold: Double { get { loopExperiments.candidateSensDampThreshold } set { loopExperiments.candidateSensDampThreshold = newValue } }
    var candidateSensDampWindow: Double { get { loopExperiments.candidateSensDampWindow } set { loopExperiments.candidateSensDampWindow = newValue } }
    var candidateSensDampMax: Double { get { loopExperiments.candidateSensDampMax } set { loopExperiments.candidateSensDampMax = newValue } }
    var candidateEgpPhysical: Bool { get { loopExperiments.candidateEgpPhysical } set { loopExperiments.candidateEgpPhysical = newValue } }
    // Candidate OpenAPS (with --candidate-openaps)
    var oapsPresetTarget: [String] { get { openaps.oapsPresetTarget } set { openaps.oapsPresetTarget = newValue } }
    var candidateOapsThreshold: Double? { get { openaps.candidateOapsThreshold } set { openaps.candidateOapsThreshold = newValue } }
    var candidateOapsSmbRatio: Double? { get { openaps.candidateOapsSmbRatio } set { openaps.candidateOapsSmbRatio = newValue } }
    var candidateOapsMaxSmbMin: Double? { get { openaps.candidateOapsMaxSmbMin } set { openaps.candidateOapsMaxSmbMin = newValue } }
    var candidateOapsDynamicIsf: Bool { get { openaps.candidateOapsDynamicIsf } set { openaps.candidateOapsDynamicIsf = newValue } }
    var candidateOapsSigmoid: Bool { get { openaps.candidateOapsSigmoid } set { openaps.candidateOapsSigmoid = newValue } }
    var candidateOapsAdjustmentFactor: Double? { get { openaps.candidateOapsAdjustmentFactor } set { openaps.candidateOapsAdjustmentFactor = newValue } }
    var candidateOapsAdjustmentFactorSigmoid: Double? { get { openaps.candidateOapsAdjustmentFactorSigmoid } set { openaps.candidateOapsAdjustmentFactorSigmoid = newValue } }
    var candidateOapsAutosensMax: Double? { get { openaps.candidateOapsAutosensMax } set { openaps.candidateOapsAutosensMax = newValue } }
    var candidateOapsAutosensMin: Double? { get { openaps.candidateOapsAutosensMin } set { openaps.candidateOapsAutosensMin = newValue } }
    var candidateOapsInsulinPeak: Double? { get { openaps.candidateOapsInsulinPeak } set { openaps.candidateOapsInsulinPeak = newValue } }
    var candidateOapsDia: Double? { get { openaps.candidateOapsDia } set { openaps.candidateOapsDia = newValue } }
    var candidateOapsCurve: String? { get { openaps.candidateOapsCurve } set { openaps.candidateOapsCurve = newValue } }
    var candidateOapsMaxIob: Double? { get { openaps.candidateOapsMaxIob } set { openaps.candidateOapsMaxIob = newValue } }
    var candidateOapsPrefsJson: String? { get { openaps.candidateOapsPrefsJson } set { openaps.candidateOapsPrefsJson = newValue } }
    var candidateOapsAfCsv: String? { get { openaps.candidateOapsAfCsv } set { openaps.candidateOapsAfCsv = newValue } }
    var candidateOapsOverridePresets: String? { get { openaps.candidateOapsOverridePresets } set { openaps.candidateOapsOverridePresets = newValue } }
    var candidateOapsSmoothGlucose: Bool { get { openaps.candidateOapsSmoothGlucose } set { openaps.candidateOapsSmoothGlucose = newValue } }
    var candidateOapsPumpPulse: Double { get { openaps.candidateOapsPumpPulse } set { openaps.candidateOapsPumpPulse = newValue } }
    var candidateOapsNoUam: Bool { get { openaps.candidateOapsNoUam } set { openaps.candidateOapsNoUam = newValue } }
    var candidateOapsNoSmb: Bool { get { openaps.candidateOapsNoSmb } set { openaps.candidateOapsNoSmb = newValue } }
}
