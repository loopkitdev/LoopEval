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

@available(macOS 10.15, macCatalyst 13, iOS 13, tvOS 13, watchOS 6, *)
struct SimulateCommand: AsyncParsableCommand {

    static let configuration = CommandConfiguration(
        commandName: "simulate",
        abstract: "Closed-loop counterfactual simulation (full feedback) — slower than bench but accurate for aggressive candidates."
    )

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

    @Option(name: .long, help: "Cache directory", transform: URL.init(fileURLWithPath:))
    var cacheDir: URL = URL(fileURLWithPath: NSHomeDirectory())
        .appendingPathComponent(".loop-eval/cache")

    @Option(name: .long, help: "Insulin model")
    var insulinType: String = "rapidActingAdult"

    @Option(name: .long, help: "Eval step (minutes, default 5)")
    var stepMinutes: Int = 5

    @Flag(name: .long, help: "Use integral RC for baseline")
    var integralRC: Bool = false

    @Flag(name: .long, help: "Disable Kalman smoothing")
    var noKalman: Bool = false

    @Flag(name: .long, inversion: .prefixedNo, help: "Run the SIMULATOR (Loop decision-time glucose input, the counter trajectory, and outcome stats) on the ORIGINAL noisy CGM samples, while keeping the RTS-smoothed trace for patient-physiology estimation (ICE + sensitivity multiplier m(t)). Raw samples are resampled onto the smoothed grid's exact timestamps so the per-grid m(t) stays aligned. Requires Kalman smoothing (no effect with --no-kalman). DEFAULT ON; pass --no-sim-raw-glucose for the legacy all-smoothed sim.")
    var simRawGlucose: Bool = true

    @Option(name: .long, help: "Baseline ISF multiplier")
    var sensitivityMultiplier: Double = 1.0

    @Flag(name: .long, help: "Use asymmetric momentum on baseline")
    var asymmetricMomentum: Bool = false

    @Option(name: .long, help: "Baseline label")
    var baselineLabel: String = "Baseline"

    @Option(name: .long, help: "Candidate label")
    var candidateLabel: String = "Candidate"

    // Candidate-side flags (subset of bench's; can extend as needed)
    @Flag(name: .long, help: "Use integral RC for candidate")
    var candidateIntegralRC: Bool = false

    @Flag(name: .long, help: "Use asymmetric momentum for candidate")
    var candidateAsymmetricMomentum: Bool = false

    @Option(name: .long, help: "Candidate asymmetric-momentum alpha-slow (default 0.15)")
    var candidateMomentumAlphaSlow: Double = 0.15

    @Option(name: .long, help: "Candidate asymmetric-momentum alpha-fast (default 0.85)")
    var candidateMomentumAlphaFast: Double = 0.85

    @Option(name: .long, help: "Candidate ISF multiplier")
    var candidateSensitivityMultiplier: Double?

    @Flag(name: .long, help: "Candidate: treat a temp basal still running at the decision instant as ENDED at t (clean going-forward design). Default off = project it forward as FieldLoop does. Baseline always stays field-faithful.")
    var candidateClipInProgressTempBasal: Bool = false

    @Option(name: .long, help: "Per-hour candidate ISF multipliers (24 csv)")
    var candidateIsfHourly: String?

    @Option(name: .long, help: "Local timezone identifier")
    var localTimezone: String?

    @Option(name: .long, help: "Output trace JSON path (compatible with tir_methodology_report.py)")
    var traceOut: String

    @Flag(name: .long, help: "Oracle mode: let sim Loop see future doses in its prediction dose window (legacy backward-compat default behavior). Causes sim Loop to forecast based on insulin it hasn't 'delivered yet' — produces dramatically over-suspended decisions. Default OFF — clean real-time replay.")
    var oracleFutureInputs: Bool = false

