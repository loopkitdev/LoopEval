// oref golden-master oracle: run Trio's REAL oref JS pipeline (profile → meal →
// autosens → iob → determine-basal) on raw Nightscout data, to validate our
// Swift OpenAPSSwift port against the upstream code on identical inputs.
//
// Usage:
//   TRIO_OREF_LIB=/path/to/Trio/trio-oref/lib \
//   node oracle.js <dataDir> <prefs.json> <clockISO>
//
//   <dataDir>   directory with treatments.json, entries.json, profile.json
//               (raw NS arrays — see fetch_ns.py)
//   <prefs.json> the user's oref preferences (oref pref keys; see repo memory)
//   <clockISO>  the decision time, e.g. the field deliverAt 2026-06-09T02:20:33Z
//
// Deps: the Trio fork's oref JS (github.com/nightscout/Trio, lib/), with
//   `npm install lodash moment-timezone` run inside trio-oref. NO secrets here.
//
// Why the Date mock: oref's autosens uses the real wall-clock for its deviation
// window. Replaying historical data, that window is empty ("0 deviations since
// today"), so we pin Date to the clock.

const [,, DATA_DIR, PREFS_PATH, CLOCK] = process.argv;
if (!DATA_DIR || !PREFS_PATH || !CLOCK) {
  console.error("usage: node oracle.js <dataDir> <prefs.json> <clockISO>");
  process.exit(1);
}
const RealDate = Date;
const _FAKE = new RealDate(CLOCK).getTime();
Date = class extends RealDate {
  constructor(...a) { if (a.length === 0) { super(_FAKE); } else { super(...a); } }
  static now() { return _FAKE; }
};

const fs = require('fs');
// Point TRIO_OREF_LIB at the lib/ dir of a trio-oref checkout.
const L = (process.env.TRIO_OREF_LIB || './trio-oref/lib') + '/';
const makeProfile = require(L + 'profile/index'), mealGen = require(L + 'meal/index');
const autosens = require(L + 'determine-basal/autosens'), iobGen = require(L + 'iob/index');
const determine = require(L + 'determine-basal/determine-basal'), basalSetTemp = require(L + 'basal-set-temp');
const glucoseGetLast = require(L + 'glucose-get-last');

const J = f => JSON.parse(fs.readFileSync(f, 'utf8'));
const T = J(DATA_DIR + '/treatments.json'), E = J(DATA_DIR + '/entries.json');
const profRec = J(DATA_DIR + '/profile.json')[0], prefs = J(PREFS_PATH);
const store = profRec.store[profRec.defaultProfile];

const temptargets = T.filter(t => t.eventType === "Temporary Target" && new Date(t.created_at) <= new Date(CLOCK))
  .map(t => ({ created_at: t.created_at, targetTop: t.targetTop, targetBottom: t.targetBottom, duration: t.duration }));

// ---- profile inputs (NS -> oref0 shapes) ----
const basals = store.basal.map((b, i) => ({ i, start: b.time + ":00", minutes: b.timeAsSeconds / 60, rate: b.value }));
const isf = { units: "mg/dL", sensitivities: store.sens.map(s => ({ sensitivity: s.value, offset: s.timeAsSeconds / 60, start: s.time + ":00" })) };
const carbratio = { units: "grams", schedule: store.carbratio.map(c => ({ ratio: c.value, offset: c.timeAsSeconds / 60, start: c.time + ":00" })) };
const targets = { units: "mg/dL", user_preferred_units: "mg/dL", targets: store.target_low.map((t, i) => ({ low: t.value, high: store.target_high[i].value, start: t.time + ":00", offset: t.timeAsSeconds / 60 })) };
const settings = { insulin_action_curve: Number(prefs.oapsDia || store.dia || 9), maxBolus: 12, maxBasal: 5, model: "720" };
// prefs are applied as TOP-LEVEL overrides (oref profile.generate's for-pref-in-profile loop)
const pinputs = Object.assign({}, prefs, { settings, targets, basals, isf, carbratio, model: '"720"', curve: prefs.curve, timezone: store.timezone, temptargets });
const profile = makeProfile(pinputs);
profile.timezone = store.timezone;
console.log("profile: dia", profile.dia, "sens", profile.sens, "current_basal", profile.current_basal, "curve", profile.curve, "insulinPeakTime", profile.insulinPeakTime, "max_iob", profile.max_iob);

