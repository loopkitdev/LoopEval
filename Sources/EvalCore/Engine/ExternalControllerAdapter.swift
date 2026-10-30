// ExternalControllerAdapter.swift — a candidate dosing function in another process.
//
// --candidate-external-controller '<cmd>': each candidate decision, the engine sends the process the
// state the decision sees — the candidate's own glucose, its own dose history (every delivered unit,
// absolute), the carb entries visible to it, the settings and limits at t — and reads back a bolus and
// a temp-basal rate. Everything around the decision (enactment, pump pulses and temp expiry, manual
// bolus resizing, disruption clamps, the body) is the unchanged simulator, so a run with an external
// controller differs from an ordinary one ONLY in the dose decision. Built for the reduction role's
// surrogate dosing functions, which want far fewer inputs than LoopAlgorithm reads.
//
// Loop still runs inside the adapter at every step: its forecast, IOB and COB fill the trace's
// diagnostic fields, and its bolus-calculator recommendation sizes the user's manual boluses as it
// does in any run. Loop's own automatic decision is also sent (as "loop"), so a controller that echoes
// it reproduces the stock run exactly — the identity check for this path. A surrogate under test must
// not read it.
//
// Protocol: one JSON object per line on stdin, one reply per line on stdout.
//   request {"t": ISO,
//            "glucose": [[ISO, mg/dL], ...],                       // the decision's glucose window
//            "doses": [[ISO start, ISO end, U, "basal"|"bolus", automatic], ...],   // absolute U
//            "carbs": [[ISO start, g, absorption s | null], ...],  // entries visible to this decision
//            "settings": {"basal": U/h, "isf": mg/dL/U, "cr": g/U, "target_lo": mg/dL, "target_hi": mg/dL,
//                         "suspend": mg/dL, "max_basal": U/h, "max_bolus": U, "bolus_inc": U, "temp_inc": U/h},
//            "user_target": [lo, hi] | null,                       // the person's target schedule at t, no override
//            "override": {"factor": x | null, "target_lo": mg/dL | null, "target_hi": mg/dL | null} | null,  // active at t
//            "loop": {"bolus": U, "temp_rate": U/h, "iob": U, "cob": g}}
//   reply   {"bolus": U, "temp_rate": U/h}
// The reply is clamped to [0, max bolus] and [0, max basal] and floored to the pump's increments,
// as Loop's own decision is.

import Foundation
import LoopAlgorithm

public final class ExternalController: @unchecked Sendable {
    private let process: Process
    private let input: FileHandle
    private let output: FileHandle
    private var buffer = Data()
    private let iso: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    public struct ControllerError: Error, CustomStringConvertible { public let description: String }

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

