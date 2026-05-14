// RiskScoreModel.swift — inline computation of hypo-risk score for use in
// closed-loop simulation's smooth-boost ISF mechanism.
//
// V2: trained with L1 lookback-sweep — 14 features from a 21-feature pool,
// C=0.1 sklearn LogisticRegression. Test ROC-AUC = 0.751 on held-out last
// 40% (vs 0.685 for the original 10-feature model). Trained on RAW features
// (no Kalman smoothing) to match Swift inference.
//
// Feature order (must match coefs[] index by index):
//   0  f_bg_now
//   1  f_iob_now
//   2  f_v_cgm
//   3  f_peak_iob_30m
//   4  f_peak_iob_90m
//   5  f_recent_insulin_15  (mean |v_insulin| over past 15 min)
//   6  f_recent_insulin_60  (mean |v_insulin| over past 60 min)
//   7  f_ice_w5             (5-min trailing mean ICE)
//   8  f_ice_w30            (30-min trailing mean ICE)
//   9  f_ice_w60            (60-min trailing mean ICE)
//   10 f_ice_trend_30       (Δ(ice_w30) over past 15 min)
//   11 f_ice_trend_60       (Δ(ice_w60) over past 30 min)
//   12 f_ice_trend_120      (Δ(ice_w120) over past 60 min)
//   13 f_hour_sin

import Foundation
import LoopAlgorithm

public struct RiskScoreModel {

    public static let coefs: [Double] = [
        -1.064127,  // f_bg_now
        +0.658522,  // f_iob_now
        +1.815703,  // f_v_cgm
        +0.802401,  // f_peak_iob_30m
        -0.463566,  // f_peak_iob_90m
        +1.342452,  // f_recent_insulin_15
        -0.139137,  // f_recent_insulin_60
        -1.935877,  // f_ice_w5
        -0.310166,  // f_ice_w30
        +0.144545,  // f_ice_w60
        -0.016349,  // f_ice_trend_30
        +0.405338,  // f_ice_trend_60
        -0.574241,  // f_ice_trend_120
        -0.042404,  // f_hour_sin
    ]
    public static let bias: Double = -0.307631

    public static let mu: [Double] = [
        203.349622, 2.074992, -0.119438, 2.419012, 3.000584,
        1.172127, 1.147938, 1.015541, 0.999169, 0.980855,
        0.019621, 0.038543, 0.059131, -0.014695,
    ]

    public static let sigma: [Double] = [
        80.849847, 1.799035, 1.673349, 1.899735, 2.016011,
        0.817264, 0.794574, 1.692798, 1.195256, 1.032688,
        0.805112, 0.732691, 0.653550, 0.702243,
    ]

    public static func score(features: [Double]) -> Double {
        precondition(features.count == coefs.count,
                     "RiskScoreModel.score: feature count mismatch (\(features.count) vs \(coefs.count))")
        var z = bias
        for i in 0..<features.count {
            let s = sigma[i] > 1e-12 ? sigma[i] : 1.0
            z += coefs[i] * (features[i] - mu[i]) / s
        }
        let clamped = max(-50.0, min(50.0, z))
        return 1.0 / (1.0 + exp(-clamped))
    }

