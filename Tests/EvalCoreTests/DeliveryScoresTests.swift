// DeliveryScoresTests.swift — unit tests for delivery-based ODR/UDR

import Foundation
import Testing
@testable import EvalCore
import LoopAlgorithm

@Suite("DeliveryScores — delivery-based ODR/UDR")
struct DeliveryScoresTests {

    // MARK: – Helpers

    private func makeSample(_ t: Date, bg: Double) -> EvalGlucoseSample {
        EvalGlucoseSample(
            startDate: t,
            quantity: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: bg),
            provenanceIdentifier: "test",
            isDisplayOnly: false,
            wasUserEntered: false
        )
    }

    private func makePrediction(_ t: Date, deltaU: Double) -> PredictionRecord {
        PredictionRecord(
            evaluatedAt: t,
            predicted: [],
            iob: 0,
            cob: 0,
            recommendedDeltaU: deltaU,
            recommendedBolus: deltaU,
            recommendedTempBasalRate: 0,
            scheduledBasalRate: 0
        )
    }

    private func makeResult(_ records: [PredictionRecord], actual: [EvalGlucoseSample]) -> EvaluationResult {
        let start = records.first!.evaluatedAt
        let end   = actual.last!.startDate
        return EvaluationResult(
            interval: DateInterval(start: start, end: end),
            config: .default,
            predictions: records,
            actual: actual,
            skippedCount: 0
        )
    }

    // Build an actual-BG timeline sampled every 5 min so interpolation at
    // arbitrary future times works.
    private func flatActualAt(_ bg: Double, from start: Date, count: Int) -> [EvalGlucoseSample] {
        (0..<count).map { i in
            makeSample(start.addingTimeInterval(Double(i) * 300), bg: bg)
        }
    }

    // MARK: – Core behaviour

    @Test("over-delivery into a pre-low moment produces positive ODR")
    func overDeliveryIntoLowProducesODR() {
        let t0 = Date(timeIntervalSince1970: 1_700_000_000)
        // Candidate delivers MORE than baseline at t0
        let baseline = makeResult(
            [makePrediction(t0, deltaU: 0.0)],
            actual: flatActualAt(60, from: t0, count: 50)   // 60 mg/dL sustained low
        )
        let candidate = makeResult(
            [makePrediction(t0, deltaU: 1.0)],              // 1 U more than baseline
            actual: flatActualAt(60, from: t0, count: 50)
        )
        let d = DeliveryScores.compute(
            baseline: baseline, candidate: candidate,
            horizons: [90 * 60], actualGlucose: baseline.actual
        )
        #expect(d.weightedODR > 0,          "Expected ODR > 0, got \(d.weightedODR)")
        #expect(d.weightedUDR == 0,         "Expected UDR = 0 at flat-low, got \(d.weightedUDR)")
    }

    @Test("under-delivery into a pre-high moment produces positive UDR")
    func underDeliveryIntoHighProducesUDR() {
        let t0 = Date(timeIntervalSince1970: 1_700_000_000)
        let baseline = makeResult(
            [makePrediction(t0, deltaU: 1.0)],              // baseline delivers 1U
            actual: flatActualAt(220, from: t0, count: 50)  // 220 mg/dL sustained high
        )
        let candidate = makeResult(
            [makePrediction(t0, deltaU: 0.0)],              // candidate delivers 0 — less than baseline
            actual: flatActualAt(220, from: t0, count: 50)
        )
        let d = DeliveryScores.compute(
            baseline: baseline, candidate: candidate,
            horizons: [90 * 60], actualGlucose: baseline.actual
        )
        #expect(d.weightedUDR > 0,          "Expected UDR > 0, got \(d.weightedUDR)")
        #expect(d.weightedODR == 0,         "Expected ODR = 0 at flat-high, got \(d.weightedODR)")
    }

    @Test("same delivery in both configs = zero scores")
    func identicalDeliveryProducesZeroScores() {
        let t0 = Date(timeIntervalSince1970: 1_700_000_000)
        let base = makeResult(
            [makePrediction(t0, deltaU: 0.5)],
            actual: flatActualAt(60, from: t0, count: 50)   // low — would score if there were a delta
        )
        let cand = makeResult(
            [makePrediction(t0, deltaU: 0.5)],              // identical
            actual: flatActualAt(60, from: t0, count: 50)
        )
        let d = DeliveryScores.compute(
            baseline: base, candidate: cand,
            horizons: [90 * 60], actualGlucose: base.actual
        )
        #expect(d.weightedODR == 0, "Expected ODR = 0 when deliveries match, got \(d.weightedODR)")
        #expect(d.weightedUDR == 0, "Expected UDR = 0 when deliveries match, got \(d.weightedUDR)")
    }

    @Test("in-range actual BG produces zero scores regardless of delta")
    func inRangeActualProducesZeroScores() {
        let t0 = Date(timeIntervalSince1970: 1_700_000_000)
        let base = makeResult(
            [makePrediction(t0, deltaU: 0.0)],
            actual: flatActualAt(108, from: t0, count: 50)  // in target (100-115)
        )
        let cand = makeResult(
            [makePrediction(t0, deltaU: 2.0)],              // huge delta — but BG is fine
            actual: flatActualAt(108, from: t0, count: 50)
        )
        let d = DeliveryScores.compute(
            baseline: base, candidate: cand,
            horizons: [90 * 60], actualGlucose: base.actual
        )
        #expect(d.weightedODR == 0, "In-range actual should zero ODR; got \(d.weightedODR)")
        #expect(d.weightedUDR == 0, "In-range actual should zero UDR; got \(d.weightedUDR)")
    }

    @Test("under-delivery at pre-low moment does NOT produce ODR")
    func underDeliveryAtLowIsNotODR() {
        // Candidate delivered LESS than baseline, but BG went low anyway.
        // ODR only penalises over-delivery, so this should be zero.
        let t0 = Date(timeIntervalSince1970: 1_700_000_000)
        let base = makeResult(
            [makePrediction(t0, deltaU: 1.0)],
            actual: flatActualAt(60, from: t0, count: 50)
        )
        let cand = makeResult(
            [makePrediction(t0, deltaU: 0.5)],              // less than baseline
            actual: flatActualAt(60, from: t0, count: 50)
        )
        let d = DeliveryScores.compute(
            baseline: base, candidate: cand,
            horizons: [90 * 60], actualGlucose: base.actual
        )
        #expect(d.weightedODR == 0, "Under-delivery at low shouldn't count toward ODR; got \(d.weightedODR)")
    }

    @Test("lower actual BG produces larger ODR (risk weighting)")
    func riskWeightingScalesWithSeverity() {
        let t0 = Date(timeIntervalSince1970: 1_700_000_000)
        let shared = { (bg: Double) -> DeliveryScores in
            let b = self.makeResult(
                [self.makePrediction(t0, deltaU: 0.0)],
                actual: self.flatActualAt(bg, from: t0, count: 50)
            )
            let c = self.makeResult(
                [self.makePrediction(t0, deltaU: 1.0)],
                actual: self.flatActualAt(bg, from: t0, count: 50)
            )
            return DeliveryScores.compute(
                baseline: b, candidate: c,
                horizons: [90 * 60], actualGlucose: b.actual
            )
        }
        let mild   = shared(95)   // barely below target
        let severe = shared(55)   // dangerous
        #expect(severe.weightedODR > mild.weightedODR,
                "Severe low (\(severe.weightedODR)) should have larger ODR than mild (\(mild.weightedODR))")
    }
}