// ---- treatments -> find_insulin format (NS eventType is parsed natively; SMB has no branch) ----
const hist = [];
for (const t of T) {
  if (t.eventType === 'SMB' || t.eventType === 'Bolus' || t.eventType === 'External Insulin') {
    if (t.insulin) hist.push({ _type: "Bolus", amount: t.insulin, timestamp: t.created_at });
  } else if (t.eventType === 'Temp Basal') {
    hist.push({ eventType: "Temp Basal", rate: (t.rate != null ? t.rate : t.absolute), duration: t.duration, timestamp: t.created_at, created_at: t.created_at });
  }
}
const carbs = T.filter(t => t.eventType === 'Carb Correction' && t.carbs).map(t => ({ carbs: t.carbs, created_at: t.created_at, _type: "carbs" }));

// ---- glucose: AAPS double-exponential smoothing (Trio's smoothGlucose) + <=clock filter ----
let g = E.filter(e => e.sgv).map(e => ({ date: new Date(e.dateString).getTime(), dateString: e.dateString, glucose: e.sgv, sgv: e.sgv }))
  .sort((a, b) => a.date - b.date).filter(x => x.date <= new Date(CLOCK).getTime());
function smooth(arr) {
  const out = arr.map(x => x.glucose); let seg = 0;
  for (let i = 1; i <= arr.length; i++) {
    const brk = (i === arr.length) || ((arr[i].date - arr[i - 1].date) / 60000 >= 12) || (Math.round(arr[i].glucose) === 38);
    if (brk) {
      const lo = seg, hi = i - 1, n = hi - lo + 1;
      if (n >= 4) {
        const fo = [arr[lo].glucose];
        for (let k = lo + 1; k <= hi; k++) fo.push(fo[fo.length - 1] + 0.5 * (arr[k].glucose - fo[fo.length - 1]));
        const so = [arr[lo].glucose]; let d = arr[lo + 1].glucose - arr[lo].glucose;
        for (let k = lo + 1; k <= hi; k++) { const ns = 0.4 * arr[k].glucose + 0.6 * (so[so.length - 1] + d); d = ns - so[so.length - 1]; so.push(ns); }
        for (let k = 0; k < n; k++) out[lo + k] = Math.max(Math.round(0.4 * fo[k] + 0.6 * so[k]), 39);
      } else { for (let k = lo; k <= hi; k++) out[k] = Math.max(arr[k].glucose, 39); }
      seg = i;
    }
  }
  return arr.map((x, i) => ({ ...x, glucose: out[i], sgv: out[i] }));
}
g = smooth(g);
const glucose = g.slice().reverse(); // newest-first

// ---- pipeline ----
const meal = mealGen({ history: hist, profile, basalprofile: basals, clock: CLOCK, glucose, carbs });
console.log("meal: COB", meal.mealCOB, "carbs", meal.carbs, "currentDeviation", meal.currentDeviation);
const as = autosens({ glucose_data: glucose, iob_inputs: { history: hist, profile, clock: CLOCK }, basalprofile: basals, profile, carbs, temptargets, retrospective: false, deviations: 96 });
console.log("autosens (deviation) ratio:", as.ratio);
const iob = iobGen({ history: hist, profile, clock: CLOCK, autosens: as });
const i0 = Array.isArray(iob) ? iob[0] : iob;
console.log("IOB:", i0.iob.toFixed(3), "basaliob", i0.basaliob.toFixed(3), "bolusiob", i0.bolusiob.toFixed(3), "netbasal", i0.netbasalinsulin.toFixed(2));
console.log("last 4 glucose (<=clock):", glucose.slice(0, 4).map(x => x.dateString.slice(11, 19) + "=" + x.glucose).join(" "));
const gs = glucoseGetLast(glucose); console.log("glucose_status: glucose", gs.glucose, "delta", gs.delta);
const ct = { duration: 0, rate: 0, temp: "absolute" };
// trio_custom: TDD fields drive dynISF; supply currentTDD/weightedAverage/average_total_data
// (from our scoring) + the override no-op fields. Set per cycle as needed.
const tc = { currentTDD: 47.2, weightedAverage: 45.7, average_total_data: 42.9, past2hoursAverage: 3.9, overridePercentage: 100, overrideTarget: 0, useOverride: false, duration: 0, smbIsOff: false, advancedSettings: false, isfAndCr: false, isf: false, cr: false, smbMinutes: 0, uamMinutes: 0 };
const out = determine(gs, ct, iob, profile, as, meal, basalSetTemp, true, 100, new Date(CLOCK), hist, prefs, basals, tc, "");
console.log("\n=== DETERMINATION ===");
console.log("rate", out.rate, "SMB", out.units, "eventualBG", out.eventualBG, "insulinReq", out.insulinReq);
console.log("reason:", (out.reason || "").slice(0, 200));
