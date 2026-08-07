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

    /// Whether this dose was automatically delivered by Loop (true) or entered
    /// manually by the user (false). Used by drift analysis to compare only the
    /// automated decisions: manual boluses must appear identically on both
    /// sides of a baseline-vs-candidate comparison, so they cancel out.
    /// Defaults to true when absent (older caches / non-Loop data sources).
    public var automatic: Bool

    /// Programmed temp-basal rate (U/hr) for `.basal` doses. Preserved so an
    /// in-progress temp basal (the one running at a forecast instant) can be
    /// recreated as `rate × elapsed` and clipped at t — the finalized record's
    /// pulse-quantized `volume` (delivered `amount`) under-reports the elapsed
    /// delivery of the still-running temp the previous loop enacted. nil for
    /// boluses / older caches.
    public var tempRate: Double?

    /// Conforms to InsulinDose — derived at runtime from insulinType.
    public var insulinModel: InsulinModel { insulinType.model }

    public init(
        deliveryType: InsulinDeliveryType,
        startDate: Date,
        endDate: Date,
        volume: Double,
        insulinType: ExponentialInsulinModelPreset = .rapidActingAdult,
        automatic: Bool = true,
        tempRate: Double? = nil
    ) {
        self.deliveryType = deliveryType
        self.startDate    = startDate
        self.endDate      = endDate
        self.volume       = volume
        self.insulinType  = insulinType
        self.automatic    = automatic
        self.tempRate     = tempRate
    }

    // Custom decoder so existing caches (written before the `automatic` field
    // was added) decode cleanly, defaulting to automatic=true.
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        deliveryType = try c.decode(InsulinDeliveryType.self, forKey: .deliveryType)
        startDate    = try c.decode(Date.self,                forKey: .startDate)
        endDate      = try c.decode(Date.self,                forKey: .endDate)
        volume       = try c.decode(Double.self,              forKey: .volume)
        insulinType  = try c.decode(ExponentialInsulinModelPreset.self, forKey: .insulinType)
        automatic    = try c.decodeIfPresent(Bool.self,       forKey: .automatic) ?? true
        tempRate     = try c.decodeIfPresent(Double.self,     forKey: .tempRate)
    }
}
