// DataCache.swift — simple JSON file cache for fetched data
//
// Files are written to `cacheDir/<key>.json`.
// No TTL logic at this layer — callers decide when to re-fetch.

import Foundation

public actor DataCache {

    // MARK: – Properties

    private let cacheDir: URL
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    // MARK: – Init

    public init(cacheDir: URL) throws {
        try FileManager.default.createDirectory(at: cacheDir,
                                                withIntermediateDirectories: true)
        self.cacheDir = cacheDir
        self.encoder = JSONEncoder()
        self.encoder.dateEncodingStrategy = .iso8601
        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .iso8601
    }

    // MARK: – Public API

    /// Persist `value` to disk under `key`.
    public func save<T: Encodable>(_ value: T, key: String) throws {
        let data = try encoder.encode(value)
        let url  = fileURL(for: key)
        try data.write(to: url, options: .atomicWrite)
    }

    /// Load a previously saved value for `key`, or `nil` if not cached.
    public func load<T: Decodable>(key: String) throws -> T? {
        let url = fileURL(for: key)
        guard FileManager.default.fileExists(atPath: url.path) else { return nil }
        let data = try Data(contentsOf: url)
        return try decoder.decode(T.self, from: data)
    }

    /// Remove all cached files.
    public func clearAll() throws {
        let files = try FileManager.default.contentsOfDirectory(
            at: cacheDir, includingPropertiesForKeys: nil)
        for file in files where file.pathExtension == "json" {
            try FileManager.default.removeItem(at: file)
        }
    }

    // MARK: – Static helpers

    /// Build a deterministic cache key from a data type name, base URL, and date interval.
    /// Safe to use as a file name component.
    public static func key(for dataType: String, url: URL, interval: DateInterval) -> String {
        let host = url.host ?? "unknown"
        let start = Int(interval.start.timeIntervalSince1970)
        let end   = Int(interval.end.timeIntervalSince1970)
        // Replace characters that are invalid in file names
        let safeHost = host.replacingOccurrences(of: "/", with: "_")
        return "\(dataType)_\(safeHost)_\(start)_\(end)"
    }

    // MARK: – Private

    private func fileURL(for key: String) -> URL {
        cacheDir.appendingPathComponent(key + ".json")
    }
}
