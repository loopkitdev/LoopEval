// PreloadedData.swift — all data pre-fetched for an evaluation run

import Foundation
import LoopAlgorithm

/// All data required for a sweep, pre-fetched once and shared across all
/// evaluation steps (or all configs in a parameter sweep).
///
/// Designed to be pre-loaded with generous buffers so individual
/// `buildInput(at:)` calls can slice without additional I/O.
public struct PreloadedData: Sendable {
    public let glucose: [EvalGlucoseSample]
    public let doses: [EvalInsulinDose]
    public let carbs: [EvalCarbEntry]
    public let therapyTimeline: TherapyTimeline

    public init(
        glucose: [EvalGlucoseSample],
        doses: [EvalInsulinDose],
        carbs: [EvalCarbEntry],
        therapyTimeline: TherapyTimeline
    ) {
        self.glucose         = glucose
        self.doses           = doses
        self.carbs           = carbs
        self.therapyTimeline = therapyTimeline
    }
}

// MARK: - PrecomputedInsulinInput factory

extension PreloadedData {
    /// Build a `PrecomputedInsulinInput` suitable for a full sweep over `interval`.
    ///
    /// - **Annotation** (`annotated(with: basal)`) is ISF-independent and is
    ///   computed here once regardless of how many ISF configs are being swept.
    ///
    /// - **Effects** (`glucoseEffects(insulinSensitivityHistory:)`) are ISF-
    ///   dependent and are computed here for the given `sensitivity` timeline
    ///   (which may already have a multiplier applied by the caller).  For an
    ///   ISF sweep, call this once per multiplier value and reuse the result
    ///   for all ~2000 time steps in that config.
    ///
    /// The effect timeline is extended to `interval.end + defaultInsulinActivityDuration`
    /// so tail steps in the sweep don't see a truncated effect array.
    ///
    /// - Parameters:
    ///   - interval: The evaluation interval (used to size the effect timeline).
    ///   - sensitivity: ISF timeline to use for effect pre-computation (pass
    ///     the scaled version for ISF sweeps).
    ///   - useMidAbsorptionISF: Mirror of `EvalConfig.useMidAbsorptionISF`.
    func precomputedInsulinInput(
        for interval: DateInterval,
        sensitivity: [AbsoluteScheduleValue<LoopQuantity>],
        useMidAbsorptionISF: Bool = false
    ) -> PrecomputedInsulinInput {
        // Annotation: ISF-independent, covers the full preloaded dose window.
        let base = PrecomputedInsulinInput.annotate(
            doses: doses,
            basal: therapyTimeline.basal
        )

        // Effects: ISF-dependent.
        //
        // The annotated dose array may contain BasalRelativeDose entries with
        // startDate as early as the preloaded basal timeline start (well before
        // the sweep window). glucoseEffects() checks ISF coverage per-dose and
        // crashes if ISF doesn't reach back that far.
        //
        // Fix: clamp effectsFrom to the earliest annotated dose startDate (or
        // the sensitivity timeline start, whichever is later), and extend the
        // sensitivity backward if needed.
        let earliestDoseStart = base.annotatedDoses.first?.startDate
        var extendedSensitivity = sensitivity
        if let earliest = earliestDoseStart,
           let firstISF = extendedSensitivity.first,
           firstISF.startDate > earliest {
            extendedSensitivity[0] = AbsoluteScheduleValue(
                startDate: earliest,
                endDate: firstISF.endDate,
                value: firstISF.value
            )
        }

        // Cover through sweep end + full activity tail so tail steps never
        // see a truncated effect array.
        let effectsEnd = interval.end.addingTimeInterval(
            InsulinMath.defaultInsulinActivityDuration + 5 * 60
        )
        return base.withEffects(
            sensitivity: extendedSensitivity,
            to: effectsEnd,
            useMidAbsorptionISF: useMidAbsorptionISF
        )
    }
}
