// OpenAPSAdapter.swift — DosingEngine backed by the OpenAPSSwift package.
//
// Translates an `EngineStepRequest` (Loop-flavored: PredictionInput,
// TherapySettings, EvalCarbEntry, EvalInsulinDose) into the JSON shapes
// the oref0 pipeline expects, runs the 5-stage pipeline
// (makeProfile → meal → autosense → iob → determineBasal), and maps the
// resulting Determination back to an `EngineStepResult`.
//
// V1 caveats:
//
// - The 24h-cyclic basal / ISF / carb-ratio / target schedules are
//   reconstructed from the slice's `AbsoluteScheduleValue` entries by
//   grouping their start-of-entry by time-of-day in the local timezone.
//   The reconstruction is exact when the underlying schedule didn't change
//   inside the lookback window.
//
// - `Preferences` are stock oref defaults except for `max_iob` (set from
//   therapy.maxBolus × 3 — a conservative cap that lets oref dose; the
//   default of 0 would otherwise gate every recommendation off).
//
// - The synthesized `LoopPrediction` carries `eventualBG`, `activeInsulin`,
//   and `activeCarbs` from the Determination, and a 1-point glucose
//   trajectory ending at the Determination's `eventualBG`. The Loop-only
//   diagnostic fields (momentum / RC effects) come back as empty arrays —
//   downstream consumers handle empty gracefully (net = 0).

import Foundation
import LoopAlgorithm
import OpenAPSSwift

struct OpenAPSAdapter: DosingEngine {
    func step(_ req: EngineStepRequest) -> EngineStepResult {
        do {
            let inputs = try buildInputs(req: req)
            // NS temp targets the user had ALREADY set by decision time t (oref
            // temptargets). Empty ("[]") when none — the prior hardcoded behavior.
            let tempTargetsJSON = orefTempTargetsJSON(req: req)

            // LEGACY path (OAPS_LEGACY env set): 5 separate JSON-bridged calls that
            // re-parse profile/pumpHistory/glucose each call. Kept only for the
            // bit-identity A/B check against the combined runPipeline below.
            if ProcessInfo.processInfo.environment["OAPS_LEGACY"] != nil {
                let profile = try OpenAPSSwift.makeProfile(
                    preferences: inputs.preferences, pumpSettings: inputs.pumpSettings,
                    bgTargets: inputs.bgTargets, basalProfile: inputs.basalProfile,
                    isf: inputs.isf, carbRatio: inputs.carbRatio, tempTargets: tempTargetsJSON,
                    model: "\"X22\"", trioSettings: "{}", clock: req.t).returnOrThrow()
                let clockStr = inputs.clockString
                let meal = try OpenAPSSwift.meal(
                    pumphistory: inputs.pumpHistory, profile: profile,
                    basalProfile: inputs.basalProfile, clock: clockStr,
                    carbs: inputs.carbs, glucose: inputs.glucose).returnOrThrow()
                let autosens = try OpenAPSSwift.autosense(
                    glucose: inputs.glucose, pumpHistory: inputs.pumpHistory,
                    basalProfile: inputs.basalProfile, profile: profile,
                    carbs: inputs.carbs, tempTargets: tempTargetsJSON, clock: clockStr).returnOrThrow()
                let iob = try OpenAPSSwift.iob(
                    pumphistory: inputs.pumpHistory, profile: profile,
                    clock: clockStr, autosens: autosens).returnOrThrow()
                let det = try OpenAPSSwift.determineBasal(
                    glucose: inputs.glucose, currentTemp: inputs.currentTemp, iob: iob,
                    profile: profile, autosens: autosens, meal: meal,
                    microBolusAllowed: true, reservoir: "100",
                    pumpHistory: inputs.pumpHistory, preferences: inputs.preferences,
                    basalProfile: inputs.basalProfile, trioCustomOrefVariables: inputs.trioCustomOref,
                    clock: req.t).returnOrThrow()
                return try mapDetermination(det, req: req, scheduledBasalUhr: inputs.scheduledBasalUhr)
            }

            // FAST PATH (default): one combined pipeline — parse each raw input once,
            // pass structs between generators (no intermediate JSON). Same generators,
            // same order → mathematically identical to the legacy 5-call sequence.
            let pipe = try OpenAPSSwift.runPipeline(
                preferences: inputs.preferences, pumpSettings: inputs.pumpSettings,
                bgTargets: inputs.bgTargets, basalProfile: inputs.basalProfile,
                isf: inputs.isf, carbRatio: inputs.carbRatio,
                model: "\"X22\"", trioSettings: "{}",
                pumpHistory: inputs.pumpHistory, carbs: inputs.carbs, glucose: inputs.glucose,
                currentTemp: inputs.currentTemp, reservoir: "100", microBolusAllowed: true,
                trioCustomOrefVariables: inputs.trioCustomOref,
                clockDate: req.t, clockJSON: inputs.clockString,
                tempTargets: tempTargetsJSON)

            let comps = Calendar(identifier: .gregorian).dateComponents([.hour, .minute], from: req.t)
            if (comps.hour ?? 0) % 6 == 0 && (comps.minute ?? 0) < 5 {
                FileHandle.standardError.write(Data("autosens \(req.t) ratio=\(String(format: "%.3f", pipe.autosensRatio))\n".utf8))
            }
            return try mapDetermination(pipe.determination, req: req, scheduledBasalUhr: inputs.scheduledBasalUhr)
        } catch {
            FileHandle.standardError.write(Data("OpenAPSAdapter error at \(req.t): \(error)\n".utf8))
            return fallbackResult(req: req, scheduledBasalUhr: activeBasal(at: req.t, req: req))
        }
    }

