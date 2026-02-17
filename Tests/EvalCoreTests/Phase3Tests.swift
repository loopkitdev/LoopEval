// Phase3Tests.swift — Phase 3: Evaluation Engine tests

import Testing
import Foundation
@testable import EvalCore
import LoopAlgorithm

// MARK: – Helpers

/// T = 2023-06-23T00:00:00Z — reference time used across tests
private let T = Date(timeIntervalSince1970: 1687478400)  // 2023-06-23T00:00:00Z

private func glucose(at date: Date, mgdL: Double = 120) -> EvalGlucoseSample {
    EvalGlucoseSample(
        startDate: date,
        quantity:  LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: mgdL)
    )
}

private func dose(
    startOffset: TimeInterval,
    endOffset: TimeInterval,
    type: InsulinDeliveryType = .basal,
    volume: Double = 0.4
) -> EvalInsulinDose {
    EvalInsulinDose(
        deliveryType: type,
        startDate: T.addingTimeInterval(startOffset),
        endDate:   T.addingTimeInterval(endOffset),
        volume:    volume
    )
}

/// Build a simple TherapyTimeline spanning `startOffset` to `endOffset` relative to T.
private func makeTimeline(
    startOffset: TimeInterval = -16 * 3600,
    endOffset:   TimeInterval =  8 * 3600,
    isfValue:    Double = 60,
    isfEndOffset: TimeInterval? = nil
) -> TherapyTimeline {
    let tStart = T.addingTimeInterval(startOffset)
    let tEnd   = T.addingTimeInterval(endOffset)
    let isfEnd = T.addingTimeInterval(isfEndOffset ?? endOffset)

    return TherapySettings(
        basal: [AbsoluteScheduleValue(startDate: tStart, endDate: tEnd, value: 0.8)],
        sensitivity: [AbsoluteScheduleValue(
            startDate: tStart,
            endDate: isfEnd,
            value: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: isfValue)
        )],
        carbRatio: [AbsoluteScheduleValue(startDate: tStart, endDate: tEnd, value: 11.0)],
        target: [AbsoluteScheduleValue(
            startDate: tStart,
            endDate: tEnd,
            value: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: 90)...LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: 110)
        )],
        suspendThreshold: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: 70),
        maxBolus: 10.0,
        maxBasalRate: 4.0
    )
}

/// Dense glucose readings every 5 min from `startOffset` to `endOffset` relative to T.
private func denseGlucose(
    startOffset: TimeInterval,
    endOffset: TimeInterval,
    mgdL: Double = 120
) -> [EvalGlucoseSample] {
    var readings: [EvalGlucoseSample] = []
    var t = T.addingTimeInterval(startOffset)
    let end = T.addingTimeInterval(endOffset)
    while t <= end {
        readings.append(glucose(at: t, mgdL: mgdL))
        t = t.addingTimeInterval(5 * 60)
    }
    return readings
}

// MARK: – 1. Glucose window slicing

@Test("InputWindowBuilder slices glucose to glucoseLookbackHours window")
func inputBuilderGlucoseWindow() {
    // Readings span T-12h to T (one every 5 min)
    let readings = denseGlucose(startOffset: -12 * 3600, endOffset: 0)

    let config   = EvalConfig(glucoseLookbackHours: 10)
    let builder  = InputWindowBuilder(
        glucose: readings,
        doses: [],
        carbs: [],
        therapyTimeline: makeTimeline(),
        config: config
    )

    let input = builder.buildInput(at: T)
    #expect(input != nil, "Expected a non-nil PredictionInput")

    guard let input else { return }
    let cutoff = T.addingTimeInterval(-10 * 3600)

    // All readings should be within the 10-hour window
    #expect(input.glucose.allSatisfy { $0.startDate >= cutoff && $0.startDate <= T },
            "Glucose slice should be bounded to T-10h...T")

    // Readings before T-10h should be excluded
    let excludedCount = readings.filter { $0.startDate < cutoff }.count
    #expect(excludedCount > 0,
            "Pre-condition: there must be readings before T-10h to exclude")
    #expect(!input.glucose.contains(where: { $0.startDate < cutoff }),
            "Readings before T-10h must not appear in the slice")
}

// MARK: – 2. ISF extension to t+8h

