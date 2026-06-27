// EvalCarbEntry.swift — concrete CarbEntry conforming type
//
// CarbEntry extends SampleValue which requires:
//   startDate, endDate (default = startDate), quantity (LoopQuantity)
// Plus CarbEntry's own:
//   absorptionTime: TimeInterval?
//
// LoopQuantity is NOT Codable — we encode quantity as grams (Double).
//
// There are exactly TWO real timestamps for a carb:
//   • startDate — the MEAL TIME (when the food is eaten); drives the absorption curve.
//   • entryDate — the ENTRY TIME (when the user logged the carbs); the true moment
//     Loop learned about them (the ObjectId DB-insert time).
// They can differ: the user can log a past or future meal.
//
// `dosingVisibleDate` is NOT a third real time — it is a derived SIM gate equal to
// entryDate, optionally deferred slightly past a paired manual bolus so normal
// auto-dosing doesn't cover the meal in the log→bolus gap and then double-cover the
// passed-through manual bolus (see NightscoutEvalDataSource). NORMAL dosing gates
// visibility on `dosingVisibleDate`; the MANUAL-BOLUS recommendation uses the true
// `entryDate` (a carb co-logged with a bolus is visible to that bolus's own rec).

import Foundation
import LoopAlgorithm

public struct EvalCarbEntry: CarbEntry, Codable, Sendable {
    public var startDate: Date                  // MEAL TIME — when eaten (drives absorption)
    public var entryDate: Date                  // ENTRY TIME — when the carbs were logged (true)
    public var dosingVisibleDate: Date          // derived gate for NORMAL dosing (entryDate, possibly deferred past a paired bolus)
    public var quantity: LoopQuantity           // grams
    public var absorptionTime: TimeInterval?
    public var foodType: String?
    // Groups the time-ordered REVISIONS of a single logged meal (e.g. the user
    // logged 15g, then edited to 45g 35 min later). All revisions of one entry
    // share the same revisionKey (Loop's syncIdentifier) and the same startDate
    // (meal time), but carry different grams + visibility dates. The window
    // builder keeps only the LATEST revision visible at the decision time, so the
    // replay sees the carbs exactly as the deployed Loop saw them at each moment.
    // nil ⇒ a standalone entry (the common, non-edited case) — no collapsing.
    public var revisionKey: String?

    public init(
        startDate: Date,
        entryDate: Date? = nil,
        dosingVisibleDate: Date? = nil,
        quantity: LoopQuantity,
        absorptionTime: TimeInterval? = nil,
        foodType: String? = nil,
        revisionKey: String? = nil
    ) {
        self.startDate         = startDate
        self.entryDate         = entryDate ?? startDate
        self.dosingVisibleDate = dosingVisibleDate ?? entryDate ?? startDate
        self.quantity          = quantity
        self.absorptionTime    = absorptionTime
        self.foodType          = foodType
        self.revisionKey       = revisionKey
    }

    // MARK: – Codable

    private enum CodingKeys: String, CodingKey {
        case startDate
        case entryDate
        case dosingVisibleDate
        case grams
        case absorptionTime
        case foodType
        case revisionKey
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        startDate         = try c.decode(Date.self, forKey: .startDate)
        // Backward compat: older caches don't have entryDate; fall back to startDate.
        entryDate         = (try? c.decode(Date.self, forKey: .entryDate)) ?? startDate
        dosingVisibleDate = (try? c.decode(Date.self, forKey: .dosingVisibleDate)) ?? entryDate
        let grams         = try c.decode(Double.self, forKey: .grams)
        quantity          = LoopQuantity(unit: .gram, doubleValue: grams)
        absorptionTime    = try c.decodeIfPresent(TimeInterval.self, forKey: .absorptionTime)
        foodType          = try c.decodeIfPresent(String.self, forKey: .foodType)
        revisionKey       = try c.decodeIfPresent(String.self, forKey: .revisionKey)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(startDate, forKey: .startDate)
        try c.encode(entryDate, forKey: .entryDate)
        try c.encode(dosingVisibleDate, forKey: .dosingVisibleDate)
        try c.encode(quantity.doubleValue(for: .gram), forKey: .grams)
        try c.encodeIfPresent(absorptionTime, forKey: .absorptionTime)
        try c.encodeIfPresent(foodType, forKey: .foodType)
        try c.encodeIfPresent(revisionKey, forKey: .revisionKey)
    }
}
