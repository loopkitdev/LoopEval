// CompareCommand.swift — `loop-eval compare` subcommand

import ArgumentParser
import EvalCore
import Foundation

struct CompareCommand: ParsableCommand {

    static let configuration = CommandConfiguration(
        commandName: "compare",
        abstract: "Compare two saved evaluation snapshots side-by-side.",
        discussion: """
        Loads two JSON snapshots produced by `loop-eval evaluate --save` and
        prints a delta table showing how each metric changed from A → B.

        Arrow legend:
          ▼  decreased   ▲  increased
          ✓  improved    ✗  regressed   (primary/RMSE/OPR/UPR: lower is better)

        Example:
          loop-eval evaluate ... --save before.json
          # (edit LoopAlgorithm, rebuild)
          loop-eval evaluate ... --save after.json
          loop-eval compare before.json after.json
        """
    )

    // MARK: – Arguments

    @Argument(help: "Baseline snapshot JSON (A).")
    var baseline: String

    @Argument(help: "Candidate snapshot JSON (B).")
    var candidate: String

    @Flag(name: .long, help: "Show per-horizon detail table in addition to the summary.")
    var detail: Bool = false

    @Option(name: .long, help: "Write a comparison HTML report to this path")
    var html: String?

    // MARK: – Run

    func run() throws {
        let a = try loadSnapshot(baseline)
        let b = try loadSnapshot(candidate)

        let ruler = String(repeating: "━", count: 76)
        let sep   = String(repeating: "─", count: 76)

        // ── Header ───────────────────────────────────────────────────────────────
        print(ruler)
        print(" loop-eval compare")
        print(" A: \(snapshotTitle(a, path: baseline))")
        print(" B: \(snapshotTitle(b, path: candidate))")
        print(ruler)

        // ── Per-horizon detail (opt-in) ───────────────────────────────────────────
        if detail {
            printHorizonTable(a: a.score, b: b.score, sep: sep, ruler: ruler)
        }

        // ── Weighted summary ──────────────────────────────────────────────────────
        print(" Weighted summary (Gaussian peak 90 min, σ=60 min)")
        print(sep)

        let rows: [(label: String, a: Double, b: Double, lowerBetter: Bool)] = [
            ("Primary  (OPR+UPR)", a.score.primaryScore,                  b.score.primaryScore,                  true),
            ("OPR (overprediction)", a.score.weightedOverpredictionRisk,   b.score.weightedOverpredictionRisk,   true),
            ("UPR (underprediction)", a.score.weightedUnderpredictionRisk, b.score.weightedUnderpredictionRisk,  true),
            ("RMSE       (mg/dL)", a.score.weightedRMSE,               b.score.weightedRMSE,               true),
            ("BGRI              ", a.score.weightedBGRI,               b.score.weightedBGRI,               true),
        ]

        for row in rows {
            print(summaryLine(row.label, valA: row.a, valB: row.b, lowerBetter: row.lowerBetter))
        }

        print(ruler)

        // ── HTML report (opt-in) ─────────────────────────────────────────────────
        if let htmlPath = html {
            let meta = ComparisonMeta(
                baselineLabel: a.label ?? URL(fileURLWithPath: baseline).lastPathComponent,
                candidateLabel: b.label ?? URL(fileURLWithPath: candidate).lastPathComponent,
                intervalStart: a.intervalStart,
                intervalEnd: a.intervalEnd,
                runDate: Date()
            )
            try ComparisonHTMLGenerator.write(
                baseline: a.score,
                candidate: b.score,
                meta: meta,
                to: URL(fileURLWithPath: htmlPath)
            )
            print("Comparison report written → \(htmlPath)")
        }
    }

    // MARK: – Horizon table

