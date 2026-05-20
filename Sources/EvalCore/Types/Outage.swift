//
//  Outage.swift
//  EvalCore
//
//  Source-agnostic representation of an insulin-delivery outage: a window in
//  which the physical pump could not deliver insulin (pod failure, occlusion,
//  intentional disconnect). The sim must NOT credit candidate deliveries
//  inside an outage when projecting counter_BG.
//
//  CSV schema matches `analysis/loopeval_analysis/outage.py`:
//
//      start,end,reason,source,notes
//      2026-04-01T20:02:00Z,2026-04-01T22:46:26Z,pod_change,nightscout/Site Change,...
//
//  Other data sources (Tidepool, raw pod logs, manual specs) write the same
//  CSV; the simulator consumes the CSV, not the upstream system.
//

import Foundation

public struct Outage: Sendable, Equatable {
    public let interval: DateInterval
    public let reason: String
    public let source: String
    public let notes: String

    public init(start: Date, end: Date, reason: String = "unknown",
                source: String = "unknown", notes: String = "") {
        precondition(end > start, "Outage end must be after start")
        self.interval = DateInterval(start: start, end: end)
        self.reason = reason
        self.source = source
        self.notes = notes
    }

    public func contains(_ t: Date) -> Bool {
        return interval.contains(t)
    }
}

public enum OutageCSV {
    public enum ParseError: Error, CustomStringConvertible {
        case fileNotFound(String)
        case missingHeader
        case unparseableTimestamp(String, row: Int)
        case missingColumn(String, row: Int)

        public var description: String {
            switch self {
            case .fileNotFound(let p): return "Outage CSV not found at \(p)"
            case .missingHeader: return "Outage CSV is empty or missing header row"
            case .unparseableTimestamp(let s, let r): return "Unparseable timestamp '\(s)' on row \(r)"
            case .missingColumn(let c, let r): return "Missing column '\(c)' on row \(r)"
            }
        }
    }

    public static func load(from path: String) throws -> [Outage] {
        let url = URL(fileURLWithPath: path)
        guard FileManager.default.fileExists(atPath: url.path) else {
            throw ParseError.fileNotFound(path)
        }
        let raw = try String(contentsOf: url, encoding: .utf8)
        return try parse(raw)
    }

    /// Parse a CSV string. Strict on column names — must have at minimum
    /// `start` and `end`. The remaining columns (`reason`, `source`, `notes`)
    /// default to empty/"unknown" when absent.
    public static func parse(_ raw: String) throws -> [Outage] {
        var lines = raw.split(omittingEmptySubsequences: false, whereSeparator: { $0 == "\n" || $0 == "\r\n" })
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
        guard !lines.isEmpty else { throw ParseError.missingHeader }

        let header = parseCSVRow(lines.removeFirst())
        let lookup: [String: Int] = Dictionary(uniqueKeysWithValues:
            header.enumerated().map { ($1.lowercased(), $0) })
        guard let startIdx = lookup["start"], let endIdx = lookup["end"] else {
            throw ParseError.missingColumn("start/end", row: 0)
        }
        let reasonIdx = lookup["reason"]
        let sourceIdx = lookup["source"]
        let notesIdx  = lookup["notes"]

        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime]
        let isoFractional = ISO8601DateFormatter()
        isoFractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        func parseTS(_ s: String, row: Int) throws -> Date {
            // Accept both "2026-04-01T20:02:00Z" and "2026-04-01 20:02:00+00:00"
            let normalized = s.replacingOccurrences(of: " ", with: "T")
            if let d = iso.date(from: normalized) { return d }
            if let d = isoFractional.date(from: normalized) { return d }
            throw ParseError.unparseableTimestamp(s, row: row)
        }

        var outages: [Outage] = []
        outages.reserveCapacity(lines.count)
        for (k, line) in lines.enumerated() {
            let cols = parseCSVRow(line)
            // Tolerate trailing-comma rows or under-populated rows
            guard cols.count > max(startIdx, endIdx) else {
                throw ParseError.missingColumn("start/end values", row: k + 1)
            }
            let start = try parseTS(cols[startIdx], row: k + 1)
            let end   = try parseTS(cols[endIdx],   row: k + 1)
            guard end > start else { continue }
            let reason = reasonIdx.flatMap { cols.indices.contains($0) ? cols[$0] : nil } ?? "unknown"
            let source = sourceIdx.flatMap { cols.indices.contains($0) ? cols[$0] : nil } ?? "unknown"
            let notes  = notesIdx.flatMap { cols.indices.contains($0) ? cols[$0] : nil } ?? ""
            outages.append(Outage(start: start, end: end,
                                  reason: reason.isEmpty ? "unknown" : reason,
                                  source: source.isEmpty ? "unknown" : source,
                                  notes: notes))
        }
        return outages.sorted { $0.interval.start < $1.interval.start }
    }

    /// Minimal RFC-4180 splitter: handles quoted fields, embedded commas, and
    /// doubled-quote escapes within quotes. Fields are returned trimmed of
    /// surrounding whitespace outside quotes.
    private static func parseCSVRow(_ line: String) -> [String] {
        var fields: [String] = []
        var current = ""
        var inQuotes = false
        var i = line.startIndex
        while i < line.endIndex {
            let c = line[i]
            if inQuotes {
                if c == "\"" {
                    let next = line.index(after: i)
                    if next < line.endIndex && line[next] == "\"" {
                        current.append("\"")
                        i = line.index(after: next)
                        continue
                    }
                    inQuotes = false
                } else {
                    current.append(c)
                }
            } else {
                if c == "," {
                    fields.append(current)
                    current = ""
                } else if c == "\"" && current.isEmpty {
                    inQuotes = true
                } else {
                    current.append(c)
                }
            }
            i = line.index(after: i)
        }
        fields.append(current)
        return fields.map { $0.trimmingCharacters(in: .whitespaces) }
    }
}

extension Array where Element == Outage {
    /// Returns the first outage covering `t`, or nil.
    public func containing(_ t: Date) -> Outage? {
        // Linear scan is fine — counts are O(20-30) per 60d.
        for o in self where o.contains(t) { return o }
        return nil
    }
}
