// NightscoutClient.swift — minimal Nightscout v1 HTTP client
//
// Uses URLSession directly (no NightscoutKit dependency).
// Implements only the three endpoints needed for evaluation:
//   • /api/v1/entries.json   → [NightscoutEntry]
//   • /api/v1/treatments.json → [NightscoutTreatment]
//   • /api/v1/profile.json   → [NightscoutProfileRecord]
//
// Auth: SHA-1 hash of the API secret sent as the "api-secret" header,
// matching Nightscout's server-side expectation.

import Foundation
import CryptoKit

// MARK: – Raw Nightscout JSON models

/// A CGM/meter/calibration entry from /api/v1/entries.json
public struct NightscoutEntry: Decodable, Sendable {
    /// ISO8601 date string (e.g. "2023-01-15T12:00:00.000Z")
    public let dateString: String
    /// CGM value in mg/dL (present for type == "sgv")
    public let sgv: Int?
    /// Entry type: "sgv" (sensor glucose), "mbg" (meter BG), "cal" (calibration)
    public let type: String?
    /// Trend direction string (e.g. "Flat", "SingleUp", "FortyFiveUp")
    public let direction: String?
    /// Noise level (1–4; 4 == display-only / unreliable)
    public let noise: Int?

    private enum CodingKeys: String, CodingKey {
        case dateString, sgv, type, direction, noise
    }
}

/// A treatment record from /api/v1/treatments.json
public struct NightscoutTreatment: Decodable, Sendable {
    /// ISO8601 creation timestamp
    public let created_at: String
    /// Treatment type string (e.g. "Temp Basal", "Bolus", "Meal Bolus", "SMB")
    public let eventType: String
    /// Bolus amount in units
    public let insulin: Double?
    /// Carbohydrate amount in grams
    public let carbs: Double?
    /// Temp basal rate (may be relative %)
    public let rate: Double?
    /// Temp basal duration in minutes
    public let duration: Double?
    /// Absolute temp basal rate in U/hr
    public let absolute: Double?
    /// Relative temp basal percent (+/- of scheduled)
    public let percent: Int?
    /// Whether this was an SMB (Super Micro Bolus)
    public let isSMB: Bool?
    /// Whether this was an automatic (algorithm-driven) delivery
    public let automatic: Bool?

    private enum CodingKeys: String, CodingKey {
        case created_at, eventType, insulin, carbs, rate, duration,
             absolute, percent, isSMB, automatic
    }
}

/// One schedule item within a Nightscout profile
public struct NightscoutScheduleItem: Decodable, Sendable {
    public let time: String         // "HH:MM" string
    public let value: Double
    public let timeAsSeconds: Int   // seconds from midnight

    private enum CodingKeys: String, CodingKey {
        case time, value, timeAsSeconds
    }
}

/// A single Nightscout profile (basal, ISF, carb ratio, targets, timezone)
public struct NightscoutProfile: Decodable, Sendable {
    public let basal: [NightscoutScheduleItem]
    public let sens: [NightscoutScheduleItem]           // ISF (mg/dL/U or mmol/L/U)
    public let carbratio: [NightscoutScheduleItem]      // g/U
    public let target_low: [NightscoutScheduleItem]     // lower target (mg/dL or mmol/L)
    public let target_high: [NightscoutScheduleItem]    // upper target
    public let timezone: String?
    public let units: String?                           // "mg/dl" or "mmol"

    private enum CodingKeys: String, CodingKey {
        case basal, sens, carbratio, target_low, target_high, timezone, units
    }
}

/// The profile store returned by /api/v1/profile.json (array or single object)
public struct NightscoutProfileRecord: Decodable, Sendable {
    public let defaultProfile: String?
    public let startDate: String?
    public let store: [String: NightscoutProfile]?
    public let mills: String?   // creation timestamp in milliseconds (NS sends as String)
    public let units: String?   // top-level units (fallback if profile lacks units)

    private enum CodingKeys: String, CodingKey {
        case defaultProfile, startDate, store, mills, units
    }
}

// MARK: – Device status models

/// A device status record from /api/v1/devicestatus.json
public struct NightscoutDeviceStatus: Decodable, Sendable {
    public let created_at: String
    public let loop: NightscoutLoopStatus?
}

/// The `loop` object within a device status record.
public struct NightscoutLoopStatus: Decodable, Sendable {
    public let iob: NightscoutIOB?
    public let cob: NightscoutCOB?
    public let predicted: NightscoutPredicted?
}

/// IOB field within a Nightscout loop status.
public struct NightscoutIOB: Decodable, Sendable {
    public let iob: Double?
}

/// COB field within a Nightscout loop status.
public struct NightscoutCOB: Decodable, Sendable {
    public let cob: Double?
}

/// The predicted glucose curve within a Nightscout loop status.
public struct NightscoutPredicted: Decodable, Sendable {
    public let startDate: String
    public let values: [Double]
}

// MARK: – Client errors

public enum NightscoutClientError: Error, Sendable {
    case invalidURL
    case httpError(statusCode: Int)
    case emptyResponse
    case decodingError(underlying: Error)
}

// MARK: – NightscoutClient

/// Minimal Nightscout v1 HTTP client.
///
/// Create once; all methods are safe to call concurrently.
public struct NightscoutClient: Sendable {

    public let baseURL: URL
    private let apiSecretHash: String?  // SHA-1 hex of apiSecret

    // ISO8601 formatter for query parameters (shared; DateFormatter is not Sendable but
    // we construct fresh ones per call to avoid concurrency issues)
    private static func makeDateFormatter() -> ISO8601DateFormatter {
        let fmt = ISO8601DateFormatter()
        fmt.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return fmt
    }

