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
    /// ACTUAL delivered units for this temp basal segment — pulse-quantized by the
    /// pump (Omnipod 0.05U pulses), so generally != rate*duration. Loop reconciles
    /// IOB/effects on this delivered amount, not the nominal rate*duration.
    public let amount: Double?
    /// Relative temp basal percent (+/- of scheduled)
    public let percent: Int?
    /// Whether this was an SMB (Super Micro Bolus)
    public let isSMB: Bool?
    /// Whether this was an automatic (algorithm-driven) delivery
    public let automatic: Bool?
    /// Meal time for carb entries — may differ from created_at when user enters past/future meals
    public let timestamp: String?
    /// Wall-clock time the user actually tapped "save" (Loop's `userCreatedDate`).
    /// Unlike `timestamp`/`created_at` (the BACKDATABLE meal/absorption-anchor time),
    /// this is when Loop genuinely learned about the carbs — the correct visibility
    /// gate. Present on 100% of this user's carb entries; `timestamp − userEnteredAt`
    /// is the true backdating signal (~4% of entries >5 min on user2).
    public let userEnteredAt: String?
    /// Carb absorption time in MINUTES (Loop publishes this per carb entry; e.g. 30, 180)
    public let absorptionTime: Double?
    /// Mongo ObjectId. Its first 4 bytes encode the DB-insertion time — the
    /// actual moment the record was written, independent of the (backdatable)
    /// created_at/timestamp. Used to recover the true entry time of carbs the
    /// user logged with a past meal time.
    public let id: String?
    /// Temporary Override: insulin-needs scale factor (basal ×f, ISF ÷f, CR ÷f).
    /// nil = no insulin scaling (target-only override).
    public let insulinNeedsScaleFactor: Double?
    /// Temporary Override: the override target/correction range [low, high] mg/dL.
    public let correctionRange: [Double]?
    /// Temporary Target: target range bounds (mg/dL). Trio sets top==bottom.
    public let targetTop: Double?
    public let targetBottom: Double?
    /// Free-text note. Trio logs Exercise/preset temp targets as eventType
    /// "Exercise" with NULL targetTop/Bottom and the target embedded here,
    /// e.g. "130 mg/dL @ 100%". Parsed as a fallback when bounds are absent.
    public let notes: String?

    private enum CodingKeys: String, CodingKey {
        case created_at, eventType, insulin, carbs, rate, duration,
             absolute, amount, percent, isSMB, automatic, timestamp, userEnteredAt, absorptionTime,
             insulinNeedsScaleFactor, correctionRange, targetTop, targetBottom, notes
        case id = "_id"
    }

    /// DB-insertion time decoded from the ObjectId (first 8 hex chars = 4-byte
    /// big-endian Unix seconds). Returns nil if `_id` is missing/not an ObjectId.
    public var objectIdInsertionDate: Date? {
        guard let id = id, id.count >= 8,
              let secs = UInt32(id.prefix(8), radix: 16) else { return nil }
        return Date(timeIntervalSince1970: TimeInterval(secs))
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
    public let mills: String?   // creation timestamp in ms. Loop uploads a String; Trio uploads a Number.
    public let units: String?   // top-level units (fallback if profile lacks units)
    /// Loop-specific runtime settings (suspend threshold, max bolus/basal,
    /// dosing strategy). Present on profiles uploaded by Loop.
    public let loopSettings: NightscoutLoopSettings?

    private enum CodingKeys: String, CodingKey {
        case defaultProfile, startDate, store, mills, units, loopSettings
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        defaultProfile = try c.decodeIfPresent(String.self, forKey: .defaultProfile)
        startDate      = try c.decodeIfPresent(String.self, forKey: .startDate)
        store          = try c.decodeIfPresent([String: NightscoutProfile].self, forKey: .store)
        units          = try c.decodeIfPresent(String.self, forKey: .units)
        loopSettings   = try c.decodeIfPresent(NightscoutLoopSettings.self, forKey: .loopSettings)
        // `mills` is a String on Loop-uploaded profiles but a JSON Number on Trio's.
        // Decoding `String.self` against a number THREW, silently dropping every
        // Trio profile record (→ stale fallback to an ancient record). Accept both.
        if let s = try? c.decode(String.self, forKey: .mills) {
            mills = s
        } else if let n = try? c.decode(Int64.self, forKey: .mills) {
            mills = String(n)
        } else if let d = try? c.decode(Double.self, forKey: .mills) {
            mills = String(Int64(d))
        } else {
            mills = nil
        }
    }
}

