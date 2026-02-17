// OutputFormatter.swift — output rendering for loop-eval results

import EvalCore
import Foundation

enum OutputFormatter {

    // MARK: – Table output

    /// Print a human-readable summary table to stdout.
    static func printTable(
        score: AggregateScore,
        interval: DateInterval,
        config: EvalConfig,
        insulinTypeName: String,
        predictionCount: Int,
        skippedCount: Int,
        durationSeconds: Double
    ) {
        let ruler = String(repeating: "━", count: 70)
        let sep   = String(repeating: "─", count: 70)

        // Header
        let days = interval.duration / 86400
        let daysStr = String(format: "%.0f", days)
        print(ruler)
        print(" loop-eval  \(formatDate(interval.start)) → \(formatDate(interval.end))  (\(daysStr) days)")

        let rcStr      = config.useIntegralRC ? "Integral" : "Standard"
        let futureStr  = config.includeFutureInsulin ? "on" : "off"
        let kalmanStr  = config.kalmanSmoothing ? "on" : "off"
        print(" Insulin: \(insulinTypeName)  |  RC: \(rcStr)  |  Future insulin: \(futureStr)  |  Kalman: \(kalmanStr)")
        print(" Predictions: \(predictionCount)  |  Skipped: \(skippedCount)  |  Eval time: \(String(format: "%.1f", durationSeconds))s")
        print(ruler)

        // Column header
        let colHeader = " Horizon │    N    │ RMSE  │  MAE  │  Bias  │  P10   │  P90   │ LBGI │ HBGI │ BGRI"
        let colDiv    = "─────────┼─────────┼───────┼───────┼────────┼────────┼────────┼──────┼──────┼──────"
        print(colHeader)
        print(colDiv)

        // Find the peak-weight horizon (Gaussian peak at 150 min)
        let peakHorizon: TimeInterval = 150 * 60
        let peakIndex = score.horizonMetrics.indices.min(by: {
            abs(score.horizonMetrics[$0].horizon - peakHorizon) <
            abs(score.horizonMetrics[$1].horizon - peakHorizon)
        })

        // Rows
        for (i, m) in score.horizonMetrics.enumerated() {
            let hMin = Int(m.horizon / 60)
            let marker = (i == peakIndex) ? " ◀" : ""
            let bias = m.meanError >= 0
                ? String(format: " +%.1f", m.meanError)
                : String(format: " %.1f", m.meanError)
            let p10 = m.percentile10 >= 0
                ? String(format: " +%.1f", m.percentile10)
                : String(format: " %.1f", m.percentile10)
            let p90 = m.percentile90 >= 0
                ? String(format: " +%.1f", m.percentile90)
                : String(format: " %.1f", m.percentile90)

            let row = String(format: " %4d min │ %7d │ %5.1f │ %5.1f │%@  │%@  │%@  │ %4.2f │ %4.2f │ %4.2f%@",
                hMin,
                m.sampleCount,
                m.rmse,
                m.mae,
                bias,
                p10,
                p90,
                m.lbgi,
                m.hbgi,
                m.bgri,
                marker
            )
            print(row)
        }

        print(ruler)

        // Weighted summary
        let pkMin = Int(peakHorizon / 60)
        let sigMin = 60
        print(" Weighted score (peak \(pkMin) min, σ=\(sigMin) min)")
        print(String(format: "   RMSE:       %5.1f mg/dL", score.weightedRMSE))
        print(String(format: "   BGRI:       %5.2f", score.weightedBGRI))
        print(String(format: "   Low RMSE:   %5.1f mg/dL", score.weightedLowRMSE))
        print(String(format: "   High RMSE:  %5.1f mg/dL", score.weightedHighRMSE))
        print(String(format: "   Primary:    %5.2f  (BGRI×0.5 + RMSE×0.5 normalized)", score.primaryScore))
        print(ruler)

        _ = sep  // suppress unused-variable warning
    }

    // MARK: – JSON output

    /// Print the AggregateScore as pretty-printed JSON to stdout.
    static func printJSON(score: AggregateScore) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.dateEncodingStrategy = .iso8601
        let data = try encoder.encode(score)
        if let str = String(data: data, encoding: .utf8) {
            print(str)
        }
    }

    // MARK: – CSV output

    /// Print one row per horizon as CSV to stdout.
    static func printCSV(score: AggregateScore) {
        // Header
        let header = "horizon_min,n,rmse,mae,bias,p10,p90,lbgi,hbgi,bgri,low_wrmse,high_wrmse"
        print(header)

        // Rows
        for m in score.horizonMetrics {
            let hMin = Int(m.horizon / 60)
            let row = "\(hMin),\(m.sampleCount)," +
                      String(format: "%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f",
                             m.rmse, m.mae, m.meanError,
                             m.percentile10, m.percentile90,
                             m.lbgi, m.hbgi, m.bgri,
                             m.lowWeightedRMSE, m.highWeightedRMSE)
            print(row)
        }

        // Weighted summary footer (as CSV comment)
        print(String(format: "# weighted: rmse=%.4f bgri=%.4f low_rmse=%.4f high_rmse=%.4f primary=%.4f",
                     score.weightedRMSE, score.weightedBGRI,
                     score.weightedLowRMSE, score.weightedHighRMSE,
                     score.primaryScore))
    }

    // MARK: – Helpers

    private static func formatDate(_ date: Date) -> String {
        let df = DateFormatter()
        df.dateFormat = "yyyy-MM-dd"
        df.locale = Locale(identifier: "en_US_POSIX")
        return df.string(from: date)
    }
}
