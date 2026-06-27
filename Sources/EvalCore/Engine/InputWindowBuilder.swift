// InputWindowBuilder.swift — slices pre-loaded data into per-step inputs

import Foundation
import LoopAlgorithm

// MARK: – Binary search helpers

/// Returns the index of the first element whose keyPath value is >= `date`.
private func lowerBound<T>(_ array: [T], by date: Date, key: KeyPath<T, Date>) -> Int {
    var lo = 0, hi = array.count
    while lo < hi {
        let mid = (lo + hi) / 2
        if array[mid][keyPath: key] < date { lo = mid + 1 } else { hi = mid }
    }
    return lo
}

/// Returns the index one past the last element whose keyPath value is <= `date`.
private func upperBound<T>(_ array: [T], by date: Date, key: KeyPath<T, Date>) -> Int {
    var lo = 0, hi = array.count
    while lo < hi {
        let mid = (lo + hi) / 2
        if array[mid][keyPath: key] <= date { lo = mid + 1 } else { hi = mid }
    }
    return lo
}

// MARK: – PredictionInput

/// The sliced inputs needed to call LoopAlgorithm.generatePrediction at a
/// specific point in time.
struct PredictionInput {
    let glucose: [EvalGlucoseSample]
    let doses: [EvalInsulinDose]
    let carbs: [EvalCarbEntry]
    let basal: [AbsoluteScheduleValue<Double>]
    let sensitivity: [AbsoluteScheduleValue<LoopQuantity>]
    let carbRatio: [AbsoluteScheduleValue<Double>]
    let target: [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>]
}

// MARK: – InputWindowBuilder

/// Efficiently slices pre-loaded data to build inputs for
/// `LoopAlgorithm.generatePrediction()` at any point in time `t`.
///
/// All arrays must be sorted ascending by startDate before passing them in.
struct InputWindowBuilder: Sendable {
    let glucose: [EvalGlucoseSample]
    let doses: [EvalInsulinDose]
    let carbs: [EvalCarbEntry]
    let therapyTimeline: TherapyTimeline
    let config: EvalConfig

    // MARK: – Build input for time t