@Test("InputWindowBuilder extends ISF to t+8h even when timeline ends earlier")
func inputBuilderISFExtension() {
    // Timeline ISF ends at T+4h (less than the required T+8h)
    let timeline = makeTimeline(startOffset: -16 * 3600, endOffset: 8 * 3600, isfEndOffset: 4 * 3600)

    let readings = denseGlucose(startOffset: -10 * 3600, endOffset: 0)
    let builder  = InputWindowBuilder(
        glucose: readings,
        doses: [],
        carbs: [],
        therapyTimeline: timeline,
        config: EvalConfig()
    )

    let input = builder.buildInput(at: T)
    #expect(input != nil)

    guard let input else { return }
    let required = T.addingTimeInterval(8 * 3600)
    let lastISFEnd = input.sensitivity.last?.endDate ?? .distantPast
    #expect(lastISFEnd >= required,
            "ISF must cover at least T+8h; got \(lastISFEnd), need \(required)")
}

// MARK: – 3. Future insulin inclusion

@Test("InputWindowBuilder includes future doses when includeFutureInsulin = true")
func inputBuilderFutureInsulin() {
    // Dose at T+2h (future of evaluation time T)
    let futureDose = dose(startOffset: 2 * 3600, endOffset: 2 * 3600 + 30, type: .bolus, volume: 1.0)
    let pastDose   = dose(startOffset: -2 * 3600, endOffset: -2 * 3600 + 30, type: .bolus, volume: 0.5)

    let readings = denseGlucose(startOffset: -10 * 3600, endOffset: 0)
    let configWithFuture = EvalConfig(includeFutureInsulin: true)
    let configNoFuture   = EvalConfig(includeFutureInsulin: false)

    let builderFuture = InputWindowBuilder(
        glucose: readings,
        doses: [pastDose, futureDose],
        carbs: [],
        therapyTimeline: makeTimeline(),
        config: configWithFuture
    )
    let builderNoFuture = InputWindowBuilder(
        glucose: readings,
        doses: [pastDose, futureDose],
        carbs: [],
        therapyTimeline: makeTimeline(),
        config: configNoFuture
    )

    let inputFuture   = builderFuture.buildInput(at: T)
    let inputNoFuture = builderNoFuture.buildInput(at: T)

    #expect(inputFuture != nil)
    #expect(inputNoFuture != nil)

    // With future insulin enabled, the future dose should be present
    let futurePresent = inputFuture?.doses.contains(where: { $0.startDate > T }) ?? false
    #expect(futurePresent, "Future dose should appear when includeFutureInsulin = true")

    // Without future insulin, the future dose should be absent
    let futureAbsent = inputNoFuture?.doses.contains(where: { $0.startDate > T }) ?? true
    #expect(!futureAbsent, "Future dose must not appear when includeFutureInsulin = false")
}

// MARK: – 4. Nil on insufficient data

@Test("InputWindowBuilder returns nil when no recent glucose reading")
func inputBuilderNilOnStaleCGM() {
    // Last reading is at T-45min (more than 30 min ago → insufficient)
    let staleReadings = denseGlucose(startOffset: -10 * 3600, endOffset: -45 * 60)

    let builder = InputWindowBuilder(
        glucose: staleReadings,
        doses: [],
        carbs: [],
        therapyTimeline: makeTimeline(),
        config: EvalConfig()
    )

    let result = builder.buildInput(at: T)
    #expect(result == nil, "buildInput should return nil when newest glucose is >30 min old")
}

@Test("InputWindowBuilder returns nil when glucose array is empty")
func inputBuilderNilOnEmptyCGM() {
    let builder = InputWindowBuilder(
        glucose: [],
        doses: [],
        carbs: [],
        therapyTimeline: makeTimeline(),
        config: EvalConfig()
    )
    let result = builder.buildInput(at: T)
    #expect(result == nil, "buildInput should return nil when there is no glucose data")
}

// MARK: – 5. Engine integration test (fixture-based)