    public static func features(
        at t: Date,
        glucose: [EvalGlucoseSample],
        glucoseMgdl: [Double],
        prediction: LoopPrediction<EvalCarbEntry>,
        currentIOB: Double,
        pastIOBs: [(Date, Double)] = [],
        localTimezone: TimeZone
    ) -> [Double]? {
        let mgdlUnit = LoopUnit.milligramsPerDeciliter
        let mgdlPerMinUnit = LoopUnit.milligramsPerDeciliterPerMinute

        guard !glucose.isEmpty else { return nil }
        var nowIdx = 0
        for i in 0..<glucose.count {
            if glucose[i].startDate <= t { nowIdx = i } else { break }
        }
        guard glucose[nowIdx].startDate >= t.addingTimeInterval(-15 * 60) else {
            return nil
        }
        let bgNow = glucoseMgdl[nowIdx]

        // f_v_cgm
        var vCgm = 0.0
        if nowIdx >= 1 {
            let dt = glucose[nowIdx].startDate.timeIntervalSince(glucose[nowIdx-1].startDate) / 60.0
            if dt > 1e-6 { vCgm = (glucoseMgdl[nowIdx] - glucoseMgdl[nowIdx-1]) / dt }
        }

        // f_peak_iob_30m and f_peak_iob_90m — rolling max over past N min from pastIOBs
        let win30Start = t.addingTimeInterval(-30 * 60)
        let win90Start = t.addingTimeInterval(-90 * 60)
        var peakIob30 = currentIOB
        var peakIob90 = currentIOB
        if !pastIOBs.isEmpty {
            for (sampleT, iob) in pastIOBs.reversed() {
                if sampleT < win90Start { break }
                if sampleT > t { continue }
                if iob > peakIob90 { peakIob90 = iob }
                if sampleT >= win30Start && iob > peakIob30 { peakIob30 = iob }
            }
        }

        // f_recent_insulin — mean |v_insulin| over past windows
        let insulinEffects = prediction.effects.insulin
        func meanAbsVInsulin(windowMin: Double) -> Double {
            let windowStart = t.addingTimeInterval(-windowMin * 60)
            let win = insulinEffects.filter { $0.startDate <= t && $0.startDate >= windowStart }
            var sum = 0.0; var n = 0
            for k in 0..<(win.count - 1) {
                let dy = win[k+1].quantity.doubleValue(for: mgdlUnit) -
                         win[k].quantity.doubleValue(for: mgdlUnit)
                let dt = win[k+1].startDate.timeIntervalSince(win[k].startDate) / 60.0
                if dt > 1e-6 { sum += abs(dy / dt); n += 1 }
            }
            return n > 0 ? sum / Double(n) : 0.0
        }
        let recentIns15 = meanAbsVInsulin(windowMin: 15)
        let recentIns60 = meanAbsVInsulin(windowMin: 60)

        // f_ice_wN — N-min trailing mean of insulinCounteraction
        let iceEffects = prediction.effects.insulinCounteraction
        func meanICE(windowMin: Double) -> Double {
            let windowStart = t.addingTimeInterval(-windowMin * 60)
            let win = iceEffects.filter { $0.endDate <= t && $0.startDate >= windowStart }
            guard !win.isEmpty else { return 0.0 }
            var sum = 0.0
            for e in win { sum += e.quantity.doubleValue(for: mgdlPerMinUnit) }
            return sum / Double(win.count)
        }
        let iceW5 = meanICE(windowMin: 5)
        let iceW30 = meanICE(windowMin: 30)
        let iceW60 = meanICE(windowMin: 60)

        // f_ice_trend — Δ(ice_wN) over past (N/2) min
        // ice_trend_N = mean ice in [t-N, t] − mean ice in [t-N-N/2, t-N/2]
        func iceTrend(windowMin: Double) -> Double {
            let half = windowMin / 2
            let now = meanICE(windowMin: windowMin)
            let prevWindowStart = t.addingTimeInterval(-(windowMin + half) * 60)
            let prevWindowEnd   = t.addingTimeInterval(-half * 60)
            let prev = iceEffects.filter { $0.endDate <= prevWindowEnd && $0.startDate >= prevWindowStart }
            guard !prev.isEmpty else { return 0.0 }
            var sum = 0.0
            for e in prev { sum += e.quantity.doubleValue(for: mgdlPerMinUnit) }
            return now - (sum / Double(prev.count))
        }
        let iceTrend30  = iceTrend(windowMin: 30)
        let iceTrend60  = iceTrend(windowMin: 60)
        let iceTrend120 = iceTrend(windowMin: 120)

        // f_hour_sin (note: hour_cos was dropped by L1)
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = localTimezone
        let comps = cal.dateComponents([.hour, .minute], from: t)
        let hour = Double(comps.hour ?? 0) + Double(comps.minute ?? 0) / 60.0
        let hourSin = sin(2 * .pi * hour / 24.0)

        return [
            bgNow, currentIOB, vCgm,
            peakIob30, peakIob90,
            recentIns15, recentIns60,
            iceW5, iceW30, iceW60,
            iceTrend30, iceTrend60, iceTrend120,
            hourSin,
        ]
    }
}