    private func printHorizonTable(a: AggregateScore, b: AggregateScore, sep: String, ruler: String) {
        // Build lookup: horizon → metrics
        let bMap = Dictionary(uniqueKeysWithValues: b.horizonMetrics.map { ($0.horizon, $0) })

        let colHeader = " Horizon │      RMSE (A→B)      │      OPR  (A→B)      │      UPR  (A→B)"
        let colDiv    = "─────────┼──────────────────────┼──────────────────────┼──────────────────────"
        print(colHeader)
        print(colDiv)

        for mA in a.horizonMetrics {
            guard let mB = bMap[mA.horizon] else { continue }
            let hMin = Int(mA.horizon / 60)
            let rmse = deltaCell(mA.rmse,  mB.rmse,  fmt: "%.1f", lowerBetter: true)
            let opr  = deltaCell(mA.opr,   mB.opr,   fmt: "%.3f", lowerBetter: true)
            let upr  = deltaCell(mA.upr,   mB.upr,   fmt: "%.3f", lowerBetter: true)
            print(String(format: " %4d min │ %@ │ %@ │ %@", hMin, rmse, opr, upr))
        }

        print(ruler)
    }

    // MARK: – Formatting helpers

    /// Single summary line: "Label    A → B   Δ ±x   ▼/▲ pct%  ✓/✗"
    private func summaryLine(
        _ label: String,
        valA: Double,
        valB: Double,
        lowerBetter: Bool
    ) -> String {
        let delta = valB - valA
        let pct   = valA != 0 ? (delta / abs(valA)) * 100 : 0
        let arrow = delta < 0 ? "▼" : (delta > 0 ? "▲" : "=")
        let improved = lowerBetter ? (delta < 0) : (delta > 0)
        let verdict  = abs(delta) < 1e-9 ? "  " : (improved ? "✓" : "✗")

        // Choose precision based on magnitude
        let fmt = abs(valA) >= 10 ? "%.2f" : "%.4f"
        let aStr = String(format: fmt, valA)
        let bStr = String(format: fmt, valB)
        let dStr = delta >= 0
            ? String(format: "+\(fmt)", delta)
            : String(format: fmt,       delta)
        let pStr = pct >= 0
            ? String(format: "+%.1f%%", pct)
            : String(format: "%.1f%%",  pct)

        let labelPad = label.padding(toLength: 22, withPad: " ", startingAt: 0)
        let aStrPad  = String(repeating: " ", count: max(0, 8 - aStr.count)) + aStr
        let bStrPad  = bStr.padding(toLength: 8, withPad: " ", startingAt: 0)
        let dStrPad  = dStr.padding(toLength: 10, withPad: " ", startingAt: 0)
        let pStrPad  = pStr.padding(toLength: 7, withPad: " ", startingAt: 0)
        return "  \(labelPad)  \(aStrPad) → \(bStrPad)  Δ \(dStrPad)  \(arrow) \(pStrPad)  \(verdict)"
    }

    /// Compact 20-char cell for the per-horizon table.
    private func deltaCell(_ a: Double, _ b: Double, fmt: String, lowerBetter: Bool) -> String {
        let arrow    = b < a ? "▼" : (b > a ? "▲" : "=")
        let improved = lowerBetter ? (b < a) : (b > a)
        let mark     = abs(b - a) < 1e-9 ? " " : (improved ? "✓" : "✗")
        let aStr = String(format: fmt, a)
        let bStr = String(format: fmt, b)
        // Pad to fixed width: "X.XXX → X.XXX ▼✓" = ~20 chars
        let aP = aStr.padding(toLength: 6, withPad: " ", startingAt: 0)
        let bP = bStr.padding(toLength: 6, withPad: " ", startingAt: 0)
        return "\(aP) → \(bP) \(arrow) \(mark)"
    }

    private func snapshotTitle(_ snap: EvalSnapshot, path: String) -> String {
        let df = DateFormatter()
        df.dateFormat = "yyyy-MM-dd"
        df.locale = Locale(identifier: "en_US_POSIX")
        let start  = df.string(from: snap.intervalStart)
        let end    = df.string(from: snap.intervalEnd)
        let ran    = df.string(from: snap.runDate)
        let lbl    = snap.label ?? URL(fileURLWithPath: path).lastPathComponent
        return "\(lbl)  [\(start) → \(end), run \(ran), \(snap.insulinType)]"
    }

    private func loadSnapshot(_ path: String) throws -> EvalSnapshot {
        let url  = URL(fileURLWithPath: path)
        let data = try Data(contentsOf: url)
        let dec  = JSONDecoder()
        dec.dateDecodingStrategy = .iso8601
        return try dec.decode(EvalSnapshot.self, from: data)
    }
}
