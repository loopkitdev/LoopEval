// TherapySettings.swift — therapy configuration at a point in time
//
// LoopQuantity and ClosedRange<LoopQuantity> are not directly Codable, so we
// use a custom Codable implementation that mirrors the AlgorithmInputFixture
// approach: sensitivity is stored as mg/dL values, targets as lower/upper
// bounds in mg/dL, and suspendThreshold as a mg/dL Double.

import Foundation
import LoopAlgorithm

public struct TherapySettings: Codable, Sendable {
    public var basal: [AbsoluteScheduleValue<Double>]
    public var sensitivity: [AbsoluteScheduleValue<LoopQuantity>]   // ISF mg/dL/U
    public var carbRatio: [AbsoluteScheduleValue<Double>]           // g/U
    public var target: [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>]  // mg/dL range
    public var suspendThreshold: LoopQuantity?                       // mg/dL
    public var maxBolus: Double
    public var maxBasalRate: Double
    public var insulinType: ExponentialInsulinModelPreset

    public init(
        basal: [AbsoluteScheduleValue<Double>],
        sensitivity: [AbsoluteScheduleValue<LoopQuantity>],
        carbRatio: [AbsoluteScheduleValue<Double>],
        target: [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>],
        suspendThreshold: LoopQuantity? = nil,
        maxBolus: Double,
        maxBasalRate: Double,
        insulinType: ExponentialInsulinModelPreset = .rapidActingAdult
    ) {
        self.basal            = basal
        self.sensitivity      = sensitivity
        self.carbRatio        = carbRatio
        self.target           = target
        self.suspendThreshold = suspendThreshold
        self.maxBolus         = maxBolus
        self.maxBasalRate     = maxBasalRate
        self.insulinType      = insulinType
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
    }
}