    @Flag(name: .long, help: "Counterfactual sim mode: candidate's recommendations REPLACE real-pump deliveries (not just add as marginal delta vs sim Loop alone). Required for evaluating candidates that fundamentally diverge from real Loop's dosing. Loop's prediction sees only candidate's accumulated deliveries (warm-up-seeded with real pump for the DIA preceding sim start so initial IOB matches reality).")
    var candidateCounterfactual: Bool = false

    @Flag(name: .long, help: "Decision-time replay (NOT a closed loop): both arms see the IDENTICAL real glucose/insulin/carb history at every step and emit a dose recommendation WITHOUT acting. For same-input Loop-vs-oref dose & forecast comparison against the insulin-hole oracle. Neither arm's recommendation feeds back. With candidate == Loop, baselineDose must equal candidateDose at every step (fairness identity check). Do not combine with --candidate-counterfactual or --candidate-infer-sensitivity.")
    var decisionTimeReplay: Bool = false

    @Option(name: .long, help: "Counterfactual burn-in hours (default 6.0): real-pump deliveries drive the sim for this period before counterfactual divergence starts. Gives candidate's prediction a fully-realistic recent dose history at the moment CF mode activates.")
    var candidateCounterfactualBurnInHours: Double = 6.0

    @Flag(name: .long, help: "No user boluses: do NOT pass through user-initiated manual boluses (post burn-in). The sim's Loop owns ALL dosing, covering meals only via its own COB-driven auto-bolusing. Tests how the fully-automated system performs with no user intervention.")
    var noUserBoluses: Bool = false

    @Flag(name: .long, help: "Unannounced meals: hide carb entries from BOTH baseline and candidate forecasts (no COB), so Loop can only react to the BG rise. The meal's BG-raising effect REMAINS in the ICE/counter (it's the real trace, not subtracted), so the meal still happens — Loop just doesn't know about it. Use with --no-user-boluses for a true fully-unannounced, fully-automated test.")
    var noCarbEntries: Bool = false

    @Option(name: .long, help: "Counter-regulation onset (mg/dL). When the counterfactual BG falls below this, model the body's defensive hepatic glucose output as a positive BG velocity that ramps with depth below onset (capped). Prevents the counter running to unphysical negatives. 0 = off (default). ~65 is a reasonable physiological onset.")
    var counterRegOnset: Double = 0

    @Option(name: .long, help: "Counter-regulation gain (mg/dL/min per mg/dL below onset). Default 0.2.")
    var counterRegGain: Double = 0.2

    @Option(name: .long, help: "Counter-regulation max rate (mg/dL/min), the saturating defense ceiling. Default 6.0.")
    var counterRegMax: Double = 6.0

    @Option(name: .long, help: "Positive momentum velocity cap (mg/dL/min). LoopAlgorithm default is 4 mg/dL/min, which limits rising-BG momentum extrapolation. Real-deployed Loop in this user's case had NO cap; pass a high value (e.g., 100) to effectively disable.")
    var candidateMomentumCap: Double?

    @Option(name: .long, help: "Per-step ISF multiplier CSV: (time, isf_multiplier) pairs. At each sim step, scales ISF by the value from the CSV nearest to step time (default 1.0 = no change). Use values >1 to make Loop see ISF as higher (less BG drop per U → recommends less dose, DAMP direction). Use <1 to make Loop see ISF as lower (more dose, BOOST direction). Steps with no matching CSV row are unchanged.")
    var candidateIsfCsv: String?

    @Option(name: .long, help: "Time-matching tolerance for --candidate-isf-csv (seconds, default 150 = ±2.5min)")
    var candidateIsfCsvToleranceSec: Double = 150.0

    @Option(name: .long, help: "Lows-protection gate for the ISF BOOST (mult<1 from --candidate-isf-csv). At each step, a boost is applied ONLY if the candidate's UNBOOSTED forecast PEAK (highest BG expected over the horizon = real headroom) exceeds this mg/dL threshold. Fires when BG is high or climbing (incl. unannounced-meal rises); suppresses the comfortable-and-falling case so the boost can't float into a developing low. The DAMP direction (mult>=1) is always kept. Unset = no gate.")
    var candidateIsfBoostGateEventual: Double?

