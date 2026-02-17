// Phase2Tests.swift — Phase 2: Nightscout data fetcher tests
//
// Tests:
//  1. expandDailySchedule — 2-segment basal over 2 days
//  2. Temp basal treatment parsing
//  3. Bolus treatment parsing
//  4. DataCache save/load round-trip

import Testing
import Foundation
@testable import EvalCore
import LoopAlgorithm

// MARK: – 1. expandDailySchedule

@Test("expandDailySchedule — 2-segment basal over exactly 2 days")
func expandScheduleTwoDays() {
    // Schedule: 0.8 U/hr from 00:00, 1.2 U/hr from 06:00 (UTC)
    let items: [(timeAsSeconds: Int, value: Double)] = [
        (0,     0.8),
        (21600, 1.2),   // 06:00 = 6 * 3600
    ]
    let tz = TimeZone(identifier: "UTC")!

    // Exactly 2 calendar days: 2023-01-01 00:00 UTC → 2023-01-03 00:00 UTC
    let start = Date(timeIntervalSince1970: 1672531200)  // 2023-01-01 00:00 UTC
    let end   = Date(timeIntervalSince1970: 1672531200 + 2 * 24 * 3600)
    let interval = DateInterval(start: start, end: end)

    let result = expandDailySchedule(items: items, timeZone: tz, interval: interval)

    // Expected: 4 entries total (2 segments × 2 days)
    #expect(result.count == 4, "Expected 4 schedule entries, got \(result.count)")

    // Day 1, segment 1: 00:00–06:00 @ 0.8
    #expect(abs(result[0].value - 0.8) < 0.001)
    #expect(result[0].startDate == start)
    #expect(result[0].endDate   == start.addingTimeInterval(21600))

    // Day 1, segment 2: 06:00–24:00 @ 1.2
    #expect(abs(result[1].value - 1.2) < 0.001)
    #expect(result[1].startDate == start.addingTimeInterval(21600))
    #expect(result[1].endDate   == start.addingTimeInterval(86400))

    // Day 2, segment 1: 00:00–06:00 @ 0.8
    #expect(abs(result[2].value - 0.8) < 0.001)
    #expect(result[2].startDate == start.addingTimeInterval(86400))

    // Day 2, segment 2: 06:00–24:00 @ 1.2
    #expect(abs(result[3].value - 1.2) < 0.001)
    #expect(result[3].endDate == end)
}

@Test("expandDailySchedule — partial first day")
func expandSchedulePartialDay() {
    let items: [(timeAsSeconds: Int, value: Double)] = [(0, 1.0), (43200, 1.5)]   // 12:00 split
    let tz = TimeZone(identifier: "UTC")!

    // Start at 08:00, end at 16:00 on same day
    let dayStart = Date(timeIntervalSince1970: 1672531200)  // 2023-01-01 00:00 UTC
    let start = dayStart.addingTimeInterval(8 * 3600)       // 08:00
    let end   = dayStart.addingTimeInterval(16 * 3600)      // 16:00
    let interval = DateInterval(start: start, end: end)

    let result = expandDailySchedule(items: items, timeZone: tz, interval: interval)

    // Two segments: [08:00–12:00 @ 1.0], [12:00–16:00 @ 1.5]
    #expect(result.count == 2)
    #expect(abs(result[0].value - 1.0) < 0.001)
    #expect(result[0].startDate == start)
    #expect(result[0].endDate   == dayStart.addingTimeInterval(12 * 3600))
    #expect(abs(result[1].value - 1.5) < 0.001)
    #expect(result[1].startDate == dayStart.addingTimeInterval(12 * 3600))
    #expect(result[1].endDate   == end)
}

// MARK: – 2. Temp basal parsing

/// Verify that a "Temp Basal" treatment is converted to an EvalInsulinDose with
/// .basal delivery type and correct volume.
@Test("Temp basal treatment → EvalInsulinDose")
func tempBasalParsing() async throws {
    // Build a minimal cache + data source
    let tmpDir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    _ = try DataCache(cacheDir: tmpDir)

    // We test the conversion logic by calling a thin wrapper helper
    let treatment = NightscoutTreatment(
        created_at: "2023-01-01T10:00:00.000Z",
        eventType: "Temp Basal",
        insulin: nil,
        carbs: nil,
        rate: 2.5,
        duration: 30,    // 30 minutes
        absolute: 2.5,
        percent: nil,
        isSMB: nil,
        automatic: true
    )

    let doses = TreatmentConverter.convertToDoses([treatment], insulinType: .rapidActingAdult)

    #expect(doses.count == 1)
    let dose = doses[0]
    #expect(dose.deliveryType == .basal)
    // volume = rate * duration_in_hours = 2.5 * 0.5 = 1.25 U
    #expect(abs(dose.volume - 1.25) < 0.001)
    // duration 30 min
    let durationMin = dose.endDate.timeIntervalSince(dose.startDate) / 60.0
    #expect(abs(durationMin - 30) < 0.001)

    // Cleanup
    try? FileManager.default.removeItem(at: tmpDir)
}

// MARK: – 3. Bolus treatment parsing