    // Build the oref `temptargets` JSON from the therapy timeline, gated to the
    // temp targets the user had already SET by decision time `t` (start <= t) so a
    // future temp target can't leak into an earlier decision. oref's makeProfile /
    // autosens pick the one active at the clock (and honor durations / cancels).
    private func orefTempTargetsJSON(req: EngineStepRequest) -> String {
        let active = req.therapy.orefTempTargets.filter { $0.start <= req.t }
        guard !active.isEmpty else { return "[]" }
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let items = active.enumerated().map { (i, tt) -> String in
            let ts = iso.string(from: tt.start)
            let tgt = Int(tt.targetMgdl.rounded())
            let dur = Int(tt.durationMin.rounded())
            // `_id` is a required key on the oref TempTarget decoder; synthesize a
            // stable one (start+index) — its value is irrelevant to dosing.
            let id = "tt\(Int(tt.start.timeIntervalSince1970))_\(i)"
            return "{\"_id\":\"\(id)\",\"created_at\":\"\(ts)\",\"targetTop\":\(tgt),\"targetBottom\":\(tgt),\"duration\":\(dur)}"
        }
        return "[" + items.joined(separator: ",") + "]"
    }

    // MARK: – Input translation

    private struct InputBundle {
        let preferences: String
        let pumpSettings: String
        let bgTargets: String
        let basalProfile: String
        let isf: String
        let carbRatio: String
        let glucose: String
        let pumpHistory: String
        let carbs: String
        let currentTemp: String
        let trioCustomOref: String
        let clockString: String
        let scheduledBasalUhr: Double
    }

    private func buildInputs(req: EngineStepRequest) throws -> InputBundle {
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        // Schedules (basal/ISF/CR/target) are DEFINED in the profile's timezone;
        // regroup them by time-of-day in THAT zone, not the host/sim zone, or a
        // user whose profile TZ ≠ host gets shifted schedules (Berlin profile on a
        // US host → mangled basal → wrong net-basal IOB). Fall back to the sim's
        // localTimezone only when the timeline doesn't carry a profile TZ (legacy).
        let tz = req.therapy.scheduleTimeZone ?? req.config.localTimezone
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = tz

        let scheduledBasalUhr = activeBasal(at: req.t, req: req)

        // ── Preferences ────────────────────────────────────────────────────────
        // max_iob: stock default is 0, which gates dosing off. Set to a high
        // multiple of maxBolus so it almost never binds — we want to compare
        // algorithm BEHAVIOR, not the max_iob safety cap. (Was previously
        // maxBolus * 3, which bound earlier than Loop's auto-bolus cap on
        // recovery-from-outage events for user2 — see 2026-06-06 notes.)
        // enableSMBAlways / enableUAM / enableSMBWithCOB / enableSMBAfterCarbs:
        //   enable Super-Micro-Boluses so oref has a fast-correction tool
        //   comparable to Loop's auto-bolus dosing strategy. Without these the
        //   first comparison showed oref capped at temp basal 2.8 U/hr while
        //   Loop dumped 0.6-0.8 U auto-boluses on the same meal trace (see
        //   runs/2026-06-05-openaps-first-run/case_study_noon_meal.html).
        // maxSMBBasalMinutes / maxUAMSMBBasalMinutes: stock 30 (≈ 30 min of
        //   scheduled basal per SMB). Kept at default to start.
        // FAITHFUL safety limits: use the user's REAL pump caps and oref STOCK
        // safety multipliers so temp basal is bounded exactly as on the device.
        // (Earlier these were inflated — max_basal×3, multipliers 10 — to "measure
        // algorithm behavior, not the safety ceiling"; that double-doses vs a real
        // oref user, which delivers via SMB and lets the temp cap bind. max_iob is
        // genuinely per-user and not uploaded by Trio → supply via --candidate-oaps-
        // max-iob; the non-binding maxBolus×10 fallback is NOT faithful.)
        let maxIob = req.config.oapsMaxIob ?? (req.therapy.maxBolus * 10.0)
        var prefs: [String: Any] = [
            "max_iob": maxIob,
            "max_basal": req.therapy.maxBasalRate,
            // Keys match Preferences.CodingKeys exactly — see
            // OpenAPSSwift/TrioModels/Preferences.swift
            "enableSMB_always": true,
            "enableSMB_with_COB": true,
            "enableSMB_after_carbs": true,
            "enableUAM": true,
            "allowSMB_with_high_temptarget": true,
            // maxSMBBasalMinutes: the field runs a high value (its SMBs require
            // ≥~68 min of basal); keep 60 (override via --candidate-oaps-max-smb-min).
            "maxSMBBasalMinutes": 60,
            "maxUAMSMBBasalMinutes": 60,
            // oref STOCK safety multipliers (were 10/10).
            "max_daily_safety_multiplier": 3,
            "current_basal_safety_multiplier": 4
        ]
        // Optional per-experiment overrides.
        if let thr = req.config.oapsThresholdSetting {
            prefs["threshold_setting"] = thr
        }
        if let ratio = req.config.oapsSmbDeliveryRatio {
            prefs["smb_delivery_ratio"] = ratio
        }
        if let mins = req.config.oapsMaxSmbBasalMinutes {
            prefs["maxSMBBasalMinutes"] = mins
            prefs["maxUAMSMBBasalMinutes"] = mins
        }
        if let unf = req.config.oapsUseNewFormula {
            prefs["useNewFormula"] = unf
        }
        if let sig = req.config.oapsSigmoid {
            prefs["sigmoid"] = sig
        }
        // Ablations (mechanism isolation). UAM-off: drop only the UAM forecast/SMB on
        // unannounced rises (SMB_always still fires on the base forecast). SMB-off: disable all
        // SMB → temp-basal-only delivery.
        if req.config.oapsEnableUAM == false {
            prefs["enableUAM"] = false
        }
        if req.config.oapsEnableSMB == false {
            prefs["enableSMB_always"]     = false
            prefs["enableSMB_with_COB"]   = false
            prefs["enableSMB_after_carbs"] = false
            prefs["enableUAM"]            = false
        }
        if let af = req.config.oapsAdjustmentFactor {
            prefs["adjustmentFactor"] = af
        }
        // Sensitivity-ratio clamps (autosens and/or Dynamic ISF). Load-bearing for
        // matching a user who runs a non-stock Dynamic limit (e.g. autosens_max 1.9).
        if let am = req.config.oapsAutosensMax {
            prefs["autosens_max"] = am
        }
        if let an = req.config.oapsAutosensMin {
            prefs["autosens_min"] = an
        }
        // Insulin peak time → drives both the IOB curve and Dynamic ISF's
        // insulinFactor (= 120 − peak). Use the ultra-rapid curve so oref permits
        // a custom peak below 50 (the rapid-acting curve clamps peak to ≥50, i.e.
        // insulinFactor ≤ 70; ultra-rapid clamps to [35,100]).
        if let peak = req.config.oapsInsulinPeakTime {
            prefs["curve"] = "ultra-rapid"
            prefs["useCustomPeakTime"] = true
            prefs["insulinPeakTime"] = peak
        } else if let curve = req.config.oapsCurve {
            // Preset curve, NO custom peak: oref's ultra-rapid branch sets IOB
            // peak 55 AND dynISF insulinFactor 70 (120−50), decoupling the two —
            // the Lyumjev/Fiasp config (see EvalConfig.oapsCurve).
            prefs["curve"] = curve
        }
        if let afs = req.config.oapsAdjustmentFactorSigmoid {
            prefs["adjustmentFactorSigmoid"] = afs
        }
        // Merge a raw oref-preferences JSON over the defaults/knobs (faithful
        // reproduction: supply a real user's complete Trio settings verbatim).
        if let pj = req.config.oapsPrefsJson,
           let data = pj.data(using: .utf8),
           let merge = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            for (k, v) in merge { prefs[k] = v }
        }
        let preferencesJSON = String(data: try JSONSerialization.data(withJSONObject: prefs),
                                     encoding: .utf8)!

