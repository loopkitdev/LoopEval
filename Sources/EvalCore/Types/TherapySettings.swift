// TherapySettings.swift — therapy configuration at a point in time
//
// LoopQuantity and ClosedRange<LoopQuantity> are not directly Codable, so we
// use a custom Codable implementation that mirrors the AlgorithmInputFixture
// approach: sensitivity is stored as mg/dL values, targets as lower/upper
// bounds in mg/dL, and suspendThreshold as a mg/dL Double.

import Foundation
import LoopAlgorithm

/// A Nightscout "Temporary Target" (oref temptarget). Carried on the therapy
/// timeline so the oref candidate can apply the user's real temp targets at
/// decision time (start <= t). oref uses target as a single value (top==bottom
/// in practice for Trio); we keep one mg/dL value + the window.
public struct EvalTempTarget: Codable, Sendable, Equatable {
    public var start: Date          // created_at
    public var durationMin: Double  // minutes (0 == cancel)
    public var targetMgdl: Double   // target BG (mg/dL)
    public init(start: Date, durationMin: Double, targetMgdl: Double) {
        self.start = start; self.durationMin = durationMin; self.targetMgdl = targetMgdl
    }
}

public struct TherapySettings: Codable, Sendable {
    public var basal: [AbsoluteScheduleValue<Double>]
    public var sensitivity: [AbsoluteScheduleValue<LoopQuantity>]   // ISF mg/dL/U
    public var carbRatio: [AbsoluteScheduleValue<Double>]           // g/U
    public var target: [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>]  // mg/dL range
    public var suspendThreshold: LoopQuantity?                       // mg/dL
    public var maxBolus: Double
    public var maxBasalRate: Double
    public var insulinType: ExponentialInsulinModelPreset

    // ── Decision-time override gating (not Codable; in-memory only) ───────────
    // The fields above (`basal`/`sensitivity`/`carbRatio`/`target`) hold the
    // FULLY-override-applied ("baked") schedules — what callers that read the
    // timeline directly (precompute, sim scheduled-basal physics) have always
    // used. To make DECISION-TIME replay faithful, we also keep the RAW
    // (un-override) schedules plus the override windows so that a forecast made
    // at time `t` can apply ONLY the overrides the user had already enabled by
    // `t` (window.start <= t) — a future override (created later) must be
    // invisible to an earlier decision, exactly like the carb visibility gate.
    // Empty `overrideWindows` ⇒ no gating (the baked == raw, behavior unchanged).
    public var rawBasal: [AbsoluteScheduleValue<Double>] = []
    public var rawSensitivity: [AbsoluteScheduleValue<LoopQuantity>] = []
    public var rawCarbRatio: [AbsoluteScheduleValue<Double>] = []
    public var rawTarget: [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>] = []
    public var overrideWindows: [OverrideWindow] = []
    // Times at which the user EDITED the profile schedule (profile-history boundaries).
    // A decision before such an edit must not see it: InputWindowBuilder holds the
    // decision-time-active profile's schedule across the forecast horizon rather than
    // switching to a future-edited profile mid-horizon (future-profile-edit leak fix).
    // Empty ⇒ no gating (single-profile/backfill behavior unchanged).
    public var profileEditTimes: [Date] = []
    // NS Temporary Targets (oref temptargets) — applied by the oref candidate at
    // decision time (start <= t). Empty ⇒ none (Loop path ignores this field).
    public var orefTempTargets: [EvalTempTarget] = []
    // The timezone the schedules (basal/ISF/CR/target) are DEFINED in — the NS
    // profile's timezone. Schedule reconstruction (time-of-day regrouping) MUST
    // use this, NOT the host/sim timezone, or a user whose profile TZ differs
    // from the host gets shifted schedules (e.g. Berlin profile on a US host →
    // mangled basal). nil ⇒ fall back to the sim's localTimezone (legacy).
    public var scheduleTimeZone: TimeZone? = nil