    @Option(name: .long, help: "Intraday ICE veto on the ISF BOOST (mult<1). Suppress the boost when the recent (last 30min) insulin-counteraction-effect RATE is below this magnitude (mg/dL/min) — i.e. non-insulin drivers are currently pulling BG down (a sensitive moment, ICE<0 ⟺ high local-ISF), so adding insulin would float into a developing drop. Takes precedence over the forecast gate. DAMP (mult>=1) always kept. e.g. 0.5 = veto boost when ICE rate < -0.5 mg/dL/min.")
    var candidateIsfBoostVetoIce: Double?

    @Flag(name: .long, help: "Apply candidate ISF boost (multiplier and/or per-step CSV) ONLY to the active-insulin term: dose-recommendation sizing and the positive-net-units glucose-effect. The EGP-credit term (negative netBasalUnits — implicit endogenous glucose production from suspending below schedule) continues to use the unmodulated scheduled ISF via Phase-1's scheduleBaselineSensitivity parameter. Default OFF preserves the legacy conflated behavior so pre-Phase-1 results stay reproducible.")
    var candidateIsfBoostActiveOnly: Bool = false

    @Option(name: .long, help: "Path to an outage CSV (start,end,reason,source,notes) describing windows where the physical pump could not deliver insulin (pod failure, occlusion, manual disconnect). During each outage the sim clamps both candidate and baseline absolute delivery to 0 so counter_BG isn't contaminated by phantom basal. Generate with `analysis/case-study` tooling: `python -m loopeval_analysis.outage from-nightscout ...`")
    var outagesCsv: String?

    @Option(name: .long, help: "Asymmetric IRC: gain scale on the retrospective correction when BG is dropping faster than predicted (negative discrepancy = sensitivity). >1 responds more strongly/faster to drops (lows-protective). Only used with --candidate-integral-rc. Default 1.0 (symmetric).")
    var candidateIrcDropScale: Double = 1.0
    @Option(name: .long, help: "Asymmetric IRC: gain scale when BG is rising faster than predicted (positive discrepancy = resistance). <1 responds more weakly/slower to rises. Only used with --candidate-integral-rc. Default 1.0 (symmetric).")
    var candidateIrcRiseScale: Double = 1.0
    @Option(name: .long, help: "IRC low-memory carry ('remember the low'): when >0 and the current discrepancy run is positive (a rebound), the integral carries the immediately-preceding negative (low) run across the sign flip instead of resetting, scaled by this factor, so the low's memory offsets the rebound's upward dosing. One-sided (only +run carries a preceding -run). Only used with --candidate-integral-rc. Default 0 (off).")
    var candidateIrcLowMemoryScale: Double = 0.0
    @Option(name: .long, help: "Asymmetric IRC persistence ('remember the low longer'): scales how long a NEGATIVE-discrepancy (sensitivity) correction lingers in the forecast. >1 = turns off slowly / persists. Only used with --candidate-integral-rc. Default 1.0.")
    var candidateIrcDropDurationScale: Double = 1.0
    @Option(name: .long, help: "Asymmetric IRC persistence: scales how long a POSITIVE-discrepancy (resistance) correction lingers. <1 = turns off fast. Only used with --candidate-integral-rc. Default 1.0.")
    var candidateIrcRiseDurationScale: Double = 1.0
    @Option(name: .long, help: "Cross-cycle sensitive-mode time constant (MINUTES): an EWMA of recent NEGATIVE discrepancies decays at this tau and raises effective ISF on future cycles to prevent a delayed SECOND low. 0 = off. Try 60-360.")
    var candidateSensitiveModeTauMin: Double = 0
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
    @Flag(name: .long, help: "Soft low-gate: replace Loop's hard 'predicted-min < range-floor -> zero auto-bolus' cliff with a graded ramp from the suspend threshold up to the range floor (bolus scaled by how far the predicted minimum sits between them). GBAF's low-BG factor still applies on top.")
    var candidateSoftLowGate: Bool = false

