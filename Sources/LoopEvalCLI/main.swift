// main.swift — entry point for loop-eval
//
// Uses Task + RunLoop.main.run() to enter an async context from a
// synchronous main.swift, since @main can't coexist with main.swift.
// The Task calls exit(0) on normal completion; error paths call exit(withError:)
// inside AsyncParsableCommand.main().
import Foundation

Task {
    await LoopEvalCLI.main()
    exit(0)
}
RunLoop.main.run()
