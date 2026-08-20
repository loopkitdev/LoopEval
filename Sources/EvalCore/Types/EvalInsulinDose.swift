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

    /// When the CONTROLLER first held this record — nil means "at startDate".
    ///
    /// Loop knows a dose it COMMANDED immediately, but a POD-INITIATED event (suspend,
    /// occlusion stop) only when the pod reports back — bddp11 2026-07-04 00:15: a 106 s
    /// pump suspend started 18 s BEFORE a decision whose record was created 90 s AFTER
    /// it; Loop's flat forecast was faithful to a store that still held the running
    /// 0.8 temp, while the replay projected the not-yet-known suspension 30 min forward
    /// (+15.8 mg/dL, the night's worst cycle). Decision input excludes doses with
    /// receivedDate > t; physics/scoring keep startDate. Same causality rule as
    /// EvalGlucoseSample.receivedDate and the carb dosingVisibleDate.
    public var receivedDate: Date?

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
        tempRate: Double? = nil,
        receivedDate: Date? = nil
    ) {
        self.receivedDate = receivedDate
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
        receivedDate = try c.decodeIfPresent(Date.self,       forKey: .receivedDate)
    }
}