private func fixtureURL(_ name: String, ext: String = "json") throws -> URL {
    if let url = Bundle.module.url(forResource: name, withExtension: ext, subdirectory: "Fixtures") {
        return url
    }
    let fileURL = URL(fileURLWithPath: #file)
        .deletingLastPathComponent()
        .appendingPathComponent("Fixtures/\(name).\(ext)")
    guard FileManager.default.fileExists(atPath: fileURL.path) else {
        throw CocoaError(.fileNoSuchFile, userInfo: [NSFilePathErrorKey: fileURL.path])
    }
    return fileURL
}

@Test("EvaluationEngine produces predictions on fixture data")
func engineIntegrationTest() async throws {
    // Use the eval_fixtures directory via JSONFileDataSource
    let fixturesDir: URL
    if let url = Bundle.module.url(forResource: "eval_fixtures", withExtension: nil, subdirectory: "Fixtures") {
        fixturesDir = url
    } else {
        fixturesDir = URL(fileURLWithPath: #file)
            .deletingLastPathComponent()
            .appendingPathComponent("Fixtures/eval_fixtures")
    }
    guard FileManager.default.fileExists(atPath: fixturesDir.path) else {
        // Skip if fixtures don't exist (shouldn't happen)
        return
    }

    let dataSource = JSONFileDataSource(baseURL: fixturesDir)
    let engine     = EvaluationEngine(dataSource: dataSource)

    // Eval window: T to T+30min (7 steps at 5-min resolution)
    // T = 2023-06-23T00:00:00Z
    let start = T
    let end   = T.addingTimeInterval(30 * 60)
    let interval = DateInterval(start: start, end: end)

    // Use a class to safely capture progress across @Sendable boundary
    final class ProgressCapture: @unchecked Sendable {
        var values: [Double] = []
    }
    let capture = ProgressCapture()

    let result = try await engine.evaluate(
        interval: interval,
        config: EvalConfig(includeFutureInsulin: false)  // don't need future insulin
    ) { p in
        capture.values.append(p)
    }

    // Should have produced at least one prediction
    #expect(result.predictionCount > 0,
            "Engine must produce at least one prediction; got skipped=\(result.skippedCount)")

    // Progress should have been reported
    #expect(!capture.values.isEmpty, "Progress callback should have been called")
    #expect(capture.values.last == 1.0, "Final progress must be 1.0")

    // Each prediction should have glucose values
    for record in result.predictions {
        #expect(!record.predicted.isEmpty,
                "Prediction at \(record.evaluatedAt) must not be empty")
    }
}

// MARK: – 6. PredictionRecord interpolation

@Test("PredictionRecord.predictedValue interpolates correctly at horizon midpoints")
func predictionRecordInterpolation() {
    // Build a simple two-point prediction: 100 mg/dL at T, 140 mg/dL at T+30min
    let p0 = PredictedGlucoseValue(
        startDate: T,
        quantity: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: 100)
    )
    let p1 = PredictedGlucoseValue(
        startDate: T.addingTimeInterval(30 * 60),
        quantity: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: 140)
    )

    let record = PredictionRecord(evaluatedAt: T, predicted: [p0, p1])

    // At horizon 0 → should return 100
    let atZero = record.predictedValue(atHorizon: 0)
    #expect(atZero != nil)
    #expect(abs(atZero! - 100.0) < 0.001, "At horizon 0 expected 100, got \(atZero!)")

    // At horizon 30min → should return 140
    let atEnd = record.predictedValue(atHorizon: 30 * 60)
    #expect(atEnd != nil)
    #expect(abs(atEnd! - 140.0) < 0.001, "At horizon 30min expected 140, got \(atEnd!)")

    // At horizon 15min (midpoint) → linear interp → 120
    let atMid = record.predictedValue(atHorizon: 15 * 60)
    #expect(atMid != nil)
    #expect(abs(atMid! - 120.0) < 0.001, "At horizon 15min expected 120, got \(atMid!)")

    // At horizon 45min (beyond prediction) → nil
    let atBeyond = record.predictedValue(atHorizon: 45 * 60 + 5)  // beyond clamp window
    #expect(atBeyond == nil, "Beyond prediction range should return nil")
}

@Test("PredictionRecord.predictedValue returns nil for empty prediction")
func predictionRecordNilOnEmpty() {
    let record = PredictionRecord(evaluatedAt: T, predicted: [])
    let result = record.predictedValue(atHorizon: 30 * 60)
    #expect(result == nil)
}

// MARK: – 7. EvalConfig new fields have correct defaults

@Test("EvalConfig new Phase 3 fields have correct defaults")
func evalConfigPhase3Defaults() {
    let cfg = EvalConfig.default
    #expect(cfg.includingPositiveVelocityAndRC == true)
    #expect(cfg.useMidAbsorptionISF == false)
    #expect(cfg.carbAbsorptionModel == .piecewiseLinear)
}

@Test("EvalConfig new Phase 3 fields round-trip through JSON")
func evalConfigPhase3Codable() throws {
    var original = EvalConfig.default
    original.includingPositiveVelocityAndRC = false
    original.useMidAbsorptionISF = true
    original.carbAbsorptionModel = .piecewiseLinear

    let data    = try JSONEncoder().encode(original)
    let decoded = try JSONDecoder().decode(EvalConfig.self, from: data)

    #expect(decoded.includingPositiveVelocityAndRC == false)
    #expect(decoded.useMidAbsorptionISF == true)
    #expect(decoded.carbAbsorptionModel == .piecewiseLinear)
}
