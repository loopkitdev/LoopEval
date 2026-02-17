// ScheduleExpander.swift — expand repeating daily schedules to absolute timelines
//
// Replicates the behaviour of LoopKit's `DailyValueSchedule.truncatingBetween`
// without pulling in LoopKit.  Handles DST transitions by walking day-by-day
// using a Calendar configured with the schedule's timezone.

import Foundation
import LoopAlgorithm

/// Expands a repeating daily schedule to ``AbsoluteScheduleValue`` entries
/// covering `interval`.
///
/// - Parameters:
///   - items: Schedule segments as `(timeAsSeconds: Int, value: T)` pairs,
///     sorted ascending by `timeAsSeconds`.  At least one item is required.
///   - timeZone: The timezone in which the schedule repeats (midnight in this
///     zone starts each new day).
///   - interval: The half-open `[start, end)` interval to cover.
/// - Returns: Non-overlapping `AbsoluteScheduleValue` entries whose union
///   exactly covers `interval`.
public func expandDailySchedule<T>(
    items: [(timeAsSeconds: Int, value: T)],
    timeZone: TimeZone,
    interval: DateInterval
) -> [AbsoluteScheduleValue<T>] {
    guard !items.isEmpty else { return [] }

    // Sort items so we can binary-search later
    let sorted = items.sorted { $0.timeAsSeconds < $1.timeAsSeconds }

    var calendar = Calendar(identifier: .gregorian)
    calendar.timeZone = timeZone

    var result: [AbsoluteScheduleValue<T>] = []

    // Walk day-by-day: find the midnight (in the schedule TZ) that is ≤ interval.start
    var dayStart = calendar.startOfDay(for: interval.start)

    while dayStart < interval.end {
        let nextDayStart = calendar.date(byAdding: .day, value: 1, to: dayStart)!

        for (idx, item) in sorted.enumerated() {
            // Absolute start of this segment within the current day
            let segmentStart = dayStart.addingTimeInterval(TimeInterval(item.timeAsSeconds))

            // Absolute end = start of next segment (or start of next day)
            let segmentEnd: Date
            if idx + 1 < sorted.count {
                segmentEnd = dayStart.addingTimeInterval(TimeInterval(sorted[idx + 1].timeAsSeconds))
            } else {
                segmentEnd = nextDayStart
            }

            // Skip segments that end before our interval starts
            if segmentEnd <= interval.start { continue }
            // Stop if this segment starts after our interval ends
            if segmentStart >= interval.end { break }

            // Clip to interval
            let clippedStart = max(segmentStart, interval.start)
            let clippedEnd   = min(segmentEnd,   interval.end)

            guard clippedStart < clippedEnd else { continue }

            result.append(AbsoluteScheduleValue(
                startDate: clippedStart,
                endDate:   clippedEnd,
                value:     item.value
            ))
        }

        dayStart = nextDayStart
    }

    return result
}
