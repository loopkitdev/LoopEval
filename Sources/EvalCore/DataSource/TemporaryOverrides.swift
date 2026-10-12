// TemporaryOverrides.swift — apply Loop Temporary Overrides to the therapy timeline.
//
// Loop's TemporaryScheduleOverride scales insulin needs over a window:
//   basal × f, ISF ÷ f, carbRatio ÷ f  (f = insulinNeedsScaleFactor; f<1 = less insulin)
// and replaces the correction (target) range with the override's range.
// f may be nil (a target-only override → no insulin scaling). A new override
// supersedes the prior one (we clip each window's end to the next window's start).

import Foundation
import LoopAlgorithm

public struct OverrideWindow: Sendable, Codable {
    public let start: Date
    public let end: Date            // realized end (active→inactive transition / scheduled end)
    public let factor: Double?     // insulinNeedsScaleFactor; nil = no insulin scaling
    public let targetLo: Double?   // mg/dL
    public let targetHi: Double?
    /// True ⇒ the override had NO scheduled end at decision time (devicestatus omitted
    /// `duration`). `end` is the realized cancel, which Loop didn't know in advance — so a
    /// decision BEFORE `end` must extend the override across its forecast horizon (no
    /// revert at `end`). InputWindowBuilder extends indefinite windows per decision time.
    public let indefinite: Bool
    /// An EDITED override: every version shares `revisionKey` and spans the whole override
    /// [start, end]; `visibleFrom` is when the version was saved. Loop keeps the original
    /// start date on an edit, and recording it deletes the previous version outright
    /// (TemporaryScheduleOverrideHistory.record -> deleteEventsStartingOnOrAfter), so from
    /// the edit on, the new settings cover the override's past as well — the net-basal
    /// reference and dose-time ISF of insulin already given. A decision at t uses the
    /// latest version with visibleFrom <= t (see `resolved(_:at:)`). nil = not edited.
    public let revisionKey: String?
    public let visibleFrom: Date?

    public init(start: Date, end: Date, factor: Double?, targetLo: Double?, targetHi: Double?, indefinite: Bool = false,
                revisionKey: String? = nil, visibleFrom: Date? = nil) {
        self.start = start; self.end = end
        self.factor = factor; self.targetLo = targetLo; self.targetHi = targetHi
        self.indefinite = indefinite
        self.revisionKey = revisionKey; self.visibleFrom = visibleFrom
    }

    private enum CodingKeys: String, CodingKey { case start, end, factor, targetLo, targetHi, indefinite, revisionKey, visibleFrom }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        start = try c.decode(Date.self, forKey: .start)
        end = try c.decode(Date.self, forKey: .end)
        factor = try c.decodeIfPresent(Double.self, forKey: .factor)
        targetLo = try c.decodeIfPresent(Double.self, forKey: .targetLo)
        targetHi = try c.decodeIfPresent(Double.self, forKey: .targetHi)
        indefinite = (try? c.decodeIfPresent(Bool.self, forKey: .indefinite)) ?? false
        revisionKey = try c.decodeIfPresent(String.self, forKey: .revisionKey)
        visibleFrom = try c.decodeIfPresent(Date.self, forKey: .visibleFrom)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(start, forKey: .start)
        try c.encode(end, forKey: .end)
        try c.encodeIfPresent(factor, forKey: .factor)
        try c.encodeIfPresent(targetLo, forKey: .targetLo)
        try c.encodeIfPresent(targetHi, forKey: .targetHi)
        try c.encode(indefinite, forKey: .indefinite)
        try c.encodeIfPresent(revisionKey, forKey: .revisionKey)
        try c.encodeIfPresent(visibleFrom, forKey: .visibleFrom)
    }

    /// The windows as the deployed Loop held them at decision time `t`: a version saved after
    /// `t` is invisible, and of an edited override's visible versions only the latest stands.
    /// No-op (returns `ws`) when nothing is edited.
    public static func resolved(_ ws: [OverrideWindow], at t: Date) -> [OverrideWindow] {
        guard ws.contains(where: { $0.revisionKey != nil }) else { return ws }
        var latest: [String: OverrideWindow] = [:]
        var out: [OverrideWindow] = []
        for w in ws {
            guard let key = w.revisionKey else { out.append(w); continue }
            let vis = w.visibleFrom ?? w.start
            guard vis <= t else { continue }
            if let cur = latest[key], (cur.visibleFrom ?? cur.start) >= vis { continue }
            latest[key] = w
        }
        return (out + latest.values).sorted { $0.start < $1.start }
    }
}

