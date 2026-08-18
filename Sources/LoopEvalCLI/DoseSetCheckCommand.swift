import ArgumentParser
import Foundation
import EvalCore
import LoopAlgorithm

/// Diff OUR per-cycle dose SET against the set a real deployed Loop actually held.
///
/// `insulin-effect-check` proves we compute the right effect from a given dose array;
/// this proves we assemble the right array in the first place. They are different
/// failure modes: every uploaded record can reconstruct exactly while the set handed to
/// the algorithm still differs, because the set depends on where the in-progress temp is
/// trimmed (`basalDosingEnd`, which deployed Loop sets to `now`) and on how
/// `annotated(with: basal)` splits doses at schedule boundaries.
///
/// The decision instant comes from the capture itself, not from the CGM cadence — on a
/// device whose CGM arrives late the two differ by minutes, and stepping on the CGM would
/// compare sets built at the wrong time.
struct DoseSetCheckCommand: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "dose-set-check",
        abstract: "Diff our per-cycle dose set against a deployed-Loop capture (JSONL from the rig)."
    )

    @Argument(help: "loopeval_fc_<hour>.jsonl from the instrumented rig")
    var dumpPath: String

    @Option(name: .long, help: "Directory of pre-exported EvalCore JSON files")
    var dataDir: String

    @Option(help: "Which captured variant to check: trimmed | untrimmed")
    var variant: String = "trimmed"

    @Option(help: "Only cycles with this dosingDecision reason (empty = all)")
    var reason: String = ""

    @Flag(help: "Print every differing cycle, not just the summary")
    var verbose: Bool = false

    // A pairing is a match when both endpoints and the volume agree this closely.
    static let timeTol: TimeInterval = 1.0
    static let unitTol = 0.001

    @Option(name: .long, help: "Start of the data window — ISO8601")
    var start: String

    @Option(name: .long, help: "End of the data window — ISO8601")
    var end: String

    func run() async throws {
        let iso = ISO8601DateFormatter()
        guard let s = iso.date(from: start), let e = iso.date(from: end) else {
            throw ValidationError("--start/--end must be ISO8601, e.g. 2026-08-17T00:00:00Z")
        }
        var config = EvalConfig()
        config.includeFutureInsulin = false
        config.clipInProgressTempBasal = (variant == "trimmed")

        let engine = EvaluationEngine(dataSource: JSONFileDataSource(baseURL: URL(fileURLWithPath: dataDir)))
        let data = try await engine.prefetchData(for: DateInterval(start: s, end: e), config: config)
        let inspector = DoseSetInspector(glucose: data.glucose, doses: data.doses,
                                         carbs: data.carbs, therapy: data.therapyTimeline,
                                         config: config)

        let text = try String(contentsOfFile: dumpPath, encoding: .utf8)
        var compared = 0, identical = 0, skipped = 0
        var worstExtra = 0.0, worstMissing = 0.0, worstVolume = 0.0
        var totalOurs = 0.0, totalLoop = 0.0
        var offenders: [(Date, Int, Int, Double)] = []
        var ourWindowH = 0.0, loopWindowH = 0.0

        for line in text.split(separator: "\n") {
            guard let d = line.data(using: .utf8),
                  let obj = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any]
            else { continue }
            if !reason.isEmpty, (obj["reason"] as? String) != reason { continue }
            guard let capAll = obj["doseCapture"] as? [String: Any],
                  let cap = capAll[variant] as? [String: Any],
                  let loopDoses = cap["trimmed"] as? [[String: Any]],
                  let capturedAt = cap["capturedAt"] as? Double,
                  !loopDoses.isEmpty
            else { skipped += 1; continue }

            // The decision instant, straight from the record Loop wrote.
            let t = Date(timeIntervalSince1970: capturedAt)
            guard let ours = inspector.doseSet(at: t) else {
                if verbose { print("  skip \(ISO8601DateFormatter().string(from: t)): buildInput returned nil") }
                skipped += 1; continue
            }
            if ours.isEmpty, verbose {
                print("  skip \(ISO8601DateFormatter().string(from: t)): our dose set is EMPTY (basal schedule missing?)")
            }

            // Our lookback horizon and Loop's need not be the same length, and that
            // difference is NOT what this check is about — it would swamp the comparison
            // with doses one side simply never looked at. Restrict BOTH sides to the span
            // they have in common (the later of the two window starts).
            var theirsAll = loopDoses.compactMap { e -> InspectedDose? in
                guard let s = e["start"] as? Double, let en = e["end"] as? Double,
                      let type = e["type"] as? String else { return nil }
                let units = (e["unitsInDeliverableIncrements"] as? Double)
                    ?? (e["programmedUnits"] as? Double) ?? 0
                return InspectedDose(type: type == "bolus" ? "bolus" : "basal",
                                     startDate: Date(timeIntervalSince1970: s),
                                     endDate: Date(timeIntervalSince1970: en),
                                     volume: units,
                                     netBasalUnits: (e["netBasalUnits"] as? Double) ?? 0)
            }
            guard let ourStart = ours.map({ $0.startDate }).min(),
                  let theirStart = theirsAll.map({ $0.startDate }).min()
            else { skipped += 1; continue }
            let floor = max(ourStart, theirStart).addingTimeInterval(-1)
            ourWindowH += ourStart.distance(to: t) / 3600
            loopWindowH += theirStart.distance(to: t) / 3600
            let oursCommon = ours.filter { $0.startDate >= floor }
            theirsAll = theirsAll.filter { $0.startDate >= floor }
            let theirs = theirsAll
            guard !theirs.isEmpty else { skipped += 1; continue }
            compared += 1

            var unmatched = theirs
            var extra: [InspectedDose] = []
            var volumeDelta = 0.0
            for o in oursCommon {
                if let i = unmatched.firstIndex(where: {
                    abs($0.startDate.timeIntervalSince(o.startDate)) <= Self.timeTol &&
                    abs($0.endDate.timeIntervalSince(o.endDate)) <= Self.timeTol
                }) {
                    volumeDelta = max(volumeDelta, abs(unmatched[i].volume - o.volume))
                    unmatched.remove(at: i)
                } else {
                    extra.append(o)
                }
            }
            totalOurs += oursCommon.reduce(0) { $0 + $1.volume }
            totalLoop += theirs.reduce(0) { $0 + $1.volume }

            if extra.isEmpty, unmatched.isEmpty, volumeDelta < Self.unitTol {
                identical += 1
            } else {
                worstExtra = max(worstExtra, extra.reduce(0) { $0 + $1.volume })
                worstMissing = max(worstMissing, unmatched.reduce(0) { $0 + $1.volume })
                worstVolume = max(worstVolume, volumeDelta)
                offenders.append((t, extra.count, unmatched.count, volumeDelta))
                if verbose {
                    let f = ISO8601DateFormatter()
                    print("  \(f.string(from: t))  ours \(oursCommon.count) vs Loop \(theirs.count):"
                          + " \(extra.count) only-ours, \(unmatched.count) only-Loop,"
                          + String(format: " worst vol Δ %.4f U", volumeDelta))
                    for e in extra.prefix(3) {
                        print(String(format: "      only ours: %@ %@ -> %@  %.4f U", e.type,
                                     f.string(from: e.startDate), f.string(from: e.endDate), e.volume))
                    }
                    for e in unmatched.prefix(3) {
                        print(String(format: "      only Loop: %@ %@ -> %@  %.4f U", e.type,
                                     f.string(from: e.startDate), f.string(from: e.endDate), e.volume))
                    }
                }
            }
        }

        guard compared > 0 else {
            print("no comparable cycles (skipped \(skipped))")
            return
        }
        print("EvalCore dose SET vs deployed-Loop capture  [variant: \(variant)]")
        print("  cycles compared: \(compared)   (skipped \(skipped))")
        print(String(format: "  mean lookback: ours %.1f h vs Loop %.1f h (compared on the common span)",
                     ourWindowH / Double(compared), loopWindowH / Double(compared)))
        print("  set identical: \(identical) / \(compared) "
              + String(format: "(%.0f%%)", 100.0 * Double(identical) / Double(compared)))
        print(String(format: "  *** WORST per-cycle: %.4f U only-ours, %.4f U only-Loop, %.4f U volume Δ ***",
                     worstExtra, worstMissing, worstVolume))
        print(String(format: "  summed units across compared cycles: ours %.3f U vs Loop %.3f U (Δ %+.3f U)",
                     totalOurs, totalLoop, totalOurs - totalLoop))
        if !offenders.isEmpty, !verbose {
            let f = ISO8601DateFormatter()
            print("  worst cycles:")
            for o in offenders.sorted(by: { $0.3 > $1.3 }).prefix(5) {
                print("    \(f.string(from: o.0))  only-ours \(o.1)  only-Loop \(o.2)"
                      + String(format: "  vol Δ %.4f U", o.3))
            }
        }
    }
}
