// JSONFileDataSource.swift — file-based EvalDataSource for testing
//
// Loads pre-saved JSON files from a directory.  Useful for offline testing or
// replaying cached data without a live Nightscout connection.
//
// Expected files in `baseURL/`:
//   glucose.json   → [EvalGlucoseSample]
//   doses.json     → [EvalInsulinDose]
//   carbs.json     → [EvalCarbEntry]
//   therapy.json   → TherapySettings  (TherapyTimeline)
//
// All files use iso8601 date encoding (same as DataCache).

import Foundation
import LoopAlgorithm

public struct JSONFileDataSource: EvalDataSource {

    // MARK: – Properties

    /// Directory containing the JSON files.
    public let baseURL: URL

    // MARK: – Init

    public init(baseURL: URL) {
        self.baseURL = baseURL
    }

    // MARK: – EvalDataSource

    public func getGlucoseValues(interval: DateInterval) async throws -> [EvalGlucoseSample] {
        let all: [EvalGlucoseSample] = try load(file: "glucose.json")
        return all.filter { interval.contains($0.startDate) }
    }

    public func getDoses(interval: DateInterval) async throws -> [EvalInsulinDose] {
        let all: [EvalInsulinDose] = try load(file: "doses.json")
        return all.filter { interval.contains($0.startDate) || interval.contains($0.endDate) }
    }

    public func getCarbEntries(interval: DateInterval) async throws -> [EvalCarbEntry] {
        let all: [EvalCarbEntry] = try load(file: "carbs.json")
        return all.filter { interval.contains($0.startDate) }
    }

    public func getTherapyTimeline(interval: DateInterval) async throws -> TherapyTimeline {
        return try load(file: "therapy.json")
    }

    // MARK: – Private helpers

    private func load<T: Decodable>(file: String) throws -> T {
        let url = baseURL.appendingPathComponent(file)
        let data = try Data(contentsOf: url)
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(T.self, from: data)
    }
}
