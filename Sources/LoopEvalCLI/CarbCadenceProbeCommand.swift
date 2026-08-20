import ArgumentParser
import Foundation
import LoopAlgorithm

/// Synthetic probe: does dynamic carb absorption depend on the ICE SAMPLE CADENCE?
///
/// bddp03 (the first 1-minute-CGM donor scored) showed our dynamic COB decaying SLOWER
/// than Loop's own recorded COB on identical entries/glucose/CSF — our absorbed carbs
/// even sat below the model's linear minimum floor. Everything previously verified
/// (rig, donors) ran at ~5-minute cadence, so cadence is the untested variable.
///
/// The probe holds the PHYSIOLOGY constant — one carb entry, ICE = a fixed known
/// counteraction curve — and presents it as velocity series at 1-minute and 5-minute
/// spacing. Any COB difference between the two runs is a cadence artifact in
/// `map(to:)` / `dynamicCarbsOnBoard`, full stop: same entry, same total effect, same
/// CSF, same clock.
struct CarbCadenceProbeCommand: ParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "carb-cadence-probe",
        abstract: "Synthetic 1-min vs 5-min ICE cadence check for dynamic carb absorption."
    )

    @Option(help: "Counteraction rate in mg/dL per 5 minutes (constant over the run)")
    var icePer5Min: Double = 5.0

    @Option(help: "Carb entry grams")
    var grams: Double = 80

    @Option(help: "CSF mg/dL per gram (ISF/CR)")
    var csf: Double = 3.6

    @Option(help: "Minutes of ICE history to feed")
    var minutes: Int = 120

    func run() throws {
        let t0 = Date(timeIntervalSince1970: 1_780_000_000)   // fixed epoch — determinism
        let entry = FixtureCarbEntry(
            absorptionTime: 3 * 3600,
            startDate: t0,
            quantity: LoopQuantity(unit: .gram, doubleValue: grams),
            foodType: nil)

        let isf = 36.0
        let cr = isf / csf
        let span0 = t0.addingTimeInterval(-86400)
        let span1 = t0.addingTimeInterval(86400)
        let crSched = [AbsoluteScheduleValue(startDate: span0, endDate: span1, value: cr)]
        let isfSched = [AbsoluteScheduleValue(startDate: span0, endDate: span1,
                                              value: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: isf))]

        func velocities(stepMin: Int) -> [GlucoseEffectVelocity] {
            // GlucoseEffectVelocity quantity is a RATE (mg/dL/min); the same physiology
            // at any cadence = same rate, finer intervals.
            let ratePerMin = icePer5Min / 5.0
            var out: [GlucoseEffectVelocity] = []
            var t = t0
            let end = t0.addingTimeInterval(TimeInterval(minutes * 60))
            while t < end {
                let e = t.addingTimeInterval(TimeInterval(stepMin * 60))
                out.append(GlucoseEffectVelocity(
                    startDate: t, endDate: e,
                    quantity: LoopQuantity(unit: .milligramsPerDeciliterPerMinute, doubleValue: ratePerMin)))
                t = e
            }
            return out
        }

        func run(stepMin: Int) -> [(Double, Double)] {
            let vels = velocities(stepMin: stepMin)
            let statuses = [entry].map(to: vels, carbRatio: crSched, insulinSensitivity: isfSched,
                                       defaultAbsorptionTime: CarbMath.defaultAbsorptionTime)
            let cob = statuses.dynamicCarbsOnBoard(
                from: t0, to: t0.addingTimeInterval(TimeInterval(minutes * 60)),
                defaultAbsorptionTime: CarbMath.defaultAbsorptionTime)
            return cob.map { ($0.startDate.timeIntervalSince(t0) / 60.0, $0.value) }
        }

        let cob1 = run(stepMin: 1)
        let cob5 = run(stepMin: 5)
        func at(_ series: [(Double, Double)], _ m: Double) -> Double? {
            series.min(by: { abs($0.0 - m) < abs($1.0 - m) }).flatMap { abs($0.0 - m) <= 2.6 ? $0.1 : nil }
        }
        let expectedAbsorbedPerMin = icePer5Min / 5.0 / csf   // g/min the ICE implies

        print("carb-cadence probe: \(grams) g entry, ICE \(icePer5Min) mg/dL per 5 min, CSF \(csf)")
        print("  (ICE-implied absorption \(String(format: "%.3f", expectedAbsorbedPerMin)) g/min)")
        print("  t+min      COB@1min   COB@5min      Δ")
        var worst = 0.0
        print("  (timeline points: 1min=\(cob1.count) 5min=\(cob5.count); first at t+\(cob1.first.map { String(format: "%.1f", $0.0) } ?? "-")/\(cob5.first.map { String(format: "%.1f", $0.0) } ?? "-") min)")
        for m in stride(from: 0, through: Double(minutes), by: 10) {
            guard let a = at(cob1, m), let b = at(cob5, m) else { continue }
            worst = Swift.max(worst, abs(a - b))
            print(String(format: "   %4.0f     %8.2f   %8.2f   %+7.2f", m, a, b, a - b))
        }
        print(String(format: "  *** WORST |Δ COB| between cadences = %.3f g ***", worst))
    }
}
