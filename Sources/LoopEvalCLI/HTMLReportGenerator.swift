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
            .wo-table { width: 100%; border-collapse: collapse; font-size: 0.82em;
                        background: #0a0d18; border-radius: 6px; overflow: hidden; }
            .wo-table th { text-align: left; padding: 8px 10px; color: #888;
                           font-weight: 500; border-bottom: 1px solid #2a2d3a;
                           font-size: 0.9em; }
            .wo-table td { padding: 7px 10px; font-family: ui-monospace, 'SF Mono',
                           Menlo, Monaco, monospace; color: #ddd; }
            .wo-table tr { cursor: pointer; transition: background 0.15s; }
            .wo-table tbody tr:hover { background: #1a1d27; }
            .wo-odr tbody tr { border-left: 3px solid rgba(224,92,92,0.25); }
            .wo-udr tbody tr { border-left: 3px solid rgba(244,164,96,0.25); }
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
            <span style="margin-left:24px;font-size:0.82em;color:#999;">Timezone:</span>
            <select id="tzSel" style="background:#252836;border:1px solid #3a3d4a;color:#ddd;border-radius:5px;padding:4px 8px;font-size:0.82em;"></select>
            <span style="margin-left:12px;font-size:0.82em;color:#999;">Risk horizon:</span>
            <select id="riskHorizonSel" style="background:#252836;border:1px solid #3a3d4a;color:#ddd;border-radius:5px;padding:4px 8px;font-size:0.82em;"></select>
            <span style="font-size:0.82em;color:#999;">Smooth:</span>
            <select id="riskSmoothSel" style="background:#252836;border:1px solid #3a3d4a;color:#ddd;border-radius:5px;padding:4px 8px;font-size:0.82em;">
              <option value="1">None</option>
              <option value="3">3-pt</option>
              <option value="6" selected>6-pt (~30 min)</option>
              <option value="12">12-pt (~1 hr)</option>
            </select>
          </div>
          <div class="timeline-scroll" id="timelineScroll">
            <div class="timeline-inner" id="timelineInner">
              <canvas id="timelineChart" title="Click a CGM point to jump prediction detail to that time"></canvas>
              <div style="height:4px;background:#0f1117;"></div>
              <canvas id="riskChart"></canvas>
            </div>
          </div>
        </div>

        <!-- Panel 2: Prediction detail -->
        <div class="panel" id="predPanel">
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


        <!-- Panel 3: Worst Offenders -->
        <div class="panel" id="worstOffendersPanel">
          <h2>Worst Offenders</h2>
          <div class="controls" style="margin-bottom:14px;">
            <label style="color:#999;font-size:0.82em;">Horizon:</label>
            <select id="woHorizonSel" style="background:#252836;border:1px solid #3a3d4a;color:#ddd;border-radius:5px;padding:4px 8px;font-size:0.82em;"></select>
            <span id="woNote" style="margin-left:16px;font-size:0.78em;color:#666;"></span>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
            <div>
              <div style="color:#e05c5c;font-size:0.85em;font-weight:500;margin-bottom:8px;">Top ODR Contributors (over-prediction)</div>
              <table id="woOdrTable" class="wo-table wo-odr"></table>
            </div>
            <div>
              <div style="color:#f4a460;font-size:0.85em;font-weight:500;margin-bottom:8px;">Top UDR Contributors (under-prediction)</div>
              <table id="woUdrTable" class="wo-table wo-udr"></table>
            </div>
          </div>
        </div>

        <!-- Panel 4: Error profile by horizon -->
        <div class="panel">
          <h2>Forecast Error Profile by Horizon</h2>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
            <div>
              <div style="color:#aaa;font-size:12px;margin-bottom:4px;text-align:center">Raw error (mg/dL)</div>
              <div class="chart-wrap"><canvas id="errorChart"></canvas></div>
            </div>
            <div>
              <div style="color:#aaa;font-size:12px;margin-bottom:4px;text-align:center">Delivery risk — overdelivery (red) vs underdelivery (orange), Clarke-Kovatchev weighted</div>
              <div class="chart-wrap"><canvas id="dangerChart"></canvas></div>
            </div>
          </div>
        </div>

        <script>
        // ── Embedded data ─────────────────────────────────────────────────────────
        const BUNDLE = \(bundleJSON);

        // ── Timezone selector ─────────────────────────────────────────────────────
        const NS_TZ = BUNDLE.nsTimezone || null;   // e.g. "America/Chicago" or null
        const LOCAL_TZ = Intl.DateTimeFormat().resolvedOptions().timeZone;

        const tzSel = document.getElementById('tzSel');
        // Always add Local and UTC
        [
          { value: 'local', label: `Local (${LOCAL_TZ})` },
          { value: 'UTC',   label: 'UTC' },
        ].forEach(({value, label}) => {
          const o = document.createElement('option');
          o.value = value; o.text = label;
          tzSel.appendChild(o);
        });
        // Add NS timezone if present and different from local
        if (NS_TZ && NS_TZ !== LOCAL_TZ && NS_TZ !== 'UTC') {
          const o = document.createElement('option');
          o.value = NS_TZ; o.text = `Nightscout (${NS_TZ})`;
          tzSel.appendChild(o);
        }
        tzSel.value = 'local';

        // ── Helpers ───────────────────────────────────────────────────────────────
        const fmt = t => {
          const tz = tzSel.value === 'local' ? LOCAL_TZ : tzSel.value;
          const use24 = (tz === 'UTC');
          return new Intl.DateTimeFormat('en-US', {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit', hour12: !use24,
            timeZone: tz
          }).format(new Date(t));
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

        // ── Risk data helpers (used inside buildTimelineChart) ────────────────────
        const riskByHorizon = new Map();
        for (const pt of (BUNDLE.dtsRiskTimeline || [])) {
          if (!riskByHorizon.has(pt.horizonMin)) riskByHorizon.set(pt.horizonMin, []);
          riskByHorizon.get(pt.horizonMin).push(pt);
        }
        for (const pts of riskByHorizon.values()) pts.sort((a,b) => a.t - b.t);
        const riskHorizons = [...riskByHorizon.keys()].sort((a,b) => a - b);

        // Populate horizon selector
        const riskHorizonSel = document.getElementById('riskHorizonSel');
        riskHorizons.forEach(h => {
          const o = document.createElement('option');
          o.value = h; o.text = h + ' min';
          riskHorizonSel.appendChild(o);
        });
        const defaultRiskH = riskHorizons.find(h => h >= 60) ?? riskHorizons[Math.floor(riskHorizons.length / 2)];
        if (defaultRiskH != null) riskHorizonSel.value = defaultRiskH;

        const movingAvg = (pts, n) => {
          if (n <= 1) return pts.map(p => ({x: p.t, y: p.risk}));
          const out = [];
          for (let i = 0; i < pts.length; i++) {
            const start = Math.max(0, i - Math.floor(n / 2));
            const end   = Math.min(pts.length, start + n);
            let sum = 0;
            for (let j = start; j < end; j++) sum += pts[j].risk;
            out.push({x: pts[i].t, y: sum / (end - start)});
          }
          return out;
        };

        const riskZone = r => Math.abs(r) < 1.5 ? 'green' : Math.abs(r) < 2.5 ? 'yellow' : 'red';
        const zoneColor = {
          green:  { border: '#4caf7d', bg: '#4caf7d22' },
          yellow: { border: '#f0c040', bg: '#f0c04022' },
          red:    { border: '#e05c5c', bg: '#e05c5c22' },
        };

        // Build risk datasets for the separate risk chart
        const buildRiskDatasets = (pts, smoothN, horizonMin) => {
          const smoothed = movingAvg(pts, smoothN);
          if (!smoothed.length) return [];
          const datasets = [];
          let runPts = [smoothed[0]], runZone = riskZone(smoothed[0].y);
          const pushRun = (rp, zone) => {
            const { border, bg } = zoneColor[zone];
            datasets.push({ data: rp, borderColor: border, backgroundColor: bg,
              borderWidth: 2, pointRadius: 0, showLine: true, tension: 0.2,
              fill: { target: { value: 0 }, above: bg, below: bg },
              label: '_risk_' + zone, _horizonMin: horizonMin });
          };
          for (let i = 1; i < smoothed.length; i++) {
            const z = riskZone(smoothed[i].y);
            if (z !== runZone) { runPts.push(smoothed[i]); pushRun(runPts, runZone); runPts = [smoothed[i]]; runZone = z; }
            else runPts.push(smoothed[i]);
          }
          if (runPts.length) pushRun(runPts, runZone);
          const tMin = smoothed[0].x, tMax = smoothed[smoothed.length-1].x;
          datasets.push({ data: [{x:tMin,y:0},{x:tMax,y:0}], borderColor: '#55555588',
            borderWidth: 1, borderDash: [4,4], pointRadius: 0, showLine: true, fill: false, label: '_zero' });
          for (const v of [1.5,-1.5,2.5,-2.5]) {
            datasets.push({ data: [{x:tMin,y:v},{x:tMax,y:v}],
              borderColor: Math.abs(v) < 2 ? '#f0c04044' : '#e05c5c44',
              borderWidth: 1, borderDash: [2,6], pointRadius: 0, showLine: true, fill: false, label: '_ref' });
          }
          return datasets;
        };

        let tlChart = null;
        let riskChart = null;
        let tlYWidth = 0;   // measured left-axis width of timeline chart; applied to risk chart
        const RISK_HEIGHT = 140;

        function buildTimelineChart(zoomFactor) {
          if (tlChart) { tlChart.destroy(); tlChart = null; }
          if (riskChart) { riskChart.destroy(); riskChart = null; }

          const pxPerDay  = basePxPerDay() * zoomFactor;
          const totalPx   = Math.max(Math.round(totalDays * pxPerDay), window.innerWidth - 40);

          // Size both canvases to the same width
          const canvas = document.getElementById('timelineChart');
          canvas.width  = totalPx; canvas.height = CHART_HEIGHT;
          canvas.style.width  = totalPx + 'px'; canvas.style.height = CHART_HEIGHT + 'px';

          const riskCanvas = document.getElementById('riskChart');
          riskCanvas.width  = totalPx; riskCanvas.height = RISK_HEIGHT;
          riskCanvas.style.width  = totalPx + 'px'; riskCanvas.style.height = RISK_HEIGHT + 'px';

          document.getElementById('timelineInner').style.width = totalPx + 'px';

          // Tick granularity
          let timeUnit = 'hour', tickLimit = 12;
          if (pxPerDay < 120) { timeUnit = 'day'; tickLimit = 10; }
          else if (pxPerDay < 400) { timeUnit = 'hour'; tickLimit = Math.round(totalDays * 6); }
          else { timeUnit = 'hour'; tickLimit = Math.round(totalDays * 12); }

          // Shared X axis config (no ticks on timeline — only on risk chart below)
          // ticks.callback routes through fmt() so timezone dropdown affects axis labels too
          const fmtTick = (val) => {
            const tz = tzSel.value === 'local' ? LOCAL_TZ : tzSel.value;
            const use24 = (tz === 'UTC');
            const d = new Date(val);
            // For day-level ticks just show month+day; for hour ticks show time too
            if (timeUnit === 'day') {
              return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', timeZone: tz }).format(d);
            }
            return new Intl.DateTimeFormat('en-US', {
              month: 'short', day: 'numeric',
              hour: '2-digit', minute: '2-digit', hour12: !use24,
              timeZone: tz
            }).format(d);
          };
          const sharedX = {
            type: 'time', min: tlStartMs, max: tlEndMs,
            time: { unit: timeUnit, displayFormats: { hour: 'MMM d HH:mm', day: 'MMM d' } },
            grid: { color: '#232638' }
          };

          tlChart = new Chart(canvas, {
            type: 'scatter',
            data: {
              datasets: [
                { label: 'Raw CGM', data: rawPts,
                  pointRadius: 4, pointBackgroundColor: '#5b9bd5',
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
                  pointRadius: bolusPts.map(p => Math.max(7, p._units * 4)),
                  pointStyle: 'triangle', pointBackgroundColor: '#f4a460',
                  showLine: false, yAxisID: 'yGlucose', order: 1 },
                { label: 'Carbs (g)', data: carbPts,
                  pointRadius: carbPts.map(p => Math.max(7, p._g * 0.18)),
                  pointStyle: 'circle', pointBackgroundColor: '#5cb85c',
                  showLine: false, yAxisID: 'yGlucose', order: 1 }
              ]
            },
            options: {
              responsive: false, maintainAspectRatio: false, animation: false,
              devicePixelRatio: DPR,
              interaction: { mode: 'nearest', intersect: true },
              onClick: (evt, elements) => {
                if (!elements.length) return;
                const el = elements[0];
                if (el.datasetIndex !== 0) return;
                const clickedT = rawPts[el.index].x;
                let bestIdx = 0, bestDist = Infinity;
                BUNDLE.predictions.forEach((p, i) => {
                  const d = Math.abs(p.t - clickedT);
                  if (d < bestDist) { bestDist = d; bestIdx = i; }
                });
                const sl = document.getElementById('predSlider');
                sl.value = bestIdx;
                sl.dispatchEvent(new Event('input'));
                document.getElementById('predPanel').scrollIntoView({ behavior: 'smooth', block: 'start' });
              },
              scales: {
                x: { ...sharedX, ticks: { display: false } },
                yGlucose: {
                  type: 'linear', position: 'left',
                  title: { display: true, text: 'mg/dL', color: '#666' },
                  min: 20, max: 400, grid: { color: '#232638' },
                  afterFit: scale => { tlYWidth = scale.width; }
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
                    title: ctx => fmt(ctx[0].raw.x),
                    label: ctx => {
                      const d = ctx.raw;
                      if (d._units != null) return `Bolus: ${d._units.toFixed(2)} U`;
                      if (d._g    != null)  return `Carbs: ${d._g.toFixed(0)} g`;
                      if (d._rate != null)  return `Basal: ${d._rate.toFixed(3)} U/hr`;
                      return `${ctx.dataset.label}: ${d.y.toFixed(1)} mg/dL`;
                    }
                  }
                }
              }
            }
          });

          // ── Risk chart (separate canvas, same width, same X range) ──────────────
          // Build after tlChart so tlYWidth is already measured via afterFit
          if (riskChart) { riskChart.destroy(); riskChart = null; }
          const h       = parseInt(riskHorizonSel.value) || (defaultRiskH ?? 0);
          const smoothN = parseInt(document.getElementById('riskSmoothSel').value);
          const riskPts = riskByHorizon.get(h) || [];
          const riskDatasets = buildRiskDatasets(riskPts, smoothN, h);

          riskChart = new Chart(riskCanvas, {
            type: 'scatter',
            data: { datasets: riskDatasets },
            options: {
              responsive: false, maintainAspectRatio: false, animation: false,
              devicePixelRatio: DPR,
              scales: {
                x: { ...sharedX, ticks: { maxTicksLimit: tickLimit, color: '#888', callback: fmtTick } },
                y: {
                  type: 'linear', position: 'left',
                  title: { display: true, text: 'DTS Risk', color: '#aaa' },
                  min: -4, max: 4,
                  grid: { color: '#232638' },
                  afterFit: scale => { if (tlYWidth > 0) scale.width = tlYWidth; },
                  ticks: { color: '#888', count: 5,
                    callback: v => {
                      if (v === -4) return 'Hypo −4';
                      if (v ===  4) return 'Hyper +4';
                      if (v ===  0) return '0';
                      return (v < 0 ? '−' : '+') + Math.abs(v);
                    }
                  }
                }
              },
              plugins: {
                legend: { display: false },
                tooltip: {
                  callbacks: {
                    title: ctx => {
                      const ds = ctx[0].dataset;
                      const baseMs = ctx[0].raw.x;
                      const hMin = ds._horizonMin;
                      if (hMin == null) return fmt(baseMs);
                      const evalMs = baseMs + hMin * 60000;
                      return `Forecast at ${fmt(baseMs)}  →  predicted BG at ${fmt(evalMs)}`;
                    },
                    label: ctx => {
                      const ds = ctx.dataset;
                      if (ds.label === '_zero' || ds.label === '_ref') return null;
                      const r = ctx.raw.y;
                      const abs = Math.abs(r);
                      const level = abs >= 3.5 ? 'Extreme' : abs >= 2.5 ? 'High'
                                  : abs >= 1.5 ? 'Moderate' : abs >= 0.5 ? 'Low' : 'Negligible';
                      const dir = r < 0 ? 'Hypo risk' : r > 0 ? 'Hyper risk' : 'No risk';
                      const hMin = ds._horizonMin;
                      const baseMs = ctx.raw.x;
                      const evalMs = baseMs + hMin * 60000;

                      // Look up actual BG at eval time (nearest smoothed CGM point within 6 min)
                      let actualBG = null;
                      let bestActDist = 6 * 60000;
                      for (const p of smoothPts) {
                        const d = Math.abs(p.x - evalMs);
                        if (d < bestActDist) { bestActDist = d; actualBG = p.y; }
                      }

                      // Look up predicted BG: find closest prediction by base time, then interpolate curve at evalMs
                      let predBG = null;
                      let bestPredDist = 10 * 60000;
                      let bestPred = null;
                      for (const p of preds) {
                        const d = Math.abs(p.t - baseMs);
                        if (d < bestPredDist) { bestPredDist = d; bestPred = p; }
                      }
                      if (bestPred) {
                        const curve = bestPred.curve;
                        for (let i = 0; i < curve.length - 1; i++) {
                          const [t0, v0] = curve[i], [t1, v1] = curve[i+1];
                          if (t0 <= evalMs && evalMs <= t1) {
                            predBG = v0 + (v1 - v0) * (evalMs - t0) / (t1 - t0);
                            break;
                          }
                        }
                      }

                      const lines = [
                        `DTS Risk: ${r.toFixed(2)}  ${level} ${dir}`,
                      ];
                      if (predBG != null)   lines.push(`  Predicted BG: ${predBG.toFixed(1)} mg/dL`);
                      if (actualBG != null) lines.push(`  Actual BG:    ${actualBG.toFixed(1)} mg/dL`);
                      return lines;
                    }
                  }
                }
              }
            }
          });
        }

        // Zoom + risk controls all call buildTimelineChart
        const zoomSlider = document.getElementById('zoomSlider');
        const zoomLabel  = document.getElementById('zoomLabel');
        function applyZoom(z) {
          const daysVisible = Math.max(0.1, totalDays / z).toFixed(1);
          zoomLabel.textContent = `${z.toFixed(2)}× — ~${daysVisible} days visible`;
          buildTimelineChart(z);
        }
        zoomSlider.addEventListener('input', () => applyZoom(parseFloat(zoomSlider.value)));
        document.getElementById('riskHorizonSel').addEventListener('change', () => applyZoom(parseFloat(zoomSlider.value)));
        document.getElementById('riskSmoothSel').addEventListener('change',  () => applyZoom(parseFloat(zoomSlider.value)));

        // Ctrl+scroll to zoom, plain scroll to pan (browser default)
        document.getElementById('timelineScroll').addEventListener('wheel', e => {
          if (!e.ctrlKey && !e.metaKey) return;
          e.preventDefault();
          const delta = e.deltaY > 0 ? -0.25 : 0.25;
          const newZ = Math.min(4, Math.max(0.25, parseFloat(zoomSlider.value) + delta));
          zoomSlider.value = newZ;
          applyZoom(newZ);
        }, { passive: false });

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

        // ── Panel 2b: Delivery risk scores ──────────────────────────────────
        new Chart(document.getElementById('dangerChart'), {
          type: 'line',
          data: {
            labels: hp.map(m => m.horizonMin + ' min'),
            datasets: [
              {
                label: 'Overdelivery Risk — forecast too high, BG ended low',
                data: hp.map(m => m.odr),
                borderColor: '#e05c5c', backgroundColor: 'rgba(224,92,92,0.08)',
                borderWidth: 2.5, tension: 0.2, fill: false,
                pointRadius: 3
              },
              {
                label: 'Underdelivery Risk — forecast too low, BG stayed high',
                data: hp.map(m => m.udr),
                borderColor: '#f4a460', backgroundColor: 'rgba(244,164,96,0.08)',
                borderWidth: 2.5, tension: 0.2, fill: false,
                pointRadius: 3
              }
            ]
          },
          options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            scales: {
              x: { grid: { color: '#232638' } },
              y: {
                title: { display: true, text: 'Risk-weighted score (lower = safer)', color: '#666' },
                grid: { color: '#232638' },
                min: 0
              }
            },
            plugins: {
              legend: { labels: { color: '#aaa', boxWidth: 18 } },
              tooltip: {
                callbacks: {
                  label: ctx => {
                    const label = ctx.dataset.label.split('—')[0].trim();
                    return `${label}: ${ctx.parsed.y.toFixed(3)}`;
                  }
                }
              }
            }
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
          const histStart = tMs - 20 * 60000;  // 20 min of context before forecast origin
          const histActual = BUNDLE.rawGlucose
            .filter(p => p.t >= histStart && p.t <= tMs)
            .map(p => ({x: p.t, y: p.v}));

          // Future: both raw and Kalman-smoothed (smoother is the error comparison target)
          const futureEnd = tMs + 6 * 3600000;
          const futureActual = BUNDLE.rawGlucose
            .filter(p => p.t > tMs && p.t <= futureEnd)
            .map(p => ({x: p.t, y: p.v}));

          // Kalman: show 15 min before t so momentum/trend is visible at the origin.
          // The smoother is run on the full CGM history (with warmup), so values before
          // t reflect real prior data, not a cold-started estimate.
          const kalmanContextMs = 15 * 60000;
          const futureSmoothed = BUNDLE.smoothedGlucose
            .filter(p => p.t >= tMs - kalmanContextMs && p.t <= futureEnd)
            .map(p => ({x: p.t, y: p.v}));

          // Prediction curve
          const predCurve = pred.curve.map(([t,v]) => ({x: t, y: v}));
          // No-future-insulin variant (null when not applicable)
          const predCurveNoFuture = pred.curveNoFutureInsulin
            ? pred.curveNoFutureInsulin.map(([t,v]) => ({x: t, y: v}))
            : null;

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
                  label: 'Kalman actual',
                  data: futureSmoothed,
                  pointRadius: 0, showLine: true,
                  borderColor: '#7eb8f7', borderWidth: 2, tension: 0.3, order: 3
                },
                {
                  label: 'Prediction (w/ future insulin)',
                  data: predCurve,
                  pointRadius: 0, showLine: true,
                  borderColor: '#f4a460', borderWidth: 2,
                  borderDash: [5,3], tension: 0.2, order: 2
                },
                {
                  label: 'Prediction (no future insulin)',
                  data: predCurveNoFuture || [],
                  hidden: predCurveNoFuture === null,
                  pointRadius: 0, showLine: true,
                  borderColor: '#f4a46070', borderWidth: 1.5,
                  borderDash: [2,4], tension: 0.2, order: 2
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
                x: {
                  type: 'time',
                  time: { unit: 'hour', displayFormats: { hour: 'MMM d HH:mm' } },
                  ticks: {
                    maxTicksLimit: 10,
                    callback: val => {
                      const tz = tzSel.value === 'local' ? LOCAL_TZ : tzSel.value;
                      const use24 = (tz === 'UTC');
                      return new Intl.DateTimeFormat('en-US', {
                        month: 'short', day: 'numeric',
                        hour: '2-digit', minute: '2-digit', hour12: !use24,
                        timeZone: tz
                      }).format(new Date(val));
                    }
                  },
                  grid: { color: '#232638' }
                },
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
        // Timezone change: rebuild timeline charts and pred panel (all labels use fmt())
        tzSel.addEventListener('change', () => {
          applyZoom(parseFloat(zoomSlider.value));
          updatePredPanel();
        });
        updatePredPanel();

        // ── Panel: Worst Offenders ────────────────────────────────────────────────
        const woHorizonSel = document.getElementById('woHorizonSel');
        const woOdrTable = document.getElementById('woOdrTable');
        const woUdrTable = document.getElementById('woUdrTable');
        const woNote = document.getElementById('woNote');

        // Populate horizon selector (reuse riskHorizons from above)
        riskHorizons.forEach(h => {
          const o = document.createElement('option');
          o.value = h; o.text = h + ' min';
          woHorizonSel.appendChild(o);
        });
        // Default to 90 min or nearest available
        const defaultWoH = riskHorizons.find(h => h >= 90) ?? riskHorizons[riskHorizons.length - 1] ?? 60;
        woHorizonSel.value = defaultWoH;

        function buildWorstOffendersPanel() {
          const h = parseInt(woHorizonSel.value) || defaultWoH;
          const pts = riskByHorizon.get(h) || [];

          // Sort for ODR (positive risk = over-prediction) and UDR (negative risk = under-prediction)
          const sortedOdr = [...pts].sort((a, b) => b.risk - a.risk).slice(0, 10);
          const sortedUdr = [...pts].sort((a, b) => a.risk - b.risk).slice(0, 10);

          // Helper to find IOB/COB from predictions by nearest timestamp
          const findPredContext = (tMs) => {
            let best = null, bestDist = Infinity;
            for (const p of preds) {
              const d = Math.abs(p.t - tMs);
              if (d < bestDist) { bestDist = d; best = p; }
            }
            return best && bestDist < 10 * 60000 ? best : null;
          };

          // Helper to jump to prediction
          const jumpToPred = (tMs) => {
            let bestIdx = 0, bestDist = Infinity;
            preds.forEach((p, i) => {
              const d = Math.abs(p.t - tMs);
              if (d < bestDist) { bestDist = d; bestIdx = i; }
            });
            const sl = document.getElementById('predSlider');
            sl.value = bestIdx;
            sl.dispatchEvent(new Event('input'));
            document.getElementById('predPanel').scrollIntoView({ behavior: 'smooth', block: 'start' });
          };

          // Render table
          const renderTable = (table, rows, isOdr) => {
            table.innerHTML = `
              <thead><tr><th>Time</th><th>Risk</th><th>IOB</th><th>COB</th></tr></thead>
              <tbody>
                ${rows.map(pt => {
                  const ctx = findPredContext(pt.t);
                  const iob = ctx?.iob != null ? ctx.iob.toFixed(2) : '—';
                  const cob = ctx?.cob != null ? ctx.cob.toFixed(0) : '—';
                  const risk = pt.risk.toFixed(2);
                  return `<tr data-t="${pt.t}"><td>${fmt(pt.t)}</td><td>${risk}</td><td>${iob}</td><td>${cob}</td></tr>`;
                }).join('')}
              </tbody>
            `;
            // Attach click handlers
            table.querySelectorAll('tbody tr').forEach(tr => {
              tr.addEventListener('click', () => jumpToPred(parseInt(tr.dataset.t)));
            });
          };

          renderTable(woOdrTable, sortedOdr, true);
          renderTable(woUdrTable, sortedUdr, false);
          woNote.textContent = `Showing top contributors at ${h} min horizon — click any row to inspect`;
        }

        woHorizonSel.addEventListener('change', buildWorstOffendersPanel);
        buildWorstOffendersPanel();

        // Initial render
        applyZoom(1.0);
        </script>
        </body>
        </html>
        """
    }
}
