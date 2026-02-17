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
    /// Returns `nil` if there is insufficient data — specifically, if there is no
    /// CGM reading within the last 30 minutes of `t`.
    func buildInput(at t: Date) -> PredictionInput? {

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
        if config.includeFutureInsulin {
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

        // ── Basal ────────────────────────────────────────────────────────────────
        let basalWindowStart = t.addingTimeInterval(-config.insulinLookbackHours * 3600)
        let basalWindowEnd   = t.addingTimeInterval(2 * 3600)
        let basalSlice = sliceSchedule(
            therapyTimeline.basal,
            from: basalWindowStart,
            to: basalWindowEnd
        )

        // ── Sensitivity (ISF) ────────────────────────────────────────────────────
        // CRITICAL: must extend to at least t+8h to prevent preconditionFailure
        // in glucoseEffects() inside LoopAlgorithm.
        let isfRequired = t.addingTimeInterval(8 * 3600)
        var sensitivitySlice = sliceSensitivity(
            therapyTimeline.sensitivity,
            from: basalWindowStart,   // ISF covers same early start as basal
            to: isfRequired
        )
        // Extend last value if it doesn't reach t+8h
        if let last = sensitivitySlice.last, last.endDate < isfRequired {
            sensitivitySlice[sensitivitySlice.count - 1] = AbsoluteScheduleValue(
                startDate: last.startDate,
                endDate: isfRequired,
                value: last.value
            )
        } else if sensitivitySlice.isEmpty, let last = therapyTimeline.sensitivity.last {
            // No sensitivity found in range — use global last value extended
            sensitivitySlice = [AbsoluteScheduleValue(
                startDate: basalWindowStart,
                endDate: isfRequired,
                value: last.value
            )]
        }

        // ── Carb Ratio ───────────────────────────────────────────────────────────
        let carbRatioSlice = sliceSchedule(
            therapyTimeline.carbRatio,
            from: t,
            to: t.addingTimeInterval(6 * 3600)
        )

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
