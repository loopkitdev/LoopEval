// InputWindowBuilder.swift — slices pre-loaded data into per-step inputs

import Foundation
import LoopAlgorithm

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
    func buildInput(at t: Date, includeFutureInsulin overrideFuture: Bool? = nil) -> PredictionInput? {

        let useFutureInsulin = overrideFuture ?? config.includeFutureInsulin

        // ── Glucose ─────────────────────────────────────────────────────────────
        let glucoseWindowStart = t.addingTimeInterval(-config.glucoseLookbackHours * 3600)
        let glucoseSlice = glucose.filter {
            $0.startDate >= glucoseWindowStart && $0.startDate <= t
        }

        // Minimum data check: at least one reading in the last 30 min
        let recentCutoff = t.addingTimeInterval(-30 * 60)
        guard glucoseSlice.contains(where: { $0.startDate >= recentCutoff }) else {
            return nil
        }

        // ── Doses ────────────────────────────────────────────────────────────────
        let doseWindowStart = t.addingTimeInterval(-config.insulinLookbackHours * 3600)
        let doseWindowEnd: Date
        if useFutureInsulin {
            doseWindowEnd = t.addingTimeInterval(6 * 3600)
        } else {
            doseWindowEnd = t
        }
        // Keep doses that overlap the window (startDate or endDate inside window,
        // or dose spans the entire window)
        let dosesSlice = doses.filter { d in
            d.startDate <= doseWindowEnd && d.endDate >= doseWindowStart
        }

        // ── Carbs ────────────────────────────────────────────────────────────────
        let carbWindowStart = t.addingTimeInterval(-8 * 3600)
        let carbWindowEnd   = t.addingTimeInterval(6 * 3600)
        let carbsSlice = carbs.filter {
            $0.startDate >= carbWindowStart && $0.startDate <= carbWindowEnd
        }

        // ── Earliest dose start (needed for basal + ISF alignment) ──────────────
        // Doses are overlap-filtered: some may have startDates BEFORE basalWindowStart
        // (due to the 2h extension in getDoses). LoopAlgorithm requires
        // `basal.first.startDate <= doses.first.startDate` or it sets activeInsulin = 0.
        let nominalBasalWindowStart = t.addingTimeInterval(-config.insulinLookbackHours * 3600)
        let earliestDoseStart = dosesSlice.map(\.startDate).min() ?? nominalBasalWindowStart
        let basalWindowStart = min(nominalBasalWindowStart, earliestDoseStart)

        // ── Basal ────────────────────────────────────────────────────────────────
        let basalWindowEnd = t.addingTimeInterval(2 * 3600)
        var basalSlice = sliceSchedule(
            therapyTimeline.basal,
            from: basalWindowStart,
            to: basalWindowEnd
        )
        // Extend basal backward/forward to fill any schedule gaps
        if basalSlice.isEmpty {
            let fallback = therapyTimeline.basal.last?.value ?? 1.0
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

        // ── Sensitivity (ISF) ────────────────────────────────────────────────────
        // ISF must cover ALL dose startDates AND extend to t+8h (same reasoning as basal).
        let isfBackStart = basalWindowStart   // already min(nominal, earliestDose)
        let isfFwdEnd    = t.addingTimeInterval(8 * 3600)
        var sensitivitySlice = sliceSensitivity(
            therapyTimeline.sensitivity,
            from: isfBackStart,
            to: isfFwdEnd
        )

        if sensitivitySlice.isEmpty {
            // No ISF data at all in range — use any available value
            let fallback = therapyTimeline.sensitivity.last?.value
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

        // ── Carb Ratio ───────────────────────────────────────────────────────────
        // Must cover ALL carb entry startDates: [t-8h, t+6h]
        let crBack = carbWindowStart    // = t - 8h
        let crFwd  = carbWindowEnd      // = t + 6h
        var carbRatioSlice = sliceSchedule(
            therapyTimeline.carbRatio,
            from: crBack,
            to: crFwd
        )
        if carbRatioSlice.isEmpty {
            let fallback = therapyTimeline.carbRatio.last?.value ?? 10.0
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

        // ── Target ───────────────────────────────────────────────────────────────
        let targetSlice = sliceTarget(
            therapyTimeline.target,
            from: t,
            to: t.addingTimeInterval(6 * 3600)
        )

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

    /// Returns schedule entries that overlap `[from, to)`, keeping entries
    /// sorted and covering the range continuously.
    private func sliceSchedule(
        _ schedule: [AbsoluteScheduleValue<Double>],
        from: Date,
        to: Date
    ) -> [AbsoluteScheduleValue<Double>] {
        schedule.filter { $0.endDate > from && $0.startDate < to }
    }

    private func sliceSensitivity(
        _ schedule: [AbsoluteScheduleValue<LoopQuantity>],
        from: Date,
        to: Date
    ) -> [AbsoluteScheduleValue<LoopQuantity>] {
        schedule.filter { $0.endDate > from && $0.startDate < to }
    }

    private func sliceTarget(
        _ schedule: [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>],
        from: Date,
        to: Date
    ) -> [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>] {
        schedule.filter { $0.endDate > from && $0.startDate < to }
    }
}