        // ── Pump settings ─────────────────────────────────────────────────────
        // Use the user's REAL maxBasal so the temp-basal cap binds exactly as on
        // the device (was ×3 to avoid binding — not faithful, see prefs above).
        let pumpSettings: [String: Any] = [
            "insulin_action_curve": req.config.oapsDia ?? 6,
            "maxBolus": req.therapy.maxBolus,
            "maxBasal": req.therapy.maxBasalRate
        ]
        let pumpSettingsJSON = String(data: try JSONSerialization.data(withJSONObject: pumpSettings),
                                      encoding: .utf8)!

        // ── 24h-cyclic schedules ──────────────────────────────────────────────
        let basalProfileJSON = encodeBasalSchedule(req.input.basal, calendar: cal)
        let isfJSON          = encodeISFSchedule(req.input.sensitivity, calendar: cal)
        let carbRatioJSON    = encodeCRSchedule(req.input.carbRatio, calendar: cal)
        // Honor the candidate correction-range override (same flag used by the Loop
        // path) so oref can be run at a fixed target/width for fair head-to-heads.
        let targetSchedule: [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>]
        if let lo = req.config.correctionRangeOverrideLow, let hi = req.config.correctionRangeOverrideHigh {
            let s = req.input.target.first?.startDate ?? Date.distantPast
            let e = req.input.target.last?.endDate ?? Date.distantFuture
            targetSchedule = [AbsoluteScheduleValue(startDate: s, endDate: e,
                value: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: lo)...LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: hi))]
        } else {
            targetSchedule = req.input.target
        }
        let bgTargetsJSON    = encodeTargetSchedule(targetSchedule, calendar: cal,
                                                    fallbackMidMgdl: 100)

        // ── Glucose history ───────────────────────────────────────────────────
        let glucoseForOref = req.config.oapsSmoothGlucose
            ? Self.aapsSmoothGlucose(req.input.glucose)
            : req.input.glucose
        let glucoseJSON = encodeGlucose(glucoseForOref, iso: iso)

        // ── Carbs ─────────────────────────────────────────────────────────────
        let carbsJSON = encodeCarbs(req.input.carbs, iso: iso)

        // ── Pump history (boluses + temp basal pairs derived from doses) ──────
        let pumpHistoryJSON = encodePumpHistory(req.input.doses, iso: iso,
                                                scheduledBasalUhr: scheduledBasalUhr)

        // ── Current temp ──────────────────────────────────────────────────────
        // Last temp basal that is still active at `t`, else neutral 0.
        let activeTemp = req.input.doses.last(where: { $0.deliveryType == .basal && $0.endDate >= req.t })
        let currentRate: Double
        let currentDuration: Int
        if let temp = activeTemp {
            let hours = temp.endDate.timeIntervalSince(temp.startDate) / 3600.0
            currentRate = hours > 0 ? temp.volume / hours : 0
            currentDuration = max(0, Int(temp.endDate.timeIntervalSince(req.t) / 60.0))
        } else {
            currentRate = 0
            currentDuration = 0
        }
        let currentTemp: [String: Any] = [
            "duration": currentDuration,
            "rate": currentRate,
            "temp": "absolute",
            "timestamp": iso.string(from: req.t)
        ]
        let currentTempJSON = String(data: try JSONSerialization.data(withJSONObject: currentTemp),
                                     encoding: .utf8)!

        // ── TDD computation (needed for Dynamic ISF) ──────────────────────────
        // Dynamic ISF gates on `tdd > 0` (DynamicISF.swift:38). The TDD is
        // total daily insulin = sum of all delivery (basal + bolus) over the
        // last 24h. We approximate from req.input.doses (sliced to insulin
        // lookback, typically 16h) by extrapolating to 24h. For dose volumes:
        //   - .bolus: dose.volume is the full bolus
        //   - .basal: dose.volume is delivery over [startDate, endDate]
        // We sum what overlaps the (t - 24h, t] window.
        // ── TDD (faithful Trio TDDStorage replication) ───────────────────────
        // The dynISF uses Trio's WEIGHTED average = weightPercentage·past2hoursAverage
        // + (1-weightPercentage)·average_total_data, where each is a MEAN of the
        // per-5min TDD records. Each record (calculateTDD) = the total insulin over
        // the most-recent 288 pump events (getPumpHistory fetchLimit; ~18h for an
        // active SMB user), with each interrupted temp segment FLOORED to the pump
        // pulse grid (roundToSupportedBasalRate). The reason line "TDD: X" DISPLAYS
        // currentTDD but the dynISF USES the weighted average — verified 2026-07-01:
        // with the weighted TDD the field's dynISF insulinFactor is a flat ~75 across
        // all BG, whereas currentTDD drifts (the past2h mean drops at post-meal rises
        // because it lags the currentTDD spike, correctly damping the dynISF).
        let tddSource = req.tddDoses.isEmpty ? req.input.doses : req.tddDoses
        let pulse = req.config.oapsPumpPulse
        let estimatedTdd = max(Self.flooredTdd288(doses: tddSource, asof: req.t, pulse: pulse), 12.0)
        // past2hoursAverage: mean of the per-5min TDD records over the last 2h.
        var p2sum = 0.0
        for i in 0..<24 { p2sum += Self.flooredTdd288(doses: tddSource, asof: req.t.addingTimeInterval(Double(-300 * i)), pulse: pulse) }
        let past2h = max(p2sum / 24.0, 12.0)
        // average_total_data: mean of the TDD records over 10 days. Sampled every 3h
        // (the record is stable enough for this 0.35-weight term; full 5-min sampling
        // would be 2880 evals/cycle).
        var a10sum = 0.0
        for i in 0..<80 { a10sum += Self.flooredTdd288(doses: tddSource, asof: req.t.addingTimeInterval(Double(-10800 * i)), pulse: pulse) }
        let avgTotalData = max(a10sum / 80.0, 12.0)
        // TODO: read weightPercentage from prefs (0.65 = Trio default & this user's).
        let weightPct = 0.65
        let weightedTdd = weightPct * past2h + (1 - weightPct) * avgTotalData

        // ── TrioCustomOrefVariables (overrides off) ───────────────────────────
        let trioCustom: [String: Any] = [
            "average_total_data": avgTotalData,
            "currentTDD": estimatedTdd,
            "weightedAverage": weightedTdd,
            "past2hoursAverage": estimatedTdd / 12.0,  // ~2h share
            "date": iso.string(from: req.t),
            "overridePercentage": 100,
            "useOverride": false,
            "duration": 0,
            "unlimited": false,
            "overrideTarget": 0,
            "smbIsOff": false,
            "advancedSettings": false,
            "isfAndCr": false,
            "isf": false,
            "cr": false,
            "smbIsScheduledOff": false,
            "start": 0,
            "end": 0,
            "smbMinutes": 0,
            "uamMinutes": 0
        ]
        let trioCustomJSON = String(data: try JSONSerialization.data(withJSONObject: trioCustom),
                                    encoding: .utf8)!

        return InputBundle(
            preferences: preferencesJSON,
            pumpSettings: pumpSettingsJSON,
            bgTargets: bgTargetsJSON,
            basalProfile: basalProfileJSON,
            isf: isfJSON,
            carbRatio: carbRatioJSON,
            glucose: glucoseJSON,
            pumpHistory: pumpHistoryJSON,
            carbs: carbsJSON,
            currentTemp: currentTempJSON,
            trioCustomOref: trioCustomJSON,
            clockString: iso.string(from: req.t),
            scheduledBasalUhr: scheduledBasalUhr
        )
    }

    // MARK: – Schedule encoders

    private func minutesFromMidnight(_ date: Date, _ cal: Calendar) -> Int {
        let comps = cal.dateComponents([.hour, .minute], from: date)
        return (comps.hour ?? 0) * 60 + (comps.minute ?? 0)
    }

    private func startString(minutes: Int) -> String {
        let h = minutes / 60
        let m = minutes % 60
        return String(format: "%02d:%02d:00", h, m)
    }

    private func uniqueByTimeOfDay<V: Equatable>(
        _ entries: [AbsoluteScheduleValue<V>],
        valueAt: Date,
        cal: Calendar,
        toValue: (V) -> Double
    ) -> [(minutes: Int, value: Double)] {
        if entries.isEmpty { return [(0, toValue(valueAt as! V))] }
        // Pair (minutesFromMidnight, value). Latest start wins on collision.
        var byMinutes: [Int: (Date, Double)] = [:]
        for e in entries {
            let mins = minutesFromMidnight(e.startDate, cal)
            let v = toValue(e.value)
            if let prev = byMinutes[mins], prev.0 >= e.startDate { continue }
            byMinutes[mins] = (e.startDate, v)
        }
        let sorted = byMinutes.keys.sorted().map { ($0, byMinutes[$0]!.1) }
        return sorted
    }

    /// oref's profile lookups (ISF/CR/basal) require a midnight (offset-0) anchor:
    /// `Isf.isfLookup` returns -1 (→ ProfileError.invalidISF) unless the first
    /// schedule entry has offset 0. A decision-time window rarely starts at local
    /// midnight, so a sliced daily schedule's earliest segment usually has a
    /// nonzero time-of-day offset. Add offset 0 using the wrap-around
    /// (largest-offset) value — the cyclic schedule's value in force at midnight.
    /// No-op when an offset-0 entry already exists.
    private func anchorMidnight(_ byMinutes: inout [Int: (Date, Double)]) {
        if byMinutes[0] == nil, let maxKey = byMinutes.keys.max() {
            byMinutes[0] = (Date.distantPast, byMinutes[maxKey]!.1)
        }
    }

    private func encodeBasalSchedule(
        _ entries: [AbsoluteScheduleValue<Double>],
        calendar cal: Calendar
    ) -> String {
        var byMinutes: [Int: (Date, Double)] = [:]
        for e in entries {
            let mins = minutesFromMidnight(e.startDate, cal)
            if let prev = byMinutes[mins], prev.0 >= e.startDate { continue }
            byMinutes[mins] = (e.startDate, e.value)
        }
        anchorMidnight(&byMinutes)
        let sorted = byMinutes.keys.sorted()
        let items: [[String: Any]] = sorted.isEmpty
            ? [["start": "00:00:00", "minutes": 0, "rate": entries.last?.value ?? 1.0]]
            : sorted.map { mins in
                ["start": startString(minutes: mins), "minutes": mins, "rate": byMinutes[mins]!.1]
            }
        return String(data: try! JSONSerialization.data(withJSONObject: items), encoding: .utf8)!
    }

    private func encodeISFSchedule(
        _ entries: [AbsoluteScheduleValue<LoopQuantity>],
        calendar cal: Calendar
    ) -> String {
        var byMinutes: [Int: (Date, Double)] = [:]
        for e in entries {
            let mins = minutesFromMidnight(e.startDate, cal)
            let v = e.value.doubleValue(for: .milligramsPerDeciliter)
            if let prev = byMinutes[mins], prev.0 >= e.startDate { continue }
            byMinutes[mins] = (e.startDate, v)
        }
        anchorMidnight(&byMinutes)
        let sorted = byMinutes.keys.sorted()
        let items: [[String: Any]] = sorted.isEmpty
            ? [["start": "00:00:00", "offset": 0, "sensitivity": 50.0]]
            : sorted.map { mins in
                ["start": startString(minutes: mins), "offset": mins, "sensitivity": byMinutes[mins]!.1]
            }
        let payload: [String: Any] = [
            "units": "mg/dL",
            "user_preferred_units": "mg/dL",
            "sensitivities": items
        ]
        return String(data: try! JSONSerialization.data(withJSONObject: payload), encoding: .utf8)!
    }

    private func encodeCRSchedule(
        _ entries: [AbsoluteScheduleValue<Double>],
        calendar cal: Calendar
    ) -> String {
        var byMinutes: [Int: (Date, Double)] = [:]
        for e in entries {
            let mins = minutesFromMidnight(e.startDate, cal)
            if let prev = byMinutes[mins], prev.0 >= e.startDate { continue }
            byMinutes[mins] = (e.startDate, e.value)
        }
        anchorMidnight(&byMinutes)
        let sorted = byMinutes.keys.sorted()
        let items: [[String: Any]] = sorted.isEmpty
            ? [["start": "00:00:00", "offset": 0, "ratio": 10.0]]
            : sorted.map { mins in
                ["start": startString(minutes: mins), "offset": mins, "ratio": byMinutes[mins]!.1]
            }
        let payload: [String: Any] = ["units": "grams", "schedule": items]
        return String(data: try! JSONSerialization.data(withJSONObject: payload), encoding: .utf8)!
    }

    private func encodeTargetSchedule(
        _ entries: [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>],
        calendar cal: Calendar,
        fallbackMidMgdl: Double
    ) -> String {
        var byMinutes: [Int: (Date, Double, Double)] = [:]
        for e in entries {
            let mins = minutesFromMidnight(e.startDate, cal)
            let lo = e.value.lowerBound.doubleValue(for: .milligramsPerDeciliter)
            let hi = e.value.upperBound.doubleValue(for: .milligramsPerDeciliter)
            if let prev = byMinutes[mins], prev.0 >= e.startDate { continue }
            byMinutes[mins] = (e.startDate, lo, hi)
        }
        if byMinutes[0] == nil, let maxKey = byMinutes.keys.max() {
            let wrap = byMinutes[maxKey]!
            byMinutes[0] = (Date.distantPast, wrap.1, wrap.2)
        }
        let sorted = byMinutes.keys.sorted()
        let items: [[String: Any]] = sorted.isEmpty
            ? [["low": fallbackMidMgdl, "high": fallbackMidMgdl, "start": "00:00:00", "offset": 0]]
            : sorted.map { mins in
                let (_, lo, hi) = byMinutes[mins]!
                return ["low": lo, "high": hi, "start": startString(minutes: mins), "offset": mins]
            }
        let payload: [String: Any] = [
            "units": "mg/dL",
            "user_preferred_units": "mg/dL",
            "targets": items
        ]
        return String(data: try! JSONSerialization.data(withJSONObject: payload), encoding: .utf8)!
    }

    // MARK: – History encoders

    // Trio's AAPS double-exponential glucose smoothing (FetchGlucoseManager
    // .applyExponentialSmoothingAndStore). oref doses on the smoothed series;
    // NS stores raw. On a fast rise the smoothed value lags below raw → lower
    // deviation → less dose, which is what the field's oref actually did.
    // Params are Trio's: 1st-order exp α0.5, 2nd-order Holt α0.4/β1.0, blend
    // 0.4/0.6, floor 39, contiguous-window (split on ≥12 min gap or a 38 error;
    // segments <4 samples pass through as max(raw,39)).
    // Floor a basal segment's delivery to the pump's pulse increment. Trio's TDD
    // floors each temp-basal segment (roundToSupportedBasalRate); matching it is
    // required to reproduce the field's TDD → dynISF → dosing. `pulse` is the
    // pump increment (Omnipod 0.05; configurable for 0.025/0.1 pumps).
    static func pulseFloor(_ units: Double, pulse: Double) -> Double {
        guard pulse > 0 else { return units }
        return (units / pulse).rounded(.down) * pulse
    }

    /// One Trio TDD record (`TDDStorage.calculateTDD` as of `asof`): total insulin
    /// over the most-recent 288 pump events within the last 24h (`getPumpHistory`
    /// predicate `pumpHistoryLast24h` + `fetchLimit: 288`). bolus = sum of all
    /// bolus amounts (manual included); temp = per interrupted segment (a reconciled
    /// dose = a temp cut at the next temp's start) delivering
    /// `roundToSupportedBasalRate(rate × durationHours)`, which floors to the pump
    /// pulse grid. `doses` must be the reconciled EvalInsulinDoses.
    fileprivate static func flooredTdd288(doses: [EvalInsulinDose], asof: Date, pulse: Double) -> Double {
        let windowStart = asof.addingTimeInterval(-24 * 3600)
        var dd: [(start: Date, amount: Double)] = []
        dd.reserveCapacity(400)
        for d in doses {
            if d.endDate <= windowStart || d.startDate >= asof { continue }
            let amount: Double
            switch d.deliveryType {
            case .bolus:
                amount = d.volume
            case .basal:
                let lo = max(d.startDate, windowStart)
                let hi = min(d.endDate, asof)
                let seg = max(0, hi.timeIntervalSince(lo))
                let full = max(d.endDate.timeIntervalSince(d.startDate), 1)
                amount = pulseFloor(d.volume * seg / full, pulse: pulse)
            }
            dd.append((start: d.startDate, amount: amount))
        }
        return dd.sorted { $0.start > $1.start }.prefix(288).reduce(0.0) { $0 + $1.amount }
    }

    static func aapsSmoothGlucose(_ samples: [EvalGlucoseSample]) -> [EvalGlucoseSample] {
        guard samples.count >= 2 else { return samples }
        let mgdl = LoopUnit.milligramsPerDeciliter
        let sorted = samples.sorted { $0.startDate < $1.startDate }   // chronological
        let raw = sorted.map { $0.quantity.doubleValue(for: mgdl) }
        let dates = sorted.map { $0.startDate }
        var out = raw
        func smoothSegment(_ lo: Int, _ hi: Int) {
            let n = hi - lo + 1
            guard n >= 4 else { for i in lo...hi { out[i] = max(raw[i], 39) }; return }
            // 1st-order exponential (α 0.5)
            var fo = [Double](); fo.reserveCapacity(n)
            var cur = raw[lo]; fo.append(cur)
            for i in (lo+1)...hi { cur += 0.5 * (raw[i] - cur); fo.append(cur) }
            // 2nd-order Holt (α 0.4, β 1.0)
            var so = [raw[lo]]; so.reserveCapacity(n)
            var ps = raw[lo]; var d = raw[lo+1] - raw[lo]
            for i in (lo+1)...hi {
                let ns = 0.4 * raw[i] + 0.6 * (ps + d)
                d = (ns - ps)          // β 1.0
                ps = ns; so.append(ns)
            }
            for k in 0..<n { out[lo+k] = max((0.4 * fo[k] + 0.6 * so[k]).rounded(), 39) }
        }
        var segStart = 0
        for i in 1...sorted.count {
            let brk: Bool
            if i == sorted.count { brk = true }
            else { brk = dates[i].timeIntervalSince(dates[i-1]) / 60 >= 12 || Int(raw[i].rounded()) == 38 }
            if brk { smoothSegment(segStart, i-1); segStart = i }
        }
        return zip(sorted, out).map { s, v in
            EvalGlucoseSample(startDate: s.startDate,
                              quantity: LoopQuantity(unit: mgdl, doubleValue: v),
                              provenanceIdentifier: s.provenanceIdentifier,
                              isDisplayOnly: s.isDisplayOnly, wasUserEntered: s.wasUserEntered)
        }
    }

    private func encodeGlucose(_ samples: [EvalGlucoseSample], iso: ISO8601DateFormatter) -> String {
        let mgdl = LoopUnit.milligramsPerDeciliter
        // oref's convention is glucose NEWEST-FIRST (descending), the order
        // Nightscout feeds real oref. `getGlucoseStatus` sorts defensively, but
        // `MealCob.bucketGlucoseForCob` does NOT — fed oldest-first, its
        // `foundPreMealBG` early-exit trips on the first (oldest) reading and
        // skips the whole series, yielding EMPTY deviations (maxDev=0/minDev=999)
        // → mealCOB=0 and a steep slopeFromDeviations that collapses the UAM/COB
        // forecast. Emit newest-first so the carb-absorption deconvolution runs.
        let entries: [[String: Any]] = samples
            .sorted { $0.startDate > $1.startDate }
            .enumerated().map { i, s in
            let val = Int(s.quantity.doubleValue(for: mgdl).rounded())
            return [
                "_id": "g\(i)",
                "sgv": val,
                "glucose": val,
                "direction": "Flat",
                "date": Int(s.startDate.timeIntervalSince1970 * 1000),
                "dateString": iso.string(from: s.startDate),
                "type": "sgv",
                "noise": 1
            ]
        }
        return String(data: try! JSONSerialization.data(withJSONObject: entries), encoding: .utf8)!
    }

    private func encodeCarbs(_ carbs: [EvalCarbEntry], iso: ISO8601DateFormatter) -> String {
        let entries: [[String: Any]] = carbs.enumerated().map { i, c in
            [
                "_id": "c\(i)",
                "created_at": iso.string(from: c.dosingVisibleDate),  // normal-dosing visibility gate (unchanged by the entryDate rename)
                "actualDate": iso.string(from: c.startDate),
                "carbs": c.quantity.doubleValue(for: .gram),
                "enteredBy": "loopeval"
            ]
        }
        return String(data: try! JSONSerialization.data(withJSONObject: entries), encoding: .utf8)!
    }

    private func encodePumpHistory(
        _ doses: [EvalInsulinDose],
        iso: ISO8601DateFormatter,
        scheduledBasalUhr: Double
    ) -> String {
        var events: [[String: Any]] = []
        events.reserveCapacity(doses.count * 2)
        // PumpHistoryEvent encodes `type` as JSON key "_type" and
        // `durationMin` as "duration (min)" — see PumpHistoryEvent CodingKeys.
        for (i, d) in doses.enumerated() {
            switch d.deliveryType {
            case .bolus:
                events.append([
                    "id": "b\(i)",
                    "_type": "Bolus",
                    "timestamp": iso.string(from: d.startDate),
                    "amount": d.volume
                ])
            case .basal:
                // Emit a TempBasal + TempBasalDuration pair. Rate is volume
                // over the segment hours; duration is the segment length in
                // minutes. Even scheduled basal entries are emitted this way:
                // it's a clean approximation since oref uses the basalProfile
                // for gap-filling between temps, and a temp at exactly the
                // scheduled rate is equivalent to no-temp.
                let seconds = d.endDate.timeIntervalSince(d.startDate)
                let durationMin = max(1, Int(seconds / 60.0))
                let rate = seconds > 0 ? d.volume / (seconds / 3600.0) : scheduledBasalUhr
                events.append([
                    "id": "tb\(i)",
                    "_type": "TempBasal",
                    "timestamp": iso.string(from: d.startDate),
                    "rate": rate,
                    "temp": "absolute"
                ])
                events.append([
                    "id": "tbd\(i)",
                    "_type": "TempBasalDuration",
                    "timestamp": iso.string(from: d.startDate),
                    "duration (min)": durationMin
                ])
            }
        }
        return String(data: try! JSONSerialization.data(withJSONObject: events), encoding: .utf8)!
    }

    // MARK: – Schedule helpers

    // `internal` (not private) so LoopMimicViaOpenAPSAdapter can reuse the
    // exact same schedBasal lookup path for the diagnostic identity test.
    internal func activeBasal(at t: Date, req: EngineStepRequest) -> Double {
        if let entry = req.input.basal.first(where: { $0.startDate <= t && t < $0.endDate }) {
            return entry.value
        }
        return req.input.basal.last?.value ?? 1.0
    }

    // MARK: – Determination decoding

    // `internal` so the LoopMimic diagnostic adapter can call them directly.
    internal struct DeterminationResp: Decodable {
        let rate: Double?
        let duration: Double?
        let units: Double?
        let eventualBG: Double?
        let IOB: Double?
        let COB: Double?
        let reason: String?
        // Withholding diagnostics: minGuardBG/minPredBG are oref's predicted
        // minimum BG; SMB is gated off when minGuardBG < threshold. sensitivityRatio
        // is autosens.
        let minGuardBG: Double?
        let minPredBG: Double?
        let sensitivityRatio: Double?
        /// Present when DeterminationGenerator threw a DeterminationError.
        /// OpenAPSSwift wraps it as `{"error": "..."}` — see OpenAPSSwift.swift:94.
        let error: String?
    }

    internal func mapDetermination(_ json: String, req: EngineStepRequest, scheduledBasalUhr: Double) throws -> EngineStepResult {
        let data = json.data(using: .utf8)!
        let det = try JSONDecoder().decode(DeterminationResp.self, from: data)

        // Surface oref's internal DeterminationError as a real adapter error
        // (otherwise OpenAPSSwift quietly returns `{"error": "..."}` and the
        // adapter decodes that as an all-nil Determination → IOB silently
        // becomes 0, candidate stops dosing, counter runs away).
        if let errMsg = det.error {
            FileHandle.standardError.write(Data(
                "OpenAPSAdapter DeterminationError at \(req.t): \(errMsg)\n".utf8))
            // Use the fallback path so at least we keep the prior trajectory's
            // IOB (we'll synthesize from req.input.doses) instead of dropping
            // to 0.
            throw NSError(domain: "OpenAPSAdapter", code: -1,
                          userInfo: [NSLocalizedDescriptionKey: "oref DeterminationError: \(errMsg)"])
        }

        let tempRate = det.rate ?? scheduledBasalUhr
        let bolus = det.units ?? 0
        // dose = marginal delivery THIS STEP relative to scheduled basal.
        // OpenAPS sets a temp basal that runs for `duration` minutes; the
        // delivery in the next 5-min step at that rate, minus scheduled, is:
        let stepHours = req.config.evalStep / 3600.0
        let dose = (tempRate - scheduledBasalUhr) * stepHours + bolus

        // Synthesize a LoopPrediction so existing diagnostic readers
        // (eventualBG/IOB/COB) work without ClosedLoopSimulator changes.
        // Fallback eventualBG = current BG (no-change forecast) when the
        // Determination didn't include one (e.g., suspend-only output).
        let currentBG = req.input.glucose.last?.quantity.doubleValue(for: .milligramsPerDeciliter) ?? 100
        let eventualBG = det.eventualBG ?? currentBG
        let predGlucose: [PredictedGlucoseValue] = [
            PredictedGlucoseValue(
                startDate: req.t.addingTimeInterval(60 * 60),
                quantity: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: eventualBG)
            )
        ]
        let prediction = LoopPrediction<EvalCarbEntry>(
            glucose: predGlucose,
            effects: LoopAlgorithmEffects<EvalCarbEntry>(
                insulin: [], carbs: [], carbStatus: [],
                retrospectiveCorrection: [], momentum: [],
                insulinCounteraction: [], retrospectiveGlucoseDiscrepancies: []
            ),
            dosesRelativeToBasal: [],
            // Default to 0 instead of nil when the Determination didn't include
            // IOB/COB — the trace serializer rejects NaN, which is what
            // `?? .nan` would produce downstream.
            activeInsulin: det.IOB ?? 0,
            activeCarbs: det.COB ?? 0
        )

        return EngineStepResult(
            dose: dose,
            bolus: bolus,
            tempRate: tempRate,
            prediction: prediction,
            autosensRatio: det.sensitivityRatio,
            minGuardBG: det.minGuardBG,
            minPredBG: det.minPredBG,
            reason: det.reason
        )
    }

    private func fallbackResult(req: EngineStepRequest, scheduledBasalUhr: Double) -> EngineStepResult {
        // Use current BG as the eventualBG sentinel so downstream
        // serialization (NaN-rejecting JSON) doesn't blow up. Surfaces as
        // "no-op" behavior: dose=0, current BG holds.
        let currentBG = req.input.glucose.last?.quantity.doubleValue(for: .milligramsPerDeciliter) ?? 100
        let prediction = LoopPrediction<EvalCarbEntry>(
            glucose: [PredictedGlucoseValue(
                startDate: req.t,
                quantity: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: currentBG)
            )],
            effects: LoopAlgorithmEffects<EvalCarbEntry>(
                insulin: [], carbs: [], carbStatus: [],
                retrospectiveCorrection: [], momentum: [],
                insulinCounteraction: [], retrospectiveGlucoseDiscrepancies: []
            ),
            dosesRelativeToBasal: [],
            activeInsulin: 0,
            activeCarbs: 0
        )
        return EngineStepResult(
            dose: 0,
            bolus: 0,
            tempRate: scheduledBasalUhr,
            prediction: prediction
        )
    }
}
