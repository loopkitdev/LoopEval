// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "LoopEval",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "loop-eval", targets: ["LoopEvalCLI"]),
        .library(name: "EvalCore", targets: ["EvalCore"]),
    ],
    dependencies: [
        .package(url: "https://github.com/tidepool-org/LoopAlgorithm", branch: "main"),
        // TODO: Re-evaluate NightscoutKit (LoopKit/NightscoutKit) — currently swift-tools-version:5.7
        // and targets iOS/watchOS; may produce Swift 6 strict-concurrency warnings.
        // Add back in Phase 2 when building the Nightscout data source.
        // .package(url: "https://github.com/LoopKit/NightscoutKit", branch: "main"),
        .package(url: "https://github.com/apple/swift-argument-parser", from: "1.3.0"),
    ],
    targets: [
        .target(
            name: "EvalCore",
            dependencies: [
                .product(name: "LoopAlgorithm", package: "LoopAlgorithm"),
                // TODO: add NightscoutKit dependency here in Phase 2
            ]
        ),
        .executableTarget(
            name: "LoopEvalCLI",
            dependencies: [
                "EvalCore",
                .product(name: "ArgumentParser", package: "swift-argument-parser"),
            ]
        ),
        .testTarget(
            name: "EvalCoreTests",
            dependencies: [
                "EvalCore",
                .product(name: "LoopAlgorithm", package: "LoopAlgorithm"),
            ],
            resources: [.copy("Fixtures")]
        ),
    ],
    swiftLanguageModes: [.v6]
)