    /// Returns a `PredictionInput` suitable for calling `generatePrediction(start: t, ...)`.
    ///
    /// - Parameter includeFutureInsulin: Override for the config flag. Pass `false` to
    ///   exclude doses after `t` (useful for side-by-side comparison curves). Defaults
    ///   to `config.includeFutureInsulin`.
    ///
    /// Returns `nil` if there is insufficient data — specifically, if there is no
    /// CGM reading within the last 30 minutes of `t`.
    /// - Parameter decisionAnchor: The instant the decision is triggered, used as the
    ///   decision-time dose cutoff (doses at/after it are this cycle's OWN output and are
    ///   excluded). Pass the COMMON step time in multi-arm contexts (the closed-loop sim
    ///   passes `t` for both arms so the cutoff is symmetric and identity is preserved).
    ///   When nil (forecast-match's natural use), it defaults to the triggering CGM time
    ///   (the latest glucose sample ≤ `t`) — robust to `t` being a few seconds AFTER the
    ///   CGM (e.g. when `t` is the timestamp of the dose this decision enacted).
    func buildInput(at t: Date,
                    includeFutureInsulin overrideFuture: Bool? = nil,
                    includeFutureCarbs overrideFutureCarbs: Bool? = nil,
                    carbVisibilityCutoff: Date? = nil,
                    decisionAnchor: Date? = nil) -> PredictionInput? {

        let useFutureInsulin = overrideFuture ?? config.includeFutureInsulin
        let useFutureCarbs   = overrideFutureCarbs ?? config.includeFutureCarbs

        // ── Glucose ─────────────────────────────────────────────────────────────
        let glucoseWindowStart = t.addingTimeInterval(-config.glucoseLookbackHours * 3600)
        let gLo = lowerBound(glucose, by: glucoseWindowStart, key: \.startDate)
        let gHi = upperBound(glucose, by: t, key: \.startDate)
        let glucoseSlice = gLo < gHi ? Array(glucose[gLo..<gHi]) : []

        // Minimum data check: at least one reading in the last 30 min
        let recentCutoff = t.addingTimeInterval(-30 * 60)
        guard glucoseSlice.last.map({ $0.startDate >= recentCutoff }) == true else {
            return nil
        }

        // ── Doses ────────────────────────────────────────────────────────────────
        // The decision is triggered by the latest CGM (`decisionTime`), NOT the
        // evaluation instant `t` (which, in field-replay, is often the timestamp of
        // the dose this very decision enacted — a few seconds AFTER the triggering
        // CGM). Loop doses strictly BEFORE the CGM that triggered it; the dose it
        // then enacts lands slightly later (startDate >= decisionTime). Including
        // that dose would feed the decision its OWN just-enacted insulin (inflated
        // IOB + a suppressed forecast → a systematic under-dose artifact). So the
        // decision-time dose window ends at the triggering CGM and EXCLUDES anything
        // at or after it.
        let decisionTime = decisionAnchor ?? glucoseSlice.last!.startDate
        let doseWindowStart = t.addingTimeInterval(-config.insulinLookbackHours * 3600)
        let dLo = lowerBound(doses, by: doseWindowStart, key: \.endDate)
        let dHi: Int
        if useFutureInsulin {
            // Oracle/debug: keep future doses out to +6h from t.
            dHi = upperBound(doses, by: t.addingTimeInterval(6 * 3600), key: \.startDate)
        } else {
            // Decision-time replay: lowerBound gives the first dose with
            // startDate >= decisionTime, so every kept dose has startDate < the
            // triggering CGM — doses "right at / right after" the CGM are ignored.
            dHi = lowerBound(doses, by: decisionTime, key: \.startDate)
        }
        var dosesSlice = dLo < dHi ? Array(doses[dLo..<dHi]) : []
        // In-progress temp basal handling (decision-time only). Default (false): keep the
        // temp's recorded duration projected forward — this best reproduces FieldLoop,
        // which projects the enacted temp/suspend forward (clipping it to end at t worsens
        // the field-match ~3 mg/dL at 6h; projecting the full 30-min commanded duration
        // OVERshoots +10 mg/dL — recorded duration is the best-balanced). Set true for the
        // cleaner going-forward design: a temp still running at t is treated as ENDED at t
        // (only the elapsed [start,t] portion counts; scheduled resumes after).
        if config.clipInProgressTempBasal && !useFutureInsulin {
            for i in dosesSlice.indices where dosesSlice[i].deliveryType == .basal && dosesSlice[i].endDate > decisionTime {
                let full = dosesSlice[i].endDate.timeIntervalSince(dosesSlice[i].startDate)
                let elapsed = max(0, decisionTime.timeIntervalSince(dosesSlice[i].startDate))
                dosesSlice[i].volume = full > 0 ? dosesSlice[i].volume * (elapsed / full) : 0
                dosesSlice[i].endDate = decisionTime
            }
        }

        // ── Carbs ────────────────────────────────────────────────────────────────
        // Window the absorption-relevant range by MEAL TIME (startDate), then
        // gate visibility by ENTRY TIME (entryDate): NORMAL dosing only knows about a
        // carb once the user has logged it by the forecast base time t (entryDate <= t).
        // A decision at t must NEVER see carbs entered after t. (The manual-bolus
        // recommendation path applies a tight, separate same-transaction relaxation —
        // see ClosedLoopSimulator — but normal auto-dosing stays strictly causal here.)
        // Meal time (startDate) can sit anywhere in the absorption window, incl. future.
        let carbWindowStart = t.addingTimeInterval(-8 * 3600)
        let carbWindowEnd   = t.addingTimeInterval(6 * 3600)
        let cLo = lowerBound(carbs, by: carbWindowStart, key: \.startDate)
        let cHi = upperBound(carbs, by: carbWindowEnd, key: \.startDate)
        var carbsSlice = cLo < cHi ? Array(carbs[cLo..<cHi]) : []
        if !useFutureCarbs {
            if let cutoff = carbVisibilityCutoff {
                // Manual-bolus recommendation path: gate by the TRUE entry time (entryDate),
                // bypassing the user-takeover visibility deferral that `dosingVisibleDate`
                // carries — so a carb co-logged with the bolus is visible to the bolus's own
                // recommendation even though normal dosing defers it. A future MEAL time
                // (startDate) is still kept (it's in the absorption window) so its predicted
                // absorption is in the forecast the bolus is computed against.
                carbsSlice = carbsSlice.filter { $0.entryDate <= cutoff }
            } else {
                // Normal dosing: strictly causal on the (possibly deferred) dosing gate.
                carbsSlice = carbsSlice.filter { $0.dosingVisibleDate <= t }
            }

            // ── Collapse carb REVISIONS ─────────────────────────────────────────
            // An edited carb entry is represented as several revisions sharing a
            // revisionKey (e.g. 15g visible from 11:26, 45g visible from 12:01).
            // The visibility filter above keeps EVERY revision whose gate <= t, so
            // after an edit both the 15g and 45g revisions survive and would SUM to
            // 60g. Keep only the LATEST-visible revision per key — exactly the grams
            // the deployed Loop had at the decision time. Entries with no
            // revisionKey (the non-edited common case) pass through untouched, so
            // this is a no-op for any input that carries no revisions.
            if carbsSlice.contains(where: { $0.revisionKey != nil }) {
                let useCutoff = carbVisibilityCutoff != nil
                var latestByKey: [String: EvalCarbEntry] = [:]
                var passthrough: [EvalCarbEntry] = []
                for c in carbsSlice {
                    guard let key = c.revisionKey else { passthrough.append(c); continue }
                    let gate = useCutoff ? c.entryDate : c.dosingVisibleDate
                    if let existing = latestByKey[key] {
                        let exGate = useCutoff ? existing.entryDate : existing.dosingVisibleDate
                        if gate > exGate { latestByKey[key] = c }
                    } else {
                        latestByKey[key] = c
                    }
                }
                carbsSlice = (passthrough + Array(latestByKey.values))
                    .sorted { $0.startDate < $1.startDate }
            }
        }

        // ── Earliest dose start (needed for basal + ISF alignment) ──────────────
        // Doses are overlap-filtered: some may have startDates BEFORE basalWindowStart
        // (due to the 2h extension in getDoses). LoopAlgorithm requires
        // `basal.first.startDate <= doses.first.startDate` or it sets activeInsulin = 0.
        let nominalBasalWindowStart = t.addingTimeInterval(-config.insulinLookbackHours * 3600)
        let earliestDoseStart = dosesSlice.map(\.startDate).min() ?? nominalBasalWindowStart
        let basalWindowStart = min(nominalBasalWindowStart, earliestDoseStart)

        // ── Decision-time override gating ─────────────────────────────────────────
        // Apply ONLY the Temporary Overrides the user had enabled by the decision
        // time `t` (window.start <= t). A future override (created later) must be
        // invisible to this earlier forecast — the same causal gate as carb
        // visibility. We slice the RAW (un-override) schedules and apply the gated
        // windows here, instead of reading the fully-baked schedule (which would
        // leak a not-yet-created override into earlier decisions — e.g. a 10pm
        // "high" override's higher target floor reaching back into a 6pm meal
        // forecast and spuriously gating its auto-bolus). When there are no
        // overrides, srcX == the baked fields and applyOv=false ⇒ behavior is
        // byte-identical to the pre-gating path.
        let applyOv = !therapyTimeline.overrideWindows.isEmpty && !therapyTimeline.rawBasal.isEmpty
        // Include every override that has STARTED by t (start <= t). A window must keep
        // applying to the PAST schedule even after it ended, because doses delivered
        // during it keep their delivery-time ISF/basal (dose-time ISF) for their whole
        // lifetime — dropping an ended override would wrongly revert those past doses'
        // ISF (over-dose). Each window's [start, end] confines its effect; for the
        // FORECAST horizon an ended override (end <= t) naturally contributes nothing.
        // EXCEPTION: an INDEFINITE override still ACTIVE at t (start <= t < end) had no
        // scheduled end known at t, so extend its end across this decision's horizon —
        // reverting the target at its realized (future) cancel would leak that cancel.
        let gatedWindows: [OverrideWindow] = applyOv ? therapyTimeline.overrideWindows.compactMap { w in
            guard w.start <= t else { return nil }
            guard w.indefinite, t < w.end else { return w }   // ended/definite: [start,end] as-is
            return OverrideWindow(start: w.start, end: t.addingTimeInterval(9 * 3600),
                                  factor: w.factor, targetLo: w.targetLo, targetHi: w.targetHi,
                                  indefinite: true)
        } : []
        // Future-profile-edit gate: a decision at t must not see a profile schedule the
        // user EDITED after t. Hold the decision-time-active profile's schedule across the
        // forecast horizon by clamping at the first edit time > t — drop later-edited
        // segments and extend the active-at-edit value forward. Daily transitions of the
        // active profile BEFORE the edit are preserved (they're known at decision time).
        // editClamp = nil ⇒ no edit ahead ⇒ no-op. (Profile-edit leak fix, 2026-06-22.)
        let editClamp = therapyTimeline.profileEditTimes.first { $0 > t }
        let srcBasal = holdPastEdit(applyOv ? therapyTimeline.rawBasal       : therapyTimeline.basal,       editClamp)
        let srcSens  = holdPastEdit(applyOv ? therapyTimeline.rawSensitivity : therapyTimeline.sensitivity, editClamp)
        let srcCR    = holdPastEdit(applyOv ? therapyTimeline.rawCarbRatio   : therapyTimeline.carbRatio,   editClamp)
        let srcTgt   = holdPastEdit(applyOv ? therapyTimeline.rawTarget      : therapyTimeline.target,      editClamp)

        // ── Basal ────────────────────────────────────────────────────────────────
        let basalWindowEnd = t.addingTimeInterval(2 * 3600)
        var basalSlice = sliceSchedule(
            srcBasal,
            from: basalWindowStart,
            to: basalWindowEnd
        )
        // Extend basal backward/forward to fill any schedule gaps
        if basalSlice.isEmpty {
            let fallback = srcBasal.last?.value ?? 1.0
            basalSlice = [AbsoluteScheduleValue(startDate: basalWindowStart, endDate: basalWindowEnd, value: fallback)]
        } else {
            if basalSlice[0].startDate > basalWindowStart {
                basalSlice[0] = AbsoluteScheduleValue(startDate: basalWindowStart, endDate: basalSlice[0].endDate, value: basalSlice[0].value)
            }
            let li = basalSlice.count - 1
            if basalSlice[li].endDate < basalWindowEnd {
                basalSlice[li] = AbsoluteScheduleValue(startDate: basalSlice[li].startDate, endDate: basalWindowEnd, value: basalSlice[li].value)
            }
        }
        // Apply decision-time-gated overrides to the basal slice (basal × f).
        if applyOv { basalSlice = TemporaryOverrides.applyDoubles(basalSlice, gatedWindows, divide: false) }

        // ── Sensitivity (ISF) ────────────────────────────────────────────────────
        // ISF must cover ALL dose startDates AND extend to t+8h (same reasoning as basal).
        let isfBackStart = basalWindowStart   // already min(nominal, earliestDose)
        let isfFwdEnd    = t.addingTimeInterval(8 * 3600)
        var sensitivitySlice = sliceSensitivity(
            srcSens,
            from: isfBackStart,
            to: isfFwdEnd
        )

        if sensitivitySlice.isEmpty {
            // No ISF data at all in range — use any available value
            let fallback = srcSens.last?.value
                ?? LoopQuantity(unit: .milligramsPerDeciliterPerInternationalUnit, doubleValue: 50)
            sensitivitySlice = [AbsoluteScheduleValue(
                startDate: isfBackStart,
                endDate: isfFwdEnd,
                value: fallback
            )]
        } else {
            // Extend first entry backward if it doesn't reach isfBackStart
            if sensitivitySlice[0].startDate > isfBackStart {
                sensitivitySlice[0] = AbsoluteScheduleValue(
                    startDate: isfBackStart,
                    endDate: sensitivitySlice[0].endDate,
                    value: sensitivitySlice[0].value
                )
            }
            // Extend last entry forward if it doesn't reach t+8h
            let lastIdx = sensitivitySlice.count - 1
            if sensitivitySlice[lastIdx].endDate < isfFwdEnd {
                sensitivitySlice[lastIdx] = AbsoluteScheduleValue(
                    startDate: sensitivitySlice[lastIdx].startDate,
                    endDate: isfFwdEnd,
                    value: sensitivitySlice[lastIdx].value
                )
            }
        }

        // Apply decision-time-gated overrides to the ISF slice (ISF ÷ f).
        if applyOv { sensitivitySlice = TemporaryOverrides.applyISF(sensitivitySlice, gatedWindows) }

        // Apply ISF multiplier (no-op when multiplier == 1.0)
        sensitivitySlice = applyISFMultiplier(sensitivitySlice)

        // Apply basal rate multiplier (no-op when multiplier == 1.0)
        basalSlice = applyBasalMultiplier(basalSlice)

        // ── Carb Ratio ───────────────────────────────────────────────────────────
        // Must cover ALL carb entry startDates: [t-8h, t+6h]
        let crBack = carbWindowStart    // = t - 8h
        let crFwd  = carbWindowEnd      // = t + 6h
        var carbRatioSlice = sliceSchedule(
            srcCR,
            from: crBack,
            to: crFwd
        )
        if carbRatioSlice.isEmpty {
            let fallback = srcCR.last?.value ?? 10.0
            carbRatioSlice = [AbsoluteScheduleValue(startDate: crBack, endDate: crFwd, value: fallback)]
        } else {
            if carbRatioSlice[0].startDate > crBack {
                carbRatioSlice[0] = AbsoluteScheduleValue(startDate: crBack, endDate: carbRatioSlice[0].endDate, value: carbRatioSlice[0].value)
            }
            let li2 = carbRatioSlice.count - 1
            if carbRatioSlice[li2].endDate < crFwd {
                carbRatioSlice[li2] = AbsoluteScheduleValue(startDate: carbRatioSlice[li2].startDate, endDate: crFwd, value: carbRatioSlice[li2].value)
            }
        }
        // Apply decision-time-gated overrides to the carb-ratio slice (CR ÷ f).
        if applyOv { carbRatioSlice = TemporaryOverrides.applyDoubles(carbRatioSlice, gatedWindows, divide: true) }

        // Apply carb ratio multiplier (no-op when multiplier == 1.0)
        carbRatioSlice = applyCarbRatioMultiplier(carbRatioSlice)

        // ── Target ───────────────────────────────────────────────────────────────
        // Start the target slice at the prediction's first point (the decision CGM,
        // which can be a little before t when the decision is triggered after the CGM),
        // NOT at t — the dose-correction is anchored there and `insulinCorrection`
        // force-unwraps `correctionRange.closestPrior(to: predictionPoint)`, so every
        // considered point (incl. the now-point) must be covered or it crashes.
        let targetStart = min(t, glucoseSlice.last?.startDate ?? t)
        var targetSlice = sliceTarget(
            srcTgt,
            from: targetStart,
            to: t.addingTimeInterval(6 * 3600)
        )
        // Apply decision-time-gated overrides to the target slice (range ← override).
        if applyOv { targetSlice = TemporaryOverrides.applyTargets(targetSlice, gatedWindows) }

        return PredictionInput(
            glucose: glucoseSlice,
            doses: dosesSlice,
            carbs: carbsSlice,
            basal: basalSlice,
            sensitivity: sensitivitySlice,
            carbRatio: carbRatioSlice,
            target: targetSlice
        )
    }

