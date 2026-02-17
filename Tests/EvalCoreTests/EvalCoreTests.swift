// EvalCoreTests.swift — Phase 1: fixture round-trip test
//
// Loads live_capture_input.json using the LoopPredictionInput decoder (same
// types used in the canonical LoopAlgorithmTests), calls generatePrediction(),
// and compares to live_capture_predicted_glucose.json.

import Testing
import Foundation
@testable import EvalCore
import LoopAlgorithm

// MARK: – Helper

private func fixtureURL(_ name: String, ext: String = "json") throws -> URL {
    // Try Bundle.module first (SPM test resource bundle)
    if let url = Bundle.module.url(forResource: name, withExtension: ext, subdirectory: "Fixtures") {
        return url
    }
    // Fallback: look relative to this source file (useful during local dev)
    let fileURL = URL(fileURLWithPath: #file)
        .deletingLastPathComponent()
        .appendingPathComponent("Fixtures/\(name).\(ext)")
    guard FileManager.default.fileExists(atPath: fileURL.path) else {
        throw CocoaError(.fileNoSuchFile, userInfo: [NSFilePathErrorKey: fileURL.path])
    }
    return fileURL
}

// MARK: – Phase 1: EvalCore type smoke tests

@Test("EvalConfig defaults are sane")
func evalConfigDefaults() {
    let cfg = EvalConfig.default
    #expect(cfg.evalStep == 300)
    #expect(cfg.horizons.count == 12)   // 30, 60, … 360 min
    #expect(cfg.horizons.first == 1800)
    #expect(cfg.horizons.last  == 21600)
    #expect(!cfg.useIntegralRC)
    #expect(cfg.kalmanSmoothing)
}

@Test("EvalConfig round-trips through JSON")
func evalConfigCodable() throws {
    let original = EvalConfig.default
    let data     = try JSONEncoder().encode(original)
    let decoded  = try JSONDecoder().decode(EvalConfig.self, from: data)
    #expect(decoded.evalStep == original.evalStep)
    #expect(decoded.horizons == original.horizons)
    #expect(decoded.useIntegralRC == original.useIntegralRC)
}

@Test("EvalGlucoseSample round-trips through JSON")
func evalGlucoseSampleCodable() throws {
    let sample = EvalGlucoseSample(
        startDate: Date(timeIntervalSince1970: 1_700_000_000),
        quantity:  LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: 145.5),
        provenanceIdentifier: "test",
        isDisplayOnly: false,
        wasUserEntered: false,
        condition: nil,
        trendRate: LoopQuantity(unit: .milligramsPerDeciliterPerMinute, doubleValue: 1.2)
    )
    let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
    let decoder = JSONDecoder(); decoder.dateDecodingStrategy = .iso8601
    let data    = try encoder.encode(sample)
    let decoded = try decoder.decode(EvalGlucoseSample.self, from: data)

    #expect(decoded.startDate == sample.startDate)
    #expect(abs(decoded.quantity.doubleValue(for: .milligramsPerDeciliter) - 145.5) < 0.001)
    #expect(abs(decoded.trendRate!.doubleValue(for: .milligramsPerDeciliterPerMinute) - 1.2) < 0.001)
}

@Test("EvalInsulinDose round-trips through JSON")
func evalInsulinDoseCodable() throws {
    let start = Date(timeIntervalSince1970: 1_700_000_000)
    let dose  = EvalInsulinDose(
        deliveryType: .bolus,
        startDate: start,
        endDate: start.addingTimeInterval(30),
        volume: 2.5,
        insulinType: .fiasp
    )
    let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
    let decoder = JSONDecoder(); decoder.dateDecodingStrategy = .iso8601
    let data    = try encoder.encode(dose)
    let decoded = try decoder.decode(EvalInsulinDose.self, from: data)

    #expect(decoded.deliveryType == .bolus)
    #expect(abs(decoded.volume - 2.5) < 0.001)
    #expect(decoded.insulinType == .fiasp)
    // insulinModel is derived — check effectDuration is non-zero
    #expect(decoded.insulinModel.effectDuration > 0)
}

@Test("EvalCarbEntry round-trips through JSON")
func evalCarbEntryCodable() throws {
    let entry = EvalCarbEntry(
        startDate: Date(timeIntervalSince1970: 1_700_000_000),
        quantity: LoopQuantity(unit: .gram, doubleValue: 45),
        absorptionTime: 10800,
        foodType: "pizza"
    )
    let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
    let decoder = JSONDecoder(); decoder.dateDecodingStrategy = .iso8601
    let data    = try encoder.encode(entry)
    let decoded = try decoder.decode(EvalCarbEntry.self, from: data)

    #expect(abs(decoded.quantity.doubleValue(for: .gram) - 45) < 0.001)
    #expect(decoded.absorptionTime == 10800)
    #expect(decoded.foodType == "pizza")
}

// MARK: – Phase 1: Algorithm fixture round-trip

/// Loads live_capture_input.json → calls generatePrediction() → compares to
/// live_capture_predicted_glucose.json.  Values must match within 0.025 mg/dL
/// (same tolerance used internally in LoopAlgorithmTests).
@Test("Live capture fixture round-trip")
func liveCaptureRoundTrip() async throws {
    let decoder = JSONDecoder()
    decoder.dateDecodingStrategy = .iso8601

    // 1. Load fixture input (uses LoopPredictionInput decoder for this fixture format)
    let inputURL = try fixtureURL("live_capture_input")
    let input    = try decoder.decode(
        LoopPredictionInput<FixtureCarbEntry, FixtureGlucoseSample, FixtureInsulinDose>.self,
        from: Data(contentsOf: inputURL)
    )

    // 2. Run prediction
    let predictionStart = input.glucoseHistory.last?.startDate ?? Date()
    let prediction = LoopAlgorithm.generatePrediction(
        start:         predictionStart,
        glucoseHistory: input.glucoseHistory,
        doses:         input.doses,
        carbEntries:   input.carbEntries,
        basal:         input.basal,
        sensitivity:   input.sensitivity,
        carbRatio:     input.carbRatio,
        useIntegralRetrospectiveCorrection: input.useIntegralRetrospectiveCorrection
    )

    // 3. Load expected output
    let expectedURL = try fixtureURL("live_capture_predicted_glucose")
    let expected    = try decoder.decode([PredictedGlucoseValue].self, from: Data(contentsOf: expectedURL))

    // 4. Compare
    #expect(prediction.glucose.count == expected.count,
            "Glucose count mismatch: got \(prediction.glucose.count), expected \(expected.count)")

    let accuracy = 1.0 / 40.0   // same as LoopAlgorithmTests
    for (idx, (calc, exp)) in zip(prediction.glucose, expected).enumerated() {
        let calcMgdL = calc.quantity.doubleValue(for: .milligramsPerDeciliter)
        let expMgdL  = exp.quantity.doubleValue(for: .milligramsPerDeciliter)
        #expect(calc.startDate == exp.startDate,
                "startDate mismatch at index \(idx): \(calc.startDate) vs \(exp.startDate)")
        #expect(abs(calcMgdL - expMgdL) <= accuracy,
                "Glucose mismatch at index \(idx): \(calcMgdL) vs \(expMgdL) (diff \(abs(calcMgdL - expMgdL)))")
    }
}
