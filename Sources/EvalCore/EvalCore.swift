// EvalCore — Loop forecast evaluation library
//
// Public API surface.  All types are defined in their own files under Types/.

import Foundation
@_exported import LoopAlgorithm   // re-export so consumers don't need to import LoopAlgorithm separately

// Type aliases for convenience
public typealias GlucoseRangeSchedule = [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>]

public enum EvalCore {
    public static let version = "0.1.0"
}