    public init(
        basal: [AbsoluteScheduleValue<Double>],
        sensitivity: [AbsoluteScheduleValue<LoopQuantity>],
        carbRatio: [AbsoluteScheduleValue<Double>],
        target: [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>],
        suspendThreshold: LoopQuantity? = nil,
        maxBolus: Double,
        maxBasalRate: Double,
        insulinType: ExponentialInsulinModelPreset = .rapidActingAdult,
        rawBasal: [AbsoluteScheduleValue<Double>] = [],
        rawSensitivity: [AbsoluteScheduleValue<LoopQuantity>] = [],
        rawCarbRatio: [AbsoluteScheduleValue<Double>] = [],
        rawTarget: [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>] = [],
        overrideWindows: [OverrideWindow] = [],
        profileEditTimes: [Date] = [],
        orefTempTargets: [EvalTempTarget] = [],
        scheduleTimeZone: TimeZone? = nil
    ) {
        self.basal            = basal
        self.sensitivity      = sensitivity
        self.carbRatio        = carbRatio
        self.target           = target
        self.suspendThreshold = suspendThreshold
        self.maxBolus         = maxBolus
        self.maxBasalRate     = maxBasalRate
        self.insulinType      = insulinType
        self.rawBasal         = rawBasal
        self.rawSensitivity   = rawSensitivity
        self.rawCarbRatio     = rawCarbRatio
        self.rawTarget        = rawTarget
        self.overrideWindows  = overrideWindows
        self.profileEditTimes = profileEditTimes
        self.orefTempTargets  = orefTempTargets
        self.scheduleTimeZone = scheduleTimeZone
    }

    // MARK: – Codable helpers

    /// Intermediate struct for encoding/decoding glucose ranges.
    private struct CodableTargetEntry: Codable {
        var startDate: Date
        var endDate: Date
        var lowerBound: Double   // mg/dL
        var upperBound: Double   // mg/dL
    }

    private enum CodingKeys: String, CodingKey {
        case basal
        case sensitivity        // stored as mg/dL values
        case carbRatio
        case target             // stored as CodableTargetEntry
        case suspendThreshold   // stored as mg/dL Double
        case maxBolus
        case maxBasalRate
        case insulinType
        // Decision-time override gating (must round-trip through the cache, else
        // a cache load silently drops the gate and the override leaks back in).
        case rawBasal
        case rawSensitivity     // stored as mg/dL values
        case rawCarbRatio
        case rawTarget          // stored as CodableTargetEntry
        case overrideWindows
        case profileEditTimes
        case orefTempTargets
        case scheduleTimeZoneIdentifier
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)

        basal     = try c.decode([AbsoluteScheduleValue<Double>].self, forKey: .basal)
        carbRatio = try c.decode([AbsoluteScheduleValue<Double>].self, forKey: .carbRatio)
        maxBolus  = try c.decode(Double.self, forKey: .maxBolus)
        maxBasalRate = try c.decode(Double.self, forKey: .maxBasalRate)
        insulinType  = try c.decode(ExponentialInsulinModelPreset.self, forKey: .insulinType)