/// Loop runtime settings as serialised into the Nightscout profile record.
public struct NightscoutLoopSettings: Decodable, Sendable {
    /// Suspend threshold (a.k.a. minimum BG guard) in mg/dL.
    public let minimumBGGuard: Double?
    /// Maximum automatic bolus / single-bolus cap in units.
    public let maximumBolus: Double?
    /// Maximum basal rate in U/hr.
    public let maximumBasalRatePerHour: Double?
    /// "automaticBolus" | "tempBasalOnly" | …
    public let dosingStrategy: String?
}

// MARK: – Device status models

/// A device status record from /api/v1/devicestatus.json
public struct NightscoutDeviceStatus: Decodable, Sendable {
    public let created_at: String
    public let loop: NightscoutLoopStatus?
    /// Temporary preset override active on this cycle, if any.
    /// Loop uploads this at the devicestatus root (sibling of `loop`).
    public let activeOverride: NightscoutOverride?

    private enum CodingKeys: String, CodingKey {
        case created_at, loop
        case activeOverride = "override"
    }
}

/// Temporary preset override state ("override" in the Loop app).
/// When active, `multiplier` scales insulin needs (basal × m, ISF ÷ m,
/// CR ÷ m) — i.e., m<1 makes Loop less aggressive.
public struct NightscoutOverride: Decodable, Sendable {
    public let active: Bool?
    public let name: String?
    public let multiplier: Double?
}

/// The `loop` object within a device status record.
public struct NightscoutLoopStatus: Decodable, Sendable {
    public let iob: NightscoutIOB?
    public let cob: NightscoutCOB?
    public let predicted: NightscoutPredicted?
    /// ISO8601 timestamp of this Loop cycle.
    public let timestamp: String?
    /// Full correction-bolus recommendation (before applicationFactor scaling).
    public let recommendedBolus: Double?
    /// Automatic-dose recommendation (after applicationFactor scaling).
    public let automaticDoseRecommendation: NightscoutAutoDoseRec?
    /// What Loop actually enacted on the pump this cycle.
    public let enacted: NightscoutEnactedDose?
}

/// Automatic-dose recommendation within a Loop status.
public struct NightscoutAutoDoseRec: Decodable, Sendable {
    public let bolusVolume: Double?
    public let timestamp: String?
}

/// Enacted dose within a Loop status (what went to the pump).
public struct NightscoutEnactedDose: Decodable, Sendable {
    /// Temp basal rate in U/hr (0 = pump suspend / basal zeroed).
    public let rate: Double?
    /// Temp basal duration in minutes (0 = cancel / instantaneous).
    public let duration: Double?
    /// Auto-bolus amount that was sent to the pump this cycle.
    public let bolusVolume: Double?
    public let timestamp: String?
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
    private let token: String?          // Nightscout subject access token (?token=…)

    // ISO8601 formatter for query parameters (shared; DateFormatter is not Sendable but
    // we construct fresh ones per call to avoid concurrency issues)
    private static func makeDateFormatter() -> ISO8601DateFormatter {
        let fmt = ISO8601DateFormatter()
        fmt.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return fmt
    }

    // MARK: – Init

    public init(baseURL: URL, apiSecret: String? = nil, token: String? = nil) {
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
        if let t = token, !t.isEmpty {
            self.token = t
        } else {
            self.token = nil
        }
    }

