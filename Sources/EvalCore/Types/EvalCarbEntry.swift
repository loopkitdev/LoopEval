// EvalCarbEntry.swift — concrete CarbEntry conforming type
//
// CarbEntry extends SampleValue which requires:
//   startDate, endDate (default = startDate), quantity (LoopQuantity)
// Plus CarbEntry's own:
//   absorptionTime: TimeInterval?
//
// LoopQuantity is NOT Codable — we encode quantity as grams (Double).
//
// `entryDate` is when the user pressed save (used by the simulator for
// per-step visibility — Loop only "sees" a carb at time t if entryDate <= t).
// `startDate` is the meal time used for the absorption curve. Users can enter
// past or future meals, so the two can differ.

import Foundation
import LoopAlgorithm

public struct EvalCarbEntry: CarbEntry, Codable, Sendable {
    public var startDate: Date                  // meal time (drives absorption)
    public var entryDate: Date                  // when user logged the entry (drives visibility)
    public var quantity: LoopQuantity           // grams
    public var absorptionTime: TimeInterval?
    public var foodType: String?

    public init(
        startDate: Date,
        entryDate: Date? = nil,
        quantity: LoopQuantity,
        absorptionTime: TimeInterval? = nil,
        foodType: String? = nil
    ) {
        self.startDate      = startDate
        self.entryDate      = entryDate ?? startDate
        self.quantity       = quantity
        self.absorptionTime = absorptionTime
        self.foodType       = foodType
    }

    // MARK: – Codable

    private enum CodingKeys: String, CodingKey {
        case startDate
        case entryDate
        case grams
        case absorptionTime
        case foodType
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        startDate      = try c.decode(Date.self, forKey: .startDate)
        // Backward compat: older caches don't have entryDate. Fall back to
        // startDate (treats as concurrent entry — matches the pre-fix behavior).
        entryDate      = (try? c.decode(Date.self, forKey: .entryDate)) ?? startDate
        let grams      = try c.decode(Double.self, forKey: .grams)
        quantity       = LoopQuantity(unit: .gram, doubleValue: grams)
        absorptionTime = try c.decodeIfPresent(TimeInterval.self, forKey: .absorptionTime)
        foodType       = try c.decodeIfPresent(String.self, forKey: .foodType)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(startDate, forKey: .startDate)
        try c.encode(entryDate, forKey: .entryDate)
        try c.encode(quantity.doubleValue(for: .gram), forKey: .grams)
        try c.encodeIfPresent(absorptionTime, forKey: .absorptionTime)
        try c.encodeIfPresent(foodType, forKey: .foodType)
    }
}
