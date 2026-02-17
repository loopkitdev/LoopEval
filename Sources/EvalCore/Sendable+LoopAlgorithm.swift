// Sendable+LoopAlgorithm.swift
//
// LoopAlgorithm was authored before Swift 6.  The enums below are backed by
// String (or are otherwise trivially safe for concurrent use) but were not
// annotated with Sendable.  We add retroactive @unchecked Sendable conformances
// so that EvalCore's Swift-6-mode code can include them in Sendable structs.

import LoopAlgorithm

extension GlucoseCondition:              @retroactive @unchecked Sendable {}
extension InsulinDeliveryType:           @retroactive @unchecked Sendable {}
extension ExponentialInsulinModelPreset: @retroactive @unchecked Sendable {}
