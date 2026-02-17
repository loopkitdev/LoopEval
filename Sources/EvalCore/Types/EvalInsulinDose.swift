// EvalInsulinDose.swift — concrete InsulinDose conforming type
//
// Design decision: InsulinModel is a protocol (not Codable).
// We store ExponentialInsulinModelPreset for serialization and derive
// insulinModel at runtime.  Default: .rapidActingAdult.

import Foundation
import LoopAlgorithm

public struct EvalInsulinDose: InsulinDose, Codable, Sendable {
    public var deliveryType: InsulinDeliveryType
    public var startDate: Date
    public var endDate: Date
    public var volume: Double

    /// Serialization-friendly model identifier.
    public var insulinType: ExponentialInsulinModelPreset

    /// Conforms to InsulinDose — derived at runtime from insulinType.
    public var insulinModel: InsulinModel { insulinType.model }

    public init(
        deliveryType: InsulinDeliveryType,
        startDate: Date,
        endDate: Date,
        volume: Double,
        insulinType: ExponentialInsulinModelPreset = .rapidActingAdult
    ) {
        self.deliveryType = deliveryType
        self.startDate    = startDate
        self.endDate      = endDate
        self.volume       = volume
        self.insulinType  = insulinType
    }
}