    @Option(name: .long, help: "Predicted-min gate threshold (mg/dL): the predicted-minimum BG below which the auto-bolus is gated off. Default (unset) = the correction-range floor (standard Loop). Set lower (e.g. 80) to KEEP the full application factor for predicted minimums down to that value before gating — 'continue the application factor down to <value>'. A small step toward the uncertainty cap (which disables the gate entirely). Composes with --candidate-soft-low-gate (ramp below the threshold) and is overridden by --candidate-uncertainty-cap.")
    var candidateLowGateThreshold: Double?

    @Flag(name: .long, inversion: .prefixedNo, help: "IOB-aware manual-bolus passthrough (DEFAULT ON — a simulation-veracity correction, not an algorithm change). Resize each real user bolus by the IOB difference between the counterfactual and reality: a real bolus of x U delivered at real IOB y becomes x-(z-y) (clamped to [0,maxBolus]) where z is the candidate's IOB at that moment — if the candidate already carries more IOB, the user would have bolused less (Loop's calc subtracts IOB), and vice versa. Pass --no-candidate-iob-adjust-manual-boluses to disable (verbatim passthrough, the old behavior).")
    var candidateIobAdjustManualBoluses: Bool = true
    @Flag(name: .long, help: "Manual-bolus mode: REPLACE each real user manual bolus with the candidate algorithm's OWN recommended manual bolus at that step (full correction vs the candidate's forecast/IOB/COB, clamped to maxBolus). Self-consistent with the candidate state, so it avoids the IOB-divergence amplification of the IOB-aware x-(z-y) resize. Takes precedence over --candidate-iob-adjust-manual-boluses.")
    var candidateManualBolusFromRecommendation: Bool = false
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
    @Flag(name: .long, help: "Export the full baseline forecast curve per step (sim Loop on real BG) into the trace, for point-by-point comparison against field devicestatus predicted.values.")
    var exportForecastCurve: Bool = false
    @Option(name: .long, help: "Auto-bolus application factor for BOTH arms (baseline + candidate inherit unless --candidate-application-factor is set) — fraction of recommended correction applied per cycle. Property of the real Loop deployment. Loop default 0.4 (the auto-bolus is floored to the pump increment AFTER this, matching real devicestatus).")
    var applicationFactor: Double = 0.4
    @Option(name: .long, help: "Candidate flat (global) auto-bolus application factor — overrides --application-factor for the candidate arm only. Negative = inherit --application-factor. Only used when GBAF is off.")
    var candidateApplicationFactor: Double = -1
    @Option(name: .long, help: "Pump bolus increment (U): round the auto-bolus to this grid (real Loop delivers on the pump's increment, e.g. Omnipod 0.05U, and drops sub-increment doses). 0 = no rounding (legacy continuous micro-dosing). Default 0.05.")
    var candidateBolusIncrement: Double = 0.05
    @Option(name: .long, help: "Pump temp-basal-rate increment (U/hr): round temp basal to this grid. 0 = none. Default 0.05.")
    var candidateTempBasalIncrement: Double = 0.05
    @Option(name: .long, help: "Diagnostic: cap every candidate carb entry's absorptionTime to at most this many MINUTES (0 = no cap). Shorter time raises the modeled carb-absorption-rate ceiling, absorbing fast rises into carbs instead of RC.")
    var candidateCarbAbsorptionCapMin: Double = 0
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
    @Option(name: .long, help: "Hours of glucose history fed to the controller each step. Default 10. oref's autosens wants ~24h — raise to 24 for a representative OpenAPS autosens (Loop only uses recent glucose for momentum/RC, so it's ~insensitive).")
    var glucoseLookbackHours: Double = 10.0
    @Option(name: .long, help: "Dump per-step NIE (de-insulinized real BG change = realBGdelta − m·real_physical_insulin) + m + substrate BG to this CSV (requires --candidate-infer-sensitivity). Feeds the offline perfect-foresight dosing oracle.")
    var candidateDumpNieCsv: String? = nil

