// main.swift — entry point for loop-eval
//
// Uses Task + RunLoop.main.run() to enter an async context from a
// synchronous main.swift, since @main can't coexist with main.swift.
// The Task calls exit(0) on normal completion; error paths call exit(withError:)
// inside AsyncParsableCommand.main().
import Foundation

Task {
    // `simulate --config/--set` expand into ordinary flags before parsing (SimulateConfig.swift).
    let args: [String]
    do {
        args = try SimulateConfig.expand(Array(CommandLine.arguments.dropFirst()))
    } catch {
        FileHandle.standardError.write(Data("Error: \(error)\n".utf8))
        exit(64)
    }
    await LoopEvalCLI.main(args)
    exit(0)
}
RunLoop.main.run()
