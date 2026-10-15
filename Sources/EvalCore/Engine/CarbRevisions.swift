// CarbRevisions.swift — splice edited carb entries into time-ordered revisions
//
// Nightscout stores only the FINAL state of a carb entry, stamped at the
// ORIGINAL entry time. A user who logs 15g at 11:26 then edits it to 45g at
// 12:01 leaves one doc: 45g @ 11:26. Naive replay therefore applies the full
// 45g from 11:26 — carrying ~30g of phantom COB until the edit and over-dosing.
//
// The reconstruction (analysis/loopeval_analysis/reconstruct_carb_history.py)
// reads the deployed Loop's per-cycle devicestatus COB to recover the as-seen
// grams at each revision time, and emits an OVERLAY JSON listing only the EDITED
// entries with their revision sequences. This module splices those revisions
// into the cached carb array: each edited entry becomes N EvalCarbEntry records
// sharing a revisionKey, and the window builder keeps only the latest-visible
// revision at each decision time. Non-edited entries are left untouched.

import Foundation
import LoopAlgorithm

/// One edited carb entry's reconstructed revision history.
struct CarbRevisionSpec: Decodable {
    let matchStartDate: String          // ISO — meal time of the cached entry to replace
    let revisionKey: String             // Loop syncIdentifier (groups the revisions)
    let absorptionTime: TimeInterval?   // seconds (optional; falls back to cached entry)
    let foodType: String?
    let revisions: [Revision]

    struct Revision: Decodable {
        let visibleFrom: String         // ISO — when this grams value became visible to Loop
        let grams: Double
        let startDate: String?          // ISO meal time of THIS revision (an edit can move it); default: the cached entry's
        let absorptionTime: TimeInterval?   // seconds, this revision's (default: the spec's / cached entry's)
    }
}

struct CarbRevisionsFile: Decodable {
    let version: Int?
    let edited: [CarbRevisionSpec]
}

enum CarbRevisions {

    /// Lenient ISO-8601 parser (with or without fractional seconds, Z or offset).
    private static func parseISO(_ s: String) -> Date? {
        let withFrac = ISO8601DateFormatter()
        withFrac.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let d = withFrac.date(from: s) { return d }
        let noFrac = ISO8601DateFormatter()
        noFrac.formatOptions = [.withInternetDateTime]
        return noFrac.date(from: s)
    }

    /// Apply a revisions overlay to a cached carb array.
    ///
    /// For each edited spec, finds the cached entry whose `startDate` matches
    /// `matchStartDate` (within `tolerance`), removes it, and inserts one
    /// `EvalCarbEntry` per revision (same meal `startDate`; `entryDate` =
    /// `dosingVisibleDate` = the revision's `visibleFrom`; `revisionKey` set).
    ///
    /// Safety: some revision's grams must equal the cached entry grams (within
    /// `gramsTol`) — usually the last, but a Tidepool food record can keep an EARLIER
    /// version than Loop's last save, and the overlay then supplies the later grams.
    /// Otherwise the overlay is stale/misaligned and the entry is left untouched
    /// (logged via `onWarning`). Specs that match
    /// no in-window cached entry are skipped silently (entry outside the window).
    static func apply(
        to carbs: [EvalCarbEntry],
        file: CarbRevisionsFile,
        tolerance: TimeInterval = 120,
        gramsTol: Double = 0.5,
        onWarning: ((String) -> Void)? = nil
    ) -> [EvalCarbEntry] {
        guard !file.edited.isEmpty else { return carbs }

        var result = carbs
        var appliedCount = 0
        for spec in file.edited {
            guard let mealTime = parseISO(spec.matchStartDate) else {
                onWarning?("carb-revisions: unparseable matchStartDate \(spec.matchStartDate)")
                continue
            }
            // Find the matching cached entry (closest startDate within tolerance), among
            // entries carrying one of the spec's grams: two carbs logged a minute apart must
            // not swap overlays.
            let near = result.enumerated().filter {
                abs($0.element.startDate.timeIntervalSince(mealTime)) <= tolerance
            }
            let candidates = near.filter { c in
                let g = c.element.quantity.doubleValue(for: .gram)
                return spec.revisions.contains(where: { abs($0.grams - g) <= gramsTol })
            }
            guard let match = candidates.min(by: {
                abs($0.element.startDate.timeIntervalSince(mealTime)) <
                abs($1.element.startDate.timeIntervalSince(mealTime))
            }) else {
                if !near.isEmpty {
                    onWarning?("carb-revisions: stale overlay for \(spec.matchStartDate) (no nearby entry has a revision's grams) — left as-is")
                }
                continue   // entry not in this window — nothing to splice
            }
            let cached = match.element
            // Remove the cached entry and splice in the revisions.
            result.remove(at: match.offset)
            let absorption = spec.absorptionTime ?? cached.absorptionTime
            let food = spec.foodType ?? cached.foodType
            for rev in spec.revisions {
                guard let vf = parseISO(rev.visibleFrom) else {
                    onWarning?("carb-revisions: unparseable visibleFrom \(rev.visibleFrom)")
                    continue
                }
                result.append(EvalCarbEntry(
                    startDate: rev.startDate.flatMap(parseISO) ?? cached.startDate,   // meal time (absorption anchor)
                    entryDate: vf,
                    dosingVisibleDate: vf,
                    quantity: LoopQuantity(unit: .gram, doubleValue: rev.grams),
                    absorptionTime: rev.absorptionTime ?? absorption,
                    foodType: food,
                    revisionKey: spec.revisionKey
                ))
            }
            appliedCount += 1
        }
        onWarning?("carb-revisions: spliced \(appliedCount)/\(file.edited.count) edited entries")
        return result.sorted { $0.startDate < $1.startDate }
    }

    /// Load + apply from a JSON file path. Returns the carbs unchanged on any I/O
    /// or decode error (logged via `onWarning`).
    static func applyFile(
        path: String,
        to carbs: [EvalCarbEntry],
        onWarning: ((String) -> Void)? = nil
    ) -> [EvalCarbEntry] {
        let url = URL(fileURLWithPath: path)
        guard let data = try? Data(contentsOf: url) else {
            onWarning?("carb-revisions: could not read \(path)")
            return carbs
        }
        guard let file = try? JSONDecoder().decode(CarbRevisionsFile.self, from: data) else {
            onWarning?("carb-revisions: could not decode \(path)")
            return carbs
        }
        return apply(to: carbs, file: file, onWarning: onWarning)
    }
}
