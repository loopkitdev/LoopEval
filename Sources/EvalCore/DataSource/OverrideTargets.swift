// OverrideTargets.swift — fill override correction RANGES (and multiplier) from
// devicestatus, for named-preset overrides whose range is absent from the NS
// treatment (targetTop/targetBottom = null; see runs/2026-06-19-divergence).
//
// The reconstruction (analysis/loopeval_analysis/override_targets.py) reads the
// deployed Loop's per-cycle devicestatus `override.currentCorrectionRange` and
// emits time windows. This module replaces the therapy timeline's override
// windows with these devicestatus-sourced ones (authoritative: the range +
// multiplier Loop actually used), so hands-on decision-time replay / sim dose to
// the target Loop had — not the un-overridden scheduled target.

import Foundation
import LoopAlgorithm

struct OverrideTargetsFile: Decodable {
    let version: Int?
    let windows: [Spec]

    struct Spec: Decodable {
        let start: String
        let end: String
        let minValue: Double
        let maxValue: Double
        let multiplier: Double?
        let name: String?
        let indefinite: Bool?
    }
}

enum OverrideTargets {

    private static func parseISO(_ s: String) -> Date? {
        let withFrac = ISO8601DateFormatter()
        withFrac.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let d = withFrac.date(from: s) { return d }
        let noFrac = ISO8601DateFormatter()
        noFrac.formatOptions = [.withInternetDateTime]
        return noFrac.date(from: s)
    }

    /// REPLACE the timeline's override windows with the devicestatus-derived ones —
    /// the decision-time-faithful source for override range, multiplier, active span,
    /// and the indefinite flag. The NS treatment's `duration` is unreliable (Loop
    /// back-fills it to the realized cancel time, leaking the future end into earlier
    /// forecasts), and named presets carry their range only in devicestatus. Windows
    /// flagged `indefinite` are extended across each decision's forecast horizon by
    /// InputWindowBuilder (no revert at the realized end). Ensures the raw (un-override)
    /// schedules are populated so the override machinery engages. No-op if the file is
    /// missing/empty.
    static func applyFile(
        path: String,
        to timeline: TherapyTimeline,
        onWarning: ((String) -> Void)? = nil
    ) -> TherapyTimeline {
        guard let data = try? Data(contentsOf: URL(fileURLWithPath: path)),
              let file = try? JSONDecoder().decode(OverrideTargetsFile.self, from: data) else {
            onWarning?("override-targets: could not read \(path)")
            return timeline
        }
        let wins: [OverrideWindow] = file.windows.compactMap { s in
            guard let start = parseISO(s.start), let end = parseISO(s.end), end > start else { return nil }
            // devicestatus `multiplier` == Loop insulinNeedsScaleFactor; 1.0/nil ⇒
            // target-only (no insulin scaling).
            let factor: Double? = s.multiplier.flatMap { abs($0 - 1.0) > 1e-9 ? $0 : nil }
            return OverrideWindow(start: start, end: end, factor: factor,
                                  targetLo: s.minValue, targetHi: s.maxValue,
                                  indefinite: s.indefinite ?? false)
        }
        guard !wins.isEmpty else { return timeline }

        var tl = timeline
        // The override machinery applies windows to the RAW (un-override) schedules; seed
        // them from the baked schedules when no treatment-based override was applied.
        if tl.rawBasal.isEmpty       { tl.rawBasal = tl.basal }
        if tl.rawSensitivity.isEmpty { tl.rawSensitivity = tl.sensitivity }
        if tl.rawCarbRatio.isEmpty   { tl.rawCarbRatio = tl.carbRatio }
        if tl.rawTarget.isEmpty      { tl.rawTarget = tl.target }
        tl.overrideWindows = wins.sorted { $0.start < $1.start }
        let nIndef = wins.filter { $0.indefinite }.count
        onWarning?("override-targets: replaced override windows with \(wins.count) devicestatus windows (\(nIndef) indefinite)")
        return tl
    }
}
