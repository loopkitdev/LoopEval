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

            let profile = try OpenAPSSwift.makeProfile(
                preferences: inputs.preferences,
                pumpSettings: inputs.pumpSettings,
                bgTargets: inputs.bgTargets,
                basalProfile: inputs.basalProfile,
                isf: inputs.isf,
                carbRatio: inputs.carbRatio,
                tempTargets: "[]",
                model: "\"X22\"",
                trioSettings: "{}",
                clock: req.t
            ).returnOrThrow()

            let clockStr = inputs.clockString

            let meal = try OpenAPSSwift.meal(
                pumphistory: inputs.pumpHistory,
                profile: profile,
                basalProfile: inputs.basalProfile,
                clock: clockStr,
                carbs: inputs.carbs,
                glucose: inputs.glucose
            ).returnOrThrow()

            let autosens = try OpenAPSSwift.autosense(
                glucose: inputs.glucose,
                pumpHistory: inputs.pumpHistory,
                basalProfile: inputs.basalProfile,
                profile: profile,
                carbs: inputs.carbs,
                tempTargets: "[]",
                clock: clockStr
            ).returnOrThrow()

            // Instrumentation: sample the autosens ratio (every 6h of sim time) so
            // we can see how far oref's autosens is running from 1.0 and with how
            // much data. Gated to keep the log light.
            if let data = autosens.data(using: .utf8),
               let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let ratio = obj["ratio"] as? Double {
                let comps = Calendar(identifier: .gregorian).dateComponents([.hour, .minute], from: req.t)
                if (comps.hour ?? 0) % 6 == 0 && (comps.minute ?? 0) < 5 {
                    FileHandle.standardError.write(Data("autosens \(req.t) ratio=\(String(format: "%.3f", ratio))\n".utf8))
                }
            }

            let iob = try OpenAPSSwift.iob(
                pumphistory: inputs.pumpHistory,
                profile: profile,
                clock: clockStr,
                autosens: autosens
            ).returnOrThrow()

            let det = try OpenAPSSwift.determineBasal(
                glucose: inputs.glucose,
                currentTemp: inputs.currentTemp,
                iob: iob,
                profile: profile,
                autosens: autosens,
                meal: meal,
                // microBolusAllowed: paired with the enableSMB* prefs above —
                // tells oref to actually emit SMBs (`units > 0`) when its
                // logic decides one is warranted.
                microBolusAllowed: true,
                reservoir: "100",
                pumpHistory: inputs.pumpHistory,
                preferences: inputs.preferences,
                basalProfile: inputs.basalProfile,
                trioCustomOrefVariables: inputs.trioCustomOref,
                clock: req.t
            ).returnOrThrow()

            return try mapDetermination(det, req: req, scheduledBasalUhr: inputs.scheduledBasalUhr)
        } catch {
            FileHandle.standardError.write(Data("OpenAPSAdapter error at \(req.t): \(error)\n".utf8))
            return fallbackResult(req: req, scheduledBasalUhr: activeBasal(at: req.t, req: req))
        }
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
        let tz = req.config.localTimezone
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
        let maxIob = req.therapy.maxBolus * 10.0
        var prefs: [String: Any] = [
            "max_iob": maxIob,
            "max_basal": req.therapy.maxBasalRate * 3.0,
            // Keys match Preferences.CodingKeys exactly — see
            // OpenAPSSwift/TrioModels/Preferences.swift
            "enableSMB_always": true,
            "enableSMB_with_COB": true,
            "enableSMB_after_carbs": true,
            "enableUAM": true,
            "allowSMB_with_high_temptarget": true,
            // Bumped from stock (30 each, 3, 4) so the algorithm's own limits
            // don't bind during recovery events. The intent is to measure how
            // the algorithm WANTS to dose, not how quickly it hits a hardcoded
            // safety ceiling that's smaller than Loop's auto-bolus cap.
            "maxSMBBasalMinutes": 60,
            "maxUAMSMBBasalMinutes": 60,
            "max_daily_safety_multiplier": 10,
            "current_basal_safety_multiplier": 10
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
        if let af = req.config.oapsAdjustmentFactor {
            prefs["adjustmentFactor"] = af
        }
        if let afs = req.config.oapsAdjustmentFactorSigmoid {
            prefs["adjustmentFactorSigmoid"] = afs
        }
        let preferencesJSON = String(data: try JSONSerialization.data(withJSONObject: prefs),
                                     encoding: .utf8)!

        // ── Pump settings ─────────────────────────────────────────────────────
        // maxBasal is multiplied so the temp-basal cap (= maxBasal × safety
        // multipliers) doesn't bind during recovery from outages. We want to
        // compare algorithm BEHAVIOR, not how quickly each algorithm hits a
        // safety ceiling.
        let pumpSettings: [String: Any] = [
            "insulin_action_curve": 6,
            "maxBolus": req.therapy.maxBolus,
            "maxBasal": req.therapy.maxBasalRate * 3.0
        ]
        let pumpSettingsJSON = String(data: try JSONSerialization.data(withJSONObject: pumpSettings),
                                      encoding: .utf8)!

        // ── 24h-cyclic schedules ──────────────────────────────────────────────
        let basalProfileJSON = encodeBasalSchedule(req.input.basal, calendar: cal)
        let isfJSON          = encodeISFSchedule(req.input.sensitivity, calendar: cal)
        let carbRatioJSON    = encodeCRSchedule(req.input.carbRatio, calendar: cal)
        let bgTargetsJSON    = encodeTargetSchedule(req.input.target, calendar: cal,
                                                    fallbackMidMgdl: 100)

        // ── Glucose history ───────────────────────────────────────────────────
        let glucoseJSON = encodeGlucose(req.input.glucose, iso: iso)

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
        let tddWindowStart = req.t.addingTimeInterval(-24 * 3600)
        var tdd = 0.0
        for d in req.input.doses {
            if d.endDate <= tddWindowStart || d.startDate >= req.t { continue }
            switch d.deliveryType {
            case .bolus:
                tdd += d.volume
            case .basal:
                // pro-rate to the intersection with the 24h window
                let lo = max(d.startDate, tddWindowStart)
                let hi = min(d.endDate, req.t)
                let segSec = max(0, hi.timeIntervalSince(lo))
                let fullSec = max(d.endDate.timeIntervalSince(d.startDate), 1)
                tdd += d.volume * segSec / fullSec
            }
        }
        // If we have less than 24h of dose history (typical: 16h slice), scale
        // up. Otherwise leave as-is.
        let earliestDoseT = req.input.doses.first?.startDate ?? req.t
        let coverageHours = max(0.5, min(24.0, req.t.timeIntervalSince(earliestDoseT) / 3600.0))
        if coverageHours < 24 {
            tdd *= 24.0 / coverageHours
        }
        // Add the scheduled-basal "default" — many sims have very few real
        // doses early on. Floor at 12 U/day so Dynamic ISF actually engages.
        let estimatedTdd = max(tdd, 12.0)

        // ── TrioCustomOrefVariables (overrides off) ───────────────────────────
        let trioCustom: [String: Any] = [
            "average_total_data": estimatedTdd,
            "currentTDD": estimatedTdd,
            "weightedAverage": estimatedTdd,
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

    private func encodeGlucose(_ samples: [EvalGlucoseSample], iso: ISO8601DateFormatter) -> String {
        let mgdl = LoopUnit.milligramsPerDeciliter
        let entries: [[String: Any]] = samples.enumerated().map { i, s in
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
                "createdAt": iso.string(from: c.entryDate),
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
            prediction: prediction
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