public enum TemporaryOverrides {
    /// Build non-overlapping override windows from "Temporary Override" treatments.
    static func windows(from treatments: [NightscoutTreatment], parse: (String) -> Date?) -> [OverrideWindow] {
        var ws: [OverrideWindow] = []
        for t in treatments where t.eventType.trimmingCharacters(in: .whitespaces) == "Temporary Override" {
            guard let start = parse(t.created_at), let dur = t.duration, dur > 0 else { continue }
            let cr = (t.correctionRange?.count == 2) ? t.correctionRange : nil
            ws.append(OverrideWindow(start: start, end: start.addingTimeInterval(dur * 60),
                                     factor: t.insulinNeedsScaleFactor,
                                     targetLo: cr?[0], targetHi: cr?[1]))
        }
        ws.sort { $0.start < $1.start }
        var out: [OverrideWindow] = []
        for (i, w) in ws.enumerated() {
            var end = w.end
            if i + 1 < ws.count, ws[i + 1].start < end { end = ws[i + 1].start }   // supersession
            if end > w.start {
                out.append(OverrideWindow(start: w.start, end: end, factor: w.factor, targetLo: w.targetLo, targetHi: w.targetHi))
            }
        }
        return out
    }

    static func active(_ ws: [OverrideWindow], at t: Date) -> OverrideWindow? {
        ws.first { $0.start <= t && t < $0.end }
    }

    private static func breakpoints(_ spans: [(Date, Date)], _ ws: [OverrideWindow]) -> [Date] {
        var s = Set<Date>()
        for (a, b) in spans { s.insert(a); s.insert(b) }
        for w in ws { s.insert(w.start); s.insert(w.end) }
        return s.sorted()
    }

    /// Resample a Double timeline at all segment+window breakpoints, scaling within windows.
    static func applyDoubles(_ tl: [AbsoluteScheduleValue<Double>], _ ws: [OverrideWindow], divide: Bool) -> [AbsoluteScheduleValue<Double>] {
        guard !ws.isEmpty, !tl.isEmpty else { return tl }
        let bps = breakpoints(tl.map { ($0.startDate, $0.endDate) }, ws)
        var out: [AbsoluteScheduleValue<Double>] = []
        for i in 0..<(bps.count - 1) {
            let a = bps[i], b = bps[i + 1]
            guard let base = tl.closestPrior(to: a)?.value else { continue }
            var v = base
            let mid = a.addingTimeInterval(b.timeIntervalSince(a) / 2)
            if let ov = active(ws, at: mid), let f = ov.factor, f > 0 { v = divide ? base / f : base * f }
            out.append(AbsoluteScheduleValue(startDate: a, endDate: b, value: v))
        }
        return out
    }

    static func applyISF(_ tl: [AbsoluteScheduleValue<LoopQuantity>], _ ws: [OverrideWindow]) -> [AbsoluteScheduleValue<LoopQuantity>] {
        guard !ws.isEmpty, !tl.isEmpty else { return tl }
        let unit = LoopUnit.milligramsPerDeciliter
        let bps = breakpoints(tl.map { ($0.startDate, $0.endDate) }, ws)
        var out: [AbsoluteScheduleValue<LoopQuantity>] = []
        for i in 0..<(bps.count - 1) {
            let a = bps[i], b = bps[i + 1]
            guard let base = tl.closestPrior(to: a)?.value.doubleValue(for: unit) else { continue }
            var v = base
            let mid = a.addingTimeInterval(b.timeIntervalSince(a) / 2)
            if let ov = active(ws, at: mid), let f = ov.factor, f > 0 { v = base / f }   // ISF ÷ f
            out.append(AbsoluteScheduleValue(startDate: a, endDate: b, value: LoopQuantity(unit: unit, doubleValue: v)))
        }
        return out
    }

    /// Replace the correction range with the override's range over each window.
    static func applyTargets(_ tl: [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>], _ ws: [OverrideWindow]) -> [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>] {
        guard !ws.isEmpty, !tl.isEmpty else { return tl }
        let unit = LoopUnit.milligramsPerDeciliter
        let bps = breakpoints(tl.map { ($0.startDate, $0.endDate) }, ws)
        var out: [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>] = []
        for i in 0..<(bps.count - 1) {
            let a = bps[i], b = bps[i + 1]
            guard let base = tl.closestPrior(to: a)?.value else { continue }
            var range = base
            let mid = a.addingTimeInterval(b.timeIntervalSince(a) / 2)
            if let ov = active(ws, at: mid), let lo = ov.targetLo, let hi = ov.targetHi {
                range = LoopQuantity(unit: unit, doubleValue: lo)...LoopQuantity(unit: unit, doubleValue: hi)
            }
            out.append(AbsoluteScheduleValue(startDate: a, endDate: b, value: range))
        }
        return out
    }
}
