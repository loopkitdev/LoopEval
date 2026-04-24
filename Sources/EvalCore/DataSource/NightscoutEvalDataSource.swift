// NightscoutEvalDataSource.swift — EvalDataSource backed by a live Nightscout instance
//
// Fetches data from Nightscout, optionally caching results to disk.
// Glucose noise filtering: entries with noise >= 4 are treated as display-only.
// Temp-basal lookback: doses are fetched from (interval.start - 2h) so that
// active temp basals that started before the evaluation window are captured.

import Foundation
import LoopAlgorithm

public actor NightscoutEvalDataSource: EvalDataSource {

    // MARK: – Properties

    public let client: NightscoutClient
    public let cache: DataCache
    public let insulinType: ExponentialInsulinModelPreset
    public let defaultMaxBolus: Double
    public let defaultMaxBasalRate: Double

    // MARK: – Init

    public init(
        client: NightscoutClient,
        cache: DataCache,
        insulinType: ExponentialInsulinModelPreset = .rapidActingAdult,
        defaultMaxBolus: Double = 10.0,
        defaultMaxBasalRate: Double = 3.0
    ) {
        self.client = client
        self.cache = cache
        self.insulinType = insulinType
        self.defaultMaxBolus = defaultMaxBolus
        self.defaultMaxBasalRate = defaultMaxBasalRate
    }

    // MARK: – EvalDataSource

    public func getGlucoseValues(interval: DateInterval) async throws -> [EvalGlucoseSample] {
        let cacheKey = DataCache.key(for: "glucose", url: client.baseURL, interval: interval)
        if let cached: [EvalGlucoseSample] = try await cache.load(key: cacheKey) {
            return cached
        }

        let entries = try await client.fetchEntries(interval: interval)
        let samples = convertEntries(entries)
        try await cache.save(samples, key: cacheKey)
        return samples
    }

    public func getDoses(interval: DateInterval) async throws -> [EvalInsulinDose] {
        // Extend lookback by 2h to capture temp basals that started before interval
        let lookback = DateInterval(
            start: interval.start.addingTimeInterval(-2 * 3600),
            end: interval.end
        )
        let cacheKey = DataCache.key(for: "doses", url: client.baseURL, interval: lookback)
        if let cached: [EvalInsulinDose] = try await cache.load(key: cacheKey) {
            return cached
        }

        let treatments = try await client.fetchTreatments(interval: lookback)
        let doses = convertTreatmentsToDoses(treatments)
        try await cache.save(doses, key: cacheKey)
        return doses
    }

    public func getCarbEntries(interval: DateInterval) async throws -> [EvalCarbEntry] {
        let cacheKey = DataCache.key(for: "carbs", url: client.baseURL, interval: interval)
        if let cached: [EvalCarbEntry] = try await cache.load(key: cacheKey) {
            return cached
        }

        let treatments = try await client.fetchTreatments(interval: interval)
        let carbs = convertTreatmentsToCarbs(treatments)
        try await cache.save(carbs, key: cacheKey)
        return carbs
    }

    public func getTherapyTimeline(interval: DateInterval) async throws -> TherapyTimeline {
        let cacheKey = DataCache.key(for: "therapy", url: client.baseURL, interval: interval)
        if let cached: TherapyTimeline = try await cache.load(key: cacheKey) {
            return cached
        }

        let profileRecord = try await client.fetchProfile()
        let timeline = buildTherapyTimeline(from: profileRecord, interval: interval)
        try await cache.save(timeline, key: cacheKey)
        return timeline
    }

    // MARK: – Glucose conversion

    private func convertEntries(_ entries: [NightscoutEntry]) -> [EvalGlucoseSample] {
        let fmt = makeISOParser()
        return entries.compactMap { entry in
            // Only sensor glucose values
            guard entry.type == "sgv" || entry.type == nil else { return nil }
            guard let sgv = entry.sgv, sgv > 0 else { return nil }

            let date: Date
            if let d = fmt.date(from: entry.dateString) {
                date = d
            } else {
                return nil
            }

            // Noise >= 4 → display-only / unreliable; flag it
            let isDisplayOnly = (entry.noise ?? 0) >= 4

            return EvalGlucoseSample(
                startDate: date,
                quantity: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: Double(sgv)),
                provenanceIdentifier: "com.evalcore.nightscout",
                isDisplayOnly: isDisplayOnly,
                wasUserEntered: false
            )
        }
        .sorted { $0.startDate < $1.startDate }
    }

    // MARK: – Treatment → Dose conversion

    private func convertTreatmentsToDoses(_ treatments: [NightscoutTreatment]) -> [EvalInsulinDose] {
        let fmt = makeISOParser()
        var doses: [EvalInsulinDose] = []

        for t in treatments {
            guard let date = fmt.date(from: t.created_at) else { continue }

            let eventType = t.eventType.trimmingCharacters(in: .whitespaces)

            switch eventType {
            case "Temp Basal":
                let rate = t.absolute ?? t.rate ?? 0.0
                let durationMin = t.duration ?? 0
                let endDate = date.addingTimeInterval(durationMin * 60)
                let dose = EvalInsulinDose(
                    deliveryType: .basal,
                    startDate: date,
                    endDate: endDate,
                    volume: rate * (durationMin / 60.0),
                    insulinType: insulinType
                )
                doses.append(dose)

            case "Bolus", "Meal Bolus", "Correction Bolus", "Carb Correction":
                guard let units = t.insulin, units > 0 else { continue }
                // Loop emits `automatic: true/false` on every bolus. Default
                // to `true` when absent, which matches older Loop versions
                // that only logged automatic boluses.
                let dose = EvalInsulinDose(
                    deliveryType: .bolus,
                    startDate: date,
                    endDate: date.addingTimeInterval(30),   // bolus delivery ~30s
                    volume: units,
                    insulinType: insulinType,
                    automatic: t.automatic ?? true
                )
                doses.append(dose)

            case "SMB":
                guard let units = t.insulin, units > 0 else { continue }
                // SMBs are algorithm-driven by definition.
                let dose = EvalInsulinDose(
                    deliveryType: .bolus,
                    startDate: date,
                    endDate: date.addingTimeInterval(30),
                    volume: units,
                    insulinType: insulinType,
                    automatic: true
                )
                doses.append(dose)

            case "Suspend Pump":
                // Model as a zero-rate temp basal of 30 minutes (approximate)
                let dose = EvalInsulinDose(
                    deliveryType: .basal,
                    startDate: date,
                    endDate: date.addingTimeInterval(30 * 60),
                    volume: 0,
                    insulinType: insulinType
                )
                doses.append(dose)

            case "Resume Pump":
                // Not directly representable; skip — resume is implied by the
                // absence of further suspend entries.
                break

            default:
                // Ignore unrecognised event types
                break
            }
        }

        return doses.sorted { $0.startDate < $1.startDate }
    }

    // MARK: – Treatment → Carb conversion

    private func convertTreatmentsToCarbs(_ treatments: [NightscoutTreatment]) -> [EvalCarbEntry] {
        let fmt = makeISOParser()
        return treatments.compactMap { t in
            guard let carbs = t.carbs, carbs > 0 else { return nil }
            guard let date = fmt.date(from: t.created_at) else { return nil }
            return EvalCarbEntry(
                startDate: date,
                quantity: LoopQuantity(unit: .gram, doubleValue: carbs),
                absorptionTime: nil,    // NS doesn't carry absorption time
                foodType: nil
            )
        }
        .sorted { $0.startDate < $1.startDate }
    }

    // MARK: – Profile → TherapyTimeline conversion

    private func buildTherapyTimeline(
        from record: NightscoutProfileRecord,
        interval: DateInterval
    ) -> TherapyTimeline {
        let profileName = record.defaultProfile ?? "Default"
        guard let store = record.store,
              let profile = store[profileName] ?? store.values.first
        else {
            // Return safe defaults when no profile is available
            return makeDefaultTherapyTimeline(interval: interval)
        }

        let tzIdentifier = profile.timezone ?? "UTC"
        let timeZone = TimeZone(identifier: tzIdentifier)
            ?? TimeZone(abbreviation: tzIdentifier)
            ?? .current

        // Determine glucose units (default mg/dL)
        let unitStr = (profile.units ?? record.units ?? "mg/dl").lowercased()
        let isMmol = unitStr.hasPrefix("mmol")

        // Convert ISF: if mmol, multiply by 18.01559 to get mg/dL
        let isfMultiplier = isMmol ? 18.01559 : 1.0
        // Convert targets: same unit conversion
        let targetMultiplier = isMmol ? 18.01559 : 1.0

        // Basal
        let basalItems = profile.basal.map { ($0.timeAsSeconds, $0.value) }
        let basalValues = expandDailySchedule(
            items: basalItems, timeZone: timeZone, interval: interval)

        // ISF (sensitivity)
        let isfItems = profile.sens.map { ($0.timeAsSeconds, $0.value * isfMultiplier) }
        let isfValues = expandDailySchedule(
            items: isfItems, timeZone: timeZone, interval: interval
        ).map { entry in
            AbsoluteScheduleValue(
                startDate: entry.startDate,
                endDate: entry.endDate,
                value: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: entry.value)
            )
        }

        // Carb ratio (g/U — unit-independent)
        let crItems = profile.carbratio.map { ($0.timeAsSeconds, $0.value) }
        let crValues = expandDailySchedule(
            items: crItems, timeZone: timeZone, interval: interval)

        // Target ranges
        let targets = buildTargetRanges(
            lowItems: profile.target_low,
            highItems: profile.target_high,
            multiplier: targetMultiplier,
            timeZone: timeZone,
            interval: interval
        )

        // Loop publishes its runtime caps and suspend threshold into
        // profile.loopSettings. Prefer those over our defaults so the sim
        // matches what the pump-side Loop is actually constrained by.
        // minimumBGGuard is in mg/dL even when the profile unit is mmol/L.
        let ls = record.loopSettings
        let suspendThreshold: LoopQuantity? = ls?.minimumBGGuard.map {
            LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: $0)
        }
        let maxBolus     = ls?.maximumBolus            ?? defaultMaxBolus
        let maxBasalRate = ls?.maximumBasalRatePerHour ?? defaultMaxBasalRate

        return TherapyTimeline(
            basal: basalValues.isEmpty ? makeDefaultBasal(interval: interval) : basalValues,
            sensitivity: isfValues.isEmpty ? makeDefaultISF(interval: interval) : isfValues,
            carbRatio: crValues.isEmpty ? makeDefaultCR(interval: interval) : crValues,
            target: targets.isEmpty ? makeDefaultTarget(interval: interval) : targets,
            suspendThreshold: suspendThreshold,
            maxBolus: maxBolus,
            maxBasalRate: maxBasalRate,
            insulinType: insulinType
        )
    }

    private func buildTargetRanges(
        lowItems: [NightscoutScheduleItem],
        highItems: [NightscoutScheduleItem],
        multiplier: Double,
        timeZone: TimeZone,
        interval: DateInterval
    ) -> [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>] {
        guard !lowItems.isEmpty, !highItems.isEmpty else { return [] }

        // Pair low/high by timeAsSeconds
        let highDict = Dictionary(uniqueKeysWithValues: highItems.map { ($0.timeAsSeconds, $0.value) })

        let rangeItems: [(Int, ClosedRange<LoopQuantity>)] = lowItems.compactMap { low in
            guard let highValue = highDict[low.timeAsSeconds] else { return nil }
            let lo = LoopQuantity(unit: .milligramsPerDeciliter,
                                  doubleValue: low.value * multiplier)
            let hi = LoopQuantity(unit: .milligramsPerDeciliter,
                                  doubleValue: highValue * multiplier)
            // Ensure lo <= hi
            if lo.doubleValue(for: .milligramsPerDeciliter) >
               hi.doubleValue(for: .milligramsPerDeciliter) {
                return (low.timeAsSeconds, hi...lo)
            }
            return (low.timeAsSeconds, lo...hi)
        }

        return expandDailySchedule(
            items: rangeItems, timeZone: timeZone, interval: interval)
    }

    // MARK: – Safe defaults (used when profile is missing data)

    private func makeDefaultBasal(interval: DateInterval) -> [AbsoluteScheduleValue<Double>] {
        [AbsoluteScheduleValue(startDate: interval.start, endDate: interval.end, value: 1.0)]
    }

    private func makeDefaultISF(interval: DateInterval) -> [AbsoluteScheduleValue<LoopQuantity>] {
        [AbsoluteScheduleValue(
            startDate: interval.start, endDate: interval.end,
            value: LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: 50.0)
        )]
    }

    private func makeDefaultCR(interval: DateInterval) -> [AbsoluteScheduleValue<Double>] {
        [AbsoluteScheduleValue(startDate: interval.start, endDate: interval.end, value: 10.0)]
    }

    private func makeDefaultTarget(
        interval: DateInterval
    ) -> [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>] {
        let lo = LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: 95.0)
        let hi = LoopQuantity(unit: .milligramsPerDeciliter, doubleValue: 105.0)
        return [AbsoluteScheduleValue(
            startDate: interval.start, endDate: interval.end, value: lo...hi)]
    }

    private func makeDefaultTherapyTimeline(interval: DateInterval) -> TherapyTimeline {
        TherapyTimeline(
            basal: makeDefaultBasal(interval: interval),
            sensitivity: makeDefaultISF(interval: interval),
            carbRatio: makeDefaultCR(interval: interval),
            target: makeDefaultTarget(interval: interval),
            suspendThreshold: nil,
            maxBolus: defaultMaxBolus,
            maxBasalRate: defaultMaxBasalRate,
            insulinType: insulinType
        )
    }

    // MARK: – Helpers

    private func makeISOParser() -> ISO8601DateFormatter {
        let fmt = ISO8601DateFormatter()
        fmt.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return fmt
    }
}

// baseURL is now public on NightscoutClient — no extension needed.
