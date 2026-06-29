# oref golden-master oracle

Runs **Trio's real oref JS** (`profile → meal → autosens → iob → determine-basal`)
on raw Nightscout data, so our Swift `OpenAPSSwift` port can be diffed against
the upstream code on **identical inputs**. This is how we proved the
determine-basal stage is byte-identical to Trio, and (extended here) that the
forecast/dynISF are faithful.

## Setup
1. Clone the Trio fork (oref JS lives under `trio-oref/lib`):
   `github.com/nightscout/Trio` → `/path/to/Trio`
2. Install its node deps:
   `cd /path/to/Trio/trio-oref && npm install lodash moment-timezone`

## Run
```sh
# 1. Fetch raw NS data (credentials via env — never commit a site URL/token)
NS_URL=https://<site> NS_TOKEN=<token> \
  python3 fetch_ns.py /tmp/oracle 2026-06-07T00:00:00.000Z 2026-06-09T03:00:00.000Z

# 2. Run Trio's pipeline at a decision time (use the field's deliverAt)
TRIO_OREF_LIB=/path/to/Trio/trio-oref/lib \
  node oracle.js /tmp/oracle /path/to/orefuser_prefs.json 2026-06-09T02:20:33Z
```

## Notes / gotchas (learned building this)
- `find_insulin` parses NS `eventType` natively (`Temp Basal`, `Meal/Correction Bolus`).
  SMBs have **no** branch — map NS `SMB` → `{_type:"Bolus", amount, timestamp:created_at}`.
- `makeProfile` applies prefs as **top-level** overrides (its for-pref-in-profile loop),
  plus `settings/targets/basals/isf/carbratio` in oref0 shapes and a `temptargets` array.
- Glucose must be **AAPS-smoothed** (Trio's `smoothGlucose`) and filtered to `<= clock`.
- `clock` must be the field **deliverAt** (a hair after the last CGM), or that CGM is filtered out.
- autosens uses the **real wall-clock** for its deviation window — replaying old data,
  `Date` must be **mocked to the clock** (done in `oracle.js`) or it finds "0 deviations".
- `trio_custom` TDD fields (`currentTDD`/`weightedAverage`/`average_total_data`) drive dynISF.

## Result (OREF user, 2026-06)
At a sample cycle the oracle reproduces the field's **forecast** exactly
(eventualBG, dynISF ratio, ISF, UAMpredBG, minGuardBG) — confirming our oref port
is faithful. The residual per-cycle dose differences localize to the
**deviation-autosens** (acutely sensitive to the exact deviation-window data) and
the decision-time data state, not the oref math.
