import ArgumentParser
import Foundation
import LoopAlgorithm

/// Verify OUR insulin-effect computation against ground truth captured from a real
/// deployed Loop.
///
/// The instrumented Loop bench rig writes, per cycle, the EXACT dose set it handed to
/// `DoseStore.getGlucoseEffects` together with the effect array that call returned and the
/// ISF in force — all in one atomic record. Feeding those same doses through
/// LoopAlgorithm's `glucoseEffects` and diffing against the captured effect isolates
/// insulin-effect GENERATION with no reconstruction, no warmup and no time alignment.
///
/// Compares CUMULATIVE DELTAS (value − value[0]), because that is all `predictGlucose`
/// consumes; the absolute offset of an effect curve is arbitrary.
struct InsulinEffectCheckCommand: ParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "insulin-effect-check",
        abstract: "Diff our insulin effect against a deployed-Loop capture (JSONL from the rig)."
    )

    @Argument(help: "loopeval_forecast_dump.jsonl from the instrumented rig")
    var dumpPath: String

    @Option(help: "Which captured variant to check: trimmed | untrimmed")
    var variant: String = "trimmed"

    @Option(help: "Only cycles with this dosingDecision reason (empty = all)")
    var reason: String = "loop"

    @Flag(help: "Print the worst cycle point-by-point")
    var verbose: Bool = false

    func run() throws {
        let text = try String(contentsOfFile: dumpPath, encoding: .utf8)
        var errors: [(Date, Double, Int)] = []
        var skipped = 0

        for line in text.split(separator: "\n") {
            guard let data = line.data(using: .utf8),
                  let obj = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
            else { continue }
            if !reason.isEmpty, (obj["reason"] as? String) != reason { continue }
            guard let capAll = obj["doseCapture"] as? [String: Any],
                  let cap = capAll[variant] as? [String: Any],
                  let effect = cap["effect"] as? [[Double]],
                  let doseJSON = cap["trimmed"] as? [[String: Any]],
                  let isf = cap["isf"] as? Double,
                  !effect.isEmpty, !doseJSON.isEmpty
            else { skipped += 1; continue }

            // Rebuild the dose set exactly as captured.
            var doses: [BasalRelativeDose] = []
            for d in doseJSON {
                guard let type = d["type"] as? String,
                      let start = d["start"] as? Double,
                      let end = d["end"] as? Double,
                      let value = d["value"] as? Double
                else { continue }
                let s = Date(timeIntervalSince1970: start)
                let e = Date(timeIntervalSince1970: end)
                let hours = max(0, end - start) / 3600.0
                let unit = (d["unit"] as? String) ?? "units"
                let delivered = d["deliveredUnits"] as? Double
                // Loop's `unitsInDeliverableIncrements`: deliveredUnits when present,
                // else programmedUnits (rounded to 0.025 U only for a rate-based dose).
                // Prefer Loop's OWN `unitsInDeliverableIncrements` when the capture carries it.
                // Deriving it (programmedUnits rounded to 0.025 U) lands on the wrong side of a
                // quantization boundary for in-progress mutable doses, where deliveredUnits is nil.
                let programmed = (unit == "unitsPerHour") ? value * hours : value
                let volume: Double = (d["unitsInDeliverableIncrements"] as? Double)
                    ?? delivered
                    ?? ((unit == "unitsPerHour") ? (programmed * 40).rounded() / 40 : programmed)
                if type == "bolus" {
                    doses.append(BasalRelativeDose(type: .bolus, startDate: s, endDate: e, volume: volume))
                } else if type == "basal" {
                    // LoopKit `DoseEntry.netBasalUnits` returns 0 for `.basal` — a SCHEDULED
                    // basal dose is the baseline and contributes no glucose effect. LoopAlgorithm's
                    // BasalRelativeDose has no such case (`.basal(scheduledRate)` always computes
                    // volume − scheduledRate×hours), so mapping a scheduled dose through it yields a
                    // small non-zero net (e.g. 0.350 delivered vs 0.357 scheduled = −0.007 U) that
                    // accumulates across the ~18 scheduled doses in a cycle. Force net-zero.
                    continue
                } else {
                    let sched = (d["scheduledBasalRate"] as? Double) ?? 0
                    doses.append(BasalRelativeDose(type: .basal(scheduledRate: sched),
                                                  startDate: s, endDate: e, volume: volume))
                }
            }
            guard !doses.isEmpty else { skipped += 1; continue }

            let first = Date(timeIntervalSince1970: effect.first![0])
            let last = Date(timeIntervalSince1970: effect.last![0])
            let isfHistory = [AbsoluteScheduleValue(
                startDate: first.addingTimeInterval(-86400 * 2),
                endDate: last.addingTimeInterval(86400 * 2),
                value: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: isf))]

            let ours = doses.glucoseEffects(insulinSensitivityHistory: isfHistory, from: first, to: last)
            guard ours.count > 1 else { skipped += 1; continue }

            // Index ours by timestamp so we compare like-for-like points.
            var byTime: [Double: Double] = [:]
            for e in ours {
                byTime[e.startDate.timeIntervalSince1970.rounded()] =
                    e.quantity.doubleValue(for: .milligramsPerDeciliter)
            }
            guard let ourFirst = byTime[first.timeIntervalSince1970.rounded()] else { skipped += 1; continue }
            let refFirst = effect.first![1]

            var worst = 0.0
            var matched = 0
            for pt in effect {
                guard let o = byTime[pt[0].rounded()] else { continue }
                matched += 1
                worst = max(worst, abs((o - ourFirst) - (pt[1] - refFirst)))
            }
            guard matched > 1 else { skipped += 1; continue }
            let t = (obj["t"] as? String).flatMap(ISO8601DateFormatter().date(from:)) ?? first
            errors.append((t, worst, matched))
        }

        guard !errors.isEmpty else {
            print("no comparable cycles (skipped \(skipped)) — needs an atomic-capture dump")
            return
        }
        let vals = errors.map { $0.1 }.sorted()
        let worst = vals.last!
        let median = vals[vals.count / 2]
        let exact = vals.filter { $0 < 0.001 }.count
        print("EvalCore insulin effect vs deployed-Loop capture  [variant: \(variant)]")
        print("  cycles compared: \(errors.count)   (skipped \(skipped))")
        print("  *** WORST |Δ| = \(String(format: "%.8f", worst)) mg/dL ***")
        print("  median |Δ| = \(String(format: "%.8f", median))   exact(<0.001): \(exact)/\(errors.count)")

        if verbose, let w = errors.max(by: { $0.1 < $1.1 }) {
            let f = ISO8601DateFormatter()
            print("  worst cycle: \(f.string(from: w.0))  (\(w.2) points)")
        }
    }
}
