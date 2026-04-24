// ISFRollingHTMLGenerator.swift — HTML plot for rolling ISF time series
//
// Single self-contained page with Chart.js via CDN. Shows:
//   1. ISF time series with optional bootstrap CI band
//   2. Sample-count per window (sanity check)
//   3. Summary stats in a header table

import EvalCore
import Foundation

enum ISFRollingHTMLGenerator {

    static func generate(
        points: [RollingISFPoint],
        pointsLog: [RollingISFPoint] = [],
        dailyPoints: [RollingISFPoint] = [],
        dailyPointsLog: [RollingISFPoint] = [],
        tddPoints: [DailyTDDPoint] = [],
        interval: DateInterval,
        config: ISFRollingConfig,
        logReferenceBG: Double = 150
    ) -> String {
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime]

        let valid = points.filter { !$0.isfEstimate.isNaN }
        let sortedISF = valid.map { $0.isfEstimate }.sorted()
        let stats = Self.summarize(sortedISF)

        // Lomb-Scargle periodogram on the rolling ISF time series. Uses the
        // valid points only; handles the irregular sampling that NaN gaps
        // create without needing interpolation.
        let periodogram = LombScargle.compute(
            times:  valid.map { $0.centerTime },
            values: valid.map { $0.isfEstimate },
            minPeriodDays: 3
        )
        let periodogramJS = periodogram.points.map { pt in
            "{x:\(String(format: "%.3f", pt.periodDays)),y:\(String(format: "%.4f", pt.power)),fap:\(String(format: "%.4f", pt.fap))}"
        }.joined(separator: ",\n")
        let peaksHTML = Self.peaksTableHTML(peaks: periodogram.peaks)

        let seriesJS = points.map { p -> String in
            let t = iso.string(from: p.centerTime)
            let isf  = p.isfEstimate.isNaN ? "null" : String(format: "%.3f", p.isfEstimate)
            let low  = p.isfCILow.isNaN    ? "null" : String(format: "%.3f", p.isfCILow)
            let high = p.isfCIHigh.isNaN   ? "null" : String(format: "%.3f", p.isfCIHigh)
            return "{x:'\(t)',y:\(isf),ci_low:\(low),ci_high:\(high),n:\(p.n)}"
        }.joined(separator: ",\n")

        let dailyJS = dailyPoints.map { p -> String in
            let t = iso.string(from: p.centerTime)
            let isf = p.isfEstimate.isNaN ? "null" : String(format: "%.3f", p.isfEstimate)
            return "{x:'\(t)',y:\(isf),n:\(p.n)}"
        }.joined(separator: ",\n")

        let rollingLogJS = pointsLog.map { p -> String in
            let t = iso.string(from: p.centerTime)
            let isf = p.isfEstimate.isNaN ? "null" : String(format: "%.3f", p.isfEstimate)
            return "{x:'\(t)',y:\(isf),n:\(p.n)}"
        }.joined(separator: ",\n")

        let dailyLogJS = dailyPointsLog.map { p -> String in
            let t = iso.string(from: p.centerTime)
            let isf = p.isfEstimate.isNaN ? "null" : String(format: "%.3f", p.isfEstimate)
            return "{x:'\(t)',y:\(isf),n:\(p.n)}"
        }.joined(separator: ",\n")

        let tddJS = tddPoints.map { p -> String in
            // centre the point at local noon of the day for a nicer plot
            let noon = p.dayStart.addingTimeInterval(12 * 3600)
            return "{x:'\(iso.string(from: noon))',y:\(String(format: "%.2f", p.tdd))}"
        }.joined(separator: ",\n")

        let hasCIs = points.contains { !$0.isfCILow.isNaN }
        let dateFmt = DateFormatter()
        dateFmt.dateFormat = "yyyy-MM-dd"
        let startStr = dateFmt.string(from: interval.start)
        let endStr   = dateFmt.string(from: interval.end)
        let xMinISO  = iso.string(from: interval.start)
        let xMaxISO  = iso.string(from: interval.end)