    @Flag(name: .long, help: "Candidate engine = OpenAPS (oref0-Swift) instead of Loop. Baseline always stays Loop. Lets you compare 'how would OpenAPS dose on this data?' against Loop's behavior on the same trace. Most Loop-specific candidate flags (asym momentum, IRC, ISF boost, etc.) are ignored on the OpenAPS leg.")
    var candidateOpenaps: Bool = false

    @Flag(name: .long, help: "DIAGNOSTIC: candidate engine = Loop's recommendation re-routed through the OpenAPSAdapter dose-translation path. If the resulting counter trace matches a plain Loop CF run, the OpenAPS translation is sound and any Loop-vs-OpenAPS divergence is genuine algorithm differences, not framework artifacts.")
    var candidateLoopMimicOaps: Bool = false

    @Option(name: .long, help: "Sensor cap on glucose reported to the controller (mg/dL). Real CGMs (Dexcom G6/G7, Libre) peg at ~400 — the algorithm never sees BG above this. Counter trajectory + outcome scoring use uncapped values. Default 400 (Dexcom-realistic). Pass 0 to disable.")
    var sensorCapMgdl: Double = 400.0

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

    @Flag(name: .long, help: "OpenAPS ablation: disable UAM (enableUAM=false) — drop the unannounced-meal forecast/SMB while keeping SMB on the base forecast. Isolates UAM's forecast contribution.")
    var candidateOapsNoUam: Bool = false
    @Flag(name: .long, help: "OpenAPS ablation: disable all SMB (temp-basal-only delivery). Isolates the SMB delivery cadence from the forecast.")
    var candidateOapsNoSmb: Bool = false

    @Option(name: .long, help: "CGM stale-data guard (minutes). Loop refuses to issue a new dose when the latest glucose is older than its inputDataRecencyInterval (15min). The sim's per-step dose path bypasses that guard, so set this to 15 to apply it: at any step where the latest CGM sample is older than N minutes, the sim makes NO dose adjustment (candidate and baseline keep delivering scheduled basal — unlike a pump outage, basal still flows during a CGM gap). 0 = disabled (legacy behavior; dose on stale data). Single missed samples (~10min) stay under 15min and are 'paved over'; 2+ missed samples cross the threshold and are treated as a gap.")
    var cgmStaleGuardMin: Double = 0

