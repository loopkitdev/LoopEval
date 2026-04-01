// ChartHTMLGenerator.swift — generates a self-contained ODR/UDR horizon chart HTML file.
//
// Usage (single run):
//   ChartHTMLGenerator.write(score:, meta:, to: url)
//
// Usage (multi-run — reads sidecar JSON if present, appends, regenerates):
//   ChartHTMLGenerator.writeAppending(score:, meta:, to: url)
//
// The chart file is accompanied by a JSON sidecar at <name>.runs.json that
// accumulates all runs. Re-generating the chart reads the sidecar so all
// previous runs remain visible.

import EvalCore
import Foundation

// MARK: – Run metadata bundled with a score

struct ChartRun: Codable {
    var label: String          // e.g. "2026-03-20 → 2026-03-27"
    var runDate: String        // ISO8601
    var odrByHorizon: [Double] // one per horizon, same order as horizonMinutes
    var udrByHorizon: [Double]
    var horizonMinutes: [Int]
    var weightedODR: Double
    var weightedUDR: Double
    var primaryScore: Double
    var weightedRMSE: Double
}

enum ChartHTMLGenerator {

    // MARK: – Public API

    /// Write (or overwrite) a chart showing only this run.
    static func write(score: AggregateScore, meta: ChartRunMeta, to url: URL) throws {
        let run = makeRun(score: score, meta: meta)
        try writeHTML([run], to: url)
    }

    /// Append this run to the sidecar and regenerate the chart with all runs.
    static func writeAppending(score: AggregateScore, meta: ChartRunMeta, to url: URL) throws {
        let sidecar = sidecarURL(for: url)
        var runs = loadSidecar(sidecar)
        let run = makeRun(score: score, meta: meta)
        runs.append(run)
        try saveSidecar(runs, to: sidecar)
        try writeHTML(runs, to: url)
    }

    // MARK: – Helpers

    private static func sidecarURL(for htmlURL: URL) -> URL {
        htmlURL.deletingPathExtension().appendingPathExtension("runs.json")
    }

    private static func loadSidecar(_ url: URL) -> [ChartRun] {
        guard let data = try? Data(contentsOf: url),
              let runs = try? JSONDecoder().decode([ChartRun].self, from: data) else {
            return []
        }
        return runs
    }

    private static func saveSidecar(_ runs: [ChartRun], to url: URL) throws {
        let enc = JSONEncoder()
        enc.outputFormatting = [.prettyPrinted]
        let data = try enc.encode(runs)
        try data.write(to: url, options: .atomic)
    }

    private static func makeRun(score: AggregateScore, meta: ChartRunMeta) -> ChartRun {
        let df = DateFormatter()
        df.dateFormat = "yyyy-MM-dd"
        df.locale = Locale(identifier: "en_US_POSIX")
        let startStr = df.string(from: meta.intervalStart)
        let endStr   = df.string(from: meta.intervalEnd)
        let label    = meta.label ?? "\(startStr) → \(endStr)"

        let iso = ISO8601DateFormatter()
        let runDate = iso.string(from: meta.runDate)

        let sorted = score.horizonMetrics.sorted { $0.horizon < $1.horizon }
        return ChartRun(
            label: label,
            runDate: runDate,
            odrByHorizon: sorted.map { $0.odr },
            udrByHorizon: sorted.map { $0.udr },
            horizonMinutes: sorted.map { Int($0.horizon / 60) },
            weightedODR: score.weightedOverdeliveryRisk,
            weightedUDR: score.weightedUnderdeliveryRisk,
            primaryScore: score.primaryScore,
            weightedRMSE: score.weightedRMSE
        )
    }

    // MARK: – HTML generation

    private static func writeHTML(_ runs: [ChartRun], to url: URL) throws {
        let html = buildHTML(runs)
        try html.write(to: url, atomically: true, encoding: .utf8)
    }

