// ISFExploreHTMLGenerator.swift — HTML report for `isf-explore`.
//
// Panels:
//  1. ICE + rolling ICE time series with meal/exercise threshold bands and
//     user-entered carb markers (carbs are visual context only).
//  2. local_ISF(t) colored by class (meal = red, exercise = blue, neutral = green).
//  3. Side-by-side histograms: all samples vs neutral-only.

import EvalCore
import Foundation

enum ISFExploreHTMLGenerator {

    static func generate(
        result: ISFExploreResult,
        interval: DateInterval,
        doses: [EvalInsulinDose],
        carbs: [EvalCarbEntry],
        options: ISFExploreOptions,
        latitude: Double = 40.0,
        longitude: Double = -93.0,
        totalInsulinU: Double = 0,
        tdd: Double = 0,
        avgCR: Double = 0
    ) -> String {

        let samples = result.samples
        let summary = result.summary

        // Time-series charts render only the most recent N days to keep the
        // browser responsive on long date ranges. Aggregated charts (diurnal,
        // sweeps, histogram) use the full data set.
        let chartWindowDays = 5.0
        let chartWindowStart = max(
            interval.start,
            interval.end.addingTimeInterval(-chartWindowDays * 86400)
        )

        // ── Time-series JS data ────────────────────────────────────────────────
        // Split by class so Chart.js can render each as its own dataset.
        func seriesJS(for klass: ISFClass) -> String {
            samples
                .filter { $0.classification == klass && $0.time >= chartWindowStart }
                .map { s -> String in
                    let x = s.time.timeIntervalSince1970 * 1000
                    return String(
                        format: "{x:%.0f,y:%.2f,ice:%.2f,iob:%.2f,bg:%.0f,w:%.3f}",
                        x, s.localISF, s.ice, s.iob, s.bgSmoothed, s.weight
                    )
                }
                .joined(separator: ",")
        }
        let mealJS      = seriesJS(for: .meal)
        let exerciseJS  = seriesJS(for: .exercise)
        let neutralJS   = seriesJS(for: .neutral)

        // ICE + rolling ICE for the top panel.
        let iceJS = samples
            .filter { $0.time >= chartWindowStart }
            .map { s -> String in
                let x = s.time.timeIntervalSince1970 * 1000
                return String(format: "{x:%.0f,y:%.3f}", x, s.ice)
            }.joined(separator: ",")
        let rollingIceJS = samples
            .filter { $0.time >= chartWindowStart }
            .map { s -> String in
                let x = s.time.timeIntervalSince1970 * 1000
                return String(format: "{x:%.0f,y:%.3f}", x, s.rollingICE)
            }.joined(separator: ",")

        // BG + IOB panels (full timelines, clipped to chart window).
        let bgJS = result.smoothedCGM
            .filter { $0.startDate >= chartWindowStart && $0.startDate <= interval.end }
            .map { s -> String in
                let x = s.startDate.timeIntervalSince1970 * 1000
                let y = s.quantity.doubleValue(for: .milligramsPerDeciliter)
                return String(format: "{x:%.0f,y:%.1f}", x, y)
            }
            .joined(separator: ",")

        let iobJS = result.iobTimeline
            .filter { $0.time >= chartWindowStart && $0.time <= interval.end }
            .map { v -> String in
                let x = v.time.timeIntervalSince1970 * 1000
                return String(format: "{x:%.0f,y:%.3f}", x, v.iob)
            }
            .joined(separator: ",")

        // Stable-ICE regression sweeps — structured objects for tooltip display.
        let sweepTData = summary.stableSweepT.map {
            String(format: "{x:%.2f,isf:%.2f,n:%d,r2:%.3f}",
                   $0.thresholdMgdlMin, $0.isfEstimate, $0.n, $0.rSquared)
        }.joined(separator: ",")
        let sweepMData = summary.stableSweepM.map {
            String(format: "{x:%.0f,isf:%.2f,n:%d,r2:%.3f}",
                   $0.halfWindowMinutes, $0.isfEstimate, $0.n, $0.rSquared)
        }.joined(separator: ",")

        // Diurnal buckets — one per local hour.
        let diurnalJS = summary.diurnal.map { d -> String in
            let isf = d.medianISF.isNaN ? "null" : String(format: "%.2f", d.medianISF)
            let sisf = d.stableMedianISF.isNaN ? "null" : String(format: "%.2f", d.stableMedianISF)
            let ice = d.medianICE.isNaN ? "null" : String(format: "%.3f", d.medianICE)
            return "{h:\(d.hour),n:\(d.n),sn:\(d.stableN),isf:\(isf),sisf:\(sisf),ice:\(ice)}"
        }.joined(separator: ",")

        // Diurnal quantile regression — one per 2-hour bin.
        // midHour is the bin midpoint (e.g. 01, 03, 05, … 23) used on the x-axis.
        // m  = median v_cgm (mg/dL/min) over the stable-ICE subset of the bin.
        //      Since v_insulin is net-of-basal, stable-ICE windows have
        //      activity ≈ 0, so this median is a direct reading of per-bin
        //      basal/EGP mismatch: m>0 = basal under-covers, m<0 = over-covers.
        // sn = number of stable-ICE samples used for `m`.
        let diurnalQuantileJS = summary.diurnalQuantile.map { d -> String in
            let mid = Double(d.binStartHour) + Double(d.binEndHour - d.binStartHour) / 2.0
            let isf = d.isfEstimate.isNaN ? "null" : String(format: "%.2f", d.isfEstimate)
            let sched = d.scheduledISF.isNaN ? "null" : String(format: "%.2f", d.scheduledISF)
            let r2 = d.pseudoR2.isNaN ? "null" : String(format: "%.4f", d.pseudoR2)
            let m = d.stableMedianVCgm.isNaN ? "null" : String(format: "%.4f", d.stableMedianVCgm)
            return "{mid:\(mid),s:\(d.binStartHour),e:\(d.binEndHour),n:\(d.n),isf:\(isf),sched:\(sched),r2:\(r2),m:\(m),sn:\(d.stableN)}"
        }.joined(separator: ",")
        let diurnalTau = summary.diurnalQuantile.first?.quantile ?? 0.10

        // Sun-elevation series at 30-min cadence over the chart window.
        // Emits [t_ms, sin_elevation] pairs; sin_elev <= 0 = below horizon.
        let sunSeries = Self.sunElevationSeries(
            from: chartWindowStart,
            to: interval.end,
            stride: 30 * 60,
            latitudeDeg: latitude,
            longitudeDeg: longitude
        )
        let sunJS = sunSeries.map { pt in
            String(format: "[%.0f,%.3f]", pt.t.timeIntervalSince1970 * 1000, pt.sinElev)
        }.joined(separator: ",")

        let doseJS = doses
            .filter { $0.startDate >= chartWindowStart && $0.startDate <= interval.end }
            .map { d -> String in
                let x = d.startDate.timeIntervalSince1970 * 1000
                let label = d.deliveryType == .bolus ? "B" : "T"
                return String(format: "{x:%.0f,v:%.2f,k:\"%@\"}", x, d.volume, label)
            }
            .joined(separator: ",")

        let carbJS = carbs
            .filter { $0.startDate >= chartWindowStart && $0.startDate <= interval.end }
            .map { c -> String in
                let x = c.startDate.timeIntervalSince1970 * 1000
                let grams = c.quantity.doubleValue(for: .gram)
                return String(format: "{x:%.0f,g:%.0f}", x, grams)
            }
            .joined(separator: ",")

        // ── Histograms ─────────────────────────────────────────────────────────
        let allVals     = samples.map { $0.localISF }
        let allWeights  = samples.map { $0.weight }
        let neutralSamples = samples.filter { $0.classification == .neutral }
        let neutralVals    = neutralSamples.map { $0.localISF }
        let neutralWeights = neutralSamples.map { $0.weight }

        // Shared bin edges so the two histograms can be overlaid.
        let (edges, allCounts, allWtCounts) = histogram(
            values: allVals, weights: allWeights, binWidth: 10.0
        )
        let neutralAligned = alignHistogram(
            values: neutralVals, weights: neutralWeights, edges: edges
        )
        let binMidsJS = zip(edges.dropLast(), edges.dropFirst())
            .map { String(format: "%.1f", ($0.0 + $0.1) / 2) }
            .joined(separator: ",")
        let allCountsJS  = allCounts.map { String($0) }.joined(separator: ",")
        let allWtJS      = allWtCounts.map { String(format: "%.2f", $0) }.joined(separator: ",")
        let neutCountsJS = neutralAligned.counts.map { String($0) }.joined(separator: ",")
        let neutWtJS     = neutralAligned.weighted.map { String(format: "%.2f", $0) }.joined(separator: ",")

        // Horizontal scrolling: aim for ~3 days per viewport width on wide
        // date ranges. Width as a % of the scroll-container (which is 100%
        // of the panel). Never shrink below 100%.
        let chartWindowSpanDays = max(
            1.0,
            interval.end.timeIntervalSince(chartWindowStart) / 86400.0
        )
        let targetDaysPerScreen = 3.0
        let widthPct = max(100, Int((chartWindowSpanDays * 100.0 / targetDaysPerScreen).rounded()))

        // ── Summary cards ──────────────────────────────────────────────────────
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime]
        let title = "ISF Explore — \(iso.string(from: interval.start)) → \(iso.string(from: interval.end))"