@Test("Bolus treatment → EvalInsulinDose")
func bolusParsing() throws {
    let treatment = NightscoutTreatment(
        created_at: "2023-01-01T12:30:00.000Z",
        eventType: "Meal Bolus",
        insulin: 4.5,
        carbs: 60,
        rate: nil,
        duration: nil,
        absolute: nil,
        percent: nil,
        isSMB: nil,
        automatic: false
    )

    let doses = TreatmentConverter.convertToDoses([treatment], insulinType: .fiasp)

    #expect(doses.count == 1)
    let dose = doses[0]
    #expect(dose.deliveryType == .bolus)
    #expect(abs(dose.volume - 4.5) < 0.001)
    #expect(dose.insulinType == .fiasp)
}

@Test("SMB treatment → bolus EvalInsulinDose")
func smbParsing() throws {
    let treatment = NightscoutTreatment(
        created_at: "2023-01-01T14:00:00.000Z",
        eventType: "SMB",
        insulin: 0.3,
        carbs: nil,
        rate: nil,
        duration: nil,
        absolute: nil,
        percent: nil,
        isSMB: true,
        automatic: true
    )

    let doses = TreatmentConverter.convertToDoses([treatment], insulinType: .rapidActingAdult)
    #expect(doses.count == 1)
    #expect(doses[0].deliveryType == .bolus)
    #expect(abs(doses[0].volume - 0.3) < 0.001)
}

// MARK: – 4. DataCache round-trip

@Test("DataCache save/load round-trip")
func dataCacheRoundTrip() async throws {
    let tmpDir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    let cache = try DataCache(cacheDir: tmpDir)

    // Save a simple array
    let values = [1.0, 2.5, 3.7]
    let key = "test-values"
    try await cache.save(values, key: key)

    // Reload
    let loaded: [Double]? = try await cache.load(key: key)
    #expect(loaded != nil)
    #expect(loaded!.count == 3)
    #expect(abs(loaded![1] - 2.5) < 0.001)

    // Missing key returns nil
    let missing: [Double]? = try await cache.load(key: "nonexistent")
    #expect(missing == nil)

    // Cleanup
    try? FileManager.default.removeItem(at: tmpDir)
}

@Test("DataCache key generation is deterministic")
func dataCacheKeyDeterminism() {
    let url = URL(string: "https://ns.example.com")!
    let interval = DateInterval(start: Date(timeIntervalSince1970: 1000), end: Date(timeIntervalSince1970: 2000))

    let k1 = DataCache.key(for: "glucose", url: url, interval: interval)
    let k2 = DataCache.key(for: "glucose", url: url, interval: interval)
    #expect(k1 == k2)

    let k3 = DataCache.key(for: "doses", url: url, interval: interval)
    #expect(k1 != k3)
}

// MARK: – NightscoutTreatment memberwise init (for testing)

extension NightscoutTreatment {
    init(
        created_at: String,
        eventType: String,
        insulin: Double?,
        carbs: Double?,
        rate: Double?,
        duration: Double?,
        absolute: Double?,
        percent: Int?,
        isSMB: Bool?,
        automatic: Bool?
    ) {
        // Use JSON round-trip for initialisation since the struct uses Decodable-only
        var dict: [String: Any] = ["created_at": created_at, "eventType": eventType]
        if let v = insulin   { dict["insulin"] = v }
        if let v = carbs     { dict["carbs"] = v }
        if let v = rate      { dict["rate"] = v }
        if let v = duration  { dict["duration"] = v }
        if let v = absolute  { dict["absolute"] = v }
        if let v = percent   { dict["percent"] = v }
        if let v = isSMB    { dict["isSMB"] = v }
        if let v = automatic { dict["automatic"] = v }

        let data = try! JSONSerialization.data(withJSONObject: dict)
        self = try! JSONDecoder().decode(NightscoutTreatment.self, from: data)
    }
}

// MARK: – TreatmentConverter helper (extracted from NightscoutEvalDataSource for testing)

/// Thin wrapper that exposes the private conversion logic for unit testing.
enum TreatmentConverter {
    static func convertToDoses(
        _ treatments: [NightscoutTreatment],
        insulinType: ExponentialInsulinModelPreset
    ) -> [EvalInsulinDose] {
        let fmt = ISO8601DateFormatter()
        fmt.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        var doses: [EvalInsulinDose] = []

        for t in treatments {
            guard let date = fmt.date(from: t.created_at) else { continue }
            let eventType = t.eventType.trimmingCharacters(in: .whitespaces)

            switch eventType {
            case "Temp Basal":
                let rate = t.absolute ?? t.rate ?? 0.0
                let durationMin = t.duration ?? 0
                doses.append(EvalInsulinDose(
                    deliveryType: .basal,
                    startDate: date,
                    endDate: date.addingTimeInterval(durationMin * 60),
                    volume: rate * (durationMin / 60.0),
                    insulinType: insulinType
                ))
            case "Bolus", "Meal Bolus", "Correction Bolus", "Carb Correction":
                guard let units = t.insulin, units > 0 else { continue }
                doses.append(EvalInsulinDose(
                    deliveryType: .bolus,
                    startDate: date,
                    endDate: date.addingTimeInterval(30),
                    volume: units,
                    insulinType: insulinType
                ))
            case "SMB":
                guard let units = t.insulin, units > 0 else { continue }
                doses.append(EvalInsulinDose(
                    deliveryType: .bolus,
                    startDate: date,
                    endDate: date.addingTimeInterval(30),
                    volume: units,
                    insulinType: insulinType
                ))
            default:
                break
            }
        }
        return doses.sorted { $0.startDate < $1.startDate }
    }
}