        let dailyPanel = dailyPoints.isEmpty ? "" : """
        <h2>Daily ISF (1-day window, no rolling)</h2>
        <div class="panel">
          <div class="chart-medium"><canvas id="dailyChart"></canvas></div>
          <div class="caption">Per-calendar-day quantile-ISF. ~250 samples per fit → much noisier than the 7-day rolling view. Large day-to-day swings here indicate that the rolling line is smoothing real variability, not suppressing noise. Dashed orange line is 1800/TDD for the same day.</div>
        </div>
        """

        let tddPanel = tddPoints.isEmpty ? "" : """
        <h2>Daily TDD (total insulin delivered)</h2>
        <div class="panel">
          <div class="chart-short"><canvas id="tddChart"></canvas></div>
          <div class="caption">Sum of bolus + temp-basal delivery per local calendar day (U). 1800-rule implied ISF = 1800 / TDD — overlaid on the daily ISF plot above for visual comparison.</div>
        </div>
        """

        return #"""
        <!doctype html>
        <html lang="en">
        <head>
        <meta charset="utf-8">
        <title>Rolling ISF — \#(startStr) → \#(endStr)</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
        <style>
          :root { color-scheme: dark; }
          body { font-family: -apple-system, system-ui, sans-serif; background:#181818; color:#ddd; margin:0; padding:24px 32px; max-width:1100px; margin-inline:auto; line-height:1.55; }
          .topbar { font-size:12px; color:#888; margin-bottom:24px; padding-bottom:12px; border-bottom:1px solid #2a2a2a; display:flex; justify-content:space-between; }
          .topbar a { color:#6ab; text-decoration:none; }
          h1 { color:#fff; font-size:24px; margin:0 0 4px; padding-bottom:8px; border-bottom:1px solid #333; }
          .sub { color:#888; font-size:13px; margin-bottom:18px; }
          h2 { color:#fff; font-size:16px; margin:28px 0 8px; padding-bottom:4px; border-bottom:1px solid #2a2a2a; text-transform:uppercase; letter-spacing:0.5px; }
          .panel { background:#1d1d1d; border-radius:6px; padding:14px; margin:14px 0; }
          .panel canvas { background:#111; border-radius:4px; }
          .chart-tall   { position: relative; height: 320px; }
          .chart-medium { position: relative; height: 260px; }
          .chart-short  { position: relative; height: 180px; }
          .stats { display:grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap:10px; margin:10px 0 20px; }
          .stat { background:#1d1d1d; border-radius:6px; padding:10px 14px; }
          .stat .label { font-size:11px; color:#888; text-transform:uppercase; letter-spacing:0.5px; }
          .stat .value { font-size:20px; color:#fff; font-family: ui-monospace, monospace; margin-top:3px; }
          .stat .unit { font-size:11px; color:#888; margin-left:3px; }
          .caption { font-size:12px; color:#888; margin-top:6px; }
          code { background:#222; padding:1px 5px; border-radius:3px; font-size:90%; font-family: ui-monospace, monospace; color:#e9c; }
          table.peaks { border-collapse: collapse; margin: 12px 0 0; font-size:12px; width:100%; }
          table.peaks th, table.peaks td { border: 1px solid #333; padding: 5px 8px; text-align: left; }
          table.peaks th { background: #222; color: #fff; }
          table.peaks td.num { font-family: ui-monospace, monospace; text-align: right; }
          table.peaks tr:nth-child(even) td { background: #1d1d1d; }
        </style>
        </head>
        <body>
        <div class="topbar">
          <a href="/">← Index</a>
          <span>window=\#(Int(config.windowDays))d, step=\#(Int(config.stepDays))d, τ=\#(String(format: "%.2f", config.quantile)), bootstrap=\#(config.bootstrapN)</span>
        </div>

        <h1>Rolling ISF — \#(startStr) → \#(endStr)</h1>
        <div class="sub">Quantile regression at τ=\#(String(format: "%.2f", config.quantile)) on rolling \#(Int(config.windowDays))-day windows, \#(Int(config.stepDays))-day step. Each point is an ISF estimate from the surrounding window.</div>

        <div class="stats">
          \#(Self.statCard("Median ISF", stats.median, "mg/dL/U"))
          \#(Self.statCard("Mean ISF", stats.mean, "mg/dL/U"))
          \#(Self.statCard("P10", stats.p10, "mg/dL/U"))
          \#(Self.statCard("P90", stats.p90, "mg/dL/U"))
          \#(Self.statCard("Min", stats.min, "mg/dL/U"))
          \#(Self.statCard("Max", stats.max, "mg/dL/U"))
          \#(Self.statCardInt("Fits", valid.count))
          \#(Self.statCardInt("Total windows", points.count))
        </div>

        <h2>ISF over time — \#(Int(config.windowDays))-day rolling</h2>
        <div class="panel">
          <div class="chart-tall"><canvas id="isfChart"></canvas></div>
          <div class="caption">Each dot is one \#(Int(config.windowDays))-day window's quantile-ISF estimate\#(hasCIs ? ". Shaded band = bootstrap 95% CI." : ". Bootstrap CIs not computed (pass <code>--bootstrap 200</code> to enable).")</div>
        </div>

        \#(dailyPanel)

        \#(tddPanel)

        <h2>Sample count per window</h2>
        <div class="panel">
          <div class="chart-short"><canvas id="nChart"></canvas></div>
          <div class="caption">Number of ISFSamples contributing to each fit. Drops indicate sensor gaps, low insulin activity, or short windows at the ends.</div>
        </div>

        <h2>Lomb-Scargle periodogram</h2>
        <div class="panel">
          <div class="chart-medium"><canvas id="periodChart"></canvas></div>
          <div class="caption">
            Periodogram power vs period (days). Peaks reveal cyclic signals in the ISF time series —
            weekly patterns (~7d), menstrual cycle (~28d), seasonal drift. Horizontal guides at FAP=5%
            and FAP=1% mark conventional significance thresholds (peaks above FAP=1% are unlikely to be noise).
          </div>
          \#(peaksHTML)
        </div>

        <script>
        const X_MIN = '\#(xMinISO)';
        const X_MAX = '\#(xMaxISO)';
        const LOG_REF_BG = \#(logReferenceBG);
        const POINTS       = [\#(seriesJS)];
        const POINTS_LOG   = [\#(rollingLogJS)];
        const DAILY        = [\#(dailyJS)];
        const DAILY_LOG    = [\#(dailyLogJS)];
        const TDD          = [\#(tddJS)];

        const isfData = POINTS.map(p => ({x: p.x, y: p.y}));
        const ciLoData = POINTS.map(p => ({x: p.x, y: p.ci_low}));
        const ciHiData = POINTS.map(p => ({x: p.x, y: p.ci_high}));
        const nData   = POINTS.map(p => ({x: p.x, y: p.n}));

        const hasCIs = \#(hasCIs ? "true" : "false");

        new Chart(document.getElementById('isfChart').getContext('2d'), {
          type: 'line',
          data: {
            datasets: [
              ...(hasCIs ? [{
                label: 'CI high',
                data: ciHiData,
                borderColor: 'rgba(108,207,255,0.0)',
                backgroundColor: 'rgba(108,207,255,0.15)',
                fill: '+1',
                pointRadius: 0,
                tension: 0,
              },{
                label: 'CI low',
                data: ciLoData,
                borderColor: 'rgba(108,207,255,0.0)',
                backgroundColor: 'rgba(108,207,255,0.15)',
                fill: false,
                pointRadius: 0,
                tension: 0,
              }] : []),
              {
                label: 'ISF τ=\#(String(format: "%.2f", config.quantile)) (linear)',
                data: isfData,
                borderColor: '#6cf',
                backgroundColor: '#6cf',
                pointRadius: 2.2,
                pointHoverRadius: 4,
                borderWidth: 1.8,
                tension: 0.05,
                fill: false,
              },
              ...(POINTS_LOG.length > 0 ? [{
                label: `ISF log @ BG=${LOG_REF_BG}`,
                data: POINTS_LOG.map(p => ({x: p.x, y: p.y})),
                borderColor: '#fc9',
                backgroundColor: '#fc9',
                pointRadius: 2.0,
                pointHoverRadius: 4,
                borderWidth: 1.6,
                borderDash: [4, 3],
                tension: 0.05,
                fill: false,
              }] : []),
            ],
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            animation: false,
            plugins: {
              legend: { position: 'top', labels: { color: '#ccc', font: { size: 11 } } },
              tooltip: {
                callbacks: {
                  label: (ctx) => {
                    const p = POINTS[ctx.dataIndex];
                    if (ctx.dataset.label.startsWith('CI')) return null;
                    let s = `ISF = ${p.y === null ? '—' : p.y.toFixed(1)} mg/dL/U`;
                    if (p.ci_low !== null && p.ci_high !== null) {
                      s += ` [${p.ci_low.toFixed(1)}, ${p.ci_high.toFixed(1)}]`;
                    }
                    s += `  (n=${p.n})`;
                    return s;
                  },
                },
              },
            },
            scales: {
              x: {
                type: 'time',
                time: { unit: 'month' },
                min: X_MIN, max: X_MAX,
                ticks: { color: '#999' },
                grid:  { color: '#2a2a2a' },
              },
              y: {
                title: { display: true, text: 'ISF (mg/dL/U)', color: '#aaa' },
                ticks: { color: '#999' }, grid: { color: '#2a2a2a' },
              },
            },
          },
        });

        const PERIODOGRAM = [\#(periodogramJS)];
        // FAP thresholds back out power: FAP = 1 - (1 - exp(-P))^M, so
        // P* = -ln(1 - (1 - FAP)^(1/M)). We compute in JS for display.
        const N_EFF = \#(periodogram.nEffectiveFrequencies);
        function powerForFAP(fap) {
          if (N_EFF <= 0) return null;
          return -Math.log(1 - Math.pow(1 - fap, 1 / N_EFF));
        }
        const p05 = powerForFAP(0.05);
        const p01 = powerForFAP(0.01);

        new Chart(document.getElementById('periodChart').getContext('2d'), {
          type: 'line',
          data: {
            datasets: [
              {
                label: 'Power',
                data: PERIODOGRAM,
                borderColor: '#f96',
                backgroundColor: 'rgba(255,150,100,0.15)',
                pointRadius: 0,
                borderWidth: 1.6,
                fill: true,
                tension: 0,
              },
              ...(p05 !== null ? [{
                label: 'FAP = 5%',
                data: PERIODOGRAM.map(p => ({x: p.x, y: p05})),
                borderColor: 'rgba(200,200,100,0.7)',
                backgroundColor: 'rgba(0,0,0,0)',
                pointRadius: 0, borderWidth: 1, borderDash: [6, 4], fill: false,
              }] : []),
              ...(p01 !== null ? [{
                label: 'FAP = 1%',
                data: PERIODOGRAM.map(p => ({x: p.x, y: p01})),
                borderColor: 'rgba(240,100,100,0.7)',
                backgroundColor: 'rgba(0,0,0,0)',
                pointRadius: 0, borderWidth: 1, borderDash: [4, 3], fill: false,
              }] : []),
            ],
          },
          options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            plugins: {
              legend: { position: 'top', labels: { color: '#ccc', font: { size: 11 } } },
              tooltip: {
                callbacks: {
                  label: (ctx) => {
                    if (ctx.datasetIndex !== 0) return null;
                    const d = ctx.raw;
                    return `period ${d.x.toFixed(1)}d · power ${d.y.toFixed(3)} · FAP ${(d.fap * 100).toFixed(2)}%`;
                  },
                },
              },
            },
            scales: {
              x: {
                type: 'logarithmic',
                title: { display: true, text: 'period (days, log scale)', color: '#aaa' },
                ticks: { color: '#999', callback: (v) => Number(v).toFixed(0) },
                grid:  { color: '#2a2a2a' },
              },
              y: {
                title: { display: true, text: 'normalized power', color: '#aaa' },
                ticks: { color: '#999' }, grid: { color: '#2a2a2a' },
                beginAtZero: true,
              },
            },
          },
        });

        // Daily ISF chart + 1800/TDD overlay (if both available)
        if (DAILY.length > 0) {
          // Build 1800/TDD data keyed to the same x (day) axis
          const tddByDay = {};
          for (const t of TDD) {
            const d = t.x.substring(0, 10);  // YYYY-MM-DD
            tddByDay[d] = t.y;
          }
          const rule1800 = DAILY.map(p => {
            const d = p.x.substring(0, 10);
            const tdd = tddByDay[d];
            return { x: p.x, y: (tdd && tdd > 0) ? (1800 / tdd) : null };
          });

          new Chart(document.getElementById('dailyChart').getContext('2d'), {
            type: 'line',
            data: {
              datasets: [
                {
                  label: '1800 / TDD',
                  data: rule1800,
                  borderColor: '#d96',
                  backgroundColor: '#d96',
                  pointRadius: 0,
                  borderWidth: 1.2,
                  borderDash: [4, 3],
                  tension: 0,
                  fill: false,
                },
                {
                  label: 'Daily ISF τ=\#(String(format: "%.2f", config.quantile)) (linear)',
                  data: DAILY,
                  borderColor: '#9cf',
                  backgroundColor: '#9cf',
                  pointRadius: 2,
                  pointHoverRadius: 4,
                  borderWidth: 1.4,
                  showLine: true,
                  spanGaps: false,
                  tension: 0,
                  fill: false,
                },
                ...(DAILY_LOG.length > 0 ? [{
                  label: `Daily ISF log @ BG=${LOG_REF_BG}`,
                  data: DAILY_LOG,
                  borderColor: '#fc9',
                  backgroundColor: '#fc9',
                  pointRadius: 1.8,
                  pointHoverRadius: 4,
                  borderWidth: 1.2,
                  borderDash: [3, 2],
                  showLine: true,
                  spanGaps: false,
                  tension: 0,
                  fill: false,
                }] : []),
              ],
            },
            options: {
              responsive: true, maintainAspectRatio: false, animation: false,
              plugins: {
                legend: { position: 'top', labels: { color: '#ccc', font: { size: 11 } } },
                tooltip: {
                  callbacks: {
                    label: (ctx) => {
                      const label = ctx.dataset.label;
                      const y = ctx.parsed.y;
                      if (y === null || y === undefined) return null;
                      return `${label}: ${y.toFixed(1)} mg/dL/U`;
                    },
                  },
                },
              },
              scales: {
                x: {
                  type: 'time',
                  time: { unit: 'month' },
                  min: X_MIN, max: X_MAX,
                  ticks: { color: '#999' }, grid: { color: '#2a2a2a' },
                },
                y: {
                  title: { display: true, text: 'ISF (mg/dL/U)', color: '#aaa' },
                  ticks: { color: '#999' }, grid: { color: '#2a2a2a' },
                },
              },
            },
          });
        }

        // TDD chart
        if (TDD.length > 0) {
          new Chart(document.getElementById('tddChart').getContext('2d'), {
            type: 'bar',
            data: { datasets: [{
              label: 'TDD (U/day)',
              data: TDD,
              backgroundColor: '#fc6',
              borderColor: '#fc6',
              borderWidth: 0,
              barPercentage: 1.0,
              categoryPercentage: 1.0,
            }] },
            options: {
              responsive: true, maintainAspectRatio: false, animation: false,
              plugins: { legend: { display: false } },
              scales: {
                x: {
                  type: 'time',
                  time: { unit: 'month' },
                  min: X_MIN, max: X_MAX,
                  ticks: { color: '#999' }, grid: { color: '#2a2a2a' },
                },
                y: {
                  title: { display: true, text: 'U/day', color: '#aaa' },
                  ticks: { color: '#999' }, grid: { color: '#2a2a2a' },
                  beginAtZero: true,
                },
              },
            },
          });
        }

        new Chart(document.getElementById('nChart').getContext('2d'), {
          type: 'bar',
          data: { datasets: [{
            label: 'n samples',
            data: nData,
            backgroundColor: '#9c6',
            borderColor: '#9c6',
            borderWidth: 0,
            barPercentage: 1.0,
            categoryPercentage: 1.0,
          }] },
          options: {
            responsive: true, maintainAspectRatio: false,
            animation: false,
            plugins: { legend: { display: false } },
            scales: {
              x: {
                type: 'time',
                time: { unit: 'month' },
                min: X_MIN, max: X_MAX,
                ticks: { color: '#999' },
                grid:  { color: '#2a2a2a' },
              },
              y: {
                title: { display: true, text: 'samples', color: '#aaa' },
                ticks: { color: '#999' }, grid: { color: '#2a2a2a' },
                beginAtZero: true,
              },
            },
          },
        });
        </script>
        </body>
        </html>
        """#
    }

    // MARK: - Helpers

    private struct ISFSummary {
        var median: Double, mean: Double
        var p10: Double, p90: Double
        var min: Double, max: Double
    }

    private static func summarize(_ sorted: [Double]) -> ISFSummary {
        guard !sorted.isEmpty else {
            return ISFSummary(median: .nan, mean: .nan, p10: .nan, p90: .nan, min: .nan, max: .nan)
        }
        let n = sorted.count
        let mean = sorted.reduce(0, +) / Double(n)
        return ISFSummary(
            median: sorted[n/2], mean: mean,
            p10: sorted[Int(0.10 * Double(n - 1))],
            p90: sorted[Int(0.90 * Double(n - 1))],
            min: sorted.first!, max: sorted.last!
        )
    }

    private static func statCard(_ label: String, _ value: Double, _ unit: String) -> String {
        let v = value.isNaN ? "—" : String(format: "%.1f", value)
        return """
        <div class="stat"><div class="label">\(label)</div><div class="value">\(v)<span class="unit">\(unit)</span></div></div>
        """
    }

    private static func statCardInt(_ label: String, _ value: Int) -> String {
        """
        <div class="stat"><div class="label">\(label)</div><div class="value">\(value)</div></div>
        """
    }

    private static func peaksTableHTML(peaks: [LombScarglePoint]) -> String {
        guard !peaks.isEmpty else {
            return "<div class=\"caption\">(no peaks detected — time series may be too short or noisy)</div>"
        }
        var rows = ""
        for (i, p) in peaks.enumerated() {
            let fapPct = p.fap * 100
            let fapStr: String
            if fapPct < 0.01 {
                fapStr = String(format: "%.2e%%", fapPct)
            } else {
                fapStr = String(format: "%.3f%%", fapPct)
            }
            let sig = p.fap < 0.01 ? "high" : (p.fap < 0.05 ? "medium" : "low")
            rows += """
            <tr><td>\(i + 1)</td><td class="num">\(String(format: "%.1f", p.periodDays))</td><td class="num">\(String(format: "%.3f", p.power))</td><td class="num">\(fapStr)</td><td>\(sig)</td></tr>
            """
        }
        return """
        <table class="peaks">
          <thead><tr><th>#</th><th>Period (days)</th><th>Power</th><th>FAP</th><th>Significance</th></tr></thead>
          <tbody>\(rows)</tbody>
        </table>
        """
    }
}