    mutating func run() async throws {
        let startDate = try parseISO8601Date(start)
        let endDate = try parseISO8601Date(end)
        guard endDate > startDate else { throw ValidationError("--end must be after --start") }
        let interval = DateInterval(start: startDate, end: endDate)
        let resolvedTz: TimeZone = localTimezone.flatMap { TimeZone(identifier: $0) } ?? .current

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
        let baselineConfig = EvalConfig(
            applicationFactor: applicationFactor,
            exportForecastCurve: exportForecastCurve,
            evalStep: TimeInterval(stepMinutes) * 60,
            includeFutureInsulin: oracleFutureInputs,
            includeFutureCarbs: oracleFutureInputs,
            glucoseLookbackHours: glucoseLookbackHours,
            useIntegralRC: integralRC,
            bolusIncrement: candidateBolusIncrement,
            tempBasalIncrement: candidateTempBasalIncrement,
            kalmanSmoothing: !noKalman,
            simRawGlucose: simRawGlucose,
            sensitivityMultiplier: sensitivityMultiplier,
            localTimezone: resolvedTz,
            useAsymmetricMomentum: asymmetricMomentum
        )

        let crHalfWidth: Double = (candidateTargetWidth ?? 0) / 2
        let crOverrideLow: Double? = candidateTargetMid.map { $0 - crHalfWidth }
        let crOverrideHigh: Double? = candidateTargetMid.map { $0 + crHalfWidth }
        let candidateConfig = EvalConfig(
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
            sensDampWindowMin: candidateSensDampWindow,
            sensDampThresholdRate: candidateSensDampThreshold,
            sensDampGain: candidateSensDampGain,
            sensDampMax: candidateSensDampMax,
            evalStep: TimeInterval(stepMinutes) * 60,
            includeFutureInsulin: oracleFutureInputs,
            includeFutureCarbs: oracleFutureInputs,
            glucoseLookbackHours: glucoseLookbackHours,
            useIntegralRC: candidateIntegralRC || integralRC,
            ircDropGainScale: candidateIrcDropScale,
            ircRiseGainScale: candidateIrcRiseScale,
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
            correctionRangeOverrideLow: crOverrideLow,
            correctionRangeOverrideHigh: crOverrideHigh,
            kalmanSmoothing: !noKalman,
            simRawGlucose: simRawGlucose,
            clipInProgressTempBasal: candidateClipInProgressTempBasal,
            carbAbsorptionTimeCapSec: candidateCarbAbsorptionCapMin * 60,
            sensitivityMultiplier: candidateSensitivityMultiplier ?? sensitivityMultiplier,
            sensitivityHourlyMultipliers: hourlyISF,
            localTimezone: resolvedTz,
            positiveVelocityCap: candidateMomentumCap,
            useAsymmetricMomentum: candidateAsymmetricMomentum || asymmetricMomentum,
            momentumAlphaSlow: candidateMomentumAlphaSlow,
            momentumAlphaFast: candidateMomentumAlphaFast
        )

        let dataSource: any EvalDataSource
        if let dataDir {
            dataSource = JSONFileDataSource(baseURL: URL(fileURLWithPath: dataDir))
        } else {
            guard !nightscoutUrl.isEmpty, let baseURL = URL(string: nightscoutUrl) else {
                throw ValidationError("Provide --nightscout-url or --data-dir")
            }
            let client = NightscoutClient(baseURL: baseURL, apiSecret: apiSecret)
            let cache = try DataCache(cacheDir: cacheDir)
            dataSource = NightscoutEvalDataSource(client: client, cache: cache, insulinType: baselinePreset)
        }
        let engine = EvaluationEngine(dataSource: dataSource)

        printStderr("Fetching data... ")
        let data = try await engine.prefetchData(for: interval, config: baselineConfig)
        printStderr("done\n")

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

        let outages: [Outage]
        if let csv = outagesCsv {
            outages = try OutageCSV.load(from: csv)
            printStderr("Loaded \(outages.count) outage(s) from \(csv)\n")
            let totalMin = outages.reduce(0.0) { $0 + $1.interval.duration / 60 }
            printStderr("  total outage time: \(String(format: "%.0f", totalMin)) min "
                        + "(\(String(format: "%.2f", totalMin / (interval.duration / 60) * 100))% of window)\n")
        } else {
            outages = []
        }

        printStderr("Running closed-loop simulation (sequential, ~10× slower than bench)...\n")
        let simResult = try await engine.simulateClosedLoop(
            data: data,
            interval: interval,
            baselineConfig: baselineConfig,
            candidateConfig: candidateConfig,
            baselineLabel: baselineLabel,
            candidateLabel: candidateLabel,
            isfMultiplierByStep: isfMultMap,
            isfBoostActiveOnly: candidateIsfBoostActiveOnly,
            egpPhysicalDecomposition: candidateEgpPhysical,
            isfBoostGateEventualMgdl: candidateIsfBoostGateEventual,
            isfBoostVetoIceRate: candidateIsfBoostVetoIce,
            outages: outages,
            cgmStaleGuardSec: cgmStaleGuardMin * 60,
            counterfactualMode: candidateCounterfactual,
            decisionTimeReplay: decisionTimeReplay,
            counterfactualBurnInSec: candidateCounterfactualBurnInHours * 3600,
            excludeManualBoluses: noUserBoluses,
            suppressCarbs: noCarbEntries,
            counterRegOnsetMgdl: counterRegOnset,
            counterRegGain: counterRegGain,
            counterRegMaxRate: counterRegMax,
            inferSensitivity: candidateInferSensitivity,
            inferSensitivityMax: candidateInferSensitivityMax,
            inferSensitivityWindowSec: candidateInferSensitivityWindowMin * 60,
            inferSensitivitySmoothSec: candidateInferSensitivitySmoothMin * 60,
            inferSensitivitySmoothPrior: candidateInferSensitivitySmoothPrior,
            dumpNiePath: candidateDumpNieCsv,
            useOpenAPSForCandidate: candidateOpenaps,
            useLoopMimicForCandidate: candidateLoopMimicOaps,
            sensorCapMgdl: sensorCapMgdl,
            progress: Self.makeProgressReporter()
        )
        printStderr("Progress: 100%\n")

        // Emit trace JSON in the same shape as bench --trace-out so the
        // existing python report script can consume it. Add a `closedLoop`
        // flag in the JSON so consumers can distinguish.
        try Self.writeTrace(
            simResult: simResult,
            data: data,
            to: URL(fileURLWithPath: traceOut)
        )
        printStderr("Closed-loop trace → \(traceOut)\n")
    }

