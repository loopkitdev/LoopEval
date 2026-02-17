// HTMLReportGenerator.swift — generates a self-contained HTML inspection report

import EvalCore
import Foundation

enum HTMLReportGenerator {

    static func generate(bundle: InspectionBundle) throws -> String {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let bundleJSON = String(data: try encoder.encode(bundle), encoding: .utf8) ?? "{}"

        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>LoopEval Inspection Report</title>
          <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
          <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
          <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                   background: #0f1117; color: #e0e0e0; padding: 20px; }
            h1 { font-size: 1.4em; font-weight: 600; color: #7eb8f7; margin-bottom: 4px; }
            .subtitle { font-size: 0.85em; color: #888; margin-bottom: 24px; }
            .panel { background: #1a1d27; border-radius: 10px; padding: 20px;
                     margin-bottom: 20px; border: 1px solid #2a2d3a; }
            .panel h2 { font-size: 1.05em; color: #b0c8f0; margin-bottom: 14px;
                        font-weight: 500; letter-spacing: 0.02em; }
            .chart-wrap { position: relative; height: 280px; }
            .chart-wrap-tall { position: relative; height: 360px; }
            .timeline-scroll { overflow-x: auto; overflow-y: hidden;
                                border-radius: 6px; }
            .timeline-scroll::-webkit-scrollbar { height: 6px; }
            .timeline-scroll::-webkit-scrollbar-track { background: #1a1d27; }
            .timeline-scroll::-webkit-scrollbar-thumb { background: #3a3d4a;
                border-radius: 3px; }
            .timeline-inner { position: relative; }
            .controls { display: flex; align-items: center; gap: 16px;
                        margin-bottom: 14px; flex-wrap: wrap; }
            .controls label { font-size: 0.82em; color: #999; }
            .controls select, .controls input[type=range] { background: #252836;
                border: 1px solid #3a3d4a; color: #ddd; border-radius: 5px;
                padding: 4px 8px; font-size: 0.82em; }
            .controls input[type=range] { width: 240px; accent-color: #7eb8f7; }
            .stat-bar { display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 14px; }
            .stat { background: #252836; border-radius: 6px; padding: 8px 14px;
                    border: 1px solid #2a2d3a; }
            .stat .label { font-size: 0.72em; color: #888; text-transform: uppercase;
                           letter-spacing: 0.05em; }
            .stat .value { font-size: 1.1em; font-weight: 600; color: #7eb8f7; }
            .legend-row { display: flex; gap: 18px; flex-wrap: wrap; margin-bottom: 10px; }
            .legend-item { display: flex; align-items: center; gap: 5px;
                           font-size: 0.78em; color: #aaa; }
            .legend-swatch { width: 18px; height: 3px; border-radius: 2px; }
            .legend-dot { width: 8px; height: 8px; border-radius: 50%; }
          </style>
        </head>
        <body>

        <h1>LoopEval Inspection Report</h1>
        <div class="subtitle" id="subtitle-text"></div>

        <!-- Panel 1: Input data timeline -->
        <div class="panel">
          <h2>Input Data — Glucose, Doses &amp; Carbs</h2>
          <div class="legend-row">
            <div class="legend-item"><div class="legend-dot" style="background:#5b9bd5"></div> Raw CGM</div>
            <div class="legend-item"><div class="legend-swatch" style="background:#7eb8f7"></div> Smoothed CGM</div>
            <div class="legend-item"><div class="legend-swatch" style="background:#9b7ed4"></div> Basal — temp (U/hr, right axis)</div>
            <div class="legend-item"><div class="legend-swatch" style="background:#9b7ed450;border:1px dashed #9b7ed4"></div> Basal — scheduled (U/hr, right axis)</div>
            <div class="legend-item"><div class="legend-dot" style="background:#f4a460;width:10px;height:10px;border-radius:0;clip-path:polygon(50% 0%,100% 100%,0% 100%)"></div> Bolus (U)</div>
            <div class="legend-item"><div class="legend-dot" style="background:#5cb85c"></div> Carbs (g)</div>
          </div>
          <div class="controls">
            <label>Zoom:</label>
            <input type="range" id="zoomSlider" min="0.25" max="4" step="0.25" value="1"
                   style="width:140px; accent-color:#7eb8f7;">
            <span id="zoomLabel" style="color:#7eb8f7;font-size:0.82em;min-width:160px;"></span>
            <span style="font-size:0.75em;color:#555;margin-left:4px;">Scroll or drag to pan · Ctrl+scroll to zoom</span>
          </div>
          <div class="timeline-scroll" id="timelineScroll">
            <div class="timeline-inner" id="timelineInner" style="height:370px;">
              <canvas id="timelineChart"></canvas>
            </div>
          </div>
        </div>

        <!-- Panel 2: Error profile by horizon -->
        <div class="panel">
          <h2>Forecast Error Profile by Horizon</h2>
          <div class="chart-wrap"><canvas id="errorChart"></canvas></div>
        </div>

        <!-- Panel 3: Prediction detail -->
        <div class="panel">
          <h2>Prediction Detail</h2>
          <div class="legend-row" style="margin-bottom:8px;">
            <div class="legend-item"><div class="legend-swatch" style="background:#f4a460;border-bottom:2px dashed #f4a460;"></div> Prediction (algo)</div>
            <div class="legend-item"><div class="legend-swatch" style="background:#50c8a8;border-bottom:2px dashed #50c8a8;"></div> Loop (NS stored)</div>
            <div class="legend-item"><div class="legend-swatch" style="background:#7eb8f7"></div> Smoothed CGM</div>
            <div class="legend-item"><div class="legend-dot" style="background:#5b9bd5"></div> Raw CGM</div>
          </div>
          <div class="controls">
            <label>Time: <span id="sliderLabel" style="color:#7eb8f7;font-weight:600"></span></label>
            <input type="range" id="predSlider" min="0" value="0">
            <label>Show horizon: </label>
            <select id="horizonSel"></select>
          </div>
          <div class="stat-bar" id="predStats"></div>
          <div class="chart-wrap-tall"><canvas id="predChart"></canvas></div>
        </div>

        <script>
        // ── Embedded data ─────────────────────────────────────────────────────────
        const BUNDLE = \(bundleJSON);

        // ── Helpers ───────────────────────────────────────────────────────────────
        const fmt = t => {
          const d = new Date(t);
          return d.toLocaleDateString('en-US',{month:'short',day:'numeric'}) + ' ' +
                 d.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',hour12:false});
        };

        // ── Subtitle ──────────────────────────────────────────────────────────────
        document.getElementById('subtitle-text').textContent =
          `${BUNDLE.startISO.slice(0,10)} → ${BUNDLE.endISO.slice(0,10)}  |  ` +
          `${BUNDLE.evalConfig.predictionCount} predictions  |  ` +
          `Kalman: ${BUNDLE.evalConfig.kalmanSmoothing ? 'on' : 'off'}`;

        // ── Chart defaults ────────────────────────────────────────────────────────
        Chart.defaults.color = '#888';
        Chart.defaults.borderColor = '#2a2d3a';

        const timeAxis = {
          type: 'time',
          time: { unit: 'hour', displayFormats: { hour: 'MMM d HH:mm' } },
          ticks: { maxTicksLimit: 10 },
          grid: { color: '#232638' }
        };

        // ── Panel 1: Timeline (scrollable) ────────────────────────────────────────
        const rawPts    = BUNDLE.rawGlucose.map(p => ({x: p.t, y: p.v}));
        const smoothPts = BUNDLE.smoothedGlucose.map(p => ({x: p.t, y: p.v}));

        const bolusPts = BUNDLE.doses
          .filter(d => d.isBolus)
          .map(d => ({x: d.t, y: 30 + d.units * 15, _units: d.units}));

        const carbPts = BUNDLE.carbs.map(c => ({x: c.t, y: 30 + c.g * 1.2, _g: c.g}));

        const basalSchedPts = [], basalTempPts = [];
        for (const seg of BUNDLE.basalTimeline) {
          const rate = seg.rate;
          const target = seg.isScheduled ? basalSchedPts : basalTempPts;
          const other  = seg.isScheduled ? basalTempPts  : basalSchedPts;
          other.push({x: seg.t, y: NaN});
          target.push({x: seg.t,    y: rate, _rate: rate});
          target.push({x: seg.tEnd, y: rate, _rate: rate});
        }

        const tlStartMs = new Date(BUNDLE.startISO).getTime();
        const tlEndMs   = new Date(BUNDLE.endISO).getTime();
        const totalDays = (tlEndMs - tlStartMs) / 86400000;
        const CHART_HEIGHT = 360;
        const DPR = window.devicePixelRatio || 1;

        // Base px per day: 1 day fills ~0.78 of the viewport at zoom=1
        const basePxPerDay = () => Math.round(window.innerWidth * 0.78);

        let tlChart = null;

        function buildTimelineChart(zoomFactor) {
          if (tlChart) { tlChart.destroy(); tlChart = null; }
          const pxPerDay  = basePxPerDay() * zoomFactor;
          const totalPx   = Math.max(Math.round(totalDays * pxPerDay), window.innerWidth - 40);
          const canvas    = document.getElementById('timelineChart');
          canvas.width    = totalPx * DPR;
          canvas.height   = CHART_HEIGHT * DPR;
          canvas.style.width  = totalPx + 'px';
          canvas.style.height = CHART_HEIGHT + 'px';
          document.getElementById('timelineInner').style.width = totalPx + 'px';

          // Tick granularity: choose unit based on px per day
          let timeUnit = 'hour', tickLimit = 12;
          if (pxPerDay < 120) { timeUnit = 'day'; tickLimit = 10; }
          else if (pxPerDay < 400) { timeUnit = 'hour'; tickLimit = Math.round(totalDays * 6); }
          else { timeUnit = 'hour'; tickLimit = Math.round(totalDays * 12); }

          tlChart = new Chart(canvas, {
            type: 'scatter',
            data: {
              datasets: [
                { label: 'Raw CGM', data: rawPts,
                  pointRadius: 2, pointBackgroundColor: '#5b9bd5',
                  showLine: false, yAxisID: 'yGlucose', order: 4 },
                { label: 'Smoothed CGM', data: smoothPts,
                  pointRadius: 0, showLine: true,
                  borderColor: '#7eb8f7', borderWidth: 2, tension: 0.3,
                  yAxisID: 'yGlucose', order: 3 },
                { label: 'Basal — temp (U/hr)', data: basalTempPts,
                  pointRadius: 0, showLine: true, stepped: 'before', spanGaps: false,
                  borderColor: '#9b7ed4', backgroundColor: 'rgba(155,126,212,0.18)',
                  borderWidth: 1.5, fill: 'origin', yAxisID: 'yBasal', order: 5 },
                { label: 'Basal — scheduled (U/hr)', data: basalSchedPts,
                  pointRadius: 0, showLine: true, stepped: 'before', spanGaps: false,
                  borderColor: '#9b7ed480', backgroundColor: 'rgba(155,126,212,0.06)',
                  borderWidth: 1, borderDash: [3,3], fill: 'origin',
                  yAxisID: 'yBasal', order: 6 },
                { label: 'Bolus (U)', data: bolusPts,
                  pointRadius: bolusPts.map(p => Math.max(4, p._units * 3)),
                  pointStyle: 'triangle', pointBackgroundColor: '#f4a460',
                  showLine: false, yAxisID: 'yGlucose', order: 1 },
                { label: 'Carbs (g)', data: carbPts,
                  pointRadius: carbPts.map(p => Math.max(4, p._g * 0.12)),
                  pointStyle: 'circle', pointBackgroundColor: '#5cb85c',
                  showLine: false, yAxisID: 'yGlucose', order: 1 }
              ]
            },
            options: {
              responsive: false, maintainAspectRatio: false, animation: false,
              scales: {
                x: {
                  type: 'time',
                  min: tlStartMs, max: tlEndMs,
                  time: { unit: timeUnit, displayFormats: {
                    hour: 'MMM d HH:mm', day: 'MMM d' } },
                  ticks: { maxTicksLimit: tickLimit, color: '#888' },
                  grid: { color: '#232638' }
                },
                yGlucose: {
                  type: 'linear', position: 'left',
                  title: { display: true, text: 'mg/dL', color: '#666' },
                  min: 20, max: 400, grid: { color: '#232638' }
                },
                yBasal: {
                  type: 'linear', position: 'right',
                  title: { display: true, text: 'U/hr', color: '#9b7ed4' },
                  min: 0, grid: { drawOnChartArea: false },
                  ticks: { color: '#9b7ed4' }
                }
              },
              plugins: {
                legend: { display: false },
                tooltip: {
                  callbacks: {
                    label: ctx => {
                      const d = ctx.raw;
                      if (d._units != null) return `Bolus: ${d._units.toFixed(2)} U`;
                      if (d._g    != null)  return `Carbs: ${d._g.toFixed(0)} g`;
                      if (d._rate != null)  return `Basal: ${d._rate.toFixed(3)} U/hr`;
                      return `${ctx.dataset.label}: ${d.y.toFixed(1)} mg/dL`;
                    },
                    title: ctx => fmt(ctx[0].raw.x)
                  }
                }
              }
            }
          });
        }

        // Zoom slider
        const zoomSlider = document.getElementById('zoomSlider');
        const zoomLabel  = document.getElementById('zoomLabel');
        function applyZoom(z) {
          const daysVisible = Math.max(0.1, totalDays / z).toFixed(1);
          zoomLabel.textContent = `${z.toFixed(2)}× — ~${daysVisible} days visible`;
          buildTimelineChart(z);
        }
        zoomSlider.addEventListener('input', () => applyZoom(parseFloat(zoomSlider.value)));

        // Ctrl+scroll to zoom, plain scroll to pan (browser default)
        document.getElementById('timelineScroll').addEventListener('wheel', e => {
          if (!e.ctrlKey && !e.metaKey) return;
          e.preventDefault();
          const delta = e.deltaY > 0 ? -0.25 : 0.25;
          const newZ = Math.min(4, Math.max(0.25, parseFloat(zoomSlider.value) + delta));
          zoomSlider.value = newZ;
          applyZoom(newZ);
        }, { passive: false });

        applyZoom(1.0);

        // ── Panel 2: Error profile ────────────────────────────────────────────────
        const hp = BUNDLE.horizonProfile;
        new Chart(document.getElementById('errorChart'), {
          type: 'line',
          data: {
            labels: hp.map(m => m.horizonMin + ' min'),
            datasets: [
              {
                label: 'RMSE',
                data: hp.map(m => m.rmse),
                borderColor: '#f4a460', backgroundColor: 'transparent',
                borderWidth: 2, tension: 0.2
              },
              {
                label: 'MAE',
                data: hp.map(m => m.mae),
                borderColor: '#7eb8f7', backgroundColor: 'transparent',
                borderWidth: 2, tension: 0.2, borderDash: [4,3]
              },
              {
                label: 'Bias',
                data: hp.map(m => m.bias),
                borderColor: '#e05c5c', backgroundColor: 'transparent',
                borderWidth: 2, tension: 0.2
              },
              {
                label: 'P10',
                data: hp.map(m => m.p10),
                borderColor: '#5cb85c', backgroundColor: 'rgba(92,184,92,0.07)',
                borderWidth: 1, tension: 0.2, fill: '+1'
              },
              {
                label: 'P90',
                data: hp.map(m => m.p90),
                borderColor: '#5cb85c', backgroundColor: 'rgba(92,184,92,0.07)',
                borderWidth: 1, tension: 0.2, fill: false
              }
            ]
          },
          options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            scales: {
              x: { grid: { color: '#232638' } },
              y: {
                title: { display: true, text: 'mg/dL', color: '#666' },
                grid: { color: '#232638' }
              }
            },
            plugins: { legend: { labels: { color: '#aaa', boxWidth: 18 } } }
          }
        });

        // ── Panel 3: Prediction detail ────────────────────────────────────────────
        const preds = BUNDLE.predictions;
        const horizons = BUNDLE.horizonProfile.map(m => m.horizonMin);
        const rawMap  = new Map(BUNDLE.rawGlucose.map(p => [Math.round(p.t), p.v]));
        const smoothMap = new Map(BUNDLE.smoothedGlucose.map(p => [Math.round(p.t), p.v]));

        // Nearest lookup helpers
        const lookup = (map, tMs) => {
          const keys = [...map.keys()];
          let best = null, bestDist = Infinity;
          for (const k of keys) {
            const d = Math.abs(k - tMs);
            if (d < bestDist) { bestDist = d; best = k; }
          }
          return bestDist < 6 * 60000 ? map.get(best) : null;  // within 6 min
        };

        // Populate horizon selector
        const sel = document.getElementById('horizonSel');
        horizons.forEach(h => {
          const o = document.createElement('option');
          o.value = h; o.text = h + ' min';
          sel.appendChild(o);
        });
        sel.value = horizons[Math.floor(horizons.length / 2)] ?? horizons[0];

        // Slider
        const slider = document.getElementById('predSlider');
        slider.max = preds.length - 1;
        slider.value = 0;

        let predChart = null;

        const updatePredPanel = () => {
          const idx = parseInt(slider.value);
          const pred = preds[idx];
          if (!pred) return;

          const tMs     = pred.t;
          const horizon = parseInt(sel.value) * 60000;  // horizon in ms
          const targetT = tMs + horizon;

          // Predicted value at selected horizon
          let predAtH = null;
          for (let i = 0; i < pred.curve.length - 1; i++) {
            const [t0, v0] = pred.curve[i];
            const [t1, v1] = pred.curve[i+1];
            if (t0 <= targetT && targetT <= t1) {
              predAtH = v0 + (v1 - v0) * (targetT - t0) / (t1 - t0);
              break;
            }
          }

          // Use smoothed for actual-at-horizon (matches error metric ground truth)
          const actualAtH = lookup(smoothMap, targetT) ?? lookup(rawMap, targetT);
          const error = (predAtH != null && actualAtH != null) ? predAtH - actualAtH : null;

          // Stats bar
          const stats = document.getElementById('predStats');
          stats.innerHTML = [
            {label: 'Time', value: fmt(tMs)},
            {label: 'Horizon', value: sel.value + ' min'},
            {label: 'Predicted', value: predAtH != null ? predAtH.toFixed(1) + ' mg/dL' : '—'},
            {label: 'Actual', value: actualAtH != null ? actualAtH.toFixed(1) + ' mg/dL' : '—'},
            {label: 'Error', value: error != null ? (error >= 0 ? '+' : '') + error.toFixed(1) + ' mg/dL' : '—'},
            {label: 'IOB', value: pred.iob != null ? pred.iob.toFixed(2) + ' U' : '—'},
            {label: 'COB', value: pred.cob != null ? pred.cob.toFixed(0) + ' g' : '—'},
          ].map(s => `<div class="stat"><div class="label">${s.label}</div><div class="value">${s.value}</div></div>`).join('');

          // Build chart data
          // Past: raw CGM only (algorithm input — no smoothing applied to past)
          const histStart = tMs - 3 * 3600000;
          const histActual = BUNDLE.rawGlucose
            .filter(p => p.t >= histStart && p.t <= tMs)
            .map(p => ({x: p.t, y: p.v}));

          // Future: both raw and Kalman-smoothed (smoother is the error comparison target)
          const futureEnd = tMs + 6 * 3600000;
          const futureActual = BUNDLE.rawGlucose
            .filter(p => p.t > tMs && p.t <= futureEnd)
            .map(p => ({x: p.t, y: p.v}));
          const futureSmoothed = BUNDLE.smoothedGlucose
            .filter(p => p.t > tMs && p.t <= futureEnd)
            .map(p => ({x: p.t, y: p.v}));

          // Prediction curve
          const predCurve = pred.curve.map(([t,v]) => ({x: t, y: v}));

          // Find closest Nightscout forecast to current snapshot time (within 10 min)
          const nsPreds = BUNDLE.nsPredictions || [];
          let closestNS = null;
          let bestDist = 10 * 60000;
          for (const ns of nsPreds) {
            const d = Math.abs(ns.t - tMs);
            if (d < bestDist) { bestDist = d; closestNS = ns; }
          }
          // Build NS curve: startMs + i*5min for each value
          const nsCurve = closestNS
            ? closestNS.values.map((v, i) => ({x: closestNS.startMs + i * 300000, y: v}))
            : [];

          // Horizon marker
          const horizonMarker = predAtH != null ? [{x: targetT, y: predAtH}] : [];
          const actualMarker  = actualAtH != null ? [{x: targetT, y: actualAtH}] : [];

          document.getElementById('sliderLabel').textContent = fmt(tMs);

          if (predChart) predChart.destroy();
          predChart = new Chart(document.getElementById('predChart'), {
            type: 'scatter',
            data: {
              datasets: [
                {
                  label: 'Raw CGM (past)',
                  data: histActual,
                  pointRadius: 2.5, pointBackgroundColor: '#5b9bd5',
                  showLine: false, order: 5
                },
                {
                  label: 'Raw CGM (future)',
                  data: futureActual,
                  pointRadius: 2.5, pointBackgroundColor: '#5b9bd570',
                  showLine: false, order: 4
                },
                {
                  label: 'Kalman actual (future)',
                  data: futureSmoothed,
                  pointRadius: 0, showLine: true,
                  borderColor: '#7eb8f7', borderWidth: 2, tension: 0.3, order: 3
                },
                {
                  label: 'Prediction',
                  data: predCurve,
                  pointRadius: 0, showLine: true,
                  borderColor: '#f4a460', borderWidth: 2,
                  borderDash: [5,3], tension: 0.2, order: 2
                },
                {
                  label: 'Loop (Nightscout)',
                  data: nsCurve,
                  pointRadius: 0, showLine: true,
                  borderColor: '#50c8a8', borderWidth: 2,
                  borderDash: [3,3], tension: 0.2, order: 3
                },
                {
                  label: 'Predicted at horizon',
                  data: horizonMarker,
                  pointRadius: 8, pointStyle: 'rectRot',
                  pointBackgroundColor: '#f4a460', showLine: false, order: 1
                },
                {
                  label: 'Actual at horizon',
                  data: actualMarker,
                  pointRadius: 8, pointStyle: 'rectRot',
                  pointBackgroundColor: '#7eb8f7', showLine: false, order: 1
                }
              ]
            },
            options: {
              responsive: true, maintainAspectRatio: false, animation: false,
              scales: {
                x: { ...timeAxis },
                y: {
                  title: { display: true, text: 'mg/dL', color: '#666' },
                  min: 40, max: 350,
                  grid: { color: '#232638' }
                }
              },
              plugins: {
                legend: { labels: { color: '#aaa', boxWidth: 12 } },
                tooltip: {
                  callbacks: {
                    title: ctx => fmt(ctx[0].raw.x),
                    label: ctx => `${ctx.dataset.label}: ${ctx.raw.y.toFixed(1)} mg/dL`
                  }
                }
              }
            }
          });
        };

        slider.addEventListener('input', updatePredPanel);
        sel.addEventListener('change', updatePredPanel);
        updatePredPanel();
        </script>
        </body>
        </html>
        """
    }
}