    func decide(_ req: EngineStepRequest, loop: EngineStepResult) throws -> (bolus: Double, tempRate: Double) {
        let mg = LoopUnit.milligramsPerDeciliter
        let t = req.t
        func at<T>(_ s: [AbsoluteScheduleValue<T>]) -> T? {
            s.first(where: { $0.startDate <= t && $0.endDate > t })?.value ?? s.last(where: { $0.startDate <= t })?.value
        }
        let target = at(req.input.target)
        let settings: [String: Double] = [
            "basal": at(req.input.basal) ?? .nan,
            "isf": at(req.input.sensitivity)?.doubleValue(for: mg) ?? .nan,
            "cr": at(req.input.carbRatio) ?? .nan,
            "target_lo": target?.lowerBound.doubleValue(for: mg) ?? .nan,
            "target_hi": target?.upperBound.doubleValue(for: mg) ?? .nan,
            "suspend": req.therapy.suspendThreshold(at: t)?.doubleValue(for: mg) ?? .nan,
            "max_basal": req.therapy.maxBasalRate(at: t),
            "max_bolus": req.therapy.maxBolus(at: t),
            "bolus_inc": req.config.bolusIncrement,
            "temp_inc": req.config.tempBasalIncrement,
        ]
        // The person's own target (the schedule without overrides) and the override active at t, sent apart from
        // "settings" (where both are already folded in) so a controller can take them as its only user inputs.
        let userTarget = at(req.therapy.rawTarget.isEmpty ? req.therapy.target : req.therapy.rawTarget)
        let active = OverrideWindow.resolved(req.therapy.overrideWindows, at: t).last { $0.start <= t && t < $0.end }
        let p = loop.prediction
        let msg: [String: Any] = [
            "t": iso.string(from: t),
            "glucose": req.input.glucose.map { [iso.string(from: $0.startDate), $0.quantity.doubleValue(for: mg)] as [Any] },
            "doses": req.input.doses.map {
                [iso.string(from: $0.startDate), iso.string(from: $0.endDate), $0.volume,
                 $0.deliveryType == .bolus ? "bolus" : "basal", $0.automatic] as [Any]
            },
            "carbs": req.input.carbs.map {
                [iso.string(from: $0.startDate), $0.quantity.doubleValue(for: .gram),
                 $0.absorptionTime.map { $0 as Any } ?? NSNull()] as [Any]
            },
            "settings": settings.mapValues { $0.isFinite ? $0 as Any : NSNull() },
            "user_target": userTarget.map { [$0.lowerBound.doubleValue(for: mg), $0.upperBound.doubleValue(for: mg)] as Any } ?? NSNull(),
            "override": active.map { w -> Any in
                ["factor": w.factor.map { $0 as Any } ?? NSNull(), "target_lo": w.targetLo.map { $0 as Any } ?? NSNull(),
                 "target_hi": w.targetHi.map { $0 as Any } ?? NSNull()] as [String: Any]
            } ?? NSNull(),
            "loop": ["bolus": loop.bolus, "temp_rate": loop.tempRate,
                     "iob": (p.activeInsulin ?? 0).isFinite ? (p.activeInsulin ?? 0) : 0,
                     "cob": (p.activeCarbs ?? 0).isFinite ? (p.activeCarbs ?? 0) : 0],
        ]
        var line = try JSONSerialization.data(withJSONObject: msg)
        line.append(0x0A)
        input.write(line)
        let reply = try readLine()
        guard let obj = try JSONSerialization.jsonObject(with: reply) as? [String: Any],
              let b = (obj["bolus"] as? NSNumber)?.doubleValue, b.isFinite,
              let r = (obj["temp_rate"] as? NSNumber)?.doubleValue, r.isFinite else {
            throw ControllerError(description: "external controller: bad reply \(String(data: reply, encoding: .utf8) ?? "?")")
        }
        return (b, r)
    }

    private func readLine() throws -> Data {
        while true {
            if let nl = buffer.firstIndex(of: 0x0A) {
                let line = buffer.subdata(in: buffer.startIndex..<nl)
                buffer.removeSubrange(buffer.startIndex...nl)
                return line
            }
            let chunk = output.availableData
            if chunk.isEmpty { throw ControllerError(description: "external controller: process closed its output") }
            buffer.append(chunk)
        }
    }

    /// Close the controller's stdin and wait for it to exit.
    public func finish() {
        try? input.close()
        process.waitUntilExit()
    }
}

struct ExternalControllerAdapter: DosingEngine {
    let controller: ExternalController
    private let loop = LoopAdapter()

    func step(_ req: EngineStepRequest) -> EngineStepResult {
        let r = loop.step(req)
        let reply: (bolus: Double, tempRate: Double)
        do { reply = try controller.decide(req, loop: r) } catch {
            FileHandle.standardError.write(Data("\(error)\n".utf8))
            exit(1)
        }
        let t = req.t
        let pump = PumpModel(basalRateIncrement: req.config.tempBasalIncrement, bolusIncrement: req.config.bolusIncrement,
                             pulseQuantum: 0, rounding: .down)
        let bolus = pump.supportedBolusVolume(min(max(reply.bolus, 0), req.therapy.maxBolus(at: t)))
        let tempRate = pump.supportedBasalRate(min(max(reply.tempRate, 0), req.therapy.maxBasalRate(at: t)))
        let sched = CandidatePump.scheduledRate(at: t, in: req.therapy.basal)
        return EngineStepResult(
            dose: bolus + (tempRate - sched) * req.config.evalStep / 3600,
            bolus: bolus,
            tempRate: tempRate,
            prediction: r.prediction,
            manualBolusRec: r.manualBolusRec,
            tempAction: "set",
            algorithmInputFixture: nil
        )
    }
}
