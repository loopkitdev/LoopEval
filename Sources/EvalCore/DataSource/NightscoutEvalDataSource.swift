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
    /// Apply Loop Temporary Overrides (insulinNeedsScaleFactor + correction range)
    /// to the therapy timeline over their active windows. Off by default.
    public let applyOverrides: Bool

    // MARK: – Init

    public init(
        client: NightscoutClient,
        cache: DataCache,
        insulinType: ExponentialInsulinModelPreset = .rapidActingAdult,
        defaultMaxBolus: Double = 10.0,
        defaultMaxBasalRate: Double = 3.0,
        applyOverrides: Bool = false
    ) {
        self.client = client
        self.cache = cache
        self.insulinType = insulinType
        self.defaultMaxBolus = defaultMaxBolus
        self.defaultMaxBasalRate = defaultMaxBasalRate
        self.applyOverrides = applyOverrides
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
        // Doses embed insulinType (EvalInsulinDose.insulinType drives the PD curve),
        // so the cache key MUST include the model — otherwise --insulin-type silently
        // reuses the first model's cached doses.
        // v2: temp-basal volume now uses the pump's delivered `amount` (not rate*duration).
        // DBG_RATEDUR=1 forces commanded rate*duration (ignore delivered amount) — a
        // diagnostic to test whether the field's runtime IOB used commanded vs delivered.
        let rateDurTag = ProcessInfo.processInfo.environment["DBG_RATEDUR"] != nil ? "_ratedur" : ""
        let cacheKey = DataCache.key(for: "doses_v3\(rateDurTag)_\(insulinType)", url: client.baseURL, interval: lookback)
        if let cached: [EvalInsulinDose] = try await cache.load(key: cacheKey) {
            return cached
        }

        let treatments = try await client.fetchTreatments(interval: lookback)
        let doses = convertTreatmentsToDoses(treatments)
        try await cache.save(doses, key: cacheKey)
        return doses
    }

    public func getCarbEntries(interval: DateInterval) async throws -> [EvalCarbEntry] {
        // v12 — robust ISO parse (with/without fractional seconds) for userEnteredAt
        // /timestamp/created_at: Loop emits userEnteredAt with NO fractional seconds,
        // which the fractional-only parser rejected → the visibility gate fell back to
        // the upload-delayed ObjectId time (80 min late on rloop). v11 switched the
        // gate to userEnteredAt; v6 user-takeover deferral; v4 ObjectId entryDate.
        let cacheKey = DataCache.key(for: "carbs_v12", url: client.baseURL, interval: interval)
        if let cached: [EvalCarbEntry] = try await cache.load(key: cacheKey) {
            return cached
        }

        let treatments = try await client.fetchTreatments(interval: interval)
        let carbs = convertTreatmentsToCarbs(treatments)
        try await cache.save(carbs, key: cacheKey)
        return carbs
    }

    public func getTherapyTimeline(interval: DateInterval) async throws -> TherapyTimeline {
        // TherapyTimeline carries insulinType → include it in the key (see getDoses).
        // Override application also changes the schedules → key on it too.
        let ovTag = applyOverrides ? "_ov" : ""
        // v4ovgate: timeline now also carries RAW schedules + override windows for
        // decision-time override gating (future overrides invisible to earlier
        // forecasts). Bump so caches written before the gate are rebuilt.
        let cacheKey = DataCache.key(for: "therapy_v4ovgate_\(insulinType)\(ovTag)", url: client.baseURL, interval: interval)
        if let cached: TherapyTimeline = try await cache.load(key: cacheKey) {
            return cached
        }

        // TIME-VARYING profile history: the user's ISF/CR/basal/target schedule
        // changes over time (each record's startDate = when it became active).
        // Backfilling one current profile across history mis-dates the schedule
        // (e.g. user2 ISF 35-37 pre-2025-05-15, 32 after). Segment the interval
        // by the profile active at each point.
        let history = (try? await client.fetchProfileHistory()) ?? []
        var overrides: [OverrideWindow] = []
        if applyOverrides {
            let treatments = try await client.fetchTreatments(interval: interval)
            overrides = TemporaryOverrides.windows(from: treatments, parse: makeISOParser().date(from:))
        }
        let timeline: TherapyTimeline
        if history.count > 1 {
            timeline = buildTherapyTimelineHistory(records: history, interval: interval, overrides: overrides)
        } else {
            let profileRecord: NightscoutProfileRecord
            if let first = history.first { profileRecord = first }
            else { profileRecord = try await client.fetchProfile() }
            timeline = buildTherapyTimeline(from: profileRecord, interval: interval, overrides: overrides)
        }
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
        var doses: [EvalInsulinDose] = []

        for t in treatments {
            guard let date = Self.robustISODate(t.created_at) else { continue }

            let eventType = t.eventType.trimmingCharacters(in: .whitespaces)

            switch eventType {
            case "Temp Basal":
                let rate = t.absolute ?? t.rate ?? 0.0
                let durationMin = t.duration ?? 0
                let endDate = date.addingTimeInterval(durationMin * 60)
                // Use the pump's ACTUAL pulse-quantized delivered amount when present
                // (Loop reconciles IOB/effects on delivered units; pumps deliver basal
                // in 0.05U pulses, so amount != rate*duration). Fall back to the nominal
                // rate*duration only when the delivered amount wasn't recorded.
                let forceRateDur = ProcessInfo.processInfo.environment["DBG_RATEDUR"] != nil
                let volume = forceRateDur ? (rate * (durationMin / 60.0)) : (t.amount ?? (rate * (durationMin / 60.0)))
                let dose = EvalInsulinDose(
                    deliveryType: .basal,
                    startDate: date,
                    endDate: endDate,
                    volume: volume,
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
        // Delivery times of USER manual boluses (automatic != true), for the
        // user-takeover rule below. A bolus timestamp is its delivery time (not
        // backdatable), so created_at is correct here.
        let manualBolusTimes: [Date] = treatments
            .compactMap { tb in
                guard let ins = tb.insulin, ins > 0, tb.automatic != true else { return nil }
                return Self.robustISODate(tb.created_at)
            }
            .sorted()
        // A co-logged meal carb and its manual bolus are effectively ATOMIC: the
        // user enters carbs and boluses in one action (90d: carb saved a median ~1s
        // from its bolus, 98% within 10s — but the NS upload / ObjectId-insert order
        // of the two can straddle a decision cycle). The user's manual bolus may
        // arrive slightly before OR after the carb's insert; pair within this window.
        let userTakeoverWindow: TimeInterval = 15 * 60

        return treatments.compactMap { t -> EvalCarbEntry? in
            guard let carbs = t.carbs, carbs > 0 else { return nil }
            guard let createdAt = Self.robustISODate(t.created_at) else { return nil }
            // Meal time may differ from entry time (user can log past/future meals).
            // Visibility is gated by entryDate; the absorption curve starts at startDate.
            //
            // created_at / timestamp are BACKDATABLE — the user logs a meal with
            // the time she ate (e.g. 20 min ago), so both equal the meal time, not
            // when Loop actually learned about the carbs. Using created_at as the
            // decision-time gate leaks the meal into the sim ~15-40 min early, so
            // the sim auto-boluses before reality did (and then double-covers the
            // user's manual meal bolus → counter blow-up).
            //
            // The correct visibility gate is `userEnteredAt` — Loop's own record of
            // the moment the user tapped "save" (its `userCreatedDate`), present on
            // 100% of this user's carb entries. It is immune to upload-latency noise
            // (unlike the ObjectId DB-insert time, which can lag the tap by seconds)
            // and is exactly "when Loop learned about the carbs". Fall back to the
            // ObjectId insert time, then created_at, when absent.
            let baseEntry = Self.robustISODate(t.userEnteredAt)
                ?? t.objectIdInsertionDate ?? createdAt
            // User-takeover + carb/bolus ALIGNMENT: when the user manual-boluses for
            // this meal, Loop (in reality) saw the carbs and the bolus together and
            // deferred to the user. Gate the carb's auto-dosing visibility to the
            // PAIRED MANUAL BOLUS's delivery time so the meal becomes visible exactly
            // when the bolus enters IOB — never before (no premature auto-dose /
            // double-cover) and never after (no bolus-in-IOB-without-its-carb forecast
            // crash). Pair to the NEAREST manual bolus within the window in EITHER
            // direction: the carb's ObjectId-insert can land just before OR after its
            // bolus, and a forward-only pair misses the bolus-uploaded-first case,
            // leaving the carb invisible while its bolus is already dosing → crash.
            // Meals with no nearby manual bolus keep baseEntry (Loop genuinely owns it).
            let pairedBolus = manualBolusTimes
                .filter { abs($0.timeIntervalSince(baseEntry)) <= userTakeoverWindow }
                .min(by: { abs($0.timeIntervalSince(baseEntry)) < abs($1.timeIntervalSince(baseEntry)) })
            // dosingVisibleDate = the (aligned) gate for NORMAL auto-dosing;
            // entryDate stays the TRUE entry time (baseEntry).
            let dosingVisibleDate = pairedBolus ?? baseEntry
            let mealDate = Self.robustISODate(t.timestamp) ?? createdAt
            // Loop publishes per-entry absorptionTime in NS (MINUTES). Use it —
            // otherwise the carb math falls back to a long default (~3h) and
            // absorbs meals far slower than the deployed Loop (e.g. a 30-min fast
            // meal modeled as 180-min), which under-projects the meal, starves the
            // retrospective correction, and makes the sim under-dose.
            let absorption: TimeInterval? = t.absorptionTime.map { $0 * 60.0 }  // minutes → seconds
            return EvalCarbEntry(
                startDate: mealDate,
                entryDate: baseEntry,                 // TRUE entry time (ObjectId DB-insert)
                dosingVisibleDate: dosingVisibleDate, // deferred gate for normal auto-dosing
                quantity: LoopQuantity(unit: .gram, doubleValue: carbs),
                absorptionTime: absorption,
                foodType: nil
            )
        }
        .sorted { $0.startDate < $1.startDate }
    }

    // MARK: – Profile → TherapyTimeline conversion

    /// Build a TIME-VARYING therapy timeline from profile history: each profile
    /// record is active from its `startDate` until the next record's, so the
    /// ISF/CR/basal/target schedule changes over time as the user changed it.
    /// Per-segment raw schedules are concatenated, THEN overrides are applied.
    private func buildTherapyTimelineHistory(
        records: [NightscoutProfileRecord],
        interval: DateInterval,
        overrides: [OverrideWindow]
    ) -> TherapyTimeline {
        // Profile `startDate` has NO fractional seconds (e.g. 2026-06-16T06:48:23Z),
        // unlike treatment `created_at` (…23.791Z), so parse robustly (with and
        // without fractional) and fall back to created_at.
        let isoFrac = makeISOParser()
        let isoPlain = ISO8601DateFormatter(); isoPlain.formatOptions = [.withInternetDateTime]
        func parseDate(_ s: String?) -> Date? {
            guard let s = s else { return nil }
            return isoFrac.date(from: s) ?? isoPlain.date(from: s)
        }
        // (startDate, record), sorted ascending; drop records with no parseable date.
        let dated = records.compactMap { r -> (Date, NightscoutProfileRecord)? in
            var d = parseDate(r.startDate)
            if d == nil, let ms = r.mills, let msv = Double(ms) {
                d = Date(timeIntervalSince1970: msv / 1000.0)   // mills = ms epoch
            }
            guard let dd = d else { return nil }
            return (dd, r)
        }.sorted { $0.0 < $1.0 }
        guard !dated.isEmpty else {
            return buildTherapyTimeline(from: records[0], interval: interval, overrides: overrides)
        }
        // Build segments covering [interval.start, interval.end): record i is
        // active from max(start_i, interval.start) to min(start_{i+1}, interval.end).
        var segBasal: [AbsoluteScheduleValue<Double>] = []
        var segISF: [AbsoluteScheduleValue<LoopQuantity>] = []
        var segCR: [AbsoluteScheduleValue<Double>] = []
        var segTarget: [AbsoluteScheduleValue<ClosedRange<LoopQuantity>>] = []
        var lastRaw: TherapyTimeline?
        for (i, (start, record)) in dated.enumerated() {
            let activeStart = max(start, interval.start)
            let activeEnd = (i + 1 < dated.count) ? min(dated[i + 1].0, interval.end) : interval.end
            guard activeStart < activeEnd else { continue }
            let raw = buildTherapyTimeline(from: record,
                                           interval: DateInterval(start: activeStart, end: activeEnd),
                                           overrides: [])
            segBasal.append(contentsOf: raw.basal)
            segISF.append(contentsOf: raw.sensitivity)
            segCR.append(contentsOf: raw.carbRatio)
            segTarget.append(contentsOf: raw.target)
            lastRaw = raw   // most-recent in-window record supplies loopSettings/caps
        }
        guard let tmpl = lastRaw, !segISF.isEmpty else {
            return buildTherapyTimeline(from: dated.last!.1, interval: interval, overrides: overrides)
        }
        // Apply overrides to the concatenated (time-varying) schedules for the
        // BAKED fields; keep the RAW concatenated schedules + windows so buildInput
        // can re-derive decision-time-gated schedules (future overrides invisible
        // to earlier decisions). No-op gating when overrides is empty.
        return TherapyTimeline(
            basal: TemporaryOverrides.applyDoubles(segBasal, overrides, divide: false),
            sensitivity: TemporaryOverrides.applyISF(segISF, overrides),
            carbRatio: TemporaryOverrides.applyDoubles(segCR, overrides, divide: true),
            target: TemporaryOverrides.applyTargets(segTarget, overrides),
            suspendThreshold: tmpl.suspendThreshold,
            maxBolus: tmpl.maxBolus,
            maxBasalRate: tmpl.maxBasalRate,
            insulinType: insulinType,
            rawBasal:       overrides.isEmpty ? [] : segBasal,
            rawSensitivity: overrides.isEmpty ? [] : segISF,
            rawCarbRatio:   overrides.isEmpty ? [] : segCR,
            rawTarget:      overrides.isEmpty ? [] : segTarget,
            overrideWindows: overrides
        )
    }

    private func buildTherapyTimeline(
        from record: NightscoutProfileRecord,
        interval: DateInterval,
        overrides: [OverrideWindow] = []
    ) -> TherapyTimeline {
        let profileName = record.defaultProfile ?? "Default"
        guard let store = record.store,
              let profile = store[profileName] ?? store.values.first
        else {
            // Return safe defaults when no profile is available
            return makeDefaultTherapyTimeline(interval: interval)
        }

        let timeZone = Self.resolveTimeZone(profile.timezone)

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

        // Apply Temporary Overrides over their active windows (basal ×f, ISF ÷f, CR ÷f,
        // target ← override range). No-op when overrides is empty.
        let basalFinal  = TemporaryOverrides.applyDoubles(basalValues, overrides, divide: false)
        let isfFinal    = TemporaryOverrides.applyISF(isfValues, overrides)
        let crFinal     = TemporaryOverrides.applyDoubles(crValues, overrides, divide: true)
        let targetsFinal = TemporaryOverrides.applyTargets(targets, overrides)

        return TherapyTimeline(
            basal: basalFinal.isEmpty ? makeDefaultBasal(interval: interval) : basalFinal,
            sensitivity: isfFinal.isEmpty ? makeDefaultISF(interval: interval) : isfFinal,
            carbRatio: crFinal.isEmpty ? makeDefaultCR(interval: interval) : crFinal,
            target: targetsFinal.isEmpty ? makeDefaultTarget(interval: interval) : targetsFinal,
            suspendThreshold: suspendThreshold,
            maxBolus: maxBolus,
            maxBasalRate: maxBasalRate,
            insulinType: insulinType,
            // RAW (un-override) schedules + windows for decision-time override
            // gating in buildInput (see TherapySettings). Empty when no overrides.
            rawBasal:       overrides.isEmpty ? [] : (basalValues.isEmpty ? makeDefaultBasal(interval: interval) : basalValues),
            rawSensitivity: overrides.isEmpty ? [] : (isfValues.isEmpty   ? makeDefaultISF(interval: interval)   : isfValues),
            rawCarbRatio:   overrides.isEmpty ? [] : (crValues.isEmpty     ? makeDefaultCR(interval: interval)    : crValues),
            rawTarget:      overrides.isEmpty ? [] : (targets.isEmpty      ? makeDefaultTarget(interval: interval): targets),
            overrideWindows: overrides
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

    /// Resolve a Nightscout profile timezone to the USER's zone (never the sim
    /// host's). Loop uploads POSIX `ETC/GMT±N` ids in UPPERCASE, which
    /// `TimeZone(identifier:)` rejects (valid id is `Etc/GMT±N`); without this
    /// the schedule would silently fall back to the host's timezone and be
    /// applied hours off. NOTE: `Etc/GMT+7` == UTC−7 (POSIX sign inversion),
    /// which `TimeZone(identifier:)` handles correctly once the case is fixed.
    static func resolveTimeZone(_ identifier: String?) -> TimeZone {
        let utc = TimeZone(identifier: "UTC")!
        guard let id = identifier, !id.isEmpty else { return utc }
        if let tz = TimeZone(identifier: id) { return tz }
        // Case-normalize the IANA "Etc/GMT±N" form (Loop sends "ETC/GMT+7").
        if let r = id.range(of: "etc/gmt", options: .caseInsensitive) {
            let suffix = String(id[r.upperBound...])   // e.g. "+7"
            if let tz = TimeZone(identifier: "Etc/GMT" + suffix) { return tz }
        }
        // Bare "GMT±N" → seconds (UTC offset, NOT POSIX-inverted here).
        if let r = id.range(of: "gmt", options: .caseInsensitive) {
            let suffix = id[r.upperBound...].trimmingCharacters(in: .whitespaces)
            if let hours = Int(suffix), let tz = TimeZone(secondsFromGMT: hours * 3600) { return tz }
        }
        if let tz = TimeZone(abbreviation: id) { return tz }
        return utc   // last resort: UTC, never the host's .current
    }

    private func makeISOParser() -> ISO8601DateFormatter {
        let fmt = ISO8601DateFormatter()
        fmt.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return fmt
    }

    /// Parse an ISO8601 timestamp robustly: WITH fractional seconds (Loop's
    /// created_at, e.g. "…21.000Z") AND WITHOUT (e.g. "…21Z"). Loop's
    /// `userEnteredAt`/`timestamp` are often emitted with NO fractional seconds,
    /// which the fractional-only parser silently rejects (returns nil) — that made
    /// the carb visibility gate fall back to the upload-delayed ObjectId time
    /// (80 min late on a batch-upload instance like rloop). Always parse both.
    static func robustISODate(_ s: String?) -> Date? {
        guard let s = s else { return nil }
        let frac = ISO8601DateFormatter(); frac.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let d = frac.date(from: s) { return d }
        let plain = ISO8601DateFormatter(); plain.formatOptions = [.withInternetDateTime]
        return plain.date(from: s)
    }
}

// baseURL is now public on NightscoutClient — no extension needed.