        let fmt: (Double) -> String = { v in v.isNaN ? "—" : String(format: "%.1f", v) }

        func statsTable(_ label: String, _ s: ISFStats) -> String {
            let p = s.percentiles
            return """
            <div class="stats-col">
              <h3>\(label)</h3>
              <table>
                <tr><td>count</td><td>\(s.count)</td></tr>
                <tr><td>median</td><td>\(fmt(s.median))</td></tr>
                <tr><td>weighted mean</td><td>\(fmt(s.weightedMean))</td></tr>
                <tr><td>mean</td><td>\(fmt(s.mean))</td></tr>
                <tr><td>P10</td><td>\(fmt(p[0.10] ?? .nan))</td></tr>
                <tr><td>P25</td><td>\(fmt(p[0.25] ?? .nan))</td></tr>
                <tr><td>P75</td><td>\(fmt(p[0.75] ?? .nan))</td></tr>
                <tr><td>P90</td><td>\(fmt(p[0.90] ?? .nan))</td></tr>
              </table>
            </div>
            """
        }

        let classCards = """
        <div class="cards">
          \(card("meal",     "\(summary.mealCount) samples", "#e76f51"))
          \(card("exercise", "\(summary.exerciseCount) samples", "#457b9d"))
          \(card("neutral",  "\(summary.neutralCount) samples", "#6a994e"))
          \(card("meal thr", String(format: "ICE > +%.2f mg/dL/min", options.mealThreshold), "#e76f51"))
          \(card("ex. thr",  String(format: "ICE < −%.2f mg/dL/min", options.exerciseThreshold), "#457b9d"))
          \(card("ICE window", String(format: "%.0f min", options.iceWindowMinutes), "#888"))
          \(card("meal tail", String(format: "%.0f min", options.mealTailMinutes), "#888"))
          \(card("ex. tail",  String(format: "%.0f min", options.exerciseTailMinutes), "#888"))
        </div>
        """

        // Stable-ICE regression block (primary estimate).
        let regBlock: String = {
            guard let r = summary.primaryStableRegression else {
                return "<div class=\"stats-col\"><h3>Stable-ICE regression</h3><table><tr><td colspan=2>insufficient data</td></tr></table></div>"
            }
            return """
            <div class="stats-col">
              <h3>Stable-ICE regression · v_cgm ~ activity</h3>
              <table>
                <tr><td>ISF estimate (slope)</td><td>\(String(format: "%.1f mg/dL/U", r.isfEstimate))</td></tr>
                <tr><td>intercept (residual C)</td><td>\(String(format: "%.3f mg/dL/min", r.intercept))</td></tr>
                <tr><td>R²</td><td>\(String(format: "%.3f", r.rSquared))</td></tr>
                <tr><td>n samples</td><td>\(r.n)</td></tr>
                <tr><td>|rolling ICE| ≤</td><td>\(String(format: "%.2f mg/dL/min", r.thresholdMgdlMin))</td></tr>
                <tr><td>stable for ±</td><td>\(String(format: "%.0f min", r.halfWindowMinutes))</td></tr>
              </table>
            </div>
            """
        }()

        let tddBlock: String = {
            guard tdd > 0 else { return "" }
            let ruleISF = 1800 / tdd
            return """
            <div class="stats-col">
              <h3>1800 rule benchmark</h3>
              <table>
                <tr><td>total insulin</td><td>\(String(format: "%.1f U", totalInsulinU))</td></tr>
                <tr><td>days covered</td><td>\(String(format: "%.1f", interval.duration / 86400.0))</td></tr>
                <tr><td>TDD</td><td>\(String(format: "%.1f U/day", tdd))</td></tr>
                <tr><td>1800/TDD</td><td>\(String(format: "%.1f mg/dL/U", ruleISF))</td></tr>
              </table>
            </div>
            """
        }()

        // Carb estimate derived from: (TDD − stable-ICE delivery rate) × avg CR.
        // Stable-ICE windows have v_carb ≈ 0 by construction, so the delivery
        // rate during them is a clean measurement of the insulin needed to
        // cover endogenous glucose production. Subtract from TDD to isolate
        // carb-covering insulin, multiply by CR to get grams.
        let carbsBlock: String = {
            guard let egp = summary.egp, tdd > 0, avgCR > 0 else { return "" }
            let carbInsulin = max(0, tdd - egp.deliveryRatePerDay)
            let carbsG = carbInsulin * avgCR
            return """
            <div class="stats-col">
              <h3>Carb estimate (EGP-subtraction)</h3>
              <table>
                <tr><td>TDD</td><td>\(String(format: "%.1f U/day", tdd))</td></tr>
                <tr><td>stable-ICE rate (EGP proxy)</td><td>\(String(format: "%.2f U/day", egp.deliveryRatePerDay))</td></tr>
                <tr><td>stable-ICE sample</td><td>\(egp.stableSampleCount) windows · \(String(format: "%.0f", egp.stableMinutes)) min</td></tr>
                <tr><td>carb-covering insulin</td><td>\(String(format: "%.2f U/day", carbInsulin))</td></tr>
                <tr><td>avg CR (time-weighted)</td><td>\(String(format: "%.2f g/U", avgCR))</td></tr>
                <tr><td><strong>est. daily carbs</strong></td><td><strong>\(String(format: "%.0f g/day", carbsG))</strong></td></tr>
              </table>
              <p class="caption">Measures actual delivery during periods where carbs are physiologically absent (stable ICE). Subtract from TDD → carb-covering insulin → ×CR = grams. Avoids the artificial basal/bolus split.</p>
            </div>
            """
        }()

