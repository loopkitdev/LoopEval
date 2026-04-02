// ComparisonHTMLGenerator.swift — generates a self-contained comparison HTML report
//
// Compares two AggregateScore values (baseline vs candidate) with:
//   - Verdict banner showing RMSE change
//   - RMSE/BGRI dual-axis chart (baseline solid, candidate dashed)
//   - Score cards grid
//   - Per-horizon delta table

import EvalCore
import Foundation

// MARK: – Metadata

struct ComparisonMeta {
    var baselineLabel: String
    var candidateLabel: String
    var intervalStart: Date
    var intervalEnd: Date
    var runDate: Date
}

// MARK: – Generator

enum ComparisonHTMLGenerator {

    /// Write a comparison report to the given URL.
    static func write(
        baseline: AggregateScore,
        candidate: AggregateScore,
        meta: ComparisonMeta,
        to url: URL
    ) throws {
        let html = buildHTML(baseline: baseline, candidate: candidate, meta: meta)
        try html.write(to: url, atomically: true, encoding: .utf8)
    }

    // MARK: – HTML generation

    // swiftlint:disable function_body_length
    private static func buildHTML(
        baseline: AggregateScore,
        candidate: AggregateScore,
        meta: ComparisonMeta
    ) -> String {

        // ── Verdict calculation (based on RMSE) ───────────────────────────────────
        let rmseDelta = candidate.weightedRMSE - baseline.weightedRMSE
        let rmsePct = baseline.weightedRMSE != 0
            ? (rmseDelta / abs(baseline.weightedRMSE)) * 100
            : 0

        let improved = rmseDelta < 0
        let neutral = abs(rmsePct) < 1.0

        let verdictColor: String
        let verdictIcon: String
        let verdictText: String

        if neutral {
            verdictColor = "#b8a038"  // yellow
            verdictIcon = "≈"
            verdictText = String(format: "RMSE unchanged (%.1f%%)", abs(rmsePct))
        } else if improved {
            verdictColor = "#5cb85c"  // green
            verdictIcon = "✓"
            verdictText = String(format: "RMSE improved %.1f%% %@", abs(rmsePct), verdictIcon)
        } else {
            verdictColor = "#e05c5c"  // red
            verdictIcon = "✗"
            verdictText = String(format: "RMSE regressed %.1f%% %@", abs(rmsePct), verdictIcon)
        }

        // ── Chart data ────────────────────────────────────────────────────────────
        let baselineSorted = baseline.horizonMetrics.sorted { $0.horizon < $1.horizon }
        let candidateSorted = candidate.horizonMetrics.sorted { $0.horizon < $1.horizon }

        let horizons = baselineSorted.map { Int($0.horizon / 60) }
        let labelsJS = horizons.map { "\"\($0) min\"" }.joined(separator: ", ")

        let baselineRMSE = baselineSorted.map { String(format: "%.1f", $0.rmse) }.joined(separator: ", ")
        let baselineBGRI = baselineSorted.map { String(format: "%.2f", $0.bgri) }.joined(separator: ", ")
        let candidateRMSE = candidateSorted.map { String(format: "%.1f", $0.rmse) }.joined(separator: ", ")
        let candidateBGRI = candidateSorted.map { String(format: "%.2f", $0.bgri) }.joined(separator: ", ")

        // ── Score cards ───────────────────────────────────────────────────────────
        func deltaCard(_ label: String, baseVal: Double, candVal: Double, colorClass: String, fmt: String = "%.1f") -> String {
            let delta = candVal - baseVal
            let pct = baseVal != 0 ? (delta / abs(baseVal)) * 100 : 0
            let arrow = delta < 0 ? "▼" : (delta > 0 ? "▲" : "=")
            let mark = abs(delta) < 1e-9 ? "" : (delta < 0 ? "✓" : "✗")
            let deltaStr = String(format: "Δ \(fmt) %@ %.1f%% %@", delta, arrow, abs(pct), mark)

            return """
            <div class="score-card \(colorClass)">
              <div class="lbl">\(label)</div>
              <div class="val">\(String(format: fmt, candVal))</div>
              <div class="delta">\(deltaStr)</div>
            </div>
            """
        }

        let baselineCardsHTML = """
        <div class="row-label">Baseline: \(escapeHTML(meta.baselineLabel))</div>
        <div class="score-row">
          <div class="score-card rmse-card"><div class="lbl">RMSE</div><div class="val">\(String(format: "%.1f", baseline.weightedRMSE))</div></div>
          <div class="score-card bgri-card"><div class="lbl">BGRI</div><div class="val">\(String(format: "%.2f", baseline.weightedBGRI))</div></div>
        </div>
        """

        let candidateCardsHTML = """
        <div class="row-label">Candidate: \(escapeHTML(meta.candidateLabel))</div>
        <div class="score-row">
          \(deltaCard("RMSE", baseVal: baseline.weightedRMSE, candVal: candidate.weightedRMSE, colorClass: "rmse-card"))
          \(deltaCard("BGRI", baseVal: baseline.weightedBGRI, candVal: candidate.weightedBGRI, colorClass: "bgri-card", fmt: "%.2f"))
        </div>
        """

        // ── Per-horizon table ─────────────────────────────────────────────────────
        let candidateMap = Dictionary(uniqueKeysWithValues: candidateSorted.map { ($0.horizon, $0) })
        var tableRows = ""
        for bm in baselineSorted {
            guard let cm = candidateMap[bm.horizon] else { continue }
            let hMin = Int(bm.horizon / 60)
            let rmseCell = deltaCell(bm.rmse, cm.rmse, fmt: "%.1f")
            let bgriCell = deltaCell(bm.bgri, cm.bgri, fmt: "%.2f")
            tableRows += "<tr><td>\(hMin) min</td><td>\(rmseCell)</td><td>\(bgriCell)</td></tr>\n"
        }

        // ── Timestamp ─────────────────────────────────────────────────────────────
        let df = DateFormatter()
        df.dateFormat = "yyyy-MM-dd"
        df.locale = Locale(identifier: "en_US_POSIX")
        let startStr = df.string(from: meta.intervalStart)
        let endStr = df.string(from: meta.intervalEnd)

        let iso = ISO8601DateFormatter()
        let runDateStr = iso.string(from: meta.runDate)

        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LoopEval — Comparison Report</title>
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
          .subtitle { color: var(--muted); font-size: 0.92rem; margin-bottom: 24px; }

          /* Verdict banner */
          .verdict { padding: 16px 24px; border-radius: 8px; margin-bottom: 24px;
                     font-size: 1.1rem; font-weight: 600; text-align: center; }

          .panel { background: var(--panel); border: 1px solid var(--border);
                   border-radius: 10px; padding: 24px; margin: 20px 0; }
          .chart-wrap { position: relative; height: 340px; margin-top: 16px; }

          /* Score cards */
          .row-label { font-size: 0.9rem; color: var(--muted); margin: 16px 0 8px; font-weight: 500; }
          .score-row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
          @media (max-width: 640px) { .score-row { grid-template-columns: 1fr 1fr; } }
          .score-card { background: #0a0d18; border: 1px solid var(--border);
                        border-radius: 8px; padding: 14px; text-align: center; }
          .score-card .val { font-size: 1.6rem; font-weight: 700; margin: 6px 0 2px; }
          .score-card .lbl { font-size: 0.75rem; color: var(--muted); }
          .score-card .delta { font-size: 0.72rem; color: var(--muted); margin-top: 4px; }
          .score-card.rmse-card .val { color: var(--teal); }
          .score-card.bgri-card .val { color: var(--orange); }

          /* Table */
          table { width: 100%; border-collapse: collapse; margin-top: 16px; }
          th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }
          th { color: var(--muted); font-size: 0.8rem; font-weight: 500; }
          td { font-size: 0.9rem; font-family: "SF Mono", Monaco, monospace; }

