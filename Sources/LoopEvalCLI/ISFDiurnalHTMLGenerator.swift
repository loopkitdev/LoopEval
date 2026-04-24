// ISFDiurnalHTMLGenerator.swift — HTML plot for hourly-quantile ISF

import EvalCore
import Foundation

enum ISFDiurnalHTMLGenerator {

    static func generate(
        all: DiurnalResult,
        weekday: DiurnalResult?,
        weekend: DiurnalResult?,
        interval: DateInterval
    ) -> String {
        let dateFmt = DateFormatter()
        dateFmt.dateFormat = "yyyy-MM-dd"
        let startStr = dateFmt.string(from: interval.start)
        let endStr   = dateFmt.string(from: interval.end)

        let allJS = Self.datasetJS(all)
        let wdJS  = weekday.map { Self.datasetJS($0) } ?? "[]"
        let weJS  = weekend.map { Self.datasetJS($0) } ?? "[]"

        let hasSplit = (weekday != nil && weekend != nil)

        return #"""
        <!doctype html>
        <html lang="en">
        <head>
        <meta charset="utf-8">
        <title>Diurnal ISF — \#(startStr) → \#(endStr)</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
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
          .chart-tall  { position: relative; height: 320px; }
          .chart-short { position: relative; height: 180px; }
          .caption { font-size:12px; color:#888; margin-top:6px; }
          code { background:#222; padding:1px 5px; border-radius:3px; font-size:90%; font-family: ui-monospace, monospace; color:#e9c; }
          .warn { background:#2a1f14; border-left:3px solid #f96; padding:10px 14px; border-radius:0 6px 6px 0; margin:14px 0; font-size:13px; color:#ddd; }
        </style>
        </head>
        <body>
        <div class="topbar">
          <a href="/">← Index</a>
          <span>hourly · τ=\#(String(format: "%.2f", all.quantile)) · bootstrap=\#(all.bootstrapN)</span>
        </div>

        <h1>Diurnal ISF — \#(startStr) → \#(endStr)</h1>
        <div class="sub">Quantile regression at τ=\#(String(format: "%.2f", all.quantile)) per local hour-of-day\#(all.bootstrapN > 0 ? ", with bootstrap 95% CIs" : "").\#(hasSplit ? " Split by weekday vs weekend." : "")</div>

        <div class="warn">
          <strong>Important caveat:</strong> diurnal swings in fitted ISF are <em>confounded with diurnal basal-schedule miscoverage</em>. A basal rate that over-covers EGP in the afternoon pulls the fitted ISF downward; under-coverage at dawn pushes it upward. These results describe <em>effective</em> ISF (what the regression reads off the data), not the <em>true metabolic</em> ISF. Treat hourly values as descriptive, not load-bearing.
        </div>

        <h2>ISF by hour of day</h2>
        <div class="panel">
          <div class="chart-tall"><canvas id="diurnalChart"></canvas></div>
          <div class="caption">Points = τ=\#(String(format: "%.2f", all.quantile)) quantile ISF for each hour. \#(all.bootstrapN > 0 ? "Shaded bands = bootstrap 95% CI." : "Bootstrap CIs not computed (pass <code>--bootstrap 200</code> to enable).")</div>
        </div>

        <h2>Sample count per hour</h2>
        <div class="panel">
          <div class="chart-short"><canvas id="nChart"></canvas></div>
        </div>

        <script>
        const ALL = \#(allJS);
        const WD  = \#(wdJS);
        const WE  = \#(weJS);
        const HAS_SPLIT = \#(hasSplit ? "true" : "false");

        function makeCIBand(points, color) {
          const hi = points.map(p => ({x: p.hour, y: p.ci_high}));
          const lo = points.map(p => ({x: p.hour, y: p.ci_low}));
          return [{
            label: '_ci_hi',
            data: hi, borderColor: color + '00',
            backgroundColor: color + '26',
            fill: '+1', pointRadius: 0, tension: 0.2,
          },{
            label: '_ci_lo',
            data: lo, borderColor: color + '00',
            backgroundColor: color + '26',
            fill: false, pointRadius: 0, tension: 0.2,
          }];
        }

        function makeLine(points, label, color) {
          return {
            label,
            data: points.map(p => ({x: p.hour, y: p.isf})),
            borderColor: color, backgroundColor: color,
            pointRadius: 3, pointHoverRadius: 5,
            borderWidth: 2, tension: 0.2, fill: false,
          };
        }

        const hasCIs = ALL.some(p => p.ci_low !== null && !isNaN(p.ci_low));

        const datasets = [];
        if (!HAS_SPLIT) {
          if (hasCIs) datasets.push(...makeCIBand(ALL, '#6cf'));
          datasets.push(makeLine(ALL, 'ISF (all days)', '#6cf'));
        } else {
          if (hasCIs) {
            datasets.push(...makeCIBand(WD, '#6cf'));
            datasets.push(...makeCIBand(WE, '#f96'));
          }
          datasets.push(makeLine(WD, 'weekday', '#6cf'));
          datasets.push(makeLine(WE, 'weekend', '#f96'));
          datasets.push(makeLine(ALL, 'all', '#ccc'));
        }

        new Chart(document.getElementById('diurnalChart').getContext('2d'), {
          type: 'line', data: { datasets },
          options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            plugins: {
              legend: {
                position: 'top', labels: {
                  color: '#ccc', font: { size: 11 },
                  filter: (item) => !item.text.startsWith('_ci'),
                },
              },
              tooltip: {
                callbacks: {
                  label: (ctx) => {
                    if (ctx.dataset.label.startsWith('_ci')) return null;
                    const h = ctx.parsed.x;
                    const isf = ctx.parsed.y;
                    return `${ctx.dataset.label}: h=${h}:00, ISF=${isf === null ? '—' : isf.toFixed(1)} mg/dL/U`;
                  },
                },
              },
            },
            scales: {
              x: {
                type: 'linear', min: 0, max: 23,
                title: { display: true, text: 'hour of day (local)', color: '#aaa' },
                ticks: { color: '#999', stepSize: 2 }, grid: { color: '#2a2a2a' },
              },
              y: {
                title: { display: true, text: 'ISF (mg/dL/U)', color: '#aaa' },
                ticks: { color: '#999' }, grid: { color: '#2a2a2a' },
              },
            },
          },
        });

        new Chart(document.getElementById('nChart').getContext('2d'), {
          type: 'bar',
          data: {
            datasets: HAS_SPLIT ? [{
              label: 'weekday',
              data: WD.map(p => ({x: p.hour, y: p.n})),
              backgroundColor: '#6cf',
              barPercentage: 0.45, categoryPercentage: 1.0,
            },{
              label: 'weekend',
              data: WE.map(p => ({x: p.hour, y: p.n})),
              backgroundColor: '#f96',
              barPercentage: 0.45, categoryPercentage: 1.0,
            }] : [{
              label: 'all',
              data: ALL.map(p => ({x: p.hour, y: p.n})),
              backgroundColor: '#9c6',
              barPercentage: 0.85, categoryPercentage: 1.0,
            }],
          },
          options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            plugins: { legend: { position: 'top', labels: { color: '#ccc', font: { size: 11 } } } },
            scales: {
              x: {
                type: 'linear', min: -0.5, max: 23.5,
                title: { display: true, text: 'hour of day', color: '#aaa' },
                ticks: { color: '#999', stepSize: 2 }, grid: { color: '#2a2a2a' },
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

    private static func datasetJS(_ r: DiurnalResult) -> String {
        let items = r.points.map { p -> String in
            let isf   = p.isfEstimate.isNaN ? "null" : String(format: "%.3f", p.isfEstimate)
            let low   = p.isfCILow.isNaN    ? "null" : String(format: "%.3f", p.isfCILow)
            let high  = p.isfCIHigh.isNaN   ? "null" : String(format: "%.3f", p.isfCIHigh)
            return "{hour:\(p.hour),n:\(p.n),isf:\(isf),ci_low:\(low),ci_high:\(high)}"
        }
        return "[" + items.joined(separator: ",") + "]"
    }
}
