// LoopEvalCLI.swift — root command definition

import ArgumentParser

/// Root entry point for the `loop-eval` CLI.
///
/// Note: `@main` is intentionally absent here because this target uses
/// a `main.swift` entry point (`LoopEvalCLI.main()`).  Swift forbids
/// having both `@main` and `main.swift` in the same executable target.
@available(macOS 10.15, macCatalyst 13, iOS 13, tvOS 13, watchOS 6, *)
struct LoopEvalCLI: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "loop-eval",
        abstract: "Evaluate LoopAlgorithm forecast accuracy against real-world CGM data.",
        version: "0.1.0",
        subcommands: [EvaluateCommand.self, CacheCommand.self, InspectCommand.self, BenchCommand.self, SimulateCommand.self],
        defaultSubcommand: EvaluateCommand.self
    )
}