    /// Append the Nightscout subject access token (`?token=…`) to a request URL,
    /// when configured. Token auth is used by instances with role-based access
    /// (`authDefaultRoles: denied`); it is an alternative to the api-secret header.
    private static func appendingToken(_ token: String?, to url: URL) -> URL {
        guard let token = token,
              var comps = URLComponents(url: url, resolvingAgainstBaseURL: false)
        else { return url }
        var items = comps.queryItems ?? []
        items.append(URLQueryItem(name: "token", value: token))
        comps.queryItems = items
        return comps.url ?? url
    }

    // MARK: – Public API

    /// Fetch CGM entries between `interval.start` and `interval.end`.
    /// Fetched in 28-day chunks: a full-year single request (~105k entries)
    /// 504s on slower hosts (e.g. slow guest). Chunking is transparent to the
    /// DataCache, which still stores one file for the requested interval.
    public func fetchEntries(interval: DateInterval) async throws -> [NightscoutEntry] {
        let chunk: TimeInterval = 28 * 24 * 3600
        var all: [NightscoutEntry] = []
        var start = interval.start
        while start < interval.end {
            let end = min(start.addingTimeInterval(chunk), interval.end)
            all += try await fetchEntriesChunk(from: start, to: end)
            start = end.addingTimeInterval(1)  // no overlap, no boundary dup
        }
        return all
    }

    private func fetchEntriesChunk(from: Date, to: Date) async throws -> [NightscoutEntry] {
        let fmt = Self.makeDateFormatter()
        var components = URLComponents(url: baseURL.appendingPathComponent("api/v1/entries.json"),
                                       resolvingAgainstBaseURL: false)!
        components.queryItems = [
            URLQueryItem(name: "find[dateString][$gte]", value: fmt.string(from: from)),
            URLQueryItem(name: "find[dateString][$lte]", value: fmt.string(from: to)),
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

    /// Fetch only treatments of a given eventType over [from, to].
    /// Used for low-volume event types (e.g. "Temporary Override") where a deep
    /// look-back is needed — a long/indefinite override can start well before the
    /// analysis window yet still be active inside it. The eventType filter keeps
    /// the deep query cheap (overrides are rare relative to temp-basals/boluses).
    public func fetchTreatments(from: Date, to: Date, eventType: String) async throws -> [NightscoutTreatment] {
        let fmt = Self.makeDateFormatter()
        var components = URLComponents(url: baseURL.appendingPathComponent("api/v1/treatments.json"),
                                       resolvingAgainstBaseURL: false)!
        components.queryItems = [
            URLQueryItem(name: "find[eventType]", value: eventType),
            URLQueryItem(name: "find[created_at][$gte]", value: fmt.string(from: from)),
            URLQueryItem(name: "find[created_at][$lte]", value: fmt.string(from: to)),
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

    /// All profile records (history), most-recent first. Used to build a
    /// TIME-VARYING therapy timeline: the user's ISF/CR/basal/target schedule
    /// changes over time, and each record's `startDate` is when that schedule
    /// became active. Backfilling a single (current) profile across history is
    /// a fidelity bug — e.g. user2's ISF was 35–37 before 2025-05-15, 32 after.
    /// Lossy wrapper: a single malformed profile record (over years of history,
    /// some have quirky/legacy fields) must NOT fail the whole array decode.
    private struct LossyProfile: Decodable {
        let value: NightscoutProfileRecord?
        init(from decoder: Decoder) throws { value = try? NightscoutProfileRecord(from: decoder) }
    }

    public func fetchProfileHistory(count: Int = 8000) async throws -> [NightscoutProfileRecord] {
        var comps = URLComponents(
            url: baseURL.appendingPathComponent("api/v1/profile.json"),
            resolvingAgainstBaseURL: false)!
        comps.queryItems = [URLQueryItem(name: "count", value: String(count))]
        let lossy = try await fetchJSON([LossyProfile].self, from: comps.url!)
        return lossy.compactMap { $0.value }
    }

    // MARK: – Private helpers

    private func fetchJSON<T: Decodable>(_ type: T.Type, from url: URL) async throws -> T {
        let finalURL = Self.appendingToken(token, to: url)
        var request = URLRequest(url: finalURL)
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