    // MARK: – Private slicing helpers

    /// Returns schedule entries that overlap `[from, to)` using binary search.
    /// Schedules are contiguous (endDate[i] == startDate[i+1]), so we step back
    /// one from the lower bound to catch entries that start before `from` but
    /// end after it.
    /// Hold the decision-time-active profile's schedule across a future profile edit.
    /// Keeps every segment starting before `editClamp` (the active profile + its known
    /// daily transitions + all past/lookback segments) and extends the last such segment
    /// to the distant future, so forecast times after the edit use the active-at-edit
    /// value rather than the future-edited profile. `editClamp == nil` ⇒ unchanged.
    private func holdPastEdit<V>(_ s: [AbsoluteScheduleValue<V>], _ editClamp: Date?) -> [AbsoluteScheduleValue<V>] {
        guard let te = editClamp else { return s }
        var out = s.filter { $0.startDate < te }
        guard let last = out.last else { return s }   // nothing before the edit → leave as-is
        out[out.count - 1] = AbsoluteScheduleValue(startDate: last.startDate,
                                                   endDate: Date.distantFuture, value: last.value)
        return out
    }

    private func sliceSchedule(
        _ schedule: [AbsoluteScheduleValue<Double>],
        from: Date,
        to: Date
    ) -> [AbsoluteScheduleValue<Double>] {
        var lo = lowerBound(schedule, by: from, key: \.startDate)
        if lo > 0 { lo -= 1 }
        let hi = lowerBound(schedule, by: to, key: \.startDate)
        guard lo < hi else { return [] }
        return Array(schedule[lo..<hi]).filter { $0.endDate > from }
    }

