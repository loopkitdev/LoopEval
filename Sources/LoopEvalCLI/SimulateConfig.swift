// SimulateConfig.swift — `simulate --config FILE.json` and `--set section.key=value`.
//
// A config file is the same settings as the flags, arranged by the sections of `simulate --help`:
//
//   {
//     "include": ["deployment/i003.json"],            // merged first, paths relative to this file
//     "data":       { "data-dir": "...", "start": "...", "end": "...", "trace-out": "..." },
//     "mode":       { "candidate-counterfactual": true, "cgm-stale-guard-min": 5 },
//     "deployment": { "from-replay-config": true, "integral-rc": true },
//     "candidate":  { "insulin-needs": 0.85 },
//     "person":     { "manual-bolus-from-recommendation": false },
//     "body":       { "counter-reg-onset": 54, "infer-sensitivity": true },
//     "plant":      { "external-plant": "python -m ...", "plant-behavior": true },
//     "loop-experiments": { "slow-rc-tau-min": 180 },
//     "openaps":    { "smb-ratio": 0.5 }
//   }
//
// A key is a flag's long name, looked up in its own section only. In the candidate sections the
// "candidate-" / "candidate-oaps-" prefix may be left off. Values: true/false for flags (false is
// the flag's --no- form where it has one), a number or string for an option, an array for a
// repeatable option. "deployment.from-replay-config": true adds the export's replay_config.json
// required_flags.
//
// The file is expanded into ordinary flags before parsing, so it can't mean anything a command line
// can't. Precedence, lowest first: replay_config.json, config files in order, --set, flags on the
// command line. `--show-config` prints the expanded command line and exits.
//
// A section the run doesn't use (OpenAPS settings with a Loop candidate, Loop experiments with an
// OpenAPS candidate, ICE-replay body settings with an external plant or decision-time replay) is
// named on stderr, so a base file can carry every branch while each run says which it reads.

import ArgumentParser
import Foundation

enum SimulateSection: String, CaseIterable {
    case data, mode, deployment, candidate, person, body, plant
    case loopExperiments = "loop-experiments"
    case openaps

    var title: String {
        switch self {
        case .data: return "Data and output"
        case .mode: return "Run mode and decision timing"
        case .deployment: return "Deployed system (the donor's Loop; both arms)"
        case .candidate: return "Candidate: controller and settings"
        case .person: return "Person: manual boluses and carbs"
        case .body: return "Body: ICE replay and patient"
        case .plant: return "Body: external plant"
        case .loopExperiments: return "Candidate Loop experiments"
        case .openaps: return "Candidate OpenAPS (with --candidate-openaps)"
        }
    }

    /// Prefixes a key in this section may leave off.
    var optionalPrefixes: [String] {
        switch self {
        case .candidate, .loopExperiments, .person, .body: return ["candidate-"]
        case .openaps: return ["candidate-oaps-", "oaps-", "candidate-"]
        default: return []
        }
    }
}

enum SimulateConfig {
    struct ConfigError: Error, CustomStringConvertible { let description: String }

    /// The command line `simulate` actually parsed (after expansion); nil when no config was used.
    nonisolated(unsafe) static var effectiveArguments: [String]? = nil

    /// A JSON true/false (JSONSerialization returns booleans and numbers alike as NSNumber; `as? Bool`
    /// would read 1 as true).
    private static func jsonBool(_ v: Any) -> Bool? {
        #if canImport(Darwin)
        guard let n = v as? NSNumber, CFGetTypeID(n) == CFBooleanGetTypeID() else { return nil }
        return n.boolValue
        #else
        return type(of: v) == Bool.self ? (v as! Bool) : nil
        #endif
    }

    private struct FlagInfo { let section: SimulateSection; let isFlag: Bool; let repeating: Bool }

