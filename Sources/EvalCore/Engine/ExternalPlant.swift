// ExternalPlant.swift — couple the closed-loop simulator to an external patient model.
//
// In counterfactual mode the candidate's glucose normally advances by the ICE replay:
// the field's own BG change plus the modeled effect of the candidate-vs-field insulin
// difference. With an external plant, THAT ONE STEP is replaced: each cycle's newly
// delivered candidate doses go to a plant process, and the plant's CGM at the next
// sample time(s) comes back as the candidate's glucose. Everything upstream — the
// decision, the pump-pulse basal accumulator, temp expiry, manual-bolus resizing,
// decision timing — is the unchanged simulator, so a plant-coupled run and an ordinary
// run differ ONLY in the physiology. That is what a sim-of-the-sim needs: the truth
// arm runs the identical controller in closed loop against a known plant.
//
// Protocol: one JSON object per line on the plant's stdin, one reply per line on its
// stdout.
//   request  {"t0": ISO, "t1": ISO, "doses": [{"type": "basal"|"bolus", "start": ISO,
//             "end": ISO, "volume": U}], "samples": [ISO, ...]}
//   reply    {"bg": [mg/dL | null, ...]}     // one entry per requested sample, in order;
//                                             // null = the CGM gave no reading at that time
// The plant owns everything that is not insulin (meals, behavior, sensor noise) and is
// expected to have reproduced the field history up to the first t0 it is sent.
//
// v2 (docs/ice/plant-protocol-v2.md), backward compatible:
//   request  + "state": {"rec_bolus": U, "iob": U, "cob": g, "bg": mg/dL}   // candidate at t0
//   reply    + "carbs":   [{"t": ISO, "grams": g, "absorption_s": s}]       // the person's
//            + "boluses": [{"t": ISO, "ratio": x} | {"t": ISO, "units": u}] // actions in (t0, t1]
//            + "overrides": [{"t": ISO, "end": ISO, "factor": f?, "targetLo": mg/dL?, "targetHi": mg/dL?}]
// Actions are only acted on with --plant-behavior: carbs enter the candidate's carb store,
// visible from the next decision; a bolus is delivered AT the next decision as ratio x the
// bolus-calculator recommendation there (or as units), so the simulator stays the source of
// truth for what was delivered and sends it back in the next request's doses. An override is a
// Temporary Override the person started at t: insulin needs x factor (basal x f, ISF / f, CR / f),
// correction range targetLo...targetHi (both or neither), until end. It joins the candidate's
// override windows exactly like an exported one, so decisions at or after t see it; a later
// override supersedes an earlier one from its start.

import Foundation

public final class ExternalPlant: @unchecked Sendable {
    private let process: Process
    private let input: FileHandle
    private let output: FileHandle
    private var buffer = Data()
    private let iso: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    /// Launch `command` through /bin/sh. Its stderr passes through to ours.
    public init(command: String) throws {
        process = Process()
        process.executableURL = URL(fileURLWithPath: "/bin/sh")
        process.arguments = ["-c", command]
        let inPipe = Pipe(), outPipe = Pipe()
        process.standardInput = inPipe
        process.standardOutput = outPipe
        process.standardError = FileHandle.standardError
        try process.run()
        input = inPipe.fileHandleForWriting
        output = outPipe.fileHandleForReading
    }

    public struct PlantError: Error, CustomStringConvertible {
        public let description: String
    }

    /// A carb entry the plant's person made in (t0, t1].
    public struct Carb { public let t: Date; public let grams: Double; public let absorption: TimeInterval? }
    /// A manual bolus the plant's person asked for in (t0, t1]: a multiple of the bolus-calculator
    /// recommendation, or an absolute amount.
    public struct Bolus { public let t: Date; public let ratio: Double?; public let units: Double? }
    /// A Temporary Override the plant's person started at `start`.
    public struct Override { public let start: Date; public let end: Date; public let factor: Double?
                             public let targetLo: Double?; public let targetHi: Double? }
    /// `bg[i]` is nil where the plant's CGM gave no reading (sensor dropout, compression, warm-up).
    public struct Reply { public let bg: [Double?]; public let carbs: [Carb]; public let boluses: [Bolus]
                          public let overrides: [Override] }