    private func sliceSensitivity(
        _ schedule: [AbsoluteScheduleValue<LoopQuantity>],
        from: Date,
        to: Date
    ) -> [AbsoluteScheduleValue<LoopQuantity>] {
        var lo = lowerBound(schedule, by: from, key: \.startDate)
        if lo > 0 { lo -= 1 }
        let hi = lowerBound(schedule, by: to, key: \.startDate)
        guard lo < hi else { return [] }
        return Array(schedule[lo..<hi]).filter { $0.endDate > from }
    }

    private func sliceTarget(
        _ schedule: [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>],
        from: Date,
        to: Date
    ) -> [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>] {
        var lo = lowerBound(schedule, by: from, key: \.startDate)
        if lo > 0 { lo -= 1 }
        let hi = lowerBound(schedule, by: to, key: \.startDate)
        guard lo < hi else { return [] }
        return Array(schedule[lo..<hi]).filter { $0.endDate > from }
    }

    /// Apply `config.sensitivityMultiplier` and (optionally) per-local-hour
    /// multipliers from `config.sensitivityHourlyMultipliers` to a sensitivity
    /// slice. When hourly multipliers are present, each entry is split at
    /// local-hour boundaries (per `config.localTimezone`) so the appropriate
    /// per-hour multiplier applies to each piece.
    private func applyISFMultiplier(
        _ slice: [AbsoluteScheduleValue<LoopQuantity>]
    ) -> [AbsoluteScheduleValue<LoopQuantity>] {
        return EvaluationEngine.applySensitivityScaling(
            slice,
            globalMultiplier: config.sensitivityMultiplier,
            hourlyMultipliers: config.sensitivityHourlyMultipliers,
            timezone: config.localTimezone
        )
    }

