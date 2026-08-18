import ArgumentParser
import Foundation
import LoopAlgorithm

/// Verify OUR carb-effect computation against ground truth captured from a real deployed Loop.
///
/// The rig captures, atomically inside `CarbStore.getGlucoseEffects`, the carb ENTRIES, the
/// effect they produced, and the ICE velocities that drive dynamic absorption — plus CR/ISF
/// and the default absorption times. Carb absorption is the most stateful part of the
/// algorithm (observed absorption depends on the ICE history, not just the entry), so without
/// the exact inputs a mismatch is unattributable and a match could be luck.
///
/// Compares CUMULATIVE DELTAS, since that is all `predictGlucose` consumes.
struct CarbEffectCheckCommand: ParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "carb-effect-check",
        abstract: "Diff our carb effect against a deployed-Loop capture (JSONL from the rig)."
    )

    @Argument(help: "loopeval_fc_<hour>.jsonl from the instrumented rig")
    var dumpPath: String

    @Flag(help: "Print each compared cycle")
    var verbose: Bool = false

    func run() throws {
        let text = try String(contentsOfFile: dumpPath, encoding: .utf8)
        var errors: [(String, Double, Int)] = []
        var skipped = 0

        for line in text.split(separator: "\n") {
            guard let data = line.data(using: .utf8),
                  let obj = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
                  let cap = obj["carbCapture"] as? [String: Any],
                  let entriesJSON = cap["entries"] as? [[String: Any]],
                  let effect = cap["effect"] as? [[Double]],
                  let velJSON = cap["velocities"] as? [[Double]],
                  let cr = cap["carbRatio"] as? Double,
                  let isf = cap["isf"] as? Double,
                  !entriesJSON.isEmpty, effect.count > 1, cr > 0, isf > 0
            else { skipped += 1; continue }

            let entries: [FixtureCarbEntry] = entriesJSON.compactMap { e in
                guard let start = e["start"] as? Double, let grams = e["grams"] as? Double else { return nil }
                return FixtureCarbEntry(
                    absorptionTime: e["absorptionTime"] as? Double,
                    startDate: Date(timeIntervalSince1970: start),
                    quantity: LoopQuantity(unit: .gram, doubleValue: grams),
                    foodType: e["foodType"] as? String)
            }
            guard !entries.isEmpty else { skipped += 1; continue }

            let velocities: [GlucoseEffectVelocity] = velJSON.compactMap { v in
                guard v.count >= 3 else { return nil }
                return GlucoseEffectVelocity(
                    startDate: Date(timeIntervalSince1970: v[0]),
                    endDate: Date(timeIntervalSince1970: v[1]),
                    quantity: LoopQuantity(unit: .milligramsPerDeciliterPerSecond, doubleValue: v[2]))
            }

            let span = (Date(timeIntervalSince1970: effect.first![0]).addingTimeInterval(-86400 * 2),
                        Date(timeIntervalSince1970: effect.last![0]).addingTimeInterval(86400 * 2))
            let crSched = [AbsoluteScheduleValue(startDate: span.0, endDate: span.1, value: cr)]
            let isfSched = [AbsoluteScheduleValue(startDate: span.0, endDate: span.1,
                                                  value: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: isf))]

            let defaults = (cap["defaultAbsorptionTimes"] as? [Double]) ?? []
            let medium = defaults.count > 1 ? defaults[1] : CarbMath.defaultAbsorptionTime

            let statuses = entries.map(to: velocities, carbRatio: crSched, insulinSensitivity: isfSched,
                                       defaultAbsorptionTime: medium)
            let ours = statuses.dynamicGlucoseEffects(
                from: Date(timeIntervalSince1970: effect.first![0]),
                to: Date(timeIntervalSince1970: effect.last![0]),
                carbRatios: crSched, insulinSensitivities: isfSched,
                defaultAbsorptionTime: medium)
            guard ours.count > 1 else { skipped += 1; continue }

            var byTime: [Double: Double] = [:]
            for e in ours {
                byTime[e.startDate.timeIntervalSince1970.rounded()] =
                    e.quantity.doubleValue(for: .milligramsPerDeciliter)
            }
            guard let ourFirst = byTime[effect.first![0].rounded()] else { skipped += 1; continue }
            let refFirst = effect.first![1]

            var worst = 0.0, matched = 0
            for pt in effect {
                guard let o = byTime[pt[0].rounded()] else { continue }
                matched += 1
                worst = max(worst, abs((o - ourFirst) - (pt[1] - refFirst)))
            }
            guard matched > 1 else { skipped += 1; continue }
            errors.append(((obj["t"] as? String) ?? "?", worst, matched))
            if verbose {
                print(String(format: "  %@  worst %.6f  (%d pts, %d entries)",
                             (obj["t"] as? String) ?? "?", worst, matched, entries.count))
            }
        }

        guard !errors.isEmpty else {
            print("no comparable cycles (skipped \(skipped)) — needs carbCapture records")
            return
        }
        let vals = errors.map { $0.1 }.sorted()
        print("EvalCore carb effect vs deployed-Loop capture")
        print("  cycles compared: \(errors.count)   (skipped \(skipped))")
        print("  *** WORST |Δ| = \(String(format: "%.8f", vals.last!)) mg/dL ***")
        print("  median |Δ| = \(String(format: "%.8f", vals[vals.count/2]))   exact(<0.001): \(vals.filter { $0 < 0.001 }.count)/\(errors.count)")
    }
}