          hr { border: none; border-top: 1px solid var(--border); margin: 32px 0; }
          .footer { font-size: 0.78rem; color: var(--muted); margin-top: 40px; text-align: center; }
          strong { color: #fff; }
        </style>
        </head>
        <body>
        <div class="page">
          <h1>LoopEval — Comparison Report</h1>
          <p class="subtitle">\(startStr) → \(endStr)</p>

          <div class="verdict" style="background: \(verdictColor)22; border: 1px solid \(verdictColor); color: \(verdictColor);">
            \(verdictText)
          </div>

          <div class="panel">
            <strong>RMSE / BGRI by Horizon</strong>
            <div class="chart-wrap"><canvas id="compChart"></canvas></div>
          </div>

          <div class="panel">
            <strong>Score Cards</strong>
            \(baselineCardsHTML)
            \(candidateCardsHTML)
          </div>

          <div class="panel">
            <strong>Per-Horizon Delta</strong>
            <table>
              <thead>
                <tr><th>Horizon</th><th>RMSE (A→B)</th><th>BGRI (A→B)</th></tr>
              </thead>
              <tbody>
                \(tableRows)
              </tbody>
            </table>
          </div>

          <p class="footer">Generated \(runDateStr) · Baseline: \(escapeHTML(meta.baselineLabel)) · Candidate: \(escapeHTML(meta.candidateLabel))</p>
        </div>

        <script>
        Chart.defaults.color = '#888';
        Chart.defaults.borderColor = '#252a3a';

        const labels = [\(labelsJS)];
        const datasets = [
          {
            label: 'Baseline RMSE',
            data: [\(baselineRMSE)],
            borderColor: '#4ac8c8', backgroundColor: '#4ac8c822',
            borderWidth: 2.5, tension: 0.2, pointRadius: 4, fill: false,
            yAxisID: 'y'
          },
          {
            label: 'Baseline BGRI',
            data: [\(baselineBGRI)],
            borderColor: '#f4a460', backgroundColor: '#f4a46022',
            borderWidth: 2.5, tension: 0.2, pointRadius: 4, fill: false,
            yAxisID: 'y2'
          },
          {
            label: 'Candidate RMSE',
            data: [\(candidateRMSE)],
            borderColor: '#4ac8c8', backgroundColor: '#4ac8c822',
            borderWidth: 2.5, tension: 0.2, pointRadius: 4, fill: false,
            borderDash: [6, 3],
            yAxisID: 'y'
          },
          {
            label: 'Candidate BGRI',
            data: [\(candidateBGRI)],
            borderColor: '#f4a460', backgroundColor: '#f4a46022',
            borderWidth: 2.5, tension: 0.2, pointRadius: 4, fill: false,
            borderDash: [6, 3],
            yAxisID: 'y2'
          }
        ];

        new Chart(document.getElementById('compChart'), {
          type: 'line',
          data: { labels, datasets },
          options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
              x: { grid: { color: '#1e2230' } },
              y: {
                type: 'linear', position: 'left',
                title: { display: true, text: 'RMSE (mg/dL)', color: '#4ac8c8' },
                grid: { color: '#1e2230' }, min: 0
              },
              y2: {
                type: 'linear', position: 'right',
                title: { display: true, text: 'BGRI', color: '#f4a460' },
                grid: { drawOnChartArea: false }, min: 0
              }
            },
            plugins: {
              legend: {
                labels: {
                  color: '#aaa', boxWidth: 18, font: { size: 12 },
                  generateLabels: function(chart) {
                    return [
                      { text: 'Baseline RMSE', fillStyle: '#4ac8c8', strokeStyle: '#4ac8c8', lineWidth: 2, lineDash: [] },
                      { text: 'Baseline BGRI', fillStyle: '#f4a460', strokeStyle: '#f4a460', lineWidth: 2, lineDash: [] },
                      { text: 'Candidate RMSE', fillStyle: '#4ac8c8', strokeStyle: '#4ac8c8', lineWidth: 2, lineDash: [6,3] },
                      { text: 'Candidate BGRI', fillStyle: '#f4a460', strokeStyle: '#f4a460', lineWidth: 2, lineDash: [6,3] }
                    ];
                  }
                }
              },
              tooltip: {
                callbacks: {
                  label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(2)
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

    // MARK: – Helpers

    private static func escapeHTML(_ str: String) -> String {
        str.replacingOccurrences(of: "<", with: "&lt;")
           .replacingOccurrences(of: ">", with: "&gt;")
           .replacingOccurrences(of: "&", with: "&amp;")
    }

    private static func deltaCell(_ a: Double, _ b: Double, fmt: String) -> String {
        let delta = b - a
        let arrow = delta < 0 ? "▼" : (delta > 0 ? "▲" : "=")
        let mark = abs(delta) < 1e-9 ? "" : (delta < 0 ? " ✓" : " ✗")
        let aStr = String(format: fmt, a)
        let bStr = String(format: fmt, b)
        return "\(aStr) → \(bStr) \(arrow)\(mark)"
    }
}
