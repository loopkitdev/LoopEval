import ArgumentParser

@main
struct LoopEval: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "loop-eval",
        abstract: "Evaluate LoopAlgorithm forecast accuracy against real-world CGM data."
    )

    mutating func run() async throws {
        print("loop-eval: no subcommand specified. Use --help for usage.")
    }
}
