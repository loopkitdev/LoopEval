// TherapyTimeline.swift — all therapy settings expanded over a time interval
//
// TherapyTimeline is the "time-expanded" version of TherapySettings: instead of
// a daily schedule, each field holds a sorted list of AbsoluteScheduleValues
// that cover the requested interval end-to-end (suitable for direct use with
// LoopAlgorithm.generatePrediction).
//
// TherapyTimeline is deliberately kept as a typealias of TherapySettings so
// serialisation code, tests, and algorithm wiring share one type.

import Foundation
import LoopAlgorithm

/// All therapy settings resolved over a time interval.
/// Fields are ordered lists of ``AbsoluteScheduleValue`` spanning the
/// requested interval; they can be sliced directly into
/// ``LoopAlgorithm.generatePrediction``.
public typealias TherapyTimeline = TherapySettings
