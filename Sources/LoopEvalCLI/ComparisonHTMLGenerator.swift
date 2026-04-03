// ComparisonHTMLGenerator.swift — ODR/UDR comparison report (matches LoopEval style)

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

    static func write(
        baseline: AggregateScore,
        candidate: AggregateScore,
        meta: ComparisonMeta,
        to url: URL
    ) throws {
        let html = buildHTML(baseline: baseline, candidate: candidate, meta: meta)
        try html.write(to: url, atomically: true, encoding: .utf8)
    }

    // MARK: – Build

    private static func buildHTML(
        baseline: AggregateScore,
        candidate: AggregateScore,
        meta: ComparisonMeta
    ) -> String {

        let baselineSorted  = baseline.horizonMetrics.sorted  { $0.horizon < $1.horizon }
        let candidateSorted = candidate.horizonMetrics.sorted { $0.horizon < $1.horizon }

        // ── JS arrays ─────────────────────────────────────────────────────────────
        let labelsJS = baselineSorted
            .map { "\"\(Int($0.horizon / 60)) min\"" }
            .joined(separator: ", ")

        func jsArr(_ vals: [Double], _ fmt: String) -> String {
            vals.map { String(format: fmt, $0) }.joined(separator: ", ")
        }

        let bODR = jsArr(baselineSorted.map  { $0.odr  }, "%.3f")
        let bUDR = jsArr(baselineSorted.map  { $0.udr  }, "%.3f")
        let cODR = jsArr(candidateSorted.map { $0.odr  }, "%.3f")
        let cUDR = jsArr(candidateSorted.map { $0.udr  }, "%.3f")

        // ── Score cards ───────────────────────────────────────────────────────────
        func card(_ label: String, val: Double, sub: String, color: String) -> String {
            """
            <div class="sc">
              <div class="sc-lbl">\(label)</div>
              <div class="sc-val" style="color:\(color)">\(String(format: "%.1f", val))</div>
              <div class="sc-sub">\(sub)</div>
            </div>
            """
        }

        func deltaArrow(_ a: Double, _ b: Double, lowerBetter: Bool) -> String {
            let d = b - a
            guard abs(d) > 1e-9 else { return "=" }
            let improved = lowerBetter ? d < 0 : d > 0
            let arrow = d < 0 ? "▼" : "▲"
            let pct = abs(a) > 1e-9 ? abs(d / a) * 100 : 0
            let mark = improved ? "✓" : "✗"
            return String(format: "%@ %.1f%% %@", arrow, pct, mark)
        }

        func deltaCard(_ label: String, baseVal: Double, candVal: Double,
                       sub: String, color: String, lowerBetter: Bool = true) -> String {
            let d = candVal - baseVal
            let pct = abs(baseVal) > 1e-9 ? (d / abs(baseVal)) * 100 : 0
            let arrow = d < 0 ? "▼" : (d > 0 ? "▲" : "=")
            let improved = lowerBetter ? d < 0 : d > 0
            let mark = abs(d) < 1e-9 ? "" : (improved ? " ✓" : " ✗")
            let dStr = String(format: "Δ %.1f%% %@ %.1f%@", abs(pct), arrow, abs(d), mark)
            return """
            <div class="sc">
              <div class="sc-lbl">\(label)</div>
              <div class="sc-val" style="color:\(color)">\(String(format: "%.1f", candVal))</div>
              <div class="sc-sub">\(sub)</div>
              <div class="sc-delta">\(dStr)</div>
            </div>
            """
        }

        let baseCards = """
        <div class="run-label">\(esc(meta.baselineLabel))</div>
        <div class="sc-row">
          \(card("ODR — Overdelivery Risk", val: baseline.weightedOverdeliveryRisk,  sub: "weighted avg",         color: "#e8685a"))
          \(card("UDR — Underdelivery Risk", val: baseline.weightedUnderdeliveryRisk, sub: "weighted avg",         color: "#f0a84a"))
          \(card("Primary (ODR + UDR)",      val: baseline.primaryScore,              sub: "optimization target ↓", color: "#6a8ef0"))
          \(card("RMSE (weighted)",          val: baseline.weightedRMSE,              sub: "mg/dL · reference",    color: "#4dcfb8"))
        </div>
        """

        let candCards = """
        <div class="run-label" style="margin-top:28px">\(esc(meta.candidateLabel))</div>
        <div class="sc-row">
          \(deltaCard("ODR — Overdelivery Risk",  baseVal: baseline.weightedOverdeliveryRisk,  candVal: candidate.weightedOverdeliveryRisk,  sub: "weighted avg",         color: "#e8685a"))
          \(deltaCard("UDR — Underdelivery Risk", baseVal: baseline.weightedUnderdeliveryRisk, candVal: candidate.weightedUnderdeliveryRisk, sub: "weighted avg",         color: "#f0a84a"))
          \(deltaCard("Primary (ODR + UDR)",      baseVal: baseline.primaryScore,              candVal: candidate.primaryScore,              sub: "optimization target ↓", color: "#6a8ef0"))
          \(deltaCard("RMSE (weighted)",          baseVal: baseline.weightedRMSE,              candVal: candidate.weightedRMSE,              sub: "mg/dL · reference",    color: "#4dcfb8"))
        </div>
        """

        // ── Timestamp ─────────────────────────────────────────────────────────────
        let iso = ISO8601DateFormatter()
        let runStr = iso.string(from: meta.runDate)

        // ── HTML ──────────────────────────────────────────────────────────────────
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>LoopEval — ODR / UDR by Horizon</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <style>
          *{box-sizing:border-box;margin:0;padding:0}
          body{background:#0f1117;color:#d0d4e8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:15px}
          .page{max-width:1000px;margin:0 auto;padding:48px 28px 80px}

          h1{font-size:2rem;font-weight:700;color:#fff;margin-bottom:6px}
          .sub{color:#7a7f9a;font-size:.92rem;margin-bottom:36px}

          .panel{background:#161b2e;border:1px solid #252a3a;border-radius:12px;padding:28px 28px 24px;margin-bottom:32px}
          .panel-title{font-size:.95rem;font-weight:600;color:#c8ccd8;margin-bottom:20px}
          .chart-wrap{position:relative;height:400px}

          .run-label{font-size:.88rem;color:#888da8;font-weight:500;margin-bottom:10px;letter-spacing:.3px}
          .sc-row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
          @media(max-width:700px){.sc-row{grid-template-columns:repeat(2,1fr)}}
          .sc{background:#0a0d18;border:1px solid #1e2230;border-radius:10px;padding:18px 14px;text-align:center}
          .sc-lbl{font-size:.72rem;color:#888da8;margin-bottom:10px;line-height:1.4}
          .sc-val{font-size:2rem;font-weight:700;margin-bottom:6px;letter-spacing:-1px}
          .sc-sub{font-size:.7rem;color:#666b85}
          .sc-delta{font-size:.7rem;color:#666b85;margin-top:4px}

          .footer{text-align:center;font-size:.78rem;color:#555a75;margin-top:40px}

          /* Explainer */
          .explainer{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:0}
          @media(max-width:640px){.explainer{grid-template-columns:1fr}}
          .exp-card{background:#0a0d18;border:1px solid #1e2230;border-radius:10px;padding:18px 20px}
          .exp-card h3{font-size:.85rem;font-weight:600;margin-bottom:10px;display:flex;align-items:center;gap:8px}
          .exp-card p{font-size:.8rem;color:#888da8;line-height:1.65;margin-bottom:8px}
          .exp-card p:last-child{margin-bottom:0}
          .exp-card code{background:#1a1e2e;border-radius:4px;padding:2px 6px;font-size:.75rem;color:#c8ccd8;font-family:'SF Mono',Monaco,monospace}
          .pill{display:inline-block;border-radius:4px;padding:2px 8px;font-size:.7rem;font-weight:600;margin-right:4px}
          .pill-red{background:rgba(232,104,90,.18);color:#e8685a}
          .pill-orange{background:rgba(240,168,74,.18);color:#f0a84a}
          .pill-blue{background:rgba(106,142,240,.18);color:#6a8ef0}
          .formula{font-family:'SF Mono',Monaco,monospace;font-size:.72rem;color:#9da8c8;background:#111520;border-radius:6px;padding:8px 12px;margin:8px 0;line-height:1.7}
        </style>
        </head>
        <body>
        <div class="page">
          <h1>LoopEval — ODR / UDR by Horizon</h1>
          <p class="sub">Overdelivery &amp; Underdelivery Risk across forecast horizons · target range 100–115 mg/dL</p>

          <div class="panel">
            <div class="panel-title">Overdelivery and Underdelivery Risk by forecast horizon</div>
            <div class="chart-wrap"><canvas id="chart"></canvas></div>
          </div>

          <div class="panel">
            \(baseCards)
            \(candCards)
          </div>

          <div class="panel">
            <div class="panel-title">What are ODR and UDR?</div>
            <div class="explainer">
              <div class="exp-card">
                <h3><span class="pill pill-red">ODR</span> Overdelivery Risk</h3>
                <p>Penalises forecasts that predict BG will be <strong>higher than it actually is</strong>, when actual BG is <strong>below the target floor</strong> (100 mg/dL). This is the dangerous case where Loop keeps delivering insulin into a falling or already-low BG.</p>
                <p>Cost is <strong>zero</strong> when BG is in-range or high. Only over-predictions in the low zone are penalised, weighted by the Clarke-Kovatchev low-risk function <code>rl(actual)</code> — so an error at BG 60 costs far more than the same error at BG 95.</p>
                <div class="formula">ODR = √( Σ rl(actual) · max(predicted − actual, 0)² / n )</div>
              </div>
              <div class="exp-card">
                <h3><span class="pill pill-orange">UDR</span> Underdelivery Risk</h3>
                <p>Penalises forecasts that predict BG will be <strong>lower than it actually is</strong>, when actual BG is <strong>above the target ceiling</strong> (115 mg/dL). This is the case where Loop withholds a correction it should have given.</p>
                <p>Cost is <strong>zero</strong> when BG is in-range or low. Only under-predictions in the high zone are penalised, weighted by the high-risk function <code>rh(actual)</code>.</p>
                <div class="formula">UDR = √( Σ rh(actual) · max(actual − predicted, 0)² / n )</div>
              </div>
              <div class="exp-card">
                <h3><span class="pill pill-blue">Primary</span> ODR + UDR — ⚠️ interpret with caution</h3>
                <p>The sum of ODR and UDR. <strong>However, this metric has a fundamental structural bias that makes it an unreliable optimisation target.</strong></p>
                <p>Loop cannot know about future unannounced carbs. When a meal raises BG, the algorithm's prediction will almost always be lower than actual — triggering UDR — even though withholding that dose was the correct, safe behaviour. Optimising to reduce UDR would mean making predictions systematically higher, which would cause over-delivery and more lows.</p>
                <p>UDR is large by design. The bias cannot be quantified or corrected for. <strong>ODR is the more meaningful safety signal.</strong></p>
              </div>
              <div class="exp-card">
                <h3>Why UDR dominates — and why that's expected</h3>
                <p>UDR is almost always much larger than ODR. The primary reason is <strong>unannounced future carbs</strong>: Loop predicts BG without knowing what a person will eat, so under-predictions when BG rises after meals are structural and unavoidable.</p>
                <p>Secondary reason: Clarke-Kovatchev risk weighting — <code>rl(60) ≈ 29.6</code> vs <code>rh(200) ≈ 3.0</code> — applies ~10× more weight to hypo errors. Even so, the sheer volume of high-BG under-predictions from unannounced carbs overwhelms this, producing a large UDR.</p>
                <p>A large UDR is not a red flag. Trying to shrink it would be dangerous.</p>
              </div>
            </div>
          </div>

          <p class="footer">Generated \(runStr) · 2 run(s)</p>
        </div>

        <script>
        const labels = [\(labelsJS)];

        const peakPlugin = {
          id:'peak',
          afterDraw(chart){
            const {ctx,chartArea:{top,bottom},scales:{x}} = chart;
            const px = x.getPixelForValue('90 min');
            if(!px) return;
            ctx.save();
            ctx.strokeStyle='rgba(100,130,220,0.35)';
            ctx.lineWidth=1.5;
            ctx.setLineDash([5,4]);
            ctx.beginPath();ctx.moveTo(px,top);ctx.lineTo(px,bottom);ctx.stroke();
            ctx.fillStyle='rgba(100,130,220,0.65)';
            ctx.font='11px system-ui';
            ctx.fillText('peak weight',px+6,top+15);
            ctx.restore();
          }
        };

        new Chart(document.getElementById('chart'),{
          type:'line',
          data:{
            labels,
            datasets:[
              {label:'\(esc(meta.baselineLabel)) ODR',data:[\(bODR)],borderColor:'#e8685a',pointBackgroundColor:'#e8685a',borderWidth:2.5,pointRadius:5,tension:.3,yAxisID:'yODR'},
              {label:'\(esc(meta.baselineLabel)) UDR',data:[\(bUDR)],borderColor:'#f0a84a',pointBackgroundColor:'#f0a84a',borderWidth:2.5,pointRadius:5,tension:.3,yAxisID:'yUDR'},
              {label:'\(esc(meta.candidateLabel)) ODR',data:[\(cODR)],borderColor:'#6a8ef0',pointBackgroundColor:'#6a8ef0',borderWidth:2,pointRadius:5,tension:.3,borderDash:[6,3],yAxisID:'yODR'},
              {label:'\(esc(meta.candidateLabel)) UDR',data:[\(cUDR)],borderColor:'#4dcfb8',pointBackgroundColor:'#4dcfb8',borderWidth:2,pointRadius:5,tension:.3,borderDash:[6,3],yAxisID:'yUDR'},
            ]
          },
          options:{
            responsive:true,maintainAspectRatio:false,
            interaction:{mode:'index',intersect:false},
            plugins:{
              legend:{labels:{color:'#b0b5c8',font:{size:12},usePointStyle:true,pointStyleWidth:14,padding:18}},
              tooltip:{
                backgroundColor:'#1e2338',titleColor:'#e0e3ed',bodyColor:'#909ab8',
                borderColor:'#2e3450',borderWidth:1,padding:12,
                callbacks:{label:c=>` ${c.dataset.label}: ${c.parsed.y.toFixed(3)}`}
              }
            },
            scales:{
              x:{ticks:{color:'#777b98',font:{size:12}},grid:{color:'rgba(255,255,255,0.04)'}},
              yODR:{
                type:'linear',position:'left',
                title:{display:true,text:'Overdelivery Risk (ODR)',color:'#e8685a',font:{size:12}},
                ticks:{color:'#e8685a',font:{size:11}},
                grid:{color:'rgba(255,255,255,0.04)'},
                min:0
              },
              yUDR:{
                type:'linear',position:'right',
                title:{display:true,text:'Underdelivery Risk (UDR)',color:'#f0a84a',font:{size:12}},
                ticks:{color:'#f0a84a',font:{size:11}},
                grid:{drawOnChartArea:false},
                min:0
              }
            }
          },
          plugins:[peakPlugin]
        });
        </script>
        </body>
        </html>
        """
    }

    private static func esc(_ s: String) -> String {
        s.replacingOccurrences(of: "&", with: "&amp;")
         .replacingOccurrences(of: "<", with: "&lt;")
         .replacingOccurrences(of: ">", with: "&gt;")
         .replacingOccurrences(of: "'", with: "&#39;")
         .replacingOccurrences(of: "\"", with: "&quot;")
    }
}