    /// Long flag name -> section and kind, from ArgumentParser's own help dump (never out of date).
    private static func flagTable() throws -> [String: FlagInfo] {
        guard let data = SimulateCommand._dumpHelp().data(using: .utf8),
              let root = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let cmd = root["command"] as? [String: Any],
              let args = cmd["arguments"] as? [[String: Any]] else {
            throw ConfigError(description: "config: could not read simulate's flag table")
        }
        let byTitle = Dictionary(uniqueKeysWithValues: SimulateSection.allCases.map { ($0.title, $0) })
        var table: [String: FlagInfo] = [:]
        for a in args {
            guard let title = a["sectionTitle"] as? String, let section = byTitle[title] else { continue }
            let isFlag = (a["kind"] as? String) == "flag"
            let repeating = (a["isRepeating"] as? Bool) ?? false
            for n in a["names"] as? [[String: Any]] ?? [] where (n["kind"] as? String) == "long" {
                if let name = n["name"] as? String { table[name] = FlagInfo(section: section, isFlag: isFlag, repeating: repeating) }
            }
        }
        return table
    }

    /// Expand `--config`/`--set`/`--show-config` in a `simulate` argument list (without the program
    /// name). Returns the arguments unchanged when none is present.
    static func expand(_ arguments: [String]) throws -> [String] {
        guard arguments.first == "simulate" else { return arguments }
        var configPaths: [String] = [], sets: [String] = [], rest: [String] = []
        var show = false
        var i = 1
        while i < arguments.count {
            let a = arguments[i]
            if a == "--config" || a == "--set" {
                guard i + 1 < arguments.count else { throw ConfigError(description: "\(a) needs a value") }
                if a == "--config" { configPaths.append(arguments[i + 1]) } else { sets.append(arguments[i + 1]) }
                i += 2; continue
            }
            if a.hasPrefix("--config=") { configPaths.append(String(a.dropFirst(9))); i += 1; continue }
            if a.hasPrefix("--set=") { sets.append(String(a.dropFirst(6))); i += 1; continue }
            if a == "--show-config" { show = true; i += 1; continue }
            rest.append(a); i += 1
        }
        if configPaths.isEmpty && sets.isEmpty && !show { return arguments }

        let table = try flagTable()
        // Merge files (each after its includes), then --set, into one section -> key -> value tree.
        var tree: [String: [String: Any]] = [:]
        func merge(_ obj: [String: Any], from file: String) throws {
            for (k, v) in obj where k != "include" {
                guard SimulateSection(rawValue: k) != nil else {
                    throw ConfigError(description: "config \(file): unknown section '\(k)' (sections: \(SimulateSection.allCases.map(\.rawValue).joined(separator: ", ")))")
                }
                guard let kv = v as? [String: Any] else {
                    throw ConfigError(description: "config \(file): section '\(k)' must be an object")
                }
                tree[k, default: [:]].merge(kv) { _, new in new }
            }
        }
        func load(_ path: String, depth: Int = 0) throws {
            guard depth < 8 else { throw ConfigError(description: "config: includes nested too deeply at \(path)") }
            let url = URL(fileURLWithPath: (path as NSString).expandingTildeInPath)
            guard let raw = try? Data(contentsOf: url) else { throw ConfigError(description: "config: cannot read \(path)") }
            guard let obj = (try? JSONSerialization.jsonObject(with: raw)) as? [String: Any] else {
                throw ConfigError(description: "config: \(path) is not a JSON object")
            }
            for inc in obj["include"] as? [String] ?? [] {
                let p = inc.hasPrefix("/") || inc.hasPrefix("~") ? inc
                    : url.deletingLastPathComponent().appendingPathComponent(inc).path
                try load(p, depth: depth + 1)
            }
            try merge(obj, from: path)
        }
        for p in configPaths { try load(p) }
        for s in sets {
            guard let eq = s.firstIndex(of: "="), let dot = s[..<eq].firstIndex(of: ".") else {
                throw ConfigError(description: "--set \(s): expected section.key=value")
            }
            let section = String(s[..<dot]), key = String(s[s.index(after: dot)..<eq])
            let rawValue = String(s[s.index(after: eq)...])
            let value: Any = (try? JSONSerialization.jsonObject(with: Data(rawValue.utf8), options: .fragmentsAllowed)) ?? rawValue
            try merge([section: [key: value]], from: "--set")
        }

        // Resolve keys to flags and render tokens.
        var tokens: [String] = []
        var fromReplayConfig = false
        var configSections: [SimulateSection: Int] = [:]
        for section in SimulateSection.allCases {
            guard let kv = tree[section.rawValue] else { continue }
            for key in kv.keys.sorted() {
                let value = kv[key]!
                if section == .deployment && key == "from-replay-config" { fromReplayConfig = jsonBool(value) == true; continue }
                let candidates = [key] + section.optionalPrefixes.map { $0 + key }
                guard let name = candidates.first(where: { table[$0]?.section == section }) else {
                    if let other = candidates.compactMap({ n in table[n].map { (n, $0.section) } }).first {
                        throw ConfigError(description: "config: --\(other.0) belongs in section '\(other.1.rawValue)', not '\(section.rawValue)'")
                    }
                    throw ConfigError(description: "config: section '\(section.rawValue)' has no setting '\(key)'")
                }
                let info = table[name]!
                configSections[section, default: 0] += 1
                if info.isFlag {
                    guard let b = jsonBool(value) else { throw ConfigError(description: "config: \(section.rawValue).\(key) is a flag; use true or false") }
                    if b { tokens.append("--" + name) }
                    else if table["no-" + name] != nil { tokens.append("--no-" + name) }
                    else if name.hasPrefix("no-"), table[String(name.dropFirst(3))] != nil { tokens.append("--" + name.dropFirst(3)) }
                    continue
                }
                let values: [Any] = (value as? [Any]) ?? [value]
                if values.count != 1 && !info.repeating {
                    throw ConfigError(description: "config: \(section.rawValue).\(key) takes one value")
                }
                for v in values {
                    let str: String
                    if jsonBool(v) != nil {
                        throw ConfigError(description: "config: \(section.rawValue).\(key) takes a value, not true/false")
                    }
                    switch v {
                    case let s as String: str = s
                    case let n as NSNumber: str = n.stringValue
                    default: throw ConfigError(description: "config: \(section.rawValue).\(key): unsupported value \(v)")
                    }
                    tokens += ["--" + name, str]
                }
            }
        }

        // replay_config.json of the export, lowest precedence.
        var prefix: [String] = []
        if fromReplayConfig {
            let all = tokens + rest
            guard let di = all.lastIndex(of: "--data-dir"), di + 1 < all.count else {
                throw ConfigError(description: "config: deployment.from-replay-config needs a data-dir")
            }
            let url = URL(fileURLWithPath: all[di + 1]).appendingPathComponent("replay_config.json")
            guard let raw = try? Data(contentsOf: url),
                  let obj = (try? JSONSerialization.jsonObject(with: raw)) as? [String: Any],
                  let req = obj["required_flags"] as? [String] else {
                throw ConfigError(description: "config: deployment.from-replay-config, but \(url.path) has no required_flags")
            }
            prefix = req.flatMap { $0.split(separator: " ", maxSplits: 1).map(String.init) }
        }
        let expanded = ["simulate"] + prefix + tokens + rest

        // Which sections this run uses.
        func has(_ flag: String) -> Bool { expanded.contains("--" + flag) }
        let openapsCandidate = has("candidate-openaps") || has("candidate-loop-mimic-oaps")
        var unused: [(SimulateSection, String)] = []
        if !openapsCandidate { unused.append((.openaps, "the candidate is Loop")) }
        if openapsCandidate { unused.append((.loopExperiments, "the candidate is OpenAPS")) }
        if has("external-plant") { unused.append((.body, "the external plant is the body")) }
        else if has("decision-time-replay") { unused.append((.body, "decision-time replay has no body")) }
        for (section, why) in unused {
            let n = expanded.filter { tok in
                tok.hasPrefix("--") && table[String(tok.dropFirst(2))]?.section == section
            }.count
            if n > 0 {
                FileHandle.standardError.write(Data("config: section '\(section.rawValue)' (\(n) setting\(n == 1 ? "" : "s")) is not used by this run: \(why)\n".utf8))
            }
        }
        if show {
            print(expanded.map { $0.contains(" ") ? "'\($0)'" : $0 }.joined(separator: " "))
            exit(0)
        }
        effectiveArguments = ["loop-eval"] + expanded
        return expanded
    }
}