    private let isoNoFrac = ISO8601DateFormatter()
    private func date(_ s: Any?) -> Date? {
        guard let s = s as? String else { return nil }
        return iso.date(from: s) ?? isoNoFrac.date(from: s)
    }

    /// Deliver `doses` over [t0, t1] and return the plant's CGM at each of `samples`, plus any
    /// actions (carb entries, manual boluses) its person took in the step. `state` describes the
    /// candidate at t0 (v2; nil sends a v1 request).
    func advance(t0: Date, t1: Date, doses: [EvalInsulinDose], samples: [Date],
                 state: [String: Double]? = nil) throws -> Reply {
        var req: [String: Any] = [
            "t0": iso.string(from: t0),
            "t1": iso.string(from: t1),
            "doses": doses.map { d -> [String: Any] in
                ["type": d.deliveryType == .bolus ? "bolus" : "basal",
                 "start": iso.string(from: d.startDate),
                 "end": iso.string(from: d.endDate),
                 "volume": d.volume]
            },
            "samples": samples.map { iso.string(from: $0) },
        ]
        if let state = state {
            req["state"] = state.mapValues { $0.isFinite ? $0 : 0.0 }
        }
        var line = try JSONSerialization.data(withJSONObject: req)
        line.append(0x0A)
        input.write(line)
        let reply = try readLine()
        let bad = PlantError(description: "external plant: bad reply \(String(data: reply, encoding: .utf8) ?? "?")")
        guard let obj = try JSONSerialization.jsonObject(with: reply) as? [String: Any],
              let raw = obj["bg"] as? [Any], raw.count == samples.count else { throw bad }
        // A number is a reading; JSON null is "no reading". Anything else is malformed.
        var bg: [Double?] = []
        for v in raw {
            if v is NSNull { bg.append(nil) }
            else if let d = (v as? NSNumber)?.doubleValue, d.isFinite { bg.append(d) }
            else { throw bad }
        }
        let carbs: [Carb] = (obj["carbs"] as? [[String: Any]] ?? []).compactMap { c in
            guard let t = date(c["t"]), let g = c["grams"] as? Double, g > 0 else { return nil }
            return Carb(t: t, grams: g, absorption: c["absorption_s"] as? Double)
        }
        let boluses: [Bolus] = (obj["boluses"] as? [[String: Any]] ?? []).compactMap { b in
            guard let t = date(b["t"]) else { return nil }
            let r = b["ratio"] as? Double, u = b["units"] as? Double
            return (r == nil && u == nil) ? nil : Bolus(t: t, ratio: r, units: u)
        }
        // An override needs t < end and a factor > 0 or a full target range; anything else is malformed.
        var overrides: [Override] = []
        for o in obj["overrides"] as? [[String: Any]] ?? [] {
            let f = o["factor"] as? Double, lo = o["targetLo"] as? Double, hi = o["targetHi"] as? Double
            guard let t = date(o["t"]), let end = date(o["end"]), end > t,
                  f.map({ $0 > 0 && $0.isFinite }) ?? true, (lo == nil) == (hi == nil),
                  lo.map({ $0 <= hi! }) ?? true, f != nil || lo != nil else {
                throw PlantError(description: "external plant: bad override \(o)")
            }
            overrides.append(Override(start: t, end: end, factor: f, targetLo: lo, targetHi: hi))
        }
        return Reply(bg: bg, carbs: carbs, boluses: boluses, overrides: overrides)
    }

    private func readLine() throws -> Data {
        while true {
            if let nl = buffer.firstIndex(of: 0x0A) {
                let line = buffer.subdata(in: buffer.startIndex..<nl)
                buffer.removeSubrange(buffer.startIndex...nl)
                return line
            }
            let chunk = output.availableData
            if chunk.isEmpty { throw PlantError(description: "external plant: process closed its output") }
            buffer.append(chunk)
        }
    }

    /// Close the plant's stdin and wait for it to exit.
    public func finish() {
        try? input.close()
        process.waitUntilExit()
    }
}