    /// Apply `config.carbRatioMultiplier` to a carb ratio slice.
    /// Multiplier > 1 → larger CR value → less insulin per carb.
    /// Multiplier < 1 → smaller CR value → more insulin per carb.
    private func applyCarbRatioMultiplier(
        _ slice: [AbsoluteScheduleValue<Double>]
    ) -> [AbsoluteScheduleValue<Double>] {
        guard config.carbRatioMultiplier != 1.0 else { return slice }
        return slice.map { entry in
            let scaled = entry.value * config.carbRatioMultiplier
            return AbsoluteScheduleValue(
                startDate: entry.startDate,
                endDate: entry.endDate,
                value: scaled
            )
        }
    }

    /// Apply `config.basalRateMultiplier` to a basal schedule slice.
    /// Multiplier > 1 → higher basal rate → more background insulin.
    /// Multiplier < 1 → lower basal rate → less background insulin.
    private func applyBasalMultiplier(
        _ slice: [AbsoluteScheduleValue<Double>]
    ) -> [AbsoluteScheduleValue<Double>] {
        guard config.basalRateMultiplier != 1.0 else { return slice }
        return slice.map { entry in
            let scaled = entry.value * config.basalRateMultiplier
            return AbsoluteScheduleValue(
                startDate: entry.startDate,
                endDate: entry.endDate,
                value: scaled
            )
        }
    }
}
