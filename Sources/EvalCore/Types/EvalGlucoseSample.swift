// EvalGlucoseSample.swift — concrete GlucoseSampleValue conforming type
//
// LoopQuantity is NOT Codable, so we use a custom Codable implementation:
// - quantity  →  encoded as Double (mg/dL)
// - trendRate →  encoded as Double? (mg/dL per minute)

import Foundation
import LoopAlgorithm

public struct EvalGlucoseSample: GlucoseSampleValue, Codable, Sendable {
    public var startDate: Date
    public var quantity: LoopQuantity

    /// When the CONTROLLER first held this sample — nil means "at `startDate`".
    ///
    /// A CGM reading's timestamp is when the sensor took it, not when Loop received it;
    /// a delayed reading can arrive minutes late, and deployed Loop decides on whatever
    /// it holds (proven: bddp11 2026-06-15 21:37, Loop anchored a 5-min-old sample while
    /// the fresh one existed — heartbeat-triggered loop, reading in transit). Decision
    /// visibility gates on this field (like a carb's `entryDate`); the sample's physical
    /// reality — counter physics, scoring — always uses `startDate`. Today only
    /// detected-stale samples are post-dated by the ETL; a future dataset that records
    /// true arrival times (e.g. a Loop change) plugs in with no further sim work.
    public var receivedDate: Date?
    public var provenanceIdentifier: String
    public var isDisplayOnly: Bool
    public var wasUserEntered: Bool
    public var condition: GlucoseCondition?
    public var trendRate: LoopQuantity?

    public init(
        startDate: Date,
        quantity: LoopQuantity,
        provenanceIdentifier: String = "com.evalcore",
        isDisplayOnly: Bool = false,
        wasUserEntered: Bool = false,
        condition: GlucoseCondition? = nil,
        trendRate: LoopQuantity? = nil,
        receivedDate: Date? = nil
    ) {
        self.receivedDate = receivedDate
        self.startDate = startDate
        self.quantity = quantity
        self.provenanceIdentifier = provenanceIdentifier
        self.isDisplayOnly = isDisplayOnly
        self.wasUserEntered = wasUserEntered
        self.condition = condition
        self.trendRate = trendRate
    }

    // MARK: – Codable

    private enum CodingKeys: String, CodingKey {
        case startDate
        case receivedDate
        case quantity       // stored as mg/dL
        case provenanceIdentifier
        case isDisplayOnly
        case wasUserEntered
        case condition
        case trendRate      // stored as mg/dL/min
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        startDate           = try c.decode(Date.self, forKey: .startDate)
        receivedDate        = try c.decodeIfPresent(Date.self, forKey: .receivedDate)
        let mgdL            = try c.decode(Double.self, forKey: .quantity)
        quantity            = LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: mgdL)
        provenanceIdentifier = try c.decodeIfPresent(String.self, forKey: .provenanceIdentifier) ?? "com.evalcore"
        isDisplayOnly       = try c.decodeIfPresent(Bool.self, forKey: .isDisplayOnly) ?? false
        wasUserEntered      = try c.decodeIfPresent(Bool.self, forKey: .wasUserEntered) ?? false
        condition           = try c.decodeIfPresent(GlucoseCondition.self, forKey: .condition)
        if let trendMgdLPerMin = try c.decodeIfPresent(Double.self, forKey: .trendRate) {
            trendRate = LoopQuantity(unit: .milligramsPerDeciliterPerMinute, doubleValue: trendMgdLPerMin)
        } else {
            trendRate = nil
        }
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(startDate, forKey: .startDate)
        try c.encodeIfPresent(receivedDate, forKey: .receivedDate)
        try c.encode(quantity.doubleValue(for: .milligramsPerDeciliter), forKey: .quantity)
        if provenanceIdentifier != "com.evalcore" {
            try c.encode(provenanceIdentifier, forKey: .provenanceIdentifier)
        }
        if isDisplayOnly  { try c.encode(isDisplayOnly,  forKey: .isDisplayOnly) }
        if wasUserEntered { try c.encode(wasUserEntered, forKey: .wasUserEntered) }
        try c.encodeIfPresent(condition, forKey: .condition)
        if let trendRate {
            try c.encode(trendRate.doubleValue(for: .milligramsPerDeciliterPerMinute), forKey: .trendRate)
        }
    }
}