        // sensitivity: stored as mg/dL scalars
        let sensRaw = try c.decode([AbsoluteScheduleValue<Double>].self, forKey: .sensitivity)
        sensitivity = sensRaw.map {
            AbsoluteScheduleValue(
                startDate: $0.startDate, endDate: $0.endDate,
                value: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: $0.value)
            )
        }

        // target: stored as {startDate, endDate, lowerBound, upperBound}
        let targetRaw = try c.decode([CodableTargetEntry].self, forKey: .target)
        target = targetRaw.map {
            let lo = LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: $0.lowerBound)
            let hi = LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: $0.upperBound)
            return AbsoluteScheduleValue(
                startDate: $0.startDate, endDate: $0.endDate,
                value: ClosedRange(uncheckedBounds: (lower: lo, upper: hi))
            )
        }

        // suspendThreshold: stored as mg/dL scalar
        if let rawThreshold = try c.decodeIfPresent(Double.self, forKey: .suspendThreshold) {
            suspendThreshold = LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: rawThreshold)
        } else {
            suspendThreshold = nil
        }

        // ── Decision-time override gating (optional; absent in legacy caches) ──────
        rawBasal     = (try? c.decodeIfPresent([AbsoluteScheduleValue<Double>].self, forKey: .rawBasal)) ?? []
        rawCarbRatio = (try? c.decodeIfPresent([AbsoluteScheduleValue<Double>].self, forKey: .rawCarbRatio)) ?? []
        let rawSensRaw = (try? c.decodeIfPresent([AbsoluteScheduleValue<Double>].self, forKey: .rawSensitivity)) ?? []
        rawSensitivity = rawSensRaw.map {
            AbsoluteScheduleValue(startDate: $0.startDate, endDate: $0.endDate,
                                  value: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: $0.value))
        }
        let rawTargetRaw = (try? c.decodeIfPresent([CodableTargetEntry].self, forKey: .rawTarget)) ?? []
        rawTarget = rawTargetRaw.map {
            let lo = LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: $0.lowerBound)
            let hi = LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: $0.upperBound)
            return AbsoluteScheduleValue(startDate: $0.startDate, endDate: $0.endDate,
                                         value: ClosedRange(uncheckedBounds: (lower: lo, upper: hi)))
        }
        overrideWindows = (try? c.decodeIfPresent([OverrideWindow].self, forKey: .overrideWindows)) ?? []
        profileEditTimes = (try? c.decodeIfPresent([Date].self, forKey: .profileEditTimes)) ?? []
        orefTempTargets = (try? c.decodeIfPresent([EvalTempTarget].self, forKey: .orefTempTargets)) ?? []
        if let tzId = (try? c.decodeIfPresent(String.self, forKey: .scheduleTimeZoneIdentifier)) ?? nil {
            scheduleTimeZone = TimeZone(identifier: tzId)
        }
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)

        try c.encode(basal, forKey: .basal)
        try c.encode(carbRatio, forKey: .carbRatio)
        try c.encode(maxBolus, forKey: .maxBolus)
        try c.encode(maxBasalRate, forKey: .maxBasalRate)
        try c.encode(insulinType, forKey: .insulinType)

        let sensRaw = sensitivity.map {
            AbsoluteScheduleValue(
                startDate: $0.startDate, endDate: $0.endDate,
                value: $0.value.doubleValue(for: .milligramsPerDeciliter)
            )
        }
        try c.encode(sensRaw, forKey: .sensitivity)

        let targetRaw = target.map { entry in
            CodableTargetEntry(
                startDate: entry.startDate,
                endDate:   entry.endDate,
                lowerBound: entry.value.lowerBound.doubleValue(for: .milligramsPerDeciliter),
                upperBound: entry.value.upperBound.doubleValue(for: .milligramsPerDeciliter)
            )
        }
        try c.encode(targetRaw, forKey: .target)

        if let st = suspendThreshold {
            try c.encode(st.doubleValue(for: .milligramsPerDeciliter), forKey: .suspendThreshold)
        }

        // ── Decision-time override gating ─────────────────────────────────────────
        if !rawBasal.isEmpty     { try c.encode(rawBasal, forKey: .rawBasal) }
        if !rawCarbRatio.isEmpty { try c.encode(rawCarbRatio, forKey: .rawCarbRatio) }
        if !rawSensitivity.isEmpty {
            let raw = rawSensitivity.map {
                AbsoluteScheduleValue(startDate: $0.startDate, endDate: $0.endDate,
                                      value: $0.value.doubleValue(for: .milligramsPerDeciliter))
            }
            try c.encode(raw, forKey: .rawSensitivity)
        }
        if !rawTarget.isEmpty {
            let raw = rawTarget.map { entry in
                CodableTargetEntry(
                    startDate: entry.startDate, endDate: entry.endDate,
                    lowerBound: entry.value.lowerBound.doubleValue(for: .milligramsPerDeciliter),
                    upperBound: entry.value.upperBound.doubleValue(for: .milligramsPerDeciliter))
            }
            try c.encode(raw, forKey: .rawTarget)
        }
        if !overrideWindows.isEmpty { try c.encode(overrideWindows, forKey: .overrideWindows) }
        if !profileEditTimes.isEmpty { try c.encode(profileEditTimes, forKey: .profileEditTimes) }
        if !orefTempTargets.isEmpty { try c.encode(orefTempTargets, forKey: .orefTempTargets) }
        if let tz = scheduleTimeZone { try c.encode(tz.identifier, forKey: .scheduleTimeZoneIdentifier) }
    }
}