    // swiftlint:disable function_body_length
    private static func buildHTML(_ runs: [ChartRun]) -> String {
        // Build the horizon labels from the first run (they're all the same)
        let horizons = runs.first?.horizonMinutes ?? []
        let labelsJS = horizons.map { "\"\($0) min\"" }.joined(separator: ", ")

        // Color palette for multiple runs (ODR colours, UDR colours)
        // We cycle through: red, blue, green, purple for ODR
        //                   orange, cyan, lime, violet for UDR
        let odrColors = ["#e05c5c", "#5b8ef0", "#5cb85c", "#a07bd4", "#e8a838"]
        let udrColors = ["#f4a460", "#4ac8c8", "#b5e05c", "#d47bb8", "#60c8f4"]

        var datasetsJS = ""
        for (i, run) in runs.enumerated() {
            let odrColor = odrColors[i % odrColors.count]
            let udrColor = udrColors[i % udrColors.count]
            let isDashed = i > 0

            let odrData = run.odrByHorizon.map { String(format: "%.3f", $0) }.joined(separator: ", ")
            let udrData = run.udrByHorizon.map { String(format: "%.3f", $0) }.joined(separator: ", ")
            let dash    = isDashed ? "borderDash: [6, 3]," : ""
            let runLabelSafe = run.label.replacingOccurrences(of: "\"", with: "'")

            datasetsJS += """
            {
              label: 'ODR – \(runLabelSafe)',
              data: [\(odrData)],
              borderColor: '\(odrColor)', backgroundColor: '\(odrColor)22',
              borderWidth: 2.5, tension: 0.2, pointRadius: 4, fill: false,
              \(dash)
              yAxisID: 'y'
            },
            {
              label: 'UDR – \(runLabelSafe)',
              data: [\(udrData)],
              borderColor: '\(udrColor)', backgroundColor: '\(udrColor)22',
              borderWidth: 2.5, tension: 0.2, pointRadius: 4, fill: false,
              \(dash)
              yAxisID: 'y2'
            },
            """
        }

        // Score cards HTML — show all runs
        var scoreCardsHTML = ""
        for run in runs {
            let labelSafe = run.label
                .replacingOccurrences(of: "<", with: "&lt;")
                .replacingOccurrences(of: ">", with: "&gt;")
            scoreCardsHTML += """
            <div class="run-block">
              <div class="run-label">\(labelSafe)</div>
              <div class="score-box">
                <div class="score-card danger">
                  <div class="lbl">ODR — Overdelivery Risk</div>
                  <div class="val">\(String(format: "%.1f", run.weightedODR))</div>
                  <div class="lbl">weighted avg</div>
                </div>
                <div class="score-card warn-card">
                  <div class="lbl">UDR — Underdelivery Risk</div>
                  <div class="val">\(String(format: "%.1f", run.weightedUDR))</div>
                  <div class="lbl">weighted avg</div>
                </div>
                <div class="score-card primary-card">
                  <div class="lbl">Primary (ODR + UDR)</div>
                  <div class="val">\(String(format: "%.1f", run.primaryScore))</div>
                  <div class="lbl">optimization target ↓</div>
                </div>
                <div class="score-card rmse-card">
                  <div class="lbl">RMSE (weighted)</div>
                  <div class="val">\(String(format: "%.1f", run.weightedRMSE))</div>
                  <div class="lbl">mg/dL · reference</div>
                </div>
              </div>
            </div>
            """
        }

        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LoopEval — Scoring Chart</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <style>
          :root {
            --bg: #0f1117; --panel: #161b2e; --border: #252a3a;
            --text: #d0d4e8; --muted: #7a7f9a; --accent: #5b8ef0;
            --red: #e05c5c; --orange: #f4a460; --green: #5cb85c;
            --teal: #4ac8c8;
          }
          * { box-sizing: border-box; margin: 0; padding: 0; }
          body { background: var(--bg); color: var(--text);
                 font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                 font-size: 15px; line-height: 1.6; }
          .page { max-width: 960px; margin: 0 auto; padding: 40px 24px 80px; }
          h1 { font-size: 1.7rem; font-weight: 700; color: #fff; margin-bottom: 4px; }
          .subtitle { color: var(--muted); font-size: 0.92rem; margin-bottom: 36px; }
          .panel { background: var(--panel); border: 1px solid var(--border);
                   border-radius: 10px; padding: 24px; margin: 20px 0; }
          .chart-wrap { position: relative; height: 340px; margin-top: 16px; }
          .run-block { margin: 24px 0; }
          .run-label { font-size: 0.9rem; color: var(--muted); margin-bottom: 10px; font-weight: 500; }
          .score-box { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
          @media (max-width: 640px) { .score-box { grid-template-columns: 1fr 1fr; } }
          .score-card { background: #0a0d18; border: 1px solid var(--border);
                        border-radius: 8px; padding: 14px; text-align: center; }
          .score-card .val { font-size: 1.6rem; font-weight: 700; margin: 6px 0 2px; }
          .score-card .lbl { font-size: 0.75rem; color: var(--muted); }
          .score-card.danger .val { color: var(--red); }
          .score-card.warn-card .val { color: var(--orange); }
          .score-card.primary-card .val { color: var(--accent); }
          .score-card.rmse-card .val { color: var(--teal); }
          hr { border: none; border-top: 1px solid var(--border); margin: 32px 0; }
          .generated { font-size: 0.78rem; color: var(--muted); margin-top: 40px; text-align: center; }
          strong { color: #fff; }
        </style>
        </head>
        <body>
        <div class="page">
          <h1>LoopEval — ODR / UDR by Horizon</h1>
          <p class="subtitle">Overdelivery &amp; Underdelivery Risk across forecast horizons · target range 100–115 mg/dL</p>

          <div class="panel">
            <strong>Overdelivery and Underdelivery Risk by forecast horizon</strong>
            <div class="chart-wrap"><canvas id="horizonChart"></canvas></div>
          </div>

          <hr>

          \(scoreCardsHTML)

          <p class="generated">Generated \(ISO8601DateFormatter().string(from: Date())) · \(runs.count) run(s)</p>
        </div>

        <script>
        Chart.defaults.color = '#888';
        Chart.defaults.borderColor = '#252a3a';

        const labels = [\(labelsJS)];
        const datasets = [\(datasetsJS)];

        new Chart(document.getElementById('horizonChart'), {
          type: 'line',
          data: { labels, datasets },
          options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
              x: { grid: { color: '#1e2230' } },
              y: {
                type: 'linear', position: 'left',
                title: { display: true, text: 'Overdelivery Risk (ODR)', color: '#e05c5c' },
                grid: { color: '#1e2230' }, min: 0
              },
              y2: {
                type: 'linear', position: 'right',
                title: { display: true, text: 'Underdelivery Risk (UDR)', color: '#f4a460' },
                grid: { drawOnChartArea: false }, min: 0
              }
            },
            plugins: {
              legend: { labels: { color: '#aaa', boxWidth: 18, font: { size: 12 } } },
              tooltip: {
                callbacks: {
                  label: ctx => {
                    const lbl = ctx.dataset.label;
                    return lbl + ': ' + ctx.parsed.y.toFixed(1);
                  }
                }
              }
            }
          },
          plugins: [{
            id: 'peakLine',
            afterDraw(chart) {
              const { ctx, chartArea: { top, bottom }, scales: { x } } = chart;
              const px = x.getPixelForValue('90 min');
              if (!px) return;
              ctx.save();
              ctx.strokeStyle = 'rgba(91,142,240,0.35)';
              ctx.lineWidth = 1.5;
              ctx.setLineDash([4, 4]);
              ctx.beginPath(); ctx.moveTo(px, top); ctx.lineTo(px, bottom); ctx.stroke();
              ctx.fillStyle = 'rgba(91,142,240,0.6)';
              ctx.font = '11px system-ui';
              ctx.fillText('peak weight', px + 5, top + 14);
              ctx.restore();
            }
          }]
        });
        </script>
        </body>
        </html>
        """
    }
}

// MARK: – Metadata carrier

struct ChartRunMeta {
    var intervalStart: Date
    var intervalEnd: Date
    var runDate: Date = Date()
    var label: String?
}