    static func writeTrace(
        simResult: ClosedLoopSimResult,
        data: PreloadedData,
        to url: URL
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
            let baselinePredCurve: [Double]?       // full baseline forecast curve (mg/dL, 5-min spaced from t); nil unless --export-forecast-curve
        }
        struct ActualSample: Codable { let t: String; let bg: Double }
        struct CounterSample: Codable { let t: String; let bg: Double }
        struct CurvePoint: Codable { let tMin: Double; let percentRemaining: Double; let percentDelivered: Double }
        struct Trace: Codable {
            let baselineLabel: String
            let candidateLabel: String
            let intervalStart: String
            let intervalEnd: String
            let activityDurationMinutes: Double
            let predictions: [Pred]
            let actual: [ActualSample]
            let counter: [CounterSample]   // closed-loop trajectory (NEW)
            let insulinActivityCurve: [CurvePoint]
            let closedLoop: Bool
        }

        let preds = simResult.steps.map {
            Pred(t: formatter.string(from: $0.t),
                 baselineDose: $0.baselineDose,
                 candidateDose: $0.candidateDose,
                 deltaDose: $0.deltaDose,
                 isf: $0.isf,
                 candidateBolus: $0.candidateBolus,
                 candidateTempRate: $0.candidateTempRate,
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
                 baselinePredCurve: $0.baselinePredCurve.isEmpty ? nil : $0.baselinePredCurve)
        }
        let actualOut = data.glucose.sorted { $0.startDate < $1.startDate }.map {
            ActualSample(t: formatter.string(from: $0.startDate),
                         bg: $0.quantity.doubleValue(for: mgdlUnit))
        }
        let counterOut = simResult.steps.map {
            CounterSample(t: formatter.string(from: $0.t), bg: $0.counterBG)
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

        let trace = Trace(
            baselineLabel: simResult.baselineLabel,
            candidateLabel: simResult.candidateLabel,
            intervalStart: formatter.string(from: simResult.intervalStart),
            intervalEnd: formatter.string(from: simResult.intervalEnd),
            activityDurationMinutes: dur / 60.0,
            predictions: preds,
            actual: actualOut,
            counter: counterOut,
            insulinActivityCurve: curve,
            closedLoop: true
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