    // MARK: – Init

    public init(baseURL: URL, apiSecret: String? = nil) {
        // Strip trailing slash
        var url = baseURL
        if url.absoluteString.hasSuffix("/") {
            url = url.deletingLastPathComponent()
        }
        self.baseURL = url
        if let secret = apiSecret, !secret.isEmpty {
            self.apiSecretHash = Self.sha1Hex(secret)
        } else {
            self.apiSecretHash = nil
        }
    }

    // MARK: – Public API

    /// Fetch CGM entries between `interval.start` and `interval.end`.
    public func fetchEntries(interval: DateInterval) async throws -> [NightscoutEntry] {
        let fmt = Self.makeDateFormatter()
        var components = URLComponents(url: baseURL.appendingPathComponent("api/v1/entries.json"),
                                       resolvingAgainstBaseURL: false)!
        components.queryItems = [
            URLQueryItem(name: "find[dateString][$gte]", value: fmt.string(from: interval.start)),
            URLQueryItem(name: "find[dateString][$lte]", value: fmt.string(from: interval.end)),
            URLQueryItem(name: "count", value: "500000"),
        ]
        guard let url = components.url else { throw NightscoutClientError.invalidURL }
        return try await fetchJSON([NightscoutEntry].self, from: url)
    }

    /// Fetch treatment records between `interval.start` and `interval.end`.
    public func fetchTreatments(interval: DateInterval) async throws -> [NightscoutTreatment] {
        let fmt = Self.makeDateFormatter()
        var components = URLComponents(url: baseURL.appendingPathComponent("api/v1/treatments.json"),
                                       resolvingAgainstBaseURL: false)!
        components.queryItems = [
            URLQueryItem(name: "find[created_at][$gte]", value: fmt.string(from: interval.start)),
            URLQueryItem(name: "find[created_at][$lte]", value: fmt.string(from: interval.end)),
            URLQueryItem(name: "count", value: "500000"),
        ]
        guard let url = components.url else { throw NightscoutClientError.invalidURL }
        return try await fetchJSON([NightscoutTreatment].self, from: url)
    }

    /// Fetch device status records between `from` and `to`.
    public func fetchDeviceStatus(from: Date, to: Date) async throws -> [NightscoutDeviceStatus] {
        let fmt = Self.makeDateFormatter()
        var components = URLComponents(url: baseURL.appendingPathComponent("api/v1/devicestatus.json"),
                                       resolvingAgainstBaseURL: false)!
        components.queryItems = [
            URLQueryItem(name: "find[created_at][$gte]", value: fmt.string(from: from)),
            URLQueryItem(name: "find[created_at][$lte]", value: fmt.string(from: to)),
            URLQueryItem(name: "count", value: "500000"),
        ]
        guard let url = components.url else { throw NightscoutClientError.invalidURL }
        return try await fetchJSON([NightscoutDeviceStatus].self, from: url)
    }

    /// Fetch the current profile store (returns the most recent profile record).
    public func fetchProfile() async throws -> NightscoutProfileRecord {
        let url = baseURL.appendingPathComponent("api/v1/profile.json")
        // Profile endpoint may return a single object or an array; try array first
        do {
            let records = try await fetchJSON([NightscoutProfileRecord].self, from: url)
            guard let first = records.first else { throw NightscoutClientError.emptyResponse }
            return first
        } catch {
            // Fall back to single-object response
            return try await fetchJSON(NightscoutProfileRecord.self, from: url)
        }
    }

    // MARK: – Private helpers

    private func fetchJSON<T: Decodable>(_ type: T.Type, from url: URL) async throws -> T {
        var request = URLRequest(url: url)
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let hash = apiSecretHash {
            request.setValue(hash, forHTTPHeaderField: "api-secret")
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            throw NightscoutClientError.httpError(statusCode: http.statusCode)
        }

        let decoder = JSONDecoder()
        do {
            return try decoder.decode(type, from: data)
        } catch {
            throw NightscoutClientError.decodingError(underlying: error)
        }
    }

    /// SHA-1 hex digest of a string, for Nightscout API secret auth.
    private static func sha1Hex(_ input: String) -> String {
        let data = Data(input.utf8)
        let digest = Insecure.SHA1.hash(data: data)
        return digest.map { String(format: "%02x", $0) }.joined()
    }
}

// MARK: – NsPrediction conversion

extension NsPrediction {
    /// Convert a raw `NightscoutDeviceStatus` into an `NsPrediction`.
    /// Returns `nil` if the record has no loop predicted curve.
    public static func from(status: NightscoutDeviceStatus) -> NsPrediction? {
        let fmt = ISO8601DateFormatter()
        fmt.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        guard let loop = status.loop,
              let predicted = loop.predicted else { return nil }

        // Try with fractional seconds first, then without
        func parseDate(_ string: String) -> Date? {
            let fmtFrac = ISO8601DateFormatter()
            fmtFrac.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let d = fmtFrac.date(from: string) { return d }
            let fmtPlain = ISO8601DateFormatter()
            fmtPlain.formatOptions = [.withInternetDateTime]
            return fmtPlain.date(from: string)
        }

        guard let createdAt = parseDate(status.created_at),
              let startDate = parseDate(predicted.startDate) else { return nil }

        return NsPrediction(
            t: createdAt.timeIntervalSince1970 * 1000,
            startMs: startDate.timeIntervalSince1970 * 1000,
            iob: loop.iob?.iob,
            cob: loop.cob?.cob,
            values: predicted.values
        )
    }
}