        let statsBlock = """
        <div class="stats-row">
          \(statsTable("ALL", summary.allStats))
          \(statsTable("NEUTRAL (classifier)", summary.neutralStats))
          \(statsTable("FASTING \(String(format: "%02d:00–%02d:00", options.fastingHourStart, options.fastingHourEnd))", summary.fastingStats))
          \(regBlock)
          \(tddBlock)
          \(carbsBlock)
        </div>
        """

        // ── Thresholds for the ICE chart guide lines ──────────────────────────
        let mealThr = String(format: "%.3f", options.mealThreshold)
        let exThr   = String(format: "%.3f", -options.exerciseThreshold)

        return """
        <!doctype html>
        <html lang="en">
        <head>
        <meta charset="utf-8">
        <title>\(title)</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
        <style>
          :root { color-scheme: dark; }
          body { font-family: -apple-system, system-ui, sans-serif; background:#181818; color:#ddd; margin:16px; }
          h1 { font-size: 18px; margin-bottom: 4px; }
          .sub { color:#888; font-size: 13px; margin-bottom: 16px; }
          .cards { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:12px; }
          .card { background:#242424; padding:8px 12px; border-radius:6px; min-width:110px; border-left: 3px solid #555; }
          .card .k { color:#888; font-size:11px; text-transform:uppercase; letter-spacing:.05em; }
          .card .v { color:#eee; font-size:14px; font-weight:600; margin-top:2px; }
          .stats-row { display:flex; gap:16px; flex-wrap:wrap; margin-bottom:14px; }
          .stats-col { background:#242424; padding:10px 14px; border-radius:6px; min-width: 260px; max-width: 380px; }
          .stats-col h3 { font-size: 12px; color: #bbb; text-transform: uppercase; letter-spacing:.05em; margin: 0 0 6px 0; font-weight: 500; }
          .stats-col table { border-collapse: collapse; font-size: 13px; width: 100%; }
          .stats-col td { padding: 2px 8px; }
          .stats-col tr td:first-child { color: #888; }
          .stats-col tr td:last-child { color: #eee; text-align: right; font-family: ui-monospace, SFMono-Regular, monospace; }
          .blurb { background:#1e1e1e; border-left: 3px solid #6a994e; padding: 10px 14px; border-radius: 4px; margin-bottom: 14px; font-size: 13px; line-height: 1.5; color: #cfcfcf; }
          .blurb summary { cursor: pointer; color: #eee; font-weight: 500; font-size: 13px; }
          .blurb summary:hover { color: #fff; }
          .blurb[open] summary { margin-bottom: 8px; }
          .blurb p { margin: 6px 0; }
          .blurb code, .blurb .eq { font-family: ui-monospace, SFMono-Regular, monospace; background:#0f0f0f; padding: 1px 5px; border-radius: 3px; color: #e0e0e0; }
          .blurb .eq { display:block; padding: 6px 10px; margin: 8px 0; font-size: 12.5px; }
          .blurb ul { margin: 6px 0; padding-left: 20px; }
          .blurb li { margin: 3px 0; }
          .panel { background:#202020; border-radius:8px; padding:12px; margin-bottom:14px; }
          .panel h2 { font-size: 14px; margin:0 0 8px 0; color:#bbb; font-weight:500; }
          .chart-wrap    { position:relative; height: 220px; }
          .chart-wrap-md { position:relative; height: 360px; }
          .chart-wrap-sm { position:relative; height: 280px; }
          .scroll-x { overflow-x: auto; overflow-y: hidden; width: 100%; }
          .scroll-x::-webkit-scrollbar { height: 8px; }
          .scroll-x::-webkit-scrollbar-track { background: #1a1a1a; }
          .scroll-x::-webkit-scrollbar-thumb { background: #444; border-radius: 4px; }
          .scroll-x::-webkit-scrollbar-thumb:hover { background: #555; }
          .note { color:#888; font-size:12px; margin-top:6px; }
        </style>
        </head>
        <body>
        <h1>\(title)</h1>
        <div class="sub">Pointwise implied ISF, classified by sustained ICE (insulin counteraction effect). User-entered carbs shown for visual reference only — not used in detection.</div>

        <details class="blurb" open>
          <summary>How do we estimate true ISF from the data?</summary>

          <p><strong>Local ISF</strong> is a per-sample estimate of the Insulin Sensitivity Factor implied by how fast BG moved relative to how much insulin was acting. At each 5-minute CGM interval:</p>
          <span class="eq">local_ISF(t) = ISF_scheduled × v_cgm_smoothed(t) / v_insulin_modeled(t)</span>

          <p>Per-sample local_ISF is invariant to the configured ISF (the factor cancels: <code>local_ISF = v_cgm / activity</code>, where <code>activity = v_insulin / ISF_sched</code> doesn&rsquo;t depend on the schedule). But it&rsquo;s noisy — meals inflate it (carbs raise <code>v_cgm</code> without raising activity) and exercise depresses it.</p>

          <p>The real task is to estimate the slope of <code>v_cgm = ISF × activity + noise</code> in the presence of <em>one-sided</em> carb contamination (<code>v_carb ≥ 0</code> always) plus smaller symmetric basal/EGP noise. Naive OLS over all samples absorbs the positive carb bias and lands near ~25 mg/dL/U — the wrong answer.</p>

          <p><strong>Primary estimator: quantile regression at low τ.</strong> Since carbs only push <code>v_cgm</code> upward, the <em>lower envelope</em> of the (activity, <code>v_cgm</code>) scatter is approximately carb-free. Quantile regression at τ=0.05–0.10 fits that envelope directly by minimizing the pinball loss <code>ρ_τ(r) = r·(τ − 𝟙[r&lt;0])</code>. No subset selection, no ISF guess needed: the x-axis reparametrization <code>activity = v_insulin / ISF_sched</code> makes the slope invariant (<code>slope × ISF_sched</code> is preserved under any rescaling of the schedule). We sweep τ below and report the fits.</p>

          <p><strong>Independent anchors that cross-check the quantile answer:</strong> the <em>1800 rule</em> (ISF ≈ 1800 / TDD) uses only total delivered insulin — invariant to both ISF and basal schedules. <em>Carb-excluded OLS</em> (drop samples within 15 min before / 4 h after any announced carb) and the <em>activity-threshold sweep</em> (keep only samples with large <code>|activity|</code>) are two more ISF-invariant cross-checks. If these three agree within a few mg/dL/U, the estimate is real.</p>

          <p><strong>Stable-ICE regression as a refinement, not a bootstrap.</strong> Selecting samples where <code>|rolling_ICE| = |v_cgm − v_insulin|</code> stays small for ±M minutes, then OLS-regressing, gives an intuitive "insulin-only windows" estimator. But <code>v_insulin</code> scales with <code>ISF_sched</code>, so the selector shifts with the ISF seed and the method does not converge under iteration (starting at 40 drifts down to ~18; starting at 120 drifts to ~108). It&rsquo;s useful once you&rsquo;re already near the answer; it can&rsquo;t locate the answer on its own.</p>

          <p><strong>What does NOT identify true ISF:</strong> the ICE-bin plot&rsquo;s intercept at ICE=0 is a tautology — it always equals <code>ISF_scheduled</code> regardless of the real ISF (verified by overriding ISF to 40 and getting intercept ≈ 41). Don&rsquo;t trust that value.</p>
        </details>

        \(classCards)
        \(statsBlock)

        <div class="panel">
          <h2>BG (Kalman-smoothed) with doses &amp; carbs</h2>
          <div class="note"><em>Time-series panels below show the most recent \(Int(chartWindowDays)) days (\(iso.string(from: chartWindowStart)) → \(iso.string(from: interval.end))). Aggregated charts — diurnal, sweep, histogram — use the full date range.</em></div>
          <div class="scroll-x time-scroller"><div class="chart-wrap" style="width:\(widthPct)%"><canvas id="bg"></canvas></div></div>
          <div class="note">Horizontal guides at 70 / 180 mg/dL. Squares = boluses (bottom axis). Triangles = user-entered carbs (hidden axis). Scroll horizontally — ~\(Int(targetDaysPerScreen)) days per viewport.</div>
        </div>

        <div class="panel">
          <h2>IOB</h2>
          <div class="scroll-x time-scroller"><div class="chart-wrap" style="width:\(widthPct)%"><canvas id="iob"></canvas></div></div>
          <div class="note">Active insulin on board (units), computed from annotated doses (net above basal schedule).</div>
        </div>

        <div class="panel">
          <h2>ICE and rolling ICE</h2>
          <div class="scroll-x time-scroller"><div class="chart-wrap" style="width:\(widthPct)%"><canvas id="ice"></canvas></div></div>
          <div class="note">Blue = raw ICE (v_cgm − v_insulin). Orange = rolling mean (\(Int(options.iceWindowMinutes)) min, centered). Dashed guides mark meal / exercise thresholds. Triangles = user-entered carbs.</div>
        </div>

        <div class="panel">
          <h2>local ISF over time, colored by class</h2>
          <div class="scroll-x time-scroller"><div class="chart-wrap-md" style="width:\(widthPct)%"><canvas id="ts"></canvas></div></div>
          <div class="note">Each dot is a 5-min sample. Neutral points (green) contribute to the baseline-ISF estimate. Meals (red) and exercise (blue) are excluded.</div>
        </div>

        <div class="panel">
          <h2>Diurnal pattern — ISF and ICE by local hour</h2>
          <div style="display:flex; gap:12px; flex-wrap:wrap;">
            <div style="flex:1; min-width:380px;">
              <div class="chart-wrap-sm"><canvas id="diurnalISF"></canvas></div>
              <div class="note">Green line = stable-subset (|rolling_ICE|≤0.3, ±30min) median local_ISF per hour. Gray line = all-sample median (heavily biased by meals). Bars = stable-sample count per hour. A dip in the green line in early-morning hours would indicate dawn-phenomenon sensitivity reduction.</div>
            </div>
            <div style="flex:1; min-width:380px;">
              <div class="chart-wrap-sm"><canvas id="diurnalICE"></canvas></div>
              <div class="note">Median rolling_ICE per hour. Positive bumps = typical meal hours (carbs pushing BG up more than insulin at that time). Zero-line marked. Helpful for identifying meal-time patterns.</div>
            </div>
          </div>
        </div>

        <div class="panel">
          <h2>Diurnal ISF — quantile regression (τ=\(String(format: "%.2f", diurnalTau)), 2-hour bins)</h2>
          <div style="display:flex; gap:12px; flex-wrap:wrap;">
            <div style="flex:1; min-width:420px;">
              <div class="chart-wrap-sm"><canvas id="diurnalQuantileISF"></canvas></div>
              <div class="note">
                Blue line = carb-robust ISF estimate per bin (slope of v_cgm vs activity at τ=\(String(format: "%.2f", diurnalTau))).
                Purple dashed line = clinician-configured (scheduled) ISF.
                Bars = pseudo-R² of the fit (taller = more confident slope).
              </div>
            </div>
            <div style="flex:1; min-width:420px;">
              <div class="chart-wrap-sm"><canvas id="diurnalQuantileC"></canvas></div>
              <div class="note">
                Orange line = median <code>v_cgm</code> (mg/dL/min) over the <b>stable-ICE subset</b> of the bin (|rolling_ICE| ≤ 0.30 for ±30 min). Stable-ICE windows have activity ≈ 0 and no meal/exercise action, so median v_cgm directly measures per-bin <b>basal/EGP mismatch</b>: <code>&gt; 0</code> = scheduled basal under-covers endogenous production (dawn signature), <code>&lt; 0</code> = basal over-covers. Zero line dashed. Bins with fewer than 10 stable samples are blank.
              </div>
            </div>
          </div>
          <div class="note">
            <b>Why the quantile ISF works:</b> carbs raise v_cgm but never lower it, so the lower envelope of v_cgm at any given activity level is (approximately) carb-free. τ=\(String(format: "%.2f", diurnalTau)) traces that envelope and gives an ISF that does not depend on carbs being announced, and does not drift with the ISF guess plugged into the insulin model.
            <br>
            <b>Slope vs. drift split:</b> Loop's <code>v_insulin</code> is computed relative to scheduled basal, so the two charts isolate distinct effects — <b>slope = ISF_true</b> (per-bin sensitivity), and <b>stable-ICE median v_cgm = basal minus EGP coverage</b> (per-bin drift not explained by insulin). Together they pinpoint whether a bad-BG hour is a sensitivity problem or a basal problem. The low-τ quantile <em>intercept</em> is not used here because it traces the lower edge of the noise cloud, not its centre.
            <br>
            <b>Look for:</b> a dawn-phenomenon ISF trough plus a positive drift spike in early-morning hours (cortisol raises insulin resistance AND EGP outpaces basal), lower ISF around typical meal hours (mixed signal: real resistance + residual carb contamination), and the evening sensitivity peak.
          </div>
        </div>

        <div class="panel">
          <h2>ISF estimate: v_cgm ~ activity regression · sweep over filter parameters</h2>
          <div style="display:flex; gap:12px; flex-wrap:wrap;">
            <div style="flex:1; min-width:380px;">
              <div class="chart-wrap-sm"><canvas id="sweepT"></canvas></div>
              <div class="note">Sweep over |rolling_ICE| threshold T, at fixed window ±30 min. Look for where the green ISF estimate stabilizes as T tightens.</div>
            </div>
            <div style="flex:1; min-width:380px;">
              <div class="chart-wrap-sm"><canvas id="sweepM"></canvas></div>
              <div class="note">Sweep over window half-width M, at fixed T=0.3 mg/dL/min. Longer M requires sustained stability (harder, fewer samples).</div>
            </div>
          </div>
        </div>

        <div class="panel">
          <h2>local ISF distribution — all vs neutral</h2>
          <div class="chart-wrap-sm"><canvas id="hist"></canvas></div>
          <div class="note">Bin width 10 mg/dL/U. Gray = all samples (unweighted). Green = neutral-only (unweighted). Look for whether the neutral distribution collapses to a tight mode that the all-samples distribution smears.</div>
        </div>

        <script>
        const ice = [\(iceJS)];
        const rolling = [\(rollingIceJS)];
        const meal = [\(mealJS)];
        const exercise = [\(exerciseJS)];
        const neutral = [\(neutralJS)];
        const doses = [\(doseJS)];
        const carbs = [\(carbJS)];
        const binMids = [\(binMidsJS)];
        const allCounts = [\(allCountsJS)];
        const allWt     = [\(allWtJS)];
        const neutCounts = [\(neutCountsJS)];
        const neutWt     = [\(neutWtJS)];

        const mealThr = \(mealThr);
        const exThr = \(exThr);

        const bg = [\(bgJS)];
        const iob = [\(iobJS)];
        const sun = [\(sunJS)];

        // Very faint daytime tint driven by sin(solar elevation).
        // Paints a horizontal linear gradient across the chart area so
        // afternoon/evening transitions render smoothly.
        function makeSunPlugin() {
          return {
            id: 'sunBg',
            beforeDatasetsDraw(chart) {
              if (!sun.length) return;
              const {ctx, chartArea: area, scales: {x}} = chart;
              if (!x || !area) return;
              const xMin = x.min, xMax = x.max;
              if (xMax <= xMin) return;
              const grad = ctx.createLinearGradient(area.left, 0, area.right, 0);
              let added = 0;
              // Effective horizon ~4° below true horizon — day appears
              // slightly wider than strict geometric sunrise/sunset.
              const horizonOffset = 0.08;
              for (let i = 0; i < sun.length; i++) {
                const [t, s] = sun[i];
                if (t < xMin || t > xMax) continue;
                const pos = Math.max(0, Math.min(1, (t - xMin) / (xMax - xMin)));
                const alpha = (Math.max(0, s + horizonOffset) * 0.10).toFixed(4);
                grad.addColorStop(pos, `rgba(255,220,130,${alpha})`);
                added++;
              }
              if (added < 2) return;
              ctx.save();
              ctx.fillStyle = grad;
              ctx.fillRect(area.left, area.top, area.right - area.left, area.bottom - area.top);
              ctx.restore();
            }
          };
        }

        // ── BG panel ──────────────────────────────────────────────────────────
        new Chart(document.getElementById('bg'), {
          type: 'line',
          data: {
            datasets: [
              {
                label: 'BG (smoothed)',
                data: bg, parsing: false,
                borderColor: 'rgba(220,220,220,0.9)',
                borderWidth: 1.5,
                pointRadius: 0, tension: 0,
              },
              {
                label: 'carbs',
                data: carbs.map(c => ({x:c.x, y:c.g})),
                parsing: false,
                pointStyle: 'triangle', pointRadius: 5,
                pointBackgroundColor: 'rgba(240,180,60,0.9)',
                pointBorderWidth: 0, showLine: false,
                yAxisID: 'yCarbs',
              },
              {
                label: 'boluses',
                data: doses.filter(d => d.k === 'B').map(d => ({x:d.x, y:d.v})),
                parsing: false,
                pointStyle: 'rectRot', pointRadius: 5,
                pointBackgroundColor: 'rgba(220,80,120,0.9)',
                pointBorderWidth: 0, showLine: false,
                yAxisID: 'yDoses',
              },
            ]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { labels: { color:'#bbb' } } },
            scales: {
              x: { type: 'time', ticks: { color:'#aaa' }, grid: { color:'#2d2d2d' } },
              y: {
                title: { display:true, text:'mg/dL', color:'#aaa' },
                min: 40, max: 400,
                ticks: { color:'#aaa' }, grid: { color:'#2d2d2d' }
              },
              yCarbs: { display: false, position: 'right', min: 0, max: 200 },
              yDoses: { display: false, position: 'right', min: 0, max: 20 },
            }
          },
          plugins: [makeSunPlugin(), {
            id: 'bgBands',
            afterDraw(chart) {
              const {ctx, chartArea: area, scales: {y}} = chart;
              ctx.save();
              ctx.strokeStyle = 'rgba(120,180,120,0.35)';
              ctx.setLineDash([4,3]);
              for (const v of [70, 180]) {
                ctx.beginPath();
                const yy = y.getPixelForValue(v);
                ctx.moveTo(area.left, yy); ctx.lineTo(area.right, yy); ctx.stroke();
              }
              ctx.restore();
            }
          }]
        });

        // ── IOB panel ─────────────────────────────────────────────────────────
        new Chart(document.getElementById('iob'), {
          type: 'line',
          data: {
            datasets: [{
              label: 'IOB (U)',
              data: iob, parsing: false,
              borderColor: 'rgba(160,200,240,0.9)',
              backgroundColor: 'rgba(160,200,240,0.15)',
              borderWidth: 1.5,
              fill: true,
              pointRadius: 0, tension: 0,
            }]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { labels: { color:'#bbb' } } },
            scales: {
              x: { type: 'time', ticks: { color:'#aaa' }, grid: { color:'#2d2d2d' } },
              y: {
                title: { display:true, text:'units', color:'#aaa' },
                ticks: { color:'#aaa' }, grid: { color:'#2d2d2d' }
              }
            }
          },
          plugins: [makeSunPlugin()]
        });

        // ── ICE panel ─────────────────────────────────────────────────────────
        new Chart(document.getElementById('ice'), {
          type: 'line',
          data: {
            datasets: [
              {
                label: 'ICE (raw)',
                data: ice, parsing: false,
                borderColor: 'rgba(120,160,200,0.35)',
                borderWidth: 1,
                pointRadius: 0, tension: 0,
              },
              {
                label: 'rolling ICE',
                data: rolling, parsing: false,
                borderColor: 'rgba(240,150,60,0.95)',
                borderWidth: 2,
                pointRadius: 0, tension: 0,
              },
              {
                label: 'carbs (×g)',
                data: carbs.map(c => ({x:c.x, y:c.g / 10})),  // scaled to ICE axis
                parsing: false,
                pointStyle: 'triangle',
                pointRadius: 5,
                pointBackgroundColor: 'rgba(240,180,60,0.9)',
                pointBorderWidth: 0,
                showLine: false,
              },
            ]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
              legend: { labels: { color:'#bbb' } },
              annotation: false
            },
            scales: {
              x: { type: 'time', ticks: { color:'#aaa' }, grid: { color:'#2d2d2d' } },
              y: {
                title: { display:true, text:'ICE (mg/dL/min) / carbs ÷10', color:'#aaa' },
                ticks: { color:'#aaa' },
                grid: { color:'#2d2d2d' },
              }
            }
          },
          plugins: [makeSunPlugin(), {
            id: 'thrBands',
            afterDraw(chart) {
              const {ctx, chartArea: area, scales: {y}} = chart;
              ctx.save();
              ctx.strokeStyle = 'rgba(231,111,81,0.6)';
              ctx.setLineDash([4,3]);
              ctx.beginPath();
              const yM = y.getPixelForValue(mealThr);
              ctx.moveTo(area.left, yM); ctx.lineTo(area.right, yM); ctx.stroke();
              ctx.strokeStyle = 'rgba(69,123,157,0.6)';
              ctx.beginPath();
              const yE = y.getPixelForValue(exThr);
              ctx.moveTo(area.left, yE); ctx.lineTo(area.right, yE); ctx.stroke();
              ctx.restore();
            }
          }]
        });

        // ── Time series (local ISF colored by class) ──────────────────────────
        new Chart(document.getElementById('ts'), {
          type: 'scatter',
          data: {
            datasets: [
              {
                label: 'neutral',
                data: neutral.map(s => ({x:s.x, y:s.y, w:s.w})),
                parsing: false,
                pointRadius: (ctx) => { const w = ctx.raw ? ctx.raw.w : 0; return 2 + Math.min(4, w*4); },
                pointBackgroundColor: 'rgba(106,153,78,0.85)',
                pointBorderWidth: 0, showLine: false,
              },
              {
                label: 'meal',
                data: meal.map(s => ({x:s.x, y:s.y, w:s.w})),
                parsing: false,
                pointRadius: (ctx) => { const w = ctx.raw ? ctx.raw.w : 0; return 2 + Math.min(4, w*4); },
                pointBackgroundColor: 'rgba(231,111,81,0.85)',
                pointBorderWidth: 0, showLine: false,
              },
              {
                label: 'exercise',
                data: exercise.map(s => ({x:s.x, y:s.y, w:s.w})),
                parsing: false,
                pointRadius: (ctx) => { const w = ctx.raw ? ctx.raw.w : 0; return 2 + Math.min(4, w*4); },
                pointBackgroundColor: 'rgba(69,123,157,0.85)',
                pointBorderWidth: 0, showLine: false,
              },
              {
                label: 'carbs (×20 g scale)',
                data: carbs.map(c => ({x:c.x, y:c.g})),
                parsing: false,
                pointStyle: 'triangle', pointRadius: 5,
                pointBackgroundColor: 'rgba(240,180,60,0.9)',
                pointBorderWidth: 0, showLine: false,
                yAxisID: 'yCarbs',
              },
            ]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'nearest', intersect: false },
            plugins: {
              legend: { labels: { color:'#bbb' } },
            },
            scales: {
              x: { type: 'time', ticks: { color:'#aaa' }, grid: { color:'#2d2d2d' } },
              y: {
                title: { display:true, text:'local ISF (mg/dL/U)', color:'#aaa' },
                ticks: { color:'#aaa' }, grid: { color:'#2d2d2d' }
              },
              yCarbs: { display: false, position: 'right', min: 0, max: 200 },
            }
          },
          plugins: [makeSunPlugin()]
        });

        // ── Diurnal charts ────────────────────────────────────────────────────
        const diurnal = [\(diurnalJS)];
        const hourLabels = diurnal.map(d => String(d.h).padStart(2,'0'));

        new Chart(document.getElementById('diurnalISF'), {
          data: {
            labels: hourLabels,
            datasets: [
              {
                type: 'bar',
                label: 'stable-sample count',
                data: diurnal.map(d => d.sn),
                backgroundColor: 'rgba(140,140,140,0.35)',
                yAxisID: 'yCount',
                order: 2,
              },
              {
                type: 'line',
                label: 'all-sample median ISF',
                data: diurnal.map(d => d.isf),
                borderColor: 'rgba(180,180,180,0.6)',
                borderDash: [4,3],
                borderWidth: 1.5,
                pointRadius: 0,
                spanGaps: false,
                yAxisID: 'yISF',
                order: 1,
              },
              {
                type: 'line',
                label: 'stable-subset median ISF',
                data: diurnal.map(d => d.sisf),
                borderColor: 'rgba(106,153,78,0.95)',
                backgroundColor: 'rgba(106,153,78,0.2)',
                borderWidth: 2,
                pointRadius: 3,
                spanGaps: false,
                yAxisID: 'yISF',
                order: 0,
              },
            ]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { labels: { color:'#bbb' } } },
            scales: {
              x: {
                title: { display:true, text:'local hour', color:'#aaa' },
                ticks: { color:'#aaa' },
                grid: { color:'#2d2d2d' },
              },
              yISF: {
                position: 'left',
                title: { display:true, text:'median local ISF (mg/dL/U)', color:'#aaa' },
                ticks: { color:'#aaa' }, grid: { color:'#2d2d2d' },
              },
              yCount: {
                position: 'right',
                title: { display:true, text:'count', color:'#aaa' },
                ticks: { color:'#aaa' }, grid: { drawOnChartArea: false },
                beginAtZero: true,
              }
            }
          }
        });

        new Chart(document.getElementById('diurnalICE'), {
          data: {
            labels: hourLabels,
            datasets: [
              {
                type: 'bar',
                label: 'all-sample count',
                data: diurnal.map(d => d.n),
                backgroundColor: 'rgba(140,140,140,0.35)',
                yAxisID: 'yCount',
                order: 2,
              },
              {
                type: 'line',
                label: 'median rolling_ICE',
                data: diurnal.map(d => d.ice),
                borderColor: 'rgba(230,130,70,0.95)',
                borderWidth: 2,
                pointRadius: 3,
                spanGaps: false,
                yAxisID: 'yICE',
                order: 1,
              },
            ]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { labels: { color:'#bbb' } } },
            scales: {
              x: {
                title: { display:true, text:'local hour', color:'#aaa' },
                ticks: { color:'#aaa' },
                grid: { color:'#2d2d2d' },
              },
              yICE: {
                position: 'left',
                title: { display:true, text:'median rolling_ICE (mg/dL/min)', color:'#aaa' },
                ticks: { color:'#aaa' }, grid: { color:'#2d2d2d' },
              },
              yCount: {
                position: 'right',
                title: { display:true, text:'count', color:'#aaa' },
                ticks: { color:'#aaa' }, grid: { drawOnChartArea: false },
                beginAtZero: true,
              }
            }
          },
          plugins: [{
            id: 'iceZero',
            afterDraw(chart) {
              const {ctx, chartArea: area, scales: {yICE}} = chart;
              const y0 = yICE.getPixelForValue(0);
              ctx.save();
              ctx.strokeStyle = 'rgba(255,255,255,0.2)';
              ctx.setLineDash([3,3]);
              ctx.beginPath(); ctx.moveTo(area.left, y0); ctx.lineTo(area.right, y0); ctx.stroke();
              ctx.restore();
            }
          }]
        });

        // ── Diurnal quantile-regression ISF chart ─────────────────────────────
        const dqData = [\(diurnalQuantileJS)];
        const dqLabels = dqData.map(d => {
          const s = String(d.s).padStart(2,'0');
          const e = String(d.e).padStart(2,'0');
          return `${s}–${e}`;
        });

        new Chart(document.getElementById('diurnalQuantileISF'), {
          data: {
            labels: dqLabels,
            datasets: [
              {
                type: 'bar',
                label: 'pseudo-R² (×1000)',
                data: dqData.map(d => d.r2 == null ? null : d.r2 * 1000),
                backgroundColor: 'rgba(140,140,140,0.35)',
                yAxisID: 'yR2',
                order: 3,
              },
              {
                type: 'line',
                label: 'scheduled ISF (NS)',
                data: dqData.map(d => d.sched),
                borderColor: 'rgba(185,140,215,0.85)',
                borderDash: [5,4],
                borderWidth: 1.5,
                pointRadius: 2,
                spanGaps: false,
                yAxisID: 'yISF',
                order: 2,
              },
              {
                type: 'line',
                label: `quantile ISF (τ=\(String(format: "%.2f", diurnalTau)))`,
                data: dqData.map(d => d.isf),
                borderColor: 'rgba(90,160,230,0.95)',
                backgroundColor: 'rgba(90,160,230,0.2)',
                borderWidth: 2.5,
                pointRadius: 4,
                spanGaps: false,
                yAxisID: 'yISF',
                order: 1,
              },
            ]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
              legend: { labels: { color:'#bbb' } },
              tooltip: {
                callbacks: {
                  afterLabel: function(ctx) {
                    const d = dqData[ctx.dataIndex];
                    if (!d) return '';
                    const r2Str = d.r2 == null ? '—' : d.r2.toFixed(3);
                    const isfStr = d.isf == null ? '—' : d.isf.toFixed(1);
                    const schedStr = d.sched == null ? '—' : d.sched.toFixed(1);
                    const mStr = d.m == null ? '—' : d.m.toFixed(3);
                    return `n=${d.n}  pseudoR²=${r2Str}\\nquantile ISF=${isfStr}  sched=${schedStr}\\nstable v_cgm median=${mStr} mg/dL/min  (n_stable=${d.sn})`;
                  }
                }
              }
            },
            scales: {
              x: {
                title: { display:true, text:'local hour bin', color:'#aaa' },
                ticks: { color:'#aaa' },
                grid: { color:'#2d2d2d' },
              },
              yISF: {
                position: 'left',
                title: { display:true, text:'ISF (mg/dL/U)', color:'#aaa' },
                ticks: { color:'#aaa' }, grid: { color:'#2d2d2d' },
                beginAtZero: true,
              },
              yR2: {
                position: 'right',
                title: { display:true, text:'pseudo-R² × 1000', color:'#aaa' },
                ticks: { color:'#aaa' }, grid: { drawOnChartArea: false },
                beginAtZero: true,
              }
            }
          }
        });

        // ── Diurnal stable-ICE median v_cgm (basal-vs-EGP mismatch) ───────────
        new Chart(document.getElementById('diurnalQuantileC'), {
          data: {
            labels: dqLabels,
            datasets: [
              {
                type: 'bar',
                label: 'stable-ICE sample count',
                data: dqData.map(d => d.sn),
                backgroundColor: 'rgba(140,140,140,0.35)',
                yAxisID: 'ySN',
                order: 2,
              },
              {
                type: 'line',
                label: 'stable v_cgm median (mg/dL/min)',
                data: dqData.map(d => d.m),
                borderColor: 'rgba(232,150,70,0.95)',
                backgroundColor: 'rgba(232,150,70,0.2)',
                borderWidth: 2.5,
                pointRadius: 4,
                spanGaps: false,
                yAxisID: 'yV',
                order: 1,
              },
            ]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
              legend: { labels: { color:'#bbb' } },
              tooltip: {
                callbacks: {
                  afterLabel: function(ctx) {
                    const d = dqData[ctx.dataIndex];
                    if (!d) return '';
                    const mStr = d.m == null ? '—' : d.m.toFixed(3);
                    const isfStr = d.isf == null ? '—' : d.isf.toFixed(1);
                    return `stable v_cgm median=${mStr} mg/dL/min  (n_stable=${d.sn})\\nquantile ISF=${isfStr} mg/dL/U`;
                  }
                }
              }
            },
            scales: {
              x: {
                title: { display:true, text:'local hour bin', color:'#aaa' },
                ticks: { color:'#aaa' },
                grid: { color:'#2d2d2d' },
              },
              yV: {
                position: 'left',
                title: { display:true, text:'stable v_cgm median (mg/dL/min)', color:'#aaa' },
                ticks: { color:'#aaa' }, grid: { color:'#2d2d2d' },
              },
              ySN: {
                position: 'right',
                title: { display:true, text:'stable sample count', color:'#aaa' },
                ticks: { color:'#aaa' }, grid: { drawOnChartArea: false },
                beginAtZero: true,
              }
            }
          },
          plugins: [{
            id: 'cZero',
            afterDraw(chart) {
              const {ctx, chartArea: area, scales: {yV}} = chart;
              const y0 = yV.getPixelForValue(0);
              ctx.save();
              ctx.strokeStyle = 'rgba(255,255,255,0.25)';
              ctx.setLineDash([3,3]);
              ctx.beginPath(); ctx.moveTo(area.left, y0); ctx.lineTo(area.right, y0); ctx.stroke();
              ctx.restore();
            }
          }]
        });

        // ── Stable-ICE regression sweeps ──────────────────────────────────────
        const sweepT = [\(sweepTData)];
        const sweepM = [\(sweepMData)];

        function sweepChart(canvasId, data, xTitle) {
          new Chart(document.getElementById(canvasId), {
            data: {
              datasets: [
                {
                  type: 'bar',
                  label: 'sample count',
                  data: data.map(d => ({x: d.x, y: d.n})),
                  backgroundColor: 'rgba(140,140,140,0.35)',
                  yAxisID: 'yCount',
                  order: 2,
                  parsing: false,
                },
                {
                  type: 'line',
                  label: 'ISF estimate (slope)',
                  data: data.map(d => ({x: d.x, y: d.isf, r2: d.r2, n: d.n})),
                  borderColor: 'rgba(106,153,78,0.95)',
                  backgroundColor: 'rgba(106,153,78,0.2)',
                  borderWidth: 2,
                  pointRadius: 4,
                  yAxisID: 'yISF',
                  order: 1,
                  parsing: false,
                },
              ]
            },
            options: {
              responsive: true, maintainAspectRatio: false,
              plugins: {
                legend: { labels: { color:'#bbb' } },
                tooltip: {
                  callbacks: {
                    label: (ctx) => {
                      const r = ctx.raw;
                      if (ctx.dataset.label === 'ISF estimate (slope)') {
                        return `ISF=${r.y.toFixed(1)}  n=${r.n}  R²=${r.r2.toFixed(3)}`;
                      }
                      return `n=${r.y}`;
                    }
                  }
                }
              },
              scales: {
                x: {
                  type: 'linear',
                  title: { display:true, text: xTitle, color:'#aaa' },
                  ticks: { color:'#aaa' },
                  grid: { color:'#2d2d2d' },
                },
                yISF: {
                  position: 'left',
                  title: { display:true, text:'ISF estimate (mg/dL/U)', color:'#aaa' },
                  ticks: { color:'#aaa' }, grid: { color:'#2d2d2d' },
                },
                yCount: {
                  position: 'right',
                  title: { display:true, text:'n samples', color:'#aaa' },
                  ticks: { color:'#aaa' }, grid: { drawOnChartArea: false },
                  beginAtZero: true,
                }
              }
            }
          });
        }
        sweepChart('sweepT', sweepT, 'threshold T (mg/dL/min)');
        sweepChart('sweepM', sweepM, 'window half-width M (min)');

        // ── Histogram ─────────────────────────────────────────────────────────
        new Chart(document.getElementById('hist'), {
          type: 'bar',
          data: {
            labels: binMids,
            datasets: [
              {
                label: 'all samples',
                data: allCounts,
                backgroundColor: 'rgba(180,180,180,0.5)',
              },
              {
                label: 'neutral only',
                data: neutCounts,
                backgroundColor: 'rgba(106,153,78,0.85)',
              },
            ]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { labels: { color:'#bbb' } } },
            scales: {
              x: {
                stacked: false,
                title: { display:true, text:'local ISF bin (mg/dL/U)', color:'#aaa' },
                ticks: { color:'#aaa' }, grid: { color:'#2d2d2d' },
              },
              y: {
                title: { display:true, text:'count', color:'#aaa' },
                ticks: { color:'#aaa' }, grid: { color:'#2d2d2d' },
              }
            }
          }
        });
        // Sync horizontal scrolling across all time-series charts so they
        // stay time-aligned as the user scrolls.
        (() => {
          const scrollers = Array.from(document.querySelectorAll('.time-scroller'));
          if (scrollers.length < 2) return;
          let syncing = false;
          scrollers.forEach(el => {
            el.addEventListener('scroll', () => {
              if (syncing) return;
              syncing = true;
              for (const other of scrollers) {
                if (other !== el) other.scrollLeft = el.scrollLeft;
              }
              requestAnimationFrame(() => { syncing = false; });
            }, { passive: true });
          });
        })();
        </script>
        </body>
        </html>
        """
    }

    // MARK: - Helpers

    private static func card(_ k: String, _ v: String, _ accent: String) -> String {
        "<div class=\"card\" style=\"border-left-color:\(accent)\"><div class=\"k\">\(k)</div><div class=\"v\">\(v)</div></div>"
    }

    private static func histogram(
        values: [Double],
        weights: [Double],
        binWidth: Double
    ) -> ([Double], [Int], [Double]) {
        guard let vMin = values.min(), let vMax = values.max() else {
            return ([], [], [])
        }
        let loEdge = (floor(vMin / binWidth)) * binWidth
        let hiEdge = (ceil(vMax / binWidth)) * binWidth
        let nBins = max(1, Int(((hiEdge - loEdge) / binWidth).rounded()))
        var edges: [Double] = []
        edges.reserveCapacity(nBins + 1)
        for i in 0...nBins {
            edges.append(loEdge + Double(i) * binWidth)
        }
        var counts = [Int](repeating: 0, count: nBins)
        var weightSums = [Double](repeating: 0, count: nBins)
        for (v, w) in zip(values, weights) {
            var idx = Int((v - loEdge) / binWidth)
            if idx < 0 { idx = 0 }
            if idx >= nBins { idx = nBins - 1 }
            counts[idx] += 1
            weightSums[idx] += w
        }
        return (edges, counts, weightSums)
    }

    // MARK: - Sun elevation

    /// sin(solar elevation) at each uniformly-spaced time step, using the
    /// NOAA Solar Position Algorithm approximation. Below-horizon values
    /// are left negative; consumers clamp to max(0, …) for rendering.
    static func sunElevationSeries(
        from start: Date,
        to end: Date,
        stride: TimeInterval,
        latitudeDeg: Double,
        longitudeDeg: Double
    ) -> [(t: Date, sinElev: Double)] {
        let phi = latitudeDeg * .pi / 180
        let sinPhi = sin(phi)
        let cosPhi = cos(phi)

        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "UTC")!

        var out: [(Date, Double)] = []
        var t = start
        while t <= end {
            // Day-of-year and fractional-day γ (radians). `dayOfYear` is
            // macOS 15+, so derive via `ordinality(of:in:for:)`.
            let doy = Double(cal.ordinality(of: .day, in: .year, for: t) ?? 1)
            let hourUTC = Double(cal.component(.hour, from: t))
            let minuteUTC = Double(cal.component(.minute, from: t))
            let secondUTC = Double(cal.component(.second, from: t))
            let fracHour = hourUTC + minuteUTC / 60 + secondUTC / 3600

            let gamma = 2 * .pi / 365 * (doy - 1 + (fracHour - 12) / 24)
            // Declination (radians).
            let decl =
                0.006918
                - 0.399912 * cos(gamma)
                + 0.070257 * sin(gamma)
                - 0.006758 * cos(2 * gamma)
                + 0.000907 * sin(2 * gamma)
                - 0.002697 * cos(3 * gamma)
                + 0.001480 * sin(3 * gamma)

            // Equation of time (minutes).
            let eqTime = 229.18 * (
                0.000075
                + 0.001868 * cos(gamma)
                - 0.032077 * sin(gamma)
                - 0.014615 * cos(2 * gamma)
                - 0.040849 * sin(2 * gamma)
            )

            // True solar time (minutes past local solar midnight).
            let trueSolarMin = fracHour * 60 + eqTime + 4 * longitudeDeg
            // Hour angle (radians): negative in morning, zero at solar noon.
            let hourAngle = (trueSolarMin / 4 - 180) * .pi / 180

            let sinH = sinPhi * sin(decl) + cosPhi * cos(decl) * cos(hourAngle)
            out.append((t, sinH))

            t = t.addingTimeInterval(stride)
        }
        return out
    }

    private static func alignHistogram(
        values: [Double], weights: [Double], edges: [Double]
    ) -> (counts: [Int], weighted: [Double]) {
        let nBins = max(0, edges.count - 1)
        var counts = [Int](repeating: 0, count: nBins)
        var weighted = [Double](repeating: 0, count: nBins)
        guard nBins > 0 else { return (counts, weighted) }
        let lo = edges.first!
        let binWidth = (edges.last! - lo) / Double(nBins)
        for (v, w) in zip(values, weights) {
            var idx = Int((v - lo) / binWidth)
            if idx < 0 { idx = 0 }
            if idx >= nBins { idx = nBins - 1 }
            counts[idx] += 1
            weighted[idx] += w
        }
        return (counts, weighted)
    }
}
